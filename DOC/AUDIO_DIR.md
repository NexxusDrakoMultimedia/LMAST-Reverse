# `ISO/AUDIO/`: music, commentary and crowd audio

The streamed audio is outside `DATA.CVM`, in the disc's `AUDIO` folder: 18
CRI **AFS** archives holding CRI **ADX** audio, plus the opening movie
`OPMOVIE.SFD` (CRI Sofdec, not decoded here). The game uses CRI's ADX
library (`ADXF_LoadPartition`, `ADXF_LoadPartitionFromAfsNw`,
`ADXT_StartAfsLp` and more are among the named symbols in `SLES_541.51`).
The short sound effects are elsewhere, in `DAT/SOUND/*.DAT` (`ps2_DTPK`
banks, `SRC/sounddat.py`).

`python SRC/afs.py` lists the archives, checks every entry and decodes to
WAV.

## The archives

| File | Entries | Format | What |
|---|---|---|---|
| `BGM.AFS` | 10 | stereo 48 kHz | the music: `bgm13`–`bgm21` (45–75 s each) and `ending` (4 min 17 s). All loop |
| `OPEN.AFS` | 1 | stereo 48 kHz | `SakatsukuOpen1028_3db` (60 s): the opening movie's soundtrack (the video is `OPMOVIE.SFD`) |
| `VIC.AFS` | 1 | stereo 48 kHz | `vic00` (93 s), probably the victory music |
| `EVENT_SE.AFS` | 6 | stereo 48 kHz | looping ambience: `PRESS`, `PRESS_B`, `PUB_LARGE`, `PUB_SMALL`, `STADIUM_LARGE`, `STADIUM_SMALL` |
| `KANSEI.AFS` | 4 | stereo 24 kHz | looping crowd noise (歓声, cheering): `EF_B_AWAY`, `EF_B_HOME`, `SND_CHR_BASE_B_20`, `TRAINING_AMBI` |
| `OUENKA.AFS` | 622 | stereo 24 kHz | crowd chants (応援歌): `ap_*` (232) and `sp_*` (390), by region or team (`eng` 92, `ita` 92, `spa` 86, `fra` 78, `ger` 62, `ned` 62, `bra`, `arg`, `usa`, `afr`, `asi`, `arb`, `oeu`, `all`) and a per-player set (`plyr`, 74) |
| `JYONAI_A.AFS` | 50 | stereo 24 kHz | stadium announcements (場内, in the ground): `tannoy00`–`tannoy49` |
| `BC_ENG/FRA/GER/ITA/SPA.AFS` | 12,899 each | mono 24 kHz | match commentary, 3–4 hours per language, built from short pieces: 0.9 s on average in English, the longest 8.6 s, and the first entries (`WC*`, `WCPL_*`) a quarter of a second. Each clip's data fills exactly its header's sample count. Many short ones are town names (`*_TWN_*`). Entry *i* is named by entry *i* of `DAT/GAME/FNAME<lang>` (see [`GAME_DIR.md`](GAME_DIR.md)) |
| `BC_ENG2/FRA2/GER2/ITA2/SPA2.AFS` | 6 each | mono 24 kHz | six more lines per language (`eng_ba_pfb_2000`–`2005`) |
| `BC_JPN2T.AFS` | 6 | mono 24 kHz | the same six lines in Japanese |

All 18 archives and all 65,225 entries pass `afs.py info`: every entry is
ADX encoding 3 (standard, unencrypted), 18-byte frames of 4-bit samples,
version 4.

`0FLIST.DIR` in the disc root lists the archives one per line
(`\Audio\bgm.afs`, `\Audio\event_se.afs`, … in the order 0 BGM, 1
EVENT_SE, 2 VIC, 3–7 BC_ENG/FRA/GER/ITA/SPA, 8 OUENKA, 9 JYONAI_A, 10
KANSEI, 11 OPEN, 12–17 BC_SPA2/ITA2/GER2/FRA2/ENG2/JPN2T). That is the
form CRI's file system reads to open files by number, so the line is most
likely the id the game uses for each archive; the code that loads it
hasn't been traced (the name isn't in the executable as text).

## AFS

Little-endian:

| Offset | Type | What |
|---|---|---|
| `0x0` | char[4] | `AFS\0` |
| `0x4` | u32 | entry count *n* |
| `0x8` | *n* × {u32 offset, u32 size} | entries, each starting on a `0x800` boundary |
| then | {u32 offset, u32 size} | the name table |

Name table: *n* × 48 bytes: `char name[32]`, six u16 (year, month, day,
hour, minute, second), and a u32 that holds the *previous* entry's size (a
known quirk of CRI's AFS tool). Every archive here has one.

## ADX

Big-endian header:

| Offset | Type | What |
|---|---|---|
| `0x00` | u16 | `0x8000` |
| `0x02` | u16 | header size − 4: the audio starts right after it, and `(c)CRI` ends just before |
| `0x04` | u8 | encoding, 3 |
| `0x05` | u8 | frame size, 18 |
| `0x06` | u8 | bits per sample, 4 |
| `0x07` | u8 | channels, 1 or 2 |
| `0x08` | u32 | sample rate |
| `0x0c` | u32 | samples per channel |
| `0x10` | u16 | high-pass cutoff (500 Hz in every file) |
| `0x12` | u8 | version, 4 |
| `0x13` | u8 | flags, 0 (not encrypted) |
| `0x24` | u32 | loop flag (only if the header reaches past `0x38`) |
| `0x28`, `0x30` | u32 | loop start and end sample |
| `0x2c`, `0x34` | u32 | loop start and end byte |

The commentary's headers end at `0x22` (audio at `0x28`), so they have no
loop fields; reading `0x24` there would hit `(c)CRI`. Music, ambience and
chants loop. Some chant headers pad the audio start past `0x800`.

Frames are 18 bytes per channel, channels interleaved frame by frame: a
u16 scale, then 32 signed 4-bit samples, high nibble first. Each sample is
`nibble × (scale + 1) + (c1 × s[−1] + c2 × s[−2]) >> 12`, clamped to 16
bits, with `c1`, `c2` computed from the cutoff and sample rate — the
standard ADX predictor, as vgmstream implements it. `afs.py wav` writes
16-bit PCM and adds a `smpl` chunk with the loop points.

## Checking

```bash
python SRC/afs.py info ISO/AUDIO
python SRC/afs.py list ISO/AUDIO/BGM.AFS
python SRC/afs.py wav ISO/AUDIO/BGM.AFS out/bgm
python SRC/afs.py wav ISO/AUDIO/BC_ENG.AFS out/commentary 1 2 3
```

## Still unknown

- Whether the commentary and tannoy clips sound right. The music, opening,
  victory tune, crowd loops and chants have been checked by ear and are
  right (pitch, speed, stereo, no crackle), as are the `DAT/SOUND` effect
  banks `SYS_SE` and `EFFECTS` decoded by `sounddat.py`.
- Which screens play which `bgm` track, and where `VIC` and the chants are
  used. `BGM.AFS` starts at `bgm13`, so the rest of the music is elsewhere:
  in the 41 sequenced songs of `DAT/SOUND/MAP01`–`MAP10` and the stereo
  pieces `MAP11`–`MAP23` (see [`GAME_DIR.md`](GAME_DIR.md#songs-sequences)).
- The loader that maps `0FLIST.DIR` lines to archives, and the commentary
  code that picks clips.
- `OPMOVIE.SFD` (MPEG video with ADX audio; not handled).
