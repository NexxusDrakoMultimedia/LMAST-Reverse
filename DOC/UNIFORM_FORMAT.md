# Club kits: `UNIFORM_LIST`, `COLOR_TBL` and the licensed kits

Every club's kit comes from one of two places:

- **Licensed clubs** (116 Italian, Spanish and Dutch clubs, team ids
  123–244) use real kit textures from `PLPACK_HOME/AWAY`, plus an 18-byte
  descriptor for numbers, names, collar and captain mark.
- **All other clubs** ("original teams") have their kits built from
  `DAT/PLAYER/UNIFORM_LIST.TBB`: designs for shirt, shorts and socks, their
  colours, and the same number, collar and captain-mark settings.

`DAT/PLAYER/COLOR_TBL.TBB` says which colours clash.

`python SRC/uniform.py info DAT/PLAYER ISO/SLES_541.51` checks all of it,
`show` prints a club's kits, `licensed` lists the licensed kits, and `set`,
`setlicence` and `setexe` edit them.

The layout is **confirmed** from the readers in `SLES_541.51` (addresses
below). The field names come from the developer Uniform Viewer
(`TESTPRG.REL`, see [`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)),
which prints them. A few small fields are still unknown. **Tested in
PCSX2**: an edited kit colour and an edited licensed number colour both
show in the Uniform Viewer (below).

## `UNIFORM_LIST.TBB`

A `TBB1` container with one table: 661 rows of 64 bytes.

**Confirmed.** The reader at `0x2d2b68` finds a team's row at
`(team id − 3) × 64` (`0x2d2bc8`) and checks that the row's first `s16` is
the team id (`0x2d2bd8`). It then unpacks the row into 76 halfwords. Each
field is read from a 32-bit word with its own shift and mask, so there are
unused bits between some fields. `FIELDS` in `SRC/uniform.py` lists the
bit position and width of every field, in the unpacker's order.

**Empirical.** Rows 0–539 hold teams 3–542, the licensed clubs included
(whether anything reads their rows isn't checked). The other 121 rows have
team id 0, so the lookup never finds them.

### Row layout

| Halfwords | Bits | Contents |
|---|---|---|
| 0 | 0–15 | team id (`s16`) |
| 1 | 16–18 | a 3-bit flag, returned by `UniformList_GetDataTeam`; meaning unknown (values 1–3) |
| 2–7 | 19–33 | home side fields (below) |
| 8 | 34 | 1 bit, unpacked but never copied out |
| 9–23 | 35–144 | home **outfield** kit, 15 fields |
| 24–38 | 145–254 | home **goalkeeper** kit, 15 fields |
| 39–44 | 256–269 | away side fields |
| 45 | 270 | 1 bit, never copied out |
| 46–60 | 271–375 | away outfield kit |
| 61–75 | 384–489 | away goalkeeper kit |

(The bit ranges include the unused gaps.)

**Confirmed.** `UniformList_GetDataTeam` (`0x2d3298`) copies the 6 side
fields and calls `UniformList_GetDataPlayer` (`0x2d3078`) twice. That copies
one 15-field kit into a `Param::PlUnifOne` of 15 bytes, one byte per field.
A `PlUnifGame` is the 6 side bytes, then the goalkeeper kit at `+6`, then the
outfield kit at `+0x15`. `pwkTeam_GetUnif` (`0x26ebd8`) fills a team's
`PlUnif` (0x50 bytes): the home `PlUnifGame` at `+6` and the away one at
`+0x2a`. For the player's own club it writes the main sponsor to `+4` and
the kit supplier to `+5` (`0x26ea2c`).

### The kit (`PlUnifOne`)

| Field | Bits | Contents |
|---|---|---|
| 0 | 9 | shirt design |
| 1, 2, 3 | 7 each | shirt colours |
| 4 | 3 | collar: `l_nml_bdy_01_el` + *n* |
| 5 | 8 | shorts design |
| 6, 7, 8 | 7 each | shorts colours |
| 9 | 8 | socks design |
| 10, 11 | 7 each | socks colours |
| 12 | 7 | shirt number colour (front and back) |
| 13 | 7 | shorts number colour |
| 14 | 3 | captain mark colour |

**Confirmed** from `CUniformLoader::_load_edit` (`0x2c2848`). It requests
the textures of fields 0, 5 and 9 (`_load_unif_req`, `0x2c2d10`, `0x2c2d98`,
`0x2c2e20`) and the palettes of fields 1–3, 6–8 and 10–13
(`_load_clut_req`, `0x2c2b84`–`0x2c2c70`). Before that it clamps the values
to the size of each pack (`0x2c28dc`–`0x2c297c`), and those limits match
the packs' entry counts exactly:

| Field | Outfield kit | Goalkeeper kit | Pack |
|---|---|---|---|
| shirt design | < 209 | < 38 | `EDIT_UNIFORM_ORG_SHT` (209) / `EDIT_UNIFORM_GK_SHT` (38) |
| shorts design | < 61 | < 38 | `EDIT_UNIFORM_ORG_PNT` (61) / `EDIT_UNIFORM_GK_PNT` (38) |
| socks design | < 18 | < 18 | `EDIT_UNIFORM_ORG_SOX` (18) |
| fields 10–13 | < 96 | < 96 | `EDIT_UNIFORM_CLUT` (96) |

A value past the limit is replaced with 0. The shirt and shorts colours
aren't clamped.

**Confirmed** from the Uniform Viewer, which prints these fields for an
unlicensed club (`TESTPRG.REL 0x15cb8`–`0x15f20`): "Collar Type" is field
4 (through the name table at `0x23570`), "Front/Back Number Color" field 12,
"Pants Number Color" field 13 and "CaptainMark Color" field 14. The values
it showed for Birmingham match the decoded row (outfield collar 0 =
`bdy_01`, numbers A8, shorts number I3, captain mark 3; keeper collar 7 =
`bdy_08`, captain mark 0).

**Empirical.** All 2,160 kits (540 teams × 4) are within the loader's
limits, and every colour is below 96, except team 427's away outfield
number colours (fields 12 and 13), which are 97 (the game resets them to 0).
`uniform.py info` reports that one kit with `!!`. Collars use 0–7.

### Side fields

| Side field | Bits | Contents |
|---|---|---|
| 0 | 2 | unknown (0 or 1) |
| 1 | 2 | unknown (0 or 1) |
| 2 | 5 | unknown (0–7) |
| 3 | 1 | front number shown (the viewer prints the front number colour only when set) |
| 4 | 2 | shorts number position: 0 off, 1 right, 2 left (names at `TESTPRG.REL 0x23560`) |
| 5 | 2 | unknown (0–2) |

Side fields 3 and 4 are **confirmed** from the same viewer code. Side field
1 has exactly the same value counts as side field 3 (878 × 0, 202 × 1), so
it may be related, but that isn't checked.

### Colours

`EDIT_UNIFORM_CLUT` holds 96 palettes, `org_uni_A1.svp` to
`org_uni_L8.svp`. Colour *n* is letter `A + n / 8` and digit `n % 8 + 1`.
The Uniform Viewer uses the same names ("Back Number Color: A8").
**Empirical**, from the palettes (256 × ABGR1555 shading ramps):

| Letter | Hue | | Letter | Hue |
|---|---|---|---|---|
| A | red | | G | cyan |
| B | orange | | H | sky blue |
| C | yellow | | I | blue |
| D | lime | | J | purple |
| E | green | | K | magenta |
| F | sea green | | L | pink |

Digits 1–7 run from light to dark. Digit 8 is a grey scale instead, from
white (A8) through greys to near-black (L8).

## Licensed kits

**Confirmed.** `CUniformLoader::_get_licence_no` (`0x2c24b0`) looks the
team up in a table at `0x3a08d8` of 8-byte rows `{u32 team id, u16
licence, u16 0}`, ending at team 0. It lists 116 clubs, teams 123–244, with
licences 0–115. A club not in it gets 0.

The licence number is the club's entry in `PLPACK_HOME.PAC` and
`PLPACK_AWAY.PAC` ([`PLAYER_DIR.md`](PLAYER_DIR.md#licensed-kits-plpack_)).
The numbers in the packs' texture names are not team ids: licence 0 is
`ita_228` and team 123, AC Milan.

`CUniformBuilder::GetLicenceUniformInfo` (`0x2c4cc8`) returns a pointer to
an 18-byte descriptor at `0x3a0c80 + (side × 116 + licence) × 0x12` in the
executable. Each pack entry's block 0 (32 bytes) starts with the same 18
bytes. **Empirical:** all 232 pairs (116 clubs × home/away) are equal, and
bytes 18–31 of every block 0 are zero.

### The descriptor

Bytes come in pairs, outfield then goalkeeper. The names are what the
Uniform Viewer prints for each byte (**confirmed**, `TESTPRG.REL
0x157f0`–`0x15bf0`):

| Bytes | Contents |
|---|---|
| 0, 1 | front number colour, `ff` = off (off in all 116 clubs) |
| 2, 3 | back number colour |
| 4, 5 | name type (1 or 2) |
| 6, 7 | name colour |
| 8, 9 | collar: `l_nml_bdy_01_el` + *n*; 11 is `l_tgt_bdy_01_el` |
| 10, 11 | shorts number position: 0 off, 1 right, 2 left |
| 12, 13 | shorts number colour |
| 14, 15 | unknown (1 or 2), not printed |
| 16, 17 | captain mark colour |

Colours use the same 96 names as above. **Empirical:** every value is in
range except licence 35 (`ita_269`) home, whose outfield shorts number
position is 4.

For example, AC Milan's home descriptor is `ff ff 13 11 01 01 11 11 01 04
02 02 03 11 02 02 00 04`. That's no front numbers, back numbers C4
(outfield) and C2 (keeper), name type 1, name colour C2, collars `bdy_02`
and `bdy_05`, shorts numbers on the left in A4 and C2, and captain marks 0
and 4.

**Tested in PCSX2:** the viewer draws the number colour from the
executable's copy, not the pack's. With AC Milan's home outfield back
number colour set to A8 (white) in `PLPACK_HOME.PAC` only, the number on
the back of the shirt stayed gold (C4). With the same change in the
executable's copy only (`uniform.py setexe`, patched as
`disc:SLES_541.51`), the viewer printed A8 and the number was white. What
`CLoader::l_realize_licenceuniform` uses the pack's copy for isn't traced.

## `COLOR_TBL.TBB`: which colours clash

**Confirmed.** `UniformList_CheckColor(a, b)` (`0x2d3420`) returns byte
`b` of row `a` of `COLOR_TBL`'s table 0. `UniformList_GetUseUniformSide`
(`0x2d3510`) calls it on outfield shirt colour 1 of the two teams (`PlUnif
+0x1c` and `+0x40`) to decide which side wears its away kit.

**Empirical.** The table is 96 × 96 bytes, all 0 or 1, symmetric, with 1 on
the diagonal: 2,089 clashing pairs. White (A8) clashes with 22 other
colours, mostly the lightest shade of each hue.
`python SRC/uniform.py clash DAT/PLAYER A8` lists them.

## Tested in PCSX2

- **Unlicensed kit colour.** With `uniform.py set ... 3
  home.outfield.1=A4 home.outfield.3=A4` (Birmingham's home shirt colours
  1 and 3, from I3 blue to A4 red), patched with `patch_disc.py --copies`
  into `UNIFORM_LIST.TBB` and its 7 copies in `PRELOAD/SIMFILE0`–`6.PAC`,
  the launcher's Uniform Viewer showed Birmingham in a red shirt with white
  panels and trim instead of blue. The shorts and socks were unchanged. The
  viewer lists Birmingham as an "original team" (`オリジナルチーム`).
- **Licensed number colour.** AC Milan, a "licence team"
  (`ライセンスチーム`), as described above: the executable's copy of the
  descriptor sets the colour of the shirt number.

## Still unknown

- The 3-bit flag, side fields 0, 1, 2 and 5, and the two unused bits.
- Descriptor bytes 14 and 15, and what the pack's copy of the descriptor
  is used for.
- What the 121 rows with team id 0 are.
- `UNIFORM_GK.TBB` (209 × 3 and 38 × 66 bytes, matching the `ORG_SHT` and
  `GK_SHT` counts).

## Tool

```bash
python SRC/uniform.py info      DAT/PLAYER ISO/SLES_541.51   # check everything
python SRC/uniform.py show      DAT/PLAYER 3                 # Birmingham's kits
python SRC/uniform.py licensed  DAT/PLAYER ISO/SLES_541.51   # the 116 licensed kits
python SRC/uniform.py clash     DAT/PLAYER A8                # colours that clash with white
python SRC/uniform.py roundtrip DAT/PLAYER/UNIFORM_LIST.TBB  # re-pack all 661 rows
python SRC/uniform.py set DAT/PLAYER/UNIFORM_LIST.TBB out/UNIFORM_LIST.TBB 3 home.outfield.1=A4
python SRC/uniform.py setexe ISO/SLES_541.51 out/SLES_541.51 home 0 outfield.backnumber=A8
```

`setexe`'s output is patched onto a disc image with
`python SRC/patch_disc.py patch <in.iso> <out.iso> disc:SLES_541.51=out/SLES_541.51`.
