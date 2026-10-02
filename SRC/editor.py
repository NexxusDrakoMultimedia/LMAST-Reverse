# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Mod editor for Let's Make a Soccer Team! (PS2): one window with a tab
per kind of data (stage 5 in GOALS.md).

Each tab edits through a writer in SRC/, using the same functions as that
writer's `set` command, and takes the fields' names and allowed values
from the writer (pbdata.edit_spec), so the editor keeps no layout of its
own. Fields with no name yet are shown read-only.

Edits are saved to a mod folder, each file under its path in DAT/, and
files from outside DATA.CVM under disc/:

    mod/PARAM/PBDATA_EU.PAC     an edited DAT/PARAM/PBDATA_EU.PAC
    mod/disc/SLES_541.51        an edited ISO/SLES_541.51
    mod/editor.log              the command line equivalent of every save

The editor reads a file from the mod folder when it is there and from
DAT/ (or ISO/) otherwise, so edits build up over several sessions. Each
save is written next to its target as <name>.new and then replaces it, so
a failed save leaves the old file. The folder's layout matches
patch_disc.py's targets: PARAM/PBDATA_EU.PAC=mod/PARAM/PBDATA_EU.PAC and
disc:SLES_541.51=mod/disc/SLES_541.51.

Tabs:
    People   players, managers and scouts (pbdata.py; DOC/PBDATA_FORMAT.md).
             A change to a player's rank, main position or nationality
             that changes the ranking (entries 2 and 3) also writes
             mod/disc/SLES_541.51, as `pbdata.py set --sles` does.

Usage:
    python SRC/editor.py open [<mod folder>] [--dat DAT] [--iso ISO]   # default: mod
