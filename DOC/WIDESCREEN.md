<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Widescreen

A PCSX2 patch that draws the 3D in 16:9 without stretching it (Hor+: more
of the pitch at the sides, players keep their shape), and draws the 2D
(the match HUD, the menus and the season-mode backgrounds) at 4:3
proportions in the middle of the screen; see [The UI fix](#the-ui-fix).

The patch is
[`PNACH/SLES-54151_3CB245D5.pnach`](../PNACH/SLES-54151_3CB245D5.pnach),
for the PAL executable (PCSX2 CRC `3CB245D5`). Copy it into PCSX2's
`patches/` folder, tick "Widescreen 16:9" under Game Properties →
Patches, and boot. It's one section, which also sets PCSX2's aspect
ratio to 16:9. [`PNACH/pcsx2/`](../PNACH/pcsx2/) holds the same patch
without the comments, for submitting to PCSX2's patch collection.
The FMVs (the intro and the event movies) stay stretched to 16:9.
PCSX2's FMV Aspect Ratio Override didn't switch them back to 4:3 in a
test (user report); the user is happy to leave them.

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

Each run of consecutive words is one `bytes` line (PCSX2 writes the hex
in memory order, so each instruction word appears byte-reversed), and
single words stay `word` lines: 15 lines in all. Unused words between
caves in the same debug function are written as zero. Checked over PINE
in PCSX2 2.8.2: after boot, all 167 words of the earlier one-word-per-line
patch read back unchanged, and the gaps read zero.

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

The second half of the patch draws the match HUD at 4:3 proportions in
the middle of the 16:9 screen. (It was a separate section, "Widescreen
16:9 UI fix", until it was tested everywhere; the two are now one.
Tested in PCSX2 as one section from boot, user report, 2026-10-09.) Tested in
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

Name tags over players need no patch of their own. The match keeps its
projection matrix in `graphics::Scene` (`+0x10`, built by
`make_perspective_matrix` at `0x12d8a8` with the 4:3 aspect) and the
patch only widens the global copy at `0x365ad0`. A tag placed with the
4:3 matrix and then squeezed by the UI fix's text path lands where the
widened 3D draws the player. Tested in PCSX2: the tags stay over their
players (user report). Which match function places them hasn't been
traced.

The black letterbox bars of the special-tactics replays are 2D, so they
are squeezed and clipped to 4:3 like the rest of the UI, and the 3D
shows beside them. That is the intended look (user's choice): drawing
full-width bars would need telling them apart from sliding panels.

### Clipping to 4:3

UI the game parks just off its 512-pixel screen (the hidden squad list,
slide-ins, the scrolling news ticker) would land in the side margins once
squeezed. The UI fix clips 2D to the 4:3 area with the GS scissor (x
64–447), like the edge of a 4:3 screen. Every way the game sets a
scissor has to agree on the squeezed coordinates, or a full-width box
reopens the margins:

| Where | What it did | Patch |
|---|---|---|
| `sort2d::CEtcSort2d::Execute` calls the 2D pass, `sort2d::CSort2d::Execute` (`0x1fe220`), at `0x14c5d4` | – | a wrapper at `0x13be98` sets the variable below to x 64–447 and applies it, runs the pass, then sets x 0–511 and applies that |
| `etc::Util_ScissorEnd` (`0x14cb20`) | restores a hard-coded full screen (`0x14cb40`–`0x14cb4c`) | reads the variable at `0x13bfc0` |
| `sort2d::CEtcSort2d::CallScissorEnd` (`0x14bf28`) | the same, at `0x14bf40`–`0x14bf4c` | reads the variable |
| `etc::Util_ScissorBeginDirect` (`0x14c860`), also behind `etc::Viewport_SetRect` | clamps boxes to x 0–511, unsqueezed | after the clamps, x0 and x1 (`0($sp)`, `8($sp)`) become x·0.75 + 64 (`0x14c9b0` → `0x13bee4`) |
| `sort2d::CEtcSort2d::CallScissorBegin` (`0x14bd70`) | the same | the same mapping (`0x14be6c` → `0x13bf1c`) |

The scissor value is the GS SCISSOR register (`x0 | x1<<16 | y0<<32 |
y1<<48`), kept in two draw contexts at `0x369dc0` and `0x369f20` and sent by
`PXPutContext` (`0x1b4ac8`). These caves sit in
`graphics::GlareFilter::display_reduction_buffer` (`0x13be98`, 0x140
bytes), a debug display nothing calls. Tested in PCSX2: the hidden squad
list no longer shows in the match, the ticker and the menu slide-ins stop
at the 4:3 edge, list rows are intact (user report, 2026-10-04).

### Season-mode backdrops

The season-mode screens draw an Acrobata scene behind their menus, such as
the scrolling map behind the Edit club screen ([`ACROBATA_DIR.md`](ACROBATA_DIR.md)). The
scene reaches past the 4:3 area, and it isn't drawn in the 2D pass, so the
clip above doesn't cover it. With the scissor held at 4:3 for the whole
frame the margin was clean, so the scene does respect the scissor.

The draws come from task draw methods in the overlays, which the task draw
loop calls one by one at `0x1052a8` (`jalr $v1`, in the function at
`0x105280`). On the Edit club screen two of them draw Acrobata scenes, both
through `ACROBATA::CAckManager::draw` (`SIMPRG.REL 0x117a98`):

| Draw method | Overlay | Fetches the manager at |
|---|---|---|
| SimRoot's draw (`SIMPRG.REL 0x7f40`) | `SIMPRG.REL` | `+0x7c` |
| the club editor's draw (`CEDITPRG.REL 0xcbc8`) | `CEDITPRG.REL` | `+0x8` |

The UI fix sends that call through a cave. If the first 40 words of the
draw method contain `jal 0x2e7378` (`ACROBATA::CAckManager::getInstance`,
the word `0c0b9cde` wherever the overlay was loaded), it runs the method
with the scissor at 4:3, with the 2D-pass wrapper restoring 4:3 rather
than full width, then sets full width back. Other draw methods are passed
straight on. No code in `GAMEPRG.REL` calls `getInstance`, so the match
isn't clipped. The cave sits in `graphics::OperatePostEffect::display_menu`
(`0x13cca8`, 0x150 bytes), a debug menu referenced only from the export
table; the menus it calls are only called from it.

Tested in PCSX2 from boot with the pnach: the map behind Edit club and the
Pre-match screen's background stop at the 4:3 edge; the Club House rooms,
staff and portraits look as before; in a match the 3D still fills 16:9
and the HUD is unchanged (user report, 2026-10-09).

Found by live hooks over PINE that logged each caller with the scissor
value at the time. Ruled out on the way:

| Tried | Result |
|---|---|
| Clipping Ninja 2D primitives (`nnBegin`/`nnEndDrawPrimitive2D`) drawn from the overlays outside the 2D pass | ran twice a frame (the Acroarts 2D layer, `SIMPRG.REL 0x1b1b94`, and `CBackgroundManager`'s screen-lock quad), margin unchanged |
| The same for 3D primitives (`nnBeginDrawPrimitive3D`, called by Acroarts at `SIMPRG.REL 0x1b155c`) | margin unchanged |
| Clipping only SimRoot's draw | margin unchanged: on this screen the club editor's draw method draws the scene |

### Room changes

When the player moves between the Club House, My Room and the Office,
`CBackgroundManager` shows the last frame while the next room loads, then
fades it out over the new room. Its draw function (`SIMPRG.REL 0xfe5c0`,
not exported) takes the captured frame's texture from the manager's
surface at `+0x154` and draws it with `nnDrawPrimitive2D` as one textured
quad: from the vertices at `SIMPRG.REL 0x1d6ab8` while the screen is
locked, and from `0x1d6a68` with alpha `+0x17c` (falling by 8 a frame)
during the fade. Both are 4 vertices of 0x14 bytes {x, y, colour, u, v},
covering x and y 0–512 with u and v 0–1.

The frame already holds the 4:3 picture in the middle (x 64–447), so the
text squeeze shrank it a second time, to x 112–399: the old room dropped
to 75% of the menu width until the new room faded in.

The UI fix sends `nnDrawPrimitive2D` (`0x1779d8`, whose first instruction
becomes `j 0x13cd40`) through a cave. For 4 vertices whose last one has
x = y = 512.0 and v = 1.0 (offsets `0x3c`, `0x40`, `0x48`; the textured
layout, stride 0x14 at `0x177dd4`), it writes the unsqueezed table values
(28672, 16), draws, and writes the squeezed ones (29696, 12) back. The
function reads the table inside its vertex loop (`0x177b68`,
`0x177ce4`), so the change applies to that quad only. Every other
primitive goes straight on. The cave follows the backdrop cave in
`display_menu`, at `0x13cd40`–`0x13cdb8`.

Tested in PCSX2 from boot: changing rooms in season mode, the old room
keeps its full 4:3 width while the next one loads and fades in (user
report, 2026-10-09).

## Known behaviour

- The FMVs stay stretched to 16:9 (see the top of this page).
- The stadium ad boards floating above the pitch in replays are the
  game's normal behaviour, not the patch (user report).
- Nothing is known to be broken: every UI item found so far is fixed or
  is the intended look.

## Checking the claims

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis nnSetProjectionPXPlusPS2 nnMakePerspectiveMatrix
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x12f9b0 92
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x20ecd8 30 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x7f40 48 --sles ISO/SLES_541.51
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x105280 16
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0xfe5c0 140 --sles ISO/SLES_541.51
python SRC/sles_disasm.py ISO/SLES_541.51 dis nnDrawPrimitive2D
```
