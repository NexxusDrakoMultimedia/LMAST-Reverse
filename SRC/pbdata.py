"""Player database reader (PBDATA_EU.PAC / PBDATA_JP.PAC) for Let's Make a
Soccer Team! (PS2).

A BINPAC of 4 entries (see DOC/PBDATA_FORMAT.md):

  0  46-byte header: record counts (27,950 players, 3,000 managers and
     coaches, 1,000 scouts) and record sizes (98, 81, 71 bytes)
  1  the records, players then managers then scouts. Each record is a
     fixed-size, MSB-first bit stream: a char[19] name, then bit fields
  2  27,950 u16, one per player (use not traced)
  3  27,950 u16, one per player: the value the game ranks players below
     id 0x63f7 by (getPinfoRank)

Database ids: players 0-27,949, managers from 0x6d2e (27,950), scouts from
0x78e6 (30,950). Ids from 0x7cce (31,950) are edit-mode players.
PBDATA_JP.PAC on the European disc has an empty entry 1.

Confirmed from SLES_541.51: plBp_Create's caller (0x11034c) passes the
entries in order, PlBpinfoTask::initBpmaster (0x20da58) reads the header,
getPbase/getMbase/getSbase (0x20c700, 0x20c808, 0x20c9b8) seek to a
record, PlBitsClass::readBits (0x20bd28) reads MSB first, and
plBits_DecPlPbaseEx/MbaseEx/SbaseEx (0x2e8568, 0x2e8a70, 0x2e8ec8) give
every field's width, order and adjustment. Field names come from the
functions that read them (plPinfo_IsForeigner, plPinfo_IsEU,
plPinfo_IsSkill, getPinfoRank, getPinfoApos0, pwkTeam_SetUnumberOpinfo);
fields without a known reader keep their offset as a name (f_2c, ...).

The player detail screen's 14 bars (SPEED ... MARK, or SAVIN ... JUMP for
goalkeepers) are averages of the first 33 abilities (ConvertPlayer_Bar,
0x285380); `show` and `csv` compute them from the database values.

Usage:
    python pbdata.py info <PBDATA_*.PAC> ...                         # layout checks + counts
    python pbdata.py list <PBDATA.PAC> [players|managers|scouts] [--find TEXT] [--mes MES.PAC]
    python pbdata.py show <PBDATA.PAC> <id> ... [--mes MES.PAC]      # every field of some records
    python pbdata.py csv  <PBDATA.PAC> <players|managers|scouts> <out.csv>
    python pbdata.py roundtrip <PBDATA_*.PAC> ...                    # re-encode everything, !! if not identical
    python pbdata.py set    <in.PAC> <out.PAC> <id> <field>=<value> ... [<id> <field>=<value> ...]
    python pbdata.py import <in.PAC> <out.PAC> <players|managers|scouts> <edited.csv>

Writing: records are re-encoded bit for bit (every record on the disc
round-trips) and entry 1 is patched in a copy of the pack; nothing else
moves. Values are given as shown (age=30, height=185, ability.15=99,
money=15000, position.0=3), names up to 18 characters (name=J.Smith).
`import` takes a CSV from `csv`, edited in a spreadsheet, and writes only
the values that changed; the bar columns are derived and ignored.

<id> is a database id (players 0-27,949, managers 27,950-30,949, scouts
30,950-31,949), or kind:index such as m:0. Nationality
names come from MES.PAC (default: ../MESSAGE/MES.PAC next to the pack's
folder) through PLRESOURCECOMMON.PAC's nation -> national-team table.
"""
import csv
import os
import struct
import sys

import pac
import tbb

HEADER_SIZE = 46
NAME_LEN = 0x13             # readBitsStr(name, 0x13)
FIRST_MANAGER = 0x6d2e      # getMbase: id - 0x6d2e
FIRST_SCOUT = 0x78e6        # getSbase: id - 0x78e6
RANK_FROM_ENTRY3 = 0x63f7   # getPinfoRank: ids below this use entry 3
KINDS = ("players", "managers", "scouts")

# plBits_* post-processing tables in SLES_541.51.
MONEY = (0, 200, 1000, 3000, 5000, 7500, 10000, 15000, 20000, 25000,
         30000, 35000, 40000, 45000, 50000, 55000)          # 0x55b970, [v & 0xf]
ABILITY = tuple(range(38, 98, 2)) + (98, 99)                # 0x55b950 via 0x2e8540
assert len(ABILITY) == 32

