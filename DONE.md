<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Done

Finished items from [`TODO.md`](TODO.md), under the same section
numbers. Each line says what was done and where it is documented; the
doc holds the details, the evidence and how it was tested. The git
history holds the rest.

## 1. Read: every file parsed and checked

- [x] Decrypt `DATA.CVM`: the ROFS key, first recovered in PCSX2 and then
      derived from the `CVMH` header; `rofs_decrypt.py` and
      `extract_disc.py` (Redump check, extraction, no mounting)
      ([`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md))
- [x] Archives: BINPAC, `.HED`, KC@P and PRSH (`pac.py`), `etc::PackData`
      (`packdata.py`), `TBB1`/`TBL1` tables (`tbb.py`)
      ([`PAC_FORMAT.md`](DOC/PAC_FORMAT.md), [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md),
      [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md))
- [x] Game code: about 12,600 symbols from `.sndata`, the 323 overlay
      import sites, the developers' field table (`sles_disasm.py`); the
      SNR2 overlays, their loader, which overlay holds each sequencer
      module, and C++ classes from type information (`snr2.py`)
      ([`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md))
- [x] Message text: `MES.PAC`'s 3,738 `MBB1` files in 7 language slots,
      escape codes, encodings ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md))
- [x] The event tables and the unused turn-event prototype
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md))
- [x] `PARAM/`: every file's loader and layout
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md)); the player database
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md)); starting leagues,
      squads, club records, nations and stadiums
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md)); the new club
      ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md)); the schedule packs
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md)); regulations,
      results, training and camps
      ([`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md),
      [`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md),
      [`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md),
      [`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md)); both resource packs
      ([`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md)). Every
      `TBB1` table in `PARAM/` has a known layout
- [x] Graphics: Ninja textures with GS unswizzling, 2D screen layouts,
      depth buffers, and Ninja models and motions with OBJ and skinned
      glTF export (all 54,051 blobs with `--prs`)
      ([`SVR_FORMAT.md`](DOC/SVR_FORMAT.md), [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md),
      [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md), [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md))
- [x] Sound: the AFS/ADX archives decoded to WAV with loop points
      ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md)); `SOUNDDAT.PAC`, the DTPK banks,
      SoundFactory songs as MIDI and rendered with the banks' own
      instruments, the executable's bank and music tables
      ([`GAME_DIR.md`](DOC/GAME_DIR.md), [`SOUND_DIR.md`](DOC/SOUND_DIR.md))
- [x] Folder docs for every `DAT/` folder but `BG/`: `0SYSTEM`,
      `ACROBATA`, `EMBLEM`, `GAME`, `NEWS`, `PARAM`, `PLAYER`, `PRELOAD`,
      `SEQ`, `SOUND`, `STADIUM`, `TEST3D` and the `CVS/` metadata, with
      `system.py`, `acrobata.py`, `emblem.py`, `news.py`, `stadium.py`,
      `preload.py` and `cvs.py`
- [x] The match's own files: the play books and combination scripts
      (`bpb.py`, `sqb.py`; [`BPB_FORMAT.md`](DOC/BPB_FORMAT.md)) and
      `GAMEDATA.BIN`'s ball-contact records (`gamedata.py`;
      [`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md))
- [x] Sequencer scripts: the root scripts and the PwkScript formulas,
      their command sets, labels, global memory and data tables
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md), [`SEQ_DIR.md`](DOC/SEQ_DIR.md))
- [x] Memory-card saves: Blowfish, the layout CRC, and the ten blocks
      decoded by running the game's own serializers (`save.py`)
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] The Japanese release (SLPM-66316): extracted by `extract_disc.py`,
      PAL addresses found in it by `gamever.py` (all 27), read by most
      tools and checked by `regress.py` as `jp_` checks, including the
      65,501-clip `BC_JPN.AFS` ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md))
- [x] `regress.py`: every tool's `info` (and every `roundtrip`) over
      `DAT/`, compared with a saved baseline; one problem marker, `!!`,
      in every tool, and appeared or vanished `!!` lines both reported
- [x] `GAME/CUTINPACK`: all 277 entries are `etc::PackData` starting with
      a `CIB0` block; none is empty, as the folder doc had said
      ([`GAME_DIR.md`](DOC/GAME_DIR.md#directory-overview))
- [x] `DAT/BG`, the last folder doc: the room codes and slots, people,
      hands, props and trophies, and `HUMANID.BIN` read by `humanid.py`
      ([`BG_DIR.md`](DOC/BG_DIR.md))

## 2. Understand: field meanings an edit needs

- [x] Message variables: the 880 global variables and the wildcard ids
      (`mbb.py vars`); `ESC 0xC3` is the talk scenes' body reaction
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md))
- [x] The game's flow from the root scripts: boot, new game, load
      results, the season loop, the main menu, match day, game over, the
      event timings ([`GAME_FLOW.md`](DOC/GAME_FLOW.md))
