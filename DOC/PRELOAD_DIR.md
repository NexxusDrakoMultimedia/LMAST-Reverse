<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# `DAT/PRELOAD`: bulk-load packs, and which copy the game reads

`DAT/PRELOAD` holds **139 BINPAC packs** ([`PAC_FORMAT.md`](PAC_FORMAT.md))
plus `DUMMY.DAT` and `CVS/`. Every entry in them is a copy of a file that
also exists elsewhere on the disc: a loose file, or a `MES.PAC` entry for
messages. A screen loads its pack in one read instead of fetching dozens
of small files. **While a pack is in memory, the game reads its copies,
not the originals.** An edit therefore has to reach both, which is what
`patch_disc.py --copies` does ([`REBUILD.md`](REBUILD.md#copies)).

`python SRC/preload.py info DAT` checks every pack against its sources
and gives its free room for a rebuild.
`python SRC/preload.py lists ISO` prints the load lists from the game
code. `python SRC/preload.py who DAT <name>` says which packs hold a file
and what loads them.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x14eb4c` | (file-manager setup) | the folder ids: 0 `0SYSTEM`, 1 `SEQ`, 2 `CSE`, 3 `MESSAGE`, 4 `PARAM`, 6 `SOUND`, 7 `TEST3D`, 8 `EMBLEM`, 9 `PLAYER`, 10 `STADIUM`, 11 `EVENT`, 12 `GAME`, 13 `ACROBATA`, 14 `BG`, 15 `NEWS`, 16 `PRELOAD`. 5 is the disc root (`version.dat`) |
| `0x10c9a0` | `CFcEuro_FileResource::CommonSetup` | a folder of 100 or more means folder − 100 with the language digit put before the dot (`simfile.pac` → `SIMFILE1.PAC`). The resource *name* keeps the plain file name |
| `0x10e000` | `fcEuroFile_GetFileResourceName` | a whole-file resource is named `F%02d_%04d_%04d_` + file name, with the folder and two zeros: `F04_0000_0000_Regulation.tbb` |
| `0x104ce0` | `CFcEuro_Common::SetupResource` | the load-list record (below) and the resource each kind creates |
| `0x104ed0` | `CFcEuro_Common::ExecuteBase` | the records are created in list order, and each one must finish loading (`CheckPrepareEnd`) before the next is created |
| `0x10d848`–`0x10d9dc` | `CFcEuro_FileResource::Execute` | when a pack finishes loading, each entry becomes a child resource (`0x10d218`) named from its column 3 folder and its name, and is registered with `fcEuroRsrc_EntryResource` |
| `0x10d8fc`–`0x10d974` | same | an entry with column 4 = 1 is registered without the character before the dot: `gp_icon0.csp` becomes `gp_icon.csp` |
| `0x112040` | `fcEuroRsrc_EntryResource` | registering a name that already exists deletes the new resource and returns the old one, so **the first copy registered wins** |
| `0x10cc98` | `CFcEuro_FileResource::ExistingSetup` | a request for an entry of a pack first looks for the pack among the resident resources |
| `0x10f1c0` | `CFcEuro_MsgResource` constructor | a message request first looks up `F03_0000_0000_<cat>_<lang>.mbb`. Only if that doesn't exist does `Execute` (`0x10f4b0`) read the file from `MES.PAC`, through the executable's own 3,738-entry offset table at `0x34df50` ([`MBB_FORMAT.md`](MBB_FORMAT.md#size)) |
| `0x10bf58`, `0x10c008` | `FC_EURO_EVCOM` sequencer commands (table `0x34de68`) | the first starts loading `stationmes.pac` (folder `0x74` = 116). The second waits until it has loaded, then creates the 10 global message categories from the table at `0x51a528` |
| `0x307f18`–`0x307f9c` | `CFileManagerRofs::FileUpdateCore` | a whole-file request (sector count 0) takes its length from `ADXF_GetFsizeSct`, allocates that many sectors × `0x800` (`0x307f2c`, the buffer call at `0x307f54`), seeks to 0 and reads them all with `ADXF_ReadNw` |
| `0x1bd234`–`0x1bd244` | inside `ADXF_GetFsizeSct` (`0x1bd1e0`) | the sector count is `(size + 0x7ff) >> 11` of the byte size from `0x1bd290` (the open ROFS file; not traced further). The ISO9660 directory record is the only place the disc stores a file's size |

### The load-list record

A module's `GetPreLoadData` returns an array of `0x28`-byte records,
ended by kind 5.

| Offset | Field |
|---|---|
| `+0x00` | kind: 0 file, 1 CSE, 2 message, 3 texture list, 4 common texture, 5 end |
| `+0x04` | folder (+100 for a language digit) |
| `+0x08` | file name pointer (kinds 0, 1, 3) |
| `+0x10` | message category (kind 2) |
| `+0x18` | stored in the file resource's flags (`CommonSetup` `0x10cb48`). 3 for the `*LARGE` packs, 5 for the `*LOCALMEM` packs, 4 for most other files; meaning not decoded |
| `+0x24` | 1 = register the pack's entries (it becomes bit 8 of `+0x125`, set at `0x10cc10` and tested by `Execute` at `0x10d83c`). Set in every record naming a `PRELOAD` pack. `plresourcesim.pac` has 0: its entries are read through `plResource`, not by name |
| `+0x1c`, `+0x20` | kind 4 only: passed to `CFcEuro_CommonTexture` (`0x104e2c`). The season list has 12 such records, `+0x20` = 1, 2, 3, 75, 147, ... 651 |
| `+0x14` | passed on to the file-resource constructor; 0 in every list |

### The pack entry

`PRELOAD` packs are BINPAC version 3, so each entry has two extra
columns:

| Column | Meaning |
|---|---|
| 3 | the folder the entry's original lives in (the ids above) |
| 4 | 1 if the name ends in the language digit, which is dropped when the entry is registered |

## Which copy the game reads

A request for a file goes by name. If a resource of that name is already
registered, it is used, and the disc isn't touched. Every load list that
names a `PRELOAD` pack puts the pack **first** and then requests the files
inside it. The pack has finished loading and registered its entries before
those requests are made, so **they are served from the pack**. The
original is read only when a file is requested while none of the packs
holding it is resident.

The loaders, from `python SRC/preload.py lists ISO` (addresses in the
file named, `SLES` = `SLES_541.51`):

| Pack | Loaded by | Resident while |
|---|---|---|
| `STATIONFILE` | root module list `SLES 0x51ab98` (`CFcEuro_RootModule::GetPreLoadData`, `0x112a08`) | the whole game |
| `STATIONMES<n>` | the two `EVCOM` commands above | the whole game. Holds the 10 global message categories 1, 3–11 (club names are category 3) |
| `SIMFILE<n>`, `SIMLARGE`, `SIMLOCALMEM<n>` | `SIMPRG.REL` list `0x214448`, `SIMROOT_MODULE` (`0x7a18`; `0x214d80` in the demo) | the season mode |
| `TOPMENU<n>` | `SIMPRG.REL` list `0x213cf8` (`0x5870`, after `pSetupSideMenuModule`) | the side menu |
| `MAIL<n>` | `SIMPRG.REL` list `0x21bd58`, `MAIL_MODULE` (`0x36d60`) | the mail screen |
| `NEWS<n>` | `SIMPRG.REL` lists `0x2193c8` (`0x23ee0`, the public relations module) and `0x2195a0` (`0x24440`, the news module) | those screens |
| `TALK_*<n>` | `SIMPRG.REL` lists `0x215190` (contract), `0x215660` (dismiss), `0x2162a8` (move), `0x217088` (normal, `CTalkNormalManager`), `0x217220` (player retire), `0x217700` (promise level 2), `0x217a40` (promise result), `0x218028` (withdraw) | that talk scene |
| `TACTICSFILE<n>`, `TACTICSLARGE<n>` | `SLES 0x55b120`, `CTacticsManagerImplement::GetPreLoadData` (`0x2e3420`) outside a match | the tactics screen |
| `TACTICSMATCHFILE<n>`, `TACTICSMATCHLARGE<n>` | `SLES 0x55b3a8`, the same function when its mode (`+0x44`) is 2 or 3 | the tactics screen in a match |
| `GAMEFILE<n>`, `GAMELOCALMEM` | `GAMEPRG.REL` list `0x265590`, `GAME_MODULE` (`0xbd0`) | a match |
| `TACTICSPITCH` | `CLoader::loadFileRequest` from `WP::CTacticsPitch`'s constructor (`SLES 0x2a89cc`) | the tactics pitch. This is the model loader, not a registering file resource; whether its entries are shared hasn't been traced |

`<n>` is the language digit, 0–6 (0 Japanese, 1 English, then French,
German, Italian, Spanish and an unused seventh slot, as in `MES.PAC`).

`TACTICSFILE.PAC` and `TACTICSMATCHFILE.PAC`, without a digit, are **not
loaded**: the tactics lists ask for folder 116, which always adds the
digit.

Some copies are resident all game (`STATIONFILE`, `STATIONMES`), and
others only on one screen. A few files are also requested from places
that don't load a pack. The welcome mail's text (`563_1.mbb`) is an
example. The event code puts up a new mail with its own message request
(`SIMPRG.REL 0x136384`, through `0x12e0c8`), while no mail pack is
resident, so it reads `MES.PAC`. The Mail screen loads `MAIL<n>.PAC`
first and reads the pack's copy. Both copies are read, on different
screens.

### Tested in PCSX2

A test disc was patched with different text in each copy:

| File | In `MES.PAC` | In the `PRELOAD` copy |
|---|---|---|
| `3_1.mbb`, all 540 English club names | `MES` | `STA` (`STATIONMES1.PAC#2`) |
| `563_1.mbb`, the welcome mail's subject and body | `Copy A: MES.PAC` | `Copy B: PRELOAD` (`MAIL1.PAC#6`) |

- VS mode, Team Selection: Birmingham showed as **`STA`**. The club names
  come from `STATIONMES1.PAC`.
- Loading a 2006–2007 save and opening the Mail screen (Check e-mails →
  Others): the welcome mail's subject and body both read **`Copy B:
  PRELOAD`**. The Mail screen reads `MAIL1.PAC`.
- An earlier test ([`MBB_FORMAT.md`](MBB_FORMAT.md#size)) showed the
  `MES.PAC` text when the same mail popped up in a new game. That is the
  event code's request, made while `MAIL1.PAC` wasn't loaded.

## Empirical, from every pack

`python SRC/preload.py info DAT`:

- 139 packs, 1,749 entries. Every entry's column 3 is a known folder,
  and its original exists under that folder (or in `MES.PAC`).
- 1,747 entries are **byte-identical** to their original. The other two
  are `gp_practiceicon.csp` in the unused `TACTICSFILE.PAC` and
  `TACTICSMATCHFILE.PAC`.
- 63 entries have column 4 = 1, all `CSE` screen layouts, and each ends in
  its pack's language digit.
- Entries by folder: 861 `MESSAGE`, 394 `CSE`, 177 `GAME`, 100 `PLAYER`,
  64 `BG`, 62 `PARAM`, 49 `NEWS`, 21 `EVENT`, 14 `0SYSTEM`, 7 `EMBLEM`.

## What this means for mods

- Edit both copies. `patch_disc.py --copies` finds them by name and bytes,
  and `preload.py who` shows which screens read each one. It isn't safe to
  skip a copy because a quick look in the game shows the other one.
- A club-name edit made only in `MES.PAC` doesn't show: the names are read
  from `STATIONMES<n>.PAC` all game.
- A message file that grows in `MES.PAC` ([`MBB_FORMAT.md`](MBB_FORMAT.md#writing))
  also grows in its `PRELOAD` copies: `patch_disc.py --copies` rebuilds
  the packs that hold it (below), and moves a pack that outgrows its
  last sector ([`REBUILD.md`](REBUILD.md#moving-files)).

## Rebuilding a pack

A pack is read whole, in sectors: `(size + 0x7ff) >> 11` of them, from
the size in its directory record (confirmed above). Its entries are then
found through its own header (`Execute`, `0x10d848`), and nothing else
on the disc holds their offsets. So a pack can be rebuilt with entries
of new sizes, as long as it still ends in the same sector. Only the
pack's bytes and the size in its directory record change; no other file
moves.

How `patch_disc.py` does it ([`REBUILD.md`](REBUILD.md#size-changes-inside-the-last-sector)):

- Every edit to an entry of a `PRELOAD` pack is collected per pack: a
  copy found by `--copies`, or a `PRELOAD/<pack>#<entry>` target.
- The pack is read from the image with the header it has there now, so
  a second run works on a pack an earlier run rebuilt.
- If every entry keeps its size, the entries are written in place.
  Otherwise the pack is rebuilt with `pac.build_binpac`, which lays it
  out exactly as the original packer did ([`PAC_FORMAT.md`](PAC_FORMAT.md#how-the-packer-laid-them-out-empirical);
  all 139 packs rebuild byte for byte). A pack that would need another
  sector is moved to the end of `DATA.ISO`
  ([`REBUILD.md`](REBUILD.md#moving-files)).
- An entry that grows but stays inside its `0x40` gap doesn't move
  anything: the pack keeps its size and only the entry's size field
  changes.

**Room.** `python SRC/preload.py info DAT` gives each pack's free bytes
to the end of its last sector. Over the 139 packs they run from 4
(`TALK_MOVE6.PAC`) to 2,032, median 1,244. Two have under 64 and 19
under 256. `STATIONMES1.PAC` (English club names and other global
messages) has 1,840, and `MAIL1.PAC` 760. A grown entry also uses up to
`0x3f` bytes of gap after it before the later entries move.

**Tested on a copy of `DATA.CVM`.** `mbb.py set` renamed Birmingham
(`3:2003`, English) to a 63-character test name, which grew `3_1.mbb`
from 6,672 to 6,724 bytes in its `MES.PAC` slot. `patch_disc.py patch
--copies` rebuilt `STATIONMES1.PAC` from 45,264 to 45,328 bytes (entries
3–9 moved by `0x40`) and rewrote its directory record. Reading the
patched image back through the decrypted table of contents gave a pack
of 45,328 bytes whose 10 entries all equal their new `MES.PAC` sources.
A second run changed nothing. Patching the original `MES.PAC` and
`STATIONMES1.PAC` back gave a `DATA.CVM` byte-identical to the original.

**Tested in PCSX2.** Birmingham (`3:2003`) and Blackburn (`3:2004`) were
renamed "Birmingham City FC (rebuilt pack)" and "Blackburn Rovers FC
(rebuilt pack)". That grew `3_1.mbb` from 6,672 to 6,720 bytes, one byte
past its `0x40` gap. `patch --copies` rebuilt `STATIONMES1.PAC` from
45,264 to 45,328 bytes, moving entries 3–9 by `0x40`, and rewrote its
directory record. In VS mode, Team Selection showed both new names in
full. The game loaded the larger pack, through the new size in the
re-encrypted directory record, and found the entries at their new
offsets.

## Still unknown

- What record field `+0x18` selects (3, 4 or 5).
- Whether `TACTICSPITCH.PAC`'s entries (loaded through `CLoader`) are ever
  used in place of their originals.
- `DUMMY.DAT` (not a pack).
