# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Nexxus Drako Multimedia
"""Patch edited game files into the disc image, DATA.CVM or DATA.ISO, for
Let's Make a Soccer Team! (PS2). A file keeps its sectors if it fits in
them; one that needs more is moved to the end of DATA.ISO.

DATA.CVM is a ROFSBLD container: a CVMH/ZONE header, then an ISO9660 image
whose table of contents (the volume descriptor and directory sectors) is
encrypted. File contents are stored as plain bytes (see
DOC/DATA_CVM_EXTRACTION.md and DOC/REBUILD.md). A replacement file of
exactly the same size can therefore be written over the original's bytes
without touching the table of contents: the directory record still gives
the same first sector and size, so nothing needs to be re-encrypted. The
disc image holds DATA.CVM as an ordinary file, so the same holds one level
up.

<image> may be:
  - the whole disc image (plain ISO9660 with DATA.CVM in its root),
  - DATA.CVM itself (starts with 'CVMH'), or
  - a decrypted DATA.ISO (plain ISO9660, as made by rofs_decrypt.py).

<path> is a file's path inside DATA.CVM as it appears under DAT/, e.g.
PARAM/PBDATA_EU.PAC (either slash, any case). Files on the disc outside
DATA.CVM take a disc: prefix, e.g. disc:SLES_541.51 or disc:DLL/SAVEPRG.REL
(whole disc images only).

--rename disc:<path>=<NEWNAME> (repeatable) renames a file on the outer
disc, keeping the name's length: it rewrites the ISO9660 directory record
and, since the disc is a UDF bridge, the UDF File Identifier Descriptor
(recomputing its tag CRC and checksum). Neither is encrypted. Other
targets in the same run still use the old name.

<target> is <path>, or <path>#<entry> for one archive entry (its index,
its name, or "header"), e.g. MESSAGE/MES.PAC#7 or PRELOAD/SIMFILE0.PAC#Regulation.tbb.

Usage:
    python patch_disc.py locate <image> <path> ...                        # where each file's bytes are
    python patch_disc.py copies <DAT> <target> ...                        # other places holding the same bytes
    python patch_disc.py patch  <image> <out_image> <target>=<file> ... [--copies] [--dat DAT] [--rename disc:<path>=<NAME>] [--mod <switch>,...] [--skip-nation <nation>]
    python patch_disc.py patch  <image> --in-place <target>=<file> ... [--copies] [--dat DAT] [--mod <switch>,...]
    python patch_disc.py verify <image> <path>=<file> ...                 # does the image hold these bytes?

`patch` re-reads every patched range afterwards. Keep an unmodified copy
of the disc: --in-place cannot be undone except by patching the original
files back. A CSO, ZSO or CHD <image> (cso.py, chd.py) is decompressed
into <out_image>, which is then patched; it can't be patched --in-place.

Size changes: the game reads a whole file as (size + 0x7ff) >> 11 sectors
(ADXF_GetFsizeSct, used at 0x307f24), so a file may grow or shrink inside
its last sector. `patch` then also rewrites the size in the file's
directory record, decrypting and re-encrypting that one sector.

Moving files: a file (or rebuilt PRELOAD pack) that needs more sectors is
written after DATA.ISO's last sector and its directory record pointed
there; its old sectors are left as they are. DATA.ISO has no free sectors
between files, and DATA.CVM is the disc's last file, followed by 10,247
zero sectors before the UDF anchor in the last sector, so DATA.CVM grows
into those (about 20 MB). That changes the ISO's volume size (PVD), the
CVMH/ZONE lengths, DATA.CVM's ISO9660 record and UDF File Entry, and the
ROFS key: the game derives it from the CVMH header, whose +0x20..+0x23
are the low bytes of the CVM's size (rofs_decrypt.header_key, from
RSU_GenerateFixedKey 0x1e7550), so the whole table of contents is
encrypted again with the new key. A file already moved to the end grows
in place on a later run. Past the free sectors the disc image grows (whole
16-sector blocks, up to a single-layer DVD's 2,295,104 sectors): its PVD
volume size, the UDF partition length in both partition descriptors and
the integrity descriptor's size table change, and the UDF end anchor moves
to the new last sector. Files outside DATA.CVM keep their size.

The Japanese release (SLPM_663.16) takes the same switches but
third-tier, which is made for the PAL executable only (so not
lmaster-full or lmaster-max). Each gives its bytes as PAL offsets; on a Japanese disc
they are found in its executable and overlays with gamever.py (so the
PAL files in ISO/ must be there), and checked as on PAL. sponsor-negotiation does nothing there
(the release negotiates already), drill-names finds the names already in
place, mod-saves renames BISLPM-66316-G/C, and fanbase scales the
Japanese merchandise table, which holds half the PAL bases. See
DOC/JAPANESE_RELEASE.md#patching-a-japanese-disc.

Switches come in three levels (DOC/LMASTER_MOD.md#the-switch-levels),
and --mod takes names of any level, comma-separated (or repeated):
    python patch_disc.py switches       # print the editions, groups and switches
Editions: --mod lmaster-lite (or lmaster) is the LMASTER Mod's fixes,
the groups training-fixes, injury-fixes, club-fixes, match-fixes and
text-fixes; --mod lmaster-full adds leagues, restorations, names and
saves, and --mod
lmaster-max adds the difficulty groups harder-economy and balance to
full. Both always save to their own folders: full's careers in -F, max's
in -M (mod-saves picks M when any difficulty switch is on), and the VS
data of both in -V.
Groups: training-fixes (camp-types, camp-cities, camp-santiago,
camp-clubs, drill-names), injury-fixes (injury-value, injury-row),
club-fixes (sponsor-negotiation, season-status, pr-cycle, mobile-site,
overseas-pop, cup-last16), match-fixes (rival-manager, press-tendency,
national-cups, vpf-styles), text-fixes (retail-text), harder-economy (facility-tiers,
wider-tickets, dearer-ads,
sponsor-fees, tv-fees, season-demand), balance (injury-odds,
overseas-bases, transfer-fees, fee-tiers, slow-reputation, fanbase,
merch-costs, pr-costs, camp-costs, tour-costs), leagues
(league-balance, third-tier), restorations (injury-lines), names
(real-names, own-stadium), stadiums (special-stadium, real-grounds, sponsor-boards), saves (mod-saves),
and test-tools (skip-tutorial, launcher), which is in no edition.
third-tier turns on mod-saves and needs --copies and --dat; real-names
needs them too. Each switch
also works as a flag of its own (--skip-tutorial, ...). With switches
and no targets, `patch <image> <out_image>` is enough.

--skip-tutorial (test discs; whole disc image only) skips the opening
playoffs of a new career, the tutorial, but runs their schedule steps: it
sets the flag word at SLES 0x34d434 (Dummy.CheckClubEditSkip, the
developers' switch, which promotes the club) and turns RootClubEditSeq.sqb's
playoff section into InitializeFirstCheck, YearStart, MonthStart,
CheckClubEditSkip and a Call to the won route's MonthEnd, YearEnd and
Finalize, so the real year end runs (club rankings, the club's status);
RootMainSeq.sqb and RootYearStartSeq.sqb keep club creation and year
starts. On an image patched by the earlier skip it also undoes that
skip's sponsor and pwkTeam_YearEndCheck workarounds. The club must be in
England (the switch calls pwkLg_Init(0)), or in the nation --skip-nation
names (England, France, Germany, Italy, Spain or Netherlands; the
argument at SLES 0x108dc4): create the club in a city there. A smaller
league makes a quicker season test (Germany: 34 second-division games
to England's 46). See DOC/SQB_FORMAT.md.

--sponsor-negotiation (whole disc image only) turns the Sponsor screen's
main sponsor negotiation back on, as in the Japanese release. The screen's
check (DLL/SIMPRG.REL 0xc5ca0) is a stub returning 0 in PAL; the patch
makes it return 1 for a sponsor not yet negotiated with on this screen, 12
words in all (0xc5ca0 and the unused method at 0xd3748). See
DOC/SPONSOR_NEGOTIATION.md.

rival-manager (whole disc image only) gives the rival club the manager of
its own style. pwkTeam_Init2 finds TEAM_INIT_DATA table 6's record for the
rival's style, but its load reads record 0, so every rival had H.Raphanel;
one instruction of SLES_541.51 (0x25e6d8). See DOC/TEAMINIT_FORMAT.md.

press-tendency (whole disc image only) lets every level of a player's
press tendency count. The press readers cap it by a per-side value that
a career match leaves at 2 (cap at level 1), so levels 2-4 acted as 1;
in each of the two readers of DLL/GAMEPRG.REL the instruction that
turns a 2 into the cap 1 becomes a nop (0x9a474, 0x9a52c). See
DOC/PBDATA_FORMAT.md#the-tendencies.

national-cups moves the World National Cup (UIDs 114-122) and the Euro
National Cup (98-102) one turn earlier (schedule.shift_pack), so the World
Cup final is no longer on the year's last turn, where the season ended
before its results could be viewed. It writes PARAM/SCHEDULE_SYSTEM.PAC and its copy in
PRELOAD/STATIONFILE.PAC. The national-team calendar moves with them
(PARAM/SCHEDULE_LIST.TBB and its copies in PRELOAD/SIMLOCALMEM0-6.PAC): in
the tournament years the matches and the release are a turn earlier, and
the call-up stays on turn 88 with the first group game. With a
SCHEDULE_SYSTEM.PAC target (leaguesize.py build, a league of another size)
the cups are moved in the target's bytes, and --copies carries them to
STATIONFILE.PAC; so is a SCHEDULE_LIST.TBB target (a calendar edited with
natcal.py), whose --copies go to the SIMLOCALMEM packs. See
DOC/LMASTER_MOD.md.

league-balance rebuilds the league schedules that send a club to one
venue up to 9 times running: the 22-club leagues (UIDs 11, 30, 40, 48),
the 26-club English second division (1) and the 8-club VS leagues
(154-155), with schedule.balance_pack at their own size, so no club plays
more than two games running at home or away. Same clubs, game days and
turns; only PARAM/SCHEDULE_COMPETITION.PAC changes, and its .HED doesn't.
A SCHEDULE_COMPETITION.PAC target (leaguesize.py build) is balanced in
its own bytes. See DOC/SCHEDULE_FORMAT.md#writing.

camp-types lowers every camp type in PARAM/CAMP_LIST.TBB by one. The
camp booking stores the record's type (1-87), but the training table
(TRAINING_LIST table 10) and the theme table at SLES 0x552cd0 are read
with it as 0-86, so every camp trained and judged its themes as the next
type (Parma, a goalkeeper camp, trained no keeping). camp-cities moves the
seven English camps that PAL left on the Japanese city ids (Liverpool's
camp was in Scunthorpe) to their PAL towns, in CAMP_LIST.TBB and
CAMP_EXPLANE.TBB. camp-santiago keys Santiago's description in
CAMP_EXPLANE.TBB to its camp's city (774, not 764), and camp-clubs (whole
disc image only) makes the camp's clubs list (SIMPRG.REL 0x4c8f8) read all
737 pairs of CAMP_LIST table 1, one instruction. See DOC/CAMP_FORMAT.md.

drill-names gives drills 75-86 their own names in the European languages.
PAL's names (MES.PAC category 801, message 971 + practice) are one
message early and end with an added "Jackknife", so the drill named Pass
training trained shooting. The names move one message later in
801_1-6.mbb and their copies (entry 28 of PRELOAD/SIMFILE1-6.PAC); the
jackknife name goes to 1045, the dummy drill 74 no coach teaches. A
MES.PAC target gets the fix in its own bytes. The Japanese release has
the right numbering and is left alone. See DOC/TRAINING_FORMAT.md.

retail-text fixes messages the retail game gets wrong: point 2 of the
Game Over conditions for Spain and the Netherlands (MES.PAC 487:1204 and
1205) names their own league and place where some languages name
Italy's, Spain's or Germany's, the Spanish intro (487:1100) says 26 clubs
for 216, and team 435's name is Al-Hyde, not AL-Hyde (categories 3, 4
and 100003, and the STATIONMES copies of 3 and 4). A MES.PAC target gets
the fixes in its own bytes; the Japanese release is left alone. See
DOC/LMASTER_MOD.md#retail-text-fixes.

real-names (LMASTER full and max) gives every league, competition, club
and national team its real name of the era, in the five European
languages: realnames.py writes SRC/realnames.csv's names into MES.PAC's
name lists and the English messages that mention a competition. The
lists grow, so it brings MES.PAC whole and needs --copies (and --dat) for
the STATIONMES copies; it runs after the third tier's text. PAL only.
The names include each club's stadium (category 10). See
DOC/LMASTER_MOD.md#real-names.

special-stadium (LMASTER full and max) makes the Special stadium, the
biggest a club can build, hold 100,000 at each level instead of 110,000,
and the match stadiums of such a ground (STADIUM_DATA 96-101) with it.
See DOC/LMASTER_MOD.md#stadiums.

real-grounds (LMASTER full and max) puts each club at a ground of its
real 2005-06 capacity, rounded to 5,000 (SRC/grounds.csv), with a look to
fit: your own ground's ladder up to 35,000 and at 50,000-60,000,
STADIUM_DATA ids 102-118 for 40,000-45,000 (the ho03a model), 65,000-75,000
(the aw04b bowl) and 80,000-85,000 (the ho04a bowl, only for the biggest),
built like those grounds (BUILD_STADIUM rows copied). The clubs of one size
are spread over as many ids as possible, each within 3,000 of its real
size. The rival's ground (114) stays its
own. It turns on special-stadium (the
100,000 ids). A target PLRESOURCESIM.PAC or STADIUM_DATA.TBB takes the
change in its own bytes, unless its own edit is in the way.

sponsor-boards (LMASTER full and max) draws every stadium's 12 advert
boards afresh from all 205 sponsor logos (BUILD_STADIUM.TBB), a fixed
shuffle per stadium (the rival's ground keeps its own); the retail grounds
use 119 of them. The adidas board the match adds stays.

own-stadium (LMASTER full and max; whole disc image only) names your
club's stadium after you, "<your name> Stadium", where the game used your
city: VarBuf_MakeMyStadium reads variable slot 0, not 3 (SLES 0x11eafc).

injury-value (whole disc image only) sets the first minimum of kind-6
injuries in the value table (SLES 0x532d70) from 1600 to 16001, where the
kinds before it end. injury-row (whole disc image only) clamps
judgeKegaKind's table row to 10 (SLES 0x21a08c, 6 words), so a player of
35 or more at full fatigue no longer reads past the injury tables; see
DOC/INJURIES.md. vpf-styles (whole disc image
only) fixes the Virtua Pro Football import's play-style sort: its compare
(DLL/SAVEPRG.REL 0x3df00) subtracted pointers, so only styles 1-4 could
come in; 4 words make it compare the ratings, best first (through the
tail of the executable's strcmp, 0x31a5b4), and one more (0x3dfe0) rates
style 0, "none", at 0 in the sorted copy, so it never takes a slot. See
DOC/PMPLAYER_FORMAT.md.

season-status (whole disc image only) restores the season-ticket status
factor: pwkUnkei_GetExpectSeat scales demand by club status in bands of
10,000 (0.5 up to 1.0 above 50,000), but its tests gave every status over
10,000 the 0.6 band. 31 words of SLES_541.51 from 0x272840 rewrite the
ladder. See DOC/ECONOMY.md#season-tickets.

facility-tiers (plrcommon.facility_tiers) doubles every facility's build
costs and upkeep, and more for the bigger levels: grounds x2 and x4,
club houses x2 and x4 (the starting one's upkeep x2), stadiums x2 for
15,000-25,000, x3 for 30,000-40,000, x5 (upkeep x4) for 50,000-60,000 and
x3.5 (upkeep x6) for 110,000. It writes PARAM/PLRESOURCECOMMON.PAC and its
copy in PRELOAD/STATIONFILE.PAC. wider-tickets (whole disc image only)
lets both ticket screens go up to 480 (£80; SIMPRG.REL 0x3ef98, 0x3d1e4)
and respaces the ticket demand table (SLES 0x556120, 0x556250) over
60-480, with crowds above 300 falling so 480 draws half of 300's.
dearer-ads (whole disc image only) halves what the ad budget buys and
doubles its maximum to 60,000,000 (£10M): the plan screen's limit and
the popularity and ticket demand steps (SLES 0x268ce0, 0x2719e0,
0x271a88, 0x271aa0). sponsor-fees and tv-fees (whole disc image only)
keep sponsor fees and TV offers up to £2M and halve the part above
(SIMPRG.REL 0x23d978, 212 sponsors; 0x241780, 19 TV offers).
season-demand (whole disc image only) halves season-ticket demand
(pwkUnkei_GetExpectSeat's divisor, SLES 0x272a10). See DOC/ECONOMY.md.

injury-odds (whole disc image only) doubles the chance of an injury of six
months or more in every row of the practice and match kind tables (SLES
0x532c28, 0x532c90), to at least 2% and 5% of a row, taking it from kind
3 and then kind 0, which leaves light match injuries as they were.
injury-lines (whole disc image only) brings back the "two months" and
"nine months" condition lines: plPinfo_KegaRecoverDaysChno's heavy ladder
(SLES 0x216e14, 15 words) gets thresholds 4,000 and 12,500 too, and
category 200's messages 4 and 7 get French, German, Italian and Spanish
text in MES.PAC and its PRELOAD copies (SIMFILE, TACTICSLARGE and
TACTICSMATCHLARGE 2-5), the same size as the placeholders they replace.
See DOC/INJURIES.md.

overseas-bases (whole disc image only) doubles the 13 overseas bases'
costs in PLRESOURCESIM.PAC entry 1 (and its PRELOAD/SIMLOCALMEM0-6.PAC
copies), which doubles their investment and upkeep too; what a level
does is unchanged, so every pound buys half as much, as with dearer-ads.
See DOC/PLRESOURCESIM_FORMAT.md#entry-1-overseas-branches.
transfer-fees (whole disc image only) doubles the base of every transfer
fee (SLES 0x247288, 1,350,000.0 -> 2,700,000.0) and raises price kind 1's
cap from 7,200,000 to 15,000,000 (£120M -> £250M) in all four
currencies (the initializer at 0x24a140). fee-tiers (whole disc image
only) multiplies the transfer fee's factor by player rank (SLES 0x398478,
16 ranks x 6 club-rank bands) by tier: ranks 0-5 x2, 6-11 x1.5, 12-14
x2, 15 x3, so lesser players cost about four times the retail fee with
transfer-fees and the best reach about £246M. slow-reputation (whole disc
image only) halves what raises club status: a match's win and draw
factors (SLES 0x399668), the points for final places (0x555188,
0x555260, 0x555288) and the yearly 500 (0x26e2c4); losses stay.
third-tier (whole disc image only, with --copies and --dat; in
lmaster-full and lmaster-max; turns on mod-saves) adds the LMASTER third tier: a hidden
league under each second division, competitions 50-55, as schedule UIDs
165-170 (3 clubs) and, for your nation, 171-176 (5 clubs). Each season
the second division's last club goes down and the tier's winner comes
up; your second division has its real size, two of its clubs starting
in the tier; finishing last in it ends the game after one season. Each
nation's lower cup (the English League Cup, the Club Cups) takes all of
its tier's clubs too, its qualifying round as it was, and starts on Dec
w1 midweek (turn 40). Clubs
442-459 become full clubs (block 2 records, squads added to
OTEAMMEMBER.TBB, the club checks, loops and lists that stopped at 441),
the save grows (block 2 by their 18 records, block 5 by the past records
of competitions 49-55), and the schedule files grow (SCHEDULE_SYSTEM,
SCHEDULE_COMPETITION, SCHEDULE_TEAM_ENTRY, REGULATION, CLUBRESULT and
PLRRSRC_INITTEAMDATA, with their PRELOAD copies). The messages that state
these rules (the advisor's intro and warning, Game Over conditions, the
second divisions' rules screens and season-start news) are rewritten in
the five European languages, in MES.PAC or a MES.PAC target, with the
NEWS packs' copies (DOC/LMASTER_MOD.md#the-text). Its saves don't load
in the retail game, nor the other way round; `save.py convert` carries a
career over. See DOC/UID_LIMITS.md, DOC/CLUB_LIMITS.md,
DOC/SAVE_FORMAT.md and DOC/LMASTER_MOD.md. The names it was built as,
save-expand, tier-clubs, tier-lists, tier-uids and one-season-end, are
taken as third-tier.
fanbase (whole disc image only)
scales the merchandise base by supporters (SIMPRG.REL 0x1d9ec8, 17 rows)
from x0.5 at the bottom to x3 at the top, makes walk-up crowds and
season-ticket demand count home popularity at 195 in place of 130 with
the fixed part 1,500 in place of 3,000 a step (SLES 0x2722d8, 0x2722f0,
0x2728ec, 0x2728f0), and widens the TV offers' popularity factor from
0.9-1.15 to 0.75-1.25 (SIMPRG.REL 0x163a60-0x163b2c). merch-costs (whole
disc image only) makes a unit of merchandise stock cost 50% of its shop
price instead of 30% (SIMPRG.REL 0xbcce4) and halves the bulk discounts
(0x1d10d8: 100, 95, ... 60 -> 100, 97, 95, 92, 90, 87, 85, 80). See
DOC/ECONOMY.md.

pr-cycle (whole disc image only) fixes the business cycle's effect on a
PR event's chance: plClubEvent_Execute's ladder (SLES 0x20dfb0, 11 words)
read the wrong byte of the event's record for every cycle, so the boom's
+20 never applied and an average economy took 10 off; now cycles 0-4 add
bytes 1, 2, none, 3 and 4. mobile-site (whole disc image only) brings
back the cut PR event 37, Renew Mobile Site, which plClubEvent_GetList
always cleared (SLES 0x20e868, now a nop); it is offered by its own
record, from 2010-11. pr-costs (whole disc image only) doubles PR
event costs (plClubEvent_GetCost's x 300 -> x 600, 0x20deec), and
camp-costs and tour-costs (whole disc image only) scale the camp rates
(SIMPRG.REL 0x1ce4e8, 8 x 14) by 2 and the tour rates (0x1ce6c0, 14) by
3. See DOC/ECONOMY.md#pr-events and #camps-and-tours.

overseas-pop (whole disc image only) fixes the overseas popularity
factor by your best player's rank from a region (SLES 0x554ec8, 1.02 up
to 1.47 in steps of 0.03): rank 2's 10.8 becomes 1.08. cup-last16 (whole
disc image only) gives the European Club Cup's popularity points for
the last 16 (60, overseas none) to the last 16, which got nothing while
the last 32 got them: 3 words at SLES 0x26894c-0x268970. See
DOC/ECONOMY.md#supporter-popularity and #titles.

--mod-saves (whole disc image only) gives a modded disc its own saves: the
memory-card folders become BESLES-54151-Fnnn for career saves (-G on the
original), or -Mnnn on a disc with any harder-economy or balance switch
(LMASTER max), and BESLES-54151-Vnnn for VS data (-C on the original),
the same on both: two bytes of SLES_541.51 (0x5213e8, 0x5213f8;
MC::CFcEuroIF::initialize 0x12ad38). Discs built before 2026-10-27 used
-M and -D; save.py rename moves a save to the new names. The original
game never opens them, and a modded game's VS teams can't reach Virtua
Pro Football or an unmodded VS mode. The serial stays SLES-54151, so
PCSX2's GameDB entry still applies (its D-pad clamp fix and memory-card
filters). See DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc.

Every patch of a whole disc image ends with the executable's PCSX2 CRC
(the XOR of its 32-bit words; 3CB245D5 unmodified). PCSX2 names a game's
settings and savestates SLES-54151_<CRC>, and keys patches and cheats on
it, so a disc with a changed executable keeps its own.

--launcher boots into the developers' launcher, a debug menu of test
modules (viewers, screen tests, MAIN GAME START): it turns RootMainSeq.sqb's
branch past the launcher at 0x98 into BranchIfZero, 1 byte. It works on
DATA.CVM or DATA.ISO too. See DOC/SQB_FORMAT.md#the-developer-launcher.

Copies: the same data is often on the disc more than once. PRELOAD/*.PAC
bundles hold copies of loose files (REGULATION.TBB is in all seven
SIMFILE packs) and of MES.PAC entries, and a .HED repeats its archive's
header. `patch` indexes DAT/ (or --dat) and, for every file, header or
entry whose bytes the edit changes, lists the other places holding the
same bytes. Those with the same name are copies the game may read
instead; --copies writes the new bytes into them too. Identical data
under other names (shared stadium parts, say) is only reported.

PRELOAD packs: an entry that changes size (a message file mbb.py grew
into its MES.PAC slot, say) is written by rebuilding its pack with
pac.build_binpac, which moves the later entries; the pack may grow to the
end of its last sector, and one that needs more is moved (above). Entries of a PRELOAD pack, as copies or as
<path>#<entry> targets, are located through the header the pack has in
the image now, so a second run works on a rebuilt pack. Any other copy
is a fixed-size slot and keeps the old data, with a warning.

Other archives: a <path>#<entry> target of another self-describing
archive that changes size rebuilds the archive (rebuild_entry_targets)
and is then a whole-archive target, so --copies carries the new header
to its .HED and the file moves if it outgrows its sectors.

Indexes in the executable: the game finds MES.PAC's files through a
copy of its index (SLES 0x34df50, CFcEuro_MsgResource::Execute 0x10f4b0)
and the Acrobata scenes through one of AcrobataPackFile.pac's (0x3a3b08).
When either archive is a target, `patch` finds that table by the records
of the archive on the disc and rewrites the ones that change; that needs
the whole disc image. See DOC/REBUILD.md#archives.
"""
import bisect
import os
import shutil
import struct
import sys

from extract_disc import walk_iso, IsoEntry, SECTOR, PVD_SECTOR, DIR_FLAG
import cso
import rofs_decrypt

DISC = "disc:"
CVM_MAGIC = b"CVMH"
ISO_MAGIC = b"CD001"
CVM_NAME = "DATA.CVM"
CHUNK = 0x1000000


class SectorView:
    """File-like view of the ISO9660 image inside a container. Offsets are
    ISO offsets; `base` is where ISO sector 0 starts in the file. With a
    key, every sector read is decrypted, which is only right for the
    table of contents: walk_iso reads nothing else."""

    def __init__(self, f, base, key=None, zone_shift=0):
        self.f, self.base, self.key, self.zone_shift = f, base, key, zone_shift
        self.pos = 0

    def seek(self, pos):
        self.pos = pos

    def read(self, size):
        self.f.seek(self.base + self.pos)
        data = self.f.read(size)
        if self.key is not None:
            if self.pos % SECTOR or len(data) % SECTOR:
                raise ValueError("encrypted reads must be whole sectors")
            # rofs_decrypt._decrypt_iso_sector: logical sector =
            # ISO sector + zone sector - ISO start sector.
            data = rofs_decrypt.decrypt_sectors(
                data, self.pos // SECTOR + self.zone_shift, SECTOR, self.key)
        self.pos += len(data)
        return data


class Image:
    """Finds every DATA.CVM file's byte range in a disc image, DATA.CVM or
    DATA.ISO."""

    def __init__(self, path, key=None):
        self.path = path
        with open(path, "rb") as f:
            head = f.read(4)
            f.seek(PVD_SECTOR * SECTOR + 1)
            iso = f.read(5) == ISO_MAGIC
            self.cvm_base = self.cvm_size = None
            if head == CVM_MAGIC:
                self.kind, cvm_base = "DATA.CVM", 0
                self.cvm_size = os.path.getsize(path)
            elif iso:
                outer = {e.path.upper(): e for e in walk_iso(SectorView(f, 0))}
                if CVM_NAME in outer:
                    self.kind = "disc image"
                    cvm_base = outer[CVM_NAME].extent * SECTOR
                    self.cvm_range = (cvm_base, outer[CVM_NAME].size)
                    self.cvm_size = outer[CVM_NAME].size
                    f.seek(PVD_SECTOR * SECTOR + 80)
                    self.disc_sectors = struct.unpack("<I", f.read(4))[0]
                else:
                    self.kind, cvm_base = "DATA.ISO", None
            else:
                raise ValueError("%s: not a disc image, DATA.CVM or DATA.ISO" % path)

            if cvm_base is None:
                view = SectorView(f, 0)
            else:
                f.seek(cvm_base)
                if f.read(4) != CVM_MAGIC:
                    raise ValueError("%s: DATA.CVM does not start with CVMH" % path)
                # read_cvm_header seeks to 0, so give it a view of the CVM.
                hdr = rofs_decrypt.read_cvm_header(_Offset(f, cvm_base))
                if key is None:
                    # The game derives the key from the CVMH sector, so a
                    # resized DATA.CVM has its own (rofs_decrypt.header_key).
                    f.seek(cvm_base)
                    key = rofs_decrypt.header_key(f.read(SECTOR)) or rofs_decrypt.DEFAULT_KEY
                base = cvm_base + hdr["iso_start_sector"] * SECTOR
                shift = hdr["iso_zone_sector"] - hdr["iso_start_sector"]
                view = SectorView(f, base, key if hdr["encrypted"] else None, shift)
                self.cvm_base, self.iso_start = cvm_base, hdr["iso_start_sector"]
            self.iso_base, self.key, self.zone_shift = view.base, view.key, view.zone_shift
            # The ISO's volume space size (PVD +80): where moved files go.
            view.seek(PVD_SECTOR * SECTOR)
            self.iso_sectors = struct.unpack_from("<I", view.read(SECTOR), 80)[0]
            try:
                self.files = {e.path.upper(): e for e in walk_iso(view) if not e.is_dir}
            except ValueError as e:
                raise ValueError("%s: can't read the table of contents (%s); wrong key?"
                                 % (path, e))
            # Files outside DATA.CVM (SLES_541.51, DLL/*.REL, ...) are
            # "disc:<path>"; their sectors count from the start of the image.
            if self.kind == "disc image":
                for e in outer.values():
                    if not e.is_dir and e.path.upper() != CVM_NAME:
                        d = IsoEntry(DISC + e.path, e.extent, e.size, False, e.mtime)
                        self.files[d.path.upper()] = d
        self.port = Port(self) if norm(JP_EXE_FILE) in self.files else None

    def entry(self, path):
        if self.port is not None and norm(path) == norm(PAL_EXE_FILE):
            path = JP_EXE_FILE
        e = self.files.get(path.replace("\\", "/").strip("/").upper())
        if e is None:
            if path.lower().startswith(DISC) and self.kind != "disc image":
                raise ValueError("%s: disc: paths need the whole disc image, not %s"
                                 % (path, self.kind))
            raise ValueError("%s is not in %s" % (path, self.path))
        return e

    def offset(self, entry):
        if entry.path.startswith(DISC):
            return entry.extent * SECTOR
        return self.iso_base + entry.extent * SECTOR

    def toc(self, f):
        """View of the DATA.CVM image that decrypts table-of-contents reads."""
        return SectorView(f, self.iso_base, self.key, self.zone_shift)


class _Offset:
    """Minimal file wrapper that shifts seeks by `base`."""
    def __init__(self, f, base):
        self.f, self.base = f, base

    def seek(self, pos, whence=0):
        self.f.seek(self.base + pos if whence == 0 else pos, whence)

    def read(self, n=-1):
        return self.f.read(n)


# --- copies ------------------------------------------------------------------

class Unit:
    """A run of bytes in a DAT file: a whole file, a BINPAC header, or an
    archive entry. `file` is the DAT-relative path of the file that holds the
    bytes (for an entry indexed by a detached .HED, the data file)."""

    def __init__(self, kind, file, off, size, name, index=None):
        self.kind, self.file, self.off, self.size = kind, file, off, size
        self.name, self.index = name, index
        self.key = None

    @property
    def label(self):
        if self.kind == "file":
            return self.file
        if self.kind == "header":
            return self.file + "#header"
        return "%s#%d:%s" % (self.file, self.index, self.name)

    def simple_name(self):
        """Lower-case name without directories, for matching copies. A
        header is named like the .HED that copies it."""
        if self.kind == "header":
            return os.path.splitext(os.path.basename(self.file))[0].lower() + ".hed"
        return self.name.replace("\\", "/").split("/")[-1].lower()


TRUNCATED_NAME = 15     # BINPAC name fields are 16+ bytes (or 4, extension only)


def same_name(a, b):
    """Equal names, or, since a BINPAC name keeps only the last name_len
    characters of the path, a long name that is the tail of the other.
    Short names must match exactly (1_0.mbb is not 100001_0.mbb)."""
    x, y = a.simple_name(), b.simple_name()
    if not x or not y:
        return False
    if x == y:
        return True
    short, long_ = sorted((x, y), key=len)
    return len(short) >= TRUNCATED_NAME and long_.endswith(short)


class Index:
    """Every loose file, BINPAC header and archive entry under a DAT
    directory, by size and SHA-1. PRS-compressed entries are compared as
    stored, so a copy stored with different compression isn't found."""

    MIN_SIZE = 16

    def __init__(self, dat):
        import hashlib
        import pac
        self.dat = dat
        self.by_key, self.by_file = {}, {}

        def add(u, data):
            if u.size < self.MIN_SIZE:
                return
            u.key = (u.size, hashlib.sha1(data).digest())
            self.by_key.setdefault(u.key, []).append(u)
            self.by_file.setdefault(u.file.upper(), []).append(u)

        for root, dirs, files in os.walk(dat):
            dirs[:] = sorted(d for d in dirs if d != "CVS")
            for n in sorted(files):
                full = os.path.join(root, n)
                rel = os.path.relpath(full, dat).replace(os.sep, "/")
                with open(full, "rb") as f:
                    data = f.read()
                add(Unit("file", rel, 0, len(data), os.path.basename(rel)), data)
                try:
                    h = pac.load_header(full)
                except (ValueError, struct.error):
                    h = None
                if h is None:
                    continue
                dp = pac.data_path(full, h)
                if dp is None or not os.path.exists(dp):
                    continue
                if dp != full:
                    with open(dp, "rb") as f:
                        if f.read(16)[10:16] == b"BINPAC":
                            continue    # the partner describes itself
                    with open(dp, "rb") as f:
                        src = f.read()
                else:
                    src = data
                    if isinstance(h, pac.BinPac):
                        add(Unit("header", rel, 0, h.header_size, ""), data[:h.header_size])
                drel = os.path.relpath(dp, dat).replace(os.sep, "/")
                for i, (off, size, name, _) in enumerate(h.entries):
                    if off + size <= len(src):
                        add(Unit("entry", drel, off, size, name, i), src[off:off + size])

    def units(self, path):
        return self.by_file.get(norm(path), [])

    def resolve(self, target):
        """'PATH' or 'PATH#N' / 'PATH#name' -> the Unit."""
        path, _, sel = target.partition("#")
        units = self.units(path)
        if not units:
            raise ValueError("%s is not in %s" % (path, self.dat))
        if not sel:
            return next(u for u in units if u.kind == "file")
        if sel.lower() == "header":
            hit = [u for u in units if u.kind == "header"]
        elif sel.isdigit():
            hit = [u for u in units if u.kind == "entry" and u.index == int(sel)]
        else:
            probe = Unit("entry", path, 0, 0, sel)
            hit = [u for u in units if u.kind == "entry" and same_name(u, probe)]
        if len(hit) != 1:
            raise ValueError("%s: %s" % (target, "no such entry" if not hit else
                                         "%d entries match; use the index" % len(hit)))
        return hit[0]

    def copies(self, unit):
        """(same-name copies, other identical units) in other files."""
        others = [u for u in self.by_key.get(unit.key, []) if u.file.upper() != unit.file.upper()]
        named = [u for u in others if same_name(u, unit)]
        return named, [u for u in others if u not in named]


def norm(path):
    return path.replace("\\", "/").strip("/").upper()


# --- the Japanese release (DOC/JAPANESE_RELEASE.md) -------------------------------

# The switches give their bytes as offsets in the PAL executable and
# overlays. On the Japanese disc (SLPM_663.16) Port moves each offset to
# the same code or table there, with gamever.py, which compares against
# the PAL files in ISO/. A switch then checks the bytes it finds as it
# does on PAL, and refuses where the Japanese build differs.
PAL_EXE_FILE = DISC + "SLES_541.51"
JP_EXE_FILE = DISC + "SLPM_663.16"
EXE_BASE = 0xff000              # SLES_541.51's file offset 0 is address 0xff000
PORT_NEAR = 0x40
PORT_CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          ".cache", "port")


