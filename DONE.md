<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Done

What is finished, under the same headings as [`TODO.md`](TODO.md), which
lists what is left, plus "Tests in PCSX2" for results seen in the game.
Each entry is a short paragraph or a few lines linking the doc that
holds the details: the evidence, the counts and how it was tested.

## The starting season

You can change how a new game begins, and the game plays on from there.

- [x] Squads, clubs, the new club, free agents, regulations and results,
      each with a writer (`initteam.py`, `teaminit.py`, `plrsim.py`,
      `regulation.py`, `clubresult.py`) and an editor tab
      ([`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md),
      [`REGULATION_FORMAT.md`](DOC/REGULATION_FORMAT.md))
- [x] Where a division's clubs come from, and schedules for leagues of
      2–32 clubs and cups of 2–128 (`schedule.py`, `leaguesize.py build`);
      a league plays on the free turns, never the national-team dates
      (Nexxus's choice)
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md))
- [x] The national-team calendar and the club ranking: `natcal.py`,
      `clubrank.py` ([`README.md`](README.md#archives-and-tables))
- [x] The club and schedule limits the third tier needed
      ([`CLUB_LIMITS.md`](DOC/CLUB_LIMITS.md),
      [`UID_LIMITS.md`](DOC/UID_LIMITS.md))

## Data

You can edit players, staff, clubs, kits, crests and stadium looks.

- [x] Nearly every player and staff field named (the open ones are in
      `TODO.md`), with the match's readers of
      each, staff careers and policies, and kit style; `pbdata.py` and
      `plrcommon.py` (facilities) write them
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md))
- [x] Kits, crests, stadiums and the player editor's tables:
      `uniform.py`, `emblem.py`, `stadium.py`, with a tab each
      ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md),
      [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md#editing),
      [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md#editing))
- [x] Which copy of a file the game reads; `TACTICSPITCH.PAC` is loaded
      but never read, so the tactics pitch uses the `CSE/` originals
      ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md))

## Parameters

Any `PARAM/` table can be swapped, and the economy, training, injuries
and match tendencies are understood well enough to change.

- [x] Containers and scripts: `pac.py`, `tbb.py` and `sqb.py` write
      BINPACs, KC@P packs, PRS, tables and sequencer commands
      ([`PAC_FORMAT.md`](DOC/PAC_FORMAT.md),
      [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#editing))
- [x] The club game: the economy, injuries, training, camps and the money
      limits; `training.py`, `camp.py`, `formset.py`, `tour.py` and
      `clubevent.py` write the tables
      ([`ECONOMY.md`](DOC/ECONOMY.md),
      [`TRAINING_FORMAT.md`](DOC/TRAINING_FORMAT.md))
- [x] The match: the tendencies (the press team cap, carry and press, the
      thresholds), and the AI's plays, combinations, zone network and
      path kinds
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md#the-tendencies),
      [`BPB_FORMAT.md`](DOC/BPB_FORMAT.md))
- [x] The travelling salesman's items and their match boosts
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#the-salesmans-items))

## Text

You can change any message in any language.

- [x] Every message in every language: `mbb.py` and the Text tab
      ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md#writing))
- [x] Message variables, the event tables and procedures, the root scripts
      and which one starts which screen, and what each PwkScript computes
      ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md),
      [`GAME_FLOW.md`](DOC/GAME_FLOW.md),
      [`SEQ_DIR.md`](DOC/SEQ_DIR.md))

## Graphics and sound

Textures go to PNG, models to OBJ and glTF, sound to WAV and MIDI, and
LMAST Realism's pictures go on a disc.

- [x] The fonts: how the European and Japanese text is drawn, checked on
      both builds by `font.py`
      ([`FONT_FORMAT.md`](DOC/FONT_FORMAT.md))
- [x] Textures: `svr.py` rebuilds every texture file and writes a picture
      into a texture (seen in the game), and `texmap.py` maps LMAST Realism's pack onto the
      disc's textures
      ([`SVR_FORMAT.md`](DOC/SVR_FORMAT.md#writing),
      [`TEXMAP.md`](DOC/TEXMAP.md))
- [x] LMAST Realism on the disc: `texmap.py apply` writes the crests and
      match pictures, `csp.py` writes the CSP packs' `Fixes` and `Leagues`
      pictures, and `--mod realism` (group `graphics`, full and max)
      builds it, with the licensed Italian, Spanish and Dutch crests given
      Realism's transparent edge (`--licensed-border`) and a box in
      Build disc
      ([`TEXMAP.md`](DOC/TEXMAP.md#putting-the-pack-on-the-disc-apply),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#lmast-realism-on-the-disc))
- [x] Widescreen: a PCSX2 pnach for 16:9 with the 2D kept at 4:3, 3D kit
      models, match portraits and the opening newspaper pages included
      ([`WIDESCREEN.md`](DOC/WIDESCREEN.md))

## Playing a mod

You can turn edits into a bootable disc or an xdelta patch, and keep a
modded disc's saves apart.

- [x] `patch_disc.py`: files of any size, moved files, a grown disc, every
      copy updated, archives rebuilt, with `--skip-tutorial` and
      `--launcher` for testing
      ([`REBUILD.md`](DOC/REBUILD.md),
      [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs))
- [x] `vcdiff.py` makes xdelta patches (xdelta3's own included), and
      `cso.py` and `chd.py` read compressed images
      ([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod))
- [x] Saves decoded by running the game's own serializers, and written by
      `save.py set`, `pmplayer.py set` and `ps2mc.py`; Virtua Pro
      Football's edit players too
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md),
      [`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md))
