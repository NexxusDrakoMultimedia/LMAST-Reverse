# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for the BINPAC (.PAC/.MRG/.HED) and KC@P (.HED + .BIN/.PAC)
archive formats in DATA.CVM, plus the PRSH (Sega PRS) compression wrapper,
and a writer for self-describing BINPACs.

See DOC/PAC_FORMAT.md for the layouts.

The writer lays entries out as the original packer did (empirical, all
662 self-describing BINPACs in DAT/): the first entry starts at
(table_end + 4 + align - 1) & ~(align - 1), or right at table_end when
align is 4; each next one at (offset + size + align) & ~(align - 1), so
there is always at least one byte of gap; gaps are filled with ASCII '0'
and the header padding with zeros; the file ends at the last entry's end.
Names, flags and the extra columns are copied from the original header.

Usage:
    python pac.py info      <file|dir> ...          # header summary + sanity checks
    python pac.py list      <file>                  # one line per entry
    python pac.py extract   <file> <outdir> [--prs] # write entries (--prs: expand PRSH)
    python pac.py unprs     <in> <out>              # expand one PRSH blob
    python pac.py roundtrip <file|dir> ...          # rebuild every BINPAC, compare bytes
    python pac.py replace   <in> <out> <entry>=<file> ...   # repack with new entries

