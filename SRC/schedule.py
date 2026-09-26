"""Season schedule reader for Let's Make a Soccer Team! (PS2).

The season calendar lives in three BINPAC packs in DAT/PARAM, all full of
TBB1 tables (see DOC/SCHEDULE_FORMAT.md):

  SCHEDULE_SYSTEM.PAC       5 named TBBs. year_schedule_data: one 20-byte
                            row per schedule UID (0-163): competition, load
                            condition, and a 96-bit mask of the turns with
                            games. open_nation: 72 rows of host nations.
                            make_list: team-list definitions. savectrl: one
                            save-buffer type per UID.
  SCHEDULE_COMPETITION.PAC  164 entries, one per UID: a 16-byte header, the
                            games (4 bytes each) and the pairings.
  SCHEDULE_TEAM_ENTRY.PAC   164 entries: where each entrant slot's team
                            comes from (last season's rank, a current table
                            position, a random pick from a list, a fixed team).

Confirmed from SLES_541.51: ScheEuro_SubCtrl::initYearScheduleData
(0x20a008), getYearSchedule (0x20a170), get_open_turn (0x209968),
getOpenNation (0x209f40), CScheEuro_*::acceptLoadRequest (0x2072a8,
0x207458, 0x2075c8), CScheEuro::OneLoadCompCB (0x2068f8),
Sche_Block_decode_main2 (0x2dc258), getOneGameFromBlockAndGameIndex
(0x2dab38), ScheEuro_TeamEntry::makeTeamEntryIDList (0x20a298) and its
four *_TeamEntryProc handlers, ScheEuro_TeamEntryList::requestMakeList
(0x20b188).

`info` checks every entry against that layout and cross-checks the packs:
each competition's game days against its UID's turn mask, and its entrant
count against the team-entry slots.

Usage:
    python schedule.py info  <DAT/PARAM>            # check all three packs
    python schedule.py year  <DAT/PARAM>            # one line per year_schedule_data row
    python schedule.py compe <DAT/PARAM> <uid>      # header, games and pairings of one UID
    python schedule.py entry <DAT/PARAM> <uid>      # team-entry slots of one UID
"""
import os
import struct
import sys
from collections import Counter

import pac
import tbb

SYSTEM_PAC = "SCHEDULE_SYSTEM.PAC"
COMPE_PAC = "SCHEDULE_COMPETITION.PAC"
ENTRY_PAC = "SCHEDULE_TEAM_ENTRY.PAC"

UID_COUNT = 164
TURNS_PER_YEAR = 96         # get_open_turn: open turn = years * 0x60 + bit
YEAR_ROW = 0x14             # year_schedule_data row size
OPEN_NATION_ROW = 0x2c      # s16 compe, s16 start, s16 nation[20]
MAKE_LIST_ROW = 4
ENTRY_ROW = 6               # every team-entry record
COMPE_HEADER = 0x10
GAME_ROW = 4
PAIR_ROW = 2
MAX_TEAM = 0x22d            # PlTeamId_TeamEntryProc fills 1 <= id <= 0x22d, skips others

# year_schedule_data +6: which mode loads the UID (acceptLoadRequest).
LOAD_KIND = {0: "always", 1: "own-nation", 2: "other-nations", 3: "runtime",
             4: "first-promote", 5: "vs"}
# Competition header +4 (Sche_Block_decode_main2 allocates the next-pairing
# table only for 1).
COMPE_TYPE = {0: "league", 1: "knockout"}
# make_list +2, through the jump table at 0x52fb10.
SRC_KIND = {0: "uefa", 1: "uefa", 2: "clubrank", 3: "clubrank", 4: "fifa",
            5: "fifa", 6: "list", 7: "domestic"}
# LIST records with a negative kind (List_TeamEntryProc 0x20a91c). Any
# other negative kind leaves the slot empty.
LIST_SPECIAL = {-4: "host-nation-team", -3: "team-1"}


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def u16(b, o):
    return struct.unpack_from("<H", b, o)[0]


