<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/TEAM_INIT_DATA.TBB`: the player's new club

At the start of a career you pick a league and a team style. That choice
selects, from this file, the new club's squad, youth team, manager,
coaches and scouts, its starting staff lists, and the rival club. It is
a TBB1 file ([`TBB_FORMAT.md`](TBB_FORMAT.md)) of 9 tables, all made of
u32 fields.

`python SRC/teaminit.py info DAT/PARAM` checks the file.
`python SRC/teaminit.py show DAT/PARAM/TEAM_INIT_DATA.TBB` lists every
table, with players and staff named from `PBDATA_EU.PAC`. `set` edits a
record ([below](#editing)).

## Who reads it

| Address | Symbol | What it shows |
|---|---|---|
| `CEDITPRG.REL 0x1b288` | load list of `CSelectTeamStyleModule` (returned at `0x2d28`) | one entry: `team_init_data.tbb`, folder 4 (`PARAM`) |
| `CEDITPRG.REL 0x2c20`–`0x2cf4` | the module's step function | creates `WP::CSelectTeamStyleTask` (`SIMPRG.REL 0xcbbc0`), takes the file as resource 0 of its list (`GetResourceHandle`, `0x2c5c`), and when the screen is done calls `pwkTeam_Init2(pwkLg_GetMyLeague(), choice − 1, file)` (`0x2ccc`) |
| `SIMPRG.REL 0xcc32c` | `CSelectTeamStyleTask` | the menu lists messages `420:200 + i` for i = 0–3: Counter-Attack, Possession, Individual Play, Teamwork |
| `0x25eae8` | `pwkTeam_Init2(PlLeague, PlMPolicyRange, const TBB_FILEHEADER*)` | reads tables 1, 2, 4 and 5 itself, and passes the file to the three helpers below |
| `0x25dc50` | (squad lookup) | the first table-0 record whose `+0` is the league and `+4` the style, searching `0x3180` bytes (528 records) |
| `0x25dce8` | (own squad) | 18 players from that record on (`slti 0x12` at `0x25df78`) |
| `0x25e190` | (youth team) | table 3, the first record whose `+0` is the league, then 16 records of 16 bytes |
| `0x25e4a8` | (rival club) | team slot 2 (`pwkOteam_GetPointer(2)`): 22 players from table 0, then tables 6, 7 and 8 |
| `0x25e950` | `pwkTeam_Init` | calls `pwkTeam_Init2(0, 0, NULL)` first. Without a file every reader falls back to built-in values ([below](#without-the-file)) |

`TESTPRG.REL`'s `HayasiTest` module also loads the file
(`plResource_LoadRequest(5, …)`, `0x103fc`), and its callback (`0x102b0`)
only checks that tables 0–6 exist. That module is a developer test.
Nothing else asks for `plResource` entry 5: no call in `SLES_541.51`
passes 5, and `SIMPRG.REL`, the only other overlay importing `plResource`
functions, always passes 1.

## Keys

Every record starts with `{u32 league, u32 style}`. A reader finds the
first record with the key it wants and takes a fixed number of records
from there.

- **League** 0–5. `pwkLg_GetMyLeague` gives the league chosen for the club.
  The names are those of `PLRRSRC_INITTEAMDATA`'s divisions
  ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)), and each league's block of
  players is mostly of that nation (**empirical**: 84 of 88 per league):

  | 0 | 1 | 2 | 3 | 4 | 5 |
  |---|---|---|---|---|---|
  | England | France | Germany | Italy | Spain | Netherlands |

- **Style** 0–3 (`PlMPolicyRange`): Counter-Attack, Possession, Individual
  Play, Teamwork (**confirmed**, the menu order above).
- Tables read by league alone hold style **4** in every record, and table
  6, read by style alone, holds league **6** (**empirical**). The code never
  reads these values.

## The tables

| # | Bytes | Record | Records | Groups | Read at | Used for |
|---|---|---|---|---|---|---|
| 0 | 12,672 | 24 | 528 | 22 per (league, style) | `0x25dce8`, `0x25e4a8` | squad: the club takes the first 18, the rival all 22 |
| 1 | 3,456 | 24 | 144 | 6 per (league, style) | `0x25ed5c`–`0x25eea8` | manager, youth-team manager, 4 coaches |
| 2 | 1,728 | 24 | 72 | 3 per (league, style) | `0x25eeb4`–`0x25ef7c` | 3 scouts |
| 3 | 1,536 | 16 | 96 | 16 per league | `0x25e190` | youth team |
| 4 | 864 | 24 | 36 | 6 per league | `0x25eba8`–`0x25ec68` | first 6 of a 30-slot manager list |
| 5 | 864 | 24 | 36 | 6 per league | `0x25ec84`–`0x25ed40` | first 6 of a 13-slot scout list |
| 6 | 48 | 12 | 4 | by style | `0x25e6a8`–`0x25e6e8` | rival's manager |
| 7 | 72 | 12 | 6 | by league | `0x25e6f4`–`0x25e738` | rival's stadium |
| 8 | 480 | 20 | 24 | by (league, style) | `0x25e740`–`0x25e7a8` | rival's club-record bytes |

### People: tables 0, 1, 2, 4, 5 (24 bytes) and 3 (16 bytes)

| Offset | Read as | Field | Where it goes (**confirmed**) |
|---|---|---|---|
| `+0x00` | u32 | league | key |
| `+0x04` | u32 | style | key (4 in tables 3, 4, 5) |
| `+0x08` | u16 (`lhu`) | id | players: database index (`getPbase`). Staff: the game adds `0x6d2e` (managers, 27,950) or `0x78e6` (scouts, 30,950) |
| `+0x0c` | u8 (`lbu`) | age | players: `PlOpinfo +2`, the age, as in `OTEAMMEMBER`. Staff: the slot's byte that the fallback fills from manager-record byte `0x22` (`0x25eff4`) or scout-record byte `0x18` (`0x25f038`) |
| `+0x10` | u8 | contract | players: `PlOpinfo +4` and `PlPinfo +0x21d`, the contract years (fallback 3). Staff: the 4th argument of `plMinfo_InitDb`/`plSinfo_InitDb` (fallback 3) |
| `+0x14` | u32 | salary | passed through `SM2MoneySave_WithInRange` (`0x246f90`) and stored as the salary (`PlPinfo +0x218`; coaches `PlMinfo +0xb8`). Fallback for players 150,000 (`0x249f0`) |

Table 3 has only the first four fields, and player `0xffffffff` is an
empty slot: `getPbase` finds no player and the slot stays empty
(`0x25e2e4`).

**Empirical**, from the file and `PBDATA_EU.PAC`:
- Player ages match the database in 456 of 528 squad records and 42 of
  48 youth records. The table's age is the one the game uses.
- Staff `+0x0c` equals manager field `f_22` in all 180 manager records
  (tables 1 and 4), and scout field `f_18` in all 108 scout records
  (tables 2 and 5). Values run from 38 to 58, so those two database
  fields are very probably the staff ages, which `pbdata.py` doesn't
  name yet.
- Contracts: 2–4 years for players, 1–3 for staff. Salaries: 90,000 to
  1,620,000 for players, 360,000 to 900,000 for staff.
- No player in table 0 or 3 is in a computer club's squad (`OTEAMMEMBER`).
  Each league has its own block of made-up players (88 squad ids from
  10,975 on for England, then France, and so on). The four styles share
  none of them. A few foreign players (database ids 22,884 and 25,386,
  for example) appear in every league.
- 48 of table 3's 96 youth slots are empty: each league has 8 youth
  players, aged 16 or 17.

### Squad (table 0)

The club gets records 0–17 of its group (`0x25dce8`), in order, through
`pwkTeam_JoinPlayer`. The captain is the one with the best
`plTeam_GetCaptainFitPoint`. Records 18–21 only go to the rival.

The rival takes records 0–17 (`0x25e580`) and 18–21 (`+0x1b0`,
`0x25e5c8`) of the group for a different style. The table at `0x5531e0`
maps the club's style to the rival's: `{1, 0, 3, 2}`, so Counter-Attack
and Possession face each other, as do Individual Play and Teamwork.

### Staff (tables 1 and 2)

| Record of the group | Becomes |
|---|---|
| table 1, 0 | the manager (`pwkTeam_GetDefaultManager`, the club's `PlMinfo` at `+0x4854`) |
| table 1, 1 | the youth-team manager (youth data `+0x3f00`, job 6 at `+0x3fa0`; job 6 is the youth manager, see [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)) |
| table 1, 2–5 | four coaches (`pwork +0x9148`, `0xbc` apart) |
| table 2, 0–2 | three scouts (`pwork +0x8f8c`, `0x94` apart) |

### Staff lists (tables 4 and 5)

Each league's 6 records fill the first 6 slots of a list of 12-byte
entries `{u32 salary, s16 id + 0x6d2e, u8 contract, u8 age, u8 8}`, and
the remaining slots are set to `-1`: 30 slots at `pwork +0x9ac8` for
managers, 13 at `+0x9c30` for scouts. Without the file, the lists hold
30 managers (database 29,950–29,979) and 13 scouts (30,953–30,965). What
the game shows these lists as, probably the staff on offer at the start,
hasn't been traced.

### The rival club (tables 6, 7 and 8)

`0x25e4a8` fills the rival's 24-byte club record (the
[`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md) layout, at rival work `+0x10`):

