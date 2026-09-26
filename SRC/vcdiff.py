"""VCDIFF (RFC 3284) patches, the format xdelta3 writes, for sharing mods
of Let's Make a Soccer Team! (PS2) as small files against the user's own
disc image. Standard library only; no xdelta3 needed.

`make` compares a source (the unmodified Redump image) with a target (the
patched image) in 8 MiB windows. Each window takes the same range of the
source as its source segment and is encoded as COPY instructions for
unchanged runs and ADD instructions for changed bytes, using the default
code table and no secondary compression, so any RFC 3284 decoder (xdelta3,
xdelta UI, DeltaPatcher, open-vcdiff) can apply it. A few changed bytes in
a 3.5 GB image make a patch of about 4 KB.

`apply` decodes any VCDIFF file without secondary compression or a custom
code table: all of the default code table, the address cache, RUN and
overlapping COPY, xdelta3's application header, and its per-window
Adler-32 (checked). See DOC/REBUILD.md.

Usage:
    python vcdiff.py make  <source> <target> <out.xdelta>
    python vcdiff.py apply <source> <patch.xdelta> <out>
    python vcdiff.py info  <patch.xdelta>
    python vcdiff.py roundtrip <source> <target>      # make + apply in memory, check the result

`make` and `apply` print SHA-1s so a patch can be published with the hash
of the image it expects and the one it produces; `make` warns if the source
isn't the Redump dump (redump.org/disc/12334).
"""
import hashlib
import io
import os
import sys
import zlib

MAGIC = b"\xd6\xc3\xc4\x00"
VCD_DECOMPRESS, VCD_CODETABLE, VCD_APPHEADER = 0x01, 0x02, 0x04    # Hdr_Indicator
VCD_SOURCE, VCD_TARGET, VCD_ADLER32 = 0x01, 0x02, 0x04             # Win_Indicator (0x04: xdelta3)
NOOP, ADD, RUN, COPY = 0, 1, 2, 3
S_NEAR, S_SAME = 4, 3
WINDOW = 1 << 23            # 8 MiB, xdelta3's default window
BLOCK = 0x1000              # compare step inside a window
MERGE_GAP = 16              # equal gaps this short are folded into an ADD
# Default code table indexes used by the encoder (RFC 3284 5.6).
ADD_SIZE0 = 1               # ADD, size follows
COPY_SELF_SIZE0 = 19        # COPY mode 0 (VCD_SELF), size follows

REDUMP_SHA1 = "78771805294c924b68fe4aa01ad52f70229abb9d"   # extract_disc.REDUMP


def default_code_table():
    """RFC 3284 section 5.6: 256 (inst1, size1, mode1, inst2, size2, mode2)."""
    t = [(RUN, 0, 0, NOOP, 0, 0)]
    t += [(ADD, s, 0, NOOP, 0, 0) for s in range(0, 18)]
    for mode in range(9):
        t.append((COPY, 0, mode, NOOP, 0, 0))
        t += [(COPY, s, mode, NOOP, 0, 0) for s in range(4, 19)]
    for mode in range(6):
        t += [(ADD, a, 0, COPY, c, mode) for a in range(1, 5) for c in range(4, 7)]
    for mode in range(6, 9):
        t += [(ADD, a, 0, COPY, 4, mode) for a in range(1, 5)]
    t += [(COPY, 4, mode, ADD, 1, 0) for mode in range(9)]
    assert len(t) == 256
    return t


CODE_TABLE = default_code_table()
assert CODE_TABLE[ADD_SIZE0] == (ADD, 0, 0, NOOP, 0, 0)
assert CODE_TABLE[COPY_SELF_SIZE0] == (COPY, 0, 0, NOOP, 0, 0)


# --- integers ----------------------------------------------------------------

def put_int(n):
    """RFC 3284 2.2: base-128, most significant digit first, high bit set on
    every byte but the last."""
    out = [n & 0x7f]
    n >>= 7
    while n:
        out.append(0x80 | (n & 0x7f))
        n >>= 7
    return bytes(reversed(out))


