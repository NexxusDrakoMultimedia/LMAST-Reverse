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

A mod built with `--mod-saves` (LMASTER full and max always are) saves
to different folders on the memory card:

| | Original game | LMASTER full | LMASTER max |
|---|---|---|---|
| careers | `BESLES-54151-G000` and up | `BESLES-54151-F000` and up | `BESLES-54151-M000` and up |
| VS data | `BESLES-54151-C000` | `BESLES-54151-V000` | `BESLES-54151-V000` |

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

A mod that changes the game's program gets its own PCSX2 CRC (the
patcher prints it, for example `SLES-54151_2CB2B141`), so a `.pnach`
made for the original, such as the widescreen patch
([`WIDESCREEN.md`](DOC/WIDESCREEN.md)), won't load on it. Copy it under
the new CRC's name to try it; that hasn't been tested.

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
separated by commas (`--mod lmaster-lite,harder-economy`):

| Name | What it is |
|---|---|
| `lmaster-lite` | the fixes: groups `training-fixes`, `injury-fixes`, `club-fixes`, `match-fixes`, `text-fixes` |
| `lmaster-full` | lite, plus `leagues` (the third tier, balanced schedules), `restorations` (the cut injury lines), `names` (real names, your own stadium), `stadiums` (real grounds, sponsor boards) and `saves` |
| `lmaster-max` | full, plus the difficulty groups `harder-economy` and `balance` |
| `--mod-saves` | the modded disc's own save folders (group `saves`) |

`python SRC/patch_disc.py switches` prints every group and switch with
a line on what it does, and
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
