"""Ninja (PS2 "NN") model and motion reader for Let's Make a Soccer Team! (PS2).

.SNJ/.SNO (models), .SNM (motions), .SNP (node-tree models) and .SNA (node
names) are Sega NN binary chunk files:

    NSIF  header: chunk count, data offset/size, NOF0 offset/size, version
    NSxx  data chunks; +8 is the offset of the main struct
    NOF0  pointer fix-up table (offsets of every pointer word)
    NFN0  source file name (optional)
    NEND  end

Pointers and NOF0 entries are relative to the data start (NSIF +0xC), not
to the file. Confirmed in SLES_541.51: DataUtility::resolveBinaryPointer
(0x10e338), convertNNDBinaryModelTexture (0x10e570), CModelHandle /
CMotionHandle::get_chunk_data (0x101cb0, 0x1021e8). Object, node, subobject
and meshset layouts come from nnCalcMatrixPaletteNode (0x16c200) and
nnDrawObjectExt (0x199730); vertex lists are raw VIF streams sent as a DMA
ref (nnDrawRigidVerticesProcessVUExt, 0x19de98). See DOC/NINJA_FORMAT.md.

Usage:
    python ninja.py info <file | dir> ... [--prs]
                                              # check every chunk against the layout;
                                              # also NSIF entries in .PAC/.MRG/.HED
                                              # (--prs: expand PRSH entries too, slow)
    python ninja.py dump <file>               # nodes, meshes, motions, names
    python ninja.py obj  <file> <out.obj>     # static mesh in bind pose

Only VU (types 0x5-0x1ff) and PX Plus (0x60000 bits set) vertex lists are
decoded. "Common vertices" lists (vertex-list pointer type 0x10000) are
counted but not exported.
"""
import os
import struct
import sys

NINJA_EXTS = (".SNJ", ".SNO", ".SNM", ".SNP", ".SNA")
OBJECT_CHUNKS = (b"NSOB", b"NSNT", b"NSME")     # all become NNS_OBJECT (0x10e570)
NSIF_SIZE = 0x18
NODE_SIZE = 0x90                                # idx * 9 * 16 at 0x16c248
NODEEX_PLAIN, NODEEX_MESH = 0x80000001, 0x80000002
SUBOBJ_SIZE = 0x14                              # nnDrawObjectExt, 0x199b00
MESHSET_SIZE = 0x24                             # 0x1996e0
EX_SUBOBJ_SIZE = MESHSET_EX_SIZE = 0x20         # opt_nnDrawPriNodeObject helper, 0x142f00
SUBMOTION_SIZE = 0x28
COMMON_VERTICES = 0xff0000                      # vertex-list pointer type test at 0x19969c
PXPLUS = 0x60000   # PX Plus attribute bits (empirical): 0x60000 position,
                   # 0x80000 normal, 0x800000 uv, 0x1000100 uv as V4-16,
                   # 0x10/0x30 per-vertex skin words
FIX12 = 1.0 / 4096                              # 16-bit normals and UVs

# VIF UNPACK vn/vl -> (components, bits)
_UNPACK = {0x0: (1, 32), 0x1: (1, 16), 0x2: (1, 8), 0x4: (2, 32), 0x5: (2, 16),
           0x6: (2, 8), 0x8: (3, 32), 0x9: (3, 16), 0xa: (3, 8), 0xc: (4, 32),
           0xd: (4, 16), 0xe: (4, 8), 0xf: (4, 5)}

# Submotion type -> key size, from every .SNM on the disc (empirical)
_KEY_SIZE = {0x101: 8, 0x201: 8, 0x401: 8,            # T x/y/z: f32 frame, f32 value
             0x812: 4, 0x1012: 4, 0x2012: 4,          # R x/y/z: s16 frame, s16 angle
             0x3812: 8}                               # R xyz: s16 frame, 3 x s16 angle


