# MBB1 message files (`MESSAGE/MES.PAC`)

All of the game's text is in `DAT/MESSAGE/MES.PAC`, a named BINPAC (see
[`PAC_FORMAT.md`](PAC_FORMAT.md)) of **3,738 `.mbb` files**: 534 message
categories × 7 language slots, named `<category>_<language>.mbb`. The two
extra BINPAC columns repeat the category and language.

`python SRC/mbb.py info DAT/MESSAGE/MES.PAC` checks every file. `dump`
prints the text with the control codes shown as tags, and `csv` writes one
row per message with one column per language. `set` and `import` write
edited text back (see [Writing](#writing)).

The header, record layout, file naming, language numbers and escape opcodes
are **confirmed** from `SLES_541.51`. The text encodings are **empirical**,
checked against every record, except for the Japanese voiced-kana table,
which comes from the executable.

## Confirmed from the game code

| Address | Symbol | What it shows |
|---|---|---|
| `0x10e2f8` | `FC_EURO_LOCALIZE::Localize_MakeMessageFileName(int, char*)` | `sprintf(buf, "%d_%d.mbb", category, language)`; language is the global at `0x34defc` |
| `0x10e1c0` | `Localize_DefaultLanguage()` | maps `sceScfGetLanguage()` to the language slots below. PS2 Dutch/Portuguese fall back to English |
| `0x30cec0` | `Msg::CMsgCategory::AnalizeHeader(void*)` | checks magic `0x3142424d` (`MBB1`) |
| `0x30cf28` | `Msg::CMsgCategory::AddSubCategory(void*)` | keys the file by header `+0x08` in a map of sub-categories |
| `0x30d1c8` | `Msg::CMsgSubCategory::Initialize(void*)` | reads count `+0x0C` and data size `+0x10`, allocates `data_size − 3 × count` bytes for the strings, walks `count` records from `+0x20`, copies each string with a NUL, then `qsort`s `{u16 id, char*}` by id |
| `0x30d2f0` | `Msg::CMsgSubCategory::GetMessage(ushort)` | `bsearch` by id |
| `0x11de80` | `Msg::CMsgNotifyFontMisc::Evaluate` | escapes `0x20` (colour index → `clr::GetRGBA` via the table at `0x51b828`), `0x21` (restore colour), `0x2F` (new line) |
| `0x11e0b8` | `Msg::CMsgNotifyNameTag::Evaluate` | escapes `0xC1` (name via `Msg::GetGlobalVariable` → `WP::CMessageWindow::SetName`), `0xC2` (`EVS::FaceChangeReqOnEvent(slot, expression)`, only if `fcEuroDummy_IsFaceChangeEnable`), `0xC3` (`Talk_MesssageCallback_SetMotion(N)`, see [Reactions](#reactions-esc-0xc3)) |
| `0x30c0e0` | `Msg::CMsgNotifyVariableGet::Evaluate` | escapes `0x10`/`0x11`/`0x12`: category as u8/u16/u32, then a u16 variable id, looked up with `CMsgDecoder::GetVariable` |
| `0x531c28` | table used by `Param::plMisc_HanZenKana` | 32 Shift-JIS codes for bytes `0x00`–`0x1F` (voiced katakana, see below) |

`MOVIEPRG.REL` `0x32ec`–`0x3330` is the language menu. Its table at `0x4c288`
(`5 0 1 3 2 4 0`) gives each slot's position in the menu. Slot 6 shares
English's position, so the loop always stops at slot 1 first. **Slot 6 is
never selected.**

## Languages

| Slot | Language | Encoding |
|---|---|---|
| 0 | Japanese | Shift-JIS (cp932), plus the voiced-kana bytes below |
| 1 | English | DOS code page 850 |
| 2 | French | cp850 |
| 3 | German | cp850 |
| 4 | Italian | cp850 |
| 5 | Spanish | cp850 |
| 6 | unused | cp850. Mostly identical to English (64,455 of 65,889 shared ids), with some strings in other languages |

cp850 rather than cp437 is confirmed by characters that only it has: `0xB5`
Á, `0xE0` Ó, `0xE9` Ú, `0xD6` Í, `0xB7` À, `0xC6` ã, `0x9B` ø, `0x9D` Ø.

## Layout

All values are little-endian.

```
0x00  char[4]  "MBB1"
0x04  u32      category id (matches the file name)
0x08  u32      sub-category id; in MES.PAC, the language slot
0x0C  u32      record count
0x10  u32      data size = file size - 0x20 (includes the padding)
0x14  u32[3]   0
0x20  records, back to back:
        u16  id
        u16  length in bytes
        u8   text[length]      no NUL terminator
      then 0-3 zero bytes to a multiple of 4
```

Records aren't always in id order (9 categories aren't sorted), which is why
the game sorts them after loading. Ids are unique within a file except in two categories: category 0 has three copies of
ids 0–36, and category 570 has id 5051 twice, with different text. Because the
game `bsearch`es a `qsort`ed list, which copy it finds is undefined. `mbb.py
csv` keeps both copies and numbers them in its `copy` column.

## Text and escape codes

A record is plain bytes interleaved with escape sequences:

```
0x1B  u8 opcode  u8 n  u8 args[n]
```

Every escape in the archive follows this shape.

| Opcode | n | Args | Meaning | `mbb.py` tag | Count |
|---|---|---|---|---|---|
| `0x2F` | 0 | | line break | `\n` | 35,747 |
| `0x10` | 3 | u8 category, u16 variable | runtime variable (name, number, ...) | `{var:C:V}` | 50,920 |
| `0x11` | 4 | u16 category, u16 variable | same, wider category | `{var:C:V}` | 7,376 |
| `0x12` | 6 | u32 category, u16 variable | same | `{var:C:V}` | 126 |
| `0x20` | 1 | u8 colour | start colour (index into the colour table) | `{color:N}` | 2,834 |
| `0x21` | 0 | | restore the default colour | `{/color}` | 2,827 |
| `0xC1` | 2 | u16 name | speaker name shown on the message window | `{name:N}` | 4,167 |
| `0xC2` | 4 | u16 slot, u16 expression | portrait expression | `{face:S:N}` | 30,086 |
| `0xC3` | 2 | u16 reaction | the speaker's body reaction (motion), see below | `{react:N}` | 15,297 |

A variable's category is a message category (`1` is the global one, set up by
`fcEuroRootTask_SetupGlobalMessageCategory`), and the game fills in its
variables at runtime with `CMsgCategory::SetVariable`. For example,
`{var:1:7}` is the player's name in the salesman dialogue. The variable ids
are not message ids.

Speaker names 100–106 match the symbolic names in category 2 (`100`
RIVAL_OWNER_NAME, `101` SECRETARY, `103` REPORTER, ...). The other ids used
(2034–3167 and 4001–4099, e.g. `4091` for a travelling salesman) aren't
named in any message file, so they probably index a table in the code.

### Reactions (`ESC 0xC3`)

`{react:N}` makes the speaking character play body reaction N in the 3D
"talk" scenes: one-to-one meetings with a player or staff member. The
chain is **confirmed**:

| Address | Symbol | What it does |
|---|---|---|
| `0x11e198` | in `Msg::CMsgNotifyNameTag::Evaluate` | reads the u16 with `GetEscapeWord` and calls `Talk_MesssageCallback_SetMotion(N)`. The call is a `jal 0` that the loader patches (see [`SNR2_FORMAT.md`](SNR2_FORMAT.md#calls-from-sles_54151-into-the-overlays)) |
| `SIMPRG.REL 0xc120` | `Talk_MesssageCallback_SetMotion(int)` | does nothing if no talk scene is active (`0x1cd1c8`) or N is the current reaction (`0x1cd1cc`). Otherwise calls `CTalkImplement::setReaction(who, N, …)` and stores N |
| `SIMPRG.REL 0xbd20` | `CTalkImplement::setReaction(char*, int, bool×4)` | `CLoader::getMotion(loader, 0, 0, N, 0)`: entry N of the merge file in the scene loader's slot 0 |
| `SIMPRG.REL 0xbff8` | `CTalkImplement::loadReactionData(int posture)` | loads that slot: posture 0 → `BG/HUMAN_MOTION_REACTION_STAND.MRG`, 1 → `..._SIT.MRG` |

So N is an **entry index into a motion pack, and which pack depends on the
scene's posture**. The two packs don't line up:

| N | Sitting (`_SIT.MRG`) | Standing (`_STAND.MRG`) |
|---|---|---|
| 0–3 | `mendan_Asit_ang_001`–`004` (angry) | `mendan_Atati_ang_001`–`004` |
| 4–7 | `hap_001`–`004` (happy) | `hap_001`–`004` |
| 8 | `nod_001` | `in_001` |
| 9 | `sad_001` | `nod_001` |
| 10–12 | `sad_002`–`004` | `sad_001`–`003` |
| 13 | `mendan_sit_001` | `sad_004` |

(`mendan` is 面談, "interview/meeting"; `tati` is 立ち, "standing".) The
packs end with entries without the `A` prefix (`mendan_sit_001`,
`mendan_sit_ang_001`, `mendan_sit_sad_001`; `mendan_tati_001`,
`mendan_tati_ang_001`, `mendan_tati_sad_001`). No text uses them as reactions, and what they're for isn't
traced.

The talk managers in `SIMPRG.REL` pass the posture. Contract, dismiss,
move, promise, promise-result, staff-retire and withdraw talks sit
(posture 1). `CTalkNormalManager` and one path of `CTalkPlayerRetire`
stand (posture 0). The text is written for the right pack: in normal talk
(categories 500–505, standing) `{react:9}` goes with neutral lines ("This new
formation – I'm well up for it", a nod), and in contract talk (sitting)
it goes with refusals ("I can't renew my contract for that sort of
figure", `sad_001`). The `{face}` expression beside each reaction agrees:
41 with angry, 51 with happy, 1 with nod, 31 and 21 with sad.

The escape appears only in the talk categories (500–599, 800–899,
1100–1199), 2,185 times in every language slot, with values 0–12. 3 is
never used. `setReaction` also does something extra for reaction 4 when
standing, and for 2 or 4 when sitting (it sends a message to a second
scene object named at `+0x588`); what that looks like in game isn't
known.

For editing: the same N means a different motion in the two packs, so what
N shows depends on the scene's posture. The text only uses 0–12.
Standing entry 13 (`sad_004`) is a reaction nothing uses. Whether
`CLoader::l_get` (`0x119540`) bounds-checks N hasn't been checked.
The same text can't be moved between a sitting and a standing scene
without re-choosing its reactions.

The two other name-tag escapes resolve the same way: `0xC1` calls
`Msg::GetGlobalVariable(char* buf, ushort id)` to fetch the speaker name
before `SetName`, and `0xC2` calls `EVS::FaceChangeReqOnEvent(slot,
expression)` (`SIMPRG.REL 0x13ac60`) when
`fcEuroDummy_IsFaceChangeEnable()` allows it.

### Other control bytes

- **`0x0A` / `0x0D` (raw).** Found next to `ESC 0x2F` in some strings (4,129
  LFs in the EU languages, 27 CR+LF pairs in Japanese). Probably left over
  from the source text. Their effect on display hasn't been checked.
  `mbb.py` shows them as `{lf}` / `{cr}`.
- **`0x10`–`0x13` in the EU languages** are the pad buttons (○ × △ □). The
  Japanese text spells the same buttons in Shift-JIS, e.g. `100001` id 810:
  EN `\x10button` / JP `(○)`.

### Japanese voiced kana

Name lists (clubs, countries, cities: categories 3, 4, 10, 11, 100003,
100006, 100961, ...) are written in single-byte half-width katakana
(`0xA1`–`0xDF`). Bytes `0x00`–`0x1F` hold the voiced forms, which JIS X 0201
has no single byte for. `SLES_541.51` `0x531c28` maps each byte to its
full-width Shift-JIS character:

| | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `0x0_` | · | · | ガ | ギ | グ | ゲ | ゴ | ザ | ジ | · | · | ズ | ゼ | · | ゾ | ダ |
| `0x1_` | ヂ | ヅ | デ | ド | バ | ビ | ブ | ベ | ボ | パ | ピ | · | プ | ペ | ポ | ヴ |

`·` is a full-width space in the table. `0x09`, `0x0A`, `0x0D` and `0x1B`
(tab, LF, CR, ESC) are skipped. For example, `b2 dd 04 d7 dd 13` is
イングランド (England). `mbb.py` writes these in half-width form (`ｸﾞ`) to
match the half-width characters around them.

## Categories

The category number says roughly what a file contains (English samples):

| Range | Files | Contents |
|---|---|---|
| 0–11 | 12 | salesman dialogue (0), UI words (1), symbolic names (2), club/city/country/league name lists (3–11) |
| 100–999 | 122 | club-management text: status lines, scouts, injuries, staff and player comments |
| 1000–9999 | 52 | menu help, screen titles, records, investment |
| 10000, 20000 | 2 | sponsor/company names, flag and item names |
| 30000–30003 | 4 | tutorials, tournament rules, game-over conditions |
| 35000–35999 | 296 | scripted event dialogue (secretary, salesmen, players), likely what the `EvsDataBin` event tables trigger |
| 36000–36030 | 31 | season-result speeches |
| 40000 | 1 | tournament information pages |
| 50563, 50832, 50833 | 3 | variable lists for the mail/news text in 563/832/833 (see below) |
| 80000, 90000 | 2 | scout/transfer report text, mail prompts |
| 100001–120000 | 9 | variants of categories 1, 3, 6, 9, 11, 960, 961, 10000, 20000 with the same ids: mostly identical, but e.g. `100009` has upper-case league names and `120000` longer item names |

Category 100's English file actually holds French text ("Voulez-vous
personnaliser votre club ?").

## Message references

Game data refers to a message with a u32 `category << 16 | id`. The
`EvsDataBin` tables use it for event dialogue (EVENT `+0x64`, whole
category), newspaper articles (NEWS `+0x64`/`+0x6c`, categories 832/833)
and mail (MAIL `+0x10`…`+0x24`, category 563). See
[`EVSDATABIN_FORMAT.md`](EVSDATABIN_FORMAT.md).

Categories `50563`, `50832` and `50833` mirror `563`, `832` and `833` id for
id, but each message there is just `W` followed by the variables the real
message uses (`W{var:1:3}{var:1:3}`). They're the lists the game uses to
fill variables (`MakeVarList`).

## Writing

`mbb.py` writes text back. `set` changes one message and `import` applies
a CSV in the format `csv` writes. Both write a new `MES.PAC`, which
`patch_disc.py` puts on the disc (see [`REBUILD.md`](REBUILD.md)):

```bash
python SRC/mbb.py set DAT/MESSAGE/MES.PAC out/MES.PAC 30000 0 1 "{name:101}Welcome.\nSecond line."
python SRC/mbb.py csv DAT/MESSAGE/MES.PAC messages.csv      # edit, delete the rows you don't change
python SRC/mbb.py import DAT/MESSAGE/MES.PAC messages.csv out/MES.PAC
python SRC/patch_disc.py patch disc.iso modded.iso MESSAGE/MES.PAC=out/MES.PAC --copies
python SRC/mbb.py roundtrip DAT/MESSAGE/MES.PAC
```

Text uses the same tags as `dump` and `csv`. A literal `{` is written `{{`.
In `set`, `\n` is a line break. `import` expects a UTF-8 CSV with the
`category,id` columns first. Rows and language columns can be deleted, and
a cell is applied only if it differs from the current text. A line break
inside a spreadsheet cell (CR LF) becomes `ESC 0x2F`. Any other raw control
character is refused, since the tags (`{lf}`, `{cr}`, `{xNN}`) are how
those bytes are written. An unknown tag, a character with no cp850/cp932
code, or an id that isn't in the file is also refused. When anything is
refused, nothing is written.

**Round trip (empirical).** All 461,992 records decode to text and encode
back to the same bytes, and all 3,738 files rebuild to their original
bytes, both at their own size and from scratch. `roundtrip` checks this
and is in `regress.py`. A variable is written in the narrowest of the
`0x10`/`0x11`/`0x12` forms that holds its category. Every variable in the
archive uses that form.

### Size

Each edited file keeps its **original size**. Shorter text is followed by
zero bytes up to the old size, and `data_size` still counts them. That is
safe. `Initialize` (`0x30d1c8`) allocates `data_size − 3 × count` bytes
for the strings at `0x30d1f4` (each record loses its 4-byte `{id, len}`
and gains a NUL). It then copies exactly `count` records
(`0x30d248`–`0x30d29c`), so it never reads the padding. The rule holds
the other way round too. A `data_size` smaller than the records would
make the copy overrun the buffer, so the builder always sets
`data_size = file size − 0x20` and never cuts records short.

Text that makes a file bigger is refused, and the message says by how
many bytes. The limit is per file (one category in one language), so a
message can grow if others in the same file shrink. Originally each file
ends 0–3 bytes after its last record (994, 920, 886 and 938 files), so
there is almost no free room until something is shortened.

Keeping the size means the `MES.PAC` header, every other entry, and the
763 copies in `PRELOAD/*.PAC` all keep their offsets and sizes.
`patch_disc.py --copies` finds and updates those copies. Tested on a copy
of `DATA.CVM`: editing `1_1.mbb` and `1_3.mbb` also rewrote
`STATIONMES1.PAC#0` and `STATIONMES3.PAC#0`.

**Room to grow (not used yet).** `MES.PAC` aligns entries to `0x800`, so
most files are followed by unused padding (median 1,544 bytes, fewer
than 64 bytes after only 15 files). A file could grow into it by changing
its size in the archive header. The `PRELOAD` packs align to `0x40`, so a
file with a copy there would first need that pack rebuilt. Whether the
game looks entries up by the header size (`fcEuroBinPac_SearchHeaderFilename`)
hasn't been checked.

## Open questions

- What the extra step in `setReaction` does for reactions 2 and 4 (a
  message to the second scene object at `+0x588`).
- Which variable ids each category defines, and how they're filled (the
  `Msg::VarBuf_*` functions at `0x11e7f0`… cover the global ones).
- Which screens use the `1000xx` variant categories instead of the originals.
- Whether an edit shows in game. `set` and `import` haven't been tried in
  PCSX2 yet.
