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
  4  competitions  7 x 22 bytes (plCombi_GetCombinationGrow), 96 x 8 bytes
                   (plCompeData_getCupUID_FromNation)

Usage:
    python plrcommon.py info <PLRESOURCECOMMON.PAC | DAT/PARAM>
    python plrcommon.py show <PLRESOURCECOMMON.PAC | DAT/PARAM> <entry>.<table>

`show` prints one table: records with their named fields for entry 0, nation
names (from PBDATA_EU.PAC and DAT/MESSAGE/MES.PAC) for entry 3, and the raw
rows otherwise.
"""
import os
import struct
import sys

import pac
import tbb

FILE = "PLRESOURCECOMMON.PAC"
NATIONS, NATIONAL_TEAMS, REGIONS, CLUBS = 146, 83, 13, 460

# (entry, table): (name, reader, record size, documented size, {offset: field})
# Record sizes are the getters' index scaling; fields marked "?" are inferred
# from the data (see the doc), the rest are read by the code named there.
FACILITY = {
    (0, 0): ("sites", "plTeam_GetSiteDb", 0x1c, 84,
             {0x8: "cost?", 0xc: "build time"}),
    (0, 1): ("training-ground equipment", "plTeam_GetGrEquipsDb", 0x34, 520,
             {0xc: "cost?", 0x10: "build time"}),
    (0, 2): ("stadium equipment", "plTeam_GetStEquipsDb", 0x20, 512,
             {0xc: "cost?", 0x10: "build time", 0x14: "upkeep"}),
    (0, 3): ("club houses", "plTeam_GetChouseDb", 0x28, 120,
             {0xc: "cost?", 0x10: "build time", 0x14: "upkeep"}),
    (0, 4): ("club-house equipment", "plTeam_GetDChEquipsDb", 0x20, 1152,
             {0xc: "cost?", 0x10: "build time", 0x14: "upkeep"}),
    (0, 5): ("youth-house equipment", "plTeam_GetDAcEquipsDb", 0x20, 576,
             {0xc: "cost?", 0x10: "build time", 0x14: "upkeep"}),
    (0, 6): ("office equipment", "plTeam_GetOfEquipsDb", 0x18, 288,
             {0x8: "cost?", 0xc: "build time", 0x10: "upkeep"}),
    (0, 7): ("stadiums", "plTeam_GetStadiumDb", 0x80, 1152,
             {0x30: "level 0 build time", 0x38: "level 0 capacity",
              0x40: "level 1 build time", 0x48: "level 1 capacity",
              0x50: "level 2 build time", 0x58: "level 2 capacity"}),
    (0, 8): ("stadium adverts", "plTeam_GetStAdvertiseDb", 0x14, 120,
             {0x8: "cost?", 0xc: "build time", 0x10: "upkeep"}),
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
    (4, 0): ("combination growth, 7 x 22", "plCombi_GetCombinationGrow", 154),
    (4, 1): ("cup UIDs by nation, 96 x 8", "plCompeData_getCupUID_FromNation", 768),
}
TABLE_COUNTS = (9, 7, 1, 6, 2)
NATIONAL_TEAM_FIRST = 0x1cc        # team id of the first national team (table 3.2)


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        data = f.read()
    _, blobs = pac.binpac_blobs(data)
    if len(blobs) != len(TABLE_COUNTS):
        raise ValueError("%d entries, expected %d" % (len(blobs), len(TABLE_COUNTS)))
    return path, [[t.data for t in tbb.parse(b)[1]] for b in blobs]


def records(data, size):
    return [data[i:i + size] for i in range(0, len(data), size)]


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
            named = ", ".join("%s %d" % (fields[o], words[o // 4]) for o in sorted(fields))
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


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
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
