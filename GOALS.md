<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Goals

The aim of this project is to make the data in *Let's Make a Soccer Team!*
(`SLES_541.51`) easy to edit, so that people can build a modded version of the
game: adjusted data, a different starting season, or tweaked parameters. The
end product is a set of GUI tools that let someone change the game's data
without knowing the file formats.

[`TODO.md`](TODO.md) lists the next concrete tasks. This file says what they
are for.

## What a mod should be able to change

- **The starting season.** The state a new game begins in: schedules,
  competitions, league membership, clubs, squads and players. The game then
  plays on from there as normal.
- **Data.** Club, player, stadium and staff records, and the text that goes
  with them.
- **Parameters.** The tuning values in the `TBB1`/`TBL1` tables: prices,
  growth rates, event odds, match settings and so on.
- **Text.** Message text in every language slot, including event dialogue,
  news and mail.

Graphics, models and sound are useful to extract, but editing them is a lower
priority than the data above.

## The path there

Each stage depends on the one before it.

0. **Decrypt.** *Done.* `DATA.CVM`'s encrypted ISO9660 table of contents is
   decrypted by `SRC/rofs_decrypt.py` with the key recovered from the running
   game, and `DATA.ISO` extracts to `DAT/`. See
   [`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md) and
   [`LMAST_DATA_CVM_INFO.md`](DOC/LMAST_DATA_CVM_INFO.md).
1. **Read.** Document every file format and every folder in `DATA.CVM` in
   `DOC/`, and parse each format in `SRC/`, checked against every file on the
   disc. This is the stage most of the current work is in. See
   [Coverage of `DATA.CVM`](#coverage-of-datacvm) below for where each folder
   stands.
2. **Understand.** Know what each field *means* in the game, not just its
   type and offset. A field can't be offered for editing until it has a name
   and a known range. Fields that are still unknown stay read-only.
3. **Write.** Add a writer for each format. A writer must round-trip: reading
   a file and writing it back unchanged gives the original bytes. That check
   runs over every file on the disc before any edit is trusted, and goes into
   `regress.py`. *Started:* `tbb.py` (all 70 tables), `pbdata.py` (the
   player database), `mbb.py` (message text), `teaminit.py` (the player's
   new club), `uniform.py` (club kits), `sqb.py` (the 41 sequencer scripts
   that decode) and `pac.py` (BINPACs) write and round-trip every file.
   `initteam.py` edits and round-trips squads and club records, and
   `save.py` edits saved games. Edits to the
   player database, text, the new club's squad, kits, free agents and saves
   have been tested in PCSX2.
4. **Rebuild.** Put edited files back into `DATA.ISO`, re-encrypt it as
   `DATA.CVM`, and produce a disc image that boots. This includes repacking
   BINPAC/KC@P archives and PRS compression, and handling files that change
   size. *Started:* `SRC/patch_disc.py` patches same-size files straight into
   the disc image, since only the table of contents is encrypted
   ([`REBUILD.md`](DOC/REBUILD.md)). A message file can also grow into
   the spare room of its `MES.PAC` slot. A file can change size inside its
   last sector (its directory record is rewritten and re-encrypted), and
   `PRELOAD` packs are rebuilt around grown entries with `pac.py`'s BINPAC
   writer. A file that needs more sectors is moved to the end of
   `DATA.ISO`, which grows `DATA.CVM` and re-keys its table of contents
   and grows the disc image when needed (both tested in PCSX2). Repacking
   other archives on the disc is still to do.
5. **Edit.** GUI tools on top of the writers, organised by what a player of
   the game would recognise (a club, a player, a season) rather than by file.
   The GUI checks values against the documented ranges and cross-references
   (for example, a message reference that no longer resolves). *Started:*
   `SRC/editor.py`, one window with a tab per kind of data, saving to a mod
   folder laid out like `DAT/`. Its People tab edits the player database
   through `pbdata.py`, with the allowed values from `pbdata.edit_spec`.
6. **Distribute.** Share mods as xdelta patches (VCDIFF, RFC 3284) against
   the user's own unmodified disc image, never as game data or disc images.
   This matches the rule that no game data goes in the repo. xdelta is the
   usual format for disc-image mods, and players can apply a patch with
   existing tools such as xdelta UI or DeltaPatcher, without installing
   anything from this repo. *Started:* `SRC/vcdiff.py` makes and applies
   these patches in plain Python, so `xdelta3` isn't needed
   ([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod)). Delta Patcher applies
   them with the same result. A modded disc can take its own serial
   (`save.py serial`), so its saves stay apart from the original game's.

## Coverage of `DATA.CVM`

The goal is that every folder in `DAT/` has a doc saying what it holds and
which scenes or systems load it, and every file type in it has a format doc
and a tool whose `info` passes over all of `DAT/`. Nothing is left as "unknown
binary". Even a format that nobody plans to edit is documented, because an
unexplained file can hide a dependency that breaks a rebuilt disc.

Where each folder stands (October 2026). The status is one of:

- **done**: every file type parses and is checked over all of `DAT/`. What
  is left is the meaning of some fields.
- **most files**: one or two file types aren't parsed yet.
- **partly**: several file types aren't parsed yet.

The "Still open" column is a summary. The full items are in
[`TODO.md`](TODO.md), and what is known is in the docs.

| Folder | Holds | Status | Docs, tools | Still open |
|---|---|---|---|---|
| `0SYSTEM/` | UI colours, crest/badge/sponsor textures, fonts | done | [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md), `system.py` | what `DETAILFLAG` switches, which UI element uses each colour |
| `ACROBATA/` | 875 Acroarts event scenes | most files | [`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md), `acrobata.py` | the `ABDT` scene layout, which code plays which scene |
| `BG/` | pre-rendered rooms: archives, textures, Z buffers, models | most files | [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md), [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md), `zbf.py`, `ninja.py`; no folder doc | `HUMANID.BIN` |
| `CSE/` | 2D screen layouts | done | [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md), `csp.py` | |
| `EMBLEM/` | the club editor's crest and flag parts | most files | [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md), `emblem.py` | preset and crest records, `EDIT_PLAYER.TBB` |
| `EVENT/` | the event, news and mail tables | done | [`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md), [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md), `evsdatabin.py` | three NEWS columns |
| `GAME/` | match data: commentary, sound, models, tactics AI | partly | [`GAME_DIR.md`](DOC/GAME_DIR.md), `sounddat.py`, `ninja.py`, `bpb.py`, `gamedata.py` | the `.CBB` fields and combination commands, what the play books' paths mean, what a `GAMEDATA.BIN` record is, whether `AI_PARAM.BIN` is used, `CUTINPACK` blocks, the `RBD0` trailer, the `SHADOWCOLLI`/`WALLCOLLI` entries, `TEAM.TMB` |
| `MESSAGE/` | all message text | done, with a writer | [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md), `mbb.py` | which value the screen-set variables hold |
| `NEWS/` | newspaper pictures and ranking months | done | [`NEWS_DIR.md`](DOC/NEWS_DIR.md), `news.py` | where ads and cartoons go on the page |
| `PARAM/` | the starting season, player database, game tables | most files, with writers | [`PARAM_DIR.md`](DOC/PARAM_DIR.md) and the docs it links; `initteam.py`, `teaminit.py`, `pbdata.py`, `schedule.py`, `plrsim.py`, `plrcommon.py` | the values in `PLRESOURCECOMMON.PAC` entries 1, 2 and 4, a few schedule tables, some player fields |
| `PLAYER/` | faces, kits, player models | most files, with a kit writer | [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md), [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md), `packdata.py`, `uniform.py` | the face block-4 header, a few kit fields |
| `PRELOAD/` | copies of other files for bulk loading | done, with a writer | [`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md), `preload.py` | |
| `SEQ/` | the root sequencer scripts | most files | [`SEQ_DIR.md`](DOC/SEQ_DIR.md), [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md), `sqb.py` | two unused 2004 scripts, `WPX` |
| `SOUND/` | 28 sound banks: effects and music | done | [`SOUND_DIR.md`](DOC/SOUND_DIR.md), `sounddat.py` | which screen plays which music, 4 banks the code never names |
| `STADIUM/` | stadium models, crowds, adverts | done | [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md), `stadium.py` | a few flags |
| `TEST3D/` | the developers' test data | most files | [`TEST3D_DIR.md`](DOC/TEST3D_DIR.md) | `SHADOWCOLLI.LBI`, who reads 110 of the 163 files |
| `CVS/` and `*/CVS/` | the developers' version-control metadata, not read by the game | done | [`CVS_DIR.md`](DOC/CVS_DIR.md), `cvs.py` | |

