# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""PARAM/PLRESOURCESIM.PAC, the season-mode resource pack of Let's Make a
Soccer Team! (PS2): plResource entry 1, loaded by the SIMPRG.REL load list.
Every reader calls plResource_GetResourceDataBinPac[Tbb[Tbl]](1, entry,
table) with constant arguments (SLES 0x21e890/0x21e940/0x21e9e0). See
DOC/PLRESOURCESIM_FORMAT.md.

  0  states and cities     TBB: 137 states {u8, u8 nation} (plState_*);
                           839 city records {u32 city, u32 population,
                           u8 state/nation, u8 climate, u8 weather, u8
                           initial choice} (Get_plStateCity_AreaDataCitySheet_
                           Pointer 0x21ef90); 64 x {zone, 12 monthly
                           temperatures} (plCity_GetAverageTemperature);
                           64 x {zone, 12 monthly weather rows} and 64 x
                           {row, 4 chances} (plCity_GetListProbability)
  1  overseas branches     TBB: 13 x {region, cost}, 8 f32 level rates (0x232d88)
  2  (unread)              TBB: 400 bytes, 128 u16; no call asks for entry 2
  3  club records          457 x 24 bytes (plOteam_GetDb), see initteam.py
  4  nations               145 x {s16 national-team manager, u16 club[8]}
  5  player affiliations   s16 stream: -player, then clubs (> 0) (0x2161b8)
  6  transfer AI           TBB, 6 byte tables (CAcquirePlayer and others)
  7  player introductions  10 groups x 100 {s16 player, s16 threshold} (0x2202f8)
  8  record kinds          164 x {s16 schedule UID, s16 PlCareerRecordKind}
  9  edit colours          TBB, EDIT::CColor: 96 RGBA colours, 6 index maps
  10 stadium ids           6 x 25 bytes (plTeam_GetStadiumDataIndex)
  11 scout exclusives      s16 stream: -scout, then players (0x21ea48)
  12 scout semi-exclusives same format
  13 good combinations     s16 stream: -level, then players; -1000 ends
  14 bad combinations      same format
  15 free agents           u16 players, ending at 0xffff (Set_InitDBSet)

Usage:
    python plrsim.py info <PLRESOURCESIM.PAC | DAT/PARAM>
    python plrsim.py show <PLRESOURCESIM.PAC | DAT/PARAM> <entry> [--pbdata PBDATA.PAC]

