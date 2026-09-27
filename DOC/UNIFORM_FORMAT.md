# Club kits: `UNIFORM_LIST.TBB` and `COLOR_TBL.TBB`

`DAT/PLAYER/UNIFORM_LIST.TBB` holds the home and away kits of every club
that doesn't use a licensed kit texture: designs for shirt, shorts and
socks, and the colours of each. `DAT/PLAYER/COLOR_TBL.TBB` says which
colours clash. `python SRC/uniform.py info DAT/PLAYER` checks both, `show`
prints a club's kits, and `set` edits them.

The layout is **confirmed** from the readers in `SLES_541.51` (addresses
below). The meaning of a few small fields is still unknown. **Tested in
PCSX2**: an edited kit shows in the developer Uniform Viewer (below).

## `UNIFORM_LIST.TBB`

A `TBB1` container with one table: 661 rows of 64 bytes.

**Confirmed.** The reader at `0x2d2b68` finds a team's row at
`(team id − 3) × 64` (`0x2d2bc8`) and checks that the row's first `s16` is
the team id (`0x2d2bd8`). It then unpacks the row into 76 halfwords. Each
field is read from a 32-bit word with its own shift and mask, so there are
unused bits between some fields. `FIELDS` in `SRC/uniform.py` lists the
bit position and width of every field, in the unpacker's order.

**Empirical.** Rows 0–539 hold teams 3–542. The other 121 rows have team
id 0, so the lookup never finds them.

### Row layout

| Halfwords | Bits | Contents |
|---|---|---|
| 0 | 0–15 | team id (`s16`) |
| 1 | 16–18 | a 3-bit flag, returned by `UniformList_GetDataTeam`; meaning unknown |
| 2–7 | 19–33 | home side fields: 2, 2, 5, 1, 2, 2 bits |
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
| 4 | 3 | unknown (not used by the loader) |
| 5 | 8 | shorts design |
| 6, 7, 8 | 7 each | shorts colours |
| 9 | 8 | socks design |
| 10–13 | 7 each | socks colours (four) |
| 14 | 3 | unknown (not used by the loader) |

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
| socks colours | < 96 | < 96 | `EDIT_UNIFORM_CLUT` (96) |

A value past the limit is replaced with 0. The shirt and shorts colours
aren't clamped.

**Empirical.** All 2,160 kits (540 teams × 4) are within those limits,
and every colour is below 96, except team 427's away socks colours 12 and
13, which are 97 (the game resets them to 0). `uniform.py info` reports
that one kit with `!!`.

### Colours

`EDIT_UNIFORM_CLUT` holds 96 palettes, `org_uni_A1.svp` to
`org_uni_L8.svp`. Colour *n* is letter `A + n / 8` and digit `n % 8 + 1`.
The developer Uniform Viewer uses the same names ("Back Number Color:
A8"). **Empirical**, from the palettes (256 × ABGR1555 shading ramps):

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

### Side fields

The 6 side fields per side (2, 2, 5, 1, 2 and 2 bits) and kit fields 4 and
14 aren't used by the texture loader, and their meaning is unknown. The
Uniform Viewer shows "Sleeve", "Pants", "Collar Type" and "Pants Type"
values, but it takes them from the licensed-kit data
(`CUniformBuilder::GetLicenceUniformInfo`, `TESTPRG.REL 0x14f10`), not from
this table.

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

With `uniform.py set ... 3 home.outfield.1=A4 home.outfield.3=A4`
(Birmingham's home shirt colours 1 and 3, from I3 blue to A4 red),
patched with `patch_disc.py --copies` into `UNIFORM_LIST.TBB` and its 7
copies in `PRELOAD/SIMFILE0`–`6.PAC`, the launcher's Uniform Viewer showed
Birmingham in a red shirt with white panels and trim instead of blue.
The shorts and socks were unchanged. The viewer lists Birmingham as an
"original team" (`オリジナルチーム`), so its kit is built from this table.
Licensed clubs (for example AC Milan, team 123, a "licence team"
`ライセンスチーム`) use their own kit textures instead.

## Still unknown

- The 3-bit flag, the 6 side fields, kit fields 4 and 14, and the two
  unused bits.
- Which clubs use a licensed kit instead of this table, and where that is
  decided (`CUniformLoader::_get_licence_no`, `0x2c24b0`).
- What the 121 rows with team id 0 are.
- `UNIFORM_GK.TBB` (209 × 3 and 38 × 66 bytes, matching the `ORG_SHT` and
  `GK_SHT` counts).

## Tool

```bash
python SRC/uniform.py info      DAT/PLAYER                   # check both tables
python SRC/uniform.py show      DAT/PLAYER 3                 # Birmingham's kits
python SRC/uniform.py clash     DAT/PLAYER A8                # colours that clash with white
python SRC/uniform.py roundtrip DAT/PLAYER/UNIFORM_LIST.TBB  # re-pack all 661 rows
python SRC/uniform.py set DAT/PLAYER/UNIFORM_LIST.TBB out/UNIFORM_LIST.TBB 3 home.outfield.1=A4
```
