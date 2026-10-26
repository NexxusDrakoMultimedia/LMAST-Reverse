<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Schedule limits: where the game fixes the schedules at 164

The career calendar has 164 schedule UIDs, 0–163
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)). The LMASTER third tier
needs six more, one hidden league per nation
([`LMASTER_MOD.md`](LMASTER_MOD.md#improvements), phase 3). This doc
lists what fixes the count at 164: the data, which sets it for most of
the schedule code, and the few code sites that name it.

## 164 is "no competition"

**Confirmed.** About 30 calls pass group 164 (`0xa4`) to
`pwkOteam_GetTeamData`/`GetTeamDataEx` (`0x24ba08`, `0x24bd30`), which
hands it to `plRec_MatchRegulations` (`0x21dc60`): `REGULATION.TBB`'s
row 164, the file's 165th, is the default rules for a club outside any
competition. Among the callers: `ScheCallbackCommand_CreateGiForFirstMatch`
(`0x114500`), `BestEleven` (`0x2d4a18`), the stationary player lists
(`0x2b6cb0`), and in `SIMPRG.REL` the Information module (`0x1258`),
the club editor (`0x50030`, `0x513d4`), the player search
(`0x926e4`), the rank lists (`0x95560`), the monthly report
(`0x9f944`, `0x9f960`), the events (`EVS::`, 13 sites) and the rival
records (`0x15f304`, `0x15f79c`, `0x15f940`). `VSPRG.REL 0x6f8c` too.

So UID 164 can't be a schedule. The third tier's UIDs are **165–170**.

## The data

The schedule code takes its count from the files, not from an
immediate (**empirical**: no loop over UIDs in the schedule functions
is bounded by 163–165; the scan below):

| File | Per UID | Now |
|---|---|---|
| `SCHEDULE_SYSTEM.PAC` `year_schedule_data.tbb` | a 20-byte row, found by UID (`getYearSchedule`, `0x20a170`) | 184 rows |
| `SCHEDULE_SYSTEM.PAC` `savectrl.tbb` | a byte: the save pool's type (below) | 164 |
| `SCHEDULE_COMPETITION.PAC`/`.HED` | an entry: games and pairings | 164 |
| `SCHEDULE_TEAM_ENTRY.PAC`/`.HED` | an entry: where the entrants come from | 164 |
| `REGULATION.TBB` | a row: rules, money, place slots | 165 (row 164 the default) |

`PRELOAD/STATIONFILE.PAC` holds copies of the schedule packs, and
`PRELOAD/SIMFILE*.PAC` of `REGULATION.TBB`
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#writing)). Competitions 50–55
already have `open_nation` rows, names (message category 100009) and,
with `--mod third-tier`, past records.

## Code that names the count

**Confirmed**, each read with its function:

| Site | What it does | For 165–170 |
|---|---|---|
| `SIMPRG.REL 0x3cfcc` (`TICKET_SET_MODULE`) | loops UIDs 0–163 (`slti 0xa4`) for a competition with your home game in the month's eight days (`0x3da80`); "none found" is the loop's end, tested against a second 164 in `$s6` (`0x3cfb8`) | as it is: you never play in a third tier |
| `GAMEPRG.REL 0xa069c` | a per-UID table of match-presentation flags at `0x26f748` (164 words); 164 and up get entry 0 | as it is |
| `GAMEPRG.REL 0x9f144` | the same table for the match being played, with no bound | never reached: you never play a third-tier match (the one-season game over ends the game first) |

Not about UIDs, though they hold 163–165: `GAMEPRG.REL`'s 163-byte
arrays at `+0xa7` (`0x97ac0`, `0x97b58`, `0x9c7b0`),
`can_use_match_rand` (26 sites), and the events' message ids.

## The save pools

**Confirmed** (`ScheEuro_Memory::init`, `0x209210`): a loaded
schedule's games, team stats and entrants live in save block 5
(`pwkRec_GetGameResult`, `GetTeamStats`, `GetCompeTeam` and their
system buffers), shared out by bitmap allocators (`CBitMapBlock`), one
per `savectrl` type and kind:

| Kind | Unit | Type 0 | Type 1 | Type 2 |
|---|---|---|---|---|
| games | 16 bytes | 5,824 | 320 | 96 |
| team stats | `0x138` bytes | 704 | 160 | 160 |
| entrants | 8 bytes | 704 | 160 | 160 |

**Empirical** (the schedule packs; a script summing every UID a
normal season loads): the type 0 schedules, the big leagues among them,
take about 5,300 games and 616 entrants. The six tier leagues as type 0
add about 50 games (England's 5 clubs, 20 games; 3 clubs elsewhere, 6
each) and 20 entrants, so they fit. Types 1 and 2 add up to more than
their room in that sum, so their slots must be freed as schedules end,
or some rows load only in some years; that isn't traced, and the tier
leagues don't use them.

## Loading more schedules

**Confirmed** (`CScheEuro`): nothing else holds a table per UID.

| Address | Symbol | What it shows |
|---|---|---|
| `0x2044f0` | `CScheEuro::makeStartCompeList` | walks the year rows by their count from the file (`+0x368`), keeping the UIDs to load in a growable vector |
| `0x2068f8` | `CScheEuro::OneLoadCompCB` | a loaded schedule takes a group slot (`getGroupIndexFromUID`, `getEmptyGroupIndex`); its `savectrl` byte is read at the table + UID (`0x206a20`), from the file |
| `0x2df600` | `scheCtrl_GetGroupStatusAddrFromUID` | a group keeps its UID as an unsigned byte (`lbu +3`), so UIDs up to 255 fit |
| `0x2d9ae0` | `ScheduleControllerBaseSystem::InitStatus` | 128 group slots. A season loads fewer than 118 schedules even counting every runtime one, so six more fit |
| `0x2055f0` | `CScheEuro::getPeriodNameFromUID` | round names come from the schedule's rules and type, not a table by UID |

## `--mod third-tier`: the tiers' seasons (phase 3)

`patch_disc.py --mod third-tier` (with `--copies --dat`; built and
tested as five switches, `save-expand`, `tier-clubs`, `tier-lists`,
`tier-uids` and `one-season-end`, merged on 2026-10-27) adds the third
tiers, one per
nation in the order of competitions 50–55 (England to the Netherlands),
and moves clubs between them and the second divisions.

**The leagues.** Each nation's tier has an other-nations version, UIDs
165–170 (3 clubs), and an own-nation version, 171–176 (5 clubs), as the
second divisions have (load kinds 2 and 1):

- `year_schedule_data`: a row each, loaded every season, its result
  kept (`+7` is 1, which `calcCompetetionFinish` needs), its game days
  spread evenly over its second division's (other-nations UIDs 2, 12,
  21, 30, 40, 49), first and last kept.
- `savectrl`: type 0 for 164–176 (177 bytes).
- `SCHEDULE_COMPETITION`: a league each, both legs (3 clubs: 6 games on
  6 game days; 5 clubs: 20 on 10); entry 164 is a copy of 163 and is
  never loaded.
- `REGULATION.TBB`: rows 165–176 copy the second division's, for their
  clubs, with one place up to it; row 164 stays the default.

**The movements**, in `SCHEDULE_TEAM_ENTRY` (all `LAST_RANK`, last
season's records):

| Schedule | Takes |
|---|---|
| a second division, either version | its own ranks as before but the last (England: 7–23), its tier's rank 1 |
| a tier | its own ranks 2–3 (your nation: 2–5), its second division's last |

The second divisions' `REGULATION` rows send 1 club down, not 2, so
the one-season game over's line is the last place. Every own-nation version of
a domestic UID (the second division and each nation's cups) differs
from its other-nations version only by places for your club and the
rival past the second division's record; each becomes a copy of it,
with the UIDs its `NOW_RANK` records and place slots name moved to the
own versions. So your second division has its real size (England 24
with your club and the rival).

**The lower cups.** Each nation's lower cup (competitions 5, 10, 15, 21,
26 and 32: the English League Cup and the Club Cups) takes every club of
its tier's record, last season's ranks 1–3 (your nation: 1–5), in
slots after its own (the user's choice, 2026-10-27; the qualifying
round and the main cup are as they were). Its knockout is rebuilt at the
new size with `schedule.py`'s builder
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#building-a-knockout)), and
`REGULATION.TBB` and `CLUBRESULT.TBB` get its club count (the round
names depend on it). Every lower cup starts on Dec w1 midweek (turn 40,
the user's choice), the main cup's first round, whose clubs (the
qualifying winners and the first division) a lower cup doesn't have, as
on the turns they shared already; its other rounds stay on the disc's
midweeks for that many rounds. No round falls on a European or
national-team day (the user's rule).

| Nation | Clubs (other nations / yours) | Rounds | Turns |
|---|---|---|---|
| England (UIDs 9 / 8) | 15 / 17 | 4 / 5 | 40, 50, 54, 76 / 40, 44, 50, 54, 76 |
| France (18 / 17) | 11 / 13 | 4 | 40, 50, 54, 76 |
| Germany (27 / 26) | 7 / 9 | 3 / 4 | 40, 54, 76 / 40, 50, 54, 76 |
| Italy (37 / 36) | 13 / 15 | 4 | 40, 50, 54, 76 |
| Spain (46 / 45) | 13 / 15 | 4 | 40, 50, 54, 76 |
| Netherlands (57 / 56) | 9 / 11 | 4 | 40, 50, 54, 76 |

**Empirical**, a script over the switch's files: in season 1 of each
nation, as yours and not, the qualifying round, the main cup and the
lower cup take no club twice by last season's records, with
`ProcPromotion`'s moves (below) in your nation. The tier's rank 1 is
the club now in the second division (the one promoted, or in season 1
the one seeded there), as the user's rule wants. Not seen in game yet.

**Season 1.** The seeding loop (`0x253200`) reads the seed table's rows
to 55, and `PLRRSRC_INITTEAMDATA.TBB` table 1 gets rows 50–55: each
second division's seeded last place holds one of its tier's clubs, and
the tier's record that last club and the other two. So everyone starts
where the seeds put them: the second division keeps its clubs, the tier
has its three. The tier club in that last place plays its nation's cups
in season 1 (later, the club relegated there does). In your nation,
`ScheCallback_ProcPromotion` (`0x1131c8`), rewritten in its own 76
words, puts your club and the rival at ranks S − 2 and S − 1 of the
second division's record, where S is its seeded size, and moves the
clubs it finds there to the tier's record:

| Record | As seeded | After |
|---|---|---|
| second division | ranks 1–(S − 1), a tier club at S | ranks 1–(S − 3), your club, the rival, the tier club |
| tier | the second division's S, two tier clubs | the second division's S − 2, two tier clubs, its S − 1, its S |

The second division then takes ranks to S − 1 and the tier's rank 1:
its seeded clubs but the two at S − 1 and S, which play the 5-club tier
with the three tier clubs. It does nothing if your club or the rival is
in the record already, as the retail code did.

**Season end.** `CScheEuro::calcCompetetionFinish` writes the tables of
competitions to 55 (`0x205fa8`). The yearly honours
(`pwkRec_GetCompeConventionRecord*`) exist for 0–48 only, so two
detours in the LMASTER code segment (`0xf8280`, after the save wrappers'
`0x280` bytes) skip them from 49: the call to
`pwkRec_ShiftCompeConventionRecord` (`0x205fc0`), and everything after
the table (`0x20631c`: the winner, best eleven, MVP, top scorer, title
effects), which goes to the function's clean-up (`0x20651c`). A rival
in a tier is a club like any other (the user's choice); its year-end
division record (`pwkRec_UpdateCompeRecordYearEnd`) is skipped there.

**No code** in the ticket module's loop (`0x3cfcc`), which stays at
164. **Seen in PCSX2** (user report): with only its bound raised to
171, the "none found" test at `0x3cfb8` (still 164) failed, and the Set
Up Ticket Price screen came up again and again with no competition
named.

The packs' headers grow to 177 entries in the same 4,096 bytes
(`pac.grow_binpac_header`), so the `.HED` files keep their size. The
switch writes the `PRELOAD` copies too (`STATIONFILE.PAC`'s
`schedule_system.pac` and `.HED` copies, which the game loads, and the
seven `SIMFILE*.PAC` copies of `REGULATION.TBB` and `CLUBRESULT.TBB`), so it refuses to run
without `--copies`. `python SRC/schedule.py info` accepts the 177-UID
layout and finds no new problem (UID 117 as on the retail disc).

**Played out offline** (**empirical**, a script over the switch's
files): five seasons with each nation as yours, each schedule filled
from the records, a random final order for each, and the records
written as `calcCompetetionFinish` does (the Dutch playoff groups
interleaved). Every slot of every league, playoff and cup is filled, no
club is in a schedule twice, and each nation's clubs are split once
between its first division, second division and tier, 262 clubs in all,
the sizes the same every season.

**Seen in PCSX2** (user reports, 2026-10-27), with the leagues alone
(`LMAST-test-tieruids2.iso`, UIDs 165–170 then): a new career plays
into September past the tiers' first game days, the All Clubs Ranking
lists the tier clubs, and the Information screen's Competitions tab
doesn't list the tiers, as the design wants (it must take its
competitions from a list of its own; not traced). With the movements
(`LMAST-test-tiers.iso`, an England career with the tutorial skip): the
Champions Division's table after its first game day has 24 clubs, your
club and the rival among them (user report, with a screenshot). In a
German career (`LMAST-test-tiers-germany.iso`, `--skip-nation
Germany`), the two clubs sent down to the Third German League at the
start were Siegen and Offenbach (user report). Your nation's cups, now
copies of the other nations' versions, run on their usual turns: the
German Club Cup's semi-finals were on December week 3 midweek with its
4 clubs, the qualifying round's losers, one of them Trier, the tier
club in the seeded last place (user report, with a screenshot). On
that disc the cup had 2 rounds where your nation's retail version had
3 (6 clubs); it now takes the tier's clubs as well ([The lower
cups](#--mod-third-tier-the-tiers-seasons-phase-3), 9 clubs in 4 rounds).

**The first season's end failed, and is fixed** (user report, with
screenshots and the save, 2026-10-27). The tiers' year rows had `+7` at
0, so `calcCompetetionFinish` (`0x205f88`) kept none of their results:
the save's records for competitions 50–55 still held their seeds (count
0), while the second divisions' were written. Each second division then
took its tier's seeded rank 1, a club it already had, so in England
Sheffield played the Champions Division twice, and in Germany Paderborn,
last in the 2nd German League and at the tier's rank 1 since the
career's start, stayed up. The rows now have `+7` at 1. The offline
play-out keeps results only for such rows, and finds the bug in the old
files (clubs twice from season 2) and none in the new
(`LMAST-test-tiers-germany2.iso`). Because `updateTurnEnd` (`0x2033e0`)
marks a result kept before calling `calcCompetetionFinish`, a career
from the old disc only recovers if it is saved before the tiers' last
game day (May) and loaded from the card on the new disc. The test
career was saved later (turn 95, June), so its tiers' records were
written into the save by hand, from their true final tables read out
of block 5's pools ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-blocks)): in
Germany Siegen won the tier and Trier was last.

**Tested in PCSX2** (user report, with screenshots, 2026-10-27): that
career, loaded on `LMAST-test-tiers-germany2.iso`, plays through the
year end into 2007–08. The 2nd German League's 18 clubs have Siegen, the
tier's winner, and not Paderborn, last the season before; Burghausen,
17th, stays. England's Champions Division (other nations, its tier's
record from the same hand-written tables) has Gillingham, English League
1's winner, Sheffield once, and not Hull, last the season before. So
both versions move one club each way.

## Still unknown

- When a schedule's pool slots are freed, and the true peak of each
  pool over a season.

## Checking

The scan is a short script over `gamever.image` of the executable and
each overlay: every `addi`/`addiu`/`slti`/`sltiu`/`andi`/`ori` with an
immediate of 163–165 (132 sites, 82 not a structure offset), and in the
schedule and record functions every immediate that is a multiple of 164
(none an array size). Then:

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis init__15ScheEuro_Memory
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x3cfa8 20 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0xa0698 10 --sles ISO/SLES_541.51
python SRC/schedule.py year DAT/PARAM
```
