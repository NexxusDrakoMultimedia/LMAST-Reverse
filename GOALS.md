<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Goals

This project wants the data in *Let's Make a Soccer Team!*
(`SLES_541.51`) to be easy to change, so that anyone can build a modded
version of the game: a different starting season, real names, a harder
economy, fixed bugs. The end product is a set of GUI tools that change
the game's data without anyone needing to know the file formats, and
patches that players apply to their own disc.

This file says what the project is for and how far it has got.
[`TODO.md`](TODO.md) turns each goal below into tasks, in the same
order, and [`DONE.md`](DONE.md) lists what is finished.

## What a mod should be able to change

These eight goals are the project's one list. Each has a short "done
when". The tasks that remain for each are in [`TODO.md`](TODO.md), under
a heading of the same name.

1. **The starting season.** The state a new game begins in: schedules,
   competitions, league membership, clubs, squads and players. The game
   then plays on from there as normal. *Done when* every change the
   editor offers here (a club moved, a division resized, a calendar
   shifted) has been played through a season or more in the game.
2. **Data.** Club, player, stadium and staff records, kits and crests,
   and the text that goes with them. *Done when* every field of those
   records has a name and a known range and is editable in a tab, or is
   shown to have no effect.
3. **Parameters.** The tuning values in the `TBB1`/`TBL1` tables and the
   executable: prices, growth rates, event odds, match settings and so
   on. *Done when* every table and constant has named fields, a writer
   and, where a mod would touch it, a switch or a tab.
4. **Text.** Message text in every language slot, including event
   dialogue, news and mail. *Done when* every message category is
   traced to the screen that shows it, and any message can be changed
   in the Text tab.
5. **Graphics and sound.** Extracting textures, models and sound comes
   first; editing them comes after the data above. The one exception is
   bringing Nexxus's LMAST Realism texture pack onto the disc
   ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#lmast-realism-on-the-disc)).
   *Done when* every texture file can be written back and the pack's
   chosen folders are seen on a disc in the game.
6. **Playing a mod.** A player turns edits into a disc or an xdelta
   patch, applies it to their own disc, and keeps its saves apart, on
   the PAL release and on the Japanese one. *Done when* the image
   formats players keep are covered and a career can be played, saved,
   edited and carried to a modded disc on both releases.
7. **The LMASTER Mod.** The project's own mod, in three editions (lite,
   full and max): fixes for what the release cut or broke, real names,
   a third tier and a harder economy. *Done when* every candidate is
   built and tested in the game or set aside, and every switch works on
   the Japanese release (the firm requirement for LMASTER 1.0.0, Nexxus's
   choice, 2026-11-01; the modern font may stay PAL only).
   See [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md).
