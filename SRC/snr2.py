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

--sles resolves imports to their address in SLES_541.51 through its
export table (names match; hashes are the same 16-bit value). Imports that
SLES doesn't export are named after the sibling overlay that exports them.

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
              "name_off", "ctors", "dtors", "loc_rel_off", "h24", "h28",
              "loc_rel_end", "h30", "h34", "h38", "h3c")

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
        i, end, pos = self.h["loc_rel_off"], self.h["loc_rel_end"], 0
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
    print("  image          0x0-%#x (code from %#x)" % (h["name_off"], h["h28"]))
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
    print("  checks: tables contiguous %s, local list ends at EOF %s, bad hashes %d, "
          "HI16 not lui %d, J26 not j/jal %d" % (
              h["ext_rel_off"] + 12 * h["ext_rel_count"] == h["sym_off"]
              and h["sym_off"] + 12 * h["sym_count"] == h["loc_rel_off"],
              m.loc_consumed == len(m.data), bad_hash, kinds.get(L_HI16, 0), kinds.get(L_J26, 0)))


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
    elif cmd == "dis" and rest:
        cmd_dis(m, int(rest[0], 16), int(rest[1]) if len(rest) > 1 else 64, sles)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
