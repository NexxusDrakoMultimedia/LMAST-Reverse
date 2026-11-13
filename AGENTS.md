<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# AGENTS.md

Instructions for any AI assistant working on this repo, such as ChatGPT
(Codex), Gemini, Perplexity or Claude. They apply whichever tool you are.
`CLAUDE.md` points Claude Code at this file.

This repo holds reverse-engineering notes (`DOC/`) and Python tools
(`SRC/`) for the PAL PS2 game *Let's Make a Soccer Team!* (`SLES_541.51`)
and its Japanese release, *Pro Soccer Club o Tsukurou! Europe
Championship* (`SLPM-66316`). The aim is GUI tools (`editor.py`,
`saveedit.py`) that change the game's data, and patches that players
apply to their own disc. The LMASTER Mod, built that way, is the first
mod ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)).

Where each kind of fact lives is in [Where things are
recorded](#where-things-are-recorded); the README holds setup, the tool
tables and the doc index.

The sister project VPF-Reverse (`../VPF-Reverse`,
github.com/NexxusDrakoMultimedia/VPF-Reverse) covers *Virtua Pro
Football*, which shares this game's engine. Formats both games use are
documented here first, and VPF-Reverse builds on them. Work on VPF's
own code (its Player Edit, its save) belongs there; bring back here
only what this game's tools need, such as `pmplayer.py`'s fields.

## Before you start

- Read "Next up" in `TODO.md` for what matters now, and the doc of the
  file or system you will touch, including its "Still unknown" list.
  The docs are the record of what is known: check a claim against the
  doc, the tool or the game code before you repeat it.
- Run `git status` first. Other sessions may work in the repo at the
  same time, so stage files by name (never `git add -A` or `.`), and
  don't bless baselines for output that someone else's work changed.
- `python SRC/regress.py run` needs a baseline in `.regress/`; if there
  is none, `bless` one from a clean checkout before changing anything.
- Find out who you are working with (see [Credit](#credit)) before you
  write a result or a choice into a doc.

## If you can't run commands or edit files

Some assistants only see the files they're given and can't run anything.
In that case:

- Don't guess at output. Say which command would answer the question
  (`python SRC/<tool>.py ...`, run from the repo root) and what to look for
  in its output, so the user can run it and paste back the result. The
  [quick reference](#quick-reference) lists the commands you will want
  most.
- Give file changes as complete replacement text for a named file or
  section, not as a patch to apply by hand. The user doesn't write code.
- The disc data (`ISO/`, `DAT/`) is never in the repo, so you can't read it.
  Base claims about the data on the docs, and label anything new as
  unchecked until a tool has run over the full data set.

## Repository map

The README's [repository map](README.md#repository-map) lists every
folder, in git or ignored. In short: `DOC/` holds the notes, `SRC/` the
tools and the CSV tables some read, `PNACH/` the PCSX2 widescreen patch,
and the top folder the guides ([Where things are
recorded](#where-things-are-recorded)). The disc's files and the tools'
output are git-ignored ([Data layout](#data-layout)).

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
- Other ignored paths: disc images in the repo root (`*.iso`, and the
  `*.cso`, `*.zso` and `*.chd` copies `cso.py` and `chd.py` read: the
  Redump dump and built discs such as the `LMAST-test-*.iso` test discs),
  `*.xdelta` patches in the repo root, `mod/` (the editor's default mod
  folder, which holds edited game files), `.regress/` (regression
  baselines, which list names and counts from the disc), `.cache/`
  (`save.py`'s recorded field list and `gamever.py`'s address results)
  and `names/` (the name tables `mbb.py names` writes for the user to
  fill in).
- The Japanese release (SLPM-66316) extracts to `ISO_JP/` and `DAT_JP/`,
  also ignored ([`JAPANESE_RELEASE.md`](DOC/JAPANESE_RELEASE.md)). When
  either is present, `regress.py` runs every check over it as
  `jp_<name>`.
- Put scratch output such as PNGs, CSVs and extracted files outside the repo
  or in an ignored path. Don't leave it in the working tree.

## Quick reference

Every command runs from the repo root. A tool run with no arguments
prints its usage, and each tool's module docstring is that text.

```bash
python SRC/extract_disc.py all "<disc>.iso"                 # fill ISO/ and DAT/ (or ISO_JP/ and DAT_JP/) from a disc image
python SRC/<tool>.py info DAT                               # check every file against the documented layout; look for !!
python SRC/<tool>.py roundtrip DAT                          # a writer: re-encode everything, !! on any difference
python SRC/sles_disasm.py ISO/SLES_541.51 syms <text>       # find a symbol by name
python SRC/sles_disasm.py ISO/SLES_541.51 dis <symbol>      # disassemble matching functions
python SRC/sles_disasm.py ISO/SLES_541.51 addr <hex address> [n]
# an overlay
python SRC/snr2.py dis ISO/DLL/<X>.REL <hex address> <n> --sles ISO/SLES_541.51
# what references an address or symbol in an overlay
python SRC/snr2.py xref ISO/DLL/<X>.REL <address or name>
python SRC/gamever.py check ISO_JP                          # does every address the tools use resolve on the Japanese build
python SRC/regress.py list                                  # every check and its command
python SRC/regress.py run [name ...] [--full]               # compare with the baseline (a name selects by prefix)
python SRC/regress.py bless [name ...]                      # save the current output as the baseline
python SRC/patch_disc.py switches                           # the LMASTER editions, groups and switches
# build an edition
python SRC/patch_disc.py patch disc.iso out.iso --mod lmaster-full --copies --dat DAT
python SRC/vcdiff.py make disc.iso out.iso out.xdelta       # the patch to share
```

The README's [tool tables](README.md#tools) list every command of every
tool. [`INSTALL.md`](INSTALL.md#4-building-a-patch) explains the
editions and the font and pack files a build needs.

## Workflow for a new format

1. Find the loader in the game code: `python SRC/sles_disasm.py
   ISO/SLES_541.51 dis <symbol>`
   or `python SRC/snr2.py dis ISO/DLL/<X>.REL <addr> <n> --sles
   ISO/SLES_541.51`.
   About 12,600 symbol names are recovered, so search by name first.
2. Write `DOC/<NAME>_FORMAT.md`, in the [structure](#structure-of-a-doc)
   below.
3. Write `SRC/<name>.py`.
4. Run its `info` over all of `DAT/` until it reports no problems, then add
   a check to `checks()` in `SRC/regress.py` and `bless` it.
5. Update the README's tool table, dependency table and doc index. Take
   the answered questions off the doc's "Still unknown" list. Tick off
   the `TODO.md` task and move it to the end of the same goal's section in
   `DONE.md` as a short paragraph or a few lines with a link to the doc
   (the doc keeps the details and the test results). If part of it is still
   open, leave that part in `TODO.md` as its own task. If the task was
   in TODO's "Next up" list, take it off and suggest a replacement to
   the user. If a folder's or a stage's status changes, update
   `GOALS.md`.

## Where things are recorded

| File | Holds |
|---|---|
| `DOC/*.md` | every fact about a file or system, how it was shown, the in-game tests, and the questions still open (its "Still unknown" section; every format and folder doc has one) |
| `DOC/LMASTER_MOD.md` | every LMASTER switch, group and edition: what each changes, its status and its tests. Other files link to it |
| `DOC/JAPANESE_RELEASE.md` | what differs on the Japanese disc, and how the tools reach it |
| `GOALS.md` | what the project is for, the eight things a mod should be able to change, each stage's status in a few lines, and the coverage table. No task lists |
| `TODO.md` | "Next up"; a table of the eight goals with what works and what is still in the way; then one section per goal, each opening with the goal, what works today and when it is done, then its open tasks. A task starts with its stage in bold (**read**, **understand**, **write**, **rebuild**, **edit** or **distribute**, the stages of `GOALS.md`; a **test** task is a check in the game and has no stage of its own) and links the doc that holds its details instead of repeating them. A **test** task points to `TESTING.md` |
| `TESTING.md` | the checks only a person can make in the game, for every contributor: how to take part and report, how a result is recorded, then the open checks under the goal each serves, each naming what to build and the doc the result goes into. A finished check moves to the "Tests in PCSX2" section of `DONE.md` |
| `DONE.md` | finished work, under the same goal headings as `TODO.md` plus "Tests in PCSX2": a short paragraph or a few lines per piece of work with a link to the doc, related items merged. No dates or test details: those are in the doc |
| `README.md` | setup, every tool with what it does, how the tools depend on each other, and the doc index |
| `INSTALL.md` | the players' guide, kept short: checking the disc, applying a patch, saves, and building a patch with the editions and groups in one line each. Release-specific notes (what changed between LMASTER versions, upgrading a career) belong in the LMASTER-Mod repo, and each switch's details in `DOC/LMASTER_MOD.md`. Update it when an edition or group is added or changes |
| `USAGE.md` | the guide to the mod editor and the save editor: every tab, Build disc, the save editor's pages. Update it when a tab, page or Build disc control is added or changes |
| `CODE_OF_CONDUCT.md` | the rules for everyone taking part, and how they are enforced |
| `CONTRIBUTING.md` | the guide for people sending a change or a report: ways to help, the ground rules, bug reports, the steps of a pull request. It summarises this file and links here for the details; update it when a step here changes |
| `CONTRIBUTORS.md` | who has worked on the project, research and test credits from outside it, the community, and the third-party software the tools build on. Add a person here when their finding or report goes into a doc |

The guides hold no facts about the data: they link to the doc that does.
A new open question goes into the doc first; it gets a `TODO.md` task
only when it is a task someone should pick up.

### Adding a writer

Adding a writer (the write stage in `GOALS.md`) follows the same steps,
plus a `roundtrip` command that re-encodes every file or record and marks
any difference with `!!`. It goes into `regress.py` as
`<name>_roundtrip`. (`save.py`, `ps2mc.py` and `pmplayer.py` work on
saves and cards that are not on the disc, so their checks run on files
you supply or on built test data: `save.py roundtrip`, and `selftest` in
`ps2mc.py` and `pmplayer.py`.) The existing writers are `pac.py` (BINPACs,
KC@P packs, PRS), `tbb.py`, `pbdata.py`, `mbb.py`, `initteam.py` (`set`,
`setteam`, `setnation`, `setstadium`, `swap`), `teaminit.py`,
`regulation.py`, `clubresult.py`, `training.py`, `camp.py`, `formset.py`,
`tour.py`, `clubrank.py` (`set`, `addrows`), `clubevent.py`, `natcal.py`,
`uniform.py`, `sqb.py` (`setcmd`, and `set_commands` for several edits checked together;
`settable` for the PwkScript data tables), `plrsim.py` (`setfree`,
`setbranch`, `setgroup`), `plrcommon.py` (`set`, the facility records),
`save.py`, `ps2mc.py` (`put`, `mkdir`, `copy`: memory card images),
`schedule.py` (`shift`, `balance`, the league and knockout builders, and
the encoders behind `roundtrip`), `leaguesize.py` (`build`, which writes
the schedule packs through `schedule.py`'s encoders), `pmplayer.py`
(`set`: Virtua Pro Football's edit players), `emblem.py` (`set`: the
crest, preset, layer and flag records of `EDIT_EMBLEM.TBB` and
`EDIT_FLAG.TBB`, and the cells of `EDIT_PLAYER.TBB`), `svr.py`
(`replace`: a picture into a texture, with its mip chain and palette),
`csp.py` (`replace`: the same inside a CSP pack), `texmap.py` (`apply`:
LMAST Realism's pictures into copies of their packs), `stadium.py`
(`setlook`, `setboards`: a stadium's look and advert boards in
`BUILD_STADIUM.TBB`), `realnames.py` (`apply`: the real names of
`SRC/realnames.csv` in `MES.PAC`, through `mbb.py`'s writer) and
`vcdiff.py` (`make` and `apply` for xdelta patches).

### Adding an editor tab

A writer can then get a tab in `editor.py` (stage 5). The tab edits through
the writer's own `set` functions and asks the writer which values each
field allows (as `pbdata.edit_spec` does), so the editor holds no layout of
its own. Its saves must equal the command it logs, byte for byte. Check
that by running the logged command and comparing the files. Test a tab
through its widgets (choose drop-down entries, type into boxes and fire
their events), not by calling its commit functions, and keep the test
window off-screen (`geometry("1280x720+-4000+0")`) so nothing appears on
the user's desktop.

### Checks only a person can make

Some things can only be checked by a person: that an edit shows in the
game (PCSX2), what a screen shows, or how audio sounds. Ask the user to
check (the pending checks are in `TESTING.md`, each naming the disc or
edit to build). Record the result in the doc ("Tested in PCSX2: ...",
"identified by ear", and who saw it; see [Credit](#credit)) and move the
check to the "Tests in PCSX2" section of `DONE.md`. The user doesn't
write code, so don't hand code tasks to them. A new check goes into `TESTING.md`
when a tool can make an edit the game hasn't been seen to take: under
the goal it serves, naming the disc or command to build, and with the
question left in the doc's "Still unknown" list.

### Regression checks

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
  guessing, and list it in the doc's `## Still unknown` section.
- Write plainly: short sentences, tables for field layouts, and a
  `python SRC/...` command showing how to check the claims.
- Keep each fact in one place: the doc of the file or system it
  describes. Other docs link to it rather than repeat it; a folder doc
  (`*_DIR.md`) gives the overview and links to the format docs.
- Write the current state. When a finding is corrected or a tool
  improves, rewrite the text to say what is true now (keep any earlier
  version to a short note); `DONE.md` keeps the history. Remove an open
  question as soon as it is answered, in every doc that lists it.
- Formatting: link another doc with its file name in backticks as the
  link text and a path relative to the linking file, adding `#anchor`
  for a section (as the links in this file do); put commands in code
  blocks tagged `bash` (layouts and diagrams in blocks tagged `text`);
  write table separators as `|---|`; use "–" for an empty table cell,
  and no em dashes (rebuild the sentence with a full stop, comma, colon
  or brackets; don't swap in a spaced hyphen). Wrap prose at about 72
  characters; table rows stay on one line.
- Before you rename, merge or delete a heading, search the tracked files
  for links to its anchor (`git grep -n "NAME.md#anchor"`) and update
  each one.
- People: credit by name, as in [Credit](#credit). In the game's own
  terms the person playing is "you" or "the player" ("your club").
- Write for people. Say what something does in the game before the
  addresses that prove it, keep sentences short, and prefer the game's
  own screen names to internal ones where both exist. Cut filler and
  hype, and use the project's terms the same way everywhere: "the PAL
  release", "the Japanese release", "the executable" (`SLES_541.51`),
  "overlay" (a `DLL/*.REL` file), "the LMASTER Mod" with its editions
  lite, full and max, and "LMAST Realism" (Nexxus's texture pack).

### Structure of a doc

Format and folder docs share one order, so a reader always knows where to
look. Leave out a part that has nothing to say, but keep the order.

1. The two SPDX comment lines, then a title naming the file or system
   and, where it helps, its tool.
2. An opener: what the file does in the game, what loads it, and which
   tool reads and writes it. A few sentences, before any address.
3. The layout, in file order: tables of fields, each claim labelled
   **confirmed** or **empirical**. A folder doc gives an overview table
   of its files and links the format docs.
4. `## Confirmed from the game code`: the Address | Symbol | What it
   shows table, when the layout is traced in the code.
5. `## Editing`: the writer's commands, what it checks, and what it
   leaves alone. `## Tested in PCSX2`: each result seen in the game, with
   what was changed, what showed and who saw it.
6. `## Still unknown`: every open question. Every format and folder doc
   has this section, even when it is short.
7. `## Checking the claims`: `bash` commands that reproduce the claims
   (`info` over the full data, `roundtrip`, a `dis` of the loader).

`LMAST_DATA_CVM_INFO.md` is the exception: it is an outside write-up
kept as it was received.

## Code conventions (`SRC/`)

- The repo is GPL-3.0-or-later (`LICENSE`). Every new `.py` file starts with
  `# SPDX-License-Identifier: GPL-3.0-or-later` and
  `# Copyright (C) 2026 Nexxus Drako Multimedia`, before the docstring.
  Every new `.md`
  file starts with the same two lines as HTML comments (`<!-- ... -->`).
- Each tool is a single standalone script run from the repo root as
  `python SRC/<tool>.py <command> ...`. There is no package, no
  `__init__.py`, and no tests: `regress.py` is the test suite.
- Use the standard library only (`tkinter` for the editors). `PIL` and
  `capstone` are imported lazily inside the functions that need them, so
  other commands still work when they aren't installed. Keep it that way.
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
- A tool that reads the executable or an overlay keeps its PAL address
  constants and looks each one up with `gamever.at(path, addr)` (a
  constant held in an instruction: `gamever.imm(path, func, value)`), so
  it works on the Japanese build too. Find the executable with
  `gamever.exe_path(iso_dir)`, not by the name `SLES_541.51`. Add new
  addresses to `ADDRESSES` in `gamever.py` so `check` covers them.
- Parse with `struct` and little-endian formats (`"<I"`, `"<H"`). Name magic
  numbers and give sizes and offsets in hex.
- Match the comment style of the surrounding code. Comments explain *why* and
  cite the game-code address when the answer comes from the executable.

## Before you finish

- The regression run (see [Regression checks](#regression-checks)) shows
  only the differences you meant. A change to comments or docstrings
  only should show none.
- Every `python SRC/...` command you wrote in a doc runs as written.
- Every link and `#anchor` you wrote or touched resolves, and no heading
  you renamed leaves a broken link behind.
- No em dashes: `grep -rnP "\xe2\x80\x94" *.md DOC SRC` finds none.
- Every new file starts with the two SPDX lines.
- A new tool is in the README's tool table, dependency table and doc
  index, and its checks are in `regress.py`. A new switch is in
  `DOC/LMASTER_MOD.md`; a new edition or group is in `INSTALL.md`; a new
  editor tab or control is in `USAGE.md`.
- The `TODO.md` task is moved to `DONE.md`, `GOALS.md` is updated if a
  status changed, and a check for a person is in `TESTING.md`.
- `git status` shows no game data and no scratch files, and you stage
  files by name (see [Before you start](#before-you-start)).

## Credit

- A doc names who saw a result or made a choice, never just "the user".
  Find out who you are working with from git (`git config user.name`
  and `git config user.email`) and look them up in
  [`CONTRIBUTORS.md`](CONTRIBUTORS.md) for the name they want used:
  "\<name\>'s report, 2026-10-31" for a result they saw in the game,
  "\<name\>'s choice" for a decision they made. The maintainer, Pyra
  Drake, is credited as Nexxus ("Nexxus's report"); don't assume
  that's who you are working with. If git names nobody, or someone not
  in `CONTRIBUTORS.md`, ask how they want to be credited.
- Keep every existing credit exactly as it is when you rewrite a passage.
- Add a person to `CONTRIBUTORS.md` when their finding or report goes
  into a doc.
- Credit yourself on a commit with a `Co-Authored-By` line at the end of
  the message ([`CONTRIBUTING.md`](CONTRIBUTING.md#commits-and-pull-requests)).

## Environment notes

- The primary platform is Windows. Paths in docs and commands use forward
  slashes, and the tools accept either.
- Capstone has no R5900 mode, so `lq`/`sq` and MMI opcodes disassemble
  incorrectly. Don't trust those lines.
- Text encodings: European message text is cp850 and Japanese is cp932 with
  extra kana bytes (see `DOC/MBB_FORMAT.md`). Don't assume ASCII or UTF-8 in
  game data.
- The tools give addresses in the PAL executable and overlays. To read
  the Japanese release, pass `ISO_JP/` and `DAT_JP/`, and keep the PAL
  files in `ISO/` too: `gamever.py` finds each PAL address in the
  Japanese build from them.
- Shell heredocs (`<<'EOF'`) mangle backslashes and quotes on this setup.
  Write a multi-line script or text to a file (in an ignored path or
  outside the repo) and run it, instead of passing it through the shell.
  Big doc edits go through a file editor, not shell commands.
- Docs are UTF-8 and committed with LF line endings, but a working copy
  on Windows may have CRLF. Keep each file's own endings: if an edit with
  a multi-line match fails, make it with a short script that opens the
  file with `newline=""`. On Windows, Python's console is cp1252, so set
  `PYTHONIOENCODING=utf-8` when printing doc text.
- A scan of all of `DAT/` and a full `regress.py run` take a while. Run
  them in the background, or run the checks you need by name prefix.
