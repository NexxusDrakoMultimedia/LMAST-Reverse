# SVR / SVM / SVP textures (`*.SVR`, `*.SVM`, `*.SVP`)

These are the Sega **Ninja (PS2)** texture formats, the PS2 counterparts
of the Dreamcast PVR/PVM/PVP files:

| Ext   | Chunks          | Contents |
|-------|-----------------|----------|
| `.SVR` | `GBIX` + `PVRT` | one texture (407 files in `DAT/`) |
| `.SVM` | `PVMH` + n × `PVRT` | texture archive (22 loose, 256 more inside `.MRG`s) |
| `.SVP` | `PVPL`          | external palette for the `0x62`–`0x65` data formats |

All values are little-endian. `python SRC/svr.py info DAT` parses every
file, and `python SRC/svr.py png DAT out/` decodes all 474 loose textures
to PNG. The 801 textures inside `.MRG`s decode the same way after
`python SRC/pac.py extract` (see [`PAC_FORMAT.md`](PAC_FORMAT.md)).

## Confirmed from the game code

| Address    | Symbol | What it shows |
|------------|--------|---------------|
| `0x1340b0` | `graphics::CalculateTextureImageSize(const NVS_SVRHEADER*)` | size per `(data fmt << 8 \| pixel fmt)` code, e.g. `0x6809` → `w*h/2 + 0x40` |
| `0x1ad658` | `nvSetupSVRTexObj` | format → GS PSM: `0x62/0x66/0x68` → PSMT4 (`0x14`), `0x64/0x6a/0x6c` → PSMT8 (`0x13`), `0x60` + pixel fmt 9 → PSMCT32, 8 → PSMCT16; masks with `0xfe00`, so odd codes (mips) set up like even ones |
| `0x1adb10` | `nvPrepareSVRTexImagePacket` | CLUT upload, then each level: if `w >= minW && h >= minH` (per-PSM table at `0x527620`) the level is sent **as PSMCT32** of `w>>shW × h>>shH` (i.e. it is stored swizzled), else in its native PSM; levels advance by `(w*h*bpp/8 + 15) & ~15` |
| `0x167a00` | `nnuSvmGetSvrCount` | `PVMH+0x0A` = texture count |

Table at `0x527620` (8-byte entries indexed by PSM: `u8 bpp, u8 shW, u8 shH, pad, u16 minW, u16 minH`):

| PSM | bpp | upload as CT32 | swizzled when |
|-----|-----|----------------|---------------|
| PSMCT32 (0x00) | 32 | — | never (min 2048×2048) |
| PSMCT16 (0x02) | 16 | `w × h/2` | `w >= 64 && h >= 64` |
| PSMT8 (0x13)   | 8  | `w/2 × h/2` | `w >= 128 && h >= 64` |
| PSMT4 (0x14)   | 4  | `w/2 × h/4` | `w >= 128 && h >= 128` |

In other words: a level is swizzled exactly when it fills at least one GS
page of its own PSM.

## `GBIX` chunk (SVR only, optional)

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | char[4] | `GBIX` |
| `0x04` | u32 | chunk length after this field (always 8) |
| `0x08` | u32 | global index (texture ID) |
| `0x0C` | u32 | 0 |

## `PVRT` chunk

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | char[4] | `PVRT` |
| `0x04` | u32 | length of the rest of the chunk (from `+0x08`). In `.SVM`s it includes padding to 16 bytes |
| `0x08` | u8  | **pixel format** (colour format of direct pixels / palette) |
| `0x09` | u8  | **data format** |
| `0x0A` | u16 | mip level count − 1, read by `nvPrepareSVRTexImagePacket`; 0 in every file on this disc |
| `0x0C` | u16 | width |
| `0x0E` | u16 | height |
| `0x10` | —   | palette (if any), then image data |

The game reads `+0x08` as one u16, so format codes appear in the code as
`0x6809` = data format `0x68`, pixel format `0x09`.

### Pixel formats

