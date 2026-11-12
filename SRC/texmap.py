# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""PCSX2 texture hashes of the disc's textures, and a map from a PCSX2
texture pack (LMAST Realism) onto them.

PCSX2 replaces a texture by file name: `<texture>-<palette>-<state>.png`,
for example `11e503e657dc5b20-649acd76961f6744-00001dd4.png`. This tool
computes the same names from the textures on the disc, so a pack's PNGs
can be matched to the disc texture each one replaces (the first step of
putting a pack on the disc; DOC/TEXMAP.md, DOC/SVR_FORMAT.md).

What PCSX2 hashes (read from its source, GSTextureCache.cpp
HashCacheKey::Create / HashTextureLevel, and checked against 173 of 173
crest textures in a PCSX2 dump folder):

  texture   XXH3-64 (seed 0, default secret) of
            - a level smaller than one GS block (4 bit 32x16, 8 bit
              16x16, 32 bit 8x8): the palette index of every texel, one
              byte each, row by row;
            - a 16 bit level: four bytes a texel, RGBA after TEXA
              (R, G, B = 5 bits << 3, A = TA1 if bit 15 else TA0);
            - everything else: the raw 256-byte GS memory blocks of the
              texture, taken in block-row order (the block table of its
              PSM), as the game left them in GS memory. A level the file
              keeps swizzled was uploaded as PSMCT32 words (svr.py); a
              smaller one was uploaded in its own PSM.
  palette   XXH3-64 of the 16 or 256 CLUT entries as little-endian u32
            (R, G, B, A with A 0 to 0x80), 0 for a direct-colour texture
  state     TEX0 bits: PSM (6), TW (4), TH (4), 1 unused, TA0 (8), AEM (1),
            TA1 (8); the file name drops leading zeros of the two hashes

The hash of the texture does not depend on its palette, so one disc
texture shows up under several names when the game draws it with several
palettes (a pack has one PNG per palette it replaces).

