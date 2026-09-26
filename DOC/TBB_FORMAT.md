# TBB table files (`*.TBB`)

`.TBB` files under `DAT/` hold the game's parameter / lookup tables
(league names, team init data, stadium layouts, uniform colours, event
scripts, ...). There are 60 of them. Each is a small container of one or
more `TBL1` tables; each table is a flat block of fixed-width binary rows.

All values are little-endian. Every file in `DAT/` parses cleanly with
the layout below (`python SRC/tbb.py info DAT`).

## Confirmed from the game code

`SLES_541.51` has no `.symtab`, but `.sndata` contains a runtime export
table for the `DLL/*.REL` overlays: 12-byte entries
`{u32 name_ptr, u32 address, u32 hash}` with mangled GCC 2.x names
(~12,600 symbols). `SRC/sles_disasm.py` recovers them and disassembles
with labels (`python SRC/sles_disasm.py ISO/SLES_541.51 dis TblData`).
The TBB accessors recovered from it:

| Address    | Symbol                                             | Behaviour |
|------------|----------------------------------------------------|-----------|
| `0x1fb2b8` | `TbbData::GetTableDataCount(const TBB_FILEHEADER*)` | checks magic `0x31424254` (`TBB1`), returns `hdr+0x08` |
| `0x1fb270` | `TbbData::GetTableDataPtr(const TBB_FILEHEADER*, uint i)` | if `i < hdr+0x08`: `return hdr + ((u32*)(hdr + hdr[+0x04]))[i]` |
| `0x2b9dd0` | `TblData::GetDataHeadPoint(TBB_FILEHEADER*, uint i)` | `tbl = GetTableDataPtr(i); return tbl + tbl[+0x04]` |
| `0x2b9df8` | `TblData::GetDataTableCount(TBB_FILEHEADER*, uint i)` | `tbl[+0x08] / tbl[+0x0C]` (unsigned int division) |
| `0x2b9db0` | `TblData::CTblData::GetDataTable1LineSize(uint i)` | `tbl[+0x0C]` |
| `0x21e970` | `Param::plResource_GetDataFromTbl(void*)` | checks magic `0x314C4254` (`TBL1`), returns `tbl + tbl[+0x04]` |

`CTblData` is just a wrapper holding a `TBB_FILEHEADER*` (`Setup(void*)`
stores it, `Clear()` zeroes it).

## Layout

### `TBB_FILEHEADER` (file offset 0)

| Offset | Type  | Meaning |
|--------|-------|---------|
| `0x00` | char[4] | magic `TBB1` |
| `0x04` | u32   | offset of the table-offset array (always `0x10`) |
| `0x08` | u32   | number of tables *N* |
| `0x0C` | u32   | end of last table's data (unpadded file length). **Not read by the accessors**; `0` in MSGCOMMON, SCHEDULE, EVENTDATA_TURN and DATABASE_FILETABLE |
| `0x10` | u32[N] | absolute file offset of each `TBL1` header |

The offset array is zero-padded to a 16-byte boundary.

### `TBL1` table header (at each offset above, 16-byte aligned)

