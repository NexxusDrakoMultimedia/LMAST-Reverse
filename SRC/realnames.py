# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Real club, national team and competition names for Let's Make a Soccer
Team! (PS2): the LMASTER real-names switch's data and writer.

The game's names are message text in DAT/MESSAGE/MES.PAC (DOC/MBB_FORMAT.md,
the name lists): category 3 is every team's name (id 2000 + team), 4 a
copy (3000 + team), 100003 a long-form list (2000 + team) and 5 the
three-letter forms (4000 + team); 9 names the competitions (10000 +),
100009 the same in capitals in every language, 11 and 100011 their
stages and groups (1000 +), and 10 each club's stadium (11000 + team,
"<club> Stadium" in the game). PRELOAD/STATIONMES<lang>.PAC holds each
language's copy of categories 1 and 3-11 (patch_disc.py --copies).

realnames.csv, next to this script, holds only the real names: one row
per name to change, keyed by category (3, 10, 9 or 11) and id, with the
English, French, German, Italian and Spanish names and, for a team, its
three-letter form. An empty cell keeps the game's name. A stadium is
named as of 2006-07; a club with a real name and no stadium row gets
"<real name> Stadium" in its language. `apply` writes
them into every list above, and puts a competition's real name in place of
its game name in the other messages that mention it (the rules and
the news; names of 6 or more characters, outside {tags}). Club names in
other messages are left: many are city names too. See
DOC/LMASTER_MOD.md#real-names for how the names were chosen.

Usage:
    python realnames.py info   <DAT/MESSAGE/MES.PAC>       # check the names against the disc
    python realnames.py import <table.csv> [out.csv]      # from mbb.py names' table, filled in
    python realnames.py apply  <MES.PAC> <out.PAC>        # write the real names

