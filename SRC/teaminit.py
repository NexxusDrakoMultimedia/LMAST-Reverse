# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The player's new club: PARAM/TEAM_INIT_DATA.TBB, for Let's Make a Soccer
Team! (PS2).

When a career starts, the Club Edit overlay (CEDITPRG.REL) asks for a
league and a team style, then calls pwkTeam_Init2(league, style, table)
(SLES 0x25eae8, from CEDITPRG.REL 0x2ccc) with this file, the only entry
of its load list (CEDITPRG.REL 0x1b288). Leagues are 0-5 (England,
France, Germany, Italy, Spain, Netherlands); styles 0-3 are the screen's
Counter-Attack, Possession, Individual Play and Teamwork (messages
420:200-203; the screen lists 200 + i, SIMPRG.REL 0xcc32c, and the module
passes the choice - 1, CEDITPRG.REL 0x2cd0). See DOC/TEAMINIT_FORMAT.md.

Nine TBB1 tables of u32 fields. Records hold {league, style, ...}; a
reader finds the first record with its key and takes the group after it.

  0  squad      24 B  {league, style, player, age, contract, salary}
                22 per (league, style). The club takes the first 18
                (0x25dce8), the rival club all 22, from the group of the
                style mapped through 0x5531e0: 0<->1, 2<->3 (0x25e4a8)
  1  staff      24 B  {league, style, manager, age, contract, salary}
                6 per (league, style): manager, youth-team manager, 4 coaches
  2  scouts     24 B  {league, style, scout, age, contract, salary}, 3 per group
  3  youth      16 B  {league, 4, player, age}, 16 per league (0x25e190);
                player 0xffffffff = empty slot
  4  coachlist  24 B  {league, 4, manager, age, contract, salary}, 6 per league:
                the first 6 of the 30-slot Coach Candidate List (pwork +0x9ac8)
  5  scoutlist  24 B  {league, 4, scout, age, contract, salary}, 6 per league:
                the first 6 of the 13-slot Scout Candidate List (pwork +0x9c30)
  6  rivalmgr   12 B  {6, style, manager}, 4 records. The loop at 0x25e6d0
                always loads the first record's manager, whatever the style
  7  rivalstad  12 B  {league, 4, stadium}: the rival's STADIUM_DATA row
  8  rivalclub  20 B  {league, style, foreign, newface, search_region}: the
                rival's club-record bytes 0x08-0x0a (INITTEAM_FORMAT.md)

Ids are database indexes within their kind (players 0-27,949, managers
0-2,999, scouts 0-999; the game adds 0x6d2e or 0x78e6). The code reads
ids as u16 (lhu), age and contract as u8 (lbu) and the salary as a u32.
Without the file, pwkTeam_Init (0x25e950) calls pwkTeam_Init2(0, 0, NULL),
which uses the built-in lists at 0x3995a8 (players 25,591-) and 0x3995d0.

Usage:
    python teaminit.py info      <TEAM_INIT_DATA.TBB | DAT/PARAM>
    python teaminit.py show      <TEAM_INIT_DATA.TBB> [table ...] [--pbdata PBDATA.PAC]
    python teaminit.py set       <in.TBB> <out.TBB> <table>:<record> <field>=<value> ... [<table>:<record> ...]
    python teaminit.py roundtrip <TEAM_INIT_DATA.TBB>

