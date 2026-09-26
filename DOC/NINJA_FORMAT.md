# Ninja 3D models and motions (`*.SNJ`, `*.SNO`, `*.SNM`, `*.SNP`, `*.SNA`)

The game's models, skeletons and animations use Sega's **NN** ("Ninja
Next") binary chunk format for PS2. The library is linked into
`SLES_541.51` with its symbols (734 `nn*`/`nnu*` functions), so most of the
layout below is confirmed from the code that reads it.

| Ext | Chunks | Contents |
|-----|--------|----------|
| `.SNJ`, `.SNO` | `NSOB` (+`NSTL`) | model (`NNS_OBJECT`) and its texture file list |
| `.snq` (in archives) | `NSME` (+`NSTL`) | model part that hangs off an external skeleton |
| `.SNP` | `NSNT` | node tree: a skeleton object with no meshes |
| `.SNM` | `NSMO` | node motion (`NNS_MOTION`) |
| `.SNA` | `NSNN` | node name list |
| `.snd` (in archives) | `NSCA` + `NSMC` | camera and camera motion of a pre-rendered background |
| `.snl` (in archives) | `NSLI` | light |

There are 138 loose files in `DAT/`, 5,254 more uncompressed entries
inside `.PAC`/`.MRG`/`.HED` archives (stadiums, background props, player
parts, `PLAYERMOTION.PAC`, ...), and 3,430 blocks inside uncompressed KC@P
`etc::PackData` entries (`GAME/CUTINPACK`: 3,357 cut-in motions and 71
models; `EDITFACEPACK`: 2 heads). `python SRC/ninja.py info DAT` checks all
8,822 against this document and reports no problems. `--prs` also expands
PRSH-compressed entries, including the player face packs, which is much
slower. That pass checks 54,051 blobs with no problems, including 41,861
face and hair models from the face packs (21,388 of them heads).

All values are little-endian.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---------|--------|---------------|
| `0x10e338` | `DataUtility::resolveBinaryPointer` | NOF0: count at `+8`, entries from `+0x10`; each entry and pointer is relative to the data start |
| `0x10e570` | `DataUtility::convertNNDBinaryModelTexture` | NSIF `+8` chunk count, `+0xC` data offset, `+0x14` NOF0 offset; chunk walk `+4` size, `+8` main struct; `NSTL` → texture list; `NSOB`/`NSNT`/`NSME` → `NNS_OBJECT`; stops at `NEND` |
| `0x10e470` | `DataUtility::convertNNDBinaryCameraMotion` | `NSCA` → camera, `NSMC` → camera motion |
| `0x101ab8` | `CChunkDataHandle::load_complete` | same header and chunk walk for streamed files |
| `0x101cb0`, `0x1021e8`, `0x102238`, `0x102270` | `CModelHandle` / `CMotionHandle` / `CCameraMotionHandle` / `CMaterialMotionHandle::get_chunk_data` | which handle takes which chunk (`NSMA` = material motion, none on the disc) |
| `0x1741e8` | `nnGetNodeName` | node name list: `+0` type (0 binary search, 1 linear), `+4` count, `+8` → 8-byte `{id, name}` |
| `0x16c508`, `0x16c200` | `nnCalcMatrixPalette`, `nnCalcMatrixPaletteNode` | node list at object `+0x30`; node stride `0x90`; node fields and flags (below) |
| `0x199730` | `nnDrawObjectExt` | subobjects at object `+0x38`/`+0x3c`, stride `0x14`; subobject type `&7` pass, `&0x300` rigid/skinned |
| `0x199410` | (rigid subobject draw) | subobject `+4`/`+8` meshsets, stride `0x24`; meshset `+0x10`–`+0x20` indices; vertex-list pointer type `&0xff0000` picks common vertices over VU |
| `0x19de98` | `nnDrawRigidVerticesProcessVUExt` | VU vertex list: `+0` type (`&3`, `&8` choose the shader), `+4` qword count, `+8` data, sent with `PXPutRef` as a DMA ref |
| `0x19d978`, `0x143158`, `0x142f00` | `nnDrawObjectPXPlusLtdPS2`, `opt_nnDrawPriNodeObject` and its node helper | extended node: `+0xa4` materials, `+0xac` vertex lists, `+0xb8`/`+0xbc` subobjects (stride `0x20`: `+4` material, `+0xc`/`+0x10` meshsets); meshset stride `0x20`: `+0` flags, `+4` matrix, `+8` vertex list |
| `0x16cab8` | `nnCalcNodeMotionCore` | submotion `+0` type (`&0x7800` rotation, `&0x700` translation), `+4` interpolation, `+8` node, `+0xc`/`+0x10` frame range, `+0x14`/`+0x18` passed to `nnCalcMotionFrame`; motion `+0xc`/`+0x10` submotions |

## Container

```
NSIF  header (0x20 bytes)
NSxx  data chunks, 16-byte aligned
NOF0  pointer fix-ups
NFN0  source file name (optional)
NEND
```

Each chunk is `{char tag[4], u32 size}` followed by `size` bytes, and the
next chunk starts right after it.

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | `NSIF` |
| 0x04 | 4 | `0x18` (chunk size) |
| 0x08 | 4 | number of data chunks (not counting `NOF0`/`NFN0`/`NEND`) |
| 0x0C | 4 | data offset, always `0x20` |
| 0x10 | 4 | data size; data offset + size = `NOF0` offset |
| 0x14 | 4 | `NOF0` offset |
| 0x18 | 4 | `NOF0` chunk size including its 8-byte header |
| 0x1C | 4 | version, always 1 |

`+0x10`, `+0x18` and `+0x1C` are **empirical**: they aren't read by the
loaders, but they hold on every file.

Every data chunk has the offset of its main struct at `+8`. **Every offset
in the file is relative to the data start (`0x20`), not to the file.** That
includes the chunk's `+8`, all pointers, and the NOF0 entries.

`NOF0`: `+8` count, `+0xC` zero, then `count` × u32 offsets of the pointer
words. The loader adds the data address to each one. A tool can use the set
to tell pointers from plain values.

`NFN0` (**empirical**, 974 files): 8 zero bytes, then the NUL-padded original file
name (`M_player.sno`).

## `NNS_OBJECT` (`NSOB`, `NSNT`, `NSME`)

| Offset | Field |
|--------|-------|
| 0x00 | center x, y, z (f32) |
| 0x0C | radius (f32) |
| 0x10 | material count, `+0x14` → `{u32 type, ptr material}` list |
| 0x18 | vertex list count, `+0x1C` → `{u32 type, ptr vertex list}` list |
| 0x20 | primitive list count, `+0x24` → `{u32 type, ptr}` list |
| 0x28 | node count, `+0x2C` max depth, `+0x30` → node list |
| 0x34 | matrix palette size |
| 0x38 | subobject count, `+0x3C` → subobjects |
| 0x40 | texture count |
| 0x44 | object type (only in node-pointer objects, see below) |
| 0x48 | version (3), then bounding box x, y, z at `+0x4C` |

The plain object is 0x44 bytes. `+0x28`–`+0x3C` are confirmed; the others
follow the same NN names and are **empirical**.

For every VU object, all primitive-list pointers are null: the vertex
lists hold the strips. Only the common-vertex lists (below) use them.

### Nodes (`NNS_NODE`, 0x90 bytes)

| Offset | Field |
|--------|-------|
| 0x00 | flags |
| 0x04 | s16 matrix palette index (-1 = none) |
| 0x06 | s16 parent |
| 0x08 | s16 first child |
| 0x0A | s16 next sibling |
| 0x0C | translation x, y, z (f32) |
| 0x18 | rotation x, y, z (s32, 0x10000 = 360°) |
| 0x24 | scale x, y, z (f32) |
| 0x30 | 4×4 inverse bind matrix (f32, translation in the last row) |
| 0x70 | bounding sphere and user data (**not decoded**) |

Flags (confirmed at `0x16c274`–`0x16c41c`):

| Bit | Meaning |
|-----|---------|
| `0x1` | no translation |
| `0x2` | no rotation |
| `0x4` | no scale |
| `0x8` | palette entry is the world matrix itself; otherwise world × inverse bind (`+0x30`) |
| `0xf00` | rotation order: `0` XYZ, `0x100` XZY, `0x400` ZXY |
| `0x1000`, `0x2000` | copy the parent's 3×3 / transform the translation (not seen used) |
| `0x40000`, `0x80000`, `0x100000` | normalise matrix column 0 / 1 / 2 |

A meshset is drawn with its matrix palette entry (meshset `+0x14`, read
at `0x1994b4`), not with its node's. Because the palette is world × inverse
bind, **vertices are stored in model space in the bind pose.** The
exception is a palette entry owned by a flag-`0x8` node: it is the node's
world matrix, so the vertices are in that node's frame, which is its
parent's bind world plus its own translation. None of these nodes rotates
or scales on the disc; most have flags `0xf`. `ninja.py obj` uses this
rule. It is **empirical**, and the exported models (players, faces,
trophies, the clubhouse test scene) assemble correctly with it.

### Node-pointer objects (players)

In 275 objects, `+0x30` points to an array of **pointers** to extended
nodes (`NNS_NODEEX`) instead of an array of nodes. These are
`L/M/S_PLAYER.SNO`, `PLAYER/LMS_PLAYER.SNP` and the `NSME` player parts.
The object then carries the type/version/box fields at `+0x44`. The types
seen are `0x10080039`, `0x1008003b`, `0x100a0020`, `0x100c0029`,
`0x100c002a`, `0x100c0031`, `0x100c0039` and `0x100c003b`; their bits
aren't decoded. Such objects have no subobjects of their own and are drawn
node by node (`opt_nnDrawPriNodeObject`).

| Offset | Field |
|--------|-------|
| 0x00 | `0x80000001` plain (0x90 bytes) or `0x80000002` with meshes (0xD0 bytes) |
| 0x04 | node flags (as above) |
| 0x08 | s16 matrix palette index, `+0xA` s16 index of this node in the full skeleton |
| 0x0C | → parent, `+0x10` → first child, `+0x14` → next sibling (0 = none) |
| 0x18 | translation, `+0x24` rotation (s32), `+0x30` scale |
| 0x40 | 4×4 inverse bind matrix |
| 0x80 | bounding sphere / box (**not decoded**) |
| 0xA0 | material count, `+0xA4` → list (confirmed) |
| 0xA8 | vertex list count, `+0xAC` → list (confirmed) |
| 0xB0 | primitive list count, `+0xB4` → list |
| 0xB8 | subobject count, `+0xBC` → subobjects (confirmed) |
| 0xC0 | count and pointer, **unknown** |

`+0xA` is how an `NSME` part attaches: a hair or boot part has one node
whose `+0xA` is its bone in `LMS_PLAYER.SNP`. `NSME` parts with no nodes at
all (e.g. `BG/HUMAN_1000.MRG`'s `HUMAN_1000_l_arm_1.snq`) use meshset node
and matrix indices that refer to that external skeleton.

### Subobjects and meshsets

Plain objects: subobject (0x14 bytes) `{u32 type, u32 meshset count, ptr
meshsets, u32 texture count, ptr texture indices}`. Type `&7` is the draw
pass (1 opaque, 2 translucent, 4 punch-through by the NN names), and
`&0x300` is `0x100` rigid or `0x200` skinned. Seen: `0x101`, `0x102`,
`0x104`, `0x201`, `0x202`, `0x204`.

Meshset (0x24 bytes): `+0x00` center, `+0x0C` radius, `+0x10` node,
`+0x14` matrix palette index, `+0x18` material, `+0x1C` vertex list,
`+0x20` primitive list.

Extended nodes: subobject (0x20 bytes) `+0` type, `+4` material, `+0xC`
meshset count, `+0x10` → meshsets; meshset (0x20 bytes) `+0` flags
(`0x100` rigid, `0x200` skinned), `+4` matrix palette index, `+8` vertex
list.

### Materials

The material pointer type picks one of two layouts. Only the texture
references are decoded so far. The colours (0–255 floats in `0x400`/`0x800`,
0–1 floats in `0x1000`) and the GS register words are not.

| Type | Where | Texture layer | Texture index |
|------|-------|---------------|---------------|
| `0x400` | plain objects | inline at `+0x50` (0x70 bytes) | u16 at layer `+6` |
| `0x800` | plain objects, 2 textures | `+0x50`, second layer at `+0xC0` | u16 at layer `+6` |
| `0x1000` | PX Plus (players) | `+0x10` → layers of 0x40 bytes | u32 at layer `+4` |

Confirmed from the game code:

| Address | Symbol | What it shows |
|---------|--------|---------------|
| `0x18855c` | `nnPutMaterialCoreExt` | passes material `+0x50` as the texture layer |
| `0x1885a8`–`0x1886e0` | `nnPutMaterialCoreExt` | the second layer's fields are read 0x70 further on (`+0xb0`, `+0xb4`, `+0xc0`) |
| `0x187b24` | `nnSetMaterialSingleTextureExtPS2` | texture index = u16 at layer `+6`, used to pick the entry in the loaded texture list |
| `0x143418` | helper of `opt_nnPutMaterialCorePXPlusLtd` | PX Plus: texture index = u32 at `+4` of each 0x40-byte layer at material `+0x10` |

The index selects an entry of the object's `NSTL`. **Empirical**, across all
5,392 blobs:

- Every index is below the `NSTL` count. `ninja.py info` checks this.
- In `0x400`/`0x800` materials, a layer whose first word (flags) is 0 has no
  texture (1,780 materials).
- Layer flags `& 0x7f00` are the mapping mode (0x18850c: `0x400` and
  `0x800` switch on texture matrices). The trophies' metal uses one of
  these, a reflection map that doesn't use the vertex UVs.

Models without `NSTL` (4,734 of the `0x400`/`0x800` materials, e.g. the
stadiums, the balls and the `BG/HUMAN_HEAD_MODEL` heads) get their textures
from outside the model file.

The face packs keep each head's and hair's texture as a sibling
`etc::PackData` block, an SVM whose texture name is the `NSTL` name without
`.svr` (`NIR_00_Maik_TAYLOR`, `buz004`). `ninja.py obj` finds them there.
The hair textures are grey patterns; the game probably tints them with the
player's hair colour (**not confirmed**; see `COLOR_TBL` in
[`PLAYER_DIR.md`](PLAYER_DIR.md)).
The player models name their kit, skin and number textures (`skn_00.svr`,
`org_000_sht.svr`, ...), but those files aren't on the disc as-is: the
game builds them from the `PLAYER/` packs.

UVs use the GS convention (V runs downwards). `ninja.py obj` writes
`1 - v`, and textured test renders (`CAMERON.SNO`, the trophies) map
correctly.

## Vertex lists

The vertex-list pointer type decides the kind (confirmed at `0x19969c`).
If `type & 0xff0000` is set (`0x10000`), it's a **common vertices** list,
described below. Otherwise the list is `{u32 type, u32 qwords, ptr data, ...}`, and `data` is a ready-made
**VIF stream** that `PXPutRef` sends to VU1 unchanged. The stream uses only
`STCYCL`, `STMASK`, `STROW`, `UNPACK`, `MSCNT` and `NOP`, and it always
ends exactly at `qwords`.

### VU lists (type < `0x200`)

The list is 0x14 bytes. `+0xC`/`+0x10` are the count and pointer of the
bone palette that skinned types use. Batches alternate between VU addresses
0 and 0x200. Each batch starts with `UNPACK V4-32` of two qwords: `{u32
vertex count, 0, 0, u32 count × 208}`, then a GIF tag. The GIF tag's NLOOP
equals the vertex count, PRIM is 4 (triangle strip) with Gouraud shading
and texturing, and the registers are ST, RGBAQ, XYZ2. All of this is
**empirical** and holds for all 120,319 VU batches.

Rigid types unpack the attributes separately at stride 3 (`STCYCL 3,1`):

| Type | +2 | +3 | +4 |
|------|----|----|----|
| `0x5` | position V3-32 | normal V3-32 | UV V2-32 |
| `0x6` | position V3-32 | colour V4-8 | UV V2-32 |
| `0x9` | position V3-32 | normal V3-16 | UV V2-16 |
| `0xa` | position V3-32 | colour V4-8 | UV V2-16 |

So bit 0 = normals, bit 1 = colours, bit 3 = 16-bit normals and UVs. The
16-bit values are 1/4096 fixed point: normals come out at unit length.
Types `0x105`, `0x106` and `0x109` have the same layouts as their low byte;
what `0x100` means is **unknown**.

Skinned types upload the whole batch as one `V4-32` block:

| Type | qwords/vertex | Layout |
|------|---------------|--------|
| `0x11`, `0x111` | 3 | `[pos, w0] [normal, 1] [u, v, i0, 0]` |
| `0x21` | 4 | `[pos, w0] [normal, 1] [u, v, i0, i1] [w1, 0, 0, 0]` |
| `0x31`, `0x32`, `0x131` | 3 | `[pos, i0] [normal/colour, 1] [u, v, 1.0, 1.0]` |

`i` are u32 bone slots × 4 (a VU matrix is 4 qwords), always below the
list's palette count (all 247,585 skinned vertices). `w` are floats. The
two weights of `0x21` add up to 1.0 in 2,858 of 6,057 vertices and to less
in the others. Where the rest of the weight goes is **unknown**: the CPU
uploads only the list's bones (`nnPutBoneMatrix`, `0x19e0a0`, an `UNPACK`
of 4 qwords per bone to VU `0x180`), so the VU program does the blend, and
the meshset's own matrix is -1. Treating the weights as if they were scaled
up to 1 animates the test models cleanly; sending the rest to the bone's
parent or to the root visibly doesn't, so `ninja.py gltf` normalises them.

