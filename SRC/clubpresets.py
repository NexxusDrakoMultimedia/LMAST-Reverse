# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The club-creation presets of CEDITPRG.REL, and the kit standard of LMASTER's club-eras for them.

When you create a club, CSelectTeamColorModule (ISO/DLL/CEDITPRG.REL, function 0x20b0) copies
one of 32 presets, chosen by the 32-colour palette id (an id of 0x20 or more takes preset 0,
0x2114), into your club's PlUnif with pwkTeam_SetUnif (0x20fc). Each preset is 0x50 bytes, from
file offset 0x150a0; the rival's fixed kit record (team 2, set at 0x2124) follows at 0x15aa0. All
32 use shirt design 206, shorts 60 and socks 14; the retail home side bytes are 0 1 0 0 0 1 and
the away 1 0 1 0 1 0, so both kits start with the front number off. The computer clubs get the
kit standard of kiteras.py (front number on, valid coupled emblems, number and band colours
chosen against the kit's colours), which the sponsors' and kit code writes at pwkTeam_GetUnif
for teams 3-441 only: this module gives your club and the rival the same standard by patching
the preset bytes (DOC/UNIFORM_FORMAT.md, DOC/LMASTER_MOD.md "Kit standards").

  PlUnif   +0 flag, +4 sponsor, +5 supplier (the sponsor functions overwrite these at SetUnif:
           left alone), home PlUnifGame at +6: six side bytes (+6..+0xb), the keeper kit
           (+0xc..+0x1a) and the outfield kit (+0x1b..+0x29); away at +0x2a: side bytes
           (+0x2a..+0x2f), keeper kit (+0x30..+0x3e), outfield kit (+0x3f..+0x4d)
  side     0 shirt emblem type (0-2; 2 shows none: never used), 1 shorts emblem type (0-2),
           2 number design (0-7), 3 front number (1 = on), 4 position on the shorts (0 and 1 show
           the number, 2 is off; the editor couples the shorts emblem type v with position v),
           5 not used by a match
  kit      0 shirt design, 1-3 shirt colours, 4 collar, 5 shorts design, 6-8 shorts colours,
           9 socks design, 10-11 socks colours, 12 shirt number colour, 13 shorts number colour,
           14 captain's band

standard_presets() changes, in each outfield kit, the six side bytes (emblem types kept where
valid, else 0; the shorts position equal to the shorts emblem type; the number design kept; the
front number 1; byte 5 = 1, as the standard's code writes it) and kit fields 12-14: the number
colours picked by kiteras.pick_number for the preset's own shirt colours 1 and 2 (colour 1
alone for a plain design) and shorts colours 1 and 2, the band by kiteras.pick_band for the
shirt's colours 1 and 2. The collar and the number design stay. The keeper kits stay too: the
game builds a keeper kit for your club and the rival from UNIFORM_GK.TBB (DOC/UNIFORM_FORMAT.md).
The patches lie inside 0x150a0-0x15aef, where CEDITPRG.REL has no relocation site.

Japanese release: its CEDITPRG.REL holds the same records 0x100 lower (presets from 0x14fa0, the
rival at 0x159a0). Every function takes `shift`, the offset to add to the PAL constants for the file
at hand (0 for PAL; shift_of(path) finds it through gamever.py), and the commands work out the
shift from the file's path.

Usage (from the repo root; DAT is the extracted DATA.ISO, default "DAT"):
    python SRC/clubpresets.py info     <CEDITPRG.REL>        # each preset's key bytes (PAL or Japanese)
    python SRC/clubpresets.py patches  <CEDITPRG.REL> [DAT]  # the (offset, old, new) byte patches
    python SRC/clubpresets.py check    <CEDITPRG.REL> [DAT]  # every patched preset is valid, no clash
    python SRC/clubpresets.py selftest <CEDITPRG.REL> [DAT]  # patch, re-decode, compare

API: presets(rel, shift) -> (list of 32 dicts, rival dict); make_plan(dat) -> a stand-in for
kiteras' plan (.swatches, .clash); standard_presets(rel, plan, dat, shift) -> [(offset, old bytes,
new bytes)]; apply_patches(rel, patches) -> bytes; standard_rel(rel, plan, dat, shift) -> the patched
REL bytes; shift_of(path) -> the shift for the CEDITPRG.REL at `path`.
"""
import os
import struct
import sys

import kiteras

PRESET_OFFSET = 0x150A0
PRESET_COUNT = 32
PRESET_SIZE = 0x50
RIVAL_OFFSET = PRESET_OFFSET + PRESET_COUNT * PRESET_SIZE       # 0x15aa0
RECORDS = PRESET_COUNT + 1                                      # the 32 presets and the rival's record
SIDES = (("home", 0x06, 0x1B), ("away", 0x2A, 0x3F))            # name, side bytes, outfield kit
KEEPERS = (0x0C, 0x30)
SHIRT_DESIGN, SHORTS_DESIGN, SOCKS_DESIGN = 206, 60, 14         # what all 32 presets use
CLUBPRESETS_END = RIVAL_OFFSET + PRESET_SIZE


class Plan:
    """The two attributes kiteras.pick_number and pick_band read."""

    def __init__(self, swatches, clash):
        self.swatches, self.clash = swatches, clash


def make_plan(dat="DAT"):
    """kiteras' colour data for the DATA.ISO files in `dat`: 96 swatches and the 96 x 96 clash table."""
    import uniform
    return Plan(uniform.colour_swatches(os.path.join(dat, "PLAYER")), kiteras.clash_table(dat))


