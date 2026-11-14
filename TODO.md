<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# TODO

The work that's left, and what each piece is for. [`GOALS.md`](GOALS.md)
lists the eight goals the project works towards; this file turns each
into tasks.

How it's laid out:

- **[Next up](#next-up)** is what to pick up first.
- **[The goals](#the-goals-and-what-each-still-needs)** shows, for each
  goal, what works today and what still stands in the way.
- **One section per goal**, in the order of
  [`GOALS.md`](GOALS.md#what-a-mod-should-be-able-to-change). Each
  opens with the goal, what works today and when it is done, then lists
  the open tasks. A task starts with the stage of
  [`GOALS.md`](GOALS.md#the-path-there) it belongs to: **read** (parse
  and document a file), **understand** (find what a field means),
  **write** (a writer that round-trips), **rebuild** (get edits onto a
  bootable disc), **edit** (a tab in the editors) or **distribute**
  (share a mod). A **test** task is a check in the game, which has no
  stage of its own. Stage 0, decrypting `DATA.CVM`, is done.

Each task links the doc that holds its details: the facts, the evidence
and the "Still unknown" list it comes from. The checks only a person can
make in the game are in [`TESTING.md`](TESTING.md), written for every
contributor (what to build, what to look for, how to report it); a
goal's **test** line points there. When a question is answered it comes
off the doc's list, and a finished task moves to the end of the same
goal's section in [`DONE.md`](DONE.md) as a short paragraph or a few
lines.

## Next up

What to work on next, most valuable first.

1. **The LMASTER Mod: max in the game.** Tested so far: every part of
   `--mod harder-economy`, `transfer-fees`, `fee-tiers` at the low end,
   `pr-costs`, `merch-costs`, `slow-reputation` after a match, and the
   separate career saves. Through a German season Nexxus found the game
   much harder economically, with the fanbase growing much more slowly
   and merchandise income much lower (2026-10-27). Left: the other
   `--mod balance` switches and `pr-cycle`, the lower cups' seeded
   brackets, and the `-V` VS folder (the third tier's transfer windows,
   season's end, saving and loading are tested). The test disc is
   `LMAST-test-season4.iso`, built 2026-10-31, with its test sheet
   `names/test-sheet-season.md`
   ([`TESTING.md`](TESTING.md#the-lmaster-mod),
   [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)).
2. **Graphics and sound: LMAST Realism on the disc.** `svr.py` writes
   textures and `texmap.py` maps the pack onto the disc: 1,612 of its
   1,613 PNGs have a disc texture, 1,600 of them in plain `.PAC` packs
   that `pac.py replace` writes, 8 in `CSE/*.CSP` packs that
   `csp.py replace` writes and 4 in the `ACROBATA` pack, which has no
   writer. `texmap.py apply` writes the crests and match
   pictures into copies of their packs (799 textures), and `--mod
   realism` (LMASTER full and max) builds them into a disc, which works
   in PCSX2. Nexxus's scope (2026-11-12): the pack's `Fixes`, `Adboards`
   and `Leagues` folders go on the disc, all 73 files (66 in plain packs,
   7 in CSP packs); `Intro` waits for LMASTER's own intros, and `Rival`
   stays out (an upscale made from mipmaps, largely incompatible). Left:
   seeing the `Fixes`, `Adboards` and `Leagues` pictures in the game
   ([`TESTING.md`](TESTING.md#graphics-and-sound)).
   The kits stay Realism-only (a PCSX2 texture pack)
   ([`TEXMAP.md`](DOC/TEXMAP.md),
   [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#lmast-realism-on-the-disc)).
3. **The LMASTER Mod: every switch on the Japanese release**, needed
   before LMASTER 1.0.0. Every switch but `realism` builds there now,
   `real-names` (English names in ASCII) and `third-tier` (its code,
   save, data and 93 places ported) included. Left: the third tier's
   rules text in Japanese, `realism` (the pack is named by PAL hashes),
   and the other switches on a Japanese disc in the game (a third-tier
   disc already boots, starts a career, saves and loads in PCSX2)
   ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#the-third-tier-on-the-japanese-disc)).
4. **The starting season: a smaller first division in the game**
   ([`TESTING.md`](TESTING.md#the-starting-season)): France at
   18 from the Season tab, and two nations changed in one build; only
   England at 22 is tested
   ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from)).
5. **The LMASTER Mod: the newest switches in the game.** Each is built on
   a test disc and waits for a look: `modern-font` and `title-banner`
   (seen on a few screens, 2026-11-13; the font's stray pixels, reported
   2026-11-14, are fixed and need a fresh disc to confirm; the rest of
   the screens still to go through), `random-sponsors` (seen on Real Betis and England's
   national team; the other clubs, leagues and the generated Italian,
   Spanish and Dutch kits are left), `moving-boards` and the charisma
   line of `retail-text` (both built 2026-11-10)
   ([`TESTING.md`](TESTING.md#newer-switches),
   [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status)).

## The goals, and what each still needs

The goals of [`GOALS.md`](GOALS.md#what-a-mod-should-be-able-to-change),
in the same order.

| Goal | What works today | Still in the way |
|---|---|---|
| [**The starting season**](#the-starting-season) | leagues, squads, clubs, the new club, free agents, schedules and division sizes, regulations and results: writers and editor tabs, tested in PCSX2. The national-team calendar and the club ranking have writers and tabs; division sizes follow the calendar, and the leagues never play on the national-team dates | a smaller first division, the national calendar and the club ranking tested in the game |
| [**Data**](#data) | players, staff, clubs, kits, crests and flags, facilities, training, camps, tours, the tactics presets, the PR events, the player links, and the stadiums' looks and boards: writers and tabs | the remaining player and staff fields; the other stadium tables |
| [**Parameters**](#parameters) | every `PARAM/` table's layout is known and `tbb.py replace` swaps any table; the economy's constants in the executable are traced and changed by named switches | the open fields of the parameter files, the match AI's files and the match parameters |
| [**Text**](#text) | every message in every language, with a writer and the Text tab; real names for every league, club and nation | the screen-set variables and a few message categories |
| [**Graphics and sound**](#graphics-and-sound) | textures to PNG, models to OBJ and glTF, sound to WAV and MIDI; kits, crests and stadium looks edited as data; every texture file rebuilt and rewritten, with LMAST Realism's crests, match pictures and Fixes, Adboards and Leagues folders on a disc (the CSP pictures not yet seen in the game) | the `ACROBATA` and `PackData` pack writers and a changed-size texture in a CSP pack; the kits stay Realism-only |
| [**Playing a mod**](#playing-a-mod) | xdelta patches against the Redump image, CSO, ZSO and CHD inputs, separate saves for a modded disc, the players' guide, the save editor | faster CHD decoding; the save editor's Candidates page; a Japanese save edited and played, and both editors on the Japanese release |
| [**The LMASTER Mod**](#the-lmaster-mod) | lite, full and max build, with most switches tested in PCSX2; every switch but `realism` builds on the Japanese release | the in-game checks of the newer switches, a Japanese disc run in the game, the candidates and the bugs reported in play |
| [**The end point**](#the-end-point) | every folder of `DAT/` has a doc and a tool; about 12,600 symbols are named; the Japanese release is extracted and read through `gamever.py` | every doc's "Still unknown" list; the editors on the Japanese release |

## The starting season

**Goal:** the state a new game begins in: schedules, competitions,
league membership, clubs, squads and players. The game then plays on
from there as normal.

**Works today:** leagues, squads, clubs, the new club, free agents,
schedules and division sizes, regulations and results have writers and
editor tabs, tested in PCSX2 (England's first division at 22 clubs over
two seasons). The national-team calendar and the club ranking have
writers and tabs, and the leagues never play on the national-team dates.

**Done when:** every change the editor offers here has been played
through a season or more in the game.

- [ ] **test** A smaller first division (France at 18, two nations
      changed in one build), the national calendar and club ranking tabs
      and squad ages, in
      [`TESTING.md`](TESTING.md#the-starting-season)
- [ ] **understand** The remaining schedule and club-ranking fields:
      `PeriodName.tbb`, the `make_list` sources, what
      `CLUB_RANK_SYSTEM`'s nation groups and tallies feed, what game bit
      `w0` 8 marks (a league that `leaguesize.py build` resizes loses
      it), which code greys an Information-menu entry and when the game
      unloads a finished schedule
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#still-unknown),
      [`PARAM_DIR.md`](DOC/PARAM_DIR.md#still-unknown))
- [ ] **understand** What adds a year to the age shown for players and
      staff on a `--skip-tutorial` career
      ([`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#still-unknown); the
      squads' side is a check in [`TESTING.md`](TESTING.md))

## Data

**Goal:** club, player, stadium and staff records, kits and crests, and
the text that goes with them.

**Works today:** players, staff, clubs, kits, crests and flags,
facilities, training, camps, tours, the tactics presets, the PR events,
the player links, and the stadiums' looks and boards have writers and
tabs. Nearly every player and staff field is named; the open ones are below.

**Done when:** every field of those records has a name and a known
range and is editable in a tab, or is shown to have no effect.

- [ ] **understand** The tendencies' last match details: the two checks
      that put a team in situation 3 or 4, and which tactics slider sets
      where situation 1 starts
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] **understand** Staff: the fields only the developers' field table
      names, and the model pattern
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] **understand** National teams: what `_getNationalTeamPoint`
      scores, why team 465 and the call-up's flag `0x300` matter, and
      what `pwkOteam_InitNonresident` mode 1 does with the fixed squads
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#national-team-call-ups))
- [ ] **understand** Stadiums: byte `+0x0c` of your stadium record and
      the names of its 6 advert slots
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#still-unknown))
- [ ] **understand** Kits and faces: the face block-4 header, the kit
      tables' open side fields and descriptor bytes 14–15
      ([`PLAYER_DIR.md`](DOC/PLAYER_DIR.md#still-unknown),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#still-unknown))
- [ ] **read** `EMBLEM/`: which player-editor choices pick the rows of
      `EDIT_PLAYER.TBB` tables 19–21, 25 and 26, and tables 29–31
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#edit_playertbb))
- [ ] **write** The `STADIUM/` tables besides `BUILD_STADIUM`'s looks
      and boards (`CONV_INFO_BUILD`, the crowd sets), if a mod needs them
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#editing))
- [ ] **edit** A tab for each writer the **write** task above adds
- [ ] **test** The kits, the player and crest editors' tabs, the
      Stadiums tab and the other tabs not yet seen in the game, in
      [`TESTING.md`](TESTING.md#data)

## Parameters

**Goal:** the tuning values in the `TBB1`/`TBL1` tables and the
executable: prices, growth rates, event odds, match settings and so on.

**Works today:** every `PARAM/` table's layout is known and `tbb.py
replace` swaps any table. The economy's constants in the executable are
traced and changed by named LMASTER switches.

**Done when:** every table and constant has named fields, a writer and,
where a mod would touch it, a switch or a tab.

The club game:

- [ ] **understand** Training and camps: the scale of a practice's
      values, the names of the camp types and youth menus, which camp
      each sponsor frees
      ([`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md#still-unknown),
      [`CAMP_FORMAT.md`](DOC/CAMP_FORMAT.md#still-unknown))
- [ ] **understand** Injuries: how many game days an injury value lasts,
      the injury chance, and what makes the match report a heavy injury
      ([`INJURIES.md`](DOC/INJURIES.md#still-unknown))
- [ ] **understand** Sponsors: where message 61's "remaining
      negotiations" text is used, if anywhere (the Japanese release
      only stops a second negotiation with the same sponsor), and the
      acceptance tables
      ([`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md#still-unknown))
- [ ] **understand** The rest of the parameter files' open fields:
      [`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#still-unknown),
      [`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md#still-unknown),
      [`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#still-unknown),
      [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md#still-unknown),
      [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#still-unknown),
      [`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md#still-unknown),
      [`ECONOMY.md`](DOC/ECONOMY.md#still-unknown),
      [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md#still-unknown)

The match:

- [ ] **understand** The tactics AI files: which gait each move order
      kind is (its animations have no names), the kicker roles' yes/no
      and the three receiver handlers, and `Combi3`'s presets 22–34
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] **understand** `GAMEDATA.BIN`: the rest of a ball-contact record,
      what sets a player's record, and whether anything reads
      `AI_PARAM.BIN`
      ([`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md#still-unknown))
- [ ] **understand** Match parameters: the kick kinds that share a
      builder and where some are first set, the flag bits, the getter
      calls with no class, the sources of parameters 5, 16 and 24, what
      the kind table's float scales and what the events `0x68`–`0x6d`
      start
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#who-reads-each-parameter),
      [`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] **test** The match policy check and the dribble styles, in
      [`TESTING.md`](TESTING.md#parameters)

## Text

**Goal:** message text in every language slot, including event dialogue,
news and mail.

**Works today:** every message in every language has a writer
(`mbb.py`) and the Text tab, and the event, news and mail tables are
parsed (`evsdatabin.py`). `--mod real-names` gives every league, club
and nation its real name.

**Done when:** every message category is traced to the screen that shows
it, and any message can be changed in the Text tab.

- [ ] **understand** Message text: the screen-set variables, the raw
      `0x0A`/`0x0D` bytes, the rival owner's name, the `1000xx`
      categories and where the speaker names (`{name:N}`) come from
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#still-unknown)); the NEWS
      columns `+0x20`, `+0x60` and `+0x70`
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#still-unknown))
- [ ] **understand** Events and procedures: the request fields, loan
      availability, the instruction-age rows, and the screens that start
      procedures 9, 14/16/18, 22 and 28
      ([`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md#still-unknown))
- [ ] **understand** The event records: what `EVENT` `+0x0c`, `+0x1c`,
      `+0xdc` and the five triplets are, the names of the condition and
      handler kinds, and what PAL's records 352 and 353 (a player comes
      to the office wanting a word) are for and why the Japanese disc
      holds them as inactive stubs
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#still-unknown))
- [ ] **test** A raw line break in a message, in
      [`TESTING.md`](TESTING.md#text)

## Graphics and sound

**Goal:** extract textures, models and sound; edit them after the data.
The one exception is bringing Nexxus's LMAST Realism texture pack onto
the disc.

**Works today:** textures go to PNG, models to OBJ and glTF, sound to WAV
and MIDI. `svr.py` rebuilds every texture file and writes a picture into
a texture; `csp.py` writes same-size textures in CSP packs (all 489 PAL
and 438 Japanese packs rebuild byte for byte). LMAST Realism's crests and
match pictures are on a disc through `--mod realism`, tested in PCSX2.
`--mod modern-font` draws the main text in a new face (PAL).

**Done when:** every texture file can be written back and the pack's
chosen folders are seen on a disc in the game.

- [ ] **read** `ACROBATA/`: the `ABDT` scene layout, the `ABRS` header
      table, why `W_BG_WALK_007` has no scene id and whether language
      slot 6 (`_du`) is Dutch
      ([`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md#still-unknown))
- [ ] **read** `OPMOVIE.SFD` (Sofdec video, outside `DATA.CVM`)
      ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md#still-unknown))
- [ ] **understand** Which screens play which music id and `bgm` track,
      and whether anything plays `MAP06`, `map02`'s songs 3–5 or the
      four banks the code never names
      ([`SOUND_DIR.md`](DOC/SOUND_DIR.md#still-unknown),
      [`AUDIO_DIR.md`](DOC/AUDIO_DIR.md#still-unknown)); closer SPU2
      emulation ([`GAME_DIR.md`](DOC/GAME_DIR.md#still-unknown))
- [ ] **understand** Ninja models: material colours and layer flags,
      hair tint, skin words and submotion interpolation
      ([`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md#still-unknown))
- [ ] **understand** Rooms and people (`BG/`): the room table's fields,
      a room's palette, `HUMANID.BIN`'s object kinds and roles
      ([`BG_DIR.md`](DOC/BG_DIR.md#still-unknown))
- [ ] **understand** Fonts, what is still open: how the picture is
      sampled (the GS filter and clamp), whether a larger atlas fits in
      VRAM, which screens use the small fonts, and the Japanese build's
      open points
      ([`FONT_FORMAT.md`](DOC/FONT_FORMAT.md#still-unknown))
- [ ] **understand** Newspapers: which paper a page uses, the special
      editions, where the ads and cartoons go
      ([`NEWS_DIR.md`](DOC/NEWS_DIR.md#still-unknown))
- [ ] **write** Writers for the packs that hold textures and have none
      (the `ACROBATA` pack's 2,137 textures and the KC@P `PackData`
      packs: kits, cut-ins, faces), and a changed-size texture in a CSP
      pack, for LMAST Realism on the disc
      ([`SVR_FORMAT.md`](DOC/SVR_FORMAT.md#writing))
- [ ] **test** LMAST Realism on the disc: the `Fixes`, `Adboards` and
      `Leagues` pictures, the CSP ones included, seen in the game. The
      kits stay Realism-only
      ([`TESTING.md`](TESTING.md#graphics-and-sound),
      [`TEXMAP.md`](DOC/TEXMAP.md),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#lmast-realism-on-the-disc))
- [ ] **understand** Idea (Nexxus, 2026-11-10; reopens the 2026-11-07
      choice that the kits stay Realism-only): LMAST Realism's kits on
      the disc as licensed kits, by widening the licence from the 116
      Italian, Spanish and Dutch clubs to the clubs of the six leagues.
      What it takes, none of it started: a finished shirt, shorts and
      socks picture per club, home and away, with the keeper kit
      (Realism has the parts with a picture per palette, not a picture
      per club, so each would be built from a club's design and
      colours); a writer for the `PLPACK_HOME`/`AWAY` packs (the
      `PackData` writer above); the licence table and the descriptor table
      grown and moved into the code segment (addresses and row layout in
      `UNIFORM_FORMAT.md`); and the descriptor bytes for each club
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#licensed-kits),
      [`TEXMAP.md`](DOC/TEXMAP.md))
- [ ] **test** The widescreen patch on a modded disc, the font and the
      sound checks, in
      [`TESTING.md`](TESTING.md#graphics-and-sound) and
      [`TESTING.md`](TESTING.md#newer-switches)

## Playing a mod

**Goal:** a player turns edits into a disc or an xdelta patch, applies it
to their own disc, and keeps its saves apart, on the PAL release and on
the Japanese one.

**Works today:** `patch_disc.py` builds a disc that boots, and
`vcdiff.py` makes xdelta patches against the Redump image (the tools read
CSO, ZSO and CHD inputs). A modded disc keeps its own saves, `save.py`
and the save editor read and edit PAL career saves, and
[`INSTALL.md`](INSTALL.md) is the players' guide. `save.py --iso ISO_JP`
reads Japanese saves, and a Japanese third-tier career saves and loads
in PCSX2 (Nexxus's report, 2026-11-12).

**Done when:** the image formats players keep are covered and a career
can be played, saved, edited and carried to a modded disc on both
releases.

- [ ] **rebuild** A Japanese save edited with `save.py --iso ISO_JP` and
      run in the game. Later, but needed before the reverse engineering
      counts as complete (Nexxus's choice, 2026-11-01)
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-japanese-release))
- [ ] **rebuild** Optional: dual-layer images, for a disc that grows
      past a single-layer DVD
      ([`REBUILD.md`](DOC/REBUILD.md#limits))
- [ ] **read** The parts of the save no tool reads: `info.bin` past the
      date, `dm.bin` and the VS data save
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] **understand** The save fields still open: PlPinfo flags and
      dissatisfaction, statistics table 1, the candidate records, the
      other clubs' and staff's untraced bytes, and when the club ranking
      runs
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] **understand** The rest of Virtua Pro Football's save, from VPF's
      code in the sister project: how VPF numbers a new edit player, the
      record bytes the import doesn't read, and `file.inf`'s check
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#still-unknown))
- [ ] **edit** The save editor's Candidates page is read-only:
      `save.py set` has no key for the candidate lists. It needs the
      player candidate record's 32 bytes decoded first
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md#still-unknown),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] **edit** The mod editor and the save editor on the Japanese
      release. Later, but needed before the reverse engineering counts
      as complete (Nexxus's choice, 2026-11-01)
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md#still-unknown))
- [ ] **distribute** Optional: faster CHD decoding (a whole disc takes
      about ten minutes in Python) and CHDs with several CD tracks
      ([`REBUILD.md`](DOC/REBUILD.md#compressed-images))
- [ ] **test** The save editor's pages, the Regulations tab's save and
      the separate-save folders, in
      [`TESTING.md`](TESTING.md#playing-a-mod) and
      [`TESTING.md`](TESTING.md#the-starting-season)

## The LMASTER Mod

**Goal:** the project's own mod, in three editions (lite, full and max):
fixes for what the release cut or broke, real names, a third tier and a
harder economy. Each fix or improvement is a named `patch_disc.py`
switch tested in PCSX2 ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)).

**Works today:** the three editions build, with the switches grouped as
[`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels) lists them, and
most are tested in PCSX2. Every switch but `realism` builds on the
Japanese release, and `modern-font` and `title-banner` draw with a font
file (`--font`).

**Done when:** every candidate is built and tested in the game or set
aside, and every switch works on the Japanese release.

- [ ] **rebuild** **Needed before LMASTER 1.0.0** (Nexxus's choice,
      2026-11-01): every switch works on the Japanese release
      (SLPM-66316), except the modern font, which may be PAL only
      (Nexxus's choice, 2026-11-13). The release itself is Nexxus's call,
      when testing, features and reverse engineering feel complete; this
      is its one firm requirement. Every switch but `realism` builds on
      the Japanese disc (`real-names` and `third-tier` 2026-11-12). Left:
      the third tier's rules text in Japanese (the messages keep the
      retail rules; whether to write it in Japanese, which someone who
      reads it would have to check, or leave it in English is not
      decided), `realism` (so LMASTER full and max can't be built for
      it), the title banner (below), and running a Japanese disc built
      with the switches in the game (a third-tier disc boots, starts a
      career, reaches the tutorial's playoffs and saves and loads,
      Nexxus's reports 2026-11-12)
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#the-third-tier-on-the-japanese-disc))
- [ ] **rebuild** The title banner on the Japanese release (2026-11-13):
      the release has one title pack, `SC_TITLEBG.CSP`, with another
      picture, so the switch skips it there
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#title-banner))
- [ ] **write** The real names in Japanese on the Japanese disc
      (Nexxus's wish, 2026-11-12): `--mod real-names` there writes the
      English names in ASCII for now. The 1,069 names (clubs, stadiums,
      nations, competitions and stages) would need half-width katakana
      forms like the original game's (Nexxus's choice, 2026-11-12), in a
      new column of `SRC/realnames.csv` that `realnames.py` writes into
      slot 0 in place of the ASCII name where it has one (`mbb.py`
      already encodes the half-width kana and the voiced-kana bytes,
      [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#japanese-voiced-kana)). A draft
      can be made here, but someone who reads Japanese should check it
      (the game's own katakana names for the unlicensed clubs are in the
      Japanese `MES.PAC` to follow, such as ﾊﾞｰﾐﾝｶﾞﾑ for Birmingham)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#real-names))
- [ ] **distribute** LMASTER Mod's build for the two switches that draw
      with a font file (`modern-font` and `title-banner`, 2026-11-13):
      its release build should pass `--version <VERSION>` and `--font` (a
      `fonts` folder in that repository with `RobotoCondensed[wght].ttf`
      and the Apache 2.0 licence text, which `patch_disc.py` already
      looks in), and its changelog should list both
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#modern-font))
- [ ] **understand** Re-assess each switch's edition (Nexxus's request,
      2026-11-01): some bug fixes may sit in full instead of lite. A
      first read: `salesman-items` (in `restorations`) bundles a plain
      fix, the spikes' and headphones' boosts swapped against their text,
      with the coach's unused flag, a restoration; `league-balance` (in
      `leagues`) fixes runs of up to 9 games at one venue but is called
      an improvement; and the other way, `national-cups` (in lite's
      `match-fixes`) moves the cups a turn to make their results
      viewable, closer to an improvement. The rule (Nexxus's,
      2026-11-01): a fix that can't break a retail career in progress
      goes in lite, one that may stays in full. Go through every switch:
      is it a fix, and could it break a retail save in progress (data the
      save holds, a schedule or club list it was made with); then propose
      moves for Nexxus to confirm
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels))
- [ ] **understand** Candidate: the short `EDIT_EMBLEM` tables 93/101/105
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] **understand** Candidate: let the unused combination records load,
      and fix the pattern repeat check; decide first whether the extra
      records play sensibly
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] **understand** Candidates from the manager's fields: the match
      reading the selection policy instead of the match policy (after
      its test in [`TESTING.md`](TESTING.md#parameters)),
      the strength ratio above 1.19 getting column 0, and the training
      plan's rows out of step with the policy names
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] **understand** Possible, for full and max: the Japanese in-game
      player editor in the PAL release; first find its code and whether
      PAL still holds it
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#planned))
- [ ] **understand** Whether stadium 117 (the seventh `ho04a` row, which
      `CONV_INFO_BUILD` doesn't list) should get the moving-boards
      treatment, and what reaches it in the game (`PARAM/STADIUM_DATA`,
      the rival's ground, the real grounds' ids 102–118)
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#the-request-in-a-match))
- [ ] **understand** Where the Information screen's Competitions tab
      takes its competition list from (it leaves out the third-tier
      leagues, as the design wants, so it must use a list of its own)
      ([`UID_LIMITS.md`](DOC/UID_LIMITS.md#still-unknown))
- [ ] **test** The newer switches and the third tier's checks, in
      [`TESTING.md`](TESTING.md#the-lmaster-mod) and
      [`TESTING.md`](TESTING.md#newer-switches)

Bugs and ideas reported in play (Nexxus's reports, 2026-11-10). None is
investigated yet unless it says so: each needs the cause found in the
game code, then a switch or a decision to set it aside. The first few
are menu and data problems; the match bugs come after them.

- [ ] **test** Bug: the rotating electric advert boards (the moving
      board, advert slot 4) don't show in your own stadium, only the LCD
      ones, though they show at computer clubs' grounds. Known so far:
      the moving board needs boards 43 and 52 on in the ground's row, and
      it wins over the LCD style when both are built. Mostly a level-4
      ground (Nexxus, 2026-11-10), whose rows have boards 43 and 52 off
      and the LCD set on. `--mod moving-boards` (lite) now makes those
      rows like level 3's, so computer clubs' level-4 grounds show the
      plain boards too. Left: test in PCSX2
      ([`TESTING.md`](TESTING.md#newer-switches))
      ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#the-request-in-a-match))
- [ ] **test** Bug: a youth candidate's comments can contradict
      themselves (a great player with a lot of potential, then almost
      none). Found in the texts: the second line rates star quality or
      charisma (スター性) but 8657, 8658 and 8660–8663 say "potential";
      only 8659 says charisma, and German 8659 is wrong. `--mod
      retail-text` now rewords them as charisma (all five languages).
      Left: test in PCSX2
      ([`TESTING.md`](TESTING.md#newer-switches)),
      and find which values the two lines read
      ([`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md#youth-candidates-comments-partly-confirmed))
- [ ] **understand** Idea: every player shown with a first name and a
      surname (`S.Aguero` as Sergio Aguero, `Cahwan` as Oliver Kahn,
      `L.Ginster` with Ginster's first name). Check how far the name
      fields allow it and what `realnames.py` and `--mod real-names`
      already cover
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] **test** Random sponsors and kit suppliers for the clubs you don't
      manage, drawn again every season (the poll went 4-0 for it,
      Nexxus, 2026-11-10), with the licensed leagues unlicensed. Done:
      `--mod random-sponsors` (full and max) sets them from the team
      number and the season, unlicenses the 114 clubs with generated kits
      from `SRC/kits.csv`, and lets every club's kit draw its logos (the
      gate was at `0x2c54d8`); seen on Real Betis in PCSX2. Left: the
      other clubs and leagues in PCSX2
      ([`TESTING.md`](TESTING.md#newer-switches)),
      the kits corrected club by club (written from memory with 12 shirt
      patterns), the other shirt designs checked in the viewer, the
      keeper kits (still the rows' own) and the Japanese release
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#random-sponsors),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#licensed-or-generated-the-flag))
- [ ] **understand** Idea (Nexxus, 2026-11-10): computer clubs' kits
      changing from season to season, as the sponsors do. The unlicensed
      clubs' kits come from `UNIFORM_LIST.TBB`'s designs and colours; a
      patch could vary the shirt, shorts or socks design by season. Left:
      see which of the 209 shirt, 61 shorts and 18 socks designs suit
      another design's colours, and keep each club's own colours so it
      stays recognisable
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md))
- [ ] **understand** Bug: a team on auto game plan doesn't substitute a
      slightly injured player nearly as often as expected, and judges
      stamina and lost ability poorly. Read the manager's substitution
      check for which inputs it weighs and the thresholds
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#still-unknown))
- [ ] **understand** Bug: on a switch of play from wing to wing, the
      player chosen to receive the ball is sometimes from the wrong side
      of the pitch. Find the receiver pick (the call-up of the selected
      player on a long pass) and what it measures from
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] **understand** Bug: a player with the ball in the attacking third
      sometimes turns and sprints back, passing only in his own third.
      Find the move order that sends the ball carrier back
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))
- [ ] **understand** Bug: the ball sticks at a player's feet or in no
      man's land and the player stands still for a while, in quick play
      sometimes for a whole half. Find what holds the ball carrier's
      decision
      ([`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md#still-unknown))
- [ ] **understand** Bug: a throw-in sometimes goes straight to the
      player in front and to the side, who dribbles it out of play at
      once. Find the throw target pick and the receiver's first move
      ([`BPB_FORMAT.md`](DOC/BPB_FORMAT.md#still-unknown))

## The end point

**Goal:** the reverse engineering is complete: every file, every line of
code and every mechanic of the game fully documented, on both releases
(Nexxus's definition, 2026-11-01;
[`GOALS.md`](GOALS.md#when-the-reverse-engineering-is-complete)).

**Works today:** every folder of `DAT/` has a doc and a tool whose `info`
passes over all of it, about 12,600 symbols of the executable are named,
and the Japanese release is extracted and read by the same tools through
`gamever.py`. `regress.py` checks every tool against a baseline.

**Done when:** every doc's "Still unknown" list is empty or shows what
has no effect on the game, on both releases, and the editors work on the
Japanese release as on PAL.

- [ ] **read** `GAME/` leftovers: the `SHADOWCOLLI.PAC` and
      `WALLCOLLI.PAC` entries (with `TEST3D/SHADOWCOLLI.LBI`), the
      `RBD0` trailer, `TEAM.TMB`, `BACK_MATCH.TBB`, the row layout of
      `TACTICS_PLAYBOOK_EDIT.TBB`, the cut-in pack's `CIB0`/`BMT1`
      blocks, the commentary's `BCR2`/`BCB3`/`BCV` records, whether the
      game loads `GAME/EFFECTS.DAT` and `TRAINING.DAT` or only the
      `SOUND/` files of the same names, and the `DTPK` kinds
      ([`GAME_DIR.md`](DOC/GAME_DIR.md#still-unknown))
- [ ] **read** `SEQ/`: `INFORMATION.WPX` and the command sets of the two
      2004 scripts
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#still-unknown))
- [ ] **read** Later (the project serves the English release first), but
      needed before the reverse engineering counts as complete: the
      Japanese release's differences still open
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#still-unknown))
- [ ] **read** The small open lists of the container, disc and
      test-data docs: [`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md#still-unknown),
      [`PAC_FORMAT.md`](DOC/PAC_FORMAT.md#still-unknown),
      [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md#still-unknown) (including the
      `0x200` bit of an animation track's kind),
      [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md#still-unknown),
      [`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md#still-unknown),
      [`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#still-unknown),
      [`TEST3D_DIR.md`](DOC/TEST3D_DIR.md#still-unknown),
      [`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md#still-unknown),
      [`WIDESCREEN.md`](DOC/WIDESCREEN.md#still-unknown)
- [ ] **understand** Game flow: which `Sche.YearEnd` value is which
      ending, how PlayAcrobata maps its argument to a scene, the
      sequencer's remaining commands and global records 0–12, and which
      players have a fixed detail-screen comment
      ([`GAME_FLOW.md`](DOC/GAME_FLOW.md#still-unknown),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#still-unknown))
- [ ] **understand** The overlay loader: where the overlay index comes
      from, and the SNR2 header fields `0x20`/`0x24`/`0x38`
      ([`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md#still-unknown))
- [ ] **understand** Decide whether the match-engine sections of
      [`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md) (about 900 lines: player
      parameters, who reads each, kick kinds, tendencies, press and
      carry) move to a doc of their own, linked from
      [`GAME_DIR.md`](DOC/GAME_DIR.md). Many links point at their
      anchors (`#the-kick-kinds`, `#the-tendencies`,
      `#who-reads-each-parameter`), so a split needs them updated
