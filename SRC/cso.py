# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""CSO and ZSO compressed disc images, which PCSX2 runs and many players
keep instead of the 3.5 GB ISO of Let's Make a Soccer Team! (PS2). Read
only: the tools that take a disc image (vcdiff.py) open one through
open_image() and see the ISO's bytes. Standard library only.

  header  0x18 bytes: char[4] magic ("CISO" or "ZISO"), u32 header size
          (0x18), u64 the ISO's size, u32 block size, u8 version, u8 index
          shift, 2 bytes unused
  index   (blocks + 1) u32: block i's data runs from (index[i] & 0x7fffffff)
          << shift to (index[i + 1] & 0x7fffffff) << shift
  blocks  CSO v0/v1: bit 31 set means stored as is, else raw deflate.
          CSO v2 (maxcso): a block at least the block size long is stored
          as is; bit 31 set means LZ4, else raw deflate. ZSO: bit 31 set
          means stored as is, else LZ4. LZ4 blocks are raw LZ4 blocks,
          decoded here in Python (slower than deflate)

The format is maxcso's documentation of it (github.com/unknownbrackets/
maxcso, README_CSO.md); see DOC/REBUILD.md#compressed-images.

Usage:
    python cso.py info    <image.cso | image.zso>      # header and index checks
    python cso.py check   <image.cso | image.zso>      # decompress all, SHA-1, Redump check
    python cso.py extract <image.cso | image.zso> <out.iso>

`check` and `extract` print the ISO's SHA-1 and say whether it is the
Redump dump (redump.info/disc/12334), so a patch's expected source can be
confirmed without writing the ISO.
"""
import hashlib
import os
import struct
import sys
import zlib

MAGICS = (b"CISO", b"ZISO")
HEADER = struct.Struct("<4sIQIBBH")      # 0x18 bytes
HEADER_SIZE = 0x18
PLAIN = 0x80000000                      # index bit 31
OFFSET_MASK = 0x7FFFFFFF
REDUMP_SHA1 = "78771805294c924b68fe4aa01ad52f70229abb9d"   # extract_disc.REDUMP
CHUNK = 1 << 24


def lz4_block(src, size):
    """Decode one raw LZ4 block to `size` bytes. Stops once `size` bytes are
    out, so padding after the block (index shift alignment) is ignored."""
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]
        i += 1
        lit = token >> 4
        if lit == 15:
            while True:
                b = src[i]
                i += 1
                lit += b
                if b != 255:
                    break
        out += src[i:i + lit]
        i += lit
        if len(out) >= size or i >= n:
            break
        off = src[i] | (src[i + 1] << 8)
        i += 2
        if off == 0 or off > len(out):
            raise ValueError("LZ4: bad match offset")
        ml = token & 15
        if ml == 15:
            while True:
                b = src[i]
                i += 1
                ml += b
                if b != 255:
                    break
        ml += 4
        start = len(out) - off
        if off >= ml:
            out += out[start:start + ml]
        else:                           # overlapping: repeat the last `off` bytes
            while ml > 0:
                piece = out[start:start + min(off, ml)]
                out += piece
                ml -= len(piece)
    if len(out) < size:
        raise ValueError("LZ4 block decoded to %d bytes, expected %d" % (len(out), size))
    return bytes(out[:size])


class Image:
    """A CSO or ZSO image as a read-only, seekable file of the ISO's bytes."""
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        head = self.f.read(HEADER_SIZE)
        if len(head) < HEADER_SIZE:
            raise ValueError("%s: too short for a CSO header" % path)
        (self.magic, self.header_size, self.size, self.block, self.version,
         self.shift, _) = HEADER.unpack(head)
        if self.magic not in MAGICS:
            raise ValueError("%s: not a CSO or ZSO image" % path)
        if self.block < 0x800 or self.block & (self.block - 1):
            raise ValueError("%s: block size %d is not a power of two >= 2048"
                             % (path, self.block))
        if self.magic == b"CISO" and self.version > 2:
            raise ValueError("%s: CSO version %d is not known" % (path, self.version))
        self.blocks = (self.size + self.block - 1) // self.block
        raw = self.f.read(4 * (self.blocks + 1))
        if len(raw) != 4 * (self.blocks + 1):
            raise ValueError("%s: the block index is cut short" % path)
        self.index = struct.unpack("<%dI" % (self.blocks + 1), raw)
        self.pos = 0
        self.cached = (-1, b"")

    def kind(self):
        if self.magic == b"ZISO":
            return "ZSO"
        return "CSO v%d" % self.version

    def problems(self):
        """Index checks: offsets past the index, rising, and within the file."""
        out = []
        file_size = os.path.getsize(self.path)
        first = HEADER_SIZE + 4 * (self.blocks + 1)
        prev = None
        for i, e in enumerate(self.index):
            off = (e & OFFSET_MASK) << self.shift
            if off < first and i < self.blocks:
                out.append("block %d starts inside the header or index" % i)
            if prev is not None and off < prev:
                out.append("block %d starts before block %d" % (i, i - 1))
            prev = off
            if len(out) > 10:
                break
        end = (self.index[-1] & OFFSET_MASK) << self.shift
        if end > file_size:
            out.append("the index ends at %#x, past the file (%#x)" % (end, file_size))
        return out

    def read_block(self, i):
        if self.cached[0] == i:
            return self.cached[1]
        a = (self.index[i] & OFFSET_MASK) << self.shift
        b = (self.index[i + 1] & OFFSET_MASK) << self.shift
        want = min(self.block, self.size - i * self.block)
        self.f.seek(a)
        data = self.f.read(b - a)
        flag = self.index[i] & PLAIN
        if self.magic == b"ZISO":
            mode = "plain" if flag else "lz4"
        elif self.version == 2:
            mode = "plain" if len(data) >= self.block else ("lz4" if flag else "deflate")
        else:
            mode = "plain" if flag else "deflate"
        if mode == "plain":
            out = data[:want]
        elif mode == "lz4":
            out = lz4_block(data, want)
        else:
            d = zlib.decompressobj(-15)
            out = d.decompress(data, want)
        if len(out) != want:
            raise ValueError("%s: block %d decoded to %d bytes, expected %d"
                             % (self.path, i, len(out), want))
        self.cached = (i, out)
        return out

    # file interface

    def seek(self, pos, whence=0):
        if whence == 1:
            pos += self.pos
        elif whence == 2:
            pos += self.size
        self.pos = max(0, pos)
        return self.pos

    def tell(self):
        return self.pos

    def read(self, n=-1):
        if n < 0 or self.pos + n > self.size:
            n = max(0, self.size - self.pos)
        out = bytearray()
        while len(out) < n:
            i, o = divmod(self.pos, self.block)
            take = self.read_block(i)[o:o + n - len(out)]
            out += take
            self.pos += len(take)
        return bytes(out)

    def close(self):
        self.f.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def is_compressed(path):
    with open(path, "rb") as f:
        return f.read(4) in MAGICS


