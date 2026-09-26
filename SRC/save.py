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
encodes back bit for bit. One run of the read functions records the field
list (604,078 fields: bits, signedness, where each is stored), which is
cached in .cache/ and replayed after that; `fields` checks the replay
against the interpreter on random data both ways.

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
    python save.py player    <save> <slot>                # one player in full (youth: y<slot>)
    python save.py staff     <save>                       # manager, youth manager, coaches, scouts
    python save.py set       <save> <out> money=N         # edit into a new main file
    python save.py set       <save> <out> 3:all=99 3:15=80  #  slot:ability=level (0-99)
    python save.py set       <save> <out> 3:fatigue=0 3:condition=65535  #  slot:field=value
                                   (fields: fatigue, condition, motivation, power, form,
                                    policy_counter, policy_organisation)
    python save.py decode    <save> <out.bin>             # the ten blocks, concatenated
    python save.py encode    <in.bin> <save> <out>        # re-encode edited blocks into a copy
    python save.py roundtrip <save> ...                   # decode + encode, compare
    python save.py blocks                                 # block sizes and offsets in .bin
    python save.py fields    [rounds]                     # re-record and check the field list
    python save.py serial    <ISO dir> <out dir> PYRA-31396   # new boot file + SYSTEM.CNF
    python save.py rename    <save folder> <parent> PYRA-31396  # copy a save to that serial

<save> is a BESLES-54151-Gnnn folder or the main file inside it (on a
PCSX2 folder memory card these are plain files). Each run decodes the whole
save from the cached field list, about a second (the first run records
the list, about 10 seconds). Needs
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
import array
import hashlib
import os
import random
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
        self.on_store = None        # f(addr, width) after every store

    # memory
    def ld(self, a, n):
        return int.from_bytes(self.mem[a:a + n], "little")

    def st(self, a, v, n):
        self.mem[a:a + n] = (v & ((1 << (8 * n)) - 1)).to_bytes(n, "little")
        if self.on_store:
            self.on_store(a, n)

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


CACHE_DIR = ".cache"            # git-ignored
FIELDS_MAGIC = b"LMSF"
BYTE_MASK = {1: 0xFF, 2: 0xFFFF, 4: M32, 8: M64}


