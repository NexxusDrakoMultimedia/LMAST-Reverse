# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Starting leagues and computer-team squads for Let's Make a Soccer Team! (PS2).

Two TBB1 files in DAT/PARAM set up the clubs at the start of a career
(see DOC/INITTEAM_FORMAT.md):

  PLRRSRC_INITTEAMDATA.TBB  table 0: 6 leagues x 2 divisions, each a list
                            of up to 26 u32 PlTeam ids ending at the first 0.
                            table 1: 56 x 32 u32 PlTeam ids, last season's
                            order per competition (PLSCHE_COMPE); the first
                            49 are read. table 2: 56 s16, the first 49 read.
  OTEAMMEMBER.TBB           teams 3-441, 25 squad slots each, 16-byte
                            records {u16 player, age, shirt, contract years}
                            with each field padded to a u32 (teams 3-459
                            once --mod third-tier adds 18 squads).
  PLRESOURCESIM.PAC #3      457 x 24-byte club records (plOteam_GetDb):
                            rank, world club rank, manager, stadium,
                            transfer policy, money factor, city, state.
  INITNATIDATA.TBB          145 nations x 6 bytes: UEFA rank and points
                            (nations 1-52), world rating.
  STADIUM_DATA.TBB          119 stadiums x 3 bytes: roof, level, capacity.
  MAPTEAM_LIST.TBB          242 x {u16 team, u16 flag}; flag 1 marks the
                            real 2005/06 top divisions (reader not found).

Confirmed from SLES_541.51: the PlRrsrc_InitTeamData callback (0x253338)
and its table readers (0x253228, 0x2531b0, 0x2532c8), plLg_EntryTeamSetToDiv
(0x2e94c8), pwkRec_SetPastRecordLastTeam (0x253650), pwkOteam_Init
(0x24a6a0), UpdateConyear (0x221480) and pwkTeam_SetUnumberOpinfo
(0x2734c8). Team names are message category 3, id 2000 + team
(Msg::GetString 0x200ea8, category table 0x51ab38, base at 0x52f7b0).

Usage:
    python initteam.py info    <DAT/PARAM>                    # check both files
    python initteam.py leagues <DAT/PARAM> [--mes MES.PAC] [--lang N]
    python initteam.py past    <DAT/PARAM> [--mes MES.PAC] [--lang N]
    python initteam.py squads  <DAT/PARAM> [team ...] [--mes MES.PAC] [--lang N]
    python initteam.py set     <OTEAMMEMBER.TBB> <out.TBB> <team>:<slot> <field>=<value> ...
    python initteam.py teams   <DAT/PARAM> [team ...]         # club records
    python initteam.py nations <DAT/PARAM>
    python initteam.py stadiums <DAT/PARAM>
    python initteam.py setteam <PLRESOURCESIM.PAC> <out.PAC> <team> <field>=<value> ... [<team> ...]
    python initteam.py setnation <INITNATIDATA.TBB> <out.TBB> <nation> <field>=<value> ... [<nation> ...]
    python initteam.py setstadium <STADIUM_DATA.TBB> <out.TBB> <stadium> <field>=<value> ... [<stadium> ...]
    python initteam.py swap    <PLRRSRC_INITTEAMDATA.TBB> <out.TBB> <team>:<team> ...
    python initteam.py roundtrip <DAT/PARAM>                 # re-encode all three, !! if not identical

