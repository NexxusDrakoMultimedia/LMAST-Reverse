<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# TODO

The sections group the open items by area. Finished items move to
[`DONE.md`](DONE.md), under the same section numbers.

## Next up

What to work on next, most valuable first. Each line points to the full
item in its section below.

1. **The editor GUI** (section 11). `SRC/editor.py` has its People tab
   (the player database, tested in PCSX2) and Clubs tab (club records and
   squads). Next: test a Clubs edit in PCSX2, then the new club
   (`teaminit.py`), kits and text tabs, and building a disc from the
   editor.
2. **Name the rest of the player fields** (section 2). The editor can only
   offer a field once it has a name and a range (stage 2 in
   [`GOALS.md`](GOALS.md)).
3. **What each PwkScript computes** (sections 2 and 7). The formulas
   behind player points, spectators, season tickets and popularity, so a
   script edit could be tested in PCSX2.
4. **Export a complete in-game player** (section 3). One model from the
   skeleton, the body and limb parts and the face-pack head, so the
   model work gives a usable result.
5. **Archive repacking** (section 9). `MES.PAC` and the `.HED` copies,
   KC@P packs and PRS recompression. Larger mods need these to get their
   edits onto a disc.
6. **The `GAME/` tactics AI files** (section 6). The play books, the
   combination scripts and `GAMEDATA.BIN`'s container are decoded
   (`BPB_FORMAT.md`, `GAMEDATA_FORMAT.md`); what's left is field meanings:
   the `.CBB` records, the 29 combination commands and `GAMEDATA.BIN`'s
   records. These are still the lead for the player fields in #2.

## 1. Message text (`DAT/MESSAGE/MES.PAC`)

The format is decoded: see [`DOC/MBB_FORMAT.md`](DOC/MBB_FORMAT.md) and
`SRC/mbb.py`. All 3,738 files and 66,102 messages parse, in 7 language slots.

- [ ] Name the remaining EvsDataBin columns: NEWS `+0x20`, `+0x60`, `+0x70`
- [ ] Message variable leftovers: which player, team or number the
      screen-set global variables (1100-1104, the 3000s) hold on each
      screen, and how variables 35 and 0 outside category 1 are filled
- [ ] Check whether raw `0x0A`/`0x0D` bytes affect display

## 2. Starting season and parameter tables (`PARAM/`, `0SYSTEM/`)

