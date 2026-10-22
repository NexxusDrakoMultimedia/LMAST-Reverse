<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# The LMASTER Mod

A mod that restores content the PAL release cut or left broken. Each
restoration is a separate `patch_disc.py` switch first, so it can be
built and tested in PCSX2 on its own. Switches are named, and
`--mod lmaster` turns on the mod's fixes together (sponsor-negotiation,
rival-manager, national-cups, camp-types, camp-cities, camp-santiago,
camp-clubs, drill-names); the editor's Build window has a box for
each. A test disc with all of them:

```bash
python SRC/patch_disc.py patch "Let's Make a Soccer Team! (Europe, Australia) (En,Fr,De,Es,It).iso" lmaster.iso --mod lmaster
```

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
| Main sponsor negotiation | cut (stub check) | [`SPONSOR_NEGOTIATION.md`](SPONSOR_NEGOTIATION.md) | `--mod sponsor-negotiation` | restored, tested in PCSX2 |
| Debug menu | developers' switch | `RootMainSeq.sqb` | `--mod launcher` | works, tested in PCSX2. A tool, not part of the mod |
| Kind-6 injuries starting at 1600 | broken data (dropped digit?), in both releases | [`INJURIES.md`](INJURIES.md#the-value-table-0x532cf8): `0x532d70` holds 1600 where 16001 fits | one u16 in `SLES_541.51` | candidate |
| Injury rows past fatigue 1000 | bug (out-of-bounds read) | [`INJURIES.md`](INJURIES.md#the-kind-tables): row 11 for ages 35+ | clamp the row in `judgeKegaKind` (`0x21a068`), a few instructions | candidate. Rare |
| "Two months" and "nine months" injury lines | cut before both releases (the Japanese code is the same) | [`INJURIES.md`](INJURIES.md#the-condition-line) | new thresholds in `plPinfo_KegaRecoverDaysChno` and text in four languages | needs a decision on thresholds |
| Training camps train as the next camp type | bug (off by one), in both releases | [`CAMP_FORMAT.md`](CAMP_FORMAT.md#two-bugs): `CAMP_LIST` numbers the types 1–87, the training table and the theme check read them as 0–86; Parma, a goalkeeper camp, trains no keeping | `--mod camp-types`: every type lowered by one in `CAMP_LIST.TBB` | tested in PCSX2: one keeper camp raised all three keepers' saving, aerial ability and GK aptitude most (559–617 experience), then catching and rushing out (444–488), and left pace and acceleration alone, the fixed row's pattern ([`CAMP_FORMAT.md`](CAMP_FORMAT.md)) |
| Seven English camps in the wrong town | PAL left the camp tables on the Japanese city numbers when it renumbered the English cities | [`CAMP_FORMAT.md`](CAMP_FORMAT.md#seven-english-camps-in-the-wrong-town-pal): Liverpool's camp is in Scunthorpe, Manchester's in West London, and five more | `--mod camp-cities`: the seven city ids in `CAMP_LIST.TBB` and `CAMP_EXPLANE.TBB` | tested in PCSX2 (user report): with low popularity the England list shows Southampton, Blackburn and Sheffield, not Basingstoke, Newport and Oakham. The other four need more popularity (Liverpool a sponsor) and weren't seen; the switch moves them the same way |
| Santiago's camp description | bug (wrong city id), in both releases | [`CAMP_FORMAT.md`](CAMP_FORMAT.md): `CAMP_EXPLANE` keys message 6146 to city 764, the camp is 774; the lookup (`SIMPRG.REL 0xa4a80`) finds nothing | `--mod camp-santiago`: the description's city 764 → 774 in `CAMP_EXPLANE.TBB` | tested in PCSX2 (user report): Santiago's camp shows "The Chilean capital is a hub of South American finance …" |
| Canberra's last two camp clubs | bug (loop bound), in both releases | [`CAMP_FORMAT.md`](CAMP_FORMAT.md): `SIMPRG.REL 0x4c8f8` reads 735 of `CAMP_LIST` table 1's 737 pairs, so Fukuoka and Kanagawa never appear | `--mod camp-clubs`: the bound `0x2de` → `0x2e0` at `SIMPRG.REL 0x4c9d4` (one instruction; whole disc image) | tested in PCSX2 (user report): Canberra's camp lists South Melbourne, Aichi, Fukuoka and Kanagawa |
| Drills 75–86 under the next drill's name | broken text (PAL: names one message early, an added "Jackknife") | [`TRAINING_FORMAT.md`](TRAINING_FORMAT.md#drills-7486-pals-names-are-one-early): practice *n*'s name is message 971 + *n* of category 801; the Japanese names (both discs) and the training rows have a dummy at 74 that no coach teaches, PAL's names in all five languages start one early, so the drill named "Pass training." trains shooting | `--mod drill-names`: messages 1045–1056 → 1046–1057 in `801_1`–`6.mbb` of `MES.PAC` and their copies in `PRELOAD/SIMFILE1`–`6.PAC` (entry 28); the jackknife name goes to the dummy's 1045, so the files keep their sizes. No new text; a `MES.PAC` target gets the fix in its own bytes | tested in PCSX2 (user report): coach R.Bloemzaad's drill 76 (short and long pass, cross) reads "Dribble training" on the retail disc and "Pass training." on `LMAST-test-drills.iso` |
| Play styles of an imported Virtua Pro Football player | bug (a compare function that subtracts pointers) | [`PMPLAYER_FORMAT.md`](PMPLAYER_FORMAT.md#the-record): the import's qsort compare (`SAVEPRG.REL 0x3df00`) never reads the ratings, so slot t keeps style t when rated 70+, and 18 of the 22 VPF styles never come in; G.Binns, rated 86 in a style that doesn't count, came in with none | make the compare read the two bytes and sort highest first (a few instructions in `SAVEPRG.REL`) | candidate |
| Crest presets 4–11 in three tables | broken data (a missing byte) | [`EMBLEM_DIR.md`](EMBLEM_DIR.md): tables 93, 101, 105 of `EDIT_EMBLEM.TBB` | add the missing `04 00` key | candidate. Check first whether the crest editor shows the gap |
| The rival's manager by style | bug (wrong register), in both releases (Japanese `0x25e8e8`) | [`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#the-rival-club-tables-6-7-and-8): the loop at `0x25e6d0` finds the record for the rival's style, but its load reads record 0, so the rival always gets H.Raphanel (898), never I.Ricardo (1,970), L.Alfano (1,247) or L.Nobili (1,246) | one instruction at `0x25e6d8`: `lw $s3, 8($a0)` (`8c930008`) becomes `lw $s3, 4($v1)` (`8c730004`). The rival's style is already the opposite of yours (`0x5531e0`), so its manager then matches it. `--mod rival-manager` | fixed, tested in PCSX2 (user report): in a new Teamwork career in England, the rival SC Dunstable's Information screen showed a different policy area (the big blue area on the right, which follows the manager) from the unpatched game. The game never shows the rival manager's name. The other three styles weren't tried |
| The World National Cup final on the last turn of the year | bug (schedule data) | the knockout UID 122 plays turns 92–95, and 95 is the year's last turn ([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#turns)), so the season ends on the turn of the final and its results can't be viewed in the Competition menu (user report). The group UIDs 114–121 play 89–91. The Euro National Cup ends on 94 | move both national cups back one turn (`schedule.py shift`, masks and start turns; the end turn stays 95): World Cup groups 88–90 and knockout 91–94, Euro groups 88–90 and knockout 91–93. No league or cup plays after turn 87, and the two cups are in different years of the cycle. The national-team calendar ([`SCHEDULE_LIST.TBB`](PARAM_DIR.md#schedule_listtbb-the-national-team-calendar)) moves with them: match days 88–94 and 88–93, release on the final's turn, and the call-up on 88 with the first group game (87 has the second-division play-off finals). `--mod national-cups` writes `SCHEDULE_SYSTEM.PAC` and its copy in `PRELOAD/STATIONFILE.PAC`, and `SCHEDULE_LIST.TBB` and its copies in `PRELOAD/SIMLOCALMEM0`–`6.PAC`. With a league of another size (`leaguesize.py build`, patched with `--copies`), it moves the cups in the league build's `SCHEDULE_SYSTEM.PAC` instead: a rebuilt league keeps its first and last game day, so it never reaches turn 88. Checked with England at 22 clubs: one build holds both, and `schedule.py info` finds no new problems | tested in PCSX2 (user reports): the Schedule screen's globes follow the new calendar (Euro year 2007-08: turns 88–93, week 4 empty; World Cup year 2009-10: turns 88–94, week 4 late empty). The World Cup's results after its final aren't seen, since that year is the fourth season of a career, but are taken to work: in the retail game the Euro National Cup's final is on turn 94 and its results can be viewed in the Competition menu after it (user report). The moved World Cup final is on that same turn, and both cups' knockouts are built the same way (an end turn of 95 and the same flag); the bug came only from a final on the last turn |
| 32 dialogue categories | cut before both releases (no reference in the Japanese code either) | [`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md): derby interviews, a facilities tour, notices | needs triggers in the event system and English text | research |

## Improvements

Not restorations: changes to data that works but plays badly. They
follow the same rules (evidence, smallest change, tested in PCSX2) and
stay separate switches, so the restorations can be used without them.

| Change | Evidence | Fix | Status |
|---|---|---|---|
| Better home and away runs in the league schedules | [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#building-a-league-of-another-size): the disc has one schedule per size, and some send a club to one venue up to 7 times running (the 22-club leagues, UIDs 11, 30, 40, 48) or 9 (the 26-club English second division with your club, UID 1); the 8-club VS league (UIDs 154–155) reaches 5 | `--mod league-balance` rebuilds those seven UIDs with `schedule.balance_pack` (`set_league` at the same size): no more than 2 running, same clubs, game days and turns, and game bit `w0` 8 kept on its day. Only `PARAM/SCHEDULE_COMPETITION.PAC` changes, by 7 entries that keep their size, so its `.HED` and the `STATIONFILE` copy stay. With a league of another size (`leaguesize.py build`) it balances the build's pack, skipping the leagues the build already rebuilt. Checked with England at 22 and France at 18 plus national-cups in one patch. An improvement, so not in `--mod lmaster` | tested in PCSX2 (user report): in a new England career on `LMAST-test-leagues.iso` (with the tutorial skip), the Schedule screen shows the club's league games alternating `AHAHAHAHAHAH…`, and each game's details screen agrees with it, where retail's first 16 in the English second division (UID 1, slot 24 or 25) are `HHAHAAHHAHHHHHAA` or `AAAAHHAAAAAAAHHH`. So the game takes its fixtures from the rebuilt pack. Not played to the end of a season, and the other rebuilt leagues (the 22-club ones, VS) weren't looked at; they are built the same way. `python SRC/schedule.py league DAT/PARAM` shows what it rebuilds |
| A harder economy that punishes mistakes: dearer facilities, a wider ticket price range, dearer advertising, and the like | [`ECONOMY.md`](ECONOMY.md), **confirmed**: a build charges the facility record's cost (`PLRESOURCECOMMON.PAC` entry 0) × the business cycle (75–125%) × any sponsor discount; the plan screen's limits are constants in its set-up (`SIMPRG.REL 0x3eda0`); the ad budget and ticket price set attendance through a 21 × 11 table that only covers prices 60–300 and budgets up to 30,000,000, and the budget adds up to 50 supporter popularity a month; the salary limits, £10,000–£12,000,000 ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#salary-limits)) | `--mod harder-economy`, three switches with the values the user chose (2026-10-23). **`facility-tiers`** (`plrcommon.facility_tiers`, data): build costs and upkeep ×2 for all equipment and adverts; grounds (sites) ×2 and ×4 (their upkeep is never charged); club houses: the starting one's upkeep ×2 (£25,000 → £50,000), the next ×2 (£15M, £150,000), the top ×4 (£60M, £600,000); stadiums: 15,000–25,000 ×2 (£15M, £45,000 a stand), 30,000–40,000 ×3 (£52.5M, £124,500), 50,000–60,000 cost ×5 and upkeep ×4 (£150M, £290,000), 110,000 cost ×3.5 and upkeep ×6 (£350M, close to the record's limit of about £358M; £600,000). The stand costs within a stadium aren't traced, so they stay. **`wider-tickets`** (code and table): both ticket screens go to 480 (£80), and the ticket demand table is respaced over 60–480 in steps of 21: up to 300 the old curve, above it crowds fall as (300 ÷ price)^1.47, so £80 draws half of £50's crowd. **`dearer-ads`** (code): the ad budget buys half as much per pound (popularity budget ÷ 1,200,000, a demand column per 6,000,000) and goes up to 60,000,000 (£10M), so the full effect costs twice as much. The season-ticket status bug is a separate restore candidate (below) | built; not yet tested in PCSX2 (`LMAST-test-economy.iso`, `TODO.md` section 7). The scripts named after season tickets, spectators and popularity are never run ([`SQB_FORMAT.md`](SQB_FORMAT.md#which-scripts-run)); the C code above is what runs |

Ideas for the harder economy (the user's), with what each would change.
The first three are built as `--mod harder-economy` (above); the rest
aren't decided:

| Idea | Where it lives | Known |
|---|---|---|
| Dearer facilities and their upkeep | `PLRESOURCECOMMON.PAC` entry 0 facility records: build cost, a tenth-size second cost at `+0x1c`, upkeep ([`ECONOMY.md`](ECONOMY.md#build-costs)) | **confirmed**: costs and upkeep are data, so this is a data edit; the business cycle and sponsor discounts still scale the build cost |
| A wider ticket price range | the plan screen's limits (`SIMPRG.REL 0x3ef94`, `0x3ef98`) and the ticket demand table (`0x556250`, rows by price, thresholds at `0x556120`) ([`ECONOMY.md`](ECONOMY.md#the-ticket-demand-value)) | **confirmed**: both are fixed at 60–300 (£10–£50). Widening the screen alone makes every price past either end draw the same crowd as that end, so the table needs new rows as well |
| Dearer advertising | the ad budget's limit (`SIMPRG.REL 0x3eec0`) and what it buys: ticket demand up to 30,000,000 and budget ÷ 600,000 supporter popularity a month ([`ECONOMY.md`](ECONOMY.md#what-the-ad-budget-does)) | **confirmed**: payment 17 is a twelfth of the budget a month, so a dearer ad means a smaller effect per pound (change the 600,000 divisor at `0x268ce0` and the table's 3,000,000 step at `0x2719e0` and `0x271a88`), not a higher price |
| Season tickets for top clubs | the status factor in `pwkUnkei_GetExpectSeat` (`0x272838`–`0x2728dc`) | **confirmed** bug: every club status above 10,000 gets 0.6, so the 0.7–1.0 steps for higher status are never reached ([`ECONOMY.md`](ECONOMY.md#season-tickets)). A restore candidate rather than an improvement |
| Dearer overseas bases, investment in them and their upkeep | `PLRESOURCESIM.PAC` entry 1: set-up cost per region and level rates (`_GetOverseasBranchEstablishCapital`, `0x232d88`; [`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md#entry-1-overseas-branches)), payments 18–19 | **confirmed**: the maintenance uses the same two tables, so this is a data edit |
| Merchandise: dearer to stock, bigger margins | income 7 (Merchandise) in the accounts | the sales code isn't traced |
| Reputation harder to raise | club rank (0–31, save `+0xa0`), the world rank points (`SIMPRG.REL 0x151568`) and the status rank (`SAVE_FORMAT.md`, club rank leftovers) | what changes the rank after a match (`0x26ddd8`) and the weights behind the points aren't traced |
| Lesser players dearer, the best up to £250,000,000 (a top tier, a "football icon") | transfer fees (income 9, payments 14) and the price limits ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#salary-limits): transfer fees are kept at £100,000–£120,000,000 by constants in the initializer at `0x24a140`, so a higher cap is a code edit) | how a transfer fee is worked out isn't traced |

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
