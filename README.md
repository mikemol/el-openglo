# EL Indiglo — a KDE theme for people who reset a lot of watches

The look of a ZnS:Cu electroluminescent backlight: near-black LCD panel, blue-green
phosphor glow (~505 nm), unlit "ghost" segments, and one deliberate inversion —
**selecting anything presses the Indiglo button** (glowing teal background, dark
digits), the way the whole panel lit when you held the crown.

## Contents

- `EL-Indiglo.colors` — system-wide Plasma/Qt color scheme (the main event)
- `EL-Indiglo.colorscheme` — matching Konsole terminal scheme
- `EL-Indiglo-wallpaper.svg` / `.png` — ghost-segment "12:00" watch-face wallpaper
- `make_wallpaper.py` — parametric generator (change the time, sizes, or colors and re-run)
- `COTYPE.md` — design log: palette tokens, decisions, and deferred variants

## Install

Color scheme, GUI route: System Settings → Colors & Themes → Colors →
"Install from File…" → pick `EL-Indiglo.colors`. Or by hand:

    mkdir -p ~/.local/share/color-schemes
    cp EL-Indiglo.colors ~/.local/share/color-schemes/

Konsole scheme:

    mkdir -p ~/.local/share/konsole
    cp EL-Indiglo.colorscheme ~/.local/share/konsole/

then Konsole → Settings → Edit Current Profile → Appearance → EL Indiglo.

Wallpaper: right-click desktop → Configure Desktop and Wallpaper → add the PNG
(or the SVG; Plasma renders it crisply at any resolution).

Optional finishing touches that push it further: set the panel clock's font to
**DSEG7 Classic** (free seven-segment font) for a true digital readout, and pick
Breeze Dark as the application style so the scheme sits on flat surfaces.

## Palette tokens

| token | hex | role |
|---|---|---|
| panel-off | `#060B0D` | view background |
| case | `#0C1517` | window background |
| body-glow | `#8CE8DA` | normal text |
| hot-glow | `#A8FFF2` | active text |
| el-core | `#00E0C2` | focus ring / accent |
| indiglo-on | `#00CDB0` on `#04211D` | selection (the backlight press) |
| ghost | `#3D6660` | inactive / unlit segment |
| amber-EL | `#FFB454` | warnings (amber EL panels were real, too) |

## Next steps (invoke by symbol)

- ⊕LIT — full "backlight-on" variant: glowing background, dark digits everywhere
- ⊕AMB — amber EL variant (same value structure, phosphor hue swapped)
- ⊕AUR — Aurorae window decoration: watch-case bezel, glow on the active titlebar
- ⊕PLA — full Plasma desktop theme SVG set (panel, system tray, widgets)
- ⊕KVT — Kvantum widget style for deeper Qt control styling
- ⊕GTK — GTK3/4 sync so Firefox/GIMP-type apps match
- ⊕SEG — DSEG7 seven-segment clock widget setup
