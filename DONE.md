<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Done

Finished items from [`TODO.md`](TODO.md), under the same section
numbers, one or two lines each. The doc linked holds the details, the
evidence and how it was tested; the git history holds the rest.

## 1. Read: every file parsed and checked

- [x] `DATA.CVM` decrypted with a key derived from its header;
      `extract_disc.py` checks a dump against Redump and extracts it
      ([`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md))
- [x] Archives and tables: BINPAC, `.HED`, KC@P, PRSH, `etc::PackData`,
      `TBB1`/`TBL1` ([`PAC_FORMAT.md`](DOC/PAC_FORMAT.md),
      [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md), [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md))
- [x] Game code: about 12,600 symbols, the overlay imports and loader,
      the developers' field table, C++ classes
      ([`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md))
- [x] Message text: 3,738 `MBB1` files in 7 language slots
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md))
- [x] The event tables and the unused turn-event prototype
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md))
- [x] `PARAM/`: every file's loader and layout, every `TBB1` table
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md))
- [x] Graphics: textures, 2D layouts, depth buffers, Ninja models and
      motions with OBJ and glTF export ([`SVR_FORMAT.md`](DOC/SVR_FORMAT.md),
      [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md), [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md),
      [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md))
- [x] Sound: AFS/ADX to WAV, the DTPK banks, songs as MIDI and WAV, the
      bank and music tables ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md),
      [`GAME_DIR.md`](DOC/GAME_DIR.md), [`SOUND_DIR.md`](DOC/SOUND_DIR.md))
- [x] A folder doc and tool for every `DAT/` folder and the `CVS/`
      metadata ([coverage table](GOALS.md#coverage-of-datacvm))
- [x] The match's files: play books, combination scripts and
      `GAMEDATA.BIN`'s container ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md),
      [`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md))
- [x] Sequencer scripts and PwkScripts: command sets, labels, global
      memory, data tables ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md))
- [x] Memory-card saves, decoded by running the game's own serializers
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] The Japanese release: extracted, every PAL address the tools use
      found by `gamever.py`, checked as `jp_` checks
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md))
- [x] `regress.py`: every tool's `info` and `roundtrip` against a
      baseline, one problem marker (`!!`) in every tool
      ([`README.md`](README.md#how-the-tools-fit-together))

## 2. Understand: field meanings an edit needs

- [x] Message variables and wildcard ids, and the talk scenes' body
      reactions ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md))
- [x] The game's flow from the root scripts ([`GAME_FLOW.md`](DOC/GAME_FLOW.md))
- [x] Events: scene, talk and id types, the code-only procedures, the
      event clock ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md))
- [x] Which copy of a file the game reads: every copy is read somewhere
      ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md))
- [x] Every player and staff field named; the match's player parameters
      and their readers; player id blocks, the ranking, call-ups
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [x] Which free agents the Transfer List shows
      ([`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#which-free-agents-the-transfer-list-shows))
- [x] Where a division's clubs come from, and the game days a league of
      another size can use ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md))
- [x] Regulations, results, training and camps, with the camps' two bugs
      ([`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md),
      [`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md),
      [`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md),
      [`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md))
- [x] Injuries: the roll, the value table, recovery and the condition
      line ([`INJURIES.md`](DOC/INJURIES.md))
- [x] Saves: money, date, squad, staff, other clubs, accounts, season
      plan, candidates, club status ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] What each PwkScript computes, and every developer launcher entry
      named ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md))
- [x] Kits, the clash table, licensed and keeper kits
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md)); stadium requests,
      crowds and adverts ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md))
- [x] The money limits: salaries £10,000–£12,000,000 in steps of £10,000
      ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#salary-limits))
- [x] Virtua Pro Football's `pmplayer.bin` and how the import converts
      each field ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md))
- [x] The economy: build costs, the plan's limits, attendance, income,
      popularity, sponsors, TV, merchandise, fees, PR events, camps and
      tours ([`ECONOMY.md`](DOC/ECONOMY.md))
- [x] The combinations: the `.CBB` records, the 29 commands, which a team
      gets and which runs ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#how-a-team-uses-the-combinations))