- [x] Separate saves for a modded disc, on the Japanese disc too
      ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc))
- [x] `editor.py` (a tab for every writer, and File > Build disc) and
      `saveedit.py` (every page `save.py set` can write)
      ([`USAGE.md`](USAGE.md),
      [`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md))
- [x] The players' guide, [`INSTALL.md`](INSTALL.md)

## The LMASTER Mod

You can build the mod in three editions from named switches
([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)).

- [x] The switch levels: editions, groups and switches, in
      `patch_disc.py` and the Build disc window
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels))
- [x] LMASTER lite: the fixes for training camps, drill names, injuries,
      the main sponsor negotiation, season tickets, PR events, popularity,
      the rival's manager, the press tendency, the national cups, VPF play
      styles and positions (the latter Ohayoghurt's find) and the retail
      text
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status),
      [`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md))
- [x] LMASTER full: the third tier, balanced schedules, the cut injury
      lines, the salesman's items, real names, your own stadium, real
      grounds, sponsor boards and separate saves
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] LMASTER max: the harder economy and the balance switches
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements))
- [x] `--mod modern-font` (Roboto Condensed for the main text, PAL only),
      `--mod title-banner` (the mod's name on the title screen) and
      `--mod random-sponsors` (a sponsor and supplier on every kit)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#modern-font))
- [x] The Japanese disc: every switch but `realism`, `third-tier`'s code,
      save and data ported (its rules text is not)
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))

## The end point

Every folder of `DAT/` has a doc and a tool, and the game code is mapped.

- [x] `DATA.CVM` decrypted and the disc extracted, and the archives and
      tables parsed (BINPAC, KC@P, PRSH, `PackData`, `TBB1`/`TBL1`)
      ([`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md),
      [`PAC_FORMAT.md`](DOC/PAC_FORMAT.md))
- [x] Game code: about 12,600 symbols, the overlays and their loader, the
      developers' field table, C++ classes
      ([`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md))
- [x] Every `DAT/` folder has a doc and a tool, the Japanese release is
      extracted and read through `gamever.py`, and `regress.py` checks it
      all ([coverage table](GOALS.md#coverage-of-datacvm),
      [`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md),
      [`README.md`](README.md#how-the-tools-fit-together))
- [x] The runtime memory map for RetroAchievements sets: where the game
      keeps its data while it runs (EE RAM addresses, root pointers,
      overlay and heap placement, the mode, demo and launcher
      indicators, save and load behaviour, and the match, club, season
      and event data), read from the game code and checked twice
      ([`RAM_MAP.md`](DOC/RAM_MAP.md),
      [`RAM_MATCH.md`](DOC/RAM_MATCH.md),
      [`RAM_CAREER.md`](DOC/RAM_CAREER.md),
      [`RAM_SEASON.md`](DOC/RAM_SEASON.md))

## Tests in PCSX2

Confirmed in the game; each result is recorded in the doc linked.

- [x] Edits through the writers: the player database, squads and clubs,
      free agents, regulations, kits, training, facilities, messages, a
      starting crest, a PR event
      ([`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#tested-in-pcsx2))
- [x] England's first division at 22 clubs over two seasons
      ([`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from))
- [x] The disc rebuilds, saves edited and copied, cards written by
      `ps2mc.py`
      ([`REBUILD.md`](DOC/REBUILD.md))
- [x] The tactics pitch reads `CSE/`, not `TACTICSPITCH.PAC`
      ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md#tacticspitchpac-is-loaded-but-not-used))
- [x] By ear: the music, opening, crowd, chants and effects banks
      ([`AUDIO_DIR.md`](DOC/AUDIO_DIR.md))
- [x] Virtua Pro Football loads an edited `pmplayer.bin`; `--mod
      vpf-positions` no longer lights the goalkeeper box for an imported
      forward
      ([`PMPLAYER_FORMAT.md`](DOC/PMPLAYER_FORMAT.md#editing))
- [x] The LMASTER switches marked tested, each on its test disc,
      including the third tier over a German season, the real names, the
      2005-06 grounds and a season on LMASTER max
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
- [x] A Japanese disc built with `--mod third-tier` boots, starts a
      career, saves and loads
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#the-third-tier-on-the-japanese-disc))
- [x] LMAST Realism's pictures on a `--mod realism` disc, mini logos
      included, and `svr.py`'s textures in the crest, badge and sponsor
      packs
      ([`TEXMAP.md`](DOC/TEXMAP.md#putting-the-pack-on-the-disc-apply))
- [x] Widescreen newspaper pages; `modern-font`, `title-banner` and
      `random-sponsors` on the screens and clubs checked so far
      ([`WIDESCREEN.md`](DOC/WIDESCREEN.md#newspaper-pages),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#status))