def open_image(path):
    """A disc image for reading: a CSO/ZSO as its ISO bytes, else the file."""
    return Image(path) if is_compressed(path) else open(path, "rb")


def image_size(f):
    """The ISO size of an open_image() result."""
    if isinstance(f, Image):
        return f.size
    here = f.tell()
    f.seek(0, os.SEEK_END)
    n = f.tell()
    f.seek(here)
    return n


def sha1_of(img, out=None, progress=None):
    h = hashlib.sha1()
    img.seek(0)
    done = 0
    while buf := img.read(CHUNK):
        h.update(buf)
        if out:
            out.write(buf)
        done += len(buf)
        if progress:
            progress(done, img.size)
    return h.hexdigest()


class Progress:
    def __init__(self, label):
        self.shown = 0
        print(label, end="", flush=True)

    def __call__(self, done, total):
        while total and self.shown < 10 * done // total:
            self.shown += 1
            print(" %d%%" % (self.shown * 10), end="", flush=True)

    def end(self):
        print()


def cmd_info(path):
    try:
        with Image(path) as img:
            problems = img.problems()
            end = (img.index[-1] & OFFSET_MASK) << img.shift
            plain = sum(1 for e in img.index[:-1] if e & PLAIN)
            print("%s: %s, ISO %d bytes in %d blocks of %d, index shift %d, data ends at %#x%s"
                  % (path, img.kind(), img.size, img.blocks, img.block, img.shift, end,
                     "  !! " + "; ".join(problems) if problems else ""))
            print("  %d blocks with bit 31 set (%s), file %d bytes (%.1f%% of the ISO)"
                  % (plain, "LZ4" if img.magic == b"CISO" and img.version == 2 else "stored",
                     os.path.getsize(path), 100.0 * os.path.getsize(path) / max(1, img.size)))
    except (ValueError, struct.error, OSError) as e:
        print("%s  !! %s" % (path, e))


def report(sha):
    print("  SHA-1 %s%s" % (sha, "  (the Redump image)" if sha == REDUMP_SHA1 else
                            "  (not the Redump image)"))


def cmd_check(path):
    with Image(path) as img:
        p = Progress("Decompressing %s:" % os.path.basename(path))
        sha = sha1_of(img, progress=p)
        p.end()
    print("%s: %s, %d bytes decompressed" % (path, img.kind(), img.size))
    report(sha)


def cmd_extract(path, out):
    if os.path.abspath(out) == os.path.abspath(path):
        raise SystemExit("the output would overwrite the input")
    with Image(path) as img, open(out, "wb") as f:
        p = Progress("Decompressing %s:" % os.path.basename(path))
        sha = sha1_of(img, f, p)
        p.end()
    print("wrote %s: %d bytes" % (out, os.path.getsize(out)))
    report(sha)


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "info" and len(args) == 1:
            cmd_info(args[0])
        elif cmd == "check" and len(args) == 1:
            cmd_check(args[0])
        elif cmd == "extract" and len(args) == 2:
            cmd_extract(*args)
        else:
            print(__doc__)
            return 1
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
