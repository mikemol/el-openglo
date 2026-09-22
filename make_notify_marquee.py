#!/usr/bin/env python3
"""Notification-marquee plasmoid emitter (⊕NOTIFY-MARQUEE; ONE package since W35, ⊕ONE-THEME).

A panel widget that SUBSUMES the occluding notification popups into a phosphor
scrolling ticker (an airport departure-board for your desktop). It restores the
behavior late Plasma 4 had before Plasma 5 replaced the ticker with popups.

Architecture (fetched): reads the PUBLIC NotificationManager.Notifications model
(import org.kde.notificationmanager) — the same feed the stock applet consumes —
rather than trying to become the D-Bus notification server. Root is PlasmoidItem
(KF6), entry ui/main.qml, KPackageStructure=Plasma/Applet.

⚑ ONE PACKAGE, THE VARIANT IS THE ACTIVE COLOUR SCHEME (catalog/one-theme.md).
lit / ghost / ground are Kirigami.Theme's textColor / disabledTextColor /
backgroundColor under colorSet View — the roles make_schemes.emit_colors writes
fg / fg_in / view into. What is NOT a role: the ghost alpha, global across the
variants (make_taskswitch.ghost_alpha refuses otherwise), baked; and the
sender-hue table, per variant — so the widget carries ALL SIX tables keyed by
the variant's fg hex and picks the row from the live lit colour (hue_tables_js).

Degrades gracefully: if the model is empty or the import is unavailable, the
widget shows an idle phosphor face rather than crashing.
"""
import os
import json
import make_wallpaper_live as WL   # colors_for: the token-derived lit/ghost/void per variant
import make_taskswitch as TS       # ghost_alpha(): the measured-global constant; VARIANTS
# ⚑ THIS SURFACE IS A DOT-MATRIX DISPLAY, NOT A SEGMENT ONE, AND NOT STYLED TEXT.
# It rendered `font.family: "monospace"` — a phosphor ticker drawn in whatever the
# system serves — because ⊕NOTIFY-MATRIXRENDER was never built. The obvious repair
# (project to "22" and draw segments) is the one ⊕NOTIFY-SEGRENDER already tried
# and moved to RESIDUE: ⊕DOT rejected "matrix as FORMATS['5x7'], reuse project()"
# outright, because a segment is a subset of a topology and a pixel-cell is a
# raster — no shared substrate. The abstraction was lifted one level instead, so
# this consumes THE REGISTRY and dispatches on `kind`.
import display_types as DT

PACKAGE_ID = "org.el.notifymarquee"
VARIANTS = TS.VARIANTS
# the variant whose hue row is the FALLBACK when the live fg matches no variant
# (a foreign scheme applied over the theme): its buckets fall back to fg anyway
FALLBACK_VARIANT = "EL-Openglo"


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def metadata():
    return {
        "KPackageStructure": "Plasma/Applet",
        "KPlugin": {
            "Id": PACKAGE_ID,
            "Name": "EL Notification Marquee",
            "Description": "Phosphor scrolling ticker that subsumes notification popups, coloured by the active scheme",
            "Category": "System Information",
            "License": "GPLv3",
            "Authors": [{"Name": "EL Openglo"}],
        },
        "X-Plasma-API-Minimum-Version": "6.0",
    }


# ⊕MATRIX-FONT-INPUT — the font the ticker's extension glyphs are rasterised
# from. DECISION (session 77, recorded): a packaged text face resolved at BUILD
# time, in this order — `EL_MATRIX_FONT` when set, else Liberation Mono (Gentoo
# media-fonts/liberation-fonts, Debian fonts-liberation: a dependency both
# packagings can name), else the other candidates check_projection already
# knows. NOT fc-match: that makes the emission a function of the build host.
# NOT a shipped EL TTF: those are the segment/matrix faces, which have no
# Latin-1 lowercase to rasterise. None -> the authored 70 only, and the SKIP is
# PRINTED, because a ticker that silently shows '?' for every lowercase letter
# is the failure this symbol exists to close.
MATRIX_DISPLAY = "5x8"
# the font check_template_parity pins the marquee baseline to, by absolute path
# (a host without it SKIPs the pair) — Liberation Mono where Gentoo installs it
PARITY_FONT = "/usr/share/fonts/liberation-fonts/LiberationMono-Regular.ttf"


