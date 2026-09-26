"""TBB1/TBL1 table container reader for Let's Make a Soccer Team! (PS2).

A .TBB file is a small container of one or more TBL1 tables of raw,
fixed-width binary rows. The layout was confirmed against the game's own
accessors in SLES_541.51 (TbbData::GetTableDataPtr,
TblData::CTblData::GetDataTable1LineSize, ...) - see DOC/TBB_FORMAT.md.

The container carries no column types; each table is just
`size` bytes cut into `line_size`-byte rows. Row schemas live in the
game code that consumes each table.

The commentary files (GAME/*.BCR, *.BCB, and the start of SOUNDDAT.PAC)
reuse the TBB1 container for other table types: BCR2 and BCB3 share the
{magic, data_offset, size, u32} header but the last field is not a line
size (see DOC/GAME_DIR.md). Those are listed with their magic and dumped
as raw hex.

build() writes a container back out: the header, the offset array padded
to 16 bytes, then each table header and its data padded to 16 bytes, as
the documented layout says. Every file on the disc rebuilds byte for byte
(`roundtrip`). The two ROUTEBOX_*.BCR files carry a 0x350-byte `RBD0`
trailer after the last table, which is kept as-is.

Usage:
    python tbb.py info      <file.TBB|.BCR|.BCB | dir> ...
    python tbb.py dump      <file.TBB> [table_index] [--rows N]
    python tbb.py extract   <file.TBB> <out_dir>
    python tbb.py roundtrip <file.TBB|.BCR|.BCB | dir> ...      # rebuild each file, !! if not identical
    python tbb.py replace   <file.TBB> <table_index> <table.bin> <out.TBB>

`replace` swaps one table's data for the contents of <table.bin> (as written
by `extract`) and keeps everything else, including the table's line size.
The data may change length; later tables move along.
"""
import os
import struct
import sys

TBB_MAGIC = b"TBB1"
TBL_MAGIC = b"TBL1"
HEADER_SIZE = 0x10     # TBB_FILEHEADER before the offset array, and each TBL1 header
ALIGN = 0x10           # offset array, each table and the file end on 16 bytes


class Table:
    def __init__(self, index, offset, data_offset, size, line_size, data, magic=TBL_MAGIC):
        self.index = index
        self.magic = magic              # TBL1, or BCR2/BCB3 in the commentary files
        self.offset = offset            # of the TBL1 header, from file start
        self.data_offset = data_offset  # relative to the TBL1 header
        self.size = size
        self.line_size = line_size
        self.data = data

    @property
    def row_count(self):
        # Matches GetDataTableCount: integer size / line_size.
        if self.magic != TBL_MAGIC or not self.line_size:
            return 0
        return self.size // self.line_size

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
        if not (tmagic.isalnum() and tmagic.isascii()):
            raise ValueError("table %d at %#x: bad magic %r" % (i, ofs, tmagic))
        start = ofs + data_ofs
        tables.append(Table(i, ofs, data_ofs, size, line_size, buf[start:start + size], tmagic))
    return total, tables


def load(path):
    with open(path, "rb") as f:
        return parse(f.read())


def _align(n):
    return (n + ALIGN - 1) // ALIGN * ALIGN


def build(tables, end=None, trailer=b""):
    """Write a TBB1 container. `end` is the header's end-of-data field: None
    computes it (the unpadded end of the last table's data); pass the parsed
    value to keep files where it is 0. `trailer` is appended after the
    padded last table."""
    out = bytearray(_align(HEADER_SIZE + 4 * len(tables)))
    offsets = []
    data_end = len(out)
    for t in tables:
        offsets.append(len(out))
        # The game only reads the line size of TBL1 tables; BCR2/BCB3 keep
        # whatever their +0x0C field held.
        out += struct.pack("<4sIII", t.magic, HEADER_SIZE, len(t.data), t.line_size)
        out += t.data
        data_end = len(out)
        out += bytes(_align(len(out)) - len(out))
    struct.pack_into("<4sIII", out, 0, TBB_MAGIC, HEADER_SIZE, len(tables),
                     data_end if end is None else end)
    struct.pack_into("<%dI" % len(tables), out, HEADER_SIZE, *offsets)
    return bytes(out) + trailer


