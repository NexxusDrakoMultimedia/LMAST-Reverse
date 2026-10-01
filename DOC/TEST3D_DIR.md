<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/TEST3D`: test models, textures and viewer data

`DAT/TEST3D` (163 files, 13.8 MB, plus `CVS/`) is folder id **7** in the
game's file manager ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). It holds the
developers' 3D test data: test models and motions, debug shapes, test
kits, and the data of the developer launcher's viewers. The retail game
doesn't need any of it. Its CVS history stops in October 2005
([`CVS_DIR.md`](CVS_DIR.md)), months before the rest of the data.

Every file parses with the existing tools: `python SRC/ninja.py info
DAT/TEST3D` (models and motions), `python SRC/svr.py info DAT/TEST3D`
(textures and palettes), `python SRC/pac.py info DAT/TEST3D` and
`python SRC/tbb.py info DAT/TEST3D`. None reports a problem. Only
`SHADOWCOLLI.LBI` has no reader.

| Kind | Files | Notes |
|---|---|---|
| `.SVR` | 80 | textures. 60 of the 101 texture files are named by a model in this folder, and `MILAN_01.SVM` by `DATABASE_FILETABLE.TBB` |
| `.SVM` | 9 | texture archives: six test kits, a player's face set, `ERR`, `TEST_SEAT` |
| `.SVP` | 12 | palettes `TST000_01FAC_*` and `TST001_01SKN_*` (face and skin, three tones × two) |
| `.SNO` | 16 | models: rooms, people, debug shapes |
| `.SNJ` | 23 | models: `HO02A_D1_*` (21 small untextured models), `M_TST000_01_1`, `MIP_TEST_PLANE01` |
| `.SNM` | 9 | motions |
| `.SNA` | 3 | node-name lists for `CAMERON`, `CLUBHOUSE`, `SUITMANDUMMY` |
| `.SND` | 1 | `CAM_INT1.SND`, a camera (`NSCA`) |
| `.PAC` / `.HED` | 5 / 3 | packs (below) |
| `.TBB` | 1 | `DATABASE_FILETABLE.TBB` (below) |
| `.LBI` | 1 | `SHADOWCOLLI.LBI` (below) |

No file here has a byte-identical copy anywhere else on the disc, and none
is in a `PRELOAD` pack (**empirical**). Each `.HED` is a copy of its
pack's header.

## What reads them

53 of the 163 files are named in the code. Everything that uses them is a
test or debug feature (**confirmed** where an address is given; the
launcher results are from [`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)).

| Files | Read by | Notes |
|---|---|---|
| `SPHERE_01`, `CUBE_01`, `TETRA_01`, `CYLINDER_01`, `TRIANGLE_01`, `CIRCLE_01`, `SQUARE_01` `.SNO` | `etc::LoadDebugObject` (`SLES 0x146534`, folder 7, list `0x35d200`) | debug shapes, drawn by `etc::_draw_debug_object` |
| `MILAN_01`, `_02`, `_11`, `REAL_01`, `_02`, `_11` `.SVM` | `CPlayer::ChangeUniform` (`SLES 0x2c6d38`, list `0x3a1d00`, folder 7) | six test kits by index. The callers weren't traced |
| `SEC_TEST.SNO` | `MODEL_VIEWER_MODULE::CModelViewerModule::CallExecute` (`TESTPRG.REL 0xb80`) | launcher module 73, MODEL VIEWER: shows a test triangle with axis lines |
| `VIEWERPLAYERMOTION.HED`/`.PAC`, `VIEWERSECRETARYMOTION.HED`/`.PAC` | `CCharacterViewer::CallExecute` (`TESTPRG.REL 0x190a4`, `0x19104`) | launcher module 104, CHARACTER VIEWER (works). The packs hold 5 player motions (`mendan_Asit_ang_001`–`004`, `mendan_sit_ang_001`) and `cameron.snm` |
| `EDIT.HED`/`.PAC` | `EMBLEMEDIT_TEST_MODULE::CEmblemEditTestModule` (`TESTPRG.REL 0x9d34`) | module 82, EMBLEM EDIT TEST (hangs). The pack is 502 `.svm` versions of the club editor's parts: 217 `emb_acce`, 214 `emb_mask`, 49 `flag_base`, 22 `emb_pattern`, the same sets as the retail `EMBLEM/` packs ([`EMBLEM_DIR.md`](EMBLEM_DIR.md)) |
| `ENG_00_MICHAEL_OWEN.SNO` | `SUGIO_TEST::CCheckFaceTask` (`TESTPRG.REL 0xa8b8`) | module 89, SUGIO TEST (a plain teal screen) |
| `NEWS_TEST.SVR` | the load list of `NEWS_TEST_MODULE` (`TESTPRG.REL 0x2be38`, a texture list, folder 7) | the news test module |
| `CAMERON.SNM` | a `TESTPRG.REL` name list (`0x2f170`) | next to the viewer motion packs |
| `MOJI_OYA.SNO`, `M_TST000_01_1.SNJ`, `ARG_00_DIEGO_SIMEONE.SNO`/`.SVM`, `01.SNO` | an executable list of {model, textures, folder 7, folder 7} (`SLES 0x346d20`) | users not traced |
| `SUITMANDUMMY.SNO`, `CAMERON.SNO`, `CLUBHOUSE.SNO`, 7 `.SNM`, `CAM_INT1.SND` | executable lists at `SLES 0x3472d0` | users not traced. The list also names `wi_n_sib06.sno` and `ibg_en_1a.sno`, which aren't on the disc |
| the 12 `.SVP` | names at `SLES 0x5214d8`, pointed to from `0x4b0634` | users not traced |
| `ERR.SVM`, `ERR.SVR` | strings at `SLES 0x51b298`, `0x51b2a0` | no pointer to them was found |

