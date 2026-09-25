"""Reader for the BINPAC (.PAC/.MRG/.HED) and KC@P (.HED + .BIN/.PAC)
archive formats in DATA.CVM, plus the PRSH (Sega PRS) compression wrapper.

See DOC/PAC_FORMAT.md for the layouts.

Usage:
    python pac.py info    <file|dir> ...          # header summary + sanity checks
    python pac.py list    <file>                  # one line per entry
    python pac.py extract <file> <outdir> [--prs] # write entries (--prs: expand PRSH)
    python pac.py unprs   <in> <out>              # expand one PRSH blob

<file> may be a self-describing .PAC/.MRG, or a detached header (.HED, or a
KC@P *_HEADER.BIN); the data file is then found next to it by name.
"""
import os
import struct
import sys

BINPAC_NAMELESS = 0x49421001  # u32 @ +0x08: entries carry a u32 tag, not a name
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
        h = load_header(p)
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


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
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
