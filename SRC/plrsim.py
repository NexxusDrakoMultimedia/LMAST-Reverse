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
  5  player affiliations   s16 stream: -player, then clubs (> 0), players
                           ascending for bsearch (0x2161b8, 0x216334)
  6  transfer AI           TBB, 6 byte tables (CAcquirePlayer and others)
  7  player introductions  10 groups x 100 {s16 player, s16 threshold} (0x2202f8)
  8  record kinds          164 x {s16 schedule UID, s16 PlCareerRecordKind}
  9  edit colours          TBB, EDIT::CColor: 96 RGBA colours, 6 index maps
  10 stadium ids           6 x 25 bytes (plTeam_GetStadiumDataIndex)
  11 scout exclusives      s16 stream: -scout, then players (0x21ea48)
  12 scout semi-exclusives same format
  13 good combinations     s16 stream: -level, then players and managers
  14 bad combinations      same format
                           Every stream ends at a header with no member
                           after it (-1 -1, -1000 -1000 in 13-14).
  15 free agents           u16 players, ending at 0xffff (Set_InitDBSet)

Usage:
    python plrsim.py info    <PLRESOURCESIM.PAC | DAT/PARAM>
    python plrsim.py show    <PLRESOURCESIM.PAC | DAT/PARAM> <entry> [--pbdata PBDATA.PAC]
    python plrsim.py setfree <in.PAC> <out.PAC> <slot>=<player> ...
    python plrsim.py setbranch <in.PAC> <out.PAC> <region>=<cost> ...
    python plrsim.py setgroup <in.PAC> <out.PAC> 5 <player>=<club>,... ...
    python plrsim.py setgroup <in.PAC> <out.PAC> 11|12 <scout>=<player>,... ...
    python plrsim.py setgroup <in.PAC> <out.PAC> 13|14 <group>=[<level>:]<id>,... ...
                     (several streams at once: <entry> <pair> ... <entry> <pair> ...)
    python plrsim.py roundtrip <PLRESOURCESIM.PAC | DAT/PARAM>

`show` prints one entry in readable form, naming players, managers and
scouts from PBDATA_EU.PAC next to the pack (or --pbdata). `setfree`
replaces players in the free-agent list (entry 15; slots as `show 15`
numbers them) and writes a same-size pack for patch_disc.py. `setbranch`
sets overseas branches' establishing costs (entry 1 table 0, regions
0-12); the investment to raise a level and the upkeep are that cost times
the level rates, so they follow it. `setgroup` edits a stream: a
player's clubs (5), a scout's exclusive or semi-exclusive players (11,
12), or a combination (13, 14; groups numbered as `show` numbers them,
the next number adding one, ids being database ids of players and
managers). An empty value removes the group, and a bare entry number
between pairs switches to that stream. Each entry keeps its size, so a
stream may only grow into its zero padding (entry 5 has none).
`roundtrip` re-encodes the unchanged free-agent list, branch costs and
streams through those encoders and checks that the rebuilt pack equals
the original byte for byte.
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
TRANSFER_LIST_MAX_RANK = 11              # top of the highest rank band (0x553170)
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
    # The Japanese release's pack ends at entry 14: it has no free-agent list.
    if len(blobs) not in (ENTRIES, ENTRIES - 1):
        raise ValueError("%d entries, expected %d" % (len(blobs), ENTRIES))
    return path, blobs


def tables(blob):
    return [t.data for t in tbb.parse(blob)[1]]


