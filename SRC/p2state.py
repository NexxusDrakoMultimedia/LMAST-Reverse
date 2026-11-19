# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""PCSX2 save-state checker for the club eras: reads a state's EE memory and checks what the
LMASTER Mod's club-eras and club-kits code (the kit eras, the kit standard and, with the third tier,
the third tier's eras) did in a match.

A PCSX2 state (.p2s) is a zip file holding eeMemory.bin (32 MiB; the EE address is the file
offset) and "PCSX2 Internal Structures.dat". Python's zipfile reads the file when the members
are stored or deflated. Newer PCSX2 versions compress with Zstandard, which zipfile of older
Python versions cannot read; only then, and only when zipfile fails, the 7-Zip command line
(7z on the PATH, else C:\\Program Files\\7-Zip\\7z.exe) extracts eeMemory.bin into a temporary
folder. A folder holding an extracted eeMemory.bin, or the eeMemory.bin itself, works too.

What it reads (EE addresses, DOC/RAM_MAP.md):

    0x5698d0 + 4 * id   the module activity table: a controller pointer, 0 = not running
    0x3906d8            the match pointer P (0 outside a match)
    P + 0x1fba0         the home team id, P + 0x24540 the away team id (u32)
    0x35d4a0            the frame counter
    patch_disc.ERA_VAR  the managers' result word: the manager index the last club-eras lookup
                        returned (the lookup runs for any club, so it need not be one of the
                        two playing)

The kits are the PlUnif (0x50 bytes) of each club, found by the bytes the LMASTER code writes
(kiteras.expect for kit-eras, kiteras.std_expect for kit-standards, then the club's retail home
colours at +0x1c to +0x1e). Teams 1 (your club) and 2 (the rival) are skipped. The test
build's --eras-offset, and which switches the disc had, are read from the code in memory when
not given (the words at the code segment's routines are compared with the ones patch_disc
generates); --offset and --switches override that, and without either the defaults are an
offset of 0 and all three switches.

Usage:
    python p2state.py info <state.p2s>
    python p2state.py kits <state.p2s> [--offset N] [--dat DAT] [--rel SIMPRG.REL] [--switches LIST] [--tables memory|plan]
    python p2state.py managers <state.p2s> [--offset N] [--dat DAT] [--switches LIST] [--tables memory|plan]
    python p2state.py selftest [--dat DAT] [--rel SIMPRG.REL]

The tables the code reads (the kit table, the standards' table, the managers' tiers, clubs and pool)
are in memory too. By default (--tables memory, when the LMASTER code is found in memory) the
expected bytes come from the tables the disc was built with, so a disc built with another seed
or an older plan still checks, and the tables are compared with the plan built from DAT now
(a note says how many bytes differ). --tables plan uses the plan built from DAT instead.

<state.p2s> is a state file, a folder holding eeMemory.bin, or an eeMemory.bin. LIST is a
comma-separated subset of kit-eras, kit-standards, tier3-eras (or "none"). --dat is the
extracted disc data (DAT by default), --rel SIMPRG.REL (ISO/DLL/SIMPRG.REL by default).
`selftest` builds a synthetic memory image and checks the commands against it; it needs no
state file. Result 1 on a problem.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import zipfile

MODULE_TABLE, MODULE_IDS = 0x5698D0, 174
MATCH_PTR, HOME_OFF, AWAY_OFF, FRAME = 0x3906D8, 0x1FBA0, 0x24540, 0x35D4A0
EE_SIZE = 32 << 20
MEMBER = "eeMemory.bin"
SEVENZ = r"C:\Program Files\7-Zip\7z.exe"
SEASONS = range(-1, 9)                 # the seasons a state can be in (-1 the opening playoffs)
SKIP_TEAMS = (1, 2)                    # your club and the rival: no era data
SWITCHES = ("kit-eras", "kit-standards", "tier3-eras")
SUPPLIER_NAMES = ("Binnonn", "Opnatis", "Wrandon", "Untelio", "Jompela", "Egamucho", "Doclla")
SUPPLIER_FIRST = 206
BANDS = ("white", "black", "blue", "red", "yellow")
SIMPRG_DEFAULT = os.path.join("ISO", "DLL", "SIMPRG.REL")


# --- reading the state --------------------------------------------------------------------

def _seven_zip():
    return shutil.which("7z") or (SEVENZ if os.path.exists(SEVENZ) else None)