- [x] Events: scene types, talk types, event id types, the code-only
      procedures 9–29, the scout-list criteria and squad limits, the
      event clock in turns ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md))
- [x] Which copy of a file the game reads: a loaded `PRELOAD` pack's
      copy, else the original; every copy is read somewhere
      ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md))
- [x] Every player and staff field named, from the developers' editors
      in `DEBUGPRG.REL` and their field table: abilities, personality,
      kit style, play styles, skills, tendencies, positions and
      aptitude, the detail screen's bars and hexagon, staff jobs and
      abilities ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [x] The match's player parameters, which `fb::` class reads each, and
      the kick kinds' ratings ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-match-engines-player-parameters))
- [x] Player id blocks, the ranking in entries 2 and 3, national-team
      call-ups, and which free agents the Transfer List shows
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#player-id-blocks),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#which-free-agents-the-transfer-list-shows))
- [x] Where a division's clubs come from, and the game days a league of
      another size can use ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md))
- [x] Every field of `REGULATION.TBB` but one, all of `CLUBRESULT.TBB`,
      the 13 training tables, the camp tables and their two bugs
- [x] Injuries: how they are rolled, the value table, recovery and the
      condition line ([`INJURIES.md`](DOC/INJURIES.md))
- [x] Saves: money and currencies, the date, the squad, condition and
      form, pair combinations, staff and dissatisfaction, the other
      clubs, club rank and reputation, the club's status, the accounts
      and the season plan, the candidate lists
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] What each PwkScript computes: only the detail-screen comments run
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#what-the-pwkscripts-compute))
- [x] The developer launcher: every entry named and tried
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-developer-launcher))
- [x] Kits: every club's kits, the colour clash table, the licensed kits'
      descriptors and the keeper kits ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md));
      stadium build requests, crowds and adverts
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md))

- [x] The kick kinds' table (`GAMEPRG.REL 0x29f680`, filled at
      `0x704f0`): flags for all 41 kinds, sorting them into passes,
      through passes, long balls, crosses, shots, throw-ins and restarts
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-kind-table))
- [x] Where each kick kind is made: the corner (36, 37), free-kick (38–40)
      and throw-in kinds, and the intention behind each in-play pass,
      cross and shot kind ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#where-each-kind-is-made))
- [x] The `COMBINATION2.CBB` record layout (`bpb.py cbb`), the
      combination roles' eight modes and what each of the 29 combination
      commands does ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#cbb-records))

## 3. Write: a writer for every format a mod changes

- [x] `tbb.py`: all 70 `.TBB`/`.BCR`/`.BCB` files round-trip; `replace`
      swaps a whole table
- [x] `pac.py`: all 662 BINPACs round-trip; KC@P packs rebuild; PRS
      compression checked over all 5,496 PRSH entries
      ([`PAC_FORMAT.md`](DOC/PAC_FORMAT.md))
- [x] `pbdata.py`: all 31,950 records round-trip; `set` and CSV
      `import`; `--sles` re-sorts the ranking and patches the executable
- [x] `mbb.py`: all 461,992 records round-trip; `set` and CSV `import`;
      a file may grow into its slot or past it
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#writing))
- [x] `initteam.py` (`set`, `setteam`, `swap`), `teaminit.py`,
      `plrsim.py setfree`, `uniform.py` (`set`, `setlicence`, `setexe`,
      `setgk`), `regulation.py`, `clubresult.py`, `training.py`,
      `camp.py`, `formset.py`, `tour.py`: field-level writers, each with
      a `roundtrip` in `regress.py`
- [x] `schedule.py`: re-encodes all three schedule packs with their
      `.HED`; builds league schedules of 2–32 clubs, finds free turns and
      shifts game days. `leaguesize.py build` changes a first division's
      size ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [x] `sqb.py`: every script re-encodes; `setcmd`, `set_commands` and
      `settable` (the PwkScript data tables)
- [x] `save.py set`: money, status, abilities, condition, combinations,
      staff, other clubs and the season plan; every save round-trips

## 4. Rebuild: edits back on a bootable disc

- [x] `patch_disc.py`: same-size patching without re-encryption, files
      outside `DATA.CVM` (`disc:`), renaming outer files
      ([`REBUILD.md`](DOC/REBUILD.md))
