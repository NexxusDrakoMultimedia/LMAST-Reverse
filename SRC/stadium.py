"""Stadium data checker for Let's Make a Soccer Team! (PS2).

DAT/STADIUM holds 10 stadium models (7 home grounds ho00a-ho04a, 3 away
grounds aw01a-aw04b; name table at GAMEPRG.REL 0x24d6a8), each as a set of
BINPAC packs of Ninja models in four lighting variants (D1, D2, N1, N2),
plus shared packs and the tables that build one of the 119 real stadiums
from a model. See DOC/STADIUM_DIR.md. Addresses are GAMEPRG.REL offsets.

  <model>.PRI            44 x u32: draw priority of each part slot, 0-100.
                         Read at 0x1caf18 (from pfs0:, a development path)
                         and requested with OpenReq(folder 0xa) at 0x1cdf60.
                         0x1cae18 / 0x1cae98 draw priorities 0-49, then 50-100.
  BUILD_STADIUM.TBB      t0: 119 x 129 bytes, one row per stadium (0x1cdb38:
                         i * 0x81). Byte 0 is the model (0x1cd72c: < 10),
                         byte 115 the crowd set (request +0xa9, 0x1d3848),
                         bytes 116-127 the 12 advert textures (0x299750,
                         0x1d31b8). t1: 10 x 12, one row per model (0x1cdbb0).
                         t2: 4 x 10 models x 10 bytes (0x1cdc28).
  CONV_INFO_BUILD.TBB    6 x 5 x 5 stadium ids: t[b*25 + a*5 + c] (0x1ce0b8).
  BUILD_ADVERTISE.TBB    32 x {s16 type, s16 alt type, s16 link, s16 part}
                         (0x1d1c60, 0x1d21c0); types 0-4 pick a creator class
                         (jump table 0x299d30, factory 0x1d2028).
  ADVERTISE_MODELPACK    32 x char[8] board names.
  AUD_JAM_HI.TBB         rows of 5 x u16 {amount[3], palette, threshold},
                         1024 = 1.0 (0x1d8188, 0x1d8330).
  AUD_JAM_LW.TBB         rows of {u16 threshold, u16 level} (0x1d8558).
  AUD_SET_<model>_<n>    t0: 9 stand sections {u16 share, u16 tiers,
                         u32 pointer slot} (0x1d68b0 patches in t1-t9);
                         t1-t9 per-section rows; t10: 40-byte crowd blocks
                         {char[32] name, u8 section, u8 tier, ...}; t11: 1 byte.

`info` checks all of these and the cross-references between them: every
crowd block has a model in its AUD_MODEL packs, every crowd set matches its
stadium's model, and BUILD_STADIUM has one row per PARAM/STADIUM_DATA.TBB
stadium.

Usage:
    python stadium.py info  <DAT/STADIUM> [<DAT/PARAM>]   # check the folder
    python stadium.py pri   <file.PRI>                    # the 44 priorities
    python stadium.py build <DAT/STADIUM> <stadium id>    # one BUILD_STADIUM row
    python stadium.py crowd <file.TBB>                    # one AUD_SET table
"""
import os
import struct
import sys
from collections import Counter

import pac
import tbb

MODELS = ("ho00a", "ho00b", "ho01a", "ho01b", "ho02a", "ho03a", "ho04a",
          "aw01a", "aw03a", "aw04b")          # GAMEPRG.REL 0x24d6a8
VARIANTS = ("d1", "d2", "n1", "n2")
PRI_SLOTS = 44                                # loops of 0x2b + 1 at 0x1caf80
PRI_MAX = 100                                 # the second draw pass ends at 0x64
PRI_PASS = 50                                 # first pass draws 0-0x31
BUILD_ROW = 0x81                              # 0x1cdb90: (i << 7) + i
BUILD_CROWD = 115                             # request +0xa9 = row +0x36 + 115
BUILD_ADVERT = slice(116, 128)                # offsets listed at 0x299750
MONTHS = 12
T2_ROW, T2_ENTRY = 100, 10                    # 0x1cdc28: row * 100 + model * 10
STADIUM_DATA_ROW = 3                          # SLES_541.51 0x22add4: i * 3, i < 0x77
# Crowd sets (request +0xa9, clamped to < 18): model and file number, from the
# byte tables at 0x24dfa8 and 0x24dfc0.
CROWD_SETS = ((0, 1), (1, 1), (2, 1), (2, 2), (2, 3), (3, 1), (3, 2), (3, 3),
              (4, 1), (4, 2), (4, 3), (5, 1), (5, 2), (5, 3), (6, 1), (7, 1),
              (8, 1), (9, 1))
