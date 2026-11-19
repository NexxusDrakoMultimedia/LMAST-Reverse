# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""The kit plan of LMASTER's club-eras: every computer club (teams 3-441) changes its kits
each time its era changes (cluberas.era_of: a third of the clubs each year), to a design of
one of the seven kit suppliers (Nexxus's idea, 2026-11-19).

What changes, for a club in era 1 or later (era 0 is the retail kit):

  supplier   one of 206-212 (PlUnif +5), the better clubs (the tier of cluberas.py) drawing
             the better suppliers: Opnatis, Binnonn, Wrandon, Untelio, Jompela, Egamucho,
             Doclla (the order of DOC/SPONSOR_NEGOTIATION.md's fees), a place either side of
             the one their tier points to
  home kit   the shirt design and the shorts design of that supplier's own lists, the
             designs the kit editor offers the player for it (SIMPRG.REL 0x21d318,
             0x21d660 and 0x21d758, DOC/UNIFORM_FORMAT.md#the-kit-editors-designs-per-supplier);
             the shirt colours 1-3 and everything else stay as the club had them
  away kit   a shirt design of the same supplier, and new colours, drawn in turn, each roll on
             its own: colour 1 mostly white, black or the home colour 2 (a swap), otherwise a
             number colour, one that does not clash (COLOR_TBL.TBB, the editor's own rule) with
             the home shirt's colour 1; colour 2 half the time the home colour 1, white or black,
             else any colour that shows on colour 1; colour 3 the freest. The shorts and socks
             take the colours; the numbers are black on a light shirt and white on a dark one
             (kit-standards' numbers replace them)

A club has VARIANTS (6) of these, used in turn, so a club keeps cycling through designs
and never repeats the one it just had. The designs and colours are drawn from the LMASTER
seed (lmseed.py, the stream "kit-eras"), so a build is the same every time.

The machine code is patch_disc.kit_words(), run by pwkTeam_GetUnif's hook at the end of the
sponsors' code; it reads this module's table, 6 bytes per club and variant:

    byte 0  home shirt design
    byte 1  away shirt design
    byte 2  away shirt colour 1 (bits 0-6), 1 in bit 7 for black numbers, 0 for white
    byte 3  supplier index 0-6 in bits 5-7 (206 + n), shorts design - 36 in bits 0-4
    byte 4  away shirt colour 2
    byte 5  away shirt colour 3

With the third tier's eras (third-tier, club-eras and club-kits on) the plan takes teams 3-459 (the
third tier's clubs, 442-459, too); every command here then runs it for both ranges. With the kit
standard (a part of club-kits) the plan also holds each club's kit standard (below, "kit-standards"): 8 bytes for each of 7 entries a club (the retail
kit, then each variant), the standards' table of patch_disc.std_words().

Usage:
    python kiteras.py info <DAT> [SIMPRG.REL]      # the plan, club by club counts, !! on a problem
    python kiteras.py check <DAT> [SIMPRG.REL]     # the plan's own rules over every club and variant
    python kiteras.py selftest <DAT> [SIMPRG.REL]  # the machine code against the plan
    python kiteras.py show <DAT> <team> [SIMPRG.REL]  # one club's variants

<DAT> holds PLAYER/UNIFORM_LIST.TBB, PLAYER/COLOR_TBL.TBB, PLAYER/EDIT_UNIFORM_CLUT.HED/.PAC
and PARAM/PLRESOURCESIM.PAC; SIMPRG.REL is ISO/DLL/SIMPRG.REL by default. The kits are the
ones the sponsors part of club-kits leaves (its kits.csv applied).
"""
import os
import struct
import sys

import cluberas
import initteam
import lmseed
import uniform

TEAM_FIRST, TEAM_LAST = 3, 441
CLUBS = TEAM_LAST - TEAM_FIRST + 1
TEAM_LAST_TIER3 = cluberas.TEAM_LAST_TIER3        # with --mod tier3-eras: the third tier's clubs too
CLUBS_TIER3 = TEAM_LAST_TIER3 - TEAM_FIRST + 1
VARIANTS = 6
ROW = 4                                   # bytes per club and variant
SUPPLIER_FIRST, SUPPLIERS = 206, 7
# Suppliers by quality, best first, as indexes from 206: Opnatis 207, Binnonn 206, Wrandon 208,
# Untelio 209, Jompela 210, Egamucho 211, Doclla 212 (the order of their fees).
SUPPLIER_RANK = (1, 0, 2, 3, 4, 5, 6)
SHIRT_MASKS, SHORTS_MASKS, SUPPLIER_MASKS = 0x21D318, 0x21D660, 0x21D758   # SIMPRG.REL
SHIRTS, SHORTS = 209, 61
SHORTS_FIRST = 36                          # the lowest shorts design of any supplier's list
# Shirts whose front shows only colour 1 (DOC/UNIFORM_FORMAT.md#shirt-designs-and-the-three-
# shirt-colours): a new design would not show against the old, so they are left out.
PLAIN = frozenset({12, 13, 15, 76, 77, 78, 79, 80})
LIGHT_LUMA = 150                           # a shirt colour lighter than this gets black numbers
# The away shirt's colours, each rolled on its own (Nexxus, 2026-11-19): the chance, in percent, of a draw from the
# club's own colours, white and black. Blocked colours leave the lists shorter, so the rolls are set above the
# shares that come out, the ones Nexxus asked for: 75 percent for colour 1 (home colour 2, white, black), 50 for
# colour 2 (home colour 1, white, black) and 25 for colour 3 (home colours, white, black), the freest.
# Colour 1 is drawn first, then 2 and 3.
AWAY1_MAJORITY, AWAY2_MAJORITY, AWAY3_MAJORITY = 93, 51, 24
KIT_ROW = 6                                # bytes a club and variant in the kit table
# Inside the pools (Nexxus's choice with the weights suggested from how real away kits look, there being no
# third kit: the neutrals clash with the fewest opponents): colour 1 white 40, black 30, the home colour 2 30;
# colour 2 the home colour 1 45, white 30, black 25; colour 3 even. An away colour 1 also has to contrast with
# the home colour 1 at least MIN_AWAY_CONTRAST to 1 (so no black away for a dark navy home).
AWAY1_WEIGHTS, AWAY2_WEIGHTS = (40, 30, 30), (45, 30, 25)
MIN_AWAY_CONTRAST = 2.0
SIMPRG_DEFAULT = os.path.join("ISO", "DLL", "SIMPRG.REL")


class Plan:
    """lists {supplier index: (shirts, shorts)}, club {team: [(home shirt, away shirt, away c1,
    black numbers, supplier index, shorts design)] * VARIANTS}, home {team: (c1, c2, c3)},
    tier {team: 0-15}, retail {team: (home shirt, away shirt, away c1)}."""

    def __init__(self, last=TEAM_LAST):
        self.lists, self.club, self.home = {}, {}, {}
        self.tier, self.retail, self.light = {}, {}, []
        self.last = last                     # the last club's team id: 441, or 459 with tier3-eras
        self.kits, self.std = {}, {}         # the retail rows; the standards' entries (below)
        self.swatches, self.clash = [], []
        self.fallbacks = 0                   # away colours drawn from all 96: no allowed colour was free


def supplier_lists(rel):
    """{supplier index 0-6: (shirt designs, shorts designs)} from SIMPRG.REL's bytes."""
    masks = struct.unpack_from("<7I", rel, SUPPLIER_MASKS)
    shirt = struct.unpack_from("<%dI" % SHIRTS, rel, SHIRT_MASKS)
    shorts = struct.unpack_from("<%dI" % SHORTS, rel, SHORTS_MASKS)
    return {s: ([d for d in range(SHIRTS) if shirt[d] & m], [d for d in range(SHORTS) if shorts[d] & m])
            for s, m in enumerate(masks)}


def clash_table(dat):
    rows, line, data = uniform.table(os.path.join(dat, "PLAYER", uniform.COLOR_TBL))
    if rows != 96 or line != 96:
        raise ValueError("COLOR_TBL.TBB: %d rows of %d" % (rows, line))
    return [[data[a * line + b] != 0 for b in range(96)] for a in range(96)]


def kit_rows(dat, last=TEAM_LAST):
    """{team: (home outfield kit, away outfield kit)} of teams 3 to `last`, after
    random-sponsors' kits (uniform.apply_kits)."""
    path = os.path.join(dat, "PLAYER", uniform.UNIFORM_LIST)
    blob = open(path, "rb").read()
    blob = uniform.apply_kits(blob) or blob
    off = struct.unpack_from("<I", blob, 0x10)[0]
    _, doff, size, line = struct.unpack_from("<4sIII", blob, off)
    out = {}
    for t in range(TEAM_FIRST, last + 1):
        i = t - uniform.FIRST_TEAM
        fields = uniform.unpack(blob[off + doff + i * line:off + doff + (i + 1) * line])
        team = uniform.Team(fields)
        out[t] = (team.sides["home"][1], team.sides["away"][1],
                  team.sides["home"][0], team.sides["away"][0])
    return out


def club_tiers(dat, last=TEAM_LAST):
    """{team: tier 0-15}, 0 the best clubs: the tiers of cluberas.py (world rank, equal sizes)."""
    db = initteam.TeamDb(os.path.join(dat, cluberas.SIM_FILE))
    world = {t: r["world_rank"] for t, r in db.records.items() if TEAM_FIRST <= t <= last}
    if len(world) != last - TEAM_FIRST + 1:
        raise ValueError("%d club records for teams %d-%d" % (len(world), TEAM_FIRST, last))
    order = sorted(world, key=lambda t: (-world[t], t))
    base, extra = divmod(last - TEAM_FIRST + 1, cluberas.TIERS)
    tier, pos = {}, 0
    for t in range(cluberas.TIERS):
        for club in order[pos:pos + base + (1 if t < extra else 0)]:
            tier[club] = t
        pos += base + (1 if t < extra else 0)
    return tier


def is_light(luma):
    return luma >= LIGHT_LUMA


def hue(c):
    """The hue of palette colour `c`: its letter 0-11 (A red to L pink), or -1 for the greys (digit 8)."""
    return -1 if c % 8 == 7 else c // 8


def family(plan, colours):
    """The colours a free draw of the away colours 2 and 3 may take next to `colours`: any shade of their
    hues and the greys, so the surprise is a shade the club could wear (Nexxus, 2026-11-19: a green
    stripe on Hansa Rostock's blue and white was off the club's brand; colours 2 and 3 need not be
    number colours)."""
    hues = {hue(c) for c in colours} - {-1}
    return {c for c in range(96) if hue(c) in hues or hue(c) == -1}


def _weighted(pairs, allowed):
    """{colour: weight} of the (colour, weight) pairs whose colour is in `allowed`, the weights of a
    colour that comes twice (a home colour that is white) added."""
    out = {}
    for c, w in pairs:
        if c in allowed:
            out[c] = out.get(c, 0) + w
    return out


def _draw(rng, major, minor, chance):
    """A colour from `major` ({colour: weight}) `chance` percent of the time, else from `minor` (a list,
    drawn evenly); the other when one is empty; None when both are. The stream is read the same
    whichever lists are empty."""
    first = rng.below(100) < chance
    pick = rng.next32()
    for pool in ((major, minor) if first else (minor, major)):
        if not pool:
            continue
        if isinstance(pool, dict):
            point = pick % sum(pool.values())
            for c, w in sorted(pool.items()):
                if point < w:
                    return c
                point -= w
        return pool[pick % len(pool)]
    return None


def build(dat, rel=None, last=TEAM_LAST):
    plan = Plan(last)
    if rel is None:
        with open(SIMPRG_DEFAULT, "rb") as f:
            rel = f.read()
    plan.lists = supplier_lists(rel)
    clash = clash_table(dat)
    swatches = uniform.colour_swatches(os.path.join(dat, "PLAYER"))
    plan.light = [is_light(0.299 * r + 0.587 * g + 0.114 * b) for r, g, b in swatches]
    plan.tier = club_tiers(dat, last)
    kits = kit_rows(dat, last)
    plan.swatches = swatches
    plan.clash = clash
    for team in range(TEAM_FIRST, last + 1):
        home, away, home_side, away_side = kits[team]
        plan.home[team] = (home[1], home[2], home[3])
        plan.retail[team] = (home[0], away[0], away[1])
        plan.kits[team] = (home, away, home_side, away_side)
        rng = lmseed.stream("kit-eras", team)
        t = plan.tier[team]
        base = t * SUPPLIERS // cluberas.TIERS
        rows, prev_shirt, prev_c1 = [], home[0], away[1]
        for v in range(VARIANTS):
            rank = min(SUPPLIERS - 1, max(0, base + rng.below(3) - 1))
            s = SUPPLIER_RANK[rank]
            shirts = [d for d in plan.lists[s][0] if d not in PLAIN]
            shorts = plan.lists[s][1]
            pool = [d for d in shirts if d != prev_shirt] or shirts
            h = pool[rng.below(len(pool))]
            pool = [d for d in shirts if d != h] or shirts
            a = pool[rng.below(len(pool))]
            sh = shorts[rng.below(len(shorts))]
            c1_home, c2_home = plan.home[team][0], plan.home[team][1]
            # The away shirt's colours (a lime away kit was off the club's brand, Nexxus 2026-11-19), drawn
            # in turn, each roll on its own. Colour 1 first: mostly the home colour 2 (a swap), white or
            # black, otherwise one of the number colours; never one that clashes in COLOR_TBL with the
            # home colour 1 (the editor's own rule), and not the one it had in the variant before.
            # Colour 2 next: mostly the home colour 1, white or black, otherwise any colour that does not
            # clash with colour 1. Colour 3, the freest: half the time the home colours, white or black,
            # otherwise any colour but colour 1.
            allowed = [c for c in range(96) if not clash[c][c1_home] and c != prev_c1
                       and contrast(plan.swatches[c], plan.swatches[c1_home]) >= MIN_AWAY_CONTRAST]
            major = _weighted(zip((WHITE, BLACK, c2_home), AWAY1_WEIGHTS), allowed)
            minor = [c for c in NUMBER_COLOURS if c in allowed and c not in major]
            c1 = _draw(rng, major, minor, AWAY1_MAJORITY)
            if c1 is None:                               # none free (a kit between everything): a number colour
                plan.fallbacks += 1                      # that does not clash, else any
                c1 = ([c for c in NUMBER_COLOURS if not clash[c][c1_home]] or
                      [c for c in range(96) if not clash[c][c1_home]])[0]
            allowed = [c for c in range(96) if c != c1 and not clash[c][c1]]
            kin = family(plan, (c1_home, c2_home, c1))
            major = _weighted(zip((c1_home, WHITE, BLACK), AWAY2_WEIGHTS), allowed)
            c2 = _draw(rng, major, [c for c in allowed if c not in major and c in kin], AWAY2_MAJORITY)
            allowed = [c for c in range(96) if c != c1]
            major = {c: 1 for c in dict.fromkeys((c1_home, c2_home, WHITE, BLACK)) if c in allowed}
            kin = family(plan, (c1_home, c2_home, c1, c2))
            c3 = _draw(rng, major, [c for c in allowed if c not in major and c in kin], AWAY3_MAJORITY)
            rows.append((h, a, c1, c2, c3, not plan.light[c1], s, sh))
            prev_shirt, prev_c1 = h, c1
        if rows[-1][0] == rows[0][0]:                                  # the cycle's seam
            s = rows[-1][6]
            shirts = [d for d in plan.lists[s][0] if d not in PLAIN and d != rows[0][0]]
            rows[-1] = (shirts[rng.below(len(shirts))],) + rows[-1][1:]
        plan.club[team] = rows
    build_standards(plan)
    return plan


# --- kit-standards (--mod kit-standards, Nexxus's idea and choices, 2026-11-19) --------------
# Every computer club's kits follow a standard, in every era: the front number on, the shorts
# number on, an emblem on the shirt and the shorts (emblem types 1 and 2, never 3), and the
# number colours and the captain's band chosen to show on the colours they sit on. From era 1 the
# collar, the number design and the emblem pair are rolled again for each variant, each of the
# three on its own: the away kit takes the home kit's value with a raised chance (MATCH_DESIGN,
# MATCH_EMBLEM, MATCH_COLLAR) and otherwise rolls its own. The shorts emblem type and the shorts number position are one
# value in a rolled kit, as the kit editor couples them (choosing one sets the other for the
# types 1 and 2; type 3 and the third position break the pair). Era 0 keeps the retail collar,
# number design and emblems, and only has the bad values replaced.
# The editor's items and the side bytes (SIMPRG.REL, DOC/UNIFORM_FORMAT.md#the-kit-editors-
# items-and-their-bytes): side 0 the shirt emblem type, 1 the shorts emblem type, 2 the number
# design (0-7), 3 the front number (1 = on), 4 the position on shorts (0, 1; 2 is off), 5 unused
# by a match; kit field 4 the collar (0-10), 12 and 13 the shirt and shorts number colours, 14 the
# captain's band (0 white, 1 black, 2 blue, 3 red, 4 yellow).
# The chances, in percent, that the away kit has the home kit's value (Nexxus's choice, 2026-11-19, from how real
# kits work: a season's home and away shirts share a supplier's template, so the number design and the crest and
# shorts-number layout nearly always match, while the collar is the part that differs most between them).
MATCH_DESIGN, MATCH_EMBLEM, MATCH_COLLAR = 90, 85, 60
COLLARS = (0, 1, 2, 3, 4, 6, 7)                    # the collars retail computer clubs use (of 0-10)
NUMBER_DESIGNS = tuple(range(8))
WHITE, BLACK = 7, 95                               # A8 and L8
NUMBER_COLOURS = (WHITE, BLACK, 3, 11, 19, 35, 67, 75, 90, 66, 2, 47)   # A4 red, B4 orange, C4 yellow, E4 green,
# I4 blue, J4 purple, then L3 pink, I3 light blue, A3 light red and F8 mid grey: the bold colours a number, and the
# supplier logo, can take. The last four are what a greedy search over the 96 colours (leaving out near-copies of
# black and white, as K7 is) found to add the most contrast: kits whose best number colour is under 3 to 1 against
# the shirt's colours 1 and 2 fell from 48.5 to 37.8 percent (all 96 colours: 36.3)
BAND_RGB = ((222, 222, 222), (24, 24, 24), (41, 41, 148), (148, 41, 41), (148, 148, 41))
STD_ENTRIES = 1 + VARIANTS                         # era 0 from the retail kit, then each variant
STD_ROW = 8                                        # bytes an entry: a side's word and two number colours, twice


def _luma(rgb):
    def lin(c):
        c /= 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def contrast(a, b):
    """The contrast ratio of two RGB colours (1 to 21)."""
    la, lb = _luma(a), _luma(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def pick_number(plan, bases):
    """The number colour with the best worst-case contrast against `bases`, the colours it can sit
    on (a pattern puts a number on the shirt's colour 2 as well as 1): of NUMBER_COLOURS, the
    bold ones, and of those one that does not clash in COLOR_TBL with any of them if there is
    one."""
    pool = [c for c in NUMBER_COLOURS if not any(plan.clash[c][b] for b in bases)] or list(NUMBER_COLOURS)
    return max(pool, key=lambda c: (min(contrast(plan.swatches[c], plan.swatches[b]) for b in bases),
                                    -NUMBER_COLOURS.index(c)))


def pick_band(plan, colours):
    """The captain's band value (0-4) with the best worst-case contrast against `colours`."""
    return max(range(5), key=lambda v: (min(contrast(BAND_RGB[v], plan.swatches[c]) for c in colours), -v))


def side_word(collar, design, shirt_emb, shorts_emb, shorts_pos, band, supplier=0):
    """One side's standard in 16 bits: collar 0-3, design 4-6, shirt emblem 7, shorts emblem 8,
    shorts position 9, band 10-12, and in the HOME word the kit supplier's index 0-6 (bits 13-15:
    the supplier the logo shows, in every era; the number colours are bytes of their own)."""
    return (collar | design << 4 | shirt_emb << 7 | shorts_emb << 8 | shorts_pos << 9 | band << 10
            | supplier << 13)


def _side(plan, word, shirt_cols, shorts_cols):
    """(word, shirt number colour, shorts number colour) for a side's colours."""
    return (word, pick_number(plan, shirt_cols), pick_number(plan, shorts_cols))


def _retail_side(plan, kit, side, supplier=0):
    """The standard of a retail kit: its collar, number design and emblems kept where they are
    valid, its numbers and band for its colours (the shirt's colour 2 only counts for a design
    that is not plain: a plain shirt shows only colour 1)."""
    collar = kit[4] if kit[4] <= 10 else 0
    shirt_emb = side[0] if side[0] in (0, 1) else 0
    shorts_emb = side[1] if side[1] in (0, 1) else 0
    shorts_pos = side[4] if side[4] in (0, 1) else shorts_emb
    shirt = (kit[1],) if kit[0] in PLAIN else (kit[1], kit[2])
    word = side_word(collar, min(side[2], 7), shirt_emb, shorts_emb, shorts_pos, pick_band(plan, (kit[1], kit[2])),
                     supplier)
    return _side(plan, word, shirt, (kit[6], kit[7]))


def build_standards(plan):
    """plan.std {team: [((word, shirt number, shorts number) home, ... away)] * STD_ENTRIES}."""
    for team in range(TEAM_FIRST, plan.last + 1):
        home, away, home_side, away_side = plan.kits[team]
        # The supplier of era 0, from the club's tier as the eras draw it (a place either side of the one
        # the tier points to), so the logo and the look agree in every era (Nexxus's idea, 2026-11-19).
        base = plan.tier[team] * SUPPLIERS // cluberas.TIERS
        s0 = SUPPLIER_RANK[min(SUPPLIERS - 1, max(0, base + lmseed.stream("kit-standards-supplier", team).below(3) - 1))]
        entries = [(_retail_side(plan, home, home_side, s0), _retail_side(plan, away, away_side))]
        rng = lmseed.stream("kit-standards", team)
        for v in range(VARIANTS):
            h, a, c1, c2, c3, black, s, sh = plan.club[team][v]
            hc, ac = COLLARS[rng.below(len(COLLARS))], COLLARS[rng.below(len(COLLARS))]
            roll_c = rng.below(100) < MATCH_COLLAR
            hn, an = rng.below(8), rng.below(8)
            roll_n = rng.below(100) < MATCH_DESIGN
            he, ae = (rng.below(2), rng.below(2)), (rng.below(2), rng.below(2))
            roll_e = rng.below(100) < MATCH_EMBLEM
            ac, an, ae = (hc if roll_c else ac), (hn if roll_n else an), (he if roll_e else ae)
            home_cols = (home[1], home[2])          # the home shirt's colours 1 and 2 (a rolled design is not plain)
            away_cols = (c1, c2)                    # the away shirt's colours 1 and 2; its shorts take them too
            home_side_ = _side(plan, side_word(hc, hn, he[0], he[1], he[1], pick_band(plan, home_cols), s),
                               home_cols, (home[6], home[7]))
            away_side_ = _side(plan, side_word(ac, an, ae[0], ae[1], ae[1], pick_band(plan, away_cols)),
                               away_cols, away_cols)
            entries.append((home_side_, away_side_))
        plan.std[team] = entries


def std_table_bytes(plan):
    """The standards table: STD_ROW bytes an entry (the home word, shirt number colour, shorts
    number colour, then the away's), STD_ENTRIES entries a club, club by club."""
    out = bytearray()
    for team in range(TEAM_FIRST, plan.last + 1):
        for home, away in plan.std[team]:
            out += struct.pack("<HBBHBB", *home, *away)
    return bytes(out)


def std_writes(side_entry, side, kit, home=False):
    """The PlUnif bytes the code writes for one side's entry: `side` the offset of its six side
    bytes (6 home, 0x2a away), `kit` of its outfield kit (0x1b home, 0x3f away)."""
    word, snum, shnum = side_entry
    collar, design = word & 15, word >> 4 & 7
    shirt_emb, shorts_emb, shorts_pos = word >> 7 & 1, word >> 8 & 1, word >> 9 & 1
    out = {side: shirt_emb, side + 1: shorts_emb, side + 2: design, side + 3: 1, side + 4: shorts_pos,
           side + 5: 1, kit + 4: collar, kit + 12: snum, kit + 13: shnum, kit + 14: word >> 10 & 7}
    if home:
        out[5] = SUPPLIER_FIRST + (word >> 13 & 7)          # the supplier byte, from the tier in every era
    return out


def std_expect(plan, team, season, offset=0):
    """What the standards code writes into a club's PlUnif in `season`: {offset: value}, empty
    for a team outside the plan's clubs."""
    if not TEAM_FIRST <= team <= plan.last:
        return {}
    e = cluberas.era_of(team, season, offset)
    home, away = plan.std[team][0 if e == 0 else 1 + (e - 1) % VARIANTS]
    out = std_writes(home, 6, 0x1B, True)
    out.update(std_writes(away, 0x2A, 0x3F))
    return out


def table_bytes(plan):
    """The kit table: KIT_ROW bytes for each club's variants, club by club: the home shirt design,
    the away shirt design, the away colour 1 (and the black numbers' flag in bit 7), the supplier
    index (bits 5-7) and the shorts design - 36, the away colours 2 and 3."""
    out = bytearray()
    for team in range(TEAM_FIRST, plan.last + 1):
        for h, a, c1, c2, c3, black, s, sh in plan.club[team]:
            out += bytes([h, a, c1 | (0x80 if black else 0), s << 5 | (sh - SHORTS_FIRST), c2, c3])
    return bytes(out)


def expect(plan, team, season, offset=0):
    """What the code writes into a club's PlUnif in `season`: {offset: value}, empty in era 0 and
    for a team outside the plan's clubs (3-441, or 3-459 with tier3-eras)."""
    if not TEAM_FIRST <= team <= plan.last:
        return {}
    e = cluberas.era_of(team, season, offset)
    if e == 0:
        return {}
    h, a, c1, c2, c3, black, s, sh = plan.club[team][(e - 1) % VARIANTS]
    num = 95 if black else 7
    return {0x1B: h, 0x20: sh, 5: SUPPLIER_FIRST + s, 0x3F: a, 0x44: sh,
            0x40: c1, 0x41: c2, 0x42: c3, 0x45: c1, 0x46: c2, 0x47: c3,
            0x49: c1, 0x4A: c2, 0x4B: num, 0x4C: num}


def problems(plan, dat=None):
    out = []
    clash = clash_table(dat) if dat else None
    for team in range(TEAM_FIRST, plan.last + 1):
        rows = plan.club[team]
        if len(rows) != VARIANTS:
            out.append("team %d: %d variants" % (team, len(rows)))
            continue
        for v, (h, a, c1, c2, c3, black, s, sh) in enumerate(rows):
            shirts, shorts = plan.lists[s]
            if h not in shirts or a not in shirts or sh not in shorts or h in PLAIN:
                out.append("team %d variant %d: a design outside supplier %d's list" % (team, v, SUPPLIER_FIRST + s))
            if not SHORTS_FIRST <= sh < SHORTS_FIRST + 32:
                out.append("team %d variant %d: shorts design %d does not fit 5 bits" % (team, v, sh))
            if clash and clash[c1][plan.home[team][0]]:
                out.append("team %d variant %d: away colour %d clashes with the home colour 1" % (team, v, c1))
            if clash and (c2 == c1 or clash[c2][c1]):
                out.append("team %d variant %d: away colour 2 (%d) does not show on colour 1 (%d)" % (team, v, c2, c1))
            if h == rows[v - 1][0]:
                out.append("team %d variant %d: the home shirt %d repeats" % (team, v, h))
        if len(out) > 8:
            break
    mean = [sum(SUPPLIER_RANK.index(r[6]) for t in plan.tier if plan.tier[t] == k for r in plan.club[t])
            / max(1, sum(1 for t in plan.tier if plan.tier[t] == k) * VARIANTS) for k in range(cluberas.TIERS)]
    if any(b < a - 0.25 for a, b in zip(mean, mean[1:])):         # neighbouring tiers share a base rank
        out.append("the tiers' suppliers do not get worse down the list: %s" % ["%.2f" % m for m in mean])
    return out


def cmd_info(dat, rel=None):
    failed = 0
    for last in (TEAM_LAST, TEAM_LAST_TIER3):
        print("teams %d-%d%s:" % (TEAM_FIRST, last, " (with tier3-eras)" if last == TEAM_LAST_TIER3 else ""))
        failed += _info(dat, rel, last)
    return 1 if failed else 0


def _info(dat, rel, last):
    plan = build(dat, rel, last)
    bad = problems(plan, dat)
    count = {s: 0 for s in range(SUPPLIERS)}
    for rows in plan.club.values():
        for r in rows:
            count[r[6]] += 1
    print("%d clubs x %d variants, table %d bytes%s" % (
        len(plan.club), VARIANTS, len(table_bytes(plan)), "  !! " + "; ".join(bad) if bad else ""))
    for s in range(SUPPLIERS):
        print("  supplier %d: %d shirts (%d without the plain ones), %d shorts, drawn %d times" % (
            SUPPLIER_FIRST + s, len(plan.lists[s][0]), len([d for d in plan.lists[s][0] if d not in PLAIN]),
            len(plan.lists[s][1]), count[s]))
    print("mean supplier rank by tier (0 = Opnatis): " + " ".join(
        "%.1f" % (sum(SUPPLIER_RANK.index(r[6]) for t in plan.tier if plan.tier[t] == k for r in plan.club[t])
                  / (sum(1 for t in plan.tier if plan.tier[t] == k) * VARIANTS)) for k in range(cluberas.TIERS)))
    return 1 if bad else 0


def cmd_check(dat, rel=None):
    failed = 0
    for last in (TEAM_LAST, TEAM_LAST_TIER3):
        plan = build(dat, rel, last)
        bad = problems(plan, dat)
        print("teams %d-%d: %d clubs checked%s" % (TEAM_FIRST, last, len(plan.club),
                                                  "  !! " + "; ".join(bad) if bad else ""))
        failed += bool(bad)
    return 1 if failed else 0


def cmd_show(dat, team, rel=None):
    team = int(team, 0)
    plan = build(dat, rel, TEAM_LAST_TIER3 if team > TEAM_LAST else TEAM_LAST)
    if team not in plan.club:
        print("team %d is outside teams %d-%d" % (team, TEAM_FIRST, plan.last))
        return 1
    if team > TEAM_LAST:
        print("team %d is a third-tier club: the eras change it only with --mod third-tier, club-eras and club-kits all on" % team)
    print("team %d: tier %d, home colours %s, retail home shirt %d, away shirt %d, away colour %s" % (
        team, plan.tier[team], tuple(uniform.colour_name(c) for c in plan.home[team]),
        plan.retail[team][0], plan.retail[team][1], uniform.colour_name(plan.retail[team][2])))

    def std(entry):
        word, snum, shnum = entry
        return "collar %d, number design %d, emblems %d/%d, shorts position %d, band %d, numbers %s/%s" % (
            word & 15, word >> 4 & 7, word >> 7 & 1, word >> 8 & 1, word >> 9 & 1, word >> 10 & 7,
            uniform.colour_name(snum), uniform.colour_name(shnum))
    home, away = plan.std[team][0]
    print("  era 0 (retail kit) standard: home %s | away %s" % (std(home), std(away)))
    for v, (h, a, c1, c2, c3, black, s, sh) in enumerate(plan.club[team]):
        print("  variant %d (era %d): supplier %d, home shirt %d, shorts %d, away shirt %d, away colours %s %s %s" % (
            v, v + 1, SUPPLIER_FIRST + s, h, sh, a, uniform.colour_name(c1), uniform.colour_name(c2),
            uniform.colour_name(c3)))
        home, away = plan.std[team][v + 1]
        print("      standard: home %s | away %s" % (std(home), std(away)))
    return 0


def cmd_selftest(dat, rel=None):
    """Run patch_disc.kit_words() for every team id 0-599, seasons -1 to 99 and the three test
    offsets against expect()."""
    import patch_disc as pd
    bad = runs = idle = 0
    chain = []
    for last in (TEAM_LAST, TEAM_LAST_TIER3):       # the plain switch, and with tier3-eras
        plan = build(dat, rel, last)
        table = table_bytes(plan)
        b, r, i = _selftest(pd, plan, table)
        bad, runs, idle = bad + b, runs + r, idle + i
        chain += chain_test(pd, plan, table)
        chain += standards_test(pd, plan, table)
        chain += standards_test(pd, plan, table, tiers=True, dat=dat)
    print("selftest: %d runs, %d left to the game%s" % (runs, idle, "  !! %d wrong" % bad if bad else ""))
    for line in chain[:5]:
        print("  !! " + line)
    print("chain: the sponsors' code into the kit code, teams 0-599%s" % (
        "  !! %d wrong" % len(chain) if chain else ", 0 wrong"))
    return 1 if bad or chain else 0


def _selftest(pd, plan, table):
    bad = runs = idle = 0
    for offset in range(10):
        words = pd.kit_words(offset, plan.last - TEAM_FIRST + 1)
        for team in range(0, 600):
            for season in (-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 33, 47, 99):
                runs += 1
                mem = {pd.KIT_TABLE + i: b for i, b in enumerate(table)}
                plunif = 0x2000000
                home = plan.home.get(team, (11, 22, 33))
                for k in range(0x50):
                    mem[plunif + k] = 0xEE
                mem[plunif + 0x1C], mem[plunif + 0x1D], mem[plunif + 0x1E] = home

                def keika(reg, season=season):
                    reg[pd.V0] = season & 0xFFFFFFFF
                kind, target, reg = cluberas.emulate(
                    words, pd.KIT_CAVE, {pd.S1: team, pd.S2: plunif, pd.SP: 0x1F00000, pd.RA: 0x26EC24,
                                         pd.V1: 1}, mem, {pd.KEIKA: keika})
                got = {k: mem[plunif + k] for k in range(0x50)
                       if mem[plunif + k] != 0xEE and k not in (0x1C, 0x1D, 0x1E)}
                want = expect(plan, team, season, offset)
                idle += not want
                if (kind, target) != ("jr", 0x26EC24) or got != want or reg[pd.V1] != 1:
                    bad += 1
                    if bad <= 5:
                        print("last %d offset %d team %d season %d: wrote %s, wanted %s (%s %#x, v1 %d)" % (
                            plan.last, offset, team, season, got, want, kind, target, reg[pd.V1]))
    return bad, runs, idle


def standards_test(pd, plan, table, tiers=False, dat="DAT"):
    """The whole chain with kit-standards on: the sponsors' code, the kit code and the
    standards' code, as the game runs them, over every team id 0-599, four seasons and the
    offsets 0 and 2: the PlUnif bytes must be the sponsor from the hash (from the club's tier
    with `tiers`: sponsortiers.py's routine called from the sponsors' code), the kit plan's bytes
    once the era is past 0, and the standard's bytes for every club, in every era."""
    bad = []
    stable = std_table_bytes(plan)
    was = pd.kit_eras, pd.kit_standards, pd.sponsor_tiers
    pd.kit_eras = pd.kit_standards = True
    pd.sponsor_tiers = tiers
    if tiers:
        import sponsortiers
        splan = sponsortiers.build(dat, plan.last)
        pick = sponsortiers.sponsor_tier_words(pd.SPONSOR_TIERS, plan.last)
        tier_table = sponsortiers.table_bytes(splan)
    try:
        sponsor_words = pd.sponsor_cave()
        count = plan.last - TEAM_FIRST + 1
        for offset in (0, 2):
            kit, std = pd.kit_words(offset, count), pd.std_words(offset, count)
            for season in (-1, 0, 3, 9):
                for team in range(0, 600):
                    mem = {pd.KIT_TABLE + i: b for i, b in enumerate(table)}
                    mem.update({pd.STD_TABLE + i: b for i, b in enumerate(stable)})
                    if tiers:
                        mem.update({pd.SPONSOR_TIERS + i: b for i, b in enumerate(tier_table)})
                    plunif = 0x2000000
                    for k in range(0x50):
                        mem[plunif + k] = 0
                    home = plan.home.get(team, (11, 22, 33))
                    mem[plunif + 0x1C], mem[plunif + 0x1D], mem[plunif + 0x1E] = home

                    def keika(reg, season=season):
                        reg[pd.V0] = season & 0xFFFFFFFF
                    regs = {pd.S1: team, pd.S2: plunif, pd.SP: 0x1F00000, pd.RA: 0x26EC24, pd.V1: 1}
                    calls = {pd.KEIKA: keika}
                    if tiers:
                        def sub(reg, mem=mem):
                            _, _, regs_ = cluberas.emulate(pick, pd.SPONSOR_PICK, {i: reg[i] for i in range(32)}, mem)
                            reg[:] = regs_
                        calls[pd.SPONSOR_PICK] = sub
                    kind, target, reg = cluberas.emulate(sponsor_words, pd.SPONSOR_CAVE, regs, mem, calls)
                    for words_, base in ((kit, pd.KIT_CAVE), (std, pd.STD_CAVE)):
                        if (kind, target) == ("jump", base):
                            kind, target, reg = cluberas.emulate(
                                words_, base, {i: v for i, v in enumerate(reg)}, mem, {pd.KEIKA: keika})
                    sponsor, supplier = pd.sponsor_hash(team, season) if 3 <= team <= 542 else (0, 0)
                    if tiers and 3 <= team <= plan.last:
                        sponsor = sponsortiers.expect(splan, team, season)
                    want = {4: sponsor, 5: supplier}
                    want.update(expect(plan, team, season, offset))
                    want.update(std_expect(plan, team, season, offset))
                    got = {k: mem[plunif + k] for k in range(0x50) if mem[plunif + k]
                           and k not in (0x1C, 0x1D, 0x1E)}
                    want = {k: v for k, v in want.items() if v}
                    if (kind, target) != ("jr", 0x26EC24) or got != want or reg[pd.V1] != 1:
                        bad.append("standards: offset %d team %d season %d: wrote %s, wanted %s (%s %#x)" % (
                            offset, team, season, {k: v for k, v in got.items() if got.get(k) != want.get(k)},
                            {k: v for k, v in want.items() if got.get(k) != want.get(k)}, kind, target))
    finally:
        pd.kit_eras, pd.kit_standards, pd.sponsor_tiers = was
    return bad


def chain_test(pd, plan, table):
    """The sponsors' code with kit-eras on, running on into the kit code as the game runs them:
    the sponsor from the sponsors' hash, the supplier and kits from the plan once the club's
    era is past 0 (the supplier the plan's, not the hash's)."""
    bad = []
    was, pd.kit_eras = pd.kit_eras, True
    try:
        sponsor_words = pd.sponsor_cave()
        for offset in (0, 2):
            kit = pd.kit_words(offset, plan.last - TEAM_FIRST + 1)
            for season in (-1, 0, 3, 9):
                for team in range(0, 600):
                    mem = {pd.KIT_TABLE + i: b for i, b in enumerate(table)}
                    plunif = 0x2000000
                    for k in range(0x50):
                        mem[plunif + k] = 0
                    home = plan.home.get(team, (11, 22, 33))
                    mem[plunif + 0x1C], mem[plunif + 0x1D], mem[plunif + 0x1E] = home

                    def keika(reg, season=season):
                        reg[pd.V0] = season & 0xFFFFFFFF
                    regs = {pd.S1: team, pd.S2: plunif, pd.SP: 0x1F00000, pd.RA: 0x26EC24, pd.V1: 1}
                    kind, target, reg = cluberas.emulate(sponsor_words, pd.SPONSOR_CAVE, regs, mem, {pd.KEIKA: keika})
                    if (kind, target) == ("jump", pd.KIT_CAVE):
                        kind, target, reg = cluberas.emulate(
                            kit, pd.KIT_CAVE, {i: v for i, v in enumerate(reg)}, mem, {pd.KEIKA: keika})
                    sponsor, supplier = pd.sponsor_hash(team, season) if 3 <= team <= 542 else (0, 0)
                    want = {4: sponsor, 5: supplier}
                    want.update(expect(plan, team, season, offset))
                    got = {k: mem[plunif + k] for k in range(0x50) if mem[plunif + k]
                           and k not in (0x1C, 0x1D, 0x1E)}
                    want = {k: v for k, v in want.items() if v}
                    if (kind, target) != ("jr", 0x26EC24) or got != want or reg[pd.V1] != 1:
                        bad.append("offset %d team %d season %d: wrote %s, wanted %s" % (
                            offset, team, season, got, want))
    finally:
        pd.kit_eras = was
    return bad


def main(argv):
    if len(argv) >= 3 and argv[1] in ("info", "check", "selftest"):
        rel = open(argv[3], "rb").read() if len(argv) > 3 else None
        return {"info": cmd_info, "check": cmd_check, "selftest": cmd_selftest}[argv[1]](argv[2], rel)
    if len(argv) >= 4 and argv[1] == "show":
        rel = open(argv[4], "rb").read() if len(argv) > 4 else None
        return cmd_show(argv[2], argv[3], rel)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
