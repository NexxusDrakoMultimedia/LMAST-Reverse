"""CSP / CSE 2D layout reader for Let's Make a Soccer Team! (PS2).

A .CSE is a scene file for the game's `cse` 2D sprite library: a picture
list (texture names + UV crop rectangles), a folder tree of scenes, each
scene holding cast nodes (a transform hierarchy), cast faces (quads that
show one crop) and keyframed animation banks. All pointers are offsets
from the start of the CSE; the game's cseProjectAbsolute (0x1ef4e8) adds
the load address to each of them.

A .CSP is a pack of one CSE plus the SVR textures its picture list names:

    u32 count
    count x {u32 offset, u32 size, u32 type, u32 0}   type 2 = CSE, 1 = SVR

See DOC/CSE_FORMAT.md.

Usage:
    python csp.py info    <file.CSP | file.CSE | dir> ...
    python csp.py tree    <file.CSP | file.CSE>
    python csp.py extract <file.CSP | dir> ... <out_dir>
    python csp.py png     <file.CSP | dir> ... <out_dir> [--crops]

Requires: pip install pillow  (only for `png`)
"""
import os
import struct
import sys

import svr

TYPE_SVR, TYPE_CSE = 1, 2


def _u32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def _cstr(b, o):
    return b[o:b.index(b"\0", o)].decode("latin1")


# --- CSP pack -----------------------------------------------------------------

def parse_csp(buf):
    """Return [(offset, size, type)]. Empty file -> []."""
    if not buf:
        return []
    n = _u32(buf, 0)
    out = []
    for i in range(n):
        off, size, typ, zero = struct.unpack_from("<4I", buf, 4 + 16 * i)
        if typ not in (TYPE_SVR, TYPE_CSE) or zero or off + size > len(buf):
            raise ValueError("bad CSP entry %d: %#x %#x %d %d" % (i, off, size, typ, zero))
        out.append((off, size, typ))
    return out


# --- CSE ----------------------------------------------------------------------

class Pic:
    """Picture-list entry: one texture and the UV rectangles cut from it."""
    def __init__(self, b, o):
        name_off, self.n_crops, self.id, crops_off = struct.unpack_from("<IhhI", b, o)
        self.name = _cstr(b, name_off) if name_off else ""
        # u0, v0, u1, v1 in 0..1 texture space
        self.crops = [struct.unpack_from("<4f", b, crops_off + 16 * i)
                      for i in range(self.n_crops)] if crops_off else []


class Face:
    """Cast face (0x28 bytes): a quad showing pattern[k] = (pic, crop).

    colors: packed 0xRRGGBBAA; [0] is the face colour, [1:5] per corner."""
    SIZE = 0x28

    def __init__(self, b, o):
        self.width, self.height, self.flags = struct.unpack_from("<hhI", b, o)
        self.colors = struct.unpack_from("<5I", b, o + 8)
        n, _, pat_off = struct.unpack_from("<hhI", b, o + 0x1C)
        # s16 pic index (bit 15 set: match Pic.id instead), s16 crop index
        self.patterns = [struct.unpack_from("<Hh", b, pat_off + 4 * i)
                         for i in range(n)] if pat_off else []


class Node:
    """Cast node (0x40 bytes): transform, linked as child (+0x34) / sibling (+0x38)."""
    SIZE = 0x40

    def __init__(self, b, o):
        self.offset = o
        (self.x, self.y, self.f08, self.sx, self.sy,
         self.px, self.py) = struct.unpack_from("<7f", b, o)
        self.u1c, self.id, self.face, self.flags, self.u28 = struct.unpack_from("<IhhII", b, o + 0x1C)
        child, sibling = struct.unpack_from("<II", b, o + 0x34)
        self.children = []
        while child:
            node = Node(b, child)
            self.children.append(node)
            child = node._sibling
        self._sibling = sibling

    def walk(self, depth=0):
        yield depth, self
        for c in self.children:
            yield from c.walk(depth + 1)


class Family:
    def __init__(self, b, o):
        n_faces, faces_off, root_off = struct.unpack_from("<3I", b, o)
        self.faces = [Face(b, faces_off + Face.SIZE * i) for i in range(n_faces)]
        self.root = Node(b, root_off) if root_off else None


# Motion.mask bit -> property; tracks are stored in ascending bit order.
TRACK_NAMES = {0: "x", 1: "y", 2: "rot", 3: "sx", 4: "sy", 5: "pattern",
               6: "color", 7: "color0", 8: "color1", 9: "color2", 10: "color3"}


class Track:
    """One animated property. kind: 0 float, 1 colour, 2 integer.
    Keys are {u8 size, u8 interp (0 step, 1 linear, 2 +2 tangent floats),
    u16 frame, value...}."""
    def __init__(self, b, o):
        self.kind, self.start, self.end, n, keys_off = struct.unpack_from("<4HI", b, o)
        self.keys = []
        k = keys_off
        for _ in range(n):
            kflags, frame = struct.unpack_from("<HH", b, k)
            size = kflags & 0xFF
            self.keys.append((frame, kflags >> 8, b[k + 4:k + size]))
            k += size


