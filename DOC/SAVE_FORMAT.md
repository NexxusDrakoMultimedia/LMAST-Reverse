# Save data (memory card)

A saved game is a memory-card folder `BESLES-54151-Gnnn` (`nnn` = slot,
`%03d`). It holds:

| File | Size | What |
|---|---|---|
| `BESLES-54151-Gnnn` | 646,184 | the game: all of `Param::PlPworkTask`, bit-packed and Blowfish encrypted (below) |
| `info.bin` | 2,048 | the summary for the load screen. The first 0x400 bytes are Blowfish encrypted with the key `FC_EURO_2005` and start with the save date as text (`26/09/21 09:39:47`). Not decoded further |
| `dm.bin` | 93,184 | plain. Not decoded |
| `icon.sys`, `static.ico` | 964, 70,264 | the standard PS2 browser icon |

`python SRC/save.py` reads and writes the main file. It doesn't copy the
field layout out of the game: it runs the game's own read and write
functions from `SAVEPRG.REL` in a small interpreter (see
[Decoding](#decoding)).

## Main file

**Confirmed from the game code (`SAVEPRG.REL` unless noted):**

| Address | Symbol / role | What it shows |
|---|---|---|
| `0x320c0`, `0x32158` | Blowfish init, key schedule | standard Blowfish: P-array at `0x4bd78`, S-boxes at `0x4bdc0`. Key bytes go into P big-endian, cycling over the key |
| `0x32358`, `0x32478` | decrypt, encrypt `(buf, size, key, keylen)` | ECB over 8-byte blocks. Each block is loaded as two native (little-endian) words, left then right. `size` must be a multiple of 8 |
| `0x331f8`, `0x336f4` | load, save | key: the 10 bytes at `0x536a8`, `sakatsukue` |
| `0x33200`–`0x3322c` | load | copies the 16-byte header; version `+0xc` must be `0x69` (`0x68` goes to an older reader at `0xe618`) |
| `0x3328c`–`0x3329c` | load | header `+8` must equal the layout CRC from `0x32ce0` |
| `0x32ce0` | layout CRC | CRC-16 (`0x31470`, table `0x53408`: reflected poly `0x8408`, init and xorout `0xFFFF`) over `getSize(0..9)` as ten u32 |
| `0x21d908` (SLES) | `PlPworkTask::getSize` | block `i` is `0x533ac8[i] − 8` bytes |
| `0x33338`–`0x33360` | load | memory-card saves take the bit-packed path: `plBits_Create` over the data at `+0x10 + header[0]`, then `0x32d50` |
| `0x32d50` | per-block loop | for `i` in 0–9: `get(i)`, then read `0x2b9b0` / write `0x2ba08`, which jump through tables at `0x4bd28` / `0x4bd50` |

Plaintext layout:

| Offset | Size | What |
|---|---|---|
| `0x0` | u32 | data offset (0 in every save) |
| `0x4` | u32 | 0 |
| `0x8` | u32 | layout CRC, `0xa225` for this build |
| `0xc` | u32 | version, `0x69` |
| `0x10` | | the bit stream: blocks 0–9 in order, MSB first (`PlBitsClass`, as in [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)) |

The layout CRC checks that a save matches the build's block sizes. **Nothing
checks the contents**, so an edited save only has to be re-encoded and
re-encrypted.

The stream is 5,169,290 bits (646,162 bytes) in all 5 saves checked. The
file is the header plus the stream rounded up to 8 bytes. The game doesn't
clear its buffer, so the 6 bytes after the stream (and the unused low bits
of the last byte) are leftover memory: zero in 2 of the 5 saves, random in
the other 3. `save.py` keeps whatever the original file had there.

### The blocks

`python SRC/save.py blocks` prints the sizes. Decoded, the ten blocks are
1,035,469 bytes, which is 1.6 times the stream: the serializers write each
field with only as many bits as it needs.

| Block | Size | Holds (from the functions that call `get(i)`) |
|---|---|---|
| 0 | 134,728 | general state: money, date, difficulty, events, mail, random seed (`pwkGen_*`) |
| 1 | 76,264 | your club: squad, staff, scouts, negotiations, sponsors, youth (`pwkTeam_*`, `pwkDis_*`) |
| 2 | 73,920 | the other clubs (`pwkOteam_*`) |
| 3 | 1,328 | leagues (`pwkLg_*`) |
| 4 | 168 | town and overseas branches (`pwkTown_*`) |
| 5 | 741,584 | records: results, finances, reports, honours (`pwkRec_*`) |
| 6 | 7,400 | schedule and camps (`pwkSche_*`) |
| 7 | 68 | options (`pwkOpt_*`) |
| 8 | 1 | (`get(8)` returns 0 when PlPwork `+0x19` is set; `0x2b990` then skips it) |
| 9 | 8 | not traced |

### Fields found so far

All **confirmed** by the accessor named. Offsets are within the block.

| Block | Offset | Type | Accessor | What |
|---|---|---|---|---|
| 0 | `0x0` | s64 | `pwkGen_GetSikin` (`0x2444e0`) | club money |
| 0 | `0x88` | PlDate | `pwkGen_GetDate` (`0x244368`) | the current date |
| 0 | `0x1344` | | `pwkGen_GetDifficultyPointer` (`0x244c78`) | difficulty settings (not decoded) |
| 1 | `0x4b4` | PlTeamData | `pwkTeam_GetMyTeamData` (`0x259898`) | your club |
| 1 | `0x4b4 + 0x20` | 25 × PlPinfo | `pwkTeam_GetForeignCitizenNumber` (`0x266450`) | the squad, 0x2a0 bytes per player |
| 1 | `0xe290` | 3 × PlPinfo | `0x266600` | a second, smaller group of players (not identified) |

**PlDate** (`plMisc_SetTurn2Date` `0x214698`, `plMisc_PlDate2TotalTurn`
`0x214d08`):

| Offset | Type | What |
|---|---|---|
| `0x0` | u16 | calendar year |
| `0x2` | u8 | turn of the season, 0–95 (8 per month, from July) |
| `0x3` | u8 | month, 1–12 |
| `0x4` | u32 | turn within the month, 0–7 |
| `0x8`, `0xc` | u32 | that turn ÷ 2 and its remainder |

**PlPinfo** (a player in your squad):

| Offset | Type | What | Source |
|---|---|---|---|
| `0x0` | s16 | database id; negative = empty slot | confirmed, `0x2664d0` |
| `0x4` | u8 | position (grid cell, as `pbdata.py`'s `POSITION_NAMES`) | empirical: GKs are 0, and a GK's bars depend on it (`PBDATA_FORMAT.md`) |
| `0x8` | u8 | age | empirical: matches the players checked |
| `0xa` | 64 × {u16 exp, u16, u16 cap} | abilities | confirmed, `plPinfo_ConvAbilLv` (`0x216c90`) |
| `0x198` | char[19] | short name, e.g. `A.Deasy` | empirical |

Ability values are experience. `plMisc_AbilExp2Lv` (`0x2153c0`) turns
experience into a level 0–99 through 101 thresholds at SLES `0x531c70`: the
level is one below the first threshold that reaches the value, so a value
exactly on a threshold reads one level low. `plMisc_AbilLv2Exp(lv, pct)`
(`0x215438`) goes the other way, `t[lv] + (t[lv+1] − t[lv]) × pct / 100`.
The third value of each triplet is always exactly a threshold, and is
never below the first (**empirical**, all 7,424 abilities of the 116 squad
players in the 5 saves): the player's ceiling for that ability. What the
second value means isn't known yet.

## Decoding

The ten serializers are generated code: 1,575 calls to
`_plBits_BitRead`/`_plBits_BitReadStr` on the read side and 1,574 to the
write versions, with loops for arrays. Those four functions are the only
imports they call. Rather than transcribe that layout, `save.py` runs the
read or write function for each block in an interpreter for the R5900
instructions they use: integer ALU, loads and stores, branches with delay
slots, three-operand `mult`, MMI `madd`, and `lq`/`sq` for register saves.
The four imports are Python functions over the bit stream. `SAVEPRG.REL`
is linked at base 0, so it runs from address 0 without relocation.

The result matches the game exactly: all 5 saves decode and re-encode to
byte-identical files. A decode takes about 8 seconds.

## Separate saves for a modded disc

`MC::CFcEuroIF::initialize` (SLES `0x12ad38`) picks the memory-card name
for each `eCATEGORY` from three strings:

| Category | Address | Name | Use |
|---|---|---|---|
| 0 | `0x5213e8` | `BESLES-54151-G` | saved games, plus `%03d` |
| 1 | `0x5213f8` | `BESLES-54151-C` | VS data, for VS mode and for Virtua Pro Football |
| 2 | `0x521408` | `BESLES-54153FASYS` | Virtua Pro Football's save, read by the import feature |

No other file on the disc contains the serial. `save.py serial` writes a
copy of `SLES_541.51` with categories 0 and 1 moved to another serial of
the same length (`PYRA-31396` → `BEPYRA-31396-G000`, `BEPYRA-31396-C000`).
Moving the VS data is deliberate, as anti-cheat: teams built in a modded
game can't be carried into Virtua Pro Football or an unmodded game's VS
mode. Category 2 stays, so the import from Virtua Pro Football still
works. Changing the
executable changes its CRC, so PCSX2 patches and cheats keyed to the
original CRC won't apply to the modded disc.

The game opens `<folder>/<folder>`, so a save moved to the new serial
needs both names changed. `save.py rename` copies a save folder with both
renamed, and fixes the name in PCSX2's `_pcsx2_meta_directory` (`+0x40`)
and `_pcsx2_index` for folder memory cards.

## Still unknown

- The second value of each ability triplet.
- The rest of PlPinfo (contract, condition, injuries, stats) and of the
  blocks. The accessors that call `get(i)` are the way in.
- `info.bin` past the date, and `dm.bin`.
- Whether the game checks `info.bin` against the main file.
- The VS data (`BESLES-54151-C000`, main file 16,152 bytes). It uses the
  same key and header (layout CRC `0x8ffb`, version 0), and its `info.bin`
  (1,024 bytes) starts with a date under `FC_EURO_2005`. The layout inside
  hasn't been traced (the VS load is at `SAVEPRG.REL 0x33868`).

## Checking

```bash
python SRC/save.py blocks
python SRC/save.py info  <card>/BESLES-54151-G003
python SRC/save.py roundtrip <card>/BESLES-54151-G00*
python SRC/save.py show  <card>/BESLES-54151-G003
python SRC/save.py set   <card>/BESLES-54151-G003 edited.bin money=2000000000 0:all=99
python SRC/snr2.py dis ISO/DLL/SAVEPRG.REL 0x33140 160 --sles ISO/SLES_541.51
python SRC/sles_disasm.py ISO/SLES_541.51 dis initialize__Q22MC9CFcEuroIF pwkGen_GetSikin plMisc_AbilExp2Lv
```
