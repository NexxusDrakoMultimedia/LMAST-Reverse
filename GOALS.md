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
   `regress.py`.
4. **Rebuild.** Put edited files back into `DATA.ISO`, re-encrypt it as
   `DATA.CVM`, and produce a disc image that boots. This includes repacking
   BINPAC/KC@P archives and PRS compression, and handling files that change
   size. *Started:* `SRC/patch_disc.py` patches same-size files straight into
   the disc image, since only the table of contents is encrypted
   ([`REBUILD.md`](DOC/REBUILD.md)). Size changes and repacking are still
   to do.
5. **Edit.** GUI tools on top of the writers, organised by what a player of
   the game would recognise (a club, a player, a season) rather than by file.
   The GUI checks values against the documented ranges and cross-references
   (for example, a message reference that no longer resolves).
6. **Distribute.** Share mods as xdelta patches (VCDIFF, made with
   `xdelta3`) against the user's own unmodified disc image, never as game
   data or disc images. This matches the rule that no game data goes in the
   repo. xdelta is the usual format for disc-image mods, and players can
   apply a patch with existing tools such as xdelta UI or DeltaPatcher,
   without installing anything from this repo. `xdelta3` runs as an external
   program, so it doesn't add a Python dependency.

## Coverage of `DATA.CVM`

The goal is that every folder in `DAT/` has a doc saying what it holds and
which scenes or systems load it, and every file type in it has a format doc
and a tool whose `info` passes over all of `DAT/`. Nothing is left as "unknown
binary". Even a format that nobody plans to edit is documented, because an
unexplained file can hide a dependency that breaks a rebuilt disc.

Where each folder stands (September 2026):

| Folder | Contents | Status |
|---|---|---|
| `0SYSTEM/` | `TBB`, `PAC`, `SVR`/`SVP`, `ICO`, `DAT` | containers and textures parse; no folder doc, table meanings unknown |
| `ACROBATA/` | `PAC`, `DAT` | not studied |
| `BG/` | 304 `MRG`, `HED`, `SVR`, Ninja `SNO`/`SNM`/`SNJ` | archives, textures, Z buffers and models done ([`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md), [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md)) |
| `CSE/` | 490 `CSP`, `CSE`, `SVR`, a few others | screen layouts done ([`CSE_FORMAT.md`](DOC/CSE_FORMAT.md)) |
| `EMBLEM/` | `TBB`, `PAC`/`HED` | tables parse (3 are a byte short, see [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md)); no folder doc |
| `EVENT/` | `EvsDataBin_*.bin`, `EVENTDATA_TURN.TBB` | done ([`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md), [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md)); some NEWS/MAIL columns unnamed |
| `GAME/` | commentary `TBL`, sound banks, models, many small types | surveyed in [`GAME_DIR.md`](DOC/GAME_DIR.md); models parse ([`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md)); several types not parsed |
| `MESSAGE/` | `MES.PAC` | done ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md)) |
| `NEWS/` | `PAC`/`HED`, `TBB` | containers parse; no folder doc |
| `PARAM/` | 18 `TBB`, `PAC`/`HED`, `BIN` | tables parse; loaders and row counts in [`PARAM_DIR.md`](DOC/PARAM_DIR.md), 7 record layouts confirmed, the rest not decoded |
| `PLAYER/` | `PAC`/`HED`, `MRG`, KC@P face/kit packs, Ninja models, `TBB` | surveyed in [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md); `etc::PackData` parsed by `packdata.py`, block contents partly decoded, 3 tables not decoded; models parse, faces included ([`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md)) |
| `PRELOAD/` | 139 `PAC` | containers parse; no folder doc |
| `SEQ/` | 19 `SQB`, `TBB`, `WPX` | not studied |
| `SOUND/` | 28 `DAT` sound banks | banks parse; no folder doc |
| `STADIUM/` | `PAC`/`HED`, 24 `TBB`, `PRI` | surveyed in [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md); `PRI` and all 24 tables decoded: part slots, stadium build, collision, crowd sets and tiers, adverts, stadium id by level (a few flags unknown) |
| `TEST3D/` | Ninja models, `SVR`/`SVP`/`SVM`, `LBI` | textures and models done; `LBI` not parsed |
| `CVS/` and `*/CVS/` | the developers' version-control metadata | not game data; worth noting in a doc, nothing to parse |

"Containers parse" means `pac.py` or `tbb.py` reads the file, but what the
entries or rows mean isn't documented yet.

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
