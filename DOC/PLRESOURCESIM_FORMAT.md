<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/PLRESOURCESIM.PAC`: the season-mode resource pack

`PLRESOURCESIM.PAC` is `plResource` entry 1 ([`PARAM_DIR.md`](PARAM_DIR.md)),
loaded by the `SIMPRG.REL` load list for the season mode. It is a BINPAC
of 16 entries: 12 TBB1 files and 4 raw streams. Every reader calls
`plResource_GetResourceDataBinPac` (`0x21e890`), `…BinPacTbb` (`0x21e940`)
or `…BinPacTbbTbl` (`0x21e9e0`) with `ePLRSRC` 1 and **constant** entry and
table numbers (empirical: every call in `SLES_541.51` was listed, and
`SIMPRG.REL`, the only overlay importing these functions, only reads
entry 9). So the reader of each entry is known for certain, and entry 2
has none.

`python SRC/plrsim.py info DAT/PARAM` checks every entry.
`python SRC/plrsim.py show DAT/PARAM <entry>` prints one, naming players,
managers and scouts from `PBDATA_EU.PAC`.

| # | Bytes | Contents | Readers (**confirmed**) |
|---|---|---|---|
| 0 | 12,480 | states, cities, climate and weather | `GetAreaData_Pointer` (`0x21ef58`), `plState_*`, `plCity_*`, `plNati_GetBelong*` |
| 1 | 208 | overseas branches: cost per region, level rates | `0x232d88`: `_GetUp1SituLevelCapital`, `_GetOverseasBranchEstablishCapital`, `pwkTown_GetOverseasBranchMaintenanceExpense[FromRegion]` |
| 2 | 720 | 400 bytes and 128 u16 | **none** |
| 3 | 11,024 | 457 club records | `plOteam_GetDb` (`0x2165d8`); see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md) |
| 4 | 2,672 | per nation: national-team manager and 8 clubs | `plOteam_GetManagerNoOffset` (`0x216668`), `plTeam_GetPlTeamFromNation` (`0x22a678`) |
| 5 | 32,152 | the clubs each player is affiliated with | `PlayerAffiliateaSearchTableInitialize` (`0x2161b8`), `plMisc_GetPlayerAffiliateTeam` (`0x2163f0`) |
| 6 | 2,848 | transfer AI tables | `CAcquirePlayer::*`, `CComOffer`, `CContractReform`, `CMakeDataBase` ([`PARAM_DIR.md`](PARAM_DIR.md#plresourcesimpac)) |
| 7 | 4,048 | players offered by introduction | `GetPlayerIntroducePlayerNo` (`0x2202f8`) |
| 8 | 704 | statistics row of each schedule UID | `0x267bf8`, from `pwkTeam_AddPlayerRecord` (`0x267d80`) |
| 9 | 832 | the edit screens' colour palette | `EDIT::CColor` (`0x2b9998`–`0x2b9c88`) in 8 `SIMPRG.REL` screens, `PlGiTask::InitStadium` (`0x212fa0`) |
| 10 | 208 | stadium id by league and level | `plTeam_GetStadiumDataIndex` ([`STADIUM_DIR.md`](STADIUM_DIR.md#conv_info_buildtbb)) |
| 11 | 22,528 | each scout's exclusive players | `0x21ea08` → `plSinfo_CheckExclusive`, `plSinfo_GetExclusivePlist`, `…MixPlist`, `plPinfo_CheckExclusive` |
| 12 | 22,528 | each scout's semi-exclusive players | `0x21ea28` → `plSinfo_CheckSemiExclusive`, `plSinfo_GetSemiExclusivePlist`, `…MixPlist` |
| 13 | 4,096 | good combinations of players and managers | `0x2145b8` → `plMisc_GetGoodLevel`, `…GoodCombi`, `…GoodCombiNum`, `_GetGoldenTblPtr` |
| 14 | 2,048 | bad combinations | `0x2145d8` → `plMisc_GetBadLevel`, `…BadCombi`, `…BadCombiNum` |
| 15 | 2,656 | free agents at the start | `CMakeDataBase::Set_InitDBSet` (`0x223110`) |

Database ids below are as in [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md):
players 0–27,949, managers 27,950–30,949, scouts 30,950–31,949. Club ids
are `PlTeam` ids (computer clubs 3–441).

## Entry 0: states, cities, climate and weather

Five byte tables, read through `GetAreaData_Pointer(i)` (`i < 5`).

| Table | Bytes | Records | Layout | Read by |
|---|---|---|---|---|
| 0 | 274 | 137 × 2 | `{u8 state, u8 nation}`, state = index; record 0 is `(0, 0)` | `plNati_GetBelongState*` (`slti 0x89`), `plState_GetBelongCountry` |
| 1 | 10,068 | 839 × 12 | city record (below), city = index | `Get_plStateCity_AreaDataCitySheet_Pointer` (`0x21ef90`, searches `0x2754` bytes) |
| 2 | 832 | 64 × 13 | `{u8 climate zone, s8 temperature[12]}`, one per month | `plCity_GetAverageTemperature` (`0x21fa60`) |
| 3 | 832 | 64 × 13 | `{u8 weather zone, u8 row[12]}`, one per month | `plCity_GetListProbability` (`0x21fbd0`) |
| 4 | 320 | 64 × 5 | `{u8 row, u8 chance[4]}` | the same |

The city record:

| Offset | Type | Field | Evidence |
|---|---|---|---|
| `+0x00` | u32 | city id | the search key |
| `+0x04` | u32 | population | `plCity_GetPopulation` |
| `+0x08` | u8 | state (cities 0–602) or nation (603–838) | `plCity_GetBelongStateOrNation` (`0x21f9d8`) sets its flag by whether the record lies before `+0x1c44` (city 603) |
| `+0x09` | u8 | climate zone (table 2) | `plCity_GetAverageTemperature` |
| `+0x0a` | u8 | weather zone (table 3) | `plCity_GetListProbability` |
| `+0x0b` | u8 | initial choice: 1 if the city can be picked at the start | `plState_GetInitChoiceCityNum/List` count only these (`_GetBelongCityNum` mode 1, `0x21f58c`) |

- `plCity_GetTemperature` (`0x21fb70`) is the month's average plus a random
  −2 to +2.
- `plCity_GetSeason` (`0x21faf8`): below 7 degrees season 3, from 18
  season 1, in between by month (table at `0x533d40`).
- `plCity_GetListProbability` copies the city's month's row of table 4.
  Below 4 degrees it moves the third chance to the fourth and sets the
  third to 0 (`0x21fcd4`): rain turns to snow. **From playing the game
  (user report):** the game's four weathers are sunny, overcast, rain
  and snow, which fits the chances in that order.
- State 48 counts the cities of three nations (table at `0x533d70`), and
  state 71 is special-cased too (`0x21f4c0`).

**Empirical:** cities are numbered 0–838 in order, and those of one state
are consecutive. 601 of the 839 are initial choices. City names are
messages (`plCity_GetString`); not yet listed by the tool.

## Entry 1: overseas branches

| Table | Layout |
|---|---|
| 0 | 13 × `{u32 region, u32 establishing cost}`, one per scouting region |
| 1 | 8 × f32: 0.015, 0.020, 0.025, 0.030, 0.045, 0.060, 0.075, 0.090 |

`_GetOverseasBranchEstablishCapital(region)` is table 0's cost (6,300,000
to 16,500,000), less the sponsor discount in
`pwkTown_GetOverseasBranchEstablishCapital`. Raising a branch to a level
costs `cost × round(rate[level] × 1000) / 1000` (`_GetUp1SituLevelCapital`,
`0x232f70`), and the maintenance expense uses the same two tables.

## Entry 2: unread

A 400-byte table cycling between 4 and 10, and 16 rows of 8 rising u16
(10 to 220). No code asks for entry 2.

## Entry 4: nations

145 records of 18 bytes, for nations 1–145:

| Offset | Type | Field | Reader |
|---|---|---|---|
| `+0x00` | s16 | the national team's manager (manager index, + `0x6d2e` for the database id) | `plOteam_GetManagerNoOffset` for teams 460–542 (`0x1cc`–`0x21e`, the national teams) |
| `+0x02` | u16[8] | club ids; short lists repeat the last club | `plTeam_GetPlTeamFromNation(nation, i < 8)` |

What the 8 clubs are used for hasn't been traced. England lists 13, 11
and 12.

## Entry 5: player affiliations

A stream of s16. A value ≤ 0 starts a player (its negation), and the
values > 0 after it are the clubs he is affiliated with.
`PlayerAffiliateaSearchTableInitialize` records a pointer to every player
header (room for 8,287, `0x817c` bytes) for a search by player number
(`CompPlayerNo`, `0x2162b0`).

**Empirical:** 8,003 players. 7,933 have one club, 64 two, 4 three, and 2
none. All clubs are computer clubs (3–441). The headers are not in
player order.

## Entry 7: players offered by introduction

10 groups of 100 records `{s16 player, s16 threshold}`. For group `g`,
`GetPlayerIntroducePlayerNo` collects the players whose threshold is at
most the team's counter byte at `+0x124b8 + g`, so more players open up
as the counter rises. Thresholds run from 0 to 55 within each group, in
order. What the 10 groups and the counter are hasn't been traced.

## Entry 8: statistics row per schedule UID

164 records `{s16 UID, s16 kind}` for schedule UIDs 0–163
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)). `pwkTeam_AddPlayerRecord`
looks up the UID of a match and adds the player's figures to that row of
his statistics (`PlCareerRecordKind`; 5 if the UID isn't listed). The
statistics tables in a save have five rows
([`SAVE_FORMAT.md`](SAVE_FORMAT.md)), so kinds 0–4 are those rows and 5 is
not counted.

| Kind | UIDs |
|---|---|
| 0 | 124–141 (18) |
| 1 | 28, starting with 0–3 |
| 2 | 36, starting with 4–9 |
| 3 | 58–80 (23) |
| 4 | 81–86 (6) |
| 5 | 87–123 and 148–163 (53) |

`SAVE_FORMAT.md` names the rows pre-season, domestic league, overseas
league, Euro and international (empirical). Kind 2 includes knockout
UIDs (UID 4 is a cup round), so those names are only approximate.

## Entry 9: the edit screens' colour palette

`EDIT::CColor` wraps this TBB (`TblData::CTblData::Setup`). It is set up
by 8 screens in `SIMPRG.REL` and by `PlGiTask::InitStadium`.

| Table | Bytes | Used by | Contents |
|---|---|---|---|
| 0 | 384 | `GetColorFromId96` | 96 colours, `R << 24 | G << 16 | B << 8 | A` |
| 1 | 32 | `GetId16FromId32` | 32-colour index → 16-colour index |
| 2 | 96 | `GetId16FromId96` | 96 → 16 |
| 3 | 16 | `GetId32FromId16` | 16 → 32 |
| 4 | 96 | `GetId32FromId96` | 96 → 32 |
| 5 | 16 | `GetId96FromId16` | 16 → 96 |
| 6 | 32 | `GetId96FromId32` | 32 → 96 |

`GetColor16` turns a colour into a PS2 15-bit colour (each channel × 31 /
255, alpha bit set when A ≠ 0). So the 32- and 16-colour palettes are
subsets of the 96.

## Entries 11 and 12: scouts' exclusive players

A stream of s16. A negative value starts a scout (its negation is the
scout index, database id − `0x78e6`), and the values after it are player
ids. The lookup (`0x21ea48`) answers whether a player is in a scout's
group. With scout −1 it searches every group, which is how
`plPinfo_CheckExclusive` asks whether any scout has the player.

Exclusive players weren't known to the user from playing, so nothing on
screen has been matched to these lists yet.

**Empirical:** entry 11 has 155 groups for 154 scouts (scout 1's header
appears twice) and 486 players. Entry 12 has 134 groups for
133 scouts and 440 players. The rest of each 22,528-byte entry is zeros.

## Entries 13 and 14: good and bad combinations

A stream of s16. A negative value starts a group (its negation is the
level, 1–3, once 4), and the values after it are its members: database
ids of players and managers. `−1000` ends the list. `plMisc_GetGoodLevel`
and `plMisc_GetBadLevel` take two ids and return their level.

**Empirical:** entry 13 has 189 groups (159 pairs, 20 trios, 7 of four, 3
of five) with 56 managers among the members, for example Owen, Gerrard
and Carragher. Entry 14 has 63 pairs, with 29 managers. How the level
changes a match or a player hasn't been traced. **User report:** the
combinations are hidden: no screen shows them.

## Entry 15: free agents at the start

u16 player ids, ending at `0xffff`. `Set_InitDBSet` reads up to 1,500
(`slti 0x5dc`) and adds each with `pwkDb_addFreePlayer`, with the age from
the database. **Empirical:** 1,300 players.

`python SRC/plrsim.py setfree <in> <out> <slot>=<player>` replaces players
in the list and keeps the pack's size. The pack has copies in the seven
`PRELOAD/SIMLOCALMEM*.PAC` packs, so patch it with `patch_disc.py
--copies`. `python SRC/plrsim.py roundtrip DAT/PARAM` re-encodes the
unchanged list through the same encoder and checks that the rebuilt pack
equals the original byte for byte. The editor's Free agents tab makes
the same edit and logs it as a `setfree` command.

**Empirical:** no free agent is in a club squad (`OTEAMMEMBER.TBB`), and
all 1,300 are rank 1–10. The editor refuses a squad player, to keep that
rule.

## Entry 6 table 2

`{1, 5, 2, 5, 3, 5, 4, 5, 5, 5, 6, 5}`: no reader of entry 6 uses table
2. The other tables are described in [`PARAM_DIR.md`](PARAM_DIR.md#plresourcesimpac)
and [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md).

## Still unknown

- The season numbers (entry 0).
- What the 8 clubs per nation in entry 4 are for.
- What the 10 introduction groups of entry 7 and their counter are.
- The exact meaning of statistics rows 1 and 2 (entry 8).
- How combination levels act in the game.
- Entry 6's tables in full.

**Tested in PCSX2.** J.Galvan (slot 627) was replaced by Gianluigi
Buffon, using Italy's national-team record 26,110
([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#player-id-blocks)). In a
new career J.Galvan was gone from the in-game Transfer List, so the
game's free agents come from this entry. Buffon didn't appear there
either. `pwkDb_addFreePlayer` (`0x235f08`) refuses only edit players
(`plPinfo_IsEdit`: id 31,950 and up), so Buffon should be in the pool.
The screen shows only part of the pool, gated by rank (the user's
suggestion; Buffon is rank 14, J.Galvan rank 5): see
[below](#which-free-agents-the-transfer-list-shows).
`SIMPRG.REL 0x15b030` moves one named free agent from the pool to the
club's own transfer list (`pwkTeam_AddPinfoTransferFree`), but it is
given the player; it doesn't choose him.

**Tested in PCSX2, second disc.** Paul Jones (Wales's national-team
goalkeeper, 26,455, rank 5 like J.Galvan) in the same slot showed on the
Transfer List (Club House / Scouting, "Acquire transfer list") in
2006–07, with no team, aged 32. So national-team records can be free
agents, and Buffon was held back by something else, most likely his
rank (14) against the club's reputation, as the user suggested.

## Which free agents the Transfer List shows

The Transfer List shows a player from the pool only when his rank lies
in a band set by the club's rank. Rank 14 is above every band, so Buffon
can never show. **Confirmed** from the code:

| Address | Symbol | What it shows |
|---|---|---|
| `0x25c168` | (band) | reads the club rank (`+0x41f8` of `pwkTeam_GetMyTeamData`, the byte `pwkOteam_GetRank` returns, 0–31), halves it and picks the band from a jump table at `0x553170` (below) |
| `0x25bfc8` | (test) | a player passes when his rank (`getPinfoRank`) is ≥ the band's low end and ≤ its high end, and his main position matches the one asked for (9 = any) |
| `0x25bf40` | (test) | a player one of the club's scouts is working on (`pwkTeam_GetScouts`, `+0x8c`) is left out |
| `0x25c3b8` | (stride) | counts the players who pass, then takes every *n*-th: *n* = 1 up to 100 players, 2 up to 200, 3 up to 300, 4 up to 400, else 5 (table at `0x5531b0`) |
| `0x25d2b8` | `pwkTeam_CheckMoveListData` | walks the 1,500 pool slots (`pwkDb_getFreePlayer`) with the band and stride, up to 30 free agents, then the clubs' out-of-plan players (`pwkDb_getComOutOfTeamPlan`) up to 60 in all. `pwkTeam_GetMoveListData` (`0x25c440`) and `pwkTeam_CheckMoveListPlayerExist` (`0x25c228`) use the same tests |

| Club rank | Player ranks shown |
|---|---|
| 0–5 | 0–5 |
| 6–9 | 0–6 |
| 10–13 | 1–7 |
| 14–17 | 1–8 |
| 18–21 | 2–9 |
| 22–25 | 2–10 |
| 26–31 | 3–11 |

Player ranks run 0–15 ([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)), so free
agents of rank 12–15 never reach the Transfer List, at any club. A top
club also stops seeing ranks 0–2. Because of the stride, a player inside
the band may still be skipped when more than 100 players pass. To offer
a star as a free agent, lower his rank (`+0x18` for ids from `0x63f7`
up) to 11 or less, and to the club's band for a new club (5 or less).
Not tested in PCSX2.

That the "move list" functions build the Transfer List screen is read
from their names and from their use of the free-agent pool; the screen's
call into them hasn't been traced.

## Checking the claims

```bash
python SRC/plrsim.py info DAT/PARAM
python SRC/plrsim.py show DAT/PARAM 13
python SRC/sles_disasm.py ISO/SLES_541.51 dis GetAreaData_Pointer plCity_GetAverageTemperature plCity_GetBelongStateOrNation
python SRC/sles_disasm.py ISO/SLES_541.51 dis _GetUp1SituLevelCapital Set_InitDBSet plOteam_GetManagerNoOffset
python SRC/sles_disasm.py ISO/SLES_541.51 addr 21ea48 45     # exclusive-player lookup
python SRC/sles_disasm.py ISO/SLES_541.51 addr 2b99f8 120    # EDIT::CColor
python SRC/sles_disasm.py ISO/SLES_541.51 addr 25bf40 300    # Transfer List tests and band
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkTeam_CheckMoveListData
```
