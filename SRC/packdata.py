# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""etc::PackData reader for Let's Make a Soccer Team! (PS2).

Every entry of a KC@P pack (face packs, licensed kits, the edit-face pack,
GAME/CUTINPACK) is an etc::PackData after PRS expansion: a block count, an
offset table and padding, then typed blocks.

    +0x00  u32  n
    +0x04  u32  off[n]          relative to the data base
    ...    zero padding up to base = 4 * (n + pad + 1), where base % 16 == 8
           so that each block's data (base + off + 8) is 16-aligned
    base + off[i]:  u32 type, u32 size, data[size]

Confirmed from SLES_541.51: etc::PackData::GetPackBlock (0x11f5f8) computes
the padding and base, and etc::PackBlock::GetPackBlockType / GetSize /
GetDataTop (0x11f598 / 0x11f5a8 / 0x11f588) read the block header. Block
roles come from CLoader::l_realize_facepack (0x11c108),
l_realize_licenceuniform (0x11c730) and l_realize_editfacepack (0x11cc08).
See DOC/PLAYER_DIR.md.

`info` checks the empirical packing rule as well: blocks sit back to back,
each at the previous offset plus (8 + size) rounded up to 16, and anything
after the last block is zero. Packs with more than SAMPLE_LIMIT entries are
sampled (every Nth entry plus the last) because expanding all of
FC_EURO_FACEPACK_00.BIN (1.1 GB) takes minutes; --all checks every entry.

Usage:
    python packdata.py info    <file|dir> ... [--all]      # check every KC@P pack found
    python packdata.py list    <header> <index>            # blocks of one entry
    python packdata.py extract <header> <index> <outdir>   # write each block's data
    python packdata.py names   <header> [first [last]]     # model and texture names
    python packdata.py cutin   <header>                    # check the CIB0 and BMT1 blocks
    python packdata.py textures  <header> [first [last]]   # the texture blocks of the entries
    python packdata.py replace   <header> <out header> <entry>.<block>[.<texture>]=<file> ... [--palette keep] [--prs]
    python packdata.py roundtrip <header> ... [--all]      # texture blocks back from their own pictures; !! on a difference

`cutin` checks the two block kinds GAME/CUTINPACK.BIN uses besides Ninja
models and motions. A BMT1 block (type 23) is spline data (confirmed from
SLES 0x11ed60, which passes `base + u32[1]`, `u32[2]` and a stride of 0x40
to CreateSISplineInterpolator): "BMT1", u32 0x10 (the offset of the
points), u32 n, a zero word, then n points of 0x40 bytes (16 floats; the
twelfth, a frame-time-like value, rises along the curve in five of the
seven blocks and dips slightly in two: empirical). A CIB0 block (type 19)
starts with "CIB0"; its table is not decoded. `cutin` marks a bad magic,
a BMT1 header, or a BMT1 size that is not 0x10 + n x 0x40 with !!, and
reports how many BMT1 blocks have a twelfth float that does not rise.

