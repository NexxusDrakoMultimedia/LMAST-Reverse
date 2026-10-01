# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Reader for the CVS metadata left in DATA.CVM (Let's Make a Soccer Team!,
PS2).

The developers checked DATA.CVM's folders out of CVS and burned the
checkout as it was, so DAT/CVS/ and every DAT/<folder>/CVS/ still hold the
three standard CVS files. The game never reads them. See DOC/CVS_DIR.md.

  ROOT        one line: the pserver address of the developers' repository
  REPOSITORY  the folder's path in it, e.g. fc_euro/Data/Emblem
  ENTRIES     one line per file: /name/revision/date/options/tag, and
              D/name//// per subfolder; a lone "D" ends the list

`info` checks every folder's REPOSITORY against its name and its ENTRIES
against the files on the disc: a listed file that is missing is marked
!!; files on the disc that CVS doesn't list (made by the build, not
checked in) are listed as such. `list` prints a folder's entries with
their original names, revisions and dates. ROOT names a person's login,
so neither command prints it.

Usage:
    python cvs.py info <DAT>
    python cvs.py list <DAT/folder>
"""
import os
import sys
import time

CVS_DIR = "CVS"
REPO_PREFIX = "fc_euro/Data"


def read_lines(path):
    with open(path, "rb") as f:
        return f.read().decode("latin1").splitlines()


class Entries:
    def __init__(self, folder):
        cvs = os.path.join(folder, CVS_DIR)
        self.repository = read_lines(os.path.join(cvs, "REPOSITORY"))[0].strip()
        self.files = []         # (name, revision, date, options, tag)
        self.dirs = []
        self.other = []
        for line in read_lines(os.path.join(cvs, "ENTRIES")):
            if line.startswith("D/"):
                self.dirs.append(line.split("/")[1])
            elif line.startswith("/"):
                f = line.split("/")
                if len(f) < 6:
                    raise ValueError("short entry %r" % line)
                self.files.append((f[1], f[2], f[3], f[4], f[5]))
            elif line != "D":
                self.other.append(line)


def parse_date(text):
    """CVS entry dates are asctime() text in UTC, e.g. 'Thu Jan 26 12:39:14 2006'."""
    try:
        return time.strptime(" ".join(text.split()), "%a %b %d %H:%M:%S %Y")
    except ValueError:
        return None


def check_folder(path):
    name = os.path.basename(path.rstrip("/\\"))
    try:
        e = Entries(path)
    except (OSError, ValueError, IndexError) as err:
        return ["%-9s !! %s" % (name, err)]
    problems = []
    tail = e.repository.split("/")[-1]
    if e.repository.lower() != ("%s/%s" % (REPO_PREFIX, name)).lower():
        problems.append("repository %s" % e.repository)
    on_disc = {n.upper() for n in os.listdir(path) if n != CVS_DIR}
    listed = {f[0].upper() for f in e.files}
    missing = sorted(listed - on_disc)
    if missing:
        problems.append("%d listed files not on the disc (%s)" % (len(missing), ", ".join(missing[:5])))
    if e.other:
        problems.append("unexpected lines %r" % e.other[:2])
    dates = sorted(d for d in (parse_date(f[2]) for f in e.files) if d)
    binary = sum(1 for f in e.files if f[3] == "-kb")
    span = ("%s to %s" % (time.strftime("%Y-%m-%d", dates[0]), time.strftime("%Y-%m-%d", dates[-1]))
            if dates else "no dates")
    line = "%-9s %-26s %3d entries (%d binary), %s" % (name, tail, len(e.files), binary, span)
    out = [line + ("  !! " + "; ".join(problems) if problems else "")]
    extra = sorted(on_disc - listed)
    if extra:
        shown = ", ".join(extra[:6]) + (", ..." if len(extra) > 6 else "")
        out.append("          not in CVS: %d (%s)" % (len(extra), shown))
    return out


def cmd_info(dat):
    folders = sorted(n for n in os.listdir(dat)
                     if n != CVS_DIR and os.path.isdir(os.path.join(dat, n)))
    try:
        top = Entries(dat)
        problems = []
        if top.repository != REPO_PREFIX:
            problems.append("repository %s" % top.repository)
        names = {d.upper() for d in top.dirs}
        if names != {f.upper() for f in folders}:
            problems.append("folders listed %s, on the disc %s" % (
                sorted(names - {f.upper() for f in folders}),
                sorted({f.upper() for f in folders} - names)))
        line = "%-9s %-26s %d folders" % ("(top)", top.repository, len(top.dirs))
        print(line + ("  !! " + "; ".join(problems) if problems else ""))
    except (OSError, ValueError, IndexError) as err:
        print("(top)  !! %s" % err)
    for name in folders:
        path = os.path.join(dat, name)
        if not os.path.isdir(os.path.join(path, CVS_DIR)):
            print("%-9s !! no CVS folder" % name)
            continue
        for line in check_folder(path):
            print(line)


def cmd_list(folder):
    e = Entries(folder)
    print("repository %s" % e.repository)
    for name, rev, date, opts, tag in e.files:
        d = parse_date(date)
        print("%-34s %-6s %s %s" % (name, rev, time.strftime("%Y-%m-%d %H:%M:%S", d) if d else date,
                                    opts))
    for name in e.dirs:
        print("%s/" % name)


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "list" and len(args) == 1:
        cmd_list(args[0])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
