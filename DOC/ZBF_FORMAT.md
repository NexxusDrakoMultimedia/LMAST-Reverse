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

`python SRC/zbf.py info DAT` checks them all; `python SRC/zbf.py png DAT
out/` writes each one as a greyscale PNG (white = near).

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

The colour image is `CSE/BG_xx_nn_00.CSP` (see [`CSE_FORMAT.md`](CSE_FORMAT.md); the name pattern
`BG_%s_%02d_00.csp` is in `DLL/SIMPRG.REL`). It holds an embedded SVR
(at `0x190` in `BG_CH_00_00.CSP`): a **512×512** 8bpp texture. 110 of the
151 background CSPs carry their own palette (data format `0x6C`). The
other 41 use an external one (`0x64`). 63 of the 140 MRGs carry a set of
32 palettes, `BG_xx_nn_00.svp` … `BG_xx_nn_31.svp`. `BG_CH_00_00.svp`
decodes `BG_CH_00_00.CSP` correctly. I haven't worked out which of the 32
the game picks, or when.

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
  `0x01000000`.
- Ranges vary by scene. Most peak at `0xC3B9` (64 files) or `0xD3EE`
  (50). The RR, IP and TV rooms go up to `0x2D4C1`.

## Not yet confirmed from code

The loader lives in the overlays (`BGCONTROL_MODULE` in `DLL/SIMPRG.REL`,
`BG_LIGHT_TEST_MODULE` in `DLL/TESTPRG.REL`). These are SNR2 relocatable
modules, and `SRC/sles_disasm.py` can't disassemble them yet. The
executable holds no `zbf` string, and nothing in it references the
`BG_%s_%02d.mrg` strings in its data section directly, so the
PSMZ24/GEQUAL reading above comes from the data alone. Still unknown: the
exact GS upload (probably a PSMZ32 transfer into a PSMZ24 buffer) and the
projection that maps scene depth to these values.