Outside `DATA.CVM`, the disc's `AUDIO/` folder (music, commentary, chants and
ambience) is done in [`AUDIO_DIR.md`](DOC/AUDIO_DIR.md), the `DLL/*.REL`
overlays in [`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md), and memory-card saves in
[`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md). `OPMOVIE.SFD` (Sofdec video) is not
studied.

## Principles

- **The docs come first.** A value is edited through a tool only when its
  meaning is documented, labelled confirmed or empirical like every other
  claim in `DOC/`.
- **Never corrupt a save or a disc silently.** Writers validate their output
  by reading it back. The GUI refuses values that break a documented
  constraint and doesn't guess.
- **Keep the tools usable without the GUI.** Every edit a GUI can make should
  also be possible from a `python SRC/...` command, so that changes can be
  scripted, diffed and reviewed.
- **Keep the setup light.** The standard library only, as elsewhere in
  `SRC/`. `tkinter` ships with Python and fits that rule for the GUI.

## Out of scope

- Distributing the game, its data, or patched disc images.
- Changes that need new game code, until the data side is done. Patching
  `SLES_541.51` or the `.REL` overlays may come later if a mod needs it.
  Small patches that flip switches already in the code (the tutorial skip,
  the developer launcher, the save serial) are fine as testing aids.