### PX Plus lists (type has bits `0x60000`)

These are used by the player models (`L/M/S_PLAYER`, `NSME` parts). The
list is 0x14 bytes, like the VU lists. Each batch is `STCYCL 4,1`, then
`UNPACK V4-32` at VU 0 of `{u32 vertex count, 4, u32 4 × count + 4, 0}`.
There is no GIF tag. The per-vertex attributes follow at stride 4 from VU 4.

| Type bit | VU | Attribute |
|----------|----|-----------|
| `0x60000` | +4 | position V3-32 (always) |
| `0x80000` | +5 | normal V3-16 (/4096) |
| `0x800000` | +6 | UV V2-16 (/4096) |
| `0x1000100` | +6 | UV as V4-16 instead (second pair **unknown**) |
| `0x10` | +4 + 4 × count | 2 u32 skin words per vertex (V2-32): `weight << 15 \| slot × 4`, 1.0 = `1 << 27`; unused word 0 |
| `0x30` | +4 + 4 × count | 1 byte per vertex (S-8): `slot × 4`, weight 1 |

The skin data is **empirical**, and `ninja.py info` checks it on every
list: it sits right after the vertices, the weights of a vertex add up to
1 (within 1/256), and every slot is below the list's bone palette count.
Slots index the bone palette at list `+0xc`/`+0x10`, as for VU lists.

