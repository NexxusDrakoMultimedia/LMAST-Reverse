# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Club kit tables for Let's Make a Soccer Team! (PS2).

DAT/PLAYER/UNIFORM_LIST.TBB holds every club's home and away kits, 64 bits
packed per row (661 rows). DAT/PLAYER/COLOR_TBL.TBB is the 96 x 96 colour
clash table. The 116 licensed clubs (team ids 123-244) use real kit
textures from PLPACK_HOME/AWAY instead, each with an 18-byte descriptor.
See DOC/UNIFORM_FORMAT.md.

  row      team id - 3 (0x2d2bc8); the row's first s16 repeats the id and
           the lookup checks it (0x2d2bd8). Rows 0-539 are teams 3-542, the
           other 121 have id 0 and are never found.
  fields   unpacked by 0x2d2b68 into 76 halfwords (FIELDS below: bit
           position and width of each). Per side (home, away): 6 side
           fields, then an outfield kit and a goalkeeper kit of 15 fields.
  kit      Param::PlUnifOne, 15 bytes (UniformList_GetDataPlayer 0x2d3078):
           0 shirt design, 1-3 shirt colours, 4 collar, 5 shorts design,
           6-8 shorts colours, 9 socks design, 10-11 socks colours, 12
           shirt number colour, 13 shorts number colour, 14 captain mark.
           CUniformLoader::_load_edit (0x2c2848) loads the designs from
           EDIT_UNIFORM_{ORG,GK}_{SHT,PNT} and ORG_SOX and the colours from
           EDIT_UNIFORM_CLUT, and clamps them first: outfield shirt < 209,
           shorts < 61, keeper shirt and shorts < 38, socks < 18, colours
           10-13 < 96 (0x2c28dc-0x2c297c). Fields 4, 12, 13, 14 and side
           fields 3 (front number on) and 4 (shorts number: off, right,
           left) are named from the developer Uniform Viewer, which prints
           them for unlicensed clubs (TESTPRG.REL 0x15cb8-0x15f20).
  licensed _get_licence_no (0x2c24b0) looks the team up in {u32 team, u16
           licence} at 0x3a08d8: 116 clubs, licence n = PLPACK entry n.
           GetLicenceUniformInfo (0x2c4cc8) returns the 18-byte descriptor
           at 0x3a0c80 + (side * 116 + n) * 0x12, the same bytes as PLPACK
           block 0 (DESCRIPTOR below, byte pairs outfield/keeper, as the
           viewer prints them at TESTPRG.REL 0x157f0-0x15bf0).
  colours  96 palettes org_uni_A1 .. org_uni_L8 (12 letters x 8 shades);
           colour n is letter 'A' + n // 8, digit n % 8 + 1.
  clash    COLOR_TBL[a][b] (UniformList_CheckColor 0x2d3420).
           UniformList_GetUseUniformSide (0x2d3510) compares outfield
           shirt colour 1 of the two teams (PlUnif +0x1c, +0x40) to pick
           home or away kits.
  keeper   DAT/PLAYER/UNIFORM_GK.TBB builds the keeper kit of your club,
           the rival and the VS teams (ids 1, 2, 0x21f-0x22e) from their
           outfield kit (UniformList_GetGKUniformData 0x2d3608, called from
           CUniformBuilder::Init 0x2c4b68 and MatchBranch 0x113d2c).
           Table 0: 209 x 3 bytes, by outfield shirt design: keeper shirt
           < 38, shorts < 38, socks < 18. Table 1: 38 x 66 bytes, by keeper
           shirt design (x 0x42 at 0x2d3728): 6 colour schemes of 11 bytes,
           kit fields 1-3, 6-8, 10-14. The first scheme whose colour 1
           doesn't clash with your outfield shirt colour 1 (and in a match
           the opponent's outfield and keeper shirt colour 1) is used, if
           colours 1-13 are < 96 and the captain mark < 5 (0x2d3970).

`info` checks the row ids, every design and colour against its pack's size
(`!!` on a value the game would clamp), COLOR_TBL's shape, and the PLPACK
descriptors; given SLES_541.51 it also checks them against the
executable's copy. `licensed` lists the licensed clubs with their
descriptors (team ids need SLES_541.51, names MES.PAC).

`set` writes an edited copy of UNIFORM_LIST.TBB. A field is named
<side>.<part>.<n>: side home or away, part outfield or keeper (kit fields
0-14) or side (the 6 side fields 0-5); `flag` is the 3-bit field. Colours
may be given by name (I3, A8). Only the field's own bits change; the unused
bits between fields are kept. `roundtrip` re-packs every row from its
fields and marks any difference with `!!`.

`gk` lists UNIFORM_GK: which outfield shirt designs get each keeper design,
and its 6 schemes. `setgk` writes an edited copy. A field is named
outfield.<design>.<shirt|shorts|socks> (table 0) or keeper.<design>.
<scheme>.<n> (table 1; n a kit field 1-3, 6-8, 10-14). Values the game
would reject are refused. Both tables are plain bytes, so `tbb.py
roundtrip` covers re-writing the file.

