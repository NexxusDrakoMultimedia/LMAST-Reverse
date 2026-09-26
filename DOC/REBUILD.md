# Putting edited files back on the disc

This is stage 4 of [`GOALS.md`](../GOALS.md). The first step, same-size
patching, works. Changing a file's size, repacking archives and producing
a distributable patch are still to do.

`SRC/patch_disc.py` writes edited `DAT/` files into a copy of the disc
image (or `DATA.CVM`, or `DATA.ISO`), provided each file keeps its size.
That covers every edit the current writers make: `pbdata.py set`/`import`
(records are fixed-size) and `tbb.py replace` when a table keeps its
length.

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

## Still to do

- **Size changes.** Re-lay files in `DATA.ISO`, rewrite the directory
  records, re-encrypt the table of contents (the XOR stream in
  `rofs_decrypt.decrypt_sectors` is its own inverse), fix the `CVMH`/`ZONE`
  lengths, and then the disc's entry for `DATA.CVM`.
- **Archive repacking** for edits inside BINPAC/KC@P entries that change
  size, and PRS recompression.
- **Distribution** as xdelta patches against the Redump image (GOALS.md
  stage 6).
