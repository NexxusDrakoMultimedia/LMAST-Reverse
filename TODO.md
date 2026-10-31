<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# TODO

The work that's left, and what each piece is for. [`GOALS.md`](GOALS.md)
says what the project wants to make possible; this file turns that into
tasks.

How it's laid out:

- **[Next up](#next-up)** is what to pick up first.
- **[The goals](#the-goals-and-what-each-still-needs)** shows, for each
  kind of change a mod should be able to make, what works today and what
  still stands in the way, with the sections that hold the tasks.
- **Sections 1 to 6** follow the stages in
  [`GOALS.md`](GOALS.md#the-path-there): read every file, understand
  its fields, write it, rebuild a disc, edit it in the GUI, and share
  the result. Stage 0, decrypting `DATA.CVM`, is done. **Section 7** is
  the checks only a person can make in the game, and **section 8** the
  LMASTER Mod.

Each task links the doc that holds its details: the facts, the evidence
and the "Still unknown" list it comes from. When a question is
answered it comes off the doc's list, and a finished task moves to the
end of the same section in [`DONE.md`](DONE.md) as a line or two.

## Next up

What to work on next, most valuable first.

1. **The player fields still open** (section 2, "Data"): `explodetype`
   and the attack pattern letters, and the match values that pick the
   carry thresholds and the press row
   ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown)). The carry
   helper and the press floats are traced.
2. **LMASTER max in the game** (sections 7 and 8). Tested so far: every
   part of `--mod harder-economy`, `transfer-fees`, `fee-tiers` at the
   low end, `pr-costs`, `merch-costs`, `slow-reputation` after a match,
   and the separate career saves. Through a German season Nexxus found
   the game much harder economically, with the fanbase growing much more
   slowly and merchandise income much lower (2026-10-27). Left: the
   other `--mod balance` switches and `pr-cycle`, the lower cups' seeded
   brackets, and the `-V` VS folder (the third tier's transfer windows,
   season's end, saving and loading are tested). The test disc is
   `LMAST-test-season4.iso`, built 2026-10-31, with its test sheet
   `names/test-sheet-season.md`
   ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)).

## The goals, and what each still needs

