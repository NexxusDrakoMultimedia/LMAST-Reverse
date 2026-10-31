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
          0-1 a code (0x2e8338); the point's code is y bits * 10 + x bits.
          On a player's path, codes 0, 1, 2 and 20 give a move order of
          kind 8, 1, 2 and 4 toward the point (GAMEPRG.REL 0x104e98)
  ids     a play id maps to a record (SplitID 0x2e8370): below 0x1000
          (id >> 8) * 10 + (id & 0xff); 0x1000-0x3fff (id >> 12 - 1) * 32 +
          ((id >> 8) & 0xf) * 8 + 100 + (id & 0xff); 0x4000-0x6fff
          ((id - 0x4000) >> 12) * 20 + 196 + (id & 0xff); 0x7000 on the
          index itself
  starts  the block at the header's end: u16 size, 2 bytes, u16 n, u16
          kind (1 corner, 2 free kick, 3 never used), n (x, y) starts
          (GetFormationData 0x2e7d88)
  kinds   role type << 8 | flag 0x80 | value (GAMEPRG.REL 0x109598); the
          types are the role factory's (0x114f30), named in ROLE_TYPES
          after the lookup's remapping (0x108c18). The value picks the
          role's variant: a corner taker's makes the corner short or a
          cross (0x105700), a free-kick taker's a short or long ball
          (0x105df8); `dump` prints these in brackets

The match asks for 16 corner plays (records 0-99) and 24 free-kick plays
(100-195) only (GAMEPRG.REL 0xb8560, 0xb85b0); COMBINATION.BPB's record
p - 1 is attack pattern p's diagram on the tactics screen (SLES
0x2faf80). See DOC/BPB_FORMAT.md#which-play-is-which.

COMBINATION2.CBB has the same container (u32 count, size-prefixed records,
GAMEPRG.REL 0xc7e84): 540 records, one per combination; its scripts are the
540 SQB1 scripts in COMBINATION2.CSB (sqb.py). A record (read by
fb::CombinationSequencer, GAMEPRG.REL 0xc7a78):

  +0x00   u16 size; u16 base (4): the offsets below are from the record + base
  +0x04   u8 n, the slots; +0x05/+0x06 u8 offsets of blocks A and B; +0x07
          + i u8 offset of slot i (slot 0 is the header block C)
  A       u8 kind; kind 1: two u8 values
  B       u8 kind; kind 2: one u8 value
  C       u16, 2 bytes pad, 4 x u32, 2 x u16 (each x 10.0; a zero second one
          with a non-zero first becomes 1055.6)
  slot i  u8 type (0-7), then by type: 0 two u8 (the second x 10); 1, 3,
          4, 5 an area; 2 and 6 a u8 and an area; 7 three u8 (the last x 10)
  area    u8 shape, s8 x, s8 y (x 10.0), then shape 0 s8 radius, else s8 x2,
          s8 y2 (x 10.0) (0xc7f00)

Slot k (1 to n - 1) is where combination participant k is found: the
first outfield player inside its area (0xc1fc8). The types are named in
CBB_SLOT_NAMES; types 0 and 6 never find anyone. A team has 11
combinations (0xc1180): 8 drawn from a fixed table of basic records
(0x14c3f0) and up to 3 of the club's attack patterns (record 60 + 16 x
(pattern - 1)); all 11 are tested against the ball holder, highest
record first (0xc1438). Only 65 records can ever load.

`info` checks every record against this layout; `cbb` prints records.

Usage:
    python bpb.py info <file.BPB | file.CBB | dir> ...
    python bpb.py dump <file.BPB> <record>
    python bpb.py cbb  <file.CBB> [first [last]]
"""
import os
import struct
import sys

BALL_KIND = 0xfe                 # path kind high byte of the ball's path
# A player's point code -> the move order kind it gives on reaching the
# point before it (GAMEPRG.REL 0x104e98, method pointers at 0x278dd0).
MOVE_CODES = {0: 8, 1: 1, 2: 2, 20: 4}
COORD_SHIFT, COORD_SCALE, COORD_SIGN = 3, 64.0, 4
ROUTE_OFF, ROUTE_LEN, NONE = 0x18, 4, 0xff
FORM_MAX = 22                    # GetFormationData stops at 0x16 values
# A path kind is a role type (high byte), a value (bits 0-6) and a flag
# (bit 7) (0x109598). The role factory (GAMEPRG.REL 0x114f30, jump table
# 0x27a4d0) makes these classes for the types the play books use.
ROLE_TYPES = {13: "RoleCKKicker", 14: "RoleFKKicker", 15: "RoleSP", 16: "RoleSP",
              17: "RoleSP", 18: "RoleSPRecvSC1", 19: "RoleSPRecvSC2", 20: "RoleSP",
              21: "RoleSP", 22: "RoleSP", 26: "RoleSPAttacker", BALL_KIND: "ball"}
# What a taker's value makes his kick when the target is a team-mate:
# PlayCKKick 0x105700 (36 short, 37 cross), PlayFKKick 0x105df8 (jump
# table 0x278df0: 38 short pass, 39 cross or long ball; a shot is 40).
CK_TAKER, FK_TAKER = 13, 15
CK_SHORT_VALUES = (1, 3, 4, 5, 6)
FK_LONG_VALUE = 1


def role_type(kind):
    """The role type the set-play lookup makes for a path kind
    (GAMEPRG.REL 0x108c18, jump table 0x279250): 15 becomes 14 unless
    the value is 2, 16 becomes 14 when the value is 0."""
    t, v = kind >> 8, kind & 0x7f
    if t == 15 and v != 2 or t == 16 and v == 0:
        return 14
    return t


def value_note(kind):
    """What a corner or free-kick taker's value does, or ''."""
    t, v = kind >> 8, kind & 0x7f
    if t == CK_TAKER:
        return "short corner" if v in CK_SHORT_VALUES else "cross"
    if t == FK_TAKER:
        return "cross/long ball" if v == FK_LONG_VALUE else "short pass"
    return ""

