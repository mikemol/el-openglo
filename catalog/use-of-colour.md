# Use of colour (WCAG 2.2 SC 1.4.1) — census and measurement design (W72)

SC 1.4.1: colour must not be the ONLY visual means of conveying information, indicating
an action, prompting a response, or distinguishing a visual element.

This began as a census and a design (W72, 2026-09-22). **The check now exists and is the
authority:** `scripts/check_use_of_colour.py --list` prints every condition's live verdict, and
`scripts/opa_gate.py use_of_colour` decides it. The table below is the census as it stood,
with the rows that later work changed updated in place and marked with the date they changed.
Where this page and `--list` disagree, `--list` is right and this page is stale.

## 1. The source: mat230 `check-a11y` `_check_use_of_colour`

Source: `/home/mikemol/github/mat230/bin/check-a11y:138-150` (mat230 is retired; copy, never edit).

- **Population:** the `.tex` source, split on `\\` into table rows (`:141`). The split is textual,
  so prose paragraphs also become "rows".
- **Colour fact:** every `\textcolor{NAME}` in the row (`:144`). A colour is *meaningful* unless it
  is in `_MEANING = {"black"}` (`:117`, the default ink).
- **Non-colour fact:** a weight cue anywhere in the same row, the regex
  `\\(mathbf|textbf|boldsymbol|bfseries|bf)\b` (`_WEIGHT`, `:116`).
- **Verdict:** a row with a meaningful colour and no weight cue is bad (`:146`). Any bad row fails,
  reported as a count of rows (`:149`).
- **Weaknesses, as the source says:** it is a *sufficient* condition, not a necessary one
  (`:140`, audit row `:276`). Only one kind of redundant cue counts (weight). Text, position and
  shape cues are invisible to it. It does not check that the weight cue sits on the same span as
  the colour. It prints no population (`n of m`), so an empty tree passes. It has no selftest.

What el-openglo keeps is the **shape of the fact**: for each place where meaning is encoded,
record (colour channel, non-colour channel). What it drops is the textual row split: the
surfaces here are QML bindings and emitted role tables, not `\\`-delimited rows.

## 2. Census

Verdicts:

- `PASS`: a non-colour cue carries the same meaning.
- `LUM-ONLY`: the only other cue is opacity or luminance. That is still a colour property, so it
  does not satisfy 1.4.1 by itself. It does help with colour-vision deficiency, because the
  difference is not in hue.
- `FAIL`: the meaning is carried by hue alone.
- `DELEGATED`: the theme defines the role, but the consumer application decides whether a
  redundant cue goes with it. This theme's source cannot decide it.

All paths are relative to the repo root. Line numbers are at `def8fee`.

