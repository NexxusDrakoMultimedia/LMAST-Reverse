<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Contributing to LMAST-Reverse

Thank you for helping. This guide covers how to report a problem, how to
send a change, and what a change needs before it can be merged. The full
conventions for docs and tools are in [`AGENTS.md`](AGENTS.md); it is
written for AI assistants but applies to everyone. Everyone taking part
follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to help

You don't need to write code to help.

| Kind | How |
|---|---|
| Test something in the game | pick a check from section 7 of [`TODO.md`](TODO.md); each names the disc or edit to build. Report what you changed and what you saw on screen |
| Report a bug | open an [issue](https://github.com/NexxusDrakoMultimedia/LMAST-Reverse/issues) (below) |
| Share what you know about the game | gameplay knowledge, screen names, what a menu does, translations of Japanese text. Open an issue or post on the [LMAST/SFCC English Fan Discord](https://discord.gg/7DNrGye9TZ) |
| Improve the docs | fix an error, or answer a question from a doc's `## Still unknown` section |
| Write code | a reader or writer for a format, a fix, or a tab in the editor. Start from "Next up" in [`TODO.md`](TODO.md) |

## Ground rules

- **No game data in the repo.** The disc image, `ISO/`, `DAT/`, extracted
  files, textures, audio and save files are never committed, and that
  includes large excerpts pasted into docs or issues. Small hex snippets
  and counts are fine. Everyone works from their own copy of the disc.
- **Label what you claim.** A layout fact in `DOC/` is either
  **confirmed** (with the game-code address that proves it) or
  **empirical** (inferred from data and checked against every file on
  the disc). A result seen in the game says so: "Tested in PCSX2", with
  what was changed and what showed. Say what is still unknown instead of
  guessing.
- **Standard library only.** Tools use plain Python 3. Pillow and
  Capstone are optional and imported only inside the functions that need
  them.
- **Writers never change their input.** They write to a new output path.

## Reporting a bug

Please include:

- which tool and command you ran (`python SRC/<tool>.py ...`), and its
  full output, especially any line marked `!!`
- your disc: which release it is (PAL `SLES_541.51` or Japanese
  `SLPM-66316`), and whether `python SRC/extract_disc.py verify <disc.iso>`
  says it matches the Redump dump
- for an in-game problem: the patch or edits applied, the PCSX2 version,
  and what you expected and what happened. A screenshot helps

Don't attach disc files or extracted game data.

## Setting up

Follow [Requirements](README.md#requirements) and
[Setup](README.md#setup) in the README to extract your disc into `ISO/`
and `DAT/`. Then, before changing anything, record a baseline from a clean
checkout:

```bash
python SRC/regress.py bless
```

## Making a change

1. Fork the repository and make a branch from `master`.
2. Read the doc for the file or system you are changing, including its
   `## Still unknown` list.
3. Make the change. A new format follows the steps in
   [Workflow for a new format](AGENTS.md#workflow-for-a-new-format): find
   the loader, write `DOC/<NAME>_FORMAT.md`, write `SRC/<name>.py`, run
   its `info` over all of `DAT/`, and add a regression check.
4. Run the regression checks:

   ```bash
   python SRC/regress.py run
   ```

   A difference is a regression unless you meant it. If you did, run
   `python SRC/regress.py bless <name>` and say in the commit what
   changed in the output. Never bless to make a failure go away.
5. Update the records the change touches: the README's tool table and
   doc index, the doc's open questions, and `TODO.md` and `DONE.md`
   ([Where things are recorded](AGENTS.md#where-things-are-recorded)).
   A change to the mod editor or the save editor updates
   [`USAGE.md`](USAGE.md); a new `--mod` switch updates
   [`INSTALL.md`](INSTALL.md).
6. Open a pull request against `master`.

## Style

The details are in [`AGENTS.md`](AGENTS.md). The main points:

- Every new `.py` file starts with
  `# SPDX-License-Identifier: GPL-3.0-or-later` and
  `# Copyright (C) 2026 Nexxus Drako Multimedia`; every new `.md` file
  starts with the same two lines as HTML comments.
- Each tool is one standalone script, run from the repo root as
  `python SRC/<tool>.py <command> ...`, with its usage text in the module
  docstring and a hand-rolled `main(argv)`.
- `info` marks every problem with `!!` and nothing else.
- Docs use short sentences and tables, hex addresses with `0x`, exact
  counts from the full data set, and commands in `bash` code blocks.

## Commits and pull requests

- Write the message in the imperative, saying what the change does, for
  example "Document X format; add x.py reader". A doc and its tool
  usually go in one commit.
- Stage files by name; other work may be in progress in the same tree.
- Credit co-authors, including AI assistants, with a
  `Co-Authored-By: Name <email>` line at the end of the message.
- In the pull request, say what you tested: the regression run, and any
  in-game check with what showed.

## Using AI assistants

Most of this project was written with Claude, and contributions made
with any AI assistant are welcome. You are responsible for what you
submit: check its claims against the data or the game code, label them
as above, and credit the assistant with a `Co-Authored-By` line.
[`AGENTS.md`](AGENTS.md) is the file to give your assistant.

## Being credited

Everyone who contributes is listed in
[`CONTRIBUTORS.md`](CONTRIBUTORS.md). Add yourself in your pull request,
or say how you would like to be credited (your name, a handle, or not at
all) when you send a finding or test result.

## License

By contributing, you agree that your work is licensed under the GNU
General Public License, version 3 or later ([`LICENSE`](LICENSE)), and
that you have the right to license it that way.
