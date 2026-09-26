# Putting edited files back on the disc

This is stage 4 of [`GOALS.md`](../GOALS.md). The first step, same-size
patching, works. Changing a file's size, repacking archives and producing
a distributable patch are still to do.

`SRC/patch_disc.py` writes edited `DAT/` files into a copy of the disc
image (or `DATA.CVM`, or `DATA.ISO`), provided each file keeps its size.
That covers every edit the current writers make: `pbdata.py set`/`import`
(records are fixed-size), `tbb.py replace` when a table keeps its
length, and `mbb.py set`/`import` (each message file keeps its size,
[`MBB_FORMAT.md`](MBB_FORMAT.md#writing)).

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
| `PRELOAD/*.PAC` packs holding copies | 139 | |

The 14 PARAM files with copies are `CLUBRESULT`, `REGULATION`,
`SCHEDULE_LIST`, `STADIUM_DATA`, `TACTICS_FORMATION_SET` and
`TRAINING_LIST` (`.TBB`), `PLRESOURCECOMMON`, `PLRESOURCESIM`,
`PSCCOMMON`, `PSCGAME` and `SCHEDULE_SYSTEM` (`.PAC`), and the
`SCHEDULE_*` `.HED` files. Which copy the game reads in which mode
hasn't been traced. The `PRELOAD` packs are what the overlays load in
bulk (`SIMFILE*` for the season mode), so both copies are assumed to
matter.

`patch` compares each target with the unmodified file in `DAT/` and finds
every unit whose bytes change: the whole file, its header, the entries
it overlaps. It warns about each one's copies, and `--copies` writes the
new bytes into them as well. They are the same size, so this is always
possible. A copy that already holds the new bytes is left alone, so a
second run is harmless. A target can also be a single archive entry,
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
two copies, the mail showed the `MES.PAC` one, so the `MAIL1` copy isn't
what that mail reads ([`MBB_FORMAT.md`](MBB_FORMAT.md#size)).

## Usage

```bash
python SRC/pbdata.py set DAT/PARAM/PBDATA_EU.PAC out/PBDATA_EU.PAC 101 age=30 name=J.Terry
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/PBDATA_EU.PAC=out/PBDATA_EU.PAC
python SRC/patch_disc.py verify modded.iso PARAM/PBDATA_EU.PAC=out/PBDATA_EU.PAC
python SRC/patch_disc.py locate ISO/DATA.CVM PARAM/PBDATA_EU.PAC      # sector, size, byte range
python SRC/patch_disc.py copies DAT PARAM/REGULATION.TBB              # where else these bytes are
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/REGULATION.TBB=out/REGULATION.TBB --copies
```

`patch` copies the image first (use `--in-place` to patch a copy you made
yourself). It refuses a file of a different size, then re-reads every
patched range. Several `<path>=<file>` pairs can go in one run. To undo a
patch, patch the original `DAT/` file back.

Files on the disc outside `DATA.CVM` take a `disc:` prefix and need the
whole disc image, for example `disc:SLES_541.51=out/SLES_541.51` (the
executable with its save names moved to another serial, see
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#separate-saves-for-a-modded-disc)) or
`disc:DLL/SAVEPRG.REL=...`. The outer disc is plain ISO9660, so the same
same-size rule applies.

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

**How `make` encodes.** It reads both images in 8 MiB windows (xdelta3's
default window size). Each window's source segment is the same range of
the source image. Unchanged runs become COPY instructions (default code
table index 19: `VCD_SELF`, size given), and changed bytes become ADD
instructions (index 1), with equal gaps of up to 16 bytes folded into the
ADD. There's no secondary compression, no custom code table, no
application header, and no checksum. That is the plainest RFC 3284, which
any decoder should accept. A target longer than the source gets windows
without a source segment for the extra bytes.

**How `apply` decodes.** It handles any VCDIFF without secondary
compression or a custom code table: the whole default code table
(including the paired instructions), the NEAR/SAME address cache, RUN,
COPYs that overlap their own output, xdelta3's application header, and
xdelta3's per-window Adler-32, which is checked. Patches made by
`xdelta3 -S none` should therefore apply too.

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
`vcdiff.py apply`. Not yet tried: decoding a patch that xdelta3 made.

**Players need the uncompressed `.iso`.** A patch describes the 3.5 GB
ISO. Applied to a CSO (compressed ISO, which PCSX2 also runs), Delta
Patcher fails with "The file you are trying to patch is not the right
one" (xdelta3: `source file too short: XD3_INVALID_INPUT`). Decompress a
CSO or CHD to ISO first, check it against the Redump hashes, then patch.
The patched ISO can be compressed again afterwards.

A patch holds only the changed bytes, so the game data it carries is
limited to the edit itself (a few dozen bytes for a player edit). Keep
patches out of the repo anyway, like everything built from the disc.

## Still to do

- **Size changes.** Re-lay files in `DATA.ISO`, rewrite the directory
  records, re-encrypt the table of contents (the XOR stream in
  `rofs_decrypt.decrypt_sectors` is its own inverse), fix the `CVMH`/`ZONE`
  lengths, and then the disc's entry for `DATA.CVM`.
- **Archive repacking** for edits inside BINPAC/KC@P entries that change
  size, and PRS recompression.
- **Compressed images.** Players who keep CSO or CHD images have to
  decompress them before patching. `vcdiff.py` could read CSO directly.
