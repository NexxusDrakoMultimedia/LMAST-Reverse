"""Stadium data checker for Let's Make a Soccer Team! (PS2).

DAT/STADIUM holds 10 stadium models (7 home grounds ho00a-ho04a, 3 away
grounds aw01a-aw04b; name table at GAMEPRG.REL 0x24d6a8), each as a set of
BINPAC packs of Ninja models in four lighting variants (D1, D2, N1, N2),
plus shared packs and the tables that build one of the 119 real stadiums
from a model. See DOC/STADIUM_DIR.md.

  <model>.PRI         44 x u32: draw priority of each of the model's 44
                      part slots, 0-100. Read by GAMEPRG.REL 0x1caf18 (from
                      pfs0:, a development path) and requested through
                      CDataHandle::OpenReq(folder 0xa, "<model>.pri") at
                      0x1cdf60. The draw passes at 0x1cae18 / 0x1cae98 draw
                      priorities 0-49, then 50-100, in increasing order.
  BUILD_STADIUM.TBB   table 0: 119 x 129 bytes, one row per stadium
                      (GAMEPRG.REL 0x1cdb38: i * 0x81). Byte 0 is the model
                      (0x1cd72c: < 10). Bytes 116-127 are copied as a
                      block (offset list at 0x299750).
                      table 1: 10 x 12 bytes, one row per model (0x1cdbb0),
                      indexed by a request byte < 12 (probably the month).
                      table 2: 4 x 100 bytes.

`info` checks the .PRI files and BUILD_STADIUM against that layout, that
BUILD_STADIUM has one row per PARAM/STADIUM_DATA.TBB stadium, and that
every model has its packs.

Usage:
    python stadium.py info  <DAT/STADIUM> [<DAT/PARAM>]   # check the folder
    python stadium.py pri   <file.PRI>                    # the 44 priorities
    python stadium.py build <DAT/STADIUM> <stadium id>    # one BUILD_STADIUM row
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
BUILD_ADVERT = slice(116, 128)                # offsets listed at 0x299750
MONTHS = 12
STADIUM_DATA_ROW = 3                          # SLES_541.51 0x22add4: i * 3, i < 0x77
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


class Build:
    def __init__(self, path):
        _, t = tbb.load(path)
        if len(t) != 3:
            raise ValueError("%d tables, expected 3" % len(t))
        self.tables = t
        d = t[0].data
        self.rows = [d[i:i + BUILD_ROW] for i in range(0, len(d) - BUILD_ROW + 1, BUILD_ROW)]
        self.leftover = len(d) % BUILD_ROW
        self.model_rows = list(t[1].rows())

    def problems(self):
        out = []
        if self.leftover:
            out.append("table 0: %d bytes left over at %d-byte rows" % (self.leftover, BUILD_ROW))
        bad = [i for i, r in enumerate(self.rows) if r[0] >= len(MODELS)]
        if bad:
            out.append("model index >= %d in rows %s" % (len(MODELS), bad))
        if len(self.model_rows) != len(MODELS) or self.tables[1].line_size != MONTHS:
            out.append("table 1 is %d x %d, expected %d x %d" % (
                len(self.model_rows), self.tables[1].line_size, len(MODELS), MONTHS))
        return out


def find(root, name):
    """Case-insensitive lookup; the disc names are upper case."""
    for f in os.listdir(root):
        if f.lower() == name.lower():
            return os.path.join(root, f)
    return None


def cmd_info(root, param):
    for m in MODELS:
        path = find(root, m + ".pri")
        if path is None:
            print("%-40s !! missing" % os.path.join(root, m.upper() + ".PRI"))
            continue
        try:
            v = read_pri(path)
        except (ValueError, struct.error) as e:
            print("%-40s !! %s" % (path, e))
            continue
        line = "%-40s priorities %3d-%3d, %2d in the first pass" % (
            path, min(v), max(v), sum(p < PRI_PASS for p in v))
        if max(v) > PRI_MAX:
            line += "  !! priority > %d is never drawn" % PRI_MAX
        print(line)

    for m in MODELS:
        missing = []
        for pre, suf in MODEL_PACKS:
            for ext in (".pac", ".hed"):
                if find(root, pre + m + suf + ext) is None:
                    missing.append(pre + m + suf + ext)
        sets = sorted(f for f in os.listdir(root)
                      if f.lower().startswith("aud_set_%s_" % m) and f.lower().endswith(".tbb"))
        counts = []
        for pre, suf in MODEL_PACKS:
            p = find(root, pre + m + suf + ".pac")
            h = pac.load_header(p) if p else None
            counts.append(h.count if h else 0)
        line = "  model %d %s  packs %s  aud_set %d" % (
            MODELS.index(m), m, "/".join(map(str, counts)), len(sets))
        if missing:
            line += "  !! missing %s" % ", ".join(missing)
        if not sets:
            line += "  !! no aud_set table"
        print(line)

    bpath = find(root, "build_stadium.tbb")
    if bpath is None:
        print("%-40s !! missing" % os.path.join(root, "BUILD_STADIUM.TBB"))
        return
    try:
        b = Build(bpath)
    except (ValueError, struct.error) as e:
        print("%-40s !! %s" % (bpath, e))
        return
    use = Counter(r[0] for r in b.rows)
    line = "%-40s %d stadiums; per model %s" % (
        bpath, len(b.rows), " ".join("%d:%d" % (k, use[k]) for k in sorted(use)))
    probs = b.problems()
    if param:
        sd = find(param, "stadium_data.tbb")
        if sd:
            _, t = tbb.load(sd)
            n = t[0].size // STADIUM_DATA_ROW
            if n != len(b.rows):
                probs.append("PARAM/STADIUM_DATA has %d stadiums" % n)
    if probs:
        line += "  !! " + "; ".join(probs)
    print(line)


def cmd_pri(path):
    for i, p in enumerate(read_pri(path)):
        print("  slot %2d  priority %3d  pass %d" % (i, p, 1 if p < PRI_PASS else 2))


def cmd_build(root, sid):
    b = Build(find(root, "build_stadium.tbb"))
    r = b.rows[sid]
    print("stadium %d: model %d (%s)" % (sid, r[0], MODELS[r[0]] if r[0] < len(MODELS) else "?"))
    print("  bytes 1-115: %s" % r[1:116].hex(" "))
    print("  bytes 116-127: %s" % " ".join(str(x) for x in r[BUILD_ADVERT]))
    print("  byte 128: %d" % r[128])
    if r[0] < len(b.model_rows):
        print("  model row (table 1): %s" % " ".join(str(x) for x in b.model_rows[r[0]]))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) in (1, 2):
        cmd_info(args[0], args[1] if len(args) == 2 else None)
    elif cmd == "pri" and len(args) == 1:
        cmd_pri(args[0])
    elif cmd == "build" and len(args) == 2:
        cmd_build(args[0], int(args[1], 0))
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
