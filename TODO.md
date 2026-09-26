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
- [x] Rename `mbb.py`'s `{c3:N}` tag to `{react:N}` (no baseline used it)
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
- [x] Schedules and competitions: `DOC/SCHEDULE_FORMAT.md` and
      `SRC/schedule.py` (in `regress.py`) cover the three `SCHEDULE_*` packs
      for all 164 UIDs. `SCHEDULE_LIST` and `REGULATION` are indexed by
      the same UID, and `0SYSTEM/SCHEDULE.TBB` is an unreferenced 2005 version.
      One `!!`: UID 117 has 6 game days but 3 turns
- [ ] Still open from the schedules: `GROUP2COMPE.TBB`, `CLUB_RANK_SYSTEM.TBB`,
      `PeriodName.tbb`, the `make_list` source functions, game bits `w0`
      8–9 and competition header bytes `0x0A`–`0x0F`
- [x] Initial clubs and squads: `PLRRSRC_INITTEAMDATA.TBB` (divisions, last
      season's order) and `OTEAMMEMBER.TBB` (player, age, shirt, contract),
      with club names from `MES.PAC` category 3 (`DOC/INITTEAM_FORMAT.md`,
      `SRC/initteam.py`)
- [x] The rest of the starting data: the 24-byte club record (rank, world
      rank, manager, stadium, transfer policy, money, city), `INITNATIDATA`
      (UEFA rank/points, world rating), `STADIUM_DATA` (roof, level,
      capacity), `MAPTEAM_LIST` (flag = real 2005/06 top divisions);
      `initteam.py teams/nations/stadiums/setteam`
- [ ] Still open: club-record bytes `0x0b`-`0x0d`/`0x0f`, the reader of
      `MAPTEAM_LIST`, and `PLRRSRC_INITTEAMDATA` table 2's negative values
- [x] Player database `PBDATA_EU.PAC`: bit-packed records for 27,950
      players, 3,000 managers and 1,000 scouts, field widths from
      `plBits_DecPl{P,M,S}baseEx` (`DOC/PBDATA_FORMAT.md`, `SRC/pbdata.py`);
      `initteam.py squads` names the players
- [x] Detail-screen bars from the abilities: the 14 player bars and the
      hexagon (`ConvertPlayer_Bar`, `plPinfo_CalcHexagon`), the manager and
      coach bars (`CalcManagerAbil`, by job) and the scout bars
      (`ConvertScout`); player `leg` and staff `job` named
      (`DOC/PBDATA_FORMAT.md`)
- [x] Position numbering and aptitude: the 13 pitch-grid cells
      (`plPinfo_CalcAptPos`); abilities 33–44 are position aptitudes; the
      grid levels match two in-game screenshots of Terry
- [ ] Name the rest of the player fields: skill bits (probably the style
      icons), money band, abilities 45–63, entry 2, and whether hexagon 0
      or 3 is Skills/Attacking
- [ ] What separates staff jobs 0–2, and the code that switches a hired
      manager to job 5
- [ ] The packs: `PLRESOURCE{COMMON,SIM}.PAC` (entries not listed in
      `PARAM_DIR.md`) and `PSC{COMMON,GAME,PRACTICE}.PAC`
- [x] `UNIFORM_NAME.BIN` and `UNIFORM_NAME2.BIN`: 27,950 × `char[19]`
      placeholders (`"a"`, or `"0"` in 142 records of `UNIFORM_NAME2`), not
      referenced by name (`DOC/PARAM_DIR.md`). 27,950 is the player count,
      so they are probably one kit name per player
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
- [x] Add `sounddat.py dtpk` over `SOUND/*.DAT` to `regress.py` (one check
      per file; each is a single bank filling the whole file)
- [ ] `.SQB` sequences (19 files in `SEQ/`), with `SQBFILENAME.TBB`,
      `GLOBALMEMORY.TBB` and `INFORMATION.WPX`

## 6. Files and folders nobody has looked at

Needed for the [coverage goal](GOALS.md#coverage-of-datacvm): nothing left as
"unknown binary".

- [ ] `ACROBATA/ACROBATAPACKFILE.PAC` (the folder is marked "not studied")
- [x] `STADIUM/*.PRI`: 44 × u32 part draw priorities per model, drawn in
      two passes (0–49, 50–100). `DOC/STADIUM_DIR.md`, `SRC/stadium.py`
      (in `regress.py`)
- [x] The 24 `STADIUM/` tables: `BUILD_STADIUM` (model, part switches,
      crowd set, advert textures), `CONV_INFO_BUILD` (stadium id by level),
      `BUILD_ADVERTISE` (board types and switches), `AUD_SET_*` (18 crowd
      sets: sections, tiers, blocks), `AUD_JAM_*` (fill thresholds); all
      checked by `stadium.py info`
- [x] `STADIUM/` unknowns: the 44 `.PRI` part slots and which
      `BUILD_STADIUM` bytes switch them; bytes 110–114/128 (shadow and wall
      collision in `GAME/`); table 2 (stand node lists); `AUD_SET` tier rows
      and the high-detail tier count; the lighting-variant and sky choice;
      `CONV_INFO_BUILD` = `plTeam_GetStadiumDataIndex` (league, level,
      stand/roof/lights)
- [ ] Still open in `STADIUM/`: what sets the night flag (request `+0x88`,
      `N2` over `N1`), request byte `+7`, the crowd block and tier flags
- [ ] `GAME/` tactics AI: `PLAYBOOK.BPB`, `COMBINATION.BPB`,
      `COMBINATION2.CBB/.CSB` (`fb::PlayBookData`, `fb::Combination`)
- [ ] `GAME/GAMEDATA.BIN` (loaded by `GAMEPRG.REL`) and `GAME/AI_PARAM.BIN`
      (467 f32, not referenced by name)
- [ ] `TEST3D/SHADOWCOLLI.LBI` and `BG/HUMANID.BIN` (no doc mentions them)
- [ ] Folder docs for `EMBLEM/`, `NEWS/`, `PRELOAD/`, `SOUND/`,
      `SEQ/`, `ACROBATA/` and `TEST3D/`, plus a note on the `CVS/` metadata
      (`STADIUM/` done: `DOC/STADIUM_DIR.md`)

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
- [x] `EMBLEM/EDIT_EMBLEM.TBB` t93/101/105: 12-byte records, but record 4
      is missing its `04 00` index, so each table is a byte short
      (`TBB_FORMAT.md`). The reader in `CEDITPRG.REL` is still unfound
- [x] Start the write stage with `tbb.py`: `build()` round-trips all 70
      `.TBB`/`.BCR`/`.BCB` files byte for byte (`roundtrip`, in
      `regress.py`); `replace` puts an edited table back
- [ ] Decode the `RBD0` trailer in `GAME/ROUTEBOX_*.BCR` (copied as-is by
      the writer)
- [x] `pbdata.py` writer: all 31,950 records re-encode and the pack
      rebuilds byte for byte (`roundtrip`, in `regress.py`); `set` and CSV
      `import` edit players, managers and scouts
- [x] Update the `PLAYER/` and `PARAM/` rows in `GOALS.md`'s coverage table

## 9. Rebuild

Stage 4 of [`GOALS.md`](GOALS.md): getting edits back onto a bootable disc.
See [`DOC/REBUILD.md`](DOC/REBUILD.md).

- [x] Same-size in-place patching: `SRC/patch_disc.py` writes edited files
      into the disc image, `DATA.CVM` or `DATA.ISO` without touching the
      encrypted table of contents; `locate` in `regress.py`. Tested byte-exact
      (12 bytes changed for a 3-field player edit, and reverting gives the
      Redump image back)
- [x] Boot a patched image in PCSX2 and confirm the edit shows in game:
      Terry's edited name, weight, leg and bars appeared in a new game.
      His height wrapped at 255 (a byte in `PlPbase`) and his age comes
      from `OTEAMMEMBER.TBB`; both now handled (`initteam.py set`)
- [x] Copies: `patch_disc.py copies` and `patch --copies` index `DAT/`
      (files, headers, entries) and update same-named copies (325 loose
      files have one, e.g. `REGULATION.TBB` in all seven `SIMFILE` packs;
      193 `.HED` headers; 763 `MES.PAC` entries); `path#entry` targets
- [ ] Which copy the game actually reads in each mode (loose file or
      `PRELOAD` pack), so `--copies` can be narrowed
- [ ] Size changes: re-lay `DATA.ISO`, rewrite directory records,
      re-encrypt the table of contents, fix the `CVMH`/`ZONE` lengths and the
      disc's `DATA.CVM` entry
- [ ] BINPAC/KC@P repacking and PRS recompression for entries that change size
- [x] xdelta patches: `SRC/vcdiff.py` makes and applies VCDIFF (RFC 3284)
      in plain Python; the Terry mod is a 10,642-byte patch that applies to
      a byte-identical image
- [x] Confirm a `vcdiff.py` patch applies with xdelta UI or DeltaPatcher:
      Delta Patcher's output matches `vcdiff.py apply` byte for byte (it
      needs the uncompressed ISO, not a CSO)
- [ ] Optional: let `vcdiff.py`/`patch_disc.py` read CSO (and CHD) images,
      which many players keep instead of ISOs
- [x] `patch_disc.py` patches files outside `DATA.CVM` (`disc:SLES_541.51`)

## 10. Save data

See [`DOC/SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md).

- [x] Encryption (Blowfish, key `sakatsukue`), header, layout CRC; no
      checksum over the contents
- [x] Decode and re-encode the ten Pwork blocks by running `SAVEPRG.REL`'s
      own serializers (`SRC/save.py`); all 5 test saves round-trip byte for
      byte
- [x] Money, date and the squad (id, name, position, age, 64 abilities)
- [x] Editor start: `save.py set` for money and squad abilities
- [x] Separate saves for a modded disc: `save.py serial` (e.g.
      `PYRA-31396`; the VS data `-C` moves too, as anti-cheat against
      Virtua Pro Football, while its `FASYS` import save stays) and `rename`
- [x] Confirm in game: an edited save loads with the new money and
      abilities (money shows ÷ 6 in pounds: `plMisc_MoneyRate`)
- [x] PCSX2 reads the serial from `SYSTEM.CNF`'s boot file, so `serial`
      also renames the executable (`PYRA_313.96`) and `patch_disc.py
      --rename` rewrites its ISO9660 and UDF directory entries
- [ ] Confirm in game: the renamed disc shows as PYRA-31396 and saves to
      `BEPYRA-31396-Gnnn`
- [ ] Which rate slot is which currency (the option screen's code)
- [ ] The second value of each ability triplet; the rest of PlPinfo
      (contract, condition, injuries, stats)
- [ ] Map more of the blocks through their accessors (staff, youth, other
      clubs, finances), and name the fields an editor should offer
- [ ] `info.bin` past the date, `dm.bin`, and the VS data (`-C`, same
      key, layout CRC `0x8ffb`)
- [ ] Faster decoding: record the serializers' field list once instead of
      interpreting them on every run (about 8 seconds a save now)
