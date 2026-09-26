"""SQB sequencer script reader for Let's Make a Soccer Team! (PS2).

A .sqb file is a TBB1 container (see DOC/TBB_FORMAT.md) whose tables are
SQB1 scripts: {'SQB1', u32 data_offset 0x10, u32 size, u32 0} and then
`size` bytes of commands. The game's sequencer (CSeqController in
SLES_541.51) runs them one command per step. See DOC/SQB_FORMAT.md.
PwkScript files also carry SQT1 data tables {'SQT1', 0x20, size, element
size, flag, rows, columns, 0}, read by the Param table commands
(CSeqController::GetTable 0x2007f8).

  command    {u32 table, u32 cmd} + argc x {u32 type, s32 value}
             argc comes from the command table (UpdateCommand 0x1ffa90
             steps by (argc + 1) * 8). Argument 0 is where the result goes.
  arg type   0, 7 literal; 2 and 3 two 50-word controller memories (+0x08,
             +0xd0); 4 and 5 two 10-word ones (+0x198, +0x1c0); 6 a
             GlobalMemory.tbb record (GetArgInt 0x1ffdd8). 1 and 8 fail.
  labels     base command 2 marks a label at the next command, base
             command 3 (Function) at itself; the label id is argument 1,
             below 200, and must be unique (ResolveLabel 0x1ffbf0). Jumps
             and branches take the label in argument 2, Call in argument 1.

Two command sets run these scripts, each a COMMAND_INFO array of 5 tables
{u32 *argc, fn *cb, u32 count, u32 0}:

  root  Seq_fc_euro::pCommandInfoTbl 0x5668b0, registered at 0x10e750:
        0 Base (39), 1 Scene (7, all Command_Nop), 2 Window (placeholder),
        3 empty, 4 RootEvent (125). Runs the SEQ/Root*Seq.sqb scripts, loaded
        by id from SqbFilename.tbb (0x14a220).
  pwk   Param::PwkScript, 0x552df0 (SetCommandTable 0x256e00): 0 Base,
        1-3 empty, 4 Param (30). Runs the PARAM/PSC*.PAC scripts.

`info` decodes every SQB1 table of every .SQB file and every .sqb entry of a
BINPAC pack under the given paths, with the set that fits, and checks each
command, argument type, memory index and label. A script that decodes under
neither set is a problem (`!!`); so is a missing or repeated label.

Usage:
    python sqb.py info    <file | dir> ...        # check every script
    python sqb.py dis     <file.SQB | pack.PAC#entry.sqb> [root|pwk]
    python sqb.py names   <SQBFILENAME.TBB>       # script id -> file
    python sqb.py globals <GLOBALMEMORY.TBB>      # {type, value, min, max}
"""
import os
import struct
import sys

import pac

TBB_MAGIC = b"TBB1"
SQB_MAGIC = b"SQB1"
SQT_MAGIC = b"SQT1"
MAX_LABELS = 200            # ResolveLabel 0x1ffcdc: sltiu 0xc8
LITERAL = (0, 7)
# Argument type -> number of words it can index (Initialize 0x1ff780 clears
# 0xc8, 0xc8, 0x28 and 0x28 bytes). Type 6's size comes from GlobalMemory.tbb.
MEMORY = {2: 50, 3: 50, 4: 10, 5: 10}
GLOBAL = 6
GLOBAL_RECORDS = 25         # GlobalMemory.tbb: 0x190 bytes / 16 (0x14a4e4)

LABEL, FUNCTION, CALL = 2, 3, 5
JUMPS = set(range(9, 15)) | set(range(27, 33))

# Table 0, Seq_fc_euro$pdwCmdParamNumBase 0x3a7720 / ppfnCommandCbBase
# 0x3a77c0 (count 39). Names are the Seq::Command_* symbols, except 2, which
# is Command_Nop but marks a label.
BASE = list(zip((
    "CreateSequenceController", "DeleteSequenceController", "Label",
    "Function", "Return", "Call", "Return", "GetControllerMemory",
    "SetControllerMemory", "JumpIfZero", "JumpIfNotZero", "JumpIfMinus",
    "JumpIfNotMinus", "JumpIfPlus", "JumpIfNotPlus", "CheckController",
    "FindController", "End", "EndLoop", "Sub", "Set", "SetIf", "SetIfRange",
    "Select", "SelectRange", "Frame", "Add", "BranchIfZero",
    "BranchIfNotZero", "BranchIfMinus", "BranchIfNotMinus", "BranchIfPlus",
    "BranchIfNotPlus", "Multi", "Div", "Base35", "Nop", "Nop", "Nop"),
    (2, 2, 2, 2, 1, 2, 1, 3, 4, 3, 3, 3, 3, 3, 3, 2, 3, 1, 1, 3, 2, 4, 5, 5,
     6, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 4, 2, 2)))

