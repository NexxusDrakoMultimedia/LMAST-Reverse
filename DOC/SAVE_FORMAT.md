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
| 0 | `0x0` | s64 | `pwkGen_GetSikin` (`0x2444e0`) | club money, in the game's own unit (below) |
| 0 | `0x88` | PlDate | `pwkGen_GetDate` (`0x244368`) | the current date |
| 0 | `0x1344` | | `pwkGen_GetDifficultyPointer` (`0x244c78`) | difficulty settings (not decoded) |
| 1 | `0x4b4` | PlTeamData | `pwkTeam_GetMyTeamData` (`0x259898`) | your club |
| 1 | `0x4b4 + 0x20` | 25 × PlPinfo | `pwkTeam_GetForeignCitizenNumber` (`0x266450`) | the squad, 0x2a0 bytes per player |
| 1 | `0xec8e` | 25 × 0x11e | `pwkTeam_GetPlayerStats` (`0x265810`, indexes `0xec90 + slot × 0x11e`) | each squad slot's match statistics (below) |
| 1 | `0x4f00` | 24 × PlPinfo | `pwkTeam_GetYteamData` (`0x270c18`); `pwkTeamType_FitCalc` (`0x270b58`) walks them up to `+0x3f00` | the youth team (21 players in the save checked, 3-year contracts, no salary) |
| 1 | `0xe290` | 3 × 0x2a0 | `0x266600` | read like PlPinfo by one foreign-player count, but the save holds ids of 0 and no players there; not identified |
| 1 | `0x4d08` | PlMinfo | `pwkTeam_GetCoachManager` (`0x26cdc8`): PlTeamData `+0x4854` | the manager |
| 1 | `0x8e00` | PlMinfo | `pwkTeam_GetYManager` (`0x26bdd8`): `pwkTeam_GetYteamData` (`+0x4f00`) `+0x3f00` | the youth manager |
| 1 | `0x9148` | 4 × PlMinfo | `pwkTeam_GetCoaches` (`0x26a7b8`) | the coaches, 0xbc bytes each |
| 1 | `0x8f8c` | 3 × PlSinfo | `pwkTeam_GetScouts` (`0x26d098`) | the scouts, 0x94 bytes each |

**Money** is stored in the game's own unit. `plMisc_MoneyRate`
(`0x215660`) converts between currencies as `value × rate[to] ÷
rate[from]`, with s16 rates at SLES `0x5314e8`: 12, 3, 2, 400. The stored
unit is rate 12 and the pound is rate 2 (**empirical**: a save edited to
2,000,000,000 shows £333,333,333, exactly ÷ 6). The euro is rate 3
(**empirical**: in game, euro amounts are 1.5 times the pound amounts), so
euros are the stored value ÷ 4 and the stored unit is worth €0.25. That
400 is the yen is still a guess from 2005 exchange rates (€1 ≈ ¥133,
£1 ≈ ¥200). The stored unit isn't the yen.

**PlDate** (`plMisc_SetTurn2Date` `0x214698`, `plMisc_PlDate2TotalTurn`
`0x214d08`):

| Offset | Type | What |
|---|---|---|
| `0x0` | u16 | the season's first year: 2019 for 2019–20, from January to June as well (confirmed: `plMisc_PlDate2TotalTurn` only counts upwards that way; `plMisc_SetTurn2Date` stores the year it is given with a turn of the season) |
| `0x2` | u8 | turn of the season, 0–95 (8 per month, from July) |
| `0x3` | u8 | month, 1–12 |
| `0x4` | u32 | turn within the month, 0–7 |
| `0x8`, `0xc` | u32 | that turn ÷ 2 and its remainder: the week (from 0) and midweek (0) or weekend (1). Turn 3 of November is the top bar's "Week 2 Weekend Nov." (**empirical**, one save) |

**PlPinfo** (a player in your squad):

