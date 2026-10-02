<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Done

Finished items from [`TODO.md`](TODO.md), under the same section numbers,
so a note such as "moved to section 7" points to the same place in both
files. Each item keeps what was found, where, and how it was tested.

## 1. Message text (`DAT/MESSAGE/MES.PAC`)

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
- [x] Text writer: `mbb.py set`/`import` (CSV) write an edited `MES.PAC`,
      each file kept at its size (zero-padded, safe per `Initialize`
      `0x30d1f4`); all 461,992 records round-trip (`roundtrip`, in
      `regress.py`); `patch_disc.py --copies` updates the `PRELOAD` copies
- [x] Confirm in PCSX2 that an edited message shows in game: the
      welcome mail's subject and body (`563:11000`/`563:1000`, English),
      written to `MES.PAC` and `PRELOAD/MAIL1.PAC`
- [x] Which copy the mail text is read from: `MES.PAC` (different text in
      `MES.PAC` and `PRELOAD/MAIL1.PAC#6`; the welcome mail showed the
      `MES.PAC` one). The rival's Big Bang lines (`487`, no copy) also
      showed
- [x] What the other `PRELOAD` copies of message files are read for: all
      of them are read while their pack is loaded (`DOC/PRELOAD_DIR.md`).
      The global categories 1, 3–11 (club names) come from `STATIONMES`
      all game. Tested in PCSX2: club names showed the `STATIONMES1` copy,
      and the welcome mail opened from the Mail screen showed the `MAIL1`
      copy
- [x] Let a message file grow into `MES.PAC`'s `0x800` slot (median 1,544
      bytes free; filler is ASCII `'0'`): only the header size changes, and
      the loader reads `(size >> 11) + 1` sectors from it (`0x10cf1c`).
      `patch_disc.py --copies` warns about, and leaves alone, `PRELOAD`
      copies of grown files instead of writing them cut short