`set` edits squad slots (fields player, age, shirt, contract) and writes a
new OTEAMMEMBER.TBB of the same size, ready for patch_disc.py. A computer
team's players take their age from here, not from the player database; a
new game shows it one year older (Terry's 25 shows as 26). `swap`
exchanges two league clubs everywhere in PLRRSRC_INITTEAMDATA.TBB: their
places in the starting divisions (table 0) and in last season's results
(table 1), which the first season's divisions, after promotion and
relegation, and its cup places are built from. Every division keeps its
size, which the schedules fix (SCHEDULE_FORMAT.md). Both clubs must be in
the starting divisions. `setnation` sets a nation's uefa_rank,
uefa_points (both read for nations 1-52 only) or world rating;
`setstadium` a stadium's roof (0/1), level (0-4) or capacity (thousands).
`set`, `setteam`, `setnation`, `setstadium` and `swap` write through the
same encoders that `roundtrip` checks: the five files re-encode byte for
byte.

Names are read from <DAT/PARAM>/../MESSAGE/MES.PAC unless --mes is given,
in language slot 1 (English) unless --lang is given. Without MES.PAC the
commands print team ids only. `squads` also names each player from
<DAT/PARAM>/PBDATA_EU.PAC (pbdata.py) when it is there.
"""
import os
import struct
import sys

import tbb

INIT_TBB = "PLRRSRC_INITTEAMDATA.TBB"
OTEAM_TBB = "OTEAMMEMBER.TBB"
PBDATA = "PBDATA_EU.PAC"

# PLRRSRC_INITTEAMDATA table 0 (reader 0x253228): league i's two divisions
# are 0x68-byte blocks at i * 0xd0 and i * 0xd0 + 0x68.
LEAGUES = 6
DIVISIONS = 2
DIV_BLOCK = 0x68
DIV_MAX = 26                # plLg_EntryTeamSetToDiv stops at 0x1a teams or a 0 id
# Table 1 (reader 0x2531b0) and table 2 (0x2532c8).
PAST_ROW = 0x80
PAST_SLOTS = 0x20           # pwkRec_SetPastRecordLastTeamOne: slot < 0x20
PAST_READ = 0x31            # the readers loop PLSCHE_COMPE 0-48
INIT_SIZES = (LEAGUES * DIVISIONS * DIV_BLOCK, 56 * PAST_ROW, 56 * 2)

# OTEAMMEMBER (pwkOteam_Init 0x24a6a0): teams 3 to 0x1b9, 25 slots each.
OTEAM_FIRST = 3
OTEAM_END = 0x1ba
# The third tier's clubs (LMASTER, patch_disc.py --mod third-tier): the
# tutorial's opponents, given squads of their own after the others. Their
# 25 players each are the database's block from 0x63f7 (the non-resident
# set-up at SLES 0x24d6b0 takes the same ids).
TIER_FIRST, TIER_END, TIER_PLAYERS = 0x1ba, 0x1cc, 0x63f7
SQUAD = 25                  # also pwkTeam_SetUnumberOpinfo's slot count
OTEAM_ROW = 0x10
# Record offsets and the PlOpinfo byte each is copied to.
OTEAM_FIELDS = (("player", 0x0, "<H"), ("age", 0x4, "B"),
                ("shirt", 0x8, "B"), ("contract", 0xC, "B"))

TEAM_NAME_CATEGORY = 3      # global message slot 2 -> category 3 (0x51ab38)
TEAM_NAME_BASE = 2000       # u16 at 0x52f7b0, added to the team id


class Division:
    def __init__(self, league, div, raw):
        self.league, self.div = league, div
        self.ids = list(struct.unpack("<%dI" % DIV_MAX, raw))

    @property
    def teams(self):
        """The clubs the game reads: up to the first 0."""
        n = self.ids.index(0) if 0 in self.ids else DIV_MAX
        return self.ids[:n]

    @property
    def ignored(self):
        """Ids after the first 0, which the game never reads."""
        return [t for t in self.ids[len(self.teams):] if t]


class InitTeamData:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.buf = f.read()
        self.end, tables = tbb.parse(self.buf)
        self.tables = tables
        if len(tables) != 3:
            raise ValueError("%d tables, expected 3" % len(tables))
        for t, size in zip(tables, INIT_SIZES):
            if t.size != size:
                raise ValueError("table %d is %d bytes, expected %d" % (t.index, t.size, size))
        d = tables[0].data
        self.divisions = [Division(lg, dv, d[(lg * DIVISIONS + dv) * DIV_BLOCK:][:DIV_BLOCK])
                          for lg in range(LEAGUES) for dv in range(DIVISIONS)]
        p = tables[1].data
        self.past = [list(struct.unpack_from("<%dI" % PAST_SLOTS, p, i * PAST_ROW))
                     for i in range(len(p) // PAST_ROW)]
        self.years = list(struct.unpack("<%dh" % (tables[2].size // 2), tables[2].data))

    def encode(self):
        """The whole file rebuilt from the divisions, past records and
        years with tbb.build."""
        trailer = tbb.trailer(self.buf, self.tables)
        self.tables[0].data = b"".join(struct.pack("<%dI" % DIV_MAX, *d.ids)
                                       for d in self.divisions)
        self.tables[1].data = b"".join(struct.pack("<%dI" % PAST_SLOTS, *r) for r in self.past)
        self.tables[2].data = struct.pack("<%dh" % len(self.years), *self.years)
        return tbb.build(self.tables, self.end, trailer)

    def past_record(self, division):
        """The past record (table 1) holding exactly this division's clubs,
        in last season's finishing order, or None. Empirical: each of the
        12 divisions matches one read record (0, 1, 6, 7, 11, 12, 16, 17,
        22, 23, 27, 28; the English second division also 3), and a swap
        keeps it so."""
        teams = set(division.teams)
        return next((i for i, r in enumerate(self.past[:PAST_READ])
                     if set(t for t in r if t) == teams), None)

    def league_clubs(self):
        """{team: (league, division)} for every club in the starting divisions."""
        return {t: (d.league, d.div) for d in self.divisions for t in d.teams}

    def swap(self, a, b):
        """Exchange clubs a and b in the starting divisions (table 0) and in
        every past record (table 1), so each takes the other's place:
        its division and slot, and its results last season, which decide
        the first season's divisions after promotion and relegation (the
        schedules' LAST_RANK slots) and its cup places. Division sizes, which
        the schedules fix, don't change. Both must be league clubs.
        Returns the number of ids changed."""
        clubs = self.league_clubs()
        for t in (a, b):
            if t not in clubs:
                raise ValueError("team %d isn't in the starting divisions (league clubs are "
                                 "%d-%d)" % (t, min(clubs), max(clubs)))
        if a == b:
            raise ValueError("team %d swapped with itself" % a)
        n = 0
        for lists in ([d.ids for d in self.divisions], self.past):
            for ids in lists:
                for k, t in enumerate(ids):
                    if t in (a, b):
                        ids[k] = b if t == a else a
                        n += 1
        return n


class Member:
    def __init__(self, raw):
        self.raw = bytes(raw)
        for name, off, fmt in OTEAM_FIELDS:
            setattr(self, name, struct.unpack_from(fmt, raw, off)[0])
        # The exporter wrote each field as a u32; the upper bytes should be 0.
        used = {off + i for _, off, fmt in OTEAM_FIELDS for i in range(struct.calcsize(fmt))}
        self.padding_ok = not any(raw[i] for i in range(OTEAM_ROW) if i not in used)

    def encode(self):
        """The 16-byte record: the fields over the original bytes, so the
        padding is kept as it was."""
        out = bytearray(self.raw)
        for name, off, fmt in OTEAM_FIELDS:
            struct.pack_into(fmt, out, off, getattr(self, name))
        return bytes(out)


class OteamMembers:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.buf = f.read()
        self.end, self.tables = tbb.parse(self.buf)
        if len(self.tables) != 1:
            raise ValueError("%d tables, expected 1" % len(self.tables))
        d = self.tables[0].data
        sizes = {(end - OTEAM_FIRST) * SQUAD * OTEAM_ROW: end for end in (OTEAM_END, TIER_END)}
        if len(d) not in sizes:
            raise ValueError("table is %d bytes, expected %s" % (
                len(d), " or ".join(str(n) for n in sorted(sizes))))
        self.end_team = sizes[len(d)]
        self.squads = {}
        for i, team in enumerate(range(OTEAM_FIRST, self.end_team)):
            base = i * SQUAD * OTEAM_ROW
            self.squads[team] = [Member(d[base + k * OTEAM_ROW:][:OTEAM_ROW])
                                 for k in range(SQUAD)]

    def encode(self):
        """The whole file, rebuilt from the squads with tbb.build."""
        data = b"".join(m.encode() for team in sorted(self.squads)
                        for m in self.squads[team])
        trailer = tbb.trailer(self.buf, self.tables)
        self.tables[0].data = data
        return tbb.build(self.tables, self.end, trailer)


def add_tier_squads(ot, db):
    """Give OteamMembers `ot` squads for the third tier's clubs 442-459,
    from their database players (pbdata.PbData `db`): age and shirt as the
    database has them, contracts of 2 years. Returns the bytes of the
    whole file."""
    if ot.end_team != OTEAM_END:
        raise ValueError("the table already has squads past club %d" % (OTEAM_END - 1))
    for team in range(TIER_FIRST, TIER_END):
        squad = []
        for k in range(SQUAD):
            pid = TIER_PLAYERS + SQUAD * (team - TIER_FIRST) + k
            r = db.record("players", pid)
            m = Member(bytes(OTEAM_ROW))
            m.player, m.age, m.shirt, m.contract = pid, r.fields["age"], r.fields["shirt"], 2
            squad.append(m)
        ot.squads[team] = squad
    ot.end_team = TIER_END
    return ot.encode()


# Limits for `set`: the fields are copied into PlOpinfo bytes, and
# pwkTeam_SetUnumberOpinfo only keeps shirt numbers 1-99.
SET_LIMITS = {"player": (0, 0xffff), "age": (0, 0xff), "shirt": (1, 99), "contract": (0, 0xff)}


# What an editor (SRC/editor.py) offers for a squad slot: the documented
# values, narrower than SET_LIMITS. Ages: 16-40 on the disc, and 15 is
# tested in PCSX2 (Terry shows 16 in a new game). Contracts: 2-6 on the
# disc. Widen these when a value outside them is tested in game.
SQUAD_EDIT_RANGES = {"age": (15, 40), "shirt": (1, 99), "contract": (2, 6)}


def set_member(m, name, value):
    """Set one squad-slot field (player, age, shirt, contract) within
    SET_LIMITS. Returns the old value."""
    if name not in SET_LIMITS:
        raise ValueError("fields are %s" % ", ".join(SET_LIMITS))
    lo, hi = SET_LIMITS[name]
    if not lo <= value <= hi:
        raise ValueError("%s must be %d-%d" % (name, lo, hi))
    old = getattr(m, name)
    setattr(m, name, value)
    return old


# --- club records, nations, stadiums -------------------------------------------

SIM_PAC = "PLRESOURCESIM.PAC"
NATION_TBB = "INITNATIDATA.TBB"
STADIUM_TBB = "STADIUM_DATA.TBB"
MAPTEAM_TBB = "MAPTEAM_LIST.TBB"

# plOteam_GetDb (0x2165d8): PLRESOURCESIM.PAC entry 3, table 0, 24 bytes per
# PlTeam - 3 (ids past 0x1cb read record 0; team 2 uses the rival's).
TEAM_FIRST = 3
TEAM_ROW = 0x18
# (name, offset, struct format, reader). Offsets without a reader in
# SLES_541.51 or the overlays keep their offset as a name.
TEAM_FIELDS = (
    ("rank", 0x00, "<h", "plOteam_GetManagerClubRank, pwkOteam_GetRank"),
    ("world_rank", 0x02, "<H", "pwkOteam_Init2 -> pwkOteam_GetWorldClubRank"),
    ("manager", 0x04, "<h", "plOteam_GetManagerNoOffset (+0x6d2e = database id)"),
    ("stadium", 0x06, "<h", "PlGiTask::InitStadium, plTeam_GetStadiumNoFromNation"),
    ("foreign", 0x08, "B", "GetCanBelongForeignPlayerNum, GetSearchNation"),
    ("newface", 0x09, "B", "CAcquirePlayer::IsAcquireNewfacePlayer"),
    ("search_region", 0x0a, "B", "CAcquirePlayer::GetSearchNation"),
    ("f_0b", 0x0b, "B", None),
    ("f_0c", 0x0c, "B", None),
    ("f_0d", 0x0d, "B", None),
    ("money", 0x0e, "B", "plTeam_IsAgreeTransferChangeMoney, 0x248140"),
    ("f_0f", 0x0f, "B", None),
    ("city", 0x10, "<H", "plTeam_GetCity"),
    ("list_state", 0x12, "<H", "plState_GetEmblemDisplayTeamList"),
    ("list_city", 0x14, "<I", "plCity_GetEmblemDisplayTeamList"),
)
CITY_CATEGORY, STATE_CATEGORY = 961, 960    # empirical: London 604, Greater London 17


def read_pac_entry(path, index):
    import pac
    h = pac.load_header(path)
    with open(pac.data_path(path, h), "rb") as f:
        buf = f.read()
    off, size, _, _ = h.entries[index]
    return buf, off, size


class TeamDb:
    def __init__(self, path=None, data=None):
        """The club records of PLRESOURCESIM.PAC at `path`, or in its bytes
        `data`."""
        if data is None:
            buf, off, size = read_pac_entry(path, 3)
        else:
            import pac
            h = pac.BinPac(data[:struct.unpack_from("<I", data)[0]])
            buf, (off, size, _, _) = data, h.entries[3]
        self.buf = buf
        _, tables = tbb.parse(buf[off:off + size])
        t = tables[0]
        if t.size % TEAM_ROW:
            raise ValueError("club table is %d bytes, not a multiple of 0x18" % t.size)
        self.data = t.data
        # Where the table's data sits in the pack file, for setteam.
        self.file_offset = off + t.offset + t.data_offset
        self.records = {}
        for i in range(t.size // TEAM_ROW):
            raw = t.data[i * TEAM_ROW:(i + 1) * TEAM_ROW]
            self.records[TEAM_FIRST + i] = {
                name: struct.unpack_from(fmt, raw, o)[0] for name, o, fmt, _ in TEAM_FIELDS}

    def encode(self):
        """The whole pack with every club record written back in place;
        nothing else in the file changes."""
        out = bytearray(self.buf)
        for team, r in self.records.items():
            base = self.file_offset + (team - TEAM_FIRST) * TEAM_ROW
            for name, o, fmt, _ in TEAM_FIELDS:
                struct.pack_into(fmt, out, base + o, r[name])
        return bytes(out)


def set_team_field(record, name, value):
    """Set one club-record field; the value must fit its type. Returns the
    old value."""
    fmt = next((fmt for n, _, fmt, _ in TEAM_FIELDS if n == name), None)
    if fmt is None:
        raise ValueError("fields are %s" % ", ".join(n for n, _, _, _ in TEAM_FIELDS))
    try:
        struct.pack(fmt, value)
    except struct.error:
        raise ValueError("%s=%d does not fit (%s)" % (name, value, fmt))
    old = record[name]
    record[name] = value
    return old


# What an editor (SRC/editor.py) may offer for each club-record field: the
# documented range where there is one
# (DOC/INITTEAM_FORMAT.md#club-records-plresourcesimpac-entry-3), else the
# type's. Fields with no reader (f_0b ...) are read-only.
TEAM_EDIT_RANGES = {
    "rank": (0, 31),
    "manager": (0, 2999),           # the 3,000 manager records of PBDATA
    "stadium": (0, 118),            # STADIUM_DATA's 119 rows (StadiumData.COUNT)
    "foreign": (0, 7),              # rows of PLRESOURCESIM entry 6, table 1
    "newface": (0, 3),              # the % table at 0x533ff8
    "search_region": (0, 31),       # rows of entry 6, table 4
}


# Club-record fields whose values are named by a message category. The
# manager is a PBDATA manager index (pbdata.py) and the stadium a
# STADIUM_DATA row (StadiumData).
TEAM_NAME_CATEGORIES = {"city": CITY_CATEGORY, "list_city": CITY_CATEGORY,
                        "list_state": STATE_CATEGORY}


def team_edit_range(name):
    """(low, high) an editor may set a club-record field to, or None for a
    field with no name yet."""
    if name.startswith("f_"):
        return None
    if name in TEAM_EDIT_RANGES:
        return TEAM_EDIT_RANGES[name]
    fmt = next(fmt for n, _, fmt, _ in TEAM_FIELDS if n == name)
    bits = struct.calcsize(fmt) * 8
    return (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if fmt[-1].islower() else (0, (1 << bits) - 1)


class NationData:
    """INITNATIDATA: the pwkRec_RequestInit callback (0x253418) copies +4
    for nations 1-145 (pwkRec_GetWorldNation) and +0/+2 for nations 1-52
    (pwkRec_GetUefaNation)."""
    ROW, COUNT, UEFA = 6, 145, 52

    FIELDS = ("uefa_rank", "uefa_points", "world")
    RANGES = {"uefa_rank": (0, 0xff), "uefa_points": (0, 0xffff), "world": (0, 0xff)}

    def __init__(self, path):
        with open(path, "rb") as f:
            self.buf = f.read()
        self.end, self.tables = tbb.parse(self.buf)
        d = self.tables[0].data
        if len(d) != self.ROW * self.COUNT:
            raise ValueError("table is %d bytes, expected %d" % (len(d), self.ROW * self.COUNT))
        self.rows = {n + 1: struct.unpack_from("<BxHBx", d, n * self.ROW) for n in range(self.COUNT)}

    def set(self, nation, name, value):
        """Set one field of a nation's row; returns the old value. The
        UEFA fields are read for nations 1-52 only, so other nations
        refuse them."""
        if nation not in self.rows:
            raise ValueError("nation %d: nations are 1-%d" % (nation, self.COUNT))
        if name not in self.FIELDS:
            raise ValueError("field %r: the fields are %s" % (name, ", ".join(self.FIELDS)))
        if name != "world" and nation > self.UEFA:
            raise ValueError("nation %d: %s is read for nations 1-%d only" % (nation, name, self.UEFA))
        lo, hi = self.RANGES[name]
        if not lo <= value <= hi:
            raise ValueError("%s=%d: allowed %d-%d" % (name, value, lo, hi))
        row = list(self.rows[nation])
        i = self.FIELDS.index(name)
        old, row[i] = row[i], value
        self.rows[nation] = tuple(row)
        return old

    def encode(self):
        """The whole file, rebuilt from the rows with tbb.build; the pad
        bytes +1 and +5 are kept."""
        d = bytearray(self.tables[0].data)
        for n, row in self.rows.items():
            off = (n - 1) * self.ROW
            struct.pack_into("<BxHBx", d, off, *row)
            d[off + 1], d[off + 5] = self.tables[0].data[off + 1], self.tables[0].data[off + 5]
        trailer = tbb.trailer(self.buf, self.tables)
        self.tables[0].data = bytes(d)
        return tbb.build(self.tables, self.end, trailer)


class StadiumData:
    """plTeam_IsRoofFromID / GetStadiumLvFromID / GetCapacityFromID
    (0x22ae18, 0x22adc8, 0x22ae68): {roof, level, capacity in thousands}."""
    ROW, COUNT = 3, 0x77
    BONUS = {0x67: 500, 0x69: 500, 0x6b: 500}   # GetCapacityFromID adds 500 seats

    FIELDS = ("roof", "level", "capacity")
    # Level 0-4 is the range on the disc (DOC/INITTEAM_FORMAT.md); the
    # capacity is in thousands.
    RANGES = {"roof": (0, 1), "level": (0, 4), "capacity": (0, 0xff)}

    def __init__(self, path=None, data=None):
        """STADIUM_DATA.TBB at `path`, or its bytes `data`."""
        if data is None:
            with open(path, "rb") as f:
                data = f.read()
        self.buf = data
        self.end, self.tables = tbb.parse(self.buf)
        d = self.tables[0].data
        if len(d) != self.ROW * self.COUNT:
            raise ValueError("table is %d bytes, expected %d" % (len(d), self.ROW * self.COUNT))
        self.rows = [tuple(d[i * 3:i * 3 + 3]) for i in range(self.COUNT)]

    def set(self, stadium, name, value):
        """Set one field of a stadium's row; returns the old value."""
        if not 0 <= stadium < self.COUNT:
            raise ValueError("stadium %d: stadiums are 0-%d" % (stadium, self.COUNT - 1))
        if name not in self.FIELDS:
            raise ValueError("field %r: the fields are %s" % (name, ", ".join(self.FIELDS)))
        lo, hi = self.RANGES[name]
        if not lo <= value <= hi:
            raise ValueError("%s=%d: allowed %d-%d" % (name, value, lo, hi))
        row = list(self.rows[stadium])
        i = self.FIELDS.index(name)
        old, row[i] = row[i], value
        self.rows[stadium] = tuple(row)
        return old

    def encode(self):
        """The whole file, rebuilt from the rows with tbb.build."""
        trailer = tbb.trailer(self.buf, self.tables)
        self.tables[0].data = b"".join(bytes(r) for r in self.rows)
        return tbb.build(self.tables, self.end, trailer)

    def capacity(self, i):
        return self.rows[i][2] * 1000 + self.BONUS.get(i, 0)


# The LMASTER Mod's real grounds (DOC/LMASTER_MOD.md#stadiums): each club
# plays at a ground of its real 2005-06 capacity (the game's season),
# rounded to 5,000 (the user's choice), and clubs of one size are spread
# over the stadium ids of that size, so they look different. grounds.csv,
# next to this script, holds {team, ground, capacity in thousands}; clubs
# naming the same ground share an id.
#
# Stadium ids 0-101 are the ones a club's own ground reaches as it is built
# (CONV_INFO_BUILD), and InitStadium fills the stands by their capacity, so
# they keep it: 8, 15-25, 30-40 and 50-60 thousand, and 100 for 96-101 with
# special-stadium. A ground's look follows its size, closer than the
# ladder's models allow at the top (user reports, 2026-10-30: the big clubs
# looked too small, but only the biggest deserve the 110,000 bowl):
#   8-35 thousand   the ladder's own ids and models
#   40-60           ho03a: 40 and 45 on the ids below, 50-60 the ladder's
#   65-75           the aw04b bowl, 80 and over the ho04a bowl
# Ids 102-118 are the computer clubs' own: each takes the look of a ground
# (its BUILD_STADIUM row, stadium.copy_rows, and its roof) and a band of its
# own: {id: (capacity in thousands, level, the ground it looks like)}.
# GetCapacityFromID adds 500 seats to 103, 105 and 107. A look is copied
# only from a row the switch leaves as it is (116-118 keep their own), so
# the copy is the same however often it is made.
GROUNDS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "grounds.csv")
GROUND_IDS = {
    102: (40, 3, 69), 103: (40, 3, 79), 104: (40, 3, 89),     # ho03a, roof
    105: (45, 3, 75), 106: (45, 3, 85), 107: (45, 3, 95),     # ho03a, roof and lights
    108: (65, 4, 116), 109: (65, 4, 118),                     # aw04b
    110: (70, 4, 116), 111: (70, 4, 118),
    116: (75, 4, 116), 118: (75, 4, 118),                     # aw04b, their own
    112: (80, 4, 97), 113: (80, 4, 117),                      # ho04a
    115: (85, 4, 99), 117: (85, 4, 117),                      # 117 its own
}
# Stadium 114 is the rival's ground in every league (TEAM_INIT_DATA table
# 7, DOC/TEAMINIT_FORMAT.md): it keeps its look, boards and size, and no
# other club is put on it (the user's request).
RIVAL_STADIUM = 114
GROUND_RETAIL = {102: 8, 103: 18, 104: 15, 105: 18, 106: 20, 107: 18, 108: 40, 109: 35,
                 110: 35, 111: 40, 112: 42, 113: 42, 114: 42, 115: 42, 116: 70, 117: 110,
                 118: 70}
