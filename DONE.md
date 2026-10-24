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
- [x] Game code: about 12,600 symbols, the overlay imports, the
      developers' field table, the SNR2 overlays and their loader, which
      overlay holds each module, and C++ classes
      ([`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md))
- [x] Message text: 3,738 `MBB1` files in 7 language slots
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md)); the event tables and the
      unused turn-event prototype ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md))
- [x] `PARAM/`: every file's loader and layout, every `TBB1` table
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md) and the docs it links)
- [x] Graphics: textures, 2D layouts, depth buffers, Ninja models and
      motions with OBJ and glTF export ([`SVR_FORMAT.md`](DOC/SVR_FORMAT.md),
      [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md), [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md),
      [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md))
- [x] Sound: AFS/ADX to WAV, the DTPK banks, songs as MIDI and rendered
      WAV, the bank and music tables ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md),
      [`GAME_DIR.md`](DOC/GAME_DIR.md), [`SOUND_DIR.md`](DOC/SOUND_DIR.md))
- [x] A folder doc for every `DAT/` folder and the `CVS/` metadata, each
      with its tool (see the [coverage table](GOALS.md#coverage-of-datacvm))
- [x] The match's files: play books, combination scripts and
      `GAMEDATA.BIN`'s container ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md),
      [`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md))
- [x] Sequencer scripts and PwkScripts: command sets, labels, global
      memory, data tables ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md))
- [x] Memory-card saves, decoded by running the game's own serializers
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] The Japanese release: extracted, every PAL address the tools use
      found by `gamever.py`, checked by `regress.py` as `jp_` checks
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md))
- [x] `regress.py`: every tool's `info` and `roundtrip` against a
      baseline, with one problem marker, `!!`, in every tool

## 2. Understand: field meanings an edit needs

- [x] Message variables and wildcard ids, and the talk scenes' body
      reactions ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md))
- [x] The game's flow from the root scripts ([`GAME_FLOW.md`](DOC/GAME_FLOW.md))
- [x] Events: scene, talk and id types, the code-only procedures, the
      event clock ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md))
- [x] Which copy of a file the game reads: every copy is read somewhere
      ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md))
- [x] Every player and staff field named, the match's player parameters
      and which `fb::` class reads each, the kick kinds' table and where
      each kind is made, player id blocks, the ranking, call-ups
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
      plan, candidates ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md))
- [x] What each PwkScript computes, and every developer launcher entry
      named ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md))
- [x] Kits, the clash table, licensed and keeper kits
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md)); stadium requests,
      crowds and adverts ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md))
- [x] `COMBINATION2.CBB`'s record layout and what each of the 29
      combination commands does ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#cbb-records))
- [x] The money limits: salaries £10,000–£12,000,000 in steps of £10,000
      ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#salary-limits))
- [x] Virtua Pro Football's `pmplayer.bin` and how the import converts
      each field ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md))
- [x] The economy: build costs, the plan's limits, attendance, income
      and popularity ([`ECONOMY.md`](DOC/ECONOMY.md))
