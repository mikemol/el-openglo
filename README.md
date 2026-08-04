# EL Openglo — a desktop theme for people who reset a lot of watches

The look of a ZnS:Cu electroluminescent backlight: near-black LCD panel, blue-green
phosphor glow (~505 nm), unlit "ghost" segments, and one deliberate inversion —
**selecting anything switches the backlight on** (glowing teal background, dark
digits), the way the whole panel lit when you held the button down.

Everything is *generated*. The palette is solved once and emitted to every surface,
so no two surfaces can drift apart: desktop colour scheme, terminal, window
decoration, widget style, boot splash, wallpapers, notification ticker, and browser.

## Generating

The environment is `uv`-managed; the manifest is `pyproject.toml`.

    uv sync                      # the core emission path
    uv sync --extra research     # + the font-ingest / glyph-matching pipeline

Each generator runs standalone, e.g.:

    uv run python3 make_schemes.py      # the colour schemes
    uv run python3 make_preview.py      # preview renders
    uv run python3 make_chrome.py       # browser theme manifests

## Contents

| file | emits |
|---|---|
| `make_palette.py` | solves the palette (upstream of everything; CVD-gated) |
| `make_schemes.py` | `*.colors` — the Plasma/Qt colour schemes |
| `make_preview.py` | preview renders; owns `parse_scheme`, the token reader |
| `make_konsole.py` | `*.colorscheme` — terminal |
| `make_aurorae.py` | window decoration (watch-case bezel) |
| `make_kvantum.py` | Kvantum widget style |
| `make_plasma.py` | Plasma desktop theme SVGs |
| `make_plymouth.py` | boot splash |
| `make_wallpaper.py`, `make_wallpaper_live.py` | wallpapers, static and live |
| `make_notify_marquee.py` | notification ticker |
| `make_clock.py`, `make_segment_display.py` | segment clock widget + QML display |
| `make_chrome.py` | browser theme (manifest v3) |
| `make_font.py`, `make_glyph_ink.py` | segment fonts, TTF ink fields |
| `make_deb.py` | the `.deb` packages |
| `segment_topology.py` | the 7/9/14/16/22-segment lattice (see below) |
| `glyph_match.py`, `project_font.py` | the glyph-matching research pipeline |
| `cvd_gate.py` | colour-vision-deficiency gating |
| `COTYPE.md` | design log — the reasoning behind every decision above |

## Install

Colour scheme, GUI route: System Settings → Colors & Themes → Colors →
"Install from File…" → pick `EL-Openglo.colors`. Or by hand:

    mkdir -p ~/.local/share/color-schemes
    cp EL-Openglo.colors ~/.local/share/color-schemes/

Konsole scheme:

    mkdir -p ~/.local/share/konsole
    cp EL-Openglo.colorscheme ~/.local/share/konsole/

then Konsole → Settings → Edit Current Profile → Appearance → EL Openglo.

Wallpaper: right-click desktop → Configure Desktop and Wallpaper → add the PNG
(or the SVG; Plasma renders it crisply at any resolution).

## Palette tokens

| token | hex | role |
|---|---|---|
| panel-off | `#060B0D` | view background |
| case | `#0C1517` | window background |
| body-glow | `#8CE8DA` | normal text |
| hot-glow | `#A8FFF2` | active text |
| el-core | `#00E0C2` | focus ring / accent |
| openglo-on | `#00CDB0` on `#04211D` | selection (the backlight press) |
| ghost | `#3D6660` | inactive / unlit segment |
| amber-EL | `#FFB454` | warnings (amber EL panels were real, too) |

## The segment lattice

`segment_topology.py` holds one canonical geometry and derives the rest:
7 / 9 / 14 / 16 / 22 segments, where the coarser formats are projections
(mask + merge) of the 16-segment cell. 22 is the odd one — not a coarsening but a
*superset*: 16 plus six additions (two dots, one extra diagonal, three descender
bars below the baseline), so lowercase letters with descenders resolve. Projecting
22 back to 16 is byte-equal to native 16, which the module asserts:

    uv run python3 segment_topology.py --selftest

## Status

This repo is a **recovery**. The original was lost before it was ever pushed, and
the tree was replayed from session transcripts; eight files are at an intermediate
state and one module (`qml_sanity.py`) did not survive at all. `RECOVERY-NOTES.md`
records what is trustworthy and what is not.

What is *checked* rather than asserted lives in `catalog/worklist/` — a claim graph
where every sentence carries a machine-checkable witness, and an item is open
exactly when its check fails:

    python3 scripts/worklist_gate.py              # are all claims discharged?
    python3 scripts/worklist_gate.py --project    # regenerate WORKLIST.md
