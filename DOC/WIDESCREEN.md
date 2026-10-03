<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Widescreen

A PCSX2 patch that draws the 3D in 16:9 without stretching it (Hor+: more
of the pitch at the sides, players keep their shape), and an optional
second section that draws the match HUD at 4:3 proportions; see
[The UI fix](#the-ui-fix).

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

## The UI fix

A second section, "Widescreen 16:9 UI fix (experimental)", draws the
match HUD at 4:3 proportions in the middle of the 16:9 screen. Tested in
PCSX2: in an exhibition match the scoreboard, clock, radar and their text
line up at 4:3 proportions (user report, 2026-10-04). The menus are not
fixed yet: their text is squeezed but their panels are not.

The match HUD draws through two paths, and both have to be squeezed the
same way (PAL is 512 pixels wide; GS units are 1/16 pixel, centre 2048):

| Path | Draws | Placement | Patch |
|---|---|---|---|
| Ninja 2D table `0x365b98` {offX, scaleX, offY, scaleY}, filled once by `nnInitSystemPS2` (`0x18f308`–`0x18f370`); read by `nnDrawPrimitive2D` (`0x1779d8`), `nnuPrimitive2DSetVertex` (`0x167580`) and `nnDrawPrimitiveSprite2DPS2` (`0x179cc0`) | text | `offX + x·scaleX`, 28672 and 16 | 29696 and 12 (two data words) |
| `CSpriteDirect::SetPrimData` (`0x126568`) | panels, scoreboard, clock, radar | `((x − 256) + 2048) × 16`, 256 in `$f23` | `sub.s` at `0x12666c` becomes `jal 0x12fa10`, which also multiplies by 0.75 |

Which functions run in a match was found by hooking each candidate with
a stub that stored its return address (live, over PINE): `CSpriteDirect::SetPrimData`,
`nnuPrimitive2DSetVertex` and `nnDrawPrimitive2D` ran; `CSprite::Draw`,
`nnDrawPrimitiveSprite2DPS2` and every CSE draw routine
(`cseCastFaceDrawCorePS2`, `cseCastFaceNonTexDrawCore`, `0x1f1378`,
`0x1f3850`) did not.

Ruled out:

| Tried | Result |
|---|---|
| CSE screen (`cseSetScreen` `0x1f47d8`; context at `0x38f458`, scale `+0x80`, offset `+0xa0`) | no change in the match (CSE doesn't draw there) |
| PX screen parameters `0x369c30` (half-width 256) | squashed the 3D, HUD unchanged |

## What's still open

- The menus (VS Mode, the management overlay `SIMPRG.REL`) draw panels
  with CSE, which builds a 3×3 matrix per cast node and hands it to VU1 in
  `cseCastFacePutTriStripParamPS2` (`0x1f2040`, rows at `$t1`, copied by
  the loop at `0x1f20b4`; `x' = x·m00 + y·m10 + tx`). `CEditFaceRender::Render`
  (`0x151858`) also uses CSE, to build face textures, so a fix there must
  leave faces alone.
- Name tags over players come from 3D positions but are drawn as text,
  so the text patch pulls them toward the centre.
- The boot video-mode box uses yet another path; it stays stretched.

## Checking the claims

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis nnSetProjectionPXPlusPS2 nnMakePerspectiveMatrix
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x12f9b0 92
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x20ecd8 30 --sles ISO/SLES_541.51
```
