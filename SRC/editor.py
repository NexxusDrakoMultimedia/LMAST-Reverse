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
    mod/build.json              the Build disc dialog's paths and options

The editor reads a file from the mod folder when it is there and from
DAT/ (or ISO/) otherwise, so edits build up over several sessions. Each
save is written next to its target as <name>.new and then replaces it, so
a failed save leaves the old file. The folder's layout matches
patch_disc.py's targets: PARAM/PBDATA_EU.PAC=mod/PARAM/PBDATA_EU.PAC and
disc:SLES_541.51=mod/disc/SLES_541.51.

File > Build disc (Ctrl+B) writes a modded disc image, an xdelta patch,
or both: `patch_disc.py patch ... --copies` puts the mod folder on a copy
of the original, and `vcdiff.py make` compares the two. For a patch on
its own that image is temporary (<patch>.building.iso, removed after).
It shows their output and logs both commands. The original must be the Redump dump
for a patch others can apply.

Tabs:
    People   players, managers and scouts (pbdata.py; DOC/PBDATA_FORMAT.md).
             A change to a player's rank, main position or nationality
             that changes the ranking (entries 2 and 3) also writes
             mod/disc/SLES_541.51, as `pbdata.py set --sles` does.
    Clubs    club records (PLRESOURCESIM.PAC entry 3) and the computer
             teams' squads (OTEAMMEMBER.TBB), through initteam.py
             (DOC/INITTEAM_FORMAT.md). Refuses a player already in another
             squad, a shirt number twice in one squad, and a manager who
             already has a club, which `initteam.py info` would flag.
    New club the player's new club by league and team style
             (TEAM_INIT_DATA.TBB, teaminit.py; DOC/TEAMINIT_FORMAT.md):
             squad, rival-only records, staff, scouts, youth team,
             candidate lists and the rival club, as pwkTeam_Init2 reads them.
    Kits     every club's home and away kits (UNIFORM_LIST.TBB) and the
             keeper kits made from the outfield kit for your club, the rival
             and the VS teams (UNIFORM_GK.TBB), through uniform.py
             (DOC/UNIFORM_FORMAT.md). Colours show as swatches.

Usage:
    python SRC/editor.py open [<mod folder>] [--dat DAT] [--iso ISO]   # default: mod
"""
import contextlib
import datetime
import io
import os
import struct
import subprocess
import sys
import threading

import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk

import initteam
import pbdata
import teaminit
import uniform

SLES = "SLES_541.51"
MOD_OWN_FILES = ("editor.log", "build.json")    # the editor's files, not the game's
WINDOW = (1280, 720)
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

    def targets(self):
        """[(patch_disc.py target, file)] for every edited file in the
        folder: <path under DAT>=file, and disc:<name>=file for disc/."""
        out = []
        for folder, dirs, files in os.walk(self.root):
            dirs.sort()
            rel_dir = os.path.relpath(folder, self.root).replace("\\", "/")
            for name in sorted(files):
                if (rel_dir == "." and name in MOD_OWN_FILES) or name.endswith(".new"):
                    continue
                rel = name if rel_dir == "." else rel_dir + "/" + name
                path = os.path.join(folder, name)
                if rel.startswith("disc/"):
                    out.append(("disc:" + rel[len("disc/"):], path))
                else:
                    out.append((rel, path))
        return out


def quote(arg):
    return subprocess.list2cmdline([arg])


# --- widgets -----------------------------------------------------------------

class Scrolled:
    """A frame inside a canvas with scroll bars. The frame fills the canvas's
    width, or keeps its own when it is wider; then the horizontal bar
    scrolls it (or Shift and the mouse wheel)."""
    def __init__(self, parent):
        self.outer = ttk.Frame(parent)
        self.canvas = tk.Canvas(self.outer, highlightthickness=0)
        vbar = ttk.Scrollbar(self.outer, orient="vertical", command=self.canvas.yview)
        hbar = ttk.Scrollbar(self.outer, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)
        self.outer.rowconfigure(0, weight=1)
        self.outer.columnconfigure(0, weight=1)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vbar.grid(row=0, column=1, sticky="ns")
        hbar.grid(row=1, column=0, sticky="ew")
        self.inner = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self._fit())
        self.canvas.bind("<Configure>", lambda e: self._fit())
        self.canvas.bind("<Enter>", lambda e: self._bind_wheel(True))
        self.canvas.bind("<Leave>", lambda e: self._bind_wheel(False))

    def _fit(self):
        width = max(self.canvas.winfo_width(), self.inner.winfo_reqwidth())
        self.canvas.itemconfigure(self.window, width=width)
        self.canvas.configure(scrollregion=(0, 0, width, self.inner.winfo_reqheight()))

    def _bind_wheel(self, on):
        for seq, fn in (("<MouseWheel>", self._wheel), ("<Shift-MouseWheel>", self._hwheel)):
            if on:
                self.canvas.bind_all(seq, fn)
            else:
                self.canvas.unbind_all(seq)

    def _wheel(self, event):
        self.canvas.yview_scroll(-event.delta // 120, "units")

    def _hwheel(self, event):
        self.canvas.xview_scroll(-event.delta // 120, "units")

    def clear(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)


def value_input(parent, spec, label, get, apply):
    """A drop-down for ("choice", [values]) or a spin box for ("range",
    low, high). label(v) is a value's text, get() the current value, and
    apply(text, revert) is called with the new value's text when it
    changes; it calls revert() to put the old value back."""
    var = tk.StringVar()
    values = [label(v) for v in spec[1]] if spec[0] == "choice" else None

    def commit(event=None):
        if values is not None and var.get() in values:
            # A drop-down entry stands for its value, whatever its label
            # looks like ("A4 red 4" is colour 3).
            text = str(spec[1][values.index(var.get())])
        else:
            text = var.get().split()[0] if var.get().strip() else ""
        if text != str(get()):
            apply(text, lambda: var.set(label(get())))

    if spec[0] == "choice":
        width = max(4, min(30, max(len(v) for v in values) + 1))
        w = ttk.Combobox(parent, textvariable=var, values=values, state="readonly",
                         width=width, height=20)
        w.bind("<<ComboboxSelected>>", commit)
    else:
        lo, hi = spec[1], spec[2]
        w = ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=1,
                        width=max(4, len(str(hi)) + 2), command=commit)
        w.bind("<Return>", commit)
        w.bind("<FocusOut>", commit)
    var.set(label(get()))
    return w


def replace_new(temps):
    """Move each written <file>.new over its target."""
    for tmp, final in temps:
        os.replace(tmp, final)


def remove_new(temps):
    """Remove the .new files of a save that failed."""
    for tmp, _ in temps:
        if os.path.exists(tmp):
            os.remove(tmp)


def log_lines(title, commands, temps, report=""):
    """The editor.log entry for one save."""
    lines = ["# %s  %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), title)]
    lines += [" ".join(c) for c in commands]
    lines.append("# then each .new file replaces %s" % ", ".join(shown_path(f) for _, f in temps))
    lines += ["# " + line for line in report.splitlines()]
    return lines


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

    def changed(self, what):
        """Another tab saved or loaded something this one shows: "squads"
        (OTEAMMEMBER.TBB) or "people" (the People tab's records)."""
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
        self.app.notify(self, "people")

    def changed(self, what):
        """The Clubs tab saved the squads: refresh which club each player
        is in, for the list, the club filter and the notes."""
        if what != "squads" or self.records is None:
            return
        squads = initteam.OteamMembers(self.app.mod.source(OTEAM)).squads
        self.club_of = {m.player: (team, m) for team, s in squads.items() for m in s}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)

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

        def get():
            return r.fields[fname] if index is None else r.fields[fname][index]
        if spec is None:
            return ttk.Label(parent, text=str(get()), foreground="#777")
        if spec[0] == "bits":
            return self.bit_boxes(parent, r, fname)
        return value_input(parent, spec,
                           lambda v: pbdata.value_label(r.kind, fname, v, self.nations), get,
                           lambda text, revert: self.commit(r, fname, index, text, revert))

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
            remove_new(temps)
            messagebox.showerror("People", "Can't save: %s" % e)
            return False
        replace_new(temps)

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
        lines = log_lines("People: %d changes in %d records" % (len(self.changes), records),
                          [cmd], temps, report.getvalue())
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


