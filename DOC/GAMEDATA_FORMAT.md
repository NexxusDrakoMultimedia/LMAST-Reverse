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

**Empirical:** the file (198,288 bytes) is exactly 4,131 records. The
`+0x8` angles run from −32 to 32 (−180° to 180°), mostly in steps of 8
(45°). In records 0–41 the `+0x4` values pair records up (4 ↔ 5, 6 ↔ 7,
10 ↔ 11, ...; the rest point at themselves), which looks like mirrored
left/right twins. From record 42 on, `+0x4` holds small values shared by
many records (1 in 1,803 of them, 4 and 5 in about 300 each) and values up
to 10,208, so its meaning changes or isn't a record link there. The float
at `+0x14` is mostly a multiple of 2.2 (4.4 in 1,117 records, 6.6 in 925,
15.4, 2.2, 11.0). Many records are full of `0xff` and `0x00` filler.

What a record stands for isn't known. 4,131 doesn't match the entry count
of any motion pack (`PLAYERMOTION.HED` has 1,008 entries, `OPTMOTION.PAC`
927, `BALLMOTION.PAC` 324).

## `AI_PARAM.BIN`

1,868 bytes: 467 f32 values (0.12, 0.4, 0.2, 0.26, 0.0, 0.02, 1.0, 0.33,
...). **Empirical:** no file name in `SLES_541.51` or any overlay refers to
it, and none of them holds a copy of its data (four 32-byte samples were
searched for). So no reader can be found. It may be unused by the retail
game, but that isn't confirmed.

## Still unknown

- What a `GAMEDATA.BIN` record is, and the rest of its fields.
- Who calls the record functions at `0x13abb8`–`0x13ad00`, and with what
  index.
- Whether anything loads `AI_PARAM.BIN` by another route.

## Checking

```bash
python SRC/gamedata.py info DAT/GAME
python SRC/gamedata.py dump DAT/GAME/GAMEDATA.BIN 0 50
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 13ab80 100 --sles ISO/SLES_541.51
```