- [x] Copies: `--copies` finds and updates every copy, and rebuilds
      `PRELOAD` packs around entries that change size
- [x] Size changes inside a file's last sector, files moved to the end
      of `DATA.ISO` with the table of contents re-keyed, and a disc that
      grows past its free sectors
- [x] Archive rebuilds: `MES.PAC` and the Acrobata pack with the
      executable's index rewritten, `.HED` archives with their header
      copies, KC@P packs and PRS entries. All tested in PCSX2
      ([`REBUILD.md`](DOC/REBUILD.md#archives))
- [x] Testing aids: `--skip-tutorial` (runs the playoffs' schedule steps
      without their matches) and `--launcher` (the developers' debug
      menu) ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md))

## 5. Edit: the GUI

- [x] `editor.py`: one window, a tab per kind of data, saving to a mod
      folder laid out like `DAT/` and logging the equivalent command;
      each save equals that command's output byte for byte
- [x] Tabs: People, Clubs, New club, Season (swaps and first-division
      sizes), Free agents, Regulations (with the results), Training,
      Camps, Kits (with licensed kits and keeper kits) and Text. All but
      the Regulations, Training and Camps saves and the Season tab's size
      change are tested in PCSX2
- [x] File > Build disc: a modded image, an xdelta patch or both, with
      boxes for `patch_disc.py`'s switches
- [x] Save editor steps 1–3: `save.py spec` and `saveedit.py`, with every
      page that `save.py set` can write; the Club page is tested in PCSX2
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md))
- [x] Save editor: File > Save to new slot, and `save.py copy`, which
      copy a save to the card's next free slot and leave the original as
      it is ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md#decisions))

## 6. Distribute: sharing a mod

- [x] `vcdiff.py`: makes and applies xdelta (VCDIFF) patches in plain
      Python; Delta Patcher applies them with the same result
      ([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod))
- [x] Separate saves for a modded disc: `--mod-saves` keeps the serial
      (and so PCSX2's GameDB fixes), `save.py rename` moves a save, and
      every patch prints the executable's PCSX2 CRC
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))

## 7. Tests in PCSX2

Each result is recorded in the doc named.

- [x] Player database edits, VS-mode national squads, play styles, kit
      style and rank changes ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [x] Message edits, a grown file, a moved file and rebuilt `PRELOAD`
      copies; which copy each screen reads
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#tested-in-pcsx2),
      [`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#tested-in-pcsx2))
- [x] Squad and club edits, swaps within and across leagues
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md)); the new club's
      squad, staff and candidate lists
      ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md)); free agents
      ([`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md))
- [x] England's first division at 22 clubs, through two seasons
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md))
- [x] A regulation edit (squad size and win bonus)
      ([`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#tested-in-pcsx2))
- [x] Kit, licensed-kit and keeper-kit edits
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#tested-in-pcsx2))
- [x] An edited detail-screen comment script
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-detail-screen-comments))
- [x] Save edits: money, status, combinations, staff, other clubs and the
      season plan ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] The disc rebuilds: moved and grown files, a grown disc, rebuilt
      archives ([`REBUILD.md`](DOC/REBUILD.md))
- [x] By ear: the music, opening, victory tune, crowd loops, chants and
      the `SYS_SE`/`EFFECTS` banks; the rendered songs
      ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md), [`GAME_DIR.md`](DOC/GAME_DIR.md))
- [x] `--mod national-cups`: the World Cup final (season 4) moved to
      turn 94 taken to work, since the retail Euro final on 94 shows its
      results afterwards ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [x] The camp switches `camp-cities`, `camp-santiago` and `camp-clubs`,
      and `camp-types` (a keeper camp trains keeping, read from save
      states) ([`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md))

## 8. LMASTER Mod and other patches

- [x] Main sponsor negotiation restored (`--mod sponsor-negotiation`),
      tested in PCSX2 ([`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md))
- [x] The rival's manager by style (`--mod rival-manager`), tested in
      PCSX2 ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#the-rival-club-tables-6-7-and-8))
- [x] Built: the national cups a turn earlier (`--mod national-cups`,
      tested) and the four camp switches; `--mod lmaster` turns
      the mod's fixes on together ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [x] Widescreen: a PCSX2 pnach for Hor+ 16:9 3D with the HUD, menus,
      backdrops, room changes, room depth and cut-ins kept at 4:3, tested
      in PCSX2 ([`WIDESCREEN.md`](DOC/WIDESCREEN.md))
