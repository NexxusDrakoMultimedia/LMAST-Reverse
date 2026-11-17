<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `.lbi`: stadium collision bundles (`lbi.py`)

A stadium's shadows and walls are data, not code. Each stadium row of
`BUILD_STADIUM.TBB` names up to five `GAME/SHADOWCOLLI.PAC` entries (row
bytes 110 to 114, where a shadow may fall) and one `GAME/WALLCOLLI.PAC`
entry (byte 128, the walls), and the game loads them into the stadium
collision object (`CStadiumCollision`, [`STADIUM_DIR.md`](STADIUM_DIR.md)).
Every entry is a `.lbi` file: a small triangle mesh inside an *echidna
link bundle*, the loader's format for data whose pointers are fixed up
when it is loaded. `TEST3D/SHADOWCOLLI.LBI`, a developer's test file, is
the same format. `python SRC/lbi.py` reads and checks all of them.

| File | Entries | Nodes or groups | Triangles |
|---|---|---|---|
| `GAME/SHADOWCOLLI.PAC` | 27, 512 to 18,944 bytes | 70 nodes | 938 |
| `GAME/WALLCOLLI.PAC` | 38, about 9 to 13 KB | 155 groups (3 to 5 per entry) | 6,264 |
| `TEST3D/SHADOWCOLLI.LBI` | 1 file, 1,536 bytes | 4 nodes | 16 |

All three files are byte-identical on the Japanese release (`cmp`).

## The link bundle

**Confirmed** from the loader (table below). A bundle is a block of
words, all little-endian:

| Offset | Holds |
|---|---|
| `0x00` | `0xffffffff`, the first word of a table of section bases that ends at the first zero word. The loader stores the bundle's own address here, so section 0 is the bundle |
| `0x04` | `0`, the end of that table |
| `0x08` | the root pointer, `0x11` here |
| `0x0c` | a pointer to the fixup list |
| `0x10` | a pointer to the object, `0x15` here |
| `0x14` | the object |
| after the object | the fixup list: pointers to every place that holds a pointer, ended by a zero word, then zero padding to the end of the file |

A pointer is tagged. Bit 0 is set until it is fixed up. The top six bits
pick a section from the base table, and bits 2 to 25 (`0x03fffffc`) are the
offset inside it, so `0x11` is section 0, offset `0x10`. `LINK_FixupPointers`
walks the fixup list and replaces each tagged pointer it finds with the
section base plus the offset. Here the list has a single entry, `0x11`: the
word at `0x10`, the pointer to the object. Everything else in the file is
plain data and has no pointers to fix.

## The object

**Empirical**, checked by `python SRC/lbi.py info DAT` over all 66 files,
where every group and triangle uses the bytes up to the fixup list
exactly.

| Offset | Size | Holds |
|---|---|---|
| `+0x00` | 6 floats | bounding box of the whole mesh: minimum x, y, z, then maximum x, y, z |
| `+0x18` | u32 | the number of nodes (`SHADOWCOLLI`) or groups (`WALLCOLLI`) that follow |

Each node or group:

| Size | Holds |
|---|---|
| u32 | the header. `SHADOWCOLLI`: `0x80000000` plus the triangle count. `WALLCOLLI`: the triangle count |
| 6 floats | the bounding box of its triangles (every vertex lies inside it, to 1 unit) |
| u32 | a colour-like word: `0x969696ff` (a grey) in the shadow files, and five values in the wall files (`0x0000ffff`, `0x00ff00ff`, `0xfe0000ff`, `0xff00ffff`, `0xffff00ff`: strong primary colours, as if each group had a debug-draw colour) |
| triangles | as below |

A `SHADOWCOLLI` triangle is `0x44` bytes:

| Offset | Size | Holds |
|---|---|---|
| `+0x00` | 3 floats | plane normal, exactly unit length in all 954 shadow triangles (the pack's 938 and the test file's 16); (0, 1, 0), a horizontal plane, in the entry read by hand |
| `+0x0c` | float | plane distance `d`: for every vertex, normal . vertex + `d` = 0 (exact in all 954) |
| `+0x10` | u32 | a flag, 1 in the entry read by hand |
| `+0x14` | 9 floats | three vertices, x, y, z each |
| `+0x38` | 3 u32 | `0xffffffff` or `0xffffff00` in the entries read by hand, and other values in the same style: they look like a colour per vertex (opaque or fully transparent white, which would fade a shadow's edge) |

A `WALLCOLLI` triangle is `0x38` bytes: the same normal, `d`, flag and
three vertices, without the three trailing words. The normal is unit
length in all 6,264 and the plane equation holds to 0.001. The flag is 1
in 4,554 triangles, 0 in 1,062 and 2 in 648. In `WALLCOLLI.PAC` entry 3,
read by hand, a wall is a vertical rectangle of two triangles 1,000 units
long and 21.87 high, and the box runs to about 830 either way.
`SHADOWCOLLI.PAC` entry 2, the smallest, is two flat rectangles (y = 0;
the first spans x from -630 to 631 and z from 375 to 546), four
triangles in all.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `SLES 0x11bd88`, `0x11bda0` | `CLoader::l_analysis_lbi`, `l_realize_lbi` | the loader's LBI type: `l_realize_lbi` runs the loaded block through `LINK_InitBundle` (call at `0x11be18`) |
| `SLES 0x11be68`, `0x11be88` | `l_analysis_pack_lbi`, `l_realize_pack_lbi` | the same for an LBI taken from a pack |
| `SLES 0x14e5a8` | `echidna::LINK_InitBundle` | stores the bundle address in its first word (`sw $v0, ($v0)` at `0x14e5b8`), then calls the fixup |
| `SLES 0x14e490` | `echidna::LINK_FixupPointers` | skips the section table to its zero word, reads the root (bit 0 set means "not yet fixed up"), then walks the fixup list and fixes each pointer it names |
| `SLES 0x14e438` | (helper, unnamed) | the pointer rule: `table[value >> 26] + (value & 0x03fffffc)` |
| `SLES 0x14e460` | `echidna::LINK_GetBundleStart` | walks to the first zero word and returns the word after it |
| `SLES 0x335858` | `CLbiDataHandle::get_lbi_data` | returns the handle's `+0x90` field, the loaded bundle |

## Editing

There is no writer. A bundle is simple enough to rebuild (the header
words, the object and a one-entry fixup list), but the meaning of the
flag and colour words is not known, so the tool only reads.

## Still unknown

- Which entry belongs to which stadium (the `BUILD_STADIUM.TBB` rows give
  entry numbers, [`STADIUM_DIR.md`](STADIUM_DIR.md)), and what the shadow
  entries a stadium lists (up to five) are for one after another.
- What `CStadiumCollision` does with the triangles: how a shadow or a wall
  is tested, and which fields it reads. The nodes' boxes are real bounds,
  so a box test comes first, but the code that reads them was not traced.
- The flag word (shadow: 1; wall: 0, 1 or 2), the colour-like words per
  node, group and shadow vertex, and the five values of the group word in
  the wall files.

## Checking the claims

```bash
python SRC/lbi.py info DAT                                    # 66 entries: look for !!
python SRC/lbi.py list DAT/GAME/WALLCOLLI.PAC                 # one line per entry, with its box
python SRC/sles_disasm.py ISO/SLES_541.51 dis l_realize_lbi   # the loader
python SRC/sles_disasm.py ISO/SLES_541.51 addr 14e438 10      # the pointer rule
python SRC/sles_disasm.py ISO/SLES_541.51 dis LINK_FixupPointers
```
