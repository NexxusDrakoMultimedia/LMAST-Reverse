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

Usage:
    python emblem.py info   <DAT/EMBLEM>
    python emblem.py colors <DAT/EMBLEM>
    python emblem.py crests <DAT/EMBLEM> [7|8|9]
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


def trs(raw):
    """Param::PlEmblemTrs, 8 bytes {s8 tx, s8 ty, s16 rot, u8 rev, u8 sx,
    u8 sy, pad} (field table 0x53cd08-0x53cde4)."""
    return dict(zip(("tx", "ty", "rot", "rev", "sx", "sy"), struct.unpack("<bbhBBB", raw[:7])))


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
    if any(s >= rows[7] for s in initial_samples):
        problems.append("t10 names a sample past t7's %d rows" % rows[7])
    else:
        # Each initial crest is its t10 sample's parts, with its own colours.
        samples7, initial = crests(t, 7), crests(t, 8)
        keys = ("sample", "base", "mask", "pattern", "acce", "layer_key")
        differ = [i for i, s in enumerate(initial_samples[:len(initial)])
                  if any(initial[i][k] != samples7[s][k] for k in keys)]
        if differ:
            problems.append("initial crests %s don't use their t10 sample's parts" % differ[:5])
    for i in range(rows[11]):
        own, c1, c2 = struct.unpack_from("<3b", t[11].data, 3 * i)
        if own != i or not (0 <= c1 < 32 and 0 <= c2 < 32):
            problems.append("t11 row %d is %d %d %d, expected %d and two 32-colour ids" % (
                i, own, c1, c2, i))
            break
    out.append(problems_line("  t10/t11: %d initial crests' samples and first colours" % rows[10],
                             problems))
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
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
