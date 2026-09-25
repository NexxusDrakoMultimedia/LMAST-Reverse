# Let's Make A Soccer Team Reverse Engineering Project

Reverse-engineering notes and tools for the PAL PS2 release of
**Let's Make a Soccer Team!** (`SLES_541.51`).

The repo has two halves:

- [`DOC/`](DOC): one spec per file format, recording what each field means
  and how it was worked out.
- [`SRC/`](SRC): standalone Python tools that parse, check and convert those
  formats.

Every layout claim in the docs is labelled either **confirmed**, with the
game-code address of the routine that proves it, or **empirical**, meaning it
was inferred from the data and checked against every file on the disc.

No game data is included. You need your own copy of the disc.

The long-term aim is GUI tools for editing the game's data to build mods.
See [`GOALS.md`](GOALS.md) for the plan and [`TODO.md`](TODO.md) for the
next tasks.

## Requirements

- Python 3, standard library only for most commands
- `pip install pillow` for the PNG commands (`svr`, `csp`, `zbf`)
- `pip install capstone` for disassembly (`sles_disasm`, `snr2 dis`)

## Setup

The tools expect this layout. `ISO/` and `DAT/` are git-ignored.

```
ISO/    the disc filesystem (SLES_541.51, DLL/, AUDIO/, DATA.CVM, ...)
        + the decrypted DATA.ISO
DAT/    the contents of DATA.ISO, which is what most tools read
SRC/    tools
DOC/    format documentation
```

1. Copy the disc's files, including `DATA.CVM`, into `ISO/`. Leave
   `DATA.CVM` unmodified.
2. Decrypt the archive. Only its ISO9660 table of contents is encrypted, and
   the key recovered from the running game is the default:

   ```bash
   python SRC/rofs_decrypt.py ISO/DATA.CVM ISO/DATA.ISO
   ```

