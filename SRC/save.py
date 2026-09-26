"""Reader / writer for the memory-card saves of Let's Make a Soccer Team! (PS2).

A save is a folder BESLES-54151-Gnnn on the memory card. Its main file
(same name as the folder, 646,184 bytes) holds the game's parameter work
(Param::PlPworkTask, ten blocks), bit-packed and Blowfish encrypted:

  file    = Blowfish-ECB(key "sakatsukue", 8-byte blocks, words little-endian)
  plain   = 16-byte header, then the bit stream from +0x10 + header[0]
  header  = u32 data offset (0), u32 0, u32 layout CRC, u32 version (0x69)
  stream  = the ten Pwork blocks, each written field by field with
            PlBitsClass (MSB first) by generated code in SAVEPRG.REL

The layout CRC is CRC-16 (reflected 0x8408, init and xorout 0xFFFF) over
the ten block sizes as u32s. It checks that the save matches the build,
not the data: there is no checksum over the contents.

The per-block serializers are about 100 KB of generated MIPS code (one
_plBits_BitRead / _plBits_BitWrite call per field, loops for arrays). This
tool doesn't copy that layout: it runs the game's own read and write
functions from ISO/DLL/SAVEPRG.REL in a small R5900 interpreter, so a save
decodes into the ten blocks exactly as the game would load them, and
encodes back bit for bit.

Confirmed from the game code:
  SAVEPRG.REL 0x32158   Blowfish key schedule (P/S constants at 0x4bd78, 0x4bdc0)
  SAVEPRG.REL 0x32358   decrypt(buf, size, key, keylen); 0x32478 encrypt
  SAVEPRG.REL 0x331f8   load: decrypt with the key at 0x536a8, length 10
  SAVEPRG.REL 0x33228   version 0x69 (0x68 is read by the older reader 0xe618)
  SAVEPRG.REL 0x32ce0   layout CRC over getSize(0..9); CRC-16 at 0x31470, table 0x53408
  SAVEPRG.REL 0x32d50   per-block loop: read 0x2b9b0 (table 0x4bd28), write 0x2ba08 (table 0x4bd50)
  0x21d908              PlPworkTask::getSize(i) = table 0x533ac8[i] - 8

See DOC/SAVE_FORMAT.md.

Usage:
    python save.py info      <save> ...                   # header, CRC, stream length
    python save.py show      <save>                       # date, money, squad
    python save.py player    <save> <slot>                # one squad player's 64 abilities
    python save.py set       <save> <out> money=N         # edit into a new main file
    python save.py set       <save> <out> 3:all=99 3:15=80  #  slot:ability=level (0-99)
    python save.py decode    <save> <out.bin>             # the ten blocks, concatenated
    python save.py encode    <in.bin> <save> <out>        # re-encode edited blocks into a copy
    python save.py roundtrip <save> ...                   # decode + encode, compare
    python save.py blocks                                 # block sizes and offsets in .bin
    python save.py serial    <ISO dir> <out dir> PYRA-31396   # new boot file + SYSTEM.CNF
    python save.py rename    <save folder> <parent> PYRA-31396  # copy a save to that serial

<save> is a BESLES-54151-Gnnn folder or the main file inside it (on a
PCSX2 folder memory card these are plain files). Each run decodes the whole
save in the interpreter, which takes about 8 seconds. Needs
ISO/DLL/SAVEPRG.REL and ISO/SLES_541.51.

`serial` changes the names MC::CFcEuroIF::initialize (0x12ad38) uses for
saved games (-G) and VS data (-C). Moving the VS data keeps a modded
game's teams out of Virtua Pro Football and unmodded VS mode. It leaves
BESLES-54153FASYS alone: that is Virtua Pro Football's own save, read by
the import feature. Emulators and loaders read the serial from
SYSTEM.CNF's boot file name, so `serial` also names the executable after
the serial (PYRA_313.96) and writes a SYSTEM.CNF that boots it; it prints
the patch_disc.py command that writes both and renames the file on the
disc (--rename).
"""
import os
import struct
import sys

from sles_disasm import Elf
import snr2

SAVEPRG = "ISO/DLL/SAVEPRG.REL"
SLES = "ISO/SLES_541.51"

# SAVEPRG.REL
BF_P, BF_S = 0x4bd78, 0x4bdc0
KEY_OFF, KEY_LEN = 0x536a8, 10
CRC_TABLE = 0x53408
READ_BLOCK, WRITE_BLOCK = 0x2b9b0, 0x2ba08
# SLES_541.51
PWORK_SIZES = 0x533ac8

NBLOCKS = 10
HEADER = 0x10
VERSION = 0x69
FILE_SIZE = 646184

