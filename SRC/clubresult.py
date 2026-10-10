# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""How a final place is reported: PARAM/CLUBRESULT.TBB, for Let's Make a
Soccer Team! (PS2).

One TBB1 table of 8-byte rows, one per schedule UID (PLSCHE_GROUP), like
REGULATION.TBB. SIMPRG.REL 0x167e90 loads it and returns the table; three
accessors read row `uid` (0x167f4c: uid << 3), all u16 (lhu). See
DOC/CLUBRESULT_FORMAT.md.

  +0x00 uid          the row's own UID; no reader found
  +0x02 kind         0 league: the place as a number; 1 cup: round names;
                     2 not ranked: "-" and no prize message
                     (0x167f38; results screen 0x9aa90, prize income
                     0x1337cc, the prize message 0x141f54)
  +0x04 third_place  1: places 3 and 4 are named "3rd"/"4th", not "Best 4"
                     (0x167f98 == 1; Msg::ConvertRankToString 0x201810)
  +0x06 clubs        clubs in a cup, which rounds have names: Champion from
                     2, Runners-up from 3, Best 4 from 5, Best 8 from 9,
                     Best 16 from 17, otherwise "Defeated 1st Rnd"
                     (0x167f68; ConvertRankToString 0x2017bc-0x201850).
                     The screen uses 9999 for UID 80 (0x9ab1c)

Usage:
    python clubresult.py info      <CLUBRESULT.TBB | DAT/PARAM>
    python clubresult.py show      <CLUBRESULT.TBB> [uid ...]
    python clubresult.py set       <in.TBB> <out.TBB> <uid> <field>=<value> ... [<uid> ...]
    python clubresult.py roundtrip <CLUBRESULT.TBB>

