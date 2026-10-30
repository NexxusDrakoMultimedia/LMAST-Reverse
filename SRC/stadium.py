# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Stadium data checker for Let's Make a Soccer Team! (PS2).

DAT/STADIUM holds 10 stadium models (7 home grounds ho00a-ho04a, 3 away
grounds aw01a-aw04b; name table at GAMEPRG.REL 0x24d6a8), each as a set of
BINPAC packs of Ninja models in four lighting variants (D1, D2, N1, N2),
plus shared packs and the tables that build one of the 119 real stadiums
from a model. See DOC/STADIUM_DIR.md. Addresses are GAMEPRG.REL offsets.

  <model>.PRI            44 x u32: draw priority of each part slot, 0-100.
                         Read at 0x1caf18 (from pfs0:, a development path)
                         and requested with OpenReq(folder 0xa) at 0x1cdf60.
                         0x1cae18 / 0x1cae98 draw priorities 0-49, then 50-100.
  BUILD_STADIUM.TBB      t0: 119 x 129 bytes, one row per stadium (0x1cdb38:
                         i * 0x81). Byte 0 is the model (0x1cd72c: < 10);
                         bytes 1-109 switch parts per lighting variant (the
                         builders at 0x1cede0-0x1cf4e8, see PARTS); byte 110-114
                         are SHADOWCOLLI entries and byte 128 the WALLCOLLI
                         entry (GAME/, 0x169d4 -> 0x212a8); byte 115 the crowd
                         set (0x1d3848); bytes 116-127 the 12 advert textures
                         (0x1d31b8). t1: 10 x 12, one row per model (0x1cdbb0).
                         t2: 4 variants x 10 models x 10 STAND_NODE_NAME
                         entries (0x1cdc28, 0x1cfd58).
  CONV_INFO_BUILD.TBB    6 leagues x 5 levels x 5 variants of stadium ids:
                         t[league*25 + level*5 + variant] (0x1ce0b8; the same
                         table is PARAM/PLRESOURCESIM.PAC entry 10, read by
                         plTeam_GetStadiumDataIndex, SLES 0x22c1e0).
  BUILD_ADVERTISE.TBB    32 x {s16 type, s16 alt type, s16 link, s16 part}
                         (0x1d1c60, 0x1d21c0); types 0-4 pick a creator class
                         (jump table 0x299d30, factory 0x1d2028).
  ADVERTISE_MODELPACK    32 x char[8] board names.
  AUD_JAM_HI.TBB         rows of 5 x u16 {amount[3], palette, threshold},
                         1024 = 1.0 (0x1d8188, 0x1d8330).
  AUD_JAM_LW.TBB         rows of {u16 threshold, u16 level} (0x1d8558).
  AUD_SET_<model>_<n>    t0: 9 stand sections {u16 share, u16 tiers,
                         u32 pointer slot} (0x1d68b0 patches in t1-t9);
                         t1-t9 per section, one 8-byte row per tier {u32
                         capacity, u16 fill/1024, u8 flag, u8 0} (0x1d73c0,
                         0x1d7d00); t10: 40-byte crowd blocks {char[32] name,
                         u8 section, u8 tier, u8 flag, ...}; t11: 1 byte, the
                         number of high-detail tiers (0x1d6ac4).
  AUD_MODEL_<model>_<v>  crowd models: with 2+ materials and 3+ nodes
                         (0x1d5340), nodes 1-3 are the figure groups
                         AUD_JAM_HI thins (front to back rows) and
                         materials 0/1 the tier's two crowd kinds.

`info` checks all of these and the cross-references between them: every
crowd block has a model in its AUD_MODEL packs (counting the three-group
and single ones, and marking an empty one a stadium can reach), every crowd set matches its
stadium's model, every table-2 entry names a node list of its own model and
variant, the collision entries exist in GAME/SHADOWCOLLI and GAME/WALLCOLLI
(when DAT/GAME is next to DAT/STADIUM), and BUILD_STADIUM has one row per
PARAM/STADIUM_DATA.TBB stadium.

The writer edits BUILD_STADIUM table 0 in place: `setlook` builds a
stadium like another (its model, parts and crowd set, keeping its own
boards), `setboards` sets a stadium's 12 advert textures (1-205: logo
v - 1 of SPONSOR_TEXTURE_M; 206 and up all draw adidas, which the match
adds by itself, so they are refused). `roundtrip` edits each row on its
own and marks with !! any byte that changes outside it.

Usage:
    python stadium.py info  <DAT/STADIUM> [<DAT/PARAM>]   # check the folder
    python stadium.py pri   <file.PRI>                    # the 44 priorities
    python stadium.py build <DAT/STADIUM> <stadium id>    # one BUILD_STADIUM row
    python stadium.py crowd <file.TBB>                    # one AUD_SET table
    python stadium.py setlook   <in> <out> <id>=<src id> ...  # built like another
    python stadium.py setboards <in> <out> <id> <v1> ... <v12> [<id> ...]
    python stadium.py roundtrip <BUILD_STADIUM.TBB or DAT/STADIUM> ...