- [x] Confirm a grown message file in PCSX2: the rival's Big Bang lines,
      `487_1.mbb` grown 9,636 -> 9,704 bytes (same 5 sectors, so the new
      header size itself isn't exercised)
- [x] Rebuild `PRELOAD` packs so grown files' copies can follow:
      `patch_disc.py --copies` rebuilds each pack holding a grown file
      (`pac.build_binpac`, the original packer's layout; all 662 BINPACs
      round-trip, `pac_roundtrip` in `regress.py`). A pack may grow to the
      end of its last sector (the game reads `(size + 0x7ff) >> 11`
      sectors, `0x307f24`), and its directory record is rewritten and
      re-encrypted. Tested on a copy of `DATA.CVM`, reverts byte-exact
      (`DOC/PRELOAD_DIR.md#rebuilding-a-pack`)
- [x] Load a rebuilt pack in PCSX2: two lengthened club names
      (`STATIONMES1.PAC` 45,264 -> 45,328 bytes, entries 3-9 moved,
      directory record changed) showed in VS mode Team Selection
- [x] The EVENT `+0x68` timing enum: each value is a moment the root
      scripts run the Event module for (`m4[3]`, confirmed through
      `SIMPRG.REL 0x6a50`/`0x129f14`), e.g. 0 year start, 4 turn start,
      16 before the Sponsor screen (`DOC/GAME_FLOW.md#event-timings`)

## 2. Starting season and parameter tables (`PARAM/`, `0SYSTEM/`)

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
- [x] Initial clubs and squads: `PLRRSRC_INITTEAMDATA.TBB` (divisions, last
      season's order) and `OTEAMMEMBER.TBB` (player, age, shirt, contract),
      with club names from `MES.PAC` category 3 (`DOC/INITTEAM_FORMAT.md`,
      `SRC/initteam.py`)
- [x] The rest of the starting data: the 24-byte club record (rank, world
      rank, manager, stadium, transfer policy, money, city), `INITNATIDATA`
      (UEFA rank/points, world rating), `STADIUM_DATA` (roof, level,
      capacity), `MAPTEAM_LIST` (flag = real 2005/06 top divisions);
      `initteam.py teams/nations/stadiums/setteam`
- [x] `TEAM_INIT_DATA.TBB`: the player's new club by league and team style
      (Counter-Attack, Possession, Individual Play, Teamwork). Read by
      `pwkTeam_Init2` (`0x25eae8`), called from the Club Edit overlay:
      squad (18; the rival takes all 22 of the opposite style), youth team,
      manager, youth manager, coaches, scouts, two staff lists, and the
      rival's manager, stadium and club bytes. `DOC/TEAMINIT_FORMAT.md`,
      `SRC/teaminit.py` (`info`, `show`, `set`, `roundtrip`; in
      `regress.py`). Table 6 quirk: only its first record is ever read
- [x] Tested in PCSX2: an edited squad record (John Terry, age 30, in
      England / Counter-Attack) showed in a new career's squad at 30, and
      the squad was exactly the group's first 18 records
- [x] Tested in PCSX2: tables 4 and 5 are the starting Coach and Scout
      Candidate Lists; the Individual Play squad, the rival's full
      22-player squad of the opposite style, and the staff (ages shown,
      salaries in pounds = value / 6) all match the table
- [x] Name manager field `f_22` and scout field `f_18` in `pbdata.py` as
      the staff ages: they equal `TEAM_INIT_DATA`'s staff age byte in all
      288 records, the fallback code reads them there, and that byte is
      the age the game shows (tested)
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
- [x] Skill bits: bit n is message 2000:6000+n (goalkeeper, defender and
      forward bits split cleanly across the database); the style icons are
      the play styles instead (`PlPinfo +0x278`/`+0x27c`/`+0x290`, names
      100001:150+style)
- [x] Staff jobs: 0 manager, 1 attacking coach, 2 defensive coach
      (database averages); 0-2 share the title "Assistant Coach" and one
      icon; `pwkTeam_SetYManager` sets job 6
- [x] `PLRESOURCESIM.PAC`: every entry's reader and layout
      (`DOC/PLRESOURCESIM_FORMAT.md`, `SRC/plrsim.py`, in `regress.py`):
      states/cities/climate/weather, overseas branch costs, nations,
      player affiliations, introductions, statistics row per schedule UID,
      the edit colour palette, scouts' exclusive players, good and bad
      player/manager combinations, free agents. Entry 2 is never read
- [x] Tested in PCSX2: replacing J.Galvan in entry 15 removed him from
      the Transfer List, so the free agents come from there. Buffon
      (26,110, rank 14) didn't show: the screen shows only part of the
      pool (reputation gate? user's suggestion)
- [x] Tested in PCSX2: Paul Jones (26,455, rank 5, Wales national team)
      in Galvan's slot shows on the Transfer List, so national-team
      records can be free agents; Buffon (rank 14) is held back by a gate
- [x] Testing aid: `patch_disc.py --skip-tutorial`, the developers'
      switches (`Dummy.CheckFirstMatchSkip`/`CheckClubEditSkip`, flags
      `0x34d430`/`0x34d434`), 4 bytes
      (`DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs`).
      Tested in PCSX2 (England): the playoffs are skipped and the season
      starts. (The launcher's MAIN GAME START still has the tutorial: user
      report)
- [x] `UNIFORM_NAME.BIN` and `UNIFORM_NAME2.BIN`: 27,950 × `char[19]`
      placeholders (`"a"`, or `"0"` in 142 records of `UNIFORM_NAME2`), not
      referenced by name (`DOC/PARAM_DIR.md`). 27,950 is the player count,
      so they are probably one kit name per player
- [x] Write `DOC/0SYSTEM_DIR.md` (and `SRC/system.py`, in `regress.py`):
      the loader of every file; 77 UI colours (`clr::GetRGBA`); the 8
      texture packs as `CFcEuro_CommonTexture` types 0-7, with how a team,
      competition or sponsor id picks the entry; fonts by language;
      `SAVE_VERSION.DAT` is a note matching the save header's version 105;
      `MSGCOMMON`, `SCHEDULE.TBB` and the kanji palettes are unreferenced
- [x] Siena's crest in game: always the made-up one (user report), so
      `FLAG_TEXTURE`'s real crest is never shown. Still open: what
      `CDetailTeamFlag`, the only type-1 (`FLAG_TEXTURE`) request, draws;
      probably nationality flags, which are the same in both packs
- [x] The free-agent gate: the Transfer List shows a free agent only if
      his rank is in a band set by the club rank (`0x25c168`, `0x25bfc8`):
      0–5 for club ranks 0–5, rising to 3–11 for 26–31. Ranks 12–15 never
      show, so Buffon (14) can't; above 100 matches it shows every 2nd–5th
      player, at most 30 (`DOC/PLRESOURCESIM_FORMAT.md`)
- [x] Tutorial skip, sub-sponsors: the starting sponsors (table at SLES
      `0x3994a8`) end when `Sche.YearStart` has run twice, and the
      playoffs run one of them. `--skip-tutorial` now starts them a year
      in (6 more bytes). Tested in PCSX2: the first Sponsor screen offers
      the main and sub-sponsor slots (`DOC/SQB_FORMAT.md`)
- [x] Player play styles and ability names: `+0x5e` is 5 play styles
      (`pwkPlayStyle_Init`, names message 1:150 + style), abilities 45–52
      are the 8 systems (match growth at `0x246884`), hexagon 0 is
      Attacking and 3 Skills, and most of the 64 abilities are named from
      Virtua Pro Football's Player Edit screen (user screenshots of Maik
      Taylor, player 0). `pbdata.py show` prints the names
      (`DOC/PBDATA_FORMAT.md#ability-names`)
- [x] Play style edit tested in PCSX2: Terry with `style.0=7` shows
      "Play maker" on his detail screen's STYLE line, on a
      `--skip-tutorial` disc (`DOC/PBDATA_FORMAT.md#play-styles`)
- [x] Player fields named from the developers' player editor in
      `DEBUGPRG.REL`: all 64 abilities ({label, number} table at
      `0x11128`), and required status (was "money"), speech tone,
      dissatisfaction sensitivities, professionalism, pressure, loyalty,
      star quality, motivation/condition type, potential, travel, injury
      resistance, recovery, foul avoidance, weak foot, policy,
      adaptability, intelligence, ball touch, dribble style. Readers
      traced in SLES for most; `+0x32` is the face number
      (`DOC/PBDATA_FORMAT.md#personality-and-condition-fields`)

## 3. Ninja 3D models and motions

- [x] Document the chunk layouts (`DOC/NINJA_FORMAT.md`)
- [x] Add a parser (`ninja.py info`/`dump`) and add it to `regress.py`
- [x] Triangle strips and winding (`strip_triangles()`); `obj` export works
- [x] Material texture references (`0x400`/`0x800` inline layers,
      `0x1000` PX Plus layers); `obj` writes `.mtl` and PNG textures
- [x] Common-vertex lists (`nnCompileCommonVerticesObject*`): the face and
      head models; `obj` exports them
- [x] Export the face packs' own textures (sibling SVM blocks in the same
      `etc::PackData` entry); `obj` takes `info` labels for archive entries
- [x] Camera (`NSCA`/`NSMC`, one per pre-rendered background) and light
      (`NSLI`) chunks
- [x] Run `ninja.py info DAT --prs` over the PRSH-compressed entries and
      the face packs (54,051 blobs, no problems)
- [x] Skinned export: `gltf` writes glTF with skeleton, skin weights
      (VU, PX Plus and common-vertex lists), textures and baked motions;
      checked by posing the result (players, background humans, test models)

## 4. `DAT/PLAYER/`

- [x] Survey the entry types: the KC@P packs (faces, `PLPACK_*` kits,
      `EDITFACEPACK`) wrap each entry in `etc::PackData`; everything else is
      Ninja models or textures
- [x] Write `DOC/PLAYER_DIR.md`
- [x] `SRC/packdata.py` parses `etc::PackData` in all 5 KC@P packs; `info`
      samples `FC_EURO_FACEPACK_00` (`--all` for every entry). In `regress.py`
- [x] The `PLPACK` block-0 kit descriptor and which clubs are licensed:
      teams 123-244 -> licence 0-115 (`0x3a08d8`), descriptor at
      `0x3a0c80` (same bytes as block 0); `uniform.py licensed`,
      `setlicence`, `setexe`. Tested in PCSX2: the number colour comes from
      the executable's copy (pack-only edit: no change; exe-only: white)
- [x] `UNIFORM_LIST` (every club's kits: designs and colours per shirt,
      shorts, socks; bit layout from `0x2d2b68`) and `COLOR_TBL` (colour
      clash table): `DOC/UNIFORM_FORMAT.md`, `SRC/uniform.py` (`info`,
      `show`, `clash`, `set`, `roundtrip`; in `regress.py`). Tested in
      PCSX2: Birmingham's shirt edited from blue to red shows in the
      Uniform Viewer

## 5. Music and sound effects

- [x] `SOUND/*.DAT` (all 28 files) are each one `ps2_DTPK` bank covering the
      whole file; `sounddat.py dtpk` parses them all
- [x] `ISO/AUDIO`: 18 CRI AFS archives of ADX audio (music, commentary,
      chants, ambience); `SRC/afs.py` checks all 65,225 entries and decodes
      them to WAV with loop points (`DOC/AUDIO_DIR.md`)
- [x] Listen to the decoded WAVs: ADX (`BGM`, `OPEN`, `VIC`, `KANSEI`,
      `OUENKA`) and DTPK (`SYS_SE`, `EFFECTS`) sound right by ear
- [x] Document `SOUND/` in a folder doc (`DOC/SOUND_DIR.md`): the
      executable's bank table (`SYS_SE`, `map01`–`map23`, with song
      requests) and music table (63 music ids: 45 `MAP` songs, 18
      streams); `sounddat.py music` (in `regress.py`)
