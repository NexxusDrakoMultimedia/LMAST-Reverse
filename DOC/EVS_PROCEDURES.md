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
- **Scout lists (22).** A scout compiles a candidate list you asked for.
  The request comes from `0x74418`, which checks
  `Param::pwkTeam_CheckScoutAcceptRequest`, sets
  `pwkTeam_SetScoutModeNot` and passes the search terms. The procedure reads them as halfwords at
  `+0x04`, `+0x06`, `+0x08` and `+0x12` of its block at `+0x1c`. The procedure finds the
  scout (`pwkTeam_GetScouts`, 3 slots of 0x94 bytes, matched on `+0x60`),
  then calls `pwkTeam_UpdatePlayerCandidates`, `…YouthCandidates`,
  `…CoachCandidates` or `…ManagerCandidates` for the list type at
  `+0x158`. It sends a mail from the table at `0x238690` (three halfwords
  per list type: players 314–316, youth 349–351, coaches 334–336, managers
  331–333): "…List now available" (two versions, one adding "There are
  some great players…") or "About … list" when nobody met the
  requirements. The choice goes through two byte tables (`0x238318`,
  `0x238320`). Then it copies its own request (`0x12bff0`), takes a delay
  from `0x12efb0(+0x06)` and submits it again, so the search repeats.
- **Loaning out (28).** You offer one of your players on loan. Two checks
  (`0x15e870`, `0x15e890`) pick the result: 441 (the squad would drop
  below the minimum), 330 (no more than five players can be out on loan
  at once), or 329 "the release… on loan transfer… has been approved"
  with `Param::pwkTeam_AddReleaseList`.

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
- Which of 28's two checks (`0x15e870`, `0x15e890`) is the squad minimum and
  which the five-loan limit.
- What the search terms in procedure 22's arguments are, and how the byte
  tables at `0x238318`/`0x238320` pick between its three mails.
- Which screens own the start functions for 9 (`0x9e7d0`), 14/16/18
  (`0x6b5f8`), 22 and 28. They're `WS::CPlateWindow` dialogs created through
  tables, so the usual symbol and caller searches don't name them.
- How the scouting procedure 9 chooses between 10 and 12.