| Offset | Type  | Meaning |
|--------|-------|---------|
| `0x00` | char[4] | magic `TBL1` |
| `0x04` | u32   | offset of row data, relative to this header (always `0x10`) |
| `0x08` | u32   | data size in bytes |
| `0x0C` | u32   | **line size** — bytes per row ("1 line size" in the game's naming) |

Row count = `size / line_size` (integer division, as the game does it).
Row data is followed by zero padding to the next 16-byte boundary, where
the next `TBL1` starts. The file itself is padded to 16 bytes.

### Example — `GAME/BACK_MATCH.TBB`

```
0000: 54424231 10000000 06000000 1f010000   TBB1, arr@0x10, 6 tables, end 0x11f
0010: 30000000 60000000 80000000 a0000000   table offsets...
0020: d0000000 f0000000 00000000 00000000
0030: 54424c31 10000000 18000000 08000000   TBL1, data@+0x10, 24 bytes, 8/line -> 3 rows
0040: 0000 3200 6400 c800 | 9001 2c01 6400 3200 | 0000 3200 c800 6400   (3 rows of 4 x u16)
```

## What the container does *not* tell you

There are no column types or names. Row schemas are baked into the code
that reads each table, so field meanings have to be worked out per file.

The line size is what the game uses for row counting, but it isn't always
the size of the record the consumer actually walks:

| File | Line size | Observed record | Notes |
|------|-----------|-----------------|-------|
| `EVENT/EVENTDATA_TURN.TBB` | 32 | **281** bytes (61258 = 281 × 218) | packed struct of strings up to char[64] + a u8; unused by the game. See [EVENTDATA_TURN.md](EVENTDATA_TURN.md) |
| `0SYSTEM/MSGCOMMON.TBB` t1/t2 | 32 / 24 | 64 / 48 | rows alternate name / 3-letter abbreviation (`ENGLAND`, `ENG`, ...) |
| `PARAM/TEAM_INIT_DATA.TBB` | 4 | 24, 144, 72, 16 ... | tables of u32 fields |
| `PARAM/REGULATION.TBB` | 2 | 120 | u16 fields |
| `STADIUM/AUD_JAM_HI.TBB` | 8 | 10 (110 = 11 × 10) | u16 values, 1024 = 1.0 fixed point; 6 bytes left over at line size 8 |
| `EMBLEM/EDIT_EMBLEM.TBB` t93/101/105 | 12 | 12, one record short by a byte | 143 bytes; see below |

### `EDIT_EMBLEM.TBB` t93, t101 and t105 (empirical)

These are the only tables on the disc whose size isn't a whole number of lines. Each
is 143 bytes, one byte short of the 144 (12 × 12) that most of their
neighbours hold. The neighbours' 12-byte records start with the record's
own index as a u16 (`00 00`, `01 00`, ... `0b 00`) and end with a `00`
byte.

In all three tables, records 0–3 and 5–11 match that pattern. Record 4 is
11 bytes and has no `04 00` index at the start. In t101 it reads
`8d 00 00 00 2b 00 00 00 50 50 00`. Every record after it therefore sits
one byte earlier than a 12-byte line would expect. That is why `tbb.py
info` shows `05`, `06`, ... as the *last* byte of each line from row 4 on.
The single byte after the data is the usual `00` alignment padding.

It looks like an authoring slip repeated in three tables that follow
the same pattern, not a different record size. The game counts rows as
`size / line_size` (`GetDataTableCount`), so it sees 11 rows and never
reaches record 11. Rows 4–10 would come out misaligned if it walks them
by line size. The code that reads these tables (`edit_emblem.tbb` is
named in `DLL/CEDITPRG.REL`) hasn't been found yet, so what the game
actually does with them is unconfirmed. `tbb.py info` keeps reporting
them as `!!` because the data really doesn't fit the line size.

For single-type tables the line size is usually the element size, and
for string tables the string width. It is *not* reliably the widest
member of a mixed struct: EVENTDATA_TURN has a char[64] field under a
line size of 32. Treat it as an exporter hint, not a schema. The
`PXPlusPutXlsFuncTbl` symbol hints these were exported from Excel sheets
by an in-house tool.

## Files that load them

Filenames appear (lower/mixed case) in the overlay that uses them, e.g.
`DLL/SIMPRG.REL` (`Regulation.tbb`, `Training_list.tbb`, `ClubResult.tbb`,
...), `DLL/GAMEPRG.REL` (`build_stadium.tbb`, `aud_jam_hi.tbb`, ...),
`DLL/CEDITPRG.REL` (`edit_emblem.tbb`, `team_init_data.tbb`, ...),
`DLL/YRSTPRG.REL` (`edit_player.tbb`). Cross-referencing those strings to
their loaders is the way to recover per-table schemas.

## Tool

```bash
python SRC/tbb.py info DAT                          # list every table in every file
python SRC/tbb.py dump DAT/GAME/BACK_MATCH.TBB 0     # hex + ASCII per row
python SRC/tbb.py extract DAT/PARAM/REGULATION.TBB out/   # raw table blobs
```
