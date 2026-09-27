<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/0SYSTEM`: game-wide tables, texture packs and fonts

`DAT/0SYSTEM` (22 files, 24 MB, plus `CVS/`) is folder id **0** in the
game's file manager (`0x14eb4c`, see [`PRELOAD_DIR.md`](PRELOAD_DIR.md)).
It holds the UI colour table, the crest, badge and sponsor textures, the
fonts, the memory-card icons and a few leftovers.

Every container parses with the existing tools: `python SRC/tbb.py info
DAT/0SYSTEM`, `python SRC/pac.py info DAT/0SYSTEM` and `python SRC/svr.py
info DAT/0SYSTEM`. `python SRC/system.py info DAT/0SYSTEM` checks the
layouts described here.

| File | Kind | Read by | Contents |
|---|---|---|---|
| `COLORDATATABLE.TBB` | TBB, 1 table | `etc::InitializeGameSystem` | 77 UI colours. **confirmed** |
| `DETAILFLAG.TBB` | TBB, 1 table | `WP::CDetailManager` | 528 one-byte flags; the first 99 are used. **confirmed** (meaning unknown) |
| `EMBLEM_TEXTURE.PAC` | BINPAC, 634 SVR | `CFcEuro_CommonTexture` type 0 | club, nation and special-team crests. **confirmed** |
| `FLAG_TEXTURE.PAC` | BINPAC, 634 SVR | type 1 | an older copy of the crests; one differs. **confirmed** |
| `MATCH_TEXTURE.PAC` | BINPAC, 70 SVR | type 2 | competition badges, large (`*_L`). **confirmed** |
| `MINIMATCH_TEXTURE.PAC` | BINPAC, 70 SVR | type 3 | the same badges, small (`*_S`). **confirmed** |
| `MINIEMBLEM_TEXTURE.PAC` | BINPAC, 10 SVR | type 4 | small crests, 72 to a sheet. **confirmed** |
| `SPONSOR_TEXTURE.PAC` | BINPAC, 232 SVR | type 5 | sponsor logos `sup_000`–`sup_231`. **confirmed** |
| `SPONSOR_TEXTURE_M.PAC` | BINPAC, 232 SVR | type 6 | the same sponsors, `txcmn_adt_000`–`231`. **confirmed** |
| `SPONSOR_TEXTURE_S.PAC` | BINPAC, 232 SVR | type 7 | the same sponsors, `BG_IP_ADT_000`–`231`. **confirmed** |
| `FONT_KANJI.SVR`, `FONT_ASCII.SVR` | SVR 1024², 256² | `CFontTexture_fc_euro::LoadTexture`, language 0 only | Japanese fonts. **confirmed** |
| `FONT_20_A.SVR` | SVR 256² | the same, languages 1–6 | the European font. **confirmed** |
| `FONT_8_A.SVR`, `FONT_8_B.SVR` | SVR 128² | the same, every language | small fonts. **confirmed** |
| `FONT_KANJI_A.SVP`, `FONT_KANJI_B.SVP` | SVP, 16 colours | nothing | not named anywhere in the code |
| `STATIC.ICO`, `STATIC_VS.ICO` | PS2 icon | `MC::CFcEuroIF::setFileInfo`, `SAVEPRG.REL` | the save and VS-data icons. **confirmed** |
| `SAVE_VERSION.DAT` | text, 58 bytes | the root module's load list | a developer note (below) |
| `MSGCOMMON.TBB` | TBB, 3 tables | nothing | a 2004 name table (below) |
| `SCHEDULE.TBB` | TBB, 2 tables | nothing | an unreferenced 2005 schedule, see [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md) |

Two of these files also have copies in `PRELOAD` packs, which the season
mode reads instead ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)):
`miniemblem_texture.pac` in `SIMFILE0`–`6`, and `DetailFlag.tbb` in
`SIMLOCALMEM0`–`6`. Patch edits to them with `patch_disc.py --copies`.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x149a90`, `0x149b0c` | `etc::InitializeGameSystem` | reads `ColorDataTable.tbb` at start-up and passes it to `clr::SetTbbFileBuffer(buf, 0x4d)` |
| `0x1f8e08` | `clr::SetTbbFileBuffer` | the colour count is table size ÷ (line size × 4), so 308 ÷ 4 = 77 |
| `0x1f8ef0` | `clr::GetRGBA(id, float*...)` | a colour is 4 bytes R, G, B, A, each divided by 255.0 |
| `0x283610`–`0x283714` | `WP::CDetailManager` constructor | opens `DetailFlag.tbb` (folder 0) and copies its first `0x63` (99) bytes to `+0x23d9` |
| `0x34d3f8` | (name table) | the 8 texture packs, in type order 0–7 |
| `0x105950` | `CFcEuro_CommonTexture(type, id, ...)` | one texture from one of the packs |
| `0x1057e8`, `0x105c70` | `ConvertFlag`, `ConvertIndex` | turn a team, competition or sponsor id into an entry index (below) |
| `0x28e354`, `0x28e474` | `WP::CDetailTeamFlag::Execute` | the team detail crest: type **1** for the first team shown, type **0** for every later one |
| `SIMPRG.REL 0x8294c` | `WP::CMapWindow_Task::SetLogoDraw` | type 0 |
| `0x2c2f2c`, table `0x55a248` | `CUniformLoader::_load_edit` | types 0, 5 and 7: the kit's crest and sponsors |
| `GAMEPRG.REL 0x20858c`, table `0x29e2b0` | (match overlay) | types 0, 0 and 2: both teams' crests and the competition badge |
| `SIMPRG.REL 0x2144e8`–`0x2146a0` | the season load list | 12 type-4 records that preload the mini-crest sheets |
| `0x149108` | `CFontTexture_fc_euro::LoadTexture` | language 0 loads the font set at `0x35d400` (`font_kanji`, `font_ascii`, `font_8_a`, `font_8_b`); other languages the set at `0x35d458` (`font_20_a`, `font_8_a`, `font_8_b`) |
| `0x12af80` | `MC::CFcEuroIF::setFileInfo` | `static.ico` is the save's icon. `SAVEPRG.REL` names `static.ico` and `static_vs.ico` |
| `0x51abe8` | root module load list | loads `save_version.dat` from folder 0. Nothing else in the code names it |

