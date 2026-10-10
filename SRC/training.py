# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Training tables: PARAM/TRAINING_LIST.TBB, for Let's Make a Soccer Team!
(PS2).

Thirteen TBB1 tables of signed bytes. The training module (SIMPRG.REL
0x159998) takes their resource from its load list (0x23d618 / 0x23d690)
and keeps a pointer to each table (CTblData::GetDataHeadPoint); SLES
0x246540 reads table 11 by name. See DOC/TRAINING_FORMAT.md.

  table  module  rows x cols  what (accessor)
  0      +0x48   29 x 65      team practices 0-28: growth per ability and
                              fatigue (0x159fb8: row * 65 + column)
  1      +0x4c   110 x 65     practices 29-138 (0x15a070: (no - 29) * 65)
  2      +0x6c   64           each ability's group: 0 physical, 1 skill,
                              2 mental (0x15a0a0, 0x15a128)
  3-5    +0x54.. 16 x 25      ability decline by growth type (PlPinfo
                              +0x1e2/3/4) and age 16-40 (0x159eb0-0x159f20),
                              taken from the experience (0x159284)
  6      +0x60   16 x 71      stadium equipment: growth bonus, % (0x159d3c)
  7      +0x64   36 x 71      club-house equipment (0x159cd8)
  8      +0x68   18 x 71      youth-house equipment, for the youth team
  9      +0x70   64           the staff ability that coaches each ability
                              (0x159b68, 0x15ab58)
  10     +0x50   87 x 65      training camps by camp type (0x15a040,
                              pwkSche_GetCampType)
  11     (SLES)  13 x 65      match growth by pitch position
                              (pwkMatchGrow_Grow 0x246830: PlPinfo +4)
  12     +0x74   28 x 65      youth-team practices (0x15ac48)

Columns 0-63 are the abilities (PlAbilNo); column 64 of the 65-wide
tables is the practice's fatigue (0x1590c8, plPinfo_CalcPracTired).

Usage:
    python training.py info      <TRAINING_LIST.TBB | DAT/PARAM>
    python training.py show      <TRAINING_LIST.TBB> [<table> [<row> ...]]
    python training.py set       <in.TBB> <out.TBB> <table> <row> <column>=<value> ... [<table> <row> ...]
    python training.py roundtrip <TRAINING_LIST.TBB>

