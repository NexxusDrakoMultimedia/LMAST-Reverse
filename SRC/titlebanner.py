# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""A version banner on the game's title screen (PAL, European languages; the Japanese release too).

The title screen is one 512x512 picture, the texture `sc_titlebg<n>_01` of
`CSE/SC_TITLEBG1.CSP` to `SC_TITLEBG6.CSP` (one pack a language, entry 2;
the same picture in all six). It holds the game's hexagonal logo and a wide
transparent margin around it. This tool draws a small banner into that
margin: "LMASTER MOD" over the version and the edition, in a navy box with
a gold edge, with the logo's own colours. LMAST Realism's pack puts its own
label at the same place (x 12 to 140, y 49 to 112), which this replaces.

The picture has a 256-colour palette that every index of is in use, so
the banner is drawn with the colours the picture has: each banner pixel
takes the nearest palette entry, and every other pixel keeps its index (the
logo is byte for byte as it was). The size, format and palette stay, so the
pack keeps its length (`csp.py replace`).

The Japanese release has one title pack, `CSE/SC_TITLEBG.CSP`, and no picture with the logo's
palette: its scene draws the stadium photograph (`sc_titlebg00`, entry 3, 512x512, 8 bits, 256
photo colours) and lays the logo band, a faint map of Europe and the menu over it. The banner
goes on the photograph, in the sky at the top left (10, 10), where the scene draws nothing.
The photograph has no navy or gold, so `stamp_jp` makes room in its palette: the 40 colours
that cost the picture least (few pixels, a near neighbour) are folded into their nearest
neighbours (the worst move is about 19 in RGB distance) and the banner, brightened because the
scene draws the photograph at colour 0xbe of 0xff, takes the 40 places. The size, format and
pack length stay.

Usage:
    python titlebanner.py preview <font.ttf> <out.png> [--version 0.5.0] [--edition Full]
    python titlebanner.py info    <SC_TITLEBG1.CSP | SC_TITLEBG.CSP> <font.ttf> [--version 0.5.0] [--edition Full]

