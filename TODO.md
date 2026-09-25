# TODO

Rough priority order, most valuable first.

## 1. Message text (`DAT/MESSAGE/MES.PAC`)

The format is decoded: see [`DOC/MBB_FORMAT.md`](DOC/MBB_FORMAT.md) and
`SRC/mbb.py`. All 3,738 files and 66,102 messages parse, in 7 language slots.

- [x] Find the `.mbb` loader (`Msg::CMsgSubCategory::Initialize`, `0x30d1c8`)
- [x] Write `DOC/MBB_FORMAT.md`
- [x] Add `SRC/mbb.py` with `info`, `dump` and `csv`
- [x] Link messages into `evsdatabin.py` output (`--text`). Message refs are
      `category << 16 | id`: EVENT `+0x64`, NEWS `+0x64`/`+0x6c`, MAIL
      `+0x10`/`+0x14`/`+0x20`/`+0x24`
- [x] Name the NEWS and MAIL columns in `DOC/EVSDATABIN_FORMAT.md` (MAIL
      complete; NEWS `+0x20`, `+0x60`, `+0x70` still unknown)
- [x] Find what triggers the 39 dialogue categories no EVENT record uses:
      7 season-result speeches (36000–36008) are chosen by the handler
      types 18/19 code; the other 32 aren't referenced anywhere (mostly
      English placeholders over real Japanese text)
- [x] Work out `ESC 0xC3`: the speaker's body reaction in talk scenes, an
      entry index into `HUMAN_MOTION_REACTION_SIT/STAND.MRG` depending on the
      scene's posture (`DOC/MBB_FORMAT.md`)
- [ ] Rename `mbb.py`'s `{c3:N}` tag to something readable (e.g.
      `{react:N}`); changes the CSV output, so re-bless `regress.py`
- [ ] Map variable ids to what fills them (`Msg::VarBuf_*`, `SetVariable` callers)
- [ ] Check whether raw `0x0A`/`0x0D` bytes affect display

## 2. Ninja 3D models and motions

Documented in [`DOC/NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md). `SRC/ninja.py`
checks all 5,392 blobs (138 loose files, 5,254 archive entries) with no
problems, and exports static meshes to OBJ.

- [x] Document the chunk layouts (`DOC/NINJA_FORMAT.md`)
- [x] Add a parser (`ninja.py info`/`dump`) and add it to `regress.py`
- [x] Triangle strips and winding (`strip_triangles()`); `obj` export works
- [ ] Decode the material structs and link textures from `NSTL` (MTL output)
- [ ] Common-vertex lists (`nnCompileCommonVerticesObject*`, 35 lists plus
      the `PLAYER/` face models)
- [ ] PX Plus skin words, VU `0x21` weight remainder, VU type bit `0x100`
- [ ] Camera (`NSCA`/`NSMC`) and light (`NSLI`) chunks; submotion
      interpolation types
- [x] Run `ninja.py info DAT --prs` over the PRSH-compressed entries
      (8,762 blobs, no problems)
- [ ] Skinned export (glTF with skeleton and motions)

## 3. `DAT/PLAYER/`

The largest directory (1.2 GB). `pac.py` covers the containers (KC@P face
packs, uniform CLUT packs, `CUTINHUMANPACK.MRG`, ...), but what the entries
hold (player models, faces, edit/uniform data) is undocumented.

- [x] Survey the entry types: the KC@P packs (faces, `PLPACK_*` kits,
      `EDITFACEPACK`) wrap each entry in `etc::PackData`; everything else is
      Ninja models or textures
- [x] Write `DOC/PLAYER_DIR.md`
- [x] `SRC/packdata.py` parses `etc::PackData` in all 5 KC@P packs; `info`
      samples `FC_EURO_FACEPACK_00` (`--all` for every entry). In `regress.py`
- [ ] `GAME/CUTINPACK.BIN` entries are `PackData` too (block types 19–24);
      reconcile with `PAC_FORMAT.md`'s "109 are empty" and document the blocks
- [ ] Decode the face block-4 header and the `PLPACK` block-0 kit descriptor
- [ ] `COLOR_TBL`, `UNIFORM_LIST`, `UNIFORM_GK` table layouts
      (`UniformList_*` at `0x2d3078`)

## 4. Music and sound effects

- [x] `SOUND/*.DAT` (all 28 files) are each one `ps2_DTPK` bank covering the
      whole file; `sounddat.py dtpk` parses them all
- [ ] Listen to the decoded WAVs to confirm the audio is right, and document
      `SOUND/` (which scene each `MAP01`–`MAP23` belongs to; `MAP11`–`MAP23`
      hold only 2 samples each)
- [ ] Add `sounddat.py dtpk` over `SOUND/*.DAT` to `regress.py`
- [ ] `.SQB` sequences (19 files in `SEQ/`)

## 5. Housekeeping

- [x] Regression check: `SRC/regress.py` runs every tool's `info` over `DAT/`
      and fails on any difference from a saved baseline
- [x] One problem marker (`!!`) in every `info`; `regress.py` lists appeared
      and vanished `!!` lines, and both need review
- [x] `mbb.py info` and `pac.py info` report a truncated file as `!!` and
      keep scanning, like the other tools
- [x] `regress.py` checks `evsdatabin.py --text MES.PAC` for all three tables
      (2,879 message references, all resolved)
- [x] `sles_disasm.py` labels the 323 relocated sites (169 `jal 0`,
      HI16/LO16, data words) with their import names; `relocs` lists them
- [ ] `EMBLEM/EDIT_EMBLEM.TBB` t93/101/105: 143-byte tables whose record size
      is unknown (`TBB_FORMAT.md` has "?"). The only `!!` on the disc with
      no documented cause
