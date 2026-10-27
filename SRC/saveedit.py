# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Save editor for Let's Make a Soccer Team! (PS2): one window for one
career save on a PCSX2 memory card, a folder card or a card file
(DOC/SAVE_EDITOR_PLAN.md).

A save is a folder BESLES-54151-Gnnn (or -Mnnn for a modded disc's
saves) on the card. The window decodes it with save.py, which runs the
game's own save code (DOC/SAVE_FORMAT.md), and shows what save.py can
read, on one page each: the club, finances, the squad and youth team,
pair combinations, staff, the other clubs, the candidate lists and the
edit player imported from Virtua Pro Football.
Everything it shows and edits comes from save.py (Save methods,
Save.get, edit_spec and edit_range), so the window keeps no layout of
its own. Money shows in pounds (the stored unit / 6) next to the stored
value.

Every field `save.py set` can write has an input: money, club status and
status rank; the season plan; a player's 64 abilities (one or all),
condition fields, salary, contract years, age, injury value and captain
and keyman experience; pair combinations (one pair or all of a player's);
staff abilities, dissatisfaction and popularity; another club's
friendship and rank (the rival's rank follows your club status); the
edit player's name, database fields and abilities. Edits
go through save.apply_assigns, the function behind `save.py set`; a
value it refuses is put back. The candidate lists are shown only.

File > Save writes over the save's main file. First it copies the file
as it is to a backup folder beside the memory card, not in it (a folder
card shows the PS2 every folder in it):

    <card>.bak/<save folder>/<main file>.<date>-<time>.bak

and it logs the equivalent command in <card>.bak/saveedit.log, which
reads that backup and writes the same bytes:

    python SRC/save.py set <backup> <main file>.new money=... 3:12=80 ...

The command lists every accepted edit in order, repeats included: some
edits raise a hidden value as they go (an ability's growth limit and
cap, a pair's cap), so only the full sequence gives the same file.

File > Save to new slot keeps the original instead: it copies the save
folder to the card's lowest free slot (save.copy_save; slots 0-100, the
same letter, -G or -M), writes the edited save into the copy and opens
it. The log gets the two commands that do the same:

    python SRC/save.py copy <save folder> <slot>
    python SRC/save.py set <original main file> <new main file>.new ...

A save on a memory card file (.ps2, PCSX2's single-file cards) opens with
File > Open save on a card file, which lists the card's career saves.
The window edits a copy of the main file (<card>.bak/<folder>/<folder>.card);
Save writes it into the card with ps2mc.py (DOC/PS2MC_FORMAT.md), after
backing up the card and the main file in <card>.bak, and logs:

    python SRC/save.py set <main backup> <folder>.new ...
    python SRC/ps2mc.py put <card backup> <card>.new <folder>/<folder>=<folder>.new

Save to new slot copies the folder on the card (ps2mc copy_folder) and
writes the edit into the copy, logging `ps2mc.py copy` before those two.
Either way the save on the card must still be the one opened.

Close the game in PCSX2 before saving, so it doesn't write the card
over the edit.

Usage:
    python SRC/saveedit.py open [<save folder or main file>]
    python SRC/saveedit.py open <card.ps2> [<save folder>]
"""
import datetime
import os
import shutil
import sys
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import editor
import initteam
import pbdata
import ps2mc
import save

WINDOW = (1280, 720)
MES = os.path.join("DAT", "MESSAGE", "MES.PAC")
PBDATA = os.path.join("DAT", "PARAM", "PBDATA_EU.PAC")
GREY = "#555"
COMBI_COLOURS = ("#c8c8c8", "#e8e8e8", "#a8c8ff", "#ff9a9a", "#ff4a4a")    # levels 1-5
ABIL_ROWS = 16              # abilities per grid column


def money(value):
    return "%s (%s)" % (format(value, ","), save.pounds(value))


def tree(parent, cols, heads, widths, height=None):
    """A Treeview with a vertical scroll bar, packed to fill `parent`."""
    t = ttk.Treeview(parent, columns=cols, show="tree headings" if cols and cols[0] == "#0"
                     else "headings", selectmode="browse", height=height or 10)
    for c, text, width in zip(cols, heads, widths):
        if c == "#0":
            t.heading("#0", text=text)
            t.column("#0", width=width, stretch=False)
            continue
        t.heading(c, text=text)
        t.column(c, width=width, stretch=False, anchor="w")
    sb = ttk.Scrollbar(parent, orient="vertical", command=t.yview)
    t.configure(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    t.pack(side="left", fill="both", expand=True)
    return t


def grid_rows(parent, rows, start=0):
    """Label pairs (name, value) in two columns."""
    for r, (name, value) in enumerate(rows, start):
        ttk.Label(parent, text=name, foreground=GREY).grid(row=r, column=0, sticky="nw",
                                                         padx=(6, 12), pady=1)
        ttk.Label(parent, text=value).grid(row=r, column=1, sticky="nw", pady=1)


def assignment(key, value):
    """A save.py set assignment: key=value, the name as text."""
    return "%s=%s" % (key, value)


def shown(value):
    return value if isinstance(value, str) else format(value, ",")


def range_text(s, key):
    lo, hi, step, _ = save.edit_range(s, key)
    text = "%s-%s" % (format(lo, ","), format(hi, ","))
    return text + (" in steps of %d" % step if step > 1 else "")


class Names:
    """Names from the disc data: players and staff (PBDATA_EU.PAC), clubs,
    reputations and the accounts' lines (MES.PAC). Loaded once."""

    def __init__(self):
        db = pbdata.PbData(PBDATA)
        self.people = {r.db_id: r.name for kind in pbdata.KINDS for r in db.records(kind)}
        self.teams = initteam.team_names(MES, 1)
        self.reputations = initteam.category_names(MES, save.REPUTATION_CATEGORY)
        self.report = initteam.category_names(MES, save.REPORT_CATEGORY)
        self.rep_table = save.reputation_table()

    def reputation(self, rank):
        n = save.reputation(self.rep_table, rank)
        return self.reputations.get(n, "203:%d" % n)


# --- pages -------------------------------------------------------------------

class Page:
    """One page of the save. fill() draws it from the save; refresh()
    draws it again after an edit, keeping what was picked."""
    title = ""

    def __init__(self, app):
        self.app = app
        self.frame = ttk.Frame(app.notebook)

    def fill(self, s, names):
        pass

    def refresh(self):
        self.fill(self.app.save, self.app.names)

    def clear(self):
        for w in self.frame.winfo_children():
            w.destroy()


class ClubPage(Page):
    title = "Club"

    def fill(self, s, names):
        self.clear()
        year, turn, month, week = s.date()
        srank, cap, status, rank = s.status()
        box = ttk.Frame(self.frame)
        box.pack(anchor="nw", padx=8, pady=8)
        ttk.Label(box, text=os.path.basename(os.path.dirname(s.path)) or s.path,
                  font=self.app.title_font).grid(row=0, column=0, columnspan=3, sticky="w",
                                                 pady=(0, 6))
        grid_rows(box, (
            ("Date", "%d-%d, Week %d %s %s. (turn %d of the season)" % (
                year, year + 1, week // 2 + 1, ("Midweek", "Weekend")[week & 1],
                save.MONTHS[month - 1], turn)),
        ), start=1)
        rows = (("money", "Money", save.pounds(s.money), "the save's unit; below 0 is debt"),
                ("status", "Club status", "cap %s at this status rank" % format(cap, ","),
                 "the club ranks follow from it, as the game sets them"),
                ("status_rank", "Status rank", "0 is the top",
                 "the game only ever lowers it; lower the status first to go down"))
        for r, (key, text, note, help_text) in enumerate(rows, 2):
            ttk.Label(box, text=text, foreground=GREY).grid(row=r, column=0, sticky="w",
                                                            padx=(6, 12), pady=2)
            cell = ttk.Frame(box)
            cell.grid(row=r, column=1, sticky="w", pady=2)
            self.app.input(cell, key, self.refresh).pack(side="left")
            ttk.Label(cell, text=note, foreground=GREY).pack(side="left", padx=8)
            ttk.Label(box, text=help_text, foreground=GREY).grid(row=r, column=2, sticky="w",
                                                                 padx=(12, 6))
        grid_rows(box, (
            ("Club rank", "%d (%s)" % (rank, names.reputation(rank))),
            ("Rival's club rank", str(s.club(2)["rank"])),
            ("File", s.path),
        ), start=5)
        ttk.Label(box, text="Close the game in PCSX2 before File > Save, so it doesn't write "
                            "the memory card over the edit. Each save first copies the file "
                            "to %s." % backup_dir(s.path), foreground=GREY, wraplength=900,
                  justify="left").grid(row=8, column=0, columnspan=3, sticky="w", pady=(12, 0))


class FinancesPage(Page):
    title = "Finances"

    def fill(self, s, names):
        self.clear()
        top = ttk.Frame(self.frame)
        top.pack(fill="x", padx=8, pady=8)
        plan = ttk.LabelFrame(top, text="Season plan (the Accounting Dept.'s "
                                        "Administrative Plan)")
        plan.pack(side="left", anchor="n", padx=(0, 12))
        for r, (name, v) in enumerate(s.plan()):
            ttk.Label(plan, text=name, foreground=GREY).grid(row=r, column=0, sticky="w",
                                                             padx=(6, 12), pady=2)
            key = save.plan_key(name)
            cell = ttk.Frame(plan)
            cell.grid(row=r, column=1, sticky="w", pady=2)
            if key is None:
                ttk.Label(cell, text=money(v)).pack(side="left")
                ttk.Label(cell, text="follows the ticket price and the rate",
                          foreground=GREY).pack(side="left", padx=8)
                continue
            self.app.input(cell, key, self.refresh).pack(side="left")
            note = range_text(s, key)
            if name in save.PLAN_MONEY:
                note = "%s; %s" % (save.pounds(v), note)
            ttk.Label(cell, text=note, foreground=GREY).pack(side="left", padx=8)
        rows = [("stadium capacity", format(s.stadium_capacity(), ","))]
        rows += [("competition %#x ticket" % c, money(v)) for c, v in s.other_tickets()]
        grid_rows(plan, rows, start=len(s.plan()))
        ttk.Label(top, text="Amounts are in the save's money unit, with pounds (the unit / %d). "
                            "The ranges are the same in either currency; the game's plan "
                            "screen also moves money in steps (pounds: 60,000 of the unit), "
                            "which these inputs don't." % save.POUND, foreground=GREY,
                  wraplength=500, justify="left").pack(side="left", anchor="n")

        box = ttk.LabelFrame(self.frame, text="Accounts (Earnings Report lines, then each type)")
        box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        accounts = s.accounts()
        cols = ("#0", "month", "season")
        t = tree(box, cols, ("Line", accounts[0][0], accounts[1][0]), (360, 200, 200))
        line = save.REPORT_LINES
        for kind, groups, first, k in (("income", save.INCOME_GROUPS, save.INCOME_NAME, 1),
                                       ("payment", save.PAYMENT_GROUPS, save.PAYMENT_NAME, 2)):
            for group in groups:
                sums = [sum(acc[k][i] for i in group) for acc in accounts]
                parent = t.insert("", "end", text=names.report.get(line, "line %d" % line).strip(),
                                  values=[money(v) for v in sums], open=True)
                line += 1
                for i in group:
                    vals = [acc[k][i] for acc in accounts]
                    if any(vals):
                        t.insert(parent, "end", text="%s %d  %s" % (
                            kind, i, names.report.get(first + i, "").strip()),
                            values=[money(v) for v in vals])


class ListPage(Page):
    """A list on the left and the picked entry's page on the right."""
    current = None

    def build(self, cols, heads, widths):
        self.clear()
        panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(panes)
        self.list = tree(left, cols, heads, widths)
        self.list.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=1)
        self.detail = editor.Scrolled(panes)
        panes.add(self.detail.outer, weight=2)

    def reselect(self, hint):
        if self.current is not None and self.list.exists(self.current):
            self.list.selection_set(self.current)
            self.list.see(self.current)
            self.show(self.current)
        else:
            ttk.Label(self.detail.inner, text=hint, foreground=GREY).pack(anchor="w", padx=8,
                                                                         pady=8)

    def select(self):
        sel = self.list.selection()
        if sel and sel[0] != self.current or sel and not self.detail.inner.winfo_children():
            self.show(sel[0])

    def show(self, iid):
        self.current = iid


class SquadPage(ListPage):
    title = "Squad"

    def fill(self, s, names):
        self.build(("slot", "id", "name", "pos", "age", "ability"),
                   ("Slot", "Id", "Name", "Pos", "Age", "Mean ability"),
                   (45, 55, 150, 50, 40, 85))
        self.slots = dict(s.squad())
        for slot in self.slots:
            self.list.insert("", "end", iid=slot, values=self.row(slot))
        self.reselect("Pick a player. Youth team slots start with y.")

    def row(self, slot):
        s = self.app.save
        p = s.pinfo(self.slots[slot])
        return (slot, p["id"], p["name"], pbdata.position_name(p["pos"]), p["age"],
                s.get("%s:all" % slot))

    def show(self, slot):
        super().show(slot)
        s, o = self.app.save, self.slots[slot]
        p, db = s.pinfo(o), s.pbase_copy(o)
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s  %s" % (slot, p["name"]), font=self.app.title_font).pack(
            anchor="w", padx=8, pady=(8, 2))
        info = ttk.Frame(box)
        info.pack(anchor="w", padx=8, pady=4)
        learned, later = s.style_path(o)
        grid_rows(info, (
            ("Id, database", "%d, rank %d, positions %s" % (
                p["id"], db["rank"], "/".join(pbdata.position_name(x) for x in db["position"]))),
            ("Position, age", "%s, %d" % (pbdata.position_name(p["position"]), p["age"])),
            ("Body", "%d cm, %d kg, %s foot, shirt %d, nation %d" % (
                db["height"], db["weight"], "right" if db["leg"] & 1 else "left",
                db["shirt"], db["nation"])),
            ("Team fit", "%d%% (the game works it out from the vision below and the "
                         "manager's)" % p["team_fit"]),
            ("Injury", "kind %d, value %d (not days)" % (p["injury"], p["injury_value"])),
            ("Captain, keyman exp", "%d, %d" % (p["captain_exp"], p["keyman_exp"])),
            ("Play style", "%s; learned: %s; to learn: %s (progress %d)" % (
                save.style_name(p["play_style"]),
                ", ".join(map(save.style_name, learned)) or "-",
                ", ".join(map(save.style_name, later)) or "-", p["style_progress"])),
            ("Skills", ", ".join(pbdata.skill_names(db["skills"])) or "none"),
            ("Contract", "%d year%s left, %s a year" % (
                p["contract_years"], "" if p["contract_years"] == 1 else "s",
                money(p["salary"] * 100))),
        ))

        cond = ttk.LabelFrame(box, text="Condition, contract and experience")
        cond.pack(anchor="w", fill="x", padx=8, pady=4)
        fields = [t[len("<slot>:"):] for t, *_ in save.edit_spec(s)
                  if t.startswith("<slot>:") and t != "<slot>:<ability>"]
        for r, name in enumerate(fields):
            key = "%s:%s" % (slot, name)
            ttk.Label(cond, text=name.replace("_", " "), foreground=GREY).grid(
                row=r, column=0, sticky="w", padx=(6, 12), pady=1)
            self.app.input(cond, key).grid(row=r, column=1, sticky="w", pady=1)
            _, _, _, note = save.edit_range(s, key)
            ttk.Label(cond, text="%s; %s" % (range_text(s, key), note), foreground=GREY,
                      wraplength=600, justify="left").grid(row=r, column=2, sticky="w",
                                                           padx=(12, 6))

        self.bars = ttk.Label(box, text="")
        self.bars.pack(anchor="w", padx=8, pady=4)
        if slot.isdigit():
            stats = ttk.LabelFrame(box, text="Stats: games, goals, assists, man of the match, "
                                             "yellow, red, points")
            row = 0
            for table, rows in s.stats(int(slot)).items():
                for comp, (gol, ast, games, _, mom, pnt, red, ylw) in zip(save.COMPETITIONS,
                                                                          rows):
                    if games:
                        ttk.Label(stats, text="%s, %s" % (table, comp), foreground=GREY).grid(
                            row=row, column=0, sticky="w", padx=(6, 12))
                        ttk.Label(stats, text="%d  %d  %d  %d  %d  %d  %.2f" % (
                            games, gol, ast, mom, ylw, red, pnt / 100)).grid(
                            row=row, column=1, sticky="w")
                        row += 1
            if row:
                stats.pack(anchor="w", fill="x", padx=8, pady=4)

        abil = ttk.LabelFrame(box, text="Abilities: level (0-99), then growth limit and cap. "
                                        "Raising a level raises the limit and cap with it, "
                                        "as save.py set does")
        abil.pack(anchor="w", padx=8, pady=4)
        all_row = ttk.Frame(abil)
        all_row.grid(row=0, column=0, columnspan=12, sticky="w", padx=6, pady=(2, 6))
        ttk.Label(all_row, text="all 64 (the mean shown)", foreground=GREY).pack(side="left")
        self.app.input(all_row, "%s:all" % slot, lambda: self.show(slot)).pack(
            side="left", padx=8)
        self.limits = []
        for k in range(save.ABIL_COUNT):
            r, c = 1 + k % ABIL_ROWS, (k // ABIL_ROWS) * 3
            ttk.Label(abil, text="%d" % k, foreground=GREY).grid(row=r, column=c, sticky="e",
                                                                 padx=(10, 4))
            self.app.input(abil, "%s:%d" % (slot, k), lambda: self.update(slot)).grid(
                row=r, column=c + 1, sticky="w")
            lim = ttk.Label(abil, text="", foreground=GREY, width=7)
            lim.grid(row=r, column=c + 2, sticky="w", padx=(4, 6))
            self.limits.append(lim)
        self.update(slot)

    def update(self, slot):
        """After an ability edit: limits, caps, bars and the list's mean."""
        s = self.app.save
        p = s.pinfo(self.slots[slot])
        lv = [save.exp2lv(s.exp, a[0]) for a in p["abil"]]
        for lim, (_, mid, cap) in zip(self.limits, p["abil"]):
            lim.configure(text="%2d %2d" % (save.exp2lv(s.exp, mid), save.exp2lv(s.exp, cap)))
        self.bars.configure(text="Bars  " + "   ".join("%s %d" % b for b in pbdata.bars(
            lv, p["position"] == 0)))
        self.list.item(slot, values=self.row(slot))


class CombiPage(ListPage):
    title = "Combinations"

    def fill(self, s, names):
        self.build(("slot", "name", "mean"), ("Slot", "Name", "Mean value"), (45, 150, 80))
        self.filled = [(i, s.pinfo(o)["name"]) for i, o in s.squad() if i.isdigit()]
        for slot, name in self.filled:
            self.list.insert("", "end", iid=slot, values=(slot, name,
                                                          s.get("combi:%s:all" % slot)))
        self.reselect("Pick a player to see and edit his pairs, as the tactics screen's "
                      "icons: %s." % ", ".join("%d %s" % (i + 1, icon) for i, icon in
                                               enumerate(save.COMBI_ICONS)))

    def show(self, a):
        super().show(a)
        s = self.app.save
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s  %s: pairs" % (a, dict(self.filled)[a]),
                  font=self.app.title_font).grid(row=0, column=0, columnspan=5, sticky="w",
                                                 padx=8, pady=(8, 2))
        legend = ttk.Frame(box)
        legend.grid(row=1, column=0, columnspan=5, sticky="w", padx=8, pady=(0, 4))
        for i, icon in enumerate(save.COMBI_ICONS):
            tk.Label(legend, text=" %d %s " % (i + 1, icon), bg=COMBI_COLOURS[i]).pack(
                side="left", padx=2)
        ttk.Label(box, text="all pairs (the mean shown)", foreground=GREY).grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8)
        self.app.input(box, "combi:%s:all" % a, lambda: self.refresh()).grid(
            row=2, column=2, sticky="w", pady=(0, 6))
        ttk.Label(box, text=range_text(s, "combi:%s:all" % a) + "; a higher value raises the "
                            "pair's cap with it, as save.py set does",
                  foreground=GREY).grid(row=2, column=3, columnspan=2, sticky="w", padx=8)
        for r, (b, name) in enumerate(self.filled, 3):
            if b == a:
                continue
            ttk.Label(box, text=b, foreground=GREY).grid(row=r, column=0, sticky="e",
                                                         padx=(8, 4))
            ttk.Label(box, text=name).grid(row=r, column=1, sticky="w", padx=(0, 8))
            level = tk.Label(box, text="", width=18, anchor="w")
            level.grid(row=r, column=3, sticky="w", padx=4)

            def show_level(b=b, level=level):
                value, cap = s.combi(int(a), int(b))
                lv = save.combi_level(value)
                level.configure(text="%d %s, cap %d" % (lv, save.COMBI_ICONS[lv - 1], cap),
                                bg=COMBI_COLOURS[lv - 1])
            self.app.input(box, "combi:%s:%s" % (a, b), lambda f=show_level: (
                f(), self.list.item(a, values=(a, dict(self.filled)[a],
                                               s.get("combi:%s:all" % a))))).grid(
                row=r, column=2, sticky="w", pady=1)
            show_level()


