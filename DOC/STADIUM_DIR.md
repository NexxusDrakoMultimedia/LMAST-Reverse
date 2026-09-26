# `DAT/STADIUM`: stadium models, crowds and adverts

`DAT/STADIUM` (320 files, 35 MB, plus `CVS/`) holds the 3D stadiums used in
matches. There are **10 stadium models**, and the tables here build each of
the game's **119 stadiums** from one of them. Everything is loaded by
`DLL/GAMEPRG.REL`, the match overlay. All file names appear there as
strings from `0x299960` on.

Every container here is a BINPAC pack ([`PAC_FORMAT.md`](PAC_FORMAT.md)),
a TBB table ([`TBB_FORMAT.md`](TBB_FORMAT.md)) or a `.PRI` file. The packs
hold Ninja models (`.sno`/`.snj`/`.sna`, [`NINJA_FORMAT.md`](NINJA_FORMAT.md))
and textures and palettes (`.svr`/`.svp`, [`SVR_FORMAT.md`](SVR_FORMAT.md)),
mostly PRSH-compressed. `python SRC/pac.py info DAT/STADIUM`,
`python SRC/tbb.py info DAT/STADIUM` and `python SRC/ninja.py info DAT
--prs` parse all of them. `python SRC/stadium.py info DAT/STADIUM
DAT/PARAM` checks the parts described here.

The `.PRI` layout and the `BUILD_STADIUM` table sizes are **confirmed**
from `GAMEPRG.REL` (addresses are file offsets in that overlay).
Everything else is **empirical** unless marked.

## The 10 models

`GAMEPRG.REL 0x24d6a8` is a table of 10 name pointers. The model index
used everywhere (`BUILD_STADIUM` byte 0, `.PRI` requests) is the position in
this table:

| Index | Name | Kind |
|---|---|---|
| 0–6 | `ho00a`, `ho00b`, `ho01a`, `ho01b`, `ho02a`, `ho03a`, `ho04a` | home grounds. The digit is the stadium level 0–4: `CONV_INFO_BUILD` picks `ho0N` stadiums for level N (below) |
| 7–9 | `aw01a`, `aw03a`, `aw04b` | away grounds |

`CDataHandle::OpenReq` is called with folder id **`0xa`** for files in this
folder (`0x1cdf90`, `0x1cd5fc`).

Each model comes in four lighting variants, **`D1`, `D2`, `N1`, `N2`**
(the strings `d1 d2 n1 n2` at `0x299954`). D and N are presumably day and
night. The model's `BUILD_STADIUM` table-1 row picks 1 or 2 per month (below). The
small functions at `0x1ce1a0`–`0x1ce378` choose a variant from the match
settings. They aren't decoded.

## Directory overview