CONV_ROWS, CONV_LEVELS, CONV_VARIANTS = 6, 5, 5
ADVERT_ROW = 8
ADVERT_TYPES = ("common", "lcd-anim", "fixed", "electric", "lcd-logo")   # 0x299d30
MODELPACK_ROW = 8
JAM_HI_ROW, JAM_LW_ROW = 10, 4
JAM_ONE = 1024
AUD_SECTIONS = 9
AUD_BLOCK = 0x28
AUD_NAME = 0x20
# Packs every model has, as (prefix, suffix) around the model name.
MODEL_PACKS = ([("", "_" + v) for v in VARIANTS + ("op",)] +
               [("adt_", "_" + v) for v in VARIANTS] +
               [("aud_model_", "_" + v) for v in VARIANTS])


def read_pri(path):
    with open(path, "rb") as f:
        buf = f.read()
    if len(buf) != 4 * PRI_SLOTS:
        raise ValueError("%d bytes, expected %d" % (len(buf), 4 * PRI_SLOTS))
    return struct.unpack("<%dI" % PRI_SLOTS, buf)


def rows(data, size):
    if len(data) % size:
        raise ValueError("%d bytes is not a whole number of %d-byte rows" % (len(data), size))
    return [data[i:i + size] for i in range(0, len(data), size)]


class Build:
    def __init__(self, path):
        _, t = tbb.load(path)
        if len(t) != 3:
            raise ValueError("%d tables, expected 3" % len(t))
        self.tables = t
        self.rows = rows(t[0].data, BUILD_ROW)
        self.model_rows = list(t[1].rows())
        self.t2 = rows(t[2].data, T2_ROW)

    def problems(self):
        out = []
        bad = [i for i, r in enumerate(self.rows) if r[0] >= len(MODELS)]
        if bad:
            out.append("model index >= %d in rows %s" % (len(MODELS), bad))
        bad = [i for i, r in enumerate(self.rows)
               if r[BUILD_CROWD] >= len(CROWD_SETS) or CROWD_SETS[r[BUILD_CROWD]][0] != r[0]]
        if bad:
            out.append("crowd set doesn't match the model in rows %s" % bad)
        if len(self.model_rows) != len(MODELS) or self.tables[1].line_size != MONTHS:
            out.append("table 1 is %d x %d, expected %d x %d" % (
                len(self.model_rows), self.tables[1].line_size, len(MODELS), MONTHS))
        if len(self.t2) != 4:
            out.append("table 2 has %d rows, expected 4" % len(self.t2))
        return out


class Crowd:
    """One AUD_SET_<model>_<n>.TBB."""

    def __init__(self, path):
        _, t = tbb.load(path)
        if len(t) != 12:
            raise ValueError("%d tables, expected 12" % len(t))
        self.sections = [struct.unpack_from("<HHI", r) for r in rows(t[0].data, 8)]
        if len(self.sections) != AUD_SECTIONS:
            raise ValueError("table 0 has %d sections" % len(self.sections))
        self.section_rows = [t[k].data for k in range(1, 1 + AUD_SECTIONS)]
        self.blocks = []
        for r in rows(t[10].data, AUD_BLOCK):
            name = r[:AUD_NAME].split(b"\0")[0].decode("latin1")
            self.blocks.append((name, r[AUD_NAME], r[AUD_NAME + 1], r[AUD_NAME + 2], r))
        self.last = t[11].data

    def problems(self):
        out = []
        for name, sec, tier, _, _ in self.blocks:
            if not name:
                out.append("unnamed block")
            elif sec >= AUD_SECTIONS:
                out.append("block %s: section %d" % (name, sec))
            elif tier >= self.sections[sec][1]:
                out.append("block %s: tier %d >= %d" % (name, tier, self.sections[sec][1]))
        if len(self.last) != 1:
            out.append("table 11 is %d bytes" % len(self.last))
        return out


def find(root, name):
    """Case-insensitive lookup; the disc names are upper case."""
    for f in os.listdir(root):
        if f.lower() == name.lower():
            return os.path.join(root, f)
    return None


def pack_names(root, name):
    p = find(root, name)
    h = pac.load_header(p) if p else None
    return [e[2] for e in h.entries] if h else None


