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

**The starting positions** (`GetFormationData`, `0x2e7d88`, into an
`IFORM`): the block from the end of the fixed header (`+0x08`) to the
first array:

| Offset | Type | What |
|---|---|---|
| `+0x00` | u16 | the block's size (**empirical**) |
| `+0x02` | 2 bytes | `00 01` in every play; not read |
| `+0x04` | u16 | *n*, the players placed |
| `+0x06` | u16 | the play's kind: 1 in records 0–99, 2 in 100–195, 3 in 196–255 (**empirical**) |
| `+0x08` | *n* × 2 u16 | each player's start, x then y, coded like the points; the reader takes at most 22 values |

**Empirical:** *n* is 11 in the 196 twelve-path plays and the number of
non-ball paths in the others, and play 0's first spot (33.6, 52.1) is at
the corner flag, where its ball starts.

**Path kinds** (**confirmed**). `0x109598` splits a kind into the role
type (high byte), a value (bits 0–6) and a flag (bit 7). The set-play
code takes the role for a type from a pool the role factory fills
(`0x109ca0` calls `0x114f30` for types 13–33; `0x1097f8` returns slot
type − 13), and the factory's jump table (`0x27a4d0`) gives the class
each type makes. The types the play book uses:

| Type | Class | Paths in `PLAYBOOK.BPB` |
|---|---|---|
| 13 | `fb::RoleCKKicker` | the corner taker, one in each of records 0–99 |
| 15 | `fb::RoleSP` | the free-kick taker (records 100–195) |
| 16–22 | `fb::RoleSP`, except 18 `fb::RoleSPRecvSC1` and 19 `fb::RoleSPRecvSC2` | runners with a special job |
| 26 | `fb::RoleSPAttacker` | most paths (1,845): the attackers' runs |
| 254 (`0xfe`) | – | the ball |
| 249–253 | none: not role types | only in records 196–255 |

**The value and the flag** (**confirmed**). `0x108bd8` hands a path's
type, value and flag to the set-play assignment, which keeps them per
path at `+0xe4`, `+0xe8` and `+0xec` (`0x12efd8`; records of 0x14
bytes, 0xdc per side). When the flag is set, `0x12d1d8` stores a
16-byte position from the set play's own record for that path (0x70
bytes each, `+0x20`) and `0xf53d8` adds it to every point of the path
(`0x12d214`), so a flagged path is drawn relative to that position
instead of the pitch. No reader of the value at `+0xe8` was found.
**Empirical**, over records 0–195: the value is 0 in all 1,845
attackers' paths (type 26) and 0–6 for the takers and runners; the flag
is set on 73 paths, most of them type 16 (37) and type 18 (11).

For reference, the factory's other types: 0 `RoleGoalKeeper`, 1
`RoleBallCarrier`, 2 `RoleBallCarrierMarker`, 3 `RoleSupporter`, 6
`RoleSpaceMarker`, 7 `RoleSpaceMarkCover`, 9 `RoleKOKicker`, 10
`RoleKOReceiver`, 12 `RoleGKKicker`, 14 `RoleFKKicker`, 27
`RoleCKGoalKeeper`, 28 `RoleSPDefender`, 29 `RoleSPMarker`, 30
`RoleFKWall`, 31 `RoleFKMove`, 32 `RolePKKicker`, 33 `RolePKKeeper`, 38
`RoleSAAttacker`, 40 `RoleSCAttacker`, 41 `RoleFakeAttacker`, 42–44
`RoleFreeRunCommon`, 45 `RolePassAndGo`, 47 `RoleCombination`. `0x108c18`
also maps some types before use: 14, and 15 and 16 when its third
argument is 0, become 14; 23–25, 28, 29, 31 and any type outside 13–32
become 28.

**Point codes.** The play setter (`0x108d00`) scales each point by 10
(to the match's tenths of a metre) and passes its code to `0xf4c18`,
which keeps it at `+0x10` of the path's 32-byte entries (`0xf52f0`
returns entry *i*, `0xf5338` the count).

**What a code does (confirmed).** `fb::PlaySPAttack` and `fb::PlaySP_TP3`
(vtables `0x256758`, `0x256590`) walk a player along his path with
`0x104c90`. When the player reaches a point, it moves on to the next and
switches on that point's code (`0x104e98`): codes 0, 1, 2 and 20 pick a
method pointer at `0x278dd0` + 8 × *k*, which gives the player a move
order toward the point, facing along the path (the angle from
`0x1c5ff0`). The order is the type-1 order at the player's `+0x5c`
(`0x1120b8`), with the target at `+4`, the angle at `+0x1c` and a kind
at `+0x20`:

| Code | Method | Order kind |
|---|---|---|
| 0 | `0x112320` | 8 |
| 1 | `0x112428` | 1 |
| 2 | `0x112480` | 2 |
| 20 | `0x1123d0` | 4 |

Any other code gives no order at that point, so the player goes on
with the order he has. `fb::PlayRunOnPath` (`0x103900`, vtable
`0x2551b8`) copies a point's code with it but never reads it.

