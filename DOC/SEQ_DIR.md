<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/SEQ`: the root sequencer scripts

`DAT/SEQ` (22 files, 37 KB, plus `CVS/`) is folder id **1** in the game's
file manager ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). It holds the root
scripts of the game's sequencer: the scripts that decide which screen
module runs next, from the boot through the season to the match. Their
format, the command sets and the global variables are documented in
[`SQB_FORMAT.md`](SQB_FORMAT.md); this page is the folder overview.

`python SRC/sqb.py info DAT/SEQ DAT/PARAM` checks every script, and
`python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB` lists one.

| File | Kind | Read by | Contents |
|---|---|---|---|
| `SQBFILENAME.TBB` | TBB, 18 × `char[32]` | `0x149f30` | the list of root scripts by id. **confirmed** |
| `GLOBALMEMORY.TBB` | TBB, 25 × 16 bytes | `0x14a050` | the sequencer's global variables. **confirmed** |
| `ROOT*SEQ.SQB` (15) | `SQB1` | `0x14a220`, through `SQBFILENAME` | root scripts 1–15. **confirmed** |
| `PINFOPOINT.SQB` | `SQB1` | the same, id 16 | an older build of `PSCCOMMON.PAC#PscCommon_PinfoPoint.sqb` |
| `A001.SQB` | `SQB1` | nothing | a 2004 test loop |
| `CHECKCLUBEDIT.SQB`, `INFORMATION.SQB` | `SQB1` | nothing | 2004 scripts for command sets the retail game doesn't have |
| `INFORMATION.WPX` | TBB, 4 tables | nothing | floats, not decoded |

The details of each are in [`SQB_FORMAT.md`](SQB_FORMAT.md#files). No
file here has a copy in `PRELOAD` or anywhere else on the disc
(**empirical**). The PwkScript scripts that compute values (`PSC*.PAC`)
are in `PARAM/`, not here ([`PARAM_DIR.md`](PARAM_DIR.md)).

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x149f30`–`0x149fc4` | (sequencer setup) | opens `SqbFilename.tbb` with folder 1 (the virtual open call at `0x149f98`, `$a1` = 1) and reads the table with `TbbData::GetTableDataPtr` |
| `0x14a050`–`0x14a0c4` | the same | opens `GlobalMemory.tbb` with folder 1 |
| `0x14a220`–`0x14a304` | the same | for each `SQBFILENAME` row that isn't `"NULL"`, copies the name and opens it with folder 1 |

So the game reads exactly the 16 scripts named in `SQBFILENAME.TBB`
(ids 1–16). `A001`, `CHECKCLUBEDIT` and `INFORMATION` are never loaded,
and no `.wpx` name appears in the code.

## CVS history

The folder's `CVS/ENTRIES` ([`CVS_DIR.md`](CVS_DIR.md)) shows how much
the root scripts were worked on: `RootMainSeq.sqb` is at revision 1.129,
`RootLauncherSeq.sqb` at 1.106 and `RootClubEditSeq.sqb` at 1.95. Most
root scripts were last committed on 4 February 2006, and `RootEventSeq`,
`RootLauncherSeq` and `RootYearStartSeq` on 27 April 2006. The four
files the game never loads (`A001`, `CheckClubEdit`, `Information.sqb`
and `Information.wpx`) were last committed in 2004, and so was
`PinfoPoint.sqb`, which is loaded. `RootOfficeSeq` and `RootOwnerRoomSeq`
(2005) are the only root scripts not touched in 2006.

## Still unknown

See [`SQB_FORMAT.md`](SQB_FORMAT.md#still-unknown): a few commands, the
command sets of the two 2004 scripts, and `INFORMATION.WPX`.