`import` takes the table `mbb.py names` writes, with its "real name"
columns filled in (a name ending in "?" isn't taken), and writes
realnames.csv (or out.csv). Letters the European text's encoding (cp850)
has no code for lose their accent ("Željezničar" -> "Zeljeznicar"), as
the game's own names do ("Besiktas"). The short form is the name's first three
letters in capitals, as the game forms them (DOC/MBB_FORMAT.md), or the
one SHORT_OVERRIDES gives where two clubs would share one.
"""
import csv
import os
import re
import sys
import tempfile

import mbb

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "realnames.csv")
LANGS = (1, 2, 3, 4, 5)                 # en, fr, de, it, es
LANG_CODES = tuple(mbb.LANGS[l] for l in LANGS)
TEAM_CAT, TEAM_BASE = 3, 2000
TEAM_COPY, TEAM_COPY_BASE = 4, 3000
TEAM_LONG = 100003
SHORT_CAT, SHORT_BASE = 5, 4000
COMP_CAT, COMP_CAPS = 9, 100009
STAGE_CAT, STAGE_VARIANT = 11, 100011
STADIUM_CAT, STADIUM_BASE = 10, 11000
CLUB_END = 460                          # teams 3-459 are clubs, with stadiums; 460-542 nations
NAME_CATS = (TEAM_CAT, STADIUM_CAT, COMP_CAT, STAGE_CAT)
NAME_LIMIT = 18                         # the player's own club name (user report)
STADIUM_LIMIT = 30                      # the game's longest ("Athletic Club de Bilbao Stadio")
MENTION_MIN = 6
# Mentions are rewritten in English only. The other languages' game names
# are often plain phrases ("monter en première division"), and a proper
# name in their place needs its article and gender changed ("nel
# campionato italiano B" -> "nella Serie B"), which a swap can't do;
# `info` counts those mentions, for edits by hand.
MENTION_LANGS = (1,)
# Lists of names and places, where a competition's name isn't a mention.
LIST_CATS = {3, 4, 5, 6, 7, 8, 9, 10, 11, 960, 961, 100003, 100006, 100009, 100011,
             100960, 100961}
# Short forms where the first three letters would match another club's.
SHORT_OVERRIDES = {"Manchester City": "MCI", "Manchester United": "MUN",
                   "Sheffield Wed": "SHW", "Sheffield United": "SHU"}
TAG = re.compile(r"(\{[^}]*\})")


# Letters with no cp850 code (the European text's encoding, DOC/MBB_FORMAT.md)
# and no accent to drop: the game writes such names without them too
# ("Besiktas").
FOLD = {"ł": "l", "Ł": "L", "ı": "i", "đ": "d", "Đ": "D", "ß": "ss"}


def fold(name):
    """`name` with each letter cp850 has no code for replaced by its plain
    letter: "Željezničar" -> "Zeljeznicar", "Wisła" -> "Wisla". Letters cp850
    has ("é", "ü", "ø", "ñ") stay."""
    import unicodedata
    out = []
    for c in name:
        try:
            c.encode("cp850")
            out.append(c)
            continue
        except UnicodeEncodeError:
            pass
        if c in FOLD:
            out.append(FOLD[c])
            continue
        base = "".join(ch for ch in unicodedata.normalize("NFKD", c)
                       if not unicodedata.combining(ch))
        out.append(base)
    return "".join(out)


def short_form(name):
    """The game's three-letter form: the name's first three letters, in
    capitals, accents kept (category 5 holds this for every club)."""
    if name in SHORT_OVERRIDES:
        return SHORT_OVERRIDES[name]
    return "".join(c for c in name if c.isalpha())[:3].upper()


def load(path=FILE):
    """[(category, id, {lang: name}, short)]; short "" for a competition."""
    rows = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            names = {l: r[c] for l, c in zip(LANGS, LANG_CODES) if r[c]}
            rows.append((int(r["category"]), int(r["id"]), names, r.get("short", "")))
    return rows


def open_pack(data):
    """A mbb.MesPack of MES.PAC bytes."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "MES.PAC")
        with open(path, "wb") as g:
            g.write(data)
        return mbb.MesPack(path)


def same_case(game, name):
    """`name` in capitals where the game's text is (category 9 in French,
    Italian and Spanish)."""
    letters = [c for c in game if c.isalpha()]
    return name.upper() if letters and game == game.upper() else name


# A competition entry for a qualifying round comes just before its
# competition (9:10003 English Cup Qualifying, 10004 English Cup), so in
# the other messages ("we'll qualify for European League Round") it takes
# the competition's own real name.
QUALIFYING = re.compile(r" (Qualifying|Round)$")


def edits(pack, rows, mention_langs=MENTION_LANGS):
    """[(category, lang, id, text)] the names make: every list, and the
    competitions' mentions in other messages in `mention_langs`."""
    out = []
    mention = {l: {} for l in LANGS}        # lang -> {game name, lower case: real name}
    comps = {rid: names for cat, rid, names, _ in rows if cat == COMP_CAT}
    stadiums = {(rid, l) for cat, rid, names, _ in rows if cat == STADIUM_CAT for l in names}
    for cat, rid, names, short in rows:
        if cat == TEAM_CAT:
            team = rid - TEAM_BASE
            for l, name in names.items():
                out += [(TEAM_CAT, l, rid, name), (TEAM_COPY, l, TEAM_COPY_BASE + team, name),
                        (TEAM_LONG, l, rid, name)]
                # A stadium with no name of its own is "<club> Stadium" with
                # the club's real name (every one is the club's game name,
                # or its long form, and the language's word).
                sid = STADIUM_BASE + team
                if team < CLUB_END and (sid, l) not in stadiums:
                    stadium = pack.text(STADIUM_CAT, l, sid)
                    for game in (pack.text(TEAM_CAT, l, rid), pack.text(TEAM_LONG, l, rid)):
                        game = game.strip()
                        if stadium.startswith(game + " "):
                            out.append((STADIUM_CAT, l, sid,
                                        name + " " + stadium[len(game):].lstrip()))
                            break
            if short:
                out += [(SHORT_CAT, l, SHORT_BASE + team, short) for l in LANGS]
        elif cat == STADIUM_CAT:
            out += [(cat, l, rid, name) for l, name in names.items()]
        elif cat == COMP_CAT:
            qualifying = QUALIFYING.search(pack.text(cat, 1, rid))
            for l, name in names.items():
                game = pack.text(cat, l, rid)
                out.append((cat, l, rid, same_case(game, name)))
                said = comps.get(rid + 1, {}).get(l, name) if qualifying else name
                if len(game) >= MENTION_MIN and not said.endswith("?"):
                    mention[l][game.lower()] = said
            if 1 in names:
                out += [(COMP_CAPS, l, rid, names[1].upper()) for l in LANGS]
        elif cat == STAGE_CAT:
            english = pack.text(cat, 1, rid)
            for l, name in names.items():
                game = pack.text(cat, l, rid)
                out.append((cat, l, rid, name))
                # 100011 repeats 11, or the English name (once run together:
                # "European LeagueGroup A").
                variant = pack.text(STAGE_VARIANT, l, rid)
                if variant == game:
                    out.append((STAGE_VARIANT, l, rid, name))
                elif variant.replace(" ", "") == english.replace(" ", "") and 1 in names:
                    out.append((STAGE_VARIANT, l, rid, names[1]))
        else:
            raise ValueError("category %d isn't a name list (3, 10, 9 or 11)" % cat)
    return out + mentions(pack, mention, mention_langs)


def mentions(pack, mention, langs):
    """[(category, lang, (id, copy), text)]: the messages outside the name
    lists with a competition's game name in `mention` replaced."""
    out = []
    for l in langs:
        if not mention[l]:
            continue
        # One pass, longest name first, outside {tags}, in any case: French,
        # Italian and Spanish keep category 9 in capitals, their text doesn't.
        pat = re.compile("|".join(re.escape(g) for g in sorted(mention[l], key=len, reverse=True)),
                         re.IGNORECASE)
        for (cat, lang), (_, _, _, _, m) in sorted(pack.files.items()):
            if lang != l or cat in LIST_CATS:
                continue
            seen = {}
            for rid, _ in m.records:
                k = seen[rid] = seen.get(rid, -1) + 1
                text = pack.text(cat, l, rid, k)
                parts = TAG.split(text)
                new = "".join(p if i % 2 else pat.sub(lambda x: mention[l][x.group(0).lower()], p)
                              for i, p in enumerate(parts))
                if new != text:
                    out.append((cat, l, (rid, k), new))
    return out


def apply(data, rows=None):
    """MES.PAC bytes with the real names; (bytes, report lines). An entry
    that outgrows its slot moves the later ones (patch_disc.py handles a
    MES.PAC that grows)."""
    pack = open_pack(data)
    changed = 0
    for cat, l, rid, text in edits(pack, load() if rows is None else rows):
        rid, copy = rid if isinstance(rid, tuple) else (rid, 0)
        changed += pack.set(cat, l, rid, copy, text)
    out, report, _, errors = pack.build()
    if errors:
        raise ValueError("real-names: " + "; ".join(errors))
    return out, ["%d messages changed" % changed] + report


def cmd_info(mes_path):
    with open(mes_path, "rb") as f:
        pack = open_pack(f.read())
    rows = load()
    problems = []
    counts = {}
    long = []
    for cat, rid, names, short in rows:
        counts[cat] = counts.get(cat, 0) + 1
        for l, name in names.items():
            try:
                pack.text(cat, l, rid)
            except ValueError as e:
                problems.append(str(e))
            if name.endswith("?") or name != name.strip():
                problems.append("%d:%d %s: %r" % (cat, rid, mbb.LANGS[l], name))
            try:
                mbb.encode(name, l)
            except ValueError as e:
                problems.append("%d:%d %s: %s" % (cat, rid, mbb.LANGS[l], e))
            if cat == TEAM_CAT and len(name) > NAME_LIMIT \
                    or cat == STADIUM_CAT and len(name) > STADIUM_LIMIT:
                long.append("%s (%d)" % (name, len(name)))
        if cat == TEAM_CAT and short and len(short) != 3:
            problems.append("%d:%d short form %r isn't three letters" % (cat, rid, short))
    print("%s: %d names (%s)%s" % (FILE.replace("\\", "/").split("/")[-1], len(rows), ", ".join(
        "%d in category %d" % (n, c) for c, n in sorted(counts.items())),
        "  !! " + "; ".join(problems) if problems else ""))
    # Short forms that two clubs share once the names are in.
    shorts = {}
    for t in range(3, 460):
        shorts.setdefault(pack.text(SHORT_CAT, 1, SHORT_BASE + t), []).append(t)
    for cat, rid, names, short in rows:
        if cat == TEAM_CAT and short:
            t = rid - TEAM_BASE
            old = pack.text(SHORT_CAT, 1, SHORT_BASE + t)
            shorts[old].remove(t)
            shorts.setdefault(short, []).append(t)
    shared = {s: ts for s, ts in shorts.items() if len(ts) > 1}
    print("  short forms shared by two clubs or more: %d (%s)" % (
        len(shared), ", ".join("%s %s" % (s, "/".join(map(str, ts))) for s, ts in
                               sorted(shared.items())[:20])))
    print("  club names over %d characters, stadiums over %d: %d%s" % (
        NAME_LIMIT, STADIUM_LIMIT, len(long), " (%s)" % ", ".join(long) if long else ""))
    try:
        e = edits(pack, rows)
    except ValueError as err:
        print("  !! %s" % err)
        return
    lists = sum(1 for cat, _, _, _ in e if cat in LIST_CATS)
    left = [x for x in edits(pack, rows, LANGS) if x[0] not in LIST_CATS and x[1] not in MENTION_LANGS]
    print("  %d list messages, %d mentions in English; %d mentions in the other languages "
          "left for edits by hand (%s)" % (
              lists, len(e) - lists, len(left), ", ".join(
                  "%s %d" % (mbb.LANGS[l], sum(x[1] == l for x in left)) for l in LANGS[1:])))


def cmd_import(table, out_path):
    rows = list(csv.DictReader(open(table, encoding="utf-8-sig", newline="")))
    out = []
    for r in rows:
        if r["section"] not in ("club", "national team", "competition", "competition stage"):
            continue
        names = [r["real name (fill in)"]] + [r.get("real " + c, "") for c in LANG_CODES[1:]]
        names = [fold(n.strip()) if n and not n.strip().endswith("?") else "" for n in names]
        if not any(names):
            continue
        short = short_form(names[0]) if r["section"] == "club" and names[0] else ""
        out.append([r["category"], r["id"]] + names + [short])
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["category", "id"] + list(LANG_CODES) + ["short"])
        w.writerows(out)
    print("%d names -> %s" % (len(out), out_path))


def cmd_apply(mes_path, out_path):
    if os.path.abspath(out_path) == os.path.abspath(mes_path):
        raise SystemExit("refusing to overwrite the input; write to a new file")
    with open(mes_path, "rb") as f:
        out, report = apply(f.read())
    with open(out_path, "wb") as f:
        f.write(out)
    for line in report:
        print(line)
    print("wrote %s" % out_path)


def main(argv):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "info" and len(args) == 1:
        cmd_info(args[0])
    elif cmd == "import" and len(args) in (1, 2):
        cmd_import(args[0], args[1] if len(args) == 2 else FILE)
    elif cmd == "apply" and len(args) == 2:
        cmd_apply(*args)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
