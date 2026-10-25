# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The club ranking's tables: PARAM/CLUB_RANK_SYSTEM.TBB, for Let's Make a
Soccer Team! (PS2).

Five TBB tables, which the club ranking (SIMPRG.REL, loader 0x150c10-
0x150d08) keeps at object +0x18, +0x20, +0x2c, +0x34 and +0x3c:

    0  52 x {u8 nation, u8 group}           nation groups (0x151210)
    1  33 x {s16 competition, s16 kind,     points for each final place
             s16 tally, u8 points[32]}       (0x152128)
    2  32 x s16                             world rank points by club rank,
                                            for clubs outside nations 1-52
                                            (0x151568)
    3  65 x {s8 nation slot, s8 size,       the club rank by position in the
             s8 positions[32]}               nation or division (0x151938)
    4  18 x {s16 UID, s16 nation,           the leagues the year end waits
             s16 division, s16 0}            for (0x150dd8)

Table 1 (0x152128): each pass walks the rows of its kind. A row with a
competition >= 0 that had a result this year (0x1520e0) gives points[n]
to the club in entry n of its past record (pwkRec_GetCompePastRecord),
that is final place n + 1. Kind 0 adds them to the club's nation (52
tallies, called from 0x150528), kind 1 to the nation (145 tallies,
national teams through plMisc_NatiTeam2Nati, 0x1505c0), kind 2 to the
club (441 tallies, 0x150680, before the world rank points at 0x151568).
Each tally is two u16 counters: kinds 0 and 1 always add to the first
(+2); kind 2 adds to the first when the row's tally field is 1, the
second (+4) otherwise.

Table 3 (0x151938): row byte 2 + i (i = 0-31) is a running position in
the nation's or division's list sorted by world rank points. The clubs
from the previous position up to it get rank 31 - i; 0, or a position not
past the previous one, gives that rank to no club. Teams 1 and 2 (your
club and the rival) take a place but keep their rank, and clubs past the
row's last position keep their old rank.

See DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables and
DOC/SAVE_FORMAT.md ("How the club rank changes").

Usage:
    python clubrank.py info      <CLUB_RANK_SYSTEM.TBB | DAT/PARAM>
    python clubrank.py show      <CLUB_RANK_SYSTEM.TBB> [MES.PAC]
    python clubrank.py set       <in.TBB> <out.TBB> <key>=<value> ...
    python clubrank.py roundtrip <CLUB_RANK_SYSTEM.TBB>

`show` names the competitions from MES.PAC (category 100009) when given.
`set` edits the three tables a mod changes, and writes a same-size file
for patch_disc.py:

    points:<row>:<place>=<0-255>   table 1: row 0-32, final place 1-32
    world:<rank>=<0-1023>          table 2: club rank 0-31
    rank:<row>:<rank>=<0-127>      table 3: row 0-64, the last position
                                   that gets club rank 0-31