- [x] DTPK songs: the SoundFactory sequence format, from the IOP driver
      `SNDFI.IRX` (stream, records, 1 ms ticks at 200 Hz); 41 songs in
      `MAP01`-`MAP10`, `sounddat.py songs` and `midi` (checked by ear)
- [x] Play the songs with the bank's own instruments: setups, programs,
      splits, layers, drum kits, mix bits and the level rule from
      `SNDFI.IRX`; `sounddat.py tones` and `wav` (checked by ear)
- [x] Add `sounddat.py dtpk` over `SOUND/*.DAT` to `regress.py` (one check
      per file; each is a single bank filling the whole file)
- [x] `.SQB` "sequences" (19 files in `SEQ/`): not audio but the game's
      sequencer scripts. Moved to section 7 (`DOC/SQB_FORMAT.md`)

## 6. Files and folders nobody has looked at

- [x] `ACROBATA/ACROBATAPACKFILE.PAC`: 875 Acroarts scenes, each an `ABDA`
      scene part and an `ABRS` part of wrapped Ninja files and textures
      (all 4,841 parse); `POF0` pointer lists decoded; the executable's
      own copy of the pack index (`SLES 0x3a3b08`) and its scene-id table
      (`0x55d7a8`, 719 ids, 26 by language). `DOC/ACROBATA_DIR.md`,
      `SRC/acrobata.py` (`info`, `scenes`; in `regress.py`)
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
- [x] `STADIUM/` night flag and request fields, via the Stadium Viewer's
      code: `+0x88` = `BUILD_STADIUM` row byte 82 (the `LIGHT_1` switch), so
      `N2` = stadiums with the second floodlight set (every lights-built
      variant of levels 1-3); `+7` = landscape level (slots 42/43 are
      LANDSCAPE_A/B, not pitch lines); the whole request named; the 44 part
      slots named (`stadium.py build`)
