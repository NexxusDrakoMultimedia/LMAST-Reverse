<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Contributing to LMAST-Reverse

Thank you for helping. This guide covers how to report a problem, how to
send a change, and what a change needs before it can be merged. It
summarises [`AGENTS.md`](AGENTS.md), which holds the full conventions for
docs and tools. `AGENTS.md` is written for AI assistants but applies to
everyone, so read it when a detail here isn't enough. Everyone taking
part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

The project is maintained by Nexxus (Pyra Drake), who reviews every
change and makes most of the in-game tests. Questions are welcome on the
[LMAST/SFCC English Fan Discord](https://discord.gg/7DNrGye9TZ) or in an
[issue](https://github.com/NexxusDrakoMultimedia/LMAST-Reverse/issues).

## Ways to help

You don't need to write code to help.

| Kind | How |
|---|---|
| Test something in the game | Pick a check from [`TESTING.md`](TESTING.md), which explains how to build the disc and report; each check names the disc or edit to build and the doc its result goes into. Report what you changed, what you saw on screen and the date. A screenshot or a PCSX2 save state helps. You need your own copy of the game and PCSX2 |
| Report a bug | Open an [issue](https://github.com/NexxusDrakoMultimedia/LMAST-Reverse/issues) ([below](#reporting-a-bug)) |
| Share what you know about the game | Gameplay knowledge, screen names, what a menu does, translations of Japanese text. Open an issue or post on the Discord |
| Improve the docs | Fix an error, or answer a question from a doc's `## Still unknown` section. Every format and folder doc has one |
| Write code | A reader or writer for a format, a fix, or a tab in the editor. Start from "Next up" in [`TODO.md`](TODO.md#next-up); [its goals table](TODO.md#the-goals-and-what-each-still-needs) says what is still in the way of each kind of mod change |

## Ground rules

- **No game data in the repo.** The disc image, `ISO/`, `DAT/`, extracted
  files, textures, audio and save files are never committed, and that
  includes large excerpts pasted into docs or issues. Small hex snippets
  and counts are fine. Everyone works from their own copy of the disc.
  The disc folders (`ISO/`, `DAT/`, `ISO_JP/`, `DAT_JP/`), the tools'
  working folders (`mod/`, `.regress/`, `.cache/`, `names/`) and the disc
  images and patches in the repo root (`*.iso`, `*.cso`, `*.zso`,
  `*.chd`, `*.xdelta`) are git-ignored; keep scratch output there or
  outside the repo.
- **Label what you claim.** A layout fact in `DOC/` is either
  **confirmed** (with the game-code address that proves it) or
  **empirical** (inferred from data and checked against every file on
  the disc). A result seen in the game says so ("Tested in PCSX2"), with
  what was changed and what showed. Say what is still unknown instead of
  guessing.
- **Standard library only.** Tools use plain Python 3, with `tkinter` for
  the editors. Pillow and Capstone are optional and imported only inside
  the functions that need them.
- **Writers never change their input.** They write to a new output path.

## Reporting a bug

Please include:

- which tool and command you ran (`python SRC/<tool>.py ...`), and its
  full output, especially any line marked `!!`
- your disc: which release it is (PAL `SLES_541.51` or Japanese
  `SLPM-66316`), and whether `python SRC/extract_disc.py verify <disc.iso>`
  says it matches the Redump dump
- for an in-game problem: the patch or edits applied, the PCSX2 version,
  and what you expected and what happened. A screenshot or a save state
  helps

Don't attach disc images, disc files or extracted game data. Paste the
relevant lines of output instead, or say which file and offset.

## Setting up

Follow [Requirements](README.md#requirements) and
[Setup](README.md#setup) in the README to extract your disc into `ISO/`
and `DAT/`. The Japanese release is optional
([setup](README.md#the-japanese-release-optional)); when it is
extracted, the regression checks also run over it. Then, before
changing anything, record a baseline from a clean checkout:

```bash
python SRC/regress.py bless
```

## Making a change

1. Fork the repository and make a branch from `master`. Check
   `git status` first: other work may be in progress in the same tree.
2. Read the doc for the file or system you are changing, including its
   `## Still unknown` list.
3. Make the change. A new format follows the steps in
   [Workflow for a new format](AGENTS.md#workflow-for-a-new-format): find
   the loader in the game code, write `DOC/<NAME>_FORMAT.md`, write
   `SRC/<name>.py`, run its `info` over all of `DAT/` until it reports no
   problems, and add a check to `regress.py`. A writer also gets a
   `roundtrip` command that re-encodes every file or record and marks any
   difference with `!!`.
4. Run the regression checks:

   ```bash
   python SRC/regress.py run
   ```

   A difference is a regression unless you meant it. If you did, run
   `python SRC/regress.py bless <name>` and say in the commit what
   changed in the output. Never bless to make a failure go away. A `!!`
   line that disappears fails the run too: a fix is fine to bless, but a
   check that stopped running is a regression.
5. Update the records the change touches
   ([Where things are recorded](AGENTS.md#where-things-are-recorded)):
   the README's tool table, dependency table and doc index, the doc's
   open questions, [`TODO.md`](TODO.md) and [`DONE.md`](DONE.md), and
   [`GOALS.md`](GOALS.md) when a folder's or a stage's status changes. A
   change to the mod editor or the save editor updates
   [`USAGE.md`](USAGE.md); a new `--mod` edition or group updates
   [`INSTALL.md`](INSTALL.md), and a new switch
   [`LMASTER_MOD.md`](DOC/LMASTER_MOD.md).
6. Open a pull request against `master`.

A change to an editor tab has two more rules. The tab edits through the
writer's own `set` functions, so the editor holds no layout of its own,
and its saves must equal the command it logs, byte for byte. Test it
through its widgets (choose drop-down entries, type into boxes and fire
their events) in a window kept off-screen, not by calling its commit
functions.

Some changes can only be checked in the game. Say so in the pull
request, and a check goes into [`TESTING.md`](TESTING.md) naming the disc
or edit to build.

## Style

The details are in [`AGENTS.md`](AGENTS.md). The main points:

- Every new `.py` file starts with
  `# SPDX-License-Identifier: GPL-3.0-or-later` and
  `# Copyright (C) 2026 Nexxus Drako Multimedia`; every new `.md` file
  starts with the same two lines as HTML comments.
- Each tool is one standalone script, run from the repo root as
  `python SRC/<tool>.py <command> ...`, with its usage text in the module
  docstring and a hand-rolled `main(argv)`. Tools reuse each other
  (`pac.py`, `tbb.py`, `svr.py`, `sles_disasm.py`) instead of
  reimplementing them. A tool that reads the executable or an overlay
  finds each address through `gamever.py`, so it works on both releases.
- `info` marks every problem with `!!` and nothing else.
- Docs use short sentences and tables, hex addresses with `0x`, exact
  counts from the full data set, and commands in `bash` code blocks.
  They say what is true now, keep each fact in one doc and link to it
  from the others, and use no em dashes.
- A result from the game names who saw it and when, for example
  "Tested in PCSX2 (Nexxus's report, 2026-10-31, `LMAST-test-season.iso`)".
  Use the name the person chose in [`CONTRIBUTORS.md`](CONTRIBUTORS.md).
- Text in game data is not ASCII or UTF-8: European messages are cp850
  and Japanese is cp932 ([`MBB_FORMAT.md`](DOC/MBB_FORMAT.md)). Docs are
  UTF-8 with LF line endings.

## Commits and pull requests

- Write the message in the imperative, saying what the change does, for
  example "Document X format; add x.py reader". A doc and its tool
  usually go in one commit.
- Stage files by name, never `git add -A` or `git add .`.
- Credit co-authors, including AI assistants, with a
  `Co-Authored-By: Name <email>` line at the end of the message.
- In the pull request, say what you tested: the regression run, and any
  in-game check with what showed.

## Using AI assistants

Most of this project was written with Claude, and contributions made
with any AI assistant are welcome. You are responsible for what you
submit: check its claims against the data or the game code, label them
as above, and credit the assistant with a `Co-Authored-By` line. The
project as a whole is declared AI:X on the [0RWX scale](https://0rwx.com/)
([README](README.md#disclaimer)); say in your pull request how you used AI.
[`AGENTS.md`](AGENTS.md) is the file to give your assistant. It also says
what to do when the assistant can't run commands: it should name the
command to run and ask you to paste the output, instead of guessing at
the result.

## Being credited

Everyone who contributes is listed in
[`CONTRIBUTORS.md`](CONTRIBUTORS.md). Add yourself in your pull request,
or say how you would like to be credited (your name, a handle, or not at
all) when you send a finding or test result.

## License

By contributing, you agree that your work is licensed under the GNU
General Public License, version 3 or later ([`LICENSE`](LICENSE)), and
that you have the right to license it that way.
