<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/CAMP_LIST.TBB` and `CAMP_EXPLANE.TBB`: training camps

The 153 places a club can hold a training camp: where each is, what
kind of camp it is, the clubs of its area, and the description shown
for it. Both files are TBB1 files ([`TBB_FORMAT.md`](TBB_FORMAT.md)) of
u16 values. Neither has a copy elsewhere on the disc.

`python SRC/camp.py info DAT/PARAM` checks both files and
`python SRC/camp.py show DAT/PARAM 604` prints a camp. The data has two
bugs, [below](#two-bugs), which `patch_disc.py --mod camp-types` and
`--mod camp-cities` fix; `--mod camp-santiago` and `--mod camp-clubs`
fix two smaller slips (Santiago's description and Canberra's clubs).
All four are part of the [LMASTER Mod](LMASTER_MOD.md).

## Who reads them

| Address | What it shows |
|---|---|
| `SIMPRG.REL 0x4bdd0` | finds the `CAMP_LIST` table 0 record whose `+0x04` is a city (records `0xe` bytes apart, up to `+0x85e`) and returns its `+0x0c` (`lbu`). **confirmed** |
| `SIMPRG.REL 0x4bea0`, `0x4bfd0` | the same search, returning `+0x06` (`lbu`) and whether `+0x0a` is set. **confirmed** |
| `SIMPRG.REL 0xa5488`–`0xa5558` | books a camp: the camp record (`pwkSche_GetCamp`, `PlPwork` task 6 `+0x1b00`) gets the week at `+0x0a`, 1 at `+0x1c`, the city at `+0x18` and `0x4bdd0`'s value at `+0x3c`. **confirmed** |
| `pwkSche_GetCampType` (`0x255690`) | returns `+0x3c` of the running camp. Its callers are the training module (`SIMPRG.REL 0x1586b4`, the row of [`TRAINING_LIST`](TRAINING_FORMAT.md) table 10) and `pwkSche_CheckCampSucucess` (`0x256948`). **confirmed** |
| `SIMPRG.REL` load lists `0x1cdd30` (entry 3), `0x23d618` | load `Camp_list.tbb` for the camp screen's module and for the training module during a camp |
| `SIMPRG.REL` load list `0x225d78` (entry 3) | loads `Camp_Explane.tbb` |
| `SIMPRG.REL 0xa4a80` | walks `CAMP_EXPLANE`'s 153 pairs (`0x99`, resource 3 of the list at `0x225d78`) for a city and returns its message, or 0 when no pair matches. **confirmed** |

## `CAMP_LIST.TBB`

**Table 0**: 153 records of 7 u16, one per camp.

| Offset | Name (`camp.py`) | Meaning | Proof |
|---|---|---|---|
| `0x00` | `region` | the nation's display region, 0–12 | **empirical**: equals `PLRESOURCECOMMON` table 3.1 for the nation in all 153 |
| `0x02` | `nation` | `PlNati` | **empirical** (1 for the English camps) |
| `0x04` | `city` | `PlCity`, the key | **confirmed** (`0x4bdd0`) |
| `0x06` | `level` | 0–7: the popularity the club needs in the camp's region | `0x459a8`, [below](#when-a-camp-is-open). **confirmed** |
| `0x08` | `event_only` | 1: hidden until an event frees the camp | `0x4c65c`, below. **confirmed** |
| `0x0a` | `unk0a` | 0 or 1 | only `0x4bfd0` reads it, and nothing calls that. Unused |
| `0x0c` | `type` | the camp type, 1–87 on the disc | **confirmed** (`0x4bdd0`, the booking) |

**Table 1**: 737 `{u16 city, u16 club}` pairs, 4 to 8 per camp city: the
clubs of the camp's area (**empirical**: London lists Highbury, Chelsea,
Tottenham, Fulham, Charlton, Crystal Palace and West Ham, and one club
from abroad). **Confirmed**: `SIMPRG.REL 0x4c8f8` collects up to 20
clubs for the camp city chosen on screen (`+0x1e1c`), walking the pairs
in order. Its loop runs 735 times (`0x2de` + 1, both releases), so the
last two pairs, Canberra's Fukuoka and Kanagawa, are never offered. `patch_disc.py
--mod camp-clubs` raises the bound to `0x2e0` (one instruction at
`SIMPRG.REL 0x4c9d4`).

### When a camp is open

The camp map's list (`SIMPRG.REL 0x4c4e0`) takes the camps of one nation
and, for each, shows it when the camp has been freed by an event
(`pwkSche_CheckCampFree(city)`); otherwise it skips one with `event_only`
set, and then asks `0x459a8(level, nation, 0)`. `0x4c288` builds the
list for a region the same way, leaving out the six league nations
(nation below 7). Both skip the club's own home town. **Confirmed.**

`0x459a8`:

- 15 camps have their own rule (two tables at `SIMPRG.REL 0x1cdca0`,
  nations, and `0x1cdce0`, cities; Germany has two): asked about such a
  camp (the map list passes the city), the answer is whether it has been
  freed. Asked about a nation with no city (`0x4c288` passes 0), a
  nation in the list counts as open when its listed camp is freed, and
  Dakar's (80) and Sipan's (123) nations otherwise count as closed.
- Otherwise the camp is open when the club's popularity in the camp's
  region (`pwkTeam_Pop`; region 0 is the club's own nation, others the
  nation's display region + 1) is at least the level's threshold (u16
  table at `0x1cdd20`):

  | Level | 0–3 | 4 | 5 | 6 | 7 |
  |---|---|---|---|---|---|
  | Popularity | 0 | 28,800 | 36,000 | 43,200 | 50,400 |

**Who frees a camp (confirmed).** `SIMPRG.REL 0x13c418` goes through the
club's sponsors (`pwkSponsor_GetMySponsors`), takes a city for each from
`0x16a940`, and frees one that isn't free yet (`pwkSche_SetCampFree`,
`0x13c4bc`), with an event message (`0x12c058`, kind `0x10`). So a
sponsor opens its camp. Which city each sponsor gives isn't traced.

The 15 cities are Liverpool, Lyon, Leverkusen, Barcelona, Munich, Turin,
Eindhoven, Sydney, Rio de Janeiro, Buenos Aires, Johannesburg, Cairo,
Dakar, Hawaii and Sipan. PAL's table gives Liverpool as city 66, the
Japanese overlay's as 63: PAL renumbered this table along with the
cities but not `CAMP_LIST`, where Liverpool's camp is still 63
([below](#seven-english-camps-in-the-wrong-town-pal)).

**Empirical**: levels 0–7 hold 14, 23, 29, 25, 22, 20, 9 and 11 camps;
14 camps are event only. Those are the listed camps except Leverkusen
and Barcelona, plus Valencia, in both releases: all three end up closed
until freed, Leverkusen and Barcelona through the list, Valencia through
the flag.

## `CAMP_EXPLANE.TBB`

One table of 153 `{u16 city, u16 message}` pairs, read by
`SIMPRG.REL 0xa4a80` (**confirmed**, above). The messages are 6000–6152
of category 570, a sentence about each place (6007: "The famous produce
of this city is ham, cheese and excellent goalkeepers.", Parma).

Its cities equal `CAMP_LIST`'s except one: Santiago's description (6146,
"The Chilean capital …") is keyed to city 764, the camp to 774. The
Japanese release names both cities Santiago; PAL calls 764 Cruzeiro. So
the lookup finds nothing for Santiago's camp, in both releases. `python
SRC/camp.py fixsantiago` (and `patch_disc.py --mod camp-santiago`) keys
the description to city 774.

## Two bugs

### The camp type is one too high (both releases)

`CAMP_LIST` numbers the camp types 1–87, and the booking stores that
number unchanged. Both readers number them 0–86:

- `TRAINING_LIST` table 10 has 87 rows and is read at row `type`
  ([`TRAINING_FORMAT.md`](TRAINING_FORMAT.md)).
- `pwkSche_CheckCampSucucess` checks the chosen theme against three
  bytes per type at `SLES 0x552cd0` (87 rows), and gives up on a type of
  87 or more (`0x256980`).

So every camp trains as the next type and is judged by the next type's
themes, and the two camps of type 87 read past both tables. The data
shows which numbering it was made for: the theme table's goalkeeper rows
(theme 2) are 72–83, the same rows where table 10 trains saving,
catching and keeping, and the goalkeeper camps' types are 81–84. With the
game's reading Parma (type 84, "excellent goalkeepers") trains no keeper
ability, only GK aptitude +1; with `type − 1` every goalkeeper camp falls in the keeper
rows. The Japanese files and executable are the same.

`python SRC/camp.py fixtypes` (and `patch_disc.py --mod camp-types`)
lowers every type by one. Nothing else reads `+0x0c`, so the training row
and the theme check both follow.

### Seven English camps in the wrong town (PAL)

The camp tables use the Japanese release's city numbers. PAL renumbered
the English cities and moved the clubs with them (the club records put
Liverpool's clubs in city 63 in the Japanese release and 66 in PAL,
Manchester's in 38 and 40), but not the camp tables. In PAL these camps
sit in a neighbouring town while keeping the description and clubs of
the real one:

| Camp | City (Japanese, the camp tables) | That id in PAL | PAL id |
|---|---|---|---|
| Liverpool | 63 | Scunthorpe | 66 |
| Manchester | 38 | West London | 40 |
| Newcastle | 85 | Gateshead | 86 |
| Birmingham | 88 | Warwick | 89 |
| Southampton | 44 | Basingstoke | 46 |
| Blackburn | 51 | Newport | 54 |
| Sheffield | 74 | Oakham | 78 |

**Empirical**, from the city names (message category 961) of both
releases and the club records. The other 146 camps have the same name in
both, apart from spellings (Nates → Nantes, Malaga → Málaga, La Coruna →
La Coruña). `python SRC/camp.py fixcities` (and `--mod camp-cities`)
moves the seven in both files.

**Tested in PCSX2** (user report, test disc `LMAST-test-camps-mes.iso`,
a career in its second season): `camp-cities` shows Southampton,
Blackburn and Sheffield on the England list, the three that need no
popularity, in place of Basingstoke, Newport and Oakham; `camp-santiago`
gives Santiago's camp its "The Chilean capital …" description; and
`camp-clubs` lists Canberra's clubs as South Melbourne, Aichi, Fukuoka
and Kanagawa. `camp-types` passes too: over one keeper camp the three
keepers' saving, aerial ability and GK aptitude gained 559–617
experience each, catching and rushing out 444–488, while pace and
acceleration, which only the retail row 84 trains, didn't move. That is
row 83's pattern (weights 10, 10, 10, 8, 8), about 60 experience per
point ([`TRAINING_FORMAT.md`](TRAINING_FORMAT.md#still-unknown)). The
experience was read from PCSX2 save states made just before and just
after the camp (the squad's PlPinfo array in RAM, at `0x1e2d2a4` in that
career). On the bars the gain is about one level, too little to see.
See [`LMASTER_MOD.md`](LMASTER_MOD.md#status).

## Editing

```bash
python SRC/camp.py set DAT/PARAM/CAMP_LIST.TBB out/CAMP_LIST.TBB 604 type=10
python SRC/camp.py fixtypes DAT/PARAM/CAMP_LIST.TBB out/CAMP_LIST.TBB
python SRC/camp.py fixcities DAT/PARAM out
python SRC/camp.py fixsantiago DAT/PARAM/CAMP_EXPLANE.TBB out/CAMP_EXPLANE.TBB
python SRC/patch_disc.py patch disc.iso modded.iso --mod camp-types,camp-cities,camp-santiago,camp-clubs
```

`set` takes a city, then `field=value` pairs (`type` 0–255, the other
fields 0–65535). The files keep their size. The editor's Camps tab edits
the type (0–87, the list's own numbering) and shows what it trains as the
retail game reads it and with the fix. A `CAMP_LIST.TBB` or
`CAMP_EXPLANE.TBB` written that way still gets the two fixes when the
disc is built with `--mod camp-types` or `camp-cities`: the switches
apply them to the target's bytes.
`python SRC/camp.py roundtrip` re-encodes `CAMP_LIST` and checks it
rebuilds byte for byte.

## Still unknown

- Which city each sponsor frees (`0x16a940`), and what the camp screen
  shows for Santiago (message 0).
- The names of the 87 camp types (the themes at `SLES 0x552cd0` are
  numbers 1–6).

## Checking the claims

```bash
python SRC/camp.py info DAT/PARAM
python SRC/camp.py show DAT/PARAM 330 604
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 4bdd0 40 --sles ISO/SLES_541.51   # the type lookup
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL a54d8 46 --sles ISO/SLES_541.51   # the booking
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkSche_GetCampType pwkSche_CheckCampSucucess
python SRC/training.py show DAT/PARAM/TRAINING_LIST.TBB camp 83 84
python SRC/mbb.py dump DAT/MESSAGE/MES.PAC --cat 961 --lang 1     # city names
```
