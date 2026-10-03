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
- [x] Message variables: the game's table of the 880 global variables
      (`SIMPRG.REL 0x1dae50`, searched by `Msg::SearchGlobalVarHeader`):
      each one's kind (the wildcard converter: player name, team name,
      number, ...) and the code behind it, including the 50 text slots
      and their writers. Variables in other categories are wildcard ids
      (1,172 of 1,187 uses). `mbb.py vars` lists both, checked by
      `regress.py` as `mbb_vars`

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
      the main and sub-sponsor slots (`DOC/SQB_FORMAT.md`). Replaced by
      the second version of the skip (below), which runs the real
      `Sche.YearStart`
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
- [x] Tutorial skip, supplier: Egamucho needs club status >= 500
      (condition kind `0x18`, `SIMPRG.REL 0x169818`); the playoffs'
      `Sche.YearEnd` adds 500 (`pwkTeam_YearEndCheck`). Measured over PINE.
      `--skip-tutorial` now also calls it from the skip command (28 bytes).
      Tested in PCSX2: status 500 and Egamucho at the first Sponsor screen
      (`DOC/SQB_FORMAT.md#the-supplier-and-the-clubs-status`). Replaced by
      the second version of the skip (below), which runs the real
      `Sche.YearEnd`
- [x] Manager and scout fields named from the developers' staff editors
      in `DEBUGPRG.REL` (`MinfoEditorTask`, `SinfoEditorTask`): all 48
      manager and 45 scout abilities ({label, number} tables at `0x103d8`
      and `0x13240`), the coach types 0-6, the manager's four policies,
      policy and ranges, formations, seven tactical leanings, attack
      pattern set, teachable drills, real-name flag and model pattern, and
      the scouts' four special searches. `pbdata.py show` names them.
      Empirical check: every nationality's scouts are best at their own
      region (`DOC/PBDATA_FORMAT.md#the-developers-staff-editors`)
- [x] National team squads: in a career they are called up from the club
      players on convene days (`jmNT_CallCheck`, `plTeam_CreateNationTeam`
      `0x227470`), by the national manager's formations, best ranked
      first, at most 3 per club and position (1 goalkeeper). The fixed
      blocks 26,041-27,949 are loaded only for VS mode
      (`pwkOteam_InitNonresident` mode 2 from `VS_Start`); 25,591-26,040
      are the squads of clubs 442-459. Entry 2 is decoded on the way: a
      ranking of players 0-25,590 by rank, position and nation, with entry
      3 its inverse, which decides those players' rank and main position
      (`DOC/PBDATA_FORMAT.md#national-team-call-ups`)
- [x] Tested in PCSX2: VS mode uses the fixed national squads. With
      26,046 renamed `NT.Terry.VS`, England's VS starters listed DF 6
      NT.Terry.VS (`DOC/PBDATA_FORMAT.md#player-id-blocks`)
- [x] Rank, main position and nationality edits for players below 25,591:
      `pbdata.py set`/`import --sles` re-sort entries 2 and 3 and patch the
      group table at SLES `0x52fbf8` (the rank ranges at `0x5eac08` are
      built from it). `roundtrip --sles` rebuilds the disc's ranking
      exactly. Tested in PCSX2: free agent A.Rankin lowered from rank 9
      to 5 showed on a new club's Transfer List
      (`DOC/PBDATA_FORMAT.md#entries-2-and-3`)
- [x] Player kit style, `+0x57`–`+0x5d`: sleeves, wristband, outfield
      gloves, goalkeeper's gloves and pants, boots. Named from the game's
      Dressing/GK Style labels (2000:1070–1082) and the common pack's
      texture names; `GAMEPRG.REL 0x1e468` copies them to
      `SPlayerUniformStyleInfo`, clamped by `0x2cd9c8`. `pbdata.py` names
      them and `info` marks values above the clamps. Tested in PCSX2 (VS
      match): boots, long sleeves, wristbands, the keeper's long pants and
      glove type show as documented
      (`DOC/PBDATA_FORMAT.md#kit-style`)