LADDER_SKIPPED = {40}           # the ladder's 40,000 grounds are ho02a; 40 uses the ids above
SPECIAL_GROUND = (range(96, 102), 100)              # with special-stadium
SMALLEST_BAND = 12.5                                # below it, the 8,000 ground
# The ladder's ids by level: 0-5 hold 8; then 30 ids a level, 6 leagues x
# 5 variants (no stand, 1 or 2 stands, roof, lights), the variants holding
# the type's three stand capacities and then the third again.
LADDER = ((range(0, 6), (8,)), (range(6, 36), (15, 20, 25, 25, 25)),
          (range(36, 66), (30, 35, 40, 40, 40)), (range(66, 96), (50, 55, 60, 60, 60)))


def load_grounds(path=GROUNDS_FILE):
    """[(team, ground, capacity in thousands)]."""
    import csv
    with open(path, encoding="utf-8-sig", newline="") as f:
        return [(int(r["team"]), r["ground"], float(r["capacity"])) for r in csv.DictReader(f)]


GROUND_SLACK = 3.0              # thousands a club may be put from its real size
SMALL_FORTY = 40.0              # the ladder's 40,000 grounds (ho02a) only below this


def ground_bands():
    """{band in thousands: [stadium ids]}: the ladder's ids (its 40,000
    ones under the key "small 40"), the ids above, and 96-101 at the
    Special stadium's."""
    bands = {}
    for ids, sizes in LADDER:
        for i in ids:
            size = sizes[(i - ids[0]) % len(sizes)]
            bands.setdefault("small 40" if size in LADDER_SKIPPED else size, []).append(i)
    for i, (size, _, _) in sorted(GROUND_IDS.items()):
        bands.setdefault(size, []).append(i)
    bands[SPECIAL_GROUND[1]] = list(SPECIAL_GROUND[0])
    return bands


