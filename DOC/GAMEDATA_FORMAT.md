<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `GAME/GAMEDATA.BIN` and `GAME/AI_PARAM.BIN`

Two files of the match engine. `GAMEDATA.BIN` is a table of fixed-size
records that `GAMEPRG.REL` reads; `AI_PARAM.BIN` has no reader that can be
found. Neither has symbols to name its fields, so this is a partial decode.

`python SRC/gamedata.py info DAT/GAME` checks `GAMEDATA.BIN`.
`python SRC/gamedata.py dump DAT/GAME/GAMEDATA.BIN 2000 2010` prints records.

## `GAMEDATA.BIN`

**Confirmed from the game code** (`GAMEPRG.REL`, no symbols):

| Address | What it shows |
|---|---|
| `0x5378` | `gamedata.bin` is loaded into loader slot 10; `0x53c8` returns its data |
| `0x13abb8` | record *n* is the data + *n* × 0x30, so the file is an array of 0x30-byte records |
| `0x13abf0`, `0x13ac20`, `0x13ac58` | compare a record's s16 at `+0x4` with a given index and with another record's `+0x4` |
| `0x13ab80` | reads the s8 at `+0x8` and multiplies it by π/32 (`0x3dc90fdc`): an angle |
| `0x13ad00` | reads the s16 pair at `+0x20` / `+0x22` as a range a value is tested against |
| `0x45f44`–`0x45f84`, `0x98e68`–`0x98e94` | a kick request's s16 at `+0x1c` is a record number. The record's byte `+0x25` picks an entry of the kick kind's variant list (`0x58000`), and bits 16–18 of its u32 at `+0xc` pick how the kick's rating is scaled: 0 and 1 by the foot (`0x97be0`), 2 and up by the header parameter ([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#the-kick-kinds)) |

**Who looks records up** (**confirmed**): `0x13abb8` has 78 call sites,
in the player loader (`player::CPlayerLoadHandleInterface`'s code,
`0x26bf0`–`0x293bc`), `fb::Player` and `fb::PlayerCore`, the pass and
shot `DecisionFactor*` rate classes, the intentions, `PlayEffector`,
`PlayBallCarrierMark`, `PlayFollowBall`, `match::MatchManager`,
`match::PlayerManipulator`, `match::BallTask` and
`match::StatisticTask`. At `0x28478` the index is a player's word at
`+0x520`, in the per-player block of `*0x2a2344` (team × 0x3c80 + slot ×
0x580 + 0x30), so each player has a current record (probably the move
the player is making); bit 15 of the record's `+0xc` then sets a flag at
`+0xc8` of the loader's object (`0x28480`). Five calls pass the
constant 1408 (`PlayADribble` twice, `fb::Player`, `match::MatchManager`
twice).
`python SRC/snr2.py callers ISO/DLL/GAMEPRG.REL 0x13abb8` lists them.

**Empirical:** the file (198,288 bytes) is exactly 4,131 records. The
`+0x8` angles run from −32 to 32 (−180° to 180°), mostly in steps of 8
(45°). In records 0–41 the `+0x4` values pair records up (4 ↔ 5, 6 ↔ 7,
10 ↔ 11, ...; the rest point at themselves), which looks like mirrored
left/right twins. From record 42 on, `+0x4` holds small values shared by
many records (1 in 1,803 of them, 4 and 5 in about 300 each) and values up
to 10,208, so its meaning changes or isn't a record link there. The float
at `+0x14` is mostly a multiple of 2.2 (4.4 in 1,117 records, 6.6 in 925,
15.4, 2.2, 11.0). Many records are full of `0xff` and `0x00` filler.

A record describes a way of touching the ball. Over all 4,131 records
(**empirical**), the body part at `+0xc` bits 16–18 and the surface at
`+0x25` (an index into the variant names: 0 INSIDE, 1 OUTSIDE, 2 HEEL, 3
SOLE, 4 TOE, 5 INSTEP, 6 INFRONT, 7 OUTFRONT, 8 CHEST, 9 HEAD_STRONG, 10
HEAD_WEAK, 11 SLIDING, 12 CHIP, 13 OVERHEAD, 14 JUMPING_VOLLEY, 15
HEEL_VOLLEY, 16 DIVING_HEAD) agree:

| Part | Records | Surfaces |
|---|---|---|
| 0, 1 | 1,308, 1,086 | foot surfaces, in nearly the same mix (INSIDE 601 / 433, INSTEP 403 / 359, INFRONT 150 / 150): the two feet |
| 2 | 353 | HEAD_STRONG 122, HEAD_WEAK 216, DIVING_HEAD 15: the head |
| 3 | 40 | CHEST, all of them |
| 4 | 1,344 | 255 (none) in 1,148, a foot surface in the rest |

The rest of a record isn't decoded. 4,131 doesn't match the entry count
of any motion pack (`PLAYERMOTION.HED` has 1,008 entries, `OPTMOTION.PAC`
927, `BALLMOTION.PAC` 324).

## `AI_PARAM.BIN`

1,868 bytes: 467 f32 values (0.12, 0.4, 0.2, 0.26, 0.0, 0.02, 1.0, 0.33,
...). **Empirical:** no file name in `SLES_541.51` or any overlay refers to
it, and none of them holds a copy of its data (four 32-byte samples were
searched for). So no reader can be found. It may be unused by the retail
game, but that isn't confirmed. It isn't a copy of the match's built-in
tuning table either (`GAMEPRG.REL 0x270000`, 1,951 entries, see
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#where-the-match-reads-the-parameters)),
whose values sit between kind words: at the best alignment only 41 of the
467 values match.

## Still unknown

- The rest of a `GAMEDATA.BIN` record's fields, and which foot parts 0
  and 1 are.
- What sets a player's action word (`+0x520`), what record 1408 is, and
  which callers use `0x13ab80`–`0x13ad00`'s comparisons for what.
- Whether anything loads `AI_PARAM.BIN` by another route.

## Checking

```bash
python SRC/gamedata.py info DAT/GAME
python SRC/gamedata.py dump DAT/GAME/GAMEDATA.BIN 0 50
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 13ab80 100 --sles ISO/SLES_541.51
```
