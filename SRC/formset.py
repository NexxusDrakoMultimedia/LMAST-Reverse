# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Tactics presets: PARAM/TACTICS_FORMATION_SET.TBB, for Let's Make a Soccer
Team! (PS2).

The tactics screen's "Set Formation" menu (CTacticsMenuFormationSet-
Implement) offers eight national styles, one 8-byte row each (TBB line
size 8). The tactics manager loads the file (CTacticsManagerImplement::
GetPreLoadData list entry 11, SLES 0x2e334c) and gives it to
CTacticsLoader::setFormationData (0x2ed298). Moving the cursor to row r
(0x2f0318) applies it to the team style (my-team data +0x4204 + style *
0x70); see DOC/PARAM_DIR.md#tactics_formation_settbb-tactics-presets.

  +0 .. +6  the seven team tactics, in the tactics screen's order (labels
            category 492 messages 0-6; the screen keeps them at +0x584 +
            4i and stores them to the style at 0x3038e0): attacking,
            attack speed, attack type, attack side, pressure, offside,
            press line. Bytes 0-3 go to style +0x5c-+0x5f, byte 4 to +0x61,
            5 to +0x62, 6 to +0x60 (0x2f0394-0x2f03d8)
  +7        the formation, an index of pbdata.FORMATIONS
            (plTeam_FormationID2Formation, 0x2f035c)

Row r is named by category 492 message 10001 + r and described by 20001
+ r (CTacticsMessage group 3, entries 0x15 and 0x16).

Usage:
    python formset.py info      <TACTICS_FORMATION_SET.TBB | DAT/PARAM>
    python formset.py show      <TACTICS_FORMATION_SET.TBB>
    python formset.py set       <in.TBB> <out.TBB> <row> <field>=<value> ... [<row> ...]
    python formset.py roundtrip <TACTICS_FORMATION_SET.TBB>

`set` writes a same-size file for patch_disc.py, which also patches its
copies in the PRELOAD/TACTICS* packs (--copies).
"""
import os
import struct
import sys

import tbb

FILE = "TACTICS_FORMATION_SET.TBB"
ROW = 8
FIELDS = ("attacking", "attack_speed", "attack_type", "attack_side", "pressure",
          "offside", "press_line", "formation")
STYLE_OFFSET = (0x5c, 0x5d, 0x5e, 0x5f, 0x61, 0x62, 0x60)   # 0x2f0394-0x2f03d8
SETS = ("English", "French", "German", "Italian", "Spanish", "Dutch", "Brazilian",
        "Argentine")                        # category 492, 10001-10008 (English)
TACTIC_RANGE = (0, 255)                     # the slider's own limits aren't traced


def formations():
    import pbdata
    return pbdata.FORMATIONS


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, raw = tbb.parse(buf)
    if len(raw) != 1 or len(raw[0].data) % ROW:
        raise ValueError("expected one table of %d-byte rows" % ROW)
    rows = [bytearray(raw[0].data[o:o + ROW]) for o in range(0, len(raw[0].data), ROW)]
    return buf, end, raw, rows


def check(rows):
    problems = []
    for r, row in enumerate(rows):
        if row[7] >= len(formations()):
            problems.append("row %d: formation %d (0-%d)" % (r, row[7], len(formations()) - 1))
    return problems


def edit_spec(name):
    """The values a field allows, as pbdata.edit_spec gives them:
    ("choice", [formation indexes]) or ("range", low, high)."""
    if name == "formation":
        return ("choice", list(range(len(formations()))))
    return ("range",) + TACTIC_RANGE


def set_field(row, name, value):
    if name not in FIELDS:
        raise ValueError("no field %r; fields are %s" % (name, ", ".join(FIELDS)))
    hi = len(formations()) - 1 if name == "formation" else TACTIC_RANGE[1]
    if not 0 <= value <= hi:
        raise ValueError("%s must be 0-%d" % (name, hi))
    k = FIELDS.index(name)
    old = row[k]
    row[k] = value
    return old


def encode_file(buf, end, raw, rows):
    problems = check(rows)
    if problems:
        raise ValueError("; ".join(problems))
    raw[0].data = b"".join(bytes(r) for r in rows)
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


def row_text(r, row):
    name = SETS[r] if r < len(SETS) else "row %d" % r
    return "%d %-10s %-12s %s" % (r, name, formations()[row[7]] if row[7] < len(formations())
                                  else "?", "  ".join("%s %d" % (FIELDS[k], row[k])
                                                      for k in range(7)))


def cmd_info(path):
    try:
        _, _, raw, rows = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    problems = check(rows)
    print("%s: %d sets of %d bytes%s" % (path, len(rows), ROW,
                                         "  !! " + "; ".join(problems) if problems else ""))
    for k in range(7):
        print("  %-12s %s" % (FIELDS[k], " ".join(str(r[k]) for r in rows)))


def cmd_show(path):
    _, _, _, rows = load(path)
    for r, row in enumerate(rows):
        print(row_text(r, row))


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw, rows = load(path)
    target = None
    for a in args:
        if "=" not in a:
            r = int(a, 0)
            if not 0 <= r < len(rows):
                raise SystemExit("%s: no such row (0-%d)" % (a, len(rows) - 1))
            target = r
            continue
        if target is None:
            raise SystemExit("give a row before %r" % a)
        name, value = a.split("=", 1)
        try:
            old = set_field(rows[target], name, int(value, 0))
        except ValueError as e:
            raise SystemExit("row %d: %s" % (target, e))
        print("row %d %s: %d -> %d" % (target, name, old, rows[target][FIELDS.index(name)]))
    try:
        out = encode_file(buf, end, raw, rows)
    except ValueError as e:
        raise SystemExit(str(e))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_roundtrip(path):
    buf, end, raw, rows = load(path)
    try:
        out = encode_file(buf, end, raw, rows)
        print("%s: %s" % (path, "rebuilt file identical" if out == buf else "!! rebuilt file differs"))
    except ValueError as e:
        print("%s: !! %s" % (path, e))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and len(args) == 1:
        cmd_show(args[0])
    elif cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
