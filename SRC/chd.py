# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""CHD (MAME's Compressed Hunks of Data) disc images, which PCSX2 runs and
many players keep instead of the 3.5 GB ISO of Let's Make a Soccer Team!
(PS2). Read only, like cso.py: cso.open_image() hands a CHD to Image here,
which reads as the ISO's bytes. Standard library only.

  header  v5, 124 bytes, big-endian: "MComprHD", u32 header size, u32
          version 5, 4 x u32 codec tags, u64 logical size, u64 map offset,
          u64 metadata offset, u32 hunk size, u32 unit size, raw SHA-1,
          SHA-1, parent SHA-1 (chd.cpp parse_v5_header)
  map     compressed: a Huffman tree (16 codes, 8 bits) of each hunk's
          compression, with run codes, then per hunk its length and CRC-16
          or a hunk number, all checked by a CRC-16 of the map
          (decompress_v5_map); uncompressed CHDs map hunks by number
  hunks   codec 0-3 (the header's tags), stored, or a copy of another hunk.
          Codecs: zlib (raw deflate), lzma (raw LZMA1, lc 3, lp 0, pb 2, the
          dictionary LZMA SDK level 8 picks for the hunk size), huff (MAME's
          8-bit Huffman), flac (raw FLAC frames of 16-bit stereo), zstd
          (Python 3.14's compression.zstd, if present), and the CD versions
          cdzl, cdlz, cdfl, cdzs: an ECC bitmap and the base length, then the
          frames' 2,352 sector bytes and their 96 subcode bytes (zlib, or zstd
          for cdzs). Marked frames get their sync and ECC rebuilt, so every
          hunk's CRC-16 is checked
  image   a DVD CHD (createdvd) or a raw one holds the ISO as is. A CD CHD
          (createcd) holds 2,448-byte frames; the ISO is each frame's 2,048
          data bytes, at the offset its one data track's type gives
          (CHT2 metadata)

Written from MAME 0.287's sources (src/lib/util: chd, chdcodec, huffman,
bitstream, flac, cdrom). Parent (delta) CHDs and versions before 5 are
refused. See DOC/REBUILD.md#compressed-images.

Usage:
    python chd.py info    <image.chd>     # header, codecs, metadata, map checks
    python chd.py check   <image.chd>     # decode all: data SHA-1 against the header, ISO SHA-1
    python chd.py extract <image.chd> <out.iso>
"""
import binascii
import hashlib
import os
import struct
import sys
import zlib

MAGIC = b"MComprHD"
V5_HEADER = 124
COMP_NONE, COMP_SELF, COMP_PARENT = 4, 5, 6
COMP_RLE_SMALL, COMP_RLE_LARGE, COMP_SELF_0, COMP_SELF_1 = 7, 8, 9, 10
COMP_PARENT_SELF, COMP_PARENT_0, COMP_PARENT_1 = 11, 12, 13
FRAME, SECTOR_DATA, SUBCODE = 2448, 2352, 96
SYNC = bytes([0] + [0xFF] * 10 + [0])
CHUNK = 1 << 24
REDUMP_SHA1 = "78771805294c924b68fe4aa01ad52f70229abb9d"   # extract_disc.REDUMP
# Where an ISO sector's 2,048 bytes sit in a frame, by CD track type (cdrom.cpp:
# cooked types store their data at the frame's start, raw ones whole sectors).
TRACK_DATA = {"MODE1": 0, "MODE1/2048": 0, "MODE2_FORM1": 0, "MODE1_RAW": 16,
              "MODE1/2352": 16, "MODE2_RAW": 24, "MODE2/2352": 24, "CDI/2352": 24}


def crc16(data):
    """MAME's util::crc16: CCITT, polynomial 0x1021, start 0xffff."""
    return binascii.crc_hqx(data, 0xFFFF)