`show` prints one entry in readable form, naming players, managers and
scouts from PBDATA_EU.PAC next to the pack (or --pbdata).
"""
import os
import struct
import sys

import pac
import tbb

FILE = "PLRESOURCESIM.PAC"
PBDATA = "PBDATA_EU.PAC"
ENTRIES = 16
PLAYERS, MANAGERS, SCOUTS = 27950, 3000, 1000
CLUB_FIRST, CLUB_END = 3, 0x1ba          # computer clubs (pwkOteam_Init)
NATIONS = 145                            # 0x91 (plTeam_GetPlTeamFromNation)
STATES = 0x89                            # plNati_GetBelongStateNum loop
CITIES = 0x347                           # city ids below this
STATE_CITIES = 0x25b                     # first city that belongs to a nation
CLIMATE_ZONES = 0x40
CLUB_RECORDS = 457                       # plOteam_GetDb, teams 3-459
SCHEDULE_UIDS = 164
END_COMBI = -1000                        # ends the combination streams
NAMES = ("states and cities", "overseas branches", "(unread)", "club records",
         "nations", "player affiliations", "transfer AI", "player introductions",
         "record kinds", "edit colours", "stadium ids", "scout exclusives",
         "scout semi-exclusives", "good combinations", "bad combinations",
         "free agents")


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        data = f.read()
    h, blobs = pac.binpac_blobs(data)
    if len(blobs) != ENTRIES:
        raise ValueError("%d entries, expected %d" % (len(blobs), ENTRIES))
    return path, blobs


def tables(blob):
    return [t.data for t in tbb.parse(blob)[1]]


def s16s(b):
    return list(struct.unpack("<%dh" % (len(b) // 2), b[:len(b) // 2 * 2]))


def stream(b, end=None):
    """[(header, [values])] of a stream where a header is <= 0 (entry 5)
    or < 0 (11-14), and the trailing zero padding."""
    v = s16s(b)
    stop = len(v)
    while stop and v[stop - 1] == 0:
        stop -= 1
    groups = []
    for x in v[:stop]:
        if x == end:
            groups.append((x, []))
        elif x < 0 or (not groups and x == 0):
            groups.append((x, []))
        elif groups:
            groups[-1][1].append(x)
        else:
            raise ValueError("stream starts with %d" % x)
    return groups, len(v) - stop


# --- per-entry parsers: (summary line, problems) ------------------------------

def e0(b):
    t = tables(b)
    p = []
    sizes = (STATES * 2, CITIES * 12, CLIMATE_ZONES * 13, CLIMATE_ZONES * 13, CLIMATE_ZONES * 5)
    if [len(x) for x in t] != list(sizes):
        return "tables %s" % [len(x) for x in t], ["table sizes %s, expected %s" % ([len(x) for x in t], list(sizes))]
    states = [struct.unpack_from("2B", t[0], i * 2) for i in range(STATES)]
    cities = [struct.unpack_from("<2I4B", t[1], i * 12) for i in range(CITIES)]
    if [c[0] for c in cities] != list(range(CITIES)):
        p.append("city records are not cities 0-%d in order" % (CITIES - 1))
    zones = {t[2][i * 13] for i in range(CLIMATE_ZONES)}
    wzones = {t[3][i * 13] for i in range(CLIMATE_ZONES)}
    bad = [c[0] for c in cities if c[3] not in zones]
    if bad:
        p.append("%d cities with an unknown climate zone" % len(bad))
    bad = [c[0] for c in cities if c[4] not in wzones]
    if bad:
        p.append("%d cities with an unknown weather zone" % len(bad))
    # Record 0 is the "no state" placeholder (0, 0); the rest are {id, nation}.
    if [st[0] for st in states] != list(range(STATES)):
        p.append("state ids are not 0-%d in order" % (STATES - 1))
    if any(not 1 <= st[1] <= NATIONS for st in states[1:]):
        p.append("state with nation outside 1-%d" % NATIONS)
    choice = sum(1 for c in cities if c[5])
    return ("%d states, %d cities (%d of states, %d of nations, %d initial choices), "
            "%d climate zones, %d weather zones" % (
                STATES, CITIES, STATE_CITIES, CITIES - STATE_CITIES, choice,
                len(zones), len(wzones))), p


def e1(b):
    t = tables(b)
    if [len(x) for x in t] != [26 * 4, 8 * 4]:
        return "", ["table sizes %s" % [len(x) for x in t]]
    pairs = [struct.unpack_from("<2I", t[0], i * 8) for i in range(13)]
    rates = struct.unpack("<8f", t[1])
    p = [] if [r for r, _ in pairs] == list(range(13)) else ["regions are not 0-12 in order"]
    return "13 regions, costs %d-%d; level rates %s" % (
        min(c for _, c in pairs), max(c for _, c in pairs),
        ", ".join("%.3f" % r for r in rates)), p


def e2(b):
    t = tables(b)
    return "tables of %s bytes; never read" % "/".join(str(len(x)) for x in t), []


def e3(b):
    t = tables(b)
    if len(t[0]) != CLUB_RECORDS * 24:
        return "", ["%d bytes, expected 457 x 24" % len(t[0])]
    return "457 club records of 24 bytes (initteam.py teams)", []


def e4(b):
    t = tables(b)
    if len(t[0]) != NATIONS * 18:
        return "", ["%d bytes, expected %d x 18" % (len(t[0]), NATIONS)]
    p = []
    for n in range(NATIONS):
        r = struct.unpack_from("<h8H", t[0], n * 18)
        if not 0 <= r[0] < MANAGERS:
            p.append("nation %d: manager %d" % (n + 1, r[0]))
        if any(not 0 <= c < CLUB_END + 128 for c in r[1:]):
            p.append("nation %d: club out of range" % (n + 1))
    return "%d nations: national-team manager and 8 clubs" % NATIONS, p


def e5(b):
    groups, pad = stream(b)
    p = []
    if any(not 0 <= -h < PLAYERS for h, _ in groups):
        p.append("player header out of range")
    if any(not CLUB_FIRST <= c < CLUB_END for _, cs in groups for c in cs):
        p.append("club outside %d-%d" % (CLUB_FIRST, CLUB_END - 1))
    multi = sum(1 for _, cs in groups if len(cs) > 1)
    return "%d players, %d clubs listed (%d players with more than one, %d with none), %d zero bytes" % (
        len(groups), sum(len(cs) for _, cs in groups), multi,
        sum(1 for _, cs in groups if not cs), pad * 2), p


def e6(b):
    t = tables(b)
    return "byte tables of %s (table 2 is never read)" % "/".join(str(len(x)) for x in t), []


def e7(b):
    t = tables(b)
    if len(t[0]) != 10 * 100 * 4:
        return "", ["%d bytes, expected 10 x 100 x 4" % len(t[0])]
    p = []
    for g in range(10):
        recs = [struct.unpack_from("<2h", t[0], g * 400 + k * 4) for k in range(100)]
        if any(not 0 <= r[0] < PLAYERS for r in recs):
            p.append("group %d: player out of range" % g)
        if [r[1] for r in recs] != sorted(r[1] for r in recs):
            p.append("group %d: thresholds not in order" % g)
    return "10 groups of 100 players with thresholds", p


def e8(b):
    t = tables(b)
    recs = [struct.unpack_from("<2h", t[0], i * 4) for i in range(len(t[0]) // 4)]
    p = []
    if [r[0] for r in recs] != list(range(SCHEDULE_UIDS)):
        p.append("UIDs are not 0-%d in order" % (SCHEDULE_UIDS - 1))
    if any(not 0 <= r[1] <= 5 for r in recs):
        p.append("kind outside 0-5")
    kinds = {}
    for _, k in recs:
        kinds[k] = kinds.get(k, 0) + 1
    return "%d UIDs; kinds %s" % (len(recs), ", ".join("%d: %d" % kv for kv in sorted(kinds.items()))), p


def e9(b):
    t = tables(b)
    sizes = [96 * 4, 32, 96, 16, 96, 16, 32]
    if [len(x) for x in t] != sizes:
        return "", ["table sizes %s, expected %s" % ([len(x) for x in t], sizes)]
    p = []
    # Map tables: 1 id32->id16, 2 id96->id16, 3 id16->id32, 4 id96->id32,
    # 5 id16->id96, 6 id32->id96 (EDIT::CColor 0x2b9aa8-0x2b9bf4).
    for i, top in ((1, 16), (2, 16), (3, 32), (4, 32), (5, 96), (6, 96)):
        if max(t[i]) >= top:
            p.append("table %d: index %d >= %d" % (i, max(t[i]), top))
    return "96 RGBA colours, index maps between 96, 32 and 16 colours", p


def e10(b):
    t = tables(b)
    return "6 x 25 bytes (STADIUM/CONV_INFO_BUILD.TBB's bytes)" if len(t[0]) == 150 else "", \
        [] if len(t[0]) == 150 else ["%d bytes, expected 150" % len(t[0])]


def e_scout(b):
    groups, pad = stream(b)
    p = []
    if any(not 0 < -h < SCOUTS for h, _ in groups):
        p.append("scout header out of range")
    if any(not 0 <= x < PLAYERS for _, xs in groups for x in xs):
        p.append("player out of range")
    return "%d groups for %d scouts, %d players, %d zero bytes" % (
        len(groups), len({h for h, _ in groups}), sum(len(xs) for _, xs in groups), pad * 2), p


def e_combi(b):
    groups, pad = stream(b, END_COMBI)
    p = []
    ends = [i for i, (h, _) in enumerate(groups) if h == END_COMBI]
    if not ends:
        p.append("no %d end marker" % END_COMBI)
    real = groups[:ends[0]] if ends else groups
    if any(not 1 <= -h <= 4 for h, _ in real):
        p.append("level outside 1-4")
    if any(len(xs) < 2 for _, xs in real):
        p.append("group with fewer than 2 players")
    # Members are database ids: players, and managers from 27,950 (0x6d2e).
    if any(not 0 <= x < PLAYERS + MANAGERS for _, xs in real for x in xs):
        p.append("member out of range")
    staff = sum(1 for _, xs in real for x in xs if x >= PLAYERS)
    sizes = {}
    for _, xs in real:
        sizes[len(xs)] = sizes.get(len(xs), 0) + 1
    return "%d groups (%s members: %s; %d managers among them), end marker, %d zero bytes" % (
        len(real), "/".join(str(k) for k in sorted(sizes)),
        ", ".join("%d" % sizes[k] for k in sorted(sizes)), staff, pad * 2), p


def e15(b):
    t = tables(b)
    v = s16s(t[0])
    p = []
    if -1 not in v:
        p.append("no 0xffff end")
    ids = v[:v.index(-1)] if -1 in v else v
    if len(ids) > 0x5dc:
        p.append("%d players; Set_InitDBSet reads 1,500" % len(ids))
    if any(not 0 <= x < PLAYERS for x in ids):
        p.append("player out of range")
    return "%d free agents, then 0xffff" % len(ids), p


PARSERS = (e0, e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e_scout, e_scout,
           e_combi, e_combi, e15)


# --- commands ----------------------------------------------------------------

def cmd_info(path):
    try:
        path, blobs = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    for i, blob in enumerate(blobs):
        try:
            line, problems = PARSERS[i](blob)
        except (ValueError, struct.error, IndexError) as e:
            line, problems = "", [str(e)]
        out = "%2d %-22s %s" % (i, NAMES[i], line)
        if problems:
            out += "  !! " + "; ".join(problems[:3])
            if len(problems) > 3:
                out += "; ... (%d)" % len(problems)
        print(out)


def pb(path, explicit):
    p = explicit or os.path.join(os.path.dirname(path), PBDATA)
    if not os.path.exists(p):
        return None
    import pbdata
    db = pbdata.PbData(p)
    return db if db.data else None


def cmd_show(path, entry, pbpath):
    path, blobs = load(path)
    b = blobs[entry]
    db = pb(path, pbpath)

    def name(kind, i):
        if db is None:
            return ""
        try:
            return db.record(kind, i).name
        except ValueError:
            return "?"

    print("entry %d: %s" % (entry, NAMES[entry]))
    if entry == 0:
        t = tables(b)
        for i in range(STATES):
            print("  state %3d  nation %3d" % (t[0][i * 2], t[0][i * 2 + 1]))
        for i in range(CITIES):
            c = struct.unpack_from("<2I4B", t[1], i * 12)
            print("  city %3d  population %8d  %s %3d  climate %2d  weather %2d  choice %d"
                  % (c[0], c[1], "state " if c[0] < STATE_CITIES else "nation", c[2], c[3], c[4], c[5]))
        for i in range(CLIMATE_ZONES):
            print("  climate %2d  %s" % (t[2][i * 13], " ".join("%3d" % x for x in struct.unpack_from("12b", t[2], i * 13 + 1))))
        for i in range(CLIMATE_ZONES):
            print("  weather %2d  %s" % (t[3][i * 13], " ".join("%2d" % x for x in t[3][i * 13 + 1:i * 13 + 13])))
        for i in range(CLIMATE_ZONES):
            print("  chances %2d  %s" % (t[4][i * 5], " ".join("%3d" % x for x in t[4][i * 5 + 1:i * 5 + 5])))
    elif entry == 4:
        t = tables(b)[0]
        for n in range(NATIONS):
            r = struct.unpack_from("<h8H", t, n * 18)
            print("  nation %3d  manager %4d %-18s clubs %s" % (
                n + 1, r[0], name("managers", r[0]), " ".join("%3d" % c for c in r[1:])))
    elif entry in (5, 11, 12, 13, 14):
        kind = {5: ("player", "players", "club"), 11: ("scout", "scouts", "player"),
                12: ("scout", "scouts", "player"), 13: ("level", None, "player"),
                14: ("level", None, "player")}[entry]
        groups, _ = stream(b, END_COMBI if entry in (13, 14) else None)
        for h, xs in groups:
            if h == END_COMBI:
                print("  end")
                break
            head = "%s %d" % (kind[0], -h)
            if kind[1]:
                head += " " + name(kind[1], -h)
            items = [str(x) + (" " + (name("players", x) if x < PLAYERS else
                                      name("managers", x - PLAYERS) + " (manager)")
                                  if kind[2] == "player" and db else "") for x in xs]
            print("  %-28s %s" % (head, ", ".join(items)))
    elif entry == 7:
        t = tables(b)[0]
        for g in range(10):
            for k in range(100):
                pl, th = struct.unpack_from("<2h", t, g * 400 + k * 4)
                print("  group %d  %3d  threshold %3d  player %5d %s" % (g, k, th, pl, name("players", pl)))
    elif entry == 8:
        t = tables(b)[0]
        for i in range(len(t) // 4):
            print("  UID %3d  kind %d" % struct.unpack_from("<2h", t, i * 4))
    elif entry == 9:
        t = tables(b)
        for i in range(96):
            print("  colour %2d  #%08x" % (i, struct.unpack_from("<I", t[0], i * 4)[0]))
        for i, label in enumerate(("32->16", "96->16", "16->32", "96->32", "16->96", "32->96"), 1):
            print("  map %s  %s" % (label, " ".join(str(x) for x in t[i])))
    elif entry == 15:
        v = s16s(tables(b)[0])
        for x in v[:v.index(-1)]:
            print("  %5d %s" % (x, name("players", x)))
    elif entry == 1:
        t = tables(b)
        for i in range(13):
            print("  region %2d  cost %d" % struct.unpack_from("<2I", t[0], i * 8))
        print("  level rates " + ", ".join("%.3f" % r for r in struct.unpack("<8f", t[1])))
    else:
        for i, x in enumerate(tables(b)):
            print("  table %d (%d bytes): %s%s" % (i, len(x), x[:48].hex(), "..." if len(x) > 48 else ""))


def _opt(args, flag):
    if flag in args:
        i = args.index(flag)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return None


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    pbpath = _opt(args, "--pbdata")
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and len(args) == 2 and args[1].isdigit() and int(args[1]) < ENTRIES:
        cmd_show(args[0], int(args[1]), pbpath)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
