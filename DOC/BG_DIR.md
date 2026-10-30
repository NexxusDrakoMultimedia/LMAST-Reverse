<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/BG`: rooms, people, hands, props and trophies

`DAT/BG` (484 files, 170.7 MB, plus `CVS/`) is folder id **14** in the
game's file manager ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). It holds what
the club-house scenes draw: the data that goes with each pre-rendered room
(depth buffer, camera, palettes), the 3D practice pitch, 103 people
with their heads, hair and palettes, hands and the props they hold, 42
trophies, and `HUMANID.BIN`, which picks a person for a role. The room
pictures themselves are in `CSE/BG_xx_nn_00.CSP`
([`CSE_FORMAT.md`](CSE_FORMAT.md)).

Every file parses with the existing tools, and none reports a problem
beyond the one below:

```bash
python SRC/pac.py info DAT/BG        # the 304 .MRG archives and 11 .HED headers
python SRC/ninja.py info DAT/BG      # models, motions, cameras, lights
python SRC/svr.py info DAT/BG        # textures and palettes
python SRC/zbf.py info DAT/BG        # the 140 depth buffers
python SRC/humanid.py info DAT       # HUMANID.BIN and its PRELOAD copies
```

`zbf.py` marks `BG_MN_00_00.zbf`, which is filled with `0x01000000`
([`ZBF_FORMAT.md`](ZBF_FORMAT.md#values)).

| Kind | Files | Notes |
|---|---|---|
| `.MRG` | 304 | 180 rooms (`BG_*`), 3 chairs, 103 people (`HUMAN_nnnn`), 6 palette packs, and the hair, hand, head, motion, skin, cut-in hand and object packs |
| `.HED` | 11 | a copy of the header of the `.MRG` of the same name (BINPAC v2) |
| `.SVR` | 109 | 84 trophy textures `TRO_nnA`/`TRO_nnE`, 25 textures of props, skin and clothes |
| `.SNO` | 46 | 42 trophies, three hands, the shadow `KAGE000` |
| `.SNM` | 10 | motions (below) |
| `.SNJ` | 1 | `BG_IP_00_00.SNJ` |
| `.SND` | 1 | `CAM_INT1.SND`, a camera ([`TEST3D_DIR.md`](TEST3D_DIR.md#what-reads-them)) |
| `.BIN` | 1 | `HUMANID.BIN` ([below](#humanidbin)) |
| `.DAT` | 1 | `DUMMY.DAT`, empty |

Merge user IDs, the column the loader matches an entry by, are in
[`PAC_FORMAT.md`](PAC_FORMAT.md). The Ninja chunks (cameras, lights,
models, part files `.snq`, skeletons `.snp`, name lists `.sna`, texture
lists `.snt`) are in [`NINJA_FORMAT.md`](NINJA_FORMAT.md).

## The rooms (`BG_xx_nn.MRG`)

**Confirmed**: the room archives are loaded by the name `BG_%s_%02d.mrg`,
built with `sprintf`. The format string is in `SIMPRG.REL` 61 times,
and 22 times more in the executable, `CEDITPRG.REL`, `SAVEPRG.REL`,
`TESTPRG.REL`, `VSPRG.REL` and `YRSTPRG.REL`. The code comes from a
table of 14 pointers at `SIMPRG.REL 0x1d69d8`, returned by
`0xfd210(index)`:

| Index | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Code | `CH` | `OF` | `OR` | `TR` | `RR` | `EN` | `IS` | `P2` | `P2` | `IP` | `SP` | `FS` | `TV` | `OR2` |

A second copy at `0x1d6a10` (returned by `0xfd228`) has `OR` instead of
`OR2` at index 13. `MN` and `PP` aren't in either table; the background
classes `CBGScene_MNTC` and `CBGScene_PP` (`SIMPRG.REL`) handle those two,
next to `CBGScene_CH`, `_FS`, `_IP`, `_OF`, `_OR` and `_RR`.

What each room is, from its picture in `CSE/` and the name of the
Acrobata scene class that matches it (`ACROBATA::VRBG_*`,
[`ACROBATA_DIR.md`](ACROBATA_DIR.md)). Both are **empirical**: the
pictures were looked at, and the classes weren't traced to a code.

| Code | Archives | Pictures in `CSE/` | Room | Acrobata class |
|---|---|---|---|---|
| `CH` | 11 | 11 | club house hall, benches and a table | `VRBG_ClubHouse` |
| `EN` | 6 | 6 | entrance with glass doors | `VRBG_Entrance` |
| `FS` | 12 | 12 | a street with fans | `VRBG_Stadium`? |
| `IP` | 4 | 4 | press room, a table with a microphone | `VRBG_InterviewRoomCH`? |
| `IS` | 1 | 0 | – (its depth buffer has `IP_03`'s range) | `VRBG_InterviewRoomSTD`? |
| `MN` | 1 | 1 (`BG_MNTC_00_00`) | tactics board menu; its depth is "far" everywhere | – |
| `OF` | 9 | 9 | office with desks and shelves | `VRBG_Office` |
| `OR` | 24 | 24 | a smaller office with a desk and a TV | `VRBG_MyRoom`? |
| `OR2` | 24 | 0 | – | – |
| `P2` | 8 | 8 | practice pitch | `VRBG_TrainingField` |
| `PP` | 8 | 1 | practice pitch, as 3D models | `VRBG_TrainingField` |
| `RR` | 3 | 3 | meeting room with a team photo | `VRBG_ReceptionRoom` |
| `SP` | 64 | 65 | sports pub | `VRBG_SportsPub` |
| `TR` | 0 | 3 | trophy room, empty shelves | `VRBG_TroffyRoom` |
| `TV` | 5 | 5 | TV studio | `VRBG_TVStudio` |

`SP` has one extra picture, `BG_SP_33.CSP`, next to `BG_SP_33_00.CSP`.
`TR` has pictures but no archive here. The trophies stand on its shelves
([below](#trophies)), and `SIMPRG.REL` names lights `BG_TR_00_LIGHT`–`02`
and `BG_PP_00_LIGHT`–`07` for the two 3D rooms.

### Inside a room archive

Every room archive uses fixed slots (**empirical**, all 180):

| Slot | Entry | Merge ID | In |
|---|---|---|---|
| 0 | `BG_xx_nn_00.zbf`, the depth buffer ([`ZBF_FORMAT.md`](ZBF_FORMAT.md)) | 4 | all but `OR2`, `P2`, `PP` (140) |
| 1 | `BG_xx_nn_00.snd`, the camera the picture was rendered with | 0 | all but `PP` (172). `MN`'s is empty |
| 2 | `.snl`, a light | 0 | `OF_00`, `OF_03` |
| 5–13 | `BG_PP_nn_0k.snj`, models | 2 | `PP` (7 to 9 each) |
| 15–23 | `BG_PP_nn_0k.svm`, their textures | 3 | `PP` |
| 20–51 | `BG_xx_nn_00.svp` … `_31.svp`, 32 palettes | 4 | `CH`, `EN_00`–`03`, `FS`, `OF`, `OR`, `OR2`, `RR` (87) |

Empty slots are `dummy.bin`. The archives have 52 slots when they carry
palettes, 21 when they don't, and 22 to 24 for `PP`.

### Which room a scene shows

`SIMPRG.REL 0x1d3e50` holds a table of 198 records of `0x38` bytes (14
s32), ended by a record whose first field is `-0x80`. `0xfd250` matches
a request against
it field by field, `-0x80` matching anything, and copies the first match
(**confirmed**). The rest is **empirical**: fields 4 and 5 are ranges
(18–99, 6–19, −10–7) that look like the temperature bands
[`HUMANID.BIN`](#humanidbin) uses, fields 6 and 7 another range (0–20000,
20001–99999), and field 11 counts from 0 within each combination of
fields 0 and 12, in groups of 24, 3, 64, 24 and 8: the sizes of the
`OR`, `RR`, `SP`, `OR2` and `P2`/`PP` sets. Which field is the room code wasn't
traced.

## People (`HUMAN_nnnn.MRG`)

103 archives, one person each, loaded by the name `HUMAN_%d.mrg`
(`sprintf` at `SIMPRG.REL 0x10c7e4`, the number from the caller's object
`+0x994`, folder 14). Each has the same slots (**empirical**, all 103):

| Slot | Entry | Merge ID |
|---|---|---|
| 0 | `HUMAN_nnnn.snp`, the skeleton (32 nodes) | 0 |
| 1 | `HUMAN_nnnn.sna`, its node names | 2 |
| 2–10 | `HUMAN_nnnn_<part>_1.snq`, 1 to 9 body parts | 0 |
| 17 | `.svm`, the textures | 1 |
| 19 | `HUMAN_nnnn_MODEL.snt`, the texture list | 2 |
| 20–24 | `.snm`, a motion (five in `HUMAN_9999`) | 3 |

`python SRC/ninja.py gltf out/human.gltf DAT/BG/HUMAN_1000.MRG` exports
one ([`NINJA_FORMAT.md`](NINJA_FORMAT.md#tools)). The numbers come in
groups: 1000–1400 (5), 2000–2805 (27), 3000–3016 (17), 3600–3705 (12),
4000–4602 (12), 5000–5602 (11), 6000–6101 (5), 9000–9600 (13) and 9999.
`HUMAN_1000`'s parts (`l_pra_bdy1`, `l_sox`, `l_spk`) are a player in
training kit.

| File | Contents |
|---|---|
| `HUMAN_1000`–`1300_PALETTE.MRG` | 16 palettes each. The four files are byte-identical, and so are their `.HED`s |
| `HUMAN_1400_PALETTE.MRG` | 3 palettes |
| `HUMAN_2000_PALETTE.MRG` | 32 palettes |
| `HUMAN_SKIN.MRG` | 20 palettes |
| `HUMAN_HAIR.MRG` | 10 hair models, each with its `.svm` (`buz001`, `lon011`, ...) |
| `HUMAN_HAIR_COLOR.MRG` | 63 palettes |
| `HUMAN_HEAD_MODEL.MRG`, `HUMAN_HEAD_TEXTURE.MRG` | 11 heads `HUMAN_head_9000`–`9600` and their textures, numbered like 11 of the 13 people `HUMAN_9000`–`9600` |
| `HUMAN_HEAD_9100.SNM` | a head motion, named in both head packs |
| `HUMAN_MOTION_FACE.MRG` | 73 face motions |
| `HUMAN_MOTION_REACTION_STAND.MRG`, `_SIT.MRG` | 17 and 16 reactions, loaded by `CTalkImplement::loadReactionData` ([`MBB_FORMAT.md`](MBB_FORMAT.md)) |
| `EVENT_HMN_SKIN.SVR`, `EVENT_HMN_SKINF.SVR` | skin textures, named by 68 and 30 files (the 27 people `HUMAN_26xx`–`28xx`, `36xx`–`37xx`, `46xx` and `56xx` use the `F` one); `SIMPRG.REL 0x22a950`, `0x22a968` name them |
| `ORG_000_SHT.SVR` | a shirt, named by 16 people `HUMAN_2000`–`2702` and `HUMAN_HAND_SPECIAL`; `SIMPRG.REL 0x22ab80` names it |

## Hands, props and furniture

| File | Contents | Named in the code |
|---|---|---|
| `HUMAN_HAND.MRG` | 35 hand models, one `.svm`, one `.snt` (92 slots) | `SIMPRG.REL 0x214338`, `0x22a9e8` |
| `HUMAN_HAND_SPECIAL.MRG` (+`.HED`) | 16 models, merge ID 5 (90 slots); their textures are the props below | `SIMPRG.REL 0x22aa10` |
| `CUTINHANDPACK.MRG` | 22 nameless `.sno` hands | `GAMEPRG.REL 0x266760` |
| `HAND_00L.SNO`, `HAND_02L.SNO`, `HAND_03L.SNO` | left hands; no pack entry has the same bytes | no |
| `BAG`, `BEER`, `CAMERA`, `CARDBOARD`, `DOCUMENT`, `FILE`, `JUG`, `JUG2`, `JUG_ME`, `MEMO_BOOK`, `MIC`, `NUM_00_0`, `PEN_00`, `PHONE`, `PHONE_00`, `SECRETARY_HAND`, `VIDEO_CAM` `.SVR` | the props' textures, each named by `HUMAN_HAND`, `HUMAN_HAND_SPECIAL` or a person | `SECRETARY_HAND` only (`SIMPRG.REL 0x22a998`) |
| `BG_CHAIR_0`–`2.MRG` | chairs `chair_Lv1`–`Lv3`, a model and its textures | `SIMPRG.REL 0x22a878` |
| `OBJECT_0000.MRG` | `s_chair`, a model and its textures | no |
| `KAGE000.SNO`, `.SVR` | a shadow (*kage*) | `SIMPRG.REL 0x214388` |
| `BG_IP_00_00.SNJ` | a model for the press room | `SIMPRG.REL 0x22a158` |

## Trophies

42 trophy models, named after their competition (`PREMIER_DIVISION.SNO`,
`EUROPEAN_CLUB_CUP.SNO`, `WORLD_NATIONAL_CUP.SNO`, ...), each with a
texture pair `TRO_nnA.SVR` and `TRO_nnE.SVR`, numbered 01–40, 42 and 43
(**empirical**: each model's texture list names exactly its pair). 40 of
them are named in both `GAMEPRG.REL` (from `0x24eb90`) and `SIMPRG.REL`
(from `0x1d3050`). `EURO_NATIONAL_CUP` and `WORLD_NATIONAL_CUP` aren't
named anywhere in the code.

## `HUMANID.BIN`

The human database: which person (outfit) a scene shows for a role,
depending on the weather. 3,230 bytes, 323 records of 10 bytes, one per
human id. Read by `python SRC/humanid.py`.

**Confirmed from the game code:**

| Address | Symbol | What it shows |
|---|---|---|
| `SIMPRG.REL 0x2146c8` | (a load-list record) | the file is loaded from folder 14 as `HumanID.bin` |
| `SIMPRG.REL 0x7d7c` | → `CHumanDataBase::setup` (`SLES 0x2d3e98`) | the loaded file is handed over; `setup` only keeps the pointer |
| `SLES 0x2d3d08` | `CHumanDataBase::CHumanDataBase` | fills 38 search-function slots (below) |
| `SLES 0x2d3ea0` | `CHumanDataBase::search(id, result, arg)` | reads record `id` (`id × 10`), the layout below |
| `SLES 0x2d4090` | `CHumanDataBase::getObjectData(object, out)` | reads entry `object` of the object table |
| `SLES 0x3a2470` | `s_aHumanDataBase_ObjectDataBase` | the object table, `{u32 kind, u32 index}` per object |

| Offset | Type | Meaning |
|---|---|---|
| `+0` | s8 | search function, −1 = none: `search` calls slot *n* as `fn(result, arg)` |
| `+1` | s8 × 3 | objects for a warm day, 19 °C or more |
| `+4` | s8 × 3 | objects for a mild day, 6–18 °C |
| `+7` | s8 | object for a cold day, below 6 °C |
| `+8` | s16 | copied to `result + 0` when it isn't negative |

The temperature is `plCity_GetTemperature` for the club's city on
today's date. On a warm or mild day `search` counts the group's leading
objects that aren't −1 and picks one at random (`fcEuroRand_Get0toI`).
The object's kind and index go to `result + 4` and `+ 8`. The result is
`0x14` bytes, set to −1 first.

The search-function slots, as the constructor fills them:

| Slot | Function | Record that uses it |
|---|---|---|
| 19 | `HumanSearch::Player_PlainCloth` | 19 |
| 30 | `Staff_M_Rand` | 294 |
| 31 | `Staff_F_Rand` | 307 |
| 32 | `Secretary_My` | 277 |
| 33 | `Manager_My` | 188 |
| 34 | `YouthManager_My` | 189 |
| 35 | `Agent` | 203 |
| 36 | `NazoCoach` | 214 |
| 37 | `YouthRand` | 322 |
| the other 29 | `Dummy` (returns 1, does nothing) | 0–18, 20–29 |

The callers at `SIMPRG.REL 0xff5f0` and `0xff60c` ask for ids 294 and
307 (`0x126`, `0x133`), and `0xff778` asks for 19.

**Empirical** (`python SRC/humanid.py info DAT`, both releases): 38
records have a search function and no objects, 265 have objects, 20 have
neither. The objects used are 100 of ids 0–111, and 226 records have a
`+8` value (0–214). In every record the objects of a group come first,
so no object is skipped. The table entries the file uses have kinds 1–4.
The file, its seven `PRELOAD` copies and the object table are the same
in the Japanese release.

```bash
python SRC/humanid.py dump DAT/BG/HUMANID.BIN ISO   # every record, with each object's kind:index
python SRC/humanid.py objects ISO                   # the object table
```

## Copies and files nothing names

Nine files have copies in `PRELOAD` packs, all byte-identical
([`PRELOAD_DIR.md`](PRELOAD_DIR.md)): `HumanID.bin`,
`HUMAN_HEAD_MODEL.hed` and `HUMAN_HEAD_TEXTURE.hed` in `SIMFILE0`–`6`;
`HUMAN_1200_PALETTE.hed`/`.mrg`, `HUMAN_HAND_SPECIAL.hed`,
`HUMAN_MOTION_FACE.mrg`, `HUMAN_SKIN.mrg` and `kage000.sno` in
`SIMLOCALMEM0`–`6`; `HUMAN_HAND.mrg` in `SIMLARGE`. An edit to one of them
needs `patch_disc.py --copies`.

Three loose motions have copies elsewhere: `FF_04_0.SNM` and
`FF_04_3.SNM` equal `GAME/`'s, and `NOM_00.SNM` equals `PLAYER/`'s. The
six loose `FF_*.SNM` differ from the entries of the same name in
`HUMAN_MOTION_FACE.MRG`.

Not named by the code, nor by any model's texture list: `FF_*.SNM`,
`KUBIMAWASHI_TEST.SNM` and `_30.SNM` ("head turning test"), `NOM_00.SNM`,
`HAND_00L`/`02L`/`03L.SNO`, `OBJECT_0000.MRG`, and the textures
`KANKYO_32`, `NAKA_TE_ASHI`, `PEN_CUP_00` and `JUG_ME2`. Of the 304
archives, the code names 19 directly; the rooms and people go by the two
patterns above.

## Still unknown

- Which room code each Acrobata class and each scene uses, and what
  `OR2` (palettes and cameras, but no depth buffer or picture) and `IS`
  (no picture) are for.
- The fields of the room table at `SIMPRG.REL 0x1d3e50`, and which of
  the 32 palettes a room uses ([`ZBF_FORMAT.md`](ZBF_FORMAT.md)).
- Why the code table has `TR` when there is no `BG_TR` archive.
- `HUMANID.BIN`: what the object kinds 1–4 and their indexes select (a
  person number, a palette?), what the `+8` value is, and which roles
  ids 30–321 are. The object table's size: nothing bounds it, and 112
  is the highest id used + 1.
- What `TRO_nnA` and `TRO_nnE` each are, and what number 41 was.
- Who uses `HUMAN_HAND_SPECIAL`'s merge ID 5 and the people's slots 2–16.