# Table 1, pdwCmdParamNumScene 0x3a79c8 / ppfnCommandCbScene 0x3a79e8: all
# seven are Command_Nop.
SCENE = [("Scene%d" % i, n) for i, n in enumerate((3, 3, 3, 3, 2, 3, 3))]

# Table 4, FC_EURO_EVCOM$pdwCmdParamNumRootEvent 0x34daf8 /
# ppfnCommandCbRootEvent 0x34dcf0 (count 125). Symbol names, shortened
# (ScheCallbackCommand_X -> Sche.X, ...); 0-15 and 94-108 have no symbol and
# are named after what they call (DOC/SQB_FORMAT.md).
ROOT_EVENT_NAMES = [
    "Module.Start", "Module.Wait", "Module.GetBranch", "Module.Activate",
    "Module.Deactivate", "Module.Delete", "Module.Get", "SeqSub.Create",
    "SeqSub.Wait", "Root9", "FileRsrc.Entry", "FileRsrc.Get",
    "FileRsrc.Delete", "Root13", "SetGameMode", "WaitFrames",
    "Sche.Initialize", "Sche.Finalize", "Sche.YearStart", "Sche.YearEnd",
    "Sche.MonthStart", "Sche.MonthEnd", "Sche.TurnStart", "Sche.TurnEnd",
    "Sche.MatchStart", "Sche.MatchBranch", "Sche.MatchEnd", "Sche.FirstCheck",
    "Sche.CheckMatchResult", "Sche.CheckDomesticTurnEndEvent",
    "Sche.CheckEuropeTurnEndEvent", "Sche.GetYear",
    "Sche.CreateGiForFirstMatch", "Sche.DeleteGiForFirstMatch",
    "Sche.InitializeFirstCheck", "Sche.CheckSeasonStart",
    "Sche.InitializeContinue", "Sche.Initialize_VsMode", "Sche.Check_VsMode",
    "Sche.EndMonthStart", "Sche.CalendarEnd", "Sche.IsVsMode",
    "Sche.EntryDemoMatch", "Sche.SetDemoMatchCurrent", "Sche.FinalizeOneMatch",
    "Sche.PreBackMatch", "Bgm.Play", "Pwk.Create", "Pwk.Delete",
    "Pwk.ReadPwkFile", "Pwk.WaitPwkFile", "Pwk.FreePwkFile", "Pwk.NewGame",
    "Pwk.ClubEditEnd", "Pwk.StartYearEnd", "Pwk.EndYearEnd",
    "Pwk.StartMonthEnd", "Pwk.EndMonthEnd", "Pwk.BpDataReadFile",
    "Pwk.BpDataWaitFile", "Pwk.BpDataFreeFile", "Pwk.CheckGameOverMember",
    "Pwk.CheckGameOverSikin", "Pwk.YearStartFirstHalf",
    "Pwk.YearStartDischarge", "Pwk.YearStartJoin", "Pwk.YearStartSecondHalf",
    "Pwk.RuntimeInitialize", "Pwk.StartMonthStart", "Pwk.TurnStart",
    "Pwk.GetGameIfData", "Pwk.VS_Start", "Pwk.VS_End", "Pwk.PromotionEnd",
    "Pwk.GetAllGameIfData", "Pwk.FreeGameIfData", "Pwk.CheckPlayerEdit",
    "Pwk.CheckTV", "Pwk.MenuIn", "Pwk.Bring_Month_First_CallBack",
    "Pwk.Bring_Year_First_CallBack", "Pwk.Bring_Match_Before_CallBack",
    "Pwk.Bring_Match_After_CallBack", "Pwk.Bring_Week_First_CallBack",
    "Pwk.Bring_Week_End_CallBack", "Dummy.CheckTurnSkip",
    "Dummy.CheckYearMonthTurnSkip", "Dummy.CheckMatchSkip",
    "Dummy.CheckFirstMatchSkip", "Dummy.CheckClubEditSkip",
    "Dummy.GetFirstMatchCount", "Snd.RequestSetup", "Snd.WaitSetup",
    "Snd.FreePort", "MsgRsrc.Entry", "MsgRsrc.SetupGlobal", "MsgRsrc.Delete",
    "ResetFontSystem", "PlayerList.Effective98", "PlayerList.Effective99",
    "TutorialHelp.Effective100", "TutorialHelp.Effective101", "TopBar102",
    "TopBar103", "TopBar.SetModeType", "Bg.ChangeNowLoading",
    "Bg.WaitNowLoadingOff", "Bg.Change18", "Bg.Rollback",
    "ResidentTexture.Create", "ResidentTexture.Delete",
    "EditFaceTexture.Create", "EditFaceTexture.Delete", "Dummy.CheckLauncher",
    "Dummy.SetLauncherFlag", "Dummy.CheckDemo", "Dummy.SetDemoFlag",
    "Dummy.CheckMatchMenuIn", "Event.YearStart", "Event.MonthStart",
    "Event.YearEnd", "Event.MonthEnd", "Event.TurnStart", "Event.TurnEnd",
    "Event.MenuEnd"]