M32, M64 = 0xFFFFFFFF, (1 << 64) - 1


# --- Blowfish ----------------------------------------------------------------

class Blowfish:
    """Standard Blowfish; the game loads each 8-byte block as two native
    (little-endian) words, left then right."""

    def __init__(self, rel, key):
        self.P = list(struct.unpack_from("<18I", rel, BF_P))
        S = struct.unpack_from("<1024I", rel, BF_S)
        self.S = [list(S[i * 256:(i + 1) * 256]) for i in range(4)]
        j = 0
        for i in range(18):
            w = 0
            for _ in range(4):
                w = (w << 8) | key[j % len(key)]
                j += 1
            self.P[i] ^= w
        l = r = 0
        for i in range(0, 18, 2):
            l, r = self._enc(l, r)
            self.P[i], self.P[i + 1] = l, r
        for s in self.S:
            for i in range(0, 256, 2):
                l, r = self._enc(l, r)
                s[i], s[i + 1] = l, r

    def _f(self, x):
        s0, s1, s2, s3 = self.S
        return (((s0[x >> 24] + s1[(x >> 16) & 255]) & M32) ^ s2[(x >> 8) & 255]) + s3[x & 255] & M32

    def _enc(self, l, r):
        P = self.P
        for i in range(16):
            l ^= P[i]
            r ^= self._f(l)
            l, r = r, l
        return r ^ P[17], l ^ P[16]

    def _dec(self, l, r):
        P = self.P
        for i in range(17, 1, -1):
            l ^= P[i]
            r ^= self._f(l)
            l, r = r, l
        return r ^ P[0], l ^ P[1]

    def _run(self, data, fn):
        if len(data) % 8:
            raise ValueError("length %d is not a multiple of 8" % len(data))
        out = bytearray(len(data))
        for o in range(0, len(data), 8):
            struct.pack_into("<II", out, o, *fn(*struct.unpack_from("<II", data, o)))
        return bytes(out)

    def decrypt(self, data):
        return self._run(data, self._dec)

    def encrypt(self, data):
        return self._run(data, self._enc)


# --- bit streams (PlBitsClass, MSB first) ------------------------------------

class BitReader:
    def __init__(self, buf, pos=0):
        self.buf, self.pos = buf, pos

    def read(self, n):
        if self.pos + n > len(self.buf) * 8:
            raise ValueError("bit stream ends at bit %d, %d more wanted" % (self.pos, n))
        v = 0
        for _ in range(n):
            v = (v << 1) | ((self.buf[self.pos >> 3] >> (7 - (self.pos & 7))) & 1)
            self.pos += 1
        return v


class BitWriter:
    def __init__(self):
        self.out, self.acc, self.n = bytearray(), 0, 0
        self.bits = 0

    def write(self, value, n):
        for i in range(n - 1, -1, -1):
            self.acc = (self.acc << 1) | ((value >> i) & 1)
            self.n += 1
            if self.n == 8:
                self.out.append(self.acc)
                self.acc = self.n = 0
        self.bits += n

    def data(self):
        if self.n:
            return bytes(self.out) + bytes([self.acc << (8 - self.n)])
        return bytes(self.out)


# --- R5900 interpreter -------------------------------------------------------

def s32(v):
    """Sign-extend the low 32 bits into a 64-bit register value."""
    v &= M32
    return v | 0xFFFFFFFF00000000 if v & 0x80000000 else v


def i64(v):
    return v - (1 << 64) if v >> 63 else v


def i32(v):
    v &= M32
    return v - (1 << 32) if v & 0x80000000 else v


