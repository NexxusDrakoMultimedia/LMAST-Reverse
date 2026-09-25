"""Reader for GAME/SOUNDDAT.PAC and the commentary / sound-bank formats it
holds, for Let's Make a Soccer Team! (PS2).

SOUNDDAT.PAC has no directory. It is 12 fixed-size commentary slots, then a
run of .TBL clip tables, then 40 ps2_DTPK sound banks. Each piece is
self-describing enough to split the pack without the loose copies in
DAT/GAME. See DOC/GAME_DIR.md for the layouts.

Usage:
    python sounddat.py info    <SOUNDDAT.PAC>                 # layout summary
    python sounddat.py extract <SOUNDDAT.PAC> <outdir> [--wav]  # split the pack (--wav: decode samples)
    python sounddat.py dtpk    <file> [<outdir>]              # list / decode samples in any ps2_DTPK file
    python sounddat.py tbl     <file.TBL> [<FNAMExx>]         # dump a clip table, optionally with clip names
    python sounddat.py fname   <FNAMExx> [id ...]             # list clip names (FNAMEEN, BCFNAME, ...)

<FNAMExx> is the .DAT/.TOC pair without extension, e.g. DAT/GAME/FNAMEEN.
"""
import os
import struct
import sys
import wave

SLOT_SIZE = 0x1D800
SLOT_COUNT = 12
# Slot k holds language SLOT_LANGS[k // 2] with crowd table SLOT_CROWD[k % 2].
# Confirmed by matching each slot against the loose VBOX_* files.
SLOT_LANGS = ["JPN_TEST", "ENG", "FRA", "GER", "ITA", "SPA"]
SLOT_CROWD = ["KANNEUT", "KANHA"]
TBL_REGION = 0x162000

TBB_MAGIC = b"TBB1"
DTPK_MAGIC = b"ps2_DTPK"
DTPK_LOOP = 4


def align(n, a):
    return (n + a - 1) // a * a


# --- commentary slot ---------------------------------------------------------

def tbb_end(d, pos):
    """TBB1 end-of-data field (u32 @ +0x0C), relative to pos."""
    if d[pos:pos + 4] != TBB_MAGIC:
        raise ValueError("no TBB1 at %#x" % pos)
    return struct.unpack_from("<I", d, pos + 12)[0]


def split_slot(d, base):
    """Return [(kind, start, end)] for one 0x1D800 commentary slot:
    BCR (EU routebox), BCB (language vbox), BCR (crowd routebox),
    BCB (crowd vbox), BCV (vbox index, 3 bytes per BCB3 record)."""
    parts = []
    pos = base
    # BCR: TBB1 of BCR2 records plus an unexplained trailer; it runs up to
    # the next TBB1, which always starts 16-aligned after the trailer.
    for kind in ("BCR", "BCB", "BCR", "BCB"):
        if kind == "BCR":
            nxt = d.find(TBB_MAGIC, pos + align(tbb_end(d, pos), 16))
            end = nxt
        else:
            end = pos + align(tbb_end(d, pos), 16)
        parts.append((kind, pos, end))
        pos = end
    # BCV: one 3-byte record per BCB3 record in the language vbox.
    lang_bcb = parts[1][1]
    bcb3 = lang_bcb + struct.unpack_from("<I", d, lang_bcb + 0x10)[0]
    count = struct.unpack_from("<I", d, bcb3 + 0x0C)[0]
    parts.append(("BCV", pos, pos + count * 3))
    return parts


# --- TBL clip tables ---------------------------------------------------------

def tbl_parse(b, pos=0):
    """TBL: u16 BE rows, u8 cols, rows*cols u16 BE clip ids. -> (rows, cols, ids, length)."""
    rows = b[pos] << 8 | b[pos + 1]
    cols = b[pos + 2]
    n = rows * cols
    ids = struct.unpack_from(">%dH" % n, b, pos + 3)
    return rows, cols, ids, 3 + n * 2


def walk_tbls(d, start, stop):
    """Yield (offset, length, rows, cols) for the packed TBL run. Tables are
    16-aligned; some groups restart on a 0x800 boundary, so zero padding
    (rows = 0) is skipped rather than treated as the end."""
    pos = start
    while pos < stop:
        rows, cols, _, length = tbl_parse(d, pos)
        if rows == 0 or cols == 0:
            pos += 16
            continue
        yield pos, length, rows, cols
        pos = align(pos + length, 16)