class Motion:
    def __init__(self, b, o):
        self.mask, n, tracks_off = struct.unpack_from("<3I", b, o)
        self.tracks = [Track(b, tracks_off + 12 * i) for i in range(n)]


class AnimBank:
    def __init__(self, b, o):
        self.u00, self.frames, n, arr = struct.unpack_from("<4I", b, o)
        # one slot per cast node (in family order), 0 = node not animated
        self.motions = [Motion(b, m) if m else None
                        for m in struct.unpack_from("<%dI" % n, b, arr)] if arr else []


class Scene:
    def __init__(self, b, o):
        self.offset = o
        fl_off, n_banks, banks_off = struct.unpack_from("<3I", b, o)
        self.families = []
        if fl_off:
            n_fam, fam_off = struct.unpack_from("<2I", b, fl_off)
            self.families = [Family(b, fam_off + 12 * i) for i in range(n_fam)]
        ptrs = struct.unpack_from("<%dI" % n_banks, b, banks_off) if banks_off else ()
        self.banks = [AnimBank(b, p) if p else None for p in ptrs]


class Folder:
    def __init__(self, b, o):
        self.offset = o
        n, scenes_off, next_off, child_off = struct.unpack_from("<4I", b, o)
        self.scenes = [Scene(b, p) if p else None
                       for p in struct.unpack_from("<%dI" % n, b, scenes_off)] if scenes_off else []
        self.child = Folder(b, child_off) if child_off else None
        self.next = Folder(b, next_off) if next_off else None


class Cse:
    def __init__(self, b):
        pics_off, root_off, self.n_folders, table_off = struct.unpack_from("<4I", b, 0)
        if pics_off != 0x40:
            raise ValueError("not a CSE (picture list at %#x)" % pics_off)
        self.bg_color = _u32(b, 0x10)
        self.width, self.height, self.u18, self.u1a, self.u1c, self.u1e = \
            struct.unpack_from("<6H", b, 0x14)
        n_pics, list_off = struct.unpack_from("<2I", b, pics_off)
        self.pics = [Pic(b, list_off + 12 * i) for i in range(n_pics)]
        self.root = Folder(b, root_off) if root_off else None
        # flat folder table (depth-first: self, child..., next...) at the end
        self.folder_table = list(struct.unpack_from("<%dI" % self.n_folders, b, table_off))
        self.size = table_off + 4 * self.n_folders

    def folders(self):
        def walk(f):
            while f:
                yield f
                if f.child:
                    yield from walk(f.child)
                f = f.next
        return list(walk(self.root))

    def scenes(self):
        return [s for f in self.folders() for s in f.scenes if s]

    def pic_index(self, pic):
        """Resolve a pattern's pic field: bit 15 set means 'the pic whose id
        is the low 15 bits' (cseCastFaceGetPatternData, 0x1f07f8)."""
        if pic & 0x8000:
            for i, p in enumerate(self.pics):
                if p.id == pic & 0x7FFF:
                    return i
            return -1
        return pic if 0 <= pic < len(self.pics) else -1


# --- CLI ----------------------------------------------------------------------

def _iter_files(args, exts):
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                for name in sorted(files):
                    if os.path.splitext(name)[1].upper() in exts:
                        yield os.path.join(root, name)
        else:
            yield a


def load(path):
    """Return (Cse or None, [(pic name, svr bytes)])."""
    with open(path, "rb") as f:
        buf = f.read()
    if path.upper().endswith(".CSE"):
        return Cse(buf), []
    cse, texs = None, []
    for off, size, typ in parse_csp(buf):
        if typ == TYPE_CSE:
            cse = Cse(buf[off:off + size])
        else:
            texs.append(buf[off:off + size])
    names = [p.name for p in cse.pics] if cse else []
    names += ["tex%02d" % i for i in range(len(names), len(texs))]
    return cse, list(zip(names, texs))


def cmd_info(paths):
    for path in _iter_files(paths, (".CSP", ".CSE")):
        name = os.path.basename(path)
        if os.path.getsize(path) == 0:
            print("%-28s !! empty file" % name)
            continue
        try:
            cse, texs = load(path)
        except (ValueError, struct.error) as e:
            print("%-28s !! %s" % (name, e))
            continue
        if cse is None:
            print("%-28s !! no CSE entry" % name)
            continue
        scenes = cse.scenes()
        nodes = sum(1 for s in scenes for fam in s.families if fam.root for _ in fam.root.walk())
        banks = sum(1 for s in scenes for bk in s.banks if bk)
        print("%-28s %dx%d bg=%08x folders=%d scenes=%d nodes=%d anims=%d  %s" % (
            name, cse.width, cse.height, cse.bg_color, len(cse.folders()), len(scenes),
            nodes, banks, " ".join("%s[%d]" % (p.name, p.n_crops) for p in cse.pics)))


