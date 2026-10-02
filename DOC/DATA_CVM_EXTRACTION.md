<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Extracting DATA.CVM

## Repo layout

```
ISO/    Preservation of the original PS2 disc filesystem (SYSTEM.CNF, DLL,
        DRIVERS, AUDIO, SLES_541.51, ...), including the encrypted ROFS
        archive DATA.CVM (never modified), plus the decrypted DATA.ISO
        produced from it. Ignored by git — too large to version.
DAT/    Plain game data unpacked from DATA.ISO (PLAYER, GAME, EVENT, PARAM,
        etc.) — this is what modding/reverse-engineering work reads from.
SRC/    Reverse-engineering tooling (this project's own scripts).
DOC/    Documentation, including notes recovered from other engineers.
```

## Format

`DATA.CVM` is a Konami "ROFSBLD Ver.1.52" container: a 3-sector (0x1800
byte) `CVMH`/`ZONE` header followed by a plain ISO9660 image. Only the
ISO's table of contents (the primary volume descriptor at sector 16 and
the directory record sectors reachable from its root, sectors 16-102 in
this disc) is encrypted — actual file contents are stored as plain
bytes. See [`LMAST_DATA_CVM_INFO.md`](LMAST_DATA_CVM_INFO.md) for how
the 8-byte ROFS key was recovered from the running game in PCSX2:

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
numbers, decrypts just the TOC sectors, and bulk-copies the rest.

## Regenerating DATA.ISO and DAT/

```bash
python SRC/rofs_decrypt.py ISO/DATA.CVM ISO/DATA.ISO
```

Then mount `ISO/DATA.ISO` (e.g. PowerShell `Mount-DiskImage`) and copy
its contents into `DAT/`.