# --- ps2_DTPK sound banks ----------------------------------------------------

class Dtpk:
    """ps2_DTPK bank: header, ps2_TBLD (tone tables), ps2_VAGD (PS-ADPCM)."""

    def __init__(self, d, pos=0):
        if d[pos:pos + 8] != DTPK_MAGIC:
            raise ValueError("no ps2_DTPK at %#x" % pos)
        self.d, self.pos = d, pos
        self.kind = chr(d[pos + 9])
        self.size, self.tbld_size, _, self.vag_size, self.vag_off = \
            struct.unpack_from("<5I", d, pos + 12)
        # TBLD +0x38: ten u32 pointers (bank-relative). [8] is the sample
        # table {u32 last_index, entries[16]}; [9] is where it ends.
        ptrs = struct.unpack_from("<10I", d, pos + 0x98)
        st = ptrs[8]
        n = struct.unpack_from("<I", d, pos + st)[0] + 1
        self.samples = []
        for k in range(n):
            off, _, flags, rate, size = struct.unpack_from("<IIHHI", d, pos + st + 4 + 16 * k)
            self.samples.append((off, size, rate, flags))

    def sample_data(self, k):
        off, size, _, _ = self.samples[k]
        a = self.pos + self.vag_off + off
        return self.d[a:a + size]


def find_banks(d, start=0):
    pos = d.find(DTPK_MAGIC, start)
    while pos >= 0:
        bank = Dtpk(d, pos)
        yield bank
        pos = d.find(DTPK_MAGIC, pos + bank.size)


_VAG_COEF = [(0, 0), (60, 0), (115, -52), (98, -55), (122, -60)]


def vag_decode(data):
    """PS-ADPCM (SPU2) -> list of s16 samples. Stops at the end-flag frame."""
    out = []
    s1 = s2 = 0
    for f in range(0, len(data) - 15, 16):
        pred, shift = data[f] >> 4, data[f] & 0x0F
        flags = data[f + 1]
        c1, c2 = _VAG_COEF[pred if pred < 5 else 0]
        for byte in data[f + 2:f + 16]:
            for nib in (byte & 0x0F, byte >> 4):
                if nib >= 8:
                    nib -= 16
                s = ((nib << 12) >> shift) + (s1 * c1 + s2 * c2 + 32) // 64
                s = max(-32768, min(32767, s))
                out.append(s)
                s2, s1 = s1, s
        if flags & 1:
            break
    return out


def write_wav(path, samples, rate):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(struct.pack("<%dh" % len(samples), *samples))


def dump_bank(bank, outdir, prefix=""):
    os.makedirs(outdir, exist_ok=True)
    for k, (_, size, rate, flags) in enumerate(bank.samples):
        name = "%s%02d_%dhz%s.wav" % (prefix, k, rate, "_loop" if flags & DTPK_LOOP else "")
        write_wav(os.path.join(outdir, name), vag_decode(bank.sample_data(k)), rate)


# --- FNAME clip-name tables --------------------------------------------------