8. **The end point.** The reverse engineering is complete
   ([below](#when-the-reverse-engineering-is-complete)). *Done when*
   every file, every line of code and every mechanic is documented on
   both releases and the editors work on the Japanese release as on
   PAL.

## The path there

Each stage builds on the one before it, for each goal above. The status
below is a summary: [`TODO.md`](TODO.md) tags every task with the stage
it belongs to, and [`DONE.md`](DONE.md) lists what is finished.

0. **Decrypt.** *Done.* `DATA.CVM`'s encrypted table of contents is
   decrypted with a key derived from its header, and `DATA.ISO` extracts
   to `DAT/` ([`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md)).
1. **Read.** Document every file format and every folder in `DATA.CVM`
   in `DOC/`, and parse each format in `SRC/`, checked against every
   file on the disc. *Nearly done:* every folder has a doc, and the few
   files still unparsed are in the [coverage table](#coverage-of-datacvm)
   below.
2. **Understand.** Know what each field *means* in the game, not just
   its type and offset. A field can't be offered for editing until it
   has a name and a known range; fields still unknown stay read-only.
   *Most of the work now:* the player database, the starting season, the
   parameter tables, the economy and saves are named field by field. The
   match AI's files and each doc's "Still unknown" list are open.
3. **Write.** A writer for each format, which must round-trip: reading a
   file and writing it back gives the original bytes, checked over every
   file on the disc in `regress.py`. *Done for what a starting-season
   mod changes*, and edits through most writers are tested in PCSX2.
   Left: the rest of the stadium tables, the writers for the ACROBATA
   and `PackData` texture packs, and a changed-size texture in a CSP
   pack (`csp.py` rebuilds all the CSP packs and replaces same-size
   textures).
4. **Rebuild.** Put edited files back on a disc image that boots.
   *Done:* `patch_disc.py` patches files of any size, moves them, grows
   the disc, updates every copy and rebuilds archives, all tested in
   PCSX2 ([`REBUILD.md`](DOC/REBUILD.md)).
5. **Edit.** GUI tools on top of the writers, organised by what a player
   of the game would recognise (a club, a player, a season) rather than
   by file, which check values against the documented ranges and
   cross-references. *Mostly done:* `editor.py` has a tab for every
   writer of game data except `schedule.py`'s and `sqb.py setcmd` (they
   edit commands, not values), and builds a disc or a patch;
   `saveedit.py` edits a career save. A tab for each writer still to
   come (the Data goal in `TODO.md`) is left, and so are the Candidates
   page of the save editor and both editors on the Japanese release.
6. **Distribute.** Share mods as xdelta patches (VCDIFF, RFC 3284)
   against the player's own unmodified disc image, never as game data or
   disc images, so no game data leaves the user's machine. Players
   apply them with tools they already have, such as Delta Patcher.
   *Done:* `vcdiff.py` makes and applies them (patches xdelta3 made
   too), the tools read CSO, ZSO and CHD images directly, a modded disc
   can keep its own saves, and [`INSTALL.md`](INSTALL.md) is the
   players' guide.

Alongside the stages, the [LMASTER Mod](DOC/LMASTER_MOD.md) is where
most new findings get used first: goal 7 above.

## Coverage of `DATA.CVM`

The goal is that every folder in `DAT/` has a doc saying what it holds
and which scenes or systems load it, and every file type in it has a
format doc and a tool whose `info` passes over all of `DAT/`. Nothing is
left as "unknown binary". Even a format nobody plans to edit is
documented, because an unexplained file can hide a dependency that
breaks a rebuilt disc.

Where each folder stands (2026-11-13). The status is one of:

- **done**: every file type parses and is checked over all of `DAT/`.
  What is left is the meaning of some fields.
- **most files**: one or two file types aren't parsed yet.
- **partly**: several file types aren't parsed yet.

The "Still open" column is a summary. Each doc's "Still unknown" section
has the full list, and [`TODO.md`](TODO.md) the tasks.

| Folder | Holds | Status | Docs, tools | Still open |
|---|---|---|---|---|
| `0SYSTEM/` | UI colours, crest/badge/sponsor textures, fonts | done | [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md), [`FONT_FORMAT.md`](DOC/FONT_FORMAT.md), `system.py`, `font.py`, `fontmod.py` (a new face for font 0) | what `DETAILFLAG` switches, which UI element uses each colour, who the `V001`–`V032` crests are |
| `ACROBATA/` | 875 Acroarts event scenes (718 scene ids) | most files | [`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md), `acrobata.py` | the `ABDT` scene layout, which code plays which scene |
| `BG/` | pre-rendered rooms' data, people, hands and props, trophies, the human database | done | [`BG_DIR.md`](DOC/BG_DIR.md), [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md), [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md), `zbf.py`, `ninja.py`, `humanid.py` | the room table's fields, what `HUMANID.BIN`'s object kinds select, `OR2` and `IS` |
| `CSE/` | 2D screen layouts | done, with a writer for same-size textures | [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md), `csp.py` | a few header and node fields, the `0x200` bit of an animation track's kind |
| `EMBLEM/` | the club editor's crest and flag parts, the player editor's tables | most files, with a writer for the crest, flag and player-editor tables | [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md), `emblem.py` | which choices pick some `EDIT_PLAYER.TBB` rows, what a part's `rev` values do |
| `EVENT/` | the event, news and mail tables | done | [`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md), [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md), `evsdatabin.py` | three NEWS columns, the names of the condition and handler kinds, some event record fields |
| `GAME/` | match data: commentary, sound, models, tactics AI | partly | [`GAME_DIR.md`](DOC/GAME_DIR.md), [`BPB_FORMAT.md`](DOC/BPB_FORMAT.md), [`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md), `sounddat.py`, `ninja.py`, `bpb.py`, `gamedata.py`, `packdata.py` | what the `.CBB` blocks and some combination areas select, which gait each play-book move order is, the rest of a `GAMEDATA.BIN` record, whether `AI_PARAM.BIN` is used, the cut-in pack's `CIB0`/`BMT1` blocks, the `RBD0` trailer, the `SHADOWCOLLI`/`WALLCOLLI` entries, `TEAM.TMB`, `BACK_MATCH.TBB`, which copy of `EFFECTS` and `TRAINING` the game loads |
| `MESSAGE/` | all message text | done, with a writer | [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md), `mbb.py` | which value the screen-set variables hold, where the speaker names come from |
| `NEWS/` | newspaper pictures and ranking months | done | [`NEWS_DIR.md`](DOC/NEWS_DIR.md), `news.py` | which paper a page uses, where ads and cartoons go on the page |
| `PARAM/` | the starting season, player database, game tables | most files, with writers | [`PARAM_DIR.md`](DOC/PARAM_DIR.md) and the docs it links; `initteam.py`, `teaminit.py`, `pbdata.py`, `schedule.py`, `leaguesize.py`, `plrsim.py`, `plrcommon.py`, `regulation.py`, `clubresult.py`, `training.py`, `camp.py`, `formset.py`, `tour.py`, `clubrank.py`, `natcal.py` | the values in `PLRESOURCECOMMON.PAC` entry 1 and table 4.1, a few schedule tables, what reads `MAPTEAM_LIST.TBB`, `SPONSOR_BOARD.TBB` and `CLUBEVENT.TBB`, what a few named player fields do |
| `PLAYER/` | faces, kits, player models | most files, with a kit writer | [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md), [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md), `packdata.py`, `uniform.py` | the face block-4 header, a few kit fields, which model is which |
| `PRELOAD/` | copies of other files for bulk loading | done, with a writer | [`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md), `preload.py` | what a record's `+0x18` selects, `DUMMY.DAT` |
| `SEQ/` | the root sequencer scripts, and which one starts which screen | most files | [`SEQ_DIR.md`](DOC/SEQ_DIR.md), [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md), `sqb.py` | two unused 2004 scripts, `WPX` |
| `SOUND/` | 28 sound banks: effects and music | done | [`SOUND_DIR.md`](DOC/SOUND_DIR.md), `sounddat.py` | which screen plays which music, 4 banks the code never names |
| `STADIUM/` | stadium models, crowds, adverts | done, with a writer for the looks and boards | [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md), `stadium.py` | byte `+0x0c` of your stadium record, the crowd palettes |
| `TEST3D/` | the developers' test data | most files | [`TEST3D_DIR.md`](DOC/TEST3D_DIR.md) | `SHADOWCOLLI.LBI`, who reads 110 of the 163 files |
| `CVS/` and `*/CVS/` | the developers' version-control metadata, not read by the game | done | [`CVS_DIR.md`](DOC/CVS_DIR.md), `cvs.py` | – |

Outside `DATA.CVM`, the disc's `AUDIO/` folder (music, commentary,
chants and ambience) is done in [`AUDIO_DIR.md`](DOC/AUDIO_DIR.md)
(`afs.py` reads it; there is no writer), the `DLL/*.REL` overlays in
[`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md), and memory-card saves in
[`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md). `OPMOVIE.SFD` (Sofdec video) is
not studied.

## Principles

- **The docs come first.** A value is edited through a tool only when
  its meaning is documented, labelled confirmed or empirical like every
  other claim in `DOC/`.
- **Never corrupt a save or a disc silently.** Writers validate their
  output by reading it back. The GUI refuses values that break a
  documented constraint and doesn't guess.
- **Keep the tools usable without the GUI.** Every edit a GUI can make
  is also a `python SRC/...` command, so changes can be scripted, diffed
  and reviewed. The editors log the command behind each save.
- **Keep the setup light.** The standard library only, as elsewhere in
  `SRC/`. `tkinter` ships with Python and fits that rule for the GUI.
- **English first.** The project serves the English-speaking LMAST
  community. The tools read the Japanese release too, but work on it
  comes later. It is still part of finishing
  ([below](#when-the-reverse-engineering-is-complete)), and LMASTER
  1.0.0 needs every switch to work on it (Nexxus's choice, 2026-11-01).

## When the reverse engineering is complete

Nexxus's definition (2026-11-01): the reverse engineering is complete
when every file, every line of code and every mechanic of the game is
fully documented, on both releases, and the mod editor and the save
editor work on the Japanese release as on PAL. The stages above get the
data editable well before that; this is the end point after them. It
includes the game's runtime memory, which a RetroAchievements set needs:
[`RAM_MAP.md`](DOC/RAM_MAP.md) and the three docs it indexes record the
PAL release's, read from the code and not yet measured in the running
game.

Only then might a follow-on project begin: **LMAST-Recompiled**, a full
decompilation of the game, recompiled, ported to other platforms and
expanded. It would be a project of its own, built on these docs.

## Out of scope

- Distributing the game, its data, or patched disc images.
- Changes that need new game code, until the data side is done. Small
  patches are fine where they flip switches already in the code (the
  tutorial skip, the developer launcher, separate saves) or restore
  content the release cut or broke with the smallest change that works
  (the [LMASTER Mod](DOC/LMASTER_MOD.md): the sponsor negotiation, the
  rival's manager, the camp list's loop bound). Each is a named
  `patch_disc.py` switch, tested in PCSX2. The one larger piece of new
  code is the third tier's, which had to grow the save to hold the extra
  clubs ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)).
- Decompiling, recompiling or porting the game. That is
  LMAST-Recompiled's, a possible later project
  ([above](#when-the-reverse-engineering-is-complete)).
