<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Player database (`PARAM/PBDATA_EU.PAC`, `PBDATA_JP.PAC`)

`PBDATA_EU.PAC` holds every real person the game knows: 27,950 players,
3,000 managers and coaches, and 1,000 scouts. That covers names,
nationality, age, height, weight, positions, preferred shirt number, a
required status, personality traits, skills, play styles and 64 ability
ratings per player. The squads in
`OTEAMMEMBER.TBB` ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)) refer to
players by their index here.

`SRC/pbdata.py` reads it. `python SRC/initteam.py squads` uses it to put
names on the squads.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x110d50`, `0x11034c` | `PwkCallbackCommand_BpDataReadFile` and its caller | loads the pack and calls `plBp_Create(work, entry0, entry1, entry2, entry3)` with the four BINPAC entries in order |
| `0x20dd78`, `0x20c5d8` | `plBp_Create`, `PlBpinfoTask::init` | entry 0 is the header, entry 1 the records, entry 2 and entry 3 are kept at `0x390670` / `0x390674`. If the header's first byte is `'0'`, it isn't parsed |
| `0x20da58` | `PlBpinfoTask::initBpmaster` | the header layout below |
| `0x20c700` | `getPbase(id)` | player *id* (0 to count−1) is at `records + id × 98`. It is decoded by `plBits_DecPlPbaseEx`. Ids from `0x7cce` are edit-mode players, held elsewhere |
| `0x20c808` | `getMbase(id)` | ids from `0x6d2e`, at `records + players×98 + (id − 0x6d2e) × 81`, decoded by `plBits_DecPlMbaseEx` |
| `0x20c9b8` | `getSbase(id)` | ids from `0x78e6`, decoded by `plBits_DecPlSbaseEx` |
| `0x20bd28` | `PlBitsClass::readBits(n)` | reads *n* bits, most significant first. Bits are taken from each byte starting at `0x80`, and bytes in order |
| `0x20bdc8` | `PlBitsClass::readBitsStr(buf, n)` | *n* 8-bit characters: the name |
| `0x2e8568` | `plBits_DecPlPbaseEx` | the player fields below, in order. Afterwards it adds 16, 150 and 45 to `+0x28`, `+0x29` and `+0x2a`, replaces `+0x34` with `STATUS[v & 0xf]`, and maps each of the 64 abilities through `0x2e8540` |
| `0x2e8a70` | `plBits_DecPlMbaseEx` | the manager fields. The two groups of 9-bit values are sign-extended from bit 8 into s32 at `+0x4c` and `+0x54` (pointers set up at `0x2e8b64`) |
| `0x2e8ec8` | `plBits_DecPlSbaseEx` | the scout fields. The last 45 of its 49 seven-bit values go through `0x2e8540` |
| `0x2e8540`, `0x55b950` | ability mapping | `ABILITY[min(v, 31)]` with `ABILITY` = 38, 40, … 96, 98, 99 |
| `0x55b970` | status table (required status) | 0, 200, 1000, 3000, 5000, 7500, 10000, 15000, 20000, 25000, 30000, 35000, 40000, 45000, 50000, 55000 |
| `0x2175e0`, `0x2176a8` | `plPinfo_IsForeigner`, `plPinfo_IsEU` | player `+0x14` is the nationality (`PlNati`). Bit 1 of `+0x63` is an EU passport on top of it |
| `0x218748` | `plPinfo_IsSkill` | `+0x64` is a bit mask, one bit per `PlPlayerSkill` |
| `0x20d908` | `getPinfoRank` | for ids ≥ `0x63f7` the rank is `+0x18`. Below that it is 15 − the row of 16 `{first, last}` ranges at `0x5eac08` (filled at run time) that holds entry 3's value for the player |
| `0x20d9a0` | `getPinfoApos0` | the main position is `+0x1c`. For ids below `0x63f7` it is the column of the group table at `0x52fbf8` (row 15 − rank) whose range holds entry 3's value ([Entries 2 and 3](#entries-2-and-3)) |
| `0x20d470` | `PlBpinfoTask::serchPinfo` | searches the ranking: entry 2 (`0x390670`) through the group table at `0x52fbf8` |
| `0x24d450`, `0x24d480`, `0x33c5d8` | `pwkOteam_InitNonresident` modes 0 and 2, `_InitCommon` | the fixed squads of the id blocks ([Player id blocks](#player-id-blocks)) |
| `0x2734c8` | `pwkTeam_SetUnumberOpinfo` | `+0x2b` is the player's preferred shirt number, 1–99 |
| `0x218728` | `plPinfo_IsSkill` (PlPinfo overload) | reads the skills at `PlPinfo +0x1fc`, so the game's copy of the record starts at `PlPinfo +0x198` |
| `0x24d8a8` | `pwkPlayStyle_Init` | `PlPinfo +0x1f6` (record `+0x5e`) holds 5 play styles: it copies the non-zero ones into the style list at `+0x27c`, then adds random styles 1–22 (`slti 0x17`) for the player's position. The first stored style becomes the current one (`+0x278`) |
| `0x289e50`, `0x52f708` | `CDetailManager::AddPlate_PLAYSTYLE`, `Msg::GetString`'s base ids | the current style is drawn as `GetString(5, style)`. Type 5's base id is 150, and types below `0x29` use global slot 0, category 1. So style *n* is message 1:150 + *n* |
| `0x246884` | match growth (in the function before `pwkGUtl_AddExp`'s caller at `0x246930`) | abilities 45–52 (`0x2d` + *k*) gain experience only when *k* is the `system` of the club's current team style (my-team data `+0x4204`); abilities 33–41 only for the player's own position row |
| `0x215a00` | `plMisc_Nati2NatiTeam` | nation → national team: `PLRESOURCECOMMON.PAC` entry 3, table 2, one u16 per nation. `pbdata.py` names nations through it, because the team names are known (message category 3) |

## Entry 0: header (46 bytes)

| Offset | Type | Value | Meaning |
|---|---|---|---|
| `0x00` | char[4] | `1000` | version text. Only checked for a leading `'0'` |
| `0x04` | u32 | 1 | not read |
| `0x08` | u32 × 3 | 27,950 / 3,000 / 1,000 | record counts: players, managers, scouts |
| `0x14` | u32 | 3,058 | stored at `+0x34` of the task. Use not traced |
| `0x18` | u16 (+2) × 3 | 98 / 81 / 71 | record sizes in bytes. Each is followed by `ff ff` |
| `0x24` | u16 | 64 | stored at `+0x50`. Use not traced |
| `0x26` | 8 bytes | `2e 02 26 a5 00 00 30 30` | not read by `initBpmaster` |

27,950 × 98 + 3,000 × 81 + 1,000 × 71 = 3,053,100 bytes, exactly the
size of entry 1 in `PBDATA_EU.PAC`.

## Entry 1: records

Each record starts with a `char[19]` name (cp850, zero-padded), followed
by bit fields read MSB first. The widths, order and destination offsets
are all **confirmed** from the decoders. The destination offset is where
the game keeps the value in memory, and it is also `pbdata.py`'s name for
a field whose meaning is unknown (`f_30`, …). Meanings marked
*empirical* come from the data alone. Player field names from `+0x34` on
are the developers' own labels ([below](#the-developers-player-editor));
**confirmed** on such a row means the game code that reads the field was
also found.

### Players (98 bytes, 779 bits used)

| Bits | × | Offset | Name | Meaning |
|---|---|---|---|---|
| 8 | 1 | `+0x14` | nation | nationality, 1–144. **confirmed** |
| 5 | 1 | `+0x18` | rank | 0–15. **confirmed** (read directly only for ids ≥ `0x63f7`) |
| 4 | 3 | `+0x1c` | position | main and up to two more positions: a cell of the detail screen's pitch grid, 0–12, with 13 meaning none. See [Positions](#positions-and-aptitude). **confirmed** |
| 7 | 1 | `+0x28` | age | stored − 16. *Empirical* meaning: 16–40, and it matches the real players in 2005. Computer-team players don't show this age: their squad slot's age from `OTEAMMEMBER.TBB` is used instead ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)). Tested in game: a database age of 16 didn't change Terry's shown age |
| 8 | 1 | `+0x29` | height | stored − 150, in cm (158–205). *Empirical*. The decoder stores the sum in a byte (`sb` at `0x2e8a14`), so heights above 255 wrap. Tested in game: 313 cm shows as 57 cm |
| 7 | 1 | `+0x2a` | weight | stored − 45, in kg (48–100). *Empirical* |
| 7 | 1 | `+0x2b` | shirt | preferred shirt number. **confirmed** |
| 3 | 1 | `+0x2c` | leg | 0–3. Bit 0 set means right-footed, clear means left. *Empirical*: every well-known left-footer tested (Robben, Ashley Cole, Giggs, Messi, Roberto Carlos, Duff, Cech) has it clear. Bit 1 is set for famously two-footed players (Maldini, Henry, Rooney, Duff), and VPF's Player Edit screen shows Rooney (leg 3) as "Both(R)", so bit 1 is two-footed. The developers' editor names the four values 左, 右, 両左, 両右 (left, right, both-left, both-right). The detail screen shows a message from 100–103 (LEFT, RIGHT, LEFT, RIGHT), which fits `100 + leg`, but the copy into `PlPinfo +0x1c4` hasn't been traced |
| 16 | 1 | `+0x30` | f_30 | always 0 |
| 16 | 1 | `+0x32` | face | face number, 0–17,172. **confirmed**: `CDetailManager` passes it to `CDetailFace::Request` (`0x2869b4`) |
| 16 | 1 | `+0x34` | req_status | required status: band 0–15, looked up in the status table (`0x55b970`). **confirmed**: `pwkTeam_UpdatePlayerCandidates` (`0x260cf8`) leaves a player out of a candidate list when it is above the club's `pwkTeam_Status()`. Managers (`+0x24`) and scouts (`+0x22`) have the same field. Earlier lead: the BPINFO CHECK screen labels the 10,000 cutoff "1mil" ([`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)) |
| 3 | 1 | `+0x36` | tone | speech tone, 0–3. Read by the event code in `SIMPRG.REL`; what each value sounds like isn't traced |
| 2 | 8 | `+0x37` | dissatis | sensitivity to 8 causes of dissatisfaction, 0–3. **confirmed**; see [Personality](#personality-and-condition-fields) |
| 4 | 1 | `+0x3f` | professionalism | picks the starting power range. **confirmed** |
| 4 | 1 | `+0x40` | pressure | pressure resistance. Read by the match engine (`GAMEPRG.REL`), not traced |
| 4 | 1 | `+0x41` | loyalty | club loyalty; sets a promoted youth player's contract years. **confirmed** |
| 4 | 1 | `+0x42` | star | star quality; scales popularity changes. **confirmed** |
| 4 | 4 | `+0x43` | f_43 | no label in the developers' editor. Mostly 0 (15,718, 24,808, 27,428 and 27,917 players) |
| 3 | 1 | `+0x47` | moti_type | motivation type, 0–7. **confirmed** |
| 3 | 1 | `+0x48` | cond_type | condition type, 0–7. No reader found outside the debug and save code |
| 5 | 1 | `+0x49` | potential | 0–7; read by `plPinfo_InitEditAbil` (`0x21b2b8`) |
| 4 | 3 | `+0x4a` | growth | physical, skill and mental growth types, 0–15. **confirmed** (`pwkGUtl_GetPhysical/Skill/MentalGrowCoe`, `0x245ef8`–`0x245f58`) |
| 3 | 1 | `+0x4d` | travel | travel tolerance, 0–7. **confirmed** |
| 3 | 1 | `+0x4e` | injury_res | injury resistance, 0–7. **confirmed** |
| 3 | 1 | `+0x4f` | recovery | recovery, 0–7. **confirmed** |
| 4 | 1 | `+0x50` | foul_avoid | foul avoidance, 0–15. Read by the match engine, not traced |
| 4 | 1 | `+0x51` | weak_foot | weak-foot accuracy, 0–15. Read by the match engine, not traced. 163 of the 499 two-footed players have 8 or more, against 324 of the other 27,451 |
| 5 | 1 | `+0x52` | policy | the player's policy type, 0–24. **confirmed** (`pwkTeamType_PolicyInit` `0x27033c`, also `plCombi_*` and `pwkPromise_*`) |
| 3 | 1 | `+0x53` | adapt | adaptability, 0–6. **confirmed**: `pwkTeamType_GetFit` (`0x270624`) looks it up in a table at `0x3996d8` (30, 33, 35, 38, 40, 45, 50) |
| 4 | 1 | `+0x54` | intelligence | always 0 |
| 2 | 1 | `+0x55` | ball_touch | ball-touch type, 0–2 |
| 2 | 1 | `+0x56` | dribble_style | 0–3 |
| 2 | 1 | `+0x57` | f_57 | always 0; no label |
| 3 | 2 | `+0x58` | f_58 | no label. Read by `pwkDissatis_PlayerResign` and `pwkDissatis_StaffResign` (`0x239a30`, `0x23a018`). 0 in 27,256 and 27,187 players |
| 2, 3, 1, 4 | 1 each | `+0x5a`…`+0x5d` | f_5a…f_5d | no label. Mostly 0; read by the match engine |
| 5 | 5 | `+0x5e` | style | play styles, 1–22, 0 for none. **confirmed**. See [Play styles](#play-styles) |
| 3 | 1 | `+0x63` | flags | bit 1: EU passport. **confirmed**. Set in 19,333 players |
| 16 | 1 | `+0x64` | skills | bit mask. **confirmed**. All 16 bits are used; see [Skills](#skills) |
| 3 | 11 | `+0x66` | f_66 | 0–4. No label. `+0x67` is the row of the affinity table (see [Personality](#personality-and-condition-fields)); the others aren't traced |
| 5 | 64 | `+0x74` | ability | 64 ratings (`PlAbilNo` 0–63), each mapped to 38–99. **confirmed**. See [Abilities](#abilities-and-the-detail-screen) |

The 5 bits after the last field are zero in every record.

### Player id blocks

The last 2,359 player records (25,591–27,949) aren't in any club's
starting squad (`OTEAMMEMBER.TBB`, teams 3–441). **Confirmed:**
`pwkOteam_InitNonresident` (`0x24d568`) gives them to teams through
`_InitCommon(record, first team, last team, first player, last player,
per team)` (`0x33c5d8`). It hands out the ids in order and takes each
player's shirt number from `+0x2b` (or his place in the block if that
is 0):

| Ids | Called from | Teams | What |
|---|---|---|---|
| 25,591–26,040 | mode 0, `0x24d450`, at new-game setup (`0x110ae4`) | 442–459, 25 each | made-up players for the 18 clubs without an `OTEAMMEMBER` squad, three per league nation: England, France, Germany, Italy, Spain, Netherlands (**empirical**: each block of 25 has one nationality). England's first 18 and 16 from 25,623 are the built-in default club ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#without-the-file)) |
| 26,041–27,949 | mode 2, `0x24d480`, from `PwkCallbackCommand_VS_Start` (`0x111478`) | 460–542, 23 each | the national teams' fixed squads, used in **VS mode**. Every block has one nationality |

A national-team record repeats a club player under the same name, as a
separate record: Gianluigi Buffon is 3,175 at Juventus and 26,110 (shirt
1) in Italy's block, John Terry 101 at Chelsea and 26,046 (shirt 6) in
England's. The two can differ (that Terry's height, abilities and age
aren't the club Terry's). The user identified these as national-team
players.

**Tested in PCSX2:** with record 26,046 (England's Terry) renamed
`NT.Terry.VS`, England's starters in a VS match listed DF 6 NT.Terry.VS,
in a 4-4-2 with the rest of the block's names (Robinson, A. Cole,
G. Neville, Ferdinand, Beckham, Gerrard, J. Cole, Wright-Phillips, Owen,
Rooney).

In a career the fixed squads aren't loaded: mode 3 (`0x24d4b0`) only
sets the 83 team numbers, and squads are called up from the club players
([National team call-ups](#national-team-call-ups)). Mode 1 (`0x24d4d8`,
from `PwkCallbackCommand_PromotionEnd`) isn't traced.

### Managers and coaches (81 bytes, 642 bits used)

`char[19]` name, then (bits × count at offset): 8 `+0x14` (nationality,
*empirical*: same range and position as the players'), 5 `+0x18`,
3 `+0x1c` (job, see below), 16 `+0x20`, 6 `+0x22` (age, see below), 16 `+0x24` (required status, **confirmed**
table lookup), 4 ×4 `+0x26`, 2 ×5 `+0x2a`, 3 ×4 `+0x2f`, 2 `+0x33`,
6 `+0x34`, 3 ×8 `+0x35`, 8 ×3 `+0x3d`, 3 ×7 `+0x40`, 5 ×5 `+0x47`,
signed 9 ×2 `+0x4c`, signed 9 ×4 `+0x54`, 1 ×2 `+0x64`, and 48 abilities
(5 bits, mapped to 38–99) at `+0x66`. The 6 bits left over are zero.
The fields from `+0x2f` on are named in
[The developers' staff editors](#the-developers-staff-editors).

### Scouts (71 bytes, 565 bits used)

`char[19]` name, then 8 `+0x14` (nationality, *empirical*), 8 `+0x18`
(age, see below), 5 `+0x1c`, 16 `+0x20`, 16 `+0x22` (required status), 4 ×4 `+0x24`, 1 `+0x28`,
and 49 × 7 bits at `+0x29`. The first 4 are special searches and the last
45 are abilities, clamped to 31 and mapped to 38–99. The 3 bits left over
are zero. See
[The developers' staff editors](#the-developers-staff-editors).

### Staff age

Manager `+0x22` and scout `+0x18` are the age, stored as is (no offset,
unlike the players' `+0x28`). Without `TEAM_INIT_DATA.TBB`,
`pwkTeam_Init2` copies manager byte `0x22` (`0x25eff4`) and scout byte
`0x18` (`0x25f038`) into the slot where the table otherwise puts the
age. Where the table gives it, it equals these fields in all 180 manager
and 108 scout records. **Tested in PCSX2:** the game shows that value as
the staff member's age, in the Coach and Scout Candidate Lists and for
the club's own staff ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md)). Ages
run 35–55 for managers and 35–58 for scouts.

## The developers' player editor

`DEBUGPRG.REL` holds the developers' editors for players, managers and
scouts (`Param::PinfoEditorTask`, `MinfoEditorTask`, `SinfoEditorTask`),
with Japanese (cp932) labels. The retail game never loads this overlay
([`SNR2_FORMAT.md`](SNR2_FORMAT.md)), but its code and labels name most
of the record.

**Abilities (confirmed).** A table at `DEBUGPRG.REL 0x11128` holds 64
pairs `{label, ability number}`, numbers 0–63 in order:

| Ability | Label | | Ability | Label |
|---|---|---|---|---|
| 0 | ドリブルスピード dribble speed | | 32 | 集中力 concentration |
| 1 | ドリブル精度 dribble accuracy | | 33 | GK適正 GK aptitude |
| 2 | シュート精度 shot accuracy | | 34 | SB適正 |
| 3 | シュートテクニック shot technique | | 35 | CB適正 |
| 4 | ショートパス精度 short pass accuracy | | 36 | WB適正 |
| 5 | ロングパス精度 long pass accuracy | | 37 | DM適正 |
| 6 | クロスボール精度 cross accuracy | | 38 | SM適正 |
| 7 | ヘディング精度 heading accuracy | | 39 | OM適正 |
| 8 | トラップ trap | | 40 | WG適正 (wing) |
| 9 | キープ力 ball keeping | | 41 | FW適正 |
| 10 | タックル tackle | | 42 | 中央適正 centre |
| 11 | インターセプト intercept | | 43 | 左サイド適正 left side |
| 12 | ボール奪取 ball winning | | 44 | 右サイド適正 right side |
| 13 | マーキング marking | | 45–52 | 3-4-3 … 5-4-1 理解度 system understanding |
| 14 | プレイスキック精度 placekick accuracy | | 53 | 速攻理解度 counterattack |
| 15 | セービング saving | | 54 | ポゼッション理解度 possession |
| 16 | キャッチング catching | | 55 | サイド攻撃理解度 side attack |
| 17 | ハイボール high balls | | 56 | 中央攻撃理解度 centre attack |
| 18 | 飛び出し rushing out | | 57 | オフサイド理解 offside |
| 19 | スピード speed | | 58 | プレス理解 pressing |
| 20 | ダッシュ dash | | 59–63 | 攻撃パターンA–E理解度 attack patterns A–E |
| 21 | ジャンプ力 jump | | | |
| 22 | レスポンス response | | | |
| 23 | スタミナ stamina | | | |
| 24 | キック力 kick strength | | | |
| 25 | 当たりの強さ contact strength | | | |
| 26 | 統率力 leadership | | | |
| 27 | 度胸 nerve | | | |
| 28 | 攻撃意識 attack minded | | | |
| 29 | 守備意識 defence minded | | | |
| 30 | サポート意識 supportiveness | | | |
| 31 | 視野の広さ vision | | | |

This agrees with every ability the game code names (the bars, the
position grid and the system growth) and with all four VPF players
([Ability names](#ability-names)). The 34–41 labels name the grid cells:
SB/CB, WB/DM, SM/OM and WG/FW are the side and centre of each row. 59–63
are the five attack patterns the tactics screen calls Left Flank, Right
Flank, Centre Drive, Counter Attack and Possession (messages 1:620–649);
which pattern is which letter isn't traced.

**Record fields (confirmed).** The player editor draws each field's label
and then reads that field, a few instructions later, in record order
(`DEBUGPRG.REL 0x5ad0`–`0x60a8`): 利き足 leg `+0x2c`, 身長 height, 体重
weight, 基本背番号 shirt, 得意ポジション position, 必要ステータス
required status `+0x34`, 口調 speech tone `+0x36`, プロフェッショナル意識
professionalism `+0x3f`, プレッシャー耐性 pressure resistance `+0x40`,
クラブ忠誠心 club loyalty `+0x41`, スター性 star quality `+0x42`,
モチベーションタイプ motivation type `+0x47`, コンディションタイプ
condition type `+0x48`, 将来性 potential `+0x49`, フィジカル/スキル/精神成長タイプ
growth types `+0x4a`–`+0x4c`, 移動耐性 travel tolerance `+0x4d`,
怪我の少なさ injury resistance `+0x4e`, 回復力 recovery `+0x4f`,
ファールしにくさ foul avoidance `+0x50`, 逆足精度 weak-foot accuracy
`+0x51`, ポリシー policy `+0x52`, 環境適応度 adaptability `+0x53`,
インテリジェンス intelligence `+0x54`, ボールタッチタイプ ball-touch type
`+0x55`, ドリブルスタイル dribble style `+0x56`, 固有プレイスタイル native
play styles `+0x5e`. The manager and scout editors read their `+0x24`
and `+0x22` under 必要ステータス too.

The editor has no label for `+0x30`, `+0x37` (shown on its dissatisfaction
page), `+0x43`–`+0x46`, `+0x57`–`+0x5d` or `+0x66`–`+0x70`.

## The developers' staff editors

The manager editor (`MinfoEditorTask`, title 監督エディット) and the scout
editor (`SinfoEditorTask`, スカウトエディット) work like the player editor:
each page draws a label and then reads the field. Both take a `PlMinfo` or
`PlSinfo` (`+0x910` and `+0x3ac` of the task), which is 4 bytes and then
the record (`PlMbase` / `PlSbase`). Offsets below are record offsets.

**Manager abilities (confirmed).** The table at `DEBUGPRG.REL 0x103d8`
holds 48 pairs `{label, ability number}`, numbers 0–47 in order. Nearly
all labels end in 指導力 "coaching ability", left out below:

| Ability | Label | | Ability | Label |
|---|---|---|---|---|
| 0 | モチベーションケア能力 motivation care | | 24 | DF |
| 1 | フィジカルケア能力 physical care | | 25 | DM |
| 2 | 人望 respect | | 26 | OM |
| 3 | 不満ケア能力 dissatisfaction care | | 27 | FW |
| 4 | 選手目利き力 judging players | | 28 | 中央適正 centre aptitude |
| 5 | 能力開発 ability development | | 29 | 左サイド適正 left side aptitude |
| 6 | ユース選手 youth players | | 30 | 右サイド適正 right side aptitude |
| 7 | 若手選手 young players | | 31–38 | 3-4-3 … 5-4-1 (the 8 systems) |
| 8 | 中堅選手 mid-career players | | 39 | 速攻 counter attack |
| 9 | ベテラン選手 veterans | | 40 | ポゼッション possession |
| 10 | ドリブル dribble | | 41 | サイド攻撃 side attack |
| 11 | シュート shot | | 42 | 中央攻撃 centre attack |
| 12 | パス pass | | 43 | オフサイド offside |
| 13 | ヘディング heading | | 44 | プレス pressing |
| 14 | インターセプト intercept | | 45 | 攻撃パターン attack patterns |
| 15 | マーキング marking | | 46 | 連携 teamwork |
| 16 | セービング saving | | 47 | セットプレイ set plays |
| 17 | 飛び出し rushing out | | | |
| 18 | スピード speed | | | |
| 19 | スタミナ stamina | | | |
| 20 | フィジカル physical | | | |
| 21 | メンタル mental | | | |
| 22 | 攻守意識 attack/defence awareness | | | |
| 23 | GK | | | |

All 31 abilities behind the manager and coach bars
([Manager, coach and scout bars](#manager-coach-and-scout-bars)) agree with
these labels: MOTIV 0, PHYSC 1, POPUL 2, COMMU 3, ASSES 4, TRAIN 5, DRIBB
10 … MARK 15, SAVIN 16, HND 17 (rushing out), SPEED 18 … MENTA 21, ATKDF
22, CENTA 28, FLANK 29/30, FASTB 39 … CLOSD 44, ATTST 45, TEAMW 46, FK 47.

**Coach type (confirmed).** The editor prints the job (`PlMinfo +0xa0`,
from record `+0x1c`) under コーチタイプ "coach type", through the list at
`0x10940`:

| Job | Label |
|---|---|
| 0 | アシスタントバランス balanced assistant |
| 1 | アシスタント攻撃 attacking assistant |
| 2 | アシスタント守備 defensive assistant |
| 3 | フィジカルコーチ physical coach |
| 4 | GKコーチ GK coach |
| 5 | 監督 manager |
| 6 | ユース監督 youth manager |

This matches what the game does with the jobs (5 and 6 are set at run time,
0–2 share the coaching bars) and the job averages below.

**Manager fields (confirmed).** The page drawn at `DEBUGPRG.REL
0x1c98`–`0x1f2c` and the two after it (`0x1f30`–`0x2214`) read these
fields. The first page (`0x1560`–`0x1c94`) shows only run-time state
(popularity, promises, age, contract, salary):

| Offset | Bits | Label | Values in the database |
|---|---|---|---|
| `+0x24` | 16 | 必要ステータス required status | (as before) |
| `+0x2f` | 3 | モチベーションタイプ motivation type | 0–7 |
| `+0x30` | 3 | 選手起用方針 player selection policy | 0–7 |
| `+0x31` | 3 | 試合進行方針 match policy | 0–7 |
| `+0x32` | 3 | 育成方針 training policy | 0–7 |
| `+0x33` | 2 | 休養方針 rest policy | 0–3 |
| `+0x34` | 6 | ポリシー policy | 0–24 |
| `+0x35` | 3 ×4 | 許容範囲 accepted range | 1–7 |
| `+0x39` | 3 ×4 | 得意範囲 best range | 2–7 |
| `+0x3d` | 8 ×3 | フォーメーション formations | 0–34, list at `0x10868` |
| `+0x40` | 3 | 攻撃志向 attacking | 1–5 |
| `+0x41` | 3 | ポゼッション志向 possession | 1–5 |
| `+0x42` | 3 | 攻撃展開中央サイド attack through centre or sides | 1–5 |
| `+0x43` | 3 | 攻撃展開左右 attack left or right | 1–5 |
| `+0x44` | 3 | プレス開始位置 where pressing starts | 1–5 |
| `+0x45` | 3 | プレス強度 pressing strength | 1–5 |
| `+0x46` | 3 | オフサイド強度 offside trap strength | 1–5 |
| `+0x47` | 5 ×5 | 監督攻撃パターンセット attack pattern set | 0–30, list at `0x107e8` |
| `+0x4c` | 9 ×2 | 監督指導可能練習 drills he can teach as manager | all −1 (none) |
| `+0x54` | 9 ×4 | コーチ指導可能練習 drills he can teach as coach | 52–138 or −1 |
| `+0x64` | 1 | 実名？ real name? (Yes/No) | all 0 |
| `+0x65` | 1 | モデルパターン model pattern | 0 (1,526), 1 (1,474) |

The affinity reader confirms `+0x2f` as well: `pwkDissatis_GetAffintyType`
takes a manager's column from `PlMinfo +0x33`. The editor prints the
accepted and best ranges as `%d %d %d %d`, so they are 4 values each; how
they bound the policy isn't traced. The player editor's policy page draws
カウンター～ポゼッション "counter to possession" and タレント～チーム
"talent to team", which are probably the two axes.

The lists the indices go into (**confirmed**, the editor prints the entry):

- Attack patterns, `0x107e8`: 0 なし none, then 6 each of `LS00`–`LS05`,
  `RS`, `CT`, `CA`, `PO` (labels like `LS00_00`). The letters fit the
  tactics screen's five kinds: left flank, right flank, centre, counter
  attack and possession. In the database, slots 0–2 are always set and 3
  and 4 are often 0 (601 and 2,153 managers).
- Formations, `0x10868`: 35 labels such as `4-4-2 dv 3` and `4-3-3 tv 1`,
  grouped by system 3-4-3 … 5-4-1. Entry 34 repeats entry 31's label
  (`5-3-2 tv 1`), probably a slip for 5-4-1.
- Drills, `0x105b8`: 139 training menu items: 0–7 the systems, 8–28 team
  training, 29–31 growth policies (長所を伸ばす, 平均的に, 短所を補足),
  32–51 forward, defender, goalkeeper, physical and mental training,
  52–73 play styles, 74–138 individual drills (シュート, 1000本セーブ, 呼吸法 …). The
  database's coaches use only 52–138.

**Scout abilities (confirmed).** The table at `0x13240` pairs 45 labels
with numbers 4–48, the index into the 49 seven-bit values at `+0x29`. So
scout ability *n* is value *n* + 4:

| Ability | Label | Ability | Label |
|---|---|---|---|
| 0 | クラブ交渉能力 club negotiation | 8–20 | GK, LSB, RSB, CB, LWB, RWB, DM, LSM, RSM, OM, LWG, RWG, FW |
| 1 | 選手交渉能力 player negotiation | 21 | MC (managers) |
| 2 | 金銭交渉能力 money negotiation | 22 | AC (assistant coaches) |
| 3 | 現役選手探索能力 search: professionals | 23 | PC (physical coaches) |
| 4 | ユース探索能力 search: youth | 24 | GC (GK coaches) |
| 5 | 新人探索能力 search: newcomers | 25 | YM (youth managers) |
| 6 | 中堅探索能力 search: mid-career | 26–31 | England, France, Germany, Italy, Spain, Netherlands |
| 7 | ベテラン探索能力 search: veterans | 32–44 | Western, Central, Eastern, Northern Europe, South America A, B, North, West, East and South Africa, North/Central America and Caribbean, East Asia, South Asia and Middle East, Oceania |

The labels of 8–44 end in `SAbil`. The 11 scout bars agree (CLB 0 …
VETER 7, MANAG 21 … GCOAC 24), and the 12th, unlabelled value the screen
computes is 25, youth managers. **Empirical** check: for each of the 14
most common nationalities, the scouts' best region on average is their
own (England 85 against 60 for the other regions, Brazil South America A,
Argentina South America B, Japan East Asia, Scotland, Belgium and
Portugal Western Europe).

**Scout fields (confirmed).** The editor (`0x97a0`–`0x98b0`) reads 実名？
real name? at `+0x28` (all 0 in the database) and 必要ステータス at
`+0x22`. Under 特殊検索 "special search" it loops over `+0x29`–`+0x2c`
and prints each value below 36 from the list at `0x13428`, or なし. These
36 are play-style types: Centre Forward, Moving, Post Player, Attacker,
Dynamo, Crusher, Covering, Central MF, Side Attacker, Cut-in, Defensive
Side, Sweeper, Libero, Stopper, Centre Back, Orthodox, Libero GK,
Playmaker, Second Striker, Operaio, Shadow Striker, Wing, Estremo, Dash
Out, Last Fort, High Tower, Attacking GK, Ace Striker, Crosser, Speed
Star, Line Conductor, All-rounder, Ace Killer, Wall, Super Dribbler,
Regista. In the database the first search is always set (0–35), and 322,
579 and 816 scouts have none (36) in the other three.

**Not labelled by either editor:** manager `+0x18` (0–15), `+0x20`,
`+0x26` (always 0) and `+0x2a`–`+0x2e` (0–3 each), and scout `+0x1c`
(0–15), `+0x20` and `+0x24` (always 0). **Empirical:** `+0x20` is a serial
number, 17,173–20,172 for the 3,000 managers in order and 20,173–21,172
for the 1,000 scouts, as if it continued a count that starts below them.
The players' `+0x30` is 0 in every record.

## Personality and condition fields

**Confirmed from the readers in `SLES_541.51`** (each reads the field at
`PlPinfo +0x198` + its record offset):

| Field | Reader | What the value does |
|---|---|---|
| `dissatis` `+0x37`–`+0x3e` | `pwkDissatis_Money`, `_Player`, `_Staff`, `_Position`, `_Match`, `_Policy`, `_CompeEnd`, `_Facility` (`0x237420`, `0x2376a8`, `0x237af8`, `0x237fbc`, `0x238350`, `0x238558`, `0x23a930`, `0x238a84`) | each scales that cause of dissatisfaction by 1.0, 1.1, 1.2 or 1.3 (tables such as `0x391150`) |
| `professionalism` `+0x3f` | `plPinfo_InitPower` (`0x21af98`) | power (`+0x24c`, 0–1000) starts at a random value in a range from the table at `0x532a38`: 800–900 for 0, rising to 980–1000 for 15 |
| `loyalty` `+0x41` | `pwkTeam_GetYouthPromoteConyear` (`0x2714cc`) | value / 2 picks the row for a promoted youth player's contract years |
| `star` `+0x42` | `plPinfo_GameCheck`, `MonthEndCheck`, `YearEndCheck`, `ClubTitleCheck`, `UpDownKeymanCaptaion` | added to the rank, capped at 30, picks the size of each popularity change (`plPinfo_ChangePop`) |
| `moti_type` `+0x47` | `plPinfo_CalcMotiYear` (`0x21bfe4`) | yearly motivation gain from the table at `0x390860`: 3000, 4500, 1500, 4500, 1500, 1500, 3000, 4500 |
| `moti_type`, `f_66` `+0x67` | `pwkDissatis_GetAffintyType` (`0x2370d0`) | how two people get on: an 8 × 8 table of u16 at `0x390fd0`, row = one person's `+0x67`, column = the other's `+0x47` (a manager's comes from his `PlMbase +0x2f`). Values 0–4 |
| `travel` `+0x4d` | `plPinfo_CalcMatchMovePowerDecline` (`0x2197dc`) | with the age, the power lost to travelling for a match (the effect is read from the function's name) |
| `injury_res` `+0x4e` | `plPinfo_CheckKega` (`0x21aa64`) | with the age, fatigue, power and motivation, the injury check |
| `recovery` `+0x4f` | `plPinfo_CalcGTired`, `CalcPracTired`, `CalcRecover` | picks a pair of multipliers from `0x532870`: (1.1, 0.9), (1.1, 1.0), (1.0, 0.9), (1.0, 1.0), (1.0, 1.1), (0.9, 0.9), (0.9, 1.0), (0.7, 0.9) |

The match engine (`GAMEPRG.REL`) reads `+0x3f`–`+0x5d` as well; that
code isn't traced, so what pressure resistance, foul avoidance, weak-foot
accuracy, ball-touch type and dribble style do on the pitch is open.

```bash
python SRC/pbdata.py show DAT/PARAM/PBDATA_EU.PAC 4408     # Beckham: every field by name
python SRC/snr2.py dis ISO/DLL/DEBUGPRG.REL 0x5ad0 400 --sles ISO/SLES_541.51
```

## Abilities and the detail screen

The 64 player abilities are finer-grained than anything the game shows.
The detail screen's 14 bars and the 6-axis "Evaluation" hexagon are
worked out from them.

**Groups (confirmed, `plPinfo_Abil2PSM` `0x216f10`).** Abilities 0–18
return 1, 19–25 return 0, and 26–63 return 2. `plPinfo_InitAbil`
(`0x21b470`) uses the group to pick which growth byte (`+0x4a`, `+0x4b`,
`+0x4c`) scales an ability's random start offset. From the bars below,
0–18 are skills, 19–25 physical and 26–63 mental, which fits the name
(P/S/M).

**Bars (confirmed, `WP::CDetailManager::ConvertPlayer_Bar` `0x285380`).**
Each bar is the integer average of the listed abilities' levels, and it
is drawn as `(value + 10) / 99` of full width. The labels are detail
messages `0x2774`+. The last 7 bars depend on whether the player's main
position (`PlPinfo +4`) is 0, the goalkeeper:

| Bar | Abilities | | Field bar | Abilities | | GK bar | Abilities |
|---|---|---|---|---|---|---|---|
| SPEED | 0, 20, 22 | | DRIBB | 0, 1 | | SAVIN | 15 |
| PHYSI | 24, 25 | | SHOT | 2, 3, 24 | | HANDL | 16 |
| STAMI | 23 | | PASS | 4, 5, 6 | | CROSS | 17 |
| MENTA | 26, 27 | | FK | 14 | | GO FW | 18 |
| SUPPO | 30, 31 | | HEAD | 7, 25, 21 | | DISTR | 4, 5, 24 |
| SYSTE | 0–7 | | INTER | 11 | | AGILI | 22 |
| TACTI | 0–10 | | MARK | 13 | | JUMP | 21 |

Only abilities 0–32 feed the bars. Where a bar has a single source, it
names that ability: 11 intercept, 13 marking, 14 free kick, 15 saving,
16 handling, 17 crosses, 18 going out, 21 jumping, 22 agility, 23
stamina. The labels SYSTE and TACTI (messages 200:10105/10106, "SYS" and
"TAC" in Japanese) suggest the systems and tactics (45–52 and 53–63, see
[Ability names](#ability-names)), but the code averages abilities 0–7 and
0–10. A check with
well-known players fits (database values, before the random start
offset): Terry has MARK 98, INTER 94 and HEAD 92, Pirlo has PASS 93 and
FK 94, Henry has SPEED 94 and DRIBB 95, and Cech and Buffon have SAVIN 98.

**Hexagon (confirmed computation, `plPinfo_CalcHexagon` `0x217ce0`,
`plPinfo_CalcHexAbil` `0x217850`).** `PLRESOURCECOMMON.PAC` entry 2,
table 0 has 8 bytes per ability. Each 4-byte half holds two
`{u8 hexagon, u8 weight}` pairs: `+4` is the field-player variant, and
`+0` is the goalkeeper variant. Hexagon *h* is the weighted average of
every ability with a pair naming *h*. `CalcHexagonNG` fills all six from
the field variant, then `CalcHexagon` recomputes 0 and 1 with the
goalkeeper variant for goalkeepers. The screen's labels are messages
670–675 of category 1 (Attacking, Physical, Teamwork, Defence, Attitude,
Skills, clockwise from the top). Which index goes to which label is
**empirical**. Hexagons 0 and 3 are told apart by Virtua Pro Football's
categories ([Ability names](#ability-names)): 0's main abilities are its
"Attack" page, and 3's are its "Skill" page.

| Hexagon | Main abilities (weight 80) | Label |
|---|---|---|
| 0 | 2, 4–7, 14 (shot skill, passes, cross, header, placekick) | Attacking |
| 1 | 10–13 (15–18 for goalkeepers) | Defence (defenders score ~90) |
| 2 | 33, 42–44 (60), 53–58 | Teamwork |
| 3 | 1, 3, 8, 9 (dribble skill, shot technique, trap, ball keeping) | Skills |
| 4 | 0, 19–25 | Physical |
| 5 | 26–32 | Attitude |

`python SRC/pbdata.py show` prints both the bars and the hexagon, and
`csv` adds the bars as columns.

### Ability names

The developers' label table ([above](#the-developers-player-editor))
names all 64 abilities. This section is the independent check that came
first: Virtua Pro Football's English names and values. `pbdata.py` uses
VPF's English name where VPF has the same parameter.

Virtua Pro Football (VPF) runs on the same engine, and its Player Edit
screen names its parameters on 8 pages. The user supplied screenshots of
that screen for four players in this database: Maik Taylor (player 0, a
goalkeeper), Wayne Rooney (258, a forward), David Beckham (4408, a right
midfielder), and Lucio (2102, a defender; Physical page only). VPF's pages
follow this game's ability order, and most values match within a point
or two. VPF has parameters this game lacks (cross technique, 1 on 1
response, balance and some tactical ones), so the lists are aligned by
value, not by position.

The values column gives this game / VPF, for Taylor (T), Rooney (R) and
Beckham (B). The evidence column says where each name comes from:
**code** (the bars, the position grid or match growth above), **VPF +
data** (VPF's name, and the players' values or a trend across the whole
database fit), or **VPF** (VPF's name, with the values as shown).

| Ability | Name | Values T, R, B | Evidence |
|---|---|---|---|
| 0 | dribble pace | 38/31, 88/92, 76/72 | VPF + data (SPEED and DRIBB bars) |
| 1 | dribble skill | 38/38, 90/90, 78/77 | VPF + data (DRIBB bar) |
| 2 | shot skill | 38/35, 86/91, 84/83 | VPF + data (SHOT bar) |
| 3 | shot technique | 38/35, 88/87, 82/81 | VPF + data (SHOT bar). VPF's "Skill" page |
| 4 | short pass | 54/54, 84/83, 86/85 | VPF + data (PASS bar) |
| 5 | long pass | 64/63, 82/81, 98/99 | VPF + data (PASS bar) |
| 6 | cross | 40/39, 80/80, 99/99 | VPF + data (PASS bar) |
| 7 | header | 38/35, 82/82, 70/70 | VPF + data (HEAD bar) |
| 8 | trap | 60/55, 88/88, 84/80 | VPF + data. VPF's "Skill" page |
| 9 | ball keeping | 38/36, 82/82, 74/73 | VPF + data. VPF's "Skill" page |
| 10 | tackle | 48/48, 66/65, 70/70 | VPF + data |
| 11 | intercept | 38/38, 46/46, 70/69 | code (INTER bar) |
| 12 | ball winning | 38/37, 48/48, 72/72 | VPF + data |
| 13 | marking | 38/35, 50/49, 76/76 | code (MARK bar) |
| 14 | placekick | 52/51, 80/80, 99/99 | code (FK bar) |
| 15–18 | saving, catching, aerial ability, rushing out | 78/77, 78/77, 82/81, 78/78 for T | code (goalkeeper bars SAVIN, HANDL, CROSS, GO FW) |
| 19 | pace | 74/70, 86/94, 80/76; Lucio 80/82 | VPF + data. Lucio settles the pair: VPF gives him pace 82 and acceleration 71 |
| 20 | acceleration | 74/69, 92/94, 78/74; Lucio 76/71 | VPF + data |
| 21–23 | jump, agility, stamina | 76/71, 88/83, 62/57 for T; 82/82, 88/88, 84/84 for Lucio | code (JUMP, AGILI, STAMI bars) |
| 24 | kick strength | 74/73, 88/88, 86/86 | VPF + data (SHOT and DISTR bars) |
| 25 | contact strength | 80/80, 90/91, 80/80 | VPF + data (PHYSI and HEAD bars) |
| 26 | leadership | 40/40, 70/70, 90/90 | VPF + data (MENTA bar) |
| 27 | nerve | 40/51, 94/45, 94/66 | developer label 度胸. VPF's "consistency" sits in this slot, but the values don't fit (MENTA bar) |
| 28 | attack minded | 52/51, 96/96, 94/93 | VPF + data: averages 45 for goalkeepers, 80 for forwards |
| 29 | defence minded | 84/84, 54/70, 72/72 | VPF + data: averages 80 for goalkeepers, 45 for forwards |
| 30 | supportiveness | 40/40, 88/79, 90/89 | VPF + data (SUPPO bar) |
| 31 | vision | 60/59, 76/75, 99/99 | VPF + data (SUPPO bar) |
| 32 | concentration | T 78, R 72, B 86 | developer label 集中力; no VPF counterpart (Attitude hexagon) |
| 33–44 | position aptitudes | see below | code ([Positions](#positions-and-aptitude)) |
| 45–52 | fit with systems 3-4-3, 3-5-2, 3-6-1, 4-3-3, 4-4-2, 4-5-1, 5-3-2, 5-4-1 | | code for "system *k*" (match growth); the order of the systems is empirical: the formation names (messages 801:0–7, 1:530–537) and their descriptions (700:270–293) are listed in this order |
| 53 | counterattack | 82/82, 88/87, 82/81 | VPF + data |
| 54 | possession | T 42, R 88, B 46 | developer label ポゼッション理解度; no VPF counterpart (Teamwork hexagon) |
| 55 | attacks down wings | 80/79, 62/78, 40/39 | VPF + data (Rooney is the one outlier) |
| 56 | attacks through middle | 38/34, 86/86, 56/55 | VPF + data |
| 57 | line DF | 64/64, 58/57, 64/63 | VPF + data. Beckham settles the pair (line DF 63, pressing 59) |
| 58 | pressing | 68/68, 58/57, 60/59 | VPF + data |
| 59–63 | attack patterns A–E | | developer labels 攻撃パターンA–E理解度; 60 is in the Teamwork hexagon |

VPF's aptitude page names the position cells. Rooney and Beckham agree
on 39 = OM (86/85, 72/70), 42 = centre (94/93, 88/87), 43 = left (82/82,
54/53) and 44 = right (54/53, 98/97), and Beckham has 38 = SM (96/95).
Rooney also fits 34 = SB (40/39), 35 = CB (44/44), 36 = WB (46/46) and
41 = FW (96/95). Taylor has 33 = GK (82/82). The defensive cells don't fit
Beckham, whose VPF values there are a flat 48 (56, 70, 76 and 92 here
for SB, CB, WB and DM). 40, the forward line's sides, has no VPF
counterpart.

Across the database, abilities 26, 27, 32 and 45–63 average 51 for every
position and play style. They are only higher across the board for
stronger players (about 62 for the holders of any skill), which suggests
filler values. That is why those names rest on the VPF players.

## Skills

`+0x64` holds one bit per `PlPlayerSkill` (`plPinfo_IsSkill`, `0x218748`).
Bit *n* is described by message 6000 + *n* of category 2000. The short
labels are summaries of those texts, as `pbdata.py` prints them:

| Bit | Label | Description (message 2000:6000 + bit) | VPF name |
|---|---|---|---|
| 0 | covering | superb covering, bails the team out | Covering |
| 1 | offside line | holds the defensive line, works the offside trap | Line Control |
| 2 | penalty taker | superb penalty taker | PK Taker |
| 3 | penalty stopper | puts pressure on the penalty taker (a keeper) | PK Goal Keeper |
| 4 | one-on-one finisher | cool in one-on-ones with the keeper | Shot on 1 on 1 |
| 5 | one-on-one keeper | saves one-on-ones | GK on 1 on 1 |
| 6 | long throw | very long throw-ins | Long Throw |
| 7 | super sub | swings a match when brought on | Super Sub |
| 8 | through balls | vision for through balls | Ball Feeding |
| 9 | positioning | exquisite positioning | Positioning |
| 10 | reflex saves | miraculous reactions | Fine Saving |
| 11 | acrobatic shot | shoots even off balance | Acrobatic Play |
| 12 | one-touch shot | one-touch finishing | Volleys |
| 13 | goal machine | pin-point shooting | Controlled Shot |
| 14 | poacher | pounces on loose balls in the box | Good Positioning |
| 15 | playmaker | leads the team with killer passes | Through Ball |

VPF's Special Skill page lists its 16 skills in this order, and each
name fits the description of the same bit, which backs up the bit order.
VPF marks Rooney with Shot on 1 on 1, Acrobatic Play and Controlled
Shot, and his `+0x64` has exactly bits 4, 11 and 13. Beckham's PK Taker,
Ball Feeding and Controlled Shot are exactly his bits 2, 8 and 13.

That bit *n* goes with message 6000 + *n* is **empirical**, from who holds
which bit. Of 2,465 goalkeepers, 90, 91 and 86 hold bits 3, 5 and 10, and
of 14,395 defenders and forwards only 1 holds any of the three. Bits 0 and
1 go mostly to defenders (237 of 238), and bits 2, 4 and 11–14 mostly to
forwards. The code confirms one: the substitutions screen tests bit 7, the
super sub (`CTacticsMenuSubstitutionsImplement::Update_MessDisplay`,
`0x2f6558`). What the skills do in a match isn't traced.

## Play styles

**Confirmed (`pwkPlayStyle_Init` `0x24d8a8`, `AddPlate_PLAYSTYLE`
`0x289e50`).** `+0x5e` holds up to 5 play styles, 1–22, with 0 for an
empty slot. When a player is set up, the game lists the stored styles,
then adds random ones that suit the player's position until the
position's count (table at `0x398e98`) is reached. The first stored
style is the one the detail screen shows. Style *n* is named by message
1:150 + *n*:

| Style | Name (message 1:150 + n) | VPF name | Players |
|---|---|---|---|
| 1 | Centre Forward | Centre Forward | forwards |
| 2 | Moving | Moving | forwards |
| 3 | Postplayer | Target man | forwards (Crouch) |
| 4 | Dash out | Darting run | forwards (Inzaghi, Shevchenko) |
| 5 | Second Striker | Second Attacker | forwards (Totti, Del Piero) |
| 6 | Wing | Wings | forwards and attacking midfielders |
| 7 | Play maker | Playmaker | midfielders (Pirlo, Zidane) |
| 8 | Shadow striker | Shadow Striker | midfielders (Lampard) |
| 9 | Attacker | Attacker | attacking midfielders (Robben, Ronaldinho) |
| 10 | Dynamo | Dynamo | midfielders (Gattuso, Vieira) |
| 11 | Man marker | Hard Marker | defensive midfielders (Makelele, Gattuso) |
| 12 | Covering | Anchor | defensive midfielders (Makelele) |
| 13 | Centre MF | Central Midfielder | midfielders (Lampard, Beckham) |
| 14 | Winger | Side Attacker | wide players (Beckham, Roberto Carlos) |
| 15 | Threaten to cut in | Wing Forward | wide players (Henry, Cafu) |
| 16 | Full back | Wing half | full-backs (Cafu) |
| 17 | Sweeper | Sweeper | defenders |
| 18 | Defensive Sweeper | Libero | defenders |
| 19 | Stopper | Stopper | defenders (Puyol, Nesta) |
| 20 | CB | Centre Back | defenders (Puyol, Nesta) |
| 21 | GK | Orthodox | goalkeepers only (Cech, Lehmann) |
| 22 | Attacking GK | Libero GK | goalkeepers only (Buffon, Barthez) |

Across the database (**empirical**), 19,403 players have at least one
style. Styles 21 and 22 are held only by goalkeepers (841 and 220), and
1–5 almost only by forwards. VPF shows its 22 styles in the same order,
each with a rating. This game stores only which styles a player has.
Beckham's three styles here (14, 13, 7) are his three best in VPF (Side
Attacker 80, Central Midfielder 70, Playmaker 92); Rooney's 2 and 5 are
his two best (Moving 87, Second Attacker 85), but his 9 (Attacker) is 48
there. The style names were already checked in game through a save
([`SAVE_FORMAT.md`](SAVE_FORMAT.md)).

**Tested in PCSX2:** John Terry (101) has styles 20, 19, 18 (CB,
Stopper, Defensive Sweeper). `pbdata.py set ... 101 style.0=7` makes them
7, 19, 18. On a disc patched with `patch_disc.py` (with
`--skip-tutorial`), his detail screen in a new career showed "Play maker"
on its STYLE line, with three style icons. So the first stored style is
the one shown, and the database value reaches the game unchanged.

## Positions and aptitude

**Confirmed, `plPinfo_CalcAptPos` (`0x217f70`),
`plPinfo_GetPositionFitValue` (`0x217e48`), and the table at `0x532610`.**
The detail screen's pitch grid has 13 cells, and they are the 13
position numbers. For each cell, the game computes a fit value, a
weighted sum of up to four abilities:

| Cell | Name | Fit |
|---|---|---|
| 0 | GK | 33 |
| 1, 2, 3 | DF left, right, centre | 0.7 × 34 + 0.3 × 43 (left) or 44 (right); centre 0.7 × 35 + 0.2 × 42 + 0.05 × (43 + 44) |
| 4, 5, 6 | DM left, right, centre | the same with 36 (sides) and 37 (centre) |
| 7, 8, 9 | AM left, right, centre | 38 and 39 |
| 10, 11, 12 | FW left, right, centre | 40 and 41 |

So abilities 33–44 are position aptitudes: 33 goalkeeper, 34–41 each
row's sides and centre, and 42/43/44 a leaning to the centre, the left
and the right. The rows go from the goal upwards. The names DF/DM/AM/FW
are descriptive, not the game's. Which of 43 and 44 is the left is
**empirical**: players who play on the left (Robben, Edu) are higher in
43, and Tevez's top-right cell lights up with 44 = 88.

Each cell's fit is converted to a level from 0 to 4 against the
player's best cell, using the table at `0x5327b0`. A cell gets level
4, 3, 2 or 1 for the first row where fit ≥ 70/60/50/40 **and** either
fit ≥ 1.0/0.95/0.9/0.8 × best, or fit ≥ 80/70/60/50. Then each listed
position (`+0x1c`, up to three) gets +1, up to 4.

**Tested in the game:** Terry with abilities alternating 38 and 99 has
99 in 33, 35, 37, 39 and 41. His grid lit the goalkeeper box and the
whole centre column, as the formula predicts. The vanilla Terry's grid
(his centre-back cell, the centre cell in front of it and one side cell)
also matches the computed levels. His two side cells score 66 and 68,
just under the level-3 threshold, and the game's random start offset
(`plPinfo_InitAbil`) can push one of them over. Which levels the screen
draws, and in which colour, hasn't been traced.

`python SRC/pbdata.py show` prints the grid (forwards at the top), and
`list` names the positions.

### Manager, coach and scout bars

**Confirmed, `WP::CDetailManager::CalcManagerAbil` (`0x286cd0`).**
`PlMinfo` is 4 bytes followed by the `PlMbase` (`plMinfo_InitDb`
`0x2e9720` copies it to `+4`), so `PlMinfo +0x6a` is ability 0 and
`+0xa0` is the job at `PlMbase +0x1c`. Every manager and coach screen has
12 shared bars, then a set picked by the job through the jump table at
`0x557630`. All are single abilities except FLANK:

| Bar | Ability | Bar | Ability | Job | Extra bars (abilities) |
|---|---|---|---|---|---|
| ATTST | 45 | FLANK | avg 29, 30 | 0, 1, 2 | DRIBB 10, SHOT 11, PASS 12, HEAD 13, INTER 14, MARK 15 |
| TEAMW | 46 | MOTIV | 0 | 3 | SPEED 18, PHYSI 20, STAMI 19, MENTA 21 |
| FK | 47 | PHYSC | 1 | 4 | SAVIN 16, HND 17 |
| TRAIN | 5 | COMMU | 3 | 5+ | FASTB 39, SLOWB 40, WINGP 41, DIREC 42, OFFSI 43, CLOSD 44 |
| ATKDF | 22 | POPUL | 2 | | |
| CENTA | 28 | ASSES | 4 | | |

The labels match the in-game help pages: 0–2 are assistant coaches, 3
physical coaches, 4 goalkeeper coaches. The database holds jobs 0 (439),
1 (786), 2 (714), 3 (678) and 4 (383), and no 5. A staff member hired as
manager gets the job-5 bars. In a save, C. Collin (job 0 in the
database) shows the manager bars, and they match abilities 39–44. So the
job is changed at run time. The shared bars for Collin and M. Boismortier
match their detail screens exactly.

**What the jobs are.** The developers' manager editor names them
(**confirmed**, see
[The developers' staff editors](#the-developers-staff-editors)): 0
balanced, 1 attacking and 2 defensive assistant, 3 physical coach, 4 GK
coach, 5 manager, 6 youth manager. Averaging the coaching bars over each
job in the database (**empirical**) agrees:

| Job | Count | Coaching bars (DRIBB SHOT PASS HEAD INTER MARK) | Is |
|---|---|---|---|
| 0 | 439 | 68 68 68 60 68 68 | a balanced assistant: all even. Hired as manager it becomes 5, as youth manager 6 |
| 1 | 786 | 80 80 80 68 55 55 | an attacking coach |
| 2 | 714 | 68 55 61 76 80 80 | a defensive coach |
| 3 | 678 | physical bars | physical coach |
| 4 | 383 | saving bars | goalkeeper coach |

In a save, M. Eulenburg and S. Saioni (job 0 in the database) are the
manager (5) and youth manager (6), and the coaches keep jobs 1–4. Job 0
is where managers start, not the only way to become one: in the game,
coaches and former players can become managers too. The code has a coach
job-change work area (`pwkTeam_SetCoachJobChangeWork`,
`pwkTeam_PutCoachJobChangeWork` and neighbours, `0x26b998`–`0x26bc88`),
and a player's `PlPinfo +0x210` holds a job change
(`plPinfo_GetChangeJob` / `SetChangeJob`); neither is traced yet.
`pwkTeam_SetYManager` (`0x26bd28`) writes 6 into the youth manager's
`+0xa0` after copying him in (**confirmed**); where 5 is set for a manager
isn't traced (`pwkTeam_SignManager`, `0x269e20`, copies the record as it
is and sets only the contract years at `+0x9e`).

The coach page's title (`SetupDetailCoachPageCommon`, jump table
`0x5577d0`) is the same string for jobs 0, 1 and 2 (`Msg::GetString(0x18,
3)`), with 4 for goalkeeper coaches and 5 for physical coaches. Those
match messages 553 "Assistant Coach", 554 "GK Coach" and 555 "Physical
Coach" of category 100001. Checked in game: S. Daerden (job 1) and
L. Lynch (job 2) are both titled "Assistant Coach", and their comment
lines call them an "outstanding forwards coach" and a "very good defence
coach", which fits the averages above. So the game gives jobs 0–2 one
title; what tells them apart is which abilities they are good at, which
the comment line puts into words.
`GP::ConvertStaff` (`0x27ee68`) likewise gives 0–2 one icon.

**Confirmed, `WP::CDetailManager::ConvertScout` (`0x287c60`).**
`PlSinfo` is 4 bytes followed by the `PlSbase` (`plSinfo_InitDb`
`0x21eb80`). The 11 scout bars are single abilities (the 45 mapped
scout abilities, starting at `PlSbase +0x2d`): CLB 0, PLAYE 1, FINDP 3,
YOUTH 4, YOUNG 5, OLDER 6, VETER 7, MANAG 21, ACOAC 22, PCOAC 23,
GCOAC 24. A 12th value, ability 25, is computed too but not labelled.
Staff and scout bars are drawn as `value / 99`. Player bars add 10
first.

`python SRC/pbdata.py show` prints these bars for managers and scouts
(the job's own set, plus the manager set for coaches), and `csv` adds
them as columns.

## Entries 2 and 3

Each is 27,950 u16. **Entry 2 is a ranking** of the player ids: players
0–25,590 sorted by rank (highest first), then main position, then
nationality, followed by ids 25,591–27,949 in order. **Entry 3 is its
inverse**, each player's place in the ranking. Both hold for all 27,950
players (**empirical**, sorted by the stored `+0x18`, `+0x1c` and
`+0x14`; `pbdata.py info` checks it).

**Confirmed from the code.** A table of 16 × 13 s32 at `0x52fbf8`, fixed
in the executable, gives the first place of each group: row 15 − rank,
column = main position, −1 for an empty group. Row 0 has two groups
(place 0 in column 9, places 1–2 in column 12), and the last group starts
at 25,585 (row 15, column 12). The readers:

- `serchPinfo` (`0x20d470`) finds a group's range of places and reads
  the players through entry 2 (`0x390670`). The last range ends at
  `0x63f7`. Given a nation, it narrows the range to that nationality,
  which is why each group is sorted by it.
- `getPinfoRank` (`0x20d908`) and `getPinfoApos0` (`0x20d9a0`) find the
  row and column that hold a player's entry-3 place. So for players below
  `0x63f7`, **the game's rank and main position come from the place**,
  not from `+0x18`/`+0x1c`.

For editing: changing the rank or main position in a record has no
effect in the game for ids below 25,591, and changing the nationality
moves the player out of his nation's call-up search. Moving a player
properly would mean re-sorting entries 2 and 3 and changing the group
starts in the executable (`0x52fbf8`, and the run-time ranges at
`0x5eac08` if they are built from it). `pbdata.py set` and `import` say
when an edit leaves the ranking out of order; they don't re-sort it.

## National team call-ups

**Confirmed, `SIMPRG.REL` and `SLES_541.51`.** In a career a national
squad is picked from the club players when it is called up:

| Address | Symbol | What it does |
|---|---|---|
| `SIMPRG.REL 0x160b68` | `jmNT_CallCheck` | on a day where `pwkSche_IsNationalConvene` is true, calls up every squad (`jmNT_CallAll`) and sets event flags `0x13f`–`0x141` |
| `SIMPRG.REL 0x1603c8`, `0x160210` | `jmNT_CallAll`, `jmNT_makeNationList` | lists the nations with an international competition on the schedule and runs `plTeam_CreateNationTeam(team, squad, 23)` for each |
| `SIMPRG.REL 0x15fbe8` | `jmNT_NewCall(team)` | the same for one team |
| `0x226338` | (unnamed) | the squad's shape: counts the positions in the national manager's three formations (`PlMbase +0x3d`, see [the staff editors](#the-developers-staff-editors)) and scales them to 25 places over the 13 positions |
| `0x227470` | `plTeam_CreateNationTeam` | for each position, walks the ranking best first (`serchPinfo` with rank, position and the team's nation) and fills a pool of up to 38 |
| `0x534148` | per-position limit | at most 1 goalkeeper and 3 players per other position from one club |
| `0x2272f8`, `0x227200` | `_sortBaseListFromNationalTeamPoint`, `_getNationalTeamPoint` | sort the pool by a national-team score before the squad is kept |

`plTeam_CreateNationTeam` takes only players whose current team (bits 22
and up of the run-time core info) is the user's club (1), another club
(2–459) or team 465. From the user's club it takes at most 8, and none
with flag `0x300` in `PlPinfo +0x20c`. The search stops at `0x63f7`, so
the fixed national records (26,041+) are never called up.

So to change who plays for a country in a career, edit the club players
(their nationality and their place in the ranking, see above). The fixed
blocks only change VS mode. What `_getNationalTeamPoint` scores, what
team 465 is, and what flag `0x300` means aren't traced.

## `PBDATA_JP.PAC`

The same header and identical entries 2 and 3, but entry 1 is empty (0
bytes). The European disc carries no Japanese player records. `pbdata.py
info` reports this as a note, not a problem.

## Writing

`pbdata.py` can write the database back out. Each record is re-encoded
from its stored field values in `readBits` order: the 19 name bytes as
they were, every field at its width, then the padding bits as they were.
Entry 1 is then replaced in a copy of the pack. Records are fixed-size,
so the entry keeps its offset and size and nothing else in the file
moves. `pbdata.py roundtrip` does this for all 31,950 records without
changes, and the result is byte-identical to the disc's file (a
`regress.py` check).

Edits are given as the values `show` prints, and are converted back:

- `add` fields subtract their offset (age 30 is stored as 14).
- Abilities must be one of the 32 table values, 38–99.
- `req_status` must be one of the 16 table values, stored as its index. The
  game reads only the low 4 bits of the 16-bit field, so an unchanged
  value keeps its stored bits.
- Signed manager fields must fit 9 bits.
- Names are cp850, at most 18 bytes, zero-padded to 19 (every name on the
  disc has a terminator).

The limits are mostly the field widths, not what the game considers
sensible. The exception is `age`, `height` and `weight`: the decoder adds
their offset and stores the sum in a byte, so `pbdata.py` refuses values
above 255. Height is the only one where that matters (the field alone
would allow up to 405 cm). Otherwise the game takes whatever fits.

**Tested in the game** (PCSX2, new game, patched with `patch_disc.py`):
Terry renamed `J.Terry.MOD`, 96 kg, left-footed, with abilities
alternating 38 and 99. The name, weight, leg and the bar pattern all
showed as predicted by `pbdata.py show` (low SPEED and FK, high STAMI,
HEAD, INTER and MARK). A height of 313 cm showed as 57 cm, which is what
led to the byte limit above. A second test with 255 cm showed 255 cm.

```bash
python SRC/pbdata.py set DAT/PARAM/PBDATA_EU.PAC out.PAC 101 age=30 ability.13=99 name=J.Terry
python SRC/pbdata.py csv DAT/PARAM/PBDATA_EU.PAC players players.csv   # edit in a spreadsheet
python SRC/pbdata.py import DAT/PARAM/PBDATA_EU.PAC out.PAC players players.csv
```

`import` writes only the values that differ from the pack, so an unedited
CSV gives an identical file. The bar and `entry2`/`entry3` columns are
derived and ignored. Putting the edited pack back on a disc is the
Rebuild stage in [`GOALS.md`](../GOALS.md), which isn't done yet.

## Still unknown

- The fields the developers' editor doesn't label: `+0x30`, `+0x43`–`+0x46`,
  `+0x57`–`+0x5d` and `+0x66`–`+0x70` (except `+0x67`'s use as the
  affinity row).
- What the match engine (`GAMEPRG.REL`) does with `+0x3f`–`+0x5d` and
  abilities 53–63, and which attack pattern letter is which.
- What each speech tone, condition type, ball-touch type and dribble
  style value is.
- The hexagon labels are matched to indices from the data and VPF's
  pages. The label order in `GP::CHexWindowBase::DrawString` (`0x27c700`)
  comes from a screen layout and hasn't been traced.
- What the play styles do in a match, beyond which abilities grow.
- The code that turns the leg field into `PlPinfo +0x1c4`.
- What sets job 5 when a manager is hired.
- The staff fields neither editor labels (manager `+0x18`, `+0x20`,
  `+0x26`, `+0x2a`–`+0x2e`; scout `+0x1c`, `+0x20`, `+0x24`), what the
  manager's 25 policies (`+0x34`) and the policy ranges mean, and what
  the 1–5 tactical values and the model pattern do in a match.
- Which game code reads the staff abilities that no bar shows (6–9,
  23–27, 31–38; scouts 2, 8–20, 26–44). The labels name them, but their
  effects aren't traced.
- Header `+0x14`, `+0x24` and the last 8 header bytes.
- What fills the rank ranges at `0x5eac08` (probably the group table at
  `0x52fbf8`), and what `_getNationalTeamPoint` scores.
- Which clubs teams 442–459 are, and a PCSX2 check that a career
  call-up doesn't show a renamed fixed national player (VS mode does).

## Checking the claims

```bash
python SRC/pbdata.py info DAT/PARAM/PBDATA_EU.PAC DAT/PARAM/PBDATA_JP.PAC
python SRC/pbdata.py list DAT/PARAM/PBDATA_EU.PAC --find terry
python SRC/pbdata.py show DAT/PARAM/PBDATA_EU.PAC 100 m:0 s:0     # every field
python SRC/snr2.py dis ISO/DLL/DEBUGPRG.REL 0x1c98 340 --sles ISO/SLES_541.51   # manager editor pages
python SRC/snr2.py dis ISO/DLL/DEBUGPRG.REL 0x97a0 70 --sles ISO/SLES_541.51    # scout editor, special searches
python SRC/pbdata.py csv DAT/PARAM/PBDATA_EU.PAC players players.csv
python SRC/initteam.py squads DAT/PARAM 7                          # Chelsea, with names
python SRC/sles_disasm.py ISO/SLES_541.51 dis initBpmaster getPbase readBits__Q25Param11PlBitsClassi
python SRC/sles_disasm.py ISO/SLES_541.51 dis plBits_DecPlPbaseEx plBits_DecPlMbaseEx plBits_DecPlSbaseEx
```