`CAM_INT1.SND` is also named by `GAMEPRG.REL` (`0x20e9c0`) and `SIMPRG.REL`
(`0xf7ff8`), but they load it from folder 14, `BG/CAM_INT1.SND`. That copy
differs from this one, which is older (December 2004) and isn't read there.

The other 110 files aren't named anywhere in the code. Most are textures
named by the test models' texture lists (`01.SNO` names 22 of them, the
room models and the people the rest).

## The test models

By the names of their files and textures (**empirical**; none has been
looked at in a viewer):

| Model | What |
|---|---|
| `01.SNO` (6,522 vertices), `CLUBHOUSE.SNO` | rooms: floor and wall tiles, sofa, windows, a vending machine (`JIHANKI_02`) |
| `CAMERON.SNO` (+ `.SNA`, `.SNM`) | a woman (`CAMERON_DRESS01`, `_SKIRT02`, `CAME_HAIR`), with her motion |
| `SEC_TEST.SNO` (+ `.SNM`) | a secretary test model (`ROSA_*` textures, 20,232 vertices) |
| `SUITMANDUMMY.SNO` (+ `.SNA`, `.SNM`) | a man in a suit, with a motion of frames −10 to 736 |
| `MOJI_OYA.SNO` (+ `.SNM`) | a figure in a kimono with a headband (`KIMONO_257`, `HATIMAKI128`) |
| `ARG_00_DIEGO_SIMEONE.SNO`, `ENG_00_MICHAEL_OWEN.SNO` | two real players' heads (2 meshes, about 1,240 vertices each) |
| `M_TST000_01_1.SNJ` | a test player body (41 nodes) |
| `HO02A_D1_*.SNJ` (21) | small untextured models, 16–608 vertices. Not identified |
| `MIP_TEST_PLANE01.SNJ` | a mipmap test plane |
| `SHC3.SNO` | 4 meshes, 32 vertices |
| the debug shapes | sphere, cube, tetrahedron, cylinder, triangle, circle, square |

`CHIPKICK_000F_RUN_RUN`, `LINK_BREADY_DRIBBLE_000F`, `LINK_RUN_READY`,
`READY_LOOP_READY_READY` and `RUN_LOOP_RUN_RUN` are footballer motions at
60 fps, 16–66 frames each.

## Packs and tables

| File | Contents |
|---|---|
| `EDIT.PAC` | the 502 club-editor parts as `.svm` (above) |
| `VIEWERPLAYERMOTION.PAC`, `VIEWERSECRETARYMOTION.PAC` | the CHARACTER VIEWER's motions (above) |
| `TESTDATA_PACK.PAC` | `TEST_512_448.svm` (a texture archive) and `TEST_512_448.zb` (917,504 bytes = 512 × 448 × 4, presumably a depth buffer like the pre-rendered rooms' in [`ZBF_FORMAT.md`](ZBF_FORMAT.md)). Not named in the code |
| `BGDATA_PALETTE.PAC` | 29 palettes `000.svp`–`028.svp` (BINPAC version 2). Not named in the code |
| `DATABASE_FILETABLE.TBB` | 4 tables of 64-byte rows. Tables 0–2 each hold a row with `0x37` and a row with a file name (`M_tst000_01_1.snj`, `MILAN_01.svm`, `run_loop_run_run.snm`); table 3 is empty. Its header's total-size field is 0. Not named in the code |

The 14 `TXCMN_ADT_*.SVR` textures (`010`–`017`, `A001`–`A004`, `LED`,
`SCR`) are advert boards. The retail adverts are
`0SYSTEM/SPONSOR_TEXTURE_M.PAC` (`txcmn_adt_000`–`231`) and the `STADIUM`
packs; these are not named anywhere.

## `SHADOWCOLLI.LBI`

1,536 bytes, dated February 2005, and not named in the code. It starts
like each of the 27 entries of `GAME/SHADOWCOLLI.PAC` (`ff ff ff ff`, then
counts and floats), the stadium shadow-collision data
([`STADIUM_DIR.md`](STADIUM_DIR.md)), but it matches none of them. The
format isn't decoded; that is a separate task, together with the `GAME/`
pack.

## Still unknown

- Who reads the executable's lists at `0x346d20`, `0x3472d0` and
  `0x4b0634` (probably the 3D TEST module, launcher entry 72, which hangs).
- Who calls `CPlayer::ChangeUniform` with the test kits.
- `DATABASE_FILETABLE.TBB`'s `0x37`, and the `.LBI` format.
