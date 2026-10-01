<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/NEWS`: the newspaper's pictures and the monthly ranking flags

`DAT/NEWS` (11 files, 5.7 MB, plus `CVS/`) is folder id **15** in the
game's file manager ([`PRELOAD_DIR.md`](PRELOAD_DIR.md)). It holds the
pictures of the season-mode newspaper: mastheads, article pictures,
adverts and cartoons. It also holds one table, which says in which months
the paper prints the best-player rankings.

The article text isn't here. It is in `MES.PAC` categories 832 and 833,
and the articles themselves are the NEWS records of
`EVENT/EvsDataBin_NEWS.bin` ([`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md)).

`python SRC/news.py info DAT/NEWS` checks the layouts described here.
`python SRC/pac.py list DAT/NEWS/NEWS_ART.HED` lists a pack, and
`python SRC/svr.py png` turns extracted entries into PNGs.

| File | Kind | Read by | Contents |
|---|---|---|---|
| `NEWS_TITLE.PAC` / `.HED` | BINPAC, 24 SVR, 256×64 | `NEWS::CFactory` | mastheads, 4 per league. **confirmed** |
| `NEWS_ART.PAC` / `.HED` | BINPAC, 286 SVR, 128×128 | `NEWS::CFactory`, one entry at a time | article pictures. **confirmed** |
| `NEWS_AD.PAC` / `.HED` | BINPAC, 35 SVR, 64×64 | `NEWS::CFactory`, every entry | adverts. **confirmed** |
| `NEWS_CARTOON.PAC` / `.HED` | BINPAC, 15 SVR, 64×64 | the same | cartoons. **confirmed** |
| `NEWS_OTHER.PAC` / `.HED` | BINPAC, 2 SVR, 64×64 | the same | a filter and a sponsor picture. **confirmed** |
| `NEWSMONTHFLAG.TBB` | TBB, 1 table | `CNewsStockManager` | 144 (competition, month) flags. **confirmed** |

Each `.HED` is a byte-for-byte copy of its pack's header (**empirical**,
all 5), as elsewhere on the disc ([`PAC_FORMAT.md`](PAC_FORMAT.md)).

## Copies in `PRELOAD`

