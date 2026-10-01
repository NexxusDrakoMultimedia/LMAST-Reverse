# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""DAT/PRELOAD checker for Let's Make a Soccer Team! (PS2).

DAT/PRELOAD holds 139 BINPAC packs of files that also exist elsewhere on
the disc (loose files, and MES.PAC entries for messages). A screen's load
list names a pack first and then the files in it. When the pack loads,
every entry is registered as a resource under the same name a normal
request for that file builds, so the later requests are served from the
pack and never reach the disc. See DOC/PRELOAD_DIR.md.

  Load list        0x28-byte records {kind, folder, name, ...} returned by
                   a module's GetPreLoadData; kind 0 file, 1 CSE, 2 message
                   (+0x10 category), 3 texture list, 4 common texture,
                   5 end (CFcEuro_Common::SetupResource 0x104ce0).
                   ExecuteBase (0x104ed0) creates them in order and waits
                   for each to finish before the next.
  Folder           0-16, set up at 0x14eb4c; +100 adds the language digit
                   to the file name (CommonSetup 0x10c9a0).
  Pack entry       BINPAC v3: column 3 = the source folder, column 4 = 1 if
                   the name ends in the language digit. FileResource::
                   Execute (0x10d848-0x10d9dc) registers each entry as
                   "F<folder>_0000_0000_<name>" (0x10e000), dropping that
                   digit; the first resource registered under a name wins
                   (fcEuroRsrc_EntryResource 0x112040).

`info` checks every pack: it is one the code loads, every entry's folder
is known, its source file exists and holds the same bytes, and a
language-digit entry ends in the pack's own digit. It also gives each
pack's free room: the bytes left in its last sector, which is how far a
rebuilt pack may grow (the game reads whole sectors, ADXF_GetFsizeSct;
patch_disc.py --copies rebuilds packs, see DOC/PRELOAD_DIR.md). `lists` prints every
load list that names a PRELOAD pack, from the executable and overlays.
`who` finds the packs holding a file and says what loads them.

Usage:
    python preload.py info  <DAT>                   # check every pack against its sources
    python preload.py lists <ISO>                   # load lists in SLES_541.51 and DLL/*.REL
    python preload.py who   <DAT> <name> ...        # which packs hold a file, and who loads them
