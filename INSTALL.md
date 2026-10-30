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

A mod built with `--mod-saves` (LMASTER full and max always are) saves
to different folders on the memory card. `G` and `C` are the original
game's career and VS folders; a modded disc uses its own letters:

| | Original game | LMASTER full | LMASTER max |
|---|---|---|---|
| careers | `BESLES-54151-G000` and up | `BESLES-54151-F000` and up | `BESLES-54151-M000` and up |
| VS data | `BESLES-54151-C000` | `BESLES-54151-V000` | `BESLES-54151-V000` |

Full and max keep their careers apart, because a career played with
max's harder economy isn't one to load without it, but share their VS
data. Discs built before 2026-10-27 used `-M` for careers (their content
is today's max) and `-D` for VS data.
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
modded name: `F` for LMASTER full, `M` for max. The original stays as
it is.

- On a **folder card** (a folder named `<card>.ps2`):

  ```bash
  python SRC/save.py rename <card>/BESLES-54151-G003 <card> F
  ```

  copies `BESLES-54151-G003` to `BESLES-54151-F003` (give `M` for
  `-M003`). Without a letter, `rename` takes a modded save back to the
  original names, and the original VS data to `-V`; `rename
  <card>/BESLES-54151-D000 <card> V` moves an older disc's VS data to
  the new name.
- On a **card file** (a single `.ps2` file):

  ```bash
  python SRC/ps2mc.py copy Mcd001.ps2 Mcd001-new.ps2 BESLES-54151-G003 BESLES-54151-F003
  ```

  then use `Mcd001-new.ps2` as the card (`ps2mc.py` never changes the
  card it reads; see [`PS2MC_FORMAT.md`](DOC/PS2MC_FORMAT.md)).

**LMASTER full and max need a new career.** Their third tier changes the save's
layout, so a career from the original game, or from LMASTER lite, won't
load on them even under the modded name. `python SRC/save.py convert`
can re-encode one, but the clubs and leagues the third tier adds start
empty in it; start a new career instead
([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-bigger-save---mod-third-tier)).

A career started on the original game plays on under the mod's rules
from then on (LMASTER lite and the other builds without the third
tier). Some changes only show at certain times: the season plan,
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
python SRC/patch_disc.py patch disc.iso lmaster.iso --mod lmaster-full --copies --dat DAT
```

(or `--mod lmaster-max`). `--copies` and `--dat` are needed for LMASTER
full and max: the third tier
changes files the game also keeps copies of, and the patcher finds and
updates those copies through the extracted `DAT/` folder.

The switches come in three levels: three editions, made of groups, made
of single switches ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels)).
`--mod` takes a name of any level, and several names separated by
commas (`--mod lmaster-lite,harder-economy`):

| Switch | What it does |
|---|---|
| `--mod lmaster-max` | LMASTER max, an edition: LMASTER full and the two difficulty groups, `harder-economy` and `balance`; careers save to `-M` |
| `--mod lmaster-full` | LMASTER full, an edition: LMASTER lite, `leagues` (the third tier and the balanced league schedules), `restorations` (the cut two-month and nine-month injury lines), `names` (the real names and your own stadium, `--mod real-names` and `--mod own-stadium`), `stadiums` (the Special stadium at 100,000 and every club's ground at its real size, `--mod special-stadium` and `--mod real-grounds`, and sponsors on every ground, `--mod sponsor-boards`), `title` (the opening movie only at boot, and demo matches between any two clubs, `--mod title-movie` and `--mod demo-teams`) and the modded disc's own save folders (`--mod-saves`), which it always includes; careers save to `-F` |
| `--mod lmaster-lite` | LMASTER lite (also `--mod lmaster`), an edition of the five groups of fixes: `training-fixes` (training camps that train their own type in their own towns, Santiago's camp description, Canberra's camp clubs, the drill names), `injury-fixes` (18-month injuries that can't come out as short as a light one, injuries to players of 35 and over at full fatigue picked from the right table), `club-fixes` (main sponsor negotiation, season tickets by club status, PR events whose chance follows the business cycle as intended, the cut PR event Renew Mobile Site, overseas popularity that a rank-2 player no longer multiplies by ten, European Club Cup popularity for the last 16 instead of the last 32) and `match-fixes` (the rival's own manager, the World National Cup's results viewable, Virtua Pro Football edit players keeping their best play styles) and `text-fixes` (messages the retail game gets wrong: the Game Over conditions for Spain and the Netherlands, the Spanish intro's club count, Al-Hyde's name; `--mod retail-text`) ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md)) |
| `--mod harder-economy` | dearer facilities (much dearer at the top), tickets up to £80, dearer advertising, and smaller late-game sponsor, TV and season-ticket income ([`ECONOMY.md`](DOC/ECONOMY.md)) |
| `--mod balance` | injuries of six months or longer about twice as common; overseas bases, their investment and upkeep twice as dear; transfer fees twice as high, more again by player rank (lesser players about four times the retail fee, the best up to £250M); club reputation rising half as fast; a bigger fanbase selling more merchandise and drawing more fans and TV money; merchandise stock that costs half its price to make; PR events twice as dear; camps twice and tours three times as dear ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#improvements)) |
| `--mod leagues` | the two league switches below |
| `--mod league-balance` | league schedules where no club plays more than two games running at home or away |
| `--mod third-tier` | a hidden third tier under each second division (England's English League 1 and the others): each season the second division's last club goes down and the tier's winner comes up, your second division has its real size, and finishing last in it ends the game after one season. The tier's clubs also play their nation's lower cup (the League Cup or Club Cup), which now starts in the first week of December. The game's messages state these rules, in all five languages. It needs a new career, `--copies` and `--dat`, and turns on `--mod-saves` itself ([`UID_LIMITS.md`](DOC/UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3)) |
| `--mod restorations` | the two-month and nine-month injury lines, cut before release, back in the condition line (`--mod injury-lines`) |
| `--mod names` | every league, competition, club and national team under its real name of the era (Highbury as Arsenal, the European League as the Champions League), and every club's stadium under its 2006-07 name (Old Trafford, Westfalenstadion), in all five languages (`--mod real-names`, which needs `--copies` and `--dat`); and your own club's stadium named after you, "\<your name\> Stadium", not your city (`--mod own-stadium`) ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#real-names)) |
| `--mod stadiums` | the Special stadium, the biggest you can build, holds 100,000 instead of 110,000 (`--mod special-stadium`); every other club plays at a ground of its real 2005-06 size, to the nearest 5,000 (Old Trafford 70,000, Stamford Bridge 40,000), with a look to fit its size (the biggest bowl only for 80,000 and up), and grounds of the same size look different (`--mod real-grounds`, which turns on `special-stadium`); every ground's advert boards drawn from all 205 sponsors (`--mod sponsor-boards`) ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#stadiums)) |
| `--mod title` | the opening movie plays once at boot, not again after each demo match on the title screen (`--mod title-movie`), and the demo match is between any two clubs at random, not a few famous ones (`--mod demo-teams`) ([`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-title-screen)) |
| `--mod-saves` | the modded disc's own save folders (above): careers to `-F`, or `-M` with any `harder-economy` or `balance` switch, VS data to `-V`; its group is `--mod saves` |

`python SRC/patch_disc.py switches` lists every edition, group and
switch. The mod editor (`python SRC/editor.py open`) does the same
through File > Build disc, with a button for each edition, a box for
each group that you can open to tick its switches one by one, the save
letters your choice gets, and adds the files you edited.

Then make the patch to share:

```bash
python SRC/vcdiff.py make disc.iso lmaster.iso lmaster.xdelta
```

It prints the SHA-1s of the original, the result and the patch; give
players the result's SHA-1 so they can check their patched image.
Share only the `.xdelta`, never the disc image or files from it
([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod)).
