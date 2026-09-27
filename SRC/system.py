# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""DAT/0SYSTEM checker for Let's Make a Soccer Team! (PS2).

DAT/0SYSTEM (folder id 0, set up at 0x14eb4c) holds the game-wide tables,
texture packs and fonts. See DOC/0SYSTEM_DIR.md.

  COLORDATATABLE.TBB    77 x RGBA8888 UI colours. etc::InitializeGameSystem
                        (0x149a90) reads it; clr::SetTbbFileBuffer (0x1f8e08)
                        counts size / 4; clr::GetRGBA(id) returns one.
  DETAILFLAG.TBB        528 one-byte flags (0-3). WP::CDetailManager
                        (0x283610) copies the first 99 into itself.
  *_TEXTURE*.PAC        8 packs of SVR textures, one per
                        CFcEuro_CommonTexture type (names at 0x34d3f8):
                        0 EMBLEM, 1 FLAG, 2 MATCH, 3 MINIMATCH, 4 MINIEMBLEM,
                        5 SPONSOR, 6 SPONSOR_M, 7 SPONSOR_S. The entry is
                        picked from a team, competition or sponsor id by
                        ConvertFlag / ConvertIndex (0x1057e8, 0x105c70).
  FONT_*.SVR            CFontTexture_fc_euro::LoadTexture (0x149108): language
                        0 loads kanji, ascii, 8_a, 8_b (0x35d400); the others
                        20_a, 8_a, 8_b (0x35d458).
  STATIC*.ICO           memory-card icons (MC::CFcEuroIF::setFileInfo,
                        SAVEPRG.REL).
  SAVE_VERSION.DAT      a text note, loaded by the root module's list.

`info` checks the layouts and the entry naming the index conversions rely
on. `colors` prints the colour table. `emblem` gives the pack entry for a
team id.

Usage:
    python system.py info   <DAT/0SYSTEM>
    python system.py colors <DAT/0SYSTEM>
    python system.py emblem <DAT/0SYSTEM> <team id> ...