Usage:
    python uniform.py info      <DAT/PLAYER> [SLES_541.51]   # check the tables
    python uniform.py show      <DAT/PLAYER> <team> ...      # a club's kits
    python uniform.py licensed  <DAT/PLAYER> [SLES_541.51]   # the 116 licensed kits
    python uniform.py clash     <DAT/PLAYER> <colour>        # colours that clash
    python uniform.py roundtrip <UNIFORM_LIST.TBB>
    python uniform.py set       <in.TBB> <out.TBB> <team> <field>=<value> ... [<team> ...]
        e.g. set UNIFORM_LIST.TBB out.TBB 3 home.outfield.1=A4 home.outfield.3=A4
    python uniform.py gk        <DAT/PLAYER> [keeper design ...]  # the keeper kit table
    python uniform.py setgk     <in.TBB> <out.TBB> <field>=<value> ...
        e.g. setgk UNIFORM_GK.TBB out.TBB outfield.0.shirt=20 keeper.35.0.1=A8
    python uniform.py setlicence <PLPACK_HOME.HED> <out.PAC> <licence> <field>=<value> ...
        e.g. setlicence PLPACK_HOME.HED out.PAC 0 outfield.backnumber=A8
        (edits the pack's copy of the descriptor only, not the executable's)
    python uniform.py setexe    <SLES_541.51> <out> <home|away> <licence> <field>=<value> ...
        (edits the executable's copy, which the Uniform Viewer draws the
        numbers from; patch it with patch_disc.py disc:SLES_541.51=<out>)