def load_ee(path):
    """(bytes of EE memory, how it was read) for a .p2s, a folder holding eeMemory.bin or the
    eeMemory.bin itself. 'zipfile' normally; '7-Zip' only when zipfile could not read the
    state."""
    if os.path.isdir(path):
        path = os.path.join(path, MEMBER)
    with open(path, "rb") as f:
        head = f.read(4)
    if head[:2] != b"PK":
        with open(path, "rb") as f:
            return f.read(), "raw file"
    try:
        with zipfile.ZipFile(path) as z:
            names = {n.lower(): n for n in z.namelist()}
            if MEMBER.lower() not in names:
                raise ValueError("%s holds no %s" % (path, MEMBER))
            return z.read(names[MEMBER.lower()]), "zipfile"
    except ValueError:
        raise
    except (NotImplementedError, RuntimeError, zipfile.BadZipFile, OSError, EOFError, ImportError):
        pass                                           # a compression zipfile lacks: try 7-Zip
    exe = _seven_zip()
    if not exe:
        raise ValueError("zipfile cannot read %s and 7-Zip is not installed" % path)
    tmp = tempfile.mkdtemp(prefix="p2state-")
    try:
        r = subprocess.run([exe, "e", "-y", "-o" + tmp, path, MEMBER], capture_output=True)
        out = os.path.join(tmp, MEMBER)
        if r.returncode or not os.path.exists(out):
            raise ValueError("7-Zip could not extract %s from %s" % (MEMBER, path))
        with open(out, "rb") as f:
            return f.read(), "7-Zip"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def u32(ee, addr):
    if addr < 0 or addr + 4 > len(ee):
        return 0
    return struct.unpack_from("<I", ee, addr)[0]


def module_names():
    try:
        import sqb
        return dict(sqb.MODULES)
    except (ImportError, SystemExit, AttributeError):
        return {}


def read_state(ee):
    """The facts `info` prints, as a dict: modules {id: pointer}, P, home, away (or None),
    frame, result (the managers' result word)."""
    import patch_disc as pd
    mods = {i: u32(ee, MODULE_TABLE + 4 * i) for i in range(MODULE_IDS)}
    P = u32(ee, MATCH_PTR)
    home = away = None
    if P and P + AWAY_OFF + 4 <= len(ee):
        home, away = u32(ee, P + HOME_OFF), u32(ee, P + AWAY_OFF)
    return {"modules": {i: p for i, p in mods.items() if p}, "P": P, "home": home,
            "away": away, "frame": u32(ee, FRAME), "result": u32(ee, pd.ERA_VAR)}


def _words(ee, addr, n):
    return list(struct.unpack_from("<%dI" % n, ee, addr)) if addr + 4 * n <= len(ee) else None


def detect_build(ee):
    """What the code in memory says about the disc: {'offset': 0-2 or None, 'tier3': bool or
    None, 'standards': bool or None, 'eras': bool, 'kits': bool}. The routines at the
    code segment are compared word for word with patch_disc's, for every combination."""
    import patch_disc as pd
    out = {"offset": None, "tier3": None, "standards": None, "eras": False, "kits": False,
           "std_code": None}
    was = pd.kit_standards
    try:
        for tier3 in (False, True):
            clubs = pd.ERA_CLUB_COUNT_TIER3 if tier3 else pd.ERA_CLUB_COUNT
            for offset in range(10):
                w = pd.era_words(offset, clubs)
                if _words(ee, pd.ERA_CAVE, len(w)) == list(w):
                    out.update(offset=offset, tier3=tier3, eras=True)
        for std in (False, True):
            pd.kit_standards = std
            for tier3 in (False, True):
                clubs = pd.ERA_CLUB_COUNT_TIER3 if tier3 else pd.ERA_CLUB_COUNT
                for offset in range(10):
                    w = pd.kit_words(offset, clubs)
                    if _words(ee, pd.KIT_CAVE, len(w)) == list(w):
                        out.update(kits=True, standards=std)
                        if out["offset"] is None:
                            out.update(offset=offset, tier3=tier3)
        if out["standards"]:                    # the standards' own code: does it equal patch_disc's now?
            clubs = pd.ERA_CLUB_COUNT_TIER3 if out["tier3"] else pd.ERA_CLUB_COUNT
            w = pd.std_words(out["offset"] or 0, clubs)
            out["std_code"] = _words(ee, pd.STD_CAVE, len(w)) == list(w)
    finally:
        pd.kit_standards = was
    return out


# --- the plans and options ----------------------------------------------------------------

class Options:
    """offset, switches (a set) and where they came from."""

    def __init__(self, ee, offset=None, switches=None, tables=None):
        det = detect_build(ee)
        self.detected = det
        self.notes = []
        if offset is None:
            offset = det["offset"] if det["offset"] is not None else 0
            self.notes.append("offset %d (%s)" % (offset, "read from the code in memory"
                              if det["offset"] is not None else "default"))
        else:
            self.notes.append("offset %d (given)" % offset)
        if switches is None:
            sw = set(SWITCHES)
            if det["eras"] or det["kits"]:
                sw = set()
                if det["kits"]:
                    sw.add("kit-eras")
                if det["standards"]:
                    sw.add("kit-standards")
                if det["tier3"]:
                    sw.add("tier3-eras")
                self.notes.append("switches %s (read from the code in memory)" % (",".join(sorted(sw)) or "none"))
            else:
                self.notes.append("switches %s (default: no LMASTER code found in memory)" % ",".join(SWITCHES))
        else:
            sw = set(switches)
            self.notes.append("switches %s (given)" % (",".join(sorted(sw)) or "none"))
        self.offset, self.switches = offset, sw
        if tables is None:
            tables = "memory" if (det["eras"] or det["kits"]) else "plan"
        if tables not in ("memory", "plan"):
            raise ValueError("--tables is memory or plan")
        self.tables = tables

    @property
    def last(self):
        return 459 if "tier3-eras" in self.switches else 441


