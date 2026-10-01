# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Patch edited game files into the disc image, DATA.CVM or DATA.ISO, for
Let's Make a Soccer Team! (PS2). Files keep their sectors: a file may
change size only inside its last sector.

DATA.CVM is a ROFSBLD container: a CVMH/ZONE header, then an ISO9660 image
whose table of contents (the volume descriptor and directory sectors) is
encrypted. File contents are stored as plain bytes (see
DOC/DATA_CVM_EXTRACTION.md and DOC/REBUILD.md). A replacement file of
exactly the same size can therefore be written over the original's bytes
without touching the table of contents: the directory record still gives
the same first sector and size, so nothing needs to be re-encrypted. The
disc image holds DATA.CVM as an ordinary file, so the same holds one level
up.

<image> may be:
  - the whole disc image (plain ISO9660 with DATA.CVM in its root),
  - DATA.CVM itself (starts with 'CVMH'), or
  - a decrypted DATA.ISO (plain ISO9660, as made by rofs_decrypt.py).

<path> is a file's path inside DATA.CVM as it appears under DAT/, e.g.
PARAM/PBDATA_EU.PAC (either slash, any case). Files on the disc outside
DATA.CVM take a disc: prefix, e.g. disc:SLES_541.51 or disc:DLL/SAVEPRG.REL
(whole disc images only).

--rename disc:<path>=<NEWNAME> (repeatable) renames a file on the outer
disc, keeping the name's length: it rewrites the ISO9660 directory record
and, since the disc is a UDF bridge, the UDF File Identifier Descriptor
(recomputing its tag CRC and checksum). Neither is encrypted. Other
targets in the same run still use the old name.

<target> is <path>, or <path>#<entry> for one archive entry (its index,
its name, or "header"), e.g. MESSAGE/MES.PAC#7 or PRELOAD/SIMFILE0.PAC#Regulation.tbb.

Usage:
    python patch_disc.py locate <image> <path> ...                        # where each file's bytes are
    python patch_disc.py copies <DAT> <target> ...                        # other places holding the same bytes
    python patch_disc.py patch  <image> <out_image> <target>=<file> ... [--copies] [--dat DAT] [--rename disc:<path>=<NAME>] [--skip-tutorial]
    python patch_disc.py patch  <image> --in-place <target>=<file> ... [--copies] [--dat DAT] [--skip-tutorial]
    python patch_disc.py verify <image> <path>=<file> ...                 # does the image hold these bytes?

`patch` re-reads every patched range afterwards. Keep an unmodified copy
of the disc: --in-place cannot be undone except by patching the original
files back.

Size changes: the game reads a whole file as (size + 0x7ff) >> 11 sectors
(ADXF_GetFsizeSct, used at 0x307f24), so a file may grow or shrink inside
its last sector. `patch` then also rewrites the size in the file's
directory record, decrypting and re-encrypting that one sector. A file
that needs more sectors is refused (that needs files moved, which isn't
supported yet). Files outside DATA.CVM keep their size.

--skip-tutorial (test discs; whole disc image only) skips the opening
playoffs of a new career, the tutorial, with the developers' own switch:
it sets the flag word at SLES 0x34d434 (Dummy.CheckClubEditSkip, which
promotes the club) and swaps commands 88/89 in RootClubEditSeq.sqb,
RootMainSeq.sqb and RootYearStartSeq.sqb, 4 bytes in all. It also starts
the six playoff-period sponsors one year into their contracts (SLES
0x3994a8, 6 bytes), so they end on time: the playoffs run one extra
Sche.YearStart, which is what ends them. The club must be in England
(the switch calls pwkLg_Init(0)). See DOC/SQB_FORMAT.md.