- [x] The match engine's player parameters: `GAMEPRG.REL 0x1435a8` and
      its helpers turn `PlPinfo` into a 0x108-byte record per player with
      a parameter array at `+0x37` (abilities through the tables at
      `0x28bd08`, `0x28bf38`, `0x28c048`; injury resistance, weak foot,
      recovery, foul avoidance, professionalism, pressure, styles, skills,
      `f_66`, ball touch, dribble style and the kit style directly).
      `f_66` is not dead data: it becomes parameters 128–138
      (`DOC/PBDATA_FORMAT.md#the-match-engines-player-parameters`)
- [x] `PLRESOURCECOMMON.PAC`: all 25 tables checked against their
      readers. Entry 0's facility records have their sizes from the
      getters (sites 0x1c, club houses 0x28, stadiums 0x80, ...), build
      time from each `plTeam_Build*`, upkeep from `payment_Equip` and
      stadium capacity by stand level; the nation tables are named.
      `plrcommon.py` (`info`, `show`), checked by `regress.py`
- [x] League membership: `initteam.py swap` exchanges two league clubs'
      ids in `PLRRSRC_INITTEAMDATA.TBB` tables 0 and 1, so each starts in
      the other's division with its results last season, keeping every
      division's size (fixed by the schedules). `roundtrip` rebuilds the
      file byte for byte (in `regress.py`). Checked: Highbury (11) and
      Cardiff (25), 8 ids, `info` has no `!!`
- [x] Schedule encoders: `schedule.py roundtrip` re-encodes all 333
      entries of the three schedule packs from their fields and rebuilds
      each pack with its `.HED` byte for byte (in `regress.py`); a pack
      and its `.HED` are written together, as the game reads offsets from
      the `.HED` copies in `PRELOAD/STATIONFILE.PAC`
- [x] Tutorial skip, second version: `--skip-tutorial` runs the playoffs'
      own schedule steps without the playoff turns (RootClubEditSeq's dead
      playoff section becomes InitializeFirstCheck, YearStart, MonthStart,
      CheckClubEditSkip and a Call to the won route's MonthEnd, YearEnd and
      Finalize), so the real `Sche.YearEnd` runs. Tested in PCSX2: All
      Clubs Ranking has real ranks (the first version left every club at
      65536), and the club starts with £3,350,000 (£1,785,000 before).
      The sponsors are normal (user report)
- [x] Tested in PCSX2: a career national squad lists each player's
      club, so call-ups draw only on club players and the renamed fixed
      record 26,046 (`NT.Terry.VS`) doesn't appear (user report)

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
- [x] `UNIFORM_GK.TBB`: the keeper kits of your club, the rival and the VS
      teams (ids 1, 2, 543-558), built in a match from the outfield shirt
      design (`UniformList_GetGKUniformData` `0x2d3608`): table 0 maps 209
      outfield shirts to keeper designs, table 1 gives each of 38 keeper
      designs 6 colour schemes, the first that doesn't clash is used.
      `uniform.py gk`, `setgk`, and a check in `info` (in `regress.py`).
      Tested in PCSX2: pink scheme colours gave a new career's keeper pink
      sleeves, shorts and socks. User report: the club editor only offers
      outfield kits

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
- [x] The play books `GAME/PLAYBOOK.BPB` (256 plays) and
      `COMBINATION.BPB` (30): records of player and ball paths, points in
      metres (x across, y along the pitch), the ball's route, play ids
      (`Pwk::PlayBookData::CPlayBookDataBase`). `bpb.py` (`info`, `dump`),
      checked by `regress.py`
- [x] `GAME/COMBINATION2.CSB`: 540 PRS-packed `SQB1` scripts in an
      `etc::PackData`, run with a third command set (Base + 29 combination
      commands, built by `GAMEPRG.REL` at `0x29fc90`); 539 decode with
      `sqb.py`, checked as `sqb_combi`. `COMBINATION2.CBB`: the matching
      540 size-prefixed records (container checked by `bpb.py`)
