<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# The Japanese release

*Pro Soccer Club o Tsukurou! Europe Championship* (プロサッカークラブをつくろう!
ヨーロッパチャンピオンシップ), SLPM-66316, v1.05, the Redump dump
[30266](https://redump.info/disc/30266). It came out on 2006-03-01. The PAL
release is dated 2006-07-16 (`DLL/VERSION.DAT`), so the Japanese one is the
earlier build, and the reference for content PAL changed or cut (see
[`LMASTER_MOD.md`](LMASTER_MOD.md)).

## Setting it up

```bash
python SRC/extract_disc.py all "Pro Soccer Club o Tsukurou! Europe Championship (Japan).iso"
```

This checks the image against Redump and extracts it to `ISO_JP/` and
`DAT_JP/` (git-ignored, like `ISO/` and `DAT/`). `DATA.CVM` decrypts with
the same key scheme as PAL.

The tools take the Japanese folders wherever they take a path:
`python SRC/acrobata.py scenes DAT_JP/ACROBATA ISO_JP`,
`python SRC/mbb.py vars DAT_JP/MESSAGE/MES.PAC ISO_JP`. With both folders
present, `python SRC/regress.py run` also runs every check over them as
`jp_<name>`.

The built-in `patch_disc.py` switches (`--skip-tutorial`,
`--sponsor-negotiation`, `--launcher`) are PAL-only. Each one checks the
bytes it replaces and refuses a disc that doesn't hold them.

## How the tools find addresses: `gamever.py`

The tools and docs give addresses in the PAL executable and overlays.
`SRC/gamever.py` finds the same address in another build, using the PAL
files in `ISO/` as the reference:

1. **symbol**: the PAL address has a name in the export tables.
2. **reference**: named functions that load the address with a
   `lui`/`addiu` pair (an overlay: a HI16/LO16 relocation) load the same
   address in the same position in the other build. Functions without a
   symbol get names from their callers (`f>2` is the third function `f`
   calls). The functions must agree. If they don't, the candidate whose
   words look most like the PAL table wins, or nothing does.
3. **bytes**: the PAL bytes, with address fields masked in code, occur
   once in the other file (or as often as in PAL: the same occurrence).
4. **near**: as 2, from an address up to 0x800 bytes away.

`gamever.imm` does the same for constants held in instructions (loop
bounds, table sizes). `python SRC/gamever.py check ISO_JP` lists all 27
addresses the tools use and how each was found. All 27 are found.

Each table's use in a tool checks it a second way (**empirical**, run on
the Japanese disc):

| Tool | Tables | Check |
|---|---|---|
| `acrobata.py scenes` | executable index and scene table, SIMPRG.REL scene names | all 869 index entries match the pack header; every scene's name agrees between the executable and `getAckName` |
| `uniform.py info` | licence and descriptor tables | 116 clubs; none of the 232 descriptors differs from `PLPACK_*.HED` |
| `sounddat.py music` | bank and music tables | every bank names its `SOUND/` file, with the right number of songs or effects |
| `mbb.py vars` | global variables, switch tables, converters | each variable resolves to a function, as in PAL |
| `save.py` | key, Blowfish tables, CRC table, block sizes | same key `sakatsukue`, same Blowfish P-array start |

## Confirmed from the game code

| Address (SLPM_663.16) | Symbol | Compared with PAL |
|---|---|---|
| SIMPRG.REL `0x17010c` | `Msg::SearchGlobalVarHeader` | 0x1b8 global variables (PAL 0x370) |
| `0x202538`, `0x202548` | `MSG_UTIL::CMsgWildCard::getString` | 0x85 converters of 12 bytes `{u32, u32 function, u32 id}` (PAL: 0x10a of 16 bytes, with an argument word) |
| `0x217618` | `plPinfo_KegaRecoverDaysChno` | identical to PAL: the injury messages "two months" and "nine months" are unreachable in both builds (see [`INJURIES.md`](INJURIES.md)) |
| `0x52e998`, `0x52ea68` | injury tables | identical to PAL, kind 6's 1600 included |

The save block sizes differ in block 1 (76,248 bytes against PAL's
76,264), so the layout CRC is `0x16da` (PAL `0xa225`). Saves of one build
can't be loaded by the other. No Japanese save has been decoded yet.

## Differences in the data (empirical)

| What | Japanese | PAL |
|---|---|---|
| Disc root | `HDD/` (install to the PS2 hard disk), `DRIVERS/` adds `ATAD`, `DEV9`, `HDD`, `PFS` | none |
| Commentary | `AUDIO/BC_JPN.AFS` only: 65,501 unnamed clips, 23.4 hours, its entry count sign-extended from 16 bits ([`AUDIO_DIR.md`](AUDIO_DIR.md#afs)) | ten `BC_*.AFS` of 12,899 named clips |
| `DAT/` | 2,029 files | 2,229: the extra 200 are per-language copies in `CSE/`, `GAME/`, `PRELOAD/` and `STADIUM/` |
| `MES.PAC` | 3,647 files. Slots 1–6 hold placeholders (`test`); 45 records of `0_0.mbb` (the salesman) are filler bytes, not text | 3,738 files, all languages translated |
| `GAME/SOUNDDAT.PAC` | 2 commentary slots of 0x51000 bytes (Japanese, two crowd tables), no BCV index; 33 clip tables from 0xa2000 | 12 slots of 0x1d800, 36 clip tables from 0x162000 |
| `PARAM/PLRESOURCESIM.PAC` | 15 entries: no free-agent list. Entry 0's climate, weather and chance tables hold 44, 49 and 27 whole records | 16 entries; 64 records each |
| `PARAM/PBDATA_*.PAC` | play style, wristband, gloves and keeper gloves above PAL's limits | within them |
| `0SYSTEM/SPONSOR_TEXTURE*.PAC` | 233, 231 and 233 entries | 232 each |
| `CSE/GP_PRACTICEICON.CSP` | the practice icons | 0 bytes; PAL loads the per-language `GP_PRACTICEICON0`–`6.CSP` instead |

Each of these is a `!!` line in a `jp_` check, kept as the baseline,
except the commentary, which `afs.py` reads as documented.

## Still unknown

- Why entry 0 of `PLRESOURCESIM.PAC` stops partway through its tables in
  the Japanese build, and whether its code reads fewer records.
- Whether the player-database limits come from the Japanese code (new
  play styles, kit options) or are data PAL corrected.
- The sponsor texture counts, how the game opens `BC_JPN.AFS` (its
  count reads as −35 through `ADXF_GetNumFilesFromAfs`), and which clip
  is which with no name table.
- A Japanese save: the block that changed size, and what `save.py` needs
  to read one.
