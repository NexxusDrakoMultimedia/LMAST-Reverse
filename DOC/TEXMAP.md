<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# PCSX2 texture names and the disc's textures (`texmap.py`)

PCSX2 can swap a game's textures for PNG files (Graphics > Texture
Replacement). It finds the right file by name: each texture the game
draws is hashed, and the PNG called `<hash>-<palette hash>-<state>.png` is
used instead. [LMAST Realism](https://github.com/NexxusDrakoMultimedia/LMAST-Realism),
Nexxus's texture pack, is a folder of such files. To put a pack's pictures
on the disc itself ([`LMASTER_MOD.md`](LMASTER_MOD.md#lmast-realism-on-the-disc)), each PNG
must first be matched to the disc texture it replaces. `SRC/texmap.py`
computes the same names from the textures on the disc, so that match needs
no running emulator.

The matching is only as good as the hash, so this page says exactly what
is hashed and how that was shown.

## What PCSX2 hashes

**Confirmed from PCSX2's source** (`GSTextureCache.cpp`,
`HashCacheKey::Create` and `HashTextureLevel`; `GSTextureReplacements.cpp`;
`GSLocalMemory.cpp`, read 2026-11-06) and **checked against real files**
below. This is PCSX2's code, not the game's.

| Part of the name | What it is |
|---|---|
| texture hash | XXH3 64-bit (seed 0, default secret) of the texture's data, below |
| palette hash | XXH3-64 of the 16 or 256 palette entries as little-endian `u32` (R, G, B, A bytes, A from 0 to `0x80`); absent for a direct-colour texture |
| state, 8 hex digits | PSM in bits 0–5, TW 6–9, TH 10–13 (sizes are `1 << TW` and `1 << TH`), bit 14 unused in current PCSX2, TA0 in 15–22, AEM in 23, TA1 in 24–31 |

The two hashes are written in hex without leading zeros; the state is
always 8 digits. A region adds `-r<w>x<h>` and a mip level `-mip<n>`.

What is hashed depends on the size of the texture:

| Texture | Bytes hashed |
|---|---|
| smaller than one GS block (4 bit under 32x16, 8 bit under 16x16, 32 bit under 8x8) | the palette index of every texel, one byte each, row by row |
| 16 bit | four bytes a texel: R, G, B = 5 bits shifted left 3, A = TA1 if bit 15 is set, else TA0 (0 if AEM and the colour is 0) |
| everything else | the raw 256-byte blocks of the texture in **GS local memory**, in block-row order (a row of blocks, left to right, then the next row), each block found by the PSM's block table; no unswizzling, no palette |

The block data is what the game left in GS memory. A level that
[`svr.py`](SVR_FORMAT.md#swizzling) keeps swizzled was uploaded as PSMCT32
words, so its memory is the stored words placed by the CT32 address
pattern; a smaller level was uploaded in its own PSM. The hash does not
depend on the palette, so one disc texture appears under several names when
the game draws it with several palettes.

## Checked

```bash
python SRC/texmap.py selfcheck
python SRC/texmap.py index DAT
python SRC/texmap.py match <LMAST-Realism>/textures/SLES-54151/replacements DAT
```

- **XXH3 in Python.** The standard library has no XXH3, so `texmap.py`
  writes it out. It agreed with the reference library on 3,007 input
  lengths (0 to 2,999, then 4 KB up to 512 KB; every length class), and
  `selfcheck` repeats 15 of those values.
- **173 of 173 crest textures.** PCSX2's `dumps` folder holds pictures of
  the textures it drew. 173 of them were matched by pixels to textures of
  `0SYSTEM/EMBLEM_TEXTURE.PAC` (128x128, 4 bit, one GS page), and the
  block-order hash of each disc texture equals the hash in its dump's file
  name: 173 of 173. Hashing the unswizzled indices, one byte or one nibble
  a texel, or the blocks in memory-address order, matched none of them; the
  small textures (8x8 and 16x16, 4 bit; 8x8, 8 bit) match the one index
  byte a texel rule.
- **LMAST Realism.** The pack's `replacements` folder has 1,635 files:
  1,614 PNG and 21 BMP (extras, not PCSX2 names). `texmap.py match` finds
  the disc texture for 1,613 of the 1,614 PNG (570 distinct textures; most
  appear under several palettes). 431 of those also match the palette hash,
  which checks the palette side. Every match agrees with the file name's
  PSM and size, so none is a hash coincidence. The one without a disc
  texture is `Rival/c748e17a1a54842d-80001dc2.png`, the HD preview of the
  rival club's logo, which the game most likely draws from a run-time
  texture.

| Where the pack's textures are | Files | A writer? |
|---|---|---|
| `0SYSTEM/EMBLEM_TEXTURE.PAC` (crests; `FLAG_TEXTURE.PAC` holds the same pictures) | 346 | yes, `pac.py replace` |
| `PLAYER/EDIT_UNIFORM_ORG_SOX/SHT/PNT.PAC`, `EDIT_UNIFORM_GK_SHT/PNT.PAC` (kit parts) | 1,182 | yes, but see the palettes below |
| `0SYSTEM/MATCH_TEXTURE`, `MINIMATCH_TEXTURE`, `MINIEMBLEM_TEXTURE`, `SPONSOR_TEXTURE_M` | 73 | yes |
| `CSE/*.CSP` (league logos and menu screens) | 8 | yes, `csp.py`'s `replace` (7 of the 8: the `Intro` one is left out) |
| `ACROBATA/ACROBATAPACKFILE.PAC` (intro scenes) | 4 | no |

(`match` prints the count of files by holder; the table shows the
sub-folders from its CSV.) A texture can sit in several places on the
disc (the `PRELOAD` copies, and `EMBLEM_TEXTURE` with `FLAG_TEXTURE`): 929
files have one target, 665 two, up to 8.

## Palettes

The disc keeps one picture and one palette per texture, while a pack has
one PNG for each palette PCSX2 saw. For the crests this is no problem: the
346 files are 344 textures with one palette each, and the PNG's palette
hash is the disc palette's. The 1,182 files whose palette differs are all
kit parts, and they are only 140 disc textures with 1 to 38 PNGs each
(17 textures have one, 27 two, 12 three, and so on up to 38): the game
draws a kit part with many palettes, and Realism has a PNG for each.
A disc texture can hold only one of them, so putting the kits on the disc
is not a texture replacement but a change to how the kits are made
([`UNIFORM_FORMAT.md`](UNIFORM_FORMAT.md)). **Nexxus's choice, 2026-11-07:
the kits stay Realism-only**, a PCSX2 texture pack, and are not put on
the disc.

```bash
python SRC/texmap.py match <LMAST-Realism>/textures/SLES-54151/replacements DAT --csv map.csv
```

The CSV has one row per file: its hashes, whether the palette matched,
how many disc textures it replaces, what holds them, and the first three
labels (`DAT/0SYSTEM/EMBLEM_TEXTURE.PAC#12:...`).

## Putting the pack on the disc (`apply`)

```bash
python SRC/texmap.py apply <LMAST-Realism>/textures/SLES-54151/replacements DAT mod \
    --licensed-border 2 [--sles ISO/SLES_541.51] [--dry-run]
```

`apply` writes copies of the files that hold the pictures, laid out like
`DAT`, into `mod/` (it never changes `DAT`). Each picture goes in only
where PCSX2 would use it, **texture hash and palette hash both equal**
(**empirical**: 431 of the pack's files, 781 disc textures with the copies
in `EMBLEM_TEXTURE` and `FLAG_TEXTURE`). The steps:

1. The picture is scaled to the disc texture's size if it differs (three
   of the pack's are 4 or 8 times larger; Lanczos).
2. The pack keeps the alpha the GS sees, 0 to `0x80`, and 1,570 of its
   1,614 PNG never pass `0x80`. A picture whose most common visible alpha
   is at most `0x80` is taken so, and scaled to 0 to 255 first, with the
   rounding `svr.py` undoes, so `0x80` is stored as `0x80` and a half
   transparent pixel stays half transparent; alpha above `0x80` (the
   seven mini-crest sheets reach 148 where they were resized) is held at
   `0x80`. Any other picture, 44 of them with opaque pixels at 255, is
   taken as 0 to 255. (A first version looked only at the highest alpha,
   so the resized sheets were stored half transparent: Nexxus's report,
   2026-11-07, the mini logos in the club ranking.)
3. `svr.py`'s writer puts it into the texture with a new palette built
   from the picture (`body_from_pixels`), halving the mip levels, and the
   file keeps its length.
4. The entry goes back into its pack (`pac.py`'s `build_binpac`, PRSH
   entries recompressed); the pack's header and the rest are untouched.

Left out, and counted in the output: the 1,182 kit pictures (palette
differs; **Nexxus's choice, 2026-11-07: the kits stay Realism-only, a
PCSX2 texture pack**), the pack's `Intro` and `Rival` folders (**Nexxus's
scope, 2026-11-12**: LMASTER will have intros of its own, and `Rival` is an
AI upscale made from mipmaps, largely incompatible; `--all-folders` puts
them in), disc textures that two different pictures of the pack claim (none at
the moment: Clermont Foot's crest had one, a mislabelled Rapid Wien
logo that Nexxus removed from the pack, 2026-11-07), and the files
without a disc texture. A texture also held in a `PRELOAD` pack is written only in
its original: `patch_disc.py --copies` carries it to the copy.

**CSP packs** (Nexxus's scope, 2026-11-12: the pack's `Fixes`, `Adboards`
and `Leagues` folders, 73 files, 65 of them in plain packs and 7 in CSP
packs). A texture in a CSP pack is labelled `<file>.CSP#<entry>` (the
entry's place in the pack, the layout being entry 0) and goes back with
`csp.py replace`: the same-size texture is spliced into the original
bytes, so no other entry moves (**empirical**: the 7 pictures write 16
packs, the `WP_FACILITIES_01` to `_03` pack of the `Fixes` folder and the
`SC_SIXNATIONS_01` to `_04` language copies of `Leagues`, each the size of
the original, with the CSE and every other entry unchanged, and the
texture reading back). The rest of the two folders was already written
through the BINPAC packs.

A crest is 4 bit with a 16-colour palette, so the pack's full-colour
pictures are reduced to 16 colours; 563 of the 781 differ by more than 16
in some channel on over 5% of their pixels, and by eye the crests keep
their shape and main colours.

`--licensed-border 2` also takes the **original crests of the licensed
clubs** (the 116 clubs of Italy, Spain and the Netherlands, team ids 123
to 244, [`UNIFORM_FORMAT.md`](UNIFORM_FORMAT.md#licensed-kits)) that the
pack does not replace, in `EMBLEM_TEXTURE.PAC` and `FLAG_TEXTURE.PAC`
(entry = team id - 3), and scales each down by twice the border, so that
it has that many more transparent pixels on every side, as Realism's
logos have (Nexxus's request, 2026-11-07; the mini-crest sheets already
had it). The picture is matched to the crest's own palette, so the
colours stay the game's. 227 of the 232 crests (116 clubs, two packs) get
it; 5 have a Realism picture. The licensed crests had 2 transparent
pixels at the top and bottom (1 or 0 in 8 of them) and about 2 to 30 at
the sides, and most of Realism's crests have 4 on every side. Nexxus
asked for 2 pixels, tried 4 on request and went back to **2** (2026-11-07),
so a crest keeps about 4 at the top and bottom.

**Tested in PCSX2** (Nexxus's report, 2026-11-07, `LMAST-test-realism.iso`): a disc built with `--mod realism` shows the pack's pictures. Its first build showed the mini logos in the club ranking half transparent (Nexxus's screenshot): the resized mini-crest sheets reached alpha 148 and were read as 0 to 255, fixed in `pack_picture`; the rebuilt disc works.

## Still unknown

- Whether the 16 bit hash (alpha from TEXA) is right: the one 16 bit file
  in the pack has no disc texture to test it on.
- About 400 of the pack's names have bit 14 of the state set (`5dd4`,
  `5dd3`, ...), which current PCSX2 writes as 0. Whether PCSX2 2.8.2 finds
  those files under either spelling is not checked here; the hashes do not
  depend on it.
- Mip level and region files (none in the pack), and whether older PCSX2
  versions hashed differently.
- The `Rival` logo's source, and the 21 BMP files in the pack.
- Which disc texture the face pack's hair and face pictures are (the
  1.1 GB `FC_EURO_FACEPACK_00` is skipped unless `--all`).