def ground_band(capacity, bands):
    """The band a capacity goes to: the nearest 5,000 the ids offer, the
    bigger one on a tie; under 12,500 the smallest ground."""
    bands = [b for b in bands if not isinstance(b, str)]
    if capacity < SMALLEST_BAND:
        return min(bands)
    target = 5 * round(capacity / 5)
    return min(bands, key=lambda b: (abs(b - target), -b))


def ground_choices(capacity, bands):
    """[(band, id)] a club of `capacity` may get: every band within
    GROUND_SLACK of it, or its nearest band if none is; the ladder's
    40,000 grounds too when it is under SMALL_FORTY."""
    sizes = [b for b in bands if not isinstance(b, str)]
    near = ground_band(capacity, sizes)
    if capacity < SMALLEST_BAND:
        ok = [near]
    else:
        ok = [b for b in sizes if abs(b - capacity) <= GROUND_SLACK] or [near]
    out = [(b, i) for b in sorted(ok) for i in bands[b]]
    if 40 in ok and capacity < SMALL_FORTY:
        out += [(40, i) for i in bands["small 40"]]
    return out


def ground_ids(grounds=None):
    """{team: stadium id} for every club in grounds.csv, using as many
    grounds as it can: each ground (clubs naming the same one share it)
    takes the least-used of its choices, nearer bands first on a tie; the
    grounds with the fewest choices pick first."""
    bands = ground_bands()
    grounds = sorted(grounds or load_grounds())
    sizes = {}
    for team, ground, capacity in grounds:
        sizes.setdefault(ground, (capacity, team))
    order = sorted(sizes, key=lambda g: (len(ground_choices(sizes[g][0], bands)), sizes[g][1]))
    used, pick = {}, {}
    for ground in order:
        capacity = sizes[ground][0]
        band, i = min(ground_choices(capacity, bands),
                      key=lambda c: (used.get(c[1], 0), abs(c[0] - capacity), c[1]))
        pick[ground] = i
        used[i] = used.get(i, 0) + 1
    return {team: pick[ground] for team, ground, _ in grounds}


