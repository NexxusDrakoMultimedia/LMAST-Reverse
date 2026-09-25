# SNR2 overlays (`ISO/DLL/*.REL`)

The game code outside `SLES_541.51` lives in ten SN Systems relocatable
overlays (`GAMEPRG`, `SIMPRG`, `SAVEPRG`, ...). Each one is a MIPS image
**linked at base 0**, so image addresses equal file offsets. After the image
come a symbol table and two relocation lists. The loader adds the load base to
every local reference and patches imports by name.

Everything here is empirical. It holds with no exceptions for all ten
overlays (`python SRC/snr2.py info <REL>` runs the checks). The module-path
strings (`../PS2_EE_Release/gameprg.elf`) show they were converted from ELF.

## Layout

```
0x00      header (0x40 bytes, zero-padded to 0x80)
0x80      code, then data (image continues up to name_off)
          ... symbol-name strings (inside the image)
name_off  module path, NUL-terminated
ext_rel   ext_rel_count × 12  external relocations
sym       sym_count × 12      symbols
loc_rel   packed local relocations, up to loc_rel_end (= EOF)
```

## Header

| Offset | Value (GAMEPRG) | Meaning |
|---|---|---|
| `0x00` | `SNR2` | magic |
| `0x04` | `0x2AE56C` | external relocation table offset |
| `0x08` | `0x253D` | external relocation count |
| `0x0C` | `0x2CA448` | symbol table offset (= `0x04 + 12 × count`) |
| `0x10` | `0x474` | symbol count |
| `0x14` | `0x2AE54C` | module path string, which is also the end of the image |
| `0x18` | `0x20FA68` | function: global constructors (it has GCC `__do_global_ctors`' `-1` count check) |
| `0x1C` | `0x20FA10` | function: global destructors (probable) |
| `0x20` | `0x2CD9B8` | local relocation list offset (= `0x0C + 12 × count`) |
| `0x28` | `0x80` | always `0x80`: start of code |
| `0x2C` | `0x2E518E` | end of local relocations = file size |
| `0x34`, `0x38` | `0x2CD9B8` | always equal to `0x20`. Meaning unknown |
| `0x24`, `0x30`, `0x3C` | 0 | |

There's no BSS beyond the file: every relocated address lands inside the
image.

## Symbols (12 bytes)

```
+0x00 u32 name       image offset of a NUL-terminated (GCC 2.x mangled) name
+0x04 u32 value      image address; 0 for imports
+0x08 u16 hash       low 16 bits of h = h*31 + c over the name
+0x0A u16 kind       1 = import, 2 = export, 3 = weak export
```

Symbol 0 is null. Kind 3 is only used for vtables (`_vt$...`), type-info
functions (`__tf...`) and template/STL instances, i.e. GCC linkonce
definitions. `SLES_541.51`'s `.sndata` export table uses the same
`{name, address, hash | kind << 16}` records, which is how the loader
matches imports.

Imports resolve against:

- the `SLES_541.51` export table: all of GAMEPRG's 1,134 imports, and most
  of every other overlay's
- the exports of `SIMPRG.REL` (and a few of `SAVEPRG.REL`) for the rest, so
  those overlays must be resident first. The imports that go to other
  overlays are CEDITPRG 211, TESTPRG 127, YRSTPRG 59, VSPRG 26, MOVIEPRG 12,
  SIMPRG 3 (from SAVEPRG) and SAVEPRG 1

## External relocations (12 bytes)

ELF `Elf32_Rel` plus an addend:

```
+0x00 u32 offset     image offset of the site
+0x04 u32 info       sym_index << 8 | type
+0x08 u32 addend     almost always 0 (e.g. 0xD0, 0x10000 for a handful)
```

The types are the ELF MIPS numbers: 2 = `R_MIPS_32`, 4 = `R_MIPS_26`
(`jal 0`), 5 = `R_MIPS_HI16`, 6 = `R_MIPS_LO16`. External calls therefore
show up in a raw disassembly as `jal 0` and `lui $x, 0`.

## Local relocations (packed)

These are sites that only need the load base added. The list is a byte
stream:

```
code >= 4:   pos += code & ~3              (delta, multiple of 4, 4..252)
code <  4:   pos  = next u32 (LE)          (absolute; the list is not sorted)
type = code & 3:  0 = LO16, 1 = HI16, 2 = J26 (j/jal), 3 = W32 (data word)
end:         00 00000000
```

Every HI16 site is a `lui` and every J26 site is a `j`/`jal`. LO16 sites
are the immediate of `addiu`, `lw`, `sw`, `lwc1`, `swc1`, `ldc1`, `lbu`, ... As in
ELF, each LO16 pairs with the most recent HI16 in list order, and the stream
reorders sites so that each `lui` comes just before its low halves. The
target is `(hi << 16) + sext(lo)`. That's how `snr2.py xref` finds, for
example, the two loads of the SOUNDDAT offset table at `GAMEPRG:0x248540`
(`0x9BDC`, `0x9C90`).

| Overlay | Local relocs | Ext relocs | Symbols (imp / exp / weak) |
|---|---|---|---|
| CEDITPRG | 3,106 | 2,798 | 653 / 11 / 0 |
| DEBUGPRG | 3,346 | 390 | 97 / 6 / 0 |
| GAMEPRG | 76,197 | 9,533 | 1,134 / 5 / 0 |
| MOVIEPRG | 6,969 | 1,037 | 391 / 11 / 0 |
| NETPRG | 16 | 34 | 4 / 0 / 0 |
| SAVEPRG | 4,187 | 8,234 | 410 / 16 / 0 |
| SIMPRG | 64,143 | 36,529 | 2,073 / 524 / 30 |
| TESTPRG | 5,097 | 3,501 | 747 / 718 / 329 |
| VSPRG | 2,264 | 1,834 | 368 / 2 / 0 |
| YRSTPRG | 6,228 | 6,024 | 627 / 7 / 0 |

Each overlay's main export is its sequencer entry point, e.g.
`pSetupGameModule__11GAME_MODULE...` at `GAMEPRG:0x998`.

## Tool

```bash
python SRC/snr2.py info   ISO/DLL/GAMEPRG.REL                      # header, exports, checks
python SRC/snr2.py syms   ISO/DLL/GAMEPRG.REL SNDF_ --sles ISO/SLES_541.51
python SRC/snr2.py relocs ISO/DLL/GAMEPRG.REL 9bd0 9c48            # every site in a range
python SRC/snr2.py xref   ISO/DLL/GAMEPRG.REL 248540               # who references an address
python SRC/snr2.py xref   ISO/DLL/GAMEPRG.REL g_pFileManager       # ... or an import
python SRC/snr2.py dis    ISO/DLL/GAMEPRG.REL 9bd0 30 --sles ISO/SLES_541.51
```

`dis` labels imports as `%hi(name)` / `%lo(name)` / `name`, adding
`@address` in `SLES_541.51` when `--sles` is given, and shows every local
site's resolved target.

## Open questions

- Header fields `0x34`/`0x38` (always equal to `0x20`). They could be an
  empty BSS range.
- Where the loader in `SLES_541.51` lives. Finding it would confirm the
  `0x18`/`0x1C` constructor/destructor reading.
- Local functions have no names; only exports and the call sites of imports
  do.
