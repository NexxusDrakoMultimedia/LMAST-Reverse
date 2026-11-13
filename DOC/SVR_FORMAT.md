<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# SVR / SVM / SVP textures (`*.SVR`, `*.SVM`, `*.SVP`)

These are the Sega **Ninja (PS2)** texture formats, the PS2 counterparts
of the Dreamcast PVR/PVM/PVP files:

| Ext   | Chunks          | Contents |
|---|---|---|
| `.SVR` | `GBIX` + `PVRT` | one texture (407 files in `DAT/`) |
| `.SVM` | `PVMH` + n × `PVRT` | texture archive (22 loose, 256 more inside `.MRG`s) |
| `.SVP` | `PVPL`          | external palette for the `0x62`–`0x65` data formats (14 loose files, more inside archives) |

`SRC/svr.py` reads and writes all three. All values are little-endian.
`python SRC/svr.py info DAT` parses every file, and `python SRC/svr.py
png DAT out/` decodes all 475 loose textures to PNG. Textures inside
archives (the 803 in `.MRG`s, and the `.PAC` packs of `STADIUM/`,
`PLAYER/`, `NEWS/`, `EMBLEM/` and `0SYSTEM/`) decode the same way after
`python SRC/pac.py extract` (see [`PAC_FORMAT.md`](PAC_FORMAT.md));
`csp.py png` handles the ones in CSP packs
([`CSE_FORMAT.md`](CSE_FORMAT.md)).

## Confirmed from the game code

| Address    | Symbol | What it shows |
|---|---|---|
| `0x1340b0` | `graphics::CalculateTextureImageSize(const NVS_SVRHEADER*)` | size per `(data fmt << 8 \| pixel fmt)` code, e.g. `0x6809` → `w*h/2 + 0x40` |
| `0x1ad658` | `nvSetupSVRTexObj` | format → GS PSM: `0x62/0x66/0x68` → PSMT4 (`0x14`), `0x64/0x6a/0x6c` → PSMT8 (`0x13`), `0x60` + pixel fmt 9 → PSMCT32, 8 → PSMCT16; masks with `0xfe00`, so odd codes (mips) set up like even ones |
| `0x1adb10` | `nvPrepareSVRTexImagePacket` | CLUT upload, then each level: if `w >= minW && h >= minH` (per-PSM table at `0x527620`) the level is sent **as PSMCT32** of `w>>shW × h>>shH` (i.e. it is stored swizzled), else in its native PSM; levels advance by `(w*h*bpp/8 + 15) & ~15` |
| `0x167a00` | `nnuSvmGetSvrCount` | `PVMH+0x0A` = texture count |

Table at `0x527620` (8-byte entries indexed by PSM: `u8 bpp, u8 shW, u8
shH, pad, u16 minW, u16 minH`):

| PSM | bpp | upload as CT32 | swizzled when |
|---|---|---|---|
| PSMCT32 (0x00) | 32 | – | never (min 2048×2048) |
| PSMCT16 (0x02) | 16 | `w × h/2` | `w >= 64 && h >= 64` |
| PSMT8 (0x13)   | 8  | `w/2 × h/2` | `w >= 128 && h >= 64` |
| PSMT4 (0x14)   | 4  | `w/2 × h/4` | `w >= 128 && h >= 128` |

In other words: a level is swizzled exactly when it fills at least one GS
page of its own PSM.

## `GBIX` chunk (SVR only, optional)

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | char[4] | `GBIX` |
| `0x04` | u32 | chunk length after this field (always 8) |
| `0x08` | u32 | global index (texture ID) |
| `0x0C` | u32 | 0 |

## `PVRT` chunk

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | char[4] | `PVRT` |
| `0x04` | u32 | length of the rest of the chunk (from `+0x08`). In `.SVM`s it includes padding to 16 bytes |
| `0x08` | u8  | **pixel format** (colour format of direct pixels / palette) |
| `0x09` | u8  | **data format** |
| `0x0A` | u16 | mip level count − 1, read by `nvPrepareSVRTexImagePacket`; 0 in every file on this disc |
| `0x0C` | u16 | width |
| `0x0E` | u16 | height |
| `0x10` | – | palette (if any), then image data |

The game reads `+0x08` as one u16, so format codes appear in the code as
`0x6809` = data format `0x68`, pixel format `0x09`.

### Pixel formats

| Code | GS PSM | Layout |
|---|---|---|
| `0x08` | PSMCT16 | u16 `ABBBBBGGGGGRRRRR` (A = bit 15; with A=0 the GS substitutes TEXA.TA0) |
| `0x09` | PSMCT32 | bytes `R G B A`, A in PS2 range: `0x80` = opaque |
| `0x0A` | PSMCT24 / 16S | handled by the code (`w*h*3`), not used on this disc |

### Data formats

Odd codes are the even format **plus mipmaps**.

