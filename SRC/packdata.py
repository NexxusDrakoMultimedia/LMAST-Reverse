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


# --- commands ----------------------------------------------------------------

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


def main(argv):
    args = [a for a in argv[2:] if a != "--all"]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and args:
        cmd_info(args, "--all" in argv)
    elif cmd == "list" and len(args) == 2:
        cmd_list(args[0], int(args[1], 0))
    elif cmd == "extract" and len(args) == 3:
        cmd_extract(args[0], int(args[1], 0), args[2])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
