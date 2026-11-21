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
      costs; `transfer-fees`' fee tiers at the low end, `pr-costs`, lower merchandise income
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
- [ ] A Japanese disc with `--mod club-kits,club-eras` (ported 2026-11-21,
      built and read back byte for byte, not seen in the game): build it with
      `python SRC/patch_disc.py patch "<the Japanese image>" out.iso --mod
      club-kits,club-eras --eras-offset 3 --dat DAT_JP`, start a career, see
      that a computer club's manager differs from the retail one (a new
      name and tactics in its squad screen or the match, as on PAL), and in a match look at a
      computer club's kit: a sponsor and a supplier logo on the shirt (as on
      PAL), a new kit from era 1 on (build with `--eras-offset 3` to start
      there, or wait for a new season), and a club-creation preset's
      number showing on the front. Report what shows; a blank
      sponsor would mean the Japanese sponsor textures are numbered
      differently ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#club-kits),
      [`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))
- [ ] *Short.* A Japanese disc with `--mod title-banner` (ported
      2026-11-21; the pack read back from a built disc equals the generated
      one, not seen in the game): build it with `python SRC/patch_disc.py
      patch "<the Japanese image>" out.iso --mod title-banner --font
      "RobotoCondensed[wght].ttf" --version 0.6.0 --dat DAT_JP`, start the
      game and look at the title screen: "LMASTER MOD" over "v0.6.0 CUSTOM"
      in a navy and gold box in the sky at the top left, readable, with the
      logo, the menu and the stadium as before. Say whether the box moves or
      flashes with the opening zoom (the scene draws the photograph at other
      scales then) and whether its colours look right
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#title-banner))
- [ ] *Short.* A Japanese disc with `--mod realism` (ported 2026-11-21; 12
      files read back equal to `texmap.py apply`'s, not seen in the game):
      build it with `python SRC/patch_disc.py patch "<the Japanese image>"
      out.iso --mod realism --copies --dat DAT_JP` (LMAST-Realism cloned
      beside the repository), start a career, and look at the club crests
      (the club ranking, the squad screen), the match pictures and a
      stadium's facilities screen: they should be Realism's, with no
      half-transparent logos or garbling
      ([`TEXMAP.md`](DOC/TEXMAP.md#the-japanese-release))
- [ ] *Short.* A Japanese disc with `--mod real-names`: build it with
      `python SRC/patch_disc.py patch "<the Japanese image>" out.iso
      --mod real-names --copies --dat DAT_JP`, start a career, and look
      at the club names in the league table, the schedule and the
      player's own club field (the longest, 18 letters), a stadium name
      and the competitions' names: Latin letters should show and fit,
      with no garbling or cut-off text
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))

### The third tier's rules text in Japanese (in need of a checker)

Nexxus's choice, 2026-11-19: the third tier's rules text on the
Japanese disc is written in Japanese. Claude wrote it below from the
Japanese retail wording of the same messages, in the game's own style
(full-width kana and kanji for sentences, half-width kana for division
names, as the retail text has them), and **it is in need of a checker**:
nobody on the project reads Japanese (Nexxus, 2026-11-21), so the
grammar, the tone and the fit with the neighbouring retail text are
unchecked. Since 2026-11-21 `patch_disc.py --mod third-tier` writes it
into slot 0 of a Japanese disc (`tier_text_edits_jp`, with a note saying
it needs a checker; a disc built with it, read back, holds every line
below and fits its slots). The check for a person who reads Japanese:
read each line for grammar, tone and fit, and say what to change; the
corrections go into the `TT_JP_*` strings of `SRC/patch_disc.py` (someone
else makes the edit), and the line moves from here to "checked" in
[`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#the-third-tier-on-the-japanese-disc).
With `--mod real-names` the tier names in the lists become English ASCII
(`League One`), while the sentences below keep the retail katakana names,
as every other retail Japanese message that mentions a name does.

Each nation's messages, England to the Netherlands, in the order of the
PAL edits (`SRC/patch_disc.py`, `tier_text_edits`). `{lf}` and the other
tags stay as the retail text has them; `\n` is a line break.

**Division sizes and the closing line, 487:1100 to 1105** (the advisor's
introduction to each nation's second division). Change the club count
and the match count, and add a last line to every message:

| Id | Nation | Retail | New |
|---|---|---|---|
| 487:1100 | England | 全26チーム, 年間50試合 | 全24チーム, 年間46試合 |
| 487:1101 | France | 全22チーム, 年間42試合 | 全20チーム, 年間38試合 |
| 487:1102 | Germany | 全20チーム, 年間38試合 | 全18チーム, 年間34試合 |
| 487:1103 | Italy | 全24チーム, 年間46試合 | 全22チーム, 年間42試合 |
| 487:1104 | Spain | 全24チーム, 年間46試合 | 全22チーム, 年間42試合 |
| 487:1105 | Netherlands | 全22チーム, 年間42試合 | 全20チーム, 年間38試合 |

New last line of each (after a `\n{lf}`):

```text
最下位になるとゲームオーバーです。
```

**Game Over conditions, 487:1200 to 1205.** Point 2 (the retail
"two years in a row at or below place N") is replaced, from `２.` up to
`３.`, so that finishing last in one season ends the game. The division
names are the retail ones:

| Id | New point 2 |
|---|---|
| 487:1200 | `{lf}　２.　シーズン終了時にﾁｬﾝﾋﾟｵﾝｽﾞﾃﾞｨﾋﾞｼﾞｮﾝで最下位{lf}　　　 （24位）の場合。` |
| 487:1201 | `{lf}　２.　シーズン終了時にﾌﾗﾝｽﾘｰｸﾞ・ﾃﾞｨﾋﾞｼﾞｮﾝ2で最下位{lf}　　　 （20位）の場合。` |
| 487:1202 | `{lf}　２.　シーズン終了時にﾄﾞｲﾂ2部ﾘｰｸﾞで最下位{lf}　　　 （18位）の場合。` |
| 487:1203 | `{lf}　２.　シーズン終了時にｲﾀﾘｱﾘｰｸﾞBで最下位{lf}　　　 （22位）の場合。` |
| 487:1204 | `{lf}　２.　シーズン終了時にｽﾍﾟｲﾝﾘｰｸﾞ・ﾃﾞｨﾋﾞｼﾞｮﾝ2で最下位{lf}　　　 （22位）の場合。` |

The division names in 487:1201 and 1204 use the full-width middle dot `・`
as those messages' retail point 2 does (the tier names in 11:1142 to
1147 use the half-width `･`).

**The game over message, 487:902** (the owner's farewell; the retail first
sentence, "for two years in a row the results were poor", no longer fits
a game that ends after one season). Its first sentence is replaced:

```text
2年連続で成績がふるいませませんでした…  ->  今季は最下位に終わってしまいました…
```

(the retail sentence has a typo, `ふるいませませんでした`, which the new one
removes).
| 487:1205 | `{lf}　２.　シーズン終了時にｵﾗﾝﾀﾞ2部ﾘｰｸﾞで最下位{lf}　　　 （20位）の場合。` |

**League rules screen, 30001** (ids 101, 107, 112, 117, 123, 128). A
relegation section is added after the promotion section. The tier's
name is the retail one of 11:1142 to 1147 without ` ﾌﾟﾚｲｵﾌ`:
ｲﾝｸﾞﾗﾝﾄﾞﾘｰｸﾞ･ﾃﾞｨﾋﾞｼﾞｮﾝ3, ﾌﾗﾝｽﾘｰｸﾞ･ﾃﾞｨﾋﾞｼﾞｮﾝ3, ﾄﾞｲﾂ3部ﾘｰｸﾞ,
ｲﾀﾘｱﾘｰｸﾞC, ｽﾍﾟｲﾝﾘｰｸﾞ･ﾃﾞｨﾋﾞｼﾞｮﾝ3 and ｵﾗﾝﾀﾞ3部ﾘｰｸﾞ.

```text
\n{lf}\n{lf}{color:4}降格条件{/color}\n{lf}最下位のクラブは<the tier's name>に降格
```

**Season-start news, 832** (ids 433, 436, 442, 438, 440, 445). A
sentence is added at the end of each news text:

```text
最下位のクラブは<the tier's name>に降格となる。
```

**Game Over screen, 30003:1, point 2** (the screen that lists the
conditions, from `２.` up to `３.`):

```text
{lf}　２.　シーズン終了時に{var:1:2031}で最下位{lf}　　　 の場合。
```

**The advisor's warning, 35680:0** (from `勝ち点から見て` to the end of
the message; the first line, `さん、警告です。`, stays):