ROOT_EVENT = list(zip(ROOT_EVENT_NAMES, (
    3, 2, 2, 2, 2, 2, 3, 2, 2, 2, 2, 2, 2, 2, 2, 2) + (1,) * 30 +
    (2, 1, 1, 2, 2, 2) + (1,) * 39 + (2, 2, 2) + (1,) * 10 +
    (2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1)))

# Table 4 of the PwkScript set, FC_EURO_PARAM$pdwCmdParamNumParam 0x3a7860 /
# ppfnCommandCbParam 0x3a78d8 (count 30). No symbols; named after what they
# call where that is clear (DOC/SQB_FORMAT.md).
PARAM = list(zip((
    "Table.Get", "Table.Get2D", "Pinfo.Get2", "Pinfo.Get3", "Pinfo.Set4",
    "Pinfo.GetExp5", "Pinfo.Set6", "Param7", "Param8", "AbilExp2Lv",
    "AbilLv2Exp", "Edit.GetTotal", "Edit.SetTotal", "Rand", "RunScript",
    "Table15", "Table16", "Table.Rand17", "Table.Rand18", "Pinfo.Apos2Pos",
    "Pinfo.Apos2Epos", "Pinfo21", "Minfo.Get22", "Minfo.Get23", "Minfo.Set24",
    "Minfo25", "Sinfo.Get26", "Sinfo.Get27", "Sinfo.Set28", "Sinfo29"),
    (3, 4, 2, 2, 3, 3, 4, 3, 3, 2, 3, 2, 3, 2, 3, 3, 4, 3, 4, 1, 1, 1, 2, 2,
     3, 2, 2, 2, 3, 2)))

SETS = {
    "root": {0: BASE, 1: SCENE, 4: ROOT_EVENT},
    "pwk": {0: BASE, 4: PARAM},
}


# Module ids for the Module.* commands (argument 1), from the module tables
# in DOC/SNR2_FORMAT.md; 70 is the wild card.
MODULES = dict(enumerate((
    "Dummy", "Dummy", "HomeSelect", "MatchResult", "SelectTeamColor",
    "SelectTeamStyle", "Game", "CheckClubEdit", "Office", "ClubHouse",
    "OwnerRoom", "Information", "BGControl", "SideMenu", "Event",
    "PersonnelAffairsMenu", "OwnerNameEntry", "ClubEditMenu", "EmblemEdit",
    "FlagEdit", "UniformEdit", "TeamNameEntry", "MeetingPlayer",
    "MeetingStaff", "SimRoot", "Practice", "Tactics",
    "InitialPersonnelAffairs", "SelectSecretary", "SelectLanguage",
    "SelectVideoMode", "Talk", "StaffContract", "SeasonEnd", "MonthEnd",
    "MatchMenu", "PlayAcrobata", "ScoutingMenu", "ScoutingMenu", "Schedule",
    "PublicRelations", "News", "Institution", "Mail", "Logo", "Title",
    "PlayerContract", "Load", "Save", "ClubEditBG", "Youth", "SelectCaptain",
    "GameIncome", "PracticeExecute", "SelectUniformNumber", "Sponsor",
    "Account", "Business", "VSModeRegulation", "Option",
    "VSModeScheduleTop", "TicketSet", "Broadcast", "PlayerEdit", "ManaPlan",
    "BootCheck", "ForcedDismissPlayer", "NewGameInstall",
    "CheckActionPlayerData", "Launcher", "WildCard")))
