<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Save editor: plan

A separate window, `SRC/saveedit.py`, for editing a career save on a
memory card, apart from the mod editor (`editor.py`). The mod editor
changes the game's files on the disc, before a career starts; the save
editor changes one career after it has started. This doc is its plan:
what it does, in what order it was built, and what is still to decide.
Steps 1–3 and 5 are built (`python SRC/saveedit.py open <save>`); what
is left is a PCSX2 test of each page's edit (step 4).

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
| Edit player | the imported Virtua Pro Football player (`editplayer`) | `edit:<field>=`, `edit:name=`, `edit:ability.<n>=` |

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
5. **More player fields** (done 2026-10-23): salary, contract years,
   age, the injury value, and captain and keyman experience are `save.py
   set` fields, each with its range from the game code (contract years
   from the saves), and show on the Squad page with the rest. The salary
   range follows the save's money option (block 7 `+0x3c`). The injury
   kind stays read-only. The fields and their sources are in
   [`SAVE_FORMAT.md`](SAVE_FORMAT.md). Tested through the widgets on a
   copy of G003: five edits, two refusals (a salary below the pound
   minimum, age 15), File > Save, and the logged command giving the
   saved bytes. Not yet loaded in game.
   An **Edit player** page (added 2026-10-23) edits the career's
   imported Virtua Pro Football player through `save.py set edit:...`:
   the name, every named database field and the 64 abilities. Tested
   through the widgets on a copy of G000 (a name with a space, three
   fields, one refusal, the logged command giving the saved bytes).

## Decisions

Decided (user, 2026-10-09):

- **Memory card format: folder cards, and card files** (card files added
  2026-10-23). `save.py` reads PCSX2 folder memory cards, where a save is
  a plain folder. A card file (`.ps2`) opens with File > Open save on a
  card file, which lists its `-G` and `-M` saves; the window edits a copy
  of the main file, `<card>.bak/<folder>/<folder>.card`. Save writes the
  edit into the card through `ps2mc.py`
  ([`PS2MC_FORMAT.md`](PS2MC_FORMAT.md)), after backing up the whole
  card and the main file in `<card>.bak`, and only while the save on the
  card is still the one opened. The log gets `save.py set <main backup>
  <folder>.new ...` and `ps2mc.py put <card backup> <card>.new
  <folder>/<folder>=<folder>.new`. Save to new slot copies the folder on
  the card to its lowest free slot (`ps2mc.py copy`, every file with its
  mode and times, the main file renamed) and writes the edit there,
  logging the copy first. Tested through the widgets, off-screen, on a
  copy of the user's `Mcd001.ps2`: G002 opened through the card dialog, a
  money edit saved (111,111 on the card), then another saved to a new
  slot, G003 (222,222 there, G002 unchanged, all five files in the new
  folder); after each, the logged commands gave the same card byte for
  byte, and the card passed `ps2mc.py info`'s checks. **Tested in
  PCSX2** (user report, 2026-10-23): a save the editor copied to a new
  slot on `Mcd001.ps2` (Save to new slot, through `ps2mc.py copy`)
  showed in the game's load list and loaded.
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
  The game loads a copied save: tested in PCSX2 with `save.py copy`
  ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#separate-saves-for-a-modded-disc),
  "Slots").

Still open:

- **PCSX2 running.** PCSX2 may keep a folder card's files open or write
  them back while the game runs. [`INSTALL.md`](../INSTALL.md#editing-a-save)
  tells players to close the game first; whether the editor should also
  warn when the card is in use is undecided.
- **Japanese saves.** `save.py --iso ISO_JP` reads and writes them
  ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-japanese-release)), but the
  save editor is PAL-only, left for later ([`TODO.md`](../TODO.md#5-edit-the-gui)).

## Still unknown

What can't be edited yet, because nothing decodes it, is listed in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#still-unknown). The save editor adds
those fields as `save.py` learns them, never before.
