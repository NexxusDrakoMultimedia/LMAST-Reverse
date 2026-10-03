<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# CLAUDE.md

Reverse-engineering notes (`DOC/`) and Python tools (`SRC/`) for the PAL PS2
game *Let's Make a Soccer Team!* (`SLES_541.51`). See `README.md` for setup,
the tool list, and the doc index. See `GOALS.md` for what the project is
working towards, `TODO.md` for what to work on next, and `DONE.md` for the
finished items.

## Data layout

- `ISO/` holds the disc files, `DATA.CVM`, and the decrypted `DATA.ISO`.
  `DAT/` holds the extracted contents of `DATA.ISO`. Both are git-ignored and
  must never be committed. No game data goes in the repo, and that includes
  large excerpts in docs. Small hex snippets and counts are fine.
- Most tools read from `DAT/`. The disassemblers read `ISO/SLES_541.51` and
  `ISO/DLL/*.REL`. `afs.py` reads `ISO/AUDIO`, which is outside `DATA.CVM`.
  `save.py` runs the serializers in `ISO/SLES_541.51` and
  `ISO/DLL/SAVEPRG.REL`. `patch_disc.py` and `vcdiff.py` work on whole disc
  images.
- Other ignored paths: `*.iso` and `*.xdelta` in the repo root (the
  Redump dump, built discs and patches), `mod/` (the editor's default mod
  folder, which holds edited game files), `.regress/` (regression
  baselines, which list names and counts from the disc) and `.cache/`
  (`save.py`'s recorded field list).
- Put scratch output such as PNGs, CSVs and extracted files outside the repo
  or in an ignored path. Don't leave it in the working tree.

## Workflow for a new format

1. Find the loader in the game code: `python SRC/sles_disasm.py ISO/SLES_541.51 dis <symbol>`
   or `python SRC/snr2.py dis ISO/DLL/<X>.REL <addr> <n> --sles ISO/SLES_541.51`.
   About 12,600 symbol names are recovered, so search by name first.
2. Write `DOC/<NAME>_FORMAT.md`.
3. Write `SRC/<name>.py`.
4. Run its `info` over all of `DAT/` until it reports no problems, then add
   a check to `checks()` in `SRC/regress.py` and `bless` it.
5. Update the README's tool table and doc index. Tick off the `TODO.md`
   item and move it to the end of the same section in `DONE.md`. If part of
   it is still open, leave that part in `TODO.md` as its own item. If the
   item was in TODO's "Next up" list, take it off and suggest a
   replacement to the user. If a
   folder's status changes, update the coverage table in `GOALS.md`.

Adding a writer (the write stage in `GOALS.md`) follows the same steps, plus
a `roundtrip` command that re-encodes every file or record and marks any
difference with `!!`. It goes into `regress.py` as `<name>_roundtrip`. The
existing writers are `pac.py` (BINPACs), `tbb.py`, `pbdata.py`, `mbb.py`,
`initteam.py` (`set`, `setteam`), `teaminit.py`, `uniform.py`, `sqb.py`
(`setcmd`) and `save.py`. `plrsim.py setfree` writes too but has no
`roundtrip` yet.

A writer can then get a tab in `editor.py` (stage 5). The tab edits through
the writer's own `set` functions and asks the writer which values each
field allows (as `pbdata.edit_spec` does), so the editor holds no layout of
its own. Its saves must equal the command it logs, byte for byte. Check
that by running the logged command and comparing the files. Test a tab
through its widgets (choose drop-down entries, type into boxes and fire
their events), not by calling its commit functions, and keep the test
window off-screen (`geometry("1280x720+-4000+0")`) so nothing appears on
the user's desktop.

Some things can only be checked by a person: that an edit shows in the game
(PCSX2), what a screen shows, or how audio sounds. Ask the user to check,
then record the result in the doc and in `TODO.md` or `DONE.md` ("Tested
in PCSX2: ...", "identified by ear"). The user doesn't write code, so don't hand code tasks
to them.

After changing any tool, run `python SRC/regress.py run`. A diff is a
regression unless the change was intended. Only then run `bless <name>`, and
say in the commit what changed in the output. Never bless to make a failure
go away. A `!!` line that disappears fails too, and needs the same review: a
fix is fine to bless, but a check that stopped running is a regression.

Commits usually add a doc and its tool together, with messages like
"Document X format; add x.py reader".

## Documentation conventions (`DOC/`)

- Label every layout claim either **confirmed**, citing the game-code address
  and symbol that proves it, or **empirical**, meaning it was inferred from
  data and checked against every file on the disc. Keep the two separate. A
  "Confirmed from the game code" table (Address | Symbol | What it shows) is
  the usual pattern. A result seen in the running game is stated as such
  ("Tested in PCSX2", "checked in game", "by ear"), with what was changed
  and what showed.
- Give addresses as hex with `0x`. Overlay addresses name the `.REL`, for
  example `MOVIEPRG.REL 0x32ec`.
- Include exact counts from the full data set, such as "3,738 files" or
  "64,455 of 65,889". Say explicitly what is still unknown instead of
  guessing.
- Write plainly: short sentences, tables for field layouts, and a
  `python SRC/...` command showing how to check the claims.

## Code conventions (`SRC/`)

- The repo is GPL-3.0-or-later (`LICENSE`). Every new `.py` file starts with
  `# SPDX-License-Identifier: GPL-3.0-or-later` and
  `# Copyright (C) 2026 Nexxus Drako Multimedia`, before the docstring. Every new `.md`
  file starts with the same two lines as HTML comments (`<!-- ... -->`).
- Each tool is a single standalone script run from the repo root as
  `python SRC/<tool>.py <command> ...`. There is no package, no
  `__init__.py`, and no tests.
- Use the standard library only. `PIL` and `capstone` are imported lazily
  inside the functions that need them, so other commands still work when
  they aren't installed. Keep it that way.
- The module docstring is the usage text. It summarises the format, cites the
  confirming addresses, points to the `DOC/` file, and lists the commands.
  Running with no arguments prints it.
- Structure: format classes and parse functions, then `cmd_<name>(...)`
  functions, then a hand-rolled `main(argv)` (no argparse), then
  `sys.exit(main(sys.argv))`.
- `info` walks files or directories and checks every file against the
  documented layout. Every problem is marked with `!!` on the line it
  concerns: `<normal line>  !! reason; reason`, or a line of its own
  (`  !! reason`) when the item spans several lines. `!!` means the data
  doesn't fit the documented layout, or the file couldn't be parsed. Don't
  use it for informational notes such as "swizzled" or "repeated ids (not an
  error)", and don't use any other marker.
- `info` catches parse errors (`ValueError`, `struct.error`) for each file and
  reports them as `!!`, so one bad file doesn't stop the scan. Other commands
  (`dump`, `extract`, `png`, ...) let errors propagate.
- The CSV exporters (`evsdatabin.py`, `eventdata_turn.py`) have no `info`
  and don't use `!!`. They write CSV to a file, or to stdout without one.
  `evsdatabin.py` raises if a file isn't a whole number of records;
  `eventdata_turn.py` ignores a partial record at the end.
- Writers never change their input. They take an output path
  (`set <in> <out> ...`, `import <in> <edits.csv> <out>`), and only
  `patch_disc.py patch --in-place` writes over an image, when asked to.
  The editor replaces files in its own mod folder, by writing
  `<file>.new` and moving it over the old one.
- Tools reuse each other through sibling imports (`from pac import BinPac`,
  `import svr`, `import tbb`). These work because the script's directory is
  on `sys.path`. Reuse `pac.py` for BINPAC/KC@P/PRS, `tbb.py` for TBB1/TBL1
  tables, `svr.py` for textures, `sles_disasm.py`/`snr2.py` for the game
  code, and `extract_disc.py`/`rofs_decrypt.py` for the disc image, rather
  than reimplementing them.
- Parse with `struct` and little-endian formats (`"<I"`, `"<H"`). Name magic
  numbers and give sizes and offsets in hex.
- Match the comment style of the surrounding code. Comments explain *why* and
  cite the game-code address when the answer comes from the executable.

## Environment notes

- The primary platform is Windows. Paths in docs and commands use forward
  slashes, and the tools accept either.
- Capstone has no R5900 mode, so `lq`/`sq` and MMI opcodes disassemble
  incorrectly. Don't trust those lines.
- Text encodings: European message text is cp850 and Japanese is cp932 with
  extra kana bytes (see `DOC/MBB_FORMAT.md`). Don't assume ASCII or UTF-8 in
  game data.
