<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Extracting DATA.CVM

Almost all of the game's data is in one file in the disc's root,
`DATA.CVM`. This page describes its encryption and how the tools undo it.
The repo layout and the one-command setup are in the
[`README`](../README.md#setup).

## Format

`DATA.CVM` is a Konami "ROFSBLD Ver.1.52" container: a 3-sector (0x1800
byte) `CVMH`/`ZONE` header followed by a plain ISO9660 image. Only the
ISO's table of contents is encrypted: the primary volume descriptor at
sector 16 and the directory record sectors reachable from its root,
sectors 16–102 on this disc. File contents are stored as plain bytes.
The 8-byte ROFS key was first recovered from the running game in PCSX2
([`LMAST_DATA_CVM_INFO.md`](LMAST_DATA_CVM_INFO.md)):

```
5A FB 65 7D 4A 57 5F D5
```

**Confirmed since:** the game doesn't store the key; it derives it from
the `CVMH` header, and `rofs_decrypt.header_key` does the same. With
flag `0x10` set in header `+0x30`, `RSU_GenerateFixedKey` (`0x1e7550`,
called from the mount code at `0x1e1328`) interleaves header bytes
`+0x25`–`+0x28` with `+0x20`–`+0x23` into 4 byte pairs (`0x1e6f50`,
`0x1e6fb8`), and `0x1e7018` replaces each pair with the big-endian
16-bit hash `_calc_one_val(pair, 18973)`. For this disc that gives
exactly the key above. Header `+0x20`–`+0x23` are the low bytes of the
CVM's size (`+0x1c`), so a `DATA.CVM` of another size has another key
([`REBUILD.md`](REBUILD.md#moving-files)).

`SRC/rofs_decrypt.py` is a pure-Python reimplementation of roxfan's CRI
ROFS decryption algorithm (`cvm_tool`), so no C++ toolchain is required.
It parses the CVMH/ZONE header directly rather than hard-coding sector
numbers, decrypts just the table-of-contents sectors, and copies the
rest as it is.

## Regenerating DATA.ISO and DAT/

`python SRC/extract_disc.py all <disc image>` does every step. To
decrypt an existing `ISO/DATA.CVM` on its own:

```bash
python SRC/rofs_decrypt.py ISO/DATA.CVM ISO/DATA.ISO
```

Then extract it into `DAT/` without mounting anything:

```bash
python SRC/extract_disc.py extract ISO/DATA.ISO DAT
```

Mounting `ISO/DATA.ISO` (for example with PowerShell's `Mount-DiskImage`)
and copying its contents works too.
