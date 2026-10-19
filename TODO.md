<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# TODO

The sections group the open items by area. Finished items move to
[`DONE.md`](DONE.md), under the same section numbers.

## Next up

What to work on next, most valuable first. Each line points to the full
item in its section below.

1. **Archive repacking: tests in PCSX2** (section 9). Every archive
   kind can now be rebuilt (`MES.PAC`, `.HED` archives, the Acrobata
   pack, KC@P packs, PRS); none of these rebuilds has been seen in game.
2. **The `GAME/` tactics AI files** (section 6). The play books, the
   combination scripts and `GAMEDATA.BIN`'s container are decoded
   (`BPB_FORMAT.md`, `GAMEDATA_FORMAT.md`); what's left is field meanings:
   the `.CBB` records, the 29 combination commands and `GAMEDATA.BIN`'s
   records. The match AI's `fb::` classes are named by their type
   information, and `snr2.py classes` and `callers` now list them and
   which class makes each call, a way in for these too.
3. **Test in PCSX2: an edited detail-screen comment script** (section
   7). The disc is built (`LMAST-test-comments.iso`); it would be the
   first PwkScript edit seen in game.

## 1. Message text (`DAT/MESSAGE/MES.PAC`)

The format is decoded: see [`DOC/MBB_FORMAT.md`](DOC/MBB_FORMAT.md) and
`SRC/mbb.py`. All 3,738 files and 66,102 messages parse, in 7 language slots.

- [ ] Name the remaining EvsDataBin columns: NEWS `+0x20`, `+0x60`, `+0x70`
- [ ] Message variable leftovers: which player, team or number the
      screen-set global variables (1100-1104, the 3000s) hold on each
      screen, and how variables 35 and 0 outside category 1 are filled
- [ ] Check whether raw `0x0A`/`0x0D` bytes affect display
- [ ] Which code picks the rival owner's name (variable 131, one of
      category 1 messages 760-783, four per league) into the rival's work,
      and whether it is `league × 4 + rand(4)` like the stadium name
      (`DOC/MBB_FORMAT.md#global-variables`)

## 2. Starting season and parameter tables (`PARAM/`, `0SYSTEM/`)

The first thing [`GOALS.md`](GOALS.md) wants a mod to change. Every table
parses with `tbb.py`, and [`DOC/PARAM_DIR.md`](DOC/PARAM_DIR.md) gives each
file's loader and size. The starting leagues, squads, schedules and player
database are decoded and editable (`initteam.py`, `schedule.py`,
`pbdata.py`); `0SYSTEM/` is surveyed in
[`DOC/0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md).

- [ ] Division sizes: room for bigger second divisions and a smaller
      English or Italian first division (start the season earlier, or
      use cup turns; the ranges are in
      `DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from`)
- [ ] Test in PCSX2: a smaller first division (France at 18, from the
      editor's Season tab) and two nations changed in one save. Only
      England at 22 is tested in game
- [ ] Parameter tables still without a field-level writer: the club
      ranking's points (`CLUB_RANK_SYSTEM.TBB` tables 1-3,
      `DOC/PARAM_DIR.md`), and the club events, which live in the
      executable (`SLES 0x52ff58`, `0x530688`), not in `CLUBEVENT.TBB`.
      `tbb.py replace` only swaps a whole table
- [ ] `TRAINING_LIST.TBB` leftovers (`DOC/TRAINING_FORMAT.md`): the
      scale of a practice's values and fatigue, the names of the 87 camp
      types, 28 youth menus and the facility rows, whether anything reads
      the facility tables' columns 64-70, and a PCSX2 test of an edit
      (a practice made much stronger)
- [ ] Camp leftovers (`DOC/CAMP_FORMAT.md`): which camp each sponsor
      frees (`SIMPRG.REL 0x16a940`), the camp types' names, and what
      Santiago's camp shows without its description (keyed to city 764,
      the camp is 774)
- [ ] `CLUBRESULT.TBB` leftovers (`DOC/CLUBRESULT_FORMAT.md`): the prize
      texts `0x8ca0`-`0x8ca7`, and a PCSX2 test of an edit (a cup given a
      third-place match shows "3rd"/"4th" on the end of tournament
      screen)
- [ ] `REGULATION.TBB` leftovers (`DOC/REGULATION_FORMAT.md`): `+0x04`,
      the reader of `squad2`, and what the place checks change on screen
- [ ] How your club and the rival become ranks 25 and 26 of the second
      division's past record, which the own-nation schedule (UID 1, 26
      slots) takes after the tutorial (`DOC/SCHEDULE_FORMAT.md`, user
      report)
- [ ] Still open from the schedules: what `CLUB_RANK_SYSTEM.TBB` table
      1's kinds and third field and table 0's groups change
      (`DOC/PARAM_DIR.md`), `PeriodName.tbb`, the `make_list` source functions, game bits `w0`
      8–9 and competition header bytes `0x0A`–`0x0F`
- [ ] Still open: club-record bytes `0x0b`-`0x0d`/`0x0f`, the reader of
      `MAPTEAM_LIST`, and `PLRRSRC_INITTEAMDATA` table 2's negative values
- [ ] `TEAM_INIT_DATA` leftovers: the candidate lists' "List criteria"
      (7 Training cycle) and H.Dale's salary showing 80,000 not 75,000
- [ ] Salary limits: read the min/max table at `0x5eb068` (filled at run
      time; `WithInRange_SM 0x246d18`, price kind 0, units of 100) over
      PINE, then give the New club tab's salaries that range
      (`DOC/TEAMINIT_FORMAT.md#still-unknown`)
- [ ] Player fields still open: whether anything reads `explodetype`
      (`+0x43`-`+0x46`, named by the developers' field table; probably
      meant for the `pwkExplo_*` growth spurts, no reader found), where
      abilities 59–63 are used (not in the match record), and which
      attack pattern letter is which
- [ ] Match parameters, after their readers
      (`DOC/PBDATA_FORMAT.md#who-reads-each-parameter`): which kick kind
      is which in helper `GAMEPRG.REL 0x98a30` (the byte at `+0x1a`, 43
      kinds), the 45 getter calls with no class, the sources of
      parameters 16 and 24, and whether any code reads leadership (61),
      pressure (64), the offside-line skill (113) or the ball touch (139)
      straight from the player object
- [ ] Tendency leftovers (`DOC/PBDATA_FORMAT.md#the-tendencies`): whose
      value the pass intentions and the carry helper `0x117480` read
      (passer or receiver), what the press floats measure, which tactics
      setting the team value at match data `+0x9764` is, which dribble
      style looks like what. No screen shows the tendencies (user
      report), so check an edit over PINE: read the edited player's
      parameters 128-138 from the match's copy (`GAMEPRG.REL 0x97b28`,
      object `+0x84`-`+0x8e`) during a match
