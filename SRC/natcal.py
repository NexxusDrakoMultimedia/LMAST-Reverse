# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The national-team calendar: PARAM/SCHEDULE_LIST.TBB, for Let's Make a
Soccer Team! (PS2).

Four TBB tables, one per year of the 4-year cycle: the season starting in
year Y reads table (Y - 2006) mod 4 (SLES 0x256a50-0x256c50). Each table
is 96 bytes, a byte of flags per turn (8 turns a month, from July):

    1  national match   pwkSche_IsNationalMatch (0x256b30): the globes on
                        the Schedule screen (SIMPRG.REL 0x4dd84)
    2  finals           pwkSche_IsNationalFMatch (0x256b90): the call-up
                        and release are for the finals (competition 45 or
                        47) instead of the qualifying (44, 46) (SIMPRG.REL
                        0x160a48); a release asks for the champion
    4  call-up          pwkSche_IsNationalConvene (0x256c50):
                        jmNT_CallCheck (SIMPRG.REL 0x160b68) picks the
                        national squads
    8  release          pwkSche_IsNationalBreak (0x256bf0): jmNT_FreeCheck
                        (0x160c50) sends the players back

Empirical, every table on the disc: the match flag is on exactly on the
turns the national cups (competitions 44-47) play in SCHEDULE_SYSTEM.PAC,
their rows of cycle c (1-4) going to table c - 1 and a second-year turn
to the next table; every match turn lies between a call-up and its
release (both may be on the match turn); only the finals years (tables 1
and 3, Euro and World) hold the finals flag, and there it is on the
call-up and the release too. `info` checks all four, the first against
SCHEDULE_SYSTEM.PAC in the same folder. The
match flag follows the schedule, so `set` leaves it alone: `patch_disc.py
--mod national-cups` moves the cups and the calendar together.

The game also reads the copies in PRELOAD/SIMLOCALMEM0-6.PAC (entry 31);
patch_disc.py's --copies updates them. See
DOC/PARAM_DIR.md#schedule_listtbb-the-national-team-calendar.

Usage:
    python natcal.py info      <SCHEDULE_LIST.TBB | DAT/PARAM>
    python natcal.py show      <SCHEDULE_LIST.TBB>
    python natcal.py set       <in.TBB> <out.TBB> <table>:<turn>:<flag>=<0|1> ...
    python natcal.py roundtrip <SCHEDULE_LIST.TBB>

