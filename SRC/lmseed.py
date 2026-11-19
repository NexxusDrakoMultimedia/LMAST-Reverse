# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The LMASTER seed: every random choice in LMASTER full and max comes from
one 32-bit seed, 0x31031996 (Nexxus's choice, 2026-11-19), so a build is the
same every time, on any machine and any Python. LMASTER lite has no random
choices and does not use it.

Python's random module is not used: its shuffle and sample may change between
versions. This is a small generator of our own (mulberry32) that never
changes, and `stream(*parts)` gives each use its own sequence from the seed
and a name, so adding a use never moves another's numbers.

What uses it:

  sponsor-boards  stadium.sponsor_boards: each ground's advert boards
  random-sponsors patch_disc.sponsor_hash: the three multipliers of the
                  sponsor and supplier hash the game's code runs
  club-eras       cluberas.build: the order of the clubs inside each tier

Usage:
    python lmseed.py selftest      # known answers of the generator and the properties
                                   # random-sponsors relies on; !! on any difference
    python lmseed.py show          # the first numbers of each stream
"""
import sys
import zlib

SEED = 0x31031996
M32 = 0xFFFFFFFF


def mix(a, b):
    """Two 32-bit numbers into one (the murmur3 finalizer of their xor, with b spread)."""
    h = (a ^ (b * 0x9E3779B1 & M32)) & M32
    h ^= h >> 16
    h = h * 0x85EBCA6B & M32
    h ^= h >> 13
    h = h * 0xC2B2AE35 & M32
    return h ^ (h >> 16)


class Rng:
    """mulberry32: next32() is a number 0 to 2**32 - 1."""

    def __init__(self, seed):
        self.state = seed & M32

    def next32(self):
        self.state = (self.state + 0x6D2B79F5) & M32
        t = self.state
        t = ((t ^ (t >> 15)) * (t | 1)) & M32
        t ^= (t + (((t ^ (t >> 7)) * (t | 61)) & M32)) & M32
        return (t ^ (t >> 14)) & M32

    def below(self, n):
        """0 to n - 1, without bias."""
        if n <= 0:
            raise ValueError("below(%d)" % n)
        limit = (1 << 32) - (1 << 32) % n
        while True:
            r = self.next32()
            if r < limit:
                return r % n

    def shuffle(self, items):
        """In place, Fisher-Yates from the end."""
        for i in range(len(items) - 1, 0, -1):
            j = self.below(i + 1)
            items[i], items[j] = items[j], items[i]

    def sample(self, population, k):
        """k different items, in a random order."""
        pool = list(population)
        if not 0 <= k <= len(pool):
            raise ValueError("sample of %d from %d" % (k, len(pool)))
        for i in range(k):
            j = i + self.below(len(pool) - i)
            pool[i], pool[j] = pool[j], pool[i]
        return pool[:k]

    def choice(self, seq):
        return seq[self.below(len(seq))]


def stream(*parts):
    """The generator for one use: the seed mixed with each part, a string (by its
    CRC-32) or an int."""
    h = SEED
    for p in parts:
        h = mix(h, zlib.crc32(p.encode()) if isinstance(p, str) else p & M32)
    return Rng(h)


def cmd_show():
    for name in (("sponsor-boards", 0), ("random-sponsors",), ("club-eras", 0)):
        r = stream(*name)
        print("%-24s %s" % (" ".join(map(str, name)), " ".join("%08x" % r.next32() for _ in range(4))))
    return 0


def cmd_selftest():
    bad = []
    r = Rng(SEED)
    known = [r.next32() for _ in range(3)]
    # the first numbers of Rng(SEED), frozen on 2026-11-19: a change here changes every build
    if known != [0x50D334D5, 0x27F298DE, 0xE066AFB3]:
        bad.append("Rng(%#x) gives %s" % (SEED, " ".join("%08x" % k for k in known)))
    seen = {stream("x", i).next32() for i in range(1000)}
    if len(seen) < 995:
        bad.append("streams collide: %d of 1000 different" % len(seen))
    r = stream("t")
    counts = [0] * 7
    for _ in range(7000):
        counts[r.below(7)] += 1
    if min(counts) < 800 or max(counts) > 1200:
        bad.append("below(7) is lopsided: %s" % counts)
    s = stream("s").sample(range(50), 10)
    if len(set(s)) != 10:
        bad.append("sample repeats")
    # random-sponsors: every sponsor and supplier comes up and no club keeps both
    import patch_disc
    sponsors, suppliers, kept = set(), set(), 0
    for team in range(3, 460):
        prev = None
        for season in range(20):
            pair = patch_disc.sponsor_hash(team, season)
            sponsors.add(pair[0])
            suppliers.add(pair[1])
            kept += pair == prev
            prev = pair
    if len(sponsors) != patch_disc.SPONSOR_KINDS or len(suppliers) != patch_disc.SUPPLIER_KINDS or kept:
        bad.append("random-sponsors: %d sponsors, %d suppliers, %d clubs keep both" % (
            len(sponsors), len(suppliers), kept))
    print("lmseed: seed %#x, the generator, the streams and random-sponsors checked%s" % (
        SEED, "  !! " + "; ".join(bad) if bad else ""))
    return 1 if bad else 0


def main(argv):
    if len(argv) != 2 or argv[1] not in ("selftest", "show"):
        print(__doc__)
        return 1
    return {"selftest": cmd_selftest, "show": cmd_show}[argv[1]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
