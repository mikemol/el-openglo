# One theme, variant by the active colour scheme (⊕ONE-THEME)

The operator, 2026-09-22: *"Ideally, that'd be a single theme whose color variant
could be selected. That way I don't have half a dozen openglo themes, I can have one
configurable one."*

Today every package is emitted six times with its colours BAKED as template holes.
The Plasma colour scheme is inherently one file per variant — that is how Plasma
selects a variant — but nothing else has to be. A package that reads the ACTIVE
scheme at runtime is one package; applying `EL-Amber.colors` is what selects amber.

## What each surface bakes today, and where it lives in the scheme

Measured from the templates and `make_schemes.emit_colors` (the `section()` role
order: Active, Inactive, Link, Negative, Neutral, Normal, Positive, Visited).

| surface | hole | token | KColorScheme role | live read (`Kirigami.Theme`, `colorSet: View`) |
|---|---|---|---|---|
| clock, marquee, live wallpaper, switcher, splash | `ground` / `void` | `view` | `[Colors:View] BackgroundNormal` | `backgroundColor` |
| all of the above | `lit` | `fg` | `ForegroundNormal` | `textColor` |
| all of the above | `ghost` | `fg_in` | `ForegroundInactive` | `disabledTextColor` |
| clock | `hot` | `fg_act` | `ForegroundActive` | `activeTextColor` |
| switcher (lit bar) | `lit` at 0.12 | — | `[Colors:Selection] BackgroundNormal` would be the honest role | `highlightColor` |
| all | `ghostAlpha` | `[EL] GhostAlpha` | **not a role** | GLOBAL since W23 (0.566) — bake the constant |
| wallpaper, splash, plymouth | `ghostAlpha` (glanced) | `[EL] GhostAlphaGlanced` | **not a role** | GLOBAL (0.309) — bake the constant |
| marquee | `hueTable` | `make_palette.hue_table(fg, view, fg_in)` | **not a role**, per variant | bake ALL six tables keyed by `fg`'s hex; pick the row from the live `fg` |
| clock | `$tables` | geometry (registry) | not a colour | unchanged — the registry is the display's, not the variant's |

So: four live reads cover every colour hole; the two alphas are constants; the
one per-variant table is a six-row lookup keyed by a live colour. **Nothing needs
a KConfig read from QML** (which Plasma does not offer) and nothing needs the
scheme's NAME (which `Kirigami.Theme` does not expose).

## What changes, per package

- **Plasmoids (clock, marquee), the live wallpaper, the switcher**: one package
  each; the four holes become `Kirigami.Theme` bindings under `colorSet: View`;
  `ghostAlpha` becomes a baked constant; the marquee carries the six hue tables.
  The Plasma Style and the icon/cursor themes stay per variant (their contracts
  are files, not runtime reads). The LnF: one package whose `defaults` selects a
  colour scheme — variant = a choice of `ColorScheme=` (and, per W37, an engine).
- **Gates**: `check_ghost_surfaces` reads holes today; a live surface has no hole
  to read, so the check must assert the BINDINGS instead (the QML binds
  `textColor`/`disabledTextColor`/`backgroundColor` to lit/ghost/ground and the
  constant to the solved alpha). `check_template_parity` loses per-variant pairs
  (one pair each). `render_qml` mocks `plasmoid`; it must mock `Kirigami.Theme`
  with a variant's tokens to render — the harness gains a `--variant`.
- **Not live**: the `.colors` files themselves (six), the Plasma Style SVGs, the
  Aurorae decorations, Union styles, GTK/terminals/browsers (their consumers do
  not read KColorScheme) — variant selection for those stays "which file".

## The probe that decides it

Does a `Kirigami.Theme`-bound plasmoid follow `plasma-apply-colorscheme EL-Azure
→ EL-Amber` without reinstall? It should (that is what the API is for), and it is
a live ⊕VER probe: render_qml cannot see the live scheme. The switcher is the
smallest surface and the first PoC.

## The Look-and-Feel

One LnF per variant STAYS. The Look-and-Feel is not a surface: it is the
SELECTOR — its `defaults` group writes `[kdeglobals][General] ColorScheme=<v>`,
and that write is what makes every bound surface amber or azure. Collapsing it
would leave nothing to choose a variant with. What changed (s104-s108): each
variant's defaults and layout script name the ONE clock (`org.el.segclock`),
marquee (`org.el.notifymarquee`), switcher (`org.el.taskswitch`) and live
wallpaper (`org.el.openglo.live`), so six LnFs select one set of packages.
W37's Oxygen flavour is another LnF of the same shape: the same scheme, a
different engine choice in `defaults`.

## What ships for a user who installed before W35

Every legacy per-variant id (`org.el.openglo.live.<v>`, `org.el.segclock.<v>`,
`org.el.notifymarquee.<v>`) still ships, as a thin copy of the one package with
only its metadata id changed — the same bound QML, so it follows the scheme like
the canonical one. Measured 2026-09-22 (the operator's shell failed to start):
a containment whose WALLPAPER plugin does not exist fails the whole shell,
where a missing applet only leaves a placeholder; the aliases make the old
config loadable, and the one-shot update script
`plasma/shells/org.kde.plasma.desktop/contents/updates/el-openglo-one-theme.js`
(plasmashell runs each once and records it in `plasmashellrc [Updates]`) moves
the wallpaper plugin and each legacy applet to the one ids with settings and
geometry kept. `scripts/check_migration.py` runs that script against a fake
shell shaped like the operator's appletsrc (@MIGRATION). The aliases retire
when no supported install can still name them.

## Residue

- The switcher's lit bar (0.12) is authored; live it would be `highlightColor`
  at that alpha, still authored.
- Ghost alpha is global TODAY; if a future solve makes it per variant again, the
  constant stops being honest and the hue-table trick (a six-row lookup keyed by
  `fg`) is the fallback for it too.
- The clock's `$tables` are geometry, untouched by this.
