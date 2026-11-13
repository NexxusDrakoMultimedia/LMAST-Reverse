<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# ZBF pre-rendered depth buffers (`*.zbf`)

The game's cut-scene and menu rooms (offices, changing rooms, TV studio,
stadium concourse, ...) are pre-rendered images with 3D characters drawn
on top. A `.zbf` is the **Z buffer that goes with one of those images**:
the game loads it into GS depth memory so characters are hidden behind
the rendered furniture.

There are 140 of them, one per MRG in the main background sets
`BG/BG_{CH,EN,FS,IP,IS,MN,OF,OR,RR,SP,TV}_nn.MRG`, always named
`BG_xx_nn_00.zbf` with merge user ID 4 (see [`PAC_FORMAT.md`](PAC_FORMAT.md)).
The `BG_OR2`, `BG_P2` and `BG_PP` MRGs have none.

`SRC/zbf.py` reads them (there is no writer). `python SRC/zbf.py info
DAT` checks them all; `python SRC/zbf.py png DAT out/` writes each one as
a greyscale PNG (white = near).

## Layout

No header. Always `0xE0000` bytes:

| | |
|---|---|
| size | 512 × 448 pixels × 4 bytes |
| pixel | little-endian u32 depth |
| order | row-major, top-left first, **linear** (not GS-swizzled) |

512×448 is the game's frame buffer size, so the file is a screen-space
depth image.

## How it relates to the background image

The colour image is `CSE/BG_xx_nn_00.CSP` (see
[`CSE_FORMAT.md`](CSE_FORMAT.md); the name pattern
`BG_%s_%02d_00.csp` is in `DLL/SIMPRG.REL`). It holds an embedded SVR
(at `0x190` in `BG_CH_00_00.CSP`): a **512×512** 8bpp texture. 110 of the
151 background CSPs carry their own palette (data format `0x6C`). The
other 41 use an external one (`0x64`). 63 of the 140 MRGs carry a set of
32 palettes, `BG_xx_nn_00.svp` … `BG_xx_nn_31.svp`. `BG_CH_00_00.svp`
decodes `BG_CH_00_00.CSP` correctly. Which of the 32 the game picks isn't
known (below).

The two sets don't match one to one (**empirical**, from the file names
and [`BG_DIR.md`](BG_DIR.md)). 139 of the 151 background CSPs have a
`.zbf` (`BG_MNTC_00_00.CSP` goes with `BG_MN_00_00.zbf`). The other 12,
the `P2`, `PP` and `TR` rooms, have none, and `BG_IS_00_00.zbf` has no CSP
of its own.

Scaled to 512×448, that texture lines up with the `.zbf` **pixel for
pixel**: every depth edge sits on the rendered furniture, plants and
window frames. So the background is drawn as a 512×512 texture squashed
onto the 448-line screen, and the Z buffer was rendered at screen
resolution.

## Values

- **Larger = nearer.** The floor at the bottom of the screen has the
  highest values, and open windows/sky are 0. This matches the usual PS2
  setup of `ZTST = GEQUAL` with the buffer cleared to 0.
- **Only the low 24 bits count (PSMZ24).** This is inferred from the data:
  `BG_MN_00_00.zbf` is filled entirely with `0x01000000`. Read as Z24 that is
  0 ("infinitely far"), so characters always draw over that menu
  background. Read as Z32 it would be nearer than anything in any other
  scene, which would hide the characters. Every other file stays below
  `0x01000000`. `zbf.py info` flags this one file with `!!` (229,376
  pixels with bits above 24); that is the expected fill, not damage.
- Ranges vary by scene (**empirical**, `zbf.py info`). Most peak at
  `0xC3B9` (64 files) or `0xD3EE` (50). The highest peak is `0x2D4C1`
  (`BG_IP_00_00`); the three RR rooms reach `0x23410` and the TV rooms
  top out at `0x18A64`.

## Loading

**Confirmed** (traced for the widescreen patch,
[`WIDESCREEN.md`](WIDESCREEN.md#room-depth)):

| Address | Symbol | What it shows |
|---|---|---|
| `SIMPRG.REL 0xfc3a8` | (unnamed) | takes the depth file through `CLoader::getBinary` and sends it with `nnuLoadImagePS2` as a 512×448 PSMZ32 image (`0x30`) of `0xe0000` bytes straight into the Z buffer |
| `0x1668f0` | `nnuLoadImagePS2` | the transfer routine |
| `SIMPRG.REL 0x408a8`, `0xcace4`; `CEDITPRG.REL 0x1db8`, `0x6bb8` | (unnamed) | their depth buffers go the same way |
| `SIMPRG.REL 0xfe8c0` | `CBackgroundManager` | clears the Z buffer with a zero buffer of the same shape |

So the upload is a plain PSMZ32 transfer. That the Z buffer itself is
PSMZ24 with `ZTST = GEQUAL` still comes from the data alone (above):
the frame's own Z buffer format and depth test weren't traced.

## Still unknown

- The frame's own Z buffer format and depth test (PSMZ24 and
  `ZTST = GEQUAL` come from the data only).
- The projection that maps scene depth to these values.
- Which of a room's 32 palettes the game picks, and when
  ([`BG_DIR.md`](BG_DIR.md#still-unknown)).

## Checking the claims

```bash
python SRC/zbf.py info DAT          # 140 depth buffers; the one !! is BG_MN_00_00.zbf
python SRC/zbf.py png DAT out/      # needs pillow
python SRC/pac.py list DAT/BG/BG_CH_00.MRG
```