3. Mount `ISO/DATA.ISO` (for example with PowerShell's `Mount-DiskImage`) and
   copy its contents into `DAT/`.

The decryption and key recovery are covered in
[`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md) and
[`LMAST_DATA_CVM_INFO.md`](DOC/LMAST_DATA_CVM_INFO.md).

## Tools

All tools run from the repo root as `python SRC/<tool>.py <command> ...`.
Running a tool with no arguments prints its full usage. Most commands accept
either files or directories, and `info` parses every matching file and marks
anything that doesn't fit the documented layout with `!!`. Search for them
with, for example, `python SRC/tbb.py info DAT | grep '!!'`.

### Game code

| Tool | Reads | Does |
|---|---|---|
| [`sles_disasm.py`](SRC/sles_disasm.py) | `ISO/SLES_541.51` | recovers about 12,600 symbol names from the `.sndata` export table and disassembles with labels, naming the 323 sites that call or reference overlay code (`relocs`) |
| [`snr2.py`](SRC/snr2.py) | `ISO/DLL/*.REL` | parses the SN Systems overlays: header, symbols, relocations, xrefs, annotated disassembly |

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis TblData
python SRC/sles_disasm.py ISO/SLES_541.51 relocs Talk_
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 12e000 40 --sles ISO/SLES_541.51
```

`--sles` resolves an overlay's imports to their addresses in the main
executable.

Capstone has no R5900 mode, so a few EE-only opcodes (`lq`/`sq`, MMI)
disassemble as unrelated MIPS instructions.

### Archives and tables

| Tool | Formats | Doc |
|---|---|---|
| [`pac.py`](SRC/pac.py) | BINPAC `.PAC`/`.MRG`/`.HED`, KC@P headers, PRSH (Sega PRS) | [`PAC_FORMAT.md`](DOC/PAC_FORMAT.md) |
| [`tbb.py`](SRC/tbb.py) | `TBB1`/`TBL1` parameter tables | [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md) |
| [`packdata.py`](SRC/packdata.py) | `etc::PackData` inside KC@P entries (face packs, licensed kits, edit face, cut-ins) | [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md) |

```bash
python SRC/pac.py info DAT
python SRC/pac.py extract DAT/BG/BG_OF_01.MRG out/ --prs
python SRC/tbb.py dump DAT/0SYSTEM/SCHEDULE.TBB 0 --rows 10
python SRC/packdata.py list DAT/PLAYER/PLPACK_HOME.HED 0
```

### Graphics

| Tool | Formats | Doc |
|---|---|---|
| [`svr.py`](SRC/svr.py) | Ninja textures `.SVR`/`.SVM`/`.SVP`, including GS unswizzling | [`SVR_FORMAT.md`](DOC/SVR_FORMAT.md) |
| [`csp.py`](SRC/csp.py) | `.CSP`/`.CSE` 2D screen layouts (sprites, node tree, animation) | [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md) |
| [`zbf.py`](SRC/zbf.py) | `.zbf` depth buffers for pre-rendered rooms | [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md) |
| [`ninja.py`](SRC/ninja.py) | Ninja models and motions `.SNJ`/`.SNO`/`.SNM`/`.SNP`/`.SNA`, loose and inside archives; OBJ export | [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md) |

```bash
python SRC/svr.py png DAT out/textures
python SRC/csp.py png DAT/CSE out/cse --crops
python SRC/zbf.py png DAT/BG out/depth
python SRC/ninja.py obj DAT/PLAYER/M_PLAYER.SNO out/m_player.obj
```

### Sound

| Tool | Formats | Doc |
|---|---|---|
| [`sounddat.py`](SRC/sounddat.py) | `SOUNDDAT.PAC`, commentary `.TBL`, `ps2_DTPK` banks, `FNAME*` clip names | [`GAME_DIR.md`](DOC/GAME_DIR.md) |

```bash
python SRC/sounddat.py info DAT/GAME/SOUNDDAT.PAC
python SRC/sounddat.py extract DAT/GAME/SOUNDDAT.PAC out/sound --wav
```

### Text

| Tool | Formats | Doc |
|---|---|---|
| [`mbb.py`](SRC/mbb.py) | `MESSAGE/MES.PAC` and its `MBB1` message files, all 7 language slots | [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md) |

```bash
python SRC/mbb.py info DAT/MESSAGE/MES.PAC
python SRC/mbb.py dump DAT/MESSAGE/MES.PAC --cat 35002 --lang 1
python SRC/mbb.py csv DAT/MESSAGE/MES.PAC messages.csv
```

The CSV has one row per message and one column per language. Control codes
appear as tags such as `{var:1:7}` and `{color:4}`.

### Event data

| Tool | Formats | Doc |
|---|---|---|
| [`evsdatabin.py`](SRC/evsdatabin.py) | `EvsDataBin_{EVENT,NEWS,MAIL}.bin` (the shipping event tables) | [`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md) |
| [`eventdata_turn.py`](SRC/eventdata_turn.py) | `EVENTDATA_TURN.TBB` (unused prototype) | [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md) |

Both write CSV to a file, or to stdout if no output path is given:

```bash
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_EVENT.BIN event.csv
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_MAIL.BIN mail.csv --text DAT/MESSAGE/MES.PAC
```

With `--text`, each message reference (event dialogue, news headline and
body, mail sender/subject/body) gets a column with its text from `MES.PAC`.

## How the tools fit together

- `csp.py` uses `svr.py` to decode the textures inside CSP packs.
- `zbf.py` uses `pac.py` to read depth buffers directly from `BG_*.MRG`
  archives.
- `eventdata_turn.py` uses `tbb.py` for the table container.
- `packdata.py` uses `pac.py` to find KC@P entries and expand PRSH.
- `ninja.py` uses `pac.py` to check the Ninja entries inside `.PAC`/`.MRG`/
  `.HED` archives.

The disassemblers connect to the format tools through the docs. The usual
workflow is:

1. Find the routine that loads a file in `SLES_541.51` or an overlay.
2. Record the layout it implies, with addresses, in `DOC/`.
3. Implement it in `SRC/`.
4. Run `info` over all of `DAT/` to check it.
5. Add it to [`regress.py`](SRC/regress.py), which runs every tool's check
   and compares the output with a saved baseline:

   ```bash
   python SRC/regress.py bless        # once, from a known-good state
   python SRC/regress.py run          # after every change; exit 1 on any difference
   ```

   Baselines are kept in `.regress/`, which is git-ignored because they list
   file names and counts from your disc. When an output change is intended,
   `bless <name>` accepts it.

## Documentation index

| Doc | Covers |
|---|---|
| [`DATA_CVM_EXTRACTION.md`](DOC/DATA_CVM_EXTRACTION.md) | repo layout, regenerating `DATA.ISO` |
| [`LMAST_DATA_CVM_INFO.md`](DOC/LMAST_DATA_CVM_INFO.md) | ROFS key recovery in PCSX2 |
| [`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md) | `DLL/*.REL` overlay format |
| [`PAC_FORMAT.md`](DOC/PAC_FORMAT.md) | BINPAC, KC@P, PRSH |
| [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md) | TBB1/TBL1 tables, symbol recovery from `SLES_541.51` |
| [`SVR_FORMAT.md`](DOC/SVR_FORMAT.md) | textures and GS swizzling |
| [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md) | `DAT/CSE` 2D layouts |
| [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md) | pre-rendered Z buffers |
| [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md) | Ninja (NN) models, skeletons, motions, VU/PX Plus vertex streams |
| [`GAME_DIR.md`](DOC/GAME_DIR.md) | `DAT/GAME`: commentary, sound banks, models |
| [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md) | `DAT/PLAYER`: face packs, licensed kits, `etc::PackData` |
| [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md) | message text, encodings and escape codes |
| [`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md) | club-management event tables |
| [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md) | the unused turn-event prototype |

## Special thanks

- **@tw09627** on the LMAST Discord, who first decrypted `DATA.CVM` with the help of
  ChatGPT and opened up the game's data for this project.
