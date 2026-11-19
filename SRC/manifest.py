# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Build manifests: a small JSON file that says what a built disc or patch holds.

Every LMASTER build is a set of switches plus a few options (the club-eras
offset, the skip-tutorial nation, the font, the banner version) and the one
LMASTER seed (lmseed.py). From those the same disc comes out every time, so
a manifest that records them is enough to answer "which build were you on?"
in a bug report, to rebuild the same disc, and to see in plain words what a
build changes from the retail game.

The manifest is written next to the output by Build disc (the editor adds
`manifest.py make` after `patch_disc.py patch`), or by hand. It holds:

  edition   Lite, Full, Max or Custom (patch_disc.edition_title)
  switches  every switch the build turned on, with its group and description
  options   the flags a switch reads (--eras-offset, --skip-nation, ...)
  seed      the LMASTER seed
  tool      the repository's commit (when git is there) and LMASTER version
  writes    the file writes the build logged (with --log): file, what
            changed it, bytes that differ from the original (--no-writes
            leaves them out)
  patch     with --patch: the patch's name, size and SHA-256
  source    with --vanilla-sha1 (and --vanilla-redump): the disc it applies to
  executable_crc  the PCSX2 CRC of the built executable, read from the --log
            (what the widescreen patch and PCSX2's state folders are named by)

A release's manifest leaves out the date (--no-date) and the writes
(--no-writes), so building the same release again gives the same file.

Usage:
    python manifest.py make <out.json> [--mod <switch>,...] [--eras-offset <0-9>]
                        [--skip-nation <nation>] [--font <font.ttf>] [--realism <folder>]
                        [--version <x.y.z>] [--test-build] [--log <patch_disc output.txt>]
                        [--no-date] [--no-writes] [--patch <file.xdelta>]
                        [--vanilla-sha1 <hex>] [--vanilla-redump <number>]
    python manifest.py show <manifest.json>       # what this build changes from the retail game
    python manifest.py diff <a.json> <b.json>     # switches and options that differ
    python manifest.py rebuild <manifest.json>    # the patch_disc.py options that rebuild it
    python manifest.py check   <manifest.json> --mod <switch>,... [--font <f>] [--realism <d>]
                        [--version <x.y.z>] [--eras-offset <0-9>] [--commit <hash>]
                                                      # !! unless it holds exactly that build (and that commit)
    python manifest.py selftest                   # make, show, diff and rebuild round trip; !! on any difference

`--mod` takes the same names as patch_disc.py (editions, groups, switches).
`rebuild` prints only the options; add the disc, the output, the targets
(`<name>=<file>`) and --copies --dat yourself.
"""
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FORMAT = 1
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The line patch_disc.cmd_patch prints for each write it makes.
WRITE_LINE = re.compile(r"^(?P<path>.*?): (?P<label>.+?) <- (?P<why>.+), (?P<bytes>\d+) bytes differ")
# The line patch_disc.cmd_patch prints for the built executable.
CRC_LINE = re.compile(r"PCSX2 CRC of the executable (?P<crc>[0-9A-Fa-f]{8})")


def _opt(args, flag, default=None):
    """Remove `flag value` from `args` and return the value (as patch_disc._opt)."""
    if flag in args:
        i = args.index(flag)
        if i + 1 >= len(args):
            raise SystemExit("%s needs a value" % flag)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


def repo_commit():
    """The repository's short commit, "+" after it when the tools have uncommitted
    changes, or None when git or the repository is not there."""
    try:
        head = subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True, timeout=10)
        if head.returncode:
            return None
        dirty = subprocess.run(["git", "-C", ROOT, "status", "--porcelain", "--", "SRC"],
                               capture_output=True, text=True, timeout=10)
        return head.stdout.strip() + ("+" if dirty.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return None


def parse_log(text):
    """[{file, label, why, bytes}] for each write line in a patch_disc.py log."""
    out = []
    for line in text.splitlines():
        m = WRITE_LINE.match(line.strip())
        if m:
            out.append({"file": m["label"], "why": m["why"], "bytes": int(m["bytes"])})
    return out


def parse_crc(text):
    """The PCSX2 CRC of the executable a patch_disc.py log names, or None."""
    m = CRC_LINE.search(text)
    return m["crc"].upper() if m else None


def file_identity(path):
    """{name, size, sha256} of a file, as the release's patch is named."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return {"name": os.path.basename(path), "size": os.path.getsize(path), "sha256": h.hexdigest()}


def build(mods, options, log_text=None, date=True, writes=True, patch=None, source=None):
    """The manifest dict for the switch names `mods` (already resolved) and the
    `options` dict of flags that were given. `date` False leaves out the time, `writes`
    False the file writes of the log, `patch` is file_identity's dict of the patch and
    `source` {sha1, redump} of the disc it applies to."""
    import lmseed
    import patch_disc
    group_of = {}
    for name, title, members in patch_disc.GROUPS:
        for switch in members:
            group_of.setdefault(switch, (name, title))
    text = {s[0]: s[3] for s in patch_disc.SWITCHES}
    switches = []
    for name in patch_disc.SWITCH_NAMES:          # table order, so two manifests compare line by line
        if name in mods:
            group, title = group_of.get(name, ("", ""))
            switches.append({"name": name, "group": group, "group_title": title,
                             "what": text.get(name, "")})
    manifest = {
        "format": FORMAT,
        "edition": patch_disc.edition_title(mods),
        "switches": switches,
        "options": {k: v for k, v in sorted(options.items()) if v not in (None, False)},
        "seed": "0x%08X" % lmseed.SEED,
        "tool": {"commit": repo_commit(), "version": options.get("version")},
    }
    if date:
        manifest["created"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    if patch:
        manifest["patch"] = patch
    if source:
        manifest["source"] = source
    if log_text is not None:
        crc = parse_crc(log_text)
        if crc:
            manifest["executable_crc"] = crc
        if writes:
            manifest["writes"] = parse_log(log_text)
    return manifest


def load(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("format") != FORMAT:
        raise SystemExit("%s: not a format %d manifest" % (path, FORMAT))
    return data


def show_text(m):
    """Plain-English lines: the edition, then each group's switches with what they change."""
    tool = m.get("tool", {})
    lines = ["%s build%s" % (m["edition"],
                            " (version %s)" % tool["version"] if tool.get("version") else ""),
             "%sfrom tools commit %s, seed %s" % (
                 "made %s " % m["created"] if m.get("created") else "",
                 tool.get("commit") or "unknown", m.get("seed", "?"))]
    if m.get("patch"):
        lines.append("patch %s, %d bytes, SHA-256 %s" % (m["patch"]["name"], m["patch"]["size"],
                                                         m["patch"]["sha256"]))
    if m.get("source"):
        lines.append("applies to the disc with SHA-1 %s%s" % (
            m["source"]["sha1"], " (Redump %s)" % m["source"]["redump"] if m["source"].get("redump") else ""))
    if m.get("executable_crc"):
        lines.append("PCSX2 CRC of the executable: %s" % m["executable_crc"])
    by_group = {}                      # a group's switches may not sit together in the table
    for s in m["switches"]:
        by_group.setdefault(s["group"], (s["group_title"], []))[1].append(s)
    groups = [(g, title, members) for g, (title, members) in by_group.items()]
    lines.append("")
    lines.append("%d switches in %d groups change the retail game:" % (len(m["switches"]), len(groups)))
    for _, title, members in groups:
        lines.append("")
        lines.append("%s" % (title or "Other"))
        for s in members:
            lines.append("  %-20s %s" % (s["name"], s["what"]))
    if m.get("options"):
        lines += ["", "Options: " + ", ".join("%s=%s" % kv for kv in m["options"].items())]
    if "writes" in m:
        files = sorted({w["file"] for w in m["writes"]})
        lines += ["", "%d writes to %d files; %d bytes differ from the original" % (
            len(m["writes"]), len(files), sum(w["bytes"] for w in m["writes"]))]
    return lines


def diff_text(a, b):
    """Lines saying which switches and options differ between manifests `a` and `b`."""
    names_a = {s["name"] for s in a["switches"]}
    names_b = {s["name"] for s in b["switches"]}
    lines = ["%s -> %s" % (a["edition"], b["edition"])]
    for name in sorted(names_b - names_a):
        lines.append("  + %s" % name)
    for name in sorted(names_a - names_b):
        lines.append("  - %s" % name)
    for key in sorted(set(a["options"]) | set(b["options"])):
        if a["options"].get(key) != b["options"].get(key):
            lines.append("  option %s: %s -> %s" % (key, a["options"].get(key), b["options"].get(key)))
    for key in ("seed",):
        if a.get(key) != b.get(key):
            lines.append("  %s: %s -> %s" % (key, a.get(key), b.get(key)))
    if len(lines) == 1:
        lines.append("  no difference in switches, options or seed")
    return lines


def rebuild_args(m):
    """The patch_disc.py options that rebuild the manifest's disc."""
    import patch_disc
    mods = patch_disc.mod_names({s["name"] for s in m["switches"]})
    out = ["--mod", ",".join(mods)] if mods else []
    for key in ("eras-offset", "skip-nation", "font", "realism", "version"):
        if key in m["options"]:
            out += ["--" + key, str(m["options"][key])]
    if m["options"].get("test-build"):
        out.append("--test-build")
    return out


def options_from(args):
    """(mods, options) from the make command's flags; `args` is consumed."""
    import patch_disc
    values = []
    while "--mod" in args:
        values.append(_opt(args, "--mod"))
    options = {k: _opt(args, "--" + k) for k in ("eras-offset", "skip-nation", "font", "realism",
                                                 "version")}
    if options["font"]:
        values.append("modern-font")
    if options["realism"]:
        values.append("realism")
    options["test-build"] = "--test-build" in args
    if options["test-build"]:
        args.remove("--test-build")
    # Keep the path's last part only: a manifest is shared, a home folder name is not.
    for key in ("font", "realism"):
        if options[key]:
            options[key] = os.path.basename(os.path.normpath(options[key]))
    return patch_disc.parse_mods(values), options


def _flag(args, name):
    if name in args:
        args.remove(name)
        return True
    return False


def cmd_make(out, args):
    log_path = _opt(args, "--log")
    patch_path = _opt(args, "--patch")
    sha1 = _opt(args, "--vanilla-sha1")
    redump = _opt(args, "--vanilla-redump")
    date = not _flag(args, "--no-date")
    writes = not _flag(args, "--no-writes")
    mods, options = options_from(args)
    if args:
        raise SystemExit("unknown option %s" % args[0])
    patch = file_identity(patch_path) if patch_path else None
    source = None
    if sha1:
        source = {"sha1": sha1.lower()}
        if redump:
            source["redump"] = redump
    log_text = None
    if log_path:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            log_text = f.read()
    manifest = build(mods, options, log_text, date, writes, patch, source)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print("%s: %s build, %d switches" % (out, manifest["edition"], len(manifest["switches"])))


def check_problems(path, args):
    """The problems (a list of sentences) unless the manifest holds exactly the build `--mod`
    (with the options) names, and, with --commit, was made from that commit with no
    uncommitted tools."""
    commit = _opt(args, "--commit")
    mods, options = options_from(args)
    if args:
        raise SystemExit("unknown option %s" % args[0])
    m = load(path)
    bad = []
    have = {s["name"] for s in m["switches"]}
    for name in sorted(mods - have):
        bad.append("missing switch %s" % name)
    for name in sorted(have - mods):
        bad.append("extra switch %s" % name)
    for key in ("eras-offset", "skip-nation", "font", "realism", "version", "test-build"):
        want = options.get(key)
        got = m["options"].get(key)
        if (want in (None, False)) != (got in (None, False)) or (want not in (None, False) and str(want) != str(got)):
            bad.append("option %s is %s, expected %s" % (key, got, want))
    if commit:
        got = m.get("tool", {}).get("commit") or ""
        if got.endswith("+"):
            bad.append("tools commit %s has uncommitted changes" % got)
        elif not got or not commit.startswith(got) and not got.startswith(commit):
            bad.append("tools commit is %s, expected %s" % (got or "unknown", commit[:12]))
    return bad, m["edition"]


def cmd_check(path, args):
    """Print the problems of check_problems as !! lines; 1 if there are any."""
    bad, edition = check_problems(path, args)
    for line in bad:
        print("  !! " + line)
    if not bad:
        print("%s: the %s build, as named" % (path, edition))
    return 1 if bad else 0


def cmd_selftest():
    import tempfile
    problems = 0

    def check(ok, what):
        nonlocal problems
        print("%s%s" % (what, "" if ok else "  !! differs"))
        problems += not ok

    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        import patch_disc
        args = ["--mod", "lmaster-max", "--version", "1.2.3"]
        mods, options = options_from(args)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(build(mods, options), f)
        m = load(path)                            # written and read back as make and show do
        check(m["edition"] == "Max", "edition of --mod lmaster-max is Max")
        check({s["name"] for s in m["switches"]} == set(patch_disc.SWITCH_GROUPS["lmaster-max"]
                                                        ) | patch_disc.implied(
            patch_disc.SWITCH_GROUPS["lmaster-max"]), "switches are the edition's, with what they imply")
        rebuilt = rebuild_args(m)
        check(rebuilt[0] == "--mod" and patch_disc.parse_mods([rebuilt[1]]) ==
              {s["name"] for s in m["switches"]}, "rebuild's --mod parses back to the same switches")
        check("1.2.3" in show_text(m)[0], "show names the version")
        lite = build(patch_disc.parse_mods(["lmaster-lite"]), {})
        d = diff_text(lite, m)
        check(any(line.startswith("  + ") for line in d), "diff lite -> max lists added switches")
        check(diff_text(m, m)[-1].endswith("no difference in switches, options or seed"),
              "diff of a manifest with itself is empty")
        log = ("out.iso: SLES_541.51 <- --mod press-tendency, 12 bytes differ from the original\n"
               "C:\\x\\out.iso: DAT/A.PAC <- --mod real-names, 0 bytes differ from the original (no change)\n")
        crc = parse_crc("x\nout.iso: PCSX2 CRC of the executable 4F04F1DD (was 3CB245D5); PCSX2 keeps\n")
        check(crc == "4F04F1DD", "the executable's CRC is read from a patch_disc log")
        crc_log = log + "out.iso: PCSX2 CRC of the executable 4F04F1DD (was 3CB245D5); PCSX2 keeps\n"
        rel = build(mods, options, crc_log, date=False, writes=False,
                    patch={"name": "p.xdelta", "size": 3, "sha256": "ab" * 32},
                    source={"sha1": "cd" * 20, "redump": "12334"})
        check("created" not in rel and "writes" not in rel and rel.get("executable_crc") == "4F04F1DD",
              "a release manifest has no date and no writes, and keeps the executable's CRC")
        again = build(mods, options, crc_log, date=False, writes=False,
                      patch=rel["patch"], source=rel["source"])
        check(rel == again, "a release manifest is the same every time it is built")
        check(any("SHA-256" in line for line in show_text(rel)), "show names the patch")
        fd2, path2 = tempfile.mkstemp(suffix=".json")
        os.close(fd2)
        try:
            with open(path2, "w", encoding="utf-8") as f2:
                json.dump(build(patch_disc.parse_mods(["lmaster-max"]), {"version": "1.2.3"}, date=False), f2)
            check(not check_problems(path2, ["--mod", "lmaster-max", "--version", "1.2.3"])[0],
                  "check accepts the build it holds")
            check(bool(check_problems(path2, ["--mod", "lmaster-full", "--version", "1.2.3"])[0]),
                  "check refuses another edition")
        finally:
            os.remove(path2)
        w = parse_log(log)
        check([(x["file"], x["bytes"]) for x in w] == [("SLES_541.51", 12), ("DAT/A.PAC", 0)],
              "write lines of a patch_disc log parse")
    finally:
        os.remove(path)
    return 1 if problems else 0


def main(argv):
    cmd = argv[1] if len(argv) > 1 else ""
    args = argv[2:]
    if cmd == "make" and args:
        cmd_make(args[0], args[1:])
        return 0
    if cmd == "show" and len(args) == 1:
        print("\n".join(show_text(load(args[0]))))
        return 0
    if cmd == "diff" and len(args) == 2:
        print("\n".join(diff_text(load(args[0]), load(args[1]))))
        return 0
    if cmd == "rebuild" and len(args) == 1:
        print(" ".join(rebuild_args(load(args[0]))))
        return 0
    if cmd == "check" and len(args) >= 2:
        return cmd_check(args[0], args[1:])
    if cmd == "selftest" and not args:
        return cmd_selftest()
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