| # | surface | meaning | colour | non-colour cue | file:line | verdict |
|---|---|---|---|---|---|---|
| C1 | SegmentChar (every mount) | segment lit vs unlit | `litColor` vs `ghostColor` at `ghostAlpha` | **stroke weight**: lit is `segThick*(1+0.25*weight)`, ghost is `segThick*ghostWeight` (0.81), about 1.54x at the defaults. **Halo**: bloom is on the lit layer only | templates/SegmentChar.qml:56-57, 80-83, 86-112, 115-121 | PASS at the defaults. It reduces to LUM-ONLY when a mount sets `weight=0` and `ghostWeight=1` and `bloom=0`. The cue is a parameter, not an invariant |
| C2 | SegmentChar colon | colon blink phase (on/off) | lit vs ghost colour, alpha 1 vs `ghostAlpha` | none: the dots keep the same size, and the halo dots at `:110-111` are the only difference. **Blink motion** (alternates every second) | templates/SegmentChar.qml:110-111, 124-135 | PASS (halo and motion). Decorative anyway: seconds are not otherwise shown |
| C3 | SDDM greeter | login failed | `negativeColor` (neg) | **text** "Login Failed"; password is re-selected and re-focused | templates/sddm-main.qml:161-169, 197-201 | PASS |
| C4 | SDDM greeter | the clock's segments | as C1 (mount passes lit, ghost, ghostAlpha; weight and bloom left at defaults) | as C1 | templates/sddm-main.qml:95-110 | PASS (inherits C1) |
| C5 | SDDM greeter | focused control | `palette.highlight: focusColor` | Controls.Basic focus frame and text cursor (style-owned) | templates/sddm-main.qml:53 | needs a render |
| C6 | marquee | CRITICAL urgency | `hotColor` (fg_act) instead of `litColor` | **text** (UPPER CASE), **shape** (descent row lit), **animation** (flashes at 2 Hz, holds lit on hover-pause and under reduced motion) — W74, 2026-09-23 | templates/marquee-main.qml (`Body.glyphFor`, `flash`) | PASS (was FAIL) |
| C7 | marquee | LOW urgency | none | **text**: lower case, applied at the glyph lookup only — W74, 2026-09-23 | templates/marquee-body.js (`displayChar`) | PASS (was LUM-ONLY; the shrunk dot measured as dimming through the aperture, W72.h) |
| C18 | marquee | NORMAL urgency | none | **text**: UPPER CASE — W74, 2026-09-23 | templates/marquee-body.js (`displayChar`) | PASS (new row) |
| C8 | marquee | suspended job (gauge) | none | **shape**: a stippled column, the top pip (the value) always lit, every other pip below it dark — W74, 2026-09-23 | templates/marquee-main.qml (gauge painter) | PASS (was LUM-ONLY) |
| C9 | marquee | hover-paused | ring in `litColor`, opacity pulsing | **animation** (ring breathes on a 400 ms sine); the scroll **stops** | templates/marquee-main.qml:380-395, 526-530 | PASS |
| C10 | marquee | bold run | a fuller dot reads as a **brighter pip** | **none, measured**: `grow = s/2` enlarges the dot painted into the backdrop, and ApertureField grades each fixed-size pip by the backdrop's coverage, so a fuller dot is a brighter pip. That is luminance. The same mechanism made W72's shrunk low-urgency dot read as dimming (W72.h) | templates/marquee-main.qml (`grow`) | **FAIL** (was PASS; the census assumed dot size survives the aperture, and it does not) |
| C11 | marquee | link / `<u>` run | (no colour) | descent row lit (underline) | templates/marquee-main.qml:469, 473 | PASS |
| C12 | marquee | sender's coloured run | hue-table colour (`overrideFor`) | whatever the sender wrote. The theme re-maps the hue and adds no meaning of its own | templates/marquee-main.qml:237-242, 459-465 | DELEGATED (to the sender) |
| C13 | task switcher | selected window | `litColor` vs `ghostColor`, with opacity | **Font.Bold** plus a highlight bar with a 1 px **border** | templates/taskswitch-main.qml:123-125, 137-144 | PASS |
| C14 | task switcher | minimised window | opacity `ghostAlpha*0.75` | caption through `itemCaption(caption, minimized)` (text marker, if it adds one) | templates/taskswitch-main.qml:120, 124 | needs a read of `itemCaption` and a render |
| C15 | kdeglobals / `.colors` | negative / neutral / positive text | `ForegroundNegative/Neutral/Positive` | not the theme's: KDE consumers pair these with icons and message text | make_schemes.py:317-318 | DELEGATED |
| C16 | GTK | error / warning / success | `--error-*`, `--warning-*`, `--success-*` | not the theme's: GTK widgets pair these with icons | make_gtk.py:60-62 | DELEGATED |
| C17 | Konsole ANSI | program-chosen SGR colours, normal vs Intense | `Color{i}`, `Color{i}Intense` | not the theme's. Programs choose. Intense may also map to bold, which is a Konsole profile setting | make_konsole.py:78, 112-119 | DELEGATED |

