# TODO

Rough priority order, most valuable first.

## 1. Message text (`DAT/MESSAGE/MES.PAC`)

`MES.PAC` is a named BINPAC (`pac.py` already opens it) holding **3,738
`.mbb` entries**, 19 MB of what should be the game's text. Nothing documents
the `.mbb` format yet.

Why first:

- **Unblocks the event tables.** The EvsDataBin NEWS and MAIL columns are
  still unnamed, and the EVENT records are fully numeric. Their message IDs
  probably point into these files, so decoding the text would turn values
  like `u_0c = 1423` into real headlines and mail.
- **Most useful output outside the project**: translation patches, wikis, the
  LMAST Discord.
- **Probably tractable.** Likely a string-offset table plus control codes;
  the main unknown is the encoding (Shift-JIS vs. a custom table for the
  European languages).

Plan:

- [ ] Find the `.mbb` loader (`sles_disasm.py syms Mes`, `snr2.py xref`)
- [ ] Write `DOC/MBB_FORMAT.md`
- [ ] Add `SRC/mbb.py` with `info` and a CSV/text dump
- [ ] Link message IDs into `evsdatabin.py` output
- [ ] Name the NEWS and MAIL columns in `DOC/EVSDATABIN_FORMAT.md`

## 2. Ninja 3D models and motions

`.SNJ` / `.SNO` / `.SNM` / `.SNP` (about 130 files in `GAME/`, `TEST3D/`,
`STADIUM/`, ...). `GAME_DIR.md` names the chunk types (`NSIF`, `NSOB`,
`NSMO`, `NSNT`, `NSTL`, `NFN0`) but nothing parses them. Textures already
decode, so this would give complete assets. The largest job on the list.

- [ ] Document the chunk layouts (`DOC/NINJA_FORMAT.md`)
- [ ] Add a parser, with export to a common format (e.g. OBJ/glTF)

## 3. `DAT/PLAYER/`

The largest directory (1.2 GB). `pac.py` covers the containers (KC@P face
packs, uniform CLUT packs, `CUTINHUMANPACK.MRG`, ...), but what the entries
hold (player models, faces, edit/uniform data) is undocumented.

- [ ] Survey the entry types
- [ ] Write `DOC/PLAYER_DIR.md`

## 4. Music and sound effects

- [ ] `SOUND/MAP*.DAT`, `EVENT_SE.DAT`, `SYS_SE.DAT`, `PACK0.DAT`: check
      whether they are `ps2_DTPK` banks `sounddat.py` can already decode
- [ ] `.SQB` sequences (19 files in `SEQ/`)

## 5. Housekeeping

- [ ] Regression check: a script that runs every tool's `info` over `DAT/`
      and fails on any new warning
