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
- [ ] Name the remaining EvsDataBin columns: NEWS `+0x20`, `+0x60`, `+0x70`,
      and the EVENT `+0x68` timing enum (values 0–21, scan at `0x12df08`)
- [ ] Map variable ids to what fills them (`Msg::VarBuf_*`, `SetVariable` callers)
- [ ] Check whether raw `0x0A`/`0x0D` bytes affect display

## 2. Starting season and parameter tables (`PARAM/`, `0SYSTEM/`)

The first thing [`GOALS.md`](GOALS.md) wants a mod to change. Every table
parses with `tbb.py`, but no folder doc says what the tables and packs hold
or which code loads them.

- [x] Write `DOC/PARAM_DIR.md`: each file's loader, row count and record size.
      Loaders found for all but `SPONSOR_BOARD.TBB` and `UNIFORM_NAME*.BIN`
      (nothing names them). Record layouts confirmed for `OTEAMMEMBER`,
      `PLRRSRC_INITTEAMDATA`, `INITNATIDATA`, `SCHEDULE_LIST`, `REGULATION`,
      `CLUBRESULT` and `STADIUM_DATA`, plus the `plResource` pack readers
- [ ] Schedules and competitions: `0SYSTEM/SCHEDULE.TBB`,
      `SCHEDULE_LIST.TBB`, `SCHEDULE_{COMPETITION,SYSTEM,TEAM_ENTRY}.PAC/.HED`,
      `GROUP2COMPE.TBB`, `REGULATION.TBB`, `CLUB_RANK_SYSTEM.TBB`
- [ ] Initial clubs, squads and stadiums: `PLRRSRC_INITTEAMDATA.TBB`,
      `INITNATIDATA.TBB`, `OTEAMMEMBER.TBB`, `MAPTEAM_LIST.TBB`,
      `STADIUM_DATA.TBB`
- [ ] The packs: `PLRESOURCE{COMMON,SIM}.PAC`, `PBDATA_{EU,JP}.PAC`,
      `PSC{COMMON,GAME,PRACTICE}.PAC`
- [x] `UNIFORM_NAME.BIN` and `UNIFORM_NAME2.BIN`: 27,950 × `char[19]`
      placeholders (`"a"`, or `"0"` in 142 records of `UNIFORM_NAME2`), not
      referenced by name (`DOC/PARAM_DIR.md`)
- [ ] Write `DOC/0SYSTEM_DIR.md`: `COLORDATATABLE`, `DETAILFLAG` and
      `MSGCOMMON` tables, the texture packs and fonts, `SAVE_VERSION.DAT`,
      `STATIC*.ICO`

## 3. Ninja 3D models and motions