class Bits:
    """MAME's bitstream_in: most significant bit first; past the end it
    reads zeros (bitstream.h)."""
    def __init__(self, data):
        self.data, self.pos = data, 0

    def peek(self, n):
        if n == 0:
            return 0
        byte, shift = self.pos >> 3, self.pos & 7
        chunk = self.data[byte:byte + 5]
        v = int.from_bytes(chunk.ljust(5, b"\0"), "big")
        return (v >> (40 - shift - n)) & ((1 << n) - 1)

    def read(self, n):
        v = self.peek(n)
        self.pos += n
        return v

    def offset(self):
        """Bytes consumed, the partial last one counted."""
        return (self.pos + 7) >> 3


class Huffman:
    """MAME's huffman_decoder: canonical codes, longest lengths numbered
    first (assign_canonical_codes); decoded by peeking maxbits."""
    def __init__(self, lengths, maxbits):
        self.maxbits = maxbits
        histo = [0] * 33
        for n in lengths:
            if n > maxbits:
                raise ValueError("Huffman: code length past the maximum")
            histo[n] += 1
        start = [0] * 33
        cur = 0
        for n in range(32, 0, -1):
            nxt = (cur + histo[n]) >> 1
            if n != 1 and nxt * 2 != cur + histo[n]:
                raise ValueError("Huffman: lengths don't make a code")
            start[n] = cur
            cur = nxt
        self.ranges = []                # (length, first code, [symbols])
        for n in range(1, maxbits + 1):
            syms = [s for s, ln in enumerate(lengths) if ln == n]
            if syms:
                self.ranges.append((n, start[n], syms))

    def decode(self, bits):
        v = bits.peek(self.maxbits)
        for n, first, syms in self.ranges:
            code = v >> (self.maxbits - n)
            if first <= code < first + len(syms):
                bits.pos += n
                return syms[code - first]
        # MAME's lookup table holds 0 for an unused code: symbol 0, no bits
        return 0

    @classmethod
    def from_rle(cls, bits, numcodes, maxbits):
        """import_tree_rle: 1 escapes a repeat count or a literal 1."""
        nb = 5 if maxbits >= 16 else (4 if maxbits >= 8 else 3)
        lengths = []
        while len(lengths) < numcodes:
            v = bits.read(nb)
            if v != 1:
                lengths.append(v)
            else:
                v = bits.read(nb)
                if v == 1:
                    lengths.append(1)
                else:
                    lengths += [v] * (bits.read(nb) + 3)
        if len(lengths) != numcodes:
            raise ValueError("Huffman: RLE tree overruns")
        return cls(lengths, maxbits)

    @classmethod
    def from_huffman(cls, bits, numcodes, maxbits):
        """import_tree_huffman: the lengths coded by a small 24-code tree."""
        small = [bits.read(3)]
        start = bits.read(3) + 1
        count = 0
        for index in range(1, 24):
            if index < start or count == 7:
                small.append(0)
            else:
                count = bits.read(3)
                small.append(0 if count == 7 else count)
        smallhuff = cls(small, 6)
        temp, fullbits = numcodes - 9, 0
        while temp:
            temp >>= 1
            fullbits += 1
        lengths, last = [], 0
        while len(lengths) < numcodes:
            v = smallhuff.decode(bits)
            if v:
                last = v - 1
                lengths.append(last)
            else:
                n = bits.read(3) + 2
                if n == 9:
                    n += bits.read(fullbits)
                lengths += [last] * min(n, numcodes - len(lengths))
        return cls(lengths, maxbits)