def _region(ee, addr, n):
    if addr + n > len(ee):
        raise ValueError("the tables lie outside the state's memory")
    return bytes(ee[addr:addr + n])


def memory_kit_plan(ee, base, last):
    """A copy of kiteras' plan `base` whose club rows and standards come from the tables in
    memory (patch_disc.KIT_TABLE, STD_TABLE), for the clubs of teams 3 to `last`."""
    import copy
    import kiteras
    import patch_disc as pd
    n = last - kiteras.TEAM_FIRST + 1
    kit = _region(ee, pd.KIT_TABLE, n * kiteras.VARIANTS * kiteras.KIT_ROW)
    std = _region(ee, pd.STD_TABLE, n * kiteras.STD_ENTRIES * kiteras.STD_ROW)
    plan = copy.copy(base)
    plan.last = last
    plan.club, plan.std = {}, {}
    for i, team in enumerate(range(kiteras.TEAM_FIRST, last + 1)):
        rows = []
        for v in range(kiteras.VARIANTS):
            h, a, c1, sb, c2, c3 = kit[(i * kiteras.VARIANTS + v) * kiteras.KIT_ROW:][:kiteras.KIT_ROW]
            rows.append((h, a, c1 & 0x7F, c2, c3, bool(c1 >> 7), sb >> 5, (sb & 31) + kiteras.SHORTS_FIRST))
        plan.club[team] = rows
        ents = []
        for e in range(kiteras.STD_ENTRIES):
            hw, hs, hn, aw, as_, an = struct.unpack_from("<HBBHBB", std, (i * kiteras.STD_ENTRIES + e) * kiteras.STD_ROW)
            ents.append(((hw, hs, hn), (aw, as_, an)))
        plan.std[team] = ents
    return plan, kit, std


def memory_era_plan(ee, base, last):
    """A copy of cluberas' plan `base` whose tiers, clubs and pool come from memory
    (patch_disc.ERA_TIERS, ERA_CLUBS, ERA_POOL)."""
    import copy
    import cluberas
    import patch_disc as pd
    plan = copy.copy(base)
    plan.last = last
    raw = _region(ee, pd.ERA_TIERS, 8 * cluberas.TIERS)
    rows = [struct.unpack_from("<4H", raw, 8 * i) for i in range(cluberas.TIERS)]
    plan.tiers = [r for r in rows if r[3]]                              # K = 0 pads the unused tiers
    n = last - cluberas.TEAM_FIRST + 1
    clubs = _region(ee, pd.ERA_CLUBS, 2 * n)
    plan.club = {}
    for i in range(n):
        v = struct.unpack_from("<H", clubs, 2 * i)[0]
        plan.club[cluberas.TEAM_FIRST + i] = (v >> 10, v & 0x3FF)
    size = sum(r[1] for r in plan.tiers)
    pool = _region(ee, pd.ERA_POOL, 2 * size)
    plan.pool = list(struct.unpack("<%dH" % size, pool))
    return plan, raw, clubs, pool


def effective_plans(ee, dat, rel, opt, want_kits=True, want_eras=True):
    """(kit plan, manager plan, notes): built from DAT, with the tables of the disc swapped in
    when opt.tables is 'memory'. The notes say how far the disc's tables differ from the plan
    built now."""
    import cluberas
    import kiteras
    notes = []
    kplan = cplan = None
    if want_kits:
        kplan = kiteras.build(dat, rel, opt.last)
    if want_eras:
        cplan = cluberas.build(dat, opt.last)
    if opt.tables != "memory":
        return kplan, cplan, ["tables: the plan built from %s" % dat]
    if kplan is not None:
        mplan, kit, std = memory_kit_plan(ee, kplan, opt.last)
        d1 = sum(a != b for a, b in zip(kit, kiteras.table_bytes(kplan)))
        d2 = sum(a != b for a, b in zip(std, kiteras.std_table_bytes(kplan)))
        notes.append("kit tables from memory: %d of %d kit bytes and %d of %d standard bytes differ from the plan "
                     "built from %s now%s" % (d1, len(kit), d2, len(std), dat,
                                              "" if d1 or d2 else " (the same plan)"))
        kplan = mplan
    if cplan is not None:
        mplan, raw, clubs, pool = memory_era_plan(ee, cplan, opt.last)
        d = (sum(a != b for a, b in zip(raw, cluberas.tier_bytes(cplan)))
             + sum(a != b for a, b in zip(clubs, cluberas.club_bytes(cplan)))
             + sum(a != b for a, b in zip(pool, cluberas.pool_bytes(cplan))))
        notes.append("manager tables from memory: %d of %d bytes differ from the plan built from %s now%s" % (
            d, len(raw) + len(clubs) + len(pool), dat, "" if d else " (the same plan)"))
        cplan = mplan
    return kplan, cplan, notes


