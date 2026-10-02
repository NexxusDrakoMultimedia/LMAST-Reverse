<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Play books: `GAME/PLAYBOOK.BPB` and `GAME/COMBINATION.BPB`

The play books hold the movements of the players and the ball in the
match AI's set plays and moves: one path per player (and one for the
ball), each a list of points in metres on the pitch. `GAMEPRG.REL` loads
`playbook.bpb` ([`GAME_DIR.md`](GAME_DIR.md)), and
`Pwk::PlayBookData::CPlayBookDataBase` in `SLES_541.51` reads it.

`python SRC/bpb.py info DAT/GAME` checks both files.
`python SRC/bpb.py dump DAT/GAME/PLAYBOOK.BPB 0` prints one play's paths.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x2e82b0` | `CPlayBookDataBase::makeBookTop` | the file is a u32 record count, then the records back to back; each record starts with its u16 size |
| `0x2e8280` | `CPlayBookDataBase::getHeader` | a record is fetched by index (out of range gives record 0) |
| `0x2e7ec8` | `CPlayBookDataBase::GetPLAYBOOK` | the record fields below; it builds an `IBOOK` from them |
| `0x2e8338` | (no symbol) | a point coordinate is (value >> 3) / 64, negated if bit 2 is set; bits 0–1 are a code |
| `0x2e8468` | `IBOOK::GetBallFlowID` | the bytes at `+0x18`, up to 4 (`0xff` = none) |
| `0x2e8370` | `Pwk::PlayBookData::SplitID` | how a play id maps to a record index (below) |

A record:

| Offset | Type | What |
|---|---|---|
| `0x00` | u16 | record size |
| `0x04` | u32 | flags: bit 0 and bit 1 set a mode at `+0x28` of the reader, bit 2 a flag at `+0x2c` |
| `0x08` | u16 | the end of the fixed header (0x20 in `PLAYBOOK.BPB`, 0x1c in `COMBINATION.BPB`, empirical) |
| `0x0a` | u16 | offset of n u16: the number of points in each path |
| `0x0c` | u16 | offset of n u16: the frame each path starts on (`GetNumPathStartFrame`) |
| `0x0e` | u16 | offset of the points, 4 bytes each, as many as the first array adds up to |
| `0x12` | u16 | offset of n u16: each path's kind |
| `0x16` | u16 | n, the number of paths |
| `0x18` | 4 × u8 | the ball's route: the paths it goes to, `0xff` for none |
| `0x1c` | u16 | read into the reader's `+0x30`; not traced |

A point is two u16, x then y. Each is a coordinate in metres
((value >> 3) / 64, bit 2 the sign), and the two low bits of each make a
code: y's × 10 + x's. The reader keeps the coordinates as floats and the
code as an int.

**Play ids.** `SplitID` turns a play id into a record index in four
ranges: ids below `0x1000` are (id >> 8) × 10 + (id & 0xff), records
0–99; `0x1000`–`0x3fff` are (id >> 12 − 1) × 32 + ((id >> 8) & 0xf) × 8
+ 100 + (id & 0xff), records 100–195; `0x4000`–`0x6fff` are
((id − 0x4000) >> 12) × 20 + 196 + (id & 0xff), records 196–255; from
`0x7000` on, id − `0x7000`. What the four ranges are (attack patterns,
set pieces, ...) isn't traced.

## Empirical

`PLAYBOOK.BPB` (65,112 bytes) holds 256 plays, 2,594 paths and 7,221
points, and its records end exactly at the end of the file. 196 plays
have 12 paths, the others 3–5. Every play has exactly one path whose
kind has high byte `0xfe`: the ball. In play 0 the ball starts at (33.0,
51.5), at a corner flag of a 68 × 105 m pitch (goal line at y = 52.5),
and its route goes to path 1; ten other paths are runs into the box. So
x runs across the pitch and y along it, in metres from the centre spot.
Other kind high bytes are 13, 15–22 and 26 (players) and 249–253. The
point codes are 0, 1, 2, 3 and 20; they change along a run (20, then 2,
then 1 near its end), so they look like movement styles.

`COMBINATION.BPB` (4,516 bytes) parses with the same layout: 30 records
of 4–5 paths, 528 points, a 0x1c-byte header, path kinds all 0 and no
ball route. Its reader (`fb::Combination` per [`GAME_DIR.md`](GAME_DIR.md))
isn't traced, so the layout match is empirical.

## `COMBINATION2.CBB` and `.CSB`

`GAMEPRG.REL` loads `combination2.csb` into loader slot 5 and
`combination2.cbb` into slot 6 (`0x5120`, `0x5170`). The two files hold
540 combinations each. **Confirmed from the game code:**

| Address (`GAMEPRG.REL`) | What it shows |
|---|---|
| `0xc7e84` | the `.CBB` is a u32 count, then records that each start with their u16 size; the code keeps a pointer to each, like `makeBookTop` |
| `0xc77c4` | combination *n*'s script is block *n* of the `.CSB`, an `etc::PackData` ([`PLAYER_DIR.md`](PLAYER_DIR.md)); the block is PRS-compressed and `Press::Expand` unpacks it into a 0x800-byte buffer |
| `0xc5fc8`–`0xc610c` | the scripts' command set, built at `0x29fc90`: table 0 is the shared Base table, tables 1–3 are empty, and table 4 has 29 commands (argument counts at `0x274790`, callbacks at `0x249280`) |

**Empirical:** every `.CSB` block (type 17) unpacks as plain PRS into a
TBB holding one `SQB1` script ([`SQB_FORMAT.md`](SQB_FORMAT.md)), 160–960
bytes. 539 of the 540 decode with the combination set; script 382 has
three stray words after its `End`. The scripts wait in loops on
conditions (`Combi14`, `JumpIfZero`) and step through the move, so they
look like the timing of each combination. The 29 commands have no
symbols and are named `Combi0`–`Combi28`. `python SRC/sqb.py dis
"DAT/GAME/COMBINATION2.CSB#2"` prints one.

The `.CBB`'s 540 records end exactly at the end of the file and are 52,
56, 60 or 68 bytes. Each starts `{u16 size, u16 4, bytes 3, 8, 12, 16,
40, 48}` (the same in every record), and the rest is full of `0xcd`,
`0xbb`, `0xaa` and `0x97` bytes, the fill patterns of uninitialised
memory, so the records are C structs written with their padding. The
code at `0xc7f00` reads small items as a type byte and s8 values × 10.0
(positions in units of 10?). The fields aren't decoded.

## Still unknown

- The block at `+0x20` (before the first array) and `+0x10`, `+0x14`,
  `+0x1c`; the flags.
- What the path kinds and point codes mean, and which play is which
  (the id ranges, and `TACTICS_PLAYBOOK_EDIT.TBB`'s link to them).
- `CPlayBookDataBase::GetFormationData` (`0x2e7d88`, `IFORM`).
- The fields of the `.CBB` records, and what the 29 combination commands
  do (their callbacks at `GAMEPRG.REL 0x249280` have no symbols).

## Checking

```bash
python SRC/bpb.py info DAT/GAME
python SRC/bpb.py dump DAT/GAME/PLAYBOOK.BPB 0
python SRC/sles_disasm.py ISO/SLES_541.51 dis GetPLAYBOOK__Q33Pwk12PlayBookData makeBookTop SplitID
```