<table> is a number 0-12 or a name (team, practice, group, decline_physical,
decline_skill, decline_mental, stadium, clubhouse, youthhouse, staff, camp,
match, youth). A row is the practice number for team and practice (0-138),
the age for the decline tables' columns (16-40), else a number from 0. A
column is an ability number or name, `fatigue` (64), or 65-70 for the
equipment tables. `set` writes a same-size file for patch_disc.py, which
also patches the copies (entry 10 of PRELOAD/SIMFILE0-6.PAC, --copies).
"""
import os
import struct
import sys

import tbb

FILE = "TRAINING_LIST.TBB"
ABILITIES = 64                  # PlAbilNo 0-63; the module's loops stop at 0x40
FATIGUE = 64                    # 0x1590cc / 0x159100: column 0x40
PRACTICES = 139                 # 0-28 table 0, 29-138 table 1 (0x15a078: no < 0x1d)
TEAM_PRACTICES = 29
STAFF_ABILITIES = 48
AGE_FIRST, AGES = 16, 25        # 0x159ed0: lb -0x10(age + row * 25)
DECLINE_AGE_LIMIT = 41          # 0x15a144: only below 0x29

# Pitch positions, the rows of table 11 (PlPinfo +4; the scout editor's
# position list, DEBUGPRG.REL 0x13240, in the same order).
POSITIONS = ("GK", "LSB", "RSB", "CB", "LWB", "RWB", "DM", "LSM", "RSM", "OM",
             "LWG", "RWG", "FW")

# The 139 training menu items, DEBUGPRG.REL 0x105b8 (the developers'
# manager editor), in PlPracNo order: (label, English).
PRACTICE_NAMES = (
    ("3-4-3", "system 3-4-3"), ("3-5-2", "system 3-5-2"), ("3-6-1", "system 3-6-1"),
    ("4-3-3", "system 4-3-3"), ("4-4-2", "system 4-4-2"), ("4-5-1", "system 4-5-1"),
    ("5-3-2", "system 5-3-2"), ("5-4-1", "system 5-4-1"),
    ("ダイレクトプレイ", "direct play"), ("ポゼッション", "possession"),
    ("センターアタック", "centre attack"), ("サイドアタック", "side attack"),
    ("コンビA", "combination A"), ("コンビB", "combination B"), ("コンビC", "combination C"),
    ("コンビD", "combination D"), ("コンビE", "combination E"),
    ("プレッシング", "pressing"), ("カバーリング", "covering"),
    ("オフサイドトラップ", "offside trap"), ("スピード", "speed"), ("パワー", "power"),
    ("スタミナ", "stamina"), ("紅白戦", "practice match"), ("連携", "teamwork"),
    ("セットプレイ", "set plays"), ("コンディショニング", "conditioning"), ("休養", "rest"),
    ("臨時休養", "extra rest"),
    ("長所を伸ばす", "develop strengths"), ("平均的に", "balanced"),
    ("短所を補足", "cover weaknesses"),
    ("シュート", "shooting"), ("パス", "passing"), ("ドリブル", "dribbling"),
    ("セットプレイ", "set plays (FW)"), ("タックル", "tackling"), ("パスカット", "pass cutting"),
    ("カバーリング", "covering (DF)"), ("セットプレイ", "set plays (DF)"), ("セーブ", "saving"),
    ("キャッチ", "catching"), ("飛び出し", "rushing out"),
    ("ペナルティーキック", "penalty kicks"), ("セットプレイ", "set plays (GK)"),
    ("スピード", "speed (physical)"), ("パワー", "power (physical)"),
    ("スタミナ", "stamina (physical)"), ("レスポンス", "response"),
    ("ボディーバランス", "body balance"), ("コンディションアップ", "condition up"),
    ("モチベーションアップ", "motivation up"),
    ("センターフォワード", "style: centre forward"), ("ムービング", "style: moving"),
    ("ポストプレーヤー", "style: post player"), ("飛び出し", "style: breaking forward"),
    ("セカンドストライカー", "style: second striker"), ("ウィング", "style: wing"),
    ("プレイメイカー", "style: playmaker"), ("シャドーストライカー", "style: shadow striker"),
    ("アタッカー", "style: attacker"), ("ダイナモ", "style: dynamo"),
    ("クラッシャー", "style: crusher"), ("カバーリング", "style: covering"),
    ("セントラルMF", "style: central MF"), ("サイドアタッカー", "style: side attacker"),
    ("切れ込み", "style: cutting inside"), ("守備的サイド", "style: defensive wide"),
    ("スイーパー", "style: sweeper"), ("リベロ", "style: libero"),
    ("ストッパー", "style: stopper"), ("センターバック", "style: centre back"),
    ("オーソドックス", "style: orthodox GK"), ("リベロGK", "style: libero GK"),
    ("ピンポイントシュート", "pinpoint shooting"), ("ベルベットパス", "velvet pass"),
    ("テクニカルドリブル", "technical dribbling"),
    ("フリーキックオフェンス", "free kick attack"),
    ("オフェンス総合練習", "all-round attack"), ("ロングシュート", "long shots"),
    ("ダイレクトシュート", "first-time shots"), ("ポストプレイ", "post play"),
    ("プルアウェイ", "pull away"), ("1対1シュート", "1-on-1 shooting"),
    ("キャノンシュート", "cannon shot"), ("キングオブドリブル", "king of dribbling"),
    ("ジャックナイフ", "jackknife"), ("ボールタッチ", "ball touch"),
    ("ボールキープ", "ball keeping"), ("センタリング", "centring"),
    ("アーリークロス", "early cross"), ("ダイレクトクロス", "first-time cross"),
    ("トラップ", "trapping"), ("ハードタックル", "hard tackle"),
    ("インターセプト", "interception"), ("フォローアップ", "follow-up"),
    ("フリーキックディフェンス", "free kick defence"),
    ("ディフェンス総合練習", "all-round defence"), ("競り合い", "challenges"),
    ("チャージ", "charge"), ("マンマーク", "man marking"),
    ("空中戦強化", "aerial strength"), ("1000本セーブ", "1000 saves"),
    ("1000本キャッチ", "1000 catches"), ("守備範囲拡大", "wider range"),
    ("PKストップ", "PK stopping"), ("フリーキック対応", "free kick handling"),
    ("キーパー総合練習", "all-round keeping"), ("ポジショニング", "positioning"),
    ("フィード力強化", "distribution"), ("1対1セーブ", "1-on-1 saves"),
    ("足技", "footwork"), ("加速力トレーニング", "acceleration training"),
    ("高負荷筋力トレーニング", "heavy strength training"),
    ("筋持久力トレーニング", "muscle endurance training"),
    ("瞬発力トレーニング", "explosive power training"),
    ("バランストレーニング", "balance training"),
    ("フィジカル総合練習", "all-round physical"), ("メンタル強化", "mental strength"),
    ("攻撃意識", "attack awareness"), ("守備意識", "defence awareness"),
    ("サポート意識", "support awareness"), ("コンディションサポート", "condition support"),
    ("メンタルサポート", "mental support"), ("疲労回復", "fatigue recovery"),
    ("怪我早期回復", "early injury recovery"), ("持久サーキット", "endurance circuit"),
    ("チューブ走", "tube running"), ("エアロバイク", "exercise bike"),
    ("インターバル走", "interval running"), ("低周波療法", "low-frequency therapy"),
    ("超音波療法", "ultrasound therapy"), ("呼吸法", "breathing"),
    ("レクリエーション", "recreation"), ("リハビリ", "rehabilitation"),
    ("リーダー育成", "leadership"), ("戦術講座", "tactics lecture"),
    ("システム講座", "system lecture"), ("サカつくプレイ", "Sakatsuku play"),
)
assert len(PRACTICE_NAMES) == PRACTICES


class Table:
    """How one table is laid out: `rows` x `cols` signed bytes, the first
    row's number, the values the code reads and a name for each row."""

    def __init__(self, index, name, rows, cols, title, first=0, lo=-128, hi=127, unsigned=False):
        self.index, self.name, self.rows, self.cols = index, name, rows, cols
        self.title, self.first, self.lo, self.hi = title, first, lo, hi
        self.unsigned = unsigned

    @property
    def size(self):
        return self.rows * self.cols

    def row_name(self, row):
        """Row `row` (as numbered for this table) in words."""
        if self.name in ("team", "practice"):
            jp, en = PRACTICE_NAMES[row]
            return "%d %s" % (row, en)
        if self.name == "match":
            return "%d %s" % (row, POSITIONS[row])
        if self.name.startswith("decline"):
            return "growth type %d" % row
        if self.name in ("group", "staff"):
            return ""
        return "%d" % row