def real_grounds_stadiums(data):
    """STADIUM_DATA.TBB bytes with ids 102-118 at their bands, with the
    level of their new model and the roof of the ground they look like;
    None when they already are."""
    table = StadiumData(data=data)
    want = {i: (table.rows[src][0], level, size) for i, (size, level, src) in GROUND_IDS.items()}
    if all(table.rows[i] == r for i, r in want.items()):
        return None
    held = {i: table.rows[i][2] for i in GROUND_IDS}
    if held != {i: GROUND_RETAIL[i] for i in GROUND_IDS}:
        raise ValueError("%s: stadiums 102-118 hold %s thousand; not the retail table?"
                         % (STADIUM_TBB, held))
    for i, (roof, level, size) in want.items():
        table.set(i, "roof", roof)
        table.set(i, "level", level)
        table.set(i, "capacity", size)
    return table.encode()


def real_grounds_build(data):
    """STADIUM/BUILD_STADIUM.TBB bytes with ids 102-118 looking like the
    grounds GROUND_IDS names; None when they already do."""
    import stadium
    return stadium.copy_rows(data, {i: src for i, (_, _, src) in GROUND_IDS.items()})


def real_grounds_clubs(data):
    """PLRESOURCESIM.PAC bytes with each club at its ground's id; None when
    they already are."""
    db = TeamDb(data=data)
    ids = ground_ids()
    if all(db.records[t]["stadium"] == i for t, i in ids.items()):
        return None
    for team, i in ids.items():
        set_team_field(db.records[team], "stadium", i)
    return db.encode()