SIMPAC = "PARAM/PLRESOURCESIM.PAC"
STADIUMS = "PARAM/STADIUM_DATA.TBB"
TEAM_LABELS = {
    "world_rank": "world rank points", "foreign": "foreign players (policy row)",
    "newface": "new faces (policy)", "search_region": "search region (policy row)",
    "money": "transfer money factor", "list_state": "listed under state",
    "list_city": "listed under city",
}
SQUAD_FIELDS = ("player", "age", "shirt", "contract")


class ClubsTab(Tab):
    """Club records (PLRESOURCESIM.PAC entry 3) and computer-team squads
    (OTEAMMEMBER.TBB), through initteam.py's set_team_field and set_member,
    as `initteam.py setteam` and `set` do."""
    title = "Clubs"

    def __init__(self, app):
        super().__init__(app)
        self.ot = self.db = None
        self.squad_changes = {}     # (team, slot, field) -> value, in edit order
        self.team_changes = {}      # (team, field) -> value
        self.current = None         # the team on the right

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Name or id").pack(side="left")
        self.find_var = tk.StringVar()
        find = ttk.Entry(bar, textvariable=self.find_var, width=22)
        find.pack(side="left", padx=(4, 12))
        find.bind("<Return>", lambda e: self.refresh_list())
        ttk.Button(bar, text="Search", command=self.refresh_list).pack(side="left")
        self.count_label = ttk.Label(bar, text="")
        self.count_label.pack(side="left", padx=12)

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("id", "name", "rank", "world", "squad")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("Id", "Club", "Rank", "World pts", "Squad"),
                                  (50, 170, 50, 70, 50)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, stretch=c == "name")
        self.tree.tag_configure("edited", foreground="#b03000")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=1)
        self.detail = Scrolled(panes)
        panes.add(self.detail.outer, weight=3)

    # loading

    def load(self, done=None):
        mod = self.app.mod
        try:
            self.ot_path, self.db_path = mod.source(OTEAM), mod.source(SIMPAC)
            self.ot = initteam.OteamMembers(self.ot_path)
            self.db = initteam.TeamDb(self.db_path)
            mes = mod.source(MES)
            self.teams = initteam.team_names(mes, 1)
            self.names = {cat: initteam.category_names(mes, cat)
                          for cat in set(initteam.TEAM_NAME_CATEGORIES.values())}
            self.stadiums = initteam.StadiumData(mod.source(STADIUMS))
        except (ValueError, struct.error, OSError, SystemExit) as e:
            self.app.status("Couldn't load the clubs: %s" % e)
            messagebox.showerror("Clubs", "Couldn't load the clubs:\n%s" % e)
            return
        self.squad_changes, self.team_changes = {}, {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    def changed(self, what):
        if what == "people" and self.current is not None and self.db is not None:
            self.show(self.current)         # the squad's names come from People

    def people(self, kind):
        """The People tab's records, edits included, or None while it loads."""
        records = self.app.people.records
        return records[kind] if records else None

    # the list

    def refresh_list(self):
        if self.db is None:
            return
        find = self.find_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        n = 0
        for team in sorted(self.db.records):
            name = self.teams.get(team, "")
            if find and not (find == str(team) or (not find.isdigit() and find in name.lower())):
                continue
            self.tree.insert("", "end", iid=str(team), values=self.row(team),
                             tags=("edited",) if self.edited(team) else ())
            n += 1
        self.count_label.configure(text="%d clubs" % n)

    def row(self, team):
        r = self.db.records[team]
        return (team, self.teams.get(team, ""), r["rank"], r["world_rank"],
                "yes" if team in self.ot.squads else "no")

    def edited(self, team):
        return (any(t == team for t, _ in self.team_changes)
                or any(t == team for t, _, _ in self.squad_changes))

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    # the detail panel

    def show(self, team):
        self.current = team
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%d  %s" % (team, self.teams.get(team, "")),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        frame = ttk.LabelFrame(box, text="Club record (PLRESOURCESIM.PAC entry 3; "
                                         "fields with no name yet are read-only)")
        frame.pack(fill="x", padx=8, pady=6)
        record = self.db.records[team]
        for row, (name, _, _, _) in enumerate(initteam.TEAM_FIELDS):
            ttk.Label(frame, text=TEAM_LABELS.get(name, name.replace("_", " "))).grid(
                row=row, column=0, sticky="w", padx=(6, 12), pady=2)
            self.team_widget(frame, team, record, name).grid(row=row, column=1, sticky="w", pady=2)
        frame = ttk.LabelFrame(box, text="Squad (OTEAMMEMBER.TBB)")
        frame.pack(fill="x", padx=8, pady=6)
        if team not in self.ot.squads:
            ttk.Label(frame, text="No squad in OTEAMMEMBER.TBB: only teams %d-%d have one "
                                  "(DOC/INITTEAM_FORMAT.md)." % (initteam.OTEAM_FIRST,
                                                                 initteam.OTEAM_END - 1),
                      foreground="#555").pack(anchor="w", padx=6, pady=4)
        else:
            self.squad_grid(frame, team)
        self.fit_detail()

    def fit_detail(self):
        self.frame.update_idletasks()
        need = self.detail.inner.winfo_reqwidth() + 24
        have = self.detail.outer.winfo_width()
        if need > have > 1:
            pos = self.panes.sashpos(0)
            self.panes.sashpos(0, max(LIST_MIN, pos - (need - have)))

    def team_widget(self, parent, team, record, name):
        rng = initteam.team_edit_range(name)
        if rng is None:
            return ttk.Label(parent, text=str(record[name]), foreground="#777")
        if name == "manager":
            managers = self.people("managers")
            spec = ("choice", list(range(rng[0], rng[1] + 1)))

            def label(v):
                return "%d %s" % (v, managers[v].name) if managers and 0 <= v < len(managers) \
                    else str(v)
        elif name == "stadium":
            spec = ("choice", list(range(rng[0], rng[1] + 1)))

            def label(v):
                if not 0 <= v < len(self.stadiums.rows):
                    return str(v)
                return "%d  %d seats%s" % (v, self.stadiums.capacity(v),
                                           ", roof" if self.stadiums.rows[v][0] else "")
        elif name in initteam.TEAM_NAME_CATEGORIES:
            names = self.names[initteam.TEAM_NAME_CATEGORIES[name]]
            spec = ("choice", sorted(set(names) | {record[name]}))

            def label(v):
                return "%d %s" % (v, names[v]) if v in names else str(v)
        else:
            spec = ("range",) + rng

            def label(v):
                return str(v)
        return value_input(parent, spec, label, lambda: record[name],
                           lambda text, revert: self.commit_team(team, name, text, revert))

    def squad_grid(self, frame, team):
        players = self.people("players")
        for col, text in enumerate(("slot", "player", "name", "position", "age", "shirt",
                                    "contract years")):
            ttk.Label(frame, text=text, foreground="#555").grid(row=0, column=col, sticky="w",
                                                               padx=(6, 8))
        for slot, m in enumerate(self.ot.squads[team]):
            row = slot + 1
            ttk.Label(frame, text=str(slot)).grid(row=row, column=0, sticky="w", padx=(6, 8))
            name = ttk.Label(frame, text="")
            pos = ttk.Label(frame, text="")

            def describe(m=m, name=name, pos=pos):
                if players and 0 <= m.player < len(players):
                    r = players[m.player]
                    name.configure(text=r.name)
                    pos.configure(text="/".join(pbdata.position_name(p)
                                                for p in r.fields["position"] if p != 13))
                else:
                    name.configure(text="(names load with People)" if players is None else "?")
            describe()
            for col, field in ((1, "player"), (4, "age"), (5, "shirt"), (6, "contract")):
                lo, hi = initteam.SQUAD_EDIT_RANGES.get(field, initteam.SET_LIMITS[field])
                if field == "player" and players:
                    hi = len(players) - 1
                w = value_input(frame, ("range", lo, hi), str,
                                lambda m=m, field=field: getattr(m, field),
                                lambda text, revert, slot=slot, field=field, d=describe:
                                    self.commit_squad(team, slot, field, text, revert, d))
                w.grid(row=row, column=col, sticky="w", padx=(0, 8), pady=1)
            name.grid(row=row, column=2, sticky="w", padx=(0, 8))
            pos.grid(row=row, column=3, sticky="w", padx=(0, 8))
        ttk.Label(frame, text="A new game shows each age one year older. The game takes these "
                              "players' age and shirt from here, not from the player database.",
                  foreground="#555").grid(row=len(self.ot.squads[team]) + 1, column=0,
                                          columnspan=7, sticky="w", padx=6, pady=(6, 4))

    # edits

    def refuse(self, what, message, revert):
        revert()
        self.app.status("%s: %s" % (what, message))
        messagebox.showerror("Clubs", "%s: %s" % (what, message))
        return False

    def commit_team(self, team, name, text, revert):
        what = "%d %s" % (team, self.teams.get(team, ""))
        try:
            value = int(text)
        except ValueError:
            return self.refuse(what, "%s must be a number" % name, revert)
        lo, hi = initteam.team_edit_range(name)
        if not lo <= value <= hi:
            return self.refuse(what, "%s must be %d-%d" % (name, lo, hi), revert)
        if name == "manager":
            # Every club has its own manager (initteam.py info checks it).
            other = next((t for t, r in self.db.records.items()
                          if t != team and r["manager"] == value), None)
            if other is not None:
                return self.refuse(what, "manager %d already manages %d %s" % (
                    value, other, self.teams.get(other, "")), revert)
        try:
            old = initteam.set_team_field(self.db.records[team], name, value)
        except ValueError as e:
            return self.refuse(what, str(e), revert)
        self.team_changes.pop((team, name), None)
        self.team_changes[team, name] = value
        self.edited_one(team, "%s: %s %s -> %s" % (what, name, old, value))
        return True

    def commit_squad(self, team, slot, field, text, revert, describe):
        what = "%d %s slot %d" % (team, self.teams.get(team, ""), slot)
        try:
            value = int(text)
        except ValueError:
            return self.refuse(what, "%s must be a number" % field, revert)
        players = self.people("players")
        if field == "player" and players and not 0 <= value < len(players):
            return self.refuse(what, "players are 0-%d" % (len(players) - 1), revert)
        if field in initteam.SQUAD_EDIT_RANGES:
            lo, hi = initteam.SQUAD_EDIT_RANGES[field]
            if not lo <= value <= hi:
                return self.refuse(what, "%s must be %d-%d (DOC/INITTEAM_FORMAT.md)" % (
                    field, lo, hi), revert)
        if field == "player":
            # Each player is in one squad only (initteam.py info checks it).
            for t, squad in self.ot.squads.items():
                for k, m in enumerate(squad):
                    if m.player == value and (t, k) != (team, slot):
                        return self.refuse(what, "player %d is already in %d %s, slot %d" % (
                            value, t, self.teams.get(t, ""), k), revert)
        if field == "shirt":
            # Shirt numbers don't repeat within a squad (initteam.py info).
            for k, m in enumerate(self.ot.squads[team]):
                if k != slot and m.shirt == value:
                    return self.refuse(what, "shirt %d is already slot %d's" % (value, k), revert)
        try:
            old = initteam.set_member(self.ot.squads[team][slot], field, value)
        except ValueError as e:
            return self.refuse(what, str(e), revert)
        self.squad_changes.pop((team, slot, field), None)
        self.squad_changes[team, slot, field] = value
        describe()
        self.edited_one(team, "%s: %s %s -> %s" % (what, field, old, value))
        return True

    def edited_one(self, team, message):
        self.app.status(message)
        if self.tree.exists(str(team)):
            self.tree.item(str(team), values=self.row(team), tags=("edited",))
        self.app.update_title()

    # saving

    def dirty(self):
        return bool(self.squad_changes or self.team_changes)

    def save(self):
        """Write the edited squad table and club pack to the mod folder."""
        if not self.dirty():
            return True
        mod = self.app.mod
        temps, commands = [], []
        try:
            if self.squad_changes:
                out = mod.target(OTEAM)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out + ".new", "wb") as f:
                    f.write(self.ot.encode())
                temps.append((out + ".new", out))
                args, last = [], None
                for (team, slot, field), value in self.squad_changes.items():
                    if (team, slot) != last:
                        args.append("%d:%d" % (team, slot))
                        last = (team, slot)
                    args.append("%s=%d" % (field, value))
                commands.append(["python", "SRC/initteam.py", "set", quote(shown_path(self.ot_path)),
                                 quote(shown_path(out + ".new"))] + args)
            if self.team_changes:
                out = mod.target(SIMPAC)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out + ".new", "wb") as f:
                    f.write(self.db.encode())
                temps.append((out + ".new", out))
                args, last = [], None
                for (team, name), value in self.team_changes.items():
                    if team != last:
                        args.append(str(team))
                        last = team
                    args.append("%s=%d" % (name, value))
                commands.append(["python", "SRC/initteam.py", "setteam",
                                 quote(shown_path(self.db_path)),
                                 quote(shown_path(out + ".new"))] + args)
        except (OSError, struct.error) as e:
            remove_new(temps)
            messagebox.showerror("Clubs", "Can't save: %s" % e)
            return False
        replace_new(temps)
        n = len(self.squad_changes) + len(self.team_changes)
        lines = log_lines("Clubs: %d changes" % n, commands, temps)
        mod.log(lines)
        self.app.write_log(lines)
        squads = bool(self.squad_changes)
        # Read the saved files back, so a bad write shows here.
        self.load("Saved %s: %d changes" % (" and ".join(shown_path(f) for _, f in temps), n))
        if squads:
            self.app.notify(self, "squads")
        return True


