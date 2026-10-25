<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Using the editors

This project has two editor windows:

- The **mod editor** (`editor.py`) changes the game's own data, such as
  players, clubs, kits and text, and builds a modded disc or a patch from
  your edits. Its changes apply to careers started on that disc.
- The **save editor** (`saveedit.py`) changes one career that has already
  started, in a save on a PCSX2 memory card: money, players, staff and
  the rest.

Neither needs any coding. This guide shows how to open each one and
what to do in it. To play a patch someone else made, see
[`INSTALL.md`](INSTALL.md) instead.

## Before you start

Both editors need the project set up as the [README](README.md#setup)
says: Python 3, and your disc extracted into `ISO/` and `DAT/` with
`extract_disc.py`. They read the game's data from there (the save
editor reads its names and runs the game's own save code from it).
Nothing else needs installing: the windows use `tkinter`, which comes
with Python.

Run every command from the project folder (the one holding `SRC/`,
`DAT/` and this file).

## The mod editor

### Opening it

```bash
python SRC/editor.py open
```

opens the mod folder `mod/`. To keep several mods apart, give each its
own folder:

```bash
python SRC/editor.py open mods/terry
```

The folder is made the first time you save into it. Opening the same
folder again carries on where you left off: the editor reads your
edited copy of a file when there is one, so edits build up over
sessions.

### The window

Each kind of data has a tab along the top:

| Tab | What you edit there |
|---|---|
| People | players, managers and scouts: search by name, id, nationality or club, then change any named field |
| Clubs | each club's rank, manager, stadium, city and transfer policy, and the computer teams' squads |
| New club | what a new career starts with, for each league and team style |
| Season | the starting divisions: swap two clubs' places, or change a first division's size |
| National calendar | when the national squads are called up and released, in each year of the four-year cycle |
| Free agents | the players with no club at the start of a career |
| Regulations | each competition's match rules, win bonus, prize money and promotion and relegation places |
| Club ranking | how clubs earn their ranking at the end of each season: the points each competition gives for each final place, and which club rank each position in a league gets |
| Training | what each practice, camp type and youth practice trains, and how tiring it is |
| Camps | each training camp's type |
| Tours | the clubs a tour can play in each region |
| Facilities | build costs, upkeep, build times and stadium capacities |
| PR events | the Publicity Department's events: when each is offered, what it costs, its chance of success and what success brings |
| Tactics | the tactics screen's eight Set Formation presets |
| Kits | every club's home, away and keeper kits, shown as colour swatches |
| Text | any message in the game, in all its language slots |
| Comments | the comment lines on the player, manager, coach and scout detail screens |
| Log | the commands your saves stood for (below) |

Most tabs work the same way: search or pick from the list on the left,
and the record opens on the right. Fields the project hasn't worked out
yet are shown greyed out and can't be changed.

### Changing a value

- A **drop-down** takes effect as soon as you pick an entry.
- A **number box** takes effect when you press Enter or click away from
  it. The arrows step through the values it allows.

A value the game can't use is refused with a message, and the box goes
back to the old value. For example, the Clubs tab refuses a player who
is already in another club's squad.

An edited tab shows a `*` after its name, and the title bar lists the
tabs with unsaved edits.

### Saving

**File > Save** (Ctrl+S) writes every tab's edits into the mod folder.
Each file goes under its own path, so `mod/PARAM/PBDATA_EU.PAC` is your
edited copy of `DAT/PARAM/PBDATA_EU.PAC`. Your disc and `DAT/` are never
changed. Closing the window with unsaved edits asks whether to save
them.

Each save also writes the matching commands to `editor.log` in the mod
folder, and the Log tab shows them. You don't need them, but they
record exactly what you changed, and running them again gives the same
files.

To start a mod again from scratch, delete its folder, or open a new
one.

### Building a disc or a patch

**File > Build disc** (Ctrl+B) turns the mod folder into something you
can play or share.

1. **Original disc image**: your unmodified Redump `.iso` (see
   [`INSTALL.md`](INSTALL.md#1-check-your-disc) for the hashes it must
   match). It is only read. If it sits in the project folder under its
   Redump name, the editor finds it for you.
2. Tick what to write:
   - **Write a modded disc image**: an `.iso` to play in PCSX2.
   - **Write an xdelta patch**: the `.xdelta` file to share. Other
     players apply it to their own disc, as `INSTALL.md` explains.

   Either or both. A patch on its own still needs room for a full
   temporary image while it is made.
3. Optionally, add the project's ready-made changes with the boxes
   below. The two LMASTER buttons tick the right boxes for each LMASTER
   build ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)), and
   [`INSTALL.md`](INSTALL.md#4-building-a-patch) says what each box
   does. Tick **Separate saves** (`--mod mod-saves`) if the modded disc
   should keep its careers apart from the original game's.
4. Check the list of edited files, then press **Build**.

The output of each step shows in the window. If you have unsaved edits,
it asks to save them first, since the disc is built from the saved
files. A build takes a few minutes. When it ends with "Built ...", the
files are ready; if it says the build failed, don't use them.

The dialog remembers its paths and boxes for this mod folder
(`build.json`).

**Sharing a mod:** share only the `.xdelta`, never the disc image or
files from it. Build the patch from the unmodified Redump image, or it
only applies to your own file; the dialog warns you if the original
looks wrong.

## The save editor

### Close the game first

**Close the game in PCSX2 before you save an edit.** PCSX2 can write the
memory card while the game runs, which would put the old save back
over your edit. The editor also refuses to save if the save changed on
the card after you opened it.

### Opening a save

PCSX2 keeps memory cards in its memcards folder (Settings > Memory
Cards shows where). A card is either:

- a **folder card**: a folder named like `Mcd001.ps2`, with one folder
  per save inside it, or
- a **card file**: a single file named like `Mcd001.ps2`.

Career saves are named `BESLES-54151-G000`, `-G001` and so on, or
`-M000` and up for a modded disc that has its own saves.

```bash
python SRC/saveedit.py open
```

opens an empty window. Then:

- **File > Open save** (Ctrl+O) for a folder card: choose the save's
  folder, such as `Mcd001.ps2/BESLES-54151-G003`.
- **File > Open save on a card file** for a card file: choose the
  `.ps2` file, then the career from the list.

Or give the save straight away:

```bash
python SRC/saveedit.py open <card>/BESLES-54151-G003
```

```bash
python SRC/saveedit.py open Mcd001.ps2
```

The first save you open takes about 10 seconds while the editor
prepares; later ones open in about a second.

### The pages

| Page | What you can change |
|---|---|
| Club | money, club status and its rank |
| Finances | the season plan: advertising budget, ticket price, season-ticket rate and season tickets. The accounts are shown only |
| Squad | for each player in the squad or youth team: the 64 abilities (one at a time, or all at once), fatigue, condition, motivation and the other condition fields, salary, contract years, age, the injury value, and captain and keyman experience |
| Combinations | how well each pair of players works together, shown as the tactics screen's icons: one pair, or all of a player's pairs |
| Staff | the manager's, youth manager's, coaches' and scouts' abilities, dissatisfaction and popularity |
| Other clubs | the other 440 clubs' friendship with your club, and their rank |
| Candidates | the scouted players and staff candidates, shown only |
| Edit player | the Virtua Pro Football player the career imported, if it has one: the name, the database fields and the abilities |

Money shows in pounds next to the value the save stores (the stored
value is six times the pounds). Edits work as in the mod editor: a
number box takes effect on Enter or when you click away, and a value
the save can't hold is refused with a message and put back. Some edits
raise a hidden value as they go: setting an ability also raises its
growth limit and cap, so setting it back down doesn't undo that part.

The title bar counts your unsaved changes.

### Saving

There are two ways to save:

- **File > Save** (Ctrl+S) writes the edit over the save. First it
  copies the save as it was to a backup folder beside the card,
  `<card>.bak` (for a card file, the whole card too), so you can always
  go back. Each save makes a new backup, named with the date and time.
- **File > Save to new slot** leaves the original career as it is: it
  copies the save to the card's first free slot (`-G004`, say), writes
  the edit into the copy and opens it. In the game it shows as another
  career in the load list.

Save to new slot is the safest choice when you try something out. The
backup folder is outside the card on purpose: anything inside a folder
card shows up in the game's save list.

To undo a File > Save, with PCSX2 closed, copy a backup back by hand
and drop its `.<date>-<time>.bak` ending:

- On a folder card, the file in `<card>.bak/<save folder>/` from the
  time you want goes back into the save folder, over the file of the
  same name.
- On a card file, the whole card's backup is in `<card>.bak` itself,
  for example `Mcd001.ps2.bak/Mcd001.ps2.20261025-143000.bak`; it goes
  back over `Mcd001.ps2`.

`<card>.bak/saveedit.log` records the command each save stood for, as
the mod editor's log does.

### Carrying a career to a modded disc

A disc built with **Separate saves** doesn't see the original game's careers.
To carry one over, copy it to the modded name: see
[`INSTALL.md`](INSTALL.md#taking-a-career-over-to-a-modded-disc).

## What isn't covered yet

- The save editor works on PAL saves only, not the Japanese release's.
- The candidate lists can't be edited yet.
- Edits from the Squad, Combinations, Staff, Other clubs and Edit
  player pages have been checked in the editor but not all yet loaded
  in the game; the Club page has been. The list is in
  [`SAVE_EDITOR_PLAN.md`](DOC/SAVE_EDITOR_PLAN.md).

What each field means, and how it was found, is in the format docs
the [README](README.md#documentation-index) lists, such as
[`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md) for saves and
[`PBDATA_FORMAT.md`](DOC/PBDATA_FORMAT.md) for the player database.
