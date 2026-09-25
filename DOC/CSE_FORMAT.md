# `DAT/CSE`: 2D screens (`*.CSP`, `*.CSE`)

`DAT/CSE` (689 files, 80 MB) holds the game's 2D graphics: every menu screen,
window, icon set and pre-rendered room background. Nearly all of it is
`.CSP` packs. Each one holds a **CSE** layout (sprites, a node hierarchy and
keyframe animation) and the SVR textures the layout uses.

`python SRC/csp.py info DAT/CSE` parses all 493 CSP/CSE files, `tree`
dumps one layout, `extract` splits packs into `.cse` + `.svr`, and `png
... --crops` decodes the textures and cuts out each sprite.

## What's in the directory

| Files | Count | What |
|---|---|---|
| `*.CSP` | 490 | CSE + textures pack (below). `GP_PRACTICEICON.CSP` is 0 bytes |
| `*.SVR` | 184 | loose textures, mostly `GP_HLP_PTN_*` (help pages) and `WP_SP_TOP_TEX_00…31` (see [`SVR_FORMAT.md`](SVR_FORMAT.md)) |
| `*.CSE` | 3 | bare layouts: `2D001` (identical to the one inside `2D001.CSP`), `SLIDE_MAIN`, `TOURNAMENT` |
| `CAM_INT*.SND` | 3 | Ninja camera animations (`NSIF` + `NSCA`), loaded as `cam_int*` |
| `PITCH.SNA/.SNO` | 2 | Ninja object + node names (`NSNN`, `NSTL`) for the tactics-screen pitch |
| `PITCH.STA/.STO` | 2 | text source of the two above, from the SoftImage 3D 3.9.2 PS2 exporter |
| `INST_SVR.HED/.PAC` | 2 | BINPAC of `nst_tex_*.svr` (see [`PAC_FORMAT.md`](PAC_FORMAT.md)) |
| `ADIDAS_BALL.PRS` | 1 | PRS-compressed texture |
| `TACTICSTEXTURE.SVM` | 1 | PVMH texture set (tactics arrows) |
| `CVS/` | 3 | left over from development, see below |

### Name prefixes

| Prefix | Used for |
|---|---|
| `BG_xx_nn_00` | pre-rendered room backgrounds. Each pairs with a `.zbf` depth buffer (see [`ZBF_FORMAT.md`](ZBF_FORMAT.md)). The name pattern `BG_%s_%02d_00.csp` is in `DLL/SIMPRG.REL` |
| `WP_*` | full-screen menus: schedule, edit, mail, facilities, … |
| `SC_*` | one-off scenes: title, negotiation, trophies, tournaments, … |
| `GP_*` | shared parts: windows, cursors, icons, help pages |
| `GM_*` | overlays drawn during a match: loading, score banners, wipes |

The meanings are guessed from the file contents.

### Numbered copies

`SLES_541.51` has a table of about 300 lower-case `.csp` names. For 21 of
them the disc has no file of that exact name. Instead it has seven copies
with a digit 0–6 added to the name:

| Code asks for | Disc has |
|---|---|
| `sc_nego.csp` | `SC_NEGO0.CSP` … `SC_NEGO6.CSP` |
| `gm_short_02.csp` | `GM_SHORT_020.CSP` … `GM_SHORT_026.CSP` |
| `sc_sixnations_01_0.csp` | `SC_SIXNATIONS_01_00.CSP` … `_06.CSP` |

The digit is almost certainly added at runtime, probably one per
language. I haven't found where that happens, so I don't know which digit
is which language. `WP_KEYBOAD.CSP` is on the disc but not in the table.
The code only loads `wp_keyboad_JP` and `wp_keyboad_PAL`.

### The `CVS/` folder

`CVS/ROOT`, `CVS/REPOSITORY` and `CVS/ENTRIES` were copied onto the disc by
mistake. They name the developer's server and module
(`:pserver:kajimah@danae:/mnt/part_1/cvsroot`, `fc_euro/Data/Cse`) and
list a revision and commit time for every file in the folder, from
September 2004 (`2d001.*`) to January 2006. `ENTRIES` uses the original
lower/mixed-case file names.

## CSP pack

All values are little-endian.

```
u32 count
count × { u32 offset, u32 size, u32 type, u32 zero }
```

