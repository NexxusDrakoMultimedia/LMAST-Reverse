<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# TODO

The sections group the open items by area. Finished items move to
[`DONE.md`](DONE.md), under the same section numbers.

## Next up

What to work on next, most valuable first. Each line points to the full
item in its section below.

1. **Name the rest of the player fields** (section 2). The editor can only
   offer a field once it has a name and a range (stage 2 in
   [`GOALS.md`](GOALS.md)).
2. **`PLRESOURCECOMMON.PAC` and what each PwkScript computes** (sections 2
   and 7). This is the largest piece of starting-season data still undecoded.
3. **Size changes on the disc** (section 9). Until files can move, an edit
   can only grow to the end of its last sector, which limits every writer.
4. **The tutorial skip's supplier** (section 2). Find the condition that
   gives a normal career Egamucho instead of Doclla, so the skip disc
   matches a played-through start.
5. **Read the root scripts as the game's flow chart** (section 7). Knowing
   which `Root*Seq` runs what, and in which order, would have found the
   sponsor bug in minutes.

## 1. Message text (`DAT/MESSAGE/MES.PAC`)

The format is decoded: see [`DOC/MBB_FORMAT.md`](DOC/MBB_FORMAT.md) and
`SRC/mbb.py`. All 3,738 files and 66,102 messages parse, in 7 language slots.

- [ ] Name the remaining EvsDataBin columns: NEWS `+0x20`, `+0x60`, `+0x70`,
      and the EVENT `+0x68` timing enum (values 0–21, scan at `0x12df08`)
- [ ] Map variable ids to what fills them (`Msg::VarBuf_*`, `SetVariable` callers)
- [ ] Check whether raw `0x0A`/`0x0D` bytes affect display

## 2. Starting season and parameter tables (`PARAM/`, `0SYSTEM/`)