def huff_decode(src, size):
    """The huff codec (huffman_8bit_decoder). Decoded through a 2^16-entry
    table of symbol | length << 8, as MAME's build_lookup_table does (an
    unused code reads as symbol 0 of length 0), peeking 16 bits from
    24-bit words made once per hunk."""
    bits = Bits(src)
    h = Huffman.from_huffman(bits, 256, 16)
    # The table only needs the tree's longest code; peeking fewer bits than
    # 16 reads the same codes (they're prefix-free and MSB first).
    top = max((n for n, _, _ in h.ranges), default=1)
    sym, length = [0] * (1 << top), [0] * (1 << top)
    for n, first, syms in h.ranges:
        span = 1 << (top - n)
        for i, s in enumerate(syms):
            lo = (first + i) << (top - n)
            sym[lo:lo + span] = [s] * span
            length[lo:lo + span] = [n] * span
    mask, shift = (1 << top) - 1, 24 - top
    # 16 bits from any bit offset need 23 bits: the 3 bytes at pos >> 3.
    # Reading past the data is an error for MAME too (bitbuf.overflow()).
    d = bytes(src) + bytes(4)
    words = [(a << 16) | (b << 8) | c for a, b, c in zip(d, d[1:], d[2:])]
    pos = bits.pos
    out = bytearray(size)
    try:
        for i in range(size):
            k = (words[pos >> 3] >> (shift - (pos & 7))) & mask
            out[i] = sym[k]
            pos += length[k]
    except IndexError:
        raise ValueError("Huffman hunk overruns its data")
    return bytes(out)


def lzma_dict_size(hunkbytes):
    """LzmaEncProps_Normalize for level 8 and reduceSize = hunkbytes."""
    d = 1 << 26
    if hunkbytes < d:
        for i in range(11, 31):
            if hunkbytes <= 2 << i:
                return 2 << i
            if hunkbytes <= 3 << i:
                return 3 << i
    return d


def lzma_decode(src, size, hunkbytes):
    import lzma
    f = [{"id": lzma.FILTER_LZMA1, "dict_size": lzma_dict_size(hunkbytes),
          "lc": 3, "lp": 0, "pb": 2}]
    return lzma.LZMADecompressor(format=lzma.FORMAT_RAW, filters=f).decompress(src, size)


def zlib_decode(src, size):
    return zlib.decompressobj(-15).decompress(src, size)


def zstd_decode(src, size):
    try:
        from compression import zstd
    except ImportError:
        raise ValueError("this CHD uses zstd, which needs Python 3.14 or later; convert it "
                         "with chdman copy -c lzma,zlib,huff,flac, or to ISO")
    return zstd.decompress(src)[:size]


# --- FLAC ----------------------------------------------------------------------
# The flac codecs store bare FLAC frames (no stream header; flac.cpp feeds
# libFLAC a made-up STREAMINFO of 44,100 Hz, 2 channels, 16 bits).

FLAC_BLOCKS = {1: 192, 2: 576, 3: 1152, 4: 2304, 5: 4608}


def _signed(v, n):
    return v - (1 << n) if v & (1 << (n - 1)) else v


def _rice_residual(bits, blocksize, order):
    method = bits.read(2)
    if method > 1:
        raise ValueError("FLAC: reserved residual method")
    pbits, escape = (4, 15) if method == 0 else (5, 31)
    porder = bits.read(4)
    out = []
    for p in range(1 << porder):
        n = (blocksize >> porder) - (order if p == 0 else 0)
        k = bits.read(pbits)
        if k == escape:
            raw = bits.read(5)
            out += [_signed(bits.read(raw), raw) if raw else 0 for _ in range(n)]
            continue
        for _ in range(n):
            q = 0
            while not bits.read(1):
                q += 1
            v = (q << k) | bits.read(k)
            out.append((v >> 1) ^ -(v & 1))
    return out


FIXED = ((), (1,), (2, -1), (3, -3, 1), (4, -6, 4, -1))


