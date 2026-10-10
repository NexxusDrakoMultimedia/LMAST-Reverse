# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Training camps: PARAM/CAMP_LIST.TBB and PARAM/CAMP_EXPLANE.TBB, for
Let's Make a Soccer Team! (PS2).

CAMP_LIST table 0 holds one 14-byte record per camp city (153); the camp
screen's module (SIMPRG.REL, load list 0x1cdd30) finds a city's record by
+0x04 (0x4bdd0; 0x4c288 and 0x4c4e0 walk the records) and the training
module loads the file too during a camp (list 0x23d618). See
DOC/CAMP_FORMAT.md.

  +0x00 u16 region   the nation's display region (empirical, all 153)
  +0x02 u16 nation   PlNati (empirical)
  +0x04 u16 city     the key every getter compares
  +0x06 u16 level    0-7: a camp is open once the club's popularity in
                     the camp's region reaches the level's threshold
                     (0x459a8: table at 0x1cdd20, 0 for levels 0-3, then
                     28,800, 36,000, 43,200, 50,400)
  +0x08 u16 event_only  1: hidden until an event frees it
                     (pwkSche_CheckCampFree; 0x4c65c)
  +0x0a u16          0 or 1; only an uncalled getter (0x4bfd0) reads it
  +0x0c u16 type     the camp type, 1-87 on the disc. 0x4bdd0 returns its
                     low byte and the booking (0xa5558) stores it in the
                     camp's +0x3c, which TRAINING_LIST table 10 (its row)
                     and the theme table at SLES 0x552cd0 read as 0-86:
                     every camp gets the next type's training and themes,
                     and type 87 reads past both tables. `fixtypes` lowers
                     every type by one.

The camp cities are numbered as in the Japanese release. PAL renumbered
the English cities (and moved the clubs with them: Liverpool's clubs are
in city 63 in the Japanese club records, 66 in PAL), but not the camp
tables, so seven English camps sit in a neighbouring town (63 is
Scunthorpe in PAL, Liverpool in the Japanese release). `fixcities` moves
them to the PAL ids in both files (CITY_FIXES).

CAMP_LIST table 1 is (u16 city, u16 club) pairs: the clubs of each camp's
area (empirical). CAMP_EXPLANE is (u16 city, u16 message) pairs: the
city's description, message category 570.

Usage:
    python camp.py info      <DAT/PARAM>
    python camp.py show      <DAT/PARAM> [city ...]
    python camp.py set       <in CAMP_LIST.TBB> <out.TBB> <city> <field>=<value> ... [<city> ...]
    python camp.py fixtypes  <in CAMP_LIST.TBB> <out.TBB>
    python camp.py fixcities <in DAT/PARAM> <out folder>
    python camp.py roundtrip <CAMP_LIST.TBB>

