# `EvsDataBin_*.bin` event tables

`DAT/EVENT/EVSDATABIN_{EVENT,NEWS,MAIL}.BIN` drive the club-management
events: scripted office/locker/meeting scenes (EVENT), newspaper items
(NEWS) and inbox mail (MAIL). They replaced the string-based
[EVENTDATA_TURN.TBB](EVENTDATA_TURN.md) prototype. All three are
headerless arrays of fixed-size little-endian records, loaded whole by
`DLL/SIMPRG.REL`.

| File | Record size | Records | Getter (SIMPRG) | `EvsWork` slot | ID type byte |
|---|---|---|---|---|---|
| `EVSDATABIN_EVENT.BIN` | 272 (`0x110`) | 382 | `0x12e000` | `+0x0` | 1 |
| `EVSDATABIN_NEWS.BIN`  | 192 (`0xc0`)  | 368 | `0x12c458` | `+0x4` | 3 |
| `EVSDATABIN_MAIL.BIN`  | 112 (`0x70`)  | 444 | `0x128e78` | `+0x8` | 2 |

Addresses below are `SIMPRG.REL` file offsets (the overlay is linked at 0).
`python SRC/snr2.py dis ISO/DLL/SIMPRG.REL <addr> <n> --sles ISO/SLES_541.51`
shows them with imports resolved.

## Common rules (confirmed in code)

- **Loading.** `0x1291d8` opens the three files with
  `CDataHandle::OpenReq` (`"EvsDataBin_EVENT.bin"` etc. at `0x238730`) and
  stores the data pointers in the global `EVS::EvsWork` at `+0x0`
  (EVENT), `+0x4` (NEWS) and `+0x8` (MAIL).
- **IDs.** An event ID is `type << 24 | index`. `0x12e8f8`/`0x12e908`/`0x12e918`
  test `id >> 24 == 1/2/3`. `0x12dff0` builds `index | 0x01000000`.
  `EVS::GetEventName` just formats the full ID with `"%08x"`.
- **Getters.** Each getter masks the ID to 24 bits and clamps it with
  `0x12e1e0`: negative or `>= count` becomes 0. Then it returns
  `EvsWork[slot] + index * size`. The clamp limits (`0x17e`, `0x170`,
  `0x1bc`) equal the file record counts.
- **Record 0** is all zeros in every file. It's the null record that
  out-of-range IDs fall back to.
- **`+0x00`** of every record is its own index (true for all records in
  all three files).
- **Message references.** Text is referenced by a u32
  `category << 16 | id` into `MESSAGE/MES.PAC` (see
  [`MBB_FORMAT.md`](MBB_FORMAT.md)). Every non-zero reference in all three
  files resolves to an existing message.
- **Weight.** `0x12b0b8` returns the "weight" of any event by type:
  EVENT `+0x6c`, MAIL `+0x5c`, NEWS `+0x78`, default 100.

## EVENT record (272 bytes)

Field names come from how `SIMPRG.REL` uses each field. **Confirmed**
means read in code with a clear meaning; **data** means inferred from
the value distribution only.

### Identity and presentation

