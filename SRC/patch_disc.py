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
PARAM/PBDATA_EU.PAC (either slash, any case).

Usage:
    python patch_disc.py locate <image> <path> ...                      # where each file's bytes are
    python patch_disc.py patch  <image> <out_image> <path>=<file> ...   # copy the image, then patch
    python patch_disc.py patch  <image> --in-place <path>=<file> ...    # patch the image itself
    python patch_disc.py verify <image> <path>=<file> ...               # does the image hold these bytes?

`patch` refuses a file whose size differs from the original (that needs a
rebuilt table of contents, which isn't supported yet) and re-reads every
patched range afterwards. Keep an unmodified copy of the disc: --in-place
cannot be undone except by patching the original files back.
"""
import os
import shutil
import struct
import sys

from extract_disc import walk_iso, SECTOR, PVD_SECTOR
import rofs_decrypt

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

    def entry(self, path):
        e = self.files.get(path.replace("\\", "/").strip("/").upper())
        if e is None:
            raise ValueError("%s is not in %s" % (path, self.path))
        return e

    def offset(self, entry):
        return self.iso_base + entry.extent * SECTOR


class _Offset:
    """Minimal file wrapper that shifts seeks by `base`."""
    def __init__(self, f, base):
        self.f, self.base = f, base

    def seek(self, pos, whence=0):
        self.f.seek(self.base + pos if whence == 0 else pos, whence)

    def read(self, n=-1):
        return self.f.read(n)


def parse_pairs(args):
    pairs = []
    for a in args:
        if "=" not in a:
            raise SystemExit("expected <path>=<file>, got %r" % a)
        path, src = a.split("=", 1)
        with open(src, "rb") as f:
            pairs.append((path, src, f.read()))
    return pairs


def check_sizes(img, pairs):
    for path, src, data in pairs:
        e = img.entry(path)
        if len(data) != e.size:
            raise SystemExit(
                "%s is %d bytes but %s is %d bytes on the disc. Only same-size "
                "files can be patched in place; a size change needs a rebuilt "
                "table of contents, which isn't supported yet." % (src, len(data), e.path, e.size))


# --- commands ----------------------------------------------------------------

def cmd_locate(image, paths):
    img = Image(image)
    print("%s: %s, %d files, ISO sector 0 at byte %#x" % (
        image, img.kind, len(img.files), img.iso_base))
    for p in paths:
        e = img.entry(p)
        print("  %-40s sector %7d  size %10d  bytes %#x-%#x" % (
            e.path, e.extent, e.size, img.offset(e), img.offset(e) + e.size))


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


def cmd_patch(image, out, in_place, args):
    pairs = parse_pairs(args)
    img = Image(image)
    check_sizes(img, pairs)
    if in_place:
        target = image
    else:
        if os.path.abspath(out) == os.path.abspath(image):
            raise SystemExit("output is the input; use --in-place to patch it directly")
        copy_file(image, out)
        target = out
    with open(target, "r+b") as f:
        for path, src, data in pairs:
            e = img.entry(path)
            off = img.offset(e)
            f.seek(off)
            old = f.read(e.size)
            changed = sum(1 for a, b in zip(old, data) if a != b)
            f.seek(off)
            f.write(data)
            f.flush()
            f.seek(off)
            if f.read(e.size) != data:
                raise SystemExit("%s: read-back after writing %s does not match" % (target, e.path))
            print("%s: %s <- %s, %d bytes differ from the original%s" % (
                target, e.path, src, changed, "" if changed else " (no change)"))
    print("%s: %d file%s patched in place; table of contents untouched" % (
        target, len(pairs), "" if len(pairs) == 1 else "s"))


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


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    try:
        if cmd == "locate" and len(args) >= 2:
            cmd_locate(args[0], args[1:])
            return 0
        if cmd == "patch" and len(args) >= 3:
            in_place = args[1] == "--in-place"
            cmd_patch(args[0], None if in_place else args[1], in_place, args[2:])
            return 0
        if cmd == "verify" and len(args) >= 2:
            return cmd_verify(args[0], args[1:])
    except ValueError as e:
        raise SystemExit(str(e))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