| Code | Meaning | Palette | Pixel data |
|---|---|---|---|
| `0x60` / `0x61` | direct colour | – | `w*h` × 2 or 4 bytes |
| `0x62` / `0x63` | 4 bpp, external palette (`.SVP`) | – | `w*h/2` |
| `0x64` / `0x65` | 8 bpp, external palette (`.SVP`) | – | `w*h` |
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
|---|---|---|
| `0x00` | char[4] | `PVMH` |
| `0x04` | u32 | header length after this field; the first `PVRT` is at `8 + this` |
| `0x08` | u16 | flags, always `0x010F` (low byte = entries carry name, format, dims, global index) |
| `0x0A` | u16 | texture count |
| `0x0C` | entry[count] | 38 bytes each, see below |

Entry:

| Offset | Type | Meaning |
|---|---|---|
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
|---|---|---|
| `0x00` | char[4] | `PVPL` |
| `0x04` | u32 | length after this field |
| `0x08` | u16 | pixel format (`0x08` or `0x09`, as above) |
| `0x0A` | u16 | 0 |
| `0x0C` | u16 | 0 |
| `0x0E` | u16 | entry count (16 or 256) |
| `0x10` | – | colours; 256-entry palettes are in CSM1 order |

Which `.SVP` goes with which external-palette texture is decided by the
code (e.g. `TEST3D/TST000_01FAC_{B,W,Y}0{0,1}.SVP` are skin-tone variants
of the `tst000_01fac` face in `TEST3D/*.SVM`; `BG/HUMAN_*_PALETTE.MRG`
bundle palettes for the `HUMAN_*` characters). Decode with
`python SRC/svr.py png <file> <out> --clut <file.SVP>`; without one, the
indices are rendered as greyscale.

## Writing

`SRC/svr.py` writes the three formats. The write goes through the same
steps as the read, backwards: a picture becomes palette indices (or
CT16/CT32 colours), the levels are halved for the mip chain, a level that
fills a GS page is swizzled (`swizzle`, the inverse of `unswizzle`), each
level is padded to 16 bytes, and the chunk gets its length field.

```bash
python SRC/svr.py roundtrip DAT
python SRC/svr.py replace DAT/GAME/BG_RAIN.SVR out.SVR picture.png
```

`replace` takes a loose `.SVR` or `.SVM`, with `--texture <name|index>`
for an SVM, `--clut file.SVP` for an external palette and `--palette
keep` to match the texture's old palette instead of building a new one.
A texture inside a pack is extracted, replaced and put back with
`pac.py` (below).

**Rebuilding is exact (empirical).** `roundtrip` takes every texture
file apart into palette, linear levels, each level's padding and the
chunk's tail, puts it together again, and compares the bytes. Over
`DAT/` that is 18,285 texture files (11,133 distinct; the language copies
repeat) with 9,846 textures and 1,826 palettes: loose files, `.MRG`s,
`.PAC`s with their PRSH entries, CSP packs including those inside the
`PRELOAD` packs, the ACROBATA pack, and the KC@P `PackData` packs
(kits, cut-ins, edit faces, event faces). All come back identical. With
`--all`, which adds the 1.1 GB face pack (`FC_EURO_FACEPACK_00`), the
`PLAYER` folder is 46,959 files and 25,431 distinct textures, also
identical. Each texture's own picture is then put back through the
picture path (`body_from_pixels`) and must decode to the same picture:
0 changes. The swizzle was also checked against the reader: the forward
swizzle undoes `unswizzle` on all 6,055 swizzled levels, and the
rewritten `unswizzle` matches the original on 373 levels of the loose
files (4, 8 and 16 bpp, 19 shapes).

What a rebuild has to keep, found by running the check over the disc:

| Fact | Count | Handled by |
|---|---|---|
| An SVR's `GBIX` chunk is 16 bytes (`8`, the id, `0`), and the file ends where the `PVRT` chunk ends | 7,439 of 7,439 | `Texture.head`, `trailer` |
| In an SVM every chunk starts where the last ended; all padding is inside the length field | 3,303 of 3,303 | `Texture.lead`, `Archive.tail` |
| The `PVMH` header padding is not a function of the count (`align16(12 + 38n)` in 2,286 archives, 16 bytes more in 158) | 2,444 archives | `Archive.head`, kept as read |
| An SVM entry's global index is stored per entry (0 in 2,959 of 3,303, a few repeated) | 3,303 | `Texture.entry`, kept as read |
| 87 non-mip textures in SVMs have 16 zero bytes after level 0, inside the length field | 87 | `tail` |
| Level padding is not always zero: the last level of `GAME/EF012.SVM` (4x4, 4 bpp, 8 bytes in a 16-byte slot) has 8 non-zero bytes after it | 1 | `pads` |
| Mip chains are cut short (2 to 6 levels, never down to 1 pixel); the count is only recoverable from the chunk length | 265 of 265 | `level_sizes` |
| A mip chain mixes swizzled upper levels and linear lower ones; each level is decided by its own size | 118 textures | `is_swizzled` per level |
| Two `.SVP`s have `99` in the word at `+0x0A` and 128 have 32 entries | 130 | `Palette.fields` |
| No CT32 alpha is above `0x80`, so the decode/encode of alpha is exact here | 8,123 | `encode_colors` |