- [ ] Kit style leftovers: what makes `gk_cap` (`+0x5a`, source name
      `nicknack_gkcap`) show (3 showed no cap), what sets
      `plGi +0x1f538` (outfield gloves; a night match didn't)
      (`DOC/PBDATA_FORMAT.md#kit-style`)
- [ ] Staff field leftovers: which code reads the fields only the
      developers' field table names (rank, face, appeartype; the
      manager's comptype), and what the 25 manager policies (`+0x34`), the
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
- [ ] Squad ages and the tutorial skip: does `OTEAMMEMBER`'s age show one
      year older because of a new game or because of `--skip-tutorial`?
      Start a career without the skip and look at Van der Sar (Manchester
      slot 0, age 16 in the mod): 16 means the skip adds the year. Then
      document which code adds it (`DOC/INITTEAM_FORMAT.md`,
      `DOC/TEAMINIT_FORMAT.md`)
- [ ] Tutorial skip leftovers: check other leagues (the switch calls
      `pwkLg_Init(0)`), and whether the rest of the skipped
      `Sche.YearEnd`/`Sche.MonthEnd` (`pwkTeam_ChangePop_Year`) changes
      anything (`DOC/SQB_FORMAT.md#the-supplier-and-the-clubs-status`)
- [ ] National team leftovers: what `_getNationalTeamPoint` (`0x227200`)
      scores, team 465 (the Netherlands national team, `PLRESOURCECOMMON` 3.3) and
      `PlPinfo +0x20c` flag `0x300` in the call-up
      filter, and which clubs teams 442-459 are
      (`DOC/PBDATA_FORMAT.md#national-team-call-ups`)
- [ ] Test in PCSX2: a main-position change with `pbdata.py --sles` on its
      own (rank edits are tested; position goes through the same table)
- [ ] `PLRESOURCECOMMON.PAC` leftovers (`DOC/PLRESOURCECOMMON_FORMAT.md`):
      the first words of each facility record and the code that charges
      the build cost, the rest of the stadium record, the values in
      entries 1 (formations), 2 (hexagon) and table 4.1 (cup ids), and
      which messages name the facilities
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
      and `+0x14`, which code plays which scene id
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
- [ ] Decode the `RBD0` trailer in `GAME/ROUTEBOX_*.BCR` (`tbb.py`'s
      writer copies it as-is; `DOC/GAME_DIR.md`)
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
- [ ] Test in PCSX2: an edited detail-screen comment script
      (`DOC/SQB_FORMAT.md#the-detail-screen-comments`). Built:
      `LMAST-test-comments.iso` (with `--skip-tutorial`; start in
      England), `PSCCOMMON.PAC` and its `STATIONFILE.PAC` copy patched by
      `sqb.py settable`: every cell of `seicyoMS` table 1 is 207, so every
      player's second comment line should read "Reaching the end of his
      career.", and every cell of `manager_syousai_nouryokuMS` table 2 is
      186, so every manager's comment should read "A leading world class
      manager with unsurpassed health management skills." Coaches and
      scouts keep their own comments. Also open there:
      which players have a fixed comment (`DETAILFLAG`), and when the
      player page shows messages 120/121
- [ ] Injury leftovers (`DOC/INJURIES.md`): how many game days an
      injury value lasts (practice slots per week, the injured player's
      practice number), the injury chance `0x219f90` and `PlPinfo
      +0x1e6`, what makes the match engine report a heavy injury
      (GAMEPRG.REL `0x19cf00`, `0x19ee80`), and how kind 8 shows
- [ ] LMASTER Mod (`DOC/LMASTER_MOD.md`): the first restorations as
      `patch_disc.py` switches, each tested in PCSX2. Candidates: the
      kind-6 injury value 1600 (`0x532d70`), the injury kind row past
      fatigue 1000, the short `EDIT_EMBLEM` tables 93/101/105. Built,
      to test in PCSX2: `--mod national-cups` (a World Cup and a Euro
      year to the end), and the four camp switches (`camp-types`,
      `camp-cities`, `camp-santiago`, `camp-clubs`). The
      "two months"/"nine months" injury lines need thresholds chosen
      first. Improvement earmarked: rebuild the badly balanced league
      schedules (22 and 26 clubs, the 8-club VS league) at the same size
      with `schedule.set_league`. Also earmarked: a harder economy
      (dearer facilities, a wider ticket price range, dearer advertising);
      first trace the facility charge, the plan screen's limits and what
      the ad budget and ticket prices do. More ideas (overseas bases,
      merchandise, reputation, player prices up to £250M) and a third
      tier with a one-season game over are listed in
      `DOC/LMASTER_MOD.md#improvements`
- [ ] Japanese release leftovers (`DOC/JAPANESE_RELEASE.md`): why
      `PLRESOURCESIM.PAC` entry 0's weather tables stop partway; whether
      the player-database values above PAL's limits are Japanese features
      or data PAL fixed; how the game opens `BC_JPN.AFS` (65,501
      unnamed clips, count sign-extended) and names its clips; the sponsor texture
      counts; reading a Japanese save (block 1 is 16 bytes smaller)
- [ ] Tools still PAL-only: `patch_disc.py`'s switches (they refuse
      other discs), `save.py`'s commands (they take no ISO folder), the
      editor

