<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Season schedule: `SCHEDULE_SYSTEM`, `SCHEDULE_COMPETITION`, `SCHEDULE_TEAM_ENTRY`

The career calendar is built from three BINPAC packs in `DAT/PARAM`
([`PARAM_DIR.md`](PARAM_DIR.md)). All their entries are `TBB1` files
([`TBB_FORMAT.md`](TBB_FORMAT.md)):

| Pack | Entries | Holds |
|---|---|---|
| `SCHEDULE_SYSTEM.PAC/.HED` | 5 named TBBs | the year plan: which schedules exist, when their games fall, host nations, team lists |
| `SCHEDULE_COMPETITION.PAC/.HED` | 164 | one schedule per UID: its games and pairings |
| `SCHEDULE_TEAM_ENTRY.PAC/.HED` | 164 | one per UID: where each entrant's team comes from |

A **schedule UID** (0–163) is one run of games: a league division, a cup
round, a group of a group stage. The game calls it `PLSCHE_GROUP`. Several
UIDs belong to one **competition** (`PLSCHE_COMPE`, 0–71). For example, UIDs 1
and 2 are both competition 1: one is used when it is the player's own
league, the other when it isn't. Entry *n* of both 164-entry packs belongs to UID
*n*, and `REGULATION.TBB` is indexed by the same number.