def category_names(mes_path, category, lang=1):
    if not mes_path or not os.path.exists(mes_path):
        return {}
    import mbb
    for _, m in mbb.iter_files([mes_path]):
        if m.category == category and m.lang == lang:
            return {rid: mbb.decode(s, lang) for rid, s in m.records}
    return {}


# --- names -------------------------------------------------------------------

def team_names(mes_path, lang):
    """{team id: name} from message category 3, or {} without MES.PAC."""
    if not mes_path or not os.path.exists(mes_path):
        return {}
    import mbb
    for _, m in mbb.iter_files([mes_path]):
        if m.category == TEAM_NAME_CATEGORY and m.lang == lang:
            return {rid - TEAM_NAME_BASE: mbb.decode(s, lang) for rid, s in m.records}
    return {}


def label(names, team):
    name = names.get(team)
    return "%3d %s" % (team, name) if name is not None else "%3d" % team


# --- loading -----------------------------------------------------------------

def find(root, name):
    p = os.path.join(root, name)
    if not os.path.exists(p):
        raise SystemExit("%s: not found" % p)
    return p


def default_mes(root):
    return os.path.join(root, os.pardir, "MESSAGE", "MES.PAC")


# --- commands ----------------------------------------------------------------

def cmd_info(root):
    path = find(root, INIT_TBB)
    try:
        init = InitTeamData(path)
    except (ValueError, struct.error) as e:
        print("%s  !! %s" % (path, e))
        init = None
    if init:
        print("%s  %d divisions, %d past records (%d read)" % (
            path, len(init.divisions), len(init.past), PAST_READ))
        seen = {}
        for dv in init.divisions:
            probs = []
            if dv.ignored:
                probs.append("ids after the terminating 0: %s" % dv.ignored)
            for t in dv.teams:
                if t in seen:
                    probs.append("team %d also in league %d division %d" % ((t,) + seen[t]))
                seen[t] = (dv.league, dv.div)
            print("  league %d division %d  %2d teams%s" % (
                dv.league, dv.div, len(dv.teams), "  !! " + "; ".join(probs) if probs else ""))
        ids = sorted(seen)
        print("  %d teams in the leagues, ids %d-%d" % (len(ids), ids[0], ids[-1]) if ids
              else "  no teams in the leagues")
        filled = [i for i, r in enumerate(init.past[:PAST_READ]) if any(r)]
        unread = [i for i, r in enumerate(init.past[PAST_READ:], PAST_READ) if any(r)]
        print("  past records: %d of %d read competitions have teams%s" % (
            len(filled), PAST_READ, "; unread %s not empty" % unread if unread else ""))
        print("  table 2 values (first %d): %s" % (
            PAST_READ, " ".join("%d x%d" % (v, init.years[:PAST_READ].count(v))
                                for v in sorted(set(init.years[:PAST_READ])))))

    path = find(root, OTEAM_TBB)
    try:
        ot = OteamMembers(path)
    except (ValueError, struct.error) as e:
        print("%s  !! %s" % (path, e))
        return
    members = [m for sq in ot.squads.values() for m in sq]
    print("%s  %d teams (%d-%d) x %d slots" % (
        path, len(ot.squads), OTEAM_FIRST, OTEAM_END - 1, SQUAD))
    probs = []
    players = [m.player for m in members]
    if len(set(players)) != len(players):
        probs.append("%d player numbers used more than once" % (len(players) - len(set(players))))
    bad_pad = sum(1 for m in members if not m.padding_ok)
    if bad_pad:
        probs.append("%d records with non-zero padding" % bad_pad)
    for team, sq in ot.squads.items():
        shirts = [m.shirt for m in sq]
        # pwkTeam_SetUnumberOpinfo treats shirts outside 1-99 as unset.
        out = [s for s in shirts if not 1 <= s <= 99]
        if out:
            probs.append("team %d shirt numbers outside 1-99: %s" % (team, out))
        if len(set(shirts)) != len(shirts):
            probs.append("team %d repeats a shirt number" % team)
    for p in probs:
        print("  !! " + p)
    print("  players %d-%d (%d distinct)" % (min(players), max(players), len(set(players))))
    for name in ("age", "shirt", "contract"):
        vals = [getattr(m, name) for m in members]
        print("  %-8s %d-%d" % (name, min(vals), max(vals)))
    check_start_data(root)


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    ot = OteamMembers(path)
    m = None
    for a in args:
        if "=" not in a:
            team, slot = (int(x, 0) for x in a.split(":"))
            if not OTEAM_FIRST <= team < OTEAM_END or not 0 <= slot < SQUAD:
                raise SystemExit("%s: teams are %d-%d and slots 0-%d" % (
                    a, OTEAM_FIRST, OTEAM_END - 1, SQUAD - 1))
            m = ot.squads[team][slot]
            label = a
            continue
        if m is None:
            raise SystemExit("give <team>:<slot> before %r" % a)
        name, value = a.split("=", 1)
        try:
            old = set_member(m, name, int(value, 0))
        except ValueError as e:
            raise SystemExit(str(e))
        print("%s %s: %d -> %d" % (label, name, old, getattr(m, name)))
    with open(out_path, "wb") as f:
        f.write(ot.encode())
    print("wrote %s" % out_path)