"""
import contextlib
import datetime
import io
import os
import subprocess
import sys
import threading

import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk

import initteam
import pbdata

SLES = "SLES_541.51"
WINDOW = (1960, 1000)
LIST_MIN = 360            # the narrowest the list gets when a page needs room
BARS_PER_LINE = 8


# --- the mod folder ----------------------------------------------------------

def shown_path(path):
    """A path as the log gives it: relative to the current folder when it is
    inside it, with forward slashes."""
    rel = os.path.relpath(path)
    return (path if rel.startswith("..") else rel).replace("\\", "/")


class Mod:
    def __init__(self, root, dat="DAT", iso="ISO"):
        self.root, self.dat, self.iso = root, dat, iso

    def source(self, rel):
        """The file to read for DAT/<rel>: the mod's copy if there is one."""
        mine = os.path.join(self.root, rel)
        return mine if os.path.exists(mine) else os.path.join(self.dat, rel)

    def target(self, rel):
        return os.path.join(self.root, rel)

    def disc_source(self, name):
        mine = os.path.join(self.root, "disc", name)
        return mine if os.path.exists(mine) else os.path.join(self.iso, name)

    def disc_target(self, name):
        return os.path.join(self.root, "disc", name)

    def log(self, lines):
        os.makedirs(self.root, exist_ok=True)
        with open(os.path.join(self.root, "editor.log"), "a", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n\n")


def quote(arg):
    return subprocess.list2cmdline([arg])


# --- widgets -----------------------------------------------------------------

class Scrolled:
    """A frame inside a canvas with a vertical scroll bar."""
    def __init__(self, parent):
        self.outer = ttk.Frame(parent)
        self.canvas = tk.Canvas(self.outer, highlightthickness=0)
        bar = ttk.Scrollbar(self.outer, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(
            self.window, width=e.width))
        self.canvas.bind("<Enter>", lambda e: self.canvas.bind_all("<MouseWheel>", self._wheel))
        self.canvas.bind("<Leave>", lambda e: self.canvas.unbind_all("<MouseWheel>"))

    def _wheel(self, event):
        self.canvas.yview_scroll(-event.delta // 120, "units")

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.yview_moveto(0)


# --- tabs --------------------------------------------------------------------

class Tab:
    """One kind of data. A tab loads its files from the mod folder (or
    DAT/), keeps its edits in memory and writes them on save."""
    title = ""

    def __init__(self, app):
        self.app = app
        self.frame = ttk.Frame(app.notebook)

    def load(self):
        pass

    def dirty(self):
        return False

    def save(self):
        pass


PBDATA = "PARAM/PBDATA_EU.PAC"
OTEAM = "PARAM/OTEAMMEMBER.TBB"
MES = "MESSAGE/MES.PAC"
COMMON = "PARAM/PLRESOURCECOMMON.PAC"
KIND_TITLES = ("Players", "Managers", "Scouts")
LIST_LIMIT = 500

# How the People tab lays out each kind's fields. Fields not listed here
# go under "Other", so a newly named field in pbdata.py still shows.
GROUPS = {
    "players": (
        ("Basics", ("name", "nation", "age", "height", "weight", "leg", "shirt", "face",
                    "rank", "position", "req_status")),
        ("Personality and condition", (
            "tone", "dissatis", "professionalism", "pressure", "loyalty", "star",
            "moti_type", "cond_type", "potential", "growth", "travel", "injury_res",
            "recovery", "foul_avoid", "weak_foot", "policy", "adapt", "intelligence",
            "ball_touch", "dribble_style")),
        ("Play", ("style", "skills", "flags")),
        ("Kit style", ("sleeves", "wristband", "gloves", "gk_gloves", "gk_pants", "boots")),
        ("Abilities", ("ability",)),
    ),
    "managers": (
        ("Basics", ("name", "nation", "age", "job", "req_status", "real_name",
                    "model_pattern")),
        ("Policies", ("moti_type", "select_policy", "match_policy", "training_policy",
                      "rest_policy", "policy", "policy_range", "policy_best")),
        ("Tactics", ("formation", "attacking", "possession", "centre_side", "left_right",
                     "press_line", "press", "offside", "attack_pattern")),
        ("Drills (training menu items)", ("manager_drill", "coach_drill")),
        ("Abilities", ("ability",)),
    ),
    "scouts": (
        ("Basics", ("name", "nation", "age", "req_status", "real_name")),
        ("Special searches", ("search",)),
        ("Abilities", ("ability",)),
    ),
}
LABELS = {
    "req_status": "required status", "dissatis": "dissatisfaction", "star": "star quality",
    "moti_type": "motivation type", "cond_type": "condition type",
    "injury_res": "injury resistance", "foul_avoid": "foul avoidance",
    "adapt": "adaptability", "gk_gloves": "GK gloves", "gk_pants": "GK pants",
    "style": "play styles", "position": "positions", "real_name": "real name",
}
POSITION_ITEMS = ("main", "2nd", "3rd")


def bar_lines(title, bars):
    """Detail-screen bars, BARS_PER_LINE to a line, under a 13-column title."""
    cells = ["%-5s %2d" % b for b in bars]
    return ["%-13s%s" % (title if i == 0 else "", "  ".join(cells[i:i + BARS_PER_LINE]))
            for i in range(0, len(cells), BARS_PER_LINE)]


class PeopleTab(Tab):
    title = "People"

    def __init__(self, app):
        super().__init__(app)
        self.db = None
        self.records = None
        self.changes = {}           # (kind, index, "field[.i]") -> text, in edit order
        self.current = None         # the Record on the right
        self.widgets = []

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Show").pack(side="left")
        self.kind_var = tk.StringVar(value=KIND_TITLES[0])
        kind = ttk.Combobox(bar, textvariable=self.kind_var, values=KIND_TITLES,
                            state="readonly", width=10)
        kind.pack(side="left", padx=(4, 12))
        kind.bind("<<ComboboxSelected>>", lambda e: self.kind_changed())
        ttk.Label(bar, text="Name or id").pack(side="left")
        self.find_var = tk.StringVar()
        find = ttk.Entry(bar, textvariable=self.find_var, width=22)
        find.pack(side="left", padx=(4, 12))
        find.bind("<Return>", lambda e: self.refresh_list())
        ttk.Label(bar, text="Nationality").pack(side="left")
        self.nation_var = tk.StringVar(value="any")
        self.nation_box = ttk.Combobox(bar, textvariable=self.nation_var, state="readonly",
                                       width=20)
        self.nation_box.pack(side="left", padx=(4, 12))
        self.nation_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())
        self.club_label = ttk.Label(bar, text="Club")
        self.club_label.pack(side="left")
        self.club_var = tk.StringVar(value="any")
        self.club_box = ttk.Combobox(bar, textvariable=self.club_var, state="readonly",
                                     width=24)
        self.club_box.pack(side="left", padx=(4, 12))
        self.club_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())
        ttk.Button(bar, text="Search", command=self.refresh_list).pack(side="left")
        self.count_label = ttk.Label(bar, text="")
        self.count_label.pack(side="left", padx=12)

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("id", "name", "nation", "age", "what", "club")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("Id", "Name", "Nationality", "Age", "Position", "Club"),
                                  (60, 150, 110, 40, 90, 140)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, stretch=c in ("name", "club"))
        self.tree.tag_configure("edited", foreground="#b03000")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=2)
        self.detail = Scrolled(panes)
        panes.add(self.detail.outer, weight=3)

    # loading

    def load(self, done=None):
        """Read the database and the names in a thread; the window stays
        responsive while it takes a few seconds."""
        self.app.status("Loading the player database...")
        self.records = None
        self.tree.delete(*self.tree.get_children())
        self.frame.configure(cursor="watch")
        result = {}

        def work():
            try:
                mod = self.app.mod
                path = mod.source(PBDATA)
                db = pbdata.PbData(path)
                if not db.data:
                    raise ValueError("%s has no records" % path)
                result["records"] = {k: list(db.records(k)) for k in pbdata.KINDS}
                mes = mod.source(MES)
                # nation_names reads PLRESOURCECOMMON.PAC next to the path it
                # is given, so give it that pack's own path (the mod's copy of
                # PBDATA_EU.PAC may be on its own).
                result["nations"] = pbdata.nation_names(mod.source(COMMON), mes)
                teams = initteam.team_names(mes, 1)
                squads = initteam.OteamMembers(mod.source(OTEAM)).squads
                result["club_of"] = {m.player: (team, m) for team, s in squads.items() for m in s}
                result["teams"] = teams
                result["db"], result["path"] = db, path
            except Exception as e:      # shown in the window, not lost in a thread
                result["error"] = e

        thread = threading.Thread(target=work, daemon=True)
        thread.start()

        def poll():
            if thread.is_alive():
                self.frame.after(100, poll)
                return
            self.frame.configure(cursor="")
            if "error" in result:
                self.app.status("Couldn't load the player database: %s" % result["error"])
                messagebox.showerror("People", "Couldn't load the player database:\n%s"
                                     % result["error"])
                return
            self.loaded(result)
            if done:
                self.app.status(done)
        poll()

    def loaded(self, result):
        self.db, self.path = result["db"], result["path"]
        self.records, self.nations = result["records"], result["nations"]
        self.club_of, self.teams = result["club_of"], result["teams"]
        self.changes = {}
        self.nation_box["values"] = ["any"] + [pbdata.value_label("players", "nation", n, self.nations)
                                               for n in range(1, pbdata.NATION_COUNT + 1)]
        clubs = sorted({team for team, _ in self.club_of.values()})
        self.club_box["values"] = ["any"] + [self.team_label(t) for t in clubs]
        self.refresh_list()
        self.app.status("%s: %d players, %d managers, %d scouts" % (
            shown_path(self.path), *(len(self.records[k]) for k in pbdata.KINDS)))
        self.app.update_title()

    def team_label(self, team):
        return "%d %s" % (team, self.teams.get(team, ""))

    # the list

    @property
    def kind(self):
        return pbdata.KINDS[KIND_TITLES.index(self.kind_var.get())]

    def kind_changed(self):
        players = self.kind == "players"
        self.club_box.configure(state="readonly" if players else "disabled")
        if not players:
            self.club_var.set("any")
        self.tree.heading("what", text="Position" if players else
                          ("Job" if self.kind == "managers" else "Status"))
        self.refresh_list()

    def matches(self, r, find, nation, club):
        if find:
            if find.isdigit():
                if str(r.db_id) != find and str(r.index) != find:
                    return False
            elif find.lower() not in r.name.lower():
                return False
        if nation is not None and r.fields["nation"] != nation:
            return False
        if club is not None and self.club_of.get(r.index, (None,))[0] != club:
            return False
        return True

    def refresh_list(self):
        if self.records is None:
            return
        find = self.find_var.get().strip()
        nation = None if self.nation_var.get() == "any" else int(self.nation_var.get().split()[0])
        club = None if self.club_var.get() == "any" else int(self.club_var.get().split()[0])
        found = [r for r in self.records[self.kind] if self.matches(r, find, nation, club)]
        self.tree.delete(*self.tree.get_children())
        for r in found[:LIST_LIMIT]:
            self.tree.insert("", "end", iid=str(r.db_id), values=self.row(r),
                             tags=("edited",) if self.edited(r) else ())
        self.count_label.configure(text="%d found%s" % (
            len(found), ", showing the first %d" % LIST_LIMIT if len(found) > LIST_LIMIT else ""))

    def row(self, r):
        f = r.fields
        nation = self.nations.get(f["nation"], str(f["nation"]))
        if r.kind == "players":
            what = "/".join(pbdata.position_name(p) for p in f["position"] if p != 13)
            club = self.club_of.get(r.index)
            club = self.teams.get(club[0], str(club[0])) if club else ""
        elif r.kind == "managers":
            what, club = pbdata.listed(pbdata.JOB_NAMES, f["job"]), ""
        else:
            what, club = str(f["req_status"]), ""
        return (r.db_id, r.name, nation, f["age"], what, club)

    def edited(self, r):
        return r.encode() != r.raw

    # the detail panel

    def select(self):
        sel = self.tree.selection()
        if not sel:
            return
        kind, index = pbdata.parse_id(sel[0])
        self.show(self.records[kind][index])

    def show(self, r):
        self.current = r
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%d  %s" % (r.db_id, r.name), font=self.app.title_font
                  ).pack(anchor="w", padx=8, pady=(8, 2))
        for note in self.notes(r):
            ttk.Label(box, text=note, foreground="#555", wraplength=560, justify="left"
                      ).pack(anchor="w", padx=8)
        listed = set()
        groups = list(GROUPS[r.kind])
        for _, names in groups:
            listed.update(names)
        other = tuple(f[0] for f in pbdata.FIELDS[r.kind] if f[0] not in listed)
        if other:
            groups.append(("Other (fields with no name yet are read-only)", other))
        for title, names in groups:
            frame = ttk.LabelFrame(box, text=title)
            frame.pack(fill="x", padx=8, pady=6)
            if names == ("ability",):
                self.ability_grid(frame, r)
            else:
                for row, fname in enumerate(names):
                    self.field_row(frame, r, fname, row)
        self.derived = ttk.Label(box, text="", justify="left", font="TkFixedFont")
        self.derived.pack(anchor="w", padx=8, pady=(4, 12))
        self.update_derived()
        self.fit_detail()

    def fit_detail(self):
        """Move the divider left when the page is wider than its pane, down
        to LIST_MIN for the list. Dragging it back is up to the user."""
        self.frame.update_idletasks()
        need = self.detail.inner.winfo_reqwidth() + 24     # and the scroll bar
        have = self.detail.outer.winfo_width()
        if need > have > 1:
            pos = self.panes.sashpos(0)
            self.panes.sashpos(0, max(LIST_MIN, pos - (need - have)))

    def notes(self, r):
        out = []
        if r.kind == "players":
            club = self.club_of.get(r.index)
            if club:
                team, m = club
                out.append("In %s's squad (OTEAMMEMBER.TBB): the game shows the age %d and "
                           "shirt %d from there, not the age and shirt below "
                           "(DOC/INITTEAM_FORMAT.md)." % (self.team_label(team), m.age, m.shirt))
            if r.index < pbdata.RANKED:
                out.append("Rank, main position and nationality decide this player's place in "
                           "the ranking. Saving a change to them re-sorts it and writes "
                           "disc/SLES_541.51 too (DOC/PBDATA_FORMAT.md#entries-2-and-3).")
        return out

    def field_row(self, frame, r, fname, row):
        text = LABELS.get(fname, fname.replace("_", " "))
        ttk.Label(frame, text=text).grid(row=row, column=0, sticky="nw", padx=(6, 12), pady=2)
        cell = ttk.Frame(frame)
        cell.grid(row=row, column=1, sticky="w", pady=2)
        if fname == "name":
            self.name_entry(cell, r)
            return
        _, _, _, count, _ = pbdata.field_spec(r.kind, fname)
        if count == 1:
            self.value_widget(cell, r, fname, None).pack(side="left")
            return
        for i in range(count):
            label = POSITION_ITEMS[i] if fname == "position" else pbdata.item_label(r.kind, fname, i)
            item = ttk.Frame(cell)
            item.grid(row=i // 4 if count > 5 else 0, column=i % 4 if count > 5 else i,
                      sticky="w", padx=(0, 10))
            ttk.Label(item, text=label, foreground="#555").pack(side="left", padx=(0, 4))
            self.value_widget(item, r, fname, i).pack(side="left")

    def ability_grid(self, frame, r):
        values = r.fields["ability"]
        cols = 4
        for i in range(len(values)):
            item = ttk.Frame(frame)
            item.grid(row=i // cols, column=i % cols, sticky="e", padx=(6, 10), pady=1)
            ttk.Label(item, text="%d %s" % (i, pbdata.item_label(r.kind, "ability", i))
                      ).pack(side="left", padx=(0, 4))
            self.value_widget(item, r, "ability", i).pack(side="left")

    def name_entry(self, cell, r):
        var = tk.StringVar(value=r.name)
        entry = ttk.Entry(cell, textvariable=var, width=22)
        entry.pack(side="left")
        ttk.Label(cell, text="up to %d characters" % (pbdata.NAME_LEN - 1),
                  foreground="#555").pack(side="left", padx=6)

        def commit(event=None):
            if var.get() != r.name:
                self.commit(r, "name", None, var.get(), lambda: var.set(r.name))
        entry.bind("<Return>", commit)
        entry.bind("<FocusOut>", commit)

    def value_widget(self, parent, r, fname, index):
        """The widget for one value: a drop-down for listed values, a spin
        box for a range, check boxes for a bit mask, a label if read-only."""
        spec = pbdata.edit_spec(r.kind, fname)
        current = r.fields[fname] if index is None else r.fields[fname][index]
        if spec is None:
            return ttk.Label(parent, text=str(current), foreground="#777")
        if spec[0] == "bits":
            return self.bit_boxes(parent, r, fname)
        var = tk.StringVar()

        def get():
            return r.fields[fname] if index is None else r.fields[fname][index]

        def commit(event=None):
            text = var.get().split()[0] if var.get().strip() else ""
            if text != str(get()):
                self.commit(r, fname, index, text, lambda: var.set(label(get())))

        if spec[0] == "choice":
            def label(v):
                return pbdata.value_label(r.kind, fname, v, self.nations)
            values = [label(v) for v in spec[1]]
            width = max(4, min(26, max(len(v) for v in values) + 1))
            w = ttk.Combobox(parent, textvariable=var, values=values, state="readonly",
                             width=width, height=20)
            w.bind("<<ComboboxSelected>>", commit)
        else:
            def label(v):
                return pbdata.value_label(r.kind, fname, v)
            lo, hi = spec[1], spec[2]
            w = ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=1,
                            width=max(4, len(str(hi)) + 2), command=commit)
            w.bind("<Return>", commit)
            w.bind("<FocusOut>", commit)
        var.set(label(current))
        return w

    def bit_boxes(self, parent, r, fname):
        frame = ttk.Frame(parent)
        bits = []

        def revert():
            for b, v in enumerate(bits):
                v.set(r.fields[fname] >> b & 1)

        def commit():
            mask = sum(1 << b for b, v in enumerate(bits) if v.get())
            self.commit(r, fname, None, str(mask), revert)
        for b, name in enumerate(pbdata.SKILLS):
            v = tk.IntVar(value=r.fields[fname] >> b & 1)
            bits.append(v)
            ttk.Checkbutton(frame, text=name, variable=v, command=commit).grid(
                row=b // 4, column=b % 4, sticky="w", padx=(0, 10))
        return frame

    def commit(self, r, fname, index, text, revert):
        """Apply one edit with pbdata.apply_value, as `pbdata.py set` does.
        A refused value is put back with revert() before the error shows, so
        the dialog taking the focus can't commit it again."""
        if fname != "name":
            try:
                text = str(int(text))       # "08" -> "8"; apply_value reads base 0
            except ValueError:
                pass
        try:
            old, new = pbdata.apply_value(r, fname, index, text)
        except ValueError as e:
            revert()
            self.app.status("%d %s: %s" % (r.db_id, r.name, e))
            messagebox.showerror("People", "%d %s: %s" % (r.db_id, r.name, e))
            return False
        key = fname if index is None else "%s.%d" % (fname, index)
        self.changes.pop((r.kind, r.index, key), None)      # keep edit order
        self.changes[r.kind, r.index, key] = text
        self.app.status("%d %s: %s %s -> %s" % (r.db_id, r.name, key, old, new))
        iid = str(r.db_id)
        if self.tree.exists(iid):
            self.tree.item(iid, values=self.row(r), tags=("edited",) if self.edited(r) else ())
        if fname == "name":
            self.show(r)
        else:
            self.update_derived()
        self.app.update_title()
        return True

    def update_derived(self):
        r = self.current
        if r is None:
            return
        ab = r.fields["ability"]
        if r.kind == "players":
            gk = r.fields["position"][0] == 0
            lines = bar_lines("Screen bars", pbdata.bars(ab, gk))
            lines += ["Positions    " + pbdata.aptitude_grid(
                          pbdata.aptitude(ab, r.fields["position"])[1]),
                      "             (levels 0-4, forwards first, left centre right)"]
        elif r.kind == "managers":
            role = pbdata.JOB_ROLE.get(r.fields["job"], "manager")
            lines = ["Screen bars as %s" % role] + bar_lines(
                "", pbdata.staff_bars(ab, role))
        else:
            lines = bar_lines("Screen bars", pbdata.average_bars(ab, pbdata.SCOUT_BARS))
        self.derived.configure(text="\n".join(lines))

    # saving

    def dirty(self):
        return bool(self.changes)

    def save(self):
        """Write the edited pack to the mod folder, and the executable too
        when the ranking changes. Returns False if nothing was written."""
        if not self.changes:
            return True
        mod = self.app.mod
        players = self.records["players"]
        out = mod.target(PBDATA)
        # The ranking changes when a rank, main position or nationality edit
        # moves a player or changes a group's size; either way the pack's
        # entries 2 and 3 and the executable's group table must follow.
        sles = None
        sles_in = mod.disc_source(SLES)
        try:
            entry2, _, table = pbdata.build_ranking(players, self.db.entry2)
            if entry2 != self.db.entry2 or table != pbdata.sles_group_table(sles_in)[1]:
                sles = (sles_in, mod.disc_target(SLES))
        except (ValueError, OSError) as e:
            messagebox.showerror("People", "Can't save: %s" % e)
            return False
        os.makedirs(os.path.dirname(out), exist_ok=True)
        if sles:
            os.makedirs(os.path.dirname(sles[1]), exist_ok=True)
        temps = [(out + ".new", out)] + ([(sles[1] + ".new", sles[1])] if sles else [])
        report = io.StringIO()
        try:
            with contextlib.redirect_stdout(report):
                pbdata.write_pack(temps[0][0], self.db, self.records,
                                  (sles[0], temps[1][0]) if sles else None)
        except (SystemExit, ValueError, OSError) as e:
            for tmp, _ in temps:
                if os.path.exists(tmp):
                    os.remove(tmp)
            messagebox.showerror("People", "Can't save: %s" % e)
            return False
        for tmp, final in temps:
            os.replace(tmp, final)

        args = []
        last = None
        for (kind, index, key), text in self.changes.items():
            r = self.records[kind][index]
            if (kind, index) != last:
                args.append(str(r.db_id))
                last = (kind, index)
            args.append(quote("%s=%s" % (key, text)))
        records = len({(k, i) for k, i, _ in self.changes})
        cmd = ["python", "SRC/pbdata.py", "set", quote(shown_path(self.path)),
               quote(shown_path(temps[0][0]))] + args
        if sles:
            cmd += ["--sles", quote(shown_path(sles[0])), quote(shown_path(temps[1][0]))]
        lines = ["# %s  People: %d changes in %d records" % (
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), len(self.changes), records),
                 " ".join(cmd),
                 "# then each .new file replaces %s" % ", ".join(shown_path(f) for _, f in temps)]
        lines += ["# " + line for line in report.getvalue().splitlines()]
        mod.log(lines)
        self.app.write_log(lines)
        done = "Saved %s%s: %d changes in %d records" % (
            shown_path(out), " and " + shown_path(sles[1]) if sles else "",
            len(self.changes), records)
        # Read the saved pack back: its entries 2 and 3 are the base for the
        # next save, and a bad write shows here rather than in the game.
        self.changes = {}
        self.current = None
        self.detail.clear()
        self.load(done)
        return True