## Crests: `EMBLEM_TEXTURE` and `FLAG_TEXTURE`

Each pack holds 634 128×128 textures in the same order. The entry for a
team id (`ConvertFlag` `0x1057e8`, then `ConvertIndex` `0x105dc4`) is:

| Team id | Entry | Names |
|---|---|---|
| 0–2 | none. These ids are the `NOT`/`USE`/`RIV` placeholders in the name table | |
| 3–459 (clubs) | id − 3 = 0–456 | `emb_C003`–`emb_C459` |
| 460–542 (national teams) | `plMisc_NatiTeam2Nati(id)` + 459 − 3 = 457–601 | `emb_N001`–`emb_N145` |
| 543 and up | id + 62 − 3 = 602–633 | `emb_V001`–`emb_V032` |

`ConvertVs` (`0x105748`) swaps ids 543–558 in some matches, depending on
the current schedule and on `GetEmblemTexture`/`GetEmblemTextureRival`.
The `V` crests are probably the player's own and the rival's clubs, but
that hasn't been checked.

`python SRC/system.py emblem DAT/0SYSTEM <team id>` gives the entry.

**The two packs differ in one crest (empirical).** `emb_C140`, Siena, is a
made-up crest (a white animal on a black and white oval) in
`EMBLEM_TEXTURE`, and the real A.C. Siena crest in `FLAG_TEXTURE`. The other 633 entries are
byte-identical. The file dates are June 2006 for `EMBLEM_TEXTURE` and
May 2006 for `FLAG_TEXTURE`, so the real crest was probably replaced late.
Because `CDetailTeamFlag` loads type 1 for the first team it shows, a team
detail screen should show the real crest first and the generic one after
switching teams. Not checked in the game.

## Competition badges: `MATCH_TEXTURE` and `MINIMATCH_TEXTURE`

70 badges each, large (`*_L`, 17,440 bytes) and small (`*_S`, 2,080
bytes), with the same names in the same order. The entry is the
competition id from `ScheEuro_SubCtrl::getScheCompe_FromTBB`
(`0x105d50`), except for the language-dependent badges
(`0x105d64`–`0x105da4`):

- Competition `0x31`, and 56–71: entry 56 + language (`EXHIBITION_0`–`6`).
- Competition `0x30`: entry 63 + language (`YOUTH_LEAGUE_0`–`6`).