class Cpu:
    """Just enough of the EE to run the save serializers: integer ops, loads
    and stores, branches with delay slots, R5900 three-operand mult/madd,
    and lq/sq for the register saves. Import calls go to Python hooks."""

    MEM_SIZE = 0x400000
    RETURN = 0x3FFFFF0      # a return address outside memory ends run()
    IMPORT = 0x3000000      # jal to an import jumps here + 4 * import index

    def __init__(self, rel_path):
        self.rel = snr2.Snr2(rel_path)
        img = self.rel.data
        self.mem = bytearray(self.MEM_SIZE)
        self.mem[:len(img)] = img
        self.r = [0] * 32
        self.rq = [0] * 32          # upper 64 bits, only moved by lq/sq
        self.lo = self.hi = 0
        self.hooks = {}
        self.imports = {}           # jal site -> import name
        for off, t, sym, _ in self.rel.ext:
            if t == 4:              # R_MIPS_26
                self.imports[off] = self.rel.syms[sym][0]
        self.names = sorted(set(self.imports.values()))
        self.code = {}
        self.steps = 0

    # memory
    def ld(self, a, n):
        return int.from_bytes(self.mem[a:a + n], "little")

    def st(self, a, v, n):
        self.mem[a:a + n] = (v & ((1 << (8 * n)) - 1)).to_bytes(n, "little")

    def call(self, pc, *args, sp=0x3F0000):
        r = self.r
        for i, a in enumerate(args):
            r[4 + i] = a & M64
        r[29], r[31] = sp, self.RETURN
        self.run(pc)
        return r[2]

    def run(self, pc):
        r, mem = self.r, self.mem
        npc = pc + 4
        while pc != self.RETURN:
            if pc >= self.IMPORT:
                name = self.names[(pc - self.IMPORT) >> 2]
                hook = self.hooks.get(name)
                if hook is None:
                    raise ValueError("call to %s, which has no hook" % name)
                r[2] = hook(r[4], r[5], r[6], r[7]) & M64
                pc, npc = r[31], r[31] + 4
                continue
            self.steps += 1
            w = int.from_bytes(mem[pc:pc + 4], "little")
            op = w >> 26
            rs, rt = (w >> 21) & 31, (w >> 16) & 31
            imm = w & 0xFFFF
            simm = imm - 0x10000 if imm & 0x8000 else imm
            target = None       # taken branch or jump
            skip = False        # likely branch not taken: annul the delay slot
            if op == 0:
                rd, sa, fn = (w >> 11) & 31, (w >> 6) & 31, w & 63
                a, b = r[rs], r[rt]
                if fn == 0x00: v = s32(b << sa)
                elif fn == 0x02: v = s32((b & M32) >> sa)
                elif fn == 0x03: v = s32(i32(b) >> sa)
                elif fn == 0x04: v = s32(b << (a & 31))
                elif fn == 0x06: v = s32((b & M32) >> (a & 31))
                elif fn == 0x07: v = s32(i32(b) >> (a & 31))
                elif fn == 0x08: target, v, rd = a, None, 0
                elif fn == 0x09: target, v = a, pc + 8
                elif fn == 0x0A: v = a if b == 0 else r[rd]
                elif fn == 0x0B: v = a if b != 0 else r[rd]
                elif fn == 0x0F: v, rd = None, 0
                elif fn == 0x10: v = self.hi
                elif fn == 0x11: self.hi, v, rd = a, None, 0
                elif fn == 0x12: v = self.lo
                elif fn == 0x13: self.lo, v, rd = a, None, 0
                elif fn == 0x14: v = (b << (a & 63)) & M64
                elif fn == 0x16: v = b >> (a & 63)
                elif fn == 0x17: v = (i64(b) >> (a & 63)) & M64
                elif fn in (0x18, 0x19):
                    p = i32(a) * i32(b) if fn == 0x18 else (a & M32) * (b & M32)
                    self.lo, self.hi = s32(p), s32(p >> 32)
                    v = self.lo
                elif fn in (0x1A, 0x1B):
                    x, y = (i32(a), i32(b)) if fn == 0x1A else (a & M32, b & M32)
                    if y:
                        q = abs(x) // abs(y) * (1 if (x < 0) == (y < 0) else -1)
                        self.lo, self.hi = s32(q), s32(x - q * y)
                    v, rd = None, 0
                elif fn in (0x20, 0x21): v = s32(a + b)
                elif fn in (0x22, 0x23): v = s32(a - b)
                elif fn == 0x24: v = a & b
                elif fn == 0x25: v = a | b
                elif fn == 0x26: v = a ^ b
                elif fn == 0x27: v = ~(a | b) & M64
                elif fn == 0x2A: v = int(i64(a) < i64(b))
                elif fn == 0x2B: v = int(a < b)
                elif fn in (0x2C, 0x2D): v = (a + b) & M64
                elif fn in (0x2E, 0x2F): v = (a - b) & M64
                elif fn == 0x38: v = (b << sa) & M64
                elif fn == 0x3A: v = b >> sa
                elif fn == 0x3B: v = (i64(b) >> sa) & M64
                elif fn == 0x3C: v = (b << (sa + 32)) & M64
                elif fn == 0x3E: v = b >> (sa + 32)
                elif fn == 0x3F: v = (i64(b) >> (sa + 32)) & M64
                else:
                    raise ValueError("%#x: SPECIAL %#x not supported" % (pc, fn))
                if rd and v is not None:
                    r[rd] = v
            elif op == 1:
                a = i64(r[rs])
                cond = a < 0 if rt in (0, 2) else a >= 0
                if rt > 3:
                    raise ValueError("%#x: REGIMM %#x not supported" % (pc, rt))
                if cond:
                    target = npc + (simm << 2)
                elif rt in (2, 3):
                    skip = True
            elif op in (2, 3):
                if op == 3:
                    r[31] = pc + 8
                if op == 3 and pc in self.imports:
                    target = self.IMPORT + 4 * self.names.index(self.imports[pc])
                else:
                    target = (w & 0x3FFFFFF) << 2
            elif op in (4, 5, 6, 7, 0x14, 0x15, 0x16, 0x17):
                a, b = r[rs], r[rt]
                k = op & 3
                cond = (a == b, a != b, i64(a) <= 0, i64(a) > 0)[k]
                if cond:
                    target = npc + (simm << 2)
                elif op >= 0x14:
                    skip = True
            elif op in (8, 9):
                if rt: r[rt] = s32(r[rs] + simm)
            elif op == 0x0A:
                if rt: r[rt] = int(i64(r[rs]) < simm)
            elif op == 0x0B:
                if rt: r[rt] = int(r[rs] < (simm & M64))
            elif op == 0x0C:
                if rt: r[rt] = r[rs] & imm
            elif op == 0x0D:
                if rt: r[rt] = r[rs] | imm
            elif op == 0x0E:
                if rt: r[rt] = r[rs] ^ imm
            elif op == 0x0F:
                if rt: r[rt] = s32(imm << 16)
            elif op in (0x18, 0x19):
                if rt: r[rt] = (r[rs] + simm) & M64
            elif op == 0x1C:
                fn, rd = w & 63, (w >> 11) & 31
                if fn not in (0, 1):
                    raise ValueError("%#x: MMI %#x not supported" % (pc, fn))
                a, b = r[rs], r[rt]
                p = i32(a) * i32(b) if fn == 0 else (a & M32) * (b & M32)
                acc = ((self.hi & M32) << 32 | (self.lo & M32)) + p
                self.lo, self.hi = s32(acc), s32(acc >> 32)
                if rd:
                    r[rd] = self.lo
            else:
                addr = (r[rs] + simm) & M32
                if op == 0x20: v = self.ld(addr, 1); v = v - 256 if v & 0x80 else v
                elif op == 0x21: v = self.ld(addr, 2); v = v - 0x10000 if v & 0x8000 else v
                elif op == 0x23: v = i32(self.ld(addr, 4))
                elif op == 0x24: v = self.ld(addr, 1)
                elif op == 0x25: v = self.ld(addr, 2)
                elif op == 0x27: v = self.ld(addr, 4)
                elif op == 0x37: v = self.ld(addr, 8)
                elif op == 0x1E:
                    addr &= ~15
                    v, self.rq[rt] = self.ld(addr, 8), self.ld(addr + 8, 8)
                elif op == 0x28: self.st(addr, r[rt], 1); v = None
                elif op == 0x29: self.st(addr, r[rt], 2); v = None
                elif op == 0x2B: self.st(addr, r[rt], 4); v = None
                elif op == 0x3F: self.st(addr, r[rt], 8); v = None
                elif op == 0x1F:
                    addr &= ~15
                    self.st(addr, r[rt], 8)
                    self.st(addr + 8, self.rq[rt] if rt else 0, 8)
                    v = None
                elif op == 0x2F: v = None      # cache
                else:
                    raise ValueError("%#x: opcode %#x not supported" % (pc, op))
                if v is not None and rt:
                    r[rt] = v & M64
            r[0] = 0
            if skip:
                pc, npc = npc + 4, npc + 8
            elif target is not None:
                pc, npc = npc, target
            else:
                pc, npc = npc, npc + 4