| Code | GS PSM | Layout |
|------|--------|--------|
| `0x08` | PSMCT16 | u16 `ABBBBBGGGGGRRRRR` (A = bit 15; with A=0 the GS substitutes TEXA.TA0) |
| `0x09` | PSMCT32 | bytes `R G B A`, A in PS2 range: `0x80` = opaque |
| `0x0A` | PSMCT24 / 16S | handled by the code (`w*h*3`), not used on this disc |

### Data formats

Odd codes are the even format **plus mipmaps**.

| Code | Meaning | Palette | Pixel data |
|------|---------|---------|------------|
| `0x60` / `0x61` | direct colour | — | `w*h` × 2 or 4 bytes |
| `0x62` / `0x63` | 4 bpp, external palette (`.SVP`) | — | `w*h/2` |
| `0x64` / `0x65` | 8 bpp, external palette (`.SVP`) | — | `w*h` |
| `0x66` / `0x67` | 4 bpp | 16 × u16 | `w*h/2` |
| `0x68` / `0x69` | 4 bpp | 16 × u32 | `w*h/2` |
| `0x6A` / `0x6B` | 8 bpp | 256 × u16 | `w*h` |
| `0x6C` / `0x6D` | 8 bpp | 256 × u32 | `w*h` |

The palette's colour format is the pixel format byte. 4-bit pixels are
packed low nibble first.

**256-colour palettes are stored in GS CSM1 order**: within every block of
32 entries, entries 8–15 and 16–23 are swapped. Swap them back when
decoding (`i -> (i & ~0x18) | ((i & 8) << 1) | ((i & 0x10) >> 1)`).

### Mipmaps

Levels follow level 0 largest-first, each padded to 16 bytes. The level
count isn't stored (`+0x0A` is 0), and files stop at different sizes
(e.g. `ROSA_DRESS02.SVR` 256→32, `KIMONO_257.SVR` 256→8), so it has to be
inferred from the chunk length. 20 loose textures use mips (all in
`TEST3D/` apart from `GAME/EF012.SVM`), plus 119 inside `.MRG` packs.

### Swizzling

Levels that meet the page threshold above are stored as the PSMCT32 image
the game uploads: to decode, write the data linearly into a simulated GS
memory as PSMCT32 (buffer width = page-aligned upload width) and read it
back with the texture's own PSM (PSMT4/PSMT8/PSMCT16) address layout.
`SRC/svr.py` implements this with the PCSX2 GS block/column tables.
Smaller levels are plain linear pixels.

## `PVMH` archive header (`.SVM`)

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | char[4] | `PVMH` |
| `0x04` | u32 | header length after this field; the first `PVRT` is at `8 + this` |
| `0x08` | u16 | flags, always `0x010F` (low byte = entries carry name, format, dims, global index) |
| `0x0A` | u16 | texture count |
| `0x0C` | entry[count] | 38 bytes each, see below |

Entry:

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | u16 | index |
| `0x02` | char[28] | name (no extension) |
| `0x1E` | u16 | format, same value as `PVRT+0x08` |
| `0x20` | u8  | dimensions: low nibble `log2(w) - 2`, high nibble `log2(h) - 2` |
| `0x21` | u8  | 0 |
| `0x22` | u32 | global index |

The `PVRT` chunks follow in entry order with no `GBIX`, each 16-byte
aligned (zero padding between them).

## `PVPL` palette (`.SVP`)

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | char[4] | `PVPL` |
| `0x04` | u32 | length after this field |
| `0x08` | u16 | pixel format (`0x08` or `0x09`, as above) |
| `0x0A` | u16 | 0 |
| `0x0C` | u16 | 0 |
| `0x0E` | u16 | entry count (16 or 256) |
| `0x10` | —   | colours; 256-entry palettes are in CSM1 order |

Which `.SVP` goes with which external-palette texture is decided by the
code (e.g. `TEST3D/TST000_01FAC_{B,W,Y}0{0,1}.SVP` are skin-tone variants
of the `tst000_01fac` face in `TEST3D/*.SVM`; `BG/HUMAN_*_PALETTE.MRG`
bundle palettes for the `HUMAN_*` characters). Decode with
`python SRC/svr.py png <file> <out> --clut <file.SVP>`; without one, the
indices are rendered as greyscale.