`set` edits the record fields by name (region, nation, level, event_only,
unk0a, type). A same-size file goes on the disc with patch_disc.py;
`patch_disc.py --mod camp-types` and `--mod camp-cities` apply
`fixtypes` and `fixcities` to a disc.
"""
import os
import struct
import sys

import tbb

LIST_FILE = "CAMP_LIST.TBB"
EXPLANE_FILE = "CAMP_EXPLANE.TBB"
RECORD = 0xe                    # 0x4be34: + 0xe per record; 0x4be24: end at + 0x85e
FIELDS = ("region", "nation", "city", "level", "event_only", "unk0a", "type")
LEVEL_POPULARITY = (0, 0, 0, 0, 28800, 36000, 43200, 50400)   # SIMPRG.REL 0x1cdd20
CAMP_TYPES = 87                 # TRAINING_LIST table 10 rows; SLES 0x256980: type < 0x57
CAMP_MESSAGES = 570             # the category CAMP_EXPLANE's ids are in (empirical)
CITY_NAMES = 961                # city names (initteam.CITY_CATEGORY)

# (Japanese city id, PAL city id) of the camps PAL left behind: the
# Japanese release's English city names (message category 961) at the old
# id equal the PAL names at the new one, and the Japanese and PAL club
# records put those towns' clubs there (Liverpool 63 -> 66, Manchester
# 38 -> 40, Birmingham 88 -> 89, Southampton 44 -> 46).
CITY_FIXES = ((63, 66),     # Liverpool (Scunthorpe in PAL)
              (38, 40),     # Manchester (West London)
              (85, 86),     # Newcastle (Gateshead)
              (88, 89),     # Birmingham (Warwick)
              (44, 46),     # Southampton (Basingstoke)
              (51, 54),     # Blackburn (Newport)
              (74, 78))     # Sheffield (Oakham)


class Camp:
    def __init__(self, index, data):
        self.index = index
        self.values = list(struct.unpack("<7H", data))

    def __getitem__(self, name):
        return self.values[FIELDS.index(name)]

    def __setitem__(self, name, value):
        self.values[FIELDS.index(name)] = value

    def encode(self):
        return struct.pack("<7H", *self.values)


def pairs(data):
    return [struct.unpack_from("<2H", data, i) for i in range(0, len(data) - 3, 4)]


def load_list(path):
    if os.path.isdir(path):
        path = os.path.join(path, LIST_FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, raw = tbb.parse(buf)
    if len(raw) != 2:
        raise ValueError("%d tables, expected 2" % len(raw))
    if len(raw[0].data) % RECORD:
        raise ValueError("table 0 is %d bytes, not a whole number of %d-byte records"
                         % (len(raw[0].data), RECORD))
    camps = [Camp(i, raw[0].data[o:o + RECORD]) for i, o in
             enumerate(range(0, len(raw[0].data), RECORD))]
    return buf, end, raw, camps


def load_explane(path):
    if os.path.isdir(path):
        path = os.path.join(path, EXPLANE_FILE)
    with open(path, "rb") as f:
        buf = f.read()
    _, raw = tbb.parse(buf)
    return pairs(raw[0].data)


def messages(mes_path, category, lang=1):
    """{id: text} of one message file in MES.PAC, read on its own (the
    editor needs only the city names and the camps' descriptions)."""
    import mbb
    from pac import BinPac
    with open(mes_path, "rb") as f:
        buf = f.read()
    for off, size, name, _ in BinPac(buf).entries:
        if name == "%d_%d.mbb" % (category, lang):
            m = mbb.Mbb(buf[off:off + size], name)
            return {rid: mbb.decode(s, lang) for rid, s in m.records}
    return {}


# What an editor offers: only the camp type, whose readers are known; the
# rest is shown. The camp list numbers the types 1-87 (one too many for
# the game's tables, which the camp-types fix lowers), so 0-87 covers both.
EDIT_RANGES = {"type": (0, CAMP_TYPES), "level": (0, len(LEVEL_POPULARITY) - 1),
               "event_only": (0, 1)}

DESCRIPTIONS = {
    "region": "the nation's display region",
    "nation": "the camp's nation",
    "city": "the camp's town; the key",
    "level": "popularity the club needs in the camp's region: 0-3 none, "
             "4-7 28,800 / 36,000 / 43,200 / 50,400",
    "event_only": "1: hidden until an event frees the camp",
    "unk0a": "0 or 1; nothing reads it",
    "type": "the camp type: picks the training (TRAINING_LIST table 10) and the "
            "themes it is judged by",
}


def edit_range(name):
    """(low, high) an editor offers for a field, or None for one it shows."""
    return EDIT_RANGES.get(name)


def training_row(type_value, fixed):
    """The TRAINING_LIST table 10 row a camp of this type trains with: the
    type itself as the retail game reads it, one lower with the camp-types
    fix; None past the table."""
    row = type_value - 1 if fixed else type_value
    return row if 0 <= row < CAMP_TYPES else None


def check(camps):
    problems = []
    cities = [c["city"] for c in camps]
    if len(set(cities)) != len(cities):
        problems.append("a city has more than one record")
    for c in camps:
        if c["type"] > 0xff:
            problems.append("city %d: type %d (only the low byte is read)" % (c["city"], c["type"]))
    return problems


def type_range(camps):
    types = [c["type"] for c in camps]
    return min(types), max(types)


def fixed(camps):
    """The records with every type lowered by one, or None when the types
    already start at 0 (fixed before)."""
    lo, _ = type_range(camps)
    if lo == 0:
        return None
    out = [Camp(c.index, c.encode()) for c in camps]
    for c in out:
        c["type"] -= 1
    return out


def encode_file(buf, end, raw, camps):
    problems = check(camps)
    if problems:
        raise ValueError("; ".join(problems))
    raw[0].data = b"".join(c.encode() for c in camps)
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


def fix_types(data):
    """CAMP_LIST.TBB bytes with the camp types lowered by one, or None when
    they already start at 0. patch_disc.py's camp-types switch."""
    end, raw = tbb.parse(data)
    camps = [Camp(i, raw[0].data[o:o + RECORD]) for i, o in
             enumerate(range(0, len(raw[0].data), RECORD))]
    new = fixed(camps)
    if new is None:
        return None
    return encode_file(data, end, raw, new)


def _moves(cities):
    """CITY_FIXES that apply to a set of city ids: {old: new}. Refuses a new
    id that is already one of them."""
    moves = {old: new for old, new in CITY_FIXES if old in cities}
    clash = cities & set(moves.values())
    if moves and clash:
        raise ValueError("cities %s are already camps" % sorted(clash))
    return moves


def _move_pairs(data, moves):
    """{u16 city, u16 x} pairs with their cities moved."""
    out = bytearray(data)
    for i in range(0, len(out) - 3, 4):
        city = struct.unpack_from("<H", out, i)[0]
        struct.pack_into("<H", out, i, moves.get(city, city))
    return bytes(out)


def fix_cities_list(data):
    """CAMP_LIST.TBB bytes with the CITY_FIXES camps moved to their PAL
    ids (records and the clubs table), or None when none is on an old id."""
    end, raw = tbb.parse(data)
    camps = [Camp(i, raw[0].data[o:o + RECORD]) for i, o in
             enumerate(range(0, len(raw[0].data), RECORD))]
    moves = _moves({c["city"] for c in camps})
    if not moves:
        return None
    for c in camps:
        c["city"] = moves.get(c["city"], c["city"])
    raw[1].data = _move_pairs(raw[1].data, moves)
    return encode_file(data, end, raw, camps)


def fix_cities_explane(data):
    """CAMP_EXPLANE.TBB bytes with the CITY_FIXES cities moved, or None."""
    end, raw = tbb.parse(data)
    moves = _moves({c for c, _ in pairs(raw[0].data)})
    if not moves:
        return None
    raw[0].data = _move_pairs(raw[0].data, moves)
    out = tbb.build(raw, end, tbb.trailer(data, raw))
    if len(out) != len(data):
        raise ValueError("rebuilt %s is %d bytes, not %d" % (EXPLANE_FILE, len(out), len(data)))
    return out


def fix_cities(list_data, explane_data):
    """(CAMP_LIST.TBB, CAMP_EXPLANE.TBB) bytes with the CITY_FIXES cities
    moved to their PAL ids, or None when neither file has an old id; a
    file already fixed comes back unchanged."""
    a, b = fix_cities_list(list_data), fix_cities_explane(explane_data)
    if a is None and b is None:
        return None
    return a or list_data, b or explane_data


# --- commands ----------------------------------------------------------------

def cmd_info(root):
    try:
        _, _, raw, camps = load_list(root)
        explane = load_explane(root)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (root, e))
        return
    line = "%s: %d camps of %d bytes" % (LIST_FILE, len(camps), RECORD)
    problems = check(camps)
    if problems:
        line += "  !! " + "; ".join(problems)
    print(line)
    lo, hi = type_range(camps)
    print("  types %d-%d, %d different%s" % (
        lo, hi, len(set(c["type"] for c in camps)),
        " (1-based: the game reads them as 0-%d, see fixtypes)" % (CAMP_TYPES - 1)
        if lo == 1 else ""))
    if hi > CAMP_TYPES:
        print("  !! a type above %d" % CAMP_TYPES)
    for name in ("region", "level", "event_only", "unk0a"):
        print("  %-6s %s" % (name, " ".join(map(str, sorted(set(c[name] for c in camps))))))
    clubs = pairs(raw[1].data)
    cities = set(c["city"] for c in camps)
    print("%s table 1: %d (city, club) pairs, %d cities%s" % (
        LIST_FILE, len(clubs), len(set(c for c, _ in clubs)),
        "" if set(c for c, _ in clubs) == cities else "  !! cities differ from table 0"))
    print("%s: %d (city, message) pairs, messages %d-%d%s" % (
        EXPLANE_FILE, len(explane), min(m for _, m in explane), max(m for _, m in explane),
        "" if set(c for c, _ in explane) == cities else "  !! cities %s aren't camps, camps %s have none"
        % (sorted(set(c for c, _ in explane) - cities), sorted(cities - set(c for c, _ in explane)))))


