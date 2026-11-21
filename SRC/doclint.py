# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Stale-claim linter for the project's Markdown: the checks AGENTS.md asks for before a
change is finished ("Before you finish"), made by a tool so nobody has to grep.

Four kinds of claim, each reported with `!!` on the line it concerns (file:line):

  links      every relative link [text](file.md#anchor) points at a file that exists
             and, with an #anchor, at a heading that exists there (GitHub's slug: lower
             case, punctuation dropped, spaces to hyphens, repeats numbered -1, -2).
             Links in fenced code blocks and external links are left alone.
  commands   every `python SRC/<tool>.py <command> ...` (in a code block or in code
             quotes) names a tool in SRC/ and, where the first word is a command and not a
             path, a command the tool's source knows (a quoted word in it); every SRC/
             path given as an argument exists.
  symbols    every `python SRC/sles_disasm.py ISO/SLES_541.51 dis|syms <text>` finds a
             symbol of the executable and every `addr <hex>` lies in its code, so the
             addresses a doc tells the reader to disassemble still resolve (through
             gamever.py: each such PAL address is also looked up in ISO_JP/, and one the
             Japanese build lacks is a note, not a `!!`, since PAL-only code is real).
  style      no em dash (U+2014) in a tracked .md or .py; every .py in SRC/ starts with
             the two SPDX lines and every tracked .md with the two SPDX comments
             (LMAST_DATA_CVM_INFO.md, an outside write-up kept as received, is left out).

What it does not check: whether a claim about the game is true (that is `regress.py`'s and
the docs' evidence), and whether a "Still unknown" item has been answered (a person reads
those). `symbols` needs ISO/ (and ISO_JP/ for the Japanese notes); without it that check is
skipped with a note.

Usage:
    python SRC/doclint.py info [<kind> ...]     # all four kinds, or only the ones named; !! on a problem
    python SRC/doclint.py anchors <file.md>     # the anchors a file offers, to write a link by
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPDX_MD = ("<!-- SPDX-License-Identifier: GPL-3.0-or-later -->", "<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->")
SPDX_PY = ("# SPDX-License-Identifier: GPL-3.0-or-later", "# Copyright (C) 2026 Nexxus Drako Multimedia")
OUTSIDE = {"DOC/LMAST_DATA_CVM_INFO.md"}                # kept as it was received
SKIP_DIRS = {".git", ".cache", ".regress", "mod", "mods", "names", "DAT", "DAT_JP", "ISO", "ISO_JP", "node_modules"}
EM_DASH = chr(0x2014)
KINDS = ("links", "commands", "symbols", "style")


def tracked(ext):
    """The tracked files with extension `ext` (git ls-files; else a walk that skips the data folders)."""
    try:
        out = subprocess.run(["git", "ls-files", "*" + ext], cwd=ROOT, capture_output=True, check=True).stdout
        return sorted(p for p in out.decode("utf-8").split("\n") if p)
    except (OSError, subprocess.CalledProcessError):
        found = []
        for folder, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            found += [os.path.relpath(os.path.join(folder, f), ROOT).replace("\\", "/")
                      for f in files if f.endswith(ext)]
        return sorted(found)


def read_lines(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read().split("\n")


def prose(lines):
    """[(line number, text)] of the lines outside fenced code blocks."""
    out, fenced = [], False
    for n, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append((n, line))
    return out


# --- anchors ---------------------------------------------------------------------------------

def slug(heading):
    """GitHub's anchor for a heading's text: markup dropped, lower case, anything but letters,
    digits, spaces, hyphens and underscores removed, spaces to hyphens."""
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)      # a link keeps its text
    text = text.replace("`", "").replace("*", "")
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text, flags=re.UNICODE)
    return text.replace(" ", "-")


def anchors_of(rel, cache={}):
    """The set of anchors a Markdown file offers (repeated headings get -1, -2, ...)."""
    if rel not in cache:
        seen, out = {}, set()
        for _, line in prose(read_lines(rel)):
            m = re.match(r"^#{1,6}\s+(.*?)\s*#*\s*$", line)
            if m:
                base = slug(m.group(1))
                n = seen.get(base, 0)
                seen[base] = n + 1
                out.add(base if n == 0 else "%s-%d" % (base, n))
        cache[rel] = out
    return cache[rel]


LINK = re.compile(r"(?<!\!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")


def check_links(md):
    bad = []
    for rel in md:
        base = os.path.dirname(rel)
        for n, line in prose(read_lines(rel)):
            # inline code is not a link
            for target in LINK.findall(re.sub(r"`[^`]*`", "", line)):
                if re.match(r"^(https?:|mailto:|ftp:)", target):
                    continue
                path, _, anchor = target.partition("#")
                dest = rel if not path else os.path.normpath(os.path.join(base, path)).replace("\\", "/")
                if path and not os.path.exists(os.path.join(ROOT, dest)):
                    bad.append("%s:%d  !! link to %s: no such file" % (rel, n, path))
                elif anchor and dest.endswith(".md") and anchor not in anchors_of(dest):
                    bad.append("%s:%d  !! link to %s#%s: no such heading" % (rel, n, dest, anchor))
    return bad


# --- commands --------------------------------------------------------------------------------

CMD = re.compile(r"python3?\s+(SRC/(\w+)\.py)((?:\s+[^\s`|;&<>()]+)*)")


def tool_words(tool, cache={}):
    """The quoted words of a tool's source (its commands, among them)."""
    if tool not in cache:
        path = os.path.join(ROOT, "SRC", tool + ".py")
        if not os.path.exists(path):
            cache[tool] = None
        else:
            with open(path, encoding="utf-8") as f:
                src = f.read()
            cache[tool] = set(re.findall(r"[\"']([A-Za-z][\w-]*)[\"']", src)) | set(
                re.findall(r"python[0-9]? \w+\.py ([a-z][\w-]*)", src))
    return cache[tool]


