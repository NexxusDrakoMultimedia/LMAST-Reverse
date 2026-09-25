"""Dump the EvsDataBin_{EVENT,NEWS,MAIL}.bin event tables to CSV.

Headerless arrays of little-endian u32 records (EVENT 272 bytes, NEWS
192, MAIL 112), loaded by DLL/SIMPRG.REL. EVENT columns get the names
worked out in DOC/EVSDATABIN_FORMAT.md; unknown columns are named by
offset, e.g. `u_0c`.

Message references (u32 = category << 16 | id, see DOC/MBB_FORMAT.md) are
written as `category:id`. With --text, each one also gets a `<name>_text`
column holding the message from MES.PAC.

Usage:
    python evsdatabin.py <EVSDATABIN_*.BIN> [out.csv] [--all] [--text MES.PAC] [--lang N]

--all keeps columns that are zero in every record. --lang picks the
language for --text (default 1, English; see mbb.py).
"""
import csv
import os
import struct
import sys

RECORD_SIZES = {"EVENT": 272, "NEWS": 192, "MAIL": 112}

# Name prefixes: '-' marks a signed field, '@' a message reference.

# Offset -> name for EVENT records. Signed fields are marked with a
# leading '-'.
EVENT_FIELDS = {
    0x00: "index",
    0x04: "always_key",
    0x08: "handler_type",
    0x10: "actor_class",
    0x18: "actor2",
    0x64: "@message",
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

NEWS_FIELDS = {
    0x00: "index",
    0x64: "@body",
    0x6c: "@headline",
    0x78: "weight",
}

MAIL_FIELDS = {
    0x00: "index",
    0x10: "@sender",
    0x14: "@recipient",
    0x20: "@subject",
    0x24: "@body",
    0x5c: "weight",
}

FIELDS = {"EVENT": EVENT_FIELDS, "NEWS": NEWS_FIELDS, "MAIL": MAIL_FIELDS}


def kind_of(path):
    name = os.path.basename(path).upper()
    for k in RECORD_SIZES:
        if k in name:
            return k
    raise ValueError("can't tell EVENT/NEWS/MAIL from %r" % path)


def columns(kind, size):
    names = FIELDS[kind]
    cols = []
    for ofs in range(0, size, 4):
        name = names.get(ofs, "u_%02x" % ofs)
        fmt = {"-": "<i", "@": "msg"}.get(name[0], "<I")
        cols.append((ofs, name.lstrip("-@"), fmt))
    return cols


def msg_ref(v):
    return "%d:%d" % (v >> 16, v & 0xFFFF) if v else 0


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
        row = {}
        for ofs, name, fmt in cols:
            if fmt == "msg":
                row[name] = msg_ref(struct.unpack_from("<I", data, base + ofs)[0])
            else:
                row[name] = struct.unpack_from(fmt, data, base + ofs)[0]
        rows.append(row)
    return kind, [c[1] for c in cols], rows, [c[1] for c in cols if c[2] == "msg"]


def add_text(names, rows, msg_cols, mes_path, lang):
    """Add a `<col>_text` column after each message column."""
    import mbb
    table = {}
    for _, m in mbb.iter_files([mes_path]):
        if m.lang == lang:
            for rid, s in m.records:
                table.setdefault((m.category, rid), mbb.decode(s, lang))
    for row in rows:
        for c in msg_cols:
            if row[c]:
                cat, rid = map(int, row[c].split(":"))
                row[c + "_text"] = table.get((cat, rid), "")
    out = []
    for n in names:
        out.append(n)
        if n in msg_cols:
            out.append(n + "_text")
    return out


def _opt(args, flag):
    if flag in args:
        k = args.index(flag)
        v = args[k + 1]
        del args[k:k + 2]
        return v
    return None


def main(argv):
    args = [a for a in argv[1:] if a != "--all"]
    mes, lang = _opt(args, "--text"), int(_opt(args, "--lang") or 1)
    if not args:
        print(__doc__)
        return 1
    _, names, rows, msg_cols = load(args[0])
    if "--all" not in argv:
        names = [n for n in names if n == "index" or any(r[n] for r in rows)]
    if mes:
        names = add_text(names, rows, msg_cols, mes, lang)
    if len(args) > 1:
        out = open(args[1], "w", newline="", encoding="utf-8-sig" if mes else None)
    else:
        out = sys.stdout
        if mes and hasattr(out, "reconfigure"):
            out.reconfigure(encoding="utf-8")
    w = csv.DictWriter(out, fieldnames=names, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
