<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# The Japanese release

*Pro Soccer Club o Tsukurou! Europe Championship* (プロサッカークラブをつくろう!
ヨーロッパチャンピオンシップ), SLPM-66316, v1.05, the Redump dump
[30266](https://redump.info/disc/30266). It came out on 2006-03-01. The PAL
release is dated 2006-07-16 (`DLL/VERSION.DAT`), so the Japanese one is the
earlier build, and the reference for content PAL changed or cut (see
[`LMASTER_MOD.md`](LMASTER_MOD.md)).

## Setting it up

```bash
python SRC/extract_disc.py all "Pro Soccer Club o Tsukurou! Europe Championship (Japan).iso"
```

This checks the image against Redump and extracts it to `ISO_JP/` and
`DAT_JP/` (git-ignored, like `ISO/` and `DAT/`). `DATA.CVM` decrypts with
the same key scheme as PAL.

The tools take the Japanese folders wherever they take a path:
`python SRC/acrobata.py scenes DAT_JP/ACROBATA ISO_JP`,
`python SRC/mbb.py vars DAT_JP/MESSAGE/MES.PAC ISO_JP`. With both folders
present, `python SRC/regress.py run` also runs every check over them as
`jp_<name>`.

`patch_disc.py` patches a Japanese disc too, with every switch but
LMASTER Realism's ([below](#patching-a-japanese-disc)), and `save.py --iso
ISO_JP` reads
and writes Japanese saves
([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-japanese-release)). Still
PAL-only: the editor and the save editor.

## How the tools find addresses: `gamever.py`

The tools and docs give addresses in the PAL executable and overlays.
`SRC/gamever.py` finds the same address in another build, using the PAL
files in `ISO/` as the reference:

1. **symbol**: the PAL address has a name in the export tables.
2. **reference**: named functions that load the address with a
   `lui`/`addiu` pair (an overlay: a HI16/LO16 relocation) load the same
   address in the same position in the other build. Functions without a
   symbol get names from their callers (`f>2` is the third function `f`
   calls). The functions must agree. If they don't, the candidate whose
   words look most like the PAL table wins, or nothing does.
3. **bytes**: the PAL bytes, with address fields masked in code, occur
   once in the other file (or as often as in PAL: the same occurrence).
4. **function**: a shorter run of the PAL bytes (0x20, 0x10 or 8 bytes)
   occurs once in the other build's function of the same name, for code
   the other build changed a few words further on.
5. **near**: as 2, from an address up to 0x800 bytes away.

`gamever.imm` does the same for constants held in instructions (loop
bounds, table sizes). `python SRC/gamever.py check ISO_JP` lists every
address the tools use and how each was found: all 37 are found.

Each table's use in a tool checks it a second way (**empirical**, run on
the Japanese disc):

| Tool | Tables | Check |
|---|---|---|
| `acrobata.py scenes` | executable index and scene table, SIMPRG.REL scene names | all 869 index entries match the pack header; every scene's name agrees between the executable and `getAckName` |
| `uniform.py info` | licence and descriptor tables | 116 clubs; none of the 232 descriptors differs from `PLPACK_*.HED` |
| `sounddat.py music` | bank and music tables | every bank names its `SOUND/` file, with the right number of songs or effects |
| `mbb.py vars` | global variables, switch tables, converters | each variable resolves to a function, as in PAL |
| `save.py` | key, Blowfish tables, CRC table, block sizes | same key `sakatsukue`, same Blowfish P-array start |
| `humanid.py objects` | the human database's object table | all 112 entries equal PAL's |

## Patching a Japanese disc

`patch_disc.py patch` takes the Japanese image, with every switch but
`realism` ("made for the PAL release": the pack is named by PAL hashes),
so LMASTER full and max can't be built for it; LMASTER lite and the
groups without it can. `third-tier` is ported except for its rules text
([below](#the-third-tier-on-the-japanese-disc)).
Every switch must work here before LMASTER 1.0.0 (Nexxus's choice,
2026-11-01; [`TODO.md`](../TODO.md) section 8).

```bash
python SRC/patch_disc.py patch "Pro Soccer Club o Tsukurou! Europe Championship (Japan).iso" out.iso --mod lmaster-lite,harder-economy,balance,league-balance,injury-lines --skip-tutorial
```

The switches give their bytes as offsets in the PAL executable and
overlays. On a Japanese disc, `patch_disc.py` finds each range a switch
reads with `gamever.py`, and writes the switch's new bytes where the
bytes it checked are. Where `gamever.py` can't place a word, it tries
the word the switch expects, found once in the Japanese function of the
same name, then the shift of a translated address up to 0x40 bytes
away. A call (`jal`) in a switch's code takes the Japanese address of
the function it called in PAL, and a word that is an address in the
executable's code (a jump table's case) takes the Japanese address of
the same code (`gamever.at`, checked for each word). Each switch then
checks the bytes as on PAL, so a place the Japanese build changed is
refused, not patched.

What each switch finds there (**empirical**, from planning every switch
on the Redump image, last on 2026-11-12: every switch but `realism`
plans there, each on its own with the switches it needs):

| Switch | On the Japanese disc |
|---|---|
| `sponsor-negotiation` | nothing to do: the release negotiates with the main sponsor ([`SPONSOR_NEGOTIATION.md`](SPONSOR_NEGOTIATION.md)) |
| `drill-names` | nothing to do: `801_1`–`6.mbb` already have the names in the Japanese numbering |
| `mod-saves` | renames the memory-card folders `BISLPM-66316-G` and `-C`, found by name, to the same letters as PAL (`-F` or `-M`, and `-V`) |
| `skip-tutorial` | as PAL; the undo of the earlier PAL-only skip is left out |
| `injury-lines` | the code fix only: the Japanese text of the two lines (category 200, messages 4 and 7, "about 2 months", "about 9 months") is already there; slots 1–6 hold `test` |
| `fanbase` | the merchandise table holds half the PAL bases (5,000 at the top, 400 at the bottom); it is scaled from those with the same factors, ×3 at the top to ×0.5 at the bottom |
| `tv-fees` | two TV stations' base offers are higher (270,000 and 300,000 against 150,000 and 111,000); the same rule halves everything above £2M |
| `pr-cycle` | the same code, with `pwkTown_Keiki` at `0x2719d0` |
| `season-status` | the same ladder, so the Japanese build has the same season-ticket bug |
| `salesman-items` | the boost jump table (PAL `0x5313c8`, Japanese `0x52d138`) holds the Japanese addresses of the same cases (`0x210d18` and `0x210e08` for PAL's `0x2104e0` and `0x2105d0`), which trade places as on PAL; the headphones' new code calls `pwkGUtl_AddExp` at its Japanese address, and its branch reaches the same epilogue (`0x210fec`) |
| `vpf-positions` | nothing to do: the release has no Virtua Pro Football import ([below](#confirmed-from-the-game-code)) |
| `real-names` | the English names in ASCII in the Japanese text (slot 0, where the game has katakana), in every list `realnames.py` writes in PAL but the three the Japanese `MES.PAC` lacks (100003, 100009 and 100011); the nations' copy, category 7, is numbered from 6000 there (PAL 5000). The mentions of a competition in other messages are left in katakana. The three-letter forms lose their accents. `MES.PAC` and `STATIONMES0.PAC` grow by 5 and 4 sectors and move to the end of the disc; the built disc's `MES.PAC` is byte for byte what `realnames.py apply` writes (**empirical**, 2026-11-12). Not run in the game |
| `third-tier` | all 93 places plan; the rules text isn't changed ([below](#the-third-tier-on-the-japanese-disc)) |
| `realism` | refused: its pack is named by PAL hashes |
| `random-sponsors` | nothing done: its code is PAL's, and `patch_disc.py` notes it and leaves the release alone |
| the rest | the same bytes, at other addresses |

Every patched spot's surrounding code (8 words either side, immediates
and jump targets ignored) agrees between the builds in at least 12 of 17
words, and the four below 14 are in `pwkUnkei_GetExpectSeat`, whose
registers differ, and the merchandise table. A PAL disc patched with the
same switches is byte for byte as before. No Japanese disc built with
the switches has been run in the game yet.

The disc's UDF file system names the archive `Data.cvm` (PAL: `DATA.CVM`),
so a patch that has to move files (a bigger `MES.PAC`) finds its UDF entry
by the name in any case.

## The third tier on the Japanese disc

`--mod third-tier` (the hidden third tier, [`CLUB_LIMITS.md`](CLUB_LIMITS.md),
[`UID_LIMITS.md`](UID_LIMITS.md)) is 93 patched places in five files,
six data files and some text. It builds for the Japanese disc since
2026-11-12, except for the rules text (below). **Empirical**: all 93
places plan there (each checks that the bytes it finds are the ones it
expects), PAL's 93 jobs are byte for byte what they were, and a disc
built with `--mod third-tier --copies --dat DAT_JP` writes 198 times
(`mod-saves` comes with it: `BISLPM-66316-F` and `-V`). **Tested in
PCSX2** (Nexxus's report, 2026-11-12): the disc boots, a new career
starts, and the game reaches the tutorial's playoffs, whose teams are
the same as on the PAL disc. In a German career the 2nd division
starts with 18 clubs, as on the PAL disc (the retail 20 less two sent
down to the hidden tier). The save
writing and loading, and a season through the third tier, are not
checked yet.

| Part | On PAL | On the Japanese disc |
|---|---|---|
| Code segment: a second program header and a cave in the executable for new code | 2 places, 34 bytes (`SLES_541.51` `0x2c`, `0x54`; the cave's file offset `0x46a350`) | the cave's file offset is `0x465fd0` (the first segment ends at `0x465f5c`, PAL `0x46a2dc`; the cave sits 0x74 after it in both); `e_phnum` and the second header are at the same header offsets; the 0x400 bytes there are zero |
| Bigger save: block 2 (+18 records) and block 5 (+7), the serializers' loops and two wrappers | 7 places, 672 bytes (3 in the executable, 4 in `SAVEPRG.REL`) | the size table is at `0x52f838` (PAL `0x533ac8`) and only block 1 differs (76,256 against 76,272), so blocks 2 and 5 grow to the same sizes. The six `SAVEPRG.REL` sites map with identical bytes (`0x29460`, `0x1b7b4`, `0x29750`, `0x1ba48`, and the dispatchers' return points `0x2b914`, `0x2b94c`); the wrappers' jump from the return address to the serializer differs for the write one (`-0xfefc`, PAL `-0xff54`), and `_plBits_BitRead` and `BitWrite` are at `0x20caa0` and `0x20ca60` |
| Past records for competitions 49–55 | 1 place, 92 bytes (`pwkRec_GetCompePastRecord`) | the function is PAL's but for two `jal` targets; the rewrite inlines `plPwork_GetPwork`, whose global is `lui 0x39 / lw -0x36b8` there (PAL `0x9a8`). Block 5's own layout is the same |
| Clubs 442–459 as full clubs | 41 places (31 executable, 7 `SIMPRG.REL`, 3 `YRSTPRG.REL`) | every one is the word PAL has (same opcode, registers and old immediate) at the same place in the same function; 37 map by `gamever.py`, and the four it can't place (`CMakeDataBase::MakeDB`, PAL `0x2230e0`, two of the four player-candidate loops, `0x2609d0` and `0x260b58`, and `YRSTPRG.REL 0x17014`) are the same word's next occurrence in the Japanese function of the same name, which holds as many of them as PAL's (`Port.expect`) |
| The lists sized for 441 clubs | 30 places, 2,060 bytes (7 executable, 23 `SIMPRG.REL`) | the five relayed functions differ from PAL's in `jal` targets and data addresses only, so every stack offset, frame size and shift of the relay holds; the other places are immediates as for the clubs |
| The tiers' seasons (competitions 50–55) | 6 places, 388 bytes in the executable | the cave's code and `ScheCallback_ProcPromotion`'s rewrite use this build's addresses (`CaveBuild.addr`: `pwkRec_ShiftCompeConventionRecord` `0x253f08`, `pwkLg_GetMyNati` `0x246818`, the competition table `0x5166b4`, and the three jump points in `calcCompetetionFinish`) |
| Game over after one season | 6 words in `SIMPRG.REL` | the same words |
| Data | `OTEAMMEMBER.TBB` (the 18 squads) and five schedule and rules files | the schedule files, `INITTEAMDATA` and `CLUBRESULT` are byte for byte PAL's, and the builders write the same bytes from them; `REGULATION.TBB` differs from PAL's by one byte (`0xec0`); `OTEAMMEMBER.TBB` has other squads, but the 18 new ones come from the tutorial's players (ids from 25,591), whose age and shirt are the same in both player databases |
| Text | the rules messages in five languages | **not done**: the Japanese text keeps its rules messages (the Game Over help, the second division's rules, the news), which state the retail rules. `patch_disc.py` leaves slot 0 alone and notes it |

`patch_disc.py`'s `CaveBuild` holds what differs between the builds for
the code segment, the save wrappers, the past records and the tiers'
seasons (the cave's file offset, the bit routines, the serializers'
offsets, the pwork global, and `addr`, which translates an executable
address with `gamever.py`).

The rules text is the part that needs a decision: written in Japanese
(someone who reads the game's Japanese should check it) or left in
English. The messages are the ones `tier_text_edits` changes in the five
European languages (category 487, 30001, 30003, 832 and 35680).

## Confirmed from the game code

| Address (SLPM_663.16) | Symbol | Compared with PAL |
|---|---|---|
| SIMPRG.REL `0x17010c` | `Msg::SearchGlobalVarHeader` | 0x1b8 global variables (PAL 0x370) |
| `0x202538`, `0x202548` | `MSG_UTIL::CMsgWildCard::getString` | 0x85 converters of 12 bytes `{u32, u32 function, u32 id}` (PAL: 0x10a of 16 bytes, with an argument word) |
| `0x217618` | `plPinfo_KegaRecoverDaysChno` | identical to PAL: the injury messages "two months" and "nine months" are unreachable in both builds (see [`INJURIES.md`](INJURIES.md)) |
| `0x52e998`, `0x52ea68` | injury tables | identical to PAL, kind 6's 1600 included |

The save block sizes differ in block 1 (76,248 bytes against PAL's
76,264), so the layout CRC is `0x16da` (PAL `0xa225`), and the header's
version is `0x68` (PAL `0x69`). Saves of one build can't be loaded by the
other. The layout is PAL's, less the end of block 1 and with a narrower
wristband and gloves ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-japanese-release)).

**The edit player.** The Japanese release has its own player editor in
the game and doesn't import players from Virtua Pro Football (or World
Football Climax); the PAL release has no such editor and imports
instead (Nexxus's report, 2026-11-01). The Japanese `SAVEPRG.REL`
still holds the import's conversion code (`0x3db60`,
[`PMPLAYER_FORMAT.md`](PMPLAYER_FORMAT.md#who-reads-it)), so
`--mod vpf-styles` and `vpf-positions` change nothing a Japanese player
sees.

## Differences in the data (empirical)

| What | Japanese | PAL |
|---|---|---|
| Disc root | `HDD/` (install to the PS2 hard disk), `DRIVERS/` adds `ATAD`, `DEV9`, `HDD`, `PFS` | none |
| Commentary | `AUDIO/BC_JPN.AFS` only: 65,501 unnamed clips, 23.4 hours, its entry count sign-extended from 16 bits ([`AUDIO_DIR.md`](AUDIO_DIR.md#afs)) | ten `BC_*.AFS` of 12,899 named clips |
| `DAT/` | 2,029 files | 2,229: the extra 200 are per-language copies in `CSE/`, `GAME/`, `PRELOAD/` and `STADIUM/` |
| `MES.PAC` | 3,647 files. Slots 1–6 hold placeholders (`test`); 45 records of `0_0.mbb` (the salesman) are filler bytes, not text | 3,738 files, all languages translated |
| `GAME/SOUNDDAT.PAC` | 2 commentary slots of 0x51000 bytes (Japanese, two crowd tables), no BCV index; 33 clip tables from 0xa2000 | 12 slots of 0x1d800, 36 clip tables from 0x162000 |
| `PARAM/PLRESOURCESIM.PAC` | 15 entries: no free-agent list. Entry 0's climate, weather and chance tables hold 44, 49 and 27 whole records | 16 entries; 64 records each |
| `PARAM/PBDATA_*.PAC` | play style, wristband, gloves and keeper gloves above PAL's limits | within them |
| `0SYSTEM/SPONSOR_TEXTURE*.PAC` | 233, 231 and 233 entries | 232 each |
| `CSE/GP_PRACTICEICON.CSP` | the practice icons | 0 bytes; PAL loads the per-language `GP_PRACTICEICON0`–`6.CSP` instead |

Each of these is a `!!` line in a `jp_` check, kept as the baseline,
except the commentary, which `afs.py` reads as documented.

## Still unknown

- Whether the Japanese game draws the real names (Latin letters, up to
  18 for a club) well in its club name field and lists: no Japanese disc
  built with `--mod real-names` has been run (`TESTING.md`).
- Why entry 0 of `PLRESOURCESIM.PAC` stops partway through its tables in
  the Japanese build, and whether its code reads fewer records.
- Whether the player-database limits come from the Japanese code (new
  play styles, kit options) or are data PAL corrected.
- The sponsor texture counts, how the game opens `BC_JPN.AFS` (its
  count reads as −35 through `ADXF_GetNumFilesFromAfs`), and which clip
  is which with no name table.
