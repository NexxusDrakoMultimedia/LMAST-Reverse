<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Save editor: plan

A separate window, `SRC/saveedit.py`, for editing a career save on a
memory card, apart from the mod editor (`editor.py`). The mod editor
changes the game's files on the disc, before a career starts; the save
editor changes one career after it has started. Nothing here is built
yet. This doc says what it would do, in what order, and what has to be
decided first.

## Why a separate tool

- It works on a different thing: one save (`BESLES-54151-Gnnn`, or
  `-Mnnn` for a modded disc), not the mod folder.
  `save.py` already decodes and encodes it ([`SAVE_FORMAT.md`](SAVE_FORMAT.md)).
- Its edits don't go on a disc, so File > Build disc and the mod folder
  don't apply.
- Saves are small to load (about a second after the first run) but slow
  the first time (about 10 seconds to record the field list), so a
  window that opens one save at a time suits them.

It reuses the mod editor's widgets (`value_input`, `Scrolled`, the
`.new`-then-replace save) by importing `editor.py`, and takes names
from the disc data as the mod editor does (players and staff from
`PBDATA_EU.PAC`, clubs from `MES.PAC`).

## Principles

The same as the mod editor's ([`GOALS.md`](../GOALS.md), stage 5):

- Every edit goes through `save.py`'s own functions (`Save.set_ability`,
  `set_field`, `set_staff`, `set_plan`, `set_status`, `set_club`,
  `set_combi`, `money`). The editor keeps no layout of its own.
- `save.py` says which values each field allows. A new
  `save.edit_spec()` gathers the ranges it already checks
  (`PLAN_EDITS`, `STAFF_ABIL_RANGE`, `CLUB_RANK_MAX`, the 0–99 ability
  levels, the 0–65,535 condition values) in one place for the editor.
- Each save logs the equivalent `python SRC/save.py set ...` command,
  and the file the editor writes must equal what that command writes,
  byte for byte. A test checks it.
- Money is shown in pounds (the stored unit ÷ 6) next to the stored
  value, as the Regulations tab does.
- Tested through the widgets, off-screen, before it's called done.

## Pages

Each page shows what `save.py` can already read, and edits only what
`save.py set` can already write. Read-only values are greyed out.

| Page | Shows (from) | Edits (as `save.py set`) |
|---|---|---|
| Club | date, money, club status and rank, reputation (`show`) | `money=`, `status=`, `status_rank=` |
| Finances | season plan, this month's and the season's accounts by type (`finances`) | `plan:ad_budget=`, `ticket_price=`, `season_ticket_rate=`, `season_tickets=` |
| Squad | the squad and youth team; for a player: abilities with their level and exp, condition fields, styles, stats (`player`) | `<slot>:<ability>=`, `<slot>:all=`, `<slot>:fatigue=` and the other condition fields |
| Combinations | the 25 × 25 pair grid as the tactics screen's icons (`combi`) | `combi:<a>:<b>=`, `combi:<a>:all=` |
| Staff | manager, youth manager, coaches, scouts (`staff`) | `manager:abil.<n>=`, `dissat.<n>=`, `pop_supporters=`, ... |
| Other clubs | friendship, rank, players (`clubs`) | `club:<team>:friendship=`, `rank=` |
| Candidates | scouted players and youth, staff candidates (`candidates`) | none yet (read-only) |

## Steps

1. **`save.edit_spec()`** and a `save.py` command that prints it. It also
   gets a check that every range it gives is one `cmd_set` accepts.
2. **Read-only window**: open a save, the pages above without inputs.
   Decoding runs in a background thread with a "Loading" status, as the
   People tab does.
3. **Edits** page by page, in the order of the table, each with its
   widget test and the logged-command check.
4. **PCSX2 test** (by the user): one save edited in each page, loaded in
   game, the change seen on its screen. Recorded in
   [`SAVE_FORMAT.md`](SAVE_FORMAT.md) and `DONE.md`.
5. **Later**: player fields that `save.py` reads but doesn't let `set`
   change (`PINFO_FIELDS` with no range: salary, contract years, age,
   injury days and kind, captain and keyman experience), each first as a
   `save.py set` field with its range from the game code, then on the
   Squad page.

## Decisions needed before building

- **Memory card format.** `save.py` reads PCSX2 **folder** memory cards,
  where a save is a plain folder. A `.ps2` card image (PCSX2's default)
  would need a reader and writer for the card's file system, a separate
  piece of work. Which kind do you use?
- **Where an edit goes.** Writing over the save in its slot is the most
  convenient, but a bad edit then loses the career. The choices are:
  (a) write over it after copying the original to `<save>.bak` next to
  it, (b) always write to a new slot (the next free `-Gnnn`), or
  (c) ask each time.
- **PCSX2 running.** PCSX2 may keep a folder card's files open or write
  them back while the game runs. The editor could warn when the card's
  folder is in use, or the guide could just say to close the game
  first.
- **Japanese saves.** `save.py` is PAL-only (`TODO.md` section 7). The
  plan leaves them out.

## Still unknown

What can't be edited yet, because nothing decodes it, is listed in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#still-unknown). The save editor adds
those fields as `save.py` learns them, never before.
