"""Symbol recovery + MIPS disassembler for SLES_541.51 (PS2).

The executable has no .symtab, but .sndata holds a runtime export table
used to link the DLL/*.REL overlays: 12-byte entries
{u32 name_ptr, u32 address, u32 hash} with mangled GCC 2.x names. This
script scans for those entries (name pointer into .sndata at the start
of a string, address inside .text) and uses them to label a capstone
disassembly.

Note: capstone has no R5900 mode, so a few EE-specific opcodes (lq/sq,
MMI) are shown as unrelated MSA/DSP instructions (e.g. `addu.qb`,
`aver_u.h`). Treat those as 128-bit stack saves/loads.

Requires: pip install capstone

Usage:
    python sles_disasm.py <SLES_541.51> syms <substring> ...   # list matching symbols
    python sles_disasm.py <SLES_541.51> dis  <substring> ...   # disassemble matching functions
    python sles_disasm.py <SLES_541.51> addr <hex_addr> [n]    # disassemble n instructions at address
"""
import struct
import sys


class Elf:
    def __init__(self, path):
        with open(path, "rb") as f:
            self.data = f.read()
        d = self.data
        if d[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        phoff, shoff = struct.unpack_from("<II", d, 0x1C)
        phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from("<HHHHH", d, 0x2A)
        self.segments = []
        for i in range(phnum):
            p_type, p_off, p_vaddr, _, p_filesz = struct.unpack_from("<5I", d, phoff + i * phentsize)
            if p_type == 1:  # PT_LOAD
                self.segments.append((p_vaddr, p_off, p_filesz))
        raw = [struct.unpack_from("<10I", d, shoff + i * shentsize) for i in range(shnum)]
        strtab_off = raw[shstrndx][4]
        self.sections = {}
        for sh in raw:
            name_end = d.index(b"\0", strtab_off + sh[0])
            name = d[strtab_off + sh[0]:name_end].decode("latin1")
            self.sections[name] = (sh[3], sh[5])  # (addr, size)

    def v2f(self, vaddr):
        for va, off, size in self.segments:
            if va <= vaddr < va + size:
                return vaddr - va + off
        return None

    def f2v(self, off):
        for va, seg_off, size in self.segments:
            if seg_off <= off < seg_off + size:
                return off - seg_off + va
        return None

    def cstr(self, vaddr, limit=512):
        o = self.v2f(vaddr)
        if o is None:
            return None
        e = self.data.find(b"\0", o, o + limit)
        return self.data[o:e].decode("latin1") if e > o else None


def recover_symbols(elf):
    """Return {name: address} from the .sndata export table."""
    d = elf.data
    sn_lo, sn_size = elf.sections[".sndata"]
    tx_lo, tx_size = elf.sections[".text"]
    sn_hi, tx_hi = sn_lo + sn_size, tx_lo + tx_size
    words = struct.unpack_from("<%dI" % (len(d) // 4 - 1), d, 0)
    syms = {}
    for i in range(len(words) - 1):
        n, a = words[i], words[i + 1]
        if sn_lo <= n < sn_hi and tx_lo <= a < tx_hi and a % 4 == 0:
            o = elf.v2f(n)
            if o and d[o - 1] == 0 and 32 < d[o] < 127:
                s = elf.cstr(n)
                if s and len(s) > 2 and all(32 < ord(c) < 127 for c in s):
                    syms[s] = a
    return syms


_GPR = ["zero", "at", "v0", "v1", "a0", "a1", "a2", "a3", "t0", "t1", "t2", "t3",
        "t4", "t5", "t6", "t7", "s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7",
        "t8", "t9", "k0", "k1", "gp", "sp", "fp", "ra"]


class _RawInsn:
    """Stand-in for a capstone insn capstone couldn't decode."""

    def __init__(self, address, word):
        self.address = address
        op, rs, rt = word >> 26, (word >> 21) & 31, (word >> 16) & 31
        if op in (0x1E, 0x1F):  # R5900 lq / sq
            imm = word & 0xFFFF
            imm -= 0x10000 if imm & 0x8000 else 0
            self.mnemonic = "lq" if op == 0x1E else "sq"
            self.op_str = "$%s, %s($%s)" % (_GPR[rt], hex(imm), _GPR[rs])
        else:
            self.mnemonic, self.op_str = ".word", "%#010x" % word


class Disassembler:
    def __init__(self, elf, syms):
        from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS64, CS_MODE_LITTLE_ENDIAN
        self.elf = elf
        self.md = Cs(CS_ARCH_MIPS, CS_MODE_MIPS64 | CS_MODE_LITTLE_ENDIAN)
        self.by_addr = {}
        for name, addr in syms.items():
            self.by_addr.setdefault(addr, name)

    def _insns(self, addr, count):
        """Decode one word at a time so an opcode capstone rejects doesn't
        end the listing; EE lq/sq are decoded by hand, the rest shown as .word."""
        o = self.elf.v2f(addr)
        for k in range(count):
            a, w = addr + k * 4, self.elf.data[o + k * 4:o + k * 4 + 4]
            if len(w) < 4:
                return
            got = list(self.md.disasm(w, a, 1))
            yield got[0] if got else _RawInsn(a, struct.unpack("<I", w)[0])

    def _fmt(self, i):
        ops = i.op_str
        if i.mnemonic in ("jal", "j"):
            ops += " <%s>" % self.by_addr.get(int(ops, 16), "?")
        return "  %08x: %-8s %s" % (i.address, i.mnemonic, ops)

    def function(self, addr, max_insns=400):
        """Disassemble until `jr $ra` plus its delay slot."""
        for i in self._insns(addr, max_insns):
            print(self._fmt(i))
            if i.mnemonic == "jr" and "ra" in i.op_str:
                for slot in self._insns(i.address + 4, 1):
                    print(self._fmt(slot))
                break

    def range(self, addr, count):
        for i in self._insns(addr, count):
            print(self._fmt(i))


def main(argv):
    if len(argv) < 4:
        print(__doc__)
        return 1
    elf = Elf(argv[1])
    syms = recover_symbols(elf)
    cmd, args = argv[2], argv[3:]
    if cmd == "syms":
        for name, addr in sorted(syms.items(), key=lambda x: x[1]):
            if any(p in name for p in args):
                print("%#x %s" % (addr, name))
    elif cmd == "dis":
        dis = Disassembler(elf, syms)
        for pat in args:
            for name, addr in sorted(syms.items()):
                if pat in name:
                    print("\n### %s @ %#x" % (name, addr))
                    dis.function(addr)
    elif cmd == "addr":
        count = int(args[1]) if len(args) > 1 else 64
        Disassembler(elf, syms).range(int(args[0], 16), count)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
