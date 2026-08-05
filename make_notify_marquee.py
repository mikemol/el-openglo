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

    ⚑ THE COLOURS ARE THE ONLY THING THIS FUNCTION OWNS.  Everything else was 88
    lines of QML held in an f-string, brace-doubled throughout. Three holes go
    in; the document comes out."""
    ground, lit, ghost = WL.colors_for(variant)
    import templates.loader as TL
    return TL.render("marquee-main.qml", lit=_hex(lit), ghost=_hex(ghost),
                     ground=_hex(ground))



def render_all(variants, dir_map):
    written = {}
    for v in variants:
        d = dir_map[v]
        ui = os.path.join(d, "contents", "ui")
        os.makedirs(ui, exist_ok=True)
        open(os.path.join(d, "metadata.json"), "w").write(
            json.dumps(metadata(v), indent=2))
        open(os.path.join(ui, "main.qml"), "w").write(main_qml(v))
        written[v] = d
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/nm-{v}" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "notification-marquee plasmoids")
    for v in variants:
        g, l, gh = WL.colors_for(v)
        print(f"  {v}: void={g} lit={l}")
