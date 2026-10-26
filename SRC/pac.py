# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for the BINPAC (.PAC/.MRG/.HED) and KC@P (.HED + .BIN/.PAC)
archive formats in DATA.CVM, plus the PRSH (Sega PRS) compression wrapper,
and writers for self-describing BINPACs and for PRS (prs_compress).

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
    python pac.py prs       <in> <out>              # compress a file into a PRSH blob
    python pac.py prscheck  <file|dir> ...          # recompress every PRSH entry, expand, compare
    python pac.py roundtrip <file|dir> ...          # rebuild every BINPAC, compare bytes
    python pac.py replace   <in> <out> <entry>=<file> ... [--prs]   # repack with new entries

<file> may be a self-describing .PAC/.MRG, or a detached header (.HED, or a
KC@P *_HEADER.BIN); the data file is then found next to it by name.
`roundtrip` and `replace` work on self-describing BINPACs and KC@P headers
(not .HED copies of a BINPAC header). <entry> is an index or a name (an
index for KC@P). With --prs, `replace` compresses a new file whose entry
was PRSH (one made by `extract --prs`). For a KC@P header, `replace`
writes <out> and the data file, under its own name, next to it: entries
start on 0x800-byte sectors with zero padding, as CLoader::loadFaceRequest
(0x1192a0) reads them.

The PRS writer is greedy LZ77 in the format stPrsInf::Extract (0x1ff570)
reads; it gives other bytes than Sega's packer (101% of its size over the
disc's 5,496 PRSH entries), so `prscheck` compares the expanded data.
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


# What the PRS stream can encode (stPrsInf::Extract, prs_decompress above):
# a short copy is 2-5 bytes from up to 0x100 back, a long copy 3-9 bytes
# (or 1-256 with a length byte) from up to 0x2000 back. 0x2000 back with
# the length byte would read as the end marker (lo = hi = 0), so long
# copies stay within 0x1fff.
PRS_SHORT_BACK, PRS_SHORT_MAX = 0x100, 5
PRS_LONG_BACK, PRS_LONG_MAX = 0x1fff, 0x100
PRS_CHAIN = 64                  # candidates tried per position


def prs_compress(data):
    """Sega PRS for prs_decompress / stPrsInf::Extract: greedy LZ77 over a
    0x1fff-byte window, control bits LSB-first in bytes placed where the
    decoder reads them (before the data they govern)."""
    out = bytearray()
    ctrl = [None, 8]                # [position of the control byte, bits used]

    def bit(b):
        if ctrl[1] == 8:
            ctrl[0], ctrl[1] = len(out), 0
            out.append(0)
        out[ctrl[0]] |= b << ctrl[1]
        ctrl[1] += 1

    chains = {}                     # 3-byte key -> positions, newest last
    n, i = len(data), 0

    def add(k):
        if k + 3 <= n:
            chains.setdefault(data[k:k + 3], []).append(k)

    while i < n:
        best_len, best_off = 0, 0
        if i + 3 <= n:
            cands = chains.get(data[i:i + 3], ())
            limit = min(PRS_LONG_MAX, n - i)
            for j in reversed(cands[-PRS_CHAIN:]):
                if i - j > PRS_LONG_BACK:
                    break
                m = 3
                while m < limit and data[j + m] == data[i + m]:
                    m += 1
                if m > best_len:
                    best_len, best_off = m, i - j
                    if m == limit:
                        break
        if best_len < 3 or (best_len <= PRS_SHORT_MAX and best_off > PRS_SHORT_BACK):
            # A short copy: 2-5 bytes within 0x100.
            short = 0
            for back in range(1, min(PRS_SHORT_BACK, i) + 1):
                m = 0
                while m < PRS_SHORT_MAX and i + m < n and data[i - back + m] == data[i + m]:
                    m += 1
                if m > short:
                    short, sback = m, back
                    if m == PRS_SHORT_MAX:
                        break
            if short >= 2 and short >= best_len:
                best_len, best_off, kind = short, sback, "short"
            elif best_len >= 3 and best_off <= PRS_LONG_BACK:
                kind = "long"
            else:
                best_len, kind = 1, "literal"
        else:
            short_ok = best_len <= PRS_SHORT_MAX and best_off <= PRS_SHORT_BACK
            kind = "short" if short_ok else "long"
        if kind == "literal":
            bit(1)
            out.append(data[i])
        elif kind == "short":
            bit(0)
            bit(0)
            v = best_len - 2
            bit(v >> 1)
            bit(v & 1)
            out.append(PRS_SHORT_BACK - best_off)
        else:
            bit(0)
            bit(1)
            raw = 0x2000 - best_off
            if best_len <= 9:
                out += bytes(((raw & 0x1f) << 3 | (best_len - 2), raw >> 5))
            else:
                out += bytes(((raw & 0x1f) << 3, raw >> 5, best_len - 1))
        for k in range(i, i + best_len):
            add(k)
        i += best_len
    bit(0)
    bit(1)
    out += b"\0\0"
    return bytes(out)


