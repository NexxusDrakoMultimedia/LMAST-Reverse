# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The club events (PR activities) in the executable, for Let's Make a
Soccer Team! (PS2).

The Publicity Department's 46 events come from three tables in
SLES_541.51, one record per event, and are named in MES.PAC category 572
(id = event, its description 5000 + event). PARAM/CLUBEVENT.TBB is an
older copy that no code reads. See DOC/CLUBEVENT_FORMAT.md.

    0x52ff58  46 x 32 bytes   when the event is offered and what it costs
              plClubEvent_GetList (0x20e488), _GetCost (0x20dee0),
              _NeedMatch (0x20ea00)
    0x530518  46 x 8 bytes    its chance of success
              plClubEvent_Execute (0x20df50)
    0x530688  46 x 28 bytes   what success brings
              plClubEvent_Execute, _GetTicket (0x20df00)
    0x52ff48  4 x s32         the priorities the list is filled by
              (100, 90, 80, 50), plClubEvent_GetList

The offer record (plClubEvent_GetList, 0x20e5c0-0x20e878):

    +0x00 u32  the event's month rule, kept in the code by event: 22 in
               January or August, 30 in July or August, 31 in December,
               32 from November to January, 35-37 from January to
               August. 0: none, and +0x18 applies instead
    +0x04 u16  the first season it is offered: 2006 + n (0 from the start)
    +0x06 u16  the home popularity it needs (block 1 +0x11248)
    +0x08 u8   2 or more: office equipment 3 at level n - 1 or higher
               (pwkTeam_GetOfficeEquipsLv)
    +0x09 u8   priority: the list takes up to 10 events, those at 100 or
               more first, then 90, 80 and 50; under 50, never
    +0x0a u8   a cap on a count the caller passes; SIMPRG.REL 0xa4150
               passes none, so it is never read
    +0x0b u8   not offered while it was held within that many turns
               (0x20e230 walks the calendar's +0x38)
    +0x0c u8   needs a successful event 27 (PR Strategy Talks) last month
               (0x20e3f0)
    +0x10 u32  in June only, when your club won its league (0x20e2d8)
    +0x14 u32  the cost, x 300 in the stored unit (x 50 in pounds)
    +0x18 u32  not offered in July
    +0x1c u32  needs a match that day (plClubEvent_NeedMatch)

Event 45 (Club Party) is offered only while a player promise 7 or 11 or
the manager's promise 37 stands, and goes first; event 37 (Renew Mobile
Site) is never offered (0x20e864).

