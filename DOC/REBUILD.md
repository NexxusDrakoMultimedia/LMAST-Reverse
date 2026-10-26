<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Putting edited files back on the disc

This is stage 4 of [`GOALS.md`](../GOALS.md). Same-size patching works,
and so does a size change that stays inside a file's last sector, which
is enough to rebuild the `PRELOAD` packs around a grown message file. A
file that needs more sectors is moved to the end of `DATA.ISO`
([Moving files](#moving-files)). Self-describing archives can be
rebuilt with entries of another size, their `.HED` copies follow, and
the two archives the executable indexes (`MES.PAC`, the Acrobata pack)
get that index rewritten ([Archives](#archives)). KC@P packs (the
face, player and cut-in packs) are rebuilt with `pac.py replace`, and
PRS-compressed entries can be written again
([`PAC_FORMAT.md`](PAC_FORMAT.md#writing-kcp)).

`SRC/patch_disc.py` writes edited `DAT/` files into a copy of the disc
image (or `DATA.CVM`, or `DATA.ISO`). The sections below go from the
simplest case, a file that keeps its size, to one that has to move.
That covers every edit the writers make: most keep the file's size
(`pbdata.py`, `initteam.py`, `teaminit.py`, `uniform.py`, `plrsim.py`,
`sqb.py setcmd`, and `mbb.py`, whose grown message files use the spare
room in their slot, [`MBB_FORMAT.md`](MBB_FORMAT.md#writing)); `tbb.py
replace`, `leaguesize.py build`, `clubrank.py addrows` and some
`--mod` switches (`third-tier`) can change it.

## Why same-size patching needs no encryption

The disc is plain ISO9660. `DATA.CVM` is an ordinary file in its root.
Inside `DATA.CVM`, a `CVMH`/`ZONE` header (3 sectors) comes before an
ISO9660 image. Only that image's table of contents is encrypted: the
primary volume descriptor at sector 16, and the directory sectors
reachable from the root (16–102 on this disc). File contents are stored
as plain bytes ([`DATA_CVM_EXTRACTION.md`](DATA_CVM_EXTRACTION.md)).

A directory record gives a file's first sector and its size. If the new
file has the same size, it can be written over the old bytes and the
record stays correct, so nothing is re-encrypted. The same holds for the
disc's own directory entry for `DATA.CVM`. The file's byte offset is:

```
disc image:  DATA.CVM extent × 0x800 + iso_start_sector × 0x800 + extent × 0x800
DATA.CVM:                              iso_start_sector × 0x800 + extent × 0x800
DATA.ISO:                                                          extent × 0x800
```

`iso_start_sector` is 3 on this disc (CVMH `+0x7c`). `patch_disc.py`
decrypts the table of contents with `rofs_decrypt.py`'s key to find each
extent. It never writes to the table of contents.

**Checked (empirical):**
- For every file tried, the bytes at the computed offset equal the `DAT/`
  file. `locate` finds all 2,229 files.
- The `CVMH` header has no checksum field. It holds sizes, a date and the
  `ROFSBLD Ver.1.52` string.
- `0FLIST.DIR` in the disc root lists only the `AUDIO/*.afs` files.
- `PBDATA_EU.PAC`'s records and `OTEAMMEMBER.TBB` appear nowhere else on
  the disc. Many other files do have copies; see [Copies](#copies).

**Tested:**
- Patching an edited `PBDATA_EU.PAC` (three fields of one player) into a
  copy of the Redump image changed exactly 12 bytes of the 3.5 GB image,
  all inside that player's record.
- Patching the original file back gives an image byte-identical to the
  Redump dump.

**Confirmed in the game (PCSX2):** a disc patched this way boots, and a
new game shows the edited player (renamed, new weight, leg and ability
bars). So nothing checks the file contents, and the game reads
`PBDATA_EU.PAC` from this one copy. Details are in
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#writing).

## Copies

The same data is often on the disc more than once, and an edit has to
reach every copy the game actually reads. `patch_disc.py copies` and
`patch` find them by indexing `DAT/`: every loose file, every BINPAC
header and every archive entry (54,032 units), by size and SHA-1. Two
units are **copies** if their bytes are identical and their names match
(equal, or one is the tail of a name of 15+ characters, since BINPAC
names are truncated). Identical data under other names, such as shared
stadium parts, is only reported. Compressed entries are compared as
stored, so a copy stored with different compression wouldn't be found.

**Empirical, from the index:**

| What | Count | Example |
|---|---|---|
| Loose files with a copy elsewhere | 325 | `PARAM/REGULATION.TBB` is also entry 9 of all seven `PRELOAD/SIMFILE*.PAC` |
| Archive headers repeated by a `.HED` | 193 | `BG/HUMAN_1000_PALETTE.HED` = the `.MRG`'s header |
| `MES.PAC` message files also in a `PRELOAD` pack | 763 | `100001_0.mbb` is `PRELOAD/SIMLOCALMEM0.PAC` entry 34 |
| `PRELOAD/*.PAC` packs holding copies | 139 | – |

The 14 PARAM files with copies are `CLUBRESULT`, `REGULATION`,
`SCHEDULE_LIST`, `STADIUM_DATA`, `TACTICS_FORMATION_SET` and
`TRAINING_LIST` (`.TBB`), `PLRESOURCECOMMON`, `PLRESOURCESIM`,
`PSCCOMMON`, `PSCGAME` and `SCHEDULE_SYSTEM` (`.PAC`), and the
`SCHEDULE_*` `.HED` files.

**Which copy the game reads (confirmed, and tested in PCSX2).** Both of
them. A screen that loads a `PRELOAD` pack registers its entries by name
and reads them from the pack. Everywhere else the original is read. Some
packs stay loaded all game (`STATIONFILE`, and `STATIONMES` with the club
names), and others only on one screen (`MAIL`, the talk scenes). So
`--copies` can't be narrowed: every copy is read somewhere. The details,
with the loader of every pack, are in [`PRELOAD_DIR.md`](PRELOAD_DIR.md).

A pack and its `.HED` patched together (`leaguesize.py build` writes
both for the schedule packs) are each other's copies: the `.PAC` starts
with the header the `.HED` repeats. `patch` skips a copy that falls
inside a file it writes whole in the same run, once it has checked that
the file's new bytes already hold it, so a pack that grows and moves
isn't also written in place.

`patch` compares each target with the unmodified file in `DAT/` and finds
every unit whose bytes change: the whole file, its header, the entries
it overlaps. It warns about each one's copies, and `--copies` writes the
new bytes into them as well. A copy inside a `PRELOAD` pack can take
new bytes of a different size: the pack is rebuilt
([below](#size-changes-inside-the-last-sector)). Any other copy is a
fixed-size slot, so a unit that changed size is only warned about there.
A copy that already holds the new bytes is left alone, so a second run
is harmless. A target can also be a single archive entry,
`<path>#<index>` or `<path>#<name>`.

Tested on a copy of `DATA.CVM`:
- A one-byte edit to `REGULATION.TBB` with `--copies` wrote all 8
  locations. The whole CVM then differed from the original in exactly 8
  bytes.
- A one-byte edit to `MES.PAC#7` (`100001_0.mbb`) also updated
  `SIMLOCALMEM0.PAC#34`.

Confirmed in PCSX2: an `mbb.py import` edit to the welcome mail
(`563_1.mbb`), patched with `--copies` into `MES.PAC` and
`PRELOAD/MAIL1.PAC#6`, showed in a new game. With different text in the
two copies, the mail showed the `MES.PAC` one when it popped up in a new
game ([`MBB_FORMAT.md`](MBB_FORMAT.md#size)). Opened later from the Mail
screen, the same mail showed the `MAIL1` copy, and the club names showed
the `STATIONMES1` copy rather than `MES.PAC`'s
([`PRELOAD_DIR.md`](PRELOAD_DIR.md#tested-in-pcsx2)).

## Size changes inside the last sector

The game reads a whole file as `(size + 0x7ff) >> 11` sectors
(**confirmed**: `CFileManagerRofs::FileUpdateCore` takes the length from
`ADXF_GetFsizeSct`, `0x307f24`, and reads that many sectors; see
[`PRELOAD_DIR.md`](PRELOAD_DIR.md#confirmed-from-the-game-code)). A file
can therefore grow or shrink as long as it ends in the same sector, and
no other file moves. Only two things change: the file's bytes, and the
size in its directory record.

The directory record sits in the encrypted table of contents.
`patch_disc.py` decrypts the one sector holding it, writes the new size
in both byte orders (ISO9660 `+10` little-endian, `+14` big-endian), and
encrypts the sector again. The XOR stream depends only on the sector
number and the key, so encrypting is the same operation as decrypting.

**Empirical:** the bytes after the end of every file, up to the end of its
last sector, are zero (2,024 of 2,024 files whose size isn't a whole
number of sectors). A file that changes size is written with zeros up to
the end of its last sector, so patching the original back gives the
original image.

This is used for:
- a whole file given as a target with a new size (still inside its last
  sector), and
- `PRELOAD` packs. An entry that changes size, as a `--copies` copy or as
  a `PRELOAD/<pack>#<entry>` target, makes `patch` rebuild the pack with
  `pac.build_binpac` ([`PRELOAD_DIR.md`](PRELOAD_DIR.md#rebuilding-a-pack)).
  The pack's entries are located through the header it has in the image,
  so a second run works on a rebuilt pack.

A file or pack that would need another sector is moved
([below](#moving-files)).

**Tested** on a copy of `DATA.CVM` and in PCSX2, with `STATIONMES1.PAC`
rebuilt around a grown `3_1.mbb` (45,264 to 45,328 bytes): the
re-encrypted directory record is exact (patching the originals back gives
a byte-identical `DATA.CVM`), and both lengthened club names showed in VS
mode Team Selection. The details are in
[`PRELOAD_DIR.md`](PRELOAD_DIR.md#rebuilding-a-pack).

## Archives

An archive entry that changes size can be put on the disc in two ways:
the whole archive as a target (`pac.py replace`, `mbb.py`), or the entry
as a `<path>#<entry>` target. `PRELOAD` packs are rebuilt as before
([above](#size-changes-inside-the-last-sector)). For any other
self-describing archive (`.PAC`, `.MRG`), `patch` rebuilds the archive
as the image holds it with `pac.build_binpac` around the new entries,
and from then on treats it as a whole-archive target:

- **`.HED` copies.** The game loads an archive's `.HED` first and reads
  entries from the archive by the offsets in it
  ([`PAC_FORMAT.md`](PAC_FORMAT.md)). A rebuilt archive's header keeps
  its size (the entry count doesn't change), so `--copies` writes the new
  header into the `.HED` and into any `PRELOAD/GAMEFILE*` copy of it.
- **Indexes in the executable.** Two archives are read through a copy of
  their header held in `SLES_541.51`: `MES.PAC` (`0x34df50`,
  [`MBB_FORMAT.md`](MBB_FORMAT.md#size)) and `AcrobataPackFile.pac`
  (`0x3a3b08`, [`ACROBATA_DIR.md`](ACROBATA_DIR.md)). When either is a
  target on a whole disc image, `patch` finds the table by the records of
  the archive now on the disc (their offsets, and for `MES.PAC` the
  category and language; sizes may differ) and rewrites the records that
  change. The Acrobata loader opens exactly the stored byte range, so any
  change there needs the executable; `MES.PAC` reads whole sectors, so
  files grown inside their slots work with the old sizes. On `DATA.CVM`
  or `DATA.ISO` alone a change the game needs is refused.
- A rebuilt archive that needs more sectors is moved
  ([below](#moving-files)).

Checked on copies of the disc: `PLAYER/NUMBER_00.PAC#0` grown by 4,000
bytes rebuilt the archive (203 sectors, moved), and `NUMBER_00.HED`
equals the new header; `ACROBATAPACKFILE.PAC#3` grown by 64 bytes was
refused on `DATA.CVM` and on the disc image rewrote one index record,
after which the executable's table equals the new header; a grown
`MES.PAC` moved 810 files and rewrote their records. A second run finds
nothing to do in each case.

**Tested in PCSX2** (user report), on two discs:
- `LMAST-test-archives.iso` (11 files moved, the disc grown past its
  spare sectors): `NEWS/NEWS_TITLE.PAC` rebuilt around two mastheads
  grown past their slots, with its `.HED` and the seven
  `PRELOAD/NEWS*.PAC` copies rebuilt and moved, showed Spain's masthead
  in an English career's newspaper. Entry 3 of all eight
  `NUMBER_0n_PRESS.PAC`, number 8's texture recompressed by
  `pac.prs_compress`, showed 8 for shirt 3 in the Uniform Viewer.
  `FC_EURO_FACEPACK_01` (KC@P, data file moved) with entry 0 replaced by
  entry 214's head, recompressed, showed a different head for SATO TEST
  ID 0 (one of the rival's women companions, which fits 214's
  `HUMAN_head_9600`; ID 214 itself couldn't be viewed). The Acrobata
  pack with entry 0 (`BG_CH_00_00`) grown past its sector, so all 874
  later scenes moved and the executable's index was rewritten, played
  its scenes: the logo and title, the club house, and ACROBATA VIEWER's
  club house room.
- `LMAST-test-camps-mes.iso`: `MES.PAC` with `3_6.mbb` grown past its
  slot (later files moved, the executable's index rewritten) and the
  welcome mail's body changed in `MES.PAC` only. The new-game popup
  showed "MOVED FILE TEST.", the Mail screen the original text from
  `PRELOAD/MAIL1.PAC`.

The plain `PLAYER/NUMBER_0n.PAC` and its `.HED` aren't loaded by name;
the game reads the `_PRESS` packs ([`PLAYER_DIR.md`](PLAYER_DIR.md)).

## Moving files

A file that needs more sectors than it has is moved. `patch` writes it
after the last sector of `DATA.ISO` and points its directory record
there. Its old sectors are left as they are, and nothing else moves. A
`PRELOAD` pack that a rebuild makes too big is moved the same way.

**Why the end of `DATA.ISO`.** The layout leaves no other room
(**empirical**, from the disc's two tables of contents):

| Where | Layout |
|---|---|
| `DATA.ISO` | 962,368 sectors. The 2,262 entries (files and directories) start at sector 21 and follow each other with no free sectors between them |
| the disc | `DATA.CVM` (sector 759,893, 962,371 sectors) is the last file. After it come 10,247 zero sectors, then a UDF anchor in the disc's last sector, 1,732,511 |

So `DATA.CVM` can grow by up to 10,247 sectors (about 20 MB) without the
disc changing size. Past that, the disc grows ([below](#growing-the-disc)).

**What changes with `DATA.CVM`'s size.** Everything below is rewritten
by `patch`, and each old value is checked before it's replaced:

| Where | Field |
|---|---|
| `DATA.ISO` PVD `+80`/`+84` | volume space size, in sectors (both byte orders) |
| `CVMH` `+0x1c` | the CVM's size in bytes (u64, big-endian) |
| `ZONE` `+0x04` (CVM `+0x804`) | the `ZONE` chunk's length: the CVM's size − `0x80c` (u64 BE) |
| `ZONE` `+0x30` (CVM `+0x830`) | the ISO's length in bytes (u64 BE) |
| disc ISO9660 record for `DATA.CVM` | size (both byte orders) |
| disc UDF File Entry for `DATA.CVM` (sector 318) | information length `+56`, blocks recorded `+64`, the length of its one allocation descriptor, and the tag CRC and checksum |
| the whole table of contents | encrypted again with the new key (below) |

Two details:
- **UDF quirk.** The mastering tool wrote the full 32-bit length into
  the allocation descriptor, over the two extent-type bits:
  1,970,935,808 is stored as `0x757a1800`. `patch` keeps that form.
- **CVM sector 2.** It holds a short table (`41 00 00 02 …`) with no
  lengths in it, so it is left alone.

**The key changes too (confirmed).** The game derives the ROFS key from
the `CVMH` header, and four of the eight bytes it starts from are the low
bytes of the CVM's size (`RSU_GenerateFixedKey`, `0x1e7550`; see
[`DATA_CVM_EXTRACTION.md`](DATA_CVM_EXTRACTION.md)). A grown `DATA.CVM`
therefore needs its table of contents, PVD through the last directory
sector (16–102), encrypted with a new key. `patch` keeps the edited
sectors decrypted until the end and encrypts all 87 again. Its first
attempt only fixed the lengths, and the game showed a black screen at
boot, even with nothing moved (`DATA.CVM` one sector longer). The
unmodified disc booted in the same PCSX2.

`Image`, `rofs_decrypt.py` and `extract_disc.py` all derive the key from
the header, so they read a rebuilt disc as they read the original.

**A second run.** A file that was moved to the end and needs more sectors
again grows in place, since nothing follows it. Patching the original
file back moves it too (or grows it in place), so a moved file can't be
undone that way. Keep the original image.

**Tested** on copies of `DATA.CVM` and of the whole disc. `PBDATA_EU.PAC`,
grown by 3,000 bytes to 3,168,084 (1,547 sectors, one more than it had),
moved from ISO sector 266,162 to 962,368. Afterwards:
- all 2,229 files of the patched image matched `DAT/`, and the moved
  file matched its new contents;
- `rofs_decrypt.py` decrypted the patched `DATA.CVM` with the key from
  its header (`5AFB619D4BF15FD5`), giving a 963,915-sector ISO;
- the UDF File Entry's tag and CRC checked out, and the UDF anchor and
  the disc's size were unchanged;
- growing it again to 1,550 sectors grew it in place.

**Confirmed in the game (PCSX2).** The whole-disc test booted. The moved
file carried the kit test's renamed England players, and a VS match
listed them as England's starters (GK.Pants1.Hat3.G5, ACole.LongSleeve,
… Rooney.Plain). So the game reads the file from its new sectors.

### Growing the disc

When the moved files don't fit before the anchor, `patch` makes the image
bigger: in whole 16-sector blocks (a DVD ECC block), with the anchor in
the new last sector, and refusing more than a single-layer DVD's
2,295,104 sectors. The disc's size is held in these places (**empirical**,
read from the disc), and each is rewritten with its descriptor's CRC and
checksum:

| Where | Field |
|---|---|
| disc PVD (sector 16) `+80`/`+84` | volume space size, 1,732,512 |
| UDF Partition Descriptor, main and reserve sequence (sectors 34 and 50) `+192` | partition length, 1,732,246: the partition starts at 265 and ends at the anchor |
| UDF Logical Volume Integrity Descriptor (sector 64) | the partition size in its size table |
| UDF end anchor (last sector) | moved to the new last sector, with its tag location; the old one is cleared |

The anchor at sector 256 and the volume descriptor sequences stay where
they are. The user reports that an image with extra fan-work files added,
so bigger than the original, still ran.

**Tested.** A disc with the grown `PBDATA_EU.PAC` and
`PLAYER/FC_EURO_FACEPACK_01.BIN` grown by 25 MB of zeros (6,103 to 18,903
sectors; the game reads it at offsets from its `.HED`) grew from
1,732,512 to 1,742,720 sectors. All 2,229 files matched, every UDF
descriptor's tag, CRC and location checked out, and the sectors between
`DATA.CVM` and the anchor were zero. **Confirmed in PCSX2:** it booted, a
VS match listed the renamed England players, and the referee, whose head
is in the moved face pack, showed his face normally.

## Usage

```bash
python SRC/pbdata.py set DAT/PARAM/PBDATA_EU.PAC out/PBDATA_EU.PAC 101 age=30 name=J.Terry
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/PBDATA_EU.PAC=out/PBDATA_EU.PAC
python SRC/patch_disc.py verify modded.iso PARAM/PBDATA_EU.PAC=out/PBDATA_EU.PAC
python SRC/patch_disc.py locate ISO/DATA.CVM PARAM/PBDATA_EU.PAC      # sector, size, byte range
python SRC/patch_disc.py copies DAT PARAM/REGULATION.TBB              # where else these bytes are
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/REGULATION.TBB=out/REGULATION.TBB --copies
python SRC/patch_disc.py patch disc.iso modded.iso MESSAGE/MES.PAC=out/MES.PAC --copies   # rebuilds PRELOAD packs as needed
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/X.PAC=bigger.pac   # needs more sectors: moved to the end of DATA.ISO
python SRC/preload.py info DAT                                        # each pack's free room
python SRC/patch_disc.py patch disc.iso test.iso PARAM/...=... --skip-tutorial   # test disc without the opening playoffs
```

`--skip-tutorial` is for test discs. It skips the opening playoffs of a
new career (5–10 minutes): the developers' own switch (one word of the
executable) plus edits to three sequencer scripts that run the
playoffs' schedule steps without their matches
([`SQB_FORMAT.md`](SQB_FORMAT.md#skipping-the-tutorial-the-opening-playoffs)).
Tested in PCSX2: the career goes from club creation to the 2006–07
season with real club rankings, the playoff season's money and the
usual sponsors. Start the career in England, or in the nation
`--skip-nation` names. It needs the whole disc image. Running it again
changes nothing.

`patch` copies the image first (use `--in-place` to patch a copy you made
yourself), plans every write against the unmodified image, then writes
and re-reads every patched range. Several `<path>=<file>` pairs can go in
one run. To undo a same-place patch, patch the original `DAT/` files
back, including any `PRELOAD` packs that `--copies` changed (the run
lists them). A moved file can't be undone that way; keep the original
image.

Files on the disc outside `DATA.CVM` take a `disc:` prefix and need the
whole disc image, for example `disc:SLES_541.51=out/SLES_541.51` (an
executable edited by `pbdata.py --sles` or `uniform.py setexe`) or
`disc:DLL/SAVEPRG.REL=...`. `--mod-saves` moves a modded disc's saves
to their own memory-card folders, and every patch of a whole image
prints the executable's PCSX2 CRC (see
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#separate-saves-for-a-modded-disc)). These keep their size: `patch` doesn't
rewrite the outer disc's directory records (or its UDF copies of them).

`--rename disc:<path>=<NAME>` renames an outer file without changing the
name's length. The disc is a UDF bridge (volume descriptors `BEA01` and
`NSR02` after the ISO9660 ones), so the name is in two places, both
unencrypted: the ISO9660 directory record, and a UDF File Identifier
Descriptor (compression id 16, big-endian UTF-16) whose tag carries a
CRC-16/CCITT over the descriptor and a checksum over the tag. `--rename`
checks the old CRC before it rewrites both. There is no Joliet tree.

## Sharing a mod

`SRC/vcdiff.py` turns a patched image into an xdelta patch (VCDIFF, RFC
3284) against the Redump image. It needs only the standard library:

```bash
python SRC/vcdiff.py make  disc.iso modded.iso mymod.xdelta   # prints source/target/patch SHA-1s
python SRC/vcdiff.py apply disc.iso mymod.xdelta modded.iso   # or use xdelta UI / DeltaPatcher
python SRC/vcdiff.py info  mymod.xdelta
```

The editor's **File > Build disc** (`SRC/editor.py`) runs both steps on a
mod folder: `patch_disc.py patch ... --copies` with every edited file, then
`vcdiff.py make` against the original, and warns when the original isn't
the Redump dump. Checked: the patch applied to the Redump image gives the
built disc byte for byte.

**How `make` encodes.** It reads both images in 8 MiB windows (xdelta3's
default window size). Each window's source segment is the same range of
the source image. Unchanged runs become COPY instructions (default code
table index 19: `VCD_SELF`, size given), and changed bytes become ADD
instructions (index 1), with equal gaps of up to 16 bytes folded into the
ADD. There's no secondary compression, no custom code table, no
application header, and no checksum. That is the plainest RFC 3284, which
any decoder should accept. A target longer than the source gets windows
without a source segment for the extra bytes.

**How `apply` decodes.** It handles any VCDIFF without a custom code
table: the whole default code table (including the paired instructions),
the NEAR/SAME address cache, RUN, COPYs that overlap their own output,
source and target (`VCD_TARGET`) windows, patches made without a source,
xdelta3's application header, and xdelta3's per-window Adler-32, which is
checked. It also decodes xdelta3's **secondary compression**, which
compresses each window's data, instruction and address sections (the
Delta_Indicator bits 1, 2 and 4) with the coder named by the byte after
the header indicator:

| Id | Coder | Support |
|---|---|---|
| 2 | LZMA, **xdelta3's default since 3.1** | Python's `lzma`. xdelta3 keeps one xz stream per section kind for the whole patch and flushes it at the end of each window (`xdelta3-lzma.h`), so `apply` keeps three decompressors from window to window |
| 1 | DJW (`-S djw`, `-S djw7`–`djw9` for several tables) | decoded in Python: per-group Huffman tables whose code lengths are themselves MTF and 1-2 run coded, and MTF-coded group selectors (`xdelta3-djw.h`) |
| 16 | FGK (`-S fgk`) | refused with a message; xdelta3 3.2 no longer builds it |

Each compressed section starts with its decoded size as a VCDIFF integer
(`xd3_decode_secondary`). Written from the xdelta3 3.1.0 and 3.2.2
sources, whose coders are the same token for token. xdelta3 3.2's
application header adds an "armor" BLAKE3 hash of the target and source
(`name#<64 hex>`, `xdelta3-main.h`); Python has no BLAKE3, so `info`
shows them and doesn't check them.

**Tested:**
- The Terry mod (two files, 56 changed bytes): a 10,642-byte patch, 423
  windows, 68 bytes of new data. `make` and `apply` take about 6 seconds
  each on the 3.5 GB image, and the applied image is byte-identical to the
  patched one.
- In-memory round trips between files of different sizes (larger,
  smaller, identical, unrelated).
- A hand-built window using RUN, a paired ADD+COPY and a HERE-mode copy
  of the window's own output.

**Confirmed with xdelta3:** Delta Patcher (an xdelta3 front end) applied
the Terry patch to the Redump image. Its output had SHA-1
`69a9b5fef73dc2099fe5900a2ca4a4de169d78c3`, byte-identical to
`vcdiff.py apply`.

**Patches xdelta3 made** (2026-10-24, xdelta3 3.1.0 and 3.2.2, the
official Windows builds). Each of 16 settings (default, `-0`, `-1`, `-9`,
`-S none`/`djw`/`lzma`/`fgk`, `-n`, `-A`, `-N`, `-9 -S djw`, `-9 -S
lzma`, small source and input windows, and no source file) on five pairs
(scattered edits, insertions and deletions, repeated content, shuffled
blocks, and a target past one 8 MiB window), with both versions: every
patch decoded byte for byte except FGK, which is refused. DJW with 2–8
tables (`-S djw7`, `djw9`, with small windows) decoded too. And the real
case: xdelta3 3.2.2 at its defaults (LZMA, armor) made a 20,535-byte patch
from the Redump image to `LMAST-test-full.iso`, and `vcdiff.py apply` gave
SHA-1 `f9f5e94c0887a0d16c50319f2616319a9df47a15`, the same as the built
image, in about 8 seconds.

### Compressed images

A patch describes the 3.5 GB ISO. Applied to a CSO (compressed ISO,
which PCSX2 also runs), Delta Patcher fails with "The file you are trying
to patch is not the right one" (xdelta3: `source file too short:
XD3_INVALID_INPUT`). This project's tools read CSO, ZSO and CHD directly
(`SRC/cso.py`, `SRC/chd.py`, below): `vcdiff.py apply` and `make` take one wherever they take
an image, and `patch_disc.py patch` decompresses one into its output
`.iso` and patches that. The output is always an ISO, which can be
compressed again afterwards.

```bash
python SRC/cso.py check   disc.cso            # SHA-1 of the ISO inside; is it the Redump dump?
python SRC/vcdiff.py apply disc.cso mod.xdelta modded.iso
python SRC/cso.py extract disc.cso disc.iso
```

The formats (maxcso's `README_CSO.md`): a 0x18-byte header (`CISO` or
`ZISO`, header size, ISO size, block size, version, index shift), then
one u32 per block plus one, giving each block's start shifted by the
index shift. CSO v0/v1 blocks are raw deflate, or stored when bit 31 is
set; CSO v2 blocks at least a block long are stored, others LZ4 when bit
31 is set and deflate otherwise; ZSO blocks are LZ4, or stored when bit
31 is set. LZ4 is decoded in Python.

**Tested** (2026-10-24): the user's CSO (CSO v1, 16 KiB blocks, index
shift 1, 2,775,024,620 bytes) decompresses to the Redump SHA-1 in about
22 seconds, and `vcdiff.py apply` from it gave the built image's SHA-1
(`f9f5e94c…` above) in about 40 seconds. maxcso 1.13.0 made CSO v1
(2 KiB, 64 KiB blocks, stored blocks), CSO v2 (deflate, LZ4 only, mixed
with stored blocks, 16 KiB blocks) and ZSO (default, brute-force LZ4, 2
and 16 KiB blocks, all stored) images of a 64 MiB slice of the disc;
each decoded byte for byte, and so did 200 random reads from each. A
maxcso ZSO of the whole disc (index shift 1, 94,882 stored blocks)
decompresses to the Redump SHA-1 in about 65 seconds. `make`, `apply` and
`roundtrip` with CSO inputs on the slice gave the expected SHA-1s.
`patch_disc.py patch --mod injury-value` gave the same image (SHA-1
`6ec16bf93c2427cc3a30f01e36ad4e555aae444d`) from the CSO as from the ISO,
and refuses `--in-place` on a CSO.

**CHD** (`SRC/chd.py`, MAME's format, which PCSX2 also runs) goes through
the same door: `cso.open_image` hands a CHD to `chd.Image`, so every tool
above takes one.

```bash
python SRC/chd.py info  disc.chd             # header, codecs, hunks by codec, metadata
python SRC/chd.py check disc.chd             # every hunk's CRC, the header's data SHA-1, the ISO's SHA-1
python SRC/vcdiff.py apply disc.chd mod.xdelta modded.iso
```

What it reads, from MAME 0.287's sources (`src/lib/util`):

| Part | Layout |
|---|---|
| header | version 5 only, 124 bytes, big-endian: `MComprHD`, header size, version, four codec tags, logical size, map offset, metadata offset, hunk size, unit size, data SHA-1, SHA-1, parent SHA-1 (a parent, delta CHD is refused) |
| map | 16 bytes (map size, first hunk offset, map CRC-16, bit widths), then a Huffman tree of each hunk's compression (16 codes, at most 8 bits, run-length coded lengths) with run codes, then per hunk its length and CRC-16 or a hunk number. The rebuilt 12-byte entries must match the map CRC (`decompress_v5_map`). An uncompressed CHD maps hunks by number |
| hunks | codec 0–3 (the header's tags), stored, or a copy of another hunk; each checked against its CRC-16 |
| codecs | `zlib` raw deflate; `lzma` raw LZMA1 (lc 3, lp 0, pb 2, the dictionary LZMA SDK level 8 picks for the hunk size); `huff` MAME's 8-bit Huffman (the lengths coded by a small 24-code tree); `flac` bare FLAC frames of 16-bit stereo after an `L`/`B` byte-order mark, decoded here; `zstd` through Python 3.14's `compression.zstd`, else refused with a message |
| CD codecs | `cdzl`, `cdlz`, `cdzs`: an ECC bitmap and the base length, then the frames' 2,352 sector bytes (base codec) and 96 subcode bytes (zlib, or zstd). `cdfl`: FLAC of the sectors (big-endian samples), then zlib subcode. Frames in the bitmap get their sync and P/Q ECC rebuilt (`cdrom.cpp`'s tables, which follow `b + 86c` and `((b/2)·43 + 44c) mod 1118 · 2 + b%2`, checked against them) |
| the ISO | a DVD or raw CHD holds the ISO as is; a CD CHD holds 2,448-byte frames, and the ISO is each frame's 2,048 data bytes at the offset its one data track's type gives (`CHT2` metadata: 0 for MODE1 and MODE2_FORM1, 16 for MODE1_RAW, 24 for MODE2_RAW). Several tracks are refused |

**Tested** (2026-10-24, chdman 0.287): on the 64 MiB slice, the default
`createdvd` (lzma, zlib, huff, flac, all four used) and `createcd` (cdlz,
cdzl, cdfl), each codec alone, no compression, hunk sizes of 2, 4 and 16
KiB, a raw CHD, and each CD codec alone: every hunk passed its CRC, the
data SHA-1 matched the header (chdman leaves it zero in an uncompressed
CHD), and the ISO matched the slice. zstd and cdzs give the message on
Python 3.13. The whole disc as a default `createdvd` CHD (2,599,704,206
bytes, 866,256 hunks: Huffman 439,019, zlib 182,253, LZMA 134,005, copies
86,081, FLAC 22,216, stored 2,682) decodes to the Redump SHA-1 in about
13 minutes. From it, `vcdiff.py apply` of the xdelta3 3.2.2 patch gave
`f9f5e94c…`, the built image, and `patch_disc.py patch --mod
injury-value` gave `6ec16bf9…`, the same image as from the ISO and the
CSO (about 13 minutes each).

**Speed.** Huffman and FLAC hunks decode in Python, at about 1.3 and 3.7
ms each, so a CHD that chdman coded mostly with them takes minutes; LZMA
and zlib hunks are fast (C). `chdman extractdvd` is far quicker for a
player who has it.

A patch holds only the changed bytes, so the game data it carries is
limited to the edit itself (a few dozen bytes for a player edit). Keep
patches out of the repo anyway, like everything built from the disc.

## Still to do

- **Dual-layer images.** The disc can grow to a single-layer DVD's
  2,295,104 sectors (about 1.1 GB more). Past that would need a layer
  break.
- **The big face pack.** `FC_EURO_FACEPACK_00.BIN` (1.1 GB) can be
  rebuilt, but if it outgrows its sectors the move needs nearly all the
  room a single-layer disc has left.
- **CHD speed and tracks.** Huffman and FLAC hunks decode slowly in
  Python, and CD CHDs with several tracks aren't read
  ([above](#compressed-images)).
