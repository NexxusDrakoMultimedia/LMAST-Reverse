<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# The club's economy

How the game charges for facilities, where the season plan's limits are
set, and what the ad budget, ticket price and season tickets do to
attendance, income and popularity. The research behind the LMASTER Mod's
harder economy ([`LMASTER_MOD.md`](LMASTER_MOD.md#improvements)).

Money is in the game's stored unit (£1 = 6, €1 = 4); the accounts, the
season plan and the income and payment types are in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far). All addresses
are PAL. Overlay addresses are in `SIMPRG.REL`, the rest in
`SLES_541.51`.

## The business cycle

The town has a business cycle (*keiki*, 景気), a value 0–4 at the start
of Pwork block 4 (`pwkTown_Keiki`, `0x2718e0`). `pwkTown_Init`
(`0x271868`) picks it at random, and `pwkTown_UpdateAnnualy` (`0x2718b0`
→ `0x271740`) moves it each season along random patterns (tables at
`0x555f88`–`0x556000`). It scales every build cost (below) and is read
by about 25 other functions, among them transfer fees and the staff
candidates. What it does there isn't traced.

**Empirical:** saves G000, G001 and G006 are in state 1, G002 and G003
in state 2.

## Build costs

**Confirmed from the game code.** The facility window
(`WP::CInstDetailWnd`) starts a build through `0x153c28`. That function
calls the build kind's own build function (jump table at `0x23ce40`),
then pays the cost from `0x154b78` with `pwkGen_Pay` (`0x153de0`), as
the payment type that the table at `0x23cdf0` gives the kind. A kind
whose type is 23 is paid nothing.

`0x154b78` (kind, slot, mode) has two modes. Mode 1 returns the
facility's monthly upkeep, unscaled, for the screen (getters at
`0x23d000`). Any other mode returns the build cost:

> cost = base × cycle% ÷ 100 × (100 − sponsor discount) ÷ 100, and at least 0

