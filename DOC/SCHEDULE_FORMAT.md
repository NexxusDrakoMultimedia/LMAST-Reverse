# Season schedule: `SCHEDULE_SYSTEM`, `SCHEDULE_COMPETITION`, `SCHEDULE_TEAM_ENTRY`

The career calendar is built from three BINPAC packs in `DAT/PARAM`
([`PARAM_DIR.md`](PARAM_DIR.md)). All their entries are `TBB1` files
([`TBB_FORMAT.md`](TBB_FORMAT.md)):

| Pack | Entries | Holds |
|---|---|---|
| `SCHEDULE_SYSTEM.PAC/.HED` | 5 named TBBs | the year plan: which schedules exist, when their games fall, host nations, team lists |
| `SCHEDULE_COMPETITION.PAC/.HED` | 164 | one schedule per UID: its games and pairings |
| `SCHEDULE_TEAM_ENTRY.PAC/.HED` | 164 | one per UID: where each entrant's team comes from |

A **schedule UID** (0–163) is one run of games: a league division, a cup
round, a group of a group stage. The game calls it `PLSCHE_GROUP`. Several
UIDs belong to one **competition** (`PLSCHE_COMPE`, 0–71). For example, UIDs 1
and 2 are both competition 1: one is used when it is the player's own
league, the other when it isn't. Entry *n* of both 164-entry packs belongs to UID
*n*, and `REGULATION.TBB` is indexed by the same number.

