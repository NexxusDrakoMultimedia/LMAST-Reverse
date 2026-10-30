<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/TRAINING_LIST.TBB`: training, growth and decline

The numbers behind training: how much each practice menu trains each
ability and how tiring it is, what the facilities and training camps
add, how a match grows a player by position, and how abilities decline
with age. The file is a TBB1 file ([`TBB_FORMAT.md`](TBB_FORMAT.md)) of
13 tables of signed bytes (line size 1). Copies sit in entry 10 of
`PRELOAD/SIMFILE0`–`6.PAC`.

`python SRC/training.py info DAT/PARAM` checks every table.
`python SRC/training.py show DAT/PARAM/TRAINING_LIST.TBB team 8` prints a
row with its abilities named. `set` edits values ([below](#editing)).

## Who reads it

| Address | Symbol | What it shows |
|---|---|---|
| `SIMPRG.REL 0x159b00` | (training module) | picks the load list `0x23d618` (`Training_list.tbb`, `Camp_list.tbb`) during a camp (`pwkSche_CheckCampTearm`), else `0x23d690` (`Training_list.tbb` alone). **confirmed** |
| `SIMPRG.REL 0x159998` | (training module, vtable `0x20f3b4`) | takes the resource (`CFcEuro_Common::GetResourceHandle(0)`) and keeps a pointer to each table (`CTblData::GetDataHeadPoint`): table 0 at `+0x48`, 1 `+0x4c`, 10 `+0x50`, 3 `+0x54`, 4 `+0x58`, 5 `+0x5c`, 6 `+0x60`, 7 `+0x64`, 8 `+0x68`, 2 `+0x6c`, 9 `+0x70`, 12 `+0x74`. **confirmed** |
| `SLES 0x246540` | (before `pwkMatchGrow_Grow`) | loads `Training_list.tbb` by name and returns table 11 for `pwkMatchGrow_Grow` (`0x2465f8`, the call at `0x2466a0`). **confirmed** |

## The tables

Columns 0–63 of the wide tables are the 64 abilities (`PlAbilNo`, named
in [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#abilities-and-the-detail-screen));
the module's loops run over `0x40` of them (`0x1589b4`). All values are
signed bytes (`lb`) except tables 2 and 9 (`lbu`).

| Table | Name (`training.py`) | Rows × columns | Row is | Accessor | **confirmed** |
|---|---|---|---|---|---|
| 0 | `team` | 29 × 65 | practice number 0–28 | `0x159fb8`: row × 65 + column | yes |
| 1 | `practice` | 110 × 65 | practice number 29–138 | `0x15a070`: (number − 29) × 65 + column, numbers below `0x1d` give 0 | yes |
| 2 | `group` | 64 | ability | `0x15a0a0`, `0x15a128`: 0 physical, 1 skill, 2 mental | yes |
| 3–5 | `decline_physical`, `decline_skill`, `decline_mental` | 16 × 25 | growth type | `0x159eb0`, `0x159ed8`, `0x159f00`: type × 25 + age − 16 | yes |
| 6 | `stadium` | 16 × 71 | stadium equipment | `0x159d3c` | yes |
| 7 | `clubhouse` | 36 × 71 | club-house equipment | `0x159cd8` | yes |
| 8 | `youthhouse` | 18 × 71 | youth-house equipment | `0x159ce4` | yes |
| 9 | `staff` | 64 | ability | `0x159b68`, `0x15ab58` | yes |
| 10 | `camp` | 87 × 65 | camp type | `0x15a040`: row × 65 + column | yes |
| 11 | `match` | 13 × 65 | pitch position | `pwkMatchGrow_Grow` `0x246830` | yes |
| 12 | `youth` | 28 × 65 | youth practice menu | `0x15ac48`: row × 65 + column | yes |

### Practices (tables 0 and 1)

A practice number (`PlPracNo`) is one of the 139 training menu items. Their
labels are in the developers' manager editor (`DEBUGPRG.REL 0x105b8`, a
list of 139 pointers); `training.py` gives them with English names:

| Numbers | What |
|---|---|
| 0–7 | the systems 3-4-3 … 5-4-1 |
| 8–28 | team training: direct play, possession, centre and side attack, combinations A–E, pressing, covering, offside trap, speed, power, stamina, practice match, teamwork, set plays, conditioning, rest, extra rest |
| 29–31 | growth policies: develop strengths, balanced, cover weaknesses |
| 32–51 | forward, defender, keeper, physical and mental practice |
| 52–73 | play styles |
| 74–138 | individual drills, physical training, therapies and lectures |

Each column 0–63 is what the practice adds to that ability's growth;
column 64 is its fatigue, passed with the facility and manager fatigue
factors to `plPinfo_CalcPracTired` (`0x1590c8`–`0x159118`). The rest
menus (27, 28) and the recovery drills and therapies have negative
fatigue; the rest menus train nothing.

Practices 12–16 (combinations A–E) don't use their own rows: `0x159f28`
reads my-team data `+0x489f` + (number − 12) and uses row 12 + (value −
1) ÷ 6 when the value is 1–30, and nothing otherwise.

**Empirical**, checked against the names: the drills raise the
abilities their names say (shooting raises shot skill, acceleration
training pace and acceleration, leadership leadership), and every row
with negative fatigue is a rest, recovery or therapy menu. In PAL's
European languages the names of drills 74–86 are one message early, below.

#### Drills 74–86: PAL's names are one early

The name of practice *n* (29–138) is message 971 + *n* of category 801
(`pwkGUtl_PlPracNo2MsgID`, SLES `0x245bd8`: *n* + `0x3cb`; below 29 the
number itself). In the Japanese names (`801_0.mbb`, on both discs)
practice 74 is ダミー "dummy", 75 is pinpoint shooting and 86 king of
dribbling, and there is no jackknife. Every row of table 1 fits those
names. PAL's European names (`801_1`–`6.mbb`; French, German, Italian
and Spanish the same) are one message early, and 1057 (practice 86) holds
an added "Jackknife":

| Practice | Japanese name (`801_0`) | PAL English name (`801_1`) | What its row trains |
|---|---|---|---|
| 74 | ダミー dummy | Shot training. | nothing (all zero, no fatigue) |
| 75 | ピンポイントシュート pinpoint shooting | Pass training. | shot skill and technique +15 |
| 76 | ベルベットパス velvet pass | Dribble training | short and long pass, cross +10 |
| 77 | テクニカルドリブル technical dribbling | Set pieces training. | dribble pace and skill +15 |
| 78 | フリーキックオフェンス free kick attack | Train all aspects. | placekick +20, cross +10 |
| 79 | オフェンス総合練習 all-round attack | Long-range shot training. | +2 to +5 in most attacking abilities |
| 80 | ロングシュート long shots | Direct shot training. | kick strength, shot skill +15 |
| 81 | ダイレクトシュート first-time shots | Target man training. | shot technique +15, nerve +5 |
| 82 | ポストプレイ post play | Train for the drifting run. | ball keeping +15, contact strength +10 |
| 83 | プルアウェイ pull away | One-on-one finishing. | vision, acceleration +10 |
| 84 | 1対1シュート 1-on-1 shooting | "Cannon Shot" training. | shot skill +20, technique +10 |
| 85 | キャノンシュート cannon shot | "King of Dribble" training. | kick strength +15, shot technique +10 |
| 86 | キングオブドリブル king of dribbling | "Jackknife" training. | dribble skill +20, dribble pace +10 |

From 87 (ball touch) the names agree again. No coach teaches drill 74 in
either release (the drills a coach can teach, `+0x54` of the 3,000
managers in `PBDATA_EU.PAC`, [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md):
75 is listed 172 times, 76 352 times, ... 86 18 times, 74 never).
Drills 52–138 are the ones coaches teach, so the dummy should never be
offered (how the menu builds its list isn't traced). So the table and the
coaches follow the Japanese numbering, and in PAL each drill 75–86 shows
the next drill's name: the drill named "Pass training." trains shooting.
The Japanese disc's English slot has the right numbering (1045 missing,
1046 "Shoot" ... 1057 "King of Dribble").

PAL's order is that of an older list of 13 drills with jackknife and no
dummy: the developers' manager editor (`DEBUGPRG.REL 0x105b8`, both
releases) and category 700 messages 8222–8234 (both releases; what reads
them isn't traced).

`python SRC/patch_disc.py patch <image> <out> --mod drill-names` moves
messages 1045–1056 to 1046–1057 in `801_1`–`6.mbb` and their copies in
`PRELOAD/SIMFILE1`–`6.PAC` (entry 28), so each drill shows its own
name; the jackknife name goes to 1045, which is never shown, and the
files keep their sizes ([`LMASTER_MOD.md`](LMASTER_MOD.md)).
**Tested in PCSX2** (Nexxus's report): coach R.Bloemzaad teaches drills 76
and 62; drill 76, whose row trains short pass, long pass and cross +10,
reads "Dribble training" on the retail disc and "Pass training." on
`LMAST-test-drills.iso`. The coach was found in a career's staff
candidate list read from a save state (block 1 `+0x9ac8`). `python
SRC/training.py show DAT/PARAM/TRAINING_LIST.TBB
practice` prints the rows; `python SRC/mbb.py dump DAT/MESSAGE/MES.PAC
--cat 801` the names.

### Groups and staff (tables 2 and 9)

Table 2 puts each ability in a group (`0x15a0a0`): 0 physical (abilities
19–25), 1 skill (0–18, 33–44, 59–63), 2 mental (26–32, 45–58). The
group picks which growth type and growth coefficient apply
(`pwkGUtl_GetPhysical/Skill/MentalGrowCoe`, `0x159e50`–`0x159e90`).

Table 9 gives the staff ability (0–47,
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md)) that coaches each ability: dribble
coaching for the dribbling abilities, speed for pace and acceleration,
the system coaching for each system. `0x159b68` reads that ability of the
manager (my-team data `+0x48be` + n), `0x15ab58` of the youth team's
coach (youth data `+0x3f6a` + n); from 50 up it adds (value × 0.2 − 1) %.

### Decline with age (tables 3–5)

Row = the player's growth type (`PlPinfo +0x1e2`, `+0x1e3`, `+0x1e4`, the
database's physical, skill and mental growth types), column = age − 16.
`0x15a128` uses the table of the ability's group and only below age 41
(`0x15a144`); `0x159284` passes the result, negated and scaled, to
`pwkGUtl_AddExp`, so it is taken from the ability's experience. The disc's
values run from 0 when young to 5–7 from the late twenties on.

### Facilities (tables 6–8)

For each ability, `0x159c68` adds up the bonus of every facility the club
has and returns it as a fraction (÷ 100):

- First team: the club-house equipment (`pwkTeam_GetChouse` `+0x5` + 3 × i,
  9 slots, −1 none) from table 7, and the stadium equipment
  (`pwkTeam_GetStadium` `+0xf` + 2 × i, 16 flags) from table 6.
- Youth team (`0x15a764`, `0x15a9c8`, third argument 1): the youth-house
  equipment (`+0x20` + 3 × i) from table 8.

The rows are the entries of the equipment tables in
[`PLRESOURCECOMMON.PAC`](PLRESOURCECOMMON_FORMAT.md) (16 stadium, 36
club-house and 18 youth-house items). The tables are 71 wide; the module
reads only columns 0–63. Columns 64–70 hold values in table 6 (column 64)
and table 7 (64–66, 68–70, in steps of three levels such as 5, 10, 15),
but no reader of them has been found.

### Camps, matches and the youth team (tables 10–12)

- Table 10's row is the camp type (`pwkSche_GetCampType`, `0x1586b4`),
  used instead of the practice's own row while a camp runs. The camp
  list numbers its types 1–87, one more than this table's rows, so every
  camp reads the next row ([`CAMP_FORMAT.md`](CAMP_FORMAT.md#two-bugs)).
- Table 11's row is the player's pitch position (`PlPinfo +4`): GK, LSB,
  RSB, CB, LWB, RWB, DM, LSM, RSM, OM, LWG, RWG, FW. **Empirical**: the
  keeper row trains saving and catching, the forward row shooting and
  dribbling, and the left and right rows their side's aptitude.
- Table 12's row is the youth team's practice menu (youth data `+0x3fbc`
  + 4 × slot, `0x15aae8`).

The 87 camp types and 28 youth menus have no names yet.

### Japanese release

The Japanese file differs only in table 1's fatigue column: 11 recovery
menus have −10 in PAL and 0 in the Japanese file. They are 50 condition
up, 51 motivation up, 122 condition support, 123 mental support, 124
fatigue recovery, 125 early injury recovery, 130 low-frequency therapy,
131 ultrasound therapy, 132 breathing, 133 recreation and 134
rehabilitation. In the Japanese release they didn't relieve fatigue
through this table.

## Editing

```bash
python SRC/training.py set DAT/PARAM/TRAINING_LIST.TBB out/TRAINING_LIST.TBB team 27 fatigue=-20 practice 32 shot_skill=25
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/TRAINING_LIST.TBB=out/TRAINING_LIST.TBB --copies
```

`set` takes a table (number or name), a row, then `column=value` pairs;
a new table and row may follow. A column is an ability number or name
(`shot_skill`), `fatigue`, a number up to 70, or for the decline tables
an age (`age30`). It refuses values the code can't use (groups 0–2,
staff abilities 0–47, signed bytes elsewhere). The file keeps its size;
`--copies` also patches the seven `SIMFILE` copies.
`python SRC/training.py roundtrip` re-encodes every table and checks that
the file rebuilds byte for byte. The editor's Training tab edits the
practice, camp-type and youth rows, match growth, the facility bonuses,
the coaching staff ability and decline with age through the same code,
and its Camps tab previews a camp type's row of table 10.

**Tested in PCSX2** (disc `LMAST-test-training.iso`: practice 32,
shooting, with shot skill +100 instead of +10 and shot technique left at
+10). Two players got "Shot training." from an assistant coach for one
turn on which the team trained set pieces (team row 25). Read from save
states before and after: the team session gave about 3–4 experience per
point (placekick, header and jump), and after taking that off (and one
player's age decline), the shooting practice added about 77–87 to shot
skill and 12–14 to shot technique. On the retail row the two would be
equal, so the edit is read; the ratio is 6–7 rather than 10, so growth
seems to rise less than linearly with the value. Training runs when the
turn advances, not when "Conduct Training" is chosen (Nexxus's report).

## Still unknown

- The scale of a practice's values (how much growth one point is) and of
  the fatigue column. One data point: a week-long keeper camp (camp row
  83) gave about 60 ability experience per point to three keepers in
  PCSX2 ([`CAMP_FORMAT.md`](CAMP_FORMAT.md)), a team session about 3–4
  per point, and an individual practice raised to +100 only 6–7 times
  what +10 gives ([Editing](#editing)); how condition, age, the coaches
  and the facilities change that isn't known.
- What reads category 700's drill list (messages 8222–8234, the older
  order with jackknife), and whether PAL shows it anywhere
  ([above](#drills-7486-pals-names-are-one-early)).
- The names of the 87 camp types and 28 youth menus, and of the facility
  rows.
- Whether anything reads columns 64–70 of the facility tables.

## Checking the claims

```bash
python SRC/training.py info DAT/PARAM
python SRC/training.py show DAT/PARAM/TRAINING_LIST.TBB team 8 22 27
python SRC/training.py show DAT/PARAM/TRAINING_LIST.TBB staff
python SRC/training.py roundtrip DAT/PARAM/TRAINING_LIST.TBB
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 159998 72 --sles ISO/SLES_541.51    # the table pointers
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 159b68 30 --sles ISO/SLES_541.51    # staff ability
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 159eb0 120 --sles ISO/SLES_541.51   # decline, team, camp, practice
python SRC/sles_disasm.py ISO/SLES_541.51 addr 246830 6                        # match growth row
```