| Offset | Type | Field | Evidence | Values |
|---|---|---|---|---|
| `0x00` | u32 | index | data (all rows) | = record index |
| `0x04` | u32 | always-eligible key | confirmed | if every condition field below is 0, the event is eligible only when this is non-zero. 0–116 |
| `0x08` | u32 | handler type | confirmed: `0x12d7d8` switches on it (80 cases), each case allocates a different handler object | 0–78 |
| `0x0c` | u32 | ? | data | 0–9 (3 ×182) |
| `0x10` | u32 | speaker/actor class | confirmed: indexes a 90-entry flag table at `0x23a3c8` (via `0x139718`) that picks the scene-type override | 0–89 |
| `0x18` | u32 | second actor? | confirmed: indexes the flag table at `0x23a428` (same call) | 0–123 |
| `0x1c` | u32 | ? | data | 0–18 |
| `0x24`–`0x5c` | 5 × {u32, u32, u32} | ? | data | five groups at `0x24`/`0x30`/`0x3c`/`0x48`/`0x54`: (0–322, {0,2,46,47}, 0 or ~2000/3000/4000) |
| `0x64` | u32 | dialogue (message ref) | confirmed: `0x1393d0` fetches the record with the EVENT getter, copies it to the stack and stores `+0x64` in the scene object at `+0x44` (unless the object's `+0x48` overrides it) | id is always 0; category 35000–36030 in 373 records, 0 in 8 (256, 311–315, 359, 361). The whole category is the scene's script |
| `0xe0` | u32 | scene type | confirmed: `0x12a578` returns it; `0x12a690` switches on it (29 cases) to set `jmTalk_SetTalkType` | 0–28 |
| `0xe8`, `0xec` | u32 | scene type override A/B | confirmed: used instead of `0xe0` when the actor flag has bit `0x02`, picked by `EvsWork+0x1f8 == 1` | |
| `0xf0`–`0x104` | 6 × u32 | scene type by variant | confirmed: used when the actor flag has bits `0x1c`, indexed by `EvsWork+0x1fc` (0–5) | |

### Trigger conditions: `CheckCondition` at `0x12d530`

Checked in this order; any failure means the event can't fire.

| Offset | Type | Field | Check |
|---|---|---|---|
| `0x68` | s32 | timing | must equal the timing the scan runs for (`0x12df08`'s 2nd arg). −1 never matches. Enum names not yet traced (0–21) |
| `0x7c` | u32 | earliest season | 0 = any, else `year − 2005 >= value` (`0x12e3b8`) |
| `0x80` | u32 | season pattern | 0 = any, else `pattern[value][year − 2005]` (`0x12e3e0`) |
| `0x84` | u32 | date pattern A | 0 = any, else `pattern[value][date[3]]` (`0x12e450`) |
| `0x88` | u32 | date pattern B | 0 = any, else `pattern[value][(date[2] & 7) + 1]` (`0x12e4b0`) |
| `0x70` | u32 | once only | non-zero: fails if the event's runtime slot shows it has fired (`0x12e220`) |
| `0x78` | u32 | cooldown class | 0 = none; 1–9 = minimum gap since last firing. Most classes are 8/24/48/96/288/480 turns; class 1 compares dates (`0x12e220`, jump table `0x238ba0`) |
| `0x8c`, `0x90` | u32, u32 | condition 1 (kind, arg) | `0x123898(kind, arg)`: switch over 170 kinds |
| `0x94`, `0x98` | u32, u32 | condition 2 (kind, arg) | same |
| `0x9c` | u32 | required flag 1 | `IsEventFlag`: 0 = none, else flag byte must be set |
| `0xa0` | u32 | required flag 2 | same |
| `0x74` | u32 | forbidden flag | `0x1243c0`: 0 = none, else flag byte must be clear (checked twice) |
| `0xa8`, `0xa4` | s32, u32 | extra date rule | skipped when `0xa8 < 0` or `0xa4 == 0`, else `0x13c1d0(date, …)` must return 0 |
| `0xb0` | u32 | chance % | `rand(0..99) < value`. 100 in 282 records |

The pattern table is signed bytes at `0x1d88a0`, 48 rows × 21 columns.
The date struct passed in starts with a u16 year (2005 = season 0).

### On firing: `0x12d758`

| Offset | Type | Field | Action |
|---|---|---|---|
| `0xd8` | u32 | flag to set | `SetEventFlag(value)` if non-zero |
| `0xb4`, `0xb8` | u32, s32 | effect 1 (kind, value) | `0x1213d0(kind, value)`: switch over 20 kinds |
| `0xbc`, `0xc0` | | effect 2 | same |
| `0xc4`, `0xc8` | | effect 3 | same |
| `0xcc`, `0xd0` | | effect 4 | same |
| `0x08` | u32 | handler type | then selects the handler (see above) |

### Effect kinds: `0x1213d0`

A jump table at `0x237d30` sends each kind (0–19) to its own handler at
`0x1210c0`–`0x1213c8`, called as `(kind, value)`. Kinds ≥ 20 do nothing.
Money values are in units of **10,000** (the handler multiplies by
`0x2710`), so `600` means 6,000,000.

| Kind | Handler | Effect | Used by (event: value) |
|---|---|---|---|
| 0 | `0x1210c0` | nothing | |
| 1 | `0x1210c8` | income: `pwkGen_Income(value × 10000, PlIncomeType 11)`; skipped if value < 0 | 257: 900, 260: 300 |
| 2 | `0x1210f8` | expense: `pwkGen_Pay(value × 10000, PlPaymentType 22)`; skipped if value < 0 | 166…189 (stadium, handler 33): 600/1500/3000; 255: 300 |
| 3 | `0x121128` | popularity +value in region 0 (`pwkTeam_ChangePopByRegion(0, value)`) | 102, 103, 199, 262, 263, 308 |
| 4 | `0x121148` | popularity +value in regions 1–13 | 102, 103, 199, 308 |
| 5 | `0x121198` | popularity −value in region 0 | 242–254 (handler 6): 500 / 10 |
| 6 | `0x1211b8` | popularity −value in regions 1–13 | |
| 7 | `0x121288` | captain gains `value` exp in ability 26 (`pwkGUtl_AddExp`), unless the captain is unused/unplayable | 194: 1000 |
| 8 | `0x121208` | for each of the 25 squad slots in use, clears `PlPinfo+0x23c` (u16). The value is ignored | 179, 190: 65535 |
| 9 | `0x121310` | nothing in the dispatcher (see below) | 167: 500 |
| 10 | `0x121318` | popularity +value for the squad player with ID `0x7cce` (31950) (`plPinfo_ChangePop`, kind 0) | 308: 50 |
| 11 | `0x121358` | same, −value | 307: 50 |
| 12 | `0x121258` | gate income: seat price × seats sold × a factor of 17–25 picked by `0x15cff8`, as `PlIncomeType 3`. The value is ignored | — |
| 13–19 | `0x121398`–`0x1213c8` | nothing in the dispatcher | 16: 261; 18: 102, 103, 241, 257, 262, 263; 19: 287 |

**Handler-read values.** Some handler modules read `effect1_value`
themselves instead of relying on the dispatcher. That's why kinds 9, 16,
18 and 19 carry values even though the dispatcher ignores them:

- **`0x132180`** stages `effect1_value × 10000` in `EvsWork+0xc0`.
  `0x1321d8` pays it (`PlPaymentType 22`) only if the player answered
  Yes (`EvsWork+0x1f8 == 1`).
- **`0x1327ec`** stages `effect1_value × 10000` in `EvsWork+0xc8`.
- **`0x132538`** finds the first effect of kind 1 or 2 and stores its
  `value × 10000` at `0x249a00`. This is probably the amount shown in
  the dialogue.
- **`0x1353dc`** adds `effect1_value` to a chosen squad player's
  popularity.

Which handler types own these functions isn't traced yet.

### Other

- **Weight.** `0x6c` is the weight/priority, default 100: 100 ×234,
  200 ×38. It's the same 100/200 split as the TBB prototype's
  priority byte.
- **Unused columns.** These are 0 in every record: `0x14`, `0x20`,
  `0x60`, `0xa0`, `0xac`, `0xcc`, `0xd0`, `0xd4`, `0xe4`, `0xec`,
  `0x108`, `0x10c`. `0xa0`, `0xac`, `0xcc` and `0xd0` are still read
  by code, so they're real fields with no data.
- **Flags.** There are 342 (`0x156`) of them, one byte each, at
  `*(EvsWork + 0x20)`. Flag 0 means "none" and is always true.
- **Runtime patches.** Code at `0x12e928` overwrites `+0x08`, `+0x68`
  and `+0x9c` for fixed lists of event IDs (tables at `0x238d58`…).
  Some events are retargeted at runtime, so the file isn't the
  whole story.

### Dialogue categories

The EVENT message reference names a whole category, and the scene plays it
from message 0. Categories are shared: records 1–47 and 366 all use
`35682` (the tournament-start speech, with a different `actor2` each), and
13 records use `35511`. 39 of the 327 categories in 35000–36999 aren't
referenced by any record (e.g. `35400`–`35402`, `35901`–`35920`,
`36000`–`36003`). Other code may trigger them, or they may be unused.

## Shared condition block

NEWS and MAIL run the same trigger checks as EVENT, in the same order and
through the same helpers, but from their own offsets. The scan loops are
`0x12c398` (NEWS, 368 records) and `0x128b78` (MAIL, 444). Each calls the
condition check, then a type-specific check, before queueing the item.

| Check | Helper | EVENT | NEWS (`0x12c220`) | MAIL (`0x128a48`) |
|---|---|---|---|---|
| timing (must equal the scan's timing) | | `0x68` | `0x74` | `0x2c` |
| earliest season | `0x12e3b8` | `0x7c` | `0x88` | `0x38` |
| season pattern | `0x12e3e0` | `0x80` | `0x8c` | `0x3c` |
| date pattern A | `0x12e450` | `0x84` | `0x90` | `0x40` |
| date pattern B | `0x12e4b0` | `0x88` | `0x94` | `0x44` |
| once only, cooldown class | `0x12e220` | `0x70`, `0x78` | `0x7c`, `0x84` | `0x30`, `0x34` |
| condition 1 (kind, arg) | `0x123898` | `0x8c`, `0x90` | `0x98`, `0x9c` | `0x48`, `0x4c` |
| condition 2 (kind, arg) | `0x123898` | `0x94`, `0x98` | `0xa0`, `0xa4` | `0x50`, `0x54` |
| required flag | `IsEventFlag` | `0x9c`, `0xa0` | `0xa8` | `0x58` |
| forbidden flag | `0x1243c0` | `0x74` | `0x80` | none |
| extra date rule (kind, arg) | `0x12e518` | `0xa8`, `0xa4` | `0xb0`, `0xac` | none |
| chance % | `0x12e570` | `0xb0` | `0xb8` | `0x60` |

The runtime slots for once-only/cooldown are `EvsWork+0x14` (EVENT),
`+0x18` (NEWS) and `+0x1c` (MAIL), 8 bytes per record.

In MAIL, 174 of 443 records have chance 0, so the random scan can never
pick them. Other code presumably sends them directly.

## NEWS record (192 bytes)

| Offset | Type | Field | Evidence | Values |
|---|---|---|---|---|
| `0x00` | u32 | index | data | = record index |
| `0x04` | u32 | check type | confirmed: `0x13f3f0` switches on it (48 cases, table `0x23b000`) after the condition check; each case tests game state. Types 14 and 34/35 also read `+0x9c` / `+0xb0` | 0–47, non-zero in 196 |
| `0x08` | u32 | handler type | confirmed: `0x12c4a0` switches on `value - 1` (32 cases, table `0x2388c0`), each allocating a 0x44-byte handler. 0 gets the default handler (`0x12fb40`) | 0–32 |
| `0x0c` | u32 | content type (`Param::PlNewsContentType`) | confirmed: `0x14c1ac` copies it to `PlNewsBody+0x8`, which `pwkGenNews_SearchStockNum` (`0x245b58`) compares with a `PlNewsContentType` | 2 ×201, 3 ×105, 0 ×40, 1 ×21 |
| `0x10` | u32 | layout flag | confirmed as a boolean: `0x14d098` returns `+0x10 != 0` for the current article, and the news screen (`0x863b8`) takes a different layout path when it's set | 3 in 17 placeholder records, else 0 |
| `0x14` | u32 | picture mode | confirmed: at `0x14c1c4`, 1 picks the article picture with `+0x18`, anything else with `+0x1c` | 1 in 130 |
| `0x18` | u32 | picture selector A | confirmed: `0x14bc10` (76 cases, table `0x23c7e0`); the result goes to article `+0x134`, which `NEWS::CFactory` reads (`0x24db0`) | 0–75 |
| `0x1c` | u32 | picture selector B | confirmed: `0x12ec50` (62-entry table at `0x238de8`), result at article `+0x134` | 0–61 |
| `0x20` | u32 | ? | data only; no traced NEWS consumer reads it | 0–14, non-zero in 204 |
| `0x24`–`0x5c` | 5 × {u32, u32, u32} | article variables 1–5: kind, arg1, arg2 | confirmed: `0x14c4d8` copies the five triplets into kind/arg1/arg2 arrays and fills variable slot *n* from triplet *n*, switching on the kind (e.g. 23) | kinds 23, 25, 26, 99, 188, 203, 257, 264–268; arg1 2/40/43/46/47; arg2 e.g. 1100, 4067–4122 |
| `0x60` | u32 | ? | data only | 0–2, non-zero in 31 |
| `0x64` | u32 | article body (message ref) | confirmed: `0x14c388`, `lhu +0x64` → `PlNewsBody+0x18` | category always 832 |
| `0x68` | u32 | caption (message ref) | data: a valid message ref, but no traced code reads it | 10 records (44–53), category 833, e.g. `Clear skies over {var:1:8}` |
| `0x6c` | u32 | headline (message ref) | confirmed: `0x14c394`, `lhu +0x6c` → `PlNewsBody+0x16` | category always 833 |
| `0x70` | s16 | ? | confirmed copied: `0x14c194` stores it at `PlNewsBody+0x10`; meaning unknown | 0, 4 ×20, 6 ×5 |
| `0x74` | s32 | timing | see the condition block | 4 ×237, -1 ×55, 0 ×40, 9 ×32, 21 ×3 |
| `0x78` | u32 | weight | confirmed (`0x12b0b8`); its low byte is also copied to `PlNewsBody+0x4` (`0x14c1a0`) | 100 ×164, 200 ×57, 140, 220, 180, … |
| `0x7c`–`0xb8` | | condition block | see above | `0x80` and `0xb4` are 0 in every record |

`0x14c0b0` builds a `Param::PlNewsBody` (at article `+0xc`) from the record.
It takes the message categories from a table at `0x1d9b10` (`50833`,
`50832`, ...) rather than from the record. `50832`/`50833` have the same
ids as `832`/`833`, but their text only lists each message's variables
(`W{var:1:3}{var:1:3}`), which the game uses to build variable lists. The
readable text is in `832`/`833`. 42 records (1–15, …, 340) are placeholders
with a label as the body (`TEXT_NP_MONTH_00`, `TEXT_NP_OFF_00`, …) and the
headline `Dummy`. The game probably fills those in from code.

`+0xb0` has a second use: besides the date rule, check types 34/35 and the
functions at `0x12fe20`, `0x130390`, `0x130960`, `0x130a50` and `0x15ec68`
read it.

## MAIL record (112 bytes)

| Offset | Type | Field | Evidence | Values |
|---|---|---|---|---|
| `0x00` | u32 | index | data | = record index |
| `0x04` | u32 | check type | confirmed: `0x13d538` switches on it (39 cases, table `0x23ae30`) after the condition check | 0–38, non-zero in 39 |
| `0x08` | u32 | handler type | confirmed: `0x128c48` switches on `value - 1` (11 cases, table `0x2386d0`) when the mail is processed | 0–11, non-zero in 40 |
| `0x0c` | u32 | direction | data: 2 marks mail the player sends (sender `{var:1:7}`, recipient a manager); 1 is received mail | 1 ×411, 2 ×32 |
| `0x10` | u32 | sender (message ref) | confirmed: `0x156da0` returns `lhu +0x10` of the current mail (MAIL getter `0x128e78`) | category 563, ids 20001–20019 (e.g. `Youth team Manager`, or `{var:1:101}`) |
| `0x14` | u32 | recipient (message ref) | confirmed: `0x156dd0`, `lhu +0x14` | category 563, ids 20001–20008, 3 distinct (mostly 20001 = `{var:1:7}`, the player) |
| `0x18` | u32 | open handler | confirmed: when non-zero, `0x128de8` creates a 0xc8-byte object (`0x131db0`, which reads the subject and body) | 1 ×257 |
| `0x1c` | u32 | question | confirmed: at `0x124fbc`, when non-zero the mail asks a yes/no question. The value (clamped to 0–4) indexes a table at `0x238678` of message refs `3000:2`–`3000:5`: "Make an offer?", "Accept the offer?", "Send a reply?", "Continue negotiations?" | 1 ×16 (player search reports) |
| `0x20` | u32 | subject (message ref) | confirmed: `0x156d70`, `lhu +0x20` | category 563, ids 11000–11309 |
| `0x24` | u32 | body (message ref) | confirmed: `0x156d40`, `lhu +0x24` | category 563, ids 1000–1442 |
| `0x28` | u32 | sender group | copied to the mail object's `+0x14` (`0x156c68`); data: groups mail by department (1 accounts, 2 facilities, 3 personnel/sales, 4 PR/sponsor, 5 secretary/other) | 0–5 |
| `0x2c` | s32 | timing | see the condition block | 4 ×386, 0 ×41, -1 ×10, 2 ×6 |
| `0x30`–`0x58` | | condition block | see above | `0x54` is 0 in every record |
| `0x5c` | u32 | weight | confirmed (`0x12b0b8`) | 100 in every record |
| `0x60` | u32 | chance % | see the condition block | 100 ×269, 0 ×174 |

As with NEWS, `50563` is the variable-list companion of `563`. Every MAIL
column with data now has a name.

## Open questions

- Names for the timing enum (`+0x68`), the 170 condition kinds
  (jump table `0x237df0`) and the 80 handler types (`0x238a40`). The
  effect kinds are decoded above.
- Which regions `PlTeam_Region` 0 and 1–13 are (0 is presumably the
  club's home region), who squad player `0x7cce` is, and what
  `PlPinfo+0x23c` holds.
- Which handler types consume `effect1_value` directly, and so what
  kinds 9/16/18/19 mean.
- What `+0x0c`, `+0x1c`, the five triplets at `+0x24`–`+0x5c` and
  `+0x64` are. They aren't read through the getter in the functions
  traced so far; the 32-byte unaligned copies of `+0x00`–`+0x1f`
  (e.g. at `0x13578c`) are a lead.
- The meaning of `date[2]` and `date[3]` in the date struct.
- How the 48×21 pattern table is laid out.
- NEWS `+0x20`, `+0x60` and `+0x70`; the NEWS/MAIL check types, handler
  types and article-variable kinds; and why no code reads NEWS `+0x68`
  (caption).
- Whether the 39 unreferenced dialogue categories are triggered elsewhere.
- Whether the five EVENT triplets at `+0x24`–`+0x5c` are variable specs
  like NEWS's (same offsets, same arg1 values 2/46/47). Their third value
  also matches speaker-name ids used in `ESC 0xC1` (e.g. 3110).

## Tool

```bash
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_EVENT.BIN events.csv   # named EVENT columns
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_NEWS.BIN  news.csv --text DAT/MESSAGE/MES.PAC
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_MAIL.BIN  mail.csv --text DAT/MESSAGE/MES.PAC --lang 2
```
