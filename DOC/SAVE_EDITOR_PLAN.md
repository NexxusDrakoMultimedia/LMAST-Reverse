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

- Every edit goes through `save.apply_assigns`, the function behind
  `save.py set`, which calls `Save.set_ability`, `set_field`,
  `set_staff`, `set_plan`, `set_status`, `set_club` and `set_combi`. The
  editor keeps no layout of its own.
- `save.py` says which values each field allows: `save.edit_spec()`
  gathers the ranges `set` checks in one place, with the ends that
  depend on the save filled in from it.
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
   *Done:* `save.py spec [<save>]`; `set`'s edits now go through
   `apply_assigns`, which the editor will call too. Checked on saves G000
   and G003 with no problems.
2. **Read-only window**: open a save, the pages above without inputs.
   Decoding runs in a background thread with a "Loading" status, as the
   People tab does. *Done:* `python SRC/saveedit.py open <save>`. The
   values the print commands worked out themselves (plan, accounts,
   candidates, style path) are now `Save` methods, so both use the same
   code; every command's output is unchanged on saves G000 and G003.
3. **Edits** page by page, in the order of the table, each with its
   widget test and the logged-command check. *Done so far:* Club (money,
   status, status rank), tested on a copy of save G003: an edit of each,
   a refused status above the cap, File > Save, the backup beside the
   card, and the logged command giving the saved bytes.
4. **PCSX2 test** (by the user): one save edited in each page, loaded in
   game, the change seen on its screen. Recorded in
   [`SAVE_FORMAT.md`](SAVE_FORMAT.md) and `DONE.md`.
5. **Later**: player fields that `save.py` reads but doesn't let `set`
   change (`PINFO_FIELDS` with no range: salary, contract years, age,
   injury days and kind, captain and keyman experience), each first as a
   `save.py set` field with its range from the game code, then on the
   Squad page.

## Decisions

Decided (user, 2026-10-09):

- **Memory card format: folder cards.** `save.py` reads PCSX2 folder
  memory cards, where a save is a plain folder. `.ps2` card images
  (PCSX2's default) are a later item in `TODO.md`.
- **Where an edit goes: over the save, after a backup.** Before each
  save, the editor copies the save's main file to
  `<card folder>.bak/<save folder>/<main file>.<date and time>.bak`,
  beside the memory card and not in it: a folder card shows the PS2
  every folder in it, and one named `BESLES-54151-…` would appear in the
  game's save list. A backup per save (rather than one per session) lets
  the logged command name it as its input:
  `<card folder>.bak/saveedit.log` gets `python SRC/save.py set <backup>
  <main file>.new ...`, which writes the same bytes. The editor also
  refuses to save when the main file changed on disk since it was
  opened. Writing to a new slot instead is a later item in `TODO.md`.

Still open:

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