"""
import os
import struct
import sys
from collections import Counter

import pac
import tbb

MODELS = ("ho00a", "ho00b", "ho01a", "ho01b", "ho02a", "ho03a", "ho04a",
          "aw01a", "aw03a", "aw04b")          # GAMEPRG.REL 0x24d6a8
VARIANTS = ("d1", "d2", "n1", "n2")
PRI_SLOTS = 44                                # loops of 0x2b + 1 at 0x1caf80
# The 44 part slots as the developer Stadium Viewer names them in its VISIBLE
# menu (GAMEPRG.REL 0x24d3c8), in slot order. They match the builders'
# slots and the part file names (lig0 LIGHT_0, lna LANDSCAPE_A, ...).
SLOT_NAMES = (
    "GOAL", "CFLAG", "SKY", "PITCH", "PITCH_PEEL", "BENCH_LOW", "BENCH_HIGH",
    "FENCE", "FENCE_SHADOW", "NET", "NET_SHADOW", "BANNER", "STAND_0",
    "STAND_SHADOW_0", "STAND_1", "STAND_SHADOW_1", "STAND_2", "STAND_SHADOW_2",
    "STAND_3", "STAND_SHADOW_3", "LIGHT_0", "LIGHT_SHADOW_0A", "LIGHT_SHADOW_0B",
    "ILLUMINATION_0", "LIGHT_1", "LIGHT_SHADOW_1", "ILLUMINATION_1", "SPOT_0",
    "SPOT_1", "SPOT_2", "SPOT_3", "STAND_CAP_1", "STAND_CAP_2", "STAND_CAP_3",
    "STAND_CAP_4", "STAND_CAP_5", "STAFF_0", "STAFF_1", "STAFF_2",
    "AURORA_VISION_1", "AURORA_VISION_SHADOW_1", "AURORA_VISION_MONITOR_1",
    "LANDSCAPE_A", "LANDSCAPE_B")
# Request +0x88 = row byte 82 (the row is copied to +0x36 at 0x1cd680). The
# callers pass "+0x88 != 0" to the variant picker 0x1ce208, which chooses N2
# over N1 at night; byte 82 is the LIGHT_1 switch.
BUILD_NIGHT2 = 82
PRI_MAX = 100                                 # the second draw pass ends at 0x64
PRI_PASS = 50                                 # first pass draws 0-0x31
BUILD_ROW = 0x81                              # 0x1cdb90: (i << 7) + i
BUILD_CROWD = 115                             # request +0xa9 = row +0x36 + 115
BUILD_SHADOW = slice(110, 115)                # 0x169d4: request bytes 0x6e-0x72
BUILD_WALL = 128                              # 0x169d4: object +0x172e
BUILD_ADVERT = slice(116, 128)                # offsets listed at 0x299750
MONTHS = 12
T2_ROW, T2_ENTRY = 100, 10                    # 0x1cdc28: row * 100 + model * 10
STADIUM_DATA_ROW = 3                          # SLES_541.51 0x22add4: i * 3, i < 0x77
# Crowd sets (request +0xa9, clamped to < 18): model and file number, from the
# byte tables at 0x24dfa8 and 0x24dfc0.
CROWD_SETS = ((0, 1), (1, 1), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3),
              (4, 1), (4, 2), (4, 3), (5, 1), (5, 2), (5, 3), (6, 1), (7, 1),
              (8, 1), (9, 1))
CONV_ROWS, CONV_LEVELS, CONV_VARIANTS = 6, 5, 5
ADVERT_ROW = 8
ADVERT_TYPES = ("common", "lcd-anim", "fixed", "electric", "lcd-logo")   # 0x299d30
MODELPACK_ROW = 8
JAM_HI_ROW, JAM_LW_ROW = 10, 4
JAM_ONE = 1024
AUD_SECTIONS = 9
AUD_BLOCK = 0x28
AUD_NAME = 0x20
CROWD_GROUP_MATS, CROWD_GROUP_NODES = 2, 3    # 0x1d5340: object +0x10 >= 2, +0x28 >= 3
# Row bytes 1-109 that switch parts on, from the builders called at 0x1cec70:
# (first byte, last byte, step, slot, pack, first entry, entry step, what).
# A byte shows its part in the variants whose bit it has (01 02 04 04 at
# 0x299828, D1 D2 N1 N2). "first" means the first enabled byte in the group
# wins. Slot is the .PRI slot. Pack "stcmn" is STCMN_<variant>, "model" the
# model's own <MODEL>_<variant> pack, "op" <MODEL>_OP.
PARTS = (
    (1, 3, 1, 0, "stcmn", 0, 1, "goal (first)"),                  # 0x1cede0
    (4, 12, 1, 3, "stcmn", 3, 1, "pitch pattern (first), + season * 9"),   # 0x1ceed8
    (13, 13, 1, 4, "model", 44, 1, "pitch edge ptp_su / ptp_wi by table 1"),
    (14, 18, 2, 5, "stcmn", 39, 2, "bench (first)"),               # 0x1cefb8
    (20, 20, 1, 1, "stcmn", 45, 1, "corner flags"),                # 0x1cee40
    (25, 25, 1, 42, "stcmn", 46, 1, "landscape A, + request byte 7 (landscape level)"),    # 0x1cf018
    (26, 26, 1, 43, "stcmn", 50, 1, "landscape B, + request byte 5 (weather)"),
    (27, 31, 1, 7, "model", 0, 1, "fence 1-5"),                    # 0x1cf0a8
    (32, 32, 1, 8, "model", 5, 1, "fence shadow"),
    (33, 35, 2, 9, "model", 6, 2, "net 1-2"),                      # 0x1cf138
    (34, 36, 2, 10, "model", 7, 2, "net shadow 1-2"),
    (37, 41, 1, 11, "model", 10, 1, "banners"),                    # 0x1cf1e0
    (70, 77, 1, 12, "model", 15, 1, "stands 0-3 and their shadows"),   # 0x1cf238
    (78, 84, 1, 20, "model", 23, 1, "lights and light shafts"),    # 0x1cf2a8
    (85, 88, 1, 27, "model", 30, 1, "spotlights 0-3"),             # 0x1cf318
    (89, 93, 1, 31, "model", 34, 1, "caps 1-5"),                   # 0x1cf388
    (98, 98, 1, 39, "model", 42, 1, "advert rig avi1 (if adverts on)"),    # 0x1cf468
    (99, 99, 1, 40, "model", 43, 1, "advert rig avs1 (if adverts on)"),
    (100, 100, 1, 41, "op", 0, 1, "the _OP part (if adverts on)"),
    (107, 109, 1, 36, "model", 39, 1, "staff areas 0-2"),          # 0x1cf3f8
)
# Packs every model has, as (prefix, suffix) around the model name.
MODEL_PACKS = ([("", "_" + v) for v in VARIANTS + ("op",)] +
               [("adt_", "_" + v) for v in VARIANTS] +
               [("aud_model_", "_" + v) for v in VARIANTS])


def read_pri(path):
    with open(path, "rb") as f:
        buf = f.read()
    if len(buf) != 4 * PRI_SLOTS:
        raise ValueError("%d bytes, expected %d" % (len(buf), 4 * PRI_SLOTS))
    return struct.unpack("<%dI" % PRI_SLOTS, buf)


def rows(data, size):
    if len(data) % size:
        raise ValueError("%d bytes is not a whole number of %d-byte rows" % (len(data), size))
    return [data[i:i + size] for i in range(0, len(data), size)]


def copy_rows(data, pairs):
    """BUILD_STADIUM.TBB bytes with each stadium `dst` of `pairs` ({dst:
    src}) built like `src`: its table-0 row (model, parts, crowd set),
    copied from the rows as they were, but for the 12 advert textures,
    which stay the stadium's own. None when every `dst` already matches.
    The file keeps its size."""
    def look(row):
        return row[:BUILD_ADVERT.start] + row[BUILD_ADVERT.stop:]
    _, t = tbb.parse(data)
    old = rows(t[0].data, BUILD_ROW)
    if all(look(old[d]) == look(old[s]) for d, s in pairs.items()):
        return None
    out = bytearray(data)
    base = t[0].offset + t[0].data_offset
    for d, s in pairs.items():
        at = base + d * BUILD_ROW
        out[at:at + BUILD_ADVERT.start] = old[s][:BUILD_ADVERT.start]
        out[at + BUILD_ADVERT.stop:at + BUILD_ROW] = old[s][BUILD_ADVERT.stop:]
    return bytes(out)


# The LMASTER Mod's sponsor boards (DOC/LMASTER_MOD.md#stadiums): each
# stadium's 12 advert textures are drawn afresh from all the sponsor logos
# (value v is logo v - 1 of SPONSOR_TEXTURE_M: 1-205, 0x1d31b8), a fixed
# shuffle per stadium, where the retail rows use 119 of them. Value 206 and
# up is ADT_TEXCMN entry 212, adidas, which the match puts first on every
# ground by itself (request +0x10, 0x1cd618); the draws leave it out.
SPONSOR_LOGOS = range(1, 206)
RIVAL_STADIUM = 114                 # the rival's ground (TEAM_INIT_DATA table 7): kept as it is
SPONSOR_SEED = 0x4c4d               # "LM": any fixed seed, so every build is the same


# How many different sponsors a ground shows grows with its size (the
# Nexxus's request, 2026-10-31): SPONSOR_KINDS[k] is the most capacity (in
# thousands) that gets k + SPONSOR_FEWEST different logos; bigger grounds
# get all 12. A ground's size is the one --mod real-grounds gives it
# (initteam.ground_bands; the ladder's ids keep the retail size).
SPONSOR_FEWEST = 3
SPONSOR_KINDS = (8, 15, 20, 25, 30, 35, 40, 45, 50)     # 3 at 8,000 ... 11 at 50,000
SPONSOR_BOARDS = 12


def sponsor_count(capacity):
    """How many different sponsors a ground of `capacity` thousand shows."""
    for k, top in enumerate(SPONSOR_KINDS):
        if capacity <= top:
            return SPONSOR_FEWEST + k
    return SPONSOR_BOARDS


def ground_sizes():
    """{stadium id: capacity in thousands} as --mod real-grounds has them."""
    import initteam
    sizes = {}
    for band, ids in initteam.ground_bands().items():
        for i in ids:
            sizes[i] = 40 if band == "small 40" else band
    return sizes


def sponsor_boards(data):
    """BUILD_STADIUM.TBB bytes with every stadium's 12 advert textures but
    the rival's drawn from SPONSOR_LOGOS: sponsor_count(its size) different
    ones, each on at least one board, in a random order; None when they
    already are. The file keeps its size."""
    import random
    _, t = tbb.parse(data)
    old = rows(t[0].data, BUILD_ROW)
    base = t[0].offset + t[0].data_offset
    out = bytearray(data)
    sizes = ground_sizes()
    for i in range(len(old)):
        if i == RIVAL_STADIUM:
            continue
        rng = random.Random(SPONSOR_SEED * 1000 + i)
        kinds = rng.sample(SPONSOR_LOGOS, sponsor_count(sizes.get(i, 40)))
        boards = kinds + [rng.choice(kinds) for _ in range(SPONSOR_BOARDS - len(kinds))]
        rng.shuffle(boards)
        at = base + i * BUILD_ROW
        out[at + BUILD_ADVERT.start:at + BUILD_ADVERT.stop] = bytes(boards)
    return None if bytes(out) == data else bytes(out)


# --- the writer --------------------------------------------------------------
# setlook and setboards edit table 0 in place (the file keeps its size);
# copy_rows above is the look, BOARD_VALUES the advert bytes' values.
BOARD_VALUES = SPONSOR_LOGOS        # 206 and up all mean adidas, which the match adds itself


def table_rows(data):
    """The table-0 rows of BUILD_STADIUM.TBB bytes, and where row 0 starts."""
    _, t = tbb.parse(data)
    return rows(t[0].data, BUILD_ROW), t[0].offset + t[0].data_offset


def look(row):
    """A row's look: every byte but the 12 advert textures."""
    return row[:BUILD_ADVERT.start] + row[BUILD_ADVERT.stop:]


