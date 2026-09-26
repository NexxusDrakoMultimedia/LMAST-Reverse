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
    ESC 0xC3           body reaction         {react:N}
    raw 0x0A / 0x0D    (effect unconfirmed)  {lf} / {cr}
    EU 0x10-0x13       pad button glyphs     {circle} {cross} {triangle} {square}

Usage:
    python mbb.py info <MES.PAC | file.mbb | dir> ...        # layout checks + totals
    python mbb.py list <MES.PAC | file.mbb | dir> ...        # one line per file
    python mbb.py dump <MES.PAC | file.mbb | dir> ... [--lang N] [--cat N] [--raw]
    python mbb.py csv  <MES.PAC | dir> <out.csv>             # one row per (category, id), one column per language
    python mbb.py roundtrip <MES.PAC>                        # text -> bytes -> pack must give the same bytes
    python mbb.py set    <MES.PAC> <out.PAC> <cat> <id> <lang> "<text>" [--copy N]
    python mbb.py import <MES.PAC> <edits.csv> <out.PAC>     # apply a CSV in `csv` format

Writing: text uses the same {tags} as dump and csv (a literal '{' is '{{').
In `set`, \\n in the text is a line break. `import` takes a CSV made by
`csv`, saved as UTF-8; rows and language columns may be deleted, and only
non-empty cells that differ from the current text are applied.

Sizes: an edited .mbb that still fits its original size is zero-padded to
it (allowed by Initialize, 0x30d1f4). A bigger one grows into the unused
rest of its 0x800-aligned slot in MES.PAC, and only its size in the
archive header changes (the loader reads (size >> 11) + 1 sectors,
0x10cf1c). A file too big for its slot is refused. The output always has
MES.PAC's size and every entry keeps its offset, so patch_disc.py can
write it to a disc; --copies updates the PRELOAD copies of files that
kept their size and warns about copies of grown files, which keep the
old text.

Languages (FC_EURO_LOCALIZE): 0 Japanese, 1 English, 2 French, 3 German,
4 Italian, 5 Spanish, 6 unused slot (mostly English).
"""
import bisect
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

    def build(self, size=None):
        """The file's bytes from self.records. The tail is zero-padded to a
        multiple of 4, or to `size` if given: Initialize (0x30d1f4) sizes
        its string buffer from data_size and walks `count` records, so
        zeros after the last record are allowed. A data_size smaller than
        the records would overflow that buffer, which build() can't do."""
        body = bytearray()
        for rid, s in self.records:
            if len(s) > 0xFFFF:
                raise ValueError("%s id %d: %d bytes (at most 65535)" % (self.name, rid, len(s)))
            body += struct.pack("<HH", rid, len(s)) + s
        total = HEADER_SIZE + len(body)
        total += -total % 4
        if size is not None:
            if total > size:
                raise ValueError("%s: %d bytes, %d over its %d" % (
                    self.name, total, total - size, size))
            total = size
        head = MAGIC + struct.pack("<4I3I", self.category, self.lang, len(self.records),
                                   total - HEADER_SIZE, *self.reserved)
        return (head + bytes(body)).ljust(total, b"\0")

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
        return "{react:%d}" % struct.unpack("<H", a)
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


JP_KANA_BYTES = {v: k for k, v in JP_KANA.items()}
EU_BUTTON_BYTES = {v[1:-1]: k for k, v in EU_BUTTONS.items()}


def _esc(op, args=b""):
    return bytes([ESC, op, len(args)]) + args


