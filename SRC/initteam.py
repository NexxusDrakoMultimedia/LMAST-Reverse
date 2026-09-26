"""Starting leagues and computer-team squads for Let's Make a Soccer Team! (PS2).

Two TBB1 files in DAT/PARAM set up the clubs at the start of a career
(see DOC/INITTEAM_FORMAT.md):

  PLRRSRC_INITTEAMDATA.TBB  table 0: 6 leagues x 2 divisions, each a list
                            of up to 26 u32 PlTeam ids ending at the first 0.
                            table 1: 56 x 32 u32 PlTeam ids, last season's
                            order per competition (PLSCHE_COMPE); the first
                            49 are read. table 2: 56 s16, the first 49 read.
  OTEAMMEMBER.TBB           teams 3-441, 25 squad slots each, 16-byte
                            records {u16 player, age, shirt, contract years}
                            with each field padded to a u32.

Confirmed from SLES_541.51: the PlRrsrc_InitTeamData callback (0x253338)
and its table readers (0x253228, 0x2531b0, 0x2532c8), plLg_EntryTeamSetToDiv
(0x2e94c8), pwkRec_SetPastRecordLastTeam (0x253650), pwkOteam_Init
(0x24a6a0), UpdateConyear (0x221480) and pwkTeam_SetUnumberOpinfo
(0x2734c8). Team names are message category 3, id 2000 + team
(Msg::GetString 0x200ea8, category table 0x51ab38, base at 0x52f7b0).

Usage:
    python initteam.py info    <DAT/PARAM>                    # check both files
    python initteam.py leagues <DAT/PARAM> [--mes MES.PAC] [--lang N]
    python initteam.py past    <DAT/PARAM> [--mes MES.PAC] [--lang N]
    python initteam.py squads  <DAT/PARAM> [team ...] [--mes MES.PAC] [--lang N]
    python initteam.py set     <OTEAMMEMBER.TBB> <out.TBB> <team>:<slot> <field>=<value> ...

`set` edits squad slots (fields player, age, shirt, contract) and writes a
new OTEAMMEMBER.TBB of the same size, ready for patch_disc.py. A computer
team's players take their age from here, not from the player database; a
new game shows it one year older (Terry's 25 shows as 26).

Names are read from <DAT/PARAM>/../MESSAGE/MES.PAC unless --mes is given,
in language slot 1 (English) unless --lang is given. Without MES.PAC the
commands print team ids only. `squads` also names each player from
<DAT/PARAM>/PBDATA_EU.PAC (pbdata.py) when it is there.
"""
import os
import struct
import sys

import tbb

INIT_TBB = "PLRRSRC_INITTEAMDATA.TBB"
OTEAM_TBB = "OTEAMMEMBER.TBB"
PBDATA = "PBDATA_EU.PAC"

# PLRRSRC_INITTEAMDATA table 0 (reader 0x253228): league i's two divisions
# are 0x68-byte blocks at i * 0xd0 and i * 0xd0 + 0x68.
LEAGUES = 6
DIVISIONS = 2
DIV_BLOCK = 0x68
DIV_MAX = 26                # plLg_EntryTeamSetToDiv stops at 0x1a teams or a 0 id
# Table 1 (reader 0x2531b0) and table 2 (0x2532c8).
PAST_ROW = 0x80
PAST_SLOTS = 0x20           # pwkRec_SetPastRecordLastTeamOne: slot < 0x20
PAST_READ = 0x31            # the readers loop PLSCHE_COMPE 0-48
INIT_SIZES = (LEAGUES * DIVISIONS * DIV_BLOCK, 56 * PAST_ROW, 56 * 2)

# OTEAMMEMBER (pwkOteam_Init 0x24a6a0): teams 3 to 0x1b9, 25 slots each.
OTEAM_FIRST = 3
OTEAM_END = 0x1ba
SQUAD = 25                  # also pwkTeam_SetUnumberOpinfo's slot count
OTEAM_ROW = 0x10
# Record offsets and the PlOpinfo byte each is copied to.
OTEAM_FIELDS = (("player", 0x0, "<H"), ("age", 0x4, "B"),
                ("shirt", 0x8, "B"), ("contract", 0xC, "B"))

TEAM_NAME_CATEGORY = 3      # global message slot 2 -> category 3 (0x51ab38)
TEAM_NAME_BASE = 2000       # u16 at 0x52f7b0, added to the team id


class Division:
    def __init__(self, league, div, raw):
        self.league, self.div = league, div
        self.ids = list(struct.unpack("<%dI" % DIV_MAX, raw))
        n = self.ids.index(0) if 0 in self.ids else DIV_MAX
        self.teams = self.ids[:n]
        # Ids after the first 0 are never read by the game.
        self.ignored = [t for t in self.ids[n:] if t]