| type | content |
|---|---|
| 2 | CSE layout. Always exactly one, always the first entry |
| 1 | SVR texture (`GBIX` + `PVRT`) |

The runtime class is `FC_EURO_CSE_RESOURCE::CFcEuro_CseResource`
(`ConvertPackFile`, `CommonSetup`).

- The CSE's picture count always equals the number of SVRs, and SVR *i*
  is the texture for picture *i*. `csp.py extract` names each SVR after its
  picture.
- 5 packs have a CSE and no textures (`SC_EVENTTITLE`, `SC_MAPOINT`,
  `WP_FACILITIES_04`, `WP_SCHEDULE01B`, `WP_SP_MEMBERS`). Their faces are
  all untextured, or the code supplies textures itself.
- Only 6 of the 780 packed SVRs are byte-identical to a loose SVR.

## CSE layout

The runtime is Sega's `cse` 2D library, linked into the executable with
its symbols intact. The C layer is at `0x1ee7d0`–`0x1f4f00`
(`cseProjectDraw`, `cseSceneAnim`, …) and the C++ wrapper is `cse::CCse`.
Menu code uses it through `cse_utl`, `sort2d` and `WP::CCseLayout`.

**Every pointer in the file is an offset from the start of the CSE.**
`cseProjectAbsolute` (`0x1ef4e8`) walks the structure and adds the base
address to each one. It then writes `0x4241` ("AB") to `project+0x1E`,
which `cseProjectIsAbsolue` checks. The `*Absolute` / `*GetSize` /
`*Collect` functions at `0x1ee858`–`0x1f0688` are where the struct layouts
below come from. A null (0) offset means "none" everywhere.

```
Project (0x00)
├── PicList            textures + UV crops
├── Folder tree        (Folders → Scenes)
│   └── Scene
│       ├── FamilyList → Family[] → { Face[], Node tree }
│       └── AnimBank[] → Motion per node → Tracks → Keys
└── Folder table       flat list of every folder (at the end of the file)
```

### Project (0x40 bytes, at offset 0)

| Off | Type | |
|---|---|---|
| 0x00 | ptr | PicList (always `0x40`) |
| 0x04 | ptr | root Folder |
| 0x08 | u32 | number of folders |
| 0x0C | ptr | folder table: `u32[n]` offsets, depth-first order. It is the last thing in the file, so `ptr + 4n` = CSE size |
| 0x10 | u32 | background colour `0xRRGGBBAA`. `cseProjectDrawBg` ORs in alpha `0xFF` and fills the screen with it. `0x4444CC00` (editor blue) or `0x80808000` |
| 0x14 | u16 | screen width (640 or 512) |
| 0x16 | u16 | screen height (448) |
| 0x18 | u16 | 0 in every file |
| 0x1A | u16 | varies (15, 100, 120, …). Possibly a default frame count; unconfirmed |
| 0x1C | u16 | 60 in every file (frame rate?) |
| 0x1E | u16 | 0 in the file; `0x4241` once relocated |
| 0x20 | | zero padding |

### PicList

```
u32 count, ptr entries
entry (12 bytes): ptr name, s16 n_crops, s16 id, ptr crops
crop  (16 bytes): f32 u0, v0, u1, v1        // 0..1 texture space
```

Names are texture names without the extension (`wp_ynw_00`,
`tex00_slide`). `id` exists so faces can refer to a picture by ID instead
of by position (below).

### Folder (0x20 bytes)

| Off | |
|---|---|
| 0x00 | u32 scene count |
| 0x04 | ptr to `u32[count]` scene offsets |
| 0x08 | ptr next (sibling) folder |
| 0x0C | ptr first child folder |
| 0x10 | unused (0) |

The root folder of `SLIDE_MAIN.CSE` has garbage in `+0x00` but a null
scene pointer, so the count is never read.

### Scene (0x20 bytes)

| Off | |
|---|---|
| 0x00 | ptr FamilyList |
| 0x04 | u32 anim bank count |
| 0x08 | ptr to `u32[count]` AnimBank offsets |
| 0x0C– | not decoded: usually `1, 0, 0…`, sometimes `1, n, 0…` |

The game looks scenes up by folder index and scene index (`cse::ACCESSID`).
There are no scene names in the file.