def _tag_bytes(tag, lang):
    """One {tag} (without braces) -> bytes; the inverse of _esc_text."""
    name, _, rest = tag.partition(":")
    f = rest.split(":") if rest else []
    if name == "var" and len(f) == 2:
        cat, var = int(f[0]), int(f[1])
        # The narrowest form that holds the category, as the game data uses.
        for op, n in ((0x10, 1), (0x11, 2), (0x12, 4)):
            if cat < 1 << (8 * n):
                return _esc(op, cat.to_bytes(n, "little") + struct.pack("<H", var))
        raise ValueError("{%s}: category too large" % tag)
    if name == "color" and len(f) == 1:
        return _esc(0x20, bytes([int(f[0])]))
    if tag == "/color":
        return _esc(0x21)
    if name == "name" and len(f) == 1:
        return _esc(0xC1, struct.pack("<H", int(f[0])))
    if name == "face" and len(f) == 2:
        return _esc(0xC2, struct.pack("<HH", int(f[0]), int(f[1])))
    if name == "react" and len(f) == 1:
        return _esc(0xC3, struct.pack("<H", int(f[0])))
    if name == "esc" and len(f) == 2:
        return _esc(int(f[0], 16), bytes.fromhex(f[1]))
    if tag in ("lf", "cr"):
        return b"\n" if tag == "lf" else b"\r"
    if lang != 0 and tag in EU_BUTTON_BYTES:
        return bytes([EU_BUTTON_BYTES[tag]])
    if len(tag) == 3 and tag[0] == "x":
        return bytes([int(tag[1:], 16)])
    raise ValueError("unknown tag {%s}" % tag)


def encode(text, lang):
    """Text with {tags}, as decode() writes it -> the record's bytes."""
    codec = "cp932" if lang == 0 else "cp850"
    out = bytearray()
    i = 0
    while i < len(text):
        c = text[i]
        if text.startswith("{{", i):
            out += b"{"
            i += 2
        elif c == "{":
            j = text.find("}", i)
            if j < 0:
                raise ValueError("unclosed '{' at %d (write '{{' for a literal '{')" % i)
            out += _tag_bytes(text[i + 1:j], lang)
            i = j + 1
        elif c == "\n":
            out += _esc(0x2F)
            i += 1
        elif c < " ":
            # decode() never writes raw control characters, so one here is
            # a stray (a CR from a spreadsheet, a tab); {lf}, {cr} and
            # {xNN} write the bytes deliberately.
            raise ValueError("control character %r at %d (use a {tag})" % (c, i))
        elif lang == 0 and text[i:i + 2] in JP_KANA_BYTES:
            out.append(JP_KANA_BYTES[text[i:i + 2]])
            i += 2
        else:
            try:
                out += c.encode(codec)
            except UnicodeEncodeError:
                raise ValueError("%r at %d has no %s code" % (c, i, codec)) from None
            i += 1
    return bytes(out)


def iter_files(paths, on_error=None):
    """Yield (label, Mbb) from MES.PAC-style BINPACs, .mbb files and dirs.

    With on_error, a file or entry that fails to parse is passed to
    on_error(label, exception) and skipped; without it the error propagates."""
    def parse(label, make):
        try:
            return make()
        except (ValueError, struct.error) as e:
            if on_error is None:
                raise
            on_error(label, e)
            return None

    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    if f.upper().endswith((".MBB", ".PAC")):
                        yield from iter_files([os.path.join(root, f)], on_error)
            continue
        with open(p, "rb") as f:
            buf = f.read()
        if buf[10:16] == b"BINPAC":
            pac = parse(os.path.basename(p), lambda: BinPac(buf))
            for off, size, name, _ in pac.entries if pac else ():
                if buf[off:off + 4] == MAGIC:
                    m = parse(name, lambda: Mbb(buf[off:off + size], name))
                    if m:
                        yield name, m
        elif buf[:4] == MAGIC:
            name = os.path.basename(p)
            m = parse(name, lambda: Mbb(buf, name))
            if m:
                yield name, m