The first thing [`GOALS.md`](GOALS.md) wants a mod to change. Every table
parses with `tbb.py`, and [`DOC/PARAM_DIR.md`](DOC/PARAM_DIR.md) gives each
file's loader and size. The starting leagues, squads, schedules and player
database are decoded and editable (`initteam.py`, `schedule.py`,
`pbdata.py`); `0SYSTEM/` is surveyed in
[`DOC/0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md).

- [ ] Still open from the schedules: `GROUP2COMPE.TBB`, `CLUB_RANK_SYSTEM.TBB`
      tables 0, 1 and 4 (tables 2 and 3 are the club ranking, `SAVE_FORMAT.md`),
      `PeriodName.tbb`, the `make_list` source functions, game bits `w0`
      8–9 and competition header bytes `0x0A`–`0x0F`
- [ ] Still open: club-record bytes `0x0b`-`0x0d`/`0x0f`, the reader of
      `MAPTEAM_LIST`, and `PLRRSRC_INITTEAMDATA` table 2's negative values
- [ ] `TEAM_INIT_DATA` leftovers: the candidate lists' "List criteria"
      (7 Training cycle) and H.Dale's salary showing 80,000 not 75,000
- [ ] Player fields still open: `+0x43`–`+0x46` (no reader found), what
      the match AI does with its player parameters (the map from fields
      to parameters is done; `f_66` is parameters 128–138, ball touch
      139, dribble style 140), where abilities 59–63 are used (not in the
      match record), and which attack pattern letter is which.
      Lead: the AI's data tables that index parameters (`0x146560` reads
      the play styles that way)
- [ ] Kit style leftovers: what `+0x5a` is (3 showed no hat), what sets
      `plGi +0x1f538` (outfield gloves; a night match didn't)
      (`DOC/PBDATA_FORMAT.md#kit-style`)
- [ ] Staff fields neither developers' editor labels: manager `+0x18`,
      `+0x20` (a serial number), `+0x26`, `+0x2a`-`+0x2e`; scout `+0x1c`,
      `+0x20`, `+0x24`; and what the 25 manager policies (`+0x34`), the
      policy ranges and the 1-5 tactical leanings do
      (`DOC/PBDATA_FORMAT.md#the-developers-staff-editors`)
- [ ] What sets job 5 when a manager is hired, and how coaches and former
      players become managers (`pwkTeam_*CoachJobChangeWork`, PlPinfo
      `+0x210`). (The "Assistant Coach" title and the forwards/defence
      split are confirmed on screen.)
- [ ] `PLRESOURCESIM` leftovers: season numbers, entry 4's 8 clubs per
      nation, entry 7's groups and counter, entry 6 in full; writers for
      the streams (5, 11-14). User reports: weathers are sunny, overcast,
      rain, snow; combinations are hidden in game
- [ ] Tutorial skip leftovers: check other leagues (the switch calls
      `pwkLg_Init(0)`), and whether the rest of the playoffs' skipped
      `Sche.YearEnd`/`Sche.MonthEnd` (club-rank year end,
      `pwkTeam_ChangePop_Year`) changes anything
      (`DOC/SQB_FORMAT.md#the-supplier-and-the-clubs-status`)
- [ ] National team leftovers: what `_getNationalTeamPoint` (`0x227200`)
      scores, team 465 (the Netherlands national team, `PLRESOURCECOMMON` 3.3) and
      `PlPinfo +0x20c` flag `0x300` in the call-up
      filter, and which clubs teams 442-459 are
      (`DOC/PBDATA_FORMAT.md#national-team-call-ups`)
- [ ] Test in PCSX2: a renamed fixed national player (26,046 as
      `NT.Terry.VS`, disc `LMAST-nt-test.iso`) should not show in a career
      call-up of England; the club Terry should
- [ ] Test in PCSX2: a main-position change with `pbdata.py --sles` on its
      own (rank edits are tested; position goes through the same table)
- [ ] `PLRESOURCECOMMON.PAC` leftovers (`DOC/PLRESOURCECOMMON_FORMAT.md`):
      the first words of each facility record and the code that charges
      the build cost, the rest of the stadium record, the values in
      entries 1 (formations), 2 (hexagon) and 4 (combination growth, cup
      ids), and which messages name the facilities
- [ ] The packs `PSC{COMMON,GAME,PRACTICE}.PAC` are PwkScript scripts,
      decoded in `DOC/SQB_FORMAT.md`; what each one computes is still open
      (section 7)
- [ ] `0SYSTEM` leftovers: what the `DETAILFLAG` flags switch (only the
      first 99 of 528 bytes are read), which UI element uses each colour,
      who the `V001`-`V032` crests are, whether `SPONSOR_TEXTURE_M`
      (type 6) is used at all, and what `CDetailTeamFlag` (the only
      `FLAG_TEXTURE` request) draws; probably nationality flags

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
- [ ] Still open in the kit tables: side fields 0/1/2/5, the 3-bit flag,
      descriptor bytes 14-15 (kit fields 4 = collar, 12/13 = number
      colours, 14 = captain mark and side fields 3/4 = front number,
      shorts number position are now named)
- [ ] `UNIFORM_GK` leftover: whether screens outside a match show your
      club's stored keeper kit rather than the `UNIFORM_GK` one

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
- [ ] `GAME/` tactics AI leftovers (`DOC/BPB_FORMAT.md`): the
      `COMBINATION2.CBB` record fields and the 29 combination commands
      (callbacks at `GAMEPRG.REL 0x249280`); in the play books the path
      kinds, point codes, which play is which, the `+0x20` block and
      `GetFormationData`
- [ ] `GAME/GAMEDATA.BIN` leftovers (`DOC/GAMEDATA_FORMAT.md`): what a
      record is (4,131 of 0x30 bytes), its fields past `+0x4`, `+0x8`,
      `+0x14`, `+0x20`, and who calls the record functions at
      `GAMEPRG.REL 0x13abb8`; whether anything reads `AI_PARAM.BIN`
- [ ] `TEST3D/SHADOWCOLLI.LBI` and `BG/HUMANID.BIN`. The `.LBI` starts
      like the 27 entries of `GAME/SHADOWCOLLI.PAC` but matches none and
      isn't named in the code (`DOC/TEST3D_DIR.md`); decode the format
      with the `GAME/` pack, and `GAME/WALLCOLLI.PAC`'s entries with it
      (both loaded into `CStadiumCollision`, `DOC/STADIUM_DIR.md`)
- [ ] `GAME/TEAM.TMB` (`TMB1`: team names, codes, stadiums; dated March
      2005 and not named in the code, `DOC/GAME_DIR.md`): parse it and
      confirm nothing reads it
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
- [ ] How the instruction-age screen rows map to values 1-4 (the editor's
      labels suggest 1 = 16-22 ... 4 = youth), and which tactical approach
      is which half of the manager-policy grid
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
- [ ] Try the launcher entries not yet recorded: YAMAZAKI TEST, Talk and
      BG LIGHT TEST (`DOC/SQB_FORMAT.md#the-developer-launcher`)
- [ ] Sequencer leftovers: Base 35, RootEvent `Root9`/`Root13`, Param 7,
      8, 21, 25, 29, the `SQT1` flag and 2-D indexing, `BranchIf` vs
      `JumpIf`; the command sets of `INFORMATION.SQB`/`CHECKCLUBEDIT.SQB`;
      `INFORMATION.WPX`
- [ ] Game-flow leftovers (`DOC/GAME_FLOW.md`): which `Sche.YearEnd`
      value is which ending or game over, how PlayAcrobata maps its
      argument (3, 4, 5, 7–10, 13–17) to a scene, the Dummy module with
      argument 15 at turn start, and whether the Option module's save is
      the one that loads as result 1
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
- [ ] Test in PCSX2: a `PRELOAD` pack that a rebuild moves (the code path
      is the same as a moved file, but untested in game)
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
- [ ] Finance leftovers: the code that reads the per-type names
      (category 550 messages 217-251), the season plan's `+0x14` and
      `+0x16`, and where the plan window checks its limits (they're from a
      user report so far)
- [ ] Candidate list leftovers: the rest of the 32-byte player
      candidate record, the first u32 of the staff candidate records, and
      what the youth join limit of 4 (`pwkTeam_GetYouthPlayerMax`) counts
- [ ] Other clubs and staff leftovers: the untraced club record bytes
      (`+0x9b`, `+0xa1`, `+0xa6`-`+0xa7`), the non-resident clubs (442 on),
      the first u32 of PlMinfo/PlSinfo, PlSinfo `+0x64`-`+0x8f`, and how
      far the manager's popularity goes in play (0 in every save)
- [ ] Club rank leftovers (no editor fields): when in the season the
      ranking runs, which competitions `0x22`-`0x24` lower the status rank,
      what changes the status after a match (`0x26ddd8`), the three
      weighted values behind the world rank points (`SIMPRG.REL
      0x151568`), and whether the reputation limits the players an AI club
      signs (the community account)
- [ ] The manager's Special Mention texts for dissatisfaction kinds 0-3
      (kind 4 shows "Won't tolerate club's facilities."), to confirm their
      names. A save edit per kind would show each one
- [ ] `info.bin` past the date, `dm.bin`, and the VS data (`-C`, same
      key, layout CRC `0x8ffb`)

## 11. Editor GUI

Stage 5 of [`GOALS.md`](GOALS.md): GUI tools on top of the writers,
organised by what a player of the game recognises (a player, a club, a
season) rather than by file. `tkinter` only, as the principles there say,
and every GUI edit must also be possible as a `python SRC/...` command.

- [ ] The player's new club (`teaminit.py`), kits (`uniform.py`), message
      text (`mbb.py`)
- [ ] Test in PCSX2: a Clubs-tab edit (a squad slot's player, age and
      shirt; a club's rank, manager and stadium) shows in game
- [ ] Build a modded disc from the GUI: collect the edited files, run
      `patch_disc.py` with `--copies`, and optionally make an xdelta
      patch with `vcdiff.py`
