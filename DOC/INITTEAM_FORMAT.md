# Starting leagues and squads

Two tables in `DAT/PARAM` set up the clubs at the start of a career:

| File | What it sets up |
|---|---|
| `PLRRSRC_INITTEAMDATA.TBB` | which clubs start in which league and division, and each competition's order from "last season" |
| `OTEAMMEMBER.TBB` | the 25-player squad of every computer-controlled club |

Both are plain `TBB1` files ([`TBB_FORMAT.md`](TBB_FORMAT.md)). Which code
loads them is in [`PARAM_DIR.md`](PARAM_DIR.md#how-the-files-are-loaded)
(`ePLRSRC` 4 and 3). `SRC/initteam.py` reads both, and gives clubs their
names from `MES.PAC`.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x253338` | `PlRrsrc_InitTeamData` load callback | hands tables 0, 1 and 2 to the three readers below |
| `0x253228` | table 0 reader | leagues 0–5 (`pwkLg_GetLeague`). Each gets two divisions (`plLg_AddDiv` twice), filled from `data + i*0xd0` and `data + i*0xd0 + 0x68` |
| `0x2e94c8` | `plLg_EntryTeamSetToDiv` | walks u32 team ids until a `0` or until the division holds `0x1a` (26) teams |
| `0x2531b0` | table 1 reader | for `PLSCHE_COMPE` 0–48 (`slti 0x31`): clears the past record and passes the next `0x80` bytes to `pwkRec_SetPastRecordLastTeam` |
| `0x253650`, `0x2535f0` | `pwkRec_SetPastRecordLastTeam`, `…One` | 32 u32 team ids, stored as positions 0–31 (`slti 0x20`) of the competition's record at `+0x08` |
| `0x2532c8` | table 2 reader | 49 u16 values to `pwkRec_GetCompeConventionRecordKeikayear` |
| `0x24a6a0` | `pwkOteam_Init` | teams 3 to `0x1b9` (`slti 0x1ba`), 25 records of 16 bytes each. Copies `+0x0`, `+0x4`, `+0x8`, `+0xC` into squad slot bytes `+0`, `+2`, `+3`, `+4` |
| `0x2734c8` | `pwkTeam_SetUnumberOpinfo` | a squad is 25 six-byte `PlOpinfo` slots. `+0` is an s16 player number, with a negative value meaning an empty slot. `+3` is the shirt number: 1–99 is kept, anything else is replaced by the player's own preferred number or the first free number from 12 |
| `0x221480` | `UpdateConyear` | writes `+4` (contract years) from `+2`: under 28 → 3–5 years, under 30 → 2–4, older → 2–3. So `+2` is the **age** |
| `0x201f20` | `MSG_UTIL::CWildCardFunc::getPlayerName` | builds a `PlOpinfo` `{player, age 16, 0, 0, 0}` to look a player up in the player database (`plBp_GetBpinfo`) |
| `0x200ea8` | `Msg::GetString` | message type `0x2a` (team name) for team *t* is global category slot 2, record `2000 + t`. The base is the u16 at `0x52f7b0`. Team 0 is a fixed string, teams 1 and 2 (your club and the rival) are runtime names, and teams `0x21f`–`0x22e` use `pwkVs_GetTeamName` |
| `0x112ad0`, `0x51ab38` | `CFcEuro_RootModule::GlobalMsgSetup` and its table | global slots 0–9 are message categories 1, 11, 3, 4, 5, 6, 7, 8, 9, 10. So slot 2 is category **3** |

## `PLRRSRC_INITTEAMDATA.TBB`

Three tables. Their line sizes (4, 4, 2) are the element sizes, not the
record sizes.

### Table 0: leagues and divisions (1,248 bytes)

6 leagues × 2 divisions × `0x68` bytes. Division *d* of league *l* is at
`(l*2 + d) * 0x68`:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u32[26] | `PlTeam` ids, in order. The list ends at the first `0`, or after 26 |

Empirical, checked by `initteam.py info`:

- The divisions hold 20, 24, 20, 20, 18, 18, 20, 22, 20, 22, 18 and 20
  clubs: 242 in total.
- Each club appears once. The ids are exactly 3–244.
- No list has non-zero ids after its terminating `0`.
- By their names the leagues are England, France, Germany, Italy, Spain
  and the Netherlands, each with a first (division 0) and second division.
  Nothing in the code names them, so this is **empirical**.

### Table 1: last season's order (7,168 bytes)

56 records of `0x80` bytes, one per `PLSCHE_COMPE`:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u32[32] | `PlTeam` id at positions 0–31, `0` for none |

Only records 0–48 are read. Records 38–43 and 48 are empty, as are the
unread 49–55, so 42 of the 49 read records have teams. For a league the
list is its starting table: record 0 is the English first division in
the same order as table 0. Records 44–47 hold national teams. Knockout
competitions have their entrants. The schedule's `LAST_RANK` team entries
read these records back through `pwkRec_GetCompePastRecord`
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)), so this table decides who
qualifies for the first season's cups.

### Table 2: years since last held (112 bytes)

56 values (u16 in the reader, all small negative numbers as s16). The
first 49 are read. They are `-1` ×45, `-2` ×2 and `-4` ×2. The -4 and -2
fall on the national-team competitions 44–47, which fits a 4-year or
2-year cycle ("keika year" is roughly "years elapsed"). How the game uses
the sign is **not traced**.

## `OTEAMMEMBER.TBB`

One table of 175,600 bytes = 439 teams (ids 3–441) × 25 slots × 16 bytes.
The line size is 4 because every field was exported as a u32:

| Offset | Type | Slot byte | Meaning |
|---|---|---|---|
| `0x0` | u16 (+2 pad) | `+0` | player number (index into the player database) |
| `0x4` | u8 (+3 pad) | `+2` | age |
| `0x8` | u8 (+3 pad) | `+3` | shirt number |
| `0xC` | u8 (+3 pad) | `+4` | contract years remaining |

Empirical, checked by `initteam.py info`:

- Every slot is filled. The player numbers are 0–10,974, each used exactly
  once.
- Ages are 16–40, and contract lengths are 2–6.
- These are the ages a computer team's players show in game, one year
  older in a new game. Tested in PCSX2: Terry's 25 shows as 26, and after
  `initteam.py set 7:1 age=15` he shows as 16. The player database's own
  age field doesn't override them.
- Shirt numbers are 1–99 and never repeat within a team.
- All padding bytes are zero.

The squads cover more clubs (439) than the leagues (242). Teams 245–441
are clubs from the rest of Europe (`Salzburg`, `Porto`, `Glasgow City`,
...), followed by clubs from South America, Africa, North America, Asia
and Oceania (`Flamengo`, `Cairo`, `Toronto`, `Kanagawa`, `North Shore`).
The names go on past 441 to 542 (`Australia`, `New Zealand`). Those teams
have no squad in this file.

## Names

Club names are message category 3, record `2000 + team id`, in each
language slot (`python SRC/mbb.py dump DAT/MESSAGE/MES.PAC --cat 3`).
Categories 4 and 5 are parallel lists (5 holds the three-letter short
names, `CHE`, `LIV`, ...). Category 10 has `<name> Stadium`, from 11000.
Category 961 is something else: 839 English town names (`Reading`,
`Slough`, ...) with short forms in 962, which aren't indexed by team.

Player names aren't in these files. The player number is an id in the
player database, `PBDATA_EU.PAC` ([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)),
and `initteam.py squads` adds each player's name from it. Team 7's squad
starts with players 100–111: Petr Cech, John Terry, Ricardo Carvalho, …
Each player's shirt number here matches their preferred number (`+0x2b`)
in the database for these examples, but the squad's own number is the
one used.

## Club records (`PLRESOURCESIM.PAC` entry 3)

**Confirmed, `plOteam_GetDb` (`0x2165d8`).** One TBB table of 457 × 24
bytes, record `PlTeam − 3` (teams 3–459; later ids read record 0, and
team 2, the rival, uses a runtime record). Readers were found for most
fields by following all 21 callers:

| Offset | Type | Name | Reader | Meaning |
|---|---|---|---|---|
| `0x00` | s16 | rank | `plOteam_GetManagerClubRank`, `pwkOteam_GetRank` (via `pwkOteam_Init2` → `+0xa0`) | club rank, 0–31 |
| `0x02` | u16 | world_rank | `pwkOteam_Init2` → `+0xa2`, `pwkOteam_GetWorldClubRank` | world club rank points, 0–1020 (Chelsea 980) |
| `0x04` | s16 | manager | `plOteam_GetManagerNoOffset` | manager: database id − `0x6d2e`. All 457 differ |
| `0x06` | s16 | stadium | `PlGiTask::InitStadium`, `plTeam_GetStadiumNoFromNation` | `STADIUM_DATA` row (below) |
| `0x08` | u8 | foreign | `GetCanBelongForeignPlayerNum`, `CAcquirePlayer::GetSearchNation` | 0–7: row of `PLRESOURCESIM` entry 6, table 1 (2 bytes: foreign players allowed, % chance to search abroad) |
| `0x09` | u8 | newface | `CAcquirePlayer::IsAcquireNewfacePlayer` | 0–3: index into the % table at `0x533ff8` (chance to sign new faces) |
| `0x0a` | u8 | search_region | `CAcquirePlayer::GetSearchNation` | 0–31: row of entry 6, table 4 (13 weights, one per scouting region) |
| `0x0b`, `0x0c`, `0x0d`, `0x0f` | u8 | | none found | `0x0b` always equals `0x0a`; `0x0c` 1–87; `0x0d` 0–4; `0x0f` 0–25 in steps of 5 |
| `0x0e` | u8 | money | `plTeam_IsAgreeTransferChangeMoney`, `0x248140` | transfer sums × 1.0 below 60, × 0.95 for 60–79, × 0.9 from 80. 438 clubs have 0, 8 have 70, 11 have 85. Clubs without a record count as 50 |
| `0x10` | u16 | city | `plTeam_GetCity` | home city |
| `0x12` | u16 | list_state | `plState_GetEmblemDisplayTeamList` | the state the club is listed under in the emblem screens |
| `0x14` | u32 | list_city | `plCity_GetEmblemDisplayTeamList` | the city it is listed under (Chelsea: West London). 0 for clubs outside the six leagues |

National teams (460–542) take their manager from `PLRESOURCESIM` entry 4
instead: 18 bytes per nation, with the s16 at `+0` read by
`plOteam_GetManagerNoOffset`. Their rank is the nation's world rating
÷ 4.

City names are message category 961 and state names category 960
(**empirical**: city 604 is London, state 17 Greater London, and every
club checked is in its own town). `plCity_GetString` and
`plState_GetString` take the category from their caller.

The best clubs by world club rank share the game's few huge grounds:
Chelsea and Highbury (Arsenal) are at stadium 96, AC Milan and Inter at
99, Bayern, Dortmund and Leverkusen at 98, and Barcelona and La Boca at
100 (110,000 seats each). The game gives the biggest clubs by reputation
these stadiums instead of their real grounds.

## `INITNATIDATA.TBB`: nations

**Confirmed, the load callback `0x253418`, `pwkRec_GetUefaNation`
(`0x253e08`) and `pwkRec_GetWorldNation` (`0x253e68`).** 145 records of
6 bytes, for nations 1–145:

| Offset | Type | Nations | Meaning |
|---|---|---|---|
| `0x0` | u8 | 1–52 | UEFA ranking position (Italy 2, England 3, France 4) |
| `0x2` | u16 | 1–52 | UEFA coefficient points (Italy 492, England 482) |
| `0x4` | u8 | all | world rating (Brazil 125, Argentina 120). ÷ 4 is the national team's rank |

Nations 1–52 are the UEFA members. Their `+0`/`+2` go into 4-byte slots
of save block 5 at `0x4663c`, and `+4` into bytes at `0x4670c`.

## `STADIUM_DATA.TBB`: stadiums

**Confirmed, `plTeam_IsRoofFromID`, `plTeam_GetStadiumLvFromID` and
`plTeam_GetCapacityFromID` (`0x22ae18`, `0x22adc8`, `0x22ae68`).** 119
records of 3 bytes: roof (0/1, 52 have one), stadium level (0–4), and
capacity in thousands. `GetCapacityFromID` adds 500 seats for stadiums
103, 105 and 107. Capacities run from 8,000 to 110,000.

## `MAPTEAM_LIST.TBB`

242 × `{u16 team, u16 flag}`, the league clubs 3–244 in order. Only the
file name is known from the code (`SIMPRG.REL`'s load list at
`0x80694`). The reader hasn't been found. **Empirical**: the 116 clubs
with flag 1 are the real 2005/06 top divisions. Compared with the
starting divisions (`PLRRSRC_INITTEAMDATA` table 0, which has the
2004/05 line-up), the flags move the clubs promoted and relegated in
2005: Sunderland, West Ham and Wigan in, Crystal Palace, Norwich and
Southampton out, and likewise in the other five leagues.

`initteam.py teams`, `nations` and `stadiums` list all of this, `info`
checks it, and `setteam` edits a club record into a same-size copy of
`PLRESOURCESIM.PAC`.

## Still unknown

- What the game does with table 2's negative values.
- Club-record bytes `0x0b`, `0x0c`, `0x0d` and `0x0f`.
- What reads `MAPTEAM_LIST.TBB`, and what its flag is for.

## Checking the claims

```bash
python SRC/initteam.py info DAT/PARAM          # layout checks and counts
python SRC/initteam.py leagues DAT/PARAM       # clubs per division, with names
python SRC/initteam.py past DAT/PARAM          # table 1 and 2 per competition
python SRC/initteam.py squads DAT/PARAM 7      # one squad
python SRC/initteam.py teams DAT/PARAM 7       # a club record, with names
python SRC/initteam.py nations DAT/PARAM
python SRC/initteam.py stadiums DAT/PARAM
python SRC/sles_disasm.py ISO/SLES_541.51 dis plOteam_ pwkOteam_Init2 plTeam_IsAgreeTransferChangeMoney
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkRec_GetUefaNation pwkRec_GetWorldNation plTeam_GetCapacityFromID
python SRC/sles_disasm.py ISO/SLES_541.51 addr 253228 40
python SRC/sles_disasm.py ISO/SLES_541.51 dis plLg_EntryTeamSetToDiv UpdateConyear pwkTeam_SetUnumberOpinfo
python SRC/sles_disasm.py ISO/SLES_541.51 dis GetString__3MsgQ23Msg5eTYPEUib GlobalMsgSetup
```

`python SRC/initteam.py set OTEAMMEMBER.TBB out.TBB 7:1 age=15` edits a
squad slot (team 7, slot 1: Terry) and writes a same-size table that
`patch_disc.py` can put on the disc. Shirt numbers are limited to 1–99,
the range `pwkTeam_SetUnumberOpinfo` keeps.

A starting-season mod can change these tables with
`python SRC/tbb.py extract` / `replace` ([`TBB_FORMAT.md`](TBB_FORMAT.md#tool)).
