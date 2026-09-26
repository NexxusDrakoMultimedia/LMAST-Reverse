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
    python sounddat.py songs   <file | dir> ...               # list the songs (sequences) in DTPK banks
    python sounddat.py midi    <file> <outdir>                # write each song as a MIDI file
    python sounddat.py tbl     <file.TBL> [<FNAMExx>]         # dump a clip table, optionally with clip names
    python sounddat.py fname   <FNAMExx> [id ...]             # list clip names (FNAMEEN, BCFNAME, ...)

<FNAMExx> is the .DAT/.TOC pair without extension, e.g. DAT/GAME/FNAMEEN.

Songs are Sega SoundFactory sequences, played by ISO/DRIVERS/SNDFI.IRX:
MIDI-like streams with running status, where the last data byte's top bit
means "more at this moment" and otherwise a 1-3 byte delay follows (1 tick
= 1 ms by default). `midi` writes them with General MIDI instruments, not
the bank's own; loop points become 'loopStart'/'loopEnd' markers.
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
        self.ptrs = ptrs
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


# --- songs (sequences) ---------------------------------------------------------
#
# The sequencer is in ISO/DRIVERS/SNDFI.IRX ("SNDF Driver Ver 2.27a"), the
# PS2 port of Sega's SoundFactory driver; addresses below are its .text.
# TBLD pointer [3] starts the song area (0 = none): u32 sub-area count - 1,
# then per sub-area a u32 {u16 offset, u8 id, u8 kind}. A sub-area is u32
# entry count - 1, then u32 entry offsets; offsets are from the area start.
# A song is a u32 header (0x00010040 in every song), then records {u24 arg,
# u8 type} read by 0xfe9c.

# Sub-area kinds: 0xa8 songs (MAP banks), 0xa9 sound effects (EFFECTS,
# SYS_SE, ...), whose entries are short layer lists such as
# "c0 df 00 50 80 df 01 50 80 ff" rather than songs; not decoded.
AREA_SONGS, AREA_EFFECTS = 0xA8, 0xA9
SONG_STREAM = 0x00      # play the stream at song + arg, then carry on with the records
SONG_COMMAND = 0x80     # send driver command (arg << 8) | 0x80 (0xff1c)
SONG_GOTO = 0x90        # continue reading records at song + arg (the loop)
# Data bytes after each status (0x10064-0x10160). The last data byte's top
# bit means "another event at the same time"; otherwise a delay follows.
SONG_DATA_BYTES = {0x8: 1, 0x9: 2, 0xa: 2, 0xb: 2, 0xc: 1, 0xd: 1, 0xe: 1, 0xf: 2}
SONG_END = 0xff
# Timing (0xa838, 0xf5bc, 0xba80-0xbaf0): the driver runs 200 times a
# second (IOP timer, sysclock / 256 / 720) and takes 0x500 / 256 = 5 ticks
# off each song's countdown per run: 1 tick = 1 ms unless a song changes it.
TICKS_PER_SECOND = 1000


def song_areas(bank):
    """[(kind, id, [entry positions])] for the bank's sub-areas; [] if the
    bank has no song area."""
    d, pos = bank.d, bank.pos
    if not bank.ptrs[3]:
        return []
    area = pos + bank.ptrs[3]
    out = []
    for j in range(struct.unpack_from("<I", d, area)[0] + 1):
        w = struct.unpack_from("<I", d, area + 4 + 4 * j)[0]
        sub = area + (w & 0xFFFF)
        n = struct.unpack_from("<I", d, sub)[0] + 1
        if n > 0x1000:
            raise ValueError("sub-area %d claims %d entries" % (j, n))
        offs = struct.unpack_from("<%dI" % n, d, sub + 4)
        out.append((w >> 24, (w >> 16) & 0xFF, [area + o for o in offs]))
    return out


def song_offsets(bank):
    return [p for kind, _, offs in song_areas(bank) if kind == AREA_SONGS for p in offs]


def song_records(d, song):
    """[(offset in song, type, arg)] from +4 up to and including the goto
    (or a play-and-stop record)."""
    out, p = [], song + 4
    while len(out) < 64:
        w = struct.unpack_from("<I", d, p)[0]
        typ, arg = w >> 24, w & 0xFFFFFF
        out.append((p - song, typ, arg))
        p += 4
        if typ == SONG_GOTO or typ not in (SONG_STREAM, SONG_COMMAND):
            return out
    raise ValueError("song at %#x: no goto within 64 records" % song)


def song_stream(d, pos):
    """[(delay before, status, data)] of a note stream, as 0xfdec-0x10244
    reads it, up to the 0xFF end byte. Returns (events, trailing delay)."""
    ev, status, delay = [], None, 0
    while True:
        if pos >= len(d):
            raise ValueError("stream runs past the end of the file")
        b = d[pos]
        if b == SONG_END:
            return ev, delay
        if b & 0x80:
            status = b
            pos += 1
        if status is None:
            raise ValueError("data byte %#x before any status at %#x" % (b, pos))
        n = SONG_DATA_BYTES[status >> 4]
        data = d[pos:pos + n]
        pos += n
        ev.append((delay, status, [x & 0x7F for x in data]))
        delay = 0
        if not data[-1] & 0x80:
            # Delay: 1-3 bytes, 7 bits each, top bit = another byte (0x101c0).
            for _ in range(3):
                x = d[pos]
                pos += 1
                delay = (delay << 7) | (x & 0x7F)
                if not x & 0x80:
                    break


