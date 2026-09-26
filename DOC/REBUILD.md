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
- `PBDATA_EU.PAC`'s records appear nowhere else on the disc. Other files
  may have copies, though: `.HED` files duplicate their archive's header,
  and `PRELOAD/GAMEFILE*.PAC` bundles some small files. An edit has to be
  made to every copy the game actually reads.

**Tested:**
- Patching an edited `PBDATA_EU.PAC` (three fields of one player) into a
  copy of the Redump image changed exactly 12 bytes of the 3.5 GB image,
  all inside that player's record.
- Patching the original file back gives an image byte-identical to the
  Redump dump.

**Not yet confirmed:** that the game boots and shows the change. That
needs a run in PCSX2 or on hardware.

## Usage

```bash
python SRC/pbdata.py set DAT/PARAM/PBDATA_EU.PAC out/PBDATA_EU.PAC 101 age=30 name=J.Terry
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/PBDATA_EU.PAC=out/PBDATA_EU.PAC
python SRC/patch_disc.py verify modded.iso PARAM/PBDATA_EU.PAC=out/PBDATA_EU.PAC
python SRC/patch_disc.py locate ISO/DATA.CVM PARAM/PBDATA_EU.PAC      # sector, size, byte range
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
