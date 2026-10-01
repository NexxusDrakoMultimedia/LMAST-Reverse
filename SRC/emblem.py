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
                      10-byte presets, t7-t9 110-byte samples / initial /
                      rival crests, t10 a byte per initial crest, t11 three
                      colour ids per initial crest, t12-t143 layer
                      accessories, table 12 + 4 * sample + layer.
  EDIT_EMBLEM_A/M/P   217 accessories, 214 masks, 22 patterns: 128x128 4bpp
                      SVRs, loaded one entry at a time (SIMPRG 0x107380).
  EDIT_FLAG.*         EDIT::CFlagData (0x104578-0x1045e8): t0 49 flag bases
                      (u32), t1 71 patterns (u16), t2 27 crest placements;
                      the pack holds the 49 bases.
  EDIT_PLAYER.TBB     32 tables, loaded by PLAYEREDIT_MODULE (YRSTPRG.REL);
                      not decoded.

`info` checks the layouts and the counts the tables and packs share.
`colors` lists the 96 colours with their 32- and 16-colour ids.

Usage:
    python emblem.py info   <DAT/EMBLEM>
    python emblem.py colors <DAT/EMBLEM>
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
    # Layer accessory tables, 12 + 4 * sample + layer. The reader walks
    # GetDataTableCount records of 12 bytes (0x1041bc-0x104230).
    samples = (len(t) - LAYER_BASE) // LAYERS
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


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "colors" and len(args) == 1:
        cmd_colors(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
