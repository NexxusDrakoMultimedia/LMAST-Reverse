<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Save data (memory card)

A saved game is a memory-card folder `BESLES-54151-Gnnn` (`nnn` = slot,
`%03d`). It holds:

| File | Size | What |
|---|---|---|
| `BESLES-54151-Gnnn` | 646,184 | the game: all of `Param::PlPworkTask`, bit-packed and Blowfish encrypted (below) |
| `info.bin` | 2,048 | the summary for the load screen. The first 0x400 bytes are Blowfish encrypted with the key `FC_EURO_2005` and start with the save date as text (`26/09/21 09:39:47`). Not decoded further |
| `dm.bin` | 93,184 | plain. Not decoded |
| `icon.sys`, `static.ico` | 964, 70,264 | the standard PS2 browser icon |

`python SRC/save.py` reads and writes the main file. It doesn't copy the
field layout out of the game: it runs the game's own read and write
functions from `SAVEPRG.REL` in a small interpreter (see
[Decoding](#decoding)).

## Main file

**Confirmed from the game code (`SAVEPRG.REL` unless noted):**

| Address | Symbol / role | What it shows |
|---|---|---|
| `0x320c0`, `0x32158` | Blowfish init, key schedule | standard Blowfish: P-array at `0x4bd78`, S-boxes at `0x4bdc0`. Key bytes go into P big-endian, cycling over the key |
| `0x32358`, `0x32478` | decrypt, encrypt `(buf, size, key, keylen)` | ECB over 8-byte blocks. Each block is loaded as two native (little-endian) words, left then right. `size` must be a multiple of 8 |
| `0x331f8`, `0x336f4` | load, save | key: the 10 bytes at `0x536a8`, `sakatsukue` |
| `0x33200`–`0x3322c` | load | copies the 16-byte header; version `+0xc` must be `0x69` (`0x68` goes to an older reader at `0xe618`) |
| `0x3328c`–`0x3329c` | load | header `+8` must equal the layout CRC from `0x32ce0` |
| `0x32ce0` | layout CRC | CRC-16 (`0x31470`, table `0x53408`: reflected poly `0x8408`, init and xorout `0xFFFF`) over `getSize(0..9)` as ten u32 |
| `0x21d908` (SLES) | `PlPworkTask::getSize` | block `i` is `0x533ac8[i] − 8` bytes |
| `0x33338`–`0x33360` | load | memory-card saves take the bit-packed path: `plBits_Create` over the data at `+0x10 + header[0]`, then `0x32d50` |
| `0x32d50` | per-block loop | for `i` in 0–9: `get(i)`, then read `0x2b9b0` / write `0x2ba08`, which jump through tables at `0x4bd28` / `0x4bd50` |

Plaintext layout:

| Offset | Size | What |
|---|---|---|
| `0x0` | u32 | data offset (0 in every save) |
| `0x4` | u32 | 0 |
| `0x8` | u32 | layout CRC, `0xa225` for this build |
| `0xc` | u32 | version, `0x69` |
| `0x10` | | the bit stream: blocks 0–9 in order, MSB first (`PlBitsClass`, as in [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)) |

The layout CRC checks that a save matches the build's block sizes. **Nothing
checks the contents**, so an edited save only has to be re-encoded and
re-encrypted.

The stream is 5,169,290 bits (646,162 bytes) in all 5 saves checked. The
file is the header plus the stream rounded up to 8 bytes. The game doesn't
clear its buffer, so the 6 bytes after the stream (and the unused low bits
of the last byte) are leftover memory: zero in 2 of the 5 saves, random in
the other 3. `save.py` keeps whatever the original file had there.

### The blocks

`python SRC/save.py blocks` prints the sizes. Decoded, the ten blocks are
1,035,469 bytes, which is 1.6 times the stream: the serializers write each
field with only as many bits as it needs.

| Block | Size | Holds (from the functions that call `get(i)`) |
|---|---|---|
| 0 | 134,728 | general state: money, date, difficulty, events, mail, random seed (`pwkGen_*`) |
| 1 | 76,264 | your club: squad, staff, scouts, negotiations, sponsors, youth (`pwkTeam_*`, `pwkDis_*`) |
| 2 | 73,920 | the other clubs (`pwkOteam_*`) |
| 3 | 1,328 | leagues (`pwkLg_*`) |
| 4 | 168 | town and overseas branches (`pwkTown_*`) |
| 5 | 741,584 | records: results, finances, reports, honours (`pwkRec_*`) |
| 6 | 7,400 | schedule and camps (`pwkSche_*`) |
| 7 | 68 | options (`pwkOpt_*`) |
| 8 | 1 | (`get(8)` returns 0 when PlPwork `+0x19` is set; `0x2b990` then skips it) |
| 9 | 8 | not traced |

### Fields found so far

All **confirmed** by the accessor named. Offsets are within the block.

| Block | Offset | Type | Accessor | What |
|---|---|---|---|---|
| 0 | `0x0` | s64 | `pwkGen_GetSikin` (`0x2444e0`) | club money, in the game's own unit (below) |
| 0 | `0x88` | PlDate | `pwkGen_GetDate` (`0x244368`) | the current date |
| 0 | `0x1344` | | `pwkGen_GetDifficultyPointer` (`0x244c78`) | difficulty settings (not decoded) |
| 1 | `0x4b4` | PlTeamData | `pwkTeam_GetMyTeamData` (`0x259898`) | your club |
| 1 | `0x4b4 + 0x20` | 25 × PlPinfo | `pwkTeam_GetForeignCitizenNumber` (`0x266450`) | the squad, 0x2a0 bytes per player |
| 1 | `0x4808` | 25 × 25 u16 | `plCombi_Get` (`0x20f638`): PlTeamData `+0x4354` | pair combinations: value above the diagonal, cap below (below) |
| 1 | `0xec8e` | 25 × 0x11e | `pwkTeam_GetPlayerStats` (`0x265810`, indexes `0xec90 + slot × 0x11e`) | each squad slot's match statistics (below) |
| 1 | `0x4f00` | 24 × PlPinfo | `pwkTeam_GetYteamData` (`0x270c18`); `pwkTeamType_FitCalc` (`0x270b58`) walks them up to `+0x3f00` | the youth team (21 players in the save checked, 3-year contracts, no salary) |
| 1 | `0xe290` | 3 × 0x2a0 | `0x266600` | read like PlPinfo by one foreign-player count, but the save holds ids of 0 and no players there; not identified |
| 2 | `0x0` | 440 × 0xa8 | `pwkOteam_GetPointer` (`0x24b788`) | the other clubs: squads, friendship, ranks (below) |
| 1 | `0x4d08` | PlMinfo | `pwkTeam_GetCoachManager` (`0x26cdc8`): PlTeamData `+0x4854` | the manager |
| 1 | `0x8e00` | PlMinfo | `pwkTeam_GetYManager` (`0x26bdd8`): `pwkTeam_GetYteamData` (`+0x4f00`) `+0x3f00` | the youth manager |
| 1 | `0x9148` | 4 × PlMinfo | `pwkTeam_GetCoaches` (`0x26a7b8`) | the coaches, 0xbc bytes each |
| 1 | `0x8f8c` | 3 × PlSinfo | `pwkTeam_GetScouts` (`0x26d098`) | the scouts, 0x94 bytes each |
| 1 | `0x12470` | | `pwkUnkei_GetWork` (`0x271cf8`) | the season plan: ad budget, ticket prices, season tickets (below) |
| 5 | `0x0` | 2 × (12 + 23) s64 | `pwkRec_AddMonthlyIncome` (`0x252d88`), `AddMonthlyPayment` (`0x252de0`), `GetMonthlyReport` (`0x252e38`), `GetAnnualReport` (`0x253090`) | the accounts for this month (`+0x0`) and this season (`+0x130`) (below) |

**Money** is stored in the game's own unit. `plMisc_MoneyRate`
(`0x215660`) converts between currencies as `value × rate[to] ÷
rate[from]`, with s16 rates at SLES `0x5314e8`: 12, 3, 2, 400. The stored
unit is rate 12 and the pound is rate 2 (**empirical**: a save edited to
2,000,000,000 shows £333,333,333, exactly ÷ 6). The euro is rate 3
(**empirical**: in game, euro amounts are 1.5 times the pound amounts), so
euros are the stored value ÷ 4 and the stored unit is worth €0.25. That
400 is the yen is still a guess from 2005 exchange rates (€1 ≈ ¥133,
£1 ≈ ¥200). The stored unit isn't the yen.

**Finances.** Money moves through `pwkGen_Income` (`0x244570`) and
`pwkGen_Pay` (`0x2445f8`). Both change the s64 at block 0 `+0x0` and
book the amount under a type in the month's accounts. On overflow,
`pwkGen_Income` sets the money to 0x7fffffff. **Confirmed from the game
code:**

| Address | Symbol | What it shows |
|---|---|---|
| `0x252d88`, `0x252de0` | `pwkRec_AddMonthlyIncome`, `AddMonthlyPayment` | block 5 `+0x0` + 8 × type is this month's s64 for income type 0–11, `+0x60` + 8 × type for payment type 0–22 |
| `0x252c98` | `pwkRec_AfterMonthlyReport` | adds the month into the season's copy at `+0x130`/`+0x190`, then clears the month |
| `0x253020` | `pwkRec_AfterAnnualReport` | clears the season's incomes and payments |
| `0x252e38`, `0x253090` | `GetMonthlyReport`, `GetAnnualReport` | a report is the 0x130 bytes at `+0x0` or `+0x130`: the 12 incomes, the 23 payments and 3 s64. `pwkRec_GetSikinChange` (`0x252fc0`) treats the first of those (`+0x118`) as the money at the start of the month |
| `0x253118` | `pwkRec_GetBalanceFromReport` | the balance is the sum of the incomes minus the sum of the payments |
| `0x252be0` | `pwkRec_InMonthlyReport` | at the report, applies income 7 and payments 7–13, 17 and 19 to the money (flags at `0x3991e8`/`0x3991f8`); the other types were applied when they happened |
| `0x21e390`, `0x21e3c0` | `plRec_GetIncomer`, `GetPaymentr` | the report screen (`SIMPRG.REL 0x997c8`) shows 7 income groups: types 0, 1–2, 3–4, 5–6, 7–8, 9–10 and 11; and 5 payment groups: 0–7, 8–16, 17, 18–19 and 20–22 (lists at `0x3909b0`, `0x3909d0`) |

**The names.** The report screen's text is message category 550. Its
loop at `SIMPRG.REL 0x98818` labels the 12 lines with messages 204 +
*line* (**confirmed**): Sponsor fee, Media licensing fee, Admission fee,
Winnings, Facilities, Transfer fees and Other for the 7 income lines;
Facilities, Staff costs, Advertising costs, Overseas investment and Other
expenditure for the 5 payment lines. Messages 217 + *type* name the 12
income types and 229 + *type* the 23 payment types. The code that reads
those isn't found, so the type names are **empirical**: the counts are
exactly 12 and 23, and every type traced from the code below matches its
name.

| Income | Name (550:217 + type) | Payment | Name (550:229 + type) |
|---|---|---|---|
| 0 | Sponsor fee | 0 | Stadium purchase & rebuild |
| 1 | League contract | 1 | Stadium facilities |
| 2 | Individual contract | 2 | Club house extension |
| 3 | Season ticket sales | 3 | Club house facilities |
| 4 | Ticket price | 4 | Practice ground expansion |
| 5 | Win bonus | 5 | Practice ground facilities |
| 6 | Position prize money | 6 | Practice ground maintenance |
| 7 | Merchandise | 7 | Facilities maintenance |
| 8 | Stadium facilities | 8 | Youth Management costs |
| 9 | Player Transfer Fee | 9 | Player Annual Salary |
| 10 | Rental Fee | 10 | Supervisor Annual Salary |
| 11 | Other income | 11 | Coach Annual Salary |
| | | 12 | Youth Supervisor Salary |
| | | 13 | Scout Salary |
| | | 14 | Player Transfer Fee |
| | | 15 | Loan fees |
| | | 16 | Pay for the Job |
| | | 17 | Advertising Costs |
| | | 18 | Overseas Investment |
| | | 19 | Overseas club bases |
| | | 20 | Match management |
| | | 21 | Camp Tour |
| | | 22 | Casual income (an expense: a translation slip) |

Media licensing fee is income 1–2 (league and individual TV contracts),
Admission fee 3–4 (season tickets and tickets) and Winnings 5–6.
Supervisor is the manager. The types traced from the code that books
them:

| Type | Source |
|---|---|
| income 4 | `pwkUnkei_BeforeReport` (`0x272ef8`) after a home match: the match's ticket money (`pwkUnkei_GetMatchIncome` `0x273008`, `+0x8`) |
| income 5 | `pwkUnkei_BeforeReport`: the match record's `+0xc`. The manual's post-match Earnings Report shows "a winning bonus for a win" |
| income 7 | `pwkRec_BeforeAcount` (`0x252b20`): `pwkGd_GoodsMonthlySales` |
| income 8 | `pwkUnkei_BeforeReport`: `pwkUnkei_GetShopIncome` |
| income 11 | `pwkUnkei_BeforeReport`: the match record's `+0x14` × 2 plus `+0x1c` |
| payment 7 | `0x2528c0` (the monthly fixed costs): `payment_Equip` (`0x251fb8`) |
| payment 8 | `0x2528c0`: `0x2523c8` walks `pwkTeam_GetYpinfo` |
| payment 9 | `0x2528c0`: `0x252548` walks the squad (`plPinfo_IsHired`) |
| payment 10 | `0x2528c0`: `0x252610` reads your team data (the manager's PlMinfo is in it) |
| payment 11 | `0x2528c0`: `0x252680` walks `pwkTeam_GetCoaches`. `pwkTeam_SignCoach` also pays type 11 |
| payment 12 | `0x2528c0`: `0x252710` reads `pwkTeam_GetYManager` |
| payment 13 | `0x2528c0`: `0x252780` walks `pwkTeam_GetScouts` |
| payment 16 | `pwkUnkei_BeforeReport`: `pwkPromise_MatchBounus` |
| payment 17 | `0x2528c0`: `0x251f38` reads `pwkUnkei_GetPR`, the season's ad budget. **Empirical:** 7,500,000 after three months of a 30,000,000 budget (save G000) |
| payment 19 | `0x2528c0`: `pwkRec_GetPayOverSea` summed over 13 regions |
| payment 20 | `pwkUnkei_BeforeReport`: the match record's `+0x18`, partly random |

**Empirical:** in all five saves the three s64 after each report's
payments, and the two records `pwkGen_GetPastYearBalance` and
`GetPastMonthBalance` point to (block 0 `+0x8` and `+0x28`), are zero.

**The season plan** (block 1 `+0x12470`, `pwkUnkei_GetWork`). The
accessors are `pwkUnkei_Get`/`Set` `PR`, `Ticket`, `SeatRate`,
`SeatPrice`, `SeatNum` and `OtherTicket`. `pwkUnkei_Init` (`0x271be0`)
gives a new career's values. **Confirmed:**

| Offset | Type | What | New career |
|---|---|---|---|
| `0x0` | u32 | ad budget per season (`GetPR`) | 3,000,000 |
| `0x4` | u32 | league ticket price (`GetTicket`) | 60 |
| `0x8` | u32 | season-ticket rate (`GetSeatRate`) | 100 |
| `0xc` | u32 | season-ticket price (`GetSeatPrice`) | 0 |
| `0x10` | u32 | season tickets on sale (`GetSeatNum`) | 0 |
| `0x14` | u8 | not traced | 0 |
| `0x16` | u16 | not traced | 7,000 |
| `0x18` | 8 × u32 | ticket prices for other competitions (`GetOtherTicket`) | 0 |
| `0x38` | 8 × u16 | their competition ids, `0xffff` for none | `0xffff` |

**Empirical**, all five saves: the rate is always 100 and the
season-ticket price equals the ticket price, so the rate looks like the
price as a percentage. `+0x14` holds 83–100 and `+0x16` 7,000. One
competition has its own ticket price in each later save (`0x2b`, `0x3d`
or `0x3f`), at the league price. The limits the plan screen puts on
these values aren't traced, so `save.py` doesn't edit them yet.
`save.py finances` prints the plan and both sets of accounts.

**PlDate** (`plMisc_SetTurn2Date` `0x214698`, `plMisc_PlDate2TotalTurn`
`0x214d08`):

| Offset | Type | What |
|---|---|---|
| `0x0` | u16 | the season's first year: 2019 for 2019–20, from January to June as well (confirmed: `plMisc_PlDate2TotalTurn` only counts upwards that way; `plMisc_SetTurn2Date` stores the year it is given with a turn of the season) |
| `0x2` | u8 | turn of the season, 0–95 (8 per month, from July) |
| `0x3` | u8 | month, 1–12 |
| `0x4` | u32 | turn within the month, 0–7 |
| `0x8`, `0xc` | u32 | that turn ÷ 2 and its remainder: the week (from 0) and midweek (0) or weekend (1). Turn 3 of November is the top bar's "Week 2 Weekend Nov." (**empirical**, one save) |

**PlPinfo** (a player in your squad):

| Offset | Type | What | Source |
|---|---|---|---|
| `0x0` | s16 | database id; negative = empty slot | confirmed, `0x2664d0` |
| `0x4` | u32 | position (grid cell, as `pbdata.py`'s `POSITION_NAMES`) | empirical: GKs are 0, and a GK's bars depend on it (`PBDATA_FORMAT.md`) |
| `0x8` | u8 | current age | confirmed: `plPinfo_ChangeKan` (`0x21c840`) passes it to `plPinfo_kanLowLimit`; matches the screen |
| `0xa` | 64 × {u16 exp, u16 limit, u16 cap} | abilities (below) | confirmed, `plPinfo_ConvAbilLv` (`0x216c90`), `pwkGUtl_AddExp` (`0x246028`) |
| `0x190` | u32 | team | confirmed, `plPinfo_Team` (`0x218358`) |
| `0x198` | 0x74 bytes | a copy of the player's database record header (`PlPbase`, the offsets in [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)): name, nation, database age, height, weight, shirt, leg, skills | confirmed: `plPinfo_IsForeigner` reads `+0x1ac` (`PlPbase +0x14`), `plPinfo_SetUnumber` `+0x1c3` (`+0x2b`), `plPinfo_IsEU` `+0x1fb` (`+0x63`), `plPinfo_IsSkill` `+0x1fc` (`+0x64`). Height, weight, leg and shirt match the screen |
| `0x218` | u32 | annual salary ÷ 100, in the stored money unit | empirical: Carson 75,600 → £1,260,000, Aiblinger 72,000 → £1,200,000 (× 100 ÷ 6) |
| `0x21d` | u8 | contract years remaining | empirical: 1 and 3, as on screen. Read by the `pwkMoney_*` transfer prices |
| `0x23c` | u16 | fatigue, 0–1000 | confirmed: `plPinfo_ChangeGtired` clamps to 1000; `plPinfo_GetGTiredLevel` (`0x21b090`) gives level 0 up to 400, 1 up to 700, else 2 |
| `0x240` | u16 | condition, 0–65535 | confirmed, `plPinfo_Cond5` (`0x217800`); the bar matches (Aiblinger 88%, "fully fit") |
| `0x242` | u16 | motivation, 0–65535 | confirmed, `plPinfo_Moti2Lv` (`0x217b88`): ÷ `0x3333` gives 5 levels |
| `0x24c` | u16 | "power", 0–1000 | confirmed range, `plPinfo_ChangePower` (`0x21c8c0`). Not the T-FIT bar |
| `0x24e` | u16 | form (the game's "kan"), an age-dependent minimum to 1000 | confirmed: `plPinfo_ChangeKan` clamps it; below 400 the condition line says the player has lost form (`ConvertPlayer_Condition`, below) |
| `0x250`, `0x254` | u16, u32 | injury days left, injury kind | `_plPinfo_SetKega`, `plPinfo_KegaRecoverDaysChno`, `plPinfo_IsHkegaFunou` |
| `0x25a`, `0x25c` | u16 | captain and keyman experience | `plPinfo_ChangeCaptainExp`, `plPinfo_ChangeKeymanExp` |
| `0x278` | u32 | current play style (below) | `plPinfo_GetPStyle` / `SetPStyle` |
| `0x27c` | 5 × u32 | the style path: styles in the order the player learns them | confirmed, `ConvertPlayer_PlayStyle` (`0x285238`) |
| `0x290` | u8 | how many of the path are learned | confirmed, the same function draws the current style and this many from the path (skipping repeats and 0) as the style icons |
| `0x292` | u16 | progress towards the next style | `pwkPlayStyle_GetExp` |
| `0x294` | u8 | policy type, copied from `PlPbase +0x52` | confirmed, `pwkTeamType_PolicyInit` (`0x270328`) |
| `0x29a` | u8 | team fit, 0–100: the T-FIT bar | confirmed: `ConvertPlayer_Bar` (`0x285380`) draws it as value ÷ 100; `pwkTeamType_FitCalc` (`0x270b58`) sets it from `pwkTeamType_GetFit(manager, player)`. Carson 100, Aiblinger 60, Ben Arfa 27 match the screens |
| `0x296` | u16 | policy point, Possession (0) to Counter (65535) | confirmed, `l_calculate_policy_rect_player` (`0x300ba8`): the P marker's height is `(v + 1) / 65536` of the grid |
| `0x298` | u16 | policy point, Individual (0) to Organisation (65535) | confirmed, the same function, across |

The policy point is the P marker on a player's second page and his
number on the team vision screen. `PolicyInit` takes its start from a
table of u16 pairs per policy type at SLES `0x555340`
(`pwkTeamType_GetPolicyBseExp`); `PolicyInitNotBlong` adds a random
−5,000 to +5,000 to each axis for players outside your club. Checked on
screen: Carson (`0xffff`, `0x7fff`) is top centre; Aiblinger comes out
0.57 up and 0.37 across, where his marker is on both screens.

The rest of the record between `0x18a` and `0x2a0` is read by the functions
listed by a scan of every `PlPinfo` accessor (flags at `0x20c`, the job
change at `0x210`, dissatisfaction bytes in the database copy), not decoded
yet.

**The condition line** under the bars is chosen by
`WP::CDetailManager::ConvertPlayer_Condition` (`0x285728`), first match
wins: an injury (with the days left); flag `0x800000` at `+0x20c`
(message 11); a slump (12); fatigue ≥ 700 (17), ≥ 400 (16), ≥ 200 (15);
form < 400 (18); condition > 55,000 (14), > 40,000 (13); otherwise 19.
Checked in game: Ben Arfa with fatigue 900 shows "Seriously fatigued and
off form", Carson with form 370 "Lost form and not playing as well as he'd
like", Aiblinger with condition 58,276 "Fully fit and on top form".

The four condition bars are drawn by the end of `ConvertPlayer_Bar`:
fatigue ÷ 1000, condition ÷ 65535, motivation ÷ 65535 and team fit ÷ 100.
Team fit is recomputed from the policy points, so an edit to it wouldn't
last: move the player's policy point (or change the manager) instead.

Edits to fatigue, condition and motivation show in game as set (Ben Arfa:
900, 0 and 65,535), and abilities set to 99 with the growth limit raised
stay at 99 after training (Carson, two turns later).

Ability values are experience. `plMisc_AbilExp2Lv` (`0x2153c0`) turns
experience into a level 0–99 through 101 thresholds at SLES `0x531c70`: the
level is one below the first threshold that reaches the value, so a value
exactly on a threshold reads one level low. `plMisc_AbilLv2Exp(lv, pct)`
(`0x215438`) goes the other way, `t[lv] + (t[lv+1] − t[lv]) × pct / 100`.
The second value is the growth limit: `pwkGUtl_AddExp` (`0x246028`)
adds experience as `exp = min(exp + gain, limit)`. The third value is
always exactly a threshold, and exp ≤ limit ≤ cap holds for all 7,424
abilities of the 116 squad players in the 5 saves (**empirical**): the cap
is the player's ceiling. Young players have limits well above their
current value, veterans' limits sit on it. `save.py set` raises the limit
and cap along with the value, or the next training would clamp the edit
back to the old limit.

**Play styles.** Style names are message 150 + style of category 1
(**confirmed**: `AddPlate_PLAYSTYLE` `0x289e50` calls `Msg::GetString(5,
style)`, and type 5's base is 150; category 100001 holds the same text).
A player's database styles are the record's `+0x5e`
([`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#play-styles)): 0 none, 1 Centre Forward, 2 Moving, 3 Postplayer, 4 Dash
out, 5 Second Striker, 6 Wing, 7 Play maker, 8 Shadow striker, 9
Attacker, 10 Dynamo, 11 Man marker, 12 Covering, 13 Centre MF, 14 Winger,
15 Threaten to cut in, 16 Full back, 17 Sweeper, 18 Defensive Sweeper, 19
Stopper, 20 CB, 21 GK, 22 Attacking GK. Checked in game: the icon rows of
Carson (GK, Attacking GK), Aiblinger (Sweeper, Defensive Sweeper, Stopper)
and Ben Arfa (Attacker), and the tactics screen's Playing Style menus of
Senderos, Schram and Poulter, which list exactly their learned styles in
style order. The player's skills are the bits at `+0x1fc` (the PlPbase
copy's `+0x64`, see [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#skills)).

**Staff.** A PlMinfo (managers and coaches, 0xbc bytes) or PlSinfo
(scouts, 0x94 bytes) is 4 bytes and then a copy of the staff member's
database record (`PlMbase` / `PlSbase`, the offsets in
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md) plus 4): the name at `+4`, the
abilities at `+0x6a` (48) or `+0x31` (45).

| PlMinfo | PlSinfo | Type | What | Source |
|---|---|---|---|---|
| `0x9c` | `0x60` | s16 | database id; −1 = empty | confirmed, `plMinfo_CloseContract` (`0x216ef0`) / `plSinfo_CloseContract` (`0x218a10`) set it to −1 |
| `0x9e` | `0x62` | u8 | contract years remaining | confirmed for managers: `pwkTeam_SignManager` (`0x269e20`) stores the contract length there; matches all five staff screens checked |
| `0xa0` | | u32 | job: 0 manager (as the database starts them), 1 attacking coach, 2 defensive coach, 3 physical coach, 4 GK coach; once hired, 5 manager, 6 youth manager. Coaches and former players can also become managers | see [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md); `pwkTeam_SetYManager` (`0x26bd28`) sets 6 |
| `0xb8` | `0x90` | u32 | annual salary ÷ 100, stored money unit | empirical: £2,510,000, £950,000, £1,060,000, £990,000 and £460,000 match |

`plMinfo_GetConyear` (`0x218dd8`) is something else: the longest contract
offered, from the age at `+0x26`. `save.py staff` lists everyone with
their bars (`pbdata.py`'s staff formulas).

More of the PlMinfo (**confirmed**):

| Offset | Type | What | Source |
|---|---|---|---|
| `0xa4` | 5 × u16 | the manager's dissatisfaction, one value per `PlMCompKind` | `pwkDissatis_MAddComp` (`0x237090`) adds to `+0xa4 + 2 × kind` and clamps to 0–65,535. `pwkDissatis_CheckExplosionM` (`0x23a4d0`) returns 1 when any of the five is 65,535. `CDetailManager::ConvertManager` (`0x286ff0`) sorts them for the manager's detail screen |
| `0xae` | u16 | popularity with the supporters | `plMinfo_ChangePop_Supporter` (`0x21c6a0`), clamped to 0–65,535 |
| `0xb0` | u16 | popularity with the players | `plMinfo_ChangePop_Player` (`0x21c6f8`) |
| `0xb6` | bit 0 | salary discount | `plMinfo_GetManagerSalary` (`0x218838`) multiplies by 0.8 when set; `SetManagerDiscount` (`0x218898`), `pwkTeam_SetWithdrawPenaltyTermManager` (`0x267868`) |

The five kinds are named after the functions that add to them
(**empirical**; kind 4 is also confirmed in game, below):

| Kind | Name | Added by |
|---|---|---|
| 0 | players and staff | `pwkDissatis_Player`, `_Staff`, `_PlayerResign`, `_StaffResign`, `_MplayerMatch` |
| 1 | signings | `pwkDissatis_PlayerSign`, `_PlayerResignAfter`, `_MplayerMatch` |
| 2 | policy | `pwkDissatis_MPolicy` |
| 3 | results | `pwkDissatis_Club`, `_CompeEnd`, `_MplayerMatch` |
| 4 | facilities | `pwkDissatis_MFacility`, `_NewFacilityClub`/`Ac`/`Site`/`Stadium` |

**Empirical**, all 5 saves: only the hired manager has non-zero
dissatisfaction (for example 33,203 for players and staff and 6,553 for
results). The two popularity values are 0 in every record, so their
range in play is unknown. The first u32 of a PlMinfo or PlSinfo is a
small number (0–4) that isn't traced.

`save.py set` edits staff by label (`manager`, `ymanager`, `coach0`–`3`,
`scout0`–`2`): `manager:dissat.<kind>=` and `pop_supporters=` /
`pop_players=` (0–65,535, managers and coaches only), and
`<label>:abil.<n>=` or `abil.all=` for abilities. The abilities are
stored on the database's 38–99 scale, which `set` keeps to.

**Tested in PCSX2** (save G000 on a test card): with C.Collin's
dissatisfaction set to facilities 60,000 and the other four kinds 0, his
second page lists "Won't tolerate club's facilities." under Special
Mention, which confirms kind 4. With coach D.Walshe's abilities all 99,
every bar on his page is full.

**Pair combinations** (the tactics screen's lines and heart icons). Block
1 `+0x4808` is `PlTeamData +0x4354`: a 25 × 25 matrix of u16 by squad
slot, 0x32 bytes a row. **Confirmed:**

| Address | Symbol | What it shows |
|---|---|---|
| `0x20f638`, `0x20ed98` | `plCombi_Get` | for slots *i* < *j*, `[i][j]` is the pair's value and `[j][i]` its cap. If the byte at `+0x4e2` is 0, a pair whose bytes at `+0x4e5` + slot differ reads as 20 |
| `0x20f6b0` | `plCombi_Set` | stores a new value only when it is below the cap |
| `0x20f1b0` | `plCombi_SetInit` | starts each pair from a table at `0x530bb0` (26 u16 a row), indexed by both players' `PlPinfo +0x1ea` (the database record's `+0x52`, the policy type), with a random spread |
| `0x2e6fb0` | `CTacticsTeam::calculateCombinationLevel` | level 1 up to 13,107, then 2, 3, 4 and 5 above 52,430 (thresholds at `0x55b850`: fifths of 65,535) |
| `0x2a5518` | `CTacticsBase::refreshCombinationLevel` | each player's icon shows the level of his pair with the selected player (`GP::SetCooperationIcon`) |

The levels' icons are a skull, "…", a blue heart, a red heart and a
bigger red heart. **Checked in game:** in save G000 (2024–25), all 22
icons shown with J.Hartman selected match `save.py combi` (Galletti's
skull, the four "…", and the blue, red and big red hearts). The line
colours follow the same levels (see
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#f_43-and-f_66)).

**Empirical**, all 5 saves: the value never exceeds the cap (1,329
pairs), the diagonal is 0, and the caps are 0 or 7,000 + 7,300 × *k* for
*k* = 0–7 (7,000 to 58,100). The byte at `+0x4e2` and the 25 bytes at
`+0x4e5` are 255 in every save, so the "20" rule never applies to your
club. `save.py combi` lists the pairs, and `save.py set ...
combi:a:b=value` edits one (`combi:a:all=value` all of a slot's pairs).
It raises the cap to the value if needed, because `plCombi_Set` ignores
any value at or above the cap.

**Tested in PCSX2:** save G000 with `combi:6:20=60000 combi:6:23=0`
(J.Hartman with Galletti and with Litmanen), loaded from a test card.
With Hartman selected, Galletti's skull became a big red heart and
Litmanen's "…" a skull.

**The other clubs** (block 2). `pwkOteam_GetPointer` (`0x24b788`)
returns block 2 + 0xa8 × `pwkOteam_Team2Otindex(team)` (`0x24b7e8`): the
rival (team 2) is record 0 and teams 3–441 are records 1–439. Clubs from
team 442 (`0x1ba`) on are "non-resident" (`pwkOteam_GetPlOpinfoNonresident`)
and not in this block. **Confirmed:**

| Offset | Type | What | Source |
|---|---|---|---|
| `0x0` | u32 | team id | empirical: all 440 records in all 5 saves hold the team their position gives |
| `0x4` | 25 × 6 bytes | the squad (`PlOpinfo`, `pwkOteam_GetOpinfoPointer` `0x24b920`) | the loop at `0x24b520` steps 6 bytes 25 times |
| `0x9a` | u8 | friendship with your club, 0–100 | the `pwkOteam_ChangeFS_*` functions (matches, players moving to or from your club, overseas branches) all go through `0x24a760`, which caps it at 20 for the rival, at 70 for a club in your city or abroad without your branch, and at 100 otherwise. Shown as the FRIENDLY bar under the crest on a club's Information screen (user report; F.C. Barcelona's bar is about a third full at 34) |
| `0x9c` | s32 | main league, −1 for none | `plTeam_GetTeamMainLeague` (`0x22bf00`) reads it (your club's is PlTeamData `+0x41f4`); `SIMPRG.REL 0x150a80` sets it for each club entered in a league (`0x151f10`). The club ranking groups the Euro6 clubs by it (below) |
| `0xa0` | u8 | club rank, 0–31 | `pwkOteam_GetRank` (`0x24bec8`); `pwkOteam_Init2` starts it from the club record's rank ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)). Picks the club's reputation text (below) |
| `0xa2` | u16 | world rank points | `pwkOteam_Init2` starts it from the club record's points (0–1,020) |
| `0xa4` | u16 | world club rank (the position) | `pwkOteam_GetWorldClubRank` (`0x24bf70`) |

A squad entry, as the expander at `0x24b1e8` turns it into a PlPinfo:

| Offset | Type | What |
|---|---|---|
| `0x0` | s16 | database id, −1 = empty slot |
| `0x2` | u8 | current age (→ PlPinfo `+0x8`) |
| `0x3` | s8 | shirt number (→ `+0x1c3`); −1 keeps the database's |
| `0x4` | u8 | contract years left (→ `+0x21d`) |
| `0x5` | u8 | flags (→ `+0x20c`) |

Everything else about these players (abilities, condition, ...) is
rebuilt from the database whenever the game needs them. The save keeps
no names: by 2019 the game reuses retired players' database entries for
new young players, so "John Terry" at Chelsea is 17 in the 2019–20 save.

**Empirical**, all 5 saves: friendship 0–82, club rank 0–31, world rank
1–441 (0 in the 2005 save, before the first ranking), 22–25 players per
club. The world rank matches the game's rankings (save G000): the club
Information screen's World Ranking (F.C. Barcelona 28, Marseille 53,
Pirouzi 438), and all 20 clubs on the first and last pages of the All
Clubs Ranking (AC Milan 1 to Chelsea 10, Diaconsa 432 to Venlo 441). The
440 records hold every rank from 1 to 441 except 2, which on screen is
your own club (kept in block 1); 6 is the rival, record 0. The ranking
follows the points: sorted by world rank, the points never rise (0 to
1,023, AC Milan first with 1,023). The club rank
isn't the League Ranking shown there (26 and 24 against 7 and 5): the
League Ranking is the club's place in its league table, and only clubs in
the Euro6 (the six main leagues and their two divisions) have one (user
report). The club rank is what `pwkOteam_GetRank` returns. **Empirical:** it runs
29–31 for the clubs at the top of the world ranking and 0–5 at the
bottom, and the Information screen calls F.C. Barcelona (26) and
Marseille (24) a "World-class club" and Pirouzi (5) a "Local club", so
it is the club's status.

**Club reputation.** The text under a club's name on its Information
screen comes from the club rank. Category 203 holds two sets of six
texts (`mbb.py dump`): messages 0–5 (Local club, Home-grown club,
Promising club in *X*, Well-known club in *X*, World-class club, World
famous club) and messages 100–105 (Promising club in *X*, Well-known
club in *X*, World class club, Leading world class club, World famous
club, World champion club). *X* is variable 310, the region of the
club's nation. **Confirmed from the game code:**

| Address | Symbol | What it shows |
|---|---|---|
| `0x24baec` | `pwkOteam_GetTeamData` | a club's PlTeamData `+0x41f8` is `pwkOteam_GetRank`, so `+0xa0` here |
| `0x2883f0`–`0x288474` | `WP::CDetailManager::ConvertTeam` | the page type at `+0x4fa8`: 2 for teams 460–542 (`0x1cc`, 83 teams), 1 for your club, 4 for teams 442–459, 0 for the other clubs (3 when a flag at `+0xa31c` is set, not traced) |
| `0x288a24`–`0x288af0` | `ConvertTeam` | the message is *n* = how many of the 6 thresholds at `0x557710` (6, 12, 18, 24, 30, 32) the club rank reaches; page type 2 uses 100 + *n* |
| `0x288c50` | `CheckTeamKoteiMessage` | always returns 0, so no club has a fixed text |
| `0x28cbdc`–`0x28cc14` | `SetupDetailTeamPage1` | fills variable 310 (`0x136`) with `plMisc_Nati2Region` of the club's nation |

So club rank 0–5 is Local club, 6–11 Home-grown, 12–17 Promising,
18–23 Well-known, 24–29 World-class and 30–31 World famous. Across the
440 clubs in save G000 that gives 88, 125, 104, 77, 38 and 8.
(`GetClubRankIndex`, `0x247010`, with 8 bands at `0x54e050`, only feeds
the transfer prices. The loads of 203 in `SIMPRG.REL` at `0x12f10` and
`0x70954` are a message window id.) The same category holds the team
style text under it: messages 20–49 are six levels each of attack-minded,
defence-minded, athletic, tactically-minded and formation-minded.
`ConvertTeam` (`0x288af4`–`0x288c14`) picks the largest of the team's
graph values, skipping the fifth. It then picks the level from the 6
thresholds at `0x557728` (56, 66, 76, 86, 92, 101).

**How the club rank changes.** `SIMPRG.REL` ranks the clubs by their
world rank points, using `PARAM/CLUB_RANK_SYSTEM.TBB`
([`PARAM_DIR.md`](PARAM_DIR.md)). When in the season it runs isn't
traced (`0x150680` updates the points, `0x150738` the ranks).
**Confirmed:**

| Address (`SIMPRG.REL`) | What it shows |
|---|---|
| `0x150c10`–`0x150d08` | the loader keeps the five tables of `CLUB_RANK_SYSTEM.TBB` at object `+0x18`, `+0x20`, `+0x2c`, `+0x34` (with the row count at `+0x38`) and `+0x3c` |
| `0x151568` | the new world rank points of each club in nations 1–52: three weighted values plus the club rank, minus half of byte 2 of the nation's UEFA record. Clubs elsewhere get table 2's s16 for their rank, ±60 at random. Capped at 1,023 |
| `0x151d58` | for each Euro6 nation (1–6) and each of its two divisions, the clubs of that division |
| `0x151e60` | for nations 7–52, all the nation's clubs |
| `0x151c10`, `0x151a28` | sorts the list by world rank points (`+0xa2`), highest first. Your club and the rival take their nation from your league (`plMisc_Club2Nati` `0x215b78`) |
| `0x151ce0` | picks the table-3 row: nation slot = byte 2 of the nation's UEFA record (block 5 `+0x46638` + 4 × nation) |
| `0x151938` | hands out the ranks: row byte 2 + *i* (*i* = 0–31) is a running position in the list; the clubs before it get rank 31 − *i*, and 0 skips that rank. Teams 1 and 2 take their place but aren't changed |

Table 3 has 65 rows of 34 bytes: `{s8 nation slot, s8 league size,
32 × s8 positions}`. Rows 7–18 are the Euro6 first divisions, by nation
slot 1–6 and 20 or 18 clubs. Rows 0–6 are the second divisions (slot −1)
by size, 18–26 clubs. Rows 19–64 are nations by slot 7–52 (size −1). For
example, slot 7's row reaches positions 1–5 at ranks 27, 24, 20, 15 and
10. Clubs past a row's last position keep their old rank, and clubs
outside nations 1–52 are never ranked.

**Empirical:** this rule gives the stored rank of every ranked club in
the four saves after the first season (382 clubs each, G001, G003, G006
and G000). The only exceptions are pairs of clubs with equal points that
the game sorted the other way (2, 4, 2 and 0 clubs; `qsort` doesn't keep
ties in order). The 57 clubs outside nations 1–52 keep their starting
rank in all five saves.

**Your club and the rival.** Neither is changed by this ranking. Both
follow your club's status instead. **Confirmed from the game code:**

| Address | Symbol | What it shows |
|---|---|---|
| `0x26e2f0` | `pwkTeam_Status` | the club status is the u16 at block 1 `+0x1126a` |
| `0x26dbb8` | `pwkTeam_StatusChange` | adds a change to the status and keeps it within 0 and a cap: the u16 at `0x555150` + 2 × the status rank (s32 at block 1 `+0x11264`, 0–8) |
| `0x26dc50` | `pwkTeam_StatusChangeRank` | only ever lowers the status rank. `pwkTeam_MatchGameCheck` and `pwkTeam_YearEndCheck` call it; `0x26dcc8` maps competitions `0x22`, `0x23` and `0x24` to ranks 0, 2 and 3 |
| `0x26e328` | `pwkTeam_StatusInit` | a new career starts at status rank 7, your club rank 0 and the rival's 7 |
| `0x26dd40` | (no symbol) | sets your club rank (PlTeamData `+0x41f8`, block 1 `+0x46ac`) to status >> 11, capped at 31, and the rival's (`+0xa0` of record 0) to the byte at `0x555168` + your club rank |
| `0x26df74`, `0x26e274`, `0x26e2d4` | `pwkTeam_GameCheck`, `MatchGameCheck`, `YearEndCheck` | call `0x26dd40` after the status change, so both ranks catch up after each match and at year end |

The caps by status rank 0–8 are 65,535, 60,000, 55,000, 40,000, 30,000,
25,000, 10,000, 7,000 and 7,000. The rival's rank for your rank 0–31 is
12, 15, 17, 18, 20, 21, 22, 23, 24, 25, 26, 26, 26, 27, 27, 27, 28, 28,
28, 29, 29, 29, 30, 30, 30, then 31 from your rank 25 on.
`pwkTeam_GetMyClubRank` (`0x259b60`) divides the status by 2,047
instead, for transfer prices, coach salaries, the audience and youth
promotion. **Empirical:** in all
five saves the status is within its cap and your club rank is status >>
11. The rival's rank matches the table in four of the five; the
exception is the 2005 save (rank 11, table 12), made before the first
match check.

`save.py show` prints the status, status rank, cap and both ranks.
`save.py set ... status=N status_rank=N` writes them and sets both club
ranks as `0x26dd40` would. A status above the cap is refused, because
the game would cut it back to the cap at the next change.

**Tested in PCSX2** (save G000 on a test card): with `status=30000`
(65,535 before), your club's Information screen said "Promising club in
Europe" (club rank 14; "World famous club" before) and the rival's
"World-class club" (rank 27; "World famous club" before). Variable 310
shows as "Europe" for a Spanish club.

**The community account.** A community write-up (overthetop2, "Club
reputation and AI club strength", March 2024) says an AI club's level
comes from its world ranking within its country, with each country's
number of top-level clubs set by its Euro coefficient. The code agrees,
with corrections: the order is by world rank points, a Euro6 club is
ranked within its division, and a club past the row's last place keeps
its old rank. The write-up says your club's level comes from the world
ranking alone (World famous in the top 30). The code ties it to the
club status instead. The rival "gets boosts" in that its rank comes from
yours through a table that puts it well above you early on (12 when you
are at 0). The write-up also says the level limits the players
an AI club signs; that isn't checked.

Bytes `+0x9b`, `+0xa1` and `+0xa6`–`+0xa7` aren't traced. `save.py
clubs` lists the clubs with their reputation text and main league (with
their squads for the teams named). `save.py set ... club:<team>:friendship=`
and `club:<team>:rank=` (0–31) edit them.

**Tested in PCSX2** (save G000 on a test card): with
`club:167:friendship=100 club:54:friendship=0`, F.C. Barcelona's FRIENDLY
bar was full and Marseille's empty (82 before).

**Tested in PCSX2** (save G000 on a test card): with
`club:432:rank=31 club:54:rank=0`, Pirouzi's Information screen said
"World famous club" (rank 5, "Local club", before) and Marseille's "Local
club" (rank 24, "World-class club", before). The style line under it
stayed as the code picks it ("Fairly defence-minded", "Not very
attack-minded"), and the world rankings (438, 53) didn't change.

**Match statistics.** For squad slot `s`, the stats start at block 1
`+0xec8e + s × 0x11e`: four tables of five rows (pre-season, domestic
league, overseas league, Euro, international), then 6 bytes not traced.
A row is 14 bytes:

| Offset | Type | What |
|---|---|---|
| `0x0` | u16 | goals |
| `0x2` | u16 | assists |
| `0x4` | u16 | games played |
| `0x6` | u16 | the club's games while the player was there |
| `0x8` | u16 | man of the match |
| `0xa` | u16 | average points × 100 |
| `0xc` | u8 | red cards |
| `0xd` | u8 | yellow cards |

Table 2 is the Season Stats page and table 4 Career Stats (**empirical**:
every value on both pages matches for Carson and Aiblinger). Table 3 looks
like last season (38 league games for a regular). Table 1 is empty in
every slot checked. The Total lines are computed by the screen.

## Decoding

The ten serializers are generated code: 1,575 calls to
`_plBits_BitRead`/`_plBits_BitReadStr` on the read side and 1,574 to the
write versions, with loops for arrays. Those four functions are the only
imports they call. Rather than transcribe that layout, `save.py` runs the
read or write function for each block in an interpreter for the R5900
instructions they use: integer ALU, loads and stores, branches with delay
slots, three-operand `mult`, MMI `madd`, and `lq`/`sq` for register saves.
The four imports are Python functions over the bit stream. `SAVEPRG.REL`
is linked at base 0, so it runs from address 0 without relocation.

The result matches the game exactly: all 5 saves decode and re-encode to
byte-identical files.

Interpreting takes about 8 seconds a save, so `save.py` does it once. The
generated code stores each value into the block right after reading it,
so one run of the read functions gives a flat field list: for each
`_plBits_BitRead` call its bit count and signedness, and the offset and
width of the first store into the blocks that follows (each string byte is
a field of its own). Replaying the list reads or writes a save in about a
second. The list is cached in `.cache/` (git-ignored), keyed by
`SAVEPRG.REL` and the block sizes.

| | Count |
|---|---|
| fields | 604,078 |
| bits | 5,169,290 (the stream length of every save) |
| signed fields | 114,509 |
| bytes of the blocks written | 947,298 of 1,035,469 |
| widths | 1–10, 14, 16, 18, 32 and 64 bits; 8 bits is the most common (143,512) |

`python SRC/save.py fields` records the list afresh and checks it: over
random streams, the replay must give the same blocks as the interpreter,
and over random blocks the same stream. That covers data the real saves
don't, so it also shows the layout doesn't depend on the contents (no
counts or flags that change which fields follow).

## Separate saves for a modded disc

`MC::CFcEuroIF::initialize` (SLES `0x12ad38`) picks the memory-card name
for each `eCATEGORY` from three strings:

| Category | Address | Name | Use |
|---|---|---|---|
| 0 | `0x5213e8` | `BESLES-54151-G` | saved games, plus `%03d` |
| 1 | `0x5213f8` | `BESLES-54151-C` | VS data, for VS mode and for Virtua Pro Football |
| 2 | `0x521408` | `BESLES-54153FASYS` | Virtua Pro Football's save, read by the import feature |

No other file on the disc contains the serial. `save.py serial` writes a
copy of `SLES_541.51` with categories 0 and 1 moved to another serial of
the same length (`PYRA-31396` → `BEPYRA-31396-G000`, `BEPYRA-31396-C000`).
Moving the VS data is deliberate, as anti-cheat: teams built in a modded
game can't be carried into Virtua Pro Football or an unmodded game's VS
mode. Category 2 stays, so the import from Virtua Pro Football still
works.

That only separates the saves. PCSX2 (and disc loaders) take a disc's
serial from the boot file named in `SYSTEM.CNF`
(`BOOT2 = cdrom0:\SLES_541.51;1`), so a disc that still boots
`SLES_541.51` still shows up as SLES-54151 (**empirical**: tested in
PCSX2). `save.py serial` therefore also writes the executable as
`PYRA_313.96` with a `SYSTEM.CNF` that boots it, and prints the
`patch_disc.py` command that patches both and renames the file on the
disc (`--rename`, see [`REBUILD.md`](REBUILD.md#usage)). The names are the
same length, so nothing moves. Nothing in the executable refers to its own
file name. Changing the executable changes its CRC, so PCSX2 patches and
cheats keyed to the original CRC won't apply to the modded disc.

Tested in PCSX2: the renamed disc boots as PYRA-31396. PCSX2 doesn't show
it in its game list without a GameDB entry for that serial, which this
project doesn't provide. The serial change is an optional feature for
mods that want their own saves; the default is to keep SLES-54151.

The game opens `<folder>/<folder>`, so a save moved to the new serial
needs both names changed. `save.py rename` copies a save folder with both
renamed, and fixes the name in PCSX2's `_pcsx2_meta_directory` (`+0x40`)
and `_pcsx2_index` for folder memory cards.

## Still unknown

- The T-FIT bar, table 1 of the statistics, and the rest of PlPinfo
  (flags, dissatisfaction, style icons). The rest of the blocks: the
  accessors that call `get(i)` are the way in.
- `info.bin` past the date, and `dm.bin`.
- Whether the game checks `info.bin` against the main file.
- The VS data (`BESLES-54151-C000`, main file 16,152 bytes). It uses the
  same key and header (layout CRC `0x8ffb`, version 0), and its `info.bin`
  (1,024 bytes) starts with a date under `FC_EURO_2005`. The layout inside
  hasn't been traced (the VS load is at `SAVEPRG.REL 0x33868`).

## Checking

```bash
python SRC/save.py blocks
python SRC/save.py info  <card>/BESLES-54151-G003
python SRC/save.py roundtrip <card>/BESLES-54151-G00*
python SRC/save.py show  <card>/BESLES-54151-G003
python SRC/save.py combi <card>/BESLES-54151-G000 6
python SRC/save.py clubs <card>/BESLES-54151-G000 167 54 432
python SRC/save.py finances <card>/BESLES-54151-G000
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x26dd40 38
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x288a24 60
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 151938 60 --sles ISO/SLES_541.51
python SRC/tbb.py dump DAT/PARAM/CLUB_RANK_SYSTEM.TBB 3
python SRC/save.py set   <card>/BESLES-54151-G003 edited.bin money=2000000000 0:all=99
python SRC/snr2.py dis ISO/DLL/SAVEPRG.REL 0x33140 160 --sles ISO/SLES_541.51
python SRC/sles_disasm.py ISO/SLES_541.51 dis initialize__Q22MC9CFcEuroIF pwkGen_GetSikin plMisc_AbilExp2Lv
```
