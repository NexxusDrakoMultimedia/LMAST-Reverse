"""MBB1 message file reader for Let's Make a Soccer Team! (PS2).

All of the game's text lives in DAT/MESSAGE/MES.PAC, a BINPAC of 3738
`<category>_<language>.mbb` files (534 categories x 7 language slots). Each
.mbb is a 0x20-byte header and a list of {u16 id, u16 len, bytes} records
whose text mixes plain characters with ESC (0x1B) control sequences. The
layout and the escape opcodes were confirmed against SLES_541.51 (Msg::
CMsgSubCategory::Initialize, Msg::CMsgNotify* Evaluate, ...) - see
DOC/MBB_FORMAT.md.

Text is rendered with {tags} for escapes (a literal '{' is written '{{'):

    ESC 0x2F           newline               \\n
    ESC 0x10/11/12     runtime variable      {var:CAT:ID}
    ESC 0x20 / 0x21    colour on / off       {color:N} ... {/color}
    ESC 0xC1           speaker name          {name:N}
    ESC 0xC2           portrait expression   {face:SLOT:N}
    ESC 0xC3           unknown, one u16      {c3:N}
    raw 0x0A / 0x0D    (effect unconfirmed)  {lf} / {cr}
    EU 0x10-0x13       pad button glyphs     {circle} {cross} {triangle} {square}

Usage:
    python mbb.py info <MES.PAC | file.mbb | dir> ...        # layout checks + totals
    python mbb.py list <MES.PAC | file.mbb | dir> ...        # one line per file
    python mbb.py dump <MES.PAC | file.mbb | dir> ... [--lang N] [--cat N] [--raw]
    python mbb.py csv  <MES.PAC | dir> <out.csv>             # one row per (category, id), one column per language

Languages (FC_EURO_LOCALIZE): 0 Japanese, 1 English, 2 French, 3 German,
4 Italian, 5 Spanish, 6 unused slot (mostly English).
"""
import csv
import os
import struct
import sys

from pac import BinPac

MAGIC = b"MBB1"
HEADER_SIZE = 0x20
ESC = 0x1B
LANGS = ["jp", "en", "fr", "de", "it", "es", "x6"]

# Japanese: bytes 0x00-0x1F outside escapes are voiced katakana. The game's
# table at 0x531c28 (used by Param::plMisc_HanZenKana) maps them to full-width
# Shift-JIS; they are written here in half-width form to match the half-width
# katakana (0xA1-0xDF) they sit between. 0x09/0x0A/0x0D/0x1B map to a space
# in the table (tab, LF, CR and ESC keep their usual meaning).
JP_KANA = {
    0x02: "ｶﾞ", 0x03: "ｷﾞ", 0x04: "ｸﾞ", 0x05: "ｹﾞ", 0x06: "ｺﾞ",
    0x07: "ｻﾞ", 0x08: "ｼﾞ", 0x0B: "ｽﾞ", 0x0C: "ｾﾞ", 0x0E: "ｿﾞ",
    0x0F: "ﾀﾞ", 0x10: "ﾁﾞ", 0x11: "ﾂﾞ", 0x12: "ﾃﾞ", 0x13: "ﾄﾞ",
    0x14: "ﾊﾞ", 0x15: "ﾋﾞ", 0x16: "ﾌﾞ", 0x17: "ﾍﾞ", 0x18: "ﾎﾞ",
    0x19: "ﾊﾟ", 0x1A: "ﾋﾟ", 0x1C: "ﾌﾟ", 0x1D: "ﾍﾟ", 0x1E: "ﾎﾟ",
    0x1F: "ｳﾞ",
}
# European languages: pad-button glyphs in the font (the Japanese files use
# Shift-JIS ○×△□ for the same messages).
EU_BUTTONS = {0x10: "{circle}", 0x11: "{cross}", 0x12: "{triangle}", 0x13: "{square}"}


class Mbb:
    def __init__(self, buf, name=""):
        self.name = name
        if buf[:4] != MAGIC:
            raise ValueError("%s: not an MBB1 file" % name)
        # +0x08 is the sub-category id (Msg::CMsgCategory::AddSubCategory);
        # MES.PAC uses one sub-category per language.
        (self.category, self.lang, count, self.data_size,
         *self.reserved) = struct.unpack_from("<4I3I", buf, 4)
        self.records = []
        p = HEADER_SIZE
        for _ in range(count):
            rid, n = struct.unpack_from("<HH", buf, p)
            self.records.append((rid, bytes(buf[p + 4:p + 4 + n])))
            p += 4 + n
        self.end = p
        self.size = len(buf)
        self.padding = bytes(buf[p:])

    def problems(self):
        out = []
        if self.data_size != self.size - HEADER_SIZE:
            out.append("data_size %#x != file size - 0x20" % self.data_size)
        if any(self.reserved):
            out.append("reserved words not zero")
        if self.padding.strip(b"\0") or self.size % 4:
            out.append("unexpected tail %r" % self.padding)
        for rid, s in self.records:
            try:
                list(tokens(s))
            except ValueError as e:
                out.append("id %d: %s" % (rid, e))
        return out

    def duplicate_ids(self):
        """Ids stored more than once. The game qsorts and bsearches records,
        so which copy it finds is undefined."""
        seen, dups = set(), []
        for rid, _ in self.records:
            if rid in seen and rid not in dups:
                dups.append(rid)
            seen.add(rid)
        return dups


def tokens(s):
    """Yield ('esc', op, args) and ('byte', b) items."""
    p = 0
    while p < len(s):
        if s[p] == ESC:
            if p + 3 > len(s) or p + 3 + s[p + 2] > len(s):
                raise ValueError("truncated escape at %d" % p)
            n = s[p + 2]
            yield "esc", s[p + 1], s[p + 3:p + 3 + n]
            p += 3 + n
        else:
            yield "byte", s[p], None
            p += 1


