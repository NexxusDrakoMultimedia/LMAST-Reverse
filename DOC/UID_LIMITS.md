<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Schedule limits: where the game fixes the schedules at 164

The career calendar has 164 schedule UIDs, 0–163
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)). The LMASTER third tier
needs six more, one hidden league per nation
([`LMASTER_MOD.md`](LMASTER_MOD.md#improvements), phase 3). This doc
lists what fixes the count at 164: the data, which sets it for most of
the schedule code, and the few code sites that name it.

## 164 is "no competition"

**Confirmed.** About 30 calls pass group 164 (`0xa4`) to
`pwkOteam_GetTeamData`/`GetTeamDataEx` (`0x24ba08`, `0x24bd30`), which
hands it to `plRec_MatchRegulations` (`0x21dc60`): `REGULATION.TBB`'s
row 164, the file's 165th, is the default rules for a club outside any
competition. Among the callers: `ScheCallbackCommand_CreateGiForFirstMatch`
(`0x114500`), `BestEleven` (`0x2d4a18`), the stationary player lists
(`0x2b6cb0`), and in `SIMPRG.REL` the Information module (`0x1258`),
the club editor (`0x50030`, `0x513d4`), the player search
(`0x926e4`), the rank lists (`0x95560`), the monthly report
(`0x9f944`, `0x9f960`), the events (`EVS::`, 13 sites) and the rival
records (`0x15f304`, `0x15f79c`, `0x15f940`). `VSPRG.REL 0x6f8c` too.

So UID 164 can't be a schedule. The third tier's UIDs are **165–170**.

## The data

The schedule code takes its count from the files, not from an
immediate (**empirical**: no loop over UIDs in the schedule functions
is bounded by 163–165; the scan below):

| File | Per UID | Now |
|---|---|---|
| `SCHEDULE_SYSTEM.PAC` `year_schedule_data.tbb` | a 20-byte row, found by UID (`getYearSchedule`, `0x20a170`) | 184 rows |
| `SCHEDULE_SYSTEM.PAC` `savectrl.tbb` | a byte: the save pool's type (below) | 164 |
| `SCHEDULE_COMPETITION.PAC`/`.HED` | an entry: games and pairings | 164 |
| `SCHEDULE_TEAM_ENTRY.PAC`/`.HED` | an entry: where the entrants come from | 164 |
| `REGULATION.TBB` | a row: rules, money, place slots | 165 (row 164 the default) |

`PRELOAD/STATIONFILE.PAC` holds copies of the schedule packs, and
`PRELOAD/SIMFILE*.PAC` of `REGULATION.TBB`
([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#writing)). Competitions 50–55
already have `open_nation` rows, names (message category 100009) and,
with `--mod save-expand`, past records.

## Code that names the count

**Confirmed**, each read with its function:

| Site | What it does | For 165–170 |
|---|---|---|
| `SIMPRG.REL 0x3cfcc` (`TICKET_SET_MODULE`) | loops UIDs 0–163 (`slti 0xa4`), looking each up in the loaded schedules (`0x3da80`) | to 171 |
| `GAMEPRG.REL 0xa069c` | a per-UID table of match-presentation flags at `0x26f748` (164 words); 164 and up get entry 0 | as it is |
| `GAMEPRG.REL 0x9f144` | the same table for the match being played, with no bound | never reached: you never play a third-tier match (`one-season-end` ends the game first) |

Not about UIDs, though they hold 163–165: `GAMEPRG.REL`'s 163-byte
arrays at `+0xa7` (`0x97ac0`, `0x97b58`, `0x9c7b0`),
`can_use_match_rand` (26 sites), and the events' message ids.

## The save pools

**Confirmed** (`ScheEuro_Memory::init`, `0x209210`): a loaded
schedule's games, team stats and entrants live in save block 5
(`pwkRec_GetGameResult`, `GetTeamStats`, `GetCompeTeam` and their
system buffers), shared out by bitmap allocators (`CBitMapBlock`), one
per `savectrl` type and kind:

| Kind | Unit | Type 0 | Type 1 | Type 2 |
|---|---|---|---|---|
| games | 16 bytes | 5,824 | 320 | 96 |
| team stats | `0x138` bytes | 704 | 160 | 160 |
| entrants | 8 bytes | 704 | 160 | 160 |

**Empirical** (the schedule packs; a script summing every UID a
normal season loads): the type 0 schedules, the big leagues among them,
take about 5,300 games and 616 entrants. The six tier leagues as type 0
add about 50 games (England's 5 clubs, 20 games; 3 clubs elsewhere, 6
each) and 20 entrants, so they fit. Types 1 and 2 add up to more than
their room in that sum, so their slots must be freed as schedules end,
or some rows load only in some years; that isn't traced, and the tier
leagues don't use them.

## Still unknown

- When a schedule's pool slots are freed, and the true peak of each
  pool over a season.
- Whether anything else keeps an array per UID sized from the 164-entry
  packs at load (the scan finds no such immediate; a size read from a
  file's entry count would grow with it).
- Whether the Information screen's competition list, which names
  competitions by nation, would show competitions 50–55.

## Checking

The scan is a short script over `gamever.image` of the executable and
each overlay: every `addi`/`addiu`/`slti`/`sltiu`/`andi`/`ori` with an
immediate of 163–165 (132 sites, 82 not a structure offset), and in the
schedule and record functions every immediate that is a multiple of 164
(none an array size). Then:

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 dis init__15ScheEuro_Memory
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x3cfa8 20 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 0xa0698 10 --sles ISO/SLES_541.51
python SRC/schedule.py year DAT/PARAM
```