class Fields:
    """The serializers' field list, in stream order: bits, signed, and the
    offset and width in the blocks it is stored to. Recorded once from a run
    of the read functions (Game.unpack_cpu) and cached in .cache/, keyed by
    SAVEPRG.REL and the block sizes. Replaying it reads or writes a save
    without the interpreter. `check` compares both ways against the
    interpreter on random data, which also shows that the list doesn't
    depend on what the save holds."""

    def __init__(self):
        self.n, self.signed = array.array("B"), array.array("B")
        self.off, self.width = array.array("I"), array.array("B")

    def add(self, n, signed):
        self.n.append(n)
        self.signed.append(signed)
        self.off.append(0)
        self.width.append(0)
        return len(self.n) - 1

    def place(self, i, off, width):
        self.off[i], self.width[i] = off, width

    def __len__(self):
        return len(self.n)

    @property
    def bits(self):
        return sum(self.n)

    # cache

    @staticmethod
    def path(game):
        return os.path.join(CACHE_DIR, "save_fields_%s.bin" % game.cache_key)

    def save(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(FIELDS_MAGIC + struct.pack("<I", len(self)))
            for a in (self.n, self.signed, self.width, self.off):
                f.write(a.tobytes())

    @classmethod
    def load(cls, path):
        with open(path, "rb") as f:
            d = f.read()
        if d[:4] != FIELDS_MAGIC:
            raise ValueError("%s: not a field list" % path)
        count = struct.unpack_from("<I", d, 4)[0]
        self, pos = cls(), 8
        for a in (self.n, self.signed, self.width, self.off):
            size = count * a.itemsize
            a.frombytes(d[pos:pos + size])
            pos += size
        return self

    @classmethod
    def trace(cls, game):
        """Run the read functions over random bits and record the fields."""
        self = cls()
        game.unpack_cpu(random_plain(game, random.Random(1)), trace=self)
        if any(w not in BYTE_MASK for w in self.width):
            raise ValueError("a field is stored with an unexpected width")
        return self

    @classmethod
    def load_or_trace(cls, game):
        path = cls.path(game)
        if os.path.exists(path):
            return cls.load(path)
        print("(recording the save field list once; about 10 seconds)", file=sys.stderr)
        self = cls.trace(game)
        self.save(path)
        return self

    # replay

    def read(self, buf, pos, total):
        """(blocks, bits used) from the stream in buf at bit pos."""
        out = bytearray(total)
        end = len(buf) * 8
        start = pos
        for n, sg, off, w in zip(self.n, self.signed, self.off, self.width):
            if n:
                if pos + n > end:
                    raise ValueError("bit stream ends at bit %d, %d more wanted" % (pos, n))
                b0, b1 = pos >> 3, (pos + n + 7) >> 3
                v = (int.from_bytes(buf[b0:b1], "big") >> ((b1 << 3) - pos - n)) & ((1 << n) - 1)
                pos += n
                if sg and v >> (n - 1):
                    v -= 1 << n
            else:
                v = 0
            out[off:off + w] = (v & BYTE_MASK[w]).to_bytes(w, "little")
        return bytes(out), pos - start

    def write(self, blocks):
        """(stream, bits) for the blocks."""
        out = bytearray()
        acc = nb = total = 0
        for n, sg, off, w in zip(self.n, self.signed, self.off, self.width):
            if not n:
                continue
            v = int.from_bytes(blocks[off:off + w], "little")
            if sg and n > 8 * w and v >> (8 * w - 1):
                v -= 1 << (8 * w)
            acc = (acc << n) | (v & ((1 << n) - 1))
            nb += n
            total += n
            if nb >= 64:
                keep = nb & 7
                out += (acc >> keep).to_bytes((nb - keep) >> 3, "big")
                acc &= (1 << keep) - 1
                nb = keep
        if nb:
            pad = -nb & 7
            out += (acc << pad).to_bytes((nb + pad) >> 3, "big")
        return bytes(out), total

    def check(self, game, rounds=1):
        """Replay against the interpreter on random streams and blocks."""
        rng = random.Random(2)
        for _ in range(rounds):
            plain = random_plain(game, rng)
            a = game.unpack_cpu(plain)
            b = self.read(plain, game.check_header(plain), game.offsets[-1])
            if a != b:
                raise ValueError("reading random data: the field list differs from the game code")
            blocks = bytes(rng.getrandbits(8) for _ in range(game.offsets[-1]))
            if game.pack_cpu(blocks) != self.write(blocks):
                raise ValueError("writing random blocks: the field list differs from the game code")


def random_plain(game, rng):
    """A decrypted save with a valid header and random bits after it."""
    body = rng.getrandbits(8 * (FILE_SIZE - HEADER)).to_bytes(FILE_SIZE - HEADER, "little")
    return struct.pack("<4I", 0, 0, game.crc, VERSION) + body


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
        self.cache_key = hashlib.sha1(self.rel + struct.pack("<%dI" % NBLOCKS, *self.sizes)).hexdigest()[:12]
        self._fields = None

    def cpu(self):
        return Cpu(self.rel_path)

    def check_header(self, plain):
        """The bit offset of the stream in a decrypted file."""
        off, _, crc, ver = struct.unpack_from("<4I", plain)
        if ver != VERSION:
            raise ValueError("version %#x; only %#x is supported" % (ver, VERSION))
        if crc != self.crc:
            raise ValueError("layout CRC %#06x, this build expects %#06x" % (crc, self.crc))
        return 8 * (HEADER + off)

    # The game's serializers, run in the interpreter.

    def unpack_cpu(self, plain, trace=None):
        """Bit stream -> (the ten blocks, bits used), by running the read
        functions. With `trace` (a Fields), record every field: its width
        and signedness from the _plBits_BitRead call, and where it goes
        from the first store into the blocks that follows."""
        start = self.check_header(plain)
        cpu = self.cpu()
        bits = BitReader(plain, start)
        base, total = self.block_base(), self.offsets[-1]
        pending = []

        def bit_read(_, n, signed, __):
            n = i32(n)
            if trace is not None:
                if pending:
                    raise ValueError("field %d is never stored" % pending[0])
                pending.append(trace.add(n, int(bool(signed))))
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
                if trace is not None:
                    if not base <= p + i < base + total:
                        raise ValueError("string byte outside the blocks")
                    trace.place(trace.add(8, 0), p + i - base, 1)
            return 0

        def on_store(a, w):
            if pending and base <= a < base + total:
                trace.place(pending.pop(), a - base, w)

        cpu.hooks["_plBits_BitRead__5ParamPQ25Param11PlBitsClassii"] = bit_read
        cpu.hooks["_plBits_BitReadStr__5ParamPQ25Param11PlBitsClassPci"] = bit_read_str
        if trace is not None:
            cpu.on_store = on_store
        for i in range(NBLOCKS):
            cpu.call(READ_BLOCK, 0x3F8000, base + self.offsets[i], i)
        if pending:
            raise ValueError("field %d is never stored" % pending[0])
        return bytes(cpu.mem[base:base + total]), bits.pos - start

    def pack_cpu(self, blocks):
        """The ten blocks -> (the bit stream, bits), by running the write
        functions."""
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

    # The same, replayed from the recorded field list.

    def fields(self):
        if self._fields is None:
            self._fields = Fields.load_or_trace(self)
        return self._fields

    def unpack(self, plain):
        """Bit stream -> (the ten blocks as one bytes object, bits used)."""
        return self.fields().read(plain, self.check_header(plain), self.offsets[-1])

    def pack(self, blocks):
        """The ten blocks -> (the bit stream without header, bits)."""
        if len(blocks) != self.offsets[-1]:
            raise ValueError("blocks are %d bytes, expected %d" % (len(blocks), self.offsets[-1]))
        return self.fields().write(blocks)

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
# +0xa 64 x {u16 exp, u16 limit, u16 cap} abilities (plPinfo_ConvAbilLv 0x216c90;
# pwkGUtl_AddExp 0x246028 clamps exp to the limit on every gain).
ABIL_OFF, ABIL_COUNT = 0xa, 64
PINFO_POS, PINFO_AGE, PINFO_NAME, NAME_LEN = 0x4, 0x8, 0x198, 0x13
# +0x198 holds a copy of the player's PlPbase header (0x74 bytes, pbdata.py's
# struct offsets): plPinfo_IsForeigner reads +0x1ac (PlPbase +0x14),
# plPinfo_SetUnumber +0x1c3 (+0x2b), plPinfo_IsEU +0x1fb (+0x63),
# plPinfo_IsSkill +0x1fc (+0x64).
PBASE_COPY, PBASE_COPY_SIZE = 0x198, 0x74
# Game state after it. (name, offset, struct format, settable range, source)
PINFO_FIELDS = (
    ("position", 0x4, "<I", None, "grid cell; 0 = GK (ConvertPlayer_Bar)"),
    ("age", 0x8, "<B", None, "current age; plPinfo_kanLowLimit(age) via ChangeKan 0x21c840"),
    ("team", 0x190, "<I", None, "plPinfo_Team 0x218358"),
    ("fatigue", 0x23c, "<H", (0, 1000), "ChangeGtired clamps 0-1000; GetGTiredLevel 0x21b090"),
    ("status", 0x23e, "<H", None, "plPinfo_ChangeStatus"),
    ("condition", 0x240, "<H", (0, 65535), "plPinfo_Cond5 0x217800"),
    ("motivation", 0x242, "<H", (0, 65535), "plPinfo_Moti2Lv 0x217b88: / 0x3333"),
    ("power", 0x24c, "<H", (0, 1000), "plPinfo_ChangePower 0x21c8c0 clamps 0-1000"),
    ("form", 0x24e, "<H", (0, 1000),
     "the game's 'kan': ChangeKan 0x21c840 clamps to an age limit-1000; below 400 the "
     "condition line says he has lost form (ConvertPlayer_Condition 0x285728)"),
    ("injury_days", 0x250, "<H", None, "_plPinfo_SetKega, KegaRecoverDaysChno"),
    ("injury", 0x254, "<I", None, "_plPinfo_SetKega kind, IsHkegaFunou"),
    ("captain_exp", 0x25a, "<H", None, "plPinfo_ChangeCaptainExp"),
    ("keyman_exp", 0x25c, "<H", None, "plPinfo_ChangeKeymanExp"),
    ("play_style", 0x278, "<I", None, "plPinfo_GetPStyle / SetPStyle"),
    ("policy_type", 0x294, "<B", None, "pwkTeamType_PolicyInit 0x270328: from PlPbase +0x52"),
    ("policy_counter", 0x296, "<H", (0, 65535),
     "team vision: 0 possession - 65535 counter (l_calculate_policy_rect_player 0x300ba8)"),
    ("policy_organisation", 0x298, "<H", (0, 65535),
     "team vision: 0 individual - 65535 organisation"),
    ("team_fit", 0x29a, "<B", None,
     "T-FIT bar, 0-100 (ConvertPlayer_Bar 0x285380 / 100); recomputed by pwkTeamType_FitCalc "
     "0x270b58 from the policy point and the manager's, so move the policy point instead"),
    ("styles_learned", 0x290, "<B", None,
     "how many of the style path at +0x27c are learned (ConvertPlayer_PlayStyle 0x285238)"),
    ("style_progress", 0x292, "<H", None, "towards the next style (pwkPlayStyle_GetExp)"),
    ("salary", 0x218, "<I", None, "annual salary / 100, stored money unit (pwkTeam_ArrivePlayer)"),
    ("contract_years", 0x21d, "<B", None, "years remaining (pwkMoney_*, CheckRentalMoveEnable)"),
)
# Staff, block 1. PlMinfo (0xbc bytes) and PlSinfo (0x94) are 4 bytes and
# then a copy of the PlMbase / PlSbase (pbdata.py's struct offsets, + 4).
# (role, offset, count, kind): the manager is PlTeamData +0x4854
# (pwkTeam_GetCoachManager 0x26cdc8), the youth manager YteamData (+0x4f00,
# pwkTeam_GetYteamData) +0x3f00 (pwkTeam_GetYManager 0x26bdd8), coaches
# pwkTeam_GetCoaches (0x26a7b8), scouts pwkTeam_GetScouts (0x26d098).
STAFF = (("manager", TEAM_OFF + 0x4854, 1, "M"), ("youth manager", 0x8e00, 1, "M"),
         ("coach", 0x9148, 4, "M"), ("scout", 0x8f8c, 3, "S"))
# kind: (size, id offset (-1 = empty, plMinfo/plSinfo_CloseContract 0x216ef0/0x218a10),
# contract years (empirical), salary / 100 (empirical, last word),
# job (PlMinfo +0xa0), abilities offset, ability count)
STAFF_KIND = {"M": (0xbc, 0x9c, 0x9e, 0xb8, 0xa0, 4 + 0x66, 48),
              "S": (0x94, 0x60, 0x62, 0x90, None, 4 + 0x2d, 45)}
# Play styles: +0x278 the current one, +0x27c five u32 (the style path),
# +0x290 how many of them are learned. ConvertPlayer_PlayStyle (0x285238)
# draws the current style and the learned ones, skipping repeats and 0;
# the tactics Playing Style menu offers the learned ones. Names: message
# category 100001, 150 + style (empirical, matches the screens).
STYLE_PATH, STYLE_PATH_LEN = 0x27c, 5
STYLES = ("none", "Centre Forward", "Moving", "Postplayer", "Dash out", "Second Striker",
          "Wing", "Play maker", "Shadow striker", "Attacker", "Dynamo", "Man marker",
          "Covering", "Centre MF", "Winger", "Threaten to cut in", "Full back", "Sweeper",
          "Defensive Sweeper", "Stopper", "CB", "GK", "Attacking GK")
# Block 1 +0xec90 + slot * 0x11e is what pwkTeam_GetPlayerStats (0x265810)
# indexes. The rows start 2 bytes before it: four tables of five
# competitions, 14 bytes a row, then 6 bytes not traced.
STATS_OFF, STATS_SIZE = 0xec8e, 0x11e
# The youth team: pwkTeam_GetYteamData (0x270c18) returns block 1 +0x4f00;
# pwkTeamType_FitCalc (0x270b58) walks its PlPinfo up to +0x3f00, where the
# youth manager is (pwkTeam_GetYManager): 24 slots.
YOUTH_OFF, YOUTH_SLOTS = 0x4f00, 0x3f00 // PINFO_SIZE
STATS_TABLES = ("table 1 (unknown)", "season", "table 3 (last season?)", "career")
COMPETITIONS = ("pre-season", "domestic league", "overseas league", "Euro", "international")
STATS_ROW = "<6H2B"     # goals, assists, games, games2, mom, points x 100, red, yellow
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
        """(season, turn of season 0-95, month 1-12, turn of month 0-7).
        The year is the season's first (2019 for 2019-20, January to June
        too): plMisc_PlDate2TotalTurn (0x214d08) only counts upwards that
        way. A turn is half a week: week = turn of month // 2 + 1, then
        midweek (even) or weekend (odd); see plMisc_SetTurn2Date."""
        o = self.at(0, DATE_OFF)
        year, turn, month = struct.unpack_from("<HBB", self.blocks, o)
        return year, turn, month, struct.unpack_from("<I", self.blocks, o + 4)[0]

    def squad(self):
        """[(slot label, offset of the PlPinfo in blocks)] for filled slots:
        "0"-"24" for the squad, "y0"-"y23" for the youth team."""
        out = []
        for prefix, off, count in (("", TEAM_OFF + SQUAD_OFF, SQUAD_SLOTS),
                                   ("y", YOUTH_OFF, YOUTH_SLOTS)):
            base = self.at(1, off)
            for i in range(count):
                o = base + i * PINFO_SIZE
                if struct.unpack_from("<h", self.blocks, o)[0] >= 0:
                    out.append(("%s%d" % (prefix, i), o))
        return out

    def pinfo(self, o):
        b = self.blocks
        name = b[o + PINFO_NAME:o + PINFO_NAME + NAME_LEN].split(b"\0")[0].decode("cp850")
        abil = [struct.unpack_from("<3H", b, o + ABIL_OFF + 6 * k) for k in range(ABIL_COUNT)]
        p = {"id": struct.unpack_from("<h", b, o)[0], "name": name,
             "pos": b[o + PINFO_POS], "age": b[o + PINFO_AGE], "abil": abil}
        for fname, off, fmt, _, _ in PINFO_FIELDS:
            p[fname] = struct.unpack_from(fmt, b, o + off)[0]
        return p

    def pbase_copy(self, o):
        """{field: value} from the PlPbase copy, as pbdata.py names them."""
        import pbdata
        b, base, out = self.blocks, o + PBASE_COPY, {}
        for fname, off, bits, count, _ in pbdata.PLAYER_FIELDS:
            if off >= PBASE_COPY_SIZE:
                continue
            size = 2 if bits > 8 else 1
            vals = [int.from_bytes(b[base + off + size * i:base + off + size * (i + 1)], "little")
                    for i in range(count)]
            out[fname] = vals if count > 1 else vals[0]
        return out

    def staff(self):
        """[(role, index, dict)] for every filled staff slot."""
        b, out = self.blocks, []
        for role, off, count, kind in STAFF:
            size, id_off, con_off, sal_off, job_off, ab_off, ab_n = STAFF_KIND[kind]
            for i in range(count):
                o = self.at(1, off) + i * size
                sid = struct.unpack_from("<h", b, o + id_off)[0]
                if sid < 0:
                    continue
                out.append((role, i, {
                    "id": sid, "offset": o,
                    "name": b[o + 4:o + 4 + NAME_LEN].split(b"\0")[0].decode("cp850"),
                    "contract_years": b[o + con_off],
                    "salary": struct.unpack_from("<I", b, o + sal_off)[0],
                    "job": struct.unpack_from("<I", b, o + job_off)[0] if job_off else None,
                    "abil": list(b[o + ab_off:o + ab_off + ab_n])}))
        return out

    def stats(self, slot):
        """{table: [(goals, assists, games, games2, mom, points x 100, red,
        yellow) per competition]} for a squad slot."""
        base = self.at(1, STATS_OFF) + slot * STATS_SIZE
        return {name: [struct.unpack_from(STATS_ROW, self.blocks, base + 70 * t + 14 * c)
                       for c in range(len(COMPETITIONS))]
                for t, name in enumerate(STATS_TABLES)}

    def set_field(self, o, fname, value):
        for name, off, fmt, rng, _ in PINFO_FIELDS:
            if name == fname:
                if rng is None:
                    raise ValueError("%s is read-only (its meaning isn't pinned down)" % fname)
                if not rng[0] <= value <= rng[1]:
                    raise ValueError("%s must be %d-%d" % (fname, rng[0], rng[1]))
                struct.pack_into(fmt, self.blocks, o + off, value)
                return
        raise ValueError("unknown field %r" % fname)

    def set_ability(self, o, k, level):
        """Set ability k to `level` (0-99): its experience becomes
        plMisc_AbilLv2Exp(level, 50), halfway into the level (a value on a
        threshold reads back one level lower). The growth limit and the cap
        are raised to match if they were lower: pwkGUtl_AddExp (0x246028)
        clamps experience to the limit on every gain, so a value above it
        would fall back at the next training."""
        if not 0 <= level <= 99:
            raise ValueError("level must be 0-99")
        t = self.exp
        exp = t[level] + (t[level + 1] - t[level]) * 50 // 100
        a = o + ABIL_OFF + 6 * k
        cur, limit, cap = struct.unpack_from("<3H", self.blocks, a)
        struct.pack_into("<3H", self.blocks, a, exp, max(limit, exp), max(cap, exp))

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
    print("  date   %d-%d Week %d %s %s. (turn %d of the season)" % (
        year, year + 1, week // 2 + 1, ("Midweek", "Weekend")[week & 1], MONTHS[month - 1], turn))
    print("  money  %d" % s.money)
    print("  squad (youth team slots start with y)")
    for slot, o in s.squad():
        p = s.pinfo(o)
        lv = [exp2lv(s.exp, a[0]) for a in p["abil"]]
        print("    %3s  id %5d  %-18s %-5s age %2d  mean ability %d" % (
            slot, p["id"], p["name"], pbdata.position_name(p["pos"]), p["age"],
            round(sum(lv) / len(lv))))


def cmd_player(game, path, slot):
    s = Save(game, path)
    hit = [o for i, o in s.squad() if i == slot]
    if not hit:
        raise SystemExit("squad slot %s is empty (see `show`)" % slot)
    import pbdata
    o = hit[0]
    p, db = s.pinfo(o), s.pbase_copy(o)
    print("%s: slot %s, id %d, %s" % (s.path, slot, p["id"], p["name"]))
    print("  position %s, age %d, shirt %d, %d cm, %d kg, %s foot, nation %d, team %d" % (
        pbdata.position_name(p["position"]), p["age"], db["shirt"], db["height"], db["weight"],
        "right" if db["leg"] & 1 else "left", db["nation"], p["team"]))
    print("  fatigue %d/1000, condition %d%%, motivation %d%%, team fit %d%%, form %d/1000, "
          "power %d/1000" % (p["fatigue"], p["condition"] * 100 // 65535,
                             p["motivation"] * 100 // 65535, p["team_fit"], p["form"], p["power"]))
    print("  injury %d, %d days; captain exp %d, keyman exp %d; play style %d; status %d" % (
        p["injury"], p["injury_days"], p["captain_exp"], p["keyman_exp"], p["play_style"],
        p["status"]))
    path = struct.unpack_from("<%dI" % STYLE_PATH_LEN, s.blocks, o + STYLE_PATH)
    name = lambda x: STYLES[x] if x < len(STYLES) else str(x)
    learned = [name(x) for x in path[:p["styles_learned"]] if x]
    later = [name(x) for x in path[p["styles_learned"]:] if x]
    print("  style %s; learned: %s; still to learn: %s (progress %d)" % (
        name(p["play_style"]), ", ".join(learned) or "-", ", ".join(later) or "-",
        p["style_progress"]))
    print("  skills: %s" % (", ".join(pbdata.skill_names(db["skills"])) or "none"))
    print("  policy type %d: %d%% towards counter (vs possession), %d%% towards organisation "
          "(vs individual)" % (p["policy_type"], (p["policy_counter"] + 1) * 100 // 65536,
                               (p["policy_organisation"] + 1) * 100 // 65536))
    print("  contract %d year%s left, salary %d a year (stored unit; GBP %d)" % (
        p["contract_years"], "" if p["contract_years"] == 1 else "s", p["salary"] * 100,
        p["salary"] * 100 // 6))
    for table, rows in (s.stats(int(slot)) if slot.isdigit() else {}).items():
        if not any(r[2] for r in rows):
            continue
        print("  %s: games/goals/assists/mom/yellow/red/points" % table)
        for comp, (gol, ast, games, games2, mom, pnt, red, ylw) in zip(COMPETITIONS, rows):
            if games:
                print("    %-16s %3d %3d %3d %3d %3d %3d  %.2f   (second count %d)" % (
                    comp, games, gol, ast, mom, ylw, red, pnt / 100, games2))
    lv = [exp2lv(s.exp, a[0]) for a in p["abil"]]
    print("  bars    " + "  ".join("%s %d" % b for b in pbdata.bars(lv, p["position"] == 0)))
    print("  database copy: age %d at the start, rank %d, positions %s, skills %#06x" % (
        db["age"], db["rank"], "/".join(pbdata.position_name(x) for x in db["position"]),
        db["skills"]))
    print("  ability  level  limit  cap   (exp, limit exp, cap exp)")
    for k, (cur, mid, cap) in enumerate(p["abil"]):
        print("  %7d  %5d  %5d  %3d   (%d, %d, %d)" % (k, lv[k], exp2lv(s.exp, mid), exp2lv(s.exp, cap), cur, mid, cap))


def cmd_staff(game, path):
    import pbdata
    s = Save(game, path)
    print(s.path)
    for role, i, st in s.staff():
        print("  %-13s %d  id %5d  %-18s job %-4s %d year%s left, GBP %d a year" % (
            role, i, st["id"], st["name"], "-" if st["job"] is None else st["job"],
            st["contract_years"], "" if st["contract_years"] == 1 else "s",
            st["salary"] * 100 // 6))
        if st["job"] is None:
            bars = pbdata.average_bars(st["abil"], pbdata.SCOUT_BARS)
        else:
            bars = pbdata.staff_bars(st["abil"], pbdata.JOB_ROLE.get(st["job"], "manager"))
        print("      " + "  ".join("%s %d" % b for b in bars))


def cmd_set(game, path, out, assigns):
    """money=N; for a squad player slot:ability=level, slot:all=level, or
    slot:field=value for the settable PINFO_FIELDS (fatigue, condition, ...)."""
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
        if slot not in squad or not which:
            raise SystemExit("%r: use money=N, <slot>:<ability>=level, <slot>:all=level or "
                             "<slot>:<field>=value (slot = a filled squad slot, see `show`)" % a)
        o = squad[slot]
        if not which.isdigit() and which != "all":
            try:
                s.set_field(o, which, int(val, 0))
            except ValueError as e:
                raise SystemExit("%s: %s" % (a, e))
            continue
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


def cmd_fields(game, rounds):
    """Record the field list afresh, check it against the game code, cache it."""
    fields = Fields.trace(game)
    print("recorded %d fields, %d bits" % (len(fields), fields.bits))
    widths = {}
    for n in fields.n:
        widths[n] = widths.get(n, 0) + 1
    print("  bits per field: " + ", ".join("%d x%d" % (n, c) for n, c in sorted(widths.items())))
    print("  signed fields: %d" % sum(fields.signed))
    covered = sum(fields.width)
    print("  bytes stored: %d of %d in the blocks" % (covered, game.offsets[-1]))
    fields.check(game, rounds)
    print("matches the game code on %d random stream%s and block set%s" % (
        rounds, "" if rounds == 1 else "s", "" if rounds == 1 else "s"))
    fields.save(Fields.path(game))


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
    elif cmd == "staff" and len(args) == 1:
        cmd_staff(game, args[0])
    elif cmd == "player" and len(args) == 2:
        cmd_player(game, args[0], args[1])
    elif cmd == "set" and len(args) >= 3:
        cmd_set(game, args[0], args[1], args[2:])
    elif cmd == "fields" and len(args) <= 1:
        cmd_fields(game, int(args[0]) if args else 1)
    elif cmd == "blocks" and not args:
        cmd_blocks(game)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