class NinjaFile:
    def __init__(self, buf):
        if buf[:4] != b"NSIF":
            raise ValueError("not an NSIF file")
        self.buf = buf
        (size, self.count, self.data_off, self.data_size, self.nof0_off,
         self.nof0_size, self.version) = struct.unpack_from("<7I", buf, 4)
        if size != NSIF_SIZE:
            raise ValueError("NSIF size %#x" % size)
        self.chunks = []                       # (tag, file offset, size)
        off = self.data_off
        while True:
            if off + 8 > len(buf):
                raise ValueError("no NEND chunk")
            tag = buf[off:off + 4]
            n = struct.unpack_from("<I", buf, off + 4)[0]
            self.chunks.append((tag, off, n))
            off += 8 + n
            if tag == b"NEND":
                break
        self.trailing = len(buf) - off
        n, = struct.unpack_from("<I", buf, self.nof0_off + 8)
        self.ptrs = set(struct.unpack_from("<%dI" % n, buf, self.nof0_off + 0x10))

    # data-relative accessors
    def u32(self, rel):
        return struct.unpack_from("<I", self.buf, self.data_off + rel)[0]

    def words(self, rel, n, fmt="I"):
        return struct.unpack_from("<%d%s" % (n, fmt), self.buf, self.data_off + rel)

    def cstr(self, rel):
        p = self.data_off + rel
        return self.buf[p:self.buf.index(b"\0", p)].decode("cp932")

    def main_struct(self, chunk):
        return self.u32(chunk[1] - self.data_off + 8)


# --- VIF / vertex lists ---------------------------------------------------------

def vif_unpacks(buf, off, qwc):
    """Yield (vu_addr, comps, bits, count, data offset) for each UNPACK in a VIF
    stream of qwc quadwords. Raises on any command the lists don't use."""
    end = off + qwc * 16
    while off < end:
        code, = struct.unpack_from("<I", buf, off)
        off += 4
        cmd, num, imm = code >> 24, (code >> 16) & 0xff, code & 0xffff
        if cmd & 0x60 == 0x60:
            comps, bits = _UNPACK[cmd & 0xf]
            n = num or 256
            yield imm & 0x3ff, comps, bits, n, off
            off += (n * comps * bits + 31) // 32 * 4
        elif cmd in (0x00, 0x01, 0x14, 0x15, 0x17):   # NOP, STCYCL, MSCAL(F), MSCNT
            pass
        elif cmd == 0x20:                               # STMASK
            off += 4
        elif cmd == 0x30:                               # STROW
            off += 16
        else:
            raise ValueError("VIF command %#04x at %#x" % (cmd, off - 4))
    if off != end:
        raise ValueError("VIF stream overruns its %d qwords" % qwc)


def _vec(buf, off, i, comps, bits, scale=1.0):
    if bits == 32:
        return struct.unpack_from("<%df" % comps, buf, off + 4 * comps * i)
    if bits == 16:
        return tuple(v * scale for v in struct.unpack_from("<%dh" % comps, buf, off + 2 * comps * i))
    return struct.unpack_from("<%dB" % comps, buf, off + comps * i)


class Batch:
    """One VU upload: a vertex strip (or list) of pos/normal/uv/colour."""
    def __init__(self, prim):
        self.prim = prim          # GS PRIM: 3 = triangles, 4 = triangle strip
        self.pos, self.nrm, self.uv, self.col, self.bones = [], [], [], [], []


