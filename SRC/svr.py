# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""SVR / SVM / SVP texture reader and writer for Let's Make a Soccer Team! (PS2).

These are the Sega Ninja (PS2) texture formats:

    .SVR  one texture: optional GBIX chunk + PVRT chunk
    .SVM  texture archive: PVMH directory + one PVRT chunk per texture
    .SVP  external palette: PVPL chunk (for the 0x62-0x65 data formats)

Pixel/data format codes and the GS swizzle rule were confirmed against
SLES_541.51 (graphics::CalculateTextureImageSize, nvSetupSVRTexObj,
nvPrepareSVRTexImagePacket and its per-PSM table at 0x527620) - see
DOC/SVR_FORMAT.md.

`roundtrip` takes every file apart into its palette and linear levels
(split) and puts it together again (join, with swizzle the inverse of
unswizzle), then puts each texture's own picture back through the PNG
path; both must come out identical. `replace` writes a copy of a file
with one texture's picture changed. The picture must be the texture's own
size; the format, size, mip chain length and padding stay, so the file
keeps its length. A texture with its own palette gets a new palette built
from the picture (--palette keep matches the old one instead); one whose
palette is a .SVP is matched to that palette (--clut).

Usage:
    python svr.py info      <file | dir> ...
    python svr.py png       <file | dir> <out_dir> [--clut file.SVP]
    python svr.py roundtrip <file | dir> ...
    python svr.py replace   <in.SVR | in.SVM> <out> <picture.png>
                            [--texture <name | index>] [--clut file.SVP]
                            [--palette keep]