TEAMINIT = "PARAM/TEAM_INIT_DATA.TBB"
RIVAL_STYLE = (1, 0, 3, 2)      # 0x5531e0: Counter-Attack <-> Possession, Individual <-> Teamwork
SALARY_RATE = 6                 # salaries show in pounds as value / 6 (TEAMINIT_FORMAT.md)


class NewClubTab(Tab):
    """The player's new club, TEAM_INIT_DATA.TBB, one page per league and
    team style as pwkTeam_Init2 reads it, through teaminit.set_field and
    encode_file, as `teaminit.py set` does."""
    title = "New club"

    def __init__(self, app):
        super().__init__(app)
        self.tables = None
        self.changes = {}           # (table, record, field) -> value, in edit order
        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="League").pack(side="left")
        self.league_var = tk.StringVar(value=teaminit.LEAGUES[0])
        box = ttk.Combobox(bar, textvariable=self.league_var, values=teaminit.LEAGUES,
                           state="readonly", width=14)
        box.pack(side="left", padx=(4, 12))
        box.bind("<<ComboboxSelected>>", lambda e: self.show())
        ttk.Label(bar, text="Team style").pack(side="left")
        self.style_var = tk.StringVar(value=teaminit.STYLES[0])
        box = ttk.Combobox(bar, textvariable=self.style_var, values=teaminit.STYLES,
                           state="readonly", width=16)
        box.pack(side="left", padx=(4, 12))
        box.bind("<<ComboboxSelected>>", lambda e: self.show())
        ttk.Label(bar, text="What a new career gets for this choice on the Club Edit screen "
                            "(DOC/TEAMINIT_FORMAT.md).", foreground="#555").pack(side="left")
        self.detail = Scrolled(self.frame)
        self.detail.outer.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # loading

    def load(self, done=None):
        mod = self.app.mod
        try:
            self.path = mod.source(TEAMINIT)
            self.buf, self.end, self.raw, self.tables = teaminit.load(self.path)
            squads = initteam.OteamMembers(mod.source(OTEAM)).squads
            self.club_of = {m.player: team for team, s in squads.items() for m in s}
            mes = mod.source(MES)
            self.teams = initteam.team_names(mes, 1)
            self.stadiums = initteam.StadiumData(mod.source(STADIUMS))
        except (ValueError, struct.error, OSError, SystemExit) as e:
            self.app.status("Couldn't load the new club: %s" % e)
            messagebox.showerror("New club", "Couldn't load the new club:\n%s" % e)
            return
        self.changes = {}
        self.show()
        if done:
            self.app.status(done)
        self.app.update_title()

    def changed(self, what):
        if self.tables is None:
            return
        if what == "squads":
            squads = initteam.OteamMembers(self.app.mod.source(OTEAM)).squads
            self.club_of = {m.player: team for team, s in squads.items() for m in s}
        self.show()

    def people(self, kind):
        records = self.app.people.records
        return records[kind] if records else None

    # the page

    def show(self):
        if self.tables is None:
            return
        league = teaminit.LEAGUES.index(self.league_var.get())
        style = teaminit.STYLES.index(self.style_var.get())
        t = self.tables
        self.salary_labels = {}     # (table, record) -> refresh its pound label
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s, %s" % (teaminit.LEAGUES[league], teaminit.STYLES[style]),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        rival = teaminit.STYLES[RIVAL_STYLE[style]]
        squad = teaminit.group(t[0], (league, style))
        self.section(box, "Your squad (table 0, records %d-%d): the club takes these 18 in "
                     "order; the game picks the captain" % (squad[0], squad[teaminit.SQUAD_OWN - 1]),
                     t[0], squad[:teaminit.SQUAD_OWN])
        self.section(box, "Rival only (records %d-%d): a rival of this style takes all 22. "
                     "Your rival plays %s, so it takes that style's 22" % (
                         squad[teaminit.SQUAD_OWN], squad[-1], rival),
                     t[0], squad[teaminit.SQUAD_OWN:])
        self.section(box, "Staff (table 1)", t[1], teaminit.group(t[1], (league, style)))
        self.section(box, "Scouts (table 2)", t[2], teaminit.group(t[2], (league, style)))
        self.section(box, "Youth team (table 3): the same for every style in %s; player -1 is "
                     "an empty slot" % teaminit.LEAGUES[league], t[3], teaminit.group(t[3], (league,)))
        self.section(box, "Coach Candidate List (table 4, every style)", t[4],
                     teaminit.group(t[4], (league,)))
        self.section(box, "Scout Candidate List (table 5, every style)", t[5],
                     teaminit.group(t[5], (league,)))
        frame = ttk.LabelFrame(box, text="Rival club")
        frame.pack(fill="x", padx=8, pady=6)
        rows = ((6, 0, "manager", "manager (table 6, record 0: the game reads only this "
                                  "record, for every league and style)"),
                (7, teaminit.group(t[7], (league,))[0], "stadium", "stadium (table 7, %s)"
                 % teaminit.LEAGUES[league]))
        r8 = teaminit.group(t[8], (league, style))[0]
        rows += tuple((8, r8, name, "%s (table 8, record %d)" % (name.replace("_", " "), r8))
                      for name in ("foreign", "newface", "search_region"))
        for row, (ti, ri, name, text) in enumerate(rows):
            ttk.Label(frame, text=text).grid(row=row, column=0, sticky="w", padx=(6, 12), pady=2)
            self.value(frame, t[ti], ri, name).grid(row=row, column=1, sticky="w", pady=2)
        ttk.Label(box, text="Salaries show in game in pounds as the value / %d. The game keeps "
                            "them within a range per currency that hasn't been read yet "
                            "(TEAMINIT_FORMAT.md)." % SALARY_RATE,
                  foreground="#555", wraplength=900, justify="left").pack(anchor="w", padx=8,
                                                                       pady=(4, 12))

    def section(self, box, title, t, records):
        frame = ttk.LabelFrame(box, text=title)
        frame.pack(fill="x", padx=8, pady=6)
        fields = t.fields[2:]
        heads = ["record", "role", fields[0], "name"] + list(fields[1:])
        for col, text in enumerate(heads):
            ttk.Label(frame, text=text, foreground="#555").grid(row=0, column=col, sticky="w",
                                                               padx=(6, 8))
        for row, ri in enumerate(records, 1):
            pos = row - 1
            role = t.roles[pos] if t.roles and pos < len(t.roles) else ""
            ttk.Label(frame, text=str(ri)).grid(row=row, column=0, sticky="w", padx=(6, 8))
            ttk.Label(frame, text=role).grid(row=row, column=1, sticky="w", padx=(0, 8))
            name = ttk.Label(frame, text="")
            name.grid(row=row, column=3, sticky="w", padx=(0, 8))

            def describe(ri=ri, name=name):
                name.configure(text=self.describe(t, ri))
            describe()
            self.value(frame, t, ri, fields[0], describe).grid(row=row, column=2, sticky="w",
                                                               padx=(0, 8), pady=1)
            for col, field in enumerate(fields[1:], 4):
                cell = ttk.Frame(frame)
                cell.grid(row=row, column=col, sticky="w", padx=(0, 8), pady=1)
                self.value(cell, t, ri, field).pack(side="left")
                if field == "salary":
                    pounds = ttk.Label(cell, text="", foreground="#555")
                    pounds.pack(side="left", padx=4)

                    def show_pounds(ri=ri, k=t.fields.index("salary"), pounds=pounds):
                        pounds.configure(text="£%s" % format(t.records[ri][k] // SALARY_RATE, ","))
                    show_pounds()
                    self.salary_labels[t.index, ri] = show_pounds

    def describe(self, t, ri):
        """Who a record's id is: name, positions, and a computer club the
        player is also in."""
        ident = t.records[ri][2]
        if t.index == 3 and ident == teaminit.NO_PLAYER:
            return "(empty)"
        records = self.people(t.kind)
        if records is None:
            return "(names load with People)"
        if not 0 <= ident < len(records):
            return "?"
        r = records[ident]
        text = r.name
        if t.kind == "players":
            text += "  " + "/".join(pbdata.position_name(p) for p in r.fields["position"] if p != 13)
            if ident in self.club_of:
                team = self.club_of[ident]
                text += "  (also in %s's squad)" % self.teams.get(team, team)
        return text

    def value(self, parent, t, ri, name, after=None):
        k = t.fields.index(name)
        lo, hi = teaminit.edit_range(t, name)
        empty_slot = t.index == 3 and name == "player"
        if empty_slot:
            lo = -1

        def get():
            v = t.records[ri][k]
            return -1 if empty_slot and v == teaminit.NO_PLAYER else v

        if name == "stadium":
            spec = ("choice", list(range(lo, hi + 1)))

            def label(v):
                if not 0 <= v < len(self.stadiums.rows):
                    return str(v)
                return "%d  %d seats%s" % (v, self.stadiums.capacity(v),
                                           ", roof" if self.stadiums.rows[v][0] else "")
        elif t.index == 6:
            managers = self.people("managers")
            spec = ("choice", list(range(lo, hi + 1)))

            def label(v):
                return "%d %s" % (v, managers[v].name) if managers and 0 <= v < len(managers) \
                    else str(v)
        else:
            spec = ("range", lo, hi)
            label = str
        return value_input(parent, spec, label, get,
                           lambda text, revert: self.commit(t, ri, name, text, revert, after))

    # edits

    def commit(self, t, ri, name, text, revert, after=None):
        what = "table %d record %d" % (t.index, ri)
        try:
            value = int(text)
        except ValueError:
            return self.refuse(what, "%s must be a number" % name, revert)
        lo, hi = teaminit.edit_range(t, name)
        if t.index == 3 and name == "player" and value == -1:
            value = teaminit.NO_PLAYER
        elif not lo <= value <= hi:
            return self.refuse(what, "%s must be %d-%d" % (name, lo, hi), revert)
        try:
            old = teaminit.set_field(t, ri, name, value)
        except ValueError as e:
            return self.refuse(what, str(e), revert)
        self.changes.pop((t.index, ri, name), None)
        self.changes[t.index, ri, name] = value
        if after:
            after()
        if (t.index, ri) in self.salary_labels:
            self.salary_labels[t.index, ri]()
        self.app.status("%s: %s %s -> %s" % (what, name, teaminit.shown_value(t, old),
                                            teaminit.shown_value(t, value)))
        self.app.update_title()
        return True

    def refuse(self, what, message, revert):
        revert()
        self.app.status("%s: %s" % (what, message))
        messagebox.showerror("New club", "%s: %s" % (what, message))
        return False

    # saving

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(TEAMINIT)
        temps = [(out + ".new", out)]
        try:
            data = teaminit.encode_file(self.buf, self.end, self.raw, self.tables)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("New club", "Can't save: %s" % e)
            return False
        replace_new(temps)
        args, last = [], None
        for (ti, ri, name), value in self.changes.items():
            if (ti, ri) != last:
                args.append("%d:%d" % (ti, ri))
                last = (ti, ri)
            args.append("%s=%s" % (name, teaminit.shown_value(self.tables[ti], value)))
        cmd = ["python", "SRC/teaminit.py", "set", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + args
        n = len(self.changes)
        lines = log_lines("New club: %d changes" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (shown_path(out), n))
        return True


UNIFORM_LIST = "PLAYER/UNIFORM_LIST.TBB"
UNIFORM_GK = "PLAYER/UNIFORM_GK.TBB"


def colour_input(parent, swatches, get, apply):
    """A kit colour: a drop-down of the 96 colours by name and a swatch of
    the chosen one (entry 128 of its palette)."""
    frame = ttk.Frame(parent)
    swatch = tk.Label(frame, width=3, relief="solid", borderwidth=1)

    def paint():
        v = get()
        if swatches and 0 <= v < len(swatches):
            swatch.configure(bg="#%02x%02x%02x" % swatches[v], text="")
        else:
            swatch.configure(bg=frame.winfo_toplevel().cget("bg"), text="?")

    def commit(text, revert):
        ok = apply(text, revert)
        paint()
        return ok
    swatch.pack(side="left", padx=(0, 4))
    value_input(frame, ("choice", list(range(uniform.COLOURS))), uniform.colour_label, get,
                commit).pack(side="left")
    paint()
    return frame


class KitsTab(Tab):
    """Club kits (UNIFORM_LIST.TBB) and the keeper kits made from them
    (UNIFORM_GK.TBB), through uniform.set_row_field and apply_gk_edit, as
    `uniform.py set` and `setgk` do."""
    title = "Kits"

    def __init__(self, app):
        super().__init__(app)
        self.blob = None
        self.changes = {}           # (team, field name) -> value, in edit order
        self.gk_changes = {}        # field name -> value
        self.current = None
        inner = ttk.Notebook(self.frame)
        inner.pack(fill="both", expand=True, padx=4, pady=4)
        clubs = ttk.Frame(inner)
        keepers = ttk.Frame(inner)
        inner.add(clubs, text="Club kits")
        inner.add(keepers, text="Keeper kits for your club, the rival and VS teams")

        bar = ttk.Frame(clubs)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Name or id").pack(side="left")
        self.find_var = tk.StringVar()
        find = ttk.Entry(bar, textvariable=self.find_var, width=22)
        find.pack(side="left", padx=(4, 12))
        find.bind("<Return>", lambda e: self.refresh_list())
        ttk.Button(bar, text="Search", command=self.refresh_list).pack(side="left")
        self.count_label = ttk.Label(bar, text="")
        self.count_label.pack(side="left", padx=12)
        panes = self.panes = ttk.PanedWindow(clubs, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("id", "name", "kit")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("Id", "Club", "Kit"), (50, 170, 70)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, stretch=c == "name")
        self.tree.tag_configure("edited", foreground="#b03000")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=1)
        self.detail = Scrolled(panes)
        panes.add(self.detail.outer, weight=3)

        bar = ttk.Frame(keepers)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Outfield shirt design").pack(side="left")
        self.design_var = tk.StringVar(value="0")
        spin = ttk.Spinbox(bar, textvariable=self.design_var, from_=0,
                           to=uniform.OUTFIELD_SHIRTS - 1, width=5, command=self.show_gk)
        spin.pack(side="left", padx=(4, 12))
        spin.bind("<Return>", lambda e: self.show_gk())
        ttk.Label(bar, text="In a match, these teams' keeper kit comes from the outfield shirt "
                            "design: the row below, then the first scheme whose shirt colour 1 "
                            "doesn't clash (DOC/UNIFORM_FORMAT.md).",
                  foreground="#555", wraplength=760, justify="left").pack(side="left")
        self.gk_detail = Scrolled(keepers)
        self.gk_detail.outer.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    # loading

    def load(self, done=None):
        mod = self.app.mod
        try:
            self.path = mod.source(UNIFORM_LIST)
            self.blob, self.base, self.n = uniform.rows_of(self.path)
            self.gk_path = mod.source(UNIFORM_GK)
            self.gk_original = open(self.gk_path, "rb").read()
            self.gk_blob = bytearray(self.gk_original)
            self.t0, self.t1 = uniform.load_gk(self.gk_path)
            self.teams = initteam.team_names(mod.source(MES), 1)
            self.swatches = uniform.colour_swatches(os.path.join(mod.dat, "PLAYER"))
            try:
                self.licensed = set(uniform.licence_table(mod.disc_source(SLES))[0])
            except (OSError, ValueError, struct.error):
                self.licensed = set()
        except (ValueError, struct.error, OSError) as e:
            self.app.status("Couldn't load the kits: %s" % e)
            messagebox.showerror("Kits", "Couldn't load the kits:\n%s" % e)
            return
        self.rows = {}              # team -> unpacked fields, edits included
        self.changes, self.gk_changes = {}, {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        self.show_gk()
        if done:
            self.app.status(done)
        self.app.update_title()

    def fields(self, team):
        if team not in self.rows:
            i = team - uniform.FIRST_TEAM
            self.rows[team] = uniform.unpack(
                self.blob[self.base + i * uniform.ROW_SIZE:self.base + (i + 1) * uniform.ROW_SIZE])
        return self.rows[team]

    # the club list

    def refresh_list(self):
        if self.blob is None:
            return
        find = self.find_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        n = 0
        for i in range(self.n):
            team = i + uniform.FIRST_TEAM
            if self.fields(team)[0] != team:
                continue            # rows with id 0 are never looked up
            name = self.teams.get(team, "")
            if find and not (find == str(team) or (not find.isdigit() and find in name.lower())):
                continue
            self.tree.insert("", "end", iid=str(team),
                             values=(team, name, "licensed" if team in self.licensed else ""),
                             tags=("edited",) if any(t == team for t, _ in self.changes) else ())
            n += 1
        self.count_label.configure(text="%d clubs" % n)

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    # a club's kits

    def show(self, team):
        self.current = team
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%d  %s" % (team, self.teams.get(team, "")),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        if team in self.licensed:
            ttk.Label(box, text="Licensed club: the game draws its kits from the licensed kit "
                                "textures (PLPACK_HOME/AWAY), not from these fields "
                                "(DOC/UNIFORM_FORMAT.md#licensed-kits).",
                      foreground="#a05000", wraplength=700, justify="left").pack(anchor="w", padx=8)
        ttk.Label(box, text="A design or colour past what its pack holds would be reset by "
                            "the game, so the lists stop there. Fields with no name yet are "
                            "read-only.", foreground="#555").pack(anchor="w", padx=8)
        for side in ("home", "away"):
            frame = ttk.LabelFrame(box, text=side.capitalize())
            frame.pack(fill="x", padx=8, pady=6)
            row = 0
            for k, label in enumerate(uniform.SIDE_FIELD_NAMES):
                name = "%s.side.%d" % (side, k)
                ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(6, 12))
                self.kit_widget(frame, team, name).grid(row=row, column=1, columnspan=2,
                                                        sticky="w", pady=1)
                row += 1
            ttk.Label(frame, text="outfield kit", foreground="#555").grid(row=row, column=1,
                                                                         sticky="w")
            ttk.Label(frame, text="keeper kit", foreground="#555").grid(row=row, column=2,
                                                                       sticky="w")
            row += 1
            for k, label in enumerate(uniform.KIT_FIELD_NAMES):
                ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(6, 12))
                for col, part in ((1, "outfield"), (2, "keeper")):
                    self.kit_widget(frame, team, "%s.%s.%d" % (side, part, k)).grid(
                        row=row, column=col, sticky="w", padx=(0, 16), pady=1)
                row += 1
        self.fit_detail()

    def fit_detail(self):
        self.frame.update_idletasks()
        need = self.detail.inner.winfo_reqwidth() + 24
        have = self.detail.outer.winfo_width()
        if need > have > 1:
            pos = self.panes.sashpos(0)
            self.panes.sashpos(0, max(LIST_MIN, pos - (need - have)))

    def kit_widget(self, parent, team, name):
        fields = self.fields(team)
        hw = uniform.field_index(name)
        rng = uniform.edit_range(name)

        def get():
            return fields[hw]
        if rng is None:
            return ttk.Label(parent, text=str(get()), foreground="#777")

        def apply(text, revert):
            return self.commit(team, name, text, revert)
        n = int(name.rsplit(".", 1)[1])
        part = name.split(".")[1]
        if part != "side" and n in uniform.COLOUR_FIELDS:
            return colour_input(parent, self.swatches, get, apply)
        if part == "side":
            names = {3: ("off", "on"), 4: uniform.SHORTS_NUMBER}[n]
            return value_input(parent, ("choice", list(range(rng[0], rng[1] + 1))),
                               lambda v: "%d %s" % (v, names[v]) if v < len(names) else str(v),
                               get, apply)
        return value_input(parent, ("range",) + rng, str, get, apply)

    def commit(self, team, name, text, revert):
        what = "%d %s" % (team, self.teams.get(team, ""))
        try:
            value = int(text)
        except ValueError:
            return self.refuse(what, "%s must be a number" % name, revert)
        lo, hi = uniform.edit_range(name)
        if not lo <= value <= hi:
            return self.refuse(what, "%s must be %d-%d" % (name, lo, hi), revert)
        try:
            old = uniform.set_row_field(self.fields(team), name, value)
        except ValueError as e:
            return self.refuse(what, str(e), revert)
        self.changes.pop((team, name), None)
        self.changes[team, name] = value
        self.app.status("%s: %s %s -> %s" % (what, name, old, value))
        if self.tree.exists(str(team)):
            self.tree.item(str(team), tags=("edited",))
        self.app.update_title()
        return True

    def refuse(self, what, message, revert):
        revert()
        self.app.status("%s: %s" % (what, message))
        messagebox.showerror("Kits", "%s: %s" % (what, message))
        return False

    # the keeper kit table

    def show_gk(self):
        if self.blob is None:
            return
        try:
            design = int(self.design_var.get())
        except ValueError:
            return
        if not 0 <= design < uniform.OUTFIELD_SHIRTS:
            return
        self.gk_detail.clear()
        box = self.gk_detail.inner
        frame = ttk.LabelFrame(box, text="Table 0: the keeper designs for outfield shirt "
                                         "design %d" % design)
        frame.pack(fill="x", padx=8, pady=6)
        for col, (part, _, limit) in enumerate(uniform.GK_ROW_FIELDS):
            ttk.Label(frame, text="keeper %s design" % part).grid(row=0, column=2 * col,
                                                                 sticky="w", padx=(6, 6))
            name = "outfield.%d.%s" % (design, part)
            self.gk_widget(frame, name, ("range", 0, limit - 1)).grid(
                row=0, column=2 * col + 1, sticky="w", padx=(0, 16), pady=4)
        off, _ = uniform.gk_offset(self.t0, self.t1, "outfield.%d.shirt" % design)
        keeper = self.gk_blob[off]
        frame = ttk.LabelFrame(box, text="Table 1: the 6 colour schemes of keeper shirt design "
                                         "%d, tried in order" % keeper)
        frame.pack(fill="x", padx=8, pady=6)
        if keeper < uniform.GK_SHIRTS:
            heads = ["scheme"] + [uniform.KIT_FIELD_NAMES[f] for f in uniform.SCHEME_FIELDS]
            for col, text in enumerate(heads):
                ttk.Label(frame, text=text, foreground="#555", wraplength=90).grid(
                    row=0, column=col, sticky="w", padx=(6, 4))
            for n in range(uniform.SCHEMES):
                ttk.Label(frame, text=str(n)).grid(row=n + 1, column=0, sticky="w", padx=(6, 4))
                for col, f in enumerate(uniform.SCHEME_FIELDS, 1):
                    name = "keeper.%d.%d.%d" % (keeper, n, f)
                    spec = ("range", 0, uniform.CAPTAIN_MARKS - 1) if f == 14 else None
                    self.gk_widget(frame, name, spec).grid(row=n + 1, column=col, sticky="w",
                                                           padx=(0, 4), pady=1)

    def gk_widget(self, parent, name, spec):
        off, _ = uniform.gk_offset(self.t0, self.t1, name)

        def get():
            return self.gk_blob[off]

        def apply(text, revert):
            return self.commit_gk(name, text, revert)
        if spec is None:
            return colour_input(parent, self.swatches, get, apply)
        return value_input(parent, spec, str, get, apply)

    def commit_gk(self, name, text, revert):
        try:
            value = int(text)
            old = uniform.apply_gk_edit(self.gk_blob, self.t0, self.t1, name, value)
        except ValueError as e:
            return self.refuse("UNIFORM_GK", str(e), revert)
        self.gk_changes.pop(name, None)
        self.gk_changes[name] = value
        self.app.status("UNIFORM_GK %s: %s -> %s" % (name, old, value))
        self.app.update_title()
        if name.endswith(".shirt"):
            self.show_gk()          # another keeper design: show its schemes
        return True

    # saving

    def dirty(self):
        return bool(self.changes or self.gk_changes)

    def save(self):
        if not self.dirty():
            return True
        mod = self.app.mod
        temps, commands = [], []
        try:
            if self.changes:
                out = mod.target(UNIFORM_LIST)
                data = bytearray(self.blob)
                for team in {t for t, _ in self.changes}:
                    i = team - uniform.FIRST_TEAM
                    lo = self.base + i * uniform.ROW_SIZE
                    data[lo:lo + uniform.ROW_SIZE] = uniform.pack(
                        bytes(self.blob[lo:lo + uniform.ROW_SIZE]), self.rows[team])
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out + ".new", "wb") as f:
                    f.write(data)
                temps.append((out + ".new", out))
                args, last = [], None
                for (team, name), value in self.changes.items():
                    if team != last:
                        args.append(str(team))
                        last = team
                    args.append("%s=%d" % (name, value))
                commands.append(["python", "SRC/uniform.py", "set", quote(shown_path(self.path)),
                                 quote(shown_path(out + ".new"))] + args)
            if self.gk_changes:
                uniform.check_gk_blob(self.gk_blob, self.gk_original, self.t0, self.t1)
                out = mod.target(UNIFORM_GK)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out + ".new", "wb") as f:
                    f.write(self.gk_blob)
                temps.append((out + ".new", out))
                commands.append(["python", "SRC/uniform.py", "setgk",
                                 quote(shown_path(self.gk_path)), quote(shown_path(out + ".new"))]
                                + ["%s=%d" % kv for kv in self.gk_changes.items()])
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Kits", "Can't save: %s" % e)
            return False
        replace_new(temps)
        n = len(self.changes) + len(self.gk_changes)
        lines = log_lines("Kits: %d changes" % n, commands, temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (" and ".join(shown_path(f) for _, f in temps), n))
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