def set_look(data, pairs):
    """BUILD_STADIUM.TBB bytes with each stadium `dst` of `pairs` ({dst:
    src}) built like stadium `src` as the rows were (copy_rows); the bytes
    unchanged when every one already is."""
    old, _ = table_rows(data)
    for d, s in pairs.items():
        for i in (d, s):
            if not 0 <= i < len(old):
                raise ValueError("stadium %d: there are %d (0-%d)" % (i, len(old), len(old) - 1))
    return copy_rows(data, pairs) or data


def set_boards(data, boards):
    """BUILD_STADIUM.TBB bytes with each stadium of `boards` ({id: 12
    values}) showing those advert textures: value v is SPONSOR_TEXTURE_M
    logo v - 1 (0x1d31b8)."""
    old, base = table_rows(data)
    out = bytearray(data)
    for i, values in boards.items():
        if not 0 <= i < len(old):
            raise ValueError("stadium %d: there are %d (0-%d)" % (i, len(old), len(old) - 1))
        values = list(values)
        if len(values) != BUILD_ADVERT.stop - BUILD_ADVERT.start:
            raise ValueError("stadium %d: %d boards, expected 12" % (i, len(values)))
        bad = [v for v in values if v not in BOARD_VALUES]
        if bad:
            raise ValueError("stadium %d: board %s not %d-%d (%d and up is adidas, which the "
                             "match adds by itself)" % (i, bad[0], BOARD_VALUES[0],
                                                        BOARD_VALUES[-1], BOARD_VALUES[-1] + 1))
        at = base + i * BUILD_ROW
        out[at + BUILD_ADVERT.start:at + BUILD_ADVERT.stop] = bytes(values)
    return bytes(out)


