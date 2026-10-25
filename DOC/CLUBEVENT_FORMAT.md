<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Club events (PR activities)

The Publicity Department's 46 events ("PR activities" in the manual; the
game calls them club events, `PlClubEvent`) are kept in three tables in
the executable, one record per event. `PARAM/CLUBEVENT.TBB` is an older
copy no code reads
([`PARAM_DIR.md`](PARAM_DIR.md#clubeventtbb-an-older-copy-of-the-club-events)).
What the events do to the economy (the chance and the business cycle,
the cost, the ticket bonus) is in [`ECONOMY.md`](ECONOMY.md#pr-events).

`python SRC/clubevent.py show ISO DAT/MESSAGE/MES.PAC` lists every event
with its cost, chance, results and when it is offered; `set` edits them
into a copy of the executable, and the mod editor's PR events tab does
the same.

| Table (PAL) | Japanese | Record | Read by |
|---|---|---|---|
| `0x52ff58` | `0x52bcc8` | 32 bytes, the offer | `plClubEvent_GetList` (`0x20e488`), `plClubEvent_GetCost` (`0x20dee0`), `plClubEvent_NeedMatch` (`0x20ea00`) |
| `0x530518` | `0x52c288` | 8 bytes, the chance | `plClubEvent_Execute` (`0x20df50`) |
| `0x530688` | `0x52c3f8` | 28 bytes, the success | `plClubEvent_Execute`, `plClubEvent_GetTicket` (`0x20df00`) |
| `0x52ff48` | `0x52bcb8` | 4 s32: 100, 90, 80, 50 | `plClubEvent_GetList` (`0x20e888`), the priorities |

The Japanese tables hold the same bytes but for four `+0x08` office
values, each one higher there: Ticket Campaign and Stadium Tours (38,
39) need office equipment 3 at level 1 in Japan and nothing on the PAL
disc, and Giveaway Days and Player Tours (41, 42) level 2 in Japan and
level 1 on PAL. So PAL made four ticket events easier to get.

## Names

MES.PAC category 572 names the events: message *n* is event *n*'s name
(0 Talk Show … 27 PR Strategy Talks … 45 Club Party) and 5000 + *n* its
description. **Empirical:** the names fit what the records say, for
example the seven ticket events (38–44) are the ones that need a match,
and 29 Victory Parade is the one offered in June after a title.
Category 563 holds 45 "… a success" mail titles, each with its
"failure".

## The offer record (32 bytes)

**Confirmed** from `plClubEvent_GetList` (`0x20e5c0`–`0x20e878`), which
builds the scheduling screen's list for a calendar turn. An event is
offered when every rule below allows it.

| Offset | Type | Field (`set`) | What it does |
|---|---|---|---|
| `0x00` | u32 | `month_rule` | nonzero: the event's month rule, held in the code by event number (`0x20e5f4`–`0x20e6e8`): 22 Soccer School in January or August, 30 Summer Festival in July or August, 31 Christmas Party in December, 32 Winter Festival from November to January, 35–37 from January to August. 0: no month rule, and `+0x18` applies |
| `0x04` | u16 | `first_season` | not offered before the season 2006 + *n* (`0x20e5cc`: year < `0x7d6` + *n*); a career starts in 2006–07 |
| `0x06` | u16 | `popularity` | not offered while the home popularity (block 1 `+0x11248`, [`ECONOMY.md`](ECONOMY.md#supporter-popularity)) is below it |
| `0x08` | u8 | `office` | 2 or more: needs office equipment 3 (`pwkTeam_GetOfficeEquipsLv(3)`) at level *n* − 1 or higher |
| `0x09` | u8 | `priority` | the list holds 10 events. After event 45 (below), it takes the events at priority 100 or more in number order, then 90 or more, 80 and 50 (the table at `0x52ff48`); an event under 50 is never listed |
| `0x0a` | u8 | – | a cap on a count per event the caller passes; the only caller (`SIMPRG.REL 0xa4150`) passes none, so it is never read |
| `0x0b` | u8 | `gap` | not offered while the same event is on the calendar within that many turns before this one (`0x20e230`: the calendar's 0x48-byte days, event at `+0x38`); 8 turns a month |
| `0x0c` | u8 | `talks` | needs event 27 (PR Strategy Talks) held with success in the previous month (`0x20e3f0`: an event 27 day with a nonzero `+0x30`) |
| `0x0d` | 3 bytes | – | 0 in every record, never read |
| `0x10` | u32 | `title` | only in June, and only when your club (team 1) finished first in its league (`0x20e2d8`) |
| `0x14` | u32 | `cost` | the cost: × 300 in the stored unit (`plClubEvent_GetCost`), so × 50 in pounds; `--mod pr-costs` makes it × 600 |
| `0x18` | u32 | `not_july` | not offered in July (read only when `+0x00` is 0) |
| `0x1c` | u32 | `match` | needs a match that day: `plClubEvent_NeedMatch`, and `GetList`'s match arguments, which the screen takes from the day (`SIMPRG.REL 0xa411c`–`0xa413c`) |

Two events are handled by number: event 45 (Club Party) is offered only
while a player has promise 7 or 11 or the manager promise 37
(`pwkPromise_GetPlayerPromise`, `GetManagerPromise`), and then goes
first; event 37 (Renew Mobile Site) is never offered (`0x20e864` clears
it after every check). So Renew Mobile Site is cut content: its record
is complete (from 2010–11, popularity 30,001, priority 99) but the game
never lists it.

## The chance record (8 bytes)

**Confirmed** from `plClubEvent_Execute`; [`ECONOMY.md`](ECONOMY.md#pr-events)
gives the sums and the business-cycle bug.

| Byte | Field (`set`) | What |
|---|---|---|
| 0 | `base` | the base chance: success when `fcEuroRand_Get0toI(100)` is at most the sum |
| 1 | `boom` | the change in business cycle 0, never read by the retail code |
| 2 | `good` | the change in cycle 1; the retail code reads it in cycles 0 and 1 |
| 3 | `poor` | the change in cycle 3; read in cycles 3 and 4 |
| 4 | `slump` | the change in cycle 4; read in cycle 2 |
| 5 | – | never read (10 for event 19, 5 for event 40, else 0) |
| 6 | `bonus6` | added when `0x20df48` returns true, which it never does |
| 7 | `status_bonus` | added when the club status is over 49,999 |

The changes are added as bytes, so 246 is −10. That bytes 1–4 are meant
for cycles 0, 1, 3 and 4 is **empirical** (`--mod pr-cycle` reads them
that way).

## The success record (28 bytes, 7 s32)

**Confirmed** from `plClubEvent_Execute`. A failed event changes nothing.

| Offset | Field (`set`) | What success changes |
|---|---|---|
| `0x00` | `pop_overseas` | the overseas popularity (`plPinfo_ChangePop` kind 1) of each player named in the event's schedule entry, up to 11 |
| `0x04` | `pop_home` | their home popularity (kind 0) |
| `0x08` | `club_home` | the club's home popularity (`pwkTeam_PopChange`) |
| `0x0c` | `club_overseas` | its popularity in every overseas region |
| `0x10` | `youth` | youth development (`pwkYouthDev_Add`) |
| `0x14` | `complaint` | supporter complaint kind 4 (`pwkSupCom_ChangeSupporterComp`); Fans' Day −400, Supporters' Forum −500 |
| `0x18` | `ticket` | the ticket bonus in percent, kept on the day (`+0x30`) for that day's match ([`ECONOMY.md`](ECONOMY.md#a-home-match)) |

## Editing

`set` takes `<event>:<field>=<value>` and writes a same-size executable,
patched with `patch_disc.py patch ... disc:SLES_541.51=<file>`. The
ranges it takes keep the code's sums sensible: chance bytes −100 to 100
(base 0–100), popularity and the other success values ±65,535, the
ticket bonus −100 to 1,000 %, the cost up to 1,000,000 (£50 million; ×
600 still fits a 32-bit sum). `roundtrip` re-encodes every field into
the executable, which gives back the same file on both releases.

```bash
python SRC/clubevent.py info ISO
python SRC/clubevent.py show ISO DAT/MESSAGE/MES.PAC
python SRC/clubevent.py set ISO/SLES_541.51 out.elf 27:cost=400 38:ticket=10
python SRC/sles_disasm.py ISO/SLES_541.51 dis plClubEvent_GetList plClubEvent_Execute
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x20e230 42
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x20e2d8 70
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x20e3f0 38
```

None of these edits is tested in game yet.

## Still unknown

- How the scheduling screen sets `GetList`'s two match arguments from
  the day (`SIMPRG.REL 0xa411c`: the day's `+0x4`, `+0x8` and `+0x40`),
  and so whether `+0x1c` events need a home match.
- Which office equipment kind 3 is (the office's four kinds by name).
- Why event 37 is disabled, and whether restoring it works in game.
