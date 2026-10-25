<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/PARAM`: career-mode parameter tables

`DAT/PARAM` (33 files, 5.5 MB, plus `CVS/`) holds the fixed data behind the
management game: the starting leagues and squads, computer teams, the
competition calendar, match regulations, training and camps. Nearly all of
it is loaded by the `Param::` code in `SLES_541.51` and by
`DLL/SIMPRG.REL` (the season mode).

The containers are all known: 23 `TBB1` table files
([`TBB_FORMAT.md`](TBB_FORMAT.md)), 8 BINPAC packs
([`PAC_FORMAT.md`](PAC_FORMAT.md)) and 2 raw `.BIN` files. `python
SRC/tbb.py info DAT/PARAM` and `python SRC/pac.py info DAT/PARAM` parse all
of them. This doc says which code loads each file and, where the reader has
been traced, what size its records are.

Loaders and the record sizes marked **confirmed** come from the game code
(addresses below). Everything else is **empirical**. The row counts in
the table are `size / line size` from the `TBL1` header, and the line size
is often not the record size (see
[`TBB_FORMAT.md`](TBB_FORMAT.md#what-the-container-does-not-tell-you)).

## How the files are loaded

There are three routes.

1. **`plResource` table** (`SLES_541.51`). `Param::ePLRSRC` indexes a table
   of 7 records of `0x94` bytes at `0x3909e8`. `+0x04` is the file name and
   `+0x90` holds the loaded data. `plResource_LoadRequest` (`0x21e620`)
   loads an entry, and `plResource_GetResourceData` (`0x21e7e0`) returns
   it:

   | `ePLRSRC` | File | Loaded by |
   |---|---|---|
   | 0 | `plresourcecommon.pac` | `FC_EURO_PWK_CALLBACK::PwkCallbackCommand_Create` (`0x1104f0`) |
   | 1 | `plresourcesim.pac` | the `SIMPRG.REL` load list (below) |
   | 2 | `plresourcegame.pac` | **not on the disc**. No code requests it |
   | 3 | `OteamMember.tbb` | `pwkOteam_RequestInit` (`0x24b720`), callback `0x24ac40` |
   | 4 | `PlRrsrc_InitTeamData.tbb` | `pwkRec_RequestInit` (`0x2534e0`), callback `0x253338` |
   | 5 | `team_init_data.tbb` | only `TESTPRG.REL`'s `HayasiTest` module. The game loads it through `CEDITPRG.REL`'s load list instead ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md)) |
   | 6 | `InitNatiData.tbb` | `pwkRec_RequestInit`, callback `0x253418` |

   Pack entries are read with
   `plResource_GetResourceDataBinPacTbbTbl(ePLRSRC, entry, table)`
   (`0x21e9e0`): BINPAC entry, then TBB table, then the `TBL1` data.
2. **By name when needed.** `fcEuroFile_GetFileResourceName` (`0x10e000`)
   with folder id 4, then `fcEuroRsrc_GetResource` (`0x112130`). The file
   must already be resident, so these files also appear in an overlay's
   load list.
3. **Load lists.** Arrays of `0x28`-byte entries with the file-name
   pointer at `+0x08`. `SIMPRG.REL`'s main list is at `0x214448`
   (`0x214d80` in the demo, chosen at `SIMPRG.REL 0x7a18`). `CEDITPRG.REL`
   has one at `0x1b288`, and `CTacticsManagerImplement::GetPreLoadData`
   (`0x2e3420`) returns the one at `SLES 0x55b3a8`. Other lists are only
   known by the address of the entry that names the file. Those addresses
   are given in the table below. The record is decoded in
   [`PRELOAD_DIR.md`](PRELOAD_DIR.md#the-load-list-record).

`CVS/ENTRIES` keeps the original mixed-case names (`OteamMember.tbb`,
`Stadium_Data.tbb`, ...) and revision numbers. `plresourcesim.pac` is at
revision 1.68 and `team_init_data.tbb` at 1.26.

## Directory overview

| File | Container | Loaded by | Contents |
|---|---|---|---|
| `OTEAMMEMBER.TBB` | TBB, 1 table | `ePLRSRC` 3 | computer-team squads (player, age, shirt, contract), see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md). **confirmed** |
| `PLRRSRC_INITTEAMDATA.TBB` | TBB, 3 tables | `ePLRSRC` 4 | starting divisions and last season's order per competition, see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md). **confirmed** |
| `INITNATIDATA.TBB` | TBB, 1 table | `ePLRSRC` 6 | UEFA rank and points, world rating per nation, see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md#initnatidatatbb-nations). **confirmed** |
| `TEAM_INIT_DATA.TBB` | TBB, 9 tables | `CEDITPRG.REL` list `0x1b288` (`CSelectTeamStyleModule`) → `pwkTeam_Init2` (`0x25eae8`) | the player's new club by league and team style: squad, youth team, manager, coaches, scouts, staff lists and the rival club, see [`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md). **confirmed** |
| `REGULATION.TBB` | TBB, 1 table | `plRec_MatchRegulations` (`0x21dc60`), `SIMPRG.REL` list | 165 match regulations × **120 bytes**, indexed by `PLSCHE_GROUP`: clubs, win bonus, prizes, bans, squad and substitution limits, places. **confirmed**, see [`REGULATION_FORMAT.md`](REGULATION_FORMAT.md) |
| `CLUBRESULT.TBB` | TBB, 1 table | `SIMPRG.REL 0x167e90` | 165 × **8 bytes**, one per schedule UID: how a final place is reported (league, cup round names, not ranked), the third-place match, the clubs. **confirmed**, see [`CLUBRESULT_FORMAT.md`](CLUBRESULT_FORMAT.md) |
| `STADIUM_DATA.TBB` | TBB, 1 table | `SLES 0x22ad20`, `SIMPRG.REL` demo list | 119 stadiums × **3 bytes**: roof, level, capacity (thousands). **confirmed** (`0x22add4`: `i < 0x77`, `i * 3`; readers in [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md#stadium_datatbb-stadiums)) |
| `SCHEDULE_LIST.TBB` | TBB, 4 tables | `pwkSche_CheckTourSucucess` (`0x256a20`), `SIMPRG.REL 0x1ce120` | one table per year of a 4-year cycle, 96 × u8 national-team flags per turn. **confirmed**; `natcal.py` reads and writes it. See below |
| `TRAINING_LIST.TBB` | TBB, 13 tables of bytes | the training module (`SIMPRG.REL 0x159998`, lists `0x23d618`, `0x23d690`), `SLES 0x246540` (table 11) | what each practice trains and its fatigue, facility and camp bonuses, match growth by position, ability groups and coaching, decline with age. **confirmed**, see [`TRAINING_FORMAT.md`](TRAINING_FORMAT.md) |
| `CAMP_LIST.TBB` | TBB, 2 tables | `SIMPRG.REL` lists `0x1cddb0`, `0x23d648`; `0x4bdd0` | the 153 training camps: city, nation, camp type, and the clubs of each area. **confirmed** in part, see [`CAMP_FORMAT.md`](CAMP_FORMAT.md) |
| `CAMP_EXPLANE.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x225df8`; `0xa4a80` | each camp city's description, message category 570. **confirmed**, see [`CAMP_FORMAT.md`](CAMP_FORMAT.md) |
| `CLUBEVENT.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x225dd0` | 48 × 20 bytes: an older copy of the club events, which the game takes from the executable instead ([`CLUBEVENT_FORMAT.md`](CLUBEVENT_FORMAT.md)). See below |
| `CLUB_RANK_SYSTEM.TBB` | TBB, 5 tables | `SIMPRG.REL 0x1509c8` through `ScheEuro_LoadModule` | 104 / 1,254 / 64 / 2,210 / 144 bytes. The club ranking: table 2 is 32 s16 world rank points by club rank (for clubs outside UEFA nations), table 3 is 65 × 34-byte rows giving the club rank by position in the nation or division; tables 0, 1 and 4 are the nation groups, the points per final place and the leagues the year end waits for. **confirmed**; `clubrank.py` reads and writes it. See [below](#club_rank_systemtbb-the-club-rankings-tables) and [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) ("How the club rank changes") |
| `GROUP2COMPE.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x1cddd8` | 166 × s16, each schedule UID's competition. Loaded but never read, see below |
| `TOUR_LIST.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x1ce170`, `0x4cab0` | 106 {region, club} pairs: the clubs a tour can play, by region. **confirmed**, see below |
| `MAPTEAM_LIST.TBB` | TBB, 1 table | `SIMPRG.REL 0x80694` | 242 × {u16 team, u16 flag}; flag 1 = the real 2005/06 top divisions (empirical), see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md#mapteam_listtbb). Reader not found |
| `TACTICS_FORMATION_SET.TBB` | TBB, 1 table | entry 11 of the `GetPreLoadData` list (`SLES 0x55b560`), and `SLES 0x55b2d8` | the tactics screen's 8 national presets: seven team tactics and a formation each. **confirmed**, see below |
| `SPONSOR_BOARD.TBB` | TBB, 1 table | **not referenced by name** | 132 bytes, `01 02 03 ...` |
| `PLRESOURCECOMMON.PAC` | BINPAC, 5 TBB entries | `ePLRSRC` 0 | team facilities, formations, nations. See [`PLRESOURCECOMMON_FORMAT.md`](PLRESOURCECOMMON_FORMAT.md) |
| `PLRESOURCESIM.PAC` | BINPAC, 16 entries | `ePLRSRC` 1 | cities and weather, club records, nations, affiliations, scouts' exclusives, combinations, free agents, colours, ... See [`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md) |
| `SCHEDULE_SYSTEM.PAC/.HED` | BINPAC, 5 named TBBs | `ScheEuro_SubCtrl::requestLoad` (`0x209b50`) | `year_schedule_data`, `open_nation`, `make_list`, `PeriodName`, `savectrl`. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `SCHEDULE_COMPETITION.PAC/.HED` | BINPAC, 164 entries | `ScheEuro_LoadModule::Execute` (`0x208c50`), name table `0x390658` | one schedule per UID: games and pairings. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `SCHEDULE_TEAM_ENTRY.PAC/.HED` | BINPAC, 164 entries | as above | where each UID's entrants come from. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `PSCCOMMON.PAC` | BINPAC, 20 named `TBB1` `.sqb` scripts | `FC_EURO_PWK_CALLBACK`, table `0x35c908` | `PscCommon_PinfoInit.sqb`, `_seasonticket`, `_spectator`, ... PwkScript formulas. Only the 8 detail-screen comment scripts are run, see [`SQB_FORMAT.md`](SQB_FORMAT.md#what-the-pwkscripts-compute) |
| `PSCGAME.PAC`, `PSCPRACTICE.PAC` | BINPAC, 2 entries | as above | copies of the first 2 `PSCCOMMON` entries; never run |
| `PBDATA_EU.PAC` / `PBDATA_JP.PAC` | BINPAC, 4 entries | `FC_EURO_PWK_CALLBACK::PwkCallbackCommand_BpDataReadFile` (`0x110d50`), names at `0x35c968` | player database: 27,950 players, 3,000 managers, 1,000 scouts in bit-packed records. JP entry 1 is empty. See [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md). **confirmed** |
| `UNIFORM_NAME.BIN`, `UNIFORM_NAME2.BIN` | raw | **not referenced by name** | 27,950 × char[19] placeholders, see below |

The `uniform_name` string in `SLES` (`0x54ad98`) is a save-data field
name next to `editplayer` and `pinfo`, not this file.

The record layouts of the files with their own doc are in that doc. The
sections below cover the files that have no doc of their own.

## `SCHEDULE_LIST.TBB`: the national-team calendar

**Confirmed** by `SLES 0x256a50`–`0x256c50`. The year (u16, e.g. 2006)
picks table `(year − 2006) mod 4` (years before 2006 use `year − 2003`).
Each table is 96 bytes, one per turn
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#turns)), and each byte holds
flags:

| Bit | Function | Meaning |
|---|---|---|
| 1 | `pwkSche_IsNationalMatch` `0x256b30` | national teams play (the globes on the Schedule screen, user report; `SIMPRG.REL 0x4dd84`) |
| 2 | `pwkSche_IsNationalFMatch` `0x256b90` | finals tournament: `SIMPRG.REL 0x160a48` takes it as the competition the call-up and release are for, the finals (45 Euro, 47 World, by `pwkGen_Keika` mod 4) instead of their qualifying (44, 46) |
| 4 | `pwkSche_IsNationalConvene` `0x256c50` | call-up: `SIMPRG.REL` `jmNT_CallCheck` `0x160b68` picks every squad |
| 8 | `pwkSche_IsNationalBreak` `0x256bf0` | release: `jmNT_FreeCheck` `0x160c50` sends the players back; with bit 2 it also asks `getChampionTeam` for the cup's winner |

The retail tables (turn: flags):

| Table | Years | Turns |
|---|---|---|
| 0, 2 | qualifying | 20, 26, 34, 36, 60, 68: 1+4+8; 88: 1+4; 89: 1+8 |
| 1 | Euro National Cup | the same up to 36; 88: 2+4; 89–91: 1; 92–93: 1+2; 94: 1+2+8 |
| 3 | World National Cup | the same up to 36; 88: 2+4; 89–91: 1; 92–94: 1+2; 95: 1+2+8 |

A season starting in 2009 or 2025 uses table 3, a World Cup year, and
one starting in 2007 table 1, a Euro year (user report). Copies sit in
`PRELOAD/SIMLOCALMEM0`–`6.PAC` (entry 31). `patch_disc.py --mod
national-cups` moves tables 1 and 3 a turn earlier
([`LMASTER_MOD.md`](LMASTER_MOD.md)).

**Empirical**, all four tables on both releases (`python SRC/natcal.py
info DAT/PARAM`):

- The match flag is on exactly on the turns the national cups
  (competitions 44–47) play in `SCHEDULE_SYSTEM.PAC`: a cup's year row of
  cycle *c* (1–4) goes to table *c* − 1, and its second-year turns to the
  next table ([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)).
- Every match turn lies between a call-up and its release, which may
  both be on the match turn itself (the qualifying dates are 1+4+8).
- Only the finals years (tables 1 and 3) hold the finals flag, and there
  it is also on the call-up and the release that frame the finals.

**Editing.** `python SRC/natcal.py set <in> <out> <table>:<turn>:<flag>=<0|1>`
sets the finals, call-up and release flags (for example
`3:88:callup=0 3:87:callup=1 3:87:finals=1` calls the World Cup squads up
a turn earlier); the mod editor's National calendar tab does the same.
Both refuse a calendar that breaks the rules above. The match flag isn't
edited: it follows the schedule, which `national-cups` moves together
with the calendar. Given an edited `SCHEDULE_LIST.TBB` as a target,
`national-cups` moves the target's tournament years a turn earlier the
same way (matches, finals and release; the call-up stays) and `--copies`
writes the result into the `SIMLOCALMEM` packs. Not tested in game.

## `GROUP2COMPE.TBB`: each schedule's competition, unread

One table of 166 s16. **Empirical** (`python SRC/schedule.py info
DAT/PARAM`, last line; the Japanese file is the same): entry *n* is the
competition of schedule UID *n* − 1 for 144 of the 164 UIDs. The other
20 are the group stages of the European League (UIDs 59–66), the Euro
National Cup (98–101) and the World National Cup (114–121), which give
the competition before theirs: 33 (the European League Round), 44 and 46
(the cups' primaries). Entry 0 is 0 and entry 165 is 72, one past the
last competition.

**Confirmed: nothing reads it.** The camp screen's module loads it (load
list `0x1cdd30`, entry 4) and keeps its handle at `+0x8f8`
(`SIMPRG.REL 0x47b18`). The only code that reads the table, the getter at
`0x4bf30` (entry *n* as a u16), is never called: no `jal`, pointer or
relocation names it. The same module's getters for the camps' `+0x06`
and `+0x0a` (`0x4bea0`, `0x4bfd0`) are dead code too
([`CAMP_FORMAT.md`](CAMP_FORMAT.md)).

## `CLUB_RANK_SYSTEM.TBB`: the club ranking's tables

Five tables, which the club ranking (`SIMPRG.REL`, loader `0x150c10`–
`0x150d08`) keeps at object `+0x18`, `+0x20`, `+0x2c`, `+0x34` and
`+0x3c`, each with its row count after it. Tables 2 and 3 are described
with the ranking in [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far).
`python SRC/clubrank.py show DAT/PARAM/CLUB_RANK_SYSTEM.TBB
DAT/MESSAGE/MES.PAC` prints all five, with the competitions' names and
the positions each club rank gets; `set` edits tables 1–3, and the mod
editor's Club ranking tab does the same. The Japanese file is the same.

| Table | Rows | Row | Reader (**confirmed**) | What the rows hold (**empirical**) |
|---|---|---|---|---|
| 0 | 52 | `{u8 nation, u8 group}` | `0x151210` collects the rows whose group is the one asked for and sorts them (`qsort`) | nations 1–52; group 0 for the six league nations, 1–4 for the others (12, 12, 19 and 3 nations) |
| 1 | 33 | `{s16 competition, s16 kind, s16 tally, u8 points[32]}` | `0x152128`, below | kind 0: the European competitions 34–36; kind 1: the national-team cups 45 and 46; kind 2: the same three European ones again (tally 1) and each league nation's two divisions and two cups (tally 2; first division winner 55 … 20th 25, second division 30 …, cup 25 …, league cup 10 …; European League 50, 35, 25, 25 …). One kind-2 row has competition −10, so it is never used |
| 2 | 32 | s16 | `0x151568` | world rank points by club rank, see [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far); 0, 5, 10 … 925 for ranks 0–31 |
| 3 | 65 | 34 bytes | the club rank by position, see [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) | – |
| 4 | 18 | `{s16 UID, s16 nation, s16 division, s16 0}` | `0x150dd8`: for each row, the year schedule of the UID (`getYearSchedule`) and its nation (`getNationFromScheCompe`); when the walk finds them done it marks the year (`+0xc` = 2) and the divisions are shifted (`pwkRec_SetDivShift_TeamUserOnly`, `0x150ecc`) | the six league nations' league UIDs: each first division (division 0) and both versions of its second division (1) |

**Table 1** (**confirmed**). `0x152128(object, tallies, count, kind)`
walks the rows of one kind. A row with a competition of 0 or more that
had a result this year (`0x1520e0`) gives `points[n]` to the club in
entry *n* of its past record (`pwkRec_GetCompePastRecord`), that is
final place *n* + 1. Each tally is 8 bytes with two u16 counters, at +2
and +4.

| Called from | Kind | Count | The points go to |
|---|---|---|---|
| `0x150528` | 0 | 52 | the club's nation (`plMisc_Club2Nati`), counter +2 |
| `0x1505c0` | 1 | 145 | the nation: a national team's through `plMisc_NatiTeam2Nati` (teams `0x1cc` and up), a club's through `plMisc_Club2Nati`; counter +2 |
| `0x150680` | 2 | 441 | the club, counter +2 when the row's tally is 1 and +4 when it is 2; the world rank points (`0x151568`) follow in the same pass |

So the European rows count twice: once for the nation (kind 0) and once
for the club (kind 2).

**Table 3's rows** (**confirmed**, `0x151ce0`). For a second division
(division 1) the game takes the row with nation slot −1 and the
division's size; for a first division, the row with the nation's slot
and the division's size, or a row of size −1, which is what nations
7–52 have. The size is the league UID's number of entrants
(`makeTeamEntryIDList`, `0x150ae0`, stored for the division at
`0x150b5c`). When no row matches, the caller (`0x151dc8`) skips the
division, so its clubs keep their ranks. The loader keeps the row count
(`+0x38`), so the table can grow.

The retail rows cover first divisions of 18 and 20 and second divisions
of 18–22, 24 and 26. For any other size, `python SRC/clubrank.py addrows
<in> <out> <division>:<size>` appends the missing rows (a first
division's for each nation slot 1–6), and `leaguesize.py build` and the
Season tab do it for a resized league: England at 22 gets six rows, its
second division at 22 and 24 has them already. The file grows by 34
bytes a row. A new row stretches the row of the nearest size of the same
slot (the larger on a tie) over the new size, so the top club keeps the
top rank and the bottom club the bottom rank. **Empirical:** built that
way from a neighbouring size, every retail row comes within one rank of
the real one at every position (the 18-club first divisions from the
20-club ones differ at 4–8 of 18 positions). The rule is this project's
choice, not the game's. A grown file isn't tested in game; the same
loader (`ScheEuro_LoadModule`) reads the schedule packs, which grow
without trouble.

## `CLUBEVENT.TBB`: an older copy of the club events

One table of 48 records of 20 bytes (10 s16; the TBB line size is 2).
**Empirical**: field 2 is 30001 in most records, field 6 a cost (100 to
10,000) and field 7 a small count (0–96), like the executable's offer
records' home popularity (`+0x06`), cost (`+0x14`) and gap (`+0x0b`).

The club events the game runs come from three tables in the executable
instead (**confirmed**), 46 events, described field by field in
[`CLUBEVENT_FORMAT.md`](CLUBEVENT_FORMAT.md) and edited with
`clubevent.py`. Their costs equal the TBB's field 6 for most records in
the same order (500, 500, 500 … 3000, 2000, 5000, 1000, 1000, 3000,
3000, 10000), but not all: the TBB has two records more and differs
around records 3, 10 and 27–37. So the file looks like an earlier
version of the executable's table.

`SIMPRG.REL` loads it with `Camp_Explane.tbb` (list `0x225d78`, entry 2;
handle at `+0x56c` of the module set up at `0xa4760`, which reads
`CAMP_EXPLANE` at `0xa4a80`). No code reading its records has been
found. Edits to club events belong in the executable's tables
([`ECONOMY.md`](ECONOMY.md#pr-events)). The Japanese file is the same.

## `TACTICS_FORMATION_SET.TBB`: tactics presets

The tactics screen's "Set Formation" menu offers eight national styles;
this table holds them, one 8-byte row each. `python SRC/formset.py show
DAT/PARAM/TACTICS_FORMATION_SET.TBB` lists them, and `set` edits them.

**Confirmed from the code:**

| Address | Symbol | What it shows |
|---|---|---|
| `SLES 0x2e334c` | `CTacticsManagerImplement` | takes the file as resource 11 of its list and hands it to `CTacticsLoader::setFormationData` (`0x2ed298`) |
| `SLES 0x2eff28` | `l_create_formationset_list` | one menu line per row, named by category 492 message 10001 + row (`CTacticsMessage` group 3, entry `0x15`) |
| `SLES 0x2f0318` | (the menu's cursor callback) | applies row *r* (`r × 8`) to the club's team style: byte 7 through `plTeam_FormationID2Formation` (the formation and its positions), bytes 0–3 to style `+0x5c`–`+0x5f`, byte 4 to `+0x61`, 5 to `+0x62`, 6 to `+0x60`; then shows message 20001 + *r*, the set's description |
| `SLES 0x2efc4c` | `CTacticsMenuFormationSetImplement::Execute` | on opening, saves the current style for a cancel and shows row 0, where the cursor starts |
| `SLES 0x3038e0`, `0x303938` | `CTacticsTeamTacticsEdit` | the tactics screen keeps its seven settings at `+0x584` + 4*i* and stores them to style `+0x5c`–`+0x62` in the same order; `0x3036c4` labels setting *i* with category 492 message *i* |

So the row's bytes are the screen's settings in order:

| Byte | Setting (message) |
|---|---|
| 0 | Attacking |
| 1 | Attack Speed |
| 2 | Attack Type |
| 3 | Attack Side |
| 4 | Pressure |
| 5 | Offside |
| 6 | Press Line |
| 7 | formation, an index of the 35 formations (`pbdata.FORMATIONS`) |

The team styles live in my-team data at `+0x4204` + style × `0x70`.
**Empirical**: the formations and settings fit the descriptions (English
4-4-2 "hi-tempo attacks" has Attack Speed 5; Italian 4-4-2 "breaking down
attacks" has Attacking 1 and Pressure 5; Spanish 4-5-1 "precision
passing" Attack Speed 1). Every setting is 1–5 except the Brazilian
set's Attacking, 6; the screen's own limits haven't been traced. The
Japanese file is the same. Copies sit in entry 0 of the
`PRELOAD/TACTICS*` packs.

## `TOUR_LIST.TBB`: tour opponents by region

One table of 106 `{u16 region, u16 club}` pairs. **Confirmed**: the camp
and tour screens' module loads it (load list `0x1cdd30`, entry 27, handle
at `+0x904`), and `SIMPRG.REL 0x4cab0(out, region)` clears 40 u16 slots
and copies in the club of every pair whose region matches, in table
order. Its caller (`0xa44d8`) takes the region from the screen's list
(the module's `+0x2028` plus the chosen line, less one).

**Empirical**: regions 0–12 hold 10, 8, 8, … 8 clubs: 0 Western Europe
(Tottenham, Marseille, Dortmund, Lazio, Valencia, Feyenoord, Glasgow
City, Porto, Basel, Brugge), 1 and 2 Central and Eastern Europe, 3
Scandinavia and the Baltic, 4 and 5 South America, 6 North Africa
(with Newcastle, Monaco, Kaiserslautern and Roma), 7 and 8 West and
southern Africa, 9 North America, 10 East Asia, 11 the Middle East and
12 Oceania. Five groups end with clubs from the six leagues. `python
SRC/tour.py show DAT/PARAM/TOUR_LIST.TBB DAT/MESSAGE/MES.PAC` lists them,
and `set` changes a pair. `python SRC/plrcommon.py show DAT/PARAM 3.0`
lists the 13 regions the game knows; whether these numbers are the same
regions isn't confirmed.

## `UNIFORM_NAME.BIN` and `UNIFORM_NAME2.BIN`

Both are 531,050 bytes = 27,950 records of `char[19]`. Every record in
`UNIFORM_NAME.BIN` is `"a"` padded with zeros. `UNIFORM_NAME2.BIN` is the
same except for 142 records (from index 6,205 on) that are `"0"`. Nothing
in the executable or the overlays names either file, so they are probably
unused placeholders for kit names.

## Still unknown

- In `CLUB_RANK_SYSTEM`: what table 0's groups change, and what the
  nation tallies and the clubs' two counters feed (the three weighted
  values of `0x151568`).
- Whether anything reads `CLUBEVENT.TBB`.
- The tactics sliders' limits, and which regions `TOUR_LIST`'s numbers
  are.
- What's still open in the files that have a doc is listed there, for
  example the schedule packs
  ([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#still-unknown)).

## Checking the claims

```bash
python SRC/tbb.py info DAT/PARAM                     # tables, sizes, line sizes
python SRC/pac.py list DAT/PARAM/PLRESOURCESIM.PAC   # pack entries
python SRC/sles_disasm.py ISO/SLES_541.51 dis plResource_LoadRequest plRec_MatchRegulations
python SRC/sles_disasm.py ISO/SLES_541.51 addr 256a50 60   # SCHEDULE_LIST reader
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 7a18 12 --sles ISO/SLES_541.51   # load-list choice
```