class LogTab(Tab):
    """The commands each save corresponds to, as written to editor.log."""
    title = "Log"

    def __init__(self, app):
        super().__init__(app)
        self.text = tk.Text(self.frame, wrap="none", font="TkFixedFont", height=10)
        sb = ttk.Scrollbar(self.frame, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set, state="disabled")
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

    def write(self, lines):
        self.text.configure(state="normal")
        self.text.insert("end", "\n".join(lines) + "\n\n")
        self.text.see("end")
        self.text.configure(state="disabled")


# --- the window --------------------------------------------------------------

class App:
    def __init__(self, mod):
        self.mod = mod
        try:        # sharp text on Windows with display scaling
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (ImportError, AttributeError, OSError):
            pass
        self.root = tk.Tk()
        self.title_font = tkfont.nametofont("TkDefaultFont").copy()
        self.title_font.configure(size=12, weight="bold")
        # Wide enough for the list and a page of four ability columns
        # (about 1,900 pixels), or the screen less a margin.
        w = min(WINDOW[0], self.root.winfo_screenwidth() - 80)
        h = min(WINDOW[1], self.root.winfo_screenheight() - 120)
        self.root.geometry("%dx%d+%d+%d" % (w, h, (self.root.winfo_screenwidth() - w) // 2,
                                            (self.root.winfo_screenheight() - h) // 3))
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save)
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit)
        menu.add_cascade(label="File", menu=file_menu)
        self.root.configure(menu=menu)
        self.root.bind_all("<Control-s>", lambda e: self.save())
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken"
                  ).pack(fill="x", side="bottom")
        self.tabs = [PeopleTab(self)]
        self.log_tab = LogTab(self)
        for tab in self.tabs + [self.log_tab]:
            self.notebook.add(tab.frame, text=tab.title)
        self.update_title()
        for tab in self.tabs:
            tab.load()

    def status(self, text):
        self.status_var.set(text)

    def write_log(self, lines):
        self.log_tab.write(lines)

    def update_title(self):
        dirty = [t.title for t in self.tabs if t.dirty()]
        for i, tab in enumerate(self.tabs):
            self.notebook.tab(i, text=tab.title + (" *" if tab.dirty() else ""))
        self.root.title("LMAST mod editor - %s%s" % (
            shown_path(os.path.abspath(self.mod.root)), "  (unsaved: %s)" % ", ".join(dirty)
            if dirty else ""))

    def save(self):
        ok = all([tab.save() for tab in self.tabs if tab.dirty()])
        self.update_title()
        return ok

    def quit(self):
        if any(t.dirty() for t in self.tabs):
            answer = messagebox.askyesnocancel("Unsaved changes",
                                               "Save the changes before closing?")
            if answer is None or (answer and not self.save()):
                return
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def _opt(args, flag, default=None):
    if flag in args:
        i = args.index(flag)
        value = args[i + 1]
        del args[i:i + 2]
        return value
    return default


def main(argv):
    args = argv[2:]
    cmd = argv[1] if len(argv) > 1 else ""
    dat = _opt(args, "--dat", "DAT")
    iso = _opt(args, "--iso", "ISO")
    if cmd == "open" and len(args) <= 1:
        if not os.path.isdir(dat):
            raise SystemExit("%s: not found; run from the repo root or give --dat" % dat)
        App(Mod(args[0] if args else "mod", dat, iso)).run()
        return 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
