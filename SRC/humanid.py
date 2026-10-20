# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for BG/HUMANID.BIN, the human database of Let's Make a Soccer
Team! (PS2): which person (outfit) the club-house scenes show for a role.

The file is a plain array of 10-byte records, one per human id (323 on
the disc). CHumanDataBase::search(id, result, arg) (SLES 0x2d3ea0) reads
record id:

    +0  s8     search function, -1 = none: an index into the 38 function
               pointers the constructor (0x2d3d08) stores at this + 8;
               called as fn(result, arg)
    +1  s8[3]  objects for a warm day (19 degrees C or more)
    +4  s8[3]  objects for a mild day (6 to 18 degrees C)
    +7  s8     object for a cold day (below 6 degrees C)
    +8  s16    copied to result + 0 when not negative

The temperature is plCity_GetTemperature for the club's city on today's
date. For a warm or mild day the game picks one of the group's objects at
random (fcEuroRand_Get0toI), counting only the leading ones that aren't
negative. The object id indexes s_aHumanDataBase_ObjectDataBase (SLES
0x3a2470), 8 bytes {u32 kind, u32 index} per object, which search copies
to result + 4 and + 8 (getObjectData, 0x2d4090, reads the same table).

SIMPRG.REL loads the file (folder 14) and hands it to
CHumanDataBase::setup (0x2d3e98, called at SIMPRG.REL 0x7d7c), which
only keeps the pointer. Copies sit in PRELOAD/SIMFILE0-6.PAC. See
DOC/BG_DIR.md#humanidbin.

Usage:
    python humanid.py info    <file | .PAC | dir> ...   # check every HUMANID.BIN (and PAC copy)
    python humanid.py dump    <HUMANID.BIN> [<ISO dir>] # one line per record (ISO: with each object's kind, index)
    python humanid.py objects <ISO dir>                 # the executable's object table
"""
import os
import struct
import sys

from pac import BinPac
import gamever

NAME = "HUMANID.BIN"
REC = struct.Struct("<b3b3bbh")
REC_SIZE = REC.size     # 10: the search multiplies the id by 10 (0x2d3ee4)

# The search functions, by the slot the constructor (0x2d3d08) gives them;
# every other slot of the 38 holds HumanSearch::Dummy (0x2d40b8), which
# returns 1 and does nothing.
FUNCTION_COUNT = 38
FUNCTIONS = {
    19: "Player_PlainCloth",
    30: "Staff_M_Rand",
    31: "Staff_F_Rand",
    32: "Secretary_My",
    33: "Manager_My",
    34: "YouthManager_My",
    35: "Agent",
    36: "NazoCoach",
    37: "YouthRand",
}

# s_aHumanDataBase_ObjectDataBase: {u32 kind, u32 index} per object.
# Nothing in the code bounds it; 112 entries is the highest id the file
# uses + 1, and entry 112 onwards ({0, 1}, {6, 7}, {8, 9}, ...) is a
# different table.
OBJECT_TABLE = 0x3a2470
OBJECT_COUNT = 112

SEASONS = (("warm", 1, 3), ("mild", 4, 3), ("cold", 7, 1))


def parse(d):
    if len(d) % REC_SIZE:
        raise ValueError("size %d isn't a whole number of %d-byte records"
                         % (len(d), REC_SIZE))
    return [REC.unpack_from(d, i) for i in range(0, len(d), REC_SIZE)]


def seasons(rec):
    """{season: [objects]} as the search sees them: the leading
    non-negative ids of each group."""
    out = {}
    for name, start, n in SEASONS:
        ids = []
        for v in rec[start:start + n]:
            if v < 0:
                break
            ids.append(v)
        out[name] = ids
    return out


def problems(rec):
    """Ways a record doesn't fit the layout (for !!)."""
    out = []
    fn = rec[0]
    if not -1 <= fn < FUNCTION_COUNT:
        out.append("search function %d not in -1..%d" % (fn, FUNCTION_COUNT - 1))
    for v in rec[1:8]:
        if not -1 <= v < OBJECT_COUNT:
            out.append("object %d not in -1..%d" % (v, OBJECT_COUNT - 1))
    for name, start, n in SEASONS:
        group = rec[start:start + n]
        used = len(seasons(rec)[name])
        if any(v >= 0 for v in group[used:]):
            out.append("%s object after a -1 is never picked" % name)
    if rec[8] < -1:
        out.append("+8 value %d below -1" % rec[8])
    return out


def function_name(fn):
    if fn < 0:
        return "-"
    return FUNCTIONS.get(fn, "Dummy")


def _iter_files(args):
    """Yield (label, bytes) for each HUMANID.BIN, loose or a PAC entry."""
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for name in sorted(files):
                    if name.upper() == NAME or name.upper().endswith(".PAC"):
                        yield from _iter_files([os.path.join(root, name)])
            continue
        with open(a, "rb") as f:
            buf = f.read()
        if a.upper().endswith(".PAC"):
            try:
                entries = BinPac(buf).entries
            except ValueError:
                continue
            for off, size, name, _ in entries:
                if name.upper() == NAME:
                    yield "%s#%s" % (a, name), buf[off:off + size]
        else:
            yield a, buf


def object_table(iso_dir):
    """[(kind, index)] for each object id, from the executable in iso_dir."""
    import sles_disasm
    exe = gamever.exe_path(iso_dir)
    elf = sles_disasm.Elf(exe)
    off = elf.v2f(gamever.at(exe, OBJECT_TABLE))
    return [struct.unpack_from("<II", elf.data, off + 8 * k)
            for k in range(OBJECT_COUNT)]


def cmd_info(paths):
    for label, d in _iter_files(paths):
        try:
            recs = parse(d)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (label, e))
            continue
        bad = [(i, problems(r)) for i, r in enumerate(recs)]
        bad = [(i, p) for i, p in bad if p]
        objs = sorted({v for r in recs for v in r[1:8] if v >= 0})
        print("%s  %d records, %d with a search function, %d with objects "
              "(%d ids, max %d), %d with a +8 value"
              % (label, len(recs), sum(r[0] >= 0 for r in recs),
                 sum(any(v >= 0 for v in r[1:8]) for r in recs),
                 len(objs), max(objs) if objs else -1,
                 sum(r[8] >= 0 for r in recs)))
        for i, p in bad:
            print("  !! record %d: %s" % (i, "; ".join(p)))


def cmd_dump(path, iso_dir=None):
    with open(path, "rb") as f:
        recs = parse(f.read())
    table = object_table(iso_dir) if iso_dir else None

    def obj(v):
        if table is None:
            return str(v)
        kind, index = table[v]
        return "%d(%d:%d)" % (v, kind, index)

    print("%4s  %-18s  %-28s  %-28s  %-14s  %s"
          % ("id", "function", "warm", "mild", "cold", "+8"))
    for i, r in enumerate(recs):
        s = seasons(r)
        cols = [",".join(obj(v) for v in s[name]) or "-" for name, _, _ in SEASONS]
        print("%4d  %-18s  %-28s  %-28s  %-14s  %s"
              % (i, function_name(r[0]), cols[0], cols[1], cols[2],
                 r[8] if r[8] >= 0 else "-"))


def cmd_objects(iso_dir):
    for k, (kind, index) in enumerate(object_table(iso_dir)):
        print("%3d  kind %d  index %d" % (k, kind, index))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args)
    elif cmd == "dump" and len(args) in (1, 2):
        cmd_dump(*args)
    elif cmd == "objects" and len(args) == 1:
        cmd_objects(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