def trailer(buf, tables):
    """Bytes after the last table's padded data (the RBD0 block in the
    ROUTEBOX_*.BCR files; empty everywhere else)."""
    if not tables:
        return buf[_align(HEADER_SIZE):]
    last = tables[-1]
    return buf[_align(last.offset + last.data_offset + last.size):]


def _iter_paths(args):
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for name in sorted(files):
                    if name.upper().endswith((".TBB", ".BCR", ".BCB")):
                        yield os.path.join(root, name)
        else:
            yield a


def cmd_info(paths):
    for path in _iter_paths(paths):
        try:
            total, tables = load(path)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            continue
        print("%s  tables=%d  total=%#x" % (path, len(tables), total))
        for t in tables:
            if t.magic != TBL_MAGIC:
                print("  [%3d] @%#07x  size=%6d  %s  field@0xC=%d" % (
                    t.index, t.offset, t.size, t.magic.decode(), t.line_size))
                continue
            rem = t.size % t.line_size if t.line_size else 0
            print("  [%3d] @%#07x  size=%6d  line=%4d  rows=%5d%s" % (
                t.index, t.offset, t.size, t.line_size, t.row_count,
                "  !! %d trailing bytes" % rem if rem else ""))


def _hexrow(b):
    return " ".join("%02x" % x for x in b)


def cmd_dump(path, index=None, max_rows=None):
    _, tables = load(path)
    for t in tables:
        if index is not None and t.index != index:
            continue
        if t.magic != TBL_MAGIC:
            print("== table %d: %s, %d bytes (raw)" % (t.index, t.magic.decode(), t.size))
            rows = (t.data[i:i + 16] for i in range(0, t.size, 16))
        else:
            print("== table %d: %d rows x %d bytes" % (t.index, t.row_count, t.line_size))
            rows = t.rows()
        for r, row in enumerate(rows):
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
        if t.magic == TBL_MAGIC:
            out = os.path.join(out_dir, "%s_%03d_L%d.bin" % (base, t.index, t.line_size))
        else:
            out = os.path.join(out_dir, "%s_%03d_%s.bin" % (base, t.index, t.magic.decode()))
        with open(out, "wb") as f:
            f.write(t.data)
        print(out)


def cmd_roundtrip(paths):
    ok = bad = 0
    for path in _iter_paths(paths):
        try:
            with open(path, "rb") as f:
                buf = f.read()
            end, tables = parse(buf)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            bad += 1
            continue
        tail = trailer(buf, tables)
        out = build(tables, end, tail)
        note = "  trailer %#x" % len(tail) if tail else ""
        if out == buf:
            ok += 1
            print("%s  %d bytes  identical%s" % (path, len(buf), note))
            continue
        bad += 1
        diff = next((i for i in range(min(len(out), len(buf))) if out[i] != buf[i]), None)
        where = "first difference at %#x" % diff if diff is not None             else "length %d, rebuilt %d" % (len(buf), len(out))
        print("%s  %d bytes%s  !! rebuilt file differs: %s" % (path, len(buf), note, where))
    print("%d identical, %d differ" % (ok, bad))


def cmd_replace(path, index, blob_path, out_path):
    with open(path, "rb") as f:
        buf = f.read()
    end, tables = parse(buf)
    if not 0 <= index < len(tables):
        raise ValueError("table %d out of range (file has %d)" % (index, len(tables)))
    with open(blob_path, "rb") as f:
        data = f.read()
    t = tables[index]
    old = t.size
    t.data, t.size = data, len(data)
    # Keep a zero end field zero; otherwise recompute it for the new layout.
    out = build(tables, 0 if end == 0 else None, trailer(buf, tables))
    with open(out_path, "wb") as f:
        f.write(out)
    print("%s: table %d %d -> %d bytes, file %d -> %d bytes" % (
        out_path, index, old, len(data), len(buf), len(out)))
    if t.magic == TBL_MAGIC and t.line_size and len(data) % t.line_size:
        print("warning: %d bytes is not a whole number of %d-byte lines" % (len(data), t.line_size))


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
    elif cmd == "roundtrip":
        cmd_roundtrip(args)
    elif cmd == "replace" and len(args) == 4:
        cmd_replace(args[0], int(args[1], 0), args[2], args[3])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