def _subframe(bits, blocksize, bps):
    if bits.read(1):
        raise ValueError("FLAC: subframe padding bit set")
    kind = bits.read(6)
    wasted = 0
    if bits.read(1):
        wasted = 1
        while not bits.read(1):
            wasted += 1
        bps -= wasted
    if kind == 0:
        s = [_signed(bits.read(bps), bps)] * blocksize
    elif kind == 1:
        s = [_signed(bits.read(bps), bps) for _ in range(blocksize)]
    elif 8 <= kind <= 12 or kind >= 32:
        if kind >= 32:
            order = kind - 31
        else:
            order = kind - 8
        s = [_signed(bits.read(bps), bps) for _ in range(order)]
        if kind >= 32:
            prec = bits.read(4) + 1
            if prec == 16:
                raise ValueError("FLAC: invalid coefficient precision")
            shift = _signed(bits.read(5), 5)
            coefs = [_signed(bits.read(prec), prec) for _ in range(order)]
        else:
            shift, coefs = 0, FIXED[order]
        res = _rice_residual(bits, blocksize, order)
        for r in res:
            acc = 0
            for j, c in enumerate(coefs):
                acc += c * s[-1 - j]
            s.append(r + (acc >> shift))
    else:
        raise ValueError("FLAC: reserved subframe type %d" % kind)
    return [v << wasted for v in s] if wasted else s


def flac_frames(src, samples):
    """Decode FLAC frames until `samples` stereo samples are out; returns
    (left, right lists, bytes consumed)."""
    bits = Bits(src)
    left, right = [], []
    while len(left) < samples:
        bits.pos = (bits.pos + 7) & ~7
        if bits.read(15) != 0x7FFC:
            raise ValueError("FLAC: no frame sync")
        bits.read(1)                    # blocking strategy
        bs_code, sr_code = bits.read(4), bits.read(4)
        chans, ss_code = bits.read(4), bits.read(3)
        bits.read(1)
        b = bits.read(8)                # UTF-8 coded frame/sample number
        extra = 0
        while b & (0x80 >> extra) and extra < 7:
            extra += 1
        for _ in range(max(0, extra - 1)):
            bits.read(8)
        if bs_code == 6:
            blocksize = bits.read(8) + 1
        elif bs_code == 7:
            blocksize = bits.read(16) + 1
        elif bs_code >= 8:
            blocksize = 256 << (bs_code - 8)
        elif bs_code in FLAC_BLOCKS:
            blocksize = FLAC_BLOCKS[bs_code]
        else:
            raise ValueError("FLAC: reserved block size")
        if sr_code == 12:
            bits.read(8)
        elif sr_code in (13, 14):
            bits.read(16)
        bits.read(8)                    # CRC-8
        bps = {0: 16, 1: 8, 2: 12, 4: 16, 5: 20, 6: 24}.get(ss_code)
        if bps is None:
            raise ValueError("FLAC: reserved sample size")
        if chans == 1:
            a, c = _subframe(bits, blocksize, bps), _subframe(bits, blocksize, bps)
        elif chans == 8:                # left / side
            a = _subframe(bits, blocksize, bps)
            side = _subframe(bits, blocksize, bps + 1)
            c = [x - y for x, y in zip(a, side)]
        elif chans == 9:                # side / right
            side = _subframe(bits, blocksize, bps + 1)
            c = _subframe(bits, blocksize, bps)
            a = [x + y for x, y in zip(side, c)]
        elif chans == 10:               # mid / side
            mid = _subframe(bits, blocksize, bps)
            side = _subframe(bits, blocksize, bps + 1)
            a, c = [], []
            for m, s in zip(mid, side):
                m = (m << 1) | (s & 1)
                a.append((m + s) >> 1)
                c.append((m - s) >> 1)
        else:
            raise ValueError("FLAC: %d channels, not stereo" % (chans + 1))
        bits.pos = (bits.pos + 7) & ~7
        bits.read(16)                   # CRC-16
        left += a
        right += c
    return left[:samples], right[:samples], bits.offset()


def flac_pcm(left, right, little):
    fmt = "<h" if little else ">h"
    out = bytearray()
    pack = struct.Struct(fmt).pack
    for x, y in zip(left, right):
        out += pack(x)
        out += pack(y)
    return bytes(out)


