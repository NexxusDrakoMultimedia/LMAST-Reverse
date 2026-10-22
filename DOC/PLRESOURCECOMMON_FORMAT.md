<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/PLRESOURCECOMMON.PAC`: the common resource pack

`PLRESOURCECOMMON.PAC` is `plResource` entry 0 ([`PARAM_DIR.md`](PARAM_DIR.md)).
It is a BINPAC of 5 TBB1 files. Every reader calls
`plResource_GetResourceDataBinPacTbbTbl` (`0x21e9e0`) with `ePLRSRC` 0 and
**constant** entry and table numbers, so each table's reader is known
(the tables below).

`python SRC/plrcommon.py info DAT/PARAM` checks every table.
`python SRC/plrcommon.py show DAT/PARAM <entry>.<table>` prints one, with
the named fields of the facility records and nation names for entry 3.
`set` edits the facility records ([Editing](#editing-the-facility-records)).

| Entry | Tables | Contents |
|---|---|---|
| 0 | 9 | facilities: sites, training-ground, stadium, club-house, youth-house and office equipment, club houses, stadiums, stadium adverts |
| 1 | 7 | formations and pitch areas (byte tables) |
| 2 | 1 | which hexagon each ability counts towards, with a weight |
| 3 | 6 | nations, regions, national teams and each club's nation |
| 4 | 2 | each league nation's divisions and cups, and cup ids by nation |

## Entry 0: facilities

The TBB headers give these tables a line size of 4, but each is an array
of larger records. The record size is how the getter scales its index
(**confirmed**), and every table is a whole number of records:

| Table | Getter | Record | Records | What |
|---|---|---|---|---|
| 0.0 | `plTeam_GetSiteDb` (`0x229aa8`) | 0x1c | 3 | club sites |
| 0.1 | `plTeam_GetGrEquipsDb` (`0x229af0`) | 0x34 | 10 | training-ground equipment |
| 0.2 | `plTeam_GetStEquipsDb` (`0x229a18`) | 0x20 | 16 | stadium equipment |
| 0.3 | `plTeam_GetChouseDb` (`0x2299d0`) | 0x28 | 3 | club houses |
| 0.4 | `plTeam_GetDChEquipsDb` (`0x229b38`) | 0x20 | 36 | club-house equipment |
| 0.5 | `plTeam_GetDAcEquipsDb` (`0x229b80`) | 0x20 | 18 | youth-house equipment |
| 0.6 | `plTeam_GetOfEquipsDb` (`0x229bc8`) | 0x18 | 12 | office equipment: (kind × 3 + level), 4 kinds × 3 levels |
| 0.7 | `plTeam_GetStadiumDb` (`0x229c28`) | 0x80 | 9 | stadiums |
| 0.8 | `plTeam_GetStAdvertiseDb` (`0x229a60`) | 0x14 | 6 | stadium adverts |

**Build time and upkeep (confirmed).** Each `plTeam_Build*` function reads
the build time (in turns) as a u8 from the record, and `payment_Equip`
(`0x251fb8`, the monthly facility upkeep, payment type 7 in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far)) reads the upkeep
as a u32:

| Table | Build time | Read by | Upkeep |
|---|---|---|---|
| 0.0 sites | `+0xc` | `plTeam_BuildSite` (`0x229d74`) | (not read by `payment_Equip`) |
| 0.1 training ground | `+0x10` | `plTeam_BuildSiteEquip` (`0x229e1c`) | (not read) |
| 0.2 stadium equipment | `+0x10` | `plTeam_BuildStadiumEquip` (`0x22a3e0`) | `+0x14` |
| 0.3 club houses | `+0x10` | `plTeam_BuildChouse` (`0x22a928`) | `+0x14` |
| 0.4 club-house equipment | `+0x10` | `plTeam_BuildChouseChEquip` (`0x22a9f8`) | `+0x14` |
| 0.5 youth-house equipment | `+0x10` | `plTeam_BuildChouseAcEquip` (`0x22ab0c`) | `+0x14` |
| 0.6 office equipment | `+0xc` | `plTeam_BuildChouseOfEquip` (`0x22abd8`) | `+0x10` |
| 0.7 stadiums | `+0x30` + level × 0x10 | `plTeam_BuildStadium` (`0x229fc4`), `BuildStadiumStand` (`0x22a0c0`) | `+0x64` (per stand) |
| 0.8 stadium adverts | `+0xc` | `plTeam_BuildStadiumEquip` (advert form, `0x22a4a0`) | `+0x10` |

**Build cost (confirmed).** The u32 just before the build time is the
build cost: the cost getters behind `SIMPRG.REL 0x154b78` read it (sites
`+0x8`, office equipment `+0x8`, the other equipment and club houses
`+0xc`, stadiums `+0x2c`). The game scales it by the business cycle and
any sponsor discount before charging it ([`ECONOMY.md`](ECONOMY.md#build-costs)).
It is 0 or −1 where the build time is 0 (what a club starts with), and
it grows with the facility (club houses 0, 45,000,000 and 90,000,000;
sites 0, 60,000,000 and 120,000,000; stadium equipment 900,000 to
90,000,000). The stadium, training-ground, club-house and youth-house
equipment records hold a second cost at `+0x1c` (training ground also
`+0x30`), charged by its own build kind. **Empirical:** it is a tenth of
the build cost. The upkeep the facility window shows is the upkeep
column above; for sites it is `+0x10`, which `payment_Equip` doesn't
read. The first words of each record hold −1 or small numbers
(requirements, by the look of them); they aren't traced.

**Stadiums.** The stand levels are 16-byte records at `+0x30`,
`+0x40` and `+0x50`, each starting with its build time; the capacity of
level *n* is the u32 at `+0x38` + *n* × 0x10 (**confirmed**:
`pwkUnkei_GetStandAllCapacity`, `0x271b48`, see
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far)). The roof, light
and screen builds read a build time from `+0x60` onwards
(`plTeam_BuildStadiumRoof`, `Light`, `Screen`). **Empirical:** stadiums 0
and 1 (the starting ones) hold 8,000 with no other levels; stadiums 2–5
hold 15,000, 20,000 and 25,000; 6 holds 30,000, 35,000 and 40,000; 7
holds 50,000–60,000; 8 holds 110,000 at every level. Which stadium is
which, and the rest of the record, aren't traced.

### Editing the facility records

`plrcommon.py set <in.PAC> <out.PAC> <table>:<record>:<field>=<value> ...`
writes a new pack. Only the edited words change; the pack keeps its
size. Every field it offers is read by the code named above or in
[`ECONOMY.md`](ECONOMY.md#build-costs):

| Field | Tables | What | Range |
|---|---|---|---|
| `cost` | all | build cost (stadiums: `+0x2c`, the stadium's price) | 0–2,147,483,647 |
| `cost2` | 0.1, 0.2, 0.4, 0.5 | the second cost at `+0x1c` | as `cost` |
| `cost_b`, `cost2_b`, `upkeep_b` | 0.1 | `+0x20`, `+0x30`, `+0x28`: what training-ground slots past the club's first group use (`0x1550f0`) | as `cost` |
| `upkeep` | all | monthly upkeep (stadiums: `+0x64`, per stand) | as `cost` |
| `time`, `time0`–`time2` | all; 0.7 per level | build time in turns, read as a u8 | 0–255 |
| `capacity0`–`capacity2` | 0.7 | a stadium level's capacity | 1–2,147,483,647 |

Money is in the stored unit (£1 = 6, €1 = 4) and read as a signed
word, so it stays below 2^31. A capacity of 0 would divide by zero
after a home match (`pwkUnkei_BeforeReport`, `0x272f9c`). The game still
scales a build cost by the business cycle and any sponsor discount.
The upkeep of sites (0.0) and the training ground (0.1) is only shown
in the facility window; `payment_Equip` doesn't charge it.

The file has copies in `PRELOAD` packs ([`REBUILD.md`](REBUILD.md)), so
patch an edit onto a disc with `patch_disc.py --copies`.

`plrcommon.py roundtrip` rebuilds the pack unchanged, then edits each of
the 494 fields of the 113 records on its own and checks that only that
field's word changes and reads back. It passes on the PAL and Japanese
packs.

**Not yet tested in PCSX2:** that an edited cost shows in the facility
window and is charged.

## Entry 1: formations

Seven byte tables, read by the formation and pitch-area functions
(**confirmed**, constant arguments):

| Table | Bytes | Reader |
|---|---|---|
| 1.0 | 700 | `plTeam_FormationID2Formation` |
| 1.1 | 90 | `plTeam_PitchArea2Apos` |
| 1.2, 1.3 | 1,419 each | `plTeam_AreaMatrix2AreaMy`, `AreaMatrix2AreaCom` |
| 1.4 | 32 | `plTeam_GetSystem2PosNum` |
| 1.5 | 8 | `plTeam_GetPosNumLimit` |
| 1.6 | 26 | `plTeam_GetAPosNumLimit` |

The meanings of the values aren't traced; `show` prints them as bytes.

## Entry 2: hexagon abilities

512 bytes read by `plPinfo_CalcHexAbil` (**confirmed**): 8 bytes per
ability, each 4-byte half two `{u8 hexagon, u8 weight}` pairs (`+0` the
goalkeeper variant, `+4` the field-player one). The detail screen's
hexagon is the weighted average; the layout and the six hexagons are in
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#abilities-and-the-detail-screen).

## Entry 3: nations

| Table | Bytes | Reader | What |
|---|---|---|---|
| 3.0 | 13 | `plMisc_DRegion2Region` | the region of each of 13 display regions |
| 3.1 | 146 | `plMisc_Nati2DRegion` | each nation's display region |
| 3.2 | 146 × u16 | `plMisc_Nati2NatiTeam` | each nation's national team (team id, 460 = `0x1cc` on) |
| 3.3 | 83 | `plMisc_NatiTeam2Nati` | the nation of national teams 460–542 |
| 3.4 | 146 | `plMisc_Nati2EU` | a 0/1 flag per nation; the reader's name says EU, what uses it isn't traced |
| 3.5 | 460 | `plMisc_Club2Nati` | each club's nation (`0x215b64`; teams 1 and 2 use your league's nation instead) |

**Empirical:** 3.3 gives England for team 460, France 461, Germany 462,
Italy 463, Spain 464 and the Netherlands 465, and every value is a nation
1–145. Every value in 3.5 is below 146. `pbdata.nation_names` already
uses 3.2 to name nations, and the club ranking in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) uses 3.5.

## Entry 4: competitions

| Table | Bytes | Reader |
|---|---|---|
| 4.0 | 7 × 22 | `0x20fbf0`, below |
| 4.1 | 96 × 8 | `plCompeData_getCupUID_FromNation` |

### Table 4.0: divisions and cups by nation

Seven records of 11 s16, one per league nation (`PlNati` 1–6, England to
the Netherlands) after an empty record 0. `0x20fbf0` returns the record
whose `+0x00` is the nation, or record 0 when none is (`0x20fc48`).
**Confirmed** from its four callers:

| Offset | Field | Reader |
|---|---|---|
| `0x00` | nation | `0x20fc48`, the lookup |
| `0x02`, `0x04` | competition (`PLSCHE_COMPE`) of the first and second division | `plCompeData_getScheCompe_FromNationDiv` (`0x20fc80`): `+0x02 + 2 × div` |
| `0x06`–`0x0a` | the nation's three cup competitions | `0x20fcf8` copies up to `plCompeData_getCupListSize` (3) of them from `+0x06` |
| `0x0c`, `0x0e` | schedule UID of the first and second division | `plCompeData_getUID_FromNationDiv` (`0x20fcb8`): `+0x0c + 2 × div` |
| `0x10`–`0x14` | the nation's three cup UIDs | `0x20fd88`, from `+0x10` |

The second division's UID is the own-nation version, the one with your
club and the rival (England: 0 and 1, competitions 0 and 1; France: 10
and 11). The relegation game over reads that UID's regulations
([`REGULATION_FORMAT.md`](REGULATION_FORMAT.md#place-slots)). The table
was labelled `plCombi_GetCombinationGrow` before: that is the symbol
just before `0x20fbf0`, which has no name of its own.

Table 4.1 is not decoded.

## Still unknown

- The first words of each facility record.
- The rest of the stadium record (`+0x0`–`+0x2f`, `+0x60`–`+0x7f`) and
  which stadium is which.
- What the values in entry 1 and table 4.1 mean.
- The facility names: which message category names each record.

## Checking

```bash
python SRC/plrcommon.py info DAT/PARAM
python SRC/plrcommon.py show DAT/PARAM 0.3
python SRC/plrcommon.py roundtrip DAT/PARAM
python SRC/plrcommon.py show DAT/PARAM 3.3
python SRC/sles_disasm.py ISO/SLES_541.51 dis plTeam_GetChouseDb plTeam_BuildChouse payment_Equip
```