def cmd_show(root, cities):
    _, _, raw, camps = load_list(root)
    clubs = pairs(raw[1].data)
    explane = dict(load_explane(root))
    for c in camps:
        if cities and c["city"] not in cities:
            continue
        print("city %3d  nation %3d  region %2d  type %2d  level %d  event only %d  +a %d  "
              "message %s  clubs %s" % (
            c["city"], c["nation"], c["region"], c["type"], c["level"], c["event_only"],
            c["unk0a"], explane.get(c["city"], "-"),
            " ".join(str(t) for city, t in clubs if city == c["city"])))


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw, camps = load_list(path)
    by_city = {c["city"]: c for c in camps}
    target = None
    for a in args:
        if "=" not in a:
            city = int(a, 0)
            if city not in by_city:
                raise SystemExit("%s: no camp in city %d" % (path, city))
            target = by_city[city]
            continue
        if target is None:
            raise SystemExit("give a city before %r" % a)
        name, value = a.split("=", 1)
        if name not in FIELDS or name == "city":
            raise SystemExit("no field %r; fields are %s" % (
                name, ", ".join(f for f in FIELDS if f != "city")))
        value = int(value, 0)
        hi = 0xff if name == "type" else 0xffff
        if not 0 <= value <= hi:
            raise SystemExit("%s must be 0-%d" % (name, hi))
        old = target[name]
        target[name] = value
        print("city %d %s: %d -> %d" % (target["city"], name, old, value))
    try:
        out = encode_file(buf, end, raw, camps)
    except ValueError as e:
        raise SystemExit(str(e))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_fixtypes(path, out_path):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(path, "rb") as f:
        data = f.read()
    out = fix_types(data)
    if out is None:
        raise SystemExit("%s: the types already start at 0" % path)
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s (types lowered by one)" % out_path)


