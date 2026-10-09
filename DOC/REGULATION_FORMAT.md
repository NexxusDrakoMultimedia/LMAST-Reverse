<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/REGULATION.TBB`: match regulations

Each schedule (a league division, a cup round, a group) has one row of
rules here: how many clubs it has, the win bonus and the prize money by
final position, the yellow cards that ban a player, the matchday squad,
the foreign-player limit, the number of substitutions, and which places
lead up or down to which competition. The file is a TBB1 file
([`TBB_FORMAT.md`](TBB_FORMAT.md)) of one table with a line size of 2:
165 rows of 120 bytes, each 60 s16 fields.

Rows are indexed by the schedule UID (`PLSCHE_GROUP`, 0–163,
[`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)). Row 164 belongs to no
schedule.

`python SRC/regulation.py info DAT/PARAM` checks every row.
`python SRC/regulation.py show DAT/PARAM/REGULATION.TBB 0` prints a row
with its fields named. `set` edits fields ([below](#editing)).

## Who reads it

| Address | Symbol | What it shows |
|---|---|---|
| `0x21dc60` | `Param::plRec_MatchRegulations(PLSCHE_GROUP, int)` | loads `Regulation.tbb` (`F04_…`, folder 4) as a resource and returns table 0 + `group * 0x78` (`0x21dd18`). **confirmed** |
| `0x21dc74` | same | returns the in-game copy at `0x5eacb4` instead when `0x5eacb0` holds the group |
| `0x21dcf8` | same | for groups `0x94`–`0xa3` (UIDs 148–163, the VS mode) with the second argument set, returns the VS copy at `0x5ead30` |
| `0x21dd38` | `plRec_SetMatchRegulationsInGame(group)` | copies a row to `0x5eacb4` and the group to `0x5eacb0` (from `CScheEuro::initializeOneMatch`, `0x203b30`) |
| `0x21de78` | `plRec_SetVSMatchRegulations(group, const PlMatchRegulations*)` | copies a row to `0x5ead30` for groups 148–163 |
| `0x206e18`–`0x206e28` | `CScheEuro::TeamEntryLoadCompCB` | the VS override: `+0x4c` and `+0x4e` from one option byte, `+0x52` from another or 25 |
| `0x212280`–`0x2123b4` | `PlGiTask::ResetGameIf` | copies `+0x50`, `+0x4c`, `+0x4e`, `+0x52`, `+0x06`, `+0x08`–`+0x49` and `+0x00` into the match's rule block (`GetRulePointer`, `PlGiTask + 8`) |
| `0x2a7670`–`0x2a769c` | `WP::CTacticsBase` (`getRegulationData`, `+0x6ad8`) | the tactics screens take `+0x4a`–`+0x52` as 5 ints |

Other overlays don't import `plRec_MatchRegulations` except `SIMPRG.REL`
(`0x9609c`, `0x141f10`, `0x15d898`, `0x15d8f8`, `0x15d9f8`). The file is
also entry 9 of all seven `PRELOAD/SIMFILE*.PAC`
([`REBUILD.md`](REBUILD.md)).

## Row layout

All fields are s16 (read with `lh`).

| Offset | Name (`regulation.py`) | Meaning | Proof |
|---|---|---|---|
| `0x00` | `grade` | match grade, 0–5 (the game's `PlMatchGrade`). 0 is the top: the European and national-team competitions | `pwkSche_RecalcAudience` passes it as the `PlMatchGrade` of `pwkUnkei_GetAllAudience` (`0x255b1c`). `pwkDissatis_CompeEnd` indexes a 6-float table at `0x391c18` with it (`0x23a840`). Also read by `pwkOteam_GetTeamData`, `pwkTeam_PopUpdateTurnly`, `pwkTeam_GameCheck` and `plPinfo_UpDownKeymanCaptaion`. **confirmed** |
| `0x02` | `clubs` | number of clubs | `SIMPRG.REL 0x960b0` puts it in a message as a number. **confirmed**. Equals the team-entry slot count for 163 of 164 UIDs (**empirical**, below) |
| `0x04` | `unk04` | values 0, 1, 2, 3, 14, 18, 19 | no reader found |
| `0x06` | `prize_kind` | 2: the prizes are scaled by the UEFA rank of the player's nation | `plRec_GetMatchBonus` (`0x21e2ec`). **confirmed**, below |
| `0x08` | `win_bonus` | the bonus for a win, in units of 10,000 | `pwkUnkei_GetMatchIncome` (`0x2732b8`): `+0x08` × 10,000 into the match record's `+0xc`, income type 5 "Win bonus" ([`SAVE_FORMAT.md`](SAVE_FORMAT.md)). **confirmed** |
| `0x0a`–`0x48` | `prize1`–`prize32` | prize money for final positions 1–32, in units of 10,000 | `plRec_GetMatchBonus(regs, rank)` reads `+0x0a + 2 × rank` for rank 0–31 (`0x21e2d4`: `rank + 1 < 0x21`). `SIMPRG.REL 0x133844` books it × 10,000 as income 6 "Position prize money". **confirmed** |
| `0x4a` | `ban_yellows` | yellow cards that ban a player; 0 or less never bans | `CDetailManager::ConvertPlayer_CompeRecord` (`0x2851d4`): banned when the player's yellows ≥ this, or after a red card. **confirmed** |
| `0x4c` | `squad` | players named for a match (11 starters and the bench) | the tactics player list puts its bench line at `squad − 11` (`0x2a37ac`); `pwkOteam_IsStartingMemberExistForGame` checks bench slots 11 to `squad − 1` (`0x24c6b0`). **confirmed** |
| `0x4e` | `squad2` | equal to `squad` in every row | the VS override writes both from one byte (`0x206e28`); `ResetGameIf` copies it to the rule block `+0x18`. No reader of that copy found |
| `0x50` | `foreigners` | foreign players allowed in the matchday squad | `pwkOteam_IsStartingMemberExistForGame` (`0x24c6cc`, counting with `plPinfo_IsForeigner`) and `plTeam_RegSel` (`0x2a7744`). **confirmed** |
| `0x52` | `subs` | substitutions allowed | `CBackMatch` (the matches played in the background, `SIMPRG.REL 0x172b5c`) substitutes only while its count is below this. **confirmed** |
| `0x54`–`0x77` | `down1`, `down2`, `up1`–`up4` | six place slots of `{s16 count, s16 compe, s16 uid}` | `plRec_getNextCompetitionData` (`0x21df60`). **confirmed**, below |

### Prizes and the UEFA rank

`plRec_GetMatchBonus` (`0x21e278`) returns the prize for a final position.
When `prize_kind` is 2 it multiplies the prize by a percentage from
`0x533b88`, indexed by the UEFA rank − 1 of the player's nation
(`pwkLg_GetMyNati`, `pwkRec_GetUefaNation` byte `+2`), then divides by 100:

| UEFA rank | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| Percent | 120 | 110 | 105 | 100 | 90 | 80 |

Other kinds pay the prize as written. 66 rows have kind 2 and prizes, 5
have kind 1 (UIDs 82–86, the runtime cups), and 94 have kind 0 and no
prizes (**empirical**). The kind also picks the message `SIMPRG.REL`
shows with the prize (`0x1337f4`). The first-division winner's prize is
7,500 (£75,000,000 before the percentage).

### Place slots

`plRec_getNextCompetitionData(out, group, clubs, upper, nation)`
(`0x21df60`) turns the slots into rank ranges. Its caller is
`CScheEuro::getNextCompetition_ScheEuro` (`0x207d1c`), which passes the
schedule's club count (`getEntryTeamMax`) and the competition's host
nation (`getOpenNation`).

- `upper` set: slots `up1`–`up4` (`+0x60`, 6 bytes apart), counted from
  the top. Otherwise `down1`–`down2` (`+0x54`), counted from the bottom.
- The walk stops at the first slot whose count is 0 (`0x21dfe8`,
  `0x21e1cc`), so a slot after it is never read.
- Each slot gives `count` ranks to `{compe, uid}`, written as a 12-byte
  `{s32 compe, s32 uid, s16 first, s16 last}` record (ranks from 0).
- A `count` of −1 is taken from the host nation's UEFA rank. The tier is
  (rank − 1) / 3, so ranks 1–3 are tier 0 and 4–6 tier 1. The table depends
  on `compe` (33, 34, 35), or on `uid` when `compe` is −1 (jump table
  `0x533b30` for uid 58–75):

  | Slot target | Tier 0 | Tier 1 | Table |
  |---|---|---|---|
  | compe 33, or uid 58 | 2 | 1 | `0x533b10` |
  | compe 34, or uid 59–66 | 2 | 2 | `0x533b18` |
  | compe 35, or uid 68–75 | 3 | 3 | `0x533b20` |

  Any other target gives no places (`0x21e16c`). That is the case for the
  `up2` slot of UIDs 103–110 (−1 to uid 113).

**Empirical**, from the schedule packs: compe 33 is UID 58, compe 34 UIDs
59–67 and compe 35 UIDs 68–76, the European competitions; the first
division of England (UID 0) sends 3 clubs down to compe 1 (its second
division) and gives places to compe 34, 33, uid 68 and 2 to compe 36.
The second division (UID 1) sends 2 up to compe 0 and 4 to compe 2 (the
play-off, UID 3). `python SRC/regulation.py show` lists every row's
places.

The slots feed the game's checks of whether a club has clinched a place
or is still within one (`CScheEuro::checkWinupFixedness`,
`checkLosedownFixedness`, `checkWinupWithin`, `checkLosedownWithin`,
`0x207ee8`–`0x208068`). `GAMEPRG.REL` (`0x9f5e8`, `0x1b44d4`, `0x1b4738`,
`0x1b4ba8`) calls `plRec_getNextCompetitionData` too, and
`SIMPRG.REL 0x15d8f0` takes the smallest `clubs − count` of the two down
slots. Which clubs really change division next season comes from the
`LAST_RANK` records of `SCHEDULE_TEAM_ENTRY`
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)), not from these slots, so a
changed count should be matched there.

### What the rows hold

**Empirical**, `python SRC/regulation.py info DAT/PARAM`:

| Field | Values (rows) |
|---|---|
| `grade` | 0 (46), 1 (11), 2 (11), 3 (42), 4 (13), 5 (42) |
| `win_bonus` | 0 (72), 30 (19), 60 (43), 90 (19), 120 (9), 150 (3) |
| `ban_yellows` | 2 (48), 3 (58), 5 (40), 255 (19) |
| `squad`, `squad2` | 16 (32), 18 (62), 23 (36), 25 (35) |
| `foreigners` | 2, 3, 16 (1 each), 5 (59), 18 (32), 23 (36), 25 (35) |
| `subs` | 3 (130), 5 (18), 14 (17: rows 148–164) |

The first divisions are grade 2 and the second divisions grade 3.
`clubs` equals the number of team-entry slots
(`SCHEDULE_TEAM_ENTRY`) for 163 of the 164 UIDs; UID 123, a runtime
schedule with no slots, says 10. All 165 rows fit the layout.

The Japanese file differs in one field: UID 31 (Italy's play-off) has a
win bonus of 0, where PAL has 60.

## Editing

```bash
python SRC/regulation.py set DAT/PARAM/REGULATION.TBB out/REGULATION.TBB 0 subs=5 win_bonus=120
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/REGULATION.TBB=out/REGULATION.TBB --copies
```

`set` takes a UID, then `field=value` pairs, and may name several UIDs.
It refuses values the code can't use (`grade` 0–5, `squad` and `squad2`
11–25, `compe` −1–71, `uid` −1–163, `count` −1 or more) and a slot left
after a count of 0. The file keeps its size. `--copies` also patches the
seven `PRELOAD/SIMFILE*.PAC` copies. `python SRC/regulation.py roundtrip`
re-encodes every row and checks that the file rebuilds byte for byte.
No edit has been tested in PCSX2 yet.

## Still unknown

- `+0x04`: no reader found.
- Who reads the match rule block's copy of `squad2` (`+0x18`).
- Whether row 164 is ever read.
- What the place checks change on screen or in the match (news, the
  league table, the match's stakes), and what `SIMPRG.REL 0x15d958` does
  with the down slots.

## Checking the claims

```bash
python SRC/regulation.py info DAT/PARAM
python SRC/regulation.py show DAT/PARAM/REGULATION.TBB 0 1 59
python SRC/regulation.py roundtrip DAT/PARAM/REGULATION.TBB
python SRC/sles_disasm.py ISO/SLES_541.51 dis plRec_MatchRegulations plRec_GetMatchBonus
python SRC/sles_disasm.py ISO/SLES_541.51 addr 21df60 160     # plRec_getNextCompetitionData
python SRC/sles_disasm.py ISO/SLES_541.51 addr 2a7670 12      # the tactics screens' copy
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 133844 10 --sles ISO/SLES_541.51   # prize income x 10,000
```
