# Extracting DATA.CVM

## Repo layout

```
CVM/    Original encrypted ROFS archive(s) straight off the disc (DATA.CVM).
        Never modified. Ignored by git — too large to version.
ISO/    Preservation of the original PS2 disc filesystem (SYSTEM.CNF, DLL,
        DRIVERS, AUDIO, SLES_541.51, ...) plus the decrypted DATA.ISO
        produced from CVM/DATA.CVM.
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

`SRC/rofs_decrypt.py` is a pure-Python reimplementation of roxfan's CRI
ROFS decryption algorithm (`cvm_tool`), so no C++ toolchain is required.
It parses the CVMH/ZONE header directly rather than hard-coding sector
numbers, decrypts just the TOC sectors, and bulk-copies the rest.

## Regenerating DATA.ISO and DAT/

```bash
python SRC/rofs_decrypt.py CVM/DATA.CVM ISO/DATA.ISO
```

Then mount `ISO/DATA.ISO` (e.g. PowerShell `Mount-DiskImage`) and copy
its contents into `DAT/`.
