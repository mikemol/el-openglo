# External standards, and the module that applies each

⚑ **THIS FILE EXISTS BECAUSE A STANDARD WENT MISSING AND NOTHING NOTICED.** The
recovery lost most of `cvd_gate.py` — 8 of the 10 attributes its consumers call —
and with them the WCAG, APCA, and normalized-q machinery. Every file still
byte-compiled, so `check_compiles` stayed green; the only symptom was a
washed-out palette on screen, which is what a scheme looks like when the gate
that enforced its separation never ran.

A standard applied by code nobody can name is a standard that can vanish
silently. Each row below says which module applies it, and what would break
first if it went missing again.

## Colour and contrast

| standard | what it fixes | applied by | first symptom if absent |
|---|---|---|---|
| **WCAG 2.x** relative luminance + contrast ratio (W3C, SC 1.4.3) | the legibility floor every foreground/background pair is judged against | `cvd_gate._wcag_L`, `cvd_gate.wcag_ratio` | schemes emit, nothing gates their contrast |
| **APCA** lightness contrast (WCAG 3 draft, apca-w3 0.0.98G) | polarity-aware contrast; WCAG 2 mis-ranks dark-mode pairs, and this is the cross-check that makes the disagreement visible | `cvd_gate.apca_Lc` | the ghost loses its definition — see below |
| **CAM02-UCS** perceptual distance | the metric semantic-accent separation is measured in | `cvd_gate._ucs` (via `colorspacious`) | distinctness measured in a space that does not match perception |
| **Machado (2009)** CVD simulation, severity 100 | protan / deutan / tritan views of every pair | `cvd_gate.VIEWS`, `worst_view_dE` | pairs distinct to trichromats but not to others pass |
| **Okabe & Ito (2008)** Color Universal Design palette | the calibration floor — a pair of ours is admissible if at least as separated as this reference palette's own tightest pair | `cvd_gate.OKABE_ITO`, `reference_floor`, `reference_floors` | the floor becomes hand-picked instead of standard-anchored |

⚑ **THE FLOOR IS NOT HAND-PICKED, AND THAT IS THE WHOLE DESIGN.** It is derived
from the Okabe-Ito palette's own tightest worst-view pair. Replacing it with a
chosen number would make the gate an opinion.

### Thresholds that are OURS, not the standards'

These are this project's judgment, defensible but not normative. They live as
named constants in `cvd_gate.py` so changing one is a one-line decision rather
than a hand-chase through emitters.

| constant | value | why |
|---|---|---|
| `OLED_VOID_MAX_LUM` | 0.02 | a truly-off OLED pixel emits 0 nits; "still reads black in a dark room" is ≲2–4 nits ≈ 2% of SDR white. Our grounds measure 0.2–0.7%. |
| `GHOST_READABLE_LC` | 30.0 | the ghost is unlit-segment **texture, not text**: it must FAIL readability by design, so it sits at APCA's "any text" minimum. Without `apca_Lc` the ghost has no definition at all. |
| `STRETCH_TARGET` | 3.0 | per-side contrast for the 3-body {lit, ghost, ground} separation |
| `CHROMA_FLOOR` | 40.0 | keep `lit` hue-faithful while stretching — don't crush to a hueless black to win a metric |
| `cvd_gate.SECTORS` | per accent | required hue sectors for neg/neu/pos/link/visited. **Canonical here**; `make_palette` imports it rather than forking it. |

⚑ **THE SOLVER OPTIMISES THE GATE'S OWN METRIC, NOT A PROXY.** `_worst_normalized`
returns ΔE normalized by the floor its pair class is judged against. A solver
maximising raw global min-ΔE optimises something that merely *correlates* with
the gate and diverges exactly at the margin — measured, and the reason
`make_palette.solve_semantic_set` scores candidates with `_worst_normalized`.

## Display and desktop

| standard | applied by | note |
|---|---|---|
| **IEC 60617** seven-segment lettering | `segment_topology.GEOM16` (7-seg `a`–`g`) | positions verified against a standard decoder, 10/10 digits |
| **KDE/Plasma colour scheme** `.colors` schema | `make_schemes.emit_colors` | group/key contract read by every Qt app |
| **Konsole** `.colorscheme` schema | `make_konsole` | |
| **Plasma 6 `KPackageStructure`** | `make_plasma`, `make_clock` | traps recorded in the design log: `WallpaperItem` root required; QML property names must be lowercase |
| **freedesktop** icon/cursor inheritance | *(unimplemented)* | open as ⊕ICONS-INHERIT, ⊕CURSOR-INHERIT |
| **Chrome/Chromium** theme manifest v3 | `make_chrome.manifest` | `theme.colors` as RGB triples |
| **Debian** package layout | `make_deb` | |

## Verifying, rather than trusting, this file

The colour standards are checkable and are checked:

    uv run python3 cvd_gate.py --selftest

APCA is validated against its **published reference vectors** — `#888` on `#fff`
= 63.06, `#fff` on `#888` = −68.54 — so a mistyped constant anywhere in the chain
fails the test. WCAG is anchored on its own normative values (black/white = 21:1,
identity = 1:1). Those numbers were not chosen here, which is what makes the
implementation falsifiable rather than merely plausible.

## Not a standard, but an absent external input

**KvFlat** (Tsu Jan, GPL-family) — `make_kvantum` recolours this upstream Kvantum
theme. It was staged in `/tmp` and did not survive the recovery; recorded in
`pyproject.toml`. The generator is intact, its input is missing.

**Brettel (1997)** CVD simulation via `daltonlens` — the *second*, independent CVD
model, used in the design log to cross-check Machado. It is neither imported in
the tree nor declared in `pyproject.toml`. Machado alone leaves that cross-check
unwitnessed. Recorded here rather than quietly dropped.
