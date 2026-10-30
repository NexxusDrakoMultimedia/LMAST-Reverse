# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for PARAM/PLRESOURCECOMMON.PAC, the common resource pack of
Let's Make a Soccer Team! (PS2): plResource entry 0. Five TBB entries; every
reader calls plResource_GetResourceDataBinPacTbbTbl(0, entry, table) with
constant arguments (SLES 0x21e9e0). See DOC/PLRESOURCECOMMON_FORMAT.md.

  0  facilities    9 tables of records (plTeam_Get*Db, SLES 0x2299d0-0x229c28):
                   sites 0x1c, training-ground equipment 0x34, stadium
                   equipment 0x20, club houses 0x28, club-house equipment
                   0x20, youth-house equipment 0x20, office equipment 0x18
                   (4 kinds x 3 levels), stadiums 0x80, stadium adverts 0x14.
                   Build time from plTeam_Build*, upkeep from payment_Equip
                   (0x251fb8), stadium capacity from
                   pwkUnkei_GetStandAllCapacity (0x271b48)
  1  formations    7 byte tables (plTeam_FormationID2Formation,
                   PitchArea2Apos, AreaMatrix2AreaMy/Com, GetSystem2PosNum,
                   GetPosNumLimit, GetAPosNumLimit)
  2  hexagon       512 bytes (plPinfo_CalcHexAbil)
  3  nations       13 regions, 146 nations, 83 national teams, 460 clubs
                   (plMisc_DRegion2Region, Nati2DRegion, Nati2NatiTeam,
                   NatiTeam2Nati, Nati2EU, Club2Nati)
  4  competitions  7 x 22 bytes, each nation's divisions and cups
                   (0x20fbf0: plCompeData_getScheCompe_FromNationDiv,
                   getUID_FromNationDiv), 96 x 8 bytes
                   (plCompeData_getCupUID_FromNation)

Usage:
    python plrcommon.py info      <PLRESOURCECOMMON.PAC | DAT/PARAM>
    python plrcommon.py show      <PLRESOURCECOMMON.PAC | DAT/PARAM> <entry>.<table>
    python plrcommon.py set       <in.PAC> <out.PAC> <table>:<record>:<field>=<value> ...
    python plrcommon.py roundtrip <PLRESOURCECOMMON.PAC | DAT/PARAM>

`show` prints one table: records with their named fields for entry 0, nation
names (from PBDATA_EU.PAC and DAT/MESSAGE/MES.PAC) for entry 3, and the raw
rows otherwise.