def parse_switches(text):
    if text.strip().lower() in ("none", ""):
        return set()
    sw = set(s.strip() for s in text.split(",") if s.strip())
    bad = sw - set(SWITCHES)
    if bad:
        raise ValueError("unknown switch %s (known: %s)" % (",".join(sorted(bad)), ", ".join(SWITCHES)))
    return sw


def expected(plan, team, season, opt):
    """({offset: value} the code writes, {offset: value} context) for one club and season. The
    context holds the club's retail home colours (and, with no kit code, the retail designs),
    which the code leaves alone."""
    import kiteras
    want = {}
    if "kit-eras" in opt.switches:
        want.update(kiteras.expect(plan, team, season, opt.offset))
    if "kit-standards" in opt.switches:
        want.update(kiteras.std_expect(plan, team, season, opt.offset))
    ctx = {}
    if team in plan.home:
        ctx[0x1C], ctx[0x1D], ctx[0x1E] = plan.home[team]
    for k in list(ctx):
        if k in want:
            del ctx[k]
    return want, ctx


# --- finding a PlUnif ---------------------------------------------------------------------

def _runs(keys):
    runs, cur = [], []
    for k in sorted(keys):
        if cur and k == cur[-1] + 1:
            cur.append(k)
        else:
            if cur:
                runs.append(cur)
            cur = [k]
    if cur:
        runs.append(cur)
    return sorted(runs, key=lambda r: -len(r))


def search_block(ee, want, ctx, limit=300, min_run=4):
    """Blocks of EE memory that carry `want` (and `ctx`): [(base, [(offset, expected, found)
    for the code's bytes that differ], [... for the context's])], fewest differences first. The
    longest runs of expected bytes are the search signatures; a block must hold one of them."""
    allk = dict(want)
    allk.update(ctx)
    if not allk:
        return []
    found = {}
    for run in _runs(allk):
        if len(run) < min_run:
            break
        sig = bytes(allk[k] for k in run)
        pos, n = -1, 0
        while n < limit:
            pos = ee.find(sig, pos + 1)
            if pos < 0:
                break
            n += 1
            base = pos - run[0]
            if base < 0 or base + 0x50 > len(ee) or base in found:
                continue
            diff = [(k, want[k], ee[base + k]) for k in sorted(want) if ee[base + k] != want[k]]
            cdiff = [(k, ctx[k], ee[base + k]) for k in sorted(ctx) if ee[base + k] != ctx[k]]
            found[base] = (base, diff, cdiff)
        if any(not d and not c for _, d, c in found.values()):
            break                                       # an exact block: no need for shorter runs
    return sorted(found.values(), key=lambda b: (len(b[1]) + len(b[2]), b[0]))


def find_kit(ee, plan, team, opt, seasons=SEASONS):
    """The best matches of a club's PlUnif over `seasons`: [{'seasons', 'era', 'base', 'diff',
    'cdiff', 'want'}], the seasons with identical expectations grouped; empty when the club's
    code writes nothing (era 0 without kit-standards, or a club outside the plan)."""
    import cluberas
    groups = {}
    for season in seasons:
        want, ctx = expected(plan, team, season, opt)
        key = (tuple(sorted(want.items())), tuple(sorted(ctx.items())))
        g = groups.setdefault(key, {"seasons": [], "eras": set(), "want": want, "ctx": ctx})
        g["seasons"].append(season)
        g["eras"].add(cluberas.era_of(team, season, opt.offset))
    out = []
    for g in groups.values():
        if not g["want"]:
            out.append({"seasons": g["seasons"], "era": sorted(g["eras"]), "base": None,
                        "diff": [], "cdiff": [], "want": {}, "hits": 0})
            continue
        blocks = search_block(ee, g["want"], g["ctx"])
        if not blocks:
            out.append({"seasons": g["seasons"], "era": sorted(g["eras"]), "base": None,
                        "diff": None, "cdiff": None, "want": g["want"], "hits": 0})
            continue
        exact = [b for b in blocks if not b[1]]
        best = blocks[0]
        out.append({"seasons": g["seasons"], "era": sorted(g["eras"]), "base": best[0],
                    "diff": best[1], "cdiff": best[2], "want": g["want"], "hits": len(exact),
                    "blocks": [b[0] for b in exact]})
    return out


# --- decoding a kit -----------------------------------------------------------------------

def decode_kit(ee, base):
    """Lines describing the PlUnif at `base`: the supplier, then each side's kit."""
    import uniform
    c = uniform.colour_name
    b = lambda k: ee[base + k]
    sup = b(5)
    name = SUPPLIER_NAMES[sup - SUPPLIER_FIRST] if 0 <= sup - SUPPLIER_FIRST < len(SUPPLIER_NAMES) else "none"
    lines = ["sponsor %d, supplier %d (%s)" % (b(4), sup, name)]
    for label, side, kit in (("home", 6, 0x1B), ("away", 0x2A, 0x3F)):
        band = b(kit + 14)
        lines.append(
            "%s: shirt %d %s/%s/%s, collar %d, shorts %d %s/%s/%s, socks %d %s/%s, numbers %s (shirt) %s (shorts)"
            % (label, b(kit), c(b(kit + 1)), c(b(kit + 2)), c(b(kit + 3)), b(kit + 4), b(kit + 5),
               c(b(kit + 6)), c(b(kit + 7)), c(b(kit + 8)), b(kit + 9), c(b(kit + 10)), c(b(kit + 11)),
               c(b(kit + 12)), c(b(kit + 13))))
        lines.append(
            "      number design %d, front number %s, emblems %d (shirt) %d (shorts), shorts number position %d, "
            "captain's band %s" % (b(side + 2), "on" if b(side + 3) == 1 else "off(%d)" % b(side + 3),
                                   b(side), b(side + 1), b(side + 4),
                                   BANDS[band] if band < len(BANDS) else "?%d" % band))
    return lines