class Port:
    """PAL offsets in SLES_541.51 and DLL/*.REL as offsets in another
    build's files. Every range a switch reads is found once and
    remembered, so the jobs it plans inside that range land where the
    bytes it checked are."""

    def __init__(self, img):
        self.img = img
        self.paths = {}         # norm(file) -> local copy for gamever
        self.ranges = []        # (norm(PAL file), PAL start, end, file, offset there)

    def code_file(self, file):
        n = norm(file)
        return n == norm(PAL_EXE_FILE) or (n.startswith(norm(DISC + "DLL/"))
                                           and n.endswith(".REL"))

    def copy(self, file):
        """A local copy of the image's `file`, where gamever can read it
        (named as on the disc, an overlay under DLL/)."""
        n = norm(file)
        if n not in self.paths:
            e = self.img.entry(file)
            with open(self.img.path, "rb") as f:
                f.seek(self.img.offset(e))
                data = f.read(e.size)
            import hashlib
            rel = e.path[len(DISC):]
            path = os.path.join(PORT_CACHE, hashlib.sha1(data).hexdigest()[:16], rel)
            if not os.path.exists(path):
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "wb") as g:
                    g.write(data)
            self.paths[n] = path
        return self.paths[n]

    def find(self, file, off):
        """(file, offset) in this build for PAL `file` and `off`."""
        import gamever
        if norm(file) == norm(PAL_EXE_FILE):
            import sles_disasm
            path = self.copy(JP_EXE_FILE)
            try:
                addr = gamever.at(path, off + EXE_BASE)
            except ValueError as e:
                raise ValueError("%s 0x%x has no counterpart in %s: %s"
                                 % (PAL_EXE_FILE, off + EXE_BASE, JP_EXE_FILE, e))
            return JP_EXE_FILE, sles_disasm.Elf(path).v2f(addr)
        try:
            return file, gamever.at(self.copy(file), off)
        except ValueError as e:
            raise ValueError("%s 0x%x has no counterpart in the Japanese build: %s"
                             % (file, off, e))

    def map(self, file, off, size=1):
        """(file, offset) to read or write `size` bytes the PAL switch
        addresses at `file` `off`; unchanged for any other file."""
        if not self.code_file(file):
            return file, off
        n = norm(file)
        for pal, start, end, there, base in self.ranges:
            if pal == n and start <= off and off + size <= end:
                return there, base + off - start
        try:
            there, base = self.find(file, off)
        except ValueError:
            # Code the byte search can't place (repeated blocks): the same
            # shift as an address translated up to PORT_NEAR before or after.
            near = [(abs(start - off), there, base - start) for pal, start, _, there, base
                    in self.ranges if pal == n and abs(start - off) <= PORT_NEAR]
            if not near:
                raise
            _, there, shift = min(near)
            base = off + shift
        self.ranges.append((n, off, off + size, there, base))
        return there, base

    def expect(self, f, file, off, old):
        """Place PAL `file` `off`, where the switch expects the bytes `old`:
        as map does, or else where `old` occurs once in this build's
        function of the same name. A word map places anywhere else is
        left for the switch to refuse."""
        if not self.code_file(file):
            return
        try:
            there, base = self.map(file, off, len(old))
            if read_raw(f, self.img, there, base, len(old)) == old:
                return
        except ValueError:
            pass
        import gamever
        pal_path = gamever.reference_of(self.copy(JP_EXE_FILE if norm(file) == norm(
            PAL_EXE_FILE) else file))
        there = JP_EXE_FILE if norm(file) == norm(PAL_EXE_FILE) else file
        ref, other = gamever.image(pal_path), gamever.image(self.copy(there))
        addr = off + (EXE_BASE if there == JP_EXE_FILE else 0)
        names = gamever._named(ref)
        i = bisect.bisect_right(names, addr) - 1
        name = ref.name_at[names[i]] if i >= 0 else None
        if name not in other.addr_of:
            return
        lo = other.addr_of[name]
        theirs = gamever._named(other)
        j = bisect.bisect_right(theirs, lo)
        hi = theirs[j] if j < len(theirs) else lo + 0x10000
        a, b = other.v2f(lo), other.v2f(hi) if other.v2f(hi) is not None else len(other.data)
        hits, k = [], other.data.find(old, a, b)
        while k >= 0:
            if k % 4 == 0:
                hits.append(k)
            k = other.data.find(old, k + 1, b)
        if len(hits) == 1:
            n = norm(file)
            self.ranges = [r for r in self.ranges if not (r[0] == n and r[1] <= off < r[2])]
            self.ranges.append((n, off, off + len(old), there, hits[0]))

    def jobs(self, jobs):
        """The jobs a switch planned in PAL offsets, moved to this build."""
        out = []
        for j in jobs:
            if j.file is None or not self.code_file(j.file):
                out.append(j)
                continue
            file, off = self.map(j.file, j.off, len(j.data))
            addr = off
            if norm(file) == norm(JP_EXE_FILE):
                import sles_disasm
                addr = sles_disasm.Elf(self.copy(JP_EXE_FILE)).f2v(off)
            out.append(Job(file, off, j.data, "%s (Japanese build: %s 0x%x)" % (
                j.label, file[len(DISC):], addr), j.why))
        return out


# --- targets -----------------------------------------------------------------

def parse_pairs(args):
    pairs = []
    for a in args:
        if "=" not in a:
            raise SystemExit("expected <path>=<file>, got %r" % a)
        target, src = a.split("=", 1)
        with open(src, "rb") as f:
            pairs.append((target, src, f.read()))
    return pairs


class Job:
    """Bytes to write at `off` inside DAT file `file`, or at byte `off` of
    the image when `file` is None (directory records)."""
    def __init__(self, file, off, data, label, why):
        self.file, self.off, self.data, self.label, self.why = file, off, data, label, why

    def pos(self, img):
        return self.off if self.file is None else img.offset(img.entry(self.file)) + self.off


# --- renaming files outside DATA.CVM -------------------------------------------

ISO_NAME_CHARS = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.")
UDF_FID = 0x101     # File Identifier Descriptor tag


def udf_crc(data):
    """CRC-16/CCITT (poly 0x1021, init 0), as UDF descriptor tags use."""
    crc = 0
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def udf_tag_ok(buf, pos):
    tag = buf[pos:pos + 16]
    return len(tag) == 16 and (sum(tag) - tag[4]) & 0xFF == tag[4]


def plan_rename(f, img, target, new):
    """Jobs renaming a file on the outer disc (same name length) in its
    ISO9660 directory record and, on a UDF bridge disc, its UDF File
    Identifier Descriptor."""
    from extract_disc import _read, _parse_record
    if img.kind != "disc image" or not target.lower().startswith(DISC):
        raise ValueError("--rename takes disc:<path> on a whole disc image")
    e = img.entry(target)
    path = e.path[len(DISC):]
    parent, _, old = path.rpartition("/")
    new = new.upper()
    if len(new) != len(old) or not set(new) <= ISO_NAME_CHARS:
        raise ValueError("%s: the new name must have the same length (%d) and use only "
                         "A-Z, 0-9, _ and ." % (target, len(old)))
    jobs = []

    # ISO9660: the record in the parent directory whose extent is the file's.
    dirs = {"": None}
    for d in walk_iso(SectorView(f, 0)):
        if d.is_dir:
            dirs[d.path.upper()] = d
    if parent:
        dext, dsize = dirs[parent.upper()].extent, dirs[parent.upper()].size
    else:
        pvd = _read(SectorView(f, 0), PVD_SECTOR, SECTOR)
        _, dext, dsize, _, _, _ = _parse_record(pvd, 156)
    buf = _read(SectorView(f, 0), dext, dsize)
    hits = []
    for sec in range(0, dsize, SECTOR):
        pos = sec
        while pos < min(sec + SECTOR, dsize) and buf[pos]:
            rec_len, ext, _, _, name, _ = _parse_record(buf, pos)
            if ext == e.extent and name.split(b";")[0].rstrip(b".").decode("ascii") == old:
                hits.append((pos, name))
            pos += rec_len
    if len(hits) != 1:
        raise ValueError("%s: found %d ISO9660 records for it" % (target, len(hits)))
    pos, name = hits[0]
    jobs.append(Job(None, dext * SECTOR + pos + 33, new.encode() + name[len(old):],
                    "%s (ISO9660 record)" % target, "rename to " + new))

    # UDF: FIDs sit in the metadata before the first file. Match the name
    # and require exactly one, with a tag whose CRC checks out.
    first = min(x.extent for x in img.files.values() if x.path.startswith(DISC))
    f.seek(0)
    meta = f.read(first * SECTOR)
    want = [(8, old.encode("latin1")), (16, old.encode("utf-16-be"))]
    hits = []
    for sec in range(0, len(meta), SECTOR):
        pos = sec
        while pos + 38 <= min(sec + SECTOR, len(meta)):
            if meta[pos:pos + 2] == UDF_FID.to_bytes(2, "little") and udf_tag_ok(meta, pos):
                crc_len = struct.unpack_from("<H", meta, pos + 10)[0]
                l_fi = meta[pos + 19]
                l_iu = struct.unpack_from("<H", meta, pos + 36)[0]
                ident = meta[pos + 38 + l_iu:pos + 38 + l_iu + l_fi]
                if ident and (ident[0], ident[1:]) in want:
                    hits.append((pos, crc_len, l_iu, ident))
                pos += (38 + l_iu + l_fi + 3) & ~3
            else:
                pos += 4
    if len(hits) > 1:
        raise ValueError("%s: found %d UDF entries with its name" % (target, len(hits)))
    if hits:
        pos, crc_len, l_iu, ident = hits[0]
        desc = bytearray(meta[pos:pos + 16 + crc_len])
        if udf_crc(desc[16:]) != struct.unpack_from("<H", desc, 8)[0]:
            raise ValueError("%s: its UDF descriptor's CRC doesn't check out" % target)
        enc = "latin1" if ident[0] == 8 else "utf-16-be"
        at = 38 + l_iu + 1
        desc[at:at + len(ident) - 1] = new.encode(enc)
        struct.pack_into("<H", desc, 8, udf_crc(desc[16:]))
        desc[4] = (sum(desc[:16]) - desc[4]) & 0xFF
        jobs.append(Job(None, pos, bytes(desc), "%s (UDF identifier)" % target, "rename to " + new))
    return jobs


# --- size changes inside the last sector --------------------------------------

def sectors(size):
    return (size + SECTOR - 1) // SECTOR


def to_sector_end(data):
    """`data` zero-padded to the end of its last sector. Every file's last
    sector ends in zeros (2,024 of 2,024 in DATA.CVM), so a file that
    changes size is written with them, and patching the original back
    gives the original image."""
    return data + bytes(-len(data) % SECTOR)


class TocEdits:
    """Edits to DATA.ISO's table of contents: new sizes and first sectors
    in files' directory records, and the volume size in the PVD. The
    sectors are kept decrypted until jobs(), which encrypts each changed
    one once. A size inside the file's last sector needs nothing else: the
    game reads a whole file as (size + 0x7ff) >> 11 sectors
    (ADXF_GetFsizeSct, used by CFileManagerRofs::FileUpdateCore at
    0x307f24). A file that needs more sectors is moved first (Moves).

    The key comes from the CVMH header and changes with DATA.CVM's size
    (rofs_decrypt.header_key). When plan_grow sets `new_key`, every
    encrypted sector, the PVD through the last directory sector, is
    encrypted again with it. The XOR stream is its own inverse."""

    def __init__(self):
        self.edits = {}
        self.plain = {}         # ISO sector -> decrypted bytes, edited in place
        self.new_key = None

    def sector(self, f, img, sec):
        if sec not in self.plain:
            view = img.toc(f)
            view.seek(sec * SECTOR)
            self.plain[sec] = bytearray(view.read(SECTOR))
        return self.plain[sec]

    def add(self, img, path, new_size, new_extent=None):
        e = img.entry(path)
        if e.path.startswith(DISC):
            raise ValueError("%s: files outside DATA.CVM can't change size or move" % path)
        if new_extent is None and sectors(new_size) != sectors(e.size):
            raise ValueError("%s: %d bytes need %d sectors, but the file has %d"
                             % (path, new_size, sectors(new_size), sectors(e.size)))
        self.edits[e.path.upper()] = (e, new_size, e.extent if new_extent is None else new_extent)

    def _record(self, f, img, e):
        """(sector, offset) of a file's directory record."""
        from extract_disc import _parse_record
        parent = e.path.rpartition("/")[0].upper()
        if parent:
            d = next(x for x in walk_iso(img.toc(f)) if x.is_dir and x.path.upper() == parent)
            dext, dsize = d.extent, d.size
        else:
            _, dext, dsize, _, _, _ = _parse_record(self.sector(f, img, PVD_SECTOR), 156)
        for sec in range(dext, dext + sectors(dsize)):
            buf = self.sector(f, img, sec)
            pos = 0
            while pos < SECTOR and buf[pos]:
                rec_len, ext, size, flags, name, _ = _parse_record(buf, pos)
                # By name too: an empty file can share the extent
                # (MESSAGE/DUMMY.DAT and MES.PAC).
                mine = name.split(b";")[0].decode("ascii", "replace").upper() ==                     e.path.rpartition("/")[2].upper()
                if ext == e.extent and not flags & DIR_FLAG and mine:
                    if size != e.size or buf[pos + 1]:
                        raise ValueError("%s: directory record doesn't match (%d bytes, "
                                         "%d extended-attribute sectors)"
                                         % (e.path, size, buf[pos + 1]))
                    return sec, pos
                pos += rec_len
        raise ValueError("%s: no directory record found" % e.path)

    def jobs(self, f, img):
        changed = {}            # sector -> reasons
        for e, new_size, new_extent in self.edits.values():
            sec, pos = self._record(f, img, e)
            buf = self.sector(f, img, sec)
            # Both-endian u32s: extent at +2/+6, size at +10/+14.
            struct.pack_into("<I", buf, pos + 2, new_extent)
            struct.pack_into(">I", buf, pos + 6, new_extent)
            struct.pack_into("<I", buf, pos + 10, new_size)
            struct.pack_into(">I", buf, pos + 14, new_size)
            changed.setdefault(sec, []).append("%s size %d -> %d%s" % (
                e.path, e.size, new_size,
                ", sector %d -> %d" % (e.extent, new_extent) if new_extent != e.extent else ""))
        if PVD_SECTOR in self.plain and self.plain[PVD_SECTOR] != self.sector_original(f, img):
            changed.setdefault(PVD_SECTOR, []).append("volume size %d -> %d sectors" % (
                img.iso_sectors, struct.unpack_from("<I", self.plain[PVD_SECTOR], 80)[0]))
        key = img.key
        if self.new_key is not None and self.new_key != img.key:
            key = self.new_key
            hdr = rofs_decrypt.read_cvm_header(_Offset(f, img.cvm_base))
            end = rofs_decrypt.find_toc_end_sector(_Offset(f, img.cvm_base), hdr, img.key)
            for sec in range(PVD_SECTOR, end):
                self.sector(f, img, sec)
                changed.setdefault(sec, []).append("re-encrypted with key %s" % key.hex().upper())
        jobs = []
        for sec, why in sorted(changed.items()):
            data = bytes(self.plain[sec])
            if key is not None:
                data = rofs_decrypt.decrypt_sectors(data, sec + img.zone_shift, SECTOR, key)
            label = ("DATA.ISO volume descriptor" if sec == PVD_SECTOR else
                     "directory sector %d" % sec)
            jobs.append(Job(None, img.iso_base + sec * SECTOR, data, label, "; ".join(why)))
        return jobs

    def sector_original(self, f, img):
        view = img.toc(f)
        view.seek(PVD_SECTOR * SECTOR)
        return bytearray(view.read(SECTOR))


# --- moving files to the end of DATA.ISO --------------------------------------
#
# DATA.ISO has no free sectors between its files, and DATA.CVM is the last
# file on the disc, followed by 10,247 zero sectors and the UDF anchor in
# the disc's last sector. A file that outgrows its sectors is written after
# the ISO's last sector and its directory record pointed there; its old
# sectors are left as they are. DATA.CVM grows into the zeros, so these
# lengths follow (DOC/REBUILD.md#moving-files):
#   ISO PVD +80/+84       volume space size, in sectors (both-endian)
#   CVMH +0x1c            DATA.CVM size in bytes (u64 big-endian)
#   ZONE +0x04            ZONE chunk length, the CVM size - 0x80c (u64 BE)
#   ZONE +0x30            the ISO's length in bytes (u64 BE)
#   disc ISO9660 record   DATA.CVM's size (both-endian u32)
#   disc UDF File Entry   information length (+56), blocks recorded (+64)
#                         and its one allocation descriptor's length
CVMH_SIZE, ZONE_AT = 0x1c, 0x800
ZONE_LENGTH, ZONE_ISO_LENGTH = 0x04, 0x30
ZONE_REST = 0x80c           # CVM size - ZONE chunk length
UDF_FILE_ENTRY = 261


class Moves:
    """Files to move to the end of DATA.ISO."""

    def __init__(self):
        self.files = {}

    def add(self, file, data, label, why):
        self.files[norm(file)] = (file, data, label, why)

    def plan(self, f, img, toc):
        if not self.files:
            return [], []
        if img.cvm_base is None and img.kind != "DATA.ISO":
            raise ValueError("can't move files in %s" % img.path)
        jobs, notes = [], []
        end = img.iso_sectors
        for file, data, label, why in self.files.values():
            e = img.entry(file)
            if e.extent + sectors(e.size) == end:
                # Already the last file (moved by an earlier run): grow in place.
                start = e.extent
            else:
                start = end
            end = start + sectors(len(data))
            where = ("moved to ISO sector %d" % start if start != e.extent else
                     "grown in place at the end of DATA.ISO")
            jobs.append(Job(None, img.iso_base + start * SECTOR, to_sector_end(data), label,
                            "%s, %s" % (why, where)))
            toc.add(img, file, len(data), start)
            notes.append("note: %s needs %d sectors (had %d): %s" % (
                e.path, sectors(len(data)), sectors(e.size),
                "moved from ISO sector %d to %d" % (e.extent, start) if start != e.extent
                else where))
        # Growing comes first: growing the disc clears the old UDF end
        # anchor, which the moved data may then cover.
        return plan_grow(f, img, end, toc) + jobs, notes