def _esc_text(op, a):
    if op == 0x2F:
        return "\n"
    if op in (0x10, 0x11, 0x12):
        cat = int.from_bytes(a[:-2], "little")
        return "{var:%d:%d}" % (cat, struct.unpack_from("<H", a, len(a) - 2)[0])
    if op == 0x20 and len(a) == 1:
        return "{color:%d}" % a[0]
    if op == 0x21 and not a:
        return "{/color}"
    if op == 0xC1 and len(a) == 2:
        return "{name:%d}" % struct.unpack("<H", a)
    if op == 0xC2 and len(a) == 4:
        return "{face:%d:%d}" % struct.unpack("<HH", a)
    if op == 0xC3 and len(a) == 2:
        return "{c3:%d}" % struct.unpack("<H", a)
    return "{esc:%02x:%s}" % (op, a.hex())


def decode(s, lang):
    """Render one record's bytes as text with {tags} for control codes."""
    out, run = [], bytearray()
    codec = "cp932" if lang == 0 else "cp850"

    def flush():
        if run:
            out.append(run.decode(codec, "replace").replace("{", "{{"))
            run.clear()

    for kind, b, args in tokens(s):
        if kind == "esc":
            flush()
            out.append(_esc_text(b, args))
        elif b in (0x0A, 0x0D):
            flush()
            out.append("{lf}" if b == 0x0A else "{cr}")
        elif b < 0x20:
            flush()
            if lang == 0 and b in JP_KANA:
                out.append(JP_KANA[b])
            elif lang != 0 and b in EU_BUTTONS:
                out.append(EU_BUTTONS[b])
            else:
                out.append("{x%02x}" % b)
        else:
            run.append(b)
    flush()
    return "".join(out)


def iter_files(paths):
    """Yield (label, Mbb) from MES.PAC-style BINPACs, .mbb files and dirs."""
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.upper().endswith((".MBB", ".PAC")):
                        yield from iter_files([os.path.join(root, f)])
            continue
        with open(p, "rb") as f:
            buf = f.read()
        if buf[10:16] == b"BINPAC":
            for off, size, name, _ in BinPac(buf).entries:
                if buf[off:off + 4] == MAGIC:
                    yield name, Mbb(buf[off:off + size], name)
        elif buf[:4] == MAGIC:
            name = os.path.basename(p)
            yield name, Mbb(buf, name)


def cmd_info(paths):
    files = bad = 0
    dup_files = []
    cats, recs, ops = set(), [0] * len(LANGS), {}
    for label, m in iter_files(paths):
        files += 1
        cats.add(m.category)
        if 0 <= m.lang < len(LANGS):
            recs[m.lang] += len(m.records)
        expect = "%d_%d.mbb" % (m.category, m.lang)
        probs = m.problems()
        if label.lower() != expect and not label.lower().endswith("_" + expect):
            probs.append("name doesn't match header (%s)" % expect)
        for _, s in m.records:
            for kind, b, _a in tokens(s):
                if kind == "esc":
                    ops[b] = ops.get(b, 0) + 1
        dups = m.duplicate_ids()
        if dups:
            dup_files.append("%s (%d)" % (label, len(dups)))
        if probs:
            bad += 1
            print("%-20s %s" % (label, "; ".join(probs)))
    print("%d files, %d categories, %d with problems" % (files, len(cats), bad))
    print("records per language: " + ", ".join(
        "%d %s=%d" % (i, n, c) for i, (n, c) in enumerate(zip(LANGS, recs))))
    if dup_files:
        print("repeated ids (not an error): " + ", ".join(dup_files))
    print("escapes: " + ", ".join("%#04x=%d" % kv for kv in sorted(ops.items())))


def cmd_list(paths):
    for label, m in iter_files(paths):
        print("%-20s cat=%-7d lang=%d records=%-5d size=%d" % (
            label, m.category, m.lang, len(m.records), m.size))


def cmd_dump(paths, lang, cat, raw):
    for label, m in iter_files(paths):
        if (lang is not None and m.lang != lang) or (cat is not None and m.category != cat):
            continue
        print("== %s (category %d, %s)" % (label, m.category, LANGS[m.lang]))
        for rid, s in m.records:
            if raw:
                print("%6d  %s" % (rid, s.hex(" ")))
            else:
                text = decode(s, m.lang).replace("\n", "\n        ")
                print("%6d  %s" % (rid, text))


def cmd_csv(paths, out_path):
    # `copy` numbers repeated ids within a file (see Mbb.duplicate_ids).
    table = {}
    for _, m in iter_files(paths):
        seen = {}
        for rid, s in m.records:
            k = seen[rid] = seen.get(rid, -1) + 1
            table.setdefault((m.category, rid, k), [""] * len(LANGS))[m.lang] = decode(s, m.lang)
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["category", "id", "copy"] + LANGS)
        for key in sorted(table):
            w.writerow(list(key) + table[key])
    print("%d messages -> %s" % (len(table), out_path))


def _opt(args, flag):
    if flag in args:
        k = args.index(flag)
        v = int(args[k + 1])
        del args[k:k + 2]
        return v
    return None


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], list(argv[2:])
    if cmd == "info":
        cmd_info(args)
    elif cmd == "list":
        cmd_list(args)
    elif cmd == "dump":
        lang, cat = _opt(args, "--lang"), _opt(args, "--cat")
        raw = "--raw" in args
        cmd_dump([a for a in args if a != "--raw"], lang, cat, raw)
    elif cmd == "csv" and len(args) >= 2:
        cmd_csv(args[:-1], args[-1])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