The options default to version 0.5.0 and edition Full. `preview` stamps
DAT/CSE/SC_TITLEBG1.CSP of this repository's folder and saves the banner
at four times its size on the logo; `info` stamps the pack it is given,
reads the picture back, and checks that only the banner's rectangle
changed (on the Japanese pack, that every other pixel is the same or its palette neighbour).
"""
import collections
import os
import sys

import csp
import svr

TEXTURE_ENTRY = 2                   # the title picture's place in SC_TITLEBG<n>.CSP
POSITION = (8, 44)                  # top-left of the banner in the picture
SIZE = (140, 66)
JP_PACK = "SC_TITLEBG.CSP"          # the Japanese release's title pack
JP_ENTRY = 3                        # its stadium photograph, sc_titlebg00
JP_POSITION = (10, 10)              # top-left of the banner on the photograph
JP_COLOURS = 40                     # palette entries the banner takes from the photograph
JP_GAIN = 255 / 190                 # the scene draws the photograph at colour 0xbe: brighten the banner to match
SCALE = 4                           # the banner is drawn this many times too large
CHAMFER = 9                         # corner cut, in pixels: the logo is a hexagon
GOLD = ((255, 226, 90), (232, 120, 24))         # top, bottom of the border and title
NAVY = ((34, 66, 140), (8, 20, 72))             # top, bottom of the box
LIGHT = (205, 224, 255)
SHADOW = (6, 12, 44)


def font_at(path, size, weight):
    from PIL import ImageFont
    f = ImageFont.truetype(path, size * SCALE, layout_engine=ImageFont.Layout.BASIC)
    try:
        f.set_variation_by_axes([weight])
    except (OSError, AttributeError):
        pass
    return f


def fit(path, text, size, weight, room):
    """The font at `size`, or smaller until `text` is at most `room`
    supersampled pixels wide."""
    f = font_at(path, size, weight)
    while size > 6 and f.getlength(text) > room:
        size -= 1
        f = font_at(path, size, weight)
    return f


def lerp(a, b, t):
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def gradient(w, h, top, bottom):
    from PIL import Image
    img = Image.new("RGBA", (w, h))
    px = img.load()
    for y in range(h):
        c = lerp(top, bottom, y / max(1, h - 1)) + (255,)
        for x in range(w):
            px[x, y] = c
    return img


def box_mask(w, h, inset, cut):
    """A box with its corners cut, `inset` pixels in from the edge (supersampled)."""
    from PIL import Image, ImageDraw
    m = Image.new("L", (w, h), 0)
    i, c = inset, cut
    ImageDraw.Draw(m).polygon([(i + c, i), (w - i - c - 1, i), (w - i - 1, i + c),
                               (w - i - 1, h - i - c - 1), (w - i - c - 1, h - i - 1),
                               (i + c, h - i - 1), (i, h - i - c - 1), (i, i + c)], fill=255)
    return m


def draw(font_path, version, edition, size=SIZE):
    """The banner as an RGBA picture of `size` pixels."""
    from PIL import Image, ImageDraw
    s = SCALE
    w, h = size[0] * s, size[1] * s
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    # border: gold gradient in the outer cut box, the navy box inside it
    outer = box_mask(w, h, 0, CHAMFER * s)
    inner = box_mask(w, h, 3 * s, (CHAMFER - 2) * s)
    img.paste(gradient(w, h, *GOLD), (0, 0), outer)
    img.paste(gradient(w, h, *NAVY), (0, 0), inner)
    d = ImageDraw.Draw(img)
    # a thin light line just inside the gold edge
    from PIL import ImageChops
    ring = ImageChops.subtract(box_mask(w, h, 4 * s - s // 2, (CHAMFER - 3) * s),
                               box_mask(w, h, 4 * s, (CHAMFER - 3) * s))
    img.paste(Image.new("RGBA", (w, h), LIGHT + (110,)), (0, 0), ring)
    # the text: LMASTER MOD (gold) over the version and edition (light)
    room = w - 2 * 12 * s                           # the text stays off the gold edge
    title = fit(font_path, "LMASTER MOD", 24, 800, room)
    sub = fit(font_path, "v%s   %s" % (version, edition.upper()), 15, 600, room)
    tw = d.textlength("LMASTER MOD", font=title)
    tx, ty = (w - tw) / 2, 8 * s
    d.text((tx + s, ty + s), "LMASTER MOD", font=title, fill=SHADOW + (255,))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).text((tx, ty), "LMASTER MOD", font=title, fill=255)
    img.paste(gradient(w, h, *GOLD), (0, 0), mask)
    line2 = ("v%s   %s" % (version, edition.upper())) if version else edition.upper()
    sw = d.textlength(line2, font=sub)
    d.text(((w - sw) / 2 + s // 2, 40 * s + s // 2), line2, font=sub, fill=SHADOW + (255,))
    d.text(((w - sw) / 2, 40 * s), line2, font=sub, fill=LIGHT + (255,))
    return img.resize(size, Image.BOX)


def stamp(blob, banner, position=POSITION):
    """The title picture (an SVR) with `banner` (RGBA) drawn at `position`
    in the picture's own palette; every other pixel keeps its index."""
    tex = svr.parse_svr(blob)
    if (tex.width, tex.height, tex.bpp) != (512, 512, 8):
        raise ValueError("the title picture is %dx%d, %d bpp, not 512x512 at 8 bpp"
                         % (tex.width, tex.height, tex.bpp))
    palette_bytes, levels, pads, tail = tex.split()
    index = bytearray(levels[0])
    pal = tex.palette()
    # swizzled 8 bpp pictures keep a CLUT permutation: `levels` is linear,
    # and tex.palette() applies it, so a linear index picks pal[index]
    bw, bh = banner.size
    px = banner.load()
    x0, y0 = position
    for y in range(bh):
        for x in range(bw):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            index[(y0 + y) * 512 + x0 + x] = svr.nearest([(r, g, b, a)], pal)[0]
    body = tex.join(palette_bytes, [bytes(index)], pads, tail)
    return svr.encode_svr(tex, body)