# --- save files --------------------------------------------------------------

def crc16(rel, data):
    tab = struct.unpack_from("<256H", rel, CRC_TABLE)
    c = 0xFFFF
    for b in data:
        c = (c >> 8) ^ tab[(b ^ c) & 0xFF]
    return c ^ 0xFFFF


def block_sizes(sles_path=SLES):
    elf = Elf(sles_path)
    raw = struct.unpack_from("<%dI" % NBLOCKS, elf.data, elf.v2f(PWORK_SIZES))
    return [v - 8 for v in raw]


class Game:
    """The pieces of the game code a save needs."""

    def __init__(self, rel_path=SAVEPRG, sles_path=SLES):
        with open(rel_path, "rb") as f:
            self.rel = f.read()
        self.rel_path = rel_path
        self.key = self.rel[KEY_OFF:KEY_OFF + KEY_LEN]
        self.bf = Blowfish(self.rel, self.key)
        self.sizes = block_sizes(sles_path)
        self.crc = crc16(self.rel, struct.pack("<%dI" % NBLOCKS, *self.sizes))
        self.offsets = [sum(self.sizes[:i]) for i in range(NBLOCKS + 1)]

    def cpu(self):
        return Cpu(self.rel_path)

    def unpack(self, plain):
        """Bit stream -> (the ten blocks as one bytes object, bits used)."""
        off, _, crc, ver = struct.unpack_from("<4I", plain)
        if ver != VERSION:
            raise ValueError("version %#x; only %#x is supported" % (ver, VERSION))
        if crc != self.crc:
            raise ValueError("layout CRC %#06x, this build expects %#06x" % (crc, self.crc))
        cpu = self.cpu()
        bits = BitReader(plain, 8 * (HEADER + off))

        def bit_read(_, n, signed, __):
            if n == 0:
                return 0
            v = bits.read(n)
            if signed and n < 64 and v >> (n - 1) & 1:
                v |= (M64 >> 4) << n     # as _plBits_BitRead (0x20c200)
            return v

        def bit_read_str(_, p, n, __):
            for i in range(i32(n)):
                c = bits.read(8)
                if p:
                    cpu.mem[p + i] = c
            return 0

        cpu.hooks["_plBits_BitRead__5ParamPQ25Param11PlBitsClassii"] = bit_read
        cpu.hooks["_plBits_BitReadStr__5ParamPQ25Param11PlBitsClassPci"] = bit_read_str
        base = self.block_base()
        for i in range(NBLOCKS):
            cpu.call(READ_BLOCK, 0x3F8000, base + self.offsets[i], i)
        return bytes(cpu.mem[base:base + self.offsets[-1]]), bits.pos - 8 * HEADER

    def pack(self, blocks):
        """The ten blocks -> the bit stream (without header)."""
        if len(blocks) != self.offsets[-1]:
            raise ValueError("blocks are %d bytes, expected %d" % (len(blocks), self.offsets[-1]))
        cpu = self.cpu()
        base = self.block_base()
        cpu.mem[base:base + len(blocks)] = blocks
        out = BitWriter()

        def bit_write(_, value, n, __):
            n = i32(n)
            if n:
                out.write(value & ((1 << n) - 1), n)
            return 0

        def bit_write_str(_, p, n, __):
            for i in range(i32(n)):
                out.write(cpu.mem[p + i] if p else 0, 8)
            return 0

        cpu.hooks["_plBits_BitWrite__5ParamPQ25Param11PlBitsClasslii"] = bit_write
        cpu.hooks["_plBits_BitWriteStr__5ParamPQ25Param11PlBitsClassPci"] = bit_write_str
        for i in range(NBLOCKS):
            cpu.call(WRITE_BLOCK, 0x3F8000, base + self.offsets[i], i)
        return out.data(), out.bits

    @staticmethod
    def block_base():
        return 0x100000

    def decrypt(self, data):
        return self.bf.decrypt(data)

    def encrypt(self, plain):
        return self.bf.encrypt(plain)


