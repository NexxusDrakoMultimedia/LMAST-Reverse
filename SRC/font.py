# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Bitmap fonts of Let's Make a Soccer Team! (PS2): the glyph tables in the
executable and the atlas pictures in DAT/0SYSTEM they point into.
See DOC/FONT_FORMAT.md.

The European text is drawn from three atlases (FONT_20_A, FONT_8_A,
FONT_8_B) by sbFontPuts (0x3123c0). The pictures hold only pixels: the
rectangle of every glyph, its advance width, the font's height and the
character list live in the executable.

  descriptor  12 bytes {u32 table, f32 space advance, u32 height}, three of
              them, reached through the pointer array DESCRIPTORS
              (sbFontSet1ByteFont 0x312198 copies it into the font;
              CFont_fc_euro::SetTexList 0x303c28 passes the array's items)
  record      20 bytes, five floats {u0, v0, u1, v1, advance}; the UVs are
              normalised (pixel / texture size). The record of glyph code c
              is at table + (c - 4) * 20 (sbFontPuts 0x31262c-0x312638; the
              advance is read at -0x40 by 0x312028)
  list        u16 per glyph, a cp850 byte; pointer array LISTS, counts
              COUNTS. sbFontSetDefault (0x312220) builds the 256-byte map
              byte -> glyph code (list index + 4; 0x20 -> 3, 0x0a -> 2;
              a later duplicate wins) that sbFontConvrtAsciiString
              (0x3131b8) applies
  quad        (x, y) to (x + advance * zoom, y + height * zoom); the next
              glyph starts advance * zoom + tracking further on

The Japanese language draws its text from three 2-byte fonts instead
(sbFontSet2BytesFont 0x3121c0; the same code is in the PAL executable):
FONT_ASCII (11 x 26 cells), and the two planes of FONT_KANJI (20 x 26
cells, plane A through the picture's palette, plane B through the 16 bytes
CLUT_B in the executable). A cell's index is the position of its Shift-JIS
code in CODE_TABLES (CFont_fc_euro::SetTexList 0x303c28).

`info` checks every record against its atlas (whole-pixel edges, advance =
width, height, white ink, and how much ink lies inside a rectangle), the
character lists, and the three 2-byte code tables against their pictures.
`coverage` checks every text byte of the six European languages against
font 0.

Usage:
    python font.py info     <executable> <DAT/0SYSTEM>
    python font.py dump     <executable> <font 0-2> [out.csv]
    python font.py png      <executable> <DAT/0SYSTEM> <font 0-2> <out.png>
    python font.py coverage <executable> <DAT/MESSAGE/MES.PAC>
"""
import os
import struct
import sys

import gamever
import sles_disasm
import svr

# Addresses in the PAL executable; gamever.at finds them in another build.
DESCRIPTORS = 0x3a76b8      # u32 x 3: the font descriptors
LISTS = 0x3a76c8            # u32 x 3: the character lists
COUNTS = 0x566838           # u32 x 3: the glyph counts
CODE_TABLES = (0x561ca8, 0x561e18, 0x562da8)   # Shift-JIS codes, 2 bytes each
CLUT_B = 0x563950           # FONT_KANJI plane B's palette, 16 x RGBA
CELL_SIZES = 0x3a7260       # u8 {width, height} of FONT_ASCII; +8 FONT_KANJI

EURO = ("FONT_20_A", "FONT_8_A", "FONT_8_B")
GLYPH_BASE = 4              # glyph code of the first record
ZEN_COUNTS = (184, 1989, 1485)   # T0, T1, T2 (SetTexList 0x303d3c, 0x303eb0)
RECORD = struct.Struct("<5f")
EDGE = 0.01                 # how far from a whole pixel an edge may be


class Exe:
    """An executable of either build."""

    def __init__(self, path):
        self.path = path
        self.elf = sles_disasm.Elf(path)
        self.data = self.elf.data

    def va(self, addr):
        """File offset of an address in this build."""
        off = self.elf.v2f(addr)
        if off is None:
            raise ValueError("%s: no data at %#x" % (os.path.basename(self.path), addr))
        return off

    def here(self, pal_addr, size=0x40):
        """File offset of a PAL address's counterpart in this build."""
        return self.va(gamever.at(self.path, pal_addr, size))

    def u32(self, off):
        return struct.unpack_from("<I", self.data, off)[0]


class Euro:
    """One of the three European fonts."""

    def __init__(self, exe, i):
        self.index, self.name = i, EURO[i]
        self.descriptor = exe.u32(exe.here(DESCRIPTORS, 0xc) + 4 * i)
        self.table, self.space, height = struct.unpack_from(
            "<IfI", exe.data, exe.va(self.descriptor))
        self.height = height & 0xff
        self.list_addr = exe.u32(exe.here(LISTS, 0xc) + 4 * i)
        n = exe.u32(exe.here(COUNTS, 0xc) + 4 * i)
        self.chars = list(struct.unpack_from("<%dH" % n, exe.data, exe.va(self.list_addr)))
        base = exe.va(self.table)
        self.records = [RECORD.unpack_from(exe.data, base + 20 * k) for k in range(n)]

    def remap(self):
        """byte -> glyph code (0: none), as sbFontSetDefault builds it."""
        m = [0] * 256
        for k, c in enumerate(self.chars):
            if c < 0x100:
                m[c] = k + GLYPH_BASE
        m[0x20], m[0x0a] = 3, 2
        return m

    def duplicates(self):
        seen, dup = set(), set()
        for c in self.chars:
            (dup if c in seen else seen).add(c)
        return sorted(dup)


def load_texture(zero_dir, name):
    return svr.load(os.path.join(zero_dir, name + ".SVR"))[0]


def ink_mask(tex):
    """1 where a pixel is not transparent, row-major."""
    return bytearray(1 if p[3] else 0 for p in tex.pixels())


def rect_px(rec, w, h):
    u0, v0, u1, v1, _ = rec
    return u0 * w, v0 * h, u1 * w, v1 * h


def near(x):
    return abs(x - round(x)) <= EDGE


def check_euro(exe, zero_dir, i):
    """The lines `info` prints for one European font."""
    f = Euro(exe, i)
    tex = load_texture(zero_dir, f.name)
    w, h = tex.width, tex.height
    ink = ink_mask(tex)
    covered = bytearray(w * h)
    problems = []
    whole = widths = tall = past = empty = 0
    for k, rec in enumerate(f.records):
        x0, y0, x1, y1 = rect_px(rec, w, h)
        if rec[0] >= rec[2] or rec[1] >= rec[3]:
            problems.append("record %d has an empty or reversed rectangle" % k)
            continue
        whole += all(near(v) for v in (x0, y0, x1, y1))
        widths += abs(rec[4] - (x1 - x0)) <= EDGE
        xa, xb = max(0, round(x0)), min(w, round(x1))
        ya, yb = max(0, round(y0)), min(h, round(y1))
        if x0 < -EDGE or y0 < -EDGE or x1 > w + 1 + EDGE or y1 > h + 1 + EDGE:
            problems.append("record %d lies outside the %dx%d texture" % (k, w, h))
        if x1 > w + EDGE or y1 > h + EDGE:
            past += 1
        has_ink = False
        for y in range(ya, yb):
            row = y * w
            covered[row + xa:row + xb] = b"\x01" * (xb - xa)
            has_ink = has_ink or any(ink[row + xa:row + xb])
        empty += not has_ink
        if round(y1 - y0) == f.height:
            tall += 1
        elif has_ink:
            problems.append("record %d is %d tall, not %d, and has ink" % (k, round(y1 - y0), f.height))
    n = len(f.records)
    uncovered = sum(1 for p in range(w * h) if ink[p] and not covered[p])
    inked = sum(ink)
    not_white = sum(1 for p in tex.pixels() if p[3] and p[:3] != (255, 255, 255))
    if whole != n:
        problems.append("%d of %d records have an edge off the pixel grid" % (n - whole, n))
    if widths != n:
        problems.append("%d of %d advances differ from the rectangle's width" % (n - widths, n))
    if not_white:
        problems.append("%d inked pixels are not white" % not_white)
    if any(c >= 0x100 for c in f.chars):
        problems.append("the character list has codes of 0x100 or more")
    m = f.remap()
    unmapped = [b for b in range(GLYPH_BASE, 256) if not m[b]]
    out = ["font %d  %-9s %dx%d  %d glyphs  height %d  space %.1f  table %#x  list %#x"
           % (i, f.name, w, h, n, f.height, f.space, f.table, f.list_addr),
           "  records: %d of %d on whole pixels, %d of %d advances = width, %d as tall as the font, "
           "%d past the texture edge, %d without ink; ink %d of %d inside a rectangle%s"
           % (whole, n, widths, n, tall, past, empty, inked - uncovered, inked,
              "" if not uncovered else " (%d pixels are left-over art no record reaches)" % uncovered),
           "  bytes: %d drawn, %d of %#x..0xff have no glyph; repeated in the list: %s"
           % (sum(1 for b in range(256) if m[b]), len(unmapped), GLYPH_BASE,
              " ".join("%#04x" % b for b in f.duplicates()) or "none")]
    out += ["  !! " + p for p in problems]
    return out


# --- the 2-byte fonts ---------------------------------------------------------

def read_codes(exe, addr, n):
    off = exe.here(addr)
    d = exe.data
    return [d[off + 2 * k] << 8 | d[off + 2 * k + 1] for k in range(n)]


def cell_ink(mask, w, cw, ch, cols, rows):
    """The cell indices that have an inked pixel."""
    out = set()
    for n in range(cols * rows):
        x0, y0 = (n % cols) * cw, (n // cols) * ch
        for y in range(y0, y0 + ch):
            if any(mask[y * w + x0:y * w + x0 + cw]):
                out.add(n)
                break
    return out


def outside_grid(mask, w, h, cw, ch, cols, rows):
    gx, gy = cols * cw, rows * ch
    return sum(1 for y in range(h) for x in range(w)
               if mask[y * w + x] and (x >= gx or y >= gy))


def check_zen(exe, zero_dir):
    """The lines `info` prints for the three 2-byte fonts."""
    d = exe.data
    cells = exe.here(CELL_SIZES, 0x10)
    t0, t1, t2 = (read_codes(exe, a, n) for a, n in zip(CODE_TABLES, ZEN_COUNTS))
    out, problems = [], []
    for label, t in (("T1", t1), ("T2", t2)):
        if any(a >= b for a, b in zip(t, t[1:])):
            problems.append("%s is not strictly ascending" % label)
    if t1[-1] >= t2[0]:
        problems.append("T1 does not end below T2's first code")
    if len(set(t0)) != len(t0):
        problems.append("T0 repeats a code")

    # FONT_ASCII: cell i draws T0[i].
    cw, ch = d[cells], d[cells + 1]
    tex = load_texture(zero_dir, "FONT_ASCII")
    w, h = tex.width, tex.height
    cols, rows = w // cw, h // ch
    mask = ink_mask(tex)
    inked = cell_ink(mask, w, cw, ch, cols, rows)
    stray = outside_grid(mask, w, h, cw, ch, cols, rows)
    blank = [n for n in range(1, len(t0)) if n not in inked]
    beyond = sorted(n for n in inked if n >= len(t0))
    out.append("zen font 0  FONT_ASCII  %dx%d  cells %dx%d, %d x %d  %d codes in T0  "
               "%d of %d cells after the space have ink; ink outside the grid %d"
               % (w, h, cw, ch, cols, rows, len(t0), len(inked - {0}), len(t0) - 1, stray))
    if blank:
        problems.append("FONT_ASCII cells %s have no ink" % blank[:6])
    if beyond:
        problems.append("FONT_ASCII has ink in cells past the table: %s" % beyond[:6])
    if stray:
        problems.append("FONT_ASCII has %d inked pixels outside its grid" % stray)
    if 0 in inked:
        problems.append("FONT_ASCII cell 0 (the space) has ink")

    # FONT_KANJI: two planes in one picture; each pixel's index picks a level
    # in each plane's palette.
    cw, ch = d[cells + 8], d[cells + 9]
    tex = load_texture(zero_dir, "FONT_KANJI")
    w, h = tex.width, tex.height
    cols, rows = w // cw, h // ch
    raw = tex.split()[1][0]
    idx = bytearray(w * h)
    idx[0::2] = bytes(b & 15 for b in raw)
    idx[1::2] = bytes(b >> 4 for b in raw)
    alpha_a = [p[3] for p in tex.palette()]
    clut = exe.here(CLUT_B)
    alpha_b = [d[clut + 4 * k + 3] for k in range(16)]
    planes = []
    for label, alpha, table in (("A", alpha_a, t1), ("B", alpha_b, t2)):
        mask = idx.translate(bytes(1 if alpha[k & 15] else 0 for k in range(256)))
        inked = cell_ink(mask, w, cw, ch, cols, rows)
        stray = outside_grid(mask, w, h, cw, ch, cols, rows)
        planes.append(inked)
        blank = [n for n in range(len(table)) if n not in inked and not (label == "A" and n == 0)]
        beyond = sum(1 for n in inked if n >= len(table))
        out.append("zen font %s  FONT_KANJI plane %s  %dx%d  cells %dx%d, %d x %d  %d codes %#06x..%#06x  "
                   "%d inked cells, %d past the table; ink outside the grid %d"
                   % (1 if label == "A" else 2, label, w, h, cw, ch, cols, rows, len(table),
                      table[0], table[-1], len(inked), beyond, stray))
        if blank:
            problems.append("FONT_KANJI plane %s: table cells %s have no ink" % (label, blank[:6]))
        if stray:
            problems.append("FONT_KANJI plane %s has %d inked pixels outside its grid" % (label, stray))
        if label == "A" and beyond:
            problems.append("FONT_KANJI plane A has ink in cells past its table")
    out += ["  !! " + p for p in problems]
    return out


# --- commands ----------------------------------------------------------------

def cmd_info(exe_path, zero_dir):
    exe = Exe(exe_path)
    for i in range(3):
        try:
            for line in check_euro(exe, zero_dir, i):
                print(line)
        except (ValueError, struct.error, OSError) as e:
            print("font %d  !! %s" % (i, e))
    try:
        for line in check_zen(exe, zero_dir):
            print(line)
    except (ValueError, struct.error, OSError) as e:
        print("zen fonts  !! %s" % e)


def cmd_dump(exe_path, font, out_path=None):
    import csv
    exe = Exe(exe_path)
    f = Euro(exe, font)
    if not out_path:
        sys.stdout.reconfigure(encoding="utf-8")    # cp850 glyphs such as ı
    fh = open(out_path, "w", encoding="utf-8", newline="") if out_path else sys.stdout
    try:
        out = csv.writer(fh, lineterminator="\n")
        out.writerow(["index", "glyph code", "byte", "char", "u0", "v0", "u1", "v1",
                      "advance", "record address"])
        for k, rec in enumerate(f.records):
            b = f.chars[k]
            ch = bytes([b]).decode("cp850") if 0x20 < b < 0x100 else ""
            out.writerow([k, k + GLYPH_BASE, "%#04x" % b, ch] + ["%.6f" % v for v in rec[:4]]
                         + ["%g" % rec[4], "%#x" % (f.table + 20 * k)])
    finally:
        if out_path:
            fh.close()


def cmd_png(exe_path, zero_dir, font, out_path):
    from PIL import Image, ImageDraw
    exe = Exe(exe_path)
    f = Euro(exe, font)
    tex = load_texture(zero_dir, f.name)
    w, h = tex.width, tex.height
    scale = 3
    bg = Image.new("RGBA", (w, h), (40, 40, 40, 255))
    pic = Image.new("RGBA", (w, h))
    pic.putdata(tex.pixels())
    bg.alpha_composite(pic)
    bg = bg.resize((w * scale, h * scale), Image.NEAREST)
    draw = ImageDraw.Draw(bg)
    ink = ink_mask(tex)
    for rec in f.records:
        x0, y0, x1, y1 = rect_px(rec, w, h)
        has = any(any(ink[y * w + max(0, round(x0)):y * w + min(w, round(x1))])
                  for y in range(max(0, round(y0)), min(h, round(y1))))
        draw.rectangle([x0 * scale, y0 * scale, x1 * scale - 1, y1 * scale - 1],
                       outline=(60, 200, 90, 255) if has else (220, 70, 70, 255))
    bg.convert("RGB").save(out_path)
    print("%s: %d rectangles on %s" % (out_path, len(f.records), f.name))


def cmd_coverage(exe_path, mes_path):
    import mbb
    from collections import Counter
    exe = Exe(exe_path)
    maps = [Euro(exe, i).remap() for i in range(3)]
    count = {lang: Counter() for lang in range(1, 7)}
    records = Counter()
    for _, m in mbb.iter_files([mes_path]):
        if m.lang not in count:
            continue
        for _, s in m.records:
            records[m.lang] += 1
            for t in mbb.tokens(s):
                if t[0] == "byte":
                    count[m.lang][t[1]] += 1
    for lang in range(1, 7):
        c = count[lang]
        missing = [sorted(b for b in c if not maps[i][b]) for i in range(3)]
        line = ("language %d: %s records, %d distinct text bytes, %d without a glyph in font 0"
                % (lang, format(records[lang], ","), len(c), len(missing[0])))
        if missing[0]:
            line += "  !! " + " ".join("%#04x" % b for b in missing[0])
        line += " (font 1 lacks %d, font 2 lacks %d)" % (len(missing[1]), len(missing[2]))
        print(line)
        low = sorted(b for b in c if b < 0x20)
        print("  bytes below 0x20 used: %s" % (" ".join("%#04x" % b for b in low) or "none"))


def main(argv):
    args = argv[1:]
    if not args or args[0] not in ("info", "dump", "png", "coverage"):
        print(__doc__)
        return 1
    cmd, rest = args[0], args[1:]
    if cmd == "info" and len(rest) == 2:
        cmd_info(*rest)
    elif cmd == "dump" and len(rest) in (2, 3):
        cmd_dump(rest[0], int(rest[1]), rest[2] if len(rest) > 2 else None)
    elif cmd == "png" and len(rest) == 4:
        cmd_png(rest[0], rest[1], int(rest[2]), rest[3])
    elif cmd == "coverage" and len(rest) == 2:
        cmd_coverage(*rest)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
