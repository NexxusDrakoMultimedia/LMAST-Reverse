# `DAT/GAME`: in-match data, commentary and sound banks

`DAT/GAME` (156 files, 112 MB) holds the data for the match engine. Most of
it is loaded by `DLL/GAMEPRG.REL` (`sounddat.pac`, `playbook.bpb`,
`cutinpack.bin`, `shadowcolli.pac`, ... appear there as strings). The
largest part is the **commentary system**: `SOUNDDAT.PAC` plus about 55 loose
files that are byte-for-byte copies of its pieces.

Nothing in this document comes from disassembly yet. The SOUNDDAT and
commentary layouts are **empirical**, checked against every file on the disc.
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

There is no directory. The `TBB1` header at offset 0 belongs to the first
piece (`ROUTEBOX_EU.BCR`), not to the pack, so `tbb.py` can't read it. The
game probably has the offsets hardcoded (not yet found in `GAMEPRG.REL`).

| Range | Contents |
|---|---|
| `0x000000`–`0x162000` | 12 commentary slots of `0x1D800` bytes |
| `0x162000`–`0x1A26BB` | 36 `.TBL` clip tables, 16-aligned; groups restart on `0x800` boundaries |
| `0x1A2800`–`0xC6E800` | 40 `ps2_DTPK` sound banks, back to back, ending exactly at EOF |

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
TBB1's end-of-data field there is a **0x350-byte trailer** of u16 values ending in
`ff 00`. It differs between the two files and its purpose is unknown.

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

- Where `GAMEPRG.REL` gets the `SOUNDDAT.PAC` offsets. This needs an `SNR2`
  (SN Systems relocatable) loader first.
- The BCR2 record layout and trailer, the BCB3 item fields and script
  opcodes, and the BCV records.
- The DTPK kinds `L`/`J`/`H`, the other TBLD pointers, and what each bank
  is for.