**The picture path (`replace`).** The picture must be the texture's own
size; the format, the length of the mip chain and the padding stay, so
the file keeps its length and no pack has to move. Mip levels are made by
averaging 2x2 blocks. For a direct-colour texture the picture is
converted to CT16 (5 bits a channel and a 1-bit alpha) or CT32 (alpha
0 to `0x80`). A 4 or 8 bpp texture with its own palette gets a new
palette built from the picture: every colour of the picture when there
are no more than the palette holds (a transparent pixel keeps its RGB,
because the GS blends it into its neighbours when it filters), else an
octree quantisation (needs pillow) with one transparent entry kept apart,
so transparency is not blended away. `--palette keep`, and every texture
whose palette is a `.SVP`, match each pixel to the closest colour of the
existing palette instead (`colour_distance`: the colour difference counts
only where both colours are visible, an alpha difference counts as much as
the largest colour difference). **Tested through the command line** over
one real texture of each combination of pixel format, data format and
swizzling on the disc (17 combinations, 52 runs; mirrored and red/blue
swapped pictures): the file length, header fields and other textures stay
the same, a picture that fits its palette comes back exactly, and one
that doesn't gets the nearest palette colour at every pixel. Gradients
over three palette sizes kept their transparent corner. **Tested in
PCSX2** (Nexxus's report, 2026-11-07, `LMAST-test-realism.iso`): textures
written this way into the crest, mini-crest and sponsor packs show in the
game ([`TEXMAP.md`](TEXMAP.md#putting-the-pack-on-the-disc-apply)).

**Containers.** A texture file inside a pack is replaced by putting the
new bytes in the pack, which the pack tools do:

| Holder | Textures | Can the pack be put back? |
|---|---|---|
| `.MRG`, `.PAC` (BINPAC): `0SYSTEM`, `EMBLEM`, `NEWS`, `STADIUM`, `PLAYER`, `BG`, `TEST3D`, `CSE/INST_SVR` | most of the disc's | yes, `pac.py replace` (rebuilt packs are identical); a changed-size entry moves the later ones, and the `.HED` copies and the `PRELOAD` copies need the same change ([`PAC_FORMAT.md`](PAC_FORMAT.md)). PRSH entries are recompressed by `pac.py`'s writer, which is not byte-identical to Sega's packer |
| `*.CSP` packs, and the `.csp` entries of the `PRELOAD` packs | 780 + 471 | a same-size texture, yes: `csp.py replace` splices it into its entry and no other entry moves, and `csp.py roundtrip` rebuilds all 489 packs byte for byte ([`CSE_FORMAT.md`](CSE_FORMAT.md#csp-pack)). A texture of another size is refused |
| `ACROBATA/ACROBATAPACKFILE.PAC` | 2,137 | same-size bodies could be patched in place; a new size needs the part's wrapper chunks, its POF0 list and the executable's copy of the index (`SLES_541.51` `0x3a3b08`) |
| KC@P `PackData` packs: `PLPACK_HOME`/`AWAY` (kits), `CUTINPACK`, `EDITFACEPACK`, the face packs | 1,392 + 444 + 7 + 41,863 | no `PackData` writer: block sizes and later offsets would be rewritten |
| `ISO/DLL/GAMEPRG.REL` at `0x265fc0` | 1 (16x16, 4 bpp) | only a same-size patch in place |

## Still unknown

- Which `.SVP` palette the code pairs with each external-palette
  texture (above), and which of a room's 32 palettes it picks
  ([`ZBF_FORMAT.md`](ZBF_FORMAT.md#still-unknown)).
- Pixel format `0x0A` (24-bit) is handled by the code but unused, so
  its layout is untested.
- Whether the game shows a rewritten texture in a CSP pack as the reader
  does (`csp.py replace` has not been looked at in PCSX2; the pending
  check is in [`TESTING.md`](../TESTING.md)).
- The writers for the ACROBATA pack and the `PackData` packs (the table
  above), and a changed-size texture in a CSP, ACROBATA or `PackData`
  pack.

## Checking the claims

```bash
python SRC/svr.py info DAT
python SRC/svr.py png DAT out/                  # needs pillow
python SRC/svr.py roundtrip DAT                 # every texture, in every pack
python SRC/svr.py roundtrip DAT --all           # adds the 1.1 GB face pack
python SRC/sles_disasm.py ISO/SLES_541.51 dis nvPrepareSVRTexImagePacket
```