CBB_SCALE = 10.0                 # 0xc7f00 and 0xc7b64 multiply by 10.0
CBB_DEFAULT_LIMIT = 1055.6       # 0xc7bc8: 0x4483f3d7
CBB_SLOT_TYPES = 8               # the jump table at 0x274a60
CBB_AREA_TYPES = (1, 3, 4, 5)    # slot types whose bytes are an area right away
CBB_BYTE_AREA_TYPES = (2, 6)     # a u8, then an area
# What each slot type builds in the fb::Combination object (0xc2450) and
# where its area is (AreaPosition::GetPosition 0xc2df0, jump table 0x274590;
# x and y in the attacking team's direction). Slot k picks participant k:
# the first outfield player inside the area (0xc1fc8). Types 0 and 6 never
# match: AreaBallHolder's test returns 0 (0x2267a8), and AreaPosition's
# test (0xc2cd8) accepts types 1-5 only.
CBB_SLOT_NAMES = (
    "ball-holder stub, never matches",          # 0 AreaBallHolder, +0x50
    "from the team's line y",                   # 1 x as given, y + manager +0x1608
    "around participant",                       # 2 the u8 is the participant
    "at the -x touchline",                      # 3 x - 328.66, y + line
    "at the +x touchline",                      # 4 x + 328.66, y + line
    "fixed spot",                               # 5 x, y as given
    "never matches",                            # 6 rejected by the test
    "node line",                                # 7 AreaNodeLine, +0x110
)


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

    def formation(self):
        """(kind, [(x, y)]): the starting positions block at the header's
        end (GetFormationData 0x2e7d88): u16 size, 2 bytes, u16 n, u16 kind,
        then n coordinate pairs (at most 22 values are read)."""
        n, kind = struct.unpack_from("<2H", self.raw, self.header + 4)
        vals = struct.unpack_from("<%dH" % min(2 * n, FORM_MAX), self.raw, self.header + 8)
        return kind, [(coord(vals[i]), coord(vals[i + 1])) for i in range(0, len(vals) - 1, 2)]

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


def cbb_area(raw, o):
    """An area at raw[o] (0xc7f00): (shape, x, y, radius) for shape 0, else
    (shape, x, y, x2, y2), the coordinates already x 10."""
    shape = raw[o]
    x, y, a, b = struct.unpack_from("<4b", raw, o + 1)
    if shape == 0:
        return (shape, x * CBB_SCALE, y * CBB_SCALE, a * CBB_SCALE)
    return (shape, x * CBB_SCALE, y * CBB_SCALE, a * CBB_SCALE, b * CBB_SCALE)


