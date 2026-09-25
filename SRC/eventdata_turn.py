"""Decode DAT/EVENT/EVENTDATA_TURN.TBB into CSV.

EVENTDATA_TURN is an early (CVS rev 1.1, Jan 2005) export of the turn
event sheet. Nothing on the disc loads it - the shipping game uses the
numeric EvsDataBin_EVENT.bin instead - so the record layout below is
inferred from the data alone. See DOC/EVENTDATA_TURN.md.

Usage:
    python eventdata_turn.py <EVENTDATA_TURN.TBB> [out.csv]
"""
import csv
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tbb  # noqa: E402

RECORD_SIZE = 281

# (name, offset, kind, size)
FIELDS = [
    ("category", 0x00, "str", 4),
    ("end_marker", 0x04, "s32", 4),
    ("event_id", 0x10, "str", 32),
    ("timing", 0x30, "str", 32),
    ("priority", 0x50, "u8", 1),
    ("mood", 0x51, "str", 32),
    ("scene_memo", 0x71, "str", 36),
    ("item", 0x95, "str", 64),
    ("location", 0xD5, "str", 36),
    ("character", 0xF9, "str", 32),
]


def _cstr(b):
    return b.split(b"\0", 1)[0]


def decode(rec):
    row = {}
    for name, ofs, kind, size in FIELDS:
        b = rec[ofs:ofs + size]
        if kind == "str":
            # One byte per character; stray non-ASCII bytes are what's left
            # of Japanese text after a lossy export, so keep them as \xNN.
            row[name] = "".join(chr(c) if 32 <= c < 127 else "\\x%02x" % c for c in _cstr(b))
        elif kind == "u8":
            row[name] = b[0]
        elif kind == "s32":
            row[name] = struct.unpack("<i", b)[0]
    return row


def records(path):
    _, tables = tbb.load(path)
    data = tables[0].data
    for i in range(len(data) // RECORD_SIZE):
        yield decode(data[i * RECORD_SIZE:(i + 1) * RECORD_SIZE])


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    out = open(argv[2], "w", newline="", encoding="utf-8") if len(argv) > 2 else sys.stdout
    w = csv.DictWriter(out, fieldnames=["index"] + [f[0] for f in FIELDS])
    w.writeheader()
    for i, row in enumerate(records(argv[1])):
        w.writerow({"index": i, **row})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
