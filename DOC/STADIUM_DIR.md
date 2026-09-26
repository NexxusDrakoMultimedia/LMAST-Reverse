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
| 0–6 | `ho00a`, `ho00b`, `ho01a`, `ho01b`, `ho02a`, `ho03a`, `ho04a` | home grounds. The digit probably follows the club's stadium level (`ho00` smallest, `ho04` largest) |
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
| `BUILD_ADVERTISE.TBB` | 1 | 32 × 8 bytes | one row per advert slot. Loaded at `0x1d2f2c` |
| `ADVERTISE_MODELPACK.TBB` | 1 | 32 × `char[8]` | advert model names (`agc1` ...) |
| `AUD_MODEL_<MODEL>_{D1,D2,N1,N2}.PAC/.HED` | 40 | 70 NSIF `.snj` | crowd models (`aw01a_d1_aud_0a.snj`). Name built with `%s_%s_%s_%s.snj` at `0x1d5b2c` |
| `AUD_SET_<MODEL>_<n>.TBB` | 18 | 12 tables | crowd placement. `n` is 1–3 for `ho01a`, `ho01b`, `ho02a`, `ho03a` and 1 for the other six models. Loaded at `0x1d5bd0` |
| `AUD_JAM_HI.TBB`, `AUD_JAM_LW.TBB` | 2 | u16, 1024 = 1.0 | crowd density curves? (`AUD_JAM_HI` has 110-byte tables, see [`TBB_FORMAT.md`](TBB_FORMAT.md)). Loaded at `0x1d397c` / `0x1d399c` |
| `AUD_TEXTURE_CLUT_CMN.PAC/.HED` | 1 | 32 | crowd textures and palettes (`txcmn_aud_hi_00.svr`, `plcmn_aud_hi_00_a.svp`) |
| `AUD_TEAM_COLOR_CLUT_CMN.PAC/.HED` | 1 | 128 `.svp` | crowd palettes in team colours (`pl_aud_tc_hi_000.svp`, `_lw_100` ...) |
| `BUILD_STADIUM.TBB` | 1 | 3 tables | which model each of the 119 stadiums uses, and how it's dressed. See below |
| `CONV_INFO_BUILD.TBB` | 1 | 6 × 25 bytes | used at `0x1ce048`/`0x1ce088`. Not decoded |
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
| 2 | 4 × 100 | `0x1cdc28` | 10 bytes are copied from it to the request at `+0x2c` |

A table-0 row (**confirmed** where cited):

| Bytes | Meaning |
|---|---|
| 0 | model index, 0–9 (`0x1cd72c`: ≥ 10 is replaced by 0) |
| 1–115 | per-part values. Most are 0, 7, 3 or 4, and some rows have values up to 26. `0x1cd850` tests them against a variant mask (`01 02 04 04` at `0x299828`, one bit per D1/D2/N1/N2) plus bit 8. So they probably say which lighting variants show each part. **Empirical** |
| 116–127 | 12 bytes copied to the request at `+0x20` when the caller leaves it empty (the offset list at `0x299750`). Values 1–200, ascending in 67 of the 119 rows. Probably advert or board ids |
| 128 | unknown |

The 119 rows match the 119 stadiums of `PARAM/STADIUM_DATA.TBB`
([`PARAM_DIR.md`](PARAM_DIR.md)). Models 3–5 (`ho01b`, `ho02a`, `ho03a`)
cover 90 of them. `stadium.py build DAT/STADIUM <id>` prints one row.

## Still unknown

- Which pack entry each `.PRI` slot and each `BUILD_STADIUM` byte 1–115
  refers to.
- `BUILD_STADIUM` byte 128 and table 2, `CONV_INFO_BUILD.TBB`, and the
  variant-choice functions at `0x1ce1a0`–`0x1ce378`.
- The `AUD_SET_*` tables (12 per file), `AUD_JAM_*`, `BUILD_ADVERTISE` and
  `ADVERTISE_MODELPACK` record layouts, and how the crowd and adverts are
  placed.
- Why four models have three `AUD_SET` tables (probably crowd sizes).
- How stadium ids are assigned to clubs (`STADIUM_DATA.TBB` and
  `plTeam_GetStadiumDataIndex`, [`PARAM_DIR.md`](PARAM_DIR.md)).

## Checking the claims

```bash
python SRC/stadium.py info  DAT/STADIUM DAT/PARAM    # .PRI files, packs per model, BUILD_STADIUM
python SRC/stadium.py pri   DAT/STADIUM/HO00A.PRI    # the 44 priorities
python SRC/stadium.py build DAT/STADIUM 6            # one stadium row
python SRC/pac.py list DAT/STADIUM/AW01A_D1.PAC
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 1caf18 48 --sles ISO/SLES_541.51   # .PRI reader
```
