# One display, three layers

The clock, the notification marquee and the live wallpaper are three MOUNTS of
one display. This names the layer each setting belongs to, because the settings
vocabulary drifted apart while the renderer was being unified — the same defect
one level up from ⊕SEGMENTCHAR-ADOPT, and invisible until the two config pages
are read side by side.

Measured 2026-09-22 by `scripts/check_config_page.py --json`: 8 declared keys on
the clock, 11 on the marquee, 0 on the live wallpaper.

## The cut

A **display** setting is a parameter of the display engine itself — it governs
how a lit or unlit primitive is DRAWN, and it means the same thing on every
mount. A **mount** setting governs what string exists and how it behaves; it
never reaches the display. An **instrument** setting changes neither, and exists
so a human can see what the widget did.

| layer | clock | marquee |
|---|---|---|
| display | `showGhost` · `ghostWeight` · `weight` · `bloom` · `digitGap` | `showField` · `ghostAlpha` · `dotFill` · `pitchScale` |
| mount | `use24h` · `showSeconds` · `blinkColon` | `speed` · `idleText` · `maxItems` · `openLinks` · `hoverPause` |
| instrument | — | `debugLog` · `traceLog` |

## ⚑ CORRECTION (2026-09-22, measured by the W59 agent against the display components)

**Two of the four equations below were wrong, and the table is kept so the error
stays legible.** They were read off the two config pages' labels, not off the
components the settings drive:

- **`ghostWeight` ≠ `ghostAlpha`.** `templates/SegmentChar.qml` carries BOTH — an
  opacity (`ghostAlpha`) and a stroke thickness (`ghostWeight`). They are two
  parameters, not one parameter spelled twice.
- **`weight` ≠ `dotFill`.** `weight` boosts the LIT layer only; `ApertureField`
  draws lit and unlit pips at one size (`dotFill`) and has no per-layer weight.

So the display layer has **seven** canonical parameters, not five: `ghost`,
`ghostOpacity`, `litWeight`, `ghostWeight`, `fill`, `pitch`, `bloom`. The
declaration now lives in `display_params.py`, each mount EXPOSES or WITHHOLDS each
parameter with a stated reason, and `policy/config_page.rego` rules D0–D4 refuse an
unexplained absence. The two correct equations (`showGhost` = `showField`,
`digitGap` = `pitchScale`) survive as legacy per-mount *spellings* of one canonical
parameter — no user key was renamed.

⚑ **The lesson is the method, not the numbers.** Equating settings by their labels
is the same error as equating checks by their names: it reads the surface a thing
presents, not what it drives. The correction came from reading the components.

## The display rows as first drawn (partly wrong — see the correction above)

| the display parameter | clock spells it | marquee spells it |
|---|---|---|
| is the unlit substrate visible at all | `showGhost` | `showField` |
| how subordinate the unlit substrate is | `ghostWeight` | `ghostAlpha` |
| the primitive's fill fraction of its cell | `weight` | `dotFill` |
| the lattice pitch between cells | `digitGap` | `pitchScale` |
| the emission spread around a lit primitive | `bloom` | **(absent)** |

Four parameters, two vocabularies, and a user who learns one page learns nothing
about the other. The labels diverge as far as the keys do: "Unlit field opacity"
and "Show unlit field" on one page are "Show ghost segments" on the other, for
the same quantity.

⚑ **`bloom` HAS NO MARQUEE COUNTERPART, AND THAT IS NOT A DECISION.** The same
display engine draws both surfaces, so the emission model is there either way;
one mount can reach it and the other cannot. Nothing recorded that choice,
because no artefact held both lists at once — which is what this file is for.

⚑ **THE LIVE WALLPAPER EXPOSES NOTHING.** It mounts the display (W33,
`templates/SegmentChar.qml`) and declares no config page at all. Its display
parameters are not differently named; they are unreachable. Three mounts, three
different answers to "can the user set the pitch": yes as `digitGap`, yes as
`pitchScale`, no.

## What the layer boundary buys

**A display setting is declared once and every mount inherits it.** That is the
settings half of ⊕SEGMENTCHAR-ADOPT: the geometry already comes from one
substrate, and the parameters that drive it should come from one declaration
too. A new display parameter then appears on every mount, or is deliberately
withheld from one — and the withholding is a recorded act rather than an
omission nobody can see.

**A mount setting stays local, and should.** `use24h` is meaningless to a
marquee and `hoverPause` is meaningless to a clock. Collapsing those would be
the destructive kind of merge — the repetition there carries identity.

**An instrument setting is neither, and naming the third layer keeps it from
being smuggled into the first two.** `debugLog` and `traceLog` change nothing a
user sees; they exist because `check_marquee_host.py` reads the trace back off
the live desktop. A display that grew a `debug` parameter would have made the
display engine's surface a function of how it is observed.

## Why this is measured rather than asserted

⚑ **THE TWO PAGES WERE NEVER READ SIDE BY SIDE UNTIL THE OPERATOR ASKED.** Each
was internally coherent; the drift is only visible in the join, and no tool
computed the join. `check_config_page.py` already measures both — it was built
to catch Plasma's `cfg_<key>Default` requirement — so the population was
available all along and the question had simply not been put to it.

That is the same shape as everything else this catalog records: not a missing
measurement, a missing QUESTION.
