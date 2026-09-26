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
    ("position", 0x1c, 4, 3, None),      # getPinfoApos0 returns the first; 13 = none
    ("age", 0x28, 7, 1, ("add", 16)),    # decoder adds 0x10
    ("height", 0x29, 8, 1, ("add", 150)),  # adds 0x96
    ("weight", 0x2a, 7, 1, ("add", 45)),   # adds 0x2d
    ("shirt", 0x2b, 7, 1, None),         # pwkTeam_SetUnumberOpinfo's preferred number
    ("f_2c", 0x2c, 3, 1, None),
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
    ("f_1c", 0x1c, 3, 1, None),
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
        self.spare = r.read(len(raw) * 8 - r.pos) if len(raw) * 8 > r.pos else 0

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
        pos = "/".join(str(p) for p in f["position"] if p != 13) or "-"
        return "%5d  %-19s %-16s age %2d  %3dcm %3dkg  pos %-8s shirt %2d  rank %2d" % (
            r.db_id, r.name, nat, f["age"], f["height"], f["weight"], pos, f["shirt"], f["rank"])
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
        if kind == "players":
            gk = r.fields["position"][0] == 0
            print("    screen    %s" % "  ".join("%s %d" % lv for lv in bars(r.fields["ability"], gk)))
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
            w.writerow(row)
            n += 1
    print("%s: %d %s" % (out_path, n, kind))


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
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
