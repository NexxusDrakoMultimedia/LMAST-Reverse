<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/PLRESOURCECOMMON.PAC`: the common resource pack

`PLRESOURCECOMMON.PAC` is `plResource` entry 0 ([`PARAM_DIR.md`](PARAM_DIR.md)).
It is a BINPAC of 5 TBB1 files. Every reader calls
`plResource_GetResourceDataBinPacTbbTbl` (`0x21e9e0`) with `ePLRSRC` 0 and
**constant** entry and table numbers, so each table's reader is known
(the list is in [`PARAM_DIR.md`](PARAM_DIR.md#plresourcecommonpac)).

`python SRC/plrcommon.py info DAT/PARAM` checks every table.
`python SRC/plrcommon.py show DAT/PARAM <entry>.<table>` prints one, with
the named fields of the facility records and nation names for entry 3.

| Entry | Tables | Contents |
|---|---|---|
| 0 | 9 | facilities: sites, training-ground, stadium, club-house, youth-house and office equipment, club houses, stadiums, stadium adverts |
| 1 | 7 | formations and pitch areas (byte tables) |
| 2 | 1 | 512 bytes for the hexagon abilities |
| 3 | 6 | nations, regions, national teams and each club's nation |
| 4 | 2 | combination growth and cup ids by nation |

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

**Empirical:** the u32 just before the build time is the build cost: it
is 0 or −1 where the build time is 0 (what a club starts with), and it
grows with the facility (club houses 0, 45,000,000 and 90,000,000; sites
0, 60,000,000 and 120,000,000; stadium equipment 900,000 to 90,000,000).
The code that charges it isn't traced. The first words of each record
hold −1 or small numbers (requirements, by the look of them); they aren't
traced either.

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

512 bytes read by `plPinfo_CalcHexAbil` (**confirmed**). Not decoded.

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
| 4.0 | 7 × 22 | `plCombi_GetCombinationGrow` |
| 4.1 | 96 × 8 | `plCompeData_getCupUID_FromNation` |

Not decoded.

## Still unknown

- The first words of each facility record, and which code charges the
  build cost.
- The rest of the stadium record (`+0x0`–`+0x2f`, `+0x60`–`+0x7f`) and
  which stadium is which.
- What the values in entries 1, 2 and 4 mean.
- The facility names: which message category names each record.

## Checking

```bash
python SRC/plrcommon.py info DAT/PARAM
python SRC/plrcommon.py show DAT/PARAM 0.3
python SRC/plrcommon.py show DAT/PARAM 3.3
python SRC/sles_disasm.py ISO/SLES_541.51 dis plTeam_GetChouseDb plTeam_BuildChouse payment_Equip
```