<file> may be a self-describing .PAC/.MRG, or a detached header (.HED, or a
KC@P *_HEADER.BIN); the data file is then found next to it by name.
`roundtrip` and `replace` work on self-describing BINPACs only (not .HED
headers or KC@P). <entry> is an index or a name.
"""
import os
import struct
import sys

BINPAC_NAMELESS = 0x49421001  # u32 @ +0x08: entries carry a u32 tag, not a name
GAP_FILL = b"0"               # the packer's filler between entries (34,410 of 34,410 gaps)
KCAP_MAGIC = b"KC@P"
PRSH_MAGIC = b"PRSH"


# --- PRS / PRSH --------------------------------------------------------------

def prs_decompress(src, pos=0, out_size=None):
    """Sega PRS, as implemented by stPrsInf::Extract (0x1ff570)."""
    out = bytearray()
    bits = nbits = 0

    def bit():
        nonlocal bits, nbits, pos
        if nbits == 0:
            bits, nbits = src[pos], 8
            pos += 1
        b = bits & 1
        bits >>= 1
        nbits -= 1
        return b

    while True:
        if bit():                       # literal
            out.append(src[pos])
            pos += 1
            continue
        if bit():                       # long copy
            lo, hi = src[pos], src[pos + 1]
            pos += 2
            if lo == 0 and hi == 0:
                break
            off = ((hi << 5) | (lo >> 3)) - 0x2000
            n = lo & 7
            if n:
                n += 2
            else:
                n = src[pos] + 1
                pos += 1
        else:                           # short copy
            n = (bit() << 1 | bit()) + 2
            off = src[pos] - 0x100
            pos += 1
        start = len(out) + off
        for k in range(n):              # byte-wise: source may overlap dest
            out.append(out[start + k])
    if out_size is not None and len(out) != out_size:
        raise ValueError("PRS: expanded %d bytes, header says %d" % (len(out), out_size))
    return bytes(out)


def prsh_expand(blob):
    """Press::ExtractData (0x1ff470): {'PRSH', data_off, comp_size, raw_size}."""
    if blob[:4] != PRSH_MAGIC:
        return None
    data_off, _comp, raw = struct.unpack_from("<III", blob, 4)
    return prs_decompress(blob, data_off, raw)


# --- BINPAC ------------------------------------------------------------------

class BinPac:
    """Header accessors mirror fcEuroBinPac_GetHeaderInfo (0x104670) and
    fcEuroBinPac_GetHeaderListData (0x1046e8)."""

    def __init__(self, hdr):
        if hdr[10:16] != b"BINPAC":
            raise ValueError("not a BINPAC header")
        (self.header_size, self.count, self.version, self.flags,
         self.align, name_len) = struct.unpack_from("<IhhI4xII", hdr)
        self.nameless = self.flags == BINPAC_NAMELESS
        if self.nameless:
            self.name_len = 4           # column 2 is a u32 tag like "snm\0"
        else:
            self.name_len = name_len if name_len >= 1 else 0x80
        self.stride = 4 * (self.version + 1) + self.name_len
        self.entries = []
        for i in range(self.count):
            o = 0x20 + i * self.stride
            off, size = struct.unpack_from("<II", hdr, o)
            name = hdr[o + 8:o + 8 + self.name_len].split(b"\0")[0].decode("latin1")
            n_extra = self.version - 1
            extra = struct.unpack_from("<%dI" % n_extra, hdr, o + 8 + self.name_len)
            self.entries.append((off, size, name, extra))

    def table_end(self):
        return 0x20 + self.count * self.stride


def binpac_header_size(table_end, align):
    """Where the packer put the first entry: one spare u32 after the table,
    then padding to `align`. The 46 archives aligned to 4 have no spare u32."""
    if align == 4:
        return table_end
    return (table_end + 4 + align - 1) & ~(align - 1)


def build_binpac(hdr_bytes, blobs):
    """A self-describing BINPAC holding `blobs`, one per entry of the archive
    whose header is `hdr_bytes`. Only the header size and each entry's
    offset and size change; names, flags and extra columns are kept."""
    h = BinPac(hdr_bytes)
    if len(blobs) != h.count:
        raise ValueError("%d blobs for %d entries" % (len(blobs), h.count))
    end = h.table_end()
    size = binpac_header_size(end, h.align)
    out = bytearray(hdr_bytes[:end]) + bytes(size - end)
    struct.pack_into("<I", out, 0, size)
    pos = size
    for i, blob in enumerate(blobs):
        struct.pack_into("<II", out, 0x20 + i * h.stride, pos, len(blob))
        out += blob
        if i < h.count - 1:
            pos = (pos + len(blob) + h.align) & ~(h.align - 1)
            out += GAP_FILL * (pos - len(out))
    return bytes(out)


def binpac_blobs(data):
    """(header, [entry bytes]) of a self-describing BINPAC."""
    h = BinPac(data[:struct.unpack_from("<I", data)[0]])
    blobs = []
    for i, (off, size, _, _) in enumerate(h.entries):
        if off + size > len(data):
            raise ValueError("entry %d past EOF" % i)
        blobs.append(data[off:off + size])
    return h, blobs


def find_entry(h, sel):
    """Index of the entry named or numbered `sel`."""
    if sel.isdigit():
        i = int(sel)
        if i >= h.count:
            raise ValueError("entry %d out of range (%d entries)" % (i, h.count))
        return i
    hits = [i for i, e in enumerate(h.entries) if e[2].lower() == sel.lower()]
    if len(hits) != 1:
        raise ValueError("%s: %s" % (sel, "no such entry" if not hits else
                                     "%d entries match; use the index" % len(hits)))
    return hits[0]


class KcAtP:
    """{'KC@P', total_size, count, 0, u32 end_offset[count]}; entry i spans
    [end[i-1] (or 0), end[i]) of a headerless data file."""

    def __init__(self, hdr):
        if hdr[:4] != KCAP_MAGIC:
            raise ValueError("not a KC@P header")
        self.total_size, self.count = struct.unpack_from("<II", hdr, 4)
        ends = struct.unpack_from("<%dI" % self.count, hdr, 16)
        starts = (0,) + ends[:-1]
        self.entries = [(s, e - s, "", ()) for s, e in zip(starts, ends)]


def load_header(path):
    with open(path, "rb") as f:
        head = f.read(0x40000)
    if head[10:16] == b"BINPAC":
        hs = struct.unpack_from("<I", head)[0]
        if hs > len(head):
            with open(path, "rb") as f:
                head = f.read(hs)
        return BinPac(head)
    if head[:4] == KCAP_MAGIC:
        return KcAtP(head)
    return None


def partner(hed_path):
    """Data file for a detached header: FOO.HED -> FOO.PAC/.MRG/.BIN,
    FOO_BIN.HED -> FOO.BIN, FOO_HEADER.BIN -> FOO.BIN."""
    stem = hed_path[:-4]
    cands = [stem + e for e in (".PAC", ".MRG", ".BIN")]
    for suffix in ("_BIN", "_HEADER"):
        if stem.upper().endswith(suffix):
            cands.insert(0, stem[:-len(suffix)] + ".BIN")
    for c in cands:
        if os.path.exists(c):
            return c
    return None


def data_path(path, hdr):
    """KC@P headers and .HED files are detached; other BINPACs are inline."""
    if path.upper().endswith(".HED") or isinstance(hdr, KcAtP):
        return partner(path)
    return path


# --- commands ----------------------------------------------------------------

def _walk(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _, files in os.walk(p):
                for f in sorted(files):
                    yield os.path.join(root, f)
        else:
            yield p


def cmd_info(paths):
    for p in _walk(paths):
        try:
            h = load_header(p)
        except (ValueError, struct.error) as e:
            print("%-50s !! %s" % (p, e))
            continue
        if h is None:
            continue
        dp = data_path(p, h)
        dsize = os.path.getsize(dp) if dp else None
        problems = []
        if isinstance(h, BinPac):
            desc = "BINPAC v%d %s align=%#x name=%d n=%d hdr=%#x" % (
                h.version, "tag" if h.nameless else "named", h.align,
                h.name_len, h.count, h.header_size)
            if h.table_end() > h.header_size:
                problems.append("entry table overruns header")
            if dp and dp != p:
                with open(dp, "rb") as f:
                    head = f.read(h.header_size)
                with open(p, "rb") as f:
                    if f.read(h.header_size) != head:
                        problems.append("differs from %s header (stale .HED?)"
                                        % os.path.basename(dp))
        else:
            desc = "KC@P n=%d total=%#x" % (h.count, h.total_size)
            if dsize is not None and dsize != h.total_size:
                problems.append("data file is %d bytes" % dsize)
        if dp is None:
            problems.append("no data file")
        elif not problems:
            for i, (off, size, _, _) in enumerate(h.entries):
                if off + size > dsize:
                    problems.append("entry %d past EOF" % i)
                    break
        print("%-50s %s%s" % (p, desc, ("  !! " + "; ".join(problems)) if problems else ""))


def cmd_list(path):
    h = load_header(path)
    if h is None:
        raise SystemExit("%s: not a BINPAC/KC@P file" % path)
    dp = data_path(path, h)
    f = open(dp, "rb") if dp else None
    for i, (off, size, name, extra) in enumerate(h.entries):
        magic = ""
        if f and size:
            f.seek(off)
            m = f.read(4)
            magic = m.decode("latin1") if all(32 <= c < 127 for c in m) else m.hex()
        ex = " ".join("%#x" % x if x == 0xFFFFFFFF else str(x) for x in extra)
        print("%5d %#10x %9d %-4s %-6s %s" % (i, off, size, magic, ex, name))


def _out_name(i, name):
    name = name.replace("/", "_").replace("\\", "_")
    if not name:
        return "%05d.bin" % i
    return "%05d%s" % (i, name) if name.startswith(".") else "%05d_%s" % (i, name)


def cmd_extract(path, outdir, prs):
    h = load_header(path)
    if h is None:
        raise SystemExit("%s: not a BINPAC/KC@P file" % path)
    dp = data_path(path, h)
    if dp is None:
        raise SystemExit("%s: data file not found" % path)
    os.makedirs(outdir, exist_ok=True)
    expanded = 0
    with open(dp, "rb") as f:
        for i, (off, size, name, _) in enumerate(h.entries):
            f.seek(off)
            blob = f.read(size)
            if prs:
                raw = prsh_expand(blob)
                if raw is not None:
                    blob, expanded = raw, expanded + 1
            with open(os.path.join(outdir, _out_name(i, name)), "wb") as o:
                o.write(blob)
    print("%d entries -> %s%s" % (len(h.entries), outdir,
                                  " (%d PRSH expanded)" % expanded if prs else ""))


def cmd_roundtrip(paths):
    ok = bad = 0
    for p in _walk(paths):
        if p.upper().endswith(".HED"):
            continue                    # detached headers; their data file is checked
        with open(p, "rb") as f:
            data = f.read()
        if data[10:16] != b"BINPAC":
            continue
        try:
            h, blobs = binpac_blobs(data)
            out = build_binpac(data[:h.header_size], blobs)
        except (ValueError, struct.error) as e:
            print("%-50s !! %s" % (p, e))
            bad += 1
            continue
        if out == data:
            ok += 1
            print("%-50s %d entries  identical" % (p, h.count))
            continue
        bad += 1
        diff = next((i for i in range(min(len(out), len(data))) if out[i] != data[i]), None)
        print("%-50s %d entries  !! rebuilt archive differs: %s" % (
            p, h.count, "first difference at %#x" % diff if diff is not None
            else "length %d, rebuilt %d" % (len(data), len(out))))
    print("%d identical, %d differ" % (ok, bad))


def cmd_replace(src, dst, pairs):
    with open(src, "rb") as f:
        data = f.read()
    h, blobs = binpac_blobs(data)
    for pair in pairs:
        sel, sep, path = pair.partition("=")
        if not sep:
            raise SystemExit("expected <entry>=<file>, got %r" % pair)
        i = find_entry(h, sel)
        with open(path, "rb") as f:
            new = f.read()
        print("#%d %s: %d -> %d bytes" % (i, h.entries[i][2], len(blobs[i]), len(new)))
        blobs[i] = new
    out = build_binpac(data[:h.header_size], blobs)
    with open(dst, "wb") as f:
        f.write(out)
    print("%s: %d -> %d bytes (%d -> %d sectors)" % (
        dst, len(data), len(out), (len(data) + 0x7ff) >> 11, (len(out) + 0x7ff) >> 11))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "roundtrip":
        cmd_roundtrip(args)
        return 0
    if cmd == "replace" and len(args) >= 3:
        cmd_replace(args[0], args[1], args[2:])
        return 0
    if cmd == "info":
        cmd_info(args)
    elif cmd == "list":
        cmd_list(args[0])
    elif cmd == "extract" and len(args) >= 2:
        cmd_extract(args[0], args[1], "--prs" in args[2:])
    elif cmd == "unprs" and len(args) == 2:
        with open(args[0], "rb") as f:
            raw = prsh_expand(f.read())
        if raw is None:
            raise SystemExit("not a PRSH blob")
        with open(args[1], "wb") as f:
            f.write(raw)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