def bits(mask):
    return [i * 8 + k for i, b in enumerate(mask) for k in range(8) if b >> k & 1]


# --- SCHEDULE_SYSTEM ---------------------------------------------------------

class YearRow:
    def __init__(self, raw):
        self.raw = raw
        self.uid = s16(raw, 0)          # -1: second-year part of the row before
        self.start, self.end = raw[2], raw[3]
        self.compe = struct.unpack_from("<b", raw, 4)[0]
        self.cycle = raw[5]             # year of the 4-year cycle, 0xff = every year
        self.kind, self.flag = raw[6], raw[7]
        self.turns = bits(raw[8:20])


def year_uids(rows):
    """{uid: (row, continuation row or None)} as getYearSchedule pairs them."""
    out = {}
    for i, r in enumerate(rows):
        if r.uid < 0:
            continue
        nxt = rows[i + 1] if i + 1 < len(rows) and rows[i + 1].uid == -1 else None
        out[r.uid] = (r, nxt)
    return out


class System:
    NAMES = ("year_schedule_data.tbb", "open_nation.tbb", "make_list.tbb",
             "PeriodName.tbb", "savectrl.tbb")

    def __init__(self, entries):
        names = [n for n, _ in entries]
        if names != list(self.NAMES):
            raise ValueError("unexpected entries %s" % ", ".join(names))
        t = [tbb.parse(buf)[1] for _, buf in entries]
        year = t[0][0].data
        if len(year) % YEAR_ROW:
            raise ValueError("year_schedule_data is not a whole number of rows")
        self.year = [YearRow(year[i:i + YEAR_ROW]) for i in range(0, len(year), YEAR_ROW)]
        on = t[1][0].data
        if len(on) % OPEN_NATION_ROW:
            raise ValueError("open_nation is not a whole number of rows")
        self.open_nation = [struct.unpack_from("<22h", on, i)
                            for i in range(0, len(on), OPEN_NATION_ROW)]
        ml = t[2][0].data
        self.make_list = [ml[i:i + MAKE_LIST_ROW] for i in range(0, len(ml), MAKE_LIST_ROW)]
        self.make_list_tables = len(t[2])
        self.savectrl = t[4][0].data


# --- SCHEDULE_COMPETITION ----------------------------------------------------

class Game:
    def __init__(self, w0, w1):
        self.day = w0 & 0xff
        self.flag = (w0 >> 8) & 3       # unknown
        self.round = (w0 >> 10) & 0xf   # 1 final, 2 semi, 3 quarter, 4 last 16, 0 other
        self.pair = w1 & 0x1ff
        self.swap = (w1 >> 9) & 3       # home = pair[swap], away = pair[1 - swap]
        self.spare = (w0 >> 14, w1 >> 11)