- [x] How a team uses the combinations: 11 per team, the trigger (block
      A's kind), the zone mask and distance limits (block C), and the
      slots as the participants' areas; records 0, 1, 4, 18 and 59 never
      start ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#how-a-team-uses-the-combinations))
- [x] Which combinations a team gets (8 from fixed tables by the style's
      attack speed and type, up to 3 from the club's attack patterns)
      and which runs (highest record first, pattern ones after a roll on
      parameters 72–74); only 65 of 540 records can load
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#how-a-team-uses-the-combinations))
- [x] `Combi17`–`Combi24`'s eight directions, and no reader of the
      `.CBB`'s A values, block B or C's words
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#the-combination-commands));
      `GAMEDATA.BIN` part 0 is the right foot and 1 the left, from the
      weak-foot check ([`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md))
- [x] Which play is which: 16 corner and 24 free-kick plays by zone,
      records 196–255 never used, `COMBINATION.BPB` as the tactics
      screen's attack pattern diagrams; path kinds as role types; the
      starting-positions block ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#which-play-is-which))

## 3. Write: a writer for every format a mod changes

- [x] `tbb.py` (all 70 table files), `pac.py` (all 662 BINPACs, KC@P,
      PRS), `pbdata.py` (31,950 records, `--sles`), `mbb.py` (461,992
      records; files may grow) round-trip ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#writing))
- [x] Field-level writers with a `roundtrip` each: `initteam.py`,
      `teaminit.py`, `plrsim.py setfree`, `uniform.py`, `regulation.py`,
      `clubresult.py`, `training.py`, `camp.py`, `formset.py`, `tour.py`
- [x] `schedule.py` and `leaguesize.py build`: the schedule packs, league
      schedules of 2–32 clubs, a first division's size
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [x] `sqb.py`: every script re-encodes; `setcmd`, `set_commands`,
      `settable`
- [x] `save.py set`, including the imported edit player
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md)); `pmplayer.py`, VPF's
      edit players ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md))
- [x] `plrcommon.py set`: the facility records, each of 494 fields
      checked ([`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md#editing-the-facility-records))

## 4. Rebuild: edits back on a bootable disc

- [x] `patch_disc.py`: same-size patching, size changes, moved files, a
      grown disc, every copy updated, archives rebuilt with their
      indexes, outer files and renames; all tested in PCSX2
      ([`REBUILD.md`](DOC/REBUILD.md))
- [x] Testing aids: `--skip-tutorial` and `--launcher`
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md))

## 5. Edit: the GUI

- [x] `editor.py`: a tab per kind of data (People, Clubs, New club,
      Season, Free agents, Regulations, Training, Camps, Facilities,
      Kits, Text), each save equal to its logged command, and File >
      Build disc for an image or patch ([`README.md`](README.md#editor))
- [x] `saveedit.py` (steps 1–3 and 5): every page `save.py set` can
      write, Save to new slot, and saves on card files
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md))
- [x] `ps2mc.py`: PCSX2 memory card images read and written
      ([`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md))
- [x] `editor.py` Tours, Tactics and Comments tabs (`tour.py`,
      `formset.py`, `sqb.py settable`, which now edits several scripts
      of a pack in one command), tested through the widgets
      ([`README.md`](README.md#editor))

## 6. Distribute: sharing a mod

- [x] `vcdiff.py`: xdelta patches in plain Python, applied the same by
      Delta Patcher ([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod))
- [x] Separate saves for a modded disc (`--mod-saves`, `save.py rename`)
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [x] The players' guide, [`INSTALL.md`](INSTALL.md)
- [x] `vcdiff.py apply` decodes patches xdelta3 3.1 and 3.2 made,
      including LZMA (their default) and DJW secondary compression
      ([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod))
- [x] `cso.py`: CSO and ZSO images read directly by `vcdiff.py` and
      `patch_disc.py` ([`REBUILD.md`](DOC/REBUILD.md#compressed-images))
- [x] `chd.py`: CHD v5 images (DVD, raw, one-track CD; every chdman codec
      but zstd on Python before 3.14) read by the same tools
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
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md))
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
- [x] The LMASTER Mod's switches and `--mod harder-economy`, each on its
      test disc ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))

## 8. LMASTER Mod and other patches

- [x] Main sponsor negotiation restored (`sponsor-negotiation`)
      ([`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md))
- [x] The rival's manager by style (`rival-manager`)
      ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#the-rival-club-tables-6-7-and-8))
- [x] The national cups a turn earlier (`national-cups`) and the four
      camp switches ([`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md)); `--mod
      lmaster` turns the fixes on together
- [x] Widescreen: a PCSX2 pnach for 16:9 with the 2D kept at 4:3
      ([`WIDESCREEN.md`](DOC/WIDESCREEN.md))
- [x] `drill-names`: PAL's drill names 74–86 one message early, moved
      ([`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md#drills-7486-pals-names-are-one-early))
- [x] `league-balance`: league schedules with no more than two games
      running at one venue ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] `injury-value` and `injury-row` ([`INJURIES.md`](DOC/INJURIES.md#the-kind-tables))
- [x] `vpf-styles`: edit players keep their best play styles
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#the-record))
- [x] `season-status`: season tickets by club status
      ([`ECONOMY.md`](DOC/ECONOMY.md#season-tickets))
- [x] `--mod harder-economy`: six switches, each tested
      ([`ECONOMY.md`](DOC/ECONOMY.md), [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] The LMASTER Mod split into LMASTER lite (`--mod lmaster-lite`, the
      fixes) and LMASTER full (`--mod lmaster-full`, every switch, with
      `mod-saves` always on); the editor's Build window has a button for
      each ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md))
- [x] `--mod balance` built: `injury-odds`, `injury-lines` (the cut two-
      and nine-month lines, with text in four languages), `overseas-bases`,
      `transfer-fees` and `fanbase`, after tracing merchandise, transfer
      fees and the overseas base levels ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements),
      [`ECONOMY.md`](DOC/ECONOMY.md#merchandise))
- [x] `merch-costs` (in `--mod balance`): merchandise stock at 50% of its
      price, bulk discounts halved, after tracing the goods screen's costs
      ([`ECONOMY.md`](DOC/ECONOMY.md#making-the-stock))
