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
  the result. Stage 0, decrypting `DATA.CVM`, is done. **Section 7**
  points to [`TESTING.md`](TESTING.md), the checks only a person can
  make in the game, and **section 8** is the LMASTER Mod.

Each task links the doc that holds its details: the facts, the evidence
and the "Still unknown" list it comes from. When a question is
answered it comes off the doc's list, and a finished task moves to the
end of the same section in [`DONE.md`](DONE.md) as a line or two.

## Next up

What to work on next, most valuable first.

1. **LMASTER max in the game** ([`TESTING.md`](TESTING.md), section
   8). Tested so far: every part of `--mod harder-economy`, `transfer-fees`, `fee-tiers` at the
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
2. **LMAST Realism on the disc** (sections 3 and 8). `svr.py` writes
   textures and `texmap.py` maps the pack onto the disc: 1,613 of its
   1,614 PNGs have a disc texture, 1,601 of them in plain `.PAC` packs
   that `pac.py replace` can write. `texmap.py apply` writes the crests
   and match pictures into copies of their packs, and `--mod realism`
   (LMASTER full and max) builds them into a disc, which works in PCSX2.
   Left: writers for the CSP and ACROBATA packs (58 pictures). The kits
   stay Realism-only (a PCSX2 texture pack)
   ([`TEXMAP.md`](DOC/TEXMAP.md), [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#lmast-realism-on-the-disc)).
3. **Every LMASTER switch on the Japanese release** (section 8), needed
   before LMASTER 1.0.0: every other switch plans there now; left are
   `third-tier` (a code port) and `real-names` (the names in Japanese)
   ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc)).
4. **League games on the national-team dates in the game**
   ([`TESTING.md`](TESTING.md)): England at 18 clubs, a short test that
   decides whether the new division sizes are safe to offer
   ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#game-days-for-a-league-of-another-size)).

## The goals, and what each still needs