def commands(md):
    """[(file, line, tool, args)] for every python SRC/<tool>.py command in the docs."""
    found = []
    for rel in md:
        lines = read_lines(rel)
        fenced = False
        for n, line in enumerate(lines, 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            for m in CMD.finditer(re.sub(r"\s#(\s.*)?$", "", line)):      # a shell comment is not an argument
                args = [a for a in m.group(3).split() if a]
                found.append((rel, n, m.group(2), args))
    return found


def check_commands(md):
    bad = []
    for rel, n, tool, args in commands(md):
        words = tool_words(tool)
        if words is None:
            bad.append("%s:%d  !! python SRC/%s.py: no such tool" % (rel, n, tool))
            continue
        # the first word is a command when it is a bare lower-case word (no path, no option)
        if args and re.match(r"^[a-z][a-z0-9_-]*$", args[0]) and args[0] not in words:
            bad.append("%s:%d  !! python SRC/%s.py %s: the tool has no such command" % (rel, n, tool, args[0]))
        for a in args:
            a = a.strip(",.")
            if a.startswith("SRC/") and "<" not in a and "*" not in a and not os.path.exists(os.path.join(ROOT, a)):
                bad.append("%s:%d  !! python SRC/%s.py ... %s: no such file" % (rel, n, tool, a))
    return bad


# --- symbols ---------------------------------------------------------------------------------

def check_symbols(md):
    """The disassembly commands of the docs against the executable's symbols and code."""
    notes, bad = [], []
    exe = os.path.join(ROOT, "ISO", "SLES_541.51")
    if not os.path.exists(exe):
        return ["note: symbols: ISO/SLES_541.51 not found, skipped"], []
    sys.path.insert(0, os.path.join(ROOT, "SRC"))
    import sles_disasm
    elf = sles_disasm.Elf(exe)
    syms = sles_disasm.recover_symbols(elf)
    text_lo, text_size = elf.sections[".text"]
    jp = os.path.join(ROOT, "ISO_JP", "SLPM_663.16")
    gamever = None
    if os.path.exists(jp):
        import gamever
    for rel, n, tool, args in commands(md):
        if tool != "sles_disasm" or len(args) < 3 or args[0] != "ISO/SLES_541.51":
            continue
        cmd, rest = args[1], args[2:]
        if cmd in ("dis", "syms"):
            for pat in rest:
                if pat.startswith("<") or pat.startswith("-"):
                    continue
                if not any(pat in name for name in syms):
                    bad.append("%s:%d  !! sles_disasm %s %s: no symbol of the executable contains that" % (rel, n, cmd, pat))
        elif cmd == "addr" and re.match(r"^[0-9a-fA-Fx]+$", rest[0]) and not rest[0].startswith("<"):
            addr = int(rest[0], 16)
            if not text_lo <= addr < text_lo + text_size:
                bad.append("%s:%d  !! sles_disasm addr %s: not in the executable's code" % (rel, n, rest[0]))
            elif gamever is not None:
                try:
                    gamever.at(jp, addr)
                except ValueError:
                    notes.append("%s:%d  note: address %s has no counterpart in the Japanese build" % (rel, n, rest[0]))
    return notes, bad


# --- style -----------------------------------------------------------------------------------

def check_style(md, py):
    bad = []
    for rel in md + py:
        if rel in OUTSIDE:
            continue
        lines = read_lines(rel)
        for n, line in enumerate(lines, 1):
            if EM_DASH in line:
                bad.append("%s:%d  !! em dash (rebuild the sentence: full stop, comma, colon or brackets)" % (rel, n))
    for rel in md:
        if rel in OUTSIDE or rel in ("CLAUDE.md",):
            continue
        if tuple(read_lines(rel)[:2]) != SPDX_MD:
            bad.append("%s:1  !! does not start with the two SPDX comment lines" % rel)
    for rel in py:
        if rel.startswith("SRC/") and tuple(read_lines(rel)[:2]) != SPDX_PY:
            bad.append("%s:1  !! does not start with the two SPDX lines" % rel)
    return bad


# --- commands --------------------------------------------------------------------------------

def cmd_info(kinds):
    kinds = kinds or KINDS
    unknown = [k for k in kinds if k not in KINDS]
    if unknown:
        print("unknown kind %s; the kinds are %s" % (", ".join(unknown), ", ".join(KINDS)))
        return 2
    md, py = tracked(".md"), tracked(".py")
    py = [p for p in py if p.startswith("SRC/")]
    problems = 0
    for kind in kinds:
        notes = []
        if kind == "links":
            bad = check_links(md)
        elif kind == "commands":
            bad = check_commands(md)
        elif kind == "symbols":
            notes, bad = check_symbols(md)
        else:
            bad = check_style(md, py)
        for line in notes:
            print(line)
        for line in bad:
            print(line)
        problems += len(bad)
        print("%-9s %s" % (kind, "%d problems" % len(bad) if bad else "no problems"))
    return 1 if problems else 0


def cmd_anchors(path):
    rel = os.path.relpath(os.path.abspath(path), ROOT).replace("\\", "/")
    for a in sorted(anchors_of(rel)):
        print("%s#%s" % (rel, a))
    return 0


def main(argv):
    if len(argv) >= 2 and argv[1] == "info":
        return cmd_info(argv[2:])
    if len(argv) == 3 and argv[1] == "anchors":
        return cmd_anchors(argv[2])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