def cmd_info(paths):
    files = bad = 0
    dup_files = []
    cats, recs, ops = set(), [0] * len(LANGS), {}

    def unparsed(label, e):
        nonlocal files, bad
        files += 1
        bad += 1
        print("%-20s  !! %s" % (label, e))

    for label, m in iter_files(paths, unparsed):
        files += 1
        cats.add(m.category)
        if 0 <= m.lang < len(LANGS):
            recs[m.lang] += len(m.records)
        expect = "%d_%d.mbb" % (m.category, m.lang)
        probs = m.problems()
        if label.lower() != expect and not label.lower().endswith("_" + expect):
            probs.append("name doesn't match header (%s)" % expect)
        for _, s in m.records:
            try:
                for kind, b, _a in tokens(s):
                    if kind == "esc":
                        ops[b] = ops.get(b, 0) + 1
            except ValueError:
                pass  # already reported by m.problems()
        dups = m.duplicate_ids()
        if dups:
            dup_files.append("%s (%d)" % (label, len(dups)))
        if probs:
            bad += 1
            print("%-20s  !! %s" % (label, "; ".join(probs)))
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


def cmd_roundtrip(path):
    """Decode every record to text, encode it back and rebuild each file at
    its own size; the whole pack must come out byte for byte."""
    with open(path, "rb") as f:
        buf = f.read()
    pac = BinPac(buf)
    out = bytearray(buf)
    records = 0
    for off, size, name, _ in pac.entries:
        m = Mbb(buf[off:off + size], name)
        m.records = [(rid, encode(decode(s, m.lang), m.lang)) for rid, s in m.records]
        records += len(m.records)
        out[off:off + size] = m.build(size)
    same = bytes(out) == buf
    print("%d files, %d records rebuilt from text: %s" % (
        len(pac.entries), records, "identical" if same else "DIFFERENT"))
    return 0 if same else 1


def apply_edits(pac_path, out_path, edits):
    """edits: (category, lang, id, copy, text) -> write an edited MES.PAC.

    An edited .mbb that still fits its original size is zero-padded to it,
    so its entry, the header and any PRELOAD copies keep their sizes. A
    bigger one grows into the unused part of its slot: entries start on
    0x800 boundaries and the gap after each is '0' filler, and the game
    reads (size >> 11) + 1 sectors from the header's size (0x10cf1c), so
    only the entry's size field changes. The archive keeps its size and
    every other entry stays put, but a PRELOAD copy of a grown file can't
    be updated (patch_disc.py warns). A file that doesn't fit its slot is
    reported and nothing is written."""
    if os.path.abspath(out_path) == os.path.abspath(pac_path):
        raise SystemExit("write to a new file, not over %s" % pac_path)
    with open(pac_path, "rb") as f:
        buf = f.read()
    pac = BinPac(buf)
    # An entry's slot runs to the next entry's data, or to the end of the
    # archive (which can't grow).
    starts = sorted(off for off, _, _, _ in pac.entries) + [len(buf)]
    files = {}                          # (category, lang) -> (index, off, size, slot, Mbb)
    for i, (off, size, name, _) in enumerate(pac.entries):
        m = Mbb(buf[off:off + size], name)
        slot = starts[bisect.bisect_right(starts, off)] - off
        files[(m.category, m.lang)] = (i, off, size, slot, m)
    changed, errors = {}, []
    for cat, lang, rid, copy, text in edits:
        where = "%d_%d.mbb id %d" % (cat, lang, rid)
        if (cat, lang) not in files:
            errors.append("%s: no such file" % where)
            continue
        m = files[(cat, lang)][4]
        hits = [k for k, (r, _) in enumerate(m.records) if r == rid]
        if copy >= len(hits):
            errors.append("%s: no such message" % where if not hits else
                          "%s: no copy %d" % (where, copy))
            continue
        try:
            new = encode(text, lang)
        except ValueError as e:
            errors.append("%s: %s" % (where, e))
            continue
        k = hits[copy]
        if new != m.records[k][1]:
            m.records[k] = (rid, new)
            changed.setdefault((cat, lang), set()).add((rid, copy))
    out = bytearray(buf)
    report, grown = [], 0
    for key in sorted(changed):
        i, off, size, slot, m = files[key]
        try:
            data = m.build()
        except ValueError as e:
            errors.append(str(e))
            continue
        used = HEADER_SIZE + sum(4 + len(s) for _, s in m.records)
        if len(data) <= size:
            out[off:off + size] = m.build(size)
            report.append("%-16s %4d changed, %6d of %6d bytes used" % (
                m.name, len(changed[key]), used, size))
        elif len(data) <= slot:
            out[off:off + slot] = data + b"0" * (slot - len(data))
            struct.pack_into("<I", out, 0x20 + i * pac.stride + 4, len(data))
            grown += 1
            report.append("%-16s %4d changed, grew %d -> %d bytes (slot %d)" % (
                m.name, len(changed[key]), size, len(data), slot))
        else:
            errors.append("%s: %d bytes, %d more than its slot in the archive holds (%d)" % (
                m.name, len(data), len(data) - slot, slot))
    if errors:
        raise SystemExit("\n".join(["nothing written:"] + ["  " + e for e in errors]))
    with open(out_path, "wb") as f:
        f.write(out)
    for line in report:
        print(line)
    print("%d messages in %d files -> %s" % (
        sum(len(v) for v in changed.values()), len(changed), out_path))
    if grown:
        print("%d file%s grew: patch_disc.py can't update PRELOAD copies of those, "
              "and says which it leaves alone" % (grown, "" if grown == 1 else "s"))