- [x] Which play is which: corner and free-kick plays by zone, the
      tactics screen's attack pattern diagrams
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#which-play-is-which))
- [x] The club and schedule limits the third tier needed: every site of
      440–442 and of 164 ([`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md),
      [`UID_LIMITS.md`](DOC/UID_LIMITS.md))
- [x] Kit style's cap and outfield gloves (the cap is an edit player's
      face part; gloves need a career match below 10 degrees), and the
      pass tendencies are the passer's ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#kit-style))
- [x] Staff careers and policies: where jobs 5 and 6 are set, how players
      become coaches or scouts and coaches managers, and the 25 policies
      as a grid with the range diamonds ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#manager-coach-and-scout-bars))

## 3. Write: a writer for every format a mod changes

- [x] `tbb.py` (all 70 table files), `pac.py` (all 662 BINPACs, KC@P,
      PRS), `pbdata.py`, `mbb.py` round-trip ([`TBB_FORMAT.md`](DOC/TBB_FORMAT.md),
      [`PAC_FORMAT.md`](DOC/PAC_FORMAT.md), [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#writing))
- [x] Field-level writers with a `roundtrip` each: `initteam.py`,
      `teaminit.py`, `plrsim.py`, `uniform.py`, `regulation.py`,
      `clubresult.py`, `training.py`, `camp.py`, `formset.py`, `tour.py`
      ([`README.md`](README.md#archives-and-tables))
- [x] `schedule.py` and `leaguesize.py build`: the schedule packs, league
      schedules of 2–32 clubs, a first division's size
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [x] `schedule.py knockout`: cup brackets of 2–128 clubs, 71 of the
      disc's 87 knockouts rebuilt byte for byte
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#building-a-knockout))
- [x] `sqb.py`: every script re-encodes; `setcmd`, `set_commands`,
      `settable` ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#tool))
- [x] `save.py set`, the edit player included
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#editing)); `pmplayer.py set`
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#editing))
- [x] `plrcommon.py set`: the facility records
      ([`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md#editing-the-facility-records))
- [x] `clubrank.py`: `CLUB_RANK_SYSTEM.TBB`, with `addrows` for resized
      leagues ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables))
- [x] `clubevent.py`: the 46 PR events in the executable, on both
      releases ([`CLUBEVENT_FORMAT.md`](DOC/CLUBEVENT_FORMAT.md))
- [x] `natcal.py`: the national-team calendar
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#schedule_listtbb-the-national-team-calendar))
- [x] `plrsim.py setgroup` and `setbranch`, `initteam.py setnation` and
      `setstadium` ([`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#writing-the-streams),
      [`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md))
- [x] `ps2mc.py`: PCSX2 memory card images read and written
      ([`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md))

## 4. Rebuild: edits back on a bootable disc

- [x] `patch_disc.py`: same-size patching, size changes, moved files, a
      grown disc, every copy updated, archives and indexes rebuilt
      ([`REBUILD.md`](DOC/REBUILD.md))
- [x] Testing aids: `--skip-tutorial` (with `--skip-nation`) and
      `--launcher` ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs))
- [x] The switches on the Japanese disc, through `gamever.py`; all but
      `third-tier` ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))
- [x] `save.py --iso ISO_JP`: Japanese saves read, edited and re-encoded
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-japanese-release))

## 5. Edit: the GUI

- [x] `editor.py`: a tab for every writer of game data, each save equal
      to its logged command, tested through the widgets
      ([`USAGE.md`](USAGE.md#the-mod-editor))
- [x] File > Build disc: a modded image or patch, with the switch
      levels as edition buttons and group boxes
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels))
- [x] `saveedit.py` (steps 1–3 and 5): every page `save.py set` can
      write, Save to new slot, card files
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md))

## 6. Distribute: sharing a mod

- [x] `vcdiff.py`: xdelta patches in plain Python, and patches xdelta3
      makes (LZMA, DJW) ([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod))
- [x] Separate saves for a modded disc (`--mod-saves`, `save.py rename`)
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [x] The players' guide, [`INSTALL.md`](INSTALL.md)
- [x] `cso.py` and `chd.py`: CSO, ZSO and CHD images read directly
      ([`REBUILD.md`](DOC/REBUILD.md#compressed-images))

## 7. Tests in PCSX2

Each result is recorded in the doc named.

- [x] Player database edits, VS squads, play styles, kit style, ranks
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [x] Messages, grown and moved files, rebuilt `PRELOAD` copies
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#tested-in-pcsx2),
      [`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#tested-in-pcsx2))
- [x] Squads, clubs, swaps, the new club, free agents
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md),
      [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md))