"""
import os
import struct
import sys

UNIFORM_LIST = "UNIFORM_LIST.TBB"
COLOR_TBL = "COLOR_TBL.TBB"
ROW_SIZE = 0x40
FIRST_TEAM = 3              # 0x2d2bc8: row = (id - 3) * 64

# (halfword offset in the unpacked record, bit position in the row, width),
# in the order of the unpacker at 0x2d2b68. Offset 0 is the s16 team id.
FIELDS = [
    (2, 16, 3), (4, 19, 2), (6, 21, 2), (8, 23, 5), (10, 28, 1), (12, 29, 2),
    (14, 32, 2), (16, 34, 1), (18, 35, 9), (20, 44, 7), (22, 51, 7), (24, 64, 7),
    (26, 71, 3), (28, 74, 8), (30, 82, 7), (32, 89, 7), (34, 96, 7), (36, 103, 8),
    (38, 111, 7), (40, 118, 7), (42, 128, 7), (44, 135, 7), (46, 142, 3),
    (48, 145, 9), (50, 160, 7), (52, 167, 7), (54, 174, 7), (56, 181, 3),
    (58, 184, 8), (60, 192, 7), (62, 199, 7), (64, 206, 7), (66, 213, 8),
    (68, 224, 7), (70, 231, 7), (72, 238, 7), (74, 245, 7), (76, 252, 3),
    (78, 256, 2), (80, 258, 2), (82, 260, 5), (84, 265, 1), (86, 266, 2),
    (88, 268, 2), (90, 270, 1), (92, 271, 9), (94, 280, 7), (96, 288, 7),
    (98, 295, 7), (100, 302, 3), (102, 305, 8), (104, 313, 7), (106, 320, 7),
    (108, 327, 7), (110, 334, 8), (112, 342, 7), (114, 352, 7), (116, 359, 7),
    (118, 366, 7), (120, 373, 3), (122, 384, 9), (124, 393, 7), (126, 400, 7),
    (128, 407, 7), (130, 416, 3), (132, 419, 8), (134, 427, 7), (136, 434, 7),
    (138, 441, 7), (140, 448, 8), (142, 456, 7), (144, 463, 7), (146, 470, 7),
    (148, 480, 7), (150, 487, 3)]

# Where each part starts in the unpacked record (halfword index). The
# readers copy home 2-7 / away 39-44 as the 6 side bytes and 9 / 46
# (outfield) and 24 / 61 (keeper) as 15-byte kits (0x2d3298, 0x2d3078).
SIDES = (("home", 2, 9, 24), ("away", 39, 46, 61))
KIT_LEN = 15
DESIGN_FIELDS = {0: "shirt", 5: "shorts", 9: "socks"}
COLOUR_FIELDS = (1, 2, 3, 6, 7, 8, 10, 11, 12, 13)
# _load_edit's clamps (0x2c28dc-0x2c297c): design limits per kit kind.
LIMITS = {"outfield": {0: 209, 5: 61, 9: 18}, "keeper": {0: 38, 5: 38, 9: 18}}
COLOURS = 96                # EDIT_UNIFORM_CLUT entries; socks colours clamp at 0x60


def colour_name(n):
    return "%s%d" % (chr(ord("A") + n // 8), n % 8 + 1) if 0 <= n < COLOURS else "?%d" % n


def table(path):
    """(rows, line size, data) of table 0 of a TBB1 file."""
    blob = open(path, "rb").read()
    off = struct.unpack_from("<I", blob, 0x10)[0]
    magic, doff, size, line = struct.unpack_from("<4sIII", blob, off)
    if magic != b"TBL1":
        raise ValueError("%s: table 0 is %r" % (path, magic))
    return size // line, line, blob[off + doff:off + doff + size]


def unpack(row):
    """The 76 halfwords of 0x2d2b68 as a list (index = halfword offset / 2)."""
    v = int.from_bytes(row, "little")
    out = [0] * 76
    out[0] = struct.unpack_from("<h", row)[0]
    for dst, pos, width in FIELDS:
        out[dst // 2] = (v >> pos) & ((1 << width) - 1)
    return out


POSITION = {dst // 2: (pos, width) for dst, pos, width in FIELDS}


def pack(row, fields):
    """Write fields (as from unpack) back into a copy of row, touching only
    each field's bits. The id is the row's first s16."""
    v = int.from_bytes(row, "little")
    for hw, (pos, width) in POSITION.items():
        mask = ((1 << width) - 1) << pos
        v = (v & ~mask) | ((fields[hw] << pos) & mask)
    out = bytearray(v.to_bytes(len(row), "little"))
    struct.pack_into("<h", out, 0, fields[0])
    return bytes(out)


def field_index(name):
    """Halfword index of a field named <side>.<part>.<n> or 'flag'."""
    if name == "flag":
        return 1
    side, part, n = name.split(".")
    starts = {s[0]: s[1:] for s in SIDES}
    if side not in starts:
        raise ValueError("side must be home or away: %r" % name)
    side_start, fp, gk = starts[side]
    n = int(n)
    base, count = {"side": (side_start, 6), "outfield": (fp, KIT_LEN),
                   "keeper": (gk, KIT_LEN)}.get(part, (None, 0))
    if base is None or not 0 <= n < count:
        raise ValueError("no field %r" % name)
    return base + n


def parse_value(text):
    if text[:1].isalpha():
        letter, digit = text[0].upper(), int(text[1:])
        if not ("A" <= letter <= "L" and 1 <= digit <= 8):
            raise ValueError("no colour %r" % text)
        return (ord(letter) - ord("A")) * 8 + digit - 1
    return int(text, 0)


def set_row_field(fields, name, value):
    """Set field `name` (<side>.<part>.<n> or flag) of an unpacked row
    (unpack's list) to `value`, which must fit the field's bits. Returns
    the old value."""
    hw = field_index(name)
    width = POSITION[hw][1]
    if not 0 <= value < (1 << width):
        raise ValueError("%s: %d doesn't fit in %d bits" % (name, value, width))
    old = fields[hw]
    fields[hw] = value
    return old


# What an editor (SRC/editor.py) offers for each field, narrower than its
# bits: the pack limits the loader clamps to (LIMITS, COLOURS), the
# collar's 3 bits (0-7 on the disc), captain marks 0-4 (the keeper table's
# check at 0x2d3a38; 0-4 on the disc), the front number on/off and the
# shorts number position (SHORTS_NUMBER). Fields with no name yet (side
# fields 0, 1, 2 and 5, the flag) are read-only.
def edit_range(name):
    """(low, high) an editor offers for a field named as `set` takes it,
    or None for a field with no name yet."""
    if name == "flag":
        return None
    side, part, n = name.split(".")
    n = int(n)
    if part == "side":
        return {3: (0, 1), 4: (0, len(SHORTS_NUMBER) - 1)}.get(n)
    if n in LIMITS[part]:
        return (0, LIMITS[part][n] - 1)
    if n in COLOUR_FIELDS:
        return (0, COLOURS - 1)
    if n == 4:
        return (0, 7)
    if n == 14:
        return (0, CAPTAIN_MARKS - 1)
    return None


KIT_FIELD_NAMES = ("shirt design", "shirt colour 1", "shirt colour 2", "shirt colour 3",
                   "collar", "shorts design", "shorts colour 1", "shorts colour 2",
                   "shorts colour 3", "socks design", "socks colour 1", "socks colour 2",
                   "shirt number colour", "shorts number colour", "captain mark")
SIDE_FIELD_NAMES = ("unknown 0", "unknown 1", "unknown 2", "front number", "shorts number",
                    "unknown 5")


# The hue of each colour letter, digits 1-7 light to dark and 8 a grey
# scale (empirical, from the palettes; DOC/UNIFORM_FORMAT.md#colours).
HUES = ("red", "orange", "yellow", "lime", "green", "sea green", "cyan", "sky blue",
        "blue", "purple", "magenta", "pink")


def colour_label(n):
    """A colour as an editor lists it: "A4 red 4", "A8 grey 1"."""
    if not 0 <= n < COLOURS:
        return str(n)
    letter, digit = n // 8, n % 8 + 1
    return "%s %s" % (colour_name(n), "grey %d" % (letter + 1) if digit == 8
                      else "%s %d" % (HUES[letter], digit))


def colour_swatches(dat):
    """[(r, g, b)] for the 96 colours: entry 128 of each EDIT_UNIFORM_CLUT
    palette, the main shade of its ramp (empirical: A1 light pink, A4 red,
    A8 white)."""
    import pac
    import svr
    path = os.path.join(dat, "EDIT_UNIFORM_CLUT.HED")
    h = pac.load_header(path)
    with open(pac.data_path(path, h), "rb") as f:
        buf = f.read()
    out = []
    for off, size, _, _ in h.entries[:COLOURS]:
        pal = svr.parse_svp(buf[off:off + size])
        out.append(svr._decode_colors(pal.data, pal.pf, pal.count)[128][:3])
    return out


class Team:
    def __init__(self, fields):
        self.id = fields[0]
        self.flag = fields[1]                       # 3 bits, meaning unknown
        self.sides = {}
        for name, side, fp, gk in SIDES:
            self.sides[name] = (fields[side:side + 6], fields[fp:fp + KIT_LEN],
                                fields[gk:gk + KIT_LEN])


def load(dat):
    rows, line, data = table(os.path.join(dat, UNIFORM_LIST))
    if line != ROW_SIZE:
        raise ValueError("%s: line size %d" % (UNIFORM_LIST, line))
    return [Team(unpack(data[i * line:(i + 1) * line])) for i in range(rows)]


def kit_problems(kind, kit):
    out = []
    for f, limit in LIMITS[kind].items():
        if kit[f] >= limit:
            out.append("%s design %d >= %d" % (DESIGN_FIELDS[f], kit[f], limit))
    for f in COLOUR_FIELDS:
        if kit[f] >= COLOURS:
            out.append("colour %d = %d >= %d" % (f, kit[f], COLOURS))
    return out


def fmt_kit(kind, kit):
    return ("shirt %3d %s/%s/%s  collar %d  shorts %2d %s/%s/%s  socks %2d %s/%s  "
            "numbers %s shorts %s  captain %d"
            % (kit[0], *(colour_name(kit[f]) for f in (1, 2, 3)), kit[4],
               kit[5], *(colour_name(kit[f]) for f in (6, 7, 8)),
               kit[9], *(colour_name(kit[f]) for f in (10, 11, 12, 13)), kit[14]))


SHORTS_NUMBER = ("off", "right", "left")        # TESTPRG.REL 0x23560


def fmt_side(s):
    number = SHORTS_NUMBER[s[4]] if s[4] < len(SHORTS_NUMBER) else "?%d" % s[4]
    return "front number %s  shorts number %s  unknown %d %d %d %d" % (
        "on" if s[3] else "off", number, s[0], s[1], s[2], s[5])


# --- licensed kits ---------------------------------------------------------------

PLPACK = ("PLPACK_HOME.HED", "PLPACK_AWAY.HED")
LICENCES = 116
LICENCE_TABLE = 0x3a08d8        # {u32 team, u16 licence, u16 pad}, ends at team 0
DESCRIPTOR_TABLE = 0x3a0c80     # (side * 116 + licence) * 0x12
DESCRIPTOR_SIZE = 0x12
NO_COLOUR = 0xff
COLLARS = 12                    # l_nml_bdy_01..11, l_tgt_bdy_01 (TESTPRG.REL 0x23570)
# (name, byte, kind): outfield at byte, keeper at byte + 1.
DESCRIPTOR = (("front number", 0, "colour"), ("back number", 2, "colour"),
              ("name type", 4, "int"), ("name colour", 6, "colour"),
              ("collar", 8, "collar"), ("shorts number", 10, "side"),
              ("shorts number colour", 12, "colour"), ("unknown", 14, "int"),
              ("captain mark", 16, "int"))


def licence_table(sles_path):
    """{team id: licence number} from the executable."""
    import sles_disasm
    elf = sles_disasm.Elf(sles_path)
    import gamever
    out, va = {}, gamever.at(sles_path, LICENCE_TABLE)
    while True:
        team, n = struct.unpack_from("<IH", elf.data, elf.v2f(va))
        if team == 0:
            return out, elf
        out[team] = n
        va += 8


def plpack_descriptors(dat):
    """[side][licence] -> (block-0 bytes, shirt texture name)."""
    import pac
    import packdata
    import svr
    out = []
    for name in PLPACK:
        path = os.path.join(dat, name)
        h = pac.load_header(path)
        side = []
        with open(pac.data_path(path, h), "rb") as f:
            for off, size, _, _ in h.entries:
                buf = packdata.read_entry(f, off, size)
                blocks = packdata.PackData(buf).blocks
                _, bsize, d = blocks[0]
                _, ssize, sd = blocks[2]
                side.append((buf[d:d + bsize], svr.parse_svm(buf[sd:sd + ssize])[0].name))
        out.append(side)
    return out


def descriptor_problems(desc):
    out = []
    if len(desc) < DESCRIPTOR_SIZE:
        return ["descriptor is %d bytes" % len(desc)]
    for name, b, kind in DESCRIPTOR:
        for v in desc[b:b + 2]:
            if kind == "colour" and v != NO_COLOUR and v >= COLOURS:
                out.append("%s colour %d" % (name, v))
            elif kind == "collar" and v >= COLLARS:
                out.append("collar %d" % v)
            elif kind == "side" and v >= len(SHORTS_NUMBER):
                out.append("shorts number position %d" % v)
    if any(desc[DESCRIPTOR_SIZE:]):
        out.append("non-zero bytes after 0x12")
    return out


def fmt_descriptor(desc):
    parts = []
    for name, b, kind in DESCRIPTOR:
        vals = []
        for v in desc[b:b + 2]:
            if kind == "colour":
                vals.append("off" if v == NO_COLOUR else colour_name(v))
            elif kind == "side":
                vals.append(SHORTS_NUMBER[v] if v < len(SHORTS_NUMBER) else "?%d" % v)
            else:
                vals.append(str(v))
        parts.append("%s %s" % (name, "/".join(vals)))
    return "  ".join(parts)


# --- keeper kits (UNIFORM_GK) ---------------------------------------------------

UNIFORM_GK = "UNIFORM_GK.TBB"
OUTFIELD_SHIRTS = 209           # table 0 rows; 0x2d379c: outfield shirt < 0xd1
GK_ROW = 3                      # keeper shirt, keeper shorts, socks
GK_ROW_FIELDS = (("shirt", 0, 38), ("shorts", 5, 38), ("socks", 9, 18))  # 0x2d37bc-0x2d37dc
GK_SHIRTS = 38                  # table 1 rows, indexed by keeper shirt (x 0x42, 0x2d3728)
SCHEMES = 6                     # the scheme search loops 6 times (0x2d3924)
SCHEME_SIZE = 11
SCHEME_FIELDS = (1, 2, 3, 6, 7, 8, 10, 11, 12, 13, 14)     # kit field of each byte
CAPTAIN_MARKS = 5               # 0x2d3a38: byte 10 < 5; bytes 0-9 < 0x60


def load_gk(path):
    """(table 0 bytes, table 1 bytes) of UNIFORM_GK.TBB, shapes checked."""
    import tbb
    _, tables = tbb.load(path)
    shapes = [(t.line_size, t.row_count) for t in tables]
    if shapes[:2] != [(GK_ROW, OUTFIELD_SHIRTS), (SCHEMES * SCHEME_SIZE, GK_SHIRTS)]:
        raise ValueError("%s: tables are %s" % (path, shapes))
    return tables[0], tables[1]


def scheme(t1, design, n):
    off = (design * SCHEMES + n) * SCHEME_SIZE
    return t1.data[off:off + SCHEME_SIZE]


def scheme_problems(s):
    out = ["colour %d = %d >= %d" % (f, v, COLOURS)
           for f, v in zip(SCHEME_FIELDS[:-1], s) if v >= COLOURS]
    if s[-1] >= CAPTAIN_MARKS:
        out.append("captain mark %d >= %d" % (s[-1], CAPTAIN_MARKS))
    return out


def fmt_scheme(s):
    c = [colour_name(v) for v in s[:-1]]
    return "shirt %s/%s/%s  shorts %s/%s/%s  socks %s/%s  numbers %s shorts %s  captain %d" % (
        *c, s[-1])


def check_gk(dat):
    path = os.path.join(dat, UNIFORM_GK)
    t0, t1 = load_gk(path)
    bad = 0
    for i in range(OUTFIELD_SHIRTS):
        row = t0.data[i * GK_ROW:(i + 1) * GK_ROW]
        p = ["%s %d >= %d" % (name, v, limit)
             for (name, _, limit), v in zip(GK_ROW_FIELDS, row) if v >= limit]
        if p:
            bad += 1
            print("  outfield shirt %d  !! %s" % (i, "; ".join(p)))
    used = sorted({t0.data[i * GK_ROW] for i in range(OUTFIELD_SHIRTS)})
    for d in range(GK_SHIRTS):
        for n in range(SCHEMES):
            p = scheme_problems(scheme(t1, d, n))
            if p:
                bad += 1
                print("  keeper design %d scheme %d  !! %s" % (d, n, "; ".join(p)))
    print("%s  %d outfield shirts -> %d keeper designs (%d-%d), %d x %d schemes, %d problems"
          % (UNIFORM_GK, OUTFIELD_SHIRTS, len(used), used[0], used[-1],
             GK_SHIRTS, SCHEMES, bad))


# --- commands ----------------------------------------------------------------

def cmd_info(dat, sles_path=None):
    teams = load(dat)
    used = [t for i, t in enumerate(teams) if t.id == i + FIRST_TEAM]
    unused = [i for i, t in enumerate(teams) if t.id == 0]
    other = [i for i, t in enumerate(teams) if t.id not in (0, i + FIRST_TEAM)]
    print("%s  %d rows: %d teams (ids %d-%d), %d rows with id 0 (never looked up)"
          % (UNIFORM_LIST, len(teams), len(used), used[0].id, used[-1].id, len(unused)))
    for i in other:
        print("  row %d  !! id %d, expected %d or 0" % (i, teams[i].id, i + FIRST_TEAM))
    bad = 0
    for i, t in enumerate(teams):
        if t.id == 0:
            continue
        for side, (_, fp, gk) in t.sides.items():
            for kind, kit in (("outfield", fp), ("keeper", gk)):
                p = kit_problems(kind, kit)
                if p:
                    bad += 1
                    print("  team %d %s %s  !! %s" % (t.id, side, kind, "; ".join(p)))
    print("  %d kits checked, %d with values the game clamps" % (4 * len(used), bad))

    rows, line, data = table(os.path.join(dat, COLOR_TBL))
    m = [data[i * line:(i + 1) * line] for i in range(rows)]
    problems = []
    if rows != COLOURS or line != COLOURS:
        problems.append("shape %d x %d" % (rows, line))
    if set(data) - {0, 1}:
        problems.append("values other than 0/1")
    if any(m[i][i] != 1 for i in range(min(rows, line))):
        problems.append("diagonal not all 1")
    if any(m[i][j] != m[j][i] for i in range(rows) for j in range(rows)):
        problems.append("not symmetric")
    print("%s  %d x %d clash table, %d clashing pairs%s"
          % (COLOR_TBL, rows, line, (sum(data) - rows) // 2,
             "  !! " + "; ".join(problems) if problems else ""))

    check_gk(dat)

    descs = plpack_descriptors(dat)
    exe = None
    if sles_path:
        licences, elf = licence_table(sles_path)
        import gamever
        base = elf.v2f(gamever.at(sles_path, DESCRIPTOR_TABLE))
        exe = elf.data[base:base + 2 * LICENCES * DESCRIPTOR_SIZE]
        numbers = sorted(licences.values())
        print("licence table  %d clubs (teams %d-%d)%s" % (
            len(licences), min(licences), max(licences),
            "" if numbers == list(range(LICENCES)) else "  !! licence numbers aren't 0-%d" % (LICENCES - 1)))
    for s, name in enumerate(PLPACK):
        bad = differ = 0
        if len(descs[s]) != LICENCES:
            print("%s  !! %d entries, expected %d" % (name, len(descs[s]), LICENCES))
        for n, (desc, tex) in enumerate(descs[s]):
            p = descriptor_problems(desc)
            if exe is not None:
                i = (s * LICENCES + n) * DESCRIPTOR_SIZE
                if desc[:DESCRIPTOR_SIZE] != exe[i:i + DESCRIPTOR_SIZE]:
                    differ += 1
                    p.append("differs from the executable's copy")
            if p:
                bad += 1
                print("  %s #%d %s  !! %s" % (name, n, tex, "; ".join(p)))
        note = "" if exe is None else "; %d differ from the executable's copy" % differ
        print("%s  %d kit descriptors, %d with problems%s" % (name, len(descs[s]), bad, note))


def cmd_show(dat, ids):
    teams = {t.id: t for t in load(dat) if t.id}
    for tid in ids:
        t = teams.get(tid)
        if t is None:
            raise ValueError("no kit row for team %d" % tid)
        print("team %d  flag=%d" % (t.id, t.flag))
        for side, (sfields, fp, gk) in t.sides.items():
            print("  %s  %s" % (side, fmt_side(sfields)))
            print("    outfield  " + fmt_kit("outfield", fp))
            print("    keeper    " + fmt_kit("keeper", gk))


def cmd_licensed(dat, sles_path=None):
    import initteam
    descs = plpack_descriptors(dat)
    team_of, names = {}, {}
    if sles_path:
        team_of = {n: t for t, n in licence_table(sles_path)[0].items()}
        names = initteam.team_names(os.path.join(os.path.dirname(os.path.abspath(dat)),
                                                 "MESSAGE", "MES.PAC"), 1)
    for n in range(len(descs[0])):
        team = team_of.get(n)
        who = initteam.label(names, team) if team is not None else "   ?"
        tex = descs[0][n][1].rsplit("_", 2)[0]
        print("%3d  %-28s %s" % (n, who, tex))
        for s, side in enumerate(("home", "away")):
            print("       %s  %s" % (side, fmt_descriptor(descs[s][n][0])))


def apply_descriptor_edits(data, base, label, edits):
    """Apply <outfield|keeper>.<name>=<value> edits to the descriptor at
    data[base:]. Names are DESCRIPTOR's without spaces (outfield.backnumber)."""
    names = {name.replace(" ", ""): (b, kind) for name, b, kind in DESCRIPTOR}
    for edit in edits:
        field, _, text = edit.partition("=")
        part, _, name = field.partition(".")
        if part not in ("outfield", "keeper") or name not in names:
            raise ValueError("no descriptor field %r (fields: %s)" % (field, ", ".join(names)))
        b = names[name][0] + (part == "keeper")
        value = NO_COLOUR if text.lower() == "off" else parse_value(text)
        if not 0 <= value <= 0xff:
            raise ValueError("%s: %d doesn't fit in a byte" % (field, value))
        print("%s %s: %d -> %d" % (label, field, data[base + b], value))
        data[base + b] = value


def cmd_setlicence(header, dst, licence, edits):
    """Edit one PLPACK entry's descriptor (block 0) in a copy of the pack's
    data file."""
    import pac
    import packdata
    h = pac.load_header(header)
    data = bytearray(open(pac.data_path(header, h), "rb").read())
    off, size, _, _ = h.entries[licence]
    if data[off:off + 4] == pac.PRSH_MAGIC:
        raise ValueError("entry %d is compressed; only raw entries can be edited" % licence)
    _, _, d = packdata.PackData(bytes(data[off:off + size])).blocks[0]
    apply_descriptor_edits(data, off + d, "licence %d pack" % licence, edits)
    with open(dst, "wb") as f:
        f.write(data)


def cmd_setexe(sles_path, dst, side, licence, edits):
    """Edit the executable's copy of a descriptor (0x3a0c80) in a copy of
    SLES_541.51."""
    import sles_disasm
    if side not in ("home", "away") or not 0 <= licence < LICENCES:
        raise ValueError("side must be home or away and licence 0-%d" % (LICENCES - 1))
    elf = sles_disasm.Elf(sles_path)
    data = bytearray(elf.data)
    import gamever
    base = elf.v2f(gamever.at(sles_path, DESCRIPTOR_TABLE)) + ((side == "away") * LICENCES + licence) * DESCRIPTOR_SIZE
    apply_descriptor_edits(data, base, "licence %d %s executable" % (licence, side), edits)
    with open(dst, "wb") as f:
        f.write(data)


def cmd_clash(dat, colour):
    rows, line, data = table(os.path.join(dat, COLOR_TBL))
    n = int(colour) if colour.isdigit() else (ord(colour[0].upper()) - ord("A")) * 8 + int(colour[1:]) - 1
    row = data[n * line:(n + 1) * line]
    print("%s (%d) clashes with: %s" % (colour_name(n), n,
          " ".join(colour_name(j) for j in range(line) if row[j] and j != n)))


def rows_of(path):
    blob = open(path, "rb").read()
    off = struct.unpack_from("<I", blob, 0x10)[0]
    _, doff, size, line = struct.unpack_from("<4sIII", blob, off)
    if line != ROW_SIZE:
        raise ValueError("%s: line size %d" % (path, line))
    return blob, off + doff, size // line


def cmd_roundtrip(path):
    blob, base, n = rows_of(path)
    bad = 0
    for i in range(n):
        row = blob[base + i * ROW_SIZE:base + (i + 1) * ROW_SIZE]
        if pack(row, unpack(row)) != row:
            bad += 1
            print("row %d  !! re-packs differently" % i)
    print("%d/%d rows re-pack byte for byte" % (n - bad, n))


def cmd_set(src, dst, args):
    """Edit rows of UNIFORM_LIST: <team> <field>=<value> ... [<team> ...]."""
    blob, base, n = rows_of(src)
    out = bytearray(blob)
    team = fields = row = None
    edited = {}
    for a in args:
        if "=" not in a:
            team = int(a, 0)
            i = team - FIRST_TEAM
            if not 0 <= i < n:
                raise ValueError("no row for team %d" % team)
            row = bytes(blob[base + i * ROW_SIZE:base + (i + 1) * ROW_SIZE])
            fields = edited.get(team) or unpack(row)
            if fields[0] != team:
                raise ValueError("row %d holds team %d, not %d" % (i, fields[0], team))
            edited[team] = fields
            continue
        if fields is None:
            raise ValueError("give a team id before %r" % a)
        name, _, text = a.partition("=")
        value = parse_value(text)
        old = set_row_field(fields, name, value)
        print("team %d %s: %d -> %d" % (team, name, old, value))
    for team, fields in edited.items():
        i = team - FIRST_TEAM
        row = bytes(blob[base + i * ROW_SIZE:base + (i + 1) * ROW_SIZE])
        out[base + i * ROW_SIZE:base + (i + 1) * ROW_SIZE] = pack(row, fields)
    with open(dst, "wb") as f:
        f.write(out)


def cmd_gk(dat, designs):
    t0, t1 = load_gk(os.path.join(dat, UNIFORM_GK))
    by_design = {}
    for i in range(OUTFIELD_SHIRTS):
        by_design.setdefault(tuple(t0.data[i * GK_ROW:(i + 1) * GK_ROW]), []).append(i)
    for d in designs or range(GK_SHIRTS):
        rows = [(k, v) for k, v in sorted(by_design.items()) if k[0] == d]
        if not rows and not designs:
            continue                # never chosen (designs 0-19 are all zero)
        print("keeper design %d" % d)
        for (shirt, shorts, socks), outfield in rows:
            print("  shorts %d socks %d  for outfield shirts %s"
                  % (shorts, socks, " ".join(map(str, outfield))))
        if not rows:
            print("  not used by any outfield shirt")
        for n in range(SCHEMES):
            print("  scheme %d  %s" % (n, fmt_scheme(scheme(t1, d, n))))


GK_ROW_INDEX = {name: (k, limit) for k, (name, _, limit) in enumerate(GK_ROW_FIELDS)}


def gk_offset(t0, t1, name):
    """(file offset, limit) of a UNIFORM_GK byte named outfield.<design>.
    <shirt|shorts|socks> or keeper.<design>.<scheme>.<field>."""
    parts = name.split(".")
    if parts[0] == "outfield" and len(parts) == 3 and parts[2] in GK_ROW_INDEX:
        i = int(parts[1], 0)
        k, limit = GK_ROW_INDEX[parts[2]]
        if not 0 <= i < OUTFIELD_SHIRTS:
            raise ValueError("%s: outfield shirt designs are 0-%d" % (name, OUTFIELD_SHIRTS - 1))
        return t0.offset + t0.data_offset + i * GK_ROW + k, limit
    if parts[0] == "keeper" and len(parts) == 4:
        d, n, f = (int(p, 0) for p in parts[1:])
        if not (0 <= d < GK_SHIRTS and 0 <= n < SCHEMES and f in SCHEME_FIELDS):
            raise ValueError("%s: keeper designs are 0-%d, schemes 0-%d, fields %s"
                             % (name, GK_SHIRTS - 1, SCHEMES - 1,
                                ",".join(map(str, SCHEME_FIELDS))))
        limit = CAPTAIN_MARKS if f == 14 else COLOURS
        return (t1.offset + t1.data_offset + (d * SCHEMES + n) * SCHEME_SIZE
                + SCHEME_FIELDS.index(f)), limit
    raise ValueError("no field %r (outfield.<design>.<shirt|shorts|socks> "
                     "or keeper.<design>.<scheme>.<field>)" % name)


def apply_gk_edit(blob, t0, t1, name, value):
    """Set one UNIFORM_GK byte in `blob` (a bytearray of the file).
    Returns the old value."""
    off, limit = gk_offset(t0, t1, name)
    # 0x2d37bc-0x2d37dc and 0x2d3970-0x2d3a38 drop the whole kit or
    # scheme on a value past these limits, so refuse it here.
    if not 0 <= value < limit:
        raise ValueError("%s: %d is out of range (the game accepts 0-%d)"
                         % (name, value, limit - 1))
    old = blob[off]
    blob[off] = value
    return old


def check_gk_blob(blob, original, t0, t1):
    """Raise ValueError if an edited UNIFORM_GK differs from `original`
    anywhere outside its two tables."""
    import tbb
    new = tbb.parse(bytes(blob))[1]
    outside = bytearray(blob)
    for t in (t0, t1):
        start = t.offset + t.data_offset
        outside[start:start + len(t.data)] = t.data
    if outside != original or [t.data for t in new[2:]]:
        raise ValueError("edit reached outside UNIFORM_GK's two tables")


def cmd_setgk(src, dst, edits):
    original = open(src, "rb").read()
    blob = bytearray(original)
    t0, t1 = load_gk(src)
    for edit in edits:
        name, _, text = edit.partition("=")
        value = parse_value(text)
        old = apply_gk_edit(blob, t0, t1, name, value)
        print("%s: %d -> %d" % (name, old, value))
    # Read the result back: only bytes inside the two tables may differ.
    check_gk_blob(blob, original, t0, t1)
    with open(dst, "wb") as f:
        f.write(blob)


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    elif cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "info" and len(args) in (1, 2):
        cmd_info(*args)
    elif cmd == "licensed" and len(args) in (1, 2):
        cmd_licensed(*args)
    elif cmd == "setlicence" and len(args) >= 4:
        cmd_setlicence(args[0], args[1], int(args[2], 0), args[3:])
    elif cmd == "setexe" and len(args) >= 5:
        cmd_setexe(args[0], args[1], args[2], int(args[3], 0), args[4:])
    elif cmd == "show" and len(args) >= 2:
        cmd_show(args[0], [int(a, 0) for a in args[1:]])
    elif cmd == "gk" and len(args) >= 1:
        cmd_gk(args[0], [int(a, 0) for a in args[1:]])
    elif cmd == "setgk" and len(args) >= 3:
        cmd_setgk(args[0], args[1], args[2:])
    elif cmd == "clash" and len(args) == 2:
        cmd_clash(args[0], args[1])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
