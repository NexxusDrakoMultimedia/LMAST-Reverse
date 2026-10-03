<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# The LMASTER Mod

A mod that restores content the PAL release cut or left broken. Each
restoration is a separate `patch_disc.py` switch first, so it can be
built and tested in PCSX2 on its own. Once several work, one switch can
turn them all on.

Rules for an entry:

- Show from the game code or data that the content exists and is cut or
  broken, with addresses, as the other docs do.
- Keep the fix as small as possible and say what it changes.
- Test it in PCSX2 before it counts as restored.
- A restoration that needs new text (a translation into the other EU
  languages, say) says so.
- Compare with the Japanese release, the earlier build (see
  [`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)). Content it has and PAL
  lacks was cut for PAL; content missing from both was cut before release.

## Status

| Content | Kind | Evidence | Fix | Status |
|---|---|---|---|---|
| Main sponsor negotiation | cut (stub check) | [`SPONSOR_NEGOTIATION.md`](SPONSOR_NEGOTIATION.md) | `--sponsor-negotiation` | restored, tested in PCSX2 |
| Debug menu | developers' switch | `RootMainSeq.sqb` | `--launcher` | works, tested in PCSX2. A tool, not part of the mod |
| Kind-6 injuries starting at 1600 | broken data (dropped digit?), in both releases | [`INJURIES.md`](INJURIES.md#the-value-table-0x532cf8): `0x532d70` holds 1600 where 16001 fits | one u16 in `SLES_541.51` | candidate |
| Injury rows past fatigue 1000 | bug (out-of-bounds read) | [`INJURIES.md`](INJURIES.md#the-kind-tables): row 11 for ages 35+ | clamp the row in `judgeKegaKind` (`0x21a068`), a few instructions | candidate. Rare |
| "Two months" and "nine months" injury lines | cut before both releases (the Japanese code is the same) | [`INJURIES.md`](INJURIES.md#the-condition-line) | new thresholds in `plPinfo_KegaRecoverDaysChno` and text in four languages | needs a decision on thresholds |
| Crest presets 4–11 in three tables | broken data (a missing byte) | [`EMBLEM_DIR.md`](EMBLEM_DIR.md): tables 93, 101, 105 of `EDIT_EMBLEM.TBB` | add the missing `04 00` key | candidate. Check first whether the crest editor shows the gap |
| 32 dialogue categories | cut before both releases (no reference in the Japanese code either) | [`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md): derby interviews, a facilities tour, notices | needs triggers in the event system and English text | research |

## Improvements

Not restorations: changes to data that works but plays badly. They
follow the same rules (evidence, smallest change, tested in PCSX2) and
stay separate switches, so the restorations can be used without them.

| Change | Evidence | Fix | Status |
|---|---|---|---|
| Better home and away runs in the league schedules | [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#building-a-league-of-another-size): the disc has one schedule per size, and some send a club to one venue up to 7 times running (the 22-club leagues, UIDs 11, 30, 40, 48) or 9 (the 26-club English second division with your club, UID 1); the 8-club VS league (UIDs 154–155) reaches 5 | rebuild those UIDs with `schedule.set_league` at the same size: no more than 2 running, same game days and turns, team slots untouched | candidate (earmarked by the user). `python SRC/schedule.py league DAT/PARAM` compares each size |

## Not candidates

- `EVENT/EVENTDATA_TURN.TBB`, `0SYSTEM/SCHEDULE.TBB` and the `CVS/`
  files are development leftovers. The game has no code that reads them.
- Language slot 6 of `MES.PAC` is an unused near-copy of English.
- `CSE/GP_PRACTICEICON.CSP` is empty in PAL but not in the Japanese
  release. PAL loads the per-language `GP_PRACTICEICON0`–`6.CSP`, which
  hold the same icons.
- The Japanese `PLRESOURCESIM.PAC` has no free-agent list: PAL added it.