def decode_vu(buf, off, qwc, vtype):
    """VU lists (types < 0x100). Each batch: UNPACK V4-32 of {nverts,0,0,cost}
    + GIF tag, then either separate pos/normal|colour/uv unpacks at stride 3
    (rigid) or one V4-32 block of 3-4 qwords per vertex (skinned, 0x10-0x30)."""
    batches, cur = [], None
    skinned = vtype & 0x30
    for addr, comps, bits, n, p in vif_unpacks(buf, off, qwc):
        slot = addr % 0x200   # lists double-buffer at VU 0 and 0x200
        if slot == 0:
            nverts = struct.unpack_from("<I", buf, p)[0]
            tag_lo, tag_hi = struct.unpack_from("<II", buf, p + 16)
            if tag_lo & 0x7fff != nverts:
                raise ValueError("GIF NLOOP %d != %d vertices" % (tag_lo & 0x7fff, nverts))
            cur = Batch((tag_hi >> 15) & 7)     # PRIM, GIF tag bits 47-49
            cur.n = nverts
            batches.append(cur)
            if skinned:
                per = (n - 2) // nverts
                if per * nverts != n - 2:
                    raise ValueError("skinned block of %d qwords for %d vertices" % (n - 2, nverts))
                for i in range(nverts):
                    q = struct.unpack_from("<%df" % (4 * per), buf, p + 32 + 16 * per * i)
                    w = struct.unpack_from("<%dI" % (4 * per), buf, p + 32 + 16 * per * i)
                    cur.pos.append(q[0:3])
                    cur.nrm.append(q[4:7])
                    cur.uv.append(q[8:10])
                    if skinned == 0x10:
                        cur.bones.append(((w[10] // 4, q[3]),))
                    elif skinned == 0x20:
                        cur.bones.append(((w[10] // 4, q[3]), (w[11] // 4, q[12])))
                    else:
                        cur.bones.append(((w[3] // 4, 1.0),))
            continue
        if cur is None or n != cur.n:
            raise ValueError("unpack of %d at VU %#x outside a batch" % (n, addr))
        if slot == 2:
            cur.pos = [_vec(buf, p, i, comps, bits) for i in range(n)]
        elif slot == 3 and comps == 4:
            cur.col = [_vec(buf, p, i, comps, bits) for i in range(n)]
        elif slot == 3:
            cur.nrm = [_vec(buf, p, i, comps, bits, FIX12) for i in range(n)]
        elif slot == 4:
            cur.uv = [_vec(buf, p, i, comps, bits, FIX12) for i in range(n)]
        else:
            raise ValueError("unpack to VU slot %d" % slot)
    return batches


def decode_pxplus(buf, off, qwc):
    """PX Plus lists: UNPACK V4-32 {nverts, 4, qwords, 0}, then pos V3-32 /
    normal V3-16 / uv V2-16|V4-16 at stride 4 from VU 4, plus optional per-
    vertex skin words (V2-32 or S-8) that aren't decoded."""
    batches, cur = [], None
    for addr, comps, bits, n, p in vif_unpacks(buf, off, qwc):
        if addr == 0:
            nverts, prim, size, _ = struct.unpack_from("<4I", buf, p)
            if size != 4 * nverts + 4:
                raise ValueError("PX Plus header size %d for %d vertices" % (size, nverts))
            cur = Batch(prim)
            cur.n = nverts
            batches.append(cur)
        elif cur is None or n != cur.n:
            raise ValueError("unpack of %d at VU %#x outside a batch" % (n, addr))
        elif addr == 4:
            cur.pos = [_vec(buf, p, i, comps, bits) for i in range(n)]
        elif addr == 5:
            cur.nrm = [_vec(buf, p, i, comps, bits, FIX12) for i in range(n)]
        elif addr == 6:
            cur.uv = [_vec(buf, p, i, comps, bits, FIX12)[:2] for i in range(n)]
        # higher addresses: skin data after the vertices
    return batches


def strip_triangles(batch):
    """Return (a, b, c) index triples for one batch, wound consistently.

    batch.prim is 4 for a triangle strip (every VU and PX Plus batch on the
    disc) or 3 for a plain triangle list. Positions are in batch.pos.
    """
    if batch.prim == 3:
        return [(i, i + 1, i + 2) for i in range(0, batch.n - 2, 3)]
    tris, pos = [], batch.pos
    for i in range(batch.n - 2):
        # Even triangles already face along the stored normals; odd ones are
        # reversed by the strip, so swap two corners. Parity is the position
        # in the strip, so degenerate triangles still count.
        a, b, c = (i, i + 1, i + 2) if i % 2 == 0 else (i + 1, i, i + 2)
        # Repeated vertices join strips and draw nothing.
        if pos[a] == pos[b] or pos[b] == pos[c] or pos[a] == pos[c]:
            continue
        tris.append((a, b, c))
    return tris


# --- objects --------------------------------------------------------------------

class Mesh:
    def __init__(self, node, matrix, material, vtx_index, vtype, flags, batches):
        self.node, self.matrix, self.material = node, matrix, material
        self.vtx_index, self.vtype, self.flags, self.batches = vtx_index, vtype, flags, batches


class Node:
    def __init__(self, flags, matrix, parent, child, sibling, trs, inv):
        self.flags, self.matrix = flags, matrix
        self.parent, self.child, self.sibling = parent, child, sibling
        self.t, self.r, self.s = trs
        self.inv = inv


class NinjaObject:
    def __init__(self, nf, rel):
        self.nf, self.problems = nf, []
        w = nf.words(rel, 17)
        self.center, self.radius = w[0:3], struct.unpack("<f", struct.pack("<I", w[3]))[0]
        (self.nmat, self.pmat, self.nvtx, self.pvtx, self.nprim, self.pprim,
         self.nnode, self.depth, self.pnode, self.nmtx, self.nsub, self.psub,
         self.ntex) = w[4:17]
        # Node-pointer objects (L/M/S_PLAYER, LMS_PLAYER.SNP): pNodeList holds
        # pointers to NNS_NODEEX; drawn by opt_nnDrawPriNodeObject (0x143158).
        self.ex = self.nnode > 0 and self.pnode in nf.ptrs
        self.type = nf.u32(rel + 0x44) if self.ex else 0
        self.nodes, self.meshes, self.common = [], [], 0
        self._vtx_cache = {}
        if self.ex:
            self._parse_ex()
        else:
            self._parse_plain()

    def _problem(self, msg):
        self.problems.append(msg)

    def _vertex_list(self, ptr_entry):
        """ptr_entry: data offset of a {type, ptr} NNS_VTXLISTPTR."""
        if ptr_entry in self._vtx_cache:
            return self._vtx_cache[ptr_entry]
        nf = self.nf
        ptype, vl = nf.words(ptr_entry, 2)
        if ptype & COMMON_VERTICES:
            self.common += 1
            res = (ptype, None)
        else:
            vtype, qwc, data = nf.words(vl, 3)
            try:
                if vtype & PXPLUS == PXPLUS:
                    res = (vtype, decode_pxplus(nf.buf, nf.data_off + data, qwc))
                elif vtype < 0x200:     # 0x100 (9 files) doesn't change the layout
                    res = (vtype, decode_vu(nf.buf, nf.data_off + data, qwc, vtype))
                else:
                    raise ValueError("vertex list type %#x" % vtype)
            except (ValueError, KeyError, struct.error) as e:
                self._problem("vertex list %#x: %s" % (vl, e))
                res = (vtype, None)
        self._vtx_cache[ptr_entry] = res
        return res

    def _parse_plain(self):
        nf = self.nf
        for i in range(self.nnode):
            p = self.pnode + NODE_SIZE * i
            flags, mtx, parent, child, sibling, _ = struct.unpack_from("<I5h", nf.buf, nf.data_off + p)
            trs = (nf.words(p + 0xc, 3, "f"), nf.words(p + 0x18, 3, "i"), nf.words(p + 0x24, 3, "f"))
            self.nodes.append(Node(flags, mtx, parent, child, sibling, trs, nf.words(p + 0x30, 16, "f")))
        for n in self.nodes:
            for link in (n.parent, n.child, n.sibling):
                if not -1 <= link < self.nnode:
                    self._problem("node link %d out of range" % link)
            if not -1 <= n.matrix < self.nmtx:
                self._problem("node matrix %d >= %d" % (n.matrix, self.nmtx))
        for s in range(self.nsub):
            stype, nmesh, pmesh = nf.words(self.psub + SUBOBJ_SIZE * s, 3)
            for m in range(nmesh):
                ms = pmesh + MESHSET_SIZE * m
                node, mtx, mat, vtx, prim = nf.words(ms + 0x10, 5)
                # NSME parts with no nodes of their own index an external
                # skeleton (the .SNP node tree), so only check other objects.
                if (node >= self.nnode and self.nnode) or mat >= self.nmat or vtx >= self.nvtx or prim >= max(self.nprim, 1):
                    self._problem("meshset %d/%d index out of range" % (s, m))
                    continue
                vtype, batches = self._vertex_list(self.pvtx + 8 * vtx)
                self.meshes.append(Mesh(node, mtx, mat, vtx, vtype, stype, batches))

    def _parse_ex(self):
        nf = self.nf
        ptrs = nf.words(self.pnode, self.nnode)
        index = {p: i for i, p in enumerate(ptrs)}
        for i, p in enumerate(ptrs):
            ext, flags, mtx, own = nf.words(p, 4)[0], nf.u32(p + 4), *struct.unpack_from(
                "<2h", nf.buf, nf.data_off + p + 8)
            if ext not in (NODEEX_PLAIN, NODEEX_MESH):
                self._problem("node %d: extended type %#x" % (i, ext))
                continue
            links = [index.get(v, -1) if v else -1 for v in nf.words(p + 0xc, 3)]
            trs = (nf.words(p + 0x18, 3, "f"), nf.words(p + 0x24, 3, "i"), nf.words(p + 0x30, 3, "f"))
            self.nodes.append(Node(flags, mtx, *links, trs, nf.words(p + 0x40, 16, "f")))
            self.nodes[-1].skeleton_index = own
            if ext != NODEEX_MESH:
                continue
            nmat, pmat, nvtx, pvtx, nprim, pprim, nsub, psub = nf.words(p + 0xa0, 8)
            for s in range(nsub):
                sb = psub + EX_SUBOBJ_SIZE * s
                stype, mat = nf.words(sb, 2)
                nmesh, pmesh = nf.words(sb + 0xc, 2)
                for m in range(nmesh):
                    mflags, mmtx, vtx = nf.words(pmesh + MESHSET_EX_SIZE * m, 3)
                    if mat >= nmat or vtx >= nvtx:
                        self._problem("node %d meshset %d/%d index out of range" % (i, s, m))
                        continue
                    vtype, batches = self._vertex_list(pvtx + 8 * vtx)
                    self.meshes.append(Mesh(i, mmtx, mat, vtx, vtype, mflags | stype, batches))


# --- motions and small chunks ----------------------------------------------------

class Motion:
    def __init__(self, nf, rel):
        self.type = nf.u32(rel)
        self.start, self.end = nf.words(rel + 4, 2, "f")
        nsub, psub = nf.words(rel + 0xc, 2)
        self.fps = nf.words(rel + 0x14, 1, "f")[0]
        self.subs, self.problems = [], []
        for i in range(nsub):
            s = psub + SUBMOTION_SIZE * i
            stype, iptype, node = nf.words(s, 3)
            start, end, loop0, loop1 = nf.words(s + 0xc, 4, "f")
            nkey, keysize, pkey = nf.words(s + 0x1c, 3)
            want = _KEY_SIZE.get(stype)
            if want is None:
                self.problems.append("submotion %d: type %#x" % (i, stype))
            elif keysize != want:
                self.problems.append("submotion %d: key size %d, want %d" % (i, keysize, want))
            if pkey + nkey * keysize > nf.data_size:
                self.problems.append("submotion %d: keys past end of data" % i)
            self.subs.append((stype, iptype, node, start, end, nkey, keysize))


def texture_names(nf, rel):
    n, p = nf.words(rel, 2)
    return [nf.cstr(nf.u32(p + 0x14 * i + 4)) for i in range(n)]


def node_names(nf, rel):
    kind, n, p = nf.words(rel, 3)
    return kind, [(nf.u32(p + 8 * i), nf.cstr(nf.u32(p + 8 * i + 4))) for i in range(n)]


# --- matrices ----------------------------------------------------------------

def invert(m):
    """Inverse of a 4x4 affine matrix stored row-vector style (translation in
    m[12:15], as the node inverse matrices are)."""
    a = [m[0:3], m[4:7], m[8:11]]
    det = (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
           - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
           + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    if abs(det) < 1e-12:
        raise ValueError("singular matrix")
    inv = [[0.0] * 3 for _ in range(3)]
    for r in range(3):
        for c in range(3):
            r1, r2, c1, c2 = (c + 1) % 3, (c + 2) % 3, (r + 1) % 3, (r + 2) % 3
            inv[r][c] = (a[r1][c1] * a[r2][c2] - a[r1][c2] * a[r2][c1]) / det
    t = m[12:15]
    ti = [-sum(t[k] * inv[k][c] for k in range(3)) for c in range(3)]
    return inv, ti


def bind_space(obj, node):
    """Matrix taking a mesh on `node` to model space in the bind pose, or None.

    The palette entry is world x inverse-bind (+0x30), which is the identity
    in the bind pose, so vertices are already in model space. Flag 0x8 nodes
    skip the inverse-bind (nnCalcMatrixPaletteNode, 0x16c41c) and so draw in
    their world frame; on the disc they all also have flags 0x7 (no T/R/S of
    their own), so that frame is their nearest non-0x8 ancestor's bind world.
    """
    n = obj.nodes[node]
    if not n.flags & 8:
        return None
    while n.flags & 8:
        if n.flags & 7 != 7:
            raise ValueError("node %d: flag 0x8 with its own transform" % node)
        if n.parent < 0:
            return None
        n = obj.nodes[n.parent]
    return invert(n.inv)


def transform(p, mat):
    inv, t = mat
    return tuple(p[0] * inv[0][c] + p[1] * inv[1][c] + p[2] * inv[2][c] + t[c] for c in range(3))


# --- file walking -------------------------------------------------------------

def _iter_blobs(args, prs=False):
    """Yield (label, bytes) for loose Ninja files and for NSIF entries inside
    BINPAC/KC@P containers (PRSH-compressed entries only with prs=True)."""
    import pac
    for a in args:
        if os.path.isdir(a):
            for root, _, files in os.walk(a):
                yield from _iter_blobs([os.path.join(root, n) for n in sorted(files)], prs)
            continue
        label = os.path.relpath(a)
        if a.upper().endswith(NINJA_EXTS):
            with open(a, "rb") as f:
                yield label, f.read()
            continue
        hdr = pac.load_header(a)
        if hdr is None:
            continue
        data = pac.data_path(a, hdr)
        # Some .HED files repeat the inline header of their .PAC; skip them.
        if data is None or (data != a and pac.load_header(data) is not None):
            continue
        with open(data, "rb") as f:
            buf = f.read()
        for i, (off, size, name, _) in enumerate(hdr.entries):
            blob = buf[off:off + size]
            if blob[:4] == b"PRSH" and prs:
                blob = pac.prsh_expand(blob)
            if blob[:4] == b"NSIF":
                yield "%s#%d%s" % (label, i, ":" + name if name else ""), blob


def _check_container(nf):
    out = []
    if nf.data_off != 0x20:
        out.append("data offset %#x" % nf.data_off)
    if nf.data_off + nf.data_size != nf.nof0_off:
        out.append("NOF0 at %#x, data ends at %#x" % (nf.nof0_off, nf.data_off + nf.data_size))
    data_chunks = [c for c in nf.chunks if c[0] not in (b"NOF0", b"NFN0", b"NEND")]
    if len(data_chunks) != nf.count:
        out.append("NSIF count %d, %d data chunks" % (nf.count, len(data_chunks)))
    nof0 = [c for c in nf.chunks if c[0] == b"NOF0"]
    if len(nof0) != 1 or nof0[0][1] != nf.nof0_off or nof0[0][2] + 8 != nf.nof0_size:
        out.append("NOF0 chunk doesn't match NSIF")
    if nf.trailing:
        out.append("%d bytes after NEND" % nf.trailing)
    if nf.version != 1:
        out.append("version %d" % nf.version)
    for p in sorted(nf.ptrs):
        if p & 3 or p + 4 > nf.data_size:
            out.append("NOF0 entry %#x outside data" % p)
            break
        if nf.u32(p) >= nf.data_size:
            out.append("pointer at %#x -> %#x outside data" % (p, nf.u32(p)))
            break
    return out


def cmd_info(paths, prs=False):
    for label, blob in _iter_blobs(paths, prs):
        try:
            nf = NinjaFile(blob)
            problems = _check_container(nf)
            parts = [b"/".join(c[0] for c in nf.chunks).decode()]
            for c in nf.chunks:
                rel = nf.main_struct(c) if c[2] >= 4 and c[0] not in (b"NOF0", b"NEND", b"NFN0") else None
                if c[0] in OBJECT_CHUNKS:
                    o = NinjaObject(nf, rel)
                    problems += o.problems
                    verts = sum(b.n for m in o.meshes if m.batches for b in m.batches)
                    types = sorted({m.vtype for m in o.meshes})
                    parts.append("nodes=%d%s meshes=%d verts=%d vtx=%s" % (
                        o.nnode, "(ex %#x)" % o.type if o.ex else "", len(o.meshes), verts,
                        ",".join("%#x" % t for t in types)))
                    if o.common:
                        parts.append("common-vertex lists=%d" % o.common)
                elif c[0] == b"NSMO":
                    m = Motion(nf, rel)
                    problems += m.problems
                    parts.append("motion %#x frames %g-%g @%gfps sub=%d" % (
                        m.type, m.start, m.end, m.fps, len(m.subs)))
                elif c[0] == b"NSTL":
                    parts.append("tex=%d" % len(texture_names(nf, rel)))
                elif c[0] == b"NSNN":
                    parts.append("names=%d" % len(node_names(nf, rel)[1]))
            line = "%-44s %s" % (label, "  ".join(parts))
        except (ValueError, struct.error, UnicodeDecodeError) as e:
            line, problems = "%-44s" % label, [str(e)]
        print(line + ("  !! " + "; ".join(problems) if problems else ""))


def cmd_dump(path):
    with open(path, "rb") as f:
        nf = NinjaFile(f.read())
    print("NSIF count=%d data=%#x+%#x NOF0=%#x (%d ptrs) version=%d" % (
        nf.count, nf.data_off, nf.data_size, nf.nof0_off, len(nf.ptrs), nf.version))
    for c in nf.chunks:
        print("%s at %#x size %#x" % (c[0].decode(), c[1], c[2]))
        if c[0] == b"NFN0":
            print("  name: %s" % nf.buf[c[1] + 0x10:c[1] + 8 + c[2]].rstrip(b"\0").decode("cp932"))
            continue
        if c[0] in (b"NOF0", b"NEND"):
            continue
        rel = nf.main_struct(c)
        if c[0] in OBJECT_CHUNKS:
            o = NinjaObject(nf, rel)
            print("  center=(%g %g %g) radius=%g mat=%d vtx=%d prim=%d nodes=%d depth=%d "
                  "mtx=%d sub=%d tex=%d%s" % (*o.center, o.radius, o.nmat, o.nvtx, o.nprim,
                                             o.nnode, o.depth, o.nmtx, o.nsub, o.ntex,
                                             " ex-type=%#x" % o.type if o.ex else ""))
            for i, n in enumerate(o.nodes):
                print("  node %3d flags=%#08x mtx=%3d parent=%3d child=%3d sib=%3d "
                      "T=(%.4g %.4g %.4g) R=(%d %d %d) S=(%.4g %.4g %.4g)" % (
                          i, n.flags, n.matrix, n.parent, n.child, n.sibling, *n.t, *n.r, *n.s))
            for m in o.meshes:
                nv = sum(b.n for b in m.batches) if m.batches else 0
                print("  mesh node=%d mtx=%d mat=%d vtxlist=%d type=%#x flags=%#x batches=%s verts=%d" % (
                    m.node, m.matrix, m.material, m.vtx_index, m.vtype, m.flags,
                    len(m.batches) if m.batches is not None else "-", nv))
            for p in o.problems:
                print("  !! " + p)
        elif c[0] == b"NSMO":
            m = Motion(nf, rel)
            print("  type=%#x frames %g-%g fps=%g" % (m.type, m.start, m.end, m.fps))
            for s in m.subs:
                print("  sub type=%#06x ip=%#07x node=%3d frames %g-%g keys=%d x %d" % s)
        elif c[0] == b"NSTL":
            for i, n in enumerate(texture_names(nf, rel)):
                print("  tex %2d %s" % (i, n))
        elif c[0] == b"NSNN":
            kind, names = node_names(nf, rel)
            print("  %s" % ("sorted" if kind == 0 else "linear"))
            for i, n in names:
                print("  %3d %s" % (i, n))


def cmd_obj(path, out):
    with open(path, "rb") as f:
        nf = NinjaFile(f.read())
    lines, nv = ["# %s" % os.path.basename(path)], 0
    for c in nf.chunks:
        if c[0] not in OBJECT_CHUNKS:
            continue
        o = NinjaObject(nf, nf.main_struct(c))
        for k, m in enumerate(o.meshes):
            if not m.batches:
                continue
            world = bind_space(o, m.node)
            lines.append("o mesh%d_node%d_mat%d" % (k, m.node, m.material))
            for b in m.batches:
                pos = [transform(p, world) for p in b.pos] if world else b.pos
                lines += ["v %.6f %.6f %.6f" % p for p in pos]
                lines += ["vt %.6f %.6f" % (u, 1 - v) for u, v in b.uv] if b.uv else []
                for a, bb, cc in strip_triangles(b):
                    if b.uv:
                        lines.append("f %d/%d %d/%d %d/%d" % tuple(
                            x for i in (a, bb, cc) for x in (nv + i + 1, nv + i + 1)))
                    else:
                        lines.append("f %d %d %d" % (nv + a + 1, nv + bb + 1, nv + cc + 1))
                nv += len(pos)
    with open(out, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("%s: %d vertices" % (out, nv))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 1
    cmd, args = argv[1], argv[2:]
    if cmd == "info":
        cmd_info([a for a in args if a != "--prs"], "--prs" in args)
    elif cmd == "dump" and len(args) == 1:
        cmd_dump(args[0])
    elif cmd == "obj" and len(args) == 2:
        cmd_obj(args[0], args[1])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
