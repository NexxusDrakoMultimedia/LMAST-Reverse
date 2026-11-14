<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Runtime memory: the club and its people

This doc covers the career identity, the player records, the club's
finances, transfers and contracts, and the staff, training and club
activities. It records where the game keeps this data while it runs, so
that tools and achievement sets can read it from the console's memory.
`SAVE_FORMAT.md` describes the same data as it sits on the memory card
([fields found so far](SAVE_FORMAT.md#fields-found-so-far)). Here the
subject is the live copy in RAM.

Every address is an EE RAM address in the PAL release (`SLES_541.51`),
inside 0 to 0x1FFFFFF, and every multi-byte value is little-endian.
Nothing here was measured in PCSX2 unless a row says so. The rows come
from reading the game code and the other docs, and each was checked
twice, by two independent readers. The one result seen in the running
game is Nexxus's report of 2026-10-27 (a German career on an LMASTER max
build, recorded in `SAVE_FORMAT.md`): it supports the root pointer chain
described below, the club status and its ranks. Every other row still
needs a live check. The Japanese release (SLPM-66316) is not covered;
its pwork pointer is at a different address
([`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)). The fixed frame of the
address space (the executable image, the heap, the overlays) is in
`RAM_MAP.md`.

## How to read this doc

**Confirmed** means the offset, size and meaning were read in the game
code at the address and symbol cited in the last column of the row.
**Empirical** means the claim was inferred from data (the saves, the
tables on the disc, the other docs) and fits it, but no code path was
traced. A row that says nothing else is confirmed for the address and
layout. Claims that were refuted, unverified or not agreed by the
readers are kept apart, in each section's "Unconfirmed" list, and
should not be relied on.

Almost all of the data is in one heap object, the `Param::PlPworkTask`.
The game never places it at a fixed address, so each value is reached
through a chain of pointers. The sections spell the notation differently
(T, D and `off_k` in the first, P and H in the second, P and B in the
others), but all five mean the same thing:

```text
root  = u32[0x3909a8]               the PlPworkTask (set once per boot)
base  = u32[root + 0x1c]            start of the save-work buffer
off_k = u32[root + 0x28 + 4*k]      offset of block k, k = 0 to 10
block k = base + off_k
```

The 11 blocks sit in a shuffled order made once at boot, so the offsets
are read, never hard-coded. Block 0 is the general state (date, funds,
flags), block 1 is your club, block 2 the other clubs, block 3 the
league, block 5 the records and block 7 the options. A field is written
`block1 + 0x4b4`: add the offset to the block's address.

The address tables have seven columns: Address, Size (in bytes), Type,
Region (`static` for a fixed address in the executable, `heap` for a
field inside the pwork buffer), Name, Meaning and values, and How known
(confirmed or empirical, with the code addresses and symbols).

The pointer chain tables have four columns. "Chain" gives the steps to
take: `[x]` is the 32-bit word stored at address x, and `[x+n]` is the
word stored at the address in x plus n. "valid_when" says when the chain
leads to real data (after a New Game or a Continue load, for example),
and "stable_across" says what leaves the result unchanged (a frame, a
screen, a match, a save and load).

Overlay addresses such as `SIMPRG.REL 0x15d958` are offsets inside the
overlay file. The overlays load at run time, so they are not RAM
addresses. "The game code" means the executable and those overlays.

## Contents

- [Career identity and objectives](#career-identity-and-objectives):
  the pwork root, the date, the club's funds, league, status and rank,
  the hidden difficulty byte, the event flags and the mode words.
- [Player records in memory](#player-records-in-memory): your 25-man
  squad, the youth team and the other clubs' compact entries.
- [Club finances and popularity](#club-finances-and-popularity): the
  money accounts, popularity, sponsors, TV deals, merchandise, the
  stadium plan and the facility levels.
- [Transfers, contracts and scouting](#transfers-contracts-and-scouting):
  the transfer window, the free-agent pool, offers, pending signings and
  the scouting lists.
- [Staff, training and club activities](#staff-training-and-club-activities):
  the staff, the training plan and its effects, camps, tours and PR
  events.
- [Still unknown](#still-unknown): the five open questions that matter
  most.
- [Checking the claims](#checking-the-claims): commands that reproduce
  the root pointer and a few of the rows.

## Career identity and objectives

This part of memory holds the state that says which career is running
and where it stands. The PAL release has no owner objectives, no board
evaluation and no player-selectable difficulty. The nearest equivalents
are the club status and rank, a hidden difficulty byte updated at each
year start, the game-over checks, and the "fired" slots of the tutorial
events. All career state lives in the PlPworkTask, a heap object reached
from the static pointer 0x3909a8. Everything here comes from disassembly
and the docs (static analysis, checked by two verifiers and two red
teams). The only results seen in the running game are the ones credited
to DOC/SAVE_FORMAT.md (Nexxus's report, 2026-10-27, a German career on
an LMASTER max build): the pwork chain, the status and its ranks.

"T" below means the value of the word at 0x3909a8. "D" means the word at
T+0x1c. "off_k" means the word at T+0x28+4*k. Block k starts at
D + off_k. There are 11 blocks (k = 0..10). The roles used here are
block 0 general, 1 your club, 3 league, 5 records, 7 options.

### Addresses

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer | static | PlPworkTask pointer | Pointer to the live Param::PlPworkTask (0x5c bytes). It is non-zero from the first script command of ROOTMAINSEQ (Pwk.Create at script offset 0x10) for the whole boot: logo, title, demo, VS, menus, matches and career. Pwk.Delete (script 0x1a20) sits behind an unconditional branch and is unreachable. So T, D and every block offset are fixed for the whole boot, and New Game, Load, saves and the year rollover work in place and do not move them. It is not a career-versus-menu flag, and the block contents are blank until Pwk.NewGame or a Continue load. Block k = [T+0x1c] + [T+0x28+4*k]. In retail no offset is 0xFFFFFFFF (only block 8 can be absent, when T+0x19 != 0, and the only Create caller passes 0). | confirmed: CreatePwork 0x21d628 stores at 0x21d65c, DeletePwork 0x21d698 clears at 0x21d6c8, each with a single caller in PwkCallbackCommand_Create / _Delete (0x1104b8, 0x110570); getter plPwork_GetPwork 0x21d6e0; constructor 0x21d6f0; pwGet 0x21da50. Script offsets from `sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB`. Chain also tested in PCSX2 per DOC/SAVE_FORMAT.md |
| T+0x18 | 1 | u8 | heap | Extended-work selector | Always 0 in retail. The extended work (T+0x20, base kept at T+0x24) is created by prepareExtWork 0x21d980 and removed by deleteExtWork 0x21d9e0, and neither has a caller in the executable, a vtable or an overlay. switchExtWork 0x21da20 (imported only by SAVEPRG.REL) returns 0 while T+0x20 is NULL. So D never swaps. | confirmed (jal scan and overlay import tables; both functions have no caller) |
| block0 + 0x88 | 16 | struct PlDate: u16 year, u8 turn, u8 month, s32 turn in month, s32 pair, s32 parity | heap | Career date | +0 u16 year of the season's first half (2005 = scripted opening playoffs, 2006 = first real season; January to June keep the season's year). +2 u8 turn 0-95, turn 0 = July, 8 turns per month. +3 u8 month 1-12 = ((turn>>3)+6)%12+1. +4 s32 turn within month (turn&7, 0-7). +8 s32 pair index (+4)/2 (0-3). +0xc s32 turn&1 (0-1). Rewritten whole, once per schedule turn-advance, never per frame. Rollover is turn 95 to 0 with year+1 (July). Years elapsed = year - 2006 (pwkGen_Keika). A new game starts at 2005 turn 92 (June), opening playoffs run 2005 turns 92-95, then pwkGen_SetStartYear sets 2006 turn 0. A VS work area is 2005 turn 95. | confirmed: pwkGen_GetDate 0x244368 (copies 0x10 bytes), plMisc_SetTurn2Date 0x214698, pwkGen_Keika 0x244430, writers updateParamDate 0x207228 / 0x207410 / 0x207580, pwkGen_IncDay 0x2443d0, plMisc_GetLaterDay 0x214788, pwkGen_Init 0x244220 (via 0x2441c8), pwkGen_SetStartYear 0x2442e8, pwkGen_InitVSDate 0x244328 |
| block0 + 0x0 | 8 | s64 | heap | Club funds | Your club's money in the game's own unit (empirical: pound = stored/6, euro = stored/4, from the rate table 12, 3, 2, 400 at 0x5314e8, DOC/SAVE_FORMAT.md). A true s64, negative means debt, not capped at 0x7fffffff. pwkGen_Income ignores amounts <= 0, adds in 64 bits and stores 0x7fffffff only if the 64-bit sum is <= 0 while funds were >= 0. pwkGen_Pay has no floor. Written in place on every income and payment. Negative funds at the July year start give game over (see below). | confirmed: pwkGen_GetSikin 0x2444e0 (ld), SetSikin 0x2444a8 (sd), pwkGen_Income 0x244570, pwkGen_Pay 0x2445f8, game-over check CheckGameOverSikin 0x110f40, plMisc_MoneyRate 0x215660 |
| block1 + 0x4b4 | 4 | s32 | heap | Club record: team number | PlTeamData +0. Constant 1 for your club, stored by the function at 0x25ddb8 (called from pwkTeam_Init2 0x25eae8). Not an identity, at most a "career block initialised" marker. | confirmed: pwkTeam_GetMyTeamData 0x259898 |
| block1 + 0x4b8 | 2 | s16 | heap | Hometown city id | PlTeamData +4. City id 0-838 (839 cities in PLRESOURCESIM, DOC/PLRESOURCESIM_FORMAT.md), set once at HomeSelect by pwkTown_SetMyCityNo (0x271910, from SetHomeTown_HomeSelectModule 0x11ebf0). Mapped to a name by plCity_GetString (0x21f970). City 0 is also the zeroed value before HomeSelect (pwkTeam_Init 0x25e950 memsets block 1, 0x129e8 bytes). Never changes after HomeSelect. | confirmed: VarBuf_MakeMyHometown 0x11e8a0. The range 0-838 comes from the city table size (empirical) |
| block3 + 0x0 | 4 | u32 | heap | League | League 0-5 = England, France, Germany, Italy, Spain, Netherlands (names empirical, INITTEAM_FORMAT.md). Nation id = league + 1. Written once by pwkLg_Init (0x246218) and never changed after (not at year end). | confirmed: pwkLg_GetMyLeague 0x2462a8, table at 0x531d40 |
| block3 + 0x4 | 4 | u32 | heap | Competition (division) | Your current domestic competition. Division 0 ids {0,6,11,16,22,27} and division 1 ids {1,7,12,17,23,28} for leagues 0-5 (table at 0x531d40, rows {nation, league, div0, div1}). Changed only by pwkLg_SetMyCompe (0x2462e0), and only within the same league. pwkLg_GetMyDiv (0x246388) via plMisc_Compe2PlDiv (0x215d00) can return -1 for ids outside those twelve. A zeroed block reads England division 0. | confirmed: pwkLg_GetMyCompe 0x246350. That a change happens at year end is empirical, not traced |
| block1 + 0x129c8 | 1 | s8 | heap | Club-name preset id | The preset id taken from the chosen league's preset list (list element, not the list index). Stored by pwkTeam_SetMyTeamNamePreset (0x25af18) and SetMyTeamNamePresetRandom (0x25af68). Reads 0 before a name is set, so unset equals preset 0. The getter's -1 only means block 1 is null, not a typed name. Low value. | confirmed: pwkTeam_GetMyTeamNamePreset 0x25b0d8 |
| block1 + 0x1126a | 2 | u16 | heap | Club status (reputation) | The hidden reputation. Capped by the status rank: 65535, 60000, 55000, 40000, 30000, 25000, 10000, 7000, 7000 (u16 table at 0x555150, indexed by status rank). New value = old + delta clamped to 0 and the cap. +500 at each year end. Changes on match results and at year end. | confirmed: pwkTeam_StatusChange 0x26dbb8, pwkTeam_Status 0x26e2f0, YearEndCheck 0x26e2a0. Tested in PCSX2 per DOC/SAVE_FORMAT.md (Nexxus's report) |
| block1 + 0x11264 | 4 | s32 | heap | Club status rank | 0-8. Starts at 7 (StatusInit 0x26e328). 0 is the best rank and its cap is the highest. StatusChangeRank (0x26dc50) only lowers the number, YearEndCheck lowers it to 5 on promotion. | confirmed: StatusInit 0x26e328 stores 7 |
| block1 + 0x46ac | 1 | u8 | heap | Club rank | 0 to 31, = min(status >> 11, 31). It rises with reputation: 0 is the lowest standing (status below 2048, a new club, set by StatusInit) and 31 the highest (status 63488 or more). A cached copy refreshed only by 0x26dd40 (called from GameCheck 0x26df74, MatchGameCheck 0x26e274, YearEndCheck 0x26e2d4), so it can lag the u16 status by up to one match. Do not mix it with pwkTeam_GetMyClubRank (0x259b60), which is status/0x7ff. | confirmed: 0x26dd40 loads u16 [block1+0x1126a], shifts right 11, clamps with plMisc_OFcheck 0x215da0 and stores at 0x46ac. DOC/SAVE_FORMAT.md records status 65535 giving rank 31 and status 30000 giving rank 14 (Nexxus's report) |
| block0 + 0x1344 | 1 | u8 | heap | mDifficulty (hidden progress level) | The only "difficulty" variable. Stored 0-16 in practice: negatives become 0 and totals of 17 or more are stored as 15. Updated once per year start by YRSTPRG.REL 0x1a420 (called from pwk_YS_FirstHalf, YRSTPRG.REL 0x1a5b0 at 0x1a5b8) by adding the sum of a 19-row table at YRSTPRG.REL 0x33448 {predicate, arg1, arg2, delta}. Rows 0-7: +1 when pwkGen_Keika is 5, 10, 15, 20, 25, 30, 40 or 50. Rows 8-16: +1 each for past-record tests (competitions 0x21, 0x22, 0x23 and your nation's top division, details not decoded). Row 17: +1 for CheckDivShift_TeamUserOnly == 1. Row 18: -1 for == 2. The only reader is pwkOteam_ChangeFS_playerMoveFromOwnerTeam (0x24b3b8). What it scales is unknown. | confirmed: pwkGen_GetDifficultyPointer 0x244c78, YRSTPRG.REL 0x1a420 and table. Rows 8-16 wording is empirical (see Unconfirmed) |
| block0 + 0x49b0 | 342 | u8[342] | heap | Event flags | One byte per flag, 0 or 1, valid indices 1-341 (index 0 means none and reads true in IsEventFlag, and an index outside 0-341 is forced to 0). Written only by SetEventFlag and ClearEventFlag. Saved with block 0 (342 fields of 8 bits at block0+0x49b0) and cleared on New Game (pwkGen_Init memset). The Event module's own init does not clear them, but its teardown does: SIMPRG.REL 0x124488 calls ClearEventFlag for every flag whose reset-group word in the table at SIMPRG 0x1d82e0 equals the argument (called from 0x12a348, which the destructor of an FC_EURO_MODULE-derived module calls at SIMPRG 0x6b94). In that table 323 flags are group 4, 10 are group 11, 8 are group 20 and 1 is group 10. So most flags can fall back to 0 while a career runs. Which module uses which group was not traced. Cached pointer to the same array at 0x5eec20 (EvsWork+0x20, static), valid only while the Event module is initialised. | confirmed: SIMPRG.REL IsEventFlag 0x124378, SetEventFlag 0x124408, ClearEventFlag 0x124448, clearing loop 0x124488 (group counts read from the file), EVS init 0x129034, pwkGen_GetEvData 0x244cb0 |
| block0 + 0x21b0 + 8*i | 8 | slot: u16 year, u8 month, u32 turn in month | heap | EVENT "last requested" slots | EVENT index i 0-381 (clamped below 0x17e). +0 u16 year != 0 means the event has been requested (created and accepted) at least once. +2 u8 is the PlDate month byte (+3), +4 u32 is the PlDate turn within month (+4). Stamped by SIMPRG.REL 0x12e758 from the request path at 0x12b648 via pwkGen_GetDate, on request and not on completion. Events 322-345 are once-only (EVENT record +0x70 = 1 in EVSDATABIN_EVENT.BIN), including 345. Tutorial and story events fall in this range. Cached base at 0x5eec14 (EvsWork+0x14). Saved with block 0. | confirmed: address maths (EvsWork+0x14 = EvData+0xc08, set at 0x129068) and writer 0x12e758. jmEvent_IsInvoke 0x15ed58 to 0x12f1b8, lookup 0x12e670, once-only check 0x12e220. That 322-345 are once-only is empirical |
| 0x390650 | 4 | u32 pointer | static | CScheEuro singleton | Zero = no schedule object: boot, logo, the idle title (before the demo starts), menus outside a schedule session, Load, club creation outside the opening playoffs, and a few frames between Finalize and the next Initialize. Non-zero = a schedule exists: a career (from Sche.Initialize or InitializeContinue to Sche.Finalize), the opening playoffs (InitializeFirstCheck), VS mode and the title attract demo (both Initialize_VsMode). Created by CreateScheEuro (0x202a50), cleared by DeleteScheEuro (0x202ba8, called from ScheCallbackCommand_Finalize 0x113408). A new game publishes it twice (opening playoffs, then the career). | confirmed: store 0x202b50, clear 0x202bdc, GetScheEuro 0x202bf8; callers 0x113310, 0x113368, 0x1133c8, 0x114604; windows from the root scripts |
| [0x390650] + 0x20 | 4 | u32 | heap | Schedule mode vtable | 0x406c28 = career (mode 0, a new game and a loaded game alike). 0x406b48 = opening playoffs (mode 1, RootClubEditSeq). 0x406a68 = VS mode (mode 2), also used by the title demo match (RootDemoMatchSeq runs Sche.Initialize_VsMode). Compare as an exact u32. Set before the singleton pointer is published. The same object has a second set at [0x390650]+8: 0x406c78 career, 0x406b98 opening playoffs, 0x406ab8 VS. Use one set consistently. | confirmed: CreateScheEuro stores +0x20 at 0x202b40 and +8 at 0x202b4c; mode mapping (arg 1 = opening playoffs, 2 = VS, else career) at 0x202a84..0x202a94 |
| 0x34d43c | 4 | u32 | static | Demo flag | 1 only while RootDemoMatchSeq runs (set at its 0x0018, cleared at 0x0208). 0 everywhere else, including the idle title screen before the demo starts. During the demo the career memory is rewritten in place by a throwaway Pwk.NewGame (script 0x88), so career reads must be gated on this being 0. | confirmed: fcEuroDummyCommand_SetDemoFlag 0x109358 (store 0x109394), CheckDemoFlag 0x1093a0; script read with `sqb.py dis` |
| 0x34d438 | 4 | u32 | static | Developer launcher flag | 1 only inside RootLauncherSeq. Always 0 on retail because ROOTMAINSEQ skips the launcher when Dummy.CheckLauncher is non-zero. | confirmed address (SetLauncherFlag 0x1092b0, store 0x1092ec); "always 0 on retail" is empirical |
| 0x34d474 | 4 | u32 | static | Title movie flag | Initial value 1 in the executable image. The title module's constructor (MOVIEPRG.REL 0x1640) reads it, and its destructor (MOVIEPRG.REL 0x1820) clears it. Means "first title since boot", not "on the title screen". | confirmed address (SetMovieFlag 0x1094d0, store 0x1094d8, getter 0x1094e0); the image value read from the file |
| block0 + 0x298 | 1 | u8 | heap | Last save point kind | The Save module argument of the most recent save made or loaded in this career: 1 turn main menu (Option save), 2 year start, 3 playoffs start (club creation), 4 club edit (the 1-4 mapping is empirical, from DOC/GAME_FLOW.md). Written by _pwkGen_SetSavePoint (0x244b78) from SAVEPRG.REL 0x336b4 and skipped when the argument is 5, so 5 is never stored. Read by _pwkGen_GetSavePoint (0x244bb0) at SAVEPRG.REL 0x32f70. Persists until the next save. Before the first save it is probably 0 (unverified). Cannot alone tell a loaded career from a new one that has saved. | confirmed for address, writer and the never-5 rule; value meanings empirical |
| block7 + 0x15 .. block7 + 0x1c | 8 | u8[8] | heap | Tutorial help seen flags | Eight 0/1 bytes inside block 7 (options, from pwkOpt_GetOptionDataWork 0x24a578 = block7+4, flags at option offset +0x11). EntryPreset (0x295398) sets one to 1 when its help is shown. Preset 14 uses byte 0, presets 29-34 use bytes 2-7. Byte 1 is written by no preset. Other helps are tracked through event ids. CheckPreset (0x2953f8) also reports a help as seen when a GetScheEuro condition holds for presets 0x1f-0x22 or task flag bit 2 is set. Cleared by pwkOpt_Init (0x24a310), which has two callers: Pwk.NewGame (0x110aac) and the title module constructor (MOVIEPRG.REL 0x1630). So they read 0 whenever the title screen has just been entered, including after returning to the title, and a Load restores them. Do not read them on the title screen. Low value. | confirmed: offsets and the clearing loops 0x24a390..0x24a3b0 and 0x24a430..0x24a448; preset table at 0x39f1c0, 8-byte rows (event id, then option offset) |

### Pointer chains and stability

The root is always the static word at 0x3909a8. The 11 blocks are laid
out in a random order made once, by plUty_ShuffleUint8 (0x235270, with
fcEuroRand, in the constructor 0x21d6f0, call at 0x21d774). That runs
once per boot, at Pwk.Create, so T, D and every offset are fixed from
the first script command until the console is reset. Whether the order
is the same on every boot is open: the generator state 0x569dc0 is set
to the constant 0x12345678 by fcEuroRand_Init (0x111698), but other
draws before Create were not ruled out. Do not hard-code a resolved
address or an offset until two boots have been compared. Re-walking the
chain on every evaluation and guarding every hop for zero is still the
safe practice, though the game itself never moves it.

| Entry | Chain | valid_when | stable_across |
|---|---|---|---|
| 0x3909a8 (T) | T = [0x3909a8]; D = [T+0x1c]; off_k = [T+0x28+4*k]; block k = D + off_k | T non-zero (it is, from the first script command). Contents are meaningful only after a Pwk.NewGame or a Continue load. | Fixed for the whole boot: New Game, Load, saves, the demo, matches and the year rollover do not change T, D or the offsets. Possibly identical across boots (unresolved). |
| Date | block0 = D + [T+0x28]; date = block0 + 0x88 | A career or save is loaded. Sanity check: year 2005..~2040, turn < 96, month == ((turn>>3)+6)%12+1. | Stable between turn-advances. Rewritten by New Game, Load and the demo. |
| Funds | block0 = D + [T+0x28]; funds = s64 at block0 | Career or save loaded. | Value changes only on income and payment events. |
| Team number and city | block1 = D + [T+0x2c]; club = block1 + 0x4b4 | A career exists. City is meaningful only after HomeSelect or a save load. Test: club+0 == 1 and city in 0-838. | City never changes after HomeSelect. Reset by a new game. |
| League and competition | block3 = D + [T+0x34]; league = [block3], compe = [block3+4] | pwkLg_Init has run. Test: league 0-5, compe in the twelve ids, and Compe2League(compe) == league. | League fixed after Init. Compe changes only through pwkLg_SetMyCompe within the same league. |
| Name preset | block1 = D + [T+0x2c]; byte at block1 + 0x129c8 | Career or save loaded. | Stable once set. |
| Status, status rank, club rank | block1 = D + [T+0x2c]; fields at block1 + 0x1126a, +0x11264, +0x46ac | Career or save loaded. Sanity check: status rank <= 8, club rank <= 31. | Stable through frames, screens and matches. Reset to rank 7 and club rank 0 by StatusInit on a new career. |
| mDifficulty | block0 = D + [T+0x28]; byte at block0 + 0x1344 | Career or save loaded. Changes only at the year-start routine pwk_YS_FirstHalf. | Stable across a season. Saved with block 0. |
| Event flags | flag = D + [T+0x28] + 0x49b0 + index. Shortcut: [0x5eec20] + index | For the shortcut, [0x5eec20] == D + [T+0x28] + 0x49b0 (Event module live). | Saved, but a flag can be cleared to 0 by a module teardown (323 of 342 are in reset group 4). Do not wait for a flag to stay set. |
| EVENT slots | slot(i) = D + [T+0x28] + 0x21b0 + 8*i. Shortcut: [0x5eec14] + 8*i | For the shortcut, [0x5eec14] non-zero (EVS manager initialised, SIMPRG.REL 0x129018). Check the address lies in 0x00100000-0x01FFFFFF. | Slots only go from 0 to non-zero for once-only events, and are saved. |
| Schedule singleton | S = [0x390650]; vtable = [S+0x20] | S non-zero, from Sche.Initialize, InitializeFirstCheck, InitializeContinue or Initialize_VsMode until Sche.Finalize. | 0x390650 and the vtable constants are fixed in the PAL executable. The value of S (a heap address) differs between runs and changes at each Finalize and Initialize. The vtable word is not rewritten during a mode's life. |
| Demo, launcher and movie flags | static words 0x34d43c, 0x34d438, 0x34d474 | Always readable after boot. | Fixed addresses. The demo flag is rewritten only twice per demo. PAL only, the Japanese build was not checked. |
| Last save point | block0 = D + [T+0x28]; byte at block0 + 0x298 | A career exists. Changes only when a save with argument 1-4 is made. | Constant until the next save. Restored from the save on load. |
| Tutorial help flags | block7 = D + [T+0x44]; flags at block7 + 0x15 + n (n 0-7) | [T+0x44] != 0xFFFFFFFF. Check that the bytes are only 0 or 1. | Flags only go 0 to 1 within a session, and are reset by a new game and whenever the title module is created. Carried across save and load. |

### RetroAchievements notes

- Gate everything on mode first. Read [0x390650]. If it is 0, no
  schedule exists (boot, idle title, menus, Load, most of club
  creation). Then require the vtable word [S+0x20] == 0x406c28 for
  career-only achievements. 0x406b48 is the opening playoffs (part of
  club creation) and 0x406a68 is VS mode or the title demo match.
- Pair the vtable check with the demo flag at 0x34d43c == 0. The demo
  runs a throwaway Pwk.NewGame, so career, schedule and event memory is
  rewritten during it.
- T = [0x3909a8] is non-zero from boot, so it says nothing about
  whether a career is active. Use it only as a null guard for the chain.
  The block contents are blank until a New Game or a Continue load.
- Resolve the chain on every evaluation (T, then D = [T+0x1c], then the
  block offset). The game never moves it, but whether the offsets match
  between boots is unresolved, so do not hard-code a block address.
- A two-value add (D plus a separate offset read) is needed, because
  both come from T. Use Remember and Recall for D, then a second pointer
  read for the offset, or an equivalent construction. This is a
  chain-building note and has not been tested in an RA toolkit.
- Reading the date: use the u16 year at block0+0x88, the u8 turn at +2
  and the u8 month at +3. Compare against the previous frame to detect
  a turn advance. The year increments when turn wraps 95 to 0 in July.
  Year 2005 exists only briefly at the start of a new career in retail
  (the opening playoffs, then it jumps to 2006 turn 0), so do not build
  "opening playoffs" logic on year < 2006 over a long window. A VS work
  area has year 2005, turn 95.
- Funds: read all 8 bytes. The low dword alone is not enough once funds
  exceed 2^31. The value changes only on income and payment events.
- Club rank at +0x46ac can lag the status, and a higher number is a
  higher standing. For a live milestone use the u16 status at +0x1126a
  and compute status >> 11 (clamp 31).
- League and division: a zeroed block 3 reads league 0, compe 0, which
  looks like England division 0. Pair with a career-mode check.
  Compe2PlDiv can return -1 for competition ids outside the twelve.
- Save point kind: do not use it to detect a loaded save. A new game
  that saved at club creation also holds 3 or 4. Pair it with a
  separate load indicator (the Load module result is not mapped to an
  address here).
- Event flags: 323 of the 342 flags can be reset to 0 when the module
  that owns their reset group is destroyed. Do not build an achievement
  on a flag staying set until the owning module is identified.
- Tutorial progress: the EVENT slot u16 at +0 non-zero means "requested
  at least once", slightly earlier than the scene finishing. Records
  322-345 are once-only. The 8 help bytes in block 7 are supplementary,
  low value, and read 0 after every visit to the title.
- mDifficulty is a weak trigger. Its role is unknown and it changes only
  at the year-start routine.
- The Japanese build is not covered. Every address here is PAL
  (gamever.py finds the Japanese equivalents for the tools).

### Unconfirmed

These claims were refuted, unverified or not agreed. Do not rely on them.

| Claim | Reason |
|---|---|
| The pwork block order and offsets are identical on every boot | The shuffle state 0x569dc0 starts at a constant, but other draws before Pwk.Create were not enumerated and no run was compared. |
| Rows 8-16 of the mDifficulty table mean "winner or runner-up" | The predicates test past-record fields (byte +6 and s16 +2 or +4 of block 5 record 0x98*compe) and were not decoded. |
| Signs of rows 17 and 18 (promoted +1, relegated -1) | Inferred from the deltas. The CheckDivShift return encoding at 0x254ef0 was not confirmed. |
| Which module uses which event-flag reset group | Only the group counts and the clearing loop were read. |
| Team number "rival = 2, AI clubs 3-441" for PlTeamData +0 | Not shown by the code. The block 2 record mapping (team 2 is record 0) is a different table. |
| PlTeamData +6 u8 prefecture-city flag | Neither a writer nor a reader was found. Omitted from the table. |
| Tutorial events "timing" values and "presets 0-28 are EVENT ids 0x01000142-0x01000158" | The id range is 23 ids, not 29, and the preset mapping was not reproduced. Timing values (322:12, 323:13, 326:15, 337 and 338:16, 339:17, 344:19) were seen by one verifier only. |
| Year 2005-06 for a first career season | DOC/SAVE_FORMAT.md describes a save state at "turn 81 to 82 of 2005-06" on an LMASTER max build, while the retail code gives 2006 turn 0 as the first real season. Probably the doc names the data season or an LMASTER third-tier change. Not checkable without a live read. |
| Second demo flag in PlGiTask (Param::PlGiTask::SetDemoFlag 0x33c408, task + 0x18000 + 0x7544) | A heap field that looks like a runtime-selected-competition regulation flag. Whether it tracks 0x34d43c is unverified. Do not use it. |
| Initial value of the save point byte before the first save | Probably 0, not read. |

### Still unknown

- No owner objective, board target or sacking-evaluation structure was
  found. Sacking is only the four checks in DOC/GAME_FLOW.md (funds below
  0 at the July year start, bottom of the lower league two years
  running, fewer than 8 players, lost opening playoff). Whether an
  "owner evaluation" is only the Information screen's reading of status
  and rank is open.
- Game over has no persistent runtime flag. The result is m4[2] in the
  sequencer's script memory (RootMainSeq), not a fixed address. A live
  trace is needed for a readable indicator, for example the schedule
  pointer 0x390650 going to 0 and the title returning.
- Where the two-years-in-the-bottom-two relegation counter lives is not
  traced. jmSche_CheckLeagueBottom (SIMPRG.REL 0x15d958) reads
  past-record data in block 5 (0x260 + 0x98*compe, compe < 49), not a
  dedicated counter.
- The one-shot (OO) flag bitmap at block0+0x29c (1023 bits,
  pwkGen_GetOO 0x244658, SetOO 0x2446c0; flags 1-126 cleared every year
  by pwkGen_SetOnecePerYearOff 0x244750) has no readers in the overlays.
  Only bits 0x383 (Pwk.RuntimeInitialize 0x110b78), 0x381 (0x1130a0) and
  0x382 (0x113150) are set in the executable. What they unlock is
  unknown.
- What mDifficulty scales is unknown, and the past-record predicates
  (records +2, +4, +6 of block 5 record 0x98*compe) are not decoded.
- The owner's name and the club name are text in VarBuf slots 0 and 1
  (50 x 0x28 bytes, Msg::SetVariableBuffer 0x11e570,
  SetOwnerName_Keyboard 0x11ec58). The buffer's static address was not
  resolved.
- How to detect the club-creation screens (HomeSelect, team style,
  uniform, emblem) was not traced. They are CEDITPRG modules; the module
  activity table at 0x5698d0 + 4*id (non-zero from Module.Start to
  Module.Delete) is the likely place. The "owner" in the rival's club
  record (+0xc, ownerNo) is not your owner.
- fcEuroRootTask_GetGameMode / SetGameMode (word at 0x35c9ac) is always
  0 and nothing reads it, so it is not a usable mode indicator.
- Which code calls pwkLg_SetMyCompe at the year end, and whether
  promotion and relegation are its only triggers, is not traced.
- Whether EVENT slots are cleared at year start is not traced (a new
  game zeroes them through the pwkGen_Init memset of block 0).
- The 17-byte list at block7+4 to block7+0x14 was only seen being
  cleared by pwkOpt_Init. Its meaning is unknown.
- The title idle state and menus keep the pwork alive, but no verified
  indicator separates "title screen" from other states for a rich
  presence rule (the module activity table is the candidate).
- The Japanese release (SLPM-66316) was not checked for any address
  here. DOC/JAPANESE_RELEASE.md gives a different pwork global there.
- Nothing in this section was read from live RAM or PINE. Every row
  needs a live check, except the results credited to
  DOC/SAVE_FORMAT.md.

### Checking the claims

Every command runs from the repo root. The first lists the pwork store
and clear, the second the script commands that create and delete it.

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 addr 21d628 44
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB
```

In the first, look for `sw $a2, 0x9a8($s1)` at 0x21d65c and
`sw $zero, 0x9a8($s0)` at 0x21d6c8. In the script listing, Pwk.Create is
at 0x0010 and Pwk.Delete at 0x1a20.

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 addr 244570 24
python SRC/sles_disasm.py ISO/SLES_541.51 addr 26dd40 24
```

The first shows the funds add in 64 bits (`daddu`, `sd`) with the
0x7fffffff store only on a non-positive sum. The second shows the club
rank: `lhu 0x126a`, `srl 0xb`, plMisc_OFcheck with 0x1f, `sb 0x46ac`.

```bash
python SRC/snr2.py dis ISO/DLL/YRSTPRG.REL 1a420 14 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 124488 24 --sles ISO/SLES_541.51
python SRC/snr2.py xref ISO/DLL/MOVIEPRG.REL pwkOpt_Init__5Paramv
python SRC/sles_disasm.py ISO/SLES_541.51 addr 202b30 12
```

In order: the mDifficulty update (pwkGen_GetDifficultyPointer, the table
sum, clamp to 15); the event-flag reset loop (`slti 0x156`, table at
0x1d82e0, ClearEventFlag 0x124448); the title module's call of
pwkOpt_Init (relocation at 0x1630); and the mode vtable store at
0x202b40 and the singleton publish at 0x202b50 in CreateScheEuro.

## Player records in memory

The career-side player data of the PAL release (`SLES_541.51`) lives in
one heap workspace, `Param::PlPworkTask`, reached through a single static
pointer at 0x3909A8. The workspace holds 11 save blocks in a shuffled
order, so every player address is found by a pointer chain and never by a
constant. Your own squad is 25 `PlPinfo` records of 0x2A0 bytes in block
1, the youth team is 24 more, and the other clubs hold only compact
6-byte squad entries in block 2.

Notation used below: `P = u32[0x3909A8]`, `H = u32[P+0x1C]`,
`B1 = H + u32[P+0x2C]`, `B2 = H + u32[P+0x30]`,
`slot(n) = B1 + 0x4D4 + 0x2A0*n` for n = 0..24.

Every claim comes from reading the PAL executable (code, not a running
emulator). Nothing here was seen in PCSX2, and no `DOC/` file records a
run of these addresses in the game. "Confirmed" means the offset, size
and meaning were read in the code at the cited address. "Empirical"
means inferred from data (the saves and tables in `DOC/SAVE_FORMAT.md`)
and consistent with it, but not read in code. Anything not settled is in
the Unconfirmed subsection.

Lifetime of the root, in one paragraph: `plPwork_CreatePwork` runs once
per boot, from the first real command of `ROOTMAINSEQ` (`Pwk.Create`,
script offset 0x0010, through `PwkCallbackCommand_Create` 0x110498). The
only `Pwk.Delete` (script offset 0x1A20) is unreachable. So `P`, `H` and
every block offset are non-zero and constant from the start of the boot
(logo, title, demo, VS mode, career) until reset. New Game, Continue and
the title demo rewrite the blocks in place and never reallocate or
reshuffle them. `P != 0` therefore says nothing about whether a career
exists: the constructor at 0x21D6F0 clears the whole buffer, and block 1
stays zero until a career is started or loaded. Details and sources are
in the roots section of this document set.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909A8 | 4 | u32 pointer | static | PlPwork root `P` | Pointer to the `PlPworkTask` object (0x5C bytes, `__builtin_new`). Non-zero and constant from the first script command of the boot, see the paragraph above. Set by `plPwork_CreatePwork` 0x21D628 (store at 0x21D65C), zeroed by `plPwork_DeletePwork` 0x21D698 (store at 0x21D6C8, never reached). Only four code accesses to this word exist (0x21D65C, 0x21D67C, 0x21D6A8 or 0x21D6C8, and the getter at 0x21D6E8). Do not use `P != 0` as a "career loaded" test. | confirmed |
| P+0x14 | 4 | u32 | heap | vtable pointer | Vtable of `PlPworkTask` (0x406F90, stored at 0x21D740). | confirmed |
| P+0x18 | 1 | u8 | heap | ext-work flag | Set to 1 by `switchExtWork` 0x21DA20 (store at 0x21DA40) when the extension buffer is swapped in. Always 0 in retail: `prepareExtWork` 0x21D980 and `deleteExtWork` 0x21D9E0 have no caller in the executable or in any overlay. | confirmed |
| P+0x19 | 1 | u8 | heap | special flag | Set from the constructor argument. When non-zero, block 8 has offset 0xFFFFFFFF and `get(8)` returns 0 (0x21D950). Careers pass 0. It does not affect block 1 or 2. | confirmed |
| P+0x1C | 4 | u32 pointer | heap | heap base `H` | Base of the one `FcEuroMalloc` buffer (after `SetHeapBlock(6)`, stored at 0x21D850) that holds all 11 blocks. `switchExtWork(1)` would copy `u32[P+0x20]` into it, but that never happens in retail because `P+0x20` stays NULL. | confirmed |
| P+0x20 | 4 | u32 pointer | heap | ext-work copy | Second buffer made by `prepareExtWork`. No caller exists (the only import of the family is `switchExtWork` in `SAVEPRG.REL`, which returns 0 at 0x21DA2C while this word is NULL). Stays 0 in retail. | confirmed |
| P+0x24 | 4 | u32 pointer | heap | saved original `H` | Stored by `prepareExtWork` (0x21D9B0). Stays 0 in retail. | confirmed |
| P+0x28+4*i, i = 0..10 | 4 each | u32 | heap | block offset table | Byte offset of save block i inside `H` (11 words, each block 8-byte aligned). 0xFFFFFFFF means absent, which only block 8 can be and only when `P+0x19` is set. Block order is shuffled by `plUty_ShuffleUint8` 0x235270 when the object is built. `pwGet` 0x21DA50 returns `H + offset`; `get` 0x21D928 wraps it. | confirmed |
| P+0x54 | 4 | u32 | heap | total size | Total allocated size of the buffer (stored at 0x21D82C). | confirmed |
| P+0x58 | 2 | u16 | heap | random key | Key used by the 8-byte trailing block headers (`setHeader` 0x21DA90, `headerCheck` 0x21DB38). | confirmed |
| B1 = H + u32[P+0x2C] | 0x129E8 usable (0x129F0 with the 8-byte trailer) | block | heap | block 1 (your club) | Club block. Your `PlTeamData` starts at B1+0x4B4 (`pwkTeam_GetMyTeamData` 0x259898 returns `get(1) + 0x4B4`); the squad is at +0x20 of it. The size comes from the table at 0x533AC8. | confirmed |
| B1+0x4D4+0x2A0*n, n = 0..24 | 0x2A0 each (25 slots) | `PlPinfo` array | heap | squad slot | One squad player. Slot number is the "pidx" used by the stats, release list and combination tables. Loops in `pwkTeam_GetForeignCitizenNumber` 0x266450, `pwkTeam_GetPlayer` 0x2670D0, `plTeam_SerchPinfo` 0x22C950 (TeamData+0x20) and `pwkTeamType_FitCalc` 0x270B58 all use 25 slots at stride 0x2A0. | confirmed |
| slot+0x0 | 2 | s16 | heap | player database id | Negative (sign bit set) means the slot is empty (`lh` then `srl 0x1F` at 0x22C980). Test the sign bit, not 0. Ids 0..27949 are database players; 0x7CCE is the Virtua Pro Football edit player (kept at B1+0x12600). The edit id and range come from `DOC/SAVE_FORMAT.md`, not from the code. | confirmed for the sign-bit rule; edit id and range empirical |
| slot+0x4 | 4 | u32 | heap | assigned position `apos` | Value 0..13, written by `pwkTeam_ChangePosPlayer` 0x2657B0 (store at 0x2657EC). Grid-cell names (0 GK, then DF-L, DF-R, DF-C, DM-L, ...) are `pbdata.py` labels: empirical. Reading 13 as "none" is not proven. | confirmed offset and range; labels empirical |
| slot+0x8 | 1 | u8 | heap | current age | Years, field table range 0..99. Read as u8 (`lbu` at 0x21C880 in `plPinfo_ChangeKan` 0x21C840). | confirmed |
| slot+0xA+6*a, a = 0..63 | 6 each (64) | struct {u16 exp; u16 nowlimexp; u16 limlimexp} | heap | abilities | `exp` +0 is current experience 0..65535. `nowlimexp` +2 is the growth limit; `pwkGUtl_AddExp` 0x246028 sets exp = min(exp + gain, limit, 0xFFFF). `limlimexp` +4 is the cap, empirically always on a threshold with exp <= limit <= cap (not read by any traced function). The last ability, a = 63, is at slot+0x184, and the array ends at slot+0x18A. Ability order labels come from `pbdata.py` and are empirical. | confirmed for exp and limit; cap role and ability order empirical |
| 0x531C70 | 202 (101 x u16) | u16 table | static | ability level thresholds | `plMisc_AbilExp2Lv` 0x2153C0: level is the largest L in 0..99 with t[L] < exp, 0 for exp <= t[1]. So exp == t[L+1] reads as level L. Read from the executable: starts 0, 72, 154, 246, 348, 460, 582, 714, 856, 1008, 1175 and ends 64688, 65535. | confirmed |
| slot+0x198..0x20B | 0x74 | raw `PlPbase` header copy | heap | database record copy | Written once by `plPinfo_InitDb` 0x21B648 (copy of 0x74 bytes at 0x21B680; the same copy at 0x24B338 in the squad expansion 0x24B1E8), then saved with the career. Record offset n is at slot+0x198+n. Not a live view of the database. | confirmed |
| slot+0x1AC | 4 | u32 (small value) | heap | nationality | Read (`lw`) by `plPinfo_IsForeigner` 0x217558. | confirmed |
| slot+0x1B0 | 4 | u32 (0..15) | heap | rank | Read as `lbu` and `lw`; record +0x18. Best rank 15. Raw record value; `getPinfoRank` 0x20D908 computes differently for ids below 0x63F7. | confirmed |
| slot+0x1B4 | 12 | 3 x u32 | heap | database main positions | The first is the database main position (`apos0`); `InitDb` copies +0x1B4 into +0x4. | confirmed |
| slot+0x1C0..0x1C3 | 1 each | u8 | heap | database age, height, weight, shirt | Database age at +0x1C0 is not the current age (+0x8). Shirt at +0x1C3 is written by `plPinfo_SetUnumber` 0x218388 (`sb` at +0x1C3). Height wraps above 255. | confirmed |
| slot+0x1CA | 2 | u16 | heap | face number | Face number (record +0x32). An earlier "3D model index" label is wrong. | confirmed |
| slot+0x1DA | 1 | u8 (0..15) | heap | star | Read (`lbu`) by `plPinfo_GameCheck` 0x21D0D0 and `plPinfo_ChangePop`. | confirmed |
| slot+0x1F6 | 5 | 5 x u8 | heap | database play styles | Copied by `pwkPlayStyle_Init` 0x24D8A8 into the style path (see +0x27C). | confirmed |
| slot+0x1FB | 1 | u8 flags | heap | core flags | Bit 2 (mask 0x4) is the EU passport (`plPinfo_IsEU` 0x217668). | confirmed |
| slot+0x1FC | 2 | u16 bitmask | heap | skill flags | Bit n tests skill n (`plPinfo_IsSkill` 0x218728, `srav`). | confirmed |
| slot+0x20C | 4 | u32 bitfield | heap | status flags | Bits 0..27 used. 0x1 away on national duty (`pwkTeam_LeavePlayer` 0x2654C0 ORs its mask into this word; it also appears in the `UnPlay` and `IsCaptain` masks); 0x2 `IsRental` 0x217220; 0x4 `IsHired` 0x217240; 0x10 `IsSearch` 0x2183C0 and 0x20 `IsNego` 0x2183E8 (both 0 unless u8 slot+0x21C >= 0xFC); 0x40 set by `pwkTeam_AddReleaseList` 0x25A830 (the same call clears 0xB0); 0x100 heavy injury; 0x200 light injury; 0x400 just injured (cleared by `plPinfo_JustKegaClear` 0x2172C8, so transient); 0x800 `IsYouth` 0x217008; 0x1000 `IsYouthUp` 0x217028 (promotion gate tested in `pwkTeam_GetYpinfo` 0x270D00); 0x2000 `IsRentalBuyOption` 0x217260 (valid only when `IsHired`); 0x4000 `IsJoin` 0x2174E8; 0x8000 `IsRetire` 0x217200; 0x20000 `IsSlump` 0x2176E8; 0x80000 `_FRetire`; 0x100000 `_VRetire`; 0x200000 `IsRetireToday` 0x218708; 0x4000000 with the 0x4000101 mask equal to 0x4000000 is `IsCaptain` 0x2171C0; 0x8000000 `IsAssignRental` 0x2171A0. `plPinfo_UnPlay` 0x216F40 is flags & 0xA04103. Bit 23 (0x800000) has no named accessor in this record (in the match engine's own copy it means sent off). The "Rental" and "Hired" meanings are inferred, not tested. | confirmed per accessor; Rental vs Hired meanings and bits 0x80000, 0x100000, 0x800000 unverified |
| slot+0x218 | 4 | u32 `PlMoneySave` | heap | annual salary | Stored money value v, validated as price kind 0 (`pwkTeam_SetSalary` 0x266350 calls `CPlMoneySaveCtrl::WithInRange` 0x246C58). `PmsValue2SM` 0x246DD0 option 0 gives v * 100 stored units. The money unit rates at 0x5314E8 are the s16 values 12, 3, 2, 400; pound = stored / 6 and euro = stored / 4 (which currency is which is empirical, `DOC/SAVE_FORMAT.md`). Skipped for `IsHired` players by the annual salary loop at 0x252548. | confirmed layout; currency assignment empirical |
| slot+0x21C | 1 | u8 | heap | life/availability byte | Gates `IsSearch` and `IsNego` when >= 0xFC (`lbu`, 0x2183C0 and 0x2183E8). Its other meaning is untraced. | confirmed offset and gate |
| slot+0x21D | 1 | u8 read signed | heap | contract years left | Read as `lbu` by `plPinfo_GetContractInfo` 0x216EA8 and as signed `lb` by `pwkTeam_ContractUpdatePlayers` 0x265F30 (0x266060). 1..5 in retail saves per the doc; 0 or less starts renewal. | confirmed; value range empirical |
| slot+0x220 | 4 | u32 | heap | contract condition word | First word of the 8-byte contract condition (`sw` at 0x2663B4). Meaning unidentified. | confirmed offset; meaning unverified |
| slot+0x224 | 4 | u32 `PlMoneySave` | heap | contract condition amount | Range-checked as price kind 3 (`WithInRange` call at 0x2663BC in `pwkTeam_SetSalary`). | confirmed |
| slot+0x238, slot+0x23A | 2 each | u16 | heap | home and overseas popularity | Written by `plPinfo_ChangePop` 0x21C5F8 at +0x238 + 2*kind (0 home, 1 overseas). Clamped per player to 0..cap, where cap = 1000 * a table byte (values 15..65) from 0x533888 (home) or 0x533988 (overseas), indexed by byte slot+0x1DA * 16 + slot+0x1B0 (via 0x21C4C0). Not a flat 65535. | confirmed |
| slot+0x23C | 2 | u16 | heap | fatigue | 0..1000, higher is more tired (`plPinfo_ChangeGtired` clamps to 1000). `plPinfo_GetGTiredLevel` 0x21B090: level 0 up to 400, 1 up to 700, 2 above. Zeroed by `plPinfo_YearInit` 0x21B1B8. | confirmed |
| slot+0x23E | 2 | u16 | heap | status points | Clamped 0..65535 by `plPinfo_ChangeStatus` 0x21C750 through `plMisc_OFcheck` 0x215DA0. | confirmed |
| slot+0x240 | 2 | u16 | heap | condition | 0..65535, derived by `plPinfo_CalcCond` 0x21AF20 (stores at 0x21B1D8 and 0x21B774) from power, form, fatigue, injury and slump. `ConvertPlayer_Condition` 0x285728 compares with 0xD6D8 (55,000, at 0x285864) and 0x9C40 (40,000, at 0x285874). Holds a join counter (set to 1 by `plPinfo_SetJoinCounter` 0x21CA10, decremented at 0x21CAA0 and in the 25-slot loop at 0x259A04..0x259A10 with no zero check) while flag 0x4000 is set. | confirmed |
| slot+0x242 | 2 | u16 | heap | motivation | 0..65535 (capped to 0xFFFE then divided by 0x3333 by `plPinfo_Moti2Lv` 0x217B88, giving levels 0..4). | confirmed |
| slot+0x24C | 2 | u16 | heap | power | 0..1000 (`plPinfo_ChangePower` 0x21C8C0). Not the T-FIT bar. | confirmed |
| slot+0x24E | 2 | u16 | heap | form (`kan`) | Clamped between `plPinfo_kanLowLimit` 0x21C488 and 1000 (`plPinfo_ChangeKan` 0x21C840). The low limit is an s16 table at 0x390900 indexed by min(max(age byte at +0x8, 15), 32) - 15. Below 400 the condition message says he has lost form. | confirmed |
| slot+0x250 | 2 | u16 | heap | injury value | Remaining injury, 0 = healed. Decremented and clamped to 0 by `plPinfo_CheckRecover` 0x21AE30, which clears flag 0x100 when it reaches 0. Set by `_plPinfo_SetKega` 0x2172F8, which ignores value <= 0 (`blez` at 0x217320) and stores the value here and the kind at +0x254. The game's own "is injured" decision for recovery is value != 0. | confirmed |
| slot+0x254 | 4 | u32 (0..8) | heap | injury kind | Below 3 is light (`slti` at 0x217328), 3..8 heavy. Kind 8 is "cannot recover" in `plPinfo_IsHkegaFunou` 0x217418 (flag 0x100 and kind == 8). Meaningful only while value != 0. | confirmed |
| slot+0x25A, slot+0x25C | 2 each | u16 | heap | captain and keyman experience | Clamped 0..10000 through `OFcheck` (`plPinfo_ChangeCaptainExp` 0x21C938, `plPinfo_ChangeKeymanExp` 0x21C9A0). Changes are skipped when the id is negative or `plPinfo_UnPlay` is true. | confirmed |
| slot+0x278 | 4 | u32 | heap | current play style | 1..22, 0 = none. `pwkPlayStyle_Init` 0x24D8A8 sets it to the database style byte at +0x1F6 only if non-zero (0x24DA54..0x24DA5C). `plPinfo_SetPStyle` 0x21C358 can change it later. `pwkPlayStyle_GetExp` also sets it to path[0] when the old count was 0 and path[0] is non-zero (0x24DEEC..0x24DEF4). Style names are message strings (category 1, 150 + style, from the doc). | confirmed |
| slot+0x27C | 20 | 5 x u32 | heap | style path | Database styles first (the non-zero bytes of +0x1F6..+0x1FA compacted, 0x24D918..0x24D934), then random styles 1..22 (from 0x24D980). | confirmed |
| slot+0x290 | 1 | u8 | heap | learned style count | `pwkPlayStyle_Init` zeroes it (0x24DA28) and sets it to the number of non-zero database style bytes (0x24DA2C..0x24DA4C). `pwkPlayStyle_GetExp` 0x24DCA0 then recomputes it: it walks the five thresholds (see +0x292), adds 1 for each threshold with u16[+0x292] >= t[k] only if the path entry u32[+0x27C + 4*count] is non-zero (0x24DE40..0x24DE74), then adds the number of non-zero database style bytes with a u8 overflow guard (0x24DE80..0x24DEB8) and caps the sum at 5 (0x24DEC4..0x24DED4). After GetExp it equals min(5, thresholds passed with a filled path slot + non-zero database styles). A changed value calls `SetPlayerFlag` with flag 8 (0x24DF00). | confirmed |
| slot+0x292 | 2 | u16 | heap | cumulative style experience | Saturates at 0xFFFF (0x24DE00..0x24DE1C). Not "progress toward the next style". Thresholds 16000, 23000, 32000, 43000, 55535 are the u16 table at 0x398F60 (the address is built at 0x24DE2C as `lui 0x3A` + `addiu -0x70A0`). | confirmed |
| slot+0x29A | 1 | u8 (0..100) | heap | team fit (T-FIT bar) | Written by `pwkTeamType_FitCalc` 0x270B58 (0x270BA4 squad, 0x270BEC youth); `pwkTeamType_GetFit` 0x2703D0 clamps the result to 0..100. Called from `pwkTeam_Init2` 0x25F1B8 and from `SIMPRG.REL`. | confirmed |
| B1+0xEC88+0x11E*n | 0x11E each (25) | per-slot record `PlPlayerIndiv` | heap | stats record | Indexed by squad slot (pidx), not by player id. Cleared when the slot is reused. `0x267978` returns `get(1) + 0xEC88`. Getters `pwkTeam_GetPlPlayerIndivFromPidx` 0x267AF0 (pidx < 0x19, n * 0x11E) and `pwkTeam_GetPlPlayerIndivFromPlno` 0x267B40 (searches the 25 squad ids). `DOC/SAVE_FORMAT.md`'s 0xEC8E is record+6, consistent with this. | confirmed |
| record+0x0 | 2 | u16 | heap | appearance history | Shift register: shifted left each club match, with bit 0 set if the player appeared (helper 0x267D58, called from `pwkTeam_AddPlayerRecord` 0x267D80, tests the match entry's byte +6). | confirmed |
| record+0x2 | 6 | 6 x u8 | heap | hexagon | Radar values written by `plPinfo_CalcHexagon` 0x217CE0 (0x217D28, 0x217E0C, 0x217E18). | confirmed |
| record+0x8 | 0x44 | bytes | heap | cleared area | Cleared by the init at 0x2679A8 (`memset` of 0x44 bytes). Contents untraced. | confirmed |
| record+0x4C+14*row | 14 each (5 rows) | row struct | heap | season table | Row (14 bytes): +0 u16 goals, +2 u16 assists, +4 u16 games played, +6 u16 club games, +8 u16 man of the match, +0xA u16 average points x100 (weighted by +4), +0xC u8 red cards, +0xD u8 yellow cards. The u16 layout is confirmed by the combiners 0x267CA0 and 0x22F2D0. Row 0..4 is the competition kind; the row order (0 pre-season, 1 domestic league, 2 overseas league, 3 Euro, 4 international) is empirical, and which of +0xC and +0xD is red and which yellow is not proven. | confirmed field layout; row order and card bytes empirical |
| record+0xD8+14*row | 14 each (5 rows) | row struct | heap | career table | Same row layout, cumulative. | confirmed layout |
| record+0x92+14*row | 14 each (5 rows) | row struct | heap | last-season table | Read by the screens (accessor 0x22F388, time kind 1; kind 0 maps to +0x4C, kind 2 to +0xD8, kind 3 to +0x4C combined with +0x92) but no writer was found besides the init, which copies a 14-byte default row (source 0x399638, all zeros in the file) into each of the 15 rows (the loop at 0x267A00 onward, `s4` = 4..0). Rollover is not confirmed. The record ends at 0xD8 + 5*14 = 0x11E, exactly the record size. | read confirmed, writer unknown |
| B1+0x4F00+0x2A0*n, n = 0..23 | 0x2A0 each (24) | `PlPinfo` array | heap | youth squad | Same layout as the first team; negative id at +0 means empty (`pwkTeam_GetYteamData` 0x270C18 returns `get(1) + 0x4F00`; `pwkTeam_GetYpinfo` 0x270C98; the 24-slot loops end at +0x3F00). | confirmed |
| B1+0x8E00 | 0xBC | `PlMinfo` | heap | youth manager | Directly after youth slot 23 (24 x 0x2A0 = 0x3F00). `pwkTeam_GetYManager` 0x26BDD8 uses YteamData+0x3F00 and copies 0xBC bytes. | confirmed |
| B1+0x9438 | 30 x 0x20 | candidate list | heap | player candidates | s16 id at +0x8, turns listed at +0xB. Loop `slti 0x1E`, stride 0x20 in `pwkTeam_AddPlayerCandidate` 0x25B988. | confirmed |
| B1+0x97F8 | 30 x 0xC | candidate list | heap | youth candidates | s16 id at +0, turns at +0x9. Loop `slti 0x1E`, stride 0xC in `pwkTeam_AddYouthCandidate` 0x25BDF0. The list starts at 0x9438 + 0x3C0. | confirmed |
| B1+0xEA7C | 18 x 0xC = 216 | 12-byte records | heap | release list | u32 destination team at +0 (0 = free), u8 squad slot at +4, u32 `PlJoin` kind at +8. First-free fill, not slot-indexed (loop 0x11..0). `pwkTeam_GetNumReleaseListFreeBlank` 0x25A7C8 counts free records. Kind 5 is a loan out (`SIMPRG.REL` 0x128904, mail 329). A player on the list has flag 0x40 (`AddReleaseList` ORs 0x40 and clears 0xB0). Deleting zeroes only the team word, so slot and kind bytes stay stale. | confirmed |
| B1+0xEB54 | 25 x 0xC = 300 | 12-byte records | heap | out-of-team plan | u32 team at +0 (0 = free), u8 slot at +4, u8 flag at +5 (1 if a money value was given), 4-byte `PlMoneySave` at +8. First-free fill, not slot-indexed (`pwkTeam_AddOutOfTeamPlan` 0x25ABC8, loop 0x18..0). 0xEA7C + 216 = 0xEB54. | confirmed |
| B2 + 0xA8*idx | 0xA8 each, 440 records | club record | heap | other clubs' squads | `pwkOteam_Team2Otindex` 0x24B7E8: team 2 gives record 0, teams 3..441 give team - 2, anything else (team 1, 442 and above) gives -1, which `pwkOteam_GetPointer` 0x24B788 maps to record 1 (team 3). `pwkOteam_GetOpinfoPointer` 0x24B920 returns record+4 for team < 0x1BA. | confirmed |
| record+0x0 | 4 | u32 | heap | club team | Team field, stored by `pwkOteam_Init` 0x24A6A0 at 0x24A6E4. The init loop starts at team 3. | confirmed |
| record+0x4+6*k, k = 0..24 | 6 each | `<hBbBB` | heap | club squad entry | s16 database id, u8 age (+2), shirt byte (+3), u8 contract years (+4), u8 flags (+5, set to 0 by the init). Written by `pwkOteam_Init` at 0x24A700..0x24A72C, 25 times. Expanded to a full `PlPinfo` on demand by 0x24B1E8. The signed shirt type comes from `save.py`. | confirmed layout; shirt signedness empirical |
| record+0x9A | 1 | u8 | heap | friendship | Stored at 0x24A6F0, read at 0x24A7F0 and 0x24A814. | confirmed |
| record+0x9C | 4 | u32 | heap | league | `lw` at 0x22BF60 (`plTeam_GetTeamMainLeague` 0x22BF00) and 0x24BCF0, via `GetPointer`. | confirmed |
| record+0xA0 | 1 | u8 | heap | club rank | `pwkOteam_GetRank` 0x24BEC8 (`lbu` at 0x24BF58); `pwkOteam_Init2` stores it at 0x24A5F4. | confirmed |
| record+0xA2 | 2 | u16 | heap | rank points | `pwkOteam_Init2` 0x24A5B0 (`sh` at 0x24A600), copied from the database entry +2. | confirmed |
| record+0xA4 | 2 | u16 | heap | world club rank | `pwkOteam_GetWorldClubRank` 0x24BF70 (`lhu` at 0x24BFF0). | confirmed |

### Pointer chains and stability

Every heap entry is reached from the static root:

```text
P  = u32[0x3909A8]
H  = u32[P+0x1C]
B1 = H + u32[P+0x2C]        (block 1, your club)
B2 = H + u32[P+0x30]        (block 2, other clubs)
squad slot n   = B1 + 0x4D4 + 0x2A0*n     (n = 0..24)
youth slot n   = B1 + 0x4F00 + 0x2A0*n    (n = 0..23)
```

`get(i)` (0x21D928, via `pwGet` 0x21DA50) returns 0 for i >= 11. For an
absent block (offset word 0xFFFFFFFF) the branch delay slot at 0x21DA7C
loads `u32[P+0x1C]`, so the result is the bare `H`, not 0. Only block 8
can be absent, and only when `P+0x19` is set, which retail never does.
Blocks 1 and 2 are always present.

Common validity for all heap entries: `P`, `H` and the sum all lie in
0x100000..0x1FFFFFF, and a slot's s16 id at +0 is not negative. The
block contents are zero until New Game or Continue, so pair the chain
with a career or mode check (see the notes below). `P+0x18 == 0` always
holds in retail and costs nothing to test.

Common stability: `P`, `H` and every block offset are fixed from the
first script command of the boot until reset. New Game, Continue,
saving, a match, the year rollover and a return to the title do not
reallocate or reshuffle them. Whether the offsets are identical on every
boot is not settled (see Still unknown). The static address 0x3909A8 and
every offset inside a block never change on the PAL executable. The
title demo (`ROOTDEMOMATCHSEQ`, which sets the flag at 0x34D43C to 1,
then runs `Pwk.NewGame`) overwrites blocks 0..7 in place, so the data in
them is not a career while that flag is 1.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| PlPwork root | `0x3909A8` fixed; `P+0x1C`, `P+0x28+4*i` | `P != 0` from the first script command of the boot, for the whole boot. Not a career test. Test `P` in range and `P+0x1C` in range. | Address fixed. `P`, `H` and offsets are constant for the whole boot. Identity across boots unverified. |
| Squad array and id | `slot(n)`; id s16 at +0 | Career loaded (or a demo is not running: `u32[0x34D43C] == 0`), `u32[P+0x2C] != 0xFFFFFFFF`, id sign bit clear. | Stable over frames, menus, matches and season rollover. Slot index shifts with transfers, so key on the id. |
| Age and position | `slot(n)+0x8`, `+0x4` | Slot occupied, career loaded. Blocks are blank at boot and overwritten by the demo. | Stable in a session. Age changes at the year turn (writer untraced) and on squad change. Position changes only when the formation or position is edited. Japanese build not checked. |
| Abilities | `slot(n)+0xA+6*a` | Slot occupied. | Stable in a session. Changes through `pwkGUtl_AddExp`, edits, aging (untraced). Not during a match frame loop. |
| Database copy | `slot(n)+0x198..0x20B` | Slot occupied; rewritten whenever the squad entry is expanded (0x24B1E8). | Value-stable per player after joining, across seasons and saves. |
| Flags 0x20C | `slot(n)+0x20C` | Slot occupied. Bits 0x10 and 0x20 only when u8 `+0x21C >= 0xFC`. | Stable in a session. Writers of individual bits were not all traced, so use change detection. |
| Contract and wage | `slot(n)+0x218/+0x21D/+0x220/+0x224` | Own squad only, slot occupied, career running. | Years change at year end (writer untraced). Slot can be vacated and refilled. |
| Fatigue, condition, motivation, form, power, fit | `slot(n)+0x23C..0x24E`, `+0x29A` | Slot occupied. For condition also require bit 14 (mask 0x4000) of `u32[slot+0x20C]` to be clear. | Written only at turn processing, practice, year and season init, join and transfer events, not per frame. |
| Injury | `slot(n)+0x250/+0x254/+0x20C` | Career loaded. Kind meaningful only while value != 0. | Value and kind change during practice slots and after match results. Flags change immediately in a match, but in the match engine's own copy. Stale values survive across loads. |
| Popularity, status, captain, keyman | `slot(n)+0x238..0x25C` | Slot occupied and `plPinfo_UnPlay` false. | Constant between game events; persists in the save. |
| Play style | `slot(n)+0x278..0x292` | Slot occupied. | Stable in a session. `+0x290` and `+0x292` change only when `pwkPlayStyle_GetExp` runs (call cadence unverified). |
| Match statistics | `B1+0xEC88+0x11E*n` | Career loaded, slot is a real squad member. | Values change only in `CScheEuro::finalizeOneMatch` 0x203DD8 (call at 0x203EC0) for your own club's match, or on load or slot clear. Slot-to-player mapping is not stable across transfers. Rollover of +0x4C and +0x92 is unconfirmed. |
| Youth squad and manager | `B1+0x4F00`, `B1+0x8E00` | Career loaded, club has a youth team (slot 0 id >= 0). | Expected stable over a session; not verified at runtime. |
| Release list, out-of-team plan | `B1+0xEA7C`, `B1+0xEB54` | Career loaded. | Written only on a player action or turn processing. Stale slot and kind bytes remain after a delete, so count records by team != 0. |
| Other clubs | `B2 + 0xA8*idx`, `idx = team - 2` (team 2 gives 0) | Career loaded. Menus, matches and loading screens inside a career still see live data. | Stable in a session. Squad ids change on transfers. |

### RetroAchievements notes

- The chain itself is constant for a boot, so it needs no "is a career
  loaded" guard from the root. Gate on a separate mode or career check,
  and on `u32[0x34D43C] == 0` so the title demo (which overwrites the
  blocks in place) is excluded. The mode check is outside this part of
  memory. Still test `u32[0x3909A8]`, `u32[P+0x1C]` and
  `u32[P+0x2C] != 0xFFFFFFFF` for range, as a defensive check.
- Do not use `P != 0` to mean a career exists. It is non-zero from the
  first script command of the boot.
- The block base is the sum of two loaded values (`H` plus a block
  offset). A plain AddAddress chain cannot form a sum of two pointers.
  Use Remember/Recall (read `H`, remember, read the block offset, add,
  then AddAddress). Whether RA expresses this exactly was not tested
  here.
- Re-reading the chain on every evaluation is cheap defensive practice.
  The game itself does not move it during a boot.
- Identify players by the s16 id at slot+0, not by slot index. Squad
  slots shift on transfers and are reused. Empty slots are not zeroed:
  test the sign bit (value >= 0x8000).
- Use deltas, not levels, for event triggers. Most fields change only at
  turn processing, practice, year init, join or transfer events, so a
  change between frames is a clean trigger.
- Abilities: trigger on `exp > t[L]` using the table at 0x531C70, not
  `exp >= t[L]`, since exp == t[L+1] reads as level L. If the u16 at
  slot+0xE (ability 0 cap) is below 100, `plPinfo_ConvAbilLv` 0x216C90
  treats the fields as already converted levels. That state was not seen
  in normal play.
- Condition at +0x240: gate on bit 14 (0x4000) of `u32[slot+0x20C]`
  being clear, otherwise the value is a join counter, and a decrement
  from 0 can wrap to 0xFFFF.
- Injury: use the value at +0x250 != 0 as the injured test. Do not rely
  on `(flags & 0x300) == 0x100 or 0x200` alone. The heavy-to-light step
  in `plPinfo_CheckRecover` ORs 0x200 without clearing 0x100 (flags
  0x300), and 0x200 is not cleared on healing (see Unconfirmed). Flag
  0x400 is only a transient "just injured" mark.
- Wage: the stored unit converts as pound = stored / 6 and euro =
  stored / 4 (empirical, see the row). Compare relative values or
  calibrate against the screen.
- Season and career statistics: goals are the u16 at
  `B1+0xEC88+0x11E*n+0x4C+14*row` (season) or `+0xD8+14*row` (career).
  They change once per finished match of your own club, so a +1 delta is
  a per-match trigger. Which row is the domestic league is empirical
  (row 1). Do not use `pwkTeam_GetPlayerStats` 0x265810 with a non-zero
  second argument: it returns a stale scratch snapshot near 0x5EB1A0.
- Transfer events: watch a release-list record's team word becoming
  non-zero with kind 5 for a loan out, or flag 0x40 appearing on a squad
  player. For Promote a youth player, compare ids between the youth
  array and the squad array. `pwkTeam_GetNumReleaseListFreeBlank`
  0x25A7C8 gives free records, so used = 18 minus free.
- Other clubs: team 1 and teams outside 2..441 alias record 1 (team 3)
  in `pwkOteam_GetPointer`, so never read B2 for team 1 or for 442 and
  above (clubs 442..459 and the national teams have no record here).
- Loading a save decodes in place (`SAVEPRG.REL`), so the blocks are
  transiently inconsistent. Avoid reading during a load.
- The Japanese release keeps its pwork global at a different address
  (`DOC/JAPANESE_RELEASE.md` gives `lui 0x39` and `lw -0x36b8`, which is
  0x38C948), so none of the static addresses here carry over.

### Unconfirmed

Do not rely on these.

| Claim | Why not |
|---|---|
| A 65th ability slot at slot+0x184 | Refuted. a = 63 is at +0x184; a 65th would start at +0x18A and no code touches it. |
| Cap (+4) meaning as exp <= limit <= cap | Not read by any traced function. Empirical from `DOC/SAVE_FORMAT.md` (7,424 abilities in 5 saves). |
| Youth flag bit 0x800 at slot+0x20C as the youth selection flag | Refuted. The code tests 0x1000 in `pwkTeam_GetYpinfo`. Treat 0x800 as `IsYouth` only. |
| Flag bit 0 (0x1) as part of `IsRental` | Refuted. `IsRental` reads bit 1 only; bit 0 is "away on national duty" (set by `pwkTeam_LeavePlayer`). |
| `(flags & 0x300) == 0x100` or `0x200` as a reliable injured test | Disputed. A converted heavy injury can sit at 0x300, where both `IsHkega` and `IsLkega` are false, and 0x200 is not cleared on healing. Could not be reconciled with `DOC/INJURIES.md`; possibly a retail bug. Unverified in the running game. |
| Kind 8 / value 0xFFFF as permanent | Value 0xFFFF comes from `calcKegav` per `DOC/INJURIES.md`, not re-read. `CheckRecover` subtracts regardless and the roll at 0x21A208 covers kinds 3..7 only. Not proven permanent. |
| Averaging the top five popularity values for sponsor income | Not verified. |
| slot+0x258 `_lastgame_join` as minutes played in the last match | Offset and range 0..120 are in the developer field table and `plPinfo_CalcGTired` 0x21A680 reads it at 0x21A7D8 (thresholds 46 and 90), but no writer was found anywhere. Do not use it. |
| Style +0x292 as "progress toward the next style" | Refuted. It is cumulative and saturating. |
| Initial style being "the first stored path entry" | Refuted. Init uses the byte at +0x1F6, which is 0 if the database lists no styles. |
| Out-of-team plan as slot-indexed, and "agreed to leave" meaning | Refuted (first-free fill). The meaning is unverified. |
| Out-of-range team returns a dummy record past the end | Refuted. It returns record 1 (team 3). |
| `pwkTeam_GetPlayerStats` 0x265810 as "pointer to season stats" | Refuted. With a zero second argument it returns a pointer to the 0x44-byte cleared area; with non-zero it returns a stale scratch copy. |
| +0x92 as last season | The screen accessor 0x22F388 reads it as time kind 1, but no writer or year-end rollover was found. |
| Which of record row bytes +0xC and +0xD is red and which yellow, and the row order of the five competition rows | Not proven. The u16 fields are confirmed; the two card bytes and the row order are empirical. |
| +0x1CA "3D model entry index"; +0x1E6 "growth/ageing type" | Refuted. +0x1CA is the face number; +0x1E6 is injury resistance, and the growth types are +0x1E2..+0x1E4 (developer field table). |
| Loan limits (5 players out, squad floor 8) | From `DOC/EVS_PROCEDURES.md`, not re-verified in code. |
| Meaning of `PlJoin` values other than 5 | Not traced. |
| The single absolute 0x1E2D2A4 (squad array in one career) | One save state in `DOC/CAMP_FORMAT.md`; not a stable address. |
| Manager, coach and scout offsets (+0x9960, +0x9AC8, +0x9C30) and the 25 x 25 pair-combination table at B1+0x4808 | Documented elsewhere, not re-derived here. |

### Still unknown

- Whether the shuffled block order, and so `H` and every block offset,
  is identical on every boot. `plUty_ShuffleUint8` 0x235270 draws from
  the generator state at 0x569DC0, which `fcEuroRand_Init` 0x111698 sets
  to the constant 0x12345678, and `Pwk.Create` is the first script
  command. Other draws on that state before `Pwk.Create` were not
  enumerated. One PCSX2 session reading `u32[P+0x28+4*i]` on two boots
  would answer it. Do not hard-code offsets until then.
- Which code advances age (+0x8) at the year turn, and which code shifts
  the season table (+0x4C) into the last-season table (+0x92) and clears
  it. Probably `SIMPRG.REL` or `YRSTPRG.REL` year-start code.
- Writers of `PlPinfo` eval (+0x214, u16 0..1000), goal (+0x216) and
  gamenum (+0x217). Only zeroing in `pwkTeam_JoinPlayer`
  0x26523C..0x265248 was found. Eval is read by
  `_pwkTeam_CalcReconSalary` 0x265C68 and `pwkTeam_ContractUpdatePlayers`
  0x265FC8.
- Exact meaning of flag bits 0x2 (`IsRental`) and 0x4 (`IsHired`), and
  of 0x80000, 0x100000 and 0x800000 in the career record. Needs in-game
  tests of a loan in and a loan out.
- Behaviour of +0x228 comp (8 x u16), +0x244 motiwork (8 bytes), +0x264
  han_term (11 x u8), +0x270 explo (8 bytes), +0x29C slump (u32 0..13)
  and +0x21C life. Offsets and sizes come from the developer field table
  only.
- The meaning of the 0x44 bytes at `PlPlayerIndiv`+0x8..+0x4B (cleared at
  init, nothing else traced). The three 70-byte tables are fully
  accounted for, so the record has no unexplained trailing bytes.
- Match-time player state (stamina, live position, goals during a match)
  belongs to GAMEPRG/PlGiTask and is not covered. A match injury rewrites
  the flag word in the match engine's own team array, not in the career
  squad copy.
- Which table the selected lineup and substitutes use (formation slots
  per squad slot are in `PlTeamData`, not decoded).
- Whether the youth slots and other-club records hold fields beyond id
  and flags that match the first-team layout; youth slots were not
  field-checked past id and flags.
- Whether RetroAchievements Remember/Recall can express `H + block
  offset` as needed.
- The Japanese release (SLPM-66316) was not checked for these offsets.

### Checking the claims

Run each from the repo root. Each prints a disassembly to read.

```bash
# the root store (sw a2, 0x9a8(s1) at 0x21d65c) and the allocator
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21d65c 2
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork

# block lookup: pwGet returns H + offset, and the bare H for 0xffffffff
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 12

# block 1 plus 0x4b4 is your PlTeamData (addiu v0, v0, 0x4b4 at 0x2598b8)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x2598b4 8

# per-slot stats record: 25 records of 0x11e; init clears +0 (2 bytes)
# and +8 (0x44 bytes), then fills three 14-byte row tables
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x267af0 14
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x2679a8 40

# play-style count: the thresholds at 0x398f60, then the cap of 5
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x24de28 40
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkOteam_Team2Otindex
```

## Club finances and popularity

Club money, the income and payment accounts, popularity, club status,
sponsors, TV deals, merchandise, the stadium plan and the facility
levels live in one heap object, the Pwork save structure, in the PAL
release (`SLES_541.51`). Only one word is at a fixed address: the
static pointer at 0x3909a8. Every other address here is reached through
that pointer. The save serializers write the same live blocks
(`SAVE_FORMAT.md`), so these are live values, not save-time copies.

The pointer is set once, by the first script command of the boot
(`Pwk.Create`), so it is non-zero from boot on (title, demo, VS mode,
career) and the buffer and the block bases never move during one boot.
What changes on New Game and Load is the content of the blocks, which
is overwritten in place. Until New Game or Continue has run, the blocks
hold blank or stale data.

Money is stored in a base unit where 1 pound = 6 and 1 euro = 4
(yen = stored * 100 / 3). The rates are s16 values at 0x5314e8
(12, 3, 2, 400) used by plMisc_MoneyRate 0x215660, which computes
value * rate[to] / rate[from]. Which rate is the pound (2) and which is
the euro (3) is **empirical** (`SAVE_FORMAT.md`). Block k means block k
of the Pwork buffer: block 0 is general (money, date), block 1 is your
club, block 4 is the town, block 5 is the accounts. Full addresses are
blockBase(k) + offset. Block 1 has 0x129e8 usable bytes (the table at
0x533ac8 holds 0x129f0 with an 8-byte trailer).

Labels: **confirmed** means read in the game code (the symbol and
address are given); **empirical** means taken from the docs or from
data and not re-derived in code. Nothing here was run in PCSX2.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer | static | Pwork root | Pointer to the PlPworkTask object (0x5c bytes). +0x1c is the buffer base, +0x28+4k is block k's offset (k is 0..10), +0x18 is the ext-work flag (always 0 in retail), +0x19 flag skips block 8 (never set in retail), +0x54 is the total size. Non-zero from boot, constant for the whole boot. The static word is 0 only in the file image and before `Pwk.Create` | **confirmed**. plPwork_GetPwork 0x21d6e0 (`lui 0x39 / lw 0x9a8`), plPwork_CreatePwork 0x21d628 (stores, only caller 0x1104b8), plPwork_DeletePwork 0x21d698 (zeroes, only caller 0x110570, whose script command is unreachable), constructor 0x21d6f0, pwGet 0x21da50 |
| block0 = u32[p+0x1c] + u32[p+0x28], offset +0x0 | 8 | s64 | heap | Club money | Stored unit (1 pound = 6, 1 euro = 4, yen = value * 100 / 3). Negative means debt. pwkGen_Pay 0x2445f8 has no floor. pwkGen_Income 0x244570 ignores amounts <= 0 and adds with a 64-bit daddu, so money passes 2^31 (a save holds 7,308,451,892); the 0x7fffffff store fires only when the 64-bit sum wraps to <= 0. Written at once by pwkGen_Income and pwkGen_Pay, and in a lump by pwkGen_SetSikin 0x2444a8, whose game-code caller is the month report pwkRec_InMonthlyReport 0x252be0 (see the next two rows); the save load and the save editor also write it | **confirmed**. Reader pwkGen_GetSikin 0x2444e0. Rates read from the executable. Pound and euro assignment **empirical** |
| block5 + 0x0 + 8*type, type 0..11 | 8 | s64 x12 | heap | Month income lines | Current month totals. 0 Sponsor fee, 1 League contract, 2 Individual contract, 3 Season ticket sales, 4 Ticket price, 5 Win bonus, 6 Position prize money, 7 Merchandise, 8 Stadium facilities, 9 Transfer fee, 10 Rental fee, 11 Other income. Positive magnitudes. pwkGen_Income books every line into money at once and into the array; income type 7 is the exception: only the array gets it (booked by pwkRec_BeforeAcount 0x252b20 and by 0x251f08, see the Unconfirmed list), and it reaches money at the month report. The array is a log, not a ledger that sums to the money balance. Reset by the month report | **confirmed** layout (pwkRec_AddMonthlyIncome 0x252d88 adds at +8*type, pwkRec_AfterMonthlyReport 0x252c98 resets). The flag table at 0x3991e8 (12 bytes) is 0 except type 7 = 1 (read from the executable). Type names **empirical** (message strings) |
| block5 + 0x60 + 8*type, type 0..22 | 8 | s64 x23 | heap | Month payment lines | 0 Stadium purchase, 1 Stadium facilities, 2 Club house ext., 3 Club house facilities, 4 Practice ground ext., 5 Practice ground facilities, 6 Practice ground maintenance, 7 Facilities maintenance, 8 Youth mgmt, 9 Player salary, 10 Manager salary, 11 Coach salary, 12 Youth supervisor, 13 Scout, 14 Transfer fee, 15 Loan fees, 16 Pay for the job (player bonuses), 17 Advertising, 18 Overseas investment, 19 Overseas bases, 20 Match management, 21 Camp tour, 22 Casual (PR events and goods orders). Types 7, 8, 9, 10, 11, 12, 13, 17 and 19 are filled into the array only, by the function at 0x2528c0 (called from pwkRec_BeforeAcount 0x252b20), and leave money at the month report. All other types are taken from money at once by pwkGen_Pay 0x2445f8, which also adds to the array. At the report money changes by +income[7] minus the nine flagged payments only | **confirmed**. pwkRec_AddMonthlyPayment 0x252de0 adds at +0x60+8*type. pwkRec_InMonthlyReport 0x252be0 sums only the lines whose flag byte is non-zero in the tables at 0x3991e8 (income) and 0x3991f8 (23 payment bytes: 1 for types 7 to 13, 17 and 19, else 0, read from the executable), then calls SetSikin(GetSikin + income - payment) at 0x252c74 to 0x252c80. Positive for payments holds only if callers pass positive amounts (not checked per caller). Type names **empirical** |
| block5 + 0x130 + 8*type (income), block5 + 0x190 + 8*type (payment) | 8 | s64 x12, x23 | heap | Season account lines | Season totals. They exclude the current month: season total = this array + the month array. The monthly report rolls the month in and zeroes the month arrays; the annual report (pwkRec_AfterAnnualReport 0x253020) clears +0x130..+0x188 and +0x190..+0x240 | **confirmed** (pwkRec_AfterMonthlyReport 0x252c98, pwkRec_AfterAnnualReport 0x253020) |
| block1 + 0x12470 | 4 | u32 | heap | Ad budget per season | Stored unit. UI range 0..30,000,000. Init 3,000,000. Setter SetPR 0x271d50 does no clamping, so the limit is UI only | **confirmed** for address, init and setter: pwkUnkei_GetWork 0x271cf8 (block1 + 0x12470), pwkUnkei_Init 0x271be0, SIMPRG.REL 0x3ec08 calls SetPR on plan confirm. UI range **empirical** (`ECONOMY.md`) |
| block1 + 0x12474 | 4 | u32 | heap | Ticket price | Stored unit, UI range 60..300 (10 to 50 pounds). Init 60 | **confirmed** for address and init (SetTicket 0x271d98, SIMPRG.REL 0x3ec10). UI range **empirical** (`ECONOMY.md`) |
| block1 + 0x12478 | 4 | u32 | heap | Season-ticket rate | Percent of ticket price, UI range 50..150. Init 100 | **confirmed** for address and init (SetSeatRate 0x271ff0, SIMPRG.REL 0x3ec18). UI range **empirical** |
| block1 + 0x1247c | 4 | u32 | heap | Season-ticket price | = ticket * rate / 100 (integer). Set only when the plan screen is confirmed (SetSeatPrice, SIMPRG.REL 0x3ec48), so it does not track edits live. Not set by Init (0 from the memset) | **confirmed** |
| block1 + 0x12480 | 4 | u32 | heap | Season tickets on sale | Multiples of 100 up to 0.8 * stadium capacity (UI limit). Init 0 | **confirmed** for address and init (SIMPRG.REL 0x3ec20). UI limit **empirical** |
| block1 + 0x12484 | 1 | u8 | heap | Season tickets sold % | min(GetExpectSeat(...), 100), written by pwkUnkei_CalcSeat 0x2733a0 only when +0x10 != 0 and only when the plan screen is opened (SIMPRG.REL 0x3e3b8). A forecast, not a running count. Keeps its old value when season tickets on sale is 0 | **confirmed** |
| block1 + 0x11248 + 2*region, region 0..13 | 2 | u16 x14 | heap | Popularity per region | Region 0 is the home nation, 1..13 overseas. Changes only through pwkTeam_PopChange 0x267ff8: add delta, floor at 0, cap by the u16 at 0x554df0 + 2*rank (65,535, 50,000, 40,000, 30,000, 15,000, 10,000, read from the executable). New career: 2,000 at home (pwkTeam_PopInit 0x268138). Reader pwkTeam_Pop 0x267fb0 | **confirmed**. Dynamics and the supporters formula **empirical** (`ECONOMY.md`) |
| block1 + 0x11228 | 4 | s32 | heap | Popularity rank | 0..5, lower is better, only ever lowered (pwkTeam_PopChangeRank 0x2680c0 stores only when the clamped value is below the current one). Caps as in the row above: rank 0 = 65,535, 1 = 50,000, 2 = 40,000, 3 = 30,000, 4 = 15,000, 5 = 10,000. New career 5. Triggers (4 on promotion, 3 top-10, 2 prime cup, 1 first-division win, 0 European League) from `ECONOMY.md`, partly re-read at 0x269430, 0x268808, 0x268a98, 0x268ab0, 0x268a0c. Read it as 32 bits (a byte read works for 0..5 only). A loaded save can start at any rank | **confirmed** for the store and the caps; triggers **empirical** |
| block1 + 0x1126a | 2 | u16 | heap | Club status (hidden reputation) | 0..65,535. Capped by the u16 at 0x555150 + 2*statusRank (65,535, 60,000, 55,000, 40,000, 30,000, 25,000, 10,000, 7,000, 7,000, read from the executable). Moves at match checks and year end, not per frame. Written by pwkTeam_StatusChange 0x26dbb8 (lhu/sh at 0x126a, floor 0), reader pwkTeam_Status 0x26e2f0 | **confirmed** |
| block1 + 0x11264 | 4 | s32 | heap | Status rank | 0..8, only lowered (pwkTeam_StatusChangeRank 0x26dc50, clamp with plMisc_OFcheck(x, 8)). New career 7 (pwkTeam_StatusInit 0x26e328). A freshly lowered cap applies only at the next status change | **confirmed** |
| block1 + 0x46ac | 1 | u8 | heap | Club rank (stored) | min(status >> 11, 31), written by the function at 0x26dd40 (sb at 0x26dd84), read with lbu. New career 0 (pwkTeam_StatusInit). pwkTeam_GetMyClubRank 0x259b60 uses status / 2047, so the game's own club rank can differ from this stored byte | **confirmed** |
| block1 + 0x1126c | 4 | u32 | heap | Supporter random factor R | Stored 101..104 (0x65 + rand 0..3), rolled once per turn start by pwkSup_CalcSupporterRand 0x258370. pwkSup_GetSupporterRand 0x2583b0 returns the stored value if > 99, else 101 (0 for a null pointer); it is not an upper clamp. Fan count is not stored: pwkTeam_Supporter 0x259a30 = ((pop/20)^2 + 10,000) * weight * R / 10,000 per region (formula **empirical**). The earlier offset +0x126c was wrong | **confirmed**. The pointer function pwkSup_GetSupoorterPointer 0x2583f0 is `lui 1 / ori 0x126c`, so block1 + 0x1126c |
| block1 + 0x4e99 | 1 | s8 | heap | Stadium id (current) | Record of 3-byte sub-records {s8 current, s8 pending, u8 countdown}. +0 current stadium id, +1 pending id (0 when idle), +2 build countdown in turns (0 = none), +3 current stand level, +4 pending stand level, +5 stand countdown. Further triples at +6 (roof), +9 (light), +0xc (screen). 16 equipment slots of 2 bytes from +0xf (first byte read by pwkUnkei_GetShopIncome 0x272ab8; slots 1, 2, 3, 9, 15 drive shop income, **empirical**). plTeam_UpdateStadium 0x22a570 ticks the countdowns; at 0 it copies pending into current. plTeam_BuildStadium 0x229f90 resets stand level +3 to 0, so +3 can fall when +0 rises | **confirmed** layout. Reader pwkTeam_GetStadium 0x25d910 (block1 + 0x4e99). Start of a build 0x2297e0, completion tick 0x229838 |
| PLRESOURCECOMMON.PAC entry 0, table 7: u32 at stadium*0x80 + level*0x10 + 0x38 | 4 | u32 | file data | Stadium capacity | Not stored in RAM. Looked up by pwkUnkei_GetStandAllCapacity 0x271b48 from the stadium id and stand level (using the pending values while their countdown is set). Pack data, not a RAM address | **confirmed**. 0x229c28 gets the table with plResource_GetResourceDataBinPacTbbTbl(0, 0, 7), stride 0x80 |
| block4 + 0x0 | 4 | s32 | heap | Business cycle (keiki) | 0..4. Scales build cost (125, 110, 100, 90, 75 %) and transfer fees (1.25, 1.1, 1.0, 0.9, 0.75). Written only through helper 0x271600 (value from the byte table 0x555ff8, 5 is a re-roll marker that is not stored), called via pwkTown_Init 0x271868 and pwkTown_UpdateAnnualy 0x2718b0 (once per season). Reader pwkTown_Keiki 0x2718e0 | **confirmed** for address, range and writers. Direction "0 boom .. 4 slump" is inferred from the higher costs at 0 (**empirical**). Other effects (camp, tour, TV, merchandise, PR chance) from `ECONOMY.md`, not traced |
| block1 + 0x11cc4 + 0x14*slot, slot 0..13 | 20 | u32 id + record | heap | Sponsor slots | 14 records of 0x14 bytes. +0 u32 sponsor database id (1..212, 0 = empty, expired contracts are zeroed). +4 u8 years served (incremented for all 14 slots at year start, SIMPRG.REL 0x16af98). +5 u8 holds 1 for the five sponsors and 2 for the supplier at init, read as contract length by fit (**empirical**, the expiry compare was not read). +6 u8 slot index. Slot 0 = main sponsor (block1 + 0x11cc4), 1..12 = sub-sponsors, 13 = supplier (block1 + 0x11dc8). New career: slot 0 id 193, slots 1..4 ids 184, 199, 187, 198, slot 13 id 212, slots 5..12 zero. Not negative when empty | **confirmed** for base, stride, ids and init: copied by 0x257200 from the static table at 0x3994a8 (byte 6 0xff gives slot 0, 0xfe sequential slots, 0xfc slot 13); GetMainSponsor reads +0x1cc4, GetSupplier +0x1dc8. +4 confirmed (SIMPRG.REL 0x16af98), +5 meaning **empirical** |
| block1 + 0x11c54 + 0x10*i, i 0..2 | 16 | record | heap | TV contracts | 3 records. +0 u32 station (0 = free), +4 u32 amount, +8 u8 years served, +9 u8 contract length. Yearly payment = sum of amounts * 100, booked as income type 2 by pwkTv_Add_TVpremium (SIMPRG.REL 0x163e88; income types 1 and 2 are the league and individual media licensing, so type 2 fits). Written by the first-free-slot function at SIMPRG.REL 0x164470 (callers 0xb0764, 0xb076c, 0xb1914; it sets +8 to 1 and zeroes +0xb, +0xc, +0xd), cleared on expiry at 0x164530. pwkTv_UpdateStatus 0x164598 increments +8 each update and clears the slot when +9 < the new +8, and the helper at 0x164570 returns +9 < +8. Slots are compacted by pwkTv_UpdateStatus, so count occupied records | **confirmed** for base, stride, station, amount, the payment and the +8 and +9 reading (canon re-read of SIMPRG.REL 0x164598 and 0x164570). +0xa and +0xb..+0xd meaning is open (see Unconfirmed) |
| 0x3991e0 | 4 | s32 | static | Last month merchandise income | Stored by 0x251ed8 (low 32 bits of pwkGd_GoodsMonthlySales(1), `sw` at -0x6e20 from 0x3a0000) and read by pwkRec_CalcMonthGoodsIncome 0x253008. Its caller 0x251f08 adds the same value to income type 7 (call at 0x251f1c), so it equals the income applied, not a pre-estimate. Never cleared on new game or load, so it is stale (0 or the last session's value) until the first month end of the career | **confirmed**. No clear was found; whether other code touches it was not checked |
| block1 + 0x12700 + 0x10*i, i 0..11 | 16 | record x12 | heap | Goods slots | 12 slots (0xC0 bytes) on sale. +0 u8 id (0 = empty), +1 u8 month put on sale, +4 stock, +8 sold, +0xc s16 player. The order function SIMPRG.REL 0x164ec8 picks the first slot with id 0 (`lbu +0`), writes the id, the month (PlDate byte 3), the stock, zero sold and the player. Stock and sold change at the month end and when ordered | **confirmed**. Stock and sold are 32-bit; their signedness is open (see Unconfirmed) |
| block1 + 0x4e8d + 3*i, i 0..3 | 1 | s8 | heap | Office equipment level | Each is a 3-byte record {level, target level, build time left} at block1 + 0x4e54 + 0x39 + 3*i. Unbuilt is 0, not -1: pwkTeam_InitChouse 0x25db10 zeroes the four level bytes (loop at 0x25db90). Starting a build fills bytes 1 and 2 only (helper 0x2297e0, plTeam_BuildChouseOfEquip 0x22ab98). Byte 0 rises on the completion tick (0x229838, via plTeam_UpdateChouse 0x22ac10 and pwkTeam_UpdateEquip 0x25dc08). Reader pwkTeam_GetOfficeEquipsLv 0x25dbb8 (`lb 0x39`) | **confirmed**. Values above 1 are unverified |
| block1 + 0x4e54, size 0x45 | 0x45 | structure | heap | Club house | Ends where the stadium structure begins (+0x4e99). +0x00 is a header byte (zeroed by InitChouse). +0x03 + 3*i (i 0..8) and +0x1e + 3*i (i 0..8) are 18 three-byte facility records whose byte 2 is -1 (none) or an equipment id; InitChouse fills those 18 bytes (+0x05..+0x1d and +0x20..+0x38) with -1, and the equipment setter 0x22a970 compares byte 2 with -1 and stores the id there (sb at 0x22a9e4). +0x39 + 3*i (i 0..3) are the four office records of the previous row. The facility records are not {level, target, countdown}. Accessors 0x229910 (chouse + 3 + 3*i, i < 9) and 0x229950 (chouse + 0x1e + 3*i, i < 9). Reader pwkTeam_GetChouse 0x25dae0. Build function 0x22a8f8 | **confirmed** for the layout above (InitChouse 0x25db10 read in full). What byte 0 and byte 1 of a facility record hold is **empirical** and not traced |
| block1 + 0x4ed4 | ? | record | heap | Practice ground site | pwkTeam_InitSite 0x25d8d0 sets byte 0 = 0 and byte 3 = 1. Layout otherwise unverified. Reader pwkTeam_GetSite 0x25d8a0 | **confirmed** for the reader and the two init stores; the rest is open |
| block0 + 0x88 | 16 | PlDate | heap | Current date | u16 at +0x88 first year of the season (Jan to Jun keep the season's year, so March 2007 shows 2006), u8 at +0x8a turn of season 0..95 (8 per month from July, turn 0 = July), u8 at +0x8b month 1..12, u32 at +0x8c turn within month 0..7, u32 at +0x90 that turn / 2, u32 at +0x94 that turn & 1 (0 first, 1 second, **empirical** midweek or weekend meaning). Reader pwkGen_GetDate 0x244368 copies 0x10 bytes. New game starts at 2005 turn 92 (June, the opening playoffs); the first real season is 2006 turn 0 | **confirmed** reader and layout (plMisc_SetTurn2Date 0x214698: month = ((turn>>3)+6)%12+1; start values pwkGen_Init 0x244220 / 0x2441c8, pwkGen_SetStartYear 0x2442e8). The writer of the live copy was not traced |

### Pointer chains and stability

Every row hangs off the same root. For all chains: p = u32[0x3909a8];
H = u32[p+0x1c]; blockBase(k) = H + u32[p+0x28+4*k]. Note that this is a
sum of two loaded values (H is a heap address, the offset word is an
offset), not a single pointer followed by a constant. pwGet 0x21da50
returns 0 only for k >= 11. An offset word of 0xFFFFFFFF would give the
bare H (the load sits in a branch delay slot), and the `get` function
0x21d928 returns 0 for k = 8 only when the byte at p+0x19 is non-zero
(never in retail). Blocks 0, 1, 4 and 5, the ones used here, are always
present.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| Pwork root | p = u32[0x3909a8] | p is non-zero from boot on (title, demo, VS mode, launcher, career), because `Pwk.Create` is the first script command (ROOTMAINSEQ offset 0x10, callback 0x110498) and `Pwk.Delete` is unreachable (offset 0x1a20 behind the unconditional branch at 0x1970). So p != 0 does not mean "in a career". Also require u32[p+0x1c] to be a plausible heap address (0x00100000 to 0x01FFFFFF). u8[p+0x18] is 0 in retail (ext-work swap, dead code: prepareExtWork 0x21d980 and deleteExtWork 0x21d9e0 have no caller) | 0x3909a8, u32[p+0x1c] and every u32[p+0x28+4k] are constant for the whole boot: New Game and Load run in place (pwkGen_Init memsets block 0 and the save decoder writes into the blocks). The block order is shuffled once, in the constructor (plUty_ShuffleUint8 0x235270). Whether the order is identical on every boot is unresolved |
| Money | block0 = u32[p+0x1c] + u32[p+0x28]; s64[block0] | A career has been started or loaded (gate: see the notes). During a match the value is stale until after-match booking (not traced) | Base fixed for the boot. The content jumps on New Game or Load |
| Accounts | block5 = u32[p+0x1c] + u32[p+0x3c] | As above. Month array resets at the monthly report, season arrays at the annual report | Base fixed for the boot. Values rise within the month and drop at the reports |
| Season plan | block1 = u32[p+0x1c] + u32[p+0x2c]; plan = block1 + 0x12470 | As above. Init defaults (ad 3,000,000, ticket 60, rate 100, seats 0) until the plan screen is confirmed. +0x14 is meaningful only when +0x10 != 0 and after the plan screen has been opened | Base fixed for the boot. Content jumps on New Game or Load |
| Popularity, rank, status, R, stadium, sponsors, TV, goods, facilities | block1 as above, plus the offsets in the table | As above. R may hold 0 before the first turn start (the game reads that as 101). Pop and status change only at discrete events | Base fixed for the boot. Offsets inside block 1 are code constants. Values persist through saves |
| Business cycle | block4 = u32[p+0x1c] + u32[p+0x38]; s32[block4] | As above, value in 0..4. Changes once per season, so a jump across a load is not a season change | Base fixed for the boot. Block 4 is overwritten by a save load |
| Date | block0 = u32[p+0x1c] + u32[p+0x28]; date = block0 + 0x88 | Sanity gate: year 2005..about 2040, month 1..12. Readable during matches; changes only on a turn advance | Base fixed for the boot. Zero year before New Game or Continue |
| 0x3991e0 | static, no chain | Meaningful only after one month end in the current career | Fixed address, survives screens and menus, not reset on new game or load |
| Stadium capacity | PLRESOURCECOMMON.PAC data, not RAM | – | – |

### RetroAchievements notes

- Do not gate on p != 0: it is non-zero from boot. Gate on state that
  says a career is running, from other domains: the schedule object
  pointer u32[0x390650] != 0 with u32[S+8] == 0x406c78 (S is that
  pointer; 0x406c78 marks the Normal career mode, 0x406b98 the opening
  playoffs, 0x406ab8 VS mode and the title demo, from CreateScheEuro
  0x202a50), and the demo flag u8[0x34d43c] == 0. Add the date sanity
  check (year 2005 to about 2040, month 1..12), because the blocks are
  blank or stale until New Game or Continue. These gate words were read
  in the code only, not in a running game.
- p, u32[p+0x1c] and the block offsets do not change during a boot, so
  a change of p or of u32[p+0x1c] is never a sign of a load. A load or
  a New Game shows only as a jump of the content (date, money, ranks)
  on one frame. Ignore a "decrease" of popularity rank, or a jump in
  money or popularity, on the frame where the date or the career gate
  changes. Re-reading the chain each frame is defensive practice, not a
  requirement. Do not hard-code a resolved block address, because it is
  not known whether the shuffled order is the same on every boot.
- Use delta logic (previous frame versus current) on the values.
- Starting values: popularity rank 5, status rank 7, club rank 0, home
  popularity 2,000, ad budget 3,000,000, ticket 60. A career loaded from
  a save can start at a better rank, so compare with the value at the
  first valid frame.
- Money is s64 in stored units. Do not assume a 2^31 ceiling (the cap
  is dead code under 64-bit adds). A 32-bit low-word read is enough for
  small thresholds; use both words near 2^31. Use stored-unit
  thresholds: the shown currency depends on the player's region
  (1 pound = 6, 1 euro = 4).
- Money changes at once for most bookings (pwkGen_Income, pwkGen_Pay),
  but at the month report it also changes in one jump by +income[7]
  (merchandise) minus payments 7 (facilities maintenance), 8 (youth
  management), 9, 10, 11 (player, manager, coach salary), 12 (youth
  supervisor), 13 (scout), 17 (advertising) and 19 (overseas bases),
  written by pwkGen_SetSikin. So a single-frame jump of this size is
  not an income event. Loads and the save editor also write money.
- For "earned X" triggers use the account lines rather than money, and
  remember that the account lines are a log: a line can rise without
  money moving (the nine flagged payments and income type 7 only reach
  money at the report). Deltas of the month arrays are clean, but they
  reset at the monthly report, so ignore drops. For a season total read
  season[+0x130] plus month[+0x0]. The season array only gains the
  month at the report.
- Popularity and status use thresholds, not equality (they move after
  matches, at month and year ends, and with player moves). Prefer
  popularity thresholds to a fan count, which is not stored. Status
  rank, popularity rank and club rank change only at discrete events,
  so a frame delta works.
- "Win the league" and "win the European League" map to popularity
  rank <= 1 and == 0 (read the rank with 32 bits). These triggers are
  **empirical** (`ECONOMY.md`). The stored club rank byte
  (status >> 11) can differ from the rank the game shows.
- Stadium upgrades: id (+0) and stand level (+3) rise when construction
  finishes, not when it is bought. A purchase shows as the countdown
  (+2 or +5) going from 0 to non-zero with the pending byte holding the
  new value. Buying a new stadium resets +3 to 0, so +3 can fall.
  Capacity is not in RAM; use the id and level as the proxy.
- Office equipment and facility levels likewise rise on the completion
  tick; an unbuilt office item is 0, not -1. The -1 values in the club
  house structure are the "no equipment" marker in byte 2 of the 18
  facility records.
- Sponsors: an empty slot is 0, so test id > 0. A new career already has
  ids in slots 0..4 and 13, so "sign a main sponsor" cannot be a
  transition from empty. Watch the id or the fee change, or income
  line 0, instead.
- Do not read the TV stack copy used by Pwk.CheckTV. It is transient.
  Count occupied records (station != 0).
- 0x3991e0 is a fixed-address read of last month's merchandise income,
  but it is stale after a new game or load. Block 5 income type 7 is
  the cleaner source.
- Ticket price "at minimum" is reliable only after the plan has been
  confirmed. While the plan screen is open the live struct still holds
  the old values. The UI limits are not enforced by the game, so an
  edited save can exceed them.
- Season tickets sold % (+0x14) is a forecast refreshed when the plan
  screen opens, not a live sales count.

### Unconfirmed

Nobody should rely on these.

| Item | Why |
|---|---|
| Sponsor record +5 as contract length | Fits the init values (1 for sponsors, 2 for the supplier) and the +4 years-served counter, but the expiry compare was not read |
| Sponsor record +7 and +0xc (fee x 100 at signing) | The signing code (SIMPRG.REL 0xc8234) was not re-read |
| TV record +0xa kind and bytes +0xb..+0xd | Meaning unknown (+0xa is compared with 4 and 7 at SIMPRG.REL 0x1641c0; the first-free-slot function zeroes +0xb, +0xc, +0xd) |
| Income type 7 booked twice | pwkRec_BeforeAcount 0x252b20 books pwkGd_GoodsMonthlySales(0) as income type 7 (call at 0x252b3c), and 0x251f08 books pwkGd_GoodsMonthlySales(1) (call at 0x251f1c). Which caller runs when, and whether both fill the same month, was not traced |
| Callers of pwkGen_Pay and pwkGen_Income per type | pwkGen_Pay has four direct callers in the executable (0x26a978, 0x26ac94, 0x272f68, 0x272f74) and pwkGen_Income five (0x272f24 to 0x272f5c); overlay callers were not enumerated, so which type each non-flagged line is booked through is not listed |
| Goods stock and sold signedness | Earlier readings disagree (s32 versus u32) |
| Whether 0x251ed8 or pwkGd_GoodsMonthlySales(1) is called from anywhere else | Not checked |
| Which writer advances the live PlDate at block0 + 0x88 | Not traced; plMisc_SetTurn2Date writes into a caller buffer |
| Whether u8 at +0x94 means midweek or weekend | The values 0 and 1 are the turn parity (`& 1`), the meaning is from the docs |
| Meaning of the extra bytes of the stadium record | Slot semantics of the 16 equipment slots, site layout, and what the facility records' byte 0 and byte 1 hold were not traced |
| Which stadium or facility writers run from SIMPRG.REL | Earlier "SIMPRG.REL 0x153c28" claim for stadium and facility levels was not confirmed; the SLES functions in the table were found, the SIMPRG callers were not traced |
| How often pwkTeam_UpdateEquip and plTeam_UpdateStadium tick | Per turn or per month, not checked |
| Meaning of the word at 0x35c970 gating CreatePwork | It is an init latch, initial 1, cleared at 0x110500 and set back to 1 at 0x110518 by the poll; the script calls the command once |

### Corrections to earlier statements

- Money is not capped at 0x7fffffff: the branch is dead code under the
  64-bit add. `SAVE_FORMAT.md` line 149 wording is misleading on this.
- An empty sponsor slot is 0, not negative. An unbuilt office item is
  0, not -1.
- The supporter factor R is at block1 + 0x1126c, not + 0x126c
  (`ECONOMY.md` line 305 carries the same typo).
- Stadium bytes +2 and +5 are countdowns, not flags.
- 0x3991e0 is the value applied to income type 7, not an estimate
  written before the report.
- The pointer 0x3909a8 is not zero outside a career, and the buffer is
  not re-created or re-shuffled on a new game, a load or a return to
  title.
- The month lines are not summed into money as a whole: only income
  type 7 and nine payment types are applied by the month report.
- The 3-byte {level, target, countdown} layout holds for the four
  office records only, not for the facility records of the club house.

### Still unknown

- Whether the shuffled block order, and therefore every block base,
  is the same on every boot of the same build. The generator state at
  0x569dc0 starts from a constant, but other draws before
  `Pwk.Create` were not enumerated, and nothing was measured in PCSX2.
- Whether the date at block0 + 0x88 and the other blocks are intact
  across New Game and Continue (blank at boot only).
- Which flag best separates "career menus", "in a match" and "demo"
  in this domain; the gate words in the notes come from other domains.
- No club loan or debt structure was found; debt is negative money, and
  payment 15 "Loan fees" is for player loans. No owner or board
  evaluation variable was found (only the Owner name string in the
  message system, SetOwnerNameString 0x201a88, and owner-team
  player-move helpers).
- Sponsor slot bytes +7, +0x10, +0x11, which category each of slots
  1 to 12 stands for, and the contract length or years remaining rule.
- Overseas branch bytes in block 4 (pwkTown_GetPlOverseasBranchPointer
  0x271940) decide which regions count towards supporters. The layout
  is in `PLRESOURCESIM_FORMAT.md`, not re-derived.
- Stadium capacity as a resident copy of PLRESOURCECOMMON.PAC entry 0
  was not located in RAM.
- Whether 0x3991e0 is kept or cleared between months beyond the
  reading above (no clear was found).
- The addresses are PAL only. The Japanese save drops six u16 at PAL
  block1 + 0x129d8 and shares offsets only where documented as the same.
  The Japanese address of the root is not `lui 0x39 / lw 0x9a8` (the
  pwork global there is `lui 0x39 / lw -0x36b8`, 0x38c948, per
  `JAPANESE_RELEASE.md`), and no value was checked on a Japanese disc.
- Wages: payments 9 to 11 are salary lines, but no per-player wage
  field or wage formula was found in this domain.
- Fan count has no stored value; its monthly dynamics and the overseas
  weights (tables at 0x553100 and 0x553110) were not read in full.
- Nothing was run in PCSX2. No pointer chain, value or timing here has
  been read from a live game. Only Nexxus's save-state read of block 1
  on 2026-10-27 (`SAVE_FORMAT.md`) supports the chain in practice.

### Checking the claims

```bash
# the root word: lui 0x39 / lw 0x9a8
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21d6e0 3
# the only caller of CreatePwork is inside the Pwk.Create callback
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork
# the month report sums only flagged lines (tables 0x3991e8 and 0x3991f8)
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkRec_InMonthlyReport
# the nine flagged payment types are booked into the array only
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x2528c0 40
# pwkGen_Income: 64-bit add, the 0x7fffffff store is a wrap branch
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkGen_Income
# the club house: -1 in byte 2 of 18 facility records, 0 in 4 office levels
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkTeam_InitChouse
# SIMPRG sets the ad budget (call at 0x3ec08)
python SRC/snr2.py xref ISO/DLL/SIMPRG.REL pwkUnkei_SetPR__5ParamUi --sles ISO/SLES_541.51
```

## Transfers, contracts and scouting

Almost all transfer, contract and scouting state sits in the save-work
heap buffer (the PlPworkTask object). Its blocks are reached through
the static word at 0x3909a8. A few true statics exist: the club-offer
arrays and the youth join list. The transfer window itself is not
stored: it is a pure function of the month byte of the current date.
All addresses are the PAL release (`SLES_541.51`). Everything here was
read from the game code and `DOC/SAVE_FORMAT.md` (static analysis).
Nothing was run in an emulator, and none of it has been seen in PCSX2.

Notation: P = u32 at 0x3909a8 (the PlPworkTask). B = u32 at P+0x1c
(buffer base). Block k = B + u32 at P+0x28+4*k. B0 = block 0 (general
state), B1 = block 1 (your club), B5 = block 5 (records).

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 (P); P+0x1c = B; P+0x28+4*k = offset of block k (k = 0..10) | 4 | u32 pointer to a heap PlPworkTask; block offsets are u32 in a shuffled order | static root, heap object | pwork root and block resolver | Pointer to the live PlPworkTask. It is non-zero from boot (Pwk.Create is the first script command and Pwk.Delete is unreachable), so it is also set on the title screen, in the demo and in VS mode. Block k is at B + offset k. The offsets come from a shuffle done once in the constructor, so read them instead of hard-coding them. An offset of 0xffffffff marks an absent block, but pwGet then returns B, not null, so test the offset yourself (only block 8 can be absent, and only when byte P+0x19 is set, which never happens in retail). The static word is written by plPwork_CreatePwork 0x21d65c and cleared by plPwork_DeletePwork 0x21d6c8. | confirmed (plPwork_GetPwork 0x21d6e0, pwGet 0x21da50, get 0x21d928, ctor 0x21d6f0, ROOTMAINSEQ script offsets 0x10 and 0x1a20) |
| B0+0x88 = B + u32[P+0x28] + 0x88 (month byte at +0x8b, turn-in-month u32 at +0x8c) | 16 | PlDate: u16 year, u8 turn (0-95), u8 month, u32 turn-in-month (0-7), u32 +8 (turn-in-month / 2, 0-3), u32 +0xc (turn-in-month & 1) | heap | Current date and transfer-window phase | Month 1 gives phase 3, months 2-6 phase 4, months 7-8 phase 1, months 9-12 phase 2 (table 0x5314a0: 0,3,4,4,4,4,4,1,1,2,2,2,2). The window is open when the phase is 1 or 3, so in months 7, 8 and 1. Turn 0 is July. Open day: month 7 or 1 and turn-in-month 0 (turns 0 and 48). Close day: month 9 or 2 and turn-in-month 0 (turns 16 and 56). Phase 4 (months 2-6) is the "special" phase. The year field is the first year of the season (January to June keep it). A new game starts at 2005 turn 92 (June, the opening playoffs), and the first real season is 2006 turn 0. | confirmed (plMisc_TransferMarketSchedule 0x214bc0, IsTransferMarketOpen 0x214ac8, OpenDay 0x214b10, CloseDay 0x214b50, SetTurn2Date 0x214698, pwkGen_GetDate 0x244368, IncDay 0x2443d0, pwkGen_Init 0x244220) |
| B0+0x18158 = B + u32[P+0x28] + 0x18158 | 6000 | array[1500] of {s16 id, u8 +2, u8 +3 date byte}, stride 4 | heap | Free-agent pool | Unattached players. A slot is empty when the s16 id is negative (-1). Count the non-negative ids for pool size. Deletion writes -1 to the id and 0 to +2 and +3, leaving holes, and the sort at 0x2361a0 reorders entries, so key on id, not slot. addFreePlayer refuses edit players. A new entry goes into the first empty slot (lowest index). When no slot is empty, slot 0 is the one that is retired (its id goes to the retire list) and overwritten. Byte +3 is filled from the turn byte of the date. Initial fill comes from PLRESOURCESIM entry 15 (1,300 present). | confirmed (helper 0x235840, getFreePlayer 0x235e18, checkExistenceFreePlayer 0x235eb0, addFreePlayer 0x235f08, deleteFreePlayer 0x235fb8) |
| B1+0xea7c = B + u32[P+0x2c] + 0xea7c | 216 | array[18] of {u32 team (0 = empty), u8 squad slot at +4, 3 pad, u32 join at +8}, stride 0xc | heap | Release, sell and loan-out list | Pending outgoing moves of your own players. +0 destination club (non-zero = in use; team 2..0x1b9 also updates the other club's friendship), +4 squad slot of the leaving player, +8 PlJoin kind. Kinds 0, 4 and 5 are used by callers; kind 5 is passed as the loan-out flag to PlayerOutCallBack. Adding sets 0x40 and clears 0x80, 0x20 and 0x10 in the player's flag word at +0x20c. The entry is cleared (+0 to 0) when the move executes or is cancelled; +4 and +8 keep stale values. The cancel path clears only +0 and flag 0x40. A full list (18 used) also suppresses computer club offers. | confirmed (pwkTeam_AddReleaseList 0x25a830, InitReleaseList 0x25a470, DeleteReleaseList 0x25a4d0, CheckReleaseListExistence 0x25a6d8, GetReleaseList 0x25a5a0, CheckReleaseListFreeBlank 0x25a750) |
| B1+0xa08c = B + u32[P+0x2c] + 0xa08c | 16900 | array[25] of {PlPinfo 0x2a0 (s16 id at +0, u8 age at +8), u32 join kind at +0x2a0}, stride 0x2a4 | heap | Pending incoming transfers | Players you agreed to sign or loan in who have not joined. In use when the s16 id is >= 0. Join kind 0 = permanent, 4 = loan-in; no other kind can be added. AddPinfoTransfer requires pinfo+0x190 non-zero and sets 0x40 in byte +5 of the player's opinfo at his old club (then masks that byte with 0x4f). AddPinfoTransferAge adds 1 to the age byte of each used entry (25 entries). GetMemberNumber(2) counts used entries, (5) counts kind 4. Saved with block 1. | confirmed (pwkTeam_AddPinfoTransfer 0x259ef8, CheckPinfoTransferExistence 0x259e08, GetPinfoTransfer 0x259da8, AddPinfoTransferAge 0x25a030, GetMemberNumber 0x2667b0, jump table 0x554670) |
| 0x390df8 (count), 0x5f8c58 (records), 0x5f8d48 (special count) | 4 + 240 (+0xcc special) | u32 count; array[10] of 0x18-byte records; special block: u32 count at 0x5f8d48, 25 x u32 at 0x5f8d4c, 25 x u32 at 0x5f8db0 | static (data and BSS) | Club offers for your players (computer clubs) | Ordinary offers. Record: +0 s32, +4 s32, +8 u16, +0xa three u16, +0x10 and +0x14 s32 in the game's save-money encoding (CPlMoneySaveCtrl). The sim-step wrapper at 0x2261a0 (table entry at 0x390e14) first runs Clear, which zeroes the count and records (and empties the special lists), so the count reads 0 whenever the refill does not happen. It refills through CComOffer::Execute only when date-struct +4 (turn-in-month) is 0 or 4, and Execute then adds two gates: (1) from year 2006 on, in months 7 to 12 it skips the refill when date +8 is below 2, which means turn-in-month 0 is skipped and only turn-in-month 4 runs; in months 1 to 6 both 0 and 4 run; (2) CheckReleaseListFreeBlank must be non-zero, so a full release list gives no offers. The count is not decremented when mail is read, so it is "pending since the last step", not a pulse. Special offers use the 25-entry lists at 0x5f8d48 (SetOfferData routes there when COM_OFFER_WORK+8 is 1). No cap of 10 on the ordinary count was verified. Field meanings other than the layout are unknown; use the count only. | confirmed (plTeam_GetComClubOfferNum 0x228540, GetComClubOfferDataPointer 0x228550, wrapper 0x2261a0, Execute__CComOffer 0x224460, CComOffer::Clear 0x224640, SetOfferData 0x2249d0, COM_OFFER_DATA::SetOfferData 0x224680) |
| B1+0x9438 (players), B1+0x97f8 (youth), B1+0x9960 (managers), B1+0x9ac8 (coaches), B1+0x9c30 (scouts); each = B + u32[P+0x2c] + offset | 960 (players); 360, 360, 360, 156 for the others; 2196 in all (B1+0x9438 to 0x9ccc) | players: 30 x 0x20 (s16 id at +8, u8 turns at +0xb); youth: 30 x 0xc (id at +0, turns at +9); managers and coaches: 30 x 0xc (id at +4, turns at +8); scouts: 13 x 0xc (id at +4, turns at +8) | heap | Scouting candidate lists | Results of scout and club searches. Id -1 = empty. Every turn pwkTeam_CandidatesDecrement counts each non-empty record's turns down and clears it at 0 (players and youth store id -1; staff go through deleteCandidates). A record whose turns byte is already 0 is skipped and stays. Youth candidates start with turns 8 (at +9) and age 16 (at +8). The Transfer List scouting page reads them. | confirmed (pwkTeam_AddPlayerCandidate 0x25b988, AddYouthCandidate 0x25bdf0, AddManager/Coach/ScoutCandidate, CandidatesDecrement 0x2643c8, UpdateYouthCandidates 0x262c40) |
| B0+0x12ec = B + u32[P+0x28] + 0x12ec | 72 | PlDisableWork array[18] of {s16 id, s8 counter, 1 unused byte}, stride 4 | heap | Negotiation lockout list | pwkGen_SetNegotiateDisable (script-callable; no direct jal in the executable) stores a player id with counter 12 in the first slot whose counter is 0. A slot is active only while the counter is > 0; an expired slot keeps its stale id, so "id == -1" is not the empty test. IsNegotiateDisable(id) is true while an entry with that id has counter > 0, also true when all 18 slots are in use, and true when the block pointer is 0. The counter drops (clamped at 0) only on turns where PlDate+8 equals 1, so the lockout is not exactly 12 turns. Read by pwkTeam_SetScoutModeRequest (call at 0x26d8a8). | confirmed (pwkGen_SetNegotiateDisable 0x244868, IsNegotiateDisable 0x2448b8, DecNegotiateDisable 0x244900, plDis_Add 0x2e92f0, plDis_IsDisable 0x2e9368, plDis_DecDisable 0x2e93b8) |

### Pointer chains and stability

Pwk.Create runs once per boot, so the root chain is fixed for the
whole boot. New Game and Load run pwkGen_Init and similar functions in
place, and never re-create or reshuffle the buffer. What changes is the
content of the blocks: they are blank until a New Game or Continue
fills them.

| Entry | Root and offsets | Valid when | Stable across |
|---|---|---|---|
| pwork root | P = u32[0x3909a8]; B = u32[P+0x1c]; block k = B + u32[P+0x28+4k], k = 0..10; offset 0xffffffff = absent | P is non-zero from boot, including the title screen, the demo and VS mode, so "P != 0" does not mean a career exists. Gate on content instead: month byte in 1..12, turn-in-month 0..7 and turn 0..95 at B0+0x88. Also check B != 0. Byte [P+0x18] is the ExtWork flag; it stays 0 in retail (prepareExtWork has no caller), so a guard on it is only defensive. | 0x3909a8, P, B and the block offsets stay fixed from boot until a reset. New Game and Load do not rebuild or reshuffle them, so the root chain needs no reset on load, only the content does. Whether the block offsets are the same on every boot is unresolved (the shuffle state starts at the constant 0x12345678, but other consumers before Create were not ruled out). |
| Date (B0+0x88) | B = u32[P+0x1c]; date = B + u32[P+0x28] + 0x88 | Inside a loaded career. Require month byte (+0x8b) in 1..12, turn-in-month (+0x8c) in 0..7, turn byte (+0x8a) in 0..95. Whether it is meaningful during a match is not traced. | The address is fixed. The value changes only when the game advances a day (pwkGen_IncDay 0x2443d0), at career start and on load; constant during frames and menus. After a load or new career the content is replaced in place, so a delta across that boundary is meaningless. |
| Free-agent pool (B0+0x18158) | B + u32[P+0x28] + 0x18158 | In a career (block content filled). Ignore during save and load. | The address is fixed. Contents are stable across frames, screens and turns. Slot indices are not stable (sort reorders), so key on the s16 id. |
| Release list (B1+0xea7c) | B + u32[P+0x2c] + 0xea7c; entry i at +0xc*i | In a loaded career. An entry is used only when u32 +0 != 0. | The address is fixed. Entry contents persist across frames, screens, matches and seasons until executed or cancelled; a load or new game replaces them. |
| Pending incoming transfers (B1+0xa08c) | B + u32[P+0x2c] + 0xa08c; entry i at +0x2a4*i | In a career (content filled). Not meaningful on the title screen. Validity during a match is unverified. | The address is fixed. Contents persist across turns and seasons until the player joins and the slot is freed; saved in block 1. |
| Club offers (0x390df8, 0x5f8c58, 0x5f8d48) | Fixed addresses; no chain | Meaningful only in a career, after the offer sim step has run. Outside a career, on the title screen, in a match or while loading, the memory holds stale or zero values. Gate with a career condition (for example the date check above). | Addresses are fixed for the whole run. The value is stable across screens and matches until the next run of the wrapper at 0x2261a0, which zeroes it and refills it. Persistence across loading a save or starting a new career is unverified (no reset-on-load code found). |
| Candidate lists (B1+0x9438 and others) | B + u32[P+0x2c] + 0x9438 / 0x97f8 / 0x9960 / 0x9ac8 / 0x9c30 | In a career. Reject ids that are not -1 or a valid database id (0 to about 0x2000). Populated after a scout report or a club search. | The address is fixed. Contents change on scout reports and once per turn (decay); a new game or save load replaces them. |
| Negotiation lockout (B0+0x12ec) | B + u32[P+0x28] + 0x12ec | In a career. A slot is active only if counter (s8 at +2) > 0. | The address is fixed. Saved with block 0, so it persists across save and load. Expired slots keep their stale id. |

### RetroAchievements notes

- Resolve every heap address from the chain. P = u32[0x3909a8], then
  B = u32[P+0x1c], then the block offset u32[P+0x28+4k]. The block
  address is the sum of two separate loads (B and the offset), which a
  plain AddAddress chain may not express directly. The chain is fixed
  for the boot, but whether it is the same between boots is not
  verified, so do not hard-code a resolved address.
- P is non-zero from boot, so a heap condition needs a content check
  as well: B != 0, the block offset != 0xffffffff, and a plausible date
  (month 1..12 at B0+0x8b, turn-in-month 0..7 at B0+0x8c, turn 0..95
  at B0+0x8a). Blocks are blank until the New Game or Continue path
  fills them.
- After a load, new career or save-state load, the buffer is not moved
  but its content is replaced. Reset Delta-based logic at that boundary,
  and gate it on the date check.
- Transfer window: test the month byte at B0+0x8b against 7, 8 and 1
  (open). For the opening or closing edge, use month 7 or 1 with
  turn-in-month (B0+0x8c) == 0, and month 9 or 2 with it == 0. The date
  changes only when a day advances, so it is a good once-per-turn change
  detector.
- Free-agent pool: detect a specific s16 id leaving the pool, or the
  count of non-negative ids dropping. This also happens when a computer
  club signs a free agent, so attribute it by checking your own squad
  (squad ids at B1+0x4d4+0x2a0*slot) or the pending free-agent slots.
  Scan all 1500 slots; do not use slot numbers.
- Pending moves: for your own outgoing moves, a 0 to non-zero change in
  a release-list entry's +0 means a sale or loan was agreed. A non-zero
  to 0 change means it executed or was cancelled; the edge alone does
  not tell them apart. For incoming moves, count entries with s16 id
  >= 0 at B1+0xa08c (id 0 is valid, so do not test for non-zero). Use
  the s16 ids, not a stored counter: none exists.
- Club offers: the count at 0x390df8 is the only field to rely on. It
  is not a pulse (it stays until the next wrapper run), and it reads 0
  after any run that is gated off, so a poller may miss a 0 to n edge
  when two runs leave the same n. Offers appear mainly at turn-in-month
  0 and 4 in months 1 to 6, and at turn-in-month 4 in months 7 to 12
  (2006 season on). It is a static address, so no chain is needed.
- Scout candidate lists: a record appears when a report or search
  completes and is removed when its turns reach 0. A rise in the count
  of ids != -1 is a "scout found someone" trigger. Staff lists use id
  at +4, player and youth lists use different offsets, as in the table.
- Negotiation lockout: weak signal only. Use "counter > 0" per slot,
  never "id == -1". The "12 turns" length is not exact (see the table).
- Money: club money is the s64 at B0+0x0 (true 64-bit, negative = debt,
  no 2^31 cap; stored / 6 = pounds, empirical) and changes immediately
  on pay and income calls. It is the safest delta signal for a
  transfer, but the transfer-fee accounts were not confirmed as booked
  on a signing (see Unconfirmed).
- Pitfall: the ExtWork copy (switchExtWork 0x21da20) could repoint
  P+0x1c while P+0x18 is non-zero, but in retail it is never armed
  (P+0x20 is NULL), so P+0x18 stays 0 and the data is read in place by
  the save code. Still ignore reads while saving or loading. Whether
  the content is consistent during a match is not traced.

### Unconfirmed

Both verifiers corrected each of the findings below, so no verifier
confirmed the original wording. The points on which they agree are
given so nobody relies on the original text; treat every row as needing
a test in the emulator.

| Finding | Why it is not in the table | What both verifiers agree on |
|---|---|---|
| Your squad (B1+0x4d4 + slot*0x2a0) | Both corrected the meaning. | 25 slots of 0x2a0, 16800 bytes, s16 id < 0 = empty. +0x190 is not always 1: a loaned-out player (flag 0x2) keeps the borrowing club there, so use id >= 0 for squad membership. +0x194 = 0 for a youth promotion (kind 3); "0 for free signings" is not shown by the code. Flag 0x8 is set on every join, but its meaning is unverified (IsJoin tests 0x4000, with the counter u16 at +0x240). 0x2000 is set by plTeam_CheckPurchaseOffer on a loaned-out player and also read after IsHired, so its meaning is unverified. Flags 0x2 (rental out) and 0x4 (hired) are confirmed. Contract years at +0x21d is written by JoinPlayer only for kind 4. "Contract years 0 means renewal talks" is unverified. |
| Pending free-agent signings (B1+0xe290) | Both corrected the size and the join field. | Entry layout is 3 x 0x2a4, in use when s16 id >= 0, cleared to -1. The join u32 is always 0 (Add rejects a non-zero join, read at 0x25a384), so it is useless. The size is 0x7ec = 2028 bytes: 0xe290 + 0x7ec ends exactly at the release list at 0xea7c (the 2532 figure is wrong). Ids sit at B1+0xe290, +0xe534 and +0xe7d8. `DOC/SAVE_FORMAT.md` lists the region as unidentified and may show id 0 in saves, which would look "used". |
| Scout slots (B1+0x8f8c + scout*0x94) | Both corrected the mode meanings. | 3 slots of 0x94, +0x60 s16 id (negative = empty), +0x64 u32 mode, +0x84 team, +0x88 s16, +0x8a u8, +0x8b s8, +0x8c s16 target. Mode 4 = negotiating (+0x8c player, +0x84 club). Mode 1 = named-player request. List searches store 2 (kinds below 2, 2, 3, 4 and 8 or more) or 5, 6, 7 (stored directly). Mode 3 is never stored by the four setters read. SetScoutModeNot zeroes +0x64, +0x7c, +0x80, +0x84 and sets +0x8c and +0x8b to -1; it copies the player to +0x88 and sets +0x8a to 8 only when its flag is set and the old mode was 1, 3 or 4. The "8 turns" reading of +0x8a and the callers (SIMPRG, event procedure 9) are unverified. |
| Youth intake (join list 0x399740, youth team B1+0x4f00, gauge B1+0x8f8a) | Both corrected the region and the cap claim. | The join list at 0x399740 is static (16 x 8: s16 id, -1 = empty, u32 argument at +4 of unknown meaning), is all -1 in the executable image, is cleared by pwkTeam_Init, and is not saved. The youth team (24 slots of 0x2a0, flag 0x808, team 1) and the gauge (u16 at B1+0x8f8a, saturating 0..0xffff, changed by pwkYouthDev_Add) are heap, not static, reached through the chain. "Capped at 4 per period" is unverified (pwkTeam_GetYouthPlayerMax only returns 4; no reader found). When the list fills and empties is unverified. |
| Per-scout negotiation targets and already-scouted list (B1+0x129d8, B1+0x9ccc) | Both corrected the size and the meaning. | Size 492 is wrong. Negotiation targets are 12 bytes at B1+0x129d8: 3 scouts x 2 s16 (player candidate id, youth candidate id), -1 = none, cleared by Reset_NegoPlayer. The discovered-players list is 120 x 4 bytes at B1+0x9ccc ({s16 id, s8 turns, pad}, empty when turns == 0). Turns default 6 when the argument is negative; the code verdict says search callers pass 8. Managers' list is at B1+0x9eac (60 entries) and scouts' list at B1+0x9f9c (60 entries). The decrement rate and the Reset_NegoPlayer callers are unverified. |
| Transfer fee accounts (B5+0x48, +0x50, +0xd0, +0xd8 and season copies) | Both found no code that books these types; one verifier calls it empirical. | The account layout is confirmed: B5 = B + u32[P+0x3c]; month income s64 at B5+8*t (12 types), month payment at B5+0x60+8*t (23 types), season copy at +0x130 (income +0x130+8*t, payment +0x190+8*t). The month folds into the season at pwkRec_AfterMonthlyReport 0x252c98 and the season is zeroed at pwkRec_AfterAnnualReport 0x253020. pwkGen_Income ignores an amount <= 0 and stores 0x7fffffff only if the 64-bit sum wraps to <= 0; pwkGen_Pay has no floor. Money is the s64 at B0+0x0; stored / 6 = pounds (empirical, `DOC/ECONOMY.md` and `DOC/SAVE_FORMAT.md`). No call in SLES or SIMPRG.REL passes type 9, 10, 14 or 15 as a literal, so that a signing or sale raises these accounts is unverified. |
| Squad member counts (GetMemberNumber, GetEmptyNumber) | Both corrected the limits. | No stored counter exists. Kinds 0..9 are as in the finding (jump table 0x554670). The squad has 25 slots, not 24. The "at most 24" limit is the youth team (GetEmptyNumber kind 1 = 24 - kind 8). The sale limit (kind 0) is a phase-dependent sum minus 8 (phase from plMisc_TransferMarketSchedule): phase 0 gives 0, phases 1 and 3 use c0 + c4, phase 2 uses c0 + c4 + c2, phase 4 uses c0 + c3 + c2, then minus 8, floored at 0. Loan-in limit is 5 - (c4 + c5) (pwkDis_IsRentalFull is true at 5 or more). Loan-out room (kind 2) is 5 - (c3 + c7) or 5 - c7 depending on phase. Kind 6 is every non-zero release entry; kind 7 only those with join kind 4 or 5. Youth slots are at B1+0x4f00, 24 x 0x2a0. |
| Special club offers kinds | The wording "permanent move, loan transfer" is not shown by the code. | SetOfferData routes on COM_OFFER_WORK+8 == 1 to the special list. What the two lists mean beyond that is unverified. |
| Cadence of the offer wrapper 0x2261a0 | The caller was not traced. | The wrapper runs Execute only for turn-in-month 0 or 4, but how often the wrapper itself is called (per turn, week or day) is unverified. |

### Still unknown

- Whether *(0x3909a8) and *(P+0x1c) are the same between boots, and
  whether the shuffled block offsets are identical on every boot, was
  not verified. The shuffle state (0x569dc0) starts at the constant
  0x12345678, but other consumers before Pwk.Create were not ruled out.
  Whether a save load refills the same buffer is believed yes (no
  re-create code exists), but was not seen running.
- Whether the content of the blocks stays valid and consistent during a
  match and in VS mode was not traced.
- PlJoin enumeration is only partly known: 3 = youth promotion (sets
  0x1000), 4 = loan in (sets 0x4, contract 1 year), 5 = loan out. Kinds
  0, 1 and 2 (purchase, free agent, other) were not separated, and the
  names of the release-list kinds 0 and 4 are unverified.
- Which code books income 9 and payment 14 (transfer fee) when a
  purchase or sale completes was not found. Callers of pwkGen_Pay in
  SIMPRG use types 0x12, 0x15, 0x16, 0x1f and data-driven types.
- COM offer record fields +0, +4, +8, +0xa..+0x15 were not individually
  identified (buying club, player slot or id, fee, offer type 1 buy or
  2 loan). The units of the +0x10 and +0x14 money fields beyond
  "save-money encoding" are unknown. Whether the ordinary offer count
  is capped at 10 is unknown, and the caller cadence of the wrapper at
  0x2261a0 is unverified.
- When pending incoming transfers (B1+0xa08c) and pending free-agent
  signings (B1+0xe290) are converted into JoinPlayer calls (at which
  window date or turn) is in SIMPRG and was not traced. The code that
  clears a pending slot on joining was not read.
- Contract negotiation state (the agreed salary and years while the
  dialog is open, and the per-player under-negotiation bits 0x10, 0x20,
  0x40 setters) lives in SIMPRG.REL UI objects whose addresses depend on
  the overlay load base, which was not determined.
- Scout PlSinfo +0x64 modes other than 0, 1, 2, 4, 5, 6, 7, and the
  meaning of +0x79, +0x7c, +0x80 result fields, are unknown.
- Whether the same layouts apply on the Japanese build (`gamever.py`)
  was not checked; PAL only. The pwork global there is at a different
  address (`DOC/JAPANESE_RELEASE.md`).
- B1+0x8f8a youth development gauge: the thresholds that decide youth
  intake quality were not traced, and the Promote scaling by the club
  rank at MyTeamData+0x41f8 was not read.
- Callers of pwkGen_SetNegotiateDisable (what triggers the lockout)
  were not identified, and the real lockout length is unknown (the
  counter drops only when PlDate+8 equals 1).
- Gaps: no entry covers contract salary or contract-years rules beyond
  the fields named in the squad finding (+0x218 salary, a PlMoneySave
  value where pounds = v * 100 / 6, and +0x21d contract years), so
  contract renewal is not described. The meaning of byte +2 of the
  free-agent slot is unknown, and the "grows when released" path into
  the free-agent pool was not traced.

### Checking the claims

Run each from the repo root. All were run and show the cited code.

```bash
# the pwork root: the store of 0x3909a8 (sw a2, 0x9a8 at 0x21d65c, after lui 0x39)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21d650 10
# pwGet: i >= 11 gives 0; offset 0xffffffff returns the bare base (delay-slot lw 0x1c)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 18
# free-agent pool: slot count 0x5dc (1500), stride 4, empty = negative s16; movz latches slot 0
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkDb_addFreePlayer
# release list: 0xea7c base, team-2 < 0x1b8, flag word +0x20c gets 0x40 and loses 0xb1 bits
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x25a830 70
# incoming transfers: base 0xa08c, 25 entries (0x18 down to 0), age byte +8 incremented
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkTeam_AddPinfoTransferAge
# club offers: wrapper clears first, refills only for +4 equal to 0 or 4; Execute's date and free-blank gates
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x2261a0 20
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x224460 40
# negotiation lockout: IsDisable result is 1 unless a slot with counter 0 exists
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x2e9368 22
```

## Staff, training and club activities

This part of memory holds the career state for coaches and other staff,
training plans and what training did to each player, camps, tours and
booked PR events. Almost all of it lives in the career work area
(PlPwork), which is a heap object, so nothing here has a fixed address
except the one static pointer to it at 0x3909a8. Every other address
below is reached through that pointer. Mode indicators (match, menu,
loading, attract) are outside this domain.

Wording of the labels: **confirmed** means the address and layout were
re-derived from the PAL executable or overlay code. **Empirical** means
inferred from the arithmetic or from data and consistent with it, but
not proved by a code path. A save-state check in PCSX2 is recorded in
`DOC/SAVE_FORMAT.md` for the pointer chain itself (Nexxus's report,
2026-10-27). Nothing else here was observed in the running game, and
nothing was read live through PINE.

Addresses written as `SIMPRG.REL 0x...` are image offsets in the
overlay. The overlay's load base was not derived here (0xc75000 was only
observed in PCSX2, see `DOC/ECONOMY.md`), so they are not runtime
addresses.

### Table of verified entries

Block i means `u32[Pwork+0x1c] + u32[Pwork+0x28+4*i]`, where Pwork is
`u32[0x3909a8]`. Only entries that were confirmed in code by at least
two readings are listed.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer to the 0x5c-byte PlPwork object | static (pointer); target is heap | PlPwork root pointer and block table | Holds the PlPworkTask pointer from boot, once the first script command Pwk.Create has run, and never changes again in that boot. It is NOT 0 outside a career, so it is not a career gate: the block contents are blank or stale until New Game or Continue fills them in place. Pwork+0x1c is the work-area base. Pwork+0x28+4*i (i = 0..10) is block i's offset from that base. In retail every block is present: the 0xFFFFFFFF "absent" value is written only for block 8 and only when the constructor argument (u8 at Pwork+0x19) is nonzero, and the only caller passes 0. u8 at Pwork+0x18 (ext-work swap flag) is always 0 in retail, because prepareExtWork and deleteExtWork have no caller, so Pwork+0x1c never changes either. Each block is the table size minus 8 bytes (table at 0x533ac8). The block order is shuffled once, in the constructor. | Confirmed from code: plPwork_GetPwork 0x21d6e0 (lui 0x39, lw 0x9a8), plPwork_CreatePwork 0x21d628 (store at 0x21d65c), plPwork_DeletePwork 0x21d698 (zeroes the word), constructor 0x21d6f0 (stores 0 to +0x18, +0x1c, +0x20, +0x24; shuffle call at 0x21d774; 0xFFFFFFFF store for block 8 only at 0x21d7e4), get 0x21d928, pwGet 0x21da50. Only caller of CreatePwork is PwkCallbackCommand_Create 0x110498 (jal at 0x1104b8). `DAT/SEQ/ROOTMAINSEQ.SQB` runs Pwk.Create at 0x10 and Pwk.Delete only at 0x1a20, which cannot be reached. |
| block0 + 0x88 | 16 | struct PlDate: u16 year@+0, u8 turn@+2, u8 month@+3, s32 turnInMonth@+4, s32 week@+8, s32 weekPart@+0xc | heap | Career date | +2 is the turn of the season, 0-95, 8 per month, turn 0 = July. +3 is the month 1-12, equal to ((turn>>3)+6)%12+1. +0 is the season's first year, so months 1-6 belong to the season that began the previous July. The first real season (after the opening playoffs) is year 2006 turn 0; seasons since start = year - 2006 (pwkGen_Keika 0x244430). At New Game the date starts at 2005 turn 92 (the opening playoffs, turns 92-95) and pwkGen_SetStartYear then sets 2006 turn 0. +4 is the turn within the month 0-7, equal to 2*(+8) + (+0xc). Changes only on a turn advance. | Confirmed from code: pwkGen_GetDate 0x244368 (copies 0x10 bytes from block0+0x88), pwkGen_IncDay 0x2443d0, pwkGen_SetStartYear 0x2442e8, plMisc_SetTurn2Date 0x214698 (sh year, sb turn, sb month, sw +4, +8, +0xc), plMisc_GetLaterDay 0x214788, pwkGen_Init 0x244220 (calls 0x2441c8 with 2005, turn 92), SIMPRG.REL 0x1583a4-0x1583bc. Values are small, so reading +4, +8, +0xc as u8 is safe. |
| block6 + t*0x48, t = 0..95 | 6912 (96 x 0x48) | 96 day records: s32 code@+4, u16 flags@+0x26, s64 ticketBonus@+0x30, u16 prEvent@+0x38 | heap | Schedule calendar (booked PR event per turn) | +0x38 is the club PR event booked on turn t; 0xFFFF = none (plClubEvent_GetEvent returns -1 for it). +0x30 is the ticket bonus in percent kept for that day's match (`DOC/CLUBEVENT_FORMAT.md`); it is stored by a successful event as a 64-bit value, so the low dword is a sign-extended s32. +4 is the day code, -1 = none; codes 0x82-0x87 mean the turn is part of a camp. +0x26 is a bit-flag set (pwkSche_SetFlag ORs into it). Block 6 continues past +0x1b00 with the camp and tour records (see Unconfirmed). | Confirmed from code: pwkSche_GetCale 0x2554d0 (get(6)), _ScheClear 0x2552e8 (loop to base+0x1b00), plClubEvent_GetEvent 0x20e9b8 (turn * 0x48 + base, lhu 0x38), plClubEvent_Execute 0x20df50 (sd at 0x20e144), pwkSche_CheckCampTearm 0x255550 (code - 0x82 < 6), pwkSche_SetFlag 0x256cb0. |
| PlPracDb + 0x324 + slot (u8) and PlPracDb + 0x33e + 2*slot (s16), slot 0..24; PlPracDb = block1 + 0x10878 | 76 (0x4c: 25 + 1 pad byte at +0x33d + 50) | u8[25] at +0x324, 1 pad byte, s16[25] at +0x33e | heap | Per-slot rest-streak counter and rest points | The u8 goes up by 1 when the practice done is 26, 27 or 28 and is set to 0 for any other practice; clamped to 100. The s16 is clamped to 0..100: practice 27 or 28 adds 4, 26 adds 1, 23 subtracts 2, any other practice subtracts 1. The slot is the player's position in the squad array (25 slots), not a player id, so a squad change can move a value to another player. The names "rest streak" and "rest point" are empirical (inferred from the arithmetic). | Confirmed from code: pwkGUtl_GetPlPracDb 0x245e68 (get(1) + 0x10878), pwkGUtl_GetPracCount 0x245c48, SetPracCount 0x245cd0, AddPracCount 0x245d08, pwkGUtl_GetRestPoint 0x245d68 (squad loop of 25 x 0x2a0 comparing the s16 id), AddRestCount 0x245df8; callers SIMPRG.REL 0x1584d8-0x158560. |
| block1 + 0x9148 + i*0xbc, i = 0..3 | 752 (4 x 0xbc) | 4 x PlMinfo: s16 id@+0x9c, s8 contractYears@+0x9e, u32 job@+0xa0, u8 abilities[48]@+0x6a, salary@+0xb8 | heap | Coaches (4 slots) | The club's 4 hired coaches. id < 0 (test the sign bit) = empty slot. Contract years is a signed byte (GetCoaches clamps values below -1 to 0). Job: 0 balanced assistant, 1 attacking assistant, 2 defensive assistant, 3 physical coach, 4 GK coach. Abilities are bytes on a 38-99 scale. Salary at +0xb8 is probably a PlMoneySave-format value (passed to MoneySave2SM_S64 0x246ea0), not verified as a plain u32. The manager (block1 + 0x4d08) and the youth manager are separate records, not among these 4 slots. The byte at +0 of a slot is set from the job at hire (job 4 gives 1, job 3 gives 2, any other gives 0). | Confirmed from code: pwkTeam_GetCoaches 0x26a7b8 (loop of 4, stride 0xbc), pwkTeam_GetCoachManager 0x26cdc8 (manager at MyTeamData + 0x4854, then the 4 slots), plMinfo_CloseContract 0x216ef0 (writes -1 to +0x9c), pwkTeam_SignCoach 0x26a870, pwkTeam_SignCoachSingle 0x26ad10 (compares job at +0xa0 with 4 and 3; slot byte stores at 0x26aea4-0x26aed4). Ability scale and job encoding come from `DOC/PBDATA_FORMAT.md` and `DOC/SAVE_FORMAT.md`, not re-read in code. |

Notes on single readings (empirical, not agreed):

- When a coach is promoted to manager, the manager-change screen writes
  job 5 into a coach slot (one reading). Test jobs 3 and 4 explicitly
  rather than "any job above 0".
- The yearly contract-years decrement was not found in
  pwkTeam_YearEndCheck or pwkTeam_AddCoachesAge. `DOC/GAME_FLOW.md`
  event 15 (StaffContract) is the likely path.
- Wrapper pwkSche_GetCale goes through get(6), which takes another path
  when byte Pwork+0x19 is nonzero (never in retail), so that edge case
  does not arise.
- The writer of calendar +0x38 (the booking screen) was not located. The
  claim that SIMPRG.REL near 0xa411c writes it could not be confirmed.
  Read-only use is sound.
- `_ScheClear` resets +0x38, +4 and +0x26 each season, sets +0x28 to
  0x19 and clears +0, +0x10, +0x24 and +0x40, but does not touch +0x30,
  so a stale ticket bonus may survive a season rollover. Whether the
  buffer is zeroed at allocation is unverified.

### Pointer chains and stability

Common root for every entry: `Pwork = u32[0x3909a8]`,
`base = u32[Pwork+0x1c]`, `off(i) = u32[Pwork+0x28+4*i]`,
`block i = base + off(i)`. The block offsets are shuffled by
plUty_ShuffleUint8 (0x235270, called at 0x21d774) when Pwork is
constructed. That happens once per boot, because Pwk.Create is the first
script command and Pwk.Delete is unreachable. New Game, Continue, the
attract demo and matches fill the blocks in place (pwkGen_Init, the team
init and the save load do not reallocate). So the root, the base and
every block offset are constant from Pwk.Create to the next reset or
emulator restart. Whether they are the same on two different boots is
unresolved (the shuffle draws from the generator state at 0x569dc0,
which starts at a constant, but other draws before Pwk.Create were not
ruled out). Reading the chain again on each evaluation is defensive
practice, not something the game requires. The base comes from
FcEuroMalloc in heap block 6 (0x21d840). Block 1 holds the offset at
Pwork+0x2c and block 6 at Pwork+0x40.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| PlPwork root pointer | `[0x3909a8]` gives Pwork; `[Pwork+0x1c] + [Pwork+0x28+4*i]` gives block i | `[0x3909a8] != 0` is true from boot, so it proves nothing about a career. A career test must come from another indicator (the block contents are blank, with ids -1 or zeros, before New Game or Continue). Accessors treat an offset word of 0xFFFFFFFF as the bare base, not 0, but no block is absent in retail. | The word at 0x3909a8 is fixed in the PAL executable. Pwork, the +0x1c base and every block offset are stable across frames, screens, seasons, saves, loads, New Game and the demo within one boot. Not known to be equal across boots. |
| Career date | block0 = `[Pwork+0x1c] + [Pwork+0x28]`; date = block0 + 0x88 | A career has been started or loaded. Sanity test: month is 1-12, turn is 0-95 and month = ((turn>>3)+6)%12+1. Not meaningful on the title screen or launcher, where block 0 is blank (or overwritten by the attract demo's VS date, 2005 turn 95). | Stable across frames, screens, menus and matches played from the career. Changes only on a turn advance. A load, a new career or the demo rewrite the contents in place. |
| Schedule calendar | block6 = `[Pwork+0x1c] + [Pwork+0x28+4*6]`; day t = block6 + t*0x48; current t = `u8[block0+0x88+2]` | A career is loaded and the turn byte is <= 95. Not meaningful before a career, or on a different save until re-read. A match keeps the calendar resident but not refreshed. | Same address for the whole boot. Contents are rewritten at season rollover by _ScheClear (0x2552e8, via pwkSche_UpdateAnnualy 0x255408) and by the schedule screen, and wholesale by a load or a new career. |
| Rest streak and rest points | block1 = `[Pwork+0x1c] + [Pwork+0x2c]`; PlPracDb = block1 + 0x10878 | A career is loaded. Meaningful in career mode only. Values change only in the per-turn training pass (SIMPRG.REL 0x1584d8-0x158564), not in matches, menus or demo mode. | Same address for the whole boot; contents are blank before a career and are overwritten by a load or new career. Frozen between turns, so a compare-with-previous-frame trigger fires on the turn tick. Indexed by squad slot, so squad changes can shift a value to another player. Values persist through seasons. |
| Coaches | block1 = `[Pwork+0x1c] + [Pwork+0x2c]`; coach i = block1 + 0x9148 + i*0xbc | A career is loaded. Slot occupied when s16 at +0x9c is >= 0. Before a career the slots read id -1 or zero. | Same address for the whole boot, stable across frames, screens, matches and seasons. Changes only on hire, dismissal, expiry or the yearly staff-contract event, and on a load or new career. GetCoaches copies into a caller buffer, so a RAM scan can find transient copies: read through the chain only. |

### RetroAchievements notes

Everything here is grounded in the entries above. No test with a running
emulator was made.

- The address of every value here is the sum of two numbers read from the
  Pwork object (`[Pwork+0x1c]` and `[Pwork+0x28+4*i]`). Both are constant
  within a boot, so one pointer chain per value is enough, but they are
  not known to match across boots: do not hard-code a flat address.
  Resolve the chain (an AddAddress chain) on every evaluation.
- `[0x3909a8] != 0` is true from the first script command on, through the
  title, the demo and career, so it is not a career test. The block
  contents are blank until New Game or Continue. For a career test use
  the date block (month 1-12, turn 0-95) and a separate mode check
  (menu, match, loading, demo), which is outside this domain. The guards
  `u8[Pwork+0x18] == 0` and a block offset not equal to 0xFFFFFFFF are
  harmless but always true in retail.
- Fire on changes of the turn byte. The turn byte (`block0+0x88+2`, 0-95)
  changes only on a turn advance and is the cheapest change detector.
  Use it for "once per turn" logic. Month (`+3`, 1-12) is also a u8. A
  season rolls when turn goes from 95 to 0 and the year at +0 increases
  by 1. After New Game the date is 2005 turn 92 until the opening
  playoffs end, so "year 2006" holds only from the first real season.
- Compare against the previous frame (Delta or Prior). The pointers do
  not move while the game runs, but the contents are rewritten in place
  by a load, a new career or the attract demo (which writes its own
  date). A value read right after such a rewrite can look like a
  transition, so add a guard on the turn or date being plausible.
- Booked PR event: `u16[block6 + turn*0x48 + 0x38] != 0xFFFF` means a PR
  event is booked on the current turn. A transition from 0xFFFF to
  another value on any day means an event was booked. A scan of all 96
  days counts booked events, but only for the current season, because
  _ScheClear resets the field each season.
- Hiring a coach: the s16 id at coach slot +0x9c going from negative to
  non-negative, or changing between two non-negative values (a hire can
  overwrite a slot without a -1 frame). Count of coaches = number of
  slots with id >= 0. Job 3 = physical coach, job 4 = GK coach. Read
  years as a signed byte.
- Rest counters per player: the u8 counter at PlPracDb+0x324+slot
  reaches 100 at most; the s16 at +0x33e+2*slot ranges 0-100. Both are by
  squad slot. If the achievement is about one named player, you need the
  squad array to match ids to slots (squad array start and id offset are
  documented in `DOC/SAVE_FORMAT.md`; not in the data given here).
- Pitfall: do not rely on the entries listed under "Unconfirmed" for a
  shipped achievement. Several of them (camp running, training done flag,
  result grade, PR event success flag, youth menu) have corrections that
  disagree or open unknowns.
- Pitfall: these are PAL addresses. `DOC/JAPANESE_RELEASE.md` says the
  Japanese build reads its pwork global with `lui 0x39 / lw -0x36b8`
  (0x38c948), not 0x3909a8, so a set for the PAL release does not apply
  to SLPM-66316 unchanged.

### Unconfirmed

These findings were corrected by both readings, or contain a claim that
was refuted or never settled. Do not rely on the original text. "Agreed"
means both readings say the same thing; it is still not a confirmed
entry. Chain for all of them: block1 and block6 as in the section above.

**Camp and tour booking records** (block6 + 0x1b00 + slot*0x80 for camps,
+0x40 more for tours).
- Agreed: camp record = block6 + 0x1b00 + slot*0x80; tour record = camp
  record + 0x40; fields u8 startTurn@+0xa, u16 place@+0x18, u32
  state@+0x1c (1 camp, 2 tour, 0 empty), u8 theme@+0x3a, s16 type@+0x3c;
  camps use 3 slots. Camp IsCampEnd (0x255798) fires when startTurn ==
  turn-1, so the last camp turn is startTurn+1. The original "camp
  finished at startTurn+2" is wrong. `_ScheClear` (0x2552e8) zeroes the
  +0x1c word of the 3 camp records and the 3 tour records at 0x1b1c +
  slot*0x80 and +0x40 further.
- Disagree: tour player ids. One reading says 5 s16 at +0x30
  (GetTourPlayer 0x256630 loop count). The other says 4 u16 at +0x30,
  0xFFFF = empty, taken from the writer. Do not use until settled.
- Disagree: tour slot count. One reading says only slots 0 and 1 are
  ever written (IsTourStart 0x255888 loops 2, writer SIMPRG.REL
  0xa55ac-0xa56f8 loops 2). Another notes IsTourStart loops 2 while
  GetTourPlace and GetTourPlayer loop 3, and that slot 2 use is
  unverified.
- One reading only: `_ScheClear` zeroes only +0x1c in each record, so
  other fields are stale when state is 0; test state first. Camp writer
  SIMPRG.REL 0xa5488-0xa5558, tour writer 0xa55ac-0xa56f8.

**Training plan: per-turn practice record (PlPracDb)** (block1 +
0x10878 + t*0x64).
- Agreed: records at stride 0x64 for 8 turns of the month; s32 team
  practice at +4 (default 27, written by pwkPrac_Init 0x24e4f8); u8 at +8
  nonzero makes everyone train as 28; u8 at +9+slot nonzero makes that
  squad slot train as 28; 4 coach blocks of 0x10 at +0x24 reset to -1 or
  0, meaning undecoded. The restSlot index is the player's position in
  the squad, not a player id. pwkPrac_InitMonth 0x24e618 does NOT reset
  +4, so the original "plan reset on InitMonth" is wrong.
- Disagree on size: one reading gives 804 bytes (a per-turn u32 flag
  sits at +0x64*(t+1), past the last record); the other keeps 800 and
  notes the same flag. See the next entry.
- One reading: a player with an individual coach assignment gets 27
  instead of +4; an injured player also gets 28.
- Turn index t = 2*(PlDate+8) + (PlDate+0xc), range 0-7.

**Training turn processed flag** (u32 at PlPracDb + 0x64*(t+1)).
- Agreed: 0 to 1 once per turn, set by the local helper at SIMPRG.REL
  0x159b28 (store at 0x159b54), called at 0x158b8c after the 25-player
  training loop with the turn index and value 1. Cleared to 0 for all 8
  turns by pwkPrac_InitMonth (0x24e618). The reader at SIMPRG.REL
  0x1583e4-0x158400 skips the training pass when it is nonzero. Values 0
  and 1 only.
- Open: whether it is serialized into the save was not traced. The
  executable's setPracDone 0x24e660 has no callers. Treated as live
  state.

**Per-player training result** (block1 + 0x10be8 + slot*0x40 + t*8).
- Agreed: s32 practice number at +0, u8 result at +4 (cleared to 0 at
  SIMPRG.REL 0x158440, stored at 0x158a20), values 0, 1, 3 or 4 (1 when
  the score is below 4.0 or when the value at 0x38($sp) is below 3, 3 for
  4.0 to below 8.0, 4 for 8.0 and above). A nonzero byte means a result
  was recorded. Meaning of the score and of 0x38($sp) is not decoded.
- One reading: skipped slots (rentals, negative id) keep a stale +0;
  when a turn's pass is skipped, its cells stay stale. No monthly reset
  was found, so do not rely on one.

**Manager, youth manager and scouts** (block1 + 0x4d08, 0x8e00, 0x8f8c +
i*0x94).
- Agreed: sizes are 0xbc (188) each for manager and youth manager;
  scouts are 3 x 0x94 (444 contiguous), not 380 total. Manager id
  s16@+0x9c, years u8@+0x9e, abilities u8@+0x6a+n; youth manager job 6
  confirmed (pwkTeam_SetYManager 0x26bd28). Scout id s16@+0x60 (-1 =
  empty), years u8@+0x62 (unverified). Manager job 5 is unverified:
  SignManager 0x269e20 does not visibly write the job.
- One reading: SignManager overwrites the 0xbc bytes in place, so the id
  can change between two non-negative values with no -1 frame. An id
  below 0x6d2e is a former player (0x269ec8).

**Club event result: PR event execution** (code in SIMPRG.REL
0x162ee8).
- Agreed: event = u16[day+0x38]; plClubEvent_Execute 0x20df50 returns 1
  on success; the driver sets EVS flag v1 on success or v1+1 on failure
  from the jump table at SIMPRG.REL 0x241620 (flag ids not strictly
  0x72+2*event: read each delay-slot value). SetEventFlag (SIMPRG.REL
  0x124408) does `u8[u32[0x5eec20] + id] = 1` after a clamp to 0x156
  flags; EvsWork is at 0x5eec00, so the pointer is the static word at
  0x5eec20. Size 0 in the original was wrong: +0x38 is u16 and +0x30 is
  a 64-bit value.
- Flags can drop back to 0 while a career runs: SIMPRG.REL 0x124488
  clears every flag whose reset-group word (table 0x1d82e0) equals its
  argument, from a module destructor path. Which group each PR-event flag
  uses was not traced, so treat these flags as transient.
- Disagree: timing. One reading says the driver is
  pwkBring_Week_End_CallBack, not turn start. Whether it runs before or
  after the date increments is unverified.
- Not cleared in the code read: day+0x38 and +0x30 (checked only
  partly).

**Squad training outcome** (block1 + 0x4d4 + slot*0x2a0, 25 slots, 16800
bytes).
- Agreed: layout and size confirmed (squad loop at 0x245c70-0x245c98,
  pwkTeam_GetMyTeamData 0x259898 = block1 + 0x4b4, id s16@+0, empty =
  negative). pwkGUtl_AddExp 0x246028 does min(exp+gain, limit) and floors
  at 0. Fatigue +0x23c clamped 0-1000 (plPinfo_ChangeGtired 0x21c7c8).
  The 0x1e2d2a4 address is from one save state only. Whether SIMPRG
  training, match growth (pwkMatchGrow_Grow 0x2465f8) and year-start age
  decline write this array was not re-traced.
- One reading: plPinfo_CalcTourPowerDecline 0x219800 has two modes (arg
  nonzero: power -200, fatigue +200; arg zero: power +100, form +200),
  skipping empty, rental and injured slots; which mode is tour or camp is
  unverified. The abilities are in "exp" form only while the u16 at
  ability0+0xe is >= 100. The claim that condition (+0x240) and
  motivation (+0x242) follow the practice fatigue column is unverified.

**Youth team practice menu** (block1 + 0x8ebc + 4*slot).
- Agreed: youth data = block1 + 0x4f00 (pwkTeam_GetYteamData 0x270c18);
  size per word is 4 (s32), not 0; youth manager abilities at block1 +
  0x8e6a + n; pwkPrac_Init does not write +0x3fbc; the reader at
  SIMPRG.REL 0x15aae8 returns -1 for an injured player at read time, so
  -1 is not stored in RAM.
- Disagree: slot meaning and count. One reading: slot is a call argument
  of the same value for all 24 youth players, count about 8 inferred. The
  other: 8 slots (load function 0xf5ac8 and commit function 0xf5bf8 loop
  8 times), written back only when the youth practice screen is left,
  screen shows stored + 0xc.
- Initial value at new game not traced, may be 0 rather than -1.

**Camp and tour 'is running'** (derived, no stored flag).
- Agreed: no stored flag. IsCampStart 0x255718, IsCampEnd 0x255798,
  IsCampNow 0x255818 (turn or turn-1, 3 camp slots); IsTourStart 0x255888
  / IsTourNow 0x255988 (2 tour slots, window turn-3..turn). The turn is
  `u8[block0+0x8a]`. The training module's path is not the slot scan:
  pwkSche_CheckCampTearm tests calendar `s32[day+4]` in 0x82..0x87.
- Open and disagreeing on scale: whether the stored startTurn (+0xa) is
  on the 0-95 season scale or the 0-7 month scale. The training module
  passes a turn-in-month value to GetCampPlace. Read slot +0xa once in a
  booked career to see.
- Stale-state risk: the state word stays 1 after a camp ends (no clear
  seen outside `_ScheClear`, which zeroes +0x1c at season start).
  Require a turn match, not state alone.
- No caller of IsCampStart, IsCampEnd or IsTourNow was found in
  SIMPRG.REL.

### Still unknown

- Whether the PlPwork heap address, the base and the block offsets are
  the same on every boot (whether the shuffle is repeatable). The
  generator state at 0x569dc0 starts at the constant 0x12345678, but
  other draws before Pwk.Create were not enumerated. Needs a PINE or
  save-state check on two boots.
- What the u8 result grade values 1, 3, 4 mean (growth grade?).
- What the 4 coach-assignment blocks at PlPracDb record +0x24 + 0x10*j
  hold, and what the u32 at PlPracDb+0 is (tested at SIMPRG.REL 0x15a4e8,
  compared against thresholds at 0x1d9cb8 and 0x1d9cc8).
- Which flag ids each PR event sets (table at SIMPRG.REL 0x162f4c) and
  the exact lifetime of those event flags.
- Whether the calendar day +0x38 is cleared after the event runs, and
  which code writes it (the booking screen).
- Which code writes day+4 values 0x82-0x87, and what the other day-code
  values (competition types, match flags, +0x40 byte, +0x28 default
  0x19, +0x24) mean.
- Whether the SIMPRG overlay loads at a fixed base, and what
  overlay-resident menu state (training menu cursor, hire screen
  selection) exists.
- The full youth practice record layout (youth data +0x3fbc..+0x3ff0) and
  the number of slots.
- Staff candidate lists (block1 +0x9ac8, 30 x 0xc for coaches) and
  negotiation state in runtime variables.
- Who decrements coach contract years each year, and how the scout years
  and the other staff record fields behave.
- Whether the training-pass cells and flags reset at a month or season
  start (and whether Init, InitMonth or InitSeasonStart does it).
- Whether the ticket bonus +0x30 is zeroed when the calendar buffer is
  first filled.
- No entry was checked in a running emulator.

### Checking the claims

Run from the repo root.

```bash
# the root pointer (lui 0x39, lw 0x9a8) and the one store of it
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork
# Pwk.Create (once, first) and Pwk.Delete (unreachable) in the root script
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB | grep "Pwk\.\(Create\|Delete\)"
# constructor: zero stores to +0x18/+0x1c, shuffle call at 0x21d774, block 8 only absent
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21d6f0 80
# pwGet: block offset lookup; 0xffffffff gives the bare base
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 24
# the date: how the PlDate fields are written
python SRC/sles_disasm.py ISO/SLES_541.51 dis plMisc_SetTurn2Date
# the calendar: _ScheClear loop (stride 0x48, end 0x1b00)
python SRC/sles_disasm.py ISO/SLES_541.51 dis _ScheClear
# rest streak and rest points: PlPracDb = get(1) + 0x10878
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkGUtl_GetPlPracDb
# the training-pass rule that updates them
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x1584d8 32 --sles ISO/SLES_541.51
```

## Still unknown

The five open questions that matter most across the sections. Each
section ends with its own, longer "Still unknown" list.

1. Whether the shuffled block order, and so `base` and every block
   offset, is the same on every boot. The shuffle (`plUty_ShuffleUint8`
   0x235270) draws from a generator that `fcEuroRand_Init` 0x111698 sets
   to the constant 0x12345678, but other draws before `Pwk.Create` were
   not ruled out. Until two boots have been compared, resolve the chain
   on every read. Every section lists this.
2. Almost nothing was seen live. Apart from Nexxus's save-state read of
   2026-10-27, no row was read from PCSX2 or over PINE, so each needs a
   live check. The sections' RetroAchievements notes say which rows to
   check first, and the plain "Nexxus's report" credit goes on the doc
   when a row is seen.
3. Game over and the owner's objectives. No persistent flag, board
   target or evaluation variable was found. The four losing checks
   ([`GAME_FLOW.md`](GAME_FLOW.md#game-over)) leave their result in the
   sequencer's script memory, not at a fixed address. See "Career
   identity and objectives".
4. Menu and negotiation state that lives in overlays. The contract
   dialog, the training menu cursor and the hire screen keep their state
   in `SIMPRG.REL` objects, whose load base was not derived. See
   "Transfers, contracts and scouting" and "Staff, training and club
   activities".
5. The Japanese release. None of the addresses was checked on SLPM-66316
   (its pwork pointer is at 0x38c948,
   [`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md)), and
   `gamever.py` has no entry for the rows here.

## Checking the claims

Every command runs from the repo root. The first two show the root
pointer, the third the block lookup, and the fourth the script commands
that create and delete the work object.

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 syms plPwork_
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21d628 44
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 12
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB | grep -E "Pwk\.(Create|Delete)"
```

In the second, look for `sw $a2, 0x9a8($s1)` at 0x21d65c (the store of
the root word) and `sw $zero, 0x9a8($s0)` at 0x21d6c8 (the clear). In
the third, `pwGet` returns zero for a block number of 11 or more. The
script listing shows `Pwk.Create` at 0x0010 and `Pwk.Delete` at 0x1a20,
and the delete sits behind an unconditional branch, so the root is
never cleared.

Two more commands reproduce a field's chain end to end: the funds add
and the club rank cache.

```bash
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x244570 24
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x26dd40 24
```

The first shows the 64-bit add (`daddu`, `sd`) of `pwkGen_Income`. The
second shows the club rank: `lhu 0x126a`, `srl 0xb`, then `sb 0x46ac`.
Each section's own "Checking the claims" lists the rest.
