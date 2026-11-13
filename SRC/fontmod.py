# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""A modern face for the game's main font (PAL, European languages).

The game draws all text of the languages 1-6 from FONT_20_A, a 256x256
picture, through glyph records in the executable (font 0: rectangle,
advance, 26 rows tall). This tool draws a TrueType face (Roboto Condensed
is the one it is tuned for) into that picture and rewrites the 214 records
to the new rectangles and widths, so the text keeps the game's own layout
code and the glyphs get the face's own proportional spacing. The two small
8x8 pixel fonts stay as they are. DOC/FONT_FORMAT.md has the format and
the rules a replacement face must keep; DOC/LMASTER_MOD.md#modern-font has
the switch.

What it does, glyph by glyph:
  * the character a record draws comes from the game's own character list
    (cp850, with the few bytes the game draws differently);
  * the face is drawn four times too large and reduced, for smooth edges,
    in white, with the 16 alpha levels of the picture's own palette;
  * the baseline sits at one row for every glyph; an accented capital
    keeps its letter at full height and only its mark is pressed into
    the rows above, and any other glyph that would leave rows 1-24 (long
    descenders) is squeezed vertically, only as much as it needs;
  * the width is the face's advance rounded to whole pixels (widened when
    ink reaches past it), because a glyph's advance is its rectangle's
    width;
  * the pad buttons, the euro sign with a small s and the blank
    placeholders keep the game's own pictures (the face has no such
    shapes); the 17 empty records all point at one blank cell.

Usage:
    python fontmod.py info    <exe> <0SYSTEM dir> <font.ttf> [options]
    python fontmod.py preview <exe> <0SYSTEM dir> <font.ttf> <out.png> [options]
    python fontmod.py render  <exe> <0SYSTEM dir> <font.ttf> <out dir> [options]

