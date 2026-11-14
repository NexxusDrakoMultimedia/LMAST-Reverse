<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Runtime memory: the season, competitions and events

This doc covers the part of the game's memory that follows a career
through time: the calendar (the date and the turn counter), the
competitions and their tables, the national teams and their tournaments,
the career records and counters, and the event, mail and news flags.
It records where the game keeps this data while it runs, so that tools
and achievement sets (RetroAchievements reads the PS2's main memory,
EE RAM, 0 to 0x1FFFFFF, little-endian) can find it. The save file holds
the same data in packed form ([`SAVE_FORMAT.md`](SAVE_FORMAT.md)); this
doc is about the live copy.

Every address is an EE RAM address in the PAL release (`SLES_541.51`).
The Japanese release (`SLPM-66316`) keeps its career root in a different
place and its blocks differ in size, so nothing here transfers to it
without a check ([`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)). Where a
row gives an address as `SIMPRG.REL 0x...`, that is a position in the
overlay as `snr2.py dis` prints it, not a RAM address; the overlay's
load address is found at run time (see the events section).

Nothing here was measured in PCSX2 unless a row says so. The rows come
from reading the game code, and each one was checked twice by a second
reader. The only tests in the running game that touch this memory are
the save-state test recorded in [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far)
(Nexxus's report, 2026-10-27), which read the block chain and the club
status. Treat every other value range and every statement about timing
as read from code, not seen.

## How to read this doc

The labels follow the repo's rules:

- **confirmed**: the game code shows it. The row cites the address and,
  usually, the symbol of the function that proves it. Run the `dis` or
  `addr` command in "Checking the claims" to see it yourself.
- **empirical**: inferred from data (a save, a table on the disc) and
  not shown by the code. A row may mix the two, for example "arithmetic
  confirmed, naming empirical".
- **unconfirmed**: each section lists, in its own "Unconfirmed"
  subsection, what the review refuted, corrected or could not verify.
  Do not build on those.

Most of the data hangs off one static word, the career work area (the
"pwork", a heap object of 0x5c bytes) at 0x3909a8. In the tables, `P`
is the 32-bit value at 0x3909a8, and block k of the work area is at
`u32[P+0x1c] + u32[P+0x28+4k]` (k = 0 to 10). Block 0 holds the date
and the event data, block 1 your club, block 5 the records and the
schedule state, block 6 the calendar. The sections name these `B0`,
`B(0)` or "block 0" and define their notation again at the top; they
all mean the same chain. A second static word, 0x390650, points to the
schedule controller object, which exists only while a schedule is
loaded.

A pointer chain row ("Pointer chains and stability" in each section)
has four columns:

| Column | Meaning |
|---|---|
| Entry | the value or record the row is about |
| Root and offsets | the chain: start at a static address, read a 32-bit word, add an offset, read again. `u32[x]` is the 32-bit value at address `x` |
| Valid when | the test to pass before trusting a read, because the contents are blank or unrelated outside a career |
| Stable across | what leaves the address and the value unchanged (frames, menus, matches, save and load, year roll-over) and what makes them jump |

In RetroAchievements terms each hop of a chain is an indirect read:
load the pointer, add the offset, read the field. Each section's
"RetroAchievements notes" say where a hop needs care. The points that
apply to every section:

- The root at 0x3909a8 is non-zero from boot, so it does not mean a
  career is running. Gate a read on a sane date, or on the schedule
  object's mode word, as the notes say.
- The block addresses are fixed for a whole boot, but whether they are
  the same on the next boot is not settled (the block order is
  shuffled once at start-up). Read the chain, never hard-code a sum.
- A load, a new game, the title attract demo and VS mode rewrite the
  contents in place, so a value can jump while its address stays the
  same. Use edges from one frame to the next, and take a fresh baseline
  after a load.

The data comes from these files, which hold the layouts the rows rely
on: [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#competitions) (competition
and schedule ids), [`PARAM_DIR.md`](PARAM_DIR.md#schedule_listtbb-the-national-team-calendar)
(the national calendar), [`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md)
(the event, news and mail tables), [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#national-team-call-ups)
(national team call-ups) and [`GAME_FLOW.md`](GAME_FLOW.md#month-start-month-end-year-end)
(the order in which the scripts advance a turn, a month and a year).

## Contents

- [Calendar, season and turns](#calendar-season-and-turns): the date
  record, the schedule controller's mode and day counter, and the
  calendar rows.
- [Leagues, cups and honours](#leagues-cups-and-honours): your league
  and division, the tables, the honours board, club ranking and status,
  and the European qualification flags.
- [National teams and tournaments](#national-teams-and-tournaments):
  the national calendar, the call-up flags and the national cups.
- [Career records and cumulative counters](#career-records-and-cumulative-counters):
  titles, entries, streaks, the UEFA table and what the game does not
  keep as lifetime totals.
- [Events, mail and news flags](#events-mail-and-news-flags): the
  last-fired slots of events, news and mail, and the event scene
  variables.

The doc ends with its own "Still unknown" and "Checking the claims"
sections, after the five above.

## Calendar, season and turns

The game date is one 16-byte PlDate record inside block 0 of the
PlPwork save data. It holds the season's first year, the turn of the
season (0-95, 8 turns per month, starting in July) and the month. There
is no separate season-phase variable: the phase has to be derived from
the date, the schedule mode and the career year. The schedule
controller (CScheEuro) keeps its own day counter and a "date advance
pending" flag next to it.

All addresses are for the PAL release (`SLES_541.51`). Executable
address = file offset + 0xFF000. The Japanese build keeps the pwork
root elsewhere (`lui 0x39 / lw -0x36b8`, that is 0x38c948, per
`DOC/JAPANESE_RELEASE.md`), so this section is PAL only.

How known: every entry below was read from the executable's code
(confirmed) by a discoverer, two verifiers and a review pass that
re-read the code. Nothing was run in the emulator and nothing here was
seen in PCSX2. Anything the review could not settle is in
"Unconfirmed".

In the table, "block 0" means `*(*(0x3909a8)+0x1c) + *(*(0x3909a8)+0x28)`.
Block k is `*(*(0x3909a8)+0x1c) + *(*(0x3909a8)+0x28+4*k)`. The PlDate
sits at block 0 + 0x88.

| Address | Size | Type | Region | Name | Meaning and values | Label |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer | static | PlPworkTask pointer (P) | Root for all career save data. Written by `plPwork_CreatePwork` 0x21d628 (store at 0x21d65c), cleared by `plPwork_DeletePwork` 0x21d698 (0x21d6c8). Each has one caller: Create is called from `PwkCallbackCommand_Create` (0x1104b8), Delete from `PwkCallbackCommand_Delete` (0x110570). The only `Pwk.Create` script command is the first command of `ROOTMAINSEQ`, and the only `Pwk.Delete` is at the end of that script behind an unconditional branch back to the title. So P is non-zero from boot onward (logo, title, demo, VS, career) and never changes during a boot. `P != 0` is therefore not a career gate. `pwGet` 0x21da50 returns 0 only for k >= 0xb. For an absent block (offset word 0xffffffff) it returns the bare base `*(P+0x1c)` (the delay slot of the `beq` at 0x21da78 loads it). | confirmed (code and `sqb.py dis`) |
| P+0x1c | 4 | u32 pointer | heap | PlPwork data buffer base | Base of the data buffer, from `FcEuroMalloc` in heap block 6 (`SetHeapBlock(6)` at 0x21d830, store at 0x21d850). Fixed for the whole boot. The "ext-work" copy mechanism (P+0x18, P+0x20, P+0x24) is dead in retail: `prepareExtWork` 0x21d980 and `deleteExtWork` 0x21d9e0 have no caller, so `switchExtWork` 0x21da20 (called from SAVEPRG) returns 0 at 0x21da2c while P+0x20 is NULL, and P+0x18 stays 0. | confirmed |
| P+0x28 | 44 | 11 x u32 | heap | Block offset table | One offset per block (0..10), laid out by the constructor 0x21d6f0 in an order shuffled by `plUty_ShuffleUint8` 0x235270 (call at 0x21d774), as a running sum, 8-byte aligned, from the size table at 0x533ac8. The table is written once per boot, so it is stable within a boot, across new game, load and year rollover. Whether the order is the same on every boot is unresolved, so read the chain, never hard-code. 0xffffffff never occurs in retail (only block 8 can be absent, and only if P+0x19 is set; the only Create caller passes 0). Block 0 table size is 0x20e50 (usable 0x20e48, the table value includes an 8-byte trailer). | confirmed; cross-boot order unresolved |
| block 0 + 0x88 | 2 | u16 | heap | PlDate.year | The season's first year. 2006 means the first career season (2006-07, and it stays 2006 for January to June 2007). 2005 means the opening playoffs (new-game date 2005 turn 92 up to turn 95: `pwkGen_Init` 0x244220 calls 0x2441c8 with 0x7d5 and 0x5c) or VS mode (`pwkGen_InitVSDate` 0x244328: 2005 turn 95). `pwkGen_SetStartYear` 0x2442e8 sets 2006 turn 0. Career year (`pwkGen_Keika` 0x244430) = year - 2006. `pwkGen_Is3rdLeague` 0x2442c0 is true when year < 2006. Increments once, in `plMisc_GetLaterDay` 0x214788 when turn plus days reaches 96, called by `pwkGen_IncDay` 0x2443d0 (at 0x2443fc). | confirmed |
| block 0 + 0x8a | 1 | u8 | heap | PlDate.turn | Turn of the season, 0-95. 8 per month. 0 = first turn of July, 95 = last turn of June. Wraps 95 to 0 together with year+1. `plMisc_GetRemainDayOfYear` 0x214aa0 = 0x5f - turn. Written by `plMisc_SetTurn2Date` 0x214698 (`sb` at 0x2146c0). | confirmed |
| block 0 + 0x8b | 1 | u8 | heap | PlDate.month | Calendar month 1-12, from ((turn>>3)+6)%12+1 (`sb` at 0x21470c). Turns 0-7 give 7 (July), turns 88-95 give 6 (June). `ScheCallbackCommand_CheckSeasonStart` 0x114558 compares this byte with 7. | confirmed |
| block 0 + 0x8c | 4 | u32 | heap | PlDate turn in month | turn - (turn>>3)*8, 0-7 (`sw` at 0x2146e4). 7 is the last turn of the month; the month changes at the next turn start. `plMisc_GetRemainDayOfMonth` 0x214a90 = 7 - this value. `ScheCallbackCommand_TurnEnd` 0x1138d0 calls `pwkGen_GetRemainDayOfMonth` and picks "month continues" (arg 0) when the result is above 0 (`blez` at 0x1139c8) and "month end" (arg 1) otherwise. | confirmed |
| block 0 + 0x90 | 4 | u32 | heap | PlDate week | turn_in_month / 2, 0-3 (`sw` at 0x2146f4). The arithmetic is confirmed; the on-screen "Week N" naming is empirical (one save, `DOC/SAVE_FORMAT.md`). | arithmetic confirmed; naming empirical |
| block 0 + 0x94 | 4 | u32 | heap | PlDate weekend flag | turn_in_month - 2*(turn_in_month/2): 0 or 1 (`sw` at 0x2146fc). The label mapping (0 midweek, 1 weekend) is empirical (one save). | arithmetic confirmed; naming empirical |
| 0x390650 | 4 | u32 pointer | static | CScheEuro singleton | Non-zero while the schedule controller exists: created by `CreateScheEuro` 0x202a50 (store at 0x202b50), zeroed by `DeleteScheEuro` 0x202ba8 (only caller: `ScheCallbackCommand_Finalize` 0x113408). Object is 0x41c bytes in heap block 1. It exists for a career, the opening playoffs, VS mode and the title attract demo (`RootDemoMatchSeq` calls `Initialize_VsMode`, mode 0x406ab8), so it only means "schedule controller exists". Creators: `Initialize` 0x1132f8 and `InitializeContinue` 0x1133b0 (mode 0), `InitializeFirstCheck` 0x113350 (mode 1), `Initialize_VsMode` 0x1145e0 (mode 2). Mode argument: 1 = FirstPromote, 2 = VS, anything else = Normal (0x202a84 to 0x202a94). | confirmed |
| *(0x390650) + 8 | 4 | u32 pointer | heap | Schedule mode (vtable pointer) | 0x406c78 = normal career (CScheEuro_Normal). 0x406b98 = opening playoffs (CScheEuro_FirstPromote). 0x406ab8 = VS mode (CScheEuro_VS), which is also what the title attract demo uses. Written once in `CreateScheEuro` (`sw` at 0x202b4c). A second vtable word at +0x20 (0x406c28, 0x406b48, 0x406a68) is a valid key too: use one set consistently. | confirmed |
| *(0x390650) + 0x404 | 1 | u8 | heap | Competition-data load state | 0 = idle (also the initial value). 1 is stored at 0x20436c and 2 at 0x2043ac, both inside `acceptCompetitionDataLoading` 0x204330, so 1 is transient and practically unobservable. 2 = loads requested and in flight (lasts many frames). 3 = data ready (set by `AllLoadCompCB` 0x207170, or by `updateTurnStart` 0x203238 / 0x203274 directly when nothing needs loading, in which case it is consumed in the same call). `updateTurnStart` proceeds only on 3 and resets it to 0 (0x20328c). Getter at 0x2043d0 returns 1 (complete) for 0 or 3 and 0 (loading) for 1 or 2. | confirmed |
| *(0x390650) + 0x418 | 4 | u32 flag | heap | Date-advance-pending flag | Set to 1 by `updateTurnEnd` 0x203348 (store at 0x20336c) until the next `updateTurnStart` 0x203238 runs the sub-controller handler through vtable +0x34 (0x207228 Normal, 0x207410 FirstPromote, 0x207580 VS), which clears it. The handler calls `pwkGen_IncDay`; Normal calls `pwkGen_SetStartYear` (2006, turn 0) instead when year < 2006. Also set to 1 by `isFinishedInitialize` 0x203120 (store at 0x20321c) once initialisation is done, and zeroed by `initialize` 0x203030 (0x203064). The same offset applies to all three modes because the vtable this-adjust halfword (+0x30) is 0 in all three. So the PlDate lags: during end-of-turn screens, MonthEnd and YearEnd it still shows the finished turn (code path only). | confirmed from code; the lag is not seen running |
| schedule day counter: block 5 + 0x467a8 (alt: `*(*(*(*(0x390650)+0)+4)+0)+8`) | 4 | s32 | heap | Schedule day counter | The schedule controller's own turn index of the year. Field +8 of the `PlRec_ScheCtrlStatusSave` record in block 5 (record at block 5 + 0x467a0, from `pwkRec_GetScheCtrlStatusSave` 0x2536c0). +1 in `ScheduleControllerBaseSystem::updateTurnEnd` 0x2d99f8 (previous value copied to +0xc first). Set to 0 by `updateYearStart` 0x2d9a50. `getNowDay` 0x2d9e28 returns -1 when it equals 0xff. `InitStatus` 0x2d9a70 rewrites the record only when its fourth argument is non-zero (the `beqz $a3` at 0x2d9a8c skips the write): +0 = 2, +4 = -1, +0xc = 0, +8 = the value passed at the three sub-controller initialize call sites (0x207204: -1 Normal; 0x2073ec: 0x5d (93) FirstPromote; 0x20753c: 0 VS). That argument is `(CScheEuro+0x408 == 0)` (`sltiu` at 0x207200, 0x2073e8, 0x207538). `initialize` 0x203030 stores its argument into +0x408 (0x203050) before the sub-controller init runs, `Initialize` and `InitializeFirstCheck` pass 0 (record rewritten), `InitializeContinue` passes 1 (record kept as saved). So the counter is rewritten on new game, opening playoffs and VS, and restored from the save on Continue. -1 means "not initialised" (a new Normal career before its first turn end). | confirmed |
| block 6 + turn*0x48 | 0x48 per row, 96 rows | array of records | heap | Calendar day records | 96 rows of 0x48 bytes at the start of block 6 (0x1b00 bytes; camp records follow at +0x1b00), indexed by PlDate turn (`plClubEvent_GetEvent` 0x20e9b8 reads the turn byte times 0x48). +0 u8 state: 0xff empty, 3 scheduled (`CB_EntryPlan` 0x208108, `sb` at 0x20817c, only when the game is not over), 1 played (`CB_SetResult` 0x208298, 0x208344, when the game is over). +4 s32: schedule group UID (PLSCHE_GROUP, 0..163, not a compe id 0..71) of the competition your club plays that turn, -1 for none; `CB_EntryPlan` stores byte 3 of the group record at 0x208160 and passes row+4 to `getRegulationFromUID` at 0x20818c; several rows can share a value. +0x38 u16: club-event number, 0xffff for none. `ScheCallbackCommand_TurnEnd` 0x1138d0 sets +4 to -1 and +0x38 to 0xffff on later rows (turn+1 to 95) whose +4 equals your UID, only when the UID is not -1, the competition is not finished and your team has no games left in it (`isRemainGameTeam` is 0). `_ScheClear` 0x2552e8 (from `pwkSche_Init` 0x2553b0 and `pwkSche_UpdateAnnualy` 0x255408) resets every row (+0 = 0xff, +4 = -1, +0x38 = 0xffff, +0x26 = 0, +0x40 = 0) at career start and at each season start. | confirmed; field meanings of other bytes unconfirmed |

### Pointer chains and stability

Every heap or overlay entry above, with its root, offsets, validity and
stability. Stability here is derived from the code, not from watching
the game.

| Entry | Root and offsets | Valid when | Stable across |
|---|---|---|---|
| PlPworkTask P | static u32 at 0x3909a8 | Non-zero from the first command of `ROOTMAINSEQ` (`Pwk.Create`) onward. A zero means the boot has not reached `Pwk.Create` yet. It says nothing about a career. | Constant for the whole boot: new game, load, demo, VS, matches, year rollover and return to title do not re-create it. P is a heap object (0x5c bytes). Its address after a reboot is not measured. |
| block 0 | `*(P+0x1c) + *(P+0x28)` | After `Pwk.Create`. The contents are blank until a new game or load fills them. | Offsets are written only by the constructor, so the address is fixed for the boot. Whether it is the same on the next boot is unresolved (shuffle seed). |
| PlDate year, turn, month, turn in month, week, weekend flag | block 0 + 0x88 (+0 u16, +2 u8, +3 u8, +4 u32, +8 u32, +0xc u32) | A career, the opening playoffs or a VS or demo Sche has initialised block 0 (`pwkGen_Init` memsets block 0, then sets 2005 turn 92). Sanity test: year in 2005..2100, turn <= 95, month 1-12. Not proof of a career on its own (`InitVSDate` sets a dummy 2005 turn 95, and the demo also overwrites block 0 in place). | Frames, screens, menus and matches. Written once per turn advance (`pwkGen_IncDay`), plus new-game init, VS init and save load. Year changes at most once per 96 turns. |
| CScheEuro object | static u32 at 0x390650 | `u32[0x390650] != 0` and an EE heap address (0x100000..0x1FFFFFF). Zero at boot, logo and idle title. Also non-zero during the title attract demo (mode 0x406ab8). | The address 0x390650 is fixed. The object (0x41c bytes, heap block 1) lives from Create to Finalize and can have a different address on the next creation. A new game creates it twice (FirstCheck mode 1, Finalize, then Initialize mode 0). |
| Schedule mode | `*(0x390650) + 8` | CScheEuro exists. Test the root for non-zero first. | Constant for the object's whole life. Changes only after the object is deleted and re-created. |
| Load state | `*(0x390650) + 0x404` | CScheEuro exists. Only meaningful around turn starts, otherwise 0. | Stable (0) between turns. Value 2 can last many frames while schedule files stream in. Live value, not a save copy. |
| Date-advance-pending flag | `*(0x390650) + 0x418` | CScheEuro exists and initialisation has finished. Before `initialize` the word is uninitialised heap (the constructor 0x202c08 does not clear it). | Toggles at every turn end and turn start; 0 to 1 to 0 can happen within a few frames. Same offset for Normal, FirstPromote and VS. Not serialised as far as checked. |
| Schedule day counter | `block 5 + 0x467a8`, where block 5 = `*(P+0x1c) + *(P+0x28+4*5)` (P+0x3c). Alt: `*(*(*(*(0x390650)+0)+4)+0)+8` (CScheEuro+0 is the ScheduleControllerBaseSystem, base+4 a 0x40c-byte status block, status+0 the save-record pointer, 0x2d98b8). | Career or league sim running. For the alt chain, CScheEuro exists and `isFinishedInitialize` 0x203120 has returned true; null-check every hop. Ignore -1. Not meaningful in match-only or VS context unless the VS CScheEuro is running. | Changes only at turn end and year start. Rewritten at CScheEuro creation by Initialize or InitializeFirstCheck (+0x408 == 0). Kept as saved on Continue. |
| Calendar day records | block 6 = `*(P+0x1c) + *(P+0x28+4*6)` (P+0x40); row address = block 6 + turn*0x48; turn = PlDate +2 | Career loaded. Rows are empty until the year's schedule is built. Career mode only. | Block address constant for the boot. Past rows keep their values; later rows are cleared at turn end under the condition above; every row is wiped at each season start by `_ScheClear` 0x2552e8. Live, written in place. The block is larger than 0x1b00 (`pwkSche_Init` also zeroes 32 bytes at +0x1cc0). |

### Timing and rollover

All of this is read from the code (confirmed in the code, not watched in
the emulator).

- The date advances at the start of the next turn, not at turn end.
  `CScheEuro::updateTurnEnd` 0x203348 sets CScheEuro+0x418 to 1. The
  next `updateTurnStart` 0x203238 calls the sub-controller handler
  through vtable +0x34, which runs `pwkGen_IncDay` and clears the flag.
  That only happens when the load-state byte at +0x404 is 3.
- The schedule day counter increments earlier, in
  `ScheduleControllerBaseSystem::updateTurnEnd` 0x2d99f8. It resets to 0
  in `updateYearStart` 0x2d9a50.
- A season rollover is the PlDate year increasing (turn going 95 to 0),
  seen at the first turn start of the new season. During YearEnd, the
  YearEnd report and the YearStart sequence the PlDate should still read
  turn 95 of the old year (derived, not traced in script order).
- Month end: `ScheCallbackCommand_TurnEnd` 0x1138d0 chooses MonthEnd when
  `pwkGen_GetRemainDayOfMonth` is 0 or less, that is turn in month = 7.
  Year end is turn 95. The TurnEnd check only runs when your competition
  still has games remaining.
- Absolute turn counter: `plMisc_PlDate2TotalTurn` 0x214d08 uses
  year-2006 for months above 6 and year-2005 for months up to 6, which
  gives (year-2006)*96 + 56 + turn for the game's own total.
  (year-2006)*96 + turn differs from it by the constant 56.
- Phase by month: turns 88-95 are June, where the national cups sit
  (`DOC/LMASTER_MOD.md`). This is derived from the docs, not from a
  phase variable.
- Detecting a new career year: year - 2006 is the number of seasons
  completed (valid only when year >= 2006). A year below 2006 means the
  opening playoffs (`pwkGen_Is3rdLeague`). A year decrease means a load
  or a new game, not a rollover. P does not change in either case (see
  the P row), so P cannot be used to detect them.
- Reset points for the schedule calendar: `pwkSche_UpdateAnnualy`
  0x255408 clears every calendar row at each season start.

### RetroAchievements notes

- Resolve the chain on every read: `P = u32[0x3909a8]`,
  `base = u32[P+0x1c]`, `off0 = u32[P+0x28]`. In RA terms this is an
  indirect read chain (AddAddress pointer, add offset, read). The code
  never moves these inside a boot, so re-reading is defensive. Do not
  hard-code the block 0 address: the block order is shuffled once per
  boot and whether it matches between boots is not settled.
- `P != 0` is not a career gate. Use a sane date (year 2005..2100,
  turn <= 95, month 1-12) together with `u32[0x390650] != 0`, which says
  the schedule controller exists.
- To tell a career from the opening playoffs or VS mode, pair the date
  with the mode word `u32[*(0x390650)+8]`: 0x406c78 career, 0x406b98
  opening playoffs, 0x406ab8 VS. The title attract demo also reads
  0x406ab8, so 0x406ab8 does not mean the player started a VS game. The
  CScheEuro pointer alone cannot distinguish them, and the date alone
  does not prove a career (VS init sets 2005 turn 95).
- Season rollover trigger: compare the year (u16 at block 0 + 0x88) with
  its previous-frame value (Delta) and require it to have increased by
  1, or the turn byte (+0x8a) going from 95 to 0. A year decrease means
  a load or a new game, not a rollover. Poll every frame.
- Timing pitfall: the date lags. It still shows the finished turn (turn
  95 of the old year) until the next turn start, so do not score a
  rollover while CScheEuro+0x418 is 1. Wait for the flag to fall back to
  0 and then read the new date. That flag is also 1 after initialisation
  (until the first turn start), so it is 1 on a fresh career or load
  before any turn has ended.
- The 0 to 1 to 0 toggle of +0x418 can pass within a few frames, so an
  achievement should not rely on seeing the 1 state. Use the edge of the
  date value instead.
- The schedule day counter is an alternative cursor: a drop to 0 marks
  YearStart. Use a signed 32-bit read and ignore -1. After a new game it
  starts from the value of its sub-controller (-1 Normal, 93 opening
  playoffs, 0 VS). After Continue it is restored from the save, so it
  should follow the career, but it was not compared with the PlDate turn
  after a mid-season load.
- Use deltas, not a fixed origin. The new-game date is 2005 turn 92
  (opening playoffs, one-time `pwkGen_Init`), `SetStartYear` gives 2006
  turn 0, and VS mode gives 2005 turn 95. `DOC/SAVE_FORMAT.md` shows a
  different example year (2019) in its PlDate table, which is an example
  from a save, not the PAL career start.
- "Match this turn" checks: read the calendar record row [turn] +4 and
  test it against -1, and use +0 as the state byte. Trust it for today's
  row and past rows only. Do not count future rows as the fixture list
  until a save state shows them.
- Month-end checks: turn in month == 7 is the last turn of a month.
  (turn in month == 7 and month == 6) is the same as turn byte == 95
  (the final month end). The turn byte is cheaper (one 8-bit read).
- Lightweight reads: the turn (u8) and month (u8) are single-byte reads
  from the same chain and are enough for most conditions.

### Unconfirmed

Do not rely on these. Nothing was refuted outright, but each was
left unverified or disputed.

| Claim | Reason |
|---|---|
| The shuffled block order (and so every block address) is identical on every boot | `plUty_ShuffleUint8` draws from the generator state at 0x569dc0, which `fcEuroRand_Init` 0x111698 starts at the constant 0x12345678, and `Pwk.Create` is the first script command. Other draws on that state between Init and Create were not enumerated and no run was observed. Do not hard-code offsets. |
| Block 8 reads | Retail never has an absent block 8, but block 8 is only 1 usable byte and was not otherwise checked. Do not read it without more checking. |
| Date table example year 2019 in `DOC/SAVE_FORMAT.md` | An example from a save. The code's start year is 2006. |
| The date advancing before the YearStart screens run, in real script order | Code-derived only. Not watched in the emulator. The callers of `pwkGen_IncDay` in the turn loop were not traced. |
| The schedule day counter "leads the PlDate by one between TurnEnd and the next TurnStart" and "reads 96 after the last turn end" | Only the +1 at turn end and the reset to 0 at year start are confirmed. No code reading 96 was traced. |
| The schedule day counter equals the PlDate turn after a mid-season load | On Continue the saved record is kept (`InitializeContinue` passes 1), but nothing was found that compares it with the PlDate, so equality is not shown. |
| Calendar rows for future days | The code that fills future rows' +4 was not found; `pwkSche_SetCaleMatch` 0x255548 is a stub. |
| Calendar row +0xc "holds the turn byte" | Not re-checked in the review. |
| Calendar row +0x30 "event success bonus" | Nothing found writes it. A 64-bit load at 0x20ea68 is tested for > 0, so width and meaning are unknown. The source was `DOC/ECONOMY.md` only. |
| Calendar row +0x26 flag bits | Bits 1, 2, 4 and 8 are set in various branches; their meaning is unverified. |
| Week and weekend naming ("Week N Midweek/Weekend") | Empirical, one save in `DOC/SAVE_FORMAT.md`. The code proves only the arithmetic. |
| "Turns 88-95 hold the national cups" | From `DOC/LMASTER_MOD.md`; not checked in the code. |
| Whether the attract demo's own `Sche.Finalize` runs when the demo is cancelled by a button | Not traced. It decides whether 0x390650 can stay non-zero on the title after a cancelled demo. |

### Still unknown

- Does the PlDate really still show turn 95 of the old year through
  MonthEnd, YearEnd, the save and the YearStart screens, and change only
  at the next TurnStart? This follows from the code but the order
  against `RootMainSeq` was not watched in PCSX2.
- How the retail game goes from the playoff date (2005 turn 92 + n;
  `FirstPromote` uses plain `IncDay`) to 2006 turn 0 (`Normal`'s handler
  0x207228 calls `pwkGen_SetStartYear` when year < 2006), and how the
  LMASTER third-tier career (tested in 2005-06 at turn 81-82 per
  `DOC/SAVE_FORMAT.md`) avoids a reset. Not traced.
- Where the record pointer given to `initialize` 0x2d9850 comes from.
  The sub-controller init (for example 0x2071c0) takes it from
  `ScheEuro_Memory::getScheduleCtrlSystemData` 0x2095d0, and
  `pwkRec_GetScheCtrlStatusSave` returns block 5 + 0x467a0, but the link
  between the two was not read.
- Where `Sche.YearEnd`'s result goes. `ScheCallbackCommand_YearEnd`
  0x113668 returns only 0 or 1 to the script (1 when
  `jmSche_CheckLeagueBottom`, an overlay function, is non-zero, the
  relegation check). What that function tests is unknown.
- No explicit season-phase variable (pre-season, regular, playoffs,
  off-season) was found. The competition-level phase (league match days,
  cup rounds, the current UID) lives in the schedule group status
  (`getCurrentUID` 0x2da428, `getCurrentGameIndex` 0x2da118), whose
  save-block location was not resolved.
- Whether `DeleteScheEuro` runs on a return to the title or after game
  over (only the call in `ScheCallbackCommand_Finalize` 0x113408 is
  known; the script Finalize sites are in `RootMainSeq`, `RootClubEditSeq`,
  `RootVsModeSeq` and `RootDemoMatchSeq`).
- Whether the shuffled block offsets and base are the same on every boot
  (see Unconfirmed). Within a boot they are fixed.
- What fills calendar record +4 for future days (`calcMyJoinCompetition`
  0x205948 and the calendar writers were not traced), and whether every
  row holds -1 before the calendar is built.
- Whether the Japanese build has the same field offsets (+0x88, +0x418,
  +0x404): `python SRC/gamever.py check ISO_JP` covers addresses, not
  these field offsets. Block 5's full layout around +0x467a0 and the
  block-size table at 0x533ac8 are not decoded here.
- Nothing was run in the emulator, so every value range above is from
  code only.

### Checking the claims

Run from the repo root. The `sqb.py` scan can take about a minute.

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB | grep -i "Pwk\.\(Create\|Delete\)"
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 14
python SRC/sles_disasm.py ISO/SLES_541.51 dis plMisc_SetTurn2Date
python SRC/sles_disasm.py ISO/SLES_541.51 dis plMisc_GetLaterDay
python SRC/sles_disasm.py ISO/SLES_541.51 dis CreateScheEuro
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x203030 12
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x2d9a70 12
```

What each shows:

- `plPwork_CreatePwork` stores the new object at 0x3909a8 (`lui 0x39`,
  `sw ... 0x9a8`).
- The script scan lists `Pwk.Create` at 0x0010 (first command) and
  `Pwk.Delete` only at 0x1a20.
- `pwGet` at 0x21da50: `slti 0xb` returns 0 for k >= 0xb, and the
  `beq` at 0x21da78 has `lw 0x1c($a2)` in its delay slot (bare base for
  an absent block).
- `plMisc_SetTurn2Date` writes the year (`sh`), turn (`sb` 2), turn in
  month (`sw` 4), week (`sw` 8), parity (`sw` 0xc) and month (`sb` 3).
- `plMisc_GetLaterDay` compares turn plus days with 0x60 and adds 1 to
  the year.
- `CreateScheEuro` stores the mode words and the singleton
  (`sw ... 8($s0)` at 0x202b4c, `sw $s0, 0x650($s1)` at 0x202b50).
- `initialize` 0x203030 stores its argument into +0x408 (0x203050) and
  zeroes +0x418 (0x203064).
- `InitStatus` 0x2d9a70 skips the record write when `$a3` is zero
  (`beqz` at 0x2d9a8c).

## Leagues, cups and honours

This part of memory holds the career state for competitions: which
league your club plays in, the tables, the cup and league results, the
honours board, the club ranking and the European qualification flags.
Almost all of it is heap data in the PAL release (`SLES_541.51`),
reached from one static root word at 0x3909a8. A second static root at
0x390650 points to the schedule system, which exists only while a
schedule is loaded. Nothing here was run in an emulator: every entry is
**confirmed** from the game code by disassembly unless a row says
otherwise. Statements about the running game are read from the code,
not seen in PCSX2, except where a row cites a test recorded in a `DOC/`
file.

Notation: P = u32 at 0x3909a8. Bk = save block k = u32[P+0x1c] +
u32[P+0x28+4k] (k 0 to 10). B0 is the general block, B1 your club, B2
other clubs, B3 leagues, B5 records, honours and schedule state. "Team
1" is your club. Competition ids (compe) are the PLSCHE_COMPE numbers of
`SCHEDULE_FORMAT.md`; schedule UIDs are a different numbering. The
Japanese release was not checked: `JAPANESE_RELEASE.md` says the
plPwork_GetPwork global differs there, so the root is not 0x3909a8.

Lifetime in one paragraph. P is created once, by Pwk.Create, the first
real command of ROOTMAINSEQ, and its delete command is unreachable. So P
is non-zero from boot through the logo, title, demo, VS mode, menus,
matches and career, and P and every block base stay fixed for the whole
boot. The block contents are blank until New Game or Continue fills
them. The attract demo and VS mode also run Pwk.NewGame in place, so
the blocks hold demo or VS data while the schedule object is in VS mode
(S+8 = 0x406ab8, see the row for 0x390650). P != 0 therefore says
nothing about a career: use the schedule object or the date.

### Memory map

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer to PlPworkTask (heap, 0x5c bytes); then u32 data base at P+0x1c and per-block u32 offsets at P+0x28+4k (k 0 to 10) | static | pwork root and block base | Root of all career data. P is stored by plPwork_CreatePwork 0x21d628 (only caller 0x1104b8, inside PwkCallbackCommand_Create) and cleared by plPwork_DeletePwork 0x21d698 (only caller 0x110570). Pwk.Create is the first real command of ROOTMAINSEQ (script offset 0x10); Pwk.Delete (offset 0x1a20) sits behind an unconditional branch back to the title and is unreachable. So P is non-zero from boot, and P, [P+0x1c] and every [P+0x28+4k] are constant for the whole boot. Re-reading the chain each frame is only defensive. The getter plPwork_GetPwork 0x21d6e0 is `lui 0x39; lw 0x9a8`. Block offsets are shuffled once, in the PlPworkTask constructor 0x21d6f0 (plUty_ShuffleUint8 0x235270). Block 8 reads as null only when byte [P+0x19] is set, which retail never does. The ext-work copy (byte [P+0x18], prepareExtWork 0x21d980) has no caller in the executable or any overlay, so [P+0x18] stays 0 and [P+0x1c] never changes. | confirmed (jal scan for the two callers; script dump of ROOTMAINSEQ). Nexxus's save-state test of 2026-10-27 in `SAVE_FORMAT.md` (LMASTER max build) read the blocks through this chain |
| B0+0x88 | 16 | struct {u16 year; u8 turn; u8 month; s32 turn_in_month; s32 week; s32 weekhalf} | heap | game date (PlDate) | Year is the season's first year (2006 for 2006-07, unchanged January to June, increments when turn wraps 95 to 0 in July). turn +2: 0 to 95, 8 per month, 0 = July. month +3: 1 to 12, = ((turn>>3)+6)%12+1. +4 is the turn in the month (0 to 7), not a calendar day. +8 week (0 to 3, = +4 / 2). +0xc weekhalf (0 midweek, 1 weekend, = +4 parity). Season index = year - 2006 (pwkGen_Keika 0x244430). New Game starts at 2005 turn 92 (June 2005, the opening playoffs); the first real season is 2006 turn 0, so the index is -1 during the opening playoffs and 0 for the whole first season 2006-07. B0 = [P+0x1c]+[P+0x28]; the block is blank until New Game or Continue. | confirmed: plMisc_SetTurn2Date 0x214698, pwkGen_GetDate 0x244368 (copies 0x10 bytes from B0+0x88), pwkGen_Init 0x244220 (0x2441c8 sets 2005 turn 92), pwkGen_SetStartYear 0x2442e8 (2006 turn 0), plMisc_GetLaterDay 0x214788 (year +1 only on the 95 to 0 wrap) |
| B3+0x0 | 4 | s32 myleague | heap | my league | 0 to 5 = England, France, Germany, Italy, Spain, Netherlands. Nation number = league + 1 (table 0x531d40). Written only by pwkLg_Init 0x246218 (store at 0x246248), at career creation or when a save restores the block. It does not change at the year end: pwkLg_SetMyCompe 0x2462e0 changes only +4 and refuses a move to another league. Getter pwkLg_GetMyLeague 0x2462a8. The block is zeroed before a career, so 0 is ambiguous with England. B3 = [P+0x1c]+[P+0x34]. | confirmed: pwkLg_Init is the only setter in the pwkLg_ group (no SetMyLeague symbol) |
| B3+0x4 | 4 | s32 mycompe | heap | my competition (division) | Your division's compe id. First divisions 0, 6, 11, 16, 22, 27; second divisions 1, 7, 12, 17, 23, 28 (England, France, Germany, Italy, Spain, Netherlands). pwkLg_Init stores plMisc_LeagueDiv2Compe(league, 1) (0x24624c to 0x246254), so a new career starts in the second division: 1, 7, 12, 17, 23 or 28. It reaches a first-division id (0, 6, 11, 16, 22, 27) only by promotion at a year end. pwkLg_SetMyCompe 0x2462e0 stores only when plMisc_Compe2League of the old and the new id are equal; the call found is at SIMPRG.REL 0x150f6c. Getter pwkLg_GetMyCompe 0x246350. pwkLg_Init then enters teams 1 and 2 into division 1 (plLg_EntryTeamToDiv, 0x24626c, 0x24627c). | confirmed. Table 0x531d40 read from the file: rows {nation, league, div0 compe, div1 compe} = {1,0,0,1}, {2,1,6,7}, {3,2,11,12}, {4,3,16,17}, {5,4,22,23}, {6,5,27,28}; the loop at 0x215d48 returns the div1 word for a second argument of 1 |
| B5+0xb50c4 | 2 | u16 | heap | previous world club ranking position | Your world ranking position saved before the latest ranking update (setter pwkRec_SetOldWorldClubRank_TeamUserOnly 0x254f18 is a `sh` at +0; getter pwkRec_GetOldWorldClubRank_TeamUserOnly 0x254f50). The old value is read from your record and saved at SIMPRG.REL 0x150700 to 0x150708, before the update at 0x1522c0. | confirmed; the record pointer function 0x254c00 returns B5+0xb50c4 |
| B5+0xb50c6 | 1 | u8 bit flags: 0x1 EU MVP, 0x2 European League, 0x4 European Club Cup, 0x8 International Club Cup | heap | European competition qualification flags | Whether your club is entered in each European competition. Bits 0x2, 0x4, 0x8 are cleared (0x113440 to 0x113450) and recomputed at the year end by the function at 0x113428, called from ScheCallbackCommand_YearEnd 0x113668 at 0x1136d8 only when ClubRank::UpdateYearEnd returns non-zero. It finds team id 1 in the first 10 slots of the nation's make list and maps (rank-1)*10+slot through the byte table at 0x51ada0: values 1, 2, 3 set European League, European Club Cup, International Club Cup (0x1135a8, 0x1135b8, 0x1135c8). CheckEuroCompeEntry 0x254e08 masks 0xe. Bit 0x1 (EU MVP) is not cleared there and its setter (0x254e38) has no caller in the executable. The init at 0x254c48 zeroes the byte, so it reads 0 before the first year end of a new career. | confirmed; setters 0x254c88 (bit 2), 0x254d08 (bit 4), 0x254d88 (bit 8), 0x254e38 (bit 1). The bit names come from symbol abbreviations |
| B5+0xb50c8 | 4 | s32 PlRec_DivShift: 0 none, 1 promoted, 2 relegated | heap | year-end division shift | Reset to 0 at SIMPRG.REL 0x150ecc, then set to 1 (new division index < old, at 0x150f4c) or 2 (old < new, at 0x150f64). Equal divisions leave 0. Value 3 exists in the enum but is never written by the code found. Holds until the next year end. Read by SIMPRG.REL 0x162328 and 0x162698 as ==1 (promotion popularity bonus, `ECONOMY.md`). A further 3 bytes at B5+0xb50cc are the unused div_shift_count. | confirmed; accessors 0x254eb8 (set, a `sw` at +4) and 0x254ef0 (check, `lw`); the init at 0x254c48 zeroes it |
| B5+0x260+0x98*compe | 152 (0x98) | struct: u16 times held +0; u16 titles won by your club +2; u16 times your club entered +4; u8 your last final place (1-based, 0 = not in it) +6; u32[32] last season's final order (team ids, position 0 = champion) +8..+0x87; PlDate of your first title +0x88 | heap | per-competition record (compe 0 to 48) | Persistent honours per competition, written once per finished competition by calcCompetetionFinish 0x205f40 (called from CScheEuro::updateTurnEnd 0x2033ec, guarded by the isSavedResult flag). +0 is incremented per finish. +2 is the trophy counter (rises when your rank is 0). +4 counts your entries. +6 = rank+1 (0 if you are not in the list). The order words +8+4*pos (pos < 0x20) are written by pwkRec_SetPastRecordLastTeamOne 0x2535f0. The PlDate at +0x88 is copied when +2 becomes exactly 1. Competitions with compe >= 49 are refused by pwkRec_GetCompePastRecord 0x253590 (it accepts compe < 0x31). The function returns early unless the year-schedule byte +7 is 1 (meaning not traced). Compe 34 (0x22) also writes compe 33's +4 and +6 (0x2061e0 to 0x2061f8). Compe 29 and 36 take special branches. | confirmed; HaveVictory 0x253dd0 reads +2 (+0x262 from the pointer), HaveEntry 0x253d98 reads +4 (+0x264) |
| B5+0x31cf4+0x1fc8*i (i 0 to 9, 0 = latest) | 8136 (0x1fc8) | per-season record: champion {u32 team id, u8 your final place 1-based or 0} at +8*c (c 0 to 48); s16 season index at +0x188+2*c; best eleven 11x12 bytes at +0x1ec+0x84*c; MVP 12 bytes at +0x1b30+0xc*c; top scorer 12 bytes at +0x1d7c+0xc*c | heap | yearly honours history (10 seasons) | The honours board. Record 0 is the most recent finished edition of each competition. ShiftCompeConventionRecord 0x253c58 copies record i-1 to i from 9 down to 1 (oldest dropped) and is called before the entry-team check. Champion team id 1 means your club won. The season index written is pwkGen_Keika (year - 2006) with a `sh`, and the reader at SIMPRG.REL 0x152108 loads it with `lh`, so read it as a signed 16-bit value (-1 is possible, see the date row). If a competition has no entry teams the shift happens but record 0 is not rewritten, so record 0 can duplicate record 1 (stale). Best eleven, MVP and goal-king contents were only partly checked. Retail covers compe 0 to 48 only (compe < 0x31 in the Keikayear getter 0x253b38). | confirmed; getters 0x253a90 (record, i < 10), 0x253af8 (champion), 0x253b38 (season), 0x253b80, 0x253bc8, 0x253c10; champion written at 0x206370 to 0x206378 |
| B1+0x4b4+0x41f4 = B1+0x46a8 | 4 | s32 | heap | my club's main league UID | Schedule UID of the league your club is entered in this season (-1 = none; 0 is a valid UID, England first division). Written by SIMPRG.REL 0x151f10 (a `sw` at 0x41f4 on pwkTeam_GetMyTeamData for team 1), called from 0x150a80 for each entered club. Reader plTeam_GetTeamMainLeague 0x22bf00. Other clubs: B2+0xa8*idx+0x9c with idx = team - 2 (pwkOteam_Team2Otindex 0x24b7e8). Does not change during a match. The evidence call at 0x206400 uses team 2, not your club. | confirmed. B1 = [P+0x1c]+[P+0x2c]; pwkTeam_GetMyTeamData 0x259898 = B1+0x4b4 |
| B1+0x4b4+0x41f8 | 1 | u8 club_rank (0 to 31) | heap | my club rank | Club rank shown on the club Information screen. For team 1 it is not written by the SIMPRG ranking (loop at 0x151938 skips teams 1 and 2). It is set from the hidden status by 0x26dd40 (stores sb at B1+0x46ac = min(31, status >> 11)), after each match and at year end. Other clubs: B2+0xa8*idx+0xa0. Reader 0x24bec8 (lbu 0x41f8). | confirmed |
| B1+0x4b4+0x41fa | 2 | u16 | heap | my club world rank points | Points rewritten for all clubs in one burst by the SIMPRG ranking pass (setter 0x151f78, a `sh` at 0x41fa for team 1; getter at 0x151fc0 is an `lhu`). Other clubs: B2+0xa8*idx+0xa2. The 0 to 1023 range is not verified. | confirmed. The three fields are separate reads; +0x41f9 is unused padding |
| B1+0x4b4+0x41fc | 2 | u16 | heap | my club world ranking position | 1 = best, 441 clubs, 0 = not yet ranked. Written by 0x152060 (a `sh` at 0x41fc) after a qsort of all 441 records (comparator 0x150848; the tie order is unstable). The old value is saved to B5+0xb50c4 before the update (SIMPRG.REL 0x150700 to 0x150708). Reader pwkOteam_GetWorldClubRank 0x24bf70 (`lhu`). Other clubs: B2+0xa8*idx+0xa4. | confirmed. When in the season the ranking task runs is not traced |
| B1+0x11264 | 4 | s32 status rank (0 to 8; new career 7) | heap | club status rank | Index into the cap table at 0x555150 (u16 caps by rank 0 to 8: 65535, 60000, 55000, 40000, 30000, 25000, 10000, 7000, 7000). StatusChangeRank 0x26dc50 only stores when the new value is numerically smaller, so the rank index only falls as status improves. StatusInit 0x26e328 stores 7 (at 0x26e364). The year-end routine 0x26e2a0 calls StatusChangeRank(5) after a promotion. | confirmed; StatusChange 0x26dbb8; cap table values read from the file |
| B1+0x1126a | 2 | u16 status points (capped by the status rank) | heap | club status (hidden reputation points) | Hidden status of your club. Not shown in game. It moves after each match (GameCheck 0x26ddd8), at final places in competitions (MatchGameCheck 0x26dfa8, called from calcCompetetionFinish 0x2063a4) and by +500 at the year end (YearEndCheck 0x26e2a0 loads the float 500.0 and calls StatusChange). StatusChange clamps it to 0 below and to cap[rank] above (0x26dbb8). A new career starts at rank 7 with cap 7000, so a threshold of 40,000 is reachable only after the rank has dropped to 3 or lower. The two fields are not adjacent (2 bytes at +0x11268 lie between them): read them separately. Reader pwkTeam_Status 0x26e2f0 (`lhu` 0x126a). | confirmed. The "club rank 24+ = World-class" label was not verified |
| 0x390650 | 4 | u32 pointer to CScheEuro (0x41c bytes, heap block 1); +8 mode word; +0x20 second mode word; D = u32[S+0x414] | static | schedule system object: alive and mode | Non-zero only between CreateScheEuro 0x202a50 (store at 0x202b50) and DeleteScheEuro 0x202ba8 (only caller Sche.Finalize 0x113408). It is 0 at boot, on the logo, and on the title while idle. It is non-zero in the opening playoffs of a new game (mode 1), in a normal career (mode 0) and in VS mode and the title attract demo (mode 2, both create the VS-mode object). The word at S+8 is a vtable-like pointer: 0x406c78 normal career (mode 0), 0x406b98 first-promote check, the opening playoffs (mode 1), 0x406ab8 VS mode and the attract demo (mode 2); the store is at 0x202b4c. S+0x20 holds a second set (0x406c28, 0x406b48, 0x406a68); use one set consistently. Compare with those constants, not as a small enum. So S+8 == 0x406ab8 does not mean the player chose VS mode: the demo sets it too. GetScheEuro 0x202bf8 reads the root. | confirmed (script offsets: Sche.Initialize in ROOTMAINSEQ 0xc30, InitializeFirstCheck in ROOTCLUBEDITSEQ 0x8c0, Initialize_VsMode in ROOTVSMODESEQ 0xa8 and ROOTDEMOMATCHSEQ 0xa8) |
| D+0x28c (D = [S+0x414]) | 4 | s32 compe | heap | competition id of your match this turn | -1 when you have no match this turn. Set in calcMyJoinCompetition 0x205948 (store at 0x205ab0, only when a user-entered UID has matches today), called from updateTurnStart 0x203238 (call at 0x2032b8). Reset to -1 by deleteGameList_MyJoinCompetition 0x205868 (stores at 0x2058d0, 0x2058d8) at the start of every updateTurnEnd (0x203368). Accessor getCompeID_MyJoinCompetition 0x202df8. The example id 34 (European League group) was not verified. | confirmed |
| D+0x290 | 4 | s32 UID | heap | schedule UID of your match this turn | -1 when you have no match. Same writers as D+0x28c (store at 0x205ab8). Accessor 0x202e08. | confirmed |
| D+0x280 | 4 | s32 | heap | total of today's matches | Total of today's matches across all UIDs sharing that competition id (not a count of competitions). 0 when you have no match. Accessor getGameListNum_MyJoinCompetition 0x202da8. | confirmed |
| D+0x288 | 4 | s32 | heap | today's match count for your UID | 0 when you have no match. Accessor getGameListNum_MyJoin 0x202dc8. | confirmed |
| D+0x29c, D+0x2a0 | 4 each | s32 nation, s32 division | heap | nation and division snapshot | Stored once in CScheEuro::initialize 0x203030 (0x203070, 0x203080) from pwkLg_GetMyNati and pwkLg_GetMyDiv. They are snapshots, not live, and can be stale after a promotion. Do not use them as the current nation or division. | confirmed |
| B5+0x467a0 | 24 (0x18) | ScheCtrlStatusSave: s32 ctrlStatus +0; s32 nowGroup +4 (slot index, -1 none); s32 nowDay +8 (current turn, none = -1 or 0xff); s32 prevDay +0xc; s32 day_night +0x10; s32 maxGameNum +0x14 | heap | schedule controller state | ctrlStatus is a per-turn state machine (2 fresh init, 0 set by updateTurnStart 0x2d99d0, 4 set by updateTurnEnd 0x2d99f8, through scheCtrl_SetStatus). nowDay: fresh init stores the initialize() argument (-1 or 0x5d at the two call sites 0x207204 and 0x2073ec). updateTurnEnd copies nowDay into prevDay then increments it. getNowDay 0x2d9e28 maps 0xff and -1 to none. +0x10 and +0x14 are not verified (nothing read touches them). Getter pwkRec_GetScheCtrlStatusSave 0x2536c0. | confirmed (field semantics for +0 to +0xc); +0x10 and +0x14 unverified |
| B5+0x467b8+12*slot (slot 0 to 127) | 1536 (128 x 12); 1560 with the control record | GroupStatus: s8 status +0 (-1 free, 3 entered, 4 finished); u8 dataStatus +1; s8 slot index +2; u8 UID +3; u8 compe +4; u8 isOveryear +5; u8 isSavedResult +6; u8 open_nation +7; s32 gameNo +8 | heap | competition group slots | Which competitions are loaded this season and their state. status 4 = finished (isCompetitionEnd 0x2db1e4). isSavedResult (+6) is set to 1 by updateTurnEnd 0x203348 (setSavedResultFlag at 0x2033e0) just before calcCompetetionFinish runs, so status 4 with +6 = 0 exists only until that pass. Slot choice is the first free slot (scheCtrl_GetEmptyGroup 0x2df398 scans for -1), so slot order is load order, not UID order: scan for status != -1 and byte +3 equal to the UID. scheCtrl_DeleteGroup 0x2df840 writes status -1. dataStatus, +2 beyond the slot index and gameNo were not verified. Status values other than -1, 3 and 4 are not decoded. Getter pwkRec_GetGroupStatusSave 0x253708. | confirmed. Total span 0x18 + 128*12 = 0x618 bytes; the ScheBlockSave follows at 0x46db8. InitStatus 0x2d9a70 writes -1 into each status byte |
| B5+0x601b8+0x138*row (stats pool); B5+0xae1b8+8*row (entrant pool) | 312 (0x138) per stats row | TeamStats row: u8 played +0; u8 won +1; u8 lost +2; u8 drawn +3; s16 points +4; s16 goals for +6; s16 goals against +8; u8 continuance_state +0xa (1 win, 2 loss, 3 draw); u8 continuance_num +0xb; rest not decoded. Entrant: u32 team id +0, u32 +4 not decoded. Order record: u8 entry index, u8 rank | heap | league table of any loaded league | Live standings, updated in place after each game (_UpdateTeamStats 0x2dcbb8, ScheCtrl_TeamStats::add 0x2de2e8). Reached per UID through [0x390650] -> +0 -> +4 -> slot (+0xc+8*slot, GroupStatus byte +3 = UID) -> BlockData at slot+4; stats = [BlockData+0x14]+0x138*entry (getTeamStats 0x2dc8c0); entrants = [BlockData+0x20]+8*entry (getTeam 0x2dc900); order = [BlockData+0x28]+2*position (getOrder 0x2dc938; a separate heap allocation, not inside block 5 and not saved). The rank is 0-based and ties share a rank (scheMisc_SetRank 0x2e0b40), so position is not always the array index. While canTemporaryBlock 0x2dc200 holds (sys+0x44 equals the UID) the accessors use a temporary BlockData at sys+0x14, so forecast or replay steps can show non-final numbers. Pools: stats 1024 rows (704+160+160), ending exactly at the entrant pool (0x4e000 = 1024*0x138). Entrants are looked up by team id (getEntryTeamIndexFromID 0x2da7f8). | confirmed (layout and chain). Pool getters pwkRec_GetTeamStats 0x2537e0 and pwkRec_GetCompeTeam 0x253828. Points per win (3) and "your entry is the entrant whose u32 is 1" were not verified in code |
| B5+0x46638+4*nation (nation 1 to 52, first at +0x4663c) | 4 | struct {u16 points +0; u8 rank +2; u8 unused +3} | heap | UEFA nation table | UEFA coefficient points (initial 452 to 502 for the six big leagues; the 0 to 511 range is the editor range) and rank position (1 to 52). PlNati 1 to 6 = England, France, Germany, Italy, Spain, Netherlands. Initial ranks from INITNATIDATA.TBB: Spain 1, Italy 2, England 3, France 4, Germany 5, Netherlands 6. The getter pwkRec_GetUefaNation 0x253e08 accepts nation < 0x35, so index 0 also resolves. The rank byte is read by the year-end qualification code at 0x113428 (call 0x113480), by SIMPRG.REL 0x151d58 and 0x151e60 as the nation slot, and by plRec_GetMatchBonus (0x21e2b4) for prizes. The table is rewritten as a block by the SIMPRG.REL function containing 0x150568 and 0x1505a0 (points copied at 0x150fb0, written back by `sh` and `sb` at 0x151000); the calendar trigger is not traced. Parallel world-rating bytes for nations 1 to 145 are at B5+0x4670b+nation (pwkRec_GetWorldNation 0x253e68, bound 0x92). The TBB stores {u8 rank, u16 points}, the runtime record the other way round. | confirmed; loader 0x253418 fills it from INITNATIDATA.TBB; getters 0x253e08 and 0x253e68 |

### Pointer chains and stability

Every entry below starts from P = u32[0x3909a8]. The static roots
0x3909a8 and 0x390650 are fixed addresses in the PAL executable. P and
the block offsets at P+0x28+4k are set once at boot (Pwk.Create, the
constructor 0x21d6f0 shuffles the block order), so they are constant
for the whole boot. Whether the shuffled order is identical on every
boot is unresolved (the generator state at 0x569dc0 starts at a
constant, but other draws before Create were not ruled out), so never
hard-code a block offset across boots.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| pwork root | P = u32[0x3909a8]; Bk = u32[P+0x1c] + u32[P+0x28+4k] | P != 0 from boot on, so it is not a career test. Block offsets are not 0xFFFFFFFF in retail (only block 8 can be absent, and only if byte [P+0x19] is set, which retail never does). The contents are blank until New Game or Continue | P, [P+0x1c] and the block bases are constant for the whole boot: through New Game, Continue and load (Load decodes in place), saves, the demo, matches, year roll-over and return to title. The demo and VS mode overwrite blocks 0 to 7 in place, so the data changes even though the address does not |
| date | B0 = u32[P+0x1c] + u32[P+0x28]; date at B0+0x88 | A career, loaded or new: the year is 2005 or later (blank before New Game or Continue). The demo and VS mode also write a date (2005 turn 95, pwkGen_InitVSDate 0x244328), so pair with the schedule object mode (S+8 == 0x406c78) to be in a career. Valid on career menus and during the match | Same address for the whole boot. The value changes with the turn, and jumps after Continue or New Game, so snapshot the date after a load before arming a rise trigger |
| my league and compe | B3 = u32[P+0x1c] + u32[P+0x28+12] (slot at P+0x34); myleague at B3+0, mycompe at B3+4 | Career created or loaded. A zeroed block reads 0/0, which looks like England first division: pair with the schedule object mode and the date. After pwkLg_Init mycompe is the second-division id | Frames, menus, matches and the rest of a season. The address is constant for the boot; the values change on a new career or a load |
| year-end division shift | B5 = u32[P+0x1c] + u32[P+0x3c]; value at B5+0xb50c8 | A career. Meaningful after the first year end (0 before). Re-zeroed at each year-end sequence (SIMPRG.REL 0x150ecc), so it holds the result only until the next one | Frames, screens, matches and the whole season; survives save and load (block 5 is serialized). Offsets +0x3c and 0xb50c4 are fixed. No mirror found |
| European qualification flags | B5 as above; flag byte at B5+0xb50c4+2 | A career. Bits 1 to 3 are set in the YearEnd callback and hold for the following season; zero before the first year end of a new game | Frames, menus, matches and the season until the next year-end recompute. After a load the value is restored by the save |
| per-competition record | B5 as above; record at B5+0x260+0x98*compe, compe 0 to 48 | A career (compe < 0x31 or the getter returns 0). Changes only inside updateTurnEnd after a competition's last game | Frames, menus, matches and seasons within one career. Values jump at a load or a new career, so do not treat the first read after that as a rise |
| yearly honours history | B5 as above; record at B5+0x31cf4+0x1fc8*i, i 0 to 9 | A career. Rows are meaningful for a competition only after it has finished at least once. Retail PAL, competitions 0 to 48 only | Frames, menus and matches (only calcCompetetionFinish 0x205f40 writes it). Persists across seasons, shifting down one slot per finish. Contents survive save and load; a new game or load jumps the values |
| club world ranking | B1 = u32[P+0x1c] + u32[P+0x28+4]; PlTeamData = B1+0x4b4; fields at +0x41f8, +0x41fa, +0x41fc. Other clubs: B2 = u32[P+0x1c] + u32[P+0x30], fields at B2+0xa8*idx+0xa0/+0xa2/+0xa4 | A loaded career. Position and points are 0 in a new career before the first ranking run | Frames, menus and matches within one career. Values jump on loading a save or starting a career. Points and position change only in the SIMPRG ranking pass; club_rank also by the status routine 0x26dd40 |
| club status | B1 = u32[P+0x1c] + u32[P+0x2c]; u16 at B1+0x1126a, s32 at B1+0x11264 | A career; the u16 should not exceed the cap (0x555150 + 2*rank) | Frames, screens, matches and seasons within a career (changes only at the three StatusChange callers). Values jump on a load or a new career |
| main league UID | B1 as above; value at B1+0x46a8. Other clubs: block 2 = u32[P+0x1c] + u32[P+0x30], +0xa8*idx+0x9c | A career. Read from menus or between matches | Frames, screens, matches and saves or loads within one career. Rewritten by SIMPRG at season roll-over |
| schedule object and today's match | S = u32[0x390650]; D = u32[S+0x414]; compe = s32[D+0x28c], UID = s32[D+0x290], today's matches +0x280 and +0x288; mode word u32[S+8] | S != 0 while the schedule object exists, then compare [S+8]: 0x406c78 normal career, 0x406b98 opening playoffs of a new game, 0x406ab8 VS mode or the title attract demo. D fields are valid from updateTurnStart until updateTurnEnd resets them; -1 in D+0x28c (or D+0x280 == 0) means no match this turn | 0x390650 is a fixed address. S changes each time CreateScheEuro runs (new career, load, opening playoffs, VS start, demo). D is allocated once in the constructor and stable for the life of S. Fields change only at turn start (written) and turn end (reset). The constants at S+8 are PAL addresses |
| schedule controller state and groups | B5 as above; control record at B5+0x467a0; slots at B5+0x467b8+12*slot | A career, and the schedule task has run initialize (0x203030 or 0x2071d0). Not meaningful on the title screen. Valid slots have status != -1 (scan status 3 and 4). In mode: ctrlStatus in {0, 4}, nowDay 0 to 95 or -1 | Frames, menus, matches and turn changes within one career, and across seasons. A UID's slot index is not stable (first-free allocation, slots freed by needCompetitionDataDelete 0x2043f8 and acceptCompetitionDataDelete 0x204460): scan for the UID byte |
| league table | S = u32[0x390650]; SC = u32[S+0]; St = u32[SC+4]; BlockData = u32[St+0xc+8*slot+4] for the slot whose GroupStatus byte +3 equals the UID; stats = u32[BlockData+0x14]+0x138*entry; entrants = u32[BlockData+0x20]+8*entry. The pools themselves sit in block 5 (B5+0x601b8, B5+0xae1b8) | [0x390650] != 0, a slot with that UID exists, BlockData+0x14 != 0. Holds from the competition's load until acceptCompetitionDataDelete withdraws it (some days after it finishes, at the latest at year end). Whether it stays non-zero during a match is not traced | Stable within one career session across frames, screens and matches while the competition stays loaded. Re-read after every load or new career. The slot index is not stable across careers or seasons. After withdrawal the pool bytes may linger but are unreachable through the chain |
| UEFA nation table | B5 as above; record at B5+0x46638+4*nation | A career; the resulting address is within 0 to 0x1FFFFFF. Not meaningful on the title screen | Stable across frames and screens within a loaded career. Changes in one burst when the SIMPRG ranking function runs (trigger not traced), on a new career (loader 0x253418) and on a save load |

### RetroAchievements notes

- P = u32[0x3909a8] is non-zero from boot and constant for the whole
  boot, so it is not a "career running" test. The block contents are
  blank until New Game or Continue. Re-reading the chain each frame is
  harmless but not required by the game. Whether the block offsets are
  the same on every boot is unresolved: read them, do not hard-code.
- Bk needs two pointer reads added together: base u32[P+0x1c] and
  offset u32[P+0x28+4k]. If the author's pointer chain cannot add two
  independent reads, read both and add them in a Measured or remember
  step.
- Pair every read with a mode check. For "a career is running" use a
  non-zero [0x390650] with [S+8] == 0x406c78, or the date year at
  B0+0x88. [S+8] == 0x406ab8 covers both VS mode and the title attract
  demo, so it does not mean the player chose VS mode, and the demo and
  VS mode overwrite blocks 0 to 7 in place. [S+8] == 0x406b98 is the
  opening playoffs of a new game. [0x390650] is 0 at boot, on the logo
  and on the idle title screen. Do not use myleague/mycompe 0/0 as a
  "no career" marker: a zeroed block reads 0/0, which equals England
  first division.
- After any load or new career, snapshot the previous values before
  arming a "rises" trigger. The first read after a load jumps.
- Trophies: compare the u16 at +2 of the per-competition record
  (B5+0x260+0x98*compe) with its value on the previous frame. It
  changes only at turn end after a competition's final game, once per
  finish. Compe numbers for cups are listed in `SCHEDULE_FORMAT.md`;
  play-offs (2, 18, 29) and qualifiers (3, 8, 13, 19, 24, 30) are not
  titles. "Finish in the top 3" is the u8 at +6 in 1 to 3 after the +0
  counter moved. Use an edge, not a level test.
- The honours board (champion team id at record 0, +8*c) can be
  stale-true from an earlier edition if a competition had no entry
  teams, so prefer the per-competition counters, or watch the season
  index s16 at +0x188+2*c change.
- Promotion and relegation: use the 0 to 1 or 0 to 2 edge of the s32 at
  B5+0xb50c8 (1 = promoted, 2 = relegated), or watch mycompe go from a
  second-division id to a first-division id (a new career starts in the
  second division). The flag resets to 0 first at each year end, so two
  consecutive promotions read 1, 0, 1 within one sequence; pair the
  check with the season year or date to avoid missing the second.
- European qualification: bits 0x2, 0x4 and 0x8 of the byte at
  B5+0xb50c6 become set at the year end and stay for the next season.
  They read 0 before the first year end. The EU MVP bit 0x1 has no known
  setter.
- Season roll-over and season number: season = u16 year at B0+0x88
  minus 2006 (0 for the whole 2006-07 season, -1 during the opening
  playoffs of a new game, which run in 2005). The year changes at the
  July roll-over (turn 95 to 0), not on 1 January. Detect the roll-over
  by the turn byte at +2 dropping from 95 to 0, or the month byte at +3
  going 6 to 7.
- Club ranking: world position is u16 at B1+0x4b4+0x41fc (1 = best, 441
  clubs). Guard against 0 (not yet ranked). Use a threshold test with
  the old position (u16 at B5+0xb50c4) to detect an improvement. The
  position is rewritten in one SIMPRG task, so it is stable across
  frames. club_rank (u8 at +0x41f8) can change after a match without a
  ranking run.
- Club status: use numeric thresholds. A threshold of 40,000 needs
  status rank 3 or lower (cap 40,000 at rank 3).
- In-season table checks need a slot search by UID, which RA cannot
  express as a plain chain, and the slot is not stable. Prefer
  end-of-season records for reliable triggers. If an in-season set is
  attempted, take the slot from a debugger on that exact save and read
  stats rows only while the competition is loaded. The tables may show
  non-final numbers while the temporary block is active (forecast or
  replay steps).
- "Competition finished" trigger: GroupStatus status byte becomes 4,
  then isSavedResult at +6 flips 0 to 1 in the same turn-end pass.
- Today's match: s32 at D+0x28c is -1 on turns without a match. It is
  useful for rich presence only when read through the validated chain.
- Signedness: read compe, UID, myleague, mycompe, the honours season
  index and the -1 sentinels as signed. Counters and the other u16
  fields are small, so unsigned and signed reads agree.
- Do not read the 5- or 6-byte span at B1+0x4b4+0x41f8 as one value: the
  fields are u8, padding, u16, u16.

### Unconfirmed

No finding was refuted outright by the game code. The statements below
were refuted, corrected or not verified, so nobody should rely on them.

| Claim | Why not to rely on it |
|---|---|
| P is zero on the title screen, or is recreated on load, new game or return to title | Refuted: Pwk.Create runs once at boot and Pwk.Delete is unreachable (`DOC/` and the script dump). P is constant for the boot |
| A byte [P+0x18] / ext-work swap changes [P+0x1c] during save or load | Refuted for retail: prepareExtWork 0x21d980 has no caller, so [P+0x18] stays 0 |
| The date year is "year - 2006 gives 0 at the first season's end in May 2006" | Refuted: the year is the season's first year, so season index 0 lasts the whole first season (2006-07) and rises at the July roll-over |
| The date field at +4 is a calendar day | Refuted: it is the turn within the month (0 to 7) |
| "turn advances only when the player ends a turn" | Not checked; the writer was not traced (pwkGen_UpdateTurnly 0x2442b8 is only a likely site) |
| myleague and mycompe are -1 when no career exists | Not seen in code; the getters return 0 when the block is absent and the block is zeroed before a career |
| myleague changes at the year end | Refuted: pwkLg_SetMyCompe stores only when old and new compe are in the same league, and pwkLg_Init is the only writer of B3+0 |
| A new career starts in the first division (mycompe 0 / 6 / 11 / 16 / 22 / 27) | Refuted: pwkLg_Init stores the div1 column, the second division |
| "mycompe changes only at year end" | Only the SIMPRG caller (0x150f6c) was found; other callers of pwkLg_SetMyCompe were not searched exhaustively |
| The 0 to 1023 range of world rank points | Not verified |
| The comparison at 0x206400 in calcCompetetionFinish proves the main league check for your club | Corrected: it calls GetTeamMainLeague(2), another club; the comparison for your club is at 0x206428 to 0x206434 |
| "Club rank 24+ = World-class" | Not verified |
| Your club is team id 1 (the rank scan and the "entrant whose u32 is 1") | Inferred from TeamUserOnly names and `CLUBEVENT_FORMAT.md`; no code or doc found that states it for the table |
| 3 points per win from REGULATION.TBB | Not verified in code for the table |
| Order-array rank base and tie encoding | Rank is 0-based with ties sharing a rank in the code read, but treat the position as uncertain when points tie |
| Slot order of GroupStatus is stable across careers | Refuted for use: first-free allocation, so slots vary; unverified whether one league is always loaded into the same slot |
| Compe 33's +4 and +6 hold the result of compe 34's finish | Unverified whether compe 33's own finish later overwrites them |
| Whether a match, a loaded save or a soft reset leaves 0x390650 stale | Not traced |
| `SAVE_FORMAT.md` says "turn 81 to 82 of 2005-06" for the LMASTER max test state | The retail date field gives 2006 for the first season; probably the doc names the data season. Not checkable without a live read |
| Best eleven, MVP and top scorer record contents, and their initial -1 values (pwkRec_InitOtherRecord 0x253948) | Only partly checked; the initial values were not re-read |
| The 3 div_shift_count bytes and the value 3 of PlRec_DivShift | Never written by the code found |
| Which pool rows belong to which competition beyond the BlockData chain | Not decoded |

### Still unknown

From the investigator:

- Slot order of the GroupStatus table: whether your league is always
  loaded into the same slot. Only a runtime check (PINE or debugger)
  can answer this, and it decides whether a live league-table chain is
  usable from RA without a search.
- Whether the block offsets (the shuffled order) are identical on every
  boot of the same build. The generator state 0x569dc0 starts at the
  constant 0x12345678, but other draws before Pwk.Create were not ruled
  out.
- Whether the first 12-byte TeamStats of each 0x138-byte pool row is
  the season total (one final table says yes) and what the other 25 x
  12-byte entries are (per period or per opponent).
  ScheduleControllerBaseSystem::addTeamStats 0x2dcae0, _UpdateTeamStats
  0x2dcbb8 and ScheCtrl_TeamStats::add 0x2de2e8 would tell.
- The meaning of SCHE_CTRL_STATUS values other than -1, 3 and 4 in the
  GroupStatus status byte, and of GroupStatus +1 dataStatus and +8
  gameNo. The callers of scheCtrl_SetStatus 0x2dee70 and
  scheCtrl_SetGroupStatus 0x2deef8 are the place to look.
- PlRec_DivShift value 3 and the three div_shift_count bytes at
  B5+0xb50c4+8: never written by the code found; whether any overlay
  sets them.
- Who sets the EU MVP bit 0x1 of the flag byte
  (pwkRec_SetEUMvp_TeamUserOnly 0x254e38 has no SLES caller; an overlay
  call was not found because the snr2 xref per overlay timed out).
- League records: pwkRec_GetCompeRecord 0x253ec8 holds 2 x 0x38-byte
  records at B5+0x31954+0x38*div (7 entries of {u32 team, u8 value}),
  updated by pwkRec_UpdateCompeRecordGameEnd 0x254568 (entries 0, 1, 4)
  and YearEnd 0x254630 (entries 2, 3, 5, 6) from the user's
  TeamRecordUpdateData. The names of the 7 records are not decoded. The
  0x318-byte honour record at B5+0x319dc (pwkRec_GetHonorRecord
  0x254960, read by plPinfo_YearEndCheck, pwkMoney_GetCoachSalary and
  pwkTeam_MoveOpinfo_RentalBack) was not decoded.
- When in the season SIMPRG.REL recomputes the club ranking (0x150680
  points, 0x150738 ranks, driven from a task state machine at 0x150790)
  and how your own world position (PlTeamData+0x41fc) is updated;
  `SAVE_FORMAT.md` lists this as unknown too.
- Third tier in retail: competitions 50 to 55 are the six first-promote
  UIDs 142 to 147 (end-of-year turns, tied to the new-game promotion
  check, eCREATE_MODE 1), and pwkRec_GetCompePastRecord refuses compe
  >= 49, so there is no retail third-tier table or honours. Under
  `--mod third-tier` the UIDs are 165 to 176 and the code is patched
  (`UID_LIMITS.md`). Where the patched code keeps compe 49 to 55 past
  records (it reuses the same B5+0x260 stride) was not read from the
  mod's code cave.
- pwkGen_Is3rdLeague (0x2442c0) returns 1 while the calendar year is
  below 2006 (lhu year minus 0x7d6, sign bit), is called only by
  CScheEuro_Normal::updateParamDate 0x207228 and picks
  pwkGen_SetStartYear instead of pwkGen_IncDay on the first turn(s). Its
  relation to a "third league" is unclear (the name looks misleading).
- Season-1 oddities: compe 0 to 48 conv records start with
  INITTEAMDATA table 2 "years since held" values (-1, -2, -4), so
  first-edition checks should use the counters (+2 and +4 of the past
  record), not the season index.
- Japanese release addresses were not checked: block 5's layout is the
  same, but code addresses differ and the pwork root is not 0x3909a8
  (`JAPANESE_RELEASE.md`).

Gaps seen in the data:

- The meaning of the year-schedule byte +7 that gates
  calcCompetetionFinish (0x205f88) is not traced, so which competitions
  are recorded in the past records and honours is not known beyond
  compe 0 to 48.
- Which flows enable the temporary BlockData redirect (canTemporaryBlock
  0x2dc200) is not known.
- Whether a match keeps 0x390650 non-zero, and whether the schedule
  object survives a load, was not traced.
- The calendar trigger of the SIMPRG UEFA rewrite and of the club
  ranking is not traced.
- The save-file offsets and the live-memory offsets are the same for
  block 5, but the order array behind the league table is not in the
  save: nothing stores the live order across a load.
- Competition ids for the European League group and other cups are not
  verified from this code; use `SCHEDULE_FORMAT.md`.
- Nothing in the data gives a value for the team-id of the rival club
  (rival = 2 per the investigator) beyond the B2 record-index note
  (team 2 is record 0, `pwkOteam_Team2Otindex` 0x24b7e8).

### Checking the claims

Each command was run from the repo root and shows what is described.

```bash
# P is read by a one-line getter (lui 0x39; lw 0x9a8)
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_GetPwork
```

```bash
# myleague: only pwkLg_Init writes B3+0 (sw at 0x246248); +4 = LeagueDiv2Compe(league, 1)
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkLg_Init
```

```bash
# SetMyCompe stores B3+4 only when old and new compe are in the same league
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkLg_SetMyCompe
```

```bash
# the id table loop at 0x531d40: second argument 1 returns the div1 word
python SRC/sles_disasm.py ISO/SLES_541.51 dis plMisc_LeagueDiv2Compe
```

```bash
# CreateScheEuro: mode 1 and 2 constants, S+8 store at 0x202b4c, pointer store at 0x202b50
python SRC/sles_disasm.py ISO/SLES_541.51 dis CreateScheEuro
```

```bash
# past record at B5+0x260+0x98*compe, compe < 0x31
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkRec_GetCompePastRecord
```

```bash
# honours record B5+0x31cf4+0x1fc8*i, and the season index reader (lh at SIMPRG 0x152108)
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkRec_GetCompeConventionRecord__5Parami
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x152100 6 --sles ISO/SLES_541.51
```

```bash
# year-end: DivShift(2) at 0x150f64, then pwkLg_SetMyCompe at 0x150f6c
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x150f60 6 --sles ISO/SLES_541.51
```

## National teams and tournaments

The game keeps no "national period" variable. Each time it needs one, it
computes call-up, finals and release from the current career date and
the national flag table in `SCHEDULE_LIST.TBB`. The values worth
watching live in the career work area (Pwork, a heap block reached from
a static pointer at 0x3909a8) and in the event system's flag arrays.

Every entry comes from reading the PAL executable (`SLES_541.51`) and
`SIMPRG.REL`, checked by several independent passes. Nothing here was
seen running in PCSX2. Code addresses written as `SIMPRG.REL` are
overlay file offsets, not EE RAM addresses. Labels: **confirmed** means
the code was read and shows it. **empirical** means inferred from data
and not shown in code.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer | static | pwork_root_ptr | Pointer to the career work object (Param::PlPworkTask, allocated as 0x5c bytes). Stored by `plPwork_CreatePwork` (0x21d628), cleared by `plPwork_DeletePwork` (0x21d698). Every career variable below is reached through it. Non-zero from boot (see "Pointer chains and stability"), so non-zero does not mean a career is loaded. | **confirmed**. Store at 0x21d65c (`sw` to 0x9a8 off `lui 0x39`), clear at 0x21d6c8, getter at 0x21d6e0. The only caller of Create is inside `PwkCallbackCommand_Create` (0x110498), the only caller of Delete is inside `PwkCallbackCommand_Delete` (0x110540). |
| [[0x3909a8]+0x1c] + [[0x3909a8]+0x28] + 0x88 | 16 | PlDate: u16 year +0, u8 turn +2, u8 month +3, u32 turn-in-month +4, u32 week-in-month +8, u32 midweek-or-weekend flag +0xc | heap | career_date_year_turn | The current career date. Year (+0) is the FIRST year of the season (2006 for 2006-07, and it stays 2006 from January to June). Turn (+2) is 0 to 95 (8 per month, turn 0 = July). June is turns 88 to 95. Month (+3) is 1 to 12, `((turn>>3)+6)%12+1`. +4 is the turn within the month (0 to 7). +8 is `+4 / 2` (0 to 3) and +0xc is `+4 & 1`. The first real season starts at year 2006, turn 0 (`pwkGen_SetStartYear` 0x2442e8). A new game first sets 2005 turn 92 (`pwkGen_Init` 0x244220 via 0x2441c8), the opening playoffs run 2005 turns 92 to 95, and `pwkGen_InitVSDate` (0x244328) sets 2005 turn 95 for VS mode. `pwkGen_Keika` (0x244430) is year minus 2006 (seasons played, so -1 in 2005). The year goes up by 1 only when the turn wraps from 95 to 0 (`plMisc_GetLaterDay` 0x214788). | **confirmed**. `pwkGen_GetDate` (0x244368) copies 0x10 bytes from block 0 + 0x88. `plMisc_SetTurn2Date` (0x214698) writes the fields. `pwkGen_IncDay` (0x2443d0) advances it in place. Block 0 is the first block of Pwork (see the chain section). |
| no fixed address (flag byte per turn in a resource buffer) | 1 | derived: u8 flags per turn, table index (year-2006) mod 4 | heap | national_period_from_date | Bit 1 = national match (`pwkSche_IsNationalMatch` 0x256b30), bit 2 = finals match (`pwkSche_IsNationalFMatch` 0x256b90), bit 4 = call-up day (`pwkSche_IsNationalConvene` 0x256c50), bit 8 = release day (`pwkSche_IsNationalBreak` 0x256bf0). Retail table: see "Retail national calendar" below. | **confirmed**. The accessors test bits 1, 2, 8 and 4 of `table[turn]` and return 0 for turn >= 0x60. The table is chosen by 0x256a50. The retail bytes were reproduced with `python SRC/natcal.py show DAT/PARAM/SCHEDULE_LIST.TBB`. |
| [0x5eec24] + slot*32 + flag | 1 | u8 per flag (0 or 1); 25 slots x 32 bytes, flags 0 to 14 used | static pointer to heap array | evs_player_flags_calledup | Per-squad-slot player flags, slot = index in your 25-man squad. Flag 9 = called up. Flag 0xa = released after a non-finals call-up. Flag 0xd = released after a finals call-up when his nation was the champion (`getChampionTeam` 0x204020). Flag 0xe = released after a finals call-up when it was not. Only your club's players are flagged. No flag is set in a finals release if `getChampionTeam` returns 0, the player record is null or his nation team is 0. | **confirmed**. 0x5eec24 is EvsWork (0x5eec00) + 0x24. The EVS constructor at SIMPRG.REL 0x129018 stores Pwork EvData + 0x3708 there (EvData = `pwkGen_GetEvData` 0x244cb0 = block 0 + 0x15a8, so the array is block 0 + 0x4cb0, 0x320 bytes). `SetPlayerFlag` (SIMPRG.REL 0x12ce18) range-checks slot < 0x19 and flag < 0xf, then stores 1 at `[0x5eec24] + slot*32 + flag`. Set by `jmNT_CallCheck` (SIMPRG.REL 0x160b68, flag 9 via 0x160ae0) and `jmNT_FreeCheck` (SIMPRG.REL 0x160c50, flags 0xa, 0xd, 0xe). |
| [[0x3909a8]+0x1c] + [[0x3909a8]+0x28+4] + 0x4b4 + 0x20 + slot*0x2a0 + 0x20c | 4 | u32 bit flags, bit 0 (0x1) | heap | pinfo_on_national_duty_flag | Bit 0 of the flags word in a squad player's PlPinfo is set by `pwkTeam_LeavePlayer` (0x2654c0) when he is called up, and cleared by `pwkTeam_ArrivePlayer` (0x265338) when he returns. While set he is out of the regular squad list. PlPinfo is 0x2a0 bytes, 25 slots from PlTeamData+0x20, s16 player id at +0 (negative = empty slot). | **confirmed**. `pwkTeam_GetMyTeamData` (0x259898) = block 1 + 0x4b4. `_plTeam_GetWritePinfo` (0x22c9d0) computes (p - 0x20 - team) / 0x2a0 and requires < 0x19. The call-up worker in SIMPRG.REL (0x160890) calls Leave with a1 = 1 and Arrive with a1 = 1 or 0x400001. Other users of bit 0 (a mask of 1 is the national-duty path, mask 2 is the loan-out path) were not fully excluded. |
| 0x390650 | 4 | u32 pointer | static pointer to heap object | sche_euro_singleton_ptr | Pointer to the live CScheEuro schedule-engine object (0x41c bytes, heap block 1). 0 when none exists. Set by `CreateScheEuro` (0x202a50, store at 0x202b50), cleared by `DeleteScheEuro` (0x202ba8, clear at 0x202bdc). Mode is chosen by the argument of `CreateScheEuro`: 1 = FirstPromote (opening playoffs), 2 = VS (also the title attract demo), anything else = Normal (career). Two vtable words identify the mode: u32 at +8 is 0x406c78 Normal, 0x406b98 FirstPromote, 0x406ab8 VS; u32 at +0x20 is 0x406c28, 0x406b48, 0x406a68. They are two vtables of the same object, so use one set consistently. `getChampionTeam` (0x204020) is a method of this object, read by `jmNT_FreeCheck`. No field offset for national cup state or champion is mapped. | **confirmed**. Stores at 0x202b40 (+0x20), 0x202b4c (+8) and 0x202b50 (the global). Only caller of `DeleteScheEuro` is `Sche.Finalize` (0x113408). The national cups are competitions 44 to 47 (qualifying 44 and 46, finals 45 and 47 per `DOC/SCHEDULE_FORMAT.md` and `natcal.py`). |

### Retail national calendar

This is read from `PARAM/SCHEDULE_LIST.TBB` (four tables, index
(year-2006) mod 4) with `natcal.py`. It applies to the retail PAL disc
only. An LMASTER national-cups build moves tables 1 and 3 a turn
earlier.

| Table (season mod 4) | Raw flag bytes by turn |
|---|---|
| 0 and 2 (Euro qualifying 2006, 2010, ...; World qualifying 2008, 2012, ...) | turns 20, 26, 34, 36, 60, 68 = 13 (match, call-up, release). Turn 88 = 5 (match, call-up). Turn 89 = 9 (match, release). |
| 1 (Euro finals 2007, 2011, ...) | turns 20, 26, 34, 36 = 13. Turn 88 = 6 (finals, call-up, no match bit). Turns 89 to 91 = 1. Turns 92 and 93 = 3. Turn 94 = 11 (match, finals, release). |
| 3 (World Cup finals 2009, 2013, ...) | turns 20, 26, 34, 36 = 13. Turn 88 = 6. Turns 89 to 91 = 1. Turns 92 to 94 = 3. Turn 95 = 11 (match, finals, release). |

Bits 4 and 8 can both be set on one turn, so test each bit on its own.

### Pointer chains and stability

All chains start at the static pointer 0x3909a8. Block i of Pwork is at
`[task+0x1c] + [task+0x28+4*i]`. There are 11 blocks (0 to 10). The
order of the blocks is shuffled once, when the task is built
(`plUty_ShuffleUint8` 0x235270, only call at 0x21d774), so block offsets
are not known in advance. Block 0 is the general block (date, events),
block 1 is your club, block 5 holds records and accounts, block 6 the
schedule calendar. Whether the shuffle gives the same offsets on every
boot is not known (see "Still unknown"), so read the offsets from RAM
and do not hard-code them.

`Pwk.Create` runs once, as the first command of ROOTMAINSEQ.SQB (script
offset 0x10). The only `Pwk.Delete` is at offset 0x1a20, behind a
branch that always goes back to the title, so it is unreachable. So
0x3909a8 is non-zero from boot through logo, title, demo, VS and
career, and the block offsets do not change again until the console is
reset. New game and load decode in place and do not re-create or
reshuffle Pwork. Re-reading the whole chain each frame is still a safe
habit, but the game does not require it. The external-work swap
(`prepareExtWork` 0x21d980, `deleteExtWork` 0x21d9e0) has no caller, so
`[task+0x1c]` never changes in retail.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| pwork_root_ptr | `task = [0x3909a8]` | Non-zero from boot. It does NOT prove a career is loaded: also check the date. | The whole boot. Fixed address on the PAL executable. Not stable across releases (Japanese build: use `gamever.py`). The heap target may differ between boots. |
| career_date_year_turn | `block0 = [[0x3909a8]+0x1c] + [[0x3909a8]+0x28]`, date at `block0+0x88` | Only meaningful once a game has started: the contents are blank until New Game or Continue. Require a non-null pointer in 0x00100000 to 0x01FFFFFF and year >= 2005 (2005 = opening playoffs or VS date, >= 2006 = real career). Readable during matches, but the date does not advance in a match. | Stable across frames, menus and matches. Changes only in `pwkGen_IncDay` or a setter. A season rollover adds 1 to the year and resets the turn. The title demo also rewrites block 0 in place (it runs `Pwk.NewGame`), so check the demo flag at 0x34d43c is 0. |
| national_period_from_date | No address. Use the date chain above and a hard-coded turn list. The flag bytes sit in a resource buffer found by name each call (`Schedule_list.tbb`). | Only with a valid date: year >= 2006, turn < 96. Use the stored year as given. In January to June it is still the season-start year. | Constant across frames, screens and loads, repeating every 4 seasons. Changes only with an LMASTER national-cups edition or another release (Japanese release not checked). |
| evs_player_flags_calledup | `ptr = [0x5eec24]` (EvsWork 0x5eec00 + 0x24). Flag byte = `ptr + slot*32 + flag`. The pointee is block 0 + 0x4cb0 (EvData + 0x3708), 0x320 bytes. | Only in a career, after the EVS object at SIMPRG.REL 0x129018 is built, so the pointer is non-zero and in RAM. Slot valid when the s16 id at `PlTeamData+0x20+slot*0x2a0` is >= 0 (slot < 25). Meaningless in a match, in menus before the career or in demo. Flags 9, 0xa, 0xd and 0xe can be cleared (see below), so latch edges every frame. | The pointer address is fixed. Its value is refreshed when the EVS object is constructed, so re-read it each frame and after any load. Contents persist across frames and screens until the module reset described below. Saves, loads and seasons not verified. |
| pinfo_on_national_duty_flag | `block1 = [[0x3909a8]+0x1c] + [[0x3909a8]+0x28+4]`. Flags word = `block1 + 0x4b4 + 0x20 + slot*0x2a0 + 0x20c`. | Only in a career: block 1 pointer non-zero, slot id >= 0. | Stable across frames, menus, matches, turns and seasons. The flag survives save and load, because PlPinfo is saved. The slot of a player can move after `InsertPidx`, so key on the s16 id at +0, not the slot. |
| sche_euro_singleton_ptr | `obj = [0x390650]` | Non-zero from `CreateScheEuro` until `DeleteScheEuro`. Also non-zero in VS mode, in the opening playoffs and in the title attract demo, so it does not prove a career. Zero at boot, logo and idle title. | The slot address is fixed. The object address changes each time it is created (new game fires it twice: FirstPromote, then Normal). |

Clearing of the player flags: the CFcEuro module destructor
(SIMPRG.REL 0x6b94) calls 0x12a348, which calls 0x12d038. That clears
the whole 25-slot column of every flag whose entry in the table at
SIMPRG.REL 0x1d8858 equals the module's period value (module+0x198). In
that table flags 0, 2 and 3 hold 21 and all others, including 9, 0xa,
0xd and 0xe, hold 4. What sets the module value to 4 was not
identified.

### RetroAchievements notes

- Read `u32 [0x3909a8]` first and follow it only when it is non-zero.
  Then require year >= 2006 in the date before treating the game as a
  real career. The root pointer alone is non-zero on title, demo and VS.
- In rcheevos terms the chain is an AddAddress chain: read 0x3909a8,
  add 0x1c, read the base, and so on. This is a suggestion and was not
  tested.
- The best national-period trigger is the date. Compare year (u16) and
  turn (u8) with the previous frame to see a turn advance, then apply
  the retail calendar above. Hard-code the turn lists. Do not look for
  the SCHEDULE_LIST table in RAM: it has no fixed address.
- The stored year is the season's first year. Turns 88 to 95 (June) are
  still read with year Y even though the calendar year is Y+1.
- Test the call-up bit (4) and release bit (8) separately. Turns 20, 26,
  34, 36, 60 and 68 carry both.
- Finals years: (year-2006) mod 4 is 1 for Euro finals and 3 for World
  finals. Call-up is turn 88 in both. The release turn is 94 (Euro) or
  95 (World).
- "One of my players was called up": watch PlPinfo flags bit 0
  (offset +0x20c) per slot. A rising edge is a call-up and a falling
  edge is the return. These are written only when the jmNT code runs,
  so edges are clean one-shots. Do not fire on the first read after a
  load: a save made mid call-up already has the bit set.
- Pair bit 0 with the slot's s16 id (>= 0) and key on the id, not the
  slot number.
- "One of my players won the Euro or World Cup": flag 0xd of the player
  flags, set at release in a finals year. Poll every frame and latch the
  rising edge. A module reset can wipe flags 9, 0xa, 0xd and 0xe, so a
  late poll can miss them. The champion is only decided through
  `getChampionTeam`, and no fixed address for the champion or the
  finalists is known.
- Flags 9, 0xa, 0xd and 0xe cover only your own 25 squad slots. Other
  clubs' players are not flagged.
- Do not use the event flags 0x13f, 0x140 and 0x141 as a persistent "has
  been called up" marker. See "Unconfirmed".
- Do not use `calendar_day_record` UID -1 as a national-window test. Use
  the date and the calendar table.
- 0x390650 is non-zero in VS mode, the opening playoffs and matches. It
  is a weak "schedule engine exists" signal only.
- All numbers here are PAL only. The Japanese build uses a different
  plPwork global (`lui 0x39 / lw -0x36b8`, that is 0x38c948) and
  different sizes for blocks 2 and 5, so offsets do not transfer
  (`JAPANESE_RELEASE.md`).

### Unconfirmed

Do not rely on these. Each is either unproven or was read differently
by different passes.

| Item | Reason |
|---|---|
| Event flags 0x13f, 0x140, 0x141 (`evs_work_event_flags_ptr` 0x5eec20) | The pointer at 0x5eec20 is static but the array it points to is in Pwork EvData (block 0 + 0x15a8 + 0x3408, 0x156 bytes). `jmNT_CallCheck` sets all three on a call-up day through `EVS::SetEventFlag` (SIMPRG.REL 0x124408). The 0x13f or 0x140 choice uses `pwkGen_Keika` & 3: 0 or 1 sets 0x13f, 2 or 3 sets 0x140, a negative value sets neither. They have reset group 4 in the table at SIMPRG.REL 0x1d82e0, and the group reset (0x12a348 then 0x124488) clears them at EVENT_MODULE teardown when the module's group is 4. Which group the normal career Event screen uses was not traced, so 0x141 does not mean "a call-up has happened in this career". At most use it as a 0 to 1 edge on a call-up day. |
| national_team_squad_records (block 5 + 0x203c, 146 records of 0x1c8) | The layout holds (team id u32 at +0, 23 used six-byte PlOpinfo entries at +0x130, s16 id negative = empty, bsearch over 0x92 records, unused id 0x21f). `pwkOteam_InitNonresident` (0x24d568) fills from index 0 in one mode: mode 0 (0x24d450) the 18 clubs 0x1ba to 0x1cb, modes 1 (0x24d4d8) and 2 (0x24d480) the 83 nationals 0x1cc to 0x21e. Clubs and nationals are never both present, so scan the ids and never index by team. Whether a normal career has national records before the `Pwk.PromotionEnd` command is unknown, and whether block 5 is saved is unverified. |
| calendar_day_record (block 6 + turn*0x48) | 96 records of 0x48 bytes, s32 UID at +4, u16 flags at +0x26, u16 event number at +0x38 (0xffff none), block 6 size 0x1ce8 usable. UID -1 does NOT mean a national window: it is the default for every unscheduled day and is also written when the club's competition is finished or the club has no games left. Use the `pwkSche_IsNationalBreak` data for national periods. The +0x30 byte is dual use in the docs and was not traced. |
| schedule_pools_national_cup_results (block 5 + 0x47bb8, + 0x601b8, + 0xae1b8) | Offsets and pool sizes are confirmed (6,240 x 16 B game records, 1,024 x 0x138 B team stat rows, 1,024 x 8 B entrants; getters 0x253798, 0x2537e0, 0x253828) and the pools are shared by all schedule competitions. Rows are not tagged with a competition and the competition-to-slot mapping was not traced, so Euro or World Cup rows cannot be picked out. The row layout (played, won, lost, drawn u8 at +0 to +3, then u16 points, goals for and against at +4, +6, +8) is empirical from one save. The writer is untraced. |
| pinfo flags: bit 0x400000 and bit 0x300 | 0x400000 appears only as an extra bit in one return path's clear mask (a1 = 0x400001). Nothing was found that sets it or tests it. The claim that 0x300 keeps a player out of the call-up is not shown by the code. `_plTeam_DeleteRegular` clears bit 0x04000000 at +0x20c. |
| "Your club has no national matches except those turns" | The code only gives the flag bytes. Whether the club schedule avoids those turns was not checked. |
| nationality field at PlPinfo +0x1ac | Used only in a reading of `jmNT_FreeCheck`. Not checked. |

### Still unknown

- Which function calls `jmNT_CallCheck` (SIMPRG.REL 0x160b68) and
  `jmNT_FreeCheck` (SIMPRG.REL 0x160c50), and on which phase of the
  turn. This decides when call-up flags change within a turn.
- What sets and clears PlPinfo+0x20c bit 0x400000, and whether bit 0x1
  is used by loans or other systems.
- Whether the event flags 0x13f, 0x140 and 0x141 and the player flags
  9, 0xa, 0xd and 0xe are ever cleared outside the group reset (year
  start, next call-up), and whether they are part of the save.
  `ClearPlayerFlag` (SIMPRG.REL 0x12ce90) and its wrappers (0x12cf58,
  0x12cfa8, 0x12d000) exist, but their callers were not traced.
- What sets the module period value to 4 in the CFcEuro module.
- How the national cups' state and champion are stored inside CScheEuro
  (0x390650): the competition-to-pool mapping, the current round, and
  the winner that `getChampionTeam` (0x204020) returns. There is no
  confirmed address for "World Cup won" or the finalists. An achievement
  for "wins the cup" can only use the player flag 0xd route, which only
  covers your own players.
- Whether the national-team records are always all 83 present and
  sorted (`InitNonresident` modes), checked on a live heap.
- What `_getNationalTeamPoint` (0x227200) scores and why team 465 is
  accepted.
- Whether `jmNT_NewCall` and `calcNewCallAnotherNation` (SIMPRG.REL
  0x15fc40) call up extra players for a nation outside the competition.
- Whether VS mode and the opening playoffs show national-calendar
  behaviour (the date there is 2005, so the retail table index and the
  Keika value of -1 are outside the normal range).
- Whether the shuffled Pwork block order is the same on every boot of
  the same build (the generator state starts at the constant
  0x12345678, but other draws before `Pwk.Create` were not
  enumerated).
- Which callers pass which mode to `CreateScheEuro` beyond the four
  call sites in `Sche.Initialize`, `InitializeFirstCheck`,
  `InitializeContinue` and `Initialize_VsMode`, and which states leave
  the pointers at 0x5eec24 and 0x390650 stale after a career.
- Whether the player-flag array and the event-flag array are written
  into the save.
- The Japanese build differs: its Pwork global and the sizes of blocks
  2 and 5 are different, so block 2 and block 5 offsets are PAL only
  (`JAPANESE_RELEASE.md`).
- Nothing was seen running in PCSX2. Every item is from code reading.

### Checking the claims

```bash
# Pwork root: Create stores 0x3909a8 at 0x21d65c
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21d628 16
# the date writer: month, turn in month, week fields
python SRC/sles_disasm.py ISO/SLES_541.51 dis plMisc_SetTurn2Date
# the national accessors (bit tests, table from 0x256a50)
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkSche_IsNationalMatch
python SRC/sles_disasm.py ISO/SLES_541.51 syms IsNational
# CScheEuro: vtable words at +0x20 and +8, global store at 0x202b50
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x202b40 8
# the retail national calendar
python SRC/natcal.py show DAT/PARAM/SCHEDULE_LIST.TBB
# player flags: SetPlayerFlag reads [EvsWork+0x24] + slot*32 + flag
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x12ce18 10 --sles ISO/SLES_541.51
```

## Career records and cumulative counters

This part of memory is the career work (`Param::PlPworkTask`), a heap
object reached from a static pointer. It holds the results, honours,
club standing, date and squad statistics that the game keeps over a
career, and the save serialises all of it, so these values survive a
save and load. There are no lifetime win, draw, loss, goal or transfer
counters in memory. The game keeps per-competition title and entry
counts, a 10-edition champion history, this season's streaks and
accounts, and per-player season and career stat rows. Anything lifetime
must be built by the achievement logic from frame-to-frame deltas.

All of this comes from static analysis (disassembly, the repo docs, the
field-name table). Nothing was run in an emulator for this section. The
only result seen in the running game is the PCSX2 save-state test in
`SAVE_FORMAT.md` (Nexxus's report, 2026-10-27), which covers the block
chain and the club status.

Notation: `p` is the u32 at 0x3909a8. `base` is the u32 at `p+0x1c`.
`B(i)` is `base + u32@(p+0x28+4*i)`. The table below writes "B(5)+off"
for an address inside block 5. The chain is spelled out under "Pointer
chains and stability".

The pwork object is built once per boot. `Pwk.Create` is the first real
command of `ROOTMAINSEQ.SQB` (script offset 0x0010) and the only
`Pwk.Delete` (0x1a20) cannot be reached, so `p`, `base` and every block
offset are fixed from boot until the console is reset. New Game, Load,
the title attract demo and VS mode rewrite the contents in place. They
never move the blocks.

### Confirmed findings

"Confirmed" means the address was read in the executable (PAL
`SLES_541.51`). "Empirical" means inferred from data or from code that
was not fully traced. Where a row was corrected after review, the text
here is the corrected one.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer | static | pwork_ptr (career work root) | Root pointer to the 0x5c-byte `PlPworkTask`. It is non-zero from the first script command of the boot (`Pwk.Create`) and does not change again, so it is not a "career is running" flag. Before New Game or Continue the blocks behind it hold blank data. For a career gate use a populated career field (see the RetroAchievements notes). | Confirmed. `plPwork_CreatePwork` 0x21d628 stores it (`sw a2, 0x9a8(s1)` at 0x21d65c), `plPwork_DeletePwork` 0x21d698 clears it (0x21d6c8), `plPwork_GetPwork` 0x21d6e0 reads it. `PwkCallbackCommand_Create` 0x110498 is the only caller of Create (0x1104b8) and `PwkCallbackCommand_Delete` 0x110540 the only caller of Delete (0x110570). |
| B(0)+0x88 | 16 | PlDate: u16 year @+0, u8 turn @+2 (0 to 95, 0 = July), u8 month @+3, s32 turn in month @+4 (0 to 7), s32 @+8 (turn in month / 2, 0 to 3), s32 @+0xc (parity: 0 midweek, 1 weekend) | heap | Career date | `year` is the first calendar year of the season: it increases only when the turn wraps from 95 to 0 (July), so January to June keep the year of the season they belong to. Month = ((turn >> 3) + 6) % 12 + 1. Only turn 0 to 95 and month 1 to 12 are valid, which makes a blank block (all zero, year 0) easy to reject. New Game sets 2005 turn 92 (the opening playoffs run turns 92 to 95), and the first real season starts at 2006 turn 0. Count seasons with year deltas. | Confirmed. `pwkGen_Init` 0x244220 (from `Pwk.NewGame` 0x110a60) memsets block 0 and sets 2005 turn 0x5c through 0x2441c8. `pwkGen_SetStartYear` 0x2442e8 sets 2006 turn 0 and `pwkGen_InitVSDate` 0x244328 sets 2005 turn 0x5f (called from `Sche.Initialize_VsMode` 0x114618). `plMisc_SetTurn2Date` 0x214698, `plMisc_GetLaterDay` 0x214788, `pwkGen_IncDay` 0x2443d0 and `pwkGen_Keika` 0x244430 (year minus 0x7d6). |
| B(5)+0x262+compe*0x98 | 2 | u16 | heap | Titles won (numvic) | Number of times your club (team id 1) finished first in competition `compe` (0 to 48). It is part of one 0x98-byte record per competition: u16 numheld @+0x260 (editions held, whether or not you took part), u16 titles @+0x262, u16 entries @+0x264, u8 last place @+0x266, last final order as u32 team ids at +0x268+4*place (place < 32), and a 16-byte PlDate of the first title at +0x2e8 (written when the count becomes exactly 1). `numheld` is incremented once per finished edition. For compe 29 and compe 36 it is incremented only when the finishing schedule UID is 0x32 (compe 29) or 0x4d (compe 36). For any other UID of those two the +0x260 word is left alone, while the title, entry and place words are still updated. Compe names are in `SCHEDULE_FORMAT.md`. | Confirmed. Getter `pwkRec_GetCompePastRecord` 0x253590 (block 5 + 0x260 + compe*0x98, compe < 0x31), `pwkRec_HaveVictory` 0x253dd0, `pwkRec_HaveEntry` 0x253d98, `pwkRec_SetPastRecordLastTeamOne` 0x2535f0. Writer `CScheEuro::calcCompetetionFinish` 0x205f40: numheld at 0x206060, 0x2060fc, 0x206208 and 0x206254, titles at 0x206310, entries at 0x2062f4, place at 0x2062e4, first-title date by the call at 0x206314. That "place index 0" means a win is empirical. |
| B(5)+0x266+compe*0x98 (u8); B(5)+0x264+compe*0x98 (u16) | 1; 2 | u8 myrank; u16 entries | heap | Your final place and entries | `myrank` is your 1-based final place in the latest finished edition (1 = winner), 0 if you were not entered. `entries` counts editions you entered and rises only when you were present. The u16 at +0x262 counts wins and the u16 at +0x260 counts editions held. Compe 33's record is also rewritten when compe 34 finishes (+0x264 incremented, +0x266 set to 1 when entered, else 0). Detect a finish by a rising edge of `entries`, not by a change of `myrank`. | Confirmed. `calcCompetetionFinish` 0x205f40 (`myrank` stored at 0x2062e4 as place + 1, or 0 when absent; `entries` at 0x2062f4 only when you are in the result list; compe 33 rewrite at 0x2061e0 to 0x2061f8). The branches for compe 29 (UID 0x32 or other) and compe 36 (UID 0x4d or other) set the last-order slots and then reach the same scan at 0x20628c, which sets the three words. |
| B(5)+0x319c4 (your club); B(5)+0x319d0 (rival) | 12 each | struct: u8 +0 clean-sheet run, u8 +1 win run, u8 +4 loss run, u32 +8 last result (1 win, 2 loss, 3 draw) | heap | League run counters (UpdateData kind 0 and 1) | Consecutive main-league wins at +1, consecutive losses at +4. A draw zeroes both, a win zeroes the loss run and a loss zeroes the win run. +0 is a clean-sheet run that is reset when goals conceded are not 0 (whether it counts shoot-out goals is unverified). +8 says how the last match ended. The record is edited on a stack copy and written back whole, so all bytes change together once per match. Bytes +2 and +3 accumulate goals for and against (saturating at 0xff) and +5 and +6 mirror them (meaning of all four unverified). Cleared at year end. Kind 0 is team id 1 (you) and kind 1 is team id 2 (the rival). The rival record is also updated from a second call site (0x11141c) behind a top-two-division test (0x111408). | Confirmed. Accessor `pwkRec_GetTeamRecordUpdateData` 0x253fe8 (and 0x254078 for the write-back) computes block 5 + 0x319c4 + kind*0xc for kind < 2. Streak helper 0x254380 is called via 0x2544c8 from `pwkRec_UpdateCompeRecordGameEnd` 0x254568, goal helper 0x254290. Updated only when the match group is below 0x8e and equals `plTeam_GetTeamMainLeague(1)` (test at 0x111324 inside `PwkCallbackCommand_GetGameIfData` 0x1112d0), so cups and European matches do not count. Cleared by `pwkRec_InitTeamRecord` 0x254710, called at 0x110bf0 from `PwkCallbackCommand_StartYearEnd` 0x110be0. |
| B(5)+0x31cf4+h*0x1fc8+compe*8 (champion); B(5)+0x31cf4+h*0x1fc8+0x188+compe*2 (season index) | 8 per champion record | champion u32 team id @+0, u8 your place @+4 (1-based, 0 = not entered); u16 season index per compe | heap | Competition history slots | The last 10 editions of every competition (h = 0 newest, 9 oldest, 0x1fc8 bytes per slot, compe 0 to 48). The u16 is the season index: the first calendar year of the season minus 2006. A final played in May 2007 (season 2006-07) stores 0, not 1. Each slot also holds Best XI (+0x1ec+compe*0x84), MVP (+0x1b30+compe*0xc) and top scorer (+0x1d7c+compe*0xc). Slot 0 byte +4 equal to 1 means you won. `pwkRec_ShiftCompeConventionRecord` 0x253c58 shifts the slots (called at 0x205fc0) just before the new result is written (0x20636c to 0x20637c), so between the two writes slot 0 briefly equals slot 1. | Confirmed. Getters `pwkRec_GetCompeConventionRecord` 0x253a90 (h < 10), VictoryTeam 0x253af8, Keikayear 0x253b38, MVP 0x253bc8. Writer `calcCompetetionFinish` 0x205f40 stores the place byte at 0x206370 and the season index (`pwkGen_Keika` 0x244430) at 0x20637c. The place being the rank of team 1 is empirical. The init tables may seed history, so detect a change of the season index or champion word, never a non-zero slot 0. |
| B(5)+0xb50c4 | 8 | struct: u16 old world club rank @+0; u8 flags @+2 (bit0 European MVP, bit1 European League entry, bit2 European Club Cup entry, bit3 International Club Cup entry); s32 division shift @+4 (0 none, 1 promoted, 2 relegated) | heap | User-only qualification and promotion flags | The division shift is set to 0 and then to 1 (new division number lower) or 2 (higher) in the year-end pass of SIMPRG.REL (0x150ecc, 0x150f4c, 0x150f64) and stays until the next pass. Use a 32-bit read. The three entry bits (masks 0x2, 0x4, 0x8) are cleared and then set by the unsymbolised function 0x113428, which sits between `ScheCallbackCommand_Finalize` 0x113408 and `ScheCallbackCommand_YearStart` 0x113608. The EU MVP bit (mask 0x1) is not touched there. Which season the entry bits describe and the meaning of the old-rank u16 were not traced. A saved 1 would re-fire a level read after a load, so edge-detect. | Confirmed. Accessor 0x254c00 (block 5 + 0xb50c4), setters `pwkRec_SetELEntry_TeamUserOnly` 0x254c88, `SetECCEntry` 0x254d08, `SetICCEntry` 0x254d88, `SetEUMvp` 0x254e38, `DivShift` 0x254eb8, old rank 0x254f18. `InitTeamUserOnly` 0x254c48 clears the whole struct. In 0x113428 the clears are at 0x113440 to 0x113450 and the sets at 0x1135a8, 0x1135b8 and 0x1135c8 (`Finalize` itself only calls `DeleteScheEuro`). Block 5 is 0xb50d0 bytes, so the struct sits at its end. |
| B(1)+0x46ac (u8); B(1)+0x1126a (u16); B(1)+0x11264 (s32) | 1; 2; 4 | u8 club rank 0 to 31; u16 status points; s32 status rank 0 to 8 | heap | Club rank and club status | Club rank = status >> 11, capped at 31. Status is capped by the status rank (caps 65535, 60000, 55000, 40000, 30000, 25000, 10000, 7000, 7000, table 0x555150). The status rank only ever lowers and is 7 at career start, and the club rank starts at 0. The club rank is written at 0x26dd84 by the function at 0x26dd40, which is called only from `pwkTeam_GameCheck` 0x26ddd8 (call at 0x26df74), `pwkTeam_MatchGameCheck` 0x26dfa8 (0x26e274) and `pwkTeam_YearEndCheck` 0x26e2a0 (0x26e2d4). `pwkTeam_GetMyClubRank` 0x259b60 divides by 2047 instead, so do not mix the two. | Confirmed. Fields from `pwkTeam_Status` 0x26e2f0, `pwkTeam_StatusChange` 0x26dbb8, `pwkTeam_StatusChangeRank` 0x26dc50 (stores only a lower rank), `pwkTeam_StatusInit` 0x26e328 (rank 7, club rank 0). PCSX2 save-state test recorded in `SAVE_FORMAT.md` (Nexxus's report, 2026-10-27). |
| B(5)+0x46638+4*nation (nation 1 to 52); B(5)+0x4670b+nation (nation 1 to 145) | 4; 1 | UEFA: u16 points @+0, u8 rank @+2, byte +3 unused; world: u8 | heap | UEFA nation points and rank, world rating ("FIFA points") | UEFA rank 1 is best (initial data has Italy 2, England 3, France 4). The world byte is a rating of about 4 times the national rank number (Brazil 125), so the range is not 0 to 127. Both tables are rewritten in play: the SIMPRG.REL year-end pass copies the table out, recomputes it and writes it back (UEFA at 0x151000, world at 0x151330). The executable itself only reads them (7 call sites). The month of the pass was not traced, so treat a change as an edge, not a constant. | Confirmed. Getters `pwkRec_GetUefaNation` 0x253e08 (nation < 0x35) and `pwkRec_GetWorldNation` 0x253e68 (nation < 0x92). SIMPRG.REL 0x151000 loops nation 1 to 0x34 and stores a u16 (0x15102c) and a u8 at +2 (0x15103c). 0x151330 loops nation 1 to 0x91 and stores a byte (0x151364). Callers 0x150528 and 0x1505c0. Initial fill by the `INITNATIDATA.TBB` callback 0x253418. |

### Pointer chains and stability

Every entry below sits behind the same root. All reads are 32-bit
little-endian.

```text
p     = u32[0x3909a8]            ; non-zero from boot
base  = u32[p + 0x1c]
B(0)  = base + u32[p + 0x28]     ; date block
B(1)  = base + u32[p + 0x2c]     ; club and squad block
B(5)  = base + u32[p + 0x3c]     ; results and honours block (0xb50d0 bytes)
```

In the retail game all 11 blocks exist, so no offset word is
0xffffffff. If one ever were, `pwGet` 0x21da50 would still return `base`
and not 0, so test the offset word yourself. The block sizes (usable
bytes) are 0x20e48, 0x129e8, 0x120c0, 0x530, 0xa8, 0xb50d0, 0x1ce8,
0x44, 1, 8 and 1 (table 0x533ac8 minus the 8-byte trailer). Block 5
offsets stay valid if the third-tier mod appends records at its end
(compe 49 to 55 past +0xb50d0; not re-checked on a patched executable).

The block order is shuffled once, in the constructor 0x21d6f0
(`plUty_ShuffleUint8` 0x235270, drawing on the generator state at
0x569dc0). The offsets are therefore fixed for the whole boot. That
state starts at the constant 0x12345678, so the layout may be the same on
every boot, but that was not checked. Use an AddAddress chain and do not
hard-code the sums.

The "ext work" swap (`prepareExtWork` 0x21d980, `switchExtWork` 0x21da20,
flag at `p+0x18`) is dead in the retail game: `prepareExtWork` has no
caller, so `p+0x18` stays 0 and `p+0x1c` never changes.

What changes is the content. Load decodes into the same buffers,
`Pwk.NewGame` re-initialises them in place, and so do the title attract
demo (`ROOTDEMOMATCHSEQ.SQB` runs `Pwk.NewGame` at 0x88 and
`Sche.Initialize_VsMode` at 0xa8) and VS mode. A value can therefore
jump or reset at those moments while its address stays the same.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| pwork_ptr | static word at 0x3909a8 (`lui 0x39; lw 0x9a8`) | Always non-zero once the first script command has run. Not a career gate. For data readiness also require a sane date at B(0)+0x88 and the demo flag at 0x34d43c equal to 0. | The whole boot: the pointer, the 0x5c-byte object, `base` and the block offsets never change until a reset. |
| Career date | B(0)+0x88 | `p != 0`, `base != 0`, block in 0x100000 to 0x1FFFFFF, then year >= 2005, turn < 96, month 1 to 12. Blank memory reads year 0. | Address fixed for the boot. The value is replaced on New Game, Load, the attract demo and VS mode (VS sets 2005 turn 95). Advances turn by turn in a career. |
| Titles won (numvic) | B(5)+0x262+compe*0x98, compe <= 48 | Chain non-zero and a sane career date. A value of 0 before the first title is normal. | Address fixed for the boot. The value survives frames, menus and seasons, and is replaced by a Load, a New Game or the attract demo. Re-baseline when the date becomes invalid or jumps. |
| Final place and entries | B(5)+0x266+compe*0x98 and B(5)+0x264+compe*0x98 | A sane career date, compe <= 48. Take the `entries` baseline after the career is loaded and ignore the edge on a load or save-slot change. | Address fixed for the boot. The value holds until the next edition of that competition finishes, and is rewritten wholesale by a Load or New Game. |
| League run counters | B(5)+0x319c4 and B(5)+0x319d0 | A sane career date. Live copy. Changes once per match in `PwkCallbackCommand_GetGameIfData` 0x1112d0, and only for main-league matches. A drop of +1 or +4 to 0 means a draw, the opposite result or year end, so keep the previous value and the +8 word to tell them apart. | Values survive a save and load and are stable across frames, screens and matches. Zeroed at `StartYearEnd`. The address is fixed for the boot. |
| Competition history slots | B(5)+0x31cf4+h*0x1fc8 (h <= 9), +compe*8 and +0x188+compe*2, compe <= 48 | A sane career date. A result is present only after `calcCompetetionFinish` has run for that competition. Watch a change of the season index u16 or the champion word. | Frames, menus, matches, save and load. Persists 10 editions, then drops off slot 9. Changes only at competition end (and when a Load or New Game replaces it). |
| Qualification and promotion flags | B(5)+0xb50c4 | A sane career date. Outside a career a non-zero value is not meaningful. | Live value saved with block 5, so it survives a load. Written rarely (DivShift in the year-end pass, entry bits by 0x113428). |
| Club rank and status | B(1)+0x46ac, B(1)+0x1126a, B(1)+0x11264 | A sane career date. | Frames, screens and matches. Changes only at the match-result, placing and year-end calls. Replaced by a Load or New Game. |
| UEFA and world tables | B(5)+0x46638+4*n and B(5)+0x4670b+n | A sane career date. Not meaningful before a career exists. | Frames, menus, matches and screens. Rewritten by the SIMPRG year-end pass, and replaced by a Load or New Game. |
| Season league table (unconfirmed, see below) | B(5)+0x601b8+row*0x138 and B(5)+0xae1b8+row*8 | A sane career date; entrant team id in 1..0x22e; played == won+lost+drawn as a sanity check. | Same address and values across frames, screens and turns; changes when a game result is recorded for that schedule. Rewritten by a Load, a New Game or the attract demo. |
| Transfer accounts (unconfirmed, see below) | B(5)+0x48, +0xd0, +0x178, +0x200 | A sane career date. | Stable across frames, screens and matches. Month copy cleared at each monthly report, season copy at each annual report. |
| Honour record (unconfirmed, see below) | B(5)+0x319dc | A sane career date. Real data only after the first season-end awards screen. | Survives save and load, overwritten wholesale at every season end. |
| Squad stat rows (unconfirmed, see below) | B(1)+0xec88+slot*0x11e | A sane career date, and the slot's PlPinfo id at +0 non-negative. | Live state. Counters change when `pwkTeam_AddPlayerRecord` 0x267d80 runs (end of match processing), not during play. Slot indices shift on transfers, so key milestones on the PlPinfo id. |

### RetroAchievements notes

- Do not use the u32 at 0x3909a8 as a career flag: it is non-zero from
  boot. Gate every condition on a populated career field instead: a
  sane date at B(0)+0x88 (year >= 2005, turn < 96, month 1 to 12) and
  the demo flag at 0x34d43c equal to 0 (`SetDemoFlag` 0x109394, set 1 by
  the attract demo script and cleared at its end). VS mode also writes a
  valid date, so if you need to exclude it, test that
  `u32[0x390650]` is 0, or that `u32[u32[0x390650]+8]` is not 0x406ab8
  (the VS schedule vtable; empirical for this use).
- The block addresses are fixed within a boot, so re-resolving the chain
  every frame is only defensive. What does change is the content: a
  Load, a New Game or the title attract demo replaces it in place.
  Key delta logic on a sane date and re-baseline silently when the date
  becomes invalid or goes backwards, instead of comparing with the old
  value. Otherwise a save load can fire or lose an achievement.
- Prefer edges from one frame to the next, never levels. A saved
  division shift of 1 or a saved non-zero history slot would re-fire as
  a level after a load.
- For "win the competition N" use the rising edge of the titles u16 at
  B(5)+0x262+compe*0x98, or slot 0 of the history (place byte +4 equal
  to 1) with a change of the season index or champion word. Do not
  treat a non-zero slot 0 as proof, because init tables may seed
  history.
- For participation and placing use the rising edge of the `entries`
  u16 at +0x264 and read `myrank` at the same time. A repeat place
  leaves `myrank` unchanged, and a non-entry edition rewrites it to 0
  without raising `entries`. Compe 33's `entries` can also rise when
  compe 34 finishes.
- For "win N league games in a row" read the u8 at B(5)+0x319c5 and look
  for the frame it goes from N-1 to N. The write happens once at match
  end, so the jump is clean. A fall to 0 can be a draw, a loss or year
  end; the u32 at +8 tells the result. Only main-league matches count.
- For promotion edge-detect the s32 at B(5)+0xb50c8 from 0 to 1 (use a
  32-bit read). Entry bit meanings: 1 European MVP, 2 European League,
  4 European Club Cup, 8 International Club Cup. Which season they
  describe is unverified.
- For reputation thresholds read the club rank u8 at B(1)+0x46ac (0 to
  31). It changes only at the match-result, placing and year-end calls.
  The status is hidden in the game.
- Season-count achievements: count increments of the date year between
  frames (the year increases when July starts). The opening playoffs sit
  in 2005 turns 92 to 95, so use deltas, not absolute values.
- Lifetime totals do not exist in memory, and the month and season
  accounts and the league table clear on their own schedules. Anything
  lifetime must be accumulated by the logic from deltas.
- The UEFA and world tables are rewritten by a year-end pass. Use them
  only as an edge, and note that the month of the pass was not traced.
- Unwritten honour and history entries read as 0, and player id 0 is a
  valid id, so require a non-zero written field before trusting an id
  match.
- Detect changes after the game processes a match, not at the moment of
  a goal. Season and career stat counters update when the match record
  is applied.

### Unconfirmed

These findings were corrected by reviewers or one finding's key claim
was refuted. They are empirical at best. The corrected form is given so
you can see what is agreed, but verify in the game before relying on
them.

- **Squad player stat rows.** Agreed: 0x11e bytes per slot (25 slots),
  row = u16 goals @+0, u16 assists @+2, u16 games @+4, u16 club games
  while present @+6, u16 man of the match @+8, u16 average rating x100
  @+0xa (weighted by games), u8 red @+0xc, u8 yellow @+0xd, 5
  competition kinds per table, 14 bytes per row. `pwkTeam_SumCareerRecord`
  0x267e88 confirms the row, and the slot-to-player map is the PlPinfo
  s16 id at B(1)+0x4b4+0x20+slot*0x2a0 (negative = empty). The stat block
  starts at B(1)+0xec88, with the season table at slot base +0x4c, a
  middle table at +0x92 (presumably last season, unverified) and the
  career table at +0xd8. That puts the season table at B(1)+0xecd4 and
  the career table at B(1)+0xed60 for slot 0. An earlier reading with
  four tables starting at +0xec8e and 6 spare bytes was not agreed.
  `pwkTeam_GetPlayerStats` 0x265810 returns an interior pointer (+0xec90)
  and must not be used to read rows. `pwkTeam_AddPlayerRecord` 0x267d80
  is the writer (adds into the season and career rows). Verify the first
  row address in an emulator.
- **Season league table rows.** Agreed: stats row i at B(5)+0x601b8+i*0x138
  and entrant i at B(5)+0xae1b8+i*8, 1024 rows each (0x601b8 + 0x4e000 =
  0xae1b8). The row's first 12 bytes are u8 played @+0, u8 won @+1, u8
  lost @+2, u8 drawn @+3, u16 points @+4, u16 goals for @+6, u16 goals
  against @+8, u8 continuance_state @+0xa, u8 continuance_num @+0xb
  (meaning unverified). The entrant team id is a 32-bit word, and the top
  team id is 0x22e (ids 0x21f to 0x22e are the 16 VS teams). A club sits
  in several schedules, so scanning for team id 1 returns several rows.
  Not agreed or not verified: lockstep between a stats row and the
  same-numbered entrant row (the code does not enforce it, use played ==
  won+lost+drawn as a check), when rows clear at year end, and the
  remaining 0x12c bytes of a row (`setCurrentGameResult` copies up to 25
  records of 12 bytes, meaning unverified).
- **Season transfer fee accounts.** Block 5 starts with four arrays of
  s64 accounts (month income at +0, month payment at +0x60, season
  income at +0x130, season payment at +0x190, 8 bytes per type). The
  offsets here are income type 9 and payment type 14 in each: s64 at
  B(5)+0x48 (month income), +0xd0 (month payment), +0x178 (season
  income) and +0x200 (season payment), updated by
  `pwkRec_AddMonthlyIncome` 0x252d88 and `pwkRec_AddMonthlyPayment`
  0x252de0. The month is folded into the season by
  `pwkRec_AfterMonthlyReport` 0x252c98 and the season is cleared by
  `pwkRec_AfterAnnualReport` 0x253020. No call site in the executable or
  in any overlay passes the constant 9 to Income or 14 to Pay, and no
  transfer code path that books these types was found. That types 9 and
  14 are player transfer fees rests only on message-name tables. Test
  with a real signing and sale before use. Unit: stored money, pound =
  value / 6, euro = value / 4 (the pound and euro assignment is
  empirical). Not lifetime totals.
- **Year-end honour record.** Agreed: 0x318 bytes at B(5)+0x319dc (Best
  XI 3 sets x 11 x 12 bytes, MVP 3 x 12 bytes at +0x18c, top scorers 3
  sets x 10 x 12 bytes at +0x1b0), each entry opening with an s16 player
  id at +0 that is compared with PlPinfo +0, entries empty as 0 (not -1).
  The writer is a SIMPRG.REL function at 0x15d498 (from
  `CBestPlayerManager`), not `BestPlayer_YearEndUpdate` 0x2b9978. Best XI
  and MVP entries are s16 id @+0, u32 @+4, u32 @+8, and a top scorer
  entry is s16 id @+0, u32 @+4, u16 goals @+8. The sets are set 0 = own
  nation division 0, set 1 = own nation division 1, set 2 = European,
  but the loop at 0x15d5c8 passes division 0 for both iterations, so sets
  0 and 1 are only empirical. The meaning of source +4 and +0x10 (team,
  position) is unverified. Gate a check on a written field (non-zero team
  or goals, or a season-counter change).
- **Dropped claims.** The earlier claim that B(1)+0x46b0 holds world club
  rank points (0 to 1023) had no code or doc behind it and was dropped.
  The 0 to 127 range for the world byte, "rises and falls with European
  results", and "no code writes the UEFA and world tables after the
  initial load" were not supported or were refuted (see the UEFA row).

### Still unknown

- Whether the block offsets (and so every block base) are identical on
  every boot. The shuffle state at 0x569dc0 starts at the constant
  0x12345678, but draws on it between `fcEuroRand_Init` 0x111698 and
  `Pwk.Create` were not enumerated.
- The exact start of the player stat rows (see Unconfirmed), and which
  of the stored time tables is the current season and which is last
  season.
- The meaning of the 7 league record entries at B(5)+0x31954+div*0x38
  (each {u32 team, u8 value}) and of bytes +2, +3, +5, +6 of the run
  counter records. Entries 0, 1 and 4 are compared with the clean-sheet,
  win and loss runs at game end. The others are updated at year end from
  helpers at 0x254290 and 0x254380 that were not fully decoded.
- Which of the three Best XI, MVP and top-scorer sets is domestic,
  European or international (partly answered under Unconfirmed), and when
  `BestPlayer_YearEndUpdate` 0x2b9978 and `CBestPlayerManager` fill them.
- The u32 derby record at B(5)+0x46634 (8 bytes, `pwkRec_GetDerbyMatch`
  0x254108, updated by `pwkRec_UpdateDerbyMatch` 0x254900 after each
  match). It was found but not decoded and may be a head-to-head record
  against your rival club.
- The 1,023-bit once-only event-flag set at B(0)+0x29c (`pwkGen_GetOO`
  0x244658, `SetOO` 0x2446c0, used for example from
  `PwkCallbackCommand_ClubEditEnd` at 0x110ba0) and the EVS event flags
  set by `jmRec_SetFlag_*Streak*` (SIMPRG 0x15ee38 and the three after
  it) probably mark story and record milestones. Their meanings were not
  traced.
- Which condition decides the three entry-bit sets in 0x113428 (the
  function takes an argument in a0, tested at 0x113458, and the loop that
  picks an entry was not read), who calls it, who calls
  `pwkRec_SetEUMvp_TeamUserOnly` 0x254e38, and the meaning of DivShift
  value 3 (the field range is 0 to 3).
- When the SIMPRG year-end pass that rewrites the UEFA and world tables
  runs (which month), and what feeds the temporary buffer it reads from.
- Whether the LMASTER third-tier edition changes any offset above. Block
  5 grows only at its end, but the competition-record pools were not
  re-checked on a patched executable.
- Lifetime counters (total matches, goals, trophies across seasons) were
  not found. If they exist outside blocks 0, 1 and 5 (block 3 leagues,
  block 4 town, block 6 schedule and camps, block 9) they were not
  searched. Block 6 +0x1cc0 (32 bytes, camp-free level per region) and
  +0x1c80 (64 flags of overseas conquest) were noticed in the fields
  table and left undecoded.
- Whether a Load, a New Game or the attract demo is ever seen mid-frame
  in a half-written state, and whether cancelling the attract demo with
  a button leaves the demo flag 0x34d43c at 1 (the script's clear at
  0x208 may be skipped).
- Whether rank ties share a value in the entry result list, and whether
  the second column of the game result is the shoot-out, are unverified.
- The Japanese build uses different code addresses and a different static
  root global (`lui 0x39 / lw -0x36b8` per `JAPANESE_RELEASE.md`, that is
  0x38c948), so every address in this section is for the PAL release
  only.
- Nothing here was checked in a running emulator. The save-state test in
  `SAVE_FORMAT.md` (Nexxus's report, 2026-10-27) covers the block chain
  and the club status only.

### Checking the claims

Run each command from the repo root. The first three show the root
pointer and its lifetime, the others show the record writer, the run
counters and the year-end rewrite of the UEFA table.

```bash
# the root: stored at 0x21d65c (sw a2, 0x9a8(s1)), cleared in DeletePwork at 0x21d6c8
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_DeletePwork
# Pwk.Create at 0x0010 is the first real command, Pwk.Delete at 0x1a20 is the only delete
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB | grep -E "Pwk\.(Create|Delete)"
# past record = block 5 + 0x260 + compe*0x98, compe < 0x31
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkRec_GetCompePastRecord
# calcCompetetionFinish: numheld sh at 0x206254, myrank sb at 0x2062e4, entries sh at 0x2062f4
python SRC/sles_disasm.py ISO/SLES_541.51 addr 2062e0 20
# history: place byte at 0x206370, season index (pwkGen_Keika = year - 0x7d6) at 0x20637c
python SRC/sles_disasm.py ISO/SLES_541.51 addr 206364 10
# qualification flags: the clears and sets are in 0x113428, not in Finalize 0x113408
python SRC/sles_disasm.py ISO/SLES_541.51 addr 113428 14
# UEFA table written in play: sh at 0x15102c, sb at +2 at 0x15103c
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 151000 22 --sles ISO/SLES_541.51
```

## Events, mail and news flags

The event, mail and news state of a career sits in the career work area
(the "pwork", block 0), which is heap memory. The event manager in
`SIMPRG.REL` also keeps a table of pointers into that area at a fixed
address in the executable (`EvsWork`, 0x5eec00). Story beats show up
here as a record's last-fired date, as a flag byte, or as a mail in the
inbox. Nothing in this section was run in the emulator: every claim
comes from the disassembly, the developers' field table or the event
tables on the disc. All addresses are the PAL release. "SIMPRG.REL
0x..." addresses are overlay file offsets, as printed by `snr2.py dis`.

Rows in the main table are confirmed in the code. Everything that is
only partly settled is in [Unconfirmed](#unconfirmed).

### Table

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer | static | pwork root (`Param::PlPworkTask`) | Static pointer to the career work object (0x5c bytes). It is set once by `Pwk.Create`, the first command of the root script, so it is non-zero from boot, through logo, title, demo, VS mode and career. It is NOT a "career present" or "title screen" detector. The content behind it (date, money, event slots) is blank until New Game or Continue, so gate on a content check, not on this word. Block k address = u32@(pwork+0x1c) + u32@(pwork+0x28+4k), for k = 0..10. All 11 blocks are present in retail. Everything below in block 0 starts from here. | **confirmed**. `plPwork_GetPwork` 0x21d6e0 (`lui 0x39 / lw 0x9a8`), stored at 0x21d65c in `plPwork_CreatePwork` 0x21d628, cleared at 0x21d6c8 in `plPwork_DeletePwork` 0x21d698. `Pwk.Create` is at script offset 0x0010 of `DAT/SEQ/ROOTMAINSEQ.SQB`, before the logo and the title. `Pwk.Delete` is only at 0x1a20, behind `BranchIfZero` at 0x1970 that returns to the title, so it does not run in normal play. The same chain is used in `SAVE_FORMAT.md` and was tested in PCSX2 (Nexxus, 2026-10-27, as recorded there). |
| 0x5eec14 | 4 | u32 pointer to array of 8-byte records | static pointer, heap records | EVENT last-fired slots | Slot for EVENT record i is at [0x5eec14] + 8*i, i = 0..381 (382 records). Slot layout: u16 year at +0 (the season's first year, 0 = never fired), u8 month at +2 (1-12), u32 turn within the month at +4 (0-7). +3 and +6 are padding. The year is 2005 for a slot stamped during the opening playoffs and 2006 or later afterwards, so only test it for non-zero. Stamped when the event handler object is created, not when the player answers. A once-only event tests exactly `u16@slot != 0`. Equals block 0 + 0x21b0 + 8*i. An out-of-range id maps to slot 0, so slot 0 can be stamped by a bad id. | **confirmed**. Cell = `EvsWork`+0x14, written at `SIMPRG.REL` 0x12903c to 0x129068 with EvData + 0xc08 (EvData = block 0 + 0x15a8, from `pwkGen_GetEvData` 0x244cb0). Id-to-slot map 0x12e670: type = id >> 24, index = id & 0xffffff, type 1 limit 0x17e, slot = [cell] + (index << 3). Index clamp 0x12e1e0 sets an out-of-range or negative index to 0 (it does not return null). Stamp at 0x12e758 (called from 0x12b648 in the request dispatcher 0x12b580) writes `lhu` year at +0, `lbu` month (PlDate+3) at +2 and the word PlDate+4 at +4. Once-only test in 0x12e220 (`lhu` at 0x12e248). The save serializer stores the slot as 14-bit, 4-bit and 4-bit fields. |
| 0x5eec18 | 4 | u32 pointer to array of 8-byte records | static pointer, heap records | NEWS last-fired slots | Same slot layout. NEWS record i is at [0x5eec18] + 8*i, i = 0..367 (368 records). Equals block 0 + 0x2db0 + 8*i. | **confirmed**. Cell = `EvsWork`+0x18 holding EvData + 0x1808 (0x12904c). Type 3 in the id-to-slot map 0x12e670, limit 0x170 (0x12e728 to 0x12e734). |
| 0x5eec1c | 4 | u32 pointer to array of 8-byte records | static pointer, heap records | MAIL last-fired slots | Same slot layout. MAIL record i is at [0x5eec1c] + 8*i, i = 0..443 (444 records). Equals block 0 + 0x39b0 + 8*i. | **confirmed**. Cell = `EvsWork`+0x1c holding EvData + 0x2408 (0x129054). Type 2 in the id-to-slot map 0x12e670, limit 0x1bc (0x12e70c, 0x12e71c). |
| 0x5eedf8 | 4 | s32 | static | Event scene variable: Yes/No answer (`EvsWork`+0x1f8) | Last Yes/No answer in an event scene. 1 = Yes, 0 = No or never answered (the two cannot be told apart). Value 1 selects the Yes scene-type override (EVENT record +0xe8, else +0xec). Left over after the scene ends. | **confirmed**. Readers at `SIMPRG.REL` 0x12a5dc, 0x1351a8 and 0x1352ec. Writers are small handlers entered through the table at 0x23a180 (9 words) from the setter 0x139628: 0x13964c stores 1, 0x13965c stores 0. The dialog result is turned into 1 (Yes) or 2 (No) at 0x146ad4 and 0x146adc and applied through the setter at 0x146b0c. |
| 0x5eedfc | 4 | u32 | static | Event scene variable: variant (`EvsWork`+0x1fc) | Which of six variants was picked, 0-5. Indexes the scene-type fields +0xf0..+0x104 of the EVENT record, and is passed as the camp theme to `pwkSche_SetCampThema`. Left over after the scene ends. | **confirmed**. Readers at `SIMPRG.REL` 0x12a5fc (bounds-checked `sltiu` below 6, then a jump table at 0x238780, reached only when flags & 0x1c is set and flags & 2 is clear) and 0x135000 (byte read). Writers 0x139668 to 0x1396b4 store 0, 1, 2, 3, 4 and 5 (table codes 3 to 8). Which dialog produces codes 3 to 8 was not traced. |

### Pointer chains and stability

The path to block 0 is the same for every entry. In pseudo-steps:

1. pwork = u32 at 0x3909a8 (non-zero from boot).
2. base = u32 at pwork+0x1c.
3. off0 = u32 at pwork+0x28.
4. block 0 = base + off0.
5. EvData = block 0 + 0x15a8.

| Entry | Chain | valid_when | stable_across |
|---|---|---|---|
| pwork root 0x3909a8 | Static word. The pointed-to object is `new(0x5c)` bytes. The data buffer at +0x1c is allocated with `FcEuroMalloc` in heap block 6. | Non-zero from boot, so the word alone says nothing about a career. Gate on content that only a career has (for example the PlDate year at block 0 + 0x88, which is blank until New Game or Continue). Also read u32@(pwork+0x1c) != 0. Byte@(pwork+0x18) is the ext-work flag and stays 0 in retail (`prepareExtWork` 0x21d980 has no caller), so the guard is defensive only. It does not tell a match from a menu. | Constant for the whole boot. `PwkCallbackCommand_Create` 0x110498 runs once (gated by the latch word 0x35c970), `Pwk.Delete` does not run in normal play, and New Game (0x110a60) and Load re-initialise or decode block 0 in place without a new allocation. So the pwork address, the +0x1c base and every block offset are fixed from boot until reset. The block shuffle (`plUty_ShuffleUint8` 0x235270, only call site 0x21d774 in the constructor 0x21d6f0) runs once per boot. Whether the offsets are the same on every boot is not settled (see Still unknown), so do not hard-code them. Re-reading the chain each frame is defensive, not required. |
| Last-fired slots, pointer cells 0x5eec14, 0x5eec18, 0x5eec1c | Records are in block 0: EVENT = EvData + 0xc08, NEWS = EvData + 0x1808, MAIL = EvData + 0x2408, i.e. block 0 + 0x21b0, +0x2db0, +0x39b0. The cells are written when the manager is constructed (`SIMPRG.REL` 0x129018, singleton created at 0x128f80). | A career is loaded and the event manager has been built. Before that the cells are 0 or left over, and nothing clears them (the teardown at 0x128fc8 does not). Check that [0x5eec14] == block 0 + 0x21b0, or skip the cell and use the full chain. Not meaningful on the title screen, launcher or viewers. | Cells are fixed addresses. Records survive save and load (EvData is part of block 0, zeroed by `pwkGen_InitEvData` 0x244ce0 at career creation). Contents persist across frames, menus and matches within a career. Block 0 does not move within a boot, so a cell that was set once keeps pointing at the right place (inference, not sampled). A repeatable event's slot is overwritten with the latest date, a once-only slot goes 0 to non-zero once. Writes happen only during turn processing. |
| Scene variables 0x5eedf8, 0x5eedfc | Static addresses inside `EvsWork`. No pointer chain. | Always readable (executable global). They reflect the latest answer only after the Yes/No dialog closes (`SIMPRG.REL` 0x146b0c) and only mean something during or just after an event scene. | Fixed address across frames, screens, overlay loads and seasons. The value persists after the event ends until another answer command overwrites it. Not saved (no `SAVEPRG.REL` reference), so a reset or save state leaves it stale. |

### RetroAchievements notes

- The pwork word at 0x3909a8 is non-zero from boot, so it is not a
  "no career" test. Pair every event or flag read with a content check
  (a PlDate year or a save-point field in block 0) instead.
- Best story-beat key: a once-only EVENT's last-fired slot. The year
  field (u16 at slot+0) goes from 0 to non-zero and stays. The slot
  address is [0x5eec14] + 8*i, where i is the EVENT record index.
  Once-only events are tested by the game with exactly this check.
  Prefer the full chain over the cell at 0x5eec14, or compare the two
  as a sanity check.
- Do not test the year for a value such as 2006 or later: a slot
  stamped in the opening playoffs holds 2005. Test non-zero only.
- Beats listed from the event tables (empirical, from `evsdatabin.py`
  columns, not re-verified in the code): EVENT 322 to 345 (manager and
  department tutorial events, once-only), EVENT 94 to 101 (stadium and
  Club House unlock announcements), EVENT 284, 285 and 286 (10th, 20th
  and 30th derby win), EVENT 296 (youth-training milestone). Check the
  event table before keying on any of these.
- A repeatable event's slot holds the last date. Compare the year,
  month and turn with the previous frame and do not test for non-zero.
- The slot is stamped when the event is created, before its scene
  plays, and whether or not the player watches it. It records that the
  event started, not that the player answered.
- Type 4 events (scouting, transfers, loans) have no table record and
  write no slot (`0x12e670` returns null for type 4). Do not look for
  them here.
- Yes/No answers at 0x5eedf8 are only meaningful at the moment a
  specific event finishes. Combine with that event's fired slot and
  edge-detect the 0 to 1 change. The value 0 cannot tell "No" from
  "never answered".
- Gate scene-variable reads on an event being active. They hold stale
  values afterward.
- Japanese release: the pwork global moves there (`lui 0x39 / lw
  -0x36b8` per `JAPANESE_RELEASE.md`, i.e. 0x38c948). All addresses
  here are PAL only.

### Unconfirmed

Nobody should build on these as written. Where the two checks
agreed on a corrected form, that form is noted so a later pass can
promote it.

| Finding | Why it is not in the table |
|---|---|
| EvsWork pointer table, 0x5eec00 | Agreed form: the pointer area is +0x0 EVENT table, +0x4 NEWS table, +0x8 MAIL table (loaded read-only files), +0xc EvData base (block 0 + 0x15a8), +0x10 to +0x2c data-area pointers (EvData + 0xc00, 0xc08, 0x1808, 0x2408, 0x3408, 0x3708, 0x3a28, 0x3c68; the stores at 0x129040 to 0x129068 are read). The original size of 52 bytes is wrong: the struct is at least 0x204 bytes (16-bit stores up to +0xea0 were seen). The "+0x30 random byte" is only read, never written, in `SIMPRG.REL`: unverified. |
| Event flag bytes, 342 used | Agreed form: 0x5eec20 is a pointer cell, flag n is the byte at [0x5eec20] + n, equal to block 0 + 0x49b0 + n. Index 0 means "none" and tests true. Indexes at or above 0x156 (342) are clamped to 0. Set to 1 by `SetEventFlag` 0x124408, cleared by 0x124448. The allocation is 768 bytes (one check only). Treat as unconfirmed until the cell's staleness is settled. |
| Story flags 244, 292, 294, 295 | Agreed form: the flags are transient, not permanent milestones. `SIMPRG.REL` 0x124488 clears every flag whose entry in the u32 table at 0x1d82e0 equals its argument. It is called from 0x12a348, which runs inside a module destructor (not a constructor), so the flags are cleared when an event module is torn down. Table values: 244 and 292 map to 4, 294 to 10, 295 to 11. Latch the 0 to 1 edge. Setters: records 264 to 270 set 244 (required by 214), 305 sets 294 (required by 306), 303 sets 295 (required by 304), 346 sets 292 (no reader). Which in-game timing the values 4, 10 and 11 correspond to is not confirmed (turn start, month end and year end is a guess). |
| Code-set flags 317, 318, 322 | Agreed form: set by `SetBigHitGoodsId` 0x12f7d0 (317), `SetBigDisGoodsId` 0x12f7f0 (318) and `SetPastMonthBalance` 0x12f770 (322, when the month's balance is negative). All three are in group 4 of the clear table, so they are transient. The goods ids are stored in the evdata store, not at `EvsWork`+0xc4 or +0xc8, and the two checks disagree on the exact offset (block 0 + 0x5234 or +0x52d4), so no goods-id address is given. No direct caller of `SetPastMonthBalance` was found, so when 322 is set is unverified. |
| Salesman item flags 331 to 336 | Agreed form: flags set by `CEvsJob_SuccessSales` 0x132318 through the {flag, event} table at 0x1d8c98 (331 with 167, 332 with 171, 333 with 175, 334 with 182, 335 with 186, 336 with event 0) and cleared by `CEvsJob_EndSales` 0x1323e0 through the table at 0x1d8cc8. Flag 336 is never set in retail. At match setup only the highest set flag's boost applies (`PlGiTask::SetTeamData`, 0x2102d0). The "8 turns later" delay was not traced. |
| Facility mirror flags 2 to 113 | Agreed form: `Inst_SetEventFlag` (`SIMPRG.REL` 0x1565a0) clears flags 2 to 0x71 inclusive then sets them from stadium, site and clubhouse state, so the range runs to block 0 + 0x4a21, not +0x4a20. Flags 6 and 7 come from the clubhouse level, not the stadium. MAIL 89 to 294 require flags 2 to 209 but flags above 0x71 are set elsewhere. No caller of `Inst_SetEventFlag` was found, so when it runs is unverified. These are derived mirrors and are not milestones. |
| Per-squad-player event flags | Agreed form: 0x5eec24 is a pointer cell. Flag bytes are at [0x5eec24] + slot*0x20 + flag, slot 0 to 24, flag 0 to 14, equal to block 0 + 0x4cb0 (0x320 bytes). `SetPlayerFlag` 0x12ce50 takes a player and finds the slot by matching the player id in the squad; the clearer and getter take a slot. The getter returns 0 for an empty slot. `jmNT_FreeCheck` (`SIMPRG.REL` 0x160c50) sets flags 0xd, 0xe and 0xa after `getChampionTeam`, but the meaning of the 15 flags as a whole is not settled here, so do not use them. |
| EVDATA store (last event ids, branch collapse, sold-out goods) | Agreed form: 0x5eec2c is a pointer cell to the store at block 0 + 0x5210 (0x800 bytes, from the `pwkGen_InitEvData` memset of 0x4468 = 0x3c68 + 0x800). Offsets from the store: u32 last event id per squad slot at +0x1f4 + 4*slot (slot 0 to 24), u32 manager id at +0x274, u32 coach id at +0x278, 12-byte sold-out goods record at +0x268, u8 branch-collapse flags at +0x27c + i (i below 13). The 0x800 boundary and the id encoding (type<<24 or index) were not confirmed. The ids are stored when the event object is created, not when it ends. |
| Mail inbox, 50 entries | Agreed form (the size, not the layout, was corrected): 50 entries of 0x9c bytes, 0x1e78 = 7800 bytes in total (not 3900), at block 0 + 0x5a10. Entry +0x00 u32 mail id (0 means unused), +0x0c u16 flags (bit 0 read, bit 1 replied, bit 2 has-body), +0x0e u16 counter decremented while non-zero. Unread count = entries with id != 0 and (flags & 1) == 0. The fields +0x04 to +0x08, +0x10 and +0x14 (index, prev, next, type, date, work values) were not re-derived. The "timing 0x10" class flag was not seen in the cited functions. The decrement loop at 0x166728 has no caller found in `SIMPRG.REL`, so when the counters change is unverified. |
| today_mail_num, block 0 + 0x7888 | Do not use it as a mail-arrival counter. A 16-bit signed field with that name exists right after the inbox (the save serializers store it as signed 16 bits). The only code that touches it is a getter at 0x166698, a zero at 0x166784 and `pwkMail_InitMailData`. No increment exists in any overlay or in the executable, and those functions have no callers found. |
| News stock and boxes | Agreed form: news struct = block 0 + 0x788c. Box t is at news + t*0xc3c (0xc3c is the stride, not an offset), 12 boxes (9 turn boxes, 3 special) ending at news + 0x92d0. Each box is 0xc3c bytes: a 0x10-byte header and 7 bodies from box + 0x18. The stock is 50 bodies of 0x1bc bytes at news + 0x92d0; a body is empty when its u32 at +0 is 0, and the s16 at +0x10 counts down. The other body fields come from the docs, not the code. Newspaper content is volatile, so it is a poor achievement source. |

### Still unknown

- The load base of `SIMPRG.REL` on a given run. The static registry at
  0x35ed98 (count at +0, 12-byte slots from 0x35eda0: name pointer,
  header = load base, check word) is the way to find it at run time.
  0xc75000 is an observed base (`ECONOMY.md`, `WIDESCREEN.md`), not
  derived. The event manager singleton (`SIMPRG` data 0x1d8848) is
  therefore not at a known fixed address, so "event module running now"
  and "current event id" cannot yet be read from a fixed place.
- Whether the block offsets, and so every block address, are the same
  on every boot. The shuffle state at 0x569dc0 starts at the constant
  0x12345678, but other draws before `Pwk.Create` were not ruled out.
  Compare u32@(pwork+0x28+4k) across two boots.
- Whether the cells at 0x5eec0c to 0x5eec2c are refreshed when a
  different career is loaded, or only when the manager is constructed.
  Block 0 does not move within a boot, so they should stay valid, but
  nothing cleared them and no one sampled them.
- What the 15 per-player flags mean as a whole, and which in-game timing
  the clear keys 4, 10 and 11 of flags 244, 292, 294 and 295 stand for
  (and whether those timings always construct the event module).
- The exact sizes of `PlNewsBody` and `PlNewsBox` as game constants,
  and which function increments `today_mail_num` (none found).
- The contents of the first 0xc00 bytes of EvData (event request queue)
  and the counter at EvData + 0xc00 (block 0 + 0x21a8, a pending-request
  count, not traced). Also `_evreqbuf` at block 0 + 0x31c (50 entries of
  72 bytes) and the disable counters at block 0 + 0x11ec, +0x126c and
  +0x12ec, read through `plDis_IsDisable` (executable 0x2e9368).
- The meaning of each facility mirror flag index, and of `EvsWork` +0xb4
  and +0xb8 (negotiation result), which were not checked.
- Whether any EVENT record fires during the opening playoffs (2005
  turns 92 to 95), which would stamp a year of 2005.
- Type 4 events (scouting, transfers, loans) write no fired slot. A
  reliable signal for "signed a player" or "offer accepted" should come
  from the roster or finance data (another domain).
- Everything here is static analysis. The first in-game sample should
  check that the chain resolves and that a once-only slot goes from 0 to
  non-zero when its event fires.
- The EVENT record fields (+0xd8 flag to set, +0x9c and +0xa0 required
  flags, +0x74 forbidden flag) come from `EVSDATABIN_FORMAT.md` and a
  table scan, and the claimed event numbers were re-scanned only once.

### Checking the claims

```bash
# Pwk.Create is the first command (0x0010); Pwk.Delete (0x1a20) is behind the branch at 0x1970. Takes about a minute.
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB | grep -E "Pwk\.(Create|Delete)|^ *1970 "
# the pwork getter: lui 0x39 / lw 0x9a8
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21d6e0 6
# pwGet: an offset word of 0xffffffff returns the bare base (delay-slot lw at 0x21da7c)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 16
# id-to-slot map: type = id>>24, limits 0x17e / 0x1bc / 0x170, cells EvsWork+0x14, +0x1c, +0x18
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x12e670 40 --sles ISO/SLES_541.51
# the stamp (u16 year, u8 month, u32 turn) and the clamp that sends a bad index to 0
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x12e758 30 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x12e1e0 20 --sles ISO/SLES_541.51
# the cells are filled with EvData + 0xc08, +0x1808, +0x2408 (EvData = block 0 + 0x15a8)
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x12903c 14 --sles ISO/SLES_541.51
# the Yes/No setter and its table of handlers (stores 1 and 0 at EvsWork+0x1f8)
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x139628 14 --sles ISO/SLES_541.51
```

## Still unknown

Each section above ends with its own "Still unknown" list and its own
"Unconfirmed" table. These five questions matter most for anyone
building on the rows, because each one decides whether a whole class of
reads is usable.

1. Are the block addresses the same on every boot? The block order is
   shuffled once, from a generator that starts at the constant
   0x12345678, but other draws before `Pwk.Create` were not counted.
   Until two boots are compared, every chain must read the block
   offsets and never hard-code them. All five sections list this.
2. Nothing was seen running. The first in-game sample should check that
   the chain resolves, that the date still shows the finished turn until
   the next turn starts, and that a once-only event slot goes from 0 to
   non-zero when its event fires. See the calendar and events sections.
3. Is a league's group slot always the same? Slots are handed out first
   free, so a live league-table chain needs a search by schedule id,
   which an achievement cannot do without a fixed slot. Only a runtime
   check settles it. See the competitions section.
4. Where does the game keep a national cup's state and its champion?
   No address for the finalists or for "cup won" was found, so a "win
   the cup" achievement can only use the player flags, which cover your
   own squad. See the national section.
5. When does the year-end pass run that rewrites the UEFA table and the
   club rankings, and which overlay base address does an event
   achievement need? The pass was not traced to a month, and the event
   manager object, with "current event id", has no fixed address while
   the overlay's load address is found at run time. See the competitions,
   records and events sections.

## Checking the claims

Run from the repo root. The first block reads the executable, the second
the overlay `SIMPRG.REL`, the third the data tables and the build
check. Each section's own "Checking the claims" lists the commands for
its rows.

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 14
python SRC/sles_disasm.py ISO/SLES_541.51 dis plMisc_SetTurn2Date
python SRC/sles_disasm.py ISO/SLES_541.51 dis CreateScheEuro
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkLg_Init
```

```bash
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x12e670 40 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x12ce18 10 --sles ISO/SLES_541.51
```

```bash
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB | grep -E "Pwk\.(Create|Delete)"
python SRC/natcal.py show DAT/PARAM/SCHEDULE_LIST.TBB
python SRC/gamever.py check ISO_JP
```

What they show:

- `plPwork_CreatePwork` stores the new work area at 0x3909a8 (`lui 0x39`,
  `sw ... 0x9a8`), and `pwGet` at 0x21da50 returns 0 only for a block
  number of 0xb or more.
- `plMisc_SetTurn2Date` writes the date record: year, turn, month, turn
  in month, week and weekend flag.
- `CreateScheEuro` stores the mode word and the object's address at
  0x390650; `pwkLg_Init` is the only writer of your league.
- The two `SIMPRG.REL` dumps are the event slot map (type = id >> 24)
  and the player flag setter.
- The script scan lists `Pwk.Create` as the first command and
  `Pwk.Delete` only at the end, so the root is non-zero from boot.
- `natcal.py show` prints the retail national calendar the national
  section quotes.
- `gamever.py check ISO_JP` reports whether each address the tools use
  also resolves on the Japanese build; it does not cover the field
  offsets inside the work area.