PRSH_DATA = 0x40                # every PRSH on the disc: header, zeros, stream at 0x40


def prsh_wrap(raw):
    """A PRSH blob of `raw`: {'PRSH', 0x40, compressed size, raw size},
    zeros to 0x40, then the stream (Press::ExtractData 0x1ff470)."""
    stream = prs_compress(raw)
    head = PRSH_MAGIC + struct.pack("<III", PRSH_DATA, len(stream), len(raw))
    return head + bytes(PRSH_DATA - len(head)) + stream


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


def grow_binpac_header(hdr_bytes, count):
    """`hdr_bytes` with room for `count` entries, the new rows copying the
    last one's name and extra columns (build_binpac then sets each row's
    offset and size). The header may not need more space than it has."""
    h = BinPac(hdr_bytes)
    if count < h.count:
        raise ValueError("%d entries, fewer than the %d there are" % (count, h.count))
    end = 0x20 + count * h.stride
    if binpac_header_size(end, h.align) > h.header_size:
        raise ValueError("%d entries need a header of %d bytes, not %d" % (
            count, binpac_header_size(end, h.align), h.header_size))
    last = hdr_bytes[h.table_end() - h.stride:h.table_end()]
    out = bytearray(hdr_bytes[:h.table_end()]) + last * (count - h.count)
    struct.pack_into("<h", out, 4, count)
    return bytes(out) + bytes(h.header_size - len(out))


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


KCAP_SECTOR = 0x800     # CLoader::loadFaceRequest (0x1192a0) reads sectors: start >> 11,
                        # (end - start) >> 11; every entry starts on one (empirical, all 5)


def kcap_payload(slot):
    """An entry's own bytes: a PRSH blob up to the end of its stream (the
    rest of the slot is zero padding), anything else the whole slot."""
    if slot[:4] == PRSH_MAGIC:
        off, comp = struct.unpack_from("<II", slot, 4)
        return slot[:off + comp]
    return slot


def build_kcap(blobs):
    """(header, data file) for entries laid out as on the disc: each starts
    on a sector, the gap after it zero-filled; the header holds the total
    size, the count, 0 and each entry's end offset."""
    data, ends = bytearray(), []
    for b in blobs:
        data += b + bytes(-len(b) % KCAP_SECTOR)
        ends.append(len(data))
    head = KCAP_MAGIC + struct.pack("<III%dI" % len(ends), len(data), len(ends), 0, *ends)
    return head, bytes(data)


def kcap_check(head, data_file):
    """Problems with a KC@P header and its data file against build_kcap's
    layout, read entry by entry (the face pack is 1.1 GB)."""
    h = KcAtP(head)
    problems = []
    if len(head) != 0x10 + 4 * h.count:
        problems.append("header is %d bytes, not 0x10 + 4 x %d" % (len(head), h.count))
    size = os.path.getsize(data_file)
    if h.total_size != size:
        problems.append("total size %d, data file %d" % (h.total_size, size))
    with open(data_file, "rb") as f:
        for i, (off, n, _, _) in enumerate(h.entries):
            if off % KCAP_SECTOR:
                problems.append("entry %d starts at %#x, not on a sector" % (i, off))
                break
            f.seek(off)
            slot = f.read(n)
            own = kcap_payload(slot)
            if len(slot) - len(own) >= KCAP_SECTOR or any(slot[len(own):]):
                problems.append("entry %d: %d bytes after its data aren't the zero padding "
                                "to the next sector" % (i, len(slot) - len(own)))
                break
            if (off + n) % KCAP_SECTOR:
                problems.append("entry %d ends at %#x, not on a sector" % (i, off + n))
                break
    return problems


def kcap_blobs(head, data):
    """The entries of a KC@P pack (kcap_payload of each slot)."""
    return [kcap_payload(data[o:o + n]) for o, n, _, _ in KcAtP(head).entries]


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
        with open(p, "rb") as f:
            magic = f.read(16)
        if magic[:4] == KCAP_MAGIC:
            # A KC@P header: rebuilding gives the same files exactly when
            # every entry sits on a sector with only zero padding after it.
            with open(p, "rb") as f:
                head = f.read()
            dp = partner(p)
            problems = kcap_check(head, dp) if dp else ["data file not found"]
            if problems:
                bad += 1
                print("%-50s KC@P  !! %s" % (p, "; ".join(problems)))
            else:
                ok += 1
                print("%-50s KC@P %d entries  identical" % (p, KcAtP(head).count))
            continue
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


