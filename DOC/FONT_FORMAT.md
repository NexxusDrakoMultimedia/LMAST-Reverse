<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Fonts: glyph tables, atlases and how text is laid out

All text in the game is drawn from bitmap pictures, which this doc calls
atlases. The text of language slots 1 to 6 (English, French, German,
Italian, Spanish and the unused slot 6, see
[`MBB_FORMAT.md`](MBB_FORMAT.md#languages)) is drawn from three of them
(`FONT_20_A`, `FONT_8_A`, `FONT_8_B` in `DAT/0SYSTEM`). A picture holds only pixels. Where each glyph sits in the
picture, how wide it is, how tall the font is and which byte draws which
glyph are all data in the executable. So a new face can be fitted in two
ways: draw it into the same rectangles, or move the rectangles by
patching the executable.

The Japanese language (language 0) uses other machinery: fixed-size cells
and Shift-JIS lookup tables (`FONT_ASCII`, `FONT_KANJI`). The PAL
executable carries that code and its tables too, but only language 0
reaches it. Folder overview: [`0SYSTEM_DIR.md`](0SYSTEM_DIR.md).

Tools: `python SRC/font.py info ISO/SLES_541.51 DAT/0SYSTEM` reads and
checks the fonts. `fontmod.py` draws a new face into font 0; it is the
switch `modern-font` ([`LMASTER_MOD.md`](LMASTER_MOD.md#modern-font)), and
its character table (`CHARS`) holds the bytes that draw a letter or sign
other than cp850's (the table below, except the pad buttons, the euro
sign with a small s and the blank cells).

## The files

| File | Picture | Drawn by | Notes |
|---|---|---|---|
| `FONT_20_A.SVR` | 256x256, 4 bpp, swizzled | European font 0, the main text of languages 1–6 | the Japanese disc's copy differs |
| `FONT_8_A.SVR` | PAL 128x128 swizzled; Japanese 64x64 linear | European font 1 (small capitals) | the two builds' pictures and tables differ |
| `FONT_8_B.SVR` | 128x128, 4 bpp, swizzled | European font 2 (small full set) | picture and table identical in both builds |
| `FONT_ASCII.SVR` | 256x256, 4 bpp, swizzled | language 0: half-width letters and katakana | identical in both builds |
| `FONT_KANJI.SVR` | 1024x1024, 4 bpp, linear | language 0: full-width kana, kanji | identical in both builds; two glyph sets in one picture |
| `FONT_KANJI_A.SVP`, `FONT_KANJI_B.SVP` | 80 bytes | nothing | copies of the two palettes of `FONT_KANJI` (below) |

LoadTexture (`0x149108`) picks the list: language 0 loads `font_kanji`,
`font_ascii`, `font_8_a`, `font_8_b` (list `0x35d400`), the other
languages `font_20_a`, `font_8_a`, `font_8_b` (list `0x35d458`).
**confirmed**. Each file is read through the SVR header
(`nnuTexinfoCreateBySvr` `0x165840`), so the game code holds no size for
the European fonts.

## How a text byte becomes pixels (European build)

1. A string reaches the font object `CFont_fc_euro`. Strings the windows
   and menus queue (`CSort2d::EntryFont` `0x1fe7b0`) are drawn later by
   `CEtcSort2d::CallFont` (`0x14bb40`) through `Print` (`0x304540`).
   Message text (`CallMessage` `0x14bf98`) goes one code at a time
   through `Msg::CMsgManager::Print` to `PutChar` (`0x304b08`). **confirmed**
2. Both end in `sbZenFontPrint` (`0x313bf8`). The European build's code
   mode is 1, so `sbZenFontIsSjis` (`0x313538`) is always false and the
   1-byte branch runs: `sbFontConvrtAsciiString` (`0x3131b8`) turns each
   byte into a glyph code through the font's 256-byte map, then
   `sbFontPuts` (`0x3123c0`) draws. **confirmed**
3. `sbFontPuts` looks the glyph code up in the font's record table (below)
   and draws one textured rectangle per glyph, then moves on by that
   glyph's advance times the zoom plus the tracking.
   **confirmed** (`0x312600`–`0x312918`, quad routine `0x311b00`)
4. The zoom is the text size divided by the font's height: a 20-pixel
   line of font 0 is drawn at 20 / 26 = 0.77 of the picture's size
   (`GetFontScale` `0x1227c8`, `DispStringSimple` `0x2749f0` multiplies by
   `0x3f44ec4f`, 20/26, for type 0). Tracking is added after the zoom, so
   it doesn't scale with the text. **confirmed**

The same advance sums decide whether text fits: string width
(`sbZenFontGetStrDispWidth` `0x3137f0` through `GetDisplayWidth`
`0x304a08`), centring and right alignment (`GetPositionFromRectLayout`
`0x304a28`), the shrink-to-fit of `CalcFontFrame` (`0x122850`), list
windows (`WS::CFcEuro_ListWindow::GetFontWidth` `0x277988`) and message
word wrap (`CMsgBody::AddNewLineEscapeEU` `0x30a078`, one glyph at a time
through `GetDisplayWidthOne`). So **text fit depends on the advances in the
executable, not on the pictures**. **confirmed**

## The three European fonts

| Font | Picture | Descriptor | Records | Character list | Glyphs | Height | Space | Default tracking |
|---|---|---|---|---|---|---|---|---|
| 0 | `FONT_20_A` | `0x3a7670` | `0x563990` | `0x564a48` | 214 | 26 | 8.0 | 0 |
| 1 | `FONT_8_A` | `0x3a7680` | `0x564bf8` | `0x5656d8` | 139 | 8 | 4.0 | 2.0 |
| 2 | `FONT_8_B` | `0x3a7690` | `0x5657f0` | `0x5666b8` | 189 | 8 | 8.0 | 1.0 |

All **confirmed** (PAL addresses). The descriptors are listed by the
pointer array at `0x3a76b8`, the lists by `0x3a76c8`, the counts (u32) by
`0x566838` and the default tracking pairs (f32 x, f32 y) by `0x3a76a0`.
`CFont_fc_euro::SetTexList` (`0x303c28`) wires them up from these arrays;
`SetFont` (`0x304850`) selects one (types 0–2 only). Fonts 0, 1, 2 use
the pictures in the order of the file list `0x35d458`. The tables sit in
`.rodata` (file offset = address − `0xff000`), each table directly
followed by the next list, so none can grow in place.

The Japanese executable has the same three descriptors at `0x3a3358`,
`0x3a3368`, `0x3a3378` (`gamever.py` maps the pointer arrays). Font 2 is
byte for byte the PAL one; fonts 0 and 1 are not: the Japanese
`FONT_8_A` has 62 glyphs (digits and letters, the lower case sharing the
capitals' cells) and a space of 3.0, and font 0 is not loaded when the
language is 0 (it is loaded for the other languages, which the Japanese
disc doesn't offer).

### Descriptor (12 bytes)

| Offset | Type | Field |
|---|---|---|
| 0x00 | u32 | address of the first glyph record (glyph code 4) |
| 0x04 | f32 | advance of a space (glyph code 3), in pixels |
| 0x08 | u32 | height; only the low byte is read. Every glyph's quad is this tall |

`sbFontSet1ByteFont` (`0x312198`) copies it into the font and sets the
font's mode word to 0 (1-byte glyphs). **confirmed**

### Glyph record (20 bytes)

| Offset | Type | Field |
|---|---|---|
| 0x00 | f32 | u0, left edge, normalised: pixel / picture width |
| 0x04 | f32 | v0, top edge |
| 0x08 | f32 | u1, right edge |
| 0x0c | f32 | v1, bottom edge |
| 0x10 | f32 | advance in pixels; also the quad's width |

The record of glyph code c is at `table + (c − 4) * 20`
(`sbFontPuts` `0x31262c`–`0x312638`; the advance is read by `0x312028`).
The quad runs from (x, y) to (x + advance * zoomX, y + height * zoomY) and
the texture coordinates come from the record alone: the 1-byte path never
reads the picture's size. **confirmed**

Checked over all 542 records of the PAL executable: the advance equals
the rectangle's width in pixels in 542 of 542, and every edge is a whole
pixel in 542 of 542. **empirical** (`python SRC/font.py info`)

### Character list and the byte → glyph map

The list holds one u16 per glyph, a cp850 byte, in the order of the
records. `sbFontSetDefault` (`0x312220`) turns it into the font's 256-byte
map: the byte `list[i]` gets glyph code `i + 4` (a later duplicate
overwrites an earlier one), then byte `0x20` gets 3 and `0x0a` gets 2.
`sbFontConvrtAsciiString` replaces each string byte by its map entry when
that is not 0 and leaves it alone otherwise. **confirmed**

| Glyph code | Meaning |
|---|---|
| 0 | end of the string |
| 1 | escape: one parameter byte follows and picks a draw style (`0x3120e0`; the styles aren't decoded) |
| 2 | new line: back to the start, down by height * zoomY + vertical tracking |
| 3 | space: advance is the descriptor's float, nothing is drawn |
| 4 and up | glyph record `code − 4` |

A byte with no list entry keeps its own value as the glyph code, so it
draws record `byte − 4` with no bounds check (8 of font 0's 36 such
bytes reach past the end of its table). `Print` and `Printf` guard
against that: `CheckErrorCode` (`0x3044b0`) replaces every unlisted byte
(except space) by a space. `PutChar`, the message path, doesn't call it.
**confirmed** Font 0 has no glyph for 36 of the codes `0x04`–`0xff`:
`0x04`–`0x09`, `0x0b`–`0x0f`, `0x14`–`0x1f`, `0x7f`, `0xc0`–`0xc3`,
`0xda`–`0xdc`, `0xdf`, `0xf2`, `0xfa`, `0xfe`, `0xff`. **empirical**

Every text byte of all six European languages (65,964 to 66,044 records
each in `MES.PAC`) has a glyph in font 0; the only bytes below `0x20`
used are `0x0a` and the four button icons `0x10`–`0x13`. Font 1 lacks
23 to 28 of the used bytes (so it isn't a general text font), font 2
lacks only the four icons and `0xb3` (the euro sign). **empirical**
(`python SRC/font.py coverage ISO/SLES_541.51 DAT/MESSAGE/MES.PAC`)

## Font 0 (`FONT_20_A`)

The glyphs are laid out freely, not on a grid, and the rectangles are in
no byte order: the first row of the picture, left to right, holds
`0x21 0x22 0x23 0x24 0x25 0x26 0x27 0x2a 0x2b 0x2d 0xf0 0x2f 0x5c 0x3a
0x3b 0x3c 0x3d 0x3e 0x3f 0x40 0x60 0x7c 0x5e`, which draw the shapes
`! " # $ % & ' * + -`, a short bar (`0xf0`), `/ \ : ; < = > ? @`, a
backtick, a broken bar `¦` (`0x7c`) and `^`. The list in the executable
says which byte each rectangle is. Records 0–93 are the printable ASCII
bytes `0x21`–`0x7e` in order, records 94–189 are the bytes from `0x80` up
in cp850 order (byte `0x80` is Ç, `0x81` ü, `0x82` é ...) with gaps for
the bytes the font lacks, and the last 24 records (190–213) hold bytes
that draw a shape other than cp850's or nothing (below). **empirical**
(`python SRC/font.py dump`).

| Fact (all **empirical**, over the 214 records) | Value |
|---|---|
| Rectangles | 201 are 26 tall (starting at y = 0, 25, 50, 75, 101, 127, 153, 179, 205, 231: rows overlap by one line, which has no ink), 13 are 7x6 blank placeholders in the free corner (x 227–255, y 153–177) |
| Widths | 6 to 19 pixels, whole numbers; 46 glyphs are 12 wide, 28 are 11 wide |
| Empty rectangles | 17: the 13 placeholders (bytes `0x9e`, `0x9f`, `0xc4`, `0xc5`, `0xc8`, `0xc9`, `0xd5`, `0xef`, `0xf1`, `0xf4`, `0xf5`, `0xf6`, `0xf9`) and four blank 14x26 ones (bytes `0xb0`, `0xb1`, `0xb4`, `0xb9`) |
| Past the picture | 15 rectangles of the last row end at v1 = 257/256, one line below the picture (that line has no ink) |
| Ink | 18,940 inked pixels, all inside a rectangle; 3 pairs of records share a rectangle |
| Vertical metrics, inside the 26-row rectangle | caps and ascenders rows 3–21 (19 tall), x-height top at row 8, baseline below row 21, descenders down to row 24, accented capitals from row 1, round letters overshoot by one row |
| Weight | vertical stems 2 px, horizontal bars about 2.25 px, 1 px side bearing on each side in most glyphs |

Bytes that draw a shape other than cp850's, or that aren't text:

| Byte | Draws |
|---|---|
| `0x10`, `0x11`, `0x12`, `0x13` | the pad buttons: circle, cross, triangle, square (`mbb.py`'s `EU_BUTTONS`) |
| `0xb3` | the euro sign, used 11 times in each language's messages (cp850: a box-drawing bar) |
| `0xba` | a euro sign with a small s |
| `0xb2` | a small middle dot `·` (cp850: a shade block) |
| `0xbf` | a yen sign `¥` (cp850: a box-drawing corner) |
| `0xcd`, `0xcc`, `0xbb`, `0xbc`, `0xca`, `0xcb`, `0xce`, `0xd9` | ć, Ć, Š, š, Ž, ž, Č, č (cp850's box-drawing bytes) |
| `0xfb`, `0xfc`, `0xfd` | superscript 1, 2, 3 (cp850 has 1, 3, 2) |
| `0xb0`, `0xb1`, `0xb4`, `0xb9` | blank cells (cp850: shade blocks and box-drawing characters) |

`0xa7` (º) and `0xab`, `0xac`, `0xf3` (½, ¼, ¾) are cp850's own
characters; `º` is drawn as a small ring in the top rows of its cell.
What each of these bytes draws is read from the picture and the list,
not seen in the running game. The messages in `MES.PAC` use none of
`0xba` and the Central European letters.

## Fonts 1 and 2 (`FONT_8_A`, `FONT_8_B`)

Both are pixel fonts with an 8-pixel height. `FONT_8_B` (189 glyphs) is a
complete set of 8x8 cells on a gapless 16-column grid, every advance 8,
with a baked shadow (alpha 83 at the right and bottom). It has the
character set of font 0 without the icons, euro sign and Central
European letters (25 bytes fewer). `FONT_8_A` (139 glyphs) holds capitals
and digits in 8x8 cells at a pitch of 10 x 9 from (1, 1), advance 8 (4 for
five narrow glyphs); lower-case bytes draw the capitals' cells. Its list
repeats three bytes (`0x8e`, `0xa2`, `0xa5`): the later entry wins, so
`0x8e` draws the cell at (81, 28) and `0xa5` the 8-wide cell, not the
narrow one. **empirical**

Which windows and layouts use fonts 1 and 2 isn't known. A layout picks
the font through `CSE_FONT_UTIL::GetFontType` (`0x122608`): flag bit 0
gives type 1, else flag bit 1 gives type 2, else type 0. **confirmed**
The developer print style table at `0x35d3c0` (`pxSetFontStyle`
`0x146ec0`: four {font, width, height} records) is not part of this: it
is used by one function of `GAMEPRG.REL` only. **confirmed**

## Palette and picture format

The glyphs use the picture's own 16-entry palette (the European build
never overrides it: `TranslatePalette` `0x3042c8` is empty); the text
colour comes from the material, not the palette. **confirmed** So every
inked pixel's colour must be white (checked: 0 inked pixels of the three
European pictures are not) and the anti-aliasing is the alpha ramp:

| Picture | Alpha levels (index → raw GS alpha, 0x80 = opaque) |
|---|---|
| `FONT_20_A` | 16 levels in a permuted order: index 5 is 0x80, index 0 is 0; raw 00 3f 21 0b 57 80 12 33 19 67 5f 28 77 4f 6f 47 |
| `FONT_8_A` | indices 12–15 only: alpha 0 / 75 / 151 / 255 in `svr.py`'s 0–255 scale |
| `FONT_8_B` | indices 12–15 only: alpha 0 / 83 / 83 / 255 in `svr.py`'s scale |

**empirical** (`svr.py` shows `a * 255 // 128`; a writer must emit the
GS value). The PAL pictures are swizzled (`svr.py` handles it).

## The Japanese build's fonts (language 0)

`SetTexList` builds three 2-byte fonts (`sbFontSet2BytesFont` `0x3121c0`,
mode word 1) and the two 1-byte fonts 8_A and 8_B. A 2-byte font has no
records: a cell index n comes from the code
(`((b0 & 0x7f) << 8 | b1) − 4`), cells per row = picture width / cell
width, the cell is at (n mod cells per row, n / cells per row), and the
quad is one cell wide (`sbFontPuts` `0x31263c`–`0x3127f8`, the Japanese
build's `0x30fab4`...). **confirmed** The advance is the cell width times
the zoom (`0x312028`), so **a 2-byte font has no per-glyph widths**.
**confirmed**

| Font | Picture | Cell | Grid | Table | Codes |
|---|---|---|---|---|---|
| zen 0 | `FONT_ASCII` | 11x26 | 23 x 9 | T0 `0x561ca8` (unsorted, linear search) | 184 |
| zen 1 | `FONT_KANJI` plane A | 20x26 | 51 x 39 | T1 `0x561e18` (`0x8140`–`0x9086`, ascending) | 1,989 |
| zen 2 | `FONT_KANJI` plane B | 20x26 | 51 x 39 | T2 `0x562da8` (`0x9087`–`0x9872`, ascending) | 1,485 |

Each table entry is two bytes, lead byte first; cell n draws the table's
n-th code (`sbCodeConvert2bytes` `0x3132b0`). The cell sizes are the byte
pairs at `0x3a7260` and `0x3a7268`; the table sizes are the immediates in
`SetTexList`. **confirmed** The Japanese build's addresses are
`0x55dfa8`, `0x55e118`, `0x55f0a8` and `0x3a2f48`.

- **`FONT_ASCII`**: cell 0 is the space, cells 1–94 the printable ASCII
  shapes in order, 95–157 the half-width katakana, 158–183 the 26 voiced
  katakana (the bytes `0x02`–`0x08`, `0x0b`, `0x0c`, `0x0e`–`0x1a`,
  `0x1c`–`0x1f` of the message text); cells 184 on are blank. Ink is
  inside the 23 x 9 grid (253 of 256 pixels wide, 234 of 256 high).
  **empirical** (`font.py info`: 183 of 183 cells after the space have ink)
- **Half-width text** goes through the byte table `ByteTo2Byte` (256
  pointers at `0x3a7270`, the Japanese build `0x3a2f58`) to a full-width
  Shift-JIS code, which T0 turns into a `FONT_ASCII` cell
  (`sbZenFontPrint` `0x313bf8`). Some bytes show other shapes: `0x5c` the
  yen sign, `0x7e` an overline, `0x2d` the katakana long-vowel mark `ー`
  (the hyphen cell, 13, is reached by no byte), `0x27` and `0x22` curly
  quotes. The slot for `0x60` doesn't decode to a T0 code (the left
  quote, cell 64, is unreachable). There are no accented Latin letters.
  **empirical**
- **Half-width advance** is the cell width minus 1 times the scale, 10
  pixels at scale 1 (`sbZenFontPrint` subtracts it for font 0;
  `sbZenFontGetCharDispWidth` `0x313708` returns the same). Read from the
  code only. A full-width character advances 20.
- **`FONT_KANJI`** holds two glyph sets in one picture, as two 2-bit
  planes: each 4-bit pixel is a pair of levels (A, B) and the 16 indices
  cover all 16 pairs. The picture's own palette shows plane A. The B
  palette is the 64 bytes at `0x563950` (Japanese build `0x55fc50`), which
  `SetTexList` loads into the second font's texture copy. The unused
  `FONT_KANJI_A.SVP` and `FONT_KANJI_B.SVP` are byte for byte these two
  palettes, so editing the files on disc changes nothing. **confirmed**
  The grid is 51 x 39 cells, 1,020 x 1,014 of the 1,024 x 1,024 pixels;
  plane A has ink in 1,988 of its 1,989 cells (all but the blank space),
  plane B in all 1,485 table cells and in 76 more (cells 1,485–1,560, an
  unused continuation of the level-2 kanji that no table reaches).
  **empirical** (`font.py info`)
- Three T1 codes (`0x87a0`–`0x87a2`) aren't valid cp932; their cells hold
  the game's own symbols. **empirical**

## What a replacement face must keep

For the European fonts (PAL; the Japanese build's fonts 0 and 1 have their
own tables). Checked against the code and the data, and tried in the game
for font 0: `fontmod.py` follows every row below, and the disc it builds
shows the new face with the menus and the pre-match screen fitting
(**Tested in PCSX2**, Nexxus's report, 2026-11-13). The longest list
names, the news and match screens and the pad icons have not been looked
at yet ([`LMASTER_MOD.md`](LMASTER_MOD.md#modern-font),
[`TESTING.md`](../TESTING.md)).

| Item | Why | Consequence |
|---|---|---|
| White ink, 16-entry palette, alpha in the GS scale (0x80 opaque) | the picture's own palette is used; the material colours the text | draw in white with an alpha ramp; index 0 transparent |
| A glyph's ink stays inside its rectangle | the quad is exactly the rectangle's UVs | either fit the face to the existing rectangles or patch the records (all three tables, in both executables) |
| The texels just outside every rectangle are blank | **empirical:** a build that left ink there showed stray pixels beside the glyphs in PCSX2, and the same face with the ring blank showed none (**tested in PCSX2**, Nexxus's reports, 2026-11-14); this fits a bilinear filter reading past the edge, but the sampler itself is not read from the code | the game's own picture keeps that ring blank (4 of 214 rectangles have ink just outside); keep glyph ink out of the rows where rectangle rows overlap and out of the edge columns that face a neighbour, or leave a blank column between neighbours |
| Advance = rectangle width | the quad is advance * zoom wide and shows u0–u1 | a changed advance needs a changed u1 too, or the glyph stretches; fold kerning and side bearings into the width (any whole or fractional number of pixels) |
| One height per font (26, 8, 8) and baseline baked into every glyph | the quad's height is the descriptor's byte for every glyph | caps rows 3–21, x-height from 8, descenders to 24 of 26 |
| A record for every list entry; no new unlisted bytes | the code space is list index + 4 and nothing bounds-checks it | the record count can't grow in place (tables are followed directly by the next list); a table can be moved if its 20-byte stride and descriptor pointer are kept |
| The button icons (`0x10`–`0x13`) and the euro sign (`0xb3`) | the messages use them | keep their shapes |
| The 17 empty rectangles stay blank | 13 are stretched 26 tall, 4 are real blank cells | leave them |
| Texture coordinates up to 1.0 | 15 rectangles reach 257/256; whether the sampler clamps or wraps is not read | a new layout should keep v1 ≤ 1.0 |
| The small fonts are 8x8 pixel art | height 8, advance 8 | a new face would have to be hinted by hand; leave them alone |

The patchable data (records, lists, counts, descriptors) is in `.rodata`
and `.data` of the executable, which `patch_disc.py` already writes
(`SLES_541.51`). A patch needs each build's own addresses: the Japanese
build's font 0 and 1 tables differ from PAL's.

## Still unknown

- How the picture is sampled: the GS filter and clamp settings, the
  texture size fields (`TEX0` TW/TH) and the screen-coordinate scaling
  table at `0x365b98` (filled at run time) were not read. They decide how
  a higher-resolution atlas would look at the 20/26 scale and what the 15
  rectangles that reach one line below the picture sample.
- Whether a larger atlas fits: the European fonts go to VRAM at
  `0x3f0000` (`nnPrepareTextureMemoryPS2`); the headroom was not checked.
- Which windows, layouts and messages use fonts 1 and 2 and at what
  sizes (`DispStringSimple` has seven other callers; `SetFont` is reached
  through the vtable), so whether changing only font 0 changes all
  visible text.
- The tracking flags: `GetFontTrack` (`0x122688`) was read as bits 16–23
  and 24–31, but the neighbouring helpers use other bit pairs.
- What the draw styles of the escape code 1 do (shadow, outline; the
  routines at `0x3115d8`, `0x311a98`, `0x3116f0`, `0x311cd0`).
- What `Msg::CMsgManager::Print` does with a byte outside the list (it
  skips `CheckErrorCode`), and a stray byte 1 to 3 in a string.
- Whether any overlay holds its own widths or draws glyphs another way.
- Whether a generated string uses `0xba` or the Central European
  letters (the messages don't), and whether any visible text uses
  `FONT_8_A`'s repeated bytes.
- In the game: that editing the character list (as opposed to the records
  and the picture, which work) changes the drawn text, and a font patch on
  the Japanese build (none exists; `modern-font` is PAL only).
- Japanese: whether code `0x9087` (the first plane-B kanji) really goes
  to the plane-A font (the comparison at the Japanese build's `0x311188`
  reads as "greater than"); what a failed lookup draws; which characters
  of the Japanese text are in no table (level-2 kanji, the 76 unused
  plane-B glyphs); which screens use which of the fonts; the 10-pixel
  half-width advance on a screenshot; whether the Japanese text has
  ASCII bytes or full-width Latin; whether anything calls
  `CFont::ConvertHanToZen` (`0x302088` in the Japanese build); whether an
  overlay reads T1, T2 or the extra glyphs.
- How the Japanese `FONT_20_A` and `FONT_8_A` tables differ from PAL's in
  detail (the widths of about a quarter of the glyphs differ by a pixel).

## Checking the claims

```bash
python SRC/font.py info ISO/SLES_541.51 DAT/0SYSTEM
python SRC/font.py info ISO_JP/SLPM_663.16 DAT_JP/0SYSTEM
python SRC/font.py coverage ISO/SLES_541.51 DAT/MESSAGE/MES.PAC
python SRC/font.py dump ISO/SLES_541.51 0 glyphs0.csv      # write the CSV and PNG outside the repo
python SRC/font.py png ISO/SLES_541.51 DAT/0SYSTEM 0 rects0.png
python SRC/fontmod.py info ISO/SLES_541.51 DAT/0SYSTEM "RobotoCondensed[wght].ttf"   # the new face, read back through font.py's checks
```

`info` checks every record against its picture and prints `!!` for a
rectangle with an off-grid edge, a short rectangle with ink in it, ink
that isn't white, a list code of `0x100` or more, or a 2-byte table or
plane that doesn't fit its picture. The Japanese build's `FONT_8_A` has
96 inked pixels (about ten shapes, among them punctuation) and its
`FONT_20_A` 2 that no record reaches: left-over art, not an error.
`png` draws the rectangles over the picture (green with ink, red without).