def keep_edits(old, mine, switched):
    """BUILD_STADIUM.TBB bytes for a target file `mine` that an LMASTER
    switch also edits: `switched` is the switch's edit of `old`, the file
    the target was made from. Each row's look and its boards are the
    target's where the target changed them from `old`, else the switch's,
    so an editor's own edit wins row by row."""
    o, base = table_rows(old)
    m, _ = table_rows(mine)
    s, _ = table_rows(switched)
    if len(o) != len(m) or len(o) != len(s) or len(old) != len(mine):
        raise ValueError("BUILD_STADIUM.TBB: the target's tables differ in size")
    out = bytearray(mine)
    for i in range(len(o)):
        row = bytearray(m[i])
        if look(m[i]) == look(o[i]):
            row[:BUILD_ADVERT.start] = s[i][:BUILD_ADVERT.start]
            row[BUILD_ADVERT.stop:] = s[i][BUILD_ADVERT.stop:]
        if m[i][BUILD_ADVERT] == o[i][BUILD_ADVERT]:
            row[BUILD_ADVERT] = s[i][BUILD_ADVERT]
        out[base + i * BUILD_ROW:base + (i + 1) * BUILD_ROW] = row
    return bytes(out)


class Build:
    def __init__(self, path):
        _, t = tbb.load(path)
        if len(t) != 3:
            raise ValueError("%d tables, expected 3" % len(t))
        self.tables = t
        self.rows = rows(t[0].data, BUILD_ROW)
        self.model_rows = list(t[1].rows())
        self.t2 = rows(t[2].data, T2_ROW)

    def problems(self, stand_nodes=None, shadows=None, walls=None):
        out = []
        bad = [i for i, r in enumerate(self.rows) if r[0] >= len(MODELS)]
        if bad:
            out.append("model index >= %d in rows %s" % (len(MODELS), bad))
        bad = [i for i, r in enumerate(self.rows)
               if r[BUILD_CROWD] >= len(CROWD_SETS) or CROWD_SETS[r[BUILD_CROWD]][0] != r[0]]
        if bad:
            out.append("crowd set doesn't match the model in rows %s" % bad)
        if len(self.model_rows) != len(MODELS) or self.tables[1].line_size != MONTHS:
            out.append("table 1 is %d x %d, expected %d x %d" % (
                len(self.model_rows), self.tables[1].line_size, len(MODELS), MONTHS))
        if len(self.t2) != len(VARIANTS):
            out.append("table 2 has %d rows, expected %d" % (len(self.t2), len(VARIANTS)))
        if stand_nodes is not None:
            for v, row in enumerate(self.t2):
                for m in range(len(MODELS)):
                    for e in row[m * T2_ENTRY:(m + 1) * T2_ENTRY]:
                        want = "%s_%s_" % (MODELS[m][1:], VARIANTS[v])
                        if e != 0xff and (e >= len(stand_nodes) or not stand_nodes[e].startswith(want)):
                            out.append("table 2 %s %s: node list %d" % (VARIANTS[v], MODELS[m], e))
        if shadows is not None:
            bad = [i for i, r in enumerate(self.rows) if any(x >= shadows for x in r[BUILD_SHADOW])]
            if bad:
                out.append("SHADOWCOLLI entry out of range in rows %s" % bad)
        if walls is not None:
            bad = [i for i, r in enumerate(self.rows) if r[BUILD_WALL] >= walls]
            if bad:
                out.append("WALLCOLLI entry out of range in rows %s" % bad)
        return out