MODULES.update({
    71: "BpinfoCheck", 72: "Test3D", 73: "ModelViewer", 74: "TestCse",
    76: "InoueTest", 77: "SakaueTest", 83: "PersonalAffairs", 89: "SugioTest",
    93: "SeasonEndTest", 104: "CharacterViewer", 107: "AcrobataViewer",
    113: "CseViewer", 124: "Goods", 125: "Hdd", 126: "HddUtil",
    127: "BootCheck", 128: "UniformViewer", 129: "TalkCheck",
    171: "StadiumViewer", 172: "Game", 173: "ShimizuTest"})
MODULE_COMMANDS = range(0, 7)       # table 4: Module.Start .. Module.Get
SEQSUB_COMMANDS = (7,)              # table 4: SeqSub.Create, argument 1


class Command:
    def __init__(self, pos, table, cmd, name, args):
        self.pos, self.table, self.cmd, self.name = pos, table, cmd, name
        self.args = args            # [(type, value)]


def tbb_tables(blob):
    """Offsets of the tables in a TBB1 container. The 2004 files count the
    end of the file as one more table; those offsets are dropped."""
    if blob[:4] != TBB_MAGIC:
        raise ValueError("not a TBB1 container")
    n = struct.unpack_from("<I", blob, 8)[0]
    offs = struct.unpack_from("<%dI" % n, blob, 0x10)
    return [o for o in offs if o < len(blob)], len(offs) - sum(o < len(blob) for o in offs)


def sqb_tables(blob):
    """[(offset, script bytes)] for every SQB1 table of a container, after
    checking that every other table is a well-formed SQT1."""
    out = []
    offs, _ = tbb_tables(blob)
    for o in offs:
        magic, doff, size, _ = struct.unpack_from("<4sIII", blob, o)
        if o + doff + size > len(blob):
            raise ValueError("table at 0x%x runs past the end" % o)
        if magic == SQB_MAGIC:
            out.append((o, blob[o + doff:o + doff + size]))
        elif magic == SQT_MAGIC:
            check_sqt(blob, o)
        else:
            raise ValueError("table at 0x%x is %r" % (o, magic))
    if not out:
        raise ValueError("no SQB1 table")
    return out


def check_sqt(blob, o):
    """SQT1: {magic, 0x20, size, element size, flag, rows, columns, 0}; the
    Param table commands read element size +0xc (1 u8, 2 s16, else u32,
    0x304f90) and the shape +0x14/+0x18 (0x306228)."""
    _, doff, size, elem, flag, rows, cols, zero = struct.unpack_from("<4s7I", blob, o)
    if doff != 0x20 or zero or flag > 1 or elem not in (1, 2, 4):
        raise ValueError("SQT1 at 0x%x has an unexpected header" % o)
    if size != elem * rows * cols:
        raise ValueError("SQT1 at 0x%x: size %d != %d x %d x %d" % (o, size, elem, rows, cols))


def decode(script, cmdset):
    """Decode one script with a command set. Raises ValueError on the first
    command the set doesn't have or if the commands overrun the script."""
    tables = SETS[cmdset]
    out = []
    p = 0
    while p < len(script):
        if p + 8 > len(script):
            raise ValueError("command header cut short at 0x%x" % p)
        table, cmd = struct.unpack_from("<II", script, p)
        if table not in tables or cmd >= len(tables[table]):
            raise ValueError("no command %d:%d at 0x%x" % (table, cmd, p))
        name, argc = tables[table][cmd]
        if p + 8 * (argc + 1) > len(script):
            raise ValueError("%s at 0x%x overruns the script" % (name, p))
        raw = struct.unpack_from("<%di" % (2 * argc), script, p + 8)
        out.append(Command(p, table, cmd, name, list(zip(raw[0::2], raw[1::2]))))
        p += 8 * (argc + 1)
    return out


