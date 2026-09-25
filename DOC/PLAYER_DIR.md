# `DAT/PLAYER`: player models, faces, hair and kits

`DAT/PLAYER` (92 files, 1.3 GB) holds everything needed to draw a player:
body models, one head per real player, hair, glasses, the licensed club
kits and the edit-mode kit parts. 1.1 GB of it is one file,
`FC_EURO_FACEPACK_00.BIN`.

Every archive here is either a BINPAC or a KC@P pack (see
[`PAC_FORMAT.md`](PAC_FORMAT.md)), and `python SRC/pac.py info DAT/PLAYER`
parses all of them. This doc covers what the entries hold. Most are Ninja
models (`NSIF`) or textures (`PVMH`/`GBIX`/`PVPL`, see
[`SVR_FORMAT.md`](SVR_FORMAT.md)). The three KC@P packs wrap each entry in
a second container, **`etc::PackData`**, which is described below.

The `PackData` layout and the role of each block are **confirmed** from the
game code. Everything else here (what the names mean, counts) is
**empirical**.

## Directory overview

| Files | Container | Entries hold |
|---|---|---|
| `FC_EURO_FACEPACK_00.HED` + `.BIN` | KC@P, PRSH entries | 21,171 real-player heads, one `PackData` each (see [Face packs](#face-packs)) |
| `FC_EURO_FACEPACK_01.HED` + `.BIN` | KC@P, PRSH entries | 215 heads for event characters (referees, supporters, staff, commissioners) |
| `EDITFACEPACK_BIN.HED` + `EDITFACEPACK.BIN` | KC@P, 1 raw entry | the face-edit resources, one `PackData` (see [Edit face pack](#edit-face-pack)) |
| `PLPACK_HOME.HED` / `_AWAY` + `.PAC` | KC@P, 116 raw entries | licensed club kits, one `PackData` per club (see [Licensed kits](#licensed-kits-plpack_)) |
| `PLAYER_MODEL.PAC/.HED`, `PLAYER_MODEL_PRI.PAC/.HED` | BINPAC v1, extension-only names | 267 / 317 entries: `.svm` textures, `.snq`/`.sno` models, `.snp` node trees, one `.sna` |
| `PLAYERDATACOMMONPACK1.MRG`, `PLAYERDATACOMMONPACK2.MRG/.HED`, `PLAYERDATAONEPACK.MRG` | BINPAC v2 (merge) | body models. `COMMONPACK2` has 12 named `LMS_player_l_{nml,tgt}_bdy_NN_el.snq`; the other two keep only extensions (117 `.snq`, 6 `.snp`, 20 `.svm`, 38 `.svp` between them) |
| `HAIR_PACK.PAC/.HED` | BINPAC v2, a PAC of `.mrg`s | 516 hair styles (`bal001.mrg` ... `ski000_cap.mrg`); 513 are one `.sno` + one `.svm`, 3 are empty |
| `HAIR_PALETTE.PAC/.HED` | BINPAC v2 | 63 hair palettes (`Data/bal_buz_ski_blue01.svp` ...) |
| `GLASSESPACK.MRG` | BINPAC v2 | 14 `.sno` + 1 `.svm` + 31 `.svp` |
| `CUTINHUMANPACK.MRG/.HED` | BINPAC v2 | 41 cut-in figures, `HUMAN_NNNN.snj` + `.svm` |
| `EDIT_UNIFORM_{ORG,GK}_{SHT,PNT}`, `EDIT_UNIFORM_ORG_SOX` `.PAC/.HED` | BINPAC v3 | edit-kit textures (`org_000_sht.svr`, `gk_000_sht.svr` ...) |
| `EDIT_UNI_{SHT,PNT}_NUM.PAC/.HED` | BINPAC v3 | the same kits with numbers applied (`00/num_00_99.svr` ...) |
| `EDIT_UNIFORM_CLUT{,_PRESS}.PAC/.HED` | BINPAC v3 | 96 kit palettes (`org_uni_A1.svp` ...) |
| `NUMBER_00`–`_07{,_PRESS}.PAC/.HED`, `NUMBER_CLUT{,_PRESS}` | BINPAC v3 | 8 shirt-number fonts × 100 numbers (`num_00_00.svr` ... `num_00_99.svr`), 96 palettes |
| `COLOR_TBL.TBB` | TBB, 96 × 96 bytes | bytes are 0/1: probably a mask per kit pattern. Unknown |
| `UNIFORM_LIST.TBB` | TBB, 661 × 64 bytes | read by `UniformList_*` (`0x2d3078`–`0x2d3608`). Bit-packed, unknown |
| `UNIFORM_GK.TBB` | TBB, 209 × 3 and 38 × 66 bytes | 209 and 38 match the `ORG_SHT` and `GK_SHT` entry counts. Unknown |
| `*.SNO`, `*.SNM`, `*.SNP` | Ninja | loose models (`HUMAN_1200.SNO`, `L/M/S_PLAYER.SNO`), motions, one node tree |
| `*.SVR`, `*.SVM` | textures | `ACCE_CAP`, `HUM1200_H`, `REF_000_*` (referee kit) ... |
| `CVS/` | CVS metadata | original mixed-case names and revision numbers |
| `DUMMY.DAT` | 0 bytes | |

The `_PRESS` archives repack their sibling with 16-byte alignment and PRSH
entries, as elsewhere on the disc.

## `etc::PackData`

A small container that sits inside each KC@P entry (after PRS expansion
for the face packs). It is a table of offsets followed by typed blocks.

### Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x11f5e8` | `etc::PackData::GetPackBlockNum` | block count is `u32@0` |
| `0x11f5f8` | `etc::PackData::GetPackBlock(int i)` | the table layout and padding below. An out-of-range `i` returns block 0 |
| `0x11f598` | `etc::PackBlock::GetPackBlockType` | `u32@+0` of a block |
| `0x11f5a8` | `etc::PackBlock::GetSize` | `u32@+4` |
| `0x11f588` | `etc::PackBlock::GetDataTop` | data starts at `+8` |
| `0x11c108` | `CLoader::l_realize_facepack` | face-pack block roles |
| `0x11c730` | `CLoader::l_realize_licenceuniform` | kit block roles |
| `0x11cc08` | `CLoader::l_realize_editfacepack` | edit-face block roles |

### Layout

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u32 | block count *n* |
| `0x04` | u32[*n*] | offset of each block, relative to the **data base** |
| – | – | zero padding up to the data base |

The data base is `base = 4 * (n + pad + 1)`, where `pad` is 1, 0, 3, 2
for `n % 4` = 0, 1, 2, 3. `GetPackBlock` computes it with that exact
switch. The result always has `base % 16 == 8`, so the base itself is
**not** 16-aligned. It is the first block's *data* (`base + 8`) that lands
on a 16-byte boundary. Examples: *n* = 5 gives base `0x18` (face packs),
*n* = 7 gives `0x28` (`PLPACK`), and *n* = 32 gives `0x88`
(`EDITFACEPACK`).

Each block:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | u32 | type |
| `0x04` | u32 | data size |
| `0x08` | – | data |

None of the three realizers calls `GetPackBlockType`. They take blocks by
index, so the type is informational. The values seen (0–3, 16, 25–28) are
listed per pack below.

**Empirical:** in every entry on the disc the blocks are packed back to
back: block 0 is at offset 0, and each next block starts at the previous
offset plus `(8 + size)` rounded up to 16. The face-pack entries end
exactly at the last block. The KC@P entries of `PLPACK_*` and
`EDITFACEPACK` have zero padding after the last block, up to the KC@P
entry size.

## Face packs

`FC_EURO_FACEPACK_00.BIN` holds the heads of real players, and
`FC_EURO_FACEPACK_01.BIN` those of event characters. Every KC@P entry is
PRSH-compressed, and expands to a 5-block `PackData`.

`CFaceLoader::LoadRequest` (`0x103450`) picks the pack. A player whose
`Param::PlPinfo` is not an edit player goes to `LoadRequestNormal`
(`0x1036a8`) with the u16 at **`PlPinfo+0x1ca`** as the entry index into
`fc_euro_facepack_00.bin`. The value `0xFFFF` there means the face is built
in the face editor instead. `LoadRequestEvent` (`0x103770`) loads from
`fc_euro_facepack_01.bin`.

| Block | Type | Contents | Used by `l_realize_facepack` as |
|---|---|---|---|
| 0 | 0 | `NSIF` head model. Its `NSTL` names one texture, e.g. `ENG_00_Matthew_UPSON.svr` | `convertNNDBinary`, then `nnCompileCommonVerticesObjectHybridPS2` |
| 1 | 1 | `PVMH`, one 128×128 texture with the same name | copied, opened as a texture |
| 2 | 2 | `NSIF` hair model (`buz004.svr`, `sho024.svr` ...), or empty | converted only if size > 0 |
| 3 | 3 | `PVMH` hair texture, or empty | opened as a second texture |
| 4 | 0 | 0x426 bytes: a 0x18-byte header, then a 256-colour `PVPL` palette | copied |

All 21,171 + 215 entries have exactly this shape: 5 blocks, types
`0,1,2,3,0`, and a 0x426-byte block 4. Blocks 2 and 3 are empty in 891
entries of pack 00 and 22 of pack 01. The first four bytes of block 4 are
small values such as `00 03 02 02`, or `ff ff ff ff`. In pack 01 the 22
`ff ff ff ff` entries are exactly the 22 without hair. Pack 00 has not been
checked for the same match. The meaning of the 0x18-byte header is
unknown. It also holds three u32s that are usually 1000 (`0x3e8`).

Pack 00's head-texture names fall into groups:

| Name pattern | Entries | Notes |
|---|---|---|
| `<NAT>_<NN>_<First>_<LAST>` | 7,035 | real players. `NAT` is one of 113 three-letter codes (`ESP` 725, `ITA` 721, `FRA` 691, `ENG` 535, `NED` 530, ...) |
| `ZZZ_<letter><NN>_<First>_<Last>` | 910 | named, no nation |
| `F<digits>` | 9,226 | numbered, no name. Probably generic faces |
| `M<digits>` | 3,000 | the same |
| `S<digits>` | 1,000 | the same |

One code is mistyped as `IRl`. The count of 113 includes it.

Pack 01's names say what the character is: `SUPPORTER` 80, `REFREE` 20,
`COMMISSIONER` 20, `STAFF` 20, `FLAGMAN` 16, `VISITOR` 12, `AGENT` 10,
`ANNOUNCER` 6, `MANAGER` 6, `REPORTER` 5, `CAMERAMAN` 5, `COACH` 4,
`SALESMAN` 3, `kihon` 4 ("basic"), `base` 1. The 3 other entries have no
`.svr` name in the model. The last entry (214) has no hair and a
two-texture `PVMH` (`camskin`, `came_hair`).

Hair-model names use the same style prefixes as `HAIR_PACK` and
`HAIR_PALETTE`. Across the 20,280 pack-00 heads with hair: `sho` 9,629,
`med` 4,002, `buz` 3,469, `ori` 1,018, `lon` 964, `bal` 335, `dre` 325,
`per` 308, `ski` 188, `moh` 42. Pack 01 also uses `wmn` (49). Readings
such as short, medium, buzz cut, long, dreadlocks and women's are guesses
from the names.

## Licensed kits (`PLPACK_*`)

`PLPACK_HOME.PAC` and `PLPACK_AWAY.PAC` each hold 116 entries of exactly
184,320 (`0x2d000`) bytes. Entry *i* is the same club in both files. Each
is a 7-block `PackData`:

| Block | Type | Contents |
|---|---|---|
| 0 | 0 | 32 bytes. `l_realize_licenceuniform` copies the first 0x12 into the kit struct. Always starts `ff ff`; the rest looks like colour/style indices. Unknown |
| 1 | 16 | `PVMH` `<nat>_<id>_X0_pnt` 128×128: outfield shorts |
| 2 | 16 | `PVMH` `<nat>_<id>_X0_sht` 256×256: outfield shirt |
| 3 | 16 | `PVMH` `<nat>_<id>_X0_sox` 128×64: outfield socks |
| 4–6 | 16 | the same three for the goalkeeper, `<nat>_<id>_X1_*` |

`X` is `0` in the home file and `1` in the away file, so home is `_00`/`_10`
and away is `_01`/`_11`. The realizer opens blocks 1–6 as six textures.

The 116 clubs are 36 Italian (`ita_228`–`ita_269`), 42 Spanish
(`esp_307`–`esp_352`) and 38 Dutch (`ned_270`–`ned_307`). The numbers look
like club ids. `esp_307` and `ned_307` both use 307, and one name is
upper case (`NED_280`). Neither has been checked against the club tables.

## Edit face pack

`EDITFACEPACK.BIN` is a KC@P pack with one uncompressed entry: a
32-block `PackData` with the resources for the face editor.

| Block | Type | Contents | Used by `l_realize_editfacepack` as |
|---|---|---|---|
| 0, 1 | 25 | `NSIF` models (0xac00, 0x7b50 bytes) | `convertNNDBinary` |
| 2 | 26 | a CSE project (0xdd1c bytes), see [`CSE_FORMAT.md`](CSE_FORMAT.md) | `cseProjectAbsolute` |
| 3 | 27 | `PVMH` textures (`tuku_tex01` ...) | opened as a texture |
| 4–31 | 28 | 28 `PVPL` palettes, 256 colours each | a loop of 28 (`0x11ce18`) collects their data pointers |

## Tool

`SRC/packdata.py` parses `PackData` in every KC@P pack it finds. Its
`info` check covers the layout and the packing rule. The same check also
passes on `GAME/CUTINPACK.BIN`, whose 277 entries are `PackData` with block
types 19–24. `FC_EURO_FACEPACK_00` is sampled (494 of 21,171 entries)
unless `--all` is given. The full scan used for the counts above took
several minutes.

```bash
python SRC/packdata.py info DAT                                 # all KC@P packs
python SRC/packdata.py info DAT/PLAYER/FC_EURO_FACEPACK_00.HED --all
python SRC/packdata.py list DAT/PLAYER/PLPACK_HOME.HED 0
python SRC/packdata.py extract DAT/PLAYER/FC_EURO_FACEPACK_01.HED 0 out/face
python SRC/svr.py info out/face                                 # the texture blocks
```

## Open questions

- The 0x18-byte header of face block 4, and whether its palette is skin.
- The 32-byte kit descriptor in `PLPACK` block 0 (only 0x12 bytes are used).
- What maps a club to its `PLPACK` index, and whether `<id>` is a club id.
- `COLOR_TBL.TBB`, `UNIFORM_LIST.TBB` and `UNIFORM_GK.TBB` record layouts
  (`UniformList_*` at `0x2d3078` is the place to start).
- Which models in `PLAYER_MODEL*.PAC` are which. Their names were cut to
  the extension, so the game must address them by index.
- Where `Param::PlPinfo+0x1ca` (the face index) is filled from.