# --- the commands -------------------------------------------------------------------------

def cmd_info(path):
    ee, how = load_ee(path)
    st = read_state(ee)
    names = module_names()
    print("state %s: %d bytes of EE memory (read with %s)" % (os.path.basename(path), len(ee), how))
    if len(ee) != EE_SIZE:
        print("  !! %d bytes, expected %d" % (len(ee), EE_SIZE))
    print("frame counter 0x%x: %d" % (FRAME, st["frame"]))
    run = st["modules"]
    print("running modules (%d): %s" % (len(run), ", ".join(
        "%d %s" % (i, names.get(i, "?")) for i in sorted(run)) or "none"))
    if st["P"]:
        print("match pointer 0x%x = 0x%x: team %d (home) v team %d (away)" % (
            MATCH_PTR, st["P"], st["home"], st["away"]))
    else:
        print("match pointer 0x%x = 0: no match is loaded" % MATCH_PTR)
    import patch_disc as pd
    print("managers' result word 0x%x = %d" % (pd.ERA_VAR, st["result"]))
    det = detect_build(ee)
    if det["eras"] or det["kits"]:
        print("LMASTER code in memory: managers %s, kits %s; offset %s, standards %s, tier3-eras %s" % (
            "yes" if det["eras"] else "no", "yes" if det["kits"] else "no", det["offset"],
            {True: "yes", False: "no", None: "?"}[det["standards"]],
            {True: "yes", False: "no", None: "?"}[det["tier3"]]))
        if det["std_code"] is False:
            print("  !! the standards' code in memory differs from patch_disc's now: the disc was built with "
                  "another version, so the bytes it writes may differ from kiteras.std_expect's")
    else:
        print("LMASTER code in memory: none found (a disc without the eras, or one built differently)")
    return 0


def _eras(g):
    return "era %s" % ",".join(str(e) for e in g["era"])


def _seasons(g):
    ss = g["seasons"]
    return "season%s %s" % ("s" if len(ss) > 1 else "", ",".join(str(x) for x in ss))


def kit_report(ee, plan, opt, teams):
    """The lines of `kits` for `teams`, and the number of problems."""
    import kiteras
    lines, bad = [], 0
    for team in teams:
        if team in SKIP_TEAMS:
            lines.append("team %d: the %s: skipped" % (team, "player's club" if team == 1 else "rival"))
            continue
        if not kiteras.TEAM_FIRST <= team <= plan.last:
            lines.append("team %d: outside the clubs of teams %d-%d with these switches: the retail kit, nothing to "
                         "compare" % (team, kiteras.TEAM_FIRST, plan.last))
            continue
        groups = find_kit(ee, plan, team, opt)
        exact = [g for g in groups if g["want"] and g["base"] is not None and not g["diff"]]
        silent = [g for g in groups if not g["want"]]
        if exact:                                       # the era (and the seasons) whose bytes are there
            for g in exact:
                lines.append("team %d: PlUnif at 0x%x holds %s (%s), 0 of %d expected bytes differ%s" % (
                    team, g["base"], _eras(g), _seasons(g), len(g["want"]),
                    "  [%d exact blocks: 0x%s]" % (g["hits"], ", 0x".join("%x" % x for x in g["blocks"][:6]))
                    if g["hits"] > 1 else ""))
                lines += ["    " + t for t in decode_kit(ee, g["base"])]
                if g["cdiff"]:
                    lines.append("    retail home colours differ: " + "; ".join(
                        "+0x%x expected %d found %d" % x for x in g["cdiff"]))
            continue
        found = [g for g in groups if g["want"] and g["base"] is not None]
        if found:                                       # no exact era: the closest block is the diagnosis
            g = min(found, key=lambda g: (len(g["diff"]), g["seasons"][0]))
            bad += 1
            d = g["diff"]
            lines.append("team %d: no era's bytes match exactly; closest is PlUnif at 0x%x, %s (%s): %d of %d "
                         "expected bytes differ  !! %s" % (
                             team, g["base"], _eras(g), _seasons(g), len(d), len(g["want"]),
                             "; ".join("+0x%x expected 0x%02x found 0x%02x" % x for x in d[:12])))
            continue
        if silent:
            g = silent[0]
            lines.append("team %d: %s (%s): the code writes nothing, so the club has the retail kit and there is "
                         "nothing to find%s" % (team, _eras(g), _seasons(g),
                                                ("; the eras 1 and up were searched and not found"
                                                 if len(groups) > 1 else "")))
            continue
        bad += 1
        lines.append("team %d: no PlUnif with the expected bytes of any season in memory  !! (another plan or "
                     "switches, or the club is not loaded)" % team)
    return lines, bad