class Song:
    """One song: its streams in play order, and which one the loop returns to."""

    def __init__(self, d, song):
        self.pos = song
        self.records = song_records(d, song)
        self.streams, self.commands = [], []
        self.loop_stream = None
        starts = {}
        for off, typ, arg in self.records:
            if typ == SONG_COMMAND:
                self.commands.append(arg)
            elif typ == SONG_GOTO:
                self.loop_stream = starts.get(arg)
            else:
                starts[off] = len(self.streams)
                self.streams.append(song_stream(d, song + arg))
        self.ticks = [sum(e[0] for e in ev) + tail for ev, tail in self.streams]

    def channels(self):
        return sorted({st & 15 for ev, _ in self.streams for _, st, _ in ev})


def midi_vlq(v):
    out = [v & 0x7F]
    v >>= 7
    while v:
        out.insert(0, 0x80 | (v & 0x7F))
        v >>= 7
    return bytes(out)


def song_midi(song):
    """A type-0 MIDI file: 500 ticks per quarter at 500,000 us per quarter,
    so one MIDI tick is one driver tick. The looped part is marked with
    'loopStart' / 'loopEnd' marker events."""
    def marker(text):
        return b"\xff\x06" + midi_vlq(len(text)) + text

    body = bytearray(b"\x00\xff\x51\x03" + (500000).to_bytes(3, "big"))
    pending = 0
    for k, (events, tail) in enumerate(song.streams):
        if k == song.loop_stream:
            body += midi_vlq(pending) + marker(b"loopStart")
            pending = 0
        for delay, status, data in events:
            pending += delay
            hi = status >> 4
            if hi == 0x8:
                msg = bytes([status, data[0], 64])      # the driver's note-off has no velocity
            elif hi == 0xE:
                msg = bytes([status, 0, data[0]])       # 7-bit bend: the MSB
            elif hi == 0xF:
                continue
            else:
                msg = bytes([status] + data)
            body += midi_vlq(pending) + msg
            pending = 0
        pending += tail
    if song.loop_stream is not None:
        body += midi_vlq(pending) + marker(b"loopEnd")
        pending = 0
    body += midi_vlq(pending) + b"\xff\x2f\x00"
    return (b"MThd" + struct.pack(">IHHH", 6, 0, 1, 500) +
            b"MTrk" + struct.pack(">I", len(body)) + bytes(body))


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


def dat_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for n in sorted(os.listdir(p)):
                if n.upper().endswith((".DAT", ".PAC")):
                    yield os.path.join(p, n).replace("\\", "/")
        else:
            yield p


def cmd_songs(paths):
    for path in dat_files(paths):
        with open(path, "rb") as f:
            d = f.read()
        for i, bank in enumerate(find_banks(d)):
            try:
                areas = song_areas(bank)
            except (ValueError, struct.error) as e:
                print("%s bank %d  !! %s" % (path, i, e))
                continue
            if not areas:
                print("%s bank %d: no song area" % (path, i))
            offs = []
            for kind, aid, entries in areas:
                if kind == AREA_EFFECTS:
                    print("%s bank %d: %d sound effects (not songs)" % (path, i, len(entries)))
                elif kind == AREA_SONGS:
                    offs += entries
                else:
                    print("%s bank %d  !! sub-area kind %#x (expected 0xa8 or 0xa9)" % (path, i, kind))
            for k, pos in enumerate(offs):
                try:
                    s = Song(d, pos)
                except (ValueError, struct.error, KeyError) as e:
                    print("%s bank %d song %d  !! %s" % (path, i, k, e))
                    continue
                events = sum(len(ev) for ev, _ in s.streams)
                loop = ("loops from stream %d" % s.loop_stream if s.loop_stream is not None
                        else "no loop")
                print("%s bank %d song %d: %d stream%s %s ticks (%.1f s), %d events, "
                      "channels %s, %s, commands %s" % (
                          path, i, k, len(s.streams), "" if len(s.streams) == 1 else "s",
                          "+".join(map(str, s.ticks)), sum(s.ticks) / TICKS_PER_SECOND, events,
                          ",".join(map(str, s.channels())), loop,
                          " ".join("%06x" % c for c in s.commands)))


def cmd_midi(path, outdir):
    with open(path, "rb") as f:
        d = f.read()
    os.makedirs(outdir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(path))[0]
    for i, bank in enumerate(find_banks(d)):
        for k, pos in enumerate(song_offsets(bank)):
            s = Song(d, pos)
            out = os.path.join(outdir, "%s_%d_song%d.mid" % (stem, i, k))
            with open(out, "wb") as f:
                f.write(song_midi(s))
            print("%s  %.1f s" % (out, sum(s.ticks) / TICKS_PER_SECOND))


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
    elif cmd == "songs":
        cmd_songs(args)
    elif cmd == "midi" and len(args) == 2:
        cmd_midi(args[0], args[1])
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
