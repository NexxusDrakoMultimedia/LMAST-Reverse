"""Patch edited game files into the disc image, DATA.CVM or DATA.ISO, for
Let's Make a Soccer Team! (PS2). Same-size files only.

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

<target> is <path>, or <path>#<entry> for one archive entry (its index,
its name, or "header"), e.g. MESSAGE/MES.PAC#7 or PRELOAD/SIMFILE0.PAC#Regulation.tbb.

Usage:
    python patch_disc.py locate <image> <path> ...                        # where each file's bytes are
    python patch_disc.py copies <DAT> <target> ...                        # other places holding the same bytes
    python patch_disc.py patch  <image> <out_image> <target>=<file> ... [--copies] [--dat DAT]
    python patch_disc.py patch  <image> --in-place <target>=<file> ... [--copies] [--dat DAT]
    python patch_disc.py verify <image> <path>=<file> ...                 # does the image hold these bytes?

`patch` refuses a replacement whose size differs from the original (that
needs a rebuilt table of contents, which isn't supported yet) and re-reads
every patched range afterwards. Keep an unmodified copy of the disc:
--in-place cannot be undone except by patching the original files back.

Copies: the same data is often on the disc more than once. PRELOAD/*.PAC
bundles hold copies of loose files (REGULATION.TBB is in all seven
SIMFILE packs) and of MES.PAC entries, and a .HED repeats its archive's
header. `patch` indexes DAT/ (or --dat) and, for every file, header or
entry whose bytes the edit changes, lists the other places holding the
same bytes. Those with the same name are copies the game may read
instead; --copies writes the new bytes into them too (they are the same
size, so this is safe). Identical data under other names (shared stadium
parts, say) is only reported.
"""
import os
import shutil
import struct
import sys

from extract_disc import walk_iso, IsoEntry, SECTOR, PVD_SECTOR
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
            self.iso_base = view.base
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
    """Bytes to write at `off` inside DAT file `file`."""
    def __init__(self, file, off, data, label, why):
        self.file, self.off, self.data, self.label, self.why = file, off, data, label, why


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


def plan_copies(img, index, f, file, off, old, new, write_copies):
    """Copy jobs (with write_copies) and notes for every unit of `file` that
    lies inside [off, off + len(new)) and differs between `old` (the DAT
    original) and `new`."""
    jobs, notes, seen = [], [], set()
    for u in index.units(file):
        lo, hi = u.off - off, u.off - off + u.size
        if lo < 0 or hi > len(new) or old[lo:hi] == new[lo:hi]:
            continue
        named, other = index.copies(u)
        for c in named:
            if (c.file.upper(), c.off) in seen:
                continue
            seen.add((c.file.upper(), c.off))
            if not write_copies:
                notes.append("warning: %s changes, but %s holds a copy of it" % (u.label, c.label))
                continue
            held = read_at(f, img, c.file, c.off, c.size)
            if held == new[lo:hi]:
                notes.append("note: %s already holds the new bytes" % c.label)
                continue
            if held != old[lo:hi]:
                notes.append("note: %s holds neither the original nor the new %s; left alone"
                             % (c.label, u.label))
                continue
            jobs.append(Job(c.file, c.off, new[lo:hi], c.label, "copy of " + u.label))
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


def cmd_patch(image, out, in_place, args, dat, write_copies):
    pairs = parse_pairs(args)
    img = Image(image)
    index = Index(dat) if dat else None
    if write_copies and index is None:
        raise SystemExit("--copies needs the DAT index (--dat)")

    # Plan everything against the unmodified image before copying it.
    jobs, notes = [], []
    with open(image, "rb") as f:
        for target, src, data in pairs:
            file, off, size, label = resolve_target(img, index, target)
            if len(data) != size:
                raise SystemExit(
                    "%s is %d bytes but %s is %d bytes on the disc. Only same-size "
                    "files can be patched in place; a size change needs a rebuilt "
                    "table of contents, which isn't supported yet." % (src, len(data), label, size))
            jobs.append(Job(file, off, data, label, src))
            if index is not None:
                # Changes are judged against the unmodified data in DAT, so a
                # second run on an already patched image still finds them.
                with open(os.path.join(index.dat, file), "rb") as g:
                    g.seek(off)
                    old = g.read(size)
                cjobs, cnotes = plan_copies(img, index, f, file, off, old, data, write_copies)
                jobs += cjobs
                notes += cnotes
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
            pos = img.offset(img.entry(j.file)) + j.off
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
    print("%s: %d write%s in place; table of contents untouched" % (
        target_path, len(jobs), "" if len(jobs) == 1 else "s"))


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
    dat = _opt(args, "--dat", "DAT" if os.path.isdir("DAT") else None)
    try:
        if cmd == "locate" and len(args) >= 2:
            cmd_locate(args[0], args[1:])
            return 0
        if cmd == "copies" and len(args) >= 2:
            cmd_copies(args[0], args[1:])
            return 0
        if cmd == "patch" and len(args) >= 3:
            in_place = args[1] == "--in-place"
            cmd_patch(args[0], None if in_place else args[1], in_place, args[2:], dat, write_copies)
            return 0
        if cmd == "verify" and len(args) >= 2:
            return cmd_verify(args[0], args[1:])
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
