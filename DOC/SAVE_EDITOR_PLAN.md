<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Save editor: plan

A separate window, `SRC/saveedit.py`, for editing a career save on a
memory card, apart from the mod editor (`editor.py`). The mod editor
changes the game's files on the disc, before a career starts; the save
editor changes one career after it has started. This doc is its plan:
what it does, in what order it was built, and what is still to decide.
Steps 1–3 are built (`python SRC/saveedit.py open <save>`); what is left
is a PCSX2 test of each page's edit (step 4) and the player fields
`save.py` can't set yet (step 5).

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
| Candidates | scouted players and youth, staff candidates (`candidates`) | none (`save.py set` can't yet) |

## Steps

1. **`save.edit_spec()`** and a `save.py` command that prints it. It also
   gets a check that every range it gives is one `cmd_set` accepts.
   *Done:* `save.py spec [<save>]`; `set`'s edits now go through
   `apply_assigns`, which the editor calls too. Checked on saves G000
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
   card, and the logged command giving the saved bytes. Tested in PCSX2
   (user): money set to 10,000,000,000 in the editor showed £1,666,666,666
   in game. Finances (the season plan's ad budget, ticket price,
   season-ticket rate and season tickets), tested the same way. *Done:*
   the other pages. Squad (a player's 64 abilities, one or all, and the
   condition fields), Combinations (one pair or all of a player's),
   Staff (abilities, dissatisfaction, popularity) and Other clubs
   (friendship and rank; the rival's rank is shown only, since a status
   edit rewrites it). Candidates stays read-only. `save.py` gained
   `Save.get`, `edit_range` and `staff_labels`, so the window still
   keeps no layout. Tested through the widgets on a copy of G003: 15
   edits over every page, two refusals, File > Save, and the logged
   command giving the saved bytes.
   The log lists every accepted edit in order, repeats included: an
   ability edit raises its growth limit and cap, and a pair edit its cap,
   so an ability set to 80 and then 30 keeps the raised limit, which
   only the full sequence reproduces.
4. **PCSX2 test** (by the user): one save edited in each page, loaded in
   game, the change seen on its screen. The Club page is tested. Recorded in
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
  opened.
- **Or to a new slot** (added 2026-10-22). File > Save to new slot
  copies the save folder to the card's lowest free slot with the same
  letter (`-G`, or `-M` for a modded disc), writes the edited save into
  the copy and opens it; the original isn't touched, so it needs no
  backup. The game takes slots 0–100 (`MC::CFcEuroIF::setNo`, `SLES
  0x12aea0`). The copy goes through `save.copy_save`, which also fixes
  the name in PCSX2's `_pcsx2_meta_directory` and `_pcsx2_index`, as
  `save.py rename` does. The log gets `python SRC/save.py copy <save
  folder> <slot>` and `python SRC/save.py set <original main file> <new
  main file>.new ...`; with no edits, only the copy. Tested through the
  widgets on a copy of the user's card (G000, G001, G003): a money edit
  saved from G003 to G002, G003 unchanged, the two logged commands giving
  the same folder byte for byte, a second copy without edits to G004
  identical to G002, and a refusal when the main file changed on disk.
  **Tested in PCSX2** (user report, 2026-10-22): on a test card holding
  G000, G001 and G003, G003 copied to G002 by `save.py copy` with
  `money=999999996` showed in the load list, loaded, and had
  £166,666,666; G003 still loaded with £2,511,807.

Still open:

- **PCSX2 running.** PCSX2 may keep a folder card's files open or write
  them back while the game runs. The editor could warn when the card's
  folder is in use, or the guide could just say to close the game
  first.
- **Japanese saves.** `save.py` is PAL-only (`TODO.md`). The plan leaves
  them out.

## Still unknown

What can't be edited yet, because nothing decodes it, is listed in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#still-unknown). The save editor adds
those fields as `save.py` learns them, never before.