The `4` in the header (all 5,646 batches) matches the GS triangle-strip
PRIM, so the exporter treats each batch as one strip. That is **empirical**.

### Strips and winding

Every batch is one triangle strip: triangle `i` uses vertices `i`, `i+1`,
`i+2`. **Empirical**, from all batches that carry normals:

| Triangle | Faces along the stored normals | Faces against them |
|----------|--------------------------------|--------------------|
| even `i` | 256,035 | 1,717 |
| odd `i`  | 1,441 | 229,400 |

So even triangles are counter-clockwise when seen from the front, and odd
ones need two corners swapped, as usual for strips. About 99.4% of
triangles agree. The rest are probably thin or folded spots where the
three vertex normals don't settle the direction.

88,138 triangles repeat a vertex position. These zero-area triangles join
separate strips inside one batch and draw nothing. They still count for
the even/odd parity. `ninja.py obj` drops them.

### Common-vertex lists (pointer type `0x10000`)

Used by the player face models and the other heads (`BG/HUMAN_HEAD_MODEL`,
`PLAYER/PLAYER_MODEL.PAC`, the face packs), plus two test files. The game
converts them at load time (`nnCompileCommonVerticesObject*`); the file
holds plain arrays and index lists. Unlike the VU lists, these meshsets use
their primitive list (meshset `+0x20`).

