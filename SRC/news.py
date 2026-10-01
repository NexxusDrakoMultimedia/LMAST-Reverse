# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""DAT/NEWS checker for Let's Make a Soccer Team! (PS2).

DAT/NEWS (folder id 15) holds the newspaper's pictures and one table. See
DOC/NEWS_DIR.md.

  NEWS_AD/CARTOON/OTHER.PAC   35, 15 and 2 small SVRs. NEWS::CFactory
                              (SIMPRG.REL 0x24868) requests every entry by
                              index, with header types 0, 1 and 4.
  NEWS_TITLE.PAC              24 mastheads, 4 per league: entry 4 * league
                              + 0..3 = paper 1, paper 2, special edition 1,
                              2 (league from pwkLg_GetMyLeague, 0x24b9c).
  NEWS_ART.PAC                286 article pictures, read one entry at a time
                              by the index in article +0x134 (0x24db0).
  *.HED                       copies of their pack's header.
  NEWSMONTHFLAG.TBB           144 records {u16 competition, u8 month, u8
                              flag}: CNewsStockManager (0x14d620) loads it,
                              0x14ddf8 looks up (competition, month) and a
                              set flag makes the month's best-player ranking
                              article (0x14dea8) for the player's league's
                              top two divisions.

`info` checks the packs and the table. `months` prints the table as a
competition x month grid.

Usage:
    python news.py info   <DAT/NEWS>
    python news.py months <DAT/NEWS>
"""
import os
import struct
import sys

from pac import load_header
import svr
import tbb

# Entries NEWS::CFactory requests: the loops at 0x248a0 (35), 0x248d0 (15),
# 0x24900 (2); 6 leagues x 4 mastheads (tables 0x2198a8-0x2198f0).
PACKS = [("NEWS_AD", 35), ("NEWS_CARTOON", 15), ("NEWS_OTHER", 2), ("NEWS_TITLE", 24),
         ("NEWS_ART", 286)]
LEAGUES = 6
TITLE_SUFFIXES = ["_%d_1.svr", "_%d_2.svr", "_%d_sp_1.svr", "_%d_sp_2.svr"]
MONTH_RECORD = 4
MONTHS = range(1, 13)
# Season order, as the table lists them.
SEASON_MONTHS = [7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6]


def check_pack(d, name, want):
    pac = os.path.join(d, name + ".PAC")
    hed = os.path.join(d, name + ".HED")
    try:
        hdr = load_header(pac)
        with open(pac, "rb") as f:
            data = f.read()
    except (OSError, ValueError, struct.error) as e:
        return ["%-17s !! %s" % (name + ".PAC", e)], None
    problems = []
    if hdr is None:
        return ["%-17s !! not a BINPAC" % (name + ".PAC")], None
    names = [e[2] for e in hdr.entries]
    if len(names) != want:
        problems.append("%d entries, the game requests %d" % (len(names), want))
    sizes = {}
    for off, size, n, _ in hdr.entries:
        try:
            tex = svr.parse_svr(data[off:off + size], n)
        except (ValueError, struct.error, KeyError) as e:
            problems.append("%s isn't an SVR (%s)" % (n, e))
            continue
        key = (tex.width, tex.height, tex.fmt_name)
        sizes[key] = sizes.get(key, 0) + 1
    try:
        with open(hed, "rb") as f:
            head = f.read()
        if data[:len(head)] != head:
            problems.append("%s isn't a copy of the pack's header" % os.path.basename(hed))
    except OSError:
        problems.append("no %s" % os.path.basename(hed))
    if name == "NEWS_TITLE" and len(names) == want:
        for league in range(LEAGUES):
            for k, suffix in enumerate(TITLE_SUFFIXES):
                if not names[4 * league + k].lower().endswith(suffix % league):
                    problems.append("entry %d isn't title%s" % (4 * league + k, suffix % league))
    line = "%-17s %3d entries, %s" % (name + ".PAC", len(names), ", ".join(
        "%d at %dx%d %s" % (n, w, h, f) for (w, h, f), n in sorted(sizes.items())))
    return [line + ("  !! " + "; ".join(problems) if problems else "")], names


def month_records(d):
    _, tables = tbb.load(os.path.join(d, "NEWSMONTHFLAG.TBB"))
    data = tables[0].data
    recs = [struct.unpack_from("<HBB", data, i)
            for i in range(0, len(data) - len(data) % MONTH_RECORD, MONTH_RECORD)]
    return tables, recs


def check_months(d):
    try:
        tables, recs = month_records(d)
    except (OSError, ValueError, struct.error) as e:
        return "NEWSMONTHFLAG.TBB  !! %s" % e
    problems = []
    if len(tables) != 1:
        problems.append("%d tables, expected 1" % len(tables))
    if len(tables[0].data) % MONTH_RECORD:
        problems.append("size %d not a whole number of records" % len(tables[0].data))
    comps = sorted({c for c, _, _ in recs})
    seen = {(c, m) for c, m, _ in recs}
    if len(seen) != len(recs):
        problems.append("repeated (competition, month) pairs")
    if seen != {(c, m) for c in comps for m in MONTHS}:
        problems.append("not every competition has every month once")
    if any(f > 1 for _, _, f in recs):
        problems.append("flags other than 0 and 1")
    on = sum(1 for _, _, f in recs if f)
    line = "NEWSMONTHFLAG.TBB  %d records, %d competitions (%s), %d flags set" % (
        len(recs), len(comps), " ".join(map(str, comps)), on)
    return line + ("  !! " + "; ".join(problems) if problems else "")


def cmd_info(d):
    for name, want in PACKS:
        lines, _ = check_pack(d, name, want)
        for line in lines:
            print(line)
    print(check_months(d))


def cmd_months(d):
    _, recs = month_records(d)
    flags = {(c, m): f for c, m, f in recs}
    comps = sorted({c for c, _, _ in recs})
    print("competition  " + " ".join("%3d" % m for m in SEASON_MONTHS))
    for c in comps:
        print("%11d  " % c + " ".join("  %s" % ("x" if flags.get((c, m)) else ".")
                                      for m in SEASON_MONTHS))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "months" and len(args) == 1:
        cmd_months(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
