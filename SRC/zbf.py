"""ZBF pre-rendered depth buffer reader for Let's Make a Soccer Team! (PS2).

A .zbf is the Z buffer of a pre-rendered background: 512x448 little-endian
u32 depth values, row-major, top-left first, not swizzled. It lines up
pixel-for-pixel with the matching CSE/BG_xx_nn_00.CSP background texture
(512x512, drawn squashed to the 512x448 screen). Only the low 24 bits
count; larger = nearer. They live inside BG/BG_*.MRG - see DOC/ZBF_FORMAT.md.

Usage:
    python zbf.py info <file.zbf | file.MRG | dir> ...
    python zbf.py png  <file.zbf | file.MRG | dir> ... <out_dir>

Requires: pip install pillow  (only for `png`)
"""
import os
import struct
import sys

from pac import BinPac

WIDTH, HEIGHT = 512, 448
SIZE = WIDTH * HEIGHT * 4
Z_MASK = 0xFFFFFF  # PSMZ24: the GS ignores the top byte


def decode(blob):
    if len(blob) != SIZE:
        raise ValueError("expected %d bytes, got %d" % (SIZE, len(blob)))
    return [v & Z_MASK for v in struct.unpack("<%dI" % (WIDTH * HEIGHT), blob)]


def _iter_zbf(args):
    """Yield (label, raw bytes) for each .zbf, including those inside .MRGs."""
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for name in sorted(files):
                    if name.upper().endswith((".ZBF", ".MRG")):
                        yield from _iter_zbf([os.path.join(root, name)])
            continue
        with open(a, "rb") as f:
            buf = f.read()
        if a.upper().endswith(".MRG"):
            for off, size, name, _ in BinPac(buf).entries:
                if name.lower().endswith(".zbf"):
                    yield name, buf[off:off + size]
        else:
            yield os.path.basename(a), buf


def cmd_info(paths):
    for label, blob in _iter_zbf(paths):
        try:
            z = decode(blob)
        except ValueError as e:
            print("%-24s !! %s" % (label, e))
            continue
        high = sum(1 for v in struct.unpack("<%dI" % (WIDTH * HEIGHT), blob) if v >> 24)
        print("%-24s min=%#08x max=%#08x%s" % (
            label, min(z), max(z), "  !! %d px with bits above 24" % high if high else ""))


def cmd_png(paths, out_dir):
    """Greyscale, min..max stretched to 0..255 (white = near)."""
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    for label, blob in _iter_zbf(paths):
        z = decode(blob)
        lo, hi = min(z), max(z)
        span = (hi - lo) or 1
        img = Image.new("L", (WIDTH, HEIGHT))
        img.putdata([(v - lo) * 255 // span for v in z])
        out = os.path.join(out_dir, os.path.splitext(label)[0] + ".png")
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
        cmd_png(args[:-1], args[-1])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