def cmd_tree(path):
    cse, texs = load(path)
    print("%s  %dx%d  bg=%08x  header u18..u1e=%d %d %d %#x" % (
        os.path.basename(path), cse.width, cse.height, cse.bg_color,
        cse.u18, cse.u1a, cse.u1c, cse.u1e))
    for i, p in enumerate(cse.pics):
        print("pic %d %-24s id=%d" % (i, p.name, p.id))
        for j, (u0, v0, u1, v1) in enumerate(p.crops):
            print("    crop %-2d (%.4f, %.4f)-(%.4f, %.4f)" % (j, u0, v0, u1, v1))
    for fi, f in enumerate(cse.folders()):
        print("folder %d @%#x: %d scene(s)" % (fi, f.offset, len(f.scenes)))
        for si, s in enumerate(f.scenes):
            if not s:
                continue
            print("  scene %d @%#x" % (si, s.offset))
            for fam in s.families:
                for depth, n in (fam.root.walk() if fam.root else ()):
                    face = fam.faces[n.face] if 0 <= n.face < len(fam.faces) else None
                    desc = ""
                    if face:
                        desc = "  face %dx%d %s" % (face.width, face.height, " ".join(
                            _pattern_name(cse, p, c) for p, c in face.patterns) or "(untextured)")
                    print("    %snode %d  pos=(%g, %g) scale=(%g, %g) pivot=(%g, %g) flags=%08x%s" % (
                        "  " * depth, n.id, n.x, n.y, n.sx, n.sy, n.px, n.py, n.flags, desc))
            for bi, bk in enumerate(s.banks):
                if not bk:
                    continue
                print("    anim %d: %d frames" % (bi, bk.frames))
                for ni, m in enumerate(bk.motions):
                    if not m:
                        continue
                    bits = [i for i in range(32) if m.mask >> i & 1]
                    for bit, t in zip(bits, m.tracks):
                        keys = " ".join("%d:%s" % (fr, _key_value(t.kind, data)) for fr, _, data in t.keys)
                        print("      node %d %-7s %s" % (ni, TRACK_NAMES.get(bit, "bit%d" % bit), keys))


def _pattern_name(cse, pic, crop):
    i = cse.pic_index(pic)
    return "%s#%d" % (cse.pics[i].name if i >= 0 else "pic%#x" % pic, crop)


def _key_value(kind, data):
    if len(data) < 4:
        return data.hex()
    if kind & 0xFF == 1:
        return "%08x" % _u32(data, 0)
    if kind & 0xFF == 2:
        return "%d" % struct.unpack_from("<i", data, 0)[0]
    return "%g" % struct.unpack_from("<f", data, 0)[0]


def cmd_extract(paths, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    for path in _iter_files(paths, (".CSP",)):
        with open(path, "rb") as f:
            buf = f.read()
        base = os.path.splitext(os.path.basename(path))[0]
        entries = parse_csp(buf)
        if not entries:
            continue
        cse, texs = load(path)
        d = os.path.join(out_dir, base)
        os.makedirs(d, exist_ok=True)
        for off, size, typ in entries:
            if typ == TYPE_CSE:
                out = os.path.join(d, base + ".cse")
                with open(out, "wb") as f:
                    f.write(buf[off:off + size])
                print(out)
        for name, data in texs:
            out = os.path.join(d, name + ".svr")
            with open(out, "wb") as f:
                f.write(data)
            print(out)


def cmd_png(paths, out_dir, crops):
    from PIL import Image
    os.makedirs(out_dir, exist_ok=True)
    for path in _iter_files(paths, (".CSP",)):
        if os.path.getsize(path) == 0:
            continue
        base = os.path.splitext(os.path.basename(path))[0]
        cse, texs = load(path)
        for i, (name, data) in enumerate(texs):
            t = svr.parse_svr(data, name)
            img = Image.new("RGBA", (t.width, t.height))
            img.putdata(t.pixels())
            stem = base if name.upper() == base.upper() else "%s_%s" % (base, name)
            out = os.path.join(out_dir, stem + ".png")
            img.save(out)
            print(out)
            if not crops or i >= len(cse.pics):
                continue
            for j, (u0, v0, u1, v1) in enumerate(cse.pics[i].crops):
                box = (round(u0 * t.width), round(v0 * t.height),
                       round(u1 * t.width), round(v1 * t.height))
                if box[2] > box[0] and box[3] > box[1]:
                    img.crop(box).save(os.path.join(out_dir, "%s_%02d.png" % (stem, j)))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info(args)
    elif cmd == "tree" and len(args) == 1:
        cmd_tree(args[0])
    elif cmd == "extract" and len(args) >= 2:
        cmd_extract(args[:-1], args[-1])
    elif cmd == "png" and len(args) >= 2:
        crops = "--crops" in args
        args = [a for a in args if a != "--crops"]
        cmd_png(args[:-1], args[-1], crops)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