def load_fname(base):
    """FNAMExx.DAT (NUL-terminated names) + .TOC (u32 offsets): index = AFS entry."""
    with open(base + ".DAT", "rb") as f:
        d = f.read()
    with open(base + ".TOC", "rb") as f:
        t = f.read()
    offs = struct.unpack("<%dI" % (len(t) // 4), t)
    return [d[o:d.index(b"\0", o)].decode("latin1") for o in offs]


# --- commands ----------------------------------------------------------------

def layout(d):
    """[(name, start, end)] for everything in SOUNDDAT.PAC."""
    items = []
    for k in range(SLOT_COUNT):
        lang, crowd = SLOT_LANGS[k // 2], SLOT_CROWD[k % 2]
        names = ["ROUTEBOX_EU.BCR", "VBOX_TABLE_%s.BCB" % lang, "ROUTEBOX_KAN.BCR",
                 "VBOX_%s.BCB" % crowd, "VBOX_TABLE_BCB.BCV"]
        for name, (_, a, b) in zip(names, split_slot(d, k * SLOT_SIZE)):
            items.append(("slot%02d_%s_%s/%s" % (k, lang, crowd, name), a, b))
    first_bank = d.find(DTPK_MAGIC, TBL_REGION)
    for i, (pos, length, _, _) in enumerate(walk_tbls(d, TBL_REGION, first_bank)):
        items.append(("tbl/%02d_%07x.TBL" % (i, pos), pos, pos + length))
    for i, bank in enumerate(find_banks(d, first_bank)):
        items.append(("dtpk/%02d_%s_%07x.DTPK" % (i, bank.kind, bank.pos), bank.pos, bank.pos + bank.size))
    return items


def cmd_info(path):
    with open(path, "rb") as f:
        d = f.read()
    items = layout(d)
    print("%s: %d bytes" % (path, len(d)))
    for k in range(SLOT_COUNT):
        parts = split_slot(d, k * SLOT_SIZE)
        used = parts[-1][2] - k * SLOT_SIZE
        print("  slot %2d @%#08x  %-8s %-7s  %s  (%#x of %#x used)" % (
            k, k * SLOT_SIZE, SLOT_LANGS[k // 2], SLOT_CROWD[k % 2],
            " ".join("%s:%#x" % (kind, b - a) for kind, a, b in parts), used, SLOT_SIZE))
    tbls = [i for i in items if i[0].startswith("tbl/")]
    print("  %d TBL clip tables @%#x-%#x" % (len(tbls), tbls[0][1], tbls[-1][2]))
    for bank in find_banks(d, TBL_REGION):
        rates = sorted(set(s[2] for s in bank.samples))
        loops = sum(1 for s in bank.samples if s[3] & DTPK_LOOP)
        print("  DTPK @%#08x %s size %#07x  %2d samples (%d looped) rates %s" % (
            bank.pos, bank.kind, bank.size, len(bank.samples), loops, rates))
    end = max(b for _, _, b in items)
    print("  end of data %#x, file %#x%s" % (
        end, len(d), "  !! %#x bytes not covered" % (len(d) - end) if end != len(d) else ""))


def cmd_extract(path, outdir, wav):
    with open(path, "rb") as f:
        d = f.read()
    items = layout(d)
    for name, a, b in items:
        out = os.path.join(outdir, name)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "wb") as f:
            f.write(d[a:b])
    n = 0
    if wav:
        for i, bank in enumerate(find_banks(d, TBL_REGION)):
            dump_bank(bank, os.path.join(outdir, "wav", "%02d_%s" % (i, bank.kind)))
            n += len(bank.samples)
    print("%d pieces -> %s%s" % (len(items), outdir, " (%d samples decoded)" % n if wav else ""))


def cmd_dtpk(path, outdir):
    with open(path, "rb") as f:
        d = f.read()
    for i, bank in enumerate(find_banks(d)):
        print("bank %d @%#x kind %s size %#x, VAGD @+%#x (%#x bytes)" % (
            i, bank.pos, bank.kind, bank.size, bank.vag_off, bank.vag_size))
        for k, (off, size, rate, flags) in enumerate(bank.samples):
            print("  %3d  off %#07x  size %#07x  %5d Hz%s" % (
                k, off, size, rate, "  loop" if flags & DTPK_LOOP else ""))
        if outdir:
            dump_bank(bank, os.path.join(outdir, "%02d_%s" % (i, bank.kind)))


def cmd_tbl(path, fname):
    with open(path, "rb") as f:
        b = f.read()
    rows, cols, ids, length = tbl_parse(b)
    names = load_fname(fname) if fname else None
    print("%s: %d rows x %d cols%s" % (path, rows, cols,
                                        "" if length == len(b) else " (file has %d extra bytes)" % (len(b) - length)))
    for r in range(rows):
        row = ids[r * cols:(r + 1) * cols]
        cells = ["%5d %-24s" % (v, names[v] if v < len(names) else "?") for v in row] if names \
            else ["%5d" % v for v in row]
        print("%5d: %s" % (r, " | ".join(cells).rstrip()))


def cmd_fname(base, ids):
    names = load_fname(base)
    for i in (map(int, ids) if ids else range(len(names))):
        print("%5d %s" % (i, names[i]))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args[0])
    elif cmd == "extract" and len(args) >= 2:
        cmd_extract(args[0], args[1], "--wav" in args[2:])
    elif cmd == "dtpk":
        cmd_dtpk(args[0], args[1] if len(args) > 1 else None)
    elif cmd == "tbl":
        cmd_tbl(args[0], args[1] if len(args) > 1 else None)
    elif cmd == "fname":
        cmd_fname(args[0], args[1:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
