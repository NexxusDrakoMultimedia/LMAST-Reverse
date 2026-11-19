<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Club kits: `UNIFORM_LIST`, `UNIFORM_GK`, `COLOR_TBL` and the licensed kits

Every club's kit comes from one of two places:

- **Licensed clubs** (116 Italian, Spanish and Dutch clubs, team ids
  123–244) use real kit textures from `PLPACK_HOME/AWAY`, plus an 18-byte
  descriptor for numbers, names, collar and captain mark.
- **All other clubs** ("original teams") have their kits built from
  `DAT/PLAYER/UNIFORM_LIST.TBB`: designs for shirt, shorts and socks, their
  colours, and the same number, collar and captain-mark settings.

`DAT/PLAYER/COLOR_TBL.TBB` says which colours clash. Your club, the rival
and the VS teams get their keeper kit in a match from
`DAT/PLAYER/UNIFORM_GK.TBB`, which picks it from their outfield shirt.

`python SRC/uniform.py info DAT/PLAYER ISO/SLES_541.51` checks all of it,
`show` prints a club's kits, `licensed` lists the licensed kits, `gk` lists
the keeper kit table, and `set`, `setlicence`, `setexe` and `setgk` edit
them.

The layout is **confirmed** from the readers in `SLES_541.51` (addresses
below). The field names come from the developer Uniform Viewer
(`TESTPRG.REL`, see [`SQB_FORMAT.md`](SQB_FORMAT.md#the-developer-launcher)),
which prints them. A few small fields are still unknown. **Tested in
PCSX2**: edited club kits, licensed number colours and keeper schemes
show in the Uniform Viewer and in matches, including edits made in the
editor's Kits tab ([below](#tested-in-pcsx2)).

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
| 1 | 16–18 | a 3-bit flag, returned by `UniformList_GetDataTeam` and stored in `PlUnif +0`: 2 or 4 makes the kit a licensed one, anything else a generated one ([below](#licensed-or-generated-the-flag)) |
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
outfield kit at `+0x15`. `pwkTeam_GetUnif` (`0x26e9d8`) fills a team's
`PlUnif` (0x50 bytes): the home `PlUnifGame` at `+6` and the away one at
`+0x2a` (the home side's lookup starts at `0x26ebd8`, its call is at
`0x26ebe8`; the away call is at `0x26ec08`). For the player's
own club it writes the main sponsor to `+4` and the kit supplier to `+5`
(`0x26ea2c`).

**The sponsor and supplier bytes (`PlUnif +4`, `+5`).** **Confirmed.**
`pwkTeam_GetUnif` (`0x26e9d8`) fills them for your club only: the main
sponsor from `pwkSponsor_GetMainSponsor` (`0x257350`) and the supplier
from `pwkSponsor_GetSupplier` (`0x257390`, `0x26ea2c`–`0x26ea40`). For
every other club, found through `UniformList_GetDataTeam`, it writes 0
to both (`0x26ec1c`–`0x26ec24`); `pwkTeam_SetLogoUnif` (`0x26e3b0`)
sets either for your club later. The licensed kit loader
(`CUniformLoader::_load_licence`, `0x2c25cc`–`0x2c25e8`) resets a main
sponsor of 200 or more and a supplier of 7 or more to 0, so a club can
show 200 sponsors and 7 suppliers. Nothing shows on a computer club's
kit, where both are 0 (Nexxus's report, 2026-11-10).
`CUniformBuilder::Init` (`0x2c48b0`) copies the whole `PlUnif` into the
builder at `+0xb4`, and the loader turns the two numbers into texture
requests ([below](#the-sponsor-and-supplier-logos-on-a-generated-kit)).
Which sponsor and supplier numbers have a logo texture isn't known.

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
| 14 | 3 | captain mark colour (the editor offers 0 to 4: white, black, blue, red, yellow) |

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

### Shirt designs and the three shirt colours

**Tested in PCSX2** (Nexxus's screenshots of the Uniform Viewer,
2026-11-10, on `LMAST-test-kits.iso`, shirt colours A4 red, E4 green,
I4 blue): in designs 0, 2 and 3 colour 1 fills the body, colour 2 is
the pattern (design 3's checks, design 2's sleeve) and colour 3 the
trim (the blue edges, and design 0's centre bar split green and blue).
**Empirical:** `EDIT_UNIFORM_ORG_SHT` textures are 256 × 256 with 8-bit
indices read through the default grey palette, and the indices fall in
three bands that match: up to 68 and shading below 100 is colour 1, 119
to 140 (about 100–179) colour 2, and 180 and up (to 206) colour 3. The
lower half of a texture holds the two torso panels, the right one the
front (design 0's bar is on it). Mapping each band to a flat colour gives
a front-panel picture of every design.

Some designs, by what the front panel shows (empirical, from those
pictures; only 0, 2 and 3 are checked in the viewer):

| Design | Front panel |
|---|---|
| 12, 13, 15, 76–80 | plain, the shirt in colour 1 (15 has no trim lines) |
| 10 | vertical stripes, 7 across; 25 three wide bars; 26 two; 44 six; 60 six broad; 91 many narrow; 50 and 66 pinstripes |
| 7 | wide hoops; 73 three broad hoops; 72, 75, 155, 182 hoop variants; 70 thin hoops |
| 33 | right half in colour 2; 47 a half with a yoke; 4 and 135 quarters |
| 1 | a diagonal half; 118 a broad diagonal band; 19, 29, 116 sashes |
| 153, 154, 179, 197 | a band across the chest; 114 a band near the top |
| 97, 125, 152, 195 | a broad centre panel; 0, 11 a narrow centre bar |
| 3, 24, 90, 138, 139 | checks |
| 45, 85, 115, 170 | V shapes; 134 and 169 a cross |

`kits.csv` uses 12 of these (`KIT_PATTERNS` in `uniform.py`). The 18
sock designs are nearly all plain in colour 1 (design 0 has only a few
marks), and most of the 61 shorts designs are plain with a mark at the
side; the table uses design 0 of both.

### Side fields

| Side field | Bits | Contents |
|---|---|---|
| 0 | 2 | the shirt's Emblem Type (the editor's item: 3 options, values 0 to 2) |
| 1 | 2 | the shorts' Emblem Type (3 options, values 0 to 2) |
| 2 | 5 | the number design (8 options, values 0 to 7) |
| 3 | 1 | the front number: 0 none, 1 the number on the chest |
| 4 | 2 | the position of the number on the shorts (3 options, values 0 to 2; 2 is the setting that decouples it from the emblem) |
| 5 | 2 | not an editor item; a match feeds the builder the constant 1 for it, so it never matters in a match (0–2 in the data) |

**Confirmed** from `SIMPRG.REL`'s kit editor, which reads and writes these
bytes ([below](#the-kit-editors-items-and-their-bytes)). The Uniform
Viewer of `TESTPRG.REL` names side field 4 "off, right, left" (names at
`TESTPRG.REL 0x23560`) and prints the front number colour only when
side field 3 is set; for a generated kit the states below contradict the
viewer's names for field 4 (position 0 shows a number), so the names are
not confirmed for a generated kit, and the field is the editor's item
"Position on shorts". Side fields 1 and 3 have the same value counts
over the whole table (878 × 0, 202 × 1), which is chance: they are
different items, and in the computer clubs their counts differ
([below](#the-kit-editors-items-and-their-bytes)).

**Sponsor and supplier logos (empirical).** In PCSX2 states (Nexxus,
2026-11-10) your club's match kit record and the rival's, whose kits show
a sponsor and a supplier logo, have side fields 1, 3 and 5 of the home
side at 1 (your club's side fields `0 1 0 1 1 1`, the rival's
`0 1 0 1 0 1`), and a computer club's (Betis, from `kits.csv`) had `0 0 0 0
1 0` with a valid sponsor and supplier and no logos. The difference is
not what hides a computer club's logos: the texture-list test is
([below](#the-sponsor-and-supplier-logos-on-a-generated-kit)), and
`--mod random-sponsors` doesn't set these fields (`--mod kit-standards`
does, [`LMASTER_MOD.md`](LMASTER_MOD.md#kit-standards)).

**The logo's colour (Nexxus's observation, 2026-11-19).** The supplier
logo on the shirt takes the shirt number colour (kit field 12): the number
colour decides the logo's colour too, so a number colour that does not
show on the shirt hides the logo as well.

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
white (A8) through greys to near-black (L8). Entries 64–191 of every ramp
hold its main shade (entry 128: A1 (255, 222, 222), A4 (148, 41, 41), A8
white), which the editor shows as each colour's swatch
(`uniform.colour_swatches`).

## The kit editor's designs per supplier

The kit editor does not offer every shirt and shorts design: it offers
the ones the club's kit supplier makes. **Confirmed** from `SIMPRG.REL`
(found 2026-11-19, from Nexxus's pointer; not yet seen in the game).

| Address | Symbol | What it shows |
|---|---|---|
| `SLES 0x257390` | `pwkSponsor_GetSupplier` | the supplier id of your club; `UniformEdit` calls it at `SIMPRG 0x3fab4` |
| `SIMPRG 0x3fab4` | `UniformEdit` | index = supplier - 206 (`0xce`); anything outside 206 to 212, 0 (no supplier) included, becomes 7 and uses Doclla's mask |
| `SIMPRG 0x21d758` | supplier mask table | 8 u32: `0x80 0x40 0x20 0x10 0x08 0x04 0x02 0x02` |
| `SIMPRG 0x21d318` | shirt masks | one mask per outfield shirt design 0 to 208, exactly one bit each |
| `SIMPRG 0x21d660` | shorts masks | one mask per shorts design 0 to 60, exactly one bit each |
| `SIMPRG 0x42b40`, `0x42b80` | shirt list builders | keep the designs whose mask AND the supplier's mask is non-zero, ascending |
| `SIMPRG 0x42c10`, `0x42c50` | shorts list builders | the same for shorts |
| `SIMPRG 0x41ea8`-`0x41ed4` | the design menu | offers only that list |
| `SIMPRG 0x3fb54`-`0x3fd18` | editor start | re-validates the existing kit (below) |
| `SIMPRG 0x21d778` | style group table | 166 entries of {u16 group, u16 design}, groups 0 to 3; a design not in it counts as group 0 |

The lists, by supplier:

| Supplier | Shirt designs | Shorts |
|---|---|---|
| 206 Binnonn | 60 to 74 and 76 to 89 (29) | 36 to 39 |
| 207 Opnatis | 91 to 119 (29) | 40 to 43 |
| 208 Wrandon | 3, 75 and 120 to 144 (27) | 44 to 47 |
| 209 Untelio | 145 to 170 (26) | 48 to 51 |
| 210 Jompela | 171 to 190 (20) | 52 to 54 |
| 211 Egamucho | 6, 7, 10, 11, 15, 18, 25, 27, 28, 34, 38, 41, 44, 45, 53, 59 (16) | 55 to 57 |
| 212 Doclla | 90 and 191 to 208 (19) | 58 to 60 |

No supplier lists 43 shirt designs (0 to 2, 4, 5, 8, 9, 12 to 14, 16, 17,
19 to 24, 26, 29 to 33, 35 to 37, 39, 40, 42 to 43, 46 to 52, 54 to 58) or
shorts 0 to 35, which are the designs most computer clubs wear. Socks (0 to
17), the keeper kit designs and all colours are not limited by the supplier.

**Re-validation.** When the editor opens, the existing kit is checked
against the list: a shirt outside it becomes the last list design of the same
style group (table `0x21d778`), else the list's first; shorts outside it
become the list's first. The result is written back with `pwkTeam_SetUnif`
(flag 1). So signing a new supplier rewrites an out-of-list shirt and
shorts without a word.

**Club creation.** In season -1 nothing is signed and the game stores
supplier 212 (Doclla; the game's own, Nexxus: retail's first contract year
has Egamucho, and the editor in season -1 makes do with Doclla), so the editor offers
Doclla's 19 shirts (the menu reads Pattern n/19), 3 shorts (1/3) and the
18 socks. The 32 club-creation presets in `CEDITPRG.REL` (`0x150a0`,
`CSelectTeamColorModule`, chosen by the 32-colour palette id, function
`0x20b0`, `pwkTeam_SetUnif` at `0x20fc`) all have shirt 206, shorts 60 and
socks 14.

**The clash rule the editor applies to you** (the second kit only,
`+0x5f4` is 0). `UniformList_CheckColor` (`COLOR_TBL`, [above](#color_tbltbb-which-colours-clash)) is called on the home shirt's colour 1 and the
away shirt's colour 1 (`SIMPRG 0x40358` and `0x42594`, `CEDITPRG 0x686c`).
On entry a clashing away colour 1 is reset to the byte of the 96-byte table
at `SIMPRG 0x21cb78` indexed by the home colour 1, and a warning flag at
`+0x948` opens message `0x20`. In the colour palette the 32 selectable colours that
clash with the home colour 1 are greyed out
(`SetPaletteSelectStateArray`, `0x43e98`). Nothing checks colours 2 and 3,
the shorts, the socks or two equal designs.

**Where the kit lives.** Your kit is in the career's `pwork` block
(`PlPworkTask` entry 1, offset 0: the `PlUnif`; entry 2 at `+0x244` is the
rival's), not in `UNIFORM_LIST`. `pwkTeam_GetUnif` re-stamps `+4` and `+5`
from `pwkSponsor_GetMainSponsor` and `pwkSponsor_GetSupplier` on every read.
A computer club reads its `UNIFORM_LIST` row (`UniformList_GetDataTeam`,
called only at `0x26ebe8` and `0x26ec08` in `pwkTeam_GetUnif`), and the
loader accepts any design below 209 shirts, 61 shorts and 18 socks, so a
computer club can wear any supplier's design. No four-kit generator exists
in the game (searched); the only whole kits are the 32 presets. `--mod
kit-eras` uses these lists ([`LMASTER_MOD.md`](LMASTER_MOD.md#kit-eras);
`python SRC/kiteras.py info DAT` prints them from `SIMPRG.REL`).

## The kit editor's items and their bytes

The kit editor of a career's club creation (`SIMPRG.REL`'s
`CUniformEditor`) edits two kits of one `PlUnif`: it holds a pointer to
the side's six side bytes (`+0x58`) and one to its outfield kit (`+0x5c`).
**Confirmed** from `SIMPRG.REL`, found by an investigator and matched with
Nexxus's two save states and screenshots (2026-11-19). The editor has
one jump table of accessors per kind of item:

| Address | Symbol | What it shows |
|---|---|---|
| `SIMPRG.REL 0x1095f8`–`0x10968c` | `CUniformEditor::Initialize` | side = `PlUnif + 6` (home) or `+ 0x2a` (away); the kit = side + 0x15, the outfield kit |
| `0x109d98`, `0x109fb8` | `GetColorIndex`, `SetColorIndex` (tables `0x22a660`, `0x22a6c0`) | colour items: 0 shirt colours (kit fields 1 to 3), 1 shorts colours (6 to 8), 2 socks colours (10, 11), 3 shirt number colour (12), 4 shorts number colour (13), 5 captain's band (14) |
| `0x109ee8`, `0x10a0f0` | `GetDesignIndex`, `SetDesignIndex` (`0x22a680`, `0x22a6e0`) | design items: 0 shirt (kit field 0), 1 shorts (5), 2 socks (9), 3 side field 2, 4 side field 5 |
| `0x109f50`, `0x10a158` | `GetOptionIndex`, `SetOptionIndex` (`0x22a6a0`, `0x22a700`) | option items: 0 collar (kit field 4), 1 side field 0, 2 side field 1, 3 side field 3, 4 side field 4 |
| `0x41e6c`, `0x41e7c`, `0x41ee8` | the menu's builders | Shirt Emblem Type (`SetOptionIndex` 1), Collar (4), Shorts Emblem Type |
| `SLES 0x2c4b80`, `0x2c4bf0`, `0x2c4bf4` | `CUniformBuilder::Init` | a match writes the style byte it would feed as the constant 1 (side field 5 never matters in a match); the constant 2 is hard-wired for licensed kits |

The menu, with the text of each item (MES category 470, ids 106 to 116):

| Menu | Item | Byte | Options |
|---|---|---|---|
| Shirt | Design | kit 0 | the supplier's list ([above](#the-kit-editors-designs-per-supplier)) |
| Shirt | Colour 1, 2, 3 | kit 1 to 3 | 32 colours |
| Shirt | Emblem Type (id 110) | side 0 | 3: values 0 to 2 |
| Shirt | Collar | kit 4 | 11: values 0 to 10 (`l_nml_bdy_01` to `11`) |
| Shorts | Design | kit 5 | 61 |
| Shorts | Colour 1 to 3 | kit 6 to 8 | 32 colours |
| Shorts | Emblem Type | side 1 | 3: values 0 to 2 |
| Socks | Design | kit 9 | 18 |
| Socks | Colour 1, 2 | kit 10, 11 | 32 colours |
| Number | Design | side 2 | 8: values 0 to 7 |
| Number | Shirt number (colour) | kit 12 | 32 colours |
| Number | Front number (id 114) | side 3 | 2: option 1 is value 0, no front number; option 2 is value 1, the number on the chest (its page reads "Position 1/2, 2/2") |
| Number | Position on shorts (id 115) | side 4 | 3: values 0, 1, 2 |
| Number | Colour on shorts (id 116) | kit 13 | 32 colours |
| Captain's band | Colour | kit 14 | 5: values 0 to 4 |

Every colour item offers 32 of the 96 colours (the map is table 6 of
`DAT/EMBLEM/COLOR_TABLE.TBB`: A1 A2 A4 A6 A7 B2 B4 C2 C4 C5 D2 D4 E5 E7 F6
G3 H3 H5 H7 I1 I4 I6 J3 J5 K3 K6 K7 L6, then A8 E8 H8 L8). A kit written
by a tool may use all 96.

**The coupling** (**confirmed**, both ways). Choosing the shorts Emblem
Type *v* also sets side field 4 to *v* when *v* is under 2
(`0x41ee0`–`0x41f04`), and choosing Position on shorts *v* also sets side
field 1 to *v* when *v* is under 2 (`0x41f8c`–`0x41fb4`). The third option
(value 2) of either breaks the pair, so the emblem side is then free
(1, 2 or 3) and the number can be on 1, 2 or 3 (Nexxus). The coupling is
not applied when the editor opens, and retail data does not follow it:
side fields 1 and 4 are equal in 345 of the 686 retail kits (the
computer clubs and the placeholder rows).

**Nexxus's states** (2026-11-19, `LMAST-test-kits.iso`; the player's kit
in PCSX2 save states, read from the career's work block, `PlPworkTask`
entry 1 `+0` = `PlUnif`). Slot 1 had the home kit with every option on its
first value (white), slot 2 the away kit at the highest useful values:

| Kit | Collar | Socks design | Band | Side fields 0 to 5 | Shirt design |
|---|---|---|---|---|---|
| Home, option 1 everywhere | 0 | 0 | 0 | 0 0 0 0 0 1 | 90 |
| Away, the highest | 10 | 17 | 4 | 1 1 7 1 1 0 | 208 |

So menu option *n* is byte *n* − 1 for the collar, the socks and the band.
In the screenshots the shorts number was on the viewer's left leg with
the emblem on the right for the home kit (side field 4 = 0) and the other
way round for the away kit (side field 4 = 1).

**Retail data** (**empirical**, `UNIFORM_LIST` teams 3 to 459: 114
licensed placeholder rows and 343 computer clubs, 260 with flag 1 and 83
with flag 3; counts over the 343 clubs, home, then away):

| Field | Home | Away |
|---|---|---|
| Side 0 | 0: 306, 1: 37 | 0: 312, 1: 31 |
| Side 1 | 0: 242, 1: 101 | 0: 245, 1: 98 |
| Side 2 | 0: 261, 1: 32, 2: 3, 3: 8, 4: 13, 5: 4, 6: 2, 7: 20 | similar |
| Side 3 (front number) | 0: 337, 1: 6 | 0: 301, 1: 42 |
| Side 4 | 0: 111, 1: 229, 2: 3 | 0: 115, 1: 226, 2: 2 |
| Side 5 | 0: 21, 1: 194, 2: 128 | 0: 18, 1: 198, 2: 127 |
| Collar (kit 4) | 0: 106, 1: 26, 2: 98, 3: 27, 4: 47, 6: 4, 7: 35 | similar; no collar 5 or above 7 |
| Captain mark (kit 14) | 0: 170, 1: 11, 2: 12, 3: 53, 4: 97 | – |

Shirt number colour against the shirt's colour 1: 18 home and 15 away
kits clash in `COLOR_TBL`, and the contrast ratio is under 3 to 1 in 49
and 42. The editor has no rule for number or band colours: the only clash
rule it applies is the second kit's shirt colour 1.

**The game's own club presets** (`CEDITPRG.REL 0x150a0`: 32 presets of
`0x50` bytes, applied by `pwkTeam_SetUnif` at `0x20fc`; the rival's at
`0x15aa0`) all use shirt design 206, shorts 60 and socks 14; the home
side fields are `0 1 0 0 0 1` and the away `1 0 1 0 1 0`.
`set_default_uniform_style` (`SLES 0x2cf3a0`) defaults the emblem
styles to 0 and the shorts number position to 1.

`--mod kit-standards` writes these bytes for every computer club
([`LMASTER_MOD.md`](LMASTER_MOD.md#kit-standards)).

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

### Licensed or generated: the flag

**Confirmed.** `CUniformBuilder::Init` (`0x2c48b0`) copies `PlUnif` and
jumps on its first word, the row's flag, through the table at
`0x55a1c0` (`0x2c4ad8`–`0x2c4af8`): flag 2 and 4 set the builder's
mode (`+0x110`) to 0 (`0x2c4b0c`), everything else to 1 (`0x2c4b00`).
`CUniformLoader::Load` (`0x2c3080`) then calls `_load_licence`
(`0x2c2510`) for mode 0 and `_load_edit` (`0x2c2848`) for 1 and 2
(`0x2c33a8`–`0x2c3420`; 3 is the referee). So a club's kit is a licensed
one only because its row's flag is 2. **Empirical:** 114 of the 116
clubs in the licence table have flag 2 and no other row has it; the
two others, teams 140 (Siena) and 148 (Bologna), have flag 1 and
authored rows (Siena a black and white design, Bologna blue and red), so
they use generated kits although the table lists them. The other 424
clubs have flag 1 (341) or 3 (83); what 3 changes isn't known.

The 114 licensed rows are placeholders for everything else: 228 of
their 244 outfield kits are shirt, shorts and socks design 0, and 58
different home shirt colour sets cover the 122 clubs of teams 123–244.
Setting a licensed club's flag to 1 and writing its kit into the row
(`uniform.py set`) is all it takes to make it a generated kit, so
`random-sponsors` can then give it a sponsor.

### The sponsor and supplier logos on a generated kit

**Confirmed** from the code and PCSX2 states (2026-11-10).
`_load_edit` stores the team id and `PlUnif` `+4` and `+5` in the loader
(`+0x1778`, `+0x177c`, `+0x1780`) and makes three texture resources,
types 0, 5 and 7, for every club (`0x2c2ef0`–`0x2c2f58`; the types are
the word table at `0x55a248`). Type 5 is `SPONSOR_TEXTURE.PAC` and type 7
`SPONSOR_TEXTURE_S.PAC` (`CmnTex_005_NNN`, `CmnTex_007_NNN`, entry =
record number − 1; a supplier number of `0xd5` or more becomes `0xce`).
`_setup_texture_list` (`0x2c5340`) then keeps the real lists only for
team 1, team 2 and the VS teams (team ids `0x21f`–`0x22e`). The code
that takes the real sponsor and supplier lists is at `0x2c54e0`, and
`0x2c54bc`–`0x2c54d8` send any other club to the default list
(`0x2c5504`), which is copied into texture list slots 4 and 6. So a
computer club holds its logos but doesn't draw them. With that test
bypassed by `--mod random-sponsors`, a computer club draws both logos (**tested in
PCSX2**, Nexxus's screenshots, 2026-11-10; the test is in
[`LMASTER_MOD.md`](LMASTER_MOD.md#random-sponsors)).

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

## `UNIFORM_GK.TBB`: keeper kits made from the outfield kit

Your club, the rival and the VS teams have kits that are made at runtime,
not taken from `UNIFORM_LIST`. For these teams the game builds the keeper
kit from the outfield kit with `UNIFORM_GK.TBB`. Every other club uses the
keeper kit in its `UNIFORM_LIST` row (or its licensed kit).

`python SRC/uniform.py gk DAT/PLAYER` lists the table, and `setgk` edits
it.

### Who uses it

**Confirmed.** `UniformList_GetGKUniformData` (`0x2d3608`) is the only
reader: it builds the name `uniform_gk.tbb` (`0x55a888`) and reads the
file's two tables. It has two callers, and both call it only for teams 1
and 2 (your club and the rival) and teams `0x21f`–`0x22e` (543–558, the VS
teams; see [`INITTEAM_FORMAT.md`](INITTEAM_FORMAT.md)):

| Address | Symbol | What it shows |
|---|---|---|
| `0x2c4ab0`–`0x2c4ad4` | `CUniformBuilder::Init` | tests the team id (`+0x10c`) for 1–2 or `0x21f`–`0x22e` |
| `0x2c4b68`–`0x2c4bcc` | `CUniformBuilder::Init` | calls it with the team's outfield kit and no opponent, and takes only the result's collar (field 4) and captain mark (field 14) into the kit-style bytes at `+0x3b80` (`0x2c4c88`) in place of the stored keeper kit's |
| `0x113cd0`–`0x113ce8` | `ScheCallbackCommand_MatchBranch` | the same team-id test, for both teams of a match |
| `0x113d2c` | `ScheCallbackCommand_MatchBranch` | calls it with the team's outfield kit and the opponent's outfield and keeper kits, for the sides chosen for the match |
| `0x113d48`–`0x113d7c` | `ScheCallbackCommand_MatchBranch` | copies all 15 bytes of the result into the team's keeper kit (`PlUnif` side `+6`) before `PlGiTask::SetUni` |

So the keeper's designs and colours come from this table in a match. Screens
outside a match draw the keeper kit stored with the team.

### Layout

A `TBB1` container with two tables. **Confirmed** from
`UniformList_GetGKUniformData`:

| Table | Rows × size | Indexed by | Contents |
|---|---|---|---|
| 0 | 209 × 3 | outfield shirt design (`< 0xd1`, `0x2d379c`) | keeper shirt design, keeper shorts design, socks design |
| 1 | 38 × 66 | keeper shirt design (`× 0x42`, `0x2d3728`) | 6 colour schemes of 11 bytes |

The 209 and 38 rows are the sizes of `EDIT_UNIFORM_ORG_SHT` and
`EDIT_UNIFORM_GK_SHT`.

A scheme's 11 bytes go into these kit fields (`0x2d3a44`–`0x2d3a98`):

| Byte | 0, 1, 2 | 3, 4, 5 | 6, 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|
| Kit field | 1–3 shirt colours | 6–8 shorts colours | 10–11 socks colours | 12 shirt number colour | 13 shorts number colour | 14 captain mark |

The table has no collar (kit field 4), so it stays 0. `Init` and
`MatchBranch` both start from a zeroed kit.

### How a scheme is chosen

**Confirmed**, from `0x2d3718`–`0x2d3aac`:

1. Table 0's row for the outfield shirt design gives the three keeper
   designs. Each must be in range (keeper shirt and shorts `< 0x26`, socks
   `< 0x12`, `0x2d37bc`–`0x2d37dc`). Otherwise the function returns 0.
2. The 6 schemes of that keeper shirt design are tried in order (`0x2d3924`,
   `0x2d3aa0`). A scheme is skipped when its byte 0 (shirt colour 1)
   clashes in `COLOR_TBL` with the own outfield shirt colour 1 (kit field
   1). In a match, it is also skipped when it clashes with the opponent's
   outfield shirt colour 1 or keeper shirt colour 1.
3. The first scheme left is checked: bytes 0–9 must be `< 0x60` (96) and
   byte 10 `< 5` (`0x2d3970`–`0x2d3a38`). If it passes, it is copied into
   the kit and the function returns 1.

If every scheme clashes, or a check fails, the function returns 0. Both
callers ignore the return value and use the kit as it is. It then holds
what was written before the search: the designs from step 1, and colours
from table 0 row 0's keeper design (scheme 0, bytes 0–9) plus byte 10 of
the new design's scheme 0 (`0x2d3718`–`0x2d387c`). With the disc's data,
row 0 points at keeper design 35.

### The data

**Empirical**, from `uniform.py info` and `gk`:

- All 209 rows of table 0 are in range. They use 18 keeper designs,
  20–37, and the shorts design always equals the shirt design. Keeper
  design 35 serves 54 outfield shirts (0–37 and some others). Socks use 7
  designs.
- Keeper designs 0–19 are never chosen, and their 6 schemes are all zero.
- All 228 schemes are in range. In each of the 18 used designs, the 6
  schemes have 6 different shirt colours 1, so a clash always moves to a
  different colour.

`setgk` refuses a value that would make the game drop the row or the
scheme.

## Editing

```bash
python SRC/uniform.py set DAT/PLAYER/UNIFORM_LIST.TBB out/UNIFORM_LIST.TBB 3 home.outfield.1=A4 7 away.outfield.0=12
python SRC/uniform.py setexe ISO/SLES_541.51 out/SLES_541.51 home 0 outfield.backnumber=A8
python SRC/uniform.py setlicence DAT/PLAYER/PLPACK_HOME.HED out/PLPACK_HOME.PAC 0 outfield.backnumber=A8
python SRC/uniform.py setgk DAT/PLAYER/UNIFORM_GK.TBB out/UNIFORM_GK.TBB keeper.35.0.1=A8
```

`set` takes several teams, each followed by its fields. The editor's
Kits tab (`SRC/editor.py`) edits the same fields through the same code
(`set_row_field`, `apply_gk_edit`), offering only values the game keeps
(`uniform.edit_range`) and showing each colour as a swatch.

For a licensed club the tab also edits the descriptor's named fields
(`set_descriptor`). It reads the executable's copy, which the game draws
from, and writes each edit to both copies, logged as one `setexe` and
one `setlicence` per side and licence, so the two stay equal as on the
disc. The values it offers (`uniform.descriptor_spec`): the 96 colours
or off, collars 0–11, shorts number off/right/left, and for name type
(1, 2) and captain mark (0–4) the values the disc uses; the unknown
bytes 14–15 are read-only. `setlicence --data <in.PAC>` reads the
pack's data from an already edited copy instead of the one next to the
header, which stays in `DAT/` (the pack keeps its size).

`setexe`'s output is patched onto a disc image with
`python SRC/patch_disc.py patch <in.iso> <out.iso>
disc:SLES_541.51=out/SLES_541.51`. Edits to `UNIFORM_LIST.TBB` and
`UNIFORM_GK.TBB` go onto a disc with `patch_disc.py --copies`, because
`PRELOAD/SIMFILE0`–`6.PAC` hold copies of both
([Tested in PCSX2](#tested-in-pcsx2)).

## Tested in PCSX2

- **Unlicensed kit colour.** With `uniform.py set ... 3
  home.outfield.1=A4 home.outfield.3=A4` (Birmingham's home shirt colours
  1 and 3, from I3 blue to A4 red), patched with `patch_disc.py --copies`
  into `UNIFORM_LIST.TBB` and its 7 copies in `PRELOAD/SIMFILE0`–`6.PAC`,
  the launcher's Uniform Viewer showed Birmingham in a red shirt with white
  panels and trim instead of blue. The shorts and socks were unchanged. The
  viewer lists Birmingham as an "original team" (`オリジナルチーム`).
- **Through the editor's Kits tab** (Nexxus's report): Birmingham's home
  outfield kit set to shirt L3, shorts F3, socks B3, numbers B3/A4, the
  home keeper kit to shirt I4, shorts D3, socks A3, numbers A3/G8, and
  the away shirt colour 1 to B1 (21 fields), built with the editor's
  Build disc (`--copies`, so the `SIMFILE` copies too): the changes
  showed in game.
- **Licensed number colour.** AC Milan, a "licence team"
  (`ライセンスチーム`), as described above: the executable's copy of the
  descriptor sets the colour of the shirt number.
- **Licensed kit in a match, through the editor's Kits tab** (Nexxus's
  report): AC Milan's home outfield back number, shorts number and front
  number colours set to L3 (pink), in both copies (`setexe` and
  `setlicence`, built with Build disc). In a match against Juventus the
  back numbers and the shorts numbers were pink. No number showed on the
  shirt front, although the front number was no longer off. Because both
  copies were changed, which one a match reads is still open.
- **Keeper kit from `UNIFORM_GK`.** With `uniform.py setgk` setting bytes
  1, 2, 3, 4, 5, 6 and 7 (kit fields 2, 3, 6, 7, 8, 10, 11) of every
  scheme of keeper designs 20–37 to L4 (pink), and shirt colour 1 left
  alone, patched with `--copies` into `UNIFORM_GK.TBB` and its 7 copies in
  `PRELOAD/SIMFILE0`–`6.PAC` (disc `LMAST-gk-test.iso`), a new career's
  keeper (Dunstable Utd) wore pink sleeves, shorts and socks in a match,
  with the shirt's main colour unchanged.
- **Keeper scheme through the editor's Kits tab** (Nexxus's report): a
  `UNIFORM_GK` scheme edited in the Kits tab and built with Build disc
  showed on your club's keeper in a match.
- **Nexxus's report:** the club editor only lets you choose your outfield
  kits. The keeper kit is never chosen, so `UNIFORM_GK` is the only place
  it comes from.

## Still unknown

- What flag 3 changes (flags 1, 2, 4 are known), and the two unused bits.
- What the kit editor's items look like on the shirt ([above](#the-kit-editors-items-and-their-bytes)): the emblem types (2 is hard-wired for licensed kits, `CUniformBuilder::Init` `0x2c4bf0`, probably "no emblem overlay"); the encoding of the shorts number positions for a generated kit (the viewer calls 0 off, 1 right and 2 left, which Nexxus's states contradict: position 0 shows a number); what the number designs and the collars look like; per shirt design, which shirt colour the back and the sleeves take; and whether a computer club's emblem is drawn at all.
- Descriptor bytes 14 and 15, and what the pack's copy of the descriptor
  is used for: which copy a match reads (an edit to one copy only would
  tell), and whether a front number can show at all (a front number
  colour showed nothing on AC Milan's shirt, Nexxus's report).
- What the 121 rows with team id 0 are.
- The kit editor's per-supplier lists ([above](#the-kit-editors-designs-per-supplier)): that the game offers exactly those designs (read in the code, not yet seen in the editor), the Japanese release's addresses, and which of the 32 palette slots is greyed out.
- What the keeper kit stored with your club holds, and whether screens
  outside a match show it rather than the `UNIFORM_GK` kit (the code says
  they should; not checked).

## Checking the claims

```bash
python SRC/uniform.py info      DAT/PLAYER ISO/SLES_541.51   # check everything
python SRC/uniform.py show      DAT/PLAYER 3                 # Birmingham's kits
python SRC/uniform.py licensed  DAT/PLAYER ISO/SLES_541.51   # the 116 licensed kits
python SRC/uniform.py clash     DAT/PLAYER A8                # colours that clash with white
python SRC/uniform.py gk        DAT/PLAYER 35                # keeper design 35 and its schemes
python SRC/uniform.py roundtrip DAT/PLAYER/UNIFORM_LIST.TBB  # re-pack all 661 rows
python SRC/kiteras.py   info      DAT                         # the per-supplier lists, read from SIMPRG.REL
python SRC/kiteras.py   selftest  DAT                         # kit-eras and kit-standards: the code against the plan (the editor's items and bytes)
python SRC/sles_disasm.py ISO/SLES_541.51 syms CUniformBuilder  # the builder's functions (the editor's own code is in SIMPRG.REL: snr2.py dis ISO/DLL/SIMPRG.REL 0x109d98 40 --sles ISO/SLES_541.51)
python SRC/tbb.py roundtrip     DAT/PLAYER/UNIFORM_GK.TBB    # the container re-writes
```
