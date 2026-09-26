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
```
