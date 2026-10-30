<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# The LMASTER Mod

A mod that restores content the PAL release cut or left broken, and
offers a few improvements. Each restoration and improvement is a
separate `patch_disc.py` switch first, so it can be built and tested in
PCSX2 on its own. The mod comes in three editions, LMASTER lite, full
and max, made of the groups below.

## The switch levels

The switches come in three levels, and `--mod` takes a name of any
level:

1. **Editions**: `lmaster-lite` (also `lmaster`), `lmaster-full` and
   `lmaster-max`, each a list of groups.
2. **Groups**: features that each work alone. Every switch is in
   exactly one group.
3. **Switches**: one feature each. Parts that need each other are one
   switch (the third tier's five parts are `third-tier`), and machinery
   is no switch: `third-tier` turns on `mod-saves` itself.

| Group | Switches | Lite | Full | Max |
|---|---|---|---|---|
| `training-fixes` | camp-types, camp-cities, camp-santiago, camp-clubs, drill-names | yes | yes | yes |
| `injury-fixes` | injury-value, injury-row | yes | yes | yes |
| `club-fixes` | sponsor-negotiation, season-status, pr-cycle, mobile-site, overseas-pop, cup-last16 | yes | yes | yes |
| `match-fixes` | rival-manager, national-cups, vpf-styles | yes | yes | yes |
| `text-fixes` | retail-text ([below](#retail-text-fixes)) | yes | yes | yes |
| `leagues` | league-balance, third-tier | – | yes | yes |
| `restorations` | injury-lines | – | yes | yes |
| `names` | real-names, own-stadium ([below](#real-names)) | – | yes | yes |
| `stadiums` | special-stadium, real-grounds, sponsor-boards ([below](#stadiums)) | – | yes | yes |
| `saves` | mod-saves | – | yes | yes |
| `harder-economy` | facility-tiers, wider-tickets, dearer-ads, sponsor-fees, tv-fees, season-demand ([`ECONOMY.md`](ECONOMY.md)) | – | – | yes |
| `balance` | injury-odds, overseas-bases, transfer-fees, fee-tiers, slow-reputation, fanbase, merch-costs, pr-costs, camp-costs, tour-costs ([below](#improvements)) | – | – | yes |
| `test-tools` | skip-tutorial, launcher | – | – | – |

LMASTER full is the fixes, the third tier, the balanced league
schedules, the restored injury lines and the real names; LMASTER max adds the two
difficulty groups, `harder-economy` and `balance` (the user's split,
2026-10-27). Until then `lmaster-full` held what `lmaster-max` holds
now, so the test reports before that date that name a full disc mean
today's max.

Full and max always include `mod-saves`, so their careers and VS data go
to their own memory-card folders and never mix with the retail game's
([`SAVE_FORMAT.md`](SAVE_FORMAT.md#separate-saves-for-a-modded-disc)).
Full's careers go to `BESLES-54151-Fnnn` and max's to `-Mnnn`:
`mod-saves` takes `M` whenever a difficulty switch is on, since a career
from a disc whose economy and injuries work differently isn't one to
load on another. The VS data of both goes to `BESLES-54151-Vnnn`, as a
VS team is the same on either. `G` and `C` stay the retail game's
career and VS folders. The tutorial skip and the developers' launcher
are test tools, in no edition.

`patch_disc.py switches` prints the tree. The editor's Build disc window
(File > Build disc) draws it: a button for each edition ticks its groups
(leaving the test tools as they are), each group has a box that ticks
all its switches, and the switches show under a group when it is opened.
The box of a partly ticked group shows as partly ticked, the window
names the edition and the save letters the choice gets, and the build
command names the highest levels that fit (`patch_disc.mod_names`:
`--mod lmaster-max,skip-tutorial`, or `lmaster-full,balance` and single
switches when a group is partly ticked). A disc built with the level
names is byte for byte the one the switch lists built (checked on
`LMAST-test-full-germany.iso`, 2026-10-27), and a max disc differs from
the earlier full build in the VS letter alone (one byte, checked on
`LMAST-test-max-germany.iso`). A test disc of each edition (full and max
need `--copies` and `--dat` for the third tier):

```bash
python SRC/patch_disc.py patch "Let's Make a Soccer Team! (Europe, Australia) (En,Fr,De,Es,It).iso" lmaster-lite.iso --mod lmaster-lite
python SRC/patch_disc.py patch "Let's Make a Soccer Team! (Europe, Australia) (En,Fr,De,Es,It).iso" lmaster-full.iso --mod lmaster-full --copies --dat DAT
python SRC/patch_disc.py patch "Let's Make a Soccer Team! (Europe, Australia) (En,Fr,De,Es,It).iso" lmaster-max.iso --mod lmaster-max --copies --dat DAT
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
| Kind-6 injuries starting at 1600 | broken data (dropped digit?), in both releases | [`INJURIES.md`](INJURIES.md#the-value-table-0x532cf8): `0x532d70` holds 1600 where 16001 fits | `--mod injury-value`: the u16 at `0x532d70` → 16001 | built; how `calcKegav` uses the table is confirmed, but the effect isn't checked in the game (kind-6 injuries are rare and random) |
| Injury rows past fatigue 1000 | bug (out-of-bounds read) | [`INJURIES.md`](INJURIES.md#the-kind-tables): row 11 for ages 35+ | `--mod injury-row`: the row clamped to 10 in `judgeKegaKind`'s own words (`0x21a08c`, 6 words) | built; checked in a MIPS simulator over 18,018 cases (only the six out-of-bounds ones change), not in the game (rare) |
| "Two months" and "nine months" injury lines | cut before both releases (the Japanese code is the same) | [`INJURIES.md`](INJURIES.md#the-condition-line): `plPinfo_KegaRecoverDaysChno` never returns chno 3 or 6; French, German, Italian and Spanish hold "See Let's Make revised text 0425" | `--mod injury-lines`: the heavy ladder (`0x216e14`, 15 words) gets thresholds 4,000 (two months) and 12,500 (nine months), and messages 4 and 7 of category 200 get text in the four languages, in the placeholders' bytes ([`INJURIES.md`](INJURIES.md#the-two-cut-lines-back-injury-lines)). It adds new text and shows lines the released game never did, so it is in `--mod restorations` (LMASTER full and max), not lite | built (thresholds chosen 2026-10-24); not checked in the game |
| Training camps train as the next camp type | bug (off by one), in both releases | [`CAMP_FORMAT.md`](CAMP_FORMAT.md#two-bugs): `CAMP_LIST` numbers the types 1–87, the training table and the theme check read them as 0–86; Parma, a goalkeeper camp, trains no keeping | `--mod camp-types`: every type lowered by one in `CAMP_LIST.TBB` | tested in PCSX2: one keeper camp raised all three keepers' saving, aerial ability and GK aptitude most (559–617 experience), then catching and rushing out (444–488), and left pace and acceleration alone, the fixed row's pattern ([`CAMP_FORMAT.md`](CAMP_FORMAT.md)) |
| Seven English camps in the wrong town | PAL left the camp tables on the Japanese city numbers when it renumbered the English cities | [`CAMP_FORMAT.md`](CAMP_FORMAT.md#seven-english-camps-in-the-wrong-town-pal): Liverpool's camp is in Scunthorpe, Manchester's in West London, and five more | `--mod camp-cities`: the seven city ids in `CAMP_LIST.TBB` and `CAMP_EXPLANE.TBB` | tested in PCSX2 (user report): with low popularity the England list shows Southampton, Blackburn and Sheffield, not Basingstoke, Newport and Oakham. The other four need more popularity (Liverpool a sponsor) and weren't seen; the switch moves them the same way |
| Santiago's camp description | bug (wrong city id), in both releases | [`CAMP_FORMAT.md`](CAMP_FORMAT.md): `CAMP_EXPLANE` keys message 6146 to city 764, the camp is 774; the lookup (`SIMPRG.REL 0xa4a80`) finds nothing | `--mod camp-santiago`: the description's city 764 → 774 in `CAMP_EXPLANE.TBB` | tested in PCSX2 (user report): Santiago's camp shows "The Chilean capital is a hub of South American finance …" |
| Canberra's last two camp clubs | bug (loop bound), in both releases | [`CAMP_FORMAT.md`](CAMP_FORMAT.md): `SIMPRG.REL 0x4c8f8` reads 735 of `CAMP_LIST` table 1's 737 pairs, so Fukuoka and Kanagawa never appear | `--mod camp-clubs`: the bound `0x2de` → `0x2e0` at `SIMPRG.REL 0x4c9d4` (one instruction; whole disc image) | tested in PCSX2 (user report): Canberra's camp lists South Melbourne, Aichi, Fukuoka and Kanagawa |
| Drills 75–86 under the next drill's name | broken text (PAL: names one message early, an added "Jackknife") | [`TRAINING_FORMAT.md`](TRAINING_FORMAT.md#drills-7486-pals-names-are-one-early): practice *n*'s name is message 971 + *n* of category 801; the Japanese names (both discs) and the training rows have a dummy at 74 that no coach teaches, PAL's names in all five languages start one early, so the drill named "Pass training." trains shooting | `--mod drill-names`: messages 1045–1056 → 1046–1057 in `801_1`–`6.mbb` of `MES.PAC` and their copies in `PRELOAD/SIMFILE1`–`6.PAC` (entry 28); the jackknife name goes to the dummy's 1045, so the files keep their sizes. No new text; a `MES.PAC` target gets the fix in its own bytes | tested in PCSX2 (user report): coach R.Bloemzaad's drill 76 (short and long pass, cross) reads "Dribble training" on the retail disc and "Pass training." on `LMAST-test-drills.iso` |
| Play styles of an imported Virtua Pro Football player | bug (a compare function that subtracts pointers) | [`PMPLAYER_FORMAT.md`](PMPLAYER_FORMAT.md#the-record): the import's qsort compare (`SAVEPRG.REL 0x3df00`) never reads the ratings, so slot t keeps style t when rated 70+, and 18 of the 22 VPF styles never come in; G.Binns, rated 86 in a style that doesn't count, came in with none | `--mod vpf-styles`: the compare's 4 words load both ratings and return b − a through the tail of the executable's `strcmp`, and one more rates style 0 ("none") at 0 in the sorted copy so it never takes a slot ([`PMPLAYER_FORMAT.md`](PMPLAYER_FORMAT.md#the-record)) | restored, tested in PCSX2: an edited V. Drake came in with four styles in slots 1–4 where the retail import gives one |
| Retail text: wrong leagues in two Game Over conditions, the Spanish intro's club count, "AL-Hyde" | broken text, in PAL | [Retail text fixes](#retail-text-fixes) | `--mod retail-text` (lite): the messages' own text in `MES.PAC`, and the name's `STATIONMES` copies | built 2026-10-30 (test disc `LMAST-test-names.iso`); not checked in the game |
| Made-up league, competition and club names | licensing (the retail game names unlicensed clubs after their cities or grounds) | [Real names](#real-names) | `--mod real-names` (full and max): `SRC/realnames.csv`'s names, the stadiums' too, in `MES.PAC`'s name lists and the English mentions, with `--copies`; `--mod own-stadium` names your stadium after you | built 2026-10-30 (test disc `LMAST-test-names.iso`, read back from the image); not checked in the game. The 75 non-English mentions are left for edits by hand |
| Crest presets 4–11 in three tables | broken data (a missing byte) | [`EMBLEM_DIR.md`](EMBLEM_DIR.md): tables 93, 101, 105 of `EDIT_EMBLEM.TBB` | add the missing `04 00` key | candidate. Check first whether the crest editor shows the gap |
| The rival's manager by style | bug (wrong register), in both releases (Japanese `0x25e8e8`) | [`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#the-rival-club-tables-6-7-and-8): the loop at `0x25e6d0` finds the record for the rival's style, but its load reads record 0, so the rival always gets H.Raphanel (898), never I.Ricardo (1,970), L.Alfano (1,247) or L.Nobili (1,246) | one instruction at `0x25e6d8`: `lw $s3, 8($a0)` (`8c930008`) becomes `lw $s3, 4($v1)` (`8c730004`). The rival's style is already the opposite of yours (`0x5531e0`), so its manager then matches it. `--mod rival-manager` | fixed, tested in PCSX2 (user report): in a new Teamwork career in England, the rival SC Dunstable's Information screen showed a different policy area (the big blue area on the right, which follows the manager) from the unpatched game. The game never shows the rival manager's name. The other three styles weren't tried |
| The World National Cup final on the last turn of the year | bug (schedule data) | the knockout UID 122 plays turns 92–95, and 95 is the year's last turn ([`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#turns)), so the season ends on the turn of the final and its results can't be viewed in the Competition menu (user report). The group UIDs 114–121 play 89–91. The Euro National Cup ends on 94 | move both national cups back one turn (`schedule.py shift`, masks and start turns; the end turn stays 95): World Cup groups 88–90 and knockout 91–94, Euro groups 88–90 and knockout 91–93. No league or cup plays after turn 87, and the two cups are in different years of the cycle. The national-team calendar ([`SCHEDULE_LIST.TBB`](PARAM_DIR.md#schedule_listtbb-the-national-team-calendar)) moves with them: match days 88–94 and 88–93, release on the final's turn, and the call-up on 88 with the first group game (87 has the second-division play-off finals). `--mod national-cups` writes `SCHEDULE_SYSTEM.PAC` and its copy in `PRELOAD/STATIONFILE.PAC`, and `SCHEDULE_LIST.TBB` and its copies in `PRELOAD/SIMLOCALMEM0`–`6.PAC`. With a league of another size (`leaguesize.py build`, patched with `--copies`), it moves the cups in the league build's `SCHEDULE_SYSTEM.PAC` instead: a rebuilt league keeps its first and last game day, so it never reaches turn 88. Checked with England at 22 clubs: one build holds both, and `schedule.py info` finds no new problems | tested in PCSX2 (user reports): the Schedule screen's globes follow the new calendar (Euro year 2007-08: turns 88–93, week 4 empty; World Cup year 2009-10: turns 88–94, week 4 late empty). The World Cup's results after its final aren't seen, since that year is the fourth season of a career, but are taken to work: in the retail game the Euro National Cup's final is on turn 94 and its results can be viewed in the Competition menu after it (user report). The moved World Cup final is on that same turn, and both cups' knockouts are built the same way (an end turn of 95 and the same flag); the bug came only from a final on the last turn |
| Season-ticket demand by club status | bug (branch order), in both releases (Japanese `0x2728f0`) | [`ECONOMY.md`](ECONOMY.md#season-tickets): `pwkUnkei_GetExpectSeat` has factors 0.5–1.0 for status bands of 10,000, but its first test takes every status over 10,000, so no club gets more than 0.6 | `--mod season-status`: the ladder (`0x272840`, 31 words) rewritten as a straight run of the intended bands | restored, tested in PCSX2: a top-status club put 88,000 season tickets on sale and sold 72%, the fixed band's value (43% on retail; [`ECONOMY.md`](ECONOMY.md#season-tickets)). Makes big clubs richer, so with `--mod harder-economy` it softens `season-demand` |
| PR events and the business cycle | bug (branch order), in both releases (Japanese `0x20e7f0`) | [`ECONOMY.md`](ECONOMY.md#pr-events): each event holds +20, +10, −5, −10 for business cycles 0, 1, 3 and 4, but `plClubEvent_Execute`'s ladder reads byte 2 for 0–1, byte 4 for 2 and byte 3 for 3–4, so the boom's +20 never applies and an average economy takes 10% off every event (41% success instead of 51%) | `--mod pr-cycle`: the ladder's first 11 words (`0x20dfb0`) read the byte of each cycle, none for cycle 2 | built 2026-10-25; not checked in the game |
| PR event 37, Renew Mobile Site | cut (one store clears it), in both releases (Japanese `0x20f108`) | [`CLUBEVENT_FORMAT.md`](CLUBEVENT_FORMAT.md#the-offer-record-32-bytes): its three records are complete (from 2010–11, popularity 30,001, Jan–Aug, £50,000, +200 home and overseas popularity) and its mail texts are in `MES.PAC` (563: 11233–11234, the report 1290–1291), but `plClubEvent_GetList` clears its flag after every check (`sw $zero, 0xa4($sp)` at `0x20e868`) | `--mod mobile-site`: that store becomes a nop, so the event follows its own record like Renew Home Page | built 2026-10-26 (test disc `LMAST-test-mobile.iso`); not checked in the game |
| Overseas popularity ten times as fast with a rank-2 player | broken data (a misplaced decimal point), in both releases (Japanese `0x550bf8`) | [`ECONOMY.md`](ECONOMY.md#supporter-popularity): the overseas factor by your best player's rank from that region (`0x554ec8`) runs 1.02, 1.05, 10.8, 1.11, … in steps of 0.03, so a best player of rank 2 multiplies the monthly, match and title changes there by 10.8 | `--mod overseas-pop`: the float at `0x554ed0` becomes 1.08 | built 2026-10-26, confirmed from the code (the disassembled patch reads as intended). No in-game test: player rank and popularity are hidden, so a rank-2 player can't be picked out on screen |
| No European Club Cup popularity for the last 16 | bug (compares the wrong competition), in both releases (Japanese `0x268aec`) | [`ECONOMY.md`](ECONOMY.md#titles): `0x268858` gives the 4th points column (European League 120, European Club Cup 60) to places 8–15 only for compe 34 and to places 16–31 only for 35, so the European Club Cup pays its last-32 losers and not its last-16 ones | `--mod cup-last16`: places 8–15 get the column for both cups and 16–31 none. `xori $v1, $v1, 0x22` at `0x26894c` becomes `sltiu $v1, $v1, 0x24` (1 for 34 and 35), `xori $v1, $v1, 0x23` at `0x26896c` becomes `move $v1, $zero`, and the shared `movz` at `0x268970` becomes `movn` | filed by the user and built 2026-10-26, confirmed from the code (the disassembled patch reads as intended). No in-game test: the points are hidden, and a last-16 exit takes a long run |
| 475 combination records that never load | unused data (and a repeat check that only works for pattern 1) | [`BPB_FORMAT.md`](BPB_FORMAT.md#how-a-team-uses-the-combinations): `0x14c3f0` takes a team's records only from three 12-entry tables (`GAMEPRG.REL 0x28c7f0`, `0x28c820`, `0x28c850`) and from `0x24a5e8`[pattern − 1], the first of each attack pattern's 16. So 15 of each 16 (450 records, same script as the first, slightly different areas, no distance limits) and 25 basic records in no table never load. 22 of those 25 could start; 0, 1 and 18 have block A kind 1, which never triggers | **Basic records (data only):** swap entries of the three tables, same size, at their file offsets in `DLL/GAMEPRG.REL` (a `disc:` target). The duplicate 12 in set 0 is a free slot. More than 12 a set needs bigger tables: no free bytes follow them (strings do), so a new table elsewhere in the image, its address in the `lui`/`addiu` pairs at `0x14c484`/`0x14c488`, `0x14c4fc`/`0x14c504` and `0x14c56c`/`0x14c574` (local relocations, so only the immediates change), and the shuffle's count 12 (`addiu $a2, $zero, 0xc` at `0x14c468`, `0x14c4f4`, `0x14c564`). **Pattern variants (code):** a random 0–15 added to `0x24a5e8`[*p* − 1] in both branches of `0x14c3f0` (`fcEuroRand_Get0toI`, as `0x14c6f8` calls it), which needs room for the extra call: rewrite the branch's three repeated loads as one. A data-only fallback points `0x24a5e8`[*p* − 1] at another fixed variant. **Repeat check:** compare with the record (`0x24a5e8`[*p* − 1]), not *p* + 60, at `0x14c718`. Each change needs its Japanese addresses through `gamever.py` | candidate. Check first whether the extra records play sensibly: their areas are untested, and only the first of each 16 has distance limits. The effect is hard to see in a match, so a test needs a way to tell which combination ran (PINE: the controller, the team's `+0x1788`, keeps the running entry at `+0x6c0` (`0xc1af0`); that entry's `+0x80` points at the combination, whose `+0x4c` is the record) |
| 32 dialogue categories | cut before both releases (no reference in the Japanese code either) | [`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md): derby interviews, a facilities tour, notices | needs triggers in the event system and English text | research |
| The manager's match policy | bug? (reads the wrong field), in both releases (Japanese `GAMEPRG.REL 0xd8f44`, `0xf34e8`) | [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#the-developers-staff-editors): nothing reads the match policy (`PlTeamData +0x4889`); the match's tactic shifts by period and score (`GAMEPRG.REL 0xd96e8`) and what looks like its substitution tables (`0xf3cb0`) read the selection policy (`+0x4888`) instead, in groups that fit the match policy's names (act boldly and change tactics a lot together, "rarely change" in the mildest group) | two instructions: the offset `0x4888` → `0x4889` in `lbu $s2, 0x4888($v0)` at `GAMEPRG.REL 0xd970c` (`90524888` → `90524889`) and `lbu $v1, 0x4888($sp)` at `0xf3cb0` (`93a34888` → `93a34889`), through `gamever.py` for the Japanese ones | candidate. Check first in the game that the selection policy changes a computer club's in-match tactics or substitutions (`TODO.md` section 7) |
| Tactics of a much stronger club | bug? (a missing case), in both releases (Japanese `0x22f46c`) | [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#the-developers-staff-editors): `plTeam_SetStyleTeamParam` picks a column of slider steps (`0x534438`) from the strength ratio; above 1.19 it gives column 0, the same as up to 0.79, and column 4 (the opposite steps) is never used | one instruction at `0x22ef8c`: `movn $v1, $zero, $v0` (`0002180b`) becomes `addu $v1, $v1, $v0` (`00621821`), so the column is 3 + (ratio > 1.19). `$v0` is overwritten by the next instruction | candidate. Check first which end of a slider (0–6) is attacking: only then is it clear that column 4 was meant for the stronger club |
| Coach's training plan by policy | broken data (rows out of step with the names), in both releases (Japanese `SIMPRG.REL 0x224d70`) | [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md#the-developers-staff-editors): the plan has 6 rows (`SIMPRG.REL 0x228cc0`) for 8 training policies; man-marking (3) gets the physical row, physical (4) the formation row, and formation, condition and match practice (5–7) the match row | needs two more rows (a man-marking one and a condition one, written new) and the clamp `slti $v0, $t1, 6` at `SIMPRG.REL 0xf0850` raised to 8. No free bytes follow the table (other data does), so the 8 rows need room elsewhere and the table's `lui`/`addiu` at `0xf06a8`/`0xf06b0` pointed there. Six rows can't fit eight names whatever their order | candidate. Only the player's own club uses the plan (computer clubs train without it), so decide first whether new rows are worth it |

## Improvements

Not restorations: changes to data that works but plays badly. They
follow the same rules (evidence, smallest change, tested in PCSX2) and
stay separate switches, so the restorations can be used without them
(LMASTER lite). LMASTER full has the league schedules, and LMASTER max
all of them. `--mod harder-economy` and `--mod balance` are the
difficulty groups, in max only; `balance` is the switches built
2026-10-24 to 26 with the values the user chose (the groups' lists are
in [the switch levels](#the-switch-levels); `injury-lines` is in
[Status](#status), and in `--mod restorations`).

| Change | Evidence | Fix | Status |
|---|---|---|---|
| Better home and away runs in the league schedules | [`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md#building-a-league-of-another-size): the disc has one schedule per size, and some send a club to one venue up to 7 times running (the 22-club leagues, UIDs 11, 30, 40, 48) or 9 (the 26-club English second division with your club, UID 1); the 8-club VS league (UIDs 154–155) reaches 5 | `--mod league-balance` rebuilds those seven UIDs with `schedule.balance_pack` (`set_league` at the same size): no more than 2 running, same clubs, game days and turns, and game bit `w0` 8 kept on its day. Only `PARAM/SCHEDULE_COMPETITION.PAC` changes, by 7 entries that keep their size, so its `.HED` and the `STATIONFILE` copy stay. With a league of another size (`leaguesize.py build`) it balances the build's pack, skipping the leagues the build already rebuilt. Checked with England at 22 and France at 18 plus national-cups in one patch. An improvement, so not in LMASTER lite | tested in PCSX2 (user report): in a new England career on `LMAST-test-leagues.iso` (with the tutorial skip), the Schedule screen shows the club's league games alternating `AHAHAHAHAHAH…`, and each game's details screen agrees with it, where retail's first 16 in the English second division (UID 1, slot 24 or 25) are `HHAHAAHHAHHHHHAA` or `AAAAHHAAAAAAAHHH`. So the game takes its fixtures from the rebuilt pack. Not played to the end of a season, and the other rebuilt leagues (the 22-club ones, VS) weren't looked at; they are built the same way. `python SRC/schedule.py league DAT/PARAM` shows what it rebuilds |
| A harder economy that punishes mistakes: dearer facilities, a wider ticket price range, dearer advertising, and the like | [`ECONOMY.md`](ECONOMY.md), **confirmed**: a build charges the facility record's cost (`PLRESOURCECOMMON.PAC` entry 0) × the business cycle (75–125%) × any sponsor discount; the plan screen's limits are constants in its set-up (`SIMPRG.REL 0x3eda0`); the ad budget and ticket price set attendance through a 21 × 11 table that only covers prices 60–300 and budgets up to 30,000,000, and the budget adds up to 50 supporter popularity a month; the salary limits, £10,000–£12,000,000 ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#salary-limits)) | `--mod harder-economy`, six switches with the values the user chose (2026-10-23). The cost side: **`facility-tiers`** (`plrcommon.facility_tiers`, data): build costs and upkeep ×2 for all equipment and adverts; grounds (sites) ×2 and ×4 (their upkeep is never charged); club houses: the starting one's upkeep ×2 (£25,000 → £50,000), the next ×2 (£15M, £150,000), the top ×4 (£60M, £600,000); stadiums: 15,000–25,000 ×2 (£15M, £45,000 a stand), 30,000–40,000 ×3 (£52.5M, £124,500), 50,000–60,000 cost ×5 and upkeep ×4 (£150M, £290,000), 110,000 cost ×3.5 and upkeep ×6 (£350M, close to the record's limit of about £358M; £600,000). The stand costs within a stadium aren't traced, so they stay. **`wider-tickets`** (code and table): both ticket screens go to 480 (£80), and the ticket demand table is respaced over 60–480 in steps of 21: up to 300 the old curve, above it crowds fall as (300 ÷ price)^1.47, so £80 draws half of £50's crowd. **`dearer-ads`** (code): the ad budget buys half as much per pound (popularity budget ÷ 1,200,000, a demand column per 6,000,000) and goes up to 60,000,000 (£10M), so the full effect costs twice as much. The income side, for the late game (chosen 2026-10-23): **`sponsor-fees`** and **`tv-fees`** (tables in `SIMPRG.REL`) keep a sponsor fee or TV offer up to £2M and halve the part above (£45M → £23.5M, the £50M TV offer → £26M; G006's TV £31.2M → £19.1M a season); **`season-demand`** (code) halves season-ticket demand (G006 would sell about half its 36,000, £20.5M → about £10.5M). The season-ticket status bug is fixed separately, by the restoration `--mod season-status` ([Status](#status)) | tested in PCSX2 (user report, `LMAST-test-economy.iso` with `--mod harder-economy`): the facility window showed the tiered costs, the plan screen and the other competitions' ticket screen went to £80 and the ad budget to £10M, and a home match at the new prices drew a crowd; "all seems fine". The three income switches were then tested on the same disc with all six (user report: sponsor fees, TV offers and season-ticket sales as on the test sheet; "all fine"). Not yet played through a whole season. The scripts named after season tickets, spectators and popularity are never run ([`SQB_FORMAT.md`](SQB_FORMAT.md#which-scripts-run)); the C code above is what runs. Played through a season with every max switch (user report, 2026-10-27, a German career on an LMASTER max build): the fanbase grows much more slowly, as the ad budget's halved popularity (`dearer-ads`) predicts, and the game feels much harder economically |
| Long injuries more common | [`INJURIES.md`](INJURIES.md#the-kind-tables), **confirmed**: a heavy match injury is six months or more 0% of the time for a rested player and 39% at full fatigue, so rotation all but rules them out | `--mod injury-odds`: kinds 4–8 doubled in every row of both kind tables, to at least 2% (practice) and 5% (match) of a row, taken from kind 3 and then kind 0 so light match injuries stay as they were; a heavy match injury is then six months or longer 5% of the time rested and 78% at full fatigue ([`INJURIES.md`](INJURIES.md#more-long-injuries-injury-odds)) | built; not checked in the game |
| Overseas bases: dearer, each pound buying half as much | [`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md#entry-1-overseas-branches), **confirmed**: one cost per region sets the set-up, the investment per level and the upkeep; the level (0–3) scales the region's popularity change by 0.6–1.2 | `--mod overseas-bases`: the 13 costs doubled in `PLRESOURCESIM.PAC` and its `SIMLOCALMEM0`–`6` copies, so the investment per level and the upkeep double too; what a level does stays as in retail (the user's choice, 2026-10-26: like `dearer-ads`) | built; not checked in the game |
| Reputation harder to raise | [`SAVE_FORMAT.md`](SAVE_FORMAT.md), **confirmed**: the club status (your club rank is status >> 11) rises after each match (win and draw factors at `0x399668`), at final places (points at `0x555188`, `0x555260`, `0x555288`) and by 500 each year end (`0x26e2c4`) | `--mod slow-reputation`: every gain halved, losses as before (the user's choice, 2026-10-26) | tested in PCSX2 (save states, 2026-10-27): a league win gained 47 status where retail gives 95 ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far)). The club status is hidden in game (user report), so it is read from saves or save states. The year-end and final-place halves aren't seen yet |
| Transfer fees by player rank: lesser players dearer, the best up to £250M | [`ECONOMY.md`](ECONOMY.md#transfer-fees), **confirmed**: the player's rank enters the fee only through table A (`0x398478`, 16 ranks × 6 club-rank bands), which only the fee function reads | `--mod fee-tiers`: table A's rows ×2 for ranks 0–5, ×1.5 for 6–11, ×2 for 12–14 and ×3 for rank 15 (the user's choice, 2026-10-26); with `transfer-fees` the best player at a top club reaches about £246M | tested in PCSX2 at the low end (user report, 2026-10-27, a German career on an LMASTER max build): lesser players' fees about 4× retail, with `transfer-fees`; a fee above £120M not yet seen |
| Transfer fees higher, up to £250M | [`ECONOMY.md`](ECONOMY.md#transfer-fees), **confirmed**: one base (1,350,000.0, `0x247288`) starts every fee you pay and every offer you get; price kind 1 caps them at £120M | `--mod transfer-fees`: the base 2,700,000.0 and the cap 15,000,000 (£250M) in all four currencies (`0x24a1c8`–`0x24a21c`) | tested in PCSX2 (user report, 2026-10-25): fees doubled; a save state holds the 15,000,000 cap in all four currencies. A fee above £120M, and any limit of the transfer screens, not yet seen ([`ECONOMY.md`](ECONOMY.md#transfer-fees)) |
| A bigger fanbase counts for more | [`ECONOMY.md`](ECONOMY.md#merchandise), **confirmed**: merchandise starts from a base by supporters, a flat table (12.5× from the smallest fanbase to the biggest); crowds and season tickets weigh popularity against a fixed part; TV offers vary only 0.9–1.15 by popularity | `--mod fanbase`: the merchandise bases ×0.5 at the bottom to ×3 at the top (`SIMPRG.REL 0x1d9ec8`), popularity weighted 195 for 130 and the fixed part 1,500 for 3,000 in crowds and season tickets, and the TV factor 0.75–1.25 | merchandise income much lower (user report, 2026-10-27, a German career on an LMASTER max build), as the halved bases of a small fanbase and `merch-costs` predict; the top of the scale, crowds and TV offers not yet compared. Goods prices stay, and their costs are `merch-costs` (below) |
| Dearer PR events | [`ECONOMY.md`](ECONOMY.md#pr-events), **confirmed**: an event costs its record's `+0x14` × 300, £5,000–£500,000 | `--mod pr-costs`: × 600 (`0x20deec`), so the booking and the refund both double | tested in PCSX2 (user report, 2026-10-27, a German career on an LMASTER max build): PR events cost double |
| Dearer camps and tours | [`ECONOMY.md`](ECONOMY.md#camps-and-tours), **confirmed**: rates by camp level and region, and by tour region, × the squad × 300; a tour earns £1.2M–£6.3M against under £1M | `--mod camp-costs`: the camp rates × 2 (`SIMPRG.REL 0x1ce4e8`); `--mod tour-costs`: the tour rates × 3 (`0x1ce6c0`), so a tour where the club is little known about breaks even. Tour income unchanged | built; not checked in the game |
| Dearer merchandise stock, smaller margins | [`ECONOMY.md`](ECONOMY.md#making-the-stock), **confirmed**: a unit of stock costs 30% of its price, less a bulk discount of up to 40%, paid when ordered (payment 22), so goods sell at margins of 70–82% | `--mod merch-costs`: the unit cost 50% (`SIMPRG.REL 0xbcce4`) and the discounts halved, down to 80% for the biggest lot (`0x1d10d8`); margins 50–60% | tested in PCSX2 (user report, 2026-10-25): orders cost half the price a unit, the biggest lot gets 20% off, margins 50% ([`ECONOMY.md`](ECONOMY.md#making-the-stock)) |

Ideas for the harder economy (the user's), with where each lives. All
are built now: the first three as `--mod harder-economy`, the fourth as
`--mod season-status` and the rest in `--mod balance` (above):

| Idea | Where it lives | Known |
|---|---|---|
| Dearer facilities and their upkeep | `PLRESOURCECOMMON.PAC` entry 0 facility records: build cost, a tenth-size second cost at `+0x1c`, upkeep ([`ECONOMY.md`](ECONOMY.md#build-costs)) | **confirmed**: costs and upkeep are data, so this is a data edit; the business cycle and sponsor discounts still scale the build cost |
| A wider ticket price range | the plan screen's limits (`SIMPRG.REL 0x3ef94`, `0x3ef98`) and the ticket demand table (`0x556250`, rows by price, thresholds at `0x556120`) ([`ECONOMY.md`](ECONOMY.md#the-ticket-demand-value)) | **confirmed**: both are fixed at 60–300 (£10–£50). Widening the screen alone makes every price past either end draw the same crowd as that end, so the table needs new rows as well |
| Dearer advertising | the ad budget's limit (`SIMPRG.REL 0x3eec0`) and what it buys: ticket demand up to 30,000,000 and budget ÷ 600,000 supporter popularity a month ([`ECONOMY.md`](ECONOMY.md#what-the-ad-budget-does)) | **confirmed**: payment 17 is a twelfth of the budget a month, so a dearer ad means a smaller effect per pound (change the 600,000 divisor at `0x268ce0` and the table's 3,000,000 step at `0x2719e0` and `0x271a88`), not a higher price |
| Season tickets for top clubs | the status factor in `pwkUnkei_GetExpectSeat` (`0x272838`–`0x2728dc`) | **confirmed** bug: every club status above 10,000 gets 0.6, so the 0.7–1.0 steps for higher status are never reached ([`ECONOMY.md`](ECONOMY.md#season-tickets)). Built as the restoration `--mod season-status` (above) |
| Dearer overseas bases, investment in them and their upkeep | `PLRESOURCESIM.PAC` entry 1: set-up cost per region and level rates (`_GetOverseasBranchEstablishCapital`, `0x232d88`; [`PLRESOURCESIM_FORMAT.md`](PLRESOURCESIM_FORMAT.md#entry-1-overseas-branches)), payments 18–19 | built as `--mod overseas-bases` (above) |
| Merchandise: dearer to stock, bigger margins | income 7 (Merchandise), `pwkGd_GoodsMonthlySales` ([`ECONOMY.md`](ECONOMY.md#merchandise)) | built as `--mod merch-costs` (dearer stock, margins 50–60%) and `--mod fanbase` (sales by fanbase), above ([`ECONOMY.md`](ECONOMY.md#making-the-stock)); the shop prices (shop list `+0x8`, `0x241a00`) stay |
| Reputation harder to raise | your club rank is the club status >> 11 ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#fields-found-so-far)) | built as `--mod slow-reputation` (above) |
| Lesser players dearer, the best up to £250,000,000 (a top tier, a "football icon") | transfer fees (income 9, payments 14) and the price limits ([`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#salary-limits)) | built as `--mod transfer-fees` and `--mod fee-tiers` (above) |

Built as `--mod third-tier` (the user's idea, design agreed
2026-10-26): **a third tier and a harsher end.**

The design:

- Every nation has a third tier that isn't played on screen, in all six
  leagues, whether you play there or not.
- Only the second division's **last** club goes down each season, and
  one third-tier club, chosen at random, comes up.
- In your own nation only, two clubs start in the third tier, sent down
  from the second division at the start, so the second division with
  your club and the rival in it has its real size (England 24). The
  other nations' second divisions don't take your club and the rival,
  so they keep their clubs, and their third tiers start with their
  three real clubs (the user's correction, 2026-10-27). One club down
  and one up each season keeps every tier at its starting size.
- A player who finishes last in the second division loses at once,
  after one season, so they never end up in the third tier.
- Third-tier clubs should still show in the other clubs' club info and
  in the world rankings, if the game allows it.

What is known so far:

- **The game over.** **Confirmed** (`SIMPRG.REL 0x15d958`): from 2007,
  with your club in the second division, the game ends when your final
  rank in each of the last two seasons is past the division's line,
  which `0x15d8f0` takes from the `down` place slots of its
  `REGULATION.TBB` row (the club count less the slot's count). The
  warning before it (`0x15da60`) uses this season's live rank and last
  season's. `patch_disc.py --mod third-tier` (built as `one-season-end`)
  makes both decide on one season (not checked in the game). With the
  down count at 1, the line is the last place.
- **A third tier was planned.** **Empirical**: every second division's
  `REGULATION.TBB` rows, own-nation and other-nation versions (UIDs 1
  and 2, 11–12, 20–21, 29–30, 39–40, 48–49), send their bottom two
  "down" to a competition the disc has no schedule for: 50 England, 51
  France, 52 Germany, 53 Italy, 54 Spain, 55 Netherlands. The past
  records' seed table (`PLRRSRC_INITTEAMDATA.TBB` table 1) has 56
  competition rows, of which the game reads 49
  ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)). So the six third tiers
  look like a cut feature, and competitions 50–55 are where they would
  go.
- **The third tiers are named and have clubs.** Competitions 50–55 are
  "English League 1", "French League Division 3", "Third German
  League", "Italian League C", "Spanish League Division 3" and "Third
  Dutch League" (message category 100009). Their UIDs, 142–147
  (`first-promote`, turns 93–95), are the tutorial's promotion playoff:
  your club (team 1) against three clubs of that nation's third tier
  (**empirical**, `schedule.py entry DAT/PARAM 142`): England's 442–444
  are Gillingham, Nottingham and Rotherham, France's 445–447 Angers,
  Valence and Niort, Germany's 448–450 Essen, Oberhausen and Trier,
  Italy's from 451 Genova and Venezia. Clubs 442–459 have club records
  (`PLRESOURCESIM.PAC` entry 3) but no squads (`OTEAMMEMBER.TBB` covers
  3–441).
- **Past records stop at 48.** **Confirmed**:
  `pwkRec_GetCompePastRecord` (`0x253590`) refuses competitions from
  49 (`slti 0x31`); a record is 0x98 bytes at save block 5 `+0x260 +
  compe × 0x98` (team ids from `+0x8`, 32 of them). So competitions
  50–55 keep no record a `LAST_RANK` slot could read.
- **No room for more records.** **Confirmed**: the 49 past records end
  at block 5 `+0x1f78`, and the non-resident clubs' league records begin
  at `+0x203c` (`0x24d330`: up to 146 records of 0x1c8 bytes, found by
  `bsearch`), so 196 bytes lie between: not enough for six more records.
- **Clubs 442–459 can't join a league as they are.** **Confirmed**: a
  non-resident club (442 on) gets a temporary league record and its 25
  players from the database (`0x24d6b0`: ids `0x63f7` + 25 × (club −
  442), 25,591 onward); for such a club `pwkOteam_GetPointer`
  (`0x24b788`) returns club 3's record (`pwkOteam_Team2Otindex` maps
  only 3–441, and −1 becomes record 1), so code that updates a league
  club's block 2 record (main league, rank) would change club 3's. In
  the retail layout block 2 has no room for more records.
- **The plan: grow the save (the user's choice, 2026-10-26).** LMASTER
  full saves are separate already (`mod-saves`), so the third tier may
  break save compatibility. **Confirmed** for the approach: the blocks'
  sizes come from the table at `0x533ac8`, and `PlPworkTask`
  (`0x21d6f0`) allocates their sum from heap 6 in a shuffled order, so
  all code reaches a block through `get(i)`; block 2's serializers loop
  a fixed 440 records (`SAVEPRG.REL 0x29548`, `slti 0x1b8`), and
  `pwkOteam_Team2Otindex` (club − 3 < 439) can map clubs 442–459 to
  records 440–457 by its bound alone. The phases:
  1. The save: block 2 gains 18 records for clubs 442–459, and block 5
     seven past records for competitions 49–55 at its end, with
     `pwkRec_GetCompePastRecord` sending them there; the serializers
     read and write the new space (`save.py` follows, as it runs them).
     **Built** (as `save-expand`, now part of `--mod third-tier`), with an LMASTER code segment in
     the executable for the new code
     ([`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-bigger-save---mod-third-tier));
     tested in PCSX2: a converted career loads, saves and loads again
     (user report).
  2. Clubs 442–459 as full clubs: the game's limits 440 (`0x1b8`), 441
     (`0x1b9`) and 442 (`0x1ba`), each checked; their records and squads at
     the start. The club info screen and the world rankings should then
     list them. The 206 sites are sorted in
     [`CLUB_LIMITS.md`](CLUB_LIMITS.md), about 65 of them about clubs.
     The order (the user's choice to go on carefully,
     2026-10-26): (a) the resident checks and the club loops, with
     squads for 442–459 added to `OTEAMMEMBER.TBB`; (b) the buffers and
     arrays sized for 441 clubs (`ClubRank`, the club-rank list, the
     schedule's club lists, the transfer AI), each read and resized;
     each step a switch of its own, tested on a disc. Step (a) is
     **built** (as `tier-clubs`)
     ([`CLUB_LIMITS.md`](CLUB_LIMITS.md#--mod-third-tier-the-clubs-phase-2a)),
     tested in PCSX2 (a new career and the tutorial's playoff). Step
     (b) is **built** (as `tier-lists`)
     ([`CLUB_LIMITS.md`](CLUB_LIMITS.md#--mod-third-tier-the-lists-phase-2b)): the
     club-rank list, the transfer AI's lists, the offers' lists and the
     world ranking hold 459 clubs; tested in PCSX2 so far: the All
     Clubs Ranking lists every club (user report).
  3. The schedules: six hidden third-tier leagues every season (three
     real clubs, and in your nation the two sent down), the second
     divisions' last club down and the tier's winner up, two clubs sent
     down at the start in your nation,
     `REGULATION.TBB`'s down count 1, and the one-season game over. The user's
     choices (2026-10-27): the third tiers get **new UIDs**, 165–170
     and their own-nation versions 171–176 (UID 164 is the default
     rules, [`UID_LIMITS.md`](UID_LIMITS.md#164-is-no-competition)), so
     the tutorial's playoff (UIDs 142–147) and VS mode's leagues
     (148–163) stay as they are; every table and loop sized for 164
     schedules was found first, as in phase 2. The club
     that comes up is the **tier's winner** (`LAST_RANK` rank 1 of its
     competition), which changes each season as the games are simulated.
     **Built** (as `tier-uids`), (a) the leagues and (b) the
     movements ([`UID_LIMITS.md`](UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3));
     tested in PCSX2: a German career's season end moves the second
     division's last club down and the tier's winner up, in your nation
     and the others, after the fix that keeps the tiers' results
     ([`UID_LIMITS.md`](UID_LIMITS.md#--mod-third-tier-the-tiers-seasons-phase-3)). The rival goes down like any club (the user's
     choice, 2026-10-27). Step (b): the movements, and your nation's
     tier at 5 clubs (an own-nation version of each tier, as the second
     divisions have). Found for (b), **confirmed**:
     - `ScheCallback_ProcPromotion` (`0x1131c8`), once at a career's
       start, puts your club and the rival in the first two empty places
       of your second division's past record (the nations' second
       divisions in a 6-entry table at `0x51ad70`, nations 1–6 to
       competitions 1, 7, 12, 17, 23, 28); that is how they become ranks
       25 and 26 in England.
     - The past records are seeded for competitions 0–48 only
       (`0x253200`, `slti 0x31`); the seed table's rows 49–55 are empty.
     - `CScheEuro::calcCompetetionFinish` (`0x205fa8`, `slti 0x31`)
       writes no record from competition 49 on. Past it, the yearly
       honours (`pwkRec_GetCompeConventionRecord*`, `0x253af8`–`0x253c58`)
       exist for competitions 0–48 only and return null past them, so a
       third tier must write its table and skip the honours and the title
       effects.
     - Every own-nation version of a domestic UID (second division,
       cup qualifying, cup, league cup) differs from its other-nations
       version only by your club's and the rival's places, the cups
       chaining on through `NOW_RANK` of their own versions. With your
       second division at its real size, each becomes a copy of its
       other-nations version, its UID references moved to the own ones.

     The plan for (b): each season a second division takes its own
     ranks but the last plus its tier's rank 1, and a tier its own ranks
     from 2 plus the second division's last. Season 1 is seeded so that
     holds: a second division's seeded last place holds a tier club, and
     the tier's rank 1 that last club. In your nation,
     `ProcPromotion` instead places your club and the rival in the
     second division's ranks S − 2 and S − 1 and sends the two below
     them down to your nation's 5-club tier. A tier club in a seeded last
     place plays that nation's cups in season 1, as relegated clubs do in
     later seasons.
  4. Two seasons played in PCSX2: done for a German career (the
     tiers' winners up, the last clubs down).

  The five switches it was built as are **one switch now, `--mod
  third-tier`** (the user's rule: switches that need each other are one
  feature), in `--mod leagues` (LMASTER full and max); it turns on `mod-saves` itself and
  needs `--copies` and `--dat`. The machinery under it is no switch: the
  LMASTER code segment (`code_segment_words`) and the save-growing
  wrappers (`save_grow_words`) are there for any later feature, and the
  old names are taken as `third-tier`. A full LMASTER build was compared
  entry by entry with one without the third tier: only the third tier's
  own files and entries differ, `national-cups` and `league-balance`
  applied on top of its schedule packs, and the switches whose PRELOAD
  edits share its rebuilt packs (`drill-names`, `injury-lines`,
  `facility-tiers`) land as entry edits of the rebuilt packs.
- **Other Club Info** lists a nation's clubs from a loop that stopped at
  441; `third-tier` runs it to 459, so the tier's clubs are listed
  (tested in PCSX2, user report, 2026-10-27;
  [`CLUB_LIMITS.md`](CLUB_LIMITS.md#--mod-third-tier-the-lists-phase-2b)).
  What is left to trace is in [`UID_LIMITS.md`](UID_LIMITS.md#still-unknown).

## The text

`--mod third-tier` rewrites the messages that state the rules the tier
changes, in English, French, German, Italian and Spanish (the user's
choice, 2026-10-27, from a reviewed draft): 136 messages, 27 in each
language and one name. With the tier your second division has its real
size, two clubs fewer than retail's own version, its last club goes
down to the tier, and finishing last ends the game after one season
(retail: two seasons past a line).

| Messages (`MES.PAC` category:id) | What changes |
|---|---|
| 487:1100–1105, the advisor's intro to your division | the club count and matches (England 24 and 46, France 20 and 38, Germany 18 and 34, Italy and Spain 22 and 42, the Netherlands 20 and 38), and a last line: finishing bottom is game over |
| 487:1200–1205, Game Over conditions (help) | point 2: finishing last (24th, 20th, 18th, 22nd, 22nd, 20th) at the end of a season |
| 30003:1, the game over screen's conditions | point 2: finishing last in the division at the end of a season |
| 35680:0, the advisor's warning | finishing bottom this season, not twice |
| 487:902, the game over message | "we finished bottom of the league", not "nothing for the past two seasons" |
| 30001:101, 107, 112, 117, 123, 128, the second divisions' rules screens | a Relegation section: the club placed last goes down to the tier, by name |
| 832:433, 436, 442, 438, 440, 445, the second divisions' season-start news | a closing sentence: the bottom club goes down to the tier |

Which message belongs to which nation (**empirical**, from the data):
the intros hold the retail sizes in the order England, France, Germany,
Italy, Spain, Netherlands (26, 22, 20, 24, 24, 22); the Game Over texts
follow it, and their Italian versions name each nation, so 1204 is Spain
and 1205 the Netherlands, where the other languages repeat Italy (1204)
and Spain (1205). The rules screens go by their promotion rules, and the
news by the competition in each news record's date rule
([`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md)): competitions 1, 7, 12,
17, 23 and 28, the second divisions. The code that picks the intros and
Game Over texts isn't traced (no script or code site names their ids).

Retail slips in the same messages are fixed on the way: "216 equipos"
(26) in the Spanish text of England's intro, a stray "Vereine" in the
German text of Italy's, "41 partite" (42) in the Italian text of the
Netherlands', the Spanish name of the Dutch tier, "Cuarta Liga
Holandesa" (fourth, 11:1147), the Spanish game over screen's point 3,
cut off at "es menor" (less than 8), and the nations of 1204 and 1205.

`patch_disc.py` keeps the edits as short replacements and its own
sentences (`tier_text_edits`), applied to `MES.PAC` by a target hook
(`target_tier_text`): the disc's own file, or one a target writes (the
editor's Text tab), which keeps its own edits. Every grown file stays in
its slot, so no entry moves; `--copies` carries category 832 to its
copies in `PRELOAD/NEWS1`–`5.PAC` and 11_5 to `STATIONMES5.PAC`.
**Checked** on `LMAST-test-max-germany.iso` (2026-10-27): the 136
messages read back as built, every other message equals the build
without the text, and the five `NEWS` copies of 832 equal `MES.PAC`'s; a
`--mod lmaster-full` build with a `MES.PAC` target keeps the target's
edit and gets the text. Not seen in game yet.

The economy switches (tickets, adverts, fees, costs, reputation) need
no text: no message states their old limits.

## Retail text fixes

Messages the retail game itself gets wrong, fixed in LMASTER lite by
`--mod retail-text` (group `text-fixes`; built 2026-10-30, not yet
checked in the game). The third tier's text, which states its own
rules, is separate ([The text](#the-text)).

| Message | Retail | Fix |
|---|---|---|
| Game Over conditions, Spain (`MES.PAC` 487:1204), point 2 | English names "Italian League B" (and says "23th"), German "Italienische Liga B"; French, Italian and Spanish are right | Spain's second division, 23rd place, in English and German |
| Game Over conditions, the Netherlands (487:1205), point 2 | English "23th in Spanish League Division 2", French "division espagnole", German "23." and "Spanischen Liga 2", Spanish "2ª Liga Alemana"; only Italian is right | the Dutch second division, 21st place, in those four languages |
| Spanish intro to the division (487:1100) | "Hay 216 equipos" | 26 |
| Team 435's name (categories 3, 4 and 100003, ids 2435 and 3435) | "AL-Hyde" | "Al-Hyde" (user report), in all five languages |

The point-2 fixes follow the Italian texts, which name each nation's
own league and place. Category 487 has no `PRELOAD` copy, so its files
grow inside their slots in `MES.PAC`; the name keeps its size, so the
switch patches its copies in `PRELOAD/STATIONMES1`-`5.PAC` byte for
byte, and lite needs no `--copies`. A `MES.PAC` target gets the fixes in
its own bytes. With `third-tier`, the tier's text rewrites point 2 again
and finds the Spanish fix in place; with `real-names`, team 435 becomes
Al-Sadd. The Japanese release is left alone.

Other retail typos seen while making the name table, not fixed:
"Repulic of Ireland" (category 3) and "Motherwwell" (category 100003).

## Real names

`--mod real-names` (group `names`, in LMASTER full and max; built
2026-10-30, not yet checked in the game) gives every league,
competition, club and national team its real name of the game's era
where the retail game uses a made-up one: Highbury as Arsenal, City as
Manchester City, the European League as the Champions League (user
request, 2026-10-30). It also names each club's stadium as of 2005-06, the game's season,
without sponsors where the ground has another name (Westfalenstadion,
not Signal Iduna Park; user's choice, 2026-10-30). The club names match the ones LMAST Realism shows
on its logos and kits, so text and textures agree. The game lets the
player name their own club and themself with at most 18 characters
(user report), so the club names keep to 18 too.

**The switch.** `SRC/realnames.csv` holds only the real names (no game
text): 729 rows, keyed by category (3 teams, 10 stadiums, 9
competitions, 11 stages) and id, with the English, French, German,
Italian and Spanish names and a team's three-letter form.
`realnames.py` writes them into:

| Category | Ids | What |
|---|---|---|
| 3, 4, 100003 | 2000, 3000, 2000 + team | the team's name, in each language the row gives |
| 10 | 11000 + team | the club's stadium (clubs 3–459). The game's is "\<club\> \<word\>" ("Highbury Stadium", "Highbury Stade"); a row gives the ground's own name, the same in every language, and a club with a real name and no row gets "\<real name\> \<word\>" |
| 5 | 4000 + team | the three-letter form, in every language: the name's first three letters in capitals, as the game forms them, or an override where two clubs would share one (MCI, MUN, SHW, SHU) |
| 9 | 10000 + competition | the competition's name; in capitals where the game has it so (French, Italian and Spanish) |
| 100009 | the same | the English name in capitals, in every language, as the game has it |
| 11 | 1000 + stage | the stage or group's name |
| 100011 | the same | the same name where it repeats 11, or the English one where it holds English (in four languages run together, "European LeagueGroup A") |

**Stadiums (2026-10-30).** 382 of the 457 clubs have a stadium row,
the grounds they played at in 2005-06 (the user's choice, 2026-10-30,
after a first list of 2006-07): Highbury for Arsenal, not the Emirates
Stadium; the Stadio delle Alpi for Juventus and Torino, not the Stadio
Olimpico di Torino they moved to in 2006; the Alkmaarderhout for AZ, not
the DSB Stadion; La Condomina for Real Murcia, not the Nueva Condomina;
the Ciudad Deportiva for Real Madrid Castilla, not the Alfredo Di
Stéfano. Sponsor names give way to the
ground's own (Westfalenstadion, Arena AufSchalke, Volksparkstadion,
Son Moix, El Sadar, Stadion Letná); where a ground had no other name
(Reebok Stadium, JJB Stadium, Ricoh Arena, KC Stadium, Walkers Stadium,
Britannia Stadium, Arke Stadion, Polman Stadion, Rosada Stadion,
Mandemakers Stadion, Kras Stadion, Finnair Stadium, Home Depot Center,
Fukuda Denshi Arena) the row is left out. Names that belong to the club
or its owner rather than a sponsor stay (Madejski Stadium, BayArena,
Volkswagen Arena, Philips Stadion, MSV-Arena, Wacker-Arena). The other
75 clubs, mostly the small and far-away ones whose 2005-06 ground isn't
certain or needs letters cp850 lacks (Bežigrad, Andrův stadion), keep
"\<club\> Stadium". The game's names are at most 30 characters
("Athletic Club de Bilbao Stadio"), and so are the rows; `info` lists
any longer. The rows are suggestions for the user to check.

**`--mod own-stadium`** (group `names`): your club's stadium is named
after you, "\<your name\> Stadium", where the game used your city (user
request, 2026-10-30). **Confirmed:** `Msg::VarBuf_MakeMyStadium`
(`0x11eaf8`) builds the name into variable slot 9, which message 11001
of category 10 (team 1, "USE Stadium") shows, as `snprintf("%s %s")` of
slot 3 and the word "Stadium" (`GetString` type `0x28`, message `0x52`,
in each language: Stade, Stadion, Stadio, Estadio). Slot 3 holds the
city (user report: the stadium defaults to "\<City\> Stadium"); slot 0
holds the name typed at the start (`SetOwnerName_Keyboard`, the
`{var:1:7}` of the messages). The switch changes the slot,
`addiu $a0, $zero, 3` → `0` at `0x11eafc` (`24040003` → `24040000`).
The buffer is 33 bytes, so an 18-character name and " Estadio" fit.
The rival's stadium (`VarBuf_MakeRivalStadium`, slot 10) is built the
same way from the rival club's name and is left alone. Not yet tested
in the game.

Letters the European text's encoding (cp850) has no code for lose their
accent ("Zeljeznicar", "Besiktas"), as the game's own names do. A
competition's real name also replaces its game name in the English
messages that mention it (26: the tournament rules, the news, the
advisor's lines), matched in any case and outside `{tags}`; a qualifying
round's mention takes its competition's name ("we'll qualify for the
Champions League"). The other languages' 75 mentions are left for edits
by hand: their game names are often plain phrases ("monter en première
division"), and a proper name in their place needs its article and
gender changed ("nel campionato italiano B" → "nella Serie B"), which a
swap can't do. Club names in other messages are left too, since many
are city names.

Every file still fits its slot in `MES.PAC`, which keeps its size; the
name lists grow by about 550 bytes in each language, so their
`STATIONMES` copies grow. The switch brings `MES.PAC` as a whole file
and needs `--copies` (and `--dat`), like `third-tier`, whose text it
follows: the tier's added sentences name the tiers' leagues, which then
read "League One" and so on. PAL only.

**Checked on `LMAST-test-names.iso`** (LMASTER full with
`skip-tutorial`, built 2026-10-30), read back from the image: Arsenal,
Manchester City and MUN in `MES.PAC`, the Champions League in each
language, "Arsenal" and "Stella Rossa" in the English and Italian
`STATIONMES` copies the game loads, and "League One" in the third tier's
rules. **Tested in PCSX2** (user report, 2026-10-30): the names showed
as intended apart from two swapped pairs, since corrected (below).
The career started in England although the club was made in Germany,
because the disc was built without `--skip-nation germany`; that is
the test switch, not the names. On the rebuilt disc (with
`--skip-nation germany`) the names, the stadium names and the new grounds
work (user report, 2026-10-30).

```bash
python SRC/realnames.py info DAT/MESSAGE/MES.PAC       # the names against the disc
python SRC/realnames.py import names/realnames.csv     # from the filled name table
python SRC/realnames.py apply DAT/MESSAGE/MES.PAC out.PAC
```

How the names were chosen:

**The name table (groundwork, 2026-10-30).** `python SRC/mbb.py names
DAT/MESSAGE/MES.PAC names/realnames.csv` lists the 776 names to
consider: 457 clubs (teams 3–459), 83 national teams (460–542), 72
competitions (category 9) and 164 competition stages and groups
(category 11). Each row has the game's English name and length, an
empty column for the real name with a length formula, the French,
German, Italian and Spanish names, every copy (categories 4, 100003,
100009, 100011 and the short name in 5), the stadium named after a
club (category 10, "<name> Stadium") and the other messages that
mention it. `names/` is ignored, since the file holds the game's text,
and the command won't overwrite a table that exists. What it shows:

- Every game club name already fits 18 characters (the longest is
  18). 113 competition and stage names are longer, so the limit can
  only be a guide for those.
- 80 club names differ by language (French "Real Madrid Cast."),
  and most competition names are translated, so each language
  needs its own real name, not only the English one.
- Category 100003 differs from 3 in 7 names (spellings such as
  "Albinoleffe" and the typo "Motherwwell").
- 142 names appear in other messages too: "European League" in 15
  (the tournament rules among them), the nations in news and
  supporter lists. Those messages need the same rename.
- The `PRELOAD/STATIONMES<lang>.PAC` copies of categories 1 and 3–11
  have little room to grow: 1,840 free bytes for English, 644 for
  French, 1,072 for German, 232 for Italian and 1,008 for Spanish
  (`python SRC/preload.py info DAT`). Longer names past that need the
  pack rebuilt (`--copies` does it), which the Italian copy will.

LMAST Realism holds no text list of names: its logos are named by
texture hash, and its kit folders use the game's made-up names. Its
league folders (`ENG/Premier League` and so on) each hold that
league's or region's real clubs, so the table's last column, "LMAST
Realism logo shows", was read from the logos by sight (contact sheets
of each folder) and paired with the game's clubs of the same league
or region. Where a game name could fit two crests, the club's kit
colours decided (`uniform.py show`: Glasgow City wears green and
white, so it is Celtic). The English folders are the 2005/06 clubs;
the game's starting divisions are a season older (Crystal Palace,
Norwich and Southampton in the top flight), which doesn't change any
name.

**Style (the user's choice, 2026-10-30): short names, like the
licensed clubs of Italy, Spain and the Netherlands** ("Juventus",
"Atlético Madrid", "PSV Eindhoven"), never shortened past the name a
club is known by ("Real Madrid", not "R. Madrid"). The table's real
name column holds a suggestion only where the game's name isn't how
the club is known (Highbury → Arsenal, Gelsenkirchen → Schalke 04,
La Boca → Boca Juniors); an empty cell keeps the game's name, and the
licensed names stay. 340 suggestions and 220 logo readings are in;
the user then gave the names of ten clubs (Sheva → Beitar Jerusalem,
North Shore → Auckland City and others), and the three "Club Cups":
Coppa Italia Dilettanti, Copa Federación de España and KNVB Amateur
Cup, the amateur cups (the first two are 23 and 25 characters). The
user confirmed the pairings that were in doubt (Velika as Radnik V.
Gorica, Kutaisi as Torpedo Kutaisi, Kulubu as Bursaspor). Two pairs
first went the wrong way round and were swapped after the user saw
them in the game (2026-10-30): the game's Principat is FC Encamp, and
Diaconsa, whose Realism crest is FC Rangers' (1981), is FC Rangers;
Baki is Inter Baku and Baku is Qarabagh. The
World Club Championship is a made-up tournament and
keeps its name. AL-Hyde is Al-Sadd (Sadd Sports Club, user report):
"Al-Sadd" in full and max, while lite only fixes its casing to
"Al-Hyde" ([Retail text fixes](#retail-text-fixes)). That leaves Doha, which had the Sadd crest: the
only Qatari crest left in Realism's Middle East folder is Al-Gharafa's,
which the user confirmed. No cell is left in doubt. Four game names end in a stray space ("Baku ",
"Moskva ", "Újpesti ", "Ararat "), which their real names drop. 27
suggestions, all competition or stage names, are over 18 characters,
as many of the game's own are.

**The other languages.** The table ends with "real fr", "real de",
"real it" and "real es" columns (`mbb.py names` adds them), filled
from the English suggestions: 1,350 cells. The game's own non-English
names are descriptive translations ("Coupe d'Angleterre",
"Englischer Pokal"), so the real names are mostly the same proper
names in every language: the national leagues and cups (FA Cup,
Bundesliga, Copa del Rey) stay untranslated. The UEFA and FIFA
competitions take each language's usual name ("Ligue des champions",
"UEFA-Pokal", "Coppa UEFA", "Copa de la UEFA"; the German
"Weltmeisterschaft" and "Europameisterschaft" are kept). Stage names
follow the game's own wording and order in each language ("Tour de
…", "Gruppe A", "Gruppo A …", "Final …"), and category 9 stays in
capitals in French, Italian and Spanish as the game has it. Clubs copy
the English suggestion, except where a language has its own common
form ("Étoile Rouge", "Roter Stern", "Sparta Prag", "CSKA Moscou",
"1860 München"); every club suggestion fits 18 characters in every
language.

## Stadiums

Group `stadiums` (LMASTER full and max, the user's request,
2026-10-30). Its switches change how big grounds are; the names of the
grounds are in [Real names](#real-names).

**How a ground's size works (confirmed).** Two tables hold capacities:

| Table | Whose | What |
|---|---|---|
| `PLRESOURCECOMMON.PAC` table 0.7 ([`PLRESOURCECOMMON_FORMAT.md`](PLRESOURCECOMMON_FORMAT.md)) | your club's | 9 stadium types with up to three stand levels each: types 0–1 8,000 (the start), 2–5 15,000/20,000/25,000, 6 30,000/35,000/40,000, 7 50,000/55,000/60,000, 8 (the Special stadium) 110,000 at every level. Gate money and the crowd use these |
| `STADIUM_DATA.TBB` ([`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md#stadium_datatbb-stadiums)) | the 119 match stadiums | roof, level and capacity in thousands for each stadium id; a computer club's record names one id |

In a match at your ground, `PlGiTask::InitStadium` (`0x2131c0`) turns
your stadium type, league and the stand, roof and lights you have built
into a stadium id through `CONV_INFO_BUILD` (`plTeam_GetStadiumDataIndex`,
[`STADIUM_DIR.md`](STADIUM_DIR.md#conv_info_buildtbb)), and `SetMyAudience`
(`0x212d9c`) divides your crowd by that id's `STADIUM_DATA` capacity to
fill the stands. The ids your builds reach are 0–101 (each level's ids
hold that level's capacities: 0–5 8,000; 6–35 15,000–25,000; 36–65
30,000–40,000; 66–95 50,000–60,000; 96–101 110,000), so their capacities
must follow your ladder. Ids 102–118 are only used by computer clubs.
Computer clubs use 89 ids, 219 clubs on ids your builds share and 238 on
the other 17, with 14 different capacities.

**`--mod special-stadium`.** The Special stadium (type 8) holds 100,000
at each level, not 110,000 (user's choice of 90,000 or 100,000).
`plrcommon.special_stadium` writes the three capacity words of record 8
(`+0x38`, `+0x48`, `+0x58`), and ids 96–101, the match stadiums of a
level-4 ground, go from 110 to 100 thousand so a full house still fills
the stands. Computer clubs on ids 96–100 (Chelsea, Arsenal, Monaco,
Bayern, Dortmund, Leverkusen, AC Milan, Inter, Barcelona, Boca Juniors)
hold 100,000 too. The switch writes only the changed bytes, like
`facility-tiers`, which writes the same records' costs (it now does the
same): on a scratch disc with both, record 8 cost £350M and held 100,000,
and the `STATIONFILE` copy and the seven `SIMFILE` copies of
`STADIUM_DATA` matched. An editor target (Facilities, Nations &
stadiums) takes the change in its own bytes. Not yet tested in the game.

**`--mod real-grounds`.** Each computer club plays at a ground of its
real 2005-06 capacity (the game's season; the user's choice, after a
first build with 2006-07 figures), rounded to 5,000 (the user's choice,
closer to the retail game's few sizes than a figure to the thousand),
and clubs of one size are spread over the stadium ids of that size, so
grounds of the same size look different (user request, 2026-10-30).
`SRC/grounds.csv` holds each club's ground and real capacity in
thousands (suggestions, from memory: lower-division and far-away
figures are approximate, which the rounding mostly absorbs; Old Trafford
68,200, the Allianz Arena 66,000 and the Olimpico 82,300 are their
2005-06 sizes). `initteam.py` does the rest:

- **Looks.** Ids 0–101 keep your ladder's capacities, and their models
  follow those sizes. The ladder's models look small for their numbers
  at the top (user report on the first build: Chelsea, Manchester United
  and Bayern), but only the biggest grounds should get the 110,000 bowl
  (user's choice), so a ground's look follows its size:

| Band | Look | Ids |
|---|---|---|
| 8,000–35,000 | the ladder's models (`ho00`–`ho02a`) | the ladder's, 6–18 a band |
| 40,000, under 40,000 real | the ladder's `ho02a` | the ladder's 40,000 ids |
| 40,000, 45,000 | `ho03a` with roof (and lights at 45,000) | 102–104, 105–107 |
| 50,000–60,000 | `ho03a` | the ladder's 66–95 |
| 65,000, 70,000, 75,000 | the `aw04b` bowl | 108–109, 110–111, 116 and 118 |
| 80,000, 85,000 | the `ho04a` bowl | 112–113, 115 and 117 |
| 100,000 | the `ho04a` bowl | the Special stadium's 96–101 |

  The club-only ids 102–118 take the look of a ground (its
  `BUILD_STADIUM` row: model, parts, crowd set, but not its advert
  boards, which stay the id's own; `stadium.copy_rows`), its roof and the level of its model: 102–104
  rows 69, 79, 89 (`ho03a`, roof), 105–107 rows 75, 85, 95 (roof and
  lights), 108, 110 row 116 and 109, 111 row 118 (`aw04b`), 112 row 97,
  113 and 117 row 117, 115 row 99 (`ho04a`). A look is copied only from
  a row the switch leaves alone (116–118 keep their own), so applying it
  twice changes nothing. `GetCapacityFromID` adds 500 seats to 103, 105
  and 107. Stadium 114 is the rival's ground in every league
  (`TEAM_INIT_DATA` table 7, [`TEAMINIT_FORMAT.md`](TEAMINIT_FORMAT.md#the-rival-club-tables-6-7-and-8)):
  it keeps its look, boards and 42,000, and no other club is put on it,
  so the rival's ground stays its own (the user's request).
- **Clubs.** As many grounds as possible, each close to its real size
  (the user's request): a ground may take any band within 3,000 of its
  real capacity, or its nearest band (the bigger on a tie) if none is;
  under 12,500 the 8,000 grounds. The ladder's own 40,000 grounds, with
  the smaller `ho02a` look, only go to grounds really under 40,000
  (Highbury, 38,400). Each ground takes the least-used of its choices,
  nearer bands first on a tie, the grounds with the fewest choices first;
  clubs naming the same ground (AC Milan and Inter, Lazio and Roma,
  Juventus and Torino, Bayern and 1860) share one. 90,000 (Azadi;
  Maracanã's 88,000) goes to 85,000, since no id is left for
  90,000–95,000. Camp Nou alone is at 100,000, which is why the switch
  turns on `special-stadium`. The 12 on the `ho04a` bowl: Camp Nou, San
  Siro (twice), the Bernabéu, the Westfalenstadion, the Olimpico
  (twice), Luzhniki, Maracanã, Morumbi, the Monumental in Lima and
  Azadi.
- **Result.** 453 bytes of the club records change; the clubs use 96
  of the 118 ids (89 in retail; the rival's 114 apart) and 17 sizes (14).
  The ids left are the ladder's 40,000 and 60,000 ones and the Special's,
  with no ground within 3,000 of them. The mean distance from the real
  capacity, over the clubs above 12,500, is 1,200 seats, the largest
  5,000 (Azadi).

The club records (`PLRESOURCESIM.PAC` entry 3, `+0x06`) and `STADIUM_DATA`
go in with their PRELOAD copies, and `BUILD_STADIUM.TBB` (no copies), only
the changed bytes, next to `overseas-bases` and `special-stadium`, which
write the same files. A
`PLRESOURCESIM.PAC` or `STADIUM_DATA.TBB` from the editor takes the change
in its own bytes (target hooks, as for `special-stadium`); where its own
edit replaced what the switch expects, the editor's value stays. A
`BUILD_STADIUM.TBB` from the editor's Stadiums tab takes the looks row by
row: rows whose look the editor changed keep it
([`STADIUM_DIR.md`](STADIUM_DIR.md#editing)).
**Tested in PCSX2** (user report, 2026-10-30, the first build): the new
grounds work; the biggest looked too small. With the looks by size above,
on `LMAST-test-stadiums.iso` (2026-10-30): "Stadiums are good" (user
report).

**`--mod sponsor-boards`.** Every stadium's 12 advert boards are drawn
afresh from all 205 sponsor logos (user request, 2026-10-30: more
variety of sponsors at the grounds). A computer club's ground shows the
boards of its `BUILD_STADIUM` row, bytes 116–127 (`InitStadium` clears
the match's own 12 at `0x2136a8`); value *v* is logo *v* − 1 of
`SPONSOR_TEXTURE_M`, 1–205 ([Adverts](STADIUM_DIR.md#adverts)). The
retail rows use 119 of them, 12 different ones a row. The switch draws 12
different logos for each of the 119 rows, a fixed shuffle per stadium
(`stadium.sponsor_boards`), so every build is the same: 204 of the 205
logos appear. The rival's ground (114) keeps its own boards. The adidas board every ground shows (the user's LMAST
Realism makes it Nexxus Drako Multimedia) isn't one of the 12: it is
`ADT_TEXCMN` entry 212, which no row names (they use 1–200); the match
request's `+0x10` moves a row's boards up one and puts it first
(`0x1cd618`), so it stays on every ground (the user's request), and the
switch's draws never pick it (value 206; *v* − 1 is clamped to 205, so
any value from 206 on would be adidas too). It writes only those bytes,
so it sits beside `real-grounds`. An edited `BUILD_STADIUM.TBB` keeps
the boards of the rows the editor changed and takes the draws in the
rest ([`STADIUM_DIR.md`](STADIUM_DIR.md#editing)). Clubs that share a stadium id still share its boards;
boards of each club's own would need code in the match set-up.
**Tested in PCSX2** with the grounds (user report, 2026-10-30).

```bash
python SRC/plrcommon.py show DAT/PARAM 0.7          # your stadium types
python SRC/initteam.py stadiums DAT/PARAM           # the 119 match stadiums
python SRC/stadium.py info DAT/STADIUM DAT/PARAM    # CONV_INFO_BUILD's ids by level
```

## Planned

Ideas the user has agreed on (2026-10-27), not started:

- **LMAST Realism on the disc.** Bring the logos, kits, texture fixes
  and real competition names of
  [LMAST Realism](https://github.com/NexxusDrakoMultimedia/LMAST-Realism),
  the user's own PCSX2 texture pack, onto the disc, so it works without
  PCSX2's texture replacement. It needs: (1) which disc texture each of
  its PNGs replaces, from the hash PCSX2 names it by (computed the same
  way from each texture `svr.py` decodes, or matched against a dump of
  the originals); (2) a texture writer, since `svr.py` only reads
  ([`SVR_FORMAT.md`](SVR_FORMAT.md)): palette, swizzle and the containers
  the textures sit in; (3) a palette for each: Realism keeps the native
  sizes for the most part (user report), so most replacements fit their
  texture once requantised to its palette, and the few larger ones need
  a choice (scaled down, or left to the pack). The pack's files stay out
  of the repo.

## Not candidates

- `EVENT/EVENTDATA_TURN.TBB`, `0SYSTEM/SCHEDULE.TBB` and the `CVS/`
  files are development leftovers. The game has no code that reads them.
- Language slot 6 of `MES.PAC` is an unused near-copy of English.
- `CSE/GP_PRACTICEICON.CSP` is empty in PAL but not in the Japanese
  release. PAL loads the per-language `GP_PRACTICEICON0`–`6.CSP`, which
  hold the same icons.
- The Japanese `PLRESOURCESIM.PAC` has no free-agent list: PAL added it.
