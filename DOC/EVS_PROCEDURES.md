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
| `+0x06` (s16) | `+0x08` | region (`PlDRegion`), used when no country is set (`plMisc_Nati2DRegion`) |
| `+0x0a` (s8) | `+0x0c` | age bracket, if non-zero (`0x25f8a0`): 1 under 23, 2 23–29, 3 30 and over, 4 under 19, tested on the candidate's byte `+0x08` (the thresholds make it the age) |
| `+0x08` (s16) | `+0x10` | position, if non-zero (`0x25fa08`, 12 cases, `plMisc_Apos2Pos` / `Apos2Epos`) |
| `+0x0b` (s8) | `+0x14` | 1: EU clubs only (`plMisc_Club2EU`) |
| `+0x0c` (s8) | `+0x18` | 0 anyone, 1 or 2: keep only candidates for which `0x260590` is true / false |
| `+0x14` (s32) | `+0x20` | budget, if positive: drop candidates whose `pwkMoney_GetMoveResearchMoney` is higher |
| `+0x12` (s16) | `+0x28` | player type: index into 40-byte entries at `0x553e58` (a play style matched against the candidate's 5 style bytes at `+0x1f6`, and a skill tested with `plPinfo_IsSkill`). 36 means any |

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

The youth, coach and manager lists use `PlYlistTerm`, `PlClistTerm` and
`PlMlistTerm` and the mail
rows 349–351, 334–336 and 331–333. Each copies its own fields of the
block: youth `+0x04`, `+0x06`, `+0x08`, `+0x12`; coaches `+0x04`, `+0x06`,
`+0x0a`, `+0x0f`, `+0x14`; managers `+0x04`, `+0x06`, `+0x0a`, `+0x0d`,
`+0x0e`, `+0x10`, `+0x14`. Their criteria aren't traced.

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

## For editing

The procedures' logic and triggers are code, so a data mod can change only
their mail text (the MAIL records in the table above), not when they
happen. The offers they react to come from `Param` code.

## Open questions

- The unit of the event clock `0x12e5a8`, and so how long "one step later"
  is.
- What `+0x0C` (always 4 for procedure steps) and the `0x12c058` argument
  (1, 6, 7, 8, 21) mean.
- What `0x260590` decides (the player search's term `+0x18`), the
  criteria of the youth, coach and manager searches, and the names of the
  13 regions.
- Which screens own the start functions for 9 (`0x9e7d0`), 14/16/18
  (`0x6b5f8`), 22 and 28. They're `WS::CPlateWindow` dialogs created through
  tables, so the usual symbol and caller searches don't name them.
- How the scouting procedure 9 chooses between 10 and 12.
