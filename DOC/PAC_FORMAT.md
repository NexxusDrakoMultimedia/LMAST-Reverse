# PAC / HED archive formats (`*.PAC`, `*.MRG`, `*.HED`)

`DAT/` uses two archive formats:

- **BINPAC**: a self-describing archive. `.PAC` and `.MRG` files are
  BINPACs (662 archives, plus 194 `.HED` headers). A `.HED` is almost always a **byte-for-byte copy of
  its partner's header**. The game loads the small `.HED` files first (some are
  bundled into `PRELOAD/GAMEFILE*.PAC`), so it knows every entry's
  offset before it touches the big archive, then reads single entries from
  the `.PAC`/`.MRG` by offset.
- **KC@P**: a bare offset table in a `.HED` (or `*_HEADER.BIN`) that
  indexes a separate, headerless data file. It's used for the face packs
  and the player packs.

Entries in either format may be wrapped in **PRSH** (Sega PRS
compression).

All values are little-endian. `python SRC/pac.py info DAT` parses every
file and checks it. Only `GAME/PLAYERMOTION.HED` is flagged (see below).

## BINPAC

### Confirmed from the game code

The accessors come from `SLES_541.51` (symbols recovered with
`SRC/sles_disasm.py`):

| Address    | Symbol | Behaviour |
|------------|--------|-----------|
| `0x104670` | `fcEuroBinPac_GetHeaderInfo(void*, int i)` | `i`: 0→`u32@0`, 1→`s16@4`, 2→`s16@6`, 3→`u32@8`, 4→`u32@0xC`, 5→`u32@0x10`, 6→`u32@0x14` (or `0x80` if < 1) |
| `0x1046e8` | `fcEuroBinPac_GetHeaderListData(void*, int idx, int col)` | returns column `col` of entry `idx` (u32). Layout below |
| `0x1047f8` | `fcEuroBinPac_GetHeaderFilename(void*, int idx)` | `hdr + 0x20 + idx*stride + 8` |
| `0x104968` | `fcEuroBinPac_SearchHeaderFilename(void*, const char*, int* off, int* size)` | linear `strcasecmp` over names. Also has a hashed path for a `CPHN` variant (see below) |
| `0x104b80` | `fcEuroBinPac_CheckHeaderLimit` | stub: returns `hdr == NULL` |
| `0x11b8b8` | `CLoader::l_realize_merge` | for each entry: `id = ListData(idx, 3 + idType)`, looked up in a 23-slot table (one per `CLoader::eFILETYPE`) to pick the realize handler for `hdr + ListData(idx, 0)` |

### Header (offset 0, 0x20 bytes)

| Offset | Type | Info # | Meaning |
|--------|------|--------|---------|
| `0x00` | u32 | 0 | header size = offset of the first entry's data (padded to `align`) |
| `0x04` | s16 | 1 | entry count *N* |
| `0x06` | s16 | 2 | **version**: the number of u32 columns after the name, plus 1 (1, 2 or 3 seen) |
| `0x08` | u32 | 3 | flags. `0x49421010` (bytes `10 10 'B' 'I'`) = named; `0x49421001` (`01 10 'B' 'I'`) = **tagged** (see below) |
| `0x0A` | char[6] | – | `BINPAC` (overlaps the top half of `0x08`) |
| `0x10` | u32 | 5 | data alignment (`0x800` sector, `0x40`, `0x10` or `4`) |
| `0x14` | u32 | 6 | name field length in bytes. **0 means 128** |
| `0x18` | 8 bytes | – | zero |

### Entry table (at `0x20`, *N* entries)

```
stride = 4*(version + 1) + name_len          (named)
stride = 4*(version + 2)                     (tagged: name_len is forced to 4)

+0x00  u32  offset   absolute offset in the archive          column 0
+0x04  u32  size     byte size (unpadded)                    column 1
+0x08  char name[name_len]                                   column 2
+0x08+name_len  u32 extra[version-1]                         columns 3..
```

- The name field holds the **last `name_len` characters** of the source
  path, NUL-padded. When the path is exactly `name_len` long there is no
  terminator, e.g. `nst_tex_0000.svr` in a 16-byte field. The truncation
  leaves some archives with odd names (`./num_00_00.svr`,
  `_mask_001_01.svr`), and archives with `name_len = 4` keep only the
  extension (`.svm`, `.snj`).
