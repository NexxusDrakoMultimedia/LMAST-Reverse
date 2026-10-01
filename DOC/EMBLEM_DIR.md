<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/EMBLEM`: the club editor's crest and flag parts

`DAT/EMBLEM` (13 files, 5.2 MB, plus `CVS/`) is folder id **8** in the
game's file manager ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). It holds what
the club editor builds the player's crest and flag from: the part
textures, the tables of presets and samples, and the editor's colour
palette. The finished crests of the real clubs are in
`0SYSTEM/EMBLEM_TEXTURE.PAC` instead ([`0SYSTEM_DIR.md`](0SYSTEM_DIR.md)).
The folder also holds the player editor's tables (`EDIT_PLAYER.TBB`) and
an empty `DUMMY.DAT`.

`python SRC/emblem.py info DAT/EMBLEM` checks the layouts described here.
`python SRC/emblem.py colors DAT/EMBLEM` lists the palette.

| File | Kind | Read by | Contents |
|---|---|---|---|
| `COLOR_TABLE.TBB` | TBB, 7 tables | `EDIT::CColor` | 96 colours and the maps to a 32- and a 16-colour palette. **confirmed** |
| `EDIT_EMBLEM.TBB` | TBB, 144 tables | `EDIT::CEmblemData` | masks, patterns, accessories, presets, sample crests and their layers. **confirmed** (most fields not named) |
| `EDIT_EMBLEM_M.PAC` / `.HED` | BINPAC, 214 SVR | the crest editor | masks (the crest's outline), in 50 groups. **confirmed** |
| `EDIT_EMBLEM_P.PAC` / `.HED` | BINPAC, 22 SVR | the same | patterns (the fill). **confirmed** |
| `EDIT_EMBLEM_A.PAC` / `.HED` | BINPAC, 217 SVR | the same | accessories (the emblems on top). **confirmed** |
| `EDIT_FLAG.TBB` | TBB, 3 tables | `EDIT::CFlagData` | flag bases, flag patterns, crest placements. **confirmed** |
| `EDIT_FLAG.PAC` / `.HED` | BINPAC, 49 SVR | the flag editor | flag bases. **confirmed** |
| `EDIT_PLAYER.TBB` | TBB, 32 tables | `PLAYEREDIT_MODULE` (`YRSTPRG.REL`) | the player editor's tables. Not decoded |
| `DUMMY.DAT` | 0 bytes | nothing | a placeholder |

The 4 part packs hold 128×128 textures at 4 bits per pixel with an
external palette (data format `0x62`, [`SVR_FORMAT.md`](SVR_FORMAT.md)):
the colours come from the palette the player picks, not from the file.
Each `.HED` is a byte-for-byte copy of its pack's header (**empirical**).

`COLOR_TABLE.TBB` has copies in `PRELOAD/GAMEFILE0`–`6` (the match). No
other file here is in a `PRELOAD` pack. `TEST3D/EDIT.PAC` holds older
`.svm` versions of the same 502 part textures
([`TEST3D_DIR.md`](TEST3D_DIR.md)).

## Confirmed from the game code

Addresses are in `DLL/SIMPRG.REL` unless marked. Function bounds in this
overlay come from the exported symbols, so code between two exports is
given by address.

| Address | Symbol | What it shows |
|---|---|---|
| `0x107174`–`0x107230` | (crest editor, after `CEmblemEditor::GetPresetLayerAccessaryColor`) | loads `edit_emblem_m.hed`, `_a.hed` and `_p.hed` with `CLoader::loadFileRequest`, folder 8 |
| `0x10738c`–`0x107418`, `0x107bc8`, `0x107cc0`, `0x107db8` | the same | load single entries of `edit_emblem_m/a/p.pac` (masks, accessories, patterns) |
| `0x107b08` | the same | loads `edit_emblem.tbb` |
| `0x108b54`–`0x108ed0` | (flag editor, after `CFlagEditor::GetPresetData`) | loads `edit_flag.hed`, entries of `edit_flag.pac`, and `edit_flag.tbb` |
| `0x109330` | `EDIT::CEditLoader::GetEditColor` | loads `color_table.tbb` |
| `0x1039f0`–`0x104310` | `EDIT::CEmblemData` getters | read `EDIT_EMBLEM.TBB` by table number (below) |
| `0x104578`–`0x1045e8` | `EDIT::CFlagData` getters | read `EDIT_FLAG.TBB` tables 0, 1, 2 |
| `SLES 0x2b99f8`–`0x2b9bf4` | `EDIT::CColor::GetColorFromId96`, `GetId16FromId32`, ... | read `COLOR_TABLE.TBB` tables 0–6 (below) |
| `SLES 0x2b9bf8` | `EDIT::CColor::GetColor16` | turns a colour word into a PS2 16-bit colour: red from bits 24–31, green 16–23, blue 8–15, and bit 15 set when bits 0–7 aren't 0 |
| `CEDITPRG.REL 0x13dc`–`0x1414` | (`SELECTTEAMCOLOR_MODULE`) | names `color_table.tbb`, `edit_emblem.tbb` and `edit_flag.tbb` |
| `SIMPRG.REL 0x223ab0`, `0x225638`, `0x225928` | load lists | `color_table.tbb` (folder 8) with message categories 1080/1085, 550 and 551 |
| `SIMPRG.REL 0x40208`, `0x10fb20` | (uniform editor, `COPerson::makeInitParam`) | more `color_table.tbb` loads |
| `GAMEPRG.REL 0x56d4` | (`GAME_MODULE`) | `color_table.tbb` for the match |
| `YRSTPRG.REL 0x31430`, `0x331d0` | load lists of `PLAYEREDIT_MODULE` | `edit_player.tbb` (folder 8) with message category 2000 |
| `TESTPRG.REL 0x2d110` | the Uniform Viewer's load list | `edit_emblem.tbb` and `color_table.tbb` |
| `TESTPRG.REL 0xb428` | `SUGIO_TEST::CEditTextureTestTask` | `color_table.tbb` and `edit_emblem_p.hed`/`.pac` |

## `COLOR_TABLE.TBB`

Seven `TBL1` tables. Table 0 is the palette; the others map an id in one
palette to the nearest id in another (**confirmed**, `EDIT::CColor`, each
getter clamps the id to the table's size):

| Table | Rows × bytes | Getter | Maps |
|---|---|---|---|
| 0 | 96 × 4 | `GetColorFromId96` | id96 → colour word (u32) |
| 1 | 32 × 1 | `GetId16FromId32` | id32 → id16 |
| 2 | 96 × 1 | `GetId16FromId96` | id96 → id16 |
| 3 | 16 × 1 | `GetId32FromId16` | id16 → id32 |
| 4 | 96 × 1 | `GetId32FromId96` | id96 → id32 |
| 5 | 16 × 1 | `GetId96FromId16` | id16 → id96 |
| 6 | 32 × 1 | `GetId96FromId32` | id32 → id96 |

`GetColorFromId32` and `GetColorFromId16` go through table 6 or 5 to table
0. A colour word holds red in its top byte, so in the file the bytes run
alpha, blue, green, red. All 96 alphas are `ff`.

The 96 colours form 12 rows of 8 (**empirical**): seven shades of one hue
from light to dark, then a grey (row 0 is `#ffbfbf` ... `#3f0000`, then
white). The 32 and 16 palettes are subsets: table 6 and table 5 list
which of the 96 they are, and going up and back (32 → 96 → 32, 16 → 96 →
16, 16 → 32 → 16) returns the same id for every colour (**empirical**,
checked by `emblem.py info`).