# (name, struct offset, bits, count, conversion). The order is the order of
# the readBits calls; the offset is where the game stores the value in its
# PlPbase/PlMbase/PlSbase, kept so fields can be matched to game code.
# Conversions: None, ("add", n), "money", "ability", "ability7", "signed".
PLAYER_FIELDS = (
    ("nation", 0x14, 8, 1, None),        # plPinfo_IsForeigner/IsEU read +0x14
    ("rank", 0x18, 5, 1, None),          # getPinfoRank (ids >= 0x63f7)
    ("position", 0x1c, 4, 3, None),      # grid cells 0-12 (POSITION_NAMES); 13 = none
    ("age", 0x28, 7, 1, ("add", 16)),    # decoder adds 0x10
    ("height", 0x29, 8, 1, ("add", 150)),  # adds 0x96; the sum is a byte, so 255 cm at most
    ("weight", 0x2a, 7, 1, ("add", 45)),   # adds 0x2d
    ("shirt", 0x2b, 7, 1, None),         # pwkTeam_SetUnumberOpinfo's preferred number
    ("leg", 0x2c, 3, 1, None),           # bit 0: right foot, else left (empirical); bit 1: two-footed?
    ("f_30", 0x30, 16, 1, None),
    ("f_32", 0x32, 16, 1, None),
    ("money", 0x34, 16, 1, "money"),
    ("f_36", 0x36, 3, 1, None),
    ("f_37", 0x37, 2, 8, None),
    ("f_3f", 0x3f, 4, 8, None),
    ("f_47", 0x47, 3, 2, None),
    ("f_49", 0x49, 5, 1, None),
    ("f_4a", 0x4a, 4, 3, None),
    ("f_4d", 0x4d, 3, 3, None),
    ("f_50", 0x50, 4, 2, None),
    ("f_52", 0x52, 5, 1, None),
    ("f_53", 0x53, 3, 1, None),
    ("f_54", 0x54, 4, 1, None),
    ("f_55", 0x55, 2, 3, None),
    ("f_58", 0x58, 3, 2, None),
    ("f_5a", 0x5a, 2, 1, None),
    ("f_5b", 0x5b, 3, 1, None),
    ("f_5c", 0x5c, 1, 1, None),
    ("f_5d", 0x5d, 4, 1, None),
    ("f_5e", 0x5e, 5, 5, None),
    ("flags", 0x63, 3, 1, None),         # bit 1: EU passport (plPinfo_IsEU)
    ("skills", 0x64, 16, 1, None),       # bit mask, plPinfo_IsSkill
    ("f_66", 0x66, 3, 11, None),
    ("ability", 0x74, 5, 64, "ability"),
)
MANAGER_FIELDS = (
    ("nation", 0x14, 8, 1, None),
    ("f_18", 0x18, 5, 1, None),
    ("job", 0x1c, 3, 1, None),           # PlMinfo +0xa0: which bars CalcManagerAbil shows
    ("f_20", 0x20, 16, 1, None),
    ("f_22", 0x22, 6, 1, None),
    ("money", 0x24, 16, 1, "money"),
    ("f_26", 0x26, 4, 4, None),
    ("f_2a", 0x2a, 2, 5, None),
    ("f_2f", 0x2f, 3, 4, None),
    ("f_33", 0x33, 2, 1, None),
    ("f_34", 0x34, 6, 1, None),
    ("f_35", 0x35, 3, 8, None),
    ("f_3d", 0x3d, 8, 3, None),
    ("f_40", 0x40, 3, 7, None),
    ("f_47", 0x47, 5, 5, None),
    ("f_4c", 0x4c, 9, 2, "signed"),      # sign-extended from bit 8, stored as s32
    ("f_54", 0x54, 9, 4, "signed"),
    ("f_64", 0x64, 1, 2, None),
    ("ability", 0x66, 5, 48, "ability"),
)
SCOUT_FIELDS = (
    ("nation", 0x14, 8, 1, None),
    ("f_18", 0x18, 8, 1, None),
    ("f_1c", 0x1c, 5, 1, None),
    ("f_20", 0x20, 16, 1, None),
    ("money", 0x22, 16, 1, "money"),
    ("f_24", 0x24, 4, 4, None),
    ("f_28", 0x28, 1, 1, None),
    ("f_29", 0x29, 7, 4, None),
    ("ability", 0x2d, 7, 45, "ability7"),  # 7-bit, clamped to 31 before the table
)
FIELDS = dict(zip(KINDS, (PLAYER_FIELDS, MANAGER_FIELDS, SCOUT_FIELDS)))

# plPinfo_Abil2PSM (0x216f10): the growth group of each of the 64 player
# abilities. InitAbil scales an ability's random start offset by +0x4a, +0x4b
# or +0x4c for groups P, S and M.
def ability_group(n):
    return "S" if n < 0x13 else ("P" if n < 0x1a else "M")

# The 14 bars of the player detail screen, WP::CDetailManager::
# ConvertPlayer_Bar (0x285380). Each is a list of ability numbers whose
# levels are averaged (integer division). The first 7 are shared; the last
# 7 depend on whether the player is a goalkeeper (PlPinfo +4 == 0, the main
# position). Labels are messages 0x2774+ of the detail category.
BARS_COMMON = (("SPEED", (0, 20, 22)), ("PHYSI", (24, 25)), ("STAMI", (23,)),
               ("MENTA", (26, 27)), ("SUPPO", (30, 31)),
               ("SYSTE", tuple(range(8))), ("TACTI", tuple(range(11))))
BARS_FIELD = (("DRIBB", (0, 1)), ("SHOT", (2, 3, 24)), ("PASS", (4, 5, 6)),
              ("FK", (14,)), ("HEAD", (7, 25, 21)), ("INTER", (11,)), ("MARK", (13,)))
BARS_GK = (("SAVIN", (15,)), ("HANDL", (16,)), ("CROSS", (17,)), ("GO FW", (18,)),
           ("DISTR", (4, 5, 24)), ("AGILI", (22,)), ("JUMP", (21,)))


