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

1. **LMASTER full in game** (sections 7 and 8). Every part of
   `--mod harder-economy` is tested in PCSX2, and so are `transfer-fees`,
   `merch-costs` and the separate career saves; the other `--mod balance`
   switches and `pr-cycle` are built but not yet seen in game. A disc built with
   `--mod lmaster-full`, played through a season, shows whether the
   economy is harder in a way players notice and whether the balance
   switches work ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)).
2. **A new Virtua Pro Football edit player** (section 2, "Saves"): how
   VPF numbers a new edit player, so `pmplayer.py` can fill an empty
   slot. The answer is in VPF's own code, which waits on the sister
   project [VPF-Reverse](https://github.com/NexxusDrakoMultimedia/VPF-Reverse)
   (not yet fully reversed).
3. **The `GAME/` tactics AI files** (section 2, "The match"): what
   reads the play books' point codes, `Combi2`/`Combi3`'s area types,
   and `GAMEDATA.BIN`'s records. `snr2.py classes` and `callers` name
   the match AI's `fb::` classes and which class makes each call.

## What a mod can change, and what is left

The four kinds of change [`GOALS.md`](GOALS.md#what-a-mod-should-be-able-to-change)
aims at:

| Goal | Where it stands | Left (section) |
|---|---|---|
| The starting season | leagues, squads, clubs, the new club, free agents, schedules and division sizes, regulations and results have writers and editor tabs, tested in PCSX2; the national-team calendar has a writer and tab | room for bigger second divisions (2), a smaller first division and the national calendar tested (7) |
| Data | players, staff, clubs, kits, facilities, training, camps, tours, the tactics presets and the PR events have writers and tabs | the remaining player and staff fields (2), the stadium and emblem tables (3) |
| Parameters | every `PARAM/` table's layout is known; `tbb.py replace` swaps any table | the open fields (2) |
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
- [ ] Later (the project serves the English release first): Japanese
      release, the differences still open in
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
      the `make_list` sources, what `CLUB_RANK_SYSTEM`'s nation groups
      and tallies feed ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#still-unknown),
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

- [ ] The tactics AI files: the area types `Combi2` and `Combi3` make;
      in the play books what reads the point codes, what a path kind's
      value and flag do, and what the corner and free-kick id groups
      stand for
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] `GAMEDATA.BIN`: the rest of a ball-contact record, what sets a
      player's record (`+0x520`), and whether
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

- [ ] The `STADIUM/` tables and `EMBLEM/` edit tables, once their fields
      are understood

## 4. Rebuild: edits back on a bootable disc

**Goal:** any edit the writers make boots on a rebuilt disc, on either
release. **Done when** the items below work; see
[`REBUILD.md`](DOC/REBUILD.md#still-to-do).

- [ ] `TACTICSPITCH.PAC` is loaded through `CLoader`, not as a
      registering resource: whether its entries stand in for their
      originals ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#still-unknown))
- [ ] Later: a Japanese disc built with `--mod lmaster-full`, and a Japanese
      save edited with `save.py --iso ISO_JP`, still to be run in the
      game ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-japanese-release))
- [ ] Optional: dual-layer images, for a disc that grows past a
      single-layer DVD

## 5. Edit: the GUI

**Goal:** a mod can be made without knowing the file formats: one tab
per kind of data, each editing through its writer and taking the allowed
values from it, tested through the widgets off-screen. **Done when**
every writer has a tab.

- [ ] Later: the editor and save editor on the Japanese release

## 6. Distribute: sharing a mod

