<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Installing a mod

A guide for players: how to play a mod made with this project. Check
your disc, apply the patch, and keep your saves safe. Sections 1 and 2
need Python only for the optional commands shown; moving a career to
a modded disc (section 3) uses it. Section 4 is for people who build
a patch; the [README](README.md) covers setting the project up.

For help, and to share what you've made, there's the
[LMAST/SFCC English Fan Discord](https://discord.gg/7DNrGye9TZ).

## What you need

- The PAL disc of *Let's Make a Soccer Team!* (SLES-54151, v1.01), as
  an `.iso` that matches the Redump dump
  ([disc 12334](https://redump.info/disc/12334/)), or a CSO/ZSO/CHD of
  it if you use this project's tools (below).
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
Decompress it to `.iso` first, check the hashes, then patch. This
project's tools read these images directly, so you can also check one
and apply the patch to it, which gives a patched `.iso`:

```bash
python SRC/cso.py check disc.cso
python SRC/chd.py check disc.chd
python SRC/vcdiff.py apply disc.chd mod.xdelta modded.iso
```

A CHD takes about ten minutes, since these tools decode it in Python. A
CHD made with zstd compression needs Python 3.14 or later.

## 2. Apply the patch

In Delta Patcher, choose your `.iso` as the original file and the
`.xdelta` as the patch, then apply. Keep a copy of the original image:
other mods need it too. Or, with this project's tools:

```bash
python SRC/vcdiff.py apply disc.iso mod.xdelta modded.iso
```

Then boot the patched image in PCSX2 as usual. If the patcher refuses
your image, it isn't the Redump one: check the hashes again.

## 3. Your saves

### A modded disc can have its own saves

A mod built with the `saves` group (`--mod-saves`; the LMASTER Mod's
full and max editions always have it) saves to different folders on the
memory card:

| | Original game | LMASTER full | LMASTER max |
|---|---|---|---|
| careers | `BESLES-54151-G000` and up | `BESLES-54151-F000` and up | `BESLES-54151-M000` and up |
| VS data | `BESLES-54151-C000` | `BESLES-54151-V000` | `BESLES-54151-V000` |

A build that is not one of those two editions but has `--mod-saves` uses
`-M` for careers when it turns on any switch of the difficulty groups,
and `-F` otherwise.

The original game never sees these saves, and the modded game never
sees the original's, so a mod can't spoil your original careers.
Importing a Virtua Pro Football edit player still works. Details:
[`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc).

A mod built without it uses the normal folders. Use a separate memory
card for it, or keep a copy of your card.

Savestates never carry between two different discs, original or
modded: use the memory card.

### Taking a career over to a modded disc

A disc with the third tier (LMASTER full and max) needs a new career:
the third tier changes the save's layout, so an older career won't
load ([`SAVE_FORMAT.md`](DOC/SAVE_FORMAT.md#the-bigger-save---mod-third-tier)).
A career from the original game plays on under the rules of any other
mod.

To carry a career to a `--mod-saves` disc, copy it to the modded name.
The original stays as it is.

- On a **folder card** (a folder named `<card>.ps2`):

  ```bash
  python SRC/save.py rename <card>/BESLES-54151-G003 <card> F
  ```

  copies `BESLES-54151-G003` to `BESLES-54151-F003` (give `M` for
  `-M003`). Without a letter, `rename` takes a modded save back to the
  original name.
- On a **card file** (a single `.ps2` file):

  ```bash
  python SRC/ps2mc.py copy Mcd001.ps2 Mcd001-new.ps2 BESLES-54151-G003 BESLES-54151-F003
  ```

  then use `Mcd001-new.ps2` as the card (`ps2mc.py` never changes the
  card it reads).

### PCSX2 patches

PCSX2 names a game's settings, savestates and `.pnach` patches by its
serial and a CRC of the executable. A mod that changes the executable
gets its own CRC (the patcher prints it at the end of a build), so a
`.pnach` made for the original, such as the widescreen patch
([`WIDESCREEN.md`](DOC/WIDESCREEN.md), named for the original's
`SLES-54151_3CB245D5`), won't load on it. Copy it under the new CRC's
name to try it; that hasn't been tested.

### Editing a save

The save editor opens a career on either kind of card; see
[`USAGE.md`](USAGE.md#the-save-editor). **Close the game in PCSX2
first**, so it doesn't write the card over your edit.

## 4. Building a patch

For people who make the mod. Set the project up as the README says,
then build a modded image from the Redump one:

```bash
python SRC/patch_disc.py patch disc.iso lmaster.iso --mod lmaster-full --copies --dat DAT
```

`--copies` and `--dat` are needed for LMASTER full and max: the third
tier and the real names change files the game also keeps copies of,
and the patcher finds those copies through `DAT/`.

`--mod` takes an edition, a group or a single switch, or several
separated by commas (`--mod lmaster-lite,harder-economy`). There are
three editions:

| Edition | What it is |
|---|---|
| `lmaster-lite` | the fixes: the first six groups below. Careers keep the original game's save folders |
| `lmaster-full` | lite, plus `leagues`, `restorations`, `names`, `stadiums`, `graphics` and `saves` |
| `lmaster-max` | full, plus the difficulty groups `harder-economy` and `balance` |

Each group holds the switches of one feature:

| Group | In | What it does |
|---|---|---|
| `training-fixes` | lite | training camps, drill names and the salesman's items work as intended |
| `injury-fixes` | lite | two injury-table errors fixed |
| `club-fixes` | lite | sponsor negotiation, season tickets, PR events, popularity and moving advert boards |
| `match-fixes` | lite | the rival's manager, pressing, national cups a turn earlier, and the Virtua Pro Football import |
| `text-fixes` | lite | wrong lines in the game's text |
| `title-screen` | lite | a banner on the title screen naming the LMASTER Mod, its version and its edition |
| `leagues` | full | a hidden third tier under each second division, and balanced league schedules |
| `restorations` | full | the cut injury condition lines |
| `names` | full | real names for leagues, clubs, stadiums and national teams, and your club's stadium named after you |
| `stadiums` | full | every club at a ground of its real size, with sponsor boards |
| `graphics` | full | LMAST Realism's crests and match pictures, random sponsors and kit suppliers (the Italian, Spanish and Dutch clubs' licensed kits become generated ones), and the game's main text in Roboto Condensed |
| `saves` | full | the modded disc's own save folders (`--mod-saves`) |
| `harder-economy` | max | dearer facilities and advertising, smaller sponsor and TV fees, fewer season tickets sold |
| `balance` | max | more long injuries, dearer transfers, camps, tours, PR and overseas bases, slower reputation |
| `test-tools` | none | the tutorial skip and the developers' debug menu, for testing |

Some switches need files that are not in this repository:

- **The Roboto Condensed font** (`RobotoCondensed[wght].ttf`) for
  `modern-font` (group `graphics`) and `title-banner` (group
  `title-screen`): give it with `--font <file>`, or the patcher finds
  it in a LMASTER-Mod clone's `fonts` folder beside this project or in
  your system's fonts.
- **The LMAST Realism pack** for `realism` (group `graphics`): a clone
  at `../LMAST-Realism`, or `--realism <folder>`.
- **The banner's version** (optional): `--version <x.y.z>`, else the
  `VERSION` file of a LMASTER-Mod clone beside this project. Without
  one the banner shows only the edition.

An edition or group that holds `modern-font`, the banner or `realism`
leaves it out, with a note, when its file is missing. Naming the
switch itself, as in `--mod modern-font`, without its font file is an
error.

`python SRC/patch_disc.py switches` prints every edition, group and
switch with a line on what it does, and
[`LMASTER_MOD.md`](DOC/LMASTER_MOD.md#the-switch-levels) has the
details. The mod editor does the same through File > Build disc
([`USAGE.md`](USAGE.md#building-a-disc-or-a-patch)).

Then make the patch to share:

```bash
python SRC/vcdiff.py make disc.iso lmaster.iso lmaster.xdelta
```

It prints the SHA-1s of the original, the result and the patch; give
players the result's SHA-1 so they can check their patched image.
Share only the `.xdelta`, never the disc image or files from it
([`REBUILD.md`](DOC/REBUILD.md#sharing-a-mod)).
