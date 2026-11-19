# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Club eras: the data behind `patch_disc.py --mod club-eras` (LMASTER full and
max), for Let's Make a Soccer Team! (PS2). Nexxus's idea and choices,
2026-11-19 (DOC/LMASTER_MOD.md, "Planned").

Every computer club changes manager every 3 seasons, a third of the clubs
each year, and the better clubs get the better managers. The manager brings
his own tactics and formations (his record holds three formations and the
seven tactical leanings; DOC/PBDATA_FORMAT.md), so those change with him.

The game reads a club's manager through plOteam_GetManagerNoOffset (SLES
0x216668), from PLRESOURCESIM.PAC entry 3, record +4 (initteam.py). The
switch replaces the call to plOteam_GetDb there with code that, for the clubs
of teams 3 to 441, finds the manager from this plan.

  tiers   the 439 clubs sorted by their starting world rank (the club record's
          +2, best first) and cut into 16 tiers of 27 or 28; a club's place
          in its tier is p (0 to K - 1)
  pool    the managers sorted by quality (rank, then the mean of the 48
          abilities, best first), less every manager the game gives to
          another use: the clubs' own retail managers, the national teams',
          your club's staff, the candidate lists and the rival's. Tier t
          gets the next M = 3 K entries
  era     (season + team mod 3) div 3, the season being pwkGen_Keika
          (SLES 0x244430): 0 in the first seasons, then 1, 2, ... Era 0 keeps
          the retail manager (and the retail managers are left out of the
          pool), so nothing collides while some clubs are in era 0 and others
          in era 1
  manager pool[start + (p + era * step) mod M], with step between K and
          M - K and coprime to M

Two clubs of one tier are in eras that differ by at most 1, so they collide
only if p1 - p2 = +-step mod M, which no step in [K, M - K] allows; different
tiers have disjoint slices. So every club has a manager of its own in every
season (`check` proves it over 100 seasons).

The cave tables (all little-endian u16):

  clubs   439 words, team 3 first: tier << 10 | p
  tiers   16 rows of 4: start, M, step, K
  pool    sum of M words: manager indexes (database id - 0x6d2e)

Usage:
    python cluberas.py info     <DAT>      # the tiers, the pool, the managers by tier
    python cluberas.py check    <DAT>      # one manager per club in 100 seasons; !! on any problem
    python cluberas.py selftest <DAT>      # run the switch's machine code against the plan
