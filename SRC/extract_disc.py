"""Set up ISO/ and DAT/ from a Redump-verified disc image.

Automates the README's setup steps for the PAL disc (SLES-54151):

  1. verify   the image matches the Redump dump (redump.org/disc/12334/):
              size, CRC-32, MD5 and SHA-1 of the 1-track 2048-byte image.
  2. extract  the disc's ISO9660 filesystem into ISO/ (SLES_541.51, DLL/,
              AUDIO/, DATA.CVM, ...).
  3. decrypt  ISO/DATA.CVM into ISO/DATA.ISO with rofs_decrypt.py (only the
              archive's ISO9660 table of contents is encrypted).
  4. extract  ISO/DATA.ISO into DAT/.

ISO9660 is read directly (primary volume descriptor at sector 16, then the
directory records), so nothing needs to be mounted. Names lose their ";1"
version suffix, and each file gets the recording date from its directory
record. Files that already exist with the right size are skipped, so an
interrupted run can simply be restarted; --force rewrites them.

See DOC/DATA_CVM_EXTRACTION.md for the DATA.CVM format and key.

Usage:
    python SRC/extract_disc.py all <disc.iso> [iso_dir] [dat_dir] [--force] [--no-verify]
        run every step; iso_dir and dat_dir default to ISO and DAT
    python SRC/extract_disc.py verify <disc.iso>
        hash the image and compare it with the Redump entry
    python SRC/extract_disc.py list <image.iso>
        list the files in a plain ISO9660 image (the disc, or DATA.ISO)
    python SRC/extract_disc.py extract <image.iso> <out_dir> [--force]
        extract a plain ISO9660 image
"""
import datetime
import hashlib
import os
import stat
import struct
import sys
import time
import zlib

from rofs_decrypt import cvm_to_iso

SECTOR = 0x800
PVD_SECTOR = 16
CHUNK = 0x1000000  # 16 MiB copy/hash buffer

# Redump "Let's Make a Soccer Team!" (Europe, Australia), SLES-54151, v1.01,
# http://redump.org/disc/12334/ (one DVD-5 track, 1,732,512 sectors).
REDUMP = {
    "size": 3548184576,
    "crc32": "1c34e97e",
    "md5": "adadf32f4fd418b60632813b011c3388",
    "sha1": "78771805294c924b68fe4aa01ad52f70229abb9d",
}

DIR_FLAG = 0x02
MULTI_EXTENT_FLAG = 0x80


# --- Redump verification ---------------------------------------------------

def hash_image(path, verbose=True):
    """Return (size, crc32, md5, sha1) of a file, as hex strings."""
    total = os.path.getsize(path)
    md5, sha1, crc, done = hashlib.md5(), hashlib.sha1(), 0, 0
    with open(path, "rb") as f:
        while buf := f.read(CHUNK):
            md5.update(buf)
            sha1.update(buf)
            crc = zlib.crc32(buf, crc)
            done += len(buf)
            if verbose:
                print(f"\rHashing: {done / total * 100:5.1f}%", end="", flush=True)
    if verbose:
        print()
    return total, f"{crc:08x}", md5.hexdigest(), sha1.hexdigest()


def verify_image(path, verbose=True):
    """Hash the image and print one line per check; return True if all match."""
    size, crc, md5, sha1 = hash_image(path, verbose)
    ok = True
    for name, got in (("size", size), ("crc32", crc), ("md5", md5), ("sha1", sha1)):
        want = REDUMP[name]
        line = f"  {name:<6} {got}"
        if got != want:
            line += f"  !! expected {want}"
            ok = False
        print(line)
    print("Matches Redump disc 12334 (SLES-54151 v1.01)." if ok
          else "Does not match the Redump dump.")
    return ok


# --- ISO9660 reader --------------------------------------------------------

class IsoEntry:
    def __init__(self, path, extent, size, is_dir, mtime):
        self.path = path        # "/"-separated, relative to the image root
        self.extent = extent    # first sector
        self.size = size        # bytes
        self.is_dir = is_dir
        self.mtime = mtime      # POSIX timestamp, or None


def _record_time(b):
    """Decode a 7-byte ISO9660 directory-record date to a POSIX timestamp."""
    year, month, day, hour, minute, second, gmt = struct.unpack("<6Bb", b)
    if month == 0 or day == 0:
        return None
    tz = datetime.timezone(datetime.timedelta(minutes=15 * gmt))
    try:
        return datetime.datetime(1900 + year, month, day, hour, minute,
                                 second, tzinfo=tz).timestamp()
    except ValueError:
        return None


def _parse_record(buf, pos):
    """Return (record_length, extent, size, flags, name, mtime) at pos."""
    rec_len = buf[pos]
    if rec_len < 0x22:
        raise ValueError(f"bad directory record length 0x{rec_len:x}")
    ext_attr = buf[pos + 1]
    extent = struct.unpack_from("<I", buf, pos + 2)[0] + ext_attr
    size = struct.unpack_from("<I", buf, pos + 10)[0]
    mtime = _record_time(buf[pos + 18:pos + 25])
    flags = buf[pos + 25]
    nlen = buf[pos + 32]
    name = buf[pos + 33:pos + 33 + nlen]
    return rec_len, extent, size, flags, name, mtime


def _read(f, sector, size):
    f.seek(sector * SECTOR)
    data = f.read(size)
    if len(data) != size:
        raise ValueError(f"image truncated at sector 0x{sector:x}")
    return data


