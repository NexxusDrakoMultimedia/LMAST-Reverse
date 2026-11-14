<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Testing in the game

Every check here needs a person playing the game in PCSX2: seeing that
an edit shows on screen, reading what a screen says, or hearing how
something sounds. The tools can prove that a file is written correctly,
but not that the game does what we think with it. Anyone with the game
and PCSX2 can help, and no code is needed.

**The goal:** every edit and switch is seen working in the game. A
check is done when someone has played it and the result is in the doc
it links.

The checks are grouped by the goals of [`TODO.md`](TODO.md), in its
order, so you can see what each one proves. A goal's **test** line in
`TODO.md` points to its section here.

## How to take part

1. **Pick a check** below. Each says what to build and what to look
   for. Checks marked *short* take one match or a few screens; the
   others need part of a season or more.
2. **Build the disc.** You need your own copy of the game, dumped to
   match the Redump image ([`INSTALL.md`](INSTALL.md) shows how to check
   it). Make the edit with the mod editor and use File > Build disc
   ([`USAGE.md`](USAGE.md)), or run the command the check gives. A
   check that names an `LMAST-test-*.iso` refers to a disc Nexxus
   built; the doc it links says how it was made, and the Discord can
   help you build the same one. Game data is never shared, so each
   tester builds their own disc. What each LMASTER switch does is in
   [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md).
3. **Play it** and note what you see. A screenshot (F8 in PCSX2) or a
   save state helps, and for numbers a save state is best: the exact
   value can be read from it.