def matrix_font():
    """Path of the outline font for the matrix extension, or None (printed)."""
    env = os.environ.get("EL_MATRIX_FONT")
    if env:
        return env if os.path.isfile(env) else None
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
    from check_projection import find_font
    p = find_font()
    if not p:
        print("make_notify_marquee: SKIP — no outline font for the matrix extension "
              "(set EL_MATRIX_FONT); the ticker carries the authored glyphs only", file=sys.stderr)
    return p


def main_qml(font_path=None):
    """The marquee plasmoid — templates/marquee-main.qml.

    ⚑ THE ALPHA, THE HUE TABLES AND THE REGISTRY ARE THE ONLY HOLES, and all three
    are READS: the colours themselves are Kirigami.Theme bindings in the template.
    The registry carries the 5x8 font — the authored table plus the Latin-1
    extension rasterised from `font_path` (matrix_font() when None) — so arbitrary
    notification text renders as a dot-matrix display, and a char outside the
    charset renders as '?' rather than as a blank cell."""
    import templates.loader as TL
    return TL.render("marquee-main.qml", ghostAlpha=TS.ghost_alpha(),
                     hueTables=hue_tables_js(), fallbackFg=_hex(WL.colors_for(FALLBACK_VARIANT)[1]),
                     registry=DT.as_qml_js(MATRIX_DISPLAY,
                                           font_path=font_path or matrix_font()))


def hue_table(variant):
    """The variant's 12-bucket sender-hue table as hex colours (index = hue / 30),
    SOLVED by make_palette.hue_table at build time — a fallback bucket already
    holds fg, so the widget only ever looks up (relations.md §5a; check_rehue)."""
    import make_palette as MP
    ground, lit, ghost, _alpha = WL.colors_for(variant)
    return [_hex(col) for _h, col, _ok in MP.hue_table(lit, ground, ghost)]


def hue_tables_js():
    """ALL variants' tables as one JS object keyed by the variant's fg hex — the
    key the widget derives from its live litColor (catalog/one-theme.md)."""
    rows = []
    for v in VARIANTS:
        fg = _hex(WL.colors_for(v)[1])
        rows.append(f'"{fg}": [' + ", ".join(f'"{c}"' for c in hue_table(v)) + "]")
    return "({" + ", ".join(rows) + "})"


# ⚑ MatrixChar.qml AND MatrixField.qml WERE RETIRED (s124). MatrixChar was the
# per-character dot cell (⊕DOT, s65) and MatrixField the fixed ghost field (W34);
# since the s120 port the marquee paints its cells from the same registry bytes
# into ApertureField's backdrop and the field's pips are the LEDs — measured by
# check_qml_lint --uses: 0 of 12 documents instantiated either. The twin-of-
# SegmentChar contract (⊕DOT: a cell, a set of lit primitives; no shared
# substrate) now lives in ApertureField, whose pips are the primitives.
def aperture_field_component():
    """The field as an APERTURE INTEGRAL — templates/ApertureField.qml (W54): pips
    graded by a supersampled backdrop's coverage under each aperture, the scroll a
    number, no rebuild. The marquee's board since s120 (the port)."""
    import templates.loader as TL
    return TL.render("ApertureField.qml")


def aperture_probe_qml(templates_url="."):
    """templates/aperture-probe.qml — the field over a synthetic edge block, the gate's
    subject (check_aperture, W54). Never shipped; `templates_url` is where the
    harness finds ApertureField.qml. The ghost alpha is the palette's global one."""
    import templates.loader as TL
    import make_wallpaper_live as WL
    return TL.render("aperture-probe.qml", templates=templates_url,
                     ghostAlpha=f"{WL.global_alpha('looked_at'):.3f}")


# ⚑ Unifont (operator: "plain Unifont behind the mask") — installed 2026-09-22; before
# that fc-match fell back to Liberation Sans and the still was Liberation Mono. Its
# 8x16 cell against the 8-row field: at pixelSize = the field's height the em is
# two backdrop pixels per Unifont pixel, i.e. HALF a pip — a 2:1 downsample through
# the aperture; the 16-row viewport (W47's fold) is the 1:1 reading.
APERTURE_TEXT_FONT = "Unifont"
APERTURE_TEXT = "Hello 世界 42 ñ 🔔"   # + emoji (operator): colour glyphs are ink by ALPHA — the silhouette lights


