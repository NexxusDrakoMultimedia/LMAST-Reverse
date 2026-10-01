<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/SOUND`: the menu music and sound-effect banks

`DAT/SOUND` (28 files, 21 MB, plus `CVS/`) is folder id **6** in the
game's file manager ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). Every file is
one `ps2_DTPK` sound bank: Sega SoundFactory tone tables (`TBLD`) and
PS-ADPCM samples (`VAGD`), played by the IOP driver `SNDFI.IRX`. The bank
format, the songs and the instruments are described in
[`GAME_DIR.md`](GAME_DIR.md#the-soundmap-banks), which also covers the 40
banks inside `GAME/SOUNDDAT.PAC`. This page says which bank is which and
how the game picks them.

The commentary, the crowd chants, the ambience and the rest of the music
are ADX streams in the disc's `AUDIO` folder, outside `DATA.CVM`
([`AUDIO_DIR.md`](AUDIO_DIR.md)).

`python SRC/sounddat.py music ISO/SLES_541.51 DAT/SOUND` prints the two
tables below and checks them against the banks. `python SRC/sounddat.py
songs DAT/SOUND` lists the songs, `midi` and `wav` render them.

| File | Bank index | Contents |
|---|---|---|
| `SYS_SE.DAT` | 0 | 20 sound effects, the menu sounds. **confirmed** loaded |
| `MAP01.DAT`–`MAP10.DAT` | 1–10 | sequenced music: 41 songs with the bank's own instruments. **confirmed** |
| `MAP11.DAT`–`MAP23.DAT` | 11–23 | one stereo piece each (two samples): the jingles before a full match and the quick-match music (identified by ear, [`GAME_DIR.md`](GAME_DIR.md#the-soundmap-banks)). **confirmed** loaded |
| `EFFECTS.DAT` | none | 6 sound effects. Not named in the code |
| `TRAINING.DAT` | none | 14 sound effects. Not named in the code |
| `EVENT_SE.DAT` | none | 10 sound effects. Not named in the code; the code names `AUDIO/EVENT_SE.AFS` instead |
| `PACK0.DAT` | none | 2 sound effects and one 349-second song on all 16 channels. Not named in the code |

None of these files is in a `PRELOAD` pack, and none is a copy of another
file on the disc (**empirical**).

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `SLES 0x35cb54` | (bank table) | 24 records of `0x1c` bytes: `SYS_SE.dat`, then `map01.dat`–`map23.dat` (below) |
| `SLES 0x115540` | `FC_EURO_SOUND_MANAGER::CFcEuro_ChangeSoundData(int)` | loads a bank by its index in that table |
| `SLES 0x114fe8`, `0x114f20` | `CFcEuro_SoundManager::PlayMidi`, `PlaySE` | play a song or an effect from a loaded bank |
| `SLES 0x5190d8` | (music table) | 63 records of `0x18` bytes, one per music id (below) |
| `SLES 0x103bd4`–`0x103c18` | `FC_EURO_BGM_CALLBACK::CFcEuro_ChangeBgm::Execute` | indexes the music table by the music id at `+0x1c` (1000 = none); for a DTPK song it creates `CFcEuro_ChangeSoundData` with the record's bank index |
| `SLES 0x35d8c8` | (string) | `CDV:/Audio/event_se.afs` |

The strings `EFFECTS`, `TRAINING`, `PACK0` and `event_se.dat` appear
nowhere in the executable or the overlays.

## The bank table (`SLES 0x35cb54`)

| Offset | Type | Field |
|---|---|---|
| `+0x00` | `char *` | file name (folder 6) |
| `+0x04` | u32 | `TBLD` size |
| `+0x08` | u32 | `VAGD` size |
| `+0x0c` | `u32 *` | the bank's request words |
| `+0x10` | u32 | number of request words |
| `+0x14` | u32 | `0x64` for `SYS_SE`, 0 for the rest. Not traced |
| `+0x18` | u32 | 2, except 0 for `map23`. Not traced |

The `TBLD` and `VAGD` sizes match the files' own headers for all 24 banks
(**empirical**, `sounddat.py music` checks it).

A **request word** is what the driver is asked to play: {u8 sub-area
kind, u8 sub-area id, u16 entry}. Kind `0xa8` is a song and `0xa9` an
effect, and the id is the sub-area's id in the bank's song area
([`GAME_DIR.md`](GAME_DIR.md#songs-sequences)). `map01`'s two songs are
`0x000000a8` and `0x000100a8`. The banks list one request per song (2, 6,
5, 5, 5, 6, 3, 3, 3, 3, then 1 each), and every one resolves to a song in
the file. `SYS_SE` lists 18 requests: 0, then effects 0–4, 6 and 8–18
of sub-area 0. The file has 20 effects (0–19), so 5, 7 and 19 aren't
listed.

## The music table (`SLES 0x5190d8`)

Each music id is one of two kinds of record (**confirmed** that `+0x00`
picks the path and `+0x04` is the bank index; the other fields are
**empirical**):

| Offset | DTPK song (`+0x00` = 0) | Stream (`+0x00` = 1) |
|---|---|---|
| `+0x04` | bank index, 1–23 | 0 |
| `+0x08` | request word | track number |
| `+0x0c` | `0x200`–`0x1600` or 0, unknown | −1 |
| `+0x10` | 0 | 0, 22, 24 or 25 |
| `+0x14` | 0 | 0 or 1 |

| Music ids | Source |
|---|---|
| 1–2 | `map01` songs 0–1 |
| 3–5 | `map02` songs 0–2 |
| 9–13, 14–18, 19–23 | `map03`, `map04`, `map05`, songs 0–4 each |
| 30–32, 33–35, 36–38, 39–41 | `map07`, `map08`, `map09`, `map10`, songs 0–2 each |
| 42–54 | `map11`–`map23` |
| 0, 6–8, 24–29, 55–62 | streams |

So 45 music ids are DTPK songs and 18 are streams. **`MAP06` has no music
id**, and neither have `map02`'s songs 3–5. Other code could still play
them through `PlayMidi`; those callers weren't searched.

The 10 streams with `+0x10` = 0 use tracks 0–9 once each, and `BGM.AFS`
has 10 tracks (`bgm13`–`bgm21` and the ending). They are probably that
archive, but the stream path wasn't traced. Ids 57–62 are tracks 0–5 with
`+0x10` = 22, and ids 0 and 56 track 0 with 25 and 24.

Which screen asks for which music id isn't known yet: that needs the
callers of `CFcEuro_ChangeBgm`.

## CVS history

The folder's `CVS/ENTRIES` ([`CVS_DIR.md`](CVS_DIR.md)) dates the banks
August 2005 to January 2006. `map11`–`map23` were all committed together on
1 October 2005, and `SYS_SE` is at revision 1.12, the most edited.

## Still unknown

- Which screens play which music id (callers of `CFcEuro_ChangeBgm`), and
  the stream path: which archive `+0x10` selects.
- What bank fields `+0x14`/`+0x18` and music field `+0x0c` do.
- Whether anything plays `MAP06`, `map02` songs 3–5, or the four banks the
  code doesn't name.
- What each `SYS_SE` effect is.