class Competition:
    def __init__(self, buf):
        _, t = tbb.parse(buf)
        if len(t) not in (3, 4):
            raise ValueError("%d tables, expected 3 or 4" % len(t))
        h = t[0].data
        if len(h) != COMPE_HEADER:
            raise ValueError("header is %d bytes" % len(h))
        self.tables = len(t)
        self.header = h
        self.uid, self.compe = u16(h, 0), u16(h, 2)     # not read by the game
        self.type, self.entrants = h[4], h[5]
        self.pair_count, self.game_count = u16(h, 6), u16(h, 8)
        g = t[1].data
        self.games = [Game(*struct.unpack_from("<HH", g, i)) for i in range(0, len(g) - 3, GAME_ROW)]
        self.game_bytes = len(g)
        p = t[2].data
        self.pairs = [(p[i], p[i + 1]) for i in range(0, len(p) - 1, PAIR_ROW)]
        self.next = None
        if len(t) == 4:
            n = t[3].data
            self.next = [(n[i], n[i + 1]) for i in range(0, len(n) - 1, PAIR_ROW)]

    @property
    def days(self):
        return max(g.day for g in self.games) + 1 if self.games else 0

    def problems(self):
        out = []
        if self.type not in COMPE_TYPE:
            out.append("type %d" % self.type)
        if self.tables != (4 if self.type == 1 else 3):
            out.append("%d tables for type %d" % (self.tables, self.type))
        if self.game_bytes != self.game_count * GAME_ROW:
            out.append("%d game bytes for %d games" % (self.game_bytes, self.game_count))
        if len(self.pairs) != self.pair_count:
            out.append("%d pairings, header says %d" % (len(self.pairs), self.pair_count))
        if self.next is not None and len(self.next) != self.pair_count:
            out.append("%d next links for %d pairings" % (len(self.next), self.pair_count))
        if any(g.spare != (0, 0) for g in self.games):
            out.append("games use bits 14-15 / 11-15")
        if any(g.pair >= self.pair_count for g in self.games):
            out.append("game pairing index out of range")
        if any(g.swap > 1 for g in self.games):
            out.append("home/away swap > 1")
        if sorted(set(g.day for g in self.games)) != list(range(self.days)):
            out.append("game days not contiguous from 0")
        if self.type == 0:
            if any(a >= self.entrants or b >= self.entrants for a, b in self.pairs):
                out.append("league pairing slot >= %d entrants" % self.entrants)
        elif self.type == 1:
            # A knockout's first-round pairings name entrant slots; later
            # pairings name winner slots after them.
            if any(max(a, b) >= 2 * self.pair_count for a, b in self.pairs):
                out.append("knockout pairing slot out of range")
            # A link at or past the pairing count sends the winner out of
            # this competition (single-round ties, the final).
            if any(n >= 2 * self.pair_count or s > 1 for n, s in self.next):
                out.append("next-pairing link out of range")
        return out


# --- SCHEDULE_TEAM_ENTRY -----------------------------------------------------

class TeamEntry:
    KINDS = ("last_rank", "list", "now_rank", "plteamid")

    def __init__(self, buf):
        _, t = tbb.parse(buf)
        if len(t) not in (4, 5):
            raise ValueError("%d tables, expected 4 or 5" % len(t))
        h = t[0].data
        if len(h) != ENTRY_ROW:
            raise ValueError("header is %d bytes" % len(h))
        self.header = h
        self.counts = {"last_rank": h[2], "list": h[3], "now_rank": h[4], "plteamid": h[5]}
        # makeTeamEntryIDList: t1 LAST_RANK, t2 LIST, t3 NOW_RANK, t4 PLTEAMID.
        self.records = {}
        for kind, tab in zip(self.KINDS, t[1:]):
            d = tab.data
            if len(d) % ENTRY_ROW:
                raise ValueError("%s table is not a whole number of records" % kind)
            self.records[kind] = [d[i:i + ENTRY_ROW] for i in range(0, len(d), ENTRY_ROW)]
        self.records.setdefault("plteamid", [])

    @property
    def slots(self):
        return sum(self.counts.values())

    def used(self, kind):
        """Records the game walks: the header count for all but NOW_RANK,
        which runs over its whole table (and only if the count is non-zero)."""
        recs = self.records[kind]
        if kind == "now_rank":
            return recs if self.counts[kind] else []
        return recs[:self.counts[kind]]

    def problems(self, list_kinds):
        out = []
        for kind in ("last_rank", "list", "plteamid"):
            if self.counts[kind] > len(self.records[kind]):
                out.append("%s count %d > %d records" % (kind, self.counts[kind],
                                                         len(self.records[kind])))
        # NOW_RANK records naming a UID that isn't loaded are skipped
        # (0x20a69c), so several may target one slot; the others may not.
        taken = Counter()
        for kind in self.KINDS:
            for r in self.used(kind):
                if kind != "now_rank":
                    taken[r[0]] += 1
                if r[0] >= self.slots:
                    out.append("%s slot %d >= %d" % (kind, r[0], self.slots))
                if kind == "last_rank" and not 1 <= r[1] <= 32:
                    out.append("last_rank rank %d" % r[1])
                if kind == "list":
                    k = s16(r, 4)
                    if k >= list_kinds:
                        out.append("list kind %d" % k)
        dup = sorted(s for s, n in taken.items() if n > 1)
        if dup:
            out.append("slots filled twice: %s" % " ".join(map(str, dup)))
        return out