```text
勝ち点から見て{var:1:2031}で最下位に\n{lf}なってしまう危険性がございます。今季\n{lf}最下位だとゲームオーバーとなるのでご注意ください。
```

**The Game Over message, 487:902** (its first sentence, which retail
spells with a typo, `ふるいませませんでした`, is replaced):

```text
今季はリーグ最下位に終わってしまいました…
```

Things the reader should look at: whether `降格` (relegated) and
`最下位` (last place) are the words the game's own text uses; whether
the lines are short enough for the message boxes (the longest is the
warning's second line); and
whether the tier's name should be the retail one with `ﾌﾟﾚｲｵﾌ` removed
or something else. Put the result into
[`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#the-third-tier-on-the-japanese-disc)

### Newer switches

Each of these switches has been built and is waiting for someone to play it.

**Reading a state.** Several checks below ask for a save state taken in a
match against a computer club. `python SRC/p2state.py kits <state.p2s>
--offset 2` reads the state's memory (the file is a zip; 7-Zip is the
fallback for the newer compression), finds the match's two clubs, and
prints each club's sponsor, supplier and both kits as the game holds
them, a `!!` marking a club whose bytes differ from what the build's plan
gives. `python SRC/p2state.py managers <state.p2s> --offset 2` does the
same for the manager. The `--offset` is the `--eras-offset` the disc was
built with (the test discs use 2); the build's switches and tables are
read from the code in memory, so a disc built with another seed still
checks. `python SRC/p2state.py info <state.p2s>` says whether a match is
loaded. To take a state: play into a match against a computer club,
save a state in PCSX2 and send the file (or say its slot), with the
club's name. Your own club and the rival are skipped. The current test
discs are `LMAST-test-3b.iso` (offset 3) and `LMAST-test-0.iso` (no offset), built with
`python SRC/patch_disc.py patch "<retail disc>.iso" <name>.iso --mod lmaster-max
--copies --dat DAT --realism ../LMAST-Realism --test-build [--eras-offset 3]`,
never with `--skip-tutorial`, which skips the opening playoffs
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#test-tools)).

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
      (the sponsors part of `--mod club-kits`, the disc is `LMAST-test-sponsors4.iso`,
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
- [ ] A whole LMASTER max disc, with every group together (the third tier,
      real names, graphics, Club eras, the economy and balance groups, the
      Realism pack), built 2026-11-19 as `LMAST-test-max.iso` (which froze
      on the Edit Emblem screen after the kits were edited in club creation:
      Nexxus's report; that freeze came from `--skip-tutorial`, which leaves
      the heap too fragmented for the emblem editor, and not from any
      switch: a max disc built without it, `LMAST-test-bis-g.iso`, did not
      freeze, see [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#test-tools). The
      logo gate and the sponsors' code also leave your club, the rival and
      the VS teams to the game, see
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#random-sponsors)) with
      `--mod lmaster-max --copies --dat DAT --realism ../LMAST-Realism
      --test-build --eras-offset 2` (no `skip-tutorial`: it skips the opening
      playoffs, which test builds always keep; pick Germany yourself; the title
      banner reads TEST BUILD; the offset puts two thirds of the clubs in
      era 1 from 2006-07). Never run as one disc: the code segment grew to
      0x1400 bytes and holds the third tier, the sponsors, the logo gate
      and the managers' code together (no overlap; the segment now sits at
      `0xe0000` and is `0xc000` bytes, since 2026-11-19). Check: it boots and the
      banner reads TEST BUILD; a career starts in Germany; a season plays
      to its end with no freeze, saving and loading once; the third tier
      (England's at the foot of the second division) and the real names
      show; kits carry a sponsor and a supplier logo, none blank, and the
      grounds' advert boards vary; and a computer club's manager is the
      plan's (`cluberas.py expect DAT <team> <season> 2`, read at
      `0xf8500` (`0xe0500` since the move on 2026-11-19) after a match
      loads). Edit Emblem after a kit edit can freeze
      on any skip-tutorial disc (see above), so test it on a disc built
      without `skip-tutorial`; and see that your
      club's and the rival's sponsors are the game's own (the sponsor
      screen, and the rival's kit in a match)

- [ ] Club eras (`--mod club-eras`; PCSX2 treats each disc as a new game).
      Seen working (Nexxus's save states, 2026-11-19, `LMAST-test-eras-s0.iso`,
      built with `--mod club-eras,skip-tutorial --eras-offset 2`, read by
      Claude): a match against a club in era 1 had the new manager, his
      formations and his tactics ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#club-eras)).
      The disc rebuilt after the LMASTER seed
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-lmaster-seed),
      `LMAST-test-eras-seed.iso`) passes the same check (states 1 and 2,
      2026-11-19). Done on a release build (`LMAST-test-0.iso`, no offset;
      Nexxus's state in the opening playoffs, 2026-11-19): a group-0 club
      keeps its retail manager and nothing changes in the playoffs
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#club-eras)). Still to check on
      that disc: (3) a whole season plays normally, with no freeze at a
      match or a screen; (4) the first changes come in seasons 1, 2 and 3 (a
      third of the clubs each, the clubs whose team id leaves 2 first), then
      every three seasons. A club's manager is shown nowhere, so it is a
      state: read the team ids in a match with `python SRC/p2state.py
      managers <state.p2s>`
- [ ] Computer clubs' kits by era (the kit eras part of `--mod club-kits`,
      the disc is `LMAST-test-3b.iso`; PCSX2 treats it as a new game). **Started:** a state of
      Nexxus's in a match against Hansa Rostock (team 119, era 1) holds
      the plan's bytes exactly, see
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-eras). Done (Nexxus's
      reports, 2026-11-19): the kits look right, and third-tier clubs in
      era 1 match the plan. Still open are an era 0 club as the control, a
      third-tier club past era 1, and the later seasons. Build with
      `python SRC/patch_disc.py patch "<retail disc>.iso"
      LMAST-test-3b.iso --mod lmaster-max --copies --dat DAT --realism
      ../LMAST-Realism --test-build --eras-offset 3`, without
      `--skip-tutorial` (it makes the Edit Emblem screen freeze, see the
      check above), and start a career in any nation. The era is
      (season + offset + team id mod 3) div 3, so with the offset 2 in
      season 0 the clubs whose team id leaves 1 or 2 when divided by 3 are
      in era 1 and those that leave 0 are in era 0. Check: (1) a club in
      era 1 shows a supplier's shirt and shorts design in a match, with its home
      colours (shirt colours 1 and 2) as before, and the supplier logo on
      the shirt is the supplier whose design it wears; (2) its away kit
      has new colours that do not clash with the home kit (the away kit
      is worn when the two clubs' home colours clash); (3) your club, the
      rival and the national teams are untouched; (4) a club in era 0
      still has its retail kit; (5) after the season rolls on (season 1)
      the other clubs' kits change too, and the first group's again after
      the next era. Any match against a computer club will do: save a state
      in it, read the two team ids as above, and compare the kit bytes with
      `python SRC/kiteras.py show DAT <team>`. Put the result into
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-eras)
- [ ] Main sponsors by tier (`--mod club-kits`, which holds the sponsor
      tiers; the disc is `LMAST-test-3b.iso`). Done in VS and match states
      (Nexxus's, 2026-11-19, read with `python SRC/p2state.py kits <state.p2s>
      --offset 3`): the sponsors fall with the tier and each shirt shows the
      logo of its sponsor's name (see
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#sponsor-tiers)). Still open, in a
      career: a club's sponsor changes from season to season but stays in
      its slice, and a top club of a big league shows a big-name sponsor
- [ ] Transfer fees on a max disc after the cut to the lower tiers (the fee
      tiers part of `--mod transfer-fees`, 2026-11-19): in the Post Player list the estimate for a
      player of rank 0 to 5 should be the retail game's, and for rank 6 to
      11 1.5 times it, half of what the same players showed before
      (the 18-year-old rank 10 at €12.3M should show about €6.2M, the
      33-year-old rank 8 at €4.8M about €2.4M, in the same career and
      week). Ranks 12 to 15 are as before. Needs a disc built with
      `--mod transfer-fees` or `lmaster-max`
      ([`ECONOMY.md`](DOC/ECONOMY.md#transfer-fees))
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

## The end point

What these prove: the runtime memory map
([`RAM_MAP.md`](DOC/RAM_MAP.md)) matches the running game. Its rows come
from reading the code. Thirty-seven save states are already read (five career
menus, ten from the init screen to a quick-mode match, eight of one
career match and eleven of a VS match played into extra time), and the
roots, the module table, the demo flag, the match object and the goal
tally held ([`RAM_MAP.md`](DOC/RAM_MAP.md#tested-in-pcsx2)). Each doc
says where a check is still owed.

- [ ] A save state for what no state has shown yet: the second half of
      extra time. A VS match, added time, extra time, a shoot-out, both
      full-time screens and the half-time tactics screen are already
      read. Run
      `python SRC/ramcheck.py check <eeMemory.bin>` on a state's memory
      dump, or `check pine` with the game running (PINE on, one
      client at a time, which also tests the addresses live), and report
      the `!!` lines
      ([`RAM_MAP.md`](DOC/RAM_MAP.md#for-achievement-authors))

## Test tools

Not a goal of their own: these help every other check
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#test-tools)).

- [ ] *Short.* The tutorial skip in France, Italy, Spain or the
      Netherlands (`--skip-nation`; England and Germany are played)
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs))
- [ ] *Short.* The launcher entries not yet tried: YAMAZAKI TEST, Talk
      and BG LIGHT TEST
      ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#the-developer-launcher))
