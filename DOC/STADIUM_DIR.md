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
(the strings `d1 d2 n1 n2` at `0x299954`). `0x1ce208` picks one from the
build request (**confirmed**):

| Request `+4` | Request `+5` | `+0x88` flag | Variant |
|---|---|---|---|
| 0 (day) | 0 | – | `D1` |
| 0 (day) | 1–3 | – | `D2` |
| 1 (night) | – | 0 | `N1` |
| 1 (night) | – | 1 | `N2` |

The same fields pick the sky (`0x1ce278`, `STCMN_SK` entry `season × 5 +
k`). k is 0 for day with `+5` = 0, 1 for `+5` = 1, 2 for `+5` = 2–3, 3 for
night with `+5` = 0 and 4 for night otherwise. The sky names (`f_sky`,
`c_sky`, `r_sky`: fine, cloudy, rain) make `+5` the weather: 0 fine, 1
cloudy, 2–3 rain (and probably snow). `+6` is the season, 0–3 = the `sp`,
`su`, `au`, `wi` names. What sets the night flag at `+0x88` wasn't found:
the request is filled by a block copy, not field by field.

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
is 80, where the others have 94).

A slot is a kind of part, not a pack entry. The build functions called
at `0x1cec70` load each part into a fixed slot. `0x1cf760(slot, entry)`
loads from `STCMN_<variant>`, `0x1cf8e0` from the model's own pack,
`0x1cfa60` from `STCMN_SK` and `0x1cfbe0` from `<MODEL>_OP`
(**confirmed**):

| Slot | Part | Pack entries |
|---|---|---|
| 0 | goal | `STCMN` 0–2 (`gol01`–`03`) |
| 1 | corner flags | `STCMN` 45 (`cflag`) |
| 2 | sky | `STCMN_SK` 0–19 (see above) |
| 3 | pitch | `STCMN` 3–38 (`pit01`–`09` × 4 seasons) |
| 4 | pitch edge | model 44–45 (`ptp_su`, `ptp_wi`, by `BUILD_STADIUM` table 1) |
| 5 | bench | `STCMN` 39, 41, 43 (`ben1l`–`ben3l`) |
| 6 | – | nothing loads this slot |
| 7, 8 | fences, fence shadow | model 0–4, 5 |
| 9, 10 | nets, net shadows | model 6, 8 and 7, 9 |
| 11 | banners | model 10–14 |
| 12–19 | stands 0–3 and their shadows | model 15–22 |
| 20–26 | lights, light shafts, illuminations | model 23–29 |
| 27–30 | spotlights | model 30–33 |
| 31–35 | caps | model 34–38 |
| 36–38 | staff areas | model 39–41 |
| 39, 40 | advert rigs `avi1`, `avs1` | model 42, 43 |
| 41 | the `_OP` part | `<MODEL>_OP` 0 |
| 42, 43 | pitch lines | `STCMN` 46–49 (`lna`), 50–54 (`lnb`) |

So the model packs' 46 entries are slots 7–40 plus the two pitch edges.

## `BUILD_STADIUM.TBB`

Three tables. `GAMEPRG.REL 0x1cd648` builds a stadium from a request whose
`+0` is the stadium id (reset to 0 if ≥ 119):

| Table | Rows × size | Reader | Contents |
|---|---|---|---|
| 0 | 119 × 129 | `0x1cdb38` (`id * 0x81`) | one row per stadium. The row is copied to the request at `+0x36` |
| 1 | 10 × 12 | `0x1cdbb0` | one row per model. The request's byte `+0x0b` (< 12, probably the month) picks a value, 1 or 2, stored at `+0x0c`. It chooses the pitch edge: 1 = `ptp_su`, 2 = `ptp_wi` (`0x1cef54`). Most rows read `2 2 2 2 2 1 1 1 1 2 2 2` or similar: winter and summer if the index is the month from January |
| 2 | 4 × 100 | `0x1cdc28` | 4 variants × 10 models × 10 bytes: `t[variant*100 + model*10]`. The 10 bytes go to the request at `+0x2c`, and `0x1ced60` loads each one that isn't `ff` as `STAND_NODE_NAME` entry *n* into node slot 0–9 (`0x1cfd58`). Every entry names a list of its own model and variant (`o01a_n1_std0.sna` ...) |