- [x] England's first division at 22 clubs over two seasons
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [x] Regulations, kits, a detail-screen comment script, training
      ([`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#tested-in-pcsx2),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#tested-in-pcsx2),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-detail-screen-comments),
      [`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md#editing))
- [x] A facility cost edit
      ([`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md#editing-the-facility-records))
- [x] Save edits, a save copied to a new slot, a card written by
      `ps2mc.py` ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md),
      [`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md#decisions),
      [`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md#writing))
- [x] The disc rebuilds ([`REBUILD.md`](DOC/REBUILD.md))
- [x] By ear: the music, opening, crowd, chants and effects banks
      ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md), [`GAME_DIR.md`](DOC/GAME_DIR.md))
- [x] Virtua Pro Football loads a `pmplayer.py`-edited file, and the
      edited player imports ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#editing))
- [x] The LMASTER switches marked tested, each on its test disc
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [x] LMASTER full (2026-10-25): careers save to `BESLES-54151-M000`,
      transfer fees double, merchandise costs half its price
      ([`ECONOMY.md`](DOC/ECONOMY.md#transfer-fees),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [x] The third tier over a German season (2026-10-27): one club moved
      each way in Germany and England
      ([`UID_LIMITS.md`](DOC/UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3))
- [x] The third tier's clubs in Other Club Info, after its loop was run
      to club 459 ([`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md#--mod-third-tier-the-lists-phase-2b))

## 8. LMASTER Mod and other patches

- [x] Main sponsor negotiation restored (`sponsor-negotiation`)
      ([`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md))
- [x] The rival's manager by style (`rival-manager`)
      ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#the-rival-club-tables-6-7-and-8))
- [x] The national cups a turn earlier (`national-cups`) and the four
      camp switches ([`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [x] Widescreen: a PCSX2 pnach for 16:9 with the 2D kept at 4:3
      ([`WIDESCREEN.md`](DOC/WIDESCREEN.md))
- [x] `drill-names`: PAL's drill names 74–86 one message early, moved
      ([`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md#drills-7486-pals-names-are-one-early))
- [x] `league-balance`: no club plays more than two games running at
      one venue ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] `injury-value`, `injury-row`, `injury-odds` and `injury-lines`
      ([`INJURIES.md`](DOC/INJURIES.md))
- [x] `vpf-styles`: edit players keep their best play styles
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#the-record))
- [x] `season-status`: season tickets by club status
      ([`ECONOMY.md`](DOC/ECONOMY.md#season-tickets))
- [x] `--mod harder-economy`: six switches, each tested
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] `--mod balance`: eleven switches built after tracing merchandise,
      fees, popularity and the PR, camp and tour costs
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements),
      [`ECONOMY.md`](DOC/ECONOMY.md))
- [x] `pr-cycle`, `mobile-site`, `overseas-pop` and `cup-last16` (in
      LMASTER lite) ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [x] The third tier (`--mod third-tier`): the bigger save, clubs
      442–459 as full clubs, the tiers' leagues and movements, and their
      clubs in the lower cups ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements),
      [`UID_LIMITS.md`](DOC/UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3))
- [x] The switch levels: LMASTER lite and LMASTER full as editions of
      independent groups ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels))
- [x] LMASTER max: the difficulty groups split off from LMASTER full,
      with careers saved to `-F` (full) or `-M` (max) and VS data to `-V`
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [x] The harder economy played through a season on LMASTER max: much
      harder in a way a player notices (user report, 2026-10-27;
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] The third tier's text: the messages that state its rules, in the
      five European languages ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-text))