def flac_decode(src, size):
    """The flac codec: 'L' or 'B' (byte order of the samples), then frames."""
    if src[:1] not in (b"L", b"B"):
        raise ValueError("FLAC hunk without a byte order mark")
    left, right, _ = flac_frames(src[1:], size // 4)
    return flac_pcm(left, right, src[:1] == b"L")


# --- CD ------------------------------------------------------------------------

def _ecc_tables():
    low = [((i << 1) ^ (0x11D if i & 0x80 else 0)) & 0xFF for i in range(256)]
    high = [0] * 256
    for i in range(256):
        high[i ^ low[i]] = i
    return low, high


ECC_LOW, ECC_HIGH = _ecc_tables()
# cdrom.cpp's poffsets/qoffsets, as the formulas they follow (checked).
ECC_P = [[b + 86 * c for c in range(24)] for b in range(86)]
ECC_Q = [[((b // 2) * 43 + c * 44) % 1118 * 2 + (b & 1) for c in range(43)] for b in range(52)]
ECC_P_OFFSET, ECC_Q_OFFSET = 0x81C, 0x81C + 172


def ecc_generate(sector):
    """cdrom_file::ecc_generate on a 2,352-byte bytearray."""
    mode2 = sector[15] == 2

    def src(off):
        return 0 if mode2 and off < 4 else sector[12 + off]

    for table, base, n in ((ECC_P, ECC_P_OFFSET, 86), (ECC_Q, ECC_Q_OFFSET, 52)):
        for b, row in enumerate(table):
            v1 = v2 = 0
            for off in row:
                x = src(off)
                v1 = ECC_LOW[v1 ^ x]
                v2 ^= x
            v1 = ECC_HIGH[ECC_LOW[v1] ^ v2]
            sector[base + b] = v1
            sector[base + n + b] = v2 ^ v1


def cd_decode(src, size, base):
    """cdzl/cdlz/cdzs: ECC bitmap, base length, base codec, subcode codec."""
    frames = size // FRAME
    len_bytes = 2 if size < 65536 else 3
    ecc_bytes = (frames + 7) // 8
    head = ecc_bytes + len_bytes
    base_len = int.from_bytes(src[ecc_bytes:head], "big")
    sectors = base(src[head:head + base_len], frames * SECTOR_DATA)
    sub_src = src[head + base_len:]
    if base is zstd_decode:
        subs = zstd_decode(sub_src, frames * SUBCODE)
    else:
        subs = zlib_decode(sub_src, frames * SUBCODE)
    return cd_join(sectors, subs, frames, src[:ecc_bytes])


def cdfl_decode(src, size):
    """cdfl: FLAC (big-endian samples) of the sectors, then zlib subcode."""
    frames = size // FRAME
    left, right, used = flac_frames(src, frames * SECTOR_DATA // 4)
    sectors = flac_pcm(left, right, False)
    subs = zlib_decode(src[used:], frames * SUBCODE)
    return cd_join(sectors, subs, frames, b"")


def cd_join(sectors, subs, frames, ecc_map):
    if len(sectors) != frames * SECTOR_DATA or len(subs) != frames * SUBCODE:
        raise ValueError("CD hunk decoded short")
    out = bytearray()
    for f in range(frames):
        sector = bytearray(sectors[f * SECTOR_DATA:(f + 1) * SECTOR_DATA])
        if ecc_map and ecc_map[f // 8] & (1 << (f % 8)):
            sector[:12] = SYNC
            ecc_generate(sector)
        out += sector
        out += subs[f * SUBCODE:(f + 1) * SUBCODE]
    return bytes(out)


# --- the file ------------------------------------------------------------------

class Image:
    """A CHD as a read-only, seekable file of the ISO's bytes."""
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        h = self.f.read(V5_HEADER)
        if h[:8] != MAGIC:
            raise ValueError("%s: not a CHD" % path)
        hlen, self.version = struct.unpack_from(">II", h, 8)
        if self.version != 5 or hlen != V5_HEADER:
            raise ValueError("%s: CHD version %d; only version 5 is read (chdman copy "
                             "converts older ones)" % (path, self.version))
        self.codecs = [h[16 + 4 * i:20 + 4 * i] for i in range(4)]
        (self.logical, self.map_off, self.meta_off, self.hunk,
         self.unit) = struct.unpack_from(">QQQII", h, 32)
        self.raw_sha1 = h[64:84].hex()
        self.sha1 = h[84:104].hex()
        if any(h[104:124]):
            raise ValueError("%s: a parent (delta) CHD; it needs its parent" % path)
        self.hunks = (self.logical + self.hunk - 1) // self.hunk
        self.meta = self.read_metadata()
        self.compressed = self.codecs[0] != b"\0\0\0\0"
        self.map = self.read_map()
        self.layout()
        self.pos = 0
        self.cached = (-1, b"")

    # metadata and layout

    def read_metadata(self):
        out = []
        off = self.meta_off
        while off:
            self.f.seek(off)
            tag, flags_len, nxt = struct.unpack(">IIQ", self.f.read(16))
            n = flags_len & 0xFFFFFF
            out.append((tag.to_bytes(4, "big"), self.f.read(n)))
            off = nxt
        return out

    def layout(self):
        """Where the ISO is: the logical bytes (DVD, raw), or frames of
        one CD data track."""
        tracks = [d for t, d in self.meta if t in (b"CHT2", b"CHTR", b"CHCD")]
        if not tracks:
            self.kind, self.size, self.data_off = "DVD" if any(
                t == b"DVD " for t, _ in self.meta) else "raw", self.logical, None
            return
        if len(tracks) != 1:
            raise ValueError("%s: a CD CHD with %d tracks; one data track is read"
                             % (self.path, len(tracks)))
        fields = dict(f.split(":", 1) for f in tracks[0].decode("ascii", "replace")
                      .rstrip("\0").split() if ":" in f)
        ttype = fields.get("TYPE", "")
        if ttype not in TRACK_DATA:
            raise ValueError("%s: CD track type %s isn't a data track" % (self.path, ttype))
        if self.hunk % FRAME:
            raise ValueError("%s: CD hunk size isn't whole frames" % self.path)
        self.kind = "CD (%s)" % ttype
        self.data_off = TRACK_DATA[ttype]
        self.size = int(fields.get("FRAMES", "0")) * 2048
        if int(fields.get("PREGAP", "0")) and fields.get("PGTYPE", "").startswith("V"):
            raise ValueError("%s: a CD track with a stored pregap isn't read" % self.path)

    def read_map(self):
        if not self.compressed:
            self.f.seek(V5_HEADER)
            raw = self.f.read(4 * self.hunks)
            return [(COMP_NONE if v else None, v * self.hunk, self.hunk, None)
                    for v in struct.unpack(">%dI" % self.hunks, raw)]
        self.f.seek(self.map_off)
        head = self.f.read(16)
        mapbytes = int.from_bytes(head[0:4], "big")
        first = int.from_bytes(head[4:10], "big")
        mapcrc = int.from_bytes(head[10:12], "big")
        lenbits, selfbits, parentbits = head[12], head[13], head[14]
        bits = Bits(self.f.read(mapbytes))
        tree = Huffman.from_rle(bits, 16, 8)
        kinds, last, rep = [], 0, 0
        for _ in range(self.hunks):
            if rep:
                kinds.append(last)
                rep -= 1
                continue
            v = tree.decode(bits)
            if v == COMP_RLE_SMALL:
                rep = 2 + tree.decode(bits)     # this hunk, then 2 + n more
                kinds.append(last)
            elif v == COMP_RLE_LARGE:
                rep = 2 + 16 + (tree.decode(bits) << 4)
                rep += tree.decode(bits)
                kinds.append(last)
            else:
                kinds.append(v)
                last = v
        out, raw = [], bytearray()
        cur, last_self = first, 0
        for n, k in enumerate(kinds):
            offset, length, crc = cur, 0, 0
            if k <= 3:
                length = bits.read(lenbits)
                cur += length
                crc = bits.read(16)
            elif k == COMP_NONE:
                length = self.hunk
                cur += length
                crc = bits.read(16)
            elif k == COMP_SELF:
                offset = last_self = bits.read(selfbits)
            elif k in (COMP_SELF_0, COMP_SELF_1):
                if k == COMP_SELF_1:
                    last_self += 1
                k, offset = COMP_SELF, last_self
            elif k in (COMP_PARENT, COMP_PARENT_SELF, COMP_PARENT_0, COMP_PARENT_1):
                raise ValueError("%s: hunk %d is in a parent CHD" % (self.path, n))
            else:
                raise ValueError("%s: hunk %d has map type %d" % (self.path, n, k))
            raw += bytes([k]) + length.to_bytes(3, "big") + offset.to_bytes(6, "big") \
                + crc.to_bytes(2, "big")
            out.append((k, offset, length, crc))
        if crc16(bytes(raw)) != mapcrc:
            raise ValueError("%s: the hunk map's CRC doesn't match" % self.path)
        return out

    # hunks

    def codec_name(self, i):
        return self.codecs[i].decode("ascii", "replace")

    def read_hunk(self, n, depth=0):
        if self.cached[0] == n:
            return self.cached[1]
        k, off, length, crc = self.map[n]
        if k is None:
            data = bytes(self.hunk)
        elif k == COMP_SELF:
            if depth > 16 or off >= self.hunks:
                raise ValueError("%s: hunk %d copies a bad hunk" % (self.path, n))
            data = self.read_hunk(off, depth + 1)
        else:
            self.f.seek(off)
            src = self.f.read(length)
            if k == COMP_NONE:
                data = src
            else:
                data = self.decode(self.codecs[k], src)
            if crc is not None and crc16(data) != crc:
                raise ValueError("%s: hunk %d (%s) fails its CRC" % (
                    self.path, n, "stored" if k == COMP_NONE else self.codec_name(k)))
        if len(data) != self.hunk:
            raise ValueError("%s: hunk %d decoded to %d bytes" % (self.path, n, len(data)))
        self.cached = (n, data)
        return data

    def decode(self, tag, src):
        size = self.hunk
        sec = size // FRAME * SECTOR_DATA
        if tag == b"zlib":
            return zlib_decode(src, size)
        if tag == b"lzma":
            return lzma_decode(src, size, size)
        if tag == b"huff":
            return huff_decode(src, size)
        if tag == b"flac":
            return flac_decode(src, size)
        if tag == b"zstd":
            return zstd_decode(src, size)
        if tag == b"cdzl":
            return cd_decode(src, size, zlib_decode)
        if tag == b"cdlz":
            return cd_decode(src, size, lambda s, n: lzma_decode(s, n, sec))
        if tag == b"cdzs":
            return cd_decode(src, size, zstd_decode)
        if tag == b"cdfl":
            return cdfl_decode(src, size)
        raise ValueError("%s: codec %r isn't read" % (self.path, tag.decode("latin1")))

    def read_logical(self, pos, n):
        out = bytearray()
        while n > 0 and pos < self.logical:
            h, o = divmod(pos, self.hunk)
            take = self.read_hunk(h)[o:o + n]
            out += take
            pos += len(take)
            n -= len(take)
        return bytes(out)

    # file interface (the ISO's bytes)

    def seek(self, pos, whence=0):
        if whence == 1:
            pos += self.pos
        elif whence == 2:
            pos += self.size
        self.pos = max(0, pos)
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n < 0 or self.pos + n > self.size:
            n = max(0, self.size - self.pos)
        if self.data_off is None:
            out = self.read_logical(self.pos, n)
        else:
            out = bytearray()
            while len(out) < n:
                sec, o = divmod(self.pos + len(out), 2048)
                frame = self.read_logical(sec * FRAME + self.data_off + o,
                                          min(2048 - o, n - len(out)))
                out += frame
            out = bytes(out)
        self.pos += len(out)
        return out

    def close(self):
        self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def is_chd(path):
    with open(path, "rb") as f:
        return f.read(8) == MAGIC


class Progress:
    def __init__(self, label):
        self.shown = 0
        print(label, end="", flush=True)

    def __call__(self, done, total):
        while total and self.shown < 10 * done // total:
            self.shown += 1
            print(" %d%%" % (self.shown * 10), end="", flush=True)

    def end(self):
        print()


def cmd_info(path):
    try:
        with Image(path) as img:
            kinds = {}
            for k, _, _, _ in img.map:
                name = ("none" if k is None else "stored" if k == COMP_NONE else
                        "copy" if k == COMP_SELF else img.codec_name(k))
                kinds[name] = kinds.get(name, 0) + 1
            print("%s: CHD v%d, %s, %d hunks of %d, logical %d bytes, ISO %d bytes" % (
                path, img.version, img.kind, img.hunks, img.hunk, img.logical, img.size))
            print("  codecs %s; hunks by codec: %s" % (
                ", ".join(img.codec_name(i) for i in range(4) if img.codecs[i] != b"\0" * 4)
                or "none", ", ".join("%s %d" % kv for kv in sorted(kinds.items()))))
            print("  data SHA-1 %s" % img.raw_sha1)
            for tag, data in img.meta:
                print("  metadata %s: %s" % (tag.decode("latin1"),
                                            data.rstrip(b"\0").decode("latin1")[:100]))
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))


def cmd_check(path):
    """Decode every hunk once: each passes its CRC, the data SHA-1 is
    checked against the header (chdman leaves it zero in an uncompressed
    CHD), and the ISO's SHA-1 comes from the same pass."""
    with Image(path) as img:
        p = Progress("Decoding %s:" % os.path.basename(path))
        raw, iso = hashlib.sha1(), hashlib.sha1()
        frames = img.size // 2048
        for n in range(img.hunks):
            data = img.read_hunk(n)[:img.logical - n * img.hunk]
            raw.update(data)
            if img.data_off is not None:
                first = n * img.hunk // FRAME
                for f in range(first, min(first + img.hunk // FRAME, frames)):
                    o = (f - first) * FRAME + img.data_off
                    iso.update(data[o:o + 2048])
            p(n + 1, img.hunks)
        p.end()
        got = raw.hexdigest()
        if img.raw_sha1 == "0" * 40:
            verdict = " (the header records none)"
        elif got == img.raw_sha1:
            verdict = " (matches the header)"
        else:
            verdict = "  !! the header says %s" % img.raw_sha1
        print("%s: every hunk %s; data SHA-1 %s%s" % (
            path, "passed its CRC" if img.compressed else "read (stored, no CRCs)", got, verdict))
        sha = got if img.data_off is None else iso.hexdigest()
        print("  ISO %d bytes, SHA-1 %s%s" % (img.size, sha, "  (the Redump image)"
                                               if sha == REDUMP_SHA1 else "  (not the Redump image)"))


def cmd_extract(path, out):
    if os.path.abspath(out) == os.path.abspath(path):
        raise SystemExit("the output would overwrite the input")
    with Image(path) as img, open(out, "wb") as f:
        p = Progress("Decoding %s:" % os.path.basename(path))
        h = hashlib.sha1()
        while buf := img.read(CHUNK):
            f.write(buf)
            h.update(buf)
            p(img.pos, img.size)
        p.end()
    sha = h.hexdigest()
    print("wrote %s: %d bytes, SHA-1 %s%s" % (out, os.path.getsize(out), sha,
                                              "  (the Redump image)" if sha == REDUMP_SHA1 else ""))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "info" and len(args) == 1:
            cmd_info(args[0])
        elif cmd == "check" and len(args) == 1:
            cmd_check(args[0])
        elif cmd == "extract" and len(args) == 2:
            cmd_extract(*args)
        else:
            print(__doc__)
            return 1
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
