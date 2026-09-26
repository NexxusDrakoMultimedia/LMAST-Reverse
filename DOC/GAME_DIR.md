# `DAT/GAME`: in-match data, commentary and sound banks

`DAT/GAME` (156 files, 112 MB) holds the data for the match engine. Most of
it is loaded by `DLL/GAMEPRG.REL` (`sounddat.pac`, `playbook.bpb`,
`cutinpack.bin`, `shadowcolli.pac`, ... appear there as strings). The
largest part is the **commentary system**: `SOUNDDAT.PAC` plus about 55 loose
files that are byte-for-byte copies of its pieces.

The `SOUNDDAT.PAC` piece offsets are **confirmed** against the table the
game itself uses in `GAMEPRG.REL`. The formats inside the pieces (TBL, BCR2,
BCB3, DTPK) are **empirical**, checked against every file on the disc.
`python SRC/sounddat.py` implements them.

## Directory overview

| Files | Format | Notes |
|---|---|---|
| `SOUNDDAT.PAC` | concatenation, see below | commentary tables + 40 sound banks |
| `ROUTEBOX_*.BCR`, `VBOX_*.BCB`, `*.BCV`, `*.TBL` | see below | loose copies of `SOUNDDAT.PAC` pieces, plus 11 stale `.TBL`s |
| `FNAME{EN,FR,GE,IT,SP,JP}.DAT/.TOC`, `BCFNAME.DAT/.TOC` | clip-name tables | names for `ISO/AUDIO/BC_<lang>.AFS` entries |
| `EFFECTS.DAT`, `TRAINING.DAT` | `ps2_DTPK` | one sound bank each (kind `H`) |
| `*.SNJ`, `*.SNO` | Ninja `NSIF` + `NSOB` (+`NSTL`, `NFN0`) | models: 7 balls (Teamgeist, Roteiro, Pelias, Total90, Finale, White, default), cursors, shadows |
| `*.SNM` | Ninja `NSIF` + `NSMO` | motion |
| `*.SNP` | Ninja `NSIF` + `NSNT` | node tree |
| `*.SVR` | `GBIX` + `PVRT` | textures. `GM_KEYHELP0-6` / `GM_TITLE0-6` are probably per-language sets; the code names only `gm_keyhelp.svr` / `gm_title.svr` |
| `*.SVM`, `EF001.BIN`, `FLARE.BIN` | `PVMH` | texture archives |
| `BALLMOTION`, `OPTMOTION*`, `PLAYERMOTION`, `SHADOWCOLLI`, `WALLCOLLI` | BINPAC | see `PAC_FORMAT.md` |
| `CUTINPACK.BIN` + `_HEADER.BIN` | KC@P | see `PAC_FORMAT.md`. 168 of 277 entries hold `CIB0` blocks, 109 are empty |
| `PLAYBOOK.BPB`, `COMBINATION.BPB`, `COMBINATION2.CBB/.CSB` | unknown | tactics AI: `fb::PlayBookData`, `fb::Combination` (`fb/thought/*.cpp`) |
| `BACK_MATCH.TBB`, `TACTICS_PLAYBOOK_EDIT.TBB` | TBB | see `TBB_FORMAT.md` |
| `AI_PARAM.BIN` | 467 × f32 | not referenced by name in any executable |
| `GAMEDATA.BIN` | unknown | loaded by `GAMEPRG.REL` |
| `TEAM.TMB` | `TMB1` | team names, 3-letter codes, stadiums (`Highbury`/`LON`). Dated Mar 2005, not referenced by name. Probably stale |
| `CVS/` | CVS metadata | original lowercase names and revision numbers |
| `DUMMY.DAT` (0 bytes), `VBNAME.VBN` (`test0`) | junk | |

## `SOUNDDAT.PAC`

