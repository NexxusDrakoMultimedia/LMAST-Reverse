# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for the stadium collision files of Let's Make a Soccer Team! (PS2):
the 27 entries of GAME/SHADOWCOLLI.PAC, the 38 of GAME/WALLCOLLI.PAC and
TEST3D/SHADOWCOLLI.LBI. Each is an `.lbi`, an echidna link bundle: the
game loads it with CLoader::l_realize_lbi (SLES 0x11bda0), which calls
echidna::LINK_InitBundle (0x14e5a8) and LINK_FixupPointers (0x14e490).
See DOC/LBI_FORMAT.md.

Link bundle (confirmed from LINK_FixupPointers and its helper 0x14e438):

  u32[]   section base table, ended by a zero word (here one word, 0xffffffff,
          which the loader fills in)
  u32     root pointer, tagged: bit 0 set, the top 6 bits a section index,
          bits 2 to 25 an offset in that section
  u32     pointer to the fixup list
  ...     the data
  u32[]   the fixup list: pointers to the places that hold a tagged pointer,
          ended by a zero word

Every file here has the root at 0x10 and its object at 0x14. The object
(empirical, all 66 files consume to the byte):

  +0x00  float[6]  bounding box: min x, y, z, max x, y, z
  +0x18  u32       count of nodes (SHADOWCOLLI) or groups (WALLCOLLI)
  then, per node or group:
    u32 header     SHADOWCOLLI: 0x80000000 | triangle count
                   WALLCOLLI: the triangle count
    float[6]       bounding box
    u32            a colour-like word (0x969696ff, 0x0000ffff, ...)
    triangles      SHADOWCOLLI 0x44 bytes: float normal[3], float d, u32 flag,
                   float vertex[3][3], u32 colour-like word[3]
                   WALLCOLLI   0x38 bytes: the same without the last three

`info` checks the link structure, that the nodes and triangles use the
bytes up to the fixup list exactly, that every normal has length 1, that
every vertex lies on its triangle's plane (normal . vertex + d = 0) and
inside its node's box. Each problem is marked with !!.

Usage:
    python lbi.py info <DAT | file.PAC | file.LBI> ...
    python lbi.py list <file.PAC | file.LBI> ...
"""
import math
import os
import struct
import sys

from pac import BinPac

SHADOW = "SHADOWCOLLI"
WALL = "WALLCOLLI"
TRI = {SHADOW: 0x44, WALL: 0x38}
NODE_FLAG = 0x80000000
ROOT_AT = 0x10
OBJECT_AT = 0x14
PLANE_TOL = 0.01
UNIT_TOL = 0.001
BOX_TOL = 1.0


def decode(ptr):
    """A tagged pointer's (section, offset), as echidna 0x14e438 reads it."""
    return ptr >> 26, ptr & 0x03FFFFFC


