"""Reader for the CRI AFS archives in ISO/AUDIO and the ADX audio they hold,
for Let's Make a Soccer Team! (PS2).

AFS (little-endian):
  +0x0  "AFS\\0"
  +0x4  u32 entry count n
  +0x8  n x {u32 offset, u32 size}      entries start on 0x800 boundaries
  then  {u32 offset, u32 size} of the name table
  names n x 48 bytes: char name[32], 6 x u16 date (year, month, day, hour,
        minute, second), u32 (the previous entry's size: an AFS quirk)

Every entry on this disc is CRI ADX (big-endian header):
  +0x00 u16 0x8000        +0x02 u16 header size - 4 (data starts after it;
  +0x04 u8 encoding (3)         "(c)CRI" ends just before)
  +0x05 u8 frame size (18) +0x06 u8 bits per sample (4)
  +0x07 u8 channels       +0x08 u32 sample rate   +0x0c u32 samples
  +0x10 u16 high-pass cutoff (Hz)  +0x12 u8 version (4)  +0x13 u8 flags (0)
  version 4: +0x24 u32 loop flag, +0x28 loop start sample,
             +0x2c loop start byte, +0x30 loop end sample, +0x34 end byte
             (only when the header is long enough; commentary headers
             end at 0x22 and hold no loop)
Frames are 18 bytes per channel, channels interleaved frame by frame: a
u16 scale, then 32 signed 4-bit samples, high nibble first. Each sample
is nibble * (scale + 1) + (c1 * s[-1] + c2 * s[-2]) >> 12, with c1 and c2
from the cutoff and rate (the standard ADX predictor, as vgmstream).

See DOC/AUDIO_DIR.md.

Usage:
    python afs.py info <file.AFS | dir> ...           # check every entry
    python afs.py list <file.AFS>                     # names, format, length, loop
    python afs.py wav  <file.AFS> <outdir> [entry ...]  # decode to WAV (entry: index or name)

WAVs get a 'smpl' chunk with the loop points when the ADX loops, so
players and editors that read it can loop them as the game does.
"""
import math
import os
import struct
import sys

AFS_MAGIC = b"AFS\0"
ADX_MAGIC = 0x8000
NAME_SIZE = 48


class Entry:
    def __init__(self, index, offset, size, name, date):
        self.index, self.offset, self.size, self.name, self.date = index, offset, size, name, date


class Afs:
    def __init__(self, path):
        self.path = path
        self.file_size = os.path.getsize(path)
        with open(path, "rb") as f:
            head = f.read(8)
            if head[:4] != AFS_MAGIC:
                raise ValueError("%s: not an AFS archive" % path)
            n = struct.unpack_from("<I", head, 4)[0]
            table = f.read(8 * n + 8)
            if len(table) < 8 * n + 8:
                raise ValueError("%s: table runs past the end" % path)
            spans = [struct.unpack_from("<II", table, 8 * i) for i in range(n)]
            name_off, name_size = struct.unpack_from("<II", table, 8 * n)
            names = [None] * n
            dates = [None] * n
            if name_off and name_size >= NAME_SIZE * n:
                f.seek(name_off)
                raw = f.read(NAME_SIZE * n)
                for i in range(n):
                    r = raw[NAME_SIZE * i:NAME_SIZE * (i + 1)]
                    names[i] = r[:32].split(b"\0")[0].decode("latin1")
                    dates[i] = struct.unpack_from("<6H", r, 32)
        self.name_span = (name_off, name_size)
        self.entries = [Entry(i, o, s, names[i] or "%05d" % i, dates[i])
                        for i, (o, s) in enumerate(spans)]

    def read(self, e):
        with open(self.path, "rb") as f:
            f.seek(e.offset)
            return f.read(e.size)

    def find(self, key):
        if key.isdigit():
            return self.entries[int(key)]
        hits = [e for e in self.entries if e.name.lower() == key.lower()]
        if not hits:
            raise ValueError("%s: no entry %r" % (self.path, key))
        return hits[0]