"""
import os
import re
import struct
import sys

from pac import load_header
import tbb

# CFcEuro_CommonTexture types, in the order of the name table at 0x34d3f8.
TEXTURE_PACKS = ["EMBLEM_TEXTURE", "FLAG_TEXTURE", "MATCH_TEXTURE", "MINIMATCH_TEXTURE",
                 "MINIEMBLEM_TEXTURE", "SPONSOR_TEXTURE", "SPONSOR_TEXTURE_M",
                 "SPONSOR_TEXTURE_S"]
TEXTURE_COUNTS = [634, 634, 70, 70, 10, 232, 232, 232]
N_COLORS = 0x4d         # clr::SetTbbFileBuffer(buf, 0x4d) at 0x149b0c
DETAIL_FLAGS = 528
DETAIL_USED = 0x63      # bytes CDetailManager copies (0x283668-0x283714)

# Emblem entries: teams 3-459 are clubs C003-C459, 460-542 map through
# plMisc_NatiTeam2Nati to N001-N145 (+0x1cb), 543+ to V001-V032 (+0x3e);
# then minus 3 (ConvertIndex 0x105dc4).
FIRST_TEAM = 3
NATION_TEAM = 0x1cc     # 460
SPECIAL_TEAM = 0x21f    # 543
ICON_MAGIC = 0x00010000


def emblem_names():
    return (["emb_C%03d.svr" % t for t in range(FIRST_TEAM, NATION_TEAM)]
            + ["emb_N%03d.svr" % n for n in range(1, 146)]
            + ["emb_V%03d.svr" % n for n in range(1, 33)])


def read_pack(path):
    hdr = load_header(path)
    with open(path, "rb") as f:
        data = f.read()
    return hdr, data


def colors(path):
    """(list of RGBA tuples, tables) of COLORDATATABLE.TBB."""
    _, tables = tbb.load(path)
    data = tables[0].data
    return [tuple(data[i:i + 4]) for i in range(0, len(data) - len(data) % 4, 4)], tables


# --- commands ----------------------------------------------------------------

def check_colors(d):
    path = os.path.join(d, "COLORDATATABLE.TBB")
    problems = []
    try:
        cols, tables = colors(path)
    except (ValueError, struct.error) as e:
        return "COLORDATATABLE.TBB  !! %s" % e
    t = tables[0]
    if len(tables) != 1:
        problems.append("%d tables, expected 1" % len(tables))
    if len(t.data) % 4:
        problems.append("size %d not a whole number of colours" % len(t.data))
    if len(cols) != N_COLORS:
        problems.append("%d colours, the game expects %d" % (len(cols), N_COLORS))
    alphas = sorted({c[3] for c in cols})
    line = "COLORDATATABLE.TBB  %d colours, alpha values %s" % (
        len(cols), " ".join("%02x" % a for a in alphas))
    return line + ("  !! " + "; ".join(problems) if problems else "")


def check_detail(d):
    path = os.path.join(d, "DETAILFLAG.TBB")
    try:
        _, tables = tbb.load(path)
    except (ValueError, struct.error) as e:
        return "DETAILFLAG.TBB  !! %s" % e
    data = tables[0].data
    problems = []
    if len(tables) != 1 or len(data) != DETAIL_FLAGS:
        problems.append("%d tables, %d bytes; expected 1 table of %d"
                        % (len(tables), len(data), DETAIL_FLAGS))
    if len(data) < DETAIL_USED:
        problems.append("shorter than the %d bytes CDetailManager copies" % DETAIL_USED)
    vals = {v: data.count(v) for v in sorted(set(data))}
    if max(vals) > 3:
        problems.append("values above 3")
    line = "DETAILFLAG.TBB  %d flags, values %s" % (
        len(data), ", ".join("%d x%d" % (v, n) for v, n in vals.items()))
    return line + ("  !! " + "; ".join(problems) if problems else "")


def check_texture_packs(d):
    out = []
    packs = {}
    for typ, (name, want) in enumerate(zip(TEXTURE_PACKS, TEXTURE_COUNTS)):
        path = os.path.join(d, name + ".PAC")
        try:
            hdr, data = read_pack(path)
        except (OSError, ValueError, struct.error) as e:
            out.append("%-24s !! %s" % (name + ".PAC", e))
            continue
        names = [e[2] for e in hdr.entries]
        problems = []
        if len(names) != want:
            problems.append("%d entries, expected %d" % (len(names), want))
        bad = [i for i, (o, s, n, x) in enumerate(hdr.entries) if data[o:o + 4] != b"GBIX"]
        if bad:
            problems.append("%d entries aren't SVR textures (first #%d)" % (len(bad), bad[0]))
        if typ in (0, 1) and names != emblem_names():
            problems.append("names aren't C003-C459, N001-N145, V001-V032 in order")
        if typ in (5, 6, 7):
            nums = [int(m.group(1)) if m else -1
                    for m in (re.search(r"_(\d{3})\.svr$", n, re.I) for n in names)]
            if nums != list(range(len(names))):
                problems.append("names aren't numbered 000-%03d in order" % (len(names) - 1))
        if typ == 4 and names != ["emb_sc%d.svr" % i for i in range(1, 8)] + \
                ["emb_sn%d.svr" % i for i in range(1, 4)]:
            problems.append("names aren't emb_sc1-7, emb_sn1-3")
        packs[typ] = (hdr, data, names)
        line = "%-24s type %d  %4d entries" % (name + ".PAC", typ, len(names))
        out.append(line + ("  !! " + "; ".join(problems) if problems else ""))
    # MATCH and MINIMATCH are the same badges, large and small.
    if 2 in packs and 3 in packs:
        big = [re.sub(r"_L\.svr$", "", n) for n in packs[2][2]]
        small = [re.sub(r"_S\.svr$", "", n) for n in packs[3][2]]
        if big != small:
            out.append("  !! MATCH_TEXTURE and MINIMATCH_TEXTURE name different badges")
        # ConvertIndex (0x105d64-0x105da4): exhibition -> 56 + language,
        # competition 0x30 -> 63 + language.
        want = ["EXHIBITION_%d" % i for i in range(7)] + ["YOUTH_LEAGUE_%d" % i for i in range(7)]
        if big[56:70] != want:
            out.append("  !! entries 56-69 aren't EXHIBITION_0-6, YOUTH_LEAGUE_0-6")
    # EMBLEM and FLAG: same layout, a few crests differ.
    if 0 in packs and 1 in packs:
        (h0, d0, n0), (h1, d1, n1) = packs[0], packs[1]
        diff = [n0[i] for i, (a, b) in enumerate(zip(h0.entries, h1.entries))
                if d0[a[0]:a[0] + a[1]] != d1[b[0]:b[0] + b[1]]]
        out.append("  EMBLEM vs FLAG: %d %s differ%s" % (
            len(diff), "entry" if len(diff) == 1 else "entries",
            " (%s)" % ", ".join(diff) if diff else ""))
    return out


def check_icons(d):
    out = []
    for name in ("STATIC.ICO", "STATIC_VS.ICO"):
        path = os.path.join(d, name)
        with open(path, "rb") as f:
            head = f.read(20)
        magic, shapes, tex_type, _, verts = struct.unpack_from("<IIIfI", head)
        line = "%-16s %d shape(s), texture type %d, %d vertices" % (name, shapes, tex_type, verts)
        if magic != ICON_MAGIC:
            line += "  !! not a PS2 icon (magic 0x%08x)" % magic
        out.append(line)
    return out


def cmd_info(d):
    print(check_colors(d))
    print(check_detail(d))
    for line in check_texture_packs(d):
        print(line)
    for line in check_icons(d):
        print(line)
    path = os.path.join(d, "SAVE_VERSION.DAT")
    text = open(path, "rb").read().decode("latin1")
    print("SAVE_VERSION.DAT  %s" % " / ".join(l.strip() for l in text.splitlines() if l.strip()))


def cmd_colors(d):
    cols, _ = colors(os.path.join(d, "COLORDATATABLE.TBB"))
    for i, (r, g, b, a) in enumerate(cols):
        print("%3d  #%02x%02x%02x  alpha %02x" % (i, r, g, b, a))


def emblem_entry(team):
    """Pack entry name for a club or special team id; nations need the
    nation number (plMisc_NatiTeam2Nati), so give 'N<n>' for those."""
    if FIRST_TEAM <= team < NATION_TEAM:
        return "emb_C%03d.svr" % team
    if team >= SPECIAL_TEAM:
        return "emb_V%03d.svr" % (team - SPECIAL_TEAM + 1)
    return None


def cmd_emblem(d, teams):
    hdr, _ = read_pack(os.path.join(d, "EMBLEM_TEXTURE.PAC"))
    names = [e[2] for e in hdr.entries]
    for arg in teams:
        if arg.upper().startswith("N"):
            name = "emb_N%03d.svr" % int(arg[1:])
        else:
            name = emblem_entry(int(arg, 0))
        if name is None or name not in names:
            print("%s: no emblem entry (ids 0-2 are placeholders; for a nation, "
                  "team 460-542, give its nation number as N<n>)" % arg)
            continue
        print("%s: entry %d, %s" % (arg, names.index(name), name))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "colors" and len(args) == 1:
        cmd_colors(args[0])
    elif cmd == "emblem" and len(args) >= 2:
        cmd_emblem(args[0], args[1:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