The layouts below are **confirmed** from the game code unless marked
**empirical**. `python SRC/schedule.py info DAT/PARAM` checks all of it
against the disc and reports one problem (UID 117, below).

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x209b50` | `ScheEuro_SubCtrl::requestLoad` | loads `schedule_system.pac` |
| `0x209bf0` | `ScheEuro_SubCtrl::isCompleteLoad` | loads its 5 entries, then runs the four `init*Data` below |
| `0x20a008` | `ScheEuro_SubCtrl::initYearScheduleData` | 20-byte rows. A row with UID −1 continues the row before it |
| `0x20a170` | `ScheEuro_SubCtrl::getYearSchedule(uid, second)` | finds a row by UID. `second` returns the −1 row after it |
| `0x20a130` | `getScheCompe_FromTBB` | `+4` is the competition |
| `0x20a230` | `isGameOpen_FromTBB(uid, turn)` | bit `turn` of the mask at `+8` |
| `0x209968` | `YEAR_SCHEDULE::get_open_turn` | first set bit of the 12-byte mask, plus 96 per year of delay from `+5` |
| `0x209f40` | `getOpenNation(compe, years)` | 44-byte `open_nation` rows |
| `0x205728` | `CScheEuro::getNationFromScheCompe` | passes `pwkGen_Keika()` (years played) as `years` |
| `0x2072a8`, `0x207458`, `0x2075c8` | `CScheEuro_{Normal,FirstPromote,VS}::acceptLoadRequest` | the load condition in `+6` |
| `0x2068f8` | `CScheEuro::OneLoadCompCB` | a `SCHEDULE_COMPETITION` entry and the UID's masks go to `decodeBlockData`/`decodeGameTurn`. `savectrl[uid]` picks the save buffer |
| `0x2dc258` | `Sche_Block_decode_main2` | the competition entry layout |
| `0x2dc650` | `scheCtrl_InitGameDay` | game day *k* is the *k*-th set bit of the turn mask |
| `0x2dab38` | `getOneGameFromBlockAndGameIndex` | home = `pair[swap]`, away = `pair[1 − swap]` |
| `0x20a298` | `ScheEuro_TeamEntry::makeTeamEntryIDList` | the team-entry layout and its four record kinds |
| `0x20a4b8`, `0x20a5e0`, `0x20a828`, `0x20a770` | `LastRank_`, `NowRank_`, `List_`, `PlTeamId_TeamEntryProc` | what each record kind reads |
| `0x20ad10` | `ScheEuro_TeamEntryList::initMakeList` | the 9 `make_list` tables |
| `0x20b188` | `ScheEuro_TeamEntryList::requestMakeList` | `make_list` table 0 rows. The jump table at `0x52fb10` picks the source |
| `0x21dc60` | `Param::plRec_MatchRegulations(group)` | `REGULATION.TBB` row = UID. VS UIDs 148–163 can be overridden at runtime |

## Turns

A year has **96 turns**. `get_open_turn` returns `years × 0x60 + bit`, and
the masks are 12 bytes (96 bits). A schedule's games fall on the turns whose
bits are set in its mask, in order. Game day 0 is on the first set bit, and
so on.

**Empirical:** the year starts in July and has 8 turns a month: 4 weeks
of a midweek turn and a weekend turn, so turn 0 is July week 1 midweek
and turn 11 is August week 2 weekend. The career screen shows the same
steps ("Week 1 Mid-Week Jul.", "Week 1 Weekend Jul."), and the English
first division's 38 game days run from turn 11 to turn 85 (May week 3
weekend), almost every weekend in between. The cups, the European
competitions and the national-team dates fall on midweeks, and the
national teams have all of June.

## `SCHEDULE_SYSTEM.PAC`

| Entry | Name | Tables | Contents |
|---|---|---|---|
| 0 | `year_schedule_data.tbb` | 1 | 184 × 20 bytes: one row per UID plus 20 second-year rows |
| 1 | `open_nation.tbb` | 1 | 72 × 44 bytes: host nation of each competition |
| 2 | `make_list.tbb` | 9 | team-list definitions |
| 3 | `PeriodName.tbb` | 2 | round names (`initPeriodNameData` `0x209d90`). Not decoded |
| 4 | `savectrl.tbb` | 1 | 164 × u8, one save-buffer type per UID (values 0, 1, 2) |

### `year_schedule_data` row (20 bytes)

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | s16 | UID. **−1**: the second-year part of the row above it (20 rows). Such a schedule runs across the year end (`isOverYear` `0x20a0c0`) |
| `0x02` | u8 | start turn, at or before the first set bit (**empirical**). In a −1 row it is copied into the row above if that row's is `0xff` |
| `0x03` | u8 | end turn, `0xff` = none. A −1 row's value plus `0x60` is written into the row above |
| `0x04` | s8 | competition (`PLSCHE_COMPE`), 0–71 |
| `0x05` | u8 | year of the 4-year cycle when it starts (1–4), `0xff` = every year |
| `0x06` | u8 | load condition, see below |
| `0x07` | u8 | flag, unknown |
| `0x08` | u8[12] | turn mask: bit *t* set = a game day on turn *t* |

The load condition in `+6` decides whether a UID is loaded in each mode:

| Value | Normal mode | Rows |
|---|---|---|
| 0 | always | 69 |
| 1 | only if the competition's nation is the player's | 24 |
| 2 | only if it isn't | 24 |
| 3 | only if selected at runtime (`pwkEvCom_GetRuntimeSelectCompe`) | 25 |
| 4 | first-promotion mode only, own nation | 6 |
| 5 | VS mode only, when selected | 16 |

Values 1 and 2 come in pairs for the same competition. The own-league
version usually has more game days (UID 1 has 50 and UID 2 has 46), which
gives the player's league more fixtures on screen.

### `open_nation` row (44 bytes)

`{s16 compe, s16 start, s16 nation[20]}`, one row per competition, in
order. With `start == −1` the host is `nation[years % 20]`. Otherwise it is
`nation[((years + 1 − start) / 4) % 20]`, so the host changes every 4
years (World Cup and European Championship style). Only competitions
44–47 have a `start` (1–4). 57 of the 72 rows repeat one nation 20 times.

### `make_list` (9 tables)

Table 0 has 71 rows of 4 bytes, one per list kind (`eLIST_KIND`). A list
is filled on first use:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u8 | number of teams in the list |
| `0x01` | u8 | parameter: nation or region. For the `list` source, `value − 0x67` picks one of tables 3–8 |
| `0x02` | s8 | source: 0/1 UEFA coefficient, 2/3 club rank, 4/5 FIFA ranking, 6 fixed list, 7 domestic (the player's nation) |
| `0x03` | u8 | option passed to the source function |

Table 1 is `MAKE_UEFA_LIST` (77 × 4 bytes, `initMakeUefaList`
`0x20ae48`), table 2 has 4 rows, and tables 3–8 are the fixed lists. The
source functions (`getList_SRC_KIND_*`, `0x20b4a8`–`0x20bb50`) aren't
decoded yet.

## `SCHEDULE_COMPETITION.PAC` entry

A TBB with 3 tables (league) or 4 (knockout).

### Table 0: header (16 bytes)

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u16 | the UID. Not read by the game. Entry 81 says 80 |
| `0x02` | u16 | a competition number. Not read by the game, and not the `year_schedule_data` one |
| `0x04` | u8 | type: 0 league, 1 knockout |
| `0x05` | u8 | entrants |
| `0x06` | u16 | pairings |
| `0x08` | u16 | games |
| `0x0A`–`0x0F` | u8 × 6 | copied to the block at `+0x1a`, `+0x16`, `+0x17`, `+0x19`, `+0x18`, `+0x1b`. Zero in leagues. Unknown |

**Empirical:** a league has `n(n−1)/2` pairings and plays each twice or
once. A knockout has `n − 1` pairings (fewer for a single round: UID 4 has
28 entrants and 14 ties).

### Table 1: games (4 bytes each)

| Bits | Meaning |
|---|---|
| `w0` 0–7 | game day. Days run 0 to *d* − 1 with no gaps |
| `w0` 8–9 | unknown (0 or 1) |
| `w0` 10–13 | round (**empirical**): 1 final, 2 semi-final, 3 quarter-final, 4 last 16, 0 anything else |
| `w1` 0–8 | pairing index |
| `w1` 9–10 | home/away swap: home is `pair[swap]` |

### Table 2: pairings (2 bytes each)

`{u8 slot_a, u8 slot_b}`. In a league both are entrant slots. In a knockout
the first round names entrant slots and later rounds name winner slots
after them (for example `3c 3d` in the 32-team UID 6 final).

### Table 3: next pairing (knockout only, 2 bytes each)

`{u8 pairing, u8 side}`: where the winner of each pairing goes. A value at
or past the pairing count means the winner leaves this competition (the
final, and single-round ties that feed another UID).

### Game days and the turn mask

Game day *k* is played on the *k*-th set bit of the UID's turn mask
(`scheCtrl_InitGameDay`), counting the second-year row's mask after the
first. So the number of game days must equal the number of set bits. That
holds for 163 of 164 UIDs. **UID 117** has 6 game days (12 games) but only
3 bits. Its header says competition 34 where its neighbours (UIDs 114–121)
say 47, so it looks like a group from competition 34 (UIDs 59–66, 6 game
days each) left in the wrong slot. What the game does with the extra days
isn't known.

## `SCHEDULE_TEAM_ENTRY.PAC` entry

A TBB with 4 or 5 tables of 6-byte records. Table 0 is the header:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u8[2] | unknown |
| `0x02` | u8 | `LAST_RANK` records used |
| `0x03` | u8 | `LIST` records used |
| `0x04` | u8 | `NOW_RANK` records (0 = skip the table) |
| `0x05` | u8 | `PLTEAMID` records |

The four counts add up to the number of entrant slots. For every UID
except the runtime-selected ones, that equals the competition's entrant
count. Tables 1–4 hold the records, one kind per table:

| Table | Kind | `+0` | `+1` | `+2` | `+3` | `+4` (s16) | Team |
|---|---|---|---|---|---|---|---|
| 1 | `LAST_RANK` | slot | rank | shuffle | – | competition | the team that finished `rank` in that competition last season (`pwkRec_GetCompePastRecord`) |
| 2 | `LIST` | slot | first rank | last rank | – | list kind | a random team from ranks `first`–`last` of that `make_list` |
| 3 | `NOW_RANK` | slot | rank | shuffle | keep | UID | the team currently at `rank` in that UID's table. Skipped if that UID isn't loaded |
| 4 | `PLTEAMID` | slot | – | shuffle | – | team id | that club (`1`–`0x22d`) |

- **shuffle:** a non-zero value puts the slot into a random reshuffle
  (`RandamSort`).
- **keep:** a zero `+3` in a `NOW_RANK` record stores the source UID with
  the slot.
- **Special `LIST` kinds:** −4 is the host nation's national team, −3 is
  team 1, and any other negative kind leaves the slot empty. The 18
  runtime friendlies (UIDs 124–141) use −2.
- **Out-of-range team ids:** `PLTEAMID` ids outside 1–557 leave the slot
  empty. UIDs 156, 157, 162 and 163 use 558.

Because a `NOW_RANK` record for an unloaded UID is skipped, the same slot
can be listed once per alternative. UID 3 fills its 4 slots from UID 1
*or* UID 2, whichever was loaded.

### What decides the first season's leagues

A league's slots are `LAST_RANK` records. UID 0 takes ranks 1–20 of
competition 0 from last season. At the start of a new game,
`PLRRSRC_INITTEAMDATA.TBB` table 1 seeds those past records
(`pwkRec_SetPastRecordLastTeam`, see
[`PARAM_DIR.md`](PARAM_DIR.md#plrrsrc_initteamdatatbb-starting-leagues)).
So that table decides which clubs start in which division, and this pack
decides how they are placed.

**England**, from the team-entry records of UIDs 0, 1 and 3 (`python
SRC/schedule.py entry DAT/PARAM 0`):

| UID | Takes |
|---|---|
| 0, first division (20) | ranks 1–17 of competition 0 (the first division), ranks 1–2 of competition 1 (the second division), rank 1 of competition 2 |
| 1, second division, own nation (26 slots) | ranks 18–20 of competition 0, ranks 2–4 of competition 2, ranks 7–26 of competition 1 |
| 3, competition 2 (4 entrants) | ranks 3, 6, 4 and 5 of the second division's current table (`NOW_RANK` of UID 1, or UID 2 when the second division isn't your league) |

UID 3 is a knockout of 5 games over 3 days: pairings 0 and 1 played home
and away (3rd v 6th, 4th v 5th), then their winners in one game. So
competition 2 is the **promotion playoffs**: the top two go up, 3rd to
6th play off for the third place, and the three losers stay down. The
second division keeps every other club; nothing is relegated from it, as
the game has no third tier (user report).

**Your club and the rival.** After the tutorial the game adds your club
and the rival to your nation's second division, which grows by 2 (user
report). That fits the slot counts: the own-nation UID 1 has 26 slots
and takes ranks 7–26 of competition 1, whose record holds 24 clubs, so
ranks 25 and 26 are the two new clubs; the other-nations UID 2 has 24.
How the game gives them those ranks isn't traced. The other leagues'
UIDs follow their own rules, not checked here.

## Writing

`python SRC/schedule.py roundtrip DAT/PARAM` re-encodes every entry of the
three packs from its fields (year rows and their turn masks, competition
headers, games, pairings and next links, team-entry headers and records)
and rebuilds each pack with `pac.py`'s BINPAC writer: all 333 entries and
the three packs come out byte for byte (in `regress.py`).

A rebuilt pack goes with a new `.HED`. Each `.HED` is the pack's header
padded with zeros to its own size (4,096 or 2,048 bytes), and the game
reads entry offsets from it: the copies it loads are
`PRELOAD/STATIONFILE.PAC` entries 1 and 2 (whole game), while
`SCHEDULE_COMPETITION.PAC` and `SCHEDULE_TEAM_ENTRY.PAC` are read from
their own files, and `SCHEDULE_SYSTEM.PAC` from `STATIONFILE.PAC` entry 0
(`python SRC/preload.py who DAT SCHEDULE_COMPETITION.HED`). So an entry
that changes size moves the entries after it, and the pack and its
`.HED` must be written together; `patch_disc.py --copies` then updates
the `STATIONFILE` copies.

## Building a league of another size

Changing a division's size needs a new league schedule for that many
clubs. `schedule.py` can now build one; putting it into the packs is the
next step (below).

**The disc's leagues (empirical, all 77 league UIDs):** there is one
fixed schedule per size. Every league of the same size and number of
legs has exactly the same games: all seven 20-club leagues (UIDs 0, 10,
12, 20, 28, 38, 49) are one template, so are the three 18-club ones and
so on. In every even-sized league each club plays once per game day,
and a double round robin uses 2(*n* − 1) days. The second half repeats
the first half's days in the same order with home and away swapped (day
19 of the 20-club league is day 0 reversed). Pairings are listed in the
order they are first played, each as (home, away) of its first game,
and return games have swap 1. The 5-club groups (UIDs 87–112) are
irregular: some clubs play twice on one day.

The templates differ a lot in how well home and away games alternate:

| Clubs, legs | UIDs | Longest run at one venue | Breaks (two in a row at one venue) |
|---|---|---|---|
| 20, 2 | 0, 10, 12, 20, 28, 38, 49 | 2 | 54 |
| 22, 2 | 11, 30, 40, 48 | 7 | 400 |
| 24, 2 | 2, 29, 39 | 2 | 168 |
| 26, 2 | 1 | 9 | 512 |

**The generator** (`league_days`, `league_tables`, `set_league`) uses
Berger tables (the circle method): club *n* − 1 stays put while the
others rotate, and every club alternates home and away. The second half
plays the first half's rounds again with home and away swapped,
starting from round 1, so round 0's return games come last. That keeps
the run at one venue to 2 at every size, gives 2*n* breaks in a double
round robin (40 for 20 clubs, against the disc's 54), and puts every
rematch at least *n* − 2 game days after the first meeting. A plain
same-order mirror gives runs of 3 where the halves meet, and a
reverse-order mirror gives back-to-back rematches. An odd number of
clubs gets a rest day: a dummy club joins the draw and its games are
left out. Sizes run from 2 to 32 clubs: the pairing index is 9 bits, so
*n*(*n* − 1)/2 must stay under 512.

`python SRC/schedule.py league DAT/PARAM` builds every size once and
twice round, checks each (every pair of clubs meets the right number of
times, home once each in a double round robin, no club twice on one
day) and prints it beside the disc's template of that size. `python
SRC/schedule.py league DAT/PARAM 22` prints one day by day. A rebuilt
entry encodes and re-reads with no problems; a 22-club UID 0 grows from
2,000 to 2,416 bytes, which moves the entries after it (see
[Writing](#writing)).

`python SRC/leaguesize.py build` puts it all together (below). Still
open:

- Memory: each loaded UID takes its games, entrants and table rows from
  shared save-buffer pools (`ScheEuro_Memory::init` `0x209210` sets
  sizes such as `0x16c0` and `0x1800`; `alloc_save_buffer` `0x2097e8`,
  type from `savectrl`). The big leagues are all type 0, which already
  holds the 26-club league (650 games), but whether the pools have room
  for more games in total isn't traced. The 22-club test below saved
  and reloaded without trouble, which doesn't rule out a limit for
  bigger changes.
- Promotion and relegation into the second season are tested for
  England at 22 clubs only (below). Other nations and sizes are checked
  by `build` but not in game.

### Where the clubs come from

**Empirical, all six nations** (`python SRC/leaguesize.py nations
DAT/PARAM`): a nation's two divisions follow one pattern.

| Division | Slots (`LAST_RANK` of last season, in this order) |
|---|---|
| First (UID 0 for England) | its own ranks 1–*k*, then the second division's promoted clubs and, where there are playoffs, the playoff winner |
| Second, other-nations (UID 2) | the first division's ranks after *k* that go down, the playoff losers, then its own ranks *m* + 1 to the end |
| Second, own-nation (UID 1) | the same plus 2 more ranks: your club and the rival |

*k* is 17 (15 in Germany and the Netherlands) and *m* is 6 in England
and Italy (ranks 1–2 promoted, 3–6 to the playoffs), 3 in France,
Germany and Spain (three promoted, no playoffs) and 7 in the
Netherlands, whose playoff groups (UIDs 50–51) take the first
division's 16th and 17th (`NOW_RANK`, the current table) and second
division ranks 2–7. The playoffs (UID 3 for England) take ranks 3–6 of
the second division's current table. The cups draw on the same ranks:
England's UIDs 4–7 name first-division, second-division and playoff
ranks by `LAST_RANK`.

The first season is built from the past records that
`PLRRSRC_INITTEAMDATA.TBB` table 1 seeds: England's record 0 (the first
division, 20 clubs), 1 (the second, 24) and 2 (the playoffs: the
winner, then the three losers, who are ranks 3–6 of record 1). Your
club and the rival fill the own-nation version's last two slots, ranks
past the seeded record. Played out from the disc's records with these
slots, every nation's first season puts each of its clubs in exactly
one division.

**Changing the size.** A nation's clubs are fixed, so the first
division grows by as many clubs as the second loses. `leaguesize.py`
moves clubs at the boundary in the seeded records: to grow the first
division by *d*, the second division's ranks *m* + 1 to *m* + *d* (its best
clubs outside the promotion and playoff places) move to the first
division's ranks *k* + 1 to *k* + *d*, above the relegation places; to
shrink it, its ranks *k* − *d* + 1 to *k* move to the second division's
ranks *m* + 1 onward. Every `LAST_RANK` reference, in the leagues and in
the nation's cups, is renumbered so it names the same club; `NOW_RANK`
references to places counted from the bottom of a table (the Dutch
playoffs) move with its size. The moved clubs' slots go to the other
division's UIDs, and table 0's starting divisions get the new records'
clubs. For England at 22 clubs: the first division keeps ranks 1–19
plus the two promoted clubs and the playoff winner, ranks 20–22 go
down, and the second division has 22 clubs (24 with yours and the
rival).

`python SRC/leaguesize.py plan DAT/PARAM England 22` shows the new slots
and the checks. `build` writes the three schedule packs with their
`.HED` and `PLRRSRC_INITTEAMDATA.TBB`, with the leagues' games
(`set_league`) and game days (`league_turns`) for the new sizes, reads
them back and plays out the first season again. Built and checked at
every size from 4 below to 6 above each nation's current first
division: England builds at 20–24, France 16–24, Germany 14–24 (and
more), Italy 20–24, Spain 18–24 and the Netherlands 16–22. The rest are
refused for lack of free turns (a second division's own-nation version
fills up first) or the 26-club limit of a division in table 0
(`plLg_EntryTeamSetToDiv`).

**Tested in PCSX2** (user report): England's first division at 22
clubs (`leaguesize.py build`, patched with `--copies` and
`--skip-tutorial`, disc `LMAST-eng22-test.iso`). In 2006–07 the Premier
Division table had 22 clubs, Reading and Sheffield U among them with
the promoted Sunderland and Wigan and the playoff winner West Ham. The
Champions Division had 24, the player's club and the relegated Crystal
Palace among them, and the player's club had 46 league fixtures: the
last three on May week 1 weekend, May week 2 midweek and May week 2
weekend, the last three turns `league_turns` gave UID 1. Saving and
reloading during the season worked.

The second season worked too (user report, with screenshots). The
2006–07 Premier Division ended with all 22 clubs on 42 games, and the
bottom three (Sunderland, Reading and Sheffield U) went down. The
Champions Division ended on 46 games: Ipswich and Leeds went up, and
ranks 3–6 (Southampton, Crystal Palace, SC Nottingham, Burnley) went
into the playoff, paired 3rd against 6th and 4th against 5th.
Southampton won it. In 2007–08 the Premier Division table again ran to
22 clubs, with Ipswich, Leeds and Southampton in it. The Champions
Division had Sunderland, Reading and Sheffield U, and Crystal Palace
and SC Nottingham, two of the losing playoff clubs, were still there.
The screenshots show that table only down to 15th place, so its 24
clubs rest on the user's report.

### Game days for a league of another size

**Empirical, all 21 domestic league UIDs** (the 18 divisions, the
Dutch playoff groups 50–51 and the runtime league 123): no league game
day falls on a turn with a game of a competition whose host changes
(the European club competitions 33–37, the national teams 44–47 and
the runtime cups 38–43) or of a knockout of the league's own nation.
The one exception is May week 3 weekend, the last game day of UIDs 0,
28 and 123, which is also a turn of the English and Italian promotion
playoffs (UIDs 3 and 31); only second-division clubs play in those.
`league_turns` keeps clear of the playoffs anyway. Competitions 0–32
each belong to one nation in `open_nation`: 0–5 England, 6–10 France,
11–15 Germany, 16–21 Italy, 22–26 Spain, 27–32 the Netherlands, in the
order of the starting leagues. The second divisions, which have more
game days, put the extra ones on free midweeks.

So a league's **free turns** are the turns inside its season (its first
to its last game day) that hold none of those games and none of its
own. `league_turns(uid, days)` adds free turns or drops game days to
reach a number of days: each added turn goes into the widest gap
between game days, a weekend before a midweek, and each dropped one is
a midweek first, then the one that leaves the smallest gap; the first
and last game days stay, so the season keeps its dates. For the English
first division at 22 clubs (42 days) it adds August week 3 midweek,
September week 1 midweek, October week 2 weekend and March week 1
weekend.

Room in each division within its current season (`python SRC/schedule.py
turns DAT/PARAM`). A second division's own-nation version holds your
club and the rival as well, 2 more than the other-nations version, so
it limits how far that division can grow:

| League | First division: clubs now, most | Second division: other-nations / own-nation now, most |
|---|---|---|
| England (UIDs 0, 2, 1) | 20, 24 | 24 / 26, 26 / 26: can't grow |
| France (10, 12, 11) | 20, 24 | 20 / 22, 26 / 26: up to 24 |
| Germany (19, 21, 20) | 18, 26 | 18 / 20, 26 / 26: up to 24 |
| Italy (28, 30, 29) | 20, 24 | 22 / 24, 24 / 24: can't grow |
| Spain (38, 40, 39) | 20, 24 | 22 / 24, 26 / 26: up to 24 |
| Netherlands (47, 49, 48) | 18, 22 | 20 / 22, 22 / 24: up to 22 |

More room would need the season to start earlier or end later (July
week 4 is free for the first divisions) or games on the turns the cups
use; neither is done.

`python SRC/schedule.py turns DAT/PARAM 0 42` draws the season with the
turns a 42-day schedule would add.

## Related files

- `0SYSTEM/SCHEDULE.TBB` (2 tables, 76 and 23 rows of 32 bytes, with a
  similar turn bitmask) is **not referenced by name**. `CVS/ENTRIES` dates it
  January 2005, a year before these packs, so it is an older version of the
  schedule table.
- `PARAM/GROUP2COMPE.TBB` holds 166 × s16 values. It matches neither the
  `year_schedule_data` competition (91 of 164 differ) nor the header's
  `+0x02` (93 differ). Only the `SIMPRG.REL` load list names it.
- `PARAM/SCHEDULE_LIST.TBB`: which competitions run in which year of the
  4-year cycle ([`PARAM_DIR.md`](PARAM_DIR.md)).

## Still unknown

- Game bits `w0` 8–9, header bytes `0x0A`–`0x0F`, `year_schedule_data`
  `+7`, and the first two team-entry header bytes.
- `PeriodName.tbb`, the `make_list` source functions and tables 1–8, and
  the meaning of the `savectrl` values.
- `GROUP2COMPE.TBB` and `CLUB_RANK_SYSTEM.TBB`.

## Checking the claims

```bash
python SRC/schedule.py info  DAT/PARAM        # every entry; reports UID 117
python SRC/schedule.py year  DAT/PARAM        # the 184 year_schedule_data rows
python SRC/schedule.py compe DAT/PARAM 6      # a 32-team knockout: games, pairings, links
python SRC/schedule.py entry DAT/PARAM 6      # where its 32 teams come from
python SRC/schedule.py league DAT/PARAM       # generated leagues of 2-32 clubs beside the disc's
python SRC/schedule.py turns  DAT/PARAM       # each domestic league's game days and room for more
python SRC/schedule.py turns  DAT/PARAM 0 42  # the English first division's season with 42 game days
python SRC/sles_disasm.py ISO/SLES_541.51 dis Sche_Block_decode_main2 makeTeamEntryIDList
```
