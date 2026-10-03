# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
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
    python schedule.py roundtrip <DAT/PARAM>        # re-encode all three packs and their .HED, !! if not identical
    python schedule.py league <DAT/PARAM> [<n> [single]]  # generated leagues: check every size, or print one
    python schedule.py turns <DAT/PARAM> [<uid> [<days>]]  # leagues' game days and room; one UID's calendar

`league` builds round robins for 2-32 clubs (league_days, set_league):
each club alternates home and away, the second leg starts one round
later than the first so rematches are far apart, and an odd size gets a
rest day. With no size it checks every size, once and twice round, and
compares each with the disc's own template of that size (`!!` on a
generated league that breaks a rule). Building a league of a new size
into the packs also needs its turn mask and team-entry slots changed.

`turns` lists each league UID's game days and how many it could have:
the free turns inside its season, where no game of its own, of its
nation's cups or of a European, national-team or runtime competition
falls (the disc's leagues keep clear of those). With a UID it draws that
season as a calendar, and with a number of days the turns
league_turns() would use: added ones fill the widest gaps, weekends
first, and dropped ones are midweeks first.

Writing: every entry re-encodes from its fields (year rows, competition
headers, games, pairings, team-entry records), and a pack is rebuilt with
pac.py's BINPAC writer together with its .HED, which the game reads the
offsets from (its copies are in PRELOAD/STATIONFILE.PAC).
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

    def encode(self):
        """The 20-byte row from its fields; the mask from the turn list."""
        mask = bytearray(12)
        for t in self.turns:
            if not 0 <= t < TURNS_PER_YEAR:
                raise ValueError("turn %d out of range 0-%d" % (t, TURNS_PER_YEAR - 1))
            mask[t >> 3] |= 1 << (t & 7)
        return (struct.pack("<hBBbBBB", self.uid, self.start, self.end, self.compe,
                            self.cycle, self.kind, self.flag) + bytes(mask))


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
        self.entries = entries
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

    def encode(self):
        """[(name, bytes)] of the 5 entries; year_schedule_data rebuilt from
        its rows, the others as they are (no writer touches them yet)."""
        out = []
        for i, (name, buf) in enumerate(self.entries):
            if i == 0:
                end, t = tbb.parse(buf)
                trailer = tbb.trailer(buf, t)
                t[0].data = b"".join(r.encode() for r in self.year)
                buf = tbb.build(t, end, trailer)
            out.append((name, buf))
        return out


# --- SCHEDULE_COMPETITION ----------------------------------------------------

class Game:
    def __init__(self, w0, w1):
        self.day = w0 & 0xff
        self.flag = (w0 >> 8) & 3       # unknown
        self.round = (w0 >> 10) & 0xf   # 1 final, 2 semi, 3 quarter, 4 last 16, 0 other
        self.pair = w1 & 0x1ff
        self.swap = (w1 >> 9) & 3       # home = pair[swap], away = pair[1 - swap]
        self.spare = (w0 >> 14, w1 >> 11)

    def encode(self):
        if not (0 <= self.day < 0x100 and 0 <= self.round < 0x10 and 0 <= self.pair < 0x200
                and 0 <= self.flag < 4 and 0 <= self.swap < 4):
            raise ValueError("game field out of range (day %d, round %d, pairing %d)"
                             % (self.day, self.round, self.pair))
        w0 = self.day | self.flag << 8 | self.round << 10 | self.spare[0] << 14
        w1 = self.pair | self.swap << 9 | self.spare[1] << 11
        return struct.pack("<HH", w0, w1)


class Competition:
    def __init__(self, buf):
        self.buf = buf
        self.end, t = tbb.parse(buf)
        self.tbb_tables = t
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
        # Bytes past the last whole record, kept as they are.
        self.tails = [g[len(self.games) * GAME_ROW:], p[len(self.pairs) * PAIR_ROW:],
                      t[3].data[len(self.next) * PAIR_ROW:] if self.next is not None else b""]

    def encode(self):
        """The entry's bytes from the header fields, games, pairings and
        next links, with tbb.build. The header's counts are written from
        the fields: entrants, pairings and games."""
        t = self.tbb_tables
        trailer = tbb.trailer(self.buf, t)
        head = bytearray(self.header)
        head[4], head[5] = self.type, self.entrants
        struct.pack_into("<HH", head, 6, self.pair_count, self.game_count)
        t[0].data = bytes(head)
        t[1].data = b"".join(g.encode() for g in self.games) + self.tails[0]
        t[2].data = b"".join(bytes(pr) for pr in self.pairs) + self.tails[1]
        if self.next is not None:
            t[3].data = b"".join(bytes(nx) for nx in self.next) + self.tails[2]
        return tbb.build(t, self.end, trailer)

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


# --- building a league -------------------------------------------------------

LEAGUE_MAX = 32             # pairing index is 9 bits: n(n-1)/2 <= 511


def league_days(n, legs=2):
    """A round robin for entrant slots 0..n-1, as a list of game days, each
    a list of (home, away). Berger tables: each club alternates home and
    away, so no club plays more than two games in a row at one venue. The
    second leg plays the first leg's rounds again with home and away
    swapped, starting from round 1 (round 0's return games come last), so
    a rematch is n-2 or more game days after the first meeting. An odd n
    gets a rest day: slot n is a dummy, and its games are left out."""
    if not 2 <= n <= LEAGUE_MAX or legs not in (1, 2):
        raise ValueError("a league has 2-%d clubs playing 1 or 2 legs" % LEAGUE_MAX)
    size = n + n % 2
    m = size - 1
    first = []
    for r in range(m):
        day = [(r, m) if r % 2 == 0 else (m, r)]
        for i in range(1, size // 2):
            a, b = (r + i) % m, (r - i) % m
            day.append((a, b) if i % 2 else (b, a))
        first.append([g for g in day if n not in g])
    if legs == 1:
        return first
    return first + [[(a, h) for h, a in day] for day in first[1:] + first[:1]]


def league_tables(n, legs=2):
    """(pairings, games) for league_days(n, legs) in the layout of
    SCHEDULE_COMPETITION tables 1 and 2: pairings in the order they are
    first played, each as (home, away) of its first game, and games in day
    order, swap 1 for a return game."""
    pairs, index, games = [], {}, []
    for day, fixtures in enumerate(league_days(n, legs)):
        for h, a in fixtures:
            key = frozenset((h, a))
            if key not in index:
                index[key] = len(pairs)
                pairs.append((h, a))
            k = index[key]
            games.append(Game(day, k | (0 if pairs[k][0] == h else 1) << 9))
    return pairs, games


def set_league(c, n, legs=2):
    """Make Competition `c` a league of n entrants with league_tables'
    pairings and games. The other header bytes are kept. Returns the
    number of game days, which the UID's turn mask must match."""
    if c.next is not None:
        raise ValueError("UID is a knockout (4 tables); only a league can be rebuilt")
    c.pairs, c.games = league_tables(n, legs)
    c.type, c.entrants = 0, n
    c.pair_count, c.game_count = len(c.pairs), len(c.games)
    return c.days


def league_stats(c):
    """(problems, breaks, longest run at one venue, shortest gap in game
    days between two meetings of the same clubs) of a league Competition."""
    probs = []
    venue = {t: {} for t in range(c.entrants)}
    meetings = {}
    for g in c.games:
        if g.pair >= len(c.pairs):
            probs.append("game on day %d names pairing %d of %d" % (g.day, g.pair, len(c.pairs)))
            continue
        pair = c.pairs[g.pair]
        h, a = pair[g.swap], pair[1 - g.swap]
        for t, v in ((h, "H"), (a, "A")):
            if t not in venue:
                probs.append("slot %d out of range" % t)
            elif g.day in venue[t]:
                probs.append("slot %d plays twice on day %d" % (t, g.day))
            else:
                venue[t][g.day] = v
        meetings.setdefault(g.pair, []).append((g.day, h))
    legs = {len(m) for m in meetings.values()}
    if len(meetings) != len(c.pairs) or len(legs) != 1:
        probs.append("pairings are played %s times" % sorted(legs))
    elif legs == {2} and any(m[0][1] == m[1][1] for m in meetings.values()):
        probs.append("a pairing has both games at the same club")
    if {frozenset(p) for p in c.pairs} != {frozenset((i, j)) for i in range(c.entrants)
                                           for j in range(i + 1, c.entrants)}:
        probs.append("pairings are not every two slots once")
    breaks = longest = 0
    for days in venue.values():
        seq = [days[d] for d in sorted(days)]
        run = 1
        for i in range(1, len(seq)):
            run = run + 1 if seq[i] == seq[i - 1] else 1
            breaks += seq[i] == seq[i - 1]
            longest = max(longest, run)
    gap = min((m[1][0] - m[0][0] for m in meetings.values() if len(m) > 1), default=0)
    return probs, breaks, longest, gap


# --- game days for a league --------------------------------------------------

MONTHS = ("Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun")
TURNS_PER_MONTH = 8         # 4 weeks of a midweek and a weekend turn (empirical)


def turn_name(t):
    """A turn as the game's calendar shows it: "Aug w2 weekend" (empirical:
    the year starts in July, 8 turns a month, even turns midweek)."""
    m, k = divmod(t % TURNS_PER_YEAR, TURNS_PER_MONTH)
    return "%s w%d %s" % (MONTHS[m], k // 2 + 1, "midweek" if k % 2 == 0 else "weekend")


def compe_nation(system, compe):
    """The one nation a competition always belongs to (open_nation rows
    that repeat a nation, with no 4-year start), or None for one whose
    host changes (the European and national-team competitions)."""
    row = next((r for r in system.open_nation if r[0] == compe), None)
    if row is None or row[1] != -1 or len(set(row[2:])) != 1:
        return None
    return row[2]


def year_turns(system):
    """{uid: (row, [turns])}, a second-year row's turns counted from 96."""
    out, last = {}, None
    for r in system.year:
        if r.uid >= 0:
            out[r.uid] = (r, list(r.turns))
            last = r.uid
        elif last is not None:
            out[last][1].extend(t + TURNS_PER_YEAR for t in r.turns)
    return out


def blocked_turns(system, compes, uid):
    """Turns a league UID's clubs may be busy on, as the disc's leagues
    keep clear of them (empirical): games of any competition whose host
    changes (European, national teams, the runtime cups) and of the
    league's own nation's knockouts. VS and first-promotion UIDs, the
    runtime friendlies and other leagues don't count."""
    rows = year_turns(system)
    nation = compe_nation(system, rows[uid][0].compe)
    out = set()
    for u, (r, turns) in rows.items():
        if u == uid or r.kind in (4, 5) or u >= len(compes):
            continue
        n = compe_nation(system, r.compe)
        if n == 0:
            continue            # the runtime friendlies (competition 49)
        if n is None or (n == nation and compes[u].type == 1):
            out.update(turns)
    return out


def free_turns(system, compes, uid):
    """The turns inside a league UID's season (its first to last game day)
    with no game of its own and none it keeps clear of."""
    turns = year_turns(system)[uid][1]
    busy = blocked_turns(system, compes, uid) | set(turns)
    return [t for t in range(turns[0], turns[-1] + 1) if t not in busy]


def league_turns(system, compes, uid, days):
    """A turn list of `days` game days for a league UID, made from its own
    by adding free turns inside its season or dropping turns. Each added
    turn goes into the widest gap between game days (a weekend before a
    midweek), each dropped one closes the narrowest (a midweek first), so
    the games stay spread over the season."""
    row, turns = year_turns(system)[uid]
    if len(turns) != len(set(turns)) or any(t >= TURNS_PER_YEAR for t in turns):
        raise ValueError("UID %d runs across the year end; not supported" % uid)
    turns = sorted(turns)
    free = free_turns(system, compes, uid)
    if days - len(turns) > len(free):
        raise ValueError("UID %d has room for %d game days (%d now, %d free turns)"
                         % (uid, len(turns) + len(free), len(turns), len(free)))
    if days < 1:
        raise ValueError("a league needs at least 1 game day")
    while len(turns) < days:
        def room(t):
            before = max((x for x in turns if x < t), default=turns[0])
            after = min((x for x in turns if x > t), default=turns[-1])
            return (min(t - before, after - t), t % 2, -t)
        t = max(free, key=room)
        free.remove(t)
        turns = sorted(turns + [t])
    while len(turns) > days:
        def loss(i):
            t = turns[i]
            # The first and last game days stay, so the season keeps its dates.
            before = turns[i - 1] if i else t - TURNS_PER_YEAR
            after = turns[i + 1] if i + 1 < len(turns) else t + TURNS_PER_YEAR
            return (t % 2, after - before, t)
        turns.pop(min(range(len(turns)), key=loss))
    return turns


# --- SCHEDULE_TEAM_ENTRY -----------------------------------------------------

class TeamEntry:
    KINDS = ("last_rank", "list", "now_rank", "plteamid")

    def __init__(self, buf):
        self.buf = buf
        self.end, t = tbb.parse(buf)
        self.tbb_tables = t
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

    def encode(self):
        """The entry's bytes: the header with the four counts, then each
        kind's records."""
        t = self.tbb_tables
        trailer = tbb.trailer(self.buf, t)
        head = bytearray(self.header)
        head[2:6] = bytes(self.counts[k] for k in self.KINDS)
        t[0].data = bytes(head)
        for kind, tab in zip(self.KINDS, t[1:]):
            tab.data = b"".join(self.records[kind])
        return tbb.build(t, self.end, trailer)

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


def build_pack(path, blobs):
    """(new .PAC bytes, new .HED bytes) for a schedule pack holding `blobs`.
    The game reads offsets from the .HED (a copy of the header, padded to
    its size; the copies in PRELOAD/STATIONFILE.PAC are what it loads) and
    the entries from the .PAC, so both must be written together."""
    with open(path, "rb") as f:
        data = f.read()
    h = pac.BinPac(data[:struct.unpack_from("<I", data)[0]])
    out = pac.build_binpac(data[:h.header_size], blobs)
    hed_path = path[:-4] + ".HED"
    hed_size = os.path.getsize(hed_path)
    head = out[:h.header_size]
    if len(head) > hed_size:
        raise ValueError("%s: the header no longer fits its .HED" % path)
    return out, head + bytes(hed_size - len(head))


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


def cmd_roundtrip(root):
    """Re-encode every entry of the three packs from its fields, rebuild
    each pack and its .HED, and compare with the files; !! on a difference."""
    for name, make in ((SYSTEM_PAC, None), (COMPE_PAC, Competition), (ENTRY_PAC, TeamEntry)):
        path = find(root, name)
        try:
            entries = read_pack(path)
            if make is None:
                blobs = [b for _, b in System(entries).encode()]
            else:
                blobs = [make(b).encode() for _, b in entries]
            bad = [i for i, ((_, old), new) in enumerate(zip(entries, blobs)) if old != new]
            pac_bytes, hed_bytes = build_pack(path, blobs)
            with open(path, "rb") as f:
                same_pac = f.read() == pac_bytes
            with open(path[:-4] + ".HED", "rb") as f:
                same_hed = f.read() == hed_bytes
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (path, e))
            continue
        probs = (["entries differ: %s" % " ".join(map(str, bad[:10]))] if bad else []) + \
                ([] if same_pac else ["rebuilt .PAC differs"]) + \
                ([] if same_hed else ["rebuilt .HED differs"])
        print("%s  %d entries re-encoded, %d differ; .PAC %s, .HED %s%s" % (
            path, len(entries), len(bad), "identical" if same_pac else "differs",
            "identical" if same_hed else "differs", "  !! " + "; ".join(probs) if probs else ""))


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


def cmd_league(root, n=None, legs=2):
    """Check the generated league for every size, beside the disc's own
    template of that size; or print one generated league day by day."""
    if n is not None:
        days = league_days(n, legs)
        print("%d clubs, %d leg%s: %d game days" % (n, legs, "s" * (legs - 1), len(days)))
        for d, fixtures in enumerate(days):
            print("  day %3d  %s" % (d, "  ".join("%d-%d" % f for f in fixtures)))
        return
    disc = {}
    for uid, (_, buf) in enumerate(read_pack(find(root, COMPE_PAC))):
        c = Competition(buf)
        if c.type == 0:
            disc.setdefault((c.entrants, len(c.games) // len(c.pairs)), (uid, c))
    for legs in (1, 2):
        for n in range(2, LEAGUE_MAX + 1):
            c = Competition.__new__(Competition)
            c.next, c.header, c.tails = None, bytes(COMPE_HEADER), [b"", b"", b""]
            days = set_league(c, n, legs)
            probs, breaks, longest, gap = league_stats(c)
            line = "%2d clubs %d leg%s: %3d days %3d games  breaks %3d  longest %d  gap %2d" % (
                n, legs, "s" if legs == 2 else " ", days, len(c.games), breaks, longest, gap)
            if (n, legs) in disc:
                uid, d = disc[n, legs]
                _, db, dl, dg = league_stats(d)
                line += "  (disc UID %d: %d days, breaks %d, longest %d, gap %d)" % (
                    uid, d.days, db, dl, dg)
            print(line + ("  !! " + "; ".join(probs) if probs else ""))


def calendar(marks):
    """A month-by-week grid of one-letter marks per turn."""
    lines = ["       " + " ".join("w%d%s" % (k // 2 + 1, "m" if k % 2 == 0 else "e")
                                   for k in range(TURNS_PER_MONTH))]
    for m in range(12):
        lines.append("  %s  " % MONTHS[m] + " ".join(
            "%-3s" % marks.get(m * TURNS_PER_MONTH + k, ".") for k in range(TURNS_PER_MONTH)))
    return lines


def cmd_turns(root, uid=None, days=None):
    """Each league UID's game days and room for more; or one UID's season
    as a calendar, with the turns a new number of game days would use."""
    system = System(read_pack(find(root, SYSTEM_PAC)))
    compes = [Competition(b) for _, b in read_pack(find(root, COMPE_PAC))]
    rows = year_turns(system)
    if uid is None:
        for u, c in enumerate(compes):
            if c.type != 0 or u not in rows or rows[u][0].kind in (4, 5) or                     compe_nation(system, rows[u][0].compe) is None:
                continue            # only the domestic leagues
            r, turns = rows[u]
            legs = len(c.games) // max(1, len(c.pairs))
            if len(turns) != c.days:
                print("UID %3d  %2d clubs: %d game days, %d turns  !! game days and turns "
                      "differ" % (u, c.entrants, c.days, len(turns)))
                continue
            try:
                free = free_turns(system, compes, u)
            except (ValueError, IndexError) as e:
                print("UID %3d  !! %s" % (u, e))
                continue
            most = len(turns) + len(free)
            clubs = max(n for n in range(2, LEAGUE_MAX + 1)
                        if len(league_days(n, legs)) <= most)
            print("UID %3d  competition %2d  %2d clubs, %d leg%s: %2d game days, turns %d-%d, "
                  "%2d free: room for %2d days, %2d clubs" % (
                      u, r.compe, c.entrants, legs, "s" if legs == 2 else " ", len(turns),
                      turns[0], turns[-1], len(free), most, clubs))
        return
    turns = rows[uid][1]
    blocked = blocked_turns(system, compes, uid)
    marks = {t: "x" for t in blocked}
    marks.update({t: "L" for t in turns})
    for t in free_turns(system, compes, uid):
        marks[t] = "."
    title = "UID %d: %d game days" % (uid, len(turns))
    if days is not None:
        try:
            new = league_turns(system, compes, uid, days)
        except ValueError as e:
            raise SystemExit(str(e))
        marks.update({t: "+" for t in set(new) - set(turns)})
        marks.update({t: "-" for t in set(turns) - set(new)})
        title += " -> %d" % days
    print(title + "  (L game day, x another competition, . free, + added, - dropped)")
    for line in calendar(marks):
        print(line)
    if days is not None:
        print("added:   " + ", ".join(turn_name(t) for t in sorted(set(new) - set(turns))))
        print("dropped: " + ", ".join(turn_name(t) for t in sorted(set(turns) - set(new))))


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
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    elif cmd == "turns" and len(args) == 1:
        cmd_turns(args[0])
    elif cmd == "turns" and len(args) in (2, 3):
        cmd_turns(args[0], int(args[1], 0), int(args[2]) if len(args) == 3 else None)
    elif cmd == "league" and len(args) == 1:
        cmd_league(args[0])
    elif cmd == "league" and len(args) in (2, 3) and args[1].isdigit() \
            and (len(args) == 2 or args[2] == "single"):
        cmd_league(args[0], int(args[1]), 1 if len(args) == 3 else 2)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
