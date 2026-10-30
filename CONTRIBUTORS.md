<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Contributors

The people, tools and communities who have helped LMAST-Reverse. The
copyright notices in each file name the copyright holder; this file
records who did the work and who made it possible.

## Maintainer

| Name | Role | Contact |
|---|---|---|
| **Pyra Drake**, also known as **Nexxus Drako** (Nexxus Drako Multimedia) | project owner and maintainer; directs the research, runs the in-game tests in PCSX2, and reviews every change. The docs call them Nexxus | [NexxusDrakoMultimedia](https://github.com/NexxusDrakoMultimedia) on GitHub |

## Code and documentation

| Contributor | Contribution |
|---|---|
| **Pyra Drake** (Nexxus) | every commit in the repository, the in-game test results recorded in `DOC/` ("Tested in PCSX2", "Nexxus's report"), the choices behind the LMASTER Mod ("Nexxus's choice"), [LMAST Realism](https://github.com/NexxusDrakoMultimedia/LMAST-Realism), and the project's goals and conventions |
| **Claude** (Anthropic; Claude Opus 5.5, with one commit by Claude Sonnet 5) | the reverse engineering, the docs in `DOC/` and the tools in `SRC/`, written under the maintainer's direction; credited with a `Co-Authored-By` line on each commit it helped write |

The README's [Disclaimer](README.md#disclaimer) explains how AI is used
in this project. To see the commit counts for yourself:

```bash
git shortlog -sne
```

```bash
git log --format="%(trailers:key=Co-Authored-By,valueonly)" | sort | uniq -c
```

## Research

| Contributor | Contribution |
|---|---|
| **@tw09627** on the LMAST Discord | first decrypted `DATA.CVM` (with the help of ChatGPT), which opened up the game's data for this project. The original write-up is kept in [`LMAST_DATA_CVM_INFO.md`](DOC/LMAST_DATA_CVM_INFO.md) |

## Community

- **The [LMAST/SFCC English Fan Discord](https://discord.gg/7DNrGye9TZ)**,
  the English-speaking community of *Let's Make a Soccer Team!* and the
  *Sakatsuku* (SFCC) series, which this project is made for.

## Third-party software

The project builds on these, but includes none of their code. Each keeps
its own license.

| Project | Used for |
|---|---|
| [Python](https://www.python.org/) | every tool in `SRC/`, standard library only, with `tkinter` for the editors |
| [Pillow](https://python-pillow.org/) | the PNG commands (`svr`, `csp`, `zbf`) and the textures in `ninja.py`'s exports (optional) |
| [Capstone](https://www.capstone-engine.org/) | disassembly in `sles_disasm.py` and `snr2.py` (optional) |
| [PCSX2](https://pcsx2.net/) | running the game for the in-game tests, its memory card images and save states |
| [cvm_tool](https://github.com/JayFoxRox/cvm_tool) by JayFoxRox | the first `DATA.CVM` decryption; `rofs_decrypt.py` reimplements its ROFS algorithm in Python ([`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md)) |

## Sister project

[VPF-Reverse](https://github.com/NexxusDrakoMultimedia/VPF-Reverse)
covers *Virtua Pro Football*, which shares this game's engine. Formats
the two games share are documented here first.

## Getting listed

Contributions of any kind are welcome: code, docs, test results from the
game, bug reports, translations or research. See
[`CONTRIBUTING.md`](CONTRIBUTING.md) for how to send one.

- **Code or docs:** add yourself to the right table above in your pull
  request, or ask to be added.
- **Research, tests or reports:** say how you would like to be credited
  (your name, a handle, or not at all) and you will be added here, and
  in the doc that records the finding.