**Empirical** (`python SRC/bpb.py info DAT/GAME`): the players' points
in `PLAYBOOK.BPB` use codes 0 (118), 1 (3,394), 2 (2,277), 3 (1) and 20
(413); in `COMBINATION.BPB` 0 (78), 1 (212), 2 (150) and 3 (88). The
ball's points use only 1, 2 and 3, and no reader of them was found.

**Play ids** (`SplitID`, `0x2e8370`, gives a type, a group and an
index; `GetPLAYBOOK` turns them into a record):

| Ids | Type | Record |
|---|---|---|
| below `0x1000` | 0 | (id >> 8) × 10 + (id & 0xff): 0–99 |
| `0x1000`–`0x3fff` | id >> 12 (1–3) | (type − 1) × 32 + ((id >> 8) & 0xf) × 8 + 100 + (id & 0xff): 100–195 |
| `0x4000`–`0x6fff` | −1 | ((id − 0x4000) >> 12) × 20 + 196 + (id & 0xff): 196–255 |
| `0x7000` on | −2 | id − `0x7000` |

## Which play is which

**Confirmed.** `GAMEPRG.REL` asks for a play in one place, the play
setter `0x108d00`. Only two functions call it, both from
`match::MatchManager`'s set-piece start (`0x1a3990`):

- **Corners** (set-piece type 2, `fb::CSetPlayAssign_CK`, `0xb8560`):
  `0x109a78` takes a random 0–99. Below 70 it shuffles the 10 ids at
  `0x2796d0`, records 2, 9, 11, 13, 21, 27, 50, 59, 81 and 89, and
  otherwise the 6 at `0x2796e8`, records 40, 42, 46, 47, 78 and 79; the
  first after the shuffle (`0x109b60`) is the play.
- **Free kicks** (type 4, `fb::CSetPlayAssign_FK`, `0xb85b0`): `0x12f860`
  sorts the ball's spot, turned to the attacking direction, into a zone:
  1 or 2 (left, right) within 12 m of the goal line (y ≥ 40.78 m); 3, 0
  or 4 (x ≤ −12 m, the middle, x > 12 m) 12–30 m from it (y ≥ 22.78 m);
  5, no play, further out. `0x109958` makes zone 0 group 0, zones 3–4
  group 1 and zones 1–2 group 2, then draws a random 0–99 against
  `0x2793d0` (80, 60, 10): below it, one of the 8 ids at `0x279670` +
  group × 16, else one of the 8 at `0x2796a0` + group × 16, shuffled the
  same way. The ids are type 1, 2 and 3 for groups 0, 1 and 2:

  | Group | Zones | Below the threshold: a direct shot | Otherwise: a pass first |
  |---|---|---|---|
  | 0 | the middle, 12–30 m | 100, 108, 116, 124 | 102, 103, 104, 105, 115 |
  | 1 | wide, 12–30 m | 132, 149 | 141, 143, 145, 155, 162 |
  | 2 | within 12 m | 164, 180, 181 | 167, 178, 179, 192, 193 |