Copies: the same data is often on the disc more than once. PRELOAD/*.PAC
bundles hold copies of loose files (REGULATION.TBB is in all seven
SIMFILE packs) and of MES.PAC entries, and a .HED repeats its archive's
header. `patch` indexes DAT/ (or --dat) and, for every file, header or
entry whose bytes the edit changes, lists the other places holding the
same bytes. Those with the same name are copies the game may read
instead; --copies writes the new bytes into them too. Identical data
under other names (shared stadium parts, say) is only reported.

PRELOAD packs: an entry that changes size (a message file mbb.py grew
into its MES.PAC slot, say) is written by rebuilding its pack with
pac.build_binpac, which moves the later entries; the pack may grow to the
end of its last sector. Entries of a PRELOAD pack, as copies or as
<path>#<entry> targets, are located through the header the pack has in
the image now, so a second run works on a rebuilt pack. Any other copy
is a fixed-size slot and keeps the old data, with a warning.
"""
import os
import shutil
import struct
import sys

from extract_disc import walk_iso, IsoEntry, SECTOR, PVD_SECTOR, DIR_FLAG
import rofs_decrypt

DISC = "disc:"
CVM_MAGIC = b"CVMH"
ISO_MAGIC = b"CD001"
CVM_NAME = "DATA.CVM"
CHUNK = 0x1000000


class SectorView:
    """File-like view of the ISO9660 image inside a container. Offsets are
    ISO offsets; `base` is where ISO sector 0 starts in the file. With a
    key, every sector read is decrypted, which is only right for the
    table of contents: walk_iso reads nothing else."""

    def __init__(self, f, base, key=None, zone_shift=0):
        self.f, self.base, self.key, self.zone_shift = f, base, key, zone_shift
        self.pos = 0

    def seek(self, pos):
        self.pos = pos

    def read(self, size):
        self.f.seek(self.base + self.pos)
        data = self.f.read(size)
        if self.key is not None:
            if self.pos % SECTOR or len(data) % SECTOR:
                raise ValueError("encrypted reads must be whole sectors")
            # rofs_decrypt._decrypt_iso_sector: logical sector =
            # ISO sector + zone sector - ISO start sector.
            data = rofs_decrypt.decrypt_sectors(
                data, self.pos // SECTOR + self.zone_shift, SECTOR, self.key)
        self.pos += len(data)
        return data


class Image:
    """Finds every DATA.CVM file's byte range in a disc image, DATA.CVM or
    DATA.ISO."""

    def __init__(self, path, key=rofs_decrypt.DEFAULT_KEY):
        self.path = path
        with open(path, "rb") as f:
            head = f.read(4)
            f.seek(PVD_SECTOR * SECTOR + 1)
            iso = f.read(5) == ISO_MAGIC
            if head == CVM_MAGIC:
                self.kind, cvm_base = "DATA.CVM", 0
            elif iso:
                outer = {e.path.upper(): e for e in walk_iso(SectorView(f, 0))}
                if CVM_NAME in outer:
                    self.kind = "disc image"
                    cvm_base = outer[CVM_NAME].extent * SECTOR
                    self.cvm_range = (cvm_base, outer[CVM_NAME].size)
                else:
                    self.kind, cvm_base = "DATA.ISO", None
            else:
                raise ValueError("%s: not a disc image, DATA.CVM or DATA.ISO" % path)

            if cvm_base is None:
                view = SectorView(f, 0)
            else:
                f.seek(cvm_base)
                if f.read(4) != CVM_MAGIC:
                    raise ValueError("%s: DATA.CVM does not start with CVMH" % path)
                # read_cvm_header seeks to 0, so give it a view of the CVM.
                hdr = rofs_decrypt.read_cvm_header(_Offset(f, cvm_base))
                base = cvm_base + hdr["iso_start_sector"] * SECTOR
                shift = hdr["iso_zone_sector"] - hdr["iso_start_sector"]
                view = SectorView(f, base, key if hdr["encrypted"] else None, shift)
            self.iso_base, self.key, self.zone_shift = view.base, view.key, view.zone_shift
            try:
                self.files = {e.path.upper(): e for e in walk_iso(view) if not e.is_dir}
            except ValueError as e:
                raise ValueError("%s: can't read the table of contents (%s); wrong key?"
                                 % (path, e))
            # Files outside DATA.CVM (SLES_541.51, DLL/*.REL, ...) are
            # "disc:<path>"; their sectors count from the start of the image.
            if self.kind == "disc image":
                for e in outer.values():
                    if not e.is_dir and e.path.upper() != CVM_NAME:
                        d = IsoEntry(DISC + e.path, e.extent, e.size, False, e.mtime)
                        self.files[d.path.upper()] = d

    def entry(self, path):
        e = self.files.get(path.replace("\\", "/").strip("/").upper())
        if e is None:
            if path.lower().startswith(DISC) and self.kind != "disc image":
                raise ValueError("%s: disc: paths need the whole disc image, not %s"
                                 % (path, self.kind))
            raise ValueError("%s is not in %s" % (path, self.path))
        return e

    def offset(self, entry):
        if entry.path.startswith(DISC):
            return entry.extent * SECTOR
        return self.iso_base + entry.extent * SECTOR

    def toc(self, f):
        """View of the DATA.CVM image that decrypts table-of-contents reads."""
        return SectorView(f, self.iso_base, self.key, self.zone_shift)


class _Offset:
    """Minimal file wrapper that shifts seeks by `base`."""
    def __init__(self, f, base):
        self.f, self.base = f, base

    def seek(self, pos, whence=0):
        self.f.seek(self.base + pos if whence == 0 else pos, whence)

    def read(self, n=-1):
        return self.f.read(n)


# --- copies ------------------------------------------------------------------

class Unit:
    """A run of bytes in a DAT file: a whole file, a BINPAC header, or an
    archive entry. `file` is the DAT-relative path of the file that holds the
    bytes (for an entry indexed by a detached .HED, the data file)."""

    def __init__(self, kind, file, off, size, name, index=None):
        self.kind, self.file, self.off, self.size = kind, file, off, size
        self.name, self.index = name, index
        self.key = None

    @property
    def label(self):
        if self.kind == "file":
            return self.file
        if self.kind == "header":
            return self.file + "#header"
        return "%s#%d:%s" % (self.file, self.index, self.name)

    def simple_name(self):
        """Lower-case name without directories, for matching copies. A
        header is named like the .HED that copies it."""
        if self.kind == "header":
            return os.path.splitext(os.path.basename(self.file))[0].lower() + ".hed"
        return self.name.replace("\\", "/").split("/")[-1].lower()


TRUNCATED_NAME = 15     # BINPAC name fields are 16+ bytes (or 4, extension only)


def same_name(a, b):
    """Equal names, or, since a BINPAC name keeps only the last name_len
    characters of the path, a long name that is the tail of the other.
    Short names must match exactly (1_0.mbb is not 100001_0.mbb)."""
    x, y = a.simple_name(), b.simple_name()
    if not x or not y:
        return False
    if x == y:
        return True
    short, long_ = sorted((x, y), key=len)
    return len(short) >= TRUNCATED_NAME and long_.endswith(short)


class Index:
    """Every loose file, BINPAC header and archive entry under a DAT
    directory, by size and SHA-1. PRS-compressed entries are compared as
    stored, so a copy stored with different compression isn't found."""

    MIN_SIZE = 16

    def __init__(self, dat):
        import hashlib
        import pac
        self.dat = dat
        self.by_key, self.by_file = {}, {}

        def add(u, data):
            if u.size < self.MIN_SIZE:
                return
            u.key = (u.size, hashlib.sha1(data).digest())
            self.by_key.setdefault(u.key, []).append(u)
            self.by_file.setdefault(u.file.upper(), []).append(u)

        for root, dirs, files in os.walk(dat):
            dirs[:] = sorted(d for d in dirs if d != "CVS")
            for n in sorted(files):
                full = os.path.join(root, n)
                rel = os.path.relpath(full, dat).replace(os.sep, "/")
                with open(full, "rb") as f:
                    data = f.read()
                add(Unit("file", rel, 0, len(data), os.path.basename(rel)), data)
                try:
                    h = pac.load_header(full)
                except (ValueError, struct.error):
                    h = None
                if h is None:
                    continue
                dp = pac.data_path(full, h)
                if dp is None or not os.path.exists(dp):
                    continue
                if dp != full:
                    with open(dp, "rb") as f:
                        if f.read(16)[10:16] == b"BINPAC":
                            continue    # the partner describes itself
                    with open(dp, "rb") as f:
                        src = f.read()
                else:
                    src = data
                    if isinstance(h, pac.BinPac):
                        add(Unit("header", rel, 0, h.header_size, ""), data[:h.header_size])
                drel = os.path.relpath(dp, dat).replace(os.sep, "/")
                for i, (off, size, name, _) in enumerate(h.entries):
                    if off + size <= len(src):
                        add(Unit("entry", drel, off, size, name, i), src[off:off + size])

    def units(self, path):
        return self.by_file.get(norm(path), [])

    def resolve(self, target):
        """'PATH' or 'PATH#N' / 'PATH#name' -> the Unit."""
        path, _, sel = target.partition("#")
        units = self.units(path)
        if not units:
            raise ValueError("%s is not in %s" % (path, self.dat))
        if not sel:
            return next(u for u in units if u.kind == "file")
        if sel.lower() == "header":
            hit = [u for u in units if u.kind == "header"]
        elif sel.isdigit():
            hit = [u for u in units if u.kind == "entry" and u.index == int(sel)]
        else:
            probe = Unit("entry", path, 0, 0, sel)
            hit = [u for u in units if u.kind == "entry" and same_name(u, probe)]
        if len(hit) != 1:
            raise ValueError("%s: %s" % (target, "no such entry" if not hit else
                                         "%d entries match; use the index" % len(hit)))
        return hit[0]

    def copies(self, unit):
        """(same-name copies, other identical units) in other files."""
        others = [u for u in self.by_key.get(unit.key, []) if u.file.upper() != unit.file.upper()]
        named = [u for u in others if same_name(u, unit)]
        return named, [u for u in others if u not in named]


def norm(path):
    return path.replace("\\", "/").strip("/").upper()


# --- targets -----------------------------------------------------------------

def parse_pairs(args):
    pairs = []
    for a in args:
        if "=" not in a:
            raise SystemExit("expected <path>=<file>, got %r" % a)
        target, src = a.split("=", 1)
        with open(src, "rb") as f:
            pairs.append((target, src, f.read()))
    return pairs


class Job:
    """Bytes to write at `off` inside DAT file `file`, or at byte `off` of
    the image when `file` is None (directory records)."""
    def __init__(self, file, off, data, label, why):
        self.file, self.off, self.data, self.label, self.why = file, off, data, label, why

    def pos(self, img):
        return self.off if self.file is None else img.offset(img.entry(self.file)) + self.off


# --- renaming files outside DATA.CVM -------------------------------------------

ISO_NAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.")
UDF_FID = 0x101     # File Identifier Descriptor tag


def udf_crc(data):
    """CRC-16/CCITT (poly 0x1021, init 0), as UDF descriptor tags use."""
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def udf_tag_ok(buf, pos):
    tag = buf[pos:pos + 16]
    return len(tag) == 16 and (sum(tag) - tag[4]) & 0xFF == tag[4]


def plan_rename(f, img, target, new):
    """Jobs renaming a file on the outer disc (same name length) in its
    ISO9660 directory record and, on a UDF bridge disc, its UDF File
    Identifier Descriptor."""
    from extract_disc import _read, _parse_record
    if img.kind != "disc image" or not target.lower().startswith(DISC):
        raise ValueError("--rename takes disc:<path> on a whole disc image")
    e = img.entry(target)
    path = e.path[len(DISC):]
    parent, _, old = path.rpartition("/")
    new = new.upper()
    if len(new) != len(old) or not set(new) <= ISO_NAME_CHARS:
        raise ValueError("%s: the new name must have the same length (%d) and use only "
                         "A-Z, 0-9, _ and ." % (target, len(old)))
    jobs = []

    # ISO9660: the record in the parent directory whose extent is the file's.
    dirs = {"": None}
    for d in walk_iso(SectorView(f, 0)):
        if d.is_dir:
            dirs[d.path.upper()] = d
    if parent:
        dext, dsize = dirs[parent.upper()].extent, dirs[parent.upper()].size
    else:
        pvd = _read(SectorView(f, 0), PVD_SECTOR, SECTOR)
        _, dext, dsize, _, _, _ = _parse_record(pvd, 156)
    buf = _read(SectorView(f, 0), dext, dsize)
    hits = []
    for sec in range(0, dsize, SECTOR):
        pos = sec
        while pos < min(sec + SECTOR, dsize) and buf[pos]:
            rec_len, ext, _, _, name, _ = _parse_record(buf, pos)
            if ext == e.extent and name.split(b";")[0].rstrip(b".").decode("ascii") == old:
                hits.append((pos, name))
            pos += rec_len
    if len(hits) != 1:
        raise ValueError("%s: found %d ISO9660 records for it" % (target, len(hits)))
    pos, name = hits[0]
    jobs.append(Job(None, dext * SECTOR + pos + 33, new.encode() + name[len(old):],
                    "%s (ISO9660 record)" % target, "rename to " + new))

    # UDF: FIDs sit in the metadata before the first file. Match the name
    # and require exactly one, with a tag whose CRC checks out.
    first = min(x.extent for x in img.files.values() if x.path.startswith(DISC))
    f.seek(0)
    meta = f.read(first * SECTOR)
    want = [(8, old.encode("latin1")), (16, old.encode("utf-16-be"))]
    hits = []
    for sec in range(0, len(meta), SECTOR):
        pos = sec
        while pos + 38 <= min(sec + SECTOR, len(meta)):
            if meta[pos:pos + 2] == UDF_FID.to_bytes(2, "little") and udf_tag_ok(meta, pos):
                crc_len = struct.unpack_from("<H", meta, pos + 10)[0]
                l_fi = meta[pos + 19]
                l_iu = struct.unpack_from("<H", meta, pos + 36)[0]
                ident = meta[pos + 38 + l_iu:pos + 38 + l_iu + l_fi]
                if ident and (ident[0], ident[1:]) in want:
                    hits.append((pos, crc_len, l_iu, ident))
                pos += (38 + l_iu + l_fi + 3) & ~3
            else:
                pos += 4
    if len(hits) > 1:
        raise ValueError("%s: found %d UDF entries with its name" % (target, len(hits)))
    if hits:
        pos, crc_len, l_iu, ident = hits[0]
        desc = bytearray(meta[pos:pos + 16 + crc_len])
        if udf_crc(desc[16:]) != struct.unpack_from("<H", desc, 8)[0]:
            raise ValueError("%s: its UDF descriptor's CRC doesn't check out" % target)
        enc = "latin1" if ident[0] == 8 else "utf-16-be"
        at = 38 + l_iu + 1
        desc[at:at + len(ident) - 1] = new.encode(enc)
        struct.pack_into("<H", desc, 8, udf_crc(desc[16:]))
        desc[4] = (sum(desc[:16]) - desc[4]) & 0xFF
        jobs.append(Job(None, pos, bytes(desc), "%s (UDF identifier)" % target, "rename to " + new))
    return jobs


# --- size changes inside the last sector --------------------------------------

def sectors(size):
    return (size + SECTOR - 1) // SECTOR


def to_sector_end(data):
    """`data` zero-padded to the end of its last sector. Every file's last
    sector ends in zeros (2,024 of 2,024 in DATA.CVM), so a file that
    changes size is written with them, and patching the original back
    gives the original image."""
    return data + bytes(-len(data) % SECTOR)


def plan_resize(f, img, path, new_size):
    """Job rewriting a DATA.CVM file's size in its directory record. Only
    a size inside the file's last sector is allowed: the game reads a
    whole file as (size + 0x7ff) >> 11 sectors (ADXF_GetFsizeSct, used by
    CFileManagerRofs::FileUpdateCore at 0x307f24), and nothing else moves.
    The sector is decrypted, edited and encrypted again (the XOR stream is
    its own inverse)."""
    from extract_disc import _parse_record
    e = img.entry(path)
    if e.path.startswith(DISC):
        raise ValueError("%s: files outside DATA.CVM can't change size" % path)
    if sectors(new_size) != sectors(e.size):
        raise ValueError("%s: %d bytes need %d sectors, but the file has %d; moving files "
                         "isn't supported yet" % (path, new_size, sectors(new_size), sectors(e.size)))
    view = img.toc(f)
    parent = e.path.rpartition("/")[0].upper()
    if parent:
        d = next(x for x in walk_iso(img.toc(f)) if x.is_dir and x.path.upper() == parent)
        dext, dsize = d.extent, d.size
    else:
        view.seek(PVD_SECTOR * SECTOR)
        _, dext, dsize, _, _, _ = _parse_record(view.read(SECTOR), 156)
    for sec in range(dext, dext + sectors(dsize)):
        view.seek(sec * SECTOR)
        buf = bytearray(view.read(SECTOR))
        pos = 0
        while pos < SECTOR and buf[pos]:
            rec_len, ext, size, flags, name, _ = _parse_record(buf, pos)
            if ext == e.extent and not flags & DIR_FLAG:
                if size != e.size:
                    raise ValueError("%s: directory record says %d bytes" % (path, size))
                struct.pack_into("<I", buf, pos + 10, new_size)    # both-endian u32
                struct.pack_into(">I", buf, pos + 14, new_size)
                data = bytes(buf)
                if img.key is not None:
                    data = rofs_decrypt.decrypt_sectors(data, sec + img.zone_shift, SECTOR, img.key)
                return Job(None, img.iso_base + sec * SECTOR, data,
                           "%s (directory record)" % e.path, "size %d -> %d" % (e.size, new_size))
            pos += rec_len
    raise ValueError("%s: no directory record found" % path)


# PRELOAD packs are the only archives that can be rebuilt with entries
# moved: the game finds their entries through the pack's own header
# (CFcEuro_FileResource::Execute, 0x10d848-0x10d9dc). MES.PAC entries are
# found by the executable too, and other archives have .HED copies of
# their header, so those keep the same-size rule.
REPACKABLE = "PRELOAD/"


def repackable(file):
    return norm(file).startswith(REPACKABLE)


class PackEdits:
    """Entry edits for PRELOAD packs, collected so that each pack is written
    once, located by the header it has in the image now (an earlier run
    may have rebuilt it), and rebuilt if an entry changes size."""

    def __init__(self):
        self.packs = {}

    def add(self, file, index, new, old, label, why):
        pack = self.packs.setdefault(norm(file), {"file": file, "edits": {}})
        prev = pack["edits"].get(index)
        if prev is not None and prev[0] != new:
            raise ValueError("%s gets two different new contents (%s, %s)" % (label, prev[3], why))
        pack["edits"][index] = (new, old, label, why)

    def plan(self, f, img):
        import pac
        jobs, notes = [], []
        for pack in self.packs.values():
            file = pack["file"]
            e = img.entry(file)
            cur = read_at(f, img, file, 0, e.size)
            h, blobs = pac.binpac_blobs(cur)
            todo = []
            for i, (new, old, label, why) in sorted(pack["edits"].items()):
                if blobs[i] == new:
                    notes.append("note: %s already holds the new bytes" % label)
                elif old is not None and blobs[i] != old:
                    notes.append("note: %s holds neither the original nor the new bytes of "
                                 "%s; left alone" % (label, why))
                else:
                    todo.append((i, new, label, why))
            if all(len(new) == len(blobs[i]) for i, new, _, _ in todo):
                for i, new, label, why in todo:
                    jobs.append(Job(file, h.entries[i][0], new, label, why))
                continue
            for i, new, label, why in todo:
                notes.append("note: %s %d -> %d bytes (%s)" % (label, len(blobs[i]), len(new), why))
                blobs[i] = new
            out = pac.build_binpac(cur[:h.header_size], blobs)
            if sectors(len(out)) > sectors(e.size):
                raise ValueError(
                    "%s: rebuilt it is %d bytes, %d over the end of its last sector (%d bytes "
                    "free); moving files isn't supported yet" % (
                        file, len(out), len(out) - sectors(e.size) * SECTOR,
                        sectors(e.size) * SECTOR - e.size))
            jobs.append(Job(file, 0, to_sector_end(out), file,
                            "rebuilt, %d -> %d bytes" % (e.size, len(out))))
            if len(out) != e.size:
                jobs.append(plan_resize(f, img, file, len(out)))
        return jobs, notes


# --- skipping the tutorial (DOC/SQB_FORMAT.md) --------------------------------

SKIP_FLAG = (DISC + "SLES_541.51", 0x24e434)    # SLES 0x34d434, Dummy.CheckClubEditSkip's flag
SKIP_SCRIPTS = (                                # (file, offset, old command, new command)
    ("SEQ/ROOTCLUBEDITSEQ.SQB", 0x868, "Dummy.CheckFirstMatchSkip", "4:89"),
    ("SEQ/ROOTMAINSEQ.SQB", 0x6d8, "Dummy.CheckClubEditSkip", "4:88"),
    ("SEQ/ROOTYEARSTARTSEQ.SQB", 0x30, "Dummy.CheckClubEditSkip", "4:88"),
)
# The starting sponsors (main, 4 subs, supplier), copied into the club's
# slots at new game by SLES 0x257200. Sche.YearStart adds a year to each
# contract (+4) and ends it once its length (+5) is less (SIMPRG.REL
# 0x16b580). The playoffs run one extra Sche.YearStart, so a skip disc
# starts them one year in.
SKIP_SPONSORS = (DISC + "SLES_541.51", 0x29a4a8)  # SLES 0x3994a8
SKIP_SPONSOR_COUNT, SKIP_SPONSOR_SIZE = 6, 0x14


def plan_skip_tutorial(f, img):
    """Jobs for --skip-tutorial, made from the files as the image holds
    them. A spot that already holds the patched value is left alone."""
    import sqb
    if img.kind != "disc image":
        raise ValueError("--skip-tutorial patches SLES_541.51 too, so it needs the whole "
                         "disc image, not %s" % img.kind)
    jobs, notes = [], []
    file, off = SKIP_FLAG
    word = struct.unpack("<I", read_at(f, img, file, off, 4))[0]
    if word == 0:
        jobs.append(Job(file, off, struct.pack("<I", 1), file + " (0x34d434)",
                        "--skip-tutorial: Dummy.CheckClubEditSkip flag 0 -> 1"))
    elif word == 1:
        notes.append("note: %s 0x34d434 already holds 1" % file)
    else:
        raise ValueError("%s 0x34d434 holds %d, not 0 or 1; not the retail executable?" % (file, word))
    for path, offset, old, spec in SKIP_SCRIPTS:
        e = img.entry(path)
        data = read_at(f, img, e.path, 0, e.size)
        new, held, name = sqb.set_command(data, offset, spec)
        if held == name:
            notes.append("note: %s 0x%x already holds %s" % (path, offset, name))
        elif held != old:
            raise ValueError("%s 0x%x holds %s, expected %s" % (path, offset, held, old))
        else:
            for i, (a, b) in enumerate(zip(data, new)):
                if a != b:
                    jobs.append(Job(e.path, i, new[i:i + 1], "%s 0x%x" % (path, offset),
                                    "--skip-tutorial: %s -> %s" % (held, name)))
    file, base = SKIP_SPONSORS
    for i in range(SKIP_SPONSOR_COUNT):
        off = base + i * SKIP_SPONSOR_SIZE
        rec = read_at(f, img, file, off, SKIP_SPONSOR_SIZE)
        if rec[6] not in (0xff, 0xfe, 0xfc):
            raise ValueError("%s: starting sponsor %d has slot code 0x%02x; not the retail "
                             "executable?" % (file, i, rec[6]))
        if rec[4] == 0:
            jobs.append(Job(file, off + 4, b"\x01", "%s (0x%x)" % (file, 0x3994a8 + i * 0x14 + 4),
                            "--skip-tutorial: starting sponsor %d one year into its contract" % i))
        elif rec[4] == 1:
            notes.append("note: %s: starting sponsor %d already one year in" % (file, i))
        else:
            raise ValueError("%s: starting sponsor %d has %d years served, not 0 or 1"
                             % (file, i, rec[4]))
    notes.append("note: --skip-tutorial: start the career in England")
    return jobs, notes


def resolve_target(img, index, target):
    """(file, offset in file, size, label) for 'PATH' or 'PATH#entry'."""
    if "#" in target:
        if index is None:
            raise SystemExit("%s: archive entries need the DAT index (--dat)" % target)
        u = index.resolve(target)
        return u.file, u.off, u.size, u.label
    e = img.entry(target)
    return e.path, 0, e.size, e.path


def read_at(f, img, file, off, size):
    f.seek(img.offset(img.entry(file)) + off)
    return f.read(size)


def plan_copies(img, index, f, file, off, old, new, write_copies, packs):
    """Copy jobs (with write_copies) and notes for every unit of `file` that
    lies inside [off, off + len(new)) and differs between `old` (the DAT
    original) and `new`. Copies inside PRELOAD packs go to `packs` instead.

    Units are DAT's original entries, so an entry that the new file moved
    or resized (mbb.py grows message files into their slot) is compared
    over its old range only, and its new bytes are taken from the new
    header. A PRELOAD pack holding a copy is rebuilt around the new size;
    any other copy is a fixed-size slot, so it is reported instead."""
    import pac
    moved = {}
    if off == 0 and new[10:16] == b"BINPAC":
        try:
            moved = {i: (o, s) for i, (o, s, _, _) in enumerate(pac.BinPac(new).entries)}
        except (ValueError, struct.error):
            pass
    jobs, notes, seen = [], [], set()
    for u in index.units(file):
        lo, hi = u.off - off, u.off - off + u.size
        if lo < 0 or hi > len(old):
            continue
        if lo == 0 and hi == len(old):
            blob = new                  # the target itself, whatever its new size
        elif u.kind == "entry" and u.index in moved:
            o, s = moved[u.index]
            blob = new[o - off:o - off + s]
        else:
            blob = new[lo:hi]
        if blob == old[lo:hi]:
            continue
        resized = len(blob) != u.size
        named, other = index.copies(u)
        for c in named:
            if (c.file.upper(), c.off) in seen:
                continue
            seen.add((c.file.upper(), c.off))
            if not write_copies:
                notes.append("warning: %s changes, but %s holds a copy of it" % (u.label, c.label))
                continue
            if c.kind == "entry" and repackable(c.file):
                packs.add(c.file, c.index, blob, old[lo:hi], c.label, "copy of " + u.label)
                continue
            if resized:
                notes.append("warning: %s is now %d bytes (was %d); its copy %s is a "
                             "fixed-size slot, so it keeps the old data" % (
                                 u.label, len(blob), u.size, c.label))
                continue
            held = read_at(f, img, c.file, c.off, c.size)
            if held == blob:
                notes.append("note: %s already holds the new bytes" % c.label)
                continue
            if held != old[lo:hi]:
                notes.append("note: %s holds neither the original nor the new %s; left alone"
                             % (c.label, u.label))
                continue
            jobs.append(Job(c.file, c.off, blob, c.label, "copy of " + u.label))
        if other:
            notes.append("note: %s has the same bytes as %d unit%s with other names (%s%s); "
                         "not treated as copies" % (
                             u.label, len(other), "" if len(other) == 1 else "s",
                             ", ".join(x.label for x in other[:3]), ", ..." if len(other) > 3 else ""))
    if notes and not write_copies and any(n.startswith("warning") for n in notes):
        notes.append("hint: add --copies to write the new bytes into those copies too")
    return jobs, notes


# --- commands ----------------------------------------------------------------

def cmd_locate(image, paths):
    img = Image(image)
    print("%s: %s, %d files, ISO sector 0 at byte %#x" % (
        image, img.kind, len(img.files), img.iso_base))
    for p in paths:
        e = img.entry(p)
        print("  %-40s sector %7d  size %10d  bytes %#x-%#x" % (
            e.path, e.extent, e.size, img.offset(e), img.offset(e) + e.size))


def cmd_copies(dat, targets):
    index = Index(dat)
    for t in targets:
        base = index.resolve(t)
        units = [base] if "#" in t else sorted(index.units(base.file), key=lambda u: (u.off, -u.size))
        shown = 0
        for u in units:
            named, other = index.copies(u)
            if not named and not other:
                continue
            shown += 1
            print("%s" % u.label)
            for c in named:
                print("    copy       %s" % c.label)
            if other:
                print("    same bytes %s%s" % (", ".join(c.label for c in other[:4]),
                                              " (+%d more)" % (len(other) - 4) if len(other) > 4 else ""))
        if not shown:
            print("%s: no copies in %s" % (base.label, dat))


def copy_file(src, dst):
    total = os.path.getsize(src)
    done = shown = 0
    print("Copying %s to %s (%d MB)" % (src, dst, total >> 20), end="", flush=True)
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while buf := fi.read(CHUNK):
            fo.write(buf)
            done += len(buf)
            while shown < 10 * done // total:
                shown += 1
                print(" %d%%" % (shown * 10), end="", flush=True)
    print()
    shutil.copystat(src, dst)
    os.chmod(dst, 0o644)


def cmd_patch(image, out, in_place, args, dat, write_copies, renames=(), skip_tutorial=False):
    pairs = parse_pairs(args)
    img = Image(image)
    index = Index(dat) if dat else None
    if write_copies and index is None:
        raise SystemExit("--copies needs the DAT index (--dat)")

    # Plan everything against the unmodified image before copying it.
    jobs, notes, packs = [], [], PackEdits()
    with open(image, "rb") as f:
        for target, src, data in pairs:
            file, off, size, label = resolve_target(img, index, target)
            if "#" in target and repackable(file):
                # Located by the pack's current header, and may change size.
                u = index.resolve(target)
                packs.add(file, u.index, data, None, label, src)
            elif len(data) == size:
                jobs.append(Job(file, off, data, label, src))
            elif "#" not in target and not file.startswith(DISC) and \
                    sectors(len(data)) == sectors(size):
                jobs.append(Job(file, 0, to_sector_end(data), label, src))
                jobs.append(plan_resize(f, img, file, len(data)))
            elif "#" in target:
                raise SystemExit(
                    "%s is %d bytes but %s is %d bytes. Only entries of PRELOAD packs can "
                    "change size; other archives keep their layout." % (
                        src, len(data), label, size))
            else:
                raise SystemExit(
                    "%s is %d bytes but %s is %d bytes on the disc. A file may only change "
                    "size inside its last sector (%d bytes free here); moving files isn't "
                    "supported yet." % (src, len(data), label, size, sectors(size) * SECTOR - size))
            # Files outside DATA.CVM aren't in DAT, and nothing there copies them.
            if index is not None and not file.startswith(DISC):
                # Changes are judged against the unmodified data in DAT, so a
                # second run on an already patched image still finds them.
                with open(os.path.join(index.dat, file), "rb") as g:
                    if "#" in target:
                        u = index.resolve(target)
                        off = u.off
                        g.seek(off)
                        old = g.read(u.size)
                    else:
                        off, old = 0, g.read()
                cjobs, cnotes = plan_copies(img, index, f, file, off, old, data,
                                            write_copies, packs)
                jobs += cjobs
                notes += cnotes
        busy = {norm(j.file) for j in jobs if j.file is not None}
        clash = busy & set(packs.packs)
        if clash:
            raise SystemExit("%s: written whole and as single entries in the same run; "
                             "patch one or the other" % ", ".join(sorted(clash)))
        pjobs, pnotes = packs.plan(f, img)
        jobs += pjobs
        notes += pnotes
        for r in renames:
            target, _, new = r.partition("=")
            jobs += plan_rename(f, img, target, new)
        if skip_tutorial:
            touched = {norm(j.file) for j in jobs if j.file is not None}
            clash = touched & {norm(p) for p, _, _, _ in SKIP_SCRIPTS}
            if clash:
                raise SystemExit("--skip-tutorial edits %s; don't patch it as a target too"
                                 % ", ".join(sorted(clash)))
            sjobs, snotes = plan_skip_tutorial(f, img)
            jobs += sjobs
            notes += snotes
    if index is None:
        notes.append("note: no DAT index (--dat), so copies elsewhere on the disc weren't checked")

    if in_place:
        target_path = image
    else:
        if os.path.abspath(out) == os.path.abspath(image):
            raise SystemExit("output is the input; use --in-place to patch it directly")
        copy_file(image, out)
        target_path = out
    with open(target_path, "r+b") as f:
        for j in jobs:
            pos = j.pos(img)
            f.seek(pos)
            old = f.read(len(j.data))
            changed = sum(1 for a, b in zip(old, j.data) if a != b)
            f.seek(pos)
            f.write(j.data)
            f.flush()
            f.seek(pos)
            if f.read(len(j.data)) != j.data:
                raise SystemExit("%s: read-back after writing %s does not match" % (target_path, j.label))
            print("%s: %s <- %s, %d bytes differ from the original%s" % (
                target_path, j.label, j.why, changed, "" if changed else " (no change)"))
    for n in notes:
        print(n)
    resized = sum(1 for j in jobs if j.label.endswith("(directory record)"))
    toc = []
    if resized:
        toc.append("%d directory record%s resized" % (resized, "" if resized == 1 else "s"))
    if renames:
        toc.append("outer directory records renamed")
    print("%s: %d write%s in place; %s" % (
        target_path, len(jobs), "" if len(jobs) == 1 else "s",
        ", ".join(toc) or "table of contents untouched"))


def cmd_verify(image, args):
    img = Image(image)
    ok = True
    with open(image, "rb") as f:
        for path, src, data in parse_pairs(args):
            e = img.entry(path)
            f.seek(img.offset(e))
            held = f.read(e.size)
            if held == data:
                print("%s: %s matches %s" % (image, e.path, src))
            else:
                ok = False
                why = ("sizes differ (%d on disc, %d in the file)" % (e.size, len(data))
                       if e.size != len(data) else
                       "%d bytes differ" % sum(1 for a, b in zip(held, data) if a != b))
                print("%s: %s does not match %s: %s" % (image, e.path, src, why))
    return 0 if ok else 1


def _opt(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    write_copies = "--copies" in args
    if write_copies:
        args.remove("--copies")
    skip_tutorial = "--skip-tutorial" in args
    if skip_tutorial:
        args.remove("--skip-tutorial")
    dat = _opt(args, "--dat", "DAT" if os.path.isdir("DAT") else None)
    renames = []
    while "--rename" in args:
        renames.append(_opt(args, "--rename"))
    try:
        if cmd == "locate" and len(args) >= 2:
            cmd_locate(args[0], args[1:])
            return 0
        if cmd == "copies" and len(args) >= 2:
            cmd_copies(args[0], args[1:])
            return 0
        if cmd == "patch" and (len(args) >= 3 or (renames or skip_tutorial) and len(args) == 2):
            in_place = args[1] == "--in-place"
            cmd_patch(args[0], None if in_place else args[1], in_place, args[2:], dat,
                      write_copies, renames, skip_tutorial)
            return 0
        if cmd == "verify" and len(args) >= 2:
            return cmd_verify(args[0], args[1:])
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