class Crowd:
    """One AUD_SET_<model>_<n>.TBB."""

    def __init__(self, path):
        _, t = tbb.load(path)
        if len(t) != 12:
            raise ValueError("%d tables, expected 12" % len(t))
        self.sections = [struct.unpack_from("<HHI", r) for r in rows(t[0].data, 8)]
        if len(self.sections) != AUD_SECTIONS:
            raise ValueError("table 0 has %d sections" % len(self.sections))
        self.section_rows = [t[k].data for k in range(1, 1 + AUD_SECTIONS)]
        self.blocks = []
        for r in rows(t[10].data, AUD_BLOCK):
            name = r[:AUD_NAME].split(b"\0")[0].decode("latin1")
            self.blocks.append((name, r[AUD_NAME], r[AUD_NAME + 1], r[AUD_NAME + 2], r))
        self.last = t[11].data

    def problems(self):
        out = []
        for name, sec, tier, _, _ in self.blocks:
            if not name:
                out.append("unnamed block")
            elif sec >= AUD_SECTIONS:
                out.append("block %s: section %d" % (name, sec))
            elif tier >= self.sections[sec][1]:
                out.append("block %s: tier %d >= %d" % (name, tier, self.sections[sec][1]))
        for sec, (_, tiers, _) in enumerate(self.sections):
            data = self.section_rows[sec]
            if tiers * 8 > len(data):
                out.append("section %d: %d tiers but %d rows" % (sec, tiers, len(data) // 8))
                continue
            for t in range(tiers):
                cap, _, flag, zero = struct.unpack_from("<IHBB", data, 8 * t)
                if cap == 0 or flag > 1 or zero:
                    out.append("section %d tier %d: %08x" % (sec, t, cap))
        if len(self.last) != 1:
            out.append("table 11 is %d bytes" % len(self.last))
        return out


def find(root, name):
    """Case-insensitive lookup; the disc names are upper case."""
    for f in os.listdir(root):
        if f.lower() == name.lower():
            return os.path.join(root, f)
    return None


def pack_names(root, name):
    p = find(root, name)
    h = pac.load_header(p) if p else None
    return [e[2] for e in h.entries] if h else None


def crowd_model_forms(path):
    """{model name: form} for one AUD_MODEL pack. 0x1d5340 takes a model
    with 2 or more materials and 3 or more nodes as a three-group crowd
    ("groups"): its nodes 1-3 are the figure groups AUD_JAM_HI thins
    (0x1d836c), and its materials 0 and 1 take the tier's two crowd kinds
    (0x1d83dc). Any other model ("single") is drawn with material 0 in the
    tier's main kind (0x1d84e8). "empty" has no meshes."""
    import ninja
    out = {}
    for label, blob in ninja._iter_blobs([path], prs=True):
        nf = ninja.NinjaFile(blob)
        for c in nf.chunks:
            if c[0] in ninja.OBJECT_CHUNKS:
                o = ninja.NinjaObject(nf, nf.main_struct(c))
                out[label.split(":", 1)[-1].lower()] = (
                    "empty" if not o.meshes else
                    "groups" if o.nmat >= CROWD_GROUP_MATS and o.nnode >= CROWD_GROUP_NODES
                    else "single")
    return out


def report(path, line, probs):
    if probs:
        line += "  !! " + "; ".join(probs)
    print("%-40s %s" % (path, line))


def check(path, fn):
    """Run fn(path) -> (line, problems); parse errors become a !! line."""
    if path is None:
        return None
    try:
        return fn(path)
    except (ValueError, struct.error) as e:
        report(path, "", [str(e)])
        return None


def cmd_info(root, param):
    for m in MODELS:
        path = find(root, m + ".pri")
        if path is None:
            report(os.path.join(root, m.upper() + ".PRI"), "", ["missing"])
            continue
        try:
            v = read_pri(path)
        except (ValueError, struct.error) as e:
            report(path, "", [str(e)])
            continue
        report(path, "priorities %3d-%3d, %2d in the first pass" % (
            min(v), max(v), sum(p < PRI_PASS for p in v)),
            ["priority > %d is never drawn" % PRI_MAX] if max(v) > PRI_MAX else [])

    for m in MODELS:
        missing = [pre + m + suf + ext for pre, suf in MODEL_PACKS for ext in (".pac", ".hed")
                   if find(root, pre + m + suf + ext) is None]
        counts = [len(pack_names(root, pre + m + suf + ".pac") or []) for pre, suf in MODEL_PACKS]
        print("  model %d %s  packs %s%s" % (MODELS.index(m), m, "/".join(map(str, counts)),
                                             "  !! missing " + ", ".join(missing) if missing else ""))

    b = check(find(root, "build_stadium.tbb"), Build)
    if b is not None:
        use = Counter(r[0] for r in b.rows)
        game = os.path.join(os.path.dirname(os.path.abspath(root)), "GAME")
        counts = []
        for name in ("shadowcolli.hed", "wallcolli.hed"):
            path = find(game, name) if os.path.isdir(game) else None
            h = pac.load_header(path) if path else None
            counts.append(h.count if h else None)
        probs = b.problems(pack_names(root, "stand_node_name.pac"), *counts)
        if param and find(param, "stadium_data.tbb"):
            _, t = tbb.load(find(param, "stadium_data.tbb"))
            if t[0].size // STADIUM_DATA_ROW != len(b.rows):
                probs.append("PARAM/STADIUM_DATA has %d stadiums" % (t[0].size // STADIUM_DATA_ROW))
        report(find(root, "build_stadium.tbb"), "%d stadiums; per model %s" % (
            len(b.rows), " ".join("%d:%d" % (k, use[k]) for k in sorted(use))), probs)

    def conv(path):
        _, t = tbb.load(path)
        ids = t[0].data
        probs = []
        if len(ids) != CONV_ROWS * CONV_LEVELS * CONV_VARIANTS:
            probs.append("%d bytes, expected %d" % (len(ids), CONV_ROWS * CONV_LEVELS * CONV_VARIANTS))
        n = len(b.rows) if b else 0
        for i, s in enumerate(ids):
            level = (i // CONV_VARIANTS) % CONV_LEVELS
            if s >= n:
                probs.append("entry %d: stadium %d" % (i, s))
            elif not MODELS[b.rows[s][0]].startswith("ho0%d" % level):
                probs.append("entry %d: level %d stadium %d uses %s" % (i, level, s, MODELS[b.rows[s][0]]))
        return report(path, "%d stadium ids, %d distinct" % (len(ids), len(set(ids))), probs)
    check(find(root, "conv_info_build.tbb"), conv)

    def advert(path):
        _, t = tbb.load(path)
        recs = [struct.unpack("<4h", r) for r in rows(t[0].data, ADVERT_ROW)]
        probs = []
        for i, (ty, alt, link, part) in enumerate(recs):
            if not (0 <= ty < len(ADVERT_TYPES) and 0 <= alt < len(ADVERT_TYPES)):
                probs.append("row %d: type %d/%d" % (i, ty, alt))
            if link != -1 and not 0 <= link < len(recs):
                probs.append("row %d: link %d" % (i, link))
            if not 0 < part < BUILD_ROW:
                probs.append("row %d: part byte %d" % (i, part))
        mp = find(root, "advertise_modelpack.tbb")
        names = rows(tbb.load(mp)[1][0].data, MODELPACK_ROW) if mp else []
        if len(names) != len(recs):
            probs.append("ADVERTISE_MODELPACK has %d names" % len(names))
        for m in MODELS:
            for v in VARIANTS:
                got = pack_names(root, "adt_%s_%s.pac" % (m, v))
                if got is not None and len(got) != len(recs):
                    probs.append("ADT_%s_%s has %d boards" % (m.upper(), v.upper(), len(got)))
        types = Counter(ADVERT_TYPES[r[0]] for r in recs if 0 <= r[0] < len(ADVERT_TYPES))
        return report(path, "%d boards: %s" % (len(recs), ", ".join(
            "%s %d" % kv for kv in sorted(types.items()))), probs)
    check(find(root, "build_advertise.tbb"), advert)

    def jam(path, size, field):
        _, t = tbb.load(path)
        probs, shapes = [], []
        for tab in t:
            recs = rows(tab.data, size)
            th = [struct.unpack_from("<H", r, 2 * field)[0] for r in recs]
            shapes.append(str(len(recs)))
            if th != sorted(th) or max(th) > JAM_ONE:
                probs.append("table %d thresholds not ascending within 0-%d" % (tab.index, JAM_ONE))
        return report(path, "%d table(s) of %s rows" % (len(t), "/".join(shapes)), probs)
    check(find(root, "aud_jam_hi.tbb"), lambda p: jam(p, JAM_HI_ROW, 4))
    check(find(root, "aud_jam_lw.tbb"), lambda p: jam(p, JAM_LW_ROW, 0))

    expected = {"aud_set_%s_%d.tbb" % (MODELS[m], n) for m, n in CROWD_SETS}
    present = {f.lower() for f in os.listdir(root)
               if f.lower().startswith("aud_set_") and f.lower().endswith(".tbb")}
    for f in sorted(present - expected):
        report(os.path.join(root, f.upper()), "", ["not one of the 18 crowd sets"])
    for f in sorted(expected - present):
        report(os.path.join(root, f.upper()), "", ["missing"])
    forms = {}                      # AUD_MODEL pack -> crowd_model_forms
    # Sets a stadium with LIGHT_1 uses, so seen in N2 at night.
    night2 = {r[BUILD_CROWD] for r in b.rows if r[BUILD_NIGHT2]} if b else set()
    for idx, (m, n) in enumerate(CROWD_SETS):
        def crowd(path):
            c = Crowd(path)
            probs = c.problems()
            share = sum(s[0] for s in c.sections)
            kinds = Counter()
            for v in VARIANTS:
                pack = find(root, "aud_model_%s_%s.pac" % (MODELS[m], v))
                if pack is None:
                    continue
                if pack not in forms:
                    forms[pack] = crowd_model_forms(pack)
                names = ["%s_%s_aud_%s.snj" % (MODELS[m], v, x[0]) for x in c.blocks]
                lost = [x[0] for x, k in zip(c.blocks, names) if k not in forms[pack]]
                if lost:
                    probs.append("no model for %s in AUD_MODEL_%s_%s" % (
                        " ".join(lost), MODELS[m].upper(), v.upper()))
                empty = [x[0] for x, k in zip(c.blocks, names) if forms[pack].get(k) == "empty"]
                if empty and (v != "n2" or idx in night2):
                    probs.append("empty model for %s in AUD_MODEL_%s_%s" % (
                        " ".join(empty), MODELS[m].upper(), v.upper()))
                if v == "d1":
                    kinds.update(("hi" if x[2] < c.last[0] else "lw", forms[pack].get(k))
                                 for x, k in zip(c.blocks, names))
                elif v == "n2" and empty:
                    kinds["n2 empty"] = len(empty)
            return report(path, "set %2d: %2d blocks, shares %d/%d; high-detail tiers %d "
                          "three-group, %d single; low %d single, %d three-group%s" % (
                              idx, len(c.blocks), share, JAM_ONE, kinds[("hi", "groups")],
                              kinds[("hi", "single")], kinds[("lw", "single")],
                              kinds[("lw", "groups")], "; N2 empty %d (no N2 stadium)" %
                              kinds["n2 empty"] if kinds["n2 empty"] else ""), probs)
        check(find(root, "aud_set_%s_%d.tbb" % (MODELS[m], n)), crowd)


def cmd_pri(path):
    for i, p in enumerate(read_pri(path)):
        print("  slot %2d  priority %3d  pass %d" % (i, p, 1 if p < PRI_PASS else 2))


def cmd_build(root, sid):
    b = Build(find(root, "build_stadium.tbb"))
    r = b.rows[sid]
    m = r[0]
    print("stadium %d: model %d (%s)" % (sid, m, MODELS[m] if m < len(MODELS) else "?"))
    for lo, hi, step, slot, pack, entry, estep, what in PARTS:
        vals = [r[k] for k in range(lo, hi + 1, step)]
        if any(vals):
            print("  bytes %3d-%3d  slot %2d %-16s %-5s %2d+  %-45s %s" % (
                lo, hi, slot, SLOT_NAMES[slot], pack, entry, what, " ".join("%x" % v for v in vals)))
    print("  night variant: %s (byte %d, LIGHT_1)" % ("N2" if r[BUILD_NIGHT2] else "N1", BUILD_NIGHT2))
    print("  advert switches (42-69, 94-97): %s %s" % (r[42:70].hex(), r[94:98].hex()))
    print("  shadow collision (110-114): %s  wall collision (128): %d" % (
        " ".join(str(x) for x in r[BUILD_SHADOW]), r[BUILD_WALL]))
    cs = r[BUILD_CROWD]
    if cs < len(CROWD_SETS):
        print("  byte 115 crowd set: %d (AUD_SET_%s_%d)" % (
            cs, MODELS[CROWD_SETS[cs][0]].upper(), CROWD_SETS[cs][1]))
    print("  bytes 116-127 advert textures: %s" % " ".join(str(x) for x in r[BUILD_ADVERT]))
    if m < len(b.model_rows):
        print("  model row (table 1): %s" % " ".join(str(x) for x in b.model_rows[m]))
        for k, row in enumerate(b.t2):
            print("  stand node lists %s: %s" % (VARIANTS[k], row[m * T2_ENTRY:(m + 1) * T2_ENTRY].hex(" ")))


def cmd_crowd(path):
    c = Crowd(path)
    for i, (share, tiers, _) in enumerate(c.sections):
        print("  section %d  share %4d/%d  tiers %d  rows %s" % (
            i, share, JAM_ONE, tiers, c.section_rows[i].hex(" ")))
    for name, sec, tier, flag, r in c.blocks:
        print("  block %-4s section %d tier %d flag %d  %s" % (name, sec, tier, flag, r[AUD_NAME + 3:].hex(" ")))
    print("  table 11: %s" % c.last.hex(" "))


def write_out(path, out_path, edit):
    """Read `path`, write edit(bytes) to `out_path` (never the input)."""
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(path, "rb") as f:
        data = f.read()
    try:
        out = edit(data)
    except ValueError as e:
        raise SystemExit(str(e))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_setlook(path, out_path, args):
    pairs = {}
    for a in args:
        try:
            d, s = (int(x, 0) for x in a.split("="))
        except ValueError:
            raise SystemExit("%s: expected <id>=<src id>" % a)
        pairs[d] = s
    with open(path, "rb") as f:
        old, _ = table_rows(f.read())
    for d, s in sorted(pairs.items()):
        if 0 <= s < len(old):
            print("stadium %d: built like stadium %d (model %s)" % (
                d, s, MODELS[old[s][0]] if old[s][0] < len(MODELS) else old[s][0]))
    write_out(path, out_path, lambda data: set_look(data, pairs))


def cmd_setboards(path, out_path, args):
    """args: one or more groups of <id> <v1> ... <v12>."""
    group = 1 + BUILD_ADVERT.stop - BUILD_ADVERT.start
    if not args or len(args) % group:
        raise SystemExit("setboards takes <id> and 12 board values, as often as you like")
    try:
        nums = [int(a, 0) for a in args]
    except ValueError as e:
        raise SystemExit(str(e))
    boards = {nums[k]: nums[k + 1:k + group] for k in range(0, len(nums), group)}
    for i, v in sorted(boards.items()):
        print("stadium %d: boards %s" % (i, " ".join(map(str, v))))
    write_out(path, out_path, lambda data: set_boards(data, boards))


def cmd_roundtrip(paths):
    """Edit each row on its own, its look and then its boards, and check
    that nothing outside the edited bytes changes, and that putting a row's
    own values back gives the file unchanged."""
    for path in paths:
        if os.path.isdir(path):
            path = find(path, "build_stadium.tbb") or os.path.join(path, "BUILD_STADIUM.TBB")
        try:
            with open(path, "rb") as f:
                data = f.read()
            old, base = table_rows(data)
        except (OSError, ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            continue
        n, probs = len(old), []
        for i in range(n):
            lo, hi = base + i * BUILD_ROW, base + (i + 1) * BUILD_ROW
            ads = range(lo + BUILD_ADVERT.start, lo + BUILD_ADVERT.stop)
            if set_look(data, {i: i}) != data or set_boards(data, {i: old[i][BUILD_ADVERT]}) != data:
                probs.append("row %d: its own values back don't give the same file" % i)
            src = (i + 1) % n
            new = set_look(data, {i: src})
            moved = [k for k in range(len(data)) if new[k] != data[k]]
            if any(not lo <= k < hi or k in ads for k in moved) or len(new) != len(data):
                probs.append("row %d: setlook changed bytes outside its look" % i)
            elif look(table_rows(new)[0][i]) != look(old[src]):
                probs.append("row %d: setlook didn't copy row %d's look" % (i, src))
            want = [BOARD_VALUES[(v + i) % len(BOARD_VALUES)] for v in range(12)]
            new = set_boards(data, {i: want})
            moved = [k for k in range(len(data)) if new[k] != data[k]]
            if any(k not in ads for k in moved) or len(new) != len(data):
                probs.append("row %d: setboards changed bytes outside its boards" % i)
            elif list(table_rows(new)[0][i][BUILD_ADVERT]) != want:
                probs.append("row %d: setboards didn't write the boards" % i)
        for p in probs:
            print("%s  !! %s" % (path, p))
        if not probs:
            print("%s  %d bytes, %d rows: each row's look and boards edited on its own, "
                  "nothing else changed" % (path, len(data), n))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) in (1, 2):
        cmd_info(args[0], args[1] if len(args) == 2 else None)
    elif cmd == "pri" and len(args) == 1:
        cmd_pri(args[0])
    elif cmd == "build" and len(args) == 2:
        cmd_build(args[0], int(args[1], 0))
    elif cmd == "crowd" and len(args) == 1:
        cmd_crowd(args[0])
    elif cmd == "setlook" and len(args) >= 3:
        cmd_setlook(args[0], args[1], args[2:])
    elif cmd == "setboards" and len(args) >= 3:
        cmd_setboards(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and args:
        cmd_roundtrip(args)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