| Files | Count | Entries | Contents |
|---|---|---|---|
| `<MODEL>_{D1,D2,N1,N2}.PAC/.HED` | 40 | 46 each, PRSH `.sno` | the stadium's own parts: stands, fences, nets, roofs (`aw01a_d1_fen1.sno`) |
| `<MODEL>_OP.PAC/.HED` | 10 | 1 PRSH `.sno` | one extra part per model (`01a_avm1.sno`) |
| `<MODEL>.PRI` | 10 | – | draw priority of each part slot, see below |
| `STCMN_{D1,D2,N1,N2}.PAC/.HED` | 4 | 55 each | parts shared by all models: goals (`d1_gol01.sno`), pitches (`pit01_sp.sno`), ... |
| `STCMN_SK.PAC/.HED` | 1 | 20 | skies (`f_sky_sp.sno`, `c_sky_su.sno`: clear, cloudy, rain × season?) |
| `STADIUM_SVR.PAC` | 1 | 635 PRSH `.svr` | shared textures (`sky_cloud3.svr`, `txcmn_fen1_01.svr`, ...). The only pack here with no `.HED`. Also named in `GAMEPRG.REL 0x26651a` (`CMatchStadium`) |
| `SEAT_CLUT.PAC/.HED` | 1 | 16 `.svp` | seat colour palettes (`_seat_00.svp` ...) |
| `STAND_NODE_NAME.PAC/.HED` | 1 | 58 `.sna` | node-name lists for the stands |
| `STAFF_NODE_NAME.PAC/.HED` | 1 | 11 `.sna` | node-name lists for the bench area, one per model (`aw01a` twice) |
| `ADT_<MODEL>_{D1,D2,N1,N2}.PAC/.HED` | 40 | 32 PRSH `.snj` | advertising boards ("ADT"). Loaded at `0x1d2e74` by `CAdvertiseLoader` |
| `ADT_TEXCMN.PAC/.HED` | 1 | 419 `.svr` | advert textures |
| `BUILD_ADVERTISE.TBB` | 1 | 32 × 8 bytes | one row per advert board. Loaded at `0x1d2f2c`. See [Adverts](#adverts) |
| `ADVERTISE_MODELPACK.TBB` | 1 | 32 × `char[8]` | board names (`agc1` ...), one per `BUILD_ADVERTISE` row |
| `AUD_MODEL_<MODEL>_{D1,D2,N1,N2}.PAC/.HED` | 40 | 70 NSIF `.snj` | crowd models (`aw01a_d1_aud_0a.snj`). Name built with `%s_%s_%s_%s.snj` at `0x1d5b2c` |
| `AUD_SET_<MODEL>_<n>.TBB` | 18 | 12 tables | the 18 crowd sets. `n` is 1–3 for `ho01a`, `ho01b`, `ho02a`, `ho03a` and 1 for the other six models. Loaded at `0x1d5bd0`. See [Crowds](#crowds) |
| `AUD_JAM_HI.TBB`, `AUD_JAM_LW.TBB` | 2 | u16, 1024 = 1.0 | how the crowd fills up. Loaded at `0x1d397c` / `0x1d399c`. See [Crowds](#crowds) |
| `AUD_TEXTURE_CLUT_CMN.PAC/.HED` | 1 | 32 | crowd textures and palettes (`txcmn_aud_hi_00.svr`, `plcmn_aud_hi_00_a.svp`) |
| `AUD_TEAM_COLOR_CLUT_CMN.PAC/.HED` | 1 | 128 `.svp` | crowd palettes in team colours (`pl_aud_tc_hi_000.svp`, `_lw_100` ...) |
| `BUILD_STADIUM.TBB` | 1 | 3 tables | which model each of the 119 stadiums uses, and how it's dressed. See below |
| `CONV_INFO_BUILD.TBB` | 1 | 6 × 25 bytes | stadium id by level. See [below](#conv_info_buildtbb) |
| `TIME_CHECK.DAT` | 1 | 8 bytes (`ff ff 00 00 ff ff 00 00`) | read from `pfs0:Data/Stadium/` at `0x1cb0a0`, a development path |
| `DUMMY.DAT` | 1 | 0 bytes | |

The BINPAC name column is 16 bytes wide in the model packs. Longer names
keep their **last** 16 characters, so `aw01a_d1_fen1.sno.prs` is stored as
`_d1_fen1.sno.prs`.

## `.PRI`: part draw priorities

Each file is 176 bytes: **44 × u32**, one per part slot of the model. All
of it is **confirmed**:

- `0x1caf18` reads the file (as `pfs0:Data/Stadium/<model>.pri`, a
  development path) 4 bytes at a time into `+0x0c` of 44 part records of
  `0x18` bytes at `+0x1aa0` of the stadium object. `0x1cafd8` writes the
  same values back, so the priorities could be edited in-game and saved.
- On the disc build the file is requested through
  `CDataHandle::OpenReq(0xa, "<model>.pri")` at `0x1cdf60`. The stadium
  index is clamped to 0–9.
- Two draw passes walk the part records by priority. `0x1cae18` draws
  priorities 0–49 and `0x1cae98` draws 50–100, each in increasing order.
  A part with a priority above 100 is never drawn.

On the disc every value is 0–100, and 18–20 slots per model are in the
first pass. `HO01A.PRI` differs most from the others (for example slot 0
is 80, where the others have 94). The mapping from slot to pack entry
isn't confirmed: the model packs hold 46 entries but there are 44 slots.

## `BUILD_STADIUM.TBB`

Three tables. `GAMEPRG.REL 0x1cd648` builds a stadium from a request whose
`+0` is the stadium id (reset to 0 if ≥ 119):

| Table | Rows × size | Reader | Contents |
|---|---|---|---|
| 0 | 119 × 129 | `0x1cdb38` (`id * 0x81`) | one row per stadium. The row is copied to the request at `+0x36` |
| 1 | 10 × 12 | `0x1cdbb0` | one row per model. The request's byte `+0x0b` (< 12, probably the month) picks a value, 1 or 2, stored at `+0x0c`. Most rows read `2 2 2 2 2 1 1 1 1 2 2 2` or similar: winter and summer if the index is the month from January |
| 2 | 4 × 100 | `0x1cdc28` | 4 rows × 10 models × 10 bytes: `t[row*100 + model*10]`, with the row taken from request `+0x04` (clamped to < 4). The 10 bytes go to the request at `+0x2c`. Values are `ff` or small ids. Meaning unknown |

A table-0 row (**confirmed** where cited):

| Bytes | Meaning |
|---|---|
| 0 | model index, 0–9 (`0x1cd72c`: ≥ 10 is replaced by 0) |
| 1–114 | per-part switches. Most are 0, 7, 3 or 4, and some rows have values up to 26. `0x1cd850` tests byte *k* against a variant mask (`01 02 04 04` at `0x299828`, one bit per D1/D2/N1/N2) plus bit 8, so a part shows only in the variants whose bit is set. Bytes 42–69 and 94–97 switch the 32 advert boards (`BUILD_ADVERTISE` `+6`, **confirmed** at `0x1d1c98`). Which part the other bytes switch isn't known |
| 115 | crowd set, 0–17 (request `+0xa9`, read at `0x1d3848`). Picks the `AUD_SET` file (see [Crowds](#crowds)). In all 119 rows its model matches byte 0 |
| 116–127 | the 12 advert textures, copied to the request at `+0x20` when the caller leaves it empty (the offset list at `0x299750`). `0x1d31b8` turns each into a texture index (value − 1, clamped to 205, plus 7) for advert slots 1–12 |
| 128 | unknown |

The 119 rows match the 119 stadiums of `PARAM/STADIUM_DATA.TBB`
([`PARAM_DIR.md`](PARAM_DIR.md)). Models 3–5 (`ho01b`, `ho02a`, `ho03a`)
cover 90 of them. `stadium.py build DAT/STADIUM <id>` prints one row.

## `CONV_INFO_BUILD.TBB`

One table of 150 bytes. `0x1ce0b8` (called from `0x1ca3d4`) reads three
bytes `a`, `b`, `c` and returns the stadium id `t[b*25 + a*5 + c]`,
keeping `b`. So it is 6 rows × 5 × 5 stadium ids (**confirmed**).

**Empirical:** every id in the `a` block of every row uses a `ho0a` model
(level 0 → `ho00a`/`ho00b`, level 4 → `ho04a`), so `a` is the stadium
level and `c` one of 5 variants of it. The 6 rows `b` are probably the 6
leagues; rows differ only in which `ho00`/`ho01` model levels 0 and 1 use.
102 of the 150 ids are distinct.

## Adverts

`CAdvertiseLoader` (`0x1d2f08`) opens `build_advertise.tbb`,
`adt_<model>_<variant>.pac` and `adt_texcmn.pac`. `BUILD_ADVERTISE` has one
8-byte row per board. Board *i* is entry *i* of the ADT packs, which all
hold 32 boards, and has name *i* in `ADVERTISE_MODELPACK`:

| Offset | Type | Meaning |
|---|---|---|
| `+0` | s16 | board type |
| `+2` | s16 | alternative type, used instead when stadium row byte 43 or 52 has bit 8 set (`0x1d1cc8`, `0x1d21e8`) |
| `+4` | s16 | another board this one is attached to, −1 = none (`0x1d2288`) |
| `+6` | s16 | the `BUILD_STADIUM` row byte that switches the board on (`0x1d1c98`) |

The type picks a creator class through the jump table at `0x299d30`
(factory `0x1d2028`). The class names come from the type-info functions
in each creator's vtable:

| Type | Class | Boards |
|---|---|---|
| 0 | `CAdvertiseCreatorCommon` | 16 |
| 1 | `CAdvertiseCreatorLCDAnm` | 2 (`aga3`, `ata3`, attached to `agc3` / `atc3`) |
| 2 | `CAdvertiseCreatorFixed` | 12 |
| 3 | `CAdvertiseCreatorElectric` | alternative type only |
| 4 | `CAdvertiseCreatorLCDLogo` | 2 (`agc3`, `atc3`) |

## Crowds

A stadium's crowd set (row byte 115) indexes two byte tables at
`0x24dfa8` (model) and `0x24dfc0` (file number − 1). The 18 sets are
exactly the 18 `AUD_SET_<model>_<n>.TBB` files, in order: `ho00a_1`,
`ho00b_1`, `ho01a_1`–`_3`, `ho01b_1`–`_3`, `ho02a_1`–`_3`,
`ho03a_1`–`_3`, `ho04a_1`, `aw01a_1`, `aw03a_1`, `aw04b_1`. So a set is
one crowd layout for a model, and the three-set models have three sizes
(the block count grows from `_1` to `_3`).

`0x1d68b0` parses an `AUD_SET` file (12 tables):

| Table | Contents |
|---|---|
| 0 | 9 stand sections × 8 bytes: `{u16 share, u16 tiers, u32 slot}`. The game writes a pointer to table *k*+1 into section *k*'s slot. Shares are 1024 = 1.0 and add up to 1018–1022 in every file |
| 1–9 | one per section, 5 rows of 8 bytes. **Empirical:** `{u32, u32 1024}`, where the first value (800, 1600, ...) grows with the share. Possibly seat counts |
| 10 | crowd blocks, 40 bytes each: `char[32]` name, `u8 section`, `u8 tier`, `u8 flag` (0/1, read at `0x1d83f8`), then two copies of one byte (`+0x23`, `+0x26`) that count up through the file or are 0. The name builds the model name `<model>_<variant>_aud_<name>.snj` (`0x1d5b08`), and every block has its model in all four `AUD_MODEL` packs. Every tier is below its section's tier count |
| 11 | 1 byte, 1 or 2 |

`AUD_JAM_HI` and `AUD_JAM_LW` control how the crowd fills up (the debug
line `  %s %3d%% [%d:%d]` at `0x29a210` prints `hi`/`lw` and a percentage):

- **`AUD_JAM_HI`**: 2 tables of 11 rows × 10 bytes (not the TBB line size
  of 8): `{u16 amount[3], u16 palette, u16 threshold}`. `0x1d8188` picks
  the last row whose threshold/1024 is at or below the fill ratio.
  `0x1d836c` uses the three amounts as `1 − v/1024`, and `+6` selects a
  palette through `0x29a448`.
- **`AUD_JAM_LW`**: 4 rows of `{u16 threshold, u16 level}`, searched the
  same way (`0x1d8548`). Thresholds are 0, 307, 512 and 716.

All thresholds ascend. The names suggest the high- and low-detail crowds
(`txcmn_aud_hi_00.svr`, `txcmn_aud_lw_00.svr`).

## Still unknown

- Which pack entry each `.PRI` slot and each other `BUILD_STADIUM` byte
  (1–41, 70–93, 98–114) refers to.
- `BUILD_STADIUM` byte 128 and table 2, and the variant-choice functions
  at `0x1ce1a0`–`0x1ce378`.
- `AUD_SET` tables 1–9 and 11, the block flag and the `+0x23` byte; what
  the three `AUD_JAM_HI` amounts control.
- Which `CONV_INFO_BUILD` row applies to which league.
- How stadium ids are assigned to clubs (`STADIUM_DATA.TBB` and
  `plTeam_GetStadiumDataIndex`, [`PARAM_DIR.md`](PARAM_DIR.md)).

## Checking the claims

```bash
python SRC/stadium.py info  DAT/STADIUM DAT/PARAM    # every table and the cross-references
python SRC/stadium.py pri   DAT/STADIUM/HO00A.PRI    # the 44 priorities
python SRC/stadium.py build DAT/STADIUM 6            # one stadium row, with its crowd set and table-2 bytes
python SRC/stadium.py crowd DAT/STADIUM/AUD_SET_HO03A_3.TBB   # sections and crowd blocks
python SRC/pac.py list DAT/STADIUM/AW01A_D1.PAC
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 1caf18 48 --sles ISO/SLES_541.51   # .PRI reader
```