Documented in [`DOC/NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md). `SRC/ninja.py`
checks all 8,822 blobs (loose files, archive entries and KC@P pack blocks)
with no problems, and exports textured static meshes to OBJ.

- [x] Document the chunk layouts (`DOC/NINJA_FORMAT.md`)
- [x] Add a parser (`ninja.py info`/`dump`) and add it to `regress.py`
- [x] Triangle strips and winding (`strip_triangles()`); `obj` export works
- [x] Material texture references (`0x400`/`0x800` inline layers,
      `0x1000` PX Plus layers); `obj` writes `.mtl` and PNG textures
- [ ] Material colours, GS register words and layer flag bits (reflection
      maps on the trophies), and where textures for models without `NSTL`
      come from (stadiums, balls)
- [x] Common-vertex lists (`nnCompileCommonVerticesObject*`): the face and
      head models; `obj` exports them
- [x] Export the face packs' own textures (sibling SVM blocks in the same
      `etc::PackData` entry); `obj` takes `info` labels for archive entries
- [ ] Hair tint: the hair textures are grey patterns, probably coloured
      from `COLOR_TBL`
- [ ] PX Plus skin words, VU `0x21` weight remainder, VU type bit `0x100`
- [x] Camera (`NSCA`/`NSMC`, one per pre-rendered background) and light
      (`NSLI`) chunks
- [ ] Submotion interpolation types (`0x20002`, `0x20004`, `0x20200`)
- [x] Run `ninja.py info DAT --prs` over the PRSH-compressed entries and
      the face packs (54,051 blobs, no problems)
- [x] Skinned export: `gltf` writes glTF with skeleton, skin weights
      (VU, PX Plus and common-vertex lists), textures and baked motions;
      checked by posing the result (players, background humans, test models)
- [ ] Which part files make up each in-game player (skeleton
      `LMS_PLAYER.SNP` + body/limb `.snq` parts + face pack head), so a
      complete player can be exported in one go
- [ ] Bind face-pack heads to the player skeleton (they bring their own
      19-node head skeleton; match nodes by name through `NSNN`?)

## 4. `DAT/PLAYER/`

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

## 5. Music and sound effects

- [x] `SOUND/*.DAT` (all 28 files) are each one `ps2_DTPK` bank covering the
      whole file; `sounddat.py dtpk` parses them all
- [ ] Listen to the decoded WAVs to confirm the audio is right, and document
      `SOUND/` (which scene each `MAP01`–`MAP23` belongs to; `MAP11`–`MAP23`
      hold only 2 samples each)
- [ ] Add `sounddat.py dtpk` over `SOUND/*.DAT` to `regress.py`
- [ ] `.SQB` sequences (19 files in `SEQ/`), with `SQBFILENAME.TBB`,
      `GLOBALMEMORY.TBB` and `INFORMATION.WPX`

## 6. Files and folders nobody has looked at

Needed for the [coverage goal](GOALS.md#coverage-of-datacvm): nothing left as
"unknown binary".

- [ ] `ACROBATA/ACROBATAPACKFILE.PAC` (the folder is marked "not studied")
- [ ] `STADIUM/*.PRI` (10 files, one per stadium variant) and the 24
      `STADIUM/` tables (`AUD_SET_*`, `BUILD_*`, `ADVERTISE_MODELPACK`, ...)
- [ ] `GAME/` tactics AI: `PLAYBOOK.BPB`, `COMBINATION.BPB`,
      `COMBINATION2.CBB/.CSB` (`fb::PlayBookData`, `fb::Combination`)
- [ ] `GAME/GAMEDATA.BIN` (loaded by `GAMEPRG.REL`) and `GAME/AI_PARAM.BIN`
      (467 f32, not referenced by name)
- [ ] `TEST3D/SHADOWCOLLI.LBI` and `BG/HUMANID.BIN` (no doc mentions them)
- [ ] Folder docs for `EMBLEM/`, `NEWS/`, `PRELOAD/`, `SOUND/`, `STADIUM/`,
      `SEQ/`, `ACROBATA/` and `TEST3D/`, plus a note on the `CVS/` metadata

## 7. Event system and game code

The event tables, the procedures and the overlay loader are documented in
[`DOC/EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
[`DOC/EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md) and
[`DOC/SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md).

- [x] The SN DLL loader (`snDllLoaded`) and `SLES_541.51`'s own SNR2
      header, import symbols and relocations
- [x] Which overlay each of the 132 sequencer modules lives in, and the
      overlay file table; `netprg`/`debugprg` are never loaded
- [x] The wild-card module (70): events opening a management screen
- [x] EVENT scene types: open a screen, start a talk, or chain an event
- [x] Talk types → talk managers, and which events and procedures set them
- [x] Event ID types (1 EVENT, 2 MAIL, 3 NEWS, 4 procedure) and the request
      API
- [x] Procedures 9–29: mails, what starts them, what follows
- [x] Procedure 28's squad and loan limits (8 minimum, 24 maximum, 5 loans)
- [x] Scout-list search criteria for players, youth, coaches and managers,
      with the option texts (category 590) and the 13 region names
- [ ] The unit of the event clock (`0x12e5a8`), so how long a procedure step
      or a scout search takes
- [ ] Request fields `+0x0C` (always 4 for procedure steps) and the
      `0x12c058` argument (1, 6, 7, 8, 21)
- [ ] How `0x260590` decides a player is available for loan
- [ ] Which instruction-age byte is which, which tactical approach is which
      half of the manager-style grid, and what the 25 manager styles
      (`+0x34`) and coach kinds 5 and 6 are
- [ ] Which screens start procedures 9, 14/16/18, 22 and 28, and how
      procedure 9 chooses between 10 and 12
- [ ] Where the overlay index passed to `0x10babc` comes from, and what SNR2
      header fields `0x20`/`0x24`/`0x38` tell the caller
- [ ] Whether anything starts module 69 (the `TESTPRG` launcher) or the test
      modules at 71–129; their viewers could be useful for modding

## 8. Housekeeping

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
- [ ] Start the write stage with `tbb.py`: a writer that round-trips every
      `TBB1`/`TBL1` file byte for byte, checked in `regress.py`
- [ ] Update the `PLAYER/` row in `GOALS.md`'s coverage table:
      `etc::PackData` is now parsed by `packdata.py`