- [x] `GAME/GAMEDATA.BIN`: 4,131 records of 0x30 bytes (loader slot 10,
      `GAMEPRG.REL 0x13abb8`), with the angle at `+0x8` (π/32) and the range
      at `+0x20` read by the code. `AI_PARAM.BIN`: no reader by name or by
      content in any executable. `gamedata.py`, checked by `regress.py`

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
- [x] The Japanese release (SLPM-66316, `DOC/JAPANESE_RELEASE.md`):
      `extract_disc.py` verifies and extracts it to `ISO_JP/`/`DAT_JP/`;
      `gamever.py` finds all 27 PAL executable and overlay addresses the
      tools use in it (and loop bounds with `imm`); `acrobata.py`,
      `mbb.py`, `pbdata.py`, `preload.py`, `save.py`, `sounddat.py`,
      `uniform.py` and `plrsim.py` read either build, and `mbb.py`
      round-trips both `MES.PAC`s byte for byte. `regress.py` runs 106
      `jp_` checks. Found: the injury code and tables are the same in
      both builds; the Japanese build has 0x1b8 global variables, 12-byte
      wildcard converters, two commentary slots, no free-agent list and a
      different save layout (CRC `0x16da`)

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
- [x] `initteam.py roundtrip` (in `regress.py` as `initteam_roundtrip`):
      all 10,975 squad slots and 457 club records re-encode and both
      files rebuild byte for byte. `set` and `setteam` now write through
      the same encoders (`Member.encode`, `OteamMembers.encode`,
      `TeamDb.encode`), with the same output as before
- [x] `plrsim.py roundtrip` (in `regress.py` as `plrsim_roundtrip`): the
      1,300 free agents (entry 15) re-encode through `encode_free`, the
      encoder `setfree` now uses, and the pack rebuilds byte for byte.
      `setfree`'s output is unchanged. The Japanese pack has no entry 15,
      so the check has no `jp_` version

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
- [x] Size changes past a file's last sector: `patch_disc.py` moves the
      file (or a rebuilt `PRELOAD` pack) to the end of `DATA.ISO` and grows
      `DATA.CVM` into the free sectors after it, rewriting the PVD volume
      size, the `CVMH`/`ZONE` lengths and the disc's ISO9660 and UDF
      entries. The ROFS key is derived from the `CVMH` header, size
      included (`RSU_GenerateFixedKey` `0x1e7550`), so the table of
      contents is encrypted again with the new key
      (`rofs_decrypt.header_key`). Tested in PCSX2: a moved, grown
      `PBDATA_EU.PAC` booted and its renamed players showed in a VS match
      (`DOC/REBUILD.md#moving-files`)
- [x] Growing the disc past the free sectors after `DATA.CVM`: the PVD
      volume size, both UDF partition descriptors, the integrity
      descriptor and the end anchor follow (single-layer limit). Tested in
      PCSX2: a disc 10,208 sectors bigger, with a 25 MB-grown referee face
      pack moved, booted and showed the referee's face
      (`DOC/REBUILD.md#growing-the-disc`)
- [x] `patch_disc.py --sponsor-negotiation` in PCSX2: the prompt, Bid
      input, accepted and refused bids and the contract question all work,
      refused sponsors leave the list, and the signed contract pays the
      negotiated fee (user report). `DOC/SPONSOR_NEGOTIATION.md`

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
- [x] Pair combinations (the tactics screen's lines and heart icons):
      block 1 `+0x4808`, 25 × 25 u16 (value above the diagonal, cap
      below; `plCombi_Get`/`Set`), levels 1–5 at fifths of 65,535.
      `save.py combi` and `set ... combi:a:b=value`. Checked against the
      game: all 22 icons on one tactics screen match. Tested in PCSX2:
      an edited pair showed a big red heart, another a skull
- [x] Staff in saves: the manager's dissatisfaction (PlMinfo `+0xa4`, five
      kinds, `pwkDissatis_MAddComp`; 65,535 in any kind "explodes",
      `CheckExplosionM`), popularity (`+0xae`, `+0xb0`) and salary discount
      (`+0xb6`). `save.py staff` shows them; `set` edits staff abilities,
      dissatisfaction and popularity. Fixed `save.py staff`, which broke
      when `pbdata.JOB_NAMES` became a tuple. Tested in PCSX2: facilities
      dissatisfaction shows as "Won't tolerate club's facilities.", and a
      coach with all abilities 99 has full bars
