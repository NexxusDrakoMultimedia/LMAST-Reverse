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
| A harder economy that punishes mistakes: dearer facilities, a wider ticket price range, dearer advertising, and the like | facility records in [`PLRESOURCECOMMON_FORMAT.md`](PLRESOURCECOMMON_FORMAT.md) (the u32 before the build time is the build cost, **empirical**: club houses 45,000,000 and 90,000,000, sites 60,000,000 and 120,000,000 in the stored unit; the code that charges it isn't traced); the season plan's limits in [`SAVE_FORMAT.md`](SAVE_FORMAT.md) (ad budget up to £5,000,000 a season, ticket price £10–£50, user report; where the plan screen checks them isn't traced); the salary limits at `0x5eb068` ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md)) | data edits where the values are data (facility costs), small code edits where they are limits in the code. Each a separate switch, with the new values chosen and played through a season in PCSX2 | earmarked by the user. Research first: the code that charges facility costs, the plan screen's limit checks, and what the ad budget, ticket price and season tickets do to income and popularity (the PwkScript formulas, TODO section 7) |

Ideas for the harder economy (the user's, not decided), with what each
would change:

| Idea | Where it lives | Known |
|---|---|---|
| Dearer facilities and their upkeep | `PLRESOURCECOMMON.PAC` entry 0 facility records; the maintenance lines in the accounts (payments 6–8, practice ground, facilities, stadium) | the build cost is **empirical**; what charges it and the maintenance aren't traced |
| A wider ticket price range | the season plan (`SAVE_FORMAT.md`) | the £10–£50 limits are a user report; the check isn't traced |
| Dearer advertising | the ad budget, payment 17 (`0x2528c0` reads `pwkUnkei_GetPR`) | what the budget buys isn't traced |
| Dearer overseas bases, investment in them and their upkeep | `PLRESOURCESIM.PAC` entry 1: set-up cost per region and level rates (`_GetOverseasBranchEstablishCapital`, `0x232d88`; [`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md#entry-1-overseas-branches)), payments 18–19 | **confirmed**: the maintenance uses the same two tables, so this is a data edit |
| Merchandise: dearer to stock, bigger margins | income 7 (Merchandise) in the accounts | the sales code isn't traced |
| Reputation harder to raise | club rank (0–31, save `+0xa0`), the world rank points (`SIMPRG.REL 0x151568`) and the status rank (`SAVE_FORMAT.md`, club rank leftovers) | what changes the rank after a match (`0x26ddd8`) and the weights behind the points aren't traced |
| Lesser players dearer, the best up to £250,000,000 (a top tier, a "football icon") | transfer fees (income 9, payments 14) and the player price kinds (`WithInRange_SM` `0x246d18` clamps by price kind; kind 0 is salary) | how a transfer fee is worked out isn't traced; the price limits are filled at run time |

Another idea (the user's, not decided): **a third tier and a harsher
end.** Each season the second division's bottom two go down to a third
tier that isn't played on screen, two clubs chosen at random from it
(its "playoffs") come up, and a player who finishes in the second
division's bottom two loses the game at once, instead of after two
seasons running there, so they are never forced out of the playable
leagues. What it would take:

- The game-over rule: the manual's four ways to lose include the second
  division's bottom two two years running, decided in `Sche.YearEnd`
  ([`GAME_FLOW.md`](GAME_FLOW.md#game-over)); the count of seasons
  isn't traced. Making it one season means finding that counter.
- Relegating out of the second division: its next season's slots stop
  naming its last two ranks (`leaguesize.py` rewrites those lists).
- The third tier: a nation's clubs are fixed (England has 44 plus yours
  and the rival), so the relegated clubs need somewhere to be and to
  come back from. `LIST` slots pick at random but from fixed lists, which
  can't follow who went down. The likeliest way is a small league the
  game simulates out of sight, whose past record holds the third-tier
  clubs, with the shuffle flag of its `LAST_RANK` slots for the random
  pick. All 164 schedule UIDs are used, so that needs one repurposed or
  the tables extended, and a few clubs moved out of the second division
  at the start to fill the tier.

## Not candidates

- `EVENT/EVENTDATA_TURN.TBB`, `0SYSTEM/SCHEDULE.TBB` and the `CVS/`
  files are development leftovers. The game has no code that reads them.
- Language slot 6 of `MES.PAC` is an unused near-copy of English.
- `CSE/GP_PRACTICEICON.CSP` is empty in PAL but not in the Japanese
  release. PAL loads the per-language `GP_PRACTICEICON0`–`6.CSP`, which
  hold the same icons.
- The Japanese `PLRESOURCESIM.PAC` has no free-agent list: PAL added it.