There is no directory in the file. The `TBB1` header at offset 0 belongs to the first
piece (`ROUTEBOX_EU.BCR`), not to the pack. The offsets are hardcoded in
`GAMEPRG.REL` (see [How the game indexes it](#how-the-game-indexes-it)).

| Range | Contents |
|---|---|
| `0x000000`–`0x162000` | 12 commentary slots of `0x1D800` bytes |
| `0x162000`–`0x1A26BB` | 36 `.TBL` clip tables, 16-aligned; groups restart on `0x800` boundaries |
| `0x1A2800`–`0xC6E800` | 40 `ps2_DTPK` sound banks, back to back, ending exactly at EOF |

### How the game indexes it

`DLL/GAMEPRG.REL` is an `SNR2` overlay linked at base 0, so its code
addresses equal file offsets and every absolute address is patched by
relocations at load time (external calls appear as `jal 0`). The offsets live in
a table of 143 records `{u32 offset, u32 size, u32 0, u32 0}` at
**`0x248540`–`0x248E30`**. It ends right before the `"sounddat.pac"` string at
`0x248E30`, which begins the file-request struct that the loader fills.
The records match the layout `SRC/sounddat.py` derives exactly.

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
  - a 13-sample looped bank, from the pairs at `0x265E3E + t*20 + v*2`
  - a 32-sample bank, from the pairs at `0x265E88 + v*2`

The level-0 indices these tables give are:

| `v` | 13-sample bank for `t` = 0 / 1 / 2 | 32-sample bank |
|---|---|---|
| 0 | 17 / 19 / 18 | 20 |
| 1 | 21 / 23 / 22 | 24 |
| 2 | 25 / 27 / 26 | 28 |
| 3 | 29 / 31 / 30 | 32 |
| 4 | 37 / 39 / 38 | 40 |
| 5 | same as 0 | same as 0 |
| 6 | 33 / 35 / 34 | 36 |

So banks 15–38 are six groups of three crowd variants plus one 32-sample
bank, one group per `v`. `v` has seven values with 5 aliasing 0, which
matches the seven country codes elsewhere in the overlays (`du`, `fr`, `ge`,
`it`, `jp`, `sp`, `uk`). **What `t` and `v` mean is a guess.** Level-0
entry 41 (bank 39) isn't selected by these tables. The second byte of each
pair isn't a level-0 index and is still unknown.

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

```
+0x00 'BCR2'  +0x04 u32 0x10  +0x08 u32 size  +0x0C u32 0
+0x10 ...     size bytes of record data (not decoded)
```

`ROUTEBOX_EU` has 106 records and `ROUTEBOX_KAN` has 11. After the
TBB1's end-of-data field there is a **0x350-byte trailer**. It starts with
the magic `RBD0`, then `u32 0x10` and a size (`0x340` in EU, `0x334` in KAN),
and continues with u16 values ending in `ff 00`. It differs between the two files and its purpose is unknown.

#### `.BCB`: vbox table

A TBB1 with one `BCB3` table:

```
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

981 records of 3 bytes each, one per language-vbox record. Not decoded.

### `.TBL`: clip tables

```
u16 BE rows
u8     cols
u16 BE id[rows * cols]      row-major
```

All 52 loose `.TBL` files fit this layout exactly. Each `id` is an index into
`BC_<lang>.AFS` and `FNAME<lang>` (see below). Index 169 (`dummy_0001`) is
used as the "no clip" filler. Examples:

| Table | Rows × cols | Points at |
|---|---|---|
| `EU_WCP_NAME_F/_S` | 27951 × 1 | player name calls (`ENG_BA_WCP_*_EV` / `_EX`), one row per player |
| `WCP_BN_*`, `EU_WCP_BN_*` | 100 × 1 | shirt numbers (`ENG_BA_NMB_*`) |
| `EU_WCT_TNAME_*`, `EU_WCT_MYTEAM*` | 560 × 1, 839 × 1/23 | team names (`ENG_BA_TWN_*`) |
| `EU_WCOT_NOWTIME` / `_LOSSTIME` | 124 × 8, 16 × 2 | match time (`ENG_BA_TIM_*`) |
| `*SCORE*` | 101 × 1, 22 × 1 | score lines (`ENG_BA_SCR_*`, `ENG_BA_MTH_*`) |
| `EU_WC_TAIKAI`, `WCOT_LEAGUE_EU` | 164 × 3, 101 × 3 | competition names (`ENG_BA_LEG_*`) |
| `OUENKA_*_A/_B` | various | 応援歌 (supporters' chants). A/B are adjacent clip pairs |
| `WCEP_NAME_F/_S` | 22821 × 1 | IDs up to 46484, so they index the 65,501-name Japanese `BCFNAME` |

The prefixes decode as WCPL = player, WCT/WCTM = team and WCOT = other.
MAE/ATO (前/後) = before/after. `_EV`/`_EX` and `_F`/`_S` are paired
variants of the same line, one clip apart.

These 11 loose `.TBL`s are **not** in `SOUNDDAT.PAC` and look like older
revisions:
`OUENKA_AP_TABLE_A/B`, `WCOT_FIXTURES_EU`, `WCOT_LEAGUE_EU`,
`WCOT_NOWTIME_EU` (124 × 2 instead of 124 × 8), `WCP_EV/EX_EURO`
(9,504 rows instead of 27,951), `WCT_{EV,EX,E,S}_EURO`.

### `FNAME*.DAT/.TOC`: clip names

`.TOC` is a u32 array of offsets into `.DAT`, which holds NUL-terminated
names. Entry *i* is the name of entry *i* of the matching AFS:

| Names | Count | Archive |
|---|---|---|
| `FNAMEEN/FR/GE/IT/SP` | 12,899 | `ISO/AUDIO/BC_ENG/FRA/GER/ITA/SPA.AFS` (12,899 entries each) |
| `FNAMEJP` | 12,821 | none on disc |
| `BCFNAME` | 65,501 (`yh_*`, `mt_*`, `kk_*`) | none on disc (only the 6-entry `BC_JPN2T.AFS`). Probably a leftover from the Japanese release |

An index means the same line in every European language, e.g. 10409 is
`ENG_BA_SHT_0001`, `FRA_BA_SHT_0001` and `GER_BA_SHT_0001`.

## `ps2_DTPK`: sound bank

Used by the 40 banks in `SOUNDDAT.PAC` and by `EFFECTS.DAT` / `TRAINING.DAT`.
Offsets are relative to the bank start:

| Offset | Type | Meaning |
|---|---|---|
| `0x00` | char[8] | `ps2_DTPK` |
| `0x08` | u8 | version (2) |
| `0x09` | char | kind: `L`, `J` or `H` (meaning unknown) |
| `0x0A` | u8 | 1 for `J` banks, else 0 |
| `0x0C` | u32 | bank size (multiple of 0x800) |
| `0x10` | u32 | `ps2_TBLD` size |
| `0x18` | u32 | `ps2_VAGD` payload size |
| `0x1C` | u32 | offset of `ps2_VAGD` (0x800, 0x1000 or 0x1800) |
| `0x60` | | `ps2_TBLD` (tone tables) |
| `0x98` | u32[10] | TBLD pointers. **[8] = sample table**, [9] = its end. The others aren't decoded |

Sample table at `ptr[8]`: `u32 last_index`, then `last_index + 1` entries:

```
+0x00 u32 offset   relative to the ps2_VAGD header (the first sample is at +0x10)
+0x04 u32 0
+0x08 u16 flags    bit 2 (0x4) = looped (matches the VAG loop-start/loop-end frame flags)
+0x0A u16 rate     Hz: 8000, 11025, 16000, 22050, 28000
+0x0C u32 size     bytes of PS-ADPCM, 16-byte frames
```

Samples are contiguous, and the last one ends within the VAGD payload in
all 42 banks.

### The `SOUND/MAP` banks

`DAT/SOUND/MAP01`–`MAP23` fall into two groups (**empirical**, every
file):

| Banks | Samples | TBLD size | What |
|---|---|---|---|
| `MAP01`–`MAP10` | 27–166, 7–41 of them looped, 8–48 kHz | 22–97 KB | instrument sets with large tone tables: sequenced (MIDI-like) music whose note data is presumably in the TBLD. Not decoded |
| `MAP11`–`MAP23` | exactly 2, same length, 32 kHz, not looped | 896 bytes | the left and right channels of one stereo piece, 11–26 s. The channels differ (0–6% of samples coincide). In game: the jingles before a full match and the quick-match music (identified by ear) |

`BGM.AFS` in `ISO/AUDIO` holds only `bgm13`–`bgm21` and the ending, so
these banks are the likely home of the other music.

### Banks in `SOUNDDAT.PAC`

- Banks 0, 5 and 10 are identical `L` banks (34 samples).
- Each is followed by 4 small `J` banks (2–6 samples, mostly looped).
- Banks 15–38 repeat a pattern of three 13-sample banks (all looped),
  then one 32-sample bank (none looped).
- Bank 39 has 23 samples, none looped.

What each bank is for (crowd loops per stadium or atmosphere?) is still
unknown.

## Tool

```bash
python SRC/sounddat.py info    DAT/GAME/SOUNDDAT.PAC             # layout summary
python SRC/sounddat.py extract DAT/GAME/SOUNDDAT.PAC out/ --wav  # 136 pieces + 590 WAVs
python SRC/sounddat.py dtpk    DAT/GAME/EFFECTS.DAT out/         # list/decode one bank file
python SRC/sounddat.py tbl     DAT/GAME/EU_WCOT_LOSSTIME.TBL DAT/GAME/FNAMEEN
python SRC/sounddat.py fname   DAT/GAME/FNAMEEN 10409
```

`extract` writes `slotNN_<lang>_<crowd>/`, `tbl/` and `dtpk/`. All 96
slot and TBL pieces match a loose file in `DAT/GAME` byte for byte.

## Open questions

- Names for the loader functions listed above. `SNR2` is now parsed
  (`SNR2_FORMAT.md`, `SRC/snr2.py`), so their imports are labelled, but
  local functions carry no names of their own.
- The meaning of the bank selectors `t`/`v`, the second byte of each
  selector pair, and what loads bank 39.
- The BCR2 record layout and trailer, the BCB3 item fields and script
  opcodes, and the BCV records.
- The DTPK kinds `L`/`J`/`H`, the other TBLD pointers, and what each bank
  is for.