def report(path, line, probs):
    if probs:
        line += "  !! " + "; ".join(probs)
    print("%-40s %s" % (path, line))


def check(path, fn):
    """Run fn(path) -> (line, problems); parse errors become a !! line."""
    if path is None:
        return None
    try:
        return fn(path)
    except (ValueError, struct.error) as e:
        report(path, "", [str(e)])
        return None


def cmd_info(root, param):
    for m in MODELS:
        path = find(root, m + ".pri")
        if path is None:
            report(os.path.join(root, m.upper() + ".PRI"), "", ["missing"])
            continue
        try:
            v = read_pri(path)
        except (ValueError, struct.error) as e:
            report(path, "", [str(e)])
            continue
        report(path, "priorities %3d-%3d, %2d in the first pass" % (
            min(v), max(v), sum(p < PRI_PASS for p in v)),
            ["priority > %d is never drawn" % PRI_MAX] if max(v) > PRI_MAX else [])

    for m in MODELS:
        missing = [pre + m + suf + ext for pre, suf in MODEL_PACKS for ext in (".pac", ".hed")
                   if find(root, pre + m + suf + ext) is None]
        counts = [len(pack_names(root, pre + m + suf + ".pac") or []) for pre, suf in MODEL_PACKS]
        print("  model %d %s  packs %s%s" % (MODELS.index(m), m, "/".join(map(str, counts)),
                                             "  !! missing " + ", ".join(missing) if missing else ""))

    b = check(find(root, "build_stadium.tbb"), Build)
    if b is not None:
        use = Counter(r[0] for r in b.rows)
        probs = b.problems()
        if param and find(param, "stadium_data.tbb"):
            _, t = tbb.load(find(param, "stadium_data.tbb"))
            if t[0].size // STADIUM_DATA_ROW != len(b.rows):
                probs.append("PARAM/STADIUM_DATA has %d stadiums" % (t[0].size // STADIUM_DATA_ROW))
        report(find(root, "build_stadium.tbb"), "%d stadiums; per model %s" % (
            len(b.rows), " ".join("%d:%d" % (k, use[k]) for k in sorted(use))), probs)

    def conv(path):
        _, t = tbb.load(path)
        ids = t[0].data
        probs = []
        if len(ids) != CONV_ROWS * CONV_LEVELS * CONV_VARIANTS:
            probs.append("%d bytes, expected %d" % (len(ids), CONV_ROWS * CONV_LEVELS * CONV_VARIANTS))
        n = len(b.rows) if b else 0
        for i, s in enumerate(ids):
            level = (i // CONV_VARIANTS) % CONV_LEVELS
            if s >= n:
                probs.append("entry %d: stadium %d" % (i, s))
            elif not MODELS[b.rows[s][0]].startswith("ho0%d" % level):
                probs.append("entry %d: level %d stadium %d uses %s" % (i, level, s, MODELS[b.rows[s][0]]))
        return report(path, "%d stadium ids, %d distinct" % (len(ids), len(set(ids))), probs)
    check(find(root, "conv_info_build.tbb"), conv)

    def advert(path):
        _, t = tbb.load(path)
        recs = [struct.unpack("<4h", r) for r in rows(t[0].data, ADVERT_ROW)]
        probs = []
        for i, (ty, alt, link, part) in enumerate(recs):
            if not (0 <= ty < len(ADVERT_TYPES) and 0 <= alt < len(ADVERT_TYPES)):
                probs.append("row %d: type %d/%d" % (i, ty, alt))
            if link != -1 and not 0 <= link < len(recs):
                probs.append("row %d: link %d" % (i, link))
            if not 0 < part < BUILD_ROW:
                probs.append("row %d: part byte %d" % (i, part))
        mp = find(root, "advertise_modelpack.tbb")
        names = rows(tbb.load(mp)[1][0].data, MODELPACK_ROW) if mp else []
        if len(names) != len(recs):
            probs.append("ADVERTISE_MODELPACK has %d names" % len(names))
        for m in MODELS:
            for v in VARIANTS:
                got = pack_names(root, "adt_%s_%s.pac" % (m, v))
                if got is not None and len(got) != len(recs):
                    probs.append("ADT_%s_%s has %d boards" % (m.upper(), v.upper(), len(got)))
        types = Counter(ADVERT_TYPES[r[0]] for r in recs if 0 <= r[0] < len(ADVERT_TYPES))
        return report(path, "%d boards: %s" % (len(recs), ", ".join(
            "%s %d" % kv for kv in sorted(types.items()))), probs)
    check(find(root, "build_advertise.tbb"), advert)

    def jam(path, size, field):
        _, t = tbb.load(path)
        probs, shapes = [], []
        for tab in t:
            recs = rows(tab.data, size)
            th = [struct.unpack_from("<H", r, 2 * field)[0] for r in recs]
            shapes.append(str(len(recs)))
            if th != sorted(th) or max(th) > JAM_ONE:
                probs.append("table %d thresholds not ascending within 0-%d" % (tab.index, JAM_ONE))
        return report(path, "%d table(s) of %s rows" % (len(t), "/".join(shapes)), probs)
    check(find(root, "aud_jam_hi.tbb"), lambda p: jam(p, JAM_HI_ROW, 4))
    check(find(root, "aud_jam_lw.tbb"), lambda p: jam(p, JAM_LW_ROW, 0))

    expected = {"aud_set_%s_%d.tbb" % (MODELS[m], n) for m, n in CROWD_SETS}
    present = {f.lower() for f in os.listdir(root)
               if f.lower().startswith("aud_set_") and f.lower().endswith(".tbb")}
    for f in sorted(present - expected):
        report(os.path.join(root, f.upper()), "", ["not one of the 18 crowd sets"])
    for f in sorted(expected - present):
        report(os.path.join(root, f.upper()), "", ["missing"])
    for idx, (m, n) in enumerate(CROWD_SETS):
        def crowd(path):
            c = Crowd(path)
            probs = c.problems()
            share = sum(s[0] for s in c.sections)
            for v in VARIANTS:
                have = pack_names(root, "aud_model_%s_%s.pac" % (MODELS[m], v))
                if have is None:
                    continue
                lost = [x[0] for x in c.blocks
                        if "%s_%s_aud_%s.snj" % (MODELS[m], v, x[0]) not in have]
                if lost:
                    probs.append("no model for %s in AUD_MODEL_%s_%s" % (
                        " ".join(lost), MODELS[m].upper(), v.upper()))
            return report(path, "set %2d: %2d blocks, shares %d/%d" % (
                idx, len(c.blocks), share, JAM_ONE), probs)
        check(find(root, "aud_set_%s_%d.tbb" % (MODELS[m], n)), crowd)


def cmd_pri(path):
    for i, p in enumerate(read_pri(path)):
        print("  slot %2d  priority %3d  pass %d" % (i, p, 1 if p < PRI_PASS else 2))


def cmd_build(root, sid):
    b = Build(find(root, "build_stadium.tbb"))
    r = b.rows[sid]
    m = r[0]
    print("stadium %d: model %d (%s)" % (sid, m, MODELS[m] if m < len(MODELS) else "?"))
    print("  bytes 1-114: %s" % r[1:BUILD_CROWD].hex(" "))
    cs = r[BUILD_CROWD]
    if cs < len(CROWD_SETS):
        print("  byte 115 crowd set: %d (AUD_SET_%s_%d)" % (
            cs, MODELS[CROWD_SETS[cs][0]].upper(), CROWD_SETS[cs][1]))
    print("  bytes 116-127 advert textures: %s" % " ".join(str(x) for x in r[BUILD_ADVERT]))
    print("  byte 128: %d" % r[128])
    if m < len(b.model_rows):
        print("  model row (table 1): %s" % " ".join(str(x) for x in b.model_rows[m]))
        for k, row in enumerate(b.t2):
            print("  table 2 row %d: %s" % (k, row[m * T2_ENTRY:(m + 1) * T2_ENTRY].hex(" ")))


def cmd_crowd(path):
    c = Crowd(path)
    for i, (share, tiers, _) in enumerate(c.sections):
        print("  section %d  share %4d/%d  tiers %d  rows %s" % (
            i, share, JAM_ONE, tiers, c.section_rows[i].hex(" ")))
    for name, sec, tier, flag, r in c.blocks:
        print("  block %-4s section %d tier %d flag %d  %s" % (name, sec, tier, flag, r[AUD_NAME + 3:].hex(" ")))
    print("  table 11: %s" % c.last.hex(" "))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) in (1, 2):
        cmd_info(args[0], args[1] if len(args) == 2 else None)
    elif cmd == "pri" and len(args) == 1:
        cmd_pri(args[0])
    elif cmd == "build" and len(args) == 2:
        cmd_build(args[0], int(args[1], 0))
    elif cmd == "crowd" and len(args) == 1:
        cmd_crowd(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
