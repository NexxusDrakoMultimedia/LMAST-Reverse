<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- Copyright (C) 2026 Nexxus Drako Multimedia -->

# Main sponsor negotiation

In the Japanese release the season's Sponsor screen lets you negotiate with
a main sponsor candidate: you name a fee, and the sponsor accepts or
refuses. PAL only offers to sign each candidate at its listed fee. The
negotiation is still in the PAL game. Its text is translated and its code is
compiled in. One check switches it off: a function that returns 0. This doc
traces the feature and describes `patch_disc.py --sponsor-negotiation`,
which turns it back on.

There's no Japanese disc in the project, so the Japanese check's body is
unknown. The rebuilt check is based on what the PAL code around it still
expects (see [The restored check](#the-restored-check)).

## The text

Message category 950 (`MESSAGE/MES.PAC`, `950_<lang>.mbb`) is the Sponsor
screen's. The negotiation lines are present in Japanese and in every PAL
language:

| Id | English | Shown by the PAL code |
|---|---|---|
| 61 | "Negotiation" (Japanese: remaining negotiations) | not found in the screen's code |
| 63 | "Bid" (Japanese: negotiated amount) | not found in the screen's code |
| 110 | "Let's negotiate with the main sponsor candidate first." (Japanese: choose a company to sign **or negotiate with**) | `0xc6580` |
| 120 | "Do you want to negotiate with {sponsor}?" | `0xc66ac`, state 0xb |
| 121 | "Set up contract money." | `0xc6798` |
| 122 | "Negotiation successful." | `0xc69d8` |
| 123 | "Negotiation successful; the terms of the contract have changed" | no call found |
| 124 | "Unfortunately negotiations have broken down. {sponsor} cannot do a deal for the season now." | `0xc6a04` |

Only 110 mentions negotiating. The sub-sponsor (111) and supplier (112)
lines only ask you to sign. That matches the code: the check is called only
in the main sponsor part of the screen.

```
python SRC/mbb.py dump DAT/MESSAGE/MES.PAC --cat 950 --lang 1
```

## Confirmed from the game code

All addresses are `SIMPRG.REL`. The Sponsor module (55) is
`SPONSOR_MODULE::pSetupSponsorModule` (`0x39ea0`). It builds the screen
object, `0x13a0` bytes from `FcEuroCalloc` (`0x3a004`), with constructor
`0xc4900`. The screen is a state machine on `this+0x240`. It shows its text
through `0xc9288(this, id)` after `SetCategory(950)` (`0xc9220`).

| Address | Symbol / role | What it shows |
|---|---|---|
| `0xc5ca0` | negotiation check (no symbol) | the stub `jr $ra; move $v0, $zero`: always 0 |
| `0xc6634` | state 8/9, main sponsor list, on a pick | calls `0xc5ca0(this, id at +0x1054)`. 1: state 0xb, or message 160 if the list (`+0x898`) has fewer than 2 entries. Otherwise state 0x17 |
| `0xc66ac` | state 0xb | asks message 120 (yes/no), then state 0xc |
| `0xc6744`-`0xc67cc` | state 0xc, Yes | opens a `WP::CMoney` input (`MakeList`) starting at the candidate's fee (`+0x119c`, ×100) and shows message 121 |
| `0xc68d4`-`0xc6944` | state 0xe, input confirmed | `GetInputValue` to `+0x378`. A bid equal to the listed fee skips the judgement (branch to `0xc82b8`, not traced further). Otherwise `0xc5c58` notes the sponsor, then state 0x10 and `0xc8ee0` |
| `0xc5c58` | note a negotiation | writes the sponsor id into the first free word of a 20-word list at `this+0x12f0`. In PAL nothing else reads this list |
| `0xc62d8` | screen setup | clears the 20 words of the list |
| `0xc8ee0` | judge the bid | `0x16aa98(id, fee × 100, bid)`. The result goes to `+0x2f4`. On success `0x16a9e0(id, bid / 100, term)`, on failure `0x16a980(id)` |
| `0x16aa98` | acceptance test | reads the sponsor's database record (`plSponsor_GetDb`, `0x160dc0`) and the town's economy (`pwkTown_Keiki`). It picks a factor from the byte table at `0x1dad80` and the float table at `0x1dada8`, and accepts if bid ≤ fee × factor. No random numbers |
| `0x16a9e0` | accept | writes the new fee (`+0xc`) and term (`+5`) into the sponsor's candidate entry (list at `0x1da918`) |
| `0x16a980` | refuse | clears the sponsor's candidate entry, so it leaves the list for the season |
| `0xc69c4`-`0xc6a3c` | state 0x11 | message 122 and sound 0xd on success, 124 and sound 0xc on failure |
| `0xc6ab0`-`0xc6bd8` | states 0x15, 0x16 | rebuild the candidate list (`0xc9830`). After a success, go to the contract question (state 0x17, message 150). After a failure, go back to the list (state 9) |
| `0xc6ea8`, `0xc7668` | sub-sponsor and supplier parts | states 0x1c and 0x29 onward. They never call `0xc5ca0` |

So everything after the check works as it did in Japan. Only the check's
body is gone.

## The restored check

The Japanese check is likely the reader of the `+0x12f0` list, since
`0xc5c58` fills it and no PAL code reads it. The patch makes `0xc5ca0`
return 1 unless the sponsor id is already in that list. You can negotiate
once with each main sponsor candidate per Sponsor screen. After a success,
picking the sponsor again goes to the contract question at the agreed fee.
After a failure the sponsor is gone from the list.

`0xc5ca0` has room for only two instructions. It becomes a branch to
`0xd3748`, an unreferenced `CStaffContractWindow` method: 24 words, with no
call, branch, pointer or relocation pointing to it. The loop goes there.
The overlay is relocated when it loads, so the new code uses only branches,
and neither spot holds a relocation site that the loader would patch over.

| Address | New code |
|---|---|
| `0xc5ca0` | `b 0xd3748` / `addiu $v1, $a0, 0x12f0` |
| `0xd3748` | `addiu $t0, $a0, 0x1340` (end of the list) |
| `0xd374c` | `lw $v0, ($v1)` |
| `0xd3750` | `beq $v0, $a1, 0xd3768` (already negotiated) / `addiu $v1, $v1, 4` |
| `0xd3758` | `bne $v1, $t0, 0xd374c` / `nop` |
| `0xd3760` | `jr $ra` / `addiu $v0, $zero, 1` |
| `0xd3768` | `jr $ra` / `move $v0, $zero` |

That's 12 words in all. The rest of the old method at `0xd3770` is left as
it was.

```
python SRC/patch_disc.py patch disc.iso nego.iso --sponsor-negotiation
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0xc6630 4 --sles ISO/SLES_541.51
python SRC/snr2.py dis ISO/DLL/SIMPRG.REL 0xc8ee0 58 --sles ISO/SLES_541.51
```

## Still unknown

- Whether the Japanese check had other conditions, for example the limit
  that message 61 ("remaining negotiations") counts down. No PAL code was
  found that shows 61 or 63, or keeps such a counter. They may be layout
  text in the screen's CSE file.
- Which acceptance factor applies to which economy and sponsor type: the
  layouts of the tables at `0x1dad80` (bytes, 5 × 7) and `0x1dada8`
  (floats).
- Message 123 (success with a changed term) has no caller.
- The "Remaining 1" line on the sponsor panel (seen in the test below) is
  probably message 60, remaining contract slots (1 for the main sponsor),
  not 61. It hasn't been traced in the code.

## Tested in PCSX2

On the skip-tutorial disc with `--sponsor-negotiation`, at the first
Sponsor screen of a new career (2006-2007, week 1), picking the main
sponsor candidate Africmap Airways (£1,350,000, 1 year) asked "Do you
want to negotiate with Africmap Airways." (message 120). Yes opened the
"Bid" money input, starting at the listed fee, with "Set up contract
money." (121). Before the patch, the same pick goes straight to the
contract question. A bid of £1,500,000 (11% over the fee) was accepted,
and the screen went on to ask whether to sign Africmap Airways as main
sponsor (state 0x17; user report). The signed contract pays the
negotiated fee, not the listed one (user report). After a reload, a higher bid was
refused: a "Broken Down" banner and "Unfortunately negotiations have
broken down. Africmap Airways cannot do a deal for the season now."
(message 124). The refused sponsors left the list. With only Yogurens
Milk (£1,000,000) left, picking it gave message 160 ("You currently have
only one sponsor. Proceed with contract...") and no negotiation, as the
`+0x898 < 2` test at `0xc6648` says. A negotiation can't cost the club
its last main sponsor candidate.
