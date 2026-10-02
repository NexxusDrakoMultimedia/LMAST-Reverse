<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# SQB sequencer scripts (`SEQ/*.SQB`, `PARAM/PSC*.PAC`)

`.SQB` files are **bytecode scripts**, not music. The game's sequencer
(`CSeqController` in `SLES_541.51`) runs them. There are two kinds:

- **Root scripts** (`DAT/SEQ/Root*Seq.sqb`) drive the game's flow. They
  start and stop the screens (sequencer modules, see
  [`SNR2_FORMAT.md`](SNR2_FORMAT.md#which-overlay-the-game-loads)), load
  resources, play BGM and run the calendar: boot, main menu, club edit,
  month start and end, matches.
- **PwkScript scripts** (`.sqb` entries in `DAT/PARAM/PSC*.PAC`) are small
  formulas over player, manager and scout data, such as ability points,
  popularity and spectators. They are run by `Param::PwkScript`.

Both use the same container, command encoding and built-in commands, but a
different set of game commands. `python SRC/sqb.py info DAT/SEQ DAT/PARAM`
decodes and checks all of them. `python SRC/sqb.py dis <file>` prints a
listing.

The layout is **confirmed** from the interpreter in `SLES_541.51` (table
below). The command names come from the executable's symbol table where
one exists. Where none exists, the name describes what the command calls
and is marked as such.

## Files

`DAT/SEQ/` holds 19 `.SQB`, 2 `.TBB` and 1 `.WPX` file (plus `CVS/`):

| File | What it is |
|---|---|
| `SQBFILENAME.TBB` | the root script list: 18 rows of `char[32]`, row = script id. Rows 1–15 are the `Root*Seq.sqb` files, 16 is `PinfoPoint.sqb`, 0 and 17 are `"NULL"`. `0x149f30` loads `SqbFilename.tbb`; `0x14a220` loads every row that isn't `"NULL"` (`strcmp` against `0x523118`) |
| `GLOBALMEMORY.TBB` | 25 records of 16 bytes, the sequencer's global variables (below). Loaded as `GlobalMemory.tbb` by `0x14a050` |
| `ROOT*SEQ.SQB` (15) | the root scripts, ids 1–15 |
| `PINFOPOINT.SQB` | id 16: an older build of `PSCCOMMON.PAC#PscCommon_PinfoPoint.sqb` (same size, 4 script words differ) |
| `A001.SQB` | a test loop (count 600 down in a function). Not in `SQBFILENAME.TBB` and not named anywhere in the code |
| `CHECKCLUBEDIT.SQB`, `INFORMATION.SQB` | 2004 scripts for other command sets; see [what doesn't decode](#what-doesnt-decode) |
| `INFORMATION.WPX` | a `TBB1` of 4 `TBL1` tables (49, 45, 45 bytes and 8 rows of 4), holding floats such as 30.0, 70.0, 300.0 and 380.0. No `.wpx` string appears in the executable or any overlay, so it isn't loaded. Content not decoded |

The 24 `.sqb` entries of `PSCCOMMON.PAC` (20), `PSCGAME.PAC` (2) and
`PSCPRACTICE.PAC` (2) are the PwkScript scripts (see
[`PARAM_DIR.md`](PARAM_DIR.md)). `PRELOAD/STATIONFILE.PAC` carries copies
of `psccommon.pac` and `pscgame.pac` as nested packs.

## Container

A script file is a `TBB1` container ([`TBB_FORMAT.md`](TBB_FORMAT.md)).
Its tables are `SQB1` scripts and, in PwkScript files, `SQT1` data tables:

```
SQB1: {'SQB1', u32 data_offset = 0x10, u32 size, u32 0} + size bytes of commands
SQT1: {'SQT1', u32 data_offset = 0x20, u32 size, u32 element_size,
       u32 flag, u32 rows, u32 columns, u32 0} + size bytes
```

- **Confirmed.** `CRsrcManager::LoadScript` (`0x1fd9c0`) PRS-expands the
  file if needed, takes table 0 (`TbbData::GetTableDataPtr`), checks the
  magic `SQB1` (`0x1fda5c`) and copies `data_offset + size` bytes.
  `CSeqController::Initialize` (`0x1ff780`) starts at table 0's data
  (`0x1ff89c`).
- **Confirmed.** `CSeqController::GetTable` (`0x2007f8`) returns table *n*
  of the script's container. The Param table commands read the element size
  at `+0xc` (1 = u8, 2 = s16, anything else = u32, `0x304f90`) and the shape
  at `+0x14`/`+0x18` (`0x306228`).
- **Empirical.** All 68 `SQT1` tables have `size = element_size × rows ×
  columns`. `flag` is 1 in 57 and 0 in 11. What it does isn't traced.
- **Empirical.** Every PwkScript has exactly one `SQB1` table, table 0.

The root scripts store the file size at `TBB1 +0xc`. The four files dated
2004 (`A001`, `CHECKCLUBEDIT`, `INFORMATION`, `PINFOPOINT`) store 0 there.
`CHECKCLUBEDIT` and `PINFOPOINT` also count the end of the file as one more
table offset, which is why `tbb.py info` can't read them. The game only reads
the tables it asks for, so neither difference matters to it.

## Commands

**Confirmed** from `CSeqController::UpdateCommand` (`0x1ffa90`):

```
command = {u32 table, u32 cmd} + argc × {u32 type, s32 value}
```

The controller looks `table` up in its command-info array (`+0x228`, 16-byte
`COMMAND_INFO` entries `{u32 *argc, fn *callback, u32 count, u32 0}`), calls
`callback[cmd]` and, if it returned 0, steps by `(argc[cmd] + 1) × 8`. The
callback's return value controls the loop:

| Return | Effect (`0x1ffb34`–`0x1ffbc8`) |
|---|---|
| 0 | next command, same frame |
| 1, 2 | stop for this frame and run the same command again next frame. `EndLoop` returns 2, so it idles forever |
| 3 | the script has ended (`End` returns 3; `Update` returns 1) |
| negative | error |

A command that jumps sets `+0x234`, and the next command is taken from
there instead.

### Arguments

**Confirmed** from `CSeqController::GetArgInt` (`0x1ffdd8`, jump table
`0x52f440`). Argument 0 is where a command writes its result
(`SetArgInt`, vtable `+0x28`, is called with `args[0]`).

| Type | Meaning | `dis` shows |
|---|---|---|
| 0 | literal value | `600` |
| 7 | literal value (same code as 0). The root scripts use it for module and resource ids | `k30` |
| 2 | controller word `+0x08 + 4 × value`, 50 words | `m2[i]` |
| 3 | controller word `+0xd0 + 4 × value`, 50 words | `m3[i]` |
| 4 | controller word `+0x198 + 4 × value`, 10 words | `m4[i]` |
| 5 | controller word `+0x1c0 + 4 × value`, 10 words; cleared by `Function`, and `m5[0]` is the return value | `m5[i]` |
| 6 | global memory record `value` (`CRsrcManager::GetGlobalMemory`, `0x1fdce8`), read only if the record's type is 0 | `g[i]` |
| 1, 8 | error (-1) | |

`Initialize` clears the four memories (`0xc8`, `0xc8`, `0x28` and `0x28`
bytes). Scripts write `m3[0]` as a "don't care" result almost everywhere.

**Empirical** (all 41 scripts that decode): 5,277 arguments. Type 2 is never
used and type 5 only once. The highest indices used are `m3[49]`, `m4[5]`,
`m5[1]` and `g[21]`.

### Labels, jumps and calls

**Confirmed** from `CSeqController::ResolveLabel` (`0x1ffbf0`), run once by
`Initialize`:

- Base command 2 (`Command_Nop`) marks a **label** at the *next* command.
  Base command 3 (`Function`) marks a label at *itself*. The label id is
  argument 1, below 200 (`0x1ffcdc`). A repeated id is an error
  (`0x1ffd34`). Both kinds share one id space.
- **Jumps and branches** (`JumpIf*`, `BranchIf*`) take the value to test in
  argument 1 and the label in argument 2 (`CSeqController::JumpIf`,
  `0x2000d0`). Zero, not-zero, minus, not-minus, plus and not-plus are the
  six `eJUMPIF` tests (`0x52f4a0`). How `BranchIf` differs from `JumpIf` in
  effect isn't traced: it calls `JumpIf` and turns a result of 1 into 0
  (`0x2001f8`).
- **`Call`** takes the label in argument 1 and saves argument 0 as the
  return-value slot (`0x200630`). Calls don't nest: `Call` fails if a
  return address is already set. `Function` fails outside a call and clears
  `m5` (`0x2005a0`). `Return` jumps back and writes `m5[0]` to the saved
  slot (`0x2005d8`).

`sqb.py info` checks that every label is unique and below 200, and that
every literal jump or call target exists. In all 41 scripts, every one does
(202 labels).

## Command sets

**Confirmed.** A set is an array of five `COMMAND_INFO` entries, registered
with `ISeqManager::SetCommandTable` (vtable `+0x40`, count 5):

| Table | Root set `Seq_fc_euro::pCommandInfoTbl` `0x5668b0` (registered at `0x10e750`) | PwkScript set `0x552df0` (`Param::PwkScript::SetCommandTable`, `0x256e00`) |
|---|---|---|
| 0 | **Base**, 39 commands: argc `0x3a7720`, callbacks `0x3a77c0` (`Seq_fc_euro$pdwCmdParamNumBase` / `ppfnCommandCbBase`) | the same Base table |
| 1 | **Scene**, 7: `0x3a79c8` / `0x3a79e8`. All seven callbacks are `Seq::Command_Nop` | empty (count 2, no arrays) |
| 2 | **Window**, `WND$pdwCmdParamNumWindow` `0x34dee8` / `ppfnCommandCbWindow` `0x34def0`, count 44. The two arrays are 8 bytes apart and zero on disc, and `0x34df08` is the wild-card module id, so this is a placeholder, not a usable table | empty |
| 3 | empty | empty |
| 4 | **RootEvent**, 125: `FC_EURO_EVCOM$pdwCmdParamNumRootEvent` `0x34daf8` / `ppfnCommandCbRootEvent` `0x34dcf0` | **Param**, 30: `FC_EURO_PARAM$pdwCmdParamNumParam` `0x3a7860` / `ppfnCommandCbParam` `0x3a78d8` |

The argument counts are copied into `sqb.py`, so it doesn't need the
executable.

### Base (table 0)

Names are the `Seq::Command_*` symbols. Argument 0 is the result in every
row.

| Cmd | Name | argc | What it does |
|---|---|---|---|
| 0, 1 | `CreateSequenceController`, `DeleteSequenceController` | 2 | |
| 2 | `Nop`, used as **Label** | 2 | marks label `arg1` (above) |
| 3 | `Function` | 2 | marks label `arg1`; see calls |
| 4, 6 | `Return` | 1 | |
| 5 | `Call` | 2 | call label `arg1` |
| 7, 8 | `GetControllerMemory`, `SetControllerMemory` | 3, 4 | |
| 9–14 | `JumpIfZero`, `NotZero`, `Minus`, `NotMinus`, `Plus`, `NotPlus` | 3 | test `arg1`, jump to label `arg2` |
| 15, 16 | `CheckController`, `FindController` | 2, 3 | |
| 17 | `End` | 1 | returns 3 |
| 18 | `EndLoop` | 1 | returns 2 |
| 19 | `Sub` | 3 | `arg0 = arg1 − arg2` (`0x31895c`) |
| 20 | `Set` | 2 | `arg0 = arg1` |
| 21 | `SetIf` | 4 | if `arg1 == arg2`: `arg0 = arg3` (`0x318cf0`) |
| 22 | `SetIfRange` | 5 | if `arg1` is between `arg2` and `arg3` (either order): `arg0 = arg4` (`0x318e0c`) |
| 23 | `Select` | 5 | `arg0 = arg1 == arg2 ? arg3 : arg4` (`0x318f64`) |
| 24 | `SelectRange` | 6 | |
| 25 | `Frame` | 2 | |
| 26, 33, 34 | `Add`, `Multi`, `Div` | 3 | by name: `arg0 = arg1 op arg2` |
| 27–32 | `BranchIfZero` … `BranchIfNotPlus` | 3 | as the jumps |
| 35 | (no symbol, `0x304df0`), `sqb.py`: `Base35` | 1 | |
| 36–38 | `Nop` | 4, 2, 2 | |

The root scripts use 14 of these and the PwkScripts use 9. 25 of the 39
are never used.

### RootEvent (root table 4)

123 of the 125 are used; only 32 and 33 aren't. Commands 16–93 and 109–124 have
symbols, and `sqb.py` shortens them (`ScheCallbackCommand_X` → `Sche.X`,
`PwkCallbackCommand_X` → `Pwk.X`, `fcEuroDummyCommand_X` → `Dummy.X`,
`fcEuroSndMng_X` → `Snd.X`, `EventCallbackCommand_X` → `Event.X`,
`BgmCallbackCommand_Play` → `Bgm.Play`, and the two texture callbacks):

| Cmds | Group |
|---|---|
| 16–45 | `Sche.*`: calendar and schedule (Initialize, YearStart … TurnEnd, MatchStart/Branch/End, VS mode, demo match) |
| 46 | `Bgm.Play`, `arg1` = track |
| 47–84 | `Pwk.*`: game data (create, read/free the save work file, new game, year and month start/end, game-over checks, the `Bring_*` callbacks) |
| 85–90, 113–117 | `Dummy.*`: skip checks, launcher and demo flags |
| 91–93 | `Snd.*`: sound setup and port |
| 109–112 | resident and edit-face textures |
| 118–124 | `Event.*`: run the event system at year/month/turn start and end and at menu end |

The 31 without a symbol are named in `sqb.py` after what they call. These
names are descriptive, not symbols:

| Cmd | `sqb.py` name | Calls (confirmed by address unless marked) |
|---|---|---|
| 0 | `Module.Start` | `fcEuroModule_Entry` after looking up module `arg1` (wild card aware), `0x10b198`. `arg2` is passed on (**empirical**: `PlayAcrobata` gets scene numbers 0, 1, 11, 12) |
| 1, 2 | `Module.Wait`, `Module.GetBranch` | `CFcEuro_ModuleController::Wait` / `GetBranch` for module `arg1` |
| 3, 4 | `Module.Activate`, `Module.Deactivate` | `SetActive(1)` (`0x10b500`), `SetActive(0)` (`0x10b588`) |
| 5, 6 | `Module.Delete`, `Module.Get` | `fcEuroModule_Delete`, `GetModule` |
| 7, 8 | `SeqSub.Create`, `SeqSub.Wait` | `new FC_EURO_EVCOM::CFcEuro_SeqSub`; `Wait` + `GetBranch`. **Empirical**: `arg1` is an `SQBFILENAME` id, the root script run as a sub-sequence (12 `RootLauncherSeq` from the main script, 13 `RootEventSeq` 21 times) |
| 9 | `Root9` | a vtable `+0x40` call on the object in `arg1`. It always follows `SeqSub.Wait` on the same handle, so it probably deletes the sub-sequence (**empirical**) |
| 10–12 | `FileRsrc.Entry`, `.Get`, `.Delete` | `fcEuroRsrc_EntryResource` / `GetResource` / `DeleteResource` of file resource `arg1` |
| 13 | `Root13` | `0x10aea8`, sets `arg0` to 0 or 1 |
| 14 | `SetGameMode` | `fcEuroRootTask_SetGameMode` |
| 15 | `WaitFrames` | counts `arg1` frames down in `0x34dadc`, returning 2 until it reaches 0 |
| 94–96 | `MsgRsrc.Entry`, `.SetupGlobal`, `.Delete` | message resources; 95 calls `fcEuroRootTask_SetupGlobalMessageCategory` |
| 97 | `ResetFontSystem` | `etc::ResetFontSystem` |
| 98, 99 | `PlayerList.Effective98/99` | `CStationaryPlayerListManager::SetEffective` (which is on and which off isn't traced) |
| 100, 101 | `TutorialHelp.Effective100/101` | `CTutorialHelpManager::SetEffective` |
| 102, 103 | `TopBar102/103` | `WP::GetTopBarTask`, `GetKeyHelpTask` |
| 104 | `TopBar.SetModeType` | `CTopBar::SetModeType` |
| 105 | `Bg.ChangeNowLoading` | `SimRoot_FunctionNowLoadingON`, then `CBackgroundManager::change` to background 13 |
| 106 | `Bg.WaitNowLoadingOff` | waits for `isChangeEnd`, then `NowLoadingOFF` |
| 107 | `Bg.Change18` | `CBackgroundManager::change` to background 18 and wait |
| 108 | `Bg.Rollback` | `CBackgroundManager::rollback` and wait |

`sqb.py dis` notes the module name after every `Module.*` command and
the script name after `SeqSub.Create`. For example, the start of
`RootMainSeq.sqb` is the boot sequence:

```
  01f0  4:0   Module.Start                 m3[0], k30, 0  ; module SelectVideoMode
  0240  4:0   Module.Start                 m3[0], k29, 0  ; module SelectLanguage
  0320  4:0   Module.Start                 m3[0], k65, 0  ; module BootCheck
  0388  4:0   Module.Start                 m3[0], k44, 0  ; module Logo
  0458  4:0   Module.Start                 m3[0], k45, 0  ; module Title
```

### Param (PwkScript table 4)

None of the 30 have a symbol. `sqb.py` names them after what they call;
the remaining ones are numbered:

| Cmd | `sqb.py` name | argc | Calls |
|---|---|---|---|
| 0 | `Table.Get` | 3 | `arg0` = element `arg2` of `SQT1` table `arg1` (`GetTable`, `0x304f10`) |
| 1 | `Table.Get2D` | 4 | `SQT1` table `arg1`, two indices |
| 2, 3 | `Pinfo.Get2`, `Pinfo.Get3` | 2 | `pwkEdit::GetValIdAdr` on the script's player (`PwkScript::GetPinfo`), field `arg1` |
| 4, 6 | `Pinfo.Set4`, `Pinfo.Set6` | 3, 4 | `SetValIdAdr` on the player |
| 5 | `Pinfo.GetExp5` | 3 | `GetValIdAdr`, then `plMisc_AbilLv2Exp` |
| 9, 10 | `AbilExp2Lv`, `AbilLv2Exp` | 2, 3 | `plMisc_AbilExp2Lv` / `plMisc_AbilLv2Exp` |
| 11, 12 | `Edit.GetTotal`, `Edit.SetTotal` | 2, 3 | `pwkEdit::GetValTotalTree` / `SetValTotalTree` |
| 13 | `Rand` | 2 | `fcEuroRand_Get0toI` |
| 14 | `RunScript` | 3 | `PwkScript::RunScript`: another script |
| 15, 16 | `Table15`, `Table16` | 3, 4 | read `SQT1` tables |
| 17, 18 | `Table.Rand17`, `Table.Rand18` | 3, 4 | read `SQT1` tables and `fcEuroRand_Get0toI` |
| 19, 20 | `Pinfo.Apos2Pos`, `Pinfo.Apos2Epos` | 1 | `plMisc_Apos2Pos` / `Apos2Epos` on the player |
| 21, 25, 29 | `Pinfo21`, `Minfo25`, `Sinfo29` | 1–2 | touch the script's player / manager / scout record |
| 22–24 | `Minfo.Get22/23`, `Minfo.Set24` | 2, 2, 3 | as 2–4, on the manager (`GetMinfo`) |
| 26–28 | `Sinfo.Get26/27`, `Sinfo.Set28` | 2, 2, 3 | as 2–4, on the scout (`GetSinfo`) |
| 7, 8 | `Param7`, `Param8` | 3 | read two arguments; not traced |

**Confirmed.** `Param::PwkScript::RunScript` (`0x256e60`) is how the game
runs these scripts. It sets the command table, creates a sequence for the
script, and writes the caller's 11 argument words to global memory
`g[14]`–`g[24]` (`SetArgInt` with type 6, index `0xe + i`, `0x256ef0`). It
then sets the player, manager and scout records, runs the script, and reads
the result from `g[13]` (`0x256f94`).

## Global memory (`GLOBALMEMORY.TBB`)

**Confirmed.** `etc::GetGlobalMemoryInfo` (`0x14a488`) uses table 0 as
`size >> 4` records of 16 bytes: `{u32 type, s32 value, s32 min, s32 max}`.
`GetGlobalMemory`/`SetGlobalMemory` (`0x1fdce8`/`0x1fdd38`) copy whole
records. Argument type 6 reads `value` when `type` is 0.

**Empirical.** All 25 records have type 0. `g[0]` and `g[7]` start at 2004
(the first season; `g[7]` has max 2104). `g[1]` is 7 (1–31), `g[5]` 0
(0–12) and `g[6]` 7 (0–31), which may be a day and a month (not
checked). `g[13]` is a PwkScript's result and `g[14]`–`g[24]` its
arguments (**confirmed**, `RunScript` above; `PinfoPoint` reads
`g[14]`–`g[17]` and writes `g[13]`). Run
`python SRC/sqb.py globals DAT/SEQ/GLOBALMEMORY.TBB` to list them.

## What doesn't decode

`sqb.py info` reports two `!!` lines. Both are dated 2004, and neither is
listed in `SQBFILENAME.TBB` or named in the code:

- `INFORMATION.SQB` uses table 2 (Window) commands such as `2:43`, inside
  the Window table's count of 44. That table is only a placeholder in the
  retail executable, so this script can't run there.
- `CHECKCLUBEDIT.SQB` uses table 3 and a table 4 whose argument counts
  differ from RootEvent (`4:0` takes 2 arguments, not 3). It matches neither
  set. The `CheckClubEdit` module (7) in `CEDITPRG.REL` doesn't load it by
  name.

## Counts

`python SRC/sqb.py info DAT/SEQ DAT/PARAM`:

| | Scripts | Commands | Labels |
|---|---|---|---|
| root set | 16 (15 `Root*Seq`, `A001`) | 1,324 | 135 |
| PwkScript set | 25 (24 pack entries, `SEQ/PINFOPOINT.SQB`) | 982 | 67 |
| neither | 2 | | |

The 25 PwkScript files hold 68 `SQT1` tables. Every one of the 41 scripts
that decodes ends exactly at the end of its table. Every argument has a
valid type and index, and every label is defined once. `A001` uses only
Base commands, so it decodes under both sets. `info` reports it under the
root set, which is tried first.

## Still unknown

- What `SQT1 +0x10` (the flag) does, and the exact indexing of `Table15`,
  `Table16`, `Table.Rand17/18` and `Table.Get2D`.
- Base 35, root `Root9` and `Root13`, Param 7, 8, 21, 25 and 29. Also which
  of 98/99 and 100/101 turns the feature on.
- What `BranchIf` does differently from `JumpIf`.
- The command sets `INFORMATION.SQB` and `CHECKCLUBEDIT.SQB` were written
  for.
- `INFORMATION.WPX`.

## Tool

```bash
python SRC/sqb.py info    DAT/SEQ DAT/PARAM            # check every script
python SRC/sqb.py dis     DAT/SEQ/ROOTMAINSEQ.SQB      # listing with labels and module names
python SRC/sqb.py dis     "DAT/PARAM/PSCCOMMON.PAC#PscCommon_PinfoPoint.sqb"
python SRC/sqb.py names   DAT/SEQ/SQBFILENAME.TBB      # script ids
python SRC/sqb.py globals DAT/SEQ/GLOBALMEMORY.TBB     # global memory records
python SRC/sqb.py roundtrip DAT/SEQ DAT/PARAM          # re-encode all 41 scripts byte for byte
python SRC/sqb.py setcmd  DAT/SEQ/ROOTMAINSEQ.SQB out/ROOTMAINSEQ.SQB 0x98 0:27
```

`setcmd` is a minimal writer. It swaps one command for another with the
same argument count, so the file keeps its size and can be patched onto the
disc with `patch_disc.py`. It re-checks the script's labels before writing.

## Skipping the tutorial (the opening playoffs)

A new career starts with a scripted promotion playoff, with cutscenes:
the club's way into the league (the game has no third division; user
report). `RootClubEditSeq.sqb` runs it after club creation and the first
save, behind a developer switch:

```
  0868  4:88  Dummy.CheckFirstMatchSkip    m3[1]
  0878  0:28  BranchIfNotZero              m3[0], m3[1], L9
  08b0  ...   (L2) Sche.InitializeFirstCheck, YearStart, MonthStart, then the
              turn and match loop (RootEventSeq, RootMatchSeq) until
              Sche.FirstCheck: won -> L8 (MonthEnd, YearEnd, Finalize) -> L9;
              lost -> L6 (cutscene 7, Finalize) and the script ends with m4[2] = 1
  0d18  4:73  Pwk.PromotionEnd             m3[0]       (L9; then the save)
```

**Confirmed** from the code:

| Address | Symbol | What it shows |
|---|---|---|
| `0x108d20` | `fcEuroDummyCommand_CheckFirstMatchSkip` (command 88) | writes 1 when the word at `0x34d430` is 1, else 0. It is 0 on the disc |
| `0x108d98` | `fcEuroDummyCommand_CheckClubEditSkip` (command 89) | when the word at `0x34d434` is 1: `pwkLg_Init(0)`, `ScheCallback_ProcPromotion`, and writes 1; else writes 0. It is 0 on the disc |
| `0x1131c8` | `ScheCallback_ProcPromotion` | enters the club in last season's records of its competitions (`pwkRec_SetPastRecordLastTeamOne`). Called only by command 89 and by `Sche.FirstCheck` (`0x114174`) after the playoffs |
| `0x1114c0` | `Pwk.PromotionEnd` (command 73) | `pwkOteam_InitNonresident` and `pwkRec_Promote` only, not the club's own promotion |

Command 89 is also used by `RootMainSeq.sqb` at `0x6d8` (non-zero skips
club creation) and by `RootYearStartSeq.sqb` at `0x30` (non-zero skips
the year start). So setting `0x34d430` alone would skip the playoffs
without promoting the club, and setting `0x34d434` alone would also skip
club creation and every year start.

**The patch** (four bytes, plus the six sponsor bytes and the status
call described [below](#why-the-playoff-sponsors-stayed); `python
SRC/patch_disc.py patch <disc> <out> ... --skip-tutorial` writes it, on a
whole disc image):

| File | Change |
|---|---|
| `SLES_541.51` `0x34d434` (file offset `0x24e434`) | 0 → 1 |
| `ROOTCLUBEDITSEQ.SQB` `0x868` | `4:88` → `4:89`: promote, then branch to `L9` |
| `ROOTMAINSEQ.SQB` `0x6d8` | `4:89` → `4:88`, which writes 0: club creation stays |
| `ROOTYEARSTARTSEQ.SQB` `0x30` | `4:89` → `4:88`: year starts stay |

```bash
python SRC/sqb.py setcmd DAT/SEQ/ROOTCLUBEDITSEQ.SQB out/ROOTCLUBEDITSEQ.SQB 0x868 4:89
python SRC/sqb.py setcmd DAT/SEQ/ROOTMAINSEQ.SQB out/ROOTMAINSEQ.SQB 0x6d8 4:88
python SRC/sqb.py setcmd DAT/SEQ/ROOTYEARSTARTSEQ.SQB out/ROOTYEARSTARTSEQ.SQB 0x30 4:88
```

The skip route leaves out what the playoff route runs between `L2` and
`L9` (the schedule's first year, month and turn steps, and their ends),
as the developers' own switch does. `pwkLg_Init(0)` names league 0
(England), so other leagues may not come out right.

**Tested in PCSX2** (England): club creation ran as usual, the playoffs
were skipped, and the career went on to 2006–07 Week 1 Mid-Week July with
the season's Sponsor contract screen. But the sponsors weren't right: only
the main sponsor changed, and the supplier and the four sub-sponsors were
left as they were. **User report:** those are the club's sponsors during
the playoffs (main sponsor Fosty Misty, supplier Doclla, four
sub-sponsors). In a normal career they end with the playoffs: the first
sponsor screen lets you sign the sub-sponsors, and the supplier becomes
Egamucho on a random 1–3 year contract.

### Why the playoff sponsors stayed

The club's sponsors are 14 slots of `0x14` bytes at `+0x11cc4` in pwork
task 1: slot 0 is the main sponsor, slots 1–12 the sub-sponsors, slot 13
the supplier. **Confirmed** from the code:

| Address | Symbol | What it shows |
|---|---|---|
| `0x257200` | (called by `pwkSponsor_Initialize`, from `PwkCallbackCommand_NewGame` `0x110abc`) | copies 6 records of `0x14` bytes from the table at `0x3994a8` into the slots. Byte `+6` of a record picks the slot: `0xff` main, `0xfe` next free sub-slot, `0xfc` supplier |
| `0x113608` | `ScheCallbackCommand_YearStart` (`Sche.YearStart`, command 18) | calls `pwkSponsor_UpdateStatus` |
| `SIMPRG.REL 0x16af80` | `pwkSponsor_UpdateStatus` | adds 1 to every slot's `+4` (years served) |
| `SIMPRG.REL 0x16b580` | `pwkSponsor_UpdateStatus` | then clears every slot whose `+5` (contract length) is less than `+4` |
| `SIMPRG.REL 0x16b878` | (signs an offer) | a new contract starts at `+4` = 1, with the offer's length in `+5` |

The table at `0x3994a8` (sponsor ids are message ids of category 10000):

| Record | Sponsor | Slot | Years served | Length |
|---|---|---|---|---|
| 0 | 193 Fostymisty | main | 0 | 1 |
| 1–4 | 184, 199, 187, 198 | sub | 0 | 1 |
| 5 | 212 Doclla | supplier | 0 | 2 |

The playoff route runs `Sche.YearStart` twice before the first Sponsor
screen: once in `RootClubEditSeq.sqb` (`0x8d0`) and once for the season
(`RootMainSeq.sqb` `0xc70`). That takes the main and sub-sponsors to 2
years served against a length of 1, so they end. The skip route runs only
the second, so they reach 1 and stay.

`--skip-tutorial` now also starts the six records one year in (`+4` = 1,
6 bytes at `0x3994ac` + `0x14`·*n*). Only `0x257200` reads the table.
TV contracts aren't affected: `pwkTv_UpdateStatus` (`SIMPRG.REL
0x164598`) does nothing while `pwkGen_Keika` (the year minus 2006) is 0
or less.

**Tested in PCSX2** with the 6-byte change (England): the first Sponsor
screen let the user sign a new main sponsor (Biassenn) and four new
sub-sponsors. The supplier was still Doclla. A second test disc also
started Doclla two years in, so its contract ended at the season's year
start, and the screen showed Doclla again: the game signed it anew. So
the supplier is chosen, not left over. The Sponsor module's setup
(`SIMPRG.REL 0xc49c0`) signs an offer by itself when `pwkGen_Keika` is 0
or less (`0xc49e0`–`0xc49f0`).

**User report:** in a normal career Egamucho is the supplier at the first
Sponsor screen, so Doclla is replaced in year 1. (EVENT 338, timing 16 in
season 2, has Jane say the supplier contract "ends soon", and the manual
says other suppliers become available after the first year; neither
contradicts this.)

### The supplier and the club's status

A sponsor qualifies by conditions in its record. The sponsor database is
213 records of `0x48` bytes at `SIMPRG.REL 0x23d978`, indexed by sponsor
id (`plSponsor_GetDb`, `0x160dc0`); ids 206–212 have kind 3 at `+4`, the
suppliers. **Confirmed** from the code:

| Address | Symbol | What it shows |
|---|---|---|
| `SIMPRG.REL 0x169818` | (candidate filter) | a condition is `{u8 kind, u16 threshold, u16 argument}` at `+0x1c`/`+0x1e`/`+0x20` (a second at `+0x22`, more from `+0x28`). The kind picks a function from the table at `0x1da458`; it writes a value to `0x2494a0`, and the condition holds when value ≥ threshold (≤ for kinds `0x11`, `0x1a`, `0x1b`). The supplier list (second argument 1) takes only kinds `0x17` and up |
| `SIMPRG.REL 0x161c28` | (kind `0x18`) | the value is `pwkTeam_Status()` |
| `SIMPRG.REL 0x162090` | (kinds `0x16`, `0x17`) | the value is 1: always holds |
| `0x26e2f0` | `pwkTeam_Status` | the club's status, u16 at `+0x1126a` in pwork task 1 |
| `0x26dbb8` | `pwkTeam_StatusChange` | adds to the status, capped by the status rank (`+0x11264`, table at `0x555150`) |
| `0x26e2a0` | `pwkTeam_YearEndCheck` (from `Sche.YearEnd`) | raises the status rank on a division change, then adds 500 (`0x26e2c4`: 500.0 to `0x26dd18`, which calls `pwkTeam_StatusChange`) |

Egamucho (211) has condition kind `0x18`, threshold 500: status ≥ 500.
Doclla (212) has kind `0x17`, which always holds, so it is the fallback.
Both are tier 6 (`+8`) with no fee.

**Tested in PCSX2** (England, status read over PINE): with the original
disc, status was 0 through the playoffs (dated June 2005) and became 500
at their end, just before the date moved to July 2006: that is the
playoffs' `Sche.YearEnd` (`RootClubEditSeq` `L8`). At the first Sponsor
screen: status 500, status rank 7, supplier Egamucho. With the skip disc,
status stayed 0 and the supplier stayed Doclla (shown as 2/2 years: the
playoffs' extra year start counts as its first year).

**The fix:** `--skip-tutorial` also rewrites `Dummy.CheckClubEditSkip`
(9 words at `0x108dac`). The flag test goes (a skip disc always passes
it), which leaves room to save `$ra` first and call, in the normal
route's order, `pwkLg_Init(0)`, `ScheCallback_ProcPromotion` and then
`pwkTeam_YearEndCheck`. **Tested in PCSX2:** status became 500 right
after club creation, and the first Sponsor screen had Egamucho as
supplier (on a 1-year contract; the term is random).

The rest of the playoffs' `Sche.YearEnd` (club-rank year end,
`pwkTeam_ChangePop_Year`) and `Sche.MonthEnd` still don't run on a skip
disc. Nothing has shown a difference from them yet.

## The developer launcher

**Confirmed** from the code: `Dummy.CheckLauncher` (`0x109270`) always
writes 1 to its argument 0. `RootMainSeq.sqb` runs it at `0x88` and at
`0x98` branches past the launcher when the value is non-zero:

```
  0088  4:113 Dummy.CheckLauncher          m3[1]
  0098  0:28  BranchIfNotZero              m3[0], m3[1], L0
  00d0  4:7   SeqSub.Create                m3[2], k12  ; RootLauncherSeq.sqb
```

So in the retail game the launcher never runs. `RootLauncherSeq.sqb`
(script 12) loads file resource 7, which is `testprg.rel` in the overlay
table ([`SNR2_FORMAT.md`](SNR2_FORMAT.md#which-overlay-the-game-loads)),
and starts module 69 (Launcher). What happens next depends on the
launcher's result *n* (`Module.GetBranch`):

| *n* | Label | Effect |
|---|---|---|
| 1, 101 | `L1` | leave the launcher |
| 2–100 | `L2` | read the player database, make a new game (`Pwk.NewGame`, `ClubEditEnd`), start SimRoot, then test module `71 + n − 2` |
| 102 and up | `L3` | make a new game, then start module `71 + n − 2` on its own |

After each test module, the script goes back to the launcher. Once the
launcher is left, the main script continues with the normal boot at `L0`.

`setcmd ... 0x98 0:27` (`BranchIfZero`) changes 1 byte and sends the boot
into the launcher.

**Tested in PCSX2** (the 1-byte patch written with `patch_disc.py`): the
game boots into a developer menu instead of the video-mode screen. It has
two tabs, `simprg` and `gameprg`.

The `simprg` tab lists MAIN GAME START and then 59 entries, 10 to a page.
Entry *i* after MAIN GAME START is module `70 + i`. That is the launcher
script's `L2` path (result *n* = *i* + 1, module `71 + n − 2`). The
screenshots and the module tables in
[`SNR2_FORMAT.md`](SNR2_FORMAT.md#which-overlay-the-game-loads) agree
wherever both name a module: 89 SugioTest, 93 SeasonEndTest, 104
CharacterViewer, 107 AcrobataViewer, 113 CseViewer, 124 Goods, 125 Hdd,
126 HddUtil, 127 BootCheck, 128 UniformViewer and 129 TalkCheck. The
overlays also match: 85, 87, 88 and 91 are in `CEDITPRG` (club edit),
and 105 and 115 in `YRSTPRG` (contracts, player edit).

| Modules | Entries |
|---|---|
| 71–79 | BPINFO CHECK, 3D TEST, MODEL VIEWER, CSE TEST, BG CONTROL, INOUE TEST, SAKAUE TEST, SATO TEST, SIDE MENU |
| 80–89 | IWASAKI TEST, SPANVERSE TEST, EMBLEM EDIT TEST, PERSONAL AFFAIRS, YAMAZAKI TEST, CLUB EDIT MENU, UNIFORM EDIT, EMBLEM EDIT, FLAG EDIT, SUGIO TEST |
| 90–99 | TOUMURA TEST, INITIAL PERSONNEL AFFAIRS, Talk, SEASON END, MONTH END, MAIL, MATCH RESULT, SCHEDULE, SCOUTING MENU, PERSONNEL AFFAIRS MENU |
| 100–109 | NEWS, SPRITE TEST, TACTICS, TRAINING, CHARACTER VIEWER, PLAYER CONTRACT, NEWS VIEWER, ACROBATA VIEWER, MEMORYCARD UTILITY, MAIL VIEWER |
| 110–119 | GAME INCOME, SELECT UNIFORM, SPONSOR, CSE TEST 2, HAYASI TEST, PLAYER EDIT, BG LIGHT TEST, TICKET SET TEST, TICKET SET, MANA PLAN TEST |
| 120–129 | MANA PLAN, TV SELECT, ARRAY BLOCK TEST, COLOR TEST, GOODS, HDD INSTALL, HDD UTIL(FORMATER), BOOT CHECK, Uniform Viewer, Talk Check |

The `gameprg` tab lists MAIN GAME START, STADIUM VIEWER MK2, GAME and BC
TEST. This fits the script's other branch, though it isn't confirmed from
the launcher's code. Result 101 leaves like 1 does. Results 102–104 take
the `L3` path, which loads file resource 1 (`gameprg.rel`) and starts
modules 171 StadiumViewer, 172 Game and 173 (`ShimizuTest` in the setup
function's name, "BC TEST" in the menu).

`sqb.py` uses these names for modules 71–129 and 171–173.

**Tested in PCSX2**, every entry, in module order. "Hangs" means a black
screen that doesn't respond, which is probably a crash. "Menu test" means
the real game screen, opened on its own with the launcher's new game.

| Module | Entry | What happened |
|---|---|---|
| — | MAIN GAME START | starts the normal game |
| 71 | BPINFO CHECK | the training-ground background and the debug text `CBpinfoCheckModule( return X button ), m_bra` / `0 all=27949 0=18871 1mil=8063`, plus a few garbled characters. The counts match the player database (below) |
| 72 | 3D TEST | hangs |
| 73 | MODEL VIEWER | a shaded test triangle with red and green axis lines. The buttons do nothing |
| 74 | CSE TEST | stays on "NOW LOADING" |
| 75 | BG CONTROL | goes straight back to the launcher |
| 76, 77 | INOUE TEST, SAKAUE TEST | hang. `TESTPRG.REL` names a `SAKAUETEST_MODULE::CNewsTextureTestTask` next to `news_ad.pac` |
| 78 | SATO TEST | **a head viewer** for `FC_EURO_FACEPACK_01` (below). The debug text shows `ID`, `NAME` and `ADD`. IDs run from 0 to 214, and `ADD` is the step for each press |
| 79 | SIDE MENU | hangs |
| 80 | IWASAKI TEST | goes straight back to the launcher |
| 81, 82 | SPANVERSE TEST, EMBLEM EDIT TEST | hang |
| 83 | PERSONAL AFFAIRS | a squad list (Num, Pos, Name, Age, Country), with Num and Pos empty. Choosing any row returns to the launcher. The players are from database IDs 25591–25615 (below) |
| 84 | YAMAZAKI TEST | not recorded |
| 85 | CLUB EDIT MENU | **works** like the real screen: club name, 1st and 2nd kit, emblem and flag. The club is called "CITY_NONE Utd". `CITY_NONE` is message 0 of the city-name categories 961 and 962 (and 100961), in all 7 languages, so the launcher's new game leaves the club with city 0 |
| 86–88 | UNIFORM EDIT, EMBLEM EDIT, FLAG EDIT | **work**: the club edit menu's own sub-screens |
| 89 | SUGIO TEST | a plain teal screen |
| 90 | TOUMURA TEST | hangs |
| 91 | INITIAL PERSONNEL AFFAIRS | goes straight back to the launcher |
| 92–100 | Talk … NEWS | Talk not recorded. SEASON END, MONTH END, MAIL, MATCH RESULT, SCHEDULE, SCOUTING MENU, PERSONNEL AFFAIRS MENU and NEWS are menu tests |
| 101 | SPRITE TEST | hangs |
| 102, 103 | TACTICS, TRAINING | menu tests |
| 104 | CHARACTER VIEWER | **works.** A standing player (training kit) over the training ground, with the debug menu SET / PUSH / BLEND (a motion, e.g. `mendan_Asit_ang_001.snm`), LINK TIME, DO-LINK, DO-BLEND, DO-MIRROR, DO-REVERSE and CHARACTER (Player), and `Play = NULL`, `Play List Num = 0`. Setting CHARACTER to null shows a column of garbled Japanese and `(null)` entries. The motion names are in `DAT/TEST3D/VIEWERPLAYERMOTION.PAC` |
| 105 | PLAYER CONTRACT | hangs |
| 106, 107 | NEWS VIEWER, ACROBATA VIEWER | newspaper menu tests. ACROBATA VIEWER is the newspaper intro at the start of a game |
| 108 | MEMORYCARD UTILITY | hangs |
| 109 | MAIL VIEWER | the e-mail menu test |
| 110 | GAME INCOME | goes straight back to the launcher |
| 111 | SELECT UNIFORM | the shirt-number selection screen |
| 112 | SPONSOR | a sponsor menu test |
| 113 | CSE TEST 2 | a separate news viewer |
| 114 | HAYASI TEST | hangs |
| 115 | PLAYER EDIT | hangs. The user's view: probably the Japanese version's in-game player editor, disabled here, where the European version has the Virtua Pro Football player import instead |
| 116 | BG LIGHT TEST | not recorded |
| 117 | TICKET SET TEST | shows a block of text |
| 118 | TICKET SET | the mid-year competition ticket-price screen, in a loop |
| 119 | MANA PLAN TEST | hangs |
| 120 | MANA PLAN | the management-plan menu test |
| 121 | TV SELECT | the TV-sponsor selection menu test |
| 122 | ARRAY BLOCK TEST | hangs |
| 123 | COLOR TEST | a test pattern: two grey ramps (0–255) and red, green and blue swatches |
| 124 | GOODS | the goods screen test |
| 125, 126 | HDD INSTALL, HDD UTIL(FORMATER) | disabled, probably the Japanese version's hard-drive features |
| 127 | BOOT CHECK | hangs |
| 128 | Uniform Viewer | **works.** A player in a club's kit (Birmingham in the screenshot, `NO : 3`, with the Japanese label `オリジナルチーム` "original team" printed as `âIâèâWâiâïâ`ü[âÇ`), with the kit settings: FP/GK, Home/Away, Sleeve and Pants (Short), Front/Back Number Color [FP]/[GK] (OFF, A8), Collar Type [FP]/[GK] (`l_nml_bdy_01_el`, `l_nml_bdy_08_el`), Pants Type (Right), Pants Number Color (13, A8) and CaptainMark Color (3, 0). The screenshot had a texture pack on, so the textures aren't vanilla |
| 129 | Talk Check | a talk scene with its text garbled (Japanese shown in the European font) |
| 171 | STADIUM VIEWER MK2 | **works.** A menu (CREATE, BUILD, VISIBLE, DRAW_PRIORITY, NODE_CHECK, CLIP_CHECK, AUDIENCE, PROJECTION, FILTER, COLLISION, SAVE, RESET, EXIT). CREATE sets the build parameters: STADIUM_LEVEL, NATION_ID, STAND_LEVEL, TIME_ID (DAY …), WEATHER_ID (FINE …), SEASON_ID, LANDSCAPE_LEVEL, MONTH_ID, TEAM_COLOR1_16/2_16, HOME/AWAY_TEAMCOLOR, HOME/AWAY_SUPPORTER, CIVILIAN_VISITOR (110000 each by default) and ADVERTISE_INDEX. BUILD then shows the stadium, with crowd and adverts, and lets you move the camera |
| 172, 173 | GAME, BC TEST | hang |

The four viewers that work are the useful ones for modding:
- **STADIUM VIEWER MK2**: the stadium build request of
  [`STADIUM_DIR.md`](STADIUM_DIR.md).
- **Uniform Viewer**: the kit fields behind `UNIFORM_LIST`, `UNIFORM_GK`
  and `COLOR_TBL` ([`PLAYER_DIR.md`](PLAYER_DIR.md)), with collar model
  names like `l_nml_bdy_01_el`.
- **CHARACTER VIEWER**: player motions by name.
- **SATO TEST**: the event-character heads.

SATO TEST's names come from a table in `TESTPRG.REL` at `0x21d18`, found
through the pointer to `REFREE_01` (`snr2.py xref ... 291e0`). Each 8-byte
row is `{char *name, u32 female}`, one row per ID:

| IDs | Names (female flag) |
|---|---|
| 0–19 | `REFREE_01`–`20` |
| 20–35 | `FLAGMAN_01`–`16` |
| 36–41 | `ANNOUNCER_M_01`–`04`, `ANNOUNCER_F_01`–`02` (1) |
| 42–121 | `SUPPORTER_M_01`–`50`, `SUPPORTER_F_01`–`30` (1) |
| 122–131 | `AGENT_01`–`10` |
| 132–135 | `COACH_01`–`04` |
| 136–139 | `SALESMAN_M_01`–`02`, `SALESMAN_F_01`–`02` (1) |
| 140–159 | `COMMISSIONER_01`–`20` |
| 160–169 | `REPORTER_01`–`05`, `CAMERAMAN_01`–`05` |
| 170–175 | `MANAGER_01`–`06` |
| 176–187 | `VISITOR_M_01`–`06`, `VISITOR_F_01`–`06` (1) |
| 188–191 | no name (null pointer) |
| 192–211 | `STAFF_M_01`–`12`, `STAFF_F_01`–`08` (1) |
| 212–214 | no name |

The flag is 1 on exactly the 40 `_F` names. The viewer's 215 IDs equal
the 215 heads of `FC_EURO_FACEPACK_01`, the event-character pack
([`PLAYER_DIR.md`](PLAYER_DIR.md)), and the screenshots fit the table (ID
10 `REFREE_11`, ID 211 `STAFF_F_08`). ID *n* is pack entry *n*: every head
in the pack carries its own model and texture name, and those names match
this table row by row (`python SRC/packdata.py names
DAT/PLAYER/FC_EURO_FACEPACK_01.HED`). The rows without a name are
`kihon.sno` (188–191, four identical copies) and the untextured test heads
`HUMAN_head_9000/9500/9600.snj` (212–214). The viewer's load code isn't
traced.

PERSONAL AFFAIRS's players belong to a block of 25 English players,
database IDs 25591–25615, with shirts 1–25 and ranks 1–4. None of them is
in a computer club's squad (`initteam.py squads`). The next block, from
25616, is another England squad numbered from shirt 1. **Empirical lead:**
these look like ready-made squads for the player's own club, and the
launcher's new game (`Pwk.NewGame`) gave its club the first English one.

BPINFO CHECK's numbers match the player database (`pbdata.py csv`):
27,949 is the last player index, 18,871 players have money 0, and 8,063
have money between 1 and 9,999. The other 1,016 have 10,000 or more, and
the three counts add up to 27,950. See
[`PBDATA_FORMAT.md`](PBDATA_FORMAT.md) for what the "1mil" label suggests.

The stadium viewer's CREATE fields look like the stadium build request of
[`STADIUM_DIR.md`](STADIUM_DIR.md): level, stand level, time of day,
weather, season and month, crowd sizes and adverts. That makes it a way to
work out the open request fields there.
