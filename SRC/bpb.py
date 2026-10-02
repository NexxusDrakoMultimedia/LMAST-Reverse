# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for the play books GAME/PLAYBOOK.BPB and GAME/COMBINATION.BPB of
Let's Make a Soccer Team! (PS2): the movements of players and ball in each
set play and move, in metres on the pitch. See DOC/BPB_FORMAT.md.

Confirmed from Pwk::PlayBookData::CPlayBookDataBase in SLES_541.51:

  file    u32 record count, then the records back to back; each starts
          with its u16 size (makeBookTop 0x2e82b0)
  record  +0x04 u32 flags; +0x0a/+0x0c/+0x12 u16 offsets of three u16
          arrays of n entries (points per path, start frame per path, path
          kind); +0x0e u16 offset of the points; +0x16 u16 n, the paths;
          +0x18 4 bytes, the ball's route through the paths (0xff = none,
          IBOOK::GetBallFlowID); +0x1c u16 (GetPLAYBOOK 0x2e7ec8)
  point   two u16, x and y: (value >> 3) / 64 metres, bit 2 the sign, bits
          0-1 a code (0x2e8338); the point's code is y bits * 10 + x bits
  ids     a play id maps to a record (SplitID 0x2e8370): below 0x1000
          (id >> 8) * 10 + (id & 0xff); 0x1000-0x3fff (id >> 12 - 1) * 32 +
          ((id >> 8) & 0xf) * 8 + 100 + (id & 0xff); 0x4000-0x6fff
          ((id - 0x4000) >> 12) * 20 + 196 + (id & 0xff); 0x7000 on the
          index itself

COMBINATION2.CBB has the same container (u32 count, size-prefixed records,
GAMEPRG.REL 0xc7e84): 540 records, one per combination; its scripts are the
540 SQB1 scripts in COMBINATION2.CSB (sqb.py). `info` checks its container.

Usage:
    python bpb.py info <file.BPB | file.CBB | dir> ...
    python bpb.py dump <file.BPB> <record>
"""
import os
import struct
import sys

BALL_KIND = 0xfe                 # path kind high byte of the ball's path
COORD_SHIFT, COORD_SCALE, COORD_SIGN = 3, 64.0, 4
ROUTE_OFF, ROUTE_LEN, NONE = 0x18, 4, 0xff


def coord(v):
    """A point coordinate in metres (0x2e8338)."""
    f = (v >> COORD_SHIFT) / COORD_SCALE
    return -f if v & COORD_SIGN else f


class Play:
    def __init__(self, raw):
        self.raw = raw
        (self.size,) = struct.unpack_from("<H", raw, 0)
        (self.flags,) = struct.unpack_from("<I", raw, 4)
        (self.header,) = struct.unpack_from("<H", raw, 8)
        (self.off_count, self.off_start, self.off_points, _, self.off_kind,
         _, self.n) = struct.unpack_from("<7H", raw, 0xa)
        self.counts = struct.unpack_from("<%dH" % self.n, raw, self.off_count)
        self.starts = struct.unpack_from("<%dH" % self.n, raw, self.off_start)
        self.kinds = struct.unpack_from("<%dH" % self.n, raw, self.off_kind)
        self.route = [b for b in raw[ROUTE_OFF:ROUTE_OFF + ROUTE_LEN] if b != NONE]

    def problems(self):
        out = []
        if not (self.header <= self.off_count < self.off_start <= self.off_points
                < self.off_kind <= self.size):
            out.append("offsets out of order")
        if self.off_points + 4 * sum(self.counts) > self.off_kind:
            out.append("%d points overrun the path kinds" % sum(self.counts))
        if any(r >= self.n for r in self.route):
            out.append("ball route %s past %d paths" % (self.route, self.n))
        return out

    def paths(self):
        """[(kind, start frame, [(x, y, code)])] per path."""
        out, p = [], self.off_points
        for k in range(self.n):
            pts = []
            for _ in range(self.counts[k]):
                x, y = struct.unpack_from("<HH", self.raw, p)
                p += 4
                pts.append((coord(x), coord(y), (y & 3) * 10 + (x & 3)))
            out.append((self.kinds[k], self.starts[k], pts))
        return out


def parse(data):
    """[Play] for a .BPB file; raises ValueError if the records don't add up."""
    (n,) = struct.unpack_from("<I", data, 0)
    plays, o = [], 4
    for i in range(n):
        if o + 2 > len(data):
            raise ValueError("record %d starts past the end" % i)
        (size,) = struct.unpack_from("<H", data, o)
        if not size or o + size > len(data):
            raise ValueError("record %d (size %d) runs past the end" % (i, size))
        plays.append(Play(data[o:o + size]))
        o += size
    if o != len(data):
        raise ValueError("%d records end at 0x%x, file is 0x%x" % (n, o, len(data)))
    return plays