**What the lists hold (empirical**, from the plays' ball routes,
`python SRC/bpb.py dump DAT/GAME/PLAYBOOK.BPB <record>`). Every ball
route ends at the goal, (0, 53.0) m. In each free-kick group the first
list's plays send the ball from the spot straight there, a shot, and
the second list's plays pass to a team-mate first (one to three
passes). So the thresholds are the chance of a direct shot: 80% from
the middle, 60% from wide and 10% from near the goal line. Of the
corners, the 70% list's ten are all a cross from the flag into the box
(the ball's first stop at x −12.0 to +8.9 m, y 42.2–49.6 m), and the
30% list's six are all short corners, played first to a team-mate on
the flag's side (x 20.2–28.9 m). All 100
corner records start at the same flag, (33.0, 51.4).

So a match can use 40 of the 256 plays: 16 corners and 24 free kicks.
Records 196–255, the type −1 range, are never asked for: no code builds
an id from `0x4000` to `0x6fff`, and their path kinds (249–253) aren't
role types. Within the 100 corner records the groups are loose themes
at most: short corners (a first pass to x > 19 m) are records 30–36,
40–42, 45–49, 78–79 and all of 90–99 (to a team-mate beside the flag),
and the rest go straight into the box.

**`COMBINATION.BPB` is the tactics screen's.** Its copies in the
`PRELOAD/TACTICS*` packs (all 14 identical to `GAME/COMBINATION.BPB`)
are what the tactics screen loads, and its Play Book page
(`CTacticsMenuTeamTacticsImplement::l_playbook_edit_get_playbookdata`,
SLES `0x2faf80`) asks for attack pattern *p* (1–30, `PlTeamAttack`
byte 0) as id `0x7000` + *p* − 1: record *p* − 1. So its 30 records are
the 30 attack patterns' diagrams, in the order `LS00`–`LS05`, `RS`,
`CT`, `CA`, `PO` ([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)), and the
screen's list (`CPlayBookList::MakeList`, `0x2f9618`) shows the club's
choices from `PlTeamData +0x498c`/`+0x498f`, the bytes the match takes a
user's club's attack patterns from
([below](#how-a-team-uses-the-combinations)).

## Empirical

`PLAYBOOK.BPB` (65,112 bytes) holds 256 plays, 2,594 paths and 7,221
points, and its records end exactly at the end of the file. 196 plays
have 12 paths, the others 3–5. Every play has exactly one path whose
kind has high byte `0xfe`: the ball. In play 0 the ball starts at (33.0,
51.5), at a corner flag of a 68 × 105 m pitch (goal line at y = 52.5),
and its route goes to path 1; ten other paths are runs into the box. So
x runs across the pitch and y along it, in metres from the centre spot.
The other kinds are in the table above. The point codes are 0, 1, 2, 3
and 20; they change along a run (20, then 2, then 1 near its end), so
they look like movement styles. Path kind values (bits 0–6) are 0–6
(0 in 2,210 of the 2,338 player paths) and the flag (bit 7) is set in
73 paths, all in free-kick records (101–195).

`COMBINATION.BPB` (4,516 bytes) parses with the same layout: 30 records
of 4–5 paths, 528 points, a 0x1c-byte header, path kinds all 0 and no
ball route. It is read by the same `CPlayBookDataBase` code on the
tactics screen ([above](#which-play-is-which)).

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

### `.CBB` records

**Confirmed** from `fb::CombinationSequencer`'s reader (`GAMEPRG.REL
0xc7a78`). Offsets in the header are bytes counted from the record +
the u16 at `+0x02`, which is 4 in every record:

| Offset | Type | What |
|---|---|---|
| `+0x00` | u16 | record size |
| `+0x02` | u16 | the base the offsets below count from (4) |
| `+0x04` | u8 | *n*, the number of slots |
| `+0x05`, `+0x06` | u8 | offsets of blocks A and B |
| `+0x07` + *i* | u8 | offset of slot *i*; slot 0 is block C |

| Block | Layout |
|---|---|
| A | u8 kind; kind 1 is followed by two u8 values |
| B | u8 kind; kind 2 is followed by one u8 value |
| C | u16, 2 pad bytes, 4 × u32, then 2 × u16 each × 10.0; when the first is non-zero and the second zero, the second becomes 1055.6 (`0xc7bc8`) |
| slot 1 … *n* − 1 | u8 type 0–7 (jump table `0x274a60`). Type 0: two u8, the second × 10. Types 1, 3, 4, 5: an area. Types 2 and 6: a u8, then an area. Type 7: three u8, the last × 10 |
| area (`0xc7f00`) | u8 shape, s8 x, s8 y, then for shape 0 an s8 radius, for others s8 x2, s8 y2; all × 10.0 |

`fb::COMBINATION::AreaPosition` (`0xc2cd8`) tests a point against an
area: shape 0 by distance against one value (a circle), others against
bounds (a box).

**Empirical**, over all 540 records (`python SRC/bpb.py info DAT/GAME`):
277 have 4 slots, 253 three and 10 two; the slot types are 2 (835
slots), 1 (474), 3 and 4 (18 each), 0 and 6 (one each), and 5 and 7
never appear. Only records 0–59 fill blocks A and B (A kind 0 or 1, B
kind 0 or 2); in the other 480 both kinds are 3 and the u32s of block C
are 0. The bytes between fields are `0xcd`, `0xbb`, `0xaa` and `0x97`,
the fill patterns of uninitialised memory, so the records are C structs
written with their padding. The areas are mostly circles of radius 100
or 150 at offsets such as (±100, −50) and (0, 150).

`python SRC/bpb.py cbb DAT/GAME/COMBINATION2.CBB 0 3` prints records,
with each slot type's name.

### How a team uses the combinations

**Confirmed** from `GAMEPRG.REL`. Each team has a combination
controller (the team's `+0x1788`) holding 11 `fb::Combination` objects
of `0x15c` bytes at `+0x6c8`. `0xc1180` fills them from the team's
`Pwk::CTeamPlayerSetting`: combination *i* (0–10) is record
`0x14b8e0(set, i)`, the u32 at style record `+0x78` + set × `0x2c` +
*i* × 4, where the set (0–2) is the style record's `+8` and the style
record is one of three of `0x5b4` bytes (`0x14af00`), one per team
style. The setting's constructor (`0x14aaf0`) writes −1 to all 33.

**Which records a team gets.** At match setup `GAME_MODULE`
(`0x2370`) builds each team's three style records from its
`PlTeamData` (`0x14bf68`, once per team style *k*):

- **The set** (`0x14c368`): with *s* the style's Attack Speed (team
  style `+0x5d`, `formset.py` byte 1) and *t* its Attack Type (`+0x5e`,
  byte 2), the largest of *s*, *t* and 6 − *t* picks it: *t* set 1,
  *s* set 2, 6 − *t* set 0 (ties go to *t*, then to 6 − *t*). It is
  stored at style record `+8` (`0x14b3a0`, its only caller), so it is
  fixed for the match.
- **Slots 0–7 of each set** (`0x14c3f0`): 8 of 12 records, drawn by a
  Fisher-Yates shuffle with the game's seeded random numbers (`0x14c2a8`,
  `g_gameSeed`) from a fixed table per set (`GAMEPRG.REL` data):

  | Set | Table | Records |
  |---|---|---|
  | 0 | `0x28c7f0` | 3, 4, 6, 7, 8, 9, 12, 12, 14, 15, 16, 19 |
  | 1 | `0x28c820` | 22, 23, 28, 29, 30, 31, 32, 33, 36, 37, 38, 39 |
  | 2 | `0x28c850` | 40, 41, 46, 47, 49, 52, 53, 54, 55, 56, 58, 59 |

- **Slots 8–10** (the same in all three sets): up to three of the
  club's attack patterns, each pattern *p* (1–30) giving record
  `0x24a5e8`[*p* − 1] = 60 + 16 × (*p* − 1). For a team whose
  `PlGiTask::GetOperator` (SLES `0x211d38`, byte `+0x8a` + side of the
  match task) is 0, three picks at random from the five pattern slots
  at `PlTeamData +0x489f` (the slots training's combination A–E
  practices read, [`TRAINING_FORMAT.md`](TRAINING_FORMAT.md)), skipping
  empty ones. The repeat check (`0x14c718`, `0x14c268`) looks for
  *p* + 60 among the stored records, which are 60 + 16 × (*p* − 1), so
  it only catches pattern 1: a club can get the same pattern twice or
  three times. Otherwise the first three non-zero entries
  found through the five bytes at `+0x498c` (each indexes 3-byte
  entries at `+0x498f`, whose first byte is the pattern); what fills
  those bytes isn't traced.

So the game can only load 65 of the 540 records: the 35 numbers in the
tables (record 12 twice) and 60, 76, …, 524, the first of each
pattern's 16. The other 15 of each 16 run the same script (identical
`.CSB` blocks) with slightly different areas and no distance limits,
and nothing loads them: `0xc2340`, the only caller of the `.CBB` reader,
takes its numbers only from these sets. Records 0–2, 5, 10, 11, 13, 17,
18, 20, 21, 24–27, 34, 35, 42–45, 48, 50, 51 and 57 aren't in any table.

**Which one runs.** No combination belongs to a ball holder. When the
controller is in its select state (`+0x6c4` = 2), `0xc1438` tests all
11 against the current ball holder (`0xc1e70`, the test below, which
returns the number of participants found), sorts the ones that pass by
record number × 10 + participants, highest first (comparator
`0xc31e8`), and goes down the list. A record below 60 is accepted
outright; a pattern record (60 or more) needs a roll (`0xc16a8`): a
random 0–99 (`0x1c5f00`, the seeded generator) below the ball holder's
match parameter for its kind:

| Records | Patterns | Parameter ([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#who-reads-each-parameter)) |
|---|---|---|
| 60–251 | 1–12 (`LS`, `RS`) | 73: attacks down wings |
| 252–347 | 13–18 (`CT`) | 74: attacks through middle |
| 348–443 | 19–24 (`CA`) | 72: counterattack |
| 444–539 | 25–30 (`PO`) | the average of 73 and 74 |

If the roll fails, `0xc6288` is called on `+0x15c8`. The candidate
starts (`0xc1af0`, the script by `0xc7770`, then `0xc1b08`) when
`+0x15e0` is then non-zero; otherwise the next one is tried. So the
club's attack patterns come first, and a basic combination runs when
none of them passes.

`0xc2340` copies a record into its combination object:

| `.CBB` field | Object | Used by |
|---|---|---|
| record number | `+0x4c` | the sort and the roll (`+0x714` from the controller) |
| A kind | `+0x8` | the trigger, below |
| A's two values (kind 1) | `+0x28`, `+0x30` | no reader found (below) |
| B kind, and its value (kind 2) | `+0x20`, `+0x24` (`0xc2b90`/`0xc2b98`) | no reader found |
| C u16 | `+0x1c` | the zone mask, below |
| C's four u32 | `+0xc`–`+0x18` | no reader found |
| C's two limits | `+0x44`, `+0x48` | the distance test, below |
| slots 1 … *n* − 1 | pointers at `+0x34` | the participants, below |

The objects are `fb::CombinationWork` (vtable `0x253118`, `0xc0780`),
and the controller is `fb::Combination` (vtable `0x253100`, constructor
`0xc07d8`). **No reader found** for A's values, block B or C's words:
the parsed record lives in the sequencer object, whose global
(`0x249418`) is used only by its getter, create and destroy
(`0xc7d08`–`0xc7e00`), and `0xc2340` is the only caller of the reader
(`0xc7a78`) and of the getter outside them. The functions that take a
combination object afterwards read only `+0` (active), `+8`, `+0x1c`,
`+0x44`, `+0x48`, `+0x4c` and the slots (`0xc1438`, `0xc1e70`,
`0xc1248`, `0xc1fc8`, `0xc1af0`), and the script gets only the record
number (`0xc7770`). A search of the overlay for the fields at their
offsets inside the controller (`+0x6c8` + field) finds nothing. So they
are probably unused, though a reader through a pointer this search
misses can't be ruled out.

The object's constructor (`0xc06b0`) sets up three area objects of each
class: `fb::COMBINATION::AreaBallHolder` at `+0x50` (`0x14` bytes each),
`AreaPosition` at `+0x8c` (`0x2c` each) and `AreaNodeLine` at `+0x110`
(`0x18` each). A slot's type picks the class (`0xc2450`): type 0 an
`AreaBallHolder` (its first u8 to `+0xc`, its distance to `+0x10`),
types 1–6 an `AreaPosition` with the type at `+4` (a circle `0xc2c00`
or a box `0xc2c58`; type 2's u8 to `+0x10`, type 6's to `+0x14`), and
type 7 an `AreaNodeLine` (`0xc3168`).

**When a combination is tried.** The controller's `0xc0ea0` takes a
mode, which it keeps at `+0x15c4`. The team's ball-holder change
(`0xb93e8`, `match::MatchManager`) calls it with mode 0;
`fb::PhaseInPlay` (`0xf549c`) calls it with mode 3, which stores 3 only
on every 60th call (`+0x1604`). These are the only two stores of
`+0x15c4`. The test before a combination starts (`0xc1e88`) needs:

1. A kind equal to the mode. So kind 0 combinations are tried when a
   team-mate receives the ball, kind 3 ones about once a second in open
   play, and the four kind 1 records (0, 1, 4 and 18) **never start**.
2. Bit *z* of the C u16 set, where *z* is the zone of the ball holder
   (`+0x1600`, from `0xc2778`): 14 when the holder is more than 36.28
   from the centre line along the pitch, else row × 3 + column, with 4
   rows of 18.14 along the pitch (from −36.28 to +36.28, in the attacking
   direction) and 3 columns across it (the left quarter, the middle
   half, the right quarter). So `0x0480`, bits 7 and 10, is the middle
   of the two attacking rows.
3. If the first limit isn't 0: the team's line value (`+0x1608`) less
   the ball holder's y (`+0x15f4`) between the two limits.
4. A participant found for every slot.

**The participants.** Participant 0 is the player at the controller's
`+0x160c` (probably the ball holder).
For slot *k*, `0xc1fc8` tests each outfield player (1–10, the keeper
never) who isn't already a participant against the slot's area
(the area's test, vtable `+0xc`), sorts the ones inside, and makes the
first participant *k*. If any slot finds no one, the combination doesn't
start. `0xc1248` also gives each slot's area position, turned to the
team's attacking direction.

Where an `AreaPosition` sits, by type (`0xc2df0`, jump table
`0x274590`); x and y are the area's offsets:

| Type | Position | Records |
|---|---|---|
| 1 | x, and the team's line value + y | 474 slots |
| 2 | participant *u8*'s player + (x, y), turned to his team's direction | 835 |
| 3 | x − 328.66, line value + y | 18 |
| 4 | x + 328.66, line value + y | 18 |
| 5 | (x, y) as given | none |
| 6 | from `0xc3270` with the u8 and the team's side | 1 (record 1) |

The area's test (`0xc2cd8`) accepts types 1–5 only, and
`AreaBallHolder`'s test returns 0 (`0x2267a8`), so a type 0 or type 6
slot never finds a participant: records 1 (type 6) and 59 (type 0)
never start either. Type 7 appears in no record.

The controller's `+0x15f0` is the ball holder's position, turned to
the attacking direction (`0xc0bc4`), and `+0x1608` is a per-team value
the field information keeps at `+0x10400` + side × 4 (`0x3e4a8`), set
when the players are placed (`0xb7784`, from the last placed player's
y). It is the team's defensive line ([below](#the-defensive-line)).

**Empirical.** The match works in tenths of a metre: the zone bounds,
the 328.66 touchline offset (32.9 m) and the default second limit,
1055.6, which is a pitch length. So the `.CBB`'s ×10 values are
metres. Over the 540 records: A kind 3 in 480, 0 in 56, 1 in 4; the C
masks are mostly `0x400` (122), `0x240` (111), `0x900`, `0x480` and
`0x80`; 452 records have both limits 0 (no distance test) and 38 have
50 and 1055.6.

### The combination commands

A combination's script moves up to three participants (0–2) through
`fb::RoleCombination`. **Confirmed:** each command's first argument is
where its result goes (`m3[0]` when it's dropped); its other arguments
start at the argument record's `+0x10`. A command returns 0 when done,
2 while it is waiting on a participant, and −1 on an error. The
participants' role objects have type `0x2f` (`fb::RoleCombination`).
Areas live in an array of 0x140-byte records (`0xc37f8`); a command that
makes one stores its index in the result, and the area's `+0x130` holds
the player sent there.

`fb::RoleCombination` keeps a pending mode at `+0x2c` (set by
`0x1296e0`) and the running one at `+0x30`; `0x128b98` switches on it
(jump table `0x27b890`):

| Mode | Handler | What it does |
|---|---|---|
| 0 | `0x128ff0` | pass to the player in the target area (`+0x180`) |
| 1 | – | nothing |
| 2 | `0x1292a0` | run to an area (`0x129748`, which takes the offsets at `+0x20`/`+0x24`) |
| 3 | `0x1293a8` | switch to the player's play at `+0x108` |
| 4 | `0x128fd0` | pass to another participant (`+0x184`) |
| 5 | `0x129128` | a kick at the target that `0x1049b8` picks (the set plays' helper; probably the shot) |
| 6 | `0x1291f0` | set the player's target (`+0x180`) |
| 7 | `0x128c80` | clear a flag in the player's `+0x1f0` |

Modes 0 and 4 build the kick with the set plays' pass builder
(`0x56f68`), which writes the kick kind at `+0x1a`. The pass type in
`+0x28` picks it (`0x128f68`): 0 a through pass (kind 1), 1 a short pass
(kind 0), 2 a long pass (kind 3), any other value a short pass. See
[the kick kinds](PBDATA_FORMAT.md#the-kick-kinds).

The 29 commands (argument counts at `0x274790`, including the result):

| Command | Arguments after the result | What it does |
|---|---|---|
| `Combi0` | *p* | participant *p* runs to area 0 (mode 2) |
| `Combi1` | *p*, *a* | *p* runs to area *a* |
| `Combi27` | *p*, *x*, *y* | *p* runs to area 0, with offsets *x*, *y* |
| `Combi28` | *p*, *a*, *x*, *y* | *p* runs to area *a*, with offsets |
| `Combi2` | *t* | makes an area of type *t*, a zone chosen by channel and depth ([below](#combi2s-areas)) |
| `Combi3` | *n* | makes preset area *n* through the table at `0x249370` ([below](#combi3s-preset-areas)); entries 13–15, 17, 18 and 21 are empty, so those *n* do nothing |
| `Combi4` | *p*, *k* | *p* passes to area 0 with pass type *k* (mode 0) |
| `Combi5` | *p*, *a*, *k* | *p* passes to area *a* |
| `Combi6` | *p*, *x*, *k* | *p* passes to a point it builds from *x* |
| `Combi7` | *p*, *q*, *k* | *p* passes straight to participant *q* (mode 4) |
| `Combi9` | *p*, *q* | the same as `Combi7` (`0xc4fd0` calls it) |
| `Combi8` | *p* | mode 7 for *p* |
| `Combi10` | *p* | 0 if *p* is still a combination role, else −1 |
| `Combi11` | *p* | mode 3; waits until *p*'s player holds the ball (`*0x249058 +0xc`) |
| `Combi12` | *p* | mode 6, with a target from `0x36c78`; waits on `0x128da0` |
| `Combi13` | *p* | mode 5, the kick; waits until it's done (`+0x188`) |
| `Combi14` | *x* | stores 1 in the result |
| `Combi15` | *p* | stores 1 if *p*'s player holds the ball, else 0 |
| `Combi16` | *x* | makes participant *x*'s own zone the area (`0xc62a8`, which finds the zone of that participant's player) |
| `Combi17`–`Combi24` | – | each makes an area around participant 0 by `0xc6150` with a fixed direction: 5, 1, 3, 7, 4, 6, 2 and 8 in command order (below) |
| `Combi25` | *c* | stores 1 with a chance of *c* % (`fcEuroRand_Get0to1`, the game's seeded random numbers), else 0 |
| `Combi26` | *p*, *d* | makes an area *d* × 10 from participant *p*, trying sideways offsets of 20, 30 or 50 until `0xc63a8` accepts one |

**The directions of `Combi17`–`Combi24`** (**confirmed**): `0xc6188`
mirrors the value through `0x274870` (0, 5, 6, 7, 8, 1, 2, 3, 4) when
the team's side (`0xa9d58`) is 1, so value *d* and *d* + 4 are opposite
directions. `0xc7108` passes it to `0xa39d8`, which turns it into an
angle (`0xa3900`, jump table `0x26fa90`): 1 90°, 2 135°, 3 180°, 4 225°,
5 270°, 6 315°, 7 360°, 8 45°. It then goes through the zones of the
[zone network](#the-zone-network), takes those that share a player
corner with the participant's zone, and tests each one's direction
against that angle with a π/2 tolerance (`0x3fc90fdc`). So
`Combi17`–`Combi24` mark the neighbouring area of the pitch in one of
eight directions, at 270°, 90°, 180°, 0°, 225°, 315°, 135° and 45°.

**Which way is forward.** The angles are the usual ones, 0° along +x and
90° along +y (**confirmed**): the direction test takes `0x1c5ff0`(−dx,
dy) + 90°, and `0x1c5ff0` is atan2 of its two arguments in that order
(the swap and quadrant fixes at `0x1c603c`–`0x1c60c4`). Side 0 is the
one the code doesn't mirror, and in the side-0 frame a team attacks
toward +y (**empirical**: every corner in `PLAYBOOK.BPB` starts at the
+y end, play 0's ball at (33.6, 52.1), and the set plays mirror a path
only for the other side, `0xa5af8`). So:

| Command | Angle | Direction |
|---|---|---|
| `Combi18` | 90° | forward, toward the opponents' goal |
| `Combi24`, `Combi23` | 45°, 135° | forward and to either side |
| `Combi20`, `Combi19` | 0°, 180° | straight across, to either side |
| `Combi22`, `Combi21` | 315°, 225° | back and to either side |
| `Combi17` | 270° | back, toward the team's own goal |

Which of 0° and 180° is the left as the attacking team sees it isn't
checked.

### `Combi2`'s areas

**Confirmed.** `Combi2` *t* picks one zone of the
[zone network](#the-zone-network) and makes it the area. Types 0–5 go
through `0xc5bc8` and `0xc6bf0` with a pair (*c*, *d*) from `0x2746f8`;
types 6 and 7 through `0xc5f30` and `0xc6a40`. Positions are first
turned to the attacking team's frame (`0xa5b40`, by side), and the
"line" is the opponents' defensive line ([below](#the-defensive-line)).

| *t* | Channel | Depth |
|---|---|---|
| 0 | wing *c* = 0 | in front of the opponents' line |
| 1 | wing *c* = 0 | behind it |
| 2 | wing *c* = 1 | in front |
| 3 | wing *c* = 1 | behind |
| 4 | centre | in front |
| 5 | centre | behind |
| 6 | the half with x ≤ 0 | any |
| 7 | the half with x ≥ 0 | any |

For types 0–5 the channel is the zone's x cut into four columns across
the pitch ((x + 328.66) × 0.00609, clamped to 0–3) and mapped through
`0x274898`: column 0 → 0, columns 1 and 2 → −1 (the centre), column 3 →
1; it must equal *c*. *d* = 0 keeps zones on the attackers' side of the
line, *d* = 1 zones beyond it. A zone must also pass the tests at
`0xc6c9c`–`0xc6d9c` (its byte `+8` is 1, and a check through `0xa23b0`
on the zone's corners), which aren't decoded. The candidates (up to 10)
are sorted by their y, smallest first (`qsort` with `0xc73b8`), and the
first is taken. Types 6 and 7 take every zone of their half and the one
with the smallest y. So each type gives the least advanced gap of its
part of the pitch.

Which of wings 0 and 1, and which half, is the attackers' left isn't
known, as for [the direction commands](#the-combination-commands).
`0x249270` would switch every search to another set of functions
(`0xc6f28`, `0xc71f0`, ...), but it is 0 in play and no code stores to
it.

### `Combi3`'s preset areas

**Confirmed.** Most presets run `Combi2`'s search (`0xc5bc8`) with
their own settings: the channel *c* (as above, or 2 for the whole
width, which skips the column test), the depth *d*, a scoring mode *m*
and a participant *p*. The mode decides which candidate comes first
(`0xc6fc8`, jump table `0x2748b0`; the candidates are sorted lowest
score first, in the attacking team's frame):

| Mode | Score |
|---|---|
| 0 | the zone's y: the least advanced first (what `Combi2` uses) |
| 1 | the zone's x: the one furthest to one side first |
| 2 | −x: the one furthest to the other side first |
| 3, 4 | −1000 for a zone whose centre has a greater x than participant *p* (`0xc7300`), so those come first |
| 5 | −1000 when the zone's backward neighbour (direction 5, `0xc6150`) is missing or past *p* in x, likewise |

| *n* | How the area is made |
|---|---|
| 0, 1 | centre, behind the line, the side of participant 0 with greater x first (modes 4 and 3) |
| 2 | any width, behind the line, past participant 1 first |
| 3 | centre, in front of the line, mode 5 with participant 2 |
| 4, 20 | any width, behind the line, past participant 2 first (modes 4 and 3) |
| 7 | wing *c* = 1, in front of the line, smallest x first |
| 8 | wing *c* = 1, in front of the line, largest x first |
| 9 | participant 1's zone, then its neighbour at 0°, or at 45° if there is none (`0xc67d0`) |
| 10 | the same at 180°, or at 135° |
| 11 | the same at 315° |
| 12 | the same at 225° |
| 5 | starts from participant 2 (`0xc2848`) and a direction search (`0xc6150`); not decoded |
| 6 | an area at participant 1's position (`0xa62c0`, `0xc38f8`); not decoded |
| 16, 19 | participant 2's zone (`0xc62a8`), then `0xc5cf0` with the tables at `0x274728` and `0x274738`; not decoded |

The angles are those of [the direction commands](#the-combination-commands):
90° forward, 0° and 180° across. In the centre channel behind the line,
`0xc5bc8` also moves the area's point back by 0.9 along the attacking
direction (`0xc5c90`, `0x1321b8`).

### The defensive line

The per-side value at the field information's `+0x10400` + side × 4
(`0x3e4a8`; the controller's `+0x1608`, the "line" of the slot tests
[above](#how-a-team-uses-the-combinations)) is that team's defensive
line. **Empirical**, from the mid-match save state: side 0's was −40.89
and its deepest outfield player stood at y −41.2; side 1's was 395.02
and its deepest outfield player at 395.1 (its keeper at 497.2). So it
is the y of the last defender, the offside line.

### The zone network

The areas the combinations make are zones of a mesh the match builds
over the players, not fixed parts of the pitch. It lives at match
`+0x102d0` (match = `*0x249058`): `+0` the number of zone slots, `+8` a
pointer to the slot array (a null slot is unused), and from `+0x20` a
list of extra points, 16 bytes each.

**Confirmed** (`0x130e38`, `0x1311e8`, the corner lookup `0xa3230`): a
zone is a 0x120-byte record:

| Offset | Type | What |
|---|---|---|
| `+0x00` | s8 | the zone's id |
| `+0x01` | s8 | number of corners |
| `+0x03` | s8 | number of triangles |
| `+0x14` | f32 | area, summed over its triangles (`0x130e38`) |
| `+0x30` | 4 × f32 | centre, the mean of its corners, recomputed when `+0x10` is clear (`0x1311e8`) |
| `+0x50` | s8 list | the corners, as vertex ids |
| `+0x5c` | 4 bytes each | the triangles: three vertex ids and a pad |

A vertex id *v* is a player or a fixed point (`0xa3230`). With *A* and
*B* the two teams' player counts (`*0x2490fc +0x8e8c`, ordered by
`+0x10c`), *v* < *A* is player *v* of the first team, *v* < *A* + *B*
player *v* − *A* of the second (position at match + team × 0x3c80 +
player × 0x580 + 0x40), and any higher *v* the network's extra point
*v* − *A* − *B*.

**Empirical**, read from a mid-match save state (England v England):
positions are in tenths of a metre, the first team's keeper stood near
its own goal at y −390 and the other's at +497 (so the unmirrored team
attacks toward +y, as [above](#the-combination-commands)), and the 8 extra
points were the pitch's corners and touchline points at x ±328.66,
y ±527.81. 15 of the 28 slots were in use, with 3 to 6 corners each; their
corners were all 11 players of one team, one of the other, and extra
points. So a zone is a gap between the players, mostly the opponents,
and the zones move as the players do. The centres in that state didn't
match their corners, so the network is rebuilt and its centres
recomputed during play; when isn't traced.

So script 0, `Combi3 8; Combi0 1; Combi3 13; Combi0 2; Combi12 0`, makes
preset area 8, sends participants 1 and 2 to area 0 (`Combi3 13` returns
−1 without doing anything), and sets participant 0's target. Whether
area 0 is the area just made (`0xc3878` stores it) wasn't checked. The
participants are the ones the record's slots found
([above](#how-a-team-uses-the-combinations)).

## Still unknown

- The header's `+0x10`, `+0x14` and `+0x1c`, the flags, and the
  starting-positions block's `+0x02` bytes.
- What the move order kinds 1, 2, 4 and 8 mean (most likely speeds or
  ways of running: no names were found), why `COMBINATION.BPB` uses
  code 3, which orders nothing, and whether anything reads the ball's
  point codes. What reads a path kind's value (`+0xe8`), and whose
  position a flagged path is drawn from.
- Whether the corner records' ten groups meant anything to the
  developers beyond loose themes, and what records 196–255 (kind 3,
  roles 249–253) were for.
- `TACTICS_PLAYBOOK_EDIT.TBB` (180 rows of 4 bytes, read through
  `CTacticsLoader::getPlayBookEditTable`).
- Whether anything reads A's two values, block B and C's four u32
  through a pointer the search missed (no reader found).
- What fills `PlTeamData +0x498c`/`+0x498f` (the attack patterns of a
  team whose `GetOperator` is set), what `GetOperator` stands for, and
  what `+0x15e0` and `0xc6288` do when a candidate is tried.
- Slot type 6's position (`0xc3270`).
- What builds the [zone network](#the-zone-network) and when, which
  players it takes (one team's 11 and one of the other's in the state
  read), what a zone's byte `+8` and the `0xa23b0` test in `Combi2`'s
  search mean, and `Combi3`'s presets 5, 6, 16 and 19.
- Which side (left or right)
  `Combi19` and `Combi20` mark, what `Combi12`'s target and
  mode 7's flag are, and the plays at the player's `+0xfc`, `+0x100`
  and `+0x108` that modes 2 and 3 switch to.

## Checking

```bash
python SRC/bpb.py info DAT/GAME
python SRC/bpb.py dump DAT/GAME/PLAYBOOK.BPB 0
python SRC/sles_disasm.py ISO/SLES_541.51 dis GetPLAYBOOK__Q33Pwk12PlayBookData makeBookTop SplitID
```
