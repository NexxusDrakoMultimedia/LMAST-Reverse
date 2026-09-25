# SNR2 overlays (`ISO/DLL/*.REL`)

The game code outside `SLES_541.51` lives in ten SN Systems relocatable
overlays (`GAMEPRG`, `SIMPRG`, `SAVEPRG`, ...). Each one is a MIPS image
**linked at base 0**, so image addresses equal file offsets. After the image
come a symbol table and two relocation lists. The loader adds the load base to
every local reference and patches imports by name.

The layout was worked out from the files. It holds with no exceptions for
all ten overlays (`python SRC/snr2.py info <REL>` runs the checks). The module-path
strings (`../PS2_EE_Release/gameprg.elf`) show they were converted from ELF.
The header fields the loader reads are **confirmed** from SN Systems' DLL
runtime in `SLES_541.51` (see [Loader](#loader-confirmed)).

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
| `0x00` | `SNR2` | magic. The loader checks the low three bytes (`SNR`) and accepts version byte `1` or `2` |
| `0x04` | `0x2AE56C` | external relocation table offset |
| `0x08` | `0x253D` | external relocation count |
| `0x0C` | `0x2CA448` | symbol table offset (= `0x04 + 12 × count`) |
| `0x10` | `0x474` | symbol count |
| `0x14` | `0x2AE54C` | module path string, which is also the end of the image |
| `0x18` | `0x20FA68` | global constructors: `snDllLoaded` calls it after linking |
| `0x1C` | `0x20FA10` | global destructors: `snDllUnload` calls it |
| `0x20` | `0x2CD9B8` | = `0x0C + 12 × count`. `snDllLoaded` returns it to the caller when `0x24` is non-zero, so it may be the end of what must stay loaded |
| `0x24` | 0 | flag for the above; 0 in every file |
| `0x28` | `0x80` | load alignment: the load address must be a multiple of it (else error 4). `0x80` in every file |
| `0x2C` | `0x2E518E` | end of local relocations = file size |
| `0x30` | 0 | zeroed by the loader (runtime use) |
| `0x34` | `0x2CD9B8` | local relocation list: the loader walks it from here |
| `0x38` | `0x2CD9B8` | an offset (the loader rebases it); use unknown |
| `0x3C` | 0 | |

`0x20`, `0x34` and `0x38` are equal in every file, so the files alone
can't tell them apart. The loader adds the load base to `0x04`, `0x0C`,
`0x14`, `0x18`, `0x1C`, `0x20`, `0x34` and `0x38` (each if non-zero), which
marks them as offsets.

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

## Calls from `SLES_541.51` into the overlays

The main executable also calls overlay functions, and it links to them the
same way. Its `.sndata` table (the export table above) is a complete
symbol table, and a relocation table sits just before it:

```
0x4a1420-0x4a2344  323 relocations {u32 site, u32 sym << 8 | type, u32 addend}
0x4a2344-0x4cef6c  15,278 symbols  {u32 name, u32 value, u32 hash | kind << 16}
```

The entries have the same layout as the overlays' external relocations
(site first). Symbol 0 is null, as in the overlays. The tables are
declared by an SNR2 header of the executable's own at the start of
`.sndata` (`0x418500`): `0x04` = `0x4a1420`, `0x08` = 323, `0x0C` =
`0x4a2344`, `0x10` = 15,278. `snInitDllSystem` reaches it through the
pointer at `0x361da4`, and the import lookup walks its symbols.
The symbol kinds are 2 (export, 13,127), 3 (weak, 1,922), 1 (import,
value 0, 222) and 4 (6 linker constants: `_gp`, `_end`, `end`, `_stack`,
`_stack_size`, `_heap_size`).

The relocation types are 2 ×130, 4 ×169, 5 ×10 and 6 ×14. All 169 type-4
sites are `jal 0`, and they're all of the `jal 0` instructions in
`.text`, so every unresolved call in a raw disassembly of the executable
is an import listed here. For example, the message escapes `0xC1`–`0xC3`
at `0x11e138`, `0x11e180` and `0x11e198` call symbols `0x3b12`
`Msg::GetGlobalVariable`, `0x3ae2` `EVS::FaceChangeReqOnEvent` and
`0x3b13` `Talk_MesssageCallback_SetMotion`, which `SIMPRG.REL` exports
(see [`MBB_FORMAT.md`](MBB_FORMAT.md#reactions-esc-0xc3)).

The layout is **empirical**. The type-4 check and those three call sites,
each matching its argument setup, are the evidence. Every relocation
targets an import (222 imports, 323 sites). The 130 `R_MIPS_32` sites
start with a table of overlay module entry points in `.data` (`0x34d5f8`…:
`pSetupTest3DModule`, `pSetupModelViewerModule`, ...).

`python SRC/sles_disasm.py ISO/SLES_541.51 relocs [name ...]` lists them,
and `dis`/`addr` label each site: `jal 0 <name>`, and `; %hi(name)` /
`; %lo(name)` on the halves of an address.

## Loader (confirmed)

The loader is SN Systems' DLL runtime, linked into `SLES_541.51` with its
symbol names:

| Address | Symbol | What it does |
|---|---|---|
| `0x15b3c8` | `snInitDllSystem` | set-up: walks the executable's own symbol table (header at `0x418500`, via `0x361da4`). For each symbol it sets byte `+0x0B` (the high byte of the kind half-word) to 0 for kinds 0–1 and 1 for kinds 2–4. Any other kind fails with error 7 |
| `0x15a5f0` | (header check) | magic `SNR` + version `1`/`2`, then the alignment check on `0x28`. Returns 0, or 1 (bad magic), 2 (bad version), 4 (misaligned) |
| `0x15ae98` | (link) | rebases the header offsets, resolves each symbol by kind (a jump table on `+0x0A`; imports go through `0x15a648(name, hash)`), then applies the packed local relocations from `0x34` |
| `0x15b448` | `snDllLoaded(header, out)` | header check → link → `0x15b288(name, header)`, which probably registers the module (its result indexes 12-byte slots at `0x35ed98`) → call the constructors at `0x18` |
| `0x15b590` | `snDllUnload` | calls the destructors at `0x1C`, then `0x15b370` and `0x15acd8` (not traced) and `snDllCacheFlush` |
| `0x15b6b0`, `0x15b828` | `snDllMove`, `snDllGetFunctionAddress` | not traced |

The game's side is `FC_EURO_FILE_RESOURCE::CFcEuro_FileResource::SetupDll`
(`0x10dd08`). Local relocation types 0–3 are the four cases of the
loader's switch on `code & 3` (type 0 is passed on as ELF type 6,
`R_MIPS_LO16`), which matches the table below.

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

- What `0x38` is for, and what `0x20`/`0x24` tell the caller. All three
  are offsets equal to `0x34` in every file.
- How `SetupDll` (`0x10dd08`) picks which overlay to load, and whether it
  uses the module entry-point table at `0x34d5f8`.
- Local functions have no names; only exports and the call sites of imports
  do.
