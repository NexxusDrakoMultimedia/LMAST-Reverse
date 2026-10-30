<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

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
night with `+5` = 0 and 4 for night otherwise. `+5` is the weather: 0 fine,
1 cloudy, 2 rain, 3 snow (the sky names `f_sky`, `c_sky`, `r_sky`, and the
Stadium Viewer's list FINE, CLOUDY, RAIN, SNOW at `0x24d510`). `+6` is the
season, 0–3 = the `sp`, `su`, `au`, `wi` names.

**The night flag (confirmed).** `+0x88` is byte 82 of the stadium's
`BUILD_STADIUM` row, because the build code copies the 129-byte row to
request `+0x36` (`0x1cd680`). Every caller of the picker passes
"`+0x88` ≠ 0" as the flag (`0x1cd864`, `0x1ce9ac`, `0x1cdaac`). Byte 82 is
the switch for the `LIGHT_1` part (the second set of floodlights, below),
so **a stadium uses `N2` at night exactly when it has `LIGHT_1`**.

**Empirical.** 19 of the 119 stadiums set byte 82: ids 10, 15, 20, …, 95
and 111. Every stadium sets exactly one of byte 81 (`ILLUMINATION_0`) and
byte 82. In `CONV_INFO_BUILD` the 18 ids 10–95 are exactly the variant-4
stadiums of levels 1–3, the ground with stand, roof and lights built
([below](#conv_info_buildtbb)); the variant-4 stadiums of levels 0 and 4
use `N1`. So building the lights at a club's ground switches its night
lighting to `N2`. Stadium 111 (`ho02a`) isn't in `CONV_INFO_BUILD`.

## The build request

The developer Stadium Viewer (module 171, see
[`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)) edits a build
request field by field. Its BUILD panel's handler (`GAMEPRG.REL 0x1c7d08`,
jump table `0x298a50`) names these fields (**confirmed**):

| Offset | Viewer name | Contents |
|---|---|---|
| `+0x00` (u32) | DATA_INDEX | stadium id, 0–118 |
| `+0x04` | TIME_ID | 0 day, 1 night |
| `+0x05` | WEATHER_ID | 0 fine, 1 cloudy, 2 rain, 3 snow |
| `+0x06` | SEASON_ID | 0 spring, 1 summer, 2 autumn, 3 winter |
| `+0x07` | LANDSCAPE_LEVEL | added to the `LANDSCAPE_A` part's entry (`lna01`–`04`) |
| `+0x08` | NATION_ID | 0 England, 1 France, 2 Germany, 3 Italy, 4 Spain, 5 Holland |
| `+0x09`, `+0x0a` | TEAM_COLOR1_16, TEAM_COLOR2_16 | – |
| `+0x0b` | MONTH_ID | 0 January … 11 December (picks the pitch edge, table 1) |
| `+0x0c`, `+0x0d` | – | pitch edge (from table 1) and adverts on (below) |
| `+0x0e` | – | advert board style: 1 makes boards 43 and 52 electric (sets bit 8, `0x1cd9c8`); 2 replaces boards 43–45 and 52–54 with 46–50 and 55–59 (`0x1cda28`, lists at `0x2997a0`, `0x2997a8`). Each applies only if the boards it starts from are on |
| `+0x0f` | – | advert board level: clears boards 95–97, then turns on board 95 at level ≥ 2 and 96 at ≥ 3 for `ho01a`/`ho01b`, 95 at ≥ 4 for `ho02a` and 95 at ≥ 5 for `ho03a` (`0x1cd8c8`, `{model, level, byte}` list at `0x299788`) |
| `+0x10` | – | when set, the 11 advert textures at `+0x20` move up one and `+0x20` becomes 232 (`0x1cd618`), which the texture clamp at `0x1d31b8` turns into the last advert texture |
| `+0x11`, `+0x12` | HOME_TEAMCOLOR, AWAY_TEAMCOLOR | – |
| `+0x13` | – | not read by the stadium code |
| `+0x14`, `+0x18`, `+0x1c` (u32) | HOME_SUPPORTER, AWAY_SUPPORTER, CIVILIAN_VISITOR | crowd sizes (110000 each by default) |
| `+0x20` | ADVERTISE_INDEX | the first of the 12 advert textures at `+0x20`–`+0x2b` ([Adverts](#adverts)) |
| `+0x2c`–`+0x35` | – | the stand node lists (table 2) |
| `+0x36`–`+0xb6` | – | the stadium's `BUILD_STADIUM` row |

The value names (DAY/NIGHT, FINE…SNOW, SPRING…WINTER, ENGLAND…HOLLAND,
JAN…DEC) are the viewer's lists at `GAMEPRG.REL 0x24d4c8`–`0x24d554`. Its
CREATE panel has STADIUM_LEVEL, NATION_ID and STAND_LEVEL instead of
DATA_INDEX. **Tested in PCSX2:** the viewer builds and shows stadiums from
these settings (see [`SQB_FORMAT.md`](SQB_FORMAT.md)).

## Directory overview

| Files | Count | Entries | Contents |
|---|---|---|---|
| `<MODEL>_{D1,D2,N1,N2}.PAC/.HED` | 40 | 46 each, PRSH `.sno` | the stadium's own parts: stands, fences, nets, roofs (`aw01a_d1_fen1.sno`) |
| `<MODEL>_OP.PAC/.HED` | 10 | 1 PRSH `.sno` | one extra part per model (`01a_avm1.sno`) |
| `<MODEL>.PRI` | 10 | – | draw priority of each part slot, see below |
| `STCMN_{D1,D2,N1,N2}.PAC/.HED` | 4 | 55 each | parts shared by all models: goals (`d1_gol01.sno`), pitches (`pit01_sp.sno`), ... |
| `STCMN_SK.PAC/.HED` | 1 | 20 | skies: five per season (`sp`, `su`, `au`, `wi`), day fine, cloudy and rain (`f_`, `c_`, `r_sky`), then night fine and cloudy; entry season × 5 + *k*, [above](#the-10-models) |
| `STADIUM_SVR.PAC` | 1 | 635 PRSH `.svr` | shared textures (`sky_cloud3.svr`, `txcmn_fen1_01.svr`, ...). The only pack here with no `.HED`. Also named in `GAMEPRG.REL 0x26651a` (`CMatchStadium`) |
| `SEAT_CLUT.PAC/.HED` | 1 | 16 `.svp` | seat colour palettes (`_seat_00.svp` ...) |
| `STAND_NODE_NAME.PAC/.HED` | 1 | 58 `.sna` | node-name lists for the stands |
| `STAFF_NODE_NAME.PAC/.HED` | 1 | 11 `.sna` | node-name lists for the bench area, one per model (`aw01a` twice) |
| `ADT_<MODEL>_{D1,D2,N1,N2}.PAC/.HED` | 40 | 32 PRSH `.snj` | advertising boards ("ADT"). Loaded at `0x1d2e74` by `CAdvertiseLoader` |
| `ADT_TEXCMN.PAC/.HED` | 1 | 419 `.svr` | advert textures. Entries 7–211 are PRSH-compressed copies of sponsor logos 0–204 of `0SYSTEM/SPONSOR_TEXTURE_M.PAC` ([`0SYSTEM_DIR.md`](0SYSTEM_DIR.md)), identical once expanded (**empirical**), which fits the `+ 7` of the advert texture index below |
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
| `DUMMY.DAT` | 1 | 0 bytes | – |

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

The Stadium Viewer's VISIBLE menu names the 44 slots, in slot order
(`GAMEPRG.REL 0x24d3c8`): GOAL, CFLAG, SKY, PITCH, PITCH_PEEL, BENCH_LOW,
BENCH_HIGH, FENCE, FENCE_SHADOW, NET, NET_SHADOW, BANNER, STAND_0 …
STAND_SHADOW_3, LIGHT_0, LIGHT_SHADOW_0A, LIGHT_SHADOW_0B, ILLUMINATION_0,
LIGHT_1, LIGHT_SHADOW_1, ILLUMINATION_1, SPOT_0–3, STAND_CAP_1–5,
STAFF_0–2, AURORA_VISION_1, AURORA_VISION_SHADOW_1,
AURORA_VISION_MONITOR_1, LANDSCAPE_A and LANDSCAPE_B. They match the
slots the builders use below and the part file names (`lig0`, `lis0a`,
`ilm0`, `lna`, `lnb`). `stadium.py build` prints them.

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
| 6 | bench, high detail (`BENCH_HIGH`) | nothing loads this slot (see the unused bytes 15, 17, 19 below) |
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
| 42, 43 | landscape A, B (the scenery behind the stands) | `STCMN` 46–49 (`lna`), 50–54 (`lnb`) |

So the model packs' 46 entries are slots 7–40 plus the two pitch edges.

## `BUILD_STADIUM.TBB`

Three tables. `GAMEPRG.REL 0x1cd648` builds a stadium from a request whose
`+0` is the stadium id (reset to 0 if ≥ 119):

| Table | Rows × size | Reader | Contents |
|---|---|---|---|
| 0 | 119 × 129 | `0x1cdb38` (`id * 0x81`) | one row per stadium. The row is copied to the request at `+0x36` |
| 1 | 10 × 12 | `0x1cdbb0` | one row per model. The request's byte `+0x0b` (the month, 0–11, see [the build request](#the-build-request)) picks a value, 1 or 2, stored at `+0x0c`. It chooses the pitch edge: 1 = `ptp_su`, 2 = `ptp_wi` (`0x1cef54`). Most rows read `2 2 2 2 2 1 1 1 1 2 2 2` or similar: the winter edge from October to May, the summer edge from June to September |
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
| 13 | 4 | pitch edge | – |
| 14, 16, 18 | 5 | bench 1–3 | first enabled |
| 20 | 1 | corner flags | – |
| 25, 26 | 42, 43 | landscape A, B | the entry adds request byte `+7` (landscape level) / `+5` (weather) |
| 27–31, 32 | 7, 8 | fences 1–5, fence shadow | – |
| 33, 35 / 34, 36 | 9 / 10 | nets 1–2 / their shadows | – |
| 37–41 | 11 | banners | – |
| 70–77 | 12–19 | stands and shadows | – |
| 78–84 | 20–26 | lights | – |
| 85–88 | 27–30 | spotlights | – |
| 89–93 | 31–35 | caps | – |
| 98–100 | 39–41 | advert rigs and the `_OP` part | only when request `+0x0d` is set (probably "adverts on") |
| 107–109 | 36–38 | staff areas | – |

Bytes 15, 17, 19 (7 in 104, 3 and 12 rows), 21–24 (always 0) and 101–106
(0 or 7) are set but never read. The benches' high-detail models
(`ben1h`–`ben3h`, `STCMN` 40, 42, 44) are never loaded either, so bytes
15, 17 and 19 were probably meant for them.

The 119 rows match the 119 stadiums of `PARAM/STADIUM_DATA.TBB`
([`PARAM_DIR.md`](PARAM_DIR.md)). Models 3–5 (`ho01b`, `ho02a`, `ho03a`)
cover 90 of them. `stadium.py build DAT/STADIUM <id>` prints one row.

### Editing

`stadium.py` writes table 0 in place; the file keeps its size and every
other byte. Both commands take `<in> <out>` and never change the input.

| Command | What it writes |
|---|---|
| `setlook <in> <out> <id>=<src id> ...` | stadium *id* built like stadium *src*: its row's bytes 0–115 and 128 (model, parts, crowd set, collision) copied from *src* as the file held it (`copy_rows`, which `--mod real-grounds` uses too). Bytes 116–127, the boards, stay the stadium's own |
| `setboards <in> <out> <id> <v1> ... <v12> [<id> ...]` | the stadium's 12 advert textures, bytes 116–127. Value *v* is logo *v* − 1 of `SPONSOR_TEXTURE_M` (`0x1d31b8`), 1–205. 206 and up all draw `ADT_TEXCMN` entry 212, adidas, which the match puts first on every ground by itself ([`LMASTER_MOD.md`](LMASTER_MOD.md#stadiums)), so they are refused. Repeats within a row are allowed (every retail row has 12 different ones) |

`roundtrip` edits each of the 119 rows on its own (its look copied from
the next row, then 12 new boards) and marks with `!!` any byte that
changes outside the edited ones, or a row whose own values don't give
the file back. It passes on the disc's file (`stadium_roundtrip` in
`regress.py`).

The editor's Stadiums tab ([`USAGE.md`](../USAGE.md#the-window)) edits
through these two. A mod folder's own `BUILD_STADIUM.TBB` still builds
with `--mod real-grounds` and `sponsor-boards` (LMASTER full and max):
each switch is applied to the file as `DAT` holds it, and each row's
look and boards take the switch's bytes only where the target left them
as they were (`stadium.keep_edits`), so the editor's own edits win row
by row. Checked on scratch LMASTER full and max builds (2026-10-30) with
a target where stadium 5 is built like 100 with new boards and 6 like 7:
those rows kept the target's bytes, 102–118 took the real grounds' looks,
the other rows the sponsor boards, and 114 stayed as it was. Not yet
seen in the game.

```bash
python SRC/stadium.py setlook   DAT/STADIUM/BUILD_STADIUM.TBB out.tbb 5=100
python SRC/stadium.py setboards DAT/STADIUM/BUILD_STADIUM.TBB out.tbb 5 1 2 3 4 5 6 7 8 9 10 11 12
python SRC/stadium.py roundtrip DAT/STADIUM
```

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
| 1–9 | one per section, one 8-byte row per tier: `{u32 capacity, u16 fill, u8 flag, u8 0}` (**confirmed**, `0x1d73c0` and `0x1d7d00`). The capacity (240–10000 across the 326 tiers in use) is most likely the number of people the tier holds, and fill/1024 its fill ratio. The flag (0/1) picks the tier's fill curve: it is copied to byte `+0x10` of the tier's work record, which indexes the tables of `AUD_JAM_HI` (pointer array at `+0x124`, filled at `0x1d3a30`; read at `0x1d82ec`, then searched by `0x1d8188`). So flag 0 uses `AUD_JAM_HI` table 0 and flag 1 table 1 (**confirmed**). Rows past the tier count are zero, except a 3600-person row in section 6 of `HO01A_2` and `_3`, whose tier count is 0 so the game skips it |
| 10 | crowd blocks, 40 bytes each: `char[32]` name, `u8 section`, `u8 tier`, `u8 flag` (0/1, see [crowd kinds](#crowd-kinds)), then two copies of one byte (`+0x23`, `+0x26`) that count up through the file or are 0. The game only reads `+0x20`–`+0x22`. The name builds the model name `<model>_<variant>_aud_<name>.snj` (`0x1d5b08`), and every block has its model in all four `AUD_MODEL` packs. Every tier is below its section's tier count |
| 11 | 1 byte, 1 or 2: the number of high-detail tiers. `0x1d6ac4` builds blocks whose tier is below it with the high-detail crowd (driven by `AUD_JAM_HI`) and the rest with the low-detail one (`AUD_JAM_LW`) |

### Crowd kinds

**Confirmed.** The build request's three crowd sizes (`+0x14` home
supporters, `+0x18` away supporters, `+0x1c` other visitors) are split
over the 9 sections (`0x1d7998`) and then over each section's tiers
(`0x1d73c0`). For each tier `0x1d7d00` sums the three counts into its fill
ratio (sum / capacity) and sorts the three kinds (0 home, 1 away, 2
visitors, starting order at `0x29a1e0`) by count. It stores the largest
kind in the tier's work record at `+8` and the second at `+0xc`. The
debug line `  %s %3d%% [%d:%d]` prints the fill and these two kinds.

A crowd block's model has two materials, and `0x1d83dc` gives material
0 or 1 (`GetSingleMaterial` through `0x1d53a0`) the tier's main kind and
the other its second kind. The block flag decides which: with flag 0 the
home supporters (when they are one of the two) go to material 0, with
flag 1 to material 1. When home fans aren't in the top two, the flag
swaps the away fans and visitors the same way. Each material then gets
palette `kind × 3 + p` of the 9 at crowd object `+0x264`
(`change_pallet_texturelist`; the table at `0x29a448` is 0–8 in order),
where p is the `AUD_JAM_HI` row's palette. The tier's work records are
`+0x27c + section × 0x64 + tier × 0x14` in the crowd object.

### Crowd models

**Confirmed.** `0x1d5340` sorts the models: one with 2 or more materials
and 3 or more nodes (object `+0x10`, `+0x28`) is a **three-group** crowd.
For it `0x1d836c` passes `AUD_JAM_HI`'s three amounts to `0x1d5540` as
groups 1–3, and `0x1dbba8` takes group *g* to be the meshsets whose node
(meshset `+0x10`) is *g*. Any other model is drawn with material 0 only,
in the tier's main kind (`0x1d84e8`), without the groups.

**Empirical** (`python SRC/stadium.py info DAT/STADIUM`, over all 2,800
models in the 40 `AUD_MODEL` packs):

- Every three-group model has 4 nodes (a root and nodes 1–3) and 6
  meshes, one per node and material. Every figure is one 4-vertex quad.
  The low-detail models have 2 nodes and one mesh, on node 1 with
  material 0. The rest have no meshes.
- In the `D1`, `D2` and `N1` packs, 292 of the 294 blocks on a
  high-detail tier (below table 11's count) have a three-group model, and
  all 230 on a low-detail tier have a low-detail one. The two exceptions
  are `aw01a` blocks `2b` and `2k`, high-detail tiers with low-detail
  models.
- **The three groups are the block's front, middle and back rows.** In
  all 172 three-group models of a `D1` pack, group 1's figures sit
  lowest on average, then group 2, then group 3; in 63 of them the three
  height bands don't overlap at all. Group 1 holds 64% of the figures on
  average, groups 2 and 3 about 18% each. A figure's nearest neighbour is
  in its own group 89% of the time (34% if the groups were mixed).
- `N2` has no crowd at all for the six models with one set (`ho00a`,
  `ho00b`, `ho04a`, `aw01a`, `aw03a`, `aw04b`: 182 blocks with empty
  models). No stadium reaches them: the 19 stadiums with `LIGHT_1` (so
  `N2` at night) all use a `_3` set of `ho01a`, `ho01b`, `ho02a` or
  `ho03a`, whose `N2` models are all there. A stadium edited to use one
  of the six with `LIGHT_1` would play night matches to empty stands;
  `info` marks that with `!!`.

### Fill curves

`AUD_JAM_HI` and `AUD_JAM_LW` control how the crowd fills up (the debug
line `  %s %3d%% [%d:%d]` at `0x29a210` prints `hi`/`lw` and a percentage):

- **`AUD_JAM_HI`**: 2 tables of 11 rows × 10 bytes (not the TBB line size
  of 8): `{u16 amount[3], u16 palette, u16 threshold}`. `0x1d8188` picks
  the last row whose threshold/1024 is at or below the fill ratio.
  `0x1d836c` passes the three amounts as `1 − v/1024` to `0x1d5540`, one
  per figure group 1–3 of the crowd model ([above](#crowd-models)).
  `0x1dbe40` then takes that fraction of the group's figures, most likely
  leaving those seats empty, so v/1024 is the share of the group still
  shown. `+6` is the palette p, 0–2 ([crowd kinds](#crowd-kinds)).

  The two tables read that way (**empirical**): table 0 (tier flag 0)
  fills from the front, with group 1 at half by 5% full and complete by
  20%, group 2 complete by 60% and group 3 last, complete at 90%. Table 1
  (flag 1) fills the three rows evenly, each a step ahead of the fill
  ratio (10% shown at 5% full, 50% at 40%), all complete from 80%. The
  palette goes from 2 at low fill to 1 from 30% (table 0) or 50% (table
  1), and to 0 from 70% or 80%. In table 0
  group 1 drops from 1024 to 819 where the palette first changes (row 4).
- **`AUD_JAM_LW`**: 4 rows of `{u16 threshold, u16 level}`, searched the
  same way (`0x1d8548`). Thresholds are 0, 307, 512 and 716.

All thresholds ascend. The names suggest the high- and low-detail crowds
(`txcmn_aud_hi_00.svr`, `txcmn_aud_lw_00.svr`).

## Still unknown

- What the crowd palettes 0–2 of each kind look like on screen (the 9
  palettes at crowd object `+0x264`; `AUD_TEAM_COLOR_CLUT_CMN` is the
  likely source), and so why table 0 thins the front rows as the palette
  changes.
- Who sets request `+0x0e`–`+0x10` in a real match (the viewer doesn't).
  `+0x10` is set in league matches: every ground shows the adidas board,
  advert texture 212, which only `+0x10` puts there (user report,
  2026-10-30, [`LMASTER_MOD.md`](LMASTER_MOD.md#stadiums)). Only the
  Stadium Viewer calls the builder `0x1cd648`; a real match goes through
  `STADIUM::CBuildData` (vtable `0x25d270`), and no code in `GAMEPRG.REL`
  stores bytes `+0x0e`–`+0x10` together, so the request is probably
  filled as words or by another module (searched 2026-10-30).
- Slot 6 (`BENCH_HIGH`): every `.PRI` file gives it a priority (60), but
  nothing loads a part into it.
- Request byte `+0x13` (not read by the stadium code).

## Checking the claims

```bash
python SRC/stadium.py info  DAT/STADIUM DAT/PARAM    # every table and the cross-references
python SRC/stadium.py pri   DAT/STADIUM/HO00A.PRI    # the 44 priorities
python SRC/stadium.py build DAT/STADIUM 6            # one stadium row, with its crowd set and table-2 bytes
python SRC/stadium.py crowd DAT/STADIUM/AUD_SET_HO03A_3.TBB   # sections and crowd blocks
python SRC/stadium.py roundtrip DAT/STADIUM          # the writer, row by row
python SRC/pac.py list DAT/STADIUM/AW01A_D1.PAC
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 1caf18 48 --sles ISO/SLES_541.51   # .PRI reader
```