def cmd_kits(path, dat, rel, offset, switches, tables=None):
    ee, how = load_ee(path)
    opt = Options(ee, offset, switches, tables)
    st = read_state(ee)
    print("kits in %s (%s)" % (os.path.basename(path), "; ".join(opt.notes)))
    if not st["P"] or st["home"] is None:
        print("no match is loaded (match pointer 0): nothing to find")
        return 1
    print("match: team %d (home) v team %d (away)" % (st["home"], st["away"]))
    plan, _, notes = effective_plans(ee, dat, rel, opt, True, False)
    for n in notes:
        print(n)
    if opt.detected["std_code"] is False:
        print("note: the standards' code in memory differs from patch_disc's now (another version built the disc): "
              "bytes the standards write may differ from kiteras.std_expect's")
    if "kit-eras" not in opt.switches:
        print("kit-eras is off: only the standard (kit-standards) is compared" if "kit-standards" in opt.switches
              else "kit-eras and kit-standards are both off: nothing is written to compare")
    lines, bad = kit_report(ee, plan, opt, (st["home"], st["away"]))
    print("\n".join(lines))
    print("%s" % ("  !! %d club(s) with differences (a disc built with another plan or switches differs)" % bad
                  if bad else "kits: every club found matches"))
    return 1 if bad else 0


def manager_report(ee, plan, cplan, pbdb, opt, teams):
    """(lines, matching teams) of `managers`: the result word against each club's lookup."""
    import cluberas
    import patch_disc as pd
    word = u32(ee, pd.ERA_VAR)

    def who(i):
        try:
            m = pbdb.record("managers", i)
            return "%d (%s, rank %d)" % (i, m.name, m.fields["rank"])
        except (ValueError, KeyError, IndexError, AttributeError):
            return "%d" % i
    lines = ["managers' result word 0x%x = %s" % (pd.ERA_VAR, who(word))]
    hits = []
    for team in teams:
        if team in SKIP_TEAMS:
            lines.append("team %d: the %s: skipped" % (team, "player's club" if team == 1 else "rival"))
            continue
        if not cluberas.TEAM_FIRST <= team <= cplan.last:
            lines.append("team %d: outside the clubs of teams %d-%d: the game's own lookup" % (
                team, cluberas.TEAM_FIRST, cplan.last))
            continue
        seasons = []
        for season in SEASONS:
            e = cluberas.era_of(team, season, opt.offset)
            if e and cluberas.manager(cplan, team, season, opt.offset) == word:
                seasons.append(season)
        info = [(s, cluberas.era_of(team, s, opt.offset), cluberas.manager(cplan, team, s, opt.offset))
                for s in SEASONS]
        eras = sorted({(e, m) for _, e, m in info})
        lines.append("team %d (group %d): by era %s" % (team, team % 3, ", ".join(
            "%d:%s" % (e, "retail " + who(m) if e == 0 else who(m)) for e, m in eras)))
        if seasons:
            hits.append(team)
            lines.append("    the word is team %d's lookup in season%s %s" % (
                team, "s" if len(seasons) > 1 else "", ",".join(str(s) for s in seasons)))
        else:
            lines.append("    the word is not team %d's lookup in any season -1 to 8 (offset %d)" % (team, opt.offset))
    if hits:
        lines.append("the word matches the lookup of team%s %s" % ("s" if len(hits) > 1 else "", ", ".join(map(str, hits))))
    else:
        lines.append("the word matches neither club: it is the last lookup of some other club (or none ran yet)")
    return lines, hits


def cmd_managers(path, dat, rel, offset, switches, tables=None):
    import cluberas
    import pbdata
    ee, how = load_ee(path)
    opt = Options(ee, offset, switches, tables)
    st = read_state(ee)
    print("managers in %s (%s)" % (os.path.basename(path), "; ".join(opt.notes)))
    if not st["P"] or st["home"] is None:
        print("no match is loaded (match pointer 0): the word is still compared with no club")
        teams = ()
    else:
        print("match: team %d (home) v team %d (away)" % (st["home"], st["away"]))
        teams = (st["home"], st["away"])
    _, cplan, notes = effective_plans(ee, dat, rel, opt, False, True)
    for n in notes:
        print(n)
    pbdb = pbdata.PbData(os.path.join(dat, cluberas.PB_FILE))
    lines, hits = manager_report(ee, None, cplan, pbdb, opt, teams)
    print("\n".join(lines))
    return 0


# --- selftest -----------------------------------------------------------------------------

