"""Regression check: run every tool's layout check over the data and compare
the output with a saved baseline.

Every `info` marks a problem with '!!' on the line it concerns, but a clean
'!!'-free run isn't the goal: the disc has known quirks (the stale
PLAYERMOTION.HED, TBB tables with trailing bytes, an empty CSP) that are
marked and expected. So this records each check's full output once (`bless`)
and afterwards fails on any difference, which catches new '!!' lines as well
as changed counts and parse results that shift after a code change.

Nothing passes on its own. A '!!' line that disappears fails the run just
like a new one: it may be a fix, or a check that stopped running, and only
a person can tell which. `run` lists '!!' lines that appeared or disappeared
before the diff, and `bless` prints each check's '!!' count (old -> new), so
the review starts from the problems.

A check also fails if it exits non-zero, writes to stderr, or its input is
missing.

Baselines are written to .regress/ (git-ignored: they list file names and
counts from your copy of the disc). Paths are normalised to '/' so a baseline
made on Windows matches on other systems.

Usage:
    python SRC/regress.py list                     # the checks and their commands
    python SRC/regress.py run   [name ...] [--full] # compare with the baseline (exit 1 on any failure)
    python SRC/regress.py bless [name ...]          # save the current output as the baseline

Names select checks by prefix, e.g. `run snr2` runs every overlay check.
--full prints the whole diff instead of the first 40 lines per check.
"""
import difflib
import glob
import os
import subprocess
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE_DIR = os.path.join(ROOT, ".regress")
DIFF_LINES = 40


def checks():
    """(name, [tool, args...], [required inputs]) for every check."""
    out = [
        ("pac", ["pac.py", "info", "DAT"], ["DAT"]),
        ("tbb", ["tbb.py", "info", "DAT"], ["DAT"]),
        ("tbb_roundtrip", ["tbb.py", "roundtrip", "DAT"], ["DAT"]),
        ("initteam", ["initteam.py", "info", "DAT/PARAM"], ["DAT/PARAM"]),
        ("pbdata", ["pbdata.py", "info", "DAT/PARAM/PBDATA_EU.PAC", "DAT/PARAM/PBDATA_JP.PAC"],
         ["DAT/PARAM/PBDATA_EU.PAC", "DAT/PARAM/PBDATA_JP.PAC"]),
        # Every field of the first and last record of each kind.
        ("pbdata_show", ["pbdata.py", "show", "DAT/PARAM/PBDATA_EU.PAC",
                         "0", "p:27949", "m:0", "m:2999", "s:0", "s:999"],
         ["DAT/PARAM/PBDATA_EU.PAC", "DAT/MESSAGE/MES.PAC"]),
        # Club names from MES.PAC category 3 against the division lists.
        ("initteam_leagues", ["initteam.py", "leagues", "DAT/PARAM"],
         ["DAT/PARAM", "DAT/MESSAGE/MES.PAC"]),
        ("packdata", ["packdata.py", "info", "DAT"], ["DAT"]),
        ("schedule", ["schedule.py", "info", "DAT/PARAM"], ["DAT/PARAM"]),
        ("stadium", ["stadium.py", "info", "DAT/STADIUM", "DAT/PARAM"],
         ["DAT/STADIUM", "DAT/PARAM"]),
        ("svr", ["svr.py", "info", "DAT"], ["DAT"]),
        ("csp", ["csp.py", "info", "DAT"], ["DAT"]),
        ("zbf", ["zbf.py", "info", "DAT"], ["DAT"]),
        ("ninja", ["ninja.py", "info", "DAT"], ["DAT"]),
        ("mbb", ["mbb.py", "info", "DAT/MESSAGE/MES.PAC"], ["DAT/MESSAGE/MES.PAC"]),
        ("sounddat", ["sounddat.py", "info", "DAT/GAME/SOUNDDAT.PAC"], ["DAT/GAME/SOUNDDAT.PAC"]),
        ("eventdata_turn", ["eventdata_turn.py", "DAT/EVENT/EVENTDATA_TURN.TBB"],
         ["DAT/EVENT/EVENTDATA_TURN.TBB"]),
        ("sles_syms", ["sles_disasm.py", "ISO/SLES_541.51", "syms", "CMsgSubCategory"],
         ["ISO/SLES_541.51"]),
        ("sles_relocs", ["sles_disasm.py", "ISO/SLES_541.51", "relocs"], ["ISO/SLES_541.51"]),
    ]
    mes = "DAT/MESSAGE/MES.PAC"
    for kind in ("EVENT", "NEWS", "MAIL"):
        p = "DAT/EVENT/EVSDATABIN_%s.BIN" % kind
        out.append(("evsdatabin_" + kind.lower(), ["evsdatabin.py", p], [p]))
        # The message references each table resolves differ (EVENT dialogue,
        # NEWS body/headline, MAIL sender/recipient/subject/body).
        out.append(("evsdatabin_text_" + kind.lower(),
                    ["evsdatabin.py", p, "--text", mes], [p, mes]))
    # Each SOUND/*.DAT is one ps2_DTPK bank; dtpk takes a single file.
    banks = sorted(glob.glob(os.path.join(ROOT, "DAT", "SOUND", "*.DAT")))
    if not banks:
        out.append(("sounddat_dtpk", ["sounddat.py", "dtpk", "DAT/SOUND/*.DAT"], ["DAT/SOUND"]))
    for b in banks:
        name = os.path.splitext(os.path.basename(b))[0].lower()
        p = "DAT/SOUND/" + os.path.basename(b)
        out.append(("sounddat_dtpk_" + name, ["sounddat.py", "dtpk", p], [p]))
    rels = sorted(glob.glob(os.path.join(ROOT, "ISO", "DLL", "*.REL")))
    if not rels:
        out.append(("snr2", ["snr2.py", "info", "ISO/DLL/*.REL"], ["ISO/DLL"]))
    for r in rels:
        name = os.path.splitext(os.path.basename(r))[0].lower()
        p = "ISO/DLL/" + os.path.basename(r)
        out.append(("snr2_" + name, ["snr2.py", "info", p], [p]))
    return out