def cmd_swap(path, out_path, args):
    """Exchange pairs of league clubs, <a>:<b>, in PLRRSRC_INITTEAMDATA.TBB."""
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    init = InitTeamData(path)
    for a in args:
        try:
            x, y = (int(v, 0) for v in a.split(":"))
            clubs = init.league_clubs()
            n = init.swap(x, y)
        except ValueError as e:
            raise SystemExit("%s: %s" % (a, e))
        print("swapped %d (league %d division %d) and %d (league %d division %d): %d ids" % (
            x, *clubs[x], y, *clubs[y], n))
    with open(out_path, "wb") as f:
        f.write(init.encode())
    print("wrote %s" % out_path)


def cmd_roundtrip(root):
    """Re-encode the starting divisions, every squad slot and club record
    and rebuild the three files; !! where anything differs."""
    path = find(root, INIT_TBB)
    try:
        init = InitTeamData(path)
        same = init.encode() == init.buf
        print("%s  %d divisions, %d past records re-encoded; file %s%s" % (
            path, len(init.divisions), len(init.past), "identical" if same else "differs",
            "" if same else "  !! file differs"))
    except (ValueError, struct.error) as e:
        print("%s  !! %s" % (path, e))
    path = find(root, OTEAM_TBB)
    try:
        ot = OteamMembers(path)
        members = [m for team in sorted(ot.squads) for m in ot.squads[team]]
        bad = sum(1 for m in members if m.encode() != m.raw)
        same = ot.encode() == ot.buf
        probs = (["%d slots differ" % bad] if bad else []) + ([] if same else ["file differs"])
        print("%s  %d squad slots re-encoded, %d differ; file %s%s" % (
            path, len(members), bad, "identical" if same else "differs",
            "  !! " + "; ".join(probs) if probs else ""))
    except (ValueError, struct.error) as e:
        print("%s  !! %s" % (path, e))
    path = find(root, SIM_PAC)
    try:
        db = TeamDb(path)
        same = db.encode() == db.buf
        print("%s #3  %d club records re-encoded; file %s%s" % (
            path, len(db.records), "identical" if same else "differs",
            "" if same else "  !! file differs"))
    except (ValueError, struct.error) as e:
        print("%s  !! %s" % (path, e))
    for name, cls, what in ((NATION_TBB, NationData, "nation rows"),
                            (STADIUM_TBB, StadiumData, "stadium rows")):
        path = find(root, name)
        try:
            table = cls(path)
            same = table.encode() == table.buf
            print("%s  %d %s re-encoded; file %s%s" % (
                path, len(table.rows), what, "identical" if same else "differs",
                "" if same else "  !! file differs"))
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))


def cmd_leagues(root, names):
    init = InitTeamData(find(root, INIT_TBB))
    for dv in init.divisions:
        print("league %d division %d  (%d teams)" % (dv.league, dv.div, len(dv.teams)))
        for t in dv.teams:
            print("  " + label(names, t))


def cmd_past(root, names):
    init = InitTeamData(find(root, INIT_TBB))
    for i, row in enumerate(init.past):
        note = "" if i < PAST_READ else "  (not read)"
        teams = [t for t in row if t]
        print("competition %2d  table 2 = %d  %d teams%s" % (i, init.years[i], len(teams), note))
        for pos, t in enumerate(row):
            if t:
                print("  %2d  %s" % (pos, label(names, t)))


def cmd_squads(root, teams, names):
    ot = OteamMembers(find(root, OTEAM_TBB))
    # The squad's player number is a player-database id (getPlayerName,
    # 0x201f20, looks it up through plBp_GetBpinfo).
    db = None
    if os.path.exists(os.path.join(root, PBDATA)):
        import pbdata
        db = pbdata.PbData(os.path.join(root, PBDATA))
        if not db.data:
            db = None
    for team in teams or sorted(ot.squads):
        if team not in ot.squads:
            raise SystemExit("team %d has no squad (computer teams are %d-%d)" % (
                team, OTEAM_FIRST, OTEAM_END - 1))
        print("team " + label(names, team))
        print("  slot  player  age  shirt  contract%s" % ("  name" if db else ""))
        for k, m in enumerate(ot.squads[team]):
            line = "  %4d  %6d  %3d  %5d  %8d" % (k, m.player, m.age, m.shirt, m.contract)
            if db:
                line += "  " + db.record("players", m.player).name
            print(line)