# Player skills, the bits of +0x64 (plPinfo_IsSkill 0x218748). Bit n is
# described by message 6000 + n of category 2000; the short labels here
# are summaries of those texts. Empirical: across the database bits 3, 5
# and 10 are held by goalkeepers only, 0 and 1 mostly by defenders, 2, 4
# and 11-14 mostly by forwards. The tactics substitution menu tests bit 7
# (0x2f6558), the super sub.
SKILL_MESSAGE = (2000, 6000)
SKILLS = ("covering", "offside line", "penalty taker", "penalty stopper",
          "one-on-one finisher", "one-on-one keeper", "long throw", "super sub",
          "through balls", "positioning", "reflex saves", "acrobatic shot",
          "one-touch shot", "goal machine", "poacher", "playmaker")


def skill_names(mask):
    return [SKILLS[b] for b in range(16) if mask >> b & 1]


def bars(abilities, goalkeeper):
    """[(label, value)] as the detail screen computes them. With database
    values this is the player before InitAbil's random start offset and
    before any growth, so a save will differ."""
    out = []
    for label, src in BARS_COMMON + (BARS_GK if goalkeeper else BARS_FIELD):
        out.append((label, sum(abilities[a] for a in src) // len(src)))
    return out


def hexagon(abilities, weights, goalkeeper):
    """The 6 hexagon values, plPinfo_CalcHexagon (0x217ce0) through
    plPinfo_CalcHexAbil (0x217850): for hexagon h, the weighted average of the
    abilities whose {u8 hexagon, u8 weight} pairs name h. `weights` is
    PLRESOURCECOMMON.PAC entry 2, table 0: 8 bytes per ability, the field
    variant at +4 and the goalkeeper variant at +0. CalcHexagonNG uses the
    field variant for all six; CalcHexagon redoes 0 and 1 with the
    goalkeeper variant for goalkeepers."""
    def calc(h, var):
        total = wsum = 0
        for a in range(64):
            for k in range(2):
                o = a * 8 + var + k * 2
                if weights[o] == h and weights[o + 1]:
                    total += abilities[a] * weights[o + 1]
                    wsum += weights[o + 1]
        return total // wsum if wsum else 0
    vals = [calc(h, 4) for h in range(6)]
    if goalkeeper:
        vals[0], vals[1] = calc(0, 0), calc(1, 0)
    return vals


# Manager and coach bars, WP::CDetailManager::CalcManagerAbil (0x286cd0).
# PlMinfo is 4 bytes and then the PlMbase, so PlMinfo +0x6a is ability 0.
# 12 shared bars, then a set chosen by the job (PlMinfo +0xa0 = PlMbase
# +0x1c) through the jump table at 0x557630.
STAFF_BARS = (("ATTST", (45,)), ("TEAMW", (46,)), ("FK", (47,)), ("TRAIN", (5,)),
              ("ATKDF", (22,)), ("CENTA", (28,)), ("FLANK", (29, 30)), ("MOTIV", (0,)),
              ("PHYSC", (1,)), ("COMMU", (3,)), ("POPUL", (2,)), ("ASSES", (4,)))
JOB_BARS = {
    "coach": (("DRIBB", (10,)), ("SHOT", (11,)), ("PASS", (12,)), ("HEAD", (13,)),
              ("INTER", (14,)), ("MARK", (15,))),                      # jobs 0-2
    "physical coach": (("SPEED", (18,)), ("PHYSI", (20,)), ("STAMI", (19,)),
                       ("MENTA", (21,))),                               # job 3
    "GK coach": (("SAVIN", (16,)), ("HND", (17,))),                    # job 4
    "manager": (("FASTB", (39,)), ("SLOWB", (40,)), ("WINGP", (41,)), ("DIREC", (42,)),
                ("OFFSI", (43,)), ("CLOSD", (44,))),                    # job 5 and up
}
# Jobs (empirical, from each job's average bars): 0 a manager, 1 an
# attacking coach, 2 a defensive coach. The game titles all three
# "Assistant Coach" and shows them the same coaching bars. Hired staff get
# 5 (manager) or 6 (youth manager, pwkTeam_SetYManager 0x26bd28). Coaches
# and former players can become managers too.
JOB_ROLE = {0: "coach", 1: "coach", 2: "coach", 3: "physical coach", 4: "GK coach"}
JOB_NAMES = {0: "manager", 1: "attacking coach", 2: "defensive coach",
             3: "physical coach", 4: "GK coach", 5: "manager", 6: "youth manager"}

# Scout bars, WP::CDetailManager::ConvertScout (0x287c60): single abilities.
# PlSinfo is 4 bytes and then the PlSbase. A 12th value (ability 25) is
# computed as well but has no label on the screen.
SCOUT_BARS = (("CLB", (0,)), ("PLAYE", (1,)), ("FINDP", (3,)), ("YOUTH", (4,)),
              ("YOUNG", (5,)), ("OLDER", (6,)), ("VETER", (7,)), ("MANAG", (21,)),
              ("ACOAC", (22,)), ("PCOAC", (23,)), ("GCOAC", (24,)))


def average_bars(abilities, spec):
    return [(label, sum(abilities[a] for a in src) // len(src)) for label, src in spec]


def staff_bars(abilities, role):
    """The 12 shared bars plus the set for `role` ("manager", "coach", ...)."""
    return average_bars(abilities, STAFF_BARS + JOB_BARS[role])


# Position aptitude, plPinfo_CalcAptPos (0x217f70). The 13 cells of the
# detail screen's pitch grid are the 13 position numbers. A cell's fit is
# a weighted sum of abilities (plPinfo_GetPositionFitValue 0x217e48, table
# at 0x532610): 33 is goalkeeper, 34-41 are row aptitudes (side, centre),
# and 42/43/44 add a centre / left / right leaning. Which of 43 and 44 is
# the left is empirical (the screen's orientation).
APT_CELLS = (
    ((33, 1.0),),
    ((34, 0.7), (43, 0.3)), ((34, 0.7), (44, 0.3)),
    ((35, 0.7), (42, 0.2), (43, 0.05), (44, 0.05)),
    ((36, 0.7), (43, 0.3)), ((36, 0.7), (44, 0.3)),
    ((37, 0.7), (42, 0.2), (43, 0.05), (44, 0.05)),
    ((38, 0.7), (43, 0.3)), ((38, 0.7), (44, 0.3)),
    ((39, 0.7), (42, 0.2), (43, 0.05), (44, 0.05)),
    ((40, 0.7), (43, 0.3)), ((40, 0.7), (44, 0.3)),
    ((41, 0.7), (42, 0.2), (43, 0.05), (44, 0.05)),
)
# 0x5327b0: {u8 min, u8 enough, f32 share of the best cell}. The first row
# a cell passes gives level 4, 3, 2 or 1; none gives 0.
APT_LEVELS = ((70, 80, 1.0), (60, 70, 0.95), (50, 60, 0.9), (40, 50, 0.8))
# Position numbers, the grid cells: rows from the goal up, each left,
# right, centre. The row names are descriptive, not from the game.
POSITION_NAMES = ("GK", "DF-L", "DF-R", "DF-C", "DM-L", "DM-R", "DM-C",
                  "AM-L", "AM-R", "AM-C", "FW-L", "FW-R", "FW-C")


def position_name(p):
    return POSITION_NAMES[p] if p < len(POSITION_NAMES) else "-"


def aptitude(abilities, positions):
    """([fit value], [level 0-4]) per cell, as plPinfo_CalcAptPos computes
    them: levels relative to the best cell, then +1 (to at most 4) for each
    of the player's listed positions. Database values, before the game's
    random start offset."""
    # The game sums in floats and converts each fit to an integer byte.
    fits = [int(sum(abilities[a] * w for a, w in cell)) for cell in APT_CELLS]
    best = max(fits)
    levels = []
    for fit in fits:
        level = 0
        for i, (low, enough, share) in enumerate(APT_LEVELS):
            if fit >= low and (fit >= best * share or fit >= enough):
                level = 4 - i
                break
        levels.append(level)
    for p in positions:
        if p < len(levels) and levels[p] < 4:
            levels[p] += 1
    return fits, levels


def aptitude_grid(levels):
    """The grid as the screen draws it: forwards at the top, left to right."""
    rows = []
    for row in range(3, -1, -1):
        left, right, centre = 1 + row * 3, 2 + row * 3, 3 + row * 3
        rows.append("%d %d %d" % (levels[left], levels[centre], levels[right]))
    return " | ".join(rows) + " | GK %d" % levels[0]


def hex_weights(pac_path):
    common = os.path.join(os.path.dirname(pac_path), "PLRESOURCECOMMON.PAC")
    if not os.path.exists(common):
        return None
    h = pac.load_header(common)
    with open(pac.data_path(common, h), "rb") as f:
        buf = f.read()
    off, size, _, _ = h.entries[2]
    _, tables = tbb.parse(buf[off:off + size])
    return tables[0].data


def field_bits(fields):
    return NAME_LEN * 8 + sum(bits * count for _, _, bits, count, _ in fields)


def convert(conv, v, bits):
    if conv is None:
        return v
    if conv == "money":
        return MONEY[v & 0xf]
    if conv == "ability":
        return ABILITY[v]
    if conv == "ability7":
        return ABILITY[min(v, 31)]
    if conv == "signed":
        return v - (1 << bits) if v & (1 << (bits - 1)) else v
    return v + conv[1]


def unconvert(conv, value, bits, old_raw=None):
    """The stored value for `value`, the inverse of convert(). If the old
    stored value already converts to `value` it is kept, so lossy fields
    (money uses only the low 4 bits) round-trip unchanged."""
    if old_raw is not None and convert(conv, old_raw, bits) == value:
        return old_raw
    if conv is None:
        raw = value
    elif conv == "money":
        if value not in MONEY:
            raise ValueError("money must be one of %s" % ", ".join(map(str, MONEY)))
        raw = MONEY.index(value)
    elif conv in ("ability", "ability7"):
        if value not in ABILITY:
            raise ValueError("ability must be one of %s" % ", ".join(map(str, ABILITY)))
        raw = ABILITY.index(value)
    elif conv == "signed":
        if not -(1 << (bits - 1)) <= value < 1 << (bits - 1):
            raise ValueError("%d does not fit a signed %d-bit field" % (value, bits))
        raw = value & ((1 << bits) - 1)
    else:
        # plBits_DecPlPbaseEx stores the sum in a byte (sb at 0x2e8a14), so
        # anything above 255 wraps: 313 cm shows as 57 cm.
        if value > 0xff:
            raise ValueError("%d is above 255; the game keeps this value in a byte" % value)
        raw = value - conv[1]
    if not 0 <= raw < 1 << bits:
        lo, hi = convert(conv, 0, bits), convert(conv, (1 << bits) - 1, bits)
        raise ValueError("%d is out of range (%d-%d)" % (value, lo, hi))
    return raw


class BitWriter:
    """The inverse of BitReader: MSB first."""
    def __init__(self):
        self.out, self.acc, self.n = bytearray(), 0, 0

    def write(self, value, bits):
        for i in range(bits - 1, -1, -1):
            self.acc = (self.acc << 1) | ((value >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.out.append(self.acc)
                self.acc = self.n = 0

    def data(self):
        assert self.n == 0, "record is not a whole number of bytes"
        return bytes(self.out)


class BitReader:
    """PlBitsClass::readBits: MSB first, bytes in order."""
    def __init__(self, buf):
        self.buf, self.pos = buf, 0

    def read(self, n):
        v = 0
        for _ in range(n):
            byte = self.buf[self.pos >> 3]
            v = (v << 1) | ((byte >> (7 - (self.pos & 7))) & 1)
            self.pos += 1
        return v


class Record:
    def __init__(self, kind, index, raw):
        self.kind, self.index, self.raw = kind, index, raw
        name = raw[:NAME_LEN]
        self.name = name.split(b"\0")[0].decode("cp850")
        self.name_tail = name[len(name.split(b"\0")[0]):]
        r = BitReader(raw)
        r.pos = NAME_LEN * 8
        self.raw_fields, self.fields = {}, {}
        for fname, _, bits, count, conv in FIELDS[kind]:
            vals = [r.read(bits) for _ in range(count)]
            self.raw_fields[fname] = vals if count > 1 else vals[0]
            conv_vals = [convert(conv, v, bits) for v in vals]
            self.fields[fname] = conv_vals if count > 1 else conv_vals[0]
        self.used_bits = r.pos
        # The rest of the record is padding; readBits never gets there.
        self.spare_bits = len(raw) * 8 - r.pos
        self.spare = r.read(self.spare_bits) if self.spare_bits > 0 else 0
        self.name_raw = bytes(name)

    def encode(self):
        """The record's bytes: name, fields in readBits order, padding."""
        w = BitWriter()
        for byte in self.name_raw:
            w.write(byte, 8)
        for fname, _, bits, count, _ in FIELDS[self.kind]:
            v = self.raw_fields[fname]
            for x in (v if count > 1 else [v]):
                w.write(x, bits)
        w.write(self.spare, self.spare_bits)
        return w.data()

    def set_name(self, text):
        b = text.encode("cp850")
        if len(b) > NAME_LEN - 1:
            raise ValueError("name %r is longer than %d bytes" % (text, NAME_LEN - 1))
        self.name_raw = b + bytes(NAME_LEN - len(b))
        self.name, self.name_tail = text, self.name_raw[len(b):]

    def set(self, fname, value, index=None):
        """Set a field by its shown (converted) value. Returns the old value."""
        spec = next((f for f in FIELDS[self.kind] if f[0] == fname), None)
        if spec is None:
            raise ValueError("%s have no field %r" % (self.kind, fname))
        _, _, bits, count, conv = spec
        if (count > 1) != (index is not None):
            raise ValueError("%s needs an index 0-%d" % (fname, count - 1) if count > 1
                             else "%s takes no index" % fname)
        if count > 1 and not 0 <= index < count:
            raise ValueError("%s index %d out of range 0-%d" % (fname, index, count - 1))
        raws, shown = self.raw_fields, self.fields
        if count > 1:
            raws, shown, key = raws[fname], shown[fname], index
        else:
            key = fname
        old = shown[key]
        raws[key] = unconvert(conv, value, bits, raws[key])
        shown[key] = convert(conv, raws[key], bits)
        return old

    @property
    def db_id(self):
        return self.index + (0, FIRST_MANAGER, FIRST_SCOUT)[KINDS.index(self.kind)]


class PbData:
    def __init__(self, path):
        h = pac.load_header(path)
        if not isinstance(h, pac.BinPac):
            raise ValueError("not a BINPAC")
        with open(pac.data_path(path, h), "rb") as f:
            buf = f.read()
        self.file = buf
        self.entry_spans = [(off, size) for off, size, _, _ in h.entries]
        self.entries = [buf[off:off + size] for off, size, _, _ in h.entries]
        if len(self.entries) != 4:
            raise ValueError("%d entries, expected 4" % len(self.entries))
        hdr = self.entries[0]
        if len(hdr) != HEADER_SIZE:
            raise ValueError("header is %d bytes, expected %d" % (len(hdr), HEADER_SIZE))
        # initBpmaster: +0 version text (skipped if it starts with '0'),
        # +8 3 x u32 counts, +0x14 u32, +0x18 3 x u16 record sizes (u32
        # apart), +0x24 u16.
        self.version = hdr[:4]
        self.counts = struct.unpack_from("<3I", hdr, 8)
        self.field_14 = struct.unpack_from("<I", hdr, 0x14)[0]
        self.sizes = tuple(struct.unpack_from("<H", hdr, 0x18 + 4 * i)[0] for i in range(3))
        self.field_24 = struct.unpack_from("<H", hdr, 0x24)[0]
        self.data = self.entries[1]
        self.rank_values = self._u16s(self.entries[3])
        self.entry2 = self._u16s(self.entries[2])

    @staticmethod
    def _u16s(b):
        return list(struct.unpack("<%dH" % (len(b) // 2), b[:len(b) // 2 * 2]))

    def offset(self, kind):
        k = KINDS.index(kind)
        return sum(self.counts[i] * self.sizes[i] for i in range(k))

    def expected_size(self):
        return self.offset("scouts") + self.counts[2] * self.sizes[2]

    def record(self, kind, index):
        k = KINDS.index(kind)
        if not 0 <= index < self.counts[k]:
            raise ValueError("%s index %d out of range" % (kind, index))
        start = self.offset(kind) + index * self.sizes[k]
        return Record(kind, index, self.data[start:start + self.sizes[k]])

    def records(self, kind):
        if not self.data:
            return
        for i in range(self.counts[KINDS.index(kind)]):
            yield self.record(kind, i)


def encode_records(records):
    """Entry 1 rebuilt from {kind: [Record]} (players, managers, scouts)."""
    return b"".join(r.encode() for kind in KINDS for r in records[kind])


def rebuild(db, entry1):
    """The whole pack with entry 1 replaced. Records are fixed-size, so the
    entry keeps its offset and size and nothing else moves."""
    off, size = db.entry_spans[1]
    if len(entry1) != size:
        raise ValueError("records are %d bytes, the entry is %d" % (len(entry1), size))
    return db.file[:off] + entry1 + db.file[off + size:]


def parse_id(text):
    """Database id, or kind:index (p:12, m:0, s:3)."""
    if ":" in text:
        k, i = text.split(":", 1)
        kind = {"p": "players", "m": "managers", "s": "scouts"}[k[0].lower()]
        return kind, int(i, 0)
    n = int(text, 0)
    if n >= FIRST_SCOUT:
        return "scouts", n - FIRST_SCOUT
    if n >= FIRST_MANAGER:
        return "managers", n - FIRST_MANAGER
    return "players", n


# --- names -------------------------------------------------------------------

def nation_names(pac_path, mes_path, lang=1):
    """{nation: name}: plMisc_Nati2NatiTeam (0x215a00: PLRESOURCECOMMON entry
    3, table 2, u16 per nation) gives the national team, whose name is a
    team name (initteam.team_names)."""
    common = os.path.join(os.path.dirname(pac_path), "PLRESOURCECOMMON.PAC")
    if not (os.path.exists(common) and mes_path and os.path.exists(mes_path)):
        return {}
    import initteam
    teams = initteam.team_names(mes_path, lang)
    h = pac.load_header(common)
    with open(pac.data_path(common, h), "rb") as f:
        buf = f.read()
    off, size, _, _ = h.entries[3]
    _, tables = tbb.parse(buf[off:off + size])
    t = tables[2]
    nati_team = struct.unpack("<%dH" % (t.size // 2), t.data)
    return {n: teams[team] for n, team in enumerate(nati_team) if team and team in teams}


def default_mes(pac_path):
    return os.path.join(os.path.dirname(os.path.abspath(pac_path)), os.pardir,
                        "MESSAGE", "MES.PAC")


# --- commands ----------------------------------------------------------------

def check(db):
    """Problems with the layout, as a list of strings."""
    probs = []
    if db.version[:1] == b"0":
        probs.append("header starts with '0': initBpmaster would skip it")
    for kind, fields, size in zip(KINDS, (PLAYER_FIELDS, MANAGER_FIELDS, SCOUT_FIELDS), db.sizes):
        if field_bits(fields) > size * 8:
            probs.append("%s: %d bits of fields in a %d-byte record" % (kind, field_bits(fields), size))
    if db.data and len(db.data) != db.expected_size():
        probs.append("records entry is %d bytes, header says %d" % (len(db.data), db.expected_size()))
    for name, arr in (("entry 2", db.entry2), ("entry 3", db.rank_values)):
        if len(arr) != db.counts[0]:
            probs.append("%s has %d values for %d players" % (name, len(arr), db.counts[0]))
    return probs


def cmd_info(paths):
    for path in paths:
        try:
            db = PbData(path)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            continue
        probs = check(db)
        print("%s  version %r  counts %s  sizes %s  header +0x14 %d  +0x24 %d%s" % (
            path, db.version.decode("latin-1"), "/".join(map(str, db.counts)),
            "/".join(map(str, db.sizes)), db.field_14, db.field_24,
            "  !! " + "; ".join(probs) if probs else ""))
        if not db.data:
            print("  records entry is empty (no player data in this pack)")
            continue
        for kind in KINDS:
            recs = list(db.records(kind))
            bad_names = sum(1 for r in recs if r.name_tail.strip(b"\0"))
            spare = sum(1 for r in recs if r.spare)
            empty = sum(1 for r in recs if not r.name)
            nations = [r.fields["nation"] for r in recs]
            line = "  %-8s %6d records  %d/%d bits used  %d unnamed  nations %d-%d" % (
                kind, len(recs), recs[0].used_bits if recs else 0,
                db.sizes[KINDS.index(kind)] * 8, empty, min(nations), max(nations))
            p = []
            if bad_names:
                p.append("%d names with bytes after the terminator" % bad_names)
            if spare:
                p.append("%d records with non-zero padding bits" % spare)
            if kind == "players":
                pos = [x for r in recs for x in r.fields["position"]]
                if max(pos) > 13:
                    p.append("position above 13")
            print(line + ("  !! " + "; ".join(p) if p else ""))
        players = list(db.records("players"))
        for fname in ("age", "height", "weight", "shirt", "rank"):
            vals = [r.fields[fname] for r in players]
            print("  players %-7s %d-%d" % (fname, min(vals), max(vals)))
        ab = [a for r in players for a in r.fields["ability"]]
        print("  players ability %d-%d over %d values" % (min(ab), max(ab), len(ab)))


def summary(r, nations):
    f = r.fields
    nat = nations.get(f["nation"], str(f["nation"]))
    if r.kind == "players":
        pos = "/".join(position_name(p) for p in f["position"] if p != 13) or "-"
        leg = ("R" if f["leg"] & 1 else "L") + ("+" if f["leg"] & 2 else " ")
        return "%5d  %-19s %-16s age %2d  %3dcm %3dkg  %s  pos %-14s shirt %2d  rank %2d" % (
            r.db_id, r.name, nat, f["age"], f["height"], f["weight"], leg, pos, f["shirt"], f["rank"])
    if r.kind == "managers":
        return "%5d  %-19s %-16s %-14s money %5d" % (
            r.db_id, r.name, nat, JOB_ROLE.get(f["job"], "manager"), f["money"])
    return "%5d  %-19s %-16s money %5d" % (r.db_id, r.name, nat, f["money"])


def cmd_list(path, kind, find, nations):
    db = PbData(path)
    for r in db.records(kind):
        if find and find.lower() not in r.name.lower():
            continue
        print(summary(r, nations))


def cmd_show(path, ids, nations):
    db = PbData(path)
    weights = hex_weights(path)
    for text in ids:
        kind, index = parse_id(text)
        r = db.record(kind, index)
        print(summary(r, nations))
        for fname, off, bits, count, conv in FIELDS[kind]:
            v = r.fields[fname]
            raw = r.raw_fields[fname]
            shown = " ".join(map(str, v)) if isinstance(v, list) else str(v)
            if conv not in (None, "ability", "ability7") and v != raw:
                shown += "  (stored %s)" % (" ".join(map(str, raw)) if isinstance(raw, list) else raw)
            print("    +%#04x %-9s %2d bit%s  %s" % (off, fname, bits,
                                                   " x%-2d" % count if count > 1 else "    ", shown))
        if kind == "managers":
            role = JOB_ROLE.get(r.fields["job"], "manager")
            print("    as %-14s %s" % (role, "  ".join("%s %d" % lv for lv in staff_bars(r.fields["ability"], role))))
            if role != "manager":
                print("    as manager        %s" % "  ".join(
                    "%s %d" % lv for lv in average_bars(r.fields["ability"], JOB_BARS["manager"])))
        if kind == "scouts":
            print("    screen    %s" % "  ".join("%s %d" % lv for lv in average_bars(r.fields["ability"], SCOUT_BARS)))
        if kind == "players":
            gk = r.fields["position"][0] == 0
            print("    skills    %s" % (", ".join(skill_names(r.fields["skills"])) or "none"))
            print("    screen    %s" % "  ".join("%s %d" % lv for lv in bars(r.fields["ability"], gk)))
            print("    positions %s  (levels 0-4, forwards at the top, left centre right)" % aptitude_grid(
                aptitude(r.fields["ability"], r.fields["position"])[1]))
            if weights:
                print("    hexagon   %s" % "  ".join(
                    "%d:%d" % hv for hv in enumerate(hexagon(r.fields["ability"], weights, gk))))
            print("    entry 2 %d, entry 3 %d%s" % (
                db.entry2[index], db.rank_values[index],
                "" if index < RANK_FROM_ENTRY3 else " (rank read from +0x18 instead)"))


def cmd_csv(path, kind, out_path):
    db = PbData(path)
    header = ["id", "name"]
    for fname, _, _, count, _ in FIELDS[kind]:
        header += [fname] if count == 1 else ["%s_%d" % (fname, i) for i in range(count)]
    if kind == "players":
        header += ["entry2", "entry3"]
        header += [label for label, _ in BARS_COMMON]
        header += ["%s/%s" % (f, g) for (f, _), (g, _) in zip(BARS_FIELD, BARS_GK)]
    elif kind == "managers":
        header += [label for label, _ in STAFF_BARS + JOB_BARS["manager"]]
        header += ["job_bar_%d" % i for i in range(6)]
    else:
        header += [label for label, _ in SCOUT_BARS]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        n = 0
        for r in db.records(kind):
            row = [r.db_id, r.name]
            for fname, _, _, count, _ in FIELDS[kind]:
                v = r.fields[fname]
                row += v if count > 1 else [v]
            if kind == "players":
                row += [db.entry2[r.index], db.rank_values[r.index]]
                row += [v for _, v in bars(r.fields["ability"], r.fields["position"][0] == 0)]
            elif kind == "managers":
                role = JOB_ROLE.get(r.fields["job"], "manager")
                row += [v for _, v in staff_bars(r.fields["ability"], "manager")]
                job = [v for _, v in average_bars(r.fields["ability"], JOB_BARS[role])]
                row += job + [""] * (6 - len(job))
            else:
                row += [v for _, v in average_bars(r.fields["ability"], SCOUT_BARS)]
            w.writerow(row)
            n += 1
    print("%s: %d %s" % (out_path, n, kind))


def cmd_roundtrip(paths):
    for path in paths:
        try:
            db = PbData(path)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            continue
        if not db.data:
            print("%s  records entry is empty, nothing to rebuild" % path)
            continue
        records = {k: list(db.records(k)) for k in KINDS}
        bad = [r.db_id for k in KINDS for r in records[k] if r.encode() != r.raw]
        out = rebuild(db, encode_records(records))
        probs = []
        if bad:
            probs.append("records differ: %s%s" % (", ".join(map(str, bad[:10])),
                                                  " ..." if len(bad) > 10 else ""))
        if out != db.file:
            probs.append("rebuilt pack is not byte-identical")
        print("%s  %d records re-encoded, %d differ; pack %s%s" % (
            path, sum(len(v) for v in records.values()), len(bad),
            "identical" if out == db.file else "differs",
            "  !! " + "; ".join(probs) if probs else ""))


def _parse_assign(text):
    """name=Foo, age=30, ability.15=99 -> (field, index, value text)."""
    key, value = text.split("=", 1)
    index = None
    if "." in key:
        key, idx = key.split(".", 1)
        index = int(idx, 0)
    return key, index, value


def apply_value(r, fname, index, text):
    """Set one field from its text. Returns (old, new) shown values."""
    if fname == "name":
        old = r.name
        r.set_name(text)
        return old, r.name
    old = r.set(fname, int(text, 0), index)
    return old, (r.fields[fname][index] if index is not None else r.fields[fname])


def _load_for_edit(src, out_path):
    if os.path.abspath(out_path) == os.path.abspath(src):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    db = PbData(src)
    if not db.data:
        raise SystemExit("%s has no records" % src)
    return db, {k: list(db.records(k)) for k in KINDS}


def _write_pack(out_path, db, records):
    with open(out_path, "wb") as f:
        f.write(rebuild(db, encode_records(records)))


def _plural(n, word):
    return "%d %s%s" % (n, word, "" if n == 1 else "s")


def cmd_set(src, out_path, args):
    db, records = _load_for_edit(src, out_path)
    r, changes = None, 0
    for a in args:
        if "=" not in a:
            kind, index = parse_id(a)
            if not 0 <= index < len(records[kind]):
                raise SystemExit("%s: no such record" % a)
            r = records[kind][index]
            continue
        if r is None:
            raise SystemExit("give a record id before %r" % a)
        fname, index, text = _parse_assign(a)
        try:
            old, new = apply_value(r, fname, index, text)
        except ValueError as e:
            raise SystemExit("%d %s: %s" % (r.db_id, r.name, e))
        label = fname if index is None else "%s.%d" % (fname, index)
        print("%5d  %-19s %s: %s -> %s" % (r.db_id, r.name, label, old, new))
        changes += 1
    _write_pack(out_path, db, records)
    print("%s: %s" % (out_path, _plural(changes, "change")))


def cmd_import(src, out_path, kind, csv_path):
    """Apply a CSV written by `csv`, possibly edited. Only values that differ
    from the pack are written. Other columns (the bars, entry2/entry3) are
    derived and ignored."""
    db, records = _load_for_edit(src, out_path)
    columns = {"name": ("name", None)}
    for fname, _, _, count, _ in FIELDS[kind]:
        if count == 1:
            columns[fname] = (fname, None)
        else:
            columns.update(("%s_%d" % (fname, i), (fname, i)) for i in range(count))
    changed_records = changes = 0
    with open(csv_path, newline="", encoding="utf-8") as f:
        for line_no, row in enumerate(csv.DictReader(f), 2):
            row_kind, index = parse_id(row["id"])
            if row_kind != kind or not 0 <= index < len(records[kind]):
                raise SystemExit("%s line %d: id %s is not one of the %s" % (
                    csv_path, line_no, row["id"], kind))
            r = records[kind][index]
            touched = False
            for col, text in row.items():
                if col not in columns or not text:
                    continue
                fname, i = columns[col]
                current = r.name if fname == "name" else (
                    r.fields[fname][i] if i is not None else r.fields[fname])
                if str(current) == text:
                    continue
                try:
                    old, new = apply_value(r, fname, i, text)
                except ValueError as e:
                    raise SystemExit("%s line %d, %s: %s" % (csv_path, line_no, col, e))
                print("%5d  %-19s %s: %s -> %s" % (r.db_id, r.name, col, old, new))
                changes += 1
                touched = True
            changed_records += touched
    _write_pack(out_path, db, records)
    print("%s: %s in %s" % (out_path, _plural(changes, "change"),
                            _plural(changed_records, "record")))


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
    find = _opt(args, "--find")
    mes = _opt(args, "--mes")
    if cmd == "info" and args:
        cmd_info(args)
        return 0
    if cmd in ("list", "show") and args:
        nations = nation_names(args[0], mes or default_mes(args[0]))
        if cmd == "list" and len(args) <= 2:
            kind = args[1] if len(args) == 2 else "players"
            if kind not in KINDS:
                raise SystemExit("kind must be one of %s" % ", ".join(KINDS))
            cmd_list(args[0], kind, find, nations)
            return 0
        if cmd == "show" and len(args) >= 2:
            cmd_show(args[0], args[1:], nations)
            return 0
    if cmd == "csv" and len(args) == 3 and args[1] in KINDS:
        cmd_csv(args[0], args[1], args[2])
        return 0
    if cmd == "roundtrip" and args:
        cmd_roundtrip(args)
        return 0
    if cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:])
        return 0
    if cmd == "import" and len(args) == 4 and args[2] in KINDS:
        cmd_import(args[0], args[1], args[2], args[3])
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