def label_arg(c):
    """Index of the argument holding a label id, or None."""
    if c.table != 0:
        return None
    if c.cmd in (LABEL, FUNCTION, CALL):
        return 1
    if c.cmd in JUMPS:
        return 2
    return None


def check(cmds):
    """Problems with arguments and labels. Returns (labels, [reasons])."""
    problems = []
    labels = {}
    for c in cmds:
        for i, (t, v) in enumerate(c.args):
            if t in LITERAL:
                continue
            size = MEMORY.get(t, GLOBAL_RECORDS if t == GLOBAL else None)
            if size is None:
                problems.append("0x%04x %s: argument %d has type %d" % (c.pos, c.name, i, t))
            elif not 0 <= v < size:
                problems.append("0x%04x %s: m%d[%d] out of range" % (c.pos, c.name, t, v))
        if c.table == 0 and c.cmd in (LABEL, FUNCTION):
            t, v = c.args[1]
            if t not in LITERAL or not 0 <= v < MAX_LABELS:
                problems.append("0x%04x %s: bad label %d:%d" % (c.pos, c.name, t, v))
            elif v in labels:
                problems.append("0x%04x %s: label %d repeated" % (c.pos, c.name, v))
            else:
                labels[v] = c.pos
    for c in cmds:
        i = label_arg(c)
        if i is None or c.cmd in (LABEL, FUNCTION):
            continue
        t, v = c.args[i]
        if t in LITERAL and v not in labels:
            problems.append("0x%04x %s: label %d not defined" % (c.pos, c.name, v))
    return labels, problems


def fit(blob):
    """(set name, [(offset, commands)]) for the first set that decodes every
    table, or (None, error) if none does."""
    tables = sqb_tables(blob)
    errors = []
    for name in SETS:
        try:
            return name, [(o, decode(s, name)) for o, s in tables]
        except ValueError as e:
            errors.append("%s: %s" % (name, e))
    return None, "; ".join(errors)


def fmt_arg(t, v):
    if t == 0:
        return str(v)
    if t == 7:
        return "k%d" % v
    if t == GLOBAL:
        return "g[%d]" % v
    return "m%d[%d]" % (t, v)


def fmt_command(c):
    li = label_arg(c)
    args = []
    for i, (t, v) in enumerate(c.args):
        args.append("L%d" % v if i == li and t in LITERAL else fmt_arg(t, v))
    return "%-28s %s" % (c.name, ", ".join(args))


def comment(c, script_names):
    """What a literal module or script id refers to, for `dis`."""
    if c.table != 4 or len(c.args) < 2 or c.args[1][0] not in LITERAL:
        return ""
    v = c.args[1][1]
    if c.cmd in MODULE_COMMANDS:
        return "  ; module %s" % MODULES.get(v, "?")
    if c.cmd in SEQSUB_COMMANDS and 0 <= v < len(script_names):
        return "  ; %s" % script_names[v]
    return ""


# --- inputs ------------------------------------------------------------------

def is_script_name(name):
    return name.lower().endswith(".sqb")


def load(spec):
    """Bytes of a script: a file, or `pack.PAC#entry` for a BINPAC entry."""
    path, _, entry = spec.partition("#")
    data = open(path, "rb").read()
    if not entry:
        return data
    hdr = pac.load_header(path)
    for off, size, name, _ in hdr.entries:
        if name == entry:
            return data[off:off + size]
    raise ValueError("%s has no entry %r" % (path, entry))


def scripts(paths):
    """(label, bytes) of every .SQB file and every .sqb entry of a top-level
    BINPAC pack under the paths."""
    for path in pac._walk(paths):
        if path.upper().endswith(".SQB"):
            yield path, open(path, "rb").read()
            continue
        if not path.upper().endswith(".PAC"):
            continue
        try:
            hdr = pac.load_header(path)
        except (ValueError, struct.error):
            continue
        if not isinstance(hdr, pac.BinPac):
            continue
        entries = [e for e in hdr.entries if is_script_name(e[2])]
        if not entries:
            continue
        data = open(path, "rb").read()
        for off, size, name, _ in entries:
            yield "%s#%s" % (path, name), data[off:off + size]