This is a different table from `0SYSTEM/COLORDATATABLE.TBB`, the 77 UI
colours, which stores R, G, B, A in byte order.

## `EDIT_EMBLEM.TBB`

144 `TBL1` tables. The record size comes from each getter's multiplier
(**confirmed**, `EDIT::CEmblemData`):

| Table | Records | Getter | Contents |
|---|---|---|---|
| 0 | 214 × 12 | `0x103e78`, `GetMaskData` | masks. Each starts with its own index as a u16 |
| 1 | 50 × 4 | `0x103e48`, `GetMaskData` | mask groups: {u16 first mask, u16 count}. `GetMaskData(group, n)` returns mask `first + n`, or `first` when `n` is past the count |
| 2 | 22 × 4 | `0x103f20` | patterns: u32 0–21, the entry in `EDIT_EMBLEM_P` |
| 3 | 217 × 4 | `GetAccessaryData` | accessories: u32 0–216, the entry in `EDIT_EMBLEM_A` |
| 4 | 50 × 10 | `GetPresetBaseData` | preset bases |
| 5 | 44 × 10 | `0x103fb8` | presets (unnamed) |
| 6 | 1 × 10 | `0x103ff0` | one more preset record |
| 7 | 29 × 110 | `GetSampleData` | sample crests. Each starts with a u16 id (0–31; 8, 21 and 24 are absent) |
| 8 | 32 × 110 | `GetInitializeData` | the crests a new club can start with |
| 9 | 32 × 110 | `GetRivalData` | rival clubs' crests |
| 10 | 32 × 1 | `GetSampleIndexFromInitializeIndex` | the sample for each starting crest (values 0–28) |
| 11 | 32 × 3 | `GetFirstColorIdSet` | three signed bytes per starting crest. In the data: the row's own index, then two ids in the 32-colour palette |
| 12–143 | 12 bytes each | `GetSampleLayerAcceData` | layer accessories, table 12 + 4 × sample + layer (below) |

