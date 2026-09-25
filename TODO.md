# TODO

Rough priority order, most valuable first.

## 1. Message text (`DAT/MESSAGE/MES.PAC`)

The format is decoded: see [`DOC/MBB_FORMAT.md`](DOC/MBB_FORMAT.md) and
`SRC/mbb.py`. All 3,738 files and 66,102 messages parse, in 7 language slots.

- [x] Find the `.mbb` loader (`Msg::CMsgSubCategory::Initialize`, `0x30d1c8`)
- [x] Write `DOC/MBB_FORMAT.md`
- [x] Add `SRC/mbb.py` with `info`, `dump` and `csv`
- [x] Link messages into `evsdatabin.py` output (`--text`). Message refs are
      `category << 16 | id`: EVENT `+0x64`, NEWS `+0x64`/`+0x6c`, MAIL
      `+0x10`/`+0x14`/`+0x20`/`+0x24`
- [ ] Name the remaining NEWS and MAIL columns in `DOC/EVSDATABIN_FORMAT.md`
- [ ] Find what triggers the 39 dialogue categories no EVENT record uses
- [ ] Work out `ESC 0xC3` (values 0–12, maybe a pose/animation)
- [ ] Map variable ids to what fills them (`Msg::VarBuf_*`, `SetVariable` callers)
- [ ] Check whether raw `0x0A`/`0x0D` bytes affect display

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

- [x] Regression check: `SRC/regress.py` runs every tool's `info` over `DAT/`
      and fails on any difference from a saved baseline
