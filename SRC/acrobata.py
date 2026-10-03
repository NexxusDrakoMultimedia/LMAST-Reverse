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
  ABRS   the resources: the same header (no version check, 0x183208), then
         wrapped chunks {magic, u32 size, u32 header 0x10, u32 0x80}
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

Usage:
    python acrobata.py info   <DAT/ACROBATA>
    python acrobata.py scenes <DAT/ACROBATA> <ISO>
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
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