TABLES = (
    Table(0, "team", TEAM_PRACTICES, 65, "team practices 0-28"),
    Table(1, "practice", PRACTICES - TEAM_PRACTICES, 65, "practices 29-138",
          first=TEAM_PRACTICES),
    Table(2, "group", 1, ABILITIES, "ability groups: 0 physical, 1 skill, 2 mental",
          lo=0, hi=2, unsigned=True),
    Table(3, "decline_physical", 16, AGES, "decline by physical growth type and age"),
    Table(4, "decline_skill", 16, AGES, "decline by skill growth type and age"),
    Table(5, "decline_mental", 16, AGES, "decline by mental growth type and age"),
    Table(6, "stadium", 16, 71, "stadium equipment bonus, %"),
    Table(7, "clubhouse", 36, 71, "club-house equipment bonus, %"),
    Table(8, "youthhouse", 18, 71, "youth-house equipment bonus, % (youth team)"),
    Table(9, "staff", 1, ABILITIES, "the staff ability that coaches each ability",
          lo=0, hi=STAFF_ABILITIES - 1, unsigned=True),
    Table(10, "camp", 87, 65, "training camps by camp type"),
    Table(11, "match", len(POSITIONS), 65, "match growth by pitch position"),
    Table(12, "youth", 28, 65, "youth-team practices"),
)
BY_NAME = {t.name: t for t in TABLES}


