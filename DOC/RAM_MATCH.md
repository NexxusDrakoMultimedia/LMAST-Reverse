<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Runtime memory: the match

This doc is what is in memory during and after a match: the score, the
clock, the two teams, the events (goals, cards, injuries) and the
statistics (minutes, ratings, possession, the career records a match
feeds). It is one of the runtime-memory docs. They record where the
game keeps its data while it runs, for tools that read or watch the
game and for achievement sets. The file formats on the disc are in the
other docs; the saved copy of a career is in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far), the match
engine's player parameters in
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#the-match-engines-player-parameters),
the schedule that decides which match is played in
[`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) and
[`REGULATION_FORMAT.md`](REGULATION_FORMAT.md), and where a match day
sits in the game's scripts in
[`GAME_FLOW.md`](GAME_FLOW.md#a-match-day-rootmatchseq). The author's
guide and the index of all the runtime-memory docs are in
`RAM_MAP.md`.

## How to read this doc

- Every address is an EE RAM address in the PAL release (`SLES_541.51`
  and its overlays). EE RAM runs from 0 to 0x1FFFFFF and is
  little-endian. The Japanese release has its own addresses; none were
  derived here (see [`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md#how-the-tools-find-addresses-gameverpy)).
- Nothing here was measured in PCSX2 unless a row says so. The rows come
  from reading the game code (static analysis), and each was checked
  twice. The one value seen in the running game is the overlay base
  0xc75000 (Nexxus's PCSX2 runs, recorded in
  [`WIDESCREEN.md`](WIDESCREEN.md) and [`ECONOMY.md`](ECONOMY.md)).
- **Confirmed** means the address, size and behaviour were read in the
  game code, and the row names the function or address that shows it.
  **Empirical** means inferred from the code, the names or the data and
  not proven. A row with both says which part is which. A claim that
  failed a check, or that nobody could settle, is in the section's
  "Unconfirmed" list and not in its table. Do not build on those.
- Overlay addresses written "GAMEPRG.REL 0x..." are offsets in the
  overlay image, not EE addresses. The EE address is the overlay's load
  base plus the offset. The base is found at run time in the overlay
  registry at 0x35eda0 (the first section's table has the row).
- A pointer chain is read from the left. `[0x3906d8] + 0x1f544` means:
  read the u32 at 0x3906d8, add 0x1f544 to it, and that is the address
  of the value. In RetroAchievements terms this is one AddAddress step.
  Check every pointer for zero before you follow it. The "Pointer chains
  and stability" table of each section has one row per chain with its
  root, `valid_when` (when the chain can be read) and `stable_across`
  (what it survives).
- The two sections name the same objects with different letters, so the
  letters are defined again at the top of each section and do not carry
  over. In "Match core state" P is the PlGiTask buffer and G the match
  engine object. In "Match events and statistics" B is the PlGiTask
  buffer, P the match engine object, R a statistics sub-object and G a
  block of the schedule object. The two names for the PlGiTask buffer
  (the static words 0x3906d8 and 0x390784) are explained in both
  sections.
- Sizes are in bytes. Counts, offsets and thresholds are written in
  hex with `0x` when they are addresses or offsets and in decimal when
  they are quantities.

## Contents

- [Match core state](#match-core-state): the match-day gate, the two
  team ids, the final score, the live goal tally, the match clock, the
  result type and period, the competition and stage, the match grade and
  the mode flags, and how to find the match engine object through the
  overlay registry.
- [Match events and statistics](#match-events-and-statistics): the live
  goal counters per time segment, per-player minutes and goals, the event
  log, the man of the match pick, possession, the PlGiTask per-side and
  per-player records, the goal, injury and card logs, the final result
  and per-player records the match leaves in the schedule object, and
  the season and career statistics rows.

## Match core state

This part of memory holds what the game knows about the match being
played: the two team ids, the score, the clock, the competition and
stage, the mode flags, and the result type (extra time, shoot-out, away
goals). It lives in two places in the PAL release. The career-side
match record, `Param::PlGiTask` (P), is a heap block whose pointer sits
at the static address 0x3906d8. The live match engine in `GAMEPRG.REL`
keeps its own heap object (G), reached through a pointer in that
overlay's data, so the overlay load base has to be found at run time
first.

All addresses are for the PAL release (`SLES_541.51` and
`GAMEPRG.REL`). Everything here comes from reading the code. Nothing
was watched in a running game, except that `DOC/WIDESCREEN.md` and
`DOC/ECONOMY.md` record the overlay base 0xc75000 in PCSX2. `P+x` means
the u32 at 0x3906d8 plus `x`. `G+x` means the u32 at (GAMEPRG base +
0x2490fc) plus `x`. Overlay addresses written "GAMEPRG.REL 0x..." are
image offsets, not EE addresses.

Rows are labelled **confirmed** (the address and behaviour were read in
the code) or **empirical** (inferred from the code or the names, not
proven). Claims that failed a check, or that nobody could settle, are
in "Unconfirmed" and not in the table.

The roots are settled in the shared facts: the PlGiTask buffer
[0x390784] is allocated once at boot (`bufer_alloc` 0x210070, called at
0x1104c0 by `PwkCallbackCommand_Create`, whose only script call is the
first command of `ROOTMAINSEQ.SQB`) and freed only by an unreachable
`Pwk.Delete`. So the buffer address is the same from boot on, and
0x3906d8 holds that address only between `plGi_Create` and
`plGi_Delete`.

### Table

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3906d8 | 4 | u32 pointer, 0 when none | static | PlGiTask pointer (P) | Non-zero from `plGi_Create` until `plGi_Delete`, and zero otherwise. Create is called at 0x20373c in `CScheEuro::initializeTodayMatch` (reached at 0x113abc inside `Sche.MatchStart` 0x113a38, only when `getTodayMatchNum(1)` is non-zero) and at 0x11451c in `ScheCallbackCommand_CreateGiForFirstMatch`. Delete is called at 0x203808 in `deleteGameInterFace` (via `finalizeTodayMatch` at 0x11406c inside `Sche.MatchEnd`) and at 0x114540. While non-zero it equals the permanent buffer root [0x390784]. It means "a match day's game interface exists" (pre-match menu, 3D match, result screens), not "the 3D match is playing". | confirmed, `plGi_Get` 0x210960, `plGi_Create` 0x2108f0, `plGi_Delete` 0x210940 |
| [0x3906d8] + 0x1f544 | 4 | u32, always 0 or 1 | heap | Demo flag (PlGiTask) | 0 or 1, written once per match by the inline store at SLES 0x203d98 (`sltu` of the result of the virtual call at vtable +0x24, `isDemoMode`), cleared by `PlGiTask::init` at 0x210ff0. `isDemoMode` returns 0 for Normal and FirstPromote and `[CScheEuro+0x40c]` for VS (0x33b8e8). That word is set at SLES 0x206e5c and 0x206e60 from `plEve_IsFlagRuntimeSelectCompe(..., 4)`. When non-zero, `GAMEPRG.REL` 0x1120 and 0x1ea8b8 skip the result path, and `GAMEPRG.REL` 0x1c2918 returns mode 2. Mode there: 2 when this flag is set, else 1 if the VS flag is set, else 0. Whether it means "title attract match" is not settled (see Unconfirmed). | confirmed for address, size, writer, reset and the mode function; the meaning is empirical |
| [0x3906d8] + 0x1f548 | 4 | u32, always 0 or 1 | heap | VS-mode flag | 0 or 1. Copy of `CScheEuro::IsVsMode()` (vtable +0x1c): 0 for Normal (0x33b5a0) and FirstPromote (0x33b740), 1 for VS (0x33b8e0). Stored once per match by `initializeOneMatch` at SLES 0x203d7c. Zeroed by `PlGiTask::init` at 0x210ff4. Reads 0 from creation until `initializeOneMatch` has run. The title attract demo also builds the VS-mode `CScheEuro` (`Initialize_VsMode`), so it has VS = 1. `SetVSFlag` 0x33c420 has no callers; the inline store is the writer. | confirmed for address, size, writer and values; the "VS mode" meaning is empirical |
| [0x3906d8] + 0x1fba0 (home), + 0x24540 (away) | 4 | u32 team id | heap | Team ids | First word of each side's primary 0x49a0-byte `PlTeamData`. Id 1 is the player's own club in a career match built through `initializeOneMatch` (0x2039e4). Ids 0x21f to 0x22e (543 to 558) are the 16 VS-mode teams (`SetTeamData` 0x210ab8 tests id - 0x21f < 0x10), so the highest id admitted is 0x22e. The title attract demo, a VS match, used ids 130 and 87 in PCSX2, so that range is not what it uses. Working copies of the same sides are at + 0x28ee0 and + 0x2d880. Filled by `PlGiTask::SetTeamData` 0x210970. The accessor at 0x210198 builds 0x10000 + 0xfba0 and reads from [0x390784], so the words stay readable after `plGi_Delete` until the next `plGi_Create`. Slot 0 = home is inferred from the argument name. | confirmed for address, size and the id tests (id == 1, id < 0x21f); side order empirical |
| [0x3906d8] + 0x1faf0 (home), + 0x1fb9c (away) | 4 | u32 | heap | Final score per side | Goals handed from the engine to `PlGiTask::SetGameScore` 0x214070 (negative inputs clamped to 0). Cleared to 0 by `bufer_clear` at each `plGi_Create`, so 0 before the hand-over. Sole writer: `GAMEPRG.REL` 0x14cb6c (0x14cb80 writes 0-0 when the tally pointer is null), inside the function at 0x14c9a8, which runs once per side, called at GAMEPRG.REL 0x9230 inside the screen set-up function 0x9150. So the words are refreshed each time that screen is set up, not by a dedicated "match end" routine. Not a live score. Values are tiny (a sum of 8 bytes), so an 8-bit read of each word is enough. | confirmed (address, writer and the zero state) |
| G + 0x4920 + side*0x80 + slot*0x10 + 8 (slot 0 to 7) | 1 each, 8 per side | u8 | heap, root in overlay data | Live goal tally per side | Goals of each side split into 8 match-time slots (thresholds in the u16 table at GAMEPRG.REL 0x26c238). Goals for a side = the sum of the 8 bytes (`GAMEPRG.REL` 0x77cb0). Side 0 feeds the first score argument of `SetGameScore` at 0x14cb6c, side 1 the second. Side order is "first team in the engine's ordering by G+0x10c", home by inference only. G is non-zero only while the engine object exists. | empirical (the reader side is read in code; no writer was found) |
| G + 0x8908 | 4 | float32, seconds | heap, root in overlay data | Match clock | Elapsed match time in game seconds on the 90-minute scale. It is zeroed at construction (0x72170) and at 0x167848, 0x16ba64, 0x16bafc and 0x16bbe0. It is a match clock while the state word at G+0x891c is 0 to 7, but not a free-running one: the controller task init (0x1664c8) loads its float at +0x6c from G+0x8908 (0x16650c), so it is not reset at every phase change. Per frame the task adds speed (+0x70) / (vsync multiplier * 59.94) to +0x6c and mirrors it to G+0x8908 (0x1667a4 to 0x166880). The period value is stored into it at 0x166f9c, 0x167000, 0x16711c and 0x1671d0 (and via 0x16b988 and 0x16b9a8), so it is snapped at period changes. In PCSX2 it stayed pinned at the period limit (2700.00, 5400.00, 6300.00) during added time, with the state word odd (1, 3, 5). Period-end table (u16, GAMEPRG.REL 0x26c238): 2700, 2700, 5400, 5400, 6300, 6300, 7200, 7200 (end of 45', 90', 105', 120'). Read as a float. | empirical; readers at GAMEPRG.REL 0xaacc0 and 0x14cb20 confirmed |
| [0x3906d8] + 0x1f540 | 4 | u32, truncated seconds | heap | Game time copy | Copy of the match clock (G+0x8908) taken by `GAMEPRG.REL` 0x14cb20 to 0x14cb38: the float is converted by GAMEPRG.REL 0x2112d8 (float to u32, truncating) and stored at P+0x7540+0x18000. Same store as the inlined `SetGameTime` 0x33c378. It is written by function 0x14c9a8, called once per team from 0x9150, so it is refreshed each time that tactics screen is set up and is 0 before the first. Zeroed at init 0x210fdc. Not the live clock. | confirmed for address, writer and lifetime; truncation empirical |
| [0x3906d8] + 0x84 (result type), + 0x80 (period reached) | 4 + 4 | 2 x u32 | heap | Result type and period | + 0x84: 0 at set-up, 1 after a goal in extra time (`Goal` 0x211830, `OwnGoal` 0x211900, when period - 2 < 2), 2 at a shoot-out kick (`PK` 0x2119a8, which also sets + 0x80 = 4), 3 by `SetResultAweyGoal2` 0x2120c0 (away goals). + 0x80: 1 from `ResetGameIf` (store at 0x2125e4, constant 1), 2 or 3 after an extra-time goal, 3 at `EnterOT` 0x212828, 4 at a shoot-out kick. `PlGiTask::init` zeroes both (0x210f78, 0x210f80) and then calls `ResetGameIf` itself at 0x211088, so + 0x80 = 1 and + 0x84 = 0 already hold from `plGi_Create`, and are written again for the real match by `ResetGameIf` at 0x203ab8. A non-zero + 0x80 does not mean the match has started. Not monotonic and not a general "current period": a goal in normal time never changes it. Both are copied into the result record by `CnvResult` (0x210b50 to 0x210cfc; period to result +4 at 0x210bd0, result type to +8 at 0x210be4). | confirmed for the writers and the encoding |
| [0x3906d8] + 0x322d0 (home), + 0x32390 (away) | 1 | u8 counter | heap | Shoot-out goals per side | Byte + 0xb0 of the per-side record at buf + 0x32220 + side * 0xc0, incremented once per `PlGiTask::PK` call when PK's last argument is non-zero (beqz at 0x2119c4). The only call site in the executable and overlays is GAMEPRG.REL 0x30a4, which passes 1 (`addiu a3, zero, 1` at 0x30a8). Goal and OwnGoal are separate calls (0x308c, 0x30d0). Copied to result byte + 0xd by `CnvResult` 0x210cf8 when period == 4. Written in one batch when the finished match's events are reflected into the record, not kick by kick. | confirmed for address, size and the copy; the batch timing is empirical |
| [0x3906d8] + 0x1f480 (UID), + 0x1f920 (competition), + 0x1f924 (UID copy) | 4 | u32 (+ 0x1f480, + 0x1f924), s32 (+ 0x1f920) | heap | Competition and stage | + 0x1f480: schedule UID (PLSCHE_GROUP, 0 to 163). It is written twice per match with the same value: first by `ResetGameIf` (0x2125b0, parameter word 4) from the call at 0x203ab8, then by `SetMyGroup` 0x212058 (call at 0x203b3c). + 0x1f920: competition (PLSCHE_COMPE, 0 to 71, or -1 when `getCompetitionID` is negative, from `getScheCompe` 0x206560), word 0 of the 0x84-byte parameter block that `ResetGameIf` copies to + 0x1f920. + 0x1f924: UID, word 4 of the same block. Right after `plGi_Create`, `init` runs `ResetGameIf` with a zeroed block (0x211088), so + 0x1f480, + 0x1f920 and + 0x1f924 all read 0 (competition 0, not -1) until the first `initializeOneMatch`. Overwritten at each `initializeOneMatch`, including AI matches of the same day. Look the UID up with `SRC/schedule.py`. | confirmed for addresses and writers; numeric ranges follow `DOC/SCHEDULE_FORMAT.md` and were not tested in play |
| [0x3906d8] + 0x6c (grade); rule fields at + 0x18, + 0x1c, + 0x20, + 0x24, + 0x28, + 0x2a to + 0x6b | 2 for grade | u16 grade | heap | Match grade and rule block | + 0x6c: match grade 0 to 5 (0 = European and national-team competitions, per `DOC/REGULATION_FORMAT.md`), from the first halfword of the regulation row for the match's group, stored by `ResetGameIf` at 0x2123b4 to 0x2123bc. The block at P+8 (`GetRulePointer` 0x211608) is a hybrid, not a row copy: 0x68 bytes from the caller's parameter block (param + 0x18), then overwritten with row + 0x50 (foreigners) at + 0x18, row + 0x4c (squad) at + 0x1c, row + 0x4e at + 0x20, row + 0x52 (subs) at + 0x24, row + 0x06 (prize_kind, u16) at + 0x28, and row + 0x08 to + 0x49 (win bonus, prizes) at + 0x2a to + 0x6b. Because `init` runs `ResetGameIf` at `plGi_Create`, these hold the values for group 0 from creation and are rewritten for the real match at 0x203ab8. | confirmed for the grade and the field map |
| 0x35eda0 + 12*i (name pointer), 0x35eda4 + 12*i (base) | 4 | u32 pointers, 12-byte slots | static | Overlay module registry | SN DLL loader table. [0x35ed98] is a slot count (a high-water mark, capped at 0x400, checked at 0x15b2e4), [0x35ed9c] is count xor 0x31415926. Slot i: + 0 name pointer, + 4 header (the load base), + 8 check word (name xor header xor 0x31415926). A slot with a zero header word is free. GAMEPRG's slot is the one where name - header == 0x2ae54c (the string there is '../PS2_EE_Release/gameprg.elf'). Written by `snDllLoaded` 0x15b448 via 0x15b288 (name relocated at 0x15aee8), cleared by the unload routine 0x15b370 (zero stores at 0x15b39c to 0x15b3ac). The base is a multiple of 0x80. | confirmed |
| GAMEPRG base + 0x2490fc | 4 | u32 pointer to a heap object (0xa8a0 bytes), 0 when absent | overlay data (target is heap) | Match engine object pointer (G) | Created at 0x72060 (allocator 0x1cc2a8, constructor 0x72490, stored at 0x72090) during GAME_MODULE set-up. Zeroed by the teardown at 0x720a8 (stores at 0x720c0 and 0x720cc). Non-zero for the whole GAME_MODULE lifetime, including pre-match and post-match screens, not only live play. Only 3 stores and 821 loads reference it. Distinct from `fb::MatchManager::_instance` at image 0x249100. Fields used here: +0x10c (side/team key), +0x4920 (tally), +0x8908 (clock), +0x891c (state word), +0x8e8c (two team player counts ordered by +0x10c). | confirmed for creation, teardown and address; the field meanings are empirical |

### Pointer chains and stability

Roots and offsets, entry by entry. Nothing here was run in a game.

| Entry | Root and chain | valid_when | stable_across |
|---|---|---|---|
| PlGiTask pointer | Static word at 0x3906d8 (0x390000 + 0x6d8). Same value as the static root [0x390784] while the task exists. P is a 0x32668-byte block from heap block 6 (`bufer_alloc` 0x210070). | Non-zero between `plGi_Create` and `plGi_Delete`, that is from `Sche.MatchStart` to `Sche.MatchEnd` of a match scheduled today. Zero otherwise. Does not by itself prove the 3D match is playing. | The address is fixed. The block P is allocated once at boot (`bufer_alloc` called at 0x1104c0) and freed only at the unreachable `Pwk.Delete` (`bufer_free` called at 0x110548), so it is the same across matches, loads and the whole boot. The word 0x3906d8 changes only at create and delete. |
| Demo flag | [0x3906d8] + 0x1f544 | [0x3906d8] != 0 and `initializeOneMatch` has run. Do not read it after delete. | Constant for the match once set. Rewritten at each match. |
| VS flag | [0x3906d8] + 0x1f548 | [0x3906d8] != 0 and `initializeOneMatch` has run (store at 0x203d7c). Before that it reads 0. | Constant through the match. Zeroed again by the next `plGi_Create`. |
| Team ids | [0x3906d8] + 0x1fba0 (home) and + 0x24540 (away). The accessor at 0x210198 uses [0x390784] as its base. | [0x3906d8] != 0 and `PlGiTask::init` plus `SetTeamData` have copied the teams in. | Constant within a match. Rewritten at each `plGi_Create`, which clears the buffer. The buffer address is fixed, so the address itself does not move. |
| Final score | [0x3906d8] + 0x1faf0 and + 0x1fb9c. Buffer is the same block as [0x390784]. | [0x3906d8] != 0 and the hand-over at GAMEPRG.REL 0x14cb6c has run. 0 before that. | Unchanged after the hand-over until the next `plGi_Create`. After `plGi_Delete` the data stays reachable through [0x390784] but not through 0x3906d8. |
| Live goal tally | Find the GAMEPRG base from the registry, G = [base + 0x2490fc], tally = G + 0x4920 + side*0x80 + slot*0x10 + 8. | GAMEPRG loaded and G non-zero (G in 0x100000 to 0x1FFFFFF). G is 0 before GAME_MODULE set-up and after its teardown. | Constant frame to frame within one match. G is a fresh allocation each match and is zeroed at teardown, so do not cache G across the end of a match. The base also depends on load order. |
| Match clock | G = [GAMEPRG base + 0x2490fc], clock = float at G + 0x8908. | Only while GAMEPRG is loaded (modules 6 or 172; modules 171 and 173 also load it) and G != 0. Not valid on menus, career screens, loading screens or the launcher. | Stable across frames within one match. Restarts at 0.0 for every new match object. Re-read the chain every frame. |
| Game time copy | [0x3906d8] + 0x1f540 | [0x3906d8] != 0 and a half-time or full-time tactics screen has been entered at least once in the match. Zeroed at init 0x210fdc. | Stable after the last tactics break, through the result screens. Not across matches. Not reset between halves. |
| Result type and period | [0x3906d8] + 0x84 and + 0x80 | [0x3906d8] != 0. + 0x80 = 1 and + 0x84 = 0 hold from `plGi_Create` (via `init`) and again after `ResetGameIf` at 0x203ab8. | Written only on events. Cleared by the next `plGi_Create`. P is the same buffer across the whole boot. |
| Shoot-out goals | [0x3906d8] + 0x322d0 and + 0x32390 (root [0x390784], same pointer). | PlGiTask buffer allocated and the finished match's events reflected into it. Read it after the match has ended. Pair with + 0x84 == 2. | Stable until `bufer_clear` 0x210100, `bufer_free` 0x2100c8 or `init` 0x210f00. |
| Competition and stage | [0x3906d8] + 0x1f480, + 0x1f920, + 0x1f924 | [0x3906d8] != 0 and `initializeOneMatch` has run for the current fixture. Before the first one after `plGi_Create`, all three read 0, so UID 0 and competition 0 cannot be told from "not set". Not set for matches that skip `initializeOneMatch`. | Stable while [0x3906d8] stays non-zero, but overwritten at every `initializeOneMatch`, so it can change between matches of the same day. Rewritten at the next `plGi_Create`. |
| Match grade and rule block | [0x3906d8] + 0x6c and the fields above. | [0x3906d8] != 0 and `ResetGameIf` 0x212128 has run (from `init` at 0x211088 with a zeroed block, or from `initializeOneMatch` at 0x203ab8 with the real one; it returns 0 early on a null parameter pointer). | Fixed while the pointer is non-zero, rewritten at match set-up (`initializeOneMatch` 0x2038d8, `PreMatchRun` 0x213cd0, `init`). Static mirror: s32 group at 0x5eacb0 and s16 grade at 0x5eacb4, set by `plRec_SetMatchRegulationsInGame` 0x21dd38 (called at 0x203b30), persisting after the interface is deleted. For groups 148 to 163 (VS), `plRec_MatchRegulations` returns a copy at 0x5ead30. |
| Module registry | Static: count at 0x35ed98, slots from 0x35eda0. base = [0x35eda4 + 12*i] for the slot with [0x35eda0 + 12*i] - base == 0x2ae54c. Then G = [base + 0x2490fc]. | Only while GAMEPRG.REL is loaded (modules 6, 172, 171, 173). Scan i = 0 to [0x35ed98] - 1 and require a non-zero header word. If no slot matches, every GAMEPRG address is invalid. | Registry addresses and slot layout fixed. The slot index and the base depend on load order and slot reuse. 0xc75000 was seen in single PCSX2 tests (`DOC/WIDESCREEN.md`, `DOC/ECONOMY.md`); not proven constant. Written only at overlay load and unload. |
| G pointer | u32 at GAMEPRG base + 0x2490fc | Non-zero from GAME_MODULE set-up (call at 0x2520, via chain 0x2b00) to teardown (0x3330). If another overlay is mapped at the same base the word is arbitrary memory, so check the module first. | Constant for one GAME_MODULE session, across kick-off, replays and half-time. New allocation each match, cleared between matches. The absolute address depends on the load base. |

### RetroAchievements notes

Concrete advice for an author, taken only from the rows above.

- Find the base first. Scan the registry at 0x35eda0 + 12*i for the slot whose name pointer minus its base word equals 0x2ae54c, then read G at base + 0x2490fc. If no slot matches, GAMEPRG is not loaded and nothing G-based is valid. Re-scan when the match starts or the slot changes. Do not hard-code 0xc75000.
- A "match day" gate is a non-zero u32 at 0x3906d8. It is not a gate for live play: it is also non-zero during set-up and result screens. Do not use 0x390784 as a gate, because it is non-zero from boot on.
- A "match engine exists" gate is G != 0 (inside 0x100000 to 0x1FFFFFF). It is true for the whole GAME_MODULE lifetime, including pre-match and post-match screens, so pair it with the clock value or another state field to get "ball in play", and with 0x3906d8 != 0. Modules 171 (StadiumViewer) and 173 (ShimizuTest) also load GAMEPRG; whether P exists there was not examined.
- Mode check: the PlGiTask flags are not a clean "career match" test. VS flag (P+0x1f548) == 0 excludes VS matches and the title attract demo (which runs as VS), and demo flag (P+0x1f544) == 0 excludes the runtime-selected "no result" case. Both also read 0 for opening-playoff (FirstPromote) matches, and both read 0 until `initializeOneMatch` has run, so latch the check after the match has started, not on the first frame where P is non-zero. Both are strict 0 or 1, so an 8-bit read is enough. For the title attract demo, the separate script flag at 0x34d43c is 1 only from `RootDemoMatchSeq` 0x18 to 0x208 (writer 0x109394 in `fcEuroDummyCommand_SetDemoFlag`).
- Per-club or per-opponent sets: read the two team ids at P+0x1fba0 and P+0x24540 and check for id 1 (the player's club in a career match). Latch them once non-zero, because the next `plGi_Create` clears the buffer. Which of the two is home is inferred, not confirmed.
- Live score: sum the 8 bytes per side at G + 0x4920 + side*0x80 + slot*0x10 + 8, compare with the previous frame, and require G != 0. Pitfall: side 0 is only inferred to be home, and the engine orders sides by G+0x10c. Latch the last value before teardown, because G is zeroed when the engine is destroyed.
- Final result: P+0x1faf0 and P+0x1fb9c are 0 until the hand-over at GAMEPRG.REL 0x14cb6c, and are refreshed each time the tactics screen is set up. A 0-0 result cannot be told from "not yet handed over" by these words alone. Read them before the next `plGi_Create`. In PCSX2 they were written at the half-time tactics screen, not at full time, so a goal after half time may be missing from them: use the live tally for the score.
- Clock: read as a float, never an integer. In added time the clock stays pinned at the period limit (seen at 2700.00, 5400.00 and 6300.00), so it does not give the minute there. Use floor(t / 60) against the previous frame for minute triggers. Guard against G changing between frames, since a delta across two different match objects is meaningless.
- Extra time and shoot-out: P+0x84 == 2 and P+0x80 == 4 mark a shoot-out, P+0x84 == 3 away goals, P+0x84 == 1 a goal in extra time. P+0x80 is 1 from `plGi_Create`, so it is not a start-of-match signal. For shoot-out winners compare the bytes at P+0x322d0 and P+0x32390 after the match has ended, not during the shoot-out, because they are written in a batch.
- Competition-specific sets: read the UID at P+0x1f480 and look it up with `SRC/schedule.py` (`DOC/SCHEDULE_FORMAT.md`). It changes at every `initializeOneMatch`, including AI matches of the same day, so confirm that the player's own match is the one in progress. The competition at P+0x1f920 can be -1 once a match is set up, and reads 0 before that.
- Do not poll P+0x1f540 for a live clock. It is a copy refreshed at tactics breaks.
- Re-read the pointers defensively and null-check before every dereference. P (the buffer) does not move during a boot, but 0x3906d8 does go to 0, and G is a new allocation for every match.
- Other overlays can be told apart by their registry constants (read from the REL headers by one reviewer, not rechecked by another): SIMPRG 0x267aa6, MOVIEPRG 0x657ce, SAVEPRG 0x5ae42, CEDITPRG 0x23b3f, VSPRG 0x1ba9b, YRSTPRG 0x3b2df, TESTPRG 0x416c2.

### Unconfirmed

Do not rely on these.

| Claim | Why it is not relied on |
|---|---|
| "Demo flag (P+0x1f544) means a title-screen attract match with no result recorded" | Not shown. The flag comes from `isDemoMode`, which for the VS class returns `[CScheEuro+0x40c]`, set from the runtime-selected-competition regulation flag 4 (`plEve_IsFlagRuntimeSelectCompe`). Only the skip of the result path at GAMEPRG.REL 0x1120 is supported. The script flag `fcEuro_CheckDemoFlag` (0x1093a0, word 0x34d43c) is a different variable. |
| Why the PlGiTask exists during the title attract demo | Measured: it does (see "Tested in PCSX2"). `RootDemoMatchSeq` calls `Sche.MatchStart` at 0x118, but `initializeTodayMatch` is guarded by `getTodayMatchNum(1)` (0x113a6c), and what the demo setup makes it return was not traced. |
| `finalizeTodayMatch` runs on every exit path (for example quitting mid-match), so 0x3906d8 is never stale | Not verified. |
| "Final score is written once at full time" | Refuted for a match with a half-time break: the writer 0x14c9a8 runs once per side inside the screen set-up function 0x9150, and in PCSX2 the score words were written at the half-time tactics screen (see "Tested in PCSX2"). Not seen to run again at full time. They did not catch up with a goal in injury time (see "Tested in PCSX2"). Whether they include own goals, extra-time or shoot-out goals, is unverified. |
| Writer 0x77c00 of the live tally, "called on a goal", own goals credit the scoring side | No static caller found (no relocation, no raw `jal`, no vtable word). Only the reader side is confirmed. |
| Side 0 of the tally is home | Inferred from the `SetGameScore` argument order only. Other code (0xaadd8, 0xa9d68) flips the side by comparing a team key with G+0x10c. |
| That the HUD clock shows exactly G+0x8908 | Not checked. |
| G+0x8910 as added (injury) time, and G+0x8918 as a per-tick counter | Guesses from the code ("looks like", "probably"); not verified. |
| State word G+0x891c: what each value means | The state word reaches 0xb (jump table at 0x290180 covers 0 to 8). The meaning of each value is unverified. Seen in PCSX2: it is the period segment (0 first half, 1 end of the first half, 2 second half, 3 at 90:00, 4 and 5 in the first half of extra time; the tally row of a goal is the word at that moment), 2 on the half-time screens and 11 at the final whistle and the full-time result screen. Values 6 to 10 were not seen. |
| "5400.0 means 90:00" | The period-end table has 5400 as the end of the 90th minute, and a compare with 5400.0 exists at GAMEPRG.REL 0xd9260. A reviewer of the game-time copy also saw thresholds 5100, 6000 and 6900. Treat 5400 as likely but untested in play. |
| P+0x1f540 holding about 2700 at half time, or above 5400 with added time | 2700 at half time was observed in PCSX2 (exactly 2700, with the clock at 2700.00). A value above 5400 with added time was not. |
| Values 4 and 5 of the developers' 0 to 5 range for P+0x80 | Value 4 is produced by `PK`. Value 5 is not produced by any code read. The guard in `OwnGoal` and the callers of `EnterOT` were not found. |
| Shoot-out byte counts "scored kicks" and is live during the shoot-out | The only call passes a constant 1 for the scored argument, and whether a missed kick is ever sent as a PK event is unknown. The byte is written in a batch after the match. Side 0 = home assumed. |
| P+0x1f484 as the previous UID | Refuted: it is a copy of P+0x1f474, a different field whose writer was not traced. P+0x1f488 is reported as a signed period byte by another draft and is not checked here. |
| P+8 to P+0x7f as a 0x78-byte copy of the REGULATION.TBB row | Refuted. Clubs (row + 2), unk04 (row + 4) and ban_yellows (row + 0x4a) are not copied, and no extra-time field was seen. |
| Grade value range 0 to 5 and "0 = top competitions" | Taken from `DOC/REGULATION_FORMAT.md`, not rechecked against the data. |
| `GetMatchGrade` readers | No reader of 0x33c468 was verified. |
| G+0x10c as "the side the human controls" | Not verified. |
| P+0x1f480 and the other competition fields hold UID 0 or competition 0 for a real match | Not a claim of the code: the zero state is only the `plGi_Create` default. Whether a real fixture can have UID 0 is not checked. |
| The Japanese release addresses | Not derived (use `gamever.py`; note `JAPANESE_RELEASE.md` records a different pwork global there). |

Claims from earlier drafts that the code refutes, listed so they do not
come back: "P is allocated per match and can move between matches"
(`bufer_alloc` has one call site and allocates only if [0x390784] is 0);
"[0x390784] marks a match day" (it is non-zero from boot);
`SetDemoFlag` 0x33c408 and `SetVSFlag` 0x33c420 as the flag writers (no
callers; the writers are the inline stores at 0x203d98 and 0x203d7c);
"the highest team id is 559" (it is 0x22e = 558); "G is 0 outside a
match" (G lives for the whole GAME_MODULE).

### Still unknown

- Is there a single clean "match in progress, kick-off taken, full time" flag? P != 0 spans the whole match day. G != 0 spans the whole GAME_MODULE lifetime. The engine's game-state machine (kick-off, half time, full time, results) was not traced. A PINE watch of G+0x8908 and P+0x1f540 around a match would settle it.
- Does the score at P+0x1faf0 and P+0x1fb9c (`SetGameScore`) cover only 90 minutes or also include extra-time goals and shoot-out kicks? The tally uses 8 time slots and no shoot-out slot was identified. Compare it with the on-screen score after an extra-time match.
- Who reads P+0x1faf0, P+0x1fb9c and P+0x1f540? Nexxus's reading is the half-time tactics screen (see "Tested in PCSX2"); the accessors `GetGameScore` 0x2140a0 and `GetGameTime` 0x33c390 have no caller found yet.
- Is 0x9150 also entered at full time? In PCSX2 it ran at the half-time tactics screen and did not run again at full time in a match with no second-half goal. Its early return (MatchManager + 0x96c >= 2) may be why. In a second career match (injury-time goal, 2-2) they stayed 0-0 to the final whistle, and Nexxus had skipped past the half-time screens there. Whether a match whose tactics screen was shown gets a second-half goal in them is not known. They are not the final score. The wrappers 0x8f98 and 0x8fb8 are reached from 0x1aa3a0, with the choice depending on MatchManager + 0x6e4, but this chain was not traced further.
- Does G+0x8908 match the HUD clock, and how is injury time represented? `GetTimeMode` (P+0x7c) and the injury-time limit were not traced. The `*LOSSTIME*` tables in `DOC/GAME_DIR.md` suggest the displayed injury time lives in the GAME data tables.
- Does the clock stop during stoppages, replays, set pieces and the half-time break (the speed at +0x70 may be 0 then)? Where is the controller task's +0x5c pointer to G set?
- Where is the live period (first half, second half, extra time, penalties) kept inside G, and what do the state values 6 to 0xb at G+0x891c mean? (0 to 5 are the period segments, 11 was seen at full time.) Only the PlGiTask side (P+0x80 and the goal event period bytes) was identified.
- Side mapping: which tally side is home, and what G+0x10c denotes. Controller assignment (`GetOperator`, `GetPort`: P+0x8a+side, P+0x8c+side*4) and the `CTacticsManager`'s "player's side" were not decoded.
- Venue, stadium and neutral ground: `GetStadium` 0x212c60 returns the `PlGi_Stadium` block, and `InitStadium` 0x212fa0 and `IsNeutrality` 0x33c4e0 were not decoded. The HUD's home/away flag and the match weather (PlGi_Env) were not located.
- Friendly, league or cup: no single match-type variable was found. Use the schedule UID (P+0x1f480) with `SRC/schedule.py`, or the regulation row data. National-team matches (`pwkSche_IsNationalMatch` 0x256b30) were not checked for a flag in P.
- Result record slots at P+0x94 + n*0x3c8 (n < 0x80; byte +6 = 1 when valid, + 0x10 and + 0x14 team ids, + 0x30 period, + 0x34 result type, score bytes from + 0x38): the per-half layout of the score bytes (`CnvResult` 0x210cd0 to 0x210cfc increments byte 0xc + side*2 + half) was not confirmed. This record is the candidate "full time reached" trigger. [P+0x1f484] is a copy of P+0x1f474, not a count, so what selects n needs rechecking.
- What the virtual calls at vtable +0x1c (VS) and +0x24 (demo) on the `CScheEuro` object return in each mode in practice, and who calls `initializeOneMatch` (called from 0x113b24 in `ScheCallbackCommand_MatchBranch` per one reading; the order of the player's match among the day's matches is unverified).
- Who calls `EnterOT` 0x212828, and whether any overlay reads or writes P+0x80 and P+0x84 through raw offsets.
- Whether `ScheCallbackCommand_CreateGiForFirstMatch` (0x1144d0) is a first-match or tutorial flow, and whether exhibition matches without a schedule group create a PlGiTask at all.
- Whether the GAMEPRG base is stable across runs and save states. The registry scan was not run in a live game. Also whether `snDllMove` 0x15b6b0 ever relocates a loaded overlay at run time (no direct call found).
- Whether the developer launcher, StadiumViewer (module 171) and ShimizuTest (173) create P and set G, and so whether the mode flags need extra gating.

### Checking the claims

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Get
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Delete
python SRC/sles_disasm.py ISO/SLES_541.51 addr 203d70 14
python SRC/sles_disasm.py ISO/SLES_541.51 addr 2125a0 12
python SRC/sles_disasm.py ISO/SLES_541.51 addr 2119a8 14
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x72060 14 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x14cb20 12 --sles ISO/SLES_541.51
python SRC/snr2.py xref ISO/DLL/GAMEPRG.REL PK__Q25Param8PlGiTaskQ25Param10PlHomeAwayii
```

What each shows. The first two give the load at 0x3906d8 and the store
of zero at 0x210954. The third shows the VS-flag store at 0x203d7c and
the demo-flag store at 0x203d98 (offsets 0x7548 and 0x7544 from
P+0x18000). The fourth shows `ResetGameIf` writing the competition word
to P+4 and to P+0x1f480 (0x7480 plus 0x18000) at 0x2125b0. The fifth
shows `PK` setting + 0x84 = 2 and + 0x80 = 4 and incrementing byte
+ 0xb0 only when its last argument is non-zero. The sixth shows the
allocation of the 0xa8a0-byte engine object and its store to
GAMEPRG + 0x2490fc at 0x72090. The seventh shows the clock float loaded with `lwc1 ... 0x908(...)` (the
G+0x8908 field, with 0x8000 added in the preceding address
arithmetic), converted by 0x2112d8 and stored at P+0x1f540 at
0x14cb38. The eighth shows the single reference
to `PK`, at GAMEPRG.REL 0x30a4.

## Match events and statistics

This part of memory holds what the PAL release keeps for one match. Two
places matter. `PlGiTask` is a 0x32668-byte heap buffer (the
game-interface object) with per-player minutes, ratings, cards,
injuries and the goal, card and injury logs. GAMEPRG.REL's match object
holds the live counters while the 3D match runs: goals per side, ball
possession counters, the event log and the man-of-the-match pick. After
the match the result and the per-player records are copied into the
schedule object (`CScheEuro`), and your club's records are added to the
career statistics. Everything below comes from code, docs and overlay
data (static analysis). No in-game memory was read for this section.
Addresses are for the PAL release (`SLES_541.51`).

Overlay addresses assume the GAMEPRG.REL load base 0xc75000. That base
was observed in Nexxus's PCSX2 runs (`DOC/WIDESCREEN.md`,
`DOC/ECONOMY.md`) and is not derived: the overlay sits in heap block 2
(0x305000 bytes, shared with SIMPRG), and the exact start of that block
was not worked out. At run time the base is the "header" word of the
GAMEPRG slot in the overlay registry at 0x35ed98 (12-byte slots from
0x35eda0, filled via `snDllLoaded` 0x15b448).

Names used below: B = the PlGiTask buffer pointer. P =
`u32[GAMEPRG_base + 0x2490fc]`, the match object (0xa8a0 bytes, heap,
class not identified). R = P + 0x4920, the statistics sub-object. G =
`u32[u32[0x390650] + 0x414]`, the current-game block of `CScheEuro`.
Side 0 and side 1 are probably home and away, but that is not proven
(side 0 of the possession counters is the team whose id equals
`u32[P + 0x10c]`). Slots run 0 to 24.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x003906d8 | 4 | u32 heap pointer (static root) | static | PlGiTask pointer (match-day gate) | B, the 0x32668-byte PlGiTask buffer. Non-zero from `plGi_Create` (0x2108f0, store at 0x210920) to `plGi_Delete` (0x210940, clear at 0x210954). Set by `CScheEuro::initializeTodayMatch` (0x203708, called at 0x113abc inside `Sche.MatchStart` only when a match is scheduled today) or by `CreateGiForFirstMatch` (0x1144d0). Cleared by `deleteGameInterFace` (0x203800) via `finalizeTodayMatch` (`Sche.MatchEnd`) or by the first-match delete (0x114538). So it is non-zero from the pre-match menu through the 3D match and the post-match screens until `Sche.MatchEnd`; it is zero on days without a match. Do not use 0x00390784 as a mirror: it is non-zero for the whole boot after `Pwk.Create`. | confirmed (code) |
| B + 0x1f544 | 4 | u32 (0 or 1) | heap | Demo flag | The schedule class's `isDemoMode`: 0 for `CScheEuro_Normal` (0x33b5a8) and `CScheEuro_FirstPromote` (0x33b748), and the field at this+0x40c for `CScheEuro_VS` (0x33b8e8). Written once per match by `CScheEuro::initializeOneMatch` (store at 0x203d98, from vtable slot +0x24), zeroed by `PlGiTask::init` (0x210f00) at 0x210ff0. The word at this+0x40c is written at 0x206e5c and 0x206e60 depending on a runtime-selected-competition flag, so this flag is a regulation flag of the VS-class controller. Non-zero stops GAMEPRG 0x10e0 from writing the result (see the GameResult row). "Title-screen attract match" is not confirmed. | confirmed (code) |
| B + 0x1f548 | 4 | u32 (0 or 1) | heap | VS flag | 1 when the schedule controller is `CScheEuro_VS` (`isVSMode` 0x33b8e0 returns 1), else 0 (Normal 0x33b5a0, FirstPromote 0x33b740). Written by `initializeOneMatch` (store at 0x203d7c, from vtable slot +0x1c), zeroed by `PlGiTask::init` at 0x210ff4. The title attract demo also builds the VS-mode `CScheEuro` (`Initialize_VsMode`), so a demo match would read 1 here, if a PlGiTask is created for it (not traced). | confirmed (code) |
| 0x00ebe0fc (GAMEPRG + 0x2490fc) | 4 | u32 heap pointer | overlay | Match object pointer P | Pointer cell to the match object. Written at GAMEPRG 0x72090 (new object of 0xa8a0 bytes, constructor 0x72490), zeroed at 0x720c0 and 0x720cc. Not the exported `fb::MatchManager$_instance` cell, which is a different cell at GAMEPRG + 0x249100. 0xebe0fc assumes base 0xc75000. | confirmed (code); base observed only |
| R + 8 + side*0x80 + i*0x10 (i = 0..7) | 8 bytes per side | u8 x8 | heap | Goals per side, per time segment | Live goals. goals(side) = sum of the 8 u8 counters, side = the scoring side (an own goal is credited to the other side). Segments end at 45, 45, 90, 90, 105, 105, 120, 120 min (u16 table at GAMEPRG 0x26c238: 2700, 2700, 5400, 5400, 6300, 6300, 7200, 7200 s). Row index is `u32[P + 0x891c]` through 0x78a90 (0 to 7; larger values are not counted). Match-end code at GAMEPRG 0x14cb48-0x14cb68 sums both sides (0x77cb0) and passes them to `PlGiTask::SetGameScore` (0x214070, called at 0x14cb6c). Live writer is 0x767b0 (reached by a jump at 0x193190). | confirmed (code) |
| R + 0x10c + side*0x9c4 + slot*0x64 (+0 and +1) | 2 | u8 x2 | heap | Live per-player minutes and played flag | +0 is a counter of match-clock minutes, incremented once per minute change for the 11 players on the pitch (0x78950, called from 0x190824 in periods 0, 2, 4, 6). +1 is the played flag, set to 1 by 0x776b8 when a player is used. Match end copies +0 to `PlGiTask::SetTime` and +1 to the player record (GAMEPRG 0x3110-0x31dc). Record stride 0x64, 25 slots per side, side stride 0x9c4. The record base is probably R + 0x108 (a u32 at +0 is the possession counter below, minutes +4, played +5, goals +7, own goals +8): empirical. | confirmed (code); record base empirical |
| R + 0x10f + side*0x9c4 + slot*0x64 | 1 | u8 | heap | Live per-player goals | Goals scored, own goals excluded. Incremented by 0x767b0 when the own-goal flag is 0. Own goals go through 0x76e60 to the byte at record +4 (R + 0x110 + ...). | confirmed (code) |
| R + 0x1712 + 3*k, count u16 at R + 0x2b88 | 3 per entry, max 396 (0x18c) | array of 3-byte entries; u16 count | heap | Match event log | Entry: byte0 low 7 bits = minute (float time x 1/60); byte1 low nibble = type, bit 4 = side; byte2 low 5 bits = squad slot. Types 0, 2, 3, 4 = goal; 1 = own goal; 9 = assist record (the next entry must be a type-0 goal on the same side); 10 = penalty-shootout goal (PK, slot -1); 5, 7, 8 and 12 are appended live and the result code skips them (it skips every type above 10 and types 5 to 8). Absolute addresses: entries at P + 0x6032, count at P + 0x74a8 (0x4920 + 0x2b88). Appender 0x776e0 is live (called from 0x775b8 for types 9 and 10 and from 0x1941c0 for types 5, 7, 8, 12) and refuses at 396 entries. Count is zeroed at match setup (0x76640). The match-end loop 0x2fa4-0x30e0 replays entries into `Goal`, `OwnGoal` and `PK`, and runs only when the field at 0x1d10 of the task is 0. | confirmed (code) |
| R + 0x2c54 (side), R + 0x2c58 (slot) = P + 0x7574, P + 0x7578 | 8 | two u32 | heap | Man of the match pick | Side (0 or 1) and slot (0 to 24) of the player with the highest float rating in the array at R + 0x2b8c (side stride 0x64, slot stride 4). Recomputed by the chooser at GAMEPRG 0x194c58 (strict greater-than from a running maximum of 0.0, so ties go to the lower side and slot; callers of the wrapper 0x1947f8 include 0x193a2c, 0x1940a4, 0x1940dc, 0x194564, 0x194654). Reset to 0 and 0 at 0x76498. At match end GAMEPRG 0x31f4-0x3208 calls `PlGiTask::SetMom(side, slot, 1)` (0x213838), which sets the PlGiTask player byte (see the per-player record row). | confirmed (code) |
| R + 4 (total), R + 0x14 + i*0x10 (side 0), R + 0x94 + i*0x10 (side 1), i = 0..7 | 4 per counter | u32 counters | heap | Ball possession counters | `match::StatisticTask` (0x1905c8) reads the word at `u32[u32[task + 0x5c] + 0x10]` (-1 means nobody) and runs only if that word masked with 0xfffeffff is below 11 (0x190608-0x190614). The low half is an on-pitch player index 0 to 10, the high half is a team id compared with `u32[P + 0x10c]` to pick the side. It then calls 0x76d78, which adds 1 to the side counter of the period row `u32[P + 0x891c]` (only if the row is below 8) and 1 to a per-player u32 at R + 0x108 + side*0x9c4 + player*0x64, and adds 1 to R + 4 (0x190640-0x190654). The function falls through at 0x190798 into the per-update minute check, so it runs on every update. The counters are therefore most probably ticks of ball-holding time, not discrete events (event versus tick is not proven). The accessor 0x78080 returns trunc(sum(side 0) * 100 / R+4), 100 minus that with the flag set, and 50 when R+4 is 0. It is probably the last of 11 rows of the post-match statistics screen (MES category 801, ids 1800 to 1811, last row "Ball Possession"; matched by row order, not by an id link in code). Updates in period rows 8 or more raise R + 4 but no side counter. Side 0 is the team whose id equals `u32[P + 0x10c]`. | confirmed (code) for the layout and the 0x78080 formula; empirical for "ticks" and the screen label |
| B + 0x32220 + side*0xc0 | 0xc0 per side | struct, arrays indexed by slot | heap | PlGiTask per-side stats block | u16[25] at +0x1a = rating x100 (`SetEval` 0x2119e8); u8[25] at +0x4c = yellows carried in from the career records (copied at 0x2126e8); u8[25] at +0x65 = yellows this match; u8[25] at +0x7e = red cards, including second-yellow reds; u8[25] at +0x97 = sent-off flag; +0xb0 = penalty-shootout goals (PK 0x2119a8, only when its last argument is non-zero); s8 +0xb1 = players on the pitch (reset to 11, red decrements it); s8 +0xb2 = minimum players (reset to 8); +0xb3 = substitutions left (reset from rule byte B + 0x24); +0xb4, +0xb8, +0xbc = goal, injury and card log pointers. `Card` (0x211610): type 0 does ++[+0x65+slot], and at 2 it resets to 0 and does ++[+0x7e+slot]; type 1 does ++[+0x7e+slot]. A yellow count of 0 can therefore mean a red. `GetCard` (0x2114a8) returns +0x4c + +0x65 as yellows. The block is cleared and rebuilt at each match start by `ResetGameIf` (0x212128). | confirmed (code) |
| B + 0x1e494 + side*0x7d0 + slot*0x50 | 0x50 per record | u8 fields | heap | PlGiTask per-player stats record | +0xa u8 minutes (`SetTime` 0x211a18; real match: the engine byte; simulated match: 45 or 90 for players with sim +0x1c set, otherwise 0); +0xb u8 played flag (start of the block `GetStatsPointer` 0x213868 returns); +0xc u8 second flag (sim: squad member; real match: played, or a helper 0x143f88 true); +0x4f u8 man of the match (`SetMom`, 0x213838 writes B + 0x1e4e3 + ...). All zero during the match. Written once at match end by GAMEPRG 0x3148-0x31d0 (real) or SIMPRG 0x1729ac-0x172a04 (simulated). The GAMEPRG teardown (0x2f70) skips the loop and `SetMom` if the field at 0x1d10 is non-zero. `PlGiTask::init` clears 0xfe0 bytes at B + 0x1e494. | confirmed (code) |
| log pointers at B + 0x32220 + side*0xc0 + 0xb4 (goals), + 0xb8 (injuries), + 0xbc (cards) | 12-byte goal records, 8-byte injury and card records | PlLinearClass log objects (0x1c bytes, heap) | heap | Goal, injury and card logs | Log object: +0 self pointer, +8 data pointer, +0xc capacity, +0x10 count, +0x14 element size (constructor 0x214308). Capacity per side: 9 goals, 3 injuries, 28 (0x1c) cards; when full, `add` (0x214140) clamps the count and keeps rewriting the last slot. Data buffers inside B: goals B + 0x323a0 + side*0x6c, injuries B + 0x32478 + side*0x18, cards B + 0x324a8 + side*0xe0. Goal record (0xc bytes): +0 u8 side, +1 s8 scorer slot, +2 s8 assist slot, +4 u16 scorer id (0xffff for an own goal), +6 u16 assist id (0xffff for none), +8 u8 period, +9 u8 minute. Own goals (`OwnGoal` 0x211900) are logged to the benefiting side with the own-goaler's id at +6. Card record (8 bytes): +0 side, +1 slot, +2 u16 id, +4 period, +5 minute, +6 type (0 yellow, 1 red; a second yellow is still type 0). Injury record: same shape, type +6 (0 gives flag 0x200, non-zero gives 0x100). Cards and injuries are appended live (`Card` from GAMEPRG 0x19cdc0, 0x19ce24, 0x19cec0, 0x19ed60, 0x19edac, 0x19ee64; `Injury` from 0x19cf78, 0x19d030, 0x19eefc, 0x19efa4). Goals are appended only after the final whistle by the GAMEPRG replay at 0x2f70 (and by SIMPRG 0x172588 for simulated matches). That replay passes period 0 for every goal. Shootout goals are not logged here: use the counter at side block +0xb0. Log objects are deleted and recreated by `ResetGameIf` each match. | confirmed (code) |
| B + 0x1fba0 + (copy*2 + side)*0x49a0 | 0x49a0 per team | PlTeamData | heap | Match squad copy, ids and flags | copy 0 is the working copy (side 0 at B + 0x1fba0, side 1 at B + 0x24540); copy 1 is the backup (side 0 at B + 0x28ee0, side 1 at B + 0x2d880); the accessor is 0x210198. Slot record at team + 0x20 + slot*0x2a0 (25 slots): s16 id at +0 (negative = empty), u32 flags at +0x20c. Flag bits: 0x200 set by `Injury` type 0, 0x100 set by non-zero type (they are mutually exclusive; light or heavy naming is not settled, see Unconfirmed); 0x800000 = sent off (set by `Card` when the red counter is non-zero: red card or second yellow). 11 slot-index bytes at team + 7 are the live XI, bench indices follow at team + 0x12 (`SwapPlayer` 0x2113b8). The side struct is at B + 0x1fa48 + 0xac*side (+0 live team, +8 stats block, +0xc backup). | confirmed (code) |
| G + 0x14 | 16 | struct | heap | Final result of the current game (GameResult) | +4 u32 end kind (from PlGiTask+0x80), +8 u32 flag (from PlGiTask+0x84), +0xc u8 home goals in periods 0 to 3, +0xd u8 home shootout goals, +0xe u8 away goals in periods 0 to 3, +0xf u8 away shootout goals. `plRec_GameResult2Win` (0x21e400) sums +0xc + +0xd and +0xe + +0xf, and returns 0 = home win, 1 = away win, 2 = draw. Forfeit path in `finalizeOneMatch` (0x203e18-0x203e20) writes 9 to +0xc and 0 to +0xe. Written at match end by GAMEPRG 0x116c through `CScheEuro::setCurrentGameResult` (0x205268), or by `ScheEuro_DummyGame` (0x208408) for background matches. The GAMEPRG write is skipped when the demo flag (B + 0x1f544) is non-zero or `GetScheEuro` (0x202bf8) returns null. `ResultClear` (0x2029b8) runs at each `initializeOneMatch`. | confirmed (code) |
| G + 0x24 (side 0), G + 0x150 (side 1); record = G + 0x24 + 0x12c*side + 0xc*slot | 0xc per record, 300 per side, 600 total | struct | heap | Per-player match records for the career | +0 u16 goals, +2 u16 assists, +4 u16 rating (zero unless played is 1; x100 scale unverified), +6 u8 played, +7 u8 club game, +8 u8 copied from PlGiTask+0x4f (man of the match, unverified as a 0/1 flag), +9 u8 reds, +0xa u8 yellows (a second yellow resets it to 0 and adds a red), +0xb unused. Zeroed at match start by `ResultClear`, all filled at once at match end by GAMEPRG 0x10e0 (`setCurrentGamePlayerRecord` 0x2052c0). Goals and assists are counted from the goal log by 0x1310, cards by 0x1398. `pwkTeam_AddPlayerRecord` (0x267d80, called from `finalizeOneMatch` at 0x203ec0) adds the records of the side whose team struct's first word is 1. Slot is the pidx of your club's PlTeamData. | confirmed (code) |
| block1 + 0xec88 + slot*0x11e + 0x4c + 0xe*type | 0xe per row, 5 rows | u16 x6, u8 x2 per row | heap | Career: Season Stats row | Row: +0 u16 goals, +2 u16 assists, +4 u16 games, +6 u16 club games, +8 u16 man of the match, +0xa u16 average points x100, +0xc u8 red, +0xd u8 yellow. Average = (old average * old games + rating) / new games (0 when games is 0). Type 0 to 4 comes from 0x267bf8 (a lookup in PlResource element 8; 5 means no update). Written by 0x267ca0 from `pwkTeam_AddPlayerRecord` for matches of the human club only. block1 = `u32[pwork + 0x1c] + u32[pwork + 0x28 + 4]`, pwork = `u32[0x3909a8]`; 0x267978 is `get(pwork, 1) + 0xec88`. Slot size 0x11e, 25 slots; the u16 at slot +0 is a played-history bit field (shifted left each match by 0x267d58, bit 0 set if played). | confirmed (code) |
| block1 + 0xec88 + slot*0x11e + 0xd8 + 0xe*type | 0xe per row, 5 rows | same as above | heap | Career: Career Stats row | Same row layout as the Season row, written by the same function 0x267ca0 (call at 0x267e0c). The slot's tables are at +8 (0x44 bytes), +0x4c (season), +0x92 and +0xd8 (career); the table at +0x92 is not written by `AddPlayerRecord`. | confirmed (code) |

### Pointer chains and stability

Two root pointers hold the PlGiTask buffer. `u32[0x390784]` is the
allocation (`bufer_alloc` 0x210070, `bufer_free` 0x2100c8, heap block
6). It is filled by `PwkCallbackCommand_Create` (0x110498, `bufer_alloc`
call at 0x1104c0), which `Pwk.Create` runs once at the start of
ROOTMAINSEQ. It is freed only by the delete callback (0x110548), which
sits behind a branch that never runs, so it is non-zero from boot on.
`u32[0x3906d8]` holds the same value only between `plGi_Create` and
`plGi_Delete`. For the stats block, the per-player record, the logs and
the squad copy the accessors read 0x390784, so those entries stay
readable after `plGi_Delete` until the next `plGi_Create` (which clears
the whole buffer). For the flags, gate on 0x3906d8 as a match-day
indicator. Both roots are static addresses in the PAL executable. The
buffer address is constant for the whole boot, but re-reading each
pointer on use is cheap and safe. P, R and G change every match.

- **PlGiTask pointer (0x3906d8).** Root: the static word. Valid when:
  `u32[0x3906d8]` is non-zero, from `plGi_Create` to `plGi_Delete`
  (`Sche.MatchStart` to `Sche.MatchEnd` of a match scheduled today, and
  the first-match setup). That covers the pre-match menu, the 3D match
  and the post-match screens. Not valid on the title screen, in menus
  on days without a match. A title attract demo creates one (tested in
  PCSX2: non-zero, with the demo and VS flags both 1). B equals `u32[0x390784]` at all times it is non-zero, so
  it is stable for the boot. `plGi_Create` is briefly non-zero while
  the buffer is still being cleared, so do not read contents on the
  first non-zero frame.
- **Demo and VS flags.** Root: B = `u32[0x3906d8]`; offsets 0x1f544 and
  0x1f548. Valid when: B is non-zero and `initializeOneMatch` has run
  for the current match (before that, `PlGiTask::init` has zeroed
  both). Stable across: written once per match, static during it,
  rewritten at the next match. Offsets are fixed.
- **Match object pointer P.** Root: `u32[GAMEPRG_base + 0x2490fc]`.
  Valid when: GAMEPRG's game module is alive (P non-zero, in 0x100000
  to 0x1FFFFFF). Allocated at module setup (GAMEPRG 0x2520 calls
  0x72060), freed at teardown (0x3330 calls 0x720a8). Outside a match
  the cell holds other overlay data (SIMPRG sits at the same 0xc75000
  base in a career), so the value is junk, not null: check a mode
  indicator first (the module slot of `Game(6)` at 0x5698e8 in the
  module activity table, which is also non-zero in demo and VS
  matches, paired with the demo flag at 0x34d43c), then that
  `u32[R + 0]` equals P (0x76410 stores P at R + 0; from code). Stable
  across: frames, half-time and extra time; not across matches (new
  object, counters restart at 0).
- **Goals per side.** Root: P; R = P + 0x4920; goals(side) = sum of
  `u8[R + 8 + side*0x80 + i*0x10]`, i = 0..7. Valid when: P is live.
  Stable across: frames and extra time; reset by 0x76410 at match
  (re)initialisation. Valid up to match end (`SetGameScore` reads them
  at 0x14cb48). Each u8 cannot overflow in practice.
- **Live per-player minutes, played, goals.** Root: P; record =
  R + 0x10c + side*0x9c4 + slot*0x64 (equals P + 0x4a2c + ...); goals
  at +3 (P + 0x4a2f + ...). Valid when: P is live, until teardown
  (0x720c0) frees the object; results then live in PlGiTask. Slot 0 to
  24 and side 0 or 1 in teardown order; bench slots accrue minutes only
  after entering. Stable across: frames, pauses, half-time,
  substitutions; minutes change once per clock minute.
- **Event log.** Root: P; count `u16[P + 0x74a8]`, entry k at
  P + 0x6032 + 3*k. Valid when: P is live. Append-only within a match;
  the count only grows and resets to 0 at the next match. Not stable
  across matches or screens.
- **Man of the match pick.** Root: P; `u32[P + 0x7574]` side,
  `u32[P + 0x7578]` slot. Valid when: P is live and after the chooser
  has run; before that, and after the reset at 0x76498, both read 0,
  which looks like side 0 slot 0. A non-zero byte at
  B + 0x1e4e3 + side*0x7d0 + slot*0x50 after `SetMom` is a more robust
  latch. Not stable across matches.
- **Possession counters.** Root: P; R + 4 and the counters above. Valid
  when: P is live (also while the post-match statistics are up).
  Counters are non-decreasing between resets; 0x76410 zeroes them at a
  new match. Check that side 0 plus side 1 is at most the total.
- **PlGiTask per-side stats block.** Root: `B = u32[0x390784]`; block =
  B + 0x32220 + 0xc0*side. Valid when: B is non-zero (from boot on).
  Test: `u8[block + 0xb1]` is in 0 to 11. Cards update live; ratings
  are written at match end (GAMEPRG 0x31b4, SIMPRG 0x172938). Values
  persist after the match until the next `ResetGameIf`. The buffer
  holds no meaningful data outside a match day.
- **PlGiTask per-player record.** Root: B = `u32[0x390784]`
  (preferred) or `u32[0x3906d8]`; record = B + 0x1e494 + side*0x7d0 +
  slot*0x50. Valid when: read after the match-end write and before the
  next `plGi_Create`. Zero during the match. Career flow only (both
  `plGi_Create` callers are career schedule code); VS and other modes
  unverified.
- **Goal, injury and card logs.** Root: B (as above), log pointer at
  B + 0x32220 + 0xc0*side + {0xb4, 0xb8, 0xbc}, then `u32[log + 8]`
  data, `u32[log + 0x10]` count (`u32[log]` equals log, so no extra
  dereference is needed). Valid when: the logs were recreated for this
  match by `PreMatchRun` (0x213ecc, `ResetGameIf`). Read goals after
  state 0x190 equals 8 (the replay at 0x2f70 has run). Log pointers
  change every match; the data buffers keep fixed offsets from B.
- **Match squad copy.** Root: B = `u32[0x390784]`; team = B + 0x1fba0 +
  0x49a0*(side + 2*copy). Valid when: B is non-zero, during or just
  after a match. `SetTeamData` (0x210a04-0x210a18) fills the copies at
  match set-up; they stay stale afterwards. No code-confirmed in-match
  flag was found, so gate on another indicator. Changes only when
  `Injury`, `Card` or `SwapPlayer` runs.
- **GameResult.** Root: S = `u32[0x390650]` (`CreateScheEuro` 0x202a50
  stores it, `DeleteScheEuro` 0x202ba8 zeroes it); G = `u32[S + 0x414]`
  (0x2a4-byte block allocated in the `CScheEuro` constructor 0x202c08);
  result = G + 0x14. Null-check both hops. Valid when: a `CScheEuro`
  exists (career, the opening playoffs, VS mode and the title attract
  demo), after GAMEPRG 0x116c has written it, until the next
  `initializeOneMatch`. Before the first match it holds the
  constructor default (u8 at +0 is 3, goals 0). Stable across: menus,
  turns and matches in one career session; the heap addresses may
  change when a career is left and entered again.
- **Per-player match records.** Root: S and G as above; record =
  G + 0x24 + 0x12c*side + 0xc*slot. Valid when: a career is loaded (S
  and `u32[S + 0x414]` non-zero). Zero from `initializeOneMatch` until
  the match-end copy by GAMEPRG 0x10e0, then valid until the next
  `initializeOneMatch`. Skipped when the demo flag is non-zero.
  CPU-versus-CPU and simulated user matches do not pass through GAMEPRG
  0x10e0; their writer was not found.
- **Career statistics.** Root: pwork = `u32[0x3909a8]`
  (`plPwork_GetPwork` 0x21d6e0); block1 = `u32[pwork + 0x1c] +
  u32[pwork + 0x28 + 4]`; slot = block1 + 0xec88 + 0x11e*slot. Valid
  when: the career data exists (pwork is created once per boot by
  `Pwk.Create`, so `u32[0x3909a8]` is non-zero from boot, but its
  blocks hold data only after New Game or Load) and after
  `finalizeOneMatch` (0x203dd8, call at 0x203ec0) ran for a match of
  the human club. Block1 is a heap block (heap 6, allocated in the
  `PlPworkTask` constructor 0x21d6f0). The block order is shuffled once
  in that constructor (0x235270). The block base is therefore fixed for
  the whole boot, and `prepareExtWork`, `deleteExtWork` and
  `switchExtWork` never move it in retail. Whether the offset is the
  same on every boot is not shown (see Still unknown). It is a live
  value, not a save copy.

### RetroAchievements notes

- **Mode check first.** Read `u32[0x3906d8]`. Only follow B when it is
  non-zero, because stale contents stay readable after `plGi_Delete`.
  Pair it with the demo flag (B + 0x1f544) equal to 0 and the VS flag
  (B + 0x1f548) equal to 0 for "career match". Read the flags only
  after the match has started: they read 0 between `plGi_Create` and
  `initializeOneMatch`. `CScheEuro_FirstPromote` matches (the opening
  playoffs of a new game) also read 0 for both flags, so "both zero"
  does not separate them from regular career matches. The "demo is the
  title attract match" meaning is unverified, so test attract mode and
  VS mode in a run before relying on it.
- **Overlay pointer checks.** For anything under P, first confirm a
  match module is running (a mode indicator from another entry), then
  require P to be non-zero, in 0x100000 to 0x1FFFFFF, and `u32[R + 0]`
  equal to P. Outside a match the cell can hold SIMPRG data. The base
  0xc75000 is observed, not proven; the Japanese release needs its own
  addresses (`gamever.py`).
- **Goals live.** Sum the 8 u8 counters per side at
  R + 8 + side*0x80 + i*0x10 and compare with the previous frame. For
  scorer-level conditions compare the u8 at
  R + 0x10f + side*0x9c4 + slot*0x64 (own goals excluded). For minute,
  type or assist details use the event log: compare the u16 count at
  P + 0x74a8 with its previous value, then read entries from the old
  count. Check the type nibble: types 5, 7, 8 and 12 also advance the
  count and are not goals. Count a type 9 entry together with the
  following type-0 entry, and note a type 9 can be visible for a frame
  before its goal arrives.
- **After the final whistle.** Goal log records and the PlGiTask
  per-player record (minutes, played, man of the match) are written
  once at match end, so do not poll them during play. Use the
  GameResult (G + 0x14) for win, draw or loss with
  `plRec_GameResult2Win` semantics (0 home, 1 away, 2 draw), and sample
  it when the post-match screen opens. A 0-0 draw leaves the bytes
  unchanged from the cleared default, so pair a result check with a
  screen or mode indicator or a transition of another value. The
  match-end write is skipped when the demo flag is non-zero.
- **Cards and injuries.** These are live in the PlGiTask block and
  logs. Use `u8[block + 0x7e + slot]` for red cards (a second yellow
  also lands there) and the sum +0x4c + +0x65 for yellows, because a
  yellow count of 0 can mean a sent-off player. The flag 0x800000 at
  record + 0x20c means sent off. For injuries, treat a set 0x100 or
  0x200 bit as "a match injury was reported" until the light and heavy
  naming is settled. Logs hold at most 9 goals, 3 injuries and 28 cards
  per side.
- **Man of the match.** The live pick at P + 0x7574 and P + 0x7578
  reads 0 and 0 when unset, so it is ambiguous with side 0 slot 0.
  Prefer the byte at B + 0x1e4e3 + side*0x7d0 + slot*0x50 after the
  final whistle.
- **Which side is the player.** Side 0 and 1 are probably home and
  away, and which one is the human club is not shown by these records.
  The career statistics and `pwkTeam_AddPlayerRecord` only count the
  side whose team struct's first word is 1.
- **Possession.** The counters most probably tick once per update while
  a player holds the ball, so use them as a ratio (the 0x78080 formula)
  and not as seconds. Do not trigger on small absolute values.
- **Career totals.** Compare the Season row
  (block1 + 0xec88 + slot*0x11e + 0x4c + 0xe*type) or Career row
  (+ 0xd8) between matches. They change only when `AddPlayerRecord`
  runs for a human-club match whose competition maps to type 0 to 4.
  Do not read them mid-match. Whether stats follow a player when squad
  slots change is unverified, so prefer per-match deltas over absolute
  totals.
- **Pitfalls.** P, R and G move between matches, so read each chain
  every frame. The substitutions-left byte (+0xb3) is not shown to fall
  on a substitution (`DecSpare` has no caller), so do not build a
  substitution trigger on it. Simulated matches write the per-player
  record with 45 or 90 minutes, unlike the engine byte of real
  matches.

### Unconfirmed

Do not rely on these.

| Item | Why it is unconfirmed |
|---|---|
| Match clock float at P + 0x8908 | Empirical: the minute byte compared at GAMEPRG 0x1907a8-0x1907c0 is this float times 1/60 (0x3c888889), and the period table is in seconds, so the unit is game seconds (0.0 at kickoff, 2700.0 = 45:00 up to 7200.0). The controller task keeps its own timer at task+0x6c, loaded from the float at start (0x16650c), advanced each frame by task+0x70 divided by the vsync multiplier times 59.94 (0x1667a4-0x1667b4), and copied back to the float (0x166880). The float is also stored and zeroed at several phase changes (0x166f9c, 0x167000, 0x16711c, 0x1671d0, 0x167848, 0x16ba64, 0x16bafc, 0x16bbe0). Whether it stops during dead balls, replays and half-time is not known. Do not use it as the match time until a live dump settles the reset behaviour. `PlGiTask+0x1f540` is only a half-time snapshot and is not live. |
| Possession counters as time or as events | The layout is confirmed, but whether they tick once per update (time-like) or once per ball-holder change was not run. The update-per-call reading rests on `StatisticTask` falling through into the per-update minute check. |
| Per-player possession u32 at R + 0x108 + side*0x9c4 + player*0x64 | The index is the on-pitch index 0 to 10. Whether it equals the squad slot used by the minute and goal bytes (the minute code maps the index to a slot through 0x73ea8) is not shown. |
| "0x100 light injury, 0x200 heavy injury" | Reversed in code (type 0 gives 0x200, non-zero gives 0x100, and `DOC/INJURIES.md` calls type 0 light). The light and heavy naming is unverified. Use the bit values only. |
| Rating default 550 for starters and floor 500 | Not rechecked. |
| "Rating x100" scale of the per-player record | Not confirmed in code; only that it matches the unit of the career average. |
| Demo flag as the title-screen attract match | Not traced: only that the flag can be non-zero in the VS schedule class, set by a runtime-selected-competition regulation flag. |
| Substitutions left falling at +0xb3 means a substitution | Not shown: `DecSpare` has no caller; +0xb3 is set through `SetSpare` (GAMEPRG 0x14cb14). |
| `*0x249100` versus `*0x2490fc` | The exported `fb::MatchManager$_instance` cell at GAMEPRG + 0x249100 is a separate cell. Whether it holds the same pointer was not checked. |
| An alternative cache of the same pointers (R at `u32[MatchManager + 0x60]`, P at `u32[MatchManager + 0x58]`, MatchManager = `u32[base + 0x249100]`) | Reported by one reviewer and not cross-checked. |

Claims found wrong in the first draft and corrected above: a goal writer
at 0x77c00 (no caller; the live writer is 0x767b0), 0x390784 as a match
flag, B = `u32[0x3906d8]` as the root of the stats block (the accessors
read 0x390784), the squad backup at "+0x49a0" (it is +2 * 0x49a0), goal
log periods of 0 to 3 and shootouts (the replay passes period 0), log
capacities 0x12, 8 and 0x12 (they are loop bounds; the capacities are 9,
3 and 28), man of the match "set at match end only" (it is recomputed
during play), possession "event counts, not time" (not supported, see
above), and the demo and VS flag clear addresses (demo is 0x210ff0, VS is
0x210ff4).

### Still unknown

- Is the GAMEPRG.REL load base always 0xc75000? It is heap block 2
  (0x305000 bytes), and the exact start of the block was not derived.
  The registry at 0x35ed98 gives it at run time.
- Does `*0x249100` equal `*0x2490fc`, and what is the class behind the
  0x2490fc cell?
- Which byte columns of the table at R + side*0x80 + row*0x10 are shots,
  shots on target, corners, free kicks, penalties, fouls, offsides,
  yellow cards and red cards? The statistics screen reads sibling
  accessors 0x77cb0 to 0x77ed0 over the bytes +8, +9, +0xa, +0xb, +0xc,
  +0xd, +0xf, +0x10 and +0x11, and MES category 801 ids 1800 to 1811
  list the screen rows in order, but no link from id to row was found.
  The per-player 0x64 record fields (+0x111, +0x112, +0x134, +0x138,
  +0x13e, +0x148, +0x14a, +0x152 to +0x15e) are unnamed.
- What do the event types 2, 3, 4 and 5 to 8 and 12 stand for (free
  kick, header, penalty)? Types 0, 2, 3 and 4 all replay as ordinary
  goals. Which of them is written by the goal writer was not traced
  (only the writers of types 5, 7, 8, 9, 10 and 12 were).
- Is the side bit of a type-1 (own goal) event the own-goaler's team or
  the credited team?
- Do the possession counters tick per update or per ball-holder change,
  and is the on-pitch index the squad slot?
- Where do the live per-player rating floats at R + 0x2b8c come from
  and when do they update? The teardown stores rating x 100 with
  `SetEval`. What do the side-selection word at obj + 0x891c + 0x498
  and the state word obj + 0x891c (values up to 0xb, compared with 7
  and 0xb at 0x194728) mean as a "match over" test?
- Does the clock float stop during dead balls, replays and half-time
  (see Unconfirmed)? What is the meaning of `OfficialsTask+0x70`? What
  do the phase codes 1 to 8 mean?
- What do `PlGiTask+0x6c` (`GetMatchGrade`), +0x7c (`GetTimeMode`),
  +0x1f488 (period) and +0x1f54c (display kind) indicate, for example
  league versus cup, or extra time allowed?
- What writes the "player joined" marker tested by `IsJoin` (u16 at
  stats + 0x1a + 2*slot), and is a non-zero rating the played marker
  for substitutes?
- Does a VS match the player starts create a PlGiTask? (The title attract
  demo does: tested in PCSX2.) Only two `plGi_Create` call sites exist in
  the executable; overlays were not scanned. What does the demo flag
  imply for matches that are not recorded?
- Who calls the per-match reset functions 0x190e18 and 0x77c00, and does
  the post-match `MatchMenu` run before B is cleared? Whether goal logs
  stay valid until `deleteGameInterFace` is not shown.
- Which screen entry calls the function at GAMEPRG 0x9150 that refreshes
  the score words (+0x1faf0, +0x1fb9c), so when are they final?
- What do the time-segment rows at R + 0x134 to R + 0x158 of the match
  object and `PlGiTask+0x7c` mean?
- Which writer fills the per-player match records for CPU-versus-CPU and
  simulated matches, and does the game keep any "played" or minutes data
  for those?
- What is the exact unit of the live minutes byte (R + 0x10c + ...) and
  the meaning of record +2?
- Is the pwork block order (and so every career block base) the same on
  every boot? The shuffle draws from the generator state at 0x569dc0,
  which starts as a constant, but other draws before `Pwk.Create` were
  not ruled out. Do not hard-code block offsets until two boots agree.
- Season rollover: is the Season table (0-based table 1) cleared and
  moved into table 2 at year end? What are the competition types 0 to 4
  (pre-season, domestic league, overseas league, Euro, international is
  empirical only), and do stats follow a player when squad slots
  change?
- Do penalty-shootout kicks count in the per-player goal byte or the
  side goal counters? Do StadiumViewer (171) and ShimizuTest (173)
  allocate the match object?
- Which side is the human club inside PlGiTask (`GetOperator` 0x211d38,
  byte + 0x8a + side, is documented in `DOC/BPB_FORMAT.md`), and is
  side 0 the home side?
- The Japanese release has its own offsets; none of these were checked
  with `gamever.py`.

### Checking the claims

Each command was run on the PAL files. The first two show the demo and
VS flag stores in `PlGiTask::init` (0x7544 at 0x210ff0, 0x7548 at
0x210ff4) and in `initializeOneMatch` (0x7548 at 0x203d7c, 0x7544 at
0x203d98).

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x210ff0 2
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x203d78 12
```

The goal counter writer: `u8[R + 8 + (row << 4) + (side << 7)]` is
incremented and the scorer byte at +0x10f only when the own-goal flag is
0.

```bash
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x767b0 30 --sles ISO/SLES_541.51
```

The match-end sum of both sides into `SetGameScore` (0x214070):

```bash
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x14cb40 20 --sles ISO/SLES_541.51
```

The possession update: the ball-holder word test below 11 at 0x190610,
the side compare against `u32[P + 0x10c]`, the `R + 4` increment at
0x190648-0x190654, and the fall-through into the minute check.

```bash
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x1905f8 30 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x1907a8 8 --sles ISO/SLES_541.51
```

The result decision (0 home, 1 away, 2 draw) and the match-day gate
(`plGi_Create` stores B at 0x6d8 + 0x390000 = 0x3906d8):

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis plRec_GameResult2Win
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x210918 6
```

## Tested in PCSX2

Nexxus's report, 2026-11-15: five save states of a career match flow
(pre-match screen, kick-off, two minutes in, loading, quick mode) and
two of the title attract demo, read from `eeMemory.bin` with the chains
above. The whole of the table's PlGiTask part held where it could be
checked. `RAM_MAP.md` has the full ten-state table.

| Row | Read | Result |
|---|---|---|
| PlGiTask pointer 0x3906d8 | 0 on the init, title and demo-movie screens, 0x1f06f90 on the pre-match screen, in all career match states and in both attract-demo states | as documented, and equal to [0x390784] |
| Demo flag (P + 0x1f544), VS flag (P + 0x1f548) | 0 and 0 in every career state, 1 and 1 in both attract-demo states | as documented: the demo is a VS match with the demo flag set |
| Team ids (P + 0x1fba0, + 0x24540) | 182 and 1 in the career match (the player's club is id 1, the second side); 130 and 87 in the demo | the career ids fit; the demo ids are not in the 543 to 558 range the table gave for VS teams (a VS match the player starts with a custom team read 543 and 13, so the range does hold for those) |
| Competition (P + 0x1f920), UID (+ 0x1f480, + 0x1f924), grade (+ 0x6c) | 22, 38, 38 and 2 in the career match; 56, 148, 148 and 5 in the demo | as documented; the static copy at 0x5eacb0 and 0x5eacb4 read 38 and 2, and 148 and 5, and -1 and -1 after the demo |
| Result type and period (P + 0x84, + 0x80) | 0 and 1 in every state | the values the table gives for a match that has not ended |
| Final score (P + 0x1faf0, + 0x1fb9c), game time copy (+ 0x1f540), shoot-out goals (+ 0x322d0, + 0x32390) | 0 | as documented for a match with no hand-over yet |
| GAMEPRG base and G | the base is 0xc75000 in all six states that had GAMEPRG loaded, G = [base + 0x2490fc] is 0x1c0de90 in all six | the registry scan and the G pointer work; G exists in the loading state too |
| Match clock (G + 0x8908) | 0.00 at kick-off and in the loading state, 123.75 two minutes in, 146.25 in quick mode | a float of elapsed seconds, as documented |
| Goal tally (G + 0x4920 ...) and state word (G + 0x891c) | 0 in all six | nothing was scored; the state word was only seen at 0 |

### Eight states of one career match

Nexxus's report, 2026-11-16: eight more states of a single career match
(club id 1 against team 182, UID 38, competition 22, grade 2), read the
same way. The states were taken at the start, just before a goal, just
after it, on the half-time result screen, on the half-time tactics
screen, at the final whistle, on the full-time result screen and on the
post-match screen. All eight pass `ramcheck.py check` with 0 problems.
The second half was not sampled, so no state shows a clock between
2700 and the final whistle.

| State | Clock (G + 0x8908) | State word (G + 0x891c) | Tally (side 0 - 1) | Score words (P + 0x1faf0, + 0x1fb9c) | Game time copy (P + 0x1f540) |
|---|---|---|---|---|---|
| Start | 308.18 | 0 | 0-0 | 0-0 | 0 |
| Just before a goal | 2606.36 | 0 | 0-0 | 0-0 | 0 |
| Just after the goal | 2700.00 | 1 | 1-0 | 0-0 | 0 |
| Half-time result screen | 2700.00 | 2 | 1-0 | 0-0 | 0 |
| Half-time tactics screen | 2700.00 | 2 | 1-0 | 1-0 | 2700 |
| Final whistle | 0.00 | 11 | 1-0 | 1-0 | 2700 |
| Full-time result screen | 0.00 | 11 | 1-0 | 1-0 | 2700 |
| Post-match screen | no engine | no engine | no engine | 1-0 | 2700 |

What it shows (empirical, one match):

- **The live tally works.** One goal moved the side 0 sum from 0 to 1
  in the state taken just after it. The first score word agrees with
  side 0 once it is written, so the two use the same side order. Which
  club is side 0 was not read: the player's club is the second team id,
  so this goal may have been the opponent's.
- **The score words are written at the half-time tactics screen.** They
  still read 0-0 on the half-time result screen, with the tally already
  at 1-0, and read 1-0 on the tactics screen that follows. The game time
  copy changes from 0 to 2700 at the same moment. This settles that the
  hand-over at GAMEPRG.REL 0x9150 runs when the tactics screen is set
  up at half time. It did not run again at full time in this match: the
  copy stayed 2700 through the final whistle and both later screens,
  and a refresh at full time would have stored the clock it found
  (0.00). Whether a goal scored after half time reaches the score words
  was not measured, so do not treat them as the final score yet.
- **The score words survive the engine.** On the post-match screen the
  Game module is no longer active, the engine chain no longer resolves
  (no GAMEPRG match in the registry, so no G) and the static group
  mirror at 0x5eacb0 and 0x5eacb4 has gone to -1 and -1, but the
  PlGiTask pointer is unchanged and the score words and the copy still
  read 1-0 and 2700. Latch the tally before the engine goes.
- **Result type and period stayed 0 and 1** for the whole 90-minute
  match, goal included, as the table says ("a goal in normal time never
  changes it").
- **The state word has more values than the one before kick-off.** 0
  in play, 1 straight after the goal, 2 on both half-time screens and 11
  at the final whistle and the full-time result screen. What each value
  means is not settled by this: the state word changed at the goal as
  well as at the break.
- **The clock is not a full-time reading.** It stopped at exactly
  2700.00 from the goal through half time (the goal state was already at
  the period limit, 94 seconds after the state before it) and it read
  0.00 at the final whistle, so it was reset, not run on to 5400.
- The first state's clock (308.18) is the match some minutes in, not 0.
  The state was taken after kick-off, so it says nothing about the clock
  at kick-off.

### Five states of a second career match

Nexxus's report, 2026-11-16: five states of another career match (the
same club, team 182 against club 1, UID 38), from the second half on:
the start of the second half, just before a goal, just after it, in
injury time and after the final whistle (slots 1 to 5). All five pass
`ramcheck.py check` with 0 problems.

| State | Clock | State word | Tally (side 0 - side 1, by slot) | Score words, copy | G + 0x8910 |
|---|---|---|---|---|---|
| Start of the second half | 2788.56 | 2 | 2 (slot 0) - 1 (slot 0) | 0-0, 0 | 127.54 |
| Just before the goal | 5400.00 | 3 | same | 0-0, 0 | 127.54 |
| Just after the goal | 5400.00 | 3 | 2 - 1 (slot 0) and 1 (slot 3) | 0-0, 0 | 150.04 |
| Injury time | 5400.00 | 3 | same (2-2) | 0-0, 0 | 150.04 |
| After the final whistle | 0.00 | 11 | same (2-2) | 0-0, 0 | 0.00 |

What it shows (empirical, one match):

- **A goal in injury time goes into tally slot 3**, the row of the state
  word at that moment, as the segment model says. Side 1 scored it, so
  the match ended 2-2 by the tally.
- **The clock is pinned at the period limit in injury time.** In the three
  states with the state word at 3 it read exactly 5400.00, before and
  after the goal, so it does not run on past 5400 here. The same
  happened in the first career match (2700.00 at state 1), in the VS
  match (5400.00 at state 3, 6300.00 at state 5). The clock is therefore
  not a way to read the minute during added time.
- **The score words stayed 0-0 and the copy 0 through the second half and
  at the final whistle**, with a 2-2 tally. In this match they were never
  written. In the first career match they were written at the half-time
  tactics screen. In this match Nexxus skipped past the half-time
  result screen and went straight to the second-half kick-off (2-1 at
  half-time), so the tactics screen was never shown. The words therefore
  depend on that screen being entered, and a match that skips it never
  gets them.
  They do not catch up at full time. The tally is the score.
- **Most likely the tactics screen's own copy of the score and time.**
  Nexxus's reading: the words exist to show the result on the half-time
  tactics screen. That fits everything seen. Their writer is in that
  screen's set-up, they were filled when the screen was entered and never
  when it was skipped, and a VS match, with no such screen, never filled
  them. It is not shown from the code: no caller of `GetGameScore`
  0x2140a0 or `GetGameTime` 0x33c390 was found (`snr2.py xref` on
  GAMEPRG, SIMPRG, VSPRG and YRSTPRG found none), so the screen that
  reads them is not identified.
- **Possible added-time fields.** G + 0x8910 rose by 22.5 (127.54 to
  150.04) with the goal, as a total of lost time would. G + 0x8918, a
  float that rose from state to state (about 7586, 14767, 14800, 15060
  and 15967), kept counting while the clock was pinned. Neither is
  confirmed as the added time or a timer.

### Ten states of a VS match

Nexxus's report, 2026-11-16: five states of a VS match started from the
menu with a custom team (slots 1 to 8, taken after the eight above had
been read and then overwritten): the intro, the start, just after a
second-half goal, just after a second-half equalizer, in added time, and
three in extra time of the same match (first half of extra time just
started, a free kick, a goal), the final whistle and the final screen.
All ten pass `ramcheck.py check` with 0
problems.

| State | Clock | State word | Tally per slot (side 0 / side 1) | Score words, game time copy |
|---|---|---|---|---|
| Intro | 0.00 | 0 | none | 0-0, 0 |
| Start | 88.96 | 0 | none | 0-0, 0 |
| Second-half goal | 2964.55 | 2 | side 1 slot 2 = 1 | 0-0, 0 |
| Second-half equalizer | 5195.41 | 2 | side 0 slot 2 = 1, side 1 slot 2 = 1 | 0-0, 0 |
| Added time | 5400.00 | 3 | same | 0-0, 0 |
| Extra time, first half just started | 5430.38 | 4 | same | 0-0, 0 |
| Extra time, a free kick | 6300.00 | 5 | same | 0-0, 0 |
| Extra time, a goal | 6300.00 | 5 | side 0 slot 2 = 1 and slot 5 = 1, side 1 slot 2 = 1 | 0-0, 0 |
| Final whistle | 0.00 | 11 | same (2-1) | 0-0, 0 |
| Final screen | no engine | no engine | no engine | 0-0, 0 |

What it shows (empirical, one match):

- **A VS match the player starts has its own flags and ids.** The
  PlGiTask pointer is 0x1f06f90, the demo flag (P + 0x1f544) is 0 and the
  VS flag (P + 0x1f548) is 1, the script flag 0x34d43c is 0, and the
  schedule object's mode vtable is 0x406a68 (VS). The team ids are 543
  (the custom team, the first word) and 13, the competition is 56, the UID
  148 and the grade 5, and the static group mirror reads 148 and 5. These
  are the same competition, UID and grade as the title attract demo, so
  those three do not tell a VS match from the demo; the demo flag does
  (1 in the demo, 0 here). The BPDATA pointers are 0, as in every 3D
  match.
- **The state word is the period segment.** The tally row a goal goes
  into is the state word at the time of the goal: the second-half goals
  are in slot 2, the first-half goal of the career match above is in slot
  0, and the word reads 0 in the first half, 1 at the end of the first
  half (the career match's 2700.00 state), 2 in the second half and 3 at
  90:00 with the clock at exactly 5400.00. This matches the period-end
  table (2700, 2700, 5400, 5400, 6300, 6300, 7200, 7200, slots 0 to 7).
  The word was also 2 on the half-time screens and 11 at the final
  whistle of the career match.
- **Both sides score into the tally.** The goal made it 0-1 (side 1) and
  the equalizer 1-1 (side 0), and the sums of the 8 bytes per side give
  the score. Which side is home was not read.
- **The score words and the game time copy stayed 0-0 and 0 in the whole
  VS match**, second-half goals included. In the career match they were
  written at the half-time tactics screen. Either no tactics screen was
  entered in this VS match (it may have been skipped) or it does not run
  that hand-over. So the score words are not reliable in either mode:
  use the live tally.
- The clock read 2964.55 in the second half and 5195.41 later, on the
  90-minute scale, so it runs through the second half and was not reset
  at half time here.

- **Extra time follows the same segment model.** The state word is 4
  just after the break at 5400 (clock 5430.38, so the clock runs on from
  5400 and was not reset) and 5 at 6300.00, the end of the first half of
  extra time. The extra-time goal went into side 0 slot 5, the row the
  word held, so the goal made it 2-1 by the tally sum. The words stayed
  0-0 and 0 again.
- **The result type and period (P + 0x84, + 0x80) stayed 0 and 1 after
  an extra-time goal.** The table gives 1 after such a goal (`Goal`
  0x211830, when period - 2 is below 2), so those writers did not run
  yet. They are most likely written with the other end-of-match events,
  as the shoot-out bytes are (still 0 and 0 here), so neither is live in
  extra time. Read them after the match, not during it.

- **The VS match's end looks like the career match's.** At the final
  whistle the state word is 11, the clock 0.00 and the tally still 2-1,
  under the Game module. On the final screen the module table shows
  SimRoot (24) and MatchMenu (35), the engine chain no longer resolves,
  the group mirror is -1 and -1 and the BPDATA pointers are non-zero
  again (0xb54b10 and 0x1137e80). The match pointer, the team ids 543
  and 13, the VS flag 1 and the schedule object (VS mode) are unchanged.
- **In this VS match the score words never left 0-0.** They read 0-0, the
  game time copy 0, and the result type and period 0 and 1 at the final
  whistle and on the final screen, with a 2-1 tally and extra time
  played. So a VS match never handed its score to the PlGiTask words
  (at least when the half-time tactics screen is not shown), and a
  0-0 there says nothing. The live tally is the only score source seen
  working in both modes, and it must be latched before the engine goes.

- **The VS mode hub screen (one more state, taken before the match).**
  The match pointer 0x3906d8 is 0, the group mirror -1 and -1, the demo
  flag 0, and only SimRoot (24) is active in the module table (no
  MatchMenu). The schedule object already exists in VS mode (vtable
  0x406a68, address 0xb56990, the one the match then used) and the BPDATA
  pointers are non-zero (0xb54b10 and 0x1137e80). The overlay registry
  holds SIMPRG at 0xc75000 and VSPRG at 0x1105800. So the VS menus can
  be told apart from a career menu by the VS-mode schedule object, and
  the match pointer stays the gate for a match.

Not measured: the second half of extra time, and whether the score words
hold a second-half goal in a match where the tactics screen was shown
(the second career match above skipped past the half-time screens and
never got them).

### Ten states of a shoot-out

Nexxus's report, 2026-11-16: ten states of a second VS match (slots 1 to
10, taken after the VS states above had been read and then overwritten),
all in the shoot-out: the start, kicks 1 to 8 one state each, and the
shoot-out result. All ten pass `ramcheck.py check` with 0 problems. The
match had one goal per side, both in the first half (tally slot 0), and
went straight to the shoot-out.

| State | Clock | State word | Tally | Score words, copy | Result type and period | Shoot-out bytes (P + 0x322d0, + 0x32390) |
|---|---|---|---|---|---|---|
| Shoot-out start | 0.00 | 8 | 1-1 (slot 0 each) | 0-0, 0 | 0 and 1 | 0 and 0 |
| Kicks 1 to 8 | 0.00 | 8 | 1-1 | 0-0, 0 | 0 and 1 | 0 and 0 |
| Shoot-out result | 0.00 | 11 | 1-1 | 0-0, 0 | 0 and 1 | 0 and 0 |

What it shows (empirical, one match):

- **The state word is 8 for the whole shoot-out** and 11 once it is over
  (the same value as at the end of a normal match). Value 8 is past the
  eight tally rows, which the tally writer ignores, so no kick is added to
  the tally: it stayed 1-1.
- **Nothing in the PlGiTask buffer moved.** A diff of the whole 0x40000
  bytes at the match pointer across the ten states found no change at
  all. The result type and period stayed 0 and 1 and the shoot-out bytes
  0 and 0 through the kicks and on the result screen (the Game module was
  still active), so the table's `PK` writers have not run by then. They
  are written after this point (or only in matches whose result is
  recorded), so do not read a shoot-out from them while the match runs.
- **The kicks live in the engine object, not decoded.** Across the ten
  states 222 dwords of the engine object changed. The ones with small
  values include G + 0x10c, which went 1, 1, 0, 1, 0, 1, 0, 1, 0, 0
  (alternating from kick 1 to kick 7, then 0), G + 0x8b80 and + 0x8b84
  (alternating 0 and 1 in step) and G + 0x8b88 and + 0x8b8c (values such
  as 20, 22, 6, 7, 21, 10, 9, perhaps kicker indices). None is a running
  count of goals, and what each means is not settled.
- **At the result the Game module is still active.** The shoot-out
  result state is not a result screen; the end screens were seen in the
  VS match above.

## Still unknown

The five questions that matter most for a tool or an achievement set.
Each section keeps its own full list (the "Still unknown" part at the
end of "Match core state" and of "Match events and statistics" above);
the shorter questions are only there.

- Is the GAMEPRG.REL load base stable? 0xc75000 was seen in single
  PCSX2 tests, but the overlay sits in a heap block whose start was not
  derived, and the registry scan at 0x35eda0 was never run in a live
  game. Until it is, find the base through the registry and do not
  hard-code it. Both sections list this; the first one also asks whether
  an overlay can be moved at run time.
- Is there one clean signal for "kick-off taken", "ball in play" and
  "full time"? The PlGiTask pointer at 0x3906d8 spans the whole match
  day, and the match engine object lives for the whole GAME_MODULE,
  pre-match and post-match screens included. The engine's state word
  (values 0 to 0xb) and the live period were not decoded. The first
  section's list has the details; a PINE watch around one match would
  settle it.
- When is the final score final, and what does it include? The words
  written by `PlGiTask::SetGameScore` were written at the half-time
  tactics screen in PCSX2 and not again at full time (a match with one
  first-half goal). Whether a second-half goal reaches them, and whether
  extra-time and shoot-out goals are in them, is not known. Until it is,
  read the live tally for the score and latch it before the engine goes.
- Which side is home, and which side is the player's club? Side 0 is
  only inferred to be home, and the engine orders its sides by a team
  key. The records that name your club (team id 1, the first word of the
  team struct) are confirmed; the side order is not.
- What does the match clock show? The float is confirmed as game seconds
  on the 90-minute scale, but whether it matches the on-screen clock,
  stops during dead balls, replays and the half-time break, and how
  added time is represented were not settled. Do not use it as the exact
  match time before a live dump.

The statistics column meanings (shots, corners, fouls and the rest of
the 0x10-byte rows), the event types 2 to 8 and 12, and the Japanese
addresses are open too. They are in "Match events and statistics".

## Checking the claims

Each command runs from the repo root on the extracted PAL files in
`ISO/`. The sections above have more commands, each next to the claim
it shows. These cover the gate, the match object and the score.

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Get
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Delete
python SRC/sles_disasm.py ISO/SLES_541.51 addr 203d70 14
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x72060 14 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x14cb40 20 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0x767b0 30 --sles ISO/SLES_541.51
```

What each shows. The first two give the load and the clearing of the
static word 0x3906d8. The third shows the stores of the VS flag (0x7548
from the PlGiTask buffer plus 0x18000) and the demo flag (0x7544). The
fourth shows the allocation of the 0xa8a0-byte match object and its
store to GAMEPRG + 0x2490fc. The fifth shows the sum of both sides'
goal counters going into `PlGiTask::SetGameScore`. The sixth shows the
live goal writer incrementing the per-segment counter.

To look a schedule id up, and to check that the addresses used here
resolve on the Japanese build, run:

```bash
python SRC/schedule.py compe DAT/PARAM 6
python SRC/gamever.py check ISO_JP
```
