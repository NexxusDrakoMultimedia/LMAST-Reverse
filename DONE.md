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
- [x] Build manifests: `manifest.py` records a build's edition,
      switches, options, seed and tools commit, shows it in plain words,
      diffs two builds and prints the options that rebuild one; Build
      disc writes one beside its output
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#build-manifests))
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
- [x] `--mod kit-eras` (PAL only, full and max, built on
      `random-sponsors`): computer clubs change kit supplier, shirt and
      shorts design and away kit with each club era, using the designs
      the kit editor offers for the supplier and keeping the home
      colours. The group `eras` ("Club eras") now holds `club-eras`,
      `random-sponsors` and `kit-eras`, and `graphics` holds `realism`
      and `modern-font`
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-eras),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#the-kit-editors-designs-per-supplier))
- [x] `--mod kit-standards` (PAL only, group `eras`, needs `kit-eras`;
      Nexxus's idea and rules, 2026-11-19): every computer club's kits, in
      every era, get a front number, a shorts number, emblems on the shirt
      and shorts, number colours that show on the colours they sit on
      (they also colour the supplier logo) and a captain's band to match.
      From era 1 the collar, number design and emblem pair are rolled
      again for each variant, the away kit matching the home kit's value
      most of the time. Built on the kit editor's items, read from
      `SIMPRG.REL`
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-standards),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#the-kit-editors-items-and-their-bytes))
- [x] The kit standard sets every club's supplier in every era, from its
      tier (Nexxus's idea, 2026-11-19), so the logo and the look agree in
      era 0 too; the away colours 2 and 3 draw their free choices only from
      the club's hues and the greys, and `patch_disc.py` notes that the
      Edit Emblem screen can freeze on a `--skip-tutorial` disc
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-standards),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#test-tools))
- [x] `--mod tier3-eras` (group `eras`, needs `club-eras`, `kit-eras` and
      `third-tier`; Nexxus's idea, 2026-11-19): the club eras and kit eras
      also take the third tier's clubs (teams 442 to 459), 457 clubs
      instead of 439, with a bigger manager pool
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#tier-3-eras))
- [x] The mod's code segment moved down in memory, from `0xf8000` to
      `0xe0000`, and grew to `0xbd00` bytes to hold the kit tables, then to
      `0xc000` for the sponsor tiers' routine and tables (the memory from
      `0x94000` to `0x100000` is unused in every state read).
      Every address in the docs is relative to the segment
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-standards))
- [x] `--mod sponsor-tiers` (PAL only, group `eras`, needs
      `random-sponsors`; Nexxus's idea, 2026-11-19): a computer club's main
      sponsor is drawn from its tier's slice of the 199 main sponsors,
      sorted by fee, instead of from all of them, so the better clubs get
      the bigger sponsors; the per-season draw stays. `sponsortiers.py`
      plans it and `patch_disc.py` builds it
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#sponsor-tiers),
      [`ECONOMY.md`](DOC/ECONOMY.md#sponsors))
- [x] Keeper kits in the kit standard (Nexxus's idea, 2026-11-19): the 114
      clubs `random-sponsors` turns from licensed into generated get real
      keeper kits, made the way the game makes them for the VS teams, and
      every computer club's keeper kit gets number colours and a captain's
      band by the standard's rule. `uniform.py keepers` shows them
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-standards),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#uniform_gktbb-keeper-kits-made-from-the-outfield-kit))
- [x] The club-creation presets follow the kit standard (Nexxus's idea,
      2026-11-19): the 32 presets of `CEDITPRG.REL` start with the front
      number, the shorts number and the emblems on, with number colours and
      a captain's band by the standard's rule; the rival's kit is left as
      it is. `clubpresets.py` plans the byte patches and
      `patch_disc.py` applies them with `kit-standards`
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#kit-standards),
      [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md#the-kit-editors-items-and-their-bytes))
- [x] `p2state.py`, the state checker: reads a PCSX2 save state, finds the
      two clubs of a match and compares each club's kit and the managers'
      result word with the plans of `kiteras.py` and `cluberas.py`, reading
      the build's offset and switches from the code in memory
      ([`TESTING.md`](TESTING.md#newer-switches),
      [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#test-tools))
- [x] The Japanese disc: every switch but `realism`, `third-tier`'s code,
      save and data ported (its rules text is not)
      ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))
- [x] The switch names rationalised (Nexxus's choice, 2026-11-19): switches
      that needed each other are one switch. `club-kits` is the old
      `random-sponsors`, `kit-eras`, `kit-standards` and `sponsor-tiers`;
      `transfer-fees` holds `fee-tiers`; `tier3-eras` is no switch (the
      eras take the third tier's clubs when `third-tier`, `club-eras` and
      `club-kits` are on). Every old name is an alias of the merged switch.
      A `lmaster-max` build is byte for byte the disc the separate
      switches made, and max stays full plus the difficulty groups
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels))

- [x] `--mod title-banner` on the Japanese release (2026-11-21): the
      banner is drawn on the stadium photograph of its one title pack
      (`SC_TITLEBG.CSP`, entry 3) at the top left, after folding the
      photograph's 40 least-used palette colours into their neighbours to
      make room; `titlebanner.py info` checks the Japanese pack and
      `regress.py` runs it. A built disc's pack equals the generated one;
      its look in the game is in `TESTING.md`
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#title-banner))
- [x] `--mod realism` on the Japanese release, so LMASTER full and max
      build for it (2026-11-21): the pack's PCSX2 names match 1,605 of its
      1,613 PNGs against the Japanese textures, and `texmap.py apply` on
      `DAT_JP` writes 12 files (1,009 textures); the build reads the
      Japanese executable's licence table and refuses a PAL `DAT`. Two
      bugs of the Japanese full and max builds are fixed: the retail-text
      hook and its clash check no longer touch a Japanese `MES.PAC`. Built on the Japanese disc with `lmaster-max`, and the code
      segment and the 12 files read back byte for byte; its check in the
      game is in `TESTING.md`
      ([`TEXMAP.md`](DOC/TEXMAP.md#the-japanese-release),
      [`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))
- [x] `--mod club-eras` on the Japanese release (2026-11-21): the
      managers' code and tables, called from the same function as on PAL
      (`plOteam_GetManagerNoOffset`, its words equal but for two `jal`
      targets). `cluberas.py` runs over `DAT_JP` (`regress.py` has the
      Japanese runs), `gamever.py check` lists the hook and `plOteam_GetDb`.
      Built and read back byte for byte; its check in the game is in
      `TESTING.md`
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#club-eras))
- [x] `--mod club-kits` on the Japanese release (2026-11-21): the
      sponsors' code, the logo gate, the kit eras, the kit standard, the
      sponsor tiers and the club-creation presets, which were PAL only.
      The code builders take the build's addresses (`CaveBuild.addr`), the
      supplier tables and presets are found through `gamever.py`, and
      `regress.py` runs the three tools over `DAT_JP`. Built on the
      Japanese disc and read back byte for byte; its check in the game is
      in `TESTING.md`
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#club-kits),
      [`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc))

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
- [x] `ramcheck.py` checks that map against a running PCSX2 over PINE or
      a save state's memory dump, and writes its rows as
      RetroAchievements code notes
      ([`RAM_MAP.md`](DOC/RAM_MAP.md#for-achievement-authors))
- [x] Three `GAME/` leftovers settled: `TEAM.TMB` read (441 records of a
      name, a 3-letter code and 23 numbers, checked by the new `tmb.py`),
      `BACK_MATCH.TBB`'s six tables written out, and
      `TACTICS_PLAYBOOK_EDIT.TBB` shown to be one six-value cycle that the
      loader stores and no code seen reads. None of the three, nor
      `EFFECTS.DAT` and `TRAINING.DAT`, is named anywhere in the
      executable or the overlays
      ([`GAME_DIR.md`](DOC/GAME_DIR.md#files-nothing-is-known-to-read))
- [x] The stadium collision files read: the 27 `SHADOWCOLLI.PAC` and 38
      `WALLCOLLI.PAC` entries and `TEST3D/SHADOWCOLLI.LBI` are echidna
      link bundles of triangles (7,218 in all), checked by the new
      `lbi.py`. The SNR2 header's `0x20`, `0x24`, `0x30` and `0x38` fields
      are explained from the loader, and `AI_PARAM.BIN` is shown not to be
      a copy of the built-in tuning table (its source file is
      `fb_aiparams.cpp`)
      ([`LBI_FORMAT.md`](DOC/LBI_FORMAT.md),
      [`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md#header),
      [`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md#ai_parambin))
- [x] Link bundles and the cut-in blocks: the echidna link-bundle format
      is used only by `.lbi` data (no other file or BINPAC entry is one),
      the `ROUTEBOX` `RBD0` trailer is a big-endian u16 array with a
      header, the cut-in pack's `BMT1` blocks are splines of 0x40-byte
      points (checked by `packdata.py cutin`), and `CIB0` has a partly
      read header
      ([`GAME_DIR.md`](DOC/GAME_DIR.md#the-cut-in-packs-cib0-and-bmt1-blocks),
      [`LBI_FORMAT.md`](DOC/LBI_FORMAT.md#where-the-format-is-used))

## Tests in PCSX2

Confirmed in the game; each result is recorded in the doc linked.

- [x] The runtime memory map's roots, the heap table, the overlay
      registry and the career work buffer, read from five career save
      states, and then the module table, the demo flag, the match object
      (flags, team ids, competition, clock) and the engine pointer, read
      from ten save states from the init screen to a quick-mode match,
      and then the goal tally, the state word and the half-time and
      full-time hand-over of the score words, from eight states of one
      career match, and a VS match with a custom team played into extra
      time (state word, tally rows, added time, extra time, the end
      screens), a shoot-out in the same VS mode, and an injury-time goal in a
      second career match, and the half-time tactics screen
      (the score words are a snapshot written when it is set up)
      ([`RAM_MAP.md`](DOC/RAM_MAP.md#tested-in-pcsx2),
      [`RAM_MATCH.md`](DOC/RAM_MATCH.md#tested-in-pcsx2))

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
- [x] LMAST Realism's `Fixes`, `Adboards` and `Leagues` pictures on a
      `--mod realism` disc, the CSP ones included (Nexxus's report,
      2026-11-19)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#lmast-realism-on-the-disc))
- [x] The eras group in the game on `LMAST-test-3b.iso` (Nexxus's states,
      2026-11-19, read with `p2state.py`): third-tier clubs in era 1 with
      the plan's managers and kits, the sponsors falling with the club's
      tier, each shirt's logo being its sponsor number's, and (reports
      earlier the same day) the computer clubs' kits, the keeper kits and the
      club-creation presets
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#club-kits))
- [x] On a release build (`LMAST-test-0.iso`, no offset) a group-0 club
      keeps its retail manager and the opening playoffs are unchanged
      (Nexxus's state, 2026-11-19, read with `p2state.py`)
      ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#club-eras))