def ability_names():
    import pbdata
    return pbdata.ABILITY_NAMES


def column_name(table, col):
    if table.name.startswith("decline"):
        return "age %d" % (AGE_FIRST + col)
    if col < ABILITIES:
        return ability_names()[col]
    if col == FATIGUE:
        return "fatigue"
    return "column %d" % col


def find_table(text):
    if text.isdigit() and int(text) < len(TABLES):
        return TABLES[int(text)]
    if text in BY_NAME:
        return BY_NAME[text]
    raise ValueError("no table %r; tables are 0-%d or %s"
                     % (text, len(TABLES) - 1, ", ".join(BY_NAME)))


def find_column(table, text):
    """A column by number, ability name, `fatigue`, or for the decline
    tables `age<n>` / the age."""
    if table.name.startswith("decline"):
        age = int(text[3:] if text.startswith("age") else text, 0)
        col = age - AGE_FIRST
    elif text == "fatigue":
        col = FATIGUE
    elif text.lstrip("-").isdigit():
        col = int(text)
    else:
        names = [n.lower() for n in ability_names()]
        key = text.lower().replace("_", " ")
        if key not in names:
            raise ValueError("no column %r" % text)
        col = names.index(key)
    if not 0 <= col < table.cols:
        raise ValueError("%s has columns 0-%d" % (table.name, table.cols - 1))
    return col


class Training:
    """The 13 tables as lists of rows of ints."""

    def __init__(self, raw):
        if len(raw) != len(TABLES):
            raise ValueError("%d tables, expected %d" % (len(raw), len(TABLES)))
        self.values = []
        for t, r in zip(TABLES, raw):
            if len(r.data) != t.size:
                raise ValueError("table %d is %d bytes, not %d x %d"
                                 % (t.index, len(r.data), t.rows, t.cols))
            fmt = "%dB" if t.unsigned else "%db"
            self.values.append(list(struct.unpack(fmt % t.size, r.data)))

    def get(self, table, row, col):
        return self.values[table.index][(row - table.first) * table.cols + col]

    def set(self, table, row, col, value):
        """Set one value, within what the code reads; returns the old one."""
        if not table.first <= row < table.first + table.rows:
            raise ValueError("%s has rows %d-%d" % (table.name, table.first,
                                                    table.first + table.rows - 1))
        if not table.lo <= value <= table.hi:
            raise ValueError("%s values are %d-%d" % (table.name, table.lo, table.hi))
        i = (row - table.first) * table.cols + col
        old = self.values[table.index][i]
        self.values[table.index][i] = value
        return old

    def encode(self, index):
        t = TABLES[index]
        return struct.pack(("%dB" if t.unsigned else "%db") % t.size, *self.values[index])


def load(path):
    if os.path.isdir(path):
        path = os.path.join(path, FILE)
    with open(path, "rb") as f:
        buf = f.read()
    end, raw = tbb.parse(buf)
    return buf, end, raw, Training(raw)


def check(tr):
    """Problems with the tables against what the code reads."""
    problems = []
    for t in TABLES:
        bad = [i for i, v in enumerate(tr.values[t.index]) if not t.lo <= v <= t.hi]
        if bad:
            problems.append("table %d (%s): %d values outside %d-%d, first at %d"
                            % (t.index, t.name, len(bad), t.lo, t.hi, bad[0]))
    return problems


def encode_file(buf, end, raw, tr):
    problems = check(tr)
    if problems:
        raise ValueError("; ".join(problems))
    for i, r in enumerate(raw):
        r.data = tr.encode(i)
    out = tbb.build(raw, end, tbb.trailer(buf, raw))
    if len(out) != len(buf):
        raise ValueError("rebuilt file is %d bytes, not %d" % (len(out), len(buf)))
    return out


# --- commands ----------------------------------------------------------------

