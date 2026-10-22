<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `pmplayer.bin`: Virtua Pro Football's edit players

Virtua Pro Football (VPF) runs on the same engine as this game. Its
Player Edit saves up to 23 players in `pmplayer.bin`, in its memory-card
folder `BESLES-54153FASYS00` (the Japanese VPF's is
`BISLPM-66324FASYS00`). This game's player editor imports one of them
into a career as the edit player, id `0x7cce`
([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-edit-player-from-virtua-pro-football)).
This doc covers the file and what the import makes of each field.
`SRC/pmplayer.py` reads and writes it.

## Who reads it

All in `SAVEPRG.REL`. **Confirmed from the game code:**

| Address | Symbol | What it shows |
|---|---|---|
| `0x3eee0` | (load `pmplayer.bin`) | calls the loader with a data size of `0x1c38` |
| `0x3ed60` | (loader) | decrypts the whole file (`0x32358`) with the key string at `0x4d310` → `0x547f0`, `_FC_ACT_2005`, then checks `crc16(first 0x1c38 bytes)` (`0x31470`) against the u32 after them |
| `0x31470` | (CRC) | CRC-16 with the table at `0x53408`, start `0xffff`, result inverted: the same as this game's saves (`save.crc16`) |
| `0x3ec60` | (writer) | rounds the size up to a multiple of `0x400` (`0x3ee90`), zeroes the buffer, copies the data, stores the CRC after it and encrypts (`0x32478`) |
| `0x3a3b8` | (import loop) | for each of 23 slots whose s16 id at `0x0 + 2i` is ≥ 0, converts the record at `0x5c + i × 0x134` |
| `0x3e198` | (conversion) | clears a 0x100-byte edit work and a 0x2a0-byte `PlPinfo`, then fills the edit work's `PlPbase` (at `+0x4`) from the record (below) |
| `0x40650`, `0x41938` | `GetEditPlayerData`, `getEditPlayerData` | hand the converted edit work and `PlPinfo` to the player editor |

The Blowfish tables are the ones this game's saves use (`0x4bd78`,
`0x4bdc0`). The Japanese `SAVEPRG.REL` has the same key, tables and
conversion (at `0x3db60`).

## File layout

**Confirmed** (the code above), 0x2000 bytes once encrypted:

| Offset | Size | Field |
|---|---|---|
| `0x0000` | 23 × s16 | player ids; −1 is an empty slot. VPF numbers its players from 20,001 (`0x4e21`) |
| `0x002e` | `0x2e` | not read by the import (*empirical*: `0c 00 ff ff`, then zeros, on the PAL card; zeros on the Japanese one) |
| `0x005c` | 23 × `0x134` | the records |
| `0x1bf8` | `0x40` | not read by the import (*empirical*: a few non-zero bytes on the PAL card) |
| `0x1c38` | u32 | CRC-16 of `0x0000`–`0x1c37` |
| `0x1c3c` | – | zeros up to `0x2000` |

An empty file (all ids −1, everything else zero) has the CRC `0x027c`,
which is what the Japanese card's empty file holds.

## The record

**Confirmed** from the conversion at `0x3e198`. "`PlPbase` x" means the
edit work's `PlPbase` field x, named as in
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md) (`pbdata.PLAYER_FIELDS`). Bytes
not listed are VPF's alone; the import doesn't read them.

