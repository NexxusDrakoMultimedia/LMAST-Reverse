# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Virtua Pro Football's edit players: pmplayer.bin, for Let's Make a Soccer
Team! (PS2), which imports them into a career.

The file sits in Virtua Pro Football's memory-card folder
(BESLES-54153FASYS00; the Japanese game's is BISLPM-66324FASYS00). This
game reads it through SAVEPRG.REL: the loader (0x3ed60) decrypts the
whole file with Blowfish and the key "_FC_ACT_2005" (0x547f0), the same
cipher as its own saves (P and S at 0x4bd78/0x4bdc0), then checks a
CRC-16 (0x31470, table 0x53408) of the first 0x1c38 bytes against the
u32 stored after them. The writer (0x3ec60) pads the data and CRC with
zeros to a multiple of 0x400, so the file is 0x2000 bytes.

  0x0000  s16 id[23]       a slot is used when its id is >= 0 (0x3a400)
  0x002e  0x2e bytes       not read by the import
  0x005c  record[23]       0x134 bytes each, record i at 0x5c + i * 0x134
  0x1bf8  0x40 bytes       not read by the import
  0x1c38  u32 CRC-16 of 0x0000-0x1c37

The import (0x3a3b8) converts each used record with 0x3e198 into the
career's edit work (block 1 +0x12600: id, PlPbase at +0x4) and a PlPinfo.
RECORD below lists every record field it reads and what it becomes; the
other record bytes are Virtua Pro Football's alone. The import also sets
age 17, rank 12 (13 if club 1 ranks 23 or lower), and random values for
the personality fields, growth types, policy, adaptability, the 8
dissatisfaction weights, the 8 formation abilities, possession and
attack pattern E (ABILITY_RANDOM). The main position comes from the
abilities (0x3ddc8). Of the 22 play-style ratings only 1-4 count: the
import means to sort them, but its compare function subtracts pointers
(0x3df00), so style t is kept in slot t when rated 70 or more. See
DOC/PMPLAYER_FORMAT.md.

Usage:
    python pmplayer.py info      <pmplayer.bin | folder> ... [--iso ISO]
    python pmplayer.py show      <pmplayer.bin> [slot ...] [--iso ISO]
    python pmplayer.py set       <in> <out> <slot> <field>=<value> ... [<slot> <field>=<value> ...] [--iso ISO]
    python pmplayer.py roundtrip <pmplayer.bin | folder> ... [--iso ISO]
    python pmplayer.py selftest  [--iso ISO]
    python pmplayer.py check     <pmplayer.bin> <career save>

A folder is searched for pmplayer.bin files (a PCSX2 folder memory card,
or one save folder). `show` prints every field of each used slot (or the
slots given) and the values the import gives the career. `set` edits
slots and writes a new file with its CRC. `roundtrip` re-encodes every
field of every record and rebuilds the encrypted file byte for byte.
`check` compares a career's edit player (block 1 +0x12600) with what the
import makes of the record of the same name: every field the import
copies or computes, and the 0x32 bytes it copies to the edit work.
`selftest` builds files without a memory card: an empty one (whose CRC
must be 0x027c, as on the Japanese card) and one with a player made
through `set`, read back field by field.
"""
import os
import struct
import sys

import gamever
import pbdata
import save

# SAVEPRG.REL
KEY = b"_FC_ACT_2005"           # 0x547f0, passed to the decrypt at 0x3edd8
NATION_MAP = 0x4ce80            # 0x3dd78: 145 {u32 nation, u32 VPF nation}
NATIONS = 145
SHIRT_MAP = 0x547e8             # 0x3e1e4: shirt for position groups 0-3

FILE_SIZE = 0x2000
DATA_SIZE = 0x1c38              # the CRC covers this much (0x3eee4)
SLOTS = 23                      # the import's loop counts 0x16 down to 0
RECORDS_OFF = 0x5c
RECORD_SIZE = 0x134
NAME_LEN = 0x13                 # strncpy into the PlPbase name (0x3e214)
SURNAME_OFF, SURNAME_LEN = 0x52, 0x15
CASTNO_MIN = 0x580e             # 0x3e2b4 raises +0x78 to at least this
SCALE = 14                      # 0-7 ratings become v * 14 + 1 (0x3e908)
RAND_LOW, RAND_SPAN = 51, 40    # fcEuroRand_Get0toI(40) + 0x33

# Record bytes copied to a PlPbase ability (pbdata.ABILITY_NAMES), in the
# order 0x3e8e8-0x3eab4 stores them. A byte can feed several abilities.
ABILITY_COPY = (tuple((0x7a + i, i) for i in range(7))
                + tuple((0x82 + i, 7 + i) for i in range(7))
                + ((0x8a, 14),)
                + tuple((0x8e + i, 15 + i) for i in range(8))
                + tuple((0x97 + i, 23 + i) for i in range(3))
                + ((0x9d, 26),)
                + tuple((0xa3 + i, 28 + i) for i in range(4))
                + ((0xae, 33), (0xb0, 34), (0xaf, 35), (0xb1, 36), (0xb2, 37),
                   (0xb4, 38), (0xb3, 39), (0xb5, 41), (0xb6, 42), (0xb7, 43),
                   (0xb8, 44), (0xa8, 53), (0xa9, 55), (0xaa, 56), (0xac, 57),
                   (0xab, 58), (0xa9, 59), (0xa9, 60), (0xaa, 61), (0xaa, 62)))
ABILITY_SCALED = ((0xa2, 27), (0xa1, 32))      # nerve, concentration: v * 14 + 1
WG_FROM = (0xb4, 0xb5)          # WG = int(SM * 0.3f + FW * 0.7f) (0x3e97c)
ABILITY_WG = 40
ABILITY_RANDOM = tuple(range(45, 53)) + (54, 63)
STYLE_OFF, STYLE_COUNT, STYLE_KEEP = 0xb9, 22, 70   # 0x3df10, see imported()
SKILL_OFF = 0xcf                # 16 flags, bit i of PlPbase +0x64 (0x3e170)
TENDENCY_OFF = 0xdf             # 11, copied to PlPbase +0x66
KIT_OFF = 0x12d                 # 7, copied to PlPbase +0x57
WORK_OFF, WORK_LEN = 0xf8, 0x32  # copied as is to the edit work +0xb8


def _ability_field(k):
    return pbdata.ABILITY_NAMES[k].replace(" ", "_")


# (name, offset, kind, low, high, what the import does with it). Kinds:
# "str" (cp850, NUL-padded, high = length), "f32", "u8", "u16".
RECORD = (
    ("nation", 0x00, "u8", 0, 255, "PlPbase nation, through the nation table (0x3dd78); 0 if absent"),
    ("name", 0x01, "str", 0, NAME_LEN, "PlPbase name (the short name the game shows)"),
    ("surname", SURNAME_OFF, "str", 0, SURNAME_LEN, "not read by the import"),
    ("height", 0x68, "f32", 150, 255, "PlPbase height, truncated to a whole number"),
    ("weight", 0x6c, "f32", 45, 172, "PlPbase weight, truncated"),
    ("leg", 0x70, "u8", 0, 3, "PlPbase leg"),
    ("position_group", 0x73, "u8", 0, 3, "PlPbase shirt: 1, 4, 7, 9 for 0-3 (table 0x547e8), else 1"),
    ("castno", 0x78, "u16", 0, 0xffff, "PlPbase castno, at least 22,542"),
) + tuple((_ability_field(k), off, "u8", 1, 99, "PlPbase ability %d" % k)
          for off, k in ABILITY_COPY if (off, k) == next(c for c in ABILITY_COPY if c[0] == off)) + (
    ("injury", 0x9a, "u8", 0, 7, "PlPbase injury_res = 7 - value"),
    ("weak_foot", 0x9b, "u8", 0, 7, "PlPbase weak_foot = value * 2 + 1"),
    ("recovery", 0x9c, "u8", 0, 7, "PlPbase recovery"),
    ("foul", 0x9e, "u8", 0, 7, "PlPbase foul_avoid = (7 - value) * 2 + 1"),
    ("pressure", 0xa0, "u8", 0, 99, "PlPbase pressure = value / 14"),
    ("concentration", 0xa1, "u8", 0, 7, "PlPbase ability 32 = value * 14 + 1"),
    ("nerve", 0xa2, "u8", 0, 7, "PlPbase ability 27 = value * 14 + 1"),
) + tuple(("style_%d" % i, STYLE_OFF + i, "u8", 0, 99,
           "PlPbase style slot %d = style %d if %d or more" % (i, i, STYLE_KEEP) if 1 <= i <= 4
           else "not imported (the import's sort doesn't work)")
          for i in range(STYLE_COUNT)) + tuple(
    ("skill_%d" % i, SKILL_OFF + i, "u8", 0, 1, "PlPbase skills bit %d" % i) for i in range(16)) + tuple(
    ("tendency_%d" % i, TENDENCY_OFF + i, "u8", 0, 4, "PlPbase tendency %d" % i) for i in range(11)) + (
    ("ball_touch", 0xea, "u8", 0, 3, "PlPbase ball_touch"),
    ("dribble_style", 0xeb, "u8", 0, 3, "PlPbase dribble_style"),
) + tuple((name, KIT_OFF + i, "u8", 0, top, "PlPbase %s" % name)
          for i, (name, top) in enumerate(pbdata.KIT_STYLE_MAX))
FIELD = {f[0]: f for f in RECORD}
ABILITY_FIELDS = tuple(f[0] for f in RECORD if f[1] in dict(ABILITY_COPY))
NOTES = {  # record bytes that feed more than one ability
    0xa9: "also attack patterns A and B (abilities 59, 60)",
    0xaa: "also attack patterns C and D (abilities 61, 62)",
    0xb4: "and 0.3 of WG (ability 40)",
    0xb5: "and 0.7 of WG (ability 40)",
}


class Tables:
    """The cipher and the import's tables, from SAVEPRG.REL (either build)."""

    def __init__(self, iso_dir):
        rel_path = os.path.join(iso_dir, "DLL", "SAVEPRG.REL")
        rel = open(rel_path, "rb").read()
        if KEY not in rel:
            raise ValueError("%s: no key %r" % (rel_path, KEY))
        at = lambda a: gamever.at(rel_path, a)
        self.bf = save.Blowfish(rel, KEY, at(save.BF_P), at(save.BF_S))
        self.crc_table = at(save.CRC_TABLE)
        self.rel = rel
        pairs = [struct.unpack_from("<II", rel, at(NATION_MAP) + 8 * i) for i in range(NATIONS)]
        self.nation = {}
        for ours, vpf in pairs:
            self.nation.setdefault(vpf, ours)       # 0x3dd78 takes the first match
        self.shirts = tuple(rel[at(SHIRT_MAP):at(SHIRT_MAP) + 4])

    def crc(self, data):
        return save.crc16(self.rel, data, self.crc_table)


def get(rec, f):
    name, off, kind, _, high, _ = f
    if kind == "str":
        return bytes(rec[off:off + high + 1]).split(b"\0")[0].decode("cp850")
    if kind == "f32":
        return struct.unpack_from("<f", rec, off)[0]
    if kind == "u16":
        return struct.unpack_from("<H", rec, off)[0]
    return rec[off]


def put(rec, f, value):
    name, off, kind, low, high, _ = f
    if kind == "str":
        raw = value.encode("cp850")
        if len(raw) > high:
            raise ValueError("%s: at most %d characters" % (name, high))
        rec[off:off + high + 1] = raw.ljust(high + 1, b"\0")
    elif kind == "f32":
        struct.pack_into("<f", rec, off, value)
    elif kind == "u16":
        struct.pack_into("<H", rec, off, value)
    else:
        rec[off] = value


def parse_value(f, text):
    name, _, kind, low, high, _ = f
    if kind == "str":
        return text
    try:
        v = float(text) if kind == "f32" else int(text, 0)
    except ValueError:
        raise ValueError("%s: %r is not a number" % (name, text))
    if not low <= v <= high:
        raise ValueError("%s: %s is outside %d-%d" % (name, text, low, high))
    return v


class PmPlayer:
    def __init__(self, data, tables):
        if len(data) != FILE_SIZE:
            raise ValueError("%d bytes, not %#x" % (len(data), FILE_SIZE))
        self.tables = tables
        self.plain = bytearray(tables.bf.decrypt(data))

    def ids(self):
        return list(struct.unpack_from("<%dh" % SLOTS, self.plain, 0))

    def record(self, slot):
        o = RECORDS_OFF + slot * RECORD_SIZE
        return self.plain[o:o + RECORD_SIZE]

    def set_record(self, slot, rec):
        o = RECORDS_OFF + slot * RECORD_SIZE
        self.plain[o:o + RECORD_SIZE] = rec

    def stored_crc(self):
        return struct.unpack_from("<I", self.plain, DATA_SIZE)[0]

    def problems(self):
        out = []
        crc = self.tables.crc(bytes(self.plain[:DATA_SIZE]))
        if crc != self.stored_crc():
            out.append("CRC %#06x, file holds %#x" % (crc, self.stored_crc()))
        if any(self.plain[DATA_SIZE + 4:]):
            out.append("padding after the CRC isn't zero")
        return out

    def encode(self):
        """The encrypted file, with the CRC made afresh."""
        plain = bytearray(self.plain)
        struct.pack_into("<I", plain, DATA_SIZE, self.tables.crc(bytes(plain[:DATA_SIZE])))
        plain[DATA_SIZE + 4:] = bytes(FILE_SIZE - DATA_SIZE - 4)
        return self.tables.bf.encrypt(bytes(plain))


def empty(tables):
    """A file with no edit players: every id -1, everything else 0."""
    plain = bytearray(FILE_SIZE)
    struct.pack_into("<%dh" % SLOTS, plain, 0, *([-1] * SLOTS))
    struct.pack_into("<I", plain, DATA_SIZE, tables.crc(bytes(plain[:DATA_SIZE])))
    return tables.bf.encrypt(bytes(plain))


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def imported(rec, tables):
    """[(PlPbase field, value)] the import computes from a record; the
    random fields and the position aren't included."""
    g = lambda off: rec[off]
    out = [("name", get(rec, FIELD["name"])),
           ("nation", tables.nation.get(rec[0], 0)),
           ("age", 17),
           ("height", int(get(rec, FIELD["height"])) & 0xff),
           ("weight", int(get(rec, FIELD["weight"])) & 0xff),
           ("leg", g(0x70)),
           ("shirt", tables.shirts[g(0x73)] if g(0x73) < 4 else 1),
           ("castno", max(get(rec, FIELD["castno"]), CASTNO_MIN)),
           ("pressure", g(0xa0) // SCALE),
           ("injury_res", (7 - g(0x9a)) & 0xff),
           ("recovery", g(0x9c)),
           ("foul_avoid", ((7 - g(0x9e)) * 2 + 1) & 0xff),
           ("weak_foot", (g(0x9b) * 2 + 1) & 0xff),
           ("intelligence", 0),
           ("ball_touch", g(0xea)), ("dribble_style", g(0xeb))]
    out += [(name, g(KIT_OFF + i)) for i, (name, _) in enumerate(pbdata.KIT_STYLE_MAX)]
    # 0x3df10 means to keep the 5 best rated styles, but its qsort compare
    # (0x3df00) subtracts the pointers, not the ratings, so the order stays
    # as it was: slot t gets style t when byte t is rated 70 or more, and
    # slot 0 stays empty.
    out.append(("style", [t if t and g(STYLE_OFF + t) >= STYLE_KEEP else 0 for t in range(5)]))
    out.append(("skills", sum(1 << i for i in range(16) if g(SKILL_OFF + i))))
    out.append(("tendency", [g(TENDENCY_OFF + i) for i in range(11)]))
    ability = [None] * 64
    for off, k in ABILITY_COPY:
        ability[k] = g(off)
    for off, k in ABILITY_SCALED:
        ability[k] = (g(off) * SCALE + 1) & 0xff
    ability[ABILITY_WG] = int(f32(f32(g(WG_FROM[0]) * f32(0.3)) + f32(g(WG_FROM[1]) * f32(0.7))))
    out.append(("ability", ability))
    return out


def files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in sorted(os.walk(p)):
                for n in sorted(names):
                    if n.lower() == "pmplayer.bin":
                        yield os.path.join(root, n)
        else:
            yield p


def label(path):
    return path.replace("\\", "/")


def cmd_info(paths, tables):
    for path in files(paths):
        try:
            pm = PmPlayer(open(path, "rb").read(), tables)
            ids = pm.ids()
            used = [s for s in range(SLOTS) if ids[s] >= 0]
            print("%s  %d edit players  CRC %#06x%s" % (
                label(path), len(used), pm.stored_crc(),
                "".join("  !! " + p for p in pm.problems()[:1]) +
                "".join("; " + p for p in pm.problems()[1:])))
            for s in range(SLOTS):
                rec = pm.record(s)
                if ids[s] < 0:
                    if any(rec):
                        print("  slot %2d  empty, record not blank (not read)" % s)
                    continue
                notes = []
                if not get(rec, FIELD["name"]):
                    notes.append("no name")
                if rec[0] not in tables.nation:
                    notes.append("nation %d isn't in the nation table" % rec[0])
                print("  slot %2d  id %5d  %-19s %-14s nation %3d -> %3d  %3d cm %3d kg  group %d%s" % (
                    s, ids[s], get(rec, FIELD["name"]), get(rec, FIELD["surname"]), rec[0],
                    tables.nation.get(rec[0], 0), get(rec, FIELD["height"]),
                    get(rec, FIELD["weight"]), rec[0x73],
                    "  !! " + "; ".join(notes) if notes else ""))
        except (ValueError, struct.error, OSError) as e:
            print("%s  !! %s" % (label(path), e))


def shown(f, v):
    return "%g" % v if f[2] == "f32" else repr(v) if f[2] == "str" else str(v)


def cmd_show(path, slots, tables):
    pm = PmPlayer(open(path, "rb").read(), tables)
    ids = pm.ids()
    for s in slots or [s for s in range(SLOTS) if ids[s] >= 0]:
        rec = pm.record(s)
        print("slot %d  id %d" % (s, ids[s]))
        for f in RECORD:
            note = NOTES.get(f[1], "")
            print("  +%#05x %-24s %-12s %s%s" % (f[1], f[0], shown(f, get(rec, f)), f[5],
                                                ("; " + note) if note else ""))
        print("  the career gets (PlPbase):")
        for name, v in imported(rec, tables):
            if name == "ability":
                for k, a in enumerate(v):
                    print("    ability %2d %-24s %s" % (k, pbdata.ABILITY_NAMES[k],
                                                        "random 51-90" if a is None else a))
            else:
                print("    %-30s %s" % (name, v))


def apply_edits(pm, args):
    """Edits `<slot> f=v ...` to pm; returns [(slot, name, old, new)]."""
    done, slot = [], None
    for a in args:
        if "=" not in a:
            slot = int(a, 0)
            if not 0 <= slot < SLOTS:
                raise ValueError("slot %d: slots are 0-%d" % (slot, SLOTS - 1))
            if pm.ids()[slot] < 0:
                raise ValueError("slot %d is empty" % slot)
            continue
        if slot is None:
            raise ValueError("%s: give a slot first" % a)
        name, text = a.split("=", 1)
        if name not in FIELD:
            raise ValueError("%s: no such field (pmplayer.py show lists them)" % name)
        f = FIELD[name]
        rec = pm.record(slot)
        old = get(rec, f)
        put(rec, f, parse_value(f, text))
        pm.set_record(slot, rec)
        done.append((slot, name, old, get(rec, f)))
    return done


def cmd_set(path, out, args, tables):
    pm = PmPlayer(open(path, "rb").read(), tables)
    for slot, name, old, new in apply_edits(pm, args):
        f = FIELD[name]
        print("slot %d %s: %s -> %s" % (slot, name, shown(f, old), shown(f, new)))
    with open(out, "wb") as fh:
        fh.write(pm.encode())
    print("wrote %s" % out)


def roundtrip(data, tables):
    """[problems] after re-encoding every field of every record."""
    pm = PmPlayer(data, tables)
    out = pm.problems()
    for s in range(SLOTS):
        rec = pm.record(s)
        values = [(f, get(rec, f)) for f in RECORD]
        blank = bytearray(rec)
        for f, _ in values:
            put(blank, f, "" if f[2] == "str" else 0)
        for f, v in values:
            put(blank, f, v)
        if blank != rec:
            out.append("slot %d differs at +%#x" % (s, next(i for i in range(RECORD_SIZE) if blank[i] != rec[i])))
        pm.set_record(s, blank)
    if pm.encode() != data:
        out.append("rebuilt file differs")
    return out


def cmd_roundtrip(paths, tables):
    n = bad = 0
    for path in files(paths):
        n += 1
        try:
            problems = roundtrip(open(path, "rb").read(), tables)
        except (ValueError, struct.error, OSError) as e:
            problems = [str(e)]
        bad += bool(problems)
        print("%s  %s" % (label(path), "!! " + "; ".join(problems) if problems else "ok"))
    print("%d files, %d differ" % (n, bad))


def cmd_selftest(tables):
    data = empty(tables)
    pm = PmPlayer(data, tables)
    print("empty file: CRC %#06x%s" % (pm.stored_crc(), "" if pm.stored_crc() == 0x27c
                                       else "  !! the Japanese card's empty file has 0x027c"))
    print("empty file round trip: %s" % ("; ".join("!! " + p for p in roundtrip(data, tables)) or "ok"))
    # A player made from scratch through the same edits `set` makes.
    struct.pack_into("<h", pm.plain, 0, 20001)
    edits = ["0", "name=T.Tester", "surname=Tester", "nation=38", "height=183.0",
             "weight=77", "leg=1", "position_group=3"]
    edits += ["%s=%d" % (name, 50 + i % 40) for i, name in enumerate(ABILITY_FIELDS)]
    edits += ["style_3=80", "style_2=60", "style_7=75", "skill_2=1", "tendency_0=4", "boots=5", "nerve=7"]
    apply_edits(pm, edits)
    data = pm.encode()
    again = PmPlayer(data, tables)
    rec = again.record(0)
    wrong = []
    for e in edits[1:]:
        name, text = e.split("=", 1)
        if get(rec, FIELD[name]) != parse_value(FIELD[name], text):
            wrong.append(name)
    print("one player: %d fields set, %d read back wrong%s, problems: %s" % (
        len(edits) - 1, len(wrong), "  !! " + ", ".join(wrong) if wrong else "",
        "; ".join(again.problems()) or "none"))
    print("one player round trip: %s" % ("; ".join("!! " + p for p in roundtrip(data, tables)) or "ok"))
    got = dict(imported(rec, tables))
    print("imported: name %s, nation %d, %d cm, %d kg, shirt %d, styles %s, skills %#x, nerve %d, WG %d" % (
        got["name"], got["nation"], got["height"], got["weight"], got["shirt"], got["style"],
        got["skills"], got["ability"][27], got["ability"][ABILITY_WG]))


EDIT_WORK = 0x12600             # block 1: the edit work (SLES 0x25d478)
EDIT_ID = 0x7cce                # the edit player's id in a career


def cmd_check(path, save_dir, tables):
    """Compare a career's edit work with what the import would make of
    the pmplayer.bin record with the same name."""
    pm = PmPlayer(open(path, "rb").read(), tables)
    sv = save.Save(save.Game(), save_dir)
    o = sv.at(1, EDIT_WORK)
    if struct.unpack_from("<h", sv.blocks, o)[0] != EDIT_ID:
        print("%s: no edit player in this career" % label(save_dir))
        return
    pb = sv.blocks[o + 4:o + 4 + 0xb4]
    name = bytes(pb[:0x14]).split(b"\0")[0].decode("cp850")
    ids = pm.ids()
    slot = next((s for s in range(SLOTS) if ids[s] >= 0
                 and get(pm.record(s), FIELD["name"]) == name), None)
    if slot is None:
        print("%s: the career's edit player %r isn't in %s  !!" % (label(save_dir), name, label(path)))
        return
    offs = {f[0]: f[1] for f in pbdata.PLAYER_FIELDS}
    same = bad = 0
    for field, want in imported(pm.record(slot), tables):
        if field == "name":
            got = name
        elif field == "castno":
            got = struct.unpack_from("<H", pb, offs[field])[0]
        elif field == "skills":
            got = struct.unpack_from("<H", pb, offs[field])[0]
        elif field == "style":
            got = list(pb[offs[field]:offs[field] + 5])
        elif field == "tendency":
            got = list(pb[offs[field]:offs[field] + 11])
        elif field == "ability":
            got = [pb[offs[field] + k] if want[k] is not None else None for k in range(64)]
        else:
            got = pb[offs[field]]
        if got == want:
            same += 1
        else:
            bad += 1
            print("  %-14s import gives %s, career holds %s  !!" % (field, want, got))
    work = bytes(sv.blocks[o + 0xb8:o + 0xb8 + WORK_LEN])
    rec_work = bytes(pm.record(slot)[WORK_OFF:WORK_OFF + WORK_LEN])
    if work != rec_work:
        bad += 1
        print("  edit work +0xb8 differs from record +%#x  !!" % WORK_OFF)
    else:
        same += 1
    print("%s: %s (slot %d of %s): %d fields agree, %d differ" % (
        label(save_dir), name, slot, label(path), same, bad))


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
    iso = _opt(args, "--iso", "ISO")
    if cmd not in ("info", "show", "set", "roundtrip", "selftest", "check"):
        print(__doc__)
        return 1
    tables = Tables(iso)
    if cmd == "info" and args:
        cmd_info(args, tables)
    elif cmd == "show" and args:
        cmd_show(args[0], [int(a, 0) for a in args[1:]], tables)
    elif cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:], tables)
    elif cmd == "roundtrip" and args:
        cmd_roundtrip(args, tables)
    elif cmd == "selftest" and not args:
        cmd_selftest(tables)
    elif cmd == "check" and len(args) == 2:
        cmd_check(args[0], args[1], tables)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