def select(names):
    all_checks = checks()
    if not names:
        return all_checks
    picked = [c for c in all_checks if any(c[0].startswith(n) for n in names)]
    unknown = [n for n in names if not any(c[0].startswith(n) for c in all_checks)]
    if unknown:
        raise SystemExit("unknown check(s): %s" % ", ".join(unknown))
    return picked


def normalise(text):
    return text.replace("\r\n", "\n").replace("\\", "/")


def run_check(argv, inputs):
    """Returns (output, errors). errors is a list of reasons the check itself
    failed, independent of the baseline."""
    missing = [p for p in inputs if not os.path.exists(os.path.join(ROOT, p))]
    if missing:
        return "", ["missing input: " + ", ".join(missing)]
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    cmd = [sys.executable, os.path.join(ROOT, "SRC", argv[0])] + argv[1:]
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True)
    out = normalise(proc.stdout.decode("utf-8", "replace"))
    err = proc.stderr.decode("utf-8", "replace").strip()
    errors = []
    if proc.returncode != 0:
        errors.append("exit code %d" % proc.returncode)
    if err:
        errors.append("stderr:\n" + "\n".join("    " + l for l in err.splitlines()[-15:]))
    return out, errors


def baseline_path(name):
    return os.path.join(BASELINE_DIR, name + ".txt")


def load_baseline(name):
    p = baseline_path(name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", newline="") as f:
        return f.read()


def problem_lines(text):
    return Counter(l.strip() for l in text.splitlines() if "!! " in l)


def problem_changes(base, out):
    """Lines describing '!!' lines that appeared or disappeared. Both fail the
    run: a new one is a regression, and a vanished one needs review too,
    because it means either a fix or a check that silently stopped running."""
    old, new = problem_lines(base), problem_lines(out)
    lines = []
    for label, gone in (("new problem", new - old),
                        ("problem gone (fixed, or the check stopped running?)", old - new)):
        for l in sorted(gone.elements()):
            lines.append("%s: %s" % (label, l))
    return lines


def cmd_list():
    for name, argv, _ in checks():
        mark = " " if load_baseline(name) is not None else "*"
        print("%s %-22s python SRC/%s" % (mark, name, " ".join(argv)))
    print("(* = no baseline yet)")


def cmd_run(names, full):
    failed = []
    for name, argv, inputs in select(names):
        out, errors = run_check(argv, inputs)
        base = load_baseline(name)
        if base is None:
            errors.append("no baseline (run `bless %s`)" % name)
        elif errors:
            pass  # a crash or missing input already explains it; the diff is noise
        elif out != base:
            errors.extend(problem_changes(base, out))
            diff = list(difflib.unified_diff(
                base.splitlines(), out.splitlines(),
                "baseline/" + name, "current/" + name, lineterm="", n=1))
            if not full and len(diff) > DIFF_LINES:
                diff = diff[:DIFF_LINES] + ["... %d more diff lines (--full)" % (len(diff) - DIFF_LINES)]
            errors.append("output differs from baseline:\n" + "\n".join("    " + l for l in diff))
        if errors:
            failed.append(name)
            print("FAIL  %s" % name)
            for e in errors:
                print("  " + e)
        else:
            print("ok    %s" % name)
    total = len(select(names))
    print("%d/%d checks passed" % (total - len(failed), total))
    return 1 if failed else 0


def cmd_bless(names):
    os.makedirs(BASELINE_DIR, exist_ok=True)
    status = 0
    for name, argv, inputs in select(names):
        out, errors = run_check(argv, inputs)
        if errors:
            # Never bless a crash: a baseline has to come from a clean run.
            print("skip  %s: %s" % (name, "; ".join(e.splitlines()[0] for e in errors)))
            status = 1
            continue
        old = load_baseline(name)
        with open(baseline_path(name), "w", encoding="utf-8", newline="") as f:
            f.write(out)
        what = "new" if old is None else ("unchanged" if old == out else "updated")
        n_new = sum(problem_lines(out).values())
        count = "!! %d" % n_new
        if old is not None:
            n_old = sum(problem_lines(old).values())
            if n_old != n_new:
                count = "!! %d -> %d" % (n_old, n_new)
        print("%-9s %s (%d lines, %s)" % (what, name, out.count("\n"), count))
    return status


def main(argv):
    args = argv[1:]
    full = "--full" in args
    args = [a for a in args if a != "--full"]
    if not args:
        print(__doc__)
        return 2
    cmd, names = args[0], args[1:]
    if cmd == "list":
        cmd_list()
        return 0
    if cmd == "run":
        return cmd_run(names, full)
    if cmd == "bless":
        return cmd_bless(names)
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