| Club-record field | Value |
|---|---|
| `0x00` rank | 11 (constant, also stored in `pwkOteam` slot 2 `+0xa0`) |
| `0x02` world_rank | 200 (constant, also `+0xa2`) |
| `0x04` manager | table 6, `+0x08` |
| `0x06` stadium | table 7, `+0x08`: the `STADIUM_DATA` row (114 for every league) |
| `0x08`–`0x0a` foreign, newface, search_region | table 8, `+0x08`, `+0x0c`, `+0x10` (one byte each, as `u32`) |
| `0x10` city | the rival's city, rival work `+0x00` |
| `0x12`, `0x14` | 0 |

Rival work `+0x0c`, the stadium name (message category `0x25`), is a
random one of four per league: `league × 4 + rand(4)`.

**Table 6 quirk (confirmed).** The loop at `0x25e6d0` compares each of the
4 records' style with the rival's, but the load in its branch delay slot
is `lw $s3, 8($a0)`, and `$a0` stays at the start of the table. So the
rival's manager is always record 0's (manager 898), and records 1–3
(1,970, 1,247, 1,246) are never read.

Table 8 holds foreign 0 and newface 1 everywhere, and search_region 13,
2, 7 or 12 by style.

### Without the file

`pwkTeam_Init` builds a default club before the style screen, with
`pwkTeam_Init2(0, 0, NULL)`:

