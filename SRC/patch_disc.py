# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Patch edited game files into the disc image, DATA.CVM or DATA.ISO, for
Let's Make a Soccer Team! (PS2). A file keeps its sectors if it fits in
them; one that needs more is moved to the end of DATA.ISO.

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
    python patch_disc.py patch  <image> <out_image> <target>=<file> ... [--copies] [--dat DAT] [--rename disc:<path>=<NAME>] [--skip-tutorial] [--sponsor-negotiation] [--launcher]
    python patch_disc.py patch  <image> --in-place <target>=<file> ... [--copies] [--dat DAT] [--skip-tutorial] [--sponsor-negotiation] [--launcher]
    python patch_disc.py verify <image> <path>=<file> ...                 # does the image hold these bytes?

`patch` re-reads every patched range afterwards. Keep an unmodified copy
of the disc: --in-place cannot be undone except by patching the original
files back.

Size changes: the game reads a whole file as (size + 0x7ff) >> 11 sectors
(ADXF_GetFsizeSct, used at 0x307f24), so a file may grow or shrink inside
its last sector. `patch` then also rewrites the size in the file's
directory record, decrypting and re-encrypting that one sector.

Moving files: a file (or rebuilt PRELOAD pack) that needs more sectors is
written after DATA.ISO's last sector and its directory record pointed
there; its old sectors are left as they are. DATA.ISO has no free sectors
between files, and DATA.CVM is the disc's last file, followed by 10,247
zero sectors before the UDF anchor in the last sector, so DATA.CVM grows
into those (about 20 MB). That changes the ISO's volume size (PVD), the
CVMH/ZONE lengths, DATA.CVM's ISO9660 record and UDF File Entry, and the
ROFS key: the game derives it from the CVMH header, whose +0x20..+0x23
are the low bytes of the CVM's size (rofs_decrypt.header_key, from
RSU_GenerateFixedKey 0x1e7550), so the whole table of contents is
encrypted again with the new key. A file already moved to the end grows
in place on a later run. Past the free sectors the disc image grows (whole
16-sector blocks, up to a single-layer DVD's 2,295,104 sectors): its PVD
volume size, the UDF partition length in both partition descriptors and
the integrity descriptor's size table change, and the UDF end anchor moves
to the new last sector. Files outside DATA.CVM keep their size.

--skip-tutorial (test discs; whole disc image only) skips the opening
playoffs of a new career, the tutorial, but runs their schedule steps: it
sets the flag word at SLES 0x34d434 (Dummy.CheckClubEditSkip, the
developers' switch, which promotes the club) and turns RootClubEditSeq.sqb's
playoff section into InitializeFirstCheck, YearStart, MonthStart,
CheckClubEditSkip and a Call to the won route's MonthEnd, YearEnd and
Finalize, so the real year end runs (club rankings, the club's status);
RootMainSeq.sqb and RootYearStartSeq.sqb keep club creation and year
starts. On an image patched by the earlier skip it also undoes that
skip's sponsor and pwkTeam_YearEndCheck workarounds. The club must be in
England (the switch calls pwkLg_Init(0)). See DOC/SQB_FORMAT.md.

--sponsor-negotiation (whole disc image only) turns the Sponsor screen's
main sponsor negotiation back on, as in the Japanese release. The screen's
check (DLL/SIMPRG.REL 0xc5ca0) is a stub returning 0 in PAL; the patch
makes it return 1 for a sponsor not yet negotiated with on this screen, 12
words in all (0xc5ca0 and the unused method at 0xd3748). See
DOC/SPONSOR_NEGOTIATION.md.

--launcher boots into the developers' launcher, a debug menu of test
modules (viewers, screen tests, MAIN GAME START): it turns RootMainSeq.sqb's
branch past the launcher at 0x98 into BranchIfZero, 1 byte. It works on
DATA.CVM or DATA.ISO too. See DOC/SQB_FORMAT.md#the-developer-launcher.

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

    def __init__(self, path, key=None):
        self.path = path
        with open(path, "rb") as f:
            head = f.read(4)
            f.seek(PVD_SECTOR * SECTOR + 1)
            iso = f.read(5) == ISO_MAGIC
            self.cvm_base = self.cvm_size = None
            if head == CVM_MAGIC:
                self.kind, cvm_base = "DATA.CVM", 0
                self.cvm_size = os.path.getsize(path)
            elif iso:
                outer = {e.path.upper(): e for e in walk_iso(SectorView(f, 0))}
                if CVM_NAME in outer:
                    self.kind = "disc image"
                    cvm_base = outer[CVM_NAME].extent * SECTOR
                    self.cvm_range = (cvm_base, outer[CVM_NAME].size)
                    self.cvm_size = outer[CVM_NAME].size
                    f.seek(PVD_SECTOR * SECTOR + 80)
                    self.disc_sectors = struct.unpack("<I", f.read(4))[0]
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
                if key is None:
                    # The game derives the key from the CVMH sector, so a
                    # resized DATA.CVM has its own (rofs_decrypt.header_key).
                    f.seek(cvm_base)
                    key = rofs_decrypt.header_key(f.read(SECTOR)) or rofs_decrypt.DEFAULT_KEY
                base = cvm_base + hdr["iso_start_sector"] * SECTOR
                shift = hdr["iso_zone_sector"] - hdr["iso_start_sector"]
                view = SectorView(f, base, key if hdr["encrypted"] else None, shift)
                self.cvm_base, self.iso_start = cvm_base, hdr["iso_start_sector"]
            self.iso_base, self.key, self.zone_shift = view.base, view.key, view.zone_shift
            # The ISO's volume space size (PVD +80): where moved files go.
            view.seek(PVD_SECTOR * SECTOR)
            self.iso_sectors = struct.unpack_from("<I", view.read(SECTOR), 80)[0]
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


class TocEdits:
    """Edits to DATA.ISO's table of contents: new sizes and first sectors
    in files' directory records, and the volume size in the PVD. The
    sectors are kept decrypted until jobs(), which encrypts each changed
    one once. A size inside the file's last sector needs nothing else: the
    game reads a whole file as (size + 0x7ff) >> 11 sectors
    (ADXF_GetFsizeSct, used by CFileManagerRofs::FileUpdateCore at
    0x307f24). A file that needs more sectors is moved first (Moves).

    The key comes from the CVMH header and changes with DATA.CVM's size
    (rofs_decrypt.header_key). When plan_grow sets `new_key`, every
    encrypted sector, the PVD through the last directory sector, is
    encrypted again with it. The XOR stream is its own inverse."""

    def __init__(self):
        self.edits = {}
        self.plain = {}         # ISO sector -> decrypted bytes, edited in place
        self.new_key = None

    def sector(self, f, img, sec):
        if sec not in self.plain:
            view = img.toc(f)
            view.seek(sec * SECTOR)
            self.plain[sec] = bytearray(view.read(SECTOR))
        return self.plain[sec]

    def add(self, img, path, new_size, new_extent=None):
        e = img.entry(path)
        if e.path.startswith(DISC):
            raise ValueError("%s: files outside DATA.CVM can't change size or move" % path)
        if new_extent is None and sectors(new_size) != sectors(e.size):
            raise ValueError("%s: %d bytes need %d sectors, but the file has %d"
                             % (path, new_size, sectors(new_size), sectors(e.size)))
        self.edits[e.path.upper()] = (e, new_size, e.extent if new_extent is None else new_extent)

    def _record(self, f, img, e):
        """(sector, offset) of a file's directory record."""
        from extract_disc import _parse_record
        parent = e.path.rpartition("/")[0].upper()
        if parent:
            d = next(x for x in walk_iso(img.toc(f)) if x.is_dir and x.path.upper() == parent)
            dext, dsize = d.extent, d.size
        else:
            _, dext, dsize, _, _, _ = _parse_record(self.sector(f, img, PVD_SECTOR), 156)
        for sec in range(dext, dext + sectors(dsize)):
            buf = self.sector(f, img, sec)
            pos = 0
            while pos < SECTOR and buf[pos]:
                rec_len, ext, size, flags, name, _ = _parse_record(buf, pos)
                if ext == e.extent and not flags & DIR_FLAG:
                    if size != e.size or buf[pos + 1]:
                        raise ValueError("%s: directory record doesn't match (%d bytes, "
                                         "%d extended-attribute sectors)"
                                         % (e.path, size, buf[pos + 1]))
                    return sec, pos
                pos += rec_len
        raise ValueError("%s: no directory record found" % e.path)

    def jobs(self, f, img):
        changed = {}            # sector -> reasons
        for e, new_size, new_extent in self.edits.values():
            sec, pos = self._record(f, img, e)
            buf = self.sector(f, img, sec)
            # Both-endian u32s: extent at +2/+6, size at +10/+14.
            struct.pack_into("<I", buf, pos + 2, new_extent)
            struct.pack_into(">I", buf, pos + 6, new_extent)
            struct.pack_into("<I", buf, pos + 10, new_size)
            struct.pack_into(">I", buf, pos + 14, new_size)
            changed.setdefault(sec, []).append("%s size %d -> %d%s" % (
                e.path, e.size, new_size,
                ", sector %d -> %d" % (e.extent, new_extent) if new_extent != e.extent else ""))
        if PVD_SECTOR in self.plain and self.plain[PVD_SECTOR] != self.sector_original(f, img):
            changed.setdefault(PVD_SECTOR, []).append("volume size %d -> %d sectors" % (
                img.iso_sectors, struct.unpack_from("<I", self.plain[PVD_SECTOR], 80)[0]))
        key = img.key
        if self.new_key is not None and self.new_key != img.key:
            key = self.new_key
            hdr = rofs_decrypt.read_cvm_header(_Offset(f, img.cvm_base))
            end = rofs_decrypt.find_toc_end_sector(_Offset(f, img.cvm_base), hdr, img.key)
            for sec in range(PVD_SECTOR, end):
                self.sector(f, img, sec)
                changed.setdefault(sec, []).append("re-encrypted with key %s" % key.hex().upper())
        jobs = []
        for sec, why in sorted(changed.items()):
            data = bytes(self.plain[sec])
            if key is not None:
                data = rofs_decrypt.decrypt_sectors(data, sec + img.zone_shift, SECTOR, key)
            label = ("DATA.ISO volume descriptor" if sec == PVD_SECTOR else
                     "directory sector %d" % sec)
            jobs.append(Job(None, img.iso_base + sec * SECTOR, data, label, "; ".join(why)))
        return jobs

    def sector_original(self, f, img):
        view = img.toc(f)
        view.seek(PVD_SECTOR * SECTOR)
        return bytearray(view.read(SECTOR))


# --- moving files to the end of DATA.ISO --------------------------------------
#
# DATA.ISO has no free sectors between its files, and DATA.CVM is the last
# file on the disc, followed by 10,247 zero sectors and the UDF anchor in
# the disc's last sector. A file that outgrows its sectors is written after
# the ISO's last sector and its directory record pointed there; its old
# sectors are left as they are. DATA.CVM grows into the zeros, so these
# lengths follow (DOC/REBUILD.md#moving-files):
#   ISO PVD +80/+84       volume space size, in sectors (both-endian)
#   CVMH +0x1c            DATA.CVM size in bytes (u64 big-endian)
#   ZONE +0x04            ZONE chunk length, the CVM size - 0x80c (u64 BE)
#   ZONE +0x30            the ISO's length in bytes (u64 BE)
#   disc ISO9660 record   DATA.CVM's size (both-endian u32)
#   disc UDF File Entry   information length (+56), blocks recorded (+64)
#                         and its one allocation descriptor's length
CVMH_SIZE, ZONE_AT = 0x1c, 0x800
ZONE_LENGTH, ZONE_ISO_LENGTH = 0x04, 0x30
ZONE_REST = 0x80c           # CVM size - ZONE chunk length
UDF_FILE_ENTRY = 261


class Moves:
    """Files to move to the end of DATA.ISO."""

    def __init__(self):
        self.files = {}

    def add(self, file, data, label, why):
        self.files[norm(file)] = (file, data, label, why)

    def plan(self, f, img, toc):
        if not self.files:
            return [], []
        if img.cvm_base is None and img.kind != "DATA.ISO":
            raise ValueError("can't move files in %s" % img.path)
        jobs, notes = [], []
        end = img.iso_sectors
        for file, data, label, why in self.files.values():
            e = img.entry(file)
            if e.extent + sectors(e.size) == end:
                # Already the last file (moved by an earlier run): grow in place.
                start = e.extent
            else:
                start = end
            end = start + sectors(len(data))
            where = ("moved to ISO sector %d" % start if start != e.extent else
                     "grown in place at the end of DATA.ISO")
            jobs.append(Job(None, img.iso_base + start * SECTOR, to_sector_end(data), label,
                            "%s, %s" % (why, where)))
            toc.add(img, file, len(data), start)
            notes.append("note: %s needs %d sectors (had %d): %s" % (
                e.path, sectors(len(data)), sectors(e.size),
                "moved from ISO sector %d to %d" % (e.extent, start) if start != e.extent
                else where))
        # Growing comes first: growing the disc clears the old UDF end
        # anchor, which the moved data may then cover.
        return plan_grow(f, img, end, toc) + jobs, notes


def _udf_cvm_entry(f, img):
    """(disc byte offset, bytes) of DATA.CVM's UDF File Entry, or None on a
    disc without UDF. Found through its File Identifier Descriptor, which
    sits in the metadata before the first file, and the partition start in
    the Partition Descriptor of the volume descriptor sequence named by the
    anchor at sector 256."""
    f.seek(256 * SECTOR)
    anchor = f.read(SECTOR)
    if struct.unpack_from("<H", anchor, 0)[0] != 2 or not udf_tag_ok(anchor, 0):
        return None
    vds_len, vds_loc = struct.unpack_from("<II", anchor, 16)
    part_start = None
    for n in range(vds_loc, vds_loc + vds_len // SECTOR):
        f.seek(n * SECTOR)
        d = f.read(SECTOR)
        tag = struct.unpack_from("<H", d, 0)[0]
        if tag == 5:
            part_start = struct.unpack_from("<I", d, 188)[0]
        if tag == 8 or tag == 0:
            break
    if part_start is None:
        raise ValueError("%s: UDF anchor found but no partition descriptor" % img.path)
    first = min(x.extent for x in img.files.values() if x.path.startswith(DISC))
    f.seek(0)
    meta = f.read(first * SECTOR)
    hits = []
    for pos in range(0, len(meta) - 38, 4):
        if meta[pos:pos + 2] == UDF_FID.to_bytes(2, "little") and udf_tag_ok(meta, pos):
            l_fi = meta[pos + 19]
            l_iu = struct.unpack_from("<H", meta, pos + 36)[0]
            ident = meta[pos + 38 + l_iu:pos + 38 + l_iu + l_fi]
            if ident[1:] in (CVM_NAME.encode("utf-16-be"), CVM_NAME.encode("latin1")):
                hits.append(struct.unpack_from("<I", meta, pos + 24)[0])
    if len(hits) != 1:
        raise ValueError("%s: found %d UDF entries for %s" % (img.path, len(hits), CVM_NAME))
    off = (part_start + hits[0]) * SECTOR
    f.seek(off)
    fe = f.read(SECTOR)
    if struct.unpack_from("<H", fe, 0)[0] != UDF_FILE_ENTRY or not udf_tag_ok(fe, 0):
        raise ValueError("%s: no UDF File Entry where %s's identifier points" % (img.path, CVM_NAME))
    return off, fe


# A single-layer DVD holds 2,295,104 sectors; a bigger image would need a
# layer break, which the disc doesn't have.
DVD5_SECTORS = 2295104
DVD_BLOCK = 16              # sectors per DVD ECC block
UDF_ANCHOR, UDF_PARTITION, UDF_LVID = 2, 5, 9


def _udf_retag(buf, location=None):
    """Recompute a UDF descriptor tag's CRC (over the descriptor after the
    16-byte tag) and checksum, optionally with a new tag location."""
    crc_len = struct.unpack_from("<H", buf, 10)[0]
    if location is not None:
        struct.pack_into("<I", buf, 12, location)
    struct.pack_into("<H", buf, 8, udf_crc(buf[16:16 + crc_len]))
    buf[4] = (sum(buf[:16]) - buf[4]) & 0xFF


def plan_grow_disc(f, img, cvm_end):
    """Jobs growing the disc image so that DATA.CVM can end at sector
    `cvm_end`, with the UDF end anchor in the new last sector. The size is
    in the ISO9660 PVD (+80/+84), the UDF Partition Descriptors of the
    main and reserve volume descriptor sequences (+192, the partition runs
    to the anchor), the Logical Volume Integrity Descriptor's size table,
    and the end anchor's own position. The user reports that an image with
    extra files added, so bigger than the original, still ran."""
    new_disc = -(-(cvm_end + 1) // DVD_BLOCK) * DVD_BLOCK
    if new_disc > DVD5_SECTORS:
        raise ValueError("the disc would need %d sectors, more than a single-layer DVD (%d)"
                         % (new_disc, DVD5_SECTORS))
    old_disc = img.disc_sectors
    jobs = []
    pvd = struct.pack("<I", new_disc) + struct.pack(">I", new_disc)
    jobs.append(Job(None, PVD_SECTOR * SECTOR + 80, pvd, "disc volume descriptor",
                    "volume size %d -> %d sectors" % (old_disc, new_disc)))

    f.seek(256 * SECTOR)
    anchor = bytearray(f.read(SECTOR))
    f.seek((old_disc - 1) * SECTOR)
    end_anchor = bytearray(f.read(SECTOR))
    if struct.unpack_from("<H", anchor, 0)[0] != UDF_ANCHOR:
        return jobs     # no UDF
    if struct.unpack_from("<H", end_anchor, 0)[0] != UDF_ANCHOR or             struct.unpack_from("<I", end_anchor, 12)[0] != old_disc - 1:
        raise ValueError("%s: no UDF anchor in the disc's last sector" % img.path)
    # Main and reserve volume descriptor sequences (anchor +16, +24).
    lvid_at = part_start = None
    for at in (16, 24):
        length, loc = struct.unpack_from("<II", anchor, at)
        for n in range(loc, loc + length // SECTOR):
            f.seek(n * SECTOR)
            d = bytearray(f.read(SECTOR))
            tag = struct.unpack_from("<H", d, 0)[0]
            if tag == UDF_PARTITION:
                part_start, part_len = struct.unpack_from("<II", d, 188)
                if part_start + part_len != old_disc - 1:
                    raise ValueError("%s: the UDF partition doesn't end at the anchor"
                                     % img.path)
                struct.pack_into("<I", d, 192, new_disc - 1 - part_start)
                _udf_retag(d)
                jobs.append(Job(None, n * SECTOR, bytes(d), "UDF partition descriptor (sector %d)"
                                % n, "length %d -> %d" % (part_len, new_disc - 1 - part_start)))
            elif tag == 6 and lvid_at is None:      # Logical Volume Descriptor
                lvid_at = struct.unpack_from("<I", d, 436)[0]
            elif tag in (0, 8):
                break
    if part_start is None:
        raise ValueError("%s: no UDF partition descriptor" % img.path)
    if lvid_at is not None:
        f.seek(lvid_at * SECTOR)
        d = bytearray(f.read(SECTOR))
        if struct.unpack_from("<H", d, 0)[0] == UDF_LVID:
            parts = struct.unpack_from("<I", d, 72)[0]
            for i in range(parts):
                at = 80 + 4 * parts + 4 * i
                if struct.unpack_from("<I", d, at)[0] == old_disc - 1 - part_start:
                    struct.pack_into("<I", d, at, new_disc - 1 - part_start)
            _udf_retag(d)
            jobs.append(Job(None, lvid_at * SECTOR, bytes(d), "UDF integrity descriptor",
                            "partition size %d -> %d" % (old_disc - 1 - part_start,
                                                         new_disc - 1 - part_start)))
    # The anchor moves to the new last sector; the old one becomes zeros
    # (written first, as DATA.CVM's new data may cover it).
    _udf_retag(end_anchor, new_disc - 1)
    jobs.insert(0, Job(None, (old_disc - 1) * SECTOR, bytes(SECTOR), "old UDF end anchor",
                       "cleared"))
    jobs.append(Job(None, (new_disc - 1) * SECTOR, bytes(end_anchor), "UDF end anchor",
                    "moved to sector %d" % (new_disc - 1)))
    return jobs


def plan_grow(f, img, iso_sectors, toc):
    """Jobs setting the ISO's volume size to `iso_sectors` and, around it,
    DATA.CVM's lengths: its header and, on a whole disc image, its ISO9660
    record and UDF File Entry. The CVM may only grow into zero sectors."""
    from extract_disc import _read, _parse_record
    jobs = []
    pvd = toc.sector(f, img, PVD_SECTOR)
    struct.pack_into("<I", pvd, 80, iso_sectors)
    struct.pack_into(">I", pvd, 84, iso_sectors)
    if img.cvm_base is None:
        return jobs

    new_size = (img.iso_start + iso_sectors) * SECTOR
    old_size = img.cvm_size
    f.seek(img.cvm_base)
    head = bytearray(f.read(ZONE_AT + ZONE_ISO_LENGTH + 8))
    if struct.unpack_from(">Q", head, CVMH_SIZE)[0] != old_size or \
            struct.unpack_from(">Q", head, ZONE_AT + ZONE_LENGTH)[0] != old_size - ZONE_REST or \
            struct.unpack_from(">Q", head, ZONE_AT + ZONE_ISO_LENGTH)[0] != \
            old_size - img.iso_start * SECTOR or head[ZONE_AT:ZONE_AT + 4] != b"ZONE":
        raise ValueError("%s: the CVMH/ZONE lengths don't match DATA.CVM's size %d"
                         % (img.path, old_size))
    struct.pack_into(">Q", head, CVMH_SIZE, new_size)
    struct.pack_into(">Q", head, ZONE_AT + ZONE_LENGTH, new_size - ZONE_REST)
    struct.pack_into(">Q", head, ZONE_AT + ZONE_ISO_LENGTH, new_size - img.iso_start * SECTOR)
    jobs.append(Job(None, img.cvm_base, bytes(head), "DATA.CVM header (CVMH/ZONE)",
                    "size %d -> %d" % (old_size, new_size)))
    if img.key is not None:
        f.seek(img.cvm_base)
        sector0 = bytearray(f.read(SECTOR))
        sector0[:len(head)] = head
        toc.new_key = rofs_decrypt.header_key(bytes(sector0))
    if img.kind != "disc image" or new_size <= old_size:
        return jobs

    # The sectors DATA.CVM grows into must be unused. On this disc they are
    # zeros up to the UDF anchor in the last sector; past that, the disc
    # grows (plan_grow_disc).
    lo, hi = sectors(img.cvm_base + old_size), sectors(img.cvm_base + new_size)
    f.seek(lo * SECTOR)
    for _ in range(lo, min(hi, img.disc_sectors - 1)):
        if any(f.read(SECTOR)):
            raise ValueError("DATA.CVM can't grow: sectors after it aren't empty")
    if hi > img.disc_sectors - 1:
        jobs += plan_grow_disc(f, img, hi)

    # ISO9660 record in the root directory.
    pvd = _read(SectorView(f, 0), PVD_SECTOR, SECTOR)
    _, dext, dsize, _, _, _ = _parse_record(pvd, 156)
    buf = _read(SectorView(f, 0), dext, dsize)
    hits = []
    for sec in range(0, dsize, SECTOR):
        pos = sec
        while pos < min(sec + SECTOR, dsize) and buf[pos]:
            rec_len, ext, size, flags, name, _ = _parse_record(buf, pos)
            if ext * SECTOR == img.cvm_base and name.split(b";")[0] == CVM_NAME.encode():
                hits.append(pos)
            pos += rec_len
    if len(hits) != 1:
        raise ValueError("%s: found %d ISO9660 records for %s" % (img.path, len(hits), CVM_NAME))
    jobs.append(Job(None, dext * SECTOR + hits[0] + 10,
                    struct.pack("<I", new_size) + struct.pack(">I", new_size),
                    "DATA.CVM (disc ISO9660 record)", "size %d -> %d" % (old_size, new_size)))

    # UDF File Entry. Its one short allocation descriptor holds the whole
    # 32-bit length, over the two extent-type bits, as the mastering tool
    # wrote it (1,970,935,808 shows as 0x757a1800); kept that way.
    udf = _udf_cvm_entry(f, img)
    if udf is not None:
        off, fe = udf
        fe = bytearray(fe)
        l_ea, l_ad = struct.unpack_from("<II", fe, 168)
        crc_len = struct.unpack_from("<H", fe, 10)[0]
        if struct.unpack_from("<Q", fe, 56)[0] != old_size or l_ad != 8 or fe[34] & 7 != 0 or \
                struct.unpack_from("<I", fe, 176 + l_ea)[0] != old_size or \
                udf_crc(fe[16:16 + crc_len]) != struct.unpack_from("<H", fe, 8)[0]:
            raise ValueError("%s: DATA.CVM's UDF File Entry isn't the expected single extent "
                             "of %d bytes" % (img.path, old_size))
        struct.pack_into("<Q", fe, 56, new_size)
        struct.pack_into("<Q", fe, 64, sectors(new_size))
        struct.pack_into("<I", fe, 176 + l_ea, new_size)
        struct.pack_into("<H", fe, 8, udf_crc(fe[16:16 + crc_len]))
        fe[4] = (sum(fe[:16]) - fe[4]) & 0xFF
        jobs.append(Job(None, off, bytes(fe[:16 + crc_len]), "DATA.CVM (disc UDF File Entry)",
                        "size %d -> %d" % (old_size, new_size)))
    return jobs


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

    def plan(self, f, img, toc, moves):
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
            why = "rebuilt, %d -> %d bytes" % (e.size, len(out))
            if sectors(len(out)) > sectors(e.size):
                moves.add(file, out, file, why)     # outgrew its sectors
                continue
            jobs.append(Job(file, 0, to_sector_end(out), file, why))
            if len(out) != e.size:
                toc.add(img, file, len(out))
        return jobs, notes


# --- skipping the tutorial (DOC/SQB_FORMAT.md) --------------------------------

SKIP_FLAG = (DISC + "SLES_541.51", 0x24e434)    # SLES 0x34d434, Dummy.CheckClubEditSkip's flag
# The skip runs the playoffs' own schedule steps without the playoff turns:
# RootClubEditSeq.sqb's playoff section (L2) becomes InitializeFirstCheck,
# YearStart, MonthStart, then Dummy.CheckClubEditSkip (pwkLg_Init(0) and
# ScheCallback_ProcPromotion, which Sche.FirstCheck runs for a won
# playoff), then Call L8: MonthEnd, YearEnd, Finalize, the won route. So the
# real Sche.YearEnd runs: the club rankings (ClubRank::UpdateYearEnd), the
# club's status (pwkTeam_YearEndCheck) and the rest. 0x868 stays the
# retail CheckFirstMatchSkip, which writes 0, so the script enters L2. The
# only jump to L3, in the playoff turn loop, now goes to L8 too, as L3's
# marker becomes the Call; that loop no longer runs. The script uses no
# other Call, so the one that never returns can't block another.
# (file, [(offset, accepted old commands, new "table:cmd", {arg: value})])
SKIP_SCRIPTS = (
    ("SEQ/ROOTCLUBEDITSEQ.SQB", [
        # 4:89 there is the earlier skip, which branched straight to L9.
        (0x868, ("Dummy.CheckFirstMatchSkip", "Dummy.CheckClubEditSkip"), "4:88", None),
        (0x8b0, ("TutorialHelp.Effective100",), "4:34", None),
        (0x8c0, ("Sche.InitializeFirstCheck",), "4:18", None),
        (0x8d0, ("Sche.YearStart",), "4:20", None),
        (0x8e0, ("Sche.MonthStart",), "4:89", None),
        (0x8f0, ("Label",), "0:5", {1: 8}),                # Call L8
        (0xba8, ("BranchIfZero",), "0:27", {2: 8}),        # its jump to L3 -> L8
    ]),
    # Year starts and club creation stay (4:88 writes 0 there).
    ("SEQ/ROOTMAINSEQ.SQB", [(0x6d8, ("Dummy.CheckClubEditSkip",), "4:88", None)]),
    ("SEQ/ROOTYEARSTARTSEQ.SQB", [(0x30, ("Dummy.CheckClubEditSkip",), "4:88", None)]),
)
# The earlier skip worked around the year start and year end it left out:
# it started the six playoff-period sponsors one year into their contracts
# (SLES 0x3994a8, byte +4 of each 0x14-byte record) and made
# Dummy.CheckClubEditSkip also call pwkTeam_YearEndCheck (9 words at SLES
# 0x108dac). With the real YearStart and YearEnd those would count twice,
# so an image patched by the earlier skip gets the retail bytes back.
OLD_SKIP_SPONSORS = (DISC + "SLES_541.51", 0x29a4a8)  # SLES 0x3994a8
OLD_SKIP_SPONSOR_COUNT, OLD_SKIP_SPONSOR_SIZE = 6, 0x14
OLD_SKIP_CODE = (DISC + "SLES_541.51", 0x9dac, bytes.fromhex(   # SLES 0x108dac: retail, earlier skip
    "34d4438c2d888000010002240f0062140000bfff8618090c2d200000724c040c00000000"),
    bytes.fromhex(
    "0000bfff2d8880008618090c2d200000724c040c00000000a8b8090c0000000000000000"))


def plan_skip_tutorial(f, img):
    """Jobs for --skip-tutorial, made from the files as the image holds
    them. A spot that already holds the patched value is left alone, and
    the earlier skip's workarounds are undone."""
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
    for path, edits in SKIP_SCRIPTS:
        e = img.entry(path)
        data = read_at(f, img, e.path, 0, e.size)
        todo = []
        for offset, olds, spec, args in edits:
            held, held_args = sqb.command_at(data, offset)
            table, cmd = (int(x, 0) for x in spec.split(":"))
            want = sqb.SETS["root"][table][cmd][0]
            if held == want and all(held_args[i][1] == v for i, v in (args or {}).items()):
                continue
            if held not in olds:
                raise ValueError("%s 0x%x holds %s, expected %s" % (path, offset, held,
                                                                    " or ".join(olds)))
            todo.append((offset, spec, args))
        if not todo:
            notes.append("note: %s already holds the tutorial skip" % path)
            continue
        new, names = sqb.set_commands(data, todo)
        what = ", ".join("0x%x %s -> %s" % (o, a, b) for (o, _, _), (a, b) in zip(todo, names))
        for i, (a, b) in enumerate(zip(data, new)):
            if a != b:
                jobs.append(Job(e.path, i, new[i:i + 1], path, "--skip-tutorial: " + what))
    file, base = OLD_SKIP_SPONSORS
    for i in range(OLD_SKIP_SPONSOR_COUNT):
        off = base + i * OLD_SKIP_SPONSOR_SIZE
        rec = read_at(f, img, file, off, OLD_SKIP_SPONSOR_SIZE)
        if rec[4] == 1 and rec[6] in (0xff, 0xfe, 0xfc):
            jobs.append(Job(file, off + 4, b"\x00", "%s (0x%x)" % (file, 0x3994a8 + i * 0x14 + 4),
                            "--skip-tutorial: undo the earlier skip's sponsor %d offset" % i))
    file, off, retail, earlier = OLD_SKIP_CODE
    held = read_at(f, img, file, off, len(retail))
    if held == earlier:
        jobs.append(Job(file, off, retail, "%s (0x108dac)" % file,
                        "--skip-tutorial: undo the earlier skip's pwkTeam_YearEndCheck call"))
    elif held != retail:
        raise ValueError("%s 0x108dac doesn't hold Dummy.CheckClubEditSkip's code; "
                         "not the retail executable?" % file)
    notes.append("note: --skip-tutorial: start the career in England")
    return jobs, notes


# --- sponsor negotiation (DOC/SPONSOR_NEGOTIATION.md) -------------------------

# The Sponsor screen asks 0xc5ca0(this, sponsor id) whether the chosen main
# sponsor can be negotiated with (SIMPRG.REL 0xc6634). In PAL it is a stub
# returning 0, so the screen always goes to the contract question. The
# negotiation states behind it (0xb-0x16) are all still there, and each
# negotiation adds the sponsor to a 20-word list at this+0x12f0 (0xc5c58)
# that nothing else reads. The new check returns 1 unless the sponsor is in
# that list: one negotiation per sponsor per Sponsor screen. The stub
# branches to the unreferenced CStaffContractWindow method at 0xd3748 (24
# words, no relocation sites), which holds the loop. Branches only, since
# the overlay is relocated when it loads.
NEGO_FILE = DISC + "DLL/SIMPRG.REL"
NEGO_CODE = (
    (0xc5ca0, bytes.fromhex("0800e0032d100000"),        # jr $ra; move $v0, $zero
     bytes.fromhex("a9360010f0128324")),                 # b 0xd3748; addiu $v1, $a0, 0x12f0
    (0xd3748, bytes.fromhex(
        "d0ffbd272000b07f1000b17f881790240000bfff010011240000048e00000000ffff312604001026"),
     bytes.fromhex(
        "40138824"      # addiu $t0, $a0, 0x1340      end of the list
        "0000628c"      # lw    $v0, ($v1)
        "05004510"      # beq   $v0, $a1, 0xd3768     already negotiated
        "04006324"      # addiu $v1, $v1, 4
        "fcff6814"      # bne   $v1, $t0, 0xd374c
        "00000000"      # nop
        "0800e003"      # jr    $ra
        "01000224"      # addiu $v0, $zero, 1
        "0800e003"      # jr    $ra
        "2d100000")),   # move  $v0, $zero
)


def plan_sponsor_negotiation(f, img):
    """Jobs for --sponsor-negotiation. A spot that already holds the new
    code is left alone."""
    if img.kind != "disc image":
        raise ValueError("--sponsor-negotiation patches DLL/SIMPRG.REL, so it needs the whole "
                         "disc image, not %s" % img.kind)
    jobs, notes = [], []
    for off, old, new in NEGO_CODE:
        held = read_at(f, img, NEGO_FILE, off, len(old))
        if held == old:
            jobs.append(Job(NEGO_FILE, off, new, "%s (0x%x)" % (NEGO_FILE, off),
                            "--sponsor-negotiation: main sponsor negotiation check"))
        elif held == new:
            notes.append("note: %s 0x%x already holds the negotiation check" % (NEGO_FILE, off))
        else:
            raise ValueError("%s 0x%x doesn't hold the expected code; not the retail "
                             "overlay?" % (NEGO_FILE, off))
    return jobs, notes


# --- the developer launcher (DOC/SQB_FORMAT.md#the-developer-launcher) --------

# RootMainSeq.sqb runs Dummy.CheckLauncher (always 1) at 0x88 and at 0x98
# branches past RootLauncherSeq.sqb when the value is non-zero. Turning the
# branch into BranchIfZero (command 0:27, 1 byte) boots into the launcher.
LAUNCHER = ("SEQ/ROOTMAINSEQ.SQB", 0x98, "BranchIfNotZero", "0:27")


def plan_launcher(f, img):
    """Jobs for --launcher. A script that already holds the new command is
    left alone."""
    import sqb
    path, offset, old, spec = LAUNCHER
    e = img.entry(path)
    data = read_at(f, img, e.path, 0, e.size)
    new, held, name = sqb.set_command(data, offset, spec)
    if held == name:
        return [], ["note: %s 0x%x already holds %s" % (path, offset, name)]
    if held != old:
        raise ValueError("%s 0x%x holds %s, expected %s" % (path, offset, held, old))
    return [Job(e.path, i, new[i:i + 1], "%s 0x%x" % (path, offset),
                "--launcher: %s -> %s, boot into the developer launcher" % (held, name))
            for i, (a, b) in enumerate(zip(data, new)) if a != b], []


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


def cmd_patch(image, out, in_place, args, dat, write_copies, renames=(), skip_tutorial=False,
              sponsor_nego=False, launcher=False):
    pairs = parse_pairs(args)
    img = Image(image)
    index = Index(dat) if dat else None
    if write_copies and index is None:
        raise SystemExit("--copies needs the DAT index (--dat)")

    # Plan everything against the unmodified image before copying it.
    jobs, notes, packs = [], [], PackEdits()
    toc, moves = TocEdits(), Moves()
    # Files written whole: a copy that falls inside one (a schedule pack's
    # header, which repeats its .HED) is already in its new bytes.
    whole = {norm(resolve_target(img, index, t)[0]): d for t, _, d in pairs if "#" not in t}
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
                toc.add(img, file, len(data))
            elif "#" in target:
                raise SystemExit(
                    "%s is %d bytes but %s is %d bytes. Only entries of PRELOAD packs can "
                    "change size; other archives keep their layout." % (
                        src, len(data), label, size))
            elif not file.startswith(DISC):
                moves.add(file, data, label, src)   # needs more sectors
            else:
                raise SystemExit("%s is %d bytes but %s is %d bytes on the disc; files outside "
                                 "DATA.CVM keep their size" % (src, len(data), label, size))
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
                for j in cjobs:
                    mine = whole.get(norm(j.file)) if j.file is not None else None
                    if mine is None or norm(j.file) == norm(file):
                        jobs.append(j)
                    elif mine[j.off:j.off + len(j.data)] != j.data:
                        raise SystemExit("%s: its copy in %s differs from that file's own "
                                         "new bytes" % (label, j.file))
                    else:
                        notes.append("%s: copy in %s already in that file's new bytes"
                                     % (label, j.file))
                notes += cnotes
        busy = {norm(j.file) for j in jobs if j.file is not None}
        clash = busy & set(packs.packs)
        if clash:
            raise SystemExit("%s: written whole and as single entries in the same run; "
                             "patch one or the other" % ", ".join(sorted(clash)))
        pjobs, pnotes = packs.plan(f, img, toc, moves)
        jobs += pjobs
        notes += pnotes
        clash = set(moves.files) & {norm(j.file) for j in jobs if j.file is not None}
        if clash:
            raise SystemExit("%s: moved, but also written in place in the same run"
                             % ", ".join(sorted(clash)))
        mjobs, mnotes = moves.plan(f, img, toc)
        jobs += mjobs + toc.jobs(f, img)
        notes += mnotes
        for r in renames:
            target, _, new = r.partition("=")
            jobs += plan_rename(f, img, target, new)
        # The files the targets write, before the switches below add theirs
        # (--skip-tutorial and --launcher both edit RootMainSeq.sqb).
        touched = {norm(j.file) for j in jobs if j.file is not None}
        if skip_tutorial:
            clash = touched & {norm(p) for p, _ in SKIP_SCRIPTS}
            if clash:
                raise SystemExit("--skip-tutorial edits %s; don't patch it as a target too"
                                 % ", ".join(sorted(clash)))
            sjobs, snotes = plan_skip_tutorial(f, img)
            jobs += sjobs
            notes += snotes
        if sponsor_nego:
            if norm(NEGO_FILE) in {norm(j.file) for j in jobs if j.file is not None}:
                raise SystemExit("--sponsor-negotiation edits %s; don't patch it as a target too"
                                 % NEGO_FILE)
            njobs, nnotes = plan_sponsor_negotiation(f, img)
            jobs += njobs
            notes += nnotes
        if launcher:
            if norm(LAUNCHER[0]) in touched:
                raise SystemExit("--launcher edits %s; don't patch it as a target too"
                                 % LAUNCHER[0])
            ljobs, lnotes = plan_launcher(f, img)
            jobs += ljobs
            notes += lnotes
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
            changed = sum(1 for a, b in zip(old, j.data) if a != b) + len(j.data) - len(old)
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
    changed = []
    resized = len(toc.edits) - len(moves.files)
    if resized:
        changed.append("%d directory record%s resized" % (resized, "" if resized == 1 else "s"))
    if moves.files:
        changed.append("%d file%s moved to the end of DATA.ISO" % (
            len(moves.files), "" if len(moves.files) == 1 else "s"))
    if renames:
        changed.append("outer directory records renamed")
    print("%s: %d write%s; %s" % (
        target_path, len(jobs), "" if len(jobs) == 1 else "s",
        ", ".join(changed) or "table of contents untouched"))


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
    sponsor_nego = "--sponsor-negotiation" in args
    if sponsor_nego:
        args.remove("--sponsor-negotiation")
    launcher = "--launcher" in args
    if launcher:
        args.remove("--launcher")
    dat =_opt(args, "--dat", "DAT" if os.path.isdir("DAT") else None)
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
        if cmd == "patch" and (len(args) >= 3 or (renames or skip_tutorial or sponsor_nego
                                                  or launcher) and len(args) == 2):
            in_place = args[1] == "--in-place"
            cmd_patch(args[0], None if in_place else args[1], in_place, args[2:], dat,
                      write_copies, renames, skip_tutorial, sponsor_nego, launcher)
            return 0
        if cmd == "verify" and len(args) >= 2:
            return cmd_verify(args[0], args[1:])
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
