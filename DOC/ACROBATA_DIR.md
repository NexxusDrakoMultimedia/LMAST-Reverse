<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/ACROBATA`: the 3D event scenes

`DAT/ACROBATA` is folder id **13** in the game's file manager
([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). It holds one 115 MB pack,
`ACROBATAPACKFILE.PAC`, and a 9-byte `DUMMY.DAT` (the text `hogehoge.`,
a Japanese placeholder word). The pack has the 875 scenes of what the
code calls **Acrobata**: the 3D scenes of the season mode. They cover the
backgrounds of the club rooms, people walking and talking in them,
event scenes, the month-start and year-start scenes, the newspaper
intro, training scenes, the endings and the game-over scenes. The scenes
are in the format of a middleware the code calls Acroarts.

`python SRC/acrobata.py info DAT/ACROBATA` checks every entry and its
resources. `python SRC/acrobata.py scenes DAT/ACROBATA ISO` checks the
executable's tables against the pack and lists every scene id.

The pack isn't in any `PRELOAD` pack. It isn't listed in the folder's
`CVS/ENTRIES` either, so the build made it ([`CVS_DIR.md`](CVS_DIR.md)).

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `SLES 0x2fbb38`–`0x2fbb60` | (`LOADER` code, after `CAckUsrMemory::reserve`) | opens `AcrobataPackFile.pac` (`0x55d748`) from folder `0xd` with `CFcEuro_FileResource`, for a byte range: offset and size come from the executable, not the pack |
| `SLES 0x3a3b08` | `LOADER::AcrobataPackFile_tbl` | the executable's copy of the pack index: per entry {u32 offset, u32 size, u32 ABDA size, u32 ABRS size}, the same four values as the pack's header row |
| `SLES 0x2faff8` | (`LOADER` helper) | turns a scene id into an entry index through the table at `0x55d7a8`: 20 bytes per id, {u32 flag, s16 entry[7]}. With the flag set, the entry is `entry[language]` (`Localize_GetLanguage`), otherwise `entry[0]` |
| `SLES 0x2fb050`, `0x2fb080`, `0x2fb0b8` | (`LOADER` helpers) | read the offset, the size and the ABDA size of a scene's entry from `0x3a3b08` |
| `SIMPRG.REL 0x116320` | `ACROBATA::getAckName(int)` | names scene ids 1–719: from the table at `0x1d7368`, or for language-dependent scenes from `0x22fd58` (an index) and `0x1d7ea8` (7 names per index, by language) |
| `SIMPRG.REL 0x1a69b0` | (Acroarts loader) | checks an `ABDA` chunk: the magic, the flag at `+0x0c` (bit `0x100` = already relocated), the version word at `+0x10`, which must be `0x77831b45`, and the `POF0` chunk at `+0x18`; then relocates the pointers (`0x1aaff8`) and sets the flag |
| `SIMPRG.REL 0x183208` | (Acroarts loader) | the same checks for an `ABRS` chunk, without the version |
| `SIMPRG.REL 0x247848`–`0x2478b0` | (strings) | the errors name the format: "ABDA(Acroarts Native Data) Version is incorrect", and print the expected and found versions as "Ver%8d R%d" |
| `SIMPRG.REL 0x1f408` | `PLAY_ACROBATA_MODULE` | sequencer module 36, PlayAcrobata, which the root scripts start with scene numbers ([`SQB_FORMAT.md`](SQB_FORMAT.md)) |
| `TESTPRG.REL 0xf320` | `ACROBATA_VIEWER_MODULE` | launcher module 107, ACROBATA VIEWER, which shows the newspaper intro ([`SQB_FORMAT.md`](SQB_FORMAT.md)) |

The version word `0x77831b45` is 2005080901, printed as "Ver 20050809 R1":
a date stamp, 9 August 2005, revision 1. The code compares it with its own
library version, the same value. All 875 scenes carry it.

**The game doesn't read the pack's header.** It takes every offset and
size from the copy in the executable. No code reading the header was
found. The copy matches the header for all 875 entries (**empirical**,
`acrobata.py scenes`). A rebuilt pack whose entries move or change size
therefore needs the table at `SLES 0x3a3b08` patched, as `MES.PAC` needs
its executable offset table ([`REBUILD.md`](REBUILD.md)).

## The entries

All 875 entries have the same two-part layout (**empirical**, every
entry):

| Part | Starts at | Size | Contents |
|---|---|---|---|
| `ABDA` | 0 | header column 3 | the scene: a `0x30`-byte chunk header, an `ABDT` chunk, `POF0`, `EOFC` |
| `ABRS` | column 3 | header column 4 | the resources: a chunk header, the wrapped resources, `POF0`, `EOFC` |

The pack's two extra columns are these two sizes, and they add up to the
entry's size.

The chunk header of both parts:

| Offset | Type | Field |
|---|---|---|
| `+0x00` | char[4] | `ABDA` or `ABRS` |
| `+0x04` | u32 | the bytes between the header and `EOFC`: the part is header size + this + `0x10` |
| `+0x08` | u32 | header size: `0x30` for every `ABDA`; `0x30`–`0xe0` for `ABRS` |
| `+0x0c` | u16 | flags; the loader sets `0x100` once the pointers are relocated |
| `+0x10` | u32 | version, `0x77831b45` |
| `+0x14` | u32 | 1 in every `ABDA`; 35 different values in `ABRS`, meaning unknown (it isn't the resource count) |
| `+0x18` | u32 | offset of the part's `POF0` chunk from the part's start |

`POF0` and `EOFC` chunks have a 16-byte header {magic, u32 size, u32
header size, u32 0}. The part ends right after `EOFC`.

### `POF0`: the pointer list

`POF0` lists the words in the part that hold pointers, which the loader
turns from offsets into addresses. After its 16-byte header comes a u32,
then Sega's usual packed list: each byte's top two bits give the size of
a step (1: 6 bits, 2: 14 bits, 3: 30 bits, in the low bits of 1, 2 or 4
bytes), counted in words, and a 0 byte ends it. Both the locations and
the values stored there are offsets from the part's start. All 455,329
pointers in the pack decode to locations and targets inside the part's
data, before `POF0` (**empirical**; the encoding matches other Sega
games, and the loader's call is confirmed, but the decoder at `0x1aaee8`
wasn't read line by line).

### `ABRS`: the resources

After the `ABRS` header, the resources follow one after another up to
`POF0`. Each is wrapped in a 16-byte header {u32 type, u32 size, u32
`0x10`, u32 `0x80`}, with the type being the payload's own magic
(**empirical**, all 4,841):

| Type | Count | Payload |
|---|---|---|
| `NSIF` | 2,795 | a Ninja file ([`NINJA_FORMAT.md`](NINJA_FORMAT.md)): 1,805 motions, 560 cameras with a camera motion, 394 textured models, 36 untextured models |
| `GBIX` | 1,962 | an `.svr` texture ([`SVR_FORMAT.md`](SVR_FORMAT.md)) |
| `PVMH` | 84 | an `.svm` texture archive |

All of them parse with `ninja.py` and `svr.py` without problems. The
`ABRS` header from `+0x20` to its end holds a small table that grows with
the header; what it lists wasn't worked out.

### `ABDT`

The scene itself, inside `ABDA` right after its header, with the
pointers `POF0` lists. Its layout isn't decoded. The classes that play a
scene are `ACROBATA::CAckManager`, `CAckDiamante` and `CAckLight`
(`SIMPRG.REL 0x115268`–`0x118060`).

## Scene ids

The game asks for scenes by id, 1–719 (**confirmed**, the two tables
above). 693 ids have one entry, and 26 have one entry per language in the
order Japanese, English, French, German, Italian, Spanish, Dutch: 26 × 7 =
182 entries. 693 + 182 = 875, so every entry belongs to exactly one id and
language, and the executable's table agrees with `getAckName` for every id
(**empirical**, `acrobata.py scenes`). The language-dependent scenes are
the endings (one per league won, plus a European one), the game-over
scenes, the `FC_EURO_LOGO`, the intro and option backgrounds, an
important mail, the month-start events and `EV_PICT_GOOD_LISTING`.

The names group the scenes (**empirical**, entry counts):

| Prefix | Entries | What, by name |
|---|---|---|
| `EV_TYPE_` | 173 | event scenes: people telling news, players leaving, press conferences, endings, game over |
| `GM_` | 124 | month-start and year-start scenes, intros (`GM_BG_INTORO`), options background |
| `CH_`, `OF_` | 97, 45 | `CH_#_M#_W#_#` and `OF_#_M#_W#_#`: probably groups of men and women in the clubhouse and the office |
| `NE_` | 90 | the newspaper's scenes (`NE_FILD`, `NE_PRESS`, `NE_PRACTICEPLACE`) |
| `EV_PICT_` | 80 | event pictures: sponsors, leagues, cups |
| `BG_` | 194 | backgrounds: clubhouse (`CH`), office (`OF`), the player's room by level (`MY_LV`), owner room (`OR`), and others, with light variants |
| `PRAC_` | 30 | training scenes, five each of `CON`, `DEF`, `OFF`, `PHY`, `SYS`, `TAC` |
| `M_`, `MW_`, `W_`, `M#_` | 30 | people walking across backgrounds |
| `FC_EURO_` | 8 | the logo (one per language) and `FC_EURO_TITLE` |
| `MY_`, `test_` | 4 | leftovers: `MY_ROOM_LV01_TEST`, `MY_test_01a`/`b`, `test_abe` |

The three largest entries are `BG_MY_LV01_02_test0`–`test2` (4.3–4.4 MB
each), test versions of a room background.

## Still unknown

- The `ABDT` scene layout, and so what a scene does.
- `+0x14` of the chunk header, and the table in larger `ABRS` headers.
- Which code asks for which scene id, beyond the root scripts' few
  `PlayAcrobata` calls.
