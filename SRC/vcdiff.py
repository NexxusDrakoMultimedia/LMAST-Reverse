# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""VCDIFF (RFC 3284) patches, the format xdelta3 writes, for sharing mods
of Let's Make a Soccer Team! (PS2) as small files against the user's own
disc image. Standard library only; no xdelta3 needed.

`make` compares a source (the unmodified Redump image) with a target (the
patched image) in 8 MiB windows. Each window takes the same range of the
source as its source segment and is encoded as COPY instructions for
unchanged runs and ADD instructions for changed bytes, using the default
code table and no secondary compression, so any RFC 3284 decoder (xdelta3,
xdelta UI, DeltaPatcher, open-vcdiff) can apply it. A few changed bytes in
a 3.5 GB image make a patch of about 10 KB (one COPY per unchanged
window: the Terry mod's is 10,642 bytes).

`apply` decodes any VCDIFF file without a custom code table: all of the
default code table, the address cache, RUN and overlapping COPY, source
and target (VCD_TARGET) windows, xdelta3's application header and its
per-window Adler-32 (checked), and xdelta3's secondary compression of the
sections: LZMA (xdelta3's default since 3.1, through the lzma module) and
DJW (decoded here). FGK, which xdelta3 3.2 no longer builds, is refused.
Tested with patches from xdelta3 3.1.0 and 3.2.2 (DOC/REBUILD.md). The
source, and make's inputs, may be CSO, ZSO or CHD images (cso.py, chd.py).

Usage:
    python vcdiff.py make  <source> <target> <out.xdelta>
    python vcdiff.py apply <source> <patch.xdelta> <out>
    python vcdiff.py info  <patch.xdelta>
    python vcdiff.py roundtrip <source> <target>      # make + apply in memory, check the result

`make` and `apply` print SHA-1s so a patch can be published with the hash
of the image it expects and the one it produces; `make` warns if the source
isn't the Redump dump (redump.info/disc/12334).
"""
import hashlib
import io
import os
import sys
import zlib

import cso

MAGIC = b"\xd6\xc3\xc4\x00"
VCD_DECOMPRESS, VCD_CODETABLE, VCD_APPHEADER = 0x01, 0x02, 0x04    # Hdr_Indicator
VCD_SOURCE, VCD_TARGET, VCD_ADLER32 = 0x01, 0x02, 0x04             # Win_Indicator (0x04: xdelta3)
NOOP, ADD, RUN, COPY = 0, 1, 2, 3
S_NEAR, S_SAME = 4, 3
WINDOW = 1 << 23            # 8 MiB, xdelta3's default window
BLOCK = 0x1000              # compare step inside a window
MERGE_GAP = 16              # equal gaps this short are folded into an ADD
# Default code table indexes used by the encoder (RFC 3284 5.6).
ADD_SIZE0 = 1               # ADD, size follows
COPY_SELF_SIZE0 = 19        # COPY mode 0 (VCD_SELF), size follows

REDUMP_SHA1 = "78771805294c924b68fe4aa01ad52f70229abb9d"   # extract_disc.REDUMP


def default_code_table():
    """RFC 3284 section 5.6: 256 (inst1, size1, mode1, inst2, size2, mode2)."""
    t = [(RUN, 0, 0, NOOP, 0, 0)]
    t += [(ADD, s, 0, NOOP, 0, 0) for s in range(0, 18)]
    for mode in range(9):
        t.append((COPY, 0, mode, NOOP, 0, 0))
        t += [(COPY, s, mode, NOOP, 0, 0) for s in range(4, 19)]
    for mode in range(6):
        t += [(ADD, a, 0, COPY, c, mode) for a in range(1, 5) for c in range(4, 7)]
    for mode in range(6, 9):
        t += [(ADD, a, 0, COPY, 4, mode) for a in range(1, 5)]
    t += [(COPY, 4, mode, ADD, 1, 0) for mode in range(9)]
    assert len(t) == 256
    return t


CODE_TABLE = default_code_table()
assert CODE_TABLE[ADD_SIZE0] == (ADD, 0, 0, NOOP, 0, 0)
assert CODE_TABLE[COPY_SELF_SIZE0] == (COPY, 0, 0, NOOP, 0, 0)


# --- integers ----------------------------------------------------------------

def put_int(n):
    """RFC 3284 2.2: base-128, most significant digit first, high bit set on
    every byte but the last."""
    out = [n & 0x7f]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7f))
        n >>= 7
    return bytes(reversed(out))


class Reader:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def byte(self):
        if self.pos >= len(self.data):
            raise ValueError("truncated VCDIFF data")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def int(self):
        n = 0
        for _ in range(10):
            b = self.byte()
            n = (n << 7) | (b & 0x7f)
            if not b & 0x80:
                return n
        raise ValueError("integer too long")

    def take(self, n):
        if self.pos + n > len(self.data):
            raise ValueError("truncated VCDIFF data")
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b


# --- encoder -----------------------------------------------------------------

def changed_ranges(src, tgt):
    """[(start, end)] where tgt differs from src (src may be shorter), with
    short equal gaps folded in."""
    ranges = []
    n = len(tgt)
    common = min(len(src), n)
    for b in range(0, common, BLOCK):
        e = min(b + BLOCK, common)
        if src[b:e] == tgt[b:e]:
            continue
        i = b
        while i < e:
            if src[i] != tgt[i]:
                j = i + 1
                while j < e and src[j] != tgt[j]:
                    j += 1
                if ranges and i - ranges[-1][1] <= MERGE_GAP:
                    ranges[-1] = (ranges[-1][0], j)
                else:
                    ranges.append((i, j))
                i = j
            else:
                i += 1
    if n > common:
        if ranges and common - ranges[-1][1] <= MERGE_GAP:
            ranges[-1] = (ranges[-1][0], n)
        else:
            ranges.append((common, n))
    return ranges


def encode_window(src, tgt, src_pos):
    """One window: tgt against the source segment src (at src_pos)."""
    data, inst, addr = bytearray(), bytearray(), bytearray()
    pos = 0
    for start, end in changed_ranges(src, tgt):
        if start > pos:
            inst += bytes([COPY_SELF_SIZE0]) + put_int(start - pos)
            addr += put_int(pos)                 # VCD_SELF: address as is
        inst += bytes([ADD_SIZE0]) + put_int(end - start)
        data += tgt[start:end]
        pos = end
    if pos < len(tgt):
        inst += bytes([COPY_SELF_SIZE0]) + put_int(len(tgt) - pos)
        addr += put_int(pos)
    body = (put_int(len(tgt)) + b"\x00" + put_int(len(data)) + put_int(len(inst))
            + put_int(len(addr)) + bytes(data) + bytes(inst) + bytes(addr))
    if src:
        head = bytes([VCD_SOURCE]) + put_int(len(src)) + put_int(src_pos)
    else:
        head = b"\x00"
    return head + put_int(len(body)) + body


def encode(src_file, tgt_file, out_file, progress=None):
    """Write a VCDIFF of tgt_file against src_file; return the SHA-1s."""
    src_len = _size(src_file)
    tgt_len = _size(tgt_file)
    hs, ht = hashlib.sha1(), hashlib.sha1()
    out_file.write(MAGIC + b"\x00")
    pos = 0
    while pos < tgt_len or pos == 0:
        tgt_file.seek(pos)
        tgt = tgt_file.read(WINDOW)
        src_file.seek(pos)
        src = src_file.read(min(WINDOW, max(0, src_len - pos)))
        hs.update(src)
        ht.update(tgt)
        out_file.write(encode_window(src, tgt, pos))
        pos += len(tgt)
        if progress:
            progress(pos, tgt_len)
        if not tgt:
            break
    if src_len > tgt_len:                       # hash the rest of a longer source
        src_file.seek(tgt_len)
        while buf := src_file.read(WINDOW):
            hs.update(buf)
    return hs.hexdigest(), ht.hexdigest()


def _size(f):
    here = f.tell()
    f.seek(0, os.SEEK_END)
    n = f.tell()
    f.seek(here)
    return n


# --- secondary compression (xdelta3's own) -----------------------------------
# xdelta3 can compress each window's data, instruction and address sections
# (Delta_Indicator bits VCD_DATACOMP 1, VCD_INSTCOMP 2, VCD_ADDRCOMP 4) with
# the compressor named by the byte after Hdr_Indicator: 1 DJW, 2 LZMA (the
# default since xdelta3 3.1), 16 FGK. A compressed section is its decoded
# size as a VCDIFF integer, then the coded bytes (xdelta3-second.h,
# xd3_decode_secondary). Written from xdelta3 3.1.0 and 3.2.2's sources,
# whose coders are the same.

SEC_DJW, SEC_LZMA, SEC_FGK = 1, 2, 16
SECTION_BITS = (1, 2, 4)                # data, inst, addr
DJW_MAX_CODELEN, DJW_TOTAL_CODES = 20, 22
DJW_EXTRA_12OFFSET, DJW_EXTRA_CODE_BITS = 7, 4
DJW_GROUP_BITS, DJW_SECTORSZ_BITS, DJW_SECTORSZ_MULT = 3, 5, 5
DJW_MAX_CLCLEN, DJW_CLCLEN_BITS, DJW_MAX_GBCLEN, DJW_GBCLEN_BITS = 15, 4, 7, 3
# The code-length MTF starts as 0, the basic lengths, then the extra ones
# (djw_init_clen_mtf_1_2).
DJW_CLEN_MTF = (0, 4, 5, 6, 7, 8, 9, 10, 3, 11, 2, 12, 13, 1, 14, 15, 16, 17, 18, 19, 20)
ALPHABET = 256


class Bits:
    """xdelta3's bit reader: bits from the low end of each byte, values most
    significant bit first (xd3_decode_bits)."""
    def __init__(self, data):
        self.data, self.pos, self.byte, self.mask = data, 0, 0, 0x100

    def bit(self):
        if self.mask == 0x100:
            if self.pos >= len(self.data):
                raise ValueError("DJW: section ends too early")
            self.byte, self.mask = self.data[self.pos], 1
            self.pos += 1
        b = 1 if self.byte & self.mask else 0
        self.mask <<= 1
        return b

    def bits(self, n):
        v = 0
        for _ in range(n):
            v = (v << 1) | self.bit()
        return v


class HuffDecoder:
    """A canonical prefix decoder from code lengths (djw_build_decoder)."""
    def __init__(self, clen, abs_max):
        nr = [0] * (abs_max + 2)
        for c in clen:
            if c > abs_max:
                raise ValueError("DJW: code length out of range")
            nr[c] += 1
        lens = [i for i in range(1, abs_max + 1) if nr[i]]
        if not lens:
            raise ValueError("DJW: empty code")
        self.min, self.max = lens[0], lens[-1]
        base, limit, tmp = {}, {}, {}
        tmp[self.min] = base[self.min] = 0
        limit[self.min] = nr[self.min] - 1
        for i in range(self.min + 1, self.max + 1):
            last = (limit[i - 1] + 1) << 1
            tmp[i] = tmp[i - 1] + nr[i - 1]
            limit[i] = last + nr[i] - 1
            base[i] = last - tmp[i]
        self.base, self.limit = base, limit
        self.inorder = [0] * len(clen)
        for sym, c in enumerate(clen):
            if c:
                self.inorder[tmp[c]] = sym
                tmp[c] += 1

    def symbol(self, bits, max_sym):
        code = n = 0
        while True:
            if n == self.max:
                raise ValueError("DJW: invalid code")
            n += 1
            code = (code << 1) | bits.bit()
            if n >= self.min and code <= self.limit[n]:
                break
        off = code - self.base[n]
        if off < 0 or off > max_sym:
            raise ValueError("DJW: invalid code")
        return self.inorder[off]


def djw_decode_1_2(bits, dec, mtf, count, skip=0, values=None):
    """Move-to-front values with 1-2 coded runs (djw_decode_1_2): symbols 0
    and 1 are run digits, others index the MTF list less one."""
    values = values if values is not None else []
    rep = sel = shift = 0
    while len(values) < count:
        n = len(values)
        if skip and n >= skip and values[n - skip] == 0:
            values.append(0)
        elif rep:
            values.append(mtf[0])
            rep -= 1
        elif sel:
            sym = mtf.pop(sel)
            mtf.insert(0, sym)
            values.append(sym)
            sel = 0
        else:
            s = dec.symbol(bits, DJW_TOTAL_CODES)
            if s <= 1:
                rep = (s + 1) << shift
                shift += 1
            else:
                sel = s - 1
                shift = 0
    if rep:
        raise ValueError("DJW: invalid repeat code")
    return values


def djw_decode(data, size):
    """One DJW-coded section (xd3_decode_huff): Huffman tables per group of
    sectors, their code lengths themselves Huffman and MTF coded."""
    bits = Bits(data)
    groups = bits.bits(DJW_GROUP_BITS) + 1
    if groups > 1:
        sector = (bits.bits(DJW_SECTORSZ_BITS) + 1) * DJW_SECTORSZ_MULT
    else:
        sector = size
    sectors = 1 + (size - 1) // sector
    # The code-length code: 7 + a 4-bit count of lengths, 4 bits each.
    n = bits.bits(DJW_EXTRA_CODE_BITS) + DJW_EXTRA_12OFFSET
    cl_clen = [bits.bits(DJW_CLCLEN_BITS) for _ in range(n)] + [0] * (DJW_TOTAL_CODES - n)
    cl_dec = HuffDecoder(cl_clen, DJW_MAX_CLCLEN)
    clen = djw_decode_1_2(bits, cl_dec, list(DJW_CLEN_MTF), ALPHABET * groups, ALPHABET)
    decs = [HuffDecoder(clen[g * ALPHABET:(g + 1) * ALPHABET], DJW_MAX_CODELEN)
            for g in range(groups)]
    if groups > 1:
        sel_clen = [bits.bits(DJW_GBCLEN_BITS) for _ in range(groups + 1)]
        sel_dec = HuffDecoder(sel_clen, DJW_MAX_GBCLEN)
        selectors = djw_decode_1_2(bits, sel_dec, list(range(groups + 1)), sectors)
    else:
        selectors = [0]
    out = bytearray()
    for c in range(sectors):
        g = selectors[c]
        if g >= groups:
            raise ValueError("DJW: invalid group")
        dec = decs[g]
        for _ in range(min(sector, size - len(out))):
            out.append(dec.symbol(bits, ALPHABET))
    if bits.pos != len(data):
        raise ValueError("DJW: unused input at the end of a section")
    return bytes(out)


class Secondary:
    """The secondary decompressor of one patch. LZMA keeps one xz stream per
    section kind for the whole file, flushed at the end of each window
    (xdelta3-lzma.h: one stream encoder, LZMA_SYNC_FLUSH), so its state
    carries from window to window."""
    NAMES = {SEC_DJW: "DJW", SEC_LZMA: "LZMA", SEC_FGK: "FGK"}

    def __init__(self, sec_id):
        if sec_id not in (SEC_DJW, SEC_LZMA):
            raise ValueError("secondary compression %s is not supported; ask for the patch "
                             "made with xdelta3 -S lzma or -S none"
                             % self.NAMES.get(sec_id, "id %d" % sec_id))
        self.id = sec_id
        self.lzma = [None, None, None]

    def decode(self, kind, section):
        r = Reader(section)
        size = r.int()
        coded = section[r.pos:]
        if size == 0:
            raise ValueError("secondary section with no output")
        if self.id == SEC_DJW:
            out = djw_decode(coded, size)
        else:
            import lzma
            if self.lzma[kind] is None:
                self.lzma[kind] = lzma.LZMADecompressor(format=lzma.FORMAT_XZ)
            out = self.lzma[kind].decompress(coded)
        if len(out) != size:
            raise ValueError("secondary section decoded to %d bytes, expected %d"
                             % (len(out), size))
        return out


# --- decoder -----------------------------------------------------------------

class Window:
    def __init__(self, indicator, seg_len, seg_pos, tgt_len, data, inst, addr, checksum):
        self.indicator, self.seg_len, self.seg_pos = indicator, seg_len, seg_pos
        self.tgt_len, self.data, self.inst, self.addr = tgt_len, data, inst, addr
        self.checksum = checksum


def parse(patch):
    """(header info, [Window]) of a VCDIFF file in memory."""
    if patch[:4] != MAGIC:
        raise ValueError("not a VCDIFF file")
    r = Reader(patch, 4)
    hdr = r.byte()
    info = {"app_header": b"", "secondary": None}
    secondary = None
    if hdr & VCD_DECOMPRESS:
        secondary = Secondary(r.byte())
        info["secondary"] = Secondary.NAMES[secondary.id]
    if hdr & VCD_CODETABLE:
        raise ValueError("custom code tables are not supported")
    if hdr & VCD_APPHEADER:
        info["app_header"] = r.take(r.int())
    windows = []
    while r.pos < len(patch):
        ind = r.byte()
        seg_len = seg_pos = 0
        if ind & VCD_SOURCE and ind & VCD_TARGET:
            raise ValueError("window with both VCD_SOURCE and VCD_TARGET")
        if ind & (VCD_SOURCE | VCD_TARGET):
            seg_len, seg_pos = r.int(), r.int()
        delta_len = r.int()
        end = r.pos + delta_len
        tgt_len = r.int()
        compressed = r.byte()
        if compressed and secondary is None:
            raise ValueError("compressed delta sections but no secondary compressor")
        dl, il, al = r.int(), r.int(), r.int()
        checksum = None
        if ind & VCD_ADLER32:
            checksum = int.from_bytes(r.take(4), "big")
        sections = [r.take(dl), r.take(il), r.take(al)]
        if r.pos != end:
            raise ValueError("window length mismatch")
        for kind, bit in enumerate(SECTION_BITS):
            if compressed & bit:
                sections[kind] = secondary.decode(kind, sections[kind])
        data, inst, addr = sections
        windows.append(Window(ind, seg_len, seg_pos, tgt_len, data, inst, addr, checksum))
    return info, windows


def decode_window(w, segment):
    """The target bytes of one window, given its source segment bytes."""
    out = bytearray()
    data, inst, addr = Reader(w.data), Reader(w.inst), Reader(w.addr)
    near, next_slot, same = [0] * S_NEAR, 0, [0] * (S_SAME * 256)
    seg_len = len(segment)

    def address(mode):
        nonlocal next_slot
        here = seg_len + len(out)
        if mode == 0:
            a = addr.int()
        elif mode == 1:
            a = here - addr.int()
        elif mode < 2 + S_NEAR:
            a = near[mode - 2] + addr.int()
        else:
            a = same[(mode - 2 - S_NEAR) * 256 + addr.byte()]
        near[next_slot] = a
        next_slot = (next_slot + 1) % S_NEAR
        same[a % (S_SAME * 256)] = a
        return a

    while inst.pos < len(w.inst):
        code = CODE_TABLE[inst.byte()]
        for kind, size, mode in (code[0:3], code[3:6]):
            if kind == NOOP:
                continue
            if size == 0:
                size = inst.int()
            if kind == ADD:
                out += data.take(size)
            elif kind == RUN:
                out += bytes([data.byte()]) * size
            else:
                a = address(mode)
                if a + size <= seg_len:
                    out += segment[a:a + size]
                else:
                    for k in range(size):       # may read what it writes
                        p = a + k
                        out.append(segment[p] if p < seg_len else out[p - seg_len])
    if len(out) != w.tgt_len:
        raise ValueError("window decoded to %d bytes, header says %d" % (len(out), w.tgt_len))
    if w.checksum is not None and (zlib.adler32(bytes(out)) & 0xffffffff) != w.checksum:
        raise ValueError("window Adler-32 mismatch: wrong source file?")
    return bytes(out)


def decode(src_file, patch, out_file, progress=None):
    """Apply a VCDIFF to src_file (None for a patch made without one);
    return the output SHA-1. A VCD_TARGET window copies from what is already
    written, so out_file must be readable too ("w+b")."""
    _, windows = parse(patch)
    h = hashlib.sha1()
    total = sum(w.tgt_len for w in windows)
    done = 0
    for w in windows:
        segment = b""
        if w.indicator & VCD_TARGET:
            if w.seg_pos + w.seg_len > done:
                raise ValueError("VCD_TARGET window reads past the output so far")
            out_file.seek(w.seg_pos)
            segment = out_file.read(w.seg_len)
            out_file.seek(done)
        elif w.indicator & VCD_SOURCE:
            if src_file is None:
                raise ValueError("this patch needs a source file")
            src_file.seek(w.seg_pos)
            segment = src_file.read(w.seg_len)
        if len(segment) != w.seg_len:
            raise ValueError("source file is too short for this patch")
        out = decode_window(w, segment)
        out_file.write(out)
        h.update(out)
        done += len(out)
        if progress:
            progress(done, total)
    return h.hexdigest()


def file_sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while buf := f.read(WINDOW):
            h.update(buf)
    return h.hexdigest()


# --- commands ----------------------------------------------------------------

class Progress:
    def __init__(self, label):
        self.label, self.shown = label, 0
        print(label, end="", flush=True)

    def __call__(self, done, total):
        while total and self.shown < 10 * done // total:
            self.shown += 1
            print(" %d%%" % (self.shown * 10), end="", flush=True)

    def end(self):
        print()


def cmd_make(src, tgt, out):
    if os.path.abspath(out) in (os.path.abspath(src), os.path.abspath(tgt)):
        raise SystemExit("the output would overwrite an input")
    p = Progress("Comparing %s with %s:" % (os.path.basename(tgt), os.path.basename(src)))
    with cso.open_image(src) as fs, cso.open_image(tgt) as ft, open(out, "wb") as fo:
        s_sha, t_sha = encode(fs, ft, fo, p)
    p.end()
    print("%s: %d bytes" % (out, os.path.getsize(out)))
    print("  source SHA-1 %s%s" % (s_sha, "  (the Redump image)" if s_sha == REDUMP_SHA1 else
                                    "  (not the Redump image; players need this exact file)"))
    print("  target SHA-1 %s" % t_sha)
    print("  patch  SHA-1 %s" % file_sha1(out))


def cmd_apply(src, patch_path, out):
    if os.path.abspath(out) == os.path.abspath(src):
        raise SystemExit("the output would overwrite the source")
    with open(patch_path, "rb") as f:
        patch = f.read()
    p = Progress("Applying %s:" % os.path.basename(patch_path))
    with cso.open_image(src) as fs, open(out, "w+b") as fo:
        sha = decode(fs, patch, fo, p)
    p.end()
    print("%s: %d bytes, SHA-1 %s" % (out, os.path.getsize(out), sha))


def app_header_files(app):
    """[(name, BLAKE3 hex or None)] for the target and source in xdelta3's
    application header, "target/comp/source/comp"; xdelta3 3.2's armor
    mode (on by default) adds "#<64 hex digits>" to each name. Python has no
    BLAKE3, so the digests are shown, not checked."""
    if not app:
        return []
    text = app.decode("utf-8", "replace")
    parts = text.split("/")
    out = []
    for i in (0, 2):
        if i < len(parts) and parts[i]:
            name, _, digest = parts[i].rpartition("#")
            if not name or len(digest) != 64:
                name, digest = parts[i], None
            out.append((name, digest))
    return out


def cmd_info(patch_path):
    with open(patch_path, "rb") as f:
        patch = f.read()
    info, windows = parse(patch)
    total = sum(w.tgt_len for w in windows)
    adds = sum(len(w.data) for w in windows)
    print("%s: %d bytes, %d windows, target %d bytes, %d bytes of new data%s" % (
        patch_path, len(patch), len(windows), total, adds,
        ", secondary compression %s" % info["secondary"] if info["secondary"] else ""))
    for role, (name, digest) in zip(("target", "source"), app_header_files(info["app_header"])):
        print("  %s: %s%s" % (role, name, "  BLAKE3 %s" % digest if digest else ""))
    changed = [(w.seg_pos, len(w.data)) for w in windows if w.data]
    for pos, n in changed[:20]:
        print("  window at %#x: %d new bytes" % (pos, n))
    if len(changed) > 20:
        print("  ... %d more windows with new bytes" % (len(changed) - 20))


def cmd_roundtrip(src, tgt):
    with cso.open_image(src) as fs, cso.open_image(tgt) as ft:
        buf = io.BytesIO()
        s_sha, t_sha = encode(fs, ft, buf)
        out = io.BytesIO()
        fs.seek(0)
        o_sha = decode(fs, buf.getvalue(), out)
    info, windows = parse(buf.getvalue())
    print("%s -> %s: patch %d bytes, %d windows, %d new bytes; decoded %s" % (
        src, tgt, len(buf.getvalue()), len(windows), sum(len(w.data) for w in windows),
        "identical" if o_sha == t_sha else "DIFFERENT  !! decoded output does not match the target"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "make" and len(args) == 3:
            cmd_make(*args)
        elif cmd == "apply" and len(args) == 3:
            cmd_apply(*args)
        elif cmd == "info" and len(args) == 1:
            cmd_info(args[0])
        elif cmd == "roundtrip" and len(args) == 2:
            cmd_roundtrip(*args)
        else:
            print(__doc__)
            return 1
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