- [x] Other clubs in saves (block 2): 440 records of 0xa8 bytes, team − 2
      (rival = 0), each a 25-player squad (id, age, shirt, contract years,
      flags), friendship with your club (`+0x9a`, 0-100), club rank and
      world club rank. `save.py clubs`, `set ... club:<team>:friendship=`. Tested in
      PCSX2: the edits show on the FRIENDLY bar (full and empty), and the
      world ranks match the Information screen
- [x] Club reputation: `CDetailManager::ConvertTeam` (`0x288a24`) picks
      message 203:*n* from the club rank with thresholds 6, 12, 18, 24,
      30 (`0x557710`); national teams use 203:100+*n*. The ranking that
      changes the club rank (`SIMPRG.REL 0x150738`) sorts each Euro6
      division and each other UEFA nation by world rank points and hands
      out ranks from `CLUB_RANK_SYSTEM.TBB` table 3, by the nation's
      coefficient slot. It matches every ranked club in four saves
      except tied pairs. The community account is right in outline
      (corrections in `SAVE_FORMAT.md`). Also named: `+0x9c`, the main
      league. `save.py clubs` shows the text and league, and `set ...
      club:<team>:rank=` edits the rank. Tested in PCSX2: rank 31 made
      Pirouzi a "World famous club" and rank 0 made Marseille a "Local
      club"
- [x] Your club's status and the rival's rank: `0x26dd40` sets your club
      rank to status >> 11 and the rival's from the table at `0x555168`,
      after each match check and at year end; the status is capped by the
      status rank (`0x555150`), which titles lower. `save.py show` prints
      them, `set ... status=N status_rank=N` edits them. Tested in PCSX2:
      status 30,000 made your club a "Promising club in Europe" and the
      rival a "World-class club"
- [x] Finances: the accounts in block 5 (12 income and 23 payment types,
      this month at `+0x0` and this season at `+0x130`, the report screen's
      7 + 5 groups) and the season plan at block 1 `+0x12470` (ad budget,
      ticket prices, season tickets). All 35 types and the 12 report
      lines named from the report screen's text (category 550), matching
      the 16 types traced in the code. `save.py finances` prints both
- [x] Season plan edits: `save.py set ... plan:ad_budget=`, `ticket_price=`,
      `season_ticket_rate=`, `season_tickets=` within the plan screen's
      limits (user report; the same ranges in pounds and euros in the
      stored unit), with season tickets capped at 80% of the stadium's
      capacity (block 1 `+0x4e99`, `pwkUnkei_GetStandAllCapacity`) and the
      season-ticket price set as the screen does. Tested in PCSX2: the
      Administrative Plan showed €2,000,000, €30, 80 and 50,000 as set, and
      the stadium capacity (110000) that save.py computes
- [x] The youth block: the youth candidates (block 1 `+0x97f8`, 30 × 12
      bytes: id, main position, age, turns left) and the four other
      candidate lists (players, managers, coaches, scouts) with their
      countdown. The youth join list isn't in the save and youth training
      isn't stored. `save.py candidates` lists them all with names

## 11. Editor GUI

- [x] The shape: one `SRC/editor.py` with a tab per kind of data, saving
      to a mod folder laid out like `DAT/` (files from outside `DATA.CVM`
      under `disc/`), which matches `patch_disc.py`'s targets. The editor
      reads the mod's copy of a file when there is one. Each tab edits
      through its writer's own functions and takes field names and allowed
      values from the writer (`pbdata.edit_spec`, `value_label`,
      `item_label`); every save logs the equivalent command to
      `editor.log`
