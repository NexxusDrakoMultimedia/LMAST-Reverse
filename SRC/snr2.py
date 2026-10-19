# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader / disassembler for the SN Systems SNR2 relocatable overlays
(ISO/DLL/*.REL) of Let's Make a Soccer Team! (PS2).

An SNR2 file is a MIPS image linked at base 0 (image offsets == file
offsets), followed by an import/export symbol table and two relocation
lists: one against symbols (imports), and one packed list of local sites
that only need the load base added. See DOC/SNR2_FORMAT.md.

Usage:
    python snr2.py info   <REL>                          # header summary + checks
    python snr2.py syms   <REL> [substr ...] [--sles SLES] # imports/exports (--sles: resolve addresses)
    python snr2.py relocs <REL> [hex_lo hex_hi]          # every relocation site in a range
    python snr2.py xref   <REL> <hex_addr | name>        # code/data referencing an address or symbol
    python snr2.py dis    <REL> <hex_addr> [n] [--sles SLES]  # annotated disassembly
    python snr2.py classes <REL> [substr ...]            # C++ classes: vtable and methods
    python snr2.py callers <REL> <hex_addr> [namespace]  # each call, its constant $a1, the class making it

--sles resolves imports to their address in SLES_541.51 through its
export table (names match; hashes are the same 16-bit value). Imports that
SLES doesn't export are named after the sibling overlay that exports them.

`classes` recovers the overlay's polymorphic classes from GCC 2.x type
information (name strings, __tf functions, vtables); `callers` uses it to
say which class's code makes each call (DOC/SNR2_FORMAT.md).

Requires capstone for `dis`: pip install capstone
"""
import struct
import sys

MAGIC = b"SNR2"

# Local (packed) relocation types.
L_LO16, L_HI16, L_J26, L_W32 = 0, 1, 2, 3
L_NAMES = {L_LO16: "LO16", L_HI16: "HI16", L_J26: "J26", L_W32: "W32"}
# External relocation types are the ELF MIPS numbers.
R_NAMES = {2: "R_MIPS_32", 4: "R_MIPS_26", 5: "R_MIPS_HI16", 6: "R_MIPS_LO16"}
SYM_IMPORT, SYM_EXPORT, SYM_WEAK = 1, 2, 3   # 3: vtables, __tf*, template instances


def name_hash(name):
    """16-bit symbol hash (h = h*31 + c), shared with SLES_541.51's export table."""
    h = 0
    for c in name.encode("latin1"):
        h = (h * 31 + c) & 0xFFFFFFFF
    return h & 0xFFFF


def _sext16(v):
    return v - 0x10000 if v & 0x8000 else v


class Snr2:
    HEADER = ("magic", "ext_rel_off", "ext_rel_count", "sym_off", "sym_count",
              "name_off", "ctors", "dtors", "loc_rel_off", "h24", "align",
              "loc_rel_end", "h30", "loc_rel_ptr", "h38", "h3c")

    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = d = f.read()
        if d[:4] != MAGIC:
            raise ValueError("%s: not an SNR2 file" % path)
        self.path = path
        self.h = dict(zip(self.HEADER, (MAGIC,) + struct.unpack_from("<15I", d, 4)))
        self.module = self.cstr(self.h["name_off"])

        # Symbols: {u32 name_ptr (image), u32 value (0 = import), u32 hash | flag<<16}
        self.syms = []
        for i in range(self.h["sym_count"]):
            n, v, hh = struct.unpack_from("<3I", d, self.h["sym_off"] + 12 * i)
            self.syms.append((self.cstr(n) if n else "", v, hh & 0xFFFF, hh >> 16))

        # External relocs: ELF REL-style {u32 offset, u32 sym<<8 | type, u32 addend}
        self.ext = []
        for i in range(self.h["ext_rel_count"]):
            o, info, add = struct.unpack_from("<3I", d, self.h["ext_rel_off"] + 12 * i)
            self.ext.append((o, info & 0xFF, info >> 8, add))

        # Local relocs: byte codes. code >= 4: pos += code & ~3; code < 4:
        # pos = next u32. Either way the low 2 bits are the type. The list
        # ends with the escape 00 00000000.
        self.local = []
        # snDllLoaded walks the list from +0x34 (equal to +0x20 in every file).
        i, end, pos = self.h["loc_rel_ptr"], self.h["loc_rel_end"], 0
        while i < end:
            b = d[i]
            i += 1
            if b < 4:
                pos = struct.unpack_from("<I", d, i)[0]
                i += 4
                if b == 0 and pos == 0:
                    break
            else:
                pos += b & ~3
            self.local.append((pos, b & 3))
        self.loc_consumed = i

    def cstr(self, off):
        e = self.data.find(b"\0", off)
        return self.data[off:e].decode("latin1")

    def word(self, off):
        return struct.unpack_from("<I", self.data, off)[0]

    def targets(self):
        """{site: target image address} for every local reloc. A LO16
        pairs with the most recent HI16 in list order (the ELF REL rule)."""
        out, hi = {}, None
        for off, t in self.local:
            w = self.word(off)
            if t == L_HI16:
                hi = (w & 0xFFFF) << 16
                out[off] = None           # filled in by its first LO16
                hi_site = off
            elif t == L_LO16:
                if hi is None:
                    continue
                v = (hi + _sext16(w & 0xFFFF)) & 0xFFFFFFFF
                out[off] = v
                if out.get(hi_site) is None:
                    out[hi_site] = v
            elif t == L_J26:
                out[off] = (w & 0x03FFFFFF) << 2
            else:
                out[off] = w
        return out

    def ext_by_site(self):
        return {o: (t, s, a) for o, t, s, a in self.ext}


# --- SLES export table ---------------------------------------------------------

def sles_exports(path):
    """{name: address} from SLES_541.51's .sndata export triples
    {u32 name_ptr, u32 address, u32 hash | flag<<16} (flag 2 or 3), checked by hash."""
    sys.path.insert(0, __file__.rsplit("snr2.py", 1)[0] or ".")
    from sles_disasm import Elf
    elf = Elf(path)
    d = elf.data
    lo, size = elf.sections[".sndata"]
    words = struct.unpack_from("<%dI" % (len(d) // 4 - 1), d, 0)
    out = {}
    for i in range(len(words) - 2):
        n, a, hh = words[i], words[i + 1], words[i + 2]
        if not (lo <= n < lo + size and hh >> 16 in (SYM_EXPORT, SYM_WEAK)):
            continue
        name = elf.cstr(n)
        if name and name_hash(name) == hh & 0xFFFF:
            out.setdefault(name, a)
    return out


# --- commands ------------------------------------------------------------------

def cmd_info(m):
    h = m.h
    print("%s  module %s  (%d bytes)" % (m.path, m.module, len(m.data)))
    print("  image          0x0-%#x (load alignment %#x)" % (h["name_off"], h["align"]))
    print("  ctors / dtors  %#x / %#x" % (h["ctors"], h["dtors"]))
    imps = sum(1 for s in m.syms if s[3] == SYM_IMPORT)
    exps = [s for s in m.syms if s[3] == SYM_EXPORT]
    weak = sum(1 for s in m.syms if s[3] == SYM_WEAK)
    print("  symbols        %d @%#x: %d imports, %d exports, %d weak" % (
        len(m.syms), h["sym_off"], imps, len(exps), weak))
    for name, v, _, _ in exps[:40]:
        print("                   export %#08x %s" % (v, name))
    print("  ext relocs     %d @%#x" % (len(m.ext), h["ext_rel_off"]))
    print("  local relocs   %d @%#x-%#x" % (len(m.local), h["loc_rel_off"], h["loc_rel_end"]))
    # sanity checks
    bad_hash = sum(1 for n, _, hv, _ in m.syms if n and name_hash(n) != hv)
    kinds = {}
    for off, t in m.local:
        op = m.word(off) >> 26
        ok = {L_HI16: op == 0x0F, L_J26: op in (2, 3)}.get(t, True)
        kinds[t] = kinds.get(t, 0) + (not ok)
    contiguous = (h["ext_rel_off"] + 12 * h["ext_rel_count"] == h["sym_off"]
                  and h["sym_off"] + 12 * h["sym_count"] == h["loc_rel_off"])
    at_eof = m.loc_consumed == len(m.data)
    hi16, j26 = kinds.get(L_HI16, 0), kinds.get(L_J26, 0)
    print("  checks: tables contiguous %s, local list ends at EOF %s, bad hashes %d, "
          "HI16 not lui %d, J26 not j/jal %d" % (contiguous, at_eof, bad_hash, hi16, j26))
    problems = []
    if not contiguous:
        problems.append("ext relocs / symbols / local relocs not contiguous")
    if not at_eof:
        problems.append("local reloc list doesn't end at EOF")
    if bad_hash:
        problems.append("%d bad symbol hashes" % bad_hash)
    if hi16:
        problems.append("%d HI16 sites not lui" % hi16)
    if j26:
        problems.append("%d J26 sites not j/jal" % j26)
    if problems:
        print("  !! " + "; ".join(problems))


def sibling_exports(m):
    """{name: overlay file} for exports of the other .REL files next to m.
    Imports not in SLES are all provided by SIMPRG or SAVEPRG."""
    import glob
    import os
    out = {}
    for f in sorted(glob.glob(os.path.join(os.path.dirname(m.path) or ".", "*.REL"))):
        if os.path.abspath(f) == os.path.abspath(m.path):
            continue
        for name, _, _, flag in Snr2(f).syms:
            if flag in (SYM_EXPORT, SYM_WEAK):
                out.setdefault(name, os.path.basename(f))
    return out


def cmd_syms(m, pats, sles):
    exp = sles_exports(sles) if sles else {}
    sib = sibling_exports(m) if sles else {}
    for i, (name, v, hv, flag) in enumerate(m.syms):
        if not name or (pats and not any(p in name for p in pats)):
            continue
        if flag in (SYM_EXPORT, SYM_WEAK):
            where = "%s %#08x" % ("export" if flag == SYM_EXPORT else "weak  ", v)
        elif sles:
            a = exp.get(name)
            if a is not None:
                where = "SLES   %#08x" % a
            else:
                where = sib.get(name, "unresolved")
        else:
            where = "import"
        print("%4d  %-17s  %04x  %s" % (i, where, hv, name))


def cmd_relocs(m, lo, hi):
    ext = m.ext_by_site()
    tgt = m.targets()
    kinds = dict(m.local)
    sites = sorted(set(o for o in ext if lo <= o < hi) | set(o for o in kinds if lo <= o < hi))
    for o in sites:
        if o in ext:
            t, s, a = ext[o]
            print("%#08x  %-11s %s%s" % (o, R_NAMES.get(t, t), m.syms[s][0], "+%#x" % a if a else ""))
        else:
            v = tgt.get(o)
            print("%#08x  %-11s %s" % (o, L_NAMES[kinds[o]], "-> %#x" % v if v is not None else ""))


def cmd_xref(m, what):
    try:
        addr = int(what, 16)
    except ValueError:
        addr = None
    if addr is None:
        idx = [i for i, s in enumerate(m.syms) if s[0] == what]
        if not idx:
            raise SystemExit("no symbol %r" % what)
        for o, t, s, a in m.ext:
            if s in idx:
                print("%#08x  %s%s" % (o, R_NAMES.get(t, t), " +%#x" % a if a else ""))
        return
    kinds = dict(m.local)
    for o, v in sorted(m.targets().items()):
        if v == addr and kinds[o] != L_HI16:
            print("%#08x  %s" % (o, L_NAMES[kinds[o]]))


# --- C++ classes from run-time type information --------------------------------

def demangle_type(s):
    """'Q22fb6Player' -> 'fb::Player' (GCC 2.x nested type names)."""
    if not s.startswith("Q"):
        return s
    n, rest, parts = int(s[1]), s[2:], []
    for _ in range(n):
        i = 0
        while i < len(rest) and rest[i].isdigit():
            i += 1
        if not i:
            return s                # template arguments and the like: left as is
        size = int(rest[:i])
        parts.append(rest[i:i + size])
        rest = rest[i + size:]
    return "::".join(parts) if not rest else s


class Classes:
    """The overlay's polymorphic classes, recovered from GCC 2.x type info.

    A class's type-info function (__tf<name>, local to the overlay) passes
    its name string to the type-info initialisers, after initialising its
    base the same way, so the last name it loads is its own. The class's
    vtable holds a pointer to that function in its second 8-byte entry
    {u32 0, fn}; the entries after it are the virtual methods, with a null
    or imported (__pure_virtual) entry for an abstract one. Only nested
    names (Q<n>...) are looked for, which covers fb:: and the other
    namespaced classes.

    Functions are found as call targets, vtable entries and stack-frame
    prologues (addiu $sp, $sp, -n); other code pointers are mostly
    switch-table cases. owner(f) is the class whose vtable holds f (the
    shortest vtable, i.e. the base class, when several do; the first by
    name among equals)."""

    def __init__(self, m):
        import bisect
        import collections
        import re
        self.m, d = m, m.data
        tg, kinds, ext = m.targets(), dict(m.local), m.ext_by_site()
        self.jal = {s: t for s, t in tg.items() if kinds.get(s) == L_J26}
        w32 = {s: t for s, t in tg.items() if kinds.get(s) == L_W32}
        self.code_end = max(self.jal) + 8           # data follows the last call site
        word = lambda a: struct.unpack_from("<I", d, a)[0]
        prolog = [o for o in range(0, self.code_end, 4)
                  if word(o) >> 16 == 0x27BD and word(o) & 0x8000]
        starts = set(t for t in self.jal.values() if t < self.code_end) | set(prolog)

        def func_of(a):
            i = bisect.bisect_right(self._starts, a) - 1
            return self._starts[i] if i >= 0 else None
        self._starts = sorted(starts)

        names = {mm.start(1): mm.group(1).decode("latin1") for mm in
                 re.finditer(rb"(?<=\x00)(Q[2-9](?:[0-9]+[A-Za-z_][A-Za-z_0-9]*){2,})(?=\x00)", d)}
        last, tf = {}, {}
        for s, t in tg.items():
            if t in names and kinds.get(s) == L_LO16 and s < self.code_end:
                f = func_of(s)
                if s > last.get(f, -1):
                    last[f], tf[f] = s, demangle_type(names[t])
        self.typeinfo = tf                         # __tf function -> class
        self.vtables, self.methods = {}, {}
        for slot, t in sorted(w32.items()):
            if t not in tf:
                continue
            meths, o = [], slot + 8
            while True:
                if o in w32 and w32[o] < self.code_end and w32[o] not in tf:
                    meths.append(w32[o])
                elif o in ext:
                    pass
                elif word(o) == 0 and word(o - 4) == 0 and w32.get(o + 8, -1) not in tf \
                        and o + 8 in w32:
                    pass                            # a pure virtual entry
                else:
                    break
                o += 8
            cls = tf[t]
            if meths and len(meths) > len(self.methods.get(cls, [])):
                self.vtables[cls], self.methods[cls] = slot - 0xC, meths   # entry 0 is {0, 0}
        self._starts = sorted(starts | set(f for ms in self.methods.values() for f in ms))
        self.func_of = func_of
        owners = collections.defaultdict(set)
        for cls, ms in self.methods.items():
            for f in ms:
                owners[f].add(cls)
        self._owner = {f: min(cs, key=lambda c: (len(self.methods[c]), c)) for f, cs in owners.items()}
        self._owned = sorted(self._owner)
        self.callers = collections.defaultdict(set)
        for site, t in self.jal.items():
            self.callers[t].add(func_of(site))

    def owner(self, f):
        return self._owner.get(f)

    def reached_from(self, f, prefix="", depth=8):
        """(levels up, [classes]): the owning classes of f, else of its
        callers, level by level, the first level that has any. With a
        prefix ("fb::"), only classes whose name starts with it count."""
        seen, level = {f}, {f}
        for up in range(depth + 1):
            found = sorted(set(self._owner[x] for x in level
                               if x in self._owner and self._owner[x].startswith(prefix)))
            if found:
                return up, found
            nxt = set()
            for x in level:
                nxt |= self.callers.get(x, set())
            level = nxt - seen
            seen |= level
            if not level:
                break
        return None, []

    def near(self, f):
        """The nearest vtable method at or before f, and its class."""
        import bisect
        i = bisect.bisect_right(self._owned, f) - 1
        return (self._owned[i], self._owner[self._owned[i]]) if i >= 0 else (None, None)


def const_arg(d, site, reg=5):
    """The constant a call passes in `reg` ($a1 by default): an addiu/ori
    from $zero in the delay slot, or before the call with no other call or
    write to the register in between. None if it isn't a constant."""
    for o in [site + 4] + list(range(site - 4, max(site - 48, -4), -4)):
        w = struct.unpack_from("<I", d, o)[0]
        op = w >> 26
        if op in (0x09, 0x0D) and (w >> 21) & 0x1F == 0 and (w >> 16) & 0x1F == reg:
            return w & 0xFFFF
        if o != site + 4 and (op == 3 or (op == 0 and w & 0x3F == 9)):
            return None                     # an earlier call
        if op == 0 and (w >> 11) & 0x1F == reg:
            return None                     # written by a register op
        if op not in (0, 1, 4, 5, 0x1F, 0x28, 0x29, 0x2B, 0x39, 0x3F) and (w >> 16) & 0x1F == reg:
            return None                     # loaded otherwise
    return None


def cmd_classes(m, pats):
    c = Classes(m)
    for cls in sorted(c.methods):
        if pats and not any(p.lower() in cls.lower() for p in pats):
            continue
        print("%-48s vtable %#08x  %3d methods  %s" % (
            cls, c.vtables[cls], len(c.methods[cls]),
            " ".join("%#x" % f for f in c.methods[cls])))
    print("%d classes with a vtable, %d type-info functions" % (len(c.methods), len(c.typeinfo)))


def cmd_callers(m, addr, prefix=""):
    """Every call to addr, with the constant $a1 it passes and the class
    whose code makes it (or, through how many calls, reaches it). A
    namespace ("fb") limits the classes to that namespace."""
    c = Classes(m)
    prefix = prefix + "::" if prefix else ""
    for site in sorted(s for s, t in c.jal.items() if t == addr):
        f = c.func_of(site)
        k = const_arg(m.data, site)
        up, found = c.reached_from(f, prefix)
        if found:
            where = ", ".join(found[:4]) + (", ..." if len(found) > 4 else "")
            where = where if up == 0 else "via %d call%s: %s" % (up, "s" if up > 1 else "", where)
        else:
            nf, nc = c.near(f)
            where = "no class found (in %s's code, after %#x)" % (nc, nf) if nc else "no class found"
        print("%#08x  a1=%-5s func %#08x  %s" % (site, "-" if k is None else k, f, where))


def cmd_dis(m, addr, count, sles):
    sys.path.insert(0, __file__.rsplit("snr2.py", 1)[0] or ".")
    from sles_disasm import _RawInsn
    from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN
    md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
    exp = sles_exports(sles) if sles else {}
    ext = m.ext_by_site()
    tgt = m.targets()
    kinds = dict(m.local)
    for k in range(count):
        a = addr + 4 * k
        w = m.data[a:a + 4]
        if len(w) < 4:
            break
        got = list(md.disasm(w, a, 1))
        i = got[0] if got else _RawInsn(a, struct.unpack("<I", w)[0])
        note = ""
        if a in ext:
            t, s, add = ext[a]
            name = m.syms[s][0] + ("+%#x" % add if add else "")
            pre = {4: "", 5: "%hi", 6: "%lo", 2: ""}.get(t, "")
            note = "%s(%s)" % (pre, name) if pre else name
            if name in exp or m.syms[s][0] in exp:
                note += " @%#x" % exp[m.syms[s][0]]
        elif a in kinds:
            v = tgt.get(a)
            if v is not None:
                exps = [s[0] for s in m.syms if s[3] in (SYM_EXPORT, SYM_WEAK) and s[1] == v]
                note = "-> %#x%s" % (v, " <%s>" % exps[0] if exps else "")
                if kinds[a] == L_W32:
                    note = "ptr " + note
        text = "%-8s %s" % (i.mnemonic, i.op_str)
        print("  %06x: %08x  %-40s%s" % (a, struct.unpack("<I", w)[0], text,
                                         ("  ; " + note) if note else ""))


def main(argv):
    args = list(argv[1:])
    sles = None
    if "--sles" in args:
        k = args.index("--sles")
        sles = args[k + 1]
        del args[k:k + 2]
    if len(args) < 2:
        print(__doc__)
        return 1
    cmd, m, rest = args[0], Snr2(args[1]), args[2:]
    if cmd == "info":
        cmd_info(m)
    elif cmd == "syms":
        cmd_syms(m, rest, sles)
    elif cmd == "relocs":
        lo = int(rest[0], 16) if rest else 0
        hi = int(rest[1], 16) if len(rest) > 1 else len(m.data)
        cmd_relocs(m, lo, hi)
    elif cmd == "xref" and rest:
        cmd_xref(m, rest[0])
    elif cmd == "classes":
        cmd_classes(m, rest)
    elif cmd == "callers" and rest:
        cmd_callers(m, int(rest[0], 16), rest[1] if len(rest) > 1 else "")
    elif cmd == "dis" and rest:
        cmd_dis(m, int(rest[0], 16), int(rest[1]) if len(rest) > 1 else 64, sles)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