- **base** comes from the kind's getter (table at `0x23d098`), which
  reads the facility record in `PLRESOURCECOMMON.PAC` entry 0
  ([`PLRESOURCECOMMON_FORMAT.md`](PLRESOURCECOMMON_FORMAT.md#entry-0-facilities)).
- **cycle%** is 125, 110, 100, 90 or 75 for business cycle 0–4 (s32
  table at `0x23cc90`).
- **sponsor discount** is `pwkSponsor_GetDiscount` (`0x16c5e0`) for the
  category that `0x1563e8` picks for the kind and slot. It applies only
  when it is above 0.

| Kind | Facility | Base (record offset) | Getter | Payment type |
|---|---|---|---|---|
| 0 | stadium | `+0x2c` | `0x154f48` | 0 Stadium purchase & rebuild |
| 1 | stadium stands | `+0x2c`, `+0x5c` and the advert record's `+0x8` (not traced in full) | `0x154f78` | 0 |
| 2 | stadium equipment | `+0xc` | `0x155090` | 1 Stadium facilities |
| 3 | stadium equipment | `+0x1c` | `0x155238` | 1 |
| 4, 5, 9, 16–18 | – | none (`0x1c85d0` returns 0) | – | none (23) |
| 6 | site | `+0x8` | `0x1550b8` | 4 Practice ground expansion |
| 7 | training-ground equipment | `+0xc` | `0x1550f0` | 5 Practice ground facilities |
| 8 | training-ground equipment | `+0x1c` (`+0x30` past the first group) | `0x155260` | 6 Practice ground maintenance |
| 10 | club house | `+0xc` | `0x155140` | 2 Club house extension |
| 11 | club-house equipment | `+0xc` | `0x155178` | 3 Club house facilities |
| 12 | office equipment | `+0x8` | `0x1551a0` | 3 |
| 13 | youth-house equipment | `+0xc` | `0x1551e8` | 3 |
| 14 | club-house equipment | `+0x1c` | `0x155300` | 3 |
| 15 | youth-house equipment | `+0x1c` | `0x155380` | 3 |

Kinds 3, 8, 14 and 15 charge a second cost at `+0x1c`. **Empirical:**
it is a tenth of the build cost in every record that has one (stadium
equipment 0: 4,500,000 and 450,000). Kind 8 is booked as "Practice
ground maintenance", so this is probably a repair. What the window calls
it isn't traced.

**Empirical,** two saves: G001 (cycle 1) booked 3,300,000, 1,650,000,
9,900,000 and 14,850,000 under payments 0, 1, 3 and 5. Those are 110% of
table costs (1,650,000 is stadium equipment 4's 1,500,000). G003
(cycle 2) booked 2,400,000 and 6,000,000 under payments 1 and 3. Those
are 100% (2,400,000 is stadium equipment 1). So a mod that changes a
facility's cost only edits the record. **Tested in PCSX2** with
`plrcommon.py set`: edited costs showed in the facility window and were
charged ([`PLRESOURCECOMMON_FORMAT.md`](PLRESOURCECOMMON_FORMAT.md#editing-the-facility-records)). The cycle and any sponsor
discount still apply on top.

## The season plan screen's limits

**Confirmed:** the plan screen's set-up at `0x3eda0` gives its four
spin controls their limits as constants in its code, in the stored unit.
The step depends on the currency; the three values are for the euro,
the pound and the yen. The setters (`pwkUnkei_SetPR`, `SetTicket`,
`SetSeatNum`, `0x271d50`…) store whatever they are given, so these
instructions are the only check.

| Control | Min | Max | Steps (€, £, ¥) | Set at |
|---|---|---|---|---|
| ad budget | 0 | 30,000,000 (£5,000,000) | 40,000, 60,000, 300,000 | max `0x3eec0`/`0x3eec4` (`lui`/`ori`), steps `0x3ee8c`–`0x3ee98` |
| ticket price | 60 (£10) | 300 (£50) | 4, 6, 3 | min `0x3ef94`, max `0x3ef98`, steps `0x3ef64`–`0x3ef6c` |
| season-ticket rate | 50 | 150 | 10 | min `0x3f05c`, max `0x3f060`, step `0x3f034` |
| season tickets | 0 | capacity × 0.8 | 100 | factor `0x3f17c`/`0x3f180` (float 0.8), step `0x3f154` |

This confirms the limits the user reported in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far). The ticket
minimum's register also fills a second field of the control (`+0x478`),
so a patch should change only the immediate at `0x3ef94` and check that
screen.

## What the ad budget does

The ad budget (`pwkUnkei_GetPR`) is read in four places:

| Reader | Effect |
|---|---|
| `0x251f38`, from the monthly costs (`0x2528c0`) | payment 17, a twelfth of the budget each month ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far)) |
| `pwkUnkei_GetTicketHosei` (`0x2719c8`) | the ticket demand value behind attendance and season-ticket sales (below) |
| `pwkSche_UpdateMonthly` (`0x255428`) | each month, the expected attendance of the next 8 turns (`GetExpectTicket`, stored with `pwkSche_SetTicket`) |
| `0x268b00`, from `pwkTeam_ChangePop_Month` (`0x269350`) | supporter popularity: budget ÷ 600,000 points a month (below) |

### Supporter popularity

**Confirmed.** Each month `pwkTeam_ChangePop_Month` works out a change
for your home region and for each of the 13 overseas regions where you
have a branch. It adds the change to the region's popularity
(`pwkTeam_PopChange`, `0x267ff8`): a u16 per region at block 1
`+0x11248`, floored at 0 and capped by the popularity rank at `+0x11228`
(caps 65,535, 50,000, 40,000, 30,000, 15,000, 10,000 for ranks 0–5,
table at `0x554df0`). The change from `0x268b00` is the sum of:

| Term | Value |
|---|---|
| star players | your five most popular players' average popularity (`PlPinfo +0x238`, or `+0x23a` overseas, `plPinfo_ChangePop`) ÷ 10,000, clamped to 0–6, through the table 0, 10, 20, 40, 60, 80, 100 (`0x554eb0`) |
| ad budget | budget ÷ 600,000: 0 to 50 within the screen's limits |
| stadium | 0, 4, 7, 10 or 14 by stadium level (`plTeam_Stadium2StadiumLv`, `0x554eb8`); home region only |
| TV | `pwkTv_DoesCoverSpecificArea`; overseas regions only |
| years | 4 × (season − 2006) from 2007 on |
| new kit | −20 when `pwkGd_DoesChangedUniType` |
| supporter complaints | minus the largest `pwkSupCom_GetSupporterComp` of 9 kinds ÷ 2,622 |

Overseas regions multiply the result by two factors: the branch's level,
(level + 1) ÷ 5 + 0.4 (`0x268e18`: 0.6–1.2 for levels 0–3;
[`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md#entry-1-overseas-branches),
where `--mod overseas-bases` makes it 0.8–2.0), and a float from
`0x554ec8` picked by `plMisc_OFcheck`(the largest `+0x1b0` among your
players from that region, 15) (`0x268e70`).

## Attendance and ticket income

### The ticket demand value

`pwkUnkei_GetTicketHosei` (ticket price, ad budget), **confirmed**:

- The price picks a row of a 21 × 11 s32 table (`0x556250`). Row
  *i* is for prices up to 300 − 12 × *i* (thresholds at `0x556120`), so
  a price is rounded up to the next multiple of 12. A price under 60 uses
  row 20 and a price over 300 uses row 0.
- The budget picks a column, budget ÷ 3,000,000 (at most 10). The value
  is interpolated linearly towards the next column, so the budget counts
  smoothly up to 30,000,000. A higher budget adds nothing.

| Price (stored) | Budget 0 | 15,000,000 | 30,000,000 |
|---|---|---|---|
| 300 (£50) | 10 | 90 | 165 |
| 180 (£30) | 27 | 240 | 440 |
| 60 (£10) | 100 | 900 | 1,650 |

So a cheap ticket brings in up to 10 times the crowd of a £50 one, and
the ad budget multiplies demand by up to 16. A wider ticket range needs
new rows in this table as well as new screen limits. Without them every
price outside 60–300 behaves like the nearest end.

### A home match

`pwkUnkei_GetAllAudience` (`0x272128`), **confirmed**, for your home
match:

> walk-ups = (home popularity ÷ 10 × 130 + (*k* + 1) × 3,000) × demand × (grade + importance) × weather × (95–104) ÷ 60,000,000

The result is capped at the stadium's capacity. Home popularity is the
region value above. `patch_disc.py --mod fanbase` (in `--mod balance`)
makes the 130 195 and the 3,000 1,500 (`addiu` immediates at `0x2722d8`
and `0x2722f0`), so the crowd follows popularity more and the fixed part
less: at the full 65,535 the first part grows by about half, while a
club of popularity 5,000 and *k* = 10 keeps about what it had. *k* is the function's u8 argument, 0–32 by its
tables (the club rank would fit; not traced). Grade is 11, 10, 9, 8, 8,
8, 5, 0 by `PlMatchGrade` (`0x556218`). Importance is 11, 13, 12, 11,
11, 40 by `IMPORTANT_MATCH` (`0x556238`). Weather is 10, 10, 5, 5, or
10, 10, 8, 8 for the other table (`0x5561f8`, `0x556208`). The game's
own random number gives the 95–104.

For a league home match it then adds the season-ticket holders:

1. Holders who come = season tickets × sold% (plan `+0x14`) × a turn-up
   rate (`pwkUnkei_GetTodayRate`, `0x2720a8`, at most 100%) ÷ 10,000.
2. The walk-ups are cut by the share of the ground the sold season
   tickets take, and the holders who came are added.
3. That sum is multiplied by (100 + club event bonus − cut) ÷ 100. The
   cut is 5%, or 15%, 30% or 50% once 60%, 80% or 95% of the season
   tickets on sale are unsold. It is 0 with no season tickets on sale.
   The club event bonus is `plClubEvent_GetTicket` during a successful
   club event.
4. The total is capped at the capacity. The paying crowd is the total
   minus the holders who came.

An away match's crowd is capacity × (70–95% by *k*, `0x5561d8`, plus 0–5)
× (95–104) ÷ 10,000.

### Match income

`pwkUnkei_GetMatchIncome` (`0x273008`) fills the match record that
`pwkUnkei_BeforeReport` (`0x272ef8`) books, **confirmed**:

| Record | Value | Booked as |
|---|---|---|
| `+0x8` | paying crowd × the competition's ticket price (`GetOtherTicket`) | income 4 Ticket price |
| `+0x10` | `pwkUnkei_GetShopIncome` (below) | income 8 Stadium facilities |
| `+0xc` | the competition rule's `+0x22` × 10,000, when you win | income 5 Win bonus |
| `+0x18` | total crowd × 15 × (95–104) ÷ 100 | payment 20 Match management |
| `+0x1c` | `0x272fd0`: a per-competition sum (22 `{competition, amount}` records at `0x3997c0`) | income 11 |
| `+0x20` | player bonuses (`pwkPromise_MatchBounus`, `0x272ca8`) | payment 16 |

After booking, the schedule stores the crowd as a percentage of the
capacity (`pwkSche_SetTicket`) and adds it to the season's attendance
(`pwkSche_AddAudience`).

**Shop income** (`pwkUnkei_GetShopIncome`, `0x272ab8`) walks 16
stadium equipment slots, the bytes at your stadium data
(`pwkTeam_GetStadium`) `+0xf` + 2 × slot. Each set slot adds: slots 1
and 2 crowd × 15, slot 3 crowd × 30, slot 9 crowd × 45, and slot 15 club
status × 30, each × (90–109) ÷ 100. The other slots add nothing.

## Season tickets

**Confirmed.** The plan's season-ticket price is ticket price × rate ÷
100 ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far)).
`pwkUnkei_CalcSeat` (`0x2733a0`) stores the share sold, 0–100, at plan
`+0x14` from `pwkUnkei_GetExpectSeat` (`0x2727c8`):

> demand = (home popularity ÷ 10 × 130 + 27,000) × ticket demand(season-ticket price, budget) × status factor ÷ (rate ÷ 100) × 18,000 ÷ 60,000,000
>
> sold% = demand × `pwkUnkei_GetSeasonRate`(popularity, club status) ÷ season tickets on sale, at most 100

(27,000 and 18,000 are for the bool argument `CalcSeat` passes, false;
true gives 66,000 and 19,000.) The first part is the walk-up formula's
popularity / 10 × 130 + (*k* + 1) × 3,000 with *k* = 8 (21 for true),
from the same immediates at `0x2728ec` and `0x2728f0`, which
`--mod fanbase` changes as it does the crowd's.

`GetSeasonRate` (`0x271ae8`) is a 15 × 15 byte table (`0x5565f0`) indexed
by popularity ÷ 4,369 and club status ÷ 4,369, from 10 (both low) to 80
(both high). The demand is 0 when its first part is below 2,501.

The status factor has a bug. The code tests status ≤ 10,000 for 0.5
and otherwise gives 0.6. Its later steps (0.7, 0.8, 0.9, 1.0 above
20,000, 30,000, 40,000 and 50,000) sit behind tests that can't succeed,
because the first test already took every status above 10,000
(`0x272838`–`0x2728dc`). A top club sells season tickets as if it were
an average one. The Japanese executable has the same 31 words (at
`0x2728f0`). `patch_disc.py --mod season-status` (in `--mod lmaster-lite`)
rewrites them as the intended ladder: 0.5 up to 10,000, then 0.6, 0.7,
0.8 and 0.9 a band of 10,000, and 1.0 above 50,000. Checked by running
both versions in a small MIPS simulator over the band edges.

**Tested in PCSX2** (`LMAST-test-seasonstatus.iso`, user's career saved
to `Mcd001.ps2` as G002 and read off it with `ps2mc.py get`): with
popularity and club status at 65,535 and 88,000 season tickets on sale
at the start of 2025–2026, the save holds 72% sold. That is the
formula's value with the fixed band (1.0); the retail 0.6 gives 43%. The
same career's previous plan, set on the retail game (39,000 on sale),
holds 98%, the formula's retail value.

The money comes in at the start of the season through the event
command that books income 3 (`SIMPRG.REL 0x121258`,
[`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md)). It pays season-ticket
price × tickets sold (`pwkUnkei_GetSaleSeatNum`: on sale × sold% ÷ 100)
× a factor that `0x15eeb8` picks by your league's competition (jump
table at `0x23d890`). **Empirical:** the factor is the division's home
league matches. It is 19 for competitions 0, 10, 20, 28 and 38, 25 for
1 (the English second division with your club, 26 clubs), 21 for 11 and
48, 17 for 19 and 47, and 23 for every other. The table is fixed per
competition, so a league resized with `leaguesize.py` keeps its old
factor.

**Checked on a save:** G000 (home popularity 65,523, club status
65,326, season tickets at 220 with a 30,000,000 ad budget, 39,000 on
sale) gives a ticket demand of 304 and sold% 98, the value in the save.
G006's inputs give demand for about 36,460 against its 36,000 on sale,
so it just sells out (it holds 100).

## Sponsors

**Confirmed.** The sponsors are a table in `SIMPRG.REL`, not a disc
file: 212 records of 0x48 bytes at `0x23d978`, ids 1–212
(`plSponsor_GetDb`, `0x160dc0`). A candidate's fee is set when the
candidate list is built (`0x1690a0`, `0x1691a8`): the record's `+0x14`
(main sponsor) or `+0x18` (the other kind) × the business-cycle factor,
1.25, 1.1, 1.0, 0.9 or 0.75 (doubles at `0x1daba0` and `0x1dac40`), stored
at the candidate's `+0xc`. Signing books fee × 100 as income 0, once
(`0xc8234`). A bigger club isn't paid more by the same sponsor; it is
offered bigger ones (which sponsors a club is offered isn't traced).

**Empirical:** 210 records have fees. `+0x14` runs £500,000–£45M
(median £3.45M), `+0x18` £50,000–£45M (median £345,000). Four records
(170, 174, 186, 194) hold the £1,350,000 of Africmap Airways, the first
main sponsor of a new career ([`SPONSOR_NEGOTIATION.md`](SPONSOR_NEGOTIATION.md#tested-in-pcsx2)).

## TV contracts

**Confirmed.** A club holds up to 3 TV contracts, 0x10 bytes each at
block 1 `+0x11c54`: `+0x0` station (0 = free slot), `+0x4` amount,
`+0x8`/`+0x9` years, `+0xa` kind. Each payment is the sum of the amounts
× 100, booked as income 2: on signing (the broadcast screen,
`0xb1cb8`) and through `Pwk.CheckTV` (`pwkTv_Add_TVpremium`,
`0x163e88`, from SLES `0x111620`).

An offer's amount (`0x163a10`, from the offer list `0x164088`) is
base × the business-cycle factor (1.25–0.75, doubles at `0x1d9e70`) × a
home-popularity factor: 0.9, 0.95, 1.0, 1.05 or 1.15 for popularity in
fifths of 0–65,535 (`pwkTeam_Pop(0)`; each factor a double built in
`$s1` by 7 instructions, `0x163a60`, `0x163a90`, 1.0 at `0x163a34`,
`0x163ad8`, `0x163b14`). `--mod fanbase` makes them 0.75, 0.875, 1.0,
1.125 and 1.25, each built by `ori` and `dsll32` as the 1.0 is. The bases are the 19 records of
0x1c bytes at `0x241780` (`+0x0` station, `+0x8` base, `+0xc` key):
£1M–£4.75M for the 13 smaller offers, £8.5M–£16.5M for four bigger
ones and £30M and £50M at the top (base × 100 ÷ 6). Which stations
are on offer is a 60-bit mask at block 1 `+0x127c0`, kept by
`pwkTv_UpdateStatus` (`0x164598`) from the 60 station records at
`0x241a00`.

**Checked on a save:** G006's contracts are stations 14, 16 and 2 at
1,143,450, 589,050 and 138,600, each its base × 1.1 (cycle 1) × 1.05
(popularity 50,000). Their sum × 100 is 187,110,000, G006's TV income
for the season. G000's three 4-year contracts hold 15% more than the
formula; what the term adds isn't traced.

## Merchandise

**Confirmed.** Merchandise income (income 7) is
`pwkGd_GoodsMonthlySales(1)` (`0x165dc0`), stored each month at SLES
`0x3991e0` (`0x251ed8`) and read by `pwkRec_CalcMonthGoodsIncome`
(`0x253008`). The goods on sale are 12 slots of 0x10 bytes at the club's
Pwork `+0x12700` (`pwkGd_GetMakeGoodsData`, `0x164b18`), each naming a
record of the shop list: 60 records of 0x10 bytes at `0x241a00`
(`0x164ac0`), `+0x0` id, `+0x1` kind, `+0x8` u32 price (stored unit; 36
to 360 for the ordinary goods, £6–£60). For each slot the month's units
are

> units = round(base × trend × combo × player × kit × kit2 × weather + 0.5)

| Factor | Function | Value |
|---|---|---|
| base | `0x165598` | from the supporters, below |
| trend | `0x165638` | a float table by months on sale (`0x1d9f60`, 12 a row) and the item's hit or flop (`0x1647f0`; `SetBigHitGoodsId`, `SetBigDisGoodsId`) |
| combo | `0x165798` | a percentage ÷ 100 (at most 1.0) from the 18 combination records of 10 bytes at `0x241dc0` that the goods on sale match |
| player | `0x165920` | for a player's goods, that player's popularity abroad (`PlPinfo +0x23a`) ÷ 4,369 through `0x1da320` (0.05–1.5); 0.1 with none, 0.8 when the slot names no player |
| kit, kit2 | `0x165b30`, `0x165c00` | for kit goods (shop list `+0x3`) from the 2009 season: 0.8 when the kit's type changed (club `+0x129d0`, `+0x129d2`), and by how many recent kits were the same (`0x1da360`: 1.0, 1.0, 0.8, 0.5); 1.0 otherwise |
| weather | `0x165a78` | 0.5 when the home city's temperature (`plCity_GetTemperature`) is under 11, 16 or 26 for goods of weather type 1, 2 or 3 (shop list `+0xc`) |

The units sold (at most the stock left) × the price (half in month 6 of
the date, `PlDate +0x3`, when sold-out goods aren't reported either) ×
the business cycle's 125, 108, 100, 92 or 75 (`0x1da370`) ÷ 100 is the
slot's income.

**The base** sums `pwkTeam_Supporter` over the 13 regions and finds it in
17 `{threshold, base}` pairs at `0x1d9ec8`: 800 below 10,001 supporters,
then 1,000, 1,200, 1,400, 1,600, 1,800, 2,000, 2,200, 2,400, 2,800,
3,200, 3,600, 4,000, 6,000, 7,000, 8,000, and 10,000 above 10,000,000. A
region's supporters (`pwkTeam_Supporter`, `0x259a30`) are ((popularity
÷ 20)² + 10,000) × a byte weight by region × `pwkSup_GetSupporterRand` ÷
10,000, so they grow with the square of popularity. The weight is from
`0x553100` for the home region and an overseas region whose branch byte
`+1` is set, from `0x553110` for one with only byte `+0` set; any other
region has none. The table is flat: the biggest fanbase
sells 12.5 times what the smallest does.

### Making the stock

**Confirmed.** Goods are paid for when they are ordered, not when they
sell. The goods screen (`SIMPRG.REL 0xbcca0`) works out a unit cost of
shop price × 30 ÷ 100 (the `addiu` 30 at `0xbcce4`), and offers 8 lot
sizes, each costing unit cost × lot × a discount ÷ 100; a lot the club
can't pay for (`pwkGen_GetSikin`) is greyed out:

| Lot (`0x1d10b8`) | 1,000 | 2,000 | 3,000 | 5,000 | 10,000 | 20,000 | 50,000 | 100,000 |
|---|---|---|---|---|---|---|---|---|
| Discount % (`0x1d10d8`) | 100 | 95 | 90 | 85 | 80 | 75 | 70 | 60 |

Ordering (`0xbc0b0`) keeps the lot's cost and its stock (the same lot
sizes, `0x1d1090`[choice], 1-based), then pays the cost as payment 22
(`pwkGen_Pay`, `0xbb814`; "Casual income", the misnamed expense, under
Other expenditure) and puts the goods on sale with that stock
(`0x164ec8`: slot `+0x0` id, `+0x4` stock, `+0x8` sold, `+0xc` player).
Item 49 (`0x31`, price 150,000,000) is the exception: one unit at a fifth
of its price (`0xbc418`).

So a unit costs 18–30% of its price, and each one sold brings in its
price × the business cycle (75–125%): margins of 70–82% in an average
cycle, before unsold stock. A £30 shirt (180) costs £9 a unit in a lot
of 1,000 and £5.40 in a lot of 100,000. The levers for dearer stock and
smaller margins are the 30, the discount table and the prices (shop list
`+0x8`).

`patch_disc.py --mod merch-costs` (in `--mod balance` and
`--mod lmaster-full`) makes the 30 50 and halves each discount (rounded
up): 100, 97, 95, 92, 90, 87, 85 and 80. A unit then costs 40–50% of its
price, so margins in an average cycle are 50–60%, and stock that doesn't
sell costs more. The £30 shirt costs £15 a unit in a lot of 1,000 and
£12 in a lot of 100,000. The prices stay.

**Tested in PCSX2** (user report, 2026-10-25, a `--mod lmaster-full`
disc): ordering goods costs half the price a unit, the biggest lot gets
only 20% off, and the margins come out at 50%. The save state of that
career shows `SIMPRG.REL` loaded at `0xc75000` with the new unit cost
(`0xbcce4`) and discount table (`0x1d10d8`), and `--mod fanbase`'s
merchandise bases and TV factors, also in place.

`--mod fanbase` scales the 17 bases from ×3 at the top to ×0.5 at the
bottom, evenly on a log scale: 30,000, 21,457, 16,786, 12,864, 7,667,
6,170, 4,903, 3,836, 2,939, 2,409, 1,958, 1,575, 1,252, 979, 751, 559
and 400, so the biggest fanbase sells 75 times the smallest.

## Transfer fees

**Confirmed.** Every player move starts from one base fee,
`0x247130` (through `pwkMoney_CalcMoveBase`, `0x247a00`, and
`pwkMoney_GetMoveBaseMoney`, `0x248450`): 1,350,000.0 (a float built at
`0x247288`) × a factor by club rank and the player's ability (a table at
`0x398478`, 0x18 bytes a row) × the sum of two more factors × two more,
then held to price kind 1's limits. It is used by

| Caller | What |
|---|---|
| `pwkMoney_CalcuPurchaceOtherTeamPlayerTransferMoney` (`0x248280`) | what you pay another club: the base × 80–100% ÷ 100 |
| `CComOffer::CalcuOfferClub` (`0x225b20`) | what clubs offer for your players |
| `plTeam_IsGenerateAgentEvent` (`0x220790`) | an agent's offer |

`CalcPurchaceOfferTransferMoney` (`0x248180`) then gives an offer × (0.7
+ a random 0 to 0.2 + 0.015 × the club's `+0xa0`). Price kind 1's limits
(the initializer at `0x24a140`, in units of 100;
[`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#salary-limits)) are a minimum
of 1,000, 4,000, 6,000 or 3,000 by currency and a maximum of 7,200,000
(£120M) in all four.

`pwkMoney_CalcPlayerMarketPrice` (`0x247d78`) isn't a transfer fee: it
is the salary a player asks for (its callers are the contract renewal and
the dissatisfaction check), 30,000 × form factors × two tables × 48.

`--mod transfer-fees` (in `--mod balance`) makes the base 2,700,000.0
(the `lui` at `0x247288`) and the maximum 15,000,000, £250M (the four
`lui`/`ori` pairs at `0x24a1c8`–`0x24a21c`), a whole number of every
currency's step. Fees within the old cap double; fees the old cap held
at £120M can now reach £250M.

**Tested in PCSX2** (user report, 2026-10-25, a `--mod lmaster-full`
disc): transfer fees came out doubled. In a save state of that career (slot 1 of the CRC `59D884B2` build, `--mod lmaster-full` without the tutorial skip) the running game holds the
new code and price kind 1's limits as filled in at start-up, `{min,
15,000,000, step}` for all four currencies at `0x5eb098`. Not yet seen: a
fee above the old £120M, and whether the transfer screens have limits of
their own.

## PR events

The Publicity Department's events ("PR activities"; the game calls them
club events, `PlClubEvent`) come from three tables in the executable,
46 events each (**confirmed**): an offer record with the cost and when
the event is offered, a chance record and a success record. Their
fields, the events' names and when each is offered are in
[`CLUBEVENT_FORMAT.md`](CLUBEVENT_FORMAT.md); `clubevent.py` and the mod
editor's PR events tab edit them. This section is what they do to the
money.

**The cost** is `+0x14` × 300: 100 to 10,000 on the disc, so £5,000 to
£500,000. The scheduling screen keeps it (`SIMPRG.REL 0xa3958`) and pays
it as payment 22 when the event is booked (`0xa2a2c`); cancelling refunds
it (`0x45bb4`, `0x49690`, a negative payment 22).

**The chance.** `plClubEvent_Execute` adds to byte 0 (50 for 45 events,
100 for event 45) a business-cycle byte, then byte 7 when the club status
is over 49,999 (`0x20df20`) and byte 6 when `0x20df48` returns true, which
it never does (a stub returning 0). The event succeeds when
`fcEuroRand_Get0toI(100)` is at most that, so the chance is the sum + 1
in 100. Bytes 1–4 hold +20, +10, −5 and −10 for most events (as 20, 10,
251, 246), the changes for cycles 0, 1, 3 and 4 (0 is the boom; cycle 2
adds nothing). But the ladder that picks one (`0x20dfb0`–`0x20e014`)
takes byte 2 for cycles 0 and 1, byte 4 for cycle 2 and byte 3 for 3
and 4: the boom's +20 is never read, and an average economy takes −10,
more than a slump does. The Japanese executable has the same code
(`SLPM_663.16 0x20e7f0`). For a typical event (50, +20, +10, −5, −10):

| Business cycle | 0 (boom) | 1 | 2 | 3 | 4 (slump) |
|---|---|---|---|---|---|
| retail | 61% | 61% | 41% | 46% | 46% |
| `--mod pr-cycle` | 71% | 61% | 51% | 46% | 41% |

That the bytes are meant in that order is **empirical** (byte 1 is
otherwise unread, and the slump's changes are the negative ones), but
which byte the code reads for each cycle is **confirmed**.
`patch_disc.py --mod pr-cycle` (in `--mod lmaster-lite`) rewrites the
ladder's first 11 words to read byte *K* + 1 below cycle 2, nothing at
2 and byte *K* above it; `--mod pr-costs` (in `--mod balance`) makes
the cost `+0x14` × 600 (the `addiu` at `0x20deec`), which doubles the
booking and the refunds alike.

**Success** changes popularity, youth development and supporter
complaints by the success record
([`CLUBEVENT_FORMAT.md`](CLUBEVENT_FORMAT.md#the-success-record-28-bytes-7-s32)),
and its ticket bonus in percent is kept on the event's day of the
calendar (`+0x30` of its 0x48-byte day) for the match that day
([attendance](#a-home-match)). A failed event changes nothing; its cost
is spent.

## Camps and tours

The camp and tour screens (`SIMPRG.REL`, the module set up at `0xa2e60`)
price a booking, keep it at `+0x520` and pay it as payment 21 (Camp
Tour) when it is booked (`0xa2548`, `0xa2690`); cancelling refunds it
(`0xa4d04`, `0xa4df4`). **Confirmed:**

> camp = rate[level][region] × players × 300 × cycle ÷ 100 × (100 − sponsor discount 16) ÷ 100 (`0x4ded8`)
>
> tour = rate[region + 1] × (players ÷ 2) × 300 × cycle ÷ 100 × (100 − sponsor discount 28) ÷ 100 (`0x4e080`)

*players* counts the filled slots of the 25-man squad. A camp's *level*
is its `CAMP_LIST` level (0–7, [`CAMP_FORMAT.md`](CAMP_FORMAT.md)) and
its *region* `plMisc_Nati2DRegion` of the camp's nation; a tour's region
is the one chosen on screen. The rates are u32 tables in `SIMPRG.REL`:

| Table | Values |
|---|---|
| camp, `0x1ce4e8`, 8 levels × 14 regions | level 0: 150–400; level 7: 400–1,000 |
| camp cycle, `0x1ce6a8` | 75, 90, 100, 110, 125 for cycles 0–4 (cheaper in a boom) |
| tour, `0x1ce6c0`, 14 (entry 0 unused) | 1,000, 800, 800, 800, 1,200, 1,200, 600, 600, 600, 1,200, 1,100, 1,000, 800 for regions 0–12 |
| tour cycle, `0x1ce6f8` | 125, 110, 100, 90, 75 (dearer in a boom) |

With 25 players in an average cycle and no discount, a camp costs
£187,500–£1,250,000 and a tour £360,000–£720,000.

**Tour income** (`pwkSche_GetTourIncome`, `0x2566f8`; booked as income
11, Other income, at `SIMPRG.REL 0x134bd0`) is

> (T1[band][region] × 300 + T0[band] × matches) × cycle ÷ 100, halved unless each of the tour's named players (up to 4, `pwkSche_GetTourPlayer`, `0x256630`) is in its matches' entries

where *band* is your popularity in the tour's region against 10
thresholds (`0x399478`: 0, 3,001, 8,001 … 60,001), T1 is 10 × 13 u32 at
`0x399258` (25,200–36,500 in band 0 up to 67,900–101,300 in band 9), T0
10 u32 at `0x399230` (1,000–20,000) and the cycle 125–75 at `0x399460`.
So a tour earns about £1.2M–£6.3M against its cost of under £1M, and is
always a profit. `pwkSche_CheckTourSucucess` (`0x256a20`) rates the
income against 1,500,000 and 30,000,000 (£250,000 and £5M) for the
tour's report.

`--mod camp-costs` doubles the camp rates and `--mod tour-costs` triples
the tour rates (both in `--mod balance`), so camps cost £375,000–£2.5M
and tours £1.1M–£2.2M; a tour where the club is little known then about
breaks even. Tour income is unchanged.

## Still unknown

- What the business cycle changes besides build costs, and its random
  patterns.
- The cost of kind 1 (stands) in full, and what the window calls the
  `+0x1c` cost of kinds 3, 8, 14 and 15.
- Which sponsor category `0x1563e8` gives each kind and slot.
- *k* in the attendance formula, and what the turn-up rate's four tables
  are indexed by.
- Plan `+0x16` (7,000 in every save).
- The shop list's other fields (`+0x2`, `+0x4`, `+0x5`), what the trend
  table's rows are, and when goods that stop selling leave the shop.
- The transfer fee's rank and ability factor and its three others, and
  what the club byte `+0xa0` in an offer is.
- What the PR events' byte 6 bonus was for (`0x20df48` is a stub), and
  how often a tour's hosts ask for players.
- Which sponsors a club is offered, and what `+0x18` is for (suppliers?).
- What a TV contract's term adds (G000's 4-year contracts are 15% over
  the formula), how often `Pwk.CheckTV` pays, and what each station
  record's fields mean.

## Checking

```bash
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 153c28 160 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 154b78 240 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 3eda0 230 --sles ISO/SLES_541.51
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkUnkei_GetTicketHosei pwkUnkei_GetAllAudience pwkUnkei_GetExpectSeat
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkTeam_ChangePop_Month pwkTeam_PopChange
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 1690a0 60 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 163a10 90 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 165dc0 240 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 165598 30 --sles ISO/SLES_541.51
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkTeam_Supporter pwkMoney_CalcuPurchaceOtherTeamPlayerTransferMoney
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x247130 160
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x24a140 110
python SRC/sles_disasm.py ISO/SLES_541.51 dis plClubEvent_Execute pwkSche_GetTourIncome
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 4ded8 110 --sles ISO/SLES_541.51
python SRC/save.py finances <save>
```