The vertex list is up to four 16-byte **streams**, `{u32 format, u32
count, u32 element size, ptr data}`, ended by a zero format.
`nnEstVtxTypeCommonVertices` (`0x191e38`) reads the format words at
`+0x0`, `+0x10`, `+0x20`, `+0x30` and turns the bits into a PX Plus vertex
type. The streams have **their own counts**, so a corner can reuse a
position with a different UV, as in an OBJ `v/vt/vn` face.

| Format | Size | Element (**empirical**) |
|--------|------|-------------------------|
| `0x1` | 12 | position x, y, z (f32) |
| `0x401` | 24 | position, then u32 bone 0, u32 bone 1, f32 weight of bone 0 |
| `0x1001` | 44 | position, then 4 × {u32 bone, f32 weight} |
| `0x2` | 12 | normal (f32) |
| `0x8` | 16 | colour, 4 × f32 (only `SHC3.SNO`) |
| `0x20` | 8 | UV (f32) |

Bones are matrix palette indices, always below the object's palette size.
In `0x401` the second bone gets `1 - weight` (the weight is between 0 and 1
in all 21,872 checked vertices).

The primitive list pointer has type `0x20000`, and the list is:

| Offset | Field |
|--------|-------|
| 0x00 | mask of the indexed streams: `7` (3 streams) or `3` (2) |
| 0x04 | indices per corner, equal to the vertex list's stream count |
| 0x08 | strip count |
| 0x0C | → u16 strip lengths |
| 0x10 | → u16 indices, one per stream per corner, stream order |