| Offset | Type | What | Source |
|---|---|---|---|
| `0x0` | s16 | database id; negative = empty slot | confirmed, `0x2664d0` |
| `0x4` | u32 | position (grid cell, as `pbdata.py`'s `POSITION_NAMES`) | empirical: GKs are 0, and a GK's bars depend on it (`PBDATA_FORMAT.md`) |
| `0x8` | u8 | current age | confirmed: `plPinfo_ChangeKan` (`0x21c840`) passes it to `plPinfo_kanLowLimit`; matches the screen |
| `0xa` | 64 × {u16 exp, u16 limit, u16 cap} | abilities (below) | confirmed, `plPinfo_ConvAbilLv` (`0x216c90`), `pwkGUtl_AddExp` (`0x246028`) |
| `0x190` | u32 | team | confirmed, `plPinfo_Team` (`0x218358`) |
| `0x198` | 0x74 bytes | a copy of the player's database record header (`PlPbase`, the offsets in [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)): name, nation, database age, height, weight, shirt, leg, skills | confirmed: `plPinfo_IsForeigner` reads `+0x1ac` (`PlPbase +0x14`), `plPinfo_SetUnumber` `+0x1c3` (`+0x2b`), `plPinfo_IsEU` `+0x1fb` (`+0x63`), `plPinfo_IsSkill` `+0x1fc` (`+0x64`). Height, weight, leg and shirt match the screen |
| `0x218` | u32 | annual salary ÷ 100, in the stored money unit | empirical: Carson 75,600 → £1,260,000, Aiblinger 72,000 → £1,200,000 (× 100 ÷ 6) |
| `0x21d` | u8 | contract years remaining | empirical: 1 and 3, as on screen. Read by the `pwkMoney_*` transfer prices |
| `0x23c` | u16 | fatigue, 0–1000 | confirmed: `plPinfo_ChangeGtired` clamps to 1000; `plPinfo_GetGTiredLevel` (`0x21b090`) gives level 0 up to 400, 1 up to 700, else 2 |
| `0x240` | u16 | condition, 0–65535 | confirmed, `plPinfo_Cond5` (`0x217800`); the bar matches (Aiblinger 88%, "fully fit") |
| `0x242` | u16 | motivation, 0–65535 | confirmed, `plPinfo_Moti2Lv` (`0x217b88`): ÷ `0x3333` gives 5 levels |
| `0x24c` | u16 | "power", 0–1000 | confirmed range, `plPinfo_ChangePower` (`0x21c8c0`). Not the T-FIT bar |
| `0x24e` | u16 | form (the game's "kan"), an age-dependent minimum to 1000 | confirmed: `plPinfo_ChangeKan` clamps it; below 400 the condition line says the player has lost form (`ConvertPlayer_Condition`, below) |
| `0x250`, `0x254` | u16, u32 | injury days left, injury kind | `_plPinfo_SetKega`, `plPinfo_KegaRecoverDaysChno`, `plPinfo_IsHkegaFunou` |
| `0x25a`, `0x25c` | u16 | captain and keyman experience | `plPinfo_ChangeCaptainExp`, `plPinfo_ChangeKeymanExp` |
| `0x278` | u32 | current play style (below) | `plPinfo_GetPStyle` / `SetPStyle` |
| `0x27c` | 5 × u32 | the style path: styles in the order the player learns them | confirmed, `ConvertPlayer_PlayStyle` (`0x285238`) |
| `0x290` | u8 | how many of the path are learned | confirmed, the same function draws the current style and this many from the path (skipping repeats and 0) as the style icons |
| `0x292` | u16 | progress towards the next style | `pwkPlayStyle_GetExp` |
| `0x294` | u8 | policy type, copied from `PlPbase +0x52` | confirmed, `pwkTeamType_PolicyInit` (`0x270328`) |
| `0x29a` | u8 | team fit, 0–100: the T-FIT bar | confirmed: `ConvertPlayer_Bar` (`0x285380`) draws it as value ÷ 100; `pwkTeamType_FitCalc` (`0x270b58`) sets it from `pwkTeamType_GetFit(manager, player)`. Carson 100, Aiblinger 60, Ben Arfa 27 match the screens |
| `0x296` | u16 | policy point, Possession (0) to Counter (65535) | confirmed, `l_calculate_policy_rect_player` (`0x300ba8`): the P marker's height is `(v + 1) / 65536` of the grid |
| `0x298` | u16 | policy point, Individual (0) to Organisation (65535) | confirmed, the same function, across |

The policy point is the P marker on a player's second page and his
number on the team vision screen. `PolicyInit` takes its start from a
table of u16 pairs per policy type at SLES `0x555340`
(`pwkTeamType_GetPolicyBseExp`); `PolicyInitNotBlong` adds a random
−5,000 to +5,000 to each axis for players outside your club. Checked on
screen: Carson (`0xffff`, `0x7fff`) is top centre; Aiblinger comes out
0.57 up and 0.37 across, where his marker is on both screens.

The rest of the record between `0x18a` and `0x2a0` is read by the functions
listed by a scan of every `PlPinfo` accessor (flags at `0x20c`, the job
change at `0x210`, dissatisfaction bytes in the database copy), not decoded
yet.

**The condition line** under the bars is chosen by
`WP::CDetailManager::ConvertPlayer_Condition` (`0x285728`), first match
wins: an injury (with the days left); flag `0x800000` at `+0x20c`
(message 11); a slump (12); fatigue ≥ 700 (17), ≥ 400 (16), ≥ 200 (15);
form < 400 (18); condition > 55,000 (14), > 40,000 (13); otherwise 19.
Checked in game: Ben Arfa with fatigue 900 shows "Seriously fatigued and
off form", Carson with form 370 "Lost form and not playing as well as he'd
like", Aiblinger with condition 58,276 "Fully fit and on top form".

The four condition bars are drawn by the end of `ConvertPlayer_Bar`:
fatigue ÷ 1000, condition ÷ 65535, motivation ÷ 65535 and team fit ÷ 100.
Team fit is recomputed from the policy points, so an edit to it wouldn't
last: move the player's policy point (or change the manager) instead.

Edits to fatigue, condition and motivation show in game as set (Ben Arfa:
900, 0 and 65,535), and abilities set to 99 with the growth limit raised
stay at 99 after training (Carson, two turns later).

Ability values are experience. `plMisc_AbilExp2Lv` (`0x2153c0`) turns
experience into a level 0–99 through 101 thresholds at SLES `0x531c70`: the
level is one below the first threshold that reaches the value, so a value
exactly on a threshold reads one level low. `plMisc_AbilLv2Exp(lv, pct)`
(`0x215438`) goes the other way, `t[lv] + (t[lv+1] − t[lv]) × pct / 100`.
The second value is the growth limit: `pwkGUtl_AddExp` (`0x246028`)
adds experience as `exp = min(exp + gain, limit)`. The third value is
always exactly a threshold, and exp ≤ limit ≤ cap holds for all 7,424
abilities of the 116 squad players in the 5 saves (**empirical**): the cap
is the player's ceiling. Young players have limits well above their
current value, veterans' limits sit on it. `save.py set` raises the limit
and cap along with the value, or the next training would clamp the edit
back to the old limit.

**Play styles.** Style names are message 150 + style of category 100001
(**empirical**): 0 none, 1 Centre Forward, 2 Moving, 3 Postplayer, 4 Dash
out, 5 Second Striker, 6 Wing, 7 Play maker, 8 Shadow striker, 9
Attacker, 10 Dynamo, 11 Man marker, 12 Covering, 13 Centre MF, 14 Winger,
15 Threaten to cut in, 16 Full back, 17 Sweeper, 18 Defensive Sweeper, 19
Stopper, 20 CB, 21 GK, 22 Attacking GK. Checked in game: the icon rows of
Carson (GK, Attacking GK), Aiblinger (Sweeper, Defensive Sweeper, Stopper)
and Ben Arfa (Attacker), and the tactics screen's Playing Style menus of
Senderos, Schram and Poulter, which list exactly their learned styles in
style order. The player's skills are the bits at `+0x1fc` (the PlPbase
copy's `+0x64`, see [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#skills)).

**Staff.** A PlMinfo (managers and coaches, 0xbc bytes) or PlSinfo
(scouts, 0x94 bytes) is 4 bytes and then a copy of the staff member's
database record (`PlMbase` / `PlSbase`, the offsets in
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md) plus 4): the name at `+4`, the
abilities at `+0x6a` (48) or `+0x31` (45).

| PlMinfo | PlSinfo | Type | What | Source |
|---|---|---|---|---|
| `0x9c` | `0x60` | s16 | database id; −1 = empty | confirmed, `plMinfo_CloseContract` (`0x216ef0`) / `plSinfo_CloseContract` (`0x218a10`) set it to −1 |
| `0x9e` | `0x62` | u8 | contract years remaining | empirical: the only byte matching all three screens checked (1, 2, 3) |
| `0xa0` | | u32 | job: 0–2 coaches, 3 physical coach, 4 GK coach, 5 manager, 6 youth manager | `pbdata.py`'s `CalcManagerAbil` notes; 5 and 6 empirical |
| `0xb8` | `0x90` | u32 | annual salary ÷ 100, stored money unit | empirical: £2,510,000, £950,000 and £1,060,000 match |

`plMinfo_GetConyear` (`0x218dd8`) is something else: the longest contract
offered, from the age at `+0x26`. `save.py staff` lists everyone with
their bars (`pbdata.py`'s staff formulas).

**Match statistics.** For squad slot `s`, the stats start at block 1
`+0xec8e + s × 0x11e`: four tables of five rows (pre-season, domestic
league, overseas league, Euro, international), then 6 bytes not traced.
A row is 14 bytes:

| Offset | Type | What |
|---|---|---|
| `0x0` | u16 | goals |
| `0x2` | u16 | assists |
| `0x4` | u16 | games played |
| `0x6` | u16 | the club's games while the player was there |
| `0x8` | u16 | man of the match |
| `0xa` | u16 | average points × 100 |
| `0xc` | u8 | red cards |
| `0xd` | u8 | yellow cards |

Table 2 is the Season Stats page and table 4 Career Stats (**empirical**:
every value on both pages matches for Carson and Aiblinger). Table 3 looks
like last season (38 league games for a regular). Table 1 is empty in
every slot checked. The Total lines are computed by the screen.

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
byte-identical files.

Interpreting takes about 8 seconds a save, so `save.py` does it once. The
generated code stores each value into the block right after reading it,
so one run of the read functions gives a flat field list: for each
`_plBits_BitRead` call its bit count and signedness, and the offset and
width of the first store into the blocks that follows (each string byte is
a field of its own). Replaying the list reads or writes a save in about a
second. The list is cached in `.cache/` (git-ignored), keyed by
`SAVEPRG.REL` and the block sizes.

| | Count |
|---|---|
| fields | 604,078 |
| bits | 5,169,290 (the stream length of every save) |
| signed fields | 114,509 |
| bytes of the blocks written | 947,298 of 1,035,469 |
| widths | 1–10, 14, 16, 18, 32 and 64 bits; 8 bits is the most common (143,512) |

`python SRC/save.py fields` records the list afresh and checks it: over
random streams, the replay must give the same blocks as the interpreter,
and over random blocks the same stream. That covers data the real saves
don't, so it also shows the layout doesn't depend on the contents (no
counts or flags that change which fields follow).

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
works.

That only separates the saves. PCSX2 (and disc loaders) take a disc's
serial from the boot file named in `SYSTEM.CNF`
(`BOOT2 = cdrom0:\SLES_541.51;1`), so a disc that still boots
`SLES_541.51` still shows up as SLES-54151 (**empirical**: tested in
PCSX2). `save.py serial` therefore also writes the executable as
`PYRA_313.96` with a `SYSTEM.CNF` that boots it, and prints the
`patch_disc.py` command that patches both and renames the file on the
disc (`--rename`, see [`REBUILD.md`](REBUILD.md#usage)). The names are the
same length, so nothing moves. Nothing in the executable refers to its own
file name. Changing the executable changes its CRC, so PCSX2 patches and
cheats keyed to the original CRC won't apply to the modded disc.

Tested in PCSX2: the renamed disc boots as PYRA-31396. PCSX2 doesn't show
it in its game list without a GameDB entry for that serial, which this
project doesn't provide. The serial change is an optional feature for
mods that want their own saves; the default is to keep SLES-54151.

The game opens `<folder>/<folder>`, so a save moved to the new serial
needs both names changed. `save.py rename` copies a save folder with both
renamed, and fixes the name in PCSX2's `_pcsx2_meta_directory` (`+0x40`)
and `_pcsx2_index` for folder memory cards.

## Still unknown

- The T-FIT bar, table 1 of the statistics, and the rest of PlPinfo
  (flags, dissatisfaction, style icons). The rest of the blocks: the
  accessors that call `get(i)` are the way in.
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