`show` names players and staff from PBDATA_EU.PAC next to the file (or
--pbdata). `set` writes a same-size table for patch_disc.py; records are
numbered from 0 within a table, as `show` prints them.
"""
import os
import struct
import sys

import tbb

FILE = "TEAM_INIT_DATA.TBB"
PBDATA = "PBDATA_EU.PAC"

LEAGUES = ("England", "France", "Germany", "Italy", "Spain", "Netherlands")
STYLES = ("Counter-Attack", "Possession", "Individual Play", "Teamwork")
ANY_STYLE = 4           # tables matched by league alone hold 4 here (empirical)
ANY_LEAGUE = 6          # table 6, matched by style alone
NO_PLAYER = 0xffffffff  # an empty youth slot: getPbase finds nothing (0x25e2e4)
STADIUMS = 119          # STADIUM_DATA rows (0x22add4)
COUNTS = {"players": 27950, "managers": 3000, "scouts": 1000}

# name, record size, fields, id kind, key ("ls" league+style, "l" league,
# "s" style), group size, roles of the records in a group.
TABLES = (
    ("squad", 24, ("league", "style", "player", "age", "contract", "salary"),
     "players", "ls", 22, None),
    ("staff", 24, ("league", "style", "manager", "age", "contract", "salary"),
     "managers", "ls", 6, ("manager", "youth manager", "coach", "coach", "coach", "coach")),
    ("scouts", 24, ("league", "style", "scout", "age", "contract", "salary"),
     "scouts", "ls", 3, None),
    ("youth", 16, ("league", "style", "player", "age"), "players", "l", 16, None),
    ("coachlist", 24, ("league", "style", "manager", "age", "contract", "salary"),
     "managers", "l", 6, None),
    ("scoutlist", 24, ("league", "style", "scout", "age", "contract", "salary"),
     "scouts", "l", 6, None),
    ("rivalmgr", 12, ("league", "style", "manager"), "managers", "s", 1, None),
    ("rivalstad", 12, ("league", "style", "stadium"), None, "l", 1, None),
    ("rivalclub", 20, ("league", "style", "foreign", "newface", "search_region"),
     None, "ls", 1, None),
)
SQUAD_OWN = 18          # 0x25df78: slti 0x12
# Fields the code reads as a byte (lbu) or a halfword (lhu).
BYTE_FIELDS = {"age", "contract", "foreign", "newface", "search_region"}
HALF_FIELDS = {"player", "manager", "scout"}


class Table:
    def __init__(self, index, data):
        (self.name, self.rec, self.fields, self.kind, self.key, self.group,
         self.roles) = TABLES[index]
        self.index = index
        if len(data) % self.rec:
            raise ValueError("table %d (%s): %d bytes, not a whole number of %d-byte records"
                             % (index, self.name, len(data), self.rec))
        n = len(self.fields)
        self.records = [list(struct.unpack_from("<%dI" % n, data, o))
                        for o in range(0, len(data), self.rec)]

    def encode(self):
        n = len(self.fields)
        return b"".join(struct.pack("<%dI" % n, *r) for r in self.records)

    def field(self, r, name):
        return r[self.fields.index(name)]

    def keys(self):
        """Every key a reader can ask for."""
        if self.key == "ls":
            return [(lg, st) for lg in range(len(LEAGUES)) for st in range(len(STYLES))]
        if self.key == "l":
            return [(lg,) for lg in range(len(LEAGUES))]
        return [(st,) for st in range(len(STYLES))]

    def key_of(self, r):
        return {"ls": (r[0], r[1]), "l": (r[0],), "s": (r[1],)}[self.key]


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, tables = tbb.parse(buf)
    if len(tables) != len(TABLES):
        raise ValueError("%d tables, expected %d" % (len(tables), len(TABLES)))
    return buf, end, tables, [Table(i, t.data) for i, t in enumerate(tables)]


def check(t):
    """Problems with table `t`: every key a reader asks for must start a
    whole group of records with that key."""
    problems = []
    if t.index == 6 and len(t.records) != 4:
        problems.append("%d records; the loop at 0x25e6d0 reads 4" % len(t.records))
    if t.index == 7 and len(t.records) != 6:
        problems.append("%d records; the loop at 0x25e718 reads 6" % len(t.records))
    for key in t.keys():
        first = next((i for i, r in enumerate(t.records) if t.key_of(r) == key), None)
        if first is None:
            problems.append("no record for %s" % (key,))
            continue
        group = t.records[first:first + t.group]
        if len(group) < t.group or any(t.key_of(r) != key for r in group):
            problems.append("records %d-%d are not all %s" % (first, first + t.group - 1, key))
    for i, r in enumerate(t.records):
        rec = dict(zip(t.fields, r))
        if t.key != "s" and rec["league"] >= len(LEAGUES):
            problems.append("#%d: league %d" % (i, rec["league"]))
        if t.key in ("ls", "s") and rec["style"] >= len(STYLES):
            problems.append("#%d: style %d" % (i, rec["style"]))
        if t.kind:
            ident = rec[t.fields[2]]
            if not (ident < COUNTS[t.kind] or (t.index == 3 and ident == NO_PLAYER)):
                problems.append("#%d: %s %d out of range" % (i, t.kind, ident))
        for name in BYTE_FIELDS & set(rec):
            if rec[name] > 0xff:
                problems.append("#%d: %s %d is more than a byte" % (i, name, rec[name]))
        if "stadium" in rec and rec["stadium"] >= STADIUMS:
            problems.append("#%d: stadium %d" % (i, rec["stadium"]))
    return problems


def pb_names(path):
    if not path or not os.path.exists(path):
        return None
    import pbdata
    db = pbdata.PbData(path)
    return db if db.data else None


def key_label(t, r):
    rec = dict(zip(t.fields, r))
    parts = []
    if t.key != "s":
        parts.append(LEAGUES[rec["league"]] if rec["league"] < len(LEAGUES) else "league %d" % rec["league"])
    if t.key != "l":
        parts.append(STYLES[rec["style"]] if rec["style"] < len(STYLES) else "style %d" % rec["style"])
    return ", ".join(parts)


# --- commands ----------------------------------------------------------------

def cmd_info(path):
    try:
        _, _, _, tables = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    for t in tables:
        problems = check(t)
        line = "table %d %-10s %4d records of %2d bytes, groups of %2d by %s" % (
            t.index, t.name, len(t.records), t.rec, t.group,
            {"ls": "league and style", "l": "league", "s": "style"}[t.key])
        if problems:
            line += "  !! " + "; ".join(problems[:3])
            if len(problems) > 3:
                line += "; ... (%d)" % len(problems)
        print(line)
    squad = tables[0]
    ids = [squad.field(r, "player") for r in squad.records]
    print("squad: %d records, %d distinct players; youth: %d players, %d empty slots"
          % (len(ids), len(set(ids)),
             sum(r[2] != NO_PLAYER for r in tables[3].records),
             sum(r[2] == NO_PLAYER for r in tables[3].records)))


def cmd_show(path, which, pb):
    _, _, _, tables = load(path)
    db = pb_names(pb or os.path.join(os.path.dirname(path), PBDATA))
    for t in tables:
        if which and t.index not in which:
            continue
        print("table %d: %s" % (t.index, t.name))
        last = None
        pos = 0
        for i, r in enumerate(t.records):
            key = t.key_of(r)
            if key != last:
                print("  %s" % key_label(t, r))
                last, pos = key, 0
            rec = dict(zip(t.fields, r))
            cols = ["%4d" % i]
            for name in t.fields[2:]:
                v = rec[name]
                cols.append("%s=%s" % (name, "-" if v == NO_PLAYER else v))
            if t.kind and db and rec[t.fields[2]] != NO_PLAYER:
                cols.append(db.record(t.kind, rec[t.fields[2]]).name)
            role = ""
            if t.roles:
                role = t.roles[pos] if pos < len(t.roles) else ""
            elif t.index == 0:
                role = "own+rival" if pos < SQUAD_OWN else "rival only"
            elif t.index == 6 and i:
                role = "never read (0x25e6d0 reads record 0)"
            if role:
                cols.append("(%s)" % role)
            print("    " + "  ".join(cols))
            pos += 1


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw, tables = load(path)
    target = None
    for a in args:
        if "=" not in a:
            ti, ri = (int(x, 0) for x in a.split(":"))
            if not 0 <= ti < len(tables) or not 0 <= ri < len(tables[ti].records):
                raise SystemExit("%s: no such table:record" % a)
            target = (tables[ti], ri, a)
            continue
        if target is None:
            raise SystemExit("give <table>:<record> before %r" % a)
        t, ri, label = target
        name, value = a.split("=", 1)
        if name not in t.fields:
            raise SystemExit("table %d fields are %s" % (t.index, ", ".join(t.fields)))
        value = NO_PLAYER if value == "-" else int(value, 0)
        hi = 0xff if name in BYTE_FIELDS else 0xffff if name in HALF_FIELDS else 0xffffffff
        if t.kind and name == t.fields[2] and not (value < COUNTS[t.kind] or
                                                    (t.index == 3 and value == NO_PLAYER)):
            raise SystemExit("%s: %s must be 0-%d%s" % (label, name, COUNTS[t.kind] - 1,
                                                        " or -" if t.index == 3 else ""))
        if not (0 <= value <= hi or value == NO_PLAYER and t.index == 3):
            raise SystemExit("%s: %s must be 0-%d" % (label, name, hi))
        k = t.fields.index(name)
        shown = lambda v: "-" if v == NO_PLAYER and t.index == 3 else str(v)
        print("%s %s: %s -> %s" % (label, name, shown(t.records[ri][k]), shown(value)))
        t.records[ri][k] = value
    for t in tables:
        problems = check(t)
        if problems:
            raise SystemExit("table %d would not fit the layout: %s" % (t.index, "; ".join(problems[:3])))
        raw[t.index].data = t.encode()
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise SystemExit("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_roundtrip(path):
    buf, end, raw, tables = load(path)
    for t in tables:
        same = t.encode() == raw[t.index].data
        print("table %d %-10s %4d records  %s" % (t.index, t.name, len(t.records),
                                                  "identical" if same else "!! re-encoded table differs"))
        raw[t.index].data = t.encode()
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    print("%s: %s" % (path, "rebuilt file identical" if out == buf else "!! rebuilt file differs"))


def _opt(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    pb = _opt(args, "--pbdata")
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and args:
        cmd_show(args[0], [int(a, 0) for a in args[1:]], pb)
    elif cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
