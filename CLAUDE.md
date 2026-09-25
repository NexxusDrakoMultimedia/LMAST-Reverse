# CLAUDE.md

Reverse-engineering notes (`DOC/`) and Python tools (`SRC/`) for the PAL PS2
game *Let's Make a Soccer Team!* (`SLES_541.51`). See `README.md` for setup,
the tool list, and the doc index. See `TODO.md` for what to work on next.

## Data layout

- `ISO/` holds the disc files, `DATA.CVM`, and the decrypted `DATA.ISO`.
  `DAT/` holds the extracted contents of `DATA.ISO`. Both are git-ignored and
  must never be committed. No game data goes in the repo, and that includes
  large excerpts in docs. Small hex snippets and counts are fine.
- Most tools read from `DAT/`. The disassemblers read `ISO/SLES_541.51` and
  `ISO/DLL/*.REL`.
- Put scratch output such as PNGs, CSVs and extracted files outside the repo
  or in an ignored path. Don't leave it in the working tree.

## Workflow for a new format

1. Find the loader in the game code: `python SRC/sles_disasm.py ISO/SLES_541.51 dis <symbol>`
   or `python SRC/snr2.py dis ISO/DLL/<X>.REL <addr> <n> --sles ISO/SLES_541.51`.
   About 12,600 symbol names are recovered, so search by name first.
2. Write `DOC/<NAME>_FORMAT.md`.
3. Write `SRC/<name>.py`.
4. Run its `info` over all of `DAT/` until it reports no problems.
5. Update the README's tool table and doc index, and tick off `TODO.md`.

Commits usually add a doc and its tool together, with messages like
"Document X format; add x.py reader".

## Documentation conventions (`DOC/`)

- Label every layout claim either **confirmed**, citing the game-code address
  and symbol that proves it, or **empirical**, meaning it was inferred from
  data and checked against every file on the disc. Keep the two separate. A
  "Confirmed from the game code" table (Address | Symbol | What it shows) is
  the usual pattern.
- Give addresses as hex with `0x`. Overlay addresses name the `.REL`, for
  example `MOVIEPRG.REL 0x32ec`.
- Include exact counts from the full data set, such as "3,738 files" or
  "64,455 of 65,889". Say explicitly what is still unknown instead of
  guessing.
- Write plainly: short sentences, tables for field layouts, and a
  `python SRC/...` command showing how to check the claims.

## Code conventions (`SRC/`)

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
- `info` walks files or directories, checks every file against the documented
  layout, and prints any mismatch. It is the regression check.
- Tools reuse each other through sibling imports (`from pac import BinPac`,
  `import svr`, `import tbb`). These work because the script's directory is
  on `sys.path`. Reuse `pac.py` for BINPAC/KC@P/PRS, `tbb.py` for TBB1/TBL1
  tables, and `svr.py` for textures rather than reimplementing them.
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