`set` edits the facility records of entry 0, for example
`0.3:1:cost=60000000` (club house 1's build cost). The fields:
    cost, cost2, cost_b, cost2_b   build costs, in the stored money unit
                                   (pound = 6), 0-2147483647. The game charges
                                   them x the business cycle (75-125%) x any
                                   sponsor discount (DOC/ECONOMY.md); cost2 is
                                   the second, smaller cost of the equipment
    upkeep, upkeep_b               monthly upkeep, same unit and range
    time, time0-time2              build time in turns, 0-255
    capacity0-capacity2            a stadium level's capacity, 1-2147483647
Training-ground equipment (0.1) has the _b fields for the slots past the
club's first group; stadiums (0.7) have cost, time0-2, capacity0-2 and the
per-stand upkeep. `roundtrip` rebuilds the pack, then edits each field of
each record on its own and checks that only that field's word changes.
"""
import os
import struct
import sys

import pac
import tbb

FILE = "PLRESOURCECOMMON.PAC"
NATIONS, NATIONAL_TEAMS, REGIONS, CLUBS = 146, 83, 13, 460

# The kinds of editable field, with the values `set` allows. Money is in the
# stored unit, read with lw (signed), so it stays below 2^31; the build is
# charged as cost x business cycle (up to 125%) x sponsor discount in 64
# bits (SIMPRG 0x154b78). Build times are read with lbu (plTeam_BuildSite
# 0x229d74, plTeam_BuildChouse 0x22a928). A capacity of 0 would divide by
# zero in pwkUnkei_BeforeReport (0x272f9c).
MONEY, TURNS, CAPACITY = "money", "turns", "capacity"
RANGES = {MONEY: (0, 0x7fffffff), TURNS: (0, 0xff), CAPACITY: (1, 0x7fffffff)}

# (entry, table): (name, reader, record size, documented size,
#                  {offset: (field, kind)})
# Record sizes are the getters' index scaling. Every field is read by the code
# named in DOC/PLRESOURCECOMMON_FORMAT.md and DOC/ECONOMY.md: the build cost
# getters behind SIMPRG 0x154b78 (cost, cost2), its upkeep mode (upkeep, as
# the facility window shows it; payment_Equip 0x251fb8 charges the same word
# where it charges one), plTeam_Build* (time) and
# pwkUnkei_GetStandAllCapacity 0x271b48 (capacity). Training-ground equipment
# past the club's first group of slots uses the _b fields (0x1550f0).
FACILITY = {
    (0, 0): ("sites", "plTeam_GetSiteDb", 0x1c, 84,
             {0x8: ("cost", MONEY), 0xc: ("time", TURNS), 0x10: ("upkeep", MONEY)}),
    (0, 1): ("training-ground equipment", "plTeam_GetGrEquipsDb", 0x34, 520,
             {0xc: ("cost", MONEY), 0x10: ("time", TURNS), 0x14: ("upkeep", MONEY),
              0x1c: ("cost2", MONEY), 0x20: ("cost_b", MONEY),
              0x28: ("upkeep_b", MONEY), 0x30: ("cost2_b", MONEY)}),
    (0, 2): ("stadium equipment", "plTeam_GetStEquipsDb", 0x20, 512,
             {0xc: ("cost", MONEY), 0x10: ("time", TURNS), 0x14: ("upkeep", MONEY),
              0x1c: ("cost2", MONEY)}),
    (0, 3): ("club houses", "plTeam_GetChouseDb", 0x28, 120,
             {0xc: ("cost", MONEY), 0x10: ("time", TURNS), 0x14: ("upkeep", MONEY)}),
    (0, 4): ("club-house equipment", "plTeam_GetDChEquipsDb", 0x20, 1152,
             {0xc: ("cost", MONEY), 0x10: ("time", TURNS), 0x14: ("upkeep", MONEY),
              0x1c: ("cost2", MONEY)}),
    (0, 5): ("youth-house equipment", "plTeam_GetDAcEquipsDb", 0x20, 576,
             {0xc: ("cost", MONEY), 0x10: ("time", TURNS), 0x14: ("upkeep", MONEY),
              0x1c: ("cost2", MONEY)}),
    (0, 6): ("office equipment", "plTeam_GetOfEquipsDb", 0x18, 288,
             {0x8: ("cost", MONEY), 0xc: ("time", TURNS), 0x10: ("upkeep", MONEY)}),
    (0, 7): ("stadiums", "plTeam_GetStadiumDb", 0x80, 1152,
             {0x2c: ("cost", MONEY),
              0x30: ("time0", TURNS), 0x38: ("capacity0", CAPACITY),
              0x40: ("time1", TURNS), 0x48: ("capacity1", CAPACITY),
              0x50: ("time2", TURNS), 0x58: ("capacity2", CAPACITY),
              0x64: ("upkeep", MONEY)}),
    (0, 8): ("stadium adverts", "plTeam_GetStAdvertiseDb", 0x14, 120,
             {0x8: ("cost", MONEY), 0xc: ("time", TURNS), 0x10: ("upkeep", MONEY)}),
}
STADIUM_LEVELS, STADIUM_LEVEL, STADIUM_CAPACITY = 3, 0x10, 0x38
# Byte tables: (entry, table): (name, reader, size)
BYTES = {
    (1, 0): ("formation ids", "plTeam_FormationID2Formation", 700),
    (1, 1): ("pitch area to position", "plTeam_PitchArea2Apos", 90),
    (1, 2): ("area matrix, own team", "plTeam_AreaMatrix2AreaMy", 1419),
    (1, 3): ("area matrix, opponents", "plTeam_AreaMatrix2AreaCom", 1419),
    (1, 4): ("system to position counts", "plTeam_GetSystem2PosNum", 32),
    (1, 5): ("position count limits", "plTeam_GetPosNumLimit", 8),
    (1, 6): ("area position count limits", "plTeam_GetAPosNumLimit", 26),
    (2, 0): ("hexagon abilities", "plPinfo_CalcHexAbil", 512),
    (3, 0): ("region of each display region", "plMisc_DRegion2Region", REGIONS),
    (3, 1): ("display region of each nation", "plMisc_Nati2DRegion", NATIONS),
    (3, 2): ("national team of each nation (u16)", "plMisc_Nati2NatiTeam", NATIONS * 2),
    (3, 3): ("nation of each national team", "plMisc_NatiTeam2Nati", NATIONAL_TEAMS),
    (3, 4): ("EU member flag of each nation", "plMisc_Nati2EU", NATIONS),
    (3, 5): ("nation of each team", "plMisc_Club2Nati", CLUBS),
    (4, 0): ("divisions and cups by nation, 7 x 22", "0x20fbf0, plCompeData_getUID_FromNationDiv", 154),
    (4, 1): ("cup UIDs by nation, 96 x 8", "plCompeData_getCupUID_FromNation", 768),
}
TABLE_COUNTS = (9, 7, 1, 6, 2)
NATIONAL_TEAM_FIRST = 0x1cc        # team id of the first national team (table 3.2)


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        return load_bytes(f.read(), path)


def load_bytes(data, path=FILE):
    _, blobs = pac.binpac_blobs(data)
    if len(blobs) != len(TABLE_COUNTS):
        raise ValueError("%d entries, expected %d" % (len(blobs), len(TABLE_COUNTS)))
    return path, [[t.data for t in tbb.parse(b)[1]] for b in blobs]


def records(data, size):
    return [data[i:i + size] for i in range(0, len(data), size)]


def facility_key(text):
    """(0, table) from "0.<table>" (or "<table>"), for a facility table."""
    e, sep, t = text.partition(".")
    if not sep:
        e, t = "0", e
    if not (e.isdigit() and t.isdigit()) or (int(e), int(t)) not in FACILITY:
        raise ValueError("no facility table %r: they are 0.0-0.8" % text)
    return int(e), int(t)


def field(key, name):
    """(offset, kind) of the facility field `name` in table `key`."""
    for off, (fname, kind) in FACILITY[key][4].items():
        if fname == name:
            return off, kind
    raise ValueError("table %d.%d has no field %r; it has %s" % (
        key + (name, ", ".join(f for f, _ in FACILITY[key][4].values()))))


def edit_spec(key, name):
    """How an editor may change a facility field: ("range", low, high)."""
    return ("range",) + RANGES[field(key, name)[1]]


def get_field(tables, key, record, name):
    off, _ = field(key, name)
    size = FACILITY[key][2]
    return struct.unpack_from("<i", tables[key[1]], record * size + off)[0]


def set_field(tables, key, record, name, value):
    """Write `value` into one field of entry 0's `tables` (bytearrays, as
    load gives them after copying). Returns the old value. Raises
    ValueError for a record, field or value out of range."""
    off, kind = field(key, name)
    size = FACILITY[key][2]
    count = len(tables[key[1]]) // size
    if not 0 <= record < count:
        raise ValueError("table %d.%d has records 0-%d" % (key + (count - 1,)))
    lo, hi = RANGES[kind]
    if not lo <= value <= hi:
        raise ValueError("%s %d: allowed %d-%d" % (name, value, lo, hi))
    old = get_field(tables, key, record, name)
    struct.pack_into("<i", tables[key[1]], record * size + off, value)
    return old


def encode(data, tables):
    """The pack `data` with entry 0's tables replaced by `tables`, each the
    size of the table it replaces. The other entries are kept as they are."""
    h, blobs = pac.binpac_blobs(data)
    end, raw = tbb.parse(blobs[0])
    if len(tables) != len(raw):
        raise ValueError("%d tables for %d in entry 0" % (len(tables), len(raw)))
    for t, new in zip(raw, tables):
        if len(new) != len(t.data):
            raise ValueError("table 0.%d: %d bytes, not %d" % (t.index, len(new), len(t.data)))
        t.data = bytes(new)
    blobs[0] = tbb.build(raw, end, tbb.trailer(blobs[0], raw))
    return pac.build_binpac(data[:h.header_size], blobs)


def check(entries):
    """[(entry.table, line, [problems])] for every table."""
    out = []
    for e, count in enumerate(TABLE_COUNTS):
        if len(entries[e]) != count:
            out.append(("%d" % e, "", ["%d tables, expected %d" % (len(entries[e]), count)]))
            continue
        for t, data in enumerate(entries[e]):
            key, probs = (e, t), []
            if key in FACILITY:
                name, reader, size, total, _ = FACILITY[key]
                if len(data) != total:
                    probs.append("%d bytes, expected %d" % (len(data), total))
                line = "%-36s %3d x 0x%02x  (%s)" % (name, len(data) // size, size, reader)
                if key == (0, 7):
                    for i, r in enumerate(records(data, size)):
                        caps = [struct.unpack_from("<i", r, STADIUM_CAPACITY + STADIUM_LEVEL * k)[0]
                                for k in range(STADIUM_LEVELS)]
                        if caps[0] <= 0:
                            probs.append("stadium %d has capacity %d" % (i, caps[0]))
            else:
                name, reader, total = BYTES[key]
                if len(data) != total:
                    probs.append("%d bytes, expected %d" % (len(data), total))
                line = "%-36s %4d bytes   (%s)" % (name, len(data), reader)
                if key == (3, 5):
                    bad = [i for i, n in enumerate(data) if n >= NATIONS]
                    if bad:
                        probs.append("nation out of range for teams %s" % bad[:5])
                elif key == (3, 3):
                    bad = [i for i, n in enumerate(data) if not 0 < n < NATIONS]
                    if bad:
                        probs.append("nation out of range for national teams %s" % bad[:5])
            out.append(("%d.%d" % key, line, probs))
    return out


def cmd_info(path):
    try:
        path, entries = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    print(path)
    for key, line, probs in check(entries):
        print("  %-4s %s%s" % (key, line, "  !! " + "; ".join(probs) if probs else ""))


def nation_names(path):
    import pbdata
    root = os.path.dirname(path)
    mes = os.path.join(os.path.dirname(root), "MESSAGE", "MES.PAC")
    return pbdata.nation_names(os.path.join(root, "PBDATA_EU.PAC"), mes)


def cmd_show(path, entry, table):
    path, entries = load(path)
    data = entries[entry][table]
    key = (entry, table)
    if key in FACILITY:
        name, reader, size, _, fields = FACILITY[key]
        print("%d.%d %s (%s), 0x%x bytes each" % (entry, table, name, reader, size))
        for i, r in enumerate(records(data, size)):
            words = struct.unpack("<%di" % (size // 4), r)
            named = ", ".join("%s %d" % (fields[o][0], words[o // 4]) for o in sorted(fields))
            print("  %2d  %s" % (i, named))
            print("      words: %s" % " ".join("%d" % w for w in words))
        return
    name, reader, _ = BYTES[key]
    print("%d.%d %s (%s)" % (entry, table, name, reader))
    if entry == 3:
        nations = nation_names(path)
        label = lambda n: "%d %s" % (n, nations.get(n, ""))
        if table == 2:
            for n, team in enumerate(struct.unpack("<%dH" % (len(data) // 2), data)):
                print("  nation %-24s team %d" % (label(n), team))
        elif table == 3:
            for i, n in enumerate(data):
                print("  national team %2d (team %d)  nation %s" % (
                    i, NATIONAL_TEAM_FIRST + i, label(n)))
        elif table in (1, 4):
            for n, v in enumerate(data):
                print("  nation %-24s %d" % (label(n), v))
        elif table == 5:
            for team, n in enumerate(data):
                print("  team %3d  nation %s" % (team, label(n)))
        else:
            print("  " + " ".join("%d" % v for v in data))
        return
    width = {(4, 0): 22, (4, 1): 8}.get(key, 16)
    for i in range(0, len(data), width):
        print("  %4d  %s" % (i // width if key[0] == 4 else i, data[i:i + width].hex(" ")))


# The LMASTER Mod's facility tiers (DOC/LMASTER_MOD.md#improvements): the
# bigger club houses, sites and stadiums cost much more to build and keep
# up, everything else costs twice as much. (table, record): (build cost x,
# upkeep x); records not named take FLAT. Fields holding 0 or -1 (what a
# club starts with, upkeep the game never charges) are left alone. The
# stand costs of a stadium (+0x5c, not traced in full) are left alone too.
FLAT = (2, 2)
TIERS = {
    (0, 0): {1: (2, 2), 2: (4, 4)},                     # grounds (sites)
    (0, 3): {0: (1, 2), 1: (2, 2), 2: (4, 4)},          # club houses
    (0, 7): {2: (2, 2), 3: (2, 2), 4: (2, 2), 5: (2, 2),    # 15,000-25,000
             6: (3, 3), 7: (5, 4), 8: (3.5, 6)},        # 30,000-40,000; 50,000-60,000; 110,000
}
TIER_COST = ("cost", "cost2", "cost_b", "cost2_b")
TIER_UPKEEP = ("upkeep", "upkeep_b")
# Club house 1's build cost on the retail disc and with the tiers.
TIER_MARK = ((0, 3), 1, "cost", 45000000, 90000000)


def facility_tiers(data):
    """PLRESOURCECOMMON.PAC with the facility tiers applied; None when it
    already has them. Raises ValueError for a pack that is neither."""
    _, entries = load_bytes(data)
    tables = [bytearray(t) for t in entries[0]]
    key, record, name, retail, tiered = TIER_MARK
    held = get_field(tables, key, record, name)
    if held == tiered:
        return None
    if held != retail:
        raise ValueError("%s: club house 1 costs %d, expected %d; not the retail pack?"
                         % (FILE, held, retail))
    for key in sorted(FACILITY):
        fields = [f for f, _ in FACILITY[key][4].values()]
        size = FACILITY[key][2]
        for record in range(len(tables[key[1]]) // size):
            if key in TIERS and record not in TIERS[key]:
                continue
            cost_x, upkeep_x = TIERS.get(key, {}).get(record, FLAT)
            for name in fields:
                x = cost_x if name in TIER_COST else upkeep_x if name in TIER_UPKEEP else 1
                value = get_field(tables, key, record, name)
                if x != 1 and value > 0:
                    set_field(tables, key, record, name, int(value * x))
    return encode(data, tables)


# The LMASTER Mod's Special stadium (DOC/LMASTER_MOD.md#stadiums): the
# biggest stadium a club can build, record 8 of table 0.7, holds 100,000 at
# each of its three levels instead of 110,000 (Nexxus's choice). The
# match's stadium ids for it (STADIUM_DATA 96-101, initteam.StadiumData)
# change with it, in patch_disc.py.
SPECIAL_STADIUM = ((0, 7), 8, 110000, 100000)


def special_stadium(data):
    """PLRESOURCECOMMON.PAC with the Special stadium at 100,000; None when
    it already is. Raises ValueError for a pack that is neither."""
    _, entries = load_bytes(data)
    tables = [bytearray(t) for t in entries[0]]
    key, record, retail, new = SPECIAL_STADIUM
    names = ["capacity%d" % n for n in range(STADIUM_LEVELS)]
    held = [get_field(tables, key, record, name) for name in names]
    if held == [new] * len(names):
        return None
    if held != [retail] * len(names):
        raise ValueError("%s: the Special stadium holds %s, expected %d; not the retail pack?"
                         % (FILE, held, retail))
    for name in names:
        set_field(tables, key, record, name, new)
    return encode(data, tables)


def parse_edit(text):
    """(key, record, field, value) from "<table>:<record>:<field>=<value>"."""
    target, sep, value = text.partition("=")
    parts = target.split(":")
    if not sep or len(parts) != 3 or not parts[1].isdigit():
        raise ValueError("expected <table>:<record>:<field>=<value>, got %r" % text)
    try:
        value = int(value)
    except ValueError:
        raise ValueError("%r: the value must be a whole number" % text)
    key = facility_key(parts[0])
    field(key, parts[2])
    return key, int(parts[1]), parts[2], value


def cmd_set(src, dst, edits):
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(src, "rb") as f:
        data = f.read()
    _, entries = load(src)
    tables = [bytearray(t) for t in entries[0]]
    for text in edits:
        try:
            key, record, name, value = parse_edit(text)
            old = set_field(tables, key, record, name, value)
        except ValueError as e:
            raise SystemExit(str(e))
        print("%d.%d %s %d %s: %d -> %d" % (key + (FACILITY[key][0], record, name, old, value)))
    out = encode(data, tables)
    if len(out) != len(data):
        raise SystemExit("rebuilt pack is %d bytes, not %d" % (len(out), len(data)))
    with open(dst, "wb") as f:
        f.write(out)
    print("wrote %s" % dst)


def cmd_roundtrip(path):
    """Rebuild the pack unchanged, then change every editable field of every
    record on its own and check that the rebuilt pack differs in that field's
    word only and reads back the new value."""
    try:
        path, entries = load(path)
        with open(path, "rb") as f:
            data = f.read()
        out = encode(data, entries[0])
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    print("%s: %s" % (path, "rebuilt pack identical" if out == data else "!! rebuilt pack differs"))
    base = pac.binpac_blobs(data)[1][0]
    start = data.index(base)
    for key in sorted(FACILITY):
        name, _, size, _, fields = FACILITY[key]
        count, probs = len(entries[0][key[1]]) // size, []
        table_at = start + tbb.parse(base)[1][key[1]].offset + tbb.HEADER_SIZE
        for record in range(count):
            for off, (fname, kind) in sorted(fields.items()):
                tables = [bytearray(t) for t in entries[0]]
                lo = RANGES[kind][0]
                new = lo if get_field(tables, key, record, fname) != lo else lo + 1
                set_field(tables, key, record, fname, new)
                out = encode(data, tables)
                at = table_at + record * size + off
                back = struct.unpack_from("<i", out, at)[0]
                if len(out) != len(data) or out[:at] != data[:at] or out[at + 4:] != data[at + 4:]:
                    probs.append("%d %s: other bytes changed" % (record, fname))
                elif back != new:
                    probs.append("%d %s: reads back %d, not %d" % (record, fname, back, new))
        line = "%d.%d %-26s %3d records x %d fields" % (key + (name, count, len(fields)))
        print("  %s  %s" % (line, "!! " + "; ".join(probs[:5]) if probs else "each edit changes its own word only"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    elif cmd == "set" and len(args) >= 3:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "show" and len(args) == 2:
        try:
            entry, table = (int(x) for x in args[1].split("."))
        except ValueError:
            print(__doc__)
            return 1
        if (entry, table) not in FACILITY and (entry, table) not in BYTES:
            print("no table %s" % args[1])
            return 1
        cmd_show(args[0], entry, table)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