`show` prints each row with the names a cup's places get. `set` edits
kind, third_place and clubs and writes a same-size file for
patch_disc.py, which also patches the copies in PRELOAD/SIMFILE*.PAC
(--copies).
"""
import os
import struct
import sys

import tbb

FILE = "CLUBRESULT.TBB"
ROW = 8                         # 0x167f4c: uid << 3
UIDS = 164                      # schedule UIDs 0-163 (SCHEDULE_FORMAT.md)
KINDS = ("league", "cup", "not ranked")
SCREEN_CLUBS = {80: 9999}       # 0x9ab04-0x9ab1c: the results screen's override

FIELDS = (("uid", 0x0), ("kind", 0x2), ("third_place", 0x4), ("clubs", 0x6))
OFFSET = dict(FIELDS)
EDITABLE = ("kind", "third_place", "clubs")

# Msg::ConvertRankToString (SLES 0x2017a0) names a cup's places from
# category 1 messages 650-656 (Msg type 0x1d, base id at 0x52f708):
# (first place, last place, message id, clubs needed).
ROUNDS = ((1, 1, 651, 2), (2, 2, 652, 3), (3, 4, 653, 5), (5, 8, 654, 9),
          (9, 16, 655, 17))
ROUND_TEXT = {651: "Champion", 652: "Runners-up", 653: "Best 4", 654: "Best 8",
              655: "Best 16", 656: "Defeated 1st Rnd"}
THIRD_TEXT = {3: "3rd", 4: "4th"}       # message 650, "%d", with third_place


class Result:
    def __init__(self, uid, data):
        self.uid = uid
        self.values = list(struct.unpack("<4H", data))

    def __getitem__(self, name):
        return self.values[OFFSET[name] // 2]

    def __setitem__(self, name, value):
        self.values[OFFSET[name] // 2] = value

    def encode(self):
        return struct.pack("<4H", *self.values)


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, tables = tbb.parse(buf)
    if len(tables) != 1:
        raise ValueError("%d tables, expected 1" % len(tables))
    data = tables[0].data
    if len(data) % ROW:
        raise ValueError("%d bytes, not a whole number of %d-byte rows" % (len(data), ROW))
    rows = [Result(i, data[o:o + ROW]) for i, o in enumerate(range(0, len(data), ROW))]
    return buf, end, tables, rows


def place_name(r, place):
    """What the results screen shows for final place `place` (from 1) in
    row `r`, as ConvertRankToString builds it."""
    if r["kind"] == 2:
        return "-"
    if r["kind"] != 1:
        return str(place)
    clubs = SCREEN_CLUBS.get(r.uid, r["clubs"])
    if clubs <= 0:
        return ""                       # 0x2017bc: nothing written
    for first, last, msg, need in ROUNDS:
        if first <= place <= last:
            if clubs < need:
                break
            if msg == 653 and r["third_place"]:
                return THIRD_TEXT[place]
            return ROUND_TEXT[msg]
    return ROUND_TEXT[656]


def check(r):
    """Problems with row `r` against what the code reads."""
    problems = []
    if r["kind"] >= len(KINDS):
        problems.append("kind %d (0, 1 or 2)" % r["kind"])
    if r["third_place"] > 1:
        problems.append("third_place %d (compared with 1)" % r["third_place"])
    return problems


def set_field(r, name, value):
    """Set field `name` of row `r`, within what the code reads. Returns
    the old value."""
    if name not in EDITABLE:
        raise ValueError("no field %r; fields are %s" % (name, ", ".join(EDITABLE)))
    lo, hi = {"kind": (0, len(KINDS) - 1), "third_place": (0, 1)}.get(name, (0, 0xffff))
    if not lo <= value <= hi:
        raise ValueError("%s must be %d-%d" % (name, lo, hi))
    old = r[name]
    r[name] = value
    return old


# What an editor offers: (value, label) for each editable field. `clubs`
# must agree with the schedule (leaguesize.py changes a league's size), so
# an editor shows it without an input.
EDIT_CHOICES = {
    "kind": ((0, "league: the place as a number"), (1, "cup: the round's name"),
             (2, "not ranked: \"-\", no prize message")),
    "third_place": ((0, "no"), (1, "yes: places 3 and 4 are 3rd and 4th")),
}

DESCRIPTIONS = {
    "kind": "how the results list shows a club's final place",
    "third_place": "a cup with a match for third place",
    "clubs": "clubs in the schedule; names a cup's rounds",
}


def edit_choices(name):
    """[(value, label)] an editor offers for `name`, or None for a field it
    shows without an input."""
    return EDIT_CHOICES.get(name)


def encode_file(buf, end, raw, rows):
    """The whole file rebuilt from the rows, refusing rows that no longer
    fit the layout (check) or a change of size."""
    for r in rows:
        problems = check(r)
        if problems:
            raise ValueError("uid %d would not fit the layout: %s" % (r.uid, "; ".join(problems)))
    raw[0].data = b"".join(r.encode() for r in rows)
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


def other_counts(path):
    """({uid: clubs} from REGULATION.TBB, {uid: entrants} from
    SCHEDULE_COMPETITION.PAC) next to `path`, each None when missing."""
    folder = path if os.path.isdir(path) else os.path.dirname(path)
    regs = comps = None
    import regulation
    if os.path.exists(os.path.join(folder, regulation.FILE)):
        regs = {r.uid: r["clubs"] for r in regulation.load(folder)[3]}
    import schedule
    p = os.path.join(folder, schedule.COMPE_PAC)
    if os.path.exists(p):
        comps = {u: schedule.Competition(b).entrants
                 for u, (_, b) in enumerate(schedule.read_pack(p))}
    return regs, comps


# --- commands ----------------------------------------------------------------

def cmd_info(path):
    try:
        _, _, raw, rows = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    line = "%s: %d rows of %d bytes, line size %d" % (path, len(rows), ROW, raw[0].line_size)
    if len(rows) < UIDS:
        line += "  !! fewer rows than the %d schedule UIDs" % UIDS
    print(line)
    bad = 0
    for r in rows:
        problems = check(r)
        if problems:
            bad += 1
            print("uid %3d  !! %s" % (r.uid, "; ".join(problems)))
    print("%d of %d rows fit the layout" % (len(rows) - bad, len(rows)))
    print("  uid equals the row number in %d rows" % sum(r["uid"] == r.uid for r in rows))
    for k, name in enumerate(KINDS):
        print("  kind %d (%s): %d rows" % (k, name, sum(r["kind"] == k for r in rows)))
    print("  third_place set: uid %s" % " ".join(str(r.uid) for r in rows if r["third_place"]))
    regs, comps = other_counts(path)
    for what, counts in (("REGULATION.TBB clubs", regs), ("the schedule's entrants", comps)):
        if counts is None:
            continue
        diff = [r.uid for r in rows if r.uid in counts and r["clubs"] != counts[r.uid]]
        cups = [u for u in diff if rows[u]["kind"] == 1]
        print("  clubs equal %s for %d of %d UIDs%s" % (
            what, len(counts) - len(diff), len(counts),
            " (not: %s)" % " ".join(map(str, diff)) if diff else ""))
        for u in cups:
            print("  uid %3d  !! a cup with %d clubs, but %s says %d" % (
                u, rows[u]["clubs"], what, counts[u]))


def cmd_show(path, uids):
    _, _, _, rows = load(path)
    for r in rows:
        if uids and r.uid not in uids:
            continue
        kind = KINDS[r["kind"]] if r["kind"] < len(KINDS) else "?"
        line = "uid %3d  %-10s  clubs %2d" % (r.uid, kind, r["clubs"])
        if r["third_place"]:
            line += "  third-place match"
        if r["uid"] != r.uid:
            line += "  (+0x00 %d)" % r["uid"]
        if r["kind"] == 1:
            names = []
            for place in (1, 2, 3, 4, 5, 9, 17):
                names.append("%d %s" % (place, place_name(r, place)))
            line += "  places: " + ", ".join(names)
            if r.uid in SCREEN_CLUBS:
                line += "  (the screen uses %d clubs)" % SCREEN_CLUBS[r.uid]
        print(line)


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw, rows = load(path)
    target = None
    for a in args:
        if "=" not in a:
            uid = int(a, 0)
            if not 0 <= uid < len(rows):
                raise SystemExit("%s: no such uid (0-%d)" % (a, len(rows) - 1))
            target = rows[uid]
            continue
        if target is None:
            raise SystemExit("give a uid before %r" % a)
        name, value = a.split("=", 1)
        try:
            old = set_field(target, name, int(value, 0))
        except ValueError as e:
            raise SystemExit("uid %d: %s" % (target.uid, e))
        print("uid %d %s: %d -> %d" % (target.uid, name, old, target[name]))
    try:
        out = encode_file(buf, end, raw, rows)
    except ValueError as e:
        raise SystemExit(str(e))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_roundtrip(path):
    buf, end, raw, rows = load(path)
    same = b"".join(r.encode() for r in rows) == raw[0].data
    print("%d rows  %s" % (len(rows), "identical" if same else "!! re-encoded table differs"))
    try:
        out = encode_file(buf, end, raw, rows)        # the encoder `set` uses
    except ValueError as e:
        out = None
        print("%s: !! %s" % (path, e))
    if out is not None:
        print("%s: %s" % (path, "rebuilt file identical" if out == buf else "!! rebuilt file differs"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and args:
        cmd_show(args[0], [int(a, 0) for a in args[1:]])
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