Writing: a block goes back into its entry at its own size, and the entry is PRSH
compressed again if it was (pac.prsh_wrap, greedy LZ77: other bytes than Sega's packer, the
same data), so only that entry's size can change; the pack is then laid out as the disc's
are (pac.build_kcap: every entry on a sector, the header holding each entry's end). `textures`
lists the texture blocks (PVMH archives, PVPL palettes) of a pack's entries; `replace` puts
pictures into PVMH blocks (or a file of the block's size into any block) and writes the new
header and data file; `roundtrip` puts every texture's own picture back and checks that
only texture bytes can differ and the pack still reads. The big face pack is streamed
entry by entry (1.1 GB).

`names` prints the NFN0 model name and the NSTL texture names of each
entry's first Ninja block. In FC_EURO_FACEPACK_01 they name the event
characters (REFREE_11.sno, STAFF_F_08.svr, ...); the developer SATO TEST
viewer's table in TESTPRG.REL 0x21d18 lists the same names by entry.
"""
import os
import struct
import sys
from collections import Counter

import pac

SAMPLE_LIMIT = 1000     # packs larger than this are sampled by `info`
SAMPLE_TARGET = 500     # ...down to about this many entries
BLOCK_ALIGN = 0x10
BLOCK_HEADER = 8        # u32 type, u32 size

EXT = {b"NSIF": ".nsif", b"PVMH": ".svm", b"PVPL": ".svp", b"PVRT": ".pvr",
       b"GBIX": ".svr"}


def table_pad(n):
    """Number of zero u32s between off[n-1] and the data base, as chosen by
    the switch on n % 4 in etc::PackData::GetPackBlock (0x11f5f8):
    n % 4 = 0, 1, 2, 3 -> pad 1, 0, 3, 2."""
    # The switch keeps n + pad + 1 == 2 (mod 4), so base % 16 == 8 and
    # each block's data (base + off + 8) starts 16-aligned.
    return (1 - n) % 4


def data_base(n):
    return 4 * (n + table_pad(n) + 1)


class PackData:
    """One expanded entry: count, base (where the blocks start), offsets
    and blocks, a list of (type, size, offset of the block's data). Raises
    ValueError when the table or a block runs past the end of buf."""

    def __init__(self, buf):
        if len(buf) < 4:
            raise ValueError("too short for a block count")
        self.count, = struct.unpack_from("<I", buf)
        self.base = data_base(self.count)
        if self.base > len(buf):
            raise ValueError("offset table (%d blocks) past end" % self.count)
        self.offsets = struct.unpack_from("<%dI" % self.count, buf, 4)
        self.blocks = []            # (type, size, data offset)
        for i, off in enumerate(self.offsets):
            o = self.base + off
            if o + BLOCK_HEADER > len(buf):
                raise ValueError("block %d header past end" % i)
            btype, size = struct.unpack_from("<II", buf, o)
            if o + BLOCK_HEADER + size > len(buf):
                raise ValueError("block %d data past end" % i)
            self.blocks.append((btype, size, o + BLOCK_HEADER))

    def problems(self, buf):
        out = []
        if any(buf[4 + 4 * self.count:self.base]):
            out.append("non-zero table padding")
        expect = 0
        for i, (off, (_, size, _)) in enumerate(zip(self.offsets, self.blocks)):
            if off != expect:
                out.append("block %d at %#x, expected %#x" % (i, off, expect))
            expect = off + ((BLOCK_HEADER + size + BLOCK_ALIGN - 1) & ~(BLOCK_ALIGN - 1))
        if any(buf[self.base + expect:]):
            out.append("non-zero bytes after the last block")
        return out


def type_signature(blocks):
    """Block types with runs collapsed: 0,16,16,16 -> '0,16x3'."""
    runs = []
    for t, _, _ in blocks:
        if runs and runs[-1][0] == t:
            runs[-1][1] += 1
        else:
            runs.append([t, 1])
    return ",".join(str(t) if n == 1 else "%dx%d" % (t, n) for t, n in runs)


def magic(data):
    m = data[:4]
    return m.decode("latin1") if all(32 <= c < 127 for c in m) else m.hex()


def read_entry(f, off, size):
    f.seek(off)
    raw = f.read(size)
    return pac.prsh_expand(raw) if raw[:4] == pac.PRSH_MAGIC else raw


def _kcap_headers(paths):
    for p in pac._walk(paths):
        try:
            h = pac.load_header(p)
        except (ValueError, struct.error):
            continue                # pac.py info reports broken headers
        if isinstance(h, pac.KcAtP):
            yield p, h


def _sample(count, check_all):
    if check_all or count <= SAMPLE_LIMIT:
        return list(range(count)), 1
    step = -(-count // SAMPLE_TARGET)
    idx = list(range(0, count, step))
    if idx[-1] != count - 1:
        idx.append(count - 1)
    return idx, step


# --- writing -------------------------------------------------------------------

TEXTURE_MAGICS = (b"PVMH", b"PVPL")


def texture_blocks(buf):
    """[(block index, magic, data offset, size)] of the texture blocks (PVMH archives and PVPL
    palettes) of an expanded entry."""
    return [(k, buf[o:o + 4], o, size) for k, (_, size, o) in enumerate(PackData(buf).blocks)
            if size and buf[o:o + 4] in TEXTURE_MAGICS]


def splice_blocks(buf, edits):
    """The expanded entry with blocks replaced: edits is {block index: new bytes}, each the size
    of the block it replaces (the packing rule, every block at the previous one's end rounded up
    to 16, is then kept as it is)."""
    pd = PackData(buf)
    out = bytearray(buf)
    for k, new in edits.items():
        if not 0 <= k < pd.count:
            raise ValueError("block %d of %d" % (k, pd.count))
        _, size, o = pd.blocks[k]
        if len(new) != size:
            raise ValueError("block %d is %d bytes, not %d" % (k, len(new), size))
        out[o:o + size] = new
    return bytes(out)


def rebuild_slot(slot, edits):
    """An entry's bytes as the pack stores them (the payload of `slot`, PRSH compressed again if
    it was) with `edits` ({block: bytes}) spliced in."""
    payload = pac.kcap_payload(slot)
    if payload[:4] == pac.PRSH_MAGIC:
        return pac.prsh_wrap(splice_blocks(pac.prsh_expand(payload), edits))
    return splice_blocks(payload, edits)


def write_pack(header_path, out_header, edits, progress=None):
    """Write a KC@P pack with entries changed: edits is {entry: {block: bytes}}. The new header is
    written to `out_header` and the data file, under its own name, beside it (as pac.py replace
    does); the pack is laid out as pac.build_kcap does, streamed an entry at a time. Returns
    (old size, new size) of the data file."""
    head = pac.load_header(header_path)
    if not isinstance(head, pac.KcAtP):
        raise ValueError("%s: not a KC@P header" % header_path)
    data_in = pac.data_path(header_path, head)
    out_data = os.path.join(os.path.dirname(os.path.abspath(out_header)), os.path.basename(data_in))
    if os.path.abspath(out_data) == os.path.abspath(data_in):
        raise ValueError("write to another folder than %s's" % header_path)
    for i in edits:
        if not 0 <= i < head.count:
            raise ValueError("entry %d of %d" % (i, head.count))
    ends = []
    with open(data_in, "rb") as src, open(out_data, "wb") as dst:
        for i, (off, size, _, _) in enumerate(head.entries):
            src.seek(off)
            slot = src.read(size)
            blob = rebuild_slot(slot, edits[i]) if i in edits else pac.kcap_payload(slot)
            dst.write(blob + bytes(-len(blob) % pac.KCAP_SECTOR))
            ends.append(dst.tell())
            if progress:
                progress(i)
        total = dst.tell()
    new_head = pac.KCAP_MAGIC + struct.pack("<III%dI" % len(ends), total, len(ends), 0, *ends)
    with open(out_header, "wb") as f:
        f.write(new_head)
    return os.path.getsize(data_in), total


def picture_edits(header_path, pictures, keep_palette=False):
    """{entry: {block: bytes}} for pictures put into PVMH blocks: pictures is
    {(entry, block, texture): RGBA pixels at the texture's size} (svr.replace_pictures)."""
    import svr
    head = pac.load_header(header_path)
    out = {}
    with open(pac.data_path(header_path, head), "rb") as f:
        groups = {}
        for (i, k, slot), px in pictures.items():
            groups.setdefault((i, k), {})[slot] = px
        for (i, k), pics in groups.items():
            off, size, _, _ = head.entries[i]
            buf = read_entry(f, off, size)
            _, bsize, o = PackData(buf).blocks[k]
            raw = buf[o:o + bsize]
            if raw[:4] != b"PVMH":
                raise ValueError("entry %d block %d is not a PVMH archive" % (i, k))
            out.setdefault(i, {})[k] = svr.replace_pictures(raw, pics, "%d.%d" % (i, k), keep_palette)
    return out


# --- commands ----------------------------------------------------------------

def cmd_textures(path, first=0, last=None):
    import svr
    head = pac.load_header(path)
    if not isinstance(head, pac.KcAtP):
        raise SystemExit("%s: not a KC@P header" % path)
    last = head.count - 1 if last is None else last
    n = 0
    with open(pac.data_path(path, head), "rb") as f:
        for i in range(first, last + 1):
            off, size, _, _ = head.entries[i]
            buf = read_entry(f, off, size)
            for k, mg, o, bsize in texture_blocks(buf):
                if mg == b"PVMH":
                    texs = svr.parse_svm(buf[o:o + bsize])
                    what = ", ".join("%dx%d %dbpp" % (t.width, t.height, t.bpp) for t in texs[:4])
                    what = "%d texture%s  %s%s" % (len(texs), "" if len(texs) == 1 else "s", what,
                                                  " ..." if len(texs) > 4 else "")
                else:
                    what = "palette"
                print("%6d.%-3d %s %8d bytes  %s" % (i, k, mg.decode(), bsize, what))
                n += 1
    print("%d texture blocks in entries %d-%d" % (n, first, last))


def cmd_replace(src, dst, pairs, keep_palette, prs):
    head = pac.load_header(src)
    if not isinstance(head, pac.KcAtP):
        raise SystemExit("%s: not a KC@P header" % src)
    pictures, files = {}, {}
    for pair in pairs:
        sel, sep, path = pair.partition("=")
        parts = sel.split(".")
        if not sep or len(parts) not in (2, 3) or not all(x.isdigit() for x in parts):
            raise SystemExit("expected <entry>.<block>[.<texture>]=<file>, got %r" % pair)
        i, k = int(parts[0]), int(parts[1])
        if len(parts) == 3 or path.lower().endswith(".png"):
            from PIL import Image
            import svr
            with open(pac.data_path(src, head), "rb") as f:
                off, size, _, _ = head.entries[i]
                buf = read_entry(f, off, size)
            _, bsize, o = PackData(buf).blocks[k]
            slot = int(parts[2]) if len(parts) == 3 else 0
            tex = svr.parse_svm(buf[o:o + bsize])[slot]
            img = Image.open(path).convert("RGBA")
            if img.size != (tex.width, tex.height):
                raise SystemExit("%s is %dx%d, the texture %dx%d; scale it first" % (
                    path, img.width, img.height, tex.width, tex.height))
            pictures[i, k, slot] = list(img.get_flattened_data() if hasattr(img, "get_flattened_data")
                                        else img.getdata())
        else:
            with open(path, "rb") as f:
                files.setdefault(i, {})[k] = f.read()
        print("%d.%d <- %s" % (i, k, path))
    edits = picture_edits(src, pictures, keep_palette) if pictures else {}
    for i, blocks in files.items():
        edits.setdefault(i, {}).update(blocks)
    old, new = write_pack(src, dst, edits)
    print("%s: %d entries changed; data file %d -> %d bytes (%d -> %d sectors)" % (
        dst, len(edits), old, new, old >> 11, new >> 11))


def cmd_roundtrip(paths, everything):
    """For each KC@P pack: every texture block's own pictures put back (matched to their own
    palettes), the entry re-spliced, and the pack read again: only texture bytes may differ and
    every picture must decode the same. Entries of the big packs are sampled like `info`'s."""
    import svr
    bad = 0
    for path, head in _kcap_headers(paths):
        idx, step = _sample(head.count, everything)
        blocks = textures = changed = 0
        with open(pac.data_path(path, head), "rb") as f:
            for i in idx:
                off, size, _, _ = head.entries[i]
                buf = read_entry(f, off, size)
                edits = {}
                for k, mg, o, bsize in texture_blocks(buf):
                    blocks += 1
                    if mg != b"PVMH":
                        continue
                    raw = buf[o:o + bsize]
                    texs = svr.parse_svm(raw)
                    pics = {j: t.pixels() for j, t in enumerate(texs) if t.palette_entries or t.bpp >= 16}
                    if not pics:
                        continue
                    try:
                        new = svr.replace_pictures(raw, pics, "%d.%d" % (i, k), keep_palette=True)
                    except ValueError as e:
                        print("%s entry %d block %d  !! %s" % (os.path.basename(path), i, k, e))
                        bad += 1
                        continue
                    again = svr.parse_svm(new)
                    for j, px in pics.items():
                        textures += 1
                        if again[j].pixels() != px:
                            print("%s entry %d block %d texture %d  !! the picture changed" % (
                                os.path.basename(path), i, k, j))
                            bad += 1
                    edits[k] = new
                if edits:
                    out = splice_blocks(buf, edits)
                    pd = PackData(out)
                    if len(out) != len(buf) or pd.problems(out):
                        print("%s entry %d  !! the rebuilt entry does not read as the packing rule says" % (
                            os.path.basename(path), i))
                        bad += 1
                    masked_a, masked_b = bytearray(buf), bytearray(out)
                    for k in edits:
                        _, bsize, o = pd.blocks[k]
                        masked_a[o:o + bsize] = masked_b[o:o + bsize] = bytes(bsize)
                    if masked_a != masked_b:
                        print("%s entry %d  !! bytes outside the textures changed" % (os.path.basename(path), i))
                        bad += 1
                    changed += 1
        note = "" if step == 1 else " (every %dth entry and the last, of %d)" % (step, head.count)
        print("%-40s %d entries%s: %d texture blocks, %d pictures put back, %d entries respliced%s" % (
            path.replace("\\", "/"), len(idx), note, blocks, textures, changed, ""))
    print("%s" % ("  !! %d problems" % bad if bad else "no problems"))
    return 1 if bad else 0

def cmd_info(paths, check_all):
    for p, h in _kcap_headers(paths):
        dp = pac.data_path(p, h)
        if dp is None:
            print("%-50s !! no data file" % p)
            continue
        idx, step = _sample(h.count, check_all)
        shapes, empty, bad = Counter(), 0, []
        with open(dp, "rb") as f:
            for i in idx:
                off, size, _, _ = h.entries[i]
                if size == 0:
                    empty += 1
                    continue
                try:
                    buf = read_entry(f, off, size)
                    pd = PackData(buf)
                except (ValueError, struct.error) as e:
                    bad.append((i, [str(e)]))
                    continue
                shapes[type_signature(pd.blocks)] += 1
                probs = pd.problems(buf)
                if probs:
                    bad.append((i, probs))
        checked = "%d of %d (every %dth + last)" % (len(idx), h.count, step) \
            if step > 1 else "%d" % h.count
        print("%-50s PackData checked=%s empty=%d" % (p, checked, empty))
        for sig, n in sorted(shapes.items(), key=lambda kv: (-kv[1], kv[0])):
            print("    %5d  types %s" % (n, sig))
        for i, probs in bad:
            print("  !! entry %d: %s" % (i, "; ".join(probs)))


def cmd_list(path, index):
    h = pac.load_header(path)
    if not isinstance(h, pac.KcAtP):
        raise SystemExit("%s: not a KC@P header" % path)
    off, size, _, _ = h.entries[index]
    with open(pac.data_path(path, h), "rb") as f:
        buf = read_entry(f, off, size)
    pd = PackData(buf)
    print("entry %d: %d bytes, %d blocks, base %#x" % (index, len(buf), pd.count, pd.base))
    for i, (btype, bsize, d) in enumerate(pd.blocks):
        print("%4d  type %3d  %#8x  %8d  %s" % (i, btype, d, bsize,
                                                magic(buf[d:d + 4]) if bsize else "-"))


def cmd_extract(path, index, outdir):
    h = pac.load_header(path)
    if not isinstance(h, pac.KcAtP):
        raise SystemExit("%s: not a KC@P header" % path)
    off, size, _, _ = h.entries[index]
    with open(pac.data_path(path, h), "rb") as f:
        buf = read_entry(f, off, size)
    os.makedirs(outdir, exist_ok=True)
    for i, (btype, bsize, d) in enumerate(PackData(buf).blocks):
        data = buf[d:d + bsize]
        name = "%d_%02d_t%d%s" % (index, i, btype, EXT.get(data[:4], ".bin"))
        with open(os.path.join(outdir, name), "wb") as f:
            f.write(data)
        print(os.path.join(outdir, name))


def cmd_names(path, first=0, last=None):
    import ninja
    h = pac.load_header(path)
    if not isinstance(h, pac.KcAtP):
        raise SystemExit("%s: not a KC@P header" % path)
    last = len(h.entries) - 1 if last is None else last
    with open(pac.data_path(path, h), "rb") as f:
        for index in range(first, last + 1):
            off, size, _, _ = h.entries[index]
            buf = read_entry(f, off, size)
            model, textures = "-", []
            for _, bsize, d in PackData(buf).blocks:
                if buf[d:d + 4] != b"NSIF":
                    continue
                nf = ninja.NinjaFile(buf[d:d + bsize])
                for tag, coff, csize in nf.chunks:
                    if tag == b"NFN0":
                        model = nf.buf[coff + 0x10:coff + 8 + csize].rstrip(b"\0").decode("cp932")
                    elif tag == b"NSTL":
                        textures = ninja.texture_names(nf, nf.main_struct((tag, coff, csize)))
                break
            print("%5d  %-24s %s" % (index, model, " ".join(textures) or "-"))


BMT1_TYPE, CIB0_TYPE = 23, 19
BMT1_POINT = 0x40
BMT1_TIME = 11          # the float of a point that looks like a frame time


def cmd_cutin(path):
    """Check every CIB0 and BMT1 block of a KC@P pack, and print the totals."""
    h = pac.load_header(path)
    if not isinstance(h, pac.KcAtP):
        raise SystemExit("%s: not a KC@P header" % path)
    cib = bmt = points = dips = 0
    with open(pac.data_path(path, h), "rb") as f:
        for i, (off, size, _, _) in enumerate(h.entries):
            buf = read_entry(f, off, size)
            for bi, (btype, bsize, d) in enumerate(PackData(buf).blocks):
                if btype not in (CIB0_TYPE, BMT1_TYPE) or not bsize:
                    continue
                b = buf[d:d + bsize]
                where = "entry %d block %d" % (i, bi)
                if btype == CIB0_TYPE:
                    cib += 1
                    if b[:4] != b"CIB0":
                        print("%s  CIB0  !! bad magic %r" % (where, b[:4]))
                    continue
                bmt += 1
                problems = []
                magic4, start, n, zero = struct.unpack_from("<4sIII", b, 0)
                if magic4 != b"BMT1" or start != 0x10 or zero:
                    problems.append("header %r %#x %d %d" % (magic4, start, n, zero))
                elif bsize != start + n * BMT1_POINT:
                    problems.append("size %d is not %#x + %d x %#x" % (bsize, start, n, BMT1_POINT))
                else:
                    times = [struct.unpack_from("<f", b, start + p * BMT1_POINT + 4 * BMT1_TIME)[0]
                             for p in range(n)]
                    points += n
                    if times != sorted(times):
                        dips += 1
                print("%s  BMT1  points=%d%s" % (where, n, "  !! " + "; ".join(problems) if problems else ""))
    print("%s  CIB0 blocks=%d  BMT1 blocks=%d  points=%d  BMT1 blocks whose 12th float dips=%d" % (
        path, cib, bmt, points, dips))


def main(argv):
    args = [a for a in argv[2:] if a != "--all"]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "cutin" and len(args) == 1:
        cmd_cutin(args[0])
    elif cmd == "info" and args:
        cmd_info(args, "--all" in argv)
    elif cmd == "list" and len(args) == 2:
        cmd_list(args[0], int(args[1], 0))
    elif cmd == "extract" and len(args) == 3:
        cmd_extract(args[0], int(args[1], 0), args[2])
    elif cmd == "names" and 1 <= len(args) <= 3:
        cmd_names(args[0], *(int(a, 0) for a in args[1:]))
    elif cmd == "textures" and 1 <= len(args) <= 3:
        cmd_textures(args[0], *(int(a, 0) for a in args[1:]))
    elif cmd == "roundtrip" and args:
        return cmd_roundtrip(args, "--all" in argv)
    elif cmd == "replace" and len(args) >= 3:
        keep = "--palette" in args and args[args.index("--palette") + 1] == "keep"
        rest = [a for k, a in enumerate(args) if a not in ("--palette", "--prs") and (k == 0 or args[k - 1] != "--palette")]
        cmd_replace(rest[0], rest[1], rest[2:], keep, "--prs" in args)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
