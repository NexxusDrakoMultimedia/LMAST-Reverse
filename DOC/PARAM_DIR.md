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
| `REGULATION.TBB` | TBB, 1 table | `plRec_MatchRegulations` (`0x21dc60`), `SIMPRG.REL` list | 165 match regulations × **120 bytes**, indexed by `PLSCHE_GROUP`. **confirmed** (`0x21dd18`: `group * 0x78`) |
| `CLUBRESULT.TBB` | TBB, 1 table | `SIMPRG.REL 0x167e90` | 165 × **8 bytes** (u16 fields), same count as `REGULATION`. **confirmed** (`0x167f4c`: `i << 3`) |
| `STADIUM_DATA.TBB` | TBB, 1 table | `SLES 0x22ad20`, `SIMPRG.REL` demo list | 119 stadiums × **3 bytes**: roof, level, capacity (thousands). **confirmed** (`0x22add4`: `i < 0x77`, `i * 3`; readers in [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md#stadium_datatbb-stadiums)) |
| `SCHEDULE_LIST.TBB` | TBB, 4 tables | `pwkSche_CheckTourSucucess` (`0x256a20`), `SIMPRG.REL 0x1ce120` | one table per year of a 4-year cycle, 96 × u8 flags. **confirmed**, see below |
| `TRAINING_LIST.TBB` | TBB, 13 tables of bytes | `SLES 0x246540` (table 11), `SIMPRG.REL` lists | training menus. Table 11 (845 bytes) feeds `pwkMatchGrow_ClubRankCoe` (`0x246520`). Other tables not traced |
| `CAMP_LIST.TBB` | TBB, 2 tables | `SIMPRG.REL` lists `0x1cddb0`, `0x23d648` | training camps. Reader not traced |
| `CAMP_EXPLANE.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x225df8` | 612 bytes. Camp explanations (the name suggests message ids) |
| `CLUBEVENT.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x225dd0` | 960 bytes. Club events (`plClubEvent_*`) |
| `CLUB_RANK_SYSTEM.TBB` | TBB, 5 tables | `SIMPRG.REL 0x1509c8` through `ScheEuro_LoadModule` | 104 / 1,254 / 64 / 2,210 / 144 bytes. The club ranking: table 2 is 32 s16 world rank points by club rank (for clubs outside UEFA nations), table 3 is 65 × 34-byte rows giving the club rank by position in the nation or division. **confirmed**, see [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) ("How the club rank changes"). Tables 0, 1 and 4 not traced |
| `GROUP2COMPE.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x1cddd8` | 332 bytes (166 × u16?): schedule group to competition |
| `TOUR_LIST.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x1ce170` | 424 bytes (212 × u16?) |
| `MAPTEAM_LIST.TBB` | TBB, 1 table | `SIMPRG.REL 0x80694` | 242 × {u16 team, u16 flag}; flag 1 = the real 2005/06 top divisions (empirical), see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md#mapteam_listtbb). Reader not found |
| `TACTICS_FORMATION_SET.TBB` | TBB, 1 table | entry 11 of the `GetPreLoadData` list (`SLES 0x55b560`), and `SLES 0x55b2d8` | 8 formations × 8 bytes |
| `SPONSOR_BOARD.TBB` | TBB, 1 table | **not referenced by name** | 132 bytes, `01 02 03 ...` |
| `PLRESOURCECOMMON.PAC` | BINPAC, 5 TBB entries | `ePLRSRC` 0 | team facilities, formations, nations. See [`PLRESOURCECOMMON_FORMAT.md`](PLRESOURCECOMMON_FORMAT.md) |
| `PLRESOURCESIM.PAC` | BINPAC, 16 entries | `ePLRSRC` 1 | cities and weather, club records, nations, affiliations, scouts' exclusives, combinations, free agents, colours, ... See [`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md) |
| `SCHEDULE_SYSTEM.PAC/.HED` | BINPAC, 5 named TBBs | `ScheEuro_SubCtrl::requestLoad` (`0x209b50`) | `year_schedule_data`, `open_nation`, `make_list`, `PeriodName`, `savectrl`. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `SCHEDULE_COMPETITION.PAC/.HED` | BINPAC, 164 entries | `ScheEuro_LoadModule::Execute` (`0x208c50`), name table `0x390658` | one schedule per UID: games and pairings. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `SCHEDULE_TEAM_ENTRY.PAC/.HED` | BINPAC, 164 entries | as above | where each UID's entrants come from. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `PSCCOMMON.PAC` | BINPAC, 20 named `TBB1` `.sqb` scripts | `FC_EURO_PWK_CALLBACK`, table `0x35c908` | `PscCommon_PinfoInit.sqb`, `_seasonticket`, `_spectator`, ... PwkScript formulas, see [`SQB_FORMAT.md`](SQB_FORMAT.md) |
| `PSCGAME.PAC`, `PSCPRACTICE.PAC` | BINPAC, 2 entries | as above | copies of the first 2 `PSCCOMMON` entries |
| `PBDATA_EU.PAC` / `PBDATA_JP.PAC` | BINPAC, 4 entries | `FC_EURO_PWK_CALLBACK::PwkCallbackCommand_BpDataReadFile` (`0x110d50`), names at `0x35c968` | player database: 27,950 players, 3,000 managers, 1,000 scouts in bit-packed records. JP entry 1 is empty. See [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md). **confirmed** |
| `UNIFORM_NAME.BIN`, `UNIFORM_NAME2.BIN` | raw | **not referenced by name** | 27,950 × char[19] placeholders, see below |

The `uniform_name` string in `SLES` (`0x54ad98`) is a save-data field
name next to `editplayer` and `pinfo`, not this file.

The record layouts of the files with their own doc are in that doc. The
sections below cover the two files whose layout is known and that have
no doc of their own.

## `SCHEDULE_LIST.TBB`: which years a competition runs

**Confirmed** by `SLES 0x256a50`/`0x256b30`. The year (u16, e.g. 2006) picks
table `(year − 2006) mod 4` (years before 2006 use `year − 2003`). The
table's byte at index `i` (`i < 0x60`) has bit 0 set if competition `i`
runs that year. This matches internationals held every 4 years (World Cup
and European Championship years).

## `UNIFORM_NAME.BIN` and `UNIFORM_NAME2.BIN`

Both are 531,050 bytes = 27,950 records of `char[19]`. Every record in
`UNIFORM_NAME.BIN` is `"a"` padded with zeros. `UNIFORM_NAME2.BIN` is the
same except for 142 records (from index 6,205 on) that are `"0"`. Nothing
in the executable or the overlays names either file, so they are probably
unused placeholders for kit names.

## Still unknown

- The fields of the tables without a doc of their own: `REGULATION`,
  `CLUBRESULT`, `TRAINING_LIST`, the camp tables, `CLUBEVENT`,
  `GROUP2COMPE`, `TOUR_LIST`, `TACTICS_FORMATION_SET` and
  `CLUB_RANK_SYSTEM` tables 0, 1 and 4.
- What's still open in the files that have a doc is listed there, for
  example the schedule packs
  ([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#still-unknown)) and what each
  PwkScript in `PSC*.PAC` computes ([`SQB_FORMAT.md`](SQB_FORMAT.md)).
- The code that walks the `SIMPRG.REL` list holding `ClubEvent` and
  `Camp_Explane` (entries at `0x225dd0`, `0x225df8`).

## Checking the claims

```bash
python SRC/tbb.py info DAT/PARAM                     # tables, sizes, line sizes
python SRC/pac.py list DAT/PARAM/PLRESOURCESIM.PAC   # pack entries
python SRC/sles_disasm.py ISO/SLES_541.51 dis plResource_LoadRequest plRec_MatchRegulations
python SRC/sles_disasm.py ISO/SLES_541.51 addr 256a50 60   # SCHEDULE_LIST reader
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 7a18 12 --sles ISO/SLES_541.51   # load-list choice
```