Requires: pip install pillow  (only for `png` and `replace`)
"""
import functools
import hashlib
import os
import struct
import sys

# --- GS local memory layout (PCSX2 GSTables) ---------------------------------

_BLOCK32 = [[0, 1, 4, 5, 16, 17, 20, 21], [2, 3, 6, 7, 18, 19, 22, 23],
            [8, 9, 12, 13, 24, 25, 28, 29], [10, 11, 14, 15, 26, 27, 30, 31]]
_BLOCK16 = [[0, 2, 8, 10], [1, 3, 9, 11], [4, 6, 12, 14], [5, 7, 13, 15],
            [16, 18, 24, 26], [17, 19, 25, 27], [20, 22, 28, 30], [21, 23, 29, 31]]
_COL32 = [[0, 1, 4, 5, 8, 9, 12, 13], [2, 3, 6, 7, 10, 11, 14, 15]]
_COL32 = [[v + 16 * k for v in row] for k in range(4) for row in _COL32]
_COL16 = [[0, 2, 8, 10, 16, 18, 24, 26, 1, 3, 9, 11, 17, 19, 25, 27],
          [4, 6, 12, 14, 20, 22, 28, 30, 5, 7, 13, 15, 21, 23, 29, 31]]
_COL16 = [[v + 32 * k for v in row] for k in range(4) for row in _COL16]
# PSMT8/PSMT4 columns: even columns use these rows; odd columns swap each
# pair of 4-pixel groups. Rows 8-15 repeat rows 0-7 one half-block later.
_c8 = [[0, 4, 16, 20, 32, 36, 48, 52, 2, 6, 18, 22, 34, 38, 50, 54],
       [8, 12, 24, 28, 40, 44, 56, 60, 10, 14, 26, 30, 42, 46, 58, 62],
       [33, 37, 49, 53, 1, 5, 17, 21, 35, 39, 51, 55, 3, 7, 19, 23],
       [41, 45, 57, 61, 9, 13, 25, 29, 43, 47, 59, 63, 11, 15, 27, 31]]
_COL8 = _c8 + [[r[i ^ 4] + 64 for i in range(16)] for r in _c8]
_COL8 = _COL8 + [[v + 128 for v in r] for r in _COL8]
_c4 = [[0, 8, 32, 40, 64, 72, 96, 104, 2, 10, 34, 42, 66, 74, 98, 106,
        4, 12, 36, 44, 68, 76, 100, 108, 6, 14, 38, 46, 70, 78, 102, 110],
       [16, 24, 48, 56, 80, 88, 112, 120, 18, 26, 50, 58, 82, 90, 114, 122,
        20, 28, 52, 60, 84, 92, 116, 124, 22, 30, 54, 62, 86, 94, 118, 126],
       [65, 73, 97, 105, 1, 9, 33, 41, 67, 75, 99, 107, 3, 11, 35, 43,
        69, 77, 101, 109, 5, 13, 37, 45, 71, 79, 103, 111, 7, 15, 39, 47],
       [81, 89, 113, 121, 17, 25, 49, 57, 83, 91, 115, 123, 19, 27, 51, 59,
        85, 93, 117, 125, 21, 29, 53, 61, 87, 95, 119, 127, 23, 31, 55, 63]]
_COL4 = _c4 + [[r[i ^ 4] + 128 for i in range(32)] for r in _c4]
_COL4 = _COL4 + [[v + 256 for v in r] for r in _COL4]


def _addr32(x, y, pw):  # word address; pw = pages per row
    return (((y >> 5) * pw + (x >> 6)) * 2048 + _BLOCK32[(y >> 3) & 3][(x >> 3) & 7] * 64
            + _COL32[y & 7][x & 7])


def _addr16(x, y, pw):  # halfword address
    return (((y >> 6) * pw + (x >> 6)) * 4096 + _BLOCK16[(y >> 3) & 7][(x >> 4) & 3] * 128
            + _COL16[y & 7][x & 15])


def _addr8(x, y, pw):  # byte address
    return (((y >> 6) * pw + (x >> 7)) * 8192 + _BLOCK32[(y >> 4) & 3][(x >> 4) & 7] * 256
            + _COL8[y & 15][x & 15])


def _addr4(x, y, pw):  # nibble address
    return (((y >> 7) * pw + (x >> 7)) * 16384 + _BLOCK16[(y >> 4) & 7][(x >> 5) & 3] * 512
            + _COL4[y & 15][x & 31])


# From the game's table at 0x527620: a level is uploaded as PSMCT32 (i.e.
# stored swizzled) only when it covers at least one GS page of its PSM.
# bpp -> (page_w, page_h, addr function, address units per byte)
_PAGE = {4: (128, 128, _addr4, 2), 8: (128, 64, _addr8, 1), 16: (64, 64, _addr16, 0.5)}


def is_swizzled(bpp, w, h):
    return bpp in _PAGE and w >= _PAGE[bpp][0] and h >= _PAGE[bpp][1]


@functools.lru_cache(maxsize=8)
def _permutation(bpp, w, h):
    """Where each pixel of a w x h level (row-major) sits in the CT32
    upload image, as an index in units of one pixel (a byte, a halfword or
    a nibble). Textures share a few sizes, so the table is kept."""
    pw_px, _, addr, _ = _PAGE[bpp]
    pw = w // pw_px
    cw = pw * 64  # CT32 upload width
    per_word = 32 // bpp
    word_of = {}
    for k in range(w * h * bpp // 32):
        word_of[_addr32(k % cw, k // cw, pw)] = k
    perm = []
    for y in range(h):
        for x in range(w):
            a = addr(x, y, pw)
            perm.append(word_of[a // per_word] * per_word + a % per_word)
    return perm


def _units(data, bpp):
    if bpp == 8:
        return data
    if bpp == 16:
        return struct.unpack("<%dH" % (len(data) // 2), data)
    return [(b >> s) & 15 for b in data for s in (0, 4)]  # low nibble first


def _bytes(units, bpp):
    if bpp == 8:
        return bytes(units)
    if bpp == 16:
        return struct.pack("<%dH" % len(units), *units)
    return bytes(lo | (hi << 4) for lo, hi in zip(units[0::2], units[1::2]))


def unswizzle(data, w, h, bpp):
    """Undo the PSMCT32 upload: `data` is a linear CT32 image of the same
    GS pages; return the texture as linear `bpp` pixels."""
    units = _units(data, bpp)
    return _bytes([units[j] for j in _permutation(bpp, w, h)], bpp)


def swizzle(data, w, h, bpp):
    """The inverse of unswizzle: linear `bpp` pixels -> the PSMCT32 image
    the game uploads (what the file stores for a level that fills a GS
    page of its PSM)."""
    units = _units(data, bpp)
    out = [0] * len(units)
    for i, j in enumerate(_permutation(bpp, w, h)):
        out[j] = units[i]
    return _bytes(out, bpp)


# --- formats -----------------------------------------------------------------

PIXEL_FORMATS = {0x08: "CT16 (ABGR1555)", 0x09: "CT32 (RGBA8888, A 0x80=1.0)"}

# data format -> (name, bits per pixel or None for "from pixel format", palette entries)
DATA_FORMATS = {
    0x60: ("direct", None, 0),
    0x61: ("direct+mips", None, 0),
    0x62: ("4bpp ext.clut", 4, 0),
    0x63: ("4bpp ext.clut+mips", 4, 0),
    0x64: ("8bpp ext.clut", 8, 0),
    0x65: ("8bpp ext.clut+mips", 8, 0),
    0x66: ("4bpp clut16", 4, 16),
    0x67: ("4bpp clut16+mips", 4, 16),
    0x68: ("4bpp clut32", 4, 16),
    0x69: ("4bpp clut32+mips", 4, 16),
    0x6A: ("8bpp clut16", 8, 256),
    0x6B: ("8bpp clut16+mips", 8, 256),
    0x6C: ("8bpp clut32", 8, 256),
    0x6D: ("8bpp clut32+mips", 8, 256),
}


def _pixel_bytes(pf):
    if pf == 0x08:
        return 2
    if pf == 0x09:
        return 4
    raise ValueError("unsupported pixel format %#x" % pf)


class Texture:
    def __init__(self, name, offset, pf, df, width, height, mip_field, body):
        self.name = name
        self.offset = offset        # of the PVRT chunk in its file
        self.pf = pf
        self.df = df
        self.width = width
        self.height = height
        self.mip_field = mip_field  # PVRT+0x0A; 0 in every file on this disc
        self.body = body            # chunk payload after the 16-byte PVRT header
        fmt_name, bpp, n_pal = DATA_FORMATS[df]
        self.fmt_name = fmt_name
        self.bpp = bpp or _pixel_bytes(pf) * 8
        self.palette_size = n_pal * _pixel_bytes(pf) if n_pal else 0
        self.palette_entries = n_pal
        # What a file keeps around the PVRT chunk, so a rebuilt file can match
        # the original: an SVR's GBIX chunk and trailing bytes; an SVM entry's
        # 38 header bytes and the zero bytes before its chunk.
        self.gbix = None
        self.head = b""
        self.trailer = b""
        self.entry = None
        self.lead = b""

    @property
    def has_mips(self):
        return self.df & 1 == 1

    def level_sizes(self):
        """Byte size of each level present (16-byte aligned, as the game
        steps through them). The level count isn't stored, so for mipmapped
        formats it's inferred from the chunk size."""
        avail = len(self.body) - self.palette_size
        sizes, w, h = [], self.width, self.height
        while w and h:
            n = (w * h * self.bpp // 8 + 15) & ~15
            if sizes and (not self.has_mips or n > avail):
                break
            sizes.append(n)
            avail -= n
            w, h = w >> 1, h >> 1
        return sizes

    def level_dims(self):
        """(width, height) of each level present, largest first."""
        return [(self.width >> k, self.height >> k) for k in range(len(self.level_sizes()))]

    def split(self):
        """(palette bytes, [each level as linear pixels], [each level's
        padding], tail): the body taken apart. A level is stored swizzled
        when it fills a GS page of its own size (is_swizzled), so a mipmap
        chain mixes both. The padding rounds a level up to 16 bytes and is
        not always zero (the last level of GAME/EF012.SVM has 8 bytes of
        something else), so it is kept. `tail` is whatever follows the last
        level (the chunk's padding)."""
        palette = self.body[:self.palette_size]
        levels, pads, off = [], [], self.palette_size
        for (w, h), size in zip(self.level_dims(), self.level_sizes()):
            n = w * h * self.bpp // 8
            raw = self.body[off:off + n]
            levels.append(unswizzle(raw, w, h, self.bpp) if is_swizzled(self.bpp, w, h) else raw)
            pads.append(self.body[off + n:off + size])
            off += size
        return palette, levels, pads, self.body[off:]

    def join(self, palette, levels, pads=None, tail=b""):
        """The body that split() takes apart: palette, then each level
        swizzled where the game wants it, then its padding (zeros unless
        `pads` gives it)."""
        out = bytearray(palette)
        for i, ((w, h), raw) in enumerate(zip(self.level_dims(), levels)):
            out += swizzle(raw, w, h, self.bpp) if is_swizzled(self.bpp, w, h) else raw
            out += pads[i] if pads else bytes(-len(raw) % 16)
        return bytes(out) + tail

    def palette(self, clut=None):
        """RGBA tuples; `clut` is a Palette (from a .SVP) for ext.clut formats."""
        if self.palette_entries:
            raw, pf, n = self.body[:self.palette_size], self.pf, self.palette_entries
        elif clut is not None:
            raw, pf, n = clut.data, clut.pf, clut.count
        else:
            return [(v, v, v, 255) for v in (range(0, 256, 17) if self.bpp == 4 else range(256))]
        pal = _decode_colors(raw, pf, n)
        if n == 256:
            # CSM1: the GS reads CLUT entries 8-15 and 16-23 of each 32 swapped.
            pal = [pal[(i & ~0x18) | ((i & 8) << 1) | ((i & 0x10) >> 1)] for i in range(256)]
        return pal

    def pixels(self, clut=None, level=0):
        """A level (0 is the full size) as a list of RGBA tuples, row-major."""
        bpp = self.bpp
        w, h = self.level_dims()[level]
        start = self.palette_size + sum(self.level_sizes()[:level])
        raw = self.body[start:start + w * h * bpp // 8]
        if is_swizzled(bpp, w, h):
            raw = unswizzle(raw, w, h, bpp)
        if bpp >= 16:
            return _decode_colors(raw, self.pf, w * h)
        pal = self.palette(clut)
        if bpp == 8:
            return [pal[b] for b in raw]
        out = []
        for b in raw:
            out.append(pal[b & 15])
            out.append(pal[b >> 4])
        return out


def _decode_colors(raw, pf, n):
    if pf == 0x08:
        out = []
        for v in struct.unpack_from("<%dH" % n, raw):
            r, g, b = v & 31, (v >> 5) & 31, (v >> 10) & 31
            out.append(((r << 3) | (r >> 2), (g << 3) | (g >> 2), (b << 3) | (b >> 2),
                        255 if v & 0x8000 else 0))
        return out
    if pf == 0x09:
        return [(raw[i], raw[i + 1], raw[i + 2], min(255, raw[i + 3] * 255 // 128))
                for i in range(0, n * 4, 4)]
    raise ValueError("unsupported pixel format %#x" % pf)


class Palette:
    def __init__(self, pf, count, data, fields=(0, 0), trailer=b""):
        self.pf, self.count, self.data = pf, count, data
        self.fields = fields        # the two u16 after the pixel format
        self.trailer = trailer


class Archive(list):
    """The textures of a PVMH archive. `head` is the file up to where the
    zero bytes before the first chunk begin, `tail` what follows the last
    chunk."""
    head = b""
    tail = b""


def parse_pvrt(buf, off, name=""):
    magic, length, pf, df, mip, w, h = struct.unpack_from("<4sIBBHHH", buf, off)
    if magic != b"PVRT":
        raise ValueError("no PVRT chunk at %#x" % off)
    return Texture(name, off, pf, df, w, h, mip, buf[off + 16:off + 8 + length]), off + 8 + length


def parse_svr(buf, name=""):
    off, gbix = 0, None
    if buf[:4] == b"GBIX":
        length = struct.unpack_from("<I", buf, 4)[0]
        gbix = struct.unpack_from("<I", buf, 8)[0]
        off = 8 + length
    tex, end = parse_pvrt(buf, off, name)
    tex.gbix = gbix
    tex.head = buf[:off]
    tex.trailer = buf[end:]
    return tex


def parse_svm(buf):
    """Return the texture list of a PVMH archive."""
    magic, hdr_len, flags, count = struct.unpack_from("<4sIHH", buf, 0)
    if magic != b"PVMH":
        raise ValueError("not a PVMH archive")
    if flags & 0xFF != 0x0F:
        raise ValueError("unsupported PVMH flags %#x" % flags)
    entries, o = [], 12
    for _ in range(count):
        idx, = struct.unpack_from("<H", buf, o)
        name = buf[o + 2:o + 30].split(b"\0")[0].decode("latin1")
        fmt, dims, gbix = struct.unpack_from("<HHI", buf, o + 30)
        entries.append((idx, name, fmt, dims, gbix, buf[o:o + 38]))
        o += 38
    texs, off = Archive(), 8 + hdr_len
    texs.head = buf[:off]
    for idx, name, fmt, dims, gbix, entry in entries:
        start = off
        while buf[off:off + 4] == b"\0\0\0\0":  # chunks are 16-byte aligned
            off += 4
        tex, end = parse_pvrt(buf, off, name)
        tex.gbix = gbix
        tex.entry = entry
        tex.lead = buf[start:off]
        texs.append(tex)
        off = end
    texs.tail = buf[off:]
    return texs


def parse_svp(buf):
    magic, length, pf, a, b, count = struct.unpack_from("<4sIHHHH", buf, 0)
    if magic != b"PVPL":
        raise ValueError("not a PVPL palette")
    return Palette(pf, count, buf[16:8 + length], (a, b), buf[8 + length:])


# --- writing ------------------------------------------------------------------

def encode_pvrt(tex, body=None):
    """The PVRT chunk: its 16-byte header, then `body` (default: the one the
    texture was read with)."""
    body = tex.body if body is None else body
    return struct.pack("<4sIBBHHH", b"PVRT", len(body) + 8, tex.pf, tex.df, tex.mip_field,
                       tex.width, tex.height) + body


def encode_svr(tex, body=None):
    """An SVR file: the GBIX chunk it was read with (or a new one for a
    texture that has a global index and no chunk), the PVRT chunk, and any
    bytes that followed it."""
    head = tex.head
    if not head and tex.gbix is not None:
        head = struct.pack("<4sIII", b"GBIX", 8, tex.gbix, 0)
    return head + encode_pvrt(tex, body) + tex.trailer


def encode_svm(texs, bodies=None):
    """A PVMH archive from the textures parse_svm returned (their entries,
    padding and chunks as read); `bodies` replaces the bodies of those that
    changed, by position."""
    out = bytearray(texs.head)
    for i, tex in enumerate(texs):
        out += tex.lead + encode_pvrt(tex, bodies[i] if bodies else None)
    return bytes(out) + texs.tail


def encode_svp(pal):
    return struct.pack("<4sIHHHH", b"PVPL", len(pal.data) + 8, pal.pf, *pal.fields,
                       pal.count) + pal.data + pal.trailer


def encode_colors(pixels, pf):
    """RGBA tuples -> CT16 or CT32 bytes, the inverse of _decode_colors up
    to what it drops: CT16 keeps 5 bits a channel and a 1-bit alpha, CT32
    alpha runs 0 to 0x80."""
    out = bytearray()
    if pf == 0x08:
        for r, g, b, a in pixels:
            out += struct.pack("<H", (r >> 3) | ((g >> 3) << 5) | ((b >> 3) << 10)
                               | (0x8000 if a >= 128 else 0))
        return bytes(out)
    if pf == 0x09:
        for r, g, b, a in pixels:
            out += bytes((r, g, b, (a * 128 + 127) // 255))
        return bytes(out)
    raise ValueError("unsupported pixel format %#x" % pf)


def encode_palette(colors, pf):
    """A palette's RGBA entries in storage order: 256 entries have bits 3
    and 4 of the index swapped (CSM1), the same swap Texture.palette undoes."""
    if len(colors) == 256:
        colors = [colors[(i & ~0x18) | ((i & 8) << 1) | ((i & 0x10) >> 1)] for i in range(256)]
    return encode_colors(colors, pf)


def half(pixels, w, h):
    """A level's RGBA pixels at half the width and height, each the average
    of a 2x2 block."""
    out = []
    for y in range(h >> 1):
        top, bottom = pixels[2 * y * w:(2 * y + 1) * w], pixels[(2 * y + 1) * w:(2 * y + 2) * w]
        for x in range(w >> 1):
            q = (top[2 * x], top[2 * x + 1], bottom[2 * x], bottom[2 * x + 1])
            out.append(tuple((q[0][c] + q[1][c] + q[2][c] + q[3][c] + 2) >> 2 for c in range(4)))
    return out


def colour_distance(p, q):
    """How far apart two RGBA colours look: the colour difference counts
    only as far as both are visible (a fully transparent pixel matches any
    transparent entry whatever its RGB), and a difference in alpha counts
    as much as the largest colour difference."""
    rgb = (p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2
    return rgb * p[3] * q[3] // 65025 + 3 * (p[3] - q[3]) ** 2


def nearest(pixels, palette):
    """The palette index of each pixel: the same colour if the palette has
    it, else the closest by colour_distance."""
    exact = {}
    for i, c in enumerate(palette):
        exact.setdefault(tuple(c), i)
    seen = {}
    out = []
    for p in pixels:
        i = seen.get(p)
        if i is None:
            i = exact.get(p)
            if i is None:
                i = min(range(len(palette)), key=lambda j: colour_distance(p, palette[j]))
            seen[p] = i
        out.append(i)
    return out


def pack_indices(indices, bpp):
    if bpp == 8:
        return bytes(indices)
    padded = list(indices) + [0] * (len(indices) & 1)
    return bytes(padded[i] | (padded[i + 1] << 4) for i in range(0, len(padded), 2))


def build_palette(pixels, size):
    """`size` colours that stand for `pixels`: each colour of the picture
    when there are no more than `size` (the RGB of a transparent pixel is
    kept: bilinear filtering blends it into its neighbours), else an octree
    quantisation (needs pillow) of the visible pixels plus one transparent
    entry, the most common transparent colour, so the quantiser can't
    blend transparency away. Unused entries are transparent black."""
    colors = list(dict.fromkeys(pixels))
    if len(colors) > size:
        visible = [p for p in pixels if p[3] != 0]
        clear = [p for p in pixels if p[3] == 0]
        room = size - bool(clear)
        from PIL import Image
        img = Image.new("RGBA", (len(visible), 1))
        img.putdata(visible)
        flat = img.quantize(colors=room, method=Image.Quantize.FASTOCTREE).getpalette("RGBA")
        colors = [tuple(flat[4 * i:4 * i + 4]) for i in range(len(flat) // 4)][:room]
        if clear:
            colors.insert(0, max(set(clear), key=clear.count))
    return colors + [(0, 0, 0, 0)] * (size - len(colors))


def body_from_pixels(tex, pixels, clut=None, new_palette=False):
    """The body of `tex` with `pixels` (RGBA, width x height, row-major) as
    its picture. Mip levels are made by halving; the format, size and
    padding stay, so the file keeps its length. A 4 or 8 bpp texture is
    matched to its palette (the .SVP's `clut` for the ext.clut formats), or
    with new_palette to a new one built from the picture, which only a
    texture that holds its own palette can have."""
    if len(pixels) != tex.width * tex.height:
        raise ValueError("%d pixels, but the texture is %dx%d" % (
            len(pixels), tex.width, tex.height))
    old_palette, _, pads, tail = tex.split()
    dims = tex.level_dims()
    images = [pixels]
    for k in range(1, len(dims)):
        images.append(half(images[-1], *dims[k - 1]))
    if tex.bpp >= 16:
        return tex.join(b"", [encode_colors(p, tex.pf) for p in images], pads, tail)
    if new_palette:
        if not tex.palette_entries:
            raise ValueError("this texture's palette is in a .SVP; it can't take a new one")
        colors = build_palette(pixels, tex.palette_entries)
        palette_bytes = encode_palette(colors, tex.pf)
    else:
        colors, palette_bytes = tex.palette(clut), old_palette
    levels = [pack_indices(nearest(p, colors), tex.bpp) for p in images]
    return tex.join(palette_bytes, levels, pads, tail)


def rebuild(buf):
    """A texture file taken apart into palette and linear levels (split) and
    put together again (join), which is exactly what a texture edit does
    with different levels. Equal to `buf` when the layout is understood."""
    if buf[:4] == b"PVPL":
        return encode_svp(parse_svp(buf))
    if buf[:4] == b"PVMH":
        texs = parse_svm(buf)
        return encode_svm(texs, [t.join(*t.split()) for t in texs])
    tex = parse_svr(buf)
    return encode_svr(tex, tex.join(*tex.split()))


def load(path):
    """Return a list of Textures (SVR -> 1, SVM -> n)."""
    with open(path, "rb") as f:
        buf = f.read()
    base = os.path.splitext(os.path.basename(path))[0]
    if buf[:4] == b"PVMH":
        return parse_svm(buf)
    return [parse_svr(buf, base)]


# --- CLI ---------------------------------------------------------------------

def _iter_paths(args, exts):
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for name in sorted(files):
                    if os.path.splitext(name)[1].upper() in exts:
                        yield os.path.join(root, name)
        else:
            yield a


def cmd_info(paths):
    for path in _iter_paths(paths, (".SVR", ".SVM", ".SVP")):
        with open(path, "rb") as f:
            buf = f.read()
        try:
            if buf[:4] == b"PVPL":
                p = parse_svp(buf)
                print("%s  PVPL %s x%d" % (path, PIXEL_FORMATS.get(p.pf, hex(p.pf)), p.count))
                continue
            texs = load(path)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            continue
        print("%s  %d texture(s)" % (path, len(texs)))
        for t in texs:
            print("  %-24s %4dx%-4d pf=%#04x df=%#04x %-20s levels=%d%s%s" % (
                t.name, t.width, t.height, t.pf, t.df, t.fmt_name, len(t.level_sizes()),
                "  swizzled" if is_swizzled(t.bpp, t.width, t.height) else "",
                "  gbix=%d" % t.gbix if t.gbix is not None else ""))


def first_difference(a, b):
    n = min(len(a), len(b))
    return next((i for i in range(n) if a[i] != b[i]), n)


# --- the textures on the disc ---------------------------------------------------

TEXTURE_MAGICS = (b"GBIX", b"PVMH", b"PVPL")
BIG_FILE = 200 << 20    # the 1.2 GB face pack takes minutes to expand; `roundtrip --all` includes it


def blobs_in(label, data, name=""):
    """(label, bytes) of each texture file in `data`: the data itself if it
    is one, else what it holds through PRSH compression, BINPAC packs and
    CSP packs (recognised by an entry or file name ending in .csp)."""
    import pac
    head = data[:4]
    if head in TEXTURE_MAGICS:
        yield label, data
    elif head == pac.PRSH_MAGIC:
        yield from blobs_in(label + "|prs", pac.prsh_expand(data), name)
    elif data[10:16] == b"BINPAC" and not name.lower().endswith(".hed"):  # .hed: header copy
        header, blobs = pac.binpac_blobs(data)
        for i, (entry, blob) in enumerate(zip(header.entries, blobs)):
            yield from blobs_in("%s#%d:%s" % (label, i, entry[2]), blob, entry[2])
    elif name.lower().endswith(".csp") and data:
        import csp
        for i, (off, size, kind) in enumerate(csp.parse_csp(data)):
            if kind == csp.TYPE_SVR:
                yield from blobs_in("%s#%d" % (label, i), data[off:off + size])


def _acrobata_blobs(label, data):
    """The textures in the ABRS part of each ACROBATA scene."""
    import acrobata
    import pac
    header, blobs = pac.binpac_blobs(data)
    for i, (entry, blob) in enumerate(zip(header.entries, blobs)):
        for magic, off, size in acrobata.resources(blob, entry[3][0]):
            if magic in TEXTURE_MAGICS:
                yield "%s#%d:%s+%#x" % (label, i, entry[2], off), blob[off:off + size]


def _packdata_blobs(label, path, everything, skipped):
    """The PVMH and PVPL blocks of each PackData in a KC@P pack."""
    import pac
    import packdata
    header = pac.load_header(path)
    data_file = pac.data_path(path, header)
    if data_file is None:
        raise ValueError("no data file next to this header")
    if os.path.getsize(data_file) > BIG_FILE and not everything:
        skipped.append("%s  skipped, %d MB (--all includes it)" % (
            label, os.path.getsize(data_file) >> 20))
        return
    with open(data_file, "rb") as f:
        for i, (off, size, _, _) in enumerate(header.entries):
            buf = packdata.read_entry(f, off, size)
            for k, (_, bsize, boff) in enumerate(packdata.PackData(buf).blocks):
                if buf[boff:boff + 4] in (b"PVMH", b"PVPL"):
                    yield "%s#%d.%d" % (label, i, k), buf[boff:boff + bsize]


def texture_files(paths, everything=False, skipped=None):
    """(label, bytes) of every texture file under `paths`, whatever holds
    it: loose files (by their first bytes, not their extension), BINPAC
    packs and MRGs, CSP packs, the ACROBATA pack and KC@P PackData packs.
    A file that can't be read gives (label, the exception). Files too big
    to expand quickly are added to `skipped` unless `everything`."""
    import pac
    skipped = [] if skipped is None else skipped
    for path in pac._walk(paths):
        label = path.replace("\\", "/")
        name = os.path.basename(path).upper()
        try:
            with open(path, "rb") as f:
                head = f.read(16)
            if head[:4] in TEXTURE_MAGICS or head[:4] == pac.PRSH_MAGIC:
                yield from blobs_in(label, open(path, "rb").read())
            elif head[:4] == pac.KCAP_MAGIC:
                yield from _packdata_blobs(label, path, everything, skipped)
            elif head[10:16] == b"BINPAC" and not name.endswith(".HED"):  # .HED: a pack's header copy
                data = open(path, "rb").read()
                yield from (_acrobata_blobs(label, data) if name == "ACROBATAPACKFILE.PAC"
                            else blobs_in(label, data))
            elif name.endswith(".CSP"):
                yield from blobs_in(label, open(path, "rb").read(), name)
        except (ValueError, struct.error, KeyError, IndexError, OSError) as e:
            yield label, e


def pictures_survive(tex):
    """Put level 0 back as a picture (body_from_pixels, matching the
    texture's own palette) and decode again: is it the same picture, and
    does the body keep its length?"""
    pixels = tex.pixels()
    body = body_from_pixels(tex, pixels)
    again, _ = parse_pvrt(encode_pvrt(tex, body), 0)
    return len(body) == len(tex.body) and again.pixels() == pixels


def textures_of(buf, name=""):
    if buf[:4] == b"PVPL":
        return []
    return parse_svm(buf) if buf[:4] == b"PVMH" else [parse_svr(buf, name)]


def cmd_roundtrip(paths, everything=False):
    """Rebuild every texture file under `paths` (loose, or inside any pack
    texture_files opens) from its palette and linear levels and compare it
    with the original, then put every texture's picture back through
    body_from_pixels; a difference is marked `!!`. Copies of one file in
    several packs (the language copies) are checked once."""
    seen = set()
    found = distinct = textures = palettes = bad = bad_pictures = 0
    skipped = []
    for label, blob in texture_files(paths, everything, skipped):
        if isinstance(blob, Exception):
            print("%s  !! %s: %s" % (label, type(blob).__name__, blob))
            bad += 1
            continue
        found += 1
        key = hashlib.sha1(blob).digest()
        if key in seen:
            continue
        seen.add(key)
        distinct += 1
        try:
            out = rebuild(blob)
            texs = textures_of(blob, label)
            lost = [t.name or "(unnamed)" for t in texs if not pictures_survive(t)]
        except (ValueError, struct.error, KeyError, IndexError) as e:
            print("%s  !! %s: %s" % (label, type(e).__name__, e))
            bad += 1
            continue
        textures += len(texs)
        palettes += blob[:4] == b"PVPL"
        if out != blob:
            print("%s  !! rebuilt file differs at %#x (%d bytes, was %d)" % (
                label, first_difference(out, blob), len(out), len(blob)))
            bad += 1
        if lost:
            print("%s  !! picture changes when put back: %s" % (label, ", ".join(lost)))
            bad_pictures += len(lost)
    for note in skipped:
        print(note)
    print("%d texture files, %d distinct (%d textures, %d palettes): %d not identical, "
          "%d pictures changed" % (found, distinct, textures, palettes, bad, bad_pictures))


def cmd_replace(path, out_path, image_path, which=None, clut_path=None, keep_palette=False):
    """Write a copy of an SVR, or of an SVM with the texture `which` (a
    name or index) replaced, with the picture in `image_path`."""
    from PIL import Image
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(path, "rb") as f:
        buf = f.read()
    if buf[:4] == b"PVMH":
        texs = parse_svm(buf)
        if which is None and len(texs) == 1:
            which = "0"
        names = [t.name for t in texs]
        i = names.index(which) if which in names else int(which) if which is not None else -1
        if not 0 <= i < len(texs):
            raise SystemExit("name or index of the texture to replace; this file has: %s" %
                             ", ".join("%d %s" % x for x in enumerate(names)))
        tex = texs[i]
    else:
        texs, i, tex = None, 0, parse_svr(buf)
    clut = None
    if clut_path:
        with open(clut_path, "rb") as f:
            clut = parse_svp(f.read())
    img = Image.open(image_path).convert("RGBA")
    if img.size != (tex.width, tex.height):
        raise SystemExit("the picture is %dx%d, the texture %dx%d; scale it first" % (
            img.width, img.height, tex.width, tex.height))
    # A texture with its own palette gets one built from the picture; an
    # ext.clut texture's palette is a shared .SVP, so the picture is matched to it.
    body = body_from_pixels(tex, list(img.getdata()), clut,
                            new_palette=bool(tex.palette_entries) and not keep_palette)
    out = encode_svm(texs, [body if k == i else None for k in range(len(texs))]) if texs \
        else encode_svr(tex, body)
    if len(out) != len(buf):
        raise SystemExit("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s (%s %dx%d, %s)" % (out_path, tex.name or "texture", tex.width, tex.height,
                                       tex.fmt_name))


def cmd_png(paths, out_dir, clut_path=None):
    from PIL import Image
    clut = None
    if clut_path:
        with open(clut_path, "rb") as f:
            clut = parse_svp(f.read())
    os.makedirs(out_dir, exist_ok=True)
    for path in _iter_paths(paths, (".SVR", ".SVM")):
        base = os.path.splitext(os.path.basename(path))[0]
        texs = load(path)
        for i, t in enumerate(texs):
            img = Image.new("RGBA", (t.width, t.height))
            img.putdata(t.pixels(clut))
            name = base if len(texs) == 1 else "%s_%02d_%s" % (base, i, t.name)
            out = os.path.join(out_dir, name + ".png")
            img.save(out)
            print(out)


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args)
    elif cmd == "roundtrip":
        cmd_roundtrip([a for a in args if a != "--all"], "--all" in args)
    elif cmd == "replace" and len(args) >= 3:
        options = {}
        for flag in ("--texture", "--clut", "--palette"):
            if flag in args:
                i = args.index(flag)
                options[flag] = args[i + 1]
                args = args[:i] + args[i + 2:]
        if len(args) != 3 or options.get("--palette", "keep") not in ("keep", "new"):
            print(__doc__)
            return 1
        cmd_replace(args[0], args[1], args[2], options.get("--texture"), options.get("--clut"),
                    options.get("--palette") == "keep")
    elif cmd == "png" and len(args) >= 2:
        clut = None
        if "--clut" in args:
            i = args.index("--clut")
            clut = args[i + 1]
            args = args[:i] + args[i + 2:]
        cmd_png(args[:-1], args[-1], clut)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
