# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""DAT/ACROBATA checker for Let's Make a Soccer Team! (PS2).

DAT/ACROBATA (folder id 13) holds ACROBATAPACKFILE.PAC, the scenes of the
game's 3D event and background system ("Acrobata", built on Acroarts
middleware), and a 9-byte DUMMY.DAT. See DOC/ACROBATA_DIR.md.

The pack is a BINPAC of 875 entries. Each entry is two parts, whose sizes
are the pack's two extra columns:

  ABDA   the scene ("Acroarts Native Data"): a chunk header, an ABDT chunk,
         a POF0 pointer list and EOFC. SIMPRG.REL 0x1a69b0 checks the magic,
         the version word 0x77831b45 (2005080901, "Ver 20050809 R1") and
         the POF0 at +0x18, then relocates the pointers (0x1aaff8).
  ABRS   the resources: the same header (the game checks no version here,
         0x183208, but `info` still compares the word and every entry
         carries it), then wrapped chunks {magic, u32 size, u32 header 0x10, u32 0x80}
         holding Ninja files (NSIF) and textures (GBIX, PVMH), then POF0
         and EOFC.

POF0 is Sega's offset list: each byte's top two bits give the size of a
step (1: 6 bits, 2: 14, 3: 30), counted in words; 0 ends it. Locations and
the pointers they hold are offsets from the chunk's start.

The game doesn't read the pack's own header. The executable carries a
copy of it (SLES 0x3a3b08: {offset, size, ABDA size, ABRS size} per entry)
and a scene-id table (0x55d7a8, 20-byte records: u32 per-language flag,
7 x s16 entry), and opens byte ranges of the pack from folder 13
(0x2fbb38). SIMPRG.REL names every scene id (ACROBATA::getAckName, tables
0x1d7368, 0x22fd58, 0x1d7ea8).

`info` checks every entry and its resources (with ninja.py and svr.py).
`scenes` checks the executable's tables against the pack and lists every
scene id with its entries.

Writing: a texture resource (a GBIX SVR or a PVMH archive) goes back into its scene's
ABRS part at its own size, so nothing else moves: the chunk's size, the POF0 pointer
lists, the entries' offsets and the executable's copy of the pack's header (SLES
0x3a3b08) all stay as they are. `replace` does it for the pictures or files you name,
`textures` lists every texture resource (an entry, its offset in the entry's bytes, its
kind and its textures), and `roundtrip` puts every texture's own picture back through
that path and checks that only the textures' bytes can differ (empirical, all 2,046
texture resources of the PAL pack; see DOC/ACROBATA_DIR.md#writing).

Usage:
    python acrobata.py info      <DAT/ACROBATA>
    python acrobata.py scenes    <DAT/ACROBATA> <ISO>
    python acrobata.py textures  <DAT/ACROBATA | pack>          # every texture resource
    python acrobata.py replace   <in pack> <out pack> <entry>@<hex offset>[.<texture>]=<file> ... [--palette keep]
    python acrobata.py roundtrip <DAT/ACROBATA | pack>          # !! on any difference

