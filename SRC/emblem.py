# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""DAT/EMBLEM checker for Let's Make a Soccer Team! (PS2).

DAT/EMBLEM (folder id 8) holds the club editor's crest and flag parts, its
colour palette, and the player-editor tables. See DOC/EMBLEM_DIR.md.

  COLOR_TABLE.TBB     EDIT::CColor (SLES 0x2b9998-0x2b9cdc): table 0 is 96
                      colours (u32, R in the top byte), tables 1-6 map
                      between the 96-, 32- and 16-colour palettes.
  EDIT_EMBLEM.TBB     EDIT::CEmblemData (SIMPRG.REL 0x1039f0-0x104310):
                      t0 masks (12 bytes), t1 mask groups {u16 first, u16
                      count}, t2 patterns, t3 accessories (u32 each), t4-t6
                      presets {u16 part, Trs} for the base, the area
                      patterns and the area accessories, t7-t9 sample /
                      initial / rival crests (Param::PlEmblemPreset, 110
                      bytes, unpacked by CEmblemData::Initialize 0x103a50),
                      t10 the sample of each initial crest, t11 three
                      colour ids per initial crest, t12-t143 layer
                      accessories {u16 key, u16 accessory, Trs}, table 12 +
                      4 * sample + layer.
  EDIT_EMBLEM_A/M/P   217 accessories, 214 masks, 22 patterns: 128x128 4bpp
                      SVRs, loaded one entry at a time (SIMPRG 0x107380).
  EDIT_FLAG.*         EDIT::CFlagData (0x104578-0x1045e8): t0 49 flag bases
                      (u32), t1 71 patterns {u8 base, u8 rev}, t2 27 crest
                      placements {pos_x, pos_y, size_x, size_y}
                      (CFlagData::Initialize 0x1044b0); the pack holds
                      the 49 bases.
  EDIT_PLAYER.TBB     32 tables, loaded by PLAYEREDIT_MODULE (YRSTPRG.REL),
                      one accessor per table at 0x1cc70-0x1d418; not
                      decoded.

`info` checks the layouts and the counts the tables and packs share.
`colors` lists the 96 colours with their 32- and 16-colour ids.
`crests` prints the sample, initial and rival crests field by field.
`set` edits EDIT_EMBLEM.TBB or EDIT_FLAG.TBB field by field into a new
file of the same size; `roundtrip` re-encodes every record of both.

Usage:
    python emblem.py info      <DAT/EMBLEM>
    python emblem.py colors    <DAT/EMBLEM>
    python emblem.py crests    <DAT/EMBLEM> [7|8|9]
    python emblem.py set       <in.TBB> <out.TBB> <target>=<value> ...
    python emblem.py roundtrip <DAT/EMBLEM | file.TBB> ...

`set` targets in EDIT_EMBLEM.TBB:
    crest:<table>:<row>:<field>[.<n>]    table 7 samples, 8 starting, 9 rival;
        fields id, sample, base, mask, pattern.<area>, acce.<area>,
        layer_key.<layer>, pattern_color.<area*2+n>, acce_color.<area*3+n>,
        layer_color.<layer*3+n>; colours are 0-31, or -1/-2/-3 for the
        club's first, second and third colour
    preset:<table>:<row>:<field>         table 4 bases, 5 area patterns,
        6 area accessories; fields part, tx, ty, rot, rev, sx, sy
    layer:<sample>:<layer>:<record>:<field>   fields key, acce (65535:
        empty), tx, ty, rot, rev, sx, sy
    start:<row>:<field>                  starting crest's sample (t10),
        color1, color2 (t11)
and in EDIT_FLAG.TBB:
    flag:pattern:<row>:<field>           fields base, rev
    flag:place:<row>:<field>             fields pos_x, pos_y, size_x, size_y