# --- what's in the blocks ----------------------------------------------------

# Block 0: general state. pwkGen_GetSikin (0x2444e0) reads the club's money
# as an s64 at +0; pwkGen_GetDate (0x244368) copies the PlDate at +0x88.
MONEY_OFF = 0x0
DATE_OFF = 0x88
# Block 1: your club. pwkTeam_GetMyTeamData (0x259898) returns +0x4b4, a
# PlTeamData whose +0x20 holds 25 PlPinfo of 0x2a0 bytes
# (pwkTeam_GetForeignCitizenNumber 0x266450 walks them).
TEAM_OFF = 0x4b4
SQUAD_OFF, SQUAD_SLOTS, PINFO_SIZE = 0x20, 25, 0x2a0
# PlPinfo: +0 s16 database id (negative = empty slot, 0x2664d0);
# +0xa 64 x {u16 exp, u16, u16 cap} abilities (plPinfo_ConvAbilLv 0x216c90).
ABIL_OFF, ABIL_COUNT = 0xa, 64
PINFO_POS, PINFO_AGE, PINFO_NAME, NAME_LEN = 0x4, 0x8, 0x198, 0x13
# SLES_541.51: ability experience per level 0-100, plMisc_AbilExp2Lv (0x2153c0)
# and plMisc_AbilLv2Exp (0x215438).
ABIL_EXP = 0x531c70
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def exp_table(sles_path=SLES):
    elf = Elf(sles_path)
    return struct.unpack_from("<101H", elf.data, elf.v2f(ABIL_EXP))


def exp2lv(table, exp):
    """plMisc_AbilExp2Lv: one less than the first level whose threshold
    reaches exp, searching 1-50 or 51-100."""
    lv, top = (1, 50) if exp < table[51] else (51, 100)
    while lv <= top and table[lv] < exp:
        lv += 1
    return lv - 1