- [x] `STADIUM/` crowd flags and the last request bytes: the tier flag
      picks the `AUD_JAM_HI` table (fill curve); the block flag picks which
      of a block's two figure groups gets the home supporters (tiers sort
      home/away/visitor counts from request `+0x14`-`+0x1c`); `+0x0e`
      advert board style (electric / bigger layout), `+0x0f` extra-board
      level by model, `+0x10` special first advert; `+0x13` unread
- [x] Folder docs for `EMBLEM/`, `NEWS/`, `SOUND/`, `SEQ/` and `TEST3D/`,
      plus the `CVS/` metadata: `DOC/EMBLEM_DIR.md`, `NEWS_DIR.md`,
      `SOUND_DIR.md`, `SEQ_DIR.md`, `TEST3D_DIR.md`, `CVS_DIR.md`, with
      `emblem.py`, `news.py` and `cvs.py` (all in `regress.py`)
- [x] Folder doc for `ACROBATA/` (`DOC/ACROBATA_DIR.md`): every folder in
      `DAT/` now has a doc

## 7. Event system and game code

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
- [x] The event clock (`0x12e5a8`) counts game turns
      (`plMisc_PlDate2TotalTurn`, 96 a season): a procedure step is the
      next turn (half a week), scout reports come every 4-6 turns by
      region, club dealings take 2-4
