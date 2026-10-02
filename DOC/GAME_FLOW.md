<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# The game's flow (the root scripts)

The game's top level is a set of sequencer scripts in `DAT/SEQ/`
([`SQB_FORMAT.md`](SQB_FORMAT.md)). `RootMainSeq.sqb` runs from boot to
power-off. It starts the other `Root*Seq` scripts as subroutines
(`SeqSub.Create`) and the screens as modules (`Module.Start`). This page
reads them as a flow chart: what runs, in which order, and on which
branch. Everything here is **confirmed** from the scripts unless marked
otherwise; the offsets are script offsets, as `sqb.py dis` prints them.
The order matches the game manual's description of a new game and a
season.

## Reading the scripts

| Form | Meaning |
|---|---|
| `kN` | the number *N*. `Module.Start k36` starts module 36, `SeqSub.Create k13` script 13 |
| `BranchIfZero m3[0], 0, L` | an unconditional jump |
| `Module.GetBranch` | the value the module ended with: which menu item, which mode |
| `m4[1]` | the last subroutine's or module's result |
| `m4[2]` | set to 1 when the career ends (lost playoffs, game over in a match) |
| `m4[3]` | the event timing for the next `RootEventSeq` run ([below](#event-timings)) |
| `m4[4]` | set by the Option module when the player exits to the title |
| `m4[5]` | the Load module's result, then which part of `RootClubEditSeq` to resume |

## The scripts

| Id | Script | Started by | What it does |
|---|---|---|---|
| 1 | `RootMainSeq` | (boot) | boot, title, new game / continue / VS, the season loop |
| 2 | `RootMainMenuSeq` | `RootMainSeq` `0x0ff0` | the turn's main menu |
| 3 | `RootClubEditSeq` | `RootMainSeq` `0x0738` | club creation, the opening playoffs, the club edit |
| 4 | `RootMatchSeq` | `RootMainSeq`, `RootClubEditSeq`, `RootVsModeSeq`, `RootDemoMatchSeq` | one match day |
| 5 | `RootYearStartSeq` | `RootMainSeq` `0x0c98` | July: contracts and the year's plan |
| 6 | `RootYearEndSeq` | `RootMainSeq` `0x15c0` | the end-of-season report |
| 7 | `RootMonthStartSeq` | `RootMainSeq` `0x0d78` | the month's schedule and ticket price |
| 8 | `RootMonthEndSeq` | `RootMainSeq` `0x1530` | the month-end report |
| 9–11 | `RootOfficeSeq`, `RootClubHouseSeq`, `RootOwnerRoomSeq` | **nothing** | menus for the office, clubhouse and owner's room. No script starts them; `RootMainMenuSeq` opens the same screens itself |
| 12 | `RootLauncherSeq` | `RootMainSeq` `0x00d0`, skipped in retail | the developer launcher ([`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)) |
| 13 | `RootEventSeq` | 21 places | runs the Event module for one timing |
| 14 | `RootVsModeSeq` | `RootMainSeq` `0x0b60` | VS Mode |
| 15 | `RootDemoMatchSeq` | `RootMainSeq` `0x0620` | the attract-mode match when the title screen is left alone |

## Boot and title (`RootMainSeq`)

1. `Pwk.Create`, read the game-work file, set up messages.
2. `Dummy.CheckLauncher` (always 1 in retail), so the launcher is skipped.
3. SelectVideoMode (module 30), SelectLanguage (29), BootCheck (65), Logo
   (44).
4. Title (45). Its result picks the route:

| Title result | Label | Route |
|---|---|---|
| 0 | `L4` | `RootDemoMatchSeq`, then back to the title |
| 1 | `L5` | New Game |
| 2 | `L8` | Continue (Load) |
| 3 or more | `L11` | `RootVsModeSeq` |

## New game

`L5`: `Pwk.NewGame`, then `RootClubEditSeq` with `m4[5]` = 0:

1. HomeSelect (league and hometown), OwnerNameEntry, SelectTeamColor,
   SelectTeamStyle, `Pwk.ClubEditEnd`, InitialPersonnelAffairs,
   SelectSecretary, then a save (Save module, argument 3).
2. The opening playoffs (`0x08b0`–`0x0cf0`, see
   [`SQB_FORMAT.md`](SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs)).
   A loss plays the game-over cutscene and sets `m4[2]` = 1.
3. After a win: `Pwk.PromotionEnd` and a save (argument 4).
4. CheckClubEdit, then the ClubEditMenu: team name, first kit, second
   kit, flag, emblem.

Back in `RootMainSeq`, `m4[2]` = 1 returns to the title. Otherwise
`Sche.Initialize` and the season loop starts at `L15`.

## Continue

The Load module's result goes to `m4[5]` and picks where to resume. The
saves the scripts make use the same numbers as arguments to the Save
module, so the Load result is the kind of save loaded (**empirical**,
from the matching numbers):

| Load result | Resumes at | Saved by |
|---|---|---|
| 0 | the title (cancelled) | |
| 1 | `L9`: the turn's main menu | Option module (the manual's SAVE); `RootOwnerRoomSeq` also has Save 1 but never runs |
| 2 | `L10`: the year start | `RootMainSeq` `0x1688`, after each season |
| 3 | `RootClubEditSeq` `L2`: the start of the playoffs | `RootClubEditSeq` `0x0800` |
| 4 | `RootClubEditSeq` `L10`: the club edit | `RootClubEditSeq` `0x0d90` |

## The season loop (`RootMainSeq` `L15`–`L24`)

```
L15  Sche.YearStart, RootYearStartSeq, Pwk.CheckGameOverSikin (funds)
L16  Sche.MonthStart, RootMonthStartSeq
L17  turn start: Sche.TurnStart, Pwk.TurnStart, events 22, 4, 23
L18  RootMainMenuSeq (exit to title -> L28)
L19  week end: PracticeExecute, event 21, the turn's matches (RootMatchSeq)
L21  turn end: event 9, Sche.TurnEnd; domestic and European end-of-turn
     cutscenes. Not the month's last turn -> L17
     RootMonthEndSeq, Sche.MonthEnd. Not the year's last month -> L16
     RootYearEndSeq, Sche.YearEnd. Game over -> L25
     save (argument 2) -> L15
```

`Sche.YearStart` also runs the year's updates in the code (sponsor and TV
contracts, towns, schedules: `ScheCallbackCommand_YearStart`, `0x113608`).

### Year start (`RootYearStartSeq`)

In order (the manual's "Season in"):

| Offset | Step |
|---|---|
| `0x00a8` | `Pwk.YearStartFirstHalf`, `Event.YearStart`, cutscene 4, event 0 |
| `0x01a0` | `Pwk.CheckPlayerEdit`: if there are edited players, CheckActionPlayerData (68) and event 19 |
| `0x0318` | event 16, then the Sponsor contract screen (55). Its results 1 and 2 open UniformEdit for the first or second kit, then return to it |
| `0x0640` | `Pwk.CheckTV`: when TV contracts are possible, event 17 and Broadcast (62) |
| `0x0750` | event 15, StaffContract (32), `Pwk.YearStartDischarge` |
| `0x0828` | PlayerContract (46), not in the first year (`Sche.GetYear` = 0) |
| `0x08c0` | SelectUniformNumber (54), `Pwk.YearStartJoin` (new players join), SelectCaptain (51), ManaPlan (64, the administrative plan), `Pwk.YearStartSecondHalf` |
| `0x09d0` | first year only: five cutscenes (16, 3, 17, 13, 5), the rivals and the press conference in the manual |
| `0x0c20` | event 1 |

The manual's order (sponsor, TV, manager/coach, scouts, players, numbers,
captain, administrative plan) is the same.

### Month start, month end, year end

- `RootMonthStartSeq`: cutscene 4 (not at the season start), events 2
  and 18, Schedule (39), `Sche.CalendarEnd`, TicketSet (61),
  `Sche.EndMonthStart`, event 3.
- `RootMonthEndSeq`: MonthEnd (34, the month-end report), event 10.
- `RootYearEndSeq`: SeasonEnd (33, the season-end report), event 11.

`Dummy.CheckYearMonthTurnSkip` (command 86) skips the screens of all
three, keeping only the `Pwk`/`Event` calls. It is the developers' skip,
like the tutorial skip.

### A turn's main menu (`RootMainMenuSeq`)

Event 7, then the SideMenu (13). Its result opens a screen and returns to
the menu, until 0 ends the turn (`Event.MenuEnd`, event 8):

| Result | Module | Result | Module |
|---|---|---|---|
| 1 | Mail (43) | 8 | PublicRelations (40) |
| 2 | News (41) | 9 | Practice (25) |
| 3 | Information (11) | 10 | ScoutingMenu (37) |
| 4 | Option (59); EXIT sets `m4[4]` and ends the menu | 11 | PersonnelAffairsMenu (15) |
| 5 | Account (56) | 12 | Talk (31) |
| 6 | Institution (42) | 13 | Youth (50) |
| 7 | Business (57) | | |

### A match day (`RootMatchSeq`)

`Sche.MatchBranch` 0 means a match the player doesn't take part in: it is
only finalised. Otherwise: event 5; `Pwk.CheckGameOverMember` (game over
with cutscene 8 and `m4[2]` = 1); the pre-match MatchMenu (35, argument
0); the Game module (6), the 3D match, unless `Dummy.CheckMatchSkip`;
SimRoot again; the post-match MatchMenu (argument 1); GameIncome (52);
event 6.

## Game over

| Where | Check | Cutscene (PlayAcrobata argument) |
|---|---|---|
| `RootClubEditSeq` `0x0b28` | the playoffs lost (`Sche.FirstCheck`) | 7 |
| `RootMatchSeq` `0x00a8` | `Pwk.CheckGameOverMember` | 8 |
| `RootMainSeq` `0x0ce0` | `Pwk.CheckGameOverSikin` after the year start ("shikin", funds) | 10 |
| `RootMainSeq` `0x1608` | `Sche.YearEnd` non-zero: 1 plays 9, other values 10 | 9 or 10 |

The manual lists four ways to lose: failing the playoffs, funds in the
red in the first week of July, finishing in the 2nd league's bottom two
two years running, and fewer than 8 players. Those match the four checks.
Which `Sche.YearEnd` value is the relegation and which is the other end
of a career (an ending?) hasn't been traced. The PlayAcrobata argument
isn't a scene id (scene 7 is a clubhouse background); how the module
maps it is still open ([`ACROBATA_DIR.md`](ACROBATA_DIR.md)).

## Event timings

`RootEventSeq` starts the Event module (14) with `m4[3]` as its
argument. **Confirmed:** the module keeps it at `+0x198`
(`SIMPRG.REL 0x6a50`) and passes it to `0x129e98` (`0x6c14`), which
passes it to the event scan `0x12df08` (`0x129f14`) as the timing an
event's `+0x68` must equal ([`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md)).
So the values the scripts set name the timings:

| Timing | When (script) | EVENT records |
|---|---|---|
| 0 | year start, after cutscene 4 (`RootYearStartSeq`) | 16 |
| 1 | end of the year start | 0 |
| 2 | month start, first | 4 |
| 3 | month start, after the ticket price | 3 |
| 4 | turn start, second | 154 |
| 5 | before a match (`RootMatchSeq`) | 32 |
| 6 | after a match | 3 |
| 7 | the main menu opens | 0 |
| 8 | the main menu closes (turn's end) | 69 |
| 9 | turn end | 38 |
| 10 | month end, after the report | 0 |
| 11 | year end, after the report | 5 |
| 12 + *n* | each playoff match day; *n* is `Dummy.GetFirstMatchCount` (`RootClubEditSeq` `0x0960`) | 12: 1, 13: 1 |
| 15 | before StaffContract | 1 |
| 16 | before the Sponsor screen | 2 |
| 17 | before the Broadcast (TV) screen | 1 |
| 18 | month start, second | 8 |
| 19 | year start, after CheckActionPlayerData | 2 |
| 21 | week end, before the matches | 5 |
| 22 | turn start, first | 0 |
| 23 | turn start, third | 0 |

The counts are the EVENT table's 382 records (37 more have −1, which
never matches). The one-off timings carry the tutorial explanations,
for example 16 Jane on sponsors, 17 a foreign TV station, 15 Robert
introducing himself, 12 and 13 the playoff manager. No script sets 20,
and 14 only if `GetFirstMatchCount` reaches 2; no EVENT record uses
either.

## Still unknown

- Which `Sche.YearEnd` value is which ending or game over, and what the
  PlayAcrobata arguments (3, 4, 5, 7–10, 13–17) show.
- What the Dummy module run with argument 15 at turn start does (its
  non-zero result skips the main menu).
- What `Root9` (command 9) and `Root13` (command 13) do; `RootEventSeq`
  skips the Event module when `Root13` returns non-zero, probably when
  nothing is due.
- Who sets the Load module's result 1: the Option module's save is
  assumed, not traced.

## Checking the claims

```bash
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB
python SRC/sqb.py dis DAT/SEQ/ROOTYEARSTARTSEQ.SQB
python SRC/sqb.py dis DAT/SEQ/ROOTMAINMENUSEQ.SQB
python SRC/sqb.py names DAT/SEQ/SQBFILENAME.TBB
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x6a00 140 --sles ISO/SLES_541.51   # Event module keeps its argument
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_EVENT.BIN events.csv        # the timing column
```