| Offset | Type | Field | What the import does |
|---|---|---|---|
| `+0x00` | u8 | nation | looks it up in 145 `{u32 nation, u32 VPF nation}` pairs at `0x4ce80` (`0x3dd78`) and stores the first match's nation, else 0 |
| `+0x01` | char[] | short name | copied to `PlPbase` name, at most 19 bytes (`strncpy` 0x13) |
| `+0x52` | char[] | surname | not read (*empirical*: the surname, "Binns") |
| `+0x68` | f32 | height | truncated to an integer, `PlPbase` height |
| `+0x6c` | f32 | weight | truncated, `PlPbase` weight |
| `+0x70` | u8 | foot | `PlPbase` leg |
| `+0x73` | u8 | position group | `PlPbase` shirt: 1, 4, 7 or 9 for 0–3 (bytes at `0x547e8`), 1 otherwise |
| `+0x78` | u16 | – | `PlPbase` castno, raised to at least 22,542 (`0x580e`) |
| `+0x7a`–`+0x80`, `+0x82`–`+0x88`, `+0x8a`, `+0x8e`–`+0x95`, `+0x97`–`+0x99`, `+0x9d`, `+0xa3`–`+0xa6`, `+0xa8`–`+0xb8` | u8 | abilities | copied to 54 `PlPbase` abilities (`pmplayer.ABILITY_COPY`). `+0xa9` also gives attack patterns A and B, `+0xaa` patterns C and D |
| `+0xb4`, `+0xb5` | u8 | SM, FW | also WG (ability 40) = `int(SM × 0.3f + FW × 0.7f)` |
| `+0x9a` | u8 | injury | `PlPbase` injury_res = 7 − value |
| `+0x9b` | u8 | weak foot | `PlPbase` weak_foot = value × 2 + 1 |
| `+0x9c` | u8 | recovery | `PlPbase` recovery |
| `+0x9e` | u8 | fouls | `PlPbase` foul_avoid = (7 − value) × 2 + 1 |
| `+0xa0` | u8 | pressure | `PlPbase` pressure = value ÷ 14 |
| `+0xa1`, `+0xa2` | u8 | concentration, nerve (0–7) | abilities 32 and 27 = value × 14 + 1 |
| `+0xb9`–`+0xce` | u8 × 22 | play-style ratings | see below |
| `+0xcf`–`+0xde` | u8 × 16 | skills | a non-zero byte i sets bit i of `PlPbase` skills (`0x3e170`) |
| `+0xdf`–`+0xe9` | u8 × 11 | tendencies | copied to `PlPbase` tendency |
| `+0xea`, `+0xeb` | u8 | ball touch, dribble style | copied |
| `+0xf8`–`+0x129` | `0x32` | – | copied as is to the edit work `+0xb8`–`+0xe9`, outside the `PlPbase` |
| `+0x12d`–`+0x133` | u8 × 7 | kit style | copied to `PlPbase` sleeves, wristband, gloves, gk_cap, gk_gloves, gk_pants, boots |

VPF stores abilities as 1–99 and the import copies them unchanged.

**What the import sets itself.** Age 17; rank 12, or 13 when club 1
ranks 23 or lower (`pwkOteam_GetRank`); intelligence 0. Random:
tone, professionalism, loyalty, star quality, the 4 explode types,
motivation and condition types, potential, the 3 growth types
(`0x3e0f8`), travel, policy, adaptability, the 8 dissatisfaction
weights, and abilities 45–52 (the formations), 54 (possession) and 63
(attack pattern E), each 51–90. The main position isn't in the record:
`plPinfo_InitAbil` works out the position aptitudes from the
abilities, and `0x3ddc8` picks the best (stored at `PlPbase +0x1c`,
`PlPinfo +0x4` and `+0x1b4`).

**Play styles (a bug in the import).** `0x3df10` copies the 22 ratings
and means to sort them, then keep up to five styles rated 70 or more.
But its compare function (`0x3df00`) subtracts the two pointers instead
of the ratings they point to (the position sort's compare, `0x3ddb0`,
does dereference). So the order never changes: style slot t (1–4) gets
style t when byte `+0xb9 + t` is 70 or more, slot 0 stays empty, and
the other 17 ratings are never imported. G.Binns (below) is rated 86 in
byte `+0xb9` and came into the career with no styles.

