<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Installing a mod

A guide for players: how to play a mod made with this project. Check
your disc, apply the patch, and keep your saves safe. The first three
sections need no Python. The last one is for people who build a patch;
the [README](README.md) covers setting the project up.

For help, and to share what you've made, there's the
[LMAST/SFCC English Fan Discord](https://discord.gg/7DNrGye9TZ).

## What you need

- The PAL disc of *Let's Make a Soccer Team!* (SLES-54151, v1.01), as
  an `.iso` that matches the Redump dump
  ([disc 12334](https://redump.info/disc/12334/)), or a CSO/ZSO of it if
  you use this project's tools (below).
- PCSX2.
- An xdelta patcher, such as Delta Patcher or xdelta UI.
- The mod's patch (`.xdelta`).

A patch only holds the changed bytes, so it works on exactly one
image: the Redump one.

## 1. Check your disc

Your `.iso` must match these values:

| | |
|---|---|
| Size | 3,548,184,576 bytes |
| CRC-32 | `1c34e97e` |
| MD5 | `adadf32f4fd418b60632813b011c3388` |
| SHA-1 | `78771805294c924b68fe4aa01ad52f70229abb9d` |

Any hashing tool works. With this project's tools:

```bash
python SRC/extract_disc.py verify "Let's Make a Soccer Team! (Europe, Australia) (En,Fr,De,Es,It).iso"
```

**A compressed image (CSO, ZSO, CHD) won't patch in Delta Patcher.** It
stops with "The file you are trying to patch is not the right one".
Decompress it to `.iso` first, check the hashes, then patch. You can
compress the patched image again afterwards. This project's tools read
these images directly, so you can skip that step: check it, then apply
the patch to it, and you get a patched `.iso`:

```bash
python SRC/cso.py check disc.cso
python SRC/chd.py check disc.chd
python SRC/vcdiff.py apply disc.chd mod.xdelta modded.iso
```

A CHD can take a while: these tools decode it in Python, about ten
minutes for the whole disc, where `chdman extractdvd` takes seconds. A
CHD made with zstd compression needs Python 3.14 or later.

## 2. Apply the patch

In Delta Patcher, choose your `.iso` as the original file and the
`.xdelta` as the patch, then apply. Keep a copy of the original image:
other mods need it too. Or, with this project's tools:

```bash
python SRC/vcdiff.py apply disc.iso mod.xdelta modded.iso
```

Then boot the patched image in PCSX2 as usual.

## 3. Your saves

### A modded disc can have its own saves

A mod built with `--mod-saves` saves to different folders on the
memory card: careers go to `BESLES-54151-M000` and up instead of
`-G000`, and the VS data to `BESLES-54151-D000` instead of `-C000`.
The original game never sees these saves, and the modded game never
sees the original's. So a mod can't spoil your original careers, and
teams from a modded game can't be carried into the original's VS mode
or Virtua Pro Football. Importing a Virtua Pro Football edit player
still works. Details: [`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc).

A mod built without it uses the normal folders. Use a separate memory
card for it, or keep a copy of your card, if you want your careers
safe.

### Taking a career over to a modded disc

To carry an existing career to a `--mod-saves` disc, copy it to the
modded name. The original stays as it is.

- On a **folder card** (a folder named `<card>.ps2`):

  ```bash
  python SRC/save.py rename <card>/BESLES-54151-G003 <card>
  ```

  copies `BESLES-54151-G003` to `BESLES-54151-M003`.
- On a **card file** (a single `.ps2` file):

  ```bash
  python SRC/ps2mc.py copy Mcd001.ps2 Mcd001-new.ps2 BESLES-54151-G003 BESLES-54151-M003
  ```

  then use `Mcd001-new.ps2` as the card (`ps2mc.py` never changes the
  card it reads; see [`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md)).

A career started on the original game plays on under the mod's rules
from then on. Some changes only show at certain times: the season plan,
for example, can only be set at the start of a season.

### PCSX2 settings and patches

A mod that changes the game's program gets its own PCSX2 CRC (the
patcher's builder prints it, for example `SLES-54151_2CB2B141`).
PCSX2 keeps that disc's settings and savestates apart from the
original's, and loads `.pnach` patches by it too. A patch made for the
original, such as the widescreen patch for CRC `3CB245D5`
([`WIDESCREEN.md`](DOC/WIDESCREEN.md)), won't load on the modded disc. Copy
it under the new CRC's name to try it; that combination hasn't been
tested.

Savestates don't carry between the original and a modded disc. Use the
memory card.

### Editing a save

The save editor opens a career on either kind of card:

```bash
python SRC/saveedit.py open <card>/BESLES-54151-G000   # a folder card
python SRC/saveedit.py open Mcd001.ps2                 # a card file: pick a save
```

It backs the save up (and a card file's whole card) in `<card>.bak`
beside the card before writing, and File > Save to new slot keeps the
original untouched. **Close the game in PCSX2 first**, so it doesn't
write the card over your edit. How to use it, page by page:
[`USAGE.md`](USAGE.md#the-save-editor).

## 4. Building a patch

For people who make the mod. Set the project up as the README says,
then build a modded image from the Redump one:

```bash
python SRC/patch_disc.py patch disc.iso lmaster.iso --mod lmaster-full
```

The switches:

| Switch | What it does |
|---|---|
| `--mod lmaster-full` | LMASTER full: everything below, with the modded disc's own save folders (`--mod-saves`), which it always includes |
| `--mod lmaster-lite` | LMASTER lite (also `--mod lmaster`), the fixes only: main sponsor negotiation, the rival's own manager, the World National Cup's results viewable, training camps that train their own type in their own towns, Santiago's camp description, Canberra's camp clubs, the drill names, 18-month injuries that can't come out as short as a light one, injuries to players of 35 and over at full fatigue picked from the right table, Virtua Pro Football edit players keeping their best play styles, season tickets by club status, PR events whose chance follows the business cycle as intended, the cut PR event Renew Mobile Site, overseas popularity that a rank-2 player no longer multiplies by ten, and European Club Cup popularity for the last 16 instead of the last 32 ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)) |
| `--mod harder-economy` | dearer facilities (much dearer at the top), tickets up to £80, dearer advertising, and smaller late-game sponsor, TV and season-ticket income ([`ECONOMY.md`](DOC/ECONOMY.md)) |
| `--mod balance` | injuries of six months or longer about twice as common, and the two-month and nine-month injury lines back; overseas bases, their investment and upkeep twice as dear; transfer fees twice as high, up to £250M; a bigger fanbase selling more merchandise and drawing more fans and TV money; merchandise stock that costs half its price to make; PR events twice as dear; camps twice and tours three times as dear ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)) |
| `--mod league-balance` | league schedules where no club plays more than two games running at home or away |
| `--mod-saves` | the modded disc's own save folders (above) |

`python SRC/patch_disc.py` with no arguments lists every switch. The
mod editor (`python SRC/editor.py open`) does the same through File >
Build disc, with a box for each switch and a button for each LMASTER
build, and adds the files you edited.

Then make the patch to share:

```bash
python SRC/vcdiff.py make disc.iso lmaster.iso lmaster.xdelta
```

It prints the SHA-1s of the original, the result and the patch; give
players the result's SHA-1 so they can check their patched image.
Share only the `.xdelta`, never the disc image or files from it
([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod)).
