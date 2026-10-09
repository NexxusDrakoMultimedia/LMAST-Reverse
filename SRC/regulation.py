# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Match regulations: PARAM/REGULATION.TBB, for Let's Make a Soccer Team!
(PS2).

One TBB1 table (line size 2) of 120-byte rows, one per schedule UID
(PLSCHE_GROUP): Param::plRec_MatchRegulations(group) (SLES 0x21dc60)
returns row `group` (0x21dd18: group * 0x78). All 60 fields are s16 (lh).
See DOC/REGULATION_FORMAT.md.

  +0x00 grade        PlMatchGrade 0-5 (pwkUnkei_GetAllAudience 0x255b1c;
                     pwkDissatis_CompeEnd 0x23a840 indexes a 6-entry table)
  +0x02 clubs        the number of clubs (SIMPRG.REL 0x960b0, a message number)
  +0x04 ?            not traced
  +0x06 prize_kind   2: the prizes scale by the UEFA rank of the player's
                     nation, 120-80 % (plRec_GetMatchBonus 0x21e2ec)
  +0x08 win_bonus    x 10,000 per win (pwkUnkei_GetMatchIncome 0x2732b8),
                     in the game's money unit: pounds are that / 6
  +0x0a prize1-32    by final position, x 10,000 (plRec_GetMatchBonus;
                     booked as income 6 at SIMPRG.REL 0x133844)
  +0x4a ban_yellows  yellow cards that ban a player (0x2851d4; <= 0 none)
  +0x4c squad        players named for a match (0x2a37ac: bench line at - 11)
  +0x4e squad2       set with squad (VS override 0x206e28); reader not found
  +0x50 foreigners   foreign players allowed in the matchday squad (0x24c6cc)
  +0x52 subs         substitutions allowed (SIMPRG.REL 0x172b5c)
  +0x54 6 slots of {count, compe, uid}: down1, down2 counted up from the
        bottom of the table, up1-up4 down from the top
        (plRec_getNextCompetitionData 0x21df60). A count of -1 takes the
        places from the host nation's UEFA rank (tables at 0x533b10).

Usage:
    python regulation.py info      <REGULATION.TBB | DAT/PARAM>
    python regulation.py show      <REGULATION.TBB> [uid ...]
    python regulation.py set       <in.TBB> <out.TBB> <uid> <field>=<value> ... [<uid> ...]
    python regulation.py roundtrip <REGULATION.TBB>

