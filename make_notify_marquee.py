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


def main_qml(variant):
    """The marquee plasmoid — templates/marquee-main.qml.

    ⚑ THE COLOURS AND THE REGISTRY ARE THE ONLY THINGS THIS FUNCTION OWNS, and it
    owns neither of them either — both are READS. Four holes go in; the document
    comes out. The registry carries the 5x7 font, so the ticker renders as a real
    dot-matrix display instead of as monospace text tinted phosphor."""
    ground, lit, ghost, alpha = WL.colors_for(variant)
    import templates.loader as TL
    return TL.render("marquee-main.qml", lit=_hex(lit), ghost=_hex(ghost),
                     ground=_hex(ground), ghostAlpha=alpha,
                     registry=DT.as_qml_js("5x7"))


def matrix_char_component():
    """The reusable dot-matrix character component — templates/MatrixChar.qml.

    The twin of make_segment_display.segment_char_component, and deliberately a
    SEPARATE component rather than a mode of it (⊕DOT: no shared substrate, one
    shared contract)."""
    import templates.loader as TL
    return TL.render("MatrixChar.qml")



def render_all(variants, dir_map):
    written = {}
    for v in variants:
        d = dir_map[v]
        ui = os.path.join(d, "contents", "ui")
        os.makedirs(ui, exist_ok=True)
        open(os.path.join(d, "metadata.json"), "w").write(
            json.dumps(metadata(v), indent=2))
        open(os.path.join(ui, "main.qml"), "w").write(main_qml(v))
        # ⚑ THE COMPONENT SHIPS BESIDE THE PLASMOID OR THE IMPORT RESOLVES TO
        # NOTHING.  main.qml instantiates MatrixChar by bare name, which QML
        # resolves from the same directory — emitting one without the other gives
        # a widget that loads and draws an empty panel.
        open(os.path.join(ui, "MatrixChar.qml"), "w").write(matrix_char_component())
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