`replace` takes a picture (.png, at the texture's size; --palette keep matches it to the
texture's old palette instead of building a new one) or, without a texture number, a
whole resource file of the same size. <entry> is the entry's index or name; the offset
is the one `textures` prints.
"""
import collections
import os
import re
import struct
import sys

from pac import load_header

PACK = "ACROBATAPACKFILE.PAC"
ABDA_VERSION = 0x77831B45           # checked at SIMPRG.REL 0x1a6a34
WRAP_HEADER, WRAP_FLAG = 0x10, 0x80
RESOURCES = (b"NSIF", b"GBIX", b"PVMH")

# Executable tables (SLES_541.51 addresses; gamever.at finds them in
# another build).
EXE_INDEX = 0x3A3B08                # LOADER::AcrobataPackFile_tbl
EXE_SCENES, SCENE_RECORD = 0x55D7A8, 0x14
LANGS = ["jp", "uk", "fr", "ge", "it", "sp", "du"]     # Localize_GetLanguage order
# SIMPRG.REL: getAckName (0x116320) takes ids 1-0x2ce.
SCENE_IDS = 0x2CF
NAME_DIRECT, NAME_LOCAL_INDEX, NAME_LOCAL = 0x1D7368, 0x22FD58, 0x1D7EA8


def pof0_offsets(d, at, end):
    """Decode a POF0 list from d[at:end]; returns word offsets."""
    out, pos, i = [], 0, at
    while i < end:
        c = d[i]
        kind = c >> 6
        if kind == 0:
            break
        if kind == 1:
            step, i = c & 0x3F, i + 1
        elif kind == 2:
            step, i = (c & 0x3F) << 8 | d[i + 1], i + 2
        else:
            step, i = (c & 0x3F) << 24 | d[i + 1] << 16 | d[i + 2] << 8 | d[i + 3], i + 4
        pos += step * 4
        out.append(pos)
    return out


def check_part(d, base, end, magic):
    """Problems with one ABDA or ABRS part d[base:end], and its POF0 count."""
    problems = []
    if d[base:base + 4] != magic:
        return ["no %s" % magic.decode()], 0
    header, _, version, _, pof = struct.unpack_from("<5I", d, base + 8)
    if version != ABDA_VERSION:
        problems.append("%s version %#x" % (magic.decode(), version))
    p = base + pof
    if d[p:p + 4] != b"POF0":
        return problems + ["no POF0 at +%#x" % pof], 0
    psize, phead = struct.unpack_from("<II", d, p + 4)
    eofc = p + 0x10 + psize
    if d[eofc:eofc + 4] != b"EOFC" or eofc + 0x10 != end:
        problems.append("%s doesn't end with EOFC at its size" % magic.decode())
    locs = pof0_offsets(d, p + phead + 4, p + 0x10 + psize)
    data_end = pof
    for loc in locs:
        if loc + 4 > data_end or struct.unpack_from("<I", d, base + loc)[0] >= data_end:
            problems.append("%s POF0 pointer at +%#x outside the data" % (magic.decode(), loc))
            break
    return problems, len(locs)


def resources(d, base):
    """[(magic, offset, size)] of the wrapped chunks in an ABRS part."""
    header, pof = struct.unpack_from("<I", d, base + 8)[0], struct.unpack_from("<I", d, base + 0x18)[0]
    pos, end, out = base + header, base + pof, []
    while pos < end:
        magic, size, head, flag = struct.unpack_from("<4sIII", d, pos)
        if head != WRAP_HEADER or flag != WRAP_FLAG or not size:
            raise ValueError("bad resource chunk %r at +%#x" % (magic, pos - base))
        out.append((magic, pos + head, size))
        pos += head + size
    if pos != end:
        raise ValueError("resources run past POF0")
    return out


def check_resource(magic, blob):
    import ninja
    import svr
    if magic == b"NSIF":
        nf = ninja.NinjaFile(blob)
        return ninja._check_container(nf), "/".join(c[0].decode() for c in nf.chunks
                                                    if c[0] not in (b"NOF0", b"NFN0", b"NEND"))
    if magic == b"GBIX":
        svr.parse_svr(blob)
    elif magic == b"PVMH":
        svr.parse_svm(blob)
    else:
        return ["unknown resource %r" % magic], None
    return [], None


def cmd_info(d):
    path = os.path.join(d, PACK)
    hdr = load_header(path)
    print("%s  BINPAC v%d, %d entries" % (PACK, hdr.version, len(hdr.entries)))
    kinds = collections.Counter()
    groups = collections.Counter()
    pointers = 0
    with open(path, "rb") as f:
        for i, (off, size, name, extra) in enumerate(hdr.entries):
            f.seek(off)
            data = f.read(size)
            problems = []
            if len(extra) != 2 or extra[0] + extra[1] != size:
                problems.append("columns %s don't add up to the size %d" % (extra, size))
                print("%4d %-40s  !! %s" % (i, name, "; ".join(problems)))
                continue
            for base, end, magic in ((0, extra[0], b"ABDA"), (extra[0], size, b"ABRS")):
                pr, n = check_part(data, base, end, magic)
                problems += pr
                pointers += n
            try:
                res = resources(data, extra[0])
            except (ValueError, struct.error) as e:
                res = []
                problems.append(str(e))
            for magic, roff, rsize in res:
                kinds[magic] += 1
                try:
                    pr, what = check_resource(magic, data[roff:roff + rsize])
                    problems += ["%s at +%#x: %s" % (magic.decode(), roff, p) for p in pr]
                    if what:
                        kinds[what] += 1
                except (ValueError, struct.error, KeyError) as e:
                    problems.append("%s at +%#x: %s" % (magic.decode(), roff, e))
            m = re.match(r"(EV_TYPE|EV_PICT|BG_[A-Za-z]+|[A-Za-z]+)", name)
            groups[m.group(1) if m else name] += 1
            if problems:
                print("%4d %-40s  !! %s" % (i, name, "; ".join(problems)))
    print("pointers relocated: %d" % pointers)
    print("resources: %s" % ", ".join("%d %s" % (v, k.decode() if isinstance(k, bytes) else k)
                                       for k, v in sorted(kinds.items(), key=lambda x: -x[1])))
    print("name groups: %s" % ", ".join("%s %d" % kv for kv in groups.most_common()))
    dummy = os.path.join(d, "DUMMY.DAT")
    print("DUMMY.DAT  %d bytes %r" % (os.path.getsize(dummy), open(dummy, "rb").read()))


TEXTURE_MAGICS = (b"GBIX", b"PVMH")


def pack_path(path):
    """The pack file for a DAT/ACROBATA folder, or the path itself."""
    return os.path.join(path, PACK) if os.path.isdir(path) else path


def texture_resources(pack):
    """[(entry index, entry name, magic, offset in the entry's bytes, size)] of every texture
    resource (GBIX, PVMH) in the ABRS parts of the pack's bytes."""
    import pac
    header, blobs = pac.binpac_blobs(pack)
    out = []
    for i, (entry, blob) in enumerate(zip(header.entries, blobs)):
        for magic, off, size in resources(blob, entry[3][0]):
            if magic in TEXTURE_MAGICS:
                out.append((i, entry[2], magic, off, size))
    return out


def replace_resources(pack, edits):
    """The pack's bytes with texture resources replaced: edits is {(entry, offset): new bytes},
    each the size of the resource at that offset of that entry's bytes (what svr's writers
    give). Nothing else changes, so build_binpac lays the pack out as it was (ValueError if
    a size or a place doesn't fit)."""
    import pac
    header, blobs = pac.binpac_blobs(pack)
    blobs = [bytearray(b) for b in blobs]
    by_entry = {}
    for (i, off), new in edits.items():
        by_entry.setdefault(i, {})[off] = new
    for i, offs in by_entry.items():
        if not 0 <= i < len(blobs):
            raise ValueError("entry %d of %d" % (i, len(blobs)))
        have = {off: (magic, size) for magic, off, size in resources(bytes(blobs[i]), header.entries[i][3][0])
                if magic in TEXTURE_MAGICS}
        for off, new in offs.items():
            if off not in have:
                raise ValueError("entry %d has no texture resource at +%#x" % (i, off))
            if len(new) != have[off][1]:
                raise ValueError("entry %d +%#x is %d bytes, not %d" % (i, off, len(new), have[off][1]))
            blobs[i][off:off + len(new)] = new
    return pac.build_binpac(pack[:header.header_size], [bytes(b) for b in blobs])


def replace_pictures(pack, pictures, keep_palette=False):
    """The pack's bytes with pictures put into texture resources: pictures is
    {(entry, offset, texture): RGBA pixels at that texture's size} (svr.replace_pictures)."""
    import pac
    import svr
    header, blobs = pac.binpac_blobs(pack)
    grouped = {}
    for (i, off, slot), pixels in pictures.items():
        grouped.setdefault((i, off), {})[slot] = pixels
    edits = {}
    for (i, off), pics in grouped.items():
        size = next((sz for magic, o, sz in resources(blobs[i], header.entries[i][3][0]) if o == off), None)
        if size is None:
            raise ValueError("entry %d has no resource at +%#x" % (i, off))
        edits[i, off] = svr.replace_pictures(blobs[i][off:off + size], pics, "%s+%#x" % (header.entries[i][2], off),
                                             keep_palette)
    return replace_resources(pack, edits)


def cmd_textures(path):
    import svr
    with open(pack_path(path), "rb") as f:
        pack = f.read()
    import pac
    header, blobs = pac.binpac_blobs(pack)
    n = 0
    for i, name, magic, off, size in texture_resources(pack):
        texs = svr.textures_of(blobs[i][off:off + size], name)
        shape = ", ".join("%dx%d %dbpp" % (t.width, t.height, t.bpp) for t in texs[:4])
        print("%4d %-34s +%#-8x %s %6d bytes  %d texture%s  %s%s" % (
            i, name, off, magic.decode(), size, len(texs), "" if len(texs) == 1 else "s", shape,
            " ..." if len(texs) > 4 else ""))
        n += 1
    print("%d texture resources" % n)


def cmd_replace(src, dst, pairs, keep_palette):
    import pac
    with open(pack_path(src), "rb") as f:
        pack = f.read()
    header, blobs = pac.binpac_blobs(pack)
    edits, pictures = {}, {}
    for pair in pairs:
        sel, sep, path = pair.partition("=")
        where, _, slot = sel.partition(".")
        entry, at, off = where.partition("@")
        if not sep or not at:
            raise SystemExit("expected <entry>@<hex offset>[.<texture>]=<file>, got %r" % pair)
        i = int(entry) if entry.isdigit() else next(
            (k for k, e in enumerate(header.entries) if e[2] == entry), None)
        if i is None:
            raise SystemExit("no entry %r" % entry)
        off = int(off, 16)
        if slot or path.lower().endswith(".png"):
            from PIL import Image
            import svr
            size = next((sz for _, o, sz in resources(blobs[i], header.entries[i][3][0]) if o == off), None)
            if size is None:
                raise SystemExit("entry %d has no resource at +%#x" % (i, off))
            tex = svr.textures_of(blobs[i][off:off + size])[int(slot or 0)]
            img = Image.open(path).convert("RGBA")
            if img.size != (tex.width, tex.height):
                raise SystemExit("%s is %dx%d, the texture %dx%d; scale it first" % (
                    path, img.width, img.height, tex.width, tex.height))
            pictures[i, off, int(slot or 0)] = list(img.get_flattened_data() if hasattr(img, "get_flattened_data")
                                                    else img.getdata())
        else:
            with open(path, "rb") as f:
                edits[i, off] = f.read()
        print("#%d %s +%#x <- %s" % (i, header.entries[i][2], off, path))
    new = pack
    if pictures:
        new = replace_pictures(new, pictures, keep_palette)
    if edits:
        new = replace_resources(new, edits)
    with open(dst, "wb") as f:
        f.write(new)
    print("%s: %d bytes (was %d)" % (dst, len(new), len(pack)))


def cmd_roundtrip(path):
    """Rebuild the pack with every texture put back from its own picture (matched to its own
    palette): the pack keeps its length, every byte outside the textures is as it was, and
    every picture decodes the same. The first failure of each kind is shown."""
    import pac
    import svr
    with open(pack_path(path), "rb") as f:
        pack = f.read()
    header, blobs = pac.binpac_blobs(pack)
    if replace_resources(pack, {}) != pack:
        print("!! rebuilding the pack with no change gives other bytes")
        return 1
    bad, n, textures = 0, 0, 0
    edits, expect = {}, {}
    for i, name, magic, off, size in texture_resources(pack):
        raw = blobs[i][off:off + size]
        texs = svr.textures_of(raw, name)
        pics = {k: t.pixels() for k, t in enumerate(texs)}
        # a texture with its palette outside it (.SVP) has no picture to match here
        pics = {k: px for k, px in pics.items() if texs[k].palette_entries or texs[k].bpp >= 16}
        try:
            new = svr.replace_pictures(raw, pics, name, keep_palette=True) if pics else raw
        except ValueError as e:
            print("%4d %-34s +%#x  !! %s" % (i, name, off, e))
            bad += 1
            continue
        again = svr.textures_of(new, name)
        for k, px in pics.items():
            textures += 1
            if again[k].pixels() != px:
                print("%4d %-34s +%#x texture %d  !! the picture changed" % (i, name, off, k))
                bad += 1
        edits[i, off] = new
        n += 1
    out = replace_resources(pack, edits)
    if len(out) != len(pack):
        print("!! the pack is %d bytes, was %d" % (len(out), len(pack)))
        bad += 1
    changed = 0
    h2, b2 = pac.binpac_blobs(out)
    covered = {}
    for i, name, magic, off, size in texture_resources(pack):
        covered.setdefault(i, []).append((off, off + size))
    for i, (a, b) in enumerate(zip(blobs, b2)):
        if a != b:
            ma, mb = bytearray(a), bytearray(b)
            for lo, hi in covered.get(i, []):
                ma[lo:hi] = bytes(hi - lo)
                mb[lo:hi] = bytes(hi - lo)
            if ma != mb:
                print("%4d %s  !! bytes outside the textures changed" % (i, header.entries[i][2]))
                bad += 1
            changed += 1
    print("%s: %d texture resources, %d textures put back from their own pictures; %d entries "
          "differ in texture bytes only%s" % (os.path.basename(pack_path(path)), n, textures, changed,
                                              "  !! %d problems" % bad if bad else ""))
    return 1 if bad else 0


def scene_names(iso):
    """{scene id: [names]} from SIMPRG.REL (one name, or one per language)."""
    import snr2
    import gamever
    path = os.path.join(iso, "DLL", "SIMPRG.REL")
    m = snr2.Snr2(path)
    targets = m.targets()
    direct, local_index, local = (gamever.at(path, a) for a in (NAME_DIRECT, NAME_LOCAL_INDEX, NAME_LOCAL))

    def ptr(addr):
        v = targets.get(addr)
        return m.cstr(v) if v else None

    out = {}
    for i in range(1, SCENE_IDS):
        n = ptr(direct + 4 * i)
        if n:
            out[i] = [n]
            continue
        k = struct.unpack_from("<i", m.data, local_index + 4 * i)[0]
        out[i] = [ptr(local + 4 * (7 * k + l)) for l in range(len(LANGS))] if k >= 0 else []
    return out


def cmd_scenes(d, iso):
    from sles_disasm import Elf
    import gamever
    exe = gamever.exe_path(iso)
    index, scenes = gamever.at(exe, EXE_INDEX), gamever.at(exe, EXE_SCENES)
    elf = Elf(exe)
    exe = elf.data
    hdr = load_header(os.path.join(d, PACK))
    names = [e[2] for e in hdr.entries]
    o = elf.v2f(index)
    rows = [struct.unpack_from("<4I", exe, o + 16 * i) for i in range(len(hdr.entries))]
    same = sum(1 for r, (off, size, _, x) in zip(rows, hdr.entries) if r == (off, size) + tuple(x))
    line = "executable index (0x%x): %d of %d entries match the pack header" % (
        index, same, len(hdr.entries))
    print(line + ("" if same == len(hdr.entries) else "  !! the game would read the wrong bytes"))
    acks = scene_names(iso)
    o = elf.v2f(scenes)
    used = collections.Counter()
    for i in range(1, SCENE_IDS):
        flag, *ent = struct.unpack_from("<I7h", exe, o + SCENE_RECORD * i)
        idx = ent if flag else ent[:1]
        got = [names[x][:-4] if 0 <= x < len(names) else None for x in idx]
        used.update(idx)
        want = acks.get(i, [])
        mark = "" if [str(g).lower() for g in got] == [str(w).lower() for w in want] else \
            "  !! getAckName says %s" % ", ".join(map(str, want))
        if flag:
            text = "  ".join("%s:%d" % (LANGS[l], x) for l, x in enumerate(idx)) + "  " + \
                re.sub(r"_(jp)$", "_<lang>", got[0] or "?")
        else:
            text = "%d %s" % (idx[0], got[0])
        print("scene %3d  %s%s" % (i, text, mark))
    unused = [i for i in range(len(names)) if not used[i]]
    print("entries used by no scene id: %d%s" % (len(unused), "" if not unused else " (%s)" % ", ".join(
        names[i] for i in unused[:8])))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "scenes" and len(args) == 2:
        cmd_scenes(args[0], args[1])
    elif cmd == "textures" and len(args) == 1:
        cmd_textures(args[0])
    elif cmd == "roundtrip" and len(args) == 1:
        return cmd_roundtrip(args[0])
    elif cmd == "replace" and len(args) >= 3:
        keep = "--palette" in args and args[args.index("--palette") + 1] == "keep"
        rest = [a for k, a in enumerate(args) if a != "--palette" and (k == 0 or args[k - 1] != "--palette")]
        cmd_replace(rest[0], rest[1], rest[2:], keep)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