def cbb_records(data):
    """[bytes] of a .CBB (GAME/COMBINATION2.CBB): a u32 count, then records
    that start with their u16 size (GAMEPRG.REL 0xc7e84 builds a pointer
    to each the same way makeBookTop does)."""
    (n,) = struct.unpack_from("<I", data, 0)
    out, o = [], 4
    for i in range(n):
        if o + 2 > len(data):
            raise ValueError("record %d starts past the end" % i)
        (size,) = struct.unpack_from("<H", data, o)
        if not size or o + size > len(data):
            raise ValueError("record %d (size %d) runs past the end" % (i, size))
        out.append(data[o:o + size])
        o += size
    if o != len(data):
        raise ValueError("%d records end at 0x%x, file is 0x%x" % (n, o, len(data)))
    return out


def files(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, names in sorted(os.walk(p)):
                for name in sorted(names):
                    if name.upper().endswith((".BPB", ".CBB")):
                        yield os.path.join(root, name)
        else:
            yield p


def cmd_info(paths):
    for path in files(paths):
        with open(path, "rb") as f:
            data = f.read()
        if path.upper().endswith(".CBB"):
            try:
                recs = cbb_records(data)
            except (ValueError, struct.error) as e:
                print("%s  !! %s" % (path, e))
                continue
            sizes = sorted(set(len(r) for r in recs))
            print("%s  %d combination records, sizes %s" % (
                path, len(recs), ", ".join("%d" % s for s in sizes)))
            continue
        try:
            plays = parse(data)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            continue
        bad = []
        for i, p in enumerate(plays):
            try:
                probs = p.problems()
            except struct.error as e:
                probs = [str(e)]
            if probs:
                bad.append("%d: %s" % (i, "; ".join(probs)))
        paths_n = sum(p.n for p in plays)
        points = sum(sum(p.counts) for p in plays)
        balls = sum(1 for p in plays if any(k >> 8 == BALL_KIND for k in p.kinds))
        print("%s  %d plays, %d paths, %d points, %d with a ball path, header 0x%x%s" % (
            path, len(plays), paths_n, points, balls,
            plays[0].header if plays else 0,
            "  !! " + "; ".join(bad[:3]) if bad else ""))


def cmd_dump(path, index):
    with open(path, "rb") as f:
        plays = parse(f.read())
    p = plays[index]
    print("%s play %d: %d bytes, flags %#x, %d paths, ball route %s" % (
        path, index, p.size, p.flags, p.n, p.route or "-"))
    for k, (kind, start, pts) in enumerate(p.paths()):
        print("  path %2d  kind %#06x%s  start %3d  %s" % (
            k, kind, " (ball)" if kind >> 8 == BALL_KIND else "       ", start,
            " ".join("(%.1f,%.1f c%d)" % pt for pt in pts)))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args)
    elif cmd == "dump" and len(args) == 2:
        cmd_dump(args[0], int(args[1], 0))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