- [x] Boot the launcher patch in PCSX2: it works. A developer menu with
      `simprg` (MAIN GAME START, BPINFO CHECK, 3D TEST, MODEL VIEWER, CSE
      TEST, BG CONTROL, ...) and `gameprg` (STADIUM VIEWER MK2, GAME, BC
      TEST) tabs (`DOC/SQB_FORMAT.md#the-developer-launcher`)
- [x] The launcher's full list: 59 `simprg` entries = modules 71-129 in
      order, `gameprg` = 171-173 (names in `DOC/SQB_FORMAT.md` and
      `sqb.py`)
- [x] Try each launcher entry in PCSX2 (all recorded in
      `DOC/SQB_FORMAT.md`): STADIUM VIEWER MK2, Uniform Viewer, CHARACTER
      VIEWER, SATO TEST (heads), CLUB EDIT and its sub-screens and many
      menu tests work; about 20 entries hang or return at once. YAMAZAKI TEST, Talk
      and BG LIGHT TEST not recorded
- [x] Use the Uniform Viewer to check `UNIFORM_LIST` (done, see section
      4). Its collar, number and captain-mark fields come from the
      licensed-kit data (`GetLicenceUniformInfo`), a lead for the `PLPACK`
      block-0 kit descriptor
- [x] `DAT/TEST3D/VIEWERPLAYERMOTION.PAC`: the CHARACTER VIEWER's motion
      set, 5 player motions (`mendan_Asit_ang_001`–`004`,
      `mendan_sit_ang_001`) read by `CCharacterViewer::CallExecute`
      (`TESTPRG.REL 0x190a4`); `VIEWERSECRETARYMOTION.PAC` holds
      `cameron.snm` (`DOC/TEST3D_DIR.md`; `ninja.py info` parses them)
- [x] Label `FC_EURO_FACEPACK_01` entries: each head carries its own
      model/texture name (`packdata.py names`, in `regress.py`), matching
      the viewer's table row by row; 188-191 `kihon`, 212-214
      `HUMAN_head_9000/9500/9600`
- [x] The PBDATA blocks of 25 low-rank players with shirts 1-25 (e.g.
      England 25591-25615, then 25616-): the built-in default club that
      `pwkTeam_Init` builds without `TEAM_INIT_DATA` (lists at `0x3995a8`,
      `0x3995d0`; rival 25655-). Club creation then replaces it from
      `TEAM_INIT_DATA.TBB` (`DOC/TEAMINIT_FORMAT.md#without-the-file`)