def cmd_fixcities(root, out):
    if os.path.abspath(out) == os.path.abspath(root):
        raise SystemExit("refusing to write into the input folder; give another one")
    data = []
    for name in (LIST_FILE, EXPLANE_FILE):
        with open(os.path.join(root, name), "rb") as f:
            data.append(f.read())
    try:
        new = fix_cities(*data)
    except ValueError as e:
        raise SystemExit(str(e))
    if new is None:
        raise SystemExit("%s: no camp uses an old city id" % root)
    os.makedirs(out, exist_ok=True)
    for name, d in zip((LIST_FILE, EXPLANE_FILE), new):
        with open(os.path.join(out, name), "wb") as f:
            f.write(d)
        print("wrote %s" % os.path.join(out, name))


def cmd_roundtrip(path):
    buf, end, raw, camps = load_list(path)
    same = b"".join(c.encode() for c in camps) == raw[0].data
    print("%d camps  %s" % (len(camps), "identical" if same else "!! re-encoded table differs"))
    try:
        out = encode_file(buf, end, raw, camps)
    except ValueError as e:
        out = None
        print("%s: !! %s" % (path, e))
    if out is not None:
        print("%s: %s" % (path, "rebuilt file identical" if out == buf else "!! rebuilt file differs"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and args:
        cmd_show(args[0], [int(a, 0) for a in args[1:]])
    elif cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "fixtypes" and len(args) == 2:
        cmd_fixtypes(args[0], args[1])
    elif cmd == "fixcities" and len(args) == 2:
        cmd_fixcities(args[0], args[1])
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