def shift_of(path):
    """The offset to add to the PAL constants for the CEDITPRG.REL at `path`: 0 for PAL's, -0x100 for
    the Japanese release's (found with gamever.at, so a file that has no counterpart raises ValueError)."""
    import gamever
    return gamever.at(path, PRESET_OFFSET) - PRESET_OFFSET


def record_offset(index, shift=0):
    """File offset of record 0-31 (a preset) or 32 (the rival's)."""
    if not 0 <= index < RECORDS:
        raise ValueError("record %d: 0-%d" % (index, RECORDS - 1))
    return PRESET_OFFSET + shift + index * PRESET_SIZE


def _record(rel, offset):
    rec = rel[offset:offset + PRESET_SIZE]
    out = {"offset": offset, "flag": struct.unpack_from("<I", rec, 0)[0], "sponsor": rec[4], "supplier": rec[5],
           "tail": rec[0x4E:]}
    for name, side, kit in SIDES:
        out[name] = {"side": tuple(rec[side:side + 6]), "outfield": tuple(rec[kit:kit + 15]),
                     "keeper": tuple(rec[KEEPERS[name == "away"]:KEEPERS[name == "away"] + 15])}
    return out


def presets(rel, shift=0):
    """([the 32 presets decoded], the rival's record decoded). Each is a dict: offset, flag, sponsor,
    supplier, tail (the 2 padding bytes), and per side 'home' and 'away' a dict of tuples: 'side' (6
    bytes), 'outfield' and 'keeper' (15 bytes each)."""
    if len(rel) < CLUBPRESETS_END + shift or rel[:4] != b"SNR2":
        raise ValueError("not a CEDITPRG.REL (an SNR2 file of at least 0x%x bytes)" % (CLUBPRESETS_END + shift))
    recs = [_record(rel, record_offset(i, shift)) for i in range(RECORDS)]
    return recs[:PRESET_COUNT], recs[PRESET_COUNT]


def standard_side(plan, side, kit):
    """(the six standard side bytes, the standard's kit bytes 12-14) for an outfield kit and its side bytes."""
    shirt_emb = side[0] if side[0] in (0, 1) else 0
    shorts_emb = side[1] if side[1] in (0, 1) else 0
    design = min(side[2], 7)
    shirt = (kit[1],) if kit[0] in kiteras.PLAIN else (kit[1], kit[2])      # a plain shirt shows colour 1 only
    numbers = (kiteras.pick_number(plan, shirt), kiteras.pick_number(plan, (kit[6], kit[7])),
               kiteras.pick_band(plan, (kit[1], kit[2])))
    return bytes((shirt_emb, shorts_emb, design, 1, shorts_emb, 1)), bytes(numbers)


def standard_presets(rel, plan=None, dat="DAT", shift=0):
    """[(file offset, old bytes, new bytes)]: the changes that give the 32 presets and the rival's record
    the kit standard (module docstring), per outfield kit a patch of the six side bytes and one of kit
    bytes 12-14, each only where it differs. 66 patches at most."""
    plan = plan or make_plan(dat)
    out = []
    for index in range(RECORDS):
        base = record_offset(index, shift)
        for name, side_at, kit_at in SIDES:
            old_side, old_kit = rel[base + side_at:base + side_at + 6], rel[base + kit_at:base + kit_at + 15]
            side, tail = standard_side(plan, old_side, old_kit)
            if side != old_side:
                out.append((base + side_at, bytes(old_side), side))
            if tail != old_kit[12:15]:
                out.append((base + kit_at + 12, bytes(old_kit[12:15]), tail))
    return out