### FamilyList / Family

```
FamilyList: u32 count, ptr families
Family (12 bytes): u32 n_faces, ptr faces, ptr root Node
```

A family is one sprite hierarchy. It has one Face per Node: `n_faces`
equals the number of nodes in the tree in all 5128 families.

### Face (0x28 bytes)

| Off | |
|---|---|
| 0x00 | s16 width, s16 height (pixels) |
| 0x04 | u32 flags (e.g. `0x80051000`) |
| 0x08 | 5 × u32 colour `0xRRGGBBAA`: face colour, then the four corners |
| 0x1C | s16 pattern count (0 = untextured, drawn by `cseCastFaceNonTexDrawCore`) |
| 0x1E | s16, not decoded (0, -1, 1, 2, …) |
| 0x20 | ptr to `pattern[count]` |
| 0x24 | 0 |

A pattern is `{u16 pic, s16 crop}`. If bit 15 of `pic` is set, the picture
is the one whose `id` equals the low 15 bits. Otherwise `pic` is an index
into the PicList (`cseCastFaceGetPatternData`, `0x1f07f8`). Most files use
the ID form. `crop = -1` shows nothing. A face with several patterns is a
flip-book: the animation's `pattern` track picks one.

### Node (0x40 bytes)

| Off | |
|---|---|
| 0x00 | f32 x, y: relative to the parent |
| 0x08 | f32 rotation (degrees) |
| 0x0C | f32 scale x, y |
| 0x14 | f32 pivot x, y: probably the point in the face that sits at (x, y). It is `(w/2, 0)` for top-centred panels, `(0, h)` for bottom-left |
| 0x1C | u32 (`cseCastNodeIsLayoutNull` tests it with `+0x28 & 0x100`) |
| 0x20 | s16 node id, s16 face index |
| 0x24 | u32 flags (`0x400000E7`, `0x40007FFF`, …) |
| 0x28 | u32 |
| 0x2C | u32, u32: usually 0; sometimes `0x1000, n` |
| 0x34 | ptr first child |
| 0x38 | ptr next sibling |
| 0x3C | unused |

One node in the whole disc points past its family's face list:
`WP_SCHEDULE01.CSP`, node 11 → face 12 of 12.

### AnimBank → Motion → Track → Key

```
AnimBank (0x10+): u32 0, u32 frames, u32 n_motions, ptr motions
                  motions = u32[n_motions], one per node in family order, 0 = not animated
Motion   (12):    u32 mask, u32 n_tracks, ptr tracks
Track    (12):    u16 kind, u16 first frame, u16 last frame, u16 n_keys, ptr keys
Key:              u8 size, u8 interp, u16 frame, value…   (size = whole key in bytes)
```

- `n_motions` equals the scene's node count in all 2246 banks.
- **mask** says which properties are animated. There is one track per set
  bit, in ascending bit order:

  | bit | property | track kind |
  |---|---|---|
  | 0, 1 | x, y | 0 (f32) |
  | 2 | rotation | 0 |
  | 3, 4 | scale x, y | 0 |
  | 5 | pattern (flip-book frame) | 2 (s32) |
  | 6 | face colour | 1 (`0xRRGGBBAA`); 25 tracks use `0x201` |
  | 7–10 | corner colours 0–3 | 1 |
  | 11, 14 | not decoded | 2 |

- **interp** 0 = step, 1 = linear (8-byte keys), 2 = curve: 16-byte keys
  with two extra f32s, presumably in/out tangents. On the disc, 17289 keys
  are linear, 936 step and 716 curve.

A typical bank from `SLIDE_MAIN.CSE`: bank 1 slides node 0 in from x = -274
to 320 over frames 0–15. Bank 2 slides it back out and fades the colour
from `ffffffff` to `ffffff00`.

## Not done yet

- Scene `+0x0C…`, Node `+0x1C/+0x24/+0x28/+0x2C`, Face `+0x04/+0x1E`
  are only described from the data.
- Project `+0x1A`, and how it relates to `AnimBank.frames`.
- Where the code adds the language digit to CSP names, and which BG
  palette (`.svp`) is picked for the 41 backgrounds without their own
  (see [`ZBF_FORMAT.md`](ZBF_FORMAT.md)).
