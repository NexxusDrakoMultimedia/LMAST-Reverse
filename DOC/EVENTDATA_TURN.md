# `EVENT/EVENTDATA_TURN.TBB`

An early export of the "turn" event sheet: one row per scripted event
(office visits, salesman pitches, locker-room talks, stadium news, ...).
218 records of **281 bytes** in a single `TBL1` table (61258 = 281 × 218).
The TBL1 line size says 32, which is wrong as a stride (see
[TBB_FORMAT.md](TBB_FORMAT.md)).

## The game doesn't use it

- **No references.** The name `EventData_TURN` doesn't appear in
  `SLES_541.51`, any `DLL/*.REL` overlay, or any other file in `DAT/`
  (including the `PRELOAD/SIMFILE*.PAC` load lists).
- **Event IDs don't appear anywhere else.** None of its 200 distinct
  event IDs (`OSA000`, `OHI006`, `LOC0110`, ...) occur in any other file
  on the disc.
- **Stale in CVS.** The leftover `DAT/EVENT/CVS/ENTRIES` shows it
  stopped at revision **1.1** (26 Jan 2005). The event data the game
  actually loads is `EvsDataBin_EVENT.bin` (rev **1.149**, 31 Mar 2006),
  referenced from `DLL/SIMPRG.REL` next to `EvsDataBin_NEWS.bin` and
  `EvsDataBin_MAIL.bin`. Those are fully numeric (no strings), so this
  TBB is a dead prototype of the same sheet.

So the layout below is **inferred from the data only**; no loader
exists to confirm the field names. It does account for every non-zero
byte in all 218 records, and no string overruns its slot.

## Record layout (281 bytes, packed, no alignment)

| Offset | Size | Type | Name (inferred) | Values seen |
|--------|------|------|-----------------|-------------|
| `0x00` | 4  | char[4] | category | always `TURN` (the shipped data splits events into EVENT / NEWS / MAIL, cf. `lastEventDate_TURN/NEWS/MAIL` in the ELF) |
| `0x04` | 4  | s32 | end marker | `0`, or `-1` on the last row only |
| `0x08` | 8  | — | padding | always 0 |
| `0x10` | 32 | char[32] | event id | `TUT000`, `OSA0006_001`, `OHI039`, `LOC0110`, `STA001` ... (prefix ≈ location/series; some IDs repeat with different `item`s) |
| `0x30` | 32 | char[32] | timing | `TURNSTART` 101, `GAMESTART` 71, `MONTHSTART` 16, `MENUEND` 12, `-` 8 (follow-ups), `YEARSTART` 4, `TURNEND` 3 |
| `0x50` | 1  | u8 | priority / weight | 100 ×124, 200 ×41 (all stadium `STA*`), 0 ×24, plus 1–10 and 101–250 |
| `0x51` | 32 | char[32] | mood / event class | `EV_NORMAL`, `EV_LUCKY1/2`, `EV_UNLUCKY1/2`, `NEUTRAL`, `NEWS0`, `LOCKER1`, `OFFICE0`, `CAMP0/1/3`, `RIVAL`, `NON` |
| `0x71` | 36 | char[36] | scene-type memo | `A`, `B`, `AorB`, `E+B`, `G`, `Y/N`, `B+Y/N`, `A+2…` + lossy Japanese |
| `0x95` | 64 | char[64] | item / picture | `AROMA_OIL`, `KEEPER_GLOVE`, `SPIKE`, `UEFA_CUP_LOGO`, `ITALY_FIRSTLEAGUE_REGULATION` ... (longest 35 chars) |
| `0xD5` | 36 | char[36] | location | `OFFICE`, `LOCKER`, `STADIUM`, `MY_ROOM`, `MEETING`, `ENTRANCE`, `GROUND`, `HOMETOWN`, `TV`, `YOUTH` |
| `0xF9` | 32 | char[32] | character | `SECRETARY`, `PLAYER`, `MANAGER`, `ANNOUNCER&SUPPORTER`, `SALESMAN`, `AGENT`, `P_COACH`, `M_COACH`, `SCOUT`, `CAPTAIN` ... |

Field boundaries at `0x10`, `0x30`, `0x51`, `0x95`, `0xD5` and `0xF9` are
certain (strings always start there, even when the preceding field is
full). The two 36-byte fields could equally be char[32] followed by an
always-zero u32; the data can't tell those apart.

## Notes

- **Lossy Japanese text.** Bytes `0x82`–`0xC6` show up singly, mostly in
  the scene-type memo (e.g. `A` + `C6 8B 8B 8B 8B C6 C6`). They don't
  form valid Shift-JIS pairs, so the exporter seems to have kept one
  byte per Japanese character. The original text can't be recovered.
  The same damage appears in a few other cells
  (`ENTRANCE\xC6BG_MODEL` for `ENTRANCE_BG_MODEL`).
- **Blank rows.** Rows 60 and 149 are blank apart from `category`,
  probably spacer rows in the sheet. Row 213 has no event ID
  (`TURNSTART` / `TUT` / `OFFICE`).
- **Priority values.** `priority` is only a guess, taken from the
  distribution. The values 100 and 200 look like percentages or
  priority tiers, and 0 shows up on tutorial and chained events.
- **Next target.** `EvsDataBin_EVENT.bin` (103,904 bytes) is the real
  event table and is loaded by `SIMPRG.REL`, so it's the one worth
  reverse-engineering next.

## Tool

```bash
python SRC/eventdata_turn.py DAT/EVENT/EVENTDATA_TURN.TBB eventdata_turn.csv
```

Non-ASCII bytes are written as `\xNN` so nothing is silently dropped.