def apply_patches(rel, patches):
    """The REL bytes with the patches applied; ValueError if a patch's old bytes are not what the file has."""
    out = bytearray(rel)
    for offset, old, new in patches:
        if len(old) != len(new) or bytes(out[offset:offset + len(old)]) != old:
            raise ValueError("patch at 0x%x: the file does not hold %s" % (offset, old.hex(" ")))
        out[offset:offset + len(new)] = new
    return bytes(out)


def standard_rel(rel, plan=None, dat="DAT", shift=0):
    """CEDITPRG.REL's bytes with every preset and the rival's record given the kit standard."""
    return apply_patches(rel, standard_presets(rel, plan, dat, shift))


def relocation_sites(path, lo=PRESET_OFFSET, hi=CLUBPRESETS_END, shift=0):
    """The relocation sites of the REL at `path` inside [lo + shift, hi + shift): none, for the records."""
    import snr2
    lo, hi = lo + shift, hi + shift
    m = snr2.Snr2(path)
    return sorted(set(s for s, *_ in m.ext if lo <= s < hi) | set(s for s, _ in m.local if lo <= s < hi))


def problems(rel, plan, shift=0):
    """[reason] for every record of `rel` that does not have the kit standard (empty: all do)."""
    bad = []
    recs = presets(rel, shift)
    for rec in recs[0] + [recs[1]]:
        who = "rival" if rec["offset"] == RIVAL_OFFSET + shift else "preset %d" % (
            (rec["offset"] - PRESET_OFFSET - shift) // PRESET_SIZE)
        for name, _, _ in SIDES:
            side, kit = rec[name]["side"], rec[name]["outfield"]
            tag = "%s %s" % (who, name)
            if side[0] not in (0, 1) or side[1] not in (0, 1):
                bad.append("%s: emblem type %d/%d" % (tag, side[0], side[1]))
            if side[2] > 7:
                bad.append("%s: number design %d" % (tag, side[2]))
            if side[3] != 1 or side[5] != 1:
                bad.append("%s: front number %d, side byte 5 is %d" % (tag, side[3], side[5]))
            if side[4] != side[1]:
                bad.append("%s: shorts position %d against emblem type %d" % (tag, side[4], side[1]))
            if kit[4] > 10:
                bad.append("%s: collar %d" % (tag, kit[4]))
            if kit[12] >= 96 or kit[13] >= 96 or kit[14] > 4:
                bad.append("%s: number colours %d/%d or band %d out of range" % (tag, kit[12], kit[13], kit[14]))
                continue
            shirt = (kit[1],) if kit[0] in kiteras.PLAIN else (kit[1], kit[2])
            for label, colour, bases in (("shirt number", kit[12], shirt), ("shorts number", kit[13], (kit[6], kit[7]))):
                if any(plan.clash[colour][b] for b in bases) and any(
                        not any(plan.clash[c][b] for b in bases) for c in kiteras.NUMBER_COLOURS):
                    bad.append("%s: %s colour %d clashes with %s" % (tag, label, colour, bases))
            if kit[14] != kiteras.pick_band(plan, (kit[1], kit[2])):
                bad.append("%s: band %d is not the best against the shirt" % (tag, kit[14]))
            if (kit[12], kit[13]) != (kiteras.pick_number(plan, shirt), kiteras.pick_number(plan, (kit[6], kit[7]))):
                bad.append("%s: number colours are not the standard's" % tag)
    return bad


def _show(rec, who):
    lines = []
    for name, _, _ in SIDES:
        side, kit = rec[name]["side"], rec[name]["outfield"]
        lines.append("  %-7s %-4s side %s  shirt %3d cols %02x %02x %02x collar %2d shorts %2d cols %02x %02x %02x"
                     "  numbers %02x/%02x band %d" % (who, name, " ".join("%d" % b for b in side), kit[0], kit[1],
                                                       kit[2], kit[3], kit[4], kit[5], kit[6], kit[7], kit[8],
                                                       kit[12], kit[13], kit[14]))
    return lines


def cmd_info(rel, shift=0):
    recs, rival = presets(rel, shift)
    print("%d presets from 0x%x, the rival's record at 0x%x" % (len(recs), PRESET_OFFSET + shift,
                                                                RIVAL_OFFSET + shift))
    designs = set()
    for i, rec in enumerate(recs + [rival]):
        for line in _show(rec, "rival" if i == PRESET_COUNT else "preset %d" % i):
            print(line)
        designs.add((rec["home"]["outfield"][0], rec["home"]["outfield"][5], rec["home"]["outfield"][9]))
    bad = []
    if {(r["home"]["outfield"][0], r["home"]["outfield"][5], r["home"]["outfield"][9]) for r in recs} != \
            {(SHIRT_DESIGN, SHORTS_DESIGN, SOCKS_DESIGN)}:
        bad.append("the presets do not all use shirt 206, shorts 60 and socks 14")
    print("designs (shirt, shorts, socks) of the 32 presets: %s%s" % (
        sorted({(r["home"]["outfield"][0], r["home"]["outfield"][5], r["home"]["outfield"][9]) for r in recs}),
        "  !! " + "; ".join(bad) if bad else ""))
    return 1 if bad else 0


def cmd_patches(rel, dat, shift=0):
    patches = standard_presets(rel, dat=dat, shift=shift)
    for offset, old, new in patches:
        print("0x%05x  %s -> %s" % (offset, old.hex(" "), new.hex(" ")))
    print("%d patches, %d bytes" % (len(patches), sum(len(o) for _, o, _ in patches)))
    return 0


def cmd_check(rel, dat, shift=0, path=None):
    plan = make_plan(dat)
    patched = standard_rel(rel, plan, shift=shift)
    bad = problems(patched, plan, shift)
    if path:
        sites = relocation_sites(path, shift=shift)
        if sites:
            bad.append("relocation sites inside the records: %s" % ", ".join("0x%x" % s for s in sites))
    recs, rival = presets(patched, shift)
    worst = min(min(kiteras.contrast(plan.swatches[r[n]["outfield"][12]], plan.swatches[r[n]["outfield"][1]])
                    for r in recs + [rival] for n in ("home", "away")), 99)
    print("%d records checked, worst shirt number contrast against shirt colour 1: %.2f%s" % (
        len(recs) + 1, worst, "  !! " + "; ".join(bad[:8]) if bad else ""))
    return 1 if bad else 0


def cmd_selftest(rel, dat, shift=0, path=None):
    plan = make_plan(dat)
    patches = standard_presets(rel, plan, shift=shift)
    patched = apply_patches(rel, patches)
    bad = []
    old, new = presets(rel, shift), presets(patched, shift)
    for before, after in zip(old[0] + [old[1]], new[0] + [new[1]]):
        for key in ("flag", "sponsor", "supplier", "tail"):
            if before[key] != after[key]:
                bad.append("record 0x%x: %s changed" % (before["offset"], key))
        for name, _, _ in SIDES:
            if before[name]["keeper"] != after[name]["keeper"]:
                bad.append("record 0x%x %s: keeper kit changed" % (before["offset"], name))
            if before[name]["outfield"][:12] != after[name]["outfield"][:12]:
                bad.append("record 0x%x %s: kit design or colours changed" % (before["offset"], name))
            if before[name]["side"][2] != after[name]["side"][2]:
                bad.append("record 0x%x %s: number design changed" % (before["offset"], name))
            side, tail = standard_side(plan, before[name]["side"], before[name]["outfield"])
            if after[name]["side"] != tuple(side) or after[name]["outfield"][12:15] != tuple(tail):
                bad.append("record 0x%x %s: not the standard after patching" % (before["offset"], name))
    # nothing outside the patches differs, the patches stay in the records, and a second run finds nothing
    mask = bytearray(len(rel))
    for offset, o, n in patches:
        if offset < PRESET_OFFSET + shift or offset + len(o) > CLUBPRESETS_END + shift:
            bad.append("patch at 0x%x leaves the records" % offset)
        mask[offset:offset + len(o)] = b"\x01" * len(o)
    if any(a != b and not m for a, b, m in zip(rel, patched, mask)):
        bad.append("bytes outside the patches changed")
    if len(patched) != len(rel):
        bad.append("the length changed")
    if standard_presets(patched, plan, shift=shift):
        bad.append("a second run still has patches")
    try:
        apply_patches(patched, patches[:1])
        bad.append("a patch applied over the wrong old bytes")
    except ValueError:
        pass
    bad += problems(patched, plan, shift)
    if path:
        sites = relocation_sites(path, shift=shift)
        if sites:
            bad.append("relocation sites inside the records: %s" % sites)
    print("selftest: %d patches (%d bytes), %d records re-decoded%s" % (
        len(patches), sum(len(o) for _, o, _ in patches), RECORDS, "  !! " + "; ".join(bad[:8]) if bad else ""))
    return 1 if bad else 0


def main(argv):
    if len(argv) >= 3 and argv[1] in ("info", "patches", "check", "selftest"):
        with open(argv[2], "rb") as f:
            rel = f.read()
        dat = argv[3] if len(argv) > 3 else "DAT"
        shift = shift_of(argv[2])
        if argv[1] == "info":
            return cmd_info(rel, shift)
        if argv[1] == "patches":
            return cmd_patches(rel, dat, shift)
        return {"check": cmd_check, "selftest": cmd_selftest}[argv[1]](rel, dat, shift, argv[2])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