def cmd_info(path):
    try:
        _, _, raw, tr = load(path)
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))
        return
    print("%s: %d tables" % (path, len(raw)))
    problems = check(tr)
    for t in TABLES:
        v = tr.values[t.index]
        line = "  %2d %-16s %3d x %2d  %-48s values %d..%d" % (
            t.index, t.name, t.rows, t.cols, t.title, min(v), max(v))
        bad = [p for p in problems if p.startswith("table %d " % t.index)]
        if bad:
            line += "  !! " + "; ".join(bad)
        print(line)
    for name in ("team", "practice", "camp", "match", "youth"):
        t = BY_NAME[name]
        cols = [tr.get(t, r, FATIGUE) for r in range(t.first, t.first + t.rows)]
        print("  %-8s fatigue column: %s" % (name, " ".join(str(c) for c in cols)))
    for name in ("stadium", "clubhouse", "youthhouse"):
        t = BY_NAME[name]
        used = [c for c in range(ABILITIES, t.cols)
                if any(tr.get(t, r, c) for r in range(t.rows))]
        print("  %-10s columns past the abilities with values: %s (no reader)"
              % (name, " ".join(map(str, used)) or "none"))


def cmd_show(path, args):
    _, _, _, tr = load(path)
    tables = [find_table(args[0])] if args else TABLES
    rows = [int(a, 0) for a in args[1:]]
    for t in tables:
        print("table %d %s: %s" % (t.index, t.name, t.title))
        for row in range(t.first, t.first + t.rows):
            if rows and row not in rows:
                continue
            if t.name in ("group", "staff"):
                import pbdata
                for col in range(t.cols):
                    v = tr.get(t, row, col)
                    what = (("physical", "skill", "mental")[v] if t.name == "group"
                            else pbdata.STAFF_ABILITY_NAMES[v])
                    print("  %2d %-24s %2d %s" % (col, column_name(t, col), v, what))
                continue
            vals = [(col, tr.get(t, row, col)) for col in range(t.cols)]
            if t.name.startswith("decline"):
                text = " ".join("%d" % v for _, v in vals)
            else:
                text = ", ".join("%s %+d" % (column_name(t, c), v) for c, v in vals if v)
            print("  %-28s %s" % (t.row_name(row), text or "-"))


def cmd_set(path, out_path, args):
    if os.path.abspath(out_path) == os.path.abspath(path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    buf, end, raw, tr = load(path)
    table = row = None
    i = 0
    try:
        while i < len(args):
            a = args[i]
            if "=" in a:
                if row is None:
                    raise ValueError("give a table and a row before %r" % a)
                name, value = a.split("=", 1)
                col = find_column(table, name)
                old = tr.set(table, row, col, int(value, 0))
                print("%s %d %s: %d -> %d" % (table.name, row, column_name(table, col),
                                              old, int(value, 0)))
                i += 1
            elif i + 1 < len(args) and "=" not in args[i + 1] and not a.lstrip("-").isdigit():
                table, row = find_table(a), int(args[i + 1], 0)
                i += 2
            elif table is not None and a.lstrip("-").isdigit():
                row = int(a, 0)
                i += 1
            else:
                raise ValueError("expected <table> <row> before %r" % a)
        out = encode_file(buf, end, raw, tr)
    except ValueError as e:
        raise SystemExit(str(e))
    with open(out_path, "wb") as f:
        f.write(out)
    print("wrote %s" % out_path)


def cmd_roundtrip(path):
    buf, end, raw, tr = load(path)
    same = all(tr.encode(i) == r.data for i, r in enumerate(raw))
    print("%d tables  %s" % (len(raw), "identical" if same else "!! re-encoded tables differ"))
    try:
        out = encode_file(buf, end, raw, tr)
    except ValueError as e:
        out = None
        print("%s: !! %s" % (path, e))
    if out is not None:
        print("%s: %s" % (path, "rebuilt file identical" if out == buf else "!! rebuilt file differs"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "show" and args:
        cmd_show(args[0], args[1:])
    elif cmd == "set" and len(args) >= 5:
        cmd_set(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and len(args) == 1:
        cmd_roundtrip(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
