# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""ramcheck.py: check the runtime memory map against a running game, and
export it as RetroAchievements code notes.

The runtime memory map (DOC/RAM_MAP.md, RAM_MATCH.md, RAM_CAREER.md and
RAM_SEASON.md) records where the PAL release keeps its data in EE RAM.
Its rows come from reading the game code, so this tool is how they are
seen in the game: it reads the addresses from PCSX2 over PINE, or from
the 32 MB EE memory dump of a save state, and says where a row or a
pointer chain does not hold. RetroAchievements reads the same RAM, with
the same addresses.

A source is `pine` (PCSX2's PINE socket, default port 28011), `pine:PORT`,
or the path of a raw EE memory dump (`eeMemory.bin`, 32 MB, the address
is the offset; 7z extracts it from a PCSX2 `.p2s` save state). PINE
serves one client at a time, and the tool only reads.

Commands (run from the repo root):
  info                       parse the four RAM docs and check the rows
                             (no game needed): counts, and !! for an
                             address outside RAM or a size that does not
                             parse
  notes [--csv]              the rows as code notes: one entry per row with
                             an absolute address; then the rows inside the
                             career work buffer ("block N + 0x...") and
                             the rows relative to another pointer (P+,
                             T+, slot+ and the like), each in the doc's
                             own form
  read <source> <addr> [size|type]
                             one value: size 1, 2, 4 or 8 (default 4), or
                             a type such as u8, s16, u32, s64, float
  check <source> [--exe SLES_541.51] [--all]
                             the structural checks (the executable's code
                             against the file, the heap block table, the
                             overlay registry, the career work buffer, the
                             schedule object, the demo flag, the frame
                             counter), then every static row of the docs
                             with a size of 1, 2, 4 or 8; prints !! where
                             a pointer is outside RAM or a chain is
                             broken, and every value with --all

Each problem is marked !! on the line it concerns. The checks read the
PAL addresses; a Japanese disc has others (gamever.py). A check that needs
a created object says so when the game has not made it yet (at the logo,
before the career work buffer exists), which is not an error.
"""
import os
import re
import socket
import struct
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = ["RAM_MAP.md", "RAM_MATCH.md", "RAM_CAREER.md", "RAM_SEASON.md"]
RAM_SIZE = 0x2000000
LOW = 0x100000          # the executable loads here; below is BIOS and kernel

# PINE opcodes (pcsx2 pine.h) and the bytes each reply carries.
OP_READ = {1: 0, 2: 1, 4: 2, 8: 3}
PINE_BATCH = 1500


# ---------------------------------------------------------------- sources

class FileSource:
    """A raw EE memory dump: the address is the file offset."""

    def __init__(self, path):
        self.f = open(path, "rb")
        self.size = os.path.getsize(path)
        self.name = path

    def read_batch(self, items):
        out = []
        for addr, size in items:
            if addr < 0 or addr + size > self.size:
                raise ValueError("address 0x%x is outside the dump" % addr)
            self.f.seek(addr)
            out.append(int.from_bytes(self.f.read(size), "little"))
        return out

    def close(self):
        self.f.close()


class PineSource:
    """PCSX2's PINE socket: batched Read8/16/32/64 over TCP."""

    def __init__(self, port=28011):
        self.sock = socket.create_connection(("127.0.0.1", port), timeout=5)
        self.name = "pine:%d" % port

    def _recv(self, n):
        buf = b""
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError("PINE closed the connection")
            buf += chunk
        return buf

    def read_batch(self, items):
        out = []
        for i in range(0, len(items), PINE_BATCH):
            part = items[i:i + PINE_BATCH]
            body = b"".join(struct.pack("<BI", OP_READ[s], a) for a, s in part)
            self.sock.sendall(struct.pack("<I", len(body) + 4) + body)
            (n,) = struct.unpack("<I", self._recv(4))
            reply = self._recv(n - 4)
            if reply[0] != 0:
                raise ConnectionError("PINE refused a read (is a game running?)")
            pos = 1
            for _, s in part:
                out.append(int.from_bytes(reply[pos:pos + s], "little"))
                pos += s
        return out

    def close(self):
        self.sock.close()


def open_source(spec):
    if spec == "pine" or spec.startswith("pine:"):
        port = int(spec.split(":")[1]) if ":" in spec else 28011
        return PineSource(port)
    return FileSource(spec)


class Mem:
    """Typed reads on top of a source."""

    def __init__(self, src):
        self.src = src

    def read(self, addr, size=4):
        return self.src.read_batch([(addr, size)])[0]

    def many(self, items):
        return self.src.read_batch(items)

    def u32(self, addr):
        return self.read(addr, 4)

    def string(self, addr, limit=48):
        words = self.many([(addr + 4 * i, 4) for i in range(limit // 4)])
        raw = b"".join(w.to_bytes(4, "little") for w in words)
        raw = raw.split(b"\0")[0]
        return raw.decode("latin-1")


# ------------------------------------------------------------- doc tables

class Row:
    def __init__(self, doc, line, cells):
        self.doc, self.line = doc, line
        self.addr_text = cells[0].strip("` ")
        self.size_text = cells[1]
        self.type = cells[2].strip("` ")
        self.region = cells[3].strip("` ").lower()
        self.name = cells[4].strip("` ")
        self.meaning = cells[5]
        self.addr = None          # absolute address, or None
        self.block = None         # (block number, offset) inside the work buffer
        self.size = None
        m = re.fullmatch(r"0x([0-9a-fA-F]+)", self.addr_text)
        if m:
            self.addr = int(m.group(1), 16)
        m = re.fullmatch(r"block\s*(\d+)\s*\+\s*0x([0-9a-fA-F]+)", self.addr_text)
        if m:
            self.block = (int(m.group(1)), int(m.group(2), 16))
        m = re.match(r"(0x[0-9a-fA-F]+|\d[\d,]*)", self.size_text.strip("` "))
        if m:
            self.size = int(m.group(1).replace(",", ""), 0)

    @property
    def kind(self):
        if self.addr is not None:
            return "absolute"
        if self.block is not None:
            return "block"
        return "other"

    @property
    def width(self):
        return self.size if self.size in (1, 2, 4, 8) else None

    @property
    def signed(self):
        return self.type.startswith("s") and not self.type.startswith("struct")

    @property
    def pointer(self):
        return "pointer" in self.type


def split_row(line):
    line = line.replace("\\|", "\x00")
    cells = [c.replace("\x00", "|").strip() for c in line.strip().strip("|").split("|")]
    return cells


def load_rows(docs=None):
    """Every main-table row (Address | Size | Type | Region | Name | ...)."""
    rows = []
    for doc in docs or DOCS:
        path = os.path.join(REPO, "DOC", doc)
        if not os.path.exists(path):
            continue
        in_table = False
        with open(path, encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                if line.startswith("| Address | Size | Type | Region | Name |"):
                    in_table = True
                    continue
                if in_table:
                    if not line.startswith("|"):
                        in_table = False
                    elif line.startswith("|---"):
                        continue
                    else:
                        cells = split_row(line)
                        if len(cells) >= 6:
                            rows.append(Row(doc, n, cells))
    return rows


def clean(text):
    text = re.sub(r"`", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def first_sentences(text, limit=420):
    text = clean(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    dot = cut.rfind(". ")
    return (cut[:dot + 1] if dot > 120 else cut.rstrip() + "...")


# ---------------------------------------------------------------- info

def cmd_info(args):
    rows = load_rows()
    if not rows:
        print("  !! no RAM docs found under DOC/")
        return 1
    bad = 0
    for doc in DOCS:
        mine = [r for r in rows if r.doc == doc]
        kinds = {"absolute": 0, "block": 0, "other": 0}
        for r in mine:
            kinds[r.kind] += 1
        print("%s: %d rows (%d absolute, %d in the work buffer, %d other)"
              % (doc, len(mine), kinds["absolute"], kinds["block"], kinds["other"]))
        for r in mine:
            why = []
            if r.size is None and r.size_text.strip("` ") not in ("?", "–", "-", ""):
                why.append("size does not parse")
            if r.addr is not None:
                if r.region.startswith("static") and not (LOW <= r.addr < RAM_SIZE):
                    why.append("static address outside 0x%x..0x%x" % (LOW, RAM_SIZE))
                if r.addr >= RAM_SIZE:
                    why.append("address outside the 32 MB of RAM")
                if r.width and r.addr % r.width:
                    why.append("not aligned to its size %d" % r.width)
            if why:
                bad += 1
                print("  line %d %s %s  !! %s" % (r.line, r.addr_text, r.name, "; ".join(why)))
    seen = {}
    for r in rows:
        if r.addr is not None:
            seen.setdefault((r.addr, r.size), set()).add(r.doc)
    shared = sum(1 for v in seen.values() if len(v) > 1)
    print("%d absolute addresses, %d listed in more than one doc (not an error)"
          % (len(seen), shared))
    return 1 if bad else 0


# --------------------------------------------------------------- notes

def size_word(r):
    return {1: "8-bit", 2: "16-bit", 4: "32-bit", 8: "64-bit"}.get(r.width, "%s bytes" % r.size)


def cmd_notes(args):
    rows = load_rows()
    csv = "--csv" in args
    out = []
    absolute = sorted((r for r in rows if r.addr is not None), key=lambda r: r.addr)
    blocks = [r for r in rows if r.block is not None]
    others = [r for r in rows if r.kind == "other"]
    if csv:
        out.append("address,size,type,region,name,note,doc")
        for r in absolute:
            note = first_sentences(r.meaning).replace('"', '""')
            out.append('0x%08x,%s,"%s",%s,"%s","%s",%s'
                       % (r.addr, r.size, r.type.replace('"', ""), r.region,
                          r.name.replace('"', ""), note, r.doc))
        for r in blocks:
            note = first_sentences(r.meaning).replace('"', '""')
            out.append('"work buffer block %d + 0x%x",%s,"%s",%s,"%s","%s",%s'
                       % (r.block[0], r.block[1], r.size, r.type.replace('"', ""),
                          r.region, r.name.replace('"', ""), note, r.doc))
        for r in others:
            note = first_sentences(r.meaning).replace('"', '""')
            out.append('"%s",%s,"%s",%s,"%s","%s",%s'
                       % (r.addr_text.replace('"', ""), r.size_text.replace('"', ""),
                          r.type.replace('"', ""), r.region, r.name.replace('"', ""),
                          note, r.doc))
    else:
        out.append("# Code notes from the runtime memory map (PAL release, EE RAM).")
        out.append("# Rows with an absolute address first; then the rows inside the")
        out.append("# career work buffer, which need the pointer chain (see RAM_MAP.md).")
        out.append("")
        for r in absolute:
            out.append("0x%08x  [%s%s] %s" % (r.addr, size_word(r),
                                              ", " + r.type if r.type else "", clean(r.name)))
            out.append("    " + first_sentences(r.meaning))
        out.append("")
        out.append("# Rows inside the career work buffer: pointer 0x3909a8, then")
        out.append("# base = u32[p+0x1c], block N at base + u32[p+0x28+4*N].")
        out.append("")
        for r in blocks:
            out.append("block %d + 0x%x  [%s%s] %s" % (r.block[0], r.block[1], size_word(r),
                                                     ", " + r.type if r.type else "",
                                                     clean(r.name)))
            out.append("    " + first_sentences(r.meaning))
        out.append("")
        out.append("# Rows relative to another pointer or record (P+, T+, slot+, [0x...]+,")
        out.append("# ranges and the like): the first column is the doc's own form, and the")
        out.append("# doc's section says which root it is relative to.")
        out.append("")
        for r in others:
            out.append("%s  [%s%s] %s  (%s)" % (clean(r.addr_text), clean(r.size_text),
                                               ", " + r.type if r.type else "",
                                               clean(r.name), r.doc))
            out.append("    " + first_sentences(r.meaning))
    sys.stdout.write("\n".join(out) + "\n")
    return 0


# ---------------------------------------------------------------- read

TYPES = {"u8": (1, False), "s8": (1, True), "u16": (2, False), "s16": (2, True),
         "u32": (4, False), "s32": (4, True), "u64": (8, False), "s64": (8, True),
         "float": (4, None)}


def fmt_value(v, size, signed):
    if signed is None:
        return "%g" % struct.unpack("<f", struct.pack("<I", v))[0]
    if signed and v >= 1 << (8 * size - 1):
        return "%d (0x%0*x)" % (v - (1 << (8 * size)), size * 2, v)
    return "%d (0x%0*x)" % (v, size * 2, v)


def parse_int(text):
    return int(text, 16) if text.lower().startswith("0x") else int(text, 0)


def cmd_read(args):
    if len(args) < 2:
        print(__doc__)
        return 2
    src = open_source(args[0])
    try:
        addr = parse_int(args[1])
        what = args[2] if len(args) > 2 else "u32"
        if what in TYPES:
            size, signed = TYPES[what]
        else:
            size, signed = int(what), False
        v = Mem(src).read(addr, size)
        print("0x%08x %s = %s" % (addr, what, fmt_value(v, size, signed)))
    finally:
        src.close()
    return 0


# --------------------------------------------------------------- check

class Report:
    def __init__(self):
        self.bad = 0

    def ok(self, text):
        print(text)

    def note(self, text):
        print("  " + text)

    def bad_line(self, text, why):
        self.bad += 1
        print("%s  !! %s" % (text, why))


def ptr_ok(v):
    return v == 0 or LOW <= v < RAM_SIZE


def check_exe(mem, rep, exe_path):
    """Sample the executable's code against the file: shows the addresses
    are the ones the docs use (the image loads at 0x100000)."""
    if not os.path.exists(exe_path):
        rep.note("executable %s not found: skipped" % exe_path)
        return
    data = open(exe_path, "rb").read()
    if data[:4] != b"\x7fELF":
        rep.note("%s is not an ELF: skipped" % exe_path)
        return
    phoff = struct.unpack_from("<I", data, 0x1c)[0]
    phentsize, phnum = struct.unpack_from("<HH", data, 0x2a)
    loads = []
    for i in range(phnum):
        p_type, p_off, p_vaddr, _, p_filesz = struct.unpack_from("<IIIII", data, phoff + i * phentsize)
        if p_type == 1 and p_filesz:
            loads.append((p_off, p_vaddr, p_filesz))
    if not loads:
        rep.bad_line("executable", "no PT_LOAD segment")
        return
    off, vaddr, filesz = loads[0]
    text_end = min(filesz, 0x346c90 - vaddr)        # .text; .data changes at run time
    count = 128
    step = max(4, (text_end // count) & ~3)
    addrs = [vaddr + i * step for i in range(count) if i * step + 4 <= text_end]
    got = mem.many([(a, 4) for a in addrs])
    wrong = [a for a, g in zip(addrs, got)
             if g != struct.unpack_from("<I", data, off + (a - vaddr))[0]]
    line = "executable: %d code words sampled over 0x%x..0x%x" % (len(addrs), vaddr, vaddr + text_end)
    if wrong:
        rep.bad_line(line, "%d differ from %s (first at 0x%x): another build, or the code is patched"
                     % (len(wrong), os.path.basename(exe_path), wrong[0]))
    else:
        rep.ok(line + ", all equal to the file")


def check_heap(mem, rep):
    vals = mem.many([(0x35dae8 + 0x10 * i + 4 * j, 4) for i in range(8) for j in range(3)])
    rows = [vals[i * 3:i * 3 + 3] for i in range(8)]
    rep.ok("heap block table 0x35dae8:")
    for i, (handle, size, buf) in enumerate(rows):
        line = "  block %d: size 0x%x, buffer 0x%x" % (i, size, buf)
        if i < 7 and size == 0:
            rep.bad_line(line, "size 0 (documented non-zero for blocks 0 to 6)")
        elif buf and not (LOW <= buf < RAM_SIZE):
            rep.bad_line(line, "buffer outside RAM")
        elif i < 7 and buf == 0:
            rep.note("block %d has no buffer yet (before the heap is set up?)" % i)
        else:
            rep.ok(line)


def check_registry(mem, rep):
    count = mem.u32(0x35ed98)
    line = "overlay registry 0x35ed98: count %d" % count
    if count > 0x400:
        rep.bad_line(line, "count above 0x400")
        return
    rep.ok(line)
    if not count:
        return
    vals = mem.many([(0x35eda0 + 12 * k + 4 * j, 4) for k in range(count) for j in range(3)])
    for k in range(count):
        name_ptr, header, check = vals[k * 3:k * 3 + 3]
        if header == 0:
            continue
        name = mem.string(name_ptr) if ptr_ok(name_ptr) and name_ptr else "?"
        line = "  slot %d: %s loaded at 0x%x" % (k, name, header)
        if not (LOW <= header < RAM_SIZE):
            rep.bad_line(line, "base outside RAM")
        elif check != (name_ptr ^ header ^ 0x31415926) & 0xffffffff:
            rep.bad_line(line, "check word 0x%x is not name ^ header ^ 0x31415926" % check)
        else:
            rep.ok(line)


BLOCK_SIZES = [0x20e48, 0x129e8, 0x120c0, 0x530, 0xa8, 0xb50d0, 0x1ce8, 0x44, 1, 8, 1]


def check_pwork(mem, rep):
    p = mem.u32(0x3909a8)
    if p == 0:
        rep.note("career work buffer: 0x3909a8 is 0 (not created yet; it exists from the first script command)")
        return None
    line = "career work buffer: PlPworkTask at 0x%x" % p
    if not (LOW <= p < RAM_SIZE):
        rep.bad_line(line, "root outside RAM")
        return None
    base, total = mem.u32(p + 0x1c), mem.u32(p + 0x54)
    offs = mem.many([(p + 0x28 + 4 * i, 4) for i in range(11)])
    if not (LOW <= base < RAM_SIZE):
        rep.bad_line(line + ", buffer 0x%x" % base, "buffer outside RAM")
        return None
    rep.ok(line + ", buffer 0x%x, total size 0x%x" % (base, total))
    blocks = {}
    for i, off in enumerate(offs):
        if off == 0xffffffff:
            rep.note("block %d absent (offset 0xffffffff)" % i)
            continue
        text = "  block %d at 0x%x (offset 0x%x, size 0x%x)" % (i, base + off, off, BLOCK_SIZES[i])
        if off + BLOCK_SIZES[i] > total:
            rep.bad_line(text, "ends past the work buffer's total size 0x%x" % total)
        else:
            rep.ok(text)
            blocks[i] = base + off
    return blocks


def check_sche(mem, rep):
    s = mem.u32(0x390650)
    if s == 0:
        rep.note("schedule object: 0x390650 is 0 (none at the logo, the title and loading)")
        return
    line = "schedule object CScheEuro at 0x%x" % s
    if not (LOW <= s < RAM_SIZE):
        rep.bad_line(line, "pointer outside RAM")
        return
    vt = mem.u32(s + 0x20)
    names = {0x406c28: "Normal (career)", 0x406b48: "FirstPromote", 0x406a68: "VS"}
    if vt in names:
        rep.ok(line + ", mode %s" % names[vt])
    else:
        rep.bad_line(line + ", vtable 0x%x" % vt, "not one of the three documented mode vtables")


def check_misc(mem, rep):
    demo = mem.u32(0x34d43c)
    rep.ok("demo flag 0x34d43c = %d (%s)" % (demo, "attract demo" if demo else "not the demo"))
    a = mem.u32(0x35d4a0)
    if isinstance(mem.src, FileSource):
        rep.ok("frame counter 0x35d4a0 = %d (a dump does not advance)" % a)
    else:
        time.sleep(0.4)
        b = mem.u32(0x35d4a0)
        line = "frame counter 0x35d4a0: %d then %d" % (a, b)
        if b == a:
            rep.bad_line(line, "did not advance in 0.4 s (game paused, or not the frame counter)")
        else:
            rep.ok(line)
    ls = mem.many([(0x34defc, 4), (0x34df00, 4)])
    rep.ok("language slots 0x34defc/0x34df00 = %d, %d" % tuple(ls))


def check_rows(mem, rep, show_all):
    rows = [r for r in load_rows()
            if r.addr is not None and r.width and r.region.startswith("static")
            and r.addr % r.width == 0 and r.addr + r.width <= RAM_SIZE]
    rep.ok("static rows of the docs: %d with a size of 1, 2, 4 or 8" % len(rows))
    vals = mem.many([(r.addr, r.width) for r in rows])
    for r, v in zip(rows, vals):
        text = "  %s 0x%08x %s = %s" % (r.doc, r.addr, r.name, fmt_value(v, r.width, r.signed))
        if r.pointer and r.width == 4 and not ptr_ok(v):
            rep.bad_line(text, "documented as a pointer but 0x%x is outside RAM" % v)
        elif show_all:
            rep.ok(text)


def cmd_check(args):
    if not args:
        print(__doc__)
        return 2
    exe = os.path.join(REPO, "ISO", "SLES_541.51")
    show_all = "--all" in args
    rest = [a for a in args if a != "--all"]
    if "--exe" in rest:
        i = rest.index("--exe")
        exe = rest[i + 1]
        del rest[i:i + 2]
    src = open_source(rest[0])
    rep = Report()
    try:
        if isinstance(src, FileSource) and src.size != RAM_SIZE:
            rep.bad_line("memory dump %s" % src.name, "%d bytes, not the 32 MB of EE RAM" % src.size)
        mem = Mem(src)
        check_exe(mem, rep, exe)
        check_heap(mem, rep)
        check_registry(mem, rep)
        check_pwork(mem, rep)
        check_sche(mem, rep)
        check_misc(mem, rep)
        check_rows(mem, rep, show_all)
    finally:
        src.close()
    print("%d problem%s" % (rep.bad, "" if rep.bad == 1 else "s"))
    return 1 if rep.bad else 0


# ---------------------------------------------------------------- main

def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        return cmd_info(args)
    if cmd == "notes":
        return cmd_notes(args)
    if cmd == "read":
        return cmd_read(args)
    if cmd == "check":
        return cmd_check(args)
    print(__doc__)
    return 2


sys.exit(main(sys.argv))