`PRELOAD/NEWS0.PAC`–`NEWS6.PAC` (one per language) hold `news_ad.pac`,
`news_cartoon.pac`, `news_other.pac`, `news_title.hed`, `news_title.pac`
and `news_art.hed`, with the two newspaper layouts and the article text.
`NEWS_ART.PAC` (5 MB) is not in them: only its header is preloaded, and
the pictures are read from the disc one at a time. `NEWSMONTHFLAG.TBB` is
in `SIMLOCALMEM0`–`6`. The `.HED` files of the ad, cartoon and other packs
are in no pack. Patch edits with `patch_disc.py --copies`
([`REBUILD.md`](REBUILD.md#copies)).

## Confirmed from the game code

Addresses are in `DLL/SIMPRG.REL` unless marked.

| Address | Symbol | What it shows |
|---|---|---|
| `0x24948` | `NEWS::CFactory` state machine (jump table `0x219730`) | loads `news_ad.pac`, `news_cartoon.pac`, `news_other.pac`, `news_art.hed` and `news_title.hed` with `CLoader::loadFileRequest`, folder `0xf` |
| `0x24758` | (`NEWS::CFactory` helper) | loads one entry of a pack by index through its header (`getBinary`, then `loadSvrSectorFileRequest`, folder `0xf`) |
| `0x24868`–`0x24920` | the same | requests entries 0–34 of the ads, 0–14 of the cartoons and 0–1 of the others |
| `0x24b9c`–`0x24c38` | the same | `pwkLg_GetMyLeague` picks four masthead entries from the tables at `0x2198a8`, `0x2198c0`, `0x2198d8` and `0x2198f0`: entries 4 × league + 0, 1, 2 and 3 |
| `0x24d60`–`0x24dd0` | the same | for each of the page's articles whose picture kind (`+0x130`, getter `0x14d078`) is 1, loads entry `+0x134` (getter `0x14d080`) of `news_art.pac` |
| `0x14d620` | `CNewsStockManager` constructor | opens `NewsMonthFlag.tbb` from folder `0xf` (`CDataHandle::OpenImm`) |
| `0x14ddf8` | (`CNewsStockManager` method) | walks the table as 4-byte records and returns 1 when one matches the competition (u16 at `+0`) and the date's month (byte 3 of `PlDate`, compared with `+2`) and has a non-zero flag (`+3`) |
| `0x14dea8`–`0x14dfd8` | (`CNewsStockManager` method) | asks `0x14ddf8` about division 0 and division 1 of the player's nation (`plCompeData_getScheCompe_FromNationDiv`). When it says yes, it fills a `CBestPlayerManager` ranking and posts it (`0x14d738`) |
| `TESTPRG.REL 0x2680` | `SAKAUETEST_MODULE::CNewsTextureTestTask` | a test module that loads `news_ad.pac` |

## Mastheads: `NEWS_TITLE`

Entry 4 × *league* + *k*, with *league* from `pwkLg_GetMyLeague`:

| *k* | Name | What |
|---|---|---|
| 0 | `news_title_L_1` | the first paper |
| 1 | `news_title_L_2` | the second paper |
| 2 | `news_title_L_sp_1` | the first paper's special edition |
| 3 | `news_title_L_sp_2` | the second paper's special edition |

The code loads all four. Which of the two papers a given page uses
hasn't been traced.

The mastheads show the league order (**seen in the textures**): 0 England,
1 France, 2 Germany, 3 Italy, 4 Spain, 5 the Netherlands. Each country has
two papers with made-up names in its own language. That is the same order
as the competition ids below.

## Article pictures: `NEWS_ART`

286 pictures, 128×128, 8 bits per pixel (284 with a 32-bit palette, and
entries 91 and 92, `…rss_three_00`/`01`, with a 16-bit one). An article's picture comes from
NEWS record `+0x14`/`+0x18`/`+0x1c`, through the selectors described in
[`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md#news-record-192-bytes). The
result, at article `+0x134`, is the entry number.

The names group the pictures (**empirical**, from the pack): weather
(`sunny`, `cloudy`, `rain`, `snow`), mood (`very_good` ... `very_bad`,
`up`, `down`), the club (`club_0`/`1`, `sta_0`–`3`, `field`, `airport`,
`bus`), facilities being built (`dounyu_01`–`09`, with 32 variants each
for 6 and 8), shops (`shop_line`, `shop_ten`, `shop_two`, 32 each),
the front page (`front_twenty`, `front_two`, 32 each) and press, stand
and shop pictures with `_a`/`_b` halves. What the 32 variants stand for
hasn't been checked.

Names in a pack hold only the last 16 characters of the original path
([`PAC_FORMAT.md`](PAC_FORMAT.md)), so `news_art_rain.svr` appears as
`ews_art_rain.svr`. The full names here are restored by the obvious
prefix.

## Adverts, cartoons and the rest

`NEWS_AD` holds 35 adverts for bikes, cars, cable TV, goods, PCs, phones
and snacks, each in up to three shapes (`_h_`, `_s_`, `_v_`: probably
horizontal, square and vertical) and one or two versions. All are 64×64
at 4 bits per pixel, the adverts with 16-bit palettes and the rest with
32-bit ones. `NEWS_CARTOON` holds 15 cartoons (`cartoon`,
`cross`, `irony`) in the same three shapes. `NEWS_OTHER` holds
`news_other_filter16` and `news_other_sponsaor_1` (spelled so). The
factory loads all of them for every newspaper. Where each is placed
wasn't traced.

## `NEWSMONTHFLAG.TBB`

One `TBL1` table of 576 bytes with line size 1. The game reads it as 144
records of 4 bytes (**confirmed**, `0x14ddf8`):

| Offset | Type | Field |
|---|---|---|
| `+0` | u16 | competition id (`getScheCompe`) |
| `+2` | u8 | month, 1–12 |
| `+3` | u8 | 1 = print the best-player ranking that month |

The 12 competitions are the top two divisions of the six leagues (the
names are those of the `MATCH_TEXTURE` badges, see
[`0SYSTEM_DIR.md`](0SYSTEM_DIR.md#competition-badges-match_texture-and-minimatch_texture)):

| Ids | League |
|---|---|
| 0, 1 | Premier Division, Champions Division (England) |
| 6, 7 | French Division 1, 2 |
| 11, 12 | first and second German leagues |
| 16, 17 | Italian leagues A and B |
| 22, 23 | Spanish Division 1, 2 |
| 27, 28 | first and second Dutch leagues |

Every competition has every month once. The records run month by month
from July to June, the 12 competitions in id order within each month. 118 of the
144 flags are set (**empirical**): August to May for every league except
the Dutch ones, which stop after April. July and June are off.
`python SRC/news.py months DAT/NEWS` prints the grid.

The lookup counts its loop with `GetDataTableCount`, which is 576 for a
table of line size 1, while it steps 4 bytes at a time. A competition or
month that isn't in the table would make it read past the end. The game
only asks about the 12 ids above, so this never happens.

## Still unknown

- Which of the two papers a page uses, and when the special editions are
  used.
- What the 32 variants of the shop, front-page and facility pictures
  stand for (probably the club colours).
- Where the ads and cartoons go on the page, and how they are picked.
