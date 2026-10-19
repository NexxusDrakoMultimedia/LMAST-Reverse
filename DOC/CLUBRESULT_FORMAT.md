<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `PARAM/CLUBRESULT.TBB`: how a final place is reported

Each schedule (a league division, a cup, a group) has one row here
saying how a club's final place in it is reported: as a number for a
league, as a round name for a cup ("Champion", "Best 8"), or not at all.
The file is a TBB1 file ([`TBB_FORMAT.md`](TBB_FORMAT.md)) of one table
with a line size of 2: 165 rows of 8 bytes, each 4 u16 fields. Rows are
indexed by the schedule UID (`PLSCHE_GROUP`, 0–163), like
[`REGULATION.TBB`](REGULATION_FORMAT.md); row 164 belongs to no schedule.

`python SRC/clubresult.py info DAT/PARAM` checks every row.
`python SRC/clubresult.py show DAT/PARAM/CLUBRESULT.TBB` prints each row
with the names a cup's places get. `set` edits fields
([below](#editing)).

## Who reads it

| Address | What it shows |
|---|---|
| `SIMPRG.REL 0x167e90` | loads `ClubResult` (folder 4, through `fcEuroFile_GetFileResourceName` and `fcEuroRsrc_GetResource`) and returns table 0. **confirmed** |
| `SIMPRG.REL 0x167f38` | returns `+0x02` of row `uid` (`0x167f4c`: `uid << 3`). **confirmed** |
| `SIMPRG.REL 0x167f98` | returns whether `+0x04` is 1. **confirmed** |
| `SIMPRG.REL 0x167f68` | returns `+0x06`. **confirmed** |

The three accessors are the only callers of the loader. The file is also
entry 12 of all seven `PRELOAD/SIMFILE*.PAC`, as `REGULATION.TBB` is
entry 9 ([`REBUILD.md`](REBUILD.md)).

## Row layout

All fields are u16 (read with `lhu`).

| Offset | Name (`clubresult.py`) | Meaning | Proof |
|---|---|---|---|
| `0x00` | `uid` | the row's own UID | no reader found. Equals the row number in all 165 rows (**empirical**) |
| `0x02` | `kind` | 0 league, 1 cup, 2 not ranked | the results list and the prize messages, below. **confirmed** |
| `0x04` | `third_place` | 1: places 3 and 4 are "3rd" and "4th" | `0x167f98` compares it with 1; `Msg::ConvertRankToString` takes it as its fourth argument (`0x201810`). **confirmed** |
| `0x06` | `clubs` | the number of clubs, which a cup's round names depend on | `ConvertRankToString`'s club count (`0x2017bc`–`0x201850`). **confirmed** |

### The results list

`SIMPRG.REL 0x9a870`–`0x9ab98` fills a list of up to five competitions
with a club's place in each (rows `0x150` bytes apart). It is the end of
tournament screen, where the prize money is paid (user report). For
each:

- A cup (`kind` 1) that hasn't finished (`AppScheCtrl::isCompetetionFinish`)
  shows "-" (`0x2256f0`).
- No place (`0xff`) or `kind` 2 shows "-" (`0x9aac0`, `0x9aad4`).
- Otherwise `Msg::ConvertRankToString(text, place − 1, kind == 1,
  third_place, clubs)` writes the place (`0x9ab20`). UID 80, the
  European Super Cup (competition 37, 2 clubs), passes 9999 instead of
  its `clubs` (`0x9ab1c`): with 2 clubs its loser would read "Defeated
  1st Rnd" ([below](#the-results-list)), with 9999 "Runners-up".

`Msg::ConvertRankToString` (`SLES 0x2017a0`) takes category 1 messages
650–656 (`Msg::GetString` type `0x1d`, base id 650 at `0x52f708`):

| Place | Text (message) | Needs `clubs` |
|---|---|---|
| any, not a cup | the number ("%d", 650) | – |
| 1 | Champion (651) | 2 or more |
| 2 | Runners-up (652) | 3 or more |
| 3–4 | Best 4 (653), or "3rd"/"4th" (650) with `third_place` | 5 or more |
| 5–8 | Best 8 (654) | 9 or more |
| 9–16 | Best 16 (655) | 17 or more |
| a place without enough clubs, or 17 on | Defeated 1st Rnd (656) | – |

A `clubs` of 0 or less writes nothing. So in the 8-club cup UID 18,
places 5–8 read "Defeated 1st Rnd", and in the 4-club UID 27 places 3
and 4 do: the round that was the first.

### Prize messages

| Address | What `kind` does |
|---|---|
| `SIMPRG.REL 0x1337cc` | kind 0 or 1 picks the text of the position prize (income 6, [`REGULATION_FORMAT.md`](REGULATION_FORMAT.md#prizes-and-the-uefa-rank)); its message ids are built from `0x8ca0`–`0x8ca7` |
| `SIMPRG.REL 0x1339ac` | kind 1 picks another text the same way |
| `SIMPRG.REL 0x141f40` | kind 2 skips the prize message (`0x141f54`) |

Which message each id is hasn't been traced.

### What the rows hold

**Empirical**, `python SRC/clubresult.py info DAT/PARAM`:

| Field | Values (rows) |
|---|---|
| `kind` | 0 (67: the league divisions, and the group stages of the European competitions 34 and 35, the national cups 44–47 and the Youth League 48), 1 (38: the national and club cups, the knockout rounds of 34, 35, 45 and 47, and 36–43, among them the European Super Cup), 2 (60: the play-offs, the cup qualifying rounds, the European League Round 33, parts of 44 and 46, and the exhibition and VS schedules 49–71) |
| `third_place` | 1 in UID 122 only, the World National Cup's knockout rounds (16 clubs) |
| `clubs` | equals `REGULATION.TBB`'s `clubs` in 163 of 165 rows, and the schedule's entrants in 163 of 164; UID 113 says 6 (10 in both) and row 164 says 0 (17 in `REGULATION.TBB`). Both are `kind` 2, which never reads `clubs` |

All 165 rows fit the layout. The Japanese file is the same.

`leaguesize.py build` writes a rebuilt league's new size here as it does
in `REGULATION.TBB` ([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md)). Only
cups read `clubs`, so for a league it is kept in step only so that the
two tables agree.

## Editing

```bash
python SRC/clubresult.py set DAT/PARAM/CLUBRESULT.TBB out/CLUBRESULT.TBB 6 third_place=1
python SRC/patch_disc.py patch disc.iso modded.iso PARAM/CLUBRESULT.TBB=out/CLUBRESULT.TBB --copies
```

`set` takes a UID, then `field=value` pairs, and may name several UIDs.
It edits `kind` (0–2), `third_place` (0–1) and `clubs` (0–65535); `uid`
has no reader and stays as it is. The file keeps its size. `--copies`
also patches the seven `PRELOAD/SIMFILE*.PAC` copies.
`python SRC/clubresult.py roundtrip` re-encodes every row and checks that
the file rebuilds byte for byte. The editor's Regulations tab edits the
same fields beside each schedule's regulations. No edit has been tested
in PCSX2 yet: a cup given a third-place match should show "3rd" and
"4th" on the end of tournament screen.

## Still unknown

- Which messages the prize texts `0x8ca0`–`0x8ca7` are.
- Whether anything reads `+0x00`.

## Checking the claims

```bash
python SRC/clubresult.py info DAT/PARAM
python SRC/clubresult.py show DAT/PARAM/CLUBRESULT.TBB 6 18 27 122
python SRC/clubresult.py roundtrip DAT/PARAM/CLUBRESULT.TBB
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 167e90 66 --sles ISO/SLES_541.51    # loader and accessors
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 9aa80 46 --sles ISO/SLES_541.51     # the results list
python SRC/sles_disasm.py ISO/SLES_541.51 dis ConvertRankToString__3MsgPcibT3i
python SRC/mbb.py dump DAT/MESSAGE/MES.PAC --cat 1 --lang 1                   # messages 650-656
```