The lengths and indices sit just before the primitive list struct, and the
index array ends exactly at it (padded to 4). This and every index being
below its stream's count hold for all 5,625 primitive lists found. Each
strip is a triangle strip, wound like the VU strips.

## Texture file list (`NSTL`)

`{u32 count, ptr entries}`. Each entry is 0x14 bytes: `+0` type (0), `+4` →
NUL-terminated file name (`ms_hed.svr`), `+8` u32 filter (`0x10001` in 873
entries, `0x10004` in 350, `0x10005` in 44), then 8 bytes that are zero in
all 1,267 entries. The textures are
the `.SVR` files described in [`SVR_FORMAT.md`](SVR_FORMAT.md). There are
also 104 `NSTL`-only files in archives.

## Node names (`NSNN`)

Layout confirmed by `nnGetNodeName`: `{u32 type, u32 count, ptr entries}`,
with 8-byte entries `{u32 node id, ptr name}`. Type 0 (sorted by id, binary
search) in 173 files and type 1 (linear) in 5. For example, `CSE/PITCH.SNA` names `away_l`, `away_r`, `home_l`, ...

## Motions (`NSMO`)

`NNS_MOTION` (0x18 bytes):

| Offset | Field |
|--------|-------|
| 0x00 | type: `0x10010001` (758), `0x10040001` (130), `0x10080001` (2), `0x40001` (1) |
| 0x04 | start frame (f32) |
| 0x08 | end frame (f32) |
| 0x0C | submotion count (confirmed) |
| 0x10 | → submotions (confirmed) |
| 0x14 | frames per second (f32; 30 or 60, 0 in the old `0x40001` file) |

