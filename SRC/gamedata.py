# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for GAME/GAMEDATA.BIN of Let's Make a Soccer Team! (PS2): the match
engine's table of 4,131 0x30-byte records, each a way of touching the
ball: a kick request names one (+0x1c). See DOC/GAMEDATA_FORMAT.md.

Confirmed from GAMEPRG.REL: the file is loader slot 10 (0x5378); record n
is data + n * 0x30 (0x13abb8). 0x13abf0 / 0x13ac20 / 0x13ac58 compare a
record's s16 at +0x4 with an index and with other records' +0x4 (what it
means isn't settled: in records 0-41 it pairs them, 4 <-> 5, 6 <-> 7, but
later records hold small shared values); 0x13ab80 reads the s8 at +0x8 as
an angle in units of pi/32; 0x13ad00 reads s16 +0x20 / +0x22 as a range.
The kick code reads the body part, bits 16-18 of the u32 at +0xc (0x98e88:
0 and 1 the feet, 2 and up scaled by the header parameter), and the
surface at +0x25 (0x45f74), an index into the kick kind's variant names
(0x58000). Empirically parts 0-4 occur and surfaces 0-16 or 255 (none).

Usage:
    python gamedata.py info <GAMEDATA.BIN | dir>
    python gamedata.py dump <GAMEDATA.BIN> [first [last]]
"""
import math
import os
import struct
import sys

FILE = "GAMEDATA.BIN"
RECORD = 0x30
PARTNER, ANGLE, PART_WORD, SPEED, RANGE, SURFACE = 0x4, 0x8, 0xC, 0x14, 0x20, 0x25
PARTS = ("foot", "foot", "head", "chest", "other")    # empirical, from the surfaces each uses
# The variant names of the kick kinds' lists (GAMEPRG.REL 0x2680cc on).
SURFACES = ("INSIDE", "OUTSIDE", "HEEL", "SOLE", "TOE", "INSTEP", "INFRONT",
            "OUTFRONT", "CHEST", "HEAD_STRONG", "HEAD_WEAK", "SLIDING", "CHIP",
            "OVERHEAD", "JUMPING_VOLLEY", "HEEL_VOLLEY", "DIVING_HEAD")
NO_SURFACE = 0xFF
ANGLE_UNIT = math.pi / 32          # 0x3dc90fdc at 0x13ab94


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        data = f.read()
    if len(data) % RECORD:
        raise ValueError("%d bytes, not a whole number of 0x%x-byte records" % (len(data), RECORD))
    return path, [data[i:i + RECORD] for i in range(0, len(data), RECORD)]


def fields(rec):
    partner = struct.unpack_from("<h", rec, PARTNER)[0]
    angle = struct.unpack_from("<b", rec, ANGLE)[0]
    speed = struct.unpack_from("<f", rec, SPEED)[0]
    lo, hi = struct.unpack_from("<hh", rec, RANGE)
    return partner, angle, speed, (lo, hi)


def contact(rec):
    """(body part, surface) of a record."""
    return (struct.unpack_from("<I", rec, PART_WORD)[0] >> 16) & 7, rec[SURFACE]


def cmd_info(path):
    """The record count and the body-part and surface tallies; a part above
    4 or a surface past the names (other than 255) is marked."""
    try:
        path, recs = load(path)
    except (ValueError, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    angles = sorted(set(fields(r)[1] for r in recs))
    print("%s  %d records of 0x%x, angles %d..%d (pi/32)" % (
        path, len(recs), RECORD, angles[0], angles[-1]))
    parts = {}
    for i, r in enumerate(recs):
        part, surface = contact(r)
        parts.setdefault(part, {}).setdefault(surface, 0)
        parts[part][surface] += 1
        bad = []
        if part >= len(PARTS):
            bad.append("body part %d" % part)
        if surface >= len(SURFACES) and surface != NO_SURFACE:
            bad.append("surface %d" % surface)
        if bad:
            print("  record %d  !! %s" % (i, "; ".join(bad)))
    for part in sorted(parts):
        tally = sorted(parts[part].items(), key=lambda kv: -kv[1])
        print("  part %d %-5s %5d records: %s" % (
            part, PARTS[part] if part < len(PARTS) else "?", sum(parts[part].values()),
            ", ".join("%s %d" % (SURFACES[s] if s < len(SURFACES) else s, n) for s, n in tally)))


def cmd_dump(path, first, last):
    path, recs = load(path)
    for i in range(first, min(last, len(recs) - 1) + 1):
        partner, angle, speed, (lo, hi) = fields(recs[i])
        part, surface = contact(recs[i])
        print("%4d  +0x4 %4d  angle %4d (%6.1f deg)  +0x14 %6.2f  range %d..%d  part %d %-14s %s" % (
            i, partner, angle, math.degrees(angle * ANGLE_UNIT), speed, lo, hi, part,
            SURFACES[surface] if surface < len(SURFACES) else "-", recs[i].hex(" ")))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "dump" and 1 <= len(args) <= 3:
        first = int(args[1], 0) if len(args) > 1 else 0
        last = int(args[2], 0) if len(args) > 2 else first + 19
        cmd_dump(args[0], first, last)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