Summary (updated 2026-09-25): 18 surfaces. 11 PASS (C1-C4, C6-C9, C11, C13, C18), 1 FAIL
(C10), 4 DELEGATED (C12, C15-C17), 2 need a render (C5, C14).

The census's one defect, **C6** (critical marked by hue alone), is fixed by W74's letterform
cues, and the operator's ruling of 2026-09-23 replaced the LUM-ONLY question for C7/C8 with
lowercase / UPPERCASE / FLASHING UPPER CASE. The remaining defect is **C10**, which the census
graded PASS: a bold run is a fuller dot, and a fuller dot through the aperture is only a brighter
pip. Bold needs a cue the aperture keeps (a different set of lit pips, as W74 did for urgency).

Residue, not deleted:

- C1's PASS depends on the parameters. Nothing stops a mount from zeroing the weight contrast. A
  check should measure the mount's actual bindings, not the component's defaults.
- C7 and C8 are LUM-ONLY. This is a judgement call, because WCAG treats "lighter vs darker" as a
  colour difference. Record them as such. Do not promote them to PASS.
- Clock-plasmoid (`templates/clock-main.qml`, `plasma-clock/.../SegmentChar.qml`) and
  live-wallpaper mounts of C1 were **not individually read** in this pass. They are covered by C1
  only if they leave `weight`, `ghostWeight` and `bloom` at non-degenerate values. The
  measurement below settles that.

## 3. Proposed measurement

### What can be MEASURED FROM SOURCE

- **C1/C4 and every SegmentChar mount.** Parse each `SegmentChar { ... }` instantiation with the
  existing QML tooling (`check_qml_lint --uses SegmentChar` already enumerates the mounts). Emit
  the bound or default `weight`, `ghostWeight` and `bloom`. The fact is
  `stroke_ratio = (1+0.25*weight)/ghostWeight` and `halo = bloom > 0`.
