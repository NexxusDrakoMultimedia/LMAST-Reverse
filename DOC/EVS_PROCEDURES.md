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

`0x12e5a8` is the event clock; its unit isn't traced. Each procedure's
constructor registers the MAIL records it sends through
`0x124f50(this, 0x02000000 | record, …)`.

## The procedures

| # | Constructor | MAIL registered | Started by | Next |
|---|---|---|---|---|
| 9 | `0x126208` | 415 "Player search report" | `0x9e7d0` (calls `Param::pwkTeam_SetScoutModeNot`) | 10 or 12 |
| 10 | `0x126540` | 420 "Player acquisition to cancel" | 9 | 11 |
| 11 | `0x1268a0` | 421 "Player acquisition to cancel", 308 "Player negotiation report" | 10 | |
| 12 | `0x126a50` | 400 "Negotiating players" | 9 | 13 |
| 13 | `0x126cd0` | 422, 423 "Player acquisition to cancel" | 12 | |
| 14 | `0x126e30` | 319 "Player acquisition report" | `0x6b5f8`, kind 0 | 15 |
| 15 | `0x1270a0` | 405 "Player acquisition report" | 14 | |
| 16 | `0x127198` | 406 "Player acquisition report" | `0x6b5f8`, kind 1 | 17 |
| 17 | `0x127458` | 408 "Player acquisition report" | 16 | |
| 18 | `0x127550` | 443 "Contract withdrawal (Youth)" | `0x6b5f8`, kind 2 | |
| 19 | `0x127688` | 353 "Permanent Move Offer" | the Event module's check (below) | 20 |
| 20 | `0x127948` | 340, 424 "Cancel Player Transfer" | 19 | 21 |
| 21 | `0x127cf0` | 340, 425 "Cancel Player Transfer" | 20 | |
| 22 | `0x127ef8` | none | `0x74418` (mail-screen code) | |
| 23 | `0x1281d0` | 363 "About players on a loan" | the Event module's check | 24 |
| 24 | `0x128328` | 364 "Report to sell loaning player" | 23 | |
| 25 | `0x128440` | 359 "About Loaning player" | the Event module's check | 26 |
| 26 | `0x128570` | 360 "Report to buy loaning player" | 25 | 27 |
| 27 | `0x128710` | 362 "Loaning player negotiation" | 26 | |
| 28 | `0x128850` | none | `0x50e88` (club-edit code), `0x12c058` argument 21 | |
| 29 | `0x1289b0` | 356 "Contacting other club players" | the Event module's check | |

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
- What procedures 22 and 28 do. They register no mail. 22 starts from the
  mail screen's code (`0x74418`) and 28 from club-edit code (`0x50e88`).
- Which screens own the start functions for 9 (`0x9e7d0`), 14/16/18
  (`0x6b5f8`), 22 and 28. They're `WS::CPlateWindow` dialogs created through
  tables, so the usual symbol and caller searches don't name them.
- How the scouting procedure 9 chooses between 10 and 12.
