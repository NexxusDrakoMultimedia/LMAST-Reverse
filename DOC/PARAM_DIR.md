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
   | 5 | `team_init_data.tbb` | no `LoadRequest` in `SLES`. `CEDITPRG.REL` lists it (below) |
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
   are given in the table below. The fields other than the name aren't
   decoded.

`CVS/ENTRIES` keeps the original mixed-case names (`OteamMember.tbb`,
`Stadium_Data.tbb`, ...) and revision numbers. `plresourcesim.pac` is at
revision 1.68 and `team_init_data.tbb` at 1.26.

## Directory overview

| File | Container | Loaded by | Contents |
|---|---|---|---|
| `OTEAMMEMBER.TBB` | TBB, 1 table | `ePLRSRC` 3 | computer-team squads (player, age, shirt, contract), see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md). **confirmed** |
| `PLRRSRC_INITTEAMDATA.TBB` | TBB, 3 tables | `ePLRSRC` 4 | starting divisions and last season's order per competition, see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md). **confirmed** |
| `INITNATIDATA.TBB` | TBB, 1 table | `ePLRSRC` 6 | per-nation start values, see below. **confirmed** |
| `TEAM_INIT_DATA.TBB` | TBB, 9 tables | `ePLRSRC` 5, `CEDITPRG.REL` list | 9 tables of u32 (3,168 / 864 / 432 / 384 / 216 / 216 / 12 / 18 / 120 words). Reader not traced |
| `REGULATION.TBB` | TBB, 1 table | `plRec_MatchRegulations` (`0x21dc60`), `SIMPRG.REL` list | 165 match regulations × **120 bytes**, indexed by `PLSCHE_GROUP`. **confirmed** (`0x21dd18`: `group * 0x78`) |
| `CLUBRESULT.TBB` | TBB, 1 table | `SIMPRG.REL 0x167e90` | 165 × **8 bytes** (u16 fields), same count as `REGULATION`. **confirmed** (`0x167f4c`: `i << 3`) |
| `STADIUM_DATA.TBB` | TBB, 1 table | `SLES 0x22ad20`, `SIMPRG.REL` demo list | 119 stadiums × **3 bytes**. **confirmed** (`0x22add4`: `i < 0x77`, `i * 3`) |
| `SCHEDULE_LIST.TBB` | TBB, 4 tables | `pwkSche_CheckTourSucucess` (`0x256a20`), `SIMPRG.REL 0x1ce120` | one table per year of a 4-year cycle, 96 × u8 flags. **confirmed**, see below |
| `TRAINING_LIST.TBB` | TBB, 13 tables of bytes | `SLES 0x246540` (table 11), `SIMPRG.REL` lists | training menus. Table 11 (845 bytes) feeds `pwkMatchGrow_ClubRankCoe` (`0x246520`). Other tables not traced |
| `CAMP_LIST.TBB` | TBB, 2 tables | `SIMPRG.REL` lists `0x1cddb0`, `0x23d648` | training camps. Reader not traced |
| `CAMP_EXPLANE.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x225df8` | 612 bytes. Camp explanations (the name suggests message ids) |
| `CLUBEVENT.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x225dd0` | 960 bytes. Club events (`plClubEvent_*`) |
| `CLUB_RANK_SYSTEM.TBB` | TBB, 5 tables | `SIMPRG.REL 0x1509c8` through `ScheEuro_LoadModule` | 104 / 1,254 / 64 / 2,210 / 144 bytes. Reader not traced |
| `GROUP2COMPE.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x1cddd8` | 332 bytes (166 × u16?): schedule group to competition |
| `TOUR_LIST.TBB` | TBB, 1 table | `SIMPRG.REL` list `0x1ce170` | 424 bytes (212 × u16?) |
| `MAPTEAM_LIST.TBB` | TBB, 1 table | `SIMPRG.REL 0x80694` | 968 bytes (484 × u16?) |
| `TACTICS_FORMATION_SET.TBB` | TBB, 1 table | entry 11 of the `GetPreLoadData` list (`SLES 0x55b560`), and `SLES 0x55b2d8` | 8 formations × 8 bytes |
| `SPONSOR_BOARD.TBB` | TBB, 1 table | **not referenced by name** | 132 bytes, `01 02 03 ...` |
| `PLRESOURCECOMMON.PAC` | BINPAC, 5 TBB entries | `ePLRSRC` 0 | team facilities, formations, nations. See [the packs](#plresourcecommonpac) |
| `PLRESOURCESIM.PAC` | BINPAC, 16 entries | `ePLRSRC` 1 | computer teams, transfers, mail. See [the packs](#plresourcesimpac) |
| `SCHEDULE_SYSTEM.PAC/.HED` | BINPAC, 5 named TBBs | `ScheEuro_SubCtrl::requestLoad` (`0x209b50`) | `year_schedule_data`, `open_nation`, `make_list`, `PeriodName`, `savectrl`. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `SCHEDULE_COMPETITION.PAC/.HED` | BINPAC, 164 entries | `ScheEuro_LoadModule::Execute` (`0x208c50`), name table `0x390658` | one schedule per UID: games and pairings. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `SCHEDULE_TEAM_ENTRY.PAC/.HED` | BINPAC, 164 entries | as above | where each UID's entrants come from. See [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |
| `PSCCOMMON.PAC` | BINPAC, 20 named `TBB1` `.sqb` scripts | `FC_EURO_PWK_CALLBACK`, table `0x35c908` | `PscCommon_PinfoInit.sqb`, `_seasonticket`, `_spectator`, ... |
| `PSCGAME.PAC`, `PSCPRACTICE.PAC` | BINPAC, 2 entries | as above | copies of the first 2 `PSCCOMMON` entries |
| `PBDATA_EU.PAC` / `PBDATA_JP.PAC` | BINPAC, 4 entries | `FC_EURO_PWK_CALLBACK::PwkCallbackCommand_BpDataReadFile` (`0x110d50`), names at `0x35c968` | player database. EU entry 1 is 3 MB (starts with a name, `Maik`); JP entry 1 is empty. Not decoded |
| `UNIFORM_NAME.BIN`, `UNIFORM_NAME2.BIN` | raw | **not referenced by name** | 27,950 × char[19] placeholders, see below |

The `uniform_name` string in `SLES` (`0x54ad98`) is a save-data field
name next to `editplayer` and `pinfo`, not this file.

## `OTEAMMEMBER.TBB`: computer-team squads

**Confirmed** by `pwkOteam_Init(TBL_FILEHEADER*)` (`0x24a6a0`), which runs
on load. It walks teams `3`–`441` (`PlTeam` ids, `slti 0x1ba`), 25 players
each, reading 16-byte records:

| Offset | Type | Copied to |
|---|---|---|
| `0x00` | u16 | squad slot `+0` (the player number) |
| `0x04` | u8 | slot `+2` |
| `0x08` | u8 | slot `+3` |
| `0x0C` | u8 | slot `+4` |

The other bytes are padding (the exporter wrote each field as a u32). 439
teams × 25 × 16 = 175,600 bytes, exactly the table size. The three bytes
are the age, shirt number and contract years. That is confirmed by
`UpdateConyear` and `pwkTeam_SetUnumberOpinfo`: see
[`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md), and `SRC/initteam.py` for a
reader.

## `PLRRSRC_INITTEAMDATA.TBB`: starting leagues

**Confirmed** by the load callback at `0x253338`, which hands each table to
its own function:

| Table | Size | Reader | Layout |
|---|---|---|---|
| 0 | 1,248 | `0x253228` | 6 leagues (`pwkLg_GetLeague` 0–5) × 2 divisions × `0x68` bytes. Each `0x68` block is passed to `plLg_EntryTeamSetToDiv` (`0x2e94c8`) as the division's team list: up to 26 u32 team ids, ending at a 0 |
| 1 | 7,168 | `0x2531b0` | 56 × `0x80`-byte records. The first 49 (`slti 0x31`) are passed to `pwkRec_SetPastRecordLastTeam` per `PLSCHE_COMPE`. The last 7 aren't read |
| 2 | 112 | `0x2532c8` | 56 × u16. The first 49 go to `pwkRec_GetCompeConventionRecordKeikayear` (the years since a competition was last held?) |

So table 0 decides which clubs start in which league and division. That is
the main thing [`GOALS.md`](../GOALS.md) wants a starting-season mod to
change. The field layouts and a reader with club names are in
[`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md).

## `INITNATIDATA.TBB`: nations

**Confirmed** by the load callback at `0x253418`. 145 records of 6 bytes
(870 = 145 × 6), for nations 1–145, copied into Pwork block 5:

| Offset | Type | Used for |
|---|---|---|
| `0x00` | u8 | nations 1–52 only |
| `0x02` | u16 | nations 1–52 only |
| `0x04` | u8 | all nations |

## `SCHEDULE_LIST.TBB`: which years a competition runs

**Confirmed** by `SLES 0x256a50`/`0x256b30`. The year (u16, e.g. 2006) picks
table `(year − 2006) mod 4` (years before 2006 use `year − 2003`). The
table's byte at index `i` (`i < 0x60`) has bit 0 set if competition `i`
runs that year. This matches internationals held every 4 years (World Cup
and European Championship years).

## `PLRESOURCECOMMON.PAC`

5 TBB entries. **Confirmed** readers (entry/table from the constant
arguments to `plResource_GetResourceDataBinPacTbb[Tbl]`):

| Entry.table | Rows × line | Reader |
|---|---|---|
| 0.0–0.8 | u32 tables | `plTeam_GetSiteDb`, `GetGrEquipsDb`, `GetStEquipsDb`, `GetChouseDb`, `GetDChEquipsDb`, `GetDAcEquipsDb`, `GetOfEquipsDb`, `GetStadiumDb`, `GetStAdvertiseDb` (club facilities, in table order) |
| 1.0 | 700 × 1 | `plTeam_FormationID2Formation` |
| 1.1 / 1.2 / 1.3 | 90 / 1,419 / 1,419 × 1 | `plTeam_PitchArea2Apos`, `AreaMatrix2AreaMy`, `AreaMatrix2AreaCom` |
| 1.4 / 1.5 / 1.6 | 32 / 8 / 26 × 1 | `plTeam_GetSystem2PosNum`, `GetPosNumLimit`, `GetAPosNumLimit` |
| 2.0 | 512 × 1 | `plPinfo_CalcHexAbil` |
| 3.0–3.5 | 13 / 146 / 146×2 / 83 / 146 / 460 | `plMisc_DRegion2Region`, `Nati2DRegion`, `Nati2NatiTeam`, `NatiTeam2Nati`, `Nati2EU`, `Club2Nati` |
| 4.0 | 7 × 22 | `plCombi_GetCombinationGrow` |
| 4.1 | 96 × 8 | `plCompeData_getCupUID_FromNation` |

## `PLRESOURCESIM.PAC`

16 entries, 12 TBB and 4 raw. **Confirmed** readers:

| Entry | Contents | Reader |
|---|---|---|
| 0 | TBB, 5 byte tables | `GetAreaData_Pointer(i)` (`0x21ef58`), `i < 5` |
| 1 | TBB, 2 tables | `SLES 0x232d88` (table `i < 2`) |
| 2 | TBB, 2 tables | not traced |
| 3 | TBB, 10,968 bytes | `plOteam_GetDb(team)` (`0x2165d8`): **457 × 24 bytes**, indexed by `PlTeam − 3`. Team 2 uses a runtime rival record instead |
| 4 | TBB, 1,305 × u16 | `plOteam_GetManagerNoOffset`, `plTeam_GetPlTeamFromNation` |
| 5 | raw, 32,152 bytes | `PlayerAffiliateaSearchTableInitialize`, `plMisc_GetPlayerAffiliateTeam` |
| 6 | TBB, 6 byte tables | `CAcquirePlayer::*` (tables 0, 1, 3, 4, 5), `CComOffer::CalcuOfferClub`, `CContractReform::Execute`, `CMakeDataBase::GetOutOfClubRange` |
| 7 | TBB, 2,000 × u16 | `GetPlayerIntroducePlayerNo` |
| 8 | TBB, 164 × u32 | `pwkTeam_GetPlPlayerIndivFromPinfo` |
| 9 | TBB, 7 tables | not traced |
| 10 | TBB, 6 × 25 bytes | `plTeam_GetStadiumDataIndex` |
| 11, 12 | raw, 22,528 bytes each | `SLES 0x21ea08` / `0x21ea28` return them. Callers not traced |
| 13, 14 | raw, 4,096 / 2,048 bytes | `plMail_ManagerTone2No` |
| 15 | TBB, 1,301 × u16 | `CMakeDataBase::Set_InitDBSet` |

## `UNIFORM_NAME.BIN` and `UNIFORM_NAME2.BIN`

Both are 531,050 bytes = 27,950 records of `char[19]`. Every record in
`UNIFORM_NAME.BIN` is `"a"` padded with zeros. `UNIFORM_NAME2.BIN` is the
same except for 142 records (from index 6,205 on) that are `"0"`. Nothing
in the executable or the overlays names either file, so they are probably
unused placeholders for kit names.

## Still unknown

- Field meanings in most tables above, including the 24-byte
  `plOteam_GetDb` record. (`OTEAMMEMBER` and `PLRRSRC_INITTEAMDATA` are
  done, in [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md).)
- `TEAM_INIT_DATA.TBB`: no reader found in `SLES`. The edit-mode overlay
  lists it.
- Parts of the schedule packs, listed in
  [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#still-unknown).
- `PBDATA_*.PAC` and the `.sqb` scripts in `PSC*.PAC`.
- The meaning of the other fields in the overlay load-list entries, and the
  code that walks the `SIMPRG.REL` list holding `ClubEvent` and
  `Camp_Explane` (entries at `0x225dd0`, `0x225df8`).

## Checking the claims

```bash
python SRC/tbb.py info DAT/PARAM                     # tables, sizes, line sizes
python SRC/pac.py list DAT/PARAM/PLRESOURCESIM.PAC   # pack entries
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkOteam_Init plResource_LoadRequest plRec_MatchRegulations
python SRC/sles_disasm.py ISO/SLES_541.51 addr 253338 60   # PlRrsrc_InitTeamData callback
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 7a18 12 --sles ISO/SLES_541.51   # load-list choice
```
