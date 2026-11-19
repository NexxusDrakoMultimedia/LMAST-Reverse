# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The main sponsors of LMASTER's club-eras: the better a club, the bigger its sponsors
(Nexxus's idea, 2026-11-19). random-sponsors gives every computer club a main sponsor 1-199
by a per-season hash; this plan keeps the hash but draws it from a slice of the sponsors
that fits the club's strength.

What the game says about a sponsor (DOC/ECONOMY.md#sponsors, DOC/LMASTER_MOD.md#club-eras):

  fee      SIMPRG.REL 0x23d978 + n * 0x48, the record of sponsor n (plSponsor_GetDb,
           0x160dc0), +0x14: the main-sponsor fee in hundredths of the stored money (£1 = 6, so
           £ = value x 100 / 6; 30,000 for the smallest of ids 1-199 to 2,700,000 for the
           biggest: £500,000 to £45 million). Records 211 and
           212 (suppliers) have none. A bigger fee is a better sponsor: the Sponsor screen
           offers it as the main sponsor's yearly pay.
  name     MES.PAC category 10000, message n, the same number (170 is Africmap Airways: its
           record holds 81,000, the £1,350,000 the first Sponsor screen of a career shows).
  logo     the kit's sponsor number (PlUnif +4) is that number; the texture is
           CmnTex_005_NNN in SPONSOR_TEXTURE.PAC, entry n - 1.

The plan: the 199 sponsors sorted by fee, best first (ties by number); the clubs' 16 tiers
of cluberas.py (kiteras.club_tiers: tier 0 the best clubs by world rank, equal sizes) get one
slice each of that list, 13 sponsors for tiers 0-6 and 12 for tiers 7-15 (199 = 7 x 13 + 9 x
12), tier 0 the biggest. A club's sponsor in a season is

    x = team * A + season * B (mod 2^32)         the hash random-sponsors uses
    sponsor = LIST[start[tier] + (x >> 11) mod length[tier]]

A and B are the two odd multipliers of patch_disc.sponsor_mults() (lmseed stream
"random-sponsors"). Teams outside 3..last keep the plain hash 1 + (x >> 11) mod 199
(expect() gives None for them).

The machine code, sponsor_tier_words(), is a leaf routine the sponsors' code calls in place
of its own hash (splice_call()); its tables, table_bytes(), are one block:

    +0                 16 bytes  tier start: the index in the list of each tier's first sponsor
    +16                16 bytes  tier length
    +32                clubs     one byte per club, teams 3..last: the club's tier
    +32 + padded clubs 199 bytes the sponsor numbers by fee, best first, then a zero byte

(the clubs' bytes padded to a multiple of 4: 440 for teams 3-441, 460 for 3-459).

Usage:
    python sponsortiers.py info <DAT> [SIMPRG.REL]      # the slices and clubs per tier, !! on a problem
    python sponsortiers.py check <DAT> [SIMPRG.REL]     # the plan's own rules, both club ranges
    python sponsortiers.py selftest <DAT> [SIMPRG.REL]  # the machine code against expect()

<DAT> is DAT/ (or DAT_JP/); SIMPRG.REL is ISO/DLL/SIMPRG.REL beside it by default (ISO_JP
for DAT_JP: the sponsor table is found there through gamever.py). The fees are read from the
retail overlay; the sponsor-fees switch cuts the big ones but keeps their order, so the plan
holds for it too.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

TEAM_FIRST, TEAM_LAST, TEAM_LAST_TIER3 = 3, 441, 459
TIERS = 16                       # cluberas.TIERS
KINDS = 199                      # the main sponsors, numbers 1-199 (patch_disc.SPONSOR_KINDS)
SPONSOR_TABLE, SPONSOR_RECORD, FEE_OFFSET = 0x23D978, 0x48, 0x14      # SIMPRG.REL, plSponsor_GetDb
M32 = 0xFFFFFFFF
TIER_START, TIER_LEN, CLUB_TABLE = 0, 16, 32     # offsets in the table block
CODE_MAX_WORDS = 32


class Plan:
    """fees {number: fee}, order [numbers, best first], slices [(start, length)] by tier,
    tier {team: 0-15}, a and b the two multipliers, last the last club's team id."""

    def __init__(self, last):
        self.fees, self.order, self.slices, self.tier = {}, [], [], {}
        self.a = self.b = 0
        self.last = last


def mults():
    """(A, B): the first two odd multipliers of patch_disc.sponsor_mults()."""
    import lmseed
    rng = lmseed.stream("random-sponsors")
    return tuple(rng.next32() | 1 for _ in range(3))[:2]


def default_paths(dat, rel=None):
    """The SIMPRG.REL that goes with a DAT folder: ISO/DLL for DAT, ISO_JP/DLL for DAT_JP."""
    if rel:
        return rel
    dat = dat.rstrip("/\\")
    head, tail = os.path.split(dat)
    return os.path.join(head, tail.replace("DAT", "ISO", 1), "DLL", "SIMPRG.REL")


def read_fees(rel):
    """{number 1-199: main-sponsor fee} from SIMPRG.REL (the Japanese build's too: the table is
    found through gamever.at)."""
    import gamever
    base = gamever.at(rel, SPONSOR_TABLE)
    data = open(rel, "rb").read()
    out = {}
    for n in range(1, KINDS + 1):
        off = base + n * SPONSOR_RECORD
        if struct.unpack_from("<I", data, off)[0] != n:
            raise ValueError("%s: record at %#x holds id %d, not %d" % (
                rel, off, struct.unpack_from("<I", data, off)[0], n))
        out[n] = struct.unpack_from("<i", data, off + FEE_OFFSET)[0]
    return out


def slice_sizes(count=KINDS, tiers=TIERS):
    base, extra = divmod(count, tiers)
    return [base + (1 if t < extra else 0) for t in range(tiers)]


def build(dat, last=TEAM_LAST, rel=None, fees=None, tiers=None):
    """The plan for the clubs of teams 3..`last`. `fees` ({number: fee}) and `tiers` ({team:
    tier}) stand in for SIMPRG.REL and for kiteras.club_tiers(dat, last), for tests."""
    plan = Plan(last)
    plan.fees = fees if fees is not None else read_fees(default_paths(dat, rel))
    if tiers is None:
        import kiteras
        tiers = kiteras.club_tiers(dat, last)
    plan.tier = dict(tiers)
    plan.order = sorted(plan.fees, key=lambda n: (-plan.fees[n], n))
    pos = 0
    for size in slice_sizes():
        plan.slices.append((pos, size))
        pos += size
    plan.a, plan.b = mults()
    return plan


def expect(plan, team, season):
    """The sponsor number the routine writes for `team` in `season` (-1 for the opening
    playoffs, 0 on), or None for a team outside 3..last, which keeps the plain hash
    (patch_disc.sponsor_hash)."""
    if not TEAM_FIRST <= team <= plan.last:
        return None
    start, length = plan.slices[plan.tier[team]]
    x = (team * plan.a + season * plan.b) & M32
    return plan.order[start + (x >> 11) % length]


def plain(plan, team, season):
    """The plain hash's sponsor, 1 + (x >> 11) mod 199 (what teams outside the plan get)."""
    return 1 + (((team * plan.a + season * plan.b) & M32) >> 11) % KINDS


def problems(plan):
    """Every way the plan breaks its rules, as strings."""
    bad = []
    n = len(plan.order)
    if sorted(plan.order) != list(range(1, KINDS + 1)):
        bad.append("the list does not hold sponsors 1-%d once each" % KINDS)
        return bad
    if any(plan.fees[a] < plan.fees[b] for a, b in zip(plan.order, plan.order[1:])):
        bad.append("the list is not sorted by fee")
    if len(plan.slices) != TIERS:
        bad.append("%d slices, not %d" % (len(plan.slices), TIERS))
        return bad
    pos = 0
    for t, (start, length) in enumerate(plan.slices):
        if start != pos or length not in (KINDS // TIERS, KINDS // TIERS + 1) or length < 1:
            bad.append("tier %d: slice %d+%d breaks the equal cut" % (t, start, length))
        pos += length
    if pos != n:
        bad.append("the slices cover %d of %d sponsors" % (pos, n))
    used = set()
    for t, (start, length) in enumerate(plan.slices):
        mine = plan.order[start:start + length]
        if used & set(mine):
            bad.append("tier %d shares a sponsor with an earlier tier" % t)
        used |= set(mine)
    if used != set(range(1, KINDS + 1)):
        bad.append("sponsors %s are in no tier" % sorted(set(range(1, KINDS + 1)) - used))
    for t in range(TIERS - 1):
        lo = min(plan.fees[x] for x in plan.order[plan.slices[t][0]:sum(plan.slices[t])])
        hi = max(plan.fees[x] for x in plan.order[plan.slices[t + 1][0]:sum(plan.slices[t + 1])])
        if lo < hi:
            bad.append("strength rises from tier %d (lowest fee %d) to %d (highest %d)" % (t, lo, t + 1, hi))
    for team in range(TEAM_FIRST, plan.last + 1):
        t = plan.tier.get(team)
        if t is None or not 0 <= t < TIERS:
            bad.append("team %d has no tier" % team)
            break
    if any(plan.fees[x] <= 0 for x in plan.order):
        bad.append("a sponsor without a fee")
    return bad


# --- the tables and the machine code ----------------------------------------------------------

def padded_clubs(plan):
    return -(-(plan.last - TEAM_FIRST + 1) // 4) * 4


def list_offset(plan):
    return CLUB_TABLE + padded_clubs(plan)


def tier_bytes(plan):
    """32 bytes: the 16 tiers' start indexes, then their lengths."""
    return bytes(s for s, _ in plan.slices) + bytes(l for _, l in plan.slices)


def club_bytes(plan):
    """One byte per club, teams 3..last: its tier, padded with zeros to a multiple of 4."""
    out = bytes(plan.tier[t] for t in range(TEAM_FIRST, plan.last + 1))
    return out.ljust(padded_clubs(plan), b"\0")


def list_bytes(plan):
    """The 199 sponsor numbers by fee, best first, and a zero byte."""
    return bytes(plan.order) + b"\0"


def table_bytes(plan):
    """The whole block (the layout in the module docstring): 672 bytes for teams 3-441, 692
    for teams 3-459."""
    return tier_bytes(plan) + club_bytes(plan) + list_bytes(plan)


def sponsor_tier_words(tables, last=TEAM_LAST):
    """The leaf routine (words) that writes the main sponsor to PlUnif +4 ($s2), for the team
    id in $s1, from the table block at address `tables`. In: $t1 the hash x = team * A + season
    * B; out: PlUnif +4 written; $t1, $v1, $s0-$s3, $ra and the stack are left alone, $t0 and
    $t2-$t6 are used. A team outside 3..last gets the plain hash's sponsor. It ends in `jr $ra`:
    call it with jal where the sponsors' code hashes (splice_call). The routine is the same
    for any `tables` and `last` bar the constants in its words."""
    import patch_disc as pd
    clubs = last - TEAM_FIRST + 1
    padded = -(-clubs // 4) * 4
    lst = CLUB_TABLE + padded
    return pd._asm(0, [
        pd.addiu(pd.T0, pd.S1, -TEAM_FIRST), pd.sltiu(pd.T2, pd.T0, clubs),
        ("beqz", pd.T2, "plain"), pd.NOP,                       # not a club of teams 3..last
        pd.lui(pd.T4, tables >> 16), pd.ori(pd.T4, pd.T4, tables & 0xFFFF),
        pd.addu(pd.T3, pd.T4, pd.T0), pd.lbu(pd.T3, CLUB_TABLE, pd.T3),      # the club's tier
        pd.addu(pd.T3, pd.T3, pd.T4), pd.lbu(pd.T5, TIER_START, pd.T3), pd.lbu(pd.T6, TIER_LEN, pd.T3),
        pd.srl(pd.T2, pd.T1, 11), pd.divu(pd.T2, pd.T6), pd.mfhi(pd.T2),     # (x >> 11) mod length
        pd.addu(pd.T2, pd.T2, pd.T5), pd.addu(pd.T2, pd.T2, pd.T4),
        pd.lbu(pd.T2, lst, pd.T2),                                           # LIST[start + pick]
        ("b", "write"), pd.NOP,
        ("label", "plain"),
        pd.srl(pd.T2, pd.T1, 11), pd.addiu(pd.T0, pd.ZERO, KINDS), pd.divu(pd.T2, pd.T0),
        pd.mfhi(pd.T2), pd.addiu(pd.T2, pd.T2, 1),                           # the plain hash
        ("label", "write"),
        pd.sb(pd.T2, 4, pd.S2), pd.jr(pd.RA), pd.NOP])


def plain_block():
    """The six words of patch_disc.sponsor_cave() that sponsor_tier_words() replaces."""
    import patch_disc as pd
    return [pd.srl(pd.T2, pd.T1, 11), pd.addiu(pd.T0, pd.ZERO, pd.SPONSOR_KINDS),
            pd.divu(pd.T2, pd.T0), pd.mfhi(pd.T2), pd.addiu(pd.T2, pd.T2, 1), pd.sb(pd.T2, 4, pd.S2)]


def splice_call(cave_words, target):
    """`cave_words` (patch_disc.sponsor_cave()) with its plain hash (plain_block) replaced by a
    `jal target` and a nop: the sponsor then comes from the routine at `target`. The cave's
    own return address is saved around the call. Raises ValueError unless the block is there
    exactly once."""
    import patch_disc as pd
    block = plain_block()
    hits = [k for k in range(len(cave_words) - len(block) + 1) if cave_words[k:k + len(block)] == block]
    if len(hits) != 1:
        raise ValueError("the plain sponsor hash is in sponsor_cave() %d times, not once" % len(hits))
    k = hits[0]
    return list(cave_words[:k]) + [pd.jal(target), pd.NOP] + list(cave_words[k + len(block):])


# --- commands ----------------------------------------------------------------------------------

def _names(dat):
    try:
        import mbb
        pack = mbb.MesPack(os.path.join(dat, "MESSAGE", "MES.PAC"))
        return lambda n: pack.text(10000, 1, n).strip()
    except Exception:
        return lambda n: ""


def _ranges(dat, rel):
    for last in (TEAM_LAST, TEAM_LAST_TIER3):
        yield last, build(dat, last, rel)


def cmd_info(dat, rel=None):
    name = _names(dat)
    failed = 0
    for last, plan in _ranges(dat, rel):
        bad = problems(plan)
        failed += bool(bad)
        print("teams %d-%d: %d sponsors, table %d bytes, routine %d words%s" % (
            TEAM_FIRST, last, len(plan.order), len(table_bytes(plan)),
            len(sponsor_tier_words(0xE0000, last)), "  !! " + "; ".join(bad) if bad else ""))
        count = [0] * TIERS
        for t in plan.tier.values():
            count[t] += 1
        for t, (start, length) in enumerate(plan.slices):
            mine = plan.order[start:start + length]
            print("  tier %2d: %3d clubs, sponsors %2d+%d, fee %7d-%7d, %s ..." % (
                t, count[t], start, length, plan.fees[mine[-1]], plan.fees[mine[0]],
                ", ".join("%d %s" % (n, name(n)) for n in mine[:2])))
    return 1 if failed else 0


def cmd_check(dat, rel=None):
    failed = 0
    for last, plan in _ranges(dat, rel):
        bad = problems(plan)
        seen = {}
        for team in range(TEAM_FIRST, last + 1):
            start, length = plan.slices[plan.tier[team]]
            mine = set(plan.order[start:start + length])
            got = {expect(plan, team, s) for s in range(-1, 100)}
            if not got <= mine:
                bad.append("team %d draws a sponsor outside its tier" % team)
            seen[team] = len(got)
        print("teams %d-%d: %d clubs, 101 seasons each draw %d-%d different sponsors of their slice%s" % (
            TEAM_FIRST, last, len(seen), min(seen.values()), max(seen.values()),
            "  !! " + "; ".join(bad) if bad else ""))
        failed += bool(bad)
    return 1 if failed else 0


def cmd_selftest(dat, rel=None):
    import cluberas
    import patch_disc as pd
    bad = runs = 0
    base_tables, routine_at = pd.SPONSOR_TIERS, pd.SPONSOR_PICK
    if mults() != pd.sponsor_mults()[:2]:
        print("  !! the multipliers differ from patch_disc.sponsor_mults()")
        bad += 1
    for last, plan in _ranges(dat, rel):
        table = table_bytes(plan)
        pick = sponsor_tier_words(base_tables, last)
        if len(pick) > CODE_MAX_WORDS:
            print("  !! the routine is %d words" % len(pick))
            bad += 1
        cave = splice_call(pd.sponsor_cave(), routine_at)
        if len(cave) * 4 > pd.GATE_CAVE - pd.SPONSOR_CAVE:
            print("  !! the spliced sponsors' code is %d words, over its space" % len(cave))
            bad += 1
        for season in range(-1, 100):
            for team in range(0, 600):
                runs += 1
                mem = {base_tables + i: b for i, b in enumerate(table)}
                plunif = 0x2000000

                def keika(reg, season=season):
                    reg[pd.V0] = season & M32

                def sub(reg):
                    kind, target, regs = cluberas.emulate(
                        pick, routine_at, {i: reg[i] for i in range(32)}, mem)
                    if kind != "jr" or target != reg[pd.RA] or regs[pd.T1] != reg[pd.T1]:
                        raise RuntimeError("the routine left by %s %#x" % (kind, target))
                    reg[:] = regs
                kind, target, reg = cluberas.emulate(
                    cave, pd.SPONSOR_CAVE, {pd.S1: team, pd.S2: plunif, pd.SP: 0x1F00000, pd.RA: 0x26EC24,
                                            pd.V1: 1}, mem, {pd.KEIKA: keika, routine_at: sub})
                got = (mem.get(plunif + 4, 0), mem.get(plunif + 5, 0))
                if 3 <= team <= 542:
                    sponsor, supplier = pd.sponsor_hash(team, season)
                    want_sponsor = expect(plan, team, season)
                    want = (sponsor if want_sponsor is None else want_sponsor, supplier)
                else:
                    want = (0, 0)
                if got != want or (kind, target) != ("jr", 0x26EC24) or reg[pd.V1] != 1:
                    bad += 1
                    if bad < 6:
                        print("  !! team %d season %d wrote %s, wanted %s" % (team, season, got, want))
    print("selftest: %d runs of the sponsors' code with the routine spliced in%s" % (
        runs, "  !! %d wrong" % bad if bad else ", 0 wrong"))
    return 1 if bad else 0


def main(argv):
    if len(argv) not in (3, 4) or argv[1] not in ("info", "check", "selftest"):
        print(__doc__)
        return 1
    return {"info": cmd_info, "check": cmd_check, "selftest": cmd_selftest}[argv[1]](*argv[2:])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