def _udf_cvm_entry(f, img):
    """(disc byte offset, bytes) of DATA.CVM's UDF File Entry, or None on a
    disc without UDF. Found through its File Identifier Descriptor, which
    sits in the metadata before the first file, and the partition start in
    the Partition Descriptor of the volume descriptor sequence named by the
    anchor at sector 256."""
    f.seek(256 * SECTOR)
    anchor = f.read(SECTOR)
    if struct.unpack_from("<H", anchor, 0)[0] != 2 or not udf_tag_ok(anchor, 0):
        return None
    vds_len, vds_loc = struct.unpack_from("<II", anchor, 16)
    part_start = None
    for n in range(vds_loc, vds_loc + vds_len // SECTOR):
        f.seek(n * SECTOR)
        d = f.read(SECTOR)
        tag = struct.unpack_from("<H", d, 0)[0]
        if tag == 5:
            part_start = struct.unpack_from("<I", d, 188)[0]
        if tag == 8 or tag == 0:
            break
    if part_start is None:
        raise ValueError("%s: UDF anchor found but no partition descriptor" % img.path)
    first = min(x.extent for x in img.files.values() if x.path.startswith(DISC))
    f.seek(0)
    meta = f.read(first * SECTOR)
    hits = []
    for pos in range(0, len(meta) - 38, 4):
        if meta[pos:pos + 2] == UDF_FID.to_bytes(2, "little") and udf_tag_ok(meta, pos):
            l_fi = meta[pos + 19]
            l_iu = struct.unpack_from("<H", meta, pos + 36)[0]
            ident = meta[pos + 38 + l_iu:pos + 38 + l_iu + l_fi]
            if ident[1:] in (CVM_NAME.encode("utf-16-be"), CVM_NAME.encode("latin1")):
                hits.append(struct.unpack_from("<I", meta, pos + 24)[0])
    if len(hits) != 1:
        raise ValueError("%s: found %d UDF entries for %s" % (img.path, len(hits), CVM_NAME))
    off = (part_start + hits[0]) * SECTOR
    f.seek(off)
    fe = f.read(SECTOR)
    if struct.unpack_from("<H", fe, 0)[0] != UDF_FILE_ENTRY or not udf_tag_ok(fe, 0):
        raise ValueError("%s: no UDF File Entry where %s's identifier points" % (img.path, CVM_NAME))
    return off, fe


# A single-layer DVD holds 2,295,104 sectors; a bigger image would need a
# layer break, which the disc doesn't have.
DVD5_SECTORS = 2295104
DVD_BLOCK = 16              # sectors per DVD ECC block
UDF_ANCHOR, UDF_PARTITION, UDF_LVID = 2, 5, 9


def _udf_retag(buf, location=None):
    """Recompute a UDF descriptor tag's CRC (over the descriptor after the
    16-byte tag) and checksum, optionally with a new tag location."""
    crc_len = struct.unpack_from("<H", buf, 10)[0]
    if location is not None:
        struct.pack_into("<I", buf, 12, location)
    struct.pack_into("<H", buf, 8, udf_crc(buf[16:16 + crc_len]))
    buf[4] = (sum(buf[:16]) - buf[4]) & 0xFF


def plan_grow_disc(f, img, cvm_end):
    """Jobs growing the disc image so that DATA.CVM can end at sector
    `cvm_end`, with the UDF end anchor in the new last sector. The size is
    in the ISO9660 PVD (+80/+84), the UDF Partition Descriptors of the
    main and reserve volume descriptor sequences (+192, the partition runs
    to the anchor), the Logical Volume Integrity Descriptor's size table,
    and the end anchor's own position. The user reports that an image with
    extra files added, so bigger than the original, still ran."""
    new_disc = -(-(cvm_end + 1) // DVD_BLOCK) * DVD_BLOCK
    if new_disc > DVD5_SECTORS:
        raise ValueError("the disc would need %d sectors, more than a single-layer DVD (%d)"
                         % (new_disc, DVD5_SECTORS))
    old_disc = img.disc_sectors
    jobs = []
    pvd = struct.pack("<I", new_disc) + struct.pack(">I", new_disc)
    jobs.append(Job(None, PVD_SECTOR * SECTOR + 80, pvd, "disc volume descriptor",
                    "volume size %d -> %d sectors" % (old_disc, new_disc)))

    f.seek(256 * SECTOR)
    anchor = bytearray(f.read(SECTOR))
    f.seek((old_disc - 1) * SECTOR)
    end_anchor = bytearray(f.read(SECTOR))
    if struct.unpack_from("<H", anchor, 0)[0] != UDF_ANCHOR:
        return jobs     # no UDF
    if struct.unpack_from("<H", end_anchor, 0)[0] != UDF_ANCHOR or             struct.unpack_from("<I", end_anchor, 12)[0] != old_disc - 1:
        raise ValueError("%s: no UDF anchor in the disc's last sector" % img.path)
    # Main and reserve volume descriptor sequences (anchor +16, +24).
    lvid_at = part_start = None
    for at in (16, 24):
        length, loc = struct.unpack_from("<II", anchor, at)
        for n in range(loc, loc + length // SECTOR):
            f.seek(n * SECTOR)
            d = bytearray(f.read(SECTOR))
            tag = struct.unpack_from("<H", d, 0)[0]
            if tag == UDF_PARTITION:
                part_start, part_len = struct.unpack_from("<II", d, 188)
                if part_start + part_len != old_disc - 1:
                    raise ValueError("%s: the UDF partition doesn't end at the anchor"
                                     % img.path)
                struct.pack_into("<I", d, 192, new_disc - 1 - part_start)
                _udf_retag(d)
                jobs.append(Job(None, n * SECTOR, bytes(d), "UDF partition descriptor (sector %d)"
                                % n, "length %d -> %d" % (part_len, new_disc - 1 - part_start)))
            elif tag == 6 and lvid_at is None:      # Logical Volume Descriptor
                lvid_at = struct.unpack_from("<I", d, 436)[0]
            elif tag in (0, 8):
                break
    if part_start is None:
        raise ValueError("%s: no UDF partition descriptor" % img.path)
    if lvid_at is not None:
        f.seek(lvid_at * SECTOR)
        d = bytearray(f.read(SECTOR))
        if struct.unpack_from("<H", d, 0)[0] == UDF_LVID:
            parts = struct.unpack_from("<I", d, 72)[0]
            for i in range(parts):
                at = 80 + 4 * parts + 4 * i
                if struct.unpack_from("<I", d, at)[0] == old_disc - 1 - part_start:
                    struct.pack_into("<I", d, at, new_disc - 1 - part_start)
            _udf_retag(d)
            jobs.append(Job(None, lvid_at * SECTOR, bytes(d), "UDF integrity descriptor",
                            "partition size %d -> %d" % (old_disc - 1 - part_start,
                                                         new_disc - 1 - part_start)))
    # The anchor moves to the new last sector; the old one becomes zeros
    # (written first, as DATA.CVM's new data may cover it).
    _udf_retag(end_anchor, new_disc - 1)
    jobs.insert(0, Job(None, (old_disc - 1) * SECTOR, bytes(SECTOR), "old UDF end anchor",
                       "cleared"))
    jobs.append(Job(None, (new_disc - 1) * SECTOR, bytes(end_anchor), "UDF end anchor",
                    "moved to sector %d" % (new_disc - 1)))
    return jobs


def plan_grow(f, img, iso_sectors, toc):
    """Jobs setting the ISO's volume size to `iso_sectors` and, around it,
    DATA.CVM's lengths: its header and, on a whole disc image, its ISO9660
    record and UDF File Entry. The CVM may only grow into zero sectors."""
    from extract_disc import _read, _parse_record
    jobs = []
    pvd = toc.sector(f, img, PVD_SECTOR)
    struct.pack_into("<I", pvd, 80, iso_sectors)
    struct.pack_into(">I", pvd, 84, iso_sectors)
    if img.cvm_base is None:
        return jobs

    new_size = (img.iso_start + iso_sectors) * SECTOR
    old_size = img.cvm_size
    f.seek(img.cvm_base)
    head = bytearray(f.read(ZONE_AT + ZONE_ISO_LENGTH + 8))
    if struct.unpack_from(">Q", head, CVMH_SIZE)[0] != old_size or \
            struct.unpack_from(">Q", head, ZONE_AT + ZONE_LENGTH)[0] != old_size - ZONE_REST or \
            struct.unpack_from(">Q", head, ZONE_AT + ZONE_ISO_LENGTH)[0] != \
            old_size - img.iso_start * SECTOR or head[ZONE_AT:ZONE_AT + 4] != b"ZONE":
        raise ValueError("%s: the CVMH/ZONE lengths don't match DATA.CVM's size %d"
                         % (img.path, old_size))
    struct.pack_into(">Q", head, CVMH_SIZE, new_size)
    struct.pack_into(">Q", head, ZONE_AT + ZONE_LENGTH, new_size - ZONE_REST)
    struct.pack_into(">Q", head, ZONE_AT + ZONE_ISO_LENGTH, new_size - img.iso_start * SECTOR)
    jobs.append(Job(None, img.cvm_base, bytes(head), "DATA.CVM header (CVMH/ZONE)",
                    "size %d -> %d" % (old_size, new_size)))
    if img.key is not None:
        f.seek(img.cvm_base)
        sector0 = bytearray(f.read(SECTOR))
        sector0[:len(head)] = head
        toc.new_key = rofs_decrypt.header_key(bytes(sector0))
    if img.kind != "disc image" or new_size <= old_size:
        return jobs

    # The sectors DATA.CVM grows into must be unused. On this disc they are
    # zeros up to the UDF anchor in the last sector; past that, the disc
    # grows (plan_grow_disc).
    lo, hi = sectors(img.cvm_base + old_size), sectors(img.cvm_base + new_size)
    f.seek(lo * SECTOR)
    for _ in range(lo, min(hi, img.disc_sectors - 1)):
        if any(f.read(SECTOR)):
            raise ValueError("DATA.CVM can't grow: sectors after it aren't empty")
    if hi > img.disc_sectors - 1:
        jobs += plan_grow_disc(f, img, hi)

    # ISO9660 record in the root directory.
    pvd = _read(SectorView(f, 0), PVD_SECTOR, SECTOR)
    _, dext, dsize, _, _, _ = _parse_record(pvd, 156)
    buf = _read(SectorView(f, 0), dext, dsize)
    hits = []
    for sec in range(0, dsize, SECTOR):
        pos = sec
        while pos < min(sec + SECTOR, dsize) and buf[pos]:
            rec_len, ext, size, flags, name, _ = _parse_record(buf, pos)
            if ext * SECTOR == img.cvm_base and name.split(b";")[0] == CVM_NAME.encode():
                hits.append(pos)
            pos += rec_len
    if len(hits) != 1:
        raise ValueError("%s: found %d ISO9660 records for %s" % (img.path, len(hits), CVM_NAME))
    jobs.append(Job(None, dext * SECTOR + hits[0] + 10,
                    struct.pack("<I", new_size) + struct.pack(">I", new_size),
                    "DATA.CVM (disc ISO9660 record)", "size %d -> %d" % (old_size, new_size)))

    # UDF File Entry. Its one short allocation descriptor holds the whole
    # 32-bit length, over the two extent-type bits, as the mastering tool
    # wrote it (1,970,935,808 shows as 0x757a1800); kept that way.
    udf = _udf_cvm_entry(f, img)
    if udf is not None:
        off, fe = udf
        fe = bytearray(fe)
        l_ea, l_ad = struct.unpack_from("<II", fe, 168)
        crc_len = struct.unpack_from("<H", fe, 10)[0]
        if struct.unpack_from("<Q", fe, 56)[0] != old_size or l_ad != 8 or fe[34] & 7 != 0 or \
                struct.unpack_from("<I", fe, 176 + l_ea)[0] != old_size or \
                udf_crc(fe[16:16 + crc_len]) != struct.unpack_from("<H", fe, 8)[0]:
            raise ValueError("%s: DATA.CVM's UDF File Entry isn't the expected single extent "
                             "of %d bytes" % (img.path, old_size))
        struct.pack_into("<Q", fe, 56, new_size)
        struct.pack_into("<Q", fe, 64, sectors(new_size))
        struct.pack_into("<I", fe, 176 + l_ea, new_size)
        struct.pack_into("<H", fe, 8, udf_crc(fe[16:16 + crc_len]))
        fe[4] = (sum(fe[:16]) - fe[4]) & 0xFF
        jobs.append(Job(None, off, bytes(fe[:16 + crc_len]), "DATA.CVM (disc UDF File Entry)",
                        "size %d -> %d" % (old_size, new_size)))
    return jobs


# PRELOAD packs are the only archives that can be rebuilt with entries
# moved: the game finds their entries through the pack's own header
# (CFcEuro_FileResource::Execute, 0x10d848-0x10d9dc). MES.PAC entries are
# found by the executable too, and other archives have .HED copies of
# their header, so those keep the same-size rule.
REPACKABLE = "PRELOAD/"


def repackable(file):
    return norm(file).startswith(REPACKABLE)


class PackEdits:
    """Entry edits for PRELOAD packs, collected so that each pack is written
    once, located by the header it has in the image now (an earlier run
    may have rebuilt it), and rebuilt if an entry changes size."""

    def __init__(self):
        self.packs = {}

    def add(self, file, index, new, old, label, why):
        pack = self.packs.setdefault(norm(file), {"file": file, "edits": {}})
        prev = pack["edits"].get(index)
        if prev is not None and prev[0] != new:
            raise ValueError("%s gets two different new contents (%s, %s)" % (label, prev[3], why))
        pack["edits"][index] = (new, old, label, why)

    def fold(self, f, img, job):
        """Fold a Job that writes inside an entry of a pack collected here
        (one this run rebuilds) into that entry's edit, so the bytes land
        where the entry ends up (drill-names' MES copies in the SIMFILE
        packs that third-tier's REGULATION.TBB copies grow)."""
        import pac
        pack = self.packs[norm(job.file)]
        e = img.entry(pack["file"])
        h, blobs = pac.binpac_blobs(read_at(f, img, pack["file"], 0, e.size))
        for i, (off, size, _, _) in enumerate(h.entries):
            if off <= job.off and job.off + len(job.data) <= off + size:
                prev = pack["edits"].get(i)
                if prev is not None and len(prev[0]) != len(blobs[i]):
                    raise ValueError("%s: an edit inside %s, which changes size too"
                                     % (job.why, prev[2]))
                cur = bytearray(prev[0] if prev else blobs[i])
                cur[job.off - off:job.off - off + len(job.data)] = job.data
                why = prev[3] if prev else job.why
                if prev and job.why not in why.split("; "):
                    why += "; " + job.why
                pack["edits"][i] = (bytes(cur), blobs[i], prev[2] if prev else job.label, why)
                return
        raise ValueError("%s: its edit at 0x%x of %s isn't inside one entry"
                         % (job.why, job.off, pack["file"]))

    def plan(self, f, img, toc, moves):
        import pac
        jobs, notes = [], []
        for pack in self.packs.values():
            file = pack["file"]
            e = img.entry(file)
            cur = read_at(f, img, file, 0, e.size)
            h, blobs = pac.binpac_blobs(cur)
            todo = []
            for i, (new, old, label, why) in sorted(pack["edits"].items()):
                if blobs[i] == new:
                    notes.append("note: %s already holds the new bytes" % label)
                elif old is not None and blobs[i] != old:
                    notes.append("note: %s holds neither the original nor the new bytes of "
                                 "%s; left alone" % (label, why))
                else:
                    todo.append((i, new, label, why))
            if all(len(new) == len(blobs[i]) for i, new, _, _ in todo):
                for i, new, label, why in todo:
                    jobs.append(Job(file, h.entries[i][0], new, label, why))
                continue
            for i, new, label, why in todo:
                notes.append("note: %s %d -> %d bytes (%s)" % (label, len(blobs[i]), len(new), why))
                blobs[i] = new
            out = pac.build_binpac(cur[:h.header_size], blobs)
            why = "rebuilt, %d -> %d bytes" % (e.size, len(out))
            if sectors(len(out)) > sectors(e.size):
                moves.add(file, out, file, why)     # outgrew its sectors
                continue
            jobs.append(Job(file, 0, to_sector_end(out), file, why))
            if len(out) != e.size:
                toc.add(img, file, len(out))
        return jobs, notes


# --- skipping the tutorial (DOC/SQB_FORMAT.md) --------------------------------

SKIP_FLAG = (DISC + "SLES_541.51", 0x24e434)    # SLES 0x34d434, Dummy.CheckClubEditSkip's flag
# The nation the career starts in: Dummy.CheckClubEditSkip calls
# pwkLg_Init(league) at 0x108dc0 with 0 (England) set in its delay slot,
# 0x108dc4. --skip-nation writes addiu $a0, $zero, league there; the
# leagues run England 0, France 1, Germany 2, Italy 3, Spain 4, the
# Netherlands 5 (PLRRSRC_INITTEAMDATA table 0's order). The club must be
# created in a city of that nation.
SKIP_NATIONS = ("England", "France", "Germany", "Italy", "Spain", "Netherlands")
SKIP_NATION_AT = (DISC + "SLES_541.51", 0x9dc4)   # SLES 0x108dc4: move $a0, $zero
skip_nation = 0                                   # set by main from --skip-nation
# The skip runs the playoffs' own schedule steps without the playoff turns:
# RootClubEditSeq.sqb's playoff section (L2) becomes InitializeFirstCheck,
# YearStart, MonthStart, then Dummy.CheckClubEditSkip (pwkLg_Init(0) and
# ScheCallback_ProcPromotion, which Sche.FirstCheck runs for a won
# playoff), then Call L8: MonthEnd, YearEnd, Finalize, the won route. So the
# real Sche.YearEnd runs: the club rankings (ClubRank::UpdateYearEnd), the
# club's status (pwkTeam_YearEndCheck) and the rest. 0x868 stays the
# retail CheckFirstMatchSkip, which writes 0, so the script enters L2. The
# only jump to L3, in the playoff turn loop, now goes to L8 too, as L3's
# marker becomes the Call; that loop no longer runs. The script uses no
# other Call, so the one that never returns can't block another.
# (file, [(offset, accepted old commands, new "table:cmd", {arg: value})])
SKIP_SCRIPTS = (
    ("SEQ/ROOTCLUBEDITSEQ.SQB", [
        # 4:89 there is the earlier skip, which branched straight to L9.
        (0x868, ("Dummy.CheckFirstMatchSkip", "Dummy.CheckClubEditSkip"), "4:88", None),
        (0x8b0, ("TutorialHelp.Effective100",), "4:34", None),
        (0x8c0, ("Sche.InitializeFirstCheck",), "4:18", None),
        (0x8d0, ("Sche.YearStart",), "4:20", None),
        (0x8e0, ("Sche.MonthStart",), "4:89", None),
        (0x8f0, ("Label",), "0:5", {1: 8}),                # Call L8
        (0xba8, ("BranchIfZero",), "0:27", {2: 8}),        # its jump to L3 -> L8
    ]),
    # Year starts and club creation stay (4:88 writes 0 there).
    ("SEQ/ROOTMAINSEQ.SQB", [(0x6d8, ("Dummy.CheckClubEditSkip",), "4:88", None)]),
    ("SEQ/ROOTYEARSTARTSEQ.SQB", [(0x30, ("Dummy.CheckClubEditSkip",), "4:88", None)]),
)
# The earlier skip worked around the year start and year end it left out:
# it started the six playoff-period sponsors one year into their contracts
# (SLES 0x3994a8, byte +4 of each 0x14-byte record) and made
# Dummy.CheckClubEditSkip also call pwkTeam_YearEndCheck (9 words at SLES
# 0x108dac). With the real YearStart and YearEnd those would count twice,
# so an image patched by the earlier skip gets the retail bytes back.
OLD_SKIP_SPONSORS = (DISC + "SLES_541.51", 0x29a4a8)  # SLES 0x3994a8
OLD_SKIP_SPONSOR_COUNT, OLD_SKIP_SPONSOR_SIZE = 6, 0x14
OLD_SKIP_CODE = (DISC + "SLES_541.51", 0x9dac, bytes.fromhex(   # SLES 0x108dac: retail, earlier skip
    "34d4438c2d888000010002240f0062140000bfff8618090c2d200000724c040c00000000"),
    bytes.fromhex(
    "0000bfff2d8880008618090c2d200000724c040c00000000a8b8090c0000000000000000"))


def plan_skip_tutorial(f, img):
    """Jobs for --skip-tutorial, made from the files as the image holds
    them. A spot that already holds the patched value is left alone, and
    the earlier skip's workarounds are undone."""
    import sqb
    if img.kind != "disc image":
        raise ValueError("--skip-tutorial patches SLES_541.51 too, so it needs the whole "
                         "disc image, not %s" % img.kind)
    jobs, notes = [], []
    file, off = SKIP_FLAG
    word = struct.unpack("<I", read_at(f, img, file, off, 4))[0]
    if word == 0:
        jobs.append(Job(file, off, struct.pack("<I", 1), file + " (0x34d434)",
                        "--skip-tutorial: Dummy.CheckClubEditSkip flag 0 -> 1"))
    elif word == 1:
        notes.append("note: %s 0x34d434 already holds 1" % file)
    else:
        raise ValueError("%s 0x34d434 holds %d, not 0 or 1; not the retail executable?" % (file, word))
    for path, edits in SKIP_SCRIPTS:
        e = img.entry(path)
        data = read_at(f, img, e.path, 0, e.size)
        todo = []
        for offset, olds, spec, args in edits:
            held, held_args = sqb.command_at(data, offset)
            table, cmd = (int(x, 0) for x in spec.split(":"))
            want = sqb.SETS["root"][table][cmd][0]
            if held == want and all(held_args[i][1] == v for i, v in (args or {}).items()):
                continue
            if held not in olds:
                raise ValueError("%s 0x%x holds %s, expected %s" % (path, offset, held,
                                                                    " or ".join(olds)))
            todo.append((offset, spec, args))
        if not todo:
            notes.append("note: %s already holds the tutorial skip" % path)
            continue
        new, names = sqb.set_commands(data, todo)
        what = ", ".join("0x%x %s -> %s" % (o, a, b) for (o, _, _), (a, b) in zip(todo, names))
        for i, (a, b) in enumerate(zip(data, new)):
            if a != b:
                jobs.append(Job(e.path, i, new[i:i + 1], path, "--skip-tutorial: " + what))
    if img.port is not None:
        # The earlier skip, undone below, was only ever made for PAL.
        if skip_nation:
            raise ValueError("--skip-nation is made for the PAL executable only")
        notes.append("note: --skip-tutorial: start the career in England")
        return jobs, notes
    file, base = OLD_SKIP_SPONSORS
    for i in range(OLD_SKIP_SPONSOR_COUNT):
        off = base + i * OLD_SKIP_SPONSOR_SIZE
        rec = read_at(f, img, file, off, OLD_SKIP_SPONSOR_SIZE)
        if rec[4] == 1 and rec[6] in (0xff, 0xfe, 0xfc):
            jobs.append(Job(file, off + 4, b"\x00", "%s (0x%x)" % (file, 0x3994a8 + i * 0x14 + 4),
                            "--skip-tutorial: undo the earlier skip's sponsor %d offset" % i))
    file, off, retail, earlier = OLD_SKIP_CODE
    held = read_at(f, img, file, off, len(retail))
    nfile, noff = SKIP_NATION_AT
    k = noff - off
    word = struct.unpack_from("<I", held, k)[0]
    if word >> 16 == 0x2404 and word & 0xFFFF < len(SKIP_NATIONS):   # addiu $a0, $zero, n
        held = held[:k] + retail[k:k + 4] + held[k + 4:]
    nation = struct.pack("<I", 0x24040000 | skip_nation if skip_nation else 0x0000202D)
    if held in (retail, earlier) and word.to_bytes(4, "little") != nation:
        jobs.append(Job(nfile, noff, nation, "%s (0x108dc4)" % nfile,
                        "--skip-tutorial: pwkLg_Init(%d), %s" % (skip_nation,
                                                                 SKIP_NATIONS[skip_nation])))
    if held == earlier:
        jobs.append(Job(file, off, retail, "%s (0x108dac)" % file,
                        "--skip-tutorial: undo the earlier skip's pwkTeam_YearEndCheck call"))
    elif held != retail:
        raise ValueError("%s 0x108dac doesn't hold Dummy.CheckClubEditSkip's code; "
                         "not the retail executable?" % file)
    notes.append("note: --skip-tutorial: start the career in %s (create the club in "
                 "a city there)" % SKIP_NATIONS[skip_nation])
    return jobs, notes


# --- sponsor negotiation (DOC/SPONSOR_NEGOTIATION.md) -------------------------

# The Sponsor screen asks 0xc5ca0(this, sponsor id) whether the chosen main
# sponsor can be negotiated with (SIMPRG.REL 0xc6634). In PAL it is a stub
# returning 0, so the screen always goes to the contract question. The
# negotiation states behind it (0xb-0x16) are all still there, and each
# negotiation adds the sponsor to a 20-word list at this+0x12f0 (0xc5c58)
# that nothing else reads. The new check returns 1 unless the sponsor is in
# that list: one negotiation per sponsor per Sponsor screen. The stub
# branches to the unreferenced CStaffContractWindow method at 0xd3748 (24
# words, no relocation sites), which holds the loop. Branches only, since
# the overlay is relocated when it loads.
NEGO_FILE = DISC + "DLL/SIMPRG.REL"
NEGO_CODE = (
    (0xc5ca0, bytes.fromhex("0800e0032d100000"),        # jr $ra; move $v0, $zero
     bytes.fromhex("a9360010f0128324")),                 # b 0xd3748; addiu $v1, $a0, 0x12f0
    (0xd3748, bytes.fromhex(
        "d0ffbd272000b07f1000b17f881790240000bfff010011240000048e00000000ffff312604001026"),
     bytes.fromhex(
        "40138824"      # addiu $t0, $a0, 0x1340      end of the list
        "0000628c"      # lw    $v0, ($v1)
        "05004510"      # beq   $v0, $a1, 0xd3768     already negotiated
        "04006324"      # addiu $v1, $v1, 4
        "fcff6814"      # bne   $v1, $t0, 0xd374c
        "00000000"      # nop
        "0800e003"      # jr    $ra
        "01000224"      # addiu $v0, $zero, 1
        "0800e003"      # jr    $ra
        "2d100000")),   # move  $v0, $zero
)


def plan_sponsor_negotiation(f, img):
    """Jobs for --sponsor-negotiation. A spot that already holds the new
    code is left alone."""
    if img.kind != "disc image":
        raise ValueError("--sponsor-negotiation patches DLL/SIMPRG.REL, so it needs the whole "
                         "disc image, not %s" % img.kind)
    if img.port is not None:
        return [], ["note: --sponsor-negotiation: the Japanese release already negotiates "
                    "with the main sponsor (DOC/SPONSOR_NEGOTIATION.md)"]
    jobs, notes = [], []
    for off, old, new in NEGO_CODE:
        held = read_at(f, img, NEGO_FILE, off, len(old))
        if held == old:
            jobs.append(Job(NEGO_FILE, off, new, "%s (0x%x)" % (NEGO_FILE, off),
                            "--sponsor-negotiation: main sponsor negotiation check"))
        elif held == new:
            notes.append("note: %s 0x%x already holds the negotiation check" % (NEGO_FILE, off))
        else:
            raise ValueError("%s 0x%x doesn't hold the expected code; not the retail "
                             "overlay?" % (NEGO_FILE, off))
    return jobs, notes


# --- separate saves (DOC/SAVE_FORMAT.md#separate-saves-for-a-modded-disc) --------

# MC::CFcEuroIF::initialize (SLES 0x12ad38) names the memory-card folders
# from these strings: category 0 saved games (+ %03d), 1 VS data.
# --mod-saves changes the letter after the serial, so the serial, and
# with it PCSX2's GameDB entry (the D-pad clamp fix, memcardFilters, which
# match folders containing "SLES-54151"), stays. Category 2,
# BESLES-54153FASYS (Virtua Pro Football's save, read by the import), stays.
# Career saves take F on a disc without the difficulty groups (LMASTER
# full) and M on one with any of their switches (LMASTER max), since a
# career from one economy isn't one to load in the other; VS data takes V
# on both, as a VS team is the same either way (the user's choice,
# 2026-10-27; earlier builds used M and D).
SLES_FILE = DISC + "SLES_541.51"
SAVE_LETTERS = {"full": "F", "max": "M"}
VS_LETTER = "V"
save_letter = "F"                                   # set by cmd_patch from the switches


def mod_saves():
    """(retail name, modded name) of the career and VS folders."""
    return ((b"-G", b"-" + save_letter.encode()), (b"-C", b"-" + VS_LETTER.encode()))


MOD_SAVES = (0x4223e8, 0x4223f8)                    # SLES 0x5213e8 (-G), 0x5213f8 (-C)
SAVE_PREFIX, SAVE_PREFIX_JP = b"BESLES-54151", b"BISLPM-66316"
# The Japanese build's folders, BISLPM-66316-G and -C, are found by name:
# the strings differ, so gamever.py can't place them.
RETAIL_CRC = 0x3cb245d5


def pcsx2_crc(data):
    """PCSX2's CRC of an executable: the XOR of its 32-bit words (it names
    settings and savestates SLES-54151_3CB245D5 for the retail one)."""
    crc = 0
    for (w,) in struct.iter_unpack("<I", data[:len(data) // 4 * 4]):
        crc ^= w
    return crc


def plan_mod_saves(f, img):
    """Jobs for --mod-saves. A name already changed is left alone."""
    if img.kind != "disc image":
        raise ValueError("--mod-saves patches SLES_541.51, so it needs the whole disc image, "
                         "not %s" % img.kind)
    jobs, notes = [], []
    if img.port is not None:
        e = img.entry(JP_EXE_FILE)
        data = read_raw(f, img, JP_EXE_FILE, 0, e.size)
        for old, new in mod_saves():
            old, new = SAVE_PREFIX_JP + old, SAVE_PREFIX_JP + new
            if data.count(new + b"\0") == 1 and old + b"\0" not in data:
                notes.append("note: %s already names %s" % (JP_EXE_FILE, new.decode()))
                continue
            if data.count(old + b"\0") != 1:
                raise ValueError("%s doesn't hold %s once; not the retail executable?"
                                 % (JP_EXE_FILE, old.decode()))
            off = data.index(old + b"\0")
            jobs.append(Job(JP_EXE_FILE, off, new, "%s (0x%x)" % (JP_EXE_FILE, off),
                            "--mod-saves: memory-card folder %s -> %s" % (
                                old.decode(), new.decode())))
        return jobs, notes
    for off, (old, new) in zip(MOD_SAVES, mod_saves()):
        old, new = SAVE_PREFIX + old, SAVE_PREFIX + new
        held = read_at(f, img, SLES_FILE, off, len(old) + 1)
        if held == old + b"\0":
            jobs.append(Job(SLES_FILE, off, new, "%s (0x%x)" % (SLES_FILE, off + 0xff000),
                            "--mod-saves: memory-card folder %s -> %s" % (
                                old.decode(), new.decode())))
        elif held == new + b"\0":
            notes.append("note: %s already names %s" % (SLES_FILE, new.decode()))
        else:
            raise ValueError("%s 0x%x doesn't hold %s; not the retail executable?"
                             % (SLES_FILE, off, old.decode()))
    return jobs, notes


# --- the rival's manager (DOC/TEAMINIT_FORMAT.md, the table 6 quirk) -----------

# pwkTeam_Init2's loop at 0x25e6d0 walks TEAM_INIT_DATA table 6 with $v1 at
# each record's style (+4) and, on the record matching the rival's style,
# loads the manager in the beql delay slot from $a0, the table's start: so
# every rival gets record 0's manager. Loading 4($v1) reads the matching
# record's +8. The rival's style is already the opposite of the club's
# (0x5531e0), so its manager follows it.
RIVAL_MANAGER = (0x15f6d8,                       # SLES 0x25e6d8
                 bytes.fromhex("0800938c"),      # lw $s3, 8($a0)
                 bytes.fromhex("0400738c"))      # lw $s3, 4($v1)


def plan_rival_manager(f, img):
    """Jobs for --mod rival-manager."""
    if img.kind != "disc image":
        raise ValueError("rival-manager patches SLES_541.51, so it needs the whole disc "
                         "image, not %s" % img.kind)
    off, old, new = RIVAL_MANAGER
    held = read_at(f, img, SLES_FILE, off, len(old))
    if held == new:
        return [], ["note: %s 0x%x already reads the rival's own manager"
                    % (SLES_FILE, off + 0xff000)]
    if held != old:
        raise ValueError("%s 0x%x doesn't hold the expected code; not the retail executable?"
                         % (SLES_FILE, off + 0xff000))
    return [Job(SLES_FILE, off, new, "%s (0x%x)" % (SLES_FILE, off + 0xff000),
                "rival-manager: the rival's manager by its style")], []


# --- the national cups a turn earlier (DOC/LMASTER_MOD.md) ---------------------

# The World National Cup's knockout (UID 122) plays turns 92-95, and 95 is
# the last turn of the year: the season ends on the turn of the final, and
# its results can't be viewed in the Competition menu (user report).
# Its groups (114-121) and the Euro National Cup's (98-101, knockout 102)
# move back with it: groups 88-90, knockouts 91-94 and 91-93. The game
# loads the system pack from PRELOAD/STATIONFILE.PAC as well, so both are
# written.
NATIONAL_UIDS = list(range(98, 103)) + list(range(114, 123))
SCHEDULE_FILE = "PARAM/SCHEDULE_SYSTEM.PAC"
STATION_FILE, STATION_ENTRY = "PRELOAD/STATIONFILE.PAC", "schedule_system.pac"


def diff_jobs(file, base, old, new, why, gap=0x20):
    """One Job per stretch of differing bytes between old and new; changes
    less than `gap` bytes apart share one."""
    diff = [i for i in range(len(old)) if old[i] != new[i]]
    jobs = []
    while diff:
        i = j = diff.pop(0)
        while diff and diff[0] - j < gap:
            j = diff.pop(0)
        jobs.append(Job(file, base + i, new[i:j + 1], "%s 0x%x" % (file, base + i), why))
    return jobs


# The national-team calendar moves with them. SCHEDULE_LIST.TBB has one
# table per year of the 4-year cycle, picked by (year - 2006) mod 4
# (0x256a50), and one byte of flags per turn: 1 national match, 2 finals
# tournament, 4 call-up, 8 release (pwkSche_IsNationalMatch/FMatch/
# Convene/Break, 0x256b30-0x256c50). SIMPRG.REL's jmNT_CallCheck
# (0x160b68) calls the squads up on a call-up turn, and jmNT_FreeCheck
# (0x160c50) releases them, and in a tournament year asks for the champion.
# Tables 1 (Euro) and 3 (World Cup) call up on 88 and play 89-94/95. The
# matches and the release move back a turn; the call-up stays on 88 and
# shares it with the first group game, as in the qualifying years, since
# turn 87 has the play-off finals of England, Italy, the Netherlands and
# Spain. The game reads the PRELOAD/SIMLOCALMEM0-6.PAC copies too.
LIST_FILE, LIST_ENTRY = "PARAM/SCHEDULE_LIST.TBB", "Schedule_list.tbb"
LIST_PACKS = ["PRELOAD/SIMLOCALMEM%d.PAC" % i for i in range(7)]
LIST_TABLES = (1, 3)                    # Euro and World Cup years
LIST_MATCH, LIST_FINALS, LIST_CALL, LIST_FREE = 1, 2, 4, 8
LIST_CALL_TURN = 88


def shift_list(data, strict=True):
    """SCHEDULE_LIST.TBB with the tournament years' matches and release a
    turn earlier; None when it already has them (a match on turn 88).
    `strict` refuses a table that isn't the retail one; a target's calendar,
    which may have been edited (natcal.py), is moved as it is."""
    import tbb
    _, tables = tbb.parse(data)
    new = bytearray(data)
    for k in LIST_TABLES:
        t = tables[k]
        b = t.data
        if len(b) != 0x60:
            raise ValueError("%s table %d: %d bytes, expected 96" % (LIST_FILE, k, len(b)))
        if b[LIST_CALL_TURN] & LIST_MATCH:
            return None
        if strict and (b[LIST_CALL_TURN] != LIST_FINALS | LIST_CALL
                       or not b[0x5f - (k == 1)] & LIST_FREE):
            raise ValueError("%s table %d: turn 88 is 0x%x; not the retail table?"
                             % (LIST_FILE, k, b[LIST_CALL_TURN]))
        moved = bytearray(b[:LIST_CALL_TURN]) + b[LIST_CALL_TURN + 1:] + b"\0"
        moved[LIST_CALL_TURN] |= b[LIST_CALL_TURN]
        start = t.offset + t.data_offset
        new[start:start + 0x60] = moved
    return bytes(new)


def shift_cups(data):
    """SCHEDULE_SYSTEM.PAC with the national cups a turn earlier; None when
    it already has them. Leagues never reach the cups' turns (a rebuilt
    league keeps its first and last game day, schedule.league_turns), so
    a pack from leaguesize.py build takes the move as the retail one does."""
    import pac
    import schedule
    h, blobs = pac.binpac_blobs(data)
    rows = schedule.year_uids(schedule.System(
        [(x[2], b) for x, b in zip(h.entries, blobs)]).year)
    first = rows[122][0].turns[0]
    if first == 91:
        return None
    if first != 92:
        raise ValueError("%s: UID 122 starts on turn %d, expected 92; not the retail pack?"
                         % (SCHEDULE_FILE, first))
    return schedule.shift_pack(data, NATIONAL_UIDS, -1)


def target_national_cups(file, data):
    """A target's new bytes with the national cups moved: a SCHEDULE_SYSTEM.PAC
    written as a target (a league of another size) gets the move itself, and
    its --copies carry it to PRELOAD/STATIONFILE.PAC; so does a
    SCHEDULE_LIST.TBB (an edited national-team calendar), whose --copies go
    to PRELOAD/SIMLOCALMEM0-6.PAC."""
    if norm(file) == norm(SCHEDULE_FILE):
        new = shift_cups(data)
    elif norm(file) == norm(LIST_FILE):
        new = shift_list(data, strict=False)
    else:
        return data
    return data if new is None else new


def plan_national_cups(f, img, adopted=()):
    """Jobs for --mod national-cups. A file already moved is left alone, and
    so is SCHEDULE_SYSTEM.PAC when a target writes it (`adopted`)."""
    why = "national-cups: World and Euro National Cups a turn earlier"
    jobs, notes = [], []
    e = img.entry(SCHEDULE_FILE)
    data = read_at(f, img, e.path, 0, e.size)
    new = None if norm(SCHEDULE_FILE) in adopted else shift_cups(data)
    if norm(SCHEDULE_FILE) in adopted:
        notes.append("note: national-cups: moved the cups in the target's %s" % SCHEDULE_FILE)
    elif new is None:
        notes.append("note: %s already has the national cups a turn earlier" % SCHEDULE_FILE)
    else:
        jobs += diff_jobs(e.path, 0, data, new, why)
        jobs += pack_copy_jobs(f, img, STATION_FILE, STATION_ENTRY, SCHEDULE_FILE, data, new, why)
    e = img.entry(LIST_FILE)
    data = read_at(f, img, e.path, 0, e.size)
    new = None if norm(LIST_FILE) in adopted else shift_list(data)
    if norm(LIST_FILE) in adopted:
        notes.append("note: national-cups: moved the national-team dates in the target's %s"
                     % LIST_FILE)
    elif new is None:
        notes.append("note: %s already has the national-team dates a turn earlier" % LIST_FILE)
    else:
        jobs += diff_jobs(e.path, 0, data, new, why)
        for p in LIST_PACKS:
            jobs += pack_copy_jobs(f, img, p, LIST_ENTRY, LIST_FILE, data, new, why)
    return jobs, notes


# --- the league schedules (DOC/SCHEDULE_FORMAT.md#writing) ---------------------

# league-balance rebuilds the league templates that send a club to one
# venue up to 9 times running (schedule.balance_pack). Each entry keeps
# its size, so SCHEDULE_COMPETITION.HED and its STATIONFILE copy stay as
# they are, and the game reads the entries from the pack itself.
COMPE_FILE = "PARAM/SCHEDULE_COMPETITION.PAC"


def target_league_balance(file, data):
    """A SCHEDULE_COMPETITION.PAC target (leaguesize.py build) with its
    leagues balanced; the ones the build rebuilt already are."""
    import schedule
    if norm(file) != norm(COMPE_FILE):
        return data
    return schedule.balance_pack(data)[0]


def plan_league_balance(f, img, adopted=()):
    """Jobs for --mod league-balance. A pack already balanced is left alone,
    and so is one a target writes (`adopted`, balanced by
    target_league_balance)."""
    import schedule
    if norm(COMPE_FILE) in adopted:
        return [], ["note: league-balance: rebuilt the leagues in the target's %s"
                    % COMPE_FILE]
    path, data = read_file(f, img, COMPE_FILE)
    new, done = schedule.balance_pack(data)
    if not done:
        return [], ["note: %s already has its leagues balanced" % COMPE_FILE]
    return diff_jobs(path, 0, data, new, "league-balance: no more than two games running "
                     "at one venue (UIDs %s)" % " ".join(map(str, done))), []


def pack_copy_jobs(f, img, pack, entry, of, old, new, why, gap=0x20):
    """diff_jobs for the copy of `of` stored as `entry` in BINPAC `pack`."""
    import pac
    s = img.entry(pack)
    sh, sblobs = pac.binpac_blobs(read_at(f, img, s.path, 0, s.size))
    i = pac.find_entry(sh, entry)
    if sblobs[i] != old:
        raise ValueError("%s#%s isn't a copy of %s" % (pack, entry, of))
    return diff_jobs(s.path, sh.entries[i][0], old, new, why, gap)


# --- archive indexes held by the executable (DOC/REBUILD.md#archives) ----------

MES_FILE = "MESSAGE/MES.PAC"
ACROBATA_FILE = "ACROBATA/ACROBATAPACKFILE.PAC"

# Archives the game reads through a copy of their header in the executable,
# not through the header: file -> (where, the byte ranges of a record that
# identify it, whether the game reads the sizes as they are).
# MES.PAC: CFcEuro_MsgResource::Execute (SLES 0x10f4b0) walks
# {offset, size, category, language} at 0x34df50 and reads (size >> 11) + 1
# sectors, so the old sizes still cover a file grown inside its slot.
# AcrobataPackFile.pac: LOADER reads {offset, size, ABDA size, ABRS size}
# at 0x3a3b08 (0x2fb050-0x2fb0b8) and opens exactly that byte range.
EXE_INDEXED = {
    MES_FILE: ("SLES 0x34df50", ((0, 4), (8, 16)), False),
    ACROBATA_FILE: ("SLES 0x3a3b08", ((0, 4),), True),
}


def pack_index(data):
    """An archive's header rows as the executable copies them: {u32 offset,
    u32 size, u32 extra columns...} per entry, in header order (equal to
    the copies at 0x34df50 and 0x3a3b08 for all entries, empirical, PAL
    and Japanese)."""
    import pac
    h = pac.BinPac(data)
    return b"".join(struct.pack("<II%dI" % len(x), o, n, *x) for o, n, _, x in h.entries)


def find_index(exe, records, stride, keys):
    """Where the executable holds an index: the one place whose records
    agree with `records` on the `keys` byte ranges (offsets, and for
    MES.PAC category and language). Sizes may differ (an image patched
    before the index was kept in step). None unless there is exactly one."""
    n = len(records) // stride
    hits = []
    i = exe.find(records[0:4])
    while i >= 0:
        if i + len(records) <= len(exe) and all(
                exe[i + stride * k + a:i + stride * k + b] ==
                records[stride * k + a:stride * k + b]
                for k in range(n) for a, b in keys):
            hits.append(i)
        i = exe.find(records[0:4], i + 1)
    return hits[0] if len(hits) == 1 else None


def plan_exe_index(f, img, file, new_data):
    """Jobs that bring the executable's copy of an archive's index
    (EXE_INDEXED) to the archive's new header. The table is found by the
    records of the archive now on the disc, so this works on either build
    and a second run finds nothing to do. On DATA.CVM or DATA.ISO alone,
    where the executable isn't, a change the game needs is refused."""
    where, keys, sizes = EXE_INDEXED[norm(file)]
    e = img.entry(file)
    import pac
    stride = 8 + 4 * len(pac.BinPac(new_data).entries[0][3])
    old = pack_index(read_at(f, img, e.path, 0, e.size))
    new = pack_index(new_data)
    if old == new:
        return [], []
    if len(old) != len(new):
        raise SystemExit("%s: %d entries, the disc's has %d; the executable's index (%s) "
                         "can't change length" % (file, len(new) // stride, len(old) // stride,
                                                  where))
    needed = sizes or any(old[i:i + 4] != new[i:i + 4] for i in range(0, len(old), stride))
    if img.kind != "disc image":
        if needed:
            raise SystemExit("%s: entries moved or changed size, so the executable's copy of "
                             "its index (%s) has to change too; patch the whole disc image"
                             % (file, where))
        return [], ["note: %s: grown files keep their places; the executable's index keeps "
                    "the old sizes, which the game reads whole sectors of" % file]
    s = img.entry(SLES_FILE)
    exe = read_at(f, img, s.path, 0, s.size)
    at = find_index(exe, old, stride, keys)
    if at is None:
        raise SystemExit("can't find the executable's copy of %s's index (%s; its offsets "
                         "should equal the disc's archive header)" % (file, where))
    held = exe[at:at + len(new)]
    if held == new:
        return [], []
    return diff_jobs(s.path, at, held, new, "%s's index in the executable" % file, gap=1), []


# --- training camps (DOC/CAMP_FORMAT.md) -------------------------------------------

CAMP_LIST_FILE = "PARAM/CAMP_LIST.TBB"
CAMP_EXPLANE_FILE = "PARAM/CAMP_EXPLANE.TBB"


def read_file(f, img, file):
    e = img.entry(file)
    return e.path, read_at(f, img, e.path, 0, e.size)


def target_camp_types(file, data):
    """A CAMP_LIST.TBB target (the editor's Camps tab) with the camp-types
    fix applied to its own bytes."""
    import camp
    if norm(file) != norm(CAMP_LIST_FILE):
        return data
    return camp.fix_types(data) or data


def target_camp_cities(file, data):
    """A CAMP_LIST.TBB or CAMP_EXPLANE.TBB target with the camp-cities fix
    applied to its own bytes."""
    import camp
    fix = {norm(CAMP_LIST_FILE): camp.fix_cities_list,
           norm(CAMP_EXPLANE_FILE): camp.fix_cities_explane}.get(norm(file))
    return data if fix is None else (fix(data) or data)


def plan_camp_types(f, img, adopted=()):
    """Jobs for --mod camp-types: CAMP_LIST's camp types lowered by one,
    so each camp gets its own row of TRAINING_LIST table 10 and of the
    theme table at SLES 0x552cd0. A file already fixed is left alone, and
    so is one a target writes (`adopted`, fixed by target_camp_types)."""
    import camp
    if norm(CAMP_LIST_FILE) in adopted:
        return [], ["note: camp-types: fixed the types in the target's %s" % CAMP_LIST_FILE]
    path, data = read_file(f, img, CAMP_LIST_FILE)
    new = camp.fix_types(data)
    if new is None:
        return [], ["note: %s already has its camp types from 0" % CAMP_LIST_FILE]
    # gap=1: only the type bytes, so camp-cities' jobs in the same table
    # don't overlap these (each plan sees the original file).
    return diff_jobs(path, 0, data, new, "camp-types: each camp trains as its own type",
                     gap=1), []


def plan_camp_cities(f, img, adopted=()):
    """Jobs for --mod camp-cities: the seven English camps PAL left on the
    Japanese city ids moved to their PAL ids, in CAMP_LIST and CAMP_EXPLANE.
    A file a target writes (`adopted`) was fixed by target_camp_cities."""
    import camp
    why = "camp-cities: the English camps in their own towns"
    jobs, notes = [], []
    for file, fix in ((CAMP_LIST_FILE, camp.fix_cities_list),
                      (CAMP_EXPLANE_FILE, camp.fix_cities_explane)):
        if norm(file) in adopted:
            notes.append("note: camp-cities: moved the cities in the target's %s" % file)
            continue
        path, data = read_file(f, img, file)
        new = fix(data)
        if new is None:
            notes.append("note: %s has no camp on an old city id" % file)
        else:
            jobs += diff_jobs(path, 0, data, new, why, gap=1)
    return jobs, notes


def target_camp_santiago(file, data):
    """A CAMP_EXPLANE.TBB target with Santiago's description fixed."""
    import camp
    if norm(file) != norm(CAMP_EXPLANE_FILE):
        return data
    return camp.fix_santiago(data) or data


def plan_camp_santiago(f, img, adopted=()):
    """Jobs for --mod camp-santiago: Santiago's description (CAMP_EXPLANE,
    keyed to city 764) moved to its camp's city, 774."""
    import camp
    if norm(CAMP_EXPLANE_FILE) in adopted:
        return [], ["note: camp-santiago: fixed the target's %s" % CAMP_EXPLANE_FILE]
    path, data = read_file(f, img, CAMP_EXPLANE_FILE)
    new = camp.fix_santiago(data)
    if new is None:
        return [], ["note: %s already has Santiago's description on its camp"
                    % CAMP_EXPLANE_FILE]
    return diff_jobs(path, 0, data, new, "camp-santiago: Santiago's camp description",
                     gap=1), []


# The camp screen's list of a camp city's clubs (SIMPRG.REL 0x4c8f8) walks
# CAMP_LIST table 1 with a count from 0x2de down to 0: 735 of its 737
# pairs, so Canberra's last two clubs never appear (both releases).
CAMP_CLUBS = (NEGO_FILE, 0x4c9d4, bytes.fromhex("de020424"),   # addiu $a0, $zero, 0x2de
              bytes.fromhex("e0020424"))                       # addiu $a0, $zero, 0x2e0


def plan_camp_clubs(f, img):
    """Jobs for --mod camp-clubs: the clubs list reads all 737 pairs."""
    file, off, old, new = CAMP_CLUBS
    if img.kind != "disc image":
        raise ValueError("--mod camp-clubs patches DLL/SIMPRG.REL, so it needs the whole "
                         "disc image, not %s" % img.kind)
    held = read_at(f, img, file, off, len(old))
    if held == new:
        return [], ["note: %s 0x%x already reads every camp club pair" % (file, off)]
    if held != old:
        raise ValueError("%s 0x%x doesn't hold the expected code; not the retail overlay?"
                         % (file, off))
    return [Job(file, off, new, "%s (0x%x)" % (file, off),
                "camp-clubs: read all 737 camp club pairs")], []


# --- the PAL drill names (DOC/TRAINING_FORMAT.md) ----------------------------------

# Practice names are category 801 of MES.PAC (training.fix_drill_names).
# Language slot n is also entry 28 of PRELOAD/SIMFILEn.PAC, which season
# mode loads (SIMPRG list 0x214448).
DRILL_LANGS = (1, 2, 3, 4, 5, 6)
DRILL_PACKS = ["PRELOAD/SIMFILE%d.PAC" % n for n in DRILL_LANGS]


def mes_entries(data):
    """{name: (offset, size)} of MES.PAC's header in `data` (the header, or
    the whole archive)."""
    import pac
    h = pac.BinPac(data[:struct.unpack_from("<I", data)[0]])
    return {name.lower(): (off, size) for off, size, name, _ in h.entries}


def target_drill_names(file, data):
    """A MES.PAC target with the drill names fixed in its own 801 files."""
    import training
    if norm(file) != norm(MES_FILE):
        return data
    out = bytearray(data)
    for name, (off, size) in mes_entries(data).items():
        if name in {"%d_%d.mbb" % (training.NAME_CATEGORY, n) for n in DRILL_LANGS}:
            new = training.fix_drill_names(data[off:off + size])
            if new is not None:
                out[off:off + size] = new
    return bytes(out)


def plan_drill_names(f, img, adopted=()):
    """Jobs for --mod drill-names: the European names of drills 75-86 moved
    one message later, in MES.PAC and the SIMFILE copies. A MES.PAC a
    target writes (`adopted`) was fixed by target_drill_names, and its
    --copies carry that to the SIMFILE packs."""
    import training
    if norm(MES_FILE) in adopted:
        return [], ["note: drill-names: fixed the names in the target's %s" % MES_FILE]
    why = "drill-names: each drill 75-86 shows its own name"
    jobs, notes = [], []
    e = img.entry(MES_FILE)
    entries = mes_entries(read_at(f, img, e.path, 0, struct.unpack_from(
        "<I", read_at(f, img, e.path, 0, 4))[0]))
    for n, pack in zip(DRILL_LANGS, DRILL_PACKS):
        name = "%d_%d.mbb" % (training.NAME_CATEGORY, n)
        off, size = entries[name]
        data = read_at(f, img, e.path, off, size)
        new = training.fix_drill_names(data)
        if new is None:
            notes.append("note: %s#%s already has the drill names in the Japanese numbering"
                         % (MES_FILE, name))
            continue
        jobs += diff_jobs(e.path, off, data, new, why)
        jobs += pack_copy_jobs(f, img, pack, name, "%s#%s" % (MES_FILE, name), data, new, why)
    return jobs, notes


# --- the developer launcher (DOC/SQB_FORMAT.md#the-developer-launcher) --------

# RootMainSeq.sqb runs Dummy.CheckLauncher (always 1) at 0x88 and at 0x98
# branches past RootLauncherSeq.sqb when the value is non-zero. Turning the
# branch into BranchIfZero (command 0:27, 1 byte) boots into the launcher.
LAUNCHER = ("SEQ/ROOTMAINSEQ.SQB", 0x98, "BranchIfNotZero", "0:27")


def plan_launcher(f, img):
    """Jobs for --launcher. A script that already holds the new command is
    left alone."""
    import sqb
    path, offset, old, spec = LAUNCHER
    e = img.entry(path)
    data = read_at(f, img, e.path, 0, e.size)
    new, held, name = sqb.set_command(data, offset, spec)
    if held == name:
        return [], ["note: %s 0x%x already holds %s" % (path, offset, name)]
    if held != old:
        raise ValueError("%s 0x%x holds %s, expected %s" % (path, offset, held, old))
    return [Job(e.path, i, new[i:i + 1], "%s 0x%x" % (path, offset),
                "--launcher: %s -> %s, boot into the developer launcher" % (held, name))
            for i, (a, b) in enumerate(zip(data, new)) if a != b], []


# --- the kind-6 injury value (DOC/INJURIES.md#the-value-table-0x532cf8) ----------

# calcKegav (SLES 0x21a120) gives an injury of kind k a value of
# min + random(max - min + 1) from one of the kind's (min, max) pairs in the
# u16 table at 0x532cf8 (0x14 bytes a kind). Every kind starts where the one
# before ends, except kind 6, whose first pair is 1600-19000 where
# 16001-19000 fits (a dropped digit, in both releases): so a kind-6 injury,
# shown as 18 months, could be as short as a light one.
INJURY_VALUE = (0x532d70, 1600, 16001)


def plan_injury_value(f, img):
    """Jobs for --mod injury-value."""
    addr, old, new = INJURY_VALUE
    words = [(SLES_FILE, addr - 0xff000, struct.pack("<H", old), struct.pack("<H", new),
              "%s 0x%x (kind-6 injury value %d -> %d)" % (SLES_FILE, addr, old, new))]
    return word_jobs(f, img, "injury-value", words)


# judgeKegaKind (SLES 0x21a068) picks an injury's kind from a row of the
# match (0x532c90) or practice (0x532c28) table, row = (fatigue + 50 at
# ages 30-34, + 100 at 35 and over) / 100. Fatigue tops out at 1000, so an
# older player at full fatigue gets row 11 of tables with 11 rows (0-10)
# and reads the bytes after them. The fix clamps the row to 10 in the same
# words: the divide-by-zero trap after the div can't fire (the divisor is
# 100), and the compare of the practice number with -1 becomes bltz (the
# match passes -1, practices 0 and up), which frees $v1's -1.
INJURY_ROW_AT = 0x21a08c
INJURY_ROW_OLD = (0x2403ffff,       # addiu $v1, $zero, -1
                  0x00a2001a,       # div   $a1, $v0
                  0x50400001,       # beql  $v0, $zero, +1 (divide-by-zero trap)
                  0x000001cd,       # break 7
                  0x00002812,       # mflo  $a1
                  0x10c30005)       # beq   $a2, $v1, 0x21a0b8
INJURY_ROW_NEW = (0x00a2001a,       # div   $a1, $v0
                  0x2402000a,       # addiu $v0, $zero, 10
                  0x00002812,       # mflo  $a1             row
                  0x28a1000b,       # slti  $at, $a1, 11
                  0x0041280a,       # movz  $a1, $v0, $at   row 11 -> 10
                  0x04c00005)       # bltz  $a2, 0x21a0b8   the match table


def plan_injury_row(f, img):
    """Jobs for --mod injury-row."""
    words = [(SLES_FILE, INJURY_ROW_AT - 0xff000,
              struct.pack("<6I", *INJURY_ROW_OLD), struct.pack("<6I", *INJURY_ROW_NEW),
              "%s 0x%x (injury kind row clamped to 10)" % (SLES_FILE, INJURY_ROW_AT))]
    return word_jobs(f, img, "injury-row", words)


# --- Virtua Pro Football play styles (DOC/PMPLAYER_FORMAT.md#the-record) --------

# The edit-player import (SAVEPRG.REL 0x3df10) sorts pointers to the 22
# play-style ratings with _plUty_qsort and keeps the first five rated 70 or
# more, but its compare (0x3df00) returns the difference of the two
# pointers, not of the ratings, so nothing moves. The fixed compare loads
# both ratings and returns b - a (best first), using the tail of the
# executable's strcmp (SLES 0x31a5b4: lbu $v0,0($a1); jr $ra; subu
# $v0,$v1,$v0), which the overlay reaches with an absolute j (the
# executable doesn't move; no relocation covers these 4 words).
#
# Rating n becomes game style n, and style 0 is "none": with the sort
# working, a high rating in byte +0xb9 would take a slot as an empty one,
# leaving a gap before the real styles. So the copy that is sorted gets 0
# for that rating (0x3dfe0, sb $s6 -> sb $zero; $s6 holds nothing else),
# and "none" sorts last and stays under 70.
SAVE_FILE = DISC + "DLL/SAVEPRG.REL"
VPF_STYLES = (
    (0x3df00, "play-style compare",
     (0x8c830000, 0x8ca20000, 0x03e00008, 0x00621023),   # lw;lw;jr $ra;subu (pointers)
     (0x8ca20000,                                         # lw  $v0, 0($a1)  pointer b
      0x8c850000,                                         # lw  $a1, 0($a0)  pointer a
      0x080c696d,                                         # j   0x31a5b4
      0x90430000)),                                       # lbu $v1, 0($v0)  rating b
    (0x3dfe0, "style 0 (none) rated 0",
     (0xa3b60000,),                                       # sb $s6, 0($sp)
     (0xa3a00000,)),                                      # sb $zero, 0($sp)
)


def plan_vpf_styles(f, img):
    """Jobs for --mod vpf-styles."""
    words = [(SAVE_FILE, off, struct.pack("<%dI" % len(old), *old),
              struct.pack("<%dI" % len(new), *new), "%s 0x%x (%s)" % (SAVE_FILE, off, what))
             for off, what, old, new in VPF_STYLES]
    return word_jobs(f, img, "vpf-styles", words)


# --- the press tendency's team cap (DOC/PBDATA_FORMAT.md#the-tendencies) -------

# The press readers (GAMEPRG.REL 0x9a418, 0x9a4c8) clamp a player's press
# tendency to 0..cap, the cap from byte 0 of the side's record at match
# data +0x9764: 1 caps at 0, 2 at 1, more at 4. In a career match the
# record keeps its constructor's 2 (0x74320; read over PINE), so levels
# 2-4 acted as 1. Each reader picks the cap 1 for a 2 with one movz,
# right after setting 4; a nop there leaves 4.
GAME_FILE = DISC + "DLL/GAMEPRG.REL"
PRESS_READERS = ((0x9a474, bytes.fromhex("0a80a200")),    # movz $s0, $a1, $v0
                 (0x9a52c, bytes.fromhex("0a80e200")))    # movz $s0, $a3, $v0
PRESS_NOP = bytes(4)


def plan_press_tendency(f, img):
    """Jobs for --mod press-tendency."""
    return word_jobs(f, img, "press-tendency",
                     [(GAME_FILE, off, old, PRESS_NOP,
                       "%s 0x%x (press reader: cap 4 kept)" % (GAME_FILE, off))
                      for off, old in PRESS_READERS])


# --- the season-ticket status factor (DOC/ECONOMY.md#season-tickets) -----------

# pwkUnkei_GetExpectSeat (SLES 0x2727c8) scales season-ticket demand by
# club status in bands of 10,000: 0.5, 0.6, 0.7, 0.8, 0.9 and 1.0 above
# 50,000. Its tests (0x272840-0x2728d8) take the first band for every status
# over 10,000, so no club gets more than 0.6. The fix rewrites the ladder
# as a straight run: load each band's value, keep it while the status is
# below the band's top (sltiu, or ori and sltu past 0x7fff), then
# mtc1 $at, $f20 and on to 0x2728dc with $v0 = 0x10000, as before. The last
# 8 words of the old ladder become unreachable and stay.
SEASON_STATUS_OLD = (
    0x3c013f00, 0x4481a000, 0x0040182d, 0x28622711, 0x14400006, 0x28624e21, 0x3c013f19,
    0x3421999a, 0x4481a000, 0x1000001d, 0x3c020001, 0x14400006, 0x28627531, 0x3c013f33,
    0x34213333, 0x4481a000, 0x10000016, 0x3c020001, 0x14400006, 0x34029c40, 0x3c013f4c,
    0x3421cccd, 0x4481a000, 0x1000000f, 0x3c020001, 0x0043102a, 0x10400006, 0x3c020001,
    0x3c013f66, 0x34216666, 0x4481a000)
SEASON_STATUS_NEW = (
    0x0040182d,                                         # move $v1, $v0 (the status)
    0x3c013f00,                                         # $at = 0.5
    0x2c622711, 0x14400018, 0x00000000,                 # < 10,001: keep
    0x3c013f19, 0x3421999a,                             # 0.6
    0x2c624e21, 0x14400013, 0x00000000,                 # < 20,001
    0x3c013f33, 0x34213333,                             # 0.7
    0x2c627531, 0x1440000e, 0x00000000,                 # < 30,001
    0x3c013f4c, 0x3421cccd,                             # 0.8
    0x34029c41, 0x0062102b, 0x14400008, 0x00000000,     # < 40,001
    0x3c013f66, 0x34216666,                             # 0.9
    0x3402c351, 0x0062102b, 0x14400002, 0x00000000,     # < 50,001
    0x3c013f80,                                         # 1.0
    0x4481a000,                                         # mtc1 $at, $f20
    0x10000009, 0x3c020001)                             # b 0x2728dc; lui $v0, 1
SEASON_STATUS_AT = 0x272840


def plan_season_status(f, img):
    """Jobs for --mod season-status."""
    words = [(SLES_FILE, SEASON_STATUS_AT - 0xff000,
              struct.pack("<%dI" % len(SEASON_STATUS_OLD), *SEASON_STATUS_OLD),
              struct.pack("<%dI" % len(SEASON_STATUS_NEW), *SEASON_STATUS_NEW),
              "%s 0x%x (season-ticket status ladder)" % (SLES_FILE, SEASON_STATUS_AT))]
    return word_jobs(f, img, "season-status", words)


# --- the PR events' business cycle (DOC/ECONOMY.md#pr-events) -----------------

# plClubEvent_Execute (SLES 0x20df50) succeeds when rand(100) <= the event's
# chance: byte 0 of its 8-byte record at 0x530518, plus a business-cycle
# byte. The bytes are +20, +10, -5, -10 for cycles 0, 1, 3 and 4 (0 the
# boom), and nothing for 2, but the ladder (0x20dfb0-0x20e014) takes byte 2
# for cycles 0-1, byte 4 for 2 and byte 3 for 3-4: byte 1 is never read,
# and an average economy gets -10. The fix reads byte K + 1 below cycle 2
# and byte K above it, and skips cycle 2, in the ladder's first 11 words.
PR_CYCLE_AT = 0x20dfb0
PR_CYCLE_OLD = (0x0c09c638, 0x00000000, 0x28420002, 0x10400003, 0x02511821, 0x10000014,
                0x90620002, 0x0c09c638, 0x00000000, 0x28420003, 0x14400003)
PR_CYCLE_NEW = (0x0c09c638,         # jal   pwkTown_Keiki       $v0 = K, 0-4
                0x00000000,         # nop
                0x02511821,         # addu  $v1, $s2, $s1       the event's record
                0x00621821,         # addu  $v1, $v1, $v0       + K
                0x28410002,         # slti  $at, $v0, 2
                0x00611821,         # addu  $v1, $v1, $at       + 1 below cycle 2
                0x2441fffe,         # addiu $at, $v0, -2
                0x10200014,         # beqz  $at, 0x20e020       cycle 2: no change
                0x90620000,         # lbu   $v0, 0($v1)
                0x10000010,         # b     0x20e018            add it to the chance
                0x00000000)         # nop


def plan_pr_cycle(f, img):
    """Jobs for --mod pr-cycle."""
    words = [(SLES_FILE, PR_CYCLE_AT - 0xff000,
              struct.pack("<11I", *PR_CYCLE_OLD), struct.pack("<11I", *PR_CYCLE_NEW),
              "%s 0x%x (PR event business-cycle ladder)" % (SLES_FILE, PR_CYCLE_AT))]
    return word_jobs(f, img, "pr-cycle", words)


# --- the harder economy (DOC/ECONOMY.md, DOC/LMASTER_MOD.md#improvements) ------

COMMON_FILE, COMMON_ENTRY = "PARAM/PLRESOURCECOMMON.PAC", "plresourcecommon.pac"


def plan_facility_tiers(f, img, adopted=()):
    """Jobs for --mod facility-tiers: plrcommon.facility_tiers in
    PLRESOURCECOMMON.PAC and its PRELOAD/STATIONFILE.PAC copy, which the
    game also reads."""
    import plrcommon
    why = "facility-tiers: bigger facilities cost much more to build and keep up"
    path, data = read_file(f, img, COMMON_FILE)
    new = plrcommon.facility_tiers(data)
    if new is None:
        return [], ["note: %s already has the facility tiers" % COMMON_FILE]
    # gap=1: only the changed words, so special-stadium's capacities in the
    # same stadium records don't overlap these (each plan sees the original).
    return (diff_jobs(path, 0, data, new, why, gap=1)
            + pack_copy_jobs(f, img, STATION_FILE, COMMON_ENTRY, COMMON_FILE, data, new, why,
                             gap=1)), []


# special-stadium: the biggest stadium a club can build holds 100,000, not
# 110,000 (LMASTER full and max, the user's choice, 2026-10-30;
# DOC/LMASTER_MOD.md#stadiums). plrcommon.special_stadium sets its three
# levels; the match's stadium ids for it, STADIUM_DATA 96-101 (level 4 of
# CONV_INFO_BUILD), go to 100 too, since InitStadium (SLES 0x213780) divides
# the crowd by that capacity to fill the stands.
STADIUM_DATA_FILE, STADIUM_DATA_ENTRY = "PARAM/STADIUM_DATA.TBB", "Stadium_Data.tbb"
STADIUM_DATA_PACKS = ["PRELOAD/SIMFILE%d.PAC" % n for n in range(7)]
SPECIAL_IDS, SPECIAL_THOUSANDS = range(96, 102), (110, 100)


def special_stadium_data(data):
    """STADIUM_DATA.TBB bytes with ids 96-101 at 100,000; None when they
    already are."""
    import initteam
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, STADIUM_DATA_ENTRY)
        with open(path, "wb") as g:
            g.write(data)
        table = initteam.StadiumData(path)
    retail, new = SPECIAL_THOUSANDS
    held = [table.rows[i][2] for i in SPECIAL_IDS]
    if held == [new] * len(held):
        return None
    if held != [retail] * len(held):
        raise ValueError("special-stadium: %s stadiums 96-101 hold %s thousand, expected %d"
                         % (STADIUM_DATA_FILE, held, retail))
    for i in SPECIAL_IDS:
        table.set(i, "capacity", new)
    return table.encode()


def hook_or_keep(edit, data):
    """`edit(data)` for a target hook, or the target as it is when the
    switch's change is already there (None) or the target's own edit has
    replaced the bytes it expects (ValueError): the target's value wins."""
    try:
        new = edit(data)
    except ValueError:
        return data
    return data if new is None else new


def target_special_stadium(file, data):
    """A PLRESOURCECOMMON.PAC or STADIUM_DATA.TBB target (the editor's
    Facilities or Nations & stadiums tab) with the Special stadium at
    100,000 in its own bytes."""
    import plrcommon
    if norm(file) == norm(COMMON_FILE):
        return hook_or_keep(plrcommon.special_stadium, data)
    if norm(file) == norm(STADIUM_DATA_FILE):
        return hook_or_keep(special_stadium_data, data)
    return data


def file_jobs(f, img, file, edit, packs, entry, why, adopted, already):
    """Only-the-changed-bytes jobs for `edit` of `file` and its copies as
    `entry` in `packs`; a note when a target (`adopted`) has it or it's
    already there."""
    if norm(file) in adopted:
        return [], ["note: %s in the target's %s" % (why.split(":")[0], file)]
    path, data = read_file(f, img, file)
    new = edit(data)
    if new is None:
        return [], ["note: %s already %s" % (file, already)]
    jobs = diff_jobs(path, 0, data, new, why, gap=1)
    for pack in packs:
        jobs += pack_copy_jobs(f, img, pack, entry, file, data, new, why, gap=1)
    return jobs, []


def plan_special_stadium(f, img, adopted=()):
    """Jobs for --mod special-stadium: PLRESOURCECOMMON.PAC and its
    STATIONFILE copy, STADIUM_DATA.TBB and its SIMFILE copies, only the
    changed bytes (facility-tiers and real-grounds write the same tables)."""
    import plrcommon
    why = "special-stadium: the Special stadium holds 100,000"
    jobs, notes = file_jobs(f, img, COMMON_FILE, plrcommon.special_stadium, [STATION_FILE],
                            COMMON_ENTRY, why, adopted, "has the Special stadium at 100,000")
    j, n = file_jobs(f, img, STADIUM_DATA_FILE, special_stadium_data, STADIUM_DATA_PACKS,
                     STADIUM_DATA_ENTRY, why, adopted, "has stadiums 96-101 at 100,000")
    return jobs + j, notes + n


# sponsor-boards: every stadium's 12 advert boards are drawn afresh from
# all 205 sponsor logos, a fixed shuffle per stadium (LMASTER full and max,
# the user's request, 2026-10-30; DOC/LMASTER_MOD.md#stadiums). A computer
# club's ground shows its BUILD_STADIUM row's boards (InitStadium leaves
# the match's own empty), and the retail rows use 119 of the logos.
def plan_sponsor_boards(f, img, adopted=()):
    """Jobs for --mod sponsor-boards: the advert bytes of every
    BUILD_STADIUM row (real-grounds writes the rest of some rows)."""
    import stadium
    return file_jobs(f, img, BUILD_STADIUM_FILE, stadium.sponsor_boards, [], None,
                     "sponsor-boards: every ground's boards from all the sponsors", adopted,
                     "has the sponsor boards")


def target_build_stadium(edit, file, data, old):
    """A BUILD_STADIUM.TBB target (the editor's Stadiums tab) with `edit`
    applied row by row: each row's look and boards the target changed from
    `old`, the file as DAT (or the image) holds it, stay the target's."""
    import stadium
    if norm(file) != norm(BUILD_STADIUM_FILE):
        return data
    try:
        return stadium.keep_edits(old, data, edit(old) or old)
    except ValueError:
        return data


def target_sponsor_boards(file, data, old):
    import stadium
    return target_build_stadium(stadium.sponsor_boards, file, data, old)


# real-grounds: each computer club plays at a ground of its real 2005-06
# capacity, rounded to 5,000, the clubs of one size spread over the stadium
# ids of that size (LMASTER full and max, the user's request, 2026-10-30;
# DOC/LMASTER_MOD.md#stadiums). Its look follows its size more closely than
# the ladder's models do: initteam.real_grounds_build gives ids 102-118 the
# look of the right grounds
# (STADIUM/BUILD_STADIUM.TBB, no copies), real_grounds_stadiums their
# bands, and real_grounds_clubs points each club record at its ground
# (SRC/grounds.csv). The 100,000 band is 96-101, so it turns on
# special-stadium.
BUILD_STADIUM_FILE = "STADIUM/BUILD_STADIUM.TBB"
def target_real_grounds(file, data, old):
    """A PLRESOURCESIM.PAC, STADIUM_DATA.TBB or BUILD_STADIUM.TBB target
    (the editor's Clubs, Nations & stadiums or Stadiums tab) with the real
    grounds in its own bytes."""
    import initteam
    if norm(file) == norm(BUILD_STADIUM_FILE):
        return target_build_stadium(initteam.real_grounds_build, file, data, old)
    if norm(file) == norm(SIM_FILE):
        return hook_or_keep(initteam.real_grounds_clubs, data)
    if norm(file) == norm(STADIUM_DATA_FILE):
        return hook_or_keep(initteam.real_grounds_stadiums, data)
    return data


def plan_real_grounds(f, img, adopted=()):
    """Jobs for --mod real-grounds: the club records in PLRESOURCESIM.PAC
    and its SIMLOCALMEM copies, ids 102-118 in STADIUM_DATA.TBB and its
    SIMFILE copies, only the changed bytes (overseas-bases and
    special-stadium write the same files)."""
    import initteam
    why = "real-grounds: clubs at grounds of their real size"
    jobs, notes = file_jobs(f, img, SIM_FILE, initteam.real_grounds_clubs, LIST_PACKS,
                            SIM_ENTRY, why, adopted, "has the real grounds")
    j, n = file_jobs(f, img, STADIUM_DATA_FILE, initteam.real_grounds_stadiums,
                     STADIUM_DATA_PACKS, STADIUM_DATA_ENTRY, why, adopted,
                     "has stadiums 102-118 at their bands")
    j2, n2 = file_jobs(f, img, BUILD_STADIUM_FILE, initteam.real_grounds_build, [], None, why,
                       adopted, "has stadiums 102-118 built like bigger grounds")
    return jobs + j + j2, notes + n + n2


def word_jobs(f, img, switch, words):
    """Jobs for a switch that rewrites known words: (file, offset, old, new,
    label) each, offsets into the file. All already new is a note; words
    already new are left alone (a disc from an earlier version of the
    switch); any word holding neither is refused."""
    if img.kind != "disc image":
        raise ValueError("%s patches the game's code, so it needs the whole disc image, "
                         "not %s" % (switch, img.kind))
    if img.port is not None:
        for file, off, old, _, _ in words:
            img.port.expect(f, file, off, old)
    held = [read_at(f, img, file, off, len(old)) for file, off, old, _, _ in words]
    if img.port is not None:
        words = [(file, off) + port_calls(h, old, new) + (label,)
                 for h, (file, off, old, new, label) in zip(held, words)]
    if all(h == new for h, (_, _, _, new, _) in zip(held, words)):
        return [], ["note: %s is already applied" % switch]
    jobs = []
    for h, (file, off, old, new, label) in zip(held, words):
        if h == new:
            continue
        if h != old:
            raise ValueError("%s: %s doesn't hold the expected bytes; not the retail disc?"
                             % (switch, label))
        jobs.append(Job(file, off, new, label, switch))
    return jobs, []


def port_calls(held, old, new):
    """(old, new) for another build: where `held` differs from `old` only in
    jal targets (functions sit elsewhere there), old takes held's targets
    and each jal in `new` to one of old's functions calls it there."""
    if len(held) != len(old) or len(old) % 4 or len(new) % 4:
        return old, new
    hw = struct.unpack("<%dI" % (len(held) // 4), held)
    ow = struct.unpack("<%dI" % (len(old) // 4), old)
    calls = {}
    for h, o in zip(hw, ow):
        if h == o:
            continue
        if h >> 26 != 3 or o >> 26 != 3 or calls.get(o, h) != h:
            return old, new
        calls[o] = h
    if not calls:
        return old, new
    nw = struct.unpack("<%dI" % (len(new) // 4), new)
    return held, struct.pack("<%dI" % len(nw), *(calls.get(w, w) for w in nw))


def sles_word(addr, old, new, what):
    """A word of SLES_541.51 at address `addr` (the file is 0xff000 before)."""
    return (SLES_FILE, addr - 0xff000, struct.pack("<I", old), struct.pack("<I", new),
            "%s 0x%x (%s)" % (SLES_FILE, addr, what))


def simprg_word(off, old, new, what):
    return (NEGO_FILE, off, struct.pack("<I", old), struct.pack("<I", new),
            "%s 0x%x (%s)" % (NEGO_FILE, off, what))


# wider-tickets: ticket prices up to 480 (£80) on both ticket screens, and a
# ticket demand table (pwkUnkei_GetTicketHosei 0x2719c8) that covers them:
# 21 rows, the price thresholds at 0x556120 (300 down to 60 in 12s) and the
# s32 rows at 0x556250 (11 budget columns each). The new thresholds run 480
# down to 60 in 21s. Rows up to 300 are the old curve read at the new
# threshold (linear between the old rows); above it, crowds fall as
# (300 / price)^TICKET_FALL, so 480 draws half of 300's crowd.
TICKET_ROWS, TICKET_COLS = 21, 11
TICKET_THRESHOLDS, TICKET_TABLE = 0x556120, 0x556250
TICKET_MAX, TICKET_MAX_NEW, TICKET_MIN = 300, 480, 60
TICKET_FALL = 1.4748                # log 2 / log 1.6


def ticket_tables(old_t, old_r):
    """(new thresholds, new rows) as bytes, from the retail executable's
    thresholds and rows; ValueError if they aren't the retail ones."""
    if list(struct.unpack("<%di" % TICKET_ROWS, old_t)) != \
            [TICKET_MAX - 12 * i for i in range(TICKET_ROWS)]:
        raise ValueError("SLES 0x%x: not the retail ticket thresholds" % TICKET_THRESHOLDS)
    rows = [struct.unpack_from("<%di" % TICKET_COLS, old_r, 4 * TICKET_COLS * i)
            for i in range(TICKET_ROWS)]
    step = (TICKET_MAX_NEW - TICKET_MIN) // (TICKET_ROWS - 1)
    new_t = [TICKET_MAX_NEW - step * i for i in range(TICKET_ROWS)]

    def demand(price, c):
        if price >= TICKET_MAX:
            return rows[0][c] * (TICKET_MAX / price) ** TICKET_FALL
        i = (TICKET_MAX - price) // 12                  # old row at or above the price
        hi, lo = TICKET_MAX - 12 * i, TICKET_MAX - 12 * (i + 1)
        if price == hi or i + 1 >= TICKET_ROWS:
            return rows[i][c]
        return rows[i][c] + (rows[i + 1][c] - rows[i][c]) * (hi - price) / (hi - lo)

    new_r = b"".join(struct.pack("<%di" % TICKET_COLS,
                                 *[max(1, round(demand(p, c))) for c in range(TICKET_COLS)])
                     for p in new_t)
    return struct.pack("<%di" % TICKET_ROWS, *new_t), new_r


def plan_wider_tickets(f, img):
    """Jobs for --mod wider-tickets."""
    if img.kind != "disc image":
        raise ValueError("wider-tickets patches SLES_541.51, so it needs the whole disc "
                         "image, not %s" % img.kind)
    old_t = read_at(f, img, SLES_FILE, TICKET_THRESHOLDS - EXE_BASE, 4 * TICKET_ROWS)
    old_r = read_at(f, img, SLES_FILE, TICKET_TABLE - EXE_BASE, 4 * TICKET_ROWS * TICKET_COLS)
    if struct.unpack_from("<i", old_t)[0] == TICKET_MAX_NEW:
        return [], ["note: wider-tickets is already applied"]
    new_t, new_r = ticket_tables(old_t, old_r)
    words = [
        simprg_word(0x3ef98, 0x2403012c, 0x240301e0, "plan screen: ticket price up to 480"),
        simprg_word(0x3d1e4, 0x2404012c, 0x240401e0, "ticket set screen: up to 480"),
        (SLES_FILE, TICKET_THRESHOLDS - 0xff000, old_t, new_t,
         "%s 0x%x (ticket demand price thresholds)" % (SLES_FILE, TICKET_THRESHOLDS)),
        (SLES_FILE, TICKET_TABLE - 0xff000, old_r, new_r,
         "%s 0x%x (ticket demand table)" % (SLES_FILE, TICKET_TABLE)),
    ]
    return word_jobs(f, img, "wider-tickets", words)


# dearer-ads: the ad budget buys half as much per pound, up to twice the old
# maximum, so the full effect costs 60,000,000 (£10,000,000) a season. The
# plan screen's maximum (SIMPRG 0x3eec0), the popularity divisor (0x268ce0,
# 600,000 -> 1,200,000) and the ticket demand table's column step (0x2719e0
# and 0x271a88, 3,000,000 -> 6,000,000, with the interpolation's 1/100th of
# a step at 0x271aa0, 30,000 -> 60,000, which needs ori to fit).
DEARER_ADS = (
    simprg_word(0x3eec0, 0x3c0301c9, 0x3c030393, "plan screen: ad budget up to 60,000,000"),
    simprg_word(0x3eec4, 0x3463c380, 0x34638700, "plan screen: ad budget up to 60,000,000"),
    sles_word(0x268ce0, 0x3c030009, 0x3c030012, "popularity: budget / 1,200,000"),
    sles_word(0x268ce4, 0x346327c0, 0x34634f80, "popularity: budget / 1,200,000"),
    sles_word(0x2719e0, 0x3c05002d, 0x3c05005b, "ticket demand: a column per 6,000,000"),
    sles_word(0x2719e4, 0x34a5c6c0, 0x34a58d80, "ticket demand: a column per 6,000,000"),
    sles_word(0x271a88, 0x3c05002d, 0x3c05005b, "ticket demand: a column per 6,000,000"),
    sles_word(0x271a8c, 0x34a5c6c0, 0x34a58d80, "ticket demand: a column per 6,000,000"),
    sles_word(0x271aa0, 0x24057530, 0x3405ea60, "ticket demand: interpolation step 60,000"),
)


def plan_dearer_ads(f, img):
    """Jobs for --mod dearer-ads."""
    return word_jobs(f, img, "dearer-ads", DEARER_ADS)


# sponsor-fees and tv-fees cut the big amounts only: up to INCOME_KEEP
# (£2,000,000; amounts are paid x 100 in the stored unit) an amount stays,
# above it half of the rest goes. The sponsors are 212 records of 0x48 at
# SIMPRG.REL 0x23d978, ids 1-212 (plSponsor_GetDb 0x160dc0), with fees at
# +0x14 and +0x18; the TV offers are 19 records of 0x1c at 0x241780 with
# the base at +0x8 (DOC/ECONOMY.md). Each table's mark is one fee before
# and after.
INCOME_KEEP = 120000


def income_cut(value):
    return value if value <= INCOME_KEEP else INCOME_KEEP + (value - INCOME_KEEP) // 2


# name: (offset, record size, first id, records, fee offsets, mark offset, retail mark)
INCOME_TABLES = {
    "sponsor-fees": (0x23d978, 0x48, 1, 212, (0x14, 0x18), 0x48 + 0x14, 1350000),
    "tv-fees": (0x241780, 0x1c, 0, 19, (0x8,), 0x1c * 17 + 0x8, 3000000),
}


def income_table(data, switch):
    """(old, new) bytes of the switch's table, from `data`, its records as
    SIMPRG.REL holds them from the table's start; None when it is already
    cut; ValueError when it is neither."""
    off, size, first, count, fields, mark, retail = INCOME_TABLES[switch]
    held = struct.unpack_from("<i", data, mark)[0]
    if held == income_cut(retail):
        return None
    if held != retail:
        raise ValueError("%s: SIMPRG.REL 0x%x holds %d, expected %d; not the retail overlay?"
                         % (switch, off + mark, held, retail))
    start, end = size * first, size * (first + count)
    new = bytearray(data[start:end])
    for i in range(count):
        for field in fields:
            at = size * i + field
            value = struct.unpack_from("<i", new, at)[0]
            if value > 0:
                struct.pack_into("<i", new, at, income_cut(value))
    return data[start:end], bytes(new)


def plan_income(f, img, switch, why):
    if img.kind != "disc image":
        raise ValueError("%s patches DLL/SIMPRG.REL, so it needs the whole disc image, not %s"
                         % (switch, img.kind))
    off, size, first, count = INCOME_TABLES[switch][:4]
    data = read_at(f, img, NEGO_FILE, off, size * (first + count))
    got = income_table(data, switch)
    if got is None:
        return [], ["note: %s is already applied" % switch]
    old, new = got
    return diff_jobs(NEGO_FILE, off + size * first, old, new, why), []


def plan_sponsor_fees(f, img):
    """Jobs for --mod sponsor-fees."""
    return plan_income(f, img, "sponsor-fees",
                       "sponsor-fees: sponsor fees over £2M lose half the rest")


def plan_tv_fees(f, img):
    """Jobs for --mod tv-fees."""
    return plan_income(f, img, "tv-fees", "tv-fees: TV offers over £2M lose half the rest")


# season-demand halves season-ticket demand: pwkUnkei_GetExpectSeat divides
# by the float 60,000,000 (SLES 0x272a10/0x272a14, lui/ori); 120,000,000
# only changes the lui. The ticket forecast and match crowds don't use it.
SEASON_DEMAND = (
    sles_word(0x272a10, 0x3c014c64, 0x3c014ce4, "season tickets: demand / 120,000,000"),
)


def plan_season_demand(f, img):
    """Jobs for --mod season-demand."""
    return word_jobs(f, img, "season-demand", SEASON_DEMAND)


# --- the balance switches (DOC/LMASTER_MOD.md#improvements) --------------------

# injury-odds: worse injuries about twice as common. judgeKegaKind (SLES
# 0x21a068) picks the kind from a 9-byte row of percentages (kinds 0-8) of
# the practice (0x532c28) or match (0x532c90) table, 11 rows by fatigue.
# Each row's kinds 4-8 (six months or longer) double, to at least
# INJURY_FLOOR of a row (a rested player can get one too), all of it added
# to kind 4 where the row had none. The extra comes off kind 3, then kind 0,
# so each row keeps its total (100, and 99 in practice row 10).
# A match turns a light report's kinds 3+ into kind 0 and a heavy report's
# kinds 0-2 into kind 3 (SIMPRG.REL 0x163638), so taking from those two
# leaves light match injuries as they were.
INJURY_TABLES = (0x532c28, 0x532c90)        # practice, match
INJURY_KINDS, INJURY_ROWS = 9, 11
INJURY_FLOOR = {0x532c28: 2, 0x532c90: 5}


def injury_odds(tables):
    """[(address, old bytes, new bytes)] of the two kind tables, from
    {address: bytes} as the retail executable holds them; ValueError if a
    table isn't the retail one."""
    out = []
    for addr in INJURY_TABLES:
        old = tables[addr]
        new = bytearray()
        for r in range(INJURY_ROWS):
            row = list(old[INJURY_KINDS * r:INJURY_KINDS * (r + 1)])
            long_before = sum(row[4:])
            for k in range(4, INJURY_KINDS):
                row[k] *= 2
            row[4] += max(0, INJURY_FLOOR[addr] - sum(row[4:]))
            extra = sum(row[4:]) - long_before
            for k in (3, 0):
                take = min(extra, row[k])
                row[k] -= take
                extra -= take
            if extra:
                raise ValueError("SLES 0x%x row %d: no room for the longer injuries" % (addr, r))
            new += bytes(row)
        out.append((addr, old, bytes(new)))
    return out


INJURY_ODDS_MARK = (0x532c90 + 4, 0, 5)     # match row 0, kind 4: retail, new


def plan_injury_odds(f, img):
    """Jobs for --mod injury-odds."""
    if img.kind != "disc image":
        raise ValueError("injury-odds patches SLES_541.51, so it needs the whole disc image, "
                         "not %s" % img.kind)
    tables = {a: read_at(f, img, SLES_FILE, a - EXE_BASE, INJURY_KINDS * INJURY_ROWS)
              for a in INJURY_TABLES}
    addr, retail, new = INJURY_ODDS_MARK
    if tables[INJURY_TABLES[1]][addr - INJURY_TABLES[1]] == new:
        return [], ["note: injury-odds is already applied"]
    words = [(SLES_FILE, a - 0xff000, old, new, "%s 0x%x (%s injury kind table)" % (
        SLES_FILE, a, "practice" if a == INJURY_TABLES[0] else "match"))
             for a, old, new in injury_odds(tables)]
    return word_jobs(f, img, "injury-odds", words)


# injury-lines: the "two months" and "nine months" condition lines, cut
# before both releases. plPinfo_KegaRecoverDaysChno (SLES 0x216dc8) gives
# a heavy injury chno 4, 5, 7, 8 or 9 below 6,000, 10,000, 16,000, 25,000
# and above, and the screen shows message chno + 1 of category 200, so 4
# and 7 never show. Its heavy ladder (0x216e14, 15 words) becomes a count:
# 9 less one for each threshold the value is under, so below 4,000 is 3
# (two months) and 10,000-12,499 is 6 (nine months). A new heavy injury
# of kind 3 is 4,000-6,000, so "two months" shows while it heals until it
# turns light; one of kind 5 starts at 10,001 and shows "nine months" up
# to 12,500. The branch at 0x216e10 to "not injured" (0x216e50, which
# sets 0) runs the first word in its delay slot, which is harmless there.
INJURY_LINES_AT = 0x216e14
INJURY_LINES_OLD = (0x2a221770, 0x1440000e, 0x24020004, 0x2a222710, 0x1440000b, 0x24020005,
                    0x2a223e80, 0x10400003, 0x2a2461a8, 0x10000006, 0x24020007, 0x24030008,
                    0x24020009, 0x10000002, 0x0064100b)
INJURY_LINES_STEPS = (4000, 6000, 10000, 12500, 16000, 25000)
INJURY_LINES_NEW = ((0x24020009,)                            # addiu $v0, $zero, 9
                    + sum(((0x2a240000 | t,                  # slti  $a0, $s1, t
                            0x00441023)                      # subu  $v0, $v0, $a0
                           for t in INJURY_LINES_STEPS), ())
                    + (0x10000002,                           # b     0x216e54
                       0x00000000))                          # nop
# The English text of messages 4 and 7 is on the disc; French, German,
# Italian and Spanish hold "See Let's Make revised text 0425". The new
# lines follow their neighbours (messages 5 and 8) and fit the placeholders'
# bytes, so the files keep their sizes. Their copies are in three PRELOAD
# packs per language.
INJURY_CATEGORY, INJURY_PLACEHOLDER = 200, "See Let's Make revised text 0425"
INJURY_TEXT = {2: ("Blessure grave. 2 mois de soins.", "Blessure grave. 9 mois de soins."),
               3: ("Schwere Verletzung - 2 Monate.", "Schwere Verletzung - 9 Monate."),
               4: ("Infortunio grave: 2 mesi di cure", "Infortunio grave: 9 mesi di cure"),
               5: ("Lesión grave: 2 meses de cura.", "Lesión grave: 9 meses de cura.")}
INJURY_TEXT_IDS = (4, 7)
INJURY_TEXT_PACKS = {n: ["PRELOAD/%s%d.PAC" % (p, n)
                         for p in ("SIMFILE", "TACTICSLARGE", "TACTICSMATCHLARGE")]
                     for n in INJURY_TEXT}


def fix_injury_lines(data):
    """A 200_<lang>.mbb (bytes) with messages 4 and 7 in its own language, the
    same size; None when it doesn't hold the placeholders (English, or
    already fixed)."""
    import mbb
    m = mbb.Mbb(data, "%d.mbb" % INJURY_CATEGORY)
    if m.category != INJURY_CATEGORY:
        raise ValueError("not a %d_<lang>.mbb" % INJURY_CATEGORY)
    if m.lang not in INJURY_TEXT:
        return None
    marker = mbb.encode(INJURY_PLACEHOLDER, m.lang)
    ids = [rid for rid, _ in m.records]
    for rid, text in zip(INJURY_TEXT_IDS, INJURY_TEXT[m.lang]):
        k = ids.index(rid)
        if m.records[k][1] != marker:
            return None
        m.records[k] = (rid, mbb.encode(text, m.lang))
    return m.build(len(data))


def target_injury_lines(file, data):
    """A MES.PAC target with the injury lines in its own 200 files."""
    if norm(file) != norm(MES_FILE):
        return data
    out = bytearray(data)
    for name, (off, size) in mes_entries(data).items():
        if name in {"%d_%d.mbb" % (INJURY_CATEGORY, n) for n in INJURY_TEXT}:
            new = fix_injury_lines(data[off:off + size])
            if new is not None:
                out[off:off + size] = new
    return bytes(out)


def plan_injury_lines(f, img, adopted=()):
    """Jobs for --mod injury-lines: the condition-line ladder, and the text
    in MES.PAC and its PRELOAD copies (or in a MES.PAC target, `adopted`)."""
    words = [(SLES_FILE, INJURY_LINES_AT - 0xff000,
              struct.pack("<15I", *INJURY_LINES_OLD), struct.pack("<15I", *INJURY_LINES_NEW),
              "%s 0x%x (injury condition lines)" % (SLES_FILE, INJURY_LINES_AT))]
    jobs, notes = word_jobs(f, img, "injury-lines", words)
    if norm(MES_FILE) in adopted:
        return jobs, notes + ["note: injury-lines: put the text in the target's %s" % MES_FILE]
    why = "injury-lines: the two-month and nine-month lines"
    e = img.entry(MES_FILE)
    entries = mes_entries(read_at(f, img, e.path, 0, struct.unpack_from(
        "<I", read_at(f, img, e.path, 0, 4))[0]))
    for n, packs in INJURY_TEXT_PACKS.items():
        name = "%d_%d.mbb" % (INJURY_CATEGORY, n)
        off, size = entries[name]
        data = read_at(f, img, e.path, off, size)
        new = fix_injury_lines(data)
        if new is None:
            continue
        jobs += diff_jobs(e.path, off, data, new, why)
        for pack in packs:
            jobs += pack_copy_jobs(f, img, pack, name, "%s#%s" % (MES_FILE, name), data, new, why)
    return jobs, notes


# overseas-bases: dearer bases. A base costs table 0 of
# PLRESOURCESIM.PAC entry 1 to set up, that cost x the level's rate to
# raise a level (_GetUp1SituLevelCapital 0x232f70) and x a higher rate in
# upkeep (GetMaintenanceExpence 0x233648), so doubling the 13 costs
# doubles all three. The game reads the pack's PRELOAD/SIMLOCALMEM0-6.PAC
# copies too. What a level does (the popularity factor at 0x268e18) stays,
# so each pound spent on a base buys half as much (the user's choice,
# 2026-10-26: like dearer-ads, not a stronger level).
SIM_FILE, SIM_ENTRY = "PARAM/PLRESOURCESIM.PAC", "plresourcesim.pac"
BRANCH_COST_X = 2
BRANCH_MARK = (6300000, 12600000)           # the cheapest base: retail, doubled
def target_overseas_bases(file, data):
    """A PLRESOURCESIM.PAC target (the editor's free agents) with the base
    costs doubled in its own bytes."""
    import plrsim
    if norm(file) != norm(SIM_FILE):
        return data
    costs = plrsim.branch_costs(data)
    if min(costs) != BRANCH_MARK[0]:
        return data
    return plrsim.encode_branch_costs(data, [c * BRANCH_COST_X for c in costs])


def plan_overseas_bases(f, img, adopted=()):
    """Jobs for --mod overseas-bases."""
    import plrsim
    jobs, notes = [], []
    if norm(SIM_FILE) in adopted:
        return jobs, notes + ["note: overseas-bases: doubled the costs in the target's %s"
                              % SIM_FILE]
    why = "overseas-bases: overseas bases cost twice as much"
    path, data = read_file(f, img, SIM_FILE)
    costs = plrsim.branch_costs(data)
    if min(costs) == BRANCH_MARK[1]:
        return jobs, notes + ["note: %s already has the doubled base costs" % SIM_FILE]
    if min(costs) != BRANCH_MARK[0]:
        raise ValueError("overseas-bases: %s's cheapest base costs %d, expected %d; not the "
                         "retail pack?" % (SIM_FILE, min(costs), BRANCH_MARK[0]))
    new = plrsim.encode_branch_costs(data, [c * BRANCH_COST_X for c in costs])
    jobs += diff_jobs(path, 0, data, new, why)
    for pack in LIST_PACKS:
        jobs += pack_copy_jobs(f, img, pack, SIM_ENTRY, SIM_FILE, data, new, why)
    return jobs, notes


# transfer-fees: every transfer fee twice as high, up to £250M. The base
# fee of a player move (0x247130, from pwkMoney_CalcMoveBase 0x247a00) is
# 1,350,000.0 x a rank and ability factor x three more (a float built by
# lui/ori at 0x247288; 2,700,000.0 differs only in the lui); what you pay
# another club (pwkMoney_CalcuPurchaceOtherTeamPlayerTransferMoney
# 0x248280) and what clubs offer for your players (CComOffer::CalcuOfferClub
# 0x225b20) start from it. Price kind 1's limits (the initializer at
# 0x24a140, in units of 100) cap it at 7,200,000, £120M, in all four
# currencies; 15,000,000 is £250M and a whole number of every currency's
# step.
TRANSFER_FEES = (
    sles_word(0x247288, 0x3c0149a4, 0x3c014a24, "transfer base fee 2,700,000"),
) + sum(((sles_word(lui, 0x3c06006d, 0x3c0600e4, "transfer fee cap 15,000,000"),
          sles_word(ori, 0x34c6dd00, 0x34c6e1c0, "transfer fee cap 15,000,000"))
         for lui, ori in ((0x24a1c8, 0x24a1d4), (0x24a1e0, 0x24a1ec),
                          (0x24a1f8, 0x24a204), (0x24a210, 0x24a21c))), ())


def plan_transfer_fees(f, img):
    """Jobs for --mod transfer-fees."""
    return word_jobs(f, img, "transfer-fees", TRANSFER_FEES)


# fee-tiers: transfer fees by player rank, on top of transfer-fees'
# doubling (the user's choice, 2026-10-26). The base fee (0x247130) is
# 1,350,000.0 x A[player rank][club-rank band] x (B[affiliation] +
# C[growth row][age]) x D[contract] x E[business cycle]; A, 16 rows of 6
# floats at 0x398478 (bands by club rank up to 5, 11, 17, 23, 29, 31 at
# 0x3985f8), is the only table the player's rank enters, and nothing
# else reads it. Each row is multiplied by its tier: lesser players
# (ranks 0-5) x2, ranks 6-11 x1.5, 12-14 x2, and rank 15, the "football
# icon", x3, so with transfer-fees the best player at a top club in a
# boom reaches about £246M, just under the £250M cap.
FEE_TABLE, FEE_RANKS, FEE_BANDS = 0x398478, 16, 6
FEE_TIERS = (2.0,) * 6 + (1.5,) * 6 + (2.0,) * 3 + (3.0,)
FEE_RETAIL_TOP = 73.5


def plan_fee_tiers(f, img):
    """Jobs for --mod fee-tiers. The new table is the retail one times the
    tiers, so the retail table is read from the disc; a table that is
    neither the retail one nor the tiered one is refused by word_jobs."""
    size = 4 * FEE_RANKS * FEE_BANDS
    held = read_at(f, img, SLES_FILE, FEE_TABLE - EXE_BASE, size)
    rows = [struct.unpack_from("<%df" % FEE_BANDS, held, 4 * FEE_BANDS * r)
            for r in range(FEE_RANKS)]
    # Rank 15 at the top band: 73.5 retail, 220.5 tiered.
    top = rows[-1][-1]
    if abs(top - FEE_RETAIL_TOP * FEE_TIERS[-1]) < 0.01:
        return [], ["note: fee-tiers is already applied"]
    if abs(top - FEE_RETAIL_TOP) >= 0.01:
        raise ValueError("fee-tiers: SLES 0x%x's top fee factor is %.2f, expected %.2f; not "
                         "the retail executable?" % (FEE_TABLE, top, FEE_RETAIL_TOP))
    new = b"".join(struct.pack("<%df" % FEE_BANDS, *(v * FEE_TIERS[r] for v in rows[r]))
                   for r in range(FEE_RANKS))
    words = [(SLES_FILE, FEE_TABLE - EXE_BASE, held, new,
              "%s 0x%x (transfer fee factor by player rank)" % (SLES_FILE, FEE_TABLE))]
    return word_jobs(f, img, "fee-tiers", words)


# slow-reputation: club status (the reputation behind the club rank,
# status >> 11) rises half as fast; losses stay (the user's choice,
# 2026-10-26). It rises from three places, all in SLES_541.51:
# - after each match (0x26ddd8): 4 x ((opponent's rank - yours) / 2 + 16,
#   or - 16 for a loss) x a competition factor x a result factor x a
#   league factor. The result factors (0x399668) are {win, draw, loss}
#   against a stronger or equal club {2, 1, 0.5} and against a weaker
#   one {1, 0.5, 1}; a win or draw always adds, a loss always takes, so
#   halving the win and draw factors halves the gains alone.
# - final places (pwkTeam_MatchGameCheck 0x26dfa8): the international
#   competitions' points ({compe, 5 places}, 9 records at 0x555188), the
#   cups' (2 x 5 at 0x555260) and the leagues' (2 x 6 at 0x555288), all
#   gains, halved (every value is even).
# - each year end (pwkTeam_YearEndCheck 0x26e2a0): 500.0, the lui at
#   0x26e2c4, becomes 250.0.
# Only this code reads those tables (every load of their addresses).
STATUS_RESULT = 0x399668
STATUS_RESULT_OLD = (2.0, 1.0, 0.5, 1.0, 0.5, 1.0)
STATUS_RESULT_NEW = (1.0, 0.5, 0.5, 0.5, 0.25, 1.0)
STATUS_INTERNATIONAL = (0x555188, (
    (34, 4000, 2000, 1000, 500, 240), (35, 2000, 1000, 500, 240, 120),
    (36, 600, 300, 150, 0, 0), (38, 1000, 500, 240, 0, 0), (39, 200, 100, 50, 0, 0),
    (40, 600, 300, 150, 0, 0), (41, 400, 200, 100, 0, 0), (42, 600, 300, 150, 0, 0),
    (43, 400, 200, 100, 0, 0)), 1)      # the first word of a record is the competition
STATUS_CUP = (0x555260, ((400, 200, 100, 0, 0), (200, 100, 50, 0, 0)), 0)
STATUS_LEAGUE = (0x555288, ((3000, 0, 600, 1000, 600, 400), (600, 300, 0, 0, 60, 0)), 0)


def status_points_word(table):
    """A slow-reputation word for a points table: retail bytes, halved."""
    addr, rows, keep = table
    old = b"".join(struct.pack("<%di" % len(r), *r) for r in rows)
    new = b"".join(struct.pack("<%di" % len(r), *(r[:keep] + tuple(v // 2 for v in r[keep:])))
                   for r in rows)
    return (SLES_FILE, addr - EXE_BASE, old, new,
            "%s 0x%x (status points by final place)" % (SLES_FILE, addr))


SLOW_REPUTATION = (
    (SLES_FILE, STATUS_RESULT - EXE_BASE, struct.pack("<6f", *STATUS_RESULT_OLD),
     struct.pack("<6f", *STATUS_RESULT_NEW),
     "%s 0x%x (status after a match: win and draw factors halved)" % (SLES_FILE, STATUS_RESULT)),
    status_points_word(STATUS_INTERNATIONAL),
    status_points_word(STATUS_CUP),
    status_points_word(STATUS_LEAGUE),
    sles_word(0x26e2c4, 0x3c0143fa, 0x3c01437a, "status each year end: 250"),
)


def plan_slow_reputation(f, img):
    """Jobs for --mod slow-reputation."""
    return word_jobs(f, img, "slow-reputation", SLOW_REPUTATION)


# third-tier, the game over: finishing in the second division's bottom ends the
# game after one season, not two running (the user's third-tier idea,
# DOC/LMASTER_MOD.md). SIMPRG.REL 0x15d958 (from 2007, with your club in
# the second division) reads your final rank in the latest season ($s1)
# and the one before ($s0) and returns 1 when both are past the
# division's line (0x15d8f0). The new code skips the test that the
# earlier record exists and returns 1 on the latest season alone. The
# warning before it (0x15da60: this season's live rank and last season's)
# likewise warns on this season alone: the last-season record is neither
# required nor read. Branches only, since the overlay is relocated.
ONE_SEASON_END = (
    simprg_word(0x15da08, 0x5200000f, 0x00000000, "game over: no earlier season needed"),
    simprg_word(0x15da34, 0x92030004, 0x10000004, "game over: the latest season decides"),
    simprg_word(0x15da38, 0x0083182a, 0x24020001, "game over: the latest season decides"),
    simprg_word(0x15daf0, 0x5040000c, 0x00000000, "warning: no last season needed"),
    simprg_word(0x15dafc, 0x90510004, 0x00000000, "warning: last season not read"),
    simprg_word(0x15db18, 0x14600002, 0x10000002, "warning: this season decides"),
)


# --- LMASTER code segment and the bigger save (DOC/LMASTER_MOD.md) -----------

# A small MIPS encoder for the code the switches add, so it reads as
# instructions. Register numbers as the EE names them.
ZERO, AT, V0, V1, A0, A1, A2, A3, T0, T1, T2 = 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10
S0, S1, S2, SP, RA = 16, 17, 18, 29, 31


def _i(op, rs, rt, imm):
    return op << 26 | rs << 21 | rt << 16 | imm & 0xFFFF


def _r(rs, rt, rd, funct):
    return rs << 21 | rt << 16 | rd << 11 | funct


def addiu(rt, rs, imm): return _i(0x09, rs, rt, imm)
def slti(rt, rs, imm): return _i(0x0A, rs, rt, imm)
def sltiu(rt, rs, imm): return _i(0x0B, rs, rt, imm)
def ori(rt, rs, imm): return _i(0x0D, rs, rt, imm)
def lui(rt, imm): return _i(0x0F, 0, rt, imm)
def lw(rt, off, rs): return _i(0x23, rs, rt, off)
def lbu(rt, off, rs): return _i(0x24, rs, rt, off)
def sb(rt, off, rs): return _i(0x28, rs, rt, off)
def sw(rt, off, rs): return _i(0x2B, rs, rt, off)
def ld(rt, off, rs): return _i(0x37, rs, rt, off)
def sd(rt, off, rs): return _i(0x3F, rs, rt, off)
def lq(rt, off, rs): return _i(0x1E, rs, rt, off)     # 128-bit, as the game saves s registers
def sq(rt, off, rs): return _i(0x1F, rs, rt, off)
def beqz(rs, off): return _i(0x04, rs, 0, off)       # off in words from the delay slot
def bnez(rs, off): return _i(0x05, rs, 0, off)
def addu(rd, rs, rt): return _r(rs, rt, rd, 0x21)
def move(rd, rs): return _r(rs, 0, rd, 0x2D)         # daddu rd, rs, $zero
def mult3(rd, rs, rt): return _r(rs, rt, rd, 0x18)   # the R5900's three-operand mult
def movn(rd, rs, rt): return _r(rs, rt, rd, 0x0B)
def jr(rs): return _r(rs, 0, 0, 0x08)
def j(target): return 0x08000000 | (target >> 2 & 0x3FFFFFF)
def jal(target): return 0x0C000000 | (target >> 2 & 0x3FFFFFF)
NOP = 0


def words(*ws):
    return struct.pack("<%dI" % len(ws), *ws)


# The LMASTER code segment. SLES_541.51 has one loadable segment, which
# ends at file offset 0x46a2dc; the .DVP.overlay sections after it are
# never loaded. A second PT_LOAD program header (the gap after the first,
# at 0x54, is zero) loads CAVE_SIZE bytes of them at CAVE, in EE RAM below
# the executable that the game leaves zero, above the BIOS's EELOAD
# (0x82000). Code there is reached from the executable and from every
# overlay with plain j/jal. The file keeps its size.
CAVE, CAVE_FILE, CAVE_SIZE = 0xF8000, 0x46A350, 0x400
PHDR2 = 0x54
_BIT_READ, _BIT_WRITE = 0x20C200, 0x20C1C0       # _plBits_BitRead(bits, n, signed), BitWrite(bits, v, n, signed)

# third-tier, the bigger save (machinery any feature may use). The blocks' sizes
# (getSize: table 0x533ac8, size + 8) decide the allocation, which
# PlPworkTask (0x21d6f0) sums, and the layout CRC.
# - Block 2 (the other clubs) gains 18 records of 0xa8, 440-457, for
#   clubs 442-459; its serializers' loops go to 458 (SAVEPRG.REL 0x29548
#   read, 0x1b844 write). pwkOteam_Team2Otindex (0x24b7e8) still sends
#   those clubs to record 1 (club 3's: it maps only 3-441, and
#   pwkOteam_GetPointer turns -1 into record 1); the third tier's phase 2
#   raises its bound.
# - Block 5 gains seven past records of 0x98 at its old end (0xb50d0) for
#   competitions 49-55, the third tiers 50-55 among them.
#   pwkRec_GetCompePastRecord (0x253590) is rewritten in its own 23 words
#   to take competitions up to 55 and send 49 on there (offset compe x
#   0x98 + 0x260 below 49, + 0xb33b8 from 49), with plPwork_GetPwork
#   (lui/lw of 0x3909a8) inlined to make room. Block 5's serializers (read
#   0x29838, write 0x1bad8) jump to a wrapper in the code segment, which
#   runs the two instructions it displaced, lets the serializer finish,
#   then reads or writes the new bytes, 8 bits each. The dispatchers call
#   them with jalr, so $ra is the overlay's base + 0x2b9fc (read) or
#   + 0x2ba34 (write), which locates the rest of the serializer.
# Saves of a disc with this switch don't load in the retail game, nor
# the other way round (the layout CRC differs); use it with mod-saves.
PWORK_SIZE_TABLE = 0x533AC8
BLOCK2_ADD, BLOCK5_ADD = 18 * 0xA8, 7 * 0x98
BLOCK5_OLD = 0xB50D0
SAVE_EXPAND_SIZES = ((2, 73928, 73928 + BLOCK2_ADD), (5, 741592, 741592 + BLOCK5_ADD))
PAST_RECORD = 0x253590
PAST_RECORD_OLD = bytes.fromhex(
    "e0ffbd271000b07f2d8080003100022a0d0040100000bfffb875080c000000002d2040004a76080c"
    "050005242d1840000500601098000224181002026002422402000010211062002d1000001000b07b"
    "0000bfdf0800e0032000bd27")
PAST_RECORD_NEW = words(
    addiu(SP, SP, -0x20), sd(RA, 0, SP), sq(S0, 0x10, SP),
    sltiu(V0, A0, 0x38),                      # competitions 0-55
    beqz(V0, 14), addiu(V1, ZERO, 0x98),      # else return 0 ($v0 is 0)
    mult3(S0, A0, V1),                        # compe x 0x98
    slti(V1, A0, 0x31),
    addiu(S0, S0, 0x260),
    lui(V0, 0xB), ori(V0, V0, 0x3158),        # 0xb33b8 - 0x260: from 49, past the old end
    movn(V0, ZERO, V1), addu(S0, S0, V0),
    lui(V1, 0x39), lw(A0, 0x9A8, V1),         # plPwork_GetPwork
    jal(0x21D928), addiu(A1, ZERO, 5),        # get(5)
    addu(V1, V0, S0), movn(V0, V1, V0),       # block 5 + offset, or 0 with no block
    ld(RA, 0, SP), lq(S0, 0x10, SP), jr(RA), addiu(SP, SP, 0x20))
SAVE_LOOPS = ((0x29548, 0x2AA301B8, 0x2AA301CA, "block 2 read: 458 records"),
              (0x1B844, 0x2AA201B8, 0x2AA201CA, "block 2 write: 458 records"))
# (serializer, its first two words, the base offset $ra holds, wrapper)
_VARS = CAVE + 0x200
SAVE_CAVE_SIZE = 0x280      # the save wrappers' part of the segment: code, then _VARS
BLOCK5_HOOKS = (("read", 0x29838, (0x27BDFF10, 0x7FB70070), 0x2B9FC),
                ("write", 0x1BAD8, (0x27BDFF00, 0x7FB70080), 0x2BA34))


def _block5_wrapper(at, hook):
    """The wrapper for one block 5 serializer, placed at CAVE address `at`."""
    kind, start, (first, second), back = hook
    after = at + 4 * 12
    delta = start + 8 - back                         # the serializer's third word, from $ra
    head = [second,                                  # the displaced sq; the addiu ran in the delay slot
            lui(T0, (_VARS + 0x8000) >> 16), sw(A0, _VARS & 0xFFFF, T0), sw(A1, (_VARS + 4) & 0xFFFF, T0),
            sw(RA, (_VARS + 8) & 0xFFFF, T0),
            lui(T2, (delta + 0x8000) >> 16 & 0xFFFF), addiu(T2, T2, delta), addu(T1, RA, T2),
            lui(RA, after >> 16), ori(RA, RA, after & 0xFFFF),
            jr(T1), NOP]
    if kind == "read":
        body = [move(A0, S1), addiu(A1, ZERO, 8), jal(_BIT_READ), move(A2, ZERO),
                sb(V0, 0, S0)]
    else:
        body = [move(A0, S1), lbu(A1, 0, S0), addiu(A2, ZERO, 8), jal(_BIT_WRITE),
                move(A3, ZERO)]
    loop = len(body)
    tail = ([addiu(SP, SP, -0x30), sq(S0, 0, SP), sq(S1, 0x10, SP), sq(S2, 0x20, SP),
             lui(T0, (_VARS + 0x8000) >> 16), lw(S1, _VARS & 0xFFFF, T0), lw(S0, (_VARS + 4) & 0xFFFF, T0),
             lui(T2, BLOCK5_OLD >> 16), ori(T2, T2, BLOCK5_OLD & 0xFFFF), addu(S0, S0, T2),
             addiu(S2, ZERO, BLOCK5_ADD)]
            + body
            + [addiu(S2, S2, -1), bnez(S2, -(loop + 2)), addiu(S0, S0, 1),
               lq(S0, 0, SP), lq(S1, 0x10, SP), lq(S2, 0x20, SP), addiu(SP, SP, 0x30),
               lui(T0, (_VARS + 0x8000) >> 16), lw(RA, (_VARS + 8) & 0xFFFF, T0), jr(RA), NOP])
    return words(*(head + tail))


def save_expand_cave():
    """The code segment's bytes: the two block 5 wrappers, then the
    wrappers' variables at CAVE + 0x200, zero."""
    out, at = b"", {}
    for hook in BLOCK5_HOOKS:
        at[hook[0]] = CAVE + len(out)
        out += _block5_wrapper(CAVE + len(out), hook)
    if len(out) > _VARS - CAVE:
        raise ValueError("the wrappers outgrow their space")
    return out.ljust(CAVE_SIZE, b"\0"), at


def phdr2():
    """The second program header: PT_LOAD, file CAVE_FILE at CAVE, RWX."""
    return struct.pack("<8I", 1, CAVE_FILE, CAVE, CAVE, CAVE_SIZE, CAVE_SIZE, 7, 0x10)


def code_segment_words(f, img):
    """Words that load the LMASTER code segment: e_phnum 2 and the second
    program header. Any switch that puts code there includes them (the
    segment's bytes are each switch's own)."""
    e_phnum = read_at(f, img, SLES_FILE, 0x2C, 2)
    if e_phnum not in (b"\x01\x00", b"\x02\x00"):
        raise ValueError("%s has %d program headers" % (SLES_FILE, e_phnum[0]))
    return [(SLES_FILE, 0x2C, b"\x01\x00", b"\x02\x00", "%s e_phnum 2" % SLES_FILE),
            (SLES_FILE, PHDR2, bytes(32), phdr2(),
             "%s program header 1: the LMASTER code segment at 0x%x" % (SLES_FILE, CAVE))]


def save_grow_words(f, img):
    """Words that grow the save: the blocks' sizes (SAVE_EXPAND_SIZES),
    block 2's serializer loops (SAVE_LOOPS), and block 5's serializers
    jumping to the wrappers in the code segment's first SAVE_CAVE_SIZE
    bytes, which save and load BLOCK5_ADD bytes from BLOCK5_OLD. A
    feature that needs more room raises these; the third tier uses them
    for clubs 442-459 and competitions 49-55."""
    cave, at = save_expand_cave()
    cave = cave[:SAVE_CAVE_SIZE]                # the rest is the third tier's own code
    held_cave = read_at(f, img, SLES_FILE, CAVE_FILE, SAVE_CAVE_SIZE)
    words_ = [(SLES_FILE, CAVE_FILE, held_cave if held_cave != cave else bytes(SAVE_CAVE_SIZE), cave,
               "%s 0x%x (the code segment's bytes, unloaded .DVP data before)"
               % (SLES_FILE, CAVE_FILE))]
    for block, old, new in SAVE_EXPAND_SIZES:
        words_.append(sles_word(PWORK_SIZE_TABLE + 4 * block, old, new,
                                "block %d size %d" % (block, new - 8)))
    for off, old, new, what in SAVE_LOOPS:
        words_.append((SAVE_FILE, off, struct.pack("<I", old), struct.pack("<I", new),
                       "%s 0x%x (%s)" % (SAVE_FILE, off, what)))
    for hook in BLOCK5_HOOKS:
        kind, start, (first, second), _ = hook
        words_.append((SAVE_FILE, start, words(first, second), words(j(at[kind]), first),
                       "%s 0x%x (block 5 %s: the wrapper at 0x%x)" % (SAVE_FILE, start, kind,
                                                                      at[kind])))
    return words_


def past_record_words():
    """pwkRec_GetCompePastRecord rewritten to send competitions 49-55 to
    block 5's added end."""
    return [(SLES_FILE, PAST_RECORD - EXE_BASE, PAST_RECORD_OLD, PAST_RECORD_NEW,
             "%s 0x%x (pwkRec_GetCompePastRecord: competitions 49-55 at block 5's end)"
             % (SLES_FILE, PAST_RECORD))]


# Relaying a function's stack frame, for buffers that grow: the frame
# size in its prologue and epilogue (addiu $sp, $sp, -/+frame), every
# load or store based on $sp (lq/sq, the s registers' saves, included),
# and every addiu/ori rt, $sp, imm that takes a buffer's address move by
# `shifts`; offsets past the frame (the caller's) move with its size.
# Anything else that touches $sp is refused, since it can't be mapped.
_SP_MEM = {0x1A, 0x1B, 0x1E, 0x1F, 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27,
           0x28, 0x29, 0x2A, 0x2B, 0x2C, 0x2D, 0x2E, 0x31, 0x35, 0x37, 0x39, 0x3D, 0x3F}


def relay_frame(code, addr, frame, new_frame, shifts):
    """`code` (a function's bytes at address `addr`) with its stack frame
    grown from `frame` to `new_frame` bytes. `shifts` is [(offset, delta)]
    in rising order: an offset from there on moves by delta (until the
    next). Raises ValueError for a use of $sp it can't map."""
    def move(off):
        if off >= frame:
            return off + new_frame - frame
        delta = 0
        for lo, d in shifts:
            if off >= lo:
                delta = d
        return off + delta

    out = []
    for k, w in enumerate(struct.unpack("<%dI" % (len(code) // 4), code)):
        op, rs, rt = w >> 26, (w >> 21) & 31, (w >> 16) & 31
        imm = w & 0xFFFF
        simm = imm - 0x10000 if imm & 0x8000 else imm
        where = addr + 4 * k
        if op == 0x09 and rs == SP and rt == SP:
            if simm not in (-frame, frame):
                raise ValueError("0x%x: $sp moves by %d, not the frame" % (where, simm))
            w = addiu(SP, SP, -new_frame if simm < 0 else new_frame)
        elif op in _SP_MEM and rs == SP or op == 0x09 and rs == SP:
            new = move(simm)
            if not -0x8000 <= new < 0x8000:
                raise ValueError("0x%x: offset 0x%x moves out of range" % (where, new))
            w = w & ~0xFFFF | new & 0xFFFF
        elif op == 0x0D and rs == SP:
            w = addiu(rt, SP, move(imm))         # ori rt, $sp, imm is $sp + imm
        elif op == 0 and SP in (rs, rt) and w & 0x3F in (0x21, 0x2D) and (w >> 11) & 31 != SP:
            # A copy of $sp, or $sp plus an index: a buffer at offset 0,
            # which must stay put (the index is the caller's to check)
            if move(0) != 0:
                raise ValueError("0x%x: $sp taken as a base, but offset 0 moves" % where)
        elif SP in (rs, rt) and not (op == 0 and (w >> 11) & 31 == SP and w & 0x3F in (0x21, 0x2D)):
            raise ValueError("0x%x: %08x uses $sp in a way that can't be mapped" % (where, w))
        out.append(w)
    return words(*out)


# third-tier, clubs 442-459: the tutorial's third-tier opponents become
# full clubs like 3-441 (the LMASTER third tier, phase 2a; needs
# the bigger save's block 2 records). DOC/CLUB_LIMITS.md sorts every site.
# - pwkOteam_Team2Otindex (0x24b7e8) maps clubs 3-459 to records 1-457.
# - The checks for a resident club (club < 442, club - 2 < 440, club - 3
#   < 439) take 442-459 in, and the non-resident path (0x24d65c) leaves
#   them out.
# - Three special cases for 442-459 are off (club - 442 < 18 never
#   holds): purchase offers skip their players (0x2289ec), team data are
#   built as non-resident (0x24bb10), the detail screen's page type 4
#   (0x288460).
# - The loops over clubs whose bodies work one club at a time through
#   block 2 (no buffer sized for 441) run to 459: set-up (pwkOteam_Init
#   with OTEAMMEMBER.TBB's 18 new squads, Init2), core info, the database
#   make, friendship by branch, player and youth candidates, the offers'
#   squad fill, and the year start (YRSTPRG.REL).
# Loops that fill buffers sized for 441 clubs stay as they are, so they
# leave 442-459 out until phase 2b relays them.
TIER_EXE = (    # (address, old immediate, new immediate, what)
    (0x24B7FC, 0x1B7, 0x1C9, "pwkOteam_Team2Otindex: clubs 3-459"),
    (0x24B930, 0x1BA, 0x1CC, "pwkOteam_GetOpinfoPointer: resident to 459"),
    (0x24BEF8, 0x1BA, 0x1CC, "pwkOteam_GetRank: resident to 459"),
    (0x24BFA0, 0x1BA, 0x1CC, "pwkOteam_GetWorldClubRank: resident to 459"),
    (0x24BCD4, 0x1B8, 0x1CA, "pwkOteam_GetTeamData: resident to 459"),
    (0x24A788, 0x1B8, 0x1CA, "pwkOteam_Init squad: resident to 459"),
    (0x24A738, 0x1BA, 0x1CC, "pwkOteam_Init: squads to club 459"),
    (0x24A60C, 0x1BA, 0x1CC, "pwkOteam_Init2: to club 459"),
    (0x24671C, 0x1BA, 0x1CC, "pwkMatchGrow_Grow: resident to 459"),
    (0x24829C, 0x1B8, 0x1CA, "transfer money: resident to 459"),
    (0x228C9C, 0x1B8, 0x1CA, "plTeam_IsPurchaseOKFromCOM: resident to 459"),
    (0x2228B0, 0x1B9, 0x1CB, "CAcquirePlayer::PickupPlayer: to club 459"),
    (0x2551B8, 0x1BA, 0x1CC, "rental by friendship: resident to 459"),
    (0x255278, 0x1BA, 0x1CC, "rental by branch: resident to 459"),
    (0x25A8C4, 0x1B8, 0x1CA, "pwkTeam_AddReleaseList: resident to 459"),
    (0x284DCC, 0x1B8, 0x1CA, "CDetailManager::ConvertPlayer_Type: resident to 459"),
    (0x284E5C, 0x1B8, 0x1CA, "CDetailManager::ConvertPlayer_Type: resident to 459"),
    (0x24D65C, 0x1BA, 0x1CC, "non-resident from club 460"),
    (0x2289EC, 0x12, 0, "plTeam_CheckPurchaseOffer: no 442-459 exception"),
    (0x24BB10, 0x12, 0, "pwkOteam_GetTeamData: no 442-459 exception"),
    (0x288460, 0x12, 0, "CDetailManager::ConvertTeam: no page type 4"),
    (0x20D314, 0x1BA, 0x1CC, "updatePlCoreInfoSub: to club 459"),
    (0x2230E0, 0x1BA, 0x1CC, "CMakeDataBase::MakeDB: to club 459"),
    (0x24A8D4, 0x1BA, 0x1CC, "friendship, branch set up: to club 459"),
    (0x24A944, 0x1BA, 0x1CC, "friendship, branch removed: to club 459"),
    (0x2607D4, 0x1BA, 0x1CC, "player candidates: to club 459"),
    (0x260830, 0x1BA, 0x1CC, "player candidates: to club 459"),
    (0x2609D0, 0x1BA, 0x1CC, "player candidates: to club 459"),
    (0x260B58, 0x1BA, 0x1CC, "player candidates: to club 459"),
    (0x262C20, 0x1BA, 0x1CC, "youth candidates: to club 459"),
    (0x22628C, 0x1BA, 0x1CC, "CComOffer::CalcuOfferClub squad fill: to club 459"),
)
TIER_OVERLAYS = (    # (file, offset, old immediate, new immediate, what)
    (NEGO_FILE, 0x9263C, 0x1BA, 0x1CC, "CPlayerSearchWindow_Task::GetPlayerAcquireCost: resident to 459"),
    (NEGO_FILE, 0x69924, 0x1B8, 0x1CA, "CKeyboard_Task::RecoveryInit: resident to 459"),
    (NEGO_FILE, 0x15AFA4, 0x1B8, 0x1CA, "ZinziYouthTeam: resident to 459"),
    (NEGO_FILE, 0x15B488, 0x1B8, 0x1CA, "ZinziMyTeam::DiscardPlayer: resident to 459"),
    (NEGO_FILE, 0x15BC5C, 0x1B8, 0x1CA, "ZinziMyTeam::JoinAllTransfer: resident to 459"),
    # 0x15ad30, called from CPracticeExecute's code (0x158470): a club's
    # rank / 4, up to 7, for a resident club and 0 for any other.
    (NEGO_FILE, 0x15AD4C, 0x1BA, 0x1CC, "practice: the club's rank level, resident to 459"),
    (NEGO_FILE, 0x527C4, 0x1B7, 0x1C9, "loans: clubs 3-459 by the usual checks"),
    (DISC + "DLL/YRSTPRG.REL", 0x17014, 0x1BA, 0x1CC, "year start: to club 459"),
    (DISC + "DLL/YRSTPRG.REL", 0x172AC, 0x1BA, 0x1CC, "year start: to club 459"),
    (DISC + "DLL/YRSTPRG.REL", 0x1783C, 0x1BA, 0x1CC, "year start: to club 459"),
)
OTEAM_FILE = "PARAM/OTEAMMEMBER.TBB"


def _imm_word(f, img, file, off, old, new, what):
    """A word whose 16-bit immediate goes from `old` to `new`, from the
    word the retail file holds there."""
    w = struct.unpack("<I", read_at(f, img, file, off, 4))[0]
    if w & 0xFFFF not in (old, new):
        raise ValueError("third-tier: %s 0x%x holds %#x, not an immediate %#x"
                         % (file, off, w, old))
    base = w & ~0xFFFF
    return (file, off, struct.pack("<I", base | old), struct.pack("<I", base | new),
            "%s 0x%x (%s)" % (file, off + (EXE_BASE if file == SLES_FILE else 0), what))


def tier_clubs_words(f, img):
    """third-tier's words for clubs 442-459 as full clubs (its
    OTEAMMEMBER.TBB comes from file_tier_clubs)."""
    words = [_imm_word(f, img, SLES_FILE, a - EXE_BASE, old, new, what)
             for a, old, new, what in TIER_EXE]
    words += [_imm_word(f, img, file, off, old, new, what)
              for file, off, old, new, what in TIER_OVERLAYS]
    return words


def file_tier_clubs(f, img, dat):
    """[(target, data)]: OTEAMMEMBER.TBB with squads for clubs 442-459,
    from the image's file and the player database in `dat` (or the
    image's own PBDATA_EU.PAC)."""
    import initteam
    import pbdata
    import tempfile
    _, data = read_file(f, img, OTEAM_FILE)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "OTEAMMEMBER.TBB")
        with open(path, "wb") as g:
            g.write(data)
        ot = initteam.OteamMembers(path)
        if ot.end_team != initteam.OTEAM_END:
            return []                                   # already has them
        pb = os.path.join(tmp, "PBDATA_EU.PAC")
        _, pdata = read_file(f, img, "PARAM/PBDATA_EU.PAC")
        with open(pb, "wb") as g:
            g.write(pdata)
        return [(OTEAM_FILE, initteam.add_tier_squads(ot, pbdata.PbData(pb)))]


# third-tier, the lists: those sized for 441 clubs grow to 459, so the third
# tier's clubs take part in what they feed (phase 2b).
# A list on the stack grows with its function's frame (relay_frame); the
# loops that fill or read it run to 459. DOC/CLUB_LIMITS.md has each one.
# - plTeam_GetClubrankList: 441 x 8 bytes on its stack, sorted.
# - CAcquirePlayer::Execute (the transfer AI): the club-rank list and the
#   clubs that buy this time, 441 words each on its stack, filled by
#   GetExecuteTeamList; CContractReform::GetExecuteTeamList's rank list.
# - GetOfferClub (offers for your players): a flag per club and four lists
#   of clubs (stride 0x6e8, an immediate), with SetLotClub's bound.
# - SIMPRG.REL ClubRank (the world ranking): 441 x 8 bytes on the stack
#   of its club update (0x150680), and the loops over clubs of its
#   helpers; the points live in block 2. The past-record points by nation
#   (0x1521e0) take 442-459's nation from the club like the others.
# - SIMPRG.REL CReport_month's club lists by nation and region (50 at
#   most, so they can't overflow).
# - SIMPRG.REL 0x8e0, a nation's clubs for Information > Club Info >
#   Other Club Info (0x1848) and the map window's counts (0x1ae8): clubs
#   2-441 of the nation, 50 at most, which its callers' lists hold. With
#   the tier a nation has 47 clubs at most, so none is cut off.
# Left as they are: ScheEuro_TeamEntryList's lists (clubs 3-440, at most
# 440, for the European places by rank: the third tier gets there by its
# league and cup records), the club editor's list (CEDITPRG.REL 0x2d84,
# capped by its caller) and Msg's 441-entry jump tables (message
# variables, not clubs).
TIER_LIST_RELAYS = (    # (file, start, end, frame, new frame, shifts, [(address, old, new)])
    (SLES_FILE, 0x22C098, 0x22C180, 0xE20, 0xEB0, [(0xDC8, 0x90)],
     [(0x22C09C, 0x1B8, 0x1CA), (0x22C0E8, 0x1B9, 0x1CB), (0x22C10C, 0x1BA, 0x1CC),
      (0x22C118, 0x1B9, 0x1CB), (0x22C138, 0x1B9, 0x1CB), (0x22C144, 0x1B8, 0x1CA)],
     "plTeam_GetClubrankList: 459 clubs"),
    (SLES_FILE, 0x221720, 0x2218B0, 0xE90, 0xF10, [(0x6F0, 0x40), (0xDE0, 0x80)], [],
     "CAcquirePlayer::Execute: two lists of 459"),
    (SLES_FILE, 0x223E10, 0x223EE0, 0x730, 0x770, [(0x6F0, 0x40)],
     [(0x223EB8, 0x1B9, 0x1CB)],
     "CContractReform::GetExecuteTeamList: 459 clubs"),
    (SLES_FILE, 0x2256F8, 0x225AA0, 0x2360, 0x24B0,
     [(0x700, 0x40), (0xDF0, 0x80), (0x14D8, 0xC8), (0x1BC0, 0x110), (0x22B0, 0x150)],
     [(0x225808, 0x1BA, 0x1CC), (0x225864, 0x1B9, 0x1CB), (0x2258E8, 0x1BA, 0x1CC),
      (0x225974, 0x1BA, 0x1CC), (0x2259D0, 0x6E8, 0x730)],
     "GetOfferClub: five lists of 460"),
    (NEGO_FILE, 0x150680, 0x150738, 0xDF0, 0xE80, [(0xDC8, 0x90)],
     [(0x150684, 0x1B8, 0x1CA), (0x1506D8, 0x1B9, 0x1CB), (0x15071C, 0x1B9, 0x1CB)],
     "ClubRank club update: 459 clubs"),
)
TIER_LIST_EXE = (
    (0x221D94, 0x1B9, 0x1CB, "CAcquirePlayer::GetExecuteTeamList: 459 clubs"),
    (0x221DBC, 0x1B9, 0x1CB, "CAcquirePlayer::GetExecuteTeamList: 459 clubs"),
    (0x2256C8, 0x1BA, 0x1CC, "SetLotClub: lists of 460"),
)
TIER_LIST_OVERLAYS = tuple(
    [(NEGO_FILE, off, 0x1B9, 0x1CB, "ClubRank: clubs 1-459")
     for off in (0x150D94, 0x1514F0, 0x151544, 0x151708, 0x1517F4, 0x151AB4, 0x151B20,
                 0x151B7C, 0x151BE8)]
    + [(NEGO_FILE, 0x1521E0, 0x1BA, 0x1CC, "ClubRank: past-record points by the club's nation"),
       (NEGO_FILE, 0xA1194, 0x1BA, 0x1CC, "CReport_month: clubs of a nation to 459"),
       (NEGO_FILE, 0xA1244, 0x1BA, 0x1CC, "CReport_month: clubs of a region to 459"),
       (NEGO_FILE, 0xA12F0, 0x1BA, 0x1CC, "CReport_month: clubs of a nation to 459"),
       (NEGO_FILE, 0xA1318, 0x1BA, 0x1CC, "CReport_month: clubs of a region to 459"),
       (NEGO_FILE, 0x918, 0x1BA, 0x1CC, "Other Club Info: clubs of a nation to 459"),
       (NEGO_FILE, 0x1CF850, 0x1B9, 0x1CB, "All Clubs Ranking: clubs 1-459")])
# The All Clubs Ranking screen (SIMPRG.REL 0x84df0, building the list at
# INFORMATION_MODULE + 0x4074, 0xe80 bytes) keeps a pointer per club at
# +8 and an index per club at +0x79c, each with room for 441, and fields
# between them. Each pointer is only the sorted data (+0x798) + 12 x i,
# and the indices are never read, so the builder stops writing both and
# the one reader (CNationRankList_Task 0x84b08) walks the data instead.
TIER_LIST_WORDS = (    # (offset, old word, new word, what)
    (0x85094, 0xAC640000, 0, "All Clubs Ranking: no pointer array"),
    (0x850A8, 0xAC520000, 0, "All Clubs Ranking: no index array"),
    (0x84BD4, 0x26B70008, 0x8EB70798, "All Clubs Ranking: lw $s7, 0x798($s5), the data"),
    (0x84BF8, 0x02E31821, 0, "All Clubs Ranking: nop"),
    (0x84C1C, 0x8C740000, 0x02E0A02D, "All Clubs Ranking: move $s4, $s7, entry i"),
    (0x84C24, 0x0080202D, 0x26F7000C, "All Clubs Ranking: addiu $s7, $s7, 12, the next"),
)


def _relay_word(f, img, file, start, end, frame, new_frame, shifts, imms, what):
    """(file, offset, old, new, label) for a function at `start`..`end`
    with its frame relaid and the immediates `imms` changed."""
    base = EXE_BASE if file == SLES_FILE else 0
    old = read_at(f, img, file, start - base, end - start)
    new = bytearray(relay_frame(old, start, frame, new_frame, shifts))
    for addr, was, now in imms:
        k = addr - start
        w = struct.unpack_from("<I", new, k)[0]
        if w & 0xFFFF != was:
            raise ValueError("third-tier: 0x%x holds %#x, not an immediate %#x" % (addr, w, was))
        struct.pack_into("<I", new, k, w & ~0xFFFF | now)
    return (file, start - base, old, bytes(new),
            "%s 0x%x-0x%x (%s)" % (file, start, end, what))


def tier_lists_words(f, img):
    """third-tier's words for the lists of 459 clubs."""
    words_ = [_relay_word(f, img, *r) for r in TIER_LIST_RELAYS]
    words_ += [_imm_word(f, img, SLES_FILE, a - EXE_BASE, old, new, what)
               for a, old, new, what in TIER_LIST_EXE]
    words_ += [_imm_word(f, img, file, off, old, new, what)
               for file, off, old, new, what in TIER_LIST_OVERLAYS]
    words_ += [(NEGO_FILE, off, struct.pack("<I", old), struct.pack("<I", new),
                "%s 0x%x (%s)" % (NEGO_FILE, off, what)) for off, old, new, what in TIER_LIST_WORDS]
    return words_


# third-tier, the tiers' seasons: competitions 50-55 (England to the
# Netherlands), as new schedule UIDs, and who goes up and down (phase 3;
# DOC/UID_LIMITS.md, DOC/LMASTER_MOD.md). UID 164 stays free: about 30
# calls pass it for the default rules (REGULATION.TBB row 164).
# - The leagues: each nation's tier as an other-nations version, 165-170
#   (its 3 clubs), and an own-nation version, 171-176 (5 clubs: two of
#   your second division's are sent down at the start), as the second
#   divisions have. Each gets a year row (loaded every season, on evenly
#   spaced game days of its second division's season), a savectrl byte
#   (type 0, the big leagues' pool, which has room), a league in
#   SCHEDULE_COMPETITION, its slots in SCHEDULE_TEAM_ENTRY and a
#   REGULATION row (its second division's, for its clubs, one place up).
#   Entry 164 of the two packs copies 163, so entry n stays UID n.
# - The movements: a second division takes its own ranks but the last,
#   and its tier's rank 1 (the winner); a tier takes its own ranks from 2,
#   and the second division's last. REGULATION's down count is 1.
# - Your nation: every own-nation version of a domestic UID (second
#   division, cup qualifying, cups) differs from its other-nations
#   version only by places for your club and the rival past the second
#   division's record, so it becomes a copy of it (UIDs it names moved to
#   the own versions): your second division has its real size.
# - Season 1: the seed table's rows 50-55 hold the tiers, and the seeding
#   loop (0x253200) reads rows to 55. A second division's seeded last
#   place holds a tier club and its tier's rank 1 that last club, so
#   everyone starts where the seeds put them. In your nation
#   ScheCallback_ProcPromotion (0x1131c8, rewritten in its own 76 words)
#   puts your club and the rival at ranks S - 2 and S - 1 and sends the
#   two seeded clubs there down to your 5-club tier.
# - Season end: calcCompetetionFinish (0x205fa8) writes the tables of
#   competitions to 55, of those whose year row's +7 is 1 (0x205f88). The yearly honours exist for 0-48 only, so for
#   49 on, a detour skips pwkRec_ShiftCompeConventionRecord (0x205fc0)
#   and everything after the table (0x20631c), in the LMASTER code
#   segment at TIER_CAVE.
# No change to the ticket-price module's loop over UIDs (SIMPRG.REL
# 0x3cfcc, your home games): its "none found" test compares with a second
# 164 (0x3cfb8), and raising only its bound made the Set Up Ticket Price
# screen come back for no game (seen in PCSX2); you never play in a tier.
# The clubs (442-459), their past records and the one-season game over
# are the switch's other parts.
TIER_UID_FIRST, TIER_NATIONS = 165, 6
TIER_UID_OWN = TIER_UID_FIRST + TIER_NATIONS          # 171-176
TIER_UID_END = TIER_UID_OWN + TIER_NATIONS            # 177
TIER_UID_SECOND = (2, 12, 21, 30, 40, 49)   # each nation's second division, other-nations version
TIER_SECOND_COMPE = (1, 7, 12, 17, 23, 28)  # ... and its competition (0x51ad70)
TIER_CLUBS, TIER_OWN_CLUBS = 3, 5
TIER_DOMESTIC = 33                          # competitions 0-32 belong to one nation each
INITTEAM_FILE = "PARAM/PLRRSRC_INITTEAMDATA.TBB"
TIER_UID_FILES = ("PARAM/SCHEDULE_SYSTEM.PAC", "PARAM/SCHEDULE_COMPETITION.PAC",
                  "PARAM/SCHEDULE_TEAM_ENTRY.PAC", "PARAM/REGULATION.TBB", INITTEAM_FILE,
                  "PARAM/CLUBRESULT.TBB")
# The lower cups (the English League Cup, the other nations' Club Cups,
# England to the Netherlands) take every club of their tier's record (the
# user's choice): a knockout grown by 3 clubs, 5 in your nation's version,
# its qualifying round as it was. The bracket is seeded with byes in the
# first round only (schedule.knockout_bracket_seeded; the user's choice,
# 2026-10-27): the top slots go straight to the second round. Every lower cup starts on Dec w1 midweek
# (turn 40, the user's choice), the cups' start turn and the main cup's
# first round, whose clubs (the qualifying winners and the first
# division) a lower cup doesn't have, as on the turns they already share.
# Its other rounds stay on the disc's midweeks for that many rounds (44,
# 50, 54, 76: the first of them moves to 40), and a 5th round (England's
# own version, 17 clubs) keeps 44. Never a European or national-team day
# (the user's rule).
TIER_CUP_COMPE = (5, 10, 15, 21, 26, 32)
TIER_CUP_TURNS = {2: (40, 76), 3: (40, 54, 76), 4: (40, 50, 54, 76), 5: (40, 44, 50, 54, 76)}
TIER_CAVE = CAVE + 0x280                    # past the save wrappers and their variables
TIER_SEED_LOOP = (0x253200, 0x2A020031, 0x2A020038, "past records seeded to competition 55")
TIER_FINISH_BOUND = (0x205FA8, 0x2A820031, 0x2A820038, "season-end tables to competition 55")
TIER_SHIFT = (0x205FC0, 0x253C58)           # jal pwkRec_ShiftCompeConventionRecord
TIER_FINISH = (0x20631C, 0x206328, 0x20651C)  # honours from here, back after the first, clean-up
PROMOTION, PROMOTION_WORDS = 0x1131C8, 76


def _asm(base, items):
    """Words for `items` at `base`: ints, ("label", name), and branches
    ("beqz"/"bnez", reg, name) or ("b", name) to a label, delay slots
    written as the next item."""
    at, pos = {}, 0
    for it in items:
        if isinstance(it, tuple) and it[0] == "label":
            at[it[1]] = pos
        else:
            pos += 1
    out = []
    for it in items:
        if isinstance(it, tuple) and it[0] == "label":
            continue
        if isinstance(it, tuple):
            off = at[it[-1]] - (len(out) + 1)
            it = {"beqz": lambda: beqz(it[1], off), "bnez": lambda: bnez(it[1], off),
                  "b": lambda: beqz(ZERO, off)}[it[0]]()
        out.append(it & 0xFFFFFFFF)
    return out


def tier_cave():
    """The tiers' code at TIER_CAVE: (words, {name: address})."""
    shift_at = TIER_CAVE
    shift = [slti(V0, A0, 0x31), ("beqz", V0, "ret"), NOP,
             j(TIER_SHIFT[1]), NOP,                 # competitions 0-48: shift their honours
             ("label", "ret"), jr(RA), NOP]
    finish_at = shift_at + 4 * len(_asm(shift_at, shift))
    start, back, cleanup = TIER_FINISH
    finish = [slti(V0, 20, 0x31), ("beqz", V0, "skip"), NOP,       # $s4: the competition
              jal(0x253AF8), move(A1, 20),          # the displaced call, its $a0 0 set before
              j(back), NOP,
              ("label", "skip"), j(cleanup), NOP]
    return _asm(shift_at, shift) + _asm(finish_at, finish), {"shift": shift_at, "finish": finish_at}


def promotion_words():
    """ScheCallback_ProcPromotion rewritten, padded with nops. Your
    nation's second division's record d is seeded with S clubs (its last
    a tier club) and its tier's t with 3 (the first d's seeded last
    club). With S the first empty place: t[4] = t[0], t[3] = d[S-2],
    t[0] = d[S-3], then your club at d[S-3] and the rival at d[S-2]. So
    the second division (d's ranks to S - 1, and t's 1) has the clubs it
    was seeded with but the two at S - 1 and S, which play in the 5-club
    tier (t's ranks 2-5, and d's S). Done once: not if your club or the
    rival is in d already."""
    w = _asm(PROMOTION, [
        addiu(SP, SP, -0x30), sd(RA, 0, SP), sq(S0, 0x10, SP), sq(S1, 0x20, SP),
        jal(0x2463B0), NOP,                         # pwkLg_GetMyNati: 1-6
        addiu(V0, V0, -1), sltiu(V1, V0, 6), ("beqz", V1, "ret"), NOP,
        (V0 << 16 | V1 << 11 | 3 << 6),             # sll $v1, $v0, 3
        lui(A0, 0x52), addu(A0, A0, V1), lw(S0, -0x528C & 0xFFFF, A0),   # 0x51ad74 + 8k: d
        addiu(S1, V0, 50),                          # t
        jal(PAST_RECORD), move(A0, S1),
        ("beqz", V0, "ret"), move(S1, V0),
        jal(PAST_RECORD), move(A0, S0),
        ("beqz", V0, "ret"), addiu(A0, V0, 8),      # d's teams
        move(T0, ZERO),
        ("label", "find"), lw(V1, 0, A0),
        addiu(V0, V1, -1), sltiu(V0, V0, 2), ("bnez", V0, "ret"), NOP,   # already there
        ("beqz", V1, "found"), NOP,
        addiu(T0, T0, 1), slti(V0, T0, 0x1F), ("bnez", V0, "find"), addiu(A0, A0, 4),
        ("b", "ret"), NOP,
        ("label", "found"), slti(V0, T0, 3), ("bnez", V0, "ret"), addiu(T1, S1, 8),
        lw(V0, 0, T1), sw(V0, 16, T1),              # t[4] = t[0]
        lw(V0, -8 & 0xFFFF, A0), sw(V0, 12, T1),    # t[3] = d[S-2]
        lw(V0, -12 & 0xFFFF, A0), sw(V0, 0, T1),    # t[0] = d[S-3]
        addiu(V0, ZERO, 1), sw(V0, -12 & 0xFFFF, A0),   # d[S-3] = your club
        addiu(V0, ZERO, 2), sw(V0, -8 & 0xFFFF, A0),    # d[S-2] = the rival
        ("label", "ret"), ld(RA, 0, SP), lq(S0, 0x10, SP), lq(S1, 0x20, SP),
        jr(RA), addiu(SP, SP, 0x30)])
    if len(w) > PROMOTION_WORDS:
        raise ValueError("ProcPromotion needs %d words, has %d" % (len(w), PROMOTION_WORDS))
    return w + [NOP] * (PROMOTION_WORDS - len(w))


def tier_uids_words(f, img):
    """third-tier's words for the tiers' seasons (the files come from
    file_tier_uids)."""
    cave, at = tier_cave()
    words_ = [sles_word(a, old, new, what) for a, old, new, what in (TIER_SEED_LOOP, TIER_FINISH_BOUND)]
    site, target = TIER_SHIFT
    words_.append(sles_word(site, jal(target), jal(at["shift"]),
                            "calcCompetetionFinish: no honours to shift from competition 49"))
    start = TIER_FINISH[0]
    words_.append((SLES_FILE, start - EXE_BASE, words(move(A0, ZERO), jal(0x253AF8)),
                   words(j(at["finish"]), move(A0, ZERO)),
                   "%s 0x%x (calcCompetetionFinish: no honours from competition 49)"
                   % (SLES_FILE, start)))
    old = read_at(f, img, SLES_FILE, PROMOTION - EXE_BASE, 4 * PROMOTION_WORDS)
    new = words(*promotion_words())
    words_.append((SLES_FILE, PROMOTION - EXE_BASE, old if old != new else bytes(len(new)), new,
                   "%s 0x%x (ScheCallback_ProcPromotion: two clubs of your second "
                   "division down to its tier)" % (SLES_FILE, PROMOTION)))
    off = CAVE_FILE + TIER_CAVE - CAVE
    held = read_at(f, img, SLES_FILE, off, 4 * len(cave))
    new = words(*cave)
    words_.append((SLES_FILE, off, held if held != new else bytes(len(new)), new,
                   "%s 0x%x (the third tier's code at 0x%x)" % (SLES_FILE, off, TIER_CAVE)))
    return words_


def _tier_turns(turns, days):
    """`days` turns spread evenly over `turns`, first and last kept."""
    if days > len(turns):
        raise ValueError("%d game days on %d turns" % (days, len(turns)))
    return [turns[round(i * (len(turns) - 1) / (days - 1))] for i in range(days)]


def _entry_record(slot, rank, compe):
    """A LAST_RANK team-entry record: rank `rank` of `compe` last season."""
    return struct.pack("<BBBBh", slot, rank, 0, 0, compe)


def file_tier_uids(f, img, dat):
    """[(target, data)]: the five files with the third tiers, from the
    image's own; [] when they have them already."""
    import initteam
    import pac
    import regulation
    import schedule
    import tbb
    import tempfile
    import clubresult
    sys_file, compe_file, entry_file, reg_file, init_file, result_file = TIER_UID_FILES
    _, sys_data = read_file(f, img, sys_file)
    head, blobs = pac.binpac_blobs(sys_data)
    system = schedule.System([(e[2], b) for e, b in zip(head.entries, blobs)])
    rows = schedule.year_uids(system.year)
    if TIER_UID_FIRST in rows:
        return []
    if len(system.savectrl) != regulation.UIDS:
        raise ValueError("third-tier: savectrl has %d UIDs, not %d"
                         % (len(system.savectrl), regulation.UIDS))
    _, compe_data = read_file(f, img, compe_file)
    chead, compes = pac.binpac_blobs(compe_data)
    _, entry_data = read_file(f, img, entry_file)
    ehead, entries = pac.binpac_blobs(entry_data)
    _, reg_data = read_file(f, img, reg_file)
    rend, rtables = tbb.parse(reg_data)
    regs = [regulation.Regulation(i, rtables[0].data[o:o + regulation.ROW])
            for i, o in enumerate(range(0, len(rtables[0].data), regulation.ROW))]
    if not len(compes) == len(entries) == regulation.UIDS == len(regs) - 1:
        raise ValueError("third-tier: the files don't have 164 UIDs")
    _, init_data = read_file(f, img, init_file)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "PLRRSRC_INITTEAMDATA.TBB")
        with open(path, "wb") as g:
            g.write(init_data)
        init = initteam.InitTeamData(path)
        _, result_data = read_file(f, img, result_file)
        path = os.path.join(tmp, "CLUBRESULT.TBB")
        with open(path, "wb") as g:
            g.write(result_data)
        result_buf, result_end, result_raw, results = clubresult.load(path)
    savectrl = bytearray(system.savectrl)

    # Your nation's versions become copies of the other nations'.
    pairs = {}
    for uid, (r, _) in rows.items():
        if r.kind in (1, 2) and 0 <= r.compe < TIER_DOMESTIC:
            pairs.setdefault(r.compe, {})[r.kind] = uid
    own_of = {d[2]: d[1] for d in pairs.values() if 1 in d and 2 in d}
    for other, own in own_of.items():
        compes[own] = compes[other]
        e = schedule.TeamEntry(entries[other])
        for i, rec in enumerate(e.records["now_rank"]):
            target = struct.unpack_from("<h", rec, 4)[0]
            if target in own_of:
                e.records["now_rank"][i] = rec[:4] + struct.pack("<h", own_of[target])
        e.header = bytes([own & 0xFF]) + e.header[1:]
        entries[own] = e.encode()
        mine, theirs = rows[own][0], rows[other][0]
        if rows[own][1] or rows[other][1]:
            raise ValueError("third-tier: UID %d or %d runs over the year end" % (own, other))
        mine.start, mine.end, mine.turns = theirs.start, theirs.end, list(theirs.turns)
        regs[own] = regulation.Regulation(own, regs[other].encode())
        for name, _ in regulation.SLOTS:
            if regs[own][name + "_uid"] in own_of:
                regs[own][name + "_uid"] = own_of[regs[own][name + "_uid"]]
        savectrl[own] = savectrl[other]

    # The lower cups take their tier's clubs, in slots after the others.
    for k, cup in enumerate(TIER_CUP_COMPE):
        t = 50 + k
        for kind, add in ((2, TIER_CLUBS), (1, TIER_OWN_CLUBS)):
            uid = pairs[cup][kind]
            c = schedule.Competition(compes[uid])
            e = schedule.TeamEntry(entries[uid])
            n = c.entrants
            if (c.type != 1 or schedule.knockout_shape(c) != (1, 1, "final", False)
                    or e.slots != n or regs[uid]["clubs"] != n):
                raise ValueError("third-tier: UID %d isn't a %d-club cup of single games"
                                 % (uid, n))
            e.records["last_rank"][e.counts["last_rank"]:e.counts["last_rank"]] = [
                _entry_record(n + i, i + 1, t) for i in range(add)]
            e.counts["last_rank"] += add
            e.header = bytes([uid & 0xFF]) + e.header[1:]
            entries[uid] = e.encode()
            days = schedule.set_knockout(c, n + add, layout="seeded")
            h = bytearray(c.header)
            struct.pack_into("<H", h, 0, uid)
            c.header = bytes(h)
            compes[uid] = c.encode()
            row = rows[uid][0]
            row.turns = list(TIER_CUP_TURNS[days])
            if row.start > row.turns[0]:
                raise ValueError("third-tier: UID %d starts on turn %d" % (uid, row.start))
            regs[uid]["clubs"] = n + add
            results[uid]["clubs"] = n + add

    compes.append(compes[-1])                       # entry 164: never loaded
    entries.append(entries[-1])
    tier_compes, tier_entries, tier_years, tier_regs = [], [], [], []
    for k, second in enumerate(TIER_UID_SECOND):
        d, t = TIER_SECOND_COMPE[k], 50 + k
        seeded = [c for c in init.past[d] if c]
        size = len(seeded)
        if regs[second]["clubs"] != size:
            raise ValueError("third-tier: UID %d has %d clubs, its record %d"
                             % (second, regs[second]["clubs"], size))
        tutorial = schedule.TeamEntry(entries[142 + k])
        real = [struct.unpack_from("<H", r, 4)[0] for r in tutorial.records["plteamid"]]
        real = [c for c in real if c != 1]
        if len(real) != TIER_CLUBS or any(init.past[t]):
            raise ValueError("third-tier: competition %d's clubs or record aren't as expected" % t)
        # Seeds: d's last place a tier club, t's rank 1 d's last club.
        init.past[d][size - 1] = real[0]
        init.past[t][:TIER_CLUBS] = [seeded[-1]] + real[1:]
        # The second divisions: the last place goes, the tier's winner comes.
        for uid in (second, own_of[second]):
            e = schedule.TeamEntry(entries[uid])
            last = [i for i, r in enumerate(e.records["last_rank"][:e.counts["last_rank"]])
                    if r[1] == size and struct.unpack_from("<h", r, 4)[0] == d]
            if len(last) != 1:
                raise ValueError("third-tier: UID %d doesn't take rank %d of competition %d"
                                 % (uid, size, d))
            i = last[0]
            e.records["last_rank"][i] = _entry_record(e.records["last_rank"][i][0], 1, t)
            e.header = bytes([uid & 0xFF]) + e.header[1:]
            entries[uid] = e.encode()
            if regs[uid]["down1_compe"] != t:
                raise ValueError("third-tier: UID %d sends its clubs to %d, not %d"
                                 % (uid, regs[uid]["down1_compe"], t))
            regs[uid]["down1_count"] = 1
        for uid, clubs in ((TIER_UID_FIRST + k, TIER_CLUBS), (TIER_UID_OWN + k, TIER_OWN_CLUBS)):
            c = schedule.Competition(compes[second])
            days = schedule.set_league(c, clubs)
            h = bytearray(c.header)
            struct.pack_into("<HH", h, 0, uid, t)
            c.header = bytes(h)
            tier_compes.append((uid, c.encode()))
            e = schedule.TeamEntry(entries[142 + k])
            e.records = {kind: [] for kind in schedule.TeamEntry.KINDS}
            e.records["last_rank"] = ([_entry_record(i, i + 2, t) for i in range(clubs - 1)]
                                      + [_entry_record(clubs - 1, size, d)])
            e.counts = {kind: 0 for kind in schedule.TeamEntry.KINDS}
            e.counts["last_rank"] = clubs
            e.header = bytes([uid & 0xFF]) + e.header[1:]
            tier_entries.append((uid, e.encode()))
            year = schedule.YearRow(rows[second][0].raw)
            # +7 is 1: calcCompetetionFinish keeps only such a competition's
            # result (0x205f88); with 0 the tiers' records stayed as seeded
            # and a relegated club came back as the winner (seen in PCSX2).
            year.uid, year.compe, year.cycle, year.flag = uid, t, 0xFF, 1
            year.kind = 2 if clubs == TIER_CLUBS else 1
            year.turns = _tier_turns(rows[second][0].turns, days)
            year.start, year.end = year.turns[0], year.turns[-1]
            tier_years.append((uid, year))
            r = regulation.Regulation(uid, regs[second].encode())
            r["clubs"] = clubs
            for name, _ in regulation.SLOTS:
                r[name + "_count"], r[name + "_compe"], r[name + "_uid"] = 0, -1, -1
            r["up1_count"], r["up1_compe"] = 1, d
            tier_regs.append((uid, r))
    for items, out in ((tier_compes, compes), (tier_entries, entries), (tier_regs, regs)):
        out.extend(b for _, b in sorted(items, key=lambda x: x[0]))
    system.year.extend(y for _, y in sorted(tier_years, key=lambda x: x[0]))

    sys_blobs = [b for _, b in system.encode()]
    end, t = tbb.parse(sys_blobs[4])
    trailer = tbb.trailer(sys_blobs[4], t)
    t[0].data = bytes(savectrl) + bytes(TIER_UID_END - len(savectrl))
    sys_blobs[4] = tbb.build(t, end, trailer)
    rtables[0].data = b"".join(r.encode() for r in regs)
    count = len(compes)
    return [(sys_file, pac.build_binpac(sys_data[:head.header_size], sys_blobs)),
            (compe_file, pac.build_binpac(pac.grow_binpac_header(
                compe_data[:chead.header_size], count), compes)),
            (entry_file, pac.build_binpac(pac.grow_binpac_header(
                entry_data[:ehead.header_size], count), entries)),
            (reg_file, tbb.build(rtables, rend, tbb.trailer(reg_data, rtables))),
            (init_file, init.encode()),
            (result_file, clubresult.encode_file(result_buf, result_end, result_raw, results))]


# third-tier, the text: the messages that state the rules the tier changes,
# in the five European languages (DOC/LMASTER_MOD.md#the-text). Your second
# division has its real size, two clubs fewer than retail's own version;
# its last club goes down to the tier; and finishing last ends the game
# after one season. Each nation's messages, England to the Netherlands:
# the advisor's intro to the division (487:1100-1105, the sizes the retail
# texts give in that order), Game Over conditions (487:1200-1205; the
# Italian ones name their nations, which shows 1204 is Spain and 1205 the
# Netherlands, where the other languages repeat Italy and Spain), the
# league rules screen (30001, by its promotion rules) and the season-start
# news (832, by the competition in the news record's date rule,
# EVSDATABIN_NEWS). With them the game over screen's conditions (30003:1),
# the advisor's warning (35680:0) and the game over message (487:902), and
# retail slips in the same messages: the Spanish intro's 216 clubs, a stray
# German word, an Italian 41 matches, the Spanish tier name "Cuarta"
# (fourth) and the Spanish point 3 cut off at "es menor". Edits are short
# replacements and our own sentences, so the retail text stays on the disc.
TT_LANGS = (1, 2, 3, 4, 5)                         # English, French, German, Italian, Spanish
TT_NATIONS = ("eng", "fra", "ger", "ita", "spa", "ned")
TT_SIZES = (26, 22, 20, 24, 24, 22)                 # retail own version; the tier's is 2 fewer
TT_RULES = (101, 107, 112, 117, 123, 128)           # 30001
TT_NEWS = (433, 436, 442, 438, 440, 445)            # 832, competitions 1, 7, 12, 17, 23, 28
TT_TIER = (                                          # MES 11:1142-1147, each language
    ("English League 1", "Ligue 1 anglaise", "Englische 1. Liga", "Prima divisione inglese",
     "Liga Inglesa 1"),
    ("French League Division 3", "Division 3 française", "Französische 3. Liga",
     "Terza divisione francese", "Liga Francesa 3ª División"),
    ("3rd German League", "Troisième division allemande", "Dritte Deutsche Liga",
     "Terza divisione tedesca", "Tercera Liga Alemana"),
    ("Italian League C", "Série C italienne", "Italienische Serie C", "Campionato italiano C",
     "Serie C Italia"),
    ("Spanish League Division 3", "Division 3 espagnole", "3. Spanische Liga",
     "Terza divisione spagnola", "Liga Española 3ª División"),
    ("3rd Dutch League", "Troisième division hollandaise", "Dritte Holländische Liga",
     "Terza divisione olandese", "Tercera Liga Holandesa"),
)
TT_COUNT = {1: ("teams", "clubs"), 2: ("équipes", "clubs"), 3: ("Teams", "Vereine"),
            4: ("squadre",), 5: ("equipos", "clubes")}
TT_MATCHES = {1: "matches", 2: "matches", 3: "Spiele", 4: "partite", 5: "encuentros"}
TT_BOTTOM = {1: "\nIf we finish bottom, it's game over.",
             2: "\nSi nous finissons derniers, la partie est finie.",
             3: "\nWenn wir Letzter werden, ist das Spiel vorbei.",
             4: "\nSe arriviamo ultimi, è la fine del gioco.",
             5: "\nSi terminamos últimos, será el fin del juego."}
# Game Over conditions, point 2: each nation's lines, in each language.
TT_POINT2 = (
    ("{lf}2. Finishing last (24th) in the Champions \n{lf}   Division at the end of a season. \n",
     "{lf}2. Finir dernier (24e) en division  \n{lf}   des champions en fin de saison.  \n",
     "{lf}2. Der Verein ist am Saisonende in der \n{lf}   Meisterliga Letzter (24.) geworden. \n",
     "{lf}2. ultimo posto (24a posizione) in \n{lf}   Divisione Campioni a fine stagione. \n",
     "{lf}2. Acabando último (puesto 24º) \n{lf}   en el Campeonato en una temporada. \n"),
    ("{lf}2. Finishing last (20th) in French League \n{lf}   Division 2 at the end of a season. \n",
     "{lf}2. Finir dernier (20e) en  \n{lf}   2ème div. en fin de saison.  \n",
     "{lf}2. Der Verein ist am Saisonende in der \n{lf}   Französischen Liga 2 Letzter (20.) \n"
     "{lf}   geworden. \n",
     "{lf}2. Ultimo posto (20a posizione) nella \n{lf}   seconda Divisione del campionato francese \n"
     "{lf}   a fine stagione. \n",
     "{lf}2. Acabando último (puesto 20º) \n{lf}   en la Liga Francesa en una temporada. \n"),
    ("{lf}2. Finishing last (18th) in the 2nd German \n{lf}   League at the end of a season. \n",
     "{lf}2. Finir dernier (18e) en 2è  \n{lf}   div. allemande en fin de saison.  \n",
     "{lf}2. Der Verein ist am Saisonende in der \n{lf}   Zweiten Deutschen Liga Letzter (18.) \n"
     "{lf}   geworden. \n",
     "{lf}2. Ultimo posto (18a posizione) nella \n{lf}   seconda Divisione del campionato tedesco \n"
     "{lf}   a fine stagione.  \n",
     "{lf}2. Acabando último (puesto 18º) \n{lf}   en la 2ª Liga Alemana en una temporada. \n"),
    ("{lf}2. Finishing last (22nd) in Italian \n{lf}   League B at the end of a season. \n",
     "{lf}2. Finir dernier (22e) en div. \n{lf}   B italienne en fin de saison.  \n",
     "{lf}2. Der Verein ist am Saisonende in der \n{lf}   Italienischen Liga B Letzter (22.) \n"
     "{lf}   geworden. \n",
     "{lf}2. Ultimo posto (22a posizione) nel  \n{lf}   campionato italiano B a fine stagione. \n",
     "{lf}2. Acabando último (puesto 22º) \n{lf}   en la Liga Italiana B en una temporada. \n"),
    ("{lf}2. Finishing last (22nd) in Spanish League \n{lf}   Division 2 at the end of a season. \n",
     "{lf}2. Finir dernier (22e) dans  \n{lf}   la div.2 esp. en fin de saison. \n",
     "{lf}2. Der Verein ist am Saisonende in der \n{lf}   Spanischen Liga 2 Letzter (22.) \n"
     "{lf}   geworden. \n",
     "{lf}2. Ultimo posto (22a posizione) nella \n{lf}    seconda Divisione del campionato spagnolo \n"
     "{lf}    a fine stagione. \n",
     "{lf}2. Acabando último (puesto 22º) \n{lf}   en la Liga Española en una temporada. \n"),
    ("{lf}2. Finishing last (20th) in the 2nd Dutch \n{lf}   League at the end of a season. \n",
     "{lf}2. Finir dernier (20e) dans la deuxième \n{lf}   division hollandaise en fin de saison. \n",
     "{lf}2. Der Verein ist am Saisonende in der \n{lf}   Zweiten Holländischen Liga Letzter (20.) \n"
     "{lf}   geworden. \n",
     "{lf}2. Ultimo posto (20a posizione) nella \n{lf}   seconda Divisione del campionato olandese \n"
     "{lf}   a fine stagione. \n",
     "{lf}2. Acabando último (puesto 20º) \n{lf}   en la 2ª Liga Holandesa en una temporada. \n"),
)
TT_SCREEN = {    # 30003:1, point 2
    1: "{lf} 2. Club team finishes last in \n{lf}    {var:1:2031} at the end \n{lf}    of a season. \n",
    2: "{lf} 2. {var:1:2031} : l'équipe du club \n{lf}    finit dernière en fin de saison. \n",
    3: "{lf} 2. Die Mannschaft ist am Saisonende \n{lf}    Letzter in der Rangliste \n"
       "{lf}    {var:1:2031}. \n",
    4: "{lf} 2. La squadra è arrivata ultima nella \n{lf}    classifica {var:1:2031} \n"
       "{lf}    a fine stagione. \n",
    5: "{lf} 2. {var:1:2031}: club en el último \n{lf}    puesto de la clasificación \n"
       "{lf}    al final de la temporada. \n"}
TT_WARNING = {   # 35680:0, from the sentence after "Careful, {name}!"
    1: ("Looking at", "Looking at our points total, we could well finish bottom of {var:1:2031}. "
        "If we finish last this season, it'll be game over."),
    2: ("Selon notre", "Selon notre total, nous pourrions bien finir derniers du groupe : "
        "{var:1:2031}. Si nous finissons derniers cette saison, tout sera terminé."),
    3: ("Bei unserer", "Bei unserer Punkteanzahl landen wir in Gruppe {var:1:2031} eventuell "
        "auf dem letzten Platz. Wenn wir diese Saison Letzter werden, ist das Spiel vorbei."),
    4: ("Di questo", "Di questo passo potremmo arrivare ultimi nel gruppo {var:1:2031}. "
        "Se arriviamo ultimi in questa stagione, siamo finiti."),
    5: ("Viendo nuestro", "Viendo nuestro total de puntos, bien podríamos acabar últimos en el "
        "grupo {var:1:2031}. Será el fin del juego si terminamos últimos esta temporada.")}
TT_OVER = {      # 487:902, its first sentence
    1: ("You've achieved nothing for the past two seasons.", "We finished bottom of the league."),
    2: ("Vous n'avez rien obtenu lors des deux dernières saisons.",
        "Nous avons fini derniers du championnat."),
    3: ("Während der letzten zwei Saisons haben Sie nichts erreicht.",
        "Wir sind Tabellenletzter geworden."),
    4: ("Non hai conquistato nulla nelle ultime due stagioni.",
        "Siamo arrivati ultimi in campionato."),
    5: ("No has logrado nada en las dos últimas temporadas.",
        "Hemos terminado últimos de la liga.")}
TT_RELEGATION = {
    1: "\n\n{color:4}Relegation{/color}\nThe club placed last is relegated to the %s.",
    2: "\n \n {color:4}Relégation{/color}\n Le club classé dernier est relégué en %s.",
    3: "\n \n {color:4}Abstieg{/color}\n Der Verein auf dem letzten Platz steigt in die %s ab.",
    4: "\n \n {color:4}Retrocessioni{/color}\n Il club classificato all'ultimo posto retrocede "
       "nel gruppo %s.",
    5: "\n \n {color:4}Descenso{/color}\n El club en el último puesto desciende a la %s."}
TT_DROP = {      # the news, at the end: the next sentence often refers back to promotion
    1: " The bottom club will be relegated to the %s.", 2: " Le dernier sera relégué en %s.",
    3: " Der Letzte steigt in die %s ab.", 4: " L'ultima classificata retrocederà nel gruppo %s.",
    5: " El último clasificado descenderá a la %s."}


def tier_text_edits():
    """[(category, id, language, edit)]: ("sub", old, new) replaces text
    found once, ("count", old, new) a club count before its word, ("block",
    start, end, new) the text from start up to end (None: the message's
    end), ("add", new) appends. The slips come before the edits they
    precede."""
    edits = [(487, 1100, 5, ("sub", "216 equipos", "26 equipos")),
             (487, 1103, 3, ("sub", "-Aufsteiger. Vereine Die", "-Aufsteiger. Die")),
             (487, 1105, 4, ("sub", "41 partite", "42 partite")),
             (11, 1147, 5, ("sub", "Cuarta Liga Holandesa", "Tercera Liga Holandesa")),
             (30003, 1, 5, ("block", "{lf}    es menor", None, "{lf}    es menor que 8. \n"))]
    for k, nation in enumerate(TT_NATIONS):
        old = TT_SIZES[k]
        for n, lang in enumerate(TT_LANGS):
            count = (("sub", "Son 22 los clubes", "Son 20 los clubes") if (nation, lang) == ("fra", 5)
                     else ("count", old, old - 2))
            edits += [(487, 1100 + k, lang, count),
                      (487, 1100 + k, lang, ("sub", "%d %s" % (2 * old - 2, TT_MATCHES[lang]),
                                             "%d %s" % (2 * old - 6, TT_MATCHES[lang]))),
                      (487, 1100 + k, lang, ("add", TT_BOTTOM[lang])),
                      (487, 1200 + k, lang, ("block", "{lf}2.", "{lf}3.", TT_POINT2[k][n])),
                      (30001, TT_RULES[k], lang, ("add", TT_RELEGATION[lang] % TT_TIER[k][n])),
                      (832, TT_NEWS[k], lang, ("add", TT_DROP[lang] % TT_TIER[k][n]))]
    for lang in TT_LANGS:
        edits += [(30003, 1, lang, ("block", "{lf} 2.", "{lf} 3.", TT_SCREEN[lang])),
                  (35680, 0, lang, ("block", TT_WARNING[lang][0], None, TT_WARNING[lang][1])),
                  (487, 902, lang, ("sub",) + TT_OVER[lang])]
    return edits


def tier_text_edit(text, lang, edit):
    """`text` with one edit applied; unchanged when it is applied already
    (a MES.PAC target that has it). ValueError when it doesn't fit."""
    kind = edit[0]
    if kind in ("sub", "count"):
        olds = ([edit[1]] if kind == "sub" else
                ["%d %s" % (edit[1], w) for w in TT_COUNT[lang]])
        news = ([edit[2]] if kind == "sub" else
                ["%d %s" % (edit[2], w) for w in TT_COUNT[lang]])
        hits = [(o, n) for o, n in zip(olds, news) if text.count(o) == 1]
        if len(hits) == 1:
            return text.replace(*hits[0])
        if any(text.count(n) == 1 for n in news):
            return text
        raise ValueError("%r: not found once" % olds[0])
    if kind == "block":
        _, start, end, new = edit
        if new in text:
            return text
        i = text.find(start)
        j = len(text) if end is None else text.find(end, i + 1)
        if i < 0 or j < 0:
            raise ValueError("%r .. %r: not found" % (start, end))
        lines = text[i:j].split("\n")
        # Keep a blank {lf} line that ends the region: the spacing between points.
        tail = lines[-2] + "\n" if end and len(lines) > 2 and lines[-2].strip() == "{lf}" else ""
        return text[:i] + new + tail + text[j:]
    if kind == "add":
        return text if text.endswith(edit[1]) else text.rstrip(" \n") + edit[1]
    raise ValueError(kind)


def target_tier_text(file, data):
    """A MES.PAC (the disc's, or a target's) with the third tier's text. An
    entry that grows stays in its slot (mbb.MesPack); one past it would
    move the later entries, which the text never needs."""
    import mbb
    import tempfile
    if norm(file) != norm(MES_FILE):
        return data
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "MES.PAC")
        with open(path, "wb") as g:
            g.write(data)
        pack = mbb.MesPack(path)
    # An image patched before already has the text (its edits build on one
    # another, so they can't be found a second time): the English intro's
    # added last line tells.
    if pack.text(487, 1, 1100).endswith(TT_BOTTOM[1]):
        return data
    errors = []
    for cat, rid, lang, edit in tier_text_edits():
        try:
            pack.set(cat, lang, rid, 0, tier_text_edit(pack.text(cat, lang, rid), lang, edit))
        except ValueError as e:
            errors.append("%d:%d language %d: %s" % (cat, rid, lang, e))
    out, _, _, build_errors = pack.build()
    if errors or build_errors:
        raise ValueError("third-tier text: " + "; ".join(errors + build_errors))
    if pack.moved:
        raise ValueError("third-tier text: a message file outgrows its slot in %s" % MES_FILE)
    return out


# retail-text: messages the retail game gets wrong, for LMASTER lite
# (DOC/LMASTER_MOD.md#retail-text-fixes). Point 2 of the Game Over conditions for
# Spain (487:1204) and the Netherlands (1205) names the wrong league in
# some languages, as the Italian texts show (Spain's 23rd, the
# Netherlands' 21st); the Spanish intro (487:1100) says 216 clubs for 26;
# and team 435's name is "AL-Hyde" for "Al-Hyde" (user report; categories
# 3, 4 and 100003). Category 487 has no PRELOAD copy and may grow inside
# its slot; the name keeps its size, so its STATIONMES copies take the
# same bytes. The third tier rewrites point 2 again, and its "216 equipos"
# edit finds the fix in place.
RETAIL_POINT2 = {
    (1204, 1): "{lf}2. Placed lower than 23rd in Spanish League \n"
               "{lf}   Division 2 for two consecutive years. \n",
    (1204, 3): "{lf}2. Der Verein ist in zwei aufeinander \n{lf}   folgenden Jahren in der "
               "Spanischen Liga 2 \n{lf}   23. oder schlechter geworden. \n",
    (1205, 1): "{lf}2. Placed lower than 21st in the 2nd Dutch \n"
               "{lf}   League for two consecutive years. \n",
    (1205, 2): "{lf}2. Ils se classent en-dessous de la 21ème place \n{lf}   dans la deuxième "
               "division hollandaise pour 2  \n{lf}   années consécutives. \n",
    (1205, 3): "{lf}2. Der Verein ist in zwei aufeinander \n{lf}   folgenden Jahren in der "
               "Zweiten Holländischen \n{lf}   Liga 21. oder schlechter geworden. \n",
    (1205, 5): "{lf}2. Estando por debajo del puesto 21º \n"
               "{lf}   en la 2ª Liga Holandesa 2 años consec. \n",
}
RETAIL_NAMES = ((435, "AL-Hyde", "Al-Hyde"),)      # (team, retail, fixed)
NAME_LISTS = ((3, 2000), (4, 3000), (100003, 2000))
STATIONMES = ["PRELOAD/STATIONMES%d.PAC" % n for n in TT_LANGS]


def retail_text_edits():
    """[(category, id, language, edit)] in tier_text_edit's terms."""
    edits = [(487, rid, lang, ("block", "{lf}2.", "{lf}3.", text))
             for (rid, lang), text in RETAIL_POINT2.items()]
    edits.append((487, 1100, 5, ("sub", "216 equipos", "26 equipos")))
    for team, old, new in RETAIL_NAMES:
        for cat, base in NAME_LISTS:
            for lang in TT_LANGS:
                edits.append((cat, base + team, lang, ("name", old, new)))
    return edits


def fix_retail_text(data):
    """MES.PAC bytes with the retail text fixed. Each fix finds its old
    text or its new (a MES.PAC fixed before) and is refused otherwise; a
    name the real names replaced (real-names, after it) is left."""
    import mbb
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "MES.PAC")
        with open(path, "wb") as g:
            g.write(data)
        pack = mbb.MesPack(path)
    errors = []
    for cat, rid, lang, edit in retail_text_edits():
        text = pack.text(cat, lang, rid)
        if edit[0] == "name":
            if text == edit[1]:
                pack.set(cat, lang, rid, 0, edit[2])
            continue
        try:
            pack.set(cat, lang, rid, 0, tier_text_edit(text, lang, edit))
        except ValueError as e:
            errors.append("%d:%d language %d: %s" % (cat, rid, lang, e))
    out, _, _, build_errors = pack.build()
    if errors or build_errors:
        raise ValueError("retail-text: " + "; ".join(errors + build_errors))
    if pack.moved:
        raise ValueError("retail-text: a message file outgrows its slot in %s" % MES_FILE)
    return out


def target_retail_text(file, data):
    """A MES.PAC target with the retail text fixed in its own bytes."""
    return fix_retail_text(data) if norm(file) == norm(MES_FILE) else data


def plan_retail_text(f, img, adopted=()):
    """Jobs for --mod retail-text: MES.PAC's changed bytes, and the
    STATIONMES copies of the name lists it changes (or a MES.PAC target,
    `adopted`, that has them)."""
    if img.port is not None:
        return [], ["note: retail-text: the fixes are to PAL's text; the Japanese release "
                    "is left alone"]
    if norm(MES_FILE) in adopted:
        return [], ["note: retail-text: fixed the text in the target's %s" % MES_FILE]
    why = "retail-text: messages the retail game gets wrong"
    path, data = read_file(f, img, MES_FILE)
    new = fix_retail_text(data)
    if new == data:
        return [], ["note: %s already has the retail text fixes" % MES_FILE]
    jobs = diff_jobs(path, 0, data, new, why)
    old_entries, new_entries = mes_entries(data), mes_entries(new)
    for lang, pack in zip(TT_LANGS, STATIONMES):
        for cat in (3, 4):
            name = "%d_%d.mbb" % (cat, lang)
            (o, size), (n, nsize) = old_entries[name], new_entries[name]
            if data[o:o + size] != new[n:n + nsize]:
                jobs += pack_copy_jobs(f, img, pack, name, "%s#%s" % (MES_FILE, name),
                                       data[o:o + size], new[n:n + nsize], why)
    return jobs, []


# real-names: every league, competition, club and national team under its
# real name of the era (LMASTER full and max; DOC/LMASTER_MOD.md#real-names).
# realnames.py holds the names and writes them into MES.PAC's name lists
# and the English messages that mention a competition. The lists grow, so
# their STATIONMES copies grow too: the switch brings MES.PAC as a whole
# file and needs --copies, like the third tier, whose text it follows
# (the tier's added sentences name the tiers' leagues).
def target_real_names(file, data):
    """A MES.PAC target with the real names in its own bytes."""
    import realnames
    return realnames.apply(data)[0] if norm(file) == norm(MES_FILE) else data


def file_real_names(f, img, dat):
    """[(target, data)] for --mod real-names: MES.PAC as the disc has it,
    for target_real_names to write the names into."""
    return [(MES_FILE, read_file(f, img, MES_FILE)[1])]


def plan_real_names(f, img, adopted=()):
    """--mod real-names writes no bytes of its own: its MES.PAC is a whole
    file (file_real_names), which target_real_names edits."""
    if img.port is not None:
        raise ValueError("real-names is made for the PAL text only")
    return [], ["note: real-names: put the names in %s" % MES_FILE]


# own-stadium: my club's stadium takes my name, "<name> Stadium", in place
# of the city's (LMASTER full and max, the user's choice, 2026-10-30).
# Msg::VarBuf_MakeMyStadium (SLES 0x11eaf8) builds the stadium name,
# variable slot 9, which category 10's message 11001 shows, as
# snprintf("%s %s", slot 3, the word "Stadium"); slot 3 is the city. Slot
# 0 is the name typed at the start (SetOwnerName_Keyboard). The slot is
# the argument of GetVariableBuffer at 0x11eafc. A new career builds the
# stadium name before the name is typed (slot 0 blank: "  Stadium", read
# over PINE, user report 2026-10-31), so SetOwnerName_Keyboard (0x11ec58)
# ends by jumping to VarBuf_MakeMyStadium instead of returning: $ra is
# already restored and the delay slot pops the frame, so the stadium's
# own return goes back to the caller. A load rebuilds it from the saved
# slot 0 anyway (SAVEPRG.REL 0x32f24).
OWN_STADIUM_AT = 0x11eafc
OWN_STADIUM_OLD, OWN_STADIUM_NEW = 0x24040003, 0x24040000   # addiu $a0, $zero, 3 -> 0
OWN_NAME_RETURN = 0x11ec74                                  # jr $ra -> j VarBuf_MakeMyStadium
OWN_STADIUM_FUNC = 0x11eaf8


def plan_own_stadium(f, img):
    """Jobs for --mod own-stadium."""
    func = OWN_STADIUM_FUNC
    if img.port is not None:            # the jump's target in the other build
        import gamever
        func = gamever.at(img.port.copy(JP_EXE_FILE), func)
    words = [(SLES_FILE, OWN_STADIUM_AT - 0xff000, struct.pack("<I", OWN_STADIUM_OLD),
              struct.pack("<I", OWN_STADIUM_NEW),
              "%s 0x%x (my stadium: my name, not my city)" % (SLES_FILE, OWN_STADIUM_AT)),
             (SLES_FILE, OWN_NAME_RETURN - 0xff000, struct.pack("<I", 0x03e00008),
              struct.pack("<I", 0x08000000 | (func >> 2)),
              "%s 0x%x (my stadium rebuilt once my name is typed)" % (SLES_FILE, OWN_NAME_RETURN))]
    return word_jobs(f, img, "own-stadium", words)


def plan_third_tier(f, img, adopted=()):
    """Jobs for --mod third-tier: the code segment, the bigger save and its
    past records, clubs 442-459, their lists, the tiers' seasons and the
    one-season game over, as one switch (the files come from
    file_third_tier, and its text goes into MES.PAC through
    target_tier_text)."""
    if img.port is not None:
        raise ValueError("third-tier is made for the PAL executable only")
    return word_jobs(f, img, "third-tier",
                     code_segment_words(f, img) + save_grow_words(f, img) + past_record_words()
                     + tier_clubs_words(f, img) + tier_lists_words(f, img)
                     + tier_uids_words(f, img) + list(ONE_SEASON_END))


def file_third_tier(f, img, dat):
    """[(target, data)] for --mod third-tier: OTEAMMEMBER.TBB with the 18
    squads, the five schedule files, and MES.PAC as the disc has it, for
    target_tier_text to write the text into (a MES.PAC target takes it
    there instead)."""
    return (file_tier_clubs(f, img, dat) + file_tier_uids(f, img, dat)
            + [(MES_FILE, read_file(f, img, MES_FILE)[1])])


# fanbase: a big fanbase counts for more. Merchandise sales start from a
# base by the sum of pwkTeam_Supporter over the 13 regions (SIMPRG.REL
# 0x165598): 17 {threshold, base} pairs at 0x1d9ec8, from 800 (under
# 10,001) to 10,000 (over 10,000,000). Each base is scaled from x0.5 at
# the bottom to x3 at the top, evenly on a log scale. Walk-up crowds
# (pwkUnkei_GetAllAudience 0x272128) and season-ticket demand
# (pwkUnkei_GetExpectSeat 0x2727c8) both start from home popularity / 10
# x 130 + (k + 1) x 3,000: 130 becomes 195 and 3,000 becomes 1,500. A TV
# offer (SIMPRG.REL 0x163a10) is x0.9, 0.95, 1.0, 1.05 or 1.15 by home
# popularity in fifths; it becomes x0.75, 0.875, 1.0, 1.125 or 1.25. Each
# factor is a double built in $s1 by 7 instructions; the new ones need 2
# (ori, then dsll32 by 14, as the 1.0 at 0x163a34 is built) and 5 nops.
MERCH_TABLE, MERCH_ROWS = 0x1d9ec8, 17
MERCH_TOP_X, MERCH_BOTTOM_X = 3.0, 0.5
# (top base, bottom base) of each build's retail table and of the new one.
# The Japanese table holds half the PAL bases, so its retail bottom equals
# the new PAL bottom: both ends tell them apart.
MERCH_RETAIL = ((10000, 800), (5000, 400))  # PAL, Japanese
TV_TAIL = {5: (0x00118cb8, 0x3631cccc, 0x00118c38, 0x3631cccc, 0x00118b38, 0x36310ccd),
           9: (0x00118c38, 0x36319999, 0x00118c38, 0x36319999, 0x00118bb8, 0x36312666)}
TV_POP = ((0x163a60, 0xffb3, 5, 0xffa0, "0.9 -> 0.75"), (0x163a90, 0xffb9, 9, 0xffb0, "0.95 -> 0.875"),
          (0x163ad8, 0xffc3, 5, 0xffc8, "1.05 -> 1.125"), (0x163b14, 0xffc9, 9, 0xffd0, "1.15 -> 1.25"))
FANBASE_CROWDS = (
    sles_word(0x2722d8, 0x24060082, 0x240600c3, "crowds: popularity / 10 x 195"),
    sles_word(0x2722f0, 0x24020bb8, 0x240205dc, "crowds: (k + 1) x 1,500"),
    sles_word(0x2728ec, 0x24060082, 0x240600c3, "season tickets: popularity / 10 x 195"),
    sles_word(0x2728f0, 0x24020bb8, 0x240205dc, "season tickets: (k + 1) x 1,500"),
)


def merch_table(old):
    """(old, new) bytes of the merchandise base table, from its bytes in
    SIMPRG.REL; ValueError when its bottom base is neither the retail nor
    the new one."""
    off = MERCH_TABLE
    pairs = [struct.unpack_from("<2I", old, 8 * i) for i in range(MERCH_ROWS)]
    ends = (pairs[0][1], pairs[-1][1])
    if ends in [(round(t * MERCH_TOP_X), round(b * MERCH_BOTTOM_X)) for t, b in MERCH_RETAIL]:
        return old, old
    if ends not in MERCH_RETAIL or pairs[-1][0] != 0:
        raise ValueError("fanbase: SIMPRG.REL 0x%x's bases run %d-%d, not a retail table's "
                         "(%s); not the retail overlay?" % (off, ends[0], ends[1], ", ".join(
                             "%d-%d" % e for e in MERCH_RETAIL)))
    step = (MERCH_BOTTOM_X / MERCH_TOP_X) ** (1 / (MERCH_ROWS - 1))
    new = b"".join(struct.pack("<2I", t, round(v * MERCH_TOP_X * step ** i))
                   for i, (t, v) in enumerate(pairs))
    return old, new


def plan_fanbase(f, img):
    """Jobs for --mod fanbase."""
    if img.kind != "disc image":
        raise ValueError("fanbase patches SLES_541.51 and DLL/SIMPRG.REL, so it needs the "
                         "whole disc image, not %s" % img.kind)
    old, new = merch_table(read_at(f, img, NEGO_FILE, MERCH_TABLE, 8 * MERCH_ROWS))
    words = list(FANBASE_CROWDS) + [
        (NEGO_FILE, MERCH_TABLE, old, new, "%s 0x%x (merchandise base by supporters)"
         % (NEGO_FILE, MERCH_TABLE))]
    for off, old_hi, tail, new_hi, what in TV_POP:
        words.append((NEGO_FILE, off,
                      struct.pack("<7I", 0x34110000 | old_hi, *TV_TAIL[tail]),
                      struct.pack("<7I", 0x34110000 | new_hi, 0x00118bbc, 0, 0, 0, 0, 0),
                      "%s 0x%x (TV offer popularity factor %s)" % (NEGO_FILE, off, what)))
    return word_jobs(f, img, "fanbase", words)


# merch-costs: dearer merchandise stock. The goods screen (SIMPRG.REL
# 0xbcca0) prices a unit at shop price x 30 / 100 (the addiu at 0xbcce4)
# and a lot at unit cost x lot x a discount / 100, the discounts 100, 95,
# 90, 85, 80, 75, 70, 60 for the 8 lots at 0x1d10d8 (u32 each). A unit
# costs half its price, and each discount is half the old one (rounded up),
# so the biggest lot gets 20% off (80) rather than 40%.
MERCH_DISCOUNTS = 0x1d10d8
MERCH_DISCOUNT_OLD = (100, 95, 90, 85, 80, 75, 70, 60)
MERCH_DISCOUNT_NEW = tuple(100 - (100 - d + 1) // 2 for d in MERCH_DISCOUNT_OLD)
MERCH_COSTS = (
    simprg_word(0xbcce4, 0x2404001e, 0x24040032, "goods: a unit costs price x 50 / 100"),
    (NEGO_FILE, MERCH_DISCOUNTS, struct.pack("<8I", *MERCH_DISCOUNT_OLD),
     struct.pack("<8I", *MERCH_DISCOUNT_NEW),
     "%s 0x%x (goods lot discounts down to 80%%)" % (NEGO_FILE, MERCH_DISCOUNTS)),
)


def plan_merch_costs(f, img):
    """Jobs for --mod merch-costs."""
    return word_jobs(f, img, "merch-costs", MERCH_COSTS)


# pr-costs: PR events twice as dear. plClubEvent_GetCost (SLES 0x20dee0) is
# the record's +0x14 x 300 (the addiu at 0x20deec), and the booking
# (SIMPRG.REL 0xa3958, paid at 0xa2a2c as payment 22) and both refunds
# (0x45bb4, 0x49690) ask it, so x 600 doubles all three.
PR_COSTS = (
    sles_word(0x20deec, 0x2405012c, 0x24050258, "PR event cost x 600"),
)


def plan_pr_costs(f, img):
    """Jobs for --mod pr-costs."""
    return word_jobs(f, img, "pr-costs", PR_COSTS)


# mobile-site: PR event 37, Renew Mobile Site, back in the list.
# plClubEvent_GetList (SLES 0x20e488) clears the event's flag after its
# checks (beql $s1, $a3 at 0x20e864, $a3 = 37, with sw $zero, 0xa4($sp),
# flag 37, in the delay slot), so the event is never offered although its
# records are complete (DOC/CLUBEVENT_FORMAT.md). A nop in the delay slot
# leaves it to the record's own rules, like Renew Home Page's.
MOBILE_SITE = (
    sles_word(0x20e868, 0xafa000a4, 0x00000000, "PR event 37 no longer cleared"),
)


def plan_mobile_site(f, img):
    """Jobs for --mod mobile-site."""
    return word_jobs(f, img, "mobile-site", MOBILE_SITE)


# overseas-pop: the overseas popularity factor by your best player's rank
# from the region (0x268e70 indexes 16 floats at 0x554ec8 by it) runs
# 1.02, 1.05, 10.8, 1.11, ... in steps of 0.03; the third is 1.08 with
# the decimal point one place off (DOC/ECONOMY.md#supporter-popularity).
OVERSEAS_POP = (
    sles_word(0x554ed0, 0x412ccccd, 0x3f8a3d71, "overseas popularity factor, rank 2: 10.8 -> 1.08"),
)


def plan_overseas_pop(f, img):
    """Jobs for --mod overseas-pop."""
    return word_jobs(f, img, "overseas-pop", OVERSEAS_POP)


# cup-last16: the title popularity (0x268858) gives its 4th points column
# to places 8-15 when the cup is 34 (European League) and to places 16-31
# when it is 35 (European Club Cup), so the Club Cup paid its last 32 and
# not its last 16 (DOC/ECONOMY.md#titles). Both branches end in a shared
# movz $s2, $a0 ($a0 = 4) on $v1 = cup ^ id. Now places 8-15 test
# cup < 36 (sltiu: 1 for 34 and 35; the table's cups are 34-43) and
# places 16-31 get 0, with movn in place of the movz.
CUP_LAST16 = (
    sles_word(0x26894c, 0x38630022, 0x2c630024, "title points, places 8-15: cup 34 or 35"),
    sles_word(0x26896c, 0x38630023, 0x0000182d, "title points, places 16-31: none"),
    sles_word(0x268970, 0x0083900a, 0x0083900b, "title points: movz -> movn"),
)


def plan_cup_last16(f, img):
    """Jobs for --mod cup-last16."""
    return word_jobs(f, img, "cup-last16", CUP_LAST16)


# camp-costs and tour-costs: the camp and tour screens (SIMPRG.REL 0xa3b00,
# 0xa3bf4) price a booking from u32 rates in SIMPRG.REL, x the squad's
# players x 300 (x 1/2 for a tour), the business cycle and the sponsor
# discount (0x4ded8, 0x4e080), and book it as payment 21. A camp's rate is
# by its level (0-7) and region, 8 rows of 14 at 0x1ce4e8; a tour's by its
# region + 1, 14 at 0x1ce6c0 (entry 0 is never used). Each switch scales
# its table.
RATE_TABLES = {"camp-costs": (0x1ce4e8, 8 * 14, 400, 2),
               "tour-costs": (0x1ce6c0, 14, 1000, 3)}


def plan_rates(f, img, switch):
    if img.kind != "disc image":
        raise ValueError("%s patches DLL/SIMPRG.REL, so it needs the whole disc image, not %s"
                         % (switch, img.kind))
    off, count, retail, x = RATE_TABLES[switch]
    old = read_at(f, img, NEGO_FILE, off, 4 * count)
    rates = struct.unpack("<%dI" % count, old)
    if rates[0] == retail * x:
        return [], ["note: %s is already applied" % switch]
    if rates[0] != retail:
        raise ValueError("%s: SIMPRG.REL 0x%x holds %d, expected %d; not the retail overlay?"
                         % (switch, off, rates[0], retail))
    new = struct.pack("<%dI" % count, *[r * x for r in rates])
    return [Job(NEGO_FILE, off, new, "%s 0x%x (%s rates x %d)" % (
        NEGO_FILE, off, switch.split("-")[0], x), switch)], []


def plan_camp_costs(f, img):
    """Jobs for --mod camp-costs."""
    return plan_rates(f, img, "camp-costs")


def plan_tour_costs(f, img):
    """Jobs for --mod tour-costs."""
    return plan_rates(f, img, "tour-costs")


# --- the switch table ----------------------------------------------------------

# (name, plan, files it edits, description), in the order they run. A
# target may not write a file a chosen switch edits. editor.py draws one
# box per row.
SWITCHES = (
    ("skip-tutorial", plan_skip_tutorial, [p for p, _ in SKIP_SCRIPTS],
     "Skip the tutorial (for testing)"),
    ("sponsor-negotiation", plan_sponsor_negotiation, [NEGO_FILE],
     "Sponsor negotiation: negotiate with the main sponsor, as in the Japanese release"),
    ("rival-manager", plan_rival_manager, [SLES_FILE],
     "Rival's manager: the rival gets the manager of its own style"),
    ("press-tendency", plan_press_tendency, [GAME_FILE],
     "Pressing: every level of a player's press tendency counts in matches "
     "(levels 2-4 all acted as 1)"),
    ("national-cups", plan_national_cups, [SCHEDULE_FILE, STATION_FILE, LIST_FILE] + LIST_PACKS,
     "National cups a turn earlier, so the World National Cup's results can be viewed"),
    ("league-balance", plan_league_balance, [COMPE_FILE],
     "League schedules: no club plays more than two games running at home or away"),
    ("camp-types", plan_camp_types, [CAMP_LIST_FILE],
     "Training camps: each camp trains and checks its themes as its own type"),
    ("camp-cities", plan_camp_cities, [CAMP_LIST_FILE, CAMP_EXPLANE_FILE],
     "Training camps: Liverpool, Manchester and five more English camps in their own towns"),
    ("camp-santiago", plan_camp_santiago, [CAMP_EXPLANE_FILE],
     "Training camps: Santiago's camp gets its description"),
    ("camp-clubs", plan_camp_clubs, [NEGO_FILE],
     "Training camps: Canberra's last two clubs appear in its list"),
    ("drill-names", plan_drill_names, [MES_FILE] + DRILL_PACKS,
     "Training: drills 75-86 show their own names (PAL's were one early, with a jackknife)"),
    ("injury-value", plan_injury_value, [SLES_FILE],
     "Injuries: an 18-month injury can't come out as short as a light one "
     "(kind 6's value 1600 -> 16001)"),
    ("injury-row", plan_injury_row, [SLES_FILE],
     "Injuries: a player of 35 or more at full fatigue reads the last row of the "
     "injury tables, not the bytes after them"),
    ("vpf-styles", plan_vpf_styles, [SAVE_FILE],
     "Virtua Pro Football import: an edit player's best play styles come in "
     "(the import's sort never sorted)"),
    ("season-status", plan_season_status, [SLES_FILE],
     "Season tickets: bigger clubs sell more of them, as the status bands intend "
     "(every club over 10,000 status was stuck at the second band)"),
    ("pr-cycle", plan_pr_cycle, [SLES_FILE],
     "PR events: the business cycle changes their chance as its table intends "
     "(an average economy took 10% off every event)"),
    ("mobile-site", plan_mobile_site, [SLES_FILE],
     "PR events: the cut Renew Mobile Site can be booked again (from 2010-11, like "
     "Renew Home Page)"),
    ("overseas-pop", plan_overseas_pop, [SLES_FILE],
     "Popularity: a rank-2 player from a region no longer makes your popularity there "
     "grow ten times as fast (10.8 -> 1.08)"),
    ("cup-last16", plan_cup_last16, [SLES_FILE],
     "Popularity: reaching the European Club Cup's last 16 earns points, its last 32 "
     "no longer does"),
    ("facility-tiers", plan_facility_tiers, [COMMON_FILE, STATION_FILE],
     "Harder economy: bigger stadiums, club houses and grounds cost much more to build "
     "and keep up; other facilities twice as much"),
    ("wider-tickets", plan_wider_tickets, [NEGO_FILE, SLES_FILE],
     "Harder economy: ticket prices up to £80, with crowds falling off above £50"),
    ("dearer-ads", plan_dearer_ads, [NEGO_FILE, SLES_FILE],
     "Harder economy: advertising buys half as much per pound, up to £10M a season"),
    ("sponsor-fees", plan_sponsor_fees, [NEGO_FILE],
     "Harder economy: sponsor fees over £2M keep only half of the rest"),
    ("tv-fees", plan_tv_fees, [NEGO_FILE],
     "Harder economy: TV offers over £2M keep only half of the rest"),
    ("season-demand", plan_season_demand, [SLES_FILE],
     "Harder economy: half as many fans buy season tickets"),
    ("injury-odds", plan_injury_odds, [SLES_FILE],
     "Balance: injuries of six months or longer about twice as common, rested players too"),
    ("injury-lines", plan_injury_lines,
     [SLES_FILE, MES_FILE] + sum(INJURY_TEXT_PACKS.values(), []),
     "Injuries: the cut \"two months\" and \"nine months\" condition lines come back"),
    ("overseas-bases", plan_overseas_bases, [SIM_FILE] + LIST_PACKS,
     "Balance: overseas bases, their investment and upkeep cost twice as much"),
    ("transfer-fees", plan_transfer_fees, [SLES_FILE],
     "Balance: transfer fees twice as high, up to £250M"),
    ("fee-tiers", plan_fee_tiers, [SLES_FILE],
     "Balance: transfer fees by player rank: lesser players x2, the best up to x3"),
    ("slow-reputation", plan_slow_reputation, [SLES_FILE],
     "Balance: club status (reputation) rises half as fast; losses stay"),
    ("third-tier", plan_third_tier,
     [SLES_FILE, SAVE_FILE, NEGO_FILE, DISC + "DLL/YRSTPRG.REL", OTEAM_FILE, MES_FILE]
     + list(TIER_UID_FILES),
     "LMASTER full: a hidden third tier under each second division; last place down, the "
     "tier's winner up, the game over after one season last; new saves; needs --copies"),
    ("fanbase", plan_fanbase, [SLES_FILE, NEGO_FILE],
     "Balance: a bigger fanbase sells more merchandise and draws more fans and TV money"),
    ("merch-costs", plan_merch_costs, [NEGO_FILE],
     "Balance: merchandise stock costs half its price to make, with bulk discounts of 20% at most"),
    ("pr-costs", plan_pr_costs, [SLES_FILE],
     "Balance: PR events cost twice as much"),
    ("camp-costs", plan_camp_costs, [NEGO_FILE],
     "Balance: training camps cost twice as much"),
    ("tour-costs", plan_tour_costs, [NEGO_FILE],
     "Balance: tours cost three times as much"),
    ("retail-text", plan_retail_text, [MES_FILE] + STATIONMES,
     "Text: the Game Over conditions for Spain and the Netherlands name their own leagues, "
     "the Spanish intro's 216 clubs are 26, and AL-Hyde is Al-Hyde"),
    ("real-names", plan_real_names, [MES_FILE],
     "LMASTER full: every league, competition, club, stadium and national team under its "
     "real name of the era, in five languages; needs --copies"),
    ("own-stadium", plan_own_stadium, [SLES_FILE],
     "Names: your club's stadium is named after you (\"<your name> Stadium\"), not your city"),
    ("special-stadium", plan_special_stadium,
     [COMMON_FILE, STATION_FILE, STADIUM_DATA_FILE] + STADIUM_DATA_PACKS,
     "Stadiums: the Special stadium holds 100,000, not 110,000"),
    ("real-grounds", plan_real_grounds,
     [SIM_FILE, STADIUM_DATA_FILE, BUILD_STADIUM_FILE] + LIST_PACKS + STADIUM_DATA_PACKS,
     "Stadiums: every club plays at a ground of its real 2005-06 size (to 5,000), with a "
     "look to fit (the biggest bowl only for 80,000 and up), clubs of one size varied"),
    ("sponsor-boards", plan_sponsor_boards, [BUILD_STADIUM_FILE],
     "Stadiums: every ground's advert boards drawn afresh from all 205 sponsors, so "
     "they vary"),
    ("launcher", plan_launcher, [LAUNCHER[0]],
     "Debug menu: boot into the developers' launcher of test modules and viewers"),
    ("mod-saves", plan_mod_saves, [SLES_FILE],
     "Separate saves: careers to BESLES-54151-F (M with a difficulty switch), VS data to "
     "-V, which the original game "
     "never opens"),
)
SWITCH_NAMES = [s[0] for s in SWITCHES]

# Switches that also edit a target's own bytes, so that a file both write
# (a league build's SCHEDULE_SYSTEM.PAC) takes the switch's change: name ->
# (hook(file, data) -> data, the files it applies to, other files the switch
# then leaves to the target's --copies). The plan is called with the files
# targets wrote, and those others, as `adopted`.
TARGET_HOOKS = {"national-cups": (target_national_cups, [SCHEDULE_FILE, LIST_FILE],
                                  [STATION_FILE] + LIST_PACKS),
                "league-balance": (target_league_balance, [COMPE_FILE], []),
                "camp-types": (target_camp_types, [CAMP_LIST_FILE], []),
                "camp-cities": (target_camp_cities, [CAMP_LIST_FILE, CAMP_EXPLANE_FILE], []),
                "camp-santiago": (target_camp_santiago, [CAMP_EXPLANE_FILE], []),
                "drill-names": (target_drill_names, [MES_FILE], DRILL_PACKS),
                "injury-lines": (target_injury_lines, [MES_FILE],
                                 sum(INJURY_TEXT_PACKS.values(), [])),
                "overseas-bases": (target_overseas_bases, [SIM_FILE], LIST_PACKS),
                # The retail fixes before the tier's text, which finds them in
                # place; the real names last, over the tier's sentences too.
                "retail-text": (target_retail_text, [MES_FILE], STATIONMES),
                "third-tier": (target_tier_text, [MES_FILE], []),
                "real-names": (target_real_names, [MES_FILE], []),
                "special-stadium": (target_special_stadium, [COMMON_FILE, STADIUM_DATA_FILE],
                                    [STATION_FILE] + STADIUM_DATA_PACKS),
                "real-grounds": (target_real_grounds,
                                 [SIM_FILE, STADIUM_DATA_FILE, BUILD_STADIUM_FILE],
                                 LIST_PACKS + STADIUM_DATA_PACKS),
                "sponsor-boards": (target_sponsor_boards, [BUILD_STADIUM_FILE], [])}
# Hooks that also take the file as DAT holds it (or the image, without
# --dat), to keep the target's own edits row by row.
HOOKS_WITH_OLD = ("real-grounds", "sponsor-boards")

# One switch per feature: parts that need each other are one switch
# (DOC/LMASTER_MOD.md, the switch levels). Switches that need another switch, that
# write whole files (file_<switch>(f, img, dat) -> [(target, data)]),
# whose files have PRELOAD copies the game loads instead (--copies), that
# turn on others (a bigger save needs saves of its own), and old names.
SWITCH_NEEDS = {}
SWITCH_FILES = {"third-tier": file_third_tier, "real-names": file_real_names}
SWITCH_COPIES = ("third-tier", "real-names")
SWITCH_IMPLIES = {"third-tier": ("mod-saves",), "real-grounds": ("special-stadium",)}
SWITCH_ALIASES = {name: "third-tier" for name in ("save-expand", "tier-clubs", "tier-lists",
                                                  "tier-uids", "one-season-end")}
# The switch levels: editions are made of groups, groups of switches, and
# --mod takes a name of any level. A group holds features that each work
# alone; every switch is in exactly one group. The test tools are a group
# of their own, in no edition. editor.py's Build tab draws this tree.
GROUPS = (       # (name, title, switches)
    ("training-fixes", "Training fixes",
     ("camp-types", "camp-cities", "camp-santiago", "camp-clubs", "drill-names")),
    ("injury-fixes", "Injury fixes", ("injury-value", "injury-row")),
    ("club-fixes", "Club fixes",
     ("sponsor-negotiation", "season-status", "pr-cycle", "mobile-site", "overseas-pop",
      "cup-last16")),
    ("match-fixes", "Match and import fixes",
     ("rival-manager", "press-tendency", "national-cups", "vpf-styles")),
    ("text-fixes", "Text fixes", ("retail-text",)),
    ("harder-economy", "Harder economy",
     ("facility-tiers", "wider-tickets", "dearer-ads", "sponsor-fees", "tv-fees",
      "season-demand")),
    ("balance", "Balance",
     ("injury-odds", "overseas-bases", "transfer-fees", "fee-tiers", "slow-reputation",
      "fanbase", "merch-costs", "pr-costs", "camp-costs", "tour-costs")),
    ("leagues", "Leagues", ("league-balance", "third-tier")),
    ("restorations", "Restored content", ("injury-lines",)),
    ("names", "Real names", ("real-names", "own-stadium")),
    ("stadiums", "Stadiums", ("special-stadium", "real-grounds", "sponsor-boards")),
    ("saves", "Separate saves", ("mod-saves",)),
    ("test-tools", "Test tools", ("skip-tutorial", "launcher")),
)
# LMASTER lite is the fixes. LMASTER full adds the leagues, the restored
# content and its own saves; LMASTER max adds the difficulty groups to it
# (the user's split, 2026-10-27). Full and max save careers under their
# own letters (SAVE_LETTERS), so neither mixes with the retail game's.
LITE_GROUPS = ("training-fixes", "injury-fixes", "club-fixes", "match-fixes", "text-fixes")
FULL_GROUPS = LITE_GROUPS + ("leagues", "restorations", "names", "stadiums", "saves")
DIFFICULTY_GROUPS = ("harder-economy", "balance")
EDITIONS = (     # (name, title, groups)
    ("lmaster-lite", "LMASTER lite (fixes only)", LITE_GROUPS),
    ("lmaster-full", "LMASTER full (fixes, third tier, restored content; F saves)",
     FULL_GROUPS),
    ("lmaster-max", "LMASTER max (full and the difficulty groups; M saves)",
     FULL_GROUPS + DIFFICULTY_GROUPS),
)
GROUP_SWITCHES = {name: switches for name, _, switches in GROUPS}
EDITION_GROUPS = {name: groups for name, _, groups in EDITIONS}
# Every name --mod takes for several switches at once.
SWITCH_GROUPS = dict(GROUP_SWITCHES)
SWITCH_GROUPS.update((name, sum((GROUP_SWITCHES[g] for g in groups), ()))
                     for name, groups in EDITION_GROUPS.items())
SWITCH_GROUPS["lmaster"] = SWITCH_GROUPS["lmaster-lite"]     # the name before the split
assert sorted(sum(GROUP_SWITCHES.values(), ())) == sorted(SWITCH_NAMES), \
    "every switch belongs to exactly one group"
DIFFICULTY = set(sum((GROUP_SWITCHES[g] for g in DIFFICULTY_GROUPS), ()))


def edition_letter(mods):
    """The career save letter --mod-saves writes for the switches `mods`:
    max's with any difficulty switch, full's without."""
    return SAVE_LETTERS["max" if DIFFICULTY & set(mods) else "full"]


def implied(names):
    """`names` with the switches they turn on (SWITCH_IMPLIES)."""
    out = set(names)
    for name in list(out):
        out.update(SWITCH_IMPLIES.get(name, ()))
    return out


def parse_mods(values):
    """The switch names in --mod values ('a,b'; edition and group names allowed)."""
    out = set()
    for v in values:
        for name in filter(None, v.lower().split(",")):
            name = SWITCH_ALIASES.get(name, name)
            if name in SWITCH_GROUPS:
                out.update(SWITCH_GROUPS[name])
            elif name in SWITCH_NAMES:
                out.add(name)
            else:
                raise SystemExit("--mod %s: no such switch (%s)" % (
                    name, ", ".join(SWITCH_NAMES + sorted(SWITCH_GROUPS))))
    return implied(out)


def mod_names(switches):
    """The shortest --mod names for the set `switches` (with what they
    imply): the biggest edition it holds, then whole groups, then single
    switches, each in table order. parse_mods(mod_names(s)) == implied(s)."""
    left = implied(switches)
    out = []
    for name, _, groups in sorted(EDITIONS, key=lambda e: -len(e[2])):
        if set(SWITCH_GROUPS[name]) <= left:
            out.append(name)
            left -= set(SWITCH_GROUPS[name])
            break
    for name, _, members in GROUPS:
        if left and set(members) <= left:
            out.append(name)
            left -= set(members)
    return out + [name for name in SWITCH_NAMES if name in left]


def rebuild_entry_targets(img, index, image, pairs):
    """Entry targets of self-describing archives outside PRELOAD that change
    size become one whole-archive target per archive: the archive as the
    image holds it, rebuilt with pac.build_binpac around the new entries.
    Its header then reaches its .HED copies (--copies), the file moves if
    it needs more sectors, and an archive the executable indexes
    (EXE_INDEXED) gets that index rewritten."""
    import pac
    groups, out = {}, []
    for target, src, data in pairs:
        if "#" in target:
            u = index.resolve(target) if index is not None else None
            if u is not None and u.kind == "entry" and not repackable(u.file) and                     len(data) != u.size:
                groups.setdefault(norm(u.file), (u.file, []))[1].append((u, src, data))
                continue
        out.append((target, src, data))
    whole = {norm(resolve_target(img, index, t)[0]) for t, _, _ in out if "#" not in t}
    with open(image, "rb") as f:
        for key, (file, edits) in groups.items():
            if key in whole:
                raise SystemExit("%s: written whole and as single entries in the same run; "
                                 "patch one or the other" % file)
            cur = read_at(f, img, file, 0, img.entry(file).size)
            try:
                h, blobs = pac.binpac_blobs(cur)
            except (ValueError, struct.error):
                raise SystemExit("%s isn't a self-describing archive, so %s can't change "
                                 "size" % (file, edits[0][0].label))
            for u, src, data in edits:
                blobs[u.index] = data
            new = pac.build_binpac(cur[:h.header_size], blobs)
            out.append((file, "%s rebuilt around %s" % (file, ", ".join(
                "%s (%s)" % (u.label, src) for u, src, _ in edits)), new))
    return out


def resolve_target(img, index, target):
    """(file, offset in file, size, label) for 'PATH' or 'PATH#entry'."""
    if "#" in target:
        if index is None:
            raise SystemExit("%s: archive entries need the DAT index (--dat)" % target)
        u = index.resolve(target)
        return u.file, u.off, u.size, u.label
    e = img.entry(target)
    return e.path, 0, e.size, e.path


def read_at(f, img, file, off, size):
    """`size` bytes of `file` at `off`, an offset in the PAL file for the
    code (moved to the other build's file on the Japanese disc)."""
    if img.port is not None:
        file, off = img.port.map(file, off, size)
    return read_raw(f, img, file, off, size)


def read_raw(f, img, file, off, size):
    """`size` bytes of the image's `file` at `off`, as it is."""
    f.seek(img.offset(img.entry(file)) + off)
    return f.read(size)


def plan_copies(img, index, f, file, off, old, new, write_copies, packs):
    """Copy jobs (with write_copies) and notes for every unit of `file` that
    lies inside [off, off + len(new)) and differs between `old` (the DAT
    original) and `new`. Copies inside PRELOAD packs go to `packs` instead.

    Units are DAT's original entries, so an entry that the new file moved
    or resized (mbb.py grows message files into their slot) is compared
    over its old range only, and its new bytes are taken from the new
    header. A PRELOAD pack holding a copy is rebuilt around the new size;
    any other copy is a fixed-size slot, so it is reported instead."""
    import pac
    moved = {}
    if off == 0 and new[10:16] == b"BINPAC":
        try:
            moved = {i: (o, s) for i, (o, s, _, _) in enumerate(pac.BinPac(new).entries)}
        except (ValueError, struct.error):
            pass
    jobs, notes, seen = [], [], set()
    for u in index.units(file):
        lo, hi = u.off - off, u.off - off + u.size
        if lo < 0 or hi > len(old):
            continue
        if lo == 0 and hi == len(old):
            blob = new                  # the target itself, whatever its new size
        elif u.kind == "entry" and u.index in moved:
            o, s = moved[u.index]
            blob = new[o - off:o - off + s]
        else:
            blob = new[lo:hi]
        if blob == old[lo:hi]:
            continue
        resized = len(blob) != u.size
        named, other = index.copies(u)
        for c in named:
            if (c.file.upper(), c.off) in seen:
                continue
            seen.add((c.file.upper(), c.off))
            if not write_copies:
                notes.append("warning: %s changes, but %s holds a copy of it" % (u.label, c.label))
                continue
            if c.kind == "entry" and repackable(c.file):
                packs.add(c.file, c.index, blob, old[lo:hi], c.label, "copy of " + u.label)
                continue
            if resized:
                notes.append("warning: %s is now %d bytes (was %d); its copy %s is a "
                             "fixed-size slot, so it keeps the old data" % (
                                 u.label, len(blob), u.size, c.label))
                continue
            held = read_at(f, img, c.file, c.off, c.size)
            if held == blob:
                notes.append("note: %s already holds the new bytes" % c.label)
                continue
            if held != old[lo:hi]:
                notes.append("note: %s holds neither the original nor the new %s; left alone"
                             % (c.label, u.label))
                continue
            jobs.append(Job(c.file, c.off, blob, c.label, "copy of " + u.label))
        if other:
            notes.append("note: %s has the same bytes as %d unit%s with other names (%s%s); "
                         "not treated as copies" % (
                             u.label, len(other), "" if len(other) == 1 else "s",
                             ", ".join(x.label for x in other[:3]), ", ..." if len(other) > 3 else ""))
    if notes and not write_copies and any(n.startswith("warning") for n in notes):
        notes.append("hint: add --copies to write the new bytes into those copies too")
    return jobs, notes


# --- commands ----------------------------------------------------------------

def cmd_locate(image, paths):
    img = Image(image)
    print("%s: %s, %d files, ISO sector 0 at byte %#x" % (
        image, img.kind, len(img.files), img.iso_base))
    for p in paths:
        e = img.entry(p)
        print("  %-40s sector %7d  size %10d  bytes %#x-%#x" % (
            e.path, e.extent, e.size, img.offset(e), img.offset(e) + e.size))


def cmd_copies(dat, targets):
    index = Index(dat)
    for t in targets:
        base = index.resolve(t)
        units = [base] if "#" in t else sorted(index.units(base.file), key=lambda u: (u.off, -u.size))
        shown = 0
        for u in units:
            named, other = index.copies(u)
            if not named and not other:
                continue
            shown += 1
            print("%s" % u.label)
            for c in named:
                print("    copy       %s" % c.label)
            if other:
                print("    same bytes %s%s" % (", ".join(c.label for c in other[:4]),
                                              " (+%d more)" % (len(other) - 4) if len(other) > 4 else ""))
        if not shown:
            print("%s: no copies in %s" % (base.label, dat))


def copy_file(src, dst):
    total = os.path.getsize(src)
    done = shown = 0
    print("Copying %s to %s (%d MB)" % (src, dst, total >> 20), end="", flush=True)
    with open(src, "rb") as fi, open(dst, "wb") as fo:
        while buf := fi.read(CHUNK):
            fo.write(buf)
            done += len(buf)
            while shown < 10 * done // total:
                shown += 1
                print(" %d%%" % (shown * 10), end="", flush=True)
    print()
    shutil.copystat(src, dst)
    os.chmod(dst, 0o644)


def cmd_patch(image, out, in_place, args, dat, write_copies, renames=(), mods=()):
    pairs = parse_pairs(args)
    if cso.is_compressed(image):
        # The output is the decompressed image, patched in place from here on.
        if in_place:
            raise SystemExit("%s is a CSO/ZSO/CHD image; give an output .iso to patch into" % image)
        if os.path.abspath(out) == os.path.abspath(image):
            raise SystemExit("output is the input")
        cso.cmd_extract(image, out)
        image, out, in_place = out, None, True
    img = Image(image)
    global save_letter
    save_letter = edition_letter(mods)
    adopted = {}
    # Switches that need other switches, and switches that bring whole
    # files of their own (a file that grows), which then go the way of a
    # target: moved when it needs more sectors, copied with --copies.
    for name, needs in SWITCH_NEEDS.items():
        missing = [n for n in needs if name in mods and n not in mods]
        if missing:
            raise SystemExit("--mod %s needs --mod %s too" % (name, ",".join(missing)))
    for name in SWITCH_COPIES:
        if name in mods and not write_copies:
            raise SystemExit("--mod %s needs --copies (and --dat): the game loads the "
                             "PRELOAD copies of its files" % name)
    for name, func in SWITCH_FILES.items():
        if name not in mods:
            continue
        given = {norm(img.entry(t).path) for t, _, _ in pairs if "#" not in t}
        with open(image, "rb") as g:
            extra = func(g, img, dat)
        for target, data in extra:
            if norm(target) in given:
                # A file the switch's target hook edits: the target takes the
                # change (below), and the switch's own copy isn't needed.
                if name in TARGET_HOOKS and norm(target) in {norm(p) for p in TARGET_HOOKS[name][1]}:
                    continue
                raise SystemExit("--mod %s writes %s; don't patch it as a target too"
                                 % (name, target))
            pairs.append((target, "--mod " + name, data))
            adopted.setdefault(name, set()).add(norm(target))
    def original(file):
        """`file` as DAT holds it, or as the image does without --dat."""
        if dat:
            with open(os.path.join(dat, file), "rb") as g:
                return g.read()
        with open(image, "rb") as g:
            return read_file(g, img, file)[1]

    # Switches that edit a target's bytes do so before anything is planned,
    # so its copies (--copies) carry the change too; after the switches'
    # own files, so one switch's change lands on another's file (the third
    # tier's SCHEDULE_SYSTEM.PAC takes national-cups').
    for name, (hook, files, also) in TARGET_HOOKS.items():
        if name not in mods:
            continue
        for k, (target, src, data) in enumerate(pairs):
            if "#" in target:
                continue
            file = norm(img.entry(target).path)
            if file in {norm(p) for p in files}:
                if name in HOOKS_WITH_OLD:
                    pairs[k] = (target, src, hook(file, data, original(img.entry(target).path)))
                else:
                    pairs[k] = (target, src, hook(file, data))
                adopted.setdefault(name, set()).update({file} | {norm(p) for p in also})
    index = Index(dat) if dat else None
    if write_copies and index is None:
        raise SystemExit("--copies needs the DAT index (--dat)")
    pairs = rebuild_entry_targets(img, index, image, pairs)

    # Plan everything against the unmodified image before copying it.
    jobs, notes, packs = [], [], PackEdits()
    toc, moves = TocEdits(), Moves()
    # Files written whole: a copy that falls inside one (a schedule pack's
    # header, which repeats its .HED) is already in its new bytes.
    whole = {norm(resolve_target(img, index, t)[0]): d for t, _, d in pairs if "#" not in t}
    with open(image, "rb") as f:
        for target, src, data in pairs:
            file, off, size, label = resolve_target(img, index, target)
            if "#" in target and repackable(file):
                # Located by the pack's current header, and may change size.
                u = index.resolve(target)
                packs.add(file, u.index, data, None, label, src)
            elif len(data) == size:
                jobs.append(Job(file, off, data, label, src))
            elif "#" not in target and not file.startswith(DISC) and \
                    sectors(len(data)) == sectors(size):
                jobs.append(Job(file, 0, to_sector_end(data), label, src))
                toc.add(img, file, len(data))
            elif "#" in target:
                raise SystemExit("%s is %d bytes but %s is %d bytes" % (
                    src, len(data), label, size))
            elif not file.startswith(DISC):
                moves.add(file, data, label, src)   # needs more sectors
            else:
                raise SystemExit("%s is %d bytes but %s is %d bytes on the disc; files outside "
                                 "DATA.CVM keep their size" % (src, len(data), label, size))
            # Files outside DATA.CVM aren't in DAT, and nothing there copies them.
            if index is not None and not file.startswith(DISC):
                # Changes are judged against the unmodified data in DAT, so a
                # second run on an already patched image still finds them.
                with open(os.path.join(index.dat, file), "rb") as g:
                    if "#" in target:
                        u = index.resolve(target)
                        off = u.off
                        g.seek(off)
                        old = g.read(u.size)
                    else:
                        off, old = 0, g.read()
                cjobs, cnotes = plan_copies(img, index, f, file, off, old, data,
                                            write_copies, packs)
                for j in cjobs:
                    mine = whole.get(norm(j.file)) if j.file is not None else None
                    if mine is None or norm(j.file) == norm(file):
                        jobs.append(j)
                    elif mine[j.off:j.off + len(j.data)] != j.data:
                        raise SystemExit("%s: its copy in %s differs from that file's own "
                                         "new bytes" % (label, j.file))
                    else:
                        notes.append("%s: copy in %s already in that file's new bytes"
                                     % (label, j.file))
                notes += cnotes
        busy = {norm(j.file) for j in jobs if j.file is not None}
        clash = busy & set(packs.packs)
        if clash:
            raise SystemExit("%s: written whole and as single entries in the same run; "
                             "patch one or the other" % ", ".join(sorted(clash)))
        # The switches, before the PRELOAD packs are rebuilt: an edit inside a
        # pack this run rebuilds (its copies grew) becomes an entry edit of it.
        # The files the targets write, before the switches add theirs
        # (skip-tutorial and launcher both edit RootMainSeq.sqb).
        touched = {norm(j.file) for j in jobs if j.file is not None} | set(moves.files)
        for name, plan, files, _ in SWITCHES:
            if name not in mods:
                continue
            mine = adopted.get(name, set())
            clash = touched & ({norm(img.entry(p).path) if img.port and norm(p) == norm(
                PAL_EXE_FILE) else norm(p) for p in files} - mine)
            if clash:
                raise SystemExit("--mod %s edits %s; don't patch it as a target too"
                                 % (name, ", ".join(sorted(clash))))
            sjobs, snotes = plan(f, img, mine) if name in TARGET_HOOKS else plan(f, img)
            if img.port is not None:
                sjobs = img.port.jobs(sjobs)
            for j in sjobs:
                if j.file is not None and norm(j.file) in packs.packs:
                    packs.fold(f, img, j)
                else:
                    jobs.append(j)
            notes += snotes
        pjobs, pnotes = packs.plan(f, img, toc, moves)
        jobs += pjobs
        notes += pnotes
        clash = set(moves.files) & {norm(j.file) for j in jobs if j.file is not None}
        if clash:
            raise SystemExit("%s: moved, but also written in place in the same run"
                             % ", ".join(sorted(clash)))
        mjobs, mnotes = moves.plan(f, img, toc)
        jobs += mjobs + toc.jobs(f, img)
        notes += mnotes
        for r in renames:
            target, _, new = r.partition("=")
            jobs += plan_rename(f, img, target, new)
        # After the switches, which may patch other bytes of the executable.
        for target, _, data in pairs:
            file = norm(resolve_target(img, index, target)[0])
            if "#" not in target and file in EXE_INDEXED:
                ijobs, inotes = plan_exe_index(f, img, file, data)
                jobs += ijobs
                notes += inotes
        crc_before = None
        if img.kind == "disc image":
            e = img.entry(SLES_FILE)
            f.seek(img.offset(e))
            crc_before = pcsx2_crc(f.read(e.size))
    if index is None:
        notes.append("note: no DAT index (--dat), so copies elsewhere on the disc weren't checked")

    if in_place:
        target_path = image
    else:
        if os.path.abspath(out) == os.path.abspath(image):
            raise SystemExit("output is the input; use --in-place to patch it directly")
        copy_file(image, out)
        target_path = out
    with open(target_path, "r+b") as f:
        for j in jobs:
            pos = j.pos(img)
            f.seek(pos)
            old = f.read(len(j.data))
            changed = sum(1 for a, b in zip(old, j.data) if a != b) + len(j.data) - len(old)
            f.seek(pos)
            f.write(j.data)
            f.flush()
            f.seek(pos)
            if f.read(len(j.data)) != j.data:
                raise SystemExit("%s: read-back after writing %s does not match" % (target_path, j.label))
            print("%s: %s <- %s, %d bytes differ from the original%s" % (
                target_path, j.label, j.why, changed, "" if changed else " (no change)"))
    for n in notes:
        print(n)
    changed = []
    resized = len(toc.edits) - len(moves.files)
    if resized:
        changed.append("%d directory record%s resized" % (resized, "" if resized == 1 else "s"))
    if moves.files:
        changed.append("%d file%s moved to the end of DATA.ISO" % (
            len(moves.files), "" if len(moves.files) == 1 else "s"))
    if renames:
        changed.append("outer directory records renamed")
    print("%s: %d write%s; %s" % (
        target_path, len(jobs), "" if len(jobs) == 1 else "s",
        ", ".join(changed) or "table of contents untouched"))
    if crc_before is not None:
        e = img.entry(SLES_FILE)
        with open(target_path, "rb") as f:
            f.seek(img.offset(e))
            crc = pcsx2_crc(f.read(e.size))
        print("%s: PCSX2 CRC of the executable %08X%s; %s" % (
            target_path, crc,
            "" if crc == crc_before else " (was %08X)" % crc_before,
            "the retail CRC" if crc == RETAIL_CRC else
            "PCSX2 keeps this disc's settings and savestates as SLES-54151_%08X" % crc))


def cmd_verify(image, args):
    img = Image(image)
    ok = True
    with open(image, "rb") as f:
        for path, src, data in parse_pairs(args):
            e = img.entry(path)
            f.seek(img.offset(e))
            held = f.read(e.size)
            if held == data:
                print("%s: %s matches %s" % (image, e.path, src))
            else:
                ok = False
                why = ("sizes differ (%d on disc, %d in the file)" % (e.size, len(data))
                       if e.size != len(data) else
                       "%d bytes differ" % sum(1 for a, b in zip(held, data) if a != b))
                print("%s: %s does not match %s: %s" % (image, e.path, src, why))
    return 0 if ok else 1


def cmd_switches():
    """Print the switch levels: each edition's groups, then each group's
    switches with their descriptions."""
    text = {s[0]: s[3] for s in SWITCHES}
    for name, title, groups in EDITIONS:
        print("%s: %s" % (name, title))
        print("  groups: %s" % ", ".join(groups))
    in_edition = set(sum((g for _, _, g in EDITIONS), ()))
    for name, title, members in GROUPS:
        print("%s: %s%s" % (name, title, "" if name in in_edition else " (in no edition)"))
        for switch in members:
            print("  %-20s %s" % (switch, text[switch]))


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
    write_copies = "--copies" in args
    if write_copies:
        args.remove("--copies")
    # Each switch's own flag (--skip-tutorial, ...) still works, as --mod <name>.
    values = []
    for name in SWITCH_NAMES:
        if "--" + name in args:
            args.remove("--" + name)
            values.append(name)
    while "--mod" in args:
        values.append(_opt(args, "--mod"))
    mods = parse_mods(values)
    dat =_opt(args, "--dat", "DAT" if os.path.isdir("DAT") else None)
    nation = _opt(args, "--skip-nation", None)
    if nation is not None:
        names = [n.lower() for n in SKIP_NATIONS]
        if nation.lower() not in names:
            raise SystemExit("--skip-nation takes %s" % ", ".join(SKIP_NATIONS))
        if "skip-tutorial" not in mods:
            raise SystemExit("--skip-nation goes with --skip-tutorial")
        global skip_nation
        skip_nation = names.index(nation.lower())
    renames = []
    while "--rename" in args:
        renames.append(_opt(args, "--rename"))
    try:
        if cmd == "locate" and len(args) >= 2:
            cmd_locate(args[0], args[1:])
            return 0
        if cmd == "copies" and len(args) >= 2:
            cmd_copies(args[0], args[1:])
            return 0
        if cmd == "patch" and (len(args) >= 3 or (renames or mods) and len(args) == 2):
            in_place = args[1] == "--in-place"
            cmd_patch(args[0], None if in_place else args[1], in_place, args[2:], dat,
                      write_copies, renames, mods)
            return 0
        if cmd == "verify" and len(args) >= 2:
            return cmd_verify(args[0], args[1:])
        if cmd == "switches" and not args:
            cmd_switches()
            return 0
    except (ValueError, OSError) as e:
        raise SystemExit(str(e))
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