- **Tagged** archives (`flags = 0x49421001`: `GAME/BALLMOTION`,
  `OPTMOTION`, `OPTMOTION_FC_EURO`, `PLAYERMOTION`) have `name_len = 0` in
  the header. The game ignores it and treats column 2 as a single u32. In
  practice that u32 is a 3-letter type (`snm\0`, `bnt\0`, `opm\0`).
- **Extra columns**:
  - v3: two u32. Usually `0,0`. In `PRELOAD/GAMEFILE*.PAC` the first
    one varies (3, 8, 9, 12) and looks like a load type.
  - v2 `.MRG`: one u32, the **merge user ID**. Confirmed from
    `CLoader::l_realize_merge`: it reads column `3 + idType` and matches
    the value against a 23-slot table, one slot per `CLoader::eFILETYPE`,
    filled by `CLoader::setMergeFileUserId(eFILETYPE, int id,
    eMERGE_USER_ID_TYPE)`. The match picks the handler
    (`l_realize_texture_svm`, `l_realize_objectpack_snj`, ...), and
    unmatched entries are skipped. The meaning of each ID is therefore set
    by the calling code, not fixed. Observed: `snd`/`snq`/`snp`/`snl`→0,
    most `snj`/`sno`→0, `svm`→1/2/3, `sna`/`snt`→2, `snm`→3,
    `svp`/`zbf`→4 (a few `svp`→2), some `sno`→5 (`CUTINHANDPACK`).
    Empty slots are `dummy.bin`/`.bin` with size 0 and ID `0xFFFFFFFF`.
    Every `.MRG` has exactly one extra column, so `idType` is always 0 here.
- The entry table is zero-padded up to `header_size`. The first entry's
  offset always equals `header_size`, and every offset is a multiple of
  `align`.
- In all 309 `.MRG`s the packer places data with
  `(pos + align) & ~(align - 1)`, so there is always at least one byte of
  gap:
  - `header_size = (0x20 + N*stride + 4 + align - 1) & ~(align - 1)`
    (the table is followed by one zero u32, then the padding);
  - `offset[i+1] = (offset[i] + size[i] + align) & ~(align - 1)`, so
    zero-size `dummy.bin` slots still take one alignment unit;
  - the file ends exactly at `offset[N-1] + size[N-1]`.

### Variants seen

| Ext | ver | align | name_len | Files | Notes |
|-----|-----|-------|----------|-------|-------|
| PAC/HED | 3 | 0x800 | 128 / 16 / 4 | 145 | textures, models, schedules |
| PAC | 3 | 0x40 | 128 | 140 | `PRELOAD/GAMEFILE*` hold `.hed`, `.tbb`, ... |
| PAC/HED | 3 | 4 | 4 / 128 | 42 | `STADIUM/ADT_*`, `AUD_*_CLUT_CMN` |
| PAC | 3 | 0x10 | 4 | 14 | `PARAM/PBDATA_*`, `PLRESOURCE*` |
| MRG | 2 | 0x10 / 0x800 | 128 / 4 | 309 | merged model/motion/texture sets |
| PAC | 2 | 0x800 | 128 | 4 | `HAIR_PACK` (a PAC of `.mrg`s), `HAIR_PALETTE`, `TEST3D/BGDATA_*` |
| PAC/HED | 1 | 0x800 | 4 | 4 | `SHADOWCOLLI`, `WALLCOLLI`, `PLAYER_MODEL` |
| PAC | 1 | 4 | tagged | 4 | motion packs |

`*_PRESS.PAC` files (e.g. `PLAYER/NUMBER_00_PRESS.PAC`) repack the same
content as their non-`PRESS` sibling. They use 16-byte alignment and store
entries either PRSH-compressed (`.svm` models) or raw (`PVPL` CLUTs).

### Example: `PLAYER/NUMBER_00.HED` (= first 0x1000 bytes of `NUMBER_00.PAC`)

```
0000: 00100000 6400 0300 10104249 4e504143   hdr 0x1000, 100 entries, v3, named, "BINPAC"
0010: 00080000 10000000 00000000 00000000   align 0x800, name_len 16
0020: 00100000 20080000 2e2f6e75 6d5f3030   off 0x1000, size 0x820, "./num_00
0030: 5f30302e 73767200 00000000 00000000   _00.svr"  extra 0, 0      (stride 32)
```

