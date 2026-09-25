"""TBB1/TBL1 table container reader for Let's Make a Soccer Team! (PS2).

A .TBB file is a small container of one or more TBL1 tables of raw,
fixed-width binary rows. The layout was confirmed against the game's own
accessors in SLES_541.51 (TbbData::GetTableDataPtr,
TblData::CTblData::GetDataTable1LineSize, ...) - see DOC/TBB_FORMAT.md.

The container carries no column types; each table is just
`size` bytes cut into `line_size`-byte rows. Row schemas live in the
game code that consumes each table.

Usage:
    python tbb.py info    <file.TBB | dir> ...
    python tbb.py dump    <file.TBB> [table_index] [--rows N]
    python tbb.py extract <file.TBB> <out_dir>
"""
import os
import struct
import sys

TBB_MAGIC = b"TBB1"
TBL_MAGIC = b"TBL1"


class Table:
    def __init__(self, index, offset, data_offset, size, line_size, data):
        self.index = index
        self.offset = offset            # of the TBL1 header, from file start
        self.data_offset = data_offset  # relative to the TBL1 header
        self.size = size
        self.line_size = line_size
        self.data = data

    @property
    def row_count(self):
        # Matches GetDataTableCount: integer size / line_size.
        return self.size // self.line_size if self.line_size else 0

    def rows(self):
        n = self.line_size
        for i in range(self.row_count):
            yield self.data[i * n:(i + 1) * n]


def parse(buf):
    magic, offs_ofs, count, total = struct.unpack_from("<4sIII", buf, 0)
    if magic != TBB_MAGIC:
        raise ValueError("not a TBB1 file (magic %r)" % magic)
    offsets = struct.unpack_from("<%dI" % count, buf, offs_ofs)
    tables = []
    for i, ofs in enumerate(offsets):
        tmagic, data_ofs, size, line_size = struct.unpack_from("<4sIII", buf, ofs)
        if tmagic != TBL_MAGIC:
            raise ValueError("table %d at %#x: bad magic %r" % (i, ofs, tmagic))
        start = ofs + data_ofs
        tables.append(Table(i, ofs, data_ofs, size, line_size, buf[start:start + size]))
    return total, tables


def load(path):
    with open(path, "rb") as f:
        return parse(f.read())


def _iter_paths(args):
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for name in sorted(files):
                    if name.upper().endswith(".TBB"):
                        yield os.path.join(root, name)
        else:
            yield a


def cmd_info(paths):
    for path in _iter_paths(paths):
        total, tables = load(path)
        print("%s  tables=%d  total=%#x" % (path, len(tables), total))
        for t in tables:
            rem = t.size % t.line_size if t.line_size else 0
            print("  [%3d] @%#07x  size=%6d  line=%4d  rows=%5d%s" % (
                t.index, t.offset, t.size, t.line_size, t.row_count,
                "  (+%d trailing bytes)" % rem if rem else ""))


def _hexrow(b):
    return " ".join("%02x" % x for x in b)


def cmd_dump(path, index=None, max_rows=None):
    _, tables = load(path)
    for t in tables:
        if index is not None and t.index != index:
            continue
        print("== table %d: %d rows x %d bytes" % (t.index, t.row_count, t.line_size))
        for r, row in enumerate(t.rows()):
            if max_rows is not None and r >= max_rows:
                print("  ...")
                break
            text = "".join(chr(c) if 32 <= c < 127 else "." for c in row)
            print("  %5d: %s  |%s|" % (r, _hexrow(row), text))


def cmd_extract(path, out_dir):
    _, tables = load(path)
    base = os.path.splitext(os.path.basename(path))[0]
    os.makedirs(out_dir, exist_ok=True)
    for t in tables:
        out = os.path.join(out_dir, "%s_%03d_L%d.bin" % (base, t.index, t.line_size))
        with open(out, "wb") as f:
            f.write(t.data)
        print(out)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args)
    elif cmd == "dump":
        max_rows = None
        if "--rows" in args:
            i = args.index("--rows")
            max_rows = int(args[i + 1])
            del args[i:i + 2]
        cmd_dump(args[0], int(args[1]) if len(args) > 1 else None, max_rows)
    elif cmd == "extract":
        cmd_extract(args[0], args[1])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
