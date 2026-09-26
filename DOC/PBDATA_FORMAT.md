# Player database (`PARAM/PBDATA_EU.PAC`, `PBDATA_JP.PAC`)

`PBDATA_EU.PAC` holds every real person the game knows: 27,950 players,
3,000 managers and coaches, and 1,000 scouts. That covers names,
nationality, age, height, weight, positions, preferred shirt number, a
money band, skills, and 64 ability ratings per player. The squads in
`OTEAMMEMBER.TBB` ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)) refer to
players by their index here.

`SRC/pbdata.py` reads it. `python SRC/initteam.py squads` uses it to put
names on the squads.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x110d50`, `0x11034c` | `PwkCallbackCommand_BpDataReadFile` and its caller | loads the pack and calls `plBp_Create(work, entry0, entry1, entry2, entry3)` with the four BINPAC entries in order |
| `0x20dd78`, `0x20c5d8` | `plBp_Create`, `PlBpinfoTask::init` | entry 0 is the header, entry 1 the records, entry 2 and entry 3 are kept at `0x390670` / `0x390674`. If the header's first byte is `'0'`, it isn't parsed |
| `0x20da58` | `PlBpinfoTask::initBpmaster` | the header layout below |
| `0x20c700` | `getPbase(id)` | player *id* (0 to count−1) is at `records + id × 98`. It is decoded by `plBits_DecPlPbaseEx`. Ids from `0x7cce` are edit-mode players, held elsewhere |
| `0x20c808` | `getMbase(id)` | ids from `0x6d2e`, at `records + players×98 + (id − 0x6d2e) × 81`, decoded by `plBits_DecPlMbaseEx` |
| `0x20c9b8` | `getSbase(id)` | ids from `0x78e6`, decoded by `plBits_DecPlSbaseEx` |
| `0x20bd28` | `PlBitsClass::readBits(n)` | reads *n* bits, most significant first. Bits are taken from each byte starting at `0x80`, and bytes in order |
| `0x20bdc8` | `PlBitsClass::readBitsStr(buf, n)` | *n* 8-bit characters: the name |
| `0x2e8568` | `plBits_DecPlPbaseEx` | the player fields below, in order. Afterwards it adds 16, 150 and 45 to `+0x28`, `+0x29` and `+0x2a`, replaces `+0x34` with `MONEY[v & 0xf]`, and maps each of the 64 abilities through `0x2e8540` |
| `0x2e8a70` | `plBits_DecPlMbaseEx` | the manager fields. The two groups of 9-bit values are sign-extended from bit 8 into s32 at `+0x4c` and `+0x54` (pointers set up at `0x2e8b64`) |
| `0x2e8ec8` | `plBits_DecPlSbaseEx` | the scout fields. The last 45 of its 49 seven-bit values go through `0x2e8540` |
| `0x2e8540`, `0x55b950` | ability mapping | `ABILITY[min(v, 31)]` with `ABILITY` = 38, 40, … 96, 98, 99 |
| `0x55b970` | money table | 0, 200, 1000, 3000, 5000, 7500, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000 |
| `0x2175e0`, `0x2176a8` | `plPinfo_IsForeigner`, `plPinfo_IsEU` | player `+0x14` is the nationality (`PlNati`). Bit 1 of `+0x63` is an EU passport on top of it |
| `0x218748` | `plPinfo_IsSkill` | `+0x64` is a bit mask, one bit per `PlPlayerSkill` |
| `0x20d908` | `getPinfoRank` | for ids ≥ `0x63f7` the rank is `+0x18`. Below that it is worked out from entry 3's value for the player (against thresholds at `0x5eac08`) |
| `0x20d9a0` | `getPinfoApos0` | the main position is `+0x1c` (for ids below `0x63f7`, it is derived from the rank again) |
| `0x2734c8` | `pwkTeam_SetUnumberOpinfo` | `+0x2b` is the player's preferred shirt number, 1–99 |
| `0x215a00` | `plMisc_Nati2NatiTeam` | nation → national team: `PLRESOURCECOMMON.PAC` entry 3, table 2, one u16 per nation. `pbdata.py` names nations through it, because the team names are known (message category 3) |

## Entry 0: header (46 bytes)

| Offset | Type | Value | Meaning |
|---|---|---|---|
| `0x00` | char[4] | `1000` | version text. Only checked for a leading `'0'` |
| `0x04` | u32 | 1 | not read |
| `0x08` | u32 × 3 | 27,950 / 3,000 / 1,000 | record counts: players, managers, scouts |
| `0x14` | u32 | 3,058 | stored at `+0x34` of the task. Use not traced |
| `0x18` | u16 (+2) × 3 | 98 / 81 / 71 | record sizes in bytes. Each is followed by `ff ff` |
| `0x24` | u16 | 64 | stored at `+0x50`. Use not traced |
| `0x26` | 8 bytes | `2e 02 26 a5 00 00 30 30` | not read by `initBpmaster` |

27,950 × 98 + 3,000 × 81 + 1,000 × 71 = 3,053,100 bytes, exactly the
size of entry 1 in `PBDATA_EU.PAC`.

## Entry 1: records

Each record starts with a `char[19]` name (cp850, zero-padded), followed
by bit fields read MSB first. The widths, order and destination offsets
are all **confirmed** from the decoders. The destination offset is where
the game keeps the value in memory, and it is also `pbdata.py`'s name for
a field whose meaning is unknown (`f_2c`, …). Meanings marked
*empirical* come from the data alone.

### Players (98 bytes, 779 bits used)

| Bits | × | Offset | Name | Meaning |
|---|---|---|---|---|
| 8 | 1 | `+0x14` | nation | nationality, 1–144. **confirmed** |
| 5 | 1 | `+0x18` | rank | 0–15. **confirmed** (read directly only for ids ≥ `0x63f7`) |
| 4 | 3 | `+0x1c` | position | main and up to two more positions, 0–12, with 13 meaning none. The first is **confirmed**. Which number is which position isn't known (goalkeepers are 0, *empirical*) |
| 7 | 1 | `+0x28` | age | stored − 16. *Empirical* meaning: 16–40, and it matches the real players in 2005 |
| 8 | 1 | `+0x29` | height | stored − 150, in cm (158–205). *Empirical* |
| 7 | 1 | `+0x2a` | weight | stored − 45, in kg (48–100). *Empirical* |
| 7 | 1 | `+0x2b` | shirt | preferred shirt number. **confirmed** |
| 3 | 1 | `+0x2c` | | 0–3 |
| 16 | 1 | `+0x30` | | always 0 |
| 16 | 1 | `+0x32` | | 0–17,172 |
| 16 | 1 | `+0x34` | money | band 0–15, looked up in the money table. What the money is (value or wages) isn't known |
| 3 | 1 | `+0x36` | | |
| 2 | 8 | `+0x37` | | |
| 4 | 8 | `+0x3f` | | the last 4 are usually 0 |
| 3, 5, 4, 3, 4, 5, 3, 4 | 2, 1, 3, 3, 2, 1, 1, 1 | `+0x47`…`+0x54` | | `+0x54` is always 0 |
| 2, 3, 2, 3, 1, 4 | 3, 2, 1, 1, 1, 1 | `+0x55`…`+0x5d` | | `+0x57` is always 0 |
| 5 | 5 | `+0x5e` | | 0–22, mostly 0 after the first |
| 3 | 1 | `+0x63` | flags | bit 1: EU passport. **confirmed**. Set in 19,333 players |
| 16 | 1 | `+0x64` | skills | bit mask. **confirmed**. All 16 bits are used |
| 3 | 11 | `+0x66` | | 0–4 |
| 5 | 64 | `+0x74` | ability | 64 ratings, each mapped to 38–99. **confirmed**. Which rating is which isn't known |

The 5 bits after the last field are zero in every record.

### Managers and coaches (81 bytes, 642 bits used)

`char[19]` name, then (bits × count at offset): 8 `+0x14` (nationality,
*empirical*: same range and position as the players'), 5 `+0x18`,
3 `+0x1c`, 16 `+0x20`, 6 `+0x22`, 16 `+0x24` (money band, **confirmed**
table lookup), 4 ×4 `+0x26`, 2 ×5 `+0x2a`, 3 ×4 `+0x2f`, 2 `+0x33`,
6 `+0x34`, 3 ×8 `+0x35`, 8 ×3 `+0x3d`, 3 ×7 `+0x40`, 5 ×5 `+0x47`,
signed 9 ×2 `+0x4c`, signed 9 ×4 `+0x54`, 1 ×2 `+0x64`, and 48 abilities
(5 bits, mapped to 38–99) at `+0x66`. The 6 bits left over are zero.

### Scouts (71 bytes, 565 bits used)

`char[19]` name, then 8 `+0x14` (nationality, *empirical*), 8 `+0x18`,
5 `+0x1c`, 16 `+0x20`, 16 `+0x22` (money band), 4 ×4 `+0x24`, 1 `+0x28`,
and 49 × 7 bits at `+0x29`. The last 45 of those are abilities, clamped
to 31 and mapped to 38–99. The 3 bits left over are zero.

## Entries 2 and 3

Each is 27,950 u16, one per player. Entry 3 is the value `getPinfoRank`
compares against its thresholds for players below `0x63f7`, so for most
players it decides the rank and main position that the game uses instead
of `+0x18`/`+0x1c`. Entry 2 is kept at `0x390670`, and what reads it
hasn't been traced. The two entries differ from each other.

## `PBDATA_JP.PAC`

The same header and identical entries 2 and 3, but entry 1 is empty (0
bytes). The European disc carries no Japanese player records. `pbdata.py
info` reports this as a note, not a problem.

## Still unknown

- The meaning of most fields, the position numbering, and which of the
  64 player abilities is which (the player screens in the overlays should
  name them).
- Entry 2, header `+0x14`, `+0x24` and the last 8 header bytes.
- How entry 3's value becomes a rank: the threshold table at `0x5eac08` is
  filled at run time.

## Checking the claims

```bash
python SRC/pbdata.py info DAT/PARAM/PBDATA_EU.PAC DAT/PARAM/PBDATA_JP.PAC
python SRC/pbdata.py list DAT/PARAM/PBDATA_EU.PAC --find terry
python SRC/pbdata.py show DAT/PARAM/PBDATA_EU.PAC 100 m:0 s:0     # every field
python SRC/pbdata.py csv DAT/PARAM/PBDATA_EU.PAC players players.csv
python SRC/initteam.py squads DAT/PARAM 7                          # Chelsea, with names
python SRC/sles_disasm.py ISO/SLES_541.51 dis initBpmaster getPbase readBits__Q25Param11PlBitsClassi
python SRC/sles_disasm.py ISO/SLES_541.51 dis plBits_DecPlPbaseEx plBits_DecPlMbaseEx plBits_DecPlSbaseEx
```
