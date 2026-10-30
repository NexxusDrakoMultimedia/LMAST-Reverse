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
`python SRC/emblem.py colors DAT/EMBLEM` lists the palette, and
`python SRC/emblem.py crests DAT/EMBLEM` the crests.

| File | Kind | Read by | Contents |
|---|---|---|---|
| `COLOR_TABLE.TBB` | TBB, 7 tables | `EDIT::CColor` | 96 colours and the maps to a 32- and a 16-colour palette. **confirmed** |
| `EDIT_EMBLEM.TBB` | TBB, 144 tables | `EDIT::CEmblemData` | masks, patterns, accessories, presets, sample crests and their layers. **confirmed** |
| `EDIT_EMBLEM_M.PAC` / `.HED` | BINPAC, 214 SVR | the crest editor | masks (the crest's outline), in 50 groups. **confirmed** |
| `EDIT_EMBLEM_P.PAC` / `.HED` | BINPAC, 22 SVR | the same | patterns (the fill). **confirmed** |
| `EDIT_EMBLEM_A.PAC` / `.HED` | BINPAC, 217 SVR | the same | accessories (the emblems on top). **confirmed** |
| `EDIT_FLAG.TBB` | TBB, 3 tables | `EDIT::CFlagData` | flag bases, flag patterns, crest placements. **confirmed** |
| `EDIT_FLAG.PAC` / `.HED` | BINPAC, 49 SVR | the flag editor | flag bases. **confirmed** |
| `EDIT_PLAYER.TBB` | TBB, 32 tables | `PLAYEREDIT_MODULE` (`YRSTPRG.REL`) | the player editor's tables: base abilities by position and nation, personality and growth ranges, the editor's choices ([below](#edit_playertbb)) |
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
colours, which stores R, G, B, A in byte order. Its near twin is
`PARAM/PLRESOURCESIM.PAC` entry 9, which the same `EDIT::CColor` wraps for
the season-mode screens ([`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md#entry-9-the-edit-screens-colour-palette)):
the same size and the same 96 colours, but 10 bytes of the maps differ
(8 in table 1, one each in tables 3 and 5; **empirical**). Which screens
use which copy is listed in each doc; a palette edit has to reach both.

## `EDIT_EMBLEM.TBB`

144 `TBL1` tables. The record size comes from each getter's multiplier
(**confirmed**, `EDIT::CEmblemData`):

| Table | Records | Getter | Contents |
|---|---|---|---|
| 0 | 214 × 12 | `0x103e78`, `GetMaskData` | masks. Each starts with its own index as a u16 |
| 1 | 50 × 4 | `0x103e48`, `GetMaskData` | mask groups: {u16 first mask, u16 count}. `GetMaskData(group, n)` returns mask `first + n`, or `first` when `n` is past the count |
| 2 | 22 × 4 | `0x103f20` | patterns: u32 0–21, the entry in `EDIT_EMBLEM_P` |
| 3 | 217 × 4 | `GetAccessaryData` | accessories: u32 0–216, the entry in `EDIT_EMBLEM_A` |
| 4 | 50 × 10 | `GetPresetBaseData` | base presets {u16 mask group, `Trs`} (below) |
| 5 | 44 × 10 | `0x103fb8` | area pattern presets {u16 pattern, `Trs`} |
| 6 | 1 × 10 | `0x103ff0` | area accessory presets {u16 accessory, `Trs`}; the one row is all 0 |
| 7 | 29 × 110 | `GetSampleData` | sample crests (`Param::PlEmblemPreset`, below). Ids 0–31; 8, 21 and 24 are absent. They are Edit Emblem's Sample list: 29 crests over three pages of 10, 10 and 9 (user report, 2026-10-31) |
| 8 | 32 × 110 | `GetInitializeData` | the crests a new club can start with |
| 9 | 32 × 110 | `GetRivalData` | rival clubs' crests: 32 copies of one crest |
| 10 | 32 × 1 | `GetSampleIndexFromInitializeIndex` | the sample row of each starting crest (values 0–28) |
| 11 | 32 × 3 | `GetFirstColorIdSet` | three signed bytes per starting crest. In the data: the row's own index, then two ids in the 32-colour palette |
| 12–143 | 12 bytes each | `GetSampleLayerAcceData` | layer accessories {u16 key, u16 accessory, `Trs`}, table 12 + 4 × sample + layer (below) |

**The mask groups are the mask pack** (**empirical**, all 214): group *g*
holds `_mask_GGG_NN` for *GGG* = *g* + 1, in order, so table 1's counts
are the number of masks in each group, and the groups follow each other
without gaps. Table 0 has one row per mask, table 2 one per pattern and
table 3 one per accessory, matching the three packs.

### The crest structures

**Confirmed.** The developers' field table
([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#the-developers-field-names);
here `SLES 0x53cd08`–`0x53d3c8`) names every member of the crest. Its
parser in `sles_disasm.py fields` skips members that are themselves
structures but whose names don't start with `_`, so these were read from
the raw rows:

| Structure | Size | Members |
|---|---|---|
| `Trs` | 8 | `tx` s8 +0, `ty` s8 +1, `rot` s16 +2, `rev` u8 +4, `sx` u8 +5, `sy` u8 +6, a pad byte |
| `Acce` | `0x12` | `trs` +0, `texture_id` +8, `texture_num` +0xa, `aColor` 3 × u16 +0xc |
| `Pattern` | `0x10` | `trs` +0, `texture_id` +8, `texture_num` +0xa, `aColor` 2 × u16 +0xc |
| `Area` | `0x22` | an `Acce` +0, a `Pattern` +0x12 |
| `Mask` | `0xac` | `mask_num` u16 +0, `aArea` 5 × `Area` +2 |
| `Base` | `0xb6` | `trs` +0, `base_num` u16 +8, `mask` +0xa |
| `PlEmblem` | `0x168` | `chunk` u32 +0, `base` +4, `aAcce` 9 × `Acce` +0xba, `aLayer` 10 × u8 +0x15c |
| `PlEmblemPresetNumber` | `0x22` | `sample`, `base`, `mask` +0–+4, `aAreaPattern` 5 × +6, `aAreaAcce` 5 × +0x10, `aLayerAcce` 4 × +0x1a (all u16) |
| `PlEmblemPresetColor` | `0x4a` | `aAreaPattern` 5 × 2 +0, `aAreaAcce` 5 × 3 +0x14, `aLayerAcce` 4 × 3 +0x32 (all u16) |
| `PlEmblemPreset` | `0x6e` | `preset` u16 +0, `number` +2, `color` +0x24 |

The next structure holds a club's crest: `emblem` (`PlEmblem`) +0,
`emblempreset` +0x168 and `main_color_id` +0x1d6. A club's crest is
read and written with `pwkTeam_GetEmblemSet`/`SetEmblemSet`.

**The 110-byte crests of tables 7–9 are `PlEmblemPreset`s (confirmed,
`EDIT::CEmblemData::Initialize`, `0x103a50`).** It builds a `PlEmblem`
from one, and the club's three colours:

| Preset offset | Field | What `Initialize` does |
|---|---|---|
| `+0x00` | `preset` | the crest's id; not read |
| `+0x02` | `sample` | the sample whose layer tables the layer keys search (0–32) |
| `+0x04` | `base` | a row of table 4: its part goes to `base_num`, its `Trs` to the base's |
| `+0x06` | `mask` | copied to `mask_num` |
| `+0x08` | `aAreaPattern` ×5 | rows of table 5: each area's pattern texture and `Trs` |
| `+0x12` | `aAreaAcce` ×5 | rows of table 6: each area's accessory texture and `Trs` |
| `+0x1c` | `aLayerAcce` ×4 | the key searched for in each layer table (below) |
| `+0x24` | colours, 5 × 2 | each area's pattern colours |
| `+0x38` | colours, 5 × 3 | each area's accessory colours |
| `+0x56` | colours, 4 × 3 | the colours of each layer's accessories |

A colour is a 32-colour id, turned into a 96-colour id
(`GetId96FromId32`), or −1, −2 or −3 for the club's first, second or
third colour (`0x103b78`). The layer part (`0x103cb8`–`0x103e10`) asks
`GetSampleLayerAcceData` for each layer's records with that key and
appends each as an accessory at `PlEmblem +0xba` + `0x12` × *n*, at most
9 in all.

The 10-byte records of tables 4–6 are a part number and a `Trs`; `sx`
and `sy` are a scale in percent (100 = full size) and `rot` an angle
(table 5 uses 0, 45, 90 and 295). Table 6 has one row, all 0, and every
crest names it for every area (**empirical**), so the area accessories
start empty and a crest's accessories come from its layers.

**Empirical**, over the 93 crests (`python SRC/emblem.py info`):

- `sample` and `base` are always equal.
- `mask` is an index inside the mask group named by the base preset's
  part (table 1): all 90 crests with a base fit, and the 3 whose base
  preset has part 65535 (4 of the 50 base presets: no base) have mask 0.
- Each starting crest (table 8) has exactly the parts of the sample row
  table 10 names; only the colours differ.
- Area accessory colours are all 31. Layer keys are 0 or 1.
- A layer record with accessory 65535 fills a slot with nothing. The
  crests get 72 (samples), 94 (starting) and 64 (rival) real layer
  accessories.
- The rival table is one crest, id 25 with sample 32, repeated 32 times.

`python SRC/emblem.py crests DAT/EMBLEM 8` prints every crest field by
field with its layer accessories.

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
| 1 | 71 × 2 | `GetPresetFlagPatternData` | flag patterns: low byte a base (0–48), high byte its `rev` (0–3) |
| 2 | 27 × 4 | `GetPresetEmblemTs` | where the crest sits on the flag (`Param::PlFlagEmblemTs`) |

**Confirmed** (`EDIT::CFlagData::Initialize`, `0x1044b0`, and the field
table at `SLES 0x53cac8`–`0x53ccdc`). A flag preset (`PlFlagPreset`, 8
bytes) is `flag_pattern` u16 +0 (a row of table 1), `emblem_position`
u16 +2 (a row of table 2) and `aColor` 2 × u16 +4 (32-colour ids). It
becomes a `PlFlag` (`0x1c` bytes: `flag` `0x14`, then the
`flagpreset`), whose `flag` part is:

| Offset | Member | From |
|---|---|---|
| `+0x00` | `chunk` u32 | – |
| `+0x04` | `pattern.trs.rev` u8 | table 1's high byte |
| `+0x06` | `pattern.texture_num` u16 | table 1's low byte: the base in `EDIT_FLAG.PAC` |
| `+0x08` | `pattern.aColor` 2 × u16 | the preset's colours, as 96-colour ids |
| `+0x0c` | `emblem` {`pos_x`, `pos_y`, `size_x`, `size_y`} | table 2's 4 bytes |
| `+0x10` | `disp_emblem` u8 | – |

So the 4 variants of a base are 4 values of its `rev` byte, the same
member a crest part's `Trs` has; what each looks like (mirrored one way
or the other is the likely reading) hasn't been checked in the game.
Table 2 holds 9 positions (x −34, 0, 34 and so on) at three sizes,
`0x36`/`0x44`, `0x27`/`0x32` and `0x1e`/`0x26`: three sizes × a 3 × 3
grid (**empirical**).

## `EDIT_PLAYER.TBB`

32 tables, loaded by the two lists of `PLAYEREDIT_MODULE` in
`YRSTPRG.REL` together with message category 2000. That module is
sequencer module 63 (PlayerEdit), started from events
([`SNR2_FORMAT.md`](SNR2_FORMAT.md)), and module 115 in the developer
launcher, where it hangs ([`SQB_FORMAT.md`](SQB_FORMAT.md)). It is the
player editor that brings a Virtua Pro Football edit player into a
career ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-edit-player-from-virtua-pro-football)).

**How the tables are read (confirmed, `YRSTPRG.REL`, 2026-10-30).** Each
table has its own accessor (`0x1d128`–`0x1d418`, tables 9–31, through the
row getter `0x1d438`, row × line size; tables 0–8 through `0x1cf98`). All
but three are called from the code after `WP::CPlayerEditFrameResult`
that makes the finished player, in two drivers: `0x1a9c8` (tables 0–18
and 26–28) and `0x1aa70` (19–25). The player is the edit work's
`PlPbase` (decoded, `0x1d4f8` returns work `+4`; field offsets as in
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)), written through small setters:
`0x1d700` an ability (index < 64, capped at 99), `0x1d7e0` a
dissatisfaction weight (< 8), `0x1d850`/`0x1d870` a tendency (< 11, set
or added, 0–4), `0x1d8c0` a skill (< 16), `0x1d928` a play-style slot
(< 5, style < 23), `0x1d6d8` a position (< 3, apos < 14).

| Table | Rows × bytes | Read by | What it holds |
|---|---|---|---|
| 0–8 | 14 × 33 | `0x1ae98` | the base abilities 0–32: the table by the main position's cell (`plMisc_Apos2Epos`, 9 cells), the row by the nation (`0x1d040`: rows 0–5 England, France, Germany, Italy, Spain, the Netherlands; 6 the rest of the first scouting region; 7–13 the other regions by `plMisc_Nati2DRegion`, several sharing a row) |
| 9 | 4 × 13 | `WP::CPlayerEditWindowPositionSettingTask` (`0x128e8`, `0x12f58`) | which of the 13 positions (GK, LSB, RSB, CB, LWB, RWB, DM, LSM, RSM, OM, LWG, RWG, FW) belong to each of 4 groups: GK; LSB–CB; LWB–OM; LWG–FW (*empirical* reading of the 0/1 grid) |
| 10 | 9 × 9 | `0x1af68` | the 9 position aptitudes (abilities 33–41) by the cell of each of the player's positions (`+0x1c`–`+0x24`), 50 on its own cell; with two or three positions the rows are blended through `0x1cde8` (weights 3; 2 and 0; 1 and 1) |
| 11 | 3 × 3 | `0x1b2d0` | the same for the 3 side aptitudes (42–44), by `plMisc_Apos2Side` |
| 12 | 8 × 2 | `0x1b5d8` | the 8 dissatisfaction weights: {min, max}, min + rand(max − min + 1) (all 0–1) |
| 13 | 21 × 2 | `0x1b660` (`0x1cea0`) | {min, max} of single fields, in this order: tone, professionalism, pressure, loyalty, star, the first `explodetype`, moti_type, cond_type, potential, three unused rows (the growth types come from table 28), travel, injury_res, recovery, foul_avoid, weak_foot, policy, adapt, ball_touch, dribble_style |
| 14 | 146 × 26 | `0x1b7e0` (`0x1cc70`) | the player's policy (`+0x52`) by nation: each row a cumulative weighting, a random number below its last value picks the first entry at or above it |
| 15 | 19 × 2 | `0x1b828` | {min, max} of abilities 45–63 (all 51–80) |
| 16 | 11 × 2 | `0x1b8b8` | {min, max} of the 11 tendencies (all 0–1) |
| 17 | 16 × 1 | `0x1b940` | the 16 skills (all 0) |
| 18 | 22 × 1 | `0x1b9b8` | the 22 play styles, for the 5 style slots (all 0) |
| 19 | 319 × 144 | `0x1c078` | the effects of the editor's choices: the row is one of up to 8 choices the task keeps at `+0x38`; its bytes override the fields in table 13's order (byte 1 tone, 5 star, 6 `explodetype`, 7 moti_type, 9 the growth types …) and further fields, `0xff` leaving a field as it is (`0x1cef0`) |
| 20, 21 | 28 × 16, 28 × 116 | `0x1c5d0` | the same kind of overrides for another set of 28 choices |
| 22 | 13 × 11 | `0x1cb18` | added to the 11 tendencies by the player's position (13 positions), clamped to 0–4 |
| 23 | 13 × 16 | `0x1cb88` (`0x1cda0`) | the 16 skills by position |
| 24 | 22 × 16 | none | its accessor (`0x1d320`) has no caller |
| 25 | 32 × 1 | `0x1cc08` | a factor (byte ÷ 100, all 94) that scales abilities 0–32 (`0x1d780`); the row is the task's `+0x64` |
| 26 | 100 × 151 | `0x1ade0`, `0x1ae38`, `0x1ba58` | 100 player templates: byte 0 a nation and byte 6 a position, checked against the player's (`0x1ade0`, `0x1ae38`); the row is the task's `+0x60`, and `0x1a9c8` stores the result at `+0x58` |
| 27 | 1 × 2 | `0x1ae98` | the spread of the base abilities: each gets rand(5) − 2 |
| 28 | 3 × 16 | `0x1cd08` | the three growth types (physical, skill, mental, `+0x4a`–`+0x4c`), 0–15, drawn from cumulative weights like table 14 |
| 29 | 8 × 10 | `0x1cde8` | used by the position aptitude blend (`+4` 100–160 and `+6` 3–6 in steps); not traced further |
| 30, 31 | 13 × 16, 13 × 19 | `WP::CPlayerEditWindowHexagonGraphTask` (`0x13a98`, `0x13ce8`) | data for the editor's hexagon graph, one row per position; not traced further |

So the editor makes a player from his nation and position (tables 0–11,
14, 22, 23), personality and growth ranges (12, 13, 15–18, 28), and the
choices made in the editor (19–21, 25, 26), with ±2 randomness (27).
Whether this runs for a player brought in from Virtua Pro Football
(whose import fills the same edit work, [`PMPLAYER_FORMAT.md`](PMPLAYER_FORMAT.md))
or only for one made in the editor isn't traced. Which screen choices fill the
task's `+0x38`, `+0x60` and `+0x64`, and so which rows of 19–21, 25 and
26 a player gets, isn't traced. `python SRC/emblem.py info DAT/EMBLEM`
checks every table's shape, that the {min, max} rows (12, 13, 15, 16)
are in order and that the cumulative rows (14, 28) never fall, on both
releases. Nothing here has been checked in the game.

## Editing

`emblem.py set` edits `EDIT_EMBLEM.TBB` and `EDIT_FLAG.TBB` field by
field into a new file of the same size, which `patch_disc.py` can put on
a disc. It changes bytes in place, so the three short layer tables keep
their odd tails. Each field takes the values the game's readers above
use:

| Target | Fields | Values |
|---|---|---|
| `crest:<table>:<row>:<field>` (tables 7–9) | `sample`, `base`, `mask`, `pattern.<area>`, `acce.<area>`, `layer_key.<layer>` | a sample with layer tables (0–32), a row of table 4, an index in that base's mask group, a row of table 5, a row of table 6, a key |
| the same | `pattern_color.<area × 2 + n>`, `acce_color.<area × 3 + n>`, `layer_color.<layer × 3 + n>` | 0–31, or −1, −2, −3 for the club's colours |
| `preset:<table>:<row>:<field>` (tables 4–6) | `part`; `tx`, `ty`, `rot`, `rev`, `sx`, `sy` | a mask group (or 65535, no base), a pattern or an accessory; the `Trs` |
| `layer:<sample>:<layer>:<record>:<field>` | `key`, `acce`; the `Trs` fields | any key, an accessory or 65535 (empty). In the short tables only records 0–3, the ones the game reads correctly |
| `start:<row>:<field>` | `sample` (table 10), `color1`, `color2` (table 11) | a row of table 7; 32-colour ids |
| `flag:pattern:<row>:<field>` | `base`, `rev` | 0–48; 0–3 |
| `flag:place:<row>:<field>` | `pos_x`, `pos_y`, `size_x`, `size_y` | −128–127; 0–255 |

`rev` is limited to 0–3, the values the flag patterns use, as long as
what it does is unchecked. **User report** (2026-10-31): flag patterns
2–5, which are base 1 with `rev` 0, 1, 2 and 3 (`EDIT_FLAG.TBB` table 1
rows 1–4), looked the same in the flag editor.

**Which starting crest a new club gets (confirmed).** The club
set-up (`CEDITPRG.REL 0x20b0`) takes one index, 0–31, for the starting
design the player picks: it sets the club's kits from the 32 at
`CEDITPRG.REL 0x150a0` and copies table 8's row of that index as the
crest (`GetInitializeData`, `0x21a0`), with table 10's sample and table
11's colours. The starting crest follows the club's colour (user
report), and table 11's first byte in each row is the row's own index,
so the index is most likely the club's main colour, an id in the
32-colour palette: row 0 goes with colour 0, the first, a light pink
(`#ffbfbf`). So an edit to table 8 row *n* shows only for a new club of
colour *n*. **Tested in PCSX2** (user report, 2026-10-31,
`LMAST-test-season2.iso`, `crest:8:0:mask=1 crest:8:0:base=15`): a
club of another colour showed no change, as expected, and a new light
pink club started with row 0's crest on the edited base, a flat-topped
shield (mask `_mask_012_02`) instead of retail's notched top
(`_mask_031_03`), its accessories and layers as before. Changing a crest's `base` is refused when its
mask is past the new base's group; set the mask first. After the edits
the file is checked as `info` checks it, and written only if that finds
nothing.

```bash
python SRC/emblem.py set DAT/EMBLEM/EDIT_EMBLEM.TBB out.TBB crest:8:0:base=15 crest:8:0:mask=1 start:0:color1=5
python SRC/emblem.py set DAT/EMBLEM/EDIT_FLAG.TBB out.TBB flag:place:0:pos_x=-20
python SRC/emblem.py roundtrip DAT/EMBLEM
```

`roundtrip` decodes every preset, crest, starting-crest, layer and flag
record, encodes each again from its fields and rebuilds the file: both
files come out identical, on the PAL and the Japanese disc. No edit made
with `set` has been tried in the game yet.

The mod editor's Crests tab ([`USAGE.md`](../USAGE.md#the-window))
edits the same records through `set`'s functions. It takes the records,
fields and allowed values from `emblem.records`, `edit_fields` and
`get_value`, and logs each save as the `emblem.py set` commands that
make the same files. Tested through its widgets off-screen: nine edits
across both files, and a base change refused because the crest's mask
didn't fit the new base; the logged commands rebuilt both saved files
byte for byte, and a second session read the edits back from the mod
folder.

## Still unknown

- What a `Trs`'s `rev` values 1–3 do (a flag's four `rev` variants look
  the same in the flag editor, user report), what
  `chunk`, `texture_id` and `aLayer` hold, and which code reads `mask_num`
  (its match with the mask groups is empirical).
- Whether the three short layer tables lose visible parts in the editor.
- What the 33rd sample (32, the rival crest's) is, given table 7 has 29
  rows.
- `EDIT_PLAYER.TBB`: which editor choices pick the rows of tables 19–21,
  25 and 26 (task `+0x38`, `+0x60`, `+0x64`), the rest of table 19's
  144 bytes, and tables 29–31 ([`EDIT_PLAYER.TBB`](#edit_playertbb)).
- Why the 4bpp part textures' palette indices map to the chosen colours
  (the palette build wasn't traced).
