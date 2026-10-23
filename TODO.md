<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# TODO

The open work, ordered by the stages in [`GOALS.md`](GOALS.md#the-path-there):
read every file, understand its fields, write it, rebuild a disc, edit
it in the GUI, and share the result. Sections 7 and 8 collect the
in-game tests and the LMASTER Mod, which cut across the stages.

Each item is a task. The research questions behind it live in the
"Still unknown" section of the doc it links, so they are kept in one
place; when one is answered, it comes off that list. A finished item
moves to the end of the same section in [`DONE.md`](DONE.md) as a line
or two.

## Next up

What to work on next, most valuable first.

1. **The harder economy over a season** (section 8). Every part of
   `--mod harder-economy` is built and tested in PCSX2; what is left is a
   season played through on it, to see that the economy is harder in a
   way players notice ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)).
2. **A new Virtua Pro Football edit player** (section 2, "Saves"): how
   VPF numbers a new edit player, so `pmplayer.py` can fill an empty
   slot. The answer is in VPF's own code, which waits on the sister
   project [VPF-Reverse](https://github.com/NexxusDrakoMultimedia/VPF-Reverse)
   (not yet fully reversed).
3. **The `GAME/` tactics AI files** (section 2, "The match"): what
   writes each team's 11 combination record numbers, the `.CBB` fields
   still unread (A's values, B, C's words), the combination commands'
   area types, and `GAMEDATA.BIN`'s records. `snr2.py classes` and
   `callers` name the match AI's `fb::` classes and which class makes
   each call.

## What a mod can change, and what is left

The four kinds of change [`GOALS.md`](GOALS.md#what-a-mod-should-be-able-to-change)
aims at:

| Goal | Where it stands | Left (section) |
|---|---|---|
| The starting season | leagues, squads, clubs, the new club, free agents, schedules and division sizes, regulations and results have writers and editor tabs, tested in PCSX2 | room for bigger second divisions (2), writers for the national-team calendar and the club ranking (3), a smaller first division tested (7) |
| Data | players, staff, clubs, kits, facilities, training and camps have writers and tabs | the remaining player and staff fields (2), the stadium and emblem tables (3), tabs for the tactics presets and tours (5) |
| Parameters | every `PARAM/` table's layout is known; `tbb.py replace` swaps any table | the open fields (2), field-level writers for the resource packs (3), tabs for them (5) |
| Text | every message in every language, with a writer and the Text tab | the screen-set variables and a few message categories (2) |

## 1. Read: every file parsed and checked

**Goal:** no file left as "unknown binary" (the
[coverage table](GOALS.md#coverage-of-datacvm)). **Done when** every file
type has a doc and a tool whose `info` passes over all of `DAT/`.

- [ ] `GAME/` leftovers ([`GAME_DIR.md`](DOC/GAME_DIR.md#still-unknown)):
      the `SHADOWCOLLI.PAC` and `WALLCOLLI.PAC` entries, decoded together
      with `TEST3D/SHADOWCOLLI.LBI`
      ([`TEST3D_DIR.md`](DOC/TEST3D_DIR.md#shadowcollilbi)); the `RBD0`
      trailer of `ROUTEBOX_*.BCR` (`tbb.py`'s writer copies it as-is);
      `TEAM.TMB` (`TMB1`), parsed and confirmed unread; the cut-in pack's
      `CIB0` and `BMT1` blocks; the commentary's `BCR2`/`BCB3`/`BCV`
      records
- [ ] `ACROBATA/`: the `ABDT` scene layout and the `ABRS` header table
      ([`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md#still-unknown))
- [ ] `EMBLEM/`: the preset and crest records (`EDIT_EMBLEM` t4–t9), the
      layer records, `EDIT_FLAG`'s variants and all of `EDIT_PLAYER.TBB`
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#still-unknown))
- [ ] `SEQ/`: `INFORMATION.WPX` and the command sets of the two 2004
      scripts ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#still-unknown))
- [ ] Outside `DATA.CVM`: `OPMOVIE.SFD` (Sofdec), `info.bin` past the date,
      `dm.bin` and the VS data save
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] Japanese release: read a Japanese save (block 1 is 16 bytes
      smaller), and the other differences in
      [`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#still-unknown)

## 2. Understand: field meanings an edit needs

**Goal:** every field a mod would change has a name and a known range,
so the editor can offer it. **Done when** the fields below are named, or
shown to have no effect. Grouped by what a mod would change.

### The starting season and the tables

- [ ] Division sizes: room for bigger second divisions and a smaller
      English or Italian first division (start the season earlier, or
      use cup turns;
      [`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#game-days-for-a-league-of-another-size)),
      and how your club and the rival become ranks 25 and 26 of the
      second division's past record
- [ ] The remaining schedule and club-ranking fields: `PeriodName.tbb`,
      the `make_list` sources, `CLUB_RANK_SYSTEM` tables 0, 1 and 4's
      effects ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#still-unknown),
      [`PARAM_DIR.md`](DOC/PARAM_DIR.md#still-unknown))
- [ ] Training and camps: the scale of a practice's values, the names of
      the 87 camp types and 28 youth menus, which camp each sponsor frees
      ([`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md#still-unknown),
      [`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md#still-unknown))
- [ ] The rest of the parameter files' open fields:
      [`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#still-unknown),
      [`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md#still-unknown),
      [`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#still-unknown),
      [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#still-unknown),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#still-unknown),
      [`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md#still-unknown),
      [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md#still-unknown)

### Players and staff

- [ ] Player fields still open: `explodetype`, abilities 59–63 and which
      attack pattern letter is which, the tendencies' passer-or-receiver
      question and press values, the kit style's cap and outfield gloves
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown)). An
      edited tendency can be checked over PINE in the match's parameter
      copy (`GAMEPRG.REL 0x97b28`, object `+0x84`–`+0x8e`)
- [ ] Staff: the fields only the developers' field table names, the 25
      manager policies and ranges, what sets job 5 when a manager is
      hired, and how coaches and former players become managers
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] National teams: what `_getNationalTeamPoint` scores, team 465,
      the call-up's flag `0x300`, and which clubs teams 442–459 are
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#national-team-call-ups))

### The match

- [ ] The tactics AI files: what sets each team's combination record
      numbers, who reads `COMBINATION2.CBB`'s A values, block B and C's
      words, the area types the combination commands make; in the play
      books the path kinds, point codes, which play is which, the
      `+0x20` block and `GetFormationData`
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] `GAMEDATA.BIN`: the rest of a ball-contact record, which foot parts
      0 and 1 are, what sets a player's record (`+0x520`), and whether
      anything reads `AI_PARAM.BIN`
      ([`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md#still-unknown))
- [ ] Match parameters: where the kick-off, penalty and goal kick kinds
      (27–29, 31, 34, 35) are first set, what tells apart 3 and 4, the
      in-play pairs and the tackles, kind 5, flag bits `0x200`–`0x2000`,
      the 45 getter calls with no class, the sources of parameters 5, 16
      and 24, and whether any code reads leadership, pressure, the
      offside-line skill or the ball touch straight from the player
      object ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#who-reads-each-parameter))
- [ ] Injuries: how many game days an injury value lasts, the injury
      chance and what makes the match report a heavy injury
      ([`INJURIES.md`](DOC/INJURIES.md#still-unknown))
- [ ] Stadiums: which crowd figure group is which, and who sets request
      `+0x0e`–`+0x10` in a real match
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#still-unknown))

### Text, events and game flow

- [ ] Message text: the screen-set variables, the raw `0x0A`/`0x0D`
      bytes, the rival owner's name and the `1000xx` categories
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#still-unknown)), and the NEWS
      columns `+0x20`, `+0x60`, `+0x70`
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#still-unknown))
- [ ] Events and procedures: the request fields, loan availability, the
      instruction-age rows and the screens that start procedures 9,
      14/16/18, 22 and 28
      ([`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md#still-unknown))
- [ ] Rooms and people (`BG/`): the room table's fields, which palette
      a room uses, what `HUMANID.BIN`'s object kinds select and which
      role each id is ([`BG_DIR.md`](DOC/BG_DIR.md#still-unknown))
- [ ] Game flow: which `Sche.YearEnd` value is which ending, how
      PlayAcrobata maps its argument to a scene, the sequencer's
      remaining commands ([`GAME_FLOW.md`](DOC/GAME_FLOW.md#still-unknown),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#still-unknown)), and which
      players have a fixed detail-screen comment
- [ ] The overlay loader: where the overlay index comes from, and the
      SNR2 header fields `0x20`/`0x24`/`0x38`
      ([`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md#still-unknown))
- [ ] Sponsors: whether Japan limited the number of negotiations, and the
      acceptance tables ([`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md#still-unknown))

### Graphics and sound

- [ ] Which screens play which music id and `bgm` track, and whether
      anything plays `MAP06`, `map02`'s songs 3–5 or the four banks the
      code never names ([`SOUND_DIR.md`](DOC/SOUND_DIR.md#still-unknown),
      [`AUDIO_DIR.md`](DOC/AUDIO_DIR.md#still-unknown)); closer SPU2
      emulation (ADSR, Gaussian interpolation, the pan table, the reverb
      preset)
- [ ] Ninja models: material colours and layer flags, hair tint, skin
      words and submotion interpolation
      ([`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md#still-unknown))
- [ ] Kits and faces: the face block-4 header, the kit tables' open side
      fields and descriptor bytes 14–15
      ([`PLAYER_DIR.md`](DOC/PLAYER_DIR.md#still-unknown),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#still-unknown))
- [ ] Newspapers: which paper a page uses, the special editions, where
      the ads and cartoons go ([`NEWS_DIR.md`](DOC/NEWS_DIR.md#still-unknown))

### Saves

- [ ] The save fields still open: PlPinfo flags and dissatisfaction,
      statistics table 1, the candidate records, the other clubs' and
      staff's untraced bytes, and when the club ranking runs
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] The rest of Virtua Pro Football's save, from VPF's code in the
      sister project: how VPF numbers a new edit player (so `pmplayer.py`
      can fill an empty slot), the record bytes the import doesn't read,
      and `file.inf`'s check
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#still-unknown))

## 3. Write: a writer for every format a mod changes

**Goal:** every value a mod changes can be written by a tool that
round-trips every file on the disc. **Done when** each format below has
a field-level writer with a `roundtrip` check in `regress.py`.

- [ ] `CLUB_RANK_SYSTEM.TBB`: a field-level writer for the ranking's
      points (tables 1–3, [`PARAM_DIR.md`](DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables))
- [ ] The club events, which live in the executable (`SLES 0x52ff58`,
      `0x530688`), not in `CLUBEVENT.TBB`: decode the records field by
      field, then a writer
- [ ] `PLRESOURCESIM.PAC`: writers for the streams (affiliations 5,
      exclusives 11–12, combinations 13–14), the overseas branch costs
      (entry 1), and the nation and stadium tables `initteam.py` reads
      (`INITNATIDATA.TBB`, `STADIUM_DATA.TBB`)
- [ ] `SCHEDULE_LIST.TBB` (the national-team calendar): a field-level
      writer; only `patch_disc.py --mod national-cups` changes it now
- [ ] The `STADIUM/` tables and `EMBLEM/` edit tables, once their fields
      are understood

## 4. Rebuild: edits back on a bootable disc

**Goal:** any edit the writers make boots on a rebuilt disc, on either
release. **Done when** the items below work; see
[`REBUILD.md`](DOC/REBUILD.md#still-to-do).

- [ ] `TACTICSPITCH.PAC` is loaded through `CLoader`, not as a
      registering resource: whether its entries stand in for their
      originals ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#still-unknown))
- [ ] Tools still PAL-only: `patch_disc.py`'s switches (they refuse other
      discs) and `save.py`'s commands (they take no ISO folder)
- [ ] Optional: dual-layer images, for a disc that grows past a
      single-layer DVD

## 5. Edit: the GUI

**Goal:** a mod can be made without knowing the file formats: one tab
per kind of data, each editing through its writer and taking the allowed
values from it, tested through the widgets off-screen. **Done when**
every writer has a tab.

- [ ] Tabs for the club ranking and the resource packs, once they have
      writers (section 3)
- [ ] The editor and save editor on the Japanese release

## 6. Distribute: sharing a mod

**Goal:** a player applies a mod with tools they already have, to the
disc they already own. **Done when** the image formats players keep are
covered. See [`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod).

- [ ] Let `vcdiff.py`/`patch_disc.py` read CSO (and CHD) images, which
      many players keep instead of ISOs
- [ ] Decode a patch that xdelta3 itself made with `vcdiff.py apply`
      (only the other direction is tested)

## 7. Tests in PCSX2

Checks that only a person can make (see [`AGENTS.md`](AGENTS.md)). Each
names the disc or the edit to build; the result goes into the doc.

- [ ] A smaller first division (France at 18, from the Season tab) and
      two nations changed in one build; only England at 22 is tested
- [ ] A `CLUBRESULT.TBB` edit (a cup given a third-place match shows
      "3rd"/"4th" on the end of tournament screen)
- [ ] A save from the Regulations tab (the same edit from
      `regulation.py set` is tested)
- [ ] A main-position change with `pbdata.py --sles` on its own (rank
      edits are tested; position goes through the same table)
- [ ] Squad ages: start a career without the tutorial skip and look at
      Van der Sar (Manchester slot 0, age 16 in the mod): 16 means the
      skip adds the year ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md))
- [ ] The tutorial skip in a league other than England
- [ ] Licensed kits: an edit to only one descriptor copy, to tell which
      one a match reads
- [ ] `UNIFORM_GK`: whether screens outside a match show your club's
      stored keeper kit
- [ ] The crest editor: whether the three short `EDIT_EMBLEM` layer
      tables lose visible parts
- [ ] The editor's Tours, Tactics and Comments tabs: a disc built with
      one edit from each (a tour opponent, a preset's formation, a
      manager comment cell) shows it in game
- [ ] Save editor step 4: one save edited on each page (the Club page is
      tested), including the step 5 player fields (salary, contract
      years, age, injury value 0 on an injured player, captain and
      keyman experience) and the Edit player page on a career with one
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md))
- [ ] The manager's Special Mention texts for dissatisfaction kinds 0–3,
      a save edit per kind
- [ ] A `--mod-saves` disc writes its VS data to `BESLES-54151-D000`
- [ ] The launcher entries not yet tried: YAMAZAKI TEST, Talk and BG
      LIGHT TEST
- [ ] By ear: the commentary (`BC_ENG`), the tannoy (`JYONAI_A`) and
      `MAP01`
- [ ] `pmplayer.py check` on a career saved after importing the edited
      V. Drake with `--mod vpf-styles` (`LMAST-vpftest.ps2`; the import
      is tested): no differences, and the fixed import's styles
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#the-record))

## 8. LMASTER Mod and other patches

**Goal:** restore content the release cut or broke, and offer a few
improvements, each as a named `patch_disc.py` switch tested in PCSX2
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)).

- [ ] Candidates: the short `EDIT_EMBLEM` tables 93/101/105
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status)). The "two
      months"/"nine months" injury lines need thresholds chosen first
- [ ] The harder economy (`--mod harder-economy`: `facility-tiers`,
      `wider-tickets`, `dearer-ads`, `sponsor-fees`, `tv-fees`,
      `season-demand`): all six are tested in PCSX2; a season played
      through on the set is left
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [ ] More improvement ideas: overseas bases, merchandise, reputation,
      player prices up to £250M, a third tier with a one-season game
      over ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