class Save:
    """A decoded save: the ten blocks plus the file it came from."""

    def __init__(self, game, path):
        self.game, self.path = game, save_path(path)
        with open(self.path, "rb") as f:
            self.file = f.read()
        self.blocks = bytearray(game.unpack(game.decrypt(self.file))[0])
        self.exp = exp_table()

    def at(self, block, off):
        return self.game.offsets[block] + off

    @property
    def money(self):
        return struct.unpack_from("<q", self.blocks, self.at(0, MONEY_OFF))[0]

    @money.setter
    def money(self, v):
        struct.pack_into("<q", self.blocks, self.at(0, MONEY_OFF), v)

    def date(self):
        """(year, turn of season 0-95, month 1-12, turn of month 0-7);
        see plMisc_SetTurn2Date (0x214698)."""
        o = self.at(0, DATE_OFF)
        year, turn, month = struct.unpack_from("<HBB", self.blocks, o)
        return year, turn, month, struct.unpack_from("<I", self.blocks, o + 4)[0]

    def squad(self):
        """[(slot, offset of the PlPinfo in blocks)] for filled slots."""
        base = self.at(1, TEAM_OFF + SQUAD_OFF)
        out = []
        for i in range(SQUAD_SLOTS):
            o = base + i * PINFO_SIZE
            if struct.unpack_from("<h", self.blocks, o)[0] >= 0:
                out.append((i, o))
        return out

    def pinfo(self, o):
        b = self.blocks
        name = b[o + PINFO_NAME:o + PINFO_NAME + NAME_LEN].split(b"\0")[0].decode("cp850")
        abil = [struct.unpack_from("<3H", b, o + ABIL_OFF + 6 * k) for k in range(ABIL_COUNT)]
        return {"id": struct.unpack_from("<h", b, o)[0], "name": name,
                "pos": b[o + PINFO_POS], "age": b[o + PINFO_AGE], "abil": abil}

    def set_ability(self, o, k, level):
        """Set ability k to `level` (0-99): its experience becomes
        plMisc_AbilLv2Exp(level, 50), halfway into the level (a value on a
        threshold reads back one level lower), and the cap is raised to
        match if it was lower."""
        if not 0 <= level <= 99:
            raise ValueError("level must be 0-99")
        t = self.exp
        exp = t[level] + (t[level + 1] - t[level]) * 50 // 100
        a = o + ABIL_OFF + 6 * k
        cur, mid, cap = struct.unpack_from("<3H", self.blocks, a)
        struct.pack_into("<3H", self.blocks, a, exp, mid, max(cap, exp))

    def encode(self):
        return build(self.game, bytes(self.blocks), self.file)[0]


def save_path(p):
    """A save folder -> its main file."""
    if os.path.isdir(p):
        return os.path.join(p, os.path.basename(os.path.normpath(p)))
    return p


# --- commands ----------------------------------------------------------------