Entries 48 (`YOUTH_LEAGUE_0`) and 49 (`EXHIBITION_0`) are therefore never
used. Some badges appear twice (`CHAMPIONS_DIVISION`, `ENGLISH_CUP`,
the national cups), once per competition id that shares them.

## Mini-crests: `MINIEMBLEM_TEXTURE`

10 sheets of 72 crests each (66,592 bytes). `emb_sc1`–`emb_sc7` hold the
clubs, sheet (id − 3) ÷ 72. `emb_sn1`–`emb_sn3` hold the national teams,
sheet 7 + (nation − 1) ÷ 72 (`ConvertIndex` `0x105cc0`–`0x105d2c`).
`GetMiniEmblemU0`/`U1`/`V0`/`V1` (`0x106678`–`0x106928`) give a crest's
place on its sheet. They weren't decoded further.

## Sponsors: `SPONSOR_TEXTURE`, `_M`, `_S`

232 sponsors in three sizes (16,416, 4,640 and 8,224 bytes). The entry is
sponsor id − 1, and id 0 also gives entry 0 (`0x105db4`). The kit loader
uses types 5 and 7. Type 6 (`txcmn_adt_*`, advert boards by the name) has
no caller: the constructors are called at the sites above, from the season
load list, and from the Uniform Viewer (`TESTPRG.REL 0x14da8`, type 0),
and none of them asks for type 6.

## `COLORDATATABLE.TBB`

One `TBL1` table, 308 bytes: 77 colours of 4 bytes, R, G, B, A.
`clr::GetRGBA` is called at 13 sites in the executable and 45 in
`SIMPRG.REL`, and nowhere else. Colour 0 is transparent black. The alphas
are `ff` (65 colours), `a0` (5), `96` (3), `50` (2), `aa` (1) and `00`
(1). Which screen element uses
which id hasn't been mapped. `python SRC/system.py colors DAT/0SYSTEM`
lists them.

## `DETAILFLAG.TBB`

One `TBL1` table of 528 bytes, line size 1. The values are 0 (197),
1 (318), 2 (9) and 3 (4). `CDetailManager` only copies bytes 0–98, and the
game code doesn't show what they switch. 528 = 16 × 33, and the manager
clears a 33-byte array next to the copy, so the table may be 16 rows of 33
flags. That is a guess.

## `SAVE_VERSION.DAT`

58 bytes of text: "save data now ver. 105", "old ver. 104",
"pbdata ver. 33", "z". It is a developer note. The numbers match the save
header ([`SAVE_FORMAT.md`](SAVE_FORMAT.md)): version `0x69` = 105 is
current, and `0x68` = 104 goes to an older reader. The root module loads
the file at start-up, but no code reads its contents.

## `MSGCOMMON.TBB`

Dated August 2004, and not named anywhere in the code. It has three tables
of fixed-width ASCII names:

| Table | Rows × bytes | Contents |
|---|---|---|
| 0 | 80 × 32 | competition names (`Premier Division`, `FA_CUP`, `CARLING_CUP`, ...) |
| 1 | 1,158 × 32 | club names in capitals, each followed by a 3-letter form (`HIGHBURY`, `HIG`), starting with `USER`/`USE` and `RIVAL`/`RIV`: 579 clubs |
| 2 | 126 × 24 | nation names and 3-letter forms (`ENGLAND`, `ENG`): 63 nations |

It predates the message files, where these names now live
([`MBB_FORMAT.md`](MBB_FORMAT.md), categories 3–5).

## Icons

`STATIC.ICO` and `STATIC_VS.ICO` start with the PS2 memory-card icon
header: `0x00010000`, 1 shape, texture type 7, 1.0, then 1,560 and 1,470
vertices. The rest of the format is Sony's standard one and isn't
described here.

## Still unknown

- What the `DETAILFLAG.TBB` flags switch, and why only 99 of 528 bytes
  are read.
- Which UI element uses each of the 77 colours.
- Who the `V001`–`V032` crests are.
- Whether anything uses `SPONSOR_TEXTURE_M.PAC` (type 6).
- The `FONT_KANJI_*.SVP` palettes (unreferenced).
- In game: whether a team detail screen shows the real Siena crest first.
