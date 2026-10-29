<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# TODO

The open work, ordered by the stages in [`GOALS.md`](GOALS.md#the-path-there):
read every file (1), understand its fields (2), write it (3), rebuild a
disc (4), edit it in the GUI (5), and share the result (6). Sections 7
and 8 collect the in-game tests and the LMASTER Mod, which cut across
the stages. Stage 0, decrypting `DATA.CVM`, is done.

Each item is a task, with a link to the doc that holds its details:
the facts, the evidence and the "Still unknown" list it comes from.
When a question is answered it comes off the doc's list, and a
finished item moves to the end of the same section in
[`DONE.md`](DONE.md) as a line or two.

## Next up

What to work on next, most valuable first.

1. **The player and staff fields** (section 2, "Players and staff"):
   the player fields still open (`explodetype`, abilities 59–63 and the
   attack pattern letters, the carry and press tendencies; an edited
   tendency can be checked over PINE), then the staff
   fields still open: the selection, match, training and rest
   policies, the 1–5 tactical values and the staff abilities no bar
   shows ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown)).
2. **LMASTER max in game** (sections 7 and 8): every part of
   `--mod harder-economy` is tested in PCSX2, and so are
   `transfer-fees`, `fee-tiers` at the low end, `pr-costs`,
   `merch-costs`, `slow-reputation` after a match and the separate
   career saves. Through a German
   season the user found the game much harder economically, the
   fanbase growing much more slowly and merchandise income much lower
   (2026-10-27). Left: the other `--mod balance` switches and `pr-cycle`, and the lower cups' seeded
   brackets and the `-V` VS folder (the third tier's transfer windows,
   season's end, saving and loading are tested). The disc
   is `LMAST-test-max-germany.iso`, built 2026-10-27
   ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)).
