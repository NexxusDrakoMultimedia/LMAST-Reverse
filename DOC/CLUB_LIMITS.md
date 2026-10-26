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
eleven overlays: 206 sites (**empirical**, the scan below). Each was
read with its function and surroundings. A table indexed by club
number without such an immediate (pointer arithmetic over a 441-entry
array) doesn't show up this way; see [Still unknown](#still-unknown).

## Not about clubs

About 140 sites use the same numbers for something else:

| Kind | Where |
|---|---|
| object and structure offsets `+0x1b8` | the window and list tasks' `OpenExecute`/`CloseExecute` (vtable entries), `CEditFaceObject`, `WP::CReport`, `CScrollPlate_Task`, `CSelectTeamStyleTask`, `CTrainingTask`, `CTournament…`, `CDetailManager`'s name copies (`+0x1b8`), `MOVIEPRG.REL`, `TESTPRG.REL`'s emblem editors, `GAMEPRG.REL` |
| offsets inside save block 5 | `pwkRec_GetTeamStats` (`+0x601b8`), `pwkRec_GetGameResultSysBuffer` (`+0xb01b8`), `pwkEdit_CallPwkEdit`, the matching `SAVEPRG.REL` serializer sites (`0xdd10`, `0x1d004`, `0x2b088`) |
| screen layout | the detail pages' `SetupDetail…Page` (`$t1` = 442, a coordinate beside 330 or 310) |
| message, event and variable ids | `SIMPRG.REL` `CEventTitle` (24 sites, `$a2` = 442 with ids 8–0x1d), `EVS::CEvsManager::Req` (21 sites, `$a0` = 440), `EVS::SetEventFlag`, `Msg::GetVariableBuffer`, `ROFS_SetIsoDir`, `ImageTransfer::initialize` |
| debug modules | `FC_EURO_DUMMY_MODULE::CPlayerPositionSetAndStamemPointDis` (a counter wrapping at 441), `TESTPRG.REL` `CHayasiTestModule` |

## About clubs

**Confirmed** from the code, by kind:

| Kind | Sites |
|---|---|
| Loops over clubs, to 441 inclusive (`slti …, 0x1ba` or a count of 441) | `pwkOteam_Init` (`0x24a738`, the squads from `OTEAMMEMBER.TBB`), `pwkOteam_Init2` (`0x24a60c`, ranks and world points), `PlBpinfoTask::updatePlCoreInfoSub` (`0x20d314`), `CMakeDataBase::MakeDB` (`0x2230e0`), `GetOfferClub` (`0x225808`, `0x225864`, `0x2258e8`, `0x225974`), `CComOffer::CalcuOfferClub` (`0x22628c`), `CAcquirePlayer::GetExecuteTeamList` (`0x221d94`, `0x221dbc`), `CContractReform::GetExecuteTeamList` (`0x223eb8`), `pwkOteam_ChangeFS_BranchEstablish`/`Remove` (`0x24a8d4`, `0x24a944`), `pwkTeam_UpdatePlayerCandidates` (`0x2607d4`, `0x260830`, `0x2609d0`, `0x260b58`), `pwkTeam_UpdateYouthCandidatesRankSet_ForAbil` (`0x262c20`), `YRSTPRG.REL` `ZinziYearStart::calcYearStartSecondHalf` (`0x17014`, `0x172ac`, `0x1783c`), `CEDITPRG.REL` initial personnel (`0x2d84`) |
| A club is resident (club < 442, or club − 2 < 440) | `pwkOteam_GetOpinfoPointer` (`0x24b930`), `pwkOteam_GetRank` (`0x24bef8`), `pwkOteam_GetWorldClubRank` (`0x24bfa0`), `pwkOteam_GetTeamData` (`0x24bcd4`), `pwkOteam_Init`'s squad set-up (`0x24a788`), `pwkMatchGrow_Grow` (`0x24671c`), `pwkMoney_CalcuPurchaceOtherTeamPlayerTransferMoney` (`0x24829c`), `plTeam_IsPurchaseOKFromCOM` (`0x228c9c`), `CAcquirePlayer::PickupPlayer` (`0x2228b0`), `SetLotClub` (`0x2256c8`), `pwkRental_CheckOpenRentalTeamByFriend`/`ByBranch` (`0x2551b8`, `0x255278`), `pwkTeam_AddReleaseList` (`0x25a8c4`), `CDetailManager::ConvertPlayer_Type` (`0x284dcc`, `0x284e5c`), `SIMPRG.REL` `CPlayerSearchWindow_Task::GetPlayerAcquireCost` (`0x9263c`), `CReport_month` (`0xa1194`, `0xa1244`, `0xa12f0`, `0xa1318`), `ZinziYouthTeam`/`ZinziMyTeam` (`0x15afa4`, `0x15b488`, `0x15bc5c`), `CKeyboard_Task::RecoveryInit` (`0x69924`), `Msg` team-name variables (`0x1706e0`, `0x171f48`, `0x1721f4`) |
| Lists and buffers of 440 or 441 clubs | `plTeam_GetClubrankList` (`0x22c09c`–`0x22c144`: 441 × 8 bytes on a `0xe20` stack frame, sorted with 441), `ScheEuro_TeamEntryList` `getTeamIdFromNation`/`Region` (`0x20afb4`, `0x20b064`: clubs 2–439) and its callers `getList_SRC_KIND_UEFA_XXX`, `_CLUBRANK`, `_FIFA` (`0x20b504`, `0x20b700`, `0x20b880`: 440 entries at `+0x478` of the list) |
| The world ranking | `SIMPRG.REL` `ClubRank` (`0x150684`–`0x1521e0`, 14 sites): its arrays of 441 clubs |
| Save block 2's serializers | `SAVEPRG.REL` `0x29548`, `0x1b844` (patched by `--mod save-expand`), and the older reader's `0xc1d0` (version `0x68` saves only) |
| The non-resident path, for 442–459 | `_pwkOteam_GetPlRec_LgTeamNonresident` (`0x24d65c`), its player base (`0x24d6b0`, `0x24d748`), the league records' set-up `0x24d454` (clubs `0x1ba`–`0x1cb`, players from `0x63f7`), `pwkOteam_ResetRentalPossibleClubFlag` (`0x24ca18`) |
| Not yet understood | `CScheEuro::clearPlayerRecord` and `movePlayerRecord` (`0x2078a0`, `0x207a98`): clubs below 441 skip a player lookup that 441 and up take |

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
| the other clubs, save block 2 | clubs 2–459 with `--mod save-expand` | `pwkOteam_GetPointer` (`0x24b788`) |

So the risk left for a club past 441 is in the buffers and object
arrays the loops above fill: `ClubRank`'s arrays, the club-rank list on
the stack, `ScheEuro_TeamEntryList`'s 440 entries, and the transfer AI's
lists.

## Still unknown

- Tables indexed by club number with no 440–442 immediate: per-club
  arrays in the save blocks (block 5's team records among them) and in
  objects such as `ClubRank`, and the stack and object buffers the loops
  above fill. Each would overflow for a resident club past 441.
- What `clearPlayerRecord` and `movePlayerRecord`'s test of 441 is for.

## Checking

The scan is a short script over `gamever.image` of each file (every
immediate of the six kinds equal to 440–442, with the nearest named
function); `python SRC/sles_disasm.py ISO/SLES_541.51 addr <hex> 20`
shows any site.