class Combination:
    """A COMBINATION2.CBB record, read the way GAMEPRG.REL 0xc7a78 reads it."""

    def __init__(self, raw):
        self.raw = raw
        self.size, self.base, self.n = struct.unpack_from("<HHB", raw, 0)
        b = self.base
        self.a_kind = raw[b + raw[5]]
        self.a_values = tuple(raw[b + raw[5] + 1:b + raw[5] + 3]) if self.a_kind == 1 else ()
        self.b_kind = raw[b + raw[6]]
        self.b_value = raw[b + raw[6] + 1] if self.b_kind == 2 else None
        c = b + raw[7]
        (self.c_u16,) = struct.unpack_from("<H", raw, c)
        self.c_words = struct.unpack_from("<4I", raw, c + 4)
        l1, l2 = struct.unpack_from("<HH", raw, c + 0x14)
        self.limits = (l1 * CBB_SCALE, l2 * CBB_SCALE if l2 or not l1 else CBB_DEFAULT_LIMIT)
        self.slots = []
        for i in range(1, self.n):
            o = b + raw[7 + i]
            t = raw[o]
            if t == 0:
                v = (raw[o + 1], raw[o + 2] * CBB_SCALE)
            elif t in CBB_AREA_TYPES:
                v = (cbb_area(raw, o + 1),)
            elif t in CBB_BYTE_AREA_TYPES:
                v = (raw[o + 1], cbb_area(raw, o + 2))
            elif t == 7:
                v = (raw[o + 1], raw[o + 2], raw[o + 3] * CBB_SCALE)
            else:
                v = ()
            self.slots.append((t, v))

    def problems(self):
        out = []
        ends = [self.base + self.raw[k] for k in range(5, 8 + self.n - 1)]
        if any(e >= self.size for e in ends):
            out.append("a block offset past the record")
        if any(t >= CBB_SLOT_TYPES for t, _ in self.slots):
            out.append("slot type past %d" % (CBB_SLOT_TYPES - 1))
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
            bad, slots = [], {}
            for i, r in enumerate(recs):
                try:
                    c = Combination(r)
                    probs = c.problems()
                except (ValueError, struct.error, IndexError) as e:
                    probs = [str(e)]
                    c = None
                if probs:
                    bad.append("%d: %s" % (i, "; ".join(probs)))
                for t, _ in (c.slots if c else []):
                    slots[t] = slots.get(t, 0) + 1
            print("%s  %d combination records, sizes %s, slot types %s%s" % (
                path, len(recs), ", ".join("%d" % s for s in sizes),
                " ".join("%d:%d" % kv for kv in sorted(slots.items())),
                "  !! " + "; ".join(bad[:3]) if bad else ""))
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
        # Player points by code: 0, 1, 2 and 20 order a move at the point
        # (MOVE_CODES); any other code orders nothing there.
        codes = {}
        for p in plays:
            for kind, _, pts in p.paths():
                if kind >> 8 != BALL_KIND:
                    for _, _, c in pts:
                        codes[c] = codes.get(c, 0) + 1
        print("%s  %d plays, %d paths, %d points, %d with a ball path, header 0x%x, "
              "player point codes %s (%d order nothing)%s" % (
            path, len(plays), paths_n, points, balls,
            plays[0].header if plays else 0,
            " ".join("%d:%d" % kv for kv in sorted(codes.items())),
            sum(v for c, v in codes.items() if c not in MOVE_CODES),
            "  !! " + "; ".join(bad[:3]) if bad else ""))


def cmd_dump(path, index):
    with open(path, "rb") as f:
        plays = parse(f.read())
    p = plays[index]
    print("%s play %d: %d bytes, flags %#x, %d paths, ball route %s" % (
        path, index, p.size, p.flags, p.n, p.route or "-"))
    form_kind, spots = p.formation()
    print("  starts (kind %d): %s" % (form_kind, " ".join("(%.1f,%.1f)" % s for s in spots)))
    for k, (kind, start, pts) in enumerate(p.paths()):
        t = role_type(kind)
        role = ROLE_TYPES.get(t, "type %d" % t)
        note = value_note(kind)
        print("  path %2d  kind %#06x %-14s %2d%s  start %3d  %s%s" % (
            k, kind, role, kind & 0x7f, "+" if kind & 0x80 else " ", start,
            "[%s] " % note if note else "",
            " ".join("(%.1f,%.1f c%d)" % pt for pt in pts)))


def fmt_area(a):
    if a[0] == 0:
        return "circle (%g,%g) r%g" % a[1:]
    return "box%d (%g,%g)-(%g,%g)" % a


def cmd_cbb(path, first, last):
    with open(path, "rb") as f:
        recs = cbb_records(f.read())
    for i in range(first, min(last, len(recs) - 1) + 1):
        c = Combination(recs[i])
        print("%4d  A %d%s  B %d%s  C %#06x words %s limits %g %g" % (
            i, c.a_kind, " %s" % (c.a_values,) if c.a_values else "",
            c.b_kind, " %d" % c.b_value if c.b_value is not None else "",
            c.c_u16, " ".join("%#x" % w for w in c.c_words), c.limits[0], c.limits[1]))
        for k, (t, v) in enumerate(c.slots, 1):
            parts = [fmt_area(x) if isinstance(x, tuple) else "%g" % x for x in v]
            name = CBB_SLOT_NAMES[t] if t < len(CBB_SLOT_NAMES) else "?"
            print("        slot %d  type %d %-26s %s" % (k, t, "(%s)" % name, "  ".join(parts)))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args)
    elif cmd == "dump" and len(args) == 2:
        cmd_dump(args[0], int(args[1], 0))
    elif cmd == "cbb" and 1 <= len(args) <= 3:
        first = int(args[1], 0) if len(args) > 1 else 0
        last = int(args[2], 0) if len(args) > 2 else (first if len(args) > 1 else 1 << 30)
        cmd_cbb(args[0], first, last)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
