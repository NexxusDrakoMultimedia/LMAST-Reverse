<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Injuries

How a player gets injured, how long it lasts, and what the condition line
says about it. The game calls an injury *kega* (怪我). A player's injury is
stored in his `PlPinfo` record (see [`SAVE_FORMAT.md`](SAVE_FORMAT.md)):

| Offset | Type | Meaning |
|---|---|---|
| `0x250` | u16 | the injury value: what's left of the injury. Recovery takes from it (below). Not days |
| `0x254` | u32 | the injury kind, 0–8 |
| `0x20c` | u32 flags | `0x200` light injury (`plPinfo_IsLkega`, `0x217490`), `0x100` heavy (`plPinfo_IsHkega`, `0x217468`), `0x400` set by every new injury |

Kinds 0–2 are light and 3–8 heavy (`_plPinfo_SetKega` `0x2172f8` sets
`0x200` for kind < 3). Kind 8 is the "can't recover" injury:
`plPinfo_IsHkegaFunou` (`0x217418`) is heavy and kind 8, and its value is
`0xffff`.

## Short answer: why injuries seem to last three months at most

All **confirmed** below. A heavy injury is kind 3 or worse, and kind 3
always shows "needs three months' treatment". The longer kinds are
picked mostly by the player's **fatigue** at the time of the injury, and
by age. A rested player almost never gets one:

- A heavy match injury rolls a kind from the table by fatigue, and any
  roll of 0–2 becomes kind 3. Kind 3 always shows "three months".
- The chance of kind 4 or worse (six months or more) is 0% for fatigue
  under 100, 1% under 200, 2% under 300, 5% under 400, and only reaches
  39% at fatigue 1000. Ages 30–34 count as 50 more fatigue, ages 35 and
  over as 100 more.
- Fatigue of 700 or more already shows "Seriously fatigued" on the
  condition line, so most players who could get a long injury are resting.

