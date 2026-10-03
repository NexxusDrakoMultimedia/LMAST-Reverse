# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Game builds: the PAL release (SLES_541.51) and the Japanese one
(SLPM_663.16, "Pro Soccer Club o Tsukurou! Europe Championship").

The tools give addresses in the PAL executable and overlays (ISO/). This
module finds the same address in another build's executable or overlay,
so a tool given ISO_JP/ reads the right table. See DOC/JAPANESE_RELEASE.md.

An address is found in the other build, in this order:

  1. symbol    the PAL address has a name (the executable's export table,
               an overlay's exports); the other build's symbol of that name.
  2. reference every named PAL function that loads the address with a
               lui/addiu-style pair (an overlay: a HI16/LO16 relocation)
               loads it as its n-th distinct address. The other build's
               function of that name loads its n-th. Every such function
               must give the same answer.
  3. bytes     the PAL bytes at the address (code with its address and
               jump fields masked) occur exactly once in the other file,
               or as often as in the PAL file: then the same occurrence.
  4. near      as 2, with the closest address a named function loads,
               up to 0x800 bytes away, plus the distance.

Functions without a symbol are named after their callers ("f>2" is the
third function f calls). A result from 2 must agree with a unique match
from 3. Results are cached in .cache/gamever.json by the other
file's SHA-1.

Usage:
    python gamever.py which <ISO dir | file>                # which build
    python gamever.py at    <file> <PAL hex address> [size] # one address, and how it was found
    python gamever.py check <ISO dir>                       # every address the tools use
"""
import bisect
import hashlib
import json
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

EXES = {"SLES_541.51": "PAL", "SLPM_663.16": "JP"}
PAL_EXE = "SLES_541.51"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_ISO = os.path.join(ROOT, "ISO")
CACHE = os.path.join(ROOT, ".cache", "gamever.json")
NEAR = 0x800

# Every address the tools read from the executable or an overlay:
# (tool, constant, file, bytes to compare). A constant that is a tuple
# names several addresses. `check` translates them all.
ADDRESSES = (
    ("acrobata", "EXE_INDEX", "exe", 0x40),
    ("acrobata", "EXE_SCENES", "exe", 0x40),
    ("acrobata", "NAME_DIRECT", "SIMPRG.REL", 0x40),
    ("acrobata", "NAME_LOCAL_INDEX", "SIMPRG.REL", 0x40),
    ("acrobata", "NAME_LOCAL", "SIMPRG.REL", 0x40),
    ("mbb", "GLOBAL_VARS", "SIMPRG.REL", 0x40),
    ("mbb", "STRING_CASES", "SIMPRG.REL", 0x40),
    ("mbb", "NUMBER_CASES", "SIMPRG.REL", 0x40),
    ("mbb", "WILDCARDS", "exe", 0x40),
    ("mbb", "VARBUF_SETTERS", "exe", 0x40),
    ("pbdata", "GROUP_TABLE", "exe", 0x40),
    ("save", "BF_P", "SAVEPRG.REL", 0x40),
    ("save", "BF_S", "SAVEPRG.REL", 0x40),
    ("save", "KEY_OFF", "SAVEPRG.REL", 0x10),
    ("save", "CRC_TABLE", "SAVEPRG.REL", 0x40),
    ("save", "READ_BLOCK", "SAVEPRG.REL", 0x40),
    ("save", "WRITE_BLOCK", "SAVEPRG.REL", 0x40),
    ("save", "PWORK_SIZES", "exe", 0x28),
    ("save", "ABIL_EXP", "exe", 0x40),
    ("save", "REPUTATION_TABLE", "exe", 0x18),
    ("save", "STATUS_CAPS", "exe", 0x18),
    ("save", "RIVAL_RANKS", "exe", 0x18),
    ("sounddat", "BANK_TABLE", "exe", 0x40),
    ("sounddat", "MUSIC_TABLE", "exe", 0x40),
    ("uniform", "LICENCE_TABLE", "exe", 0x40),
    ("uniform", "DESCRIPTOR_TABLE", "exe", 0x40),
)


# --- builds ---------------------------------------------------------------------

def exe_name(iso_dir):
    """The executable's name in an extracted disc folder."""
    for name in EXES:
        if os.path.isfile(os.path.join(iso_dir, name)):
            return name
    raise ValueError("%s: no %s" % (iso_dir, " or ".join(EXES)))


def exe_path(iso_dir):
    return os.path.join(iso_dir, exe_name(iso_dir))


def build_of(path):
    """'PAL' or 'JP' for a disc folder, an executable, or an overlay in DLL/."""
    if os.path.isdir(path):
        return EXES[exe_name(path)]
    name = os.path.basename(path).upper()
    if name in EXES:
        return EXES[name]
    iso = os.path.dirname(os.path.dirname(os.path.abspath(path)))
    return EXES[exe_name(iso)]


def reference_of(path):
    """The PAL file that `path` corresponds to."""
    name = os.path.basename(path)
    if name.upper() in EXES or open(path, "rb").read(4) == b"\x7fELF":
        return os.path.join(REFERENCE_ISO, PAL_EXE)
    return os.path.join(REFERENCE_ISO, "DLL", name.upper())


def _same_file(a, b):
    if not os.path.exists(b):
        return False
    if os.path.samefile(a, b):
        return True
    if os.path.getsize(a) != os.path.getsize(b):
        return False
    with open(a, "rb") as fa, open(b, "rb") as fb:
        return fa.read() == fb.read()


# --- images ---------------------------------------------------------------------

def _hilo_refs(words, base):
    """Distinct addresses built by `lui` plus an immediate use of the same
    register (addiu, ori, a load or store), in order. Capstone isn't needed:
    only the opcode fields are read."""
    hi, out = {}, []
    for w in words:
        op, rs, rt, imm = w >> 26, (w >> 21) & 31, (w >> 16) & 31, w & 0xFFFF
        if op == 0x0F:                                  # lui
            hi[rt] = imm << 16
            continue
        if rs in hi and op in _IMM_OPS:
            a = hi[rs] + (imm if op == 0x0D else imm - (imm & 0x8000) * 2)
            a &= 0xFFFFFFFF
            if a not in out:
                out.append(a)
        if op in (0, 0x1C):                             # SPECIAL, MMI: rd was written
            hi.pop((w >> 11) & 31, None)
        elif op not in _STORE_OPS and op not in (1, 2, 3, 4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
            hi.pop(rt, None)                            # rt was written
    return out


_STORE_OPS = {0x28, 0x29, 0x2B, 0x3F, 0x39, 0x1F, 0x2C, 0x2D, 0x2E, 0x3D}
_IMM_OPS = {0x09, 0x0D, 0x20, 0x21, 0x23, 0x24, 0x25, 0x27, 0x37, 0x31, 0x35, 0x1A, 0x1B,
            0x1E, 0x26, 0x22} | _STORE_OPS


class Image:
    """An executable or overlay: its bytes, named functions, and the
    addresses each function loads."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as f:
            head = f.read(4)
        if head == b"\x7fELF":
            self._load_exe(path)
        else:
            self._load_rel(path)
        self.starts = sorted(self.refs)
        self._name_callees()

    def _load_exe(self, path):
        import sles_disasm
        elf = self.elf = sles_disasm.Elf(path)
        self.data = elf.data
        self.v2f = elf.v2f
        funcs = sles_disasm.recover_symbols(elf)
        self.addr_of = dict(funcs)
        for name, value, _ in sles_disasm.Links(elf).symbols:
            if name and value and elf.v2f(value) is not None:
                self.addr_of.setdefault(name, value)
        self.name_at = {}
        for name, a in self.addr_of.items():
            self.name_at.setdefault(a, name)
        lo, size = elf.sections[".text"]
        words = struct.unpack_from("<%dI" % (size // 4), self.data, elf.v2f(lo))
        # Function starts: the symbols and every jal target.
        starts = set(funcs.values())
        starts |= {(w & 0x3FFFFFF) << 2 for w in words if w >> 26 == 3}
        starts = sorted(a for a in starts if lo <= a < lo + size) + [lo + size]
        self.refs, self.calls = {}, {}
        for a, b in zip(starts, starts[1:]):
            body = words[(a - lo) // 4:(b - lo) // 4]
            self.refs[a] = _hilo_refs(body, a)
            self.calls[a] = list(dict.fromkeys(
                (w & 0x3FFFFFF) << 2 for w in body if w >> 26 == 3 and w & 0x3FFFFFF))

    def _load_rel(self, path):
        import snr2
        m = self.rel = snr2.Snr2(path)
        self.data = m.data
        self.v2f = lambda a: a if 0 <= a < len(m.data) else None
        self.addr_of = {}
        for name, value, _, kind in m.syms:
            if name and value and kind in (snr2.SYM_EXPORT, snr2.SYM_WEAK):
                self.addr_of.setdefault(name, value)
        self.name_at = {}
        for name, a in self.addr_of.items():
            self.name_at.setdefault(a, name)
        targets = m.targets()
        # Function starts: the exports and every local jal target.
        starts = set(self.addr_of.values())
        starts |= {targets[o] for o, t in m.local if t == snr2.L_J26 and targets.get(o) is not None}
        starts = sorted(s for s in starts if s < m.h["sym_off"])
        self.refs = {s: [] for s in starts}
        self.calls = {s: [] for s in starts}
        for off, t in sorted(m.local):
            if targets.get(off) is None:
                continue
            i = bisect.bisect_right(starts, off) - 1
            if i < 0:
                continue
            into = self.calls if t == snr2.L_J26 else self.refs if t in (snr2.L_HI16, snr2.L_LO16) else None
            if into is not None and targets[off] not in into[starts[i]]:
                into[starts[i]].append(targets[off])

    def _name_callees(self, depth=3):
        """Give functions aliases after their named callers: 'caller>n' is
        the n-th distinct function the caller calls. A function gets one
        alias per caller, so a caller that only one build has doesn't
        rename it; an alias that would name two functions is dropped."""
        self.aliases = {a: [n] for a, n in self.name_at.items() if a in self.refs}
        for _ in range(depth):
            new = {}
            for start in self.starts:
                for name in self.aliases.get(start, ()):
                    for n, callee in enumerate(self.calls.get(start, ())):
                        if callee in self.refs and callee not in self.name_at:
                            new.setdefault(callee, set()).add("%s>%d" % (name, n))
            grown = False
            for a, names in new.items():
                have = self.aliases.setdefault(a, [])
                for name in sorted(names - set(have)):
                    have.append(name)
                    grown = True
            if not grown:
                break
        self.alias_addr, clash = {}, set()
        for a, names in self.aliases.items():
            for name in names:
                if self.alias_addr.setdefault(name, a) != a:
                    clash.add(name)
        for name in clash:
            del self.alias_addr[name]

    def function_at(self, addr):
        i = bisect.bisect_right(self.starts, addr) - 1
        return self.starts[i] if i >= 0 else None

    def bytes_at(self, addr, size):
        o = self.v2f(addr)
        return None if o is None else self.data[o:o + size]

    def pattern(self, addr, size):
        """A regex for the bytes at `addr`. Inside a function, the immediate
        of lui/addiu/ori/loads/stores and jal's target are wildcards, since
        addresses differ between builds."""
        raw = self.bytes_at(addr, size)
        if raw is None:
            return None
        code = self.function_at(addr) is not None and self.function_at(addr) <= addr < self._code_end()
        if not code:
            return re.escape(raw)
        out = []
        for k in range(0, len(raw) - 3, 4):
            w = struct.unpack_from("<I", raw, k)[0]
            op = w >> 26
            if op == 3 or op == 2:                       # jal / j
                out.append(b"...[" + re.escape(bytes([op << 2])) + b"-" + re.escape(bytes([op << 2 | 3])) + b"]")
            elif op == 0x0F or op in _IMM_OPS:
                out.append(b".." + re.escape(raw[k + 2:k + 4]))
            else:
                out.append(re.escape(raw[k:k + 4]))
        return b"".join(out)

    def _code_end(self):
        if hasattr(self, "elf"):
            lo, size = self.elf.sections[".text"]
            return lo + size
        return self.rel.h["sym_off"]

    def find(self, pattern):
        """The addresses where `pattern` matches, 4-aligned."""
        out = []
        for mt in re.finditer(pattern, self.data, re.DOTALL):
            if mt.start() % 4 == 0:
                a = self._f2v(mt.start())
                if a is not None:
                    out.append(a)
        return out

    def _f2v(self, off):
        return self.elf.f2v(off) if hasattr(self, "elf") else off


# --- translation ----------------------------------------------------------------

_images = {}


def image(path):
    key = os.path.abspath(path)
    if key not in _images:
        _images[key] = Image(path)
    return _images[key]


def translate(ref_path, path, addr, size=0x40):
    """(address in `path`, how it was found) for PAL address `addr` in
    `ref_path`, or (None, why not)."""
    ref, other = image(ref_path), image(path)
    name = ref.name_at.get(addr)
    if name and name in other.addr_of:
        return other.addr_of[name], "symbol %s" % name
    # A function without a symbol: one of its caller-made names. They must agree.
    theirs = {other.alias_addr[n]: n for n in ref.aliases.get(addr, ())
              if n in ref.alias_addr and n in other.alias_addr}
    if len(theirs) == 1:
        (found, alias), = theirs.items()
        return found, "function %s" % alias

    pat = ref.pattern(addr, size)
    hits = other.find(pat) if pat else []
    exact = _vote(ref, other, addr, size, True)
    if exact:
        best, how = exact
        if best is None:
            return None, how
        if len(hits) == 1 and hits[0] != best:
            return None, "%s gives %#x, but the bytes are at %#x" % (how, best, hits[0])
        return best, how + (", bytes agree" if hits == [best] else "")
    if len(hits) == 1:
        return hits[0], "bytes"
    if hits:
        # The same bytes in several places: take the one in the same
        # place in the order, if both files have the same number.
        mine = ref.find(pat)
        if len(mine) == len(hits) and addr in mine:
            k = mine.index(addr)
            return hits[k], "bytes, match %d of %d in both" % (k + 1, len(hits))
    near = _vote(ref, other, addr, size, False)
    if near:
        return near
    return None, "not found (%s)" % ("bytes match %d places" % len(hits) if hits else "no match")


def _vote(ref, other, addr, size, exact):
    """(address, how) from the functions that load `addr` (exact) or an
    address up to NEAR away; (None, why) if they disagree; None if none do."""
    votes = {}
    for start, loads in ref.refs.items():
        for fname in ref.aliases.get(start, ()):
            theirs = other.refs.get(other.alias_addr.get(fname), [])
            if fname not in ref.alias_addr or len(theirs) != len(loads):
                continue            # unknown there, or the code differs
            for n, a in enumerate(loads):
                d = addr - a
                if d == 0 if exact else 0 < abs(d) <= NEAR:
                    votes.setdefault((theirs[n] + d) & 0xFFFFFFFF, []).append((abs(d), fname, n, d))
    if not votes:
        return None
    # Most functions first; a close call goes to the candidate whose words
    # look most like the PAL ones.
    shape = {v: similarity(ref, addr, other, v, size) for v in votes}
    ranked = sorted(votes, key=lambda v: (-len(votes[v]), -shape[v], min(votes[v])[0]))
    best = ranked[0]
    if len(ranked) > 1 and len(votes[ranked[1]]) * 2 > len(votes[best]):
        ranked.sort(key=lambda v: -shape[v])
        best = ranked[0]
        if shape[best] <= shape[ranked[1]] or shape[best] < size // 8:
            return None, "%s: functions disagree (%s)" % (
                "reference" if exact else "near", ", ".join("%#x" % v for v in ranked))
    _, fname, n, d = min(votes[best])
    how = "reference %s #%d" % (fname, n) if d == 0 else "near %s #%d %+#x" % (fname, n, d)
    if len(votes) > 1:
        how += " (%d of %d functions)" % (len(votes[best]), sum(map(len, votes.values())))
    return best, how


def similarity(ref, addr, other, cand, size):
    """How many of the words at `cand` match the PAL words at `addr`: the
    same value, or the same distance from the first word (a table of code
    or data pointers keeps its shape when everything moves)."""
    a, b = ref.bytes_at(addr, size), other.bytes_at(cand, size)
    if not a or not b or len(a) != len(b):
        return 0
    n = len(a) // 4
    x, y = struct.unpack("<%dI" % n, a[:4 * n]), struct.unpack("<%dI" % n, b[:4 * n])
    return sum(1 for i in range(n) if x[i] == y[i] or (x[i] - x[0]) == (y[i] - y[0]))


def _cache():
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _sha1(path):
    with open(path, "rb") as f:
        return hashlib.sha1(f.read()).hexdigest()[:16]


_cached, _digests = None, {}


def at(path, addr, size=0x40):
    """PAL address `addr` as an address in `path` (an executable or
    overlay of any build). Raises ValueError if it can't be found."""
    global _cached
    ref_path = reference_of(path)
    if _same_file(path, ref_path):
        return addr
    if not os.path.exists(ref_path):
        raise ValueError("%s is needed to find addresses in %s" % (ref_path, path))
    if _cached is None:
        _cached = _cache()
    key = os.path.abspath(path)
    if key not in _digests:
        _digests[key] = _sha1(path)
    k = "%s:%s:%x:%x" % (_digests[key], os.path.basename(path).upper(), addr, size)
    if k not in _cached:
        found, how = translate(ref_path, path, addr, size)
        if found is None:
            raise ValueError("%s: can't find PAL %#x: %s" % (path, addr, how))
        _cached[k] = [found, how]
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        with open(CACHE, "w", encoding="utf-8") as f:
            json.dump(_cached, f, indent=0, sort_keys=True)
    return _cached[k][0]


def imm(path, func, value):
    """A constant the code holds as an immediate (a loop bound, a table
    size): `value` in the PAL function at `func`, as the other build's
    copy of that function has it. The instruction is the one with the
    same opcode and registers, counted from the function's start; if
    registers were allocated differently, the same opcode and destination,
    then the same opcode alone."""
    ref_path = reference_of(path)
    if _same_file(path, ref_path):
        return value
    ref, other = image(ref_path), image(path)
    mine = _function_words(ref, func)
    theirs = _function_words(other, at(path, func))
    for i, w in enumerate(mine):
        if w & 0xFFFF == value and w >> 26 in (0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D):
            break
    else:
        raise ValueError("%s: no immediate %#x in the function at %#x" % (ref_path, value, func))
    for mask in (0xFFFF0000, 0xFC1F0000, 0xFC000000):
        k = sum(1 for x in mine[:i] if x & mask == w & mask)
        same = [x for x in theirs if x & mask == w & mask]
        if len(same) == sum(1 for x in mine if x & mask == w & mask) and k < len(same):
            return same[k] & 0xFFFF
    raise ValueError("%s: no instruction like PAL %#x's immediate %#x" % (path, func, value))


def _function_words(im, func):
    i = im.starts.index(func)
    end = im.starts[i + 1] if i + 1 < len(im.starts) else im._code_end()
    o = im.v2f(func)
    return struct.unpack_from("<%dI" % ((end - func) // 4), im.data, o)


# --- commands -------------------------------------------------------------------

def _file_for(iso_dir, kind):
    return exe_path(iso_dir) if kind == "exe" else os.path.join(iso_dir, "DLL", kind)


def cmd_check(iso_dir):
    import importlib
    problems = 0
    for tool, const, kind, size in ADDRESSES:
        value = getattr(importlib.import_module(tool), const)
        path = _file_for(iso_dir, kind)
        ref_path = reference_of(path)
        for addr in value if isinstance(value, tuple) else (value,):
            label = "%-9s %-17s %-12s %#8x" % (tool, const, os.path.basename(path), addr)
            found, how = translate(ref_path, path, addr, size)
            if found is None:
                problems += 1
                print("%s  ->     ?      !! %s" % (label, how))
                continue
            same = image(ref_path).bytes_at(addr, size) == image(path).bytes_at(found, size)
            print("%s  -> %#8x  %s%s" % (label, found, how, "" if same else "; bytes differ"))
    print("%d addresses, %d not found" % (sum(
        len(getattr(__import__(t), c)) if isinstance(getattr(__import__(t), c), tuple) else 1
        for t, c, _, _ in ADDRESSES), problems))
    return 1 if problems else 0


def main(argv):
    args = argv[1:]
    if len(args) == 2 and args[0] == "which":
        print(build_of(args[1]))
        return 0
    if len(args) in (3, 4) and args[0] == "at":
        size = int(args[3], 16) if len(args) == 4 else 0x40
        found, how = translate(reference_of(args[1]), args[1], int(args[2], 16), size)
        print("%s  %s" % ("%#x" % found if found is not None else "?", how))
        return 0 if found is not None else 1
    if len(args) == 2 and args[0] == "check":
        return cmd_check(args[1])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
