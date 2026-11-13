<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# DATA.CVM: the encrypted data archive and how the tools open it

Almost all of the game's data is in one file in the disc's root,
`DATA.CVM` (1,970,935,808 bytes on the PAL disc). It is a CRI ROFS
container that holds an ISO9660 image with an encrypted table of
contents. `SRC/rofs_decrypt.py` undoes the encryption and writes a plain
`ISO/DATA.ISO`, and `SRC/extract_disc.py` extracts that into `DAT/`,
which is what almost every other tool reads. The repo layout and the
one-command setup are in the [`README`](../README.md#setup). To check it, run
`python SRC/extract_disc.py list ISO/DATA.ISO` (every file of the
decrypted image).

## Format

`DATA.CVM` was built with "ROFSBLD Ver.1.52" (2003-06-09). A 3-sector
(0x1800 byte) `CVMH`/`ZONE` header is followed by a plain ISO9660 image.
Only the ISO's table of contents is encrypted: the primary volume
descriptor at sector 16 and the directory record sectors reachable from
its root, sectors 16–102 of the ISO on this disc. File contents are
stored as plain bytes, so a file of the same size can be written over the
original's bytes without touching the table of contents
([`REBUILD.md`](REBUILD.md)).

All header values are big-endian. **Empirical**: read from the PAL
`DATA.CVM` with `rofs_decrypt.read_cvm_header` (the fields the tool
parses) and from the header bytes themselves. Only the key's inputs
(`+0x20`–`+0x23`, `+0x25`–`+0x28` and the flag at `+0x30`) are proved by the game code
(next section).

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | char[4] | `CVMH` |
| `0x04` | u64 | length of the rest of the chunk, `0x7f4`; the `ZONE` chunk starts at `0x800` |
| `0x1c` | u64 | size of `DATA.CVM` (`0x757a1800`) |
| `0x20` | u8[4] | the low 32 bits of that size: one input of the key |
| `0x25` | u8[4] | the other input of the key (`07 10 10 29` here); `0x24` is not used |
| `0x30` | u32 | flags. Bit `0x10` = the table of contents is encrypted (the value here) |
| `0x34` | char[4] | `ROFS` |
| `0x38` | char[] | `ROFSBLD Ver.1.52 2003-06-09` |
| `0x88` | u32 | first sector of the ISO image (3, so the header is 3 sectors) |
| `0x800` | char[4] | `ZONE` |
| `0x804` | u64 | length of the rest of the chunk: the file size − `0x80c` |
| `0x82c` | u32 | the ISO's zone sector (3) |
| `0x830` | u64 | the ISO's length in bytes (1,970,929,664, the size of `ISO/DATA.ISO`) |

## The key

The ROFS key is 8 bytes:

```text
5A FB 65 7D 4A 57 5F D5
```

It was first recovered from the running game in PCSX2
([`LMAST_DATA_CVM_INFO.md`](LMAST_DATA_CVM_INFO.md)). The game doesn't
store it; it derives it from the `CVMH` header, and
`rofs_decrypt.header_key` does the same. For this disc that gives exactly
the key above.

### Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x1e1328` | (the mount code) | calls `RSU_GenerateFixedKey` with the `CVMH` sector |
| `0x1e7550` | `RSU_GenerateFixedKey` | with flag `0x10` set in header `+0x30` and no password, builds the 8-byte key |
| `0x1e6f50`, `0x1e6fb8` | (unnamed) | interleave header bytes `+0x25`–`+0x28` with `+0x20`–`+0x23` into 4 byte pairs |
| `0x1e7018` | (unnamed) | replaces each pair with the big-endian 16-bit hash `_calc_one_val(pair, 18973)` |

Header `+0x20`–`+0x23` are the low 32 bits of the CVM's size (table
above), so a `DATA.CVM` of another size has another key.
`patch_disc.py` encrypts the table of contents again with the new key
when it grows the file ([`REBUILD.md`](REBUILD.md#moving-files)).

## The tools

`SRC/rofs_decrypt.py` is a pure-Python reimplementation of roxfan's CRI
ROFS decryption algorithm (`cvm_tool`), so no C++ toolchain is required.
It parses the `CVMH`/`ZONE` header directly rather than hard-coding
sector numbers, decrypts only the table-of-contents sectors, and copies
the rest as it is. Without a key argument it uses `header_key`; an 8-byte
hex key as a third argument overrides that.

`SRC/extract_disc.py` reads ISO9660 directly (the volume descriptor at
sector 16, then the directory records), so nothing needs to be mounted.
Names lose their `;1` version suffix, and each file gets the recording
date from its directory record. Files that already exist with the right
size are skipped, so an interrupted run can be restarted; `--force`
rewrites them.

## Regenerating DATA.ISO and DAT/

`python SRC/extract_disc.py all <disc image>` does every step: it checks
the image against Redump, extracts the disc into `ISO/`, decrypts
`ISO/DATA.CVM` and extracts the result into `DAT/`. To decrypt an
existing `ISO/DATA.CVM` on its own:

```bash
python SRC/rofs_decrypt.py ISO/DATA.CVM ISO/DATA.ISO
```

Then extract it into `DAT/` without mounting anything:

```bash
python SRC/extract_disc.py extract ISO/DATA.ISO DAT
```

Mounting `ISO/DATA.ISO` (for example with PowerShell's `Mount-DiskImage`)
and copying its contents works too.

## Still unknown

- The rest of the `CVMH` and `ZONE` chunks. Only the fields named above
  are decoded, and the tools need no others. The `ZONE` chunk holds
  several more small values between `0x80c` and `0x82b` (for example
  `0x410` and `0x800`) that nothing reads.

## Checking the claims

```bash
python SRC/extract_disc.py verify <disc image>     # size, CRC-32, MD5, SHA-1 against Redump
python SRC/extract_disc.py list ISO/DATA.ISO       # every file of the decrypted image
python SRC/sles_disasm.py ISO/SLES_541.51 dis RSU_GenerateFixedKey
```