class Reader:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def byte(self):
        if self.pos >= len(self.data):
            raise ValueError("truncated VCDIFF data")
        b = self.data[self.pos]
        self.pos += 1
        return b

    def int(self):
        n = 0
        for _ in range(10):
            b = self.byte()
            n = (n << 7) | (b & 0x7f)
            if not b & 0x80:
                return n
        raise ValueError("integer too long")

    def take(self, n):
        if self.pos + n > len(self.data):
            raise ValueError("truncated VCDIFF data")
        b = self.data[self.pos:self.pos + n]
        self.pos += n
        return b


# --- encoder -----------------------------------------------------------------

def changed_ranges(src, tgt):
    """[(start, end)] where tgt differs from src (src may be shorter), with
    short equal gaps folded in."""
    ranges = []
    n = len(tgt)
    common = min(len(src), n)
    for b in range(0, common, BLOCK):
        e = min(b + BLOCK, common)
        if src[b:e] == tgt[b:e]:
            continue
        i = b
        while i < e:
            if src[i] != tgt[i]:
                j = i + 1
                while j < e and src[j] != tgt[j]:
                    j += 1
                if ranges and i - ranges[-1][1] <= MERGE_GAP:
                    ranges[-1] = (ranges[-1][0], j)
                else:
                    ranges.append((i, j))
                i = j
            else:
                i += 1
    if n > common:
        if ranges and common - ranges[-1][1] <= MERGE_GAP:
            ranges[-1] = (ranges[-1][0], n)
        else:
            ranges.append((common, n))
    return ranges


def encode_window(src, tgt, src_pos):
    """One window: tgt against the source segment src (at src_pos)."""
    data, inst, addr = bytearray(), bytearray(), bytearray()
    pos = 0
    for start, end in changed_ranges(src, tgt):
        if start > pos:
            inst += bytes([COPY_SELF_SIZE0]) + put_int(start - pos)
            addr += put_int(pos)                 # VCD_SELF: address as is
        inst += bytes([ADD_SIZE0]) + put_int(end - start)
        data += tgt[start:end]
        pos = end
    if pos < len(tgt):
        inst += bytes([COPY_SELF_SIZE0]) + put_int(len(tgt) - pos)
        addr += put_int(pos)
    body = (put_int(len(tgt)) + b"\x00" + put_int(len(data)) + put_int(len(inst))
            + put_int(len(addr)) + bytes(data) + bytes(inst) + bytes(addr))
    if src:
        head = bytes([VCD_SOURCE]) + put_int(len(src)) + put_int(src_pos)
    else:
        head = b"\x00"
    return head + put_int(len(body)) + body


def encode(src_file, tgt_file, out_file, progress=None):
    """Write a VCDIFF of tgt_file against src_file; return the SHA-1s."""
    src_len = _size(src_file)
    tgt_len = _size(tgt_file)
    hs, ht = hashlib.sha1(), hashlib.sha1()
    out_file.write(MAGIC + b"\x00")
    pos = 0
    while pos < tgt_len or pos == 0:
        tgt_file.seek(pos)
        tgt = tgt_file.read(WINDOW)
        src_file.seek(pos)
        src = src_file.read(min(WINDOW, max(0, src_len - pos)))
        hs.update(src)
        ht.update(tgt)
        out_file.write(encode_window(src, tgt, pos))
        pos += len(tgt)
        if progress:
            progress(pos, tgt_len)
        if not tgt:
            break
    if src_len > tgt_len:                       # hash the rest of a longer source
        src_file.seek(tgt_len)
        while buf := src_file.read(WINDOW):
            hs.update(buf)
    return hs.hexdigest(), ht.hexdigest()


def _size(f):
    here = f.tell()
    f.seek(0, os.SEEK_END)
    n = f.tell()
    f.seek(here)
    return n


# --- decoder -----------------------------------------------------------------