def synthetic_state(plan, cplan, home, away, season, opt, var_team, size=0x800000):
    """A memory image of `size` bytes with a match between `home` and `away`: the code
    segment's routines, the pointers, the result word of `var_team`'s lookup, and each club's
    PlUnif written as the machine code writes it. Returns (ee, {team: block base})."""
    import kiteras
    import cluberas
    import patch_disc as pd
    ee = bytearray(size)
    for addr, blob in ((pd.KIT_TABLE, kiteras.table_bytes(plan)), (pd.STD_TABLE, kiteras.std_table_bytes(plan)),
                       (pd.ERA_TIERS, cluberas.tier_bytes(cplan)), (pd.ERA_CLUBS, cluberas.club_bytes(cplan)),
                       (pd.ERA_POOL, cluberas.pool_bytes(cplan))):
        ee[addr:addr + len(blob)] = blob
    was = pd.kit_standards
    pd.kit_standards = "kit-standards" in opt.switches
    clubs = pd.ERA_CLUB_COUNT_TIER3 if "tier3-eras" in opt.switches else pd.ERA_CLUB_COUNT
    try:
        w = pd.era_words(opt.offset, clubs)
        struct.pack_into("<%dI" % len(w), ee, pd.ERA_CAVE, *w)
        w = pd.kit_words(opt.offset, clubs)
        struct.pack_into("<%dI" % len(w), ee, pd.KIT_CAVE, *w)
    finally:
        pd.kit_standards = was
    struct.pack_into("<I", ee, MODULE_TABLE + 4 * 6, 0x123450)                  # Game running
    P = 0x600000
    struct.pack_into("<I", ee, MATCH_PTR, P)
    struct.pack_into("<I", ee, P + HOME_OFF, home)
    struct.pack_into("<I", ee, P + AWAY_OFF, away)
    struct.pack_into("<I", ee, FRAME, 4321)
    struct.pack_into("<I", ee, pd.ERA_VAR, cluberas.manager(cplan, var_team, season, opt.offset))
    bases = {}
    for n, team in enumerate((home, away)):
        base = 0x500000 + 0x100 * n
        bases[team] = base
        for k in range(0x50):                                                # the retail kit the code writes onto
            ee[base + k] = (k * 7 + 3 * n + 1) & 0x7F
        want, ctx = expected(plan, team, season, opt)
        for k, v in ctx.items():
            ee[base + k] = v
        for k, v in want.items():
            ee[base + k] = v
    return ee, bases