# --- commands ----------------------------------------------------------------

def cmd_info(paths):
    total = {}
    count = 0
    for label, blob in scripts(paths):
        label = label.replace("\\", "/")
        count += 1
        try:
            offs, extra = tbb_tables(blob)
            name, result = fit(blob)
        except (ValueError, struct.error) as e:
            print("%s  !! %s" % (label, e))
            continue
        notes = []
        if extra:
            notes.append("table count includes the end offset")
        if struct.unpack_from("<I", blob, 0xc)[0] == 0:
            notes.append("size field 0")
        note = "  (%s)" % "; ".join(notes) if notes else ""
        if name is None:
            print("%s  tables=%d%s  !! decodes with no command set (%s)"
                  % (label, len(offs), note, result))
            continue
        ncmd = 0
        problems = []
        nlabels = 0
        for o, cmds in result:
            labels, p = check(cmds)
            problems += ["table @0x%x %s" % (o, x) for x in p]
            ncmd += len(cmds)
            nlabels += len(labels)
        total[name] = total.get(name, 0) + 1
        line = "%s  %s  scripts=%d  data=%d  commands=%d  labels=%d%s" % (
            label, name, len(result), len(offs) - len(result), ncmd, nlabels, note)
        if len(problems) == 1:
            print("%s  !! %s" % (line, problems[0]))
        else:
            print(line)
            for p in problems:
                print("  !! %s" % p)
    print("%d scripts: %s" % (count, ", ".join("%d %s" % (n, k) for k, n in sorted(total.items()))))


def cmd_dis(spec, cmdset=None):
    blob = load(spec)
    if cmdset:
        tables = [(o, decode(s, cmdset)) for o, s in sqb_tables(blob)]
    else:
        cmdset, tables = fit(blob)
        if cmdset is None:
            raise ValueError(tables)
    names = []
    if cmdset == "root":
        path = os.path.join(os.path.dirname(spec.partition("#")[0]), "SQBFILENAME.TBB")
        if os.path.exists(path):
            names = read_names(path)
    print("; %s  set=%s" % (spec, cmdset))
    for o, cmds in tables:
        print("; table @0x%x, %d commands" % (o, len(cmds)))
        for c in cmds:
            if c.table == 0 and c.cmd == FUNCTION:
                print("L%d:" % c.args[1][1])
            print("  %04x  %d:%-3d %s%s" % (c.pos, c.table, c.cmd, fmt_command(c),
                                            comment(c, names) if cmdset == "root" else ""))
            if c.table == 0 and c.cmd == LABEL:
                print("L%d:" % c.args[1][1])


def read_names(path):
    """SqbFilename.tbb: one table of char[32] names, row = script id
    (0x14a1b0); 0x14a220 loads every row that isn't "NULL"."""
    blob = open(path, "rb").read()
    off = struct.unpack_from("<I", blob, 0x10)[0]
    doff, size, line = struct.unpack_from("<III", blob, off + 4)
    base = off + doff
    return [blob[base + i * line:base + (i + 1) * line].split(b"\0")[0].decode("latin1")
            for i in range(size // line)]


def cmd_names(path):
    for i, name in enumerate(read_names(path)):
        print("%3d  %s" % (i, name))


def cmd_globals(path):
    blob = open(path, "rb").read()
    off = struct.unpack_from("<I", blob, 0x10)[0]
    doff, size = struct.unpack_from("<II", blob, off + 4)
    base = off + doff
    for i in range(size // 16):
        typ, value, lo, hi = struct.unpack_from("<Iiii", blob, base + 16 * i)
        print("g[%2d]  type=%d  value=%d  min=%d  max=%d" % (i, typ, value, lo, hi))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and args:
        cmd_info(args)
    elif cmd == "dis" and len(args) in (1, 2):
        if len(args) == 2 and args[1] not in SETS:
            print(__doc__)
            return 1
        cmd_dis(args[0], args[1] if len(args) == 2 else None)
    elif cmd == "names" and len(args) == 1:
        cmd_names(args[0])
    elif cmd == "globals" and len(args) == 1:
        cmd_globals(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