`show` and `set` name the fields as above (prize1 is the winner's prize;
`show` gives money in pounds, as the game shows it;
slot fields are up1_count, up1_compe, up1_uid, ...). `set` writes a
same-size file for patch_disc.py, which also patches the copies in
PRELOAD/SIMFILE*.PAC (--copies).
"""
import os
import struct
import sys

import tbb

FILE = "REGULATION.TBB"
ENTRY_PAC = "SCHEDULE_TEAM_ENTRY.PAC"
ROW = 0x78                      # 0x21dd18: group * 0x78
FIELD_COUNT = ROW // 2
UIDS = 164                      # schedule UIDs 0-163 (SCHEDULE_FORMAT.md)
COMPES = 72                     # PLSCHE_COMPE 0-71
GRADES = 6                      # the float table at 0x391c18 has 6 entries
SQUAD_MIN, SQUAD_MAX = 11, 25   # bench slots 11..squad-1 of 25 (0x24c6ac, 0x24c618)
PRIZES = 32                     # plRec_GetMatchBonus: rank + 1 < 0x21
MONEY_UNIT = 10000              # 0x2732b8 and SIMPRG.REL 0x133844
POUND = 6                       # the game's money unit / 6 = pounds (SAVE_FORMAT.md)
PRIZE_SCALED = 2                # prize_kind that scales by UEFA rank (0x21e2ec)
UEFA_PERCENT = (120, 110, 105, 100, 90, 80)     # 0x533b88, by UEFA rank 1-6

# Places a count of -1 gives, by tier (UEFA rank - 1) // 3: tables at
# 0x533b10/18/20 picked by compe 33-35, or by uid 58-75 when compe is -1
# (jump table 0x533b30; uid 67 gives nothing).
UEFA_PLACES = {"compe": {33: (2, 1), 34: (2, 2), 35: (3, 3)},
               "uid": dict([(58, (2, 1))] + [(u, (2, 2)) for u in range(59, 67)] +
                           [(u, (3, 3)) for u in range(68, 76)])}

SLOTS = (("down1", 0x54), ("down2", 0x5a),
         ("up1", 0x60), ("up2", 0x66), ("up3", 0x6c), ("up4", 0x72))
FIELDS = ([("grade", 0x00), ("clubs", 0x02), ("unk04", 0x04), ("prize_kind", 0x06),
           ("win_bonus", 0x08)] +
          [("prize%d" % (i + 1), 0x0a + 2 * i) for i in range(PRIZES)] +
          [("ban_yellows", 0x4a), ("squad", 0x4c), ("squad2", 0x4e),
           ("foreigners", 0x50), ("subs", 0x52)] +
          [("%s_%s" % (s, f), o + 2 * k) for s, o in SLOTS
           for k, f in enumerate(("count", "compe", "uid"))])
OFFSET = dict(FIELDS)


class Regulation:
    def __init__(self, uid, data):
        self.uid = uid
        self.values = list(struct.unpack("<%dh" % FIELD_COUNT, data))

    def __getitem__(self, name):
        return self.values[OFFSET[name] // 2]

    def __setitem__(self, name, value):
        self.values[OFFSET[name] // 2] = value

    def encode(self):
        return struct.pack("<%dh" % FIELD_COUNT, *self.values)

    def slot(self, name):
        return tuple(self["%s_%s" % (name, f)] for f in ("count", "compe", "uid"))

    def prizes(self):
        return [self["prize%d" % (i + 1)] for i in range(PRIZES)]


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
    rows = [Regulation(i, data[o:o + ROW]) for i, o in enumerate(range(0, len(data), ROW))]
    return buf, end, tables, rows


def uefa_places(compe, uid):
    """(tier 0, tier 1) places a slot with count -1 gives, or None when
    the code finds no table for it and gives no places (0x21e16c)."""
    if compe in UEFA_PLACES["compe"]:
        return UEFA_PLACES["compe"][compe]
    if compe == -1:
        return UEFA_PLACES["uid"].get(uid)
    return None


def read_slots(r, names):
    """The slots plRec_getNextCompetitionData walks: it stops at the first
    count of 0 (0x21dfe8, 0x21e1cc)."""
    out = []
    for name in names:
        s = r.slot(name)
        if s[0] == 0:
            break
        out.append((name, s))
    return out


def check(r):
    """Problems with row `r` against what the code reads."""
    problems = []
    if not 0 <= r["grade"] < GRADES:
        problems.append("grade %d (0x391c18 has %d entries)" % (r["grade"], GRADES))
    for name in ("squad", "squad2"):
        if not SQUAD_MIN <= r[name] <= SQUAD_MAX:
            problems.append("%s %d not %d-%d" % (name, r[name], SQUAD_MIN, SQUAD_MAX))
    if r["subs"] < 0:
        problems.append("subs %d" % r["subs"])
    for names in (("down1", "down2"), ("up1", "up2", "up3", "up4")):
        walked = read_slots(r, names)
        for name in names[len(walked):]:
            if r.slot(name)[0]:
                problems.append("%s %s is after a count of 0 and never read" % (name, r.slot(name)))
        for name, (count, compe, uid) in walked:
            if count < -1:
                problems.append("%s count %d" % (name, count))
            if not -1 <= compe < COMPES:
                problems.append("%s compe %d" % (name, compe))
            if not -1 <= uid < UIDS:
                problems.append("%s uid %d" % (name, uid))
    return problems


def pounds(value):
    """A field's money as the game shows it in pounds (rounded down)."""
    return "GBP {:,}".format(value * MONEY_UNIT // POUND)


def slot_text(count, compe, uid):
    if count == -1:
        p = uefa_places(compe, uid)
        n = "%d/%d by UEFA rank" % p if p else "none (no UEFA table)"
    else:
        n = str(count)
    to = []
    if compe != -1:
        to.append("compe %d" % compe)
    if uid != -1:
        to.append("uid %d" % uid)
    return "%s -> %s" % (n, ", ".join(to) or "-")


def entry_slots(path):
    """{uid: slots} from SCHEDULE_TEAM_ENTRY.PAC next to `path`, or None."""
    p = os.path.join(os.path.dirname(path) if not os.path.isdir(path) else path, ENTRY_PAC)
    if not os.path.exists(p):
        return None
    import schedule
    return {u: schedule.TeamEntry(b).slots for u, (_, b) in enumerate(schedule.read_pack(p))}


def set_field(r, name, value):
    """Set field `name` of row `r`, within what the code reads. Returns
    the old value."""
    if name not in OFFSET:
        raise ValueError("no field %r; fields are %s" % (name, ", ".join(n for n, _ in FIELDS)))
    lo, hi = -0x8000, 0x7fff
    if name == "grade":
        lo, hi = 0, GRADES - 1
    elif name in ("squad", "squad2"):
        lo, hi = SQUAD_MIN, SQUAD_MAX
    elif name.endswith("_count"):
        lo = -1
    elif name.endswith("_compe"):
        lo, hi = -1, COMPES - 1
    elif name.endswith("_uid"):
        lo, hi = -1, UIDS - 1
    if not lo <= value <= hi:
        raise ValueError("%s must be %d-%d" % (name, lo, hi))
    old = r[name]
    r[name] = value
    return old


# What an editor offers, narrower than set_field allows: the values on the
# disc and their neighbours. ban_yellows 255 is "no ban" on the disc.
# `clubs` must agree with the schedule packs (leaguesize.py changes a
# division's size), and `squad2` follows `squad` (the VS override at
# 0x206e28 writes both), so an editor shows them without its own input.
EDIT_RANGES = {
    "grade": (0, GRADES - 1),
    "prize_kind": (0, 2),
    "win_bonus": (0, 0x7fff),
    "ban_yellows": (0, 255),
    "squad": (SQUAD_MIN, SQUAD_MAX),
    "foreigners": (0, SQUAD_MAX),
    "subs": (0, SQUAD_MAX - SQUAD_MIN),
}


FOLLOWS = {"squad": ("squad2",)}      # an editor sets these with the field

DESCRIPTIONS = {
    "grade": "match grade, 0 the top (European and national-team); feeds attendance",
    "clubs": "clubs in the schedule; a division's size is changed in the schedule packs",
    "unk04": "not traced",
    "prize_kind": "2: prizes scale by your nation's UEFA rank, 120% (rank 1) to 80% (rank 6)",
    "win_bonus": "paid for each win",
    "ban_yellows": "yellow cards that ban a player; 255 never",
    "squad": "players named for a match: 11 starters and the bench",
    "squad2": "always equal to the squad",
    "foreigners": "foreign players allowed among them",
    "subs": "substitutions allowed in a match",
}


def edit_range(name):
    """(low, high) an editor offers for `name`, or None for fields it
    shows without an input: +0x04 (not traced), clubs and squad2."""
    if name in ("unk04", "clubs", "squad2"):
        return None
    if name in EDIT_RANGES:
        return EDIT_RANGES[name]
    if name.startswith("prize"):
        return (0, 0x7fff)
    if name.endswith("_count"):
        return (-1, 32)
    if name.endswith("_compe"):
        return (-1, COMPES - 1)
    return (-1, UIDS - 1)


def uid_names(root, over=None):
    """{uid: name} from the schedule packs of the DAT/PARAM folder `root`
    (each file from `over` when it is there): the six nations' divisions
    by name, other UIDs by competition and when they are loaded."""
    import leaguesize
    import schedule
    data = leaguesize.load(root, over)
    names = {u: "competition %d, %s" % (r.compe, schedule.LOAD_KIND.get(r.kind, r.kind))
             for u, (r, _) in schedule.year_uids(data[0].year).items()}
    for league, nation in enumerate(leaguesize.LEAGUE_NAMES):
        n = leaguesize.Nation(*data[:3], league)
        names[n.d1] = "%s first division" % nation
        names[n.own] = "%s second division (your nation)" % nation
        names[n.other] = "%s second division (other nations)" % nation
    return names


def encode_file(buf, end, raw, rows):
    """The whole file rebuilt from the rows, refusing rows that no longer
    fit the layout (check) or a change of size."""
    for r in rows:
        problems = check(r)
        if problems:
            raise ValueError("uid %d would not fit the layout: %s" % (r.uid, "; ".join(problems[:3])))
    raw[0].data = b"".join(r.encode() for r in rows)
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


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
    for name in ("grade", "prize_kind", "unk04", "ban_yellows", "squad", "foreigners", "subs"):
        values = sorted(set(r[name] for r in rows))
        print("  %-11s %s" % (name, " ".join(map(str, values))))
    slots = entry_slots(path)
    if slots is not None:
        diff = [u for u in slots if u < len(rows) and rows[u]["clubs"] != slots[u]]
        print("clubs equal the team-entry slots for %d of %d UIDs%s" % (
            len(slots) - len(diff), len(slots),
            " (not: %s)" % " ".join(map(str, diff)) if diff else ""))


def cmd_show(path, uids):
    _, _, _, rows = load(path)
    for r in rows:
        if uids and r.uid not in uids:
            continue
        prizes = r.prizes()
        while prizes and prizes[-1] == 0:
            prizes.pop()
        print("uid %3d  grade %d  clubs %2d  +0x04 %2d  win bonus %s  "
              "ban at %d yellows  squad %d/%d  foreigners %d  subs %d" % (
                  r.uid, r["grade"], r["clubs"], r["unk04"], pounds(r["win_bonus"]),
                  r["ban_yellows"], r["squad"], r["squad2"], r["foreigners"], r["subs"]))
        if prizes:
            print("    prizes (kind %d): %s" % (r["prize_kind"], " ".join(
                pounds(p) for p in prizes)))
        for names, where in ((("up1", "up2", "up3", "up4"), "top"), (("down1", "down2"), "bottom")):
            for name, s in read_slots(r, names):
                print("    %-5s %s (from the %s)" % (name, slot_text(*s), where))


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
