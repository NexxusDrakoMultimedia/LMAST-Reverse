<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Widescreen

A PCSX2 patch that draws the 3D in 16:9 without stretching it (Hor+: more
of the pitch at the sides, players keep their shape). The 2D UI is still
stretched; see [What's still open](#whats-still-open).

The patch is
[`PNACH/SLES-54151_3CB245D5.pnach`](../PNACH/SLES-54151_3CB245D5.pnach),
for the PAL executable (PCSX2 CRC `3CB245D5`). Copy it into PCSX2's
`patches/` folder, tick "Widescreen 16:9" under Game Properties →
Patches, and boot. The section also sets PCSX2's aspect ratio to 16:9.

Tested in PCSX2: in an exhibition match the pitch widens at the sides
and players keep their proportions, in play and in close-ups
(user report, 2026-10-04).

## How it works

The match sets its camera through Ninja's `nnSetProjectionPXPlusPS2`.
That function copies the projection matrix to a global one, then builds
the VU screen matrix and the clip planes from the copy. The patch
redirects the copy to a cave that also scales `m[0][0]` by 0.75, but only
for perspective projections. Drawing and culling both come from the
scaled copy, so nothing is culled early at the new edges.

The cave sits in `graphics::Graphics::print_config_parameter`, a debug
print that nothing calls (no `jal`, no pointer outside the export
table, and no `.REL` imports it).

| Address | Was | Now |
|---|---|---|
| `0x18f900` | `jal nnCopyMatrix` | `jal 0x12f9b0` |
| `0x12f9b0`–`0x12f9d8` | `print_config_parameter` | `move t9,ra; jal nnCopyMatrix; nop; bnez s0,+5; lui at,0x3f40; mtc1 at,f1; lwc1 f0,0(a0); mul.s f0,f0,f1; swc1 f0,0(a0); jr t9; nop` |

`$s0` holds the projection type (0 = perspective) and `$a0` still points
at the copy after `nnCopyMatrix`, which only touches `$t0`–`$t3`.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x183b60` | `nnMakePerspectiveMatrix` | `(mtx, fov, aspect, near, far)`; fov in 65536ths of a turn (`0x38c90fda` = 2π/65536); `m[0][0] = 1/tan(fov/2)/aspect` |
| `0x18f8a8` | `nnSetProjectionPXPlusPS2` | copies the matrix to `0x365ad0` (`0x18f900`), sets clip planes from it, and derives the PX Plus screen matrix from `m[0][0]` and `m[1][1]` (`0x18fa44`–`0x18fab0`); type in `$s0` |
| `GAMEPRG.REL 0x20ecfc` | (match camera) | `nnMakePerspectiveMatrix` with aspect `0x3faaa993` (≈4/3), then `nnSetProjectionPXPlusPS2` type 0 |
| `GAMEPRG.REL 0x100e4` etc. | (match) | `graphics::Scene::set_projection_matrix_pxplus` (`0x12d8f8`), which calls `nnSetProjectionPXPlusPS2` with the scene's stored matrix |
| `0x1384c8` | `graphics::StadiumShadowContext::make_shadow_matrix` | the stadium shadow uses `nnMakePerspectiveMatrix` and `nnSetProjection` (`0x18f450`), not the PX Plus path, so the patch leaves it alone |
| `0x12f9b0` | `graphics::Graphics::print_config_parameter` | 0x170 bytes, unreferenced |

Patching `nnMakePerspectiveMatrix` itself would also squash the stadium
shadow's projection, which is why the patch works one step later.

## What's still open

The UI draws through several separate 2D paths, and an attempt to
squeeze it to 4:3 only moved some of them. Found so far (PAL, 512-wide
screen, GS units of 1/16 pixel centred on 2048):

| Path | Used for | Placement | Result of scaling it |
|---|---|---|---|
| Ninja 2D table `0x365b98` {offX, scaleX, offY, scaleY}, filled once by `nnInitSystemPS2` (`0x18f308`–`0x18f370`); read by `nnDrawPrimitive2D` (`0x1779d8`) and `nnDrawPrimitiveSprite2DPS2` (`0x179cc0`) | text | `offX + x·scaleX`; values 28672 and 16 | text squeezed correctly (tested in PCSX2) |
| CSE screen, set by `cseSetScreen` (`0x1f47d8`) from `etc::InitializeGameSystem` (`0x14997c`); context pointer at `0x38f458`, scale `+0x80`, offset `+0xa0` | — | offset −0.5, scale 1 | no visible change in the match |
| PX screen parameters `0x369c30` (half-width 256, half-height −224, centre 2048) | 3D (non-PX Plus) | — | squashed the 3D, HUD unchanged (tested live over PINE) |
| `CSpriteDirect::SetPrimData` (`0x126568`) | sprites | hard-coded `(x − 256 + 2048) × 16` | not tried |

`CSpriteRef` (`0x1267e8`, `0x126d70`, `0x127018`) holds the same
hard-coded constants. The scoreboard frames, squad list, radar and
crests still need their path found. `CEditFaceRender::Render`
(`0x151858`) also calls `cseSetScreen`, to build face textures, so a
global CSE change would distort faces.

## Checking the claims

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis nnSetProjectionPXPlusPS2 nnMakePerspectiveMatrix
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x12f9b0 92
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x20ecd8 30 --sles ISO/SLES_541.51
```
