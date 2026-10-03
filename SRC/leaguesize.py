# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Changing a division's size in Let's Make a Soccer Team! (PS2).

A nation's two divisions share its clubs, so the first division grows by
as many clubs as the second loses. Four things change together (see
DOC/SCHEDULE_FORMAT.md#building-a-league-of-another-size):

  where clubs come from   SCHEDULE_TEAM_ENTRY: each league UID's slots are
                          LAST_RANK records naming last season's ranks.
                          The first division keeps ranks 1-k of its own
                          table; the second keeps ranks m+1 to the end of
                          its own (empirical, all six nations).
  last season             PLRRSRC_INITTEAMDATA table 1 seeds the past
                          records the first season is built from
                          (pwkRec_SetPastRecordLastTeam); table 0 lists
                          the same clubs as the starting divisions.
  the games               schedule.set_league, a round robin of the new size.
  the game days           schedule.league_turns, one free turn per day.

To grow the first division by d, the second division's ranks m+1..m+d
move into the first division's past record at ranks k+1..k+d, above its
relegation places. To shrink it, its ranks k-d+1..k move to the second
division's ranks m+1..m+d. Every LAST_RANK reference to a moved or
shifted rank, in the leagues and in the nation's cups, is renumbered so
it still names the same club, and NOW_RANK references to ranks counted
from the bottom of a league table shift with its size. `plan` then
plays out the first season from the new records and checks that every
club of the nation is in exactly one division.

Usage:
    python leaguesize.py nations <DAT/PARAM>                   # each nation's divisions and their k, m
    python leaguesize.py plan <DAT/PARAM> <league> <clubs>     # the first division at <clubs>: new slots and checks
    python leaguesize.py build <DAT/PARAM> <outdir> <league> <clubs>   # write the changed files

`build` writes SCHEDULE_SYSTEM, SCHEDULE_COMPETITION and
SCHEDULE_TEAM_ENTRY (.PAC and .HED, which go together) and
PLRRSRC_INITTEAMDATA.TBB to <outdir>, reads them back and checks them
(the rebuilt leagues' games against their turns, and the first season
played out again), and prints the patch_disc.py targets. Patch with
--copies: the game reads the .HED copies in PRELOAD/STATIONFILE.PAC.

<league> is a number 0-5 or a name: England, France, Germany, Italy,
Spain, Netherlands.
"""
import os
import sys

import initteam
import schedule

LEAGUE_NAMES = ("England", "France", "Germany", "Italy", "Spain", "Netherlands")
DIV_MAX = initteam.DIV_MAX          # plLg_EntryTeamSetToDiv reads at most 26 clubs


class Nation:
    """One nation's divisions, found from the packs: its first division
    is the league UID loaded always, its second the own-nation and
    other-nations pair of the next competition."""

    def __init__(self, system, compes, entries, league):
        self.league = league
        nation = league + 1                 # open_nation numbers the leagues from 1
        rows = schedule.year_turns(system)
        mine = [u for u, (r, _) in rows.items() if u < len(compes) and compes[u].type == 0
                and schedule.compe_nation(system, r.compe) == nation and r.kind in (0, 1, 2)]
        firsts = [u for u in mine if rows[u][0].kind == 0]
        self.d1 = min(firsts, key=lambda u: rows[u][0].compe)
        self.c1 = rows[self.d1][0].compe
        seconds = [u for u in mine if rows[u][0].kind in (1, 2)]
        self.c2 = min(rows[u][0].compe for u in seconds)
        self.own = next(u for u in seconds if rows[u][0].compe == self.c2 and rows[u][0].kind == 1)
        self.other = next(u for u in seconds if rows[u][0].compe == self.c2
                          and rows[u][0].kind == 2)
        self.compes = [c for c in range(len(system.open_nation))
                       if schedule.compe_nation(system, c) == nation]
        d1 = refs(entries[self.d1])
        ranks = sorted(r for kind, src, r, _ in d1 if kind == "last_rank" and src == self.c1)
        self.k = next(i for i in range(len(ranks) + 1) if i == len(ranks) or ranks[i] != i + 1)
        d2 = [r for kind, src, r, _ in refs(entries[self.other])
              if kind == "last_rank" and src == self.c2]
        self.m = min(d2) - 1
        self.size1 = compes[self.d1].entrants
        self.size2 = compes[self.other].entrants


def refs(entry):
    """[(kind, source, rank, record)] for the LAST_RANK and NOW_RANK records
    the game walks, in slot order of the table they're in."""
    out = []
    for kind in ("last_rank", "now_rank"):
        for r in entry.used(kind):
            out.append((kind, int.from_bytes(r[4:6], "little", signed=True), r[1], r))
    return out


def remap(n, d, kind, src, rank):
    """Where a reference points after the first division grows by d (or
    shrinks by -d): (source, rank) naming the same club, or for NOW_RANK
    the same place counted from the bottom of the table."""
    k, m, c1, c2 = n.k, n.m, n.c1, n.c2
    if kind == "now_rank":
        if src == n.d1 and rank > k:
            return src, rank + d
        if src in (n.own, n.other) and rank > m:
            return src, rank - d
        return src, rank
    if d >= 0:
        if src == c1 and rank > k:
            return c1, rank + d
        if src == c2 and m < rank <= m + d:
            return c1, k + rank - m
        if src == c2 and rank > m + d:
            return c2, rank - d
    else:
        e = -d
        if src == c1 and k - e < rank <= k:
            return c2, m + rank - (k - e)
        if src == c1 and rank > k:
            return c1, rank - e
        if src == c2 and rank > m:
            return c2, rank + e
    return src, rank


def new_records(n, init, d):
    """(first division's past record, second's) after moving d clubs up
    (or -d down), as lists of team ids in last season's order."""
    r1 = [t for t in init.past[n.c1] if t]
    r2 = [t for t in init.past[n.c2] if t]
    if d >= 0:
        moved = r2[n.m:n.m + d]
        return r1[:n.k] + moved + r1[n.k:], r2[:n.m] + r2[n.m + d:]
    e = -d
    moved = r1[n.k - e:n.k]
    return r1[:n.k - e] + r1[n.k:], r2[:n.m] + moved + r2[n.m:]


def load(root):
    """(system, competitions, team entries, starting-division data) of a
    DAT/PARAM folder."""
    system = schedule.System(schedule.read_pack(os.path.join(root, schedule.SYSTEM_PAC)))
    compes = [schedule.Competition(b) for _, b in
              schedule.read_pack(os.path.join(root, schedule.COMPE_PAC))]
    entries = [schedule.TeamEntry(b) for _, b in
               schedule.read_pack(os.path.join(root, schedule.ENTRY_PAC))]
    init = initteam.InitTeamData(os.path.join(root, initteam.INIT_TBB))
    return system, compes, entries, init


def plan(root, league, clubs, data=None):
    """Everything the change needs, checked; returns (nation, d, {uid:
    [(kind, source, rank, record bytes)]}, records, problems)."""
    system, compes, entries, init = data or load(root)
    n = Nation(system, compes, entries, league)
    d = clubs - n.size1
    probs = []
    total = n.size1 + n.size2
    size2 = total - clubs
    if not 2 <= clubs <= DIV_MAX or not 2 <= size2 <= DIV_MAX:
        probs.append("each division holds 2-%d clubs; %d + %d don't fit" % (DIV_MAX, clubs, size2))
    if d > 0 and n.m + d > n.size2:
        probs.append("the second division has only %d clubs below rank %d" % (n.size2 - n.m, n.m))
    if d < 0 and -d > n.k:
        probs.append("only %d first-division clubs are safe from relegation" % n.k)
    if probs:
        return n, d, {}, None, probs
    rec1, rec2 = new_records(n, init, d)

    # Renumber every reference in the nation's UIDs.
    uids = [u for u, e in enumerate(entries) if any(
        (kind == "last_rank" and src in n.compes) or
        (kind == "now_rank" and src in (n.d1, n.own, n.other)) for kind, src, _, _ in refs(e))]
    lists = {}
    for u in uids:
        lists[u] = [(kind,) + remap(n, d, kind, src, rank) + (rec,)
                    for kind, src, rank, rec in refs(entries[u])]

    # Move the moved clubs' slots between the divisions.
    def is_moved(ref):
        kind, src, rank = ref[:3]
        if kind != "last_rank":
            return False
        if d > 0:
            return src == n.c1 and n.k < rank <= n.k + d
        return src == n.c2 and n.m < rank <= n.m - d
    if d > 0:
        moved = [r for r in lists[n.other] if is_moved(r)]
        for u in (n.own, n.other):
            lists[u] = [r for r in lists[u] if not is_moved(r)]
        at = max(i for i, r in enumerate(lists[n.d1]) if r[1] == n.c1 and r[2] <= n.k) + 1
        lists[n.d1][at:at] = moved
    elif d < 0:
        moved = [r for r in lists[n.d1] if is_moved(r)]
        lists[n.d1] = [r for r in lists[n.d1] if not is_moved(r)]
        for u in (n.own, n.other):
            at = next(i for i, r in enumerate(lists[u]) if r[1] == n.c2 and r[2] > n.m - d)
            lists[u][at:at] = moved

    # Play out the first season from the new records.
    past = [list(r) for r in init.past]
    past[n.c1] = rec1 + [0] * (initteam.PAST_SLOTS - len(rec1))
    past[n.c2] = rec2 + [0] * (initteam.PAST_SLOTS - len(rec2))

    def resolve(ref):
        kind, src, rank = ref[:3]
        if kind != "last_rank":
            return None
        rec = [t for t in past[src] if t]
        return rec[rank - 1] if 1 <= rank <= len(rec) else None
    clubs_of = {}
    for u in (n.d1, n.other, n.own):
        got = [resolve(r) for r in lists[u] if r[0] == "last_rank"]
        clubs_of[u] = got
    want = {n.d1: clubs, n.other: size2, n.own: size2 + 2}
    for u, size in want.items():
        if len(lists[u]) != size:
            probs.append("UID %d has %d slots, not %d" % (u, len(lists[u]), size))
    d1, d2 = clubs_of[n.d1], clubs_of[n.other]
    nation_clubs = set(rec1) | set(rec2)
    if None in d1 or None in d2:
        probs.append("a first-season slot names a rank past its record")
    if set(d1) & set(d2):
        probs.append("clubs in both divisions: %s" % sorted(set(d1) & set(d2)))
    if set(d1) | set(d2) != nation_clubs or len(d1) + len(d2) != len(nation_clubs):
        probs.append("the first season's divisions don't hold the nation's %d clubs once each"
                     % len(nation_clubs))
    own_extra = [r for r, t in zip(lists[n.own], clubs_of[n.own]) if t is None]
    if len(own_extra) != 2:
        probs.append("own-nation version has %d slots for your club and the rival, not 2"
                     % len(own_extra))
    for u in uids:
        for kind, src, rank, _ in lists[u]:
            if kind == "last_rank" and src in (n.c1, n.c2):
                size = len(rec1 if src == n.c1 else rec2) + (2 if u == n.own or src == n.c2 and
                                                             u not in (n.d1, n.other) else 0)
                if not 1 <= rank <= size:
                    probs.append("UID %d names rank %d of competition %d (%d clubs)"
                                 % (u, rank, src, size))
    return n, d, lists, (rec1, rec2), probs


def runs(lst):
    """Compact slot list: L0:1-17 L1:1-2 ..."""
    out, i = [], 0
    while i < len(lst):
        kind, src, rank = lst[i][:3]
        j = i
        while j + 1 < len(lst) and lst[j + 1][:2] == (kind, src) and lst[j + 1][2] == lst[j][2] + 1:
            j += 1
        out.append("%s%d:%d%s" % ("L" if kind == "last_rank" else "N", src, rank,
                                  "-%d" % lst[j][2] if j > i else ""))
        i = j + 1
    return " ".join(out)


def league_number(text):
    if text.isdigit() and int(text) < len(LEAGUE_NAMES):
        return int(text)
    names = [n.lower() for n in LEAGUE_NAMES]
    if text.lower() in names:
        return names.index(text.lower())
    raise SystemExit("league must be 0-5 or one of %s" % ", ".join(LEAGUE_NAMES))


def build(root, league, clubs):
    """The changed files' bytes, {file name: bytes}: the three schedule
    packs and their .HED, and PLRRSRC_INITTEAMDATA.TBB."""
    import struct
    data = load(root)
    system, compes, entries, init = data
    n, d, lists, recs, probs = plan(root, league, clubs, data)
    if probs:
        raise ValueError("; ".join(probs))
    size2 = n.size1 + n.size2 - clubs
    # Game days first, from the disc's calendar, then the games.
    sizes = {n.d1: clubs, n.other: size2, n.own: size2 + 2}
    turns = {}
    for u, size in sizes.items():
        legs = len(compes[u].games) // len(compes[u].pairs)
        turns[u] = schedule.league_turns(system, compes, u, len(schedule.league_days(size, legs)))
    for u, size in sizes.items():
        legs = len(compes[u].games) // len(compes[u].pairs)
        schedule.set_league(compes[u], size, legs)
    for r in system.year:
        if r.uid in turns:
            r.turns = turns[r.uid]
    # The slots: the leagues' rebuilt in their new order, the rest renumbered in place.
    for u, lst in lists.items():
        e = entries[u]
        if u in sizes:
            if any(e.counts[k] for k in ("list", "now_rank", "plteamid")):
                raise ValueError("UID %d has slots of other kinds" % u)
            new = []
            for slot, (kind, src, rank, rec) in enumerate(lst):
                b = bytearray(rec)
                b[0], b[1] = slot, rank
                b[4:6] = struct.pack("<h", src)
                new.append(bytes(b))
            e.records["last_rank"], e.counts["last_rank"] = new, len(new)
            continue
        for kind in ("last_rank", "now_rank"):
            items = [x for x in lst if x[0] == kind]
            if len(items) != len(e.used(kind)):
                raise ValueError("UID %d: %s slots changed in number" % (u, kind))
            for i, (_, src, rank, rec) in enumerate(items):
                b = bytearray(rec)
                b[1] = rank
                b[4:6] = struct.pack("<h", src)
                e.records[kind][i] = bytes(b)
    # Last season and the starting divisions.
    rec1, rec2 = recs
    init.past[n.c1] = rec1 + [0] * (initteam.PAST_SLOTS - len(rec1))
    init.past[n.c2] = rec2 + [0] * (initteam.PAST_SLOTS - len(rec2))
    init.divisions[league * initteam.DIVISIONS].ids = rec1 + [0] * (DIV_MAX - len(rec1))
    init.divisions[league * initteam.DIVISIONS + 1].ids = rec2 + [0] * (DIV_MAX - len(rec2))
    out = {}
    for name, blobs in ((schedule.SYSTEM_PAC, [b for _, b in system.encode()]),
                        (schedule.COMPE_PAC, [c.encode() for c in compes]),
                        (schedule.ENTRY_PAC, [e.encode() for e in entries])):
        pac_bytes, hed_bytes = schedule.build_pack(os.path.join(root, name), blobs)
        out[name], out[name[:-4] + ".HED"] = pac_bytes, hed_bytes
    out[initteam.INIT_TBB] = init.encode()
    return out, n, turns


def verify(folder, league, clubs, turns):
    """Problems in a built folder: read back, each rebuilt UID's games
    against its turn mask, and the first season played out again."""
    probs = []
    system, compes, entries, init = load(folder)
    rows = schedule.year_turns(system)
    for u, t in turns.items():
        c = compes[u]
        probs += ["UID %d: %s" % (u, p) for p in c.problems()]
        probs += ["UID %d: %s" % (u, p) for p in schedule.league_stats(c)[0]]
        if rows[u][1] != t or len(t) != c.days:
            probs.append("UID %d: %d game days on %d turns" % (u, c.days, len(rows[u][1])))
    probs += plan(folder, league, clubs)[4]
    return probs


def cmd_build(root, out, league, clubs):
    if os.path.abspath(root) == os.path.abspath(out):
        raise SystemExit("refusing to write into the input folder; give another one")
    try:
        files, n, turns = build(root, league, clubs)
    except ValueError as e:
        raise SystemExit(str(e))
    os.makedirs(out, exist_ok=True)
    for name, data in sorted(files.items()):
        with open(os.path.join(out, name), "wb") as f:
            f.write(data)
        print("wrote %s (%d bytes)" % (os.path.join(out, name), len(data)))
    for u, t in sorted(turns.items()):
        print("UID %d: %d game days, turns %s" % (u, len(t), " ".join(map(str, t))))
    probs = verify(out, league, clubs, turns)
    print("checked: %s" % ("no problems" if not probs else "!! " + "; ".join(probs)))
    targets = " ".join("PARAM/%s=%s" % (name, os.path.join(out, name).replace("\\", "/"))
                       for name in sorted(files))
    print("patch with: python SRC/patch_disc.py patch <in.iso> <out.iso> %s --copies" % targets)


def cmd_nations(root):
    """Each nation's divisions, and the first season played out from the
    disc's own records (plan with no change), which checks the model."""
    data = load(root)
    for league in range(len(LEAGUE_NAMES)):
        n = Nation(data[0], data[1], data[2], league)
        _, _, _, _, probs = plan(root, league, n.size1, data)
        print("%-11s first division UID %2d (competition %2d, %d clubs, ranks 1-%d stay), "
              "second UIDs %d/%d (competition %2d, %d clubs, ranks %d- stay)%s" % (
                  LEAGUE_NAMES[league], n.d1, n.c1, n.size1, n.k, n.other, n.own, n.c2,
                  n.size2, n.m + 1, "  !! " + "; ".join(probs) if probs else ""))


def cmd_plan(root, league, clubs):
    n, d, lists, recs, probs = plan(root, league, clubs)
    print("%s: first division %d -> %d clubs, second %d -> %d (%d with your club and the rival)"
          % (LEAGUE_NAMES[league], n.size1, clubs, n.size2, n.size2 - d, n.size2 - d + 2))
    if recs:
        print("last season's first division (record %d): %d clubs" % (n.c1, len(recs[0])))
        print("last season's second division (record %d): %d clubs" % (n.c2, len(recs[1])))
        for u, lst in sorted(lists.items()):
            print("  UID %3d  %2d slots  %s" % (u, len(lst), runs(lst)))
    for p in probs:
        print("  !! " + p)


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "nations" and len(args) == 1:
        cmd_nations(args[0])
    elif cmd == "plan" and len(args) == 3 and args[2].isdigit():
        cmd_plan(args[0], league_number(args[1]), int(args[2]))
    elif cmd == "build" and len(args) == 4 and args[3].isdigit():
        cmd_build(args[0], args[1], league_number(args[2]), int(args[3]))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