def cmd_replace_kcap(src, dst, pairs, prs):
    """replace for a KC@P header: writes <dst> and the data file, named as
    the original's, next to it."""
    with open(src, "rb") as f:
        head = f.read()
    dp = partner(src)
    if dp is None:
        raise SystemExit("%s: data file not found" % src)
    out_data = os.path.join(os.path.dirname(os.path.abspath(dst)), os.path.basename(dp))
    if os.path.abspath(out_data) == os.path.abspath(dp):
        raise SystemExit("write to another folder than %s's" % src)
    with open(dp, "rb") as f:
        data = f.read()
    blobs = kcap_blobs(head, data)
    for pair in pairs:
        sel, sep, path = pair.partition("=")
        if not sep or not sel.isdigit() or not 0 <= int(sel) < len(blobs):
            raise SystemExit("expected <index>=<file> with an index 0-%d, got %r"
                             % (len(blobs) - 1, pair))
        i = int(sel)
        with open(path, "rb") as f:
            new = f.read()
        note = ""
        if prs and blobs[i][:4] == PRSH_MAGIC and new[:4] != PRSH_MAGIC:
            note = " (%d expanded, PRSH)" % len(new)
            new = prsh_wrap(new)
        print("#%d: %d -> %d bytes%s" % (i, len(blobs[i]), len(new), note))
        blobs[i] = new
    new_head, new_data = build_kcap(blobs)
    with open(dst, "wb") as f:
        f.write(new_head)
    with open(out_data, "wb") as f:
        f.write(new_data)
    print("%s: %d bytes; %s: %d -> %d bytes (%d -> %d sectors)" % (
        dst, len(new_head), out_data, len(data), len(new_data),
        len(data) >> 11, len(new_data) >> 11))


def cmd_replace(src, dst, pairs, prs=False):
    with open(src, "rb") as f:
        data = f.read()
    if data[:4] == KCAP_MAGIC:
        return cmd_replace_kcap(src, dst, pairs, prs)
    h, blobs = binpac_blobs(data)
    for pair in pairs:
        sel, sep, path = pair.partition("=")
        if not sep:
            raise SystemExit("expected <entry>=<file>, got %r" % pair)
        i = find_entry(h, sel)
        with open(path, "rb") as f:
            new = f.read()
        note = ""
        if prs and blobs[i][:4] == PRSH_MAGIC and new[:4] != PRSH_MAGIC:
            note = " (%d expanded, PRSH)" % len(new)
            new = prsh_wrap(new)
        print("#%d %s: %d -> %d bytes%s" % (i, h.entries[i][2], len(blobs[i]), len(new), note))
        blobs[i] = new
    out = build_binpac(data[:h.header_size], blobs)
    with open(dst, "wb") as f:
        f.write(out)
    print("%s: %d -> %d bytes (%d -> %d sectors)" % (
        dst, len(data), len(out), (len(data) + 0x7ff) >> 11, (len(out) + 0x7ff) >> 11))


def cmd_prscheck(paths):
    """Every PRSH entry of every self-describing archive: expanded,
    compressed again by prs_compress, expanded again; `!!` where that
    doesn't give the same data."""
    total = ours = theirs = 0
    for p in _walk(paths):
        with open(p, "rb") as f:
            data = f.read()
        try:
            h = BinPac(data)
        except (ValueError, struct.error):
            continue
        n = bad = 0
        for off, size, name, _ in h.entries:
            blob = data[off:off + size]
            if blob[:4] != PRSH_MAGIC:
                continue
            raw = prsh_expand(blob)
            again = prsh_wrap(raw)
            n += 1
            ours += len(again)
            theirs += len(blob)
            if prsh_expand(again) != raw:
                bad += 1
                print("%s %s  !! recompressed entry expands to other data" % (p, name))
        if n:
            total += n
            print("%s: %d PRSH entries recompressed%s" % (p, n, "" if not bad else
                                                           "  !! %d differ" % bad))
    if total:
        print("%d entries; recompressed %d bytes, the disc's %d (%.1f%%)"
              % (total, ours, theirs, 100.0 * ours / theirs))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "roundtrip":
        cmd_roundtrip(args)
        return 0
    if cmd == "replace" and len([a for a in args if a != "--prs"]) >= 3:
        cmd_replace(args[0], args[1], [a for a in args[2:] if a != "--prs"], "--prs" in args)
        return 0
    if cmd == "prscheck":
        cmd_prscheck(args)
        return 0
    if cmd == "info":
        cmd_info(args)
    elif cmd == "list":
        cmd_list(args[0])
    elif cmd == "extract" and len(args) >= 2:
        cmd_extract(args[0], args[1], "--prs" in args[2:])
    elif cmd == "prs" and len(args) == 2:
        with open(args[0], "rb") as f:
            raw = f.read()
        out = prsh_wrap(raw)
        with open(args[1], "wb") as f:
            f.write(out)
        print("%s: %d -> %d bytes" % (args[1], len(raw), len(out)))
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