def s16s(b):
    return list(struct.unpack("<%dh" % (len(b) // 2), b[:len(b) // 2 * 2]))


# The s16 streams. A value at or above MEMBER_MIN is a member, anything
# below it a header: entry 5's initializer takes > 0 as a club (bgtz,
# 0x216214), the scout lookup and the combination search take >= 0 as a
# member (bgez 0x21ea74, bltz 0x215e18). Every reader stops at a header
# with no member after it, so the disc ends each stream with two headers
# (-1 -1, or -1000 -1000 in 13-14) and zeros after.
STREAMS = (5, 11, 12, 13, 14)
MEMBER_MIN = {5: 1, 11: 0, 12: 0, 13: 0, 14: 0}
AFFIL_ROOM = 0x817c // 4                 # PlayerAffiliateaSearchTableInitialize's pointer table


def stream(b, entry):
    """(groups, end, pad) of stream entry `entry`: groups [(header,
    [members])] up to the end marker, `end` the values from the marker to
    the zero padding, `pad` the number of zero s16 after it."""
    v = s16s(b)
    lo = MEMBER_MIN[entry]
    groups = []
    i = 0
    while i < len(v):
        if v[i] >= lo:
            raise ValueError("value %d at s16 %d where a header should be" % (v[i], i))
        j = i + 1
        while j < len(v) and v[j] >= lo:
            j += 1
        if j == i + 1:
            break                        # a header with no member: every reader stops here
        groups.append((v[i], v[i + 1:j]))
        i = j
    else:
        raise ValueError("no end marker")
    rest = v[i:]
    stop = len(rest)
    while stop and rest[stop - 1] == 0:
        stop -= 1
    return groups, rest[:stop], len(rest) - stop


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


def end_text(end):
    return "end %s" % " ".join(str(x) for x in end)


def e5(b):
    groups, end, pad = stream(b, 5)
    p = check_groups(5, [(-h, xs) for h, xs in groups])
    multi = sum(1 for _, cs in groups if len(cs) > 1)
    return "%d players, %d clubs listed (%d players with more than one), %s, %d zero bytes" % (
        len(groups), sum(len(cs) for _, cs in groups), multi, end_text(end), pad * 2), p[:3]


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


def e_scout(b, entry):
    groups, end, pad = stream(b, entry)
    p = check_groups(entry, [(-h, xs) for h, xs in groups])
    return "%d scouts, %d players, %s, %d zero bytes" % (
        len(groups), sum(len(xs) for _, xs in groups), end_text(end), pad * 2), p[:3]


def e_combi(b, entry):
    groups, end, pad = stream(b, entry)
    p = check_groups(entry, [(-h, xs) for h, xs in groups])
    if end != [END_COMBI] * 2:
        p.append("end %s, expected %d %d" % (end, END_COMBI, END_COMBI))
    staff = sum(1 for _, xs in groups for x in xs if x >= PLAYERS)
    sizes = {}
    for _, xs in groups:
        sizes[len(xs)] = sizes.get(len(xs), 0) + 1
    return "%d groups (%s members: %s; %d managers among them), %s, %d zero bytes" % (
        len(groups), "/".join(str(k) for k in sorted(sizes)),
        ", ".join("%d" % sizes[k] for k in sorted(sizes)), staff, end_text(end), pad * 2), p[:3]


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


PARSERS = (e0, e1, e2, e3, e4, e5, e6, e7, e8, e9, e10,
           lambda b: e_scout(b, 11), lambda b: e_scout(b, 12),
           lambda b: e_combi(b, 13), lambda b: e_combi(b, 14), e15)


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
    if len(blobs) < ENTRIES:
        print("%2d %-22s none: the pack ends at entry %d (as in the Japanese release)" % (
            ENTRIES - 1, NAMES[ENTRIES - 1], len(blobs) - 1))


def pb(path, explicit):
    p = explicit or os.path.join(os.path.dirname(path), PBDATA)
    if not os.path.exists(p):
        return None
    import pbdata
    db = pbdata.PbData(p)
    return db if db.data else None


def cmd_show(path, entry, pbpath):
    path, blobs = load(path)
    if entry >= len(blobs):
        raise SystemExit("%s has no entry %d (%s)" % (path, entry, NAMES[entry]))
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
        # The Japanese release's tables are shorter (44, 49 and 27 whole
        # records); show the whole records there are.
        for i in range(min(CLIMATE_ZONES, len(t[2]) // 13)):
            print("  climate %2d  %s" % (t[2][i * 13], " ".join("%3d" % x for x in struct.unpack_from("12b", t[2], i * 13 + 1))))
        for i in range(min(CLIMATE_ZONES, len(t[3]) // 13)):
            print("  weather %2d  %s" % (t[3][i * 13], " ".join("%2d" % x for x in t[3][i * 13 + 1:i * 13 + 13])))
        for i in range(min(CLIMATE_ZONES, len(t[4]) // 5)):
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
        groups, end, _ = stream(b, entry)
        for g, (h, xs) in enumerate(groups):
            # Combinations are numbered by place, as setgroup takes them.
            head = ("group %3d  " % g if entry in (13, 14) else "") + "%s %d" % (kind[0], -h)
            if kind[1]:
                head += " " + name(kind[1], -h)
            items = [str(x) + (" " + (name("players", x) if x < PLAYERS else
                                      name("managers", x - PLAYERS) + " (manager)")
                                  if kind[2] == "player" and db else "") for x in xs]
            print("  %-28s %s" % (head, ", ".join(items)))
        print("  " + end_text(end))
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
        for i, x in enumerate(v[:v.index(-1)]):
            print("  %4d  %5d %s" % (i, x, name("players", x)))
    elif entry == 1:
        t = tables(b)
        for i in range(13):
            print("  region %2d  cost %d" % struct.unpack_from("<2I", t[0], i * 8))
        print("  level rates " + ", ".join("%.3f" % r for r in struct.unpack("<8f", t[1])))
    else:
        for i, x in enumerate(tables(b)):
            print("  table %d (%d bytes): %s%s" % (i, len(x), x[:48].hex(), "..." if len(x) > 48 else ""))


def free_agents(data):
    """The free-agent list (entry 15) of a whole pack, as player ids."""
    h, blobs = pac.binpac_blobs(data)
    end, raw = tbb.parse(blobs[15])
    v = s16s(raw[0].data)
    return v[:v.index(-1)]


def encode_free(data, ids):
    """The pack `data` with its free-agent list replaced by `ids`, the same
    length as the old list. Whatever follows the 0xffff end is kept."""
    h, blobs = pac.binpac_blobs(data)
    end, raw = tbb.parse(blobs[15])
    v = s16s(raw[0].data)
    count = v.index(-1)
    if len(ids) != count:
        raise ValueError("%d players; the list holds %d" % (len(ids), count))
    v[:count] = ids
    raw[0].data = struct.pack("<%dh" % len(v), *v)
    blobs[15] = tbb.build(raw, end, tbb.trailer(blobs[15], raw))
    return pac.build_binpac(data[:h.header_size], blobs)


BRANCH_REGIONS = 13                      # entry 1 table 0 (_GetOverseasBranchEstablishCapital)


def branch_costs(data):
    """The 13 overseas branches' establishing costs (entry 1 table 0) of a
    whole pack, by region."""
    _, blobs = pac.binpac_blobs(data)
    t = tables(blobs[1])[0]
    pairs = [struct.unpack_from("<2I", t, 8 * i) for i in range(BRANCH_REGIONS)]
    if [r for r, _ in pairs] != list(range(BRANCH_REGIONS)):
        raise ValueError("entry 1: regions are not 0-12 in order")
    return [c for _, c in pairs]


def encode_branch_costs(data, costs):
    """The pack `data` with entry 1's establishing costs replaced by `costs`
    (13, by region). The level rates and the other entries are kept."""
    if len(costs) != BRANCH_REGIONS or not all(0 < c < 1 << 32 for c in costs):
        raise ValueError("expected 13 costs of 1 to 4,294,967,295")
    h, blobs = pac.binpac_blobs(data)
    end, raw = tbb.parse(blobs[1])
    raw[0].data = b"".join(struct.pack("<2I", r, c) for r, c in enumerate(costs)) +         raw[0].data[8 * BRANCH_REGIONS:]
    blobs[1] = tbb.build(raw, end, tbb.trailer(blobs[1], raw))
    return pac.build_binpac(data[:h.header_size], blobs)


def cmd_setbranch(src, dst, pairs):
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(src, "rb") as f:
        data = f.read()
    costs = branch_costs(data)
    for pair in pairs:
        region, sep, cost = pair.partition("=")
        if not sep or not region.isdigit() or not cost.isdigit():
            raise SystemExit("expected <region>=<cost>, got %r" % pair)
        if not 0 <= int(region) < BRANCH_REGIONS:
            raise SystemExit("region %s: regions are 0-%d" % (region, BRANCH_REGIONS - 1))
        print("region %s: %d -> %s" % (region, costs[int(region)], cost))
        costs[int(region)] = int(cost)
    try:
        out = encode_branch_costs(data, costs)
    except ValueError as e:
        raise SystemExit(str(e))
    if len(out) != len(data):
        raise SystemExit("rebuilt pack is %d bytes, not %d" % (len(out), len(data)))
    with open(dst, "wb") as f:
        f.write(out)
    print("wrote %s" % dst)


# --- the streams (entries 5, 11-14) -------------------------------------------

def check_groups(entry, groups):
    """Problems with stream groups [(key, [members])], key the negated
    header: a player (5), a scout index (11-12) or a level (13-14)."""
    p = []
    keys = [k for k, _ in groups]
    if any(not xs for _, xs in groups):
        p.append("a group with no member would end the stream")
    # Entry 5 is exempt: player 11,811 lists club 398 twice on both
    # releases, which the search doesn't mind.
    if entry != 5 and any(len(set(xs)) != len(xs) for _, xs in groups):
        p.append("a member listed twice in one group")
    if entry == 5:
        if any(not 0 <= k < PLAYERS for k in keys):
            p.append("player outside 0-%d" % (PLAYERS - 1))
        # bsearch (0x216334) with CompPlayerNo (0x2162b0): players ascending.
        if any(a >= b for a, b in zip(keys, keys[1:])):
            p.append("players not in ascending order, or listed twice")
        # The end marker's first header takes a pointer too.
        if len(keys) + 1 > AFFIL_ROOM:
            p.append("%d players; the search table holds %d" % (len(keys), AFFIL_ROOM - 1))
        if any(not CLUB_FIRST <= c < CLUB_END for _, xs in groups for c in xs):
            p.append("club outside %d-%d" % (CLUB_FIRST, CLUB_END - 1))
    elif entry in (11, 12):
        if any(not 0 < k < SCOUTS for k in keys):
            p.append("scout outside 1-%d" % (SCOUTS - 1))
        # The lookup (0x21ea48) stops at a scout's first group.
        if len(set(keys)) != len(keys):
            p.append("a scout listed twice")
        if any(not 0 <= x < PLAYERS for _, xs in groups for x in xs):
            p.append("player outside 0-%d" % (PLAYERS - 1))
    else:
        if any(not 1 <= k <= 4 for k in keys):
            p.append("level outside 1-4")
        # plMisc_GetGoodLevel (0x215df8) needs two members of one group.
        if any(len(xs) < 2 for _, xs in groups):
            p.append("a group with fewer than 2 members")
        # Members are database ids: players, and managers from 27,950 (0x6d2e).
        if any(not 0 <= x < PLAYERS + MANAGERS for _, xs in groups for x in xs):
            p.append("member outside 0-%d" % (PLAYERS + MANAGERS - 1))
    return p


def groups(data, entry):
    """Stream entry `entry` of a whole pack, as [[key, [members]]] in stream
    order (key as check_groups takes it)."""
    _, blobs = pac.binpac_blobs(data)
    gs, _, _ = stream(blobs[entry], entry)
    return [[-h, list(xs)] for h, xs in gs]


def encode_groups(data, entry, gs):
    """The pack `data` with stream entry `entry` rebuilt from `gs`, keeping
    the end marker and the entry's size: the zero padding takes up the
    difference. Raises ValueError for groups check_groups refuses, or for
    a stream that no longer fits."""
    p = check_groups(entry, gs)
    if p:
        raise ValueError("entry %d: %s" % (entry, "; ".join(p)))
    h, blobs = pac.binpac_blobs(data)
    old = blobs[entry]
    _, end, _ = stream(old, entry)
    v = [x for k, xs in gs for x in [-k] + xs] + end
    if 2 * len(v) > len(old):
        raise ValueError("entry %d: the stream needs %d bytes; the entry holds %d (%d over)"
                         % (entry, 2 * len(v), len(old), 2 * len(v) - len(old)))
    blobs[entry] = struct.pack("<%dh" % len(v), *v) + bytes(len(old) - 2 * len(v))
    return pac.build_binpac(data[:h.header_size], blobs)


def set_group(entry, gs, key, members, level=None):
    """Edit the groups `gs` (as groups() returns them) in place, as
    `setgroup` does, and return the old members ([] for a new group).
    Entries 5, 11 and 12: `key` is the player or scout; `members` replace
    its clubs or players, and [] removes it. A new player goes in player
    order, a new scout at the end. Entries 13 and 14: `key` is the group's
    place (len(gs) adds one at the end), `level` its level (None keeps
    it), and [] removes it. Raises ValueError for anything check_groups
    would refuse."""
    if entry in (13, 14):
        if not 0 <= key <= len(gs):
            raise ValueError("group %d: there are groups 0-%d, and %d adds one"
                             % (key, len(gs) - 1, len(gs)))
        trial = [list(g) for g in gs]
        if key == len(gs):
            if not members:
                raise ValueError("group %d: a new group needs members" % key)
            trial.append([level or 1, list(members)])
            old = []
        elif not members:
            old = trial.pop(key)[1]
        else:
            old = trial[key][1]
            trial[key] = [trial[key][0] if level is None else level, list(members)]
    else:
        keys = [k for k, _ in gs]
        trial = [list(g) for g in gs]
        if key in keys:
            i = keys.index(key)
            old = trial[i][1]
            if members:
                trial[i][1] = list(members)
            else:
                del trial[i]
        else:
            if not members:
                raise ValueError("%s %d has no group to remove" % ("player" if entry == 5 else "scout", key))
            old = []
            if entry == 5:
                i = 0
                while i < len(keys) and keys[i] < key:
                    i += 1
                trial.insert(i, [key, list(members)])
            else:
                trial.append([key, list(members)])
    p = check_groups(entry, trial)
    if p:
        raise ValueError("; ".join(p))
    gs[:] = trial
    return old


def parse_ids(text):
    """'1,2,3' as [1, 2, 3]; '' as []."""
    if not text:
        return []
    out = []
    for x in text.split(","):
        if not x.strip().isdigit():
            raise ValueError("expected numbers separated by commas, got %r" % text)
        out.append(int(x))
    return out


def group_arg(entry, key, members, level=None):
    """The `setgroup` argument for one set_group call."""
    ids = ",".join(str(x) for x in members)
    if entry in (13, 14) and level is not None and members:
        ids = "%d:%s" % (level, ids)
    return "%d=%s" % (key, ids)


def cmd_setgroup(src, dst, args):
    """setgroup <in> <out> <entry> <pair> ... [<entry> <pair> ...]: a bare
    number picks the stream the pairs after it edit."""
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(src, "rb") as f:
        data = f.read()
    entry, edited = None, {}
    for pair in args:
        if pair.isdigit():
            entry = int(pair)
            if entry not in STREAMS:
                raise SystemExit("entry %d: the streams are %s" % (entry, ", ".join(map(str, STREAMS))))
            if entry not in edited:
                edited[entry] = groups(data, entry)
            continue
        if entry is None:
            raise SystemExit("give an entry (%s) before %r" % (", ".join(map(str, STREAMS)), pair))
        key, sep, value = pair.partition("=")
        level = None
        try:
            if not sep or not key.isdigit():
                raise ValueError("expected <key>=<id>,<id>..., got %r" % pair)
            if entry in (13, 14) and ":" in value:
                lv, _, value = value.partition(":")
                if not lv.isdigit():
                    raise ValueError("expected <group>=<level>:<id>,<id>..., got %r" % pair)
                level = int(lv)
            old = set_group(entry, edited[entry], int(key), parse_ids(value), level)
        except ValueError as e:
            raise SystemExit("entry %d %s: %s" % (entry, pair, e))
        print("entry %d %s %s: %s -> %s" % (entry, ("player", "scout", "scout", "group", "group")[
            STREAMS.index(entry)], key, ",".join(map(str, old)) or "(none)", value or "(removed)"))
    out = data
    try:
        for entry, gs in edited.items():
            out = encode_groups(out, entry, gs)
    except ValueError as e:
        raise SystemExit(str(e))
    if len(out) != len(data):
        raise SystemExit("rebuilt pack is %d bytes, not %d" % (len(out), len(data)))
    with open(dst, "wb") as f:
        f.write(out)
    print("wrote %s" % dst)


def cmd_roundtrip(path):
    path, blobs = load(path)
    with open(path, "rb") as f:
        data = f.read()
    try:
        out = encode_branch_costs(data, branch_costs(data))   # the encoder setbranch uses
    except (ValueError, struct.error) as e:
        print("entry 1: !! %s" % e)
    else:
        print("entry 1: %d branch costs  %s" % (BRANCH_REGIONS, "rebuilt pack identical"
                                                if out == data else "!! rebuilt pack differs"))
    for e in STREAMS:
        try:
            gs = groups(data, e)
            out = encode_groups(data, e, gs)            # the encoder setgroup uses
        except (ValueError, struct.error) as err:
            print("entry %d: !! %s" % (e, err))
            continue
        print("entry %d: %d groups  %s" % (e, len(gs), "rebuilt pack identical"
                                           if out == data else "!! rebuilt pack differs"))
    if len(blobs) <= 15:
        print("%s: %d entries, no free-agent list to rebuild" % (path, len(blobs)))
        return
    ids = free_agents(data)
    try:
        out = encode_free(data, ids)                    # the encoder setfree uses
    except (ValueError, struct.error) as e:
        print("%s: !! %s" % (path, e))
        return
    same = free_agents(out) == ids
    print("entry 15: %d free agents  %s" % (len(ids), "identical" if same else "!! re-read list differs"))
    print("%s: %s" % (path, "rebuilt pack identical" if out == data else "!! rebuilt pack differs"))


def set_free(ids, slot, player):
    """Put `player` in free-agent slot `slot` of the list `ids` (as
    free_agents returns it), as `setfree` does. Returns the old player.
    Raises ValueError for a slot or player out of range, or a player the
    list already holds (the disc's list has no repeats)."""
    if not 0 <= slot < len(ids):
        raise ValueError("slot %d: the list has slots 0-%d" % (slot, len(ids) - 1))
    if not 0 <= player < PLAYERS:
        raise ValueError("player %d: players are 0-%d" % (player, PLAYERS - 1))
    if player in ids and ids.index(player) != slot:
        raise ValueError("player %d is already in the list (slot %d)" % (player, ids.index(player)))
    old = ids[slot]
    ids[slot] = player
    return old


def cmd_setfree(src, dst, pairs):
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(src, "rb") as f:
        data = f.read()
    v = free_agents(data)
    for pair in pairs:
        slot, sep, player = pair.partition("=")
        if not sep or not slot.isdigit() or not player.isdigit():
            raise SystemExit("expected <slot>=<player>, got %r" % pair)
        try:
            old = set_free(v, int(slot), int(player))
        except ValueError as e:
            raise SystemExit(str(e))
        print("slot %s: %d -> %s" % (slot, old, player))
    out = encode_free(data, v)
    if len(out) != len(data):
        raise SystemExit("rebuilt pack is %d bytes, not %d" % (len(out), len(data)))
    with open(dst, "wb") as f:
        f.write(out)
    print("wrote %s" % dst)


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
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    elif cmd == "setfree" and len(args) >= 3:
        cmd_setfree(args[0], args[1], args[2:])
    elif cmd == "setbranch" and len(args) >= 3:
        cmd_setbranch(args[0], args[1], args[2:])
    elif cmd == "setgroup" and len(args) >= 4:
        cmd_setgroup(args[0], args[1], args[2:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
