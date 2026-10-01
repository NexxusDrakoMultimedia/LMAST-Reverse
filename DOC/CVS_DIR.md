<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `CVS/`: the developers' version-control files

`DAT/CVS/` and a `CVS/` folder inside each of the 16 data folders hold
the three bookkeeping files of a CVS checkout: 51 files in 17 folders. The
developers burned their working copy of the data repository onto the disc
as it was, so these came along. The game never reads them: no file
manager folder id points at them ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)),
and no code names `ENTRIES`, `REPOSITORY` or `ROOT`. They are worth
keeping in mind for two reasons: they give each file's original name and
last commit date, and they show which files the build made rather than
the developers.

`python SRC/cvs.py info DAT` checks every folder's files against its
`ENTRIES`. `python SRC/cvs.py list DAT/NEWS` lists one folder's entries
with their original names, revisions and dates.

## The files

These are standard CVS files (**empirical**, all 17 folders):

| File | Contents |
|---|---|
| `ROOT` | one line: the `:pserver:` address of the repository, a login on the developers' server. The same in every folder. Not reproduced here |
| `REPOSITORY` | the folder's path in the repository: `fc_euro/Data` at the top, `fc_euro/Data/<Folder>` below it |
| `ENTRIES` | one line per file, `/name/revision/date/options/`, then `D` |

`fc_euro` is the project's internal name; the same name appears in the
code's namespaces (`FC_EURO_COMMON`, `CFcEuro_*`). The top folder's
`ENTRIES` lists the 16 subfolders as `D/0System////` and so on, in the
developers' mixed case: `0System`, `Acrobata`, `Bg`, `Cse`, `Emblem`,
`Event`, `Game`, `Message`, `News`, `Param`, `Player`, `PreLoad`, `Seq`,
`Sound`, `Stadium`, `Test3D`.

In an entry, the name keeps its original case (`NewsMonthFlag.tbb`,
`RootMainSeq.sqb`), which the disc's ISO 9660 names have lost. The date
is the time of the last commit or checkout, in the asctime form
(`Thu Jan 26 12:39:14 2006`, UTC by CVS convention). The options column is
`-kb` (binary) for 2,021 of the 2,029 entries. The other 8 were stored as
text: the `dummy.dat` of `ACROBATA` (9 bytes), `BG`, `EMBLEM`, `MESSAGE`,
`PLAYER` and `STADIUM` (empty), and `CSE`'s `pitch.sta` and `pitch.sto`.

## What the entries show

`python SRC/cvs.py info DAT`:

| Folder | Entries | Dates | Not in CVS |
|---|---|---|---|
| `0SYSTEM` | 21 | Aug 2004 – Jun 2006 | `SAVE_VERSION.DAT` |
| `ACROBATA` | 1 (`dummy.dat`) | Dec 2005 | `ACROBATAPACKFILE.PAC` |
| `BG` | 484 | Mar 2005 – Apr 2006 | |
| `CSE` | 688 | Jul 2004 – Jul 2006 | |
| `EMBLEM` | 13 | Dec 2004 – Feb 2006 | |
| `EVENT` | 4 | Jan 2005 – Mar 2006 | |
| `GAME` | 153 | Feb 2005 – Jul 2006 | `CUTINPACK.BIN`, `CUTINPACK_HEADER.BIN`, `GAMEDATA.BIN` |
| `MESSAGE` | 1 (`dummy.dat`) | Dec 2005 | `MES.PAC` |
| `NEWS` | 11 | Jun 2005 – Jan 2006 | |
| `PARAM` | 33 | Aug 2005 – Jul 2006 | |
| `PLAYER` | 87 | Dec 2004 – Jun 2006 | `FC_EURO_FACEPACK_00`/`01` `.BIN` and `.HED` |
| `PRELOAD` | 1 (`dummy.dat`) | Aug 2005 | all 139 packs |
| `SEQ` | 22 | Aug 2004 – Apr 2006 | |
| `SOUND` | 28 | Aug 2005 – Jan 2006 | |
| `STADIUM` | 319 | Dec 2004 – May 2006 | |
| `TEST3D` | 163 | Nov 2004 – Oct 2005 | |

Every file `ENTRIES` lists is on the disc (**empirical**). The 149 files
that aren't listed look generated: the `PRELOAD` packs and `MES.PAC` are
built from other files ([`PRELOAD_DIR.md`](PRELOAD_DIR.md),
[`MBB_FORMAT.md`](MBB_FORMAT.md)), and the face packs and `CUTINPACK` are
large packed archives. In `ACROBATA`, `MESSAGE` and `PRELOAD` the only
file checked in is `dummy.dat`, presumably there to keep the folder in
CVS. So the build put these files in place after the checkout, and
`ENTRIES` lists only what the developers committed. `SAVE_VERSION.DAT`
and `GAMEDATA.BIN` are also missing from it; they were probably written
by the build too.

The latest dates are July 2006 (`CSE`, `GAME`, `PARAM`), which bounds when
the disc's data was checked out. `TEST3D` stops in October 2005, the
other test-heavy folder `SEQ` keeps its 2004 leftovers (see
[`SEQ_DIR.md`](SEQ_DIR.md)), and `EMBLEM/edit_emblem.tbb` is at revision
1.39.

## For a rebuilt disc

The `CVS/` folders can stay as they are. Nothing reads them, so they
don't need to match edited files.
