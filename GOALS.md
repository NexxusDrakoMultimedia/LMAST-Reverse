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
   new club), `uniform.py` (club kits), `sqb.py` (sequencer scripts) and
   `pac.py` (BINPACs) write and round-trip every file. `initteam.py` edits
   squads and club records, and `save.py` edits saved games. Edits to the
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
   writer. Moving files, and repacking other archives on the disc, are
   still to do.
5. **Edit.** GUI tools on top of the writers, organised by what a player of
   the game would recognise (a club, a player, a season) rather than by file.
   The GUI checks values against the documented ranges and cross-references
   (for example, a message reference that no longer resolves).
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

Where each folder stands (October 2026):

| Folder | Contents | Status |
|---|---|---|
| `0SYSTEM/` | `TBB`, `PAC`, `SVR`/`SVP`, `ICO`, `DAT` | surveyed in [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md), `system.py`: loader of every file, the colour table, the 8 texture packs and their index rules, fonts by language; `DETAILFLAG` meaning and colour uses unknown |
| `ACROBATA/` | `PAC`, `DAT` | surveyed in [`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md), `acrobata.py`: the 875 Acroarts scenes (`ABDA` + `ABRS`), their `POF0` pointers and 4,841 Ninja and texture resources check; the executable's index copy and scene-id table decoded; the `ABDT` scene layout not decoded |
| `BG/` | 304 `MRG`, `HED`, `SVR`, Ninja `SNO`/`SNM`/`SNJ` | archives, textures, Z buffers and models done ([`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md), [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md)) |
| `CSE/` | 490 `CSP`, `CSE`, `SVR`, a few others | screen layouts done ([`CSE_FORMAT.md`](DOC/CSE_FORMAT.md)) |
| `EMBLEM/` | `TBB`, `PAC`/`HED` | surveyed in [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md), `emblem.py`: loaders of every file, the 96-colour palette and its maps, which `EDIT_EMBLEM`/`EDIT_FLAG` table holds what and how they line up with the part packs, what the game does with the 3 short tables; preset and crest record fields and `EDIT_PLAYER.TBB` not decoded |
| `EVENT/` | `EvsDataBin_*.bin`, `EVENTDATA_TURN.TBB` | done ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md), [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md)); some NEWS/MAIL columns unnamed |
| `GAME/` | commentary `TBL`, sound banks, models, many small types | surveyed in [`GAME_DIR.md`](DOC/GAME_DIR.md); `SOUNDDAT.PAC` and commentary tables decode (`sounddat.py`); models parse ([`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md)); tactics AI, `GAMEDATA.BIN`, `AI_PARAM.BIN` not parsed |
| `MESSAGE/` | `MES.PAC` | done, with a writer ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md)) |
| `NEWS/` | `PAC`/`HED`, `TBB` | done ([`NEWS_DIR.md`](DOC/NEWS_DIR.md), `news.py`): the loader of every pack, mastheads by league, article pictures by index, `NEWSMONTHFLAG` decoded; where ads and cartoons go on the page not traced |
| `PARAM/` | 18 `TBB`, `PAC`/`HED`, `BIN` | tables parse; loaders and row counts in [`PARAM_DIR.md`](DOC/PARAM_DIR.md), 8 record layouts confirmed (`TEAM_INIT_DATA`, the player's new club, in [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md)), and every entry of `PLRESOURCESIM.PAC` ([`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md)); `PLRESOURCECOMMON` and some tables not decoded |
| `PLAYER/` | `PAC`/`HED`, `MRG`, KC@P face/kit packs, Ninja models, `TBB` | surveyed in [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md); `etc::PackData` parsed by `packdata.py`, block contents partly decoded; kit tables `UNIFORM_LIST` and `COLOR_TBL` decoded with an editor ([`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md)), `UNIFORM_GK` not; models parse, faces included ([`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md)) |
| `PRELOAD/` | 139 `PAC` | done ([`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md), `preload.py`): every entry is a byte-identical copy of a file elsewhere, the loader of every pack is known, and which copy the game reads is confirmed and tested in PCSX2 |
| `SEQ/` | 19 `SQB`, `TBB`, `WPX` | sequencer scripts decoded ([`SQB_FORMAT.md`](DOC/SQB_FORMAT.md), `sqb.py`), folder overview in [`SEQ_DIR.md`](DOC/SEQ_DIR.md): 17 of 19 decode and check (two unused 2004 scripts don't); `SQBFILENAME` and `GLOBALMEMORY` done; `WPX` unreferenced, not decoded |
| `SOUND/` | 28 `DAT` sound banks | surveyed in [`SOUND_DIR.md`](DOC/SOUND_DIR.md): all 28 `ps2_DTPK` banks parse, and samples, songs and instruments decode (`sounddat.py`, [`GAME_DIR.md`](DOC/GAME_DIR.md#the-soundmap-banks)); the executable's bank table and music table (music id → song) decoded (`sounddat.py music`); which screen plays which music id, and 4 banks the code never names, unknown |
| `STADIUM/` | `PAC`/`HED`, 24 `TBB`, `PRI` | surveyed in [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md); `PRI` and all 24 tables decoded: part slots, stadium build, collision, crowd sets and tiers, adverts, stadium id by level (a few flags unknown) |
| `TEST3D/` | Ninja models, `SVR`/`SVP`/`SVM`, `LBI` | surveyed in [`TEST3D_DIR.md`](DOC/TEST3D_DIR.md): test data only; textures and models done, what reads 53 of the 163 files known; `LBI` not parsed |
| `CVS/` and `*/CVS/` | the developers' version-control metadata | done ([`CVS_DIR.md`](DOC/CVS_DIR.md), `cvs.py`): not read by the game; gives original file names and dates, and shows which files the build made |

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