"""
import os
import struct
import sys

from pac import load_header
import svr
import tbb

# COLOR_TABLE.TBB: (rows, line size) per table, from the bounds EDIT::CColor
# checks (0x60, 0x20, 0x10) and its GetDataHeadPoint indices.
COLOR_TABLES = [(96, 4), (32, 1), (96, 1), (16, 1), (96, 1), (16, 1), (32, 1)]
COLOR_MAPS = {1: (32, 16), 2: (96, 16), 3: (16, 32), 4: (96, 32), 5: (16, 96), 6: (32, 96)}

# EDIT_EMBLEM.TBB record sizes, from the getters' multipliers.
EMBLEM_RECORDS = {0: 12, 1: 4, 2: 4, 3: 4, 4: 10, 5: 10, 6: 10, 7: 110, 8: 110, 9: 110,
                  10: 1, 11: 3}
LAYER_BASE, LAYERS, LAYER_RECORD = 12, 4, 12      # GetSampleLayerAcceData 0x104180
EMBLEM_TABLES = 144
CREST_TABLES = {7: "sample", 8: "initial", 9: "rival"}
AREAS = 5                       # PlEmblem's mask holds 5 areas (field table aArea x5)
MAX_LAYER_ACCE = 9              # PlEmblem aAcce x9; Initialize stops at 9 (0x103cfc)
NO_BASE = 0xFFFF                # a base preset with no base part
CLUB_COLORS = {-1: "club 1", -2: "club 2", -3: "club 3"}   # 0x103b78: the club's 3 colours

# Param::PlEmblemPreset, 0x6e bytes (field table at SLES 0x53d158-0x53d39c):
# u16 preset, then PlEmblemPresetNumber {sample, base, mask, aAreaPattern
# x5, aAreaAcce x5, aLayerAcce x4} and PlEmblemPresetColor {aAreaPattern
# x5 x2, aAreaAcce x5 x3, aLayerAcce x4 x3}, all s16.
CREST_FORMAT = "<55h"


TRS_FIELDS = ("tx", "ty", "rot", "rev", "sx", "sy", "pad")
TRS_FORMAT = "<bbhBBBB"


def trs(raw):
    """Param::PlEmblemTrs, 8 bytes {s8 tx, s8 ty, s16 rot, u8 rev, u8 sx,
    u8 sy, pad} (field table 0x53cd08-0x53cde4)."""
    return dict(zip(TRS_FIELDS, struct.unpack(TRS_FORMAT, raw[:8])))


def encode_trs(r):
    return struct.pack(TRS_FORMAT, *(r[k] for k in TRS_FIELDS))


def presets(t, table):
    """Tables 4-6: 10-byte {u16 part, PlEmblemTrs} records (Initialize
    copies +0 to the part's number and +2..+9 to its Trs)."""
    out = []
    for k in range(0, t[table].size - 9, 10):
        part, = struct.unpack_from("<H", t[table].data, k)
        out.append((part, trs(t[table].data[k + 2:k + 10])))
    return out


def crest(raw):
    v = struct.unpack(CREST_FORMAT, raw)
    return {"id": v[0], "sample": v[1], "base": v[2], "mask": v[3],
            "pattern": v[4:9], "acce": v[9:14], "layer_key": v[14:18],
            "pattern_color": [v[18 + 2 * a:20 + 2 * a] for a in range(AREAS)],
            "acce_color": [v[28 + 3 * a:31 + 3 * a] for a in range(AREAS)],
            "layer_color": [v[43 + 3 * l:46 + 3 * l] for l in range(LAYERS)]}


def crests(t, table):
    return [crest(t[table].data[k:k + 110]) for k in range(0, t[table].size - 109, 110)]


def layer_records(t, sample, layer):
    """GetSampleLayerAcceData: the 12-byte {u16 key, u16 accessory, Trs}
    records of table 12 + 4 * sample + layer, as many whole records as
    the table holds."""
    data = t[LAYER_BASE + LAYERS * sample + layer].data
    return [(struct.unpack_from("<HH", data, k), trs(data[k + 4:k + 12]))
            for k in range(0, len(data) - 11, LAYER_RECORD)]


def color_name(c):
    return CLUB_COLORS.get(c, str(c))


# --- Writing -----------------------------------------------------------
#
# Every edit changes bytes in place, so the file keeps its size and the
# three short layer tables (93, 101, 105) keep their odd tails.

FLAG_FILE, EMBLEM_FILE = "EDIT_FLAG.TBB", "EDIT_EMBLEM.TBB"
CREST_SIZE, PRESET_SIZE = 110, 10
# Crest fields in PlEmblemPreset order: (name, count) of s16 values.
CREST_FIELDS = (("id", 1), ("sample", 1), ("base", 1), ("mask", 1), ("pattern", AREAS),
                ("acce", AREAS), ("layer_key", LAYERS), ("pattern_color", 2 * AREAS),
                ("acce_color", 3 * AREAS), ("layer_color", 3 * LAYERS))
COLOR_GROUPS = {"pattern_color": 2, "acce_color": 3, "layer_color": 3}
TRS_RANGES = {"tx": (-128, 127), "ty": (-128, 127), "rot": (-32768, 32767),
              # rev: the flag patterns use 0-3 (CFlagData::Initialize copies
              # table 1's high byte into the pattern's Trs.rev); no crest
              # part uses anything but 0, and what 1-3 look like isn't checked.
              "rev": (0, 3), "sx": (0, 255), "sy": (0, 255)}
COLOR_RANGE = (-3, 31)          # 32-colour ids, or -1..-3 the club's colours (0x103b78)


def encode_crest(c):
    values = [c["id"], c["sample"], c["base"], c["mask"]]
    values += list(c["pattern"]) + list(c["acce"]) + list(c["layer_key"])
    for name in ("pattern_color", "acce_color", "layer_color"):
        values += [x for group in c[name] for x in group]
    return struct.pack(CREST_FORMAT, *values)


def encode_preset(part, r):
    return struct.pack("<H", part) + encode_trs(r)


def encode_layer_record(key, acce, r):
    return struct.pack("<HH", key, acce) + encode_trs(r)


def context(t):
    """What the range checks need from EDIT_EMBLEM.TBB: rows per table,
    the mask groups, the number of samples with layer tables."""
    rows = {i: t[i].size // rec for i, rec in EMBLEM_RECORDS.items()}
    groups = [struct.unpack_from("<HH", t[1].data, 4 * g) for g in range(rows[1])]
    return rows, groups, (len(t) - LAYER_BASE) // LAYERS


def crest_range(t, field, base=None):
    """The values a crest field allows, as Initialize (0x103a50) uses them.
    `mask` needs the crest's base: it indexes that base preset's mask group."""
    rows, groups, samples = context(t)
    if field in COLOR_GROUPS:
        return COLOR_RANGE
    if field == "id":
        return 0, 0x7FFF                # not read by Initialize
    if field == "sample":
        return 0, samples - 1
    if field == "base":
        return 0, rows[4] - 1
    if field == "mask":
        part = presets(t, 4)[base][0]
        return 0, 0 if part == NO_BASE else groups[part][1] - 1
    if field == "pattern":
        return 0, rows[5] - 1
    if field == "acce":
        return 0, rows[6] - 1
    if field == "layer_key":
        return 0, 0x7FFF                # matched against a layer record's u16 key
    raise ValueError("no crest field %r" % field)


def preset_range(t, table, field):
    rows, groups, _ = context(t)
    if field == "part":
        # t4: a mask group or NO_BASE; t5: a pattern; t6: an accessory.
        return {4: (0, len(groups) - 1), 5: (0, rows[2] - 1), 6: (0, rows[3] - 1)}[table]
    if field in TRS_RANGES:
        return TRS_RANGES[field]
    raise ValueError("no preset field %r" % field)


def layer_range(t, field):
    if field == "key":
        return 0, 0xFFFF
    if field == "acce":
        return 0, context(t)[0][3] - 1  # or NO_BASE: an empty slot
    if field in TRS_RANGES:
        return TRS_RANGES[field]
    raise ValueError("no layer record field %r" % field)


def _check_value(value, lo, hi, what, extra=()):
    if not (lo <= value <= hi or value in extra):
        raise ValueError("%s takes %d-%d%s, not %d" % (
            what, lo, hi, "".join(" or %d" % x for x in extra), value))


def set_crest(t, table, row, field, value, index=0):
    """Set one field of crest `row` of table 7, 8 or 9. List fields take
    `index`: the area (pattern, acce), the layer (layer_key), or the
    colour's place in the flattened colour list (pattern_color is area x 2
    + n, acce_color and layer_color area/layer x 3 + n). Returns the old
    value."""
    if table not in CREST_TABLES:
        raise ValueError("crests are in tables 7, 8 and 9")
    recs = crests(t, table)
    if not 0 <= row < len(recs):
        raise ValueError("table %d has rows 0-%d" % (table, len(recs) - 1))
    c = recs[row]
    lo, hi = crest_range(t, field, c["base"])
    _check_value(value, lo, hi, field)
    if field in COLOR_GROUPS:
        n = COLOR_GROUPS[field]
        flat = [x for group in c[field] for x in group]
        if not 0 <= index < len(flat):
            raise ValueError("%s has places 0-%d" % (field, len(flat) - 1))
        old, flat[index] = flat[index], value
        c[field] = [tuple(flat[k:k + n]) for k in range(0, len(flat), n)]
    elif field in ("pattern", "acce", "layer_key"):
        values = list(c[field])
        if not 0 <= index < len(values):
            raise ValueError("%s has places 0-%d" % (field, len(values) - 1))
        old, values[index] = values[index], value
        c[field] = tuple(values)
    else:
        old, c[field] = c[field], value
        if field == "base":
            # Keep the mask inside the new base's group.
            _, mhi = crest_range(t, "mask", value)
            if c["mask"] > mhi:
                raise ValueError("mask %d is past base %d's group (0-%d); set the mask first"
                                 % (c["mask"], value, mhi))
    data = bytearray(t[table].data)
    data[row * CREST_SIZE:(row + 1) * CREST_SIZE] = encode_crest(c)
    t[table].data = bytes(data)
    return old


def set_preset(t, table, row, field, value):
    """Set the part or a Trs field of preset `row` of table 4, 5 or 6."""
    if table not in (4, 5, 6):
        raise ValueError("presets are in tables 4, 5 and 6")
    recs = presets(t, table)
    if not 0 <= row < len(recs):
        raise ValueError("table %d has rows 0-%d" % (table, len(recs) - 1))
    part, r = recs[row]
    lo, hi = preset_range(t, table, field)
    _check_value(value, lo, hi, field, (NO_BASE,) if table == 4 and field == "part" else ())
    if field == "part":
        old, part = part, value
    else:
        old, r[field] = r[field], value
    data = bytearray(t[table].data)
    data[row * PRESET_SIZE:(row + 1) * PRESET_SIZE] = encode_preset(part, r)
    t[table].data = bytes(data)
    return old


def set_layer(t, sample, layer, record, field, value):
    """Set a field of one layer record. Only whole records can be edited:
    in the three short tables the game misreads records 4 onwards."""
    _, _, samples = context(t)
    if not (0 <= sample < samples and 0 <= layer < LAYERS):
        raise ValueError("samples 0-%d, layers 0-%d" % (samples - 1, LAYERS - 1))
    table = LAYER_BASE + LAYERS * sample + layer
    recs = layer_records(t, sample, layer)
    usable = len(recs) if t[table].size % LAYER_RECORD == 0 else 4
    if not 0 <= record < usable:
        raise ValueError("sample %d layer %d has records 0-%d%s" % (
            sample, layer, usable - 1,
            "" if usable == len(recs) else " the game reads correctly (TBB_FORMAT.md)"))
    (key, acce), r = recs[record]
    lo, hi = layer_range(t, field)
    _check_value(value, lo, hi, field, (NO_BASE,) if field == "acce" else ())
    if field == "key":
        old, key = key, value
    elif field == "acce":
        old, acce = acce, value
    else:
        old, r[field] = r[field], value
    data = bytearray(t[table].data)
    o = record * LAYER_RECORD
    data[o:o + LAYER_RECORD] = encode_layer_record(key, acce, r)
    t[table].data = bytes(data)
    return old


def set_start(t, row, field, value):
    """Table 10 (`sample`: the t7 row of starting crest `row`) or table 11
    (`color1`, `color2`: its first colours, 32-colour ids; byte 0 is the
    row's own index and isn't editable)."""
    rows, _, _ = context(t)
    if not 0 <= row < rows[10]:
        raise ValueError("starting crests 0-%d" % (rows[10] - 1))
    if field == "sample":
        _check_value(value, 0, rows[7] - 1, field)
        data = bytearray(t[10].data)
        old, data[row] = data[row], value
        t[10].data = bytes(data)
        return old
    if field in ("color1", "color2"):
        _check_value(value, 0, 31, field)
        data = bytearray(t[11].data)
        o = 3 * row + (1 if field == "color1" else 2)
        old = struct.unpack_from("<b", data, o)[0]
        struct.pack_into("<b", data, o, value)
        t[11].data = bytes(data)
        return old
    raise ValueError("starting crest fields: sample, color1, color2")


FLAG_PLACE_FIELDS = (("pos_x", "b"), ("pos_y", "b"), ("size_x", "B"), ("size_y", "B"))


def set_flag_pattern(t, row, field, value):
    """EDIT_FLAG table 1: `base` (low byte, a base in EDIT_FLAG.PAC) or
    `rev` (high byte, 0-3)."""
    n = t[1].size // 2
    if not 0 <= row < n:
        raise ValueError("flag patterns 0-%d" % (n - 1))
    base, rev = t[1].data[2 * row], t[1].data[2 * row + 1]
    if field == "base":
        _check_value(value, 0, t[0].size // 4 - 1, field)
        old, base = base, value
    elif field == "rev":
        _check_value(value, *TRS_RANGES["rev"], what=field)
        old, rev = rev, value
    else:
        raise ValueError("flag pattern fields: base, rev")
    data = bytearray(t[1].data)
    data[2 * row:2 * row + 2] = bytes((base, rev))
    t[1].data = bytes(data)
    return old


def set_flag_place(t, row, field, value):
    """EDIT_FLAG table 2 (Param::PlFlagEmblemTs): s8 pos_x, s8 pos_y,
    u8 size_x, u8 size_y."""
    n = t[2].size // 4
    if not 0 <= row < n:
        raise ValueError("crest placements 0-%d" % (n - 1))
    names = [f for f, _ in FLAG_PLACE_FIELDS]
    if field not in names:
        raise ValueError("crest placement fields: %s" % ", ".join(names))
    k = names.index(field)
    fmt = FLAG_PLACE_FIELDS[k][1]
    _check_value(value, *((-128, 127) if fmt == "b" else (0, 255)), what=field)
    data = bytearray(t[2].data)
    o = 4 * row + k
    old = struct.unpack_from("<" + fmt, data, o)[0]
    struct.pack_into("<" + fmt, data, o, value)
    t[2].data = bytes(data)
    return old

PACKS = [("EDIT_EMBLEM_A", 217), ("EDIT_EMBLEM_M", 214), ("EDIT_EMBLEM_P", 22),
         ("EDIT_FLAG", 49)]
FLAG_RECORDS = {0: 4, 1: 2, 2: 4}


def problems_line(line, problems):
    return line + ("  !! " + "; ".join(problems) if problems else "")


def load_tables(d, name):
    _, tables = tbb.load(os.path.join(d, name))
    return tables


def color_rgba(word):
    """EDIT::CColor colour word -> (r, g, b, a): GetColor16 (0x2b9bf8)
    takes red from bits 24-31, green 16-23, blue 8-15, alpha 0-7."""
    return word >> 24, (word >> 16) & 0xFF, (word >> 8) & 0xFF, word & 0xFF


def check_colors(d):
    try:
        t = load_tables(d, "COLOR_TABLE.TBB")
    except (OSError, ValueError, struct.error) as e:
        return ["COLOR_TABLE.TBB  !! %s" % e]
    problems = []
    if len(t) != len(COLOR_TABLES):
        return ["COLOR_TABLE.TBB  !! %d tables, expected %d" % (len(t), len(COLOR_TABLES))]
    for i, (rows, line) in enumerate(COLOR_TABLES):
        if t[i].size != rows * line:
            problems.append("t%d is %d bytes, expected %d" % (i, t[i].size, rows * line))
    for i, (src, dst) in COLOR_MAPS.items():
        if any(v >= dst for v in t[i].data):
            problems.append("t%d maps outside 0-%d" % (i, dst - 1))
    if not problems:
        m = {i: t[i].data for i in COLOR_MAPS}
        # A smaller palette's colours map up and back to themselves.
        if any(m[4][m[6][i]] != i for i in range(32)):
            problems.append("32 -> 96 -> 32 doesn't return")
        if any(m[2][m[5][i]] != i for i in range(16)):
            problems.append("16 -> 96 -> 16 doesn't return")
        if any(m[1][m[3][i]] != i for i in range(16)):
            problems.append("16 -> 32 -> 16 doesn't return")
    words = struct.unpack_from("<%dI" % (t[0].size // 4), t[0].data)
    alphas = sorted({w & 0xFF for w in words})
    line = "COLOR_TABLE.TBB  %d colours (alpha %s), 32- and 16-colour palettes" % (
        len(words), " ".join("%02x" % a for a in alphas))
    return [problems_line(line, problems)]


def pack_names(d, name):
    hdr = load_header(os.path.join(d, name + ".PAC"))
    return [e[2] for e in hdr.entries]


def check_packs(d):
    out = []
    counts = {}
    for name, want in PACKS:
        pac = os.path.join(d, name + ".PAC")
        try:
            hdr = load_header(pac)
            with open(pac, "rb") as f:
                data = f.read()
            with open(os.path.join(d, name + ".HED"), "rb") as f:
                head = f.read()
        except (OSError, ValueError, struct.error) as e:
            out.append("%-18s !! %s" % (name + ".PAC", e))
            continue
        problems = []
        if data[:len(head)] != head:
            problems.append("%s.HED isn't a copy of the pack's header" % name)
        kinds = {}
        for off, size, n, _ in hdr.entries:
            try:
                tex = svr.parse_svr(data[off:off + size], n)
            except (ValueError, struct.error, KeyError) as e:
                problems.append("%s: %s" % (n, e))
                continue
            k = "%dx%d %s" % (tex.width, tex.height, tex.fmt_name)
            kinds[k] = kinds.get(k, 0) + 1
        counts[name] = len(hdr.entries)
        if len(hdr.entries) != want:
            problems.append("%d entries, expected %d" % (len(hdr.entries), want))
        line = "%-18s %3d entries, %s" % (name + ".PAC", len(hdr.entries),
                                          ", ".join("%d at %s" % (v, k) for k, v in kinds.items()))
        out.append(problems_line(line, problems))
    return out, counts


def check_edit_emblem(d, counts):
    try:
        t = load_tables(d, "EDIT_EMBLEM.TBB")
    except (OSError, ValueError, struct.error) as e:
        return ["EDIT_EMBLEM.TBB  !! %s" % e]
    out = []
    problems = []
    if len(t) != EMBLEM_TABLES:
        problems.append("%d tables, expected %d" % (len(t), EMBLEM_TABLES))
    for i, rec in EMBLEM_RECORDS.items():
        if i < len(t) and t[i].size % rec:
            problems.append("t%d (%d bytes) isn't whole %d-byte records" % (i, t[i].size, rec))
    if problems or len(t) < LAYER_BASE:
        return [problems_line("EDIT_EMBLEM.TBB", problems)]
    rows = {i: t[i].size // rec for i, rec in EMBLEM_RECORDS.items()}
    # Masks: t1 groups index t0 (GetMaskData 0x103eb0), and the groups are
    # the _mask_GGG_NN names of the M pack.
    groups = [struct.unpack_from("<HH", t[1].data, 4 * g) for g in range(rows[1])]
    first = 0
    for g, (start, n) in enumerate(groups):
        if start != first:
            problems.append("mask group %d starts at %d, not %d" % (g, start, first))
            break
        first += n
    if first != rows[0]:
        problems.append("mask groups cover %d masks, t0 has %d" % (first, rows[0]))
    if any(struct.unpack_from("<H", t[0].data, 12 * i)[0] != i for i in range(rows[0])):
        problems.append("t0 records don't start with their own index")
    try:
        names = pack_names(d, "EDIT_EMBLEM_M")
        want = ["_mask_%03d_%02d.svr" % (g + 1, k + 1) for g, (_, n) in enumerate(groups)
                for k in range(n)]
        if [n[-16:] for n in names] != [n[-16:] for n in want]:
            problems.append("EDIT_EMBLEM_M names don't follow the mask groups")
    except (OSError, ValueError, struct.error) as e:
        problems.append("EDIT_EMBLEM_M: %s" % e)
    for tab, pack in ((0, "EDIT_EMBLEM_M"), (2, "EDIT_EMBLEM_P"), (3, "EDIT_EMBLEM_A")):
        if pack in counts and rows[tab] != counts[pack]:
            problems.append("t%d has %d rows, %s %d entries" % (tab, rows[tab], pack, counts[pack]))
    for tab in (2, 3):
        vals = struct.unpack_from("<%dI" % rows[tab], t[tab].data)
        if list(vals) != list(range(rows[tab])):
            problems.append("t%d isn't 0-%d in order" % (tab, rows[tab] - 1))
    out.append(problems_line(
        "EDIT_EMBLEM.TBB  %d masks in %d groups, %d patterns, %d accessories, presets %d/%d/%d, "
        "samples %d, initial %d, rival %d" % (
            rows[0], rows[1], rows[2], rows[3], rows[4], rows[5], rows[6], rows[7], rows[8],
            rows[9]), problems))
    samples = (len(t) - LAYER_BASE) // LAYERS
    out.extend(check_presets(t, rows, groups))
    for table in CREST_TABLES:
        out.append(check_crests(t, table, rows, groups, samples))
    problems = []
    initial_samples = list(t[10].data)
    same = ""
    if any(s >= rows[7] for s in initial_samples):
        problems.append("t10 names a sample past t7's %d rows" % rows[7])
    else:
        # On the disc each initial crest is its t10 sample's parts with its
        # own colours. The game doesn't need that, so it's a count, not !!.
        samples7, initial = crests(t, 7), crests(t, 8)
        keys = ("sample", "base", "mask", "pattern", "acce", "layer_key")
        same = ", %d with their sample's parts" % sum(
            all(initial[i][k] == samples7[s][k] for k in keys)
            for i, s in enumerate(initial_samples[:len(initial)]))
    for i in range(rows[11]):
        own, c1, c2 = struct.unpack_from("<3b", t[11].data, 3 * i)
        if own != i or not (0 <= c1 < 32 and 0 <= c2 < 32):
            problems.append("t11 row %d is %d %d %d, expected %d and two 32-colour ids" % (
                i, own, c1, c2, i))
            break
    out.append(problems_line("  t10/t11: %d initial crests' samples and first colours%s" % (
        rows[10], same), problems))
    # Layer accessory tables, 12 + 4 * sample + layer. The reader walks
    # GetDataTableCount records of 12 bytes (0x1041bc-0x104230).
    short = []
    total = 0
    for i in range(LAYER_BASE, len(t)):
        total += t[i].size // LAYER_RECORD
        if t[i].size % LAYER_RECORD:
            short.append(i)
    out.append("  layer tables t%d-t%d: %d samples x %d layers, %d records" % (
        LAYER_BASE, len(t) - 1, samples, LAYERS, total))
    for i in short:
        s, layer = divmod(i - LAYER_BASE, LAYERS)
        out.append("  t%d (sample %d, layer %d): %d bytes  !! not whole 12-byte records; "
                   "the game reads %d of them, misreads records 4-10 and never reaches "
                   "record 11 (TBB_FORMAT.md)" % (
                       i, s, layer, t[i].size, t[i].size // LAYER_RECORD))
    return out


def check_presets(t, rows, groups):
    """Tables 4-6: t4's part is a mask group (or NO_BASE), t5's a pattern,
    t6's an accessory."""
    out = []
    for table, what, limit in ((4, "base", len(groups)), (5, "pattern", rows[2]),
                               (6, "accessory", rows[3])):
        recs = presets(t, table)
        problems = []
        bad = [i for i, (part, _) in enumerate(recs)
               if part >= limit and not (table == 4 and part == NO_BASE)]
        if bad:
            problems.append("rows %s name a %s past %d" % (bad[:5], what, limit - 1))
        none = sum(part == NO_BASE for part, _ in recs) if table == 4 else 0
        rots = sorted({r["rot"] for _, r in recs})
        out.append(problems_line("  t%d: %d %s presets%s, rotations %s" % (
            table, len(recs), what, ", %d with no base" % none if none else "",
            " ".join(map(str, rots))), problems))
    return out


def check_crests(t, table, rows, groups, samples):
    """A PlEmblemPreset's references, as Initialize (0x103a50) follows them:
    base -> t4 (whose part is the mask group the mask indexes), the area
    patterns -> t5, the area accessories -> t6, the sample and layer keys
    -> the layer tables; colours are 32-colour ids or -1..-3."""
    recs = crests(t, table)
    base_parts = [p for p, _ in presets(t, 4)]
    problems = []
    layered = 0
    for n, c in enumerate(recs):
        p = []
        if not 0 <= c["base"] < rows[4]:
            p.append("base %d" % c["base"])
        else:
            group = base_parts[c["base"]]
            count = 1 if group == NO_BASE else groups[group][1]
            if not 0 <= c["mask"] < count:
                p.append("mask %d past base %d's group (%d masks)" % (c["mask"], c["base"], count))
        if not 0 <= c["sample"] < samples:
            p.append("sample %d" % c["sample"])
        if any(not 0 <= x < rows[5] for x in c["pattern"]):
            p.append("area pattern past t5")
        if any(not 0 <= x < rows[6] for x in c["acce"]):
            p.append("area accessory past t6")
        colors = [x for cs in c["pattern_color"] + c["acce_color"] + c["layer_color"] for x in cs]
        if any(not -3 <= x < 32 for x in colors):
            p.append("a colour outside -3..31")
        if not p:
            hits = [acc for l in range(LAYERS) for (key, acc), _ in layer_records(t, c["sample"], l)
                    if key == c["layer_key"][l]]
            if len(hits) > MAX_LAYER_ACCE:
                p.append("%d layer accessories, the game keeps %d" % (len(hits), MAX_LAYER_ACCE))
            # Accessory 0xffff fills a slot with nothing.
            layered += sum(acc != NO_BASE for acc in hits[:MAX_LAYER_ACCE])
        if p:
            problems.append("row %d: %s" % (n, ", ".join(p)))
    return problems_line("  t%d: %d %s crests, %d layer accessories" % (
        table, len(recs), CREST_TABLES[table], layered), problems)


def check_edit_flag(d, counts):
    try:
        t = load_tables(d, "EDIT_FLAG.TBB")
    except (OSError, ValueError, struct.error) as e:
        return "EDIT_FLAG.TBB  !! %s" % e
    problems = []
    if len(t) != len(FLAG_RECORDS):
        return "EDIT_FLAG.TBB  !! %d tables, expected %d" % (len(t), len(FLAG_RECORDS))
    for i, rec in FLAG_RECORDS.items():
        if t[i].size % rec:
            problems.append("t%d isn't whole %d-byte records" % (i, rec))
    if problems:
        return problems_line("EDIT_FLAG.TBB", problems)
    bases = struct.unpack_from("<%dI" % (t[0].size // 4), t[0].data)
    if list(bases) != list(range(len(bases))):
        problems.append("t0 isn't 0-%d in order" % (len(bases) - 1))
    if "EDIT_FLAG" in counts and len(bases) != counts["EDIT_FLAG"]:
        problems.append("t0 has %d bases, EDIT_FLAG.PAC %d" % (len(bases), counts["EDIT_FLAG"]))
    patterns = struct.unpack_from("<%dH" % (t[1].size // 2), t[1].data)
    if any((p & 0xFF) >= len(bases) for p in patterns):
        problems.append("a pattern's low byte is past the last base")
    return problems_line("EDIT_FLAG.TBB  %d bases, %d patterns (%d variants), %d crest placements"
                         % (len(bases), len(patterns), len({p >> 8 for p in patterns}),
                            t[2].size // 4), problems)


def cmd_info(d):
    for line in check_colors(d):
        print(line)
    lines, counts = check_packs(d)
    for line in lines:
        print(line)
    for line in check_edit_emblem(d, counts):
        print(line)
    print(check_edit_flag(d, counts))
    try:
        t = load_tables(d, "EDIT_PLAYER.TBB")
        print("EDIT_PLAYER.TBB  %d tables, %d rows (layout not decoded)" % (
            len(t), sum(x.row_count for x in t)))
    except (OSError, ValueError, struct.error) as e:
        print("EDIT_PLAYER.TBB  !! %s" % e)
    size = os.path.getsize(os.path.join(d, "DUMMY.DAT"))
    print("DUMMY.DAT  %d bytes" % size)


def cmd_colors(d):
    t = load_tables(d, "COLOR_TABLE.TBB")
    words = struct.unpack_from("<%dI" % (t[0].size // 4), t[0].data)
    to32, to16 = t[4].data, t[2].data
    in32, in16 = set(t[6].data), set(t[5].data)
    for i, w in enumerate(words):
        r, g, b, a = color_rgba(w)
        print("%2d  #%02x%02x%02x  alpha %02x  -> 32:%2d%s  16:%2d%s" % (
            i, r, g, b, a, to32[i], "*" if i in in32 else " ", to16[i], "*" if i in in16 else ""))


def load_file(path):
    """(buf, end, tables, kind), kind "emblem" or "flag" by table count."""
    with open(path, "rb") as f:
        buf = f.read()
    end, t = tbb.parse(buf)
    if len(t) == EMBLEM_TABLES:
        return buf, end, t, "emblem"
    if len(t) == len(FLAG_RECORDS):
        return buf, end, t, "flag"
    raise ValueError("%d tables: not EDIT_EMBLEM.TBB (%d) or EDIT_FLAG.TBB (%d)" % (
        len(t), EMBLEM_TABLES, len(FLAG_RECORDS)))


def edit_problems(t, kind):
    """The record checks `info` makes, for a file about to be written."""
    if kind == "flag":
        return []
    rows, groups, samples = context(t)
    lines = check_presets(t, rows, groups)
    lines += [check_crests(t, table, rows, groups, samples) for table in CREST_TABLES]
    return [line.split("  !! ", 1)[1] for line in lines if "  !! " in line]


def encode_file(buf, end, t, kind):
    problems = edit_problems(t, kind)
    if problems:
        raise ValueError("; ".join(problems))
    out = tbb.build(t, end, tbb.trailer(buf, t))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


def apply_edit(t, kind, edit):
    """One `set` argument: <target>=<value>. Returns a line for the log."""
    target, sep, value = edit.partition("=")
    if not sep:
        raise ValueError("expected <target>=<value>")
    value = int(value, 0)
    p = target.split(":")
    if kind == "flag":
        if len(p) == 4 and p[0] == "flag" and p[1] in ("pattern", "place"):
            fn = set_flag_pattern if p[1] == "pattern" else set_flag_place
            old = fn(t, int(p[2], 0), p[3], value)
            return "%s: %d -> %d" % (target, old, value)
        raise ValueError("EDIT_FLAG.TBB takes flag:pattern:<row>:<field> or "
                         "flag:place:<row>:<field>")
    if p[0] == "crest" and len(p) == 4:
        field, _, index = p[3].partition(".")
        old = set_crest(t, int(p[1], 0), int(p[2], 0), field, value, int(index or "0", 0))
    elif p[0] == "preset" and len(p) == 4:
        old = set_preset(t, int(p[1], 0), int(p[2], 0), p[3], value)
    elif p[0] == "layer" and len(p) == 5:
        old = set_layer(t, int(p[1], 0), int(p[2], 0), int(p[3], 0), p[4], value)
    elif p[0] == "start" and len(p) == 3:
        old = set_start(t, int(p[1], 0), p[2], value)
    else:
        raise ValueError("EDIT_EMBLEM.TBB takes crest:<table>:<row>:<field>[.<n>], "
                         "preset:<table>:<row>:<field>, "
                         "layer:<sample>:<layer>:<record>:<field> or start:<row>:<field>")
    return "%s: %d -> %d" % (target, old, value)


def cmd_set(path, out_path, edits):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, t, kind = load_file(path)
    for e in edits:
        try:
            print(apply_edit(t, kind, e))
        except ValueError as err:
            raise SystemExit("%s: %s" % (e, err))
    try:
        out = encode_file(buf, end, t, kind)
    except ValueError as err:
        raise SystemExit(str(err))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def rebuild_records(t, kind):
    """Decode every record the writer edits and encode it again from its
    fields, leaving the bytes no record covers (the short layer tables'
    tails) as they are. Returns the names of tables that came out
    different."""
    differ = []

    def put(i, data):
        if data != t[i].data:
            differ.append("t%d" % i)
        t[i].data = data

    if kind == "flag":
        put(1, b"".join(struct.pack("<BB", *struct.unpack_from("<BB", t[1].data, k))
                        for k in range(0, t[1].size, 2)))
        put(2, b"".join(struct.pack("<bbBB", *struct.unpack_from("<bbBB", t[2].data, k))
                        for k in range(0, t[2].size, 4)))
        return differ
    for i in (4, 5, 6):
        put(i, b"".join(encode_preset(part, r) for part, r in presets(t, i)))
    for i in CREST_TABLES:
        put(i, b"".join(encode_crest(c) for c in crests(t, i)))
    put(10, bytes(t[10].data))
    put(11, b"".join(struct.pack("<3b", *struct.unpack_from("<3b", t[11].data, 3 * k))
                     for k in range(t[11].size // 3)))
    _, _, samples = context(t)
    for s in range(samples):
        for l in range(LAYERS):
            i = LAYER_BASE + LAYERS * s + l
            recs = layer_records(t, s, l)
            whole = len(recs) * LAYER_RECORD
            put(i, b"".join(encode_layer_record(k, a, r) for (k, a), r in recs)
                + t[i].data[whole:])
    return differ


def cmd_roundtrip(paths):
    for path in paths:
        if os.path.isdir(path):
            targets = [os.path.join(path, EMBLEM_FILE), os.path.join(path, FLAG_FILE)]
        else:
            targets = [path]
        for p in targets:
            try:
                buf, end, t, kind = load_file(p)
                differ = rebuild_records(t, kind)
                out = encode_file(buf, end, t, kind)
            except (OSError, ValueError, struct.error) as e:
                print("%s  !! %s" % (p, e))
                continue
            if differ or out != buf:
                print("%s  !! rebuilt file differs%s" % (
                    p, " (tables %s)" % ", ".join(differ) if differ else ""))
            else:
                print("%s  %d bytes, every record re-encoded, identical" % (p, len(buf)))


def fmt_trs(r):
    return "at %d,%d rot %d rev %d scale %d%%x%d%%" % (r["tx"], r["ty"], r["rot"], r["rev"],
                                                       r["sx"], r["sy"])


def cmd_crests(d, tables):
    t = load_tables(d, "EDIT_EMBLEM.TBB")
    bases, patterns = presets(t, 4), presets(t, 5)
    for table in tables:
        print("t%d: %s crests" % (table, CREST_TABLES[table]))
        for n, c in enumerate(crests(t, table)):
            part, r = bases[c["base"]]
            print("  row %d  id %d  sample %d  base %d (%s, %s)  mask %d" % (
                n, c["id"], c["sample"], c["base"],
                "no base" if part == NO_BASE else "mask group %d" % part, fmt_trs(r), c["mask"]))
            for a in range(AREAS):
                pat, pr = patterns[c["pattern"][a]]
                print("    area %d  pattern %d (texture %d, %s), colours %s; accessory %d, "
                      "colours %s" % (
                          a, c["pattern"][a], pat, fmt_trs(pr),
                          "/".join(map(color_name, c["pattern_color"][a])), c["acce"][a],
                          "/".join(map(color_name, c["acce_color"][a]))))
            for l in range(LAYERS):
                hits = [(acc, lr) for (key, acc), lr in layer_records(t, c["sample"], l)
                        if key == c["layer_key"][l]]
                print("    layer %d  key %d, colours %s: %s" % (
                    l, c["layer_key"][l], "/".join(map(color_name, c["layer_color"][l])),
                    "; ".join("no accessory" if acc == NO_BASE else
                              "accessory %d %s" % (acc, fmt_trs(lr)) for acc, lr in hits)
                    or "none"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "colors" and len(args) == 1:
        cmd_colors(args[0])
    elif cmd == "crests" and len(args) in (1, 2) and all(a in ("7", "8", "9") for a in args[1:]):
        cmd_crests(args[0], [int(a) for a in args[1:]] or sorted(CREST_TABLES))
    elif cmd == "set" and len(args) >= 3:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and args:
        cmd_roundtrip(args)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
