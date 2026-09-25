"""SVR / SVM / SVP texture reader for Let's Make a Soccer Team! (PS2).

These are the Sega Ninja (PS2) texture formats:

    .SVR  one texture: optional GBIX chunk + PVRT chunk
    .SVM  texture archive: PVMH directory + one PVRT chunk per texture
    .SVP  external palette: PVPL chunk (for the 0x62-0x65 data formats)

Pixel/data format codes and the GS swizzle rule were confirmed against
SLES_541.51 (graphics::CalculateTextureImageSize, nvSetupSVRTexObj,
nvPrepareSVRTexImagePacket and its per-PSM table at 0x527620) - see
DOC/SVR_FORMAT.md.

Usage:
    python svr.py info <file | dir> ...
    python svr.py png  <file | dir> <out_dir> [--clut file.SVP]

Requires: pip install pillow  (only for `png`)
"""
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


def unswizzle(data, w, h, bpp):
    """Undo the PSMCT32 upload: `data` is a linear CT32 image of the same
    GS pages; return the texture as linear `bpp` pixels."""
    pw_px, _, addr, _ = _PAGE[bpp]
    pw = w // pw_px
    cw = pw * 64  # CT32 upload width
    word_of = {}
    for k in range(len(data) // 4):
        word_of[_addr32(k % cw, k // cw, pw)] = k
    out = bytearray(len(data))
    if bpp == 8:
        for y in range(h):
            for x in range(w):
                a = addr(x, y, pw)
                out[y * w + x] = data[word_of[a >> 2] * 4 + (a & 3)]
    elif bpp == 16:
        for y in range(h):
            for x in range(w):
                a = addr(x, y, pw)
                s = word_of[a >> 1] * 4 + (a & 1) * 2
                i = (y * w + x) * 2
                out[i:i + 2] = data[s:s + 2]
    else:
        for y in range(h):
            for x in range(w):
                a = addr(x, y, pw)
                b = data[word_of[a >> 3] * 4 + ((a >> 1) & 3)]
                v = (b >> 4) if a & 1 else (b & 15)
                i = y * w + x
                out[i >> 1] |= v << (4 if i & 1 else 0)
    return bytes(out)


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

    def pixels(self, clut=None):
        """Level 0 as a list of RGBA tuples, row-major."""
        w, h, bpp = self.width, self.height, self.bpp
        start = self.palette_size
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
    def __init__(self, pf, count, data):
        self.pf, self.count, self.data = pf, count, data


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
    tex, _ = parse_pvrt(buf, off, name)
    tex.gbix = gbix
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
        entries.append((idx, name, fmt, dims, gbix))
        o += 38
    texs, off = [], 8 + hdr_len
    for idx, name, fmt, dims, gbix in entries:
        while buf[off:off + 4] == b"\0\0\0\0":  # chunks are 16-byte aligned
            off += 4
        tex, off = parse_pvrt(buf, off, name)
        tex.gbix = gbix
        texs.append(tex)
    return texs


def parse_svp(buf):
    magic, length, pf, _, _, count = struct.unpack_from("<4sIHHHH", buf, 0)
    if magic != b"PVPL":
        raise ValueError("not a PVPL palette")
    return Palette(pf, count, buf[16:8 + length])


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
