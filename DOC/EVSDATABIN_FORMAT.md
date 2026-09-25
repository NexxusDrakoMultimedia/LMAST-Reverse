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
| `0x64` | u32 | ? | data | high halfword looks like a hash (`0x8b62`…) |
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

## NEWS and MAIL records

These are only partly worked out so far. Like EVENT, each record starts
with its own index, and the weight sits at NEWS `+0x78` / MAIL `+0x5c`.

## Open questions

- Names for the timing enum (`+0x68`), the 170 condition kinds, the 20
  effect kinds and the 80 handler types. Each is a jump table in
  SIMPRG, at `0x237df0`, `0x237d30` and `0x238a40`.
- What `+0x0c`, `+0x1c`, the five triplets at `+0x24`–`+0x5c` and
  `+0x64` are. They aren't read through the getter in the functions
  traced so far; the 32-byte unaligned copies of `+0x00`–`+0x1f`
  (e.g. at `0x13578c`) are a lead.
- The meaning of `date[2]` and `date[3]` in the date struct.
- How the 48×21 pattern table is laid out.
- The NEWS and MAIL field layouts.

## Tool

```bash
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_EVENT.BIN events.csv   # named EVENT columns
python SRC/evsdatabin.py DAT/EVENT/EVSDATABIN_NEWS.BIN  news.csv     # raw u32 columns
```
