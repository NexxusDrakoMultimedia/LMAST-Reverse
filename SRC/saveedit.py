# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Save editor for Let's Make a Soccer Team! (PS2): one window for one
career save on a PCSX2 folder memory card (DOC/SAVE_EDITOR_PLAN.md).

A save is a folder BESLES-54151-Gnnn (or -Mnnn for a modded disc's
saves) on the card. The window decodes it with save.py, which runs the
game's own save code (DOC/SAVE_FORMAT.md), and shows what save.py can
read, on one page each: the club, finances, the squad and youth team,
pair combinations, staff, the other clubs and the candidate lists.
Everything it shows comes from save.py's Save methods, so the window
keeps no layout of its own. Money shows in pounds (the stored unit / 6)
next to the stored value.

Edits go through save.apply_assigns, the function behind `save.py set`,
with the ranges from save.edit_spec; a value it refuses is put back. So
far the Club page edits money, the club status and the status rank; the
other pages only show (the plan's step 3 adds them page by page).

File > Save writes over the save's main file. First it copies the file
as it is to a backup folder beside the memory card, not in it (a folder
card shows the PS2 every folder in it):

    <card>.bak/<save folder>/<main file>.<date>-<time>.bak

and it logs the equivalent command in <card>.bak/saveedit.log, which
reads that backup and writes the same bytes:

    python SRC/save.py set <backup> <main file>.new money=... status=...

Close the game in PCSX2 before saving, so it doesn't write the card
over the edit.

Usage:
    python SRC/saveedit.py open [<save folder or main file>]
"""
import datetime
import os
import sys
import threading

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import editor
import initteam
import pbdata
import save

WINDOW = (1280, 720)
MES = os.path.join("DAT", "MESSAGE", "MES.PAC")
PBDATA = os.path.join("DAT", "PARAM", "PBDATA_EU.PAC")
GREY = "#555"
COMBI_COLOURS = ("#c8c8c8", "#e8e8e8", "#a8c8ff", "#ff9a9a", "#ff4a4a")    # levels 1-5


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
    title = ""

    def __init__(self, app):
        self.app = app
        self.frame = ttk.Frame(app.notebook)

    def fill(self, s, names):
        pass

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
            self.app.input(cell, key, refill=True).pack(side="left")
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
        plan = ttk.LabelFrame(top, text="Season plan")
        plan.pack(side="left", anchor="n", padx=(0, 12))
        rows = [(name, money(v) if name in save.PLAN_MONEY else format(v, ","))
                for name, v in s.plan()]
        rows.append(("stadium capacity", format(s.stadium_capacity(), ",")))
        rows += [("competition %#x ticket" % c, money(v)) for c, v in s.other_tickets()]
        grid_rows(plan, rows)
        ttk.Label(top, text="Amounts are in the save's money unit, with pounds (the unit / %d) "
                            "in brackets." % save.POUND, foreground=GREY,
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


class SquadPage(Page):
    title = "Squad"

    def fill(self, s, names):
        self.clear()
        self.s = s
        panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=6)
        left = ttk.Frame(panes)
        self.list = tree(left, ("slot", "id", "name", "pos", "age", "ability"),
                         ("Slot", "Id", "Name", "Pos", "Age", "Mean ability"),
                         (45, 55, 150, 50, 40, 85))
        self.list.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=1)
        self.detail = editor.Scrolled(panes)
        panes.add(self.detail.outer, weight=2)
        self.slots = dict(s.squad())
        for slot, o in s.squad():
            p = s.pinfo(o)
            lv = [save.exp2lv(s.exp, a[0]) for a in p["abil"]]
            self.list.insert("", "end", iid=slot, values=(
                slot, p["id"], p["name"], pbdata.position_name(p["pos"]), p["age"],
                round(sum(lv) / len(lv))))
        ttk.Label(self.detail.inner, text="Pick a player. Youth team slots start with y.",
                  foreground=GREY).pack(anchor="w", padx=8, pady=8)

    def select(self):
        sel = self.list.selection()
        if sel:
            self.show(sel[0])

    def show(self, slot):
        s, o = self.s, self.slots[slot]
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
            ("Condition", "fatigue %d/1000, condition %d%%, motivation %d%%, power %d/1000, "
                          "form %d/1000" % (p["fatigue"], p["condition"] * 100 // 65535,
                                            p["motivation"] * 100 // 65535, p["power"],
                                            p["form"])),
            ("Team fit, vision", "%d%%; %d%% towards counter, %d%% towards organisation" % (
                p["team_fit"], (p["policy_counter"] + 1) * 100 // 65536,
                (p["policy_organisation"] + 1) * 100 // 65536)),
            ("Injury", "kind %d, %d days" % (p["injury"], p["injury_days"])),
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
        lv = [save.exp2lv(s.exp, a[0]) for a in p["abil"]]
        ttk.Label(box, text="Bars  " + "   ".join("%s %d" % b for b in pbdata.bars(
            lv, p["position"] == 0))).pack(anchor="w", padx=8, pady=4)
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
        abil = ttk.LabelFrame(box, text="Abilities: level, growth limit, cap (0-99)")
        abil.pack(anchor="w", padx=8, pady=4)
        for k, (cur, mid, cap) in enumerate(p["abil"]):
            r, c = k % 16, (k // 16) * 2
            ttk.Label(abil, text="%d" % k, foreground=GREY).grid(row=r, column=c, sticky="e",
                                                                 padx=(10, 4))
            ttk.Label(abil, text="%2d  %2d  %2d" % (lv[k], save.exp2lv(s.exp, mid),
                                                  save.exp2lv(s.exp, cap))).grid(
                row=r, column=c + 1, sticky="w", padx=(0, 10))


class CombiPage(Page):
    title = "Combinations"

    def fill(self, s, names):
        self.clear()
        ttk.Label(self.frame, text="Pair combinations of the squad, as the tactics screen's "
                                   "icons: %s. Each cell is the pair's value (0-65535)." % ", ".join(
                                       "%d %s" % (i + 1, icon) for i, icon in
                                       enumerate(save.COMBI_ICONS)),
                  foreground=GREY, wraplength=1100, justify="left").pack(anchor="w", padx=8,
                                                                        pady=6)
        legend = ttk.Frame(self.frame)
        legend.pack(anchor="w", padx=8)
        for i, icon in enumerate(save.COMBI_ICONS):
            tk.Label(legend, text=" %s " % icon, bg=COMBI_COLOURS[i]).pack(side="left", padx=2)
        area = editor.Scrolled(self.frame)
        area.outer.pack(fill="both", expand=True, padx=6, pady=6)
        box = area.inner
        filled = [(int(i), s.pinfo(o)["name"]) for i, o in s.squad() if i.isdigit()]
        for c, (b, _) in enumerate(filled, 1):
            ttk.Label(box, text=str(b), foreground=GREY).grid(row=0, column=c)
        for r, (a, name) in enumerate(filled, 1):
            ttk.Label(box, text="%2d %s" % (a, name)).grid(row=r, column=0, sticky="w", padx=4)
            for c, (b, _) in enumerate(filled, 1):
                if a == b:
                    continue
                value, cap = s.combi(a, b)
                lv = save.combi_level(value)
                tk.Label(box, text=str(value), width=6, bg=COMBI_COLOURS[lv - 1],
                         font=("TkFixedFont", 8)).grid(row=r, column=c, padx=1, pady=1)


class StaffPage(Page):
    title = "Staff"

    def fill(self, s, names):
        self.clear()
        area = editor.Scrolled(self.frame)
        area.outer.pack(fill="both", expand=True, padx=6, pady=6)
        for role, i, st in s.staff():
            job = st["job"]
            title = "%s %d: %s (id %d)" % (role, i, st["name"], st["id"])
            box = ttk.LabelFrame(area.inner, text=title)
            box.pack(fill="x", padx=8, pady=4)
            rows = []
            if job is not None:
                rows.append(("Job", "%d %s" % (job, pbdata.JOB_NAMES[job]
                                                if job < len(pbdata.JOB_NAMES) else "?")))
            rows.append(("Contract", "%d year%s left, %s a year" % (
                st["contract_years"], "" if st["contract_years"] == 1 else "s",
                money(st["salary"] * 100))))
            if st["kind"] == "M":
                rows.append(("Dissatisfaction", ", ".join(
                    "%s %d" % kv for kv in zip(save.M_DISSAT_KINDS, st["dissat"]))))
                rows.append(("Popularity", "supporters %d, players %d%s" % (
                    st["pop_supporters"], st["pop_players"],
                    "; salary discount" if st["discount"] else "")))
            if job is None:
                bars = pbdata.average_bars(st["abil"], pbdata.SCOUT_BARS)
            else:
                bars = pbdata.staff_bars(st["abil"], pbdata.JOB_ROLE.get(job, "manager"))
            rows.append(("Bars", "   ".join("%s %d" % b for b in bars)))
            rows.append(("Abilities", " ".join(map(str, st["abil"]))))
            grid_rows(box, rows)


class ClubsPage(Page):
    title = "Other clubs"

    def fill(self, s, names):
        self.clear()
        self.s, self.names = s, names
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
        self.players = tree(bottom, ("slot", "id", "name", "age", "shirt", "years", "flags"),
                            ("Slot", "Id", "Player", "Age", "Shirt", "Contract", "Flags"),
                            (45, 60, 180, 45, 50, 70, 60), height=6)
        panes.add(bottom, weight=2)
        for team in [2] + list(range(3, save.CLUBS + 2)):
            c = s.club(team)
            self.list.insert("", "end", iid=str(team), values=(
                team, names.teams.get(team, ""), c["friendship"], c["rank"],
                names.reputation(c["rank"]), c["world_rank"], c["points"], c["league"],
                len(c["players"])))

    def select(self):
        sel = self.list.selection()
        if not sel:
            return
        self.players.delete(*self.players.get_children())
        for k, pid, age, shirt, years, flags in self.s.club(int(sel[0]))["players"]:
            self.players.insert("", "end", values=(
                k, pid, self.names.people.get(pid, "?"), age, "-" if shirt < 0 else shirt,
                years, "%#x" % flags if flags else ""))


class CandidatesPage(Page):
    title = "Candidates"

    def fill(self, s, names):
        self.clear()
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


def spec_range(s, key):
    """(low, high) save.edit_spec gives for a concrete key of save `s`."""
    for k, lo, hi, step, _ in save.edit_spec(s):
        if k == key:
            return lo, hi
    raise KeyError(key)


PAGES = (ClubPage, FinancesPage, SquadPage, CombiPage, StaffPage, ClubsPage, CandidatesPage)


# --- the window --------------------------------------------------------------

class App:
    def __init__(self, path=None):
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
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.write)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit)
        menu.add_cascade(label="File", menu=file_menu)
        self.root.configure(menu=menu)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind_all("<Control-o>", lambda e: self.ask_open())
        self.root.bind_all("<Control-s>", lambda e: self.write())
        self.changes = {}           # save.py set key -> value, in edit order
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken"
                  ).pack(fill="x", side="bottom")
        self.pages = [cls(self) for cls in PAGES]
        for page in self.pages:
            self.notebook.add(page.frame, text=page.title)
        self.game = self.names = self.save = None
        self.root.title("LMAST save editor")
        self.status("Open a save folder (BESLES-54151-G000 and so on) on a PCSX2 folder "
                    "memory card: File > Open save.")
        if path:
            self.open(path)

    def status(self, text):
        self.status_var.set(text)

    def ask_open(self):
        if not self.keep_changes():
            return
        path = filedialog.askdirectory(title="Open a save folder (BESLES-54151-...)",
                                       mustexist=True)
        if path:
            self.open(path)

    def open(self, path, done=None):
        """Decode the save (and the names, the first time) in a thread; the
        first decode of a session records save.py's field list."""
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
            self.loaded(result["save"], done)
        poll()

    def loaded(self, s, done=None):
        self.save = s
        self.changes = {}
        for page in self.pages:
            page.fill(s, self.names)
        self.update_title()
        self.status(done or "Opened %s." % editor.shown_path(s.path))

    def update_title(self):
        if self.save is None:
            return
        self.root.title("LMAST save editor - %s%s" % (
            editor.shown_path(self.save.path), "  (unsaved: %d changes)" % len(self.changes)
            if self.changes else ""))

    # edits

    def input(self, parent, key, refill=False):
        """A spin box for a save.py set key, its range from save.edit_spec.
        refill: redraw the pages after a change (values that follow it)."""
        lo, hi = spec_range(self.save, key)
        return editor.value_input(
            parent, ("range", lo, hi), str, lambda: self.value(key),
            lambda text, revert: self.commit(key, text, revert, refill))

    def value(self, key):
        """The current value of a key the inputs edit."""
        s = self.save
        if key == "money":
            return s.money
        srank, _, status, _ = s.status()
        return {"status": status, "status_rank": srank}[key]

    def commit(self, key, text, revert, refill=False):
        try:
            value = int(text)
        except ValueError:
            return self.refuse("%s must be a number" % key, revert)
        old = self.value(key)
        before = bytes(self.save.blocks)
        try:
            save.apply_assigns(self.save, ["%s=%d" % (key, value)])
        except ValueError as e:
            self.save.blocks[:] = before
            return self.refuse(str(e), revert)
        self.changes.pop(key, None)
        self.changes[key] = value
        if refill:
            # Redraw after the widget's own event has finished.
            self.root.after_idle(lambda: [page.fill(self.save, self.names)
                                          for page in self.pages])
        self.update_title()
        self.status("%s: %s -> %s" % (key, format(old, ","), format(value, ",")))
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
        cmd += ["%s=%d" % kv for kv in self.changes.items()]
        lines = editor.log_lines("%s: %d changes" % (os.path.basename(main), len(self.changes)),
                                 [cmd], [(new, main)], moved="the .new file")
        with open(os.path.join(os.path.dirname(folder), "saveedit.log"), "a",
                  encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")
        n = len(self.changes)
        self.open(main, "Saved %s: %d changes (backup %s)" % (
            editor.shown_path(main), n, editor.shown_path(backup)))
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
    if cmd == "open" and len(args) <= 1:
        if not os.path.isdir("DAT"):
            raise SystemExit("DAT: not found; run from the repo root")
        App(args[0] if args else None).run()
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
