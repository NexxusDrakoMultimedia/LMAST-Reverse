<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Save editor: design, decisions and what is left

`SRC/saveedit.py` is a separate window for editing one career save on a
PCSX2 memory card, apart from the mod editor (`editor.py`). The mod
editor changes the game's files on the disc, before a career starts; the
save editor changes one career after it has started. It is built and
works on PAL saves: [`USAGE.md`](../USAGE.md#the-save-editor) is the
guide to using it, and this doc holds its design, the decisions behind it
and what is still untested in the game. Open a save with
`python SRC/saveedit.py open <save>`.

## Why a separate tool

- It works on a different thing: one save (`BESLES-54151-Gnnn`, or
  `-Fnnn` or `-Mnnn` for a modded disc), not the mod folder.
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
  depend on the save filled in from it. `Save.get`, `edit_range` and
  `staff_labels` give the window the rest, so it reads nothing by offset.
- Each save logs the equivalent `python SRC/save.py set ...` command,
  and the file the editor writes must equal what that command writes,
  byte for byte. A test checks it.
- Money is shown in pounds (the stored unit ÷ 6) next to the stored
  value, as the Regulations tab does.
- A page is tested through its widgets, off-screen, before it is called
  done.

## Pages

Each page shows what `save.py` can read, and edits only what
`save.py set` can write. Read-only values are greyed out.

| Page | Shows (from) | Edits (as `save.py set`) |
|---|---|---|
| Club | date, money, club status and rank, reputation (`show`) | `money=`, `status=`, `status_rank=` |
| Finances | season plan, this month's and the season's accounts by type (`finances`) | `plan:ad_budget=`, `ticket_price=`, `season_ticket_rate=`, `season_tickets=` |
| Squad | the squad and youth team; for a player: abilities with their level, growth limit and cap, condition fields, contract, play styles, skills, stats (`player`) | `<slot>:<n>=` and `<slot>:all=` (abilities), and every `<slot>:<field>=` key: fatigue, condition, motivation, power, form, age, injury value, captain and keyman experience, the two policy points, salary, contract years |
| Combinations | the 25 × 25 pair grid as the tactics screen's icons (`combi`) | `combi:<a>:<b>=`, `combi:<a>:all=` |
| Staff | manager, youth manager, coaches, scouts (`staff`) | `<staff>:abil.<n>=`, `dissat.<kind>=`, `pop_supporters=`, `pop_players=` |
| Other clubs | friendship, rank, players (`clubs`) | `club:<team>:friendship=`, `rank=` (the rival's rank is shown only, since a status edit rewrites it) |
| Candidates | scouted players and youth, staff candidates (`candidates`) | nothing: `save.py set` can't write them yet |
| Edit player | the imported Virtua Pro Football player (`editplayer`) | `edit:<field>=`, `edit:name=`, `edit:ability.<n>=` |

The injury kind stays read-only, like the team fit (the game works it
out again from the policy points and the manager's). The salary range
follows the save's money option (block 7 `+0x3c`).

## Steps

The editor was built in five steps. Each has its widget test, and each
page's logged command was checked to give the saved bytes.

| Step | What | State |
|---|---|---|
| 1 | `save.edit_spec()` and `save.py spec [<save>]`, with a check that every range it gives is one `cmd_set` accepts. `set`'s edits go through `apply_assigns`, which the editor calls too | built; checked on saves G000 and G003 with no problems |
| 2 | A read-only window: `python SRC/saveedit.py open <save>`. Decoding runs in a background thread with a "Loading" status, as the mod editor's People tab does. What the print commands worked out themselves (plan, accounts, candidates, style path) are `Save` methods, so both use the same code | built; every command's output unchanged on G000 and G003 |
| 3 | Edits page by page: Club, Finances, Squad (the 64 abilities, one or all, and the condition fields), Combinations, Staff and Other clubs. Candidates stays read-only | built; tested through the widgets on a copy of G003: 15 edits over every page, two refusals, File > Save, and the logged command giving the saved bytes |
| 4 | A PCSX2 test: one save edited on each page, loaded in game, the change seen on its screen | partly done, below |
| 5 | More player fields: salary, contract years, age, the injury value, and captain and keyman experience, each with its range from the game code (contract years from the saves), and an Edit player page | built; tested through the widgets on a copy of G003 (five edits, two refusals: a salary below the pound minimum, and age 15) and on a copy of G000 for the Edit player page (a name with a space, three fields, one refusal) |

The log lists every accepted edit in order, repeats included: an ability
edit raises its growth limit and cap, and a pair edit its cap, so an
ability set to 80 and then 30 keeps the raised limit, which only the
full sequence reproduces.

**Step 4, what has been loaded in game.** The editor writes the same
bytes as the logged `save.py set` command, so a test of a `set` key
tests the page that offers it. The edits seen in PCSX2 so far:

| Edit seen in game | Recorded in |
|---|---|
| money set to 10,000,000,000 showed £1,666,666,666, made in the editor's Club page (Nexxus) | [`SAVE_FORMAT.md`](SAVE_FORMAT.md#editing) |
| club status and status rank | [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) |
| the season plan | [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) |
| a player's fatigue, condition, motivation and abilities | [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) |
| a manager's dissatisfaction and a coach's abilities | [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) |
| pair combinations | [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) |
| another club's friendship and rank | [`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far) |

Not loaded in game yet: the Squad page's age, salary, contract years,
injury value, captain and keyman experience and policy points, and the
Edit player page. The Candidates page is read-only. The pending check,
one save edited on each page through the editor itself, is in
[`TESTING.md`](../TESTING.md).

## Saving

Decided (Nexxus, 2026-10-09):

- **Memory card format: folder cards, and card files** (card files added
  2026-10-23). `save.py` reads PCSX2 folder memory cards, where a save is
  a plain folder. A card file (`.ps2`) opens with File > Open save on a
  card file, which lists its `-G`, `-F` and `-M` saves; the window edits
  a copy of the main file, `<card>.bak/<folder>/<folder>.card`. Save writes the
  edit into the card through `ps2mc.py`
  ([`PS2MC_FORMAT.md`](PS2MC_FORMAT.md)), after backing up the whole
  card and the main file in `<card>.bak`, and only while the save on the
  card is still the one opened. The log gets `save.py set <main backup>
  <folder>.new ...` and `ps2mc.py put <card backup> <card>.new
  <folder>/<folder>=<folder>.new`. Save to new slot copies the folder on
  the card to its lowest free slot (`ps2mc.py copy`, every file with its
  mode and times, the main file renamed) and writes the edit there,
  logging the copy first. Tested through the widgets, off-screen, on a
  copy of Nexxus's `Mcd001.ps2`: G002 opened through the card dialog, a
  money edit saved (111,111 on the card), then another saved to a new
  slot, G003 (222,222 there, G002 unchanged, all five files in the new
  folder); after each, the logged commands gave the same card byte for
  byte, and the card passed `ps2mc.py info`'s checks. **Tested in
  PCSX2** (Nexxus's report, 2026-10-23): a save the editor copied to a new
  slot on `Mcd001.ps2` (Save to new slot, through `ps2mc.py copy`)
  showed in the game's load list and loaded.
- **Where an edit goes: over the save, after a backup.** Before each
  save, the editor copies the save's main file to
  `<card folder>.bak/<save folder>/<main file>.<date>-<time>.bak`,
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
  letter (`-G`, or `-F` or `-M` for a modded disc), writes the edited
  save into the copy and opens it; the original isn't touched, so it
  needs no backup. The game takes slots 0–100 (`MC::CFcEuroIF::setNo`,
  `SLES 0x12aea0`). The copy goes through `save.copy_save`, which also
  fixes the name in PCSX2's `_pcsx2_meta_directory` and `_pcsx2_index`,
  as `save.py rename` does. The log gets `python SRC/save.py copy <save
  folder> <slot>` and `python SRC/save.py set <original main file> <new
  main file>.new ...`; with no edits, only the copy. Tested through the
  widgets on a copy of Nexxus's card (G000, G001, G003): a money edit
  saved from G003 to G002, G003 unchanged, the two logged commands giving
  the same folder byte for byte, a second copy without edits to G004
  identical to G002, and a refusal when the main file changed on disk.
  The game loads a copied save: tested in PCSX2 with `save.py copy`
  ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#separate-saves-for-a-modded-disc),
  "Slots").

## Still unknown

- **A running PCSX2.** PCSX2 may keep a folder card's files open or write
  them back while the game runs. The Club page and
  [`INSTALL.md`](../INSTALL.md#editing-a-save) tell you to close the game
  first; the editor doesn't detect a running PCSX2, and whether it should
  warn when the card is in use is undecided.
- **Japanese saves.** `save.py --iso ISO_JP` reads and writes them
  ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-japanese-release)), but the
  save editor is PAL-only, left for later
  ([`TODO.md`](../TODO.md#playing-a-mod)).
- **Candidates.** The page is read-only: `save.py set` has no key for the
  candidate lists. Part of the player candidate record isn't decoded
  either ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far), "The
  youth block").
- What can't be edited yet, because nothing decodes it, is listed in
  [`SAVE_FORMAT.md`](SAVE_FORMAT.md#still-unknown). The save editor adds
  those fields as `save.py` learns them, never before.

## Checking the claims

```bash
python SRC/save.py spec <card>/BESLES-54151-G003
python SRC/save.py set <card>/BESLES-54151-G003 edited.bin money=2000000000 3:fatigue=0
python SRC/saveedit.py open <card>/BESLES-54151-G003
python SRC/saveedit.py open Mcd001.ps2
python SRC/ps2mc.py info Mcd001.ps2
```

`spec` checks each range on the save: both ends accepted, the values just
outside refused. The editor's own test has no command: drive the widgets
off-screen (`geometry("1280x720+-4000+0")`), save, then run the command
the editor logged in `<card>.bak/saveedit.log` and compare its output
with the saved file.
