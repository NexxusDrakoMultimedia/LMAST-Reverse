<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/SEQ`: the root sequencer scripts

`DAT/SEQ` (22 files, 37,808 bytes, plus `CVS/`) is folder id **1** in the
game's file manager ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). It holds the
root scripts of the game's sequencer: the scripts that decide which
screen module runs next, from the boot through the season to the match.
Their format, the command sets and the global variables are documented in
[`SQB_FORMAT.md`](SQB_FORMAT.md); this page is the folder overview.

`python SRC/sqb.py info DAT/SEQ DAT/PARAM` checks every script, and
`python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB` lists one. The writers
are `sqb.py setcmd`, which swaps single commands, and `sqb.py settable`,
which changes the cells of a PwkScript's data tables (here only
`PINFOPOINT.SQB` has any); both are described in
[`SQB_FORMAT.md`](SQB_FORMAT.md#editing). `patch_disc.py` uses `setcmd`
for the developers' launcher and the tutorial skip
([launcher](SQB_FORMAT.md#the-developer-launcher),
[tutorial skip](SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs)).

## Files

| File | Kind | Read by | Contents |
|---|---|---|---|
| `SQBFILENAME.TBB` | TBB, 18 × `char[32]` | `0x149f30` | the list of root scripts by id: rows 1–15 are the `Root*Seq.sqb` files, row 16 is `PinfoPoint.sqb`, rows 0 and 17 are `"NULL"`. **confirmed** |
| `GLOBALMEMORY.TBB` | TBB, 25 × 16 bytes | `0x14a050` | the sequencer's global variables ([`SQB_FORMAT.md`](SQB_FORMAT.md#global-memory-globalmemorytbb)). **confirmed** |
| `ROOT*SEQ.SQB` (15) | `SQB1` | `0x14a220`, through `SQBFILENAME` | root scripts 1–15. **confirmed** |
| `PINFOPOINT.SQB` | `SQB1` | the same, id 16 | an older build of `PSCCOMMON.PAC#PscCommon_PinfoPoint.sqb` (same size, 4 script words differ) |
| `A001.SQB` | `SQB1` | nothing | a 2004 test loop that counts 600 down in a function; not in `SQBFILENAME.TBB` |
| `CHECKCLUBEDIT.SQB`, `INFORMATION.SQB` | `SQB1` | nothing | 2004 scripts for command sets the retail game doesn't have ([what doesn't decode](SQB_FORMAT.md#what-doesnt-decode)) |
| `INFORMATION.WPX` | `TBB1` of 4 `TBL1` tables | nothing | tables of 49, 45 and 45 bytes and 8 rows of 4, holding floats such as 30.0, 70.0, 300.0 and 380.0. Content not decoded. No `.wpx` string appears in the executable or any overlay |

No file here has a copy in `PRELOAD` or anywhere else on the disc
(**empirical**). The PwkScript scripts (`PSC*.PAC`) are in `PARAM/`, not
here ([`PARAM_DIR.md`](PARAM_DIR.md)).

## The root scripts

The ids are the rows of `SQBFILENAME.TBB` (`python SRC/sqb.py names
DAT/SEQ/SQBFILENAME.TBB`). A script starts a screen module with
`Module.Start` and runs another root script as a sub-sequence with
`SeqSub.Create`, whose argument is one of these ids. The table is
**empirical**, read from `sqb.py dis`, with the modules in the order a
script first starts them (module names:
[`SNR2_FORMAT.md`](SNR2_FORMAT.md#which-overlay-the-game-loads)):

| Id | Script | Commands | Starts these modules | Runs these scripts |
|---|---|---|---|---|
| 1 | `RootMainSeq` | 287 | SelectVideoMode, SelectLanguage, BootCheck, Logo, Title, SimRoot, Load, Dummy, PracticeExecute, PlayAcrobata, Save | 12, 15, 3, 14, 5, 7, 13, 2, 4, 8, 6 |
| 2 | `RootMainMenuSeq` | 146 | SideMenu, Mail, News, Information, Option, Account, Institution, Business, PublicRelations, Practice, ScoutingMenu, PersonnelAffairsMenu, Talk, Youth | 13 |
| 3 | `RootClubEditSeq` | 208 | NewGameInstall, PlayAcrobata, ClubEditBG, HomeSelect, OwnerNameEntry, SelectTeamColor, SelectTeamStyle, InitialPersonnelAffairs, SelectSecretary, Save, CheckClubEdit, ClubEditMenu, TeamNameEntry, UniformEdit, FlagEdit, EmblemEdit | 13, 4 |
| 4 | `RootMatchSeq` | 126 | PlayAcrobata, MatchMenu, Game, SimRoot, GameIncome | 13 |
| 5 | `RootYearStartSeq` | 136 | PlayAcrobata, CheckActionPlayerData, Sponsor, UniformEdit, Broadcast, StaffContract, PlayerContract, SelectUniformNumber, SelectCaptain, ManaPlan | 13 |
| 6 | `RootYearEndSeq` | 20 | SeasonEnd | 13 |
| 7 | `RootMonthStartSeq` | 42 | PlayAcrobata, Schedule, TicketSet | 13 |
| 8 | `RootMonthEndSeq` | 20 | MonthEnd | 13 |
| 9 | `RootOfficeSeq` | 40 | Office, Dummy, Institution | – |
| 10 | `RootClubHouseSeq` | 52 | ClubHouse, Practice, Dummy, PersonnelAffairsMenu, Talk, Youth | – |
| 11 | `RootOwnerRoomSeq` | 40 | OwnerRoom, Mail, News, Information, Save | – |
| 12 | `RootLauncherSeq` | 74 | Launcher, SimRoot, Dummy | – |
| 13 | `RootEventSeq` | 29 | Event, WildCard | – |
| 14 | `RootVsModeSeq` | 63 | VSModeRegulation, VSModeScheduleTop | 4 |
| 15 | `RootDemoMatchSeq` | 30 | SimRoot | 4 |

`RootMainSeq` is the top of the tree: the boot screens, then the career
and the season loop (it runs the schedule steps `Sche.*` and starts
the year, month, event, match and menu scripts), the launcher check
([`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)) and the demo
match. Scripts 1–8 each run `RootEventSeq`, which starts the Event
module and then the wild-card module, the screen the last event queued
([`SNR2_FORMAT.md`](SNR2_FORMAT.md#which-overlay-the-game-loads)).
Script 16, `PinfoPoint.sqb`, is a PwkScript, not a root script.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x149f30`–`0x149fc4` | (sequencer setup) | opens `SqbFilename.tbb` with folder 1 (the virtual open call at `0x149f98`, `$a1` = 1) and reads the table with `TbbData::GetTableDataPtr` |
| `0x14a050`–`0x14a0c4` | the same | opens `GlobalMemory.tbb` with folder 1 |
| `0x14a220`–`0x14a304` | the same | for each `SQBFILENAME` row that isn't `"NULL"` (`strcmp` against the string at `0x523118`), copies the name and opens it with folder 1 |

So the game reads exactly the 16 scripts named in `SQBFILENAME.TBB`
(ids 1–16). `A001`, `CHECKCLUBEDIT` and `INFORMATION` are never loaded,
and no `.wpx` name appears in the code.

## CVS history

The folder's `CVS/ENTRIES` ([`CVS_DIR.md`](CVS_DIR.md)) shows how much
the root scripts were worked on: `RootMainSeq.sqb` is at revision 1.129,
`RootLauncherSeq.sqb` at 1.106 and `RootClubEditSeq.sqb` at 1.95. Most
root scripts were last committed on 4 February 2006, and `RootEventSeq`,
`RootLauncherSeq` and `RootYearStartSeq` on 27 April 2006. The four
files the game never loads (`A001`, `CheckClubEdit`, `Information.sqb`
and `Information.wpx`) were last committed in 2004, and so was
`PinfoPoint.sqb`, which is loaded. `RootOfficeSeq` and `RootOwnerRoomSeq`
(2005) are the only root scripts not touched in 2006. `SqbFilename.tbb`
is at 1.19 (December 2005) and `GlobalMemory.tbb` at 1.3 (February 2005).

## Still unknown

- What `INFORMATION.WPX` holds and what it was written for (nothing loads
  it).

The open questions about the command sets (the sets the two 2004 scripts
`INFORMATION.SQB` and `CHECKCLUBEDIT.SQB` were written for, a few unnamed
commands, `BranchIf`) are in
[`SQB_FORMAT.md`](SQB_FORMAT.md#still-unknown).