**The mask groups are the mask pack** (**empirical**, all 214): group *g*
holds `_mask_GGG_NN` for *GGG* = *g* + 1, in order, so table 1's counts
are the number of masks in each group, and the groups follow each other
without gaps. Table 0 has one row per mask, table 2 one per pattern and
table 3 one per accessory, matching the three packs.

The 10-byte records of tables 4–6 look like {u16 part, ...,
u8 100, u8 100, u8 0}: the two 100s are probably a scale in percent
(**empirical**, not checked in the game). The 110-byte crests of tables
7–9 aren't decoded. Their layout is presumably `Param::PlEmblem`, whose
part names (`PlEmblemBase`, `Mask`, `Area`, `Pattern`, `Acce`, `Trs`) are
in the executable's string table (`SLES 0x53b2a0`–`0x53b350`). A club's
crest is read and written with `pwkTeam_GetEmblemSet`/`SetEmblemSet`.

### The layer tables (12–143)

`GetSampleLayerAcceData(out, max, sample, layer, key)` (`0x104180`) reads
table 12 + 4 × *sample* + *layer*, so the 132 tables are 33 samples × 4
layers. It walks `GetDataTableCount` records of 12 bytes, and for each
whose u16 at `+0` equals *key* it copies the u16 at `+2` and the 8 bytes at
`+4` into a 10-byte output record. `0x104268` counts the records whose
`+0` matches. 838 records in all (**empirical**).

**Tables 93, 101 and 105 are a byte short.** These are the three tables
[`TBB_FORMAT.md`](TBB_FORMAT.md#edit_emblemtbb-t93-t101-and-t105-empirical)
describes: 143 bytes, where record 4 lacks its `04 00` key. The reader
above settles what the game does with them (**confirmed**): it reads 11
records of 12 bytes, so record 4 comes out with key 141 (or 160 in
table 93) instead of 4, records 5–10 are read one byte late with keys
like `0x9500`, and record 11 is never reached. A lookup for keys 4–11 in
sample 20, 22 or 23, layer 1, therefore finds nothing. Whether that shows
in the crest editor hasn't been checked.

## `EDIT_FLAG.TBB`

| Table | Records | Getter | Contents |
|---|---|---|---|
| 0 | 49 × 4 | `0x104578` | flag bases: u32 0–48, the entry in `EDIT_FLAG.PAC` |
| 1 | 71 × 2 | `GetPresetFlagPatternData` | flag patterns: low byte a base (0–48), high byte a variant (0–3) |
| 2 | 27 × 4 | `GetPresetEmblemTs` | where the crest sits on the flag (`Param::PlFlagEmblemTs`) |

Table 2's records are {s8 x, s8 y, u8, u8} (**empirical**): 9 positions
(x −34, 0, 34 and so on) at three sizes, `0x36`/`0x44`, `0x27`/`0x32` and
`0x1e`/`0x26`. That is three sizes × a 3 × 3 grid. The meaning of each
byte hasn't been checked in the game.

## `EDIT_PLAYER.TBB`

32 tables, loaded by the two lists of `PLAYEREDIT_MODULE` in
`YRSTPRG.REL` together with message category 2000. That module is
sequencer module 63 (PlayerEdit), started from events
([`SNR2_FORMAT.md`](SNR2_FORMAT.md)), and module 115 in the developer
launcher, where it hangs ([`SQB_FORMAT.md`](SQB_FORMAT.md)). It is
probably the Japanese version's player editor.

The tables aren't decoded. Their shapes (**empirical**): tables 0–8 are
14 rows of 33 bytes (values like 30–80, a rating per ability and
position?), table 14 is 146 rows of 26 rising values (growth curves?),
table 19 is 319 rows of 144 bytes, table 26 is 100 rows of 151 bytes, and
the rest are small lists of 1–16-byte rows. Nothing here has been checked
in the game.

## Still unknown

- The fields of the presets (tables 4–6), the 110-byte crests (7–9) and
  the layer records.
- Which sample crest each layer table's key selects, and whether the three
  short tables lose visible parts in the editor.
- `EDIT_FLAG` table 2's byte meanings, and table 1's variants.
- All of `EDIT_PLAYER.TBB`.
- Why the 4bpp part textures' palette indices map to the chosen colours
  (the palette build wasn't traced).
