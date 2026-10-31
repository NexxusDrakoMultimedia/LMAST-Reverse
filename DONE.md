<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Done

What's finished, under the same section numbers as
[`TODO.md`](TODO.md). Each line links the doc that holds the details,
the evidence and how it was tested; the git history holds the rest.

## 1. Read: every file parsed and checked

- [x] `DATA.CVM` decrypted and the disc extracted, checked against
      Redump ([`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md))
- [x] Archives and tables: BINPAC, `.HED`, KC@P, PRSH, `etc::PackData`,
      `TBB1`/`TBL1` ([`PAC_FORMAT.md`](DOC/PAC_FORMAT.md),
      [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md))
- [x] Game code: about 12,600 symbols, the overlays and their loader,
      the developers' field table, C++ classes
      ([`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md))
- [x] Every `DAT/` folder has a doc and a tool
      ([coverage table](GOALS.md#coverage-of-datacvm)): text, events,
      `PARAM/`, graphics, models, sound, the match's play books and
      combinations, the sequencer scripts, crests and the player
      editor's tables
- [x] Memory-card saves, decoded by running the game's own serializers
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] The Japanese release extracted, with every PAL address the tools
      use found by `gamever.py`
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md))
- [x] `regress.py`: every tool's `info` and `roundtrip` against a
      baseline ([`README.md`](README.md#how-the-tools-fit-together))

## 2. Understand: field meanings an edit needs

- [x] Every player and staff field named, with the match's readers of
      each, staff careers and policies, kit style and the tendencies
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [x] The starting season: where a division's clubs come from, leagues
      of another size, regulations, results, free agents
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md),
      [`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md))
- [x] The club game: the economy, injuries, training and camps, the
      money limits ([`ECONOMY.md`](DOC/ECONOMY.md),
      [`INJURIES.md`](DOC/INJURIES.md),
      [`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md),
      [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#salary-limits))
- [x] Text, events and flow: message variables, the event tables and
      procedures, the root scripts, what each PwkScript computes
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md),
      [`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`GAME_FLOW.md`](DOC/GAME_FLOW.md),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md))
- [x] Kits, stadiums and crowds, and which copy of a file the game reads
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md),
      [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md),
      [`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md))
- [x] The match AI: which play is which, the combinations, the zone
      network, `Combi2`'s and most of `Combi3`'s areas
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md))
- [x] Saves field by field, and Virtua Pro Football's edit players
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md),
      [`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md))
- [x] The club and schedule limits the third tier needed
      ([`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md),
      [`UID_LIMITS.md`](DOC/UID_LIMITS.md))
- [x] The press tendency's team cap: always 2 in a career match, so
      levels 2–4 act as 1
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-tendencies))
- [x] The carry and press tendencies in the roles: carry is the
      player's own and decides how long he keeps a play; press sets how
      far from the ball carrier the marker stands and how close counts
      as on him ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-tendencies))
- [x] The travelling salesman's items and their match boosts, the only
      code besides the hexagon that reads abilities 59–63
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#the-salesmans-items))

## 3. Write: a writer for every format a mod changes

- [x] Containers and text: `pac.py`, `tbb.py`, `mbb.py`, `sqb.py`
      ([`PAC_FORMAT.md`](DOC/PAC_FORMAT.md),
      [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md),
      [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#writing),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#tool))
- [x] The starting season and the tables: `pbdata.py`, `initteam.py`,
      `teaminit.py`, `plrsim.py`, `plrcommon.py`, `regulation.py`,
      `clubresult.py`, `training.py`, `camp.py`, `formset.py`, `tour.py`,
      `clubrank.py`, `natcal.py`, `clubevent.py`
      ([`README.md`](README.md#archives-and-tables))
- [x] Schedules: `schedule.py` and `leaguesize.py build`, leagues of
      2–32 clubs and cups of 2–128
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md))
- [x] Kits, crests and stadiums: `uniform.py`, `emblem.py`, `stadium.py`
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md),
      [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#editing),
      [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#editing))
- [x] Saves and cards: `save.py set`, `pmplayer.py set`, `ps2mc.py`
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#editing),
      [`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#editing),
      [`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md))

## 4. Rebuild: edits back on a bootable disc

- [x] `patch_disc.py`: files of any size, moved files, a grown disc,
      every copy updated, archives rebuilt
      ([`REBUILD.md`](DOC/REBUILD.md))
- [x] Testing aids: `--skip-tutorial` and `--launcher`
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs))
- [x] The Japanese disc: every switch but `third-tier`, and its saves
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))

## 5. Edit: the GUI

- [x] `editor.py`: a tab for every writer of game data, each save equal
      to its logged command, and File > Build disc
      ([`USAGE.md`](USAGE.md#the-mod-editor))
- [x] `saveedit.py`: every page `save.py set` can write, Save to new
      slot, card files
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md))

## 6. Distribute: sharing a mod

- [x] `vcdiff.py`: xdelta patches in plain Python, xdelta3's own
      included ([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod))
- [x] `cso.py` and `chd.py`: compressed images read directly
      ([`REBUILD.md`](DOC/REBUILD.md#compressed-images))
- [x] Separate saves for a modded disc
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [x] The players' guide, [`INSTALL.md`](INSTALL.md)

## 7. Tests in PCSX2

Each result is recorded in the doc linked.

- [x] Edits through the writers: the player database, squads and clubs,
      free agents, regulations, kits, training, facilities, messages,
      a starting crest, a PR event
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md),
      [`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#tested-in-pcsx2),
      [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#tested-in-pcsx2),
      [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#editing),
      [`CLUBEVENT_FORMAT.md`](DOC/CLUBEVENT_FORMAT.md#editing))
- [x] England's first division at 22 clubs over two seasons
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [x] The disc rebuilds, saves edited and copied, cards written by
      `ps2mc.py` ([`REBUILD.md`](DOC/REBUILD.md),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md),
      [`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md#writing))
- [x] By ear: the music, opening, crowd, chants and effects banks
      ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md))
- [x] Virtua Pro Football loads an edited `pmplayer.bin`, and the player
      imports ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#editing))
- [x] The LMASTER switches marked tested, each on its test disc,
      including the third tier over a German season, the real names, the
      2005-06 grounds and a season on LMASTER max
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))

## 8. LMASTER Mod and other patches

- [x] LMASTER lite: the fixes for training camps, drill names,
      injuries, the main sponsor negotiation, season tickets, PR events,
      overseas popularity, cup popularity, the rival's manager, the press
      tendency, the national cups, VPF play styles and the retail text
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [x] LMASTER full: the third tier, balanced league schedules, the cut
      injury lines, real names, your own stadium, real grounds, sponsor
      boards and separate saves
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] LMASTER max: the harder economy and the balance switches
      ([`ECONOMY.md`](DOC/ECONOMY.md),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] The switch levels: editions, groups and switches, in
      `patch_disc.py` and the Build disc window
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels))
- [x] Widescreen: a PCSX2 pnach for 16:9 with the 2D kept at 4:3
      ([`WIDESCREEN.md`](DOC/WIDESCREEN.md))
