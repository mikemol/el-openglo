#!/usr/bin/env python3
"""Notification-marquee plasmoid emitter (⊕NOTIFY-MARQUEE).

A panel widget that SUBSUMES the occluding notification popups into a phosphor
scrolling ticker (an airport departure-board for your desktop). It restores the
behavior late Plasma 4 had before Plasma 5 replaced the ticker with popups.

Architecture (fetched): reads the PUBLIC NotificationManager.Notifications model
(import org.kde.notificationmanager) — the same feed the stock applet consumes —
rather than trying to become the D-Bus notification server. Root is PlasmoidItem
(KF6), entry ui/main.qml, KPackageStructure=Plasma/Applet. Colors bake from the
scheme tokens like every other emitter (9th emission surface). A companion helper
suppresses the stock popups (plasmanotifyrc) so the marquee replaces them.

Degrades gracefully: if the model is empty or the import is unavailable, the
widget shows an idle phosphor face rather than crashing.
"""
import os
import json
import make_wallpaper_live as WL   # reuse colors_for (token-derived lit/ghost/void)
# ⚑ THIS SURFACE IS A DOT-MATRIX DISPLAY, NOT A SEGMENT ONE, AND NOT STYLED TEXT.
# It rendered `font.family: "monospace"` — a phosphor ticker drawn in whatever the
# system serves — because ⊕NOTIFY-MATRIXRENDER was never built. The obvious repair
# (project to "22" and draw segments) is the one ⊕NOTIFY-SEGRENDER already tried
# and moved to RESIDUE: ⊕DOT rejected "matrix as FORMATS['5x7'], reuse project()"
# outright, because a segment is a subset of a topology and a pixel-cell is a
# raster — no shared substrate. The abstraction was lifted one level instead, so
# this consumes THE REGISTRY and dispatches on `kind`.
import display_types as DT


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def metadata(variant):
    return {
        "KPackageStructure": "Plasma/Applet",
        "KPlugin": {
            "Id": f"org.el.notifymarquee.{variant.lower().replace('-', '')}",
            "Name": f"EL Notification Marquee ({variant})",
            "Description": "Phosphor scrolling ticker that subsumes notification popups",
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


def main_qml(variant, font_path=None):
    """The marquee plasmoid — templates/marquee-main.qml.

    ⚑ THE COLOURS AND THE REGISTRY ARE THE ONLY THINGS THIS FUNCTION OWNS, and it
    owns neither of them either — both are READS. Four holes go in; the document
    comes out. The registry carries the 5x8 font — the authored table plus the
    Latin-1 extension rasterised from `font_path` (matrix_font() when None) — so
    arbitrary notification text renders as a dot-matrix display, and a char
    outside the charset renders as '?' rather than as a blank cell."""
    ground, lit, ghost, alpha = WL.colors_for(variant)
    import templates.loader as TL
    return TL.render("marquee-main.qml", lit=_hex(lit), ghost=_hex(ghost),
                     ground=_hex(ground), ghostAlpha=alpha,
                     hueTable=hue_table_js(variant),
                     registry=DT.as_qml_js(MATRIX_DISPLAY,
                                           font_path=font_path or matrix_font()))


def hue_table_js(variant):
    """The variant's 12-bucket sender-hue table as a JS array of hex colours
    (index = hue / 30), SOLVED by make_palette.hue_table at build time — a
    fallback bucket already holds fg, so the widget only ever looks up
    (relations.md §5a; the gate is check_rehue's)."""
    import make_palette as MP
    ground, lit, ghost, _alpha = WL.colors_for(variant)
    return "[" + ", ".join(f'"{_hex(col)}"' for _h, col, _ok in MP.hue_table(lit, ground, ghost)) + "]"


def matrix_char_component():
    """The reusable dot-matrix character component — templates/MatrixChar.qml.

    The twin of make_segment_display.segment_char_component, and deliberately a
    SEPARATE component rather than a mode of it (⊕DOT: no shared substrate, one
    shared contract)."""
    import templates.loader as TL
    return TL.render("MatrixChar.qml")


def matrix_field_component():
    """The FIXED dot field — templates/MatrixField.qml: every unlit LED bezel to
    bezel, drawn once; the characters scroll lit dots over it (W34, the
    operator's live report that the ghost pips scrolled with the glyphs)."""
    import templates.loader as TL
    return TL.render("MatrixField.qml")



def body_parser():
    """templates/marquee-body.js — notification body markup -> text + style runs."""
    import templates.loader as TL
    return TL.render("marquee-body.js")


def config_xml(variant):
    """contents/config/main.xml — the settings' kcfg. The ghostAlpha DEFAULT is the
    palette's solved alpha, filled here: the slider is a per-user override, so an
    unconfigured widget draws exactly what check_ghost_surfaces measured."""
    _g, _l, _gh, alpha = WL.colors_for(variant)
    import templates.loader as TL
    return TL.render("marquee-config.kcfg", ghostAlpha=alpha)


def config_qml():
    """contents/ui/configGeneral.qml — the settings page (clock pattern, W34 c)."""
    import templates.loader as TL
    return TL.render("marquee-config.qml")


CONFIG_MODEL = ('import org.kde.plasma.configuration\n\nConfigModel {\n'
                '    ConfigCategory {\n        name: "General"\n        icon: "view-list-text"\n'
                '        source: "configGeneral.qml"\n    }\n}\n')


def render_all(variants, dir_map):
    written = {}
    for v in variants:
        d = dir_map[v]
        ui = os.path.join(d, "contents", "ui")
        cfg = os.path.join(d, "contents", "config")
        os.makedirs(ui, exist_ok=True)
        os.makedirs(cfg, exist_ok=True)
        open(os.path.join(d, "metadata.json"), "w").write(
            json.dumps(metadata(v), indent=2))
        open(os.path.join(ui, "main.qml"), "w").write(main_qml(v))
        # the settings page (W34 c): the same three files the clock ships
        open(os.path.join(ui, "configGeneral.qml"), "w").write(config_qml())
        open(os.path.join(cfg, "main.xml"), "w").write(config_xml(v))
        open(os.path.join(cfg, "config.qml"), "w").write(CONFIG_MODEL)
        # ⚑ THE COMPONENT SHIPS BESIDE THE PLASMOID OR THE IMPORT RESOLVES TO
        # NOTHING.  main.qml instantiates MatrixChar by bare name, which QML
        # resolves from the same directory — emitting one without the other gives
        # a widget that loads and draws an empty panel.
        open(os.path.join(ui, "MatrixChar.qml"), "w").write(matrix_char_component())
        open(os.path.join(ui, "MatrixField.qml"), "w").write(matrix_field_component())
        # the body-markup parser (W39): main.qml imports it by bare name
        open(os.path.join(ui, "marquee-body.js"), "w").write(body_parser())
        written[v] = d
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/nm-{v}" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "notification-marquee plasmoids")
    for v in variants:
        g, l, gh, a = WL.colors_for(v)
        print(f"  {v}: void={g} lit={l} ghost={gh}@{a}")
