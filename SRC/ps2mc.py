# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader and writer for PS2 memory card images (.ps2), as PCSX2 keeps them.

A card image is a run of pages: 512 bytes of data, each followed by a
16-byte spare area holding the data's ECC (12 bytes, 3 per 128-byte chunk)
and 4 zero bytes. An image without spare areas (a whole number of 512-byte
pages) is read and written too. Page 0 is the superblock ("Sony PS2 Memory
Card Format 1.2.0.0"): page size, pages per cluster (2, so 1,024-byte
clusters), the clusters of the allocatable area (alloc_offset, alloc_end),
the root directory's cluster and the indirect FAT clusters (ifc_list).

The FAT has one u32 per allocatable cluster, through the indirect clusters:
bit 31 set is in use, with the next cluster below it (0xffffffff ends a
chain); bit 31 clear is free (0x7fffffff never used, other values freed
and keeping their old link). A directory is a chain of 512-byte entries,
two per cluster: u16 mode (0x8000 exists, 0x20 directory, 0x10 file),
u32 length (bytes, or entries for a directory), created and modified times
(Japan time), u32 first cluster, u32 parent index, name at +0x40. The root
holds the save folders and keeps its entry count in its "." entry; a
folder's count is in its root entry. See DOC/PS2MC_FORMAT.md.

Usage:
    python ps2mc.py info      <card.ps2> ...                  # summary and checks
    python ps2mc.py ls        <card.ps2> [<folder>]           # folders, or a folder's files
    python ps2mc.py get       <card.ps2> <folder>[/<file>] <out>
    python ps2mc.py put       <card.ps2> <out.ps2> <folder>/<file>=<local file> ... [--touch]
    python ps2mc.py mkdir     <card.ps2> <out.ps2> <folder> ...
    python ps2mc.py roundtrip <card.ps2> ...
    python ps2mc.py selftest