| What | Built-in value |
|---|---|
| squad | 18 ids at `0x3995a8`: players 25,591–25,608, ages from the database, contract 3, salary 150,000 |
| youth team | 16 ids at `0x3995d0`: players 25,623–25,638, ages 16 + i mod 3 |
| rival squad | players 25,655 + i (`0x6437`) and 25,673 + i (`0x6449`) |
| manager | manager 0 (database 27,950, `pwkTeam_GetDefaultManager` with no record) |
| coaches, youth manager | managers 1–4 and 5 (database 27,951–27,955, `0x6d2f`…), contract 3 |
| scouts | scouts 0–2 (database 30,950–30,952), contract 3 |
| staff lists | see above |

With the file, `0x25dd38` and `0x25e234` copy the table's ids over those
two lists before using them. The built-in players come from the blocks
of low-rank England players with shirts 1–25 that `TODO.md` asked about
(25,591–25,615 and 25,616 on).

## Editing

```bash
python SRC/teaminit.py set DAT/PARAM/TEAM_INIT_DATA.TBB out/TEAM_INIT_DATA.TBB 0:0 player=101 age=30 1:0 salary=1000000
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/TEAM_INIT_DATA.TBB=out/TEAM_INIT_DATA.TBB --copies
```

`<table>:<record>` numbers records from 0 within a table, as `show` prints
them. `set` keeps the file's size, refuses ids outside the database,
bytes over 255 and ids over 65,535, and refuses a key change that would
break a group. Use `-` for an empty youth slot. `teaminit.py roundtrip`
re-encodes every table and rebuilds the file byte for byte (in
`regress.py`).

**Tested in PCSX2.** Squad record 0 of England / Counter-Attack
(A.Hinshelwood, 23) was set to database player 26,046 ("John Terry",
in no computer squad) at age 30, and record 44 (England / Individual
Play) to the same player at 31. A new career in England with
Counter-Attack (the club came out as Dunstable Utd, English League 1)
showed John Terry in the squad at age **30**, as a centre back and
captain. The squad was exactly records 0–17 of the group: 11 starters,
5 on the bench and 2 not registered. Records 18–21, which only the
rival gets, weren't in it. So the game reads this file, the style picks
the group, the club takes 18 records, and the age field is the age the
game shows (not one year more, unlike `OTEAMMEMBER`'s squads, which a
new game shows a year older). The captain is chosen by
`plTeam_GetCaptainFitPoint`, not by record order.

**From playing the game (user report).** The team style sets the
starting players, and the rival club gets the opposite style. This
matches the code above (`0x25dc50`, and the style map at `0x5531e0`).

## Still unknown

- What the game shows the staff lists of tables 4 and 5 as.
- Whether the staff `+0x0c` byte is shown as the age (the database
  fields it matches aren't named yet).
- The unit of the salary before `SM2MoneySave_WithInRange`.

## Checking the claims

```bash
python SRC/teaminit.py info DAT/PARAM
python SRC/teaminit.py show DAT/PARAM/TEAM_INIT_DATA.TBB 1 6 7 8
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkTeam_Init2
python SRC/sles_disasm.py ISO/SLES_541.51 addr 25dc50 38      # squad lookup
python SRC/sles_disasm.py ISO/SLES_541.51 addr 25e4a8 220     # rival club, table 6 quirk at 0x25e6d0
python SRC/snr2.py dis ISO/DLL/CEDITPRG.REL 2bf0 70 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL cc310 20 --sles ISO/SLES_541.51
```
