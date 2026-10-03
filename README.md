<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

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
See [`GOALS.md`](GOALS.md) for the plan, [`TODO.md`](TODO.md) for the
next tasks and [`DONE.md`](DONE.md) for what's finished.

## Disclaimer

100% of the reverse engineering has been done using Claude Opus 5.5. I'm
neither anti-AI nor pro-AI, and I am pro user choice. If you hate genAI with
the passion of a thousand suns, this project is not for you. If you're a
far-right techbro chud, this project is ALSO not for you.

## Requirements

- Python 3, standard library only for most commands (`editor.py` uses
  `tkinter`, which ships with Python)
- `pip install pillow` for the PNG commands (`svr`, `csp`, `zbf`) and the
  textures in `ninja.py`'s exports
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

Put a dump of the disc that matches Redump
([disc 12334](https://redump.info/disc/12334/), SLES-54151 v1.01) in the repo
root, then run:

```bash
python SRC/extract_disc.py all "Let's Make a Soccer Team! (Europe, Australia) (En,Fr,De,Es,It).iso"
```

[`extract_disc.py`](SRC/extract_disc.py) checks the image's size, CRC-32, MD5
and SHA-1 against Redump, extracts the disc filesystem into `ISO/`, decrypts
`ISO/DATA.CVM` into `ISO/DATA.ISO`, and extracts that into `DAT/`. Nothing is
mounted. Re-running skips files that are already there. `*.iso` files in the
repo root are git-ignored.

To do the same by hand:

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
| [`pac.py`](SRC/pac.py) | BINPAC `.PAC`/`.MRG`/`.HED`, KC@P headers, PRSH (Sega PRS); rebuilds BINPACs byte for byte (`roundtrip`, `replace`) | [`PAC_FORMAT.md`](DOC/PAC_FORMAT.md) |
| [`tbb.py`](SRC/tbb.py) | `TBB1`/`TBL1` parameter tables; reads and writes (all 70 files round-trip) | [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md) |
| [`packdata.py`](SRC/packdata.py) | `etc::PackData` inside KC@P entries (face packs, licensed kits, edit face, cut-ins); `names` lists each head's model and texture name | [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md) |
| [`pbdata.py`](SRC/pbdata.py) | player database `PBDATA_*.PAC`: 27,950 players, 3,000 managers, 1,000 scouts (bit-packed records); list, show, CSV; writes edits (`set`, CSV `import`; every record round-trips; `--sles` re-sorts the ranking and patches the executable for rank, position and nationality edits) | [`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md) |
| [`initteam.py`](SRC/initteam.py) | starting divisions, last season's order and computer-team squads (`PLRRSRC_INITTEAMDATA.TBB`, `OTEAMMEMBER.TBB`), with club names; club records, nations and stadiums; edits squad slots (`set`) and club records (`setteam`); every slot and record round-trips | [`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md) |
| [`teaminit.py`](SRC/teaminit.py) | the player's new club (`TEAM_INIT_DATA.TBB`) by league and team style: squad, youth team, staff, staff lists and the rival club, named from the player database; edits records (`set`), round-trips | [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md) |
| [`gamedata.py`](SRC/gamedata.py) | `GAME/GAMEDATA.BIN`: checks the 4,131 records and prints them with the fields the match engine is known to read | [`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md) |
| [`bpb.py`](SRC/bpb.py) | the play books `GAME/PLAYBOOK.BPB` and `COMBINATION.BPB`: checks every play and prints one's paths (players and ball, in metres) | [`BPB_FORMAT.md`](DOC/BPB_FORMAT.md) |
| [`plrcommon.py`](SRC/plrcommon.py) | the common pack `PLRESOURCECOMMON.PAC`: checks all 25 tables (facilities, formations, nations, competitions) and prints any one, with the facility records' build time, upkeep and stadium capacity | [`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md) |
| [`plrsim.py`](SRC/plrsim.py) | the season-mode pack `PLRESOURCESIM.PAC`: checks all 16 entries (cities and weather, nations, affiliations, scouts' exclusives, combinations, free agents, colours, ...) and prints any one, named from the player database; replaces free agents (`setfree`) | [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md) |
| [`schedule.py`](SRC/schedule.py) | season schedule packs `SCHEDULE_{SYSTEM,COMPETITION,TEAM_ENTRY}.PAC`: turns, games, pairings, team sources | [`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md) |
| [`sqb.py`](SRC/sqb.py) | `SQB1` sequencer scripts: the root flow scripts in `SEQ/` and the PwkScript formulas in `PSC*.PAC`; checks every command and label, disassembles with command and module names, re-encodes every script byte for byte (`roundtrip`) and patches a command (`setcmd`); `SQBFILENAME`, `GLOBALMEMORY` | [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md) |
| [`uniform.py`](SRC/uniform.py) | club kits `UNIFORM_LIST.TBB` (designs and colours of every club's kits), the colour clash table `COLOR_TBL.TBB`, the 116 licensed kits' descriptors (`PLPACK` and the executable's copy), and the keeper kit table `UNIFORM_GK.TBB`; edits kits (`set`, `setlicence`, `setexe`, `setgk`; every row round-trips) | [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md) |
| [`stadium.py`](SRC/stadium.py) | `DAT/STADIUM`: `.PRI` draw priorities, `BUILD_STADIUM.TBB` (which model each of the 119 stadiums uses), packs per model | [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md) |
| [`system.py`](SRC/system.py) | `DAT/0SYSTEM`: the 77 UI colours, `DETAILFLAG`, the 8 crest, badge and sponsor texture packs (which entry a team id picks), icons | [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md) |
| [`emblem.py`](SRC/emblem.py) | `DAT/EMBLEM`: the club editor's 96-colour palette and its 32/16-colour maps, crest masks, patterns and accessories, flag parts, and how the tables and packs line up | [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md) |
| [`news.py`](SRC/news.py) | `DAT/NEWS`: the newspaper's picture packs (mastheads by league, article pictures, ads) and `NEWSMONTHFLAG` (which months print the best-player rankings) | [`NEWS_DIR.md`](DOC/NEWS_DIR.md) |
| [`acrobata.py`](SRC/acrobata.py) | `DAT/ACROBATA`: the 875 Acroarts event scenes (`ABDA`/`ABRS`, `POF0` pointers, the Ninja and texture resources inside), and the executable's index copy and scene-id table | [`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md) |
| [`cvs.py`](SRC/cvs.py) | the developers' `CVS/` folders: each file's original name, revision and date, and which files the build added | [`CVS_DIR.md`](DOC/CVS_DIR.md) |

```bash
python SRC/pac.py info DAT
python SRC/pac.py extract DAT/BG/BG_OF_01.MRG out/ --prs
python SRC/tbb.py dump DAT/0SYSTEM/SCHEDULE.TBB 0 --rows 10
python SRC/tbb.py replace DAT/PARAM/REGULATION.TBB 0 edited.bin out/REGULATION.TBB
python SRC/packdata.py list DAT/PLAYER/PLPACK_HOME.HED 0
python SRC/schedule.py compe DAT/PARAM 6
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB
python SRC/initteam.py leagues DAT/PARAM
python SRC/pbdata.py list DAT/PARAM/PBDATA_EU.PAC --find terry
python SRC/pbdata.py set DAT/PARAM/PBDATA_EU.PAC out/PBDATA_EU.PAC 101 age=30 ability.13=99
```

### Graphics

| Tool | Formats | Doc |
|---|---|---|
| [`svr.py`](SRC/svr.py) | Ninja textures `.SVR`/`.SVM`/`.SVP`, including GS unswizzling | [`SVR_FORMAT.md`](DOC/SVR_FORMAT.md) |
| [`csp.py`](SRC/csp.py) | `.CSP`/`.CSE` 2D screen layouts (sprites, node tree, animation) | [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md) |
| [`zbf.py`](SRC/zbf.py) | `.zbf` depth buffers for pre-rendered rooms | [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md) |
| [`ninja.py`](SRC/ninja.py) | Ninja models and motions `.SNJ`/`.SNO`/`.SNM`/`.SNP`/`.SNA`, loose and inside archives; OBJ export, animated glTF export | [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md) |

```bash
python SRC/svr.py png DAT out/textures
python SRC/csp.py png DAT/CSE out/cse --crops
python SRC/zbf.py png DAT/BG out/depth
python SRC/ninja.py obj DAT/TEST3D/CAMERON.SNO out/cameron.obj
python SRC/ninja.py obj "DAT/PLAYER/FC_EURO_FACEPACK_00.HED#0.0" out/face.obj
python SRC/ninja.py gltf out/player.gltf DAT/PLAYER/M_PLAYER.SNO "DAT/GAME/PLAYERMOTION.PAC#68:snm"
```

### Sound

| Tool | Formats | Doc |
|---|---|---|
| [`sounddat.py`](SRC/sounddat.py) | `SOUNDDAT.PAC`, commentary `.TBL`, `ps2_DTPK` banks (samples, instruments, and songs as MIDI files or rendered WAVs), `FNAME*` clip names; the executable's sound-bank and music-id tables (`music`) | [`GAME_DIR.md`](DOC/GAME_DIR.md), [`SOUND_DIR.md`](DOC/SOUND_DIR.md) |
| [`afs.py`](SRC/afs.py) | `ISO/AUDIO/*.AFS`: music, commentary, crowd chants and ambience (CRI AFS + ADX); checks every entry, decodes to WAV with loop points | [`AUDIO_DIR.md`](DOC/AUDIO_DIR.md) |

```bash
python SRC/sounddat.py info DAT/GAME/SOUNDDAT.PAC
python SRC/sounddat.py extract DAT/GAME/SOUNDDAT.PAC out/sound --wav
python SRC/sounddat.py songs DAT/SOUND
python SRC/sounddat.py midi DAT/SOUND/MAP01.DAT out/midi
python SRC/sounddat.py music ISO/SLES_541.51 DAT/SOUND
python SRC/afs.py list ISO/AUDIO/BGM.AFS
python SRC/afs.py wav ISO/AUDIO/BGM.AFS out/bgm
```

The MIDI files carry the note data only, with `loopStart`/`loopEnd`
markers. `wav` renders the songs with the banks' own instruments instead.

### Text

| Tool | Formats | Doc |
|---|---|---|
| [`mbb.py`](SRC/mbb.py) | `MESSAGE/MES.PAC` and its `MBB1` message files, all 7 language slots; `vars` reads what fills each variable from `SLES_541.51` and `SIMPRG.REL` | [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md) |

```bash
python SRC/mbb.py info DAT/MESSAGE/MES.PAC
python SRC/mbb.py dump DAT/MESSAGE/MES.PAC --cat 35002 --lang 1
python SRC/mbb.py csv DAT/MESSAGE/MES.PAC messages.csv
python SRC/mbb.py import DAT/MESSAGE/MES.PAC messages.csv out/MES.PAC
python SRC/mbb.py set DAT/MESSAGE/MES.PAC out/MES.PAC 3 2007 1 "Chelsea FC" 3 2007 2 "Chelsea"
```

The CSV has one row per message and one column per language. Control codes
appear as tags such as `{var:1:7}` and `{color:4}`. `import` writes an
edited CSV back (and `set` one or more messages). A file that gets longer
grows into the spare room after it in `MES.PAC` (a median of 1,544
bytes per category and language), and the archive keeps its size
([details](DOC/MBB_FORMAT.md#writing)).

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

The tables aren't the whole event system. Scouting, transfers and loans run
as code-only "procedures" that send MAIL records; see
[`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md). What an EVENT does after its
dialogue (open a screen, start a talk, chain another event) is its scene
type; see [`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md#scene-types).

### Patching the disc

| Tool | Reads | Does |
|---|---|---|
| [`patch_disc.py`](SRC/patch_disc.py) | the disc image, `ISO/DATA.CVM` or `ISO/DATA.ISO` | writes edited `DAT/` files or archive entries back (a file may change size inside its last sector; one that needs more sectors is moved to the end of `DATA.ISO`, re-keying the table of contents and growing the disc image if needed; `PRELOAD` packs are rebuilt around entries that change size), and files outside `DATA.CVM` (`disc:SLES_541.51`, renamed with `--rename`), finds and updates their copies elsewhere on the disc (`copies`, `--copies`), skips the tutorial on test discs (`--skip-tutorial`), boots into the developers' debug menu (`--launcher`), turns the Japanese main sponsor negotiation back on (`--sponsor-negotiation`), finds where each file lives, and checks an image holds given bytes |
| [`preload.py`](SRC/preload.py) | `DAT/PRELOAD`, `ISO/SLES_541.51`, `ISO/DLL/*.REL` | checks every `PRELOAD` pack entry against the file it copies, gives each pack's free room for a rebuild, prints the game's load lists, and says which packs hold a file and which screen loads each (`who`), i.e. where the game reads that file from |

```bash
python SRC/pbdata.py set DAT/PARAM/PBDATA_EU.PAC out/PBDATA_EU.PAC 101 age=30
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/PBDATA_EU.PAC=out/PBDATA_EU.PAC
python SRC/preload.py who DAT 3_1.mbb       # the English club names: read from STATIONMES1.PAC
```

Many files have a copy in a `PRELOAD` pack, and the game reads that copy
whenever the pack is loaded, so an edit must reach both (`--copies`). See
[`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md).

Only the table of contents of `DATA.CVM` is encrypted, so a file that keeps
its size can be written over the original without re-encrypting anything.
A file can grow to the end of its last sector in place. One that needs more
sectors is moved to the end of `DATA.ISO`, and the disc image grows if it
has to. Repacking archives other than `PRELOAD` packs isn't supported yet.
See [`REBUILD.md`](DOC/REBUILD.md).

| Tool | Reads | Does |
|---|---|---|
| [`vcdiff.py`](SRC/vcdiff.py) | two disc images, or an image and a patch | makes and applies xdelta patches (VCDIFF, RFC 3284) in plain Python, for sharing a mod against the Redump image |

```bash
python SRC/vcdiff.py make disc.iso modded.iso mymod.xdelta
```

### Saves

| Tool | Reads | Does |
|---|---|---|
| [`save.py`](SRC/save.py) | a memory-card save folder, `ISO/SLES_541.51`, `ISO/DLL/SAVEPRG.REL` | decrypts and decodes a saved game by running the game's own serializers, shows the date, money, squad, youth team and staff, edits money, your club's status, abilities, fatigue, condition, motivation the pair combinations behind the tactics screen's hearts (`combi`), staff abilities and the manager's dissatisfaction, the candidate lists (`candidates`), the accounts and season plan (`finances`; ad budget, ticket prices and season tickets can be set), and other clubs' friendship and club rank, with each club's reputation text (`clubs`), and re-encodes byte for byte; moves saves to another serial (`serial`, `rename`) so a modded disc keeps its own |

```bash
python SRC/save.py show <card>/BESLES-54151-G003
python SRC/save.py player <card>/BESLES-54151-G003 3
python SRC/save.py set <card>/BESLES-54151-G003 edited.bin money=2000000000 0:all=99
python SRC/save.py serial ISO out PYRA-31396
python SRC/patch_disc.py patch disc.iso modded.iso disc:SLES_541.51=out/PYRA_313.96 disc:SYSTEM.CNF=out/SYSTEM.CNF --rename disc:SLES_541.51=PYRA_313.96
```

See [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md).

### Editor

| Tool | Reads | Does |
|---|---|---|
| [`editor.py`](SRC/editor.py) | `DAT/`, `ISO/`, a mod folder | a window with a tab per kind of data. **People** edits players, managers and scouts in the player database: search by name, id, nationality or club, every named field with its allowed values, unnamed fields read-only. **Clubs** edits the club records (rank, manager, stadium, city, transfer policy) and the computer teams' squads (player, age, shirt, contract). **New club** edits what a new career gets for each league and team style: squad, staff, scouts, youth team, candidate lists and the rival club. **Kits** edits every club's home and away kits, with colour swatches, and the keeper kits made for your club, the rival and the VS teams. **Text** finds any message by category, text or id and edits it in all 7 language slots, refusing an edit that would make its file too big. It saves to a mod folder (`mod/` by default) and writes the matching `python SRC/...` command to `mod/editor.log` |

```bash
python SRC/editor.py open             # the mod folder mod/
python SRC/editor.py open mods/terry  # another mod folder
```

**File > Build disc** (Ctrl+B) writes a modded disc image, an xdelta
patch for sharing, or both: it puts the mod folder's files on a copy of
your disc image (`patch_disc.py patch ... --copies`) and makes the patch
from it (`vcdiff.py make`), showing their output and logging both
commands. For a patch on its own the image is temporary and removed
afterwards. Boxes add `patch_disc.py`'s switches: skip the tutorial,
main sponsor negotiation, and the debug menu. Use the unmodified Redump image as the
original, so the patch applies for everyone; the dialog warns if it isn't.

Each tab edits through a writer's own functions and takes the field names
and ranges from it (`pbdata.edit_spec`), so a file saved by the editor is
byte for byte what the logged command gives. The mod folder keeps each file
under its `DAT/` path, and files from outside `DATA.CVM` under `disc/`
(`mod/disc/SLES_541.51`), which matches `patch_disc.py`'s targets. The
editor reads the mod's copy of a file when there is one, so edits build up
over sessions.

## How the tools fit together

- `csp.py` uses `svr.py` to decode the textures inside CSP packs.
- `zbf.py` uses `pac.py` to read depth buffers directly from `BG_*.MRG`
  archives.
- `eventdata_turn.py` uses `tbb.py` for the table container.
- `packdata.py` uses `pac.py` to find KC@P entries and expand PRSH.
- `ninja.py` uses `pac.py` to check the Ninja entries inside `.PAC`/`.MRG`/
  `.HED` archives.
- `teaminit.py` uses `tbb.py`, and `pbdata.py` for names; `plrsim.py` and
  `plrcommon.py` use `pac.py`, `tbb.py` and `pbdata.py`.
- `mbb.py` uses `pac.py` for `MES.PAC`; `pbdata.py`, `initteam.py`,
  `schedule.py`, `stadium.py` and `system.py` use `pac.py` and `tbb.py`;
  `sqb.py` uses `pac.py`, and `packdata.py` for `COMBINATION2.CSB`.
- `evsdatabin.py --text` uses `mbb.py`.
- `uniform.py` uses `pac.py`, `packdata.py` and `svr.py` for the licensed
  kits, `sles_disasm.py` for the executable's copy, and `initteam.py` for
  club names.
- `editor.py` edits through `pbdata.py` (People), `initteam.py`
  (Clubs), `teaminit.py` (New club), `uniform.py` (Kits) and `mbb.py`
  (Text).
- `save.py` loads the game's serializers with `sles_disasm.py` and
  `snr2.py`, and takes field layouts, names and tables from `pbdata.py`,
  `initteam.py` and `tbb.py`.
- `patch_disc.py` uses `extract_disc.py` and `rofs_decrypt.py` to find files
  in the image and rewrite directory records, `pac.py` to rebuild
  `PRELOAD` packs, and `sqb.py` for `--skip-tutorial`.
- `preload.py` uses `pac.py` for the packs and `MES.PAC`.
- `emblem.py` and `news.py` use `pac.py`, `tbb.py` and `svr.py`;
  `acrobata.py` uses `pac.py`, `ninja.py`, `svr.py`, `snr2.py` and
  `sles_disasm.py`;
  `sounddat.py music` reads the executable through `sles_disasm.py`.

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
| [`REBUILD.md`](DOC/REBUILD.md) | putting edited files back on the disc (in-place patching, size changes inside a file's last sector, copies and rebuilt `PRELOAD` packs), sharing mods as xdelta patches, what's still needed for size changes |
| [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md) | memory-card saves: Blowfish key, header and layout CRC, the ten Pwork blocks, money, date and squad fields, the save-name serial |
| [`LMAST_DATA_CVM_INFO.md`](DOC/LMAST_DATA_CVM_INFO.md) | ROFS key recovery in PCSX2 |
| [`SNR2_FORMAT.md`](DOC/SNR2_FORMAT.md) | `DLL/*.REL` overlay format, the SN DLL loader, `SLES_541.51`'s imports, which overlay each sequencer module lives in, the wild-card module |
| [`SQB_FORMAT.md`](DOC/SQB_FORMAT.md) | `SEQ/*.SQB` and `PSC*.PAC` sequencer scripts: command encoding, argument types, labels, the root and PwkScript command sets, global memory |
| [`GAME_FLOW.md`](DOC/GAME_FLOW.md) | the root scripts as a flow chart: title routes, new game, loading, the season loop, year start, main menu, match day, game over, the event timings |
| [`SPONSOR_NEGOTIATION.md`](DOC/SPONSOR_NEGOTIATION.md) | the Sponsor screen's main sponsor negotiation, switched off in PAL by a stub check, and the `patch_disc.py --sponsor-negotiation` patch that restores it |
| [`PAC_FORMAT.md`](DOC/PAC_FORMAT.md) | BINPAC, KC@P, PRSH, and how the packer laid BINPACs out (the writer) |
| [`TBB_FORMAT.md`](DOC/TBB_FORMAT.md) | TBB1/TBL1 tables, symbol recovery from `SLES_541.51` |
| [`SVR_FORMAT.md`](DOC/SVR_FORMAT.md) | textures and GS swizzling |
| [`CSE_FORMAT.md`](DOC/CSE_FORMAT.md) | `DAT/CSE` 2D layouts |
| [`ZBF_FORMAT.md`](DOC/ZBF_FORMAT.md) | pre-rendered Z buffers |
| [`NINJA_FORMAT.md`](DOC/NINJA_FORMAT.md) | Ninja (NN) models, skeletons, motions, VU/PX Plus vertex streams |
| [`GAME_DIR.md`](DOC/GAME_DIR.md) | `DAT/GAME`: commentary, sound banks, models |
| [`AUDIO_DIR.md`](DOC/AUDIO_DIR.md) | `ISO/AUDIO`: the AFS archives (music, commentary, chants, ambience), AFS and ADX layouts, `0FLIST.DIR` |
| [`PLAYER_DIR.md`](DOC/PLAYER_DIR.md) | `DAT/PLAYER`: face packs, licensed kits, `etc::PackData` |
| [`UNIFORM_FORMAT.md`](DOC/UNIFORM_FORMAT.md) | club kits: `UNIFORM_LIST` bit layout, kit designs and colours, the 96 colours, the `COLOR_TBL` clash table, `UNIFORM_GK` keeper kits |
| [`0SYSTEM_DIR.md`](DOC/0SYSTEM_DIR.md) | `DAT/0SYSTEM`: UI colours, crest/badge/sponsor texture packs and how an id picks an entry, fonts by language, icons, leftovers |
| [`PRELOAD_DIR.md`](DOC/PRELOAD_DIR.md) | `DAT/PRELOAD`: the bulk-load packs, the load lists and folder ids, and which copy of a file the game reads, and rebuilding a pack |
| [`STADIUM_DIR.md`](DOC/STADIUM_DIR.md) | `DAT/STADIUM`: the 10 stadium models, `.PRI` draw priorities, crowds, adverts, `BUILD_STADIUM` |
| [`EMBLEM_DIR.md`](DOC/EMBLEM_DIR.md) | `DAT/EMBLEM`: the club editor's crest and flag parts, its colour palette, the edit tables, and the player-editor tables |
| [`NEWS_DIR.md`](DOC/NEWS_DIR.md) | `DAT/NEWS`: newspaper mastheads, article pictures, ads and cartoons, and the monthly ranking flags |
| [`SOUND_DIR.md`](DOC/SOUND_DIR.md) | `DAT/SOUND`: which bank is which, the executable's bank table, and the music table (music id → song or stream) |
| [`SEQ_DIR.md`](DOC/SEQ_DIR.md) | `DAT/SEQ`: the root sequencer scripts, which are loaded, their CVS history |
| [`TEST3D_DIR.md`](DOC/TEST3D_DIR.md) | `DAT/TEST3D`: test models, debug shapes, test kits, the launcher viewers' data |
| [`ACROBATA_DIR.md`](DOC/ACROBATA_DIR.md) | `DAT/ACROBATA`: the Acroarts event scenes, their chunk layout and resources, the executable's copy of the pack index, scene ids by language |
| [`CVS_DIR.md`](DOC/CVS_DIR.md) | the `CVS/` folders left on the disc: original file names, commit dates, which files the build made |
| [`PARAM_DIR.md`](DOC/PARAM_DIR.md) | `DAT/PARAM`: starting leagues, squads, schedules, which code loads each table |
| [`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md) | the player database: header, bit-packed player/manager/scout records, ability and money tables |
| [`INITTEAM_FORMAT.md`](DOC/INITTEAM_FORMAT.md) | starting leagues and divisions, last season's order, computer-team squads, where club names come from |
| [`TEAMINIT_FORMAT.md`](DOC/TEAMINIT_FORMAT.md) | the player's new club: what the league and team style choose (squad, youth team, staff, rival club) |
| [`GAMEDATA_FORMAT.md`](DOC/GAMEDATA_FORMAT.md) | `GAME/GAMEDATA.BIN`'s 0x30-byte records (partial) and the unread `AI_PARAM.BIN` |
| [`BPB_FORMAT.md`](DOC/BPB_FORMAT.md) | the match AI's play books: records of player and ball paths, point coordinates, play ids |
| [`PLRESOURCECOMMON_FORMAT.md`](DOC/PLRESOURCECOMMON_FORMAT.md) | the common resource pack: facility records (build time, upkeep, stadium capacity), formation and nation tables, and which code reads each |
| [`PLRESOURCESIM_FORMAT.md`](DOC/PLRESOURCESIM_FORMAT.md) | the season-mode resource pack: what each of its 16 entries holds and which code reads it |
| [`SCHEDULE_FORMAT.md`](DOC/SCHEDULE_FORMAT.md) | the season calendar: schedule UIDs, turns, games, pairings, where entrants come from |
| [`MBB_FORMAT.md`](DOC/MBB_FORMAT.md) | message text, encodings and escape codes, talk-scene body reactions (`{react:N}`) |
| [`EVSDATABIN_FORMAT.md`](DOC/EVSDATABIN_FORMAT.md) | club-management event tables, event ID types, scene types (what happens after a scene), talk types |
| [`EVS_PROCEDURES.md`](DOC/EVS_PROCEDURES.md) | the scouting, transfer and loan procedures (code-only events), scout-list search criteria, squad and loan limits, the 13 regions |
| [`EVENTDATA_TURN.md`](DOC/EVENTDATA_TURN.md) | the unused turn-event prototype |

## License

The code in `SRC/` and the documentation in `DOC/` and this repository are
licensed under the GNU General Public License, version 3 or (at your option)
any later version. See [`LICENSE`](LICENSE). Each file carries an
`SPDX-License-Identifier: GPL-3.0-or-later` header.

This covers only the work in this repository. The game, its disc image and
its data files are not part of it and are not covered by this license.

## Special thanks

- **@tw09627** on the LMAST Discord, who first decrypted `DATA.CVM` with the help of
  ChatGPT and opened up the game's data for this project.