class InitTeamData:
    def __init__(self, path):
        _, tables = tbb.load(path)
        if len(tables) != 3:
            raise ValueError("%d tables, expected 3" % len(tables))
        for t, size in zip(tables, INIT_SIZES):
            if t.size != size:
                raise ValueError("table %d is %d bytes, expected %d" % (t.index, t.size, size))
        d = tables[0].data
        self.divisions = [Division(lg, dv, d[(lg * DIVISIONS + dv) * DIV_BLOCK:][:DIV_BLOCK])
                          for lg in range(LEAGUES) for dv in range(DIVISIONS)]
        p = tables[1].data
        self.past = [list(struct.unpack_from("<%dI" % PAST_SLOTS, p, i * PAST_ROW))
                     for i in range(len(p) // PAST_ROW)]
        self.years = list(struct.unpack("<%dh" % (tables[2].size // 2), tables[2].data))


class Member:
    def __init__(self, raw):
        for name, off, fmt in OTEAM_FIELDS:
            setattr(self, name, struct.unpack_from(fmt, raw, off)[0])
        # The exporter wrote each field as a u32; the upper bytes should be 0.
        used = {off + i for _, off, fmt in OTEAM_FIELDS for i in range(struct.calcsize(fmt))}
        self.padding_ok = not any(raw[i] for i in range(OTEAM_ROW) if i not in used)


class OteamMembers:
    def __init__(self, path):
        _, tables = tbb.load(path)
        if len(tables) != 1:
            raise ValueError("%d tables, expected 1" % len(tables))
        d = tables[0].data
        want = (OTEAM_END - OTEAM_FIRST) * SQUAD * OTEAM_ROW
        if len(d) != want:
            raise ValueError("table is %d bytes, expected %d" % (len(d), want))
        self.squads = {}
        for i, team in enumerate(range(OTEAM_FIRST, OTEAM_END)):
            base = i * SQUAD * OTEAM_ROW
            self.squads[team] = [Member(d[base + k * OTEAM_ROW:][:OTEAM_ROW])
                                 for k in range(SQUAD)]


# --- names -------------------------------------------------------------------

def team_names(mes_path, lang):
    """{team id: name} from message category 3, or {} without MES.PAC."""
    if not mes_path or not os.path.exists(mes_path):
        return {}
    import mbb
    for _, m in mbb.iter_files([mes_path]):
        if m.category == TEAM_NAME_CATEGORY and m.lang == lang:
            return {rid - TEAM_NAME_BASE: mbb.decode(s, lang) for rid, s in m.records}
    return {}


def label(names, team):
    name = names.get(team)
    return "%3d %s" % (team, name) if name is not None else "%3d" % team


# --- loading -----------------------------------------------------------------

def find(root, name):
    p = os.path.join(root, name)
    if not os.path.exists(p):
        raise SystemExit("%s: not found" % p)
    return p


def default_mes(root):
    return os.path.join(root, os.pardir, "MESSAGE", "MES.PAC")


# --- commands ----------------------------------------------------------------

def cmd_info(root):
    path = find(root, INIT_TBB)
    try:
        init = InitTeamData(path)
    except (ValueError, struct.error) as e:
        print("%s  !! %s" % (path, e))
        init = None
    if init:
        print("%s  %d divisions, %d past records (%d read)" % (
            path, len(init.divisions), len(init.past), PAST_READ))
        seen = {}
        for dv in init.divisions:
            probs = []
            if dv.ignored:
                probs.append("ids after the terminating 0: %s" % dv.ignored)
            for t in dv.teams:
                if t in seen:
                    probs.append("team %d also in league %d division %d" % ((t,) + seen[t]))
                seen[t] = (dv.league, dv.div)
            print("  league %d division %d  %2d teams%s" % (
                dv.league, dv.div, len(dv.teams), "  !! " + "; ".join(probs) if probs else ""))
        ids = sorted(seen)
        print("  %d teams in the leagues, ids %d-%d" % (len(ids), ids[0], ids[-1]) if ids
              else "  no teams in the leagues")
        filled = [i for i, r in enumerate(init.past[:PAST_READ]) if any(r)]
        unread = [i for i, r in enumerate(init.past[PAST_READ:], PAST_READ) if any(r)]
        print("  past records: %d of %d read competitions have teams%s" % (
            len(filled), PAST_READ, "; unread %s not empty" % unread if unread else ""))
        print("  table 2 values (first %d): %s" % (
            PAST_READ, " ".join("%d x%d" % (v, init.years[:PAST_READ].count(v))
                                for v in sorted(set(init.years[:PAST_READ])))))

    path = find(root, OTEAM_TBB)
    try:
        ot = OteamMembers(path)
    except (ValueError, struct.error) as e:
        print("%s  !! %s" % (path, e))
        return
    members = [m for sq in ot.squads.values() for m in sq]
    print("%s  %d teams (%d-%d) x %d slots" % (
        path, len(ot.squads), OTEAM_FIRST, OTEAM_END - 1, SQUAD))
    probs = []
    players = [m.player for m in members]
    if len(set(players)) != len(players):
        probs.append("%d player numbers used more than once" % (len(players) - len(set(players))))
    bad_pad = sum(1 for m in members if not m.padding_ok)
    if bad_pad:
        probs.append("%d records with non-zero padding" % bad_pad)
    for team, sq in ot.squads.items():
        shirts = [m.shirt for m in sq]
        # pwkTeam_SetUnumberOpinfo treats shirts outside 1-99 as unset.
        out = [s for s in shirts if not 1 <= s <= 99]
        if out:
            probs.append("team %d shirt numbers outside 1-99: %s" % (team, out))
        if len(set(shirts)) != len(shirts):
            probs.append("team %d repeats a shirt number" % team)
    for p in probs:
        print("  !! " + p)
    print("  players %d-%d (%d distinct)" % (min(players), max(players), len(set(players))))
    for name in ("age", "shirt", "contract"):
        vals = [getattr(m, name) for m in members]
        print("  %-8s %d-%d" % (name, min(vals), max(vals)))


# Limits for `set`: the fields are copied into PlOpinfo bytes, and
# pwkTeam_SetUnumberOpinfo only keeps shirt numbers 1-99.
SET_LIMITS = {"player": (0, 0xffff), "age": (0, 0xff), "shirt": (1, 99), "contract": (0, 0xff)}


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(path, "rb") as f:
        buf = f.read()
    end, tables = tbb.parse(buf)
    OteamMembers(path)                  # layout check
    data = bytearray(tables[0].data)
    offsets = {name: (off, fmt) for name, off, fmt in OTEAM_FIELDS}
    slot_base = None
    for a in args:
        if "=" not in a:
            team, slot = (int(x, 0) for x in a.split(":"))
            if not OTEAM_FIRST <= team < OTEAM_END or not 0 <= slot < SQUAD:
                raise SystemExit("%s: teams are %d-%d and slots 0-%d" % (
                    a, OTEAM_FIRST, OTEAM_END - 1, SQUAD - 1))
            slot_base = ((team - OTEAM_FIRST) * SQUAD + slot) * OTEAM_ROW
            label = a
            continue
        if slot_base is None:
            raise SystemExit("give <team>:<slot> before %r" % a)
        name, value = a.split("=", 1)
        if name not in offsets:
            raise SystemExit("fields are %s" % ", ".join(offsets))
        value = int(value, 0)
        lo, hi = SET_LIMITS[name]
        if not lo <= value <= hi:
            raise SystemExit("%s must be %d-%d" % (name, lo, hi))
        off, fmt = offsets[name]
        old = struct.unpack_from(fmt, data, slot_base + off)[0]
        struct.pack_into(fmt, data, slot_base + off, value)
        print("%s %s: %d -> %d" % (label, name, old, value))
    tables[0].data = bytes(data)
    with open(out_path, "wb") as f:
        f.write(tbb.build(tables, end, tbb.trailer(buf, tables)))
    print("wrote %s" % out_path)


def cmd_leagues(root, names):
    init = InitTeamData(find(root, INIT_TBB))
    for dv in init.divisions:
        print("league %d division %d  (%d teams)" % (dv.league, dv.div, len(dv.teams)))
        for t in dv.teams:
            print("  " + label(names, t))


def cmd_past(root, names):
    init = InitTeamData(find(root, INIT_TBB))
    for i, row in enumerate(init.past):
        note = "" if i < PAST_READ else "  (not read)"
        teams = [t for t in row if t]
        print("competition %2d  table 2 = %d  %d teams%s" % (i, init.years[i], len(teams), note))
        for pos, t in enumerate(row):
            if t:
                print("  %2d  %s" % (pos, label(names, t)))


def cmd_squads(root, teams, names):
    ot = OteamMembers(find(root, OTEAM_TBB))
    # The squad's player number is a player-database id (getPlayerName,
    # 0x201f20, looks it up through plBp_GetBpinfo).
    db = None
    if os.path.exists(os.path.join(root, PBDATA)):
        import pbdata
        db = pbdata.PbData(os.path.join(root, PBDATA))
        if not db.data:
            db = None
    for team in teams or sorted(ot.squads):
        if team not in ot.squads:
            raise SystemExit("team %d has no squad (computer teams are %d-%d)" % (
                team, OTEAM_FIRST, OTEAM_END - 1))
        print("team " + label(names, team))
        print("  slot  player  age  shirt  contract%s" % ("  name" if db else ""))
        for k, m in enumerate(ot.squads[team]):
            line = "  %4d  %6d  %3d  %5d  %8d" % (k, m.player, m.age, m.shirt, m.contract)
            if db:
                line += "  " + db.record("players", m.player).name
            print(line)


def _opt(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    mes = _opt(args, "--mes")
    lang = int(_opt(args, "--lang", "1"))
    if not args:
        print(__doc__)
        return 1
    root = args[0]
    if cmd == "set" and len(args) >= 4:
        cmd_set(args[0], args[1], args[2:])
        return 0
    if cmd == "info" and len(args) == 1:
        cmd_info(root)
        return 0
    names = team_names(mes or default_mes(root), lang)
    if cmd == "leagues" and len(args) == 1:
        cmd_leagues(root, names)
    elif cmd == "past" and len(args) == 1:
        cmd_past(root, names)
    elif cmd == "squads":
        cmd_squads(root, [int(a, 0) for a in args[1:]], names)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
