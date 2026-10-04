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
and players keep their proportions, in play and in close-ups; shadows
stay under the players; the Club House staff and the player-card
portraits keep their shape (user report, 2026-10-04).

## How it works

Ninja sets a projection with `nnSetProjectionPXPlusPS2` (the match, most
3D scenes) or `nnSetProjection` (some management-screen models, the
stadium shadow). Both copy the projection matrix to a global one, then
build the VU screen matrix and the clip planes from the copy. The patch
redirects both copies to caves that scale the copy's `m[0][0]` by 0.75,
for perspective projections only. Drawing and culling both come from the
scaled copy, so nothing is culled early at the new edges.

Two checks keep the scaling to the real screen:

- It only applies while the PX screen half-width (`0x369c30`) is 256.
  `graphics::TargetSurface::begin` (`0x1394a8`) puts the texture's own
  screen parameters when the game renders into a texture (player
  portraits), and `end` (`0x139598`) restores the screen's. Without this
  the portraits came out narrow, squeezed once here and once more by the
  UI fix when shown.
- `nnSetProjection` skips the stadium shadow's two call sites (return
  addresses `0x13853c` and `0x1385c4`, read from its frame at
  `0x60($sp)`). Without the `nnSetProjection` cave, the Club House
  staff's heads (PX Plus) and bodies (`nnSetProjection`) came apart.

The caves sit in `graphics::Graphics::print_config_parameter`, a debug
print that nothing calls (no `jal`, no pointer outside the export
table, and no `.REL` imports it): `0x12f9b0` (PX Plus), `0x12fa90`
(`nnSetProjection`) and `0x12fad8` (the shared check and scale). The
hooks are `0x18f900` and `0x18f488`, both `jal nnCopyMatrix` before.

All code patches use `patch=0`, applied once when the executable loads.
With `patch=1` PCSX2 rewrote the code every frame, which makes it
recompile those pages each frame; a custom (VPF) player's face, which the
match builds at load time, then came out striped (tested in PCSX2: fixed
by `patch=0`, user report). Only the two Ninja 2D table words of the UI
fix stay `patch=1`, because the game writes that table itself after boot.

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
line up at 4:3 proportions; in season mode the Club House and Pre-match
menus and the pre-match intro panel line up too, and faces look normal
(user report, 2026-10-04). On the Pre-match screen the striped
background still runs past the 4:3 area.

The HUD and menus draw through three paths, and all have to be squeezed
the same way (PAL is 512 pixels wide; GS units are 1/16 pixel, centre 2048):

| Path | Draws | Placement | Patch |
|---|---|---|---|
| Ninja 2D table `0x365b98` {offX, scaleX, offY, scaleY}, filled once by `nnInitSystemPS2` (`0x18f308`–`0x18f370`); read by `nnDrawPrimitive2D` (`0x1779d8`), `nnuPrimitive2DSetVertex` (`0x167580`) and `nnDrawPrimitiveSprite2DPS2` (`0x179cc0`) | text | `offX + x·scaleX`, 28672 and 16 | 29696 and 12 (two data words) |
| `CSpriteDirect::SetPrimData` (`0x126568`) | panels, scoreboard, clock, radar | `((x − 256) + 2048) × 16`, 256 in `$f23` | `sub.s` at `0x12666c` becomes `jal 0x12fa10`, which also multiplies by 0.75 |
| CSE: `cseCastFacePutTriStripParamPS2` (`0x1f2040`) copies each cast node's 3×3 matrix (rows at `$t1`, `x' = x·m00 + y·m10 + tx`) into the VU1 packet in the loop at `0x1f20b4` | menu panels | the node matrix | `0x1f20e0` jumps to `0x12fa30`, which scales the copied x column by 0.75 and adds 64 to tx, then returns; CSE's own matrices are unchanged. It only does so while the CSE screen's offX (context `0x38f458` `+0x68`) is −0.5, the menus' value, so `CEditFaceRender::Render` (`0x151858`), which sets its own screen to build custom players' faces, is left alone |

Which functions run in a match was found by hooking each candidate with
a stub that stored its return address (live, over PINE): `CSpriteDirect::SetPrimData`,
`nnuPrimitive2DSetVertex` and `nnDrawPrimitive2D` ran; `CSprite::Draw`,
`nnDrawPrimitiveSprite2DPS2` and every CSE draw routine
(`cseCastFaceDrawCorePS2`, `cseCastFaceNonTexDrawCore`, `0x1f1378`,
`0x1f3850`) did not.

Ruled out:

| Tried | Result |
|---|---|
| CSE screen (`cseSetScreen` `0x1f47d8`; context at `0x38f458`, scale `+0x80`, offset `+0xa0`) | no change in the match (CSE doesn't draw there); the per-node matrix in the VU1 packet is patched instead |
| PX screen parameters `0x369c30` (half-width 256) | squashed the 3D, HUD unchanged |

## What's still open

- UI the game parks just off its 512-pixel screen now lands in the side
  margins: the hidden squad list in the match, and probably the
  Pre-match screen's striped background. Clipping the 2D layer to the
  4:3 area would hide it, but needs the point in the frame where 2D
  drawing starts.
- `etc::Util_ScissorBeginDirect` (`0x14c860`) clamps clip rectangles to
  0–511 and writes them to the GS unchanged, so lists that clip will
  clip at unsqueezed positions.
- Name tags over players come from 3D positions but are drawn as text,
  so the text patch pulls them toward the centre.
- The boot video-mode box uses yet another path; it stays stretched.

## Checking the claims

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis nnSetProjectionPXPlusPS2 nnMakePerspectiveMatrix
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x12f9b0 92
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x20ecd8 30 --sles ISO/SLES_541.51
```
