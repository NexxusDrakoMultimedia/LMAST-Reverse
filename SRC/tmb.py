# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for GAME/TEAM.TMB (Let's Make a Soccer Team!, PS2): a list of the
441 resident clubs with a name, a 3-letter code and a block of 23 numbers
each. No code in the executable or the overlays names the file, so the
game does not appear to read it (DOC/GAME_DIR.md, "TEAM.TMB").

Layout (empirical, checked over the whole file):

  +0x00  "TMB1"
  +0x04  u32 0x10, the offset of the first record
  +0x08  u32 the bytes the records take (record size x count)
  +0x0c  u32 the record size, 0x4a
  record (0x4a bytes)
    +0x00  char[0x16]  name, NUL padded ("Highbury", "Chelsea", "USER_TEAM_32")
    +0x16  char[4]     3-letter code, NUL padded
    +0x1a  u16[23]     23 consecutive numbers, the first a multiple of 23
    +0x48  u16         always 6
  The file is padded with zero bytes to 0x8000.

`info` checks every one of these and marks each problem with !!. `list`
prints the records.

Usage:
    python tmb.py info <TEAM.TMB | DAT>
    python tmb.py list <TEAM.TMB | DAT>
"""
import os
import struct
import sys

MAGIC = b"TMB1"
HEADER = 0x10
RECORD = 0x4A
NAME_LEN = 0x16
CODE_LEN = 4
RUN = 23
FILE_SIZE = 0x8000
LAST = 6
REL_PATH = os.path.join("GAME", "TEAM.TMB")


def _text(raw):
    # Game text is cp850 (DOC/MBB_FORMAT.md): a few club names carry accents.
    return raw.split(b"\0")[0].decode("cp850")


def parse(data):
    """Return (header dict, records). Raises ValueError on a bad header."""
    if len(data) < HEADER or data[:4] != MAGIC:
        raise ValueError("not a TMB1 file")
    first, size, rec = struct.unpack_from("<III", data, 4)
    if first != HEADER or rec != RECORD or size % rec or HEADER + size > len(data):
        raise ValueError("unexpected header %#x %#x %#x" % (first, size, rec))
    records = []
    for i in range(size // rec):
        o = HEADER + i * rec
        ids = struct.unpack_from("<%dH" % RUN, data, o + NAME_LEN + CODE_LEN)
        last = struct.unpack_from("<H", data, o + rec - 2)[0]
        records.append((_text(data[o:o + NAME_LEN]),
                        _text(data[o + NAME_LEN:o + NAME_LEN + CODE_LEN]),
                        ids, last))
    return {"size": size, "tail": data[HEADER + size:]}, records


def find_file(path):
    return os.path.join(path, REL_PATH) if os.path.isdir(path) else path


def cmd_info(path):
    path = find_file(path)
    with open(path, "rb") as f:
        data = f.read()
    try:
        head, records = parse(data)
    except ValueError as e:
        print("%s  !! %s" % (path, e))
        return 1
    problems = []
    if len(data) != FILE_SIZE:
        problems.append("size %#x, not %#x" % (len(data), FILE_SIZE))
    if any(head["tail"]):
        problems.append("non-zero bytes after the records")
    for i, (name, code, ids, last) in enumerate(records):
        if not name or not code:
            problems.append("record %d: empty name or code" % i)
        if list(ids) != list(range(ids[0], ids[0] + RUN)) or ids[0] % RUN:
            problems.append("record %d: ids are not 23 consecutive numbers from a multiple of 23" % i)
        if last != LAST:
            problems.append("record %d: last value %d, not %d" % (i, last, LAST))
    blocks = {r[2][0] for r in records}
    print("%s  records=%d  distinct id blocks=%d  codes=%d%s" % (
        path, len(records), len(blocks), len({r[1] for r in records}),
        "  !! " + "; ".join(problems[:6]) + (" (and %d more)" % (len(problems) - 6)
                                              if len(problems) > 6 else "") if problems else ""))
    return 1 if problems else 0


def cmd_list(path):
    with open(find_file(path), "rb") as f:
        _, records = parse(f.read())
    for i, (name, code, ids, last) in enumerate(records):
        print("%3d  %-14s %-4s ids %5d..%-5d  %d" % (i, name, code, ids[0], ids[-1], last))
    return 0


def main(argv):
    if len(argv) != 3 or argv[1] not in ("info", "list"):
        print(__doc__)
        return 1
    return {"info": cmd_info, "list": cmd_list}[argv[1]](argv[2])


sys.exit(main(sys.argv))