Submotion (0x28 bytes):

| Offset | Field |
|--------|-------|
| 0x00 | type (confirmed: `&0x700` translation, `&0x7800` rotation) |
| 0x04 | interpolation: `0x20002`, `0x20004`, `0x20200` (meaning **not decoded**) |
| 0x08 | node index (confirmed) |
| 0x0C | start frame, `+0x10` end frame (f32, confirmed) |
| 0x14 | loop start, `+0x18` loop end (f32; passed to `nnCalcMotionFrame`) |
| 0x1C | key count |
| 0x20 | key size |
| 0x24 | → keys |

The key formats (**empirical**, from all 891 motions):

| Type | Key size | Key |
|------|----------|-----|
| `0x101` / `0x201` / `0x401` | 8 | translation X / Y / Z: f32 frame, f32 value |
| `0x812` / `0x1012` / `0x2012` | 4 | rotation X / Y / Z: s16 frame, s16 angle |
| `0x3812` | 8 | rotation XYZ: s16 frame, 3 × s16 angle |

Angles are 16-bit NN angles (0x10000 = 360°). No scale, user-data or
hide submotions occur, although `nnCalcNodeMotionCore` supports them. Key
frames always increase (checked by `info`). The submotion type's low
nibble gives the key encoding: `1` f32 frame and f32 values, `2` s16 frame
and s16 values.