def describe(kind, r):
    if kind == "last_rank":
        return "rank %d of compe %d last season" % (r[1], s16(r, 4))
    if kind == "now_rank":
        return "rank %d of UID %d%s" % (r[1], s16(r, 4), "" if r[3] else " (keeps UID)")
    if kind == "list":
        k = s16(r, 4)
        if k in LIST_SPECIAL:
            return LIST_SPECIAL[k]
        if k < 0:
            return "left empty (kind %d)" % k
        return "random pick from ranks %d-%d of make_list %d" % (r[1], r[2], k)
    t = u16(r, 4)
    return "team %d" % t if 1 <= t <= MAX_TEAM else "left empty (team %d)" % t


# --- loading -----------------------------------------------------------------

def read_pack(path):
    h = pac.load_header(path)
    if not isinstance(h, pac.BinPac):
        raise ValueError("not a BINPAC")
    with open(pac.data_path(path, h), "rb") as f:
        out = []
        for off, size, name, _ in h.entries:
            f.seek(off)
            out.append((name, f.read(size)))
    return out


def find(root, name):
    p = os.path.join(root, name)
    if not os.path.exists(p):
        raise SystemExit("%s: not found" % p)
    return p


# --- commands ----------------------------------------------------------------

def cmd_info(root):
    sysp = find(root, SYSTEM_PAC)
    try:
        system = System(read_pack(sysp))
    except (ValueError, struct.error) as e:
        print("%-45s !! %s" % (sysp, e))
        return
    uids = year_uids(system.year)
    probs = []
    if sorted(uids) != list(range(UID_COUNT)):
        probs.append("UIDs are not 0-%d" % (UID_COUNT - 1))
    for r in system.year:
        if r.uid >= 0 and r.kind not in LOAD_KIND:
            probs.append("UID %d load kind %d" % (r.uid, r.kind))
        if r.uid >= 0 and not 0 <= r.compe < len(system.open_nation):
            probs.append("UID %d compe %d" % (r.uid, r.compe))
        if r.turns and r.start > r.turns[0]:
            probs.append("UID %d start %d after first turn %d" % (r.uid, r.start, r.turns[0]))
    if len(system.savectrl) != UID_COUNT:
        probs.append("savectrl has %d bytes" % len(system.savectrl))
    for i, row in enumerate(system.open_nation):
        if row[0] != i:
            probs.append("open_nation row %d is compe %d" % (i, row[0]))
    bad_src = [i for i, r in enumerate(system.make_list) if r[2] not in SRC_KIND]
    if bad_src:
        probs.append("make_list source kind out of range in rows %s" % bad_src)
    kinds = Counter(LOAD_KIND.get(r.kind, r.kind) for r in system.year if r.uid >= 0)
    print("%-45s year rows=%d uids=%d (+%d second-year) open_nation=%d make_list=%d" % (
        sysp, len(system.year), len(uids), sum(1 for r in system.year if r.uid < 0),
        len(system.open_nation), len(system.make_list)))
    print("    load kinds: %s" % ", ".join("%s %d" % kv for kv in sorted(kinds.items())))
    for p in probs:
        print("  !! %s" % p)

    compp = find(root, COMPE_PAC)
    entp = find(root, ENTRY_PAC)
    comps, entries = {}, {}
    for path, cls, store in ((compp, Competition, comps), (entp, TeamEntry, entries)):
        try:
            pack = read_pack(path)
        except (ValueError, struct.error) as e:
            print("%-45s !! %s" % (path, e))
            continue
        if len(pack) != UID_COUNT:
            print("%-45s !! %d entries, expected %d" % (path, len(pack), UID_COUNT))
        for uid, (_, buf) in enumerate(pack):
            try:
                store[uid] = cls(buf)
            except (ValueError, struct.error) as e:
                store[uid] = e
    types = Counter()
    for uid in sorted(comps):
        c = comps[uid]
        if isinstance(c, Exception):
            print("  compe %3d  !! %s" % (uid, c))
            continue
        types[COMPE_TYPE.get(c.type, c.type)] += 1
        p = c.problems()
        row, nxt = uids.get(uid, (None, None))
        if row is not None:
            nturns = len(row.turns) + (len(nxt.turns) if nxt else 0)
            if c.days != nturns:
                p.append("%d game days, UID has %d turns" % (c.days, nturns))
        # Runtime-selected UIDs take their teams from the event system
        # (CScheEuro::TeamEntryLoadCompCB 0x206af0), not from the team entry.
        e = entries.get(uid)
        runtime = row is not None and row.kind == 3
        if isinstance(e, TeamEntry) and e.slots != c.entrants and not runtime:
            p.append("%d entrants, team entry fills %d slots" % (c.entrants, e.slots))
        if p:
            print("  compe %3d  !! %s" % (uid, "; ".join(p)))
    print("%-45s %d competitions: %s" % (compp, len(comps), ", ".join(
        "%s %d" % kv for kv in sorted(types.items()))))
    used = Counter()
    for uid in sorted(entries):
        e = entries[uid]
        if isinstance(e, Exception):
            print("  entry %3d  !! %s" % (uid, e))
            continue
        for k in TeamEntry.KINDS:
            used[k] += len(e.used(k))
        p = e.problems(len(system.make_list))
        if p:
            print("  entry %3d  !! %s" % (uid, "; ".join(p)))
    print("%-45s %d team entries: %s" % (entp, len(entries), ", ".join(
        "%s %d" % (k, used[k]) for k in TeamEntry.KINDS)))


