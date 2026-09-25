"""Dump the EvsDataBin_{EVENT,NEWS,MAIL}.bin event tables to CSV.

Headerless arrays of little-endian u32 records (EVENT 272 bytes, NEWS
192, MAIL 112), loaded by DLL/SIMPRG.REL. EVENT columns get the names
worked out in DOC/EVSDATABIN_FORMAT.md; unknown columns (and all of
NEWS/MAIL for now) are named by offset, e.g. `u_0c`.

Usage:
    python evsdatabin.py <EVSDATABIN_*.BIN> [out.csv] [--all]

--all keeps columns that are zero in every record.
"""
import csv
import os
import struct
import sys

RECORD_SIZES = {"EVENT": 272, "NEWS": 192, "MAIL": 112}

# Offset -> name for EVENT records. Signed fields are marked with a
# leading '-'.
EVENT_FIELDS = {
    0x00: "index",
    0x04: "always_key",
    0x08: "handler_type",
    0x10: "actor_class",
    0x18: "actor2",
    0x68: "-timing",
    0x6c: "weight",
    0x70: "once_only",
    0x74: "forbidden_flag",
    0x78: "cooldown_class",
    0x7c: "min_season",
    0x80: "season_pattern",
    0x84: "date_pattern_a",
    0x88: "date_pattern_b",
    0x8c: "cond1_kind",
    0x90: "cond1_arg",
    0x94: "cond2_kind",
    0x98: "cond2_arg",
    0x9c: "req_flag1",
    0xa0: "req_flag2",
    0xa4: "date_rule_arg",
    0xa8: "-date_rule_kind",
    0xb0: "chance_pct",
    0xb4: "effect1_kind",
    0xb8: "-effect1_value",
    0xbc: "effect2_kind",
    0xc0: "-effect2_value",
    0xc4: "effect3_kind",
    0xc8: "-effect3_value",
    0xcc: "effect4_kind",
    0xd0: "-effect4_value",
    0xd8: "set_flag",
    0xe0: "scene_type",
    0xe8: "scene_type_alt_a",
    0xec: "scene_type_alt_b",
    0xf0: "scene_type_var0",
    0xf4: "scene_type_var1",
    0xf8: "scene_type_var2",
    0xfc: "scene_type_var3",
    0x100: "scene_type_var4",
    0x104: "scene_type_var5",
}


def kind_of(path):
    name = os.path.basename(path).upper()
    for k in RECORD_SIZES:
        if k in name:
            return k
    raise ValueError("can't tell EVENT/NEWS/MAIL from %r" % path)


def columns(kind, size):
    names = EVENT_FIELDS if kind == "EVENT" else {0: "index"}
    cols = []
    for ofs in range(0, size, 4):
        name = names.get(ofs, "u_%02x" % ofs)
        signed = name.startswith("-")
        cols.append((ofs, name.lstrip("-"), "<i" if signed else "<I"))
    return cols


def load(path):
    kind = kind_of(path)
    size = RECORD_SIZES[kind]
    with open(path, "rb") as f:
        data = f.read()
    if len(data) % size:
        raise ValueError("%s: %d bytes is not a multiple of %d" % (path, len(data), size))
    cols = columns(kind, size)
    rows = []
    for i in range(len(data) // size):
        base = i * size
        rows.append({name: struct.unpack_from(fmt, data, base + ofs)[0] for ofs, name, fmt in cols})
    return kind, [c[1] for c in cols], rows


def main(argv):
    args = [a for a in argv[1:] if a != "--all"]
    if not args:
        print(__doc__)
        return 1
    _, names, rows = load(args[0])
    if "--all" not in argv:
        names = [n for n in names if n == "index" or any(r[n] for r in rows)]
    out = open(args[1], "w", newline="") if len(args) > 1 else sys.stdout
    w = csv.DictWriter(out, fieldnames=names, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