The layouts below are **confirmed** from the game code unless marked
**empirical**. `python SRC/schedule.py info DAT/PARAM` checks all of it
against the disc and reports one problem (UID 117, below).

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x209b50` | `ScheEuro_SubCtrl::requestLoad` | loads `schedule_system.pac` |
| `0x209bf0` | `ScheEuro_SubCtrl::isCompleteLoad` | loads its 5 entries, then runs the four `init*Data` below |
| `0x20a008` | `ScheEuro_SubCtrl::initYearScheduleData` | 20-byte rows. A row with UID −1 continues the row before it |
| `0x20a170` | `ScheEuro_SubCtrl::getYearSchedule(uid, second)` | finds a row by UID. `second` returns the −1 row after it |
| `0x20a130` | `getScheCompe_FromTBB` | `+4` is the competition |
| `0x20a230` | `isGameOpen_FromTBB(uid, turn)` | bit `turn` of the mask at `+8` |
| `0x209968` | `YEAR_SCHEDULE::get_open_turn` | first set bit of the 12-byte mask, plus 96 per year of delay from `+5` |
| `0x209f40` | `getOpenNation(compe, years)` | 44-byte `open_nation` rows |
| `0x205728` | `CScheEuro::getNationFromScheCompe` | passes `pwkGen_Keika()` (years played) as `years` |
| `0x2072a8`, `0x207458`, `0x2075c8` | `CScheEuro_{Normal,FirstPromote,VS}::acceptLoadRequest` | the load condition in `+6` |
| `0x2068f8` | `CScheEuro::OneLoadCompCB` | a `SCHEDULE_COMPETITION` entry and the UID's masks go to `decodeBlockData`/`decodeGameTurn`. `savectrl[uid]` picks the save buffer |
| `0x2dc258` | `Sche_Block_decode_main2` | the competition entry layout |
| `0x2dc650` | `scheCtrl_InitGameDay` | game day *k* is the *k*-th set bit of the turn mask |
| `0x2dab38` | `getOneGameFromBlockAndGameIndex` | home = `pair[swap]`, away = `pair[1 − swap]` |
| `0x20a298` | `ScheEuro_TeamEntry::makeTeamEntryIDList` | the team-entry layout and its four record kinds |
| `0x20a4b8`, `0x20a5e0`, `0x20a828`, `0x20a770` | `LastRank_`, `NowRank_`, `List_`, `PlTeamId_TeamEntryProc` | what each record kind reads |
| `0x20ad10` | `ScheEuro_TeamEntryList::initMakeList` | the 9 `make_list` tables |
| `0x20b188` | `ScheEuro_TeamEntryList::requestMakeList` | `make_list` table 0 rows. The jump table at `0x52fb10` picks the source |
| `0x21dc60` | `Param::plRec_MatchRegulations(group)` | `REGULATION.TBB` row = UID. VS UIDs 148–163 can be overridden at runtime |

## Turns

A year has **96 turns**. `get_open_turn` returns `years × 0x60 + bit`, and
the masks are 12 bytes (96 bits). A schedule's games fall on the turns whose
bits are set in its mask, in order. Game day 0 is on the first set bit, and
so on.

## `SCHEDULE_SYSTEM.PAC`

| Entry | Name | Tables | Contents |
|---|---|---|---|
| 0 | `year_schedule_data.tbb` | 1 | 184 × 20 bytes: one row per UID plus 20 second-year rows |
| 1 | `open_nation.tbb` | 1 | 72 × 44 bytes: host nation of each competition |
| 2 | `make_list.tbb` | 9 | team-list definitions |
| 3 | `PeriodName.tbb` | 2 | round names (`initPeriodNameData` `0x209d90`). Not decoded |
| 4 | `savectrl.tbb` | 1 | 164 × u8, one save-buffer type per UID (values 0, 1, 2) |

### `year_schedule_data` row (20 bytes)

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | s16 | UID. **−1**: the second-year part of the row above it (20 rows). Such a schedule runs across the year end (`isOverYear` `0x20a0c0`) |
| `0x02` | u8 | start turn, at or before the first set bit (**empirical**). In a −1 row it is copied into the row above if that row's is `0xff` |
| `0x03` | u8 | end turn, `0xff` = none. A −1 row's value plus `0x60` is written into the row above |
| `0x04` | s8 | competition (`PLSCHE_COMPE`), 0–71 |
| `0x05` | u8 | year of the 4-year cycle when it starts (1–4), `0xff` = every year |
| `0x06` | u8 | load condition, see below |
| `0x07` | u8 | flag, unknown |
| `0x08` | u8[12] | turn mask: bit *t* set = a game day on turn *t* |

The load condition in `+6` decides whether a UID is loaded in each mode:

| Value | Normal mode | Rows |
|---|---|---|
| 0 | always | 69 |
| 1 | only if the competition's nation is the player's | 24 |
| 2 | only if it isn't | 24 |
| 3 | only if selected at runtime (`pwkEvCom_GetRuntimeSelectCompe`) | 25 |
| 4 | first-promotion mode only, own nation | 6 |
| 5 | VS mode only, when selected | 16 |

Values 1 and 2 come in pairs for the same competition. The own-league
version usually has more game days (UID 1 has 50 and UID 2 has 46), which
gives the player's league more fixtures on screen.

### `open_nation` row (44 bytes)

`{s16 compe, s16 start, s16 nation[20]}`, one row per competition, in
order. With `start == −1` the host is `nation[years % 20]`. Otherwise it is
`nation[((years + 1 − start) / 4) % 20]`, so the host changes every 4
years (World Cup and European Championship style). Only competitions
44–47 have a `start` (1–4). 57 of the 72 rows repeat one nation 20 times.

### `make_list` (9 tables)

Table 0 has 71 rows of 4 bytes, one per list kind (`eLIST_KIND`). A list
is filled on first use:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u8 | number of teams in the list |
| `0x01` | u8 | parameter: nation or region. For the `list` source, `value − 0x67` picks one of tables 3–8 |
| `0x02` | s8 | source: 0/1 UEFA coefficient, 2/3 club rank, 4/5 FIFA ranking, 6 fixed list, 7 domestic (the player's nation) |
| `0x03` | u8 | option passed to the source function |

Table 1 is `MAKE_UEFA_LIST` (77 × 4 bytes, `initMakeUefaList`
`0x20ae48`), table 2 has 4 rows, and tables 3–8 are the fixed lists. The
source functions (`getList_SRC_KIND_*`, `0x20b4a8`–`0x20bb50`) aren't
decoded yet.

## `SCHEDULE_COMPETITION.PAC` entry

A TBB with 3 tables (league) or 4 (knockout).

### Table 0: header (16 bytes)

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u16 | the UID. Not read by the game. Entry 81 says 80 |
| `0x02` | u16 | a competition number. Not read by the game, and not the `year_schedule_data` one |
| `0x04` | u8 | type: 0 league, 1 knockout |
| `0x05` | u8 | entrants |
| `0x06` | u16 | pairings |
| `0x08` | u16 | games |
| `0x0A`–`0x0F` | u8 × 6 | copied to the block at `+0x1a`, `+0x16`, `+0x17`, `+0x19`, `+0x18`, `+0x1b`. Zero in leagues. Unknown |

**Empirical:** a league has `n(n−1)/2` pairings and plays each twice or
once. A knockout has `n − 1` pairings (fewer for a single round: UID 4 has
28 entrants and 14 ties).

### Table 1: games (4 bytes each)

| Bits | Meaning |
|---|---|
| `w0` 0–7 | game day. Days run 0 to *d* − 1 with no gaps |
| `w0` 8–9 | unknown (0 or 1) |
| `w0` 10–13 | round (**empirical**): 1 final, 2 semi-final, 3 quarter-final, 4 last 16, 0 anything else |
| `w1` 0–8 | pairing index |
| `w1` 9–10 | home/away swap: home is `pair[swap]` |

### Table 2: pairings (2 bytes each)

`{u8 slot_a, u8 slot_b}`. In a league both are entrant slots. In a knockout
the first round names entrant slots and later rounds name winner slots
after them (for example `3c 3d` in the 32-team UID 6 final).

### Table 3: next pairing (knockout only, 2 bytes each)

`{u8 pairing, u8 side}`: where the winner of each pairing goes. A value at
or past the pairing count means the winner leaves this competition (the
final, and single-round ties that feed another UID).

### Game days and the turn mask

Game day *k* is played on the *k*-th set bit of the UID's turn mask
(`scheCtrl_InitGameDay`), counting the second-year row's mask after the
first. So the number of game days must equal the number of set bits. That
holds for 163 of 164 UIDs. **UID 117** has 6 game days (12 games) but only
3 bits. Its header says competition 34 where its neighbours (UIDs 114–121)
say 47, so it looks like a group from competition 34 (UIDs 59–66, 6 game
days each) left in the wrong slot. What the game does with the extra days
isn't known.

## `SCHEDULE_TEAM_ENTRY.PAC` entry

A TBB with 4 or 5 tables of 6-byte records. Table 0 is the header:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u8[2] | unknown |
| `0x02` | u8 | `LAST_RANK` records used |
| `0x03` | u8 | `LIST` records used |
| `0x04` | u8 | `NOW_RANK` records (0 = skip the table) |
| `0x05` | u8 | `PLTEAMID` records |

The four counts add up to the number of entrant slots. For every UID
except the runtime-selected ones, that equals the competition's entrant
count. Tables 1–4 hold the records, one kind per table:

| Table | Kind | `+0` | `+1` | `+2` | `+3` | `+4` (s16) | Team |
|---|---|---|---|---|---|---|---|
| 1 | `LAST_RANK` | slot | rank | shuffle | – | competition | the team that finished `rank` in that competition last season (`pwkRec_GetCompePastRecord`) |
| 2 | `LIST` | slot | first rank | last rank | – | list kind | a random team from ranks `first`–`last` of that `make_list` |
| 3 | `NOW_RANK` | slot | rank | shuffle | keep | UID | the team currently at `rank` in that UID's table. Skipped if that UID isn't loaded |
| 4 | `PLTEAMID` | slot | – | shuffle | – | team id | that club (`1`–`0x22d`) |

- **shuffle:** a non-zero value puts the slot into a random reshuffle
  (`RandamSort`).
- **keep:** a zero `+3` in a `NOW_RANK` record stores the source UID with
  the slot.
- **Special `LIST` kinds:** −4 is the host nation's national team, −3 is
  team 1, and any other negative kind leaves the slot empty. The 18
  runtime friendlies (UIDs 124–141) use −2.
- **Out-of-range team ids:** `PLTEAMID` ids outside 1–557 leave the slot
  empty. UIDs 156, 157, 162 and 163 use 558.

Because a `NOW_RANK` record for an unloaded UID is skipped, the same slot
can be listed once per alternative. UID 3 fills its 4 slots from UID 1
*or* UID 2, whichever was loaded.

### What decides the first season's leagues

A league's slots are `LAST_RANK` records. UID 0 takes ranks 1–20 of
competition 0 from last season. At the start of a new game,
`PLRRSRC_INITTEAMDATA.TBB` table 1 seeds those past records
(`pwkRec_SetPastRecordLastTeam`, see
[`PARAM_DIR.md`](PARAM_DIR.md#plrrsrc_initteamdatatbb-starting-leagues)).
So that table decides which clubs start in which division, and this pack
decides how they are placed.

## Related files

- `0SYSTEM/SCHEDULE.TBB` (2 tables, 76 and 23 rows of 32 bytes, with a
  similar turn bitmask) is **not referenced by name**. `CVS/ENTRIES` dates it
  January 2005, a year before these packs, so it is an older version of the
  schedule table.
- `PARAM/GROUP2COMPE.TBB` holds 166 × s16 values. It matches neither the
  `year_schedule_data` competition (91 of 164 differ) nor the header's
  `+0x02` (93 differ). Only the `SIMPRG.REL` load list names it.
- `PARAM/SCHEDULE_LIST.TBB`: which competitions run in which year of the
  4-year cycle ([`PARAM_DIR.md`](PARAM_DIR.md)).

## Still unknown

- Game bits `w0` 8–9, header bytes `0x0A`–`0x0F`, `year_schedule_data`
  `+7`, and the first two team-entry header bytes.
- `PeriodName.tbb`, the `make_list` source functions and tables 1–8, and
  the meaning of the `savectrl` values.
- `GROUP2COMPE.TBB` and `CLUB_RANK_SYSTEM.TBB`.

## Checking the claims

```bash
python SRC/schedule.py info  DAT/PARAM        # every entry; reports UID 117
python SRC/schedule.py year  DAT/PARAM        # the 184 year_schedule_data rows
python SRC/schedule.py compe DAT/PARAM 6      # a 32-team knockout: games, pairings, links
python SRC/schedule.py entry DAT/PARAM 6      # where its 32 teams come from
python SRC/sles_disasm.py ISO/SLES_541.51 dis Sche_Block_decode_main2 makeTeamEntryIDList
```