def walk_iso(f):
    """Yield an IsoEntry for every directory and file in a plain ISO9660 image."""
    pvd = _read(f, PVD_SECTOR, SECTOR)
    if pvd[0] != 1 or pvd[1:6] != b"CD001":
        raise ValueError("no ISO9660 primary volume descriptor at sector 16")
    _, root_extent, root_size, _, _, _ = _parse_record(pvd, 156)

    stack = [("", root_extent, root_size)]
    seen = set()
    while stack:
        dir_path, extent, size = stack.pop()
        if extent in seen:
            raise ValueError(f"directory loop at sector 0x{extent:x}")
        seen.add(extent)
        buf = _read(f, extent, size)
        # Records never cross a sector boundary; a zero length byte pads the
        # rest of the sector.
        for sec in range(0, size, SECTOR):
            pos = sec
            while pos < min(sec + SECTOR, size) and buf[pos] != 0:
                rec_len, ext, sz, flags, name, mtime = _parse_record(buf, pos)
                pos += rec_len
                if name in (b"\x00", b"\x01"):  # "." and ".."
                    continue
                if flags & MULTI_EXTENT_FLAG:
                    raise ValueError(f"{dir_path}/{name!r}: multi-extent files "
                                     "are not supported")
                text = name.decode("ascii").split(";")[0].rstrip(".")
                path = f"{dir_path}/{text}" if dir_path else text
                is_dir = bool(flags & DIR_FLAG)
                yield IsoEntry(path, ext, sz, is_dir, mtime)
                if is_dir:
                    stack.append((path, ext, sz))


def extract_iso(image, out_dir, force=False, verbose=True):
    """Extract every file of a plain ISO9660 image into out_dir.

    Returns (written, skipped) file counts."""
    written = skipped = 0
    with open(image, "rb") as f:
        entries = sorted(walk_iso(f), key=lambda e: e.path)
        total = sum(e.size for e in entries if not e.is_dir)
        done = 0
        for e in entries:
            dest = os.path.join(out_dir, *e.path.split("/"))
            if e.is_dir:
                os.makedirs(dest, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if not force and os.path.isfile(dest) and os.path.getsize(dest) == e.size:
                skipped += 1
                done += e.size
                continue
            if os.path.exists(dest):
                # Files copied off a mounted disc are read-only.
                os.chmod(dest, stat.S_IWRITE | stat.S_IREAD)
            f.seek(e.extent * SECTOR)
            remaining = e.size
            with open(dest, "wb") as out:
                while remaining:
                    buf = f.read(min(CHUNK, remaining))
                    if not buf:
                        raise ValueError(f"{e.path}: image truncated")
                    out.write(buf)
                    remaining -= len(buf)
                    done += len(buf)
                    if verbose and total:
                        print(f"\rExtracting {image}: {done / total * 100:5.1f}%",
                              end="", flush=True)
            if e.mtime is not None:
                os.utime(dest, (e.mtime, e.mtime))
            written += 1
    if verbose:
        print(f"\rExtracted {image} to {out_dir}: {written} written, "
              f"{skipped} already present")
    return written, skipped


# --- commands --------------------------------------------------------------

def cmd_verify(disc):
    return 0 if verify_image(disc) else 1


def cmd_list(image):
    with open(image, "rb") as f:
        for e in sorted(walk_iso(f), key=lambda e: e.path):
            if e.is_dir:
                print(f"{'<dir>':>12}  {e.path}/")
            else:
                print(f"{e.size:>12,}  {e.path}")
    return 0


def cmd_extract(image, out_dir, force):
    extract_iso(image, out_dir, force)
    return 0


def cmd_all(disc, iso_dir, dat_dir, force, verify):
    start = time.time()
    if verify:
        print(f"[1/4] Verifying {disc} against Redump")
        if not verify_image(disc):
            print("Stopping. Use --no-verify to extract a different dump anyway.")
            return 1
    else:
        print("[1/4] Skipping Redump verification")

    print(f"[2/4] Extracting the disc to {iso_dir}")
    extract_iso(disc, iso_dir, force)

    cvm = os.path.join(iso_dir, "DATA.CVM")
    data_iso = os.path.join(iso_dir, "DATA.ISO")
    print(f"[3/4] Decrypting {cvm} to {data_iso}")
    if not os.path.isfile(cvm):
        raise ValueError(f"{cvm} not found on the disc")
    if not force and os.path.isfile(data_iso):
        print(f"  {data_iso} already exists; skipping (use --force to redo)")
    else:
        cvm_to_iso(cvm, data_iso)

    print(f"[4/4] Extracting {data_iso} to {dat_dir}")
    extract_iso(data_iso, dat_dir, force)

    print(f"Done in {time.time() - start:.0f} s.")
    return 0


def main(argv):
    flags = {a for a in argv[1:] if a.startswith("--")}
    args = [a for a in argv[1:] if not a.startswith("--")]
    unknown = flags - {"--force", "--no-verify"}
    if not args or unknown:
        if unknown:
            print(f"unknown option: {', '.join(sorted(unknown))}\n")
        print(__doc__)
        return 1
    force = "--force" in flags
    cmd, rest = args[0], args[1:]
    if cmd == "all" and 1 <= len(rest) <= 3:
        iso_dir = rest[1] if len(rest) > 1 else "ISO"
        dat_dir = rest[2] if len(rest) > 2 else "DAT"
        return cmd_all(rest[0], iso_dir, dat_dir, force, "--no-verify" not in flags)
    if cmd == "verify" and len(rest) == 1:
        return cmd_verify(rest[0])
    if cmd == "list" and len(rest) == 1:
        return cmd_list(rest[0])
    if cmd == "extract" and len(rest) == 2:
        return cmd_extract(rest[0], rest[1], force)
    print(__doc__)
    return 1


sys.exit(main(sys.argv))