# --- building a disc ---------------------------------------------------------

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
REDUMP_NAME = "Let's Make a Soccer Team! (Europe, Australia) (En,Fr,De,Es,It).iso"


def redump_size():
    import extract_disc
    return extract_disc.REDUMP["size"]


def find_original():
    """The Redump dump in the current folder, by its Redump name and size
    (a disc built from it has the same size, so the name decides)."""
    if os.path.exists(REDUMP_NAME) and os.path.getsize(REDUMP_NAME) == redump_size():
        return REDUMP_NAME
    return ""


class BuildDialog:
    """Build a disc image from the mod folder with patch_disc.py, and an
    xdelta patch of it with vcdiff.py, running the same commands a user
    would type and showing their output."""

    def __init__(self, app):
        self.app, self.mod = app, app.mod
        self.proc = None
        self.running = False
        self.queue = []
        self.lock = threading.Lock()
        win = self.win = tk.Toplevel(app.root)
        win.title("Build disc")
        win.transient(app.root)
        win.geometry("960x620")
        win.protocol("WM_DELETE_WINDOW", self.close)
        settings = self.load_settings()
        name = os.path.basename(os.path.abspath(self.mod.root))
        original = settings.get("original")
        if not (original and os.path.isfile(original)):    # moved or deleted since
            original = find_original()
        self.original = tk.StringVar(value=original)
        self.make_image = tk.IntVar(value=settings.get("make_image", 1))
        self.output = tk.StringVar(value=settings.get("output") or name + ".iso")
        self.make_patch = tk.IntVar(value=settings.get("make_patch", 1))
        self.patch = tk.StringVar(value=settings.get("patch") or name + ".xdelta")
        self.skip = tk.IntVar(value=settings.get("skip_tutorial", 0))

        form = ttk.Frame(win)
        form.pack(fill="x", padx=10, pady=10)
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text="Original disc image").grid(row=0, column=0, sticky="w",
                                                         padx=(0, 8), pady=3)
        ttk.Entry(form, textvariable=self.original).grid(row=0, column=1, sticky="ew", pady=3)
        ttk.Button(form, text="Browse...", command=lambda: self.browse(self.original, "open")
                   ).grid(row=0, column=2, padx=(8, 0), pady=3)
        # What to write: a disc image, an xdelta patch, or both. A patch on
        # its own still needs a patched image to compare with, so one is
        # built next to the patch and removed afterwards.
        self.entries = {}
        for row, (text, flag, var, kind) in enumerate((
                ("Write a modded disc image", self.make_image, self.output, "save"),
                ("Write an xdelta patch", self.make_patch, self.patch, "patch")), 1):
            ttk.Checkbutton(form, text=text, variable=flag, command=self.update_entries
                            ).grid(row=row, column=0, sticky="w", padx=(0, 8), pady=3)
            entry = ttk.Entry(form, textvariable=var)
            entry.grid(row=row, column=1, sticky="ew", pady=3)
            button = ttk.Button(form, text="Browse...",
                                command=lambda v=var, k=kind: self.browse(v, k))
            button.grid(row=row, column=2, padx=(8, 0), pady=3)
            self.entries[kind] = (flag, entry, button)
        ttk.Checkbutton(form, text="Skip the tutorial (for testing; patch_disc.py "
                                   "--skip-tutorial)", variable=self.skip
                        ).grid(row=3, column=0, columnspan=3, sticky="w", pady=(6, 0))
        ttk.Label(form, text="The original must be the Redump dump (redump.info/disc/12334) "
                             "for a patch others can apply. It is only read. A patch without "
                             "the image still needs room for a temporary one while it is made.",
                  foreground="#555", wraplength=900, justify="left"
                  ).grid(row=4, column=0, columnspan=3, sticky="w", pady=(6, 0))
        self.update_entries()

        targets = self.mod.targets()
        ttk.Label(win, text="Edited files in %s (%d):" % (shown_path(os.path.abspath(
            self.mod.root)), len(targets))).pack(anchor="w", padx=10)
        files = tk.Listbox(win, height=min(6, max(2, len(targets))))
        for target, path in targets:
            files.insert("end", "%s  <-  %s" % (target, shown_path(path)))
        files.pack(fill="x", padx=10)

        out = ttk.Frame(win)
        out.pack(fill="both", expand=True, padx=10, pady=(8, 0))
        self.text = tk.Text(out, wrap="word", font="TkFixedFont", height=12, state="disabled")
        sb = ttk.Scrollbar(out, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.text.pack(fill="both", expand=True)

        buttons = ttk.Frame(win)
        buttons.pack(fill="x", padx=10, pady=10)
        self.close_button = ttk.Button(buttons, text="Close", command=self.close)
        self.close_button.pack(side="right")
        self.build_button = ttk.Button(buttons, text="Build", command=self.build)
        self.build_button.pack(side="right", padx=8)
        if not targets:
            self.write("No edited files in the mod folder yet; save some edits first.\n")
            self.build_button.configure(state="disabled")

    # settings, kept in the mod folder

    def settings_path(self):
        return os.path.join(self.mod.root, "build.json")

    def load_settings(self):
        import json
        try:
            with open(self.settings_path(), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def save_settings(self):
        import json
        os.makedirs(self.mod.root, exist_ok=True)
        with open(self.settings_path(), "w", encoding="utf-8") as f:
            json.dump({"original": self.original.get(), "make_image": self.make_image.get(),
                       "output": self.output.get(), "make_patch": self.make_patch.get(),
                       "patch": self.patch.get(), "skip_tutorial": self.skip.get()}, f,
                      indent=2)

    def update_entries(self):
        for flag, entry, button in self.entries.values():
            state = "normal" if flag.get() else "disabled"
            entry.configure(state=state)
            button.configure(state=state)

    def image_path(self):
        """Where patch_disc.py writes the image: the chosen output, or a
        temporary file next to the patch when only the patch is wanted."""
        if self.make_image.get():
            return self.output.get()
        return os.path.splitext(self.patch.get())[0] + ".building.iso"

    def browse(self, var, kind):
        from tkinter import filedialog
        start = os.path.dirname(os.path.abspath(var.get() or "."))
        if kind == "open":
            path = filedialog.askopenfilename(parent=self.win, initialdir=start,
                                              filetypes=[("Disc images", "*.iso"), ("All", "*")])
        elif kind == "save":
            path = filedialog.asksaveasfilename(parent=self.win, initialdir=start,
                                                defaultextension=".iso",
                                                filetypes=[("Disc images", "*.iso")])
        else:
            path = filedialog.asksaveasfilename(parent=self.win, initialdir=start,
                                                defaultextension=".xdelta",
                                                filetypes=[("xdelta patches", "*.xdelta")])
        if path:
            var.set(shown_path(path))

    # output

    def write(self, text):
        self.text.configure(state="normal")
        self.text.insert("end", text)
        self.text.see("end")
        self.text.configure(state="disabled")

    def poll(self):
        with self.lock:
            chunks, self.queue = self.queue, []
        for c in chunks:
            if isinstance(c, tuple):        # ("done", ok, log lines)
                self.finished(*c[1:])
            else:
                self.write(c)
        if (self.running or chunks) and self.win.winfo_exists():
            self.win.after(100, self.poll)

    # building

    def commands(self):
        original, output = self.original.get(), self.image_path()
        cmd = ["patch_disc.py", "patch", original, output]
        cmd += ["%s=%s" % (t, shown_path(p)) for t, p in self.mod.targets()]
        cmd += ["--copies", "--dat", shown_path(self.mod.dat)]
        if self.skip.get():
            cmd.append("--skip-tutorial")
        out = [cmd]
        if self.make_patch.get():
            out.append(["vcdiff.py", "make", original, output, self.patch.get()])
        return out

    def check(self):
        """Problems that stop a build, or that the user must accept."""
        original, output = self.original.get(), self.image_path()
        if not original or not os.path.isfile(original):
            messagebox.showerror("Build disc", "Choose the original disc image.", parent=self.win)
            return False
        if not (self.make_image.get() or self.make_patch.get()):
            messagebox.showerror("Build disc", "Choose a disc image, a patch or both to write.",
                                 parent=self.win)
            return False
        if self.make_patch.get() and not self.patch.get():
            messagebox.showerror("Build disc", "Choose where to write the patch.", parent=self.win)
            return False
        same = {os.path.abspath(original)}
        for path in [output] + ([self.patch.get()] if self.make_patch.get() else []):
            if not path:
                messagebox.showerror("Build disc", "Choose where to write the outputs.",
                                     parent=self.win)
                return False
            if os.path.abspath(path) in same:
                messagebox.showerror("Build disc", "%s would overwrite another file of this "
                                     "build." % path, parent=self.win)
                return False
            same.add(os.path.abspath(path))
        if os.path.getsize(original) != redump_size():
            msg = ("%s is not the size of the Redump dump, so it isn't an unmodified disc."
                   % original)
            if self.make_patch.get():
                msg += " A patch made against it only applies to this exact file."
            if not messagebox.askyesno("Build disc", msg + "\n\nBuild anyway?", parent=self.win):
                return False
        existing = [p for p in (output, self.patch.get() if self.make_patch.get() else "")
                    if p and os.path.exists(p)]
        if existing and not messagebox.askyesno(
                "Build disc", "Overwrite %s?" % " and ".join(existing), parent=self.win):
            return False
        # The image is a full copy of the original (it can grow a little).
        import shutil
        folder = os.path.dirname(os.path.abspath(output))
        free = shutil.disk_usage(folder).free + (os.path.getsize(output)
                                                 if os.path.exists(output) else 0)
        need = os.path.getsize(original) + (64 << 20)
        if free < need:
            messagebox.showerror("Build disc", "%s needs about %d MB free for the %s image; "
                                 "there are %d MB." % (folder, need >> 20, "disc" if
                                 self.make_image.get() else "temporary", free >> 20),
                                 parent=self.win)
            return False
        return True

    def build(self):
        if any(t.dirty() for t in self.app.tabs):
            if not messagebox.askyesno("Build disc", "Save the unsaved edits first? The disc is "
                                       "built from the saved files.", parent=self.win):
                return
            if not self.app.save():
                return
            # A save reloads its tab; the files it wrote are on disk now.
        if not self.check():
            return
        self.save_settings()
        commands = self.commands()
        temp = None if self.make_image.get() else self.image_path()
        self.build_button.configure(state="disabled")
        self.running = True
        self.write("\n")

        def work():
            log = ["# %s  Build disc" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M")]
            ok = True
            for cmd in commands:
                shown = ["python", "SRC/" + cmd[0]] + [quote(a) for a in cmd[1:]]
                log.append(" ".join(shown))
                with self.lock:
                    self.queue.append("> %s\n" % " ".join(shown))
                try:
                    self.proc = subprocess.Popen(
                        [sys.executable, "-u", os.path.join(SRC_DIR, cmd[0])] + cmd[1:],
                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                except OSError as e:
                    with self.lock:
                        self.queue.append("!! %s\n" % e)
                    ok = False
                    break
                while True:
                    data = self.proc.stdout.read1(4096)
                    if not data:
                        break
                    with self.lock:
                        self.queue.append(data.decode("utf-8", "replace").replace("\r\n", "\n"))
                code = self.proc.wait()
                if code != 0:
                    ok = False
                    with self.lock:
                        self.queue.append("\n!! %s stopped with exit code %d\n" % (cmd[0], code))
                    log.append("# stopped with exit code %d" % code)
                    break
            if temp and os.path.exists(temp):
                os.remove(temp)
                log.append("# removed the temporary image %s" % shown_path(temp))
                with self.lock:
                    self.queue.append("Removed the temporary image %s\n" % shown_path(temp))
            log.append("# %s" % ("built" if ok else "failed; the outputs are incomplete"))
            with self.lock:
                self.queue.append(("done", ok, log))
            self.running = False

        threading.Thread(target=work, daemon=True).start()
        self.poll()

    def finished(self, ok, log):
        self.proc = None
        self.build_button.configure(state="normal")
        self.mod.log(log)
        self.app.write_log(log)
        if ok:
            done = "Built " + " and ".join(
                ([self.output.get()] if self.make_image.get() else [])
                + ([self.patch.get()] if self.make_patch.get() else []))
            self.write("\n%s.\n" % done)
            self.app.status(done)
            # vcdiff.py make names the source's SHA-1; a disc of the right
            # size can still be an earlier modded one.
            if self.make_patch.get() and "not the Redump image" in self.text.get("1.0", "end"):
                messagebox.showwarning(
                    "Build disc", "The original isn't the Redump dump (see its SHA-1 above), "
                    "so the patch only applies to that exact file. Build from an unmodified "
                    "disc to share it.", parent=self.win)
        else:
            self.write("\nThe build failed; don't use the output image or patch.\n")
            self.app.status("Build failed")

    def close(self):
        if self.running:
            if not messagebox.askyesno("Build disc", "Stop the build? The output it was "
                                       "writing will be incomplete.", parent=self.win):
                return
            if self.proc:
                self.proc.terminate()
        self.win.destroy()


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
        # 1280x720, or the screen less a margin. A page wider than its pane
        # scrolls sideways.
        w = min(WINDOW[0], self.root.winfo_screenwidth() - 80)
        h = min(WINDOW[1], self.root.winfo_screenheight() - 120)
        self.root.geometry("%dx%d+%d+%d" % (w, h, (self.root.winfo_screenwidth() - w) // 2,
                                            (self.root.winfo_screenheight() - h) // 3))
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        menu = tk.Menu(self.root)
        file_menu = tk.Menu(menu, tearoff=False)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save)
        file_menu.add_command(label="Build disc...", accelerator="Ctrl+B",
                              command=lambda: BuildDialog(self))
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.quit)
        menu.add_cascade(label="File", menu=file_menu)
        self.root.configure(menu=menu)
        self.root.bind_all("<Control-s>", lambda e: self.save())
        self.root.bind_all("<Control-b>", lambda e: BuildDialog(self))
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True)
        self.status_var = tk.StringVar()
        ttk.Label(self.root, textvariable=self.status_var, anchor="w", relief="sunken"
                  ).pack(fill="x", side="bottom")
        self.people = PeopleTab(self)
        self.clubs = ClubsTab(self)
        self.newclub = NewClubTab(self)
        self.kits = KitsTab(self)
        self.tabs = [self.people, self.clubs, self.newclub, self.kits]
        self.log_tab = LogTab(self)
        for tab in self.tabs + [self.log_tab]:
            self.notebook.add(tab.frame, text=tab.title)
        self.update_title()
        for tab in self.tabs:
            tab.load()

    def status(self, text):
        self.status_var.set(text)

    def notify(self, source, what):
        for tab in self.tabs:
            if tab is not source:
                tab.changed(what)

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