The kinds of change [`GOALS.md`](GOALS.md#what-a-mod-should-be-able-to-change)
aims at, and the two things every mod also needs: a way to play it, and
the graphics that come after the data.

| Goal | What works today | Still in the way | Sections |
|---|---|---|---|
| **The starting season** | leagues, squads, clubs, the new club, free agents, schedules and division sizes, regulations and results: writers and editor tabs, tested in PCSX2. The national-team calendar and the club ranking have writers and tabs; leagues on the national-team dates allow every size from 18 English clubs up | a smaller first division, league games on the national-team dates, the national calendar and the club ranking tested in the game | 2, 7 |
| **Data** | players, staff, clubs, kits, crests and flags, facilities, training, camps, tours, the tactics presets, the PR events, the player links, and the stadiums' looks and boards: writers and tabs | the remaining player and staff fields; the other stadium tables | 2, 3 |
| **Parameters** | every `PARAM/` table's layout is known and `tbb.py replace` swaps any table; the economy's constants in the executable are traced and changed by named switches | the open fields of the parameter files, the match AI's files and the match parameters | 2 |
| **Text** | every message in every language, with a writer and the Text tab; real names for every league, club and nation | the screen-set variables and a few message categories | 2 |
| **Playing a mod** | xdelta patches against the Redump image, CSO, ZSO and CHD inputs, separate saves for a modded disc, the players' guide | faster CHD decoding; the Japanese release | 4, 6 |
| **Graphics and sound** (after the data) | textures to PNG, models to OBJ and glTF, sound to WAV and MIDI; kits, crests and stadium looks edited as data | writers for the CSP, ACROBATA and `PackData` packs, which its league logos and intro need (the kits stay Realism-only) | 3, 8 |

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
- [ ] Later (the project serves the English release first), but
      needed before the reverse engineering counts as complete: the
      Japanese release's differences still open
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#still-unknown))

## 2. Understand: field meanings an edit needs

**Goal:** every field a mod would change has a name and a known range,
so the editor can offer it. **Done when** the fields below are named, or
shown to have no effect. Grouped by the goal each one serves.

### The starting season

- [ ] The remaining schedule and club-ranking fields: `PeriodName.tbb`,
      the `make_list` sources, what `CLUB_RANK_SYSTEM`'s nation groups
      and tallies feed
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#still-unknown),
      [`PARAM_DIR.md`](DOC/PARAM_DIR.md#still-unknown))

### Data: players, staff and clubs

- [ ] The tendencies' last match details: the two checks that put a
      team in situation 3 or 4, and which tactics slider sets where
      situation 1 starts
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
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#editing))
- [ ] Writers for the packs that hold textures and have none: the CSP
      packs (780 textures, and 471 in the `PRELOAD` packs), the ACROBATA
      pack (2,137) and the KC@P `PackData` packs (kits, cut-ins, faces),
      for LMAST Realism on the disc
      ([`SVR_FORMAT.md`](DOC/SVR_FORMAT.md#writing))

## 4. Rebuild: edits back on a bootable disc

**Goal:** any edit the writers make boots on a rebuilt disc, on either
release. **Done when** the items below work; see
[`REBUILD.md`](DOC/REBUILD.md#still-to-do).

- [ ] Every LMASTER switch on the Japanese release, needed before
      LMASTER 1.0.0 (section 8)
- [ ] Later, but needed before the reverse engineering counts as
      complete (Nexxus's choice, 2026-11-01): a Japanese save edited
      with `save.py --iso ISO_JP`, run in the game
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-japanese-release))
- [ ] Optional: dual-layer images, for a disc that grows past a
      single-layer DVD

## 5. Edit: the GUI

**Goal:** a mod can be made without knowing the file formats: one tab
per kind of data, each editing through its writer and taking the allowed
values from it, tested through the widgets off-screen. **Done when**
every writer has a tab.

- [ ] A tab for each writer section 3 adds
- [ ] Later, but needed before the reverse engineering counts as
      complete (Nexxus's choice, 2026-11-01): the editor and save editor
      on the Japanese release

## 6. Distribute: sharing a mod

**Goal:** a player applies a mod with tools they already have, to the
disc they already own. **Done when** the image formats players keep are
covered. See [`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod).

- [ ] Optional: faster CHD decoding (a whole disc takes about ten
      minutes in Python) and CHDs with several CD tracks
      ([`REBUILD.md`](DOC/REBUILD.md#compressed-images))

## 7. Tests in PCSX2

The checks only a person can make in the game are in
[`TESTING.md`](TESTING.md), written for every contributor: what to
build, what to look for and how to report it.

## 8. LMASTER Mod and other patches

**Goal:** restore content the release cut or broke, and offer a few
improvements, each as a named `patch_disc.py` switch tested in PCSX2
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)). **Done when** every candidate
is built and tested, or set aside.

- [ ] **Needed before LMASTER 1.0.0** (Nexxus's choice, 2026-11-01):
      every switch works on the Japanese release (SLPM-66316). The
      release itself is Nexxus's call, when testing, features and
      reverse engineering feel complete; this is its one firm
      requirement. Every other switch plans on the Japanese disc
      (2026-11-01). Left: `third-tier` (its code, save, clubs, lists and
      seasons ported, and its text in Japanese) and `real-names` (the
      names in Japanese), so LMASTER full and max can't be built for it
      yet; and no Japanese disc built with the switches has been run in
      the game
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))

- [ ] Re-assess each switch's edition (Nexxus's request, 2026-11-01):
      some bug fixes may sit in full instead of lite. A first read:
      `salesman-items` (in `restorations`) bundles a plain fix, the
      spikes' and headphones' boosts swapped against their text, with
      the coach's unused flag, a restoration; `league-balance` (in
      `leagues`) fixes runs of up to 9 games at one venue but is called
      an improvement; and the other way, `national-cups` (in lite's
      `match-fixes`) moves the cups a turn to make their results
      viewable, closer to an improvement. The rule (Nexxus's,
      2026-11-01): a fix that can't break a retail career in progress
      goes in lite, one that may stays in full. Go through every switch:
      is it a fix, and could it break a retail save in progress (data
      the save holds, a schedule or club list it was made with); then
      propose moves for Nexxus to confirm
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels))
- [ ] Candidate: the short `EDIT_EMBLEM` tables 93/101/105
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Candidate: let the unused combination records load, and fix the
      pattern repeat check; decide first whether the extra records play
      sensibly ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Candidates from the manager's fields: the match reading the
      selection policy instead of the match policy (after its test in
      [`TESTING.md`](TESTING.md)), the strength ratio above 1.19 getting column 0, and the
      training plan's rows out of step with the policy names
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Possible, for full and max: the Japanese in-game player editor
      in the PAL release; first find its code and whether PAL still
      holds it ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))
- [ ] LMAST Realism on the disc: the map (`texmap.py match`), the
      picture-to-texture step (`svr.py replace`), the command that
      applies the crests and match pictures (`texmap.py apply`) and the
      `--mod realism` switch (LMASTER full and max, with the licensed
      crests' border) work, tested in PCSX2; left are the CSP and
      ACROBATA pack writers (section 3). The kits stay Realism-only
      ([`TEXMAP.md`](DOC/TEXMAP.md),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#lmast-realism-on-the-disc))

Bugs and ideas reported in play (Nexxus's reports, 2026-11-10). None is
investigated yet: each needs the cause found in the game code, then a
switch or a decision to set it aside. The first four are menu and data
problems; the match bugs come after them.

- [ ] Bug: the rotating (non-digital) advert boards don't show in your
      own stadium. Find out whether the board type is read from the
      stadium's advert slots, and whether the model or the look record
      loses it
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#still-unknown))
- [ ] Bug: a youth player's potential screen can contradict itself (a
      great player with a lot of potential, then almost none). Find the
      two comments' sources and the values each reads; the fix is a
      candidate switch
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#still-unknown))
- [ ] Idea: every player shown with a first name and a surname
      (`S.Aguero` as Sergio Aguero, `Cahwan` as Oliver Kahn, `L.Ginster`
      with Ginster's first name). Check how far the name fields allow
      it and what `realnames.py` and `--mod real-names` already cover
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] Idea: random sponsors and kit manufacturers for the clubs you
      don't manage, drawn again every season. Find where the other
      clubs' sponsors are set and whether the season rollover can run
      the draw
      ([`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md#still-unknown))
- [ ] Bug: a team on auto game plan doesn't substitute a slightly
      injured player nearly as often as expected, and judges stamina
      and lost ability poorly. Read the manager's substitution check
      for which inputs it weighs and the thresholds
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] Bug: on a switch of play from wing to wing, the player chosen to
      receive the ball is sometimes from the wrong side of the pitch.
      Find the receiver pick (the call-up of the selected player on a
      long pass) and what it measures from
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] Bug: a player with the ball in the attacking third sometimes
      turns and sprints back, passing only in his own third. Find the
      move order that sends the ball carrier back
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] Bug: the ball sticks at a player's feet or in no man's land and
      the player stands still for a while, in quick play sometimes for
      a whole half. Find what holds the ball carrier's decision
      ([`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md#still-unknown))
- [ ] Bug: a throw-in sometimes goes straight to the player in front and
      to the side, who dribbles it out of play at once. Find the throw
      target pick and the receiver's first move
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