def _distance(p, q):
    return sum((a - b) ** 2 for a, b in zip(p[:3], q[:3]))


def stamp_jp(blob, banner, position=JP_POSITION, colours=JP_COLOURS):
    """The Japanese title photograph (an SVR) with `banner` (RGBA) drawn at `position`. The
    photograph's palette has no room for the banner's colours, so the `colours` that cost it least
    (pixel count times the distance to the nearest other colour) are folded into their nearest
    neighbours, and the banner, composited over the photograph and brightened by JP_GAIN, is reduced
    to `colours` colours that take their places. Needs pillow."""
    from PIL import Image
    tex = svr.parse_svr(blob)
    if (tex.width, tex.height, tex.bpp) != (512, 512, 8):
        raise ValueError("the title photograph is %dx%d, %d bpp, not 512x512 at 8 bpp"
                         % (tex.width, tex.height, tex.bpp))
    px = list(tex.pixels())
    count = collections.Counter(px)
    visible = [c for c in count if c[3] != 0]
    remove = max(0, len(count) + colours - 256)
    cost = {c: count[c] * min(_distance(c, d) for d in visible if d != c) for c in visible}
    gone = set(sorted(visible, key=cost.get)[:remove])
    keep = [c for c in visible if c not in gone]
    remap = {c: min(keep, key=lambda k: _distance(c, k)) for c in gone}
    px = [remap.get(p, p) for p in px]
    x0, y0 = position
    bw, bh = banner.size
    bpx = banner.load()
    region = {}
    for y in range(bh):
        for x in range(bw):
            r, g, b, a = bpx[x, y]
            if a == 0:
                continue
            r, g, b = (min(255, round(v * JP_GAIN)) for v in (r, g, b))
            i = (y0 + y) * 512 + x0 + x
            pr, pg, pb, _ = px[i]
            t = a / 255
            region[i] = (round(r * t + pr * (1 - t)), round(g * t + pg * (1 - t)), round(b * t + pb * (1 - t)))
    where = sorted(region)
    strip = Image.new("RGB", (len(where), 1))
    strip.putdata([region[i] for i in where])
    q = strip.quantize(colors=colours, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()
    for i, k in zip(where, q.tobytes()):
        px[i] = (pal[3 * k], pal[3 * k + 1], pal[3 * k + 2], 255)
    if len(set(px)) > 256:
        raise ValueError("the stamped photograph has %d colours" % len(set(px)))
    return svr.encode_svr(tex, svr.body_from_pixels(tex, px, new_palette=True))


def stamp_pack(pack, banner, position=None, jp=False):
    """The CSP `pack` with its title picture stamped (`jp`: the Japanese pack's photograph)."""
    ents, _ = csp.split_csp(pack)
    if jp:
        return csp.replace_entry(pack, JP_ENTRY, stamp_jp(ents[JP_ENTRY][0], banner, position or JP_POSITION))
    new = stamp(ents[TEXTURE_ENTRY][0], banner, position or POSITION)
    return csp.replace_entry(pack, TEXTURE_ENTRY, new)


def preview_image(blob, banner, position=POSITION):
    from PIL import Image
    tex = svr.parse_svr(svr_bytes := stamp(blob, banner, position))
    px = tex.pixels()
    img = Image.new("RGBA", (512, 512))
    img.putdata(px)
    bg = Image.new("RGBA", img.size, (70, 70, 70, 255))
    bg.alpha_composite(img)
    return bg.convert("RGB")


def cmd_info(pack_path, font_path, opts):
    """Stamp a title pack and read it back: the pack keeps its length and
    every other entry, only the banner's rectangle of the picture changes
    (every pixel outside it keeps its palette index), the palette is the
    same, and the banner's pixels all took a palette entry."""
    with open(pack_path, "rb") as f:
        pack = f.read()
    banner = draw(font_path, opts["version"], opts["edition"])
    jp = os.path.basename(pack_path).upper() == JP_PACK
    new = stamp_pack(pack, banner, jp=jp)
    problems = []
    if len(new) != len(pack):
        problems.append("the pack is %d bytes, was %d" % (len(new), len(pack)))
    old_e, _ = csp.split_csp(pack)
    new_e, _ = csp.split_csp(new)
    entry = JP_ENTRY if jp else TEXTURE_ENTRY
    for i, (a, b) in enumerate(zip(old_e, new_e)):
        if i != entry and a != b:
            problems.append("entry %d changed" % i)
    if jp:
        return info_jp(pack_path, svr.parse_svr(old_e[entry][0]), svr.parse_svr(new_e[entry][0]), banner, problems)
    t0, t1 = svr.parse_svr(old_e[TEXTURE_ENTRY][0]), svr.parse_svr(new_e[TEXTURE_ENTRY][0])
    if t0.split()[0] != t1.split()[0]:
        problems.append("the palette changed")
    a, b = t0.split()[1][0], t1.split()[1][0]
    x0, y0 = POSITION
    bw, bh = banner.size
    outside = changed = 0
    for y in range(512):
        for x in range(512):
            if a[y * 512 + x] != b[y * 512 + x]:
                if x0 <= x < x0 + bw and y0 <= y < y0 + bh:
                    changed += 1
                else:
                    outside += 1
    if outside:
        problems.append("%d pixels outside the banner's rectangle changed" % outside)
    print("%s: banner %dx%d at (%d, %d), %d of %d pixels of its rectangle changed, %d outside it"
          % (os.path.basename(pack_path), bw, bh, x0, y0, changed, bw * bh, outside))
    for p in problems:
        print("  !! " + p)


def info_jp(pack_path, t0, t1, banner, problems):
    """The Japanese pack's check: the photograph keeps its size and 256 colours, every pixel outside the
    banner's rectangle is the same or moved to a near palette neighbour (at most 19 in RGB distance), and
    the corners the banner leaves transparent keep the photograph."""
    a, b = t0.pixels(), t1.pixels()
    x0, y0 = JP_POSITION
    bw, bh = banner.size
    bpx = banner.load()
    outside = moved = worst = 0
    for y in range(512):
        for x in range(512):
            i = y * 512 + x
            inside = x0 <= x < x0 + bw and y0 <= y < y0 + bh
            if inside and bpx[x - x0, y - y0][3] != 0:
                continue
            if a[i] != b[i]:
                moved += 1
                worst = max(worst, _distance(a[i], b[i]) ** 0.5)
                if a[i][3] != b[i][3]:
                    problems.append("a pixel changed its alpha")
                    break
    if worst > 20:
        problems.append("a photograph pixel moved by %.0f in RGB distance" % worst)
    colours = len(set(b))
    if colours > 256:
        problems.append("%d colours" % colours)
    print("%s: banner %dx%d at (%d, %d) on the photograph, %d pixels outside it moved to a palette neighbour "
          "(worst %.1f), %d colours" % (os.path.basename(pack_path), bw, bh, x0, y0, moved, worst, colours))
    for p in problems:
        print("  !! " + p)


def parse_opts(args):
    opts, rest, it = {"version": "0.5.0", "edition": "Full"}, [], iter(args)
    for a in it:
        if a == "--version":
            opts["version"] = next(it)
        elif a == "--edition":
            opts["edition"] = next(it)
        else:
            rest.append(a)
    return rest, opts


def main(argv):
    args = argv[1:]
    if not args or args[0] not in ("preview", "info"):
        print(__doc__)
        return 1
    cmd, (rest, opts) = args[0], parse_opts(args[1:])
    if cmd == "preview" and len(rest) == 2:
        pack = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DAT", "CSE",
                            "SC_TITLEBG1.CSP")
        with open(pack, "rb") as f:
            blob = csp.split_csp(f.read())[0][TEXTURE_ENTRY][0]
        banner = draw(rest[0], opts["version"], opts["edition"])
        img = preview_image(blob, banner)
        crop = img.crop((0, 0, 256, 192)).resize((1024, 768), 0)
        crop.save(rest[1])
        print("wrote", rest[1])
        return 0
    if cmd == "info" and len(rest) == 2:
        cmd_info(rest[0], rest[1], opts)
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