for example `points:9:1=80` (the Premier Division's champions get 80),
`world:31=950`, `rank:7:31=2` (the top two clubs of a slot-1 first
division of 20 get rank 31).
"""
import os
import struct
import sys

import tbb

FILE = "CLUB_RANK_SYSTEM.TBB"
# (rows, bytes a row) of tables 0-4, as the readers above step through them.
SHAPES = ((52, 2), (33, 38), (32, 2), (65, 34), (18, 8))
POINTS, WORLD, RANKS = 1, 2, 3
PLACES = 32                     # table 1's u8 points[32]
POINTS_AT = 6
RANK_MAX = 31                   # club ranks 0-31 (0x151938: 0x1f - i)
WORLD_MAX = 1023                # 0x151568 caps the world rank points at 1,023
POSITION_MAX = 127              # an s8; a negative one is skipped like 0
POSITIONS_AT = 2
NATIONS = 52                    # nations 1-52 are ranked (0x151d58, 0x151e60)
EURO6 = 6                       # nation slots 1-6: the league nations
SCHEDULE_UIDS = 164             # SCHEDULE_FORMAT.md: UIDs 0-163
COMPETITIONS = 72               # PLSCHE_COMPE 0-71
COMPE_NAME_CATEGORY, COMPE_NAME_BASE = 100009, 10000    # SCHEDULE_FORMAT.md
KINDS = {0: "to the club's nation (52 tallies)", 1: "to the nation (145 tallies)",
         2: "to the club (441 tallies)"}


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, raw = tbb.parse(buf)
    if len(raw) != len(SHAPES):
        raise ValueError("expected %d tables, not %d" % (len(SHAPES), len(raw)))
    for t, (rows, size) in enumerate(SHAPES):
        if len(raw[t].data) != rows * size:
            raise ValueError("table %d is %d bytes, not %d x %d" % (t, len(raw[t].data),
                                                                   rows, size))
        raw[t].data = bytearray(raw[t].data)
    return buf, end, raw


# --- the rows ----------------------------------------------------------------

def nation_groups(raw):
    d = raw[0].data
    return [(d[o], d[o + 1]) for o in range(0, len(d), 2)]


def points_row(raw, row):
    """(competition, kind, tally, [points for places 1-32]) of table 1."""
    o = row * SHAPES[POINTS][1]
    d = raw[POINTS].data
    return struct.unpack_from("<3h", d, o) + (list(d[o + POINTS_AT:o + POINTS_AT + PLACES]),)


def world_points(raw):
    return list(struct.unpack("<%dh" % SHAPES[WORLD][0], raw[WORLD].data))


def rank_row(raw, row):
    """(nation slot, size, [the positions for i = 0-31, rank 31 - i])."""
    o = row * SHAPES[RANKS][1]
    v = struct.unpack_from("<34b", raw[RANKS].data, o)
    return v[0], v[1], list(v[2:])


def year_end_leagues(raw):
    d = raw[4].data
    return [struct.unpack_from("<4h", d, o) for o in range(0, len(d), 8)]


def rank_ranges(positions):
    """[(rank, first, last)] the positions (1-based) each rank gets, as
    0x151938 hands them out over a long enough list."""
    out, done = [], 0
    for i, p in enumerate(positions):
        if p > done:
            out.append((RANK_MAX - i, done + 1, p))
            done = p
    return out


def rank_row_label(raw, row):
    slot, size, _ = rank_row(raw, row)
    if slot < 0:
        return "second division of %d" % size
    if slot <= EURO6:
        return "nation slot %d, first division of %d" % (slot, size)
    return "nation slot %d" % slot


# --- edits -------------------------------------------------------------------

def field(key):
    """(table, offset, struct format, low, high) of a `set` key."""
    parts = key.split(":")
    try:
        nums = [int(p, 0) for p in parts[1:]]
    except ValueError:
        raise ValueError("%s: expected numbers after %s:" % (key, parts[0]))
    if parts[0] == "points" and len(nums) == 2:
        row, place = nums
        if not 0 <= row < SHAPES[POINTS][0] or not 1 <= place <= PLACES:
            raise ValueError("%s: row 0-%d, place 1-%d" % (key, SHAPES[POINTS][0] - 1, PLACES))
        return POINTS, row * SHAPES[POINTS][1] + POINTS_AT + place - 1, "<B", 0, 0xff
    if parts[0] == "world" and len(nums) == 1:
        rank, = nums
        if not 0 <= rank <= RANK_MAX:
            raise ValueError("%s: rank 0-%d" % (key, RANK_MAX))
        return WORLD, rank * 2, "<h", 0, WORLD_MAX
    if parts[0] == "rank" and len(nums) == 2:
        row, rank = nums
        if not 0 <= row < SHAPES[RANKS][0] or not 0 <= rank <= RANK_MAX:
            raise ValueError("%s: row 0-%d, rank 0-%d" % (key, SHAPES[RANKS][0] - 1, RANK_MAX))
        return (RANKS, row * SHAPES[RANKS][1] + POSITIONS_AT + RANK_MAX - rank, "<b", 0,
                POSITION_MAX)
    raise ValueError("%s: expected points:<row>:<place>, world:<rank> or rank:<row>:<rank>"
                     % key)


def edit_spec(key):
    """The values a key allows, as the editor's inputs take them."""
    _, _, _, lo, hi = field(key)
    return ("range", lo, hi)


def get(raw, key):
    t, o, fmt, _, _ = field(key)
    return struct.unpack_from(fmt, raw[t].data, o)[0]


def set_value(raw, key, value):
    """Set one field; returns the old value."""
    t, o, fmt, lo, hi = field(key)
    if not lo <= value <= hi:
        raise ValueError("%s is %d-%d" % (key, lo, hi))
    old = struct.unpack_from(fmt, raw[t].data, o)[0]
    struct.pack_into(fmt, raw[t].data, o, value)
    return old


# --- checks and encoding -----------------------------------------------------

def check(raw):
    problems = []
    groups = nation_groups(raw)
    if sorted(n for n, _ in groups) != list(range(1, NATIONS + 1)):
        problems.append("table 0: not nations 1-%d once each" % NATIONS)
    for row in range(SHAPES[POINTS][0]):
        compe, kind, tally, _ = points_row(raw, row)
        if kind not in KINDS or tally not in (1, 2) or compe >= COMPETITIONS:
            problems.append("table 1 row %d: competition %d, kind %d, tally %d"
                            % (row, compe, kind, tally))
    for rank, v in enumerate(world_points(raw)):
        if not 0 <= v <= WORLD_MAX:
            problems.append("table 2 rank %d: %d points" % (rank, v))
    for row in range(SHAPES[RANKS][0]):
        slot, size, positions = rank_row(raw, row)
        if not (slot == -1 or 1 <= slot <= NATIONS) or (size < 0) != (slot > EURO6):
            problems.append("table 3 row %d: nation slot %d, size %d" % (row, slot, size))
        if any(p < 0 for p in positions):
            problems.append("table 3 row %d: a negative position" % row)
    for uid, nation, division, zero in year_end_leagues(raw):
        if not (0 <= uid < SCHEDULE_UIDS and 1 <= nation <= EURO6 and division in (0, 1)
                and zero == 0):
            problems.append("table 4: %d, %d, %d, %d" % (uid, nation, division, zero))
    return problems


def encode_file(buf, end, raw):
    problems = check(raw)
    if problems:
        raise ValueError("; ".join(problems))
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


def compe_names(mes_path):
    if not mes_path:
        return {}
    import camp
    return {rid - COMPE_NAME_BASE: t.strip() for rid, t in
            camp.messages(mes_path, COMPE_NAME_CATEGORY).items()}


def compe_label(compe, names):
    if compe < 0:
        return "%d (never used)" % compe
    return "%d %s" % (compe, names.get(compe, "")) if names else str(compe)


# --- commands ----------------------------------------------------------------

def cmd_info(path):
    try:
        _, _, raw = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    problems = check(raw)
    print("%s: %s" % (path, ", ".join("table %d %d x %d" % ((t,) + s)
                                      for t, s in enumerate(SHAPES)))
          + ("  !! " + "; ".join(problems) if problems else ""))
    kinds = {}
    for row in range(SHAPES[POINTS][0]):
        kinds[points_row(raw, row)[1]] = kinds.get(points_row(raw, row)[1], 0) + 1
    print("  table 1 rows by kind: %s" % ", ".join("%d: %d" % kv for kv in sorted(kinds.items())))


def cmd_show(path, mes=None):
    _, _, raw = load(path)
    names = compe_names(mes)
    groups = {}
    for nation, group in nation_groups(raw):
        groups.setdefault(group, []).append(nation)
    print("table 0, nation groups:")
    for group, nations in sorted(groups.items()):
        print("  group %d: %s" % (group, " ".join(map(str, nations))))
    print("table 1, points for each final place:")
    for row in range(SHAPES[POINTS][0]):
        compe, kind, tally, points = points_row(raw, row)
        while len(points) > 1 and points[-1] == 0:
            points = points[:-1]
        print("  row %2d: %s, kind %d, tally %d: %s" % (row, compe_label(compe, names), kind,
                                                       tally, " ".join(map(str, points))))
    print("table 2, world rank points by club rank (ranks 0-31): %s"
          % " ".join(map(str, world_points(raw))))
    print("table 3, club rank by position:")
    for row in range(SHAPES[RANKS][0]):
        print("  row %2d (%s): %s" % (row, rank_row_label(raw, row), ", ".join(
            "%d: %s" % (rank, first if first == last else "%d-%d" % (first, last))
            for rank, first, last in rank_ranges(rank_row(raw, row)[2]))))
    print("table 4, the leagues the year end waits for (UID, nation, division):")
    print("  " + ", ".join("%d %d %d" % r[:3] for r in year_end_leagues(raw)))


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw = load(path)
    for a in args:
        key, eq, v = a.partition("=")
        try:
            value = int(v, 0)
        except ValueError:
            raise SystemExit("expected <key>=<number>, got %r" % a)
        try:
            old = set_value(raw, key, value)
        except ValueError as e:
            raise SystemExit(str(e))
        print("%s: %d -> %d" % (key, old, value))
    try:
        out = encode_file(buf, end, raw)
    except ValueError as e:
        raise SystemExit(str(e))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_roundtrip(path):
    buf, end, raw = load(path)
    try:
        out = encode_file(buf, end, raw)
        print("%s: %s" % (path, "rebuilt file identical" if out == buf else "!! rebuilt file differs"))
    except ValueError as e:
        print("%s: !! %s" % (path, e))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and len(args) in (1, 2):
        cmd_show(args[0], args[1] if len(args) == 2 else None)
    elif cmd == "set" and len(args) >= 3:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