def cmd_info(game, paths):
    for p in paths:
        f = save_path(p)
        try:
            with open(f, "rb") as fh:
                data = fh.read()
            probs = []
            if len(data) != FILE_SIZE:
                probs.append("size %d, expected %d" % (len(data), FILE_SIZE))
            plain = game.decrypt(data[:len(data) & ~7])
            off, zero, crc, ver = struct.unpack_from("<4I", plain)
            if off or zero:
                probs.append("header words %#x %#x, expected 0 0" % (off, zero))
            _, used = game.unpack(plain)
            tail = plain[HEADER + off + (used + 7) // 8:]
            print("%s: version %#x, layout CRC %#06x, stream %d bits (%d bytes), %d bytes spare%s" % (
                f, ver, crc, used, (used + 7) // 8, len(tail),
                "  !! " + "; ".join(probs) if probs else ""))
        except (ValueError, struct.error, OSError) as e:
            print("%s  !! %s" % (f, e))


def cmd_decode(game, src, out):
    with open(save_path(src), "rb") as f:
        plain = game.decrypt(f.read())
    blocks, used = game.unpack(plain)
    with open(out, "wb") as f:
        f.write(blocks)
    print("%s: %d bytes, 10 blocks, from %d bits" % (out, len(blocks), used))


def build(game, blocks, template):
    """Encode blocks into a save the size of `template`, keeping its header."""
    stream, bits = game.pack(blocks)
    plain = bytearray(game.decrypt(template))
    off = struct.unpack_from("<I", plain)[0]
    start = HEADER + off
    if start + len(stream) > len(plain):
        raise ValueError("the stream is %d bytes; the file has room for %d" % (
            len(stream), len(plain) - start))
    # The game doesn't clear its buffer, so the bits after the stream are
    # leftover memory. Keep the template's, so an unedited save comes back
    # byte for byte.
    end = start + len(stream)
    if bits % 8:
        keep = 0xFF >> (bits % 8)
        stream = stream[:-1] + bytes([stream[-1] & ~keep | plain[end - 1] & keep])
    plain[start:end] = stream
    return game.encrypt(bytes(plain)), bits


def cmd_encode(game, src, template, out):
    with open(src, "rb") as f:
        blocks = f.read()
    with open(save_path(template), "rb") as f:
        tmpl = f.read()
    data, bits = build(game, blocks, tmpl)
    with open(out, "wb") as f:
        f.write(data)
    print("%s: %d bytes, stream %d bits" % (out, len(data), bits))


def cmd_roundtrip(game, paths):
    bad = 0
    for p in paths:
        f = save_path(p)
        with open(f, "rb") as fh:
            data = fh.read()
        blocks, used = game.unpack(game.decrypt(data))
        again, bits = build(game, blocks, data)
        same = again == data
        bad += not same
        print("%s: %s (%d bits)" % (f, "identical" if same else "DIFFERENT", bits))
    return 1 if bad else 0


def cmd_show(game, path):
    import pbdata
    s = Save(game, path)
    year, turn, month, week = s.date()
    print("%s" % s.path)
    print("  date   %s %d, week %d (turn %d of the season)" % (MONTHS[month - 1], year, week + 1, turn))
    print("  money  %d" % s.money)
    print("  squad")
    for slot, o in s.squad():
        p = s.pinfo(o)
        lv = [exp2lv(s.exp, a[0]) for a in p["abil"]]
        print("    %2d  id %5d  %-18s %-5s age %2d  mean ability %d" % (
            slot, p["id"], p["name"], pbdata.position_name(p["pos"]), p["age"],
            round(sum(lv) / len(lv))))


def cmd_player(game, path, slot):
    s = Save(game, path)
    hit = [o for i, o in s.squad() if i == slot]
    if not hit:
        raise SystemExit("squad slot %d is empty" % slot)
    p = s.pinfo(hit[0])
    print("%s: slot %d, id %d, %s" % (s.path, slot, p["id"], p["name"]))
    print("  ability  level  cap   (exp, ?, cap exp)")
    for k, (cur, mid, cap) in enumerate(p["abil"]):
        print("  %7d  %5d  %3d   (%d, %d, %d)" % (k, exp2lv(s.exp, cur), exp2lv(s.exp, cap), cur, mid, cap))


def cmd_set(game, path, out, assigns):
    """money=N, or slot:ability=level / slot:all=level for a squad player."""
    s = Save(game, path)
    squad = dict(s.squad())
    for a in assigns:
        key, _, val = a.partition("=")
        if not val:
            raise SystemExit("expected field=value, got %r" % a)
        if key == "money":
            s.money = int(val, 0)
            continue
        slot, _, which = key.partition(":")
        if not slot.isdigit() or int(slot) not in squad or not which:
            raise SystemExit("%r: use money=N, <slot>:<ability>=level or <slot>:all=level "
                             "(slot = a filled squad slot, see `show`)" % a)
        o = squad[int(slot)]
        for k in range(ABIL_COUNT) if which == "all" else [int(which)]:
            if not 0 <= k < ABIL_COUNT:
                raise SystemExit("ability must be 0-%d" % (ABIL_COUNT - 1))
            s.set_ability(o, k, int(val))
    data = s.encode()
    with open(out, "wb") as f:
        f.write(data)
    print("%s: %d bytes written" % (out, len(data)))


# MC::CFcEuroIF::initialize (0x12ad38) picks the memory-card name for each
# eCATEGORY: 0 game saves ("-G" + %03d), 1 VS data ("-C"), 2
# "BESLES-54153FASYS". Virtua Pro Football (SLES-54153) reads the VS data,
# and category 2 is its own save, read for the import. `serial` moves the
# game saves and the VS data, so a modded game's teams can't be carried
# into Virtua Pro Football or an unmodded VS mode (anti-cheat), and leaves
# the import alone.
CARD_NAMES = ((0x5213e8, b"BESLES-54151-G"), (0x5213f8, b"BESLES-54151-C"))


BOOT_NAME = "SLES_541.51"


def cmd_serial(iso_dir, out_dir, serial):
    """Write <out_dir>/<new boot name> (SLES_541.51 with the memory-card
    names moved to `serial`) and a SYSTEM.CNF booting it. Emulators and
    loaders take the serial from SYSTEM.CNF's BOOT2 file name, so the
    executable is renamed on the disc too (patch_disc.py --rename)."""
    import re
    if not re.fullmatch(r"[A-Z]{4}-\d{5}", serial):
        raise SystemExit("serial must look like ABCD-12345")
    boot = serial.replace("-", "_")[:8] + "." + serial[-2:]     # PYRA_313.96
    src = os.path.join(iso_dir, BOOT_NAME)
    with open(os.path.join(iso_dir, "SYSTEM.CNF"), "rb") as f:
        cnf = f.read()
    if cnf.count(BOOT_NAME.encode()) != 1:
        raise SystemExit("SYSTEM.CNF doesn't name %s once" % BOOT_NAME)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "SYSTEM.CNF"), "wb") as f:
        f.write(cnf.replace(BOOT_NAME.encode(), boot.encode()))
    out = os.path.join(out_dir, boot)
    elf = Elf(src)
    data = bytearray(elf.data)
    for va, old in CARD_NAMES:
        o = elf.v2f(va)
        if data[o:o + len(old) + 1] != old + b"\0":
            raise SystemExit("%s: %#x holds %r, expected %r" % (src, va, bytes(data[o:o + len(old)]), old))
        new = b"BE" + serial.encode() + old[12:]
        data[o:o + len(new)] = new
        print("  %#x  %s -> %s" % (va, old.decode(), new.decode()))
    with open(out, "wb") as f:
        f.write(data)
    print("%s: %d bytes" % (out, len(data)))
    print("%s: BOOT2 = cdrom0:\\%s;1" % (os.path.join(out_dir, "SYSTEM.CNF"), boot))
    print("Patch them in with:")
    print("  python SRC/patch_disc.py patch <disc.iso> <modded.iso> "
          "disc:%s=%s disc:SYSTEM.CNF=%s --rename disc:%s=%s" % (
              BOOT_NAME, out, os.path.join(out_dir, "SYSTEM.CNF"), BOOT_NAME, boot))