class StaffPage(ListPage):
    title = "Staff"

    def fill(self, s, names):
        self.build(("label", "name", "role"), ("Slot", "Name", "Role"), (80, 150, 110))
        self.staff = {label: (role, st) for label, role, _, st in s.staff_labels()}
        for label, (role, st) in self.staff.items():
            self.list.insert("", "end", iid=label, values=(label, st["name"], role))
        self.reselect("Pick a manager, coach or scout.")

    def show(self, label):
        super().show(label)
        s = self.app.save
        role, st = self.staff[label]
        st = {lb: x for lb, _, _, x in s.staff_labels()}[label]
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s  %s (id %d)" % (label, st["name"], st["id"]),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        job = st["job"]
        rows = []
        if job is not None:
            rows.append(("Job", "%d %s" % (job, pbdata.JOB_NAMES[job]
                                            if job < len(pbdata.JOB_NAMES) else "?")))
        rows.append(("Contract", "%d year%s left, %s a year" % (
            st["contract_years"], "" if st["contract_years"] == 1 else "s",
            money(st["salary"] * 100))))
        if st["kind"] == "M" and st["discount"]:
            rows.append(("Salary", "discount"))
        info = ttk.Frame(box)
        info.pack(anchor="w", padx=8, pady=4)
        grid_rows(info, rows)
        if st["kind"] == "M":
            frame = ttk.LabelFrame(box, text="Dissatisfaction and popularity (0-65535)")
            frame.pack(anchor="w", padx=8, pady=4)
            keys = [("dissat.%d" % k, "dissatisfaction: %s" % name)
                    for k, name in enumerate(save.M_DISSAT_KINDS)]
            keys += [("pop_supporters", "popularity with supporters"),
                     ("pop_players", "popularity with players")]
            for r, (field, text) in enumerate(keys):
                ttk.Label(frame, text=text, foreground=GREY).grid(row=r, column=0, sticky="w",
                                                                  padx=(6, 12), pady=1)
                self.app.input(frame, "%s:%s" % (label, field)).grid(row=r, column=1,
                                                                     sticky="w", pady=1)
        self.bars = ttk.Label(box, text="")
        self.bars.pack(anchor="w", padx=8, pady=4)
        abil = ttk.LabelFrame(box, text="Abilities (%s)" % range_text(s, "%s:abil.0" % label))
        abil.pack(anchor="w", padx=8, pady=4)
        all_row = ttk.Frame(abil)
        all_row.grid(row=0, column=0, columnspan=12, sticky="w", padx=6, pady=(2, 6))
        ttk.Label(all_row, text="all %d (the mean shown)" % len(st["abil"]),
                  foreground=GREY).pack(side="left")
        self.app.input(all_row, "%s:abil.all" % label, lambda: self.show(label)).pack(
            side="left", padx=8)
        for k in range(len(st["abil"])):
            r, c = 1 + k % ABIL_ROWS, (k // ABIL_ROWS) * 2
            ttk.Label(abil, text="%d" % k, foreground=GREY).grid(row=r, column=c, sticky="e",
                                                                 padx=(10, 4))
            self.app.input(abil, "%s:abil.%d" % (label, k), lambda: self.update(label)).grid(
                row=r, column=c + 1, sticky="w")
        self.update(label)

    def update(self, label):
        st = {lb: x for lb, _, _, x in self.app.save.staff_labels()}[label]
        if st["job"] is None:
            bars = pbdata.average_bars(st["abil"], pbdata.SCOUT_BARS)
        else:
            bars = pbdata.staff_bars(st["abil"], pbdata.JOB_ROLE.get(st["job"], "manager"))
        self.bars.configure(text="Bars  " + "   ".join("%s %d" % b for b in bars))


class ClubsPage(Page):
    title = "Other clubs"
    current = None

    def fill(self, s, names):
        self.clear()
        self.names = names
        panes = ttk.PanedWindow(self.frame, orient="vertical")
        panes.pack(fill="both", expand=True, padx=6, pady=6)
        top = ttk.Frame(panes)
        cols = ("team", "name", "friendship", "rank", "reputation", "world", "points",
                "league", "players")
        self.list = tree(top, cols, ("Team", "Club", "Friendship", "Rank", "Reputation",
                                     "World rank", "Points", "League", "Players"),
                         (50, 180, 75, 45, 150, 75, 60, 55, 60))
        self.list.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(top, weight=3)
        bottom = ttk.Frame(panes)
        self.edit = ttk.Frame(bottom)
        self.edit.pack(side="top", fill="x", pady=(0, 4))
        self.players = tree(bottom, ("slot", "id", "name", "age", "shirt", "years", "flags"),
                            ("Slot", "Id", "Player", "Age", "Shirt", "Contract", "Flags"),
                            (45, 60, 180, 45, 50, 70, 60), height=6)
        panes.add(bottom, weight=2)
        for team in [2] + list(range(3, save.CLUBS + 2)):
            self.list.insert("", "end", iid=str(team), values=self.row(team))
        if self.current is not None:
            self.list.selection_set(self.current)
            self.list.see(self.current)
            self.show(self.current)
        else:
            ttk.Label(self.edit, text="Pick a club to see its players and edit its friendship "
                                      "and rank.", foreground=GREY).pack(anchor="w")

    def row(self, team):
        c = self.app.save.club(team)
        return (team, self.names.teams.get(team, ""), c["friendship"], c["rank"],
                self.names.reputation(c["rank"]), c["world_rank"], c["points"], c["league"],
                len(c["players"]))

    def select(self):
        sel = self.list.selection()
        if sel and sel[0] != self.current:
            self.show(sel[0])

    def show(self, team):
        self.current = team
        s = self.app.save
        for w in self.edit.winfo_children():
            w.destroy()
        ttk.Label(self.edit, text="%s %s" % (team, self.names.teams.get(int(team), "")),
                  font=self.app.title_font).pack(side="left", padx=(0, 12))
        ttk.Label(self.edit, text="friendship", foreground=GREY).pack(side="left")
        self.app.input(self.edit, "club:%s:friendship" % team,
                       lambda: self.list.item(team, values=self.row(int(team)))).pack(
            side="left", padx=(4, 12))
        ttk.Label(self.edit, text="rank", foreground=GREY).pack(side="left")
        if team == "2":
            # set_status writes the rival's rank from your club rank (0x26dd40).
            ttk.Label(self.edit, text="%d (your rival: it follows your club status)"
                      % s.club(2)["rank"]).pack(side="left", padx=4)
        else:
            self.app.input(self.edit, "club:%s:rank" % team,
                           lambda: self.list.item(team, values=self.row(int(team)))).pack(
                side="left", padx=4)
            ttk.Label(self.edit, text=range_text(s, "club:%s:rank" % team),
                      foreground=GREY).pack(side="left", padx=4)
        self.players.delete(*self.players.get_children())
        for k, pid, age, shirt, years, flags in s.club(int(team))["players"]:
            self.players.insert("", "end", values=(
                k, pid, self.names.people.get(pid, "?"), age, "-" if shirt < 0 else shirt,
                years, "%#x" % flags if flags else ""))


class CandidatesPage(Page):
    title = "Candidates"

    def fill(self, s, names):
        self.clear()
        ttk.Label(self.frame, text="Shown only: save.py doesn't edit the candidate lists yet.",
                  foreground=GREY).pack(anchor="w", padx=8, pady=(6, 0))
        box = ttk.Frame(self.frame)
        box.pack(fill="both", expand=True, padx=6, pady=6)
        t = tree(box, ("#0", "id", "name", "turns", "pos", "age"),
                 ("List", "Id", "Name", "Turns left", "Position", "Age"),
                 (200, 60, 200, 80, 70, 50))
        for name, count, rows in s.candidates():
            parent = t.insert("", "end", text="%s (%d of %d)" % (name, len(rows), count),
                              open=True)
            for pid, turns, youth in rows:
                t.insert(parent, "end", values=(
                    pid, names.people.get(pid, "?"), turns,
                    pbdata.position_name(youth[0]) if youth else "",
                    youth[1] if youth else ""))


def backup_dir(main):
    """<card>.bak/<save folder> for a save's main file <card>/<folder>/<file>:
    beside the memory card, since a folder card shows the PS2 every folder
    in it."""
    folder = os.path.dirname(os.path.abspath(main))
    card = os.path.dirname(folder)
    return os.path.join(card + ".bak", os.path.basename(folder))


def card_bak(card):
    """<card>.bak beside a memory card file: its backups and log."""
    return os.path.abspath(card) + ".bak"


def card_work(card, folder):
    """The copy of a card file's save that the window edits."""
    return os.path.join(card_bak(card), folder, folder + ".card")


def card_saves(card):
    """The career saves (-G and -M folders) on a card file, in name order."""
    names = []
    for name in card.folders():
        try:
            if save.save_name(name)[1] in "GM":
                names.append(name)
        except ValueError:
            pass
    return sorted(names)


class EditPlayerPage(Page):
    title = "Edit player"

    def fill(self, s, names):
        self.clear()
        ep = s.edit_player()
        if ep is None:
            ttk.Label(self.frame, text="This career has no edit player. The game's player "
                                       "editor imports one from Virtua Pro Football "
                                       "(PMPLAYER_FORMAT.md).", foreground=GREY).pack(
                anchor="w", padx=8, pady=8)
            return
        detail = editor.Scrolled(self.frame)
        detail.outer.pack(fill="both", expand=True)
        box = detail.inner
        ttk.Label(box, text="%s  (id %#x, %s)" % (
            ep["name"], save.EDIT_ID, "squad slot %s" % ep["slot"] if ep["slot"] is not None
            else "not in your squad"), font=self.app.title_font).pack(anchor="w", padx=8,
                                                                       pady=(8, 2))
        ttk.Label(box, text="The player's database record, which a career keeps in the save "
                            "instead of PBDATA. The first fields are also in the squad "
                            "player's own copy, and an edit changes both. His abilities in "
                            "matches and training are the Squad page's; these are the "
                            "record's.", foreground=GREY, wraplength=900,
                  justify="left").pack(anchor="w", padx=8, pady=(0, 6))
        top = ttk.Frame(box)
        top.pack(anchor="w", padx=8, pady=4)
        ttk.Label(top, text="name", foreground=GREY).grid(row=0, column=0, sticky="w",
                                                         padx=(6, 12), pady=1)
        var = tk.StringVar(value=ep["name"])
        entry = ttk.Entry(top, textvariable=var, width=24)
        entry.grid(row=0, column=1, sticky="w", pady=1)

        def commit_name(event=None):
            if var.get() != self.app.save.get("edit:name"):
                self.app.commit("edit:name", var.get(),
                                lambda: var.set(self.app.save.get("edit:name")), self.refresh)
        entry.bind("<Return>", commit_name)
        entry.bind("<FocusOut>", commit_name)
        self.name_entry = entry
        ttk.Label(top, text="1-%d characters" % save.NAME_LEN, foreground=GREY).grid(
            row=0, column=2, sticky="w", padx=(12, 6))
        fields = [f for f in save.edit_fields() if f[5] != "ability"]
        per_col = (len(fields) + 2) // 3
        for i, (key, _, _, _, _, _) in enumerate(fields):
            r, c = 1 + i % per_col, (i // per_col) * 3
            ttk.Label(top, text=key[5:].replace("_", " "), foreground=GREY).grid(
                row=r, column=c, sticky="w", padx=(6, 8), pady=1)
            self.app.input(top, key).grid(row=r, column=c + 1, sticky="w", pady=1)
            ttk.Label(top, text=range_text(s, key), foreground=GREY).grid(
                row=r, column=c + 2, sticky="w", padx=(4, 12))
        abil = ttk.LabelFrame(box, text="Abilities (%d-%d)" % save.EDIT_ABIL_RANGE)
        abil.pack(anchor="w", padx=8, pady=4)
        all_row = ttk.Frame(abil)
        all_row.grid(row=0, column=0, columnspan=12, sticky="w", padx=6, pady=(2, 6))
        ttk.Label(all_row, text="all 64 (the mean shown)", foreground=GREY).pack(side="left")
        self.app.input(all_row, "edit:ability.all", self.refresh).pack(side="left", padx=8)
        for k in range(save.ABIL_COUNT):
            r, c = 1 + k % ABIL_ROWS, (k // ABIL_ROWS) * 2
            ttk.Label(abil, text="%d %s" % (k, pbdata.ABILITY_NAMES[k]), foreground=GREY).grid(
                row=r, column=c, sticky="e", padx=(10, 4))
            self.app.input(abil, "edit:ability.%d" % k).grid(row=r, column=c + 1, sticky="w")


PAGES = (ClubPage, FinancesPage, SquadPage, CombiPage, StaffPage, ClubsPage, CandidatesPage,
         EditPlayerPage)


# --- the window --------------------------------------------------------------

class App:
    def __init__(self, path=None, folder=None):
        try:        # sharp text on Windows with display scaling
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError, OSError):
            pass
        self.root = tk.Tk()
        self.title_font = editor.tkfont.nametofont("TkDefaultFont").copy()
        self.title_font.configure(size=12, weight="bold")
        w = min(WINDOW[0], self.root.winfo_screenwidth() - 80)
        h = min(WINDOW[1], self.root.winfo_screenheight() - 120)
        self.root.geometry("%dx%d+%d+%d" % (w, h, (self.root.winfo_screenwidth() - w) // 2,
                                            (self.root.winfo_screenheight() - h) // 3))
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Open save...", accelerator="Ctrl+O", command=self.ask_open)
        file_menu.add_command(label="Open save on a card file...", command=self.ask_open_card)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.write)
        file_menu.add_command(label="Save to new slot...", command=self.write_new_slot)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit)
        menu.add_cascade(label="File", menu=file_menu)
        self.root.configure(menu=menu)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind_all("<Control-o>", lambda e: self.ask_open())
        self.root.bind_all("<Control-s>", lambda e: self.write())
        self.changes = []           # (save.py set key, value): every accepted edit, in order
        self.stale = set()          # pages to draw again when they are shown
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<<NotebookTabChanged>>", lambda e: self.tab_changed())
        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken"
                  ).pack(fill="x", side="bottom")
        self.pages = [cls(self) for cls in PAGES]
        for page in self.pages:
            self.notebook.add(page.frame, text=page.title)
        self.game = self.names = self.save = None
        self.card = None            # (card file, save folder) for a save from a card file
        self.card_dialog = None
        self.root.title("LMAST save editor")
        self.status("Open a save folder (BESLES-54151-G000 and so on) on a PCSX2 folder "
                    "memory card: File > Open save. For a card file (.ps2): File > Open "
                    "save on a card file.")
        if path and os.path.isfile(path) and path.lower().endswith(".ps2"):
            if folder:
                self.open_card(path, folder)
            else:
                self.choose_card_save(path)
        elif path:
            self.open(path)

    def status(self, text):
        self.status_var.set(text)

    def page(self):
        return self.pages[self.notebook.index("current")]

    def tab_changed(self):
        page = self.page()
        if page in self.stale and self.save is not None:
            self.stale.discard(page)
            page.refresh()

    def ask_open(self):
        if not self.keep_changes():
            return
        path = filedialog.askdirectory(title="Open a save folder (BESLES-54151-...)",
                                       mustexist=True)
        if path:
            self.open(path)

    def ask_open_card(self):
        if not self.keep_changes():
            return
        path = filedialog.askopenfilename(title="Open a PCSX2 memory card file",
                                          filetypes=[("PS2 memory card", "*.ps2"),
                                                     ("All files", "*.*")])
        if path:
            self.choose_card_save(path)

    def choose_card_save(self, path):
        """A small window listing the card file's career saves."""
        try:
            names = card_saves(ps2mc.load(path))
        except (ValueError, OSError) as e:
            messagebox.showerror("Save editor", "Can't read %s:\n%s" % (path, e))
            return
        if not names:
            messagebox.showerror("Save editor", "%s holds no career saves (BESLES-54151-G or "
                                                "-M folders)." % path)
            return
        top = tk.Toplevel(self.root)
        top.title("Saves on %s" % os.path.basename(path))
        top.transient(self.root)
        ttk.Label(top, text="Career saves on %s:" % editor.shown_path(path)).pack(
            anchor="w", padx=8, pady=(8, 4))
        box = tk.Listbox(top, height=min(12, len(names)), width=36, exportselection=False)
        for name in names:
            box.insert("end", name)
        box.selection_set(0)
        box.pack(fill="both", expand=True, padx=8)
        buttons = ttk.Frame(top)
        buttons.pack(anchor="e", padx=8, pady=8)

        def choose(event=None):
            picked = box.curselection()
            if picked:
                top.destroy()
                self.card_dialog = None
                self.open_card(path, names[picked[0]])
        ttk.Button(buttons, text="Open", command=choose).pack(side="left", padx=4)
        ttk.Button(buttons, text="Cancel", command=top.destroy).pack(side="left")
        box.bind("<Double-Button-1>", choose)
        self.card_dialog = (top, box, choose)

    def open_card(self, path, folder, done=None):
        """Open save `folder` on a card file: its main file is copied to
        <card>.bak/<folder>/<folder>.card, which the window edits."""
        work = card_work(path, folder)
        try:
            card = ps2mc.load(path)
            _, e = card.find("%s/%s" % (folder, folder))
            if e is None:
                raise ValueError("%s has no main file %s" % (folder, folder))
            os.makedirs(os.path.dirname(work), exist_ok=True)
            with open(work, "wb") as f:
                f.write(card.read_file(e))
        except (ValueError, OSError) as e:
            messagebox.showerror("Save editor", "Can't open %s on %s:\n%s" % (folder, path, e))
            return
        self.open(work, done or "Opened %s on %s." % (folder, editor.shown_path(path)),
                  card=(os.path.abspath(path), folder))

    def where(self):
        """The open save, as the title and messages show it."""
        if self.card:
            return "%s on %s" % (self.card[1], editor.shown_path(self.card[0]))
        return editor.shown_path(self.save.path)

    def open(self, path, done=None, card=None):
        """Decode the save (and the names, the first time) in a thread; the
        first decode of a session records save.py's field list. `card` is
        (card file, save folder) when `path` is a save copied off a card file."""
        self.status("Loading %s ..." % path)
        self.root.configure(cursor="watch")
        result = {}

        def work():
            try:
                if self.game is None:
                    result["game"] = save.Game()
                if self.names is None:
                    result["names"] = Names()
                result["save"] = save.Save(result.get("game") or self.game, path)
            except Exception as e:      # shown in the window, not lost in a thread
                result["error"] = e

        thread = threading.Thread(target=work, daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                self.root.after(100, poll)
                return
            self.root.configure(cursor="")
            if "error" in result:
                self.status("Couldn't open %s: %s" % (path, result["error"]))
                messagebox.showerror("Save editor", "Couldn't open %s:\n%s"
                                     % (path, result["error"]))
                return
            self.game = result.get("game") or self.game
            self.names = result.get("names") or self.names
            self.card = card
            self.loaded(result["save"], done)
        poll()

    def loaded(self, s, done=None):
        same = self.save is not None and self.save.path == s.path
        self.save = s
        self.changes = []
        self.stale = set()
        for page in self.pages:
            if not same and hasattr(page, "current"):
                page.current = None
            page.fill(s, self.names)
        self.update_title()
        self.status(done or "Opened %s." % self.where())

    def update_title(self):
        if self.save is None:
            return
        self.root.title("LMAST save editor - %s%s" % (
            self.where(), "  (unsaved: %d changes)" % len(self.changes)
            if self.changes else ""))

    # edits

    def input(self, parent, key, after=None):
        """A spin box for a concrete save.py set key, its range from
        save.edit_range. after() runs once an edit is accepted, to redraw
        what follows from it on this page."""
        lo, hi, step, _ = save.edit_range(self.save, key)
        return editor.value_input(
            parent, ("range", lo, hi, step), str, lambda: self.save.get(key),
            lambda text, revert: self.commit(key, text, revert, after))

    def commit(self, key, text, revert, after=None):
        if key in save.TEXT_KEYS:
            value = text
        else:
            try:
                value = int(text)
            except ValueError:
                return self.refuse("%s must be a number" % key, revert)
        old = self.save.get(key)
        before = bytes(self.save.blocks)
        try:
            save.apply_assigns(self.save, [assignment(key, value)])
        except ValueError as e:
            self.save.blocks[:] = before
            return self.refuse(str(e), revert)
        self.changes.append((key, value))
        current = self.page()
        self.stale = {p for p in self.pages if p is not current}
        if after:
            # Redraw after the widget's own event has finished.
            self.root.after_idle(after)
        self.update_title()
        self.status("%s: %s -> %s" % (key, shown(old), shown(value)))
        return True

    def refuse(self, message, revert):
        revert()
        self.status(message)
        messagebox.showerror("Save editor", message)
        return False

    # saving

    def write(self):
        """Back up the main file, write the edited save over it and log the
        save.py set command that gives the same bytes from the backup."""
        if self.save is None or not self.changes:
            return True
        if self.card:
            return self.write_card()
        s = self.save
        main = s.path
        folder = backup_dir(main)
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = os.path.join(folder, "%s.%s.bak" % (os.path.basename(main), stamp))
        new = main + ".new"
        try:
            data = s.encode()
            os.makedirs(folder, exist_ok=True)
            with open(main, "rb") as f:
                original = f.read()
            if original != s.file:
                raise ValueError("the file changed on disk since it was opened (was the game "
                                 "running?); open it again")
            with open(backup, "wb") as f:
                f.write(original)
            with open(new, "wb") as f:
                f.write(data)
            os.replace(new, main)
        except (ValueError, OSError) as e:
            if os.path.exists(new):
                os.remove(new)
            messagebox.showerror("Save editor", "Can't save: %s" % e)
            return False
        cmd = ["python", "SRC/save.py", "set", editor.quote(editor.shown_path(backup)),
               editor.quote(editor.shown_path(new))]
        cmd += [editor.quote(assignment(*kv)) for kv in self.changes]
        n = len(self.changes)
        lines = editor.log_lines("%s: %d changes" % (os.path.basename(main), n),
                                 [cmd], [(new, main)], moved="the .new file")
        with open(os.path.join(os.path.dirname(folder), "saveedit.log"), "a",
                  encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")
        self.open(main, "Saved %s: %d changes (backup %s)" % (
            editor.shown_path(main), n, editor.shown_path(backup)))
        return True

    def write_new_slot(self):
        """Copy the save folder to the card's next free slot (save.copy_save)
        and write the edited save into the copy, leaving the original as it
        is. Logs `save.py copy` and the `save.py set` that writes the same
        bytes from the original, then opens the copy."""
        if self.save is None:
            return False
        if self.card:
            return self.write_card_new_slot()
        s = self.save
        main = s.path
        src = os.path.dirname(os.path.abspath(main))
        card = os.path.dirname(src)
        try:
            prefix, letter, _ = save.save_name(src)
            n = save.free_slot(card, letter)
        except ValueError as e:
            messagebox.showerror("Save editor", "Can't save to a new slot: %s" % e)
            return False
        name = "%s%s%03d" % (prefix, letter, n)
        if not messagebox.askokcancel("Save to new slot", "Save as %s on this card?\n%s stays "
                                      "as it is." % (name, os.path.basename(src))):
            return False
        dst = os.path.join(card, name)
        dst_main = os.path.join(dst, name)
        new = dst_main + ".new"
        copied = False
        try:
            # With no edits the copy is the save as it is: nothing to encode.
            data = s.encode() if self.changes else None
            with open(main, "rb") as f:
                if f.read() != s.file:
                    raise ValueError("the file changed on disk since it was opened (was the "
                                     "game running?); open it again")
            save.copy_save(src, dst)
            copied = True
            if data is not None:
                with open(new, "wb") as f:
                    f.write(data)
                os.replace(new, dst_main)
        except (ValueError, OSError) as e:
            if copied:
                shutil.rmtree(dst, ignore_errors=True)
            messagebox.showerror("Save editor", "Can't save to a new slot: %s" % e)
            return False
        cmds = [["python", "SRC/save.py", "copy", editor.quote(editor.shown_path(src)), str(n)]]
        n_changes = len(self.changes)
        if self.changes:
            cmds.append(["python", "SRC/save.py", "set", editor.quote(editor.shown_path(main)),
                         editor.quote(editor.shown_path(new))]
                        + [editor.quote(assignment(*kv)) for kv in self.changes])
        lines = editor.log_lines("%s -> %s: %d changes" % (os.path.basename(src), name, n_changes),
                                 cmds, [(new, dst_main)], moved="the .new file")
        if not self.changes:
            lines = [line for line in lines if not line.startswith("# then ")]
        log_dir = card + ".bak"
        os.makedirs(log_dir, exist_ok=True)
        with open(os.path.join(log_dir, "saveedit.log"), "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")
        self.open(dst, "Saved %s: %d changes; %s is unchanged" % (
            editor.shown_path(dst), n_changes, os.path.basename(src)))
        return True

    # saving to a card file

    def read_card(self):
        """The card file as it is now, and the open save's main file on it,
        which must still be the bytes the window opened."""
        path, folder = self.card
        with open(path, "rb") as f:
            raw = f.read()
        card = ps2mc.Card(raw)
        _, e = card.find("%s/%s" % (folder, folder))
        if e is None or card.read_file(e) != self.save.file:
            raise ValueError("the save changed on the card since it was opened (was the game "
                             "running?); open it again")
        return raw, card

    def replace_card(self, raw, card, backup):
        """Check the edited card, back the old one up and write the new one
        over it (<card>.new, then moved)."""
        path = self.card[0]
        out = card.flush()
        _, probs = ps2mc.Card(out).check()
        if probs:
            raise ValueError("the edited card fails its checks: %s" % "; ".join(probs))
        os.makedirs(os.path.dirname(backup), exist_ok=True)
        with open(backup, "wb") as f:
            f.write(raw)
        with open(path + ".new", "wb") as f:
            f.write(out)
        os.replace(path + ".new", path)

    def log_card(self, title, cmds):
        path = self.card[0]
        lines = editor.log_lines(title, cmds, [(path + ".new", path)], moved="the .new card")
        with open(os.path.join(card_bak(path), "saveedit.log"), "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")

    def write_card(self):
        """Write the edited save into its card file. The card and the save's
        main file are backed up in <card>.bak first, and the log gets the
        save.py set and ps2mc.py put that give the same card from them."""
        path, folder = self.card
        s = self.save
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = card_bak(path)
        card_backup = os.path.join(bak, "%s.%s.bak" % (os.path.basename(path), stamp))
        main_backup = os.path.join(bak, folder, "%s.%s.bak" % (folder, stamp))
        new_main = os.path.join(bak, folder, folder + ".new")
        try:
            data = s.encode()
            raw, card = self.read_card()
            card.put("%s/%s" % (folder, folder), data)
            os.makedirs(os.path.dirname(main_backup), exist_ok=True)
            with open(main_backup, "wb") as f:
                f.write(s.file)
            self.replace_card(raw, card, card_backup)
        except (ValueError, OSError) as e:
            if os.path.exists(path + ".new"):
                os.remove(path + ".new")
            messagebox.showerror("Save editor", "Can't save: %s" % e)
            return False
        n = len(self.changes)
        q = lambda p: editor.quote(editor.shown_path(p))
        self.log_card("%s on %s: %d changes" % (folder, os.path.basename(path), n), [
            ["python", "SRC/save.py", "set", q(main_backup), q(new_main)]
            + [editor.quote(assignment(*kv)) for kv in self.changes],
            ["python", "SRC/ps2mc.py", "put", q(card_backup), q(path + ".new"),
             editor.quote("%s/%s=%s" % (folder, folder, editor.shown_path(new_main)))]])
        self.open_card(path, folder, "Saved %s: %d changes (backup %s)" % (
            self.where(), n, editor.shown_path(card_backup)))
        return True

    def write_card_new_slot(self):
        """Copy the save folder to the card file's lowest free slot (ps2mc
        copy_folder) and write the edited save into the copy, leaving the
        original as it is; then open the copy."""
        path, src = self.card
        s = self.save
        try:
            prefix, letter, _ = save.save_name(src)
            raw, card = self.read_card()
            taken = set(card.folders())
            free = [n for n in range(save.SLOT_MAX + 1)
                    if "%s%s%03d" % (prefix, letter, n) not in taken]
            if not free:
                raise ValueError("no free %s slot on the card (0-%d are taken)"
                                 % (letter, save.SLOT_MAX))
        except (ValueError, OSError) as e:
            messagebox.showerror("Save editor", "Can't save to a new slot: %s" % e)
            return False
        name = "%s%s%03d" % (prefix, letter, free[0])
        if not messagebox.askokcancel("Save to new slot", "Save as %s on this card?\n%s stays "
                                      "as it is." % (name, src)):
            return False
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        bak = card_bak(path)
        card_backup = os.path.join(bak, "%s.%s.bak" % (os.path.basename(path), stamp))
        main_backup = os.path.join(bak, src, "%s.%s.bak" % (src, stamp))
        copied = os.path.join(bak, os.path.basename(path) + ".copy")
        new_main = os.path.join(bak, name, name + ".new")
        try:
            data = s.encode() if self.changes else None
            card.copy_folder(src, name)
            if data is not None:
                card.put("%s/%s" % (name, name), data)
                os.makedirs(os.path.dirname(main_backup), exist_ok=True)
                with open(main_backup, "wb") as f:
                    f.write(s.file)
            self.replace_card(raw, card, card_backup)
        except (ValueError, OSError) as e:
            if os.path.exists(path + ".new"):
                os.remove(path + ".new")
            messagebox.showerror("Save editor", "Can't save to a new slot: %s" % e)
            return False
        n = len(self.changes)
        q = lambda p: editor.quote(editor.shown_path(p))
        if data is None:
            cmds = [["python", "SRC/ps2mc.py", "copy", q(card_backup), q(path + ".new"),
                     src, name]]
        else:
            cmds = [["python", "SRC/ps2mc.py", "copy", q(card_backup), q(copied), src, name],
                    ["python", "SRC/save.py", "set", q(main_backup), q(new_main)]
                    + [editor.quote(assignment(*kv)) for kv in self.changes],
                    ["python", "SRC/ps2mc.py", "put", q(copied), q(path + ".new"),
                     editor.quote("%s/%s=%s" % (name, name, editor.shown_path(new_main)))]]
        self.log_card("%s -> %s on %s: %d changes" % (src, name, os.path.basename(path), n),
                      cmds)
        self.open_card(path, name, "Saved %s on %s: %d changes; %s is unchanged" % (
            name, editor.shown_path(path), n, src))
        return True

    def keep_changes(self):
        """False when the user cancels leaving unsaved changes."""
        if not self.changes:
            return True
        answer = messagebox.askyesnocancel("Unsaved changes", "Save the changes first?")
        return answer is not None and (not answer or self.write())

    def quit(self):
        if self.keep_changes():
            self.root.destroy()

    def run(self):
        self.root.mainloop()


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    if cmd == "open" and len(args) <= 2:
        if not os.path.isdir("DAT"):
            raise SystemExit("DAT: not found; run from the repo root")
        App(*args).run()
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