"""
import math
import os
import statistics
import struct
import sys

import initteam
import pbdata
import tbb
import teaminit

TEAM_FIRST, TEAM_LAST = 3, 441
CLUBS = TEAM_LAST - TEAM_FIRST + 1          # 439
TIERS = 16
ERA = 3                                      # seasons a manager stays
GROUPS = 3                                   # a third of the clubs change each year
POOL_FACTOR = 3                              # M = 3 K
SEASONS_CHECKED = 100
SIM_FILE = os.path.join("PARAM", "PLRESOURCESIM.PAC")
PB_FILE = os.path.join("PARAM", "PBDATA_EU.PAC")
NATION_ROW = 0x12


class Plan:
    """tiers [(start, M, step, K)], club {team: (tier, p)}, pool [manager index],
    retail {team: manager index}, quality {manager index: score}."""

    def __init__(self):
        self.tiers, self.club, self.pool = [], {}, []
        self.retail, self.quality, self.excluded = {}, {}, set()


def load_inputs(dat):
    """(world rank by team, retail manager by team, excluded manager indexes,
    managers as [(score, index)])."""
    db = initteam.TeamDb(os.path.join(dat, SIM_FILE))
    clubs = {t: r for t, r in db.records.items() if TEAM_FIRST <= t <= TEAM_LAST}
    if len(clubs) != CLUBS:
        raise ValueError("%d club records for teams %d-%d, expected %d"
                         % (len(clubs), TEAM_FIRST, TEAM_LAST, CLUBS))
    world = {t: r["world_rank"] for t, r in clubs.items()}
    retail = {t: r["manager"] for t, r in db.records.items()}
    buf, off, size = initteam.read_pac_entry(os.path.join(dat, SIM_FILE), 4)
    _, tables = tbb.parse(buf[off:off + size])
    nation = tables[0].data
    excluded = set(retail.values())
    excluded |= {struct.unpack_from("<h", nation, i * NATION_ROW)[0]
                 for i in range(len(nation) // NATION_ROW)}
    _, _, _, init = teaminit.load(os.path.join(dat, "PARAM"))
    for ti in (1, 4, 6):                     # staff, coach list, the rival's manager
        t = init[ti]
        excluded |= {t.field(r, "manager") for r in t.records}
    pb = pbdata.PbData(os.path.join(dat, PB_FILE))
    managers = []
    for m in pb.records("managers"):
        score = m.fields["rank"] * 1000.0 + statistics.mean(m.fields["ability"])
        managers.append((score, m.index))
    return world, retail, excluded, managers


def _step(K, M):
    """The step in [K, M - K] coprime to M nearest M / 2 (the lower on a tie)."""
    best = None
    for s in range(K, M - K + 1):
        if math.gcd(s, M) == 1:
            d = abs(2 * s - M)
            if best is None or d < best[0]:
                best = (d, s)
    if best is None:
        raise ValueError("no step for K=%d, M=%d" % (K, M))
    return best[1]


def build(dat):
    world, retail, excluded, managers = load_inputs(dat)
    plan = Plan()
    plan.retail, plan.excluded = retail, excluded
    plan.quality = {i: s for s, i in managers}
    order = sorted(world, key=lambda t: (-world[t], t))       # best club first
    base, extra = divmod(CLUBS, TIERS)
    sizes = [base + (1 if i < extra else 0) for i in range(TIERS)]
    avail = [i for s, i in sorted(managers, key=lambda x: (-x[0], x[1])) if i not in excluded]
    need = sum(POOL_FACTOR * k for k in sizes)
    if len(avail) < need:
        raise ValueError("%d managers are free, %d are needed" % (len(avail), need))
    pos = 0
    start = 0
    for t, K in enumerate(sizes):
        M = POOL_FACTOR * K
        plan.tiers.append((start, M, _step(K, M), K))
        plan.pool += avail[start:start + M]
        for p in range(K):
            plan.club[order[pos + p]] = (t, p)
        pos += K
        start += M
    return plan


def era_of(team, season):
    return (max(season, 0) + team % GROUPS) // ERA


def manager(plan, team, season):
    """The manager index the switch gives `team` in `season` (0 = the first
    season, pwkGen_Keika), or the retail one."""
    e = era_of(team, season)
    if not TEAM_FIRST <= team <= TEAM_LAST or e == 0:
        return plan.retail[team]
    tier, p = plan.club[team]
    start, M, step, K = plan.tiers[tier]
    return plan.pool[start + (p + e * step) % M]


def club_bytes(plan):
    return b"".join(struct.pack("<H", plan.club[t][0] << 10 | plan.club[t][1])
                    for t in range(TEAM_FIRST, TEAM_LAST + 1))


def tier_bytes(plan):
    rows = plan.tiers + [(0, 1, 0, 0)] * (TIERS - len(plan.tiers))
    return b"".join(struct.pack("<4H", *r) for r in rows)


def pool_bytes(plan):
    return b"".join(struct.pack("<H", i) for i in plan.pool)


def problems(plan, seasons=SEASONS_CHECKED):
    out = []
    if len(plan.pool) != len(set(plan.pool)):
        out.append("a manager is in the pool twice")
    if set(plan.pool) & plan.excluded:
        out.append("the pool holds %d managers the game uses elsewhere" % len(set(plan.pool) & plan.excluded))
    for t, (start, M, step, K) in enumerate(plan.tiers):
        if not K <= step <= M - K or math.gcd(step, M) != 1:
            out.append("tier %d: step %d is not coprime to %d inside [%d, %d]" % (t, step, M, K, M - K))
    for s in range(seasons):
        seen = {}
        for t in range(TEAM_FIRST, TEAM_LAST + 1):
            m = manager(plan, t, s)
            if m in seen:
                out.append("season %d: teams %d and %d both have manager %d" % (s, seen[m], t, m))
                break
            seen[m] = t
        if len(out) > 5:
            break
    # the managers of tier 0 must be better than tier 15's
    mean = [statistics.mean(plan.quality[i] for i in plan.pool[a:a + M]) for a, M, _, _ in plan.tiers]
    if mean != sorted(mean, reverse=True):
        out.append("the tiers' managers do not get worse down the list")
    return out


def cmd_info(dat):
    plan = build(dat)
    print("%d clubs, %d tiers, a pool of %d managers (%d free, %d used elsewhere)" % (
        len(plan.club), len(plan.tiers), len(plan.pool),
        len(plan.quality) - len(plan.excluded & set(plan.quality)), len(plan.excluded)))
    print("tier  start    M  step   K   mean manager score   best club (team)")
    best = {}
    for t, (tier, p) in plan.club.items():
        if p == 0:
            best[tier] = t
    for i, (start, M, step, K) in enumerate(plan.tiers):
        sc = statistics.mean(plan.quality[m] for m in plan.pool[start:start + M])
        print("%4d %6d %4d %5d %3d   %17.1f   team %d" % (i, start, M, step, K, sc, best[i]))
    return 0


def cmd_check(dat):
    plan = build(dat)
    bad = problems(plan)
    print("%d clubs checked over %d seasons%s" % (len(plan.club), SEASONS_CHECKED,
                                                   "  !! " + "; ".join(bad) if bad else ""))
    return 1 if bad else 0


def cmd_selftest(dat):
    """Run the machine code of the switch (patch_disc.era_words) against manager()."""
    import patch_disc as pd
    plan = build(dat)
    words = pd.era_words()
    mem = {}
    for base, blob in ((pd.ERA_CLUBS, club_bytes(plan)), (pd.ERA_TIERS, tier_bytes(plan)),
                       (pd.ERA_POOL, pool_bytes(plan))):
        for i, b in enumerate(blob):
            mem[base + i] = b
    bad = fallbacks = runs = 0
    for team in range(0, 460):
        for season in (-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 33, 47, 99):
            runs += 1
            # the plan's manager, or "retail" when the code leaves the game's own lookup
            want = ("retail" if not TEAM_FIRST <= team <= TEAM_LAST or era_of(team, season) == 0
                    else manager(plan, team, season))
            got = _run(pd, words, mem, team, season)
            fallbacks += got == "retail"
            if got != want:
                bad += 1
                if bad <= 5:
                    print("team %d season %d: the code gives %r, the plan %r" % (team, season, got, want))
    print("selftest: %d runs, %d left to the game's own lookup%s" % (
        runs, fallbacks, "  !! %d wrong" % bad if bad else ""))
    return 1 if bad else 0


def _run(pd, words, mem, team, season):
    """Emulate the routine at ERA_CAVE for `team`/`season`. Returns the manager
    index it hands back, or "retail" when it jumps to plOteam_GetDb."""
    M32 = 0xFFFFFFFF
    reg = [0] * 32
    reg[pd.A0], reg[pd.SP], reg[pd.RA] = team, 0x1F00000, 0x2166D8
    hi = lo = 0
    stack = {}
    base = pd.ERA_CAVE
    pc = base
    delay = None
    steps = 0

    def s32(x):
        x &= M32
        return x - (1 << 32) if x & 0x80000000 else x

    def rd8(a, n):
        return sum(mem.get(a + i, 0) << (8 * i) for i in range(n))

    while True:
        steps += 1
        if steps > 400:
            raise RuntimeError("runaway")
        w = words[(pc - base) // 4] if base <= pc < base + 4 * len(words) else None
        if w is None:
            raise RuntimeError("pc %#x outside the routine" % pc)
        op, rs, rt, rdn, sa, fn = w >> 26, w >> 21 & 31, w >> 16 & 31, w >> 11 & 31, w >> 6 & 31, w & 63
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        nxt = pc + 4
        jump = None
        if op == 0:
            if fn == 0x21:
                reg[rdn] = (reg[rs] + reg[rt]) & M32
            elif fn == 0 and w != 0:
                reg[rdn] = (reg[rt] << sa) & M32
            elif fn == 2:
                reg[rdn] = (reg[rt] & M32) >> sa
            elif fn == 0x1B:
                a, b = reg[rs] & M32, reg[rt] & M32
                lo, hi = a // b, a % b
            elif fn == 0x10:
                reg[rdn] = hi
            elif fn == 0x12:
                reg[rdn] = lo
            elif fn == 0x18 and rdn:
                reg[rdn] = (s32(reg[rs]) * s32(reg[rt])) & M32
            elif fn == 0x08:
                jump = reg[rs]
            elif w == 0:
                pass
            else:
                raise RuntimeError("unhandled R-type %#x" % w)
        elif op == 0x09:
            reg[rt] = (reg[rs] + simm) & M32
        elif op == 0x0B:
            reg[rt] = 1 if (reg[rs] & M32) < (simm & M32) else 0
        elif op == 0x0A:
            reg[rt] = 1 if s32(reg[rs]) < simm else 0
        elif op == 0x0C:
            reg[rt] = reg[rs] & imm
        elif op == 0x0D:
            reg[rt] = reg[rs] | imm
        elif op == 0x0F:
            reg[rt] = imm << 16
        elif op == 0x25:
            reg[rt] = rd8((reg[rs] + simm) & M32, 2)
        elif op == 0x23:
            reg[rt] = rd8((reg[rs] + simm) & M32, 4)
        elif op == 0x2B:
            for i in range(4):
                mem[(reg[rs] + simm + i) & M32] = reg[rt] >> (8 * i) & 255
        elif op == 0x3F:
            a = (reg[rs] + simm) & M32
            for i in range(8):
                stack[a + i] = (reg[rt] >> (8 * i)) & 255
        elif op == 0x37:
            a = (reg[rs] + simm) & M32
            reg[rt] = sum(stack.get(a + i, 0) << (8 * i) for i in range(8))
        elif op == 0x04:
            if reg[rs] == reg[rt]:
                jump = ("branch", nxt + 4 * simm)
        elif op == 0x05:
            if reg[rs] != reg[rt]:
                jump = ("branch", nxt + 4 * simm)
        elif op == 0x03:                                     # jal
            target = (w & 0x3FFFFFF) << 2
            jump = ("call", target)
        elif op == 0x02:                                     # j
            jump = ("jump", (w & 0x3FFFFFF) << 2)
        else:
            raise RuntimeError("unhandled opcode %#x at %#x" % (w, pc))
        reg[0] = 0
        if isinstance(jump, int):
            jump = ("jr", jump)
        if jump is None:
            pc = nxt
            continue
        # run the delay slot, then take the jump
        dw = words[(nxt - base) // 4]
        if dw != 0:
            # only nops and the simple ones the routine puts in delay slots
            op2 = dw >> 26
            if op2 == 0 and dw & 63 == 0:
                pass
            else:
                raise RuntimeError("delay slot %#x not handled" % dw)
        kind, target = jump
        if kind == "call":
            if target != pd.KEIKA:
                raise RuntimeError("call to %#x" % target)
            reg[pd.V0] = season & M32
            reg[pd.RA] = nxt + 4
            pc = nxt + 4
            continue
        if kind == "jump":
            if target == pd.ERA_GETDB:
                return "retail"
            raise RuntimeError("jump to %#x" % target)
        if kind == "jr":
            if target != 0x2166D8:
                raise RuntimeError("returned to %#x" % target)
            ptr = reg[pd.V0]
            return rd8((ptr + 4) & M32, 2)
        pc = target


def main(argv):
    if len(argv) != 3 or argv[1] not in ("info", "check", "selftest"):
        print(__doc__)
        return 1
    return {"info": cmd_info, "check": cmd_check, "selftest": cmd_selftest}[argv[1]](argv[2])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