A table-0 row (**confirmed** where cited):

| Bytes | Meaning |
|---|---|
| 0 | model index, 0–9 (`0x1cd72c`: ≥ 10 is replaced by 0) |
| 1–109 | per-part switches, 0, 3, 4 or 7. The builders test byte *k* against the current variant's bit (`01 02 04 04` at `0x299828`, D1 D2 N1 N2), so a part shows only in the variants whose bit is set. Which byte switches which part is in the table below. Bytes 42–69 and 94–97 switch the 32 advert boards (`BUILD_ADVERTISE` `+6`). Bit 8 of bytes 43 and 52 turns their boards electric (`0x1cd9c8`) |
| 110–114 | up to five `GAME/SHADOWCOLLI.PAC` entries (1–26, 0 = none), loaded by `0x169d4` → `0x212a8` into the stadium collision object (`CStadiumCollision`) |
| 115 | crowd set, 0–17 (request `+0xa9`, read at `0x1d3848`). Picks the `AUD_SET` file (see [Crowds](#crowds)). In all 119 rows its model matches byte 0 |
| 116–127 | the 12 advert textures, copied to the request at `+0x20` when the caller leaves it empty (the offset list at `0x299750`). `0x1d31b8` turns each into a texture index (value − 1, clamped to 205, plus 7) for advert slots 1–12 |
| 128 | the `GAME/WALLCOLLI.PAC` entry (1–37), loaded by the same code |

Row bytes that switch parts (**confirmed** from the builders; slots as
in the [`.PRI` table](#pri-part-draw-priorities)):

| Bytes | Slot | Part | Rule |
|---|---|---|---|
| 1–3 | 0 | goal | the first enabled byte picks `STCMN` entry *k* − 1 |
| 4–12 | 3 | pitch pattern 1–9 | the first enabled byte *k* picks `STCMN` entry season × 9 + *k* − 1 |
| 13 | 4 | pitch edge | |
| 14, 16, 18 | 5 | bench 1–3 | first enabled |
| 20 | 1 | corner flags | |
| 25, 26 | 42, 43 | pitch lines A, B | the entry adds request byte `+7` / `+5` |
| 27–31, 32 | 7, 8 | fences 1–5, fence shadow | |
| 33, 35 / 34, 36 | 9 / 10 | nets 1–2 / their shadows | |
| 37–41 | 11 | banners | |
| 70–77 | 12–19 | stands and shadows | |
| 78–84 | 20–26 | lights | |
| 85–88 | 27–30 | spotlights | |
| 89–93 | 31–35 | caps | |
| 98–100 | 39–41 | advert rigs and the `_OP` part | only when request `+0x0d` is set (probably "adverts on") |
| 107–109 | 36–38 | staff areas | |

Bytes 15, 17, 19 (7 in 104, 3 and 12 rows), 21–24 (always 0) and 101–106
(0 or 7) are set but never read. The benches' high-detail models
(`ben1h`–`ben3h`, `STCMN` 40, 42, 44) are never loaded either, so bytes
15, 17 and 19 were probably meant for them.

The 119 rows match the 119 stadiums of `PARAM/STADIUM_DATA.TBB`
([`PARAM_DIR.md`](PARAM_DIR.md)). Models 3–5 (`ho01b`, `ho02a`, `ho03a`)
cover 90 of them. `stadium.py build DAT/STADIUM <id>` prints one row.

## `CONV_INFO_BUILD.TBB`

One table of 150 bytes. `0x1ce0b8` (called from `0x1ca3d4`) reads three
bytes `a`, `b`, `c` and returns the stadium id `t[b*25 + a*5 + c]`,
keeping `b`. So it is 6 rows × 5 × 5 stadium ids (**confirmed**).

The same 150 bytes are `PARAM/PLRESOURCESIM.PAC` entry 10, which
`plTeam_GetStadiumDataIndex(stadium, league)` (`SLES 0x22c1e0`) reads to
turn a club's stadium into a stadium id (**confirmed**):

- **Row** `b` = `PlLeague`, one of the 6 leagues.
- **Level** `a` = `plTeam_Stadium2StadiumLv(stadium type)` (`0x229f40`):
  type 0–1 → 0, 2–5 → 1, 6 → 2, 7 → 3, 8 → 4.
- **Variant** `c` comes from the `PlTeam_Stadium` facilities (`+3` stand,
  `+6` roof, `+9` lights, set by `plTeam_BuildStadiumStand`/`Roof`/`Light`):
  - stand < 0 → 0; stand 0 or 1 → that value; stand ≥ 3 → 2
  - stand 2 → 2, or 3 once the roof is built, or 4 once the roof and the
    lights are built

Every id in the level-*N* block uses a `ho0N` model. The 6 league rows
differ only in which `ho00`/`ho01` model levels 0 and 1 use. 102 of the
150 ids are distinct. So a club's ground grows through the `ho00`–`ho04`
models as its stadium type goes up, and through the 5 variants as it adds
a stand, roof and lights.

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
| 1–9 | one per section, one 8-byte row per tier: `{u32 capacity, u16 fill, u8 flag, u8 0}` (**confirmed**, `0x1d73c0` and `0x1d7d00`). The capacity (240–10000 across the 326 tiers in use) is most likely the number of people the tier holds, and fill/1024 its fill ratio. The flag (0/1) is copied into the tier's work data. Rows past the tier count are zero, except a 3600-person row in section 6 of `HO01A_2` and `_3`, whose tier count is 0 so the game skips it |
| 10 | crowd blocks, 40 bytes each: `char[32]` name, `u8 section`, `u8 tier`, `u8 flag` (0/1, read at `0x1d83f8`), then two copies of one byte (`+0x23`, `+0x26`) that count up through the file or are 0. The game only reads `+0x20`–`+0x22`. The name builds the model name `<model>_<variant>_aud_<name>.snj` (`0x1d5b08`), and every block has its model in all four `AUD_MODEL` packs. Every tier is below its section's tier count |
| 11 | 1 byte, 1 or 2: the number of high-detail tiers. `0x1d6ac4` builds blocks whose tier is below it with the high-detail crowd (driven by `AUD_JAM_HI`) and the rest with the low-detail one (`AUD_JAM_LW`) |

`AUD_JAM_HI` and `AUD_JAM_LW` control how the crowd fills up (the debug
line `  %s %3d%% [%d:%d]` at `0x29a210` prints `hi`/`lw` and a percentage):

- **`AUD_JAM_HI`**: 2 tables of 11 rows × 10 bytes (not the TBB line size
  of 8): `{u16 amount[3], u16 palette, u16 threshold}`. `0x1d8188` picks
  the last row whose threshold/1024 is at or below the fill ratio.
  `0x1d836c` passes the three amounts as `1 − v/1024` to `0x1d5540`, one
  per figure group 1–3 of the crowd model. `0x1dbe40` then takes that
  fraction of the group's figures, most likely leaving those seats empty.
  `+6` selects a palette through `0x29a448`.
- **`AUD_JAM_LW`**: 4 rows of `{u16 threshold, u16 level}`, searched the
  same way (`0x1d8548`). Thresholds are 0, 307, 512 and 716.

All thresholds ascend. The names suggest the high- and low-detail crowds
(`txcmn_aud_hi_00.svr`, `txcmn_aud_lw_00.svr`).

## Still unknown

- What sets the night flag (request `+0x88`) that picks `N2` over `N1`,
  and what the request byte `+7` for pitch lines A is.
- What the crowd block flag (`+0x22`) and the tier flag do in the draw
  code, beyond being copied.
- Slot 6: every `.PRI` file gives it a priority (60), but nothing loads a
  part into it.

## Checking the claims

```bash
python SRC/stadium.py info  DAT/STADIUM DAT/PARAM    # every table and the cross-references
python SRC/stadium.py pri   DAT/STADIUM/HO00A.PRI    # the 44 priorities
python SRC/stadium.py build DAT/STADIUM 6            # one stadium row, with its crowd set and table-2 bytes
python SRC/stadium.py crowd DAT/STADIUM/AUD_SET_HO03A_3.TBB   # sections and crowd blocks
python SRC/pac.py list DAT/STADIUM/AW01A_D1.PAC
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 1caf18 48 --sles ISO/SLES_541.51   # .PRI reader
```