"""
import os
import struct
import sys

from pac import load_header

# Folder ids from the file-manager setup at 0x14eb4c (5 is the disc root,
# e.g. version.dat in the root module's list).
FOLDERS = {0: "0SYSTEM", 1: "SEQ", 2: "CSE", 3: "MESSAGE", 4: "PARAM", 5: "",
           6: "SOUND", 7: "TEST3D", 8: "EMBLEM", 9: "PLAYER", 10: "STADIUM",
           11: "EVENT", 12: "GAME", 13: "ACROBATA", 14: "BG", 15: "NEWS",
           16: "PRELOAD"}
LOCALIZE = 100          # folder + 100: add the language digit (0x10c9b4)
MSG_FOLDER = 3          # messages are MES.PAC entries, not loose files

KIND = {0: "file", 1: "cse", 2: "msg", 3: "texlist", 4: "commontex", 5: "end"}
REC_SIZE = 0x28
SECTOR = 0x800          # a whole file is read as (size + 0x7ff) >> 11 sectors

# pack name (no digit) -> (language digit?, what loads it). Addresses of
# the load list and of the function that returns it; see PRELOAD_DIR.md.
LOADERS = {
    "STATIONFILE": (False, "root module, whole game (SLES list 0x51ab98, 0x112a08)"),
    "STATIONMES": (True, "global messages, whole game (EVCOM commands SLES 0x10bf58/0x10c008)"),
    "SIMFILE": (True, "season mode (SIMPRG list 0x214448, SIMROOT_MODULE 0x7a18)"),
    "SIMLARGE": (False, "season mode (SIMPRG list 0x214448, SIMROOT_MODULE 0x7a18)"),
    "SIMLOCALMEM": (True, "season mode (SIMPRG list 0x214448, SIMROOT_MODULE 0x7a18)"),
    "TOPMENU": (True, "side menu (SIMPRG list 0x213cf8, 0x5870)"),
    "MAIL": (True, "mail screen (SIMPRG list 0x21bd58, MAIL_MODULE 0x36d60)"),
    "NEWS": (True, "public relations and news screens (SIMPRG lists 0x2193c8, 0x2195a0)"),
    "TALK_CONTRACT": (True, "contract talks (SIMPRG list 0x215190)"),
    "TALK_DISMISS": (True, "dismissal talks (SIMPRG list 0x215660)"),
    "TALK_MOVE": (True, "transfer talks (SIMPRG list 0x2162a8)"),
    "TALK_NORMAL": (True, "normal talks (SIMPRG list 0x217088, CTalkNormalManager)"),
    "TALK_PLAYER_RETIRE": (True, "retirement talks (SIMPRG list 0x217220)"),
    "TALK_PROMISE_LV2": (True, "promise talks (SIMPRG list 0x217700)"),
    "TALK_PROMISE_RESULT": (True, "promise result talks (SIMPRG list 0x217a40)"),
    "TALK_WITHDRAW": (True, "withdrawal talks (SIMPRG list 0x218028)"),
    "TACTICSFILE": (True, "tactics screen (SLES list 0x55b120, CTacticsManagerImplement)"),
    "TACTICSLARGE": (True, "tactics screen (SLES list 0x55b120, CTacticsManagerImplement)"),
    "TACTICSMATCHFILE": (True, "tactics in a match (SLES list 0x55b3a8, CTacticsManagerImplement)"),
    "TACTICSMATCHLARGE": (True, "tactics in a match (SLES list 0x55b3a8, CTacticsManagerImplement)"),
    "GAMEFILE": (True, "match (GAMEPRG list 0x265590, GAME_MODULE 0xbd0)"),
    "GAMELOCALMEM": (False, "match (GAMEPRG list 0x265590, GAME_MODULE 0xbd0)"),
    # Read through CLoader::loadFileRequest (WP::CTacticsPitch, SLES
    # 0x2a89cc), not as a registering file resource.
    "TACTICSPITCH": (False, "tactics pitch model (CLoader, SLES 0x2a89cc)"),
}


def split_pack_name(fname):
    """'SIMFILE3.PAC' -> ('SIMFILE', 3); 'SIMLARGE.PAC' -> ('SIMLARGE', None)."""
    stem = os.path.splitext(fname)[0].upper()
    if stem[-1:].isdigit() and stem[:-1] in LOADERS:
        return stem[:-1], int(stem[-1])
    return stem, None


def loader(fname):
    """What loads this pack, or None if no code asks for it by this name."""
    base, digit = split_pack_name(fname)
    if base not in LOADERS:
        return None
    localized, what = LOADERS[base]
    return what if localized == (digit is not None) else None


def resource_name(folder, name, digit_flag):
    """Name the entry is registered under (0x10d8fc: the character before
    the dot is dropped for language-digit entries)."""
    if digit_flag == 1:
        stem, dot, ext = name.partition(".")
        name = stem[:-1] + dot + ext
    return "F%02d_%04d_%04d_%s" % (folder, 0, 0, name)


class Sources:
    """Loose files by (folder, NAME), and MES.PAC entries by NAME."""

    def __init__(self, dat):
        self.files = {}
        for root, dirs, files in os.walk(dat):
            rel = os.path.relpath(root, dat).split(os.sep)
            if "CVS" in rel or rel[0].upper() == "PRELOAD":
                continue
            top = "" if rel == ["."] else rel[0].upper()
            for f in files:
                self.files.setdefault((top, f.upper()), os.path.join(root, f))
        mes = os.path.join(dat, "MESSAGE", "MES.PAC")
        self.mes_path, self.mes = mes, {}
        if os.path.exists(mes):
            for off, size, name, _ in load_header(mes).entries:
                self.mes[name.upper()] = (off, size)

    def get(self, folder, name):
        """(label, bytes) of the source, or None."""
        if folder == MSG_FOLDER:
            hit = self.mes.get(name.upper())
            if hit is None:
                return None
            with open(self.mes_path, "rb") as f:
                f.seek(hit[0])
                return "MESSAGE/MES.PAC#" + name, f.read(hit[1])
        path = self.files.get((FOLDERS.get(folder), name.upper()))
        if path is None:
            return None
        with open(path, "rb") as f:
            return path.replace(os.sep, "/"), f.read()


def pack_entries(path):
    """(index, offset, size, name, folder, digit_flag) per entry."""
    hdr = load_header(path)
    if hdr is None or not hasattr(hdr, "version"):
        raise ValueError("not a BINPAC")
    if hdr.version != 3:
        raise ValueError("BINPAC version %d, expected 3" % hdr.version)
    return [(i, off, size, name, extra[0], extra[1])
            for i, (off, size, name, extra) in enumerate(hdr.entries)]


def packs(dat):
    d = os.path.join(dat, "PRELOAD")
    return [(f, os.path.join(d, f)) for f in sorted(os.listdir(d))
            if f.upper().endswith(".PAC")]


# --- commands ----------------------------------------------------------------

def cmd_info(dat):
    src = Sources(dat)
    n_packs = n_entries = n_same = n_unloaded = 0
    for fname, path in packs(dat):
        n_packs += 1
        what = loader(fname)
        _, digit = split_pack_name(fname)
        try:
            entries = pack_entries(path)
        except (ValueError, struct.error) as e:
            print("%-26s  !! %s" % (fname, e))
            continue
        problems, notes = [], []
        with open(path, "rb") as f:
            data = f.read()
        for i, off, size, name, folder, flag in entries:
            n_entries += 1
            if folder not in FOLDERS:
                problems.append("#%d %s: unknown folder %d" % (i, name, folder))
                continue
            if flag not in (0, 1):
                problems.append("#%d %s: column 4 = %d" % (i, name, flag))
            elif flag == 1 and (digit is None or name.partition(".")[0][-1:] != str(digit)):
                problems.append("#%d %s: doesn't end in the pack's language digit" % (i, name))
            got = src.get(folder, name)
            if got is None:
                problems.append("#%d %s: no source in %s" % (i, name, FOLDERS[folder] or "the root"))
            elif got[1] != data[off:off + size]:
                # A pack no code loads is never read, so a stale copy in it
                # is only worth a note.
                msg = "#%d %s differs from %s" % (i, name, got[0])
                (problems if what else notes).append(msg)
            else:
                n_same += 1
        if what is None:
            n_unloaded += 1
        line = "%-26s %4d entries %5d free  %s" % (fname, len(entries), -len(data) % SECTOR,
                                                   what or "not loaded by the code")
        if problems:
            line += "  !! " + "; ".join(problems[:3])
            if len(problems) > 3:
                line += "; ... (%d)" % len(problems)
        print(line)
        for n in notes:
            print("    %s (pack not loaded)" % n)
    print("\n%d packs (%d not loaded by the code), %d entries, %d identical to their source"
          % (n_packs, n_unloaded, n_entries, n_same))


def _string(d, base, va):
    o = va - base
    if 0 < o < len(d) and 32 <= d[o] < 127:
        return d[o:d.index(b"\0", o)].decode("latin1")
    return None


def _load_sites(d, base, target):
    """Code that builds the address with lui/addiu (within 8 instructions)."""
    hi = ((target + 0x8000) >> 16) & 0xffff
    lo = target & 0xffff
    sites = []
    for o in range(0, len(d) - 4, 4):
        w = struct.unpack_from("<I", d, o)[0]
        if w >> 26 != 9 or w & 0xffff != lo:
            continue
        rs = (w >> 21) & 31
        for back in range(1, 9):
            p = o - 4 * back
            if p < 0:
                break
            v = struct.unpack_from("<I", d, p)[0]
            if v >> 26 == 15 and (v >> 16) & 31 == rs and v & 0xffff == hi:
                sites.append(o + base)
                break
    return sites


def cmd_lists(iso):
    bins = [("SLES_541.51", os.path.join(iso, "SLES_541.51"), 0xff000)]
    dll = os.path.join(iso, "DLL")
    for f in sorted(os.listdir(dll)):
        if f.upper().endswith(".REL"):
            bins.append((f, os.path.join(dll, f), 0))
    preload = {b.lower() for b in LOADERS}
    for label, path, base in bins:
        with open(path, "rb") as f:
            d = f.read()

        def rec(r):
            o = r - base
            if o < 0 or o + REC_SIZE > len(d):
                return None
            return struct.unpack_from("<10i", d, o)

        def valid(w):
            if w is None or not 0 <= w[0] <= 4:
                return False
            if w[0] in (0, 1, 3):
                return w[2] != 0 and _string(d, base, w[2]) is not None
            if w[0] == 2:
                return w[1] == MSG_FOLDER and w[2] == 0
            return w[1] == 0 and w[2] == 0

        # Records whose name is a PRELOAD pack, then the whole list around each.
        starts = set()
        for o in range(0, len(d) - REC_SIZE, 4):
            w = struct.unpack_from("<3i", d, o)
            if w[0] != 0 or w[1] % LOCALIZE != 16:
                continue
            name = _string(d, base, w[2])
            if not name or os.path.splitext(name)[0].lower() not in preload:
                continue
            r = o + base
            while valid(rec(r - REC_SIZE)):
                r -= REC_SIZE
            starts.add(r)
        for start in sorted(starts):
            # Overlays are linked at 0, so their lui/addiu pairs hold the
            # same offsets before relocation.
            sites = _load_sites(d, base, start)
            print("%s list 0x%x%s" % (label, start,
                  "  (loaded at %s)" % ", ".join("0x%x" % s for s in sites) if sites else ""))
            r = start
            while True:
                w = rec(r)
                kind = KIND.get(w[0], w[0])
                if w[0] == 5:
                    print("  0x%x  end" % r)
                    break
                if w[0] == 2:
                    desc = "msg     category %d" % w[4]
                elif w[0] in (0, 1, 3):
                    folder = w[1] % LOCALIZE
                    desc = "%-7s %s/%s%s" % (kind, FOLDERS.get(folder, "?%d" % folder) or ".",
                                             _string(d, base, w[2]),
                                             "  (+language digit)" if w[1] >= LOCALIZE else "")
                else:
                    desc = "%-7s %s" % (kind, list(w[3:]))
                print("  0x%x  %s" % (r, desc))
                r += REC_SIZE


def cmd_who(dat, names):
    for want in names:
        want_u = want.upper()
        hits = []
        for fname, path in packs(dat):
            for i, off, size, name, folder, flag in pack_entries(path):
                if name.upper() == want_u:
                    hits.append((fname, i, folder, flag, name))
        if not hits:
            print("%s: in no PRELOAD pack, so it is always read from its own file" % want)
            continue
        print("%s: registered as %s" % (want, resource_name(hits[0][2], hits[0][4], hits[0][3])))
        for fname, i, folder, flag, name in hits:
            print("  PRELOAD/%s#%d  %s" % (fname, i, loader(fname) or "not loaded by the code"))


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "lists" and len(args) == 1:
        cmd_lists(args[0])
    elif cmd == "who" and len(args) >= 2:
        cmd_who(args[0], args[1:])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
