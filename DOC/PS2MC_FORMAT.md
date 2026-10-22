<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# PS2 memory card images (`.ps2`)

How PCSX2 stores a memory card in a single file, so the save tools can
read and write saves on it. PCSX2 also offers *folder* cards: a
directory named `<card>.ps2` holding each save folder as an ordinary
folder (the user's `Pyra.ps2` and `Hax.ps2`). `save.py` reads those
directly; this format is the file kind (`Mcd001.ps2`).

The game doesn't read the card's file system itself: the PS2's memory
card driver does. So nothing here cites the game code. Every claim is
**empirical**: checked on three card images (`Mcd001.ps2` and
`WE9LE.ps2`, 8 MB, and `Twitch.ps2`, 32 MB) with
`python SRC/ps2mc.py info`, which parses every directory and chain and
checks every page's ECC. `python SRC/ps2mc.py roundtrip` writes every
file of those cards back and gets each image identical.

## Pages

An image is a run of pages. Each page is 512 bytes of data and, in
PCSX2's images, a 16-byte spare area: 8 MB of data is 8,650,752 bytes
(16,384 pages of 528). An image of plain 512-byte pages (no spare area)
is read and written too.

The spare area holds 12 ECC bytes (3 for each 128-byte quarter of the
page) and 4 zero bytes. For each quarter, the column parity starts at
0x77 and is XORed with each byte's mask of parities over the bit groups
0x55, 0x33, 0x0f, 0x00, 0xaa, 0xcc, 0xf0. Each byte with odd parity
XORs its index into line parity 1 and the index's complement into line
parity 0 (both start at 0x7f). The three bytes are column, line 0
(masked to 7 bits) and line 1.

| Card | Pages | ECC matches | Erased (data and spare all 0xFF) | Other |
|---|---|---|---|---|
| `Mcd001.ps2` | 16,384 | 9,711 | 6,672 | page 1 |
| `WE9LE.ps2` | 16,384 | 16,367 | 16 | page 1 |
| `Twitch.ps2` | 65,536 | 1,903 | 63,632 | page 1 |

Page 1, the second page of the superblock's cluster, holds 8 bytes and
0xFF on all three cards, with the ECC of an empty page. PCSX2 writes it
that way; `ps2mc.py` never checks or writes it.

## Superblock (page 0)

| Offset | Type | What | On the 8 MB cards |
|---|---|---|---|
| `0x00` | 28 bytes | `Sony PS2 Memory Card Format ` | – |
| `0x1c` | 12 bytes | version | `1.2.0.0` |
| `0x28` | u16 | page size | 512 |
| `0x2a` | u16 | pages a cluster | 2 (1,024-byte clusters) |
| `0x2c` | u16 | pages an erase block | 16 |
| `0x2e` | u16 | – | `0xff00` |
| `0x30` | u32 | clusters on the card | 8,192 (32 MB: 32,768) |
| `0x34` | u32 | first allocatable cluster (`alloc_offset`) | 41 or 49 (32 MB: 137) |
| `0x38` | u32 | allocatable clusters (`alloc_end`) | 8,135 or 8,127 |
| `0x3c` | u32 | root directory's first cluster, allocatable-relative | 0 |
| `0x40`, `0x44` | u32 | the two backup erase blocks, the card's last | 1,023, 1,022 |
| `0x50` | 32 × u32 | indirect FAT clusters (0 unused) | one: 8 or 16 |
| `0xd0` | 32 × u32 | bad blocks | all `0xffffffff` |
| `0x150` | u8 | card type | 2 |
| `0x151` | u8 | flags | `0x2b` |

The allocatable area ends where the backup blocks start: on 8 MB,
`alloc_offset` + `alloc_end` = 8,176 = 1,022 × 8 clusters.

## The FAT

Each indirect cluster holds 256 cluster numbers of FAT clusters,
`0xffffffff` after the last (32 on 8 MB, right after the indirect
cluster, up to `alloc_offset`). Each FAT cluster holds 256 u32 entries,
one for each allocatable cluster, numbered from `alloc_offset`:

| Entry | Meaning | `Mcd001.ps2` |
|---|---|---|
| bit 31 set, `0xffffffff` | in use, the end of a chain | 102 |
| bit 31 set, otherwise | in use, next cluster in the low 31 bits | 3,757 |
| `0x7fffffff` | free, never used | 3,339 |
| bit 31 clear, otherwise | free, keeping the link it had | 937 |

Every cluster in use belongs to exactly one directory or file on all
three cards.

## Directories

A directory is a chain of 512-byte entries, two to a cluster. The card
has two levels: the root holds the save folders, and each folder holds
files.

| Offset | Type | What |
|---|---|---|
| `0x00` | u16 | mode: `0x8000` exists, `0x2000` hidden, `0x0400`, `0x0080`, `0x0020` directory, `0x0010` file, `0x0008` protected, `0x0007` read/write/execute |
| `0x04` | u32 | a file's length in bytes; a folder's entry count |
| `0x08` | 8 bytes | created: u8 0, seconds, minutes, hour, day, month, u16 year (Japan time) |
| `0x10` | u32 | first cluster, allocatable-relative |
| `0x14` | u32 | in a folder's `.`: the folder's index in the root |
| `0x18` | 8 bytes | modified, as created |
| `0x20` | u32 | attributes (0 on every entry seen) |
| `0x40` | 32 bytes | name, NUL-padded |

Entries 0 and 1 are `.` and `..`. The root's `.` holds the root's entry
count (20 on `Mcd001.ps2`); its `..` has mode `0xa426`. A folder's count
is in its root entry; its `.` and `..` have length 0. Files are written
with mode `0x8497` and folders `0x8427`; this game's career folders
(`BESLES-54151-G000`) are `0x842f`. An entry without `0x8000` is deleted
and stays counted.

## Writing

`ps2mc.py put` replaces a file or creates one in an existing folder, and
`mkdir` adds a folder. Each writes a new image and never touches the
input:

- A file that changes size gains clusters (the lowest free ones) or frees
  them at the end of its chain (`0x7fffffff`). A cluster keeps its old
  bytes past the end of the data.
- A new entry takes the first deleted slot, or is added at the end; a
  directory that needs another cluster gets one, and its count is
  updated (the root's `.`, or the folder's root entry).
- Every page written gets its ECC. The FAT clusters that changed are
  written back.
- The result is checked like `info` before it is written.

A new file's created and modified times are now (Japan time), and so is
its folder's modified time. `--touch` does the same for a replaced file.

**Tested:** `selftest` builds a blank 8 MB card in memory, then creates,
grows, shrinks and reads back a 646,184-byte save, adds files until its
folder needs a second cluster and folders until the root does. It checks
the card and writes every file back to an identical image. On a copy of
`Mcd001.ps2`, `save.py set ... money=123456` on G000's save, put back with
`put --touch`, read back byte-identical, and `save.py show` read the new
money; 23 bytes of the card changed.

**Not yet tested in PCSX2:** that an edited card loads in the game, and
that a folder or file created by `ps2mc.py` shows in the PS2 browser.

## Still unknown

- What PCSX2's 8 bytes in page 1 are, and what mode bits `0x0400` and
  `0x0080` mean.
- Superblock `0x48`–`0x4f` (0 on every card seen).
- Cards with bad blocks, or other page or cluster sizes, haven't been
  seen; `ps2mc.py` refuses page sizes other than 512 and clusters other
  than 2 pages.

## Checking

```bash
python SRC/ps2mc.py info <card.ps2>
python SRC/ps2mc.py ls <card.ps2> BESLES-54151-G000
python SRC/ps2mc.py roundtrip <card.ps2>
python SRC/ps2mc.py selftest
```