`set` takes table 0-3, turn 0-95 and the flag finals, callup or release,
for example `3:88:callup=0 3:87:callup=1 3:87:finals=1` (the World Cup
squads called up a turn earlier), checks the result and writes a
same-size file.
"""
import os
import struct
import sys

import tbb

FILE = "SCHEDULE_LIST.TBB"
SCHEDULE_PAC = "SCHEDULE_SYSTEM.PAC"
TABLES, TURNS = 4, 96
FIRST_YEAR = 2006                       # 0x256a50: (year - 2006) mod 4
MATCH, FINALS, CALLUP, RELEASE = 1, 2, 4, 8
FLAGS = {"match": MATCH, "finals": FINALS, "callup": CALLUP, "release": RELEASE}
EDITABLE = ("finals", "callup", "release")
NATIONAL_COMPES = (44, 45, 46, 47)      # Euro primary, Euro, World primary, World
FINALS_COMPES = (45, 47)
TABLE_NAMES = ("Euro qualifying", "Euro National Cup", "World qualifying",
               "World National Cup")
MONTHS = ("Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun")


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, raw = tbb.parse(buf)
    if len(raw) != TABLES or any(len(t.data) != TURNS for t in raw):
        raise ValueError("expected %d tables of %d bytes" % (TABLES, TURNS))
    for t in raw:
        t.data = bytearray(t.data)
    return buf, end, raw


def turn_label(turn):
    """A turn as the top bar names it: month, week, midweek or weekend
    (8 turns a month from July; SAVE_FORMAT.md, PlDate)."""
    return "%s week %d %s" % (MONTHS[turn // 8], turn % 8 // 2 + 1,
                              "weekend" if turn % 2 else "midweek")


def table_label(table):
    years = ", ".join(str(FIRST_YEAR + table + 4 * i) for i in range(3))
    return "%d %s (%s, ...)" % (table, TABLE_NAMES[table], years)


def flags_text(v):
    return "+".join(n for n, bit in FLAGS.items() if v & bit) or "-"


def get(raw, table, turn, flag):
    return int(bool(raw[table].data[turn] & FLAGS[flag]))


def set_flag(raw, table, turn, flag, value):
    """Set one editable flag; returns the old value."""
    if not 0 <= table < TABLES or not 0 <= turn < TURNS:
        raise ValueError("table 0-%d, turn 0-%d" % (TABLES - 1, TURNS - 1))
    if flag not in EDITABLE:
        raise ValueError("flag %r: one of %s (the match flag follows the schedule)"
                         % (flag, ", ".join(EDITABLE)))
    if value not in (0, 1):
        raise ValueError("%s is 0 or 1" % flag)
    old = get(raw, table, turn, flag)
    if value:
        raw[table].data[turn] |= FLAGS[flag]
    else:
        raw[table].data[turn] &= ~FLAGS[flag] & 0xff
    return old


def windows(data):
    """([(call-up turn, release turn)], problems) of one table: a release
    closes the call-up before it, on the same turn or later."""
    out, problems, open_at = [], [], None
    for t in range(TURNS):
        if data[t] & CALLUP:
            if open_at is not None:
                problems.append("call-up on turn %d while called up since %d" % (t, open_at))
            open_at = t
        if data[t] & RELEASE:
            if open_at is None:
                problems.append("release on turn %d without a call-up" % t)
            else:
                out.append((open_at, t))
                open_at = None
    if open_at is not None:
        problems.append("call-up on turn %d never released" % open_at)
    return out, problems


def schedule_turns(path):
    """({table: set of turns} the national cups play in SCHEDULE_SYSTEM.PAC,
    {tables with a finals cup}), or None when the pack isn't there. `path`
    is the pack or the folder holding it."""
    if os.path.isdir(path):
        path = os.path.join(path, SCHEDULE_PAC)
    if not os.path.exists(path):
        return None
    import schedule
    system = schedule.System(schedule.read_pack(path))
    out = {k: set() for k in range(TABLES)}
    finals = set()
    for _, (r, turns) in schedule.year_turns(system).items():
        if r.compe in NATIONAL_COMPES:
            for t in turns:
                k = (r.cycle - 1 + t // TURNS) % TABLES
                out[k].add(t % TURNS)
                if r.compe in FINALS_COMPES:
                    finals.add(k)
    return out, finals


def check(raw, scheduled=None):
    """Problems with the calendar: flag bits the game doesn't read, a
    call-up without its release, a match outside a call-up, the finals flag
    outside a finals year, and (given the schedule) match flags that
    differ from the national cups' turns."""
    problems = []
    finals_years = scheduled[1] if scheduled else {1, 3}
    for k in range(TABLES):
        d = raw[k].data
        if any(v & ~0xf for v in d):
            problems.append("table %d: flag bits above 8" % k)
        wins, probs = windows(d)
        problems += ["table %d: %s" % (k, p) for p in probs]
        for t in range(TURNS):
            if d[t] & MATCH and not any(a <= t <= b for a, b in wins):
                problems.append("table %d: a match on turn %d outside a call-up" % (k, t))
        # The finals flag picks the competition the squads are called up
        # for and released from (0x160a48), so a finals window needs it on
        # both ends, as on the disc.
        for a, b in wins:
            if any(d[t] & FINALS for t in range(a, b + 1)) and not d[a] & d[b] & FINALS:
                problems.append("table %d: the finals call-up %d-%d without the finals flag "
                                "on both ends" % (k, a, b))
        if k not in finals_years and any(v & FINALS for v in d):
            problems.append("table %d: the finals flag in a year with no finals" % k)
        if scheduled:
            mine = {t for t in range(TURNS) if d[t] & MATCH}
            if mine != scheduled[0][k]:
                problems.append("table %d: match flags on %s, the national cups play on %s"
                                % (k, sorted(mine), sorted(scheduled[0][k])))
    return problems


def encode_file(buf, end, raw, scheduled=None):
    problems = check(raw, scheduled)
    if problems:
        raise ValueError("; ".join(problems))
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


def param_dir_of(path):
    return path if os.path.isdir(path) else os.path.dirname(path)


# --- commands ----------------------------------------------------------------

def cmd_info(path):
    try:
        _, _, raw = load(path)
        scheduled = schedule_turns(param_dir_of(path))
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    problems = check(raw, scheduled)
    print("%s: %d tables of %d turns%s%s" % (
        path, TABLES, TURNS, "" if scheduled else " (no %s to check against)" % SCHEDULE_PAC,
        "  !! " + "; ".join(problems) if problems else ""))
    for k in range(TABLES):
        d = raw[k].data
        print("  table %d: %d match turns, call-ups %s" % (
            k, sum(1 for v in d if v & MATCH),
            ", ".join("%d-%d" % w for w in windows(d)[0])))


def cmd_show(path):
    _, _, raw = load(path)
    for k in range(TABLES):
        print("table %s" % table_label(k))
        for t in range(TURNS):
            v = raw[k].data[t]
            if v:
                print("  turn %2d %-22s %s" % (t, turn_label(t), flags_text(v)))


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw = load(path)
    for a in args:
        key, _, v = a.partition("=")
        parts = key.split(":")
        try:
            table, turn, value = int(parts[0]), int(parts[1]), int(v)
            flag = parts[2]
        except (ValueError, IndexError):
            raise SystemExit("expected <table>:<turn>:<flag>=<0|1>, got %r" % a)
        try:
            old = set_flag(raw, table, turn, flag, value)
        except ValueError as e:
            raise SystemExit("%s: %s" % (a, e))
        print("table %d turn %d %s: %d -> %d" % (table, turn, flag, old, value))
    try:
        out = encode_file(buf, end, raw, schedule_turns(param_dir_of(path)))
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
    elif cmd == "show" and len(args) == 1:
        cmd_show(args[0])
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