`info` checks every page's ECC and every chain (bounds, loops, clusters
used twice, chains too short for their entry) and marks problems with !!.
`get` writes a folder's files into <out>/<folder>/, or one file to <out>.
`put` replaces a file (any size: clusters are added or freed) or creates
it in an existing folder, and writes a new image; --touch sets the
modified time of the file and its folder to now (a new file always gets
it). `mkdir` adds an empty save folder. Neither changes the input image.
`roundtrip` writes every file back with its own data and checks that the
image comes out identical. `selftest` builds a blank card in memory and
creates, grows, shrinks and reads files and folders on it.
"""
import os
import struct
import sys
import time

MAGIC = b"Sony PS2 Memory Card Format "
VERSION = b"1.2.0.0"
PAGE = 0x200
SPARE = 0x10
ECC_CHUNK = 0x80
ENTRY = 0x200

# Superblock offsets.
SB_PAGE_LEN, SB_ALLOC_OFF, SB_ROOT, SB_IFC, SB_BAD = 0x28, 0x34, 0x3c, 0x50, 0xd0
IFC_COUNT = 32

FAT_USED = 0x80000000
FAT_END = 0xffffffff
FAT_FREE = 0x7fffffff

MODE_EXISTS, MODE_HIDDEN, MODE_DIR, MODE_FILE = 0x8000, 0x2000, 0x20, 0x10
MODE_NEW_FILE = 0x8497          # as the PS2 browser writes them (DOC/PS2MC_FORMAT.md)
MODE_NEW_DIR = 0x8427
MODE_ROOT_PARENT = 0xa426       # the root's "..", hidden
NAME_MAX = 31

# PCSX2 leaves page 1 (the second page of the superblock's cluster) with 8
# bytes of its own and the ECC of an empty page; it is never checked or
# written.
PCSX2_PAGE = 1
JST = 9 * 3600


def _parity(b):
    b ^= b >> 4
    b ^= b >> 2
    b ^= b >> 1
    return b & 1


_PARITY = [_parity(b) for b in range(256)]
_COLUMN_MASKS = (0x55, 0x33, 0x0f, 0x00, 0xaa, 0xcc, 0xf0)
_COLUMN = [sum(_PARITY[b & m] << i for i, m in enumerate(_COLUMN_MASKS)) for b in range(256)]


def ecc_chunk(chunk):
    """The 3 ECC bytes of 128 data bytes: column parity and two line parities."""
    cp, l0, l1 = 0x77, 0x7f, 0x7f
    for i, b in enumerate(chunk):
        cp ^= _COLUMN[b]
        if _PARITY[b]:
            l0 ^= ~i
            l1 ^= i
    return bytes((cp, l0 & 0x7f, l1))


def page_spare(data):
    """The 16-byte spare area for a page of data."""
    return b"".join(ecc_chunk(data[i:i + ECC_CHUNK]) for i in range(0, PAGE, ECC_CHUNK)) + bytes(4)


def tod_now():
    """Now as a directory entry time: u8 0, sec, min, hour, day, month, u16 year (Japan)."""
    t = time.gmtime(time.time() + JST)
    return struct.pack("<BBBBBBH", 0, t.tm_sec, t.tm_min, t.tm_hour, t.tm_mday, t.tm_mon,
                       t.tm_year)


def tod_text(raw):
    _, s, mi, h, d, mo, y = struct.unpack("<BBBBBBH", raw)
    return "%04d-%02d-%02d %02d:%02d:%02d" % (y, mo, d, h, mi, s)


class Entry:
    """One 512-byte directory entry and where it lives (directory chain, index)."""
    def __init__(self, raw, first, index):
        self.raw = bytearray(raw)
        self.first, self.index = first, index

    mode = property(lambda self: struct.unpack_from("<H", self.raw, 0)[0])
    length = property(lambda self: struct.unpack_from("<I", self.raw, 4)[0])
    cluster = property(lambda self: struct.unpack_from("<I", self.raw, 0x10)[0])
    created = property(lambda self: bytes(self.raw[8:0x10]))
    modified = property(lambda self: bytes(self.raw[0x18:0x20]))
    name = property(lambda self: self.raw[0x40:0x60].split(b"\0")[0].decode("latin-1"))
    exists = property(lambda self: bool(self.mode & MODE_EXISTS))
    is_dir = property(lambda self: bool(self.mode & MODE_DIR))

    def set(self, length=None, cluster=None, modified=None):
        if length is not None:
            struct.pack_into("<I", self.raw, 4, length)
        if cluster is not None:
            struct.pack_into("<I", self.raw, 0x10, cluster)
        if modified is not None:
            self.raw[0x18:0x20] = modified


def new_entry(mode, length, cluster, parent, name, now):
    raw = bytearray(ENTRY)
    struct.pack_into("<HHI", raw, 0, mode, 0, length)
    raw[8:0x10] = now
    struct.pack_into("<II", raw, 0x10, cluster, parent)
    raw[0x18:0x20] = now
    raw[0x40:0x40 + len(name)] = name.encode("latin-1")
    return raw


class Card:
    def __init__(self, data):
        self.raw = bytearray(data)
        if len(data) % (PAGE + SPARE) == 0 and (len(data) // (PAGE + SPARE)) % 16 == 0:
            self.ecc = True
        elif len(data) % PAGE == 0:
            self.ecc = False
        else:
            raise ValueError("%d bytes is neither whole 528- nor 512-byte pages" % len(data))
        self.raw_page = PAGE + SPARE if self.ecc else PAGE
        self.pages = len(data) // self.raw_page
        sb = self.page(0)
        if not sb.startswith(MAGIC):
            raise ValueError("no superblock (not a PS2 memory card image)")
        (self.page_len, self.ppc, self.ppb, _, self.clusters, self.alloc_off, self.alloc_end,
         self.root) = struct.unpack_from("<4H4I", sb, SB_PAGE_LEN)
        if self.page_len != PAGE or self.ppc != 2:
            raise ValueError("page size %d, %d pages a cluster; only 512 and 2 are known"
                             % (self.page_len, self.ppc))
        if self.clusters * self.ppc != self.pages:
            raise ValueError("superblock says %d clusters, the image holds %d pages"
                             % (self.clusters, self.pages))
        self.csize = PAGE * self.ppc
        self.epc = self.csize // 4                  # FAT entries a cluster
        self.ifc = [c for c in struct.unpack_from("<%dI" % IFC_COUNT, sb, SB_IFC) if c]
        self.fat_clusters = []
        for c in self.ifc:
            self.fat_clusters += [x for x in struct.unpack("<%dI" % self.epc, self.cluster(c))
                                  if x != FAT_END]
        self.fat = []
        for c in self.fat_clusters:
            self.fat += struct.unpack("<%dI" % self.epc, self.cluster(c))
        if len(self.fat) < self.alloc_end:
            raise ValueError("the FAT covers %d clusters, the card %d"
                             % (len(self.fat), self.alloc_end))
        self.fat_dirty = set()

    # --- pages and clusters ---------------------------------------------------

    def page(self, p):
        o = p * self.raw_page
        return bytes(self.raw[o:o + PAGE])

    def write_page(self, p, data):
        if p == PCSX2_PAGE or p < self.alloc_off * self.ppc and p // self.ppc not in \
                set(self.ifc) | set(self.fat_clusters):
            raise ValueError("page %d is in the card's reserved area" % p)
        o = p * self.raw_page
        self.raw[o:o + PAGE] = data
        if self.ecc:
            self.raw[o + PAGE:o + PAGE + SPARE] = page_spare(data)

    def cluster(self, c):
        return b"".join(self.page(c * self.ppc + i) for i in range(self.ppc))

    def write_cluster(self, c, data):
        for i in range(self.ppc):
            self.write_page(c * self.ppc + i, data[i * PAGE:(i + 1) * PAGE])

    # --- the FAT ----------------------------------------------------------------

    def chain(self, first):
        """The clusters (relative to alloc_offset) of the chain starting at
        `first`; ValueError for one that leaves the card, loops or ends on a
        free cluster."""
        out, seen, c = [], set(), first
        while True:
            if not 0 <= c < self.alloc_end:
                raise ValueError("chain from %d reaches cluster %d, outside the card" % (first, c))
            if c in seen:
                raise ValueError("chain from %d loops at cluster %d" % (first, c))
            seen.add(c)
            out.append(c)
            e = self.fat[c]
            if e == FAT_END:
                return out
            if not e & FAT_USED:
                raise ValueError("chain from %d runs into free cluster %d" % (first, c))
            c = e & ~FAT_USED

    def set_fat(self, n, value):
        self.fat[n] = value
        self.fat_dirty.add(n // self.epc)

    def flush(self):
        for k in sorted(self.fat_dirty):
            words = self.fat[k * self.epc:(k + 1) * self.epc]
            self.write_cluster(self.fat_clusters[k], struct.pack("<%dI" % self.epc, *words))
        self.fat_dirty.clear()
        return bytes(self.raw)

    def free_clusters(self):
        return sum(1 for e in self.fat[:self.alloc_end] if not e & FAT_USED)

    def allocate(self):
        for n in range(self.alloc_end):
            if not self.fat[n] & FAT_USED:
                self.set_fat(n, FAT_END)
                return n
        raise ValueError("the card is full")

    def resize_chain(self, first, count):
        """The chain from `first` (None for a new one) made `count` clusters
        long, adding or freeing clusters at its end; returns its clusters."""
        chain = self.chain(first) if first is not None else []
        if len(chain) > count:
            for c in chain[count:]:
                self.set_fat(c, FAT_FREE)
            chain = chain[:count]
            self.set_fat(chain[-1], FAT_END)
        while len(chain) < count:
            n = self.allocate()
            if chain:
                self.set_fat(chain[-1], FAT_USED | n)
            chain.append(n)
        return chain

    def read_chain(self, first, length):
        return b"".join(self.cluster(c + self.alloc_off) for c in self.chain(first))[:length]

    def write_chain(self, chain, data):
        """`data` into the clusters of `chain`; past its end a cluster keeps
        the bytes it held."""
        for i, c in enumerate(chain):
            part = data[i * self.csize:(i + 1) * self.csize]
            if len(part) < self.csize:
                part += self.cluster(c + self.alloc_off)[len(part):]
            self.write_cluster(c + self.alloc_off, part)

    # --- directories --------------------------------------------------------------

    def entries(self, first, count):
        data = self.read_chain(first, count * ENTRY)
        if len(data) < count * ENTRY:
            raise ValueError("directory at %d holds %d entries, its chain %d"
                             % (first, count, len(data) // ENTRY))
        return [Entry(data[i * ENTRY:(i + 1) * ENTRY], first, i) for i in range(count)]

    def write_entry(self, e):
        c = self.chain(e.first)[e.index * ENTRY // self.csize] + self.alloc_off
        data = bytearray(self.cluster(c))
        o = e.index * ENTRY % self.csize
        data[o:o + ENTRY] = e.raw
        self.write_cluster(c, bytes(data))

    def root_dot(self):
        return self.entries(self.root, 1)[0]

    def root_entries(self):
        return self.entries(self.root, self.root_dot().length)

    def folder(self, name):
        """The root entry of save folder `name`."""
        for e in self.root_entries()[2:]:
            if e.exists and e.is_dir and e.name == name:
                return e
        raise ValueError("no folder %r on the card" % name)

    def folder_entries(self, folder):
        return self.entries(folder.cluster, folder.length)

    def find(self, path):
        """(folder entry, file entry or None) for "folder/file"."""
        folder_name, sep, name = path.partition("/")
        if not sep or not name or "/" in name:
            raise ValueError("expected <folder>/<file>, got %r" % path)
        folder = self.folder(folder_name)
        for e in self.folder_entries(folder)[2:]:
            if e.exists and not e.is_dir and e.name == name:
                return folder, e
        return folder, None

    def read_file(self, e):
        return self.read_chain(e.cluster, e.length)

    def _slot(self, first, count, set_count):
        """An entry index for a new entry in the directory at `first` with
        `count` entries: the first deleted one, or a new one at the end
        (growing the directory's chain; `set_count` stores the new count)."""
        for e in self.entries(first, count)[2:]:
            if not e.exists:
                return e.index
        self.resize_chain(first, -(-(count + 1) * ENTRY // self.csize))
        set_count(count + 1)
        return count

    def put(self, path, data, touch=False):
        """Replace or create the file at "folder/file"; returns "replaced" or
        "created"."""
        if not data:
            raise ValueError("%s: a file needs at least one byte" % path)
        folder, e = self.find(path)
        name = path.partition("/")[2]
        if len(name) > NAME_MAX:
            raise ValueError("%s: a name has at most %d characters" % (name, NAME_MAX))
        now = tod_now()
        clusters = -(-len(data) // self.csize)
        if e is not None:
            chain = self.resize_chain(e.cluster, clusters)
            self.write_chain(chain, data)
            e.set(length=len(data), modified=now if touch else None)
            self.write_entry(e)
            done = "replaced"
        else:
            def set_count(n):
                folder.set(length=n)
                self.write_entry(folder)
            index = self._slot(folder.cluster, folder.length, set_count)
            chain = self.resize_chain(None, clusters)
            self.write_chain(chain, data)
            raw = new_entry(MODE_NEW_FILE, len(data), chain[0], 0, name, now)
            self.write_entry(Entry(raw, folder.cluster, index))
            touch, done = True, "created"
        if touch:
            folder.set(modified=now)
            self.write_entry(folder)
        return done

    def mkdir(self, name):
        if not name or "/" in name or len(name) > NAME_MAX:
            raise ValueError("bad folder name %r" % name)
        for e in self.root_entries()[2:]:
            if e.exists and e.name == name:
                raise ValueError("%s is already on the card" % name)
        dot = self.root_dot()

        def set_count(n):
            dot.set(length=n)
            self.write_entry(dot)
        index = self._slot(self.root, dot.length, set_count)
        now = tod_now()
        chain = self.resize_chain(None, 1)
        body = (new_entry(MODE_NEW_DIR, 0, 0, index, ".", now)
                + new_entry(MODE_NEW_DIR, 0, 0, 0, "..", dot.created))
        self.write_chain(chain, body + bytes(self.csize - len(body)))
        self.write_entry(Entry(new_entry(MODE_NEW_DIR, 2, chain[0], 0, name, now),
                               self.root, index))

    # --- checks -----------------------------------------------------------------------

    def check(self):
        """(notes, problems): every page's ECC, every chain's shape."""
        notes, probs = [], []
        if self.ecc:
            bad = []
            for p in range(self.pages):
                if p == PCSX2_PAGE:
                    continue
                o = p * self.raw_page
                data, spare = self.raw[o:o + PAGE], self.raw[o + PAGE:o + PAGE + SPARE]
                if spare == b"\xff" * SPARE and data == b"\xff" * PAGE:
                    continue                                # erased, never written
                if spare != page_spare(data):
                    bad.append(p)
            if bad:
                probs.append("ECC wrong on %d pages (first %s)" % (len(bad), bad[:5]))
        owner = {}

        def claim(chain, what):
            for c in chain:
                if c in owner:
                    probs.append("cluster %d in both %s and %s" % (c, owner[c], what))
                owner[c] = what
        try:
            dot = self.root_dot()
            root_chain = self.chain(self.root)
            claim(root_chain, "the root")
            entries = self.entries(self.root, dot.length)
        except ValueError as err:
            return notes, probs + ["root: %s" % err]
        folders = files = 0
        for f in entries[2:]:
            if not f.exists:
                continue
            if not f.is_dir:
                probs.append("%s: a file in the root" % f.name)
                continue
            folders += 1
            try:
                chain = self.chain(f.cluster)
                claim(chain, f.name)
                inner = self.entries(f.cluster, f.length)
            except ValueError as err:
                probs.append("%s: %s" % (f.name, err))
                continue
            for e in inner[2:]:
                if not e.exists:
                    continue
                files += 1
                what = "%s/%s" % (f.name, e.name)
                try:
                    chain = self.chain(e.cluster)
                except ValueError as err:
                    probs.append("%s: %s" % (what, err))
                    continue
                claim(chain, what)
                if len(chain) * self.csize < e.length:
                    probs.append("%s: %d bytes in %d clusters" % (what, e.length, len(chain)))
        used = sum(1 for e in self.fat[:self.alloc_end] if e & FAT_USED)
        lost = used - len(owner)
        notes.append("%d folders, %d files; %d clusters in use, %d free%s"
                     % (folders, files, used, self.alloc_end - used,
                        "; %d in use by no file" % lost if lost else ""))
        return notes, probs


def load(path):
    with open(path, "rb") as f:
        return Card(f.read())


def blank_card(clusters=8192):
    """A freshly laid-out card, as the real ones are (alloc_offset 41 for 8
    MB, root at cluster 0, two backup blocks at the end); for selftest."""
    ppc, ppb, epc = 2, 16, 256
    fat_clusters = -(-clusters // epc)
    ifc = [8]
    alloc_off = ifc[0] + 1 + fat_clusters
    backup1 = clusters // (ppb // ppc) - 1
    alloc_end = (backup1 - 1) * (ppb // ppc) - alloc_off
    raw = bytearray(b"\xff" * (PAGE + SPARE) * clusters * ppc)
    card = object.__new__(Card)
    card.raw, card.ecc, card.raw_page, card.pages = raw, True, PAGE + SPARE, clusters * ppc
    sb = bytearray(PAGE)
    sb[:len(MAGIC)] = MAGIC
    sb[len(MAGIC):len(MAGIC) + len(VERSION)] = VERSION
    struct.pack_into("<4H6I", sb, SB_PAGE_LEN, PAGE, ppc, ppb, 0xff00, clusters, alloc_off,
                     alloc_end, 0, backup1, backup1 - 1)
    struct.pack_into("<%dI" % IFC_COUNT, sb, SB_IFC, *(ifc + [0] * (IFC_COUNT - len(ifc))))
    struct.pack_into("<%dI" % IFC_COUNT, sb, SB_BAD, *[FAT_END] * IFC_COUNT)
    sb[0x150], sb[0x151] = 2, 0x2b
    for p, data in ((0, bytes(sb)), (1, bytes(PAGE))):
        raw[p * card.raw_page:p * card.raw_page + PAGE] = data
        raw[p * card.raw_page + PAGE:(p + 1) * card.raw_page] = page_spare(data)
    card.page_len, card.ppc, card.ppb, card.clusters = PAGE, ppc, ppb, clusters
    card.alloc_off, card.alloc_end, card.root = alloc_off, alloc_end, 0
    card.csize, card.epc, card.ifc = PAGE * ppc, epc, ifc
    card.fat_clusters = list(range(ifc[0] + 1, ifc[0] + 1 + fat_clusters))
    card.fat, card.fat_dirty = [FAT_FREE] * (fat_clusters * epc), set(range(fat_clusters))
    card.write_cluster(ifc[0], struct.pack("<%dI" % epc, *(
        card.fat_clusters + [FAT_END] * (epc - fat_clusters))))
    card.set_fat(0, FAT_END)
    now = tod_now()
    body = (new_entry(MODE_NEW_DIR, 2, 0, 0, ".", now)
            + new_entry(MODE_ROOT_PARENT, 0, 0, 0, "..", now))
    card.write_cluster(alloc_off, body)
    card.flush()
    return Card(bytes(card.raw))


# --- commands -------------------------------------------------------------------

def cmd_info(paths):
    for path in paths:
        try:
            with open(path, "rb") as f:
                head = f.read(PAGE)
            if head == b"\xff" * PAGE:
                print("%s  unformatted (page 0 is erased)" % path)
                continue
            card = load(path)
            notes, probs = card.check()
        except (ValueError, struct.error, OSError) as e:
            print("%s  !! %s" % (path, e))
            continue
        print("%s  %d KB, %s, %d clusters of %d bytes, allocatable %d-%d"
              % (path, card.clusters * card.csize // 1024,
                 "ECC" if card.ecc else "no ECC", card.clusters, card.csize,
                 card.alloc_off, card.alloc_off + card.alloc_end - 1))
        for n in notes:
            print("  " + n)
        for p in probs:
            print("  !! " + p)


def cmd_ls(path, folder_name=None):
    card = load(path)
    if folder_name is None:
        for e in card.root_entries()[2:]:
            if e.exists:
                print("%-32s %3d entries  %s  mode 0x%04x" % (e.name, e.length,
                                                             tod_text(e.modified), e.mode))
        return
    for e in card.folder_entries(card.folder(folder_name))[2:]:
        if e.exists:
            print("%-32s %8d  %s  mode 0x%04x" % (e.name, e.length, tod_text(e.modified), e.mode))


def cmd_get(path, what, out):
    card = load(path)
    if "/" in what:
        _, e = card.find(what)
        if e is None:
            raise SystemExit("no file %s on the card" % what)
        target = os.path.join(out, e.name) if os.path.isdir(out) else out
        with open(target, "wb") as f:
            f.write(card.read_file(e))
        print("wrote %s (%d bytes)" % (target, e.length))
        return
    folder = card.folder(what)
    os.makedirs(os.path.join(out, what), exist_ok=True)
    for e in card.folder_entries(folder)[2:]:
        if e.exists and not e.is_dir:
            target = os.path.join(out, what, e.name)
            with open(target, "wb") as f:
                f.write(card.read_file(e))
            print("wrote %s (%d bytes)" % (target, e.length))


def _write_out(src, dst, card):
    if os.path.abspath(src) == os.path.abspath(dst):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    data = card.flush()
    notes, probs = Card(data).check()
    if probs:
        raise SystemExit("the new image fails its checks: %s" % "; ".join(probs))
    with open(dst + ".new", "wb") as f:
        f.write(data)
    os.replace(dst + ".new", dst)
    print("wrote %s (%s)" % (dst, notes[0]))


def cmd_put(src, dst, pairs, touch):
    card = load(src)
    for pair in pairs:
        target, sep, local = pair.partition("=")
        if not sep:
            raise SystemExit("expected <folder>/<file>=<local file>, got %r" % pair)
        with open(local, "rb") as f:
            data = f.read()
        try:
            done = card.put(target, data, touch)
        except ValueError as e:
            raise SystemExit(str(e))
        print("%s %s (%d bytes)" % (done, target, len(data)))
    _write_out(src, dst, card)


def cmd_mkdir(src, dst, names):
    card = load(src)
    for name in names:
        try:
            card.mkdir(name)
        except ValueError as e:
            raise SystemExit(str(e))
        print("created %s" % name)
    _write_out(src, dst, card)


def cmd_roundtrip(paths):
    for path in paths:
        try:
            with open(path, "rb") as f:
                data = f.read()
            card = Card(data)
            _, probs = card.check()
            files = 0
            for folder in card.root_entries()[2:]:
                if not (folder.exists and folder.is_dir):
                    continue
                for e in card.folder_entries(folder)[2:]:
                    if e.exists and not e.is_dir:
                        card.put("%s/%s" % (folder.name, e.name), card.read_file(e))
                        files += 1
            out = card.flush()
        except (ValueError, struct.error, OSError) as e:
            print("%s  !! %s" % (path, e))
            continue
        same = "identical" if out == data else "!! %d bytes differ" % sum(
            a != b for a, b in zip(out, data))
        print("%s: %d files written back, image %s%s" % (
            path, files, same, "".join("  !! " + p for p in probs)))


def cmd_selftest():
    def report(what, ok, detail=""):
        print("%-46s %s%s" % (what, "ok" if ok else "!!", " " + detail if detail else ""))

    card = blank_card()
    notes, probs = card.check()
    report("blank card checks", not probs, notes[0])
    card.mkdir("BESLES-54151-G000")
    save = bytes((i * 7 + 3) & 0xff for i in range(646184))
    small = b"icon" * 241
    print("  " + card.put("BESLES-54151-G000/BESLES-54151-G000", save))
    print("  " + card.put("BESLES-54151-G000/icon.sys", small))
    card = Card(card.flush())
    _, e = card.find("BESLES-54151-G000/BESLES-54151-G000")
    report("a 646,184-byte save reads back", card.read_file(e) == save,
           "%d clusters" % len(card.chain(e.cluster)))
    free = card.free_clusters()
    card.put("BESLES-54151-G000/BESLES-54151-G000", save + save)
    card.put("BESLES-54151-G000/BESLES-54151-G000", save[:5000])
    card = Card(card.flush())
    _, e = card.find("BESLES-54151-G000/BESLES-54151-G000")
    report("grown, then shrunk to 5,000 bytes", card.read_file(e) == save[:5000],
           "%d clusters freed" % (card.free_clusters() - free))
    for i in range(7):
        card.put("BESLES-54151-G000/f%d" % i, bytes([i]) * (100 + i))
    card = Card(card.flush())
    folder = card.folder("BESLES-54151-G000")
    ok = all(card.read_file(card.find("BESLES-54151-G000/f%d" % i)[1]) == bytes([i]) * (100 + i)
             for i in range(7))
    report("7 more files: the folder grows a cluster", ok and folder.length == 11,
           "%d entries" % folder.length)
    for i in range(30):
        card.mkdir("FOLDER%02d" % i)
    card = Card(card.flush())
    report("30 more folders: the root grows", card.root_dot().length == 33,
           "%d entries" % card.root_dot().length)
    data = card.flush()
    notes, probs = Card(data).check()
    report("final checks", not probs, notes[0] + "".join("; " + p for p in probs))
    again = Card(data)
    for folder in again.root_entries()[2:]:
        for e in again.folder_entries(folder)[2:]:
            if e.exists:
                again.put("%s/%s" % (folder.name, e.name), again.read_file(e))
    report("every file written back: image identical", again.flush() == data)


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    touch = "--touch" in args
    if touch:
        args.remove("--touch")
    if cmd == "info" and args:
        cmd_info(args)
    elif cmd == "ls" and len(args) in (1, 2):
        cmd_ls(*args)
    elif cmd == "get" and len(args) == 3:
        cmd_get(*args)
    elif cmd == "put" and len(args) >= 3:
        cmd_put(args[0], args[1], args[2:], touch)
    elif cmd == "mkdir" and len(args) >= 3:
        cmd_mkdir(args[0], args[1], args[2:])
    elif cmd == "roundtrip" and args:
        cmd_roundtrip(args)
    elif cmd == "selftest" and not args:
        cmd_selftest()
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