Options (each takes a value): --size N (default 24, the face's pixel
size), --weight N (default 450, for a variable face's weight axis),
--baseline N (the baseline row, default 21), --gamma G (default 1.0,
alpha ** G), --tracking T (default 0.0, pixels added to every advance).

`info` builds the new picture and records and checks them; `preview`
saves the old and new pictures and sample lines as the game scales them;
`render` writes FONT_20_A.SVR and records.bin (the 214 new records, for
the executable at the font's table) into <out dir>.
"""
import os
import struct
import sys

import font
import svr

PIXEL_SCALE = 4             # the face is drawn this many times too large
ROWS = 26                   # the font's height (descriptor +8)
FIRST, LAST = 1, 24         # rows a glyph may ink; 0 and 25 are shared with
                            # the next rectangle row (rectangles overlap by one)
PITCH = 25                  # rows between rectangle rows
PAD = 6                     # columns of room each side of a drawn glyph
DESCENT = 4                 # rows below the baseline (to row LAST)
DEFAULT_SIZE = 24
DEFAULT_WEIGHT = 450
# Bytes the game draws differently from cp850 (DOC/FONT_FORMAT.md).
CHARS = {0xfb: "¹", 0xfc: "²", 0xfd: "³", 0xb3: "€",
         0xcd: "ć", 0xcc: "Ć", 0xbb: "Š", 0xbc: "š",
         0xca: "Ž", 0xcb: "ž", 0xce: "Č", 0xd9: "č",
         0xb2: "·", 0xee: "¯",
         0xbf: "¥"}                 # shares the yen sign's place; cp850 has a box corner
# Records that keep the game's own art: the pad buttons, the euro sign
# with a small s.
KEEP = {0x10, 0x11, 0x12, 0x13, 0xba}


def char_of(byte):
    """The character the game draws for a byte of font 0."""
    if byte in CHARS:
        return CHARS[byte]
    return bytes([byte]).decode("cp850")


def byte_of(ch):
    """The byte that draws `ch`: the reverse of char_of."""
    for b, c in CHARS.items():
        if c == ch:
            return b
    return ch.encode("cp850")[0]


def levels(tex):
    """The picture's palette as (index, alpha 0-255), faintest first."""
    pal = tex.palette()
    return sorted((p[3], i) for i, p in enumerate(pal))


def to_index(table, coverage):
    """The palette index whose alpha is nearest to `coverage` (0-255)."""
    best = min(table, key=lambda t: abs(t[0] - coverage))
    return best[1]


class Face:
    """A TrueType face at one size and weight."""

    def __init__(self, path, size=DEFAULT_SIZE, weight=DEFAULT_WEIGHT):
        from PIL import ImageFont
        self.path, self.size, self.weight = path, size, weight
        self.big = ImageFont.truetype(path, size * PIXEL_SCALE,
                                      layout_engine=ImageFont.Layout.BASIC)
        try:
            self.big.set_variation_by_axes([weight])
        except (OSError, AttributeError):
            pass                                    # a face without a weight axis

    def draw(self, ch, baseline):
        """(cell, advance): `ch` drawn four times too large on a canvas of
        ROWS rows (supersampled) with its baseline at row `baseline` and
        PAD columns of room on each side, and the face's advance in pixels."""
        from PIL import Image, ImageDraw
        s = PIXEL_SCALE
        adv = self.big.getlength(ch) / s
        w = int(adv) + 2 * PAD
        img = Image.new("L", (w * s, ROWS * s * 2), 0)
        d = ImageDraw.Draw(img)
        base = ROWS * s                             # room above and below
        d.text((PAD * s, base), ch, font=self.big, fill=255, anchor="ls")
        top = base - baseline * s
        return img.crop((0, top, img.width, top + ROWS * s)), adv

    def cell(self, ch, baseline):
        """(cell, advance, how): the glyph for `ch`, fitted into rows
        FIRST to LAST. An accented capital keeps its letter at full height
        and only its mark is pressed into the rows above it; anything else
        that is still too tall or deep is squeezed (`how` says which)."""
        import unicodedata
        from PIL import Image, ImageChops
        s = PIXEL_SCALE
        cell, adv = self.draw(ch, baseline)
        how = ""
        nfd = unicodedata.normalize("NFD", ch)
        if len(nfd) > 1 and nfd[0].isupper():
            letter, _ = self.draw(nfd[0], baseline)
            cap = letter.getbbox()[1]               # the letter's top row
            up = cell.crop((0, 0, cell.width, cap))
            mark_box = up.getbbox()
            if mark_box:
                m0, m1 = mark_box[1], mark_box[3]
                mark = up.crop((0, m0, up.width, m1))
                gap = max(min(cap - m1, 1.0 * s), 0.5 * s)
                bottom = cap - gap
                room = bottom - FIRST * s
                if mark.height > room:
                    mark = mark.resize((mark.width, max(1, round(room))), Image.BOX)
                canvas = Image.new("L", cell.size, 0)
                canvas.paste(mark, (0, round(bottom - mark.height)))
                cell = ImageChops.lighter(letter, canvas)
                how = "accent"
        before = cell
        cell = squeeze(cell, baseline * s, (baseline - FIRST) * s, (LAST + 1 - baseline) * s)
        if cell is not before:
            how = "squeezed"
        return cell, adv, how


def squeeze(img, base, top_rows, bottom_rows):
    """`img` (a supersampled glyph, baseline at row `base`) with the part
    above the baseline pressed into `top_rows` rows and the part below into
    `bottom_rows`, only where it is taller than that (in supersampled
    rows, which the caller multiplies out)."""
    from PIL import Image
    box = img.getbbox()
    if not box:
        return img
    top, bottom = base - box[1], box[3] - base
    out = img
    if top > top_rows or bottom > bottom_rows:
        parts = []
        up = img.crop((0, 0, img.width, base))
        dn = img.crop((0, base, img.width, img.height))
        if top > top_rows:
            keep = max(1, round(up.height * top_rows / top))
            up = up.resize((up.width, keep), Image.BOX)
            canvas = Image.new("L", (img.width, base), 0)
            canvas.paste(up, (0, base - keep))
            up = canvas
        if bottom > bottom_rows:
            keep = max(1, round(dn.height * bottom_rows / bottom))
            dn = dn.resize((dn.width, keep), Image.BOX)
            canvas = Image.new("L", (img.width, img.height - base), 0)
            canvas.paste(dn, (0, 0))
            dn = canvas
        out = Image.new("L", img.size, 0)
        out.paste(up, (0, 0))
        out.paste(dn, (0, base))
    return out


def build(exe_path, zero_dir, ttf, size=DEFAULT_SIZE, weight=DEFAULT_WEIGHT,
          baseline=None, gamma=1.0, tracking=0.0):
    """The new font 0: a dict with `pixels` (the picture's palette indices,
    256 x 256, row-major), `records` (five floats each, in the old order),
    `old`, `tex`, `lines` (what to report) and `problems`."""
    from PIL import Image
    exe = font.Exe(exe_path)
    f = font.Euro(exe, 0)
    tex = font.load_texture(zero_dir, f.name)
    W, H = tex.width, tex.height
    table = levels(tex)
    ink = font.ink_mask(tex)
    old_px = tex.pixels()
    face = Face(ttf, size, weight)
    s = PIXEL_SCALE
    # The baseline row: descenders get the DESCENT rows from it down to
    # row LAST, caps the rows above it.
    if baseline is None:
        baseline = LAST + 1 - DESCENT
    cells = []                                      # (k, byte, w, rows of 0-255, adv) per record
    problems, notes = [], []
    squeezed = []
    for k, (b, rec) in enumerate(zip(f.chars, f.records)):
        x0, y0, x1, y1 = [round(v) for v in font.rect_px(rec, W, H)]
        w_old = x1 - x0
        n_ink = sum(ink[y * W + x] for y in range(y0, min(y1, H)) for x in range(x0, x1))
        if b in KEEP or n_ink == 0:
            rows = [[old_px[y * W + x][3] for x in range(x0, x1)] if y < H else [0] * w_old
                    for y in range(y0, y0 + ROWS)]
            cells.append((k, b, w_old, rows, rec[4], "kept" if n_ink else "blank"))
            continue
        ch = char_of(b)
        cell, adv, how = face.cell(ch, baseline)
        if how:
            squeezed.append(ch)
        box = cell.getbbox()
        if box is None:
            cells.append((k, b, w_old, [[0] * w_old for _ in range(ROWS)], rec[4], "blank"))
            continue
        # The ink's extent in pixels from the start of the advance box,
        # the advance with the tracking, and the whole pixels the glyph gets:
        # the advance box centred in them, widened where ink reaches out.
        left, right = box[0] / s - PAD, box[2] / s - PAD
        want = adv + tracking
        w = max(1, round(want))
        offset = (w - adv) / 2
        if left + offset < 0:
            offset = -left
        w = max(w, -int(-(right + offset) // 1))
        canvas = Image.new("L", (w * s, ROWS * s), 0)
        canvas.paste(cell, (round((offset - PAD) * s), 0))
        small = canvas.resize((w, ROWS), Image.BOX)
        px = small.load()
        rows = [[px[x, y] for x in range(w)] for y in range(ROWS)]
        if gamma != 1.0:
            rows = [[int(255 * (v / 255) ** gamma) for v in r] for r in rows]
        cells.append((k, b, w, rows, float(w), "drawn"))
    # --- pack the rectangles: rows of PITCH, in the old order, with the
    # blank cell (for every record without ink) at the end.
    placed = {}
    blank_w = max((c[2] for c in cells if c[5] == "blank"), default=0)
    x = y = 0
    order = [c for c in cells if c[5] != "blank"]
    for c in order:
        if x + c[2] > W:
            x, y = 0, y + PITCH
        placed[c[0]] = (x, y)
        x += c[2]
    if x + blank_w > W:
        x, y = 0, y + PITCH
    blank_at = (x, y)
    if y + ROWS > H:
        problems.append("the glyphs need %d rows, the picture has %d" % (y + ROWS, H))
    # --- draw the new picture
    new = bytearray(W * H)                              # palette index 0 = transparent
    records = []
    for c in cells:
        k, b, w, rows, adv, kind = c
        if kind == "blank":
            xx, yy = blank_at
        else:
            xx, yy = placed[k]
            for ry in range(ROWS):
                if yy + ry >= H:
                    break
                for rx in range(w):
                    v = rows[ry][rx]
                    if v:
                        new[(yy + ry) * W + xx + rx] = to_index(table, v)
        # an empty rectangle keeps its old width and advance
        ww = w if kind != "blank" else round(f.records[k][2] * W - f.records[k][0] * W)
        records.append((xx / W, yy / H, (xx + ww) / W, (yy + ROWS) / H, adv if kind != "blank" else f.records[k][4]))
    # --- checks: rows 0 and ROWS - 1 of every drawn rectangle are blank
    for c in cells:
        k, b, w, rows, adv, kind = c
        if kind == "drawn":
            if any(rows[0]) or any(rows[ROWS - 1]):
                problems.append("glyph %#04x %r inks a shared row" % (b, char_of(b)))
    lines = ["%d records: %d drawn, %d kept, %d blank; picture rows used %d of %d; squeezed %s"
             % (len(cells), sum(c[5] == "drawn" for c in cells), sum(c[5] == "kept" for c in cells),
                sum(c[5] == "blank" for c in cells), y + ROWS, H, "".join(squeezed) or "none")]
    return {"pixels": new, "records": records, "old": f.records, "tex": tex, "face": face,
            "lines": lines, "problems": problems, "baseline": baseline, "table": table,
            "cells": cells, "euro": f}


def records_bytes(result):
    """The 214 new glyph records as the executable holds them."""
    return b"".join(font.RECORD.pack(*r) for r in result["records"])


def svr_bytes(result):
    """The new FONT_20_A.SVR: the picture's header, palette and padding as
    they were, with the new indices as its pixels (swizzled)."""
    tex = result["tex"]
    palette, _, pads, tail = tex.split()
    body = tex.join(palette, [svr.pack_indices(list(result["pixels"]), 4)], pads, tail)
    return svr.encode_svr(tex, body)


def verify(result, exe_path, zero_dir):
    """Lines that check the new files by reading them back the way the
    game does: the picture and the records are written to a scratch copy
    and `font.py` checks the glyph table against the picture, then every
    rectangle is compared with the glyph that was drawn into it. Each
    problem starts with `!!`."""
    import shutil
    import tempfile
    out = []
    f = result["euro"]
    with tempfile.TemporaryDirectory() as tmp:
        for name in font.EURO:
            shutil.copyfile(os.path.join(zero_dir, name + ".SVR"), os.path.join(tmp, name + ".SVR"))
        data = svr_bytes(result)
        with open(os.path.join(tmp, f.name + ".SVR"), "wb") as g:
            g.write(data)
        exe = font.Exe(exe_path)
        patched = bytearray(exe.data)
        off = exe.va(f.table)
        patched[off:off + 20 * len(f.records)] = records_bytes(result)
        new_exe = os.path.join(tmp, "exe")
        with open(new_exe, "wb") as g:
            g.write(patched)
        out += font.check_euro(font.Exe(new_exe), tmp, 0)
        back = svr.load(os.path.join(tmp, f.name + ".SVR"))[0]
        W, H = back.width, back.height
        alpha = [p[3] for p in back.pixels()]
        table = {i: a for a, i in result["table"]}
        bad = 0
        for c, rec in zip(result["cells"], result["records"]):
            k, b, w, rows, adv, kind = c
            if kind == "blank":
                continue
            x0, y0 = round(rec[0] * W), round(rec[1] * H)
            for ry in range(ROWS):
                for rx in range(w):
                    want = table[to_index(result["table"], rows[ry][rx])]
                    if alpha[(y0 + ry) * W + x0 + rx] != want:
                        bad += 1
        if bad:
            out.append("  !! %d pixels of the new picture differ from the glyphs drawn" % bad)
    out += ["  !! " + p for p in result["problems"]]
    return out


def picture(result, which="new"):
    """A PIL image (white text on a dark blue ground) of the old or new picture."""
    from PIL import Image
    tex = result["tex"]
    W, H = tex.width, tex.height
    img = Image.new("RGB", (W, H), (40, 40, 90))
    alphas = {i: a for a, i in result["table"]}
    if which == "new":
        idx = result["pixels"]
        data = [alphas[i] for i in idx]
    else:
        data = [p[3] for p in tex.pixels()]
    px = img.load()
    for i, a in enumerate(data):
        t = a / 255
        px[i % W, i // W] = tuple(int(c + (255 - c) * t) for c in (40, 40, 90))
    return img


def sample(result, text, which="new", zoom=20 / 26, ground=(40, 40, 90)):
    """`text` laid out the way sbFontPuts does and scaled by `zoom` with
    bilinear sampling, as a PIL image."""
    from PIL import Image
    f = result["euro"]
    remap = f.remap()
    tex = result["tex"]
    W, H = tex.width, tex.height
    alphas = {i: a for a, i in result["table"]}
    if which == "new":
        atlas_a = [alphas[i] for i in result["pixels"]]
        recs = result["records"]
    else:
        atlas_a = [p[3] for p in tex.pixels()]
        recs = result["old"]
    atlas = Image.new("L", (W, H))
    atlas.putdata(atlas_a)
    codes = [remap[byte_of(c)] for c in text]
    width = sum(recs[code - 4][4] if code >= 4 else f.space for code in codes) * zoom + 8
    out = Image.new("RGB", (int(width) + 4, int(ROWS * zoom) + 4), ground)
    x = 2.0
    for code in codes:
        if code < 4:
            x += f.space * zoom
            continue
        u0, v0, u1, v1, adv = recs[code - 4]
        x0, y0, x1, y1 = round(u0 * W), round(v0 * H), round(u1 * W), round(v0 * H) + ROWS
        glyph = atlas.crop((x0, y0, x0 + int(adv), y0 + ROWS))
        gw, gh = max(1, round(adv * zoom)), round(ROWS * zoom)
        scaled = glyph.transform((gw, gh), Image.AFFINE, (1 / zoom, 0, 0, 0, 1 / zoom, 0),
                                 Image.BILINEAR)
        ink = Image.new("RGB", (gw, gh), (255, 255, 255))
        out.paste(ink, (int(round(x)), 2), scaled)
        x += adv * zoom
    return out


SAMPLES = ["Manchester United 3-1 Real Madrid", "Zinedine Zidane   Ronaldinho   Raúl",
           "ÄÖÜ ÅÆØ Çéèêë Šćžč ñÑ ß £1,250,000 € 100% (12/34)",
           "The quick brown fox jumps over the lazy dog. 0123456789"]


def cmd_preview(exe, zero, ttf, out, opts):
    from PIL import Image
    r = build(exe, zero, ttf, **opts)
    print("\n".join(r["lines"]))
    for p in r["problems"]:
        print("  !! " + p)
    parts = [picture(r, "old").resize((512, 512), Image.NEAREST),
             picture(r, "new").resize((512, 512), Image.NEAREST)]
    sheet_w = 1024
    lines = []
    for zoom in (20 / 26, 1.0):
        for t in SAMPLES:
            for which in ("old", "new"):
                lines.append(sample(r, t, which, zoom))
    h = 512 + sum(l.height + 2 for l in lines)
    sheet = Image.new("RGB", (sheet_w, h), (40, 40, 90))
    sheet.paste(parts[0], (0, 0))
    sheet.paste(parts[1], (512, 0))
    y = 512
    for l in lines:
        sheet.paste(l, (0, y))
        y += l.height + 2
    sheet.save(out)
    print("wrote", out)


def parse_opts(args):
    opts = {}
    rest = []
    it = iter(args)
    for a in it:
        if a == "--size":
            opts["size"] = int(next(it))
        elif a == "--weight":
            opts["weight"] = int(next(it))
        elif a == "--baseline":
            opts["baseline"] = int(next(it))
        elif a == "--gamma":
            opts["gamma"] = float(next(it))
        elif a == "--tracking":
            opts["tracking"] = float(next(it))
        else:
            rest.append(a)
    return rest, opts


def cmd_info(exe, zero, ttf, opts):
    r = build(exe, zero, ttf, **opts)
    print("face %s, size %s, weight %s, baseline row %d" % (
        os.path.basename(ttf), r["face"].size, r["face"].weight, r["baseline"]))
    print(r["lines"][0])
    for line in verify(r, exe, zero):
        print(line)


def cmd_render(exe, zero, ttf, out_dir, opts):
    r = build(exe, zero, ttf, **opts)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, r["euro"].name + ".SVR"), "wb") as g:
        g.write(svr_bytes(r))
    with open(os.path.join(out_dir, "records.bin"), "wb") as g:
        g.write(records_bytes(r))
    print(r["lines"][0])
    print("wrote %s and records.bin (%d records, for the table at %#x)"
          % (r["euro"].name + ".SVR", len(r["records"]), r["euro"].table))


def main(argv):
    args = argv[1:]
    if not args or args[0] not in ("info", "preview", "render"):
        print(__doc__)
        return 1
    cmd, rest = args[0], args[1:]
    rest, opts = parse_opts(rest)
    if cmd == "preview" and len(rest) == 4:
        cmd_preview(*rest, opts)
    elif cmd == "info" and len(rest) == 3:
        cmd_info(*rest, opts)
    elif cmd == "render" and len(rest) == 4:
        cmd_render(*rest, opts)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
