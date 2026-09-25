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
| (archives only) | `NSCA` + `NSMC` | camera and camera motion (not decoded) |
| (archives only) | `NSLI` | light (not decoded) |

There are 138 loose files in `DAT/` and 5,254 more uncompressed entries
inside `.PAC`/`.MRG`/`.HED` archives (stadiums, background props, player
parts, `PLAYERMOTION.PAC`, ...). `python SRC/ninja.py info DAT` checks all
5,392 against this document and reports no problems. `--prs` also expands
PRSH-compressed archive entries, which is much slower. That pass finds
3,370 more, and all 8,762 check with no problems.

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
lists hold the strips. Only the 35 common-vertex lists (below) use them.

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

Because the palette is world × inverse bind, **vertices are stored in
model space in the bind pose.** The exception is meshes on flag-`0x8`
nodes. On the disc these nodes always have flags `0xf` (no transform of
their own), so their vertices are in the frame of the nearest ancestor
without `0x8`. `ninja.py obj` uses this rule. It is **empirical**, and the
exported models (players, trophies, the clubhouse test scene) assemble
correctly with it.

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

The material pointer types are `0x400`, `0x800` and `0x1000`. The material
structs (colours as 0–255 floats, GS register values, texture layers) are
**not decoded yet**, so the exporter doesn't link textures. `NSTL` gives
the texture names.

## Vertex lists

The vertex-list pointer type decides the kind (confirmed at `0x19969c`).
If `type & 0xff0000` is set, it's a **common vertices** list, compiled at
load time by `nnCompileCommonVerticesObject*` (35 lists, e.g. `SHC3.SNO`
and `ENG_00_MICHAEL_OWEN.SNO`). Those aren't decoded. Otherwise the list
is `{u32 type, u32 qwords, ptr data, ...}`, and `data` is a ready-made
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
in the others. Where the rest of
the weight goes (probably the meshset's own matrix) is **unknown**.

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
| `0x10` | after the vertices | 2 u32 skin words per vertex (V2-32, **not decoded**) |
| `0x30` | after the vertices | 1 byte per vertex (S-8, **not decoded**) |

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
hide submotions occur, although `nnCalcNodeMotionCore` supports them.

## Still unknown

- Material structs and how they select textures from `NSTL`.
- The node sphere/box fields (`+0x70` plain, `+0x80` extended) and
  extended node `+0xC0`.
- Object type bits at `+0x44`, VU type bit `0x100`, the PX Plus skin
  words, and skinned weight remainders.
- Common-vertex lists (`nnCompileCommonVerticesObject`), used by the 35
  lists above and by the face models in `PLAYER/` (see
  [`PLAYER_DIR.md`](PLAYER_DIR.md)).
- Camera (`NSCA`/`NSMC`) and light (`NSLI`) chunks.
- Submotion interpolation types.

## Tools

```
python SRC/ninja.py info DAT                    # all 5,392 blobs, no problems
python SRC/ninja.py dump DAT/PLAYER/M_PLAYER.SNO
python SRC/ninja.py obj  DAT/GAME/BALL.SNJ out/ball.obj
```