class Window:
    def __init__(self, indicator, seg_len, seg_pos, tgt_len, data, inst, addr, checksum):
        self.indicator, self.seg_len, self.seg_pos = indicator, seg_len, seg_pos
        self.tgt_len, self.data, self.inst, self.addr = tgt_len, data, inst, addr
        self.checksum = checksum


def parse(patch):
    """(header info, [Window]) of a VCDIFF file in memory."""
    if patch[:4] != MAGIC:
        raise ValueError("not a VCDIFF file")
    r = Reader(patch, 4)
    hdr = r.byte()
    info = {"app_header": b""}
    if hdr & VCD_DECOMPRESS:
        raise ValueError("secondary compression (id %d) is not supported; make the patch "
                         "with xdelta3 -S none" % r.byte())
    if hdr & VCD_CODETABLE:
        raise ValueError("custom code tables are not supported")
    if hdr & VCD_APPHEADER:
        info["app_header"] = r.take(r.int())
    windows = []
    while r.pos < len(patch):
        ind = r.byte()
        seg_len = seg_pos = 0
        if ind & (VCD_SOURCE | VCD_TARGET):
            if ind & VCD_TARGET:
                raise ValueError("VCD_TARGET windows are not supported")
            seg_len, seg_pos = r.int(), r.int()
        delta_len = r.int()
        end = r.pos + delta_len
        tgt_len = r.int()
        if r.byte():
            raise ValueError("compressed delta sections are not supported")
        dl, il, al = r.int(), r.int(), r.int()
        checksum = None
        if ind & VCD_ADLER32:
            checksum = int.from_bytes(r.take(4), "big")
        data, inst, addr = r.take(dl), r.take(il), r.take(al)
        if r.pos != end:
            raise ValueError("window length mismatch")
        windows.append(Window(ind, seg_len, seg_pos, tgt_len, data, inst, addr, checksum))
    return info, windows


def decode_window(w, segment):
    """The target bytes of one window, given its source segment bytes."""
    out = bytearray()
    data, inst, addr = Reader(w.data), Reader(w.inst), Reader(w.addr)
    near, next_slot, same = [0] * S_NEAR, 0, [0] * (S_SAME * 256)
    seg_len = len(segment)

    def address(mode):
        nonlocal next_slot
        here = seg_len + len(out)
        if mode == 0:
            a = addr.int()
        elif mode == 1:
            a = here - addr.int()
        elif mode < 2 + S_NEAR:
            a = near[mode - 2] + addr.int()
        else:
            a = same[(mode - 2 - S_NEAR) * 256 + addr.byte()]
        near[next_slot] = a
        next_slot = (next_slot + 1) % S_NEAR
        same[a % (S_SAME * 256)] = a
        return a

    while inst.pos < len(w.inst):
        code = CODE_TABLE[inst.byte()]
        for kind, size, mode in (code[0:3], code[3:6]):
            if kind == NOOP:
                continue
            if size == 0:
                size = inst.int()
            if kind == ADD:
                out += data.take(size)
            elif kind == RUN:
                out += bytes([data.byte()]) * size
            else:
                a = address(mode)
                if a + size <= seg_len:
                    out += segment[a:a + size]
                else:
                    for k in range(size):       # may read what it writes
                        p = a + k
                        out.append(segment[p] if p < seg_len else out[p - seg_len])
    if len(out) != w.tgt_len:
        raise ValueError("window decoded to %d bytes, header says %d" % (len(out), w.tgt_len))
    if w.checksum is not None and (zlib.adler32(bytes(out)) & 0xffffffff) != w.checksum:
        raise ValueError("window Adler-32 mismatch: wrong source file?")
    return bytes(out)


