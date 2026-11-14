<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Runtime memory map (EE RAM)

This is the overview doc of the runtime memory map. It records where the
game keeps its data while it runs, so that tools and achievement sets
(RetroAchievements) can read it. This file covers the address space
(what sits where, and what is fixed), how an achievement author reads
this memory, the mode and guard indicators (which screen or mode the
game is in, and which flags show a demo, a developer launcher or a
skipped match), save and load behaviour, and the ids a Rich Presence
script can turn into words. Three more docs hold the data itself and are
indexed below: `RAM_MATCH.md`, `RAM_CAREER.md` and `RAM_SEASON.md`.

Every address is an EE RAM address in the PAL release (`SLES_541.51`).
RetroAchievements reads the PS2's 32 MB of EE RAM (0 to 0x1FFFFFF) as
little-endian values. Nothing here was measured in PCSX2 unless a row
says so. The rows come from reading the game code (the executable, the
overlays and the root scripts), and each one was checked twice by
separate readers. "Static" means the address is fixed in the
executable's image; it does not mean the value is constant. The
Japanese release (`SLPM-66316`) has different addresses, which
[`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md#how-the-tools-find-addresses-gameverpy)
explains.

## How to read this doc

Each memory table has the columns Address, Size, Type, Region, Name,
Meaning and values, and How known.

- **Region** says where the value lives: `static` (a word in the
  executable's `.data` or `.bss`, at a fixed address), `heap` (inside a
  heap object, so its address depends on a pointer) or `overlay` (inside
  a loaded `DLL/*.REL`, whose base is found at run time).
- **confirmed** means the address and the behaviour are proven by game
  code, and the row names the function and the address that prove it.
  **empirical** means the claim was inferred from data, script call
  sites or an observation, and is consistent with everything read, but
  the code does not prove it. A row can be confirmed for the address and
  empirical for the meaning. Material that was disputed or not shown is
  kept apart under "Unconfirmed" in each section. Do not rely on it.
- Addresses are hex with `0x`. Overlay offsets (`SIMPRG.REL 0x1d0c0`)
  are offsets in the file, not RAM addresses.
- Counts and offsets come from the full data set, as in the other docs.

A pointer chain row has four columns:

| Column | What it says |
|---|---|
| Entry | the value you want |
| Root and offsets | the static root and the hops, where `u32[X]` is the 32-bit value stored at address X |
| valid_when | when the chain can be trusted, including the checks to make before each hop |
| stable_across | what keeps the chain valid (frames, screens, loads, matches, a reset) |

Read `p = u32[0x3909a8]`, then `u32[p+0x1c]`, as: read the 32-bit
pointer at the static address, add the offset to it, and read again. The
pointer value is itself an EE RAM address, so it must lie in 0x100000 to
0x1FFFFFF. In RetroAchievements this is an indirect read (an
`AddAddress` step, then the next read at the offset). When the final
address needs two memory values added together (a base plus a
shuffled offset), it needs two `AddAddress` steps. Check each pointer is
non-zero and in range before you follow it.

## For achievement authors

1. Hard-code only static addresses. Everything behind a heap pointer is
   read through its root, never by a fixed address.
2. A non-zero root is not the same as "in a career". The career data
   root (0x3909a8) is non-zero from boot. Use the mode and guard
   indicators in the Game mode and Non-career sections to say what is
   running, and the demo flag (0x34d43c) to exclude the attract demo.
3. Debounce. A pointer can change between frames at a screen or match
   change, and a 0 to non-zero edge is not always a clean event.
4. A save state restores all of EE RAM, heap pointers included. A soft
   reset frees and reallocates the heap, so cached bases are then wrong.
   Re-read a chain after any reset or load.
5. Do not build a set from rows marked "Unconfirmed". Test the rows you
   do use in a running game first, since none of this was observed live.

## The RAM docs

| Doc | Holds |
|---|---|
| [`RAM_MAP.md`](RAM_MAP.md) | this file: the address space, mode and guard indicators, save and load behaviour, Rich Presence ids |
| [`RAM_MATCH.md`](RAM_MATCH.md) | the match: the live match state while a match is played (clock, score, events) |
| [`RAM_CAREER.md`](RAM_CAREER.md) | the career: your club, players, staff, transfers, finance and records |
| [`RAM_SEASON.md`](RAM_SEASON.md) | the season: the date, the competitions, the schedule and the national teams |

The layouts behind the career blocks are in
[`SAVE_FORMAT.md`](SAVE_FORMAT.md#the-blocks) (the save's blocks and
fields) and [`PBDATA_FORMAT.md`](PBDATA_FORMAT.md) (the player database
the Bp-data pointers lead to). The order of screens and scripts is in
[`GAME_FLOW.md`](GAME_FLOW.md). The overlay loader and its registry are
in [`SNR2_FORMAT.md`](SNR2_FORMAT.md#loader-confirmed). The schedule's
competitions and turns are in
[`SCHEDULE_FORMAT.md`](SCHEDULE_FORMAT.md).

## Contents

1. [Address space layout](#address-space-layout): the executable image,
   the stack, the heap blocks, the overlay registry and the career work
   buffer root
2. [Game mode, screens and flow](#game-mode-screens-and-flow): the
   schedule session object, the match-day object, the module activity
   table and the one-way latches
3. [Non-career modes and guards](#non-career-modes-and-guards): the
   attract demo, VS mode, the opening playoffs, the developer launcher
   and the skip flags
4. [Save, load and new game transitions](#save-load-and-new-game-transitions):
   the career buffer, the save point and how to detect a load
5. [Rich presence identifiers](#rich-presence-identifiers): the match
   group, the competition of your game today and the name lookups
6. Still unknown (at the end of this doc)
7. Checking the claims (at the end of this doc)

## Address space layout

This part of memory is the fixed frame that everything else sits in.
The PAL executable (`SLES_541.51`) loads once at 0x100000 and never
moves. The game then carves its own heap blocks out of memory that
starts at the end of the executable, and the overlays (`DLL/*.REL`) are
read into two of those blocks at run time, so overlay addresses are not
fixed by the file. Big runtime structures (the career work buffer, the
season manager) are heap objects reached through static root pointers
in `.data` and `.bss`.

All findings below come from the PAL executable's code and data, from
the root sequencer scripts (`DAT/SEQ/ROOT*.SQB`, read with `sqb.py
dis`) and from the overlay import tables. This is static analysis. No
heap buffer base was measured in PCSX2 or over PINE. The only recorded
overlay load base is 0xc75000 for SIMPRG (`DOC/ECONOMY.md` line 597) and
for GAMEPRG (`DOC/WIDESCREEN.md` line 198), an observation that is not
derived from the code. "Static" means the address is fixed; it does not
mean the value is constant.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x100000 | 0x4f95f4 (5,215,732) | region | static | Executable image | One ELF PT_LOAD at 0x100000 (filesz 0x4692dc, memsz 0x4f95f4), ending at `_end` 0x5f95f4. Sections: .text 0x100000-0x346c90, .data 0x346d00-0x418500, .sndata 0x418500-0x518500, .rodata 0x518500-0x569278, .gcc_except_table 0x569280 (0x5c bytes), .sbss 0x569300 (0x3d0 bytes), .bss 0x569700-0x5f95f4 (0x8fef4 bytes). Linker constants: `_gp` 0x5712f0, `_stack` 0x1fd0000, `_stack_size` 0x2f000, heap size -1. crt0 (0x100198-0x1001e4) calls SetupThread, then SetupHeap(0x5f95f4, -1), so the kernel heap starts at `_end`. Only .text and .rodata are read-only. .data, .sndata, .gcc_except_table, .sbss and .bss are writable sections, and values that change live in them. | confirmed (ELF program and section headers, crt0 disassembly at 0x100198). The contents of .sndata were not examined. That addresses below 0x100000 are BIOS and kernel is PS2 convention only |
| 0x1fd0000 | 0x2f000 (192,512) | region | stack | Main thread stack | Given to SetupThread by crt0: a1 = 0x1fd0000 (0x10019c, 0x1001b0), a2 = 0x2f000 (0x1001a0, 0x1001b4). The stack range is 0x1fd0000 to 0x1fff000 (exclusive end), and the initial sp is near the top. Contents change every frame. Not game state. | empirical (the crt0 constants are confirmed; that a1 is the low end of the stack is SDK convention, not read from the kernel) |
| 0x3a89c4 | 4 | u32 pointer | static | sbrk break | newlib sbrk's current break. File image holds 0x5f95f4 (= `_end`). Grows from `_end` through `_sbrk_r` 0x3241a8 / `sbrk` 0x326a20 (which addresses it as lui 0x3b / -0x763c), limited by EndOfHeap (syscall 0x3e). Can also shrink (`_malloc_trim_r` 0x322590). Moves rarely. Not a count of bytes in use. | confirmed. Only accessor found is sbrk |
| 0x35dae8 | 0x80 (8 entries x 0x10) | array of {u32 handle, u32 size, u32 buffer, u32 pad} | static (table), heap (buffers) | sbHeap block table | The game's own heap blocks, entry i at 0x35dae8 + 0x10*i. +0x00 handle (the `sbHeapCreate` result stored at 0x14d884, non-zero while the heap is alive; recreated by `fcEuro_ReflashHeapBlock` 0x14e3e8, so not an identity key). +0x04 size, constant. +0x08 buffer base (memalign(0x40) result stored once by `HeapInitialize` 0x14d840, constant after boot). +0x0c padding. Sizes, read from the file at 0x35daec + 0x10*i: blk0 0x48b000, blk1 0x1f0000, blk2 0x305000, blk3 0xa20000, blk4 0x258000, blk5 0x218000, blk6 0x1a4000, blk7 0. Total 0x19b4000 (about 26.9 MB). Entry 7 is skipped (size 0). Current block index is at 0x58a918 (`SysMemory::SetHeapBlock` 0x1fa510). Use +4 and +8 for region classification: a pointer inside [buffer, buffer+size) belongs to block i. Roles confirmed from the code: block 1 holds CScheEuro and its data block (`SetHeapBlock(1)` at 0x202a74), block 6 holds the career work buffer and the PlGiTask buffer (0x21008c), blocks 2 and 3 hold the overlays (see the next rows). Blocks 0, 4 and 5 have no known user. | confirmed (`HeapInitialize` 0x14d840 disassembled: it fills entries 0 to 6 in order and loads the size with lw at the entry's +4) |
| 0x35ed98 | 0x3008 (12,296) | u32 count at +0, u32 at +4, then 0x400 slots of 12 bytes from 0x35eda0 | static | Loaded-overlay registry | Slot k at 0x35eda0 + 12*k: +0 pointer to the module path string inside the overlay image (e.g. "../PS2_EE_Release/gameprg.elf"), +4 header address = the overlay's load base, +8 check = name ^ header ^ 0x31415926. The image is linked at base 0 with the SNR2 header at offset 0, so address = base + overlay offset. A slot is empty when its header word is 0, and the first empty slot is reused. The count at +0 is a high-water mark (never decremented); the append returns -1 at 0x400 slots. The word at 0x35ed9c is count ^ 0x31415926 after an append and the bare constant 0x31415926 after the init at 0x15b3c8 (the file's 0xbadc5 is only the pre-init value, and the file's count word is 0), so ignore it. Registered only from `snDllLoaded` 0x15b448 (calls at 0x15b4d4 and 0x15b77c), unregistered from 0x15b600. The only reliable way to find an overlay base at run time. | confirmed (`register` 0x15b288, `unregister` 0x15b370, `snDllLoaded` 0x15b448, `snDllUnload` 0x15b590; see also `DOC/SNR2_FORMAT.md`) |
| 0x34da18 | 0xc0 (8 rows x 0x18) | array of 6 x u32 | static | Overlay file index table | Constant, never written at run time (only lw and addiu references at 0x10bad4, 0x10bcfc, 0x10be0c). Rows: 0 simprg, 1 gameprg, 2 movieprg, 3 saveprg, 4 ceditprg, 5 vsprg, 6 yrstprg, 7 testprg. Row +0 = 5, +4 = name pointer, +8 = 1, +0xc = 0, +0x10 = heap-block selector (2, 2, 3, 3, 0x40000003, 3, 0x40000003, 3), +0x14 = block to recreate first (5, 5, then 0). The selector goes to `SetCurrentBlock` (0x10d5dc) as selector & 0x7ffffff, so the block is 2 for SIMPRG and GAMEPRG, 3 for MOVIEPRG, SAVEPRG, VSPRG and TESTPRG. Selector 0x40000003 (CEDITPRG, YRSTPRG) is block 3 allocated from the top: bit 0x40000000 picks the reverse allocator 0x148698 instead of 0x148660. Allocation alignment is 0x800 when bit 0x08000000 of the file-manager entry's +0x30 word is set and 0x40 when it is clear (`movz` at 0x14867c and 0x1486bc). Per the reading of `CommonSetup` 0x10cb9c, the bit is set when the row's +8 flag is 1, which holds for all 8 rows, so overlays use 0x800. Overlay sizes (SNR2 header word +0x2c): SIMPRG 0x2f0628 (3,081,768 B), GAMEPRG 0x2e518e (3,035,534 B), MOVIEPRG 0x6c072, SAVEPRG 0x75c18, CEDITPRG 0x2f17f, VSPRG 0x22fa5, YRSTPRG 0x5118d, TESTPRG 0x52caa. SIMPRG and GAMEPRG each fit block 2 (0x305000 = 3,166,208 B), but not both at once. | confirmed for the table values and the selector decoding; empirical for the 0x800 alignment (the link from the row's +8 flag to the bit was read only in `CommonSetup`). This is configuration, not a live value. The usable anchor at run time is the sbHeap table and the registry |
| 0x3909a8 | 4 | u32 pointer to PlPworkTask (0x5c bytes) | static | Career work buffer root ("pwork") | Root of the pwork state. Created by the first script command, `Pwk.Create` at ROOTMAINSEQ 0x0010, before SelectVideoMode, the logo and the title, so it is non-zero from boot through logo, title, demo, VS and career. `Pwk.Delete` (ROOTMAINSEQ 0x1a20) is unreachable in play, so the pointer never changes again within a boot. 0 only before that first command has run. Object: +0x14 vtable 0x406f90, +0x19 flag byte (block 8 omitted when set, never in retail), +0x1c pointer to the work buffer (heap block 6, align 0x10, zeroed, total size u32 at +0x54), +0x28 + 4*i offset of block i for i = 0..10 (0xffffffff = absent). Block address = *(p+0x1c) + *(p+0x28+4*i). The offsets are drawn once, when the object is built (`plUty_ShuffleUint8` 0x235270, only call at 0x21d774), each block 8-byte aligned, and then stay fixed for the boot. Block sizes are table 0x533ac8 minus 8: 0:0x20e48 1:0x129e8 2:0x120c0 3:0x530 4:0xa8 5:0xb50d0 6:0x1ce8 7:0x44 8:1 9:8 10:1 (blocks 0..9 sum 1,035,469; block 10 is extra). Created by `plPwork_CreatePwork` 0x21d628 (store 0x21d65c, only caller 0x1104b8 inside `PwkCallbackCommand_Create` 0x110498), deleted by `plPwork_DeletePwork` 0x21d698 (store of 0 at 0x21d6c8, only caller 0x110570). New Game and Load decode into the blocks in place and do not re-create or re-shuffle them. The blocks are blank until New Game or Load fills them. Per-block contents are in `DOC/SAVE_FORMAT.md`. | confirmed (code and sequencer scripts). Same chain recorded from PCSX2 save states in `DOC/SAVE_FORMAT.md` (Nexxus's report, 2026-10-27) |
| 0x35c970 | 4 | u32 | static | Pwk init latch | Initial value 1 in the file. `PwkCallbackCommand_Create` creates the Pwk objects only while it is 1, clears it at 0x110500, and sets it back to 1 at 0x110518 when `pwkOteam_WaitInit` returns 1. So the command is a two-phase poll that can be re-armed, but the script calls it once. | confirmed (`PwkCallbackCommand_Create` 0x110498 disassembled) |
| 0x390784 | 4 | u32 pointer to the PlGiTask buffer (0x32668 bytes) | static (slot), heap (buffer) | PlGiTask buffer slot | Heap block 6 (`SetHeapBlock(6)` at 0x21008c), allocated once by `bufer_alloc` 0x210070 from `PwkCallbackCommand_Create` (0x1104c0, right after CreatePwork), and freed by `bufer_free` 0x2100c8 only from `PwkCallbackCommand_Delete` (0x110548, unreachable). So it is a constant, non-zero heap pointer from boot, not a match flag. The PlGiTask accessors read this slot, not 0x3906d8. | confirmed (code and sequencer scripts) |
| 0x390650 | 4 | u32 pointer to CScheEuro (0x41c bytes) | static | CScheEuro singleton | Calendar and competition system, allocated with `SetHeapBlock(1)`. 0 = not created. Created by `CreateScheEuro` 0x202a50 (store 0x202b50), cleared by `DeleteScheEuro` 0x202ba8 (store 0x202bdc, only caller `Sche.Finalize` 0x113408). CreateScheEuro stores two vtable-like words, both valid keys for the creation mode: u32[s+0x20] = 0x406c28 Normal (career), 0x406b48 FirstPromote (opening playoffs), 0x406a68 VS, and u32[s+8] = 0x406c78, 0x406b98, 0x406ab8 for the same three modes. They are two vtables of one object, so use one set consistently. The pointer is set before `initialize` 0x203030 finishes, so also gate on `isFinishedInitialize` 0x203120. +0x408 is the initialize argument (1 only for InitializeContinue). For the VS class, u32 at +0x40c is the runtime-select-competition flag 4, set by `TeamEntryLoadCompCB` 0x206e5c; it is not a proven demo flag. Non-zero windows are listed in the pointer-chain table below. | confirmed (code and sequencer scripts) |
| 0x35c9a4 | 4 | u32 pointer | static | CSystemRootTask pointer | System root task. Written once at 0x112c64 on the first Execute of the root task (guarded by the check at 0x112c3c), never cleared. Getter at 0x113028. Non-zero means boot finished and the task tree exists. | confirmed |
| 0x35c9a8 | 4 | u32 pointer | static | CGameRootTask pointer | Game root task. Written once at 0x112c9c under the same one-shot guard. Getter at 0x113038. Its root module controller is at object +0x1c (read by `GetRootModule` 0x112f60, null until the first Execute of CGameRootTask). Non-zero means the task tree exists. | confirmed |
| 0x35c9ac | 4 | u32 | static | eFcEuroGameMode | Write-only. The only writer is `SetGameMode` 0x113090 (store 0x113098), called only from the sequencer handler at 0x10c324. The only reader, `GetGameMode` 0x113080, has no caller in the executable, and no overlay imports it. The only scripts that call SetGameMode are ROOTMAINSEQ 0x06a0 and 0x08a8, both with the literal 0, so the word is always 0. Not a mode indicator. | confirmed for address, size and accessors; empirical for the value 0 (scripts and import tables) |
| 0x35d4a0 | 4 | u32 | static | Per-frame counter | Incremented once per call of `ExecuteUpdateGameSystem` 0x149b40 (the increment at 0x149b48 to 0x149b58, lui 0x36 / -0x2b60), which the main loop calls at 0x14eee4, between `CSbTaskManager::Execute` 0x11d800 and `Draw` 0x11d828. Zeroed at game-system init (store at 0x14974c, in a branch delay slot). Getter `etc::GetGlobalCounterGameSystem` 0x14a448. Known readers, both in the executable's own .text: 0x1148b8 (demo pairing, mod 50) and 0x2748a8 (in the FC_EURO_WS_COMMON code). No overlay reader was shown. Wraps at 32 bits. Runs in every mode, so it shows the process is alive, not that a match is running. | confirmed for the address, increment, zero-store, getter and caller; empirical that the main loop runs once per video frame (the vsync wait was not read) |
| 0x39066c | 4 | u32 pointer to Param::PlBpinfoTask (0x120 bytes) | static | PlBpinfoTask singleton (`plBp_GetBpinfo` 0x20ded0) | Heap object built from the PBDATA pack by the Bp-data read callbacks. Set by `plBp_Create` 0x20dd78 (store 0x20ddf0, called at 0x11034c inside the Bp creator 0x1101c8), cleared by `plBp_Delete` 0x20de70 only when called with a non-zero argument (store 0x20deac, from 0x110398). Create reuses the object through `init` 0x20c5d8 when the pointer is already non-zero. Over 60 callers of the getter. Its lifetime equals that of the BPDATA buffer at 0x35c960: set by `Pwk.BpDataReadFile` (0x110d6c) and zeroed by `BpDataFreeFile` (0x110dbc). So it is 0 at boot, logo and title, 0 during the 3D match (the Game module), and non-zero in the attract demo, new game, club edit, career and after a match. Target layout is documented elsewhere. | confirmed (store, clear and size; the script brackets come from `sqb.py dis` of the ROOT scripts) |
| 0x35c960 | 4 | u32 pointer | static | BPDATA buffer pointer | Written at 0x110d70 (start of `BpDataReadFile`, before the asynchronous read completes) and zeroed at 0x110de0 (`BpDataFreeFile`). Script brackets: ROOTMAINSEQ 0x530..0x7f0 (new game and club edit, also re-freed and re-read inside ROOTCLUBEDITSEQ 0x5c0..0x638 and 0xea8..0x13a0) and ..0x1948 (career end); ROOTDEMOMATCHSEQ 0x68..0x1e0 (the attract demo); ROOTMATCHSEQ frees it at 0x488 (zero from just before the 3D match) and re-reads it at 0x688. | confirmed (code and `sqb.py dis`) |
| 0x391cf8 | 4 | u32 pointer to PwkEditTask (0x23c bytes) | static | PwkEdit singleton | Set by `pwkEdit_Create` 0x23c328 (store 0x23c354) from `Pwk.Create` (0x1104c8), cleared by `pwkEdit_Delete` 0x23c3a0 (store 0x23c3d0) from `Pwk.Delete`, which is unreachable. So it is non-zero for the whole boot after the first script command and cannot gate any mode. Getter at 0x23c3e8; its name is not recorded in the symbols, so "pwkEdit_GetPwkEdit" is unconfirmed. Created in retail too, not debug-only. | confirmed |
| 0x5eb170 | 4 | u32 pointer to PwkScript (0x24 bytes) | static (.bss) | PwkScript singleton | Set by `pwkScript_Create` 0x256ff8 (store 0x257020) from `Pwk.Create` (0x1104d0), cleared by `pwkScript_Delete` 0x257058 (store 0x257088) from `Pwk.Delete` (unreachable). Getter `pwkScript_GetPwkScript` 0x2570a0. Same lifetime as 0x391cf8: set once at the start of the boot, never cleared in retail. It is not a "Pwk world loaded" flag. | confirmed |
| 0x3906d8 | 4 | u32 pointer to Param::PlGiTask buffer (0x32668 bytes) | static | plGi pointer (`plGi_Get` 0x210960) | The match-day gate. Set by `plGi_Create` 0x2108f0 (store 0x210920) to the value of [0x390784] (read by 0x210148), zeroed by `plGi_Delete` 0x210940 (store 0x210954). While non-zero it equals [0x390784]. Callers of `plGi_Create`: 0x20373c (`CScheEuro::initializeTodayMatch`, called at 0x113abc inside `Sche.MatchStart` 0x113a38 only when `getTodayMatchNum(1)` is non-zero) and 0x11451c (`Sche.CreateGiForFirstMatch`). Callers of `plGi_Delete`: 0x203808 (`deleteGameInterFace`, via `finalizeTodayMatch` at 0x11406c inside `Sche.MatchEnd`) and 0x114540 (`DeleteGiForFirstMatch`). So it is non-zero from MatchStart to MatchEnd of a match scheduled today, covering the pre-match menu, the 3D match and the post-match screens, and 0 on days without a match. The accessors read the 0x390784 slot, so team ids, stats and logs stay readable after `plGi_Delete` until the next `plGi_Create`. | confirmed (jal scan and code); whether a title-demo match creates it is not traced |
| 0x3906dc | 4 | u32 pointer to plGiManage object (0x24 bytes) | static | plGiManage pointer (`plGiManage_Get` 0x214130) | Heap block from `FcEuroMalloc(0x24, 0x10)` (0x2140d4), set by `plGiManage_Create` 0x2140c8 (store 0x2140e4) from `PwkCallbackCommand_GetGameIfData` (script command `Pwk.GetGameIfData`, ROOTMATCHSEQ 0x998), freed and zeroed by `plGiManage_Delete` 0x2140f0 (store 0x214114) from `PwkCallbackCommand_FreeGameIfData`. Non-zero only between those two script commands (the post-match income stage), and the address changes every match. | confirmed (jal scan and scripts) |
| 0x34defc | 4 | u32 | static (.data) | Current language slot | `Localize_GetLanguage` 0x10e2a0. Written at boot by `Localize_DefaultLanguage` 0x10e1c0 (stores at 0x10e20c to 0x10e25c and 0x10e264) and later by `Localize_SetLanguage` 0x10e2b0 (the language menu). Encoding: 0 JP, 1 UK English, 2 FR, 3 DE, 4 IT, 5 ES, 6 Dutch (never selected). Used to build file names (the digit, 0x10cad4) and "%d_%d.mbb" (0x10e2f8). File value 0. | confirmed (jump table at 0x51a6d0, lui 0x52 / -0x5930; encoding also in `DOC/MBB_FORMAT.md`) |
| 0x34df00 | 4 | u32 | static (.data) | Boot-time language slot | `Localize_GetFixedLanguage` 0x10e290. Copy of the boot default, written only at 0x10e278 in the executable (overlays not searched). `Localize_DefaultLanguage` turns a `sceScfGetLanguage` result of 0 into 1 (`movn` at 0x10e1d8), then looks up values 1 to 7 in the table at 0x51a6d0, which gives slots 1, 2, 5, 3, 4, 1, 1 for results 1 to 7 (English 1, French 2, Spanish 5, German 3, Italian 4, and 6 and 7 fall back to 1). A result of 8 or more takes the default at 0x10e260 and stores 1. Does not change after boot. File value 0. | confirmed |
| 0x569dc0 | 0x10 | RNG state words | static (.bss) | Shuffle generator state | `plUty_ShuffleUint8` passes this state to `fcEuroRand_Get0toI` 0x111730. `fcEuroRand_Init` 0x111698 (called at 0x112940 when the root module is built) sets 0x569dc0 = 0x12345678 and 0x569dc4 = 0x87654321, copies the EE timer 0 count (the word at 0x10000000) into 0x569dc8, and points 0x569dcc at it. Whether the pwork block order is the same on every boot depends on other draws before `Pwk.Create`; those were not enumerated. | empirical (code read; no run observed) |
| 0x5698d0 | 4 per module id | table of u32 | static (.bss) | Module activity table | Slot at 0x5698d0 + 4*id is set by `Module.Start` (store at 0x10b2d8, which executes even when the controller is 0) and zeroed by `Module.Delete` (0x10b684). It is non-zero from `Module.Start` until the script's `Module.Delete`, not until the module's own end. Zero at boot. Slots: Game (6) 0x5698e8, SimRoot (24) 0x569930, MatchMenu (35) 0x56995c, Logo (44) 0x569980, Title (45) 0x569984, Load (47) 0x56998c, Save (48) 0x569990, Launcher (69) 0x5699e4. In a match SimRoot is deleted before Game starts and restarted after it. The attract demo also runs the Game module (and skips MatchMenu), and so do VS matches, so pair slot 6 with 0x34d43c. | empirical (code and `sqb.py dis` of ROOTMATCHSEQ and ROOTDEMOMATCHSEQ) |
| 0x34d43c | 4 | u32 | static (.data) | Demo flag | Initial value 0. Only writer `fcEuroDummyCommand_SetDemoFlag` (store 0x109394): set to 1 at ROOTDEMOMATCHSEQ 0x18 and cleared at 0x208. Readers 0x109328 and 0x1093a8. It is not the PlGiTask demo flag. | confirmed (code and script) |

### Pointer chains and stability

Rule for every heap-resident target: the root address is fixed, the
target address is not. The Pwk roots (0x3909a8, 0x391cf8, 0x5eb170) and
the PlGiTask slot (0x390784) are filled once at the start of the boot
and keep their value for the whole boot, but re-reading a chain after
any 0 to non-zero transition of its root costs nothing, and is the safe
habit across a reset or a save-state load.

**Heap and overlay entries**

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| sbHeap block table | Entry i at 0x35dae8 + 0x10*i. Buffer base = u32 at 0x35daf0 + 0x10*i. Size = u32 at 0x35daec + 0x10*i. Block 2 base at 0x35db10, block 3 base at 0x35db20. | After `HeapInitialize` 0x14d840 (handle and buffer non-zero for blocks 0 to 6; entry 7 stays 0). Before that only the size fields are set. Test: buffer in 0x100000 to 0x1ffffff. | Table address, sizes and buffer bases are fixed from boot until `HeapFinalize` or a soft reset, and stay the same across frames, menus, loads, seasons and matches. The +0 handle can be replaced by `fcEuro_ReflashHeapBlock`. Buffer values come from libc memalign and are not shown to be the same across boots. |
| Overlay registry | Count = u32 at 0x35ed98. For k in 0 to min(count, 0x400) - 1: name pointer = u32 at 0x35eda0 + 12*k, base = u32 at 0x35eda4 + 12*k. Overlay variable address = base + overlay offset. | A slot is usable only while its header word (0x35eda4 + 12*k) is non-zero. The table is valid once the executable has run its init at 0x15b3c8. | The table address is fixed for the whole run. A slot's base is stable only while that overlay stays loaded. Unload zeroes the slot, a reload may land at a different base, and the slot index may change (first empty slot is reused). Count never decreases. Re-scan rather than cache. |
| Overlay file index table | Row r at 0x34da18 + 0x18*r. | Always (static, never written). | Constant for the whole session. It does not say whether an overlay is loaded. The overlay's own offset inside its block is not proven fixed. |
| Career work buffer | p = u32[0x3909a8]; base = u32[p+0x1c]; off = u32[p+0x28+4*i]; block i = base + off, for i = 0..10. | u32[0x3909a8] != 0 and u32[p+0x1c] != 0 (true from the first script command `Pwk.Create` at ROOTMAINSEQ 0x0010 onward), and off != 0xffffffff. The block contents are blank until New Game or Load. | p, base and every offset are fixed for the whole boot: not reallocated or reshuffled by New Game, Load, saves, the demo, matches, year rollover or a return to the title. The shuffled offsets are drawn once per boot. Whether they are identical on every boot of the same build is not settled (see Unconfirmed). Re-reading the chain is optional defensive practice. |
| PlGiTask buffer slot | u32[0x390784] | Non-zero from boot (after `Pwk.Create`). | Constant for the whole boot. Heap object, not a match flag. |
| CScheEuro | s = u32[0x390650]; mode = u32[s+0x20] (or u32[s+8]). | u32[0x390650] != 0 and the object has finished initializing (`isFinishedInitialize` 0x203120). Non-zero windows (script offsets): `Sche.Initialize` (ROOTMAINSEQ 0xc30, new game after the opening playoffs) and `InitializeContinue` (0xa80, 0xaf8) until `Sche.Finalize` (0x1918); `InitializeFirstCheck` (ROOTCLUBEDITSEQ 0x8c0, mode FirstPromote) until `Finalize` (0xc70); `Initialize_VsMode` in ROOTVSMODESEQ 0xa8 until `Finalize` 0x490 or 0x568; and `Initialize_VsMode` in ROOTDEMOMATCHSEQ 0xa8 until `Finalize` 0x1d0, so the title attract demo creates the VS-mode object (u32[s+0x20] = 0x406a68, u32[s+8] = 0x406ab8). Zero at boot, logo, idle title, Load, and club creation outside the opening playoffs. New Game fires the pointer twice (FirstCheck mode 1, Finalize, then Initialize mode 0). u32[s+0x40c] is meaningful only when mode is VS and a competition load has run. | The slot address is fixed. The pointer is stable between create and `Finalize`; after `DeleteScheEuro` and a new `CreateScheEuro` the heap address may differ. Vtable constants are fixed. Creator calls: 0x113310 (`Sche.Initialize`) passes 0, 0x113368 (`InitializeFirstCheck`) passes 1, 0x1133c8 (`InitializeContinue`) passes 0, 0x114604 (`Initialize_VsMode`) passes 2. |
| PlBpinfoTask | u32[0x39066c] | Non-zero and below 0x2000000, between `Pwk.BpDataReadFile` and `BpDataFreeFile` (same lifetime as 0x35c960). Zero during the 3D Game module. | Address fixed. Value stable while the object exists (repeated Create reuses it). Can change after a Delete and a new Create. Do not cache it across a load or a match. |
| PwkEdit and PwkScript | u32[0x391cf8], u32[0x5eb170] | Non-zero from `Pwk.Create` (0x1104c8, 0x1104d0), i.e. from the start of the boot. Never cleared in retail, so they cannot gate any mode. | Slot addresses never change. Written only on create and delete, so the values are constant for the boot. |
| plGi | u32[0x3906d8] | Non-zero and below 0x2000000, from `Sche.MatchStart` to `Sche.MatchEnd` of a match scheduled today (and from `CreateGiForFirstMatch` to `DeleteGiForFirstMatch`). While non-zero its value equals u32[0x390784]. | Slot address fixed. The target is the constant 0x390784 buffer, so it is the same address in every match of the boot. |
| plGiManage | u32[0x3906dc] | Non-zero and below 0x2000000, only between `Pwk.GetGameIfData` and `Pwk.FreeGameIfData`. | Slot address fixed. The target is freed and reallocated on each delete and create, so it has a new address every match. |

**Other static entries**

| Entry | valid_when | stable_across |
|---|---|---|
| Executable image 0x100000 to 0x5f95f4 | Always after boot, in every mode. | Frames, screens, loads, matches, seasons and saves. Not relocated. The writable sections (.data, .sndata, .gcc_except_table, .sbss, .bss) hold changing values; .text and .rodata are constant. |
| Main thread stack 0x1fd0000 to 0x1fff000 | Always. Any pointer from 0x1fd0000 up to 0x1ffefff is a stack address, not game data. | Range constant. Contents volatile. |
| sbrk break 0x3a89c4 | Always after boot. Test: value >= 0x5f95f4 and below 0x2000000. | Fixed address. The value rises when malloc extends the arena and can fall on a trim. Not reset by loads. Restored with a save state. |
| Root task pointers 0x35c9a4, 0x35c9a8 | Non-zero once the first Execute of the root task has run (zero before that). Test: value in 0x100000 to 0x1fffff. 0x35c9ac is always 0 and carries no mode. | Written once per run, never cleared. Stable across frames, screens, loads, matches and seasons. A reset or reboot recreates them and the heap target may move. |
| Frame counter 0x35d4a0 | After the game-system init (zero-store at 0x14974c) and while the main loop at 0x14eee4 runs. Valid in every mode. | Keeps counting through modes and overlay loads. Resets to 0 at game-system re-init or reset. Not shown to be saved in save data. |
| Language words 0x34defc, 0x34df00 | After `Localize_Create` has run at boot. Before that both read 0, which looks like the Japanese slot. On a PAL build expect 1 to 5. | Both fixed for the run. 0x34df00 changes only at boot. 0x34defc changes only if the language menu runs. Not a mode indicator. |
| Module activity table 0x5698d0 + 4*id, demo flag 0x34d43c | Table slot non-zero from `Module.Start` to the script's `Module.Delete`. 0x34d43c is 1 only inside the attract demo script. | Static addresses. Slot values follow the scripts, not the module's own end. |

### RetroAchievements notes

- Static addresses (the executable image, all pointer cells above) are
  safe to hard-code on the PAL release. Everything behind a heap
  pointer is not. Read the root, check it is non-zero and below
  0x2000000, then add the offset. Do not hard-code the target of any
  root.
- For career data, pair the chain at 0x3909a8 with a non-zero check on
  both u32[0x3909a8] and u32[p+0x1c]. The pointer is non-zero from the
  start of the boot, so it is not a "career loaded" flag: the blocks
  stay blank until New Game or Load fills them, and the title, the
  attract demo and VS mode use the same buffer. The shuffled block
  offsets are drawn once per boot and do not change on New Game or
  Load. Keep reading them through the chain rather than hard-coding
  them: whether they are identical on every boot is not settled. In
  RAIntegration terms, put the pointer read in an indirect chain.
- To read an overlay-resident value, walk the registry at 0x35ed98 for
  the slot whose name matches, take the header word as the base, and
  add the overlay offset. Skip slots whose header is 0. Do not use the
  count as the number of loaded overlays. Re-scan on mode changes
  because an unload zeroes the slot and a reload may land elsewhere.
- Use 0x35d4a0 for liveness only. A drop to a low value means a reset,
  a re-init or a reboot. It ticks through menus and loading, so it is
  not game time.
- Use 0x35c9a4 and 0x35c9a8 as "boot finished" gates, not as mode
  flags. Do not use 0x35c9ac: it is write-only and always 0. For a
  "season system alive" gate use 0x390650 plus `isFinishedInitialize`;
  for career versus VS read the vtable at u32[s+0x20] (0x406c28 career,
  0x406b48 opening playoffs, 0x406a68 VS and the title attract demo).
- Do not use 0x391cf8 or 0x5eb170 as a "Pwk world loaded" or mode flag.
  Both are set once at the start of the boot (`Pwk.Create`) and never
  cleared in retail.
- For "a match is on", u32[0x3906d8] != 0 covers the pre-match menu,
  the 3D match and the post-match screens of a match scheduled today.
  For "the 3D match itself", use the Game module slot 0x5698e8 and
  exclude the demo with 0x34d43c == 0. u32[0x39066c] and u32[0x35c960]
  are zero during the 3D match and non-zero around it.
- Do not read 0x3a89c4, 0x34da18, the stack, .text or .rodata for
  achievement logic. The first moves rarely, the others are constant or
  volatile.
- Region checks: any pointer inside [buffer, buffer+size) of an sbHeap
  entry is in that block. A pointer in 0x100000 to 0x5f95f4 is static.
  A pointer from 0x1fd0000 up to 0x1ffefff is a stack address.
- Pitfall: soft resets and save states. A save state restores all of
  EE RAM including the heap pointers; a soft reset frees and
  reallocates the heap blocks, so cached bases are invalid after it.
- Pitfall: the language words read 0 before `Localize_Create` runs.
  Gate on the title screen or later.
- Everything here is for the PAL release. The Japanese build has
  different addresses and needs a `gamever.py` lookup. For example the
  pwork global there is `lui 0x39 / lw -0x36b8`, i.e. 0x38c948, not
  0x3909a8 (`DOC/JAPANESE_RELEASE.md` line 177).

### Unconfirmed

These parts were disputed, left open, or not shown. Do not rely on them.

| Item | Reason |
|---|---|
| ".sndata holds symbol and relocation tables" | Its contents were not read. Only the kind-4 constants that match crt0 were checked. |
| Heap memory ends at the stack base 0x1fd0000, and "the whole arena holds the heap blocks" | Not shown. The real limit is whatever EndOfHeap returns, which was not traced. A heap size of -1 usually means "up to the stack base". |
| Buffer bases of the sbHeap blocks are the same on every boot | Not verified. They come from libc memalign and depend on allocations before `HeapInitialize`. |
| Block 2 base is 0xc75000 or near it | 0xc75000 is an observed overlay base (`DOC/ECONOMY.md`, `DOC/WIDESCREEN.md`), not derived. Blocks 0 and 1 together are 0x67b000 bytes, and 0xc75000 - 0x67b000 = 0x5fa000, just above `_end` 0x5f95f4, but the odd difference (the malloc header and alignment) was not reconciled. |
| Overlay allocation direction (bottom or top) in blocks 2 and 3, and that the flags toggle at 0x10d788 | Not resolved. Only the selector bits were traced (bit 0x40000000 picks the reverse allocator, bit 0x20000000 wraps the allocation in `ForceBlockSwitch`). The hop from the resource +0xfc to the file-manager entry +0x30 is read in `CommonSetup` 0x10cb9c but was not independently re-checked. |
| Pwork block offsets identical on every boot | The shuffle state 0x569dc0 starts at the constant 0x12345678 and `Pwk.Create` is the first script command, so the order may be deterministic, but draws between `fcEuroRand_Init` (0x112940) and `Pwk.Create` were not enumerated and no run was observed. |
| CScheEuro +0x40c is an attract or demo flag | Refuted as stated: the only writer is `TeamEntryLoadCompCB`, which sets it from runtime-select-competition flag 4. Whether demo matches use it is unverified. |
| CScheEuro turn field and `getNowTurn` 0x2042a8 | The turn is read through the ScheduleControllerBaseSystem pointer at u32[s+0]. The inner offset was not traced. |
| A match object (0x3906d8) exists in a title-demo match | `Sche.MatchStart` is called at ROOTDEMOMATCHSEQ 0x118, but `initializeTodayMatch` is guarded by `getTodayMatchNum(1)` (0x113a6c), and what the demo setup makes it return was not traced. |
| Cancelling the attract demo with a button | Whether it skips the `SetDemoFlag 0` at ROOTDEMOMATCHSEQ 0x208 (and so leaves 0x34d43c at 1) and whether CScheEuro is finalized on that path was not traced. |
| Stale non-zero values after a soft reset, the developer launcher or a save state from another boot | Whether 0x390650, 0x3906d8, 0x39066c or 0x35c960 can keep old values was not checked. Heap target addresses across boots were not measured. |
| `pwkEdit_GetPwkEdit` as the symbol name at 0x23c3e8 | The getter is not named in the symbols. |

### Still unknown

- The actual runtime values were not measured: the buffer base of each
  sbHeap block (u32 at 0x35daf0 + 0x10*i) and the load base of SIMPRG,
  GAMEPRG, SAVEPRG and the others in the registry at 0x35ed98. A PCSX2
  or PINE read of the registry and the block table would settle whether
  they are the same on every boot of the same disc.
- Direction of overlay allocation in heap blocks 2 and 3 (bottom or
  top), and whether SIMPRG stays resident while GAMEPRG (matches) is
  loaded, which decides whether both bases are valid at the same time.
- Which game objects live in heap blocks 0, 4 and 5 (0x48b000,
  0x258000, 0x218000 bytes). Block 5 is reset by
  `fcEuro_ReflashHeapBlock(5)` before each overlay load.
- Meaning of 0x35db70 (set to 1 at 0x112f14 when the root module
  controller's Wait returns 0) and 0x35db74 (read in the card and tray
  handler near 0x14e60c). Possibly "root module finished" and a
  power-off flag. Not traced.
- Whether any overlay reads 0x35c9ac or 0x35c9a8 directly (the import
  tables show no `GetGameMode`, but direct reads of the word were not
  scanned for).
- The internal layout of an sbHeap block (`sbHeapCreate` 0x1f8350), so
  the offset of the first user allocation inside a block buffer is
  unknown.
- Memory-card and save I/O buffers (SAVEPRG.REL working buffers, the
  5,169,290-bit stream buffer) were not located in RAM. Only the career
  work buffer (pwork) was resolved as the in-memory form of the save.
- Module slot ids 171, 172 and 173 (a second Game id): only the
  launcher was seen to use them. Wild card id 70 (ROOTEVENTSEQ 0x208)
  was not resolved.
- Whether VS mode (ROOTVSMODESEQ) keeps 0x35c960 and 0x39066c loaded
  for its whole stay: ROOTMATCHSEQ frees and re-reads the buffer around
  each Game module.
- The contents of .sndata, and the layout of the memory below 0x100000
  and above 0x1fff000 (assumed BIOS and kernel by convention).
- Other threads' stacks: the game may run threads other than the main
  one; they were not examined.
- The Japanese build: only the pwork global is known to differ
  (0x38c948). No other address here was checked through `gamever.py`
  (`ADDRESSES` has no entry for 0x390650, 0x5698d0 or the vtable
  constants).

### Checking the claims

```bash
# the first script command creates the Pwk roots (latch 0x35c970, stores of 0x3909a8 via 0x21d628)
python SRC/sles_disasm.py ISO/SLES_541.51 dis PwkCallbackCommand_Create
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork
# sbHeap table: size at +4 (0x35daec), buffer at +8, handle at +0 (stores at 0x14d880 to 0x14d884)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 14d840 40
# overlay allocation alignment: movz picks 0x40 only when bit 0x08000000 is clear
python SRC/sles_disasm.py ISO/SLES_541.51 addr 148660 14
# crt0: a1 = 0x1fd0000 (lui 0x1fd), a2 = 0x2f000, then SetupThread (syscall 0x3c)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 100198 14
# language slots: jump table at lui 0x52 / -0x5930 = 0x51a6d0, stores to 0x34defc and 0x34df00
python SRC/sles_disasm.py ISO/SLES_541.51 addr 10e1c0 40
# registry init at 0x15b3c8 (count word 0x35ed98 zeroed, word +4 = 0x31415926)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 15b3c8 12
# frame counter increment (lui 0x36 / -0x2b60 = 0x35d4a0)
python SRC/sles_disasm.py ISO/SLES_541.51 dis ExecuteUpdateGameSystem
# match-day gate: plGi_Create stores [0x390784] into 0x3906d8 (sw at 0x210920)
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Create
```

## Game mode, screens and flow

The PAL release has no single "current screen" or "game mode" word. The
top-level flow is a script-driven state machine: RootMainSeq starts
screen modules and Root*Seq sub-scripts, and each screen is a heap
object with no static pointer to the active one. The best indicators
are therefore indirect: whether a schedule session object exists, which
kind it is, whether a match-day object exists, the attract-demo flag, a
few one-way latches and counters, the module activity table, and the
developer skip flags. All addresses are PAL `SLES_541.51`. Everything
here was read from the executable and the root scripts (static
analysis); nothing was seen running in PCSX2. The only exception is the
overlay base 0xc75000, which two docs record as seen in PCSX2 (see the
overlay row).

Labels: **confirmed** means the address and behaviour are proven by game
code at the cited addresses. **empirical** means inferred from script
call sites, data or observation and not proven by code.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x390650 | 4 | u32 pointer to a heap CScheEuro (0x41c bytes, heap block 1), 0 = none | static | ScheEuro_ptr | Non-zero while a CScheEuro session object exists. Created by CreateScheEuro (0x202a50, store at 0x202b50) from Sche.Initialize (0x1132f8, mode 0), Sche.InitializeContinue (0x1133b0, mode 0), Sche.InitializeFirstCheck (0x113350, mode 1) and Sche.Initialize_VsMode (0x1145e0, mode 2, used by VS mode and by the attract-demo match). Zeroed by DeleteScheEuro (0x202ba8, store at 0x202bdc) through Sche.Finalize (0x113408). It is 0 at boot, logo and title (idle, before the demo starts). The pointer is set before initialisation finishes (isFinishedInitialize 0x203120), so it means "session exists", not "data ready". A new career fires it twice: mode 1 (opening playoffs), Finalize, then mode 0. | **confirmed** (creator modes read at 0x113310, 0x113368, 0x1133c8, 0x114604; mode dispatch at 0x202a84 to 0x202a94). Script windows: RootMainSeq Sche.Initialize 0xc30 and InitializeContinue 0xa80 / 0xaf8 until Finalize 0x1918; RootClubEditSeq InitializeFirstCheck 0x8c0 until Finalize 0xc70; RootVsModeSeq Initialize_VsMode 0xa8 until Finalize 0x490 / 0x568; RootDemoMatchSeq 0xa8 until Finalize 0x1d0 (empirical, from `sqb.py dis`). |
| *(0x390650)+0x08 | 4 | u32 pointer into .data (constant) | heap | ScheEuro_vtable | Session kind. 0x406c78 = mode 0 (a career: new game or Continue), 0x406b98 = mode 1 (FirstPromote, the opening playoffs of a new career, created by InitializeFirstCheck from RootClubEditSeq), 0x406ab8 = mode 2 (VS mode or attract-demo match). The virtual at vtable+0x1c (IsVsMode) returns 0 for modes 0 and 1 and 1 for mode 2. This word does not separate VS mode from the demo. A second, equivalent key is the word at +0x20: 0x406c28 / 0x406b48 / 0x406a68 for modes 0 / 1 / 2 (store at 0x202b40). Use one pair consistently. | **confirmed** from CreateScheEuro 0x202a50 (stores at 0x202b4c and 0x202b40) and the vtable contents. Both ROOTVSMODESEQ and ROOTDEMOMATCHSEQ call Sche.Initialize_VsMode at 0xa8 (empirical). |
| 0x34d43c | 4 | u32 (0 or 1) | static | Demo_flag | 1 while RootDemoMatchSeq runs (the attract-mode match). Set to 1 at script offset 0x0018 and back to 0 at 0x0208. RootMatchSeq tests it with Dummy.CheckDemo (0x0228, 0x07d0). Initial value 0. Not the same variable as the Param::PlGiTask demo flag (SetDemoFlag / GetDemoFlag 0x33c408 / 0x33c438, a regulation-style flag in the match object). | **confirmed**. Single writer fcEuroDummyCommand_SetDemoFlag 0x109358 (store at 0x109394, `sw $a0,-0x2bc4`); readers 0x109328 and 0x1093a8. |
| 0x3906d8 | 4 | u32 pointer (0 = none) | static | PlGiTask_ptr | Param::PlGiTask, the match game-interface object (teams, score, cards, clock). Either 0 or equal to [0x390784]. Non-zero from plGi_Create (0x2108f0, store at 0x210920) to plGi_Delete (0x210940, clear at 0x210954), reader plGi_Get 0x210960. Created by CScheEuro::initializeTodayMatch (0x203708, call 0x20373c), reached from Sche.MatchStart (0x113a38, call at 0x113abc, only when getTodayMatchNum(1) is non-zero), and by Sche.CreateGiForFirstMatch (0x1144d0, call 0x11451c). Deleted by deleteGameInterFace (call 0x203808, via finalizeTodayMatch at 0x11406c inside Sche.MatchEnd) and Sche.DeleteGiForFirstMatch (0x114538, call 0x114540). So it is non-zero from MatchStart to MatchEnd of a match scheduled that day: pre-match menu, 3D match and post-match screens. It is 0 on title, in menus and on days without a match. Data readable through it: home team id u32 at +0x1fba0, away at +0x24540; game-time copy u32 at +0x1f540 (GetGameTime 0x33c390 reads buffer+0x18000+0x7540); final score words at +0x1faf0 and +0x1fb9c (side struct +0x1fa48 + 0xac*side, +0xa8; GetGameScore 0x2140a0 returns u32[u32[obj+4*side]+0xa8] for side 0 or 1, where obj holds two side-struct pointers, so it does not read task+0). The score and time words are refreshed when a match screen is set up (function 0x14c9a8, only caller GAMEPRG 0x9230), not at a dedicated match-end moment (empirical; which screen entry is open). | **confirmed** (store 0x210920, clear 0x210954, jal scan finds only the listed callers; GetGameTime and GetGameScore disassembled). Offsets of the data words are from the season canon (read at 0x210198 and 0x210fdc); not seen running. Presence during VS matches and the attract demo is unverified. |
| 0x390784 | 4 | u32 pointer to heap block 6 (0x32668 bytes) | static | PlGiTask buffer slot | The buffer that 0x3906d8 points at while a match exists. Allocated once by bufer_alloc (0x210070, SetHeapBlock(6) at 0x21008c) from PwkCallbackCommand_Create (0x1104c0, right after CreatePwork), freed by bufer_free (0x2100c8) only from PwkCallbackCommand_Delete (0x110548), which is unreachable in play. So it is non-zero and constant from Pwk.Create (first script command, RootMainSeq 0x0010) for the whole boot. It is not a match flag. The PlGiTask accessors read this slot, not 0x3906d8, so team ids and stats stay readable after plGi_Delete until the next plGi_Create. | **confirmed** from the allocator and free sites; Pwk.Delete reachability from the script (empirical, `sqb.py dis`: Pwk.Delete only at RootMainSeq 0x1a20, behind the BranchIfZero at 0x1970). |
| 0x34d440 | 4 | u32 counter | static | FirstMatchCount | Counts completed turns of the new-career opening playoffs (the tutorial). Reset to 0 by fcEuroDummy_ResetFirstMatchCount (0x109460, store at 0x109468), called only from Sche.InitializeFirstCheck (call 0x113380). Incremented by fcEuroDummy_SetNextFirstMatchCount (0x109470, +1 at 0x109480), called only from Sche.FirstCheck (0x114090, call 0x1140f4). Read by the getter at 0x109488; RootClubEditSeq reads it with Dummy.GetFirstMatchCount (0x108e30) for event timing 12 + n. The increment check always returns 1 for the mode-1 object (vtable 0x406b98 slot +0x14 at 0x33b738), so it increments on every FirstCheck call. Initial value 0. Keeps its last value after the playoffs and is not saved. | **confirmed** for address and accessors. The meaning "completed playoff turns" is **empirical** (from ROOTCLUBEDITSEQ.SQB). Not seen in the running game. |
| *(*(0x3909a8)+0x1c)+*(*(0x3909a8)+0x28)+0x298 | 1 | u8 | heap | Pwork general block: last save point | Byte at +0x298 of Pwork block 0, set by pwkGen_SetSavePoint (0x244b78, `sb` to +0x298) and read by pwkGen_GetSavePoint (0x244bb0, `lbu`). SAVEPRG.REL calls the setter at 0x336b4 unless the Save argument is 5 (beq at 0x3366a4), and the Load path reads it at 0x32f70 as the Load module result. Values by the Save argument (empirical, GAME_FLOW.md): 1 = main-menu save, 2 = year-end autosave, 3 = start of the opening playoffs, 4 = club edit. It records the career phase at the last save or load, not the live screen. 0 before any save or load. Unrelated to PlPinfo +0x298 in SAVE_FORMAT.md. | **confirmed** for address, size and chain (get() 0x21d928 with i = 0 goes to pwGet 0x21da50, which returns u32[P+0x1c] + u32[P+0x28+4*i]). The meanings 1 to 4 and the use of the Load result by RootMainSeq are **empirical**. |
| 0x34d474 | 4 | u32 (0 or 1) | static | MovieFlag | One-way boot latch. Static initial value 1. The Title module constructor (MOVIEPRG.REL 0x1640) reads it with fcEuroDummy_GetMovieFlag (0x1094e0) to pick its phase row at 0x4c0c8 (1 = row with the opening movie), and its destructor (0x1820) calls fcEuroDummy_SetMovieFlag (0x1094d0, store at 0x1094d8) with 0. So it is 1 from boot until the first Title module ends, then 0 for the whole session. It is not a "title screen is showing" flag. | **confirmed**. Overlays other than MOVIEPRG were not audited for other callers of SetMovieFlag. |
| 0x5698d0 + 4*id | 4 each | u32 controller pointer, 0 = none | static (.bss) | Module activity table | One slot per module id (eMODULE). A slot is non-zero from Module.Start until the script's Module.Delete (not until the module's own end). Written by `sw $a0,($v1)` at 0x10b2d8 in Module.Start (table base lui 0x57 / -0x6730, index id*4; it executes even when the controller is 0) and cleared by `sw $zero,($v1)` at 0x10b684 in Module.Delete. Slots: Game(6) 0x5698e8, SimRoot(24) 0x569930, MatchMenu(35) 0x56995c, Logo(44) 0x569980, Title(45) 0x569984, Load(47) 0x56998c, Save(48) 0x569990, Launcher(69) 0x5699e4. In a match RootMatchSeq deletes SimRoot(24) at 0x498, starts Game(6) at 0x570, deletes it at 0x5a8 and restarts SimRoot at 0x638. The attract demo also runs Game(6) (through RootMatchSeq, skipping MatchMenu via Dummy.CheckDemo 0x228), so slot 6 is non-zero in the demo and in VS matches: pair with 0x34d43c. | **confirmed** for the store and clear sites and the table base (read at 0x10b2c8 and 0x10b674). The id-to-screen mapping comes from the script ids (empirical). Not seen running. |
| 0x34d428 | 4 | u32 skip-mode word (0 in retail) | static | Turn-skip dev flag | Developer turn-skip switch. Dummy.CheckTurnSkip (0x108b00) passes skip = 1 to the sequence controller when this word is 1. CheckYearMonthTurnSkip (0x108b78) passes skip = 1 only when this word is 1 and the TurnSkipType word at 0x34d470 is 0 (code at 0x108b98 to 0x108ba0). 0x34d470 holds 1 on the disc, so the year and month skip never fires even with this word set. fcEuroDummy_CheckTurnSkip (0x108e98) returns the raw word. It is also read by CheckMatchSkip (0x108cb4) and at 0x1080c0. No store to it exists in the executable. The neighbours 0x34d430 (first-match skip) and 0x34d434 (club-edit skip) are 0 in the file and have no stores either. | **confirmed** for address, size and the 0x34d470 condition (`lw $v1,-0x2b90` at 0x108b9c is 0x34d470). The meaning of values other than 1 is unknown. Overlay writers were not checked. |
| 0x34d42c | 4 | u32 (0 in retail) | static | Match-skip dev flag | fcEuroDummy_SetMatchSkip (0x1094c0, store at 0x1094c8) writes here. Dummy.CheckMatchSkip (0x108c90) returns 1 if this word or the turn-skip word 0x34d428 equals 1. RootMatchSeq tests it at 0x03e0 and a non-zero result jumps past the Game module (the 3D match). Zero in the shipped executable. The setter has no direct caller (only a function-pointer table entry near 0x4a9b0c, not traced). | **confirmed**. The "result is simulated" wording rests on GAME_FLOW.md (empirical). It is a debug module switch, not an anti-tamper check. |
| 0x34d438 | 4 | u32 (0 or 1) | static | Launcher flag | Set to 1 by RootLauncherSeq at its offset 0x0000 (Dummy.SetLauncherFlag 1, store at 0x1092ec) and back to 0 at 0x0248. So it is 1 only while the developer launcher or its test viewers run on a disc patched with --launcher. 0 in retail and again after the launcher is left. Dummy.CheckLauncher (0x109270) always returns 1, so retail skips the launcher. Read by fcEuroDummy_CheckLauncherFlag (0x1092f8); the neighbour 0x34d444 (read at 0x109310) is the cutscene number the launcher passes. | **confirmed**. It is a live "launcher running" flag, not a "patched disc" marker. Readers inside the launcher were not located. |
| 0x35c9ac | 4 | u32 (eFcEuroGameMode) | static | GameMode word (write-only) | Written by fcEuroRootTask_SetGameMode (0x113090, store at 0x113098), read only by fcEuroRootTask_GetGameMode (0x113080), which has no caller. The only writer call is the script command at 0x10c324, with literal argument 0 (RootMainSeq 0x06a0 and 0x08a8). None of the 8 overlays imports either function. It is 0 at all times. Do not use it as a mode indicator. | **confirmed** for address and the lack of readers. The constant argument 0 rests on the `sqb.py dis` output (empirical for the value). |
| *(0x39f6c4)+0x1ee0 | 4 | u32 (WP::CTopBar::eMODE_TYPE) | heap | TopBar mode type | Last mode set through SetModeType (0x2abba0, WP::CTopBar::SetModeType; CTopBar+0x1ec8 with CTopBar at CTopBarTask+0x18). Script command TopBar.SetModeType (handler 0x10c480) sets 2 in RootMatchSeq (0x02e0, 0x0888) and RootVsModeSeq (0x0048, 0x03b0), 3 in RootClubEditSeq at 0x0288 (club creation) and 0 at 0x0678. The Save module (SAVEPRG.REL) also calls SetModeType directly: 0x045498 sets 4 and 0x0455b4 sets 0. So value 4 does occur in retail while a save screen runs, and the word changes on save screens as well as by script. It is sticky: it is not cleared when leaving the match or VS menus, so 2 can persist. The script call is skipped when a TopBar virtual (+0x98) returns non-zero. | **confirmed** for the chain and the setter calls (SAVEPRG sites read with `snr2.py dis`: `addiu $a1,$zero,4` before the jal at 0x045498, `move $a1,$zero` after the jal at 0x0455b4). The meanings of 0, 2, 3 and 4 are **empirical** (call sites only). The initial value was not verified. |
| 0xc75000 (+0x2c = 0xc7502c) | 4 | u32 SNR2 header word at +0x2c (REL file size) | overlay | Overlay identity at the shared load base | While SIMPRG.REL or GAMEPRG.REL is resident, the SNR2 header stays at the start of the load buffer: u32 at 0xc75000 is 0x32524e53 ('SNR2') and u32 at 0xc7502c is the file size, 0x2f0628 for SIMPRG (career and management screens) or 0x2e518e for GAMEPRG (3D match). Other sizes: MOVIEPRG 0x6c072, SAVEPRG 0x75c18, CEDITPRG 0x2f17f, VSPRG 0x22fa5, YRSTPRG 0x5118d, TESTPRG 0x52caa (DEBUGPRG 0x1d327 and NETPRG 0x911 also exist). The small overlays load at unknown bases. The overlay registry at 0x35ed98 (count at +0, 12-byte slots from 0x35eda0: name pointer, load base, check word) is the code-derived way to find a base at run time (filled via snDllLoaded 0x15b448). | Header persistence is **confirmed** from the loader (snDllLoaded 0x15b448 and the link routine 0x15ae98 never write +0x00 or +0x2c). The base 0xc75000 is **empirical**: observed in PCSX2 for SIMPRG (DOC/ECONOMY.md) and GAMEPRG (DOC/WIDESCREEN.md), not derived from code. SIMPRG and GAMEPRG share heap block 2 (0x305000 bytes), not block 5 (0x218000, too small). The registry layout is from the loader (read) and DOC/SNR2_FORMAT.md. |

### Pointer chains and stability

| Entry | Chain | valid_when | stable_across |
|---|---|---|---|
| ScheEuro_ptr 0x390650 (pointee heap) | The static word holds the CScheEuro object address. | Non-zero from CreateScheEuro (store at 0x202b50) until DeleteScheEuro (store at 0x202bdc). 0 at boot, logo, title, and after Sche.Finalize in the career, VS and demo sequences. | The static address is fixed in the PAL executable and is written only at create and delete. The heap object address changes between sessions, so re-read it after any 0 to non-zero change. |
| ScheEuro_vtable | [0x390650] -> +0x08 (u32). Career test: ptr != 0 and u32[ptr+8] == 0x406c78. Opening-playoffs test: 0x406b98. VS or demo test: 0x406ab8. | Only while [0x390650] != 0. | Written once at creation and never changed while the object lives. The constants are fixed PAL addresses. The object address is not fixed. |
| PlGiTask_ptr 0x3906d8 (pointee) | The static word holds the task pointer. It is 0 or equal to [0x390784]. The object is the 0x32668-byte heap block 6 buffer in the slot at 0x390784. | Non-zero from plGi_Create to plGi_Delete, that is Sche.MatchStart to Sche.MatchEnd of a match scheduled that day (career and opening playoffs). VS and demo presence is unverified. | The address 0x3906d8 is fixed and written only at create and delete. Its value, when non-zero, is the same constant address for the whole boot, because [0x390784] is allocated once by Pwk.Create and not freed in play. After plGi_Delete the data stays readable through [0x390784]. Cheap and safe: dereference [0x390784] for stale data, 0x3906d8 for "match exists". |
| Pwork general block: last save point | [0x3909a8] -> pwork; base = u32[pwork+0x1c]; block0_off = u32[pwork+0x28]; byte at base + block0_off + 0x298. | After Pwk.Create (PwkCallbackCommand_Create 0x110498, the first script command at RootMainSeq 0x0010), which is non-zero from boot, so the chain resolves on the title screen too (contents blank until New Game or Continue). Guard on pwork+0x18 == 0 (it stays 0 in retail), [pwork+0x1c] non-zero and block0_off != 0xffffffff. Byte 0 = no save or load yet. | Pwork is created once per boot (Pwk.Delete is unreachable), so pwork, base and the block offsets are constant for the whole boot: New Game, Continue, saves, demo, matches and return to title do not reallocate or reshuffle them. Whether the shuffled offsets are the same on every boot is unresolved (the generator state 0x569dc0 starts at 0x12345678 but other draws were not enumerated), so do not hard-code the offset across boots. The byte changes only on a Save (argument not 5) or a career load. |
| Module activity table | Fixed array at 0x5698d0, slot = 0x5698d0 + 4*id. | Slot non-zero from Module.Start to Module.Delete. | Static .bss address, constant. Slot values are heap controller pointers that change each start. |
| TopBar mode type | [0x39f6c4] -> CTopBarTask; word at task+0x1ee0 (CTopBar+0x1ec8 with CTopBar at task+0x18). | Only while [0x39f6c4] != 0 (CreateTopBarTask 0x2ab468, store at 0x2ab498, has run and DeleteTopBarTask 0x2ab4d8, clears at 0x2ab508 and 0x2ab658, has not). | The pointer cell is fixed. The task is a 0x1ef0-byte heap object whose address can change each time it is created. The word changes when a script runs TopBar.SetModeType or the Save module calls SetModeType, never per frame, and is not saved. |
| Overlay identity | No chain: fixed base 0xc75000 assumed for SIMPRG and GAMEPRG (observation only). | Only while SIMPRG or GAMEPRG is fully loaded and linked. Invalid during load and unload. | The size field is constant per overlay and never rewritten by the loader. The base is observed stable only in the two PCSX2 sessions the docs record. The overlays are unloaded and reloaded around the match (FileRsrc.Delete/Entry in RootMatchSeq), so stale bytes of the previous overlay can remain; reads during a transfer may see partial data. |

The static entries (0x34d43c, 0x34d440, 0x34d474, 0x34d428, 0x34d42c,
0x34d438, 0x35c9ac, 0x390784, the module table) are fixed words in the
executable's static data with no chain. They are valid in every mode
and stable across frames, screens, loads and seasons, apart from the
writes described in the table.

### RetroAchievements notes

- Gate on session first. Read 0x390650. If it is 0 there is no schedule
  session (boot, logo, title). If it is non-zero, read u32 at ptr+8:
  0x406c78 means a career, 0x406b98 the opening playoffs of a new
  career, 0x406ab8 VS mode or the attract demo. Treat the pointer as a
  heap address and read it fresh each frame.
- Pair the career test with the demo flag. The mode word cannot tell VS
  mode from the demo, and the demo plays AI against AI. Require
  0x34d43c == 0 for any achievement, and treat 0x34d43c == 1 as "demo,
  ignore everything". Whether the flag can stay 1 if the demo is
  cancelled by a button press before script offset 0x0208 was not
  traced, so check it on a real interrupt.
- Match day. Use 0x3906d8 != 0 as "a match-day flow exists" (career or
  opening playoffs) and its 0 to non-zero and non-zero to 0 edges to
  open and close match logic. It covers the pre-match menu through the
  post-match menu, so it does not by itself mean the 3D match is
  running. Pair it with the overlay check (0x2e518e at 0xc7502c) or with
  the module table slot 0x5698e8 (Game, non-zero during the 3D match)
  for the 3D match. Dereference only while it is non-zero.
- Overlay check pitfalls. Require 'SNR2' at 0xc75000 and then compare
  0xc7502c with 0x2f0628 (career and management screens) or 0x2e518e
  (3D match). Debounce over several frames, because both overlays are
  unloaded and reloaded around the match and any other value means a
  transition, a moved base or another overlay. The base is only
  observed, and a modded disc with different REL sizes needs the
  patched sizes. The small overlays cannot be detected this way.
- Live screens. The module activity table at 0x5698d0 + 4*id is the
  best code-derived screen indicator: a non-zero slot means that module
  was started and not yet deleted by its script (Title 0x569984, Load
  0x56998c, Save 0x569990, SimRoot 0x569930, MatchMenu 0x56995c, Game
  0x5698e8). Several slots are non-zero at once, so test the one you
  need.
- Opening playoffs (tutorial). 0x34d440 is a counter, not a mode flag.
  Use it only together with the session pointer (mode word 0x406b98).
  It keeps its last value after the playoffs and is 0 at boot. It is
  not saved, so after a load it holds whatever it last held.
- Career stage after a load. The save-point byte (values 1 to 4) says
  which phase was last saved, not the screen. Do not use it to tell menu
  from match. Walk the chain on every read as a defensive habit and
  check pwork+0x18 == 0.
- First title. 0x34d474 is 1 from boot until the first Title module
  ends, then 0 for the session. Use it only to ignore the boot, logo
  and opening-movie period.
- Developer flags. Require 0x34d428 and 0x34d42c to be 0 (test
  non-zero for 0x34d428, since other values may mean other things), and
  0x34d438 to be 0. 0x34d438 is 1 only while the developer launcher
  runs, so it is not a "patched disc" marker. 0x34d428 and 0x34d42c
  both make the match check return 1, so check both. These words carry
  no game-state information and catch only a debug flag set by a cheat
  or developer.
- Do not use 0x35c9ac (always 0, nothing reads it) or the TopBar mode
  word (sticky, and also written by the Save module) as mode
  indicators. If the TopBar word is used as a hint, read [0x39f6c4]
  each frame and treat 0 as "no top bar".
- Japanese release. None of these addresses was checked through
  gamever.py. The pwork global there is at 0x38c948 (DOC/
  JAPANESE_RELEASE.md), so no address of this section can be assumed
  shared. Add them to `ADDRESSES` in `gamever.py` before using them on
  SLPM-66316.

### Unconfirmed

| Finding | Verdicts | Reason |
|---|---|---|
| The CFcEuro_Module+0x188 module id read through the fixed chain [0x35c9a8] -> +0x1c -> +0x20 -> +0x188 as a "current screen" indicator | The field is real (GetId 0x10edc0, SetId 0x10edc8, a 4-byte word at +0x188), but the chain always reads 1 (the root Dummy module). | It does not follow the screen. Use the module activity table at 0x5698d0 instead. |
| Meanings of the TopBar eMODE_TYPE values 0, 2, 3 and 4 | Inferred from script and SAVEPRG call sites only. | No code names the values and the initial value was not read. |
| Whether the PlGiTask exists in the attract demo and in VS matches | Not traced. | RootDemoMatchSeq calls Sche.MatchStart at 0x118, but initializeTodayMatch is guarded by getTodayMatchNum(1) (0x113a6c), and what EntryDemoMatch and SetDemoMatchCurrent make it return was not read. |
| The id-to-screen meaning of module ids other than those named in the table row | Ids 70, 171, 172 and 173 (a wild-card id in RootEventSeq 0x208 and the launcher's second Game id) were not resolved. | Retail match uses id 6. |

The companion TurnSkipType word at 0x34d470 (holds 1) appears only in
the turn-skip row above. Its use by scripts beyond the check at 0x108b98
was not otherwise verified.

### Still unknown

- Which memory holds the live module id of the foreground screen beyond
  the activity table. Module.Start creates a heap
  CFcEuro_ModuleController per screen and only the script's m3[] handle
  variables point at it. Walking the CSbTaskManager (instance pointer
  at 0x35ce04, +4 root task, +8 current task) to the module task and
  reading +0x188 is plausible, but the child-link layout of CSbTask
  (EntryTask 0x11d088, LinkOut 0x11d038) was not traced.
- Whether the SeqController's m3[] array is at a static or
  root-reachable address.
- Whether the 3D match has its own pause flag. None was found in the
  executable (the Pause symbols are only audio, ADX and cse). It would
  be inside GAMEPRG (fb::MatchManager, export
  _Q22fb12MatchManager$_instance at GAMEPRG 0x249100) and so depends on
  the overlay base.
- Whether the pointer at 0x3906d8 is non-zero during the pre-match
  MatchMenu. By the create and delete sites it should be (MatchStart to
  MatchEnd), but it was not watched.
- Whether VS and demo matches build the PlGiTask through the schedule
  path, or elsewhere in overlays. Callers of plGi_Create in overlays
  were not checked.
- Whether a soft reset, the developer launcher or a save-state load
  from another boot leaves a stale non-zero value in 0x390650, 0x3906d8
  or the BPDATA pointers.
- The meaning of every CTopBar eMODE_TYPE value and whether the TopBar
  task (0x39f6c4) exists in all screens.
- The Save argument values that map to the save-point byte (1 to 4, and
  5 meaning "do not update") are matched by number to the Load result in
  GAME_FLOW.md (empirical). The Option-module save as value 1 is
  assumed. The value before any save in a new career is unchecked.
- Where the Title module keeps its phase (0 to 8, jump table 0x4c030)
  and the SideMenu result (which sub-screen of the career main menu is
  open). Both live inside MOVIEPRG or SIMPRG objects at unknown runtime
  addresses. The phase field sits at object+0x1a4 to +0x1bc of the Title
  module object.
- The tutorial help state (WP::CTutorialHelpManager, Effective/SetDirect,
  preset-seen flags saved via SearchSaveData 0x295150) was not followed
  to concrete addresses. The singleton pointer lives behind
  GetInstancePtrHelpManager 0x294408.
- The true load address of each overlay (heap block table at 0x35dae8:
  handle, size, buffer; CFcEuro_FileResource +0x124 state, buffer
  pointer) and the exact base of heap block 2. 0xc75000 was observed
  only in PCSX2. The runtime bases of the small overlays (MOVIEPRG,
  SAVEPRG, CEDITPRG, VSPRG, YRSTPRG, TESTPRG) are unknown.
- Whether any overlay writes the developer flags (0x34d428, 0x34d42c)
  or sets MovieFlag back to 1, and whether a flag set from a debug path
  survives a state load.
- Whether a demo cancelled by a button press resets 0x34d43c to 0, and
  whether CScheEuro is finalised on that path.
- Whether the shuffled Pwork block offsets are identical on every boot
  of the same build.
- The remaining game-flow variables of Sche (current year, month and
  turn, game-over status, Sche.YearEnd result) are in Pwork block 0
  (+0x88 PlDate) and CScheEuro state. The layout of Pwork block 0 beyond
  +0x88 and +0x298 belongs to the calendar and economy domains.
- Gap: no confirmed variable says whether the career main menu or one
  of its sub-screens (SideMenu) is open, nor whether a loading screen is
  in progress, other than the module activity table slots above.

### Checking the claims

```bash
# the schedule session pointer: store at 0x202b50 (sw $s0,0x650($s1)), vtable stores at 0x202b40 and 0x202b4c
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x202b30 14
# the match-day pointer: plGi_Create stores 0x3906d8 at 0x210920, plGi_Delete clears it at 0x210954
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Delete
# GetGameTime reads buffer + 0x18000 + 0x7540 = +0x1f540; GetGameScore reads u32[u32[obj+4*side]+0xa8]
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x33c390 6
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x2140a0 12
# the demo flag has a single writer (sw $a0,-0x2bc4 at 0x109394 is 0x34d43c)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x109390 4
# the module activity table store (0x10b2d8) and clear (0x10b684), base lui 0x57 / -0x6730
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x10b2c8 8
# the Save module also calls WP::CTopBar::SetModeType (0x2abba0): mode 4 at 0x045498, mode 0 at 0x0455b4
python SRC/snr2.py xref ISO/DLL/SAVEPRG.REL SetModeType__Q22WP7CTopBarQ32WP7CTopBar10eMODE_TYPEPCc
python SRC/snr2.py dis ISO/DLL/SAVEPRG.REL 0x45490 6 --sles ISO/SLES_541.51
```

## Non-career modes and guards

This part of memory holds the indicators that tell a normal career
apart from everything else: the title screen, the attract demo, VS
mode, the opening playoffs, the developer launcher and its test
modules, and the developer words (skip flags and similar). All
addresses are EE addresses in the PAL release (`SLES_541.51`). Everything
was read from the game code and the scripts; nothing was run in PCSX2.
The most useful indicator is the module activity table at 0x5698d0.

Labels in "How known": **confirmed** means the address and meaning were
read from the disassembly (the function or script offset is given).
**empirical** means the claim is consistent with all the code that was
read but a search for other writers or readers was not exhaustive.
Overlay offsets (SIMPRG, MOVIEPRG) are file-relative.

Which test separates which mode (all PAL, all static analysis):

| Mode | How to recognise it |
|---|---|
| Attract demo | u32 at 0x34d43c is 1 |
| Developer launcher or test module | u32 at 0x34d438 is 1, or a slot in the launcher ranges of the module table is nonzero |
| VS mode | u32[*(0x390650) + 8] is 0x406ab8 and 0x34d43c is 0 |
| Opening playoffs (new game) | u32[*(0x390650) + 8] is 0x406b98 |
| Career, regular schedule | u32[*(0x390650) + 8] is 0x406c78 |
| Match in progress (any mode) | module slot 6 at 0x5698e8 is nonzero (also in VS and in the demo) |

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x5698d0 + 4*id | 4 | u32 pointer to the module controller, 0 = not running | static | Module activity table | One slot per module id (0..173). Module.Start (SLES 0x10b198) stores the controller pointer at 0x10b2d8 (table base `lui 0x57` / -0x6730, index id*4); Module.Delete (0x10b5ac) zeroes the slot at 0x10b684 in the same call. Nonzero means started and not yet deleted. Test only zero versus nonzero, never the value. A failed Start (controller 0) leaves 0. Wild card id 70 is stored under the real id it resolves to. Slots: Title(45)=0x569984, Logo(44)=0x569980, Load(47)=0x56998c, Save(48)=0x569990, SimRoot(24)=0x569930, Game(6)=0x5698e8, MatchMenu(35)=0x56995c, VSModeRegulation(58)=0x5699b8, VSModeScheduleTop(60)=0x5699c0, PlayerEdit(63)=0x5699cc, ClubEditMenu(17)=0x569914, EmblemEdit(18)=0x569918, FlagEdit(19)=0x56991c, UniformEdit(20)=0x569920, NewGameInstall(67)=0x5699dc. Module 172 is a second Game id (GAMEPRG), so slot 6 is not the only match slot. In a match SimRoot (24) is deleted (ROOTMATCHSEQ 0x498) before Game (6) starts (0x570), and SimRoot restarts at 0x638. Slot 6 is nonzero in career matches, in VS matches and in the attract demo (the demo also runs RootMatchSeq), so pair it with 0x34d43c and the schedule mode word. Several modules are nonzero at once in a career, so test specific slots. | confirmed (stores read at 0x10b2d8 and 0x10b684; all 15 slot addresses recomputed). The slot stays nonzero until the script's Module.Delete, not until the screen itself ends. The table is .bss (the file-backed part of the ELF ends at 0x5692dc) |
| 0x5699e4 | 4 | u32 pointer, nonzero = running | static | Launcher module slot (id 69) | Nonzero while the developer launcher menu or one of its test modules runs. Only a patched disc starts it (RootLauncherSeq 0x78 starts id 69, 0xc8 deletes it). | confirmed (slot formula, script offsets) |
| 0x5699ec..0x569ad4 | 4 each | u32 pointer, nonzero = running | static | Developer test and viewer module slots (ids 71..129) | The TESTPRG tests and viewers, for example CharacterViewer(104)=0x569a70, AcrobataViewer(107)=0x569a7c, CseViewer(113)=0x569a94, UniformViewer(128)=0x569ad0. Some ids are the same screens as career ones (75, 79, 83, 85..88, 91, 92, 98..100, 102, 105, 109..112, 115, 118, 120, 121, 124); the launcher starts them through its test path (RootLauncherSeq 0x390..0x3c8 computes id = 71 + m4[1]), so any slot here means "not a career". Only RootLauncherSeq.sqb starts them. Slot 70 (0x5699e8) is the wild card and holds nothing: the wild card queues ids 0..69 only (DOC/SNR2_FORMAT.md, "Module 70, the wild card"). | confirmed. A disassembly of 13 root scripts (Main, MainMenu, ClubEdit, Match, YearStart, YearEnd, MonthStart, MonthEnd, Office, ClubHouse, OwnerRoom, VsMode, DemoMatch) finds no literal Module.Start with an id of 70 or more. RootEventSeq starts only id 70 (wild card), at 0x208 |
| 0x569b7c..0x569b84 | 4 each | u32 pointer, nonzero = running | static | Launcher GAMEPRG-branch slots (ids 171..173) | 171 StadiumViewer MK2 = 0x569b7c, 172 Game = 0x569b80, 173 BC TEST = 0x569b84. Nonzero means a developer screen runs. Slot 172 is also a Game id, so check it against the launcher flag before treating it as developer only. In Module.Start ids at or above 0xab index a separate table (-0x2830, id minus 0xab). | confirmed for the addresses. That these ids are reachable only through the launcher's GAMEPRG branch (the script's second path) is empirical. Retail matches use id 6 |
| 0x34d438 | 4 | s32 (0 or 1) | static | Launcher flag | Set to 1 by Dummy.SetLauncherFlag at RootLauncherSeq.sqb 0x0000, back to 0 at label L1 (0x0248). It is 1 while the launcher and its test modules run. Retail value 0 (ELF image value 0). Setter fcEuroDummyCommand_SetLauncherFlag 0x1092b0 (store at 0x1092ec), getter fcEuroDummy_CheckLauncherFlag 0x1092f8. SIMPRG imports the getter (22 xref lines). The setter stores whatever the script passes, but the only users pass 1 and 0. Dummy.CheckLauncher (0x109270) is unrelated: it always writes 1 to its script variable. | confirmed |
| 0x34d43c | 4 | s32 (0 or 1) | static | Attract-demo flag | 1 while the title screen's attract demo match runs, else 0. RootDemoMatchSeq.sqb: Dummy.SetDemoFlag 1 at 0x18 (before SimRoot loads, so loading is covered) and 0 at 0x208 after Module.Delete SimRoot. Only 3 accesses in the executable: setter 0x109394 (store), command check 0x109328, getter 0x1093a8. RootMatchSeq.sqb 0x228 and 0x7d0 use Dummy.CheckDemo. Written twice per demo run. Read nonzero as demo. Not the PlGiTask demo flag (see Unconfirmed). | confirmed |
| 0x390650 | 4 | u32 pointer to a 0x41c-byte CScheEuro heap object (heap block 1), 0 = none | static | Schedule object singleton | Nonzero between a Sche.Initialize* callback and Sche.Finalize (0x113408, which calls DeleteScheEuro 0x202ba8; the clear is at 0x202bdc). CreateScheEuro 0x202a50 stores it at 0x202b50. The mode is picked by the create argument: 0 or any other value = Normal, 1 = FirstPromote, 2 = VS. Callers: Sche.Initialize 0x1132f8 passes 0 (call at 0x113310), InitializeFirstCheck 0x113350 passes 1 (0x113368), InitializeContinue 0x1133b0 passes 0 (0x1133c8), Initialize_VsMode 0x1145e0 passes 2 (0x114604). The word at object+8 is not a small number. It is a pointer to one of three constant tables, stored at 0x202b4c: 0x406c78 (Normal), 0x406b98 (FirstPromote, the scripted opening playoffs), 0x406ab8 (VS). The word at object+0x20 (store at 0x202b40) holds a second set: 0x406c28, 0x406b48, 0x406a68. Both are valid keys. Use one set consistently. The title attract demo creates the VS-mode object (RootDemoMatchSeq 0xa8 Sche.Initialize_VsMode until Sche.Finalize at 0x1d0), so P nonzero does not separate the demo or VS mode from a career: test the mode word and 0x34d43c. A new game fires the pointer twice (opening playoffs in mode FirstPromote, Finalize, then Initialize in Normal mode). Zero at boot, logo, title while idle, Load, and club creation outside the opening playoffs. | confirmed (CreateScheEuro and the four callers read). Zero at boot is assumed from .bss |
| 0x34d428 | 4 | s32, 1 = active | static | Developer turn skip | Dummy.CheckTurnSkip (0x108b00) tests it against exactly 1. CheckMatchSkip (0x108c90) also takes its skip path when it is 1 (the OR branch at 0x108cb4). CheckYearMonthTurnSkip (0x108b78) reports 1 only when it is 1 and the word at 0x34d470 is 0. Other readers: the getter fcEuroDummy_CheckTurnSkip (0x108e98, load at 0x108ea0) and Dummy CallExecute (0x107fd8, load at 0x1080c0, which seeds a menu field at +0x19c). The executable never stores to it. Retail value 0 (ELF image value 0). Since 0x34d470 is 1 on the disc, the year and month skip never fires even with 0x34d428 set. | confirmed for address, readers and exact-1 tests. "never stored" is empirical (a scan of the executable; overlays read it through the getter and could write it only through a setter, and none exists) |
| 0x34d42c | 4 | s32 | static | Match skip state | A gameplay variable, not a developer flag. The setter fcEuroDummy_SetMatchSkip (0x1094c0, store at 0x1094c8) is called only from SIMPRG (the match-flow state machine): with 1 at SIMPRG 0x1d0c0, right after a virtual call on the object at +0x194 returns 3 (bne at 0x1d0b8), and with 0 at SIMPRG 0x1d110 and 0x1bf04. So it is 1 while a match is being skipped and 0 otherwise (0 at boot, ELF image value 0). While it is 1, CheckMatchSkip (0x108c90) reports 1 and runs execOneMatch through 0x108c00 instead of the 3D match, so the Game module (6) does not start (DOC/GAME_FLOW.md). Which menu choice returns 3 was not traced. Do not use it as a tamper test: it is 1 in ordinary play. | confirmed for the setter, the three SIMPRG call sites and the CheckMatchSkip reaction. The menu choice that returns 3 is not traced |
| 0x34d430 | 4 | s32, 1 = active | static | Developer first-match skip | CheckFirstMatchSkip (0x108d20, load at 0x108d28) tests it against 1. ROOTCLUBEDITSEQ 0x868 calls it right before TutorialHelp 0x8b0 and Sche.InitializeFirstCheck 0x8c0, so it skips the opening playoffs (DOC/SQB_FORMAT.md). Retail value 0, no stores in the executable. | confirmed for address and reader. The opening-playoffs effect is empirical (script order and DOC/SQB_FORMAT.md) |
| 0x34d434 | 4 | s32, 1 = active | static | Developer club-edit skip | CheckClubEditSkip (0x108d98, load at 0x108dac): when 1, runs pwkLg_Init(0) and ScheCallback_ProcPromotion (0x1131c8), then reports 1. The LMASTER skip-tutorial patch sets it (patch_disc.py SKIP_FLAG, file offset 0x24e434 = 0x34d434 - 0x100000 + 0x1000) and also rewrites ROOTMAINSEQ.SQB 0x6d8 and ROOTYEARSTARTSEQ.SQB 0x30 from command 89 to 88, so club creation and year starts still run. Expect 1 on discs built with that switch. Retail value 0, no stores in the executable. | confirmed |
| 0x34d474 | 4 | s32 (0 or 1) | static | Title movie flag | 1 from boot (ELF image value 1) until the Title module's destructor (MOVIEPRG.REL 0x1820) calls fcEuroDummy_SetMovieFlag(0). It is a one-way latch: it only says "the title was not yet left since boot". While 1, the Title constructor (MOVIEPRG.REL 0x1640) picks phase row 0 {0,5,-1,-1} of the table at MOVIEPRG.REL 0x4c0c8, otherwise row 1 {4,0,5,-1}. Set fcEuroDummy_SetMovieFlag 0x1094d0 (store 0x1094d8), get 0x1094e0. | confirmed. MOVIEPRG.REL 0x1820 is the only SetMovieFlag caller among MOVIEPRG, SIMPRG, GAMEPRG, SAVEPRG, VSPRG and TESTPRG; CEDITPRG and YRSTPRG were not checked |
| 0x34d478 / 0x34d47c | 4 each | u32 team ids | static | Attract-demo club pair | The two clubs the demo plays. ScheCallbackCommand_EntryDemoMatch (0x114870) writes them at 0x1148f8 and 0x1148fc from the 50-row, 8-byte table at 0x35c9b8 (`lui 0x36` / -0x3648), row = GetGlobalCounterGameSystem mod 50. Image values 3 and 4. They keep the last demo's clubs afterwards, so they are stale outside the demo. | confirmed; no other code in the executable touches them (overlays not scanned) |
| 0x34d480 | 4 | s32 (0 or 1) | static | Fixed-pair developer flag | Read only at demo entry (0x11488c, compared with 1 at 0x114894). When 1 the stored pair at 0x34d478 and 0x34d47c is used instead of the table. Retail value 0. | confirmed |
| 0x35d4a0 | 4 | u32 counter | static | Global game-system frame counter | Incremented once per call of etc::ExecuteUpdateGameSystem (0x149b40, lw/addiu/sw at 0x149b48..0x149b58); the only call site is the main loop at 0x14eee4. Zeroed by InitializeGameSystem (0x14974c, single caller at 0x14ee20 in main), so it resets only at boot or soft reset. Also seeds the demo pair (mod 50). Wraps at 2^32. It keeps ticking in menus and is not a match clock. GetGlobalCounterGameSystem (0x14a448) is a reader. | confirmed. One loop iteration per video frame is not proven |

### Pointer chains and stability

Static entries have no pointer chain: they are fixed words in the
executable's data or .bss, read directly. The only heap-linked entry in
the table is the schedule object.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| Module activity table | None. u32 at 0x5698d0 + 4*id. | Nonzero from the store at 0x10b2d8 (after fcEuroModule_Entry returns a controller) until Module.Delete zeroes it at 0x10b684 in that same call. The delete wait counter at 0x34dad8 runs after the slot is already 0, so it does not keep the slot nonzero. A slot may also be 0 for a Delete of an id that never started. | Fixed .bss address across frames, screens, loads, seasons. The value changes with every Module.Start, so detect transitions by zero versus nonzero. Zero at boot. A PCSX2 save state restores it with RAM. Not valid on the Japanese build without a gamever lookup. |
| Launcher slot 0x5699e4 | None. | Nonzero from Module.Start k69 (RootLauncherSeq.sqb 0x78) until its Module.Delete. Only on a disc with RootMainSeq.sqb 0x98 patched (patch_disc.py --launcher, LMASTER test-tools group). | Fixed address. On retail and on LMASTER editions without test-tools it stays 0 all session. Only zero versus nonzero is stable. |
| Test and viewer slots 0x5699ec..0x569ad4, 0x569b7c..0x569b84 | None. | Nonzero from Module.Start m3[1] (RootLauncherSeq.sqb 0x3c8 and 0x620) until Module.Delete. Only on a launcher-enabled disc. The slot is zeroed only when a script runs Module.Delete, not when the module ends on its own. | Fixed address. The nonzero value is a heap pointer, so never compare it with a constant. |
| Launcher flag 0x34d438 | None. | Nonzero only between RootLauncherSeq.sqb 0x0000 and 0x0248 on a launcher-enabled disc. | Fixed address, not stored in saves, not moved by overlay loads. Written only at launcher entry and exit. |
| Attract-demo flag 0x34d43c | None. | 1 from RootDemoMatchSeq.sqb 0x18 to 0x208, otherwise 0. | Fixed for the whole session. Written twice per demo run. Not saved. A soft reset returns it to 0. A save state restores whatever it held. |
| Schedule singleton 0x390650 | Root: u32 P at 0x390650. Object is the 0x41c-byte heap CScheEuro. Mode word u32[P+8] (second set at u32[P+0x20]). | Between CreateScheEuro (0x202a50) and DeleteScheEuro (0x202ba8). Test P != 0 and 0x100000 <= P < 0x2000000. P != 0 also holds in the attract demo (VS mode object) and in the opening playoffs. | The slot is written only by Create and Delete, so it is stable within a session. P itself changes on every create, so re-read 0x390650 each time. The mode constants are fixed addresses in the executable. Slot address is PAL fixed. |
| Skip flags 0x34d428, 0x34d430, 0x34d434 | None. | Always. Compare with exactly 1, not just nonzero. CheckYearMonthTurnSkip also needs 0x34d470 == 0. | Fixed static .data words with no stores in the executable. Not saved. Change only by disc patch or cheat. |
| Match skip state 0x34d42c | None. | Written at run time by SIMPRG: 1 at SIMPRG 0x1d0c0 (menu result 3), 0 at 0x1d110 and 0x1bf04. | Fixed address, 0 at boot. A normal gameplay variable, so it changes during a career. A save state restores whatever it held. |
| Title movie flag 0x34d474 | None. | Readable always; meaningful only as a boot latch. 1 until the Title module is first destroyed, then 0 until reset. | Fixed. A PCSX2 save state can set it back to 1 or 0. Not part of the save game. |
| Demo pair and fixed-pair flag 0x34d478, 0x34d47c, 0x34d480 | None. | Pair meaningful only while 0x34d43c is 1. Flag is read only at demo entry and is 0 in retail. | Fixed static addresses. The pair is rewritten once per attract loop and otherwise left alone, so it goes stale. |
| Frame counter 0x35d4a0 | None. | Valid from InitializeGameSystem at boot, in every mode the main loop runs. | Not reset on mode changes (the outer re-entry at 0x14ee40 does not re-init). A state load can make it jump backwards. |

### RetroAchievements notes

- Read the module table with a fixed address and a zero test. For a
  given slot, `read u32 at 0x5698d0 + 4*id != 0` is "module started".
  Never compare the pointer to a value, because it changes on every
  start and a heap pointer is not an id.
- Title: slot 45 at 0x569984. Match: slot 6 at 0x5698e8, but also check
  slot 172 (0x569b80), the second Game id. Slot 6 is nonzero in career
  matches, VS matches and the attract demo alike. A career-match test is
  slot 6 != 0, and 0x34d43c == 0, and the mode word u32[*(0x390650)+8]
  != 0x406ab8 (not VS). Matches of the opening playoffs (mode word
  0x406b98) also pass that test.
- Demo guard: pause or ignore everything while the u32 at 0x34d43c is
  nonzero. The flag is set before SimRoot loads, so it covers the load
  into the demo too. The demo also creates a VS-mode schedule object,
  so do not use the schedule object to tell the demo from VS mode.
- Developer guard: pause the set when the launcher flag 0x34d438 is
  nonzero, when launcher slot 0x5699e4 is nonzero, or when any slot in
  0x5699ec..0x569ad4 or 0x569b7c..0x569b84 is nonzero. Slot 69 alone
  catches every test module on a patched disc. On retail all of these
  stay 0, so this only fires on a patched disc, and such a disc has
  different bytes in ROOTMAINSEQ.SQB, so a hash-based set would not load
  for it anyway.
- Tamper guard on the skip words: test each of 0x34d428, 0x34d430 and
  0x34d434 for exactly 1. 0x34d434 is intentionally 1 on discs built
  with the LMASTER skip-tutorial switch, so an author must decide
  whether to allow it. Do not include 0x34d42c: it is 1 whenever a
  match is being skipped in normal play. 0x34d428 is 0 in normal play,
  so a 1 there is a developer or cheat value.
- Match skipped: 0x34d42c == 1 means the current match is resolved
  without the 3D match, so module slot 6 stays 0 for it. Achievements
  that need a played match can use it as a "not played" signal.
- Schedule root: read P at 0x390650. P == 0 means no schedule (title,
  menus, Load, launcher). P turning 0 again signals that the schedule
  was finalized. The mode word u32[P+8] is 0x406c78 (regular), 0x406b98
  (opening playoffs) or 0x406ab8 (VS mode or the attract demo). The
  constants are PAL-only.
- Title movie flag: only "title not yet left since boot". Do not use it
  as "at the title". After a save state load it can be 1 or 0.
- Frame counter 0x35d4a0 is a heartbeat and a boot detector (a drop to
  a small value means reset or state load). It is not a match clock and
  it keeps ticking in menus.
- Pitfalls: there is a delay of up to about 4 script ticks between a
  Module.Delete and the following Module.Start in the sequencer, so two
  modules can briefly look absent; read the slot you need, not "any
  slot". Do not hard-code any 0x00c0xxxx..0x00dxxxxx overlay address
  (see Unconfirmed).
- Japanese release: every address here is PAL. `gamever.py` has no
  entries for the module table at 0x5698d0, 0x390650 or the three
  constants 0x406ab8, 0x406b98, 0x406c78.

### Unconfirmed

Do not rely on these.

| Finding | Status | Reason |
|---|---|---|
| Per-object flag CScheEuro+0x40c as a demo indicator | unconfirmed | The VS table's isDemoMode returns it. It is zeroed in the constructor at 0x202d80 and written at 0x206e5c/0x206e60 when isVSMode is nonzero and plEve_IsFlagRuntimeSelectCompe(..., 4) is true. It is a runtime-selected-competition flag, not shown to mean "title attract match". Use 0x34d43c for the demo. |
| Other developer debug words block 0x34d440..0x34d4bc | empirical, partly traced | The accessor mapping is traced except that 0x34d4bc is fcEuroDummy_IsDebugCalcuMethodDraw (0x109608, a debug draw flag, default 0), not an agent event type; 0x34d4ac is the agent-event word (IsAgentEventGenerateDebug 0x1095e0 returns value != -1, GetAgentEventGenerateDebugType 0x1095f8 returns the raw word); and 0x34d468 has a setter, fcEuroDummy_SetDispEventNoDebug (0x109570), with no traced caller. 0x34d470 is read by fcEuroDummy_GetTurnSkipType (0x108ea8). Retail defaults (one verifier): 0x34d448, 0x34d44c, 0x34d454, 0x34d458, 0x34d45c, 0x34d464 = 0; 0x34d460 = 1; 0x34d468, 0x34d46c = -1; 0x34d470 = 1; 0x34d498..0x34d4a4 = 0; 0x34d4a8, 0x34d4ac = -1; 0x34d4bc = 0. What each flag does inside overlays is untraced. 0x34d440 (FirstMatchCount, reset at 0x109468, incremented at 0x109480) and 0x34d450 are state words that change legitimately. 0x34d444 is the cutscene number (read at 0x109310). |
| Player-edit entry check 0x34d488 | empirical | A static 0 word read only by PwkCallbackCommand_CheckPlayerEdit (0x1114e8, lw at 0x11154c). It matters only when the edit-work value from pwkTeam_GetEditWork is -1; then a nonzero value selects the same branch (a1=0) as division 0 or year >= 0x7d8. It is not an "in PlayerEdit" state. The step is Pwk.CheckPlayerEdit in the year-start script (RootYearStartSeq 0x01a0, then CheckActionPlayerData module 68 and event 19 per DOC/GAME_FLOW.md); the debug-variable name is "PlayerEditFlag". Not usable as a trigger because it stays 0 in retail. PlayerEdit is also queued by the wild card (id 63), so slot 0x5699cc can be nonzero in a career. |
| Overlay load base 0xc75000 | empirical | SIMPRG (career) and GAMEPRG (match) were each seen at 0xc75000 in single PCSX2 sessions (DOC/ECONOMY.md line 597, DOC/WIDESCREEN.md line 198). Both overlays share loader row settings (+0x10 = 2, +0x14 = 5) in the 8-row table at 0x34da18 (heap block 2), which makes the same slot plausible, but this is not proven. A static registry probably holds each base: 0x35ed98 (count; +4 = count xor 0x31415926; 12-byte slots from 0x35eda0: name, header = load base, check word), filled by 0x15b288 through snDllLoaded (0x15b448); DOC/SNR2_FORMAT.md says 0x15b288 "probably" registers the module. The registry slot contents were not read at run time. Stability across sessions, builds or mods is untested. The loader at 0x10babc rejects index 8 and above and SetupDll (0x10dd08) calls snDllLoaded (0x15b448). |
| PlPinfo cheat field, PlPinfo + 0x18a (6 bytes) | refuted as a trigger | plCheat_SetPinfoCheat (0x2e9120, called from 0x21b434 and 0x21b608) stores three u16 values at +0x18a, +0x18c, +0x18e, derived through plMisc_AbilLv2Exp (0x215438) from the byte at +0x1c1 and the word at +0x1b0. plCheat_IsPinfoCheat (0x2e9170) checks all three. It has zero callers in the executable and no import in the nine overlays, so it is dead code: nothing reads the field. The PlPinfo base is not established. It has no use for achievements. |

### Still unknown

- Where the Title module's phase (opening movie, title, menu) lives. It
  is inside the heap TITLE_MODULE object; no static pointer to it was
  found. The slot at 0x569984 only says "at the title".
- Whether any static byte tells the title menu choice (New Game,
  Continue, VS) after the menu ends. The result goes to script memory
  m4[1] in the heap sequence controller (0 = demo, 1 = New Game,
  2 = Continue, 3 and up = VS). VS shows up afterwards as the schedule
  mode word and modules 58 and 60.
- Which menu choice makes the virtual call at SIMPRG 0x1d0b8 return 3
  (and so sets 0x34d42c to 1), probably the skip or instant-result
  option.
- Whether cancelling the attract demo with a button press skips the
  SetDemoFlag 0 at RootDemoMatchSeq 0x208 and leaves 0x34d43c at 1, and
  whether CScheEuro is finalized on that path.
- Whether a soft reset, the developer launcher or a save-state load
  from another boot leaves stale nonzero values in 0x390650 or in the
  module table.
- Who writes CScheEuro +0x40c, probably Sche.SetDemoMatchCurrent
  (0x114980), and whether it is a second demo indicator.
- Param::PlGiTask has its own demo flag (SetDemoFlag 0x33c408,
  GetDemoFlag 0x33c438) used by Dummy.CheckMatchMenuIn (0x1093b0), in a
  heap object reached through plGi_Get (0x210960). The pointer chain
  was not resolved.
- Whether the module table at 0x5698d0 has exactly 174 slots and what
  follows it (id 173 gives 0x569b84, so the table ends at 0x569b88 at
  least).
- The exact meaning of the launcher flag 0x34d438 inside SIMPRG (22 call
  sites) was not traced.
- Whether etc::ExecuteUpdateGameSystem (0x149b40) runs once per video
  frame in all modes including inside a match.
- No button-combination cheat codes or hidden debug menus other than the
  launcher were found. A full search of overlay input handlers
  (TITLE_MODULE in MOVIEPRG, the Option module) was not done.
  DEBUGPRG.REL and NETPRG.REL are never loaded by the retail game, per
  DOC/SNR2_FORMAT.md.
- How in-match tutorial help state is stored. CTutorialHelpManager is a
  heap singleton (SLES 0x294330 CreateInstanceHelpManager);
  TutorialHelp.Effective100 and 101 enable it. Its instance pointer
  address was not resolved. The opening-playoffs mode word (0x406b98)
  is the only tutorial-phase indicator.
- Emblem, flag, uniform and club edit modes have module slots (17..20,
  63) but nothing was traced for this purpose; only the slot formula
  was checked.
- Japanese release (SLPM-66316): every constant here is a PAL address,
  and `gamever.py` lacks entries for the module table, 0x390650 and
  the three constants 0x406ab8, 0x406b98 and 0x406c78.
- None of the findings above was observed in PCSX2, so no value has
  been seen changing in a running game.

### Checking the claims

```bash
# match-skip setter: one store to 0x34d42c; the three SIMPRG callers
python SRC/sles_disasm.py ISO/SLES_541.51 dis fcEuroDummy_SetMatchSkip
python SRC/snr2.py xref ISO/DLL/SIMPRG.REL fcEuroDummy_SetMatchSkip__20FC_EURO_DUMMY_MODULEi --sles ISO/SLES_541.51
# the set-to-1 site: virtual call returns 3 (bne at 0x1d0b8), then SetMatchSkip(1)
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0x1d0a8 8 --sles ISO/SLES_541.51
# module table: store at 0x10b2d8 (base -0x6730) and zeroing store at 0x10b684
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x10b2c8 8
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x10b678 6
# CreateScheEuro: 0x41c allocation and the three tables chosen by the mode argument
python SRC/sles_disasm.py ISO/SLES_541.51 dis CreateScheEuro
# the attract demo: SetDemoFlag 1 at 0x18 and 0, Initialize_VsMode at 0xa8, Finalize at 0x1d0
python SRC/sqb.py dis DAT/SEQ/ROOTDEMOMATCHSEQ.SQB
# demo flag store (0x109394) and frame counter increment (0x149b48..0x149b58)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x109390 8
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x149b48 6
```

## Save, load and new game transitions

This part of memory is the career state and the markers around it. The whole career lives in one heap buffer owned by the PlPworkTask object (PAL release, `SLES_541.51`). New game, load and save all work on that same set of blocks: a load decodes the save in place, and a save serialises into a separate buffer. The object is created once at boot, so the buffer address and the block order do not change while the game runs (see "Pointer chains and stability"). The block order is shuffled when the object is built, so an author must resolve a block base through the pointer chain and never hard-code a block address. No static "save in progress" or "load finished" flag was found.

Nothing in this section was run in an emulator by the authors of this section. Every claim comes from reading the PAL executable, `SAVEPRG.REL` and the SQB scripts. The one result seen in the running game is the block chain itself, in the PCSX2 save-state test recorded in `DOC/SAVE_FORMAT.md` (Nexxus's report and save states, 2026-10-27). Block field layouts are in `DOC/SAVE_FORMAT.md`.

Labels: **confirmed** means shown from the game code, with the address that proves it. **empirical** means inferred from names or data and not proven in the code. Unconfirmed material is in its own subsection.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x3909a8 | 4 | u32 pointer to Param::PlPworkTask (0x5c bytes, heap via `__builtin_new`) | static | PlPwork task pointer T (career data root) | Non-zero from boot, on the title screen, in the demo, in VS Mode and in a career. It is not a career indicator. Written only by plPwork_CreatePwork 0x21d628 (store at 0x21d65c) and cleared by plPwork_DeletePwork 0x21d698 (store at 0x21d6c8). The only caller of Create is PwkCallbackCommand_Create 0x110498 (call at 0x1104b8), run once by the script command Pwk.Create at ROOTMAINSEQ 0x0010. The only caller of Delete is PwkCallbackCommand_Delete 0x110540 (call at 0x110570), run by Pwk.Delete at ROOTMAINSEQ 0x1a20, which is unreachable (it sits behind the unconditional branch at 0x1970 back to the title). The contents behind the pointer are blank until New Game or Continue fills them. | **confirmed** from code and the SQB scripts (`python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB`). |
| 0x35c970 | 4 | u32 state word | static | Pwk.Create init latch | Initial value 1. PwkCallbackCommand_Create is a two-phase poll. The first call (word == 1) creates the objects, stores 0 at 0x110500 and returns 2. Later calls take the branch at 0x1104b0 and call pwkOteam_WaitInit 0x24b750. When that returns 1, the delay slot at 0x110518 stores 1 back into the word and the command returns 0 (0x110524). At rest the word reads 1 again, and it reads 0 only while the init poll is pending. It is not a "Create has run" flag; use a non-zero test of 0x3909a8 for that. | **confirmed** from code (0x110498 to 0x110538). |
| [0x3909a8] + 0x1c | 4 | u32 pointer | heap | Career data buffer D | Base of the buffer holding all 11 block slots (ids 0 to 10). Allocated by the PlPworkTask constructor 0x21d6f0 with SetHeapBlock(6) and FcEuroMalloc(total, 16), stored at +0x1c (0x21d850), then cleared with memset (0x21d860). Total size is the u32 at T+0x54 (store at 0x21d82c). The load path (`SAVEPRG.REL` 0x33338 to 0x33360, then 0x32d50) decodes into this buffer in place. Fixed for the whole boot: prepareExtWork 0x21d980 and deleteExtWork 0x21d9e0 have no caller in the executable or in any overlay, so nothing swaps +0x1c. | **confirmed** from code. |
| [0x3909a8] + 0x54 | 4 | u32 | heap | Career buffer total size | Sum of the block sizes from the table at 0x533ac8, each padded to 8 bytes. | **confirmed** (constructor store at 0x21d82c). |
| [0x3909a8] + 0x28 + 4*i, i = 0..10 | 44 | 11 x u32 offsets | heap | Block offset table | Block i base = u32[T+0x1c] + u32[T+0x28+4*i]. The constructor 0x21d6f0 fills ids 0..10, shuffles them with plUty_ShuffleUint8 0x235270 (only call at 0x21d774) and writes offset[id] = running total (aligned to 8) in that order. Sizes including an 8-byte trailer, from the table at 0x533ac8: 0=0x20e50, 1=0x129f0, 2=0x120c8, 3=0x538, 4=0xb0, 5=0xb50d8, 6=0x1cf0, 7=0x4c, 8=0x9, 9=0x10, 10=0x9. Usable size is the table size minus 8 (getSize 0x21d908). The trailer check (headerCheck 0x21db38) result is ignored by get 0x21d928. get(8) returns 0 only when the byte at T+0x19 is set, which never happens in retail (the only Create caller passes 0). pwGet 0x21da50 returns 0 only for i >= 11; for an absent block (offset word 0xffffffff) it returns the base through the delay-slot load at 0x21da7c. Field layouts of the blocks are in `DOC/SAVE_FORMAT.md` (block 0 general, 1 your club, 2 other clubs, 3 league, 4 town, 5 records, 6 calendar, 7 options). | Layout and sizes **confirmed**; the 11 size words were read from the executable at 0x533ac8. Whether the shuffled order is the same on every boot is open (see "Unconfirmed"). |
| [0x3909a8] + 0x18 | 1 | u8 | heap | Extra work area active flag | 0 in retail. Written only by switchExtWork 0x21da20 (store at 0x21da40), which returns 0 without writing while T+0x20 is NULL. The only callers are in `SAVEPRG.REL` (0x33180 and 0x33580). | **confirmed** from code (no caller of prepareExtWork found in the executable or any overlay). |
| block 0 + 0x298, where block 0 = u32[T+0x1c] + u32[T+0x28], T = u32[0x3909a8] | 1 | u8 | heap | Save point | 0 after a new game (pwkGen_Init memsets block 0, 0x20e48 bytes, at 0x244250). Written by _pwkGen_SetSavePoint 0x244b78 (store at 0x244b98), read by pwkGen_GetSavePoint 0x244bb0 (load at 0x244bcc); both reach block 0 through get(0). In the save task, SetSavePoint is called at `SAVEPRG.REL` 0x336b4, before the encode call at 0x336dc. A save task kind of 5 (+0x28) skips the call (beq at 0x336a4). Kinds passed by saves: 1 (Option screen), 2 (after each season, ROOTMAINSEQ 0x1688), 3 (start of the opening playoffs, ROOTCLUBEDITSEQ 0x0800), 4 (club edit, ROOTCLUBEDITSEQ 0x0d90). After a load, GetSavePoint is stored into the load task at +0xc (`SAVEPRG.REL` 0x32f70 and 0x32f78), which is the Load module result (1 main menu, 2 year start, 3 playoffs, 4 club edit). Whether the encode pass includes this byte was not checked. | **confirmed** from code and the SQB scripts for kinds 2 to 4; kind 1 is from `DOC/GAME_FLOW.md`. |
| block 0 + 0x0 | 8 | s64 | heap | Club funds (Sikin) | Signed 64-bit, negative is debt, no 2^31 cap. Set to 0 at new game by pwkGen_SetSikin(0) (0x2444a8, `sd`; the call is at 0x244258 inside pwkGen_Init); read by pwkGen_GetSikin 0x2444e0 (`ld`). Stored unit: plMisc_MoneyRate 0x215660 uses s16 rates at 0x5314e8 = 12, 3, 2, 400, and the stored unit is rate 12, so pounds = stored / 6 and euros = stored / 4 (the pound and euro assignment is empirical, per `DOC/SAVE_FORMAT.md`). | Type, offset and new-game value **confirmed**; the unit is **empirical** for the currency names. |
| block 0 + 0x88 | 16 | PlDate | heap | Career date | Layout from plMisc_SetTurn2Date 0x214698: u16 year at +0 (the first year of the season), u8 season turn at +2 (0 to 95, turn 0 is July), u8 month at +3, u32 at +4 (turn within month, turn & 7), u32 at +8 (that value / 2), u32 at +0xc (that value % 2). Month = ((turn >> 3) + 6) % 12 + 1. pwkGen_Init 0x244220 (called from 0x110a7c in PwkCallbackCommand_NewGame) sets year 0x7d5 (2005), turn 0x5c (92), which is June, and these turns 92 to 95 are the opening playoffs. In the third-league start, the first CScheEuro_Normal updateParamDate (0x207228) calls pwkGen_SetStartYear 0x2442e8 at 0x207254, which sets 2006 turn 0 (July); the first real season therefore starts at 2006 turn 0, so a rule keyed on "2005 turn 92" covers only the pre-playoff window. pwkGen_InitVSDate 0x244328 sets 2005 turn 95 (0x5f); it is called from Sche.Initialize_VsMode at 0x114618, so VS Mode and the title attract demo (which runs Pwk.NewGame and Initialize_VsMode, ROOTDEMOMATCHSEQ 0x88 and 0xa8) overwrite the date in place. A load restores the saved date. | **confirmed** from code. The month and turn arithmetic is from reading SetTurn2Date, not from a running game. |
| 0x35c998 | 4 | u32 state word | static | Pwk.NewGame progress word | Poll state of the Pwk.NewGame command (PwkCallbackCommand_NewGame 0x110a60). The handler returns 2 while running and 0 when done. The first call (word 0) runs the init calls (pwkGen_Init, pwkOteam_RequestInit, pwkTeam_Init, pwkRec_RequestInit, pwkSche_Init, pwkTown_Init, pwkOpt_Init, pwkPrac_Init, pwkSponsor_Initialize and others) and stores 1 at 0x110b10. Later calls OR in mask 0x2 when pwkRec_WaitInit (0x253528) returns 1 and mask 0x4 when pwkOteam_WaitInit (0x24b750) returns 1. When (value & 6) == 6 it stores 0 (0x110b58) and the command returns 0. Values seen: 1, 3, 5 (7 only transiently). 0 means idle or just finished, so it cannot separate never-started from finished. A load does not touch it. The title attract demo also runs Pwk.NewGame (ROOTDEMOMATCHSEQ 0x88), so the word cycles once per demo as well and alone does not mean "new career". | **confirmed** from code. Only this function was read; other writers were not ruled out. |
| 0x390650 | 4 | u32 pointer | static | CScheEuro (season scheduler) pointer | Points to the CScheEuro object (0x41c bytes, heap block 1). Written only by CreateScheEuro 0x202a50 (store at 0x202b50) and cleared by DeleteScheEuro 0x202ba8 (store at 0x202bdc; the only caller is Sche.Finalize 0x113408). Reader GetScheEuro 0x202bf8. Creators: Sche.Initialize 0x1132f8 (new game, mode 0, call at 0x113310), Sche.InitializeFirstCheck 0x113350 (opening playoffs, mode 1, 0x113368), Sche.InitializeContinue 0x1133b0 (after a load, mode 0, 0x1133c8), Sche.Initialize_VsMode 0x1145e0 (mode 2, 0x114604). Non-zero in a career, in the opening playoffs, in VS Mode and in the title attract demo (ROOTDEMOMATCHSEQ 0xa8 to 0x1d0). Zero at boot, logo, the idle title, on the Load screen and during club creation outside the opening playoffs. The pointer is set before the object's own initialisation finishes. Continue script order in ROOTMAINSEQ: Load module (0x8c0 to 0x910), Pwk.RuntimeInitialize (0x978), Sche.InitializeContinue (0xa80 or 0xaf8). The mode can be read from two fields written by CreateScheEuro: u32[S+8] = 0x406c78 (career), 0x406b98 (opening playoffs), 0x406ab8 (VS and demo); and u32[S+0x20] = 0x406c28, 0x406b48, 0x406a68. They are two vtables of the same object; use one set consistently. | **confirmed** from code and the SQB scripts. |
| [0x390650] + 0x408 | 4 | u32 | heap | CScheEuro init mode | The argument given to CScheEuro::initialize (0x203030, store at 0x203050). 1 only when created by Sche.InitializeContinue (a loaded career, arg 1 at 0x1133dc); 0 for Initialize (0x113324), InitializeFirstCheck (0x11337c) and Initialize_VsMode (0x114628). It is transient: isFinishedInitialize 0x203120 clears it to 0 at 0x203204 once the loaded-career initialisation completes. | **confirmed** from code. |
| [0x390650] + 0x418 | 4 | u32 | heap | Date-advance pending flag | Not an initialisation marker. Zeroed in initialize (0x203064), set to 1 at 0x20321c when isFinishedInitialize completes (non-load path included), and set to 1 again at 0x20336c in updateTurnEnd 0x203348 on every turn end. It is cleared to 0 by updateParamDate: CScheEuro_Normal at 0x207260 or 0x20726c (the latter after pwkGen_IncDay 0x2443d0), CScheEuro_VS 0x207590 (clear at 0x2075a4) and CScheEuro_FirstPromote 0x207420 (clear at 0x207434); it is also read by updateYearStart 0x203538. So it toggles during normal play and says nothing about a finished load. | **confirmed** from code at the listed stores. The read sites in the VS and FirstPromote controllers were taken from a second reading, not re-run here. |
| 0x35c960 | 4 | u32 pointer | static | Player database (BPDATA) pointer | LargeMalloc(0x3369f8, 0x40) buffer, stored by PwkCallbackCommand_BpDataReadFile 0x110d50 (store at 0x110d70, then it calls 0x1101c8) and zeroed by PwkCallbackCommand_BpDataFreeFile 0x110db0 (LargeFree, then the store at 0x110de0). The pointer is stored at the start of the asynchronous read; contents are valid only after Pwk.BpDataWaitFile returns. Non-zero from ROOTMAINSEQ 0x0530 (new game and continue) and during the title attract demo (ROOTDEMOMATCHSEQ BpDataReadFile 0x68, WaitFile 0x78, FreeFile 0x1e0). Zero at boot, logo and the idle title. It is also zero during a 3D match (ROOTMATCHSEQ frees it at 0x488 and reads it again at 0x688) and during gaps in New Game club editing (ROOTCLUBEDITSEQ 0x05c0 to 0x0638 and 0x0ea8 to 0x13a0). Other frees are at ROOTMAINSEQ 0x07f0 and 0x1948. | **confirmed** from code and the SQB scripts. |

### Pointer chains and stability

Every chain starts at a static word in `SLES_541.51`. The static roots are 0x3909a8, 0x390650, 0x35c960, 0x35c998 and 0x35c970. They are fixed addresses in the PAL executable.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| Task pointer T | u32 at 0x3909a8 (static) | Non-zero from just after Pwk.Create (ROOTMAINSEQ 0x0010) for the whole boot: logo, title, demo, VS Mode and career. Career data behind it is meaningful only after New Game or Load has filled it. | The static word is fixed. The object address is constant from Pwk.Create to the end of the boot (Pwk.Delete is unreachable): frames, screens, matches, season rollovers, saves, loads, New Game and returning to the title. The object is on the heap, so its address may differ between boots; do not cache it across sessions. |
| Buffer D | T = u32[0x3909a8]; D = u32[T+0x1c] | T != 0 and D != 0, the same span as T. Block contents are meaningful only after New Game or Continue has filled them, so pair with a separate career indicator. | Constant for the boot. New Game, Continue and saves work in place and do not reallocate it. It changes only on an emulator reset or when a save state from a different boot is loaded. |
| Block i base | base_i = u32[T+0x1c] + u32[T+0x28+4*i], i = 0..10 | T != 0, D != 0, and the sum lies in 0x00100000 to 0x01FFFFFF. | The offsets are set once in the constructor, so they do not change on New Game or Load. Whether the shuffle gives the same offsets on every boot is open (see "Unconfirmed"), so re-read the chain rather than hard-code it. |
| Block 0 + 0x298 (save point), + 0x0 (funds), + 0x88 (date) | block 0 = u32[T+0x1c] + u32[T+0x28]; then + 0x298, + 0x0 or + 0x88 | The chain above, in a career (new or loaded). The new-game date (2005 turn 92) and funds (0) hold only until the first date advance or payment. | The save point changes only on a save (SetSavePoint at the start of the save task), a load (restored) and a new game (cleared to 0). The date changes at every turn advance, funds on payments. |
| Scheduler object | u32[0x390650] (static), fields +0x408 and +0x418 | Pointer non-zero while a scheduler object exists: opening playoffs, a career, VS Mode, the title attract demo. +0x408 == 1 only inside the load-time initialisation window. | The pointer value (heap) changes each time the object is recreated and is zeroed at each Sche.Finalize (end of the opening playoffs, return to the title, end of a VS or demo match). It persists across menus, matches and season rollover while the career runs. New Game creates it twice (FirstCheck, Finalize, then Initialize). |
| BPDATA buffer | u32[0x35c960] (static) | Non-zero from ROOTMAINSEQ 0x0530 (after the read wait completes) in a career, and during the demo. Zero during a 3D match and in the club-editing gaps listed above. | Address 0x35c960 fixed. The pointer value changes on each ReadFile (session entry, the New Game club-edit re-reads, and after every 3D match), so debounce it. |

On the Japanese release resolve each root through `gamever.py`; the Japanese build also differs in save constants (version 0x68, CRC 0x16da, key string at 0x53f28 per `DOC/SAVE_FORMAT.md`). The pwork global there is a different address (`DOC/JAPANESE_RELEASE.md`).

### RetroAchievements notes

All advice below follows from the code reading above; none of it was tested in an achievement set.

- Resolve block bases through the chain. RetroAchievements needs T = u32[0x3909a8], then u32[T+0x1c], then u32[T+0x28+4*i]. The block base is the sum of two values read from memory, so a plain single offset chain does not express it; it needs a Remember/AddAddress sequence with two AddAddress steps (empirical, not tried). Do not hard-code a block offset: it is shuffled when the object is built.
- Guard the chain. Check T != 0, D != 0 and that the resolved address lies in 0x100000 to 0x1FFFFF. The game never moves T or D after boot, so re-reading every frame is defensive practice, not a requirement.
- Pointer non-zero is not "in a career". 0x3909a8 is non-zero from boot. 0x390650 is non-zero in a career, the opening playoffs, VS Mode and the demo. 0x35c960 is non-zero in a career and the demo (and in VS Mode, except during matches). The word at 0x35c9ac (SetGameMode) is write-only and always 0, so it is no mode flag. A demo discriminator is the demo flag 0x34d43c (set to 1 at ROOTDEMOMATCHSEQ 0x18, cleared at 0x208; writer 0x109394). Pair a pointer test with that flag, and with the mode vtable words of the scheduler (0x406ab8 for VS and demo).
- Detecting a load: the best gate is the scheduler pointer 0x390650 becoming non-zero, then [0x390650]+0x408 == 1. The window is short, so poll every frame, latch "load started" on that frame and re-arm when 0x390650 returns to 0. The load-finished marker is +0x408 going back to 0 (isFinishedInitialize 0x203120 clears it). Do not use +0x418 for this, because it is set again at every turn end. +0x408 reads 0 for the rest of the career, so it cannot tell a loaded career from a new one later.
- Detecting a new career: the 0x35c998 word goes non-zero (1, 3 or 5) and back to 0 while Pwk.NewGame runs. Require the previous frame to be non-zero for the 1/3/5 to 0 edge, because 0 is also the idle value. A load does not touch it. The title attract demo produces the same cycle, so check the demo flag 0x34d43c is 0. A new career also shows year 2005, turn 92, funds 0 and save point 0 in block 0 for a short window; do not use the date or funds alone, because Initialize_VsMode sets 2005 turn 95 and a loaded save can legitimately hold 2005.
- New Game fires the scheduler pointer twice. Sche.InitializeFirstCheck (opening playoffs, from ROOTCLUBEDITSEQ 0x8c0) creates it and Sche.Finalize (0xc70) clears it, then Sche.Initialize creates it again for the career proper. A rule on the first 0-to-non-zero edge fires in the opening playoffs. +0x408 is 0 in both creations of a new game.
- Save point: a 0 to N change is the only usable signal (0 also means "career created, never saved"). It changes at the start of the save task, before the memory-card write finishes, so it is not a "save completed" signal. After the opening playoffs begin a save of kind 3 follows, 2 is the end-of-season save, and 1 or 4 appear on manual or club-edit saves; a value 1 to 4 right after a load says which point was loaded. The per-kind readings of 1 rest on `DOC/GAME_FLOW.md`.
- Avoid half-built data. While 0x35c998 is non-zero a new career is being built, so do not read career blocks. Do not read player data through 0x35c960 on its first non-zero frame: the pointer is stored before the file read finishes. Debounce 0x35c960, which drops to 0 and returns with a different address in New Game club editing and around every 3D match.
- Loads decode in place. A mid-frame read during the load decode (`SAVEPRG.REL` 0x33360, call to 0x32d50) could see half-decoded data, and the decode length in frames was not measured. The scheduler pointer becomes non-zero after the Load module and Pwk.RuntimeInitialize in the Continue script, so by script order the blocks are decoded by then. A save serialises into a separate buffer (`SAVEPRG.REL` 0x336dc, call to 0x32d50) and changes the live blocks only through the save point byte, so reading blocks during the card write is considered safe (empirical).
- Do not use the random seed word 0x569dc0 as a marker (see "Unconfirmed").
- Do not look for a load-task flag or a save key/CRC in RAM: the load task status (+4: 2 done, 3 failed) is on a heap object with no known static pointer.

### Unconfirmed

Do not rely on the following.

| Item | Why it is unconfirmed |
|---|---|
| Random-number state, 0x569dc0 (u32), saved at block 0 + 0x133c (and 0x569dc4 at block 0 + 0x1340) | `_pwkGen_SaveRandomSeed` 0x244be8 copies 0x569dc0 into block 0 + 0x133c and `_pwkGen_LoadRandomSeed` 0x244c30 copies it back (callers `SAVEPRG.REL` 0x336bc on save, 0x33368 on load). fcEuroRand_Init 0x111698 sets 0x569dc0 to 0x12345678, 0x569dc4 to 0x87654321, and points 0x569dcc at a timer-seeded word copied into 0x569dc8. One reading says default draws use the timer-seeded state, another found about 200 call sites that pass 0x569dc0 as the state pointer, so it may advance in play. Not settled. The word may change on a load and during play; do not use it as a marker. |
| Whether the block offsets (and so every block base) are the same on every boot | plUty_ShuffleUint8 0x235270 draws from state 0x569dc0, which starts at the constant 0x12345678, and Pwk.Create is the first script command, so the order may be deterministic. Draws on 0x569dc0 between fcEuroRand_Init (called at 0x112940) and Pwk.Create were not enumerated and no second boot was read. Do not hard-code offsets until a PCSX2 read of u32[T+0x28+4*i] on two boots agrees. |
| Save/load layout metadata (save key "sakatsukue" at `SAVEPRG.REL` 0x536a8, layout CRC 0xa225 from 0x32ce0, version 0x69 at 0x3322c) | These are image offsets of the overlay, not RAM addresses (the load base of `SAVEPRG.REL` is not determined; the registry at 0x35ed98 holds loaded bases). The CRC 0xa225 is not stored in the overlay: 0x32ce0 computes it at run time over getSize(0..9), and the save header at +8 holds it. Only the version 0x69 is an immediate. The only run-time variable is the load task's +4 status on a heap object with no known static root. |
| Blocks 2 and 5 are "still being built" while 0x35c998 is non-zero | Inferred from the names pwkRec and pwkOteam only; which blocks those loaders fill was not traced. |
| Whether the encode/decode pass includes block 0 byte 0x298 | Not checked. |
| Whether the object survives a match (VS_Start, VS_End, Bring_Match_Before/After) | Only the Create and Delete script commands were traced. Both are outside the match scripts, so it is expected to survive. |

### Still unknown

- No static save-in-progress flag was found. The save task (`SAVEPRG.REL`, MC::CFcEuroSave and CSaveModule) is a heap object with state at +4 (0 running, 2 done, 3 failed, from `SAVEPRG.REL` 0x333c0 and 0x33728). Where the Save and Load module objects are kept needs the module manager; the pointer to the running module table is not traced. The module activity table at 0x5698d0 + 4*id (Load id 47 at 0x56998c, Save id 48 at 0x569990) is non-zero from Module.Start until Module.Delete, so it may serve as a save or load screen marker; this was not tested for these screens.
- The save serialiser runs in one step (`SAVEPRG.REL` 0x336dc, call to 0x32d50) and the memory-card write is asynchronous. The number of frames the load decode (0x33360, call to 0x32d50) takes is not measured. The gate that is safe by script order is the 0x390650 pointer becoming non-zero.
- Whether the heap addresses (the PlPwork buffer and the schedule object) are identical on every boot of the same disc and settings is not checked. It depends on allocation order (SetHeapBlock 6 for the PlPwork buffer).
- Save kind 5 (skips SetSavePoint) has no matching script in `DAT/SEQ`; only kinds 1 to 4 were found in SQB Save calls, and kind 1 is in the Option overlay module. Which screen uses kind 5 is open.
- The meaning of CScheEuro +0x404 (a byte set to 3 during init, cleared at 0x2031f8) and the exact condition at which isFinishedInitialize returns 1 are not fully traced. Only the new-versus-load argument at +0x408 is confirmed.
- The plBp_GetBpinfo pointer (0x39066c) is updated by Pwk.RuntimeInitialize (0x110b78 calls updatePlCoreInfoSub on it) right after a load. Its lifetime equals the BPDATA buffer 0x35c960. What the table holds, and whether its values are a better "load finished" marker than the schedule object, was not checked.
- The VS-mode path (Sche.Initialize_VsMode 0x1145e0, Pwk.VS_Start 0x111478 using pwkVs_CreateVsTeamBuffer) was not followed beyond the date and scheduler creation above.
- Where the Load module sits relative to the title's memory-card check (WP::CMemoryCardNewGameCheck, MC::CFcEuroNewGameCheck) was not traced. A blank-card new game goes through NewGameInstall (module 67) before club creation; its runtime flags are unexplored.
- Whether cancelling the attract demo with a button press leaves the demo flag 0x34d43c at 1 and skips Sche.Finalize was not traced.
- Whether the scheduler pointer and BPDATA pointer behave the same on the Japanese release was not checked; `python SRC/gamever.py check ISO_JP` would show whether each address resolves.
- The value of the block 0 offset (u32[T+0x28]) was not read from data.
- Whether the date, funds and save-point values behave as described in a running game was not tested in PCSX2.

### Checking the claims

Run from the repo root. Each command was run and shows the lines named.

```bash
# Pwk.Create: gate on 0x35c970 (0x1104a8), CreatePwork (0x1104b8), clear 0x110500, re-arm 0x110518
python SRC/sles_disasm.py ISO/SLES_541.51 dis PwkCallbackCommand_Create
# Pwk.Create is the first command; Pwk.Delete is behind the title branch (needs DAT/)
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB
# the demo runs Pwk.NewGame (0x88) and Sche.Initialize_VsMode (0xa8)
python SRC/sqb.py dis DAT/SEQ/ROOTDEMOMATCHSEQ.SQB
# Initialize_VsMode: CreateScheEuro(2) at 0x114604, pwkGen_InitVSDate at 0x114618
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x1145e0 20
# pwGet: i >= 11 returns 0; absent block returns the base (delay slot 0x21da7c)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21da50 14
# SetSavePoint writes block 0 + 0x298 (0x244b98); the save task calls it at 0x336b4
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x244b78 12
python SRC/snr2.py dis ISO/DLL/SAVEPRG.REL 0x336a4 20 --sles ISO/SLES_541.51
# CScheEuro +0x418: set at 0x20336c (turn end), cleared at 0x207260 / 0x20726c
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x203348 10
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x207250 8
```

## Rich presence identifiers

This part of memory holds the numbers an author can turn into words
for Rich Presence: which competition you are in, which match is on, who
the opponent is, and whether the demo is running. The game has no single
"current screen" number (the module activity table below is the nearest
thing). Your own club is always team id 1, so the club id itself
carries no text. Most useful values sit behind pointers in the heap, so
read them through the pointer chains below. All addresses are for the
PAL release (`SLES_541.51`). Everything here comes from reading the
code; none of it was seen running in PCSX2 unless a row says so.

| Address | Size | Type | Region | Name | Meaning and values | How known |
|---|---|---|---|---|---|---|
| 0x5eacb0 | 4 | s32 | static | Current match group (schedule UID) | The schedule UID of your match, 0 to 163 (148 to 163 are VS mode). -1 (0xFFFFFFFF) when none. Stored at 0x21dd6c in `plRec_SetMatchRegulationsInGame` (0x21dd38), called from `CScheEuro::initializeOneMatch` (0x203b30). The store happens only when the regulation lookup returns non-null and the vtable test `isNextGameForeground` (slot +0x50/0x54, branch at 0x203b28) is true, that is, your club plays. AI-only matches leave it at -1. Cleared (memset of 0x7c bytes to 0xFF at 0x5eacb0 by `plRec_ClearMatchRegulationsInGame` 0x21de50) from `finalizeOneMatch` (0x203ee4) and `Pwk.NewGame` (0x110adc). It is not cleared on a save load or abnormal exit, so it can be stale. The 0x78-byte regulation row is a copy at 0x5eacb4 (VS rows are at 0x5ead30). | confirmed (store, clear and condition re-read in the code); stale-after-load is by absence of any other clear |
| block1 + 0x4b4 | 18848 (0x49a0) | PlTeamData: u32 team id at +0 (always 1, empirical), s16 hometown city at +4, s32 main league at +0x41f4, u8 club rank 0 to 31 at +0x41f8 | heap | Your club's team record | Your club is team 1 and the rival is team 2, so the id tells you nothing. The club name is user text. Useful fields: city id (+4), main league (+0x41f4, same league index as block 3 +0), club rank (+0x41f8, from `status >> 11` capped at 31 by 0x26dd40, which stores it at block1+0x46ac). Rank only changes when 0x26dd40 runs, so it is not live per frame. The record address comes from `pwkTeam_GetMyTeamData` (0x259898, `get(P,1) + 0x4b4`). Readers: `plTeam_GetCity` 0x22bf78 (`lh` +4 at 0x22bf94), `plTeam_GetTeamMainLeague` 0x22bf00 (`lw` +0x41f4), `pwkOteam_GetRank` 0x24bec8 (`lbu` +0x41f8 at 0x24bee8). | confirmed (offsets and readers re-read); "id always 1" and write timing are empirical |
| 0x34d43c | 4 | s32 flag | static | Demo (attract mode) flag | 1 while the attract-mode demo runs, from `Dummy.SetDemoFlag 1` at script offset 0x18 of `ROOTDEMOMATCHSEQ.SQB` to `SetDemoFlag 0` at 0x208. It covers the demo's loading phase as well. Only `fcEuroDummyCommand_SetDemoFlag` (0x109358, store at 0x109394, address `lui 0x35` / -0x2bc4) writes it; the only reads are at 0x109328 and 0x1093a8 (`CheckDemoFlag`). The sibling launcher flag is at 0x34d438 (store 0x1092ec). | confirmed |
| *0x390650 then +0x414 then +0x28c | 4 | s32 (PLSCHE_COMPE, read as signed) | heap | Competition of your game today | PLSCHE_COMPE (0 to 71) of the competition where your team has a game TODAY, or -1 when there is none. It is not the next future match. `calcMyJoinCompetition` (0x205948) first calls `deleteGameList_MyJoinCompetition` (0x205868, which stores -1 at +0x28c at 0x2058d0 and at +0x290 at 0x2058d8, and 0 at +0x280 and +0x288), then scans today's competition UIDs (`getNowCompetitionUIDList`) in order. The competition chosen is that of the first UID in which your team (`isEntryTeam` team 1, or VS mode via vtable +0x1c) has a game, and only if the matches-today total is positive and the UID is not -1 (0x205a90 to 0x205a98). It then stores +0x280 at 0x205aa8, +0x28c at 0x205ab0 (value from `getScheCompe` 0x206560, which gives -1 for negative ids), +0x290 at 0x205ab8, +0x288 at 0x205acc and +0x298 at 0x205ad4. A second competition on the same day is not reported. Written from `updateTurnStart` (0x2032b8, call `jal` 0x205948) and, on Continue only, from `isFinishedInitialize` (0x203120, call at 0x203198; its body runs only when `u32[S+0x408] != 0`, which is the `initialize(1)` argument of `InitializeContinue`). A New Game therefore gets its first value at the first turn start. Reset again at turn end (0x203368). Sibling fields in the same 0x2a4-byte block: +0x280 matches today inside the chosen competition (sum over its UIDs), +0x288 matches today in the chosen UID, +0x290 the chosen UID, +0x298 number of UIDs of that competition in today's list. +0x29c nation and +0x2a0 division are set once in `initialize` (0x203030, stores at 0x203070 and 0x203080, from `pwkLg_GetMyNati` and `pwkLg_GetMyDiv`). | confirmed (stores, resets and call sites re-read); the root store is 0x202b50 and the clear 0x202bdc |
| 0x3906d8 | 4 | u32 pointer | static | Match-day gate (PlGiTask pointer) | Non-zero from `Sche.MatchStart` (via `CScheEuro::initializeTodayMatch` 0x20373c, only when `getTodayMatchNum(1)` is non-zero) or `Sche.CreateGiForFirstMatch` (0x11451c) until `Sche.MatchEnd` (`deleteGameInterFace` 0x203808) or `DeleteGiForFirstMatch` (0x114540). So it is set across the pre-match menu, the 3D match and the post-match screens, and it is 0 on days with no match. `plGi_Create` (0x2108f0) stores it at 0x210920 and `plGi_Delete` (0x210940) zeroes it at 0x210954. It equals `u32[0x390784]` while non-zero. Whether the title demo creates it is not traced (see Still unknown). | confirmed (callers by `jal` scan); demo behaviour unresolved |
| 0x5698d0 + 4 * module id | 4 | u32 | static | Module activity table | The slot of a module is non-zero from `Module.Start` (store at 0x10b2d8, table base `lui 0x57` / -0x6730, index = id * 4, executes even when the controller is 0) until the script's `Module.Delete` (zero store at 0x10b684). It lasts until the script deletes the module, not until the module's own end. Slot examples: Game (6) 0x5698e8, SimRoot (24) 0x569930, MatchMenu (35) 0x56995c, Logo (44) 0x569980, Title (45) 0x569984, Load (47) 0x56998c, Save (48) 0x569990, Launcher (69) 0x5699e4. The attract demo also runs the Game module, so slot 6 is non-zero in the demo and in VS matches: pair it with 0x34d43c. In the match path SimRoot is deleted before Game starts and restarted after it. | confirmed (store and zero re-read); the slot examples and the match-path order are from the script check and not re-read here |
| 0x35c9ac | 4 | s32 (enum eFcEuroGameMode) | static | Game mode word | Not usable. Only writer is `fcEuroRootTask_SetGameMode` (0x113090, store at 0x113098, address `lui 0x36` / -0x3654), reached from sequencer handler 0x10c2f0 (`jal` at 0x10c324). `ROOTMAINSEQ.SQB` passes literal 0 at script offsets 0x06a0 and 0x08a8. Nothing reads it: `GetGameMode` (0x113080) has no caller in the executable and no overlay imports it. It holds 0 throughout retail play. | confirmed |

### Lookup tables for names

These come from the investigator and from `DOC/` files. The message
categories were not re-checked, so treat them as empirical.

| Id | Where the words are | Range |
|---|---|---|
| Nation id | message category 6, record 5000 + id | 1 England, 2 France, 3 Germany, 4 Italy, 5 Spain, 6 Netherlands |
| Club id | message category 3, record 2000 + id | 3 to 542 have names (ids 1 and 2 are your club and the rival; your club name is user text) |
| Competition id | message category 9, record 10000 + compe (category 100009 holds capitals) | 0 to 71; names in `DOC/SCHEDULE_FORMAT.md` |
| Stage and group name | message category 11, record 1000 + UID | empirical, not matched to UIDs |
| Hometown city | message category 961 | 839 English towns, empirical |

Team id ranges: 1 is your club, 2 to 0x21e are other teams, and 0x21f
to 0x22e (543 to 558) are the 16 VS teams (`SetTeamData` 0x210ab8 tests
`(id minus 0x21f) < 0x10`). The split into clubs (3 to 459) and national teams
(460 to 542) is from `DOC/` only. VS team names are typed by the user.
Only teams 2 to 441 have a record in block 2; clubs 442 to 459 and the
national teams have none.

UID to competition (empirical, the investigator's reading of
`python SRC/schedule.py year DAT/PARAM`, not re-checked): 0 to 0; 1, 2
to 1; 3 to 2; 4, 5 to 3; 6, 7 to 4; 8, 9 to 5; 10 to 6; 11, 12 to 7;
13, 14 to 8; 15, 16 to 9; 17, 18 to 10; 19 to 11; 20, 21 to 12; 22, 23
to 13; 24, 25 to 14; 26, 27 to 15; 28 to 16; 29, 30 to 17; 31 to 18;
32, 33 to 19; 34, 35 to 20; 36, 37 to 21; 38 to 22; 39, 40 to 23; 41,
42 to 24; 43, 44 to 25; 45, 46 to 26; 47 to 27; 48, 49 to 28; 50, 51 to
29; 52, 53 to 30; 54, 55 to 31; 56, 57 to 32; 58 to 33; 59 to 67 to 34;
68 to 76 to 35; 77 to 79 to 36; 80 to 37; 81 to 38; 82 to 39; 83 to 40;
84 to 41; 85 to 42; 86 to 43; 87 to 97 to 44; 98 to 102 to 45; 103 to
113 to 46; 114 to 122 to 47; 123 to 48; 124 to 141 to 49; 142 to 147 to
50 to 55; 148 to 163 to 56 to 71 (VS mode).

### Pointer chains and stability

The career data root is the static word at 0x3909a8. It is non-zero
from boot: `Pwk.Create` is the first real command of `ROOTMAINSEQ.SQB`
(script offset 0x10, callback `PwkCallbackCommand_Create` 0x110498, the
only caller of `plPwork_CreatePwork` 0x21d628 at 0x1104b8, which stores
the pointer at 0x21d65c). `Pwk.Delete` is only at offset 0x1a20, behind
an unconditional branch back to Title (0x1970), so it never runs in
play. New Game (`Pwk.NewGame` 0x110a60) and Load re-initialise the
blocks in place and do not re-create or re-shuffle them. So the root
`P`, the buffer `u32[P+0x1c]` and every block offset are fixed for the
whole boot (empirical from the scripts and call scan; checked that no
overlay references the create or delete functions). A non-zero `P` does
NOT mean a career is loaded: before New Game or Continue the contents
are blank or demo data.

| Entry | Root and offsets | valid_when | stable_across |
|---|---|---|---|
| Your club's team record | `P = u32[0x3909a8]`; `block1 = u32[P+0x1c] + u32[P+0x2c]`; record = block1 + 0x4b4 | Content-based gate only: `u32[block1+0x4b4] == 1` and rank byte (+0x41f8) at most 31, plus the demo flag 0x34d43c at 0. `P != 0` is true from boot and proves nothing. | The whole boot: `P`, `+0x1c` and the block offset do not move on New Game, load, demo or return to title. The contents change. Re-reading the chain each frame (three reads) is defensive practice only. Season changes do not move it. Whether the shuffled offsets are identical on separate boots is unresolved. |
| Competition of your game today | `s = u32[0x390650]`; `d = u32[s+0x414]`; `compe = s32[d+0x28c]` | `s != 0`, `d != 0` and `compe >= 0`. `0x390650` is 0 before `CreateScheEuro` (0x202a50) and after `DeleteScheEuro` (0x202ba8); `+0x414` is 0 during construction. It exists in a career, the opening playoffs, VS mode and the attract demo (the demo builds the VS variant), so gate on 0x34d43c being 0. Meaningful only between turn start and turn end on a day when your team has a game. | Stable within one match day, rewritten once per turn start and reset to -1 at turn end. `d` is a 0x2a4-byte block from heap block 1 and can change on each `CreateScheEuro` (new career, load, VS, demo), so re-read the chain every frame. The root 0x390650 is fixed. Nation (+0x29c) and division (+0x2a0) persist until the object is rebuilt. |

The `CScheEuro` variant can be read from `u32[S+8]` (0x406c78 normal
career, 0x406b98 opening playoffs, 0x406ab8 VS and the attract demo) or
from `u32[S+0x20]` (0x406c28, 0x406b48, 0x406a68). They are two vtables
of the same object, set by `CreateScheEuro` (stores 0x202b4c and
0x202b40). Use one set consistently. Neither is a small enum.

Static entries (no pointer chain): 0x5eacb0 is valid from
`initializeOneMatch` to `finalizeOneMatch` of a match your club plays,
and is a fixed BSS address that never moves between runs; it is stable
across frames, the pre-match menu, the 3D match and extra time, and is
not a per-season value. 0x34d43c is readable at all times, is a fixed
static word, and changes only twice per demo cycle. 0x35c9ac is a fixed
static word that holds 0 throughout retail play.

### RetroAchievements notes

- The block base never moves inside one boot, but the contents are
  blank or demo data before New Game or Continue. Gate career values on
  contents (`u32[block1+0x4b4] == 1`, a sane year or rank), not on
  `P != 0`. Re-resolving the chain each frame is cheap and safe.
- Pair every heap read with a mode check. For the schedule object test
  both pointer hops. Do not hard-code block offsets across boots until
  they are read on two boots (see Still unknown).
- For "a match of mine is on", compare 0x5eacb0 against -1 (as s32 or
  0xFFFFFFFF). An edge from -1 to a value starts a match, and back to -1
  ends it. Pair it with the demo flag at 0x34d43c: the demo plays the
  normal match machinery, so gate on the demo flag being 0 or the title
  demo can look like a career match. Whether 0x5eacb0 itself is set
  during the demo was not verified.
- Stale values: 0x5eacb0 is not cleared on a save load or when you quit
  mid-match. Use previous-frame deltas and do not assume only clean
  transitions happen.
- Map the UID in 0x5eacb0 to a competition with the table above, and
  treat UID 148 to 163 as VS mode. Competition names use category 9 at
  10000 + compe.
- For "what competition is my game today", use the schedule object value
  and require `>= 0`. It is -1 on days without a game and after turn
  end, so it cannot say what your next match is. It reports only the
  first competition of the day in which you play.
- Club rank (+0x41f8) is a derived value and changes only when 0x26dd40
  runs, so use it for bands, not for per-frame progress.
- Do not use 0x35c9ac (game mode) for anything. Do not use the club id:
  it is always 1.
- Rich Presence can look up the club name from the opponent id
  (category 3, 2000 + id) once the team-id chain is trusted, but see
  "Unconfirmed".
- The Japanese release (`SLPM-66316`) was not checked for any address
  here. Translate with `gamever.py` first.

### Unconfirmed

These rows are empirical or partly read from the code. Re-test live
before an achievement depends on any of them.

| Entry | Reading | Why it is not in the table |
|---|---|---|
| Career root block layout at 0x3909a8 | u32 pointer to the `PlPworkTask` (0x5c bytes). There are 11 blocks (k = 0 to 10). `block_k = u32[P+0x1c] + u32[P+0x28+4*k]`, each 8-byte aligned, order shuffled in the constructor (0x21d6f0) by `plUty_ShuffleUint8` (0x235270, only call at 0x21d774). Block sizes (usable, table at 0x533ac8 minus 8): 0 0x20e48, 1 0x129e8, 2 0x120c0, 3 0x530, 4 0xa8, 5 0xb50d0, 6 0x1ce8, 7 0x44. Only block 8 can be absent (offset 0xFFFFFFFF), and only when `u8[P+0x19] != 0`, which never happens in retail. The ext-work swap (`u8[P+0x18]`, `switchExtWork` 0x21da20) is dead in retail: `prepareExtWork` 0x21d980 and `deleteExtWork` 0x21d9e0 have no callers, so `+0x18` stays 0 and `+0x1c` never changes. | The shuffle draws from the generator state at 0x569dc0, set to the constant 0x12345678 by `fcEuroRand_Init` (0x111698), so the offsets may be identical on every boot, but other draws before `Pwk.Create` were not enumerated and no run was observed. |
| Career date at block0 + 0x88 (16 bytes) | u16 year (the season's first year) at +0, u8 turn of season 0 to 95 at +2, u8 month 1 to 12 at +3, u32 turn in month 0 to 7 at +4, u32 +8 = turn in month / 2, u32 +0xc = parity. Month = ((turn/8)+6)%12+1, so turn 0 is July (`plMisc_SetTurn2Date` 0x214698). Keika (`pwkGen_Keika` 0x244430) is year minus 2006. The date changes in `pwkGen_IncDay` (0x2443d0). Chain: `block0 = u32[P+0x1c] + u32[P+0x28]`. A New Game starts at 2005 turn 92 (`pwkGen_Init` 0x244220, date helper 0x2441c8). The opening playoffs run 2005 turns 92 to 95, and the first real season is 2006 turn 0: `pwkGen_SetStartYear` (0x2442e8) writes 2006 turn 0, called from the Normal sub-controller handler 0x207228. `pwkGen_InitVSDate` (0x244328) writes 2005 turn 95 and is called from `Sche.Initialize_VsMode` (0x114618). | Read in the code, but the block is blank before New Game or Continue, so gate on a sane year. The "Sche.TurnStart" writer was not verified. `DOC/SAVE_FORMAT.md` names a "2005-06" career at turn 81 on an LMASTER test build: that is a mod question, not retail. |
| Your league and competition at block3 + 0 and + 4 | `block3 = u32[P+0x1c] + u32[P+0x28+12]`. +0 is the league index (England 0, France 1, Germany 2, Italy 3, Spain 4, Netherlands 5), written only by `pwkLg_Init` (0x246218), so it does not change at promotion, relegation or year end. +4 is the competition of the division you play in, set to the division-1 competition at start and changed only within the same league by `pwkLg_SetMyCompe` (0x2462e0). Table at 0x531d40 (stride 0x10): {nation, league, compe div 0, compe div 1} = (1,0,0,1), (2,1,6,7), (3,2,11,12), (4,3,16,17), (5,4,22,23), (6,5,27,28). | No caller of `pwkLg_SetMyCompe` was found, so what changes +4 and when is unproven. A block that is still blank reads as league 0, which looks like England, so gate on a career flag. |
| Home and away team ids (PlGiTask) | The PlGiTask buffer is a heap object in block 6, allocated once by `bufer_alloc` (0x210070) from `Pwk.Create` and held at 0x390784 for the whole boot; 0x3906d8 equals it only between create and delete. Direct form (confirmed, `0x210198` builds `0x10000 \| 0xfba0`): home id `u32[buf + 0x1fba0]`, away id `u32[buf + 0x24540]`, stride 0x49a0 (backups at +0x28ee0 and +0x2d880). Read via `u32[0x390784]`, since the accessors read that word and the ids stay readable after `plGi_Delete` until the next `plGi_Create`. An older chain form (`A = u32[g+0]`, `S = u32[A+4*side]`, `T = u32[S+0]`, `id = u32[T+0]`) agrees with this only if its base is the same buffer. | Which side is home is empirical (side 0), not decoded (`GetOperator(PlHomeAway)` was not read). The ids are rewritten on every `initializeOneMatch`, so latch them when the match with id 1 starts. Do not use 0x5eacb0 as an existence flag for the controller. Club and national ranges come from `DOC/` only. |
| Match group, period and competition in PlGiTask | UID (group) u32 at buf+0x1f480, a copy of it at +0x1f924, competition s32 (0 to 71 or -1) at +0x1f920, period s32 at +0x1f488 (sign-extended from a signed byte), turn counter u32 at +0x1f474 (copy at +0x1f484). Set by `initializeOneMatch` (`SetMyGroup` at 0x203b3c, `SetMyPeriod` at 0x203b50). Demo flag at buf+0x1f544 (written at 0x203d98 from vtable +0x24 `isDemoMode`) and VS flag at buf+0x1f548 (written at 0x203d7c from vtable +0x1c `isVSMode`), both cleared at 0x210ff0 and 0x210ff4. `isVSMode` returns 1 only for the VS variant; `isDemoMode` returns 0, 0 and `u32[CScheEuro+0x40c]` for VS (0x33b8e8). `GAMEPRG.REL` passes group and period to `Msg::GetPeriodNameString`. | Null-check the pointer. The id-to-round-name mapping (`PeriodName.tbb`) is not decoded. The turn counter's meaning is only an accessor-level reading. For the first match of a career (`CreateGiForFirstMatch` 0x1144d0) the period may stay 0. The PlGiTask demo flag follows a runtime-selected-competition regulation flag and is not shown to mean "title attract match". Also, "demo == 0 and VS == 0" holds for opening-playoff matches as well as career matches. |

Refuted:

| Entry | Reason |
|---|---|
| BGM change task pointer at 0x347750 (proposed screen indicator) | The pointer is set when `Bgm.Play` starts a change (store 0x104344) and cleared to 0 when the change finishes (store 0x104390), so it reads 0 almost always. Task +0x1c is a remapped track id, not the script argument. A candidate, not validated, is the static at 0x347364 (current or last BGM track id, written by `ChangeBgm::Execute` at 0x103e04). Do not rely on either as a screen indicator; music can continue across screens. |
| "0x3909a8 is 0 outside a career", "re-created on New Game or load", "reshuffled on each load" | The create runs once per boot and the delete is unreachable (see "Pointer chains and stability"). |
| "The first season is 2005-06" as a code fact | The code gives 2005 turn 92 at New Game and 2006 turn 0 for the first real season. |

### Still unknown

- There is no static current-module (screen) id beyond the activity
  table above, which says which modules the script has started and not
  yet deleted. Modules are also heap tasks: `CFcEuro_ModuleController`
  (0xc0 bytes, made in `fcEuroModule_Entry` 0x10eea0) holds the module at
  +0x20, and the module id is a word at module +0x188 (`SetId` 0x10edc8)
  with an active flag at +0x184. No root pointer from the sequencer to
  these tasks was found. Module ids are in `SRC/sqb.py` `MODULES` (6
  Game, 35 MatchMenu, 45 Title, 24 SimRoot, 33 SeasonEnd, 34 MonthEnd and
  so on).
- How to tell the 3D match from the pre-match menu with the PlGiTask
  alone: both have 0x5eacb0 set. The activity table slot of Game (6)
  versus MatchMenu (35) is the likely signal. `PlGiTask+0x7c`
  (`GetTimeMode`) and `+0x80` (set to 3 by `EnterOT`) look like a match
  phase and an extra-time marker, but their values were not traced.
- How VS mode is flagged at run time. The `CScheEuro` variant words
  above identify it, and `IsVsMode` (0x1147c8) calls a virtual at vtable
  +0x18. As a cheap proxy, use UID 148 to 163 in 0x5eacb0 or a team id of
  0x21f to 0x22e.
- The round id to name mapping (`PeriodName.tbb` round names, category
  11 names at 1000 + UID) is not decoded and not matched to UIDs in
  `DOC/SCHEDULE_FORMAT.md`.
- A "career is loaded" flag: since `P` is non-zero from boot, a content
  test (`u32[block1+0x4b4] == 1` plus a plausible year) is the
  investigator's proposal, not read from code. Whether the blocks are
  blank, demo data or stale data on the title screen was not traced.
- Whether the block offsets and base are identical across separate
  boots (shuffle state seeded 0x12345678, other consumers of 0x569dc0
  unchecked).
- Whether the demo flag clears promptly when the player skips or
  interrupts the demo (whether `SetDemoFlag 0` at 0x208 is skipped), and
  whether `CScheEuro` is finalised on that path. Not traced.
- Whether the PlGiTask (0x3906d8) is created in a title-demo match:
  `Sche.MatchStart` is called at script offset 0x118 of
  `ROOTDEMOMATCHSEQ.SQB`, but `initializeTodayMatch` is guarded by
  `getTodayMatchNum(1)` and what the demo setup makes it return was not
  traced. So whether 0x5eacb0 is set during the demo is also unknown.
- Whether a soft reset, the developer launcher or a save-state load
  from another boot leaves stale non-zero values in 0x390650, 0x3906d8
  or the other roots.
- Whether a match simulated by the controller for other fixtures of the
  day changes the PlGiTask team ids.
- What changes a club's competition (+4 of block 3) at promotion or
  relegation, and when, needs a save-state diff across a season rollover.
- Gap: the stage and group name lookup, the nation of the opponent, and
  a "season number" display have no verified source.
- Gap: the modded LMASTER builds add competitions 50 to 55 and change
  the league table, `ProcPromotion` and `Compe2PlDiv`. The tables above
  are the PAL retail ones.
- Gap: the Japanese release (`SLPM-66316`) addresses were not
  re-checked. Use `python SRC/gamever.py check ISO_JP` and translate the
  constants before use. `DOC/JAPANESE_RELEASE.md` puts the pwork global
  there at a different address (0x38c948), so no address here is shared.

### Checking the claims

Each command was run and shows the lines named. `addr` takes a hex
address and a count of instructions.

```bash
# Demo flag: sw to lui 0x35 / -0x2bc4 = 0x34d43c at 0x109394
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x109358 16

# Current match group: store at 0x21dd6c (lui 0x5f / -0x5350 = 0x5eacb0)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x21dd38 50

# Competition today: stores to +0x280, +0x28c, +0x290, +0x288, +0x298
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x205a90 30

# Reset to -1 (stores at 0x2058d0 and 0x2058d8)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x205868 32

# Continue-only call site (0x203134 test of +0x408, call at 0x203198)
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x203120 30

# Your club's record: get(P,1) + 0x4b4
python SRC/sles_disasm.py ISO/SLES_541.51 dis pwkTeam_GetMyTeamData

# Module activity table stores
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x10b2c0 10
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x10b670 8
```

## Still unknown

Each section above ends with its own "Still unknown" list, which holds
every open question. These five matter most for an achievement set.

- **No value was measured in a running game.** The buffer base of each
  heap block, the load base of each overlay and the shuffled block
  offsets of the career work buffer were never read at run time. Whether
  they are the same on every boot of the same disc is open, so no
  heap-resident address may be hard-coded. See "Address space layout"
  and "Save, load and new game transitions".
- **Cancelling the attract demo.** Whether a button press skips
  `SetDemoFlag 0` at `ROOTDEMOMATCHSEQ` 0x208, leaves the demo flag
  0x34d43c at 1 and skips `Sche.Finalize`, was not traced. A set that
  needs the demo guard depends on it. See "Game mode, screens and flow"
  and "Non-career modes and guards".
- **Matches in the demo and in VS mode.** Whether the match-day object
  (0x3906d8) and the current match group (0x5eacb0) exist in a title-demo
  match or a VS match was not traced. See "Game mode, screens and flow"
  and "Rich presence identifiers".
- **Save and load progress.** No static "save in progress" or "load
  finished" flag was found, and the number of frames a load takes to
  decode was not measured. The safe gate by script order is the
  schedule pointer 0x390650 becoming non-zero. See "Save, load and new
  game transitions".
- **The Japanese release.** `gamever.py` has no entries for the module
  table, 0x390650 or the mode constants, and the pwork global is already
  known to differ (0x38c948). No address in this doc was checked on
  `SLPM-66316`. See "Non-career modes and guards" and
  [`JAPANESE_RELEASE.md`](JAPANESE_RELEASE.md#still-unknown).

## Checking the claims

Run from the repo root. The disassembly commands need `ISO/`, and the
script listings need `DAT/` (see the README for setup).

```bash
# the career work buffer root is created by the first script command
python SRC/sles_disasm.py ISO/SLES_541.51 dis PwkCallbackCommand_Create
python SRC/sles_disasm.py ISO/SLES_541.51 dis plPwork_CreatePwork
python SRC/sqb.py dis DAT/SEQ/ROOTMAINSEQ.SQB

# the schedule session object and its three mode words
python SRC/sles_disasm.py ISO/SLES_541.51 dis CreateScheEuro

# the match-day object: created and cleared by plGi_Create and plGi_Delete
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Create
python SRC/sles_disasm.py ISO/SLES_541.51 dis plGi_Delete

# the module activity table: store at 0x10b2d8, clear at 0x10b684
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x10b2c8 8
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x10b678 6

# the attract demo and its flag (0x34d43c is stored at 0x109394)
python SRC/sqb.py dis DAT/SEQ/ROOTDEMOMATCHSEQ.SQB
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x109390 4

# the heap block table is filled by HeapInitialize
python SRC/sles_disasm.py ISO/SLES_541.51 addr 0x14d840 40

# which of these addresses resolve on the Japanese build
python SRC/gamever.py check ISO_JP
```