The first thing [`GOALS.md`](GOALS.md) wants a mod to change. Every table
parses with `tbb.py`, and [`DOC/PARAM_DIR.md`](DOC/PARAM_DIR.md) gives each
file's loader and size. The starting leagues, squads, schedules and player
database are decoded and editable (`initteam.py`, `schedule.py`,
`pbdata.py`); `0SYSTEM/` is surveyed in
[`DOC/0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md).

- [ ] Still open from the schedules: `GROUP2COMPE.TBB`, `CLUB_RANK_SYSTEM.TBB`,
      `PeriodName.tbb`, the `make_list` source functions, game bits `w0`
      8–9 and competition header bytes `0x0A`–`0x0F`
- [ ] Still open: club-record bytes `0x0b`-`0x0d`/`0x0f`, the reader of
      `MAPTEAM_LIST`, and `PLRRSRC_INITTEAMDATA` table 2's negative values
- [ ] `TEAM_INIT_DATA` leftovers: the candidate lists' "List criteria"
      (7 Training cycle) and H.Dale's salary showing 80,000 not 75,000
- [ ] Name the rest of the player fields: money band (lead: BPINFO CHECK
      calls band value 10,000 "1mil"), entry 2, the bit fields `+0x30`
      to `+0x5d` and `+0x66`, abilities 27, 32, 54 and 59–63, and what
      the skills and play styles do in a match. Still open after the
      Taylor and Rooney VPF screenshots: which of 19/20 is pace and of
      57/58 pressing (equal VPF values in both), and whether 54/55 are
      the left and right flanks. A VPF player with a clear left/right
      bias or pace/acceleration gap would settle them
- [ ] User check (PCSX2): give a player play styles with `pbdata.py set`
      (`style.0=7`) and see the detail screen's Play Style plate show
      "Play maker"
- [ ] What sets job 5 when a manager is hired, and how coaches and former
      players become managers (`pwkTeam_*CoachJobChangeWork`, PlPinfo
      `+0x210`). (The "Assistant Coach" title and the forwards/defence
      split are confirmed on screen.)
- [ ] `PLRESOURCESIM` leftovers: season numbers, entry 4's 8 clubs per
      nation, entry 7's groups and counter, entry 6 in full; writers for
      the streams (5, 11-14). User reports: weathers are sunny, overcast,
      rain, snow; combinations are hidden in game
- [ ] Tutorial skip leftovers: the supplier stays Doclla instead of
      Egamucho, even when Doclla's contract ends (Tested in PCSX2). Lead:
      Egamucho's record has condition `0x18` = 500 that the playoffs may
      provide (`DOC/SQB_FORMAT.md#why-the-playoff-sponsors-stayed`). Also
      check other leagues (the switch calls `pwkLg_Init(0)`)
- [ ] Test in PCSX2: a free agent lowered to rank 5 or less shows on a
      new club's Transfer List (`DOC/PLRESOURCESIM_FORMAT.md`)
- [ ] Trace which code builds a national team's squad from players
      26,041-27,949 (83 blocks of 23, one per national team; empirical,
      `DOC/PBDATA_FORMAT.md#player-id-blocks-empirical`)
- [ ] The packs: `PLRESOURCECOMMON.PAC` (readers listed in `PARAM_DIR.md`,
      layouts not decoded). `PSC{COMMON,GAME,PRACTICE}.PAC` are PwkScript
      scripts, decoded in `DOC/SQB_FORMAT.md`; what each one computes is
      still open (section 7)
- [ ] `0SYSTEM` leftovers: what the `DETAILFLAG` flags switch (only the
      first 99 of 528 bytes are read), which UI element uses each colour,
      who the `V001`-`V032` crests are, and whether `SPONSOR_TEXTURE_M`
      (type 6) is used at all

## 3. Ninja 3D models and motions

Documented in [`DOC/NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md). `SRC/ninja.py`
checks all 8,822 blobs (loose files, archive entries and KC@P pack blocks)
with no problems, exports textured meshes to OBJ, and exports skinned,
animated models to glTF.

- [ ] Material colours, GS register words and layer flag bits (reflection
      maps on the trophies), and where textures for models without `NSTL`
      come from (stadiums, balls)
- [ ] Hair tint: the hair textures are grey patterns, tinted from
      somewhere (not `COLOR_TBL`, which is the kit clash table)
- [ ] PX Plus skin words, VU `0x21` weight remainder, VU type bit `0x100`
- [ ] Submotion interpolation types (`0x20002`, `0x20004`, `0x20200`)
- [ ] Which part files make up each in-game player (skeleton
      `LMS_PLAYER.SNP` + body/limb `.snq` parts + face pack head), so a
      complete player can be exported in one go
- [ ] Bind face-pack heads to the player skeleton (they bring their own
      19-node head skeleton; match nodes by name through `NSNN`?)

## 4. `DAT/PLAYER/`

The largest directory (1.2 GB), surveyed in
[`DOC/PLAYER_DIR.md`](DOC/PLAYER_DIR.md). `pac.py` covers the containers and
`packdata.py` the `etc::PackData` entries inside the KC@P packs. Some block
contents and three tables are still undecoded.

- [ ] `GAME/CUTINPACK.BIN` entries are `PackData` too (block types 19–24);
      reconcile with `GAME_DIR.md`'s "109 are empty" and document the blocks
- [ ] Decode the face block-4 header
- [ ] Still open in the kit tables: `UNIFORM_GK`, side fields 0/1/2/5, the
      3-bit flag, descriptor bytes 14-15 (kit fields 4 = collar, 12/13 =
      number colours, 14 = captain mark and side fields 3/4 = front number,
      shorts number position are now named)

## 5. Music and sound effects

- [ ] Which screens play which `bgm` track, and `OPMOVIE.SFD` (Sofdec).
      Lead: the music table (`DOC/SOUND_DIR.md`) maps the 63 music ids to
      `MAP` songs or streams; trace the callers of
      `CFcEuro_ChangeBgm` and what selects the stream archive (`+0x10`)
- [ ] Commentary (`BC_ENG`), tannoy (`JYONAI_A`) and `MAP01` still unheard
- [ ] `SOUND/` leftovers: `MAP06` and `map02` songs 3–5 have no music id;
      `EFFECTS`, `EVENT_SE`, `PACK0` and `TRAINING` aren't named in the
      code. Find out whether anything plays them
- [ ] Closer to the SPU2: the ADSR envelopes (layer `+0xe`/`+0x10`),
      Gaussian interpolation, the driver's pan table, and the game's reverb
      preset

## 6. Files and folders nobody has looked at

Needed for the [coverage goal](GOALS.md#coverage-of-datacvm): nothing left as
"unknown binary".

- [ ] `ACROBATA/` leftovers: the `ABDT` scene layout, `ABRS` header table
      and `+0x14`, which code plays which scene id. A rebuilt pack whose
      entries move needs `SLES 0x3a3b08` patched (no tool does that yet)
- [ ] Still open in `STADIUM/`: which crowd figure group is which on
      screen, who sets request `+0x0e`-`+0x10` in a real match
- [ ] `GAME/` tactics AI: `PLAYBOOK.BPB`, `COMBINATION.BPB`,
      `COMBINATION2.CBB/.CSB` (`fb::PlayBookData`, `fb::Combination`)
- [ ] `GAME/GAMEDATA.BIN` (loaded by `GAMEPRG.REL`) and `GAME/AI_PARAM.BIN`
      (467 f32, not referenced by name)
- [ ] `TEST3D/SHADOWCOLLI.LBI` and `BG/HUMANID.BIN`. The `.LBI` starts
      like the 27 entries of `GAME/SHADOWCOLLI.PAC` but matches none and
      isn't named in the code (`DOC/TEST3D_DIR.md`); decode the format
      with the `GAME/` pack
- [ ] `EMBLEM/` leftovers: the preset records (`EDIT_EMBLEM` t4–t6), the
      110-byte crests (t7–t9, `Param::PlEmblem`?), the layer records and
      their key, `EDIT_FLAG` t1 variants and t2 bytes, all of
      `EDIT_PLAYER.TBB`; whether the 3 short layer tables lose parts in the
      crest editor (a PCSX2 check)
- [ ] `NEWS/` leftovers: which of a league's two papers a page uses, when
      the special editions show, where the ads and cartoons go
- [ ] `TEST3D/`: who reads the executable's test lists (`0x346d20`,
      `0x3472d0`, `0x4b0634`) and calls `CPlayer::ChangeUniform` with the
      six test kits

## 7. Event system and game code

The event tables, the procedures and the overlay loader are documented in
[`DOC/EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
[`DOC/EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md) and
[`DOC/SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md).

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
      modules at 71–129; their viewers could be useful for modding.
      `RootMainSeq` skips `RootLauncherSeq.sqb` because
      `Dummy.CheckLauncher` always returns 1; `sqb.py setcmd
      ROOTMAINSEQ.SQB out 0x98 0:27` flips the test (1 byte,
      `DOC/SQB_FORMAT.md#the-developer-launcher`)
- [ ] Why the blank test modules show nothing: missing data, or waiting
      for input or arguments from the launcher
- [ ] Sequencer leftovers: Base 35, RootEvent `Root9`/`Root13`, Param 7,
      8, 21, 25, 29, the `SQT1` flag and 2-D indexing, `BranchIf` vs
      `JumpIf`; the command sets of `INFORMATION.SQB`/`CHECKCLUBEDIT.SQB`;
      `INFORMATION.WPX`
- [ ] Read the root scripts as the game's flow chart: which modules each
      `Root*Seq` starts, in which order, and on which branch results
      (`python SRC/sqb.py dis`)
- [ ] What each PwkScript computes (`PinfoInit`, `PinfoPoint`,
      `seasonticket`, `spectator*`, `Plpop*`, the `*_syousai_nouryokuMS`
      detail-screen scripts): name the `pwkEdit` value ids they read and
      write. A script edit could then be tested in PCSX2

## 8. Housekeeping

- [ ] Decode the `RBD0` trailer in `GAME/ROUTEBOX_*.BCR` (copied as-is by
      the writer)

## 9. Rebuild

Stage 4 of [`GOALS.md`](GOALS.md): getting edits back onto a bootable disc.
See [`DOC/REBUILD.md`](DOC/REBUILD.md).

- [ ] `TACTICSPITCH.PAC` is loaded through `CLoader`, not as a registering
      resource: whether its entries stand in for their originals
- [ ] Size changes: re-lay `DATA.ISO`, rewrite directory records,
      re-encrypt the table of contents, fix the `CVMH`/`ZONE` lengths and the
      disc's `DATA.CVM` entry
- [ ] Repacking where something else holds the offsets (`.HED` copies,
      `MES.PAC`), KC@P repacking, and PRS recompression
- [ ] Optional: let `vcdiff.py`/`patch_disc.py` read CSO (and CHD) images,
      which many players keep instead of ISOs

## 10. Save data

See [`DOC/SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md).

- [ ] Which rate slot is which currency: pound (2) and euro (3) seen in
      game; 400 presumably the yen (the option screen's code)
- [ ] Stats table 1, PlPinfo flags at `0x20c`, dissatisfaction, style
      icons, and what the 3 records at block 1 `+0xe290` are
- [ ] Map more of the blocks through their accessors (staff, youth, other
      clubs, finances), and name the fields an editor should offer
- [ ] `info.bin` past the date, `dm.bin`, and the VS data (`-C`, same
      key, layout CRC `0x8ffb`)