The 22 elements are pointers to the rating bytes, and the slot loop
after the sort (`0x3e050`–`0x3e0bc`) takes the first five whose rating
is 70 or more, so the sort is meant to put the best first.
`patch_disc.py --mod vpf-styles` (in `--mod lmaster`) rewrites the
compare's 4 words to load both ratings and return b − a: it loads the
two pointers and the second rating, then jumps (an absolute `j`; the
executable never moves, and no relocation covers these words) to the
tail of the executable's `strcmp` at `SLES 0x31a5b4`, `lbu $v0,0($a1);
jr $ra; subu $v0,$v1,$v0`. Checked in a small MIPS simulator with that
tail read from the executable: the result is rating b − rating a, ties
0. Style 0 is "none" in the game's list, so a top rating in byte
`+0xb9` still comes in as an empty slot; that is the import's own
numbering, not this bug.

`pmplayer.styles(rec, fixed)` gives either import's slots, and
`pmplayer.py check` says which one a career's styles match (equally
rated styles may come in either order).

**Tested in PCSX2** (user screenshot, `LMAST-test-vpfstyles.iso` with
the `LMAST-vpftest.ps2` card): V. Drake, edited with `pmplayer.py set`
to 190 cm and rated 95/90/88/80 in styles 5, 12, 17 and 3 (84 in byte
`+0xb9`), was imported into career G000 at the 2012–2013 season break
(after G.Binns, its earlier edit player, was released). The player
editor's result showed 190 cm and style icons in slots 1, 2, 3 and 5,
slot 4 empty: the fixed import's `[5, 12, 17, 0, 3]`, with byte `+0xb9`
(84, style 0, "none") ranked fourth. The retail import would give one
style, in slot 4. So the edited file imports, and the sort works.

## Tested

**Checked against a career** (`pmplayer.py check`): save G000 on the
user's card holds G.Binns, imported from slot 1 of the card's
`pmplayer.bin`. Every field the conversion computes from the record
matches the career's edit work: name, nation (38 → 1), age, height,
weight, foot, shirt, castno, the derived personality values, the kit
style, skills, tendencies, all 54 copied abilities, WG, nerve and
concentration, the empty style slots, and the 0x32 bytes at `+0xb8`
(28 checks, none differ).

Both cards' files (PAL with 2 players, Japanese with none) round-trip
byte for byte. No edited file has been imported in game yet
([`TODO.md`](../TODO.md) section 7).

## Editing

```bash
python SRC/pmplayer.py info <card>
python SRC/pmplayer.py show <card>/BESLES-54153FASYS00/pmplayer.bin 1
python SRC/pmplayer.py set <card>/BESLES-54153FASYS00/pmplayer.bin out.bin 1 name=P.Drake height=191 shot_skill=99 style_1=85
python SRC/pmplayer.py check <card>/BESLES-54153FASYS00/pmplayer.bin <card>/BESLES-54151-G000
```

`set` edits fields of a used slot by the names `show` prints, within
the ranges the import handles (abilities 1–99, 0–7 ratings, kit styles
as in `pbdata.py`), and writes a new file with its CRC. The ids and the
bytes the import doesn't read are kept. To use the file, copy it over
`pmplayer.bin` in the card's `BESLES-54153FASYS00` folder (keep a
backup); PCSX2 folder memory cards hold it as a plain file.

Once a player is in a career, `save.py set edit:<field>=...` and the
save editor's Edit player page change the career's copy
([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-edit-player-from-virtua-pro-football)).

`pmplayer.py roundtrip` re-encodes every field of every record and
rebuilds the encrypted file. `pmplayer.py selftest` (in `regress.py`)
builds an empty file and checks its CRC, then makes a player through the
same edits as `set` and reads every field back.

## Still unknown

- The record bytes the import doesn't read (`+0x15`–`+0x51` apart from
  the names, `+0x81`, `+0x89`, `+0x8b`–`+0x8d`, `+0x96`, `+0x9f`,
  `+0xa7`, `+0xad`, `+0xec`–`+0xf7`, `+0x12a`–`+0x12c`), the header
  bytes `0x2e`–`0x5b` and the tail `0x1bf8`–`0x1c37`: VPF's own data.
- What the `+0x78` value and the 0x32 bytes copied to the edit work
  `+0xb8` do in this game (face or body data from VPF's editor?).
- Whether VPF itself accepts a file edited outside its editor (the CRC
  is the same, but VPF may check its own ranges).
- How VPF numbers a new player's id, so a player could be added to an
  empty slot.
- `file.inf`'s check: its CRC over the first 0x20 bytes doesn't match
  the u32 after them, so it may use another length.

## Checking the claims

```bash
python SRC/pmplayer.py selftest
python SRC/pmplayer.py roundtrip <card>
python SRC/snr2.py dis ISO/DLL/SAVEPRG.REL 3e198 700 --sles ISO/SLES_541.51   # the conversion
python SRC/snr2.py dis ISO/DLL/SAVEPRG.REL 3a3b8 40 --sles ISO/SLES_541.51    # the slot loop
python SRC/snr2.py dis ISO/DLL/SAVEPRG.REL 3ded8 20 --sles ISO/SLES_541.51    # the style compare
```
