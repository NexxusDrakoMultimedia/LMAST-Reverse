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

Player names aren't in these files. The player number indexes the player
database in `PBDATA_EU.PAC`, which isn't decoded yet (entry 0 is a small
header, entry 1 holds 3 MB of records starting `Maik Taylor`).

## Still unknown

- What the game does with table 2's negative values.
- The player database, so squads can show names, positions and ratings.
- `INITNATIDATA.TBB`'s three fields, `STADIUM_DATA.TBB`, and the 24-byte
  computer-team record (`plOteam_GetDb`, `PLRESOURCESIM.PAC` entry 3).

## Checking the claims

```bash
python SRC/initteam.py info DAT/PARAM          # layout checks and counts
python SRC/initteam.py leagues DAT/PARAM       # clubs per division, with names
python SRC/initteam.py past DAT/PARAM          # table 1 and 2 per competition
python SRC/initteam.py squads DAT/PARAM 7      # one squad
python SRC/sles_disasm.py ISO/SLES_541.51 addr 253228 40
python SRC/sles_disasm.py ISO/SLES_541.51 dis plLg_EntryTeamSetToDiv UpdateConyear pwkTeam_SetUnumberOpinfo
python SRC/sles_disasm.py ISO/SLES_541.51 dis GetString__3MsgQ23Msg5eTYPEUib GlobalMsgSetup
```

A starting-season mod can change these tables with
`python SRC/tbb.py extract` / `replace` ([`TBB_FORMAT.md`](TBB_FORMAT.md#tool)).