The kinds of change [`GOALS.md`](GOALS.md#what-a-mod-should-be-able-to-change)
aims at, and the two things every mod also needs: a way to play it, and
the graphics that come after the data.

| Goal | What works today | Still in the way | Sections |
|---|---|---|---|
| **The starting season** | leagues, squads, clubs, the new club, free agents, schedules and division sizes, regulations and results: writers and editor tabs, tested in PCSX2. The national-team calendar and the club ranking have writers and tabs | room for bigger second divisions and a smaller English or Italian first division; a smaller first division, the national calendar and the club ranking tested in the game | 2, 7 |
| **Data** | players, staff, clubs, kits, crests and flags, facilities, training, camps, tours, the tactics presets, the PR events, the player links, and the stadiums' looks and boards: writers and tabs | the remaining player and staff fields; the other stadium tables and `EDIT_PLAYER.TBB` | 2, 3 |
| **Parameters** | every `PARAM/` table's layout is known and `tbb.py replace` swaps any table; the economy's constants in the executable are traced and changed by named switches | the open fields of the parameter files, the match AI's files and the match parameters | 2 |
| **Text** | every message in every language, with a writer and the Text tab; real names for every league, club and nation | the screen-set variables and a few message categories | 2 |
| **Playing a mod** | xdelta patches against the Redump image, CSO, ZSO and CHD inputs, separate saves for a modded disc, the players' guide | faster CHD decoding; the Japanese release | 4, 6 |
| **Graphics and sound** (after the data) | textures to PNG, models to OBJ and glTF, sound to WAV and MIDI; kits, crests and stadium looks edited as data | a texture writer, which LMAST Realism on the disc needs | 3, 8 |

## 1. Read: every file parsed and checked

**Goal:** no file left as "unknown binary" (the
[coverage table](GOALS.md#coverage-of-datacvm)). **Done when** every
file type has a doc and a tool whose `info` passes over all of `DAT/`.

- [ ] `GAME/` leftovers: the `SHADOWCOLLI.PAC` and `WALLCOLLI.PAC`
      entries (with `TEST3D/SHADOWCOLLI.LBI`), the `RBD0` trailer,
      `TEAM.TMB`, the cut-in pack's `CIB0`/`BMT1` blocks, the
      commentary's `BCR2`/`BCB3`/`BCV` records
      ([`GAME_DIR.md`](DOC/GAME_DIR.md#still-unknown))
- [ ] `ACROBATA/`: the `ABDT` scene layout and the `ABRS` header table
      ([`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md#still-unknown))
- [ ] `EMBLEM/`: which player-editor choices pick the rows of
      `EDIT_PLAYER.TBB` tables 19–21, 25 and 26, and tables 29–31
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#edit_playertbb))
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
shown to have no effect. Grouped by the goal each one serves.

### The starting season

- [ ] Division sizes: room for bigger second divisions and a smaller
      English or Italian first division (start the season earlier, or
      use cup turns)
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#game-days-for-a-league-of-another-size))
- [ ] The remaining schedule and club-ranking fields: `PeriodName.tbb`,
      the `make_list` sources, what `CLUB_RANK_SYSTEM`'s nation groups
      and tallies feed
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#still-unknown),
      [`PARAM_DIR.md`](DOC/PARAM_DIR.md#still-unknown))

### Data: players, staff and clubs

- [ ] Player fields still open: `explodetype`, which attack pattern
      letter is which (no reader picks one out), and the match values
      that pick the carry thresholds and the press row
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] Staff: the fields only the developers' field table names, and the
      model pattern ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] National teams: what `_getNationalTeamPoint` scores, and why team
      465 and the call-up's flag `0x300` matter
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#national-team-call-ups))
- [ ] Stadiums: byte `+0x0c` of your stadium record and the names of its
      6 advert slots
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#still-unknown))

### Parameters: the club game

- [ ] Training and camps: the scale of a practice's values, the names of
      the camp types and youth menus, which camp each sponsor frees
      ([`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md#still-unknown),
      [`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md#still-unknown))
- [ ] Injuries: how many game days an injury value lasts, the injury
      chance, and what makes the match report a heavy injury
      ([`INJURIES.md`](DOC/INJURIES.md#still-unknown))
- [ ] Sponsors: whether Japan limited the number of negotiations, and
      the acceptance tables
      ([`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md#still-unknown))
- [ ] The rest of the parameter files' open fields:
      [`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#still-unknown),
      [`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md#still-unknown),
      [`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#still-unknown),
      [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#still-unknown),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#still-unknown),
      [`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md#still-unknown),
      [`ECONOMY.md`](DOC/ECONOMY.md#still-unknown),
      [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md#still-unknown)

### Parameters: the match

- [ ] The tactics AI files: which gait each move order kind is (its
      animations have no names), the kicker roles' yes/no and the three
      receiver handlers, and `Combi3`'s presets 22–34
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] `GAMEDATA.BIN`: the rest of a ball-contact record, what sets a
      player's record, and whether anything reads `AI_PARAM.BIN`
      ([`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md#still-unknown))
- [ ] Match parameters: the kick kinds that share a builder and where
      some are first set, the flag bits, the getter calls with no class,
      and the sources of parameters 5, 16 and 24
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#who-reads-each-parameter))

### Text, events and game flow

- [ ] Message text: the screen-set variables, the raw `0x0A`/`0x0D`
      bytes, the rival owner's name and the `1000xx` categories
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#still-unknown)); the NEWS
      columns `+0x20`, `+0x60` and `+0x70`
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#still-unknown))
- [ ] Events and procedures: the request fields, loan availability, the
      instruction-age rows, and the screens that start procedures 9,
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
      the ads and cartoons go
      ([`NEWS_DIR.md`](DOC/NEWS_DIR.md#still-unknown))

### Saves

- [ ] The save fields still open: PlPinfo flags and dissatisfaction,
      statistics table 1, the candidate records, the other clubs' and
      staff's untraced bytes, and when the club ranking runs
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] The rest of Virtua Pro Football's save, from VPF's code in the
      sister project: how VPF numbers a new edit player, the record
      bytes the import doesn't read, and `file.inf`'s check
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#still-unknown))

## 3. Write: a writer for every format a mod changes

**Goal:** every value a mod changes can be written by a tool that
round-trips every file on the disc. **Done when** each format below has
a field-level writer with a `roundtrip` check in `regress.py`.

- [ ] The `STADIUM/` tables besides `BUILD_STADIUM`'s looks and boards
      (`CONV_INFO_BUILD`, the crowd sets), if a mod needs them
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#editing)); `EDIT_PLAYER.TBB`,
      whose tables are now read (base abilities by position and nation,
      the personality ranges;
      [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#edit_playertbb))
- [ ] A texture writer for `svr.py`, which only reads, for LMAST Realism
      on the disc ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))

## 4. Rebuild: edits back on a bootable disc

**Goal:** any edit the writers make boots on a rebuilt disc, on either
release. **Done when** the items below work; see
[`REBUILD.md`](DOC/REBUILD.md#still-to-do).

- [ ] `TACTICSPITCH.PAC` is loaded through `CLoader`, not as a
      registering resource: whether its entries stand in for their
      originals ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#still-unknown))
- [ ] Later: `--mod third-tier` on the Japanese release, which it
      refuses now, and a Japanese disc built with the other switches and
      a Japanese save edited with `save.py --iso ISO_JP`, run in the game
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-japanese-release))
- [ ] Optional: dual-layer images, for a disc that grows past a
      single-layer DVD

## 5. Edit: the GUI

**Goal:** a mod can be made without knowing the file formats: one tab
per kind of data, each editing through its writer and taking the allowed
values from it, tested through the widgets off-screen. **Done when**
every writer has a tab.

- [ ] A tab for each writer section 3 adds
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

### The starting season and data

- [ ] A smaller first division (France at 18, from the Season tab) and
      two nations changed in one build; only England at 22 is tested
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [ ] Squad ages: a career started without the tutorial skip, with Van
      der Sar (Manchester slot 0) at 16 in the mod: 16 means the skip
      adds the year
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#oteammembertbb))
- [ ] A main-position change with `pbdata.py --sles` on its own (rank
      edits are tested) ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [ ] Kits: an edit to only one licensed-kit descriptor copy, to tell
      which one a match reads; whether screens outside a match show
      your club's stored keeper kit
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#still-unknown),
      [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#editing))
- [ ] Kit style: outfield gloves on a player with `gloves` 1–4 in a
      career match between November and March (not in VS), and the cap
      on an edit player made with the GK Style page's Hat, in the
      editor's preview and in a match
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#kit-style))
- [ ] The match policy: give a computer club's manager selection policy
      0 and then 7 (match policy unchanged), play a match against it
      while behind or ahead late, and see whether its tactics and
      substitutions change; that tells whether the match reads the
      selection byte by mistake
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-developers-staff-editors))
- [ ] `pmplayer.py check` on a career saved after importing the edited
      V. Drake with `--mod vpf-styles` (`LMAST-vpftest.ps2`)
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#tested))

### The editor's tabs

- [ ] A `CLUBRESULT.TBB` edit: a cup given a third-place match shows
      "3rd"/"4th" on the end of tournament screen
      ([`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md#editing))
- [ ] A save from the Regulations tab (the same edit from
      `regulation.py set` is tested)
      ([`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#editing))
- [ ] The crest editor: whether the three short `EDIT_EMBLEM` layer
      tables lose visible parts
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#the-layer-tables-12143))
- [ ] The National calendar tab: the World Cup squads called up a turn
      earlier (`3:88:callup=0 3:87:callup=1 3:87:finals=1`, a season
      starting in 2009), alone and with `--mod national-cups`
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#schedule_listtbb-the-national-team-calendar))
- [ ] The Club ranking tab (for example `rank:7:31=3`), and a resized
      league's added ranking rows (England at 22), each played to the
      end of the first season and read with `save.py clubs`
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables))
- [ ] The Nations & stadiums and Player links tabs: one edit from each
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#stadium_datatbb-stadiums),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#writing-the-streams))
- [ ] The Tours, Tactics and Comments tabs: one edit from each (a tour
      opponent, a preset's formation, a manager comment cell)
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-detail-screen-comments))
- [ ] The Stadiums tab: one stadium built like another (for example a
      small club's ground built like 99, the `ho04a` bowl) and one of
      its boards changed, on a test disc built from the editor (File >
      Build disc); play a match there, with and without LMASTER full
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#editing))
- [ ] Save editor step 4: one save edited on each page (the Club page is
      tested), the step 5 player fields and the Edit player page
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md#steps))
- [ ] The manager's Special Mention texts for dissatisfaction kinds 0–3,
      a save edit per kind
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))

### The LMASTER Mod

- [ ] The rest of the `--mod balance` switches, `injury-lines` and
      `pr-cycle`, on a `--mod lmaster-max` disc: each row marked "not
      checked in the game" in
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements) (the injury
      lines and odds, overseas bases, a fee above £120M, `fanbase`'s
      crowds, TV offers and big-fanbase merchandise, the camp and tour
      costs; `fee-tiers`' low end, `pr-costs`, lower merchandise income
      and `slow-reputation` after a win are seen)
- [ ] The third tier's lower cups on `LMAST-test-max-germany.iso` (its
      transfer windows, season's end, saving and loading are tested,
      [`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md#--mod-third-tier-the-lists-phase-2b)):
      the German Club Cup's seeded bracket (one first-round tie on Dec
      w1 midweek, the other 7 clubs from the second round) played to
      its final, another nation's lower cup the same way, and the round
      names on the end of tournament screen
      ([`UID_LIMITS.md`](DOC/UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3))
- [ ] The third tier's text in a language other than English (the
      English is tested): the advisor's intro, the Game Over help, the
      2nd German League's rules screen and its season-start news
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-text))
- [ ] A `--mod-saves` disc writes its VS data to `BESLES-54151-V000`,
      and an LMASTER full disc its careers to `-F000`
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [ ] The Special stadium late in a career: a 100,000 ground (`--mod
      special-stadium`) that fills when sold out
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#stadiums))
- [ ] `--mod press-tendency` by eye: a club of high-press players closes
      down harder than without it (the patch is checked in memory)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))

### Testing aids and sound

- [ ] The tutorial skip in France, Italy, Spain or the Netherlands
      (`--skip-nation`; England and Germany are played)
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs))
- [ ] The launcher entries not yet tried: YAMAZAKI TEST, Talk and BG
      LIGHT TEST ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-developer-launcher))
- [ ] By ear: the commentary (`BC_ENG`), the tannoy (`JYONAI_A`) and
      `MAP01` ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md#still-unknown))

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
- [ ] Candidates from the manager's fields: the match reading the
      selection policy instead of the match policy (after the section 7
      test), the strength ratio above 1.19 getting column 0, and the
      training plan's rows out of step with the policy names
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Candidate: the salesman's items. Flag 336 (the attack-pattern
      boost) is paired with no event, probably meant for the special
      training coach (event 190), and the headphones' and spikes'
      boosts don't match their text
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#the-salesmans-items))
- [ ] LMAST Realism on the disc: the texture hash map, a texture writer
      (section 3) and the palettes
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))