4. **Report it**: open an
   [issue](https://github.com/NexxusDrakoMultimedia/LMAST-Reverse/issues)
   or post on the [LMAST/SFCC English Fan
   Discord](https://discord.gg/7DNrGye9TZ) with what you changed, what
   you saw and the date. "It didn't work" is a result too: say what
   showed instead.

Use a separate memory card or the `--mod-saves` switch for test discs,
so a test can't touch a career you care about
([`INSTALL.md`](INSTALL.md)).

## How results are recorded

The result goes into the doc the check links, as "Tested in PCSX2" (or
"by ear") with who saw it and the date, for example "Nexxus's report,
2026-10-27". People are credited by the name they choose in
[`CONTRIBUTORS.md`](CONTRIBUTORS.md). The check then moves to the
"Tests in PCSX2" section of [`DONE.md`](DONE.md) as a short entry. A check
that is only partly done stays here, reworded to what is left.

A new check goes here when a tool can make an edit the game hasn't been
seen to take. It goes under the goal it serves, and the question behind
it stays in its doc's "Still unknown" list.

## The starting season

What these prove: the state a new game begins in (schedules, division
sizes, club lists, squads and free agents) plays on normally.

- [ ] A smaller first division (France at 18, from the Season tab) and
      two nations changed in one build; only England at 22 is tested
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [ ] The Club ranking tab (for example `rank:7:31=3`), and a resized
      league's added ranking rows (England at 22), each played to the
      end of the first season and read with `save.py clubs`
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#club_rank_systemtbb-the-club-rankings-tables))
- [ ] The National calendar tab: the World Cup squads called up a turn
      earlier (`3:88:callup=0 3:87:callup=1 3:87:finals=1`, a season
      starting in 2009), alone and with `--mod national-cups`
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md#schedule_listtbb-the-national-team-calendar))
- [ ] A save from the Regulations tab (the same edit from
      `regulation.py set` is tested)
      ([`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md#editing))
- [ ] A `CLUBRESULT.TBB` edit: a cup given a third-place match shows
      "3rd"/"4th" on the end of tournament screen
      ([`CLUBRESULT_FORMAT.md`](DOC/CLUBRESULT_FORMAT.md#editing))
- [ ] Squad ages: a career started without the tutorial skip, with Van
      der Sar (Manchester slot 0) at 16 in the mod: 16 means the skip
      adds the year
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#oteammembertbb))
- [ ] A club from outside the leagues (team 245 on, the rest of Europe
      and beyond) swapped into a league with `initteam.py swap`: whether
      it plays its league games
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#swapping-clubs))
- [ ] The Nations & stadiums tab: one nation edit (`setnation`) and one
      stadium edit (`setstadium`), neither checked in the game yet
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md#stadium_datatbb-stadiums))
- [ ] Transfer List bands: free agents set just inside and just outside
      the rank band of a club above the lowest rank, seen on its
      Transfer List (only a new club's band is tested)
      ([`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#which-free-agents-the-transfer-list-shows))

## Data

What these prove: edits to players, kits, crests, stadiums, tours and
the other records show in the game as the editor says they will.

- [ ] *Short.* A main-position change with `pbdata.py --sles` on its own
      (rank edits are tested) ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [ ] Kits: an edit to only one licensed-kit descriptor copy, to tell
      which one a match reads; whether screens outside a match show
      your club's stored keeper kit; and whether anything reads a
      licensed club's own `UNIFORM_LIST.TBB` row (edit only that row)
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#still-unknown),
      [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#editing))
- [ ] Kit style: outfield gloves on a player with `gloves` 1–4 in a
      career match between November and March (not in VS), and the cap
      on an edit player made with the GK Style page's Hat, in the
      editor's preview and in a match
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#kit-style))
- [ ] *Short.* The crest editor: whether the three short `EDIT_EMBLEM`
      layer tables lose visible parts
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#the-layer-tables-12143))
- [ ] *Short.* The Crests tab's other tables (only the starting crest
      is tested): one edit each to a preset's position, a layer record
      and a flag crest placement, seen in the club editor's crest and
      flag screens, and a crest part's `rev` set to 1 to see what it
      does (mirrored is the likely reading)
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#editing))
- [ ] *Short.* The Player editor tab: an edit to `EDIT_PLAYER.TBB`
      shows on a player made in the game's player editor, for example
      table 15's {min, max} for one ability raised to {90, 90}, so every
      new player gets 90 there
      ([`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#edit_playertbb))
- [ ] The Player links tab: one edit
      ([`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md#writing-the-streams))
- [ ] The Tours, Tactics and Comments tabs: one edit from each (a tour
      opponent, a preset's formation, a manager comment cell)
      ([`PARAM_DIR.md`](DOC/PARAM_DIR.md),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-detail-screen-comments))
- [ ] *Short.* The Stadiums tab: one stadium built like another (for
      example a small club's ground built like 99, the `ho04a` bowl) and
      one of its boards changed, on a test disc built from the editor
      (File > Build disc); play a match there, with and without LMASTER
      full ([`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#editing))

## Parameters

What these prove: what the match reads from its parameters, and how the
match AI behaves.

- [ ] The match policy: give a computer club's manager selection policy
      0 and then 7 (match policy unchanged), play a match against it
      while behind or ahead late, and see whether its tactics and
      substitutions change; that tells whether the match reads the
      selection byte by mistake
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-developers-staff-editors))
- [ ] By eye: what the four dribble styles look like. Give players
      `dribble_style` 0, 1, 2 and 3 (People tab, "Personality and
      condition") and describe how each dribbles in a match
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-tendencies))
- [ ] Match bugs, caught as save states (the retail disc will do; the
      bugs are in the retail game). When one happens, pause and save a
      state to its own slot straight away, then note the slot, the match
      and what was happening. The bugs are listed in
      [`TODO.md`](TODO.md#the-lmaster-mod) under "Bugs and ideas
      reported in play". The most useful is the stuck ball, since it
      lasts: a player standing still with the ball at his feet or the
      ball dead in open play, ideally still stuck when you save. A
      state taken just after a wrong-side receiver pick, a backwards
      sprint with the ball in the attacking third, or a throw-in to the
      player in front that dribbles it out also works. Report the slot:
      the ball carrier's and the team's AI state can then be read from
      the state's memory
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))

## Text

What this proves: how a message's control bytes show on screen.

- [ ] By eye: whether a raw line break in a message (`{lf}` in
      `mbb.py`'s output, 4,129 in the European languages) breaks the
      line on screen
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#other-control-bytes))

## Graphics and sound

What these prove: the pictures and sounds written to a disc, and the
widescreen patch, work in the game.

- [ ] LMAST Realism's `Fixes`, `Adboards` and `Leagues` pictures on a disc
      built with `--mod realism` (`python SRC/patch_disc.py patch "<the
      PAL image>" out.iso --mod realism --copies --dat DAT --realism
      <the pack>`; the CSP pictures are new): the club facilities
      screens (`WP_FACILITIES_01` to `_03`), an advertising board, and the
      league logos (the six-nation league screens, `SC_SIXNATIONS_01` to
      `_04`) show the pack's pictures, with nothing garbled or missing
      ([`TEXMAP.md`](DOC/TEXMAP.md#putting-the-pack-on-the-disc-apply),
      [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md))
- [ ] *Short.* The widescreen patch on a modded disc: copy the pnach
      under the modded executable's own CRC
      ([`INSTALL.md`](INSTALL.md#pcsx2-patches)) and check the picture
      is widened ([`WIDESCREEN.md`](DOC/WIDESCREEN.md#still-unknown))
- [ ] By ear: the commentary (`BC_ENG`), the tannoy (`JYONAI_A`) and
      `MAP01` ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md#still-unknown))

The modern font and the title banner, which also change what the game
looks like, are under [the LMASTER Mod](#newer-switches).

## Playing a mod

What these prove: a modded disc keeps its own saves, and the save
editor's edits load in the game.

- [ ] *Short.* A `--mod-saves` disc writes its VS data to
      `BESLES-54151-V000`, and an LMASTER full disc its careers to
      `-F000`
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [ ] Save editor step 4: load an edit made through the editor itself
      (not `save.py set`) on each page it has not been seen on. Already
      seen in the game: money, club status and rank, the season plan, a
      player's fatigue, condition, motivation and abilities, a manager's
      dissatisfaction, a coach's abilities, pair combinations and
      another club's friendship and rank. Still to load: the Squad
      page's age, salary, contract years, injury value, captain and
      keyman experience and the two policy points, and the Edit player
      page
      ([`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md#steps),
      [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#fields-found-so-far))
- [ ] The manager's Special Mention texts for dissatisfaction kinds 0–3,
      a save edit per kind
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#still-unknown))
- [ ] *Short.* `pmplayer.py check` on a career saved after importing the
      edited V. Drake with `--mod vpf-styles` (`LMAST-vpftest.ps2`)
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#tested))

## The LMASTER Mod

What these prove: each switch does in the game what
[`LMASTER_MOD.md`](DOC/LMASTER_MOD.md) says it does, and every
edition plays through a season.

### Economy and balance

- [ ] The rest of the `--mod balance` switches, `injury-lines`,
      `injury-value` and `pr-cycle`, on a `--mod lmaster-max` disc: each
      row marked "not checked in the game" in
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements) (the injury
      lines and odds, overseas bases, a fee above £120M, `fanbase`'s
      crowds, TV offers and big-fanbase merchandise, the camp and tour
      costs; `fee-tiers`' low end, `pr-costs`, lower merchandise income
      and `slow-reputation` after a win are seen, but not its year-end
      and final-place halves). The current test disc is
      `LMAST-test-season4.iso` with its sheet
      `names/test-sheet-season.md`
- [ ] *Short.* `--mod league-balance` seen further than the first 16
      games: a season of an English second-division club's home and away
      runs on the Schedule screen, and another rebuilt league (a
      22-club one, or VS); only the first 16 games in a new England
      career are seen
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))

### Fixes and stadiums

- [ ] *Short.* `--mod press-tendency` by eye: a club of high-press
      players closes down harder than without it (the patch is checked
      in memory) ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] `--mod salesman-items` in a career from season 8, where the
      special training coach visits: hire him, check that his "worked
      wonders" follow-up comes and the "has waned" message 8 turns
      after it, and over PINE that flag 336 is set and the match's copy
      of your squad has abilities 59–63 raised (the saved players don't
      change); the headphones and spikes the same way
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [ ] The Special stadium late in a career: a 100,000 ground (`--mod
      special-stadium`) that fills when sold out
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#stadiums))

### The third tier

- [ ] The third tier's lower cups on `LMAST-test-max-germany.iso` (its
      transfer windows, season's end, saving and loading are tested,
      [`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md#--mod-third-tier-the-lists-phase-2b)):
      the German Club Cup's seeded bracket (one first-round tie on Dec
      w1 midweek, the other 7 clubs from the second round) played to
      its final, another nation's lower cup the same way, and the round
      names on the end of tournament screen
      ([`UID_LIMITS.md`](DOC/UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3))
- [ ] Relegation on a `--mod third-tier` disc decided by this season's
      rank alone: at a season's end, the warning before it and the drop
      both follow the final table, not last season's
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [ ] The third tier's text in a language other than English (the
      English is tested): the advisor's intro, the Game Over help, the
      2nd German League's rules screen and its season-start news
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-text))

### The Japanese release

- [ ] A Japanese disc with `--mod third-tier`, played to a season's end.
      Already seen (Nexxus's report, 2026-11-12): it boots, starts a
      career and reaches the tutorial's playoffs with the same teams as
      on the PAL release, the German 2nd division starts with 18 clubs without
      Siegen or Offenbach (a screenshot), and a save loads. Still to
      check: build it with `python SRC/patch_disc.py patch "<the
      Japanese image>" out.iso --mod third-tier --copies --dat DAT_JP`,
      start a new career (its saves go to `BISLPM-66316-F`), and see
      that a season's end moves one club each way as on the PAL release,
      and that the third tier itself stays hidden
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#the-third-tier-on-the-japanese-disc))
- [ ] *Short.* A Japanese disc with `--mod real-names`: build it with
      `python SRC/patch_disc.py patch "<the Japanese image>" out.iso
      --mod real-names --copies --dat DAT_JP`, start a career, and look
      at the club names in the league table, the schedule and the
      player's own club field (the longest, 18 letters), a stadium name
      and the competitions' names: Latin letters should show and fit,
      with no garbling or cut-off text
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))

### Newer switches

Each of these switches has been built and is waiting for someone to play it.

- [ ] The modern font and the title banner on a full or max disc
      (`python SRC/patch_disc.py patch "<the PAL image>" out.iso --mod
      lmaster-max --font "RobotoCondensed[wght].ttf" --version 0.5.0
      --copies --dat DAT`): look through the screens for text that is
      cut off, overlaps or sits badly, mainly the longest club, player and
      stadium names in the lists and tables, the news pages, the match
      screens (scoreboard, substitutions, results), the Text-heavy
      messages, and the pad buttons and euro sign; switch the language to
      French, German, Spanish or Italian once and see that the title
      banner is there too (Nexxus saw the font on the pre-match and
      Select Hometown screens and the banner on a lite disc, 2026-11-13;
      the first disc's font had stray pixels beside letters, reported
      2026-11-14; fixed in `fontmod.py` the same day, and Nexxus saw them
      gone on the rebuilt disc, so a disc built now has the fix)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#modern-font),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#title-banner))
- [ ] Computer clubs' sponsors, suppliers and the unlicensed kits
      (`--mod random-sponsors`, the disc is `LMAST-test-sponsors4.iso`,
      built 2026-11-10; PCSX2 treats it as a new game, with its own
      settings and states). Real Betis shows the chest sponsor and the
      supplier logo, and England's national team shows its kit maker
      and no main sponsor (Nexxus's screenshots, 2026-11-10). Still to
      check: the other clubs of other leagues (each logo real, none
      blank, broken or oversized, two clubs differing, all seven
      suppliers' colours right); the Italian, Spanish and Dutch clubs
      (Milan, Barcelona, Ajax and some smaller ones), whose kit is now a
      generated one in the club's colours from `SRC/kits.csv`, so say
      which clubs look wrong (wrong colours, wrong pattern) and what
      they should be; and after a season that the sponsors changed
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#random-sponsors))
- [ ] The moving advert board at the last ground (`--mod moving-boards`,
      the disc is `LMAST-test-boards.iso`, built 2026-11-10): in a
      career with the moving board bought and a level-4 stadium, check
      that the rotating electric boards show at home games, then buy the
      LCD board and check that it replaces them; also look at a computer
      club's level-4 ground (the plain boards, not LCD). The board
      shop may also stop you buying the moving board at level 4; say
      what it does
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status),
      [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#the-request-in-a-match))
- [ ] The youth academy's second comment on a candidate, rewritten as
      charisma by `--mod retail-text` (the disc is `LMAST-test-charisma.iso`,
      built 2026-11-10): open a youth candidate's page and check that
      the line under the summary reads "almost no charisma" up to
      "superb charisma", with no cut-off or stray spaces, and say which
      screen it was (the switch patches both preloaded copies, so
      this also shows which copy the game reads); try another language
      if you can
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#retail-text-fixes))

## Test tools

Not a goal of their own: these help every other check
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#test-tools)).

- [ ] *Short.* The tutorial skip in France, Italy, Spain or the
      Netherlands (`--skip-nation`; England and Germany are played)
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs))
- [ ] *Short.* The launcher entries not yet tried: YAMAZAKI TEST, Talk
      and BG LIGHT TEST
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-developer-launcher))