def check_start_data(root):
    """Layout checks for the club records, nations, stadiums and MAPTEAM_LIST."""
    teams = TeamDb(find(root, SIM_PAC))
    stadiums = StadiumData(find(root, STADIUM_TBB))
    nations = NationData(find(root, NATION_TBB))
    print("%s #3  %d club records (teams %d-%d)" % (
        os.path.join(root, SIM_PAC), len(teams.records), TEAM_FIRST,
        TEAM_FIRST + len(teams.records) - 1))
    probs = []
    managers = [r["manager"] for r in teams.records.values()]
    if len(set(managers)) != len(managers):
        probs.append("a manager is used by more than one club")
    for t, r in teams.records.items():
        if not 0 <= r["stadium"] < StadiumData.COUNT:
            probs.append("team %d stadium %d" % (t, r["stadium"]))
        if not 0 <= r["manager"] < 3000:
            probs.append("team %d manager %d" % (t, r["manager"]))
        if r["foreign"] > 7 or r["newface"] > 3 or r["search_region"] > 31:
            probs.append("team %d transfer policy out of range" % t)
    for p in probs:
        print("  !! " + p)
    for name in ("rank", "world_rank", "stadium", "money", "city"):
        vals = [r[name] for r in teams.records.values()]
        print("  %-10s %d-%d" % (name, min(vals), max(vals)))
    print("  managers %d distinct" % len(set(managers)))

    p = os.path.join(root, NATION_TBB)
    uefa_tail = [n for n, r in nations.rows.items() if n > NationData.UEFA and (r[0] or r[1])]
    print("%s  %d nations, %d with UEFA values%s" % (
        p, len(nations.rows), sum(1 for r in nations.rows.values() if r[0] or r[1]),
        "  !! UEFA values past nation 52 (never read): %s" % uefa_tail if uefa_tail else ""))

    p = os.path.join(root, STADIUM_TBB)
    bad = [i for i, r in enumerate(stadiums.rows) if r[0] > 1 or r[1] > 4]
    print("%s  %d stadiums, %d with a roof, capacity %d-%d%s" % (
        p, len(stadiums.rows), sum(r[0] for r in stadiums.rows),
        min(stadiums.capacity(i) for i in range(len(stadiums.rows))),
        max(stadiums.capacity(i) for i in range(len(stadiums.rows))),
        "  !! roof/level out of range: %s" % bad if bad else ""))

    p = find(root, MAPTEAM_TBB)
    _, tables = tbb.load(p)
    d = tables[0].data
    pairs = [struct.unpack_from("<HH", d, i * 4) for i in range(len(d) // 4)]
    probs = []
    if sorted(t for t, _ in pairs) != list(range(3, 3 + len(pairs))):
        probs.append("teams are not 3-%d" % (2 + len(pairs)))
    if any(flag > 1 for _, flag in pairs):
        probs.append("flags other than 0/1")
    print("%s  %d teams, %d flagged%s" % (p, len(pairs), sum(f for _, f in pairs),
                                        "  !! " + "; ".join(probs) if probs else ""))


def cmd_teams(root, teams, names):
    db = TeamDb(find(root, SIM_PAC))
    stadiums = StadiumData(find(root, STADIUM_TBB))
    mes = default_mes(root)
    cities = category_names(mes, CITY_CATEGORY)
    states = category_names(mes, STATE_CATEGORY)
    pb = None
    if os.path.exists(os.path.join(root, PBDATA)):
        import pbdata
        pb = pbdata.PbData(os.path.join(root, PBDATA))
    for t in teams or sorted(db.records):
        if t not in db.records:
            raise SystemExit("team %d has no club record (%d-%d)" % (
                t, TEAM_FIRST, TEAM_FIRST + len(db.records) - 1))
        r = db.records[t]
        mgr = str(r["manager"])
        if pb and pb.data and 0 <= r["manager"] < pb.counts[1]:
            mgr = pb.record("managers", r["manager"]).name
        s = r["stadium"]
        stad = "%d (%d seats%s)" % (s, stadiums.capacity(s), ", roof" if stadiums.rows[s][0] else "") \
            if 0 <= s < len(stadiums.rows) else str(s)
        print("%s  rank %2d  world %4d  manager %-16s stadium %s" % (
            label(names, t), r["rank"], r["world_rank"], mgr, stad))
        print("      city %s  listed under %s / %s  foreign %d  newface %d  region %d  money %d"
              "  f_0b %d f_0c %d f_0d %d f_0f %d" % (
                  cities.get(r["city"], r["city"]), states.get(r["list_state"], r["list_state"]),
                  cities.get(r["list_city"], r["list_city"]), r["foreign"], r["newface"],
                  r["search_region"], r["money"], r["f_0b"], r["f_0c"], r["f_0d"], r["f_0f"]))


def cmd_nations(root):
    nat = NationData(find(root, NATION_TBB))
    names = {}
    try:
        import pbdata
        names = pbdata.nation_names(os.path.join(root, PBDATA), default_mes(root))
    except (ImportError, ValueError, OSError):
        pass
    print("nation                    UEFA rank  UEFA points  world rating")
    for n, (rank, points, world) in nat.rows.items():
        print("%3d %-22s %9s  %11s  %12d" % (
            n, names.get(n, ""), rank if n <= NationData.UEFA else "-",
            points if n <= NationData.UEFA else "-", world))


def cmd_stadiums(root):
    st = StadiumData(find(root, STADIUM_TBB))
    print("  id  roof  level  capacity")
    for i, (roof, level, _) in enumerate(st.rows):
        print("%4d  %4s  %5d  %8d" % (i, "yes" if roof else "no", level, st.capacity(i)))


def cmd_setteam(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    db = TeamDb(path)
    team = None
    for a in args:
        if "=" not in a:
            team = int(a, 0)
            if team not in db.records:
                raise SystemExit("team %d has no club record" % team)
            continue
        if team is None:
            raise SystemExit("give a team id before %r" % a)
        name, value = a.split("=", 1)
        try:
            old = set_team_field(db.records[team], name, int(value, 0))
        except ValueError as e:
            raise SystemExit(str(e))
        print("team %d %s: %d -> %d" % (team, name, old, db.records[team][name]))
    with open(out_path, "wb") as f:
        f.write(db.encode())
    print("wrote %s (same size; patch it with patch_disc.py)" % out_path)


def cmd_setrows(cls, label, path, out_path, args):
    """setnation and setstadium: <row> <field>=<value> ... [<row> ...]."""
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    table = cls(path)
    row = None
    for a in args:
        if "=" not in a:
            row = int(a, 0)
            continue
        if row is None:
            raise SystemExit("give a %s before %r" % (label, a))
        name, value = a.split("=", 1)
        try:
            old = table.set(row, name, int(value, 0))
        except ValueError as e:
            raise SystemExit(str(e))
        print("%s %d %s: %d -> %s" % (label, row, name, old, value))
    out = table.encode()
    if len(out) != len(table.buf):
        raise SystemExit("rebuilt file is %d bytes, not %d" % (len(out), len(table.buf)))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s (same size; patch it with patch_disc.py)" % out_path)


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
    mes = _opt(args, "--mes")
    lang = int(_opt(args, "--lang", "1"))
    if not args:
        print(__doc__)
        return 1
    root = args[0]
    if cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:])
        return 0
    if cmd == "setteam" and len(args) >= 4:
        cmd_setteam(args[0], args[1], args[2:])
        return 0
    if cmd == "setnation" and len(args) >= 4:
        cmd_setrows(NationData, "nation", args[0], args[1], args[2:])
        return 0
    if cmd == "setstadium" and len(args) >= 4:
        cmd_setrows(StadiumData, "stadium", args[0], args[1], args[2:])
        return 0
    if cmd == "swap" and len(args) >= 3:
        cmd_swap(args[0], args[1], args[2:])
        return 0
    if cmd == "nations" and len(args) == 1:
        cmd_nations(root)
        return 0
    if cmd == "stadiums" and len(args) == 1:
        cmd_stadiums(root)
        return 0
    if cmd == "info" and len(args) == 1:
        cmd_info(root)
        return 0
    if cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(root)
        return 0
    names = team_names(mes or default_mes(root), lang)
    if cmd == "leagues" and len(args) == 1:
        cmd_leagues(root, names)
    elif cmd == "past" and len(args) == 1:
        cmd_past(root, names)
    elif cmd == "squads":
        cmd_squads(root, [int(a, 0) for a in args[1:]], names)
    elif cmd == "teams":
        cmd_teams(root, [int(a, 0) for a in args[1:]], names)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
