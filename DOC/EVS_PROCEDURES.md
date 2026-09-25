# Event procedures (type-4 events)

Besides the EVENT, MAIL and NEWS records in the `EvsDataBin` tables (see
[`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md)), the event system runs
**procedures**: multi-step processes that exist only in code. They are the
scouting, transfer and loan processes. A procedure is requested like any
other event, with the ID `0x04000000 | index`, and has no table record. Each
step sends mail from `EvsDataBin_MAIL.bin` and can schedule the next step.

All addresses are in `SIMPRG.REL` unless noted. The structure is
**confirmed** from the code. What each procedure is *about* is
**empirical**, read from the MAIL records it registers (English text,
`python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_MAIL.BIN mail.csv --text DAT/MESSAGE/MES.PAC`).

## Requests

An event request is a struct the event manager queues:

| Offset | Type | Set by | Meaning |
|---|---|---|---|
| `0x00` | u32 | caller | event ID, `type << 24 \| index` |
| `0x04` | s32 | `0x12c058` | −1 |
| `0x08` | s32 | `0x12c058`, `0x12c160` | due time: −1, or `0x12e5a8()` + a delay |
| `0x0C` | s16 | `0x12c058`, `0x12c160` | −1, or a value the caller gives (4 in every procedure step) |
| `0x0E` | u8 | `0x12c058` | 100 (probably the weight, like the tables' default) |
| `0x0F` | u8 | `0x12c058` | second argument of `0x12c058` |
| `0x10`–`0x2F` | 32 bytes | caller | arguments (zeroed by `0x12c058`) |

| Address | What it does |
|---|---|
| `0x12c058(req, b)` | initialise a request (fields above) |
| `0x12c160(req, delay, x)` | due time = −1 if `delay` is −1, else `0x12e5a8() + delay`; `+0x0C` = `x` |
| `0x12b490(manager, req)` | submit (calls `0x12ba60`) |
| `0x12ba38(manager, req, …)` | submit, used when an EVENT chains another (`0x12a518`) |
| `0x12b580` | dispatch by type byte (jump table `0x238860`): 1 EVENT, 2 MAIL, 3 NEWS, 4 procedure |
| `0x12caf0` | build the procedure object: `(ID & 0xffffff) − 9` into the jump table `0x238970`, so indexes 9–29 |

`0x12e5a8` is the event clock; its unit isn't traced. A procedure sends a mail with
`0x124f50(this, 0x02000000 | record, n)`, which fetches the MAIL record
(getter `0x128e78`) and fills in the procedure's message fields.

## The procedures

| # | Code | MAIL it sends | Started by | Next |
|---|---|---|---|---|
| 9 | `0x126208` | 295–297, 370–372, 412, 415 "Player search report" | `0x9e7d0` (calls `Param::pwkTeam_SetScoutModeNot`) | 10 or 12 |
| 10 | `0x126540` | 298–305, 373, 374, 416, 420 "Player acquisition to cancel" | 9 | 11 |
| 11 | `0x1268a0` | 306–310 ("Player negotiation report", ...), 421 | 10 | |
| 12 | `0x126a50` | 300, 305, 398–400 ("Negotiating players", ...), 409 | 9 | 13 |
| 13 | `0x126cd0` | 401, 402, 422, 423 | 12 | |
| 14 | `0x126e30` | 317–319 ("Player acquisition report", ...), 403, 404, 410 | `0x6b5f8`, kind 0 | 15 |
| 15 | `0x1270a0` | 405 "Player acquisition report" | 14 | |
| 16 | `0x127198` | 323–325, 406, 407, 411 | `0x6b5f8`, kind 1 | 17 |
| 17 | `0x127458` | 408 "Player acquisition report" | 16 | |
| 18 | `0x127550` | 352, 443 "Contract withdrawal (Youth)" | `0x6b5f8`, kind 2 | |
| 19 | `0x127688` | 353 "Permanent Move Offer", 354, 386, 387 | the Event module's check (below) | 20 |
| 20 | `0x127948` | 337–343 ("Cancel Player Transfer", ...), 388, 389, 424, 442 | 19 | 21 |
| 21 | `0x127cf0` | 339, 340, 344–348, 425, 442 | 20 | |
| 22 | `0x127ef8` | one of 314–316, 349–351, 334–336, 331–333, from a table (below) | `0x74418`, a scout request | itself |
| 23 | `0x1281d0` | 363 "About players on a loan", 396, 397 | the Event module's check | 24 |
| 24 | `0x128328` | 364 "Report to sell loaning player" | 23 | |
| 25 | `0x128440` | 359 "About Loaning player", 392, 393 | the Event module's check | 26 |
| 26 | `0x128570` | 360 "Report to buy loaning player", 361, 394, 395 | 25 | 27 |
| 27 | `0x128710` | 362 "Loaning player negotiation" | 26 | |
| 28 | `0x128850` | 329 "Transfer negotiation", 330, 441 "Cancel Player Transfer" | `0x50e88`, a player-list screen (`0x12c058` argument 21) | |
| 29 | `0x1289b0` | 356 "Contacting other club players" | the Event module's check | |

"Code" is the constructor. The MAIL column lists every MAIL ID built as a
constant in the class's code, from its constructor up to the next one, so
it covers the methods as well (only the constructor's own registration
is certain to be that class's; the rest is by address). Each procedure
sends one of them at a time, depending on how the step turns out.

Every "Next" step is queued with `0x12c160(req, 1, 4)`: one clock unit
later. The "Next" column lists the sites that build each ID; which
procedure owns a site is by address (a class's methods follow its
constructor), except where a vtable ties it down (27: vtable `0x20a878`).

So the processes are:

- **Scouting (9–13).** A search report, then negotiations that end in a
  signing or a cancellation.
- **Signing a player (14–18).** Started from the negotiation code at
  `0x6b5f8`, which picks the procedure from a byte at `+0x21c` of its
  object: 0 → 14, 1 → 16, 2 → 18. 14 and 18 also call
  `Param::Set_aaNegoPlayerNo`, with 0 and 1 as its second argument. From the mail text, 0 is a
  player at another club, 1 a free agent ("the currently unaffiliated…")
  and 2 a youth player.
- **Offers for your players (19–21).** Another club's offer, then the
  transfer or its cancellation.
- **Loans (23–27).** 23–24: an offer for a player you've loaned out. 25–27:
  a player on loan to you, whose club offers to sell him, ending in a
  negotiation.
- **Contract approaches (29).** Another club approaches one of your players
  whose contract is ending.
- **Scout lists (22)** and **loaning out (28)**: see the next two
  sections.

### Scout lists (procedure 22)

A scout compiles a candidate list you asked for. The request comes from
`0x74418`, which checks `Param::pwkTeam_CheckScoutAcceptRequest`, sets
`pwkTeam_SetScoutModeNot` and passes the search terms. The procedure finds
the scout (`pwkTeam_GetScouts`, 3 slots of 0x94 bytes, matched on `+0x60`)
and switches on the list type at `+0x158`: 0 players, 1 youth, 2 coaches,
3 managers. For each type it copies fields of its block at `+0x1c` into a
"term" struct and calls the matching `Param` function.

**Player lists (confirmed).** `pwkTeam_UpdatePlayerCandidates(PlPlistTerm*,
int*)` (`SLES_541.51 0x260768`):

| Block | Term | Search criterion |
|---|---|---|
| | `+0x00` | the scout (`PlSinfo*`) |
| `+0x04` (s16) | `+0x04` | country: when non-zero, only clubs whose `plMisc_Club2Nati` equals it |
| `+0x06` (s16) | `+0x08` | region (`PlDRegion`, see [Regions](#regions)), used when no country is set (`plMisc_Nati2DRegion`) |
| `+0x0a` (s8) | `+0x0c` | age bracket, if non-zero (`0x25f8a0`): 1 under 23, 2 23–29, 3 30 and over, 4 under 19, tested on the candidate's byte `+0x08` (the thresholds make it the age) |
| `+0x08` (s16) | `+0x10` | position, if non-zero (`0x25fa08`, 12 cases, `plMisc_Apos2Pos` / `Apos2Epos`): 1 GK, 2 FB or CB, 3 FB, 4 CB, 5 WB/DM/SM/AM, 6 WB, 7 DM, 8 SM, 9 AM, 10 W or FW, 11 W, 12 FW (590:601–612) |
| `+0x0b` (s8) | `+0x14` | 1: EU clubs only (`plMisc_Club2EU`) |
| `+0x0c` (s8) | `+0x18` | loan option: 1 lists only players `0x260590` finds available for loan (590:701 "List players available for loan"); 2 (not offered on the screen) lists only those it doesn't |
| `+0x14` (s32) | `+0x20` | budget, if positive: drop candidates whose `pwkMoney_GetMoveResearchMoney` is higher |
| `+0x12` (s16) | `+0x28` | scout special condition 0–35 (590:500–535, e.g. 515 "goalkeepers with a safe pair of hands"); 36 is 590:536 "Do not set any special conditions". Index into 40-byte entries at `0x553e58`: a play style matched against the candidate's 5 style bytes at `+0x1f6`, and a skill tested with `plPinfo_IsSkill` |

Every search also drops players under an exclusive or semi-exclusive deal
(`plSinfo_CheckExclusive` / `CheckSemiExclusive`), players who need a
higher club status than yours (candidate `+0x1cc` against
`pwkTeam_Status`), players already in the discovered list
(`pwkDis_IsPlayer`; new candidates go in with `pwkDis_AddPlayer`) and
players with bit `0x40` set at `+0x20c`. The age and position checks end
in a random roll against one of the scout's skill bytes (`+0x35`–`+0x38`
for the four age brackets; `+0x39`, `+0x3c`, … by position), and the scout
also has a byte per country (`+0x4a` + country) and per region (`+0x51` +
region) that the search reads. So a better scout finds more. `0x260590` combines the month, a byte of the
candidate's club (`+0x9a`), the candidate's value at `+0x1b0`, float tables
at `0x553648`–`0x553688` and `plTeam_GetPositionEnhancementLevel` for that
club. What it decides isn't traced.

The function returns 0 when it adds no candidate, 1 when it adds some, and
2 when the best added candidate's `+0x1b0` is 11 or more. The procedure
indexes two byte tables with that value (`0x238318` = 0, 1, 1, …;
`0x238320` = 0, 0, 1, …) to pick a mail from its row of the table at
`0x238690`:

| Result | Mail (player list) |
|---|---|
| 0 | 316 "About Player list": nobody met the requirements |
| 1 | 314 "Player List now available" |
| 2 | 315 "Player List now available" with "There are some great players…" |

The option texts are in message category 590, the request screen ("Make
Player List", "Youth Player List", "Manager List", "Coach List"). The age
options there are 550 none, 551 16–22, 552 23–29 and 553 over 30, matching
values 0–3; value 4 (under 19) isn't offered for players.

**Youth lists (confirmed).** `pwkTeam_UpdateYouthCandidates(PlYlistTerm*,
int*)` (`0x262c40`) tests the player's own nationality (`getPbase` field
`+0x14`), not his club's:

| Block | Term | Search criterion |
|---|---|---|
| `+0x04` | `+0x04` | country |
| `+0x06` | `+0x08` | region |
| `+0x08` | `+0x0c` | position, if non-zero (`0x2623e8`, the same 12 positions) |
| `+0x12` | `+0x10` | scout special condition, 36 = any (as for players) |

**Coach lists (confirmed).** `pwkTeam_UpdateCoachCandidates(PlClistTerm*,
int*)` (`0x261d10`) walks 3,000 staff records (`getMbase`, ids from
`0x6d2e`) and tests the coach's nationality (field `+0x14`):

| Block | Term | Search criterion |
|---|---|---|
| `+0x04` | `+0x04` | country |
| `+0x06` | `+0x08` | region (scout byte `+0x50` + region) |
| `+0x0f` | `+0x0c` | coach type (590:900–903): allowed if the byte table at `0x553860` has a 1 at `type × 7 + kind`, where kind is the coach's byte `+0x1c`. 0 none (kinds 0–4), 1 assistant coaches (kinds 0–2), 2 fitness coaches (kind 3), 3 goalkeeping coaches (kind 4) |
| `+0x0a` | `+0x10` | instruction age (590:950–954), if non-zero: the coach's byte `0x66` + (7, 8, 9, 6)[value − 1], from the table at `0x399600`, must be at least 70 |
| `+0x14` | `+0x18` | salary limit (590:164), if positive: compared with `0x260fc0(coach +0x18, 7)` |

**Manager lists (confirmed).** `pwkTeam_UpdateManagerCandidates(PlMlistTerm*,
int*)` (`0x261500`), over the same 3,000 staff records:

| Block | Term | Search criterion |
|---|---|---|
| `+0x04` | `+0x04` | country |
| `+0x06` | `+0x08` | region |
| `+0x0d` | `+0x0c` | tactical approach (590:152): `0x260f08` looks up `value × 25 + style` in the byte table at `0x5536b0`, where style is the manager's byte `+0x34` (0–24), then rolls against the scout's byte `+0x46` |
| `+0x0e` | `+0x10` | favoured tactics 1–6 (590:751–756: quick break, possession, wing attack, centre, offside trap, pressurise): the manager's byte `+0x8c` + value must be at least 70 |
| `+0x10` | `+0x14` | formation 1–8 (590:801–808: 3-4-3, 3-5-2, 3-6-1, 4-3-3, 4-4-2, 4-5-1, 5-3-2, 5-4-1): byte `+0x84` + value must be at least 70 |
| `+0x0a` | `+0x18` | instruction age (590:850–854), as for coaches (table `0x3995f0`, the same 7, 8, 9, 6) |
| `+0x14` | `+0x20` | salary limit (590:156) |

Which of block `+0x0e` and `+0x10` is tactics and which is formation is
taken from the screen order (Team Policy, Preferred Tactics, Preferred
System, then age and salary, 590:6–10), not from the code. Both readings
give byte ranges that don't overlap.

So a manager's record holds a style at `+0x34`, formation ratings at
`+0x85`–`+0x8c`, tactic ratings at `+0x8d`–`+0x92` and age ratings at
`+0x6c`–`+0x6f`, and 70 is the "good at it" threshold. Which age byte
belongs to which option isn't settled. If the values follow the player
search (1 16–22, 2 23–29, 3 over 30, 4 youth), youth is `+0x6c` and the
three age groups are `+0x6d`–`+0x6f` in order.

The tactical-approach table's first rows are masks over the 25 styles laid
out as a 5 × 5 grid (style = 5 × row + column): 0 accepts all, 1 the top
two rows and the centre, 2 the bottom two rows and the centre, 3 the left
two columns and the centre, 4 the right two columns and the centre. The
approaches on the team-style screen (category 420) are 200 Counter-Attack,
201 Possession, 202 Individual Play and 203 Teamwork. 103–106 pair them
as quick/slow build-up and playmaker/whole team, which fits two axes.
That 1–4 follow that order is an assumption.

**The search repeats.** The procedure copies its own request (`0x12bff0`)
and submits it again after `0x12efb0(region)`. That clamps the region to
0–12 and reads a delay from the byte table at `0x238ee0`: 4, 4, 4, 4, 6, 6,
5, 5, 5, 6, 6, 5, 6. If the club has an overseas branch in the region
(`pwkTown_GetPlOverseasBranchPointer`, byte `+1` set), the delay is 4.

### Loaning out (procedure 28)

You offer one of your players on loan. Two checks decide the result, both
`Param::pwkTeam_GetEmptyNumber(kind) > 0` (`SLES_541.51 0x266b38`), which
returns how many more players fit before a limit, floored at 0:

| Check | Kind | `GetEmptyNumber` returns | If 0 |
|---|---|---|---|
| `0x15e870` | 0 | squad members − 8 (which members count depends on the transfer-market phase, `plMisc_TransferMarketSchedule`) | mail 441: the squad would drop below 8 |
| `0x15e890` | 2 | 5 − a count of members by kind, depending on the phase (jump table `0x5546c0`) | mail 330: at most five players can be out on loan |

Otherwise it calls `pwkTeam_AddReleaseList(player, 5, …)` and sends 329
"the release… on loan transfer… has been approved". The other kinds are
1 (24 − `pwkTeam_GetMemberNumber(8)`, a squad of at most 24) and 3 (5 −
another loan count, table `0x5546e0`).

### Where the automatic ones start

The Event module (module 14) checks for offers and loans itself. Its object
(constructor `0x6a00`, created by `pSetupEventModule`) calls `0x129e98`,
which calls:

| Function | Requests | Using |
|---|---|---|
| `0x12c878` | 19 | `Param::plTeam_GetComClubOfferNum` / `plTeam_GetComClubOfferDataPointer` |
| `0x12c878` | 29 | `Param::PlTeam_GetSpecialComOfferNum` / `plTeam_GetSpecialComClubOfferDataPointer` |
| `0x129568` | 23 | `Param::plTeam_GetPurchaceOfferPlayer`, `pwkMoney_CalcuPurchaceOtherTeamPlayerTransferMoney` |
| `0x129568` | 25 | `Param::pwkTeam_GetMyTeamData`, `plPinfo_IsHired` |

So the offers themselves are decided in the `Param` simulation code, and
the procedures only turn them into mail and follow-up steps.

### Talks

Procedures 10–17 (by the position of the call sites of the helper
`0x1258e8`) and 27 (`0x128790`, a method in its vtable) call
`jmTalk_SetTalkType(1)`, the Move talk: the face-to-face transfer
negotiation (see [`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md#scene-types)).

## Regions

`PlDRegion` has 13 values, named by message `1:(310 + region)`. The report
layout (`WP::CReport`, `SIMPRG.REL 0x99130`) and the region list
(`0xbee14`) both add `0x136` to the region. The scout-search repeat delay
from the table at `0x238ee0` is shown with each:

| Region | Name | Delay |
|---|---|---|
| 0 | Western Europe | 4 |
| 1 | Central Europe | 4 |
| 2 | Eastern Europe | 4 |
| 3 | Northern Europe | 4 |
| 4 | South America A | 6 |
| 5 | South America B | 6 |
| 6 | North Africa | 5 |
| 7 | West Africa | 5 |
| 8 | East and South Africa | 5 |
| 9 | North Central America, Caribbean | 6 |
| 10 | East Asia | 6 |
| 11 | South Asia and Middle East | 5 |
| 12 | Oceania | 6 |

Messages 1:300–305 name the six continents.

## For editing

The procedures' logic and triggers are code, so a data mod can change only
their mail text (the MAIL records in the table above), not when they
happen. The offers they react to come from `Param` code.

## Open questions

- The unit of the event clock `0x12e5a8`, and so how long "one step later"
  is.
- What `+0x0C` (always 4 for procedure steps) and the `0x12c058` argument
  (1, 6, 7, 8, 21) mean.
- How `0x260590` decides that a player is available for loan.
- Which instruction-age byte is which, which tactical approach is which
  grid half, and what the manager styles (`+0x34`) and coach kinds 5 and 6
  are.
- Which screens own the start functions for 9 (`0x9e7d0`), 14/16/18
  (`0x6b5f8`), 22 and 28. They're `WS::CPlateWindow` dialogs created through
  tables, so the usual symbol and caller searches don't name them.
- How the scouting procedure 9 chooses between 10 and 12.