def cmd_set(pac_path, out_path, cat, rid, lang, text, copy):
    apply_edits(pac_path, out_path, [(cat, lang, rid, copy or 0, text)])


def cmd_import(pac_path, csv_path, out_path):
    """Apply a CSV in `csv` format. Rows and language columns may be left
    out; an empty cell, or one equal to the current text, changes nothing."""
    with open(pac_path, "rb") as f:
        buf = f.read()
    pac = BinPac(buf)
    current = {}
    for off, size, name, _ in pac.entries:
        m = Mbb(buf[off:off + size], name)
        seen = {}
        for rid, s in m.records:
            k = seen[rid] = seen.get(rid, -1) + 1
            current[(m.category, m.lang, rid, k)] = decode(s, m.lang)
    edits = []
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        rows = csv.reader(f)
        head = next(rows)
        if head[:2] != ["category", "id"]:
            raise SystemExit("%s: first columns must be category,id" % csv_path)
        cols = {c: i for i, c in enumerate(head)}
        langs = [(LANGS.index(c), i) for c, i in cols.items() if c in LANGS]
        for line, row in enumerate(rows, 2):
            if not any(row):
                continue
            try:
                cat, rid = int(row[0]), int(row[1])
                copy = int(row[cols["copy"]] or 0) if "copy" in cols else 0
            except (ValueError, IndexError):
                raise SystemExit("%s line %d: bad category/id/copy" % (csv_path, line))
            for lang, i in langs:
                # Spreadsheets save line breaks inside a cell as CR LF.
                text = row[i].replace("\r\n", "\n") if i < len(row) else ""
                # An empty cell is never an edit: blanking a message by
                # accident (a cell left empty in a shared row) is far more
                # likely than wanting one empty.
                if text and text != current.get((cat, lang, rid, copy)):
                    edits.append((cat, lang, rid, copy, text))
    apply_edits(pac_path, out_path, edits)


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
    elif cmd == "roundtrip" and len(args) == 1:
        return cmd_roundtrip(args[0])
    elif cmd == "set":
        copy = _opt(args, "--copy")
        if len(args) != 6:
            print(__doc__)
            return 1
        cmd_set(args[0], args[1], int(args[2]), int(args[3]), int(args[4]),
                args[5].replace("\\n", "\n"), copy)
    elif cmd == "import" and len(args) == 3:
        cmd_import(*args)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