The condition line counts down as the player recovers. A "six months"
injury later shows "three months" and then a light-injury message.
"Three months" is only a label: how many game days an injury value
lasts depends on the recovery rate (below), which hasn't been timed in
game.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x21aa00` | `plPinfo_CheckKega` | the practice injury check. Returns at once for a match (`PlPracNo` −1, `0x21aa38`), so its match branches are dead code. At most 3 injuries until the counter at `0x390840` is reset by `plPinfo_CheckKegaInitialize` (`0x21a9f0`). The chance is `0x219f90`(age, `+0x1e6`, fatigue, power, motivation) out of 10,000 |
| `0x21aad4`–`0x21ab08` | (same) | an injured player who gets a kind no worse than his current one gets his current kind + 1 instead (8 at most) |
| `0x21ab38`–`0x21abb4` | (same) | a heavy practice injury (kind ≥ 3) only happens to a player in your squad, and only if another of your 25 players can play. Otherwise there is no injury |
| `0x21a068` | `judgeKegaKind` | picks the kind: row = (fatigue `+0x23c` + 50 at age 30–34, + 100 at 35+) ÷ 100 of a 9-column percentage table. Practice uses `0x532c28`, matches use `0x532c90` |
| `0x21a120` | `calcKegav` | the injury value: kind 8 gives `0xffff`. Otherwise the kind's row of `0x532cf8` (10 × u16) holds up to five min/max pairs; it picks a pair, then a value in that range |
| `0x111730` | `fcEuroRand_Get0toI` | `(rand16 × n) >> 16`, so 0 to n − 1. `calcKegav` never picks past the last pair |
| SIMPRG.REL `0x163638`–`0x16370c` | (match results) | match injuries: for each of up to 8 injury records in the result, `judgeKegaKind` with the match table, the same +1 rule, then: if the record's word at `+8` is 0, kinds 3+ become 0; otherwise kinds 0–2 become 3. Then `calcKegav` and `_plPinfo_SetKega` |
| `0x211758` | `PlGiTask::Injury` | the match engine's injury report. Its last argument, `PlInjuryType`, sets the light (0) or heavy (non-zero) flag. GAMEPRG.REL calls it with 1 at `0x19cf78` and `0x19eefc`, and with 0 at `0x19d030` and `0x19efa4`. SIMPRG.REL `0x17275c` (the simulated match) takes it from a table |
| SIMPRG.REL `0x158d50`–`0x158dc8` | (practice) | each practice slot: the injury check, then for an injured player `plPinfo_CalcKegaDecrease` and `plPinfo_CheckRecover` (`0x21ae30`) |
| `0x21ac28` | `plPinfo_CalcKegaDecrease` | recovery per slot: a base by practice number (match −1: 70, or 0–20; `0x1b`/`0x1c` 180; `0x7d`/`0x84` 250; `0x82`/`0x83` 300; `0x86` 400; others 0–60), × (1 + a staff factor from the table at `0x532a28` + 0.0015 × the coaches' points) × (1 + (26 − age) ÷ 52) |
| `0x216dc8` | `plPinfo_KegaRecoverDaysChno` | the condition-line message, below |
| `0x285778`–`0x2857e0` | `WP::CDetailManager::ConvertPlayer_Condition` | shows message `chno + 1` of category 200 for an injured player |

That the word at `+8` of a match injury record is the `PlInjuryType` is
**empirical**: it is the only light/heavy value the match engine reports,
but the copy into the result (`PlGiTask::GetResult`, `0x211dc8`) hasn't
been traced.

### The kind tables

Match table `0x532c90`, percent per kind (columns 0–8):

| Row (fatigue ÷ 100) | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | kind ≥ 4 |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 40 | 40 | 20 | | | | | | | 0 |
| 1 | 30 | 34 | 30 | 5 | 1 | | | | | 1 |
| 2 | 20 | 33 | 40 | 5 | 1 | 1 | | | | 2 |
| 3 | 15 | 30 | 43 | 7 | 3 | 1 | 1 | | | 5 |
| 4 | 10 | 25 | 44 | 10 | 7 | 2 | 1 | 1 | | 11 |
| 5 | 5 | 21 | 44 | 15 | 10 | 3 | 1 | 1 | | 15 |
| 6 | 5 | 21 | 40 | 15 | 12 | 3 | 2 | 1 | 1 | 19 |
| 7 | | 15 | 35 | 30 | 12 | 3 | 2 | 2 | 1 | 20 |
| 8 | | 10 | 30 | 37 | 15 | 3 | 2 | 2 | 1 | 23 |
| 9 | | 5 | 24 | 40 | 20 | 5 | 3 | 2 | 1 | 31 |
| 10 | | | 16 | 45 | 25 | 5 | 4 | 3 | 2 | 39 |

The practice table `0x532c28` has the same shape, starts at 50/40/10 and
never gives kind 8. Its kind ≥ 4 column reads 0, 0, 0, 1, 4, 6, 10, 15,
22, 29, 31.

**Row 11 is out of bounds.** Fatigue 1000 with an age of 35 or more gives
row 11, which neither table has. The game then reads the next bytes: for
practice, padding and the match table's row 0 (kinds 5/6/7 at 40/40/20);
for a match, padding and the start of the value table (kind 5 at 250,
kind 7 at 244, kind 8 at 1). What `fcEuroRand_GetProbabilityTblNoAdd`
makes of a row that doesn't add up to 100 hasn't been traced.

### The value table `0x532cf8`

| Kind | Pairs (min–max) | Condition line when set |
|---|---|---|
| 0 | 250–500, 500–600 | a week |
| 1 | 601–900, 900–1000 | two weeks (a week below 600) |
| 2 | 1001–1250, 1350–1700 | a month |
| 3 | 4000–5000, 5000–6000 | three months |
| 4 | 6001–6750, 6500–8500, 8000–10000, 9000–10000 | six months |
| 5 | 10001–11000, 11000–13000, 12500–14500, 14000–16000, 14000–16000 | a year |
| 6 | **1600**–19000, 20000–25000 | anything from a month to 18 months |
| 7 | 25000–28500, 31000–36000 | two years |
| 8 | `0xffff` (not from the table) | can't recover |

Every kind starts where the one before ends, except kind 6. Its first
pair starts at 1600 where 16001 would fit, so a kind-6 injury can be as
short as a light one. It looks like a dropped digit (**empirical**: a
reading of the table, not proven).

### The condition line

`plPinfo_KegaRecoverDaysChno` returns, and the screen shows message
`chno + 1` of category 200:

| Injury | Value | chno | Message (English) |
|---|---|---|---|
| light | < 600 | 0 | 1 "Minor knock - needs a week's treatment." |
| light | < 1000 | 1 | 2 "Minor injury - needs two weeks' treatment." |
| light | else | 2 | 3 "... a month's treatment." |
| heavy | < 6000 | 4 | 5 "Serious injury - needs three months' treatment." |
| heavy | < 10000 | 5 | 6 "... six months' ..." |
| heavy | < 16000 | 7 | 8 "... a year's ..." |
| heavy | < 25000 | 8 | 9 "... 18 months' ..." |
| heavy | else | 9 | 10 "... two years' ..." |

chno 3 and 6 are never returned, so messages 4 ("two months") and 7
("nine months") are never shown. They were cut before either release:
the Japanese build's `plPinfo_KegaRecoverDaysChno` (SLPM_663.16
`0x217618`) is the same code (**confirmed**, see
[`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)). In PAL French, German,
Italian and Spanish both lines read "See Let's Make revised text 0425".
In Japanese, message 4 is a *light* injury of two months
(全治約2ヶ月の軽傷), which no light kind lasts long enough to be. English
kept text for both.

The Japanese build's kind and value tables (`0x52e998`, `0x52ea00`,
`0x52ea68`) are identical to PAL's, kind 6's 1600 included.

## Still unknown

- How many game days one injury value lasts: how often practice slots
  run, and which practice number an injured player gets.
- What `0x219f90` computes (the injury chance) and what `+0x1e6` is.
- What decides a heavy or light report in the match engine
  (GAMEPRG.REL around `0x19cf00` and `0x19ee80`).
- How kind 8 shows on the condition line (`0x285778` skips the
  message for it).

## Checking

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis judgeKegaKind calcKegav plPinfo_KegaRecoverDaysChno
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPinfo_CheckKega__
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x163638 60 --sles ISO/SLES_541.51
python SRC/mbb.py dump DAT/MESSAGE/MES.PAC --lang 1 --cat 200
```
