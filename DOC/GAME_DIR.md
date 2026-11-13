<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/GAME`: in-match data, commentary and sound banks

`DAT/GAME` (156 files, 116 MB, plus `CVS/`) holds the data the match
engine loads: the spoken commentary and crowd sounds, the ball and cursor
models, the play books and the match AI's tables. `DLL/GAMEPRG.REL` loads
most of it (`sounddat.pac`, `playbook.bpb`, `cutinpack.bin`,
`shadowcolli.pac`, ... appear there as strings). The largest part is the
**commentary system**: `SOUNDDAT.PAC` plus 53 loose files that are
byte-for-byte copies of its pieces.

The `SOUNDDAT.PAC` piece offsets are **confirmed** against the table the
game itself uses in `GAMEPRG.REL`. The formats inside the pieces (TBL, BCR2,
BCB3, DTPK) are **empirical**, checked against every file on the disc.
`python SRC/sounddat.py info DAT/GAME/SOUNDDAT.PAC` checks the pack and
`SRC/sounddat.py` implements the pieces. The other files have their own
tools, named in the table below. The Japanese release's `GAME/` has no
loose commentary files and a smaller pack
([`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)).

## Directory overview

| Files | Format | Notes |
|---|---|---|
| `SOUNDDAT.PAC` | concatenation, see below | commentary tables + 40 sound banks |
| `ROUTEBOX_*.BCR`, `VBOX_*.BCB`, `*.BCV`, `*.TBL` | see below | 53 loose files equal to `SOUNDDAT.PAC` pieces byte for byte (2 `.BCR`, 8 `.BCB`, 1 `.BCV`, 42 `.TBL`; the pack holds 36 clip tables, 31 of them different, so several loose files equal the same piece), plus 11 older `.TBL`s that match no piece |
| `FNAME{EN,FR,GE,IT,SP,JP}.DAT/.TOC`, `BCFNAME.DAT/.TOC` | clip-name tables | names for `ISO/AUDIO/BC_<lang>.AFS` entries |
| `EFFECTS.DAT`, `TRAINING.DAT` | `ps2_DTPK` | one sound bank each (kind `H`). `DAT/SOUND` has same-named banks that are not copies ([`SOUND_DIR.md`](SOUND_DIR.md)) |
| `*.SNJ`, `*.SNO` | Ninja `NSIF` + `NSOB` (+`NSTL`, `NFN0`) | models: 7 balls (Teamgeist, Roteiro, Pelias, Total90, Finale, White, default), cursors (`CURSOL_ON*`), shadows (`D_SDW`, `N_SDW`), `PLAYER`, `KEY_PLAYER`. `python SRC/ninja.py info DAT/GAME` ([`NINJA_FORMAT.md`](NINJA_FORMAT.md)) |
| `*.SNM` | Ninja `NSIF` + `NSMO` | motion |
| `*.SNP` | Ninja `NSIF` + `NSNT` | node tree |
| `*.SVR` | `GBIX` + `PVRT` | textures ([`SVR_FORMAT.md`](SVR_FORMAT.md), `svr.py`). `GM_KEYHELP0-6` / `GM_TITLE0-6` are probably per-language sets; the code names only `gm_keyhelp.svr` / `gm_title.svr` |
| `*.SVM`, `EF001.BIN`, `FLARE.BIN` | `PVMH` | texture archives |
| `BALLMOTION`, `OPTMOTION*`, `PLAYERMOTION`, `SHADOWCOLLI`, `WALLCOLLI` | BINPAC | see [`PAC_FORMAT.md`](PAC_FORMAT.md) |
| `CUTINPACK.BIN` + `_HEADER.BIN` | KC@P of 277 `etc::PackData` entries | the match's cut-ins ([`PAC_FORMAT.md`](PAC_FORMAT.md#kcp), [`PLAYER_DIR.md`](PLAYER_DIR.md)). Every entry starts with a `CIB0` block (type 19); after it come Ninja models (types 20 and 24, 71 in all), `PVMH` textures (21, 71), motions (22, 3,357) and 7 `BMT1` blocks (23). 24 entries hold only the `CIB0` block (**empirical**, `packdata.py info --all`). `CIB0` and `BMT1` aren't decoded. The header is entry 9 of the seven `PRELOAD/GAMEFILE` packs ([`PAC_FORMAT.md`](PAC_FORMAT.md#kcp)) |
| `PLAYBOOK.BPB`, `COMBINATION.BPB` | play books | the players' and ball's paths, in metres: the corner and free-kick plays, and the tactics screen's 30 attack pattern diagrams: see [`BPB_FORMAT.md`](BPB_FORMAT.md) (`Pwk::PlayBookData`; `python SRC/bpb.py info DAT/GAME`). `COMBINATION.BPB` is entry 12 of the tactics screen's load list (`SLES 0x55b588`, **confirmed**) |
| `COMBINATION2.CBB/.CSB` | 540 combination records / 540 PRS-packed `SQB1` scripts | the combinations' data and scripts: see [`BPB_FORMAT.md`](BPB_FORMAT.md#combination2cbb-and-csb) |
| `BACK_MATCH.TBB` | TBB, 6 tables | lines of 8, 4, 4, 8, 1 and 1 bytes ([`TBB_FORMAT.md`](TBB_FORMAT.md) shows it as the example). No executable or overlay names it; its use is unknown |
| `TACTICS_PLAYBOOK_EDIT.TBB` | TBB, 1 table | 180 rows of 4 bytes. Entry 13 of the tactics screen's load list (`SLES 0x55b5b0`, **confirmed**), read through `CTacticsLoader::getPlayBookEditTable`; the row layout is open ([`BPB_FORMAT.md`](BPB_FORMAT.md#still-unknown)) |
| `AI_PARAM.BIN` | 467 × f32 | no reader found, by name or by content: see [`GAMEDATA_FORMAT.md`](GAMEDATA_FORMAT.md#ai_parambin). Identical on the Japanese release (`cmp`) |
| `GAMEDATA.BIN` | 4,131 records of 0x30 bytes | the match engine's table (loader slot 10); a few fields read: see [`GAMEDATA_FORMAT.md`](GAMEDATA_FORMAT.md) (`python SRC/gamedata.py info DAT/GAME`). Identical on the Japanese release (`cmp`) |
| `TEAM.TMB` | `TMB1` | team names, 3-letter codes, stadiums (`Highbury`/`LON`). Dated Mar 2005, not referenced by name. Probably stale |
| `CVS/` | CVS metadata | original lowercase names and revision numbers |
| `DUMMY.DAT` (0 bytes), `VBNAME.VBN` (`test0`) | junk | – |

## `SOUNDDAT.PAC`

There is no directory in the file. The `TBB1` header at offset 0 belongs
to the first piece (`ROUTEBOX_EU.BCR`), not to the pack. The offsets are
hardcoded in `GAMEPRG.REL` (see
[How the game indexes it](#how-the-game-indexes-it)).

| Range | Contents |
|---|---|
| `0x000000`–`0x162000` | 12 commentary slots of `0x1D800` bytes |
| `0x162000`–`0x1A26BB` | 36 `.TBL` clip tables, 16-aligned; groups restart on `0x800` boundaries |
| `0x1A2800`–`0xC6E800` | 40 `ps2_DTPK` sound banks, back to back, ending exactly at EOF |

### How the game indexes it

`DLL/GAMEPRG.REL` is an `SNR2` overlay linked at base 0, so its code
addresses equal file offsets and every absolute address is patched by
relocations at load time (external calls appear as `jal 0`). The offsets
live in a table of 143 records `{u32 offset, u32 size, u32 0, u32 0}` at
**`0x248540`–`0x248E30`**. It ends right before the `"sounddat.pac"`
string at `0x248E30`, which begins the file-request struct that the
loader fills. The records match the layout `SRC/sounddat.py` derives
exactly.

| Address | Records | Offsets relative to | Contents |
|---|---|---|---|
| `0x248540` | 42 | file | **level 0**: 0–11 slots (size = used bytes, 16-aligned), 12 = TBL group A `0x162000`, 13 = TBL group B `0x163000`, 14–16 = the three `L`+4×`J` bank groups, 17–41 = banks 15–39 |
| `0x2487E0` | 3 × 5 | bank group | banks of level-0 entry 14, 16, 15, in that order |
| `0x2488D0` | 10 × 5 | slot | the 5 pieces of slots 2–11. There is none for the JPN_TEST slots |
| `0x248BF0` | 11 | `0x162000` | TBL group A: the `*LOSSTIME*`, `*NOWTIME*`, `*SCORE*`, `KAI_*` tables |
| `0x248CA0` | 25 | `0x163000` | TBL group B: names, teams, `TAIKAI`, fixtures, rivals, `OUENKA_*`, `BN` |

Functions that use it (addresses = `GAMEPRG.REL` file offsets):

| Address | What it does |
|---|---|
| `0x9C88` | `size(i)`: `align_up(level0[i].size, 0x800)` |
| `0x9BD0` | `load(buf, i)`: stores `buf`, `level0[i].offset >> 11` (sector) and `size(i) >> 11` (sector count) at `+0x34/+0x38/+0x3C` of the `sounddat.pac` struct, then issues request 0xC through a virtual call |
| `0xA5A8` | loads a commentary slot. It gets `{b0, b1}` and picks level-0 `pair[b1][b0 != 0]` from the byte pairs at `0x265E98`: `(3,2) (5,4) (7,6) (9,8) (11,10) (1,0)`. So `b1` 0–4 = ENG, FRA, GER, ITA, SPA and 5 = JPN_TEST, and `b0 == 0` picks the `KANHA` slot |
| `0x9DA0` | `piece_offset(i, flag)`: gets the commentary language from `0xAB40`, uses it in a jump table (`0x265E00` / `0x265E20`, chosen by `flag`) to select that language's `0x2488D0`-block piece table, and returns `table[i].offset`. For language ≥ 5 it falls back to the ENG table. Because JPN_TEST's BCB is a different size, its later pieces would then be read at the wrong offsets |
| `0xA658`, `0xA6C8` | return pointers to slot pieces: `align_up(buf, 0x800) + piece_offset(...)` |
| `0xA7D0` / `0xA848` | load TBL group A (level 0 entry 12); `tbl_a(i)` = `align_up(buf, 0x800) + table[i].offset` |
| `0xA888` / `0xA8C0` | the same for group B. `0xA8C0` is called from 23 sites around `0x1B89E4`–`0x1B8FBC` (the commentary code) |
| `0x9FE0` | sets up the sound banks (called from `0x370C`), see below |

The bank setup at `0x9FE0` reads two bytes, `t = sel[0]` and `v = sel[1]`:

- **`t`** (0–3) chooses the common bank group:
  - through the bytes at `0x265E38 + t*20`: level-0 entry 15, 16, 14 or 15
  - through its matching `0x2487E0`-block sub-table (5 bank offsets per group)
  - so `t` = 3 is the same as `t` = 0
- **`v`** (0–6) chooses one per-`v` bank of each type:
  - a looped bank of 12–14 samples (13 in all but two), from the pairs at
    `0x265E3E + t*20 + v*2`
  - a 32-sample bank, from the pairs at `0x265E88 + v*2`

The level-0 indices these tables give are:

| `v` | Looped bank for `t` = 0 / 1 / 2 | 32-sample bank |
|---|---|---|
| 0 | 17 / 19 / 18 | 20 |
| 1 | 21 / 23 / 22 | 24 |
| 2 | 25 / 27 / 26 | 28 |
| 3 | 29 / 31 / 30 | 32 |
| 4 | 37 / 39 / 38 | 40 |
| 5 | same as 0 | same as 0 |
| 6 | 33 / 35 / 34 | 36 |

So banks 15–38 are six groups of three looped banks plus one 32-sample
bank, one group per `v` (for these banks, level-0 index = bank + 2). `v`
has seven values with 5 aliasing 0, which matches the seven country codes
elsewhere in the overlays (`du`, `fr`, `ge`, `it`, `jp`, `sp`, `uk`).
**What `t` and `v` mean is a guess.** Level-0 entry 41 (bank 39) isn't
selected by these tables. The second byte of each pair isn't a level-0
index and is still unknown.

### Commentary slots

Slot *k* is language `[JPN_TEST, ENG, FRA, GER, ITA, SPA][k/2]` with crowd
table `[KANNEUT, KANHA][k%2]`. Each slot holds, in order and zero-padded to
`0x1D800`:

| Piece | Loose copy | Length |
|---|---|---|
| EU routebox | `ROUTEBOX_EU.BCR` | runs to the next `TBB1` |
| language vbox | `VBOX_TABLE_<lang>.BCB` | `align16(TBB1 end field)` |
| crowd routebox | `ROUTEBOX_KAN.BCR` | runs to the next `TBB1` |
| crowd vbox | `VBOX_KANNEUT.BCB` / `VBOX_KANHA.BCB` | `align16(TBB1 end field)` |
| vbox index | `VBOX_TABLE_JPN_TEST_BCB.BCV` | 3 × the language vbox's record count |

The same `.BCV` is used in every slot. *KAN* is probably 観客 (spectators),
with *NEUT* for neutral and *HA* possibly for home/away. **Unconfirmed.**

#### `.BCR`: routebox

A TBB1 container whose tables are `BCR2` rather than `TBL1`:

```text
+0x00 'BCR2'  +0x04 u32 0x10  +0x08 u32 size  +0x0C u32 0
+0x10 ...     size bytes of record data (not decoded)
```

`ROUTEBOX_EU` holds 106 such tables and `ROUTEBOX_KAN` 11
(`python SRC/tbb.py info DAT/GAME`). After the TBB1's end-of-data field
there is a **0x350-byte trailer**. It starts with the magic `RBD0`, then
`u32 0x10` and a size (`0x340` in EU, `0x334` in KAN), and continues with
u16 values ending in `ff 00`. It differs between the two files and its
purpose is unknown.

#### `.BCB`: vbox table

A TBB1 with one `BCB3` table:

```text
+0x00 'BCB3'  +0x04 u32 0x10  +0x08 u32 size  +0x0C u32 N (records)
+0x10 N × {u32 item_off, u32 item_count}      offsets relative to 'BCB3'
      items: item_count × 6 bytes each, contiguous
      script area: variable-length u16 LE streams, to the end of data
```

Each item is `{u16 script_off, u16 flags?, u16 ?}`, and `script_off` always
points into the script area. The script streams mix clip IDs (e.g.
`0x2A7A` = `ENG_BA_CST_0473`) with small opcodes (`0x0001`, `0x0003`,
`0x003F`, `0x00A3`, ...). They look like commentary bytecode. **Not decoded.**

| File | Records | Items |
|---|---|---|
| `VBOX_TABLE_<lang>` (all 6) | 981 | 2232 |
| `VBOX_KANNEUT` / `VBOX_KANHA` | 82 | 82 |

#### `.BCV`

981 records of 3 bytes each (2,943 bytes), one per language-vbox
record. Read as little-endian 24-bit numbers they are all different;
the first ten run 0, 1, 2 ... 9, but the sequence does not keep
counting (the last is 11,023) (**empirical**). The meaning is not
decoded. The Japanese release's `SOUNDDAT.PAC` has no `.BCV` index
([`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)).

### `.TBL`: clip tables

```text
u16 BE rows
u8     cols
u16 BE id[rows * cols]      row-major
```

All 53 loose `.TBL` files fit this layout exactly (**empirical**; the file
length is `3 + 2 * rows * cols` in every one). Each `id` is an index into
`BC_<lang>.AFS` and `FNAME<lang>` (see below). Index 169 (`dummy_0001`) is
used as the "no clip" filler. Examples:

| Table | Rows × cols | Points at |
|---|---|---|
| `EU_WCP_NAME_F/_S` | 27951 × 1 | player name calls (`ENG_BA_WCP_*_EV` / `_EX`), one row per player |
| `WCP_BN_*`, `EU_WCP_BN_*` | 100 × 1 | shirt numbers (`ENG_BA_NMB_*`) |
| `EU_WCT_TNAME_*`, `EU_WCT_MYTEAM*` | 560 × 1, 839 × 1/23 | team names (`ENG_BA_TWN_*`) |
| `EU_WCOT_NOWTIME` / `_LOSSTIME` | 124 × 8, 16 × 2 | match time (`ENG_BA_TIM_*`) |
| `*SCORE*` | 101 × 1, 22 × 1 | score lines (`ENG_BA_SCR_*`, `ENG_BA_MTH_*`) |
| `EU_WC_TAIKAI`, `WCOT_LEAGUE_EU` | 164 × 3, 101 × 3 | competition names (`ENG_BA_LEG_*`); `WCOT_LEAGUE_EU` is one of the older tables below |
| `OUENKA_*_A/_B` | various | 応援歌 (supporters' chants). A/B are adjacent clip pairs |
| `WCEP_NAME_F/_S` | 22821 × 1 | IDs up to 46484, so they index the 65,501-name Japanese `BCFNAME` |

The prefixes decode as WCPL = player, WCT/WCTM = team and WCOT = other.
MAE/ATO (前/後) = before/after. `_EV`/`_EX` and `_F`/`_S` are paired
variants of the same line, one clip apart.

Of the 53 loose `.TBL` files, 42 equal a table in `SOUNDDAT.PAC` byte for
byte (the pack's 36 tables hold 31 different contents, so some loose files
are equal to each other, such as `EU_WCT_TNAME_F/_FTR/_HDR`). The other 11 are **not** in the pack and look
like older revisions: `OUENKA_AP_TABLE_A/B`, `WCOT_FIXTURES_EU` (72 rows
instead of 99), `WCOT_LEAGUE_EU`, `WCOT_NOWTIME_EU` (124 × 2 instead of
124 × 8), `WCP_EV/EX_EURO` (9,504 rows instead of 27,951) and
`WCT_{EV,EX,E,S}_EURO` (482 rows instead of 560).

### `FNAME*.DAT/.TOC`: clip names

`.TOC` is a u32 array of offsets into `.DAT`, which holds NUL-terminated
names. Entry *i* is the name of entry *i* of the matching AFS:

| Names | Count | Archive |
|---|---|---|
| `FNAMEEN/FR/GE/IT/SP` | 12,899 | `ISO/AUDIO/BC_ENG/FRA/GER/ITA/SPA.AFS` (12,899 entries each) |
| `FNAMEJP` | 12,821 | none on disc |
| `BCFNAME` | 65,501 (`yh_*`, `mt_*`, `kk_*`, plus a few `WCPL_*`, `WCTM_*`, `WCOT_*`) | none on the PAL disc (only the 6-entry `BC_JPN2T.AFS`). It names the 65,501 entries of the Japanese release's `BC_JPN.AFS` ([`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)); the file is byte for byte the same there (**empirical**, `cmp`) |

An index means the same line in every European language, e.g. 10409 is
`ENG_BA_SHT_0001`, `FRA_BA_SHT_0001` and `GER_BA_SHT_0001`.

## `ps2_DTPK`: sound bank

Used by the 40 banks in `SOUNDDAT.PAC`, by `EFFECTS.DAT` / `TRAINING.DAT`
here, and by every file of `DAT/SOUND`. Offsets are relative to the bank
start:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | char[8] | `ps2_DTPK` |
| `0x08` | u8 | version (2) |
| `0x09` | char | kind, meaning unknown: `L` (3 banks of `SOUNDDAT.PAC`), `J` (the pack's other 37 banks and 25 files of `DAT/SOUND`), `H` (the two files here) or `K` (`DAT/SOUND`'s `EFFECTS`, `TRAINING` and `PACK0`) |
| `0x0A` | u8 | 1 for `J` banks, 5 in `SOUND/PACK0.DAT`, else 0 (meaning unknown) |
| `0x0C` | u32 | bank size (multiple of 0x800) |
| `0x10` | u32 | `ps2_TBLD` size |
| `0x18` | u32 | `ps2_VAGD` payload size |
| `0x1C` | u32 | offset of `ps2_VAGD` (0x800, 0x1000 or 0x1800) |
| `0x60` | – | `ps2_TBLD` (tone tables) |
| `0x98` | u32[10] | TBLD pointers: [0] setups, [1] programs, [2] level curves ([Instruments](#instruments-tone-tables)), [3] the song area ([Songs](#songs-sequences)), **[8] the sample table**, [9] its end. 4–7 aren't decoded |

Sample table at `ptr[8]`: `u32 last_index`, then `last_index + 1` entries:

```text
+0x00 u32 offset   relative to the ps2_VAGD header (the first sample is at +0x10)
+0x04 u32 0
+0x08 u16 flags    bit 2 (0x4) = looped (matches the VAG loop-start/loop-end frame flags)
+0x0A u16 rate     Hz: 8000, 11025, 16000, 22050, 28000
+0x0C u32 size     bytes of PS-ADPCM, 16-byte frames
```

Samples are contiguous, and the last one ends within the VAGD payload in
all 42 banks.

### The `SOUND/MAP` banks

Which bank the game loads and which music id plays which song are in
[`SOUND_DIR.md`](SOUND_DIR.md). `DAT/SOUND/MAP01`–`MAP23` fall into two
groups (**empirical**, every file):

| Banks | Samples | TBLD size | What |
|---|---|---|---|
| `MAP01`–`MAP10` | 27–166, 7–41 of them looped, 8–48 kHz | 22–97 KB | sequenced music: 41 songs (below) played with the bank's instruments |
| `MAP11`–`MAP23` | exactly 2, same length, 32 kHz, not looped | 896 bytes | the left and right channels of one stereo piece, 11–26 s. The channels differ (0–6% of samples coincide). In game: the jingles before a full match and the quick-match music (identified by ear) |

`BGM.AFS` in `ISO/AUDIO` holds only `bgm13`–`bgm21` and the ending; the
game's music table names these banks' songs for the other music ids
([`SOUND_DIR.md`](SOUND_DIR.md#the-music-table-sles-0x5190d8)).

### Songs (sequences)

The music in `MAP01`–`MAP10` is sequenced: Sega SoundFactory songs, played
by the IOP driver `ISO/DRIVERS/SNDFI.IRX` ("SNDF Driver Ver 2.27a", the PS2
port of Sega's Dreamcast sound driver). Composers wrote MIDI files;
SoundFactory packed them into this form. No public description of it
existed. **Confirmed** from the driver (addresses in its `.text`, loaded at
0; it has no symbols):

| Address | What it shows |
|---|---|
| `0xfdec`–`0x10244` | the stream reader: status bytes, data bytes, delays, the end byte |
| `0xfe9c`–`0xfff0` | the song records: stream, command, goto |
| `0xa838`, `0xf5bc`, `0xe11c` | each driver run subtracts the song's increment (default `0x500`, 5 ticks in 8.8 fixed point) from its countdown; a command sets another |
| `0xba80`–`0xbaf0` | the driver runs on an IOP hard timer: sysclock ÷ 256 ÷ 720 (the compare value at `0x12af0`) = 200 times a second |

So by default **1 tick = 1 ms**. (Checked by ear: the MIDI files play at
the right speed.)

**Song area.** TBLD pointer [3] (0 = none): u32 sub-area count − 1, then
per sub-area a u32 {u16 offset, u8 id, u8 kind}. Kind `0xa8` is songs,
`0xa9` sound effects (the entries of `EFFECTS`, `SYS_SE` and the like are
short layer lists such as `c0 df 00 50 80 df 01 50 80 ff`, not decoded). A
sub-area is u32 entry count − 1, then u32 offsets from the area start.

**Song.** A u32 header (`0x00010040` in every song), then records
{u24 arg, u8 type}:

| Type | Does |
|---|---|
| `0x00` | play the note stream at song + arg, then read on |
| `0x80` | send driver command `(arg << 8) \| 0x80` (every song sends `a00012` and `a019nn`, *nn* its number in the bank) |
| `0x90` | continue at the record at song + arg: the loop |
| other | play the stream at song + arg and stop there (arg 0: stop now) |

Songs with two streams play an intro once and loop the second (`MAP02`
songs 1 and 2, `MAP06` songs 1, 3 and 4).

**Note stream.** MIDI with running status and one change. A byte with the
top bit set is a status (kept for later events); it is followed by one
data byte for `0x8n` (note-off: key only), `0xCn`, `0xDn`, `0xEn` (bend:
the 7-bit MSB), or two for `0x9n`, `0xAn`, `0xBn`, `0xFn`. The **top bit
of the last data byte** means "another event at the same moment";
otherwise a delay follows, 1–3 bytes of 7 bits, top bit = another byte
(standard MIDI delta coding, at most 3 bytes). `0xFF` ends the stream.

Across the 41 songs: 116,442 note-ons, 21,458 note-offs, 6,280
controllers, 49 pitch bends, 3 `0xAn` events, and no program changes (a
channel's instrument comes from the setup the song selects, below).
Every stream ends exactly at its `0xFF`.

| Banks | Songs | Length at 1 ms/tick |
|---|---|---|
| `MAP01` | 2 | 72, 60 s |
| `MAP02` | 6 | 30–89 s |
| `MAP03`, `MAP04`, `MAP05` | 5 each (they share four) | 60–127 s |
| `MAP06` | 6 | 10–57 s |
| `MAP07`–`MAP10` | 3 each (`07`/`08` and `09`/`10` share two) | 30–94 s |
| `MAP11`–`MAP23` | 1 each: one long note that plays the stereo sample pair | – |
| `PACK0` | 1 | – |

`SOUNDDAT.PAC` holds six more songs of 24–36 s, one each in its banks 3,
4, 8, 9, 13 and 14 (**empirical**, `python SRC/sounddat.py songs
DAT/GAME/SOUNDDAT.PAC`). `python SRC/sounddat.py midi DAT/SOUND/MAP01.DAT
out/` writes each song as a MIDI file (General MIDI instruments, loop
points as `loopStart`/`loopEnd` markers).

### Instruments (tone tables)

How a note becomes a sound, **confirmed** from `SNDFI.IRX`:

| Address | What it shows |
|---|---|
| `0x8068`–`0x8110` | a setup record fills a channel's state: bank, program, volume, pan, mix bits, tune |
| `0x81f0`–`0x8338` | program lookup: bank table, then program table |
| `0x3878`–`0x3a54` | note on: every split whose velocity range fits; the layer by key (melodic) or by key table (drum kit) |
| `0x3e40`–`0x4110` | voice start: left/right volume, ADSR1 = layer `+0xe`, ADSR2 = layer `+0x10` |
| `0x4cec` | the voice level (below) |
| `0x50e4`, `0x9edc`–`0xa034` | mix bits: layer `+8` or, with its bit 7 set, the channel's; bits 0–3 switch VMIXL, VMIXR, VMIXEL, VMIXER (dry left/right, reverb left/right) |
| `0x9a08` | controller 7 overwrites the channel volume the setup set |

Offsets are from the bank start. **ptr[0] setups:** u16 count − 1, u16
offsets. A setup is an 8-byte header (byte 0: last record index) and one
16-byte record per MIDI channel:

| Offset | What |
|---|---|
| `+1` | channel |
| `+2`, `+3` | bank, program |
| `+6` | volume |
| `+8` | pan |
| `+9` | mix bits (0/1 dry left/right, 2/3 reverb left/right), bits 4–5 the SPU2 core |
| `+0xa` | s16 tune, cents |

A song's command `a019nn` selects setup *nn* + 1 for the streams after it
(`MAP02` songs 1 and 2 change setup between intro and loop). Setup 0 is a
default.

**ptr[1] programs:** u16 bank count − 1, u16 bank offsets; a bank is u16
program count − 1 and u16 program offsets, both from the start of the
table they are in. A program has a type at `+0` (0 melodic, 1 drum kit)
and up to four u16 split offsets at `+8` (0 = none). Every split whose
velocity range fits the note sounds, so a stereo sound is two splits
panned apart (`MAP11`–`MAP23`).

A **split** has the layer count − 1 at `+0`, the velocity range at `+2`/
`+3` and the velocity curve at `+6`. A melodic split's 32-byte layers
start at `+0x20`; the first whose top key is at least the note plays. A
drum kit's split has its key range at `+0x20`/`+0x21` and one u16 layer
offset per key from `+0x22` (0 = no drum).

A **layer** (32 bytes):

| Offset | What |
|---|---|
| `+0` | top key (melodic) |
| `+1` | bit 7: fixed pitch (drum layers) |
| `+2` | sample number |
| `+7` | pan; above `0x7f` the channel's |
| `+8` | mix bits; with bit 7 set the channel's |
| `+9` | volume |
| `+0xa` | s16 tune, cents |
| `+0xe`, `+0x10` | the SPU2 ADSR1 and ADSR2 words |

The tune folds in the sample's rate and root key: a note plays at
`(key − 60) × 100 + tune` cents relative to 48 kHz (`MAP11`'s −702 is
exactly 32 kHz). **empirical**, from the zone layouts (tunes 500 cents
apart for zones 5 keys apart) and from rendering `MAP11`, which gives back
the stereo recording.

**ptr[2] curves:** u32 count − 1, then 128-byte level curves.

**Level** (`0x4cec`): `curve[velocity]` (the split's curve) × layer
volume ÷ 256 × channel volume ÷ 128 × song volume ÷ 128 × master ÷ 128;
then × a pan factor for each side. Controller 7 replaces the setup's
volume rather than scaling it.

The noise on `MAP01` channels 9 and 10 has mix bits `0xc`: reverb only.
Played dry it sounds like foreground hiss; through the reverb it is the
quiet wash heard in the game.

`python SRC/sounddat.py tones <bank>` lists setups and programs, and
`wav <bank> <dir> [song]` renders songs with them. The renderer follows
everything above and approximates the rest of the SPU2: linear
interpolation (the SPU2 filters), a 150 ms release instead of the ADSR
envelopes, equal-power panning instead of the driver's pan table at
`0x12048`, and a generic reverb for the reverb bus (the game's preset
isn't decoded). Checked by ear against the game for nine songs.

### Banks in `SOUNDDAT.PAC`

- Banks 0, 5 and 10 are identical `L` banks (34 samples).
- Each is followed by 4 small `J` banks (2–6 samples, mostly looped).
- Banks 15–38 repeat a pattern of three looped banks (13 samples each,
  except bank 29 with 14 and bank 37 with 12), then one 32-sample bank
  (none looped).
- Bank 39 has 23 samples, none looped.

What each bank is for (crowd loops per stadium or atmosphere?) is still
unknown.

## Checking the claims

```bash
python SRC/sounddat.py info    DAT/GAME/SOUNDDAT.PAC             # layout summary
python SRC/sounddat.py extract DAT/GAME/SOUNDDAT.PAC out/ --wav  # 136 pieces + 590 WAVs
python SRC/sounddat.py dtpk    DAT/GAME/EFFECTS.DAT out/         # list/decode one bank file
python SRC/sounddat.py tbl     DAT/GAME/EU_WCOT_LOSSTIME.TBL DAT/GAME/FNAMEEN
python SRC/sounddat.py fname   DAT/GAME/FNAMEEN 10409
python SRC/sounddat.py songs   DAT/SOUND DAT/GAME/SOUNDDAT.PAC   # songs of every bank
python SRC/snr2.py dis ISO/DLL/GAMEPRG.REL 9c88 8 --sles ISO/SLES_541.51   # size(i)
python SRC/tbb.py info DAT/GAME                                  # TBB, BCR and BCB tables
python SRC/packdata.py info DAT/GAME/CUTINPACK_HEADER.BIN --all  # the 277 cut-in entries
python SRC/bpb.py info DAT/GAME
python SRC/gamedata.py info DAT/GAME
python SRC/ninja.py info DAT/GAME
```

`extract` writes `slotNN_<lang>_<crowd>/`, `tbl/` and `dtpk/`. All 96
slot and TBL pieces match a loose file in `DAT/GAME` byte for byte.

## Still unknown

- Names for the loader functions listed above. `snr2.py` labels their
  imports ([`SNR2_FORMAT.md`](SNR2_FORMAT.md)), but local functions carry
  no names of their own.
- The meaning of the bank selectors `t`/`v`, the second byte of each
  selector pair, and what loads bank 39.
- The BCR2 record layout, the `RBD0` trailer of the `ROUTEBOX` tables
  (0x350 bytes, purpose unknown), the BCB3 item fields and script
  opcodes, and the BCV records.
- What the cut-in pack's `CIB0` and `BMT1` blocks hold.
- The entries of `SHADOWCOLLI.PAC` and `WALLCOLLI.PAC` (both loaded into
  `CStadiumCollision`, [`STADIUM_DIR.md`](STADIUM_DIR.md)), which
  `TEST3D/SHADOWCOLLI.LBI` resembles ([`TEST3D_DIR.md`](TEST3D_DIR.md)).
- `TEAM.TMB`'s layout, and confirming that nothing reads it.
- What `BACK_MATCH.TBB` holds and what loads it (no code names it), and
  the row layout of `TACTICS_PLAYBOOK_EDIT.TBB`.
- Whether the game loads `GAME/EFFECTS.DAT` and `GAME/TRAINING.DAT` or only
  the `SOUND/` files of the same names (the two sets differ).
- The DTPK kinds `L`/`J`/`H`/`K`, TBLD pointers 4–7, the driver command
  `a00012`, the sound-effect entries, the SPU2 reverb preset the game
  sets, the pan table's exact law, and what each bank is for.
- `AI_PARAM.BIN`'s reader and the rest of `GAMEDATA.BIN`'s record fields
  ([`GAMEDATA_FORMAT.md`](GAMEDATA_FORMAT.md#still-unknown)); the play
  books' own open items ([`BPB_FORMAT.md`](BPB_FORMAT.md#still-unknown)).
