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

**Empirical**, checked against the labels: the drills raise the
abilities their names say (shooting raises shot skill, acceleration
training pace and acceleration, leadership leadership), and every row
with negative fatigue is a rest, recovery or therapy menu.

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
and its Camps tab previews a camp type's row of table 10. No edit has
been tested in PCSX2 yet: a practice made much stronger would show in a
player's growth after a few weeks.

## Still unknown

- The scale of a practice's values (how much growth one point is) and of
  the fatigue column. One data point: a week-long keeper camp (camp row
  83) gave about 60 ability experience per point to three keepers in
  PCSX2 ([`CAMP_FORMAT.md`](CAMP_FORMAT.md)); how condition, age, the
  coaches and the facilities change that isn't known.
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