def parse(data, kind):
    """Walk one `.lbi` of the given kind. Returns (summary dict, problems)."""
    problems = []
    if len(data) < 0x40 or len(data) % 4:
        return None, ["size %d is not a whole number of words" % len(data)]
    n = len(data) // 4
    w = struct.unpack("<%dI" % n, data)
    f = struct.unpack("<%df" % n, data)
    if w[0] != 0xFFFFFFFF or w[1] != 0:
        problems.append("section table %#x, %#x" % (w[0], w[1]))
    root_sec, root_off = decode(w[2])
    fix_sec, fix_off = decode(w[3])
    if not (w[2] & 1 and w[3] & 1) or root_sec or fix_sec:
        problems.append("root %#x or fixup pointer %#x is not a tagged section-0 pointer" % (w[2], w[3]))
    if root_off != ROOT_AT or w[4] != OBJECT_AT | 1:
        problems.append("root at %#x holds %#x, not a pointer to %#x" % (root_off, w[4], OBJECT_AT))
    if fix_off + 8 > len(data):
        return None, problems + ["fixup list at %#x is past the end" % fix_off]
    fix = []
    i = fix_off // 4
    while i < n and w[i]:
        fix.append(w[i])
        i += 1
    if fix != [ROOT_AT | 1]:
        problems.append("fixup list %s, not just the root" % [hex(x) for x in fix])
    if any(data[(i + 1) * 4:]):
        problems.append("non-zero bytes after the fixup list")
    box = f[OBJECT_AT // 4:OBJECT_AT // 4 + 6]
    pos = OBJECT_AT + 24
    count = w[pos // 4]
    pos += 4
    size = TRI[kind]
    groups = 0
    tris = 0
    worst_unit = worst_plane = 0.0
    outside = 0
    for _ in range(count):
        if pos + 32 > fix_off:
            problems.append("a group runs past the fixup list")
            break
        head = w[pos // 4]
        if (kind == SHADOW) != bool(head & NODE_FLAG):
            problems.append("group header %#x at %#x has the wrong flag for %s" % (head, pos, kind))
            break
        k = head & ~NODE_FLAG
        gbox = f[pos // 4 + 1:pos // 4 + 7]
        pos += 32
        if pos + k * size > fix_off:
            problems.append("group at %#x holds %d triangles, past the fixup list" % (pos, k))
            break
        for t in range(k):
            j = pos // 4
            nx, ny, nz, d = f[j:j + 4]
            vs = [f[j + 5 + 3 * v:j + 8 + 3 * v] for v in range(3)]
            worst_unit = max(worst_unit, abs(math.sqrt(nx * nx + ny * ny + nz * nz) - 1))
            for p in vs:
                worst_plane = max(worst_plane, abs(nx * p[0] + ny * p[1] + nz * p[2] + d))
                if any(p[a] < gbox[a] - BOX_TOL or p[a] > gbox[a + 3] + BOX_TOL for a in range(3)):
                    outside += 1
            pos += size
        groups += 1
        tris += k
    else:
        if pos != fix_off:
            problems.append("the %d groups end at %#x, the fixup list is at %#x" % (groups, pos, fix_off))
    if groups != count and not problems:
        problems.append("%d groups of %d" % (groups, count))
    if worst_unit > UNIT_TOL:
        problems.append("a normal is off unit length by %.4f" % worst_unit)
    if worst_plane > PLANE_TOL:
        problems.append("a vertex is %.3f off its plane" % worst_plane)
    if outside:
        problems.append("%d vertices outside their group's box" % outside)
    return {"groups": groups, "tris": tris, "box": box, "end": fix_off}, problems


def sources(arg):
    """(label, kind, bytes) for every entry of the files `arg` names."""
    paths = []
    if os.path.isdir(arg):
        paths = [os.path.join(arg, "GAME", "SHADOWCOLLI.PAC"), os.path.join(arg, "GAME", "WALLCOLLI.PAC"),
                 os.path.join(arg, "TEST3D", "SHADOWCOLLI.LBI")]
    else:
        paths = [arg]
    for p in paths:
        base = os.path.basename(p).upper()
        kind = WALL if base.startswith(WALL) else SHADOW
        with open(p, "rb") as fh:
            data = fh.read()
        if base.endswith(".PAC"):
            for i, (off, size, _name, _x) in enumerate(BinPac(data).entries):
                yield "%s[%d]" % (p, i), kind, data[off:off + size]
        else:
            yield p, kind, data


def cmd_info(args):
    bad = 0
    for arg in args:
        total = {"entries": 0, "groups": 0, "tris": 0}
        label = arg
        for label, kind, blob in sources(arg):
            try:
                s, problems = parse(blob, kind)
            except (ValueError, struct.error, IndexError) as e:
                s, problems = None, [str(e)]
            if problems:
                bad += 1
                print("%s  %s  !! %s" % (label, kind, "; ".join(problems)))
            if s:
                total["entries"] += 1
                total["groups"] += s["groups"]
                total["tris"] += s["tris"]
        print("%s  entries=%d groups=%d triangles=%d" % (arg, total["entries"], total["groups"], total["tris"]))
    return 1 if bad else 0


def cmd_list(args):
    for arg in args:
        for label, kind, blob in sources(arg):
            s, problems = parse(blob, kind)
            if s:
                b = s["box"]
                print("%s  %-11s groups=%d triangles=%-4d box (%.0f %.0f %.0f) to (%.0f %.0f %.0f)%s" % (
                    label, kind, s["groups"], s["tris"], *b, "  !!" if problems else ""))
            else:
                print("%s  !! %s" % (label, "; ".join(problems)))
    return 0


def main(argv):
    if len(argv) < 3 or argv[1] not in ("info", "list"):
        print(__doc__)
        return 1
    return {"info": cmd_info, "list": cmd_list}[argv[1]](argv[2:])


sys.exit(main(sys.argv))