3. **The stadium tables and `EDIT_PLAYER.TBB`** (sections 2 and 3):
   the crowd figure groups (they need a look at the models) and request
   `+0x0e`–`+0x10`, then a stadium writer and tab; `EDIT_PLAYER.TBB`'s
   32 tables from their accessors' callers
   ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#still-unknown),
   [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#still-unknown)).

## What a mod can change, and what is left

The four kinds of change [`GOALS.md`](GOALS.md#what-a-mod-should-be-able-to-change)
aims at:

| Goal | Where it stands | Left (section) |
|---|---|---|
| The starting season | leagues, squads, clubs, the new club, free agents, schedules and division sizes, regulations and results have writers and editor tabs, tested in PCSX2; the national-team calendar has a writer and tab | room for bigger second divisions (2), a smaller first division and the national calendar tested (7) |
| Data | players, staff, clubs, kits, crests and flags, facilities, training, camps, tours, the tactics presets, the PR events and the player links have writers and tabs | the remaining player and staff fields (2), the stadium tables (3) |
| Parameters | every `PARAM/` table's layout is known; `tbb.py replace` swaps any table | the open fields (2) |
| Text | every message in every language, with a writer and the Text tab | the screen-set variables and a few message categories (2) |

## 1. Read: every file parsed and checked

**Goal:** no file left as "unknown binary" (the
[coverage table](GOALS.md#coverage-of-datacvm)). **Done when** every file
type has a doc and a tool whose `info` passes over all of `DAT/`.

- [ ] `GAME/` leftovers: the `SHADOWCOLLI.PAC` and `WALLCOLLI.PAC`
      entries (with `TEST3D/SHADOWCOLLI.LBI`), the `RBD0` trailer,
      `TEAM.TMB`, the cut-in pack's `CIB0`/`BMT1` blocks, the
      commentary's `BCR2`/`BCB3`/`BCV` records
      ([`GAME_DIR.md`](DOC/GAME_DIR.md#still-unknown))
- [ ] `ACROBATA/`: the `ABDT` scene layout and the `ABRS` header table
      ([`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md#still-unknown))
- [ ] `EMBLEM/`: `EDIT_PLAYER.TBB`'s 32 tables (each has an accessor in
      `YRSTPRG.REL`; their callers aren't traced)
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#still-unknown))
- [ ] `SEQ/`: `INFORMATION.WPX` and the command sets of the two 2004
      scripts ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#still-unknown))
- [ ] Outside `DATA.CVM`: `OPMOVIE.SFD` (Sofdec;
      [`AUDIO_DIR.md`](DOC/AUDIO_DIR.md#still-unknown)), `info.bin` past
      the date, `dm.bin` and the VS data save
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] Later (the project serves the English release first): the
      Japanese release's differences still open
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#still-unknown))

## 2. Understand: field meanings an edit needs

**Goal:** every field a mod would change has a name and a known range,
so the editor can offer it. **Done when** the fields below are named, or
shown to have no effect. Grouped by what a mod would change.

### The starting season and the tables

- [ ] Division sizes: room for bigger second divisions and a smaller
      English or Italian first division (start the season earlier, or
      use cup turns)
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#game-days-for-a-league-of-another-size))
- [ ] The remaining schedule and club-ranking fields: `PeriodName.tbb`,
      the `make_list` sources, what `CLUB_RANK_SYSTEM`'s nation groups
      and tallies feed ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#still-unknown),
      [`PARAM_DIR.md`](DOC/PARAM_DIR.md#still-unknown))
- [ ] Training and camps: the scale of a practice's values, the names of
      the camp types and youth menus, which camp each sponsor frees
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

- [ ] Player fields still open: `explodetype`, abilities 59–63 and the
      attack pattern letters (no reader picks one out), the carry and
      press tendencies ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] Staff: the fields only the developers' field table names, the
      selection, match, training and rest policies, the 1–5 tactical
      values and the staff abilities no bar shows
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] National teams: what `_getNationalTeamPoint` scores, why team 465
      and the call-up's flag `0x300` matter
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#national-team-call-ups))

### The match

- [ ] The tactics AI files: the combination commands' areas, what reads
      the play books' point codes and path kinds, the corner and
      free-kick id groups ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] `GAMEDATA.BIN`: the rest of a ball-contact record, what sets a
      player's record, and whether anything reads `AI_PARAM.BIN`
      ([`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md#still-unknown))
- [ ] Match parameters: the kick kinds that share a builder and where
      some are first set, the flag bits, the getter calls with no class,
      and the sources of parameters 5, 16 and 24
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#who-reads-each-parameter))
- [ ] Injuries: how many game days an injury value lasts, the injury
      chance and what makes the match report a heavy injury
      ([`INJURIES.md`](DOC/INJURIES.md#still-unknown))
- [ ] Stadiums: which crowd figure group is which, and who sets request
      `+0x0e`–`+0x10` in a real match
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#still-unknown))

### Text, events and game flow

- [ ] Message text: the screen-set variables, the raw `0x0A`/`0x0D`
      bytes, the rival owner's name and the `1000xx` categories
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#still-unknown)); the NEWS
      columns `+0x20`, `+0x60`, `+0x70`
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#still-unknown))
- [ ] Events and procedures: the request fields, loan availability, the
      instruction-age rows and the screens that start procedures 9,
      14/16/18, 22 and 28
      ([`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md#still-unknown))
- [ ] Rooms and people (`BG/`): the room table's fields, a room's
      palette, `HUMANID.BIN`'s object kinds and roles
      ([`BG_DIR.md`](DOC/BG_DIR.md#still-unknown))
- [ ] Game flow: which `Sche.YearEnd` value is which ending, how
      PlayAcrobata maps its argument to a scene, the sequencer's
      remaining commands, and which players have a fixed detail-screen
      comment ([`GAME_FLOW.md`](DOC/GAME_FLOW.md#still-unknown),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#still-unknown))
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
      emulation ([`GAME_DIR.md`](DOC/GAME_DIR.md#still-unknown))
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
      sister project: how VPF numbers a new edit player, the record bytes
      the import doesn't read, and `file.inf`'s check
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#still-unknown))

## 3. Write: a writer for every format a mod changes

**Goal:** every value a mod changes can be written by a tool that
round-trips every file on the disc. **Done when** each format below has
a field-level writer with a `roundtrip` check in `regress.py`.

- [ ] The `STADIUM/` tables, once their fields are understood
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md)); `EDIT_PLAYER.TBB` after
      its tables are decoded ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md))
- [ ] A texture writer for `svr.py`, which only reads, for LMAST Realism
      on the disc ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))

## 4. Rebuild: edits back on a bootable disc

**Goal:** any edit the writers make boots on a rebuilt disc, on either
release. **Done when** the items below work; see
[`REBUILD.md`](DOC/REBUILD.md#still-to-do).

- [ ] `TACTICSPITCH.PAC` is loaded through `CLoader`, not as a
      registering resource: whether its entries stand in for their
      originals ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#still-unknown))
- [ ] Later: `--mod third-tier` on the Japanese release, which it refuses
      now, and a Japanese disc built with the other switches and a
      Japanese save edited with `save.py --iso ISO_JP`, run in the game
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-japanese-release))
- [ ] Optional: dual-layer images, for a disc that grows past a
      single-layer DVD

## 5. Edit: the GUI

**Goal:** a mod can be made without knowing the file formats: one tab
per kind of data, each editing through its writer and taking the allowed
values from it, tested through the widgets off-screen. **Done when**
every writer has a tab.

- [ ] A stadium tab, once the stadium writer exists (section 3)
- [ ] Later: the editor and save editor on the Japanese release

## 6. Distribute: sharing a mod

**Goal:** a player applies a mod with tools they already have, to the
disc they already own. **Done when** the image formats players keep are
covered. See [`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod).

- [ ] Optional: faster CHD decoding (a whole disc takes about ten
      minutes in Python) and CHDs with several CD tracks
      ([`REBUILD.md`](DOC/REBUILD.md#compressed-images))

## 7. Tests in PCSX2

**Goal:** every edit and switch is seen working in the game. Only a
person can check these (see [`AGENTS.md`](AGENTS.md)). Each names the
disc or the edit to build; the result goes into the doc linked.

- [ ] A smaller first division (France at 18, from the Season tab) and
      two nations changed in one build; only England at 22 is tested
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [ ] A `CLUBRESULT.TBB` edit: a cup given a third-place match shows
      "3rd"/"4th" on the end of tournament screen
      ([`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md#editing))
- [ ] A save from the Regulations tab (the same edit from
      `regulation.py set` is tested)
      ([`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#editing))
- [ ] A main-position change with `pbdata.py --sles` on its own (rank
      edits are tested) ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [ ] Squad ages: a career started without the tutorial skip, with Van
      der Sar (Manchester slot 0) at 16 in the mod: 16 means the skip
      adds the year ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#oteammembertbb))
- [ ] The tutorial skip in France, Italy, Spain or the Netherlands
      (`--skip-nation`; England and Germany are played)
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs))
- [ ] Kits: an edit to only one licensed-kit descriptor copy, to tell
      which one a match reads; whether screens outside a match show
      your club's stored keeper kit
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#still-unknown))
- [ ] An edited starting crest (`emblem.py set`, for example
      `crest:8:0:base=15 crest:8:0:mask=1`) shows when a new club picks
      it, and a flag pattern's `rev` 1–3 in the flag editor
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#editing))
- [ ] Kit style: outfield gloves on a player with `gloves` 1–4 in a
      career match between November and March (not in VS), and the cap
      on an edit player made with the GK Style page's Hat, in the
      editor's preview and in a match
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#kit-style))
- [ ] The crest editor: whether the three short `EDIT_EMBLEM` layer
      tables lose visible parts
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#the-layer-tables-12143))
- [ ] `--mod mobile-site` on `LMAST-test-mobile.iso` (with
      `--skip-tutorial` and event 37 offered from the start:
      `37:month_rule=0 37:first_season=0 37:popularity=0
      37:priority=101`): Renew Mobile Site is in the PR activities list
      from September, can be booked, and its month-end mail reports it
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] The National calendar tab: the World Cup squads called up a turn
      earlier (`3:88:callup=0 3:87:callup=1 3:87:finals=1`, a season
      starting in 2009), alone and with `--mod national-cups`
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#schedule_listtbb-the-national-team-calendar))
- [ ] The PR events tab: an event's cost and ticket bonus changed (for
      example `38:cost=200 38:ticket=50`)
      ([`CLUBEVENT_FORMAT.md`](DOC/CLUBEVENT_FORMAT.md#editing))
- [ ] The Club ranking tab (for example `rank:7:31=3`), and a resized
      league's added ranking rows (England at 22), each played to the
      end of the first season and read with `save.py clubs`
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables))
- [ ] The Nations & stadiums and Player links tabs: one edit from each
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#stadium_datatbb-stadiums),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#writing-the-streams))
- [ ] The Tours, Tactics and Comments tabs: one edit from each (a tour
      opponent, a preset's formation, a manager comment cell)
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md), [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-detail-screen-comments))
- [ ] Save editor step 4: one save edited on each page (the Club page is
      tested), the step 5 player fields and the Edit player page
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md#steps))
- [ ] The manager's Special Mention texts for dissatisfaction kinds 0–3,
      a save edit per kind ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] The third tier's text on `LMAST-test-max-germany.iso` (German
      career): the advisor's intro at the start (18 clubs, 34 matches,
      game over at the bottom), Game Over conditions in the help (last
      place, 18th), the 2nd German League's rules screen (a Relegation
      section) and its season-start news (the bottom club goes down);
      one other language if possible
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-text))
- [ ] The third tier's lower cups on `LMAST-test-max-germany.iso` (its
      transfer windows, season's end, saving and loading are tested,
      [`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md#--mod-third-tier-the-lists-phase-2b)):
      the German Club Cup's seeded bracket (one first-round tie on Dec
      w1 midweek, the other 7 clubs from the second round) played to
      its final, another nation's lower cup the same way, and the round
      names on the end of tournament screen
      ([`UID_LIMITS.md`](DOC/UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3))
- [ ] A `--mod-saves` disc writes its VS data to `BESLES-54151-V000`,
      and an LMASTER full disc its careers to `-F000`
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [ ] The launcher entries not yet tried: YAMAZAKI TEST, Talk and BG
      LIGHT TEST ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-developer-launcher))
- [ ] By ear: the commentary (`BC_ENG`), the tannoy (`JYONAI_A`) and
      `MAP01` ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md#still-unknown))
- [ ] The rest of the `--mod balance` switches, `injury-lines` and
      `pr-cycle`, on a `--mod lmaster-max` disc: each row marked "not
      checked in the game" in [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements) (the
      injury lines and odds, overseas bases, a fee above £120M,
      `fanbase`'s crowds, TV
      offers and big-fanbase merchandise, the camp and tour costs;
      `fee-tiers`' low end, `pr-costs`, lower merchandise income and
      `slow-reputation` after a win are seen)
- [ ] `pmplayer.py check` on a career saved after importing the edited
      V. Drake with `--mod vpf-styles` (`LMAST-vpftest.ps2`)
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#tested))

## 8. LMASTER Mod and other patches

**Goal:** restore content the release cut or broke, and offer a few
improvements, each as a named `patch_disc.py` switch tested in PCSX2
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)). **Done when** every candidate
is built and tested, or set aside.

- [ ] Candidate: the short `EDIT_EMBLEM` tables 93/101/105
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Candidate: let the unused combination records load, and fix the
      pattern repeat check; decide first whether the extra records play
      sensibly ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Retail text fixes for LMASTER lite: messages wrong in the retail
      game itself, starting with Game Over conditions 1204 and 1205 (the
      third tier's text is done)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))
- [ ] Real names for LMASTER full and max: every league, competition,
      club and national team under its real name of the era (Highbury as
      Arsenal, European League as UEFA Champions League), matching LMAST
      Realism's club names, in all five languages, each at most 18
      characters like the player's own club name; first the list of
      names (from Realism, checked by the user)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))
- [ ] LMAST Realism on the disc: the texture hash map, a texture writer
      (section 3) and the palettes
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))
