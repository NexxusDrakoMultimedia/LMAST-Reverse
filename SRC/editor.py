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
or both, optionally with patch_disc.py's switches (--skip-tutorial,
--sponsor-negotiation, --launcher, --mod-saves): `patch_disc.py patch ...
--copies` puts the mod folder on a copy of the original, and `vcdiff.py
make` compares the two. For a patch on its own that image is temporary
(<patch>.building.iso, removed after). It shows their output and logs
both commands. The original must be the Redump dump for a patch others
can apply.

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
    Season   the starting divisions by league, with last season's table,
             swapping two league clubs' places (initteam.py swap;
             DOC/INITTEAM_FORMAT.md#swapping-clubs), and each first
             division's size, in the range leaguesize.py allows; a size
             change also rewrites the three schedule packs and their .HED
             and the leagues' club counts in REGULATION.TBB and
             CLUBRESULT.TBB, which the Regulations tab then reads again
             (leaguesize.py build --over;
             DOC/SCHEDULE_FORMAT.md#where-the-clubs-come-from).
    Free agents
             the players without a club at the start of a career
             (PLRESOURCESIM.PAC entry 15, plrsim.py setfree;
             DOC/PLRESOURCESIM_FORMAT.md). Refuses a player already in the
             list or in a club's squad. Shares the pack with the Clubs tab:
             each saves its edits onto the file as it is then.
    Regulations
             each schedule's match rules, win bonus, prizes and places
             (REGULATION.TBB, regulation.py set; DOC/REGULATION_FORMAT.md),
             named from the schedule packs, and how each reports a final
             place: league, cup or not ranked, and the third-place match
             (CLUBRESULT.TBB, clubresult.py set;
             DOC/CLUBRESULT_FORMAT.md), with the names a cup's places
             get. The club counts are shown, not edited (they must match
             the schedule; the Season tab sets them), and the squad's
             copy follows the squad. Money shows in pounds.
    Training the training tables (TRAINING_LIST.TBB, training.py set;
             DOC/TRAINING_FORMAT.md): pick a table, then a row (a practice,
             camp type, pitch position, equipment item or growth type), and
             edit its value for each ability, its fatigue or each age.
             Columns the game doesn't read are shown, not edited.
    Camps    the training camps (CAMP_LIST.TBB, camp.py set;
             DOC/CAMP_FORMAT.md): each camp's town, description and the
             clubs of its area, and its camp type, the one field edited,
             with what that type trains (from the Training tab, as the
             retail game reads it and with the LMASTER camp-types fix).
    Facilities the facility records (PLRESOURCECOMMON.PAC entry 0,
             plrcommon.py set; DOC/PLRESOURCECOMMON_FORMAT.md): pick a
             table (sites, equipment, club houses, stadiums, adverts), then
             a record, and edit its build costs, upkeep, build times and
             stadium capacities. Money shows in pounds.
    Kits     every club's home and away kits (UNIFORM_LIST.TBB) and the
             keeper kits made from the outfield kit for your club, the rival
             and the VS teams (UNIFORM_GK.TBB), through uniform.py
             (DOC/UNIFORM_FORMAT.md). Colours show as swatches. A licensed
             club's descriptors (numbers, name, collar, captain mark) are
             written to both copies, the executable's (mod/disc/SLES_541.51,
             which the game draws from) and PLPACK_HOME/AWAY.PAC, as
             `uniform.py setexe` and `setlicence` do.
    Text     message text in MES.PAC, one message in all 7 language slots,
             found by category, text or id (mbb.py; DOC/MBB_FORMAT.md). A
             file that outgrows its slot makes MES.PAC grow and moves the
             later files; Build disc then also updates the executable's
             index of them.
    Tours    the clubs a tour can play, by region (TOUR_LIST.TBB, tour.py
             set; DOC/PARAM_DIR.md#tour_listtbb-tour-opponents-by-region):
             each pair's club and region, at most 40 clubs a region.
    Tactics  the tactics screen's eight Set Formation presets
             (TACTICS_FORMATION_SET.TBB, formset.py set;
             DOC/PARAM_DIR.md#tactics_formation_settbb-tactics-presets):
             seven team tactics and a formation each. Build disc's
             --copies carries them into the PRELOAD/TACTICS* packs.
    Comments the detail screens' comment lines for players, managers,
             coaches and scouts: the data tables of the PSCCOMMON.PAC
             scripts the game runs (sqb.py settable;
             DOC/SQB_FORMAT.md#the-detail-screen-comments), with each
             message number's text. --copies carries the pack into
             PRELOAD/STATIONFILE.PAC.

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
import leaguesize
import mbb
import patch_disc
import pbdata
import plrcommon
import plrsim
import camp
import clubresult
import formset
import regulation
import sqb
import tour
import training
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
            # A <name>.new folder is a save in progress, like a .new file.
            dirs[:] = sorted(d for d in dirs if not d.endswith(".new"))
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
    low, high[, step]). label(v) is a value's text, get() the current value, and
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
        step = spec[3] if len(spec) > 3 else 1
        w = ttk.Spinbox(parent, textvariable=var, from_=lo, to=hi, increment=step,
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


def log_lines(title, commands, temps, report="", moved="each .new file"):
    """The editor.log entry for one save."""
    lines = ["# %s  %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), title)]
    lines += [" ".join(c) for c in commands]
    lines.append("# then %s replaces %s" % (moved, ", ".join(shown_path(f) for _, f in temps)))
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
        (OTEAMMEMBER.TBB), "people" (the People tab's records) or
        "schedules" (the Season tab's size change, which also writes
        REGULATION.TBB)."""
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
            "ball_touch", "dribble_style", "explodetype")),
        ("Play", ("style", "skills", "tendency", "flags")),
        ("Kit style", ("sleeves", "wristband", "gloves", "gk_cap", "gk_gloves", "gk_pants",
                       "boots")),
        ("Abilities", ("ability",)),
    ),
    "managers": (
        ("Basics", ("name", "nation", "age", "rank", "job", "face", "req_status",
                    "appeartype", "real_name", "model_pattern")),
        ("Policies", ("comptype", "moti_type", "select_policy", "match_policy", "training_policy",
                      "rest_policy", "policy", "policy_range", "policy_best")),
        ("Tactics", ("formation", "attacking", "possession", "centre_side", "left_right",
                     "press_line", "press", "offside", "attack_pattern")),
        ("Drills (training menu items)", ("manager_drill", "coach_drill")),
        ("Abilities", ("ability",)),
    ),
    "scouts": (
        ("Basics", ("name", "nation", "age", "rank", "face", "req_status", "appeartype",
                    "real_name")),
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
                # The Free agents tab writes the same pack, so apply the
                # edits to the file as it is now, not as it was loaded.
                self.db_path = mod.source(SIMPAC)
                db = initteam.TeamDb(self.db_path)
                for (team, name), value in self.team_changes.items():
                    initteam.set_team_field(db.records[team], name, value)
                out = mod.target(SIMPAC)
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out + ".new", "wb") as f:
                    f.write(db.encode())
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
        except (OSError, struct.error, ValueError) as e:
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
        lo, hi, step = teaminit.SALARY_LIMITS[teaminit.POUND]
        ttk.Label(box, text="Salaries are %s-%s (£%s-£%s). The game rounds a salary up to a "
                            "multiple of %s (£%s); the pound amount next to each is what the "
                            "game shows. In euros the step is 40,000 (€10,000) "
                            "(TEAMINIT_FORMAT.md)." % (
                                format(lo, ","), format(hi, ","),
                                format(teaminit.shown_money(lo), ","),
                                format(teaminit.shown_money(hi), ","), format(step, ","),
                                format(teaminit.shown_money(step), ",")),
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
                        pounds.configure(text="£%s" % format(teaminit.shown_money(
                            teaminit.salary_in_game(t.records[ri][k])), ","))
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


REGULATION = "PARAM/REGULATION.TBB"
CLUBRESULT = "PARAM/CLUBRESULT.TBB"
RULE_FIELDS = ("grade", "clubs", "unk04", "ban_yellows", "squad", "squad2", "foreigners", "subs")
RULE_LABELS = {"unk04": "+0x04", "ban_yellows": "ban at yellows", "squad2": "squad (copy)",
               "prize_kind": "prize kind", "win_bonus": "win bonus"}
RESULT_LABELS = {"kind": "shown as", "third_place": "third-place match", "clubs": "clubs"}
SLOT_NAMES = ("up1", "up2", "up3", "up4", "down1", "down2")
PRIZE_COLUMNS = 4


def pounds(value):
    """A regulation's money field as the game shows it in pounds."""
    return "£%s" % format(value * regulation.MONEY_UNIT // regulation.POUND, ",")


class RegulationsTab(Tab):
    """Match regulations, one row per schedule UID (REGULATION.TBB),
    through regulation.set_field and encode_file, as `regulation.py set`
    does, and how each schedule reports a final place (CLUBRESULT.TBB,
    through clubresult.set_field, as `clubresult.py set`). The schedules'
    names come from the schedule packs (regulation.uid_names)."""
    title = "Regulations"

    def __init__(self, app):
        super().__init__(app)
        self.rows = None
        self.results = None
        self.changes = {}           # (uid, field) -> value, in edit order
        self.result_changes = {}    # the same for CLUBRESULT.TBB
        self.current = None

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Name or UID").pack(side="left")
        self.find_var = tk.StringVar()
        find = ttk.Entry(bar, textvariable=self.find_var, width=22)
        find.pack(side="left", padx=(4, 12))
        find.bind("<Return>", lambda e: self.refresh_list())
        ttk.Button(bar, text="Search", command=self.refresh_list).pack(side="left")
        self.count_label = ttk.Label(bar, text="")
        self.count_label.pack(side="left", padx=12)
        ttk.Label(bar, text="Each schedule's rules, money and places "
                            "(DOC/REGULATION_FORMAT.md).", foreground="#555").pack(side="left")

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("uid", "name", "clubs")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("UID", "Schedule", "Clubs"), (50, 260, 50)):
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
            self.path = mod.source(REGULATION)
            self.buf, self.end, self.raw, self.rows = regulation.load(self.path)
            self.result_path = mod.source(CLUBRESULT)
            (self.result_buf, self.result_end, self.result_raw,
             self.results) = clubresult.load(self.result_path)
            # The schedule packs from the mod folder when the Season tab
            # has written them, as `leaguesize.py build --over` reads them.
            self.names = regulation.uid_names(os.path.join(mod.dat, "PARAM"),
                                              mod.target("PARAM"))
        except (ValueError, struct.error, OSError, StopIteration) as e:
            self.rows = None
            self.app.status("Couldn't load the regulations: %s" % e)
            messagebox.showerror("Regulations", "Couldn't load the regulations:\n%s" % e)
            return
        self.changes = {}
        self.result_changes = {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    def changed(self, what):
        """The Season tab rebuilt the schedules and wrote new club counts:
        read the file again and put any unsaved edits back on top (they
        never touch `clubs`), so a save here doesn't undo the counts."""
        if what != "schedules" or self.rows is None:
            return
        changes, result_changes = self.changes, self.result_changes
        self.load()
        if self.rows is None:
            return
        for (uid, name), value in changes.items():
            regulation.set_field(self.rows[uid], name, value)
        for (uid, name), value in result_changes.items():
            clubresult.set_field(self.results[uid], name, value)
        self.changes, self.result_changes = changes, result_changes
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        self.app.update_title()

    # the list

    def name(self, uid):
        return self.names.get(uid, "(no schedule)")

    def refresh_list(self):
        if self.rows is None:
            return
        find = self.find_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        n = 0
        for r in self.rows:
            if find and not (find == str(r.uid) or
                             (not find.isdigit() and find in self.name(r.uid).lower())):
                continue
            self.tree.insert("", "end", iid=str(r.uid), values=self.row(r),
                             tags=("edited",) if self.edited(r.uid) else ())
            n += 1
        self.count_label.configure(text="%d schedules" % n)

    def row(self, r):
        return (r.uid, self.name(r.uid), r["clubs"])

    def edited(self, uid):
        return any(u == uid for u, _ in list(self.changes) + list(self.result_changes))

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    # the detail panel

    def show(self, uid):
        self.current = uid
        r = self.rows[uid]
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="UID %d  %s" % (uid, self.name(uid)),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))

        frame = ttk.LabelFrame(box, text="Match rules")
        frame.pack(fill="x", padx=8, pady=6)
        for row, name in enumerate(RULE_FIELDS):
            self.field_row(frame, r, name, row)

        frame = ttk.LabelFrame(box, text="Money: the game shows the value × %s ÷ %d in pounds"
                               % (format(regulation.MONEY_UNIT, ","), regulation.POUND))
        frame.pack(fill="x", padx=8, pady=6)
        self.field_row(frame, r, "win_bonus", 0, money=True)
        self.field_row(frame, r, "prize_kind", 1)
        grid = ttk.Frame(frame)
        grid.grid(row=2, column=0, columnspan=3, sticky="w", padx=6, pady=(6, 4))
        ttk.Label(grid, text="Prize money by final position", foreground="#555").grid(
            row=0, column=0, columnspan=3 * PRIZE_COLUMNS, sticky="w")
        for i in range(regulation.PRIZES):
            row, col = 1 + i // PRIZE_COLUMNS, (i % PRIZE_COLUMNS) * 3
            beyond = i >= r["clubs"]
            ttk.Label(grid, text="%d" % (i + 1), foreground="#999" if beyond else "").grid(
                row=row, column=col, sticky="e", padx=(8, 4))
            name = "prize%d" % (i + 1)
            money = ttk.Label(grid, text="", foreground="#555", width=12)
            money.grid(row=row, column=col + 2, sticky="w", padx=(4, 8))

            def show_money(name=name, money=money):
                money.configure(text=pounds(r[name]))
            show_money()
            self.input(grid, r, name, show_money).grid(row=row, column=col + 1, sticky="w",
                                                       pady=1)

        frame = ttk.LabelFrame(box, text="Places: rank ranges counted from the top (up) or the "
                                         "bottom (down) of the table")
        frame.pack(fill="x", padx=8, pady=6)
        ttk.Label(frame, text="The game uses these to tell when a club has clinched or is in "
                              "a place. Which clubs really move next season is set in the "
                              "schedule packs, so change those to match. A count of -1 is "
                              "set by the host nation's UEFA rank; a count of 0 ends the list.",
                  foreground="#555", wraplength=900, justify="left").grid(
            row=0, column=0, columnspan=5, sticky="w", padx=6, pady=(2, 6))
        for col, text in enumerate(("slot", "count", "competition", "UID", "gives")):
            ttk.Label(frame, text=text, foreground="#555").grid(row=1, column=col, sticky="w",
                                                               padx=(6, 8))
        for row, slot in enumerate(SLOT_NAMES, 2):
            ttk.Label(frame, text=slot).grid(row=row, column=0, sticky="w", padx=(6, 8))
            gives = ttk.Label(frame, text="")
            gives.grid(row=row, column=4, sticky="w", padx=(0, 8))

            def show_gives(slot=slot, gives=gives):
                group = SLOT_NAMES[:4] if slot.startswith("up") else SLOT_NAMES[4:]
                read = dict(regulation.read_slots(r, group))
                gives.configure(text=regulation.slot_text(*read[slot]) if slot in read
                                else "(not read: comes after a count of 0)"
                                if r.slot(slot)[0] else "-")
            for col, part in enumerate(("count", "compe", "uid"), 1):
                self.input(frame, r, "%s_%s" % (slot, part), self.refresh_slots).grid(
                    row=row, column=col, sticky="w", padx=(0, 8), pady=1)
            show_gives()

        self.show_results(box, uid)
        self.fit_detail()

    def show_results(self, box, uid):
        """CLUBRESULT.TBB's row: how the results list shows a final place."""
        res = self.results[uid]
        frame = ttk.LabelFrame(box, text="Results: how a club's final place is shown "
                                         "(CLUBRESULT.TBB)")
        frame.pack(fill="x", padx=8, pady=6)
        for row, name in enumerate(("kind", "third_place", "clubs")):
            ttk.Label(frame, text=RESULT_LABELS[name]).grid(row=row, column=0, sticky="w",
                                                            padx=(6, 12), pady=2)
            choices = clubresult.edit_choices(name)
            if choices is None:
                w = ttk.Label(frame, text=str(res[name]), foreground="#777")
            else:
                text = dict(choices)
                w = value_input(frame, ("choice", [v for v, _ in choices]),
                                lambda v, text=text: text.get(v, str(v)), lambda n=name: res[n],
                                lambda t, revert, n=name: self.commit_result(res, n, t, revert))
            w.grid(row=row, column=1, sticky="w", pady=2)
            ttk.Label(frame, text=clubresult.DESCRIPTIONS.get(name, ""),
                      foreground="#555").grid(row=row, column=2, sticky="w", padx=(12, 6))
        if res["kind"] == 1:
            places = ", ".join("%d %s" % (p, clubresult.place_name(res, p))
                               for p in (1, 2, 3, 4, 5, 9, 17))
            ttk.Label(frame, text="Places read: " + places, foreground="#555",
                      wraplength=900, justify="left").grid(
                row=3, column=0, columnspan=3, sticky="w", padx=6, pady=(4, 2))

    def refresh_slots(self):
        """Redraw the page after a slot edit: every slot's text depends on
        the others (the list ends at a count of 0)."""
        self.frame.after_idle(lambda: self.show(self.current))

    def fit_detail(self):
        self.frame.update_idletasks()
        need = self.detail.inner.winfo_reqwidth() + 24
        have = self.detail.outer.winfo_width()
        if need > have > 1:
            pos = self.panes.sashpos(0)
            self.panes.sashpos(0, max(LIST_MIN, pos - (need - have)))

    def field_row(self, frame, r, name, row, money=False):
        ttk.Label(frame, text=RULE_LABELS.get(name, name)).grid(row=row, column=0, sticky="w",
                                                                padx=(6, 12), pady=2)
        cell = ttk.Frame(frame)
        cell.grid(row=row, column=1, sticky="w", pady=2)
        after = None
        if money:
            label = ttk.Label(cell, text="", foreground="#555")

            def after(label=label):
                label.configure(text=pounds(r[name]))
        self.input(cell, r, name, after).pack(side="left")
        if money:
            label.pack(side="left", padx=6)
            after()
        ttk.Label(frame, text=regulation.DESCRIPTIONS.get(name, ""), foreground="#555").grid(
            row=row, column=2, sticky="w", padx=(12, 6))

    def input(self, parent, r, name, after=None):
        rng = regulation.edit_range(name)
        if rng is None:
            return ttk.Label(parent, text=str(r[name]), foreground="#777")
        if name == "grade":
            spec = ("choice", list(range(rng[0], rng[1] + 1)))
        else:
            spec = ("range",) + rng
        return value_input(parent, spec, str, lambda: r[name],
                           lambda text, revert: self.commit(r, name, text, revert, after))

    # edits

    def commit(self, r, name, text, revert, after=None):
        what = "UID %d" % r.uid
        try:
            value = int(text)
        except ValueError:
            return self.refuse(what, "%s must be a number" % name, revert)
        lo, hi = regulation.edit_range(name)
        if not lo <= value <= hi:
            return self.refuse(what, "%s must be %d-%d" % (name, lo, hi), revert)
        names = (name,) + regulation.FOLLOWS.get(name, ())
        old = {n: r[n] for n in names}
        try:
            for n in names:
                regulation.set_field(r, n, value)
            problems = regulation.check(r)
            if problems:
                raise ValueError("; ".join(problems))
        except ValueError as e:
            for n, v in old.items():
                r[n] = v
            return self.refuse(what, str(e), revert)
        for n in names:
            self.changes.pop((r.uid, n), None)
            self.changes[r.uid, n] = value
        if after:
            after()
        if len(names) > 1:
            self.frame.after_idle(lambda: self.show(r.uid))     # the copies' labels
        self.tree.item(str(r.uid), values=self.row(r), tags=("edited",))
        self.app.status("%s: %s %d -> %d%s" % (what, name, old[name], value,
                                               " (and %s)" % ", ".join(names[1:])
                                               if len(names) > 1 else ""))
        self.app.update_title()
        return True

    def commit_result(self, res, name, text, revert):
        what = "UID %d" % res.uid
        try:
            old = clubresult.set_field(res, name, int(text))
        except ValueError as e:
            return self.refuse(what, str(e), revert)
        self.result_changes.pop((res.uid, name), None)
        self.result_changes[res.uid, name] = res[name]
        self.frame.after_idle(lambda: self.show(res.uid))     # the place names
        self.tree.item(str(res.uid), tags=("edited",))
        self.app.status("%s: %s %d -> %d" % (what, name, old, res[name]))
        self.app.update_title()
        return True

    def refuse(self, what, message, revert):
        revert()
        self.app.status("%s: %s" % (what, message))
        messagebox.showerror("Regulations", "%s: %s" % (what, message))
        return False

    # saving

    def dirty(self):
        return bool(self.changes or self.result_changes)

    def save(self):
        """Each changed file through its writer's encoder, logged as its
        own command."""
        if not self.dirty():
            return True
        mod = self.app.mod
        files = []
        if self.changes:
            files.append((REGULATION, self.path, "SRC/regulation.py", self.changes,
                          lambda: regulation.encode_file(self.buf, self.end, self.raw,
                                                         self.rows)))
        if self.result_changes:
            files.append((CLUBRESULT, self.result_path, "SRC/clubresult.py",
                          self.result_changes,
                          lambda: clubresult.encode_file(self.result_buf, self.result_end,
                                                         self.result_raw, self.results)))
        temps = []
        try:
            for target, _, _, _, encode in files:
                out = mod.target(target)
                temps.append((out + ".new", out))
                data = encode()
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with open(out + ".new", "wb") as f:
                    f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Regulations", "Can't save: %s" % e)
            return False
        replace_new(temps)
        cmds = []
        for (_, path, tool, changes, _), (new, _) in zip(files, temps):
            args, last = [], None
            for (uid, name), value in changes.items():
                if uid != last:
                    args.append(str(uid))
                    last = uid
                args.append("%s=%d" % (name, value))
            cmds.append(["python", tool, "set", quote(shown_path(path)),
                         quote(shown_path(new))] + args)
        n = len(self.changes) + len(self.result_changes)
        lines = log_lines("Regulations: %d changes" % n, cmds, temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (", ".join(shown_path(f) for _, f in temps), n))
        return True


TRAINING = "PARAM/TRAINING_LIST.TBB"
TRAINING_COLUMNS = 4        # value inputs per line of a row's page


class TrainingTab(Tab):
    """The training tables (TRAINING_LIST.TBB) through Training.set and
    training.encode_file, as `training.py set` does: a table, then a row
    (a practice, camp type, position, equipment item or growth type), then
    its values. The writer says which columns the code reads and which
    values each table allows (training.read_columns, edit_choices)."""
    title = "Training"

    def __init__(self, app):
        super().__init__(app)
        self.tr = None
        self.changes = {}           # (table, row, column) -> value, in edit order
        self.table = training.TABLES[0]
        self.current = None

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Table").pack(side="left")
        self.table_names = ["%d %s: %s" % (t.index, t.name, t.title) for t in training.TABLES]
        self.table_var = tk.StringVar(value=self.table_names[0])
        box = ttk.Combobox(bar, textvariable=self.table_var, values=self.table_names,
                           state="readonly", width=60)
        box.pack(side="left", padx=(4, 12))
        box.bind("<<ComboboxSelected>>", lambda e: self.pick_table())
        self.table_box = box
        ttk.Label(bar, text="Growth per ability, fatigue, bonuses and decline "
                            "(DOC/TRAINING_FORMAT.md).", foreground="#555").pack(side="left")

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        self.tree = ttk.Treeview(left, columns=("row",), show="headings", selectmode="browse")
        self.tree.heading("row", text="Row")
        self.tree.column("row", width=260)
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
        try:
            self.path = self.app.mod.source(TRAINING)
            self.buf, self.end, self.raw, self.tr = training.load(self.path)
        except (ValueError, struct.error, OSError) as e:
            self.tr = None
            self.app.status("Couldn't load the training tables: %s" % e)
            messagebox.showerror("Training", "Couldn't load the training tables:\n%s" % e)
            return
        self.changes = {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    # the list

    def pick_table(self):
        self.table = training.TABLES[self.table_names.index(self.table_var.get())]
        self.current = None
        self.detail.clear()
        self.refresh_list()

    def rows(self):
        t = self.table
        return range(t.first, t.first + t.rows)

    def row_label(self, row):
        t = self.table
        if t.name in ("group", "staff"):
            return "all abilities"
        name = t.row_name(row)
        if t.name in ("stadium", "clubhouse", "youthhouse"):
            name = "equipment %s" % name
        elif t.name == "camp":
            name = "camp type %s" % name
        elif t.name == "youth":
            name = "youth practice %s" % name
        return name

    def refresh_list(self):
        if self.tr is None:
            return
        self.tree.delete(*self.tree.get_children())
        t = self.table
        for row in self.rows():
            edited = any(k[0] == t.index and k[1] == row for k in self.changes)
            self.tree.insert("", "end", iid=str(row), values=(self.row_label(row),),
                             tags=("edited",) if edited else ())

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    # the detail panel

    def show(self, row):
        self.current = row
        t = self.table
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s: %s" % (t.name, self.row_label(row)),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        if t.name in ("team", "practice"):
            jp, _ = training.PRACTICE_NAMES[row]
            ttk.Label(box, text="Menu item %d (%s). Each value adds to that ability's growth; "
                                "fatigue is how tiring the practice is." % (row, jp),
                      foreground="#555").pack(anchor="w", padx=8)
        frame = ttk.LabelFrame(box, text=t.title)
        frame.pack(fill="x", padx=8, pady=6)
        readable = set(training.read_columns(t))
        for col in range(t.cols):
            r, c = divmod(col, TRAINING_COLUMNS)
            ttk.Label(frame, text=training.column_name(t, col)).grid(
                row=r, column=2 * c, sticky="w", padx=(8, 4), pady=1)
            if col in readable:
                w = self.input(frame, t, row, col)
            else:
                w = ttk.Label(frame, text="%d (not read)" % self.tr.get(t, row, col),
                              foreground="#777")
            w.grid(row=r, column=2 * c + 1, sticky="w", padx=(0, 12), pady=1)

    def input(self, parent, t, row, col):
        get = lambda: self.tr.get(t, row, col)
        apply = lambda text, revert: self.commit(t, row, col, text, revert)
        choices = training.edit_choices(t)
        if choices is not None:
            text = dict(choices)
            return value_input(parent, ("choice", [v for v, _ in choices]),
                               lambda v: text.get(v, str(v)), get, apply)
        return value_input(parent, ("range", t.lo, t.hi), str, get, apply)

    # edits

    def commit(self, t, row, col, text, revert):
        what = "%s %s, %s" % (t.name, self.row_label(row), training.column_name(t, col))
        try:
            old = self.tr.set(t, row, col, int(text))
        except ValueError as e:
            revert()
            self.app.status("%s: %s" % (what, e))
            messagebox.showerror("Training", "%s: %s" % (what, e))
            return False
        value = self.tr.get(t, row, col)
        self.changes.pop((t.index, row, col), None)
        self.changes[t.index, row, col] = value
        self.tree.item(str(row), tags=("edited",))
        self.app.status("%s: %d -> %d" % (what, old, value))
        self.app.update_title()
        return True

    # saving

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(TRAINING)
        temps = [(out + ".new", out)]
        try:
            data = training.encode_file(self.buf, self.end, self.raw, self.tr)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Training", "Can't save: %s" % e)
            return False
        replace_new(temps)
        args, last = [], None
        for (index, row, col), value in self.changes.items():
            t = training.TABLES[index]
            if (index, row) != last:
                args += [t.name, str(row)]
                last = (index, row)
            args.append("%s=%d" % (training.column_arg(t, col), value))
        cmd = ["python", "SRC/training.py", "set", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + args
        n = len(self.changes)
        lines = log_lines("Training: %d changes" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (shown_path(out), n))
        return True


CAMP_LIST = "PARAM/CAMP_LIST.TBB"
CAMP_FIELDS = ("city", "nation", "region", "type", "level", "event_only", "unk0a")
CAMP_LABELS = {"event_only": "event only", "unk0a": "+0x0a"}


class CampsTab(Tab):
    """The training camps (CAMP_LIST.TBB) through camp.set_field's checks
    and camp.encode_file, as `camp.py set` does. The type, level and
    event-only flag are edited (camp.edit_range); the rest, the clubs of
    the camp's area and its description (CAMP_EXPLANE.TBB, message
    category 570) are shown.
    Names come from MES.PAC (cities, category 961; clubs, category 3)."""
    title = "Camps"

    def __init__(self, app):
        super().__init__(app)
        self.camps = None
        self.changes = {}           # (city, field) -> value, in edit order
        self.current = None

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Town").pack(side="left")
        self.find_var = tk.StringVar()
        find = ttk.Entry(bar, textvariable=self.find_var, width=22)
        find.pack(side="left", padx=(4, 12))
        find.bind("<Return>", lambda e: self.refresh_list())
        ttk.Button(bar, text="Search", command=self.refresh_list).pack(side="left")
        self.count_label = ttk.Label(bar, text="")
        self.count_label.pack(side="left", padx=12)
        ttk.Label(bar, text="The training camps (DOC/CAMP_FORMAT.md). The LMASTER Mod fixes the "
                            "camp types and seven English towns when it builds a disc.",
                  foreground="#555").pack(side="left")

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("city", "name", "type")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("City", "Town", "Type"), (50, 200, 50)):
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
            self.path = mod.source(CAMP_LIST)
            self.buf, self.end, self.raw, self.camps = camp.load_list(self.path)
            self.explane = dict(camp.load_explane(mod.source("PARAM/" + camp.EXPLANE_FILE)))
            mes = mod.source(MES)
            self.towns = camp.messages(mes, camp.CITY_NAMES)
            self.texts = camp.messages(mes, camp.CAMP_MESSAGES)
            self.clubs = {rid - initteam.TEAM_NAME_BASE: t for rid, t in
                          camp.messages(mes, initteam.TEAM_NAME_CATEGORY).items()}
        except (ValueError, struct.error, OSError) as e:
            self.camps = None
            self.app.status("Couldn't load the camps: %s" % e)
            messagebox.showerror("Camps", "Couldn't load the camps:\n%s" % e)
            return
        self.by_city = {c["city"]: c for c in self.camps}
        self.changes = {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    # the list

    def town(self, city):
        return self.towns.get(city, "")

    def refresh_list(self):
        if self.camps is None:
            return
        find = self.find_var.get().strip().lower()
        self.tree.delete(*self.tree.get_children())
        n = 0
        for c in sorted(self.camps, key=lambda c: self.town(c["city"])):
            if find and find not in self.town(c["city"]).lower() and find != str(c["city"]):
                continue
            self.tree.insert("", "end", iid=str(c["city"]),
                             values=(c["city"], self.town(c["city"]), c["type"]),
                             tags=("edited",) if any(k[0] == c["city"] for k in self.changes)
                             else ())
            n += 1
        self.count_label.configure(text="%d camps" % n)

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    # the detail panel

    def show(self, city):
        self.current = city
        c = self.by_city[city]
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s (city %d)" % (self.town(city), city),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        text = self.texts.get(self.explane.get(city), "")
        ttk.Label(box, text=text or "(no description for this town in CAMP_EXPLANE)",
                  foreground="#555", wraplength=640, justify="left").pack(anchor="w", padx=8)
        frame = ttk.LabelFrame(box, text="The camp")
        frame.pack(fill="x", padx=8, pady=6)
        for row, name in enumerate(CAMP_FIELDS):
            ttk.Label(frame, text=CAMP_LABELS.get(name, name)).grid(
                row=row, column=0, sticky="w", padx=(6, 12), pady=2)
            rng = camp.edit_range(name)
            if rng is None:
                w = ttk.Label(frame, text=str(c[name]), foreground="#777")
            else:
                w = value_input(frame, ("range",) + rng, str, lambda n=name: c[n],
                                lambda t, revert, n=name: self.commit(c, n, t, revert))
            w.grid(row=row, column=1, sticky="w", pady=2)
            ttk.Label(frame, text=camp.DESCRIPTIONS.get(name, ""), foreground="#555").grid(
                row=row, column=2, sticky="w", padx=(12, 6))
        self.trains = ttk.Label(box, text="", foreground="#555", wraplength=640, justify="left")
        self.trains.pack(anchor="w", padx=8, pady=(0, 6))
        self.show_training(c)
        clubs = [club for town, club in camp.pairs(self.raw[1].data) if town == city]
        ttk.Label(box, text="Clubs of the area (not edited): " + ", ".join(
            "%s" % self.clubs.get(t, t) for t in clubs), foreground="#555",
            wraplength=640, justify="left").pack(anchor="w", padx=8, pady=(0, 8))

    def show_training(self, c):
        """What the camp trains, from the Training tab's table 10 (edits
        included): the row the retail game reads and the one with the fix."""
        tr = self.app.training.tr
        if tr is None:
            return
        t = training.BY_NAME["camp"]
        lines = []
        for fixed, what in ((True, "with the LMASTER camp-types fix"), (False, "retail")):
            row = camp.training_row(c["type"], fixed)
            if row is None:
                lines.append("%s: past the training table" % what)
                continue
            vals = sorted(((tr.get(t, row, col), col) for col in range(training.ABILITIES)),
                          reverse=True)[:6]
            lines.append("%s, row %d: %s" % (what, row, ", ".join(
                "%s %d" % (training.column_name(t, col), v) for v, col in vals if v)))
        self.trains.configure(text="Trains most: " + "; ".join(lines))

    # edits

    def commit(self, c, name, text, revert):
        what = "%s (city %d)" % (self.town(c["city"]), c["city"])
        try:
            value = int(text)
        except ValueError:
            return self.refuse("%s: %s must be a number" % (what, name), revert)
        lo, hi = camp.edit_range(name)
        if not lo <= value <= hi:
            return self.refuse("%s: %s must be %d-%d" % (what, name, lo, hi), revert)
        old = c[name]
        c[name] = value
        self.changes.pop((c["city"], name), None)
        self.changes[c["city"], name] = value
        self.tree.item(str(c["city"]), values=(c["city"], self.town(c["city"]), c["type"]),
                       tags=("edited",))
        self.show_training(c)
        self.app.status("%s: %s %d -> %d" % (what, name, old, value))
        self.app.update_title()
        return True

    def refuse(self, message, revert):
        revert()
        self.app.status(message)
        messagebox.showerror("Camps", message)
        return False

    # saving

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(CAMP_LIST)
        temps = [(out + ".new", out)]
        try:
            data = camp.encode_file(self.buf, self.end, self.raw, self.camps)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Camps", "Can't save: %s" % e)
            return False
        replace_new(temps)
        args, last = [], None
        for (city, name), value in self.changes.items():
            if city != last:
                args.append(str(city))
                last = city
            args.append("%s=%d" % (name, value))
        cmd = ["python", "SRC/camp.py", "set", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + args
        n = len(self.changes)
        lines = log_lines("Camps: %d changes" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (shown_path(out), n))
        return True


FORMSET = "PARAM/" + formset.FILE
FORMSET_CATEGORY = 492      # setting labels 0-6, set names 10001 + row, descriptions 20001 + row


class TacticsTab(Tab):
    """The tactics screen's eight national presets (TACTICS_FORMATION_SET.TBB)
    through formset.set_field and formset.encode_file, as `formset.py set`
    does: seven team tactics and a formation each, in the ranges
    formset.edit_spec gives. The labels, names and descriptions come from
    MES.PAC (category 492). Build disc's --copies carries the file into the
    PRELOAD/TACTICS* packs."""
    title = "Tactics"

    def __init__(self, app):
        super().__init__(app)
        self.rows = None
        self.changes = {}           # (row, field) -> value, in edit order
        self.current = None

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="The tactics screen's Set Formation presets (DOC/PARAM_DIR.md). The "
                            "retail sets use 1-5 (Brazil's Attacking 6); the screen's own limits "
                            "aren't traced.", foreground="#555").pack(side="left")

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("row", "name", "formation")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("Row", "Set", "Formation"), (40, 160, 100)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, stretch=c == "name")
        self.tree.tag_configure("edited", foreground="#b03000")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=1)
        self.detail = Scrolled(panes)
        panes.add(self.detail.outer, weight=3)

    def load(self, done=None):
        mod = self.app.mod
        try:
            self.path = mod.source(FORMSET)
            self.buf, self.end, self.raw, self.rows = formset.load(self.path)
            self.texts = camp.messages(mod.source(MES), FORMSET_CATEGORY)
        except (ValueError, struct.error, OSError) as e:
            self.rows = None
            self.app.status("Couldn't load the tactics presets: %s" % e)
            messagebox.showerror("Tactics", "Couldn't load the tactics presets:\n%s" % e)
            return
        self.changes = {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    def name(self, r):
        return (self.texts.get(10001 + r) or
                (formset.SETS[r] if r < len(formset.SETS) else "row %d" % r)).strip()

    def formation(self, v):
        f = formset.formations()
        return "%d %s" % (v, f[v] if v < len(f) else "?")

    def refresh_list(self):
        if self.rows is None:
            return
        self.tree.delete(*self.tree.get_children())
        for r, row in enumerate(self.rows):
            self.tree.insert("", "end", iid=str(r), values=(r, self.name(r), self.formation(row[7])),
                             tags=("edited",) if any(k[0] == r for k in self.changes) else ())

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    def show(self, r):
        self.current = r
        row = self.rows[r]
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s (row %d)" % (self.name(r), r),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(box, text=(self.texts.get(20001 + r) or "").strip(), foreground="#555",
                  wraplength=640, justify="left").pack(anchor="w", padx=8)
        frame = ttk.LabelFrame(box, text="The preset")
        frame.pack(fill="x", padx=8, pady=6)
        for k, name in enumerate(formset.FIELDS):
            text = self.texts.get(k) if name != "formation" else "Formation"
            ttk.Label(frame, text=text or name).grid(row=k, column=0, sticky="w", padx=(6, 12),
                                                    pady=2)
            w = value_input(frame, formset.edit_spec(name),
                            self.formation if name == "formation" else str,
                            lambda k=k: row[k],
                            lambda t, revert, n=name: self.commit(r, n, t, revert))
            w.grid(row=k, column=1, sticky="w", pady=2)

    def commit(self, r, name, text, revert):
        what = "%s (row %d)" % (self.name(r), r)
        try:
            old = formset.set_field(self.rows[r], name, int(text))
        except ValueError as e:
            revert()
            message = "%s: %s" % (what, e if text.strip() else "%s must be a number" % name)
            self.app.status(message)
            messagebox.showerror("Tactics", message)
            return False
        self.changes.pop((r, name), None)
        self.changes[r, name] = self.rows[r][formset.FIELDS.index(name)]
        self.tree.item(str(r), values=(r, self.name(r), self.formation(self.rows[r][7])),
                       tags=("edited",))
        self.app.status("%s: %s %d -> %d" % (what, name, old, self.changes[r, name]))
        self.app.update_title()
        return True

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(FORMSET)
        temps = [(out + ".new", out)]
        try:
            data = formset.encode_file(self.buf, self.end, self.raw, self.rows)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Tactics", "Can't save: %s" % e)
            return False
        replace_new(temps)
        args = []
        for r in sorted({r for r, _ in self.changes}):
            args.append(str(r))
            args += ["%s=%d" % (n, v) for (row, n), v in self.changes.items() if row == r]
        cmd = ["python", "SRC/formset.py", "set", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + args
        n = len(self.changes)
        lines = log_lines("Tactics: %d changes" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (shown_path(out), n))
        return True


TOUR = "PARAM/" + tour.FILE


class ToursTab(Tab):
    """The clubs a tour can play, by region (TOUR_LIST.TBB), through
    tour.set_pair and tour.encode_file, as `tour.py set` does. Each pair
    is a region and a club; changing the region moves the club to that
    region's list. Club names come from MES.PAC (category 3); the region
    names are tour.REGION_NAMES, read from the clubs (not confirmed)."""
    title = "Tours"

    def __init__(self, app):
        super().__init__(app)
        self.pairs = None
        self.changes = {}           # pair -> (region, club), in edit order
        self.current = None

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="The tour opponents by region (DOC/PARAM_DIR.md). The screen takes "
                            "up to %d clubs a region, and the file keeps its number of pairs."
                            % tour.SLOTS, foreground="#555").pack(side="left")

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("region", "name", "clubs")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("Region", "Area", "Clubs"), (50, 200, 50)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, stretch=c == "name")
        self.tree.tag_configure("edited", foreground="#b03000")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=1)
        self.detail = Scrolled(panes)
        panes.add(self.detail.outer, weight=3)

    def load(self, done=None):
        mod = self.app.mod
        try:
            self.path = mod.source(TOUR)
            self.buf, self.end, self.raw, self.pairs = tour.load(self.path)
            self.clubs = tour.club_names(mod.source(MES))
        except (ValueError, struct.error, OSError) as e:
            self.pairs = None
            self.app.status("Couldn't load the tour list: %s" % e)
            messagebox.showerror("Tours", "Couldn't load the tour list:\n%s" % e)
            return
        self.changes = {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    def club(self, c):
        return "%d %s" % (c, self.clubs.get(c, ""))

    def region(self, r):
        return "%d %s" % (r, tour.region_name(r))

    def refresh_list(self):
        if self.pairs is None:
            return
        self.tree.delete(*self.tree.get_children())
        edited = {self.pairs[k][0] for k in self.changes}
        for r in range(tour.REGIONS):
            self.tree.insert("", "end", iid=str(r), values=(
                r, tour.region_name(r), sum(p[0] == r for p in self.pairs)),
                tags=("edited",) if r in edited else ())

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    def show(self, region):
        self.current = region
        self.detail.clear()
        box = self.detail.inner
        mine = [k for k, p in enumerate(self.pairs) if p[0] == region]
        ttk.Label(box, text="%s (region %d)" % (tour.region_name(region), region),
                  font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(box, text="%d of %d clubs, in the order the screen lists them" % (
            len(mine), tour.SLOTS), foreground="#555").pack(anchor="w", padx=8)
        frame = ttk.LabelFrame(box, text="The pairs: club and region")
        frame.pack(fill="x", padx=8, pady=6)
        regions = ("choice", list(range(tour.REGIONS)))
        clubs = ("choice", list(range(1, tour.CLUBS)))
        for row, k in enumerate(mine):
            ttk.Label(frame, text="pair %d" % k).grid(row=row, column=0, sticky="w",
                                                      padx=(6, 12), pady=2)
            value_input(frame, clubs, self.club, lambda k=k: self.pairs[k][1],
                        lambda t, revert, k=k: self.commit(k, self.pairs[k][0], t, revert)
                        ).grid(row=row, column=1, sticky="w", pady=2)
            value_input(frame, regions, self.region, lambda k=k: self.pairs[k][0],
                        lambda t, revert, k=k: self.commit(k, t, self.pairs[k][1], revert)
                        ).grid(row=row, column=2, sticky="w", padx=(12, 6), pady=2)

    def commit(self, k, region, club, revert):
        try:
            old = tour.set_pair(self.pairs, k, int(region), int(club))
        except ValueError as e:
            revert()
            message = "pair %d: %s" % (k, e)
            self.app.status(message)
            messagebox.showerror("Tours", message)
            return False
        self.changes.pop(k, None)
        self.changes[k] = tuple(self.pairs[k])
        self.app.status("pair %d: %s in %s -> %s in %s" % (
            k, self.club(old[1]), tour.region_name(old[0]), self.club(self.pairs[k][1]),
            tour.region_name(self.pairs[k][0])))
        self.refresh_list()
        if old[0] != self.pairs[k][0]:
            # The pair leaves this region's list; redraw it once the
            # drop-down's own event is done.
            self.frame.after_idle(lambda: self.show(self.current))
        self.app.update_title()
        return True

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(TOUR)
        temps = [(out + ".new", out)]
        try:
            data = tour.encode_file(self.buf, self.end, self.raw, self.pairs)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Tours", "Can't save: %s" % e)
            return False
        replace_new(temps)
        cmd = ["python", "SRC/tour.py", "set", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + [
            "%d=%d:%d" % (k, r, c) for k, (r, c) in self.changes.items()]
        n = len(self.changes)
        lines = log_lines("Tours: %d pairs" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d pairs" % (shown_path(out), n))
        return True


PSC = "PARAM/PSCCOMMON.PAC"
COMMENT_KINDS = {
    "weight": "how much each ability counts for each of the 9 position kinds (each retail "
              "column adds up to 17, and the sum is divided by 17)",
    "message": "message numbers in category %d; click a cell to see its text",
    "band": "the bands of the best group's value: {low, high, band}",
}


class CommentsTab(Tab):
    """The detail screens' comment lines: the SQT1 data tables of the
    PSCCOMMON.PAC scripts the game runs (sqb.COMMENT_SCRIPTS), through
    sqb.set_table_values and sqb.set_pack_values, as `sqb.py settable`
    does. Pick a page, then edit its tables' cells in the range their
    element size allows; a message number's text shows from MES.PAC.
    Build disc's --copies carries the pack into PRELOAD/STATIONFILE.PAC."""
    title = "Comments"

    def __init__(self, app):
        super().__init__(app)
        self.data = None
        self.changes = {}           # (entry, table, row, element) -> value, in edit order
        self.current = 0

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Page").pack(side="left")
        self.page_var = tk.StringVar()
        self.page = ttk.Combobox(bar, textvariable=self.page_var, state="readonly", width=28,
                                 values=[s[1] for s in sqb.COMMENT_SCRIPTS])
        self.page.pack(side="left", padx=(4, 12))
        self.page.bind("<<ComboboxSelected>>", lambda e: self.show(self.page.current()))
        ttk.Label(bar, text="The detail screens' comment lines (DOC/SQB_FORMAT.md, "
                            "\"The detail-screen comments\").", foreground="#555").pack(side="left")
        self.cell_var = tk.StringVar()
        ttk.Label(self.frame, textvariable=self.cell_var, foreground="#0050a0", wraplength=1000,
                  justify="left").pack(fill="x", padx=8)
        self.detail = Scrolled(self.frame)
        self.detail.outer.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def load(self, done=None):
        mod = self.app.mod
        try:
            self.path = mod.source(PSC)
            with open(self.path, "rb") as f:
                self.data = f.read()
            self.entries = sqb.pack_scripts(self.path)
            self.values, self.shapes = {}, {}
            for entry, _, _, _ in sqb.COMMENT_SCRIPTS:
                off, size = self.entries[entry]
                blob = self.data[off:off + size]
                self.shapes[entry] = sqb.sqt_shapes(blob)
                self.values[entry] = {(t, r, c): v for t, r, c, v in sqb.table_cells(blob)}
            mes = mod.source(MES)
            self.texts = {cat: camp.messages(mes, cat)
                          for cat in {s[2] for s in sqb.COMMENT_SCRIPTS}}
        except (KeyError, ValueError, struct.error, OSError) as e:
            self.data = None
            self.app.status("Couldn't load the comment scripts: %s" % e)
            messagebox.showerror("Comments", "Couldn't load the comment scripts:\n%s" % e)
            return
        self.changes = {}
        self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    def script(self, entry):
        return next(s for s in sqb.COMMENT_SCRIPTS if s[0] == entry)

    def show(self, i):
        self.current = i
        self.page.current(i)
        entry, page, category, tables = sqb.COMMENT_SCRIPTS[i]
        self.cell_var.set("")
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s (%s)" % (page, entry), font=self.app.title_font).pack(
            anchor="w", padx=8, pady=(8, 2))
        for t, (rows, width, lo, hi) in sorted(self.shapes[entry].items()):
            kind, row_label, col_label = tables[t]
            about = COMMENT_KINDS[kind] % category if kind == "message" else COMMENT_KINDS[kind]
            frame = ttk.LabelFrame(box, text="Table %d: %s" % (t, about))
            frame.pack(anchor="w", padx=8, pady=6)
            for c in range(width):
                ttk.Label(frame, text=col_label(c), foreground="#555").grid(
                    row=0, column=c + 1, padx=1)
            for r in range(rows):
                ttk.Label(frame, text=row_label(r)).grid(row=r + 1, column=0, sticky="w",
                                                         padx=(6, 8))
                for c in range(width):
                    key = (t, r, c)
                    w = value_input(frame, ("range", lo, hi), str,
                                    lambda key=key: self.values[entry][key],
                                    lambda text, revert, key=key: self.commit(entry, key, text,
                                                                              revert))
                    w.grid(row=r + 1, column=c + 1, padx=1, pady=1)
                    w.bind("<FocusIn>", lambda e, key=key: self.show_cell(entry, key))

    def show_cell(self, entry, key):
        _, page, category, tables = self.script(entry)
        t, r, c = key
        kind, row_label, col_label = tables[t]
        v = self.values[entry][key]
        text = "%s, table %d, %s, %s: %d" % (page, t, row_label(r), col_label(c), v)
        if kind == "message":
            text += "  =  %s" % (self.texts[category].get(v) or "(no message %d in category %d)"
                                 % (v, category)).strip()
        self.cell_var.set(text)

    def commit(self, entry, key, text, revert):
        off, size = self.entries[entry]
        try:
            value = int(text)
            # Checks the cell and its range; save writes every change at once.
            sqb.set_table_values(self.data[off:off + size], [key + (value,)])
        except ValueError as e:
            revert()
            message = "%s %s: %s" % (self.script(entry)[1], key,
                                     e if text.strip() else "give a number")
            self.app.status(message)
            messagebox.showerror("Comments", message)
            return False
        old = self.values[entry][key]
        self.values[entry][key] = value
        self.changes.pop((entry,) + key, None)
        self.changes[(entry,) + key] = value
        self.app.status("%s table %d row %d element %d: %d -> %d" % (
            (self.script(entry)[1],) + key + (old, value)))
        self.show_cell(entry, key)
        self.app.update_title()
        return True

    def edits(self):
        """{entry: [(table, row, element, value)]}, in edit order."""
        out = {}
        for (entry, t, r, c), v in self.changes.items():
            out.setdefault(entry, []).append((t, r, c, v))
        return out

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(PSC)
        temps = [(out + ".new", out)]
        edits = self.edits()
        try:
            data = sqb.set_pack_values(self.data, self.entries, edits)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Comments", "Can't save: %s" % e)
            return False
        replace_new(temps)
        args = []
        for entry, cells in edits.items():
            args.append(entry)
            args += ["%d:%d:%d=%d" % cell for cell in cells]
        cmd = ["python", "SRC/sqb.py", "settable", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + args
        n = len(self.changes)
        lines = log_lines("Comments: %d cells" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d cells" % (shown_path(out), n))
        return True


FACILITY_HELP = {
    plrcommon.MONEY: "the game charges a build cost x the business cycle (75-125%) x any "
                     "sponsor discount; upkeep is monthly",
    plrcommon.TURNS: "turns (8 a month)",
    plrcommon.CAPACITY: "seats",
}
STORED_PER_POUND = 6


class FacilitiesTab(Tab):
    """The facility records of PLRESOURCECOMMON.PAC entry 0 through
    plrcommon.set_field and plrcommon.encode, as `plrcommon.py set` does:
    a table, then a record, then its build costs, upkeep, build times and
    (stadiums) capacities, in the ranges plrcommon.edit_spec gives. Money is
    the stored unit, shown in pounds beside it."""
    title = "Facilities"

    def __init__(self, app):
        super().__init__(app)
        self.tables = None
        self.changes = {}           # (table key, record, field) -> value, in edit order
        self.key = sorted(plrcommon.FACILITY)[0]
        self.current = None

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Table").pack(side="left")
        self.keys = sorted(plrcommon.FACILITY)
        self.table_names = ["%d.%d %s" % (k + (plrcommon.FACILITY[k][0],)) for k in self.keys]
        self.table_var = tk.StringVar(value=self.table_names[0])
        box = ttk.Combobox(bar, textvariable=self.table_var, values=self.table_names,
                           state="readonly", width=34)
        box.pack(side="left", padx=(4, 12))
        box.bind("<<ComboboxSelected>>", lambda e: self.pick_table())
        self.table_box = box
        ttk.Label(bar, text="Build costs, upkeep, build times and stadium capacities "
                            "(DOC/PLRESOURCECOMMON_FORMAT.md, DOC/ECONOMY.md).",
                  foreground="#555").pack(side="left")

        panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("record", "cost", "time")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, head, width in zip(cols, ("Record", "Build cost", "Build time"), (70, 130, 80)):
            self.tree.heading(c, text=head)
            self.tree.column(c, width=width, anchor="w" if c == "record" else "e")
        self.tree.tag_configure("edited", foreground="#b03000")
        sb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.select())
        panes.add(left, weight=1)
        self.detail = Scrolled(panes)
        panes.add(self.detail.outer, weight=2)

    # loading

    def load(self, done=None):
        try:
            self.path = self.app.mod.source(COMMON)
            with open(self.path, "rb") as f:
                self.data = f.read()
            _, entries = plrcommon.load_bytes(self.data, self.path)
            self.tables = [bytearray(t) for t in entries[0]]
        except (ValueError, struct.error, OSError) as e:
            self.tables = None
            self.app.status("Couldn't load the facility records: %s" % e)
            messagebox.showerror("Facilities", "Couldn't load the facility records:\n%s" % e)
            return
        self.changes = {}
        self.refresh_list()
        if self.current is not None:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    # the list

    def pick_table(self):
        self.key = self.keys[self.table_names.index(self.table_var.get())]
        self.current = None
        self.detail.clear()
        self.refresh_list()

    def count(self):
        return len(self.tables[self.key[1]]) // plrcommon.FACILITY[self.key][2]

    def first_time(self):
        return "time0" if self.key == (0, 7) else "time"

    def row(self, record):
        cost = plrcommon.get_field(self.tables, self.key, record, "cost")
        time_ = plrcommon.get_field(self.tables, self.key, record, self.first_time())
        return (record, money_text(cost) if cost > 0 else "-", time_ if time_ >= 0 else "-")

    def refresh_list(self):
        if self.tables is None:
            return
        self.tree.delete(*self.tree.get_children())
        for record in range(self.count()):
            edited = any(k[:2] == (self.key, record) for k in self.changes)
            self.tree.insert("", "end", iid=str(record), values=self.row(record),
                             tags=("edited",) if edited else ())

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(int(sel[0]))

    # the detail panel

    def show(self, record):
        self.current = record
        name = plrcommon.FACILITY[self.key][0]
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="%s, record %d" % (name, record), font=self.app.title_font).pack(
            anchor="w", padx=8, pady=(8, 2))
        if plrcommon.get_field(self.tables, self.key, record, self.first_time()) <= 0:
            ttk.Label(box, text="Build time 0 or none: a level clubs start with, so its build "
                                "cost is never charged.", foreground="#555").pack(
                anchor="w", padx=8)
        frame = ttk.Frame(box)
        frame.pack(anchor="w", padx=8, pady=6)
        self.pound_labels = {}
        fields = sorted(plrcommon.FACILITY[self.key][4].items())
        for r, (_, (fname, kind)) in enumerate(fields):
            ttk.Label(frame, text=fname.replace("_", " ")).grid(row=r, column=0, sticky="w",
                                                                padx=(0, 8), pady=1)
            self.input(frame, record, fname).grid(row=r, column=1, sticky="w", pady=1)
            extra = ttk.Label(frame, foreground="#555")
            extra.grid(row=r, column=2, sticky="w", padx=(8, 0))
            if kind == plrcommon.MONEY:
                self.pound_labels[fname] = extra
            lo, hi = plrcommon.edit_spec(self.key, fname)[1:]
            ttk.Label(frame, text="%d-%d %s" % (lo, hi, "stored unit" if kind == plrcommon.MONEY
                                                  else FACILITY_HELP[kind]),
                      foreground="#777").grid(row=r, column=3, sticky="w", padx=(12, 0))
        self.update_pounds(record)
        ttk.Label(box, text="Money is in the game's stored unit (£1 = 6, €1 = 4); "
                            + FACILITY_HELP[plrcommon.MONEY] + ".", foreground="#555",
                  wraplength=700, justify="left").pack(anchor="w", padx=8, pady=(4, 8))

    def update_pounds(self, record):
        for fname, label in self.pound_labels.items():
            v = plrcommon.get_field(self.tables, self.key, record, fname)
            label.configure(text=money_text(v) if v >= 0 else "")

    def input(self, parent, record, fname):
        get = lambda: plrcommon.get_field(self.tables, self.key, record, fname)
        apply = lambda text, revert: self.commit(record, fname, text, revert)
        return value_input(parent, plrcommon.edit_spec(self.key, fname), str, get, apply)

    # edits

    def commit(self, record, fname, text, revert):
        key = self.key
        what = "%s %d, %s" % (plrcommon.FACILITY[key][0], record, fname)
        try:
            old = plrcommon.set_field(self.tables, key, record, fname, int(text))
        except ValueError as e:
            revert()
            self.app.status("%s: %s" % (what, e))
            messagebox.showerror("Facilities", "%s: %s" % (what, e))
            return False
        value = plrcommon.get_field(self.tables, key, record, fname)
        self.changes.pop((key, record, fname), None)
        self.changes[key, record, fname] = value
        self.tree.item(str(record), values=self.row(record), tags=("edited",))
        self.update_pounds(record)
        self.app.status("%s: %d -> %d" % (what, old, value))
        self.app.update_title()
        return True

    # saving

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(COMMON)
        temps = [(out + ".new", out)]
        try:
            data = plrcommon.encode(self.data, self.tables)
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, struct.error, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Facilities", "Can't save: %s" % e)
            return False
        replace_new(temps)
        args = ["%d.%d:%d:%s=%d" % (key + (record, fname, value))
                for (key, record, fname), value in self.changes.items()]
        cmd = ["python", "SRC/plrcommon.py", "set", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + args
        n = len(self.changes)
        lines = log_lines("Facilities: %d changes" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (shown_path(out), n))
        return True


def money_text(value):
    """A stored money value in pounds."""
    return "£%s" % format(value // STORED_PER_POUND, ",")


UNIFORM_LIST = "PLAYER/UNIFORM_LIST.TBB"
UNIFORM_GK = "PLAYER/UNIFORM_GK.TBB"
PLPACK = {"home": "PLAYER/PLPACK_HOME", "away": "PLAYER/PLPACK_AWAY"}   # .HED and .PAC


def colour_input(parent, swatches, get, apply, values=None):
    """A kit colour: a drop-down of the 96 colours by name (or `values`,
    where 0xff is "off") and a swatch of the chosen one (entry 128 of its
    palette)."""
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
    value_input(frame, ("choice", values or list(range(uniform.COLOURS))),
                lambda v: "off" if v == uniform.NO_COLOUR else uniform.colour_label(v), get,
                commit).pack(side="left")
    paint()
    return frame


class KitsTab(Tab):
    """Club kits (UNIFORM_LIST.TBB), the keeper kits made from them
    (UNIFORM_GK.TBB) and the licensed clubs' kit descriptors, through
    uniform.set_row_field, apply_gk_edit and set_descriptor, as `uniform.py
    set`, `setgk`, `setexe` and `setlicence` do."""
    title = "Kits"

    def __init__(self, app):
        super().__init__(app)
        self.blob = None
        self.changes = {}           # (team, field name) -> value, in edit order
        self.gk_changes = {}        # field name -> value
        self.lic_changes = {}       # (side, licence, field) -> value
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
                self.sles_path = mod.disc_source(SLES)
                self.licence_of, elf = uniform.licence_table(self.sles_path)
                # The descriptors as the game draws them: the executable's
                # copy (DOC/UNIFORM_FORMAT.md#the-descriptor). Saves write
                # the pack's copy too, so the two stay equal.
                self.desc = {}
                for side in ("home", "away"):
                    for n in range(uniform.LICENCES):
                        b = uniform.exe_descriptor_base(self.sles_path, elf, side, n)
                        self.desc[side, n] = bytearray(elf.data[b:b + uniform.DESCRIPTOR_SIZE])
            except (OSError, ValueError, struct.error):
                self.licence_of, self.desc = {}, {}
            self.licensed = set(self.licence_of)
        except (ValueError, struct.error, OSError) as e:
            self.app.status("Couldn't load the kits: %s" % e)
            messagebox.showerror("Kits", "Couldn't load the kits:\n%s" % e)
            return
        self.rows = {}              # team -> unpacked fields, edits included
        self.changes, self.gk_changes, self.lic_changes = {}, {}, {}
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
                             tags=("edited",) if self.edited(team) else ())
            n += 1
        self.count_label.configure(text="%d clubs" % n)

    def edited(self, team):
        return any(t == team for t, _ in self.changes) or any(
            n == self.licence_of.get(team) for _, n, _ in self.lic_changes)

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
                                "textures (PLPACK_HOME/AWAY), not from the fields further down. "
                                "The descriptor below gives the numbers, name, collar and "
                                "captain mark (DOC/UNIFORM_FORMAT.md#licensed-kits).",
                      foreground="#a05000", wraplength=700, justify="left").pack(anchor="w", padx=8)
            if self.desc:
                self.licence_frames(box, self.licence_of[team])
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

    def licence_frames(self, box, licence):
        for side in ("home", "away"):
            frame = ttk.LabelFrame(box, text="Licensed %s kit descriptor (licence %d)"
                                             % (side, licence))
            frame.pack(fill="x", padx=8, pady=6)
            ttk.Label(frame, text="outfield kit", foreground="#555").grid(row=0, column=1,
                                                                         sticky="w")
            ttk.Label(frame, text="keeper kit", foreground="#555").grid(row=0, column=2,
                                                                       sticky="w")
            for row, (label, _, _) in enumerate(uniform.DESCRIPTOR, 1):
                ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", padx=(6, 12))
                for col, part in ((1, "outfield"), (2, "keeper")):
                    field = "%s.%s" % (part, label.replace(" ", ""))
                    self.licence_widget(frame, side, licence, field).grid(
                        row=row, column=col, sticky="w", padx=(0, 16), pady=1)

    def licence_widget(self, parent, side, licence, field):
        desc = self.desc[side, licence]
        b, kind = uniform.descriptor_field(field)
        spec = uniform.descriptor_spec(field)

        def get():
            return desc[b]
        if spec is None:
            return ttk.Label(parent, text=str(get()), foreground="#777")

        def apply(text, revert):
            return self.commit_licence(side, licence, field, text, revert)
        if kind == "colour":
            return colour_input(parent, self.swatches, get, apply, spec[1])
        names = {"collar": lambda v: "%d %s" % (v, uniform.collar_name(v)),
                 "side": lambda v: "%d %s" % (v, uniform.SHORTS_NUMBER[v])
                 if v < len(uniform.SHORTS_NUMBER) else str(v)}
        return value_input(parent, spec, names.get(kind, str), get, apply)

    def commit_licence(self, side, licence, field, text, revert):
        what = "licence %d %s" % (licence, side)
        try:
            value = int(text)
        except ValueError:
            return self.refuse(what, "%s must be a number" % field, revert)
        if value not in uniform.descriptor_spec(field)[1]:
            return self.refuse(what, "%s can't be %d" % (field, value), revert)
        old = uniform.set_descriptor(self.desc[side, licence], 0, field, value)
        self.lic_changes.pop((side, licence, field), None)
        self.lic_changes[side, licence, field] = value
        self.app.status("%s: %s %s -> %s" % (what, field, old, value))
        team = next((t for t, n in self.licence_of.items() if n == licence), None)
        if team is not None and self.tree.exists(str(team)):
            self.tree.item(str(team), tags=("edited",))
        self.app.update_title()
        return True

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
        return bool(self.changes or self.gk_changes or self.lic_changes)

    def licence_commands(self, temps, commands):
        """Write the descriptor edits into both copies, each read as it is
        now (the People tab writes the executable too): one setexe and one
        setlicence command per side and licence."""
        import pac
        import sles_disasm
        mod = self.app.mod
        groups = {}
        for (side, n, field), value in self.lic_changes.items():
            groups.setdefault((side, n), []).append((field, value))

        def args(edits):
            return ["%s=%d" % e for e in edits]
        sles_in = mod.disc_source(SLES)
        elf = sles_disasm.Elf(sles_in)
        data = bytearray(elf.data)
        out = mod.disc_target(SLES)
        src = sles_in
        for (side, n), edits in groups.items():
            base = uniform.exe_descriptor_base(sles_in, elf, side, n)
            for field, value in edits:
                uniform.set_descriptor(data, base, field, value)
            commands.append(["python", "SRC/uniform.py", "setexe", quote(shown_path(src)),
                             quote(shown_path(out + ".new")), side, str(n)] + args(edits))
            src = out + ".new"
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out + ".new", "wb") as f:
            f.write(data)
        temps.append((out + ".new", out))
        for side in ("home", "away"):
            mine = [(n, edits) for (s, n), edits in groups.items() if s == side]
            if not mine:
                continue
            # The header stays in DAT/ (same size); the data may be the
            # mod's edited copy, hence --data.
            header = os.path.join(mod.dat, PLPACK[side] + ".HED")
            src = mod.source(PLPACK[side] + ".PAC")
            h = pac.load_header(header)
            with open(src, "rb") as f:
                data = bytearray(f.read())
            out = mod.target(PLPACK[side] + ".PAC")
            for n, edits in mine:
                base = uniform.pack_descriptor_base(h, data, n)
                for field, value in edits:
                    uniform.set_descriptor(data, base, field, value)
                commands.append(["python", "SRC/uniform.py", "setlicence",
                                 quote(shown_path(header)), quote(shown_path(out + ".new")),
                                 str(n)] + args(edits) + ["--data", quote(shown_path(src))])
                src = out + ".new"
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
            temps.append((out + ".new", out))

    def save(self):
        if not self.dirty():
            return True
        mod = self.app.mod
        temps, commands = [], []
        try:
            if self.lic_changes:
                self.licence_commands(temps, commands)
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
        except (ValueError, OSError, struct.error) as e:
            remove_new(temps)
            messagebox.showerror("Kits", "Can't save: %s" % e)
            return False
        replace_new(temps)
        n = len(self.changes) + len(self.gk_changes) + len(self.lic_changes)
        lines = log_lines("Kits: %d changes" % n, commands, temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (" and ".join(shown_path(f) for _, f in temps), n))
        return True


MESPAC = "MESSAGE/MES.PAC"
LANG_NAMES = ("Japanese", "English", "French", "German", "Italian", "Spanish",
              "unused slot")        # FC_EURO_LOCALIZE; DOC/MBB_FORMAT.md#languages
TEXT_LIMIT = 1000


class TextTab(Tab):
    """Message text in MES.PAC, all 7 language slots, through mbb.MesPack
    (the code `mbb.py set` and `import` use). A file may outgrow its slot:
    MES.PAC grows and the later files move (MesPack.build)."""
    title = "Text"

    def __init__(self, app):
        super().__init__(app)
        self.pack = None
        self.changes = {}           # (cat, lang, id, copy) -> text, in edit order
        self.current = None
        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Language").pack(side="left")
        self.lang_var = tk.StringVar(value="1 English")
        box = ttk.Combobox(bar, textvariable=self.lang_var, state="readonly", width=14,
                           values=["%d %s" % kv for kv in enumerate(LANG_NAMES)])
        box.pack(side="left", padx=(4, 12))
        box.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())
        ttk.Label(bar, text="Category").pack(side="left")
        self.cat_var = tk.StringVar(value="any")
        self.cat_box = ttk.Combobox(bar, textvariable=self.cat_var, state="readonly", width=40)
        self.cat_box.pack(side="left", padx=(4, 12))
        self.cat_box.bind("<<ComboboxSelected>>", lambda e: self.refresh_list())
        ttk.Label(bar, text="Text or id").pack(side="left")
        self.find_var = tk.StringVar()
        find = ttk.Entry(bar, textvariable=self.find_var, width=24)
        find.pack(side="left", padx=(4, 12))
        find.bind("<Return>", lambda e: self.refresh_list())
        ttk.Button(bar, text="Search", command=self.refresh_list).pack(side="left")
        self.count_label = ttk.Label(bar, text="")
        self.count_label.pack(side="left", padx=12)

        panes = self.panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        left = ttk.Frame(panes)
        cols = ("cat", "id", "text")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, text, width in zip(cols, ("Category", "Id", "Text"), (70, 70, 360)):
            self.tree.heading(c, text=text)
            self.tree.column(c, width=width, stretch=c == "text")
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
        try:
            self.path = self.app.mod.source(MESPAC)
            self.pack = mbb.MesPack(self.path)
        except (ValueError, struct.error, OSError) as e:
            self.app.status("Couldn't load the text: %s" % e)
            messagebox.showerror("Text", "Couldn't load the text:\n%s" % e)
            return
        # Every message by (category, id, copy), whichever languages have it.
        self.keys = {}
        for (cat, lang), (_, _, _, _, m) in self.pack.files.items():
            seen = {}
            for rid, _ in m.records:
                k = seen[rid] = seen.get(rid, -1) + 1
                self.keys.setdefault((cat, rid, k), set()).add(lang)
        self.order = sorted(self.keys)
        self.texts = {}             # lang -> {(cat, id, copy): text}, decoded on first use
        self.changes = {}
        cats = sorted({cat for cat, _ in self.pack.files})
        self.cat_box["values"] = ["any"] + [mbb.category_label(c) for c in cats]
        self.refresh_list()
        if self.current is not None and self.current in self.keys:
            self.show(self.current)
        if done:
            self.app.status(done)
        self.app.update_title()

    def lang_texts(self, lang):
        if lang not in self.texts:
            out = {}
            for (cat, l), (_, _, _, _, m) in self.pack.files.items():
                if l != lang:
                    continue
                seen = {}
                for rid, s in m.records:
                    k = seen[rid] = seen.get(rid, -1) + 1
                    out[(cat, rid, k)] = mbb.decode(s, lang)
            self.texts[lang] = out
        return self.texts[lang]

    # the list

    @property
    def lang(self):
        return int(self.lang_var.get().split()[0])

    def refresh_list(self):
        if self.pack is None:
            return
        texts = self.lang_texts(self.lang)
        cat = None if self.cat_var.get() == "any" else int(self.cat_var.get().split()[0])
        find = self.find_var.get().strip()
        low = find.lower()
        found = []
        for key in self.order:
            if cat is not None and key[0] != cat:
                continue
            if find:
                if find.isdigit() and str(key[1]) == find:
                    pass
                elif low not in texts.get(key, "").lower():
                    continue
            found.append(key)
        self.tree.delete(*self.tree.get_children())
        for key in found[:TEXT_LIMIT]:
            self.tree.insert("", "end", iid="%d:%d:%d" % key, values=self.row(key, texts),
                             tags=("edited",) if self.edited(key) else ())
        self.count_label.configure(text="%d found%s" % (
            len(found), ", showing the first %d" % TEXT_LIMIT if len(found) > TEXT_LIMIT else ""))

    def row(self, key, texts=None):
        texts = texts or self.lang_texts(self.lang)
        text = texts.get(key, "(none in this language)").replace("\n", " / ")
        return (key[0], key[1] if not key[2] else "%d (copy %d)" % (key[1], key[2]),
                text[:200])

    def edited(self, key):
        return any((c, r, k) == key for c, _, r, k in self.changes)

    def select(self):
        sel = self.tree.selection()
        if sel:
            self.show(tuple(int(x) for x in sel[0].split(":")))

    # one message in every language

    def show(self, key):
        self.current = key
        cat, rid, copy = key
        self.detail.clear()
        box = self.detail.inner
        ttk.Label(box, text="Category %s, message %d%s" % (
            mbb.category_label(cat), rid, " (copy %d)" % copy if copy else ""),
            font=self.app.title_font).pack(anchor="w", padx=8, pady=(8, 2))
        ttk.Label(box, text="Control codes are {tags}: {var:CAT:ID} a variable, {color:N} ... "
                            "{/color} colour, {name:N} speaker, {face:S:N}, {react:N}, "
                            "{circle} and other pad buttons; '{{' is a literal '{'. A new line "
                            "is a line break (DOC/MBB_FORMAT.md). Changes apply when you leave "
                            "the box or press Ctrl+Enter.",
                  foreground="#555", wraplength=640, justify="left").pack(anchor="w", padx=8)
        for lang, name in enumerate(LANG_NAMES):
            frame = ttk.LabelFrame(box, text="%d %s" % (lang, name))
            frame.pack(fill="x", padx=8, pady=4)
            if lang not in self.keys[key]:
                ttk.Label(frame, text="(no message in this language)", foreground="#777").pack(
                    anchor="w", padx=6, pady=2)
                continue
            text = self.pack.text(cat, lang, rid, copy)
            widget = tk.Text(frame, height=min(8, text.count("\n") + 2), width=72, wrap="word",
                             undo=True, font="TkDefaultFont")
            widget.insert("1.0", text)
            widget.edit_reset()
            widget.pack(fill="x", padx=6, pady=(4, 0))
            room = ttk.Label(frame, text="", foreground="#555")
            room.pack(anchor="w", padx=6, pady=(0, 4))
            self.show_room(room, cat, lang)

            def commit(event=None, lang=lang, widget=widget, room=room):
                new = widget.get("1.0", "end-1c")
                if new != self.pack.text(cat, lang, rid, copy):
                    self.commit(key, lang, new, widget, room)
                return "break" if event is not None and event.keysym == "Return" else None
            widget.bind("<FocusOut>", commit)
            widget.bind("<Control-Return>", commit)
        self.fit_detail()

    def fit_detail(self):
        self.frame.update_idletasks()
        need = self.detail.inner.winfo_reqwidth() + 24
        have = self.detail.outer.winfo_width()
        if need > have > 1:
            pos = self.panes.sashpos(0)
            self.panes.sashpos(0, max(LIST_MIN, pos - (need - have)))

    def show_room(self, label, cat, lang):
        need, size, slot = self.pack.room(cat, lang)
        name = "%d_%d.mbb" % (cat, lang)
        if need <= size:
            label.configure(text="%s: %s of %s bytes used" % (name, format(need, ","),
                                                               format(size, ",")))
        elif mbb.MesPack.fits(need, slot):
            label.configure(text="%s: %s bytes, grown from %s into its slot of %s (the editor "
                                 "updates the PRELOAD copies when it builds a disc)" % (
                                     name, format(need, ","), format(size, ","), format(slot, ",")))
        else:
            label.configure(text="%s: %s bytes, past its slot of %s: MES.PAC grows and the "
                                 "later files move (Build disc also updates the game's index "
                                 "of them)" % (name, format(need, ","), format(slot, ",")))

    def commit(self, key, lang, text, widget, room):
        cat, rid, copy = key
        what = "%d_%d.mbb id %d" % (cat, lang, rid)
        old = self.pack.text(cat, lang, rid, copy)

        def revert():
            widget.delete("1.0", "end")
            widget.insert("1.0", old)
        try:
            self.pack.set(cat, lang, rid, copy, text)
        except ValueError as e:
            return self.refuse(str(e), revert)
        self.changes.pop((cat, lang, rid, copy), None)
        self.changes[cat, lang, rid, copy] = text
        if lang in self.texts:
            self.texts[lang][key] = self.pack.text(cat, lang, rid, copy)
        self.show_room(room, cat, lang)
        iid = "%d:%d:%d" % key
        if self.tree.exists(iid):
            self.tree.item(iid, values=self.row(key), tags=("edited",))
        self.app.status("%s changed" % what)
        self.app.update_title()
        return True

    def refuse(self, message, revert):
        revert()
        self.app.status(message)
        messagebox.showerror("Text", message)
        return False

    # saving

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        out = mod.target(MESPAC)
        temps = [(out + ".new", out)]
        data, report, grown, errors = self.pack.build()
        if errors:
            messagebox.showerror("Text", "Can't save:\n" + "\n".join(errors))
            return False
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except OSError as e:
            remove_new(temps)
            messagebox.showerror("Text", "Can't save: %s" % e)
            return False
        replace_new(temps)
        args = []
        for (cat, lang, rid, copy), text in self.changes.items():
            args += [str(cat), "%d:%d" % (rid, copy) if copy else str(rid), str(lang),
                     quote(text.replace("\n", "\\n"))]
        cmd = ["python", "SRC/mbb.py", "set", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + args
        n = len(self.changes)
        lines = log_lines("Text: %d messages" % n, [cmd], temps, "\n".join(report))
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d messages%s" % (shown_path(out), n, ", %d file%s grew" % (
            grown, "" if grown == 1 else "s") if grown else ""))
        return True


INIT_TEAMS = "PARAM/PLRRSRC_INITTEAMDATA.TBB"
LEAGUESIZE_NEW = "leaguesize.new"     # where a size change is built before it replaces the files


class SeasonTab(Tab):
    """The starting season's divisions (PLRRSRC_INITTEAMDATA.TBB):
    swapping two league clubs' places through initteam.InitTeamData.swap,
    as `initteam.py swap` does, and changing a first division's size
    through leaguesize.py, which also writes the three schedule packs.
    A pending size change is shown from leaguesize.plan; the save runs
    leaguesize.build after the swaps are written, as the log's commands
    do. A swap only exchanges two ids, so it gives the same result before
    or after a size change."""
    title = "Season"

    def __init__(self, app):
        super().__init__(app)
        self.init = None
        self.swaps = []             # [(a, b)] in order
        self.sizes = {}             # {league: first-division clubs} not saved yet
        self.last_pick = None
        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="League").pack(side="left")
        self.league_var = tk.StringVar(value=teaminit.LEAGUES[0])
        box = ttk.Combobox(bar, textvariable=self.league_var, values=teaminit.LEAGUES,
                           state="readonly", width=14)
        box.pack(side="left", padx=(4, 20))
        box.bind("<<ComboboxSelected>>", lambda e: self.show())
        self.size_cell = ttk.Frame(bar)
        self.size_cell.pack(side="left", padx=(0, 20))
        ttk.Label(bar, text="Swap").pack(side="left")
        self.a_var, self.b_var = tk.StringVar(), tk.StringVar()
        self.a_box = ttk.Combobox(bar, textvariable=self.a_var, state="readonly", width=30,
                                  height=25)
        self.a_box.pack(side="left", padx=4)
        ttk.Label(bar, text="with").pack(side="left")
        self.b_box = ttk.Combobox(bar, textvariable=self.b_var, state="readonly", width=30,
                                  height=25)
        self.b_box.pack(side="left", padx=4)
        ttk.Button(bar, text="Swap", command=self.swap).pack(side="left", padx=8)
        ttk.Label(self.frame, text="A swap exchanges two clubs' places in the starting divisions "
                                   "and in last season's results, which decide the first "
                                   "season's divisions after promotion and relegation, and the "
                                   "cup places. Each club keeps its squad, kit and record "
                                   "(DOC/INITTEAM_FORMAT.md). A nation's two divisions share its "
                                   "clubs: a bigger first division takes the second division's "
                                   "best clubs below its promotion places, a smaller one sends "
                                   "its lowest clubs above the relegation places down. Both "
                                   "divisions get new schedules and game days, which must fit "
                                   "their seasons (DOC/SCHEDULE_FORMAT.md). Tested in PCSX2: "
                                   "England at 22 clubs through two seasons.",
                  foreground="#555", wraplength=1100, justify="left").pack(anchor="w", padx=8)
        self.body = ttk.Frame(self.frame)
        self.body.pack(fill="both", expand=True, padx=6, pady=6)
        self.trees = []
        for div in range(initteam.DIVISIONS):
            frame = ttk.LabelFrame(self.body, text="")
            frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
            tree = ttk.Treeview(frame, columns=("rank", "id", "club", "note"), show="headings",
                                selectmode="browse", height=26)
            for c, text, width in (("rank", "Last season", 80), ("id", "Id", 50),
                                   ("club", "Club", 200), ("note", "", 90)):
                tree.heading(c, text=text)
                tree.column(c, width=width, stretch=c == "club")
            tree.tag_configure("edited", foreground="#b03000")
            tree.pack(fill="both", expand=True)
            tree.bind("<<TreeviewSelect>>", lambda e, t=tree: self.pick(t))
            self.trees.append((frame, tree))

    def load(self, done=None):
        mod = self.app.mod
        try:
            self.path = mod.source(INIT_TEAMS)
            # The schedule packs and the divisions, each file from the mod
            # folder when it is there, as `leaguesize.py build --over` reads them.
            self.data = leaguesize.load(self.param_dir(), self.param_over())
            self.init = self.data[3]
            self.nations = [leaguesize.Nation(*self.data[:3], lg)
                            for lg in range(len(teaminit.LEAGUES))]
            self.teams = initteam.team_names(mod.source(MES), 1)
        except (ValueError, struct.error, OSError, StopIteration) as e:
            self.app.status("Couldn't load the starting divisions: %s" % e)
            messagebox.showerror("Season", "Couldn't load the starting divisions:\n%s" % e)
            return
        self.swaps = []
        self.sizes = {}
        self.show()
        if done:
            self.app.status(done)
        self.app.update_title()

    def param_dir(self):
        return os.path.join(self.app.mod.dat, "PARAM")

    def param_over(self):
        return self.app.mod.target("PARAM")

    def divisions(self, league):
        """[(clubs in last season's order, past record or None)] for the
        league's two divisions, with a size change not saved yet."""
        if league in self.sizes:
            n, _, _, recs, _ = leaguesize.plan(None, league, self.sizes[league], self.data)
            return [(recs[0], n.c1), (recs[1], n.c2)]
        out = []
        for div in range(initteam.DIVISIONS):
            d = self.init.divisions[league * initteam.DIVISIONS + div]
            rec = self.init.past_record(d)
            out.append(([t for t in self.init.past[rec] if t] if rec is not None else d.teams,
                        rec))
        return out

    def club_label(self, team):
        lg, dv = self.where[team]
        return "%d %s (%s %d)" % (team, self.teams.get(team, ""), teaminit.LEAGUES[lg], dv + 1)

    def league(self):
        return teaminit.LEAGUES.index(self.league_var.get())

    def show(self):
        """The chosen league's divisions and its size box."""
        if self.init is None:
            return
        self.show_tables()
        self.size_input(self.league())

    def show_tables(self):
        league = self.league()
        swapped = {t for pair in self.swaps for t in pair}
        divs = {lg: self.divisions(lg) for lg in range(len(teaminit.LEAGUES))}
        self.where = {t: (lg, div) for lg, two in divs.items()
                      for div, (order, _) in enumerate(two) for t in order}
        n = self.nations[league]
        for div, ((order, rec), (frame, tree)) in enumerate(zip(divs[league], self.trees)):
            was = (n.size1, n.size2)[div]
            frame.configure(text="%s division %d: %d clubs%s%s" % (
                teaminit.LEAGUES[league], div + 1, len(order),
                " (was %d)" % was if len(order) != was else "",
                ", last season's table is competition %d" % rec if rec is not None else ""))
            before = set(self.init.divisions[league * initteam.DIVISIONS + div].teams)
            tree.delete(*tree.get_children())
            for k, team in enumerate(order):
                note = ", ".join(w for w, on in (("swapped", team in swapped),
                                                 ("moved", team not in before)) if on)
                tree.insert("", "end", iid=str(team),
                            values=(k + 1 if rec is not None else "", team,
                                    self.teams.get(team, ""), note),
                            tags=("edited",) if note else ())
        labels = [self.club_label(t) for t in sorted(self.init.league_clubs())]
        self.a_box["values"] = labels
        self.b_box["values"] = labels

    def size_input(self, league):
        """The first division's size, in the range leaguesize.allowed gives.
        Rebuilt when the league changes, not from the box's own events."""
        for w in self.size_cell.winfo_children():
            w.destroy()
        n = self.nations[league]
        lo, hi = leaguesize.allowed(n)
        ttk.Label(self.size_cell, text="First division clubs").pack(side="left")
        get = lambda: self.sizes.get(league, n.size1)
        self.size_box = value_input(self.size_cell, ("range", lo, hi), str, get,
                                    lambda text, revert: self.resize(league, text, revert))
        self.size_box.pack(side="left", padx=4)
        self.size_note = ttk.Label(self.size_cell)
        self.size_note.pack(side="left")
        self.show_size_note(league)

    def show_size_note(self, league):
        n = self.nations[league]
        lo, hi = leaguesize.allowed(n)
        self.size_note.configure(text="(%d-%d; second division %d)" % (
            lo, hi, n.size1 + n.size2 - self.sizes.get(league, n.size1)))

    def resize(self, league, text, revert):
        n = self.nations[league]
        try:
            clubs = int(text)
        except ValueError:
            return self.refuse("Not a number: %r" % text, revert)
        probs = leaguesize.plan(None, league, clubs, self.data)[4]
        if probs:
            return self.refuse("%s can't have %d clubs in its first division: %s" % (
                teaminit.LEAGUES[league], clubs, "; ".join(probs)), revert)
        if clubs == n.size1:
            self.sizes.pop(league, None)
        else:
            self.sizes[league] = clubs
        self.app.status("%s: first division %d clubs, second %d" % (
            teaminit.LEAGUES[league], clubs, n.size1 + n.size2 - clubs))
        self.show_tables()
        self.show_size_note(league)
        self.app.update_title()

    def refuse(self, message, revert):
        revert()
        self.app.status(message)
        messagebox.showerror("Season", message)
        return False

    def pick(self, tree):
        sel = tree.selection()
        if not sel:
            return
        label = self.club_label(int(sel[0]))
        # The first pick fills "Swap", the next one "with", and a pick after
        # both starts again. Picking the same club again (or a repeated
        # selection event) changes nothing.
        if label == self.last_pick:
            return
        self.last_pick = label
        if self.a_var.get() and not self.b_var.get():
            self.b_var.set(label)
        else:
            self.a_var.set(label)
            self.b_var.set("")

    def swap(self):
        try:
            a, b = int(self.a_var.get().split()[0]), int(self.b_var.get().split()[0])
            n = self.init.swap(a, b)
        except (ValueError, IndexError) as e:
            messagebox.showerror("Season", "Choose two different league clubs to swap. %s" % e)
            return
        self.swaps.append((a, b))
        self.app.status("Swapped %d %s and %d %s (%d places)" % (
            a, self.teams.get(a, ""), b, self.teams.get(b, ""), n))
        self.a_var.set("")
        self.b_var.set("")
        self.last_pick = None
        self.show()
        self.app.update_title()

    def dirty(self):
        return bool(self.swaps or self.sizes)

    def save(self):
        """The swaps first, then the size changes, which read the swapped
        file back from the mod folder; each is logged as its own command."""
        if not self.dirty():
            return True
        done = []
        if self.swaps:
            if not self.save_swaps():
                return False
            done.append("%d swaps" % len(self.swaps))
        if self.sizes:
            if not self.save_sizes():
                # Any swaps are saved by now: reload them, keep the sizes.
                sizes = self.sizes
                self.load()
                self.sizes = sizes
                self.show()
                self.app.update_title()
                return False
            done.append(", ".join("%s %d clubs" % (teaminit.LEAGUES[lg], c)
                                  for lg, c in sorted(self.sizes.items())))
        self.load("Saved the starting season: %s" % "; ".join(done))
        return True

    def save_swaps(self):
        mod = self.app.mod
        out = mod.target(INIT_TEAMS)
        temps = [(out + ".new", out)]
        try:
            data = self.init.encode()
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(data)
        except (ValueError, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Season", "Can't save: %s" % e)
            return False
        replace_new(temps)
        cmd = ["python", "SRC/initteam.py", "swap", quote(shown_path(self.path)),
               quote(shown_path(out + ".new"))] + ["%d:%d" % p for p in self.swaps]
        lines = log_lines("Season: %d swaps" % len(self.swaps), [cmd], temps)
        self.app.mod.log(lines)
        self.app.write_log(lines)
        return True

    def save_sizes(self):
        """leaguesize.build into <mod>/leaguesize.new, checked there with
        leaguesize.verify, then each file replaces its copy in <mod>/PARAM."""
        mod = self.app.mod
        sizes = sorted(self.sizes.items())
        folder = os.path.join(mod.root, LEAGUESIZE_NEW)
        temps = []
        try:
            files, turns = leaguesize.build(self.param_dir(), sizes, self.param_over())
            os.makedirs(folder, exist_ok=True)
            os.makedirs(self.param_over(), exist_ok=True)
            for name, data in sorted(files.items()):
                temps.append((os.path.join(folder, name), os.path.join(self.param_over(), name)))
                with open(temps[-1][0], "wb") as f:
                    f.write(data)
            probs = leaguesize.verify(folder, sizes, turns)
            if probs:
                raise ValueError("; ".join(probs))
        except (ValueError, struct.error, OSError) as e:
            remove_new(temps)
            if os.path.isdir(folder) and not os.listdir(folder):
                os.rmdir(folder)
            messagebox.showerror("Season", "Can't save the division sizes: %s" % e)
            return False
        replace_new(temps)
        os.rmdir(folder)
        cmd = ["python", "SRC/leaguesize.py", "build", quote(shown_path(self.param_dir())),
               quote(shown_path(folder))]
        for lg, clubs in sizes:
            cmd += [teaminit.LEAGUES[lg], str(clubs)]
        cmd += ["--over", quote(shown_path(self.param_over()))]
        lines = log_lines("Season: %s" % ", ".join("%s first division %d clubs" % (
            teaminit.LEAGUES[lg], c) for lg, c in sizes), [cmd], temps,
            moved="each file in %s" % shown_path(folder))
        mod.log(lines)
        self.app.write_log(lines)
        self.app.notify(self, "schedules")
        return True


class FreeAgentsTab(Tab):
    """The free agents at the start of a career (PLRESOURCESIM.PAC entry
    15), through plrsim.set_free, as `plrsim.py setfree` does. The players'
    names, ranks and clubs come from the People tab."""
    title = "Free agents"

    def __init__(self, app):
        super().__init__(app)
        self.ids = None             # the list as edited
        self.original = None
        self.changes = {}           # slot -> player, in edit order

        bar = ttk.Frame(self.frame)
        bar.pack(fill="x", padx=6, pady=6)
        ttk.Label(bar, text="Find a player (name or id)").pack(side="left")
        self.find_var = tk.StringVar()
        find = ttk.Entry(bar, textvariable=self.find_var, width=22)
        find.pack(side="left", padx=(4, 12))
        find.bind("<Return>", lambda e: self.refresh_candidates())
        self.search_button = ttk.Button(bar, text="Search", command=self.refresh_candidates)
        self.search_button.pack(side="left")
        self.count_label = ttk.Label(bar, text="")
        self.count_label.pack(side="left", padx=12)
        ttk.Label(self.frame, text="Pick a slot on the left and a player on the right, then "
                                   "Replace. The Transfer List only shows free agents whose rank "
                                   "is in the band for the club's rank: 0-5 for a new club, at "
                                   "most %d for any club (DOC/PLRESOURCESIM_FORMAT.md). A player "
                                   "in a club's squad can't also be a free agent."
                                   % plrsim.TRANSFER_LIST_MAX_RANK,
                  foreground="#555", wraplength=1100, justify="left").pack(anchor="w", padx=8)

        panes = ttk.PanedWindow(self.frame, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=6, pady=6)
        cols = ("id", "name", "nation", "age", "position", "rank")
        widths = (60, 160, 90, 40, 90, 40)
        left = ttk.LabelFrame(panes, text="Free agents at the start")
        self.tree = self.player_tree(left, ("slot",) + cols + ("note",),
                                     (50,) + widths + (150,))
        self.tree.bind("<<TreeviewSelect>>", lambda e: self.picked())
        panes.add(left, weight=1)
        right = ttk.LabelFrame(panes, text="Players to bring in")
        foot = ttk.Frame(right)
        foot.pack(side="bottom", fill="x", pady=4)
        self.replace_button = ttk.Button(foot, text="Replace", command=self.replace,
                                         state="disabled")
        self.replace_button.pack(side="left", padx=4)
        self.pick_label = ttk.Label(foot, text="")
        self.pick_label.pack(side="left", padx=8)
        self.found = self.player_tree(right, cols + ("club",), widths + (150,))
        self.found.bind("<<TreeviewSelect>>", lambda e: self.picked())
        self.found.bind("<Double-1>", lambda e: self.replace())
        panes.add(right, weight=1)

    def player_tree(self, parent, cols, widths):
        tree = ttk.Treeview(parent, columns=cols, show="headings", selectmode="browse")
        for c, width in zip(cols, widths):
            tree.heading(c, text=c.capitalize())
            tree.column(c, width=width, stretch=c == "name")
        tree.tag_configure("edited", foreground="#b03000")
        sb = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        tree.pack(side="left", fill="both", expand=True)
        return tree

    def load(self, done=None):
        self.path = self.app.mod.source(SIMPAC)
        try:
            with open(self.path, "rb") as f:
                self.ids = plrsim.free_agents(f.read())
        except (ValueError, struct.error, OSError, IndexError) as e:
            self.ids = None
            self.app.status("Couldn't load the free agents: %s" % e)
            messagebox.showerror("Free agents", "Couldn't load the free agents:\n%s" % e)
            return
        self.original = list(self.ids)
        self.changes = {}
        self.refresh_list()
        self.refresh_candidates()
        if done:
            self.app.status(done)
        self.app.update_title()

    def changed(self, what):
        if what in ("people", "squads") and self.ids is not None:
            self.refresh_list()
            self.refresh_candidates()

    # the lists

    def players(self):
        """The People tab's players, edits included, or None while it loads."""
        records = self.app.people.records
        return records["players"] if records else None

    def club(self, player):
        club = self.app.people.club_of.get(player) if self.players() else None
        return club[0] if club else None

    def cells(self, player):
        players = self.players()
        if players is None or player >= len(players):
            return (player, "", "", "", "", "")
        f = players[player].fields
        return (player, players[player].name, self.app.people.nations.get(f["nation"], f["nation"]),
                f["age"], "/".join(pbdata.position_name(p) for p in f["position"] if p != 13),
                f["rank"])

    def note(self, player):
        players = self.players()
        if players and player < len(players) and \
                players[player].fields["rank"] > plrsim.TRANSFER_LIST_MAX_RANK:
            return "never on the Transfer List"
        return ""

    def refresh_list(self):
        sel = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        for slot, player in enumerate(self.ids):
            self.tree.insert("", "end", iid=str(slot),
                             values=(slot,) + self.cells(player) + (self.note(player),),
                             tags=("edited",) if slot in self.changes else ())
        if sel and self.tree.exists(sel[0]):
            self.tree.selection_set(sel)
            self.tree.see(sel[0])
        self.tree.master.configure(text="Free agents at the start: %d, %d changed" % (
            len(self.ids), len(self.changes)))

    def refresh_candidates(self):
        self.found.delete(*self.found.get_children())
        players = self.players()
        if players is None or self.ids is None:
            self.count_label.configure(text="(waiting for the player database)")
            return
        find = self.find_var.get().strip()
        listed = set(self.ids)
        found = [r for r in players[:plrsim.PLAYERS] if r.index not in listed and
                 (str(r.index) == find if find.isdigit() else find.lower() in r.name.lower())]
        for r in found[:LIST_LIMIT]:
            club = self.club(r.index)
            self.found.insert("", "end", iid=str(r.index), values=self.cells(r.index) + (
                "" if club is None else self.app.people.team_label(club),))
        self.count_label.configure(text="%d found%s" % (
            len(found), ", showing the first %d" % LIST_LIMIT if len(found) > LIST_LIMIT else ""))
        self.picked()

    def picked(self):
        slot, player = self.tree.selection(), self.found.selection()
        if slot and player:
            self.pick_label.configure(text="slot %s: %s -> %s" % (
                slot[0], self.cells(self.ids[int(slot[0])])[1], self.cells(int(player[0]))[1]))
        else:
            self.pick_label.configure(text="choose a slot and a player")
        self.replace_button.configure(state="normal" if slot and player else "disabled")

    # editing

    def replace(self):
        slot, player = self.tree.selection(), self.found.selection()
        if not slot or not player:
            return
        slot, player = int(slot[0]), int(player[0])
        name = self.cells(player)[1]
        club = self.club(player)
        if club is not None:
            # No free agent on the disc is in a squad (initteam.py's squads).
            return self.refuse("%d %s is in the squad of %s" % (
                player, name, self.app.people.team_label(club)))
        try:
            old = plrsim.set_free(self.ids, slot, player)
        except ValueError as e:
            return self.refuse(str(e))
        self.changes.pop(slot, None)
        if player != self.original[slot]:
            self.changes[slot] = player
        self.app.status("Free agents slot %d: %d %s -> %d %s" % (
            slot, old, self.cells(old)[1], player, name))
        self.refresh_list()
        self.refresh_candidates()
        self.app.update_title()

    def refuse(self, message):
        self.app.status("Refused: " + message)
        messagebox.showerror("Free agents", message)

    def dirty(self):
        return bool(self.changes)

    def save(self):
        if not self.changes:
            return True
        mod = self.app.mod
        # The Clubs tab writes the same pack, so start from the file as it
        # is now.
        src = mod.source(SIMPAC)
        out = mod.target(SIMPAC)
        temps = [(out + ".new", out)]
        try:
            with open(src, "rb") as f:
                data = f.read()
            ids = plrsim.free_agents(data)
            for slot, player in self.changes.items():
                plrsim.set_free(ids, slot, player)
            new = plrsim.encode_free(data, ids)
            if len(new) != len(data):
                raise ValueError("rebuilt pack is %d bytes, not %d" % (len(new), len(data)))
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out + ".new", "wb") as f:
                f.write(new)
        except (ValueError, struct.error, OSError) as e:
            remove_new(temps)
            messagebox.showerror("Free agents", "Can't save: %s" % e)
            return False
        replace_new(temps)
        cmd = ["python", "SRC/plrsim.py", "setfree", quote(shown_path(src)),
               quote(shown_path(out + ".new"))] + ["%d=%d" % c for c in self.changes.items()]
        n = len(self.changes)
        lines = log_lines("Free agents: %d changes" % n, [cmd], temps)
        mod.log(lines)
        self.app.write_log(lines)
        self.load("Saved %s: %d changes" % (shown_path(out), n))
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
    return extract_disc.REDUMP[0]["size"]   # the PAL dump; the editor builds PAL discs


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
        # patch_disc.py's switches by name, saved as e.g. "skip_tutorial".
        self.switches = {name: tk.IntVar(value=settings.get(name.replace("-", "_"), 0))
                         for name in patch_disc.SWITCH_NAMES}

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
        # patch_disc.py's switches, one box each, from its switch table (its
        # docstring and the docs say what each changes).
        for row, (name, _, _, text) in enumerate(patch_disc.SWITCHES, 3):
            ttk.Checkbutton(form, text="%s (--mod %s)" % (text, name),
                            variable=self.switches[name]).grid(
                row=row, column=0, columnspan=3, sticky="w", pady=(6 if row == 3 else 0, 0))
        note_row = 3 + len(patch_disc.SWITCHES)
        ttk.Label(form, text="The original must be the Redump dump (redump.info/disc/12334) "
                             "for a patch others can apply. It is only read. A patch without "
                             "the image still needs room for a temporary one while it is made.",
                  foreground="#555", wraplength=900, justify="left"
                  ).grid(row=note_row, column=0, columnspan=3, sticky="w", pady=(6, 0))
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
                       "patch": self.patch.get(),
                       **{name.replace("-", "_"): var.get()
                          for name, var in self.switches.items()}},
                      f,
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
        mods = [name for name in patch_disc.SWITCH_NAMES if self.switches[name].get()]
        if mods:
            cmd += ["--mod", ",".join(mods)]
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
        self.text = TextTab(self)
        self.season = SeasonTab(self)
        self.free = FreeAgentsTab(self)
        self.regulations = RegulationsTab(self)
        self.training = TrainingTab(self)
        self.camps = CampsTab(self)
        self.facilities = FacilitiesTab(self)
        self.tours = ToursTab(self)
        self.tactics = TacticsTab(self)
        self.comments = CommentsTab(self)
        self.tabs = [self.people, self.clubs, self.newclub, self.season, self.free,
                     self.regulations, self.training, self.camps, self.tours, self.facilities,
                     self.tactics, self.kits, self.text, self.comments]
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