- [x] Sequencer scripts (`SEQ/*.SQB`, `PSC*.PAC`): `CSeqController`'s
      command encoding, argument types, labels and calls; the root set
      (Base, Scene, RootEvent: 125 commands, 94 by symbol) and the
      PwkScript set (Param, 30); `SQT1` data tables; `SQBFILENAME` ids
      and `GLOBALMEMORY` records. `DOC/SQB_FORMAT.md`, `SRC/sqb.py`
      (`info`, `dis`; in `regress.py`). 41 of 43 scripts decode, every
      label resolves
- [x] Read the root scripts as the game's flow chart
      (`DOC/GAME_FLOW.md`): boot and title routes, the new game, what each
      Load result resumes, the season loop, the year start's order, the
      main menu's 13 screens, a match day, the four game-over checks and
      the event timings. Scripts 9-11 are never started

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
      (`TBB_FORMAT.md`). The reader is `EDIT::CEmblemData::
      GetSampleLayerAcceData` (`SIMPRG.REL 0x104180`): it walks 12-byte
      rows, so records 4–10 are misread and 11 never reached
      (`DOC/EMBLEM_DIR.md`)
- [x] Start the write stage with `tbb.py`: `build()` round-trips all 70
      `.TBB`/`.BCR`/`.BCB` files byte for byte (`roundtrip`, in
      `regress.py`); `replace` puts an edited table back
- [x] `pbdata.py` writer: all 31,950 records re-encode and the pack
      rebuilds byte for byte (`roundtrip`, in `regress.py`); `set` and CSV
      `import` edit players, managers and scouts
- [x] Update the `PLAYER/` and `PARAM/` rows in `GOALS.md`'s coverage table

## 9. Rebuild

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
- [x] Which copy the game actually reads: a loaded `PRELOAD` pack
      registers its entries under the originals' names, and requests are
      served from it; the original is read when no pack holding it is
      loaded. Every copy is read somewhere, so `--copies` stays
      (`DOC/PRELOAD_DIR.md`, `SRC/preload.py`, in `regress.py`)
- [x] BINPAC writer: `pac.py roundtrip` rebuilds all 662 self-describing
      BINPACs byte for byte, `replace` repacks with new entries;
      `patch_disc.py` rebuilds `PRELOAD` packs and lets a file change
      size inside its last sector (directory record re-encrypted)
- [x] xdelta patches: `SRC/vcdiff.py` makes and applies VCDIFF (RFC 3284)
      in plain Python; the Terry mod is a 10,642-byte patch that applies to
      a byte-identical image
- [x] Confirm a `vcdiff.py` patch applies with xdelta UI or DeltaPatcher:
      Delta Patcher's output matches `vcdiff.py apply` byte for byte (it
      needs the uncompressed ISO, not a CSO)
- [x] `patch_disc.py` patches files outside `DATA.CVM` (`disc:SLES_541.51`)

## 10. Save data

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
- [x] Confirm in game: the renamed disc boots in PCSX2 as PYRA-31396.
      PCSX2 only lists it with a GameDB entry for the new serial; left
      alone, as the serial change is an optional feature, not the default
- [x] PlPinfo: growth limit (`pwkGUtl_AddExp`), current age, team, the
      embedded `PlPbase` copy, salary, contract years, fatigue, condition,
      motivation, injuries; match statistics (season, last season, career)
      checked against two players' screens; `save.py player` shows them and
      `set` edits fatigue/condition/motivation
- [x] "kan" is form: the condition line's thresholds
      (`ConvertPlayer_Condition`) match three players; edited fatigue,
      condition, motivation and 99 abilities hold in game
- [x] T-FIT is team fit (`+0x29a`, 0-100, `pwkTeamType_FitCalc` from the
      policy points); the youth team (block 1 `+0x4f00`, 24 slots) in
      `show`/`player`/`set` as `y<slot>`
- [x] Faster decoding: the serializers' field list (604,078 fields) is
      recorded once, cached in `.cache/`, and replayed (about a second a
      save); `save.py fields` checks it against the interpreter on random
      data