XXH3 is not in the Python standard library, so it is written out here
(after Yann Collet's xxHash, BSD-2-Clause) and checked against known
values by `selfcheck`.

Usage:
    python texmap.py selfcheck
    python texmap.py index <DAT> ... [--all] [--csv out.csv]
    python texmap.py match <pack folder> <DAT> ... [--all] [--csv out.csv]
    python texmap.py apply <pack folder> <DAT> <out folder> [--licensed-border N]
                           [--sles <executable>] [--dry-run] [--all-folders]
    python texmap.py name  <name.png>

`index` hashes every texture under the folders (loose files and the
packs `svr.py roundtrip` opens; --all adds the 1.1 GB face pack) and
prints counts. `match` reads a pack folder (a PCSX2 `replacements`
folder: every .png/.bmp under it) and says which disc textures each file
replaces. `apply` writes the pictures that match a disc texture and its
palette exactly into copies of the files that hold them, under <out folder>
(laid out like DAT, for patch_disc.py --copies); the kit pictures, whose
palette the game changes, are left out. --licensed-border N also scales the
original crests of the licensed Italian, Spanish and Dutch clubs (teams 123
to 244) that the pack doesn't replace down by 2N pixels, leaving N more
transparent pixels on every side (--sles names the executable that holds the
licence table; the default is the one in ISO/ next to DAT). A picture whose
alpha never passes 0x80 is taken as the GS's 0 to 0x80. A texture in a CSP
pack goes back with csp.py's replace. `apply` leaves the pack's `Intro`
and `Rival` folders out (Nexxus's scope, 2026-11-12: LMASTER will have
its own intros, and Rival is an upscale made from mipmaps); --all-folders
puts them in. `name` decodes one file name.
"""
import csv
import functools
import hashlib
import os
import re
import struct
import sys

import svr

# --- XXH3-64 -----------------------------------------------------------------

SECRET = bytes.fromhex(
    "b8fe6c3923a44bbe7c01812cf721ad1cded46de9839097db7240a4a4b7b3671f"
    "cb79e64eccc0e578825ad07dccff7221b8084674f743248ee03590e6813a264c"
    "3c2852bb91c300cb88d0658b1b532ea371644897a20df94e3819ef46a9deacd8"
    "a8fa763fe39c343ff9dcbbc7c70b4f1d8a51e04bcdb45931c89f7ec9d9787364"
    "eac5ac8334d3ebc3c581a0fffa1363eb170ddd51b7f0da49d316552629d4689e"
    "2b16be587d47a1fc8ff8b8d17ad031ce45cb3a8f95160428afd7fbcabb4b407e")
M64 = (1 << 64) - 1
P32_1, P32_2, P32_3 = 0x9E3779B1, 0x85EBCA77, 0xC2B2AE3D
P64_1, P64_2, P64_3 = 0x9E3779B185EBCA87, 0xC2B2AE3D27D4EB4F, 0x165667B19E3779F9
P64_4, P64_5 = 0x85EBCA77C2B2AE63, 0x27D4EB2F165667C5
MX1, MX2 = 0x165667919E3779F9, 0x9FB21C651E98DF25

# XXH3-64 of bytes(i % 251 for i in range(n)), from the reference library
XXH3_VECTORS = {
    0: 0x2d06800538d394c2, 1: 0xc44bdff4074eecdb, 3: 0x5f4299fc161c9cbb,
    4: 0x60dab036a58211f2, 8: 0x3a1c2d7c85af88f8, 9: 0xe9612598145bb9dc,
    16: 0x8355e3a6f61770db, 17: 0x9ef341a99de37328, 128: 0x85c6174c7ff4c46b,
    129: 0xec7642b431ba3e5a, 240: 0x375a384d957fe865, 241: 0x02e8cd95421c6d02,
    1024: 0xe5d78bafa45b2aa5, 1025: 0xe95c42288f28186e, 8192: 0x40a71c16bbe37322,
}


def _r64(b, o):
    return struct.unpack_from("<Q", b, o)[0]


def _r32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _rotl(x, r):
    return ((x << r) | (x >> (64 - r))) & M64


def _fold(a, b):
    p = a * b
    return (p & M64) ^ (p >> 64)


def _avalanche(h):
    h ^= h >> 37
    h = (h * MX1) & M64
    return h ^ (h >> 32)


def _avalanche64(h):
    h ^= h >> 33
    h = (h * P64_2) & M64
    h ^= h >> 29
    h = (h * P64_3) & M64
    return h ^ (h >> 32)


def _mix16(d, o, s):
    return _fold(_r64(d, o) ^ _r64(SECRET, s), _r64(d, o + 8) ^ _r64(SECRET, s + 8))


def xxh3_64(d):
    """XXH3 64-bit hash of `d` with seed 0 and the default secret."""
    n = len(d)
    if n == 0:
        return _avalanche64(_r64(SECRET, 56) ^ _r64(SECRET, 64))
    if n <= 3:
        c = (d[0] << 16) | (d[n >> 1] << 24) | d[n - 1] | (n << 8)
        return _avalanche64(c ^ (_r32(SECRET, 0) ^ _r32(SECRET, 4)))
    if n <= 8:
        keyed = (_r32(d, n - 4) + (_r32(d, 0) << 32)) ^ (_r64(SECRET, 8) ^ _r64(SECRET, 16))
        keyed ^= _rotl(keyed, 49) ^ _rotl(keyed, 24)
        keyed = (keyed * MX2) & M64
        keyed ^= (keyed >> 35) + n
        keyed = (keyed * MX2) & M64
        return keyed ^ (keyed >> 28)
    if n <= 16:
        lo = _r64(d, 0) ^ (_r64(SECRET, 24) ^ _r64(SECRET, 32))
        hi = _r64(d, n - 8) ^ (_r64(SECRET, 40) ^ _r64(SECRET, 48))
        swapped = int.from_bytes(lo.to_bytes(8, "little"), "big")
        return _avalanche((n + swapped + hi + _fold(lo, hi)) & M64)
    if n <= 128:
        acc = n * P64_1
        if n > 32:
            if n > 64:
                if n > 96:
                    acc += _mix16(d, 48, 96) + _mix16(d, n - 64, 112)
                acc += _mix16(d, 32, 64) + _mix16(d, n - 48, 80)
            acc += _mix16(d, 16, 32) + _mix16(d, n - 32, 48)
        acc += _mix16(d, 0, 0) + _mix16(d, n - 16, 16)
        return _avalanche(acc & M64)
    if n <= 240:
        acc = n * P64_1
        for i in range(8):
            acc += _mix16(d, 16 * i, 16 * i)
        acc = _avalanche(acc & M64)
        for i in range(8, n // 16):
            acc += _mix16(d, 16 * i, 16 * (i - 8) + 3)
        acc += _mix16(d, n - 16, 136 - 17)
        return _avalanche(acc & M64)
    acc = [P32_3, P64_1, P64_2, P64_3, P64_4, P32_2, P64_5, P32_1]

    def stripe(o, s):
        for i in range(8):
            v = _r64(d, o + 8 * i)
            k = v ^ _r64(SECRET, s + 8 * i)
            acc[i ^ 1] = (acc[i ^ 1] + v) & M64
            acc[i] = (acc[i] + (k & 0xFFFFFFFF) * (k >> 32)) & M64

    per_block = (len(SECRET) - 64) // 8
    block = 64 * per_block
    blocks = (n - 1) // block
    for b in range(blocks):
        for s in range(per_block):
            stripe(b * block + 64 * s, 8 * s)
        for i in range(8):
            a = acc[i]
            a ^= a >> 47
            a ^= _r64(SECRET, len(SECRET) - 64 + 8 * i)
            acc[i] = (a * P32_1) & M64
    for s in range(((n - 1) - block * blocks) // 64):
        stripe(blocks * block + 64 * s, 8 * s)
    stripe(n - 64, len(SECRET) - 64 - 7)
    r = (n * P64_1) & M64
    for i in range(4):
        r += _fold(acc[2 * i] ^ _r64(SECRET, 11 + 16 * i),
                   acc[2 * i + 1] ^ _r64(SECRET, 11 + 16 * i + 8))
    return _avalanche(r & M64)


def cmd_selfcheck():
    bad = [n for n, want in XXH3_VECTORS.items()
           if xxh3_64(bytes(i % 251 for i in range(n))) != want]
    print("XXH3-64: %d of %d test values%s" % (
        len(XXH3_VECTORS) - len(bad), len(XXH3_VECTORS),
        "  !! lengths %s differ" % bad if bad else ""))


# --- the GS memory a texture sits in -------------------------------------------

PSM_CT32, PSM_CT16, PSM_T8, PSM_T4 = 0x00, 0x02, 0x13, 0x14
BPP_PSM = {32: PSM_CT32, 16: PSM_CT16, 8: PSM_T8, 4: PSM_T4}
# PSM -> (block w, h in pixels), (page w, h in blocks), block table
# (GSLocalMemory: blockTable32/16/8/4; the same tables svr.py swizzles with)
GEOMETRY = {
    PSM_CT32: ((8, 8), (8, 4), svr._BLOCK32),
    PSM_CT16: ((16, 8), (4, 8), svr._BLOCK16),
    PSM_T8: ((16, 16), (8, 4), svr._BLOCK32),
    PSM_T4: ((32, 16), (4, 8), svr._BLOCK16),
}
PAGE_PIXELS = {PSM_CT32: (64, 32), PSM_T8: (128, 64), PSM_T4: (128, 128)}
BLOCK_BYTES = 256


@functools.lru_cache(maxsize=16)
def _scatter(w, h, bpp):
    """For a level uploaded as PSMCT32 words (svr.py's swizzled levels):
    the stored word each GS word address holds."""
    pw = w // svr._PAGE[bpp][0]
    cw = pw * 64
    slot = [0] * (w * h * bpp // 32)
    for k in range(len(slot)):
        slot[svr._addr32(k % cw, k // cw, pw)] = k
    return slot


def gs_memory(stored, linear, w, h, bpp):
    """The level as it lies in GS local memory: a swizzled level is the
    stored CT32 words in address order, a smaller one the linear pixels
    written in the level's own PSM. Returns (bytes, pages per row)."""
    if svr.is_swizzled(bpp, w, h):
        return (b"".join(stored[4 * k:4 * k + 4] for k in _scatter(w, h, bpp)),
                w // svr._PAGE[bpp][0])
    psm = BPP_PSM[bpp]
    page_w, page_h = PAGE_PIXELS[psm]
    pages_x, pages_y = -(-w // page_w), -(-h // page_h)
    mem = bytearray(pages_x * pages_y * 8192)
    addr = {PSM_T4: svr._addr4, PSM_T8: svr._addr8, PSM_CT32: svr._addr32}[psm]
    for y in range(h):
        for x in range(w):
            a, i = addr(x, y, pages_x), y * w + x
            if psm == PSM_T8:
                mem[a] = linear[i]
            elif psm == PSM_CT32:
                mem[4 * a:4 * a + 4] = linear[4 * i:4 * i + 4]
            else:
                mem[a >> 1] |= ((linear[i >> 1] >> (4 if i & 1 else 0)) & 15) << (4 if a & 1 else 0)
    return bytes(mem), pages_x


def block_data(mem, pages_x, w, h, psm):
    """The 256-byte blocks of a w x h texture in block-row order."""
    (bw, bh), (pbw, pbh), table = GEOMETRY[psm]
    out = []
    for by in range(-(-h // bh)):
        for bx in range(-(-w // bw)):
            block = ((by // pbh) * pages_x + bx // pbw) * 32 + table[by % pbh][bx % pbw]
            out.append(mem[block * BLOCK_BYTES:(block + 1) * BLOCK_BYTES])
    return b"".join(out)


def expand_ct16(linear, texa):
    """CT16 pixels as the four bytes a texel PCSX2 hashes: R, G, B = 5 bits
    << 3 and A from TEXA (ta0, ta1, aem)."""
    ta0, ta1, aem = texa
    out = bytearray()
    for (c,) in struct.iter_unpack("<H", linear):
        a = ta1 if c & 0x8000 else (0 if aem and c == 0 else ta0)
        out += bytes(((c & 31) << 3, ((c >> 5) & 31) << 3, ((c >> 10) & 31) << 3, a))
    return bytes(out)


def texture_hash(tex, level=0, texa=(0, 0x80, 0)):
    """(hash, how) of a texture level as PCSX2 names it; `how` is "index"
    (palette index bytes), "rgba" (16 bit, TEXA applied) or "blocks" (raw
    GS memory blocks). `texa` is (TA0, TA1, AEM) for 16 bit textures."""
    w, h = tex.level_dims()[level]
    bpp = tex.bpp
    psm = BPP_PSM[bpp]
    _, levels, _, _ = tex.split()
    linear = levels[level]
    (bw, bh), _, _ = GEOMETRY[psm]
    if bpp == 16:
        return xxh3_64(expand_ct16(linear, texa)), "rgba"
    if w < bw or h < bh:
        if bpp == 4:
            linear = bytes((b >> s) & 15 for b in linear for s in (0, 4))
        return xxh3_64(linear), "index"
    start = tex.palette_size + sum(tex.level_sizes()[:level])
    stored = tex.body[start:start + w * h * bpp // 8]
    mem, pages_x = gs_memory(stored, linear, w, h, bpp)
    return xxh3_64(block_data(mem, pages_x, w, h, psm)), "blocks"


def palette_words(tex, texa=(0, 0x80, 0)):
    """The palette as PCSX2 holds it: 16 or 256 u32 entries (R, G, B, A
    bytes), in index order, or None for a texture whose palette is a .SVP."""
    if not tex.palette_entries:
        return None
    raw = tex.body[:tex.palette_size]
    if tex.pf == 0x08:
        raw = expand_ct16(raw, texa)
    words = [raw[i:i + 4] for i in range(0, len(raw), 4)]
    if len(words) == 256:   # CSM1 stores entries 8-15 and 16-23 of each 32 swapped
        words = [words[(i & ~0x18) | ((i & 8) << 1) | ((i & 0x10) >> 1)] for i in range(256)]
    return b"".join(words)


def palette_hash(tex, texa=(0, 0x80, 0)):
    words = palette_words(tex, texa)
    return None if words is None else xxh3_64(words)


# --- PCSX2 file names ------------------------------------------------------------

NAME = re.compile(r"^(?P<tex>[0-9a-f]{1,16})(?:-(?P<clut>[0-9a-f]{1,16}))?"
                  r"(?:-r(?P<rw>\d+)x(?P<rh>\d+))?(?:-mip(?P<mip>\d+))?-(?P<state>[0-9a-f]{8})"
                  r"(?: \(\d+\))?$")


def parse_name(stem):
    """The fields of a PCSX2 texture file name (without extension), or None."""
    m = NAME.match(stem.lower())
    if not m:
        return None
    state = int(m.group("state"), 16)
    return {"tex": int(m.group("tex"), 16),
            "clut": int(m.group("clut"), 16) if m.group("clut") else None,
            "psm": state & 0x3F, "w": 1 << ((state >> 6) & 15), "h": 1 << ((state >> 10) & 15),
            "ta0": (state >> 15) & 0xFF, "aem": (state >> 23) & 1, "ta1": state >> 24,
            "region": (int(m.group("rw")), int(m.group("rh"))) if m.group("rw") else None,
            "mip": int(m.group("mip") or 0)}


def format_name(tex, clut, psm, w, h, texa=(0, 0, 0)):
    """The file name PCSX2 gives a texture (the first two fields drop their
    leading zeros)."""
    state = psm | ((w.bit_length() - 1) << 6) | ((h.bit_length() - 1) << 10)
    state |= (texa[0] << 15) | (texa[2] << 23) | (texa[1] << 24)
    return "%x%s-%08x.png" % (tex, "-%x" % clut if clut is not None else "", state)


# --- the disc ---------------------------------------------------------------------

def disc_index(paths, everything=False):
    """({(texture hash, palette hash or None): [(label, texture)]}, how
    counts, problems) for every texture under `paths`. The language copies
    of a file are hashed once and each gets its label."""
    found, counts, problems, seen = {}, {}, [], {}
    skipped = []
    for label, blob in svr.texture_files(paths, everything, skipped):
        if isinstance(blob, Exception):
            problems.append("%s  !! %s: %s" % (label, type(blob).__name__, blob))
            continue
        if blob[:4] == b"PVPL":
            continue
        key = hashlib.sha1(blob).digest()
        if key not in seen:
            rows = []
            try:
                for slot, tex in enumerate(svr.textures_of(blob, label)):
                    tex.slot = slot     # its place in an SVM, for `apply`
                    h, how = texture_hash(tex)
                    rows.append((tex, h, how, palette_hash(tex)))
            except (ValueError, struct.error, KeyError, IndexError) as e:
                problems.append("%s  !! %s: %s" % (label, type(e).__name__, e))
                rows = []
            seen[key] = rows
            for _, _, how, _ in rows:
                counts[how] = counts.get(how, 0) + 1
        for tex, h, how, ph in seen[key]:
            found.setdefault((h, ph), []).append((label, tex))
    return found, counts, problems + skipped


def summary_lines(found, counts, problems):
    textures = sum(len(v) for v in found.values())
    digest = hashlib.sha1()
    for (h, ph), items in sorted(found.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
        digest.update(b"%x-%x:%d;" % (h, ph or 0, len(items)))
    out = ["%d textures, %d distinct (texture, palette) hashes, %d distinct texture hashes" % (
        textures, len(found), len({h for h, _ in found})),
        "hashed as: %s" % ", ".join("%d %s" % (v, k) for k, v in sorted(counts.items())),
        "digest of all hashes: %s" % digest.hexdigest()[:16]]
    return out + problems


def cmd_index(args):
    everything = "--all" in args
    csv_path = args[args.index("--csv") + 1] if "--csv" in args else None
    paths = [a for i, a in enumerate(args) if not a.startswith("--") and
             (i == 0 or args[i - 1] != "--csv")]
    found, counts, problems = disc_index(paths, everything)
    cmd_selfcheck()
    for line in summary_lines(found, counts, problems):
        print(line)
    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["texture_hash", "palette_hash", "width", "height", "psm", "label", "name"])
            for (h, ph), items in sorted(found.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
                for label, tex in items:
                    wr.writerow(["%x" % h, "" if ph is None else "%x" % ph, tex.width, tex.height,
                                 "%#04x" % BPP_PSM[tex.bpp], label, tex.name])


def pack_files(folder):
    for root, _, files in os.walk(folder):
        for name in sorted(files):
            if os.path.splitext(name)[1].lower() in (".png", ".bmp"):
                yield os.path.join(root, name)


def cmd_match(args):
    everything = "--all" in args
    csv_path = args[args.index("--csv") + 1] if "--csv" in args else None
    plain = [a for i, a in enumerate(args) if not a.startswith("--") and
             (i == 0 or args[i - 1] != "--csv")]
    folder, paths = plain[0], plain[1:]
    found, counts, problems = disc_index(paths, everything)
    by_texture = {}
    for (h, ph), items in found.items():
        by_texture.setdefault(h, []).append((ph, items))
    rows, tally = [], {}

    def count(key):
        tally[key] = tally.get(key, 0) + 1

    for path in pack_files(folder):
        rel = os.path.relpath(path, folder).replace("\\", "/")
        name = parse_name(os.path.splitext(os.path.basename(path))[0])
        if name is None:
            count("status: not a PCSX2 name")
            rows.append((rel, "", "", "not a PCSX2 name", 0, "", ""))
            continue
        hits = by_texture.get(name["tex"])
        writer = ""
        if name["mip"] or name["region"]:
            status = "mip or region file"
        elif not hits:
            status = "no disc texture"
        else:
            exact = [it for ph, items in hits if ph is not None and ph == name["clut"] for it in items]
            targets = exact or [it for _, items in hits for it in items]
            status = "texture and palette" if exact else "texture (palette differs or is a .SVP)"
            # the name's PSM and size are the disc texture's, or the hash is a coincidence
            if not any((t.width, t.height, BPP_PSM[t.bpp]) == (name["w"], name["h"], name["psm"])
                       for _, t in targets):
                status += ", but PSM or size differ"
            writer = holder_kind(sorted(label for label, _ in targets)[0])
        count("status: " + status)
        if writer:
            count("holder: " + writer)
        labels = []
        if hits and not (name["mip"] or name["region"]):
            labels = sorted({label for label, _ in targets})
        rows.append((rel, "%x" % name["tex"], "" if name["clut"] is None else "%x" % name["clut"],
                     status, len(labels), writer, "; ".join(labels[:3])))
    print("%s: %d files" % (folder, len(rows)))
    for k, v in sorted(tally.items(), key=lambda kv: (kv[0].split(":")[0], -kv[1])):
        print("  %5d  %s" % (v, k))
    if csv_path:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            wr = csv.writer(f)
            wr.writerow(["file", "texture_hash", "palette_hash", "status", "disc_textures",
                         "holder", "first_labels"])
            wr.writerows(rows)
    for line in problems:
        print(line)


def holder_kind(label):
    """What holds a texture (the label svr.texture_files gave it), and
    whether a writer can put a changed one back: a plain BINPAC pack or MRG
    goes back with pac.py replace (SVR_FORMAT.md)."""
    path = label.split("#")[0].upper()
    if ".CSP" in label.upper():
        # a texture entry of a CSP pack on its own; one inside a BINPAC has no writer
        if CSP_LABEL.match(label):
            return "CSP pack (csp.py replace)"
        return "CSP pack (no writer)"
    if "ACROBATAPACKFILE" in path:
        return "ACROBATA pack (no writer)"
    if path.endswith((".PAC", ".MRG")):
        return "BINPAC pack (pac.py replace)"
    if path.endswith(".HED") or "#" in label:
        return "KC@P PackData pack (no writer)"
    return "loose file"


def cmd_name(arg):
    parsed = parse_name(os.path.splitext(os.path.basename(arg))[0])
    if parsed is None:
        print("%s  !! not a PCSX2 texture name" % arg)
        return
    psm = {0: "PSMCT32", 2: "PSMCT16", 0x13: "PSMT8", 0x14: "PSMT4"}.get(parsed["psm"], hex(parsed["psm"]))
    print("texture hash %x, palette hash %s, %s %dx%d, TEXA ta0=%d ta1=%d aem=%d%s" % (
        parsed["tex"], "none" if parsed["clut"] is None else "%x" % parsed["clut"], psm,
        parsed["w"], parsed["h"], parsed["ta0"], parsed["ta1"], parsed["aem"],
        ", region %dx%d" % parsed["region"] if parsed["region"] else ""))


# --- putting a pack on the disc ----------------------------------------------------

# svr.texture_files labels: <file>, or <file>#<entry>:<name>[|prs] for a BINPAC
# entry (deeper nesting and the pack kinds without a writer don't match)
LABEL = re.compile(r"^(?P<path>[^#|]+)(?:#(?P<idx>\d+):(?P<name>[^#|]*)(?P<prs>\|prs)?)?$")
# a texture entry of a CSP pack: <file>.CSP#<entry>, the entry's place in the pack
CSP_LABEL = re.compile(r"^(?P<path>[^#|]+\.csp)#(?P<idx>\d+)$", re.I)
WRITERS = ("BINPAC pack (pac.py replace)", "loose file", "CSP pack (csp.py replace)")


def pack_picture(path, size):
    """(pixels, ps2 range) of a pack picture at the disc texture's size, as
    svr.py wants them. A pack made for PCSX2 holds the alpha the GS sees,
    0 to 0x80 (0x80 = opaque). A picture whose most common visible alpha is
    at most 0x80 is taken so and scaled to 0 to 255 first, the exact inverse
    of encode_colors' rounding, with any alpha above 0x80 (the resizing
    that made the mini-crest sheets overshoots to 148) held at 0x80; any
    other picture is taken as 0 to 255."""
    import collections
    from PIL import Image
    img = Image.open(path).convert("RGBA")
    visible = collections.Counter(a for a in img.getchannel("A").getdata() if a)
    ps2 = bool(visible) and visible.most_common(1)[0][0] <= 0x80   # before resizing
    if img.size != size:
        img = img.resize(size, getattr(Image, "Resampling", Image).LANCZOS)
    px = list(img.getdata())
    if ps2:
        px = [(r, g, b, (min(a, 0x80) * 255 + 127) // 128) for r, g, b, a in px]
    return px, ps2


def cmd_apply(args):
    """Write the pack's pictures that match a disc texture exactly (texture
    and palette) into copies of the files that hold them, under an output
    folder laid out like DAT (a mod folder for patch_disc.py)."""
    dry = "--dry-run" in args
    for flag in ("--licensed-border", "--sles"):
        if flag in args and args.index(flag) + 1 >= len(args):
            raise SystemExit("%s needs a value" % flag)
    border = int(args[args.index("--licensed-border") + 1]) if "--licensed-border" in args else 0
    sles = args[args.index("--sles") + 1] if "--sles" in args else None
    plain = [a for i, a in enumerate(args) if not a.startswith("--") and
             (i == 0 or args[i - 1] not in ("--licensed-border", "--sles"))]
    if len(plain) != 3:
        print(__doc__)
        return 1
    folder, dat, out_dir = plain

    def emit(rel, data):
        if dry:
            return
        target = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(target) or ".", exist_ok=True)
        with open(target + ".new", "wb") as f:
            f.write(data)
        os.replace(target + ".new", target)
    apply_pack(folder, dat, border, sles, emit,
               "%s -> %s%s" % (folder, out_dir, "  (dry run: nothing written)" if dry else ""),
               () if "--all-folders" in args else LEFT_OUT)
    return 0


# Pack folders `apply` leaves alone unless --all-folders (Nexxus's scope, 2026-11-12):
# Intro waits for LMASTER's own intros, Rival is an AI upscale made from mipmaps
LEFT_OUT = ("Intro", "Rival")


def apply_pack(folder, dat, border, sles, emit, title, left_out=LEFT_OUT):
    """The work of `apply`: emit(path relative to DAT, new file bytes) for each
    file that changes, and print the tally. `border` > 0 also insets the
    licensed clubs' crests the pack leaves alone (`sles`: the executable with
    the licence table; by default ISO/ beside DAT)."""
    import collections
    import pac
    found, _, problems = disc_index([dat])
    by_texture = {}
    for (h, ph), items in found.items():
        by_texture.setdefault(h, []).append((ph, items))
    tally = collections.Counter()
    wanted = {}   # (label, slot) -> {picture digest: path}
    for path in pack_files(folder):
        name = parse_name(os.path.splitext(os.path.basename(path))[0])
        if name is None:
            tally["not a PCSX2 name"] += 1
            continue
        top = os.path.relpath(path, folder).replace("\\", "/").split("/")[0]
        if top in left_out:
            tally["pack folder %s left out" % top] += 1
            continue
        if name["mip"] or name["region"]:
            tally["mip or region file"] += 1
            continue
        hits = by_texture.get(name["tex"])
        if not hits:
            tally["no disc texture"] += 1
            continue
        exact = [it for ph, items in hits if ph == name["clut"] for it in items]
        if not exact:
            tally["palette differs (kits): not applied"] += 1
            continue
        good = [(label, tex) for label, tex in exact
                if (tex.width, tex.height, BPP_PSM[tex.bpp]) == (name["w"], name["h"], name["psm"])]
        if not good:
            tally["PSM or size differ: not applied"] += 1
            continue
        with open(path, "rb") as f:
            digest = hashlib.sha1(f.read()).digest()
        for label, tex in good:
            wanted.setdefault((label, tex.slot), {}).setdefault(digest, path)
    def writable(label, pics):
        return len(pics) == 1 and (LABEL.match(label) or CSP_LABEL.match(label)) \
            and holder_kind(label) in WRITERS

    # one picture per disc texture; a copy in PRELOAD follows its original
    # (patch_disc.py --copies), unless no other holder of the picture is written
    outside = {d for (label, _), pics in wanted.items()
               if not is_preload(label) and writable(label, pics) for d in pics}
    jobs = {}     # file -> {(entry index, name, prs): {slot: picture path}}
    for (label, slot), pics in sorted(wanted.items()):
        if len(pics) > 1:
            tally["several pictures for one disc texture: not applied"] += 1
            continue
        (digest, pic), = pics.items()
        if is_preload(label) and digest in outside:
            tally["PRELOAD copy (patch_disc.py --copies)"] += 1
            continue
        m = CSP_LABEL.match(label) or LABEL.match(label)
        kind = holder_kind(label)
        if not m or kind not in WRITERS:
            tally["no writer (%s)" % kind] += 1
            continue
        key = (int(m.group("idx")) if m.group("idx") else None,
               m.groupdict().get("name"), bool(m.groupdict().get("prs")))
        jobs.setdefault(m.group("path"), {}).setdefault(key, {})[slot] = pic
        tally["textures to write"] += 1
    if border:      # the licensed clubs' own crests that the pack leaves alone
        import gamever
        sles = sles or gamever.exe_path(os.path.join(os.path.dirname(os.path.abspath(dat)), "ISO"))
        for path, idx in licensed_crests(dat, sles):
            with open(path, "rb") as f:
                head = pac.binpac_blobs(f.read())[0]
            slots = jobs.setdefault(path, {}).setdefault((idx, head.entries[idx][2], False), {})
            if 0 in slots:
                tally["licensed crest: the pack has a picture"] += 1
            else:
                slots[0] = ("inset", border)
                tally["licensed crest: %dpx transparent border" % border] += 1
    written = []
    worst = []
    ps2_pics = 0
    for path, entries in sorted(jobs.items()):
        with open(path, "rb") as f:
            data = f.read()
        blobs, head = None, None
        is_csp = path.upper().endswith(".CSP")
        if is_csp:
            import csp
            csp_ents = csp.parse_csp(data)
        elif any(k[0] is not None for k in entries):
            head, blobs = pac.binpac_blobs(data)
        new_file = data
        for (idx, name, prs), slots in sorted(entries.items(), key=lambda kv: kv[0][0] or 0):
            if is_csp:      # a texture entry of a CSP pack: its bytes, spliced back at the same size
                off, size, kind_ = csp_ents[idx]
                if kind_ != csp.TYPE_SVR:
                    raise SystemExit("%s entry %d is not a texture" % (path, idx))
                raw, name = data[off:off + size], os.path.basename(path) + "#%d" % idx
            else:
                raw = data if idx is None else blobs[idx]
            if idx is not None and not is_csp and head.entries[idx][2] != name:
                raise SystemExit("%s entry %d is %r, not %r" % (path, idx, head.entries[idx][2], name))
            if prs:
                raw = pac.prsh_expand(raw)
            texs = svr.textures_of(raw, name)
            bodies, expect = [None] * len(texs), {}
            for slot, pic in slots.items():
                tex = texs[slot]
                if isinstance(pic, tuple):
                    px, ps2 = inset_pixels(tex, pic[1]), False
                else:
                    px, ps2 = pack_picture(pic, (tex.width, tex.height))
                ps2_pics += ps2
                bodies[slot] = svr.body_from_pixels(
                    tex, px, new_palette=bool(tex.palette_entries) and not isinstance(pic, tuple))
                expect[slot] = px
            new = svr.encode_svm(texs, bodies) if raw[:4] == b"PVMH" else svr.encode_svr(texs[0], bodies[0])
            if len(new) != len(raw):
                raise SystemExit("%s: rebuilt entry is %d bytes, not %d" % (path, len(new), len(raw)))
            for slot, px in expect.items():       # how close the stored picture is to the pack's
                tex = svr.textures_of(new, name)[slot]
                got = tex.pixels()
                far = sum(1 for a, b in zip(px, got)
                          if max(abs(a[0] - b[0]), abs(a[1] - b[1]), abs(a[2] - b[2])) > 16 and a[3] > 16)
                worst.append((far / len(px), path, idx, slot))
            if is_csp:
                new_file = csp.replace_entry(new_file, idx, new)
            elif idx is None:
                new_file = new
            else:
                blobs[idx] = pac.prsh_wrap(new) if prs else new
        if blobs is not None:
            new_file = pac.build_binpac(data[:head.header_size], blobs)
        rel = os.path.relpath(path, dat)
        written.append((rel, len(data), len(new_file)))
        emit(rel, new_file)
    print(title)
    for k, v in sorted(tally.items(), key=lambda kv: (-kv[1], kv[0])):
        print("  %5d  %s" % (v, k))
    print("  %5d  files written, %d textures; %d pictures had the PS2 alpha range" % (
        len(written), sum(len(s) for e in jobs.values() for s in e.values()), ps2_pics))
    grown = [w for w in written if w[1] != w[2]]
    if grown:
        print("  %5d  files changed size (PRSH entries recompressed): patch_disc.py moves them" % len(grown))
    worst.sort(reverse=True)
    print("  stored pictures with over 5%% of their pixels more than 16 off the pack's: %d of %d" % (
        sum(1 for w in worst if w[0] > 0.05), len(worst)))
    for frac, path, idx, slot in worst[:5]:
        print("    %4.1f%%  %s entry %s texture %d" % (100 * frac, path, idx, slot))
    for line in problems:
        print(line)
    return 0


def inset_pixels(tex, border):
    """The texture with its picture scaled down to leave `border` pixels of
    transparent edge all round (the margin LMAST Realism crests have)."""
    from PIL import Image
    w, h = tex.width, tex.height
    px = tex.pixels()
    img = Image.new("RGBA", (w, h))
    img.putdata(px)
    clear = next((p for p in px if p[3] == 0), (0, 0, 0, 0))
    out = Image.new("RGBA", (w, h), clear)
    out.paste(img.resize((w - 2 * border, h - 2 * border), getattr(Image, "Resampling", Image).LANCZOS),
              (border, border))
    return list(out.getdata())


def licensed_crests(dat, sles):
    """(file, entry) of the crest of each licensed club (teams 123 to 244:
    entry = team id - 3, 0SYSTEM_DIR.md) in both crest packs."""
    import uniform
    teams, _ = uniform.licence_table(sles)
    return [(os.path.join(dat, "0SYSTEM", f).replace("\\", "/"), team - 3)
            for f in ("EMBLEM_TEXTURE.PAC", "FLAG_TEXTURE.PAC") for team in sorted(teams)]


def is_preload(label):
    return "/PRELOAD/" in label.replace("\\", "/").upper()


def main(argv):
    cmd, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if cmd == "selfcheck":
        cmd_selfcheck()
    elif cmd == "index" and args:
        cmd_index(args)
    elif cmd == "match" and len(args) >= 2:
        cmd_match(args)
    elif cmd == "apply" and len(args) >= 3:
        return cmd_apply(args)
    elif cmd == "name" and len(args) == 1:
        cmd_name(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
