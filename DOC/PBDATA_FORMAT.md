<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

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
| `0x218728` | `plPinfo_IsSkill` (PlPinfo overload) | reads the skills at `PlPinfo +0x1fc`, so the game's copy of the record starts at `PlPinfo +0x198` |
| `0x24d8a8` | `pwkPlayStyle_Init` | `PlPinfo +0x1f6` (record `+0x5e`) holds 5 play styles: it copies the non-zero ones into the style list at `+0x27c`, then adds random styles 1–22 (`slti 0x17`) for the player's position. The first stored style becomes the current one (`+0x278`) |
| `0x289e50`, `0x52f708` | `CDetailManager::AddPlate_PLAYSTYLE`, `Msg::GetString`'s base ids | the current style is drawn as `GetString(5, style)`. Type 5's base id is 150, and types below `0x29` use global slot 0, category 1. So style *n* is message 1:150 + *n* |
| `0x246884` | match growth (in the function before `pwkGUtl_AddExp`'s caller at `0x246930`) | abilities 45–52 (`0x2d` + *k*) gain experience only when *k* is the `system` of the club's current team style (my-team data `+0x4204`); abilities 33–41 only for the player's own position row |
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
| 4 | 3 | `+0x1c` | position | main and up to two more positions: a cell of the detail screen's pitch grid, 0–12, with 13 meaning none. See [Positions](#positions-and-aptitude). **confirmed** |
| 7 | 1 | `+0x28` | age | stored − 16. *Empirical* meaning: 16–40, and it matches the real players in 2005. Computer-team players don't show this age: their squad slot's age from `OTEAMMEMBER.TBB` is used instead ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)). Tested in game: a database age of 16 didn't change Terry's shown age |
| 8 | 1 | `+0x29` | height | stored − 150, in cm (158–205). *Empirical*. The decoder stores the sum in a byte (`sb` at `0x2e8a14`), so heights above 255 wrap. Tested in game: 313 cm shows as 57 cm |
| 7 | 1 | `+0x2a` | weight | stored − 45, in kg (48–100). *Empirical* |
| 7 | 1 | `+0x2b` | shirt | preferred shirt number. **confirmed** |
| 3 | 1 | `+0x2c` | leg | 0–3. Bit 0 set means right-footed, clear means left. *Empirical*: every well-known left-footer tested (Robben, Ashley Cole, Giggs, Messi, Roberto Carlos, Duff, Cech) has it clear. Bit 1 is set for famously two-footed players (Maldini, Henry, Rooney, Duff), and VPF's Player Edit screen shows Rooney (leg 3) as "Both(R)", so bit 1 is two-footed (*empirical*). The detail screen shows a message from 100–103 (LEFT, RIGHT, LEFT, RIGHT), which fits `100 + leg`, but the copy into `PlPinfo +0x1c4` hasn't been traced |
| 16 | 1 | `+0x30` | | always 0 |
| 16 | 1 | `+0x32` | | 0–17,172 |
| 16 | 1 | `+0x34` | money | band 0–15, looked up in the money table. What the money is (value or wages) isn't known. A lead: the developer BPINFO CHECK screen counts 8,063 players with money between 1 and 9,999 and labels the 10,000 cutoff "1mil" ([`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)), so one unit may be 100 of some currency |
| 3 | 1 | `+0x36` | | |
| 2 | 8 | `+0x37` | | |
| 4 | 8 | `+0x3f` | | the last 4 are usually 0 |
| 3, 5, 4, 3, 4, 5, 3, 4 | 2, 1, 3, 3, 2, 1, 1, 1 | `+0x47`…`+0x54` | | `+0x54` is always 0 |
| 2, 3, 2, 3, 1, 4 | 3, 2, 1, 1, 1, 1 | `+0x55`…`+0x5d` | | `+0x57` is always 0 |
| 5 | 5 | `+0x5e` | style | play styles, 1–22, 0 for none. **confirmed**. See [Play styles](#play-styles) |
| 3 | 1 | `+0x63` | flags | bit 1: EU passport. **confirmed**. Set in 19,333 players |
| 16 | 1 | `+0x64` | skills | bit mask. **confirmed**. All 16 bits are used; see [Skills](#skills) |
| 3 | 11 | `+0x66` | | 0–4 |
| 5 | 64 | `+0x74` | ability | 64 ratings (`PlAbilNo` 0–63), each mapped to 38–99. **confirmed**. See [Abilities](#abilities-and-the-detail-screen) |

The 5 bits after the last field are zero in every record.

### Player id blocks (empirical)

The last 2,359 player records (25,591–27,949) aren't in any club's
starting squad (`OTEAMMEMBER.TBB`):

| Ids | Blocks | What |
|---|---|---|
| 25,591–26,040 | 6 × 75, nations 1–6 (England, France, Germany, Italy, Spain, Netherlands) | made-up players. England's first 18 and 16 from 25,623 are the built-in default club ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#without-the-file)) |
| 26,041–27,949 | 83 × 23, one nation each | national-team squads: 83 blocks for the 83 national teams (`PlTeam` 460–542), and 26,041 + 83 × 23 = 27,950 |

A national-team record repeats a club player under the same name, as a
separate record: Gianluigi Buffon is 3,175 at Juventus and 26,110 (shirt
1) in Italy's block, John Terry 101 at Chelsea and 26,046 (shirt 6) in
England's. The two can differ (that Terry's height, abilities and age
aren't the club Terry's). Which code picks a nation's 23 hasn't been
traced. The user identified these as national-team players.

### Managers and coaches (81 bytes, 642 bits used)

`char[19]` name, then (bits × count at offset): 8 `+0x14` (nationality,
*empirical*: same range and position as the players'), 5 `+0x18`,
3 `+0x1c` (job, see below), 16 `+0x20`, 6 `+0x22` (age, see below), 16 `+0x24` (money band, **confirmed**
table lookup), 4 ×4 `+0x26`, 2 ×5 `+0x2a`, 3 ×4 `+0x2f`, 2 `+0x33`,
6 `+0x34`, 3 ×8 `+0x35`, 8 ×3 `+0x3d`, 3 ×7 `+0x40`, 5 ×5 `+0x47`,
signed 9 ×2 `+0x4c`, signed 9 ×4 `+0x54`, 1 ×2 `+0x64`, and 48 abilities
(5 bits, mapped to 38–99) at `+0x66`. The 6 bits left over are zero.

### Scouts (71 bytes, 565 bits used)

`char[19]` name, then 8 `+0x14` (nationality, *empirical*), 8 `+0x18`
(age, see below), 5 `+0x1c`, 16 `+0x20`, 16 `+0x22` (money band), 4 ×4 `+0x24`, 1 `+0x28`,
and 49 × 7 bits at `+0x29`. The last 45 of those are abilities, clamped
to 31 and mapped to 38–99. The 3 bits left over are zero.

### Staff age

Manager `+0x22` and scout `+0x18` are the age, stored as is (no offset,
unlike the players' `+0x28`). Without `TEAM_INIT_DATA.TBB`,
`pwkTeam_Init2` copies manager byte `0x22` (`0x25eff4`) and scout byte
`0x18` (`0x25f038`) into the slot where the table otherwise puts the
age. Where the table gives it, it equals these fields in all 180 manager
and 108 scout records. **Tested in PCSX2:** the game shows that value as
the staff member's age, in the Coach and Scout Candidate Lists and for
the club's own staff ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md)). Ages
run 35–55 for managers and 35–58 for scouts.

## Abilities and the detail screen

The 64 player abilities are finer-grained than anything the game shows.
The detail screen's 14 bars and the 6-axis "Evaluation" hexagon are
worked out from them.

**Groups (confirmed, `plPinfo_Abil2PSM` `0x216f10`).** Abilities 0–18
return 1, 19–25 return 0, and 26–63 return 2. `plPinfo_InitAbil`
(`0x21b470`) uses the group to pick which growth byte (`+0x4a`, `+0x4b`,
`+0x4c`) scales an ability's random start offset. From the bars below,
0–18 are skills, 19–25 physical and 26–63 mental, which fits the name
(P/S/M).

**Bars (confirmed, `WP::CDetailManager::ConvertPlayer_Bar` `0x285380`).**
Each bar is the integer average of the listed abilities' levels, and it
is drawn as `(value + 10) / 99` of full width. The labels are detail
messages `0x2774`+. The last 7 bars depend on whether the player's main
position (`PlPinfo +4`) is 0, the goalkeeper:

| Bar | Abilities | | Field bar | Abilities | | GK bar | Abilities |
|---|---|---|---|---|---|---|---|
| SPEED | 0, 20, 22 | | DRIBB | 0, 1 | | SAVIN | 15 |
| PHYSI | 24, 25 | | SHOT | 2, 3, 24 | | HANDL | 16 |
| STAMI | 23 | | PASS | 4, 5, 6 | | CROSS | 17 |
| MENTA | 26, 27 | | FK | 14 | | GO FW | 18 |
| SUPPO | 30, 31 | | HEAD | 7, 25, 21 | | DISTR | 4, 5, 24 |
| SYSTE | 0–7 | | INTER | 11 | | AGILI | 22 |
| TACTI | 0–10 | | MARK | 13 | | JUMP | 21 |

Only abilities 0–32 feed the bars. Where a bar has a single source, it
names that ability: 11 intercept, 13 marking, 14 free kick, 15 saving,
16 handling, 17 crosses, 18 going out, 21 jumping, 22 agility, 23
stamina. The labels SYSTE and TACTI (messages 200:10105/10106, "SYS" and
"TAC" in Japanese) suggest the systems and tactics (45–52 and 53–63, see
[Ability names](#ability-names)), but the code averages abilities 0–7 and
0–10. A check with
well-known players fits (database values, before the random start
offset): Terry has MARK 98, INTER 94 and HEAD 92, Pirlo has PASS 93 and
FK 94, Henry has SPEED 94 and DRIBB 95, and Cech and Buffon have SAVIN 98.

**Hexagon (confirmed computation, `plPinfo_CalcHexagon` `0x217ce0`,
`plPinfo_CalcHexAbil` `0x217850`).** `PLRESOURCECOMMON.PAC` entry 2,
table 0 has 8 bytes per ability. Each 4-byte half holds two
`{u8 hexagon, u8 weight}` pairs: `+4` is the field-player variant, and
`+0` is the goalkeeper variant. Hexagon *h* is the weighted average of
every ability with a pair naming *h*. `CalcHexagonNG` fills all six from
the field variant, then `CalcHexagon` recomputes 0 and 1 with the
goalkeeper variant for goalkeepers. The screen's labels are messages
670–675 of category 1 (Attacking, Physical, Teamwork, Defence, Attitude,
Skills, clockwise from the top). Which index goes to which label is
**empirical**. Hexagons 0 and 3 are told apart by Virtua Pro Football's
categories ([Ability names](#ability-names)): 0's main abilities are its
"Attack" page, and 3's are its "Skill" page.

| Hexagon | Main abilities (weight 80) | Label |
|---|---|---|
| 0 | 2, 4–7, 14 (shot skill, passes, cross, header, placekick) | Attacking |
| 1 | 10–13 (15–18 for goalkeepers) | Defence (defenders score ~90) |
| 2 | 33, 42–44 (60), 53–58 | Teamwork |
| 3 | 1, 3, 8, 9 (dribble skill, shot technique, trap, ball keeping) | Skills |
| 4 | 0, 19–25 | Physical |
| 5 | 26–32 | Attitude |

`python SRC/pbdata.py show` prints both the bars and the hexagon, and
`csv` adds the bars as columns.

### Ability names

Virtua Pro Football (VPF) runs on the same engine, and its Player Edit
screen names its parameters on 8 pages. The user supplied screenshots of
that screen for two players in this database: Maik Taylor (player 0, a
goalkeeper) and Wayne Rooney (player 258, a forward). VPF's pages follow
this game's ability order, and most values match within a point or two.
VPF has parameters this game lacks (cross technique, 1 on 1 response,
balance and some tactical ones), so the lists are aligned by value, not
by position.

The values column gives this game / VPF, for Taylor (T) and Rooney (R).
The evidence column says where each name comes from: **code** (the bars,
the position grid or match growth above), **VPF + data** (VPF's name, and
both players' values or a trend across the whole database fit), or
**VPF** (VPF's name, with the values as shown).

| Ability | Name | Values T, R | Evidence |
|---|---|---|---|
| 0 | dribble pace | 38/31, 88/92 | VPF + data (SPEED and DRIBB bars) |
| 1 | dribble skill | 38/38, 90/90 | VPF + data (DRIBB bar) |
| 2 | shot skill | 38/35, 86/91 | VPF + data (SHOT bar) |
| 3 | shot technique | 38/35, 88/87 | VPF + data (SHOT bar). VPF's "Skill" page |
| 4, 5 | short pass, long pass | 54/54, 84/83; 64/63, 82/81 | VPF + data (PASS bar) |
| 6 | cross | 40/39, 80/80 | VPF + data (PASS bar) |
| 7 | header | 38/35, 82/82 | VPF + data (HEAD bar) |
| 8, 9 | trap, ball keeping | 60/55, 88/88; 38/36, 82/82 | VPF + data. VPF's "Skill" page |
| 10 | tackle | 48/48, 66/65 | VPF + data |
| 11 | intercept | 38/38, 46/46 | code (INTER bar) |
| 12 | ball winning | 38/37, 48/48 | VPF + data |
| 13 | marking | 38/35, 50/49 | code (MARK bar) |
| 14 | placekick | 52/51, 80/80 | code (FK bar) |
| 15–18 | saving, catching, aerial ability, rushing out | 78/77, 78/77, 82/81, 78/78 for T | code (goalkeeper bars SAVIN, HANDL, CROSS, GO FW) |
| 19, 20 | pace, acceleration | 74/70, 74/69; 86/94, 92/94 | VPF. Both players have equal VPF values, so which is which isn't settled |
| 21–23 | jump, agility, stamina | 76/71, 88/83, 62/57; 76/80, 86/85, 86/85 | code (JUMP, AGILI, STAMI bars) |
| 24 | kick strength | 74/73, 88/88 | VPF + data (SHOT and DISTR bars) |
| 25 | contact strength | 80/80, 90/91 | VPF + data (PHYSI and HEAD bars) |
| 26 | leadership | 40/40, 70/70 | VPF + data (MENTA bar) |
| 27 | unknown, "consistency" by VPF's order | 40/51, 94/45 | the values don't fit (MENTA bar) |
| 28 | attack minded | 52/51, 96/96 | VPF + data: averages 45 for goalkeepers, 80 for forwards |
| 29 | defence minded | 84/84, 54/70 | VPF + data: averages 80 for goalkeepers, 45 for forwards |
| 30, 31 | supportiveness, vision | 40/40, 88/79; 60/59, 76/75 | VPF + data (SUPPO bar) |
| 32 | unknown (Attitude hexagon) | T 78, R 72 | no VPF counterpart |
| 33–44 | position aptitudes | see below | code ([Positions](#positions-and-aptitude)) |
| 45–52 | fit with systems 3-4-3, 3-5-2, 3-6-1, 4-3-3, 4-4-2, 4-5-1, 5-3-2, 5-4-1 | | code for "system *k*" (match growth); the order of the systems is empirical: the formation names (messages 801:0–7, 1:530–537) and their descriptions (700:270–293) are listed in this order |
| 53 | counterattack | 82/82, 88/87 | VPF + data |
| 54 | unknown (Teamwork hexagon) | T 42, R 88 | possibly one flank of VPF's "wings" (see below) |
| 55 | attacks down wings | 80/79, 62/78 | VPF; fits Taylor only |
| 56 | attacks through middle | 38/34, 86/86 | VPF + data |
| 57, 58 | line DF, pressing | 64/64, 68/68 for T; 58, 58 vs 57, 57 for R | VPF. VPF lists pressing first, so this pair rests on Taylor's values |
| 59–63 | unknown | | 60 is in the Teamwork hexagon |

VPF's aptitude page names the position cells. For Rooney: 34 = SB
(40/39), 35 = CB (44/44), 36 = WB (46/46), 39 = OM (86/85), 41 = FW
(96/95), 42 = centre (94/93), 43 = left (82/82), 44 = right (54/53). VPF's
DM (48) and SM (48) don't match 37 and 38 (66, 64). For Taylor, 33 = GK
(82/82), and VPF's FW is the centre cell. The left/right match backs up
43 = left. 40, the forward line's sides, has no VPF counterpart.

Rooney prefers the left (43 = 82, 44 = 54) and has 88 in 54 but 62 in
55, while VPF gives him 78 for "wings". So 54 and 55 may be the left and
right flank attacks that VPF merges into one value. The game's own attack
names (messages 1:620–649) do list Left Flank and Right Flank
separately. This isn't settled.

Across the database, abilities 26, 27, 32 and 45–63 average 51 for every
position and play style. They are only higher across the board for
stronger players (about 62 for the holders of any skill), which suggests
filler values. That is why those names rest on the two VPF players, and
why 19/20 and 57/58 stay open: both players have equal VPF values there.

## Skills

`+0x64` holds one bit per `PlPlayerSkill` (`plPinfo_IsSkill`, `0x218748`).
Bit *n* is described by message 6000 + *n* of category 2000. The short
labels are summaries of those texts, as `pbdata.py` prints them:

| Bit | Label | Description (message 2000:6000 + bit) | VPF name |
|---|---|---|---|
| 0 | covering | superb covering, bails the team out | Covering |
| 1 | offside line | holds the defensive line, works the offside trap | Line Control |
| 2 | penalty taker | superb penalty taker | PK Taker |
| 3 | penalty stopper | puts pressure on the penalty taker (a keeper) | PK Goal Keeper |
| 4 | one-on-one finisher | cool in one-on-ones with the keeper | Shot on 1 on 1 |
| 5 | one-on-one keeper | saves one-on-ones | GK on 1 on 1 |
| 6 | long throw | very long throw-ins | Long Throw |
| 7 | super sub | swings a match when brought on | Super Sub |
| 8 | through balls | vision for through balls | Ball Feeding |
| 9 | positioning | exquisite positioning | Positioning |
| 10 | reflex saves | miraculous reactions | Fine Saving |
| 11 | acrobatic shot | shoots even off balance | Acrobatic Play |
| 12 | one-touch shot | one-touch finishing | Volleys |
| 13 | goal machine | pin-point shooting | Controlled Shot |
| 14 | poacher | pounces on loose balls in the box | Good Positioning |
| 15 | playmaker | leads the team with killer passes | Through Ball |

VPF's Special Skill page lists its 16 skills in this order, and each
name fits the description of the same bit, which backs up the bit order.
VPF marks Rooney with Shot on 1 on 1, Acrobatic Play and Controlled
Shot, and his `+0x64` has exactly bits 4, 11 and 13.

That bit *n* goes with message 6000 + *n* is **empirical**, from who holds
which bit. Of 2,465 goalkeepers, 90, 91 and 86 hold bits 3, 5 and 10, and
of 14,395 defenders and forwards only 1 holds any of the three. Bits 0 and
1 go mostly to defenders (237 of 238), and bits 2, 4 and 11–14 mostly to
forwards. The code confirms one: the substitutions screen tests bit 7, the
super sub (`CTacticsMenuSubstitutionsImplement::Update_MessDisplay`,
`0x2f6558`). What the skills do in a match isn't traced.

## Play styles

**Confirmed (`pwkPlayStyle_Init` `0x24d8a8`, `AddPlate_PLAYSTYLE`
`0x289e50`).** `+0x5e` holds up to 5 play styles, 1–22, with 0 for an
empty slot. When a player is set up, the game lists the stored styles,
then adds random ones that suit the player's position until the
position's count (table at `0x398e98`) is reached. The first stored
style is the one the detail screen shows. Style *n* is named by message
1:150 + *n*:

| Style | Name (message 1:150 + n) | VPF name | Players |
|---|---|---|---|
| 1 | Centre Forward | Centre Forward | forwards |
| 2 | Moving | Moving | forwards |
| 3 | Postplayer | Target man | forwards (Crouch) |
| 4 | Dash out | Darting run | forwards (Inzaghi, Shevchenko) |
| 5 | Second Striker | Second Attacker | forwards (Totti, Del Piero) |
| 6 | Wing | Wings | forwards and attacking midfielders |
| 7 | Play maker | Playmaker | midfielders (Pirlo, Zidane) |
| 8 | Shadow striker | Shadow Striker | midfielders (Lampard) |
| 9 | Attacker | Attacker | attacking midfielders (Robben, Ronaldinho) |
| 10 | Dynamo | Dynamo | midfielders (Gattuso, Vieira) |
| 11 | Man marker | Hard Marker | defensive midfielders (Makelele, Gattuso) |
| 12 | Covering | Anchor | defensive midfielders (Makelele) |
| 13 | Centre MF | Central Midfielder | midfielders (Lampard, Beckham) |
| 14 | Winger | Side Attacker | wide players (Beckham, Roberto Carlos) |
| 15 | Threaten to cut in | Wing Forward | wide players (Henry, Cafu) |
| 16 | Full back | Wing half | full-backs (Cafu) |
| 17 | Sweeper | Sweeper | defenders |
| 18 | Defensive Sweeper | Libero | defenders |
| 19 | Stopper | Stopper | defenders (Puyol, Nesta) |
| 20 | CB | Centre Back | defenders (Puyol, Nesta) |
| 21 | GK | Orthodox | goalkeepers only (Cech, Lehmann) |
| 22 | Attacking GK | Libero GK | goalkeepers only (Buffon, Barthez) |

Across the database (**empirical**), 19,403 players have at least one
style. Styles 21 and 22 are held only by goalkeepers (841 and 220), and
1–5 almost only by forwards. VPF shows its 22 styles in the same order,
each with a rating. This game stores only which styles a player has. The
style names were already checked in game through a save
([`SAVE_FORMAT.md`](SAVE_FORMAT.md)).

## Positions and aptitude

**Confirmed, `plPinfo_CalcAptPos` (`0x217f70`),
`plPinfo_GetPositionFitValue` (`0x217e48`), and the table at `0x532610`.**
The detail screen's pitch grid has 13 cells, and they are the 13
position numbers. For each cell, the game computes a fit value, a
weighted sum of up to four abilities:

| Cell | Name | Fit |
|---|---|---|
| 0 | GK | 33 |
| 1, 2, 3 | DF left, right, centre | 0.7 × 34 + 0.3 × 43 (left) or 44 (right); centre 0.7 × 35 + 0.2 × 42 + 0.05 × (43 + 44) |
| 4, 5, 6 | DM left, right, centre | the same with 36 (sides) and 37 (centre) |
| 7, 8, 9 | AM left, right, centre | 38 and 39 |
| 10, 11, 12 | FW left, right, centre | 40 and 41 |

So abilities 33–44 are position aptitudes: 33 goalkeeper, 34–41 each
row's sides and centre, and 42/43/44 a leaning to the centre, the left
and the right. The rows go from the goal upwards. The names DF/DM/AM/FW
are descriptive, not the game's. Which of 43 and 44 is the left is
**empirical**: players who play on the left (Robben, Edu) are higher in
43, and Tevez's top-right cell lights up with 44 = 88.

Each cell's fit is converted to a level from 0 to 4 against the
player's best cell, using the table at `0x5327b0`. A cell gets level
4, 3, 2 or 1 for the first row where fit ≥ 70/60/50/40 **and** either
fit ≥ 1.0/0.95/0.9/0.8 × best, or fit ≥ 80/70/60/50. Then each listed
position (`+0x1c`, up to three) gets +1, up to 4.

**Tested in the game:** Terry with abilities alternating 38 and 99 has
99 in 33, 35, 37, 39 and 41. His grid lit the goalkeeper box and the
whole centre column, as the formula predicts. The vanilla Terry's grid
(his centre-back cell, the centre cell in front of it and one side cell)
also matches the computed levels. His two side cells score 66 and 68,
just under the level-3 threshold, and the game's random start offset
(`plPinfo_InitAbil`) can push one of them over. Which levels the screen
draws, and in which colour, hasn't been traced.

`python SRC/pbdata.py show` prints the grid (forwards at the top), and
`list` names the positions.

### Manager, coach and scout bars

**Confirmed, `WP::CDetailManager::CalcManagerAbil` (`0x286cd0`).**
`PlMinfo` is 4 bytes followed by the `PlMbase` (`plMinfo_InitDb`
`0x2e9720` copies it to `+4`), so `PlMinfo +0x6a` is ability 0 and
`+0xa0` is the job at `PlMbase +0x1c`. Every manager and coach screen has
12 shared bars, then a set picked by the job through the jump table at
`0x557630`. All are single abilities except FLANK:

| Bar | Ability | Bar | Ability | Job | Extra bars (abilities) |
|---|---|---|---|---|---|
| ATTST | 45 | FLANK | avg 29, 30 | 0, 1, 2 | DRIBB 10, SHOT 11, PASS 12, HEAD 13, INTER 14, MARK 15 |
| TEAMW | 46 | MOTIV | 0 | 3 | SPEED 18, PHYSI 20, STAMI 19, MENTA 21 |
| FK | 47 | PHYSC | 1 | 4 | SAVIN 16, HND 17 |
| TRAIN | 5 | COMMU | 3 | 5+ | FASTB 39, SLOWB 40, WINGP 41, DIREC 42, OFFSI 43, CLOSD 44 |
| ATKDF | 22 | POPUL | 2 | | |
| CENTA | 28 | ASSES | 4 | | |

The labels match the in-game help pages: 0–2 are assistant coaches, 3
physical coaches, 4 goalkeeper coaches. The database holds jobs 0 (439),
1 (786), 2 (714), 3 (678) and 4 (383), and no 5. A staff member hired as
manager gets the job-5 bars. In a save, C. Collin (job 0 in the
database) shows the manager bars, and they match abilities 39–44. So the
job is changed at run time. The shared bars for Collin and M. Boismortier
match their detail screens exactly.

**What the jobs are.** Averaging the coaching bars over each job in the
database (**empirical**) separates 0–2:

| Job | Count | Coaching bars (DRIBB SHOT PASS HEAD INTER MARK) | Is |
|---|---|---|---|
| 0 | 439 | 68 68 68 60 68 68 | the database's managers: all even. Hired as manager it becomes 5, as youth manager 6 |
| 1 | 786 | 80 80 80 68 55 55 | an attacking coach |
| 2 | 714 | 68 55 61 76 80 80 | a defensive coach |
| 3 | 678 | physical bars | physical coach |
| 4 | 383 | saving bars | goalkeeper coach |

In a save, M. Eulenburg and S. Saioni (job 0 in the database) are the
manager (5) and youth manager (6), and the coaches keep jobs 1–4. Job 0
is where managers start, not the only way to become one: in the game,
coaches and former players can become managers too. The code has a coach
job-change work area (`pwkTeam_SetCoachJobChangeWork`,
`pwkTeam_PutCoachJobChangeWork` and neighbours, `0x26b998`–`0x26bc88`),
and a player's `PlPinfo +0x210` holds a job change
(`plPinfo_GetChangeJob` / `SetChangeJob`); neither is traced yet.
`pwkTeam_SetYManager` (`0x26bd28`) writes 6 into the youth manager's
`+0xa0` after copying him in (**confirmed**); where 5 is set for a manager
isn't traced (`pwkTeam_SignManager`, `0x269e20`, copies the record as it
is and sets only the contract years at `+0x9e`).

The coach page's title (`SetupDetailCoachPageCommon`, jump table
`0x5577d0`) is the same string for jobs 0, 1 and 2 (`Msg::GetString(0x18,
3)`), with 4 for goalkeeper coaches and 5 for physical coaches. Those
match messages 553 "Assistant Coach", 554 "GK Coach" and 555 "Physical
Coach" of category 100001. Checked in game: S. Daerden (job 1) and
L. Lynch (job 2) are both titled "Assistant Coach", and their comment
lines call them an "outstanding forwards coach" and a "very good defence
coach", which fits the averages above. So the game gives jobs 0–2 one
title; what tells them apart is which abilities they are good at, which
the comment line puts into words.
`GP::ConvertStaff` (`0x27ee68`) likewise gives 0–2 one icon.

**Confirmed, `WP::CDetailManager::ConvertScout` (`0x287c60`).**
`PlSinfo` is 4 bytes followed by the `PlSbase` (`plSinfo_InitDb`
`0x21eb80`). The 11 scout bars are single abilities (the 45 mapped
scout abilities, starting at `PlSbase +0x2d`): CLB 0, PLAYE 1, FINDP 3,
YOUTH 4, YOUNG 5, OLDER 6, VETER 7, MANAG 21, ACOAC 22, PCOAC 23,
GCOAC 24. A 12th value, ability 25, is computed too but not labelled.
Staff and scout bars are drawn as `value / 99`. Player bars add 10
first.

`python SRC/pbdata.py show` prints these bars for managers and scouts
(the job's own set, plus the manager set for coaches), and `csv` adds
them as columns.

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

## Writing

`pbdata.py` can write the database back out. Each record is re-encoded
from its stored field values in `readBits` order: the 19 name bytes as
they were, every field at its width, then the padding bits as they were.
Entry 1 is then replaced in a copy of the pack. Records are fixed-size,
so the entry keeps its offset and size and nothing else in the file
moves. `pbdata.py roundtrip` does this for all 31,950 records without
changes, and the result is byte-identical to the disc's file (a
`regress.py` check).

Edits are given as the values `show` prints, and are converted back:

- `add` fields subtract their offset (age 30 is stored as 14).
- Abilities must be one of the 32 table values, 38–99.
- `money` must be one of the 16 table values, stored as its index. The
  game reads only the low 4 bits of the 16-bit field, so an unchanged
  value keeps its stored bits.
- Signed manager fields must fit 9 bits.
- Names are cp850, at most 18 bytes, zero-padded to 19 (every name on the
  disc has a terminator).

The limits are mostly the field widths, not what the game considers
sensible. The exception is `age`, `height` and `weight`: the decoder adds
their offset and stores the sum in a byte, so `pbdata.py` refuses values
above 255. Height is the only one where that matters (the field alone
would allow up to 405 cm). Otherwise the game takes whatever fits.

**Tested in the game** (PCSX2, new game, patched with `patch_disc.py`):
Terry renamed `J.Terry.MOD`, 96 kg, left-footed, with abilities
alternating 38 and 99. The name, weight, leg and the bar pattern all
showed as predicted by `pbdata.py show` (low SPEED and FK, high STAMI,
HEAD, INTER and MARK). A height of 313 cm showed as 57 cm, which is what
led to the byte limit above. A second test with 255 cm showed 255 cm.

```bash
python SRC/pbdata.py set DAT/PARAM/PBDATA_EU.PAC out.PAC 101 age=30 ability.13=99 name=J.Terry
python SRC/pbdata.py csv DAT/PARAM/PBDATA_EU.PAC players players.csv   # edit in a spreadsheet
python SRC/pbdata.py import DAT/PARAM/PBDATA_EU.PAC out.PAC players players.csv
```

`import` writes only the values that differ from the pack, so an unedited
CSV gives an identical file. The bar and `entry2`/`entry3` columns are
derived and ignored. Putting the edited pack back on a disc is the
Rebuild stage in [`GOALS.md`](../GOALS.md), which isn't done yet.

## Still unknown

- The meaning of most fields between `+0x30` and `+0x5d`, and `+0x66`.
- Abilities 27, 32, 54 and 59–63. Which of 19/20 is pace and which of
  57/58 is pressing (both VPF players have equal values there), and
  whether 54/55 are the left and right flanks. The
  game code that reads 53–63 hasn't been found (the match engine,
  `GAMEPRG.REL`, is the likely reader).
- The hexagon labels are matched to indices from the data and VPF's
  pages. The label order in `GP::CHexWindowBase::DrawString` (`0x27c700`)
  comes from a screen layout and hasn't been traced.
- What the play styles do in a match, beyond which abilities grow.
- The code that turns the leg field into `PlPinfo +0x1c4`.
- What sets job 5 when a manager is hired.
- Staff abilities other than the ones the bars name (6–9, 23–27, 31–38),
  and scout abilities 2, 8–20 and 26–44 (the preferred areas and search
  types on the scout screen probably come from some of them).
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