### Variant not present on disk

`SearchHeaderFilename` checks `u32@0x0C == 'CPHN'`. In that case it
hashes the name and uses a bucket table of `{u16 first, u16 count}` at
`+0x20`, 16-byte records `{u32 off, u32 size, u32 name_off, u32 hash}` at
`+0x420`, and names at `+0x420 + count*16 + name_off*8`.
`GetHeaderListData` also returns 0 for it. No file in `DAT/` uses this
layout.

### Anomaly: `GAME/PLAYERMOTION.HED`

The `.HED` is dated Feb 2005 and lists 1008 named entries. The `.PAC` is
dated Aug 2005 and is a tagged v1 archive with 649 entries. They don't
match. The `.PAC` is self-describing, so the `.HED` looks like a stale
leftover.

## KC@P

The data files have no header at all. Entries run back to back and are
2048-aligned.

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | char[4] | `KC@P` |
| `0x04` | u32 | total size of the data file |
| `0x08` | u32 | entry count *N* |
| `0x0C` | u32 | 0 |
| `0x10` | u32[N] | **end** offset of each entry. Entry *i* spans `[end[i-1], end[i])`, and entry 0 starts at 0 |

| Header | Data file | N | Payload |
|--------|-----------|---|---------|
| `PLAYER/FC_EURO_FACEPACK_00.HED` | `FC_EURO_FACEPACK_00.BIN` (1.1 GB) | 21171 | PRSH |
| `PLAYER/FC_EURO_FACEPACK_01.HED` | `FC_EURO_FACEPACK_01.BIN` | 215 | PRSH |
| `PLAYER/EDITFACEPACK_BIN.HED` | `EDITFACEPACK.BIN` | 1 | raw |
| `PLAYER/PLPACK_HOME.HED` / `_AWAY` | `PLPACK_HOME.PAC` / `_AWAY` | 116 | 184320-byte blocks starting `07 00 00 00` |
| `GAME/CUTINPACK_HEADER.BIN` | `GAME/CUTINPACK.BIN` | 277 | raw, starts with a small u32 count (`0x0d`, `0x10`, ...) |

The `KC@P` magic doesn't appear as an immediate in the executable, so the
loader probably doesn't check it. The layout above is empirical, but it
holds for all five headers: the sizes match, the offsets increase, and the
last end offset equals the file size.

## PRSH (compressed entry)

| Offset | Type | Meaning |
|--------|------|---------|
| `0x00` | char[4] | `PRSH` |
| `0x04` | u32 | offset of the compressed stream (0x40) |
| `0x08` | u32 | compressed size |
| `0x0C` | u32 | decompressed size |

The stream is standard **Sega PRS**. This is confirmed from
`Press::ExtractData` (`0x1ff470`) → `Press::Expand` (`0x1ff3f0`) →
`stPrsInf::Extract` (`0x1ff570`) / `getCtrlCode` (`0x1ff6f0`). Control
bits are read LSB-first, one byte at a time:

- `1`: literal byte.
- `01` + `lo, hi`: long copy. `offset = ((hi<<5)|(lo>>3)) - 0x2000`.
  `len = (lo&7)+2`, or if `lo&7 == 0`, `len = next_byte + 1`.
  `lo = hi = 0` ends the stream.
- `00` + 2 bits `b1 b0` + 1 byte: short copy. `len = (b1<<1|b0)+2`,
  `offset = byte - 0x100`.

All 5,496 PRSH entries inside BINPACs decompress to exactly their
header's size, and so do all sampled face-pack entries.

## Tool

```bash
python SRC/pac.py info DAT                                   # check every archive
python SRC/pac.py list DAT/PRELOAD/GAMEFILE0.PAC              # entries + payload magic
python SRC/pac.py extract DAT/PLAYER/NUMBER_00.HED out/       # .HED -> reads NUMBER_00.PAC
python SRC/pac.py extract DAT/PLAYER/FC_EURO_FACEPACK_01.HED out/ --prs   # expand PRSH
```

Extracted files are named `<index>_<name>`, or `<index><.ext>` when only an
extension survives, so duplicate names don't collide.
