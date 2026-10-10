# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Tour opponents: PARAM/TOUR_LIST.TBB, for Let's Make a Soccer Team! (PS2).

One table of {u16 region, u16 club} pairs (TBB line size 2). The camp and
tour screens' module loads it (SIMPRG.REL load list 0x1cdd30, entry 27;
handle at +0x904), and 0x4cab0(out, region) clears 40 u16 slots and copies
in the club of every pair whose region matches, in table order. Its
caller (0xa44d8) takes the region from the screen's list. See
DOC/PARAM_DIR.md#tour_listtbb-tour-opponents-by-region.

Usage:
    python tour.py info      <TOUR_LIST.TBB | DAT/PARAM>
    python tour.py show      <TOUR_LIST.TBB> [MES.PAC]
    python tour.py set       <in.TBB> <out.TBB> <pair>=<region>:<club> ...
    python tour.py roundtrip <TOUR_LIST.TBB>

`show` names the clubs from MES.PAC (category 3) when given. `set`
replaces whole pairs, by their number in the table (0-105), and writes a
same-size file for patch_disc.py.
"""
import os
import struct
import sys

import tbb

FILE = "TOUR_LIST.TBB"
SLOTS = 40                      # 0x4cb0c: 0x27 + 1 u16 cleared and filled
CLUBS = 0x22e                   # team ids 1-0x22d (SCHEDULE_FORMAT.md, PLTEAMID)
REGIONS = 13


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, raw = tbb.parse(buf)
    if len(raw) != 1 or len(raw[0].data) % 4:
        raise ValueError("expected one table of 4-byte pairs")
    pairs = [list(struct.unpack_from("<2H", raw[0].data, o)) for o in range(0, len(raw[0].data), 4)]
    return buf, end, raw, pairs


def check(pairs):
    problems = []
    for i, (region, club) in enumerate(pairs):
        if not 1 <= club < CLUBS:
            problems.append("pair %d: club %d" % (i, club))
    counts = {}
    for region, _ in pairs:
        counts[region] = counts.get(region, 0) + 1
    for region, n in sorted(counts.items()):
        if n > SLOTS:
            problems.append("region %d has %d clubs; the screen takes %d" % (region, n, SLOTS))
    return problems


def encode_file(buf, end, raw, pairs):
    problems = check(pairs)
    if problems:
        raise ValueError("; ".join(problems))
    raw[0].data = b"".join(struct.pack("<2H", *p) for p in pairs)
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


def club_names(mes_path):
    if not mes_path:
        return {}
    import camp
    import initteam
    return {rid - initteam.TEAM_NAME_BASE: t for rid, t in
            camp.messages(mes_path, initteam.TEAM_NAME_CATEGORY).items()}


def cmd_info(path):
    try:
        _, _, raw, pairs = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    problems = check(pairs)
    counts = {}
    for region, _ in pairs:
        counts[region] = counts.get(region, 0) + 1
    print("%s: %d pairs%s" % (path, len(pairs), "  !! " + "; ".join(problems) if problems else ""))
    print("  clubs by region: %s" % ", ".join("%d: %d" % kv for kv in sorted(counts.items())))


def cmd_show(path, mes=None):
    _, _, _, pairs = load(path)
    names = club_names(mes)
    for region in sorted({r for r, _ in pairs}):
        print("region %2d: %s" % (region, ", ".join(
            "%d %s" % (c, names.get(c, "")) if names else str(c)
            for r, c in pairs if r == region)))


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw, pairs = load(path)
    for a in args:
        try:
            k, _, v = a.partition("=")
            region, _, club = v.partition(":")
            k, region, club = int(k, 0), int(region, 0), int(club, 0)
        except ValueError:
            raise SystemExit("expected <pair>=<region>:<club>, got %r" % a)
        if not 0 <= k < len(pairs):
            raise SystemExit("%s: no such pair (0-%d)" % (a, len(pairs) - 1))
        if not 0 <= region < REGIONS or not 1 <= club < CLUBS:
            raise SystemExit("%s: region 0-%d, club 1-%d" % (a, REGIONS - 1, CLUBS - 1))
        print("pair %d: %d:%d -> %d:%d" % (k, pairs[k][0], pairs[k][1], region, club))
        pairs[k] = [region, club]
    try:
        out = encode_file(buf, end, raw, pairs)
    except ValueError as e:
        raise SystemExit(str(e))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_roundtrip(path):
    buf, end, raw, pairs = load(path)
    try:
        out = encode_file(buf, end, raw, pairs)
        print("%s: %s" % (path, "rebuilt file identical" if out == buf else "!! rebuilt file differs"))
    except ValueError as e:
        print("%s: !! %s" % (path, e))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and len(args) in (1, 2):
        cmd_show(args[0], args[1] if len(args) == 2 else None)
    elif cmd == "set" and len(args) >= 3:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