def decode(src_file, patch, out_file, progress=None):
    """Apply a VCDIFF to src_file; return (source SHA-1 of the bytes used is
    not meaningful, so) the output SHA-1."""
    _, windows = parse(patch)
    h = hashlib.sha1()
    total = sum(w.tgt_len for w in windows)
    done = 0
    for w in windows:
        src_file.seek(w.seg_pos)
        segment = src_file.read(w.seg_len)
        if len(segment) != w.seg_len:
            raise ValueError("source file is too short for this patch")
        out = decode_window(w, segment)
        out_file.write(out)
        h.update(out)
        done += len(out)
        if progress:
            progress(done, total)
    return h.hexdigest()


def file_sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while buf := f.read(WINDOW):
            h.update(buf)
    return h.hexdigest()


# --- commands ----------------------------------------------------------------

class Progress:
    def __init__(self, label):
        self.label, self.shown = label, 0
        print(label, end="", flush=True)

    def __call__(self, done, total):
        while total and self.shown < 10 * done // total:
            self.shown += 1
            print(" %d%%" % (self.shown * 10), end="", flush=True)

    def end(self):
        print()


def cmd_make(src, tgt, out):
    if os.path.abspath(out) in (os.path.abspath(src), os.path.abspath(tgt)):
        raise SystemExit("the output would overwrite an input")
    p = Progress("Comparing %s with %s:" % (os.path.basename(tgt), os.path.basename(src)))
    with open(src, "rb") as fs, open(tgt, "rb") as ft, open(out, "wb") as fo:
        s_sha, t_sha = encode(fs, ft, fo, p)
    p.end()
    print("%s: %d bytes" % (out, os.path.getsize(out)))
    print("  source SHA-1 %s%s" % (s_sha, "  (the Redump image)" if s_sha == REDUMP_SHA1 else
                                    "  (not the Redump image; players need this exact file)"))
    print("  target SHA-1 %s" % t_sha)
    print("  patch  SHA-1 %s" % file_sha1(out))


def cmd_apply(src, patch_path, out):
    if os.path.abspath(out) == os.path.abspath(src):
        raise SystemExit("the output would overwrite the source")
    with open(patch_path, "rb") as f:
        patch = f.read()
    p = Progress("Applying %s:" % os.path.basename(patch_path))
    with open(src, "rb") as fs, open(out, "wb") as fo:
        sha = decode(fs, patch, fo, p)
    p.end()
    print("%s: %d bytes, SHA-1 %s" % (out, os.path.getsize(out), sha))


def cmd_info(patch_path):
    with open(patch_path, "rb") as f:
        patch = f.read()
    info, windows = parse(patch)
    total = sum(w.tgt_len for w in windows)
    adds = sum(len(w.data) for w in windows)
    print("%s: %d bytes, %d windows, target %d bytes, %d bytes of new data%s" % (
        patch_path, len(patch), len(windows), total, adds,
        ", app header %r" % info["app_header"] if info["app_header"] else ""))
    changed = [(w.seg_pos, len(w.data)) for w in windows if w.data]
    for pos, n in changed[:20]:
        print("  window at %#x: %d new bytes" % (pos, n))
    if len(changed) > 20:
        print("  ... %d more windows with new bytes" % (len(changed) - 20))


def cmd_roundtrip(src, tgt):
    with open(src, "rb") as fs, open(tgt, "rb") as ft:
        buf = io.BytesIO()
        s_sha, t_sha = encode(fs, ft, buf)
        out = io.BytesIO()
        fs.seek(0)
        o_sha = decode(fs, buf.getvalue(), out)
    info, windows = parse(buf.getvalue())
    print("%s -> %s: patch %d bytes, %d windows, %d new bytes; decoded %s" % (
        src, tgt, len(buf.getvalue()), len(windows), sum(len(w.data) for w in windows),
        "identical" if o_sha == t_sha else "DIFFERENT  !! decoded output does not match the target"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "make" and len(args) == 3:
            cmd_make(*args)
        elif cmd == "apply" and len(args) == 3:
            cmd_apply(*args)
        elif cmd == "info" and len(args) == 1:
            cmd_info(args[0])
        elif cmd == "roundtrip" and len(args) == 2:
            cmd_roundtrip(*args)
        else:
            print(__doc__)
            return 1
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