def cmd_rename(src, parent, serial):
    """Copy a save folder under another serial: BESLES-54151-G003 becomes
    <parent>/BEPYRA-31396-G003, main file included. The game opens
    <folder>/<folder>, so both names must change. PCSX2 folder memory cards
    also keep the name in _pcsx2_meta_directory (+0x40) and _pcsx2_index."""
    import re
    import shutil
    src = os.path.normpath(src)
    old = os.path.basename(src)
    m = re.fullmatch(r"BE([A-Z]{4}-\d{5})(-[GC]\d*)", old)
    if not m or not re.fullmatch(r"[A-Z]{4}-\d{5}", serial):
        raise SystemExit("expected a BExxxx-nnnnn-Gnnn folder and a serial like ABCD-12345")
    new = "BE" + serial + m.group(2)
    dst = os.path.join(parent, new)
    if os.path.exists(dst):
        raise SystemExit("%s already exists" % dst)
    shutil.copytree(src, dst)
    if os.path.exists(os.path.join(dst, old)):
        os.rename(os.path.join(dst, old), os.path.join(dst, new))
    meta = os.path.join(dst, "_pcsx2_meta_directory")
    if os.path.exists(meta):
        with open(meta, "r+b") as f:
            f.seek(0x40)
            if f.read(32).split(b"\0")[0] == old.encode():
                f.seek(0x40)
                f.write(new.encode().ljust(32, b"\0"))
    index = os.path.join(dst, "_pcsx2_index")
    if os.path.exists(index):
        with open(index, encoding="latin1") as f:
            text = f.read()
        with open(index, "w", encoding="latin1", newline="") as f:
            f.write(text.replace(old + ":", new + ":"))
    print("%s -> %s" % (src, dst))


def cmd_blocks(game):
    print("layout CRC %#06x" % game.crc)
    for i, s in enumerate(game.sizes):
        print("  block %d  offset %#08x  size %#07x (%d)" % (i, game.offsets[i], s, s))
    print("  total %d bytes" % game.offsets[-1])


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "serial" and len(args) == 3:
        cmd_serial(*args)
        return 0
    if cmd == "rename" and len(args) == 3:
        cmd_rename(*args)
        return 0
    game = Game()
    if cmd == "info" and args:
        cmd_info(game, args)
    elif cmd == "decode" and len(args) == 2:
        cmd_decode(game, *args)
    elif cmd == "encode" and len(args) == 3:
        cmd_encode(game, *args)
    elif cmd == "roundtrip" and args:
        return cmd_roundtrip(game, args)
    elif cmd == "show" and len(args) == 1:
        cmd_show(game, args[0])
    elif cmd == "player" and len(args) == 2:
        cmd_player(game, args[0], int(args[1]))
    elif cmd == "set" and len(args) >= 3:
        cmd_set(game, args[0], args[1], args[2:])
    elif cmd == "blocks" and not args:
        cmd_blocks(game)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