The chance record: byte 0 the base, bytes 1-4 the business cycle's
changes (signed), 6 a bonus a stub never grants, 7 a bonus when the club
status is over 49,999; byte 5 is never read. Success when
fcEuroRand_Get0toI(100) is at most the sum (DOC/ECONOMY.md#pr-events).

The success record, 7 s32: +0x00 and +0x04 the popularity of the players
named in the event's schedule entry (overseas, home; plPinfo_ChangePop),
+0x08 home and +0x0c overseas popularity (pwkTeam_PopChange), +0x10
youth development (pwkYouthDev_Add), +0x14 supporter complaint kind 4,
+0x18 the ticket bonus in percent for that day's match.

Usage:
    python clubevent.py info      <ISO dir | executable>
    python clubevent.py show      <ISO dir | executable> [MES.PAC]
    python clubevent.py set       <in exe> <out exe> <event>:<field>=<value> ...
    python clubevent.py roundtrip <ISO dir | executable>

`show` names the events from MES.PAC when given, and gives each one's
chance as the retail code works it out (without `--mod pr-cycle`).
`set` writes a same-size executable for patch_disc.py (target
disc:SLES_541.51). The fields, by event 0-45:

    month_rule    0-1       offer +0x00
    first_season  0-50      offer +0x04, from the season 2006 + n
    popularity    0-65535   offer +0x06, the home popularity it needs
    office        0-3       offer +0x08
    priority      0-255     offer +0x09
    gap           0-255     offer +0x0b, turns
    talks         0-1       offer +0x0c, after PR Strategy Talks
    title         0-1       offer +0x10, June after a league title
    cost          0-1000000 offer +0x14, x 50 in pounds
    not_july      0-1       offer +0x18
    match         0-1       offer +0x1c
    base          0-100     chance byte 0
    boom          -100-100  chance byte 1: business cycle 0 (unread, retail)
    good          -100-100  chance byte 2: cycle 1 (retail: cycles 0 and 1)
    poor          -100-100  chance byte 3: cycle 3 (retail: cycles 3 and 4)
    slump         -100-100  chance byte 4: cycle 4 (retail: cycle 2)
    bonus6        -100-100  chance byte 6, never granted
    status_bonus  -100-100  chance byte 7, club status over 49,999
    pop_overseas  +-65535   success +0x00, the named players
    pop_home      +-65535   success +0x04, the named players
    club_home     +-65535   success +0x08
    club_overseas +-65535   success +0x0c
    youth         +-65535   success +0x10
    complaint     +-65535   success +0x14
    ticket        -100-1000 success +0x18, percent

for example `set ISO/SLES_541.51 out.elf 27:cost=400 38:ticket=10`.
"""
import os
import struct
import sys

import gamever
import sles_disasm

EVENTS = 46
OFFER_TABLE, OFFER_SIZE = 0x52ff58, 0x20      # plClubEvent_GetList, _GetCost
CHANCE_TABLE, CHANCE_SIZE = 0x530518, 8       # plClubEvent_Execute
RESULT_TABLE, RESULT_SIZE = 0x530688, 0x1c    # plClubEvent_Execute, _GetTicket
PRIORITIES = 0x52ff48                         # 4 s32, copied at 0x20e888
LIST_MAX = 10                                 # 0x20e928: slti $a3, 0xa
COST_UNIT = 300                               # plClubEvent_GetCost: x 300
STORED_PER_POUND = 6
FIRST_SEASON = 2006                           # 0x20e5cc: + 0x7d6
TALKS, PARTY, NEVER = 27, 45, 37              # 0x20e3f0, 0x20e84c, 0x20e864
NAME_CATEGORY, DESCRIPTION_BASE = 572, 5000

# (name, table, offset, struct format, low, high). Byte 1-4 and 6-7 of the
# chance record are added as bytes, so they are kept signed here.
OFFER, CHANCE, RESULT = "offer", "chance", "result"
FIELDS = (
    ("month_rule", OFFER, 0x00, "<I", 0, 1),
    ("first_season", OFFER, 0x04, "<H", 0, 50),
    ("popularity", OFFER, 0x06, "<H", 0, 0xffff),
    ("office", OFFER, 0x08, "<B", 0, 3),
    ("priority", OFFER, 0x09, "<B", 0, 0xff),
    ("gap", OFFER, 0x0b, "<B", 0, 0xff),
    ("talks", OFFER, 0x0c, "<B", 0, 1),
    ("title", OFFER, 0x10, "<I", 0, 1),
    ("cost", OFFER, 0x14, "<I", 0, 1000000),
    ("not_july", OFFER, 0x18, "<I", 0, 1),
    ("match", OFFER, 0x1c, "<I", 0, 1),
    ("base", CHANCE, 0, "<b", 0, 100),
    ("boom", CHANCE, 1, "<b", -100, 100),
    ("good", CHANCE, 2, "<b", -100, 100),
    ("poor", CHANCE, 3, "<b", -100, 100),
    ("slump", CHANCE, 4, "<b", -100, 100),
    ("bonus6", CHANCE, 6, "<b", -100, 100),
    ("status_bonus", CHANCE, 7, "<b", -100, 100),
    ("pop_overseas", RESULT, 0x00, "<i", -0xffff, 0xffff),
    ("pop_home", RESULT, 0x04, "<i", -0xffff, 0xffff),
    ("club_home", RESULT, 0x08, "<i", -0xffff, 0xffff),
    ("club_overseas", RESULT, 0x0c, "<i", -0xffff, 0xffff),
    ("youth", RESULT, 0x10, "<i", -0xffff, 0xffff),
    ("complaint", RESULT, 0x14, "<i", -0xffff, 0xffff),
    ("ticket", RESULT, 0x18, "<i", -100, 1000),
)
FIELD = {f[0]: f for f in FIELDS}
# What each field does, as the editor labels it.
HELP = {
    "month_rule": "keep the event's month rule (events 22, 30-32, 35-37); 0 drops it",
    "first_season": "the first season it is offered: 2006 + n (0 from the start)",
    "popularity": "the home popularity it needs (0 none)",
    "office": "2 or 3: needs office equipment 3 at level 1 or 2",
    "priority": "the list takes 10 events: 100 or more first, then 90, 80, 50; under 50 never",
    "gap": "turns that must pass before it is offered again (8 a month)",
    "talks": "needs a successful PR Strategy Talks the month before",
    "title": "June only, after your club wins its league",
    "cost": "x 50 in pounds",
    "not_july": "not offered in July (events without a month rule)",
    "match": "only on a day with a match",
    "base": "the chance: rand(100) at most the sum succeeds",
    "boom": "added in a boom (cycle 0); the retail code never reads it",
    "good": "added in cycle 1; the retail code reads it in cycles 0 and 1",
    "poor": "added in cycle 3; the retail code reads it in cycles 3 and 4",
    "slump": "added in a slump (cycle 4); the retail code reads it in cycle 2",
    "bonus6": "a bonus the code never grants (a stub)",
    "status_bonus": "added when the club status is over 49,999",
    "pop_overseas": "the overseas popularity of the players taking part",
    "pop_home": "the home popularity of the players taking part",
    "club_home": "the club's home popularity",
    "club_overseas": "the club's popularity in every overseas region",
    "youth": "youth development",
    "complaint": "supporter complaints (kind 4); negative calms them",
    "ticket": "extra crowd at that day's match, percent",
}
# Bytes no code reads, which `info` checks are as on the disc.
UNREAD = ((OFFER, 0x0a, 1), (OFFER, 0x0d, 3), (CHANCE, 5, 1))
# Events with a month rule in the code (0x20e5f4-0x20e6e8): (event, months).
MONTHS = {22: (1, 8), 30: (7, 8), 31: (12,), 32: (11, 12, 1), 35: tuple(range(1, 9)),
          36: tuple(range(1, 9)), 37: tuple(range(1, 9))}
MONTH_NAMES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
               "Nov", "Dec")


def exe_of(path):
    return gamever.exe_path(path) if os.path.isdir(path) else path


class Events:
    """The three tables of an executable, in place in a copy of its bytes."""

    def __init__(self, path):
        self.path = exe_of(path)
        self.elf = sles_disasm.Elf(self.path)
        self.data = bytearray(self.elf.data)
        self.base = {}
        for table, addr, size in ((OFFER, OFFER_TABLE, OFFER_SIZE),
                                  (CHANCE, CHANCE_TABLE, CHANCE_SIZE),
                                  (RESULT, RESULT_TABLE, RESULT_SIZE)):
            o = self.elf.v2f(gamever.at(self.path, addr))
            if o is None or o + EVENTS * size > len(self.data):
                raise ValueError("%s: no %s table" % (self.path, table))
            self.base[table] = (o, size)
        o = self.elf.v2f(gamever.at(self.path, PRIORITIES))
        self.priorities = struct.unpack_from("<4i", self.data, o)

    def offset(self, event, table, at):
        if not 0 <= event < EVENTS:
            raise ValueError("no event %d (0-%d)" % (event, EVENTS - 1))
        o, size = self.base[table]
        return o + event * size + at

    def get(self, event, name):
        _, table, at, fmt, _, _ = field(name)
        return struct.unpack_from(fmt, self.data, self.offset(event, table, at))[0]

    def set(self, event, name, value):
        """Set one field; returns the old value."""
        _, table, at, fmt, lo, hi = field(name)
        if not lo <= value <= hi:
            raise ValueError("%s is %d-%d" % (name, lo, hi))
        old = self.get(event, name)
        struct.pack_into(fmt, self.data, self.offset(event, table, at), value)
        return old

    def raw(self, event, table, at, n):
        o = self.offset(event, table, at)
        return bytes(self.data[o:o + n])

    def encode(self):
        """The executable with the edited tables: a re-encode of every
        field into the original bytes, so an unedited copy comes out the
        same."""
        out = bytearray(self.elf.data)
        for event in range(EVENTS):
            for name, table, at, fmt, _, _ in FIELDS:
                struct.pack_into(fmt, out, self.offset(event, table, at), self.get(event, name))
            for table, at, n in UNREAD:
                o = self.offset(event, table, at)
                out[o:o + n] = self.data[o:o + n]
        return bytes(out)


def field(name):
    if name not in FIELD:
        raise ValueError("no field %r (%s)" % (name, ", ".join(FIELD)))
    return FIELD[name]


def edit_spec(name):
    """The values a field allows, as the editor's inputs take them."""
    _, _, _, _, lo, hi = field(name)
    return ("range", lo, hi)


def check(ev):
    """Problems: values outside the ranges `set` takes, and unread bytes
    that aren't as on the disc."""
    problems = []
    for event in range(EVENTS):
        for name, _, _, _, lo, hi in FIELDS:
            v = ev.get(event, name)
            if not lo <= v <= hi:
                problems.append("event %d: %s %d" % (event, name, v))
        if ev.raw(event, OFFER, 0x0d, 3) != bytes(3):
            problems.append("event %d: offer +0x0d-0x0f not zero" % event)
        if ev.get(event, "month_rule") and event not in MONTHS:
            problems.append("event %d: a month rule the code doesn't have" % event)
    if ev.priorities != (100, 90, 80, 50):
        problems.append("priorities %s" % (ev.priorities,))
    return problems


def names(mes_path):
    """{event: name}, {event: description} from MES.PAC category 572."""
    if not mes_path:
        return {}, {}
    import camp
    m = camp.messages(mes_path, NAME_CATEGORY)
    return ({e: m[e].strip() for e in range(EVENTS) if e in m},
            {e: m[DESCRIPTION_BASE + e].strip() for e in range(EVENTS)
             if DESCRIPTION_BASE + e in m})


def pounds(cost):
    return cost * COST_UNIT // STORED_PER_POUND


def chance(ev, event, cycle=2, status=0):
    """The chance of success in percent the retail code gives in business
    cycle 0-4 (ECONOMY.md: it reads byte 2 for cycles 0 and 1, byte 4 for
    2 and byte 3 for 3 and 4), with or without the status bonus."""
    byte = {0: "good", 1: "good", 2: "slump", 3: "poor", 4: "poor"}[cycle]
    total = ev.get(event, "base") + ev.get(event, byte)
    if status:
        total += ev.get(event, "status_bonus")
    return max(0, min(100, (total & 0xff) + 1))


def conditions(ev, event):
    """When an event is offered, in words."""
    out = []
    if event == NEVER:
        out.append("never offered")
    if event == PARTY:
        out.append("while a promise stands, first")
    if ev.get(event, "month_rule") and event in MONTHS:
        out.append("in " + ", ".join(MONTH_NAMES[m - 1] for m in MONTHS[event]))
    elif ev.get(event, "not_july"):
        out.append("not in July")
    if ev.get(event, "first_season"):
        y = FIRST_SEASON + ev.get(event, "first_season")
        out.append("from %d-%02d" % (y, (y + 1) % 100))
    if ev.get(event, "popularity"):
        out.append("home popularity %d+" % ev.get(event, "popularity"))
    if ev.get(event, "office") >= 2:
        out.append("office equipment 3 level %d+" % (ev.get(event, "office") - 1))
    if ev.get(event, "talks"):
        out.append("after PR Strategy Talks")
    if ev.get(event, "title"):
        out.append("June after a league title")
    if ev.get(event, "match"):
        out.append("on a match day")
    if ev.get(event, "gap"):
        out.append("%d turns apart" % ev.get(event, "gap"))
    if ev.get(event, "priority") < min(ev.priorities):
        out.append("priority too low to be listed")
    return out


def results(ev, event):
    out = []
    for name, label in (("club_home", "home popularity"), ("club_overseas", "overseas popularity"),
                        ("pop_home", "players' home popularity"),
                        ("pop_overseas", "players' overseas popularity"),
                        ("youth", "youth development"), ("complaint", "complaints"),
                        ("ticket", "tickets %")):
        v = ev.get(event, name)
        if v:
            out.append("%s %+d" % (label, v))
    return out


# --- commands ----------------------------------------------------------------

def cmd_info(path):
    try:
        ev = Events(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    problems = check(ev)
    print("%s: %d events at %s" % (ev.path.replace("\\", "/"), EVENTS, ", ".join(
        "%s %#x" % (t, ev.elf.f2v(o)) for t, (o, _) in ev.base.items()))
          + ("  !! " + "; ".join(problems) if problems else ""))
    listed = [e for e in range(EVENTS) if ev.get(e, "priority") >= min(ev.priorities)]
    print("  priorities %s; %d events can be listed" % (
        " ".join(map(str, ev.priorities)), len(listed)))


def cmd_show(path, mes=None):
    ev = Events(path)
    name, _ = names(mes)
    for e in range(EVENTS):
        print("%2d %-20s cost £%s, priority %d; chance %d%% (%d%% in a boom); %s" % (
            e, name.get(e, ""), format(pounds(ev.get(e, "cost")), ","), ev.get(e, "priority"),
            chance(ev, e), chance(ev, e, 0), "; ".join(results(ev, e)) or "nothing"))
        when = conditions(ev, e)
        if when:
            print("   offered: %s" % "; ".join(when))


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(exe_of(path)):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    ev = Events(path)
    for a in args:
        key, _, v = a.partition("=")
        event, _, name = key.partition(":")
        try:
            event, value = int(event, 0), int(v, 0)
        except ValueError:
            raise SystemExit("expected <event>:<field>=<number>, got %r" % a)
        try:
            old = ev.set(event, name, value)
        except ValueError as e:
            raise SystemExit("%s: %s" % (a, e))
        print("event %d %s: %d -> %d" % (event, name, old, value))
    with open(out_path, "wb") as f:
        f.write(ev.encode())
    print("wrote %s" % out_path)


def cmd_roundtrip(path):
    ev = Events(path)
    same = ev.encode() == ev.elf.data
    print("%s: %s" % (ev.path.replace("\\", "/"), "rebuilt file identical" if same
                      else "!! rebuilt file differs"))


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