# the transfer curve for text read at 2:1 (operator: the pinholes sheet entry was
# "really, really faded"); 1.0 is the identity — an authored value until W56's
# OCR objective tunes it
APERTURE_TEXT_GAMMA = 0.5
# the viewport (W47 folded into W54): Unifont's cell is 8x16, so the backdrop is 16
# rows and ONE Unifont pixel is one pip; the 8-row field looks through ONE band of it.
# Measured (s121): caps span rows 2-13 (12 rows) — no 8-row band holds them, which is
# what the vertical scroll is for; the x-height band, rows 6-13, is exactly 8 and
# shows lowercase whole. The still shows that band; the scroll is the animation.
APERTURE_BACKDROP_ROWS = 16
APERTURE_OFFSET_ROWS = 6


def aperture_text_probe_qml(templates_url=".", font=APERTURE_TEXT_FONT, text=APERTURE_TEXT,
                            gamma=APERTURE_TEXT_GAMMA, backdrop_rows=APERTURE_BACKDROP_ROWS,
                            offset_rows=APERTURE_OFFSET_ROWS):
    """templates/aperture-text-probe.qml — a Qt Text item as the backdrop (W54 step 3):
    the font Qt shapes, read 1:1 through the pinholes via the viewport (W47)."""
    import templates.loader as TL
    import make_wallpaper_live as WL
    return TL.render("aperture-text-probe.qml", templates=templates_url, font=font, text=text,
                     gamma=f"{gamma:.3f}", backdropRows=str(backdrop_rows), offsetRows=str(offset_rows),
                     ghostAlpha=f"{WL.global_alpha('looked_at'):.3f}")


def body_parser():
    """templates/marquee-body.js — notification body markup -> text + style runs."""
    import templates.loader as TL
    return TL.render("marquee-body.js")


def config_xml():
    """contents/config/main.xml — the settings' kcfg. The ghostAlpha DEFAULT is the
    palette's solved (global) alpha, filled here: the slider is a per-user override,
    so an unconfigured widget draws exactly what check_ghost_surfaces measured."""
    import templates.loader as TL
    return TL.render("marquee-config.kcfg", ghostAlpha=TS.ghost_alpha())


def config_qml():
    """contents/ui/configGeneral.qml — the settings page (clock pattern, W34 c)."""
    import templates.loader as TL
    return TL.render("marquee-config.qml")


CONFIG_MODEL = ('import org.kde.plasma.configuration\n\nConfigModel {\n'
                '    ConfigCategory {\n        name: "General"\n        icon: "view-list-text"\n'
                '        source: "configGeneral.qml"\n    }\n}\n')


def render_all(d):
    """Write the ONE package into d."""
    ui = os.path.join(d, "contents", "ui")
    cfg = os.path.join(d, "contents", "config")
    os.makedirs(ui, exist_ok=True)
    os.makedirs(cfg, exist_ok=True)
    open(os.path.join(d, "metadata.json"), "w").write(json.dumps(metadata(), indent=2))
    open(os.path.join(ui, "main.qml"), "w").write(main_qml())
    # the settings page (W34 c): the same three files the clock ships
    open(os.path.join(ui, "configGeneral.qml"), "w").write(config_qml())
    open(os.path.join(cfg, "main.xml"), "w").write(config_xml())
    open(os.path.join(cfg, "config.qml"), "w").write(CONFIG_MODEL)
    # ⚑ THE COMPONENT SHIPS BESIDE THE PLASMOID OR THE IMPORT RESOLVES TO
    # NOTHING.  main.qml instantiates ApertureField by bare name, which QML
    # resolves from the same directory — emitting one without the other gives
    # a widget that loads and draws an empty panel.
    open(os.path.join(ui, "ApertureField.qml"), "w").write(aperture_field_component())
    # the body-markup parser (W39): main.qml imports it by bare name
    open(os.path.join(ui, "marquee-body.js"), "w").write(body_parser())
    return d


if __name__ == "__main__":
    out = "/tmp/nm-el"
    render_all(out)
    print(f"rendered the notification-marquee plasmoid ({PACKAGE_ID}) into {out}; alpha={TS.ghost_alpha()}")
    for v in VARIANTS:
        print(f"  hue row for fg {_hex(WL.colors_for(v)[1])}: {v}")