def cmd_selftest(dat="DAT", rel=None):
    import cluberas
    import kiteras
    import pbdata
    bad = []
    runs = 0
    # a team with the 2 offset: season 1 puts group 0..2 clubs at era 1 or 0, so use 3 clubs of each group
    for tier3 in (False, True):
        sw = {"kit-eras", "kit-standards"} | ({"tier3-eras"} if tier3 else set())
        opt = Options(bytearray(16), 2, sw)
        plan = kiteras.build(dat, rel, opt.last)
        cplan = cluberas.build(dat, opt.last)
        pbdb = pbdata.PbData(os.path.join(dat, cluberas.PB_FILE))
        for season in (0, 1, 5):
            for home, away in ((119, 200), (120, 121), (3, 441 + (3 if tier3 else 0))):
                ee, bases = synthetic_state(plan, cplan, home, away, season, opt, away)
                runs += 1
                tag = "tier3=%s season %d teams %d v %d" % (tier3, season, home, away)
                st = read_state(ee)
                if (st["P"], st["home"], st["away"], st["frame"]) != (0x600000, home, away, 4321) or 6 not in st["modules"]:
                    bad.append(tag + ": info read %s" % st)
                det = detect_build(ee)
                if (det["offset"], det["tier3"], det["standards"], det["eras"], det["kits"]) != (2, tier3, True, True, True):
                    bad.append(tag + ": detected %s" % det)
                auto = Options(ee)
                if auto.offset != 2 or auto.switches != sw:
                    bad.append(tag + ": auto options %s %s" % (auto.offset, sorted(auto.switches)))
                lines, nbad = kit_report(ee, plan, opt, (home, away))
                if nbad:
                    bad.append(tag + ": kits reported %d differ: %s" % (nbad, lines))
                for team in (home, away):
                    gs = find_kit(ee, plan, team, opt)
                    hit = [g for g in gs if season in g["seasons"]]
                    want, _ = expected(plan, team, season, opt)
                    if len(hit) != 1:
                        bad.append(tag + ": team %d: season %d not in one group" % (team, season))
                        continue
                    g = hit[0]
                    if want and (g["base"] != bases[team] or g["diff"]):
                        bad.append(tag + ": team %d found at %s diff %s, want %#x" % (team, g["base"] and hex(g["base"]), g["diff"], bases[team]))
                    if not want and g["base"] is not None:
                        bad.append(tag + ": team %d expected nothing but found %#x" % (team, g["base"]))
                # the managers' word is the away club's lookup
                _, hits = manager_report(ee, None, cplan, pbdb, opt, (home, away))
                if cluberas.era_of(away, season, 2) and away not in hits:
                    bad.append(tag + ": managers: away club %d not matched (%s)" % (away, hits))
                if (home, away) in ((120, 121),) and cluberas.manager(cplan, home, season, 2) == cluberas.manager(cplan, away, season, 2):
                    bad.append(tag + ": managers coincide")
        # a wrong byte is reported, with its offset
        home, away = 119, 200
        ee, bases = synthetic_state(plan, cplan, home, away, 1, opt, away)
        want, _ = expected(plan, home, 1, opt)
        k = max(want)
        ee[bases[home] + k] ^= 0x55
        runs += 1
        g = [g for g in find_kit(ee, plan, home, opt) if 1 in g["seasons"]][0]
        if g["base"] != bases[home] or [x[0] for x in g["diff"]] != [k]:
            bad.append("a wrong byte at +0x%x was reported as %s" % (k, g["diff"]))
        # the disc's own tables: a plan that differs from the one built now still checks from memory
        import copy
        other = copy.copy(plan)
        other.club = {t: rows[1:] + rows[:1] for t, rows in plan.club.items()}      # the variants shifted by one
        other.std = {t: ents[:1] + ents[2:] + ents[1:2] for t, ents in plan.std.items()}
        cother = copy.copy(cplan)
        cother.pool = cplan.pool[1:] + cplan.pool[:1]                              # another seed's pool
        for season in (1, 5):
            ee2, bases2 = synthetic_state(other, cother, 119, 200, season, opt, 200)
            runs += 1
            mem_plan = memory_kit_plan(ee2, plan, opt.last)[0]
            mem_c = memory_era_plan(ee2, cplan, opt.last)[0]
            opt2 = Options(ee2, 2, sw, "memory")
            if opt2.tables != "memory":
                bad.append("tables option")
            lines, nbad = kit_report(ee2, mem_plan, opt2, (119, 200))
            if nbad or sum("0 of" in l for l in lines) != 2:
                bad.append("memory tables, season %d: %s" % (season, lines))
            _, hits = manager_report(ee2, None, mem_c, pbdb, opt2, (119, 200))
            if 200 not in hits:
                bad.append("memory managers, season %d: %s" % (season, hits))
            if cluberas.manager(mem_c, 200, season, 2) != cluberas.manager(cother, 200, season, 2):
                bad.append("memory manager plan differs from the written one")
        # no match loaded: P = 0
        struct.pack_into("<I", ee, MATCH_PTR, 0)
        if read_state(ee)["home"] is not None:
            bad.append("P = 0 still gave teams")
        # an off-plan club is not searched
        if tier3 is False:
            lines, _ = kit_report(ee, plan, opt, (1, 2, 450))
            if len(lines) != 3 or "skipped" not in lines[0] or "outside" not in lines[2]:
                bad.append("teams 1, 2 and 450 handled as %s" % lines)
    # reading a zip, deflated, and as a folder and raw
    ee = bytearray(EE_SIZE)
    struct.pack_into("<I", ee, MATCH_PTR, 0x1234)
    tmp = tempfile.mkdtemp(prefix="p2state-selftest-")
    try:
        p2s = os.path.join(tmp, "t.p2s")
        with zipfile.ZipFile(p2s, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("PCSX2 Internal Structures.dat", b"x")
            z.writestr(MEMBER, bytes(ee))
        for p in (p2s, tmp):
            if p == tmp:
                with open(os.path.join(tmp, MEMBER), "wb") as f:
                    f.write(bytes(ee))
            got, how = load_ee(p)
            runs += 1
            if len(got) != EE_SIZE or u32(got, MATCH_PTR) != 0x1234:
                bad.append("load_ee(%s) via %s wrong" % (p, how))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("selftest: %d runs%s" % (runs, "  !! %d wrong" % len(bad) if bad else ", 0 wrong"))
    for line in bad[:8]:
        print("  !! " + line)
    return 1 if bad else 0


# --- main ---------------------------------------------------------------------------------

def _options(args):
    opts = {"--offset": None, "--dat": "DAT", "--rel": SIMPRG_DEFAULT, "--switches": None, "--tables": None}
    rest = []
    i = 0
    while i < len(args):
        if args[i] in opts:
            if i + 1 >= len(args):
                raise ValueError("%s needs a value" % args[i])
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            rest.append(args[i])
            i += 1
    offset = int(opts["--offset"]) if opts["--offset"] is not None else None
    if offset is not None and not 0 <= offset <= 9:
        raise ValueError("--offset is 0 to 9")
    switches = parse_switches(opts["--switches"]) if opts["--switches"] is not None else None
    rel = None
    if os.path.exists(opts["--rel"]):
        with open(opts["--rel"], "rb") as f:
            rel = f.read()
    return rest, opts["--dat"], rel, offset, switches, opts["--tables"]


def main(argv):
    if len(argv) < 2 or argv[1] not in ("info", "kits", "managers", "selftest"):
        print(__doc__)
        return 1
    try:
        rest, dat, rel, offset, switches, tables = _options(argv[2:])
        if argv[1] == "selftest":
            return cmd_selftest(dat, rel)
        if len(rest) != 1:
            print(__doc__)
            return 1
        if argv[1] == "info":
            return cmd_info(rest[0])
        if argv[1] == "kits":
            return cmd_kits(rest[0], dat, rel, offset, switches, tables)
        return cmd_managers(rest[0], dat, rel, offset, switches, tables)
    except (ValueError, OSError) as e:
        print("!! %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