- [x] People tab on `pbdata.py`: players, managers and scouts; search by
      name or id, nationality and club (`OTEAMMEMBER.TBB`); every named
      field with its documented range or named values, unnamed fields
      read-only, refused values explained; the screen bars and position
      grid follow the edits. It notes when a squad player's age and shirt
      come from `OTEAMMEMBER.TBB`. A save re-sorts the ranking and writes
      `disc/SLES_541.51` when an edit changes it. Checked: a save with six
      edits (name, height, ability, skills, rank, a manager's leaning)
      equals the logged `pbdata.py set --sles` output byte for byte, a
      second session builds on the mod's copies, and `pbdata.py roundtrip
      --sles` finds the mod's pack and executable consistent
- [x] Tested in PCSX2: an edit made only in the editor shows in game. Van
      der Sar (250, Manchester) edited in the People tab and put on a disc
      with `patch_disc.py --copies --skip-tutorial`: his detail screen
      shows 8 ft 4 in (255 cm), 7 st 1 lb (45 kg), LEFT (leg 2), full bars
      and every position cell lit. Age 36 and shirt 19 came from
      `OTEAMMEMBER.TBB`, not the edited 16 and 69, as the editor's note
      says. The kit style (long sleeves, GK pants, gloves, boots) wasn't
      checked in a match
- [x] Clubs tab on `initteam.py`: the 457 club records (named fields with
      their documented ranges; managers, stadiums, cities and states by
      name; unnamed bytes read-only) and the 439 squads (player, age,
      shirt, contract per slot, named from the People tab's records). It
      refuses a player already in another squad, a repeated shirt number
      and a manager who already has a club, as `initteam.py info` would
      flag them. A squad save refreshes the People tab's club notes.
      Checked: a save with 7 edits (and 4 refused) equals the logged
      `initteam.py set` and `setteam` output byte for byte, and `info`
      over the result has no `!!`
- [x] Tested in PCSX2: a Clubs-tab edit shows in game. Van der Sar
      (Manchester slot 0) set to age 16 and shirt 69 in the editor, on a
      disc with the earlier People edits (`patch_disc.py --copies
      --skip-tutorial`): his detail screen shows age 17 (one year more:
      the tutorial skip starts a season on, see the ages note in
      `TEAMINIT_FORMAT.md`) and 69 in the shirt badge, with the People
      edits intact
- [x] Build a modded disc from the editor: File > Build disc runs
      `patch_disc.py patch ... --copies` with every file in the mod folder
      (`disc/` files as `disc:` targets), then optionally `vcdiff.py make`
      against the original, shows their output and logs both commands.
      Paths and options are kept in `build.json` in the mod folder. It
      warns when the original isn't the Redump dump (by size before, and
      by `vcdiff.py`'s SHA-1 after). Checked: a build took 15 seconds,
      the 10,647-byte patch applied to the Redump image gives the built
      disc byte for byte, and `patch_disc.py verify` finds both edited
      files on it
- [x] Build disc writes a patch without keeping an image: the dialog
      offers a disc image, an xdelta patch or both. For a patch alone it
      builds `<patch>.building.iso`, makes the patch and removes the image
      (also after a failure or a stop), and checks for the free space
      first. Checked: a patch-only build gives the same patch byte for
      byte (SHA-1 `2448a83d…`) as the full build, and leaves no image
- [x] New club tab on `teaminit.py`: one page per league and team style
      as `pwkTeam_Init2` reads `TEAM_INIT_DATA.TBB` (the 18 squad records
      the club takes, the 4 rival-only ones, staff, scouts, the league's
      youth team and candidate lists, and the rival's manager, stadium and
      club bytes). Ids are named from the People tab and flagged when the
      player is also in a computer squad; salaries show their pound value.
      Ages and contracts get the documented ranges (`teaminit.EDIT_RANGES`).
      `teaminit.py set` now writes through `set_field` and `encode_file`
      (same output as before). Checked: a save with 9 edits (3 refused)
      equals the logged `teaminit.py set` output byte for byte
- [x] Tested in PCSX2: a New club edit shows in a new career. England /
      Counter-Attack records 0-17 set to age 16 in the New club tab, the
      disc built with the editor's Build disc (`--skip-tutorial`): the
      Club House squad list shows the same players, all aged 17, in
      2006-07. The extra year fits the skip starting a season on (noted in
      `TEAMINIT_FORMAT.md`; a check without the skip is in TODO section 2)
- [x] Kits tab on `uniform.py`: every club's home and away outfield and
      keeper kits (UNIFORM_LIST), with each colour named ("A4 red 4") and
      shown as a swatch from its palette, licensed clubs marked, and the
      keeper kit table (UNIFORM_GK) by outfield shirt design with its
      keeper design's 6 schemes. Values the game would reset are not
      offered (`uniform.edit_range`); unnamed fields are read-only.
      `uniform.py set` takes several teams now, and `set`/`setgk` write
      through `set_row_field`/`apply_gk_edit` (same output as before).
      Checked: a save with 5 edits (4 refused) equals the logged `set` and
      `setgk` output byte for byte
- [x] Tested in PCSX2 (user report): a Kits-tab edit shows in game.
      Birmingham's home outfield and keeper kits and away shirt colour 1
      (21 fields, `UNIFORM_LIST.TBB`), built with Build disc without the
      tutorial skip
- [x] Text tab on `mbb.py`: every message of MES.PAC by category (with
      what its range holds), text or id in any language, shown and edited
      in all 7 language slots with the file's room left. An edit with a
      bad {tag}, a character the language's code page lacks, or that
      would make its file too big for its slot is refused as it is made.
      `mbb.py` gets `MesPack`, which `set`, `import` and the editor use
      (same output as before), and `set` takes several messages. Checked
      through the widgets: a save with 2 messages (2 refused), one file
      grown, equals the logged `mbb.py set` output byte for byte
- [x] Tested in PCSX2 (user report): a Text-tab edit shows in game. Seven
      English club names (category 3: Arsenal, Man Utd, Man City, Aston
      Villa, Schalke, Sheffield W, Cardiff), built with Build disc: the
      names show in VS mode Team Selection, read from the `STATIONMES1.PAC`
      copy that `--copies` updates. All five tabs are now tested in game
- [x] Tested in PCSX2 (user report): event dialogue edited through a
      variable. Category 1 messages 760-783 (the rival owners' names,
      variable 131) all set to "The FRC" in the Text tab: the reporter in
      the Big Bang Konzern event called the rival owner "The FRC"
- [x] Build disc switches: boxes for `--sponsor-negotiation` and a new
      `patch_disc.py --launcher` (the developers' debug menu, the 1-byte
      `RootMainSeq.sqb` patch tested in PCSX2 before), next to the
      tutorial skip, remembered in `build.json`. Checked: all three
      switches in one build write the expected bytes, and the dialog's
      boxes add them to the command it runs
- [x] Season tab on `initteam.py`: each league's two starting divisions
      in last season's finishing order (`InitTeamData.past_record`), and
      swapping two league clubs picked from the lists or drop-downs.
      Checked through the widgets: two swaps (one across leagues) and a
      refused same-club swap; the save equals the logged `initteam.py
      swap` output byte for byte
- [x] Tested in PCSX2: a Season-tab swap shows in the first season.
      Chelsea (1st of the Premier Division last season) swapped with
      Sheffield (24th of 24 in the Champions Division), built with the
      tutorial skip: in 2006-07 Chelsea plays in the Champions Division.
      The second division keeps its last season's ranks 7-26, and there
      is no third tier (user report)

- [x] Tested in PCSX2: a keeper scheme (`UNIFORM_GK`) edited in the Kits
      tab shows on your club's keeper in a match (user report)
- [x] Tested in PCSX2: the welcome mail's body rewritten in the Text tab
      shows on the Mail screen, sender filled in. The window wraps at its
      width, not at spaces, so long edits need their own line breaks
      (user report)
- [x] Tested in PCSX2: a Season-tab swap across leagues. F.C. Barcelona
      in the Champions Division has fixtures there in 2006-07 and keeps
      Spain on its Information page. League Ranking is the current
      table place, so "-" before the first league match (user report)