**Goal:** a player applies a mod with tools they already have, to the
disc they already own. **Done when** the image formats players keep are
covered. See [`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod).

- [ ] Optional: faster CHD decoding (Huffman and FLAC hunks decode in
      Python at about 1.3 and 3.7 ms each; a whole disc takes about ten
      minutes) and CHDs with several CD tracks
      ([`REBUILD.md`](DOC/REBUILD.md#compressed-images))

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
- [ ] `--mod mobile-site` (in LMASTER lite): on `LMAST-test-mobile.iso`
      (the switch, `--skip-tutorial`, and event 37 offered from the start:
      `37:month_rule=0 37:first_season=0 37:popularity=0 37:priority=101`),
      Renew Mobile Site is in the PR activities list from September,
      can be booked, and its month-end mail reports it
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] The National calendar tab: a disc with the World Cup squads called
      up a turn earlier (`3:88:callup=0 3:87:callup=1 3:87:finals=1`,
      on a season starting in 2009), where your club's internationals
      leave on turn 87 (the last weekend of May) instead of 88; and the
      same edit built with `--mod national-cups`
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#schedule_listtbb-the-national-team-calendar))
- [ ] The PR events tab: a disc with an event's cost and its ticket
      bonus changed (for example Ticket Campaign, `38:cost=200
      38:ticket=50`): the scheduling screen shows the new cost, and a
      successful campaign on a match day draws the bigger crowd
      ([`CLUBEVENT_FORMAT.md`](DOC/CLUBEVENT_FORMAT.md))
- [ ] The Club ranking tab: a disc with one edit to table 3 (for
      example `rank:7:31=3`, the top three of a slot-1 first division of
      20 at rank 31), played to the end of the first season; `save.py
      clubs` on the next save shows the new ranks
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables))
- [ ] A resized league in the club ranking: a disc with England's first
      division at 22 from the Season tab (which adds six ranking rows),
      played to the end of the first season; `save.py clubs` shows the
      English first division's ranks changed by the new rows, and the
      grown `CLUB_RANK_SYSTEM.TBB` loads
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables))
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
- [ ] Clubs 442–459 as full clubs (`--mod tier-clubs`):
      `LMAST-test-tierclubs.iso` (with the tutorial skip) starts a new
      career, plays through a transfer window and saves and loads;
      `LMAST-test-tierclubs-tutorial.iso` plays the tutorial's playoff
      against them ([`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md#--mod-tier-clubs-phase-2a))
- [ ] The launcher entries not yet tried: YAMAZAKI TEST, Talk and BG
      LIGHT TEST
- [ ] By ear: the commentary (`BC_ENG`), the tannoy (`JYONAI_A`) and
      `MAP01`
- [ ] The rest of the `--mod balance` switches, on a `--mod lmaster-full`
      disc (`transfer-fees` and `merch-costs` are tested;
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)): an injured
      player's condition line reading "two months" or "nine months"
      (English, and one other language); more long injuries over a
      season; an overseas base's set-up cost twice the retail one; a
      transfer fee above £120M, and a lesser player's fee about four
      times the retail one (`fee-tiers`); club status rising about half
      as fast after wins (`slow-reputation`, `save.py show`); merchandise income, crowds and TV offers
      against the retail game's for the same save; a PR event, a camp and
      a tour costing 2×, 2× and 3× the retail price; PR events succeeding
      about half the time in an average economy (`pr-cycle`)
- [ ] `pmplayer.py check` on a career saved after importing the edited
      V. Drake with `--mod vpf-styles` (`LMAST-vpftest.ps2`; the import
      is tested): no differences, and the fixed import's styles
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#the-record))

## 8. LMASTER Mod and other patches

**Goal:** restore content the release cut or broke, and offer a few
improvements, each as a named `patch_disc.py` switch tested in PCSX2
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)).

- [ ] Candidates: the short `EDIT_EMBLEM` tables 93/101/105
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Candidate: let the unused combination records load, the 15 extra
      records in each attack pattern's block (code: a random variant in
      `GAMEPRG.REL 0x14c3f0`) and the 25 basic records in no table
      (data: the three 12-entry tables, or bigger ones moved), and fix
      the pattern repeat check. Decide first whether the extra records
      play sensibly ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] The harder economy (`--mod harder-economy`: `facility-tiers`,
      `wider-tickets`, `dearer-ads`, `sponsor-fees`, `tv-fees`,
      `season-demand`): all six are tested in PCSX2; a season played
      through on the set is left
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [ ] The third tier (in progress, design agreed; LMASTER full, breaks
      save compatibility): phase 1 the save (block 2 and 5 grow), 2 clubs
      442–459 as full clubs, 3 the schedules, 4 the season test; phase 1
      is tested in PCSX2
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements));
      `one-season-end` is built ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