def cmd_year(root):
    system = System(read_pack(find(root, SYSTEM_PAC)))
    print("  uid start end compe cycle kind            flag turns")
    for r in system.year:
        t = r.turns
        span = "%d (%d-%d)" % (len(t), t[0], t[-1]) if t else "0"
        print("%5d %5s %3s %5d %5s %-15s %4d %s" % (
            r.uid, r.start, "-" if r.end == 0xff else r.end, r.compe,
            "-" if r.cycle == 0xff else r.cycle, LOAD_KIND.get(r.kind, r.kind),
            r.flag, span))


def cmd_compe(root, uid):
    c = Competition(read_pack(find(root, COMPE_PAC))[uid][1])
    print("UID %d: %s, %d entrants, %d pairings, %d games over %d days" % (
        uid, COMPE_TYPE.get(c.type, c.type), c.entrants, c.pair_count, c.game_count, c.days))
    print("header %s" % c.header.hex(" "))
    for i, g in enumerate(c.games):
        a, b = c.pairs[g.pair]
        home, away = (b, a) if g.swap else (a, b)
        print("  game %3d  day %3d  pairing %3d  slot %3d v %3d  round %d  flag %d" % (
            i, g.day, g.pair, home, away, g.round, g.flag))
    if c.next is not None:
        for i, (n, s) in enumerate(c.next):
            print("  pairing %3d winner -> pairing %3d side %d" % (i, n, s))


def cmd_entry(root, uid):
    e = TeamEntry(read_pack(find(root, ENTRY_PAC))[uid][1])
    print("UID %d: %d slots (%s), header %s" % (uid, e.slots, ", ".join(
        "%s %d" % (k, e.counts[k]) for k in TeamEntry.KINDS), e.header.hex(" ")))
    for kind in TeamEntry.KINDS:
        for r in e.used(kind):
            shuffle = " shuffled" if kind != "list" and r[2] else ""
            print("  slot %3d  %-9s %s%s" % (r[0], kind, describe(kind, r), shuffle))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "year" and len(args) == 1:
        cmd_year(args[0])
    elif cmd == "compe" and len(args) == 2:
        cmd_compe(args[0], int(args[1], 0))
    elif cmd == "entry" and len(args) == 2:
        cmd_entry(args[0], int(args[1], 0))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