- **C3 and C6-C11, C13 (colour-bearing bindings).** For each QML element or painter branch whose
  colour depends on a state predicate (`cond ? A : B`, or a `fillStyle` chosen per `urgency`),
  find whether the SAME predicate also drives a non-colour property. The non-colour properties
  are `font.weight`, `text`, width/thickness, `border.width`, `grow`, an extra lit row, a running
  `Animation`, or `visible` on a sibling. The colour fact and the cue fact are both structural
  (the predicate's identifier set). This is the same-row test from mat230, made structural:
  "same row" becomes "same predicate".
- **C15-C17 (DELEGATED).** Measurable as a fact: role emitted, consumer unknown. It is reported
  as `withheld` with the reason "consumer-owned". It is never admitted and never denied.

### What NEEDS A RENDER

- **C5** focus frame, and **C14** minimised caption: the style or a helper function draws the cue,
  and the source binding does not show it.
- Whether a PASS cue is **perceptible**, for example whether a 1.54x stroke ratio reads at
  panel size. That needs the existing screens library (`catalog/library/screens/`, e.g.
  `marquee-paused-*.png` for C9). The source check proves the cue EXISTS. Only a render proves it
  is SEEN.

### `scripts/check_use_of_colour.py --json` (the measurement)

It emits only facts:

```json
{
  "cases": [
    {"id": "C6", "surface": "marquee", "file": "templates/marquee-main.qml", "line": 464,
     "meaning": "urgency==2", "predicate": ["urgency"],
     "colour": {"channel": "hue", "from": "litColor", "to": "hotColor"},
     "cues": []},
    {"id": "C13", "surface": "taskswitch", "file": "templates/taskswitch-main.qml", "line": 123,
     "meaning": "row.current", "predicate": ["row.current"],
     "colour": {"channel": "hue+lum", "from": "ghostColor", "to": "litColor"},
     "cues": [{"kind": "weight", "line": 125}, {"kind": "border", "line": 143}]},
    {"id": "C1", "surface": "segment:sddm", "file": "templates/sddm-main.qml", "line": 95,
     "meaning": "segment lit", "colour": {"channel": "hue+lum"},
     "cues": [{"kind": "stroke", "ratio": 1.54}, {"kind": "halo", "bloom": 1.5}]}
  ],
  "withheld": [
    {"id": "C15", "file": "make_schemes.py", "line": 317, "reason": "consumer-owned role"},
    {"id": "C5", "file": "templates/sddm-main.qml", "line": 53, "reason": "cue drawn by style; needs render"}
  ]
}
```

- `--selftest`: the measurement must SEE two fixtures. One QML with a colour-only ternary must
  emit `cues: []`. One with a matching `font.weight` must emit a weight cue. This proves the scan
  distinguishes found from not-found.
- It refuses unknown flags. It prints `n of m` surfaces. A missing QML parser is a counted SKIP.
- Weakness to state in the docstring: it proves the cue exists, and it proves the cue shares the
  predicate. It does not prove the cue is perceptible (see render).

### `policy/use_of_colour.rego` (the requirement)

```rego
package el.use_of_colour

# first rule: an ABSENT or empty population is a broken search, not a clean tree
deny contains "no colour-bearing surfaces measured: the search is broken" if {
    count(object.get(input, "cases", [])) == 0
}

non_colour := {"weight", "text", "shape", "border", "stroke", "halo", "animation", "position"}

# colour is the sole cue: no cue of a non-colour kind
deny contains msg if {
    some c in input.cases
    count({k | some q in c.cues; k := q.kind; non_colour[k]}) == 0
    msg := sprintf("%s %s:%d: '%s' carried by colour alone", [c.id, c.file, c.line, c.meaning])
}

# a stroke cue whose ratio collapsed to equal strokes is not a cue
deny contains msg if {
    some c in input.cases
    some q in c.cues
    q.kind == "stroke"
    q.ratio <= 1.0
    not halo(c)
    msg := sprintf("%s: lit/ghost differ by luminance only (stroke ratio %v, no halo)", [c.id, q.ratio])
}

halo(c) if { some q in c.cues; q.kind == "halo"; q.bloom > 0 }

admitted contains c.id if { some c in input.cases; not denied_id(c.id) }
denied_id(id) if { some c in input.cases; c.id == id; count({k | some q in c.cues; k := q.kind; non_colour[k]}) == 0 }

withheld contains msg if {
    some w in object.get(input, "withheld", [])
    msg := sprintf("%s %s:%d: %s", [w.id, w.file, w.line, w.reason])
}
```

`policy/use_of_colour_test.rego` should hold at least these cases:

- empty `{}`: denied.
- C6 as measured today: denied.
- C6 with a `weight` cue: admitted.
- C1 with `weight=0`, `ghostWeight=1`, `bloom=0`: denied.
- delegated rows only: withheld, which gives exit 3.

`scripts/opa_gate.py use_of_colour` joins them. LUM-ONLY cases (C7, C8) need a decision before
the policy is written. Either `lum` joins `non_colour`, which is permissive, or they deny, which
is strict and turns C7/C8 red with C6. That decision is the one open design question.

## Next steps

- ~~⟐W72.a Decide LUM-ONLY policy (C7/C8)~~ — superseded by the operator's letterform ruling
  (2026-09-23); C7 and C8 now carry text and shape cues (W74).
- ~~⟐W72.b Fix C6~~ — done by W74 (text, shape and animation cues).
- ~~⟐W72.c Implement `check_use_of_colour.py --json` plus the rego pair~~ — done; the gate is
  `opa_gate.py use_of_colour`.
- ⟐W72.f Fix C10: give a bold run a cue the aperture preserves. Grow is luminance through it.
- ⟐W72.d Read the clock-plasmoid and live-wallpaper SegmentChar mounts (the C1 residue), and
  `itemCaption` (C14).
- ⟐W72.e Render check for C5/C14, and a perceptibility check for C1/C9 against `catalog/library/screens/`.