A submotion replaces its components of the node's rest translation or
rotation. A node's rotation is built in the order its flags name, first
axis first, with row vectors and local = scale × rotation × translation.
That makes the glTF rotation `qz·qy·qx` for XYZ order (`qy·qz·qx` for
XZY, `qy·qx·qz` for ZXY). **Empirical**: rebuilding every bone of
`TEST3D/01.SNO` from its T/R/S chain reproduces its inverse bind matrices
to within 0.05. Only XYZ and XZY occur on the disc.

The rest T/R/S of an animated model is often a pose, not the bind pose the
inverse matrices were built from (the Cameron test model stands with her
hands together; players stand with their hands on their hips). A renderer
must use both, as glTF does.

## Cameras (`NSCA` + `NSMC`)

Each pre-rendered background (`BG/BG_*.MRG`, 171 files) has one `.snd`
entry holding the camera it was rendered with; `PRELOAD/TACTICSPITCH.PAC`
has 3 more. That is the camera to use with its
[`.zbf` depth buffer](ZBF_FORMAT.md) and background image.

`NSCA` main struct: `{u32 type, ptr camera}` with type `0xff` (all 174).
The camera (type 0 in all 174):

| Offset | Field |
|--------|-------|
| 0x00 | camera type (0) |
| 0x04 | vertical field of view, s32 NN angle (0x10000 = 360°) |
| 0x08 | aspect ratio (f32, 1.3333) |
| 0x0C | near clip, `+0x10` far clip (f32) |
| 0x14 | position x, y, z (f32) |
| 0x20 | target x, y, z (f32) |

`NSMC` is an `NNS_MOTION` (type `0x10010002` or `0x10040002`) whose
submotions animate the camera. Confirmed from `nnCalcCameraMotionCore`
(`0x175c98`), which picks the evaluator by type mask and writes the results
to the fields above:

| Submotion type | Mask | Evaluator | Animates | Key |
|----------------|------|-----------|----------|-----|
| `0x101`/`0x201`/`0x401` | `0x700` | `nnCalcMotionTranslate` | position X/Y/Z | f32 frame, f32 |
| `0x40001`/`0x80001`/`0x100001` | `0x1c0000` | `nnCalcMotionCameraXYZ` | target X/Y/Z | f32 frame, f32 |
| `0x200012` | `0x200000` | `nnCalcMotionCameraAngle` | roll | s16 frame, s16 angle |
| `0x10000012` | `0x10000000` | `nnCalcMotionCameraAngle` | field of view | s16 frame, s16 angle |

Every camera on the disc has exactly these eight submotions. Most have one
key each, so the camera doesn't move.

## Lights (`NSLI`)

Two files (`BG/BG_OF_00.MRG`, `BG/BG_OF_03.MRG`). `NSLI` main struct:
`{u32 type, ptr light}`, passed to `nnSetLight(index, light, type)` by
`graphics::CLight::SetPointer` (`0x3414f8`). Both lights are type `0x10`,
whose branch in `nnSetLight` (`0x17b330`) reads:

| Offset | Field | Set with |
|--------|-------|----------|
| 0x04 | colour R, G, B (f32) | `nnSetLightColor` |
| 0x10 | alpha | `nnSetLightAlpha` |
| 0x14 | intensity | `nnSetLightIntensity` |
| 0x18 | position x, y, z | `nnSetLightPosition` |
| 0x24 | target x, y, z | `nnSetLightTarget` |
| 0x30 | range (2 × f32) | `nnSetLightRange` |
| 0x38 | falloff (2 × f32) | `nnSetLightFallOff` |

## Still unknown

- Material colours, GS register words and the layer flag bits.
- Where the textures of models without `NSTL` come from.
- The node sphere/box fields (`+0x70` plain, `+0x80` extended) and
  extended node `+0xC0`.
- Object type bits at `+0x44` and VU type bit `0x100`.
- How the VU program fills the remaining weight of skinned VU vertices.
- Submotion interpolation types (`0x20002`, `0x20004`, `0x20200`);
  `ninja.py gltf` bakes every track linearly, one sample per frame.
- Node flags `0x1000`/`0x2000` (97 nodes), which glTF can't express.

## Tools

```
python SRC/ninja.py info DAT                    # 8,822 blobs, no problems
python SRC/ninja.py info DAT --prs              # also the PRS-compressed ones
python SRC/ninja.py dump DAT/PLAYER/M_PLAYER.SNO
python SRC/ninja.py obj  DAT/TEST3D/CAMERON.SNO out/cameron.obj   # + .mtl and PNG textures
python SRC/ninja.py obj  "DAT/PLAYER/FC_EURO_FACEPACK_00.HED#0.0" out/face.obj   # a player's head
python SRC/ninja.py gltf out/player.gltf DAT/PLAYER/M_PLAYER.SNO "DAT/GAME/PLAYERMOTION.PAC#68:snm"
python SRC/ninja.py gltf out/human.gltf DAT/BG/HUMAN_1000.MRG       # a whole background human
```

`gltf` writes a skinned, animated glTF 2.0 (`.gltf`, `.bin` and PNG
textures) that Blender and other tools open. Its inputs are files, labels
or whole archives, sorted by content: the first model with nodes is the
skeleton; other models are parts drawn with it (node-less `NSME` parts use
the skeleton's matrix numbers, player parts attach through their node's
skeleton index at `+0xa`); an `NSTL`-only file names the parts' textures;
each motion becomes an animation. Every node is a joint; rigid meshes get
weight 1 on the node that owns their matrix. A part that brings its own
skeleton without skeleton indices (a face-pack head) is skipped and
reported instead of being bound to the wrong bones.

`obj` takes a file or any label that `info` prints for an archive entry:
`ARCHIVE#entry:name` (BINPAC) or `ARCHIVE#entry.block` (a block inside a
KC@P pack entry). Textures come from, in order: sibling blocks of the same
pack entry, same-named entries of the same archive, or files next to a
loose model.