## 8. Housekeeping

Nothing open.

## 9. Rebuild

Stage 4 of [`GOALS.md`](GOALS.md): getting edits back onto a bootable disc.
See [`DOC/REBUILD.md`](DOC/REBUILD.md).

- [ ] `TACTICSPITCH.PAC` is loaded through `CLoader`, not as a registering
      resource: whether its entries stand in for their originals
- [ ] Test in PCSX2: a `PRELOAD` pack that a rebuild moves (the code path
      is the same as a moved file, but untested in game)
- [ ] Test in PCSX2: a face changed in a rebuilt `FC_EURO_FACEPACK_01`
      (`pac.py replace --prs`), and any PRS entry written by
      `pac.prs_compress`
- [ ] Test in PCSX2: an archive rebuilt around a grown entry, with its
      `.HED` (a `PLAYER/NUMBER_*.PAC` number texture), and an Acrobata
      scene in a rebuilt pack
- [ ] Test in PCSX2: a `MES.PAC` whose files moved (`LMAST-test-camps-mes.iso`, with `--mod lmaster` and the skip:
      `3_6.mbb` grown past its slot, the welcome mail's body starting
      "MOVED FILE TEST." in `MES.PAC` only; the new-game popup should show
      it, the Mail screen the original from `MAIL1.PAC`)
- [ ] Optional: let `vcdiff.py`/`patch_disc.py` read CSO (and CHD) images,
      which many players keep instead of ISOs
- [ ] Sponsor negotiation leftovers: whether Japan limited the number of
      negotiations (message 61; compare the Japanese `SIMPRG.REL`'s
      Sponsor screen, now that `ISO_JP/` is set up), and the acceptance
      tables at `SIMPRG.REL 0x1dad80`/`0x1dada8`

## 10. Save data

See [`DOC/SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md).

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
- [ ] Test in PCSX2: a `--mod-saves` disc writes its VS data to
      `BESLES-54151-D000` (career saves to `-M` are tested)

## 11. Editor GUI

Stage 5 of [`GOALS.md`](GOALS.md): GUI tools on top of the writers,
organised by what a player of the game recognises (a player, a club, a
season) rather than by file. `tkinter` only, as the principles there say,
and every GUI edit must also be possible as a `python SRC/...` command.

- [ ] Licensed kits: which descriptor copy a match reads (an edit to
      only one copy would tell), and whether a front number can show at
      all (a front number colour showed nothing on AC Milan's shirt, user
      report)
- [ ] Save editor (`SRC/saveedit.py`), a separate window for career saves
      on folder memory cards, on top of `save.py`: steps 3-5 in
      `DOC/SAVE_EDITOR_PLAN.md`: step 4, a PCSX2 test of each page's
      edit (the Club page is tested), then step 5, the player fields
      `save.py` reads but can't set yet
- [ ] Save editor: `.ps2` memory card images (PCSX2's default), which
      need a reader and writer for the card's file system
- [ ] Save editor: an option to write an edited save to a new slot (the
      next free `-Gnnn`) instead of over the original
- [ ] Test in PCSX2: a save from the Regulations tab (the same edit from
      `regulation.py set` is tested)
