<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Club limits: where the game fixes the clubs at 441

The game has 459 club ids, but only 1–441 are "resident": your club (1),
the rival (2) and the computer clubs 3–441 have records in save block 2
([`SAVE_FORMAT.md`](SAVE_FORMAT.md)) and take part in the season's
systems. Clubs 442–459, the tutorial's third-tier opponents, are
"non-resident": they get a temporary league record and players from the
database only while they play ([`LMASTER_MOD.md`](LMASTER_MOD.md#improvements)).
The national teams are 460–542. This doc lists the code that fixes those
limits, for making 442–459 full clubs (the LMASTER third tier, phase 2).

## How the sites were found

Every `addiu`/`addi`/`slti`/`sltiu`/`andi`/`ori` with an immediate of
440 (`0x1b8`), 441 (`0x1b9`) or 442 (`0x1ba`) in the executable and the
ten overlays: 206 sites (**empirical**, the scan below). Each was
read with its function and surroundings. A second pass (2026-10-27)
over every `slti`/`sltiu` with 439–442 that this doc or `patch_disc.py`
didn't yet name found four more: `SIMPRG.REL` `0x918` (Other Club Info)
and `0x15ad4c` (the practice code's club rank), both now in the tables below,
`VSPRG.REL` `0x7808` (VS mode's clubs, below) and the debug counter at
`0x1099fc`, besides the debug modules. A table indexed by club
number without such an immediate (pointer arithmetic over a 441-entry
array) doesn't show up this way; see [Still unknown](#still-unknown).

## Not about clubs

About 140 sites use the same numbers for something else:

| Kind | Where |
|---|---|
| object and structure offsets `+0x1b8` | the window and list tasks' `OpenExecute`/`CloseExecute` (vtable entries), `CEditFaceObject`, `WP::CReport`, `CScrollPlate_Task`, `CSelectTeamStyleTask`, `CTrainingTask`, `CTournament…`, `CDetailManager`'s name copies (`+0x1b8`), `MOVIEPRG.REL`, `TESTPRG.REL`'s emblem editors, `GAMEPRG.REL` |
| offsets inside save block 5 | `pwkRec_GetTeamStats` (`+0x601b8`), `pwkRec_GetGameResultSysBuffer` (`+0xb01b8`), `pwkEdit_CallPwkEdit`, the matching `SAVEPRG.REL` serializer sites (`0xdd10`, `0x1d004`, `0x2b088`) |
| screen layout | the detail pages' `SetupDetail…Page` (`$t1` = 442, a coordinate beside 330 or 310) |
| message, event and variable ids | `SIMPRG.REL` `CEventTitle` (24 sites, `$a2` = 442 with ids 8–0x1d), `EVS::CEvsManager::Req` (21 sites, `$a0` = 440), `EVS::SetEventFlag`, `Msg::GetVariableBuffer`, `ROFS_SetIsoDir`, `ImageTransfer::initialize`, and `SIMPRG.REL` `Msg`'s jump tables over 441 message variables (`0x1706e0`, `0x171f48`, `0x1721f4`) |
| debug modules | `FC_EURO_DUMMY_MODULE::CPlayerPositionSetAndStamemPointDis` (a counter wrapping at 441, `0x1099fc`), `TESTPRG.REL` `CHayasiTestModule` (`0x106ec`), `DEBUGPRG.REL` (`0x3170`) |

## About clubs

**Confirmed** from the code, by kind:

| Kind | Sites |
|---|---|
| Loops over clubs, to 441 inclusive (`slti …, 0x1ba` or a count of 441) | `pwkOteam_Init` (`0x24a738`, the squads from `OTEAMMEMBER.TBB`), `pwkOteam_Init2` (`0x24a60c`, ranks and world points), `PlBpinfoTask::updatePlCoreInfoSub` (`0x20d314`), `CMakeDataBase::MakeDB` (`0x2230e0`), `GetOfferClub` (`0x225808`, `0x225864`, `0x2258e8`, `0x225974`), `CComOffer::CalcuOfferClub` (`0x22628c`), `CAcquirePlayer::GetExecuteTeamList` (`0x221d94`, `0x221dbc`), `CContractReform::GetExecuteTeamList` (`0x223eb8`), `pwkOteam_ChangeFS_BranchEstablish`/`Remove` (`0x24a8d4`, `0x24a944`), `pwkTeam_UpdatePlayerCandidates` (`0x2607d4`, `0x260830`, `0x2609d0`, `0x260b58`), `pwkTeam_UpdateYouthCandidatesRankSet_ForAbil` (`0x262c20`), `YRSTPRG.REL` `ZinziYearStart::calcYearStartSecondHalf` (`0x17014`, `0x172ac`, `0x1783c`) |
| A club is resident (club < 442, or club − 2 < 440) | `SIMPRG.REL` `0x15ad30` (from `CPracticeExecute`'s code, `0x158470`: the club's rank ÷ 4, up to 7, for the practice code, and 0 for a club not resident; what the practice uses it for isn't traced; the check at `0x15ad4c`), `pwkOteam_GetOpinfoPointer` (`0x24b930`), `pwkOteam_GetRank` (`0x24bef8`), `pwkOteam_GetWorldClubRank` (`0x24bfa0`), `pwkOteam_GetTeamData` (`0x24bcd4`), `pwkOteam_Init`'s squad set-up (`0x24a788`), `pwkMatchGrow_Grow` (`0x24671c`), `pwkMoney_CalcuPurchaceOtherTeamPlayerTransferMoney` (`0x24829c`), `plTeam_IsPurchaseOKFromCOM` (`0x228c9c`), `CAcquirePlayer::PickupPlayer` (`0x2228b0`), `pwkRental_CheckOpenRentalTeamByFriend`/`ByBranch` (`0x2551b8`, `0x255278`), `pwkTeam_AddReleaseList` (`0x25a8c4`), `CDetailManager::ConvertPlayer_Type` (`0x284dcc`, `0x284e5c`), `SIMPRG.REL` `CPlayerSearchWindow_Task::GetPlayerAcquireCost` (`0x9263c`), `ZinziYouthTeam`/`ZinziMyTeam` (`0x15afa4`, `0x15b488`, `0x15bc5c`), `CKeyboard_Task::RecoveryInit` (`0x69924`) |
| Lists and buffers of 440 or 441 clubs | `GetOfferClub`'s five lists and `SetLotClub` (`0x2256c8`, a list's bound), `plTeam_GetClubrankList` (`0x22c09c`–`0x22c144`: 441 × 8 bytes on a `0xe20` stack frame, sorted with 441), `ScheEuro_TeamEntryList` `getTeamIdFromNation`/`Region` (`0x20afb4`, `0x20b064`: clubs 3–440, at most the count given) and its callers `getList_SRC_KIND_UEFA_XXX`, `_CLUBRANK`, `_FIFA` (`0x20b504`, `0x20b700`, `0x20b880`: 440 entries at `+0x478` of the list) |
| The world ranking | `SIMPRG.REL` `ClubRank` (`0x150684`–`0x1521e0`, 14 sites): a list of 441 clubs on the stack of its club update (`0x150680`), and its helpers' loops over clubs; each club's points and rank are in its block 2 record (`+0x9c`, `+0xa0`–`+0xa4`) |
| Lists of a nation's or region's clubs, capped | `SIMPRG.REL` `CReport_month` (`0xa1194`, `0xa1244`, `0xa12f0`, `0xa1318`: 50 at most), `CEDITPRG.REL` (`0x2d84`: as many as its caller allows) |
| Save block 2's serializers | `SAVEPRG.REL` `0x29548`, `0x1b844` (patched by `--mod third-tier`), and the older reader's `0xc1d0` (version `0x68` saves only) |
| The non-resident path, for 442–459 | `_pwkOteam_GetPlRec_LgTeamNonresident` (`0x24d65c`), its player base (`0x24d6b0`, `0x24d748`), the league records' set-up `0x24d454` (clubs `0x1ba`–`0x1cb`, players from `0x63f7`), `pwkOteam_ResetRentalPossibleClubFlag` (`0x24ca18`) |
| Not yet understood | `CScheEuro::clearPlayerRecord` and `movePlayerRecord` (`0x2078a0`, `0x207a98`): clubs below 441 skip a player lookup that 441 and up take |

## `--mod third-tier`: the clubs (phase 2a)

`patch_disc.py --mod third-tier` (built as `tier-clubs`), with the
bigger save's block 2 records, makes clubs 442–459 full clubs, as far as
code that
works one club at a time goes:

- `pwkOteam_Team2Otindex` maps clubs 3–459 to records 1–457.
- Every resident check above takes 442–459 in (club < 460, club − 2 <
  458, club − 3 < 457), and the non-resident path starts at 460.
- The three special cases for 442–459 are off: purchase offers
  (`0x2289ec`), team data (`0x24bb10`) and the detail screen's page type
  (`0x288460`).
- The loops below that work through block 2 run to 459, among them
  `pwkOteam_Init`, which reads 18 more squads from `OTEAMMEMBER.TBB`
  (`initteam.add_tier_squads`: each club's 25 database players from
  `0x63f7`, with their ages and shirt numbers, contracts of 2 years).

The loops that fill buffers sized for 441 clubs stay as they are, so
they leave 442–459 out; [the lists](#--mod-third-tier-the-lists-phase-2b)
grows them. A save from before the switch has empty records for the new
clubs; start a new career.

**Tested in PCSX2** (Nexxus's report, 2026-10-26): with `save-expand`,
`tier-clubs` and `mod-saves`, a new career (tutorial skipped) plays
through a transfer window and saves and loads, and the tutorial's
promotion playoff against the third-tier clubs plays; "all working".

## `--mod third-tier`: the lists (phase 2b)

`patch_disc.py --mod third-tier` (built as `tier-lists`) grows the
lists sized for 441 clubs to 459, and the loops that fill and read them
run to 459. A list on the stack grows with its function's frame:
`relay_frame` moves every `$sp` offset from the list's end on, the
saved registers included, and refuses any use of `$sp` it can't map.
**Confirmed** from the code of each function:

| Function | Lists | Frame |
|---|---|---|
| `plTeam_GetClubrankList` (`0x22c098`) | clubs 1–441 × 8 bytes (club, rank), sorted by rank; the caller gets 441 words | `0xe20` → `0xeb0` |
| `CAcquirePlayer::Execute` (`0x221720`), the transfer AI | the club-rank list (`$sp + 0x6f0`) and the clubs that buy this time (`$sp`, from `GetExecuteTeamList`, `0x221d94`/`0x221dbc`), 441 words each | `0xe90` → `0xf10` |
| `CContractReform::GetExecuteTeamList` (`0x223e10`) | the club-rank list at `$sp`; its caller's list (`$sp + 0x70` of `0x223ee0`, `0x6f0` bytes) takes every fourth club, so it already fits | `0x730` → `0x770` |
| `GetOfferClub` (`0x2256f8`), offers for your players | a flag per club 0–441 (`$sp + 0x10`), the clubs drawn (`$sp + 0x700`) and three lists by nation (`$sp + 0xdf0`, a stride of `0x6e8` at `0x2259d0`), each filled by `SetLotClub` up to 442 entries; their counts at `$sp`–`$sp + 8` and `+0x22b0` | `0x2360` → `0x24b0`, each list 460 words |
| `SIMPRG.REL` `0x150680`, `ClubRank`'s club update | clubs 1–441 × 8 bytes (the points, and at `+2` and `+4` the points from past records), filled by `0x1514c8`, `0x151568` and `0x152128`, written back by `0x151510` | `0xdf0` → `0xe80` |

Also to 459: `ClubRank`'s other loops over clubs (`0x150d94`, the year's
reset; `0x151758`, its draw by nation, 220 a nation at most; the counts
and lists by main league and by nation at `0x151a70`–`0x151be8`, whose
lists are allocated by the count), and the past-record points by nation
(`0x1521e0`) take the nation of 442–459 from the club as for the others
(the retail code would add them to nation 1). `CReport_month`'s lists
by nation and region run to 459 too; they stop at 50 clubs.

**Other Club Info** (My Room > Information > Club Info): you pick a
nation, then a club from one list of its clubs (Nexxus's report). The list
comes from `SIMPRG.REL` `0x8e0`, which walks clubs 2–441 (`slti …,
0x1ba` at `0x918`), keeps those of the nation (`plMisc_Club2Nati`) and
stores each club's id and name, up to the count its caller gives: 50
for the list itself (`0x1848`, names at `0x248410` and ids at
`+0x55cc` of the module, menu entries of `0x54` bytes in its `0x1100`
frame) and for the map window's count of each nation's clubs
(`0x1ae8`). **Confirmed** from the code. So 442–459 were left out
(Nexxus's report on `LMAST-test-tiers-germany.iso`), and `third-tier`
makes the bound 460. With the tier, the most clubs a nation has is 47
(nation 1, 44 before; **empirical**, `PLRESOURCECOMMON.PAC` entry 3
table 5), so the cap of 50 cuts none off. **Tested in PCSX2** (Nexxus's
report, 2026-10-27, `LMAST-test-max-germany.iso`): Other Club Info
lists the tier's clubs and shows their info.

`VSPRG.REL` `0x7808` builds VS mode's club list from clubs 3–441 of the
six main nations; it is left as it is, so VS mode offers the clubs the
retail game does.

The **All Clubs Ranking** screen (Information, `SIMPRG.REL` `0x84df0`)
lists the clubs from a table at `0x1cf848` (52 nations, 145 national
teams, 441 clubs, each from id 1). Each club's rank is its own (block 2
`+0xa4`), so with only the count raised to 459, 442–459 would still
miss the list and leave gaps in its numbers. **Seen in PCSX2** (Nexxus's
report): before this, the list showed ranks 437, 440, 441, 442 (your
club) and 443, with 438 and 439 missing. The list's object
(`INFORMATION_MODULE + 0x4074`, cleared for `0xe80` bytes) has room for
441 at `+8` (a pointer per club) and `+0x79c` (an index per club), with
the column records at `+0x6ec` between them. The pointers are only
`+0x798` (the sorted data, 12 bytes a club) + 12 × i, and nothing reads
the indices, so `third-tier` stops writing both (`0x85094`, `0x850a8`)
and the one reader, `CNationRankList_Task` (`0x84b08`), walks the data
with a pointer of its own (`0x84bd4`, `0x84bf8`, `0x84c1c`,
`0x84c24`). The count becomes 459.

Left as they are:

- `ScheEuro_TeamEntryList`'s lists, the European places filled by club
  rank (clubs 3–440, at most 440). They stop at the count they are
  given, so they can't overflow. Clubs past 440 still reach Europe by
  their league and cup records.
- `CEDITPRG.REL` `0x2d84`, the club editor's clubs of a nation, capped
  by its caller.
- `CScheEuro::clearPlayerRecord` and `movePlayerRecord`, not yet
  understood.

**Tested in PCSX2** (Nexxus's report, 2026-10-27): on
`LMAST-test-tierlists2.iso`, the All Clubs Ranking at the start of the
first season lists every club, numbered with no gaps. A German career
on an LMASTER max build (Nexxus's report, 2026-10-27; then built as
`--mod lmaster-full`) passed both transfer windows and the season's
end, and saved and loaded. The world ranking's update at the season's
end wasn't looked at in that career; an earlier test showed it working
(Nexxus's report).

## Each loop's body

Whether a loop over clubs can simply run to 459, or fills a buffer
sized for 441 clubs. **Confirmed** from the code, as each was read:

| Loop | Body | To 459 |
|---|---|---|
| `updatePlCoreInfoSub` (`0x20d314`) | each club through block 2 (`updatePlCoreInfoSub_Team_OteamOne`, `0x20cdb8`), which records the club on its players' core info; your club's players get `0x1cc` (460), past every club | as it is |
| `CMakeDataBase::MakeDB` (`0x2230e0`) | each club through block 2 (`MakeDBEach`) | as it is |
| `pwkOteam_Init` (`0x24a738`) | each club's 25 squad slots, read in order from `OTEAMMEMBER.TBB` | with 18 squads added to the file |
| `GetOfferClub` (`0x225808`…) | a 4-byte entry per club on the stack at `$sp + 0x10`, below other buffers in a `0x2360`-byte frame | the frame relaid (`third-tier`) |

## Tables indexed by club

**Empirical**, from the 161 executable functions that take a `PlTeam`
(and 3 in `SIMPRG.REL`), each listed with the functions it calls and the
data it loads: apart from save block 2, the tables they index by club
already cover clubs to 459. **Confirmed** for the main ones:

| Table | Covers | Reader |
|---|---|---|
| club records, `PLRESOURCESIM.PAC` entry 3 | clubs 3–459 | `plOteam_GetDb` (`0x2165d8`) |
| club → nation, `PLRESOURCECOMMON.PAC` entry 3 table 5, a byte per club | clubs below 460 (`slti 0x1cc`) | `plMisc_Club2Nati` (`0x215af0`), and through it `plMisc_Club2Region` |
| city clubs, `0x531f30` | searched by club id | `plOteam_SearchCteam` (`0x216590`) |
| league entries | searched by club id (`bsearch`) | `plLg_GetEntry` (`0x2e9630`) |
| the other clubs, save block 2 | clubs 2–441 (records 0–439); 18 more records with `--mod third-tier`, which `pwkOteam_Team2Otindex` (`0x24b7e8`, club − 3 < 439) reaches once its bound is 457 | `pwkOteam_GetPointer` (`0x24b788`); a club past 441 gets record 1, club 3's |

So the risk for a club past 441 was in the buffers the loops above
fill, which `--mod third-tier` grows; `ClubRank` keeps its points in
block 2, not in arrays of its own.

## Still unknown

- Tables indexed by club number with no 440–442 immediate: per-club
  arrays in the save blocks (block 5's team records among them) and in
  objects. Each would overflow for a resident club past 441.
- What `clearPlayerRecord` and `movePlayerRecord`'s test of 441 is for.

## Checking

The scan is a short script over `gamever.image` of each file (every
immediate of the six kinds equal to 440–442, with the nearest named
function); `python SRC/sles_disasm.py ISO/SLES_541.51 addr <hex> 20`
shows any site.