class Adx:
    def __init__(self, data):
        if len(data) < 0x14 or struct.unpack_from(">H", data)[0] != ADX_MAGIC:
            raise ValueError("not ADX")
        (self.data_off, self.encoding, self.frame, self.bits, self.channels,
         self.rate, self.samples, self.cutoff, self.version, self.flags) = struct.unpack_from(
            ">HBBBBIIHBB", data, 2)
        self.data_off += 4
        self.loop = None
        # The loop fields exist only if the header reaches past them: short
        # headers (commentary, data at 0x28) have "(c)CRI" there instead.
        header_end = self.data_off - 6
        if self.version == 4 and header_end >= 0x38 and len(data) >= 0x38:
            flag, start, _, end, _ = struct.unpack_from(">IIIII", data, 0x24)
            if flag:
                self.loop = (start, end)
        elif self.version == 3 and header_end >= 0x2c and len(data) >= 0x2c:
            flag, start, _, end, _ = struct.unpack_from(">IIIII", data, 0x18)
            if flag:
                self.loop = (start, end)
        self.raw = data

    def problems(self):
        p = []
        if self.encoding != 3:
            p.append("encoding %d (only 3 is decoded)" % self.encoding)
        if self.frame != 18 or self.bits != 4:
            p.append("frame %d, %d bits" % (self.frame, self.bits))
        if self.flags:
            p.append("flags %#x (encrypted?)" % self.flags)
        if self.raw[self.data_off - 6:self.data_off] != b"(c)CRI":
            p.append("no (c)CRI before the data")
        need = self.data_off + -(-self.samples // 32) * self.frame * self.channels
        if need > len(self.raw):
            p.append("%d samples need %d bytes, the entry has %d" % (self.samples, need, len(self.raw)))
        return p

    def coefs(self):
        z = math.cos(2.0 * math.pi * self.cutoff / self.rate)
        a = math.sqrt(2.0) - z
        b = math.sqrt(2.0) - 1.0
        c = (a - math.sqrt((a + b) * (a - b))) / b
        return int(math.floor(c * 8192)), int(math.floor(c * c * -4096))

    def decode(self):
        """Interleaved 16-bit PCM as bytes (little-endian)."""
        c1, c2 = self.coefs()
        ch, fs, raw = self.channels, self.frame, self.raw
        frames = -(-self.samples // 32)
        out = [[] for _ in range(ch)]
        hist = [[0, 0] for _ in range(ch)]
        pos = self.data_off
        for _ in range(frames):
            for c in range(ch):
                scale = ((raw[pos] << 8) | raw[pos + 1]) + 1
                h1, h2 = hist[c]
                o = out[c]
                for b in raw[pos + 2:pos + fs]:
                    for nib in (b >> 4, b & 15):
                        s = (nib - 16 if nib & 8 else nib) * scale + ((c1 * h1) >> 12) + ((c2 * h2) >> 12)
                        if s > 32767:
                            s = 32767
                        elif s < -32768:
                            s = -32768
                        o.append(s)
                        h2, h1 = h1, s
                hist[c] = [h1, h2]
                pos += fs
        n = self.samples
        if ch == 1:
            pcm = out[0][:n]
        else:
            pcm = [v for frame in zip(*(o[:n] for o in out)) for v in frame]
        return struct.pack("<%dh" % len(pcm), *pcm)


def write_wav(path, pcm, channels, rate, loop=None):
    fmt = struct.pack("<HHIIHH", 1, channels, rate, rate * channels * 2, channels * 2, 16)
    chunks = [b"fmt " + struct.pack("<I", len(fmt)) + fmt,
              b"data" + struct.pack("<I", len(pcm)) + pcm + (b"\0" if len(pcm) & 1 else b"")]
    if loop:
        # smpl: manufacturer, product, period (ns), MIDI note, fraction, SMPTE
        # format/offset, 1 loop, no extra data; then {id, type 0, start, end
        # (inclusive), fraction, play count 0 = forever}.
        body = struct.pack("<9I", 0, 0, 1000000000 // rate, 60, 0, 0, 0, 1, 0)
        body += struct.pack("<6I", 0, 0, loop[0], max(loop[0], loop[1] - 1), 0, 0)
        chunks.append(b"smpl" + struct.pack("<I", len(body)) + body)
    riff = b"WAVE" + b"".join(chunks)
    with open(path, "wb") as f:
        f.write(b"RIFF" + struct.pack("<I", len(riff)) + riff)


def read_head(f, e):
    """An entry's ADX header, however long (some pad it past 0x800)."""
    f.seek(e.offset)
    head = f.read(min(e.size, 4))
    if len(head) == 4:
        f.seek(e.offset)
        head = f.read(min(e.size, struct.unpack_from(">H", head, 2)[0] + 4 + 0x40))
    return head


def secs(adx):
    return adx.samples / adx.rate


# --- commands ----------------------------------------------------------------

def afs_files(paths):
    for p in paths:
        if os.path.isdir(p):
            for n in sorted(os.listdir(p)):
                if n.upper().endswith(".AFS"):
                    yield os.path.join(p, n)
        else:
            yield p


def cmd_info(paths):
    for p in afs_files(paths):
        try:
            a = Afs(p)
        except (ValueError, struct.error, OSError) as e:
            print("%s  !! %s" % (p, e))
            continue
        probs, kinds, total = [], {}, 0.0
        end = 0
        for e in a.entries:
            if e.offset % 0x800:
                probs.append("entry %d at %#x is not 0x800-aligned" % (e.index, e.offset))
            if e.offset < end:
                probs.append("entry %d overlaps the one before" % e.index)
            if e.offset + e.size > a.file_size:
                probs.append("entry %d runs past the end" % e.index)
            end = e.offset + e.size
            try:
                with open(p, "rb") as f:
                    head = read_head(f, e)
                adx = Adx(head)
                ep = [x for x in adx.problems() if not x.startswith("%d samples" % adx.samples)]
                if adx.data_off + -(-adx.samples // 32) * adx.frame * adx.channels > e.size:
                    ep.append("samples need more bytes than the entry has")
                if ep:
                    probs.append("entry %d (%s): %s" % (e.index, e.name, "; ".join(ep)))
                key = "%d ch %d Hz" % (adx.channels, adx.rate)
                kinds[key] = kinds.get(key, 0) + 1
                total += secs(adx)
            except (ValueError, struct.error) as err:
                probs.append("entry %d (%s): %s" % (e.index, e.name, err))
        named = sum(1 for e in a.entries if e.date)
        print("%s: %d entries, %d named, ADX %s, %.0f s of audio%s" % (
            p, len(a.entries), named,
            ", ".join("%s x%d" % kv for kv in sorted(kinds.items())), total,
            ""))
        for pr in probs[:20]:
            print("  !! %s" % pr)
        if len(probs) > 20:
            print("  !! ... %d more" % (len(probs) - 20))


def cmd_list(path):
    a = Afs(path)
    for e in a.entries:
        with open(path, "rb") as f:
            head = read_head(f, e)
        try:
            adx = Adx(head)
            desc = "%d ch %5d Hz %7.1f s" % (adx.channels, adx.rate, secs(adx))
            if adx.loop:
                desc += "  loop %.2f-%.2f s" % (adx.loop[0] / adx.rate, adx.loop[1] / adx.rate)
        except ValueError as err:
            desc = "(%s)" % err
        date = "%04d-%02d-%02d" % e.date[:3] if e.date else ""
        print("%5d  %-24s %10d  %s  %s" % (e.index, e.name, e.size, date, desc))


def cmd_wav(path, outdir, keys):
    a = Afs(path)
    entries = [a.find(k) for k in keys] if keys else a.entries
    os.makedirs(outdir, exist_ok=True)
    for e in entries:
        adx = Adx(a.read(e))
        for pr in adx.problems():
            raise SystemExit("%s: %s" % (e.name, pr))
        out = os.path.join(outdir, os.path.splitext(e.name)[0] + ".wav")
        write_wav(out, adx.decode(), adx.channels, adx.rate, adx.loop)
        print("%s  %d ch %d Hz %.1f s%s" % (out, adx.channels, adx.rate, secs(adx),
                                           "  (loops)" if adx.loop else ""))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args)
    elif cmd == "list" and len(args) == 1:
        cmd_list(args[0])
    elif cmd == "wav" and len(args) >= 2:
        cmd_wav(args[0], args[1], args[2:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
