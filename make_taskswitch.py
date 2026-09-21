#!/usr/bin/env python3
"""Alt+Tab window switcher emitter (⊕TASKSWITCH; W31).

A KWin/WindowSwitcher package per variant: the task list as a phosphor
departure board — the selected window LIT, the rest the GHOST, on the void.
The QML is templates/taskswitch-main.qml with four colour holes filled from
the same tokens the marquee and live wallpaper read (make_wallpaper_live.
colors_for); the package shape and the switcher contract were read from the
host's own /usr/share/kwin/tabbox/compact (Plasma 6.7, 2026-09-21). Selected
by the Look-and-Feel defaults: [kwinrc][TabBox] LayoutName=<package id>.

    make_taskswitch.py            # print EL-Openglo's main.qml
"""
import json
import os
import sys

import make_wallpaper_live as WL   # colors_for: the token-derived ground/lit/ghost/alpha

VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
            "EL-Amber", "EL-Amber-Lit")


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def package_id(variant):
    return f"org.el.taskswitch.{variant.lower().replace('-', '')}"


def metadata(variant):
    return {
        "KPackageStructure": "KWin/WindowSwitcher",
        "KPlugin": {
            "Authors": [{"Name": "EL Openglo"}],
            "Description": f"Phosphor departure-board window switcher — {variant}",
            "Icon": "preferences-system-windows-switcher-compact",
            "Id": package_id(variant),
            "License": "GPLv3",
            "Name": f"EL Openglo ({variant})",
        },
    }


def main_qml(variant):
    ground, lit, ghost, alpha = WL.colors_for(variant)
    import templates.loader as TL
    return TL.render("taskswitch-main.qml", lit=_hex(lit), ghost=_hex(ghost),
                     ground=_hex(ground), ghostAlpha=alpha)


def defaults_fragment(variant):
    """The Look-and-Feel `defaults` group that selects this switcher."""
    return f"[kwinrc][TabBox]\nLayoutName={package_id(variant)}\n\n"


def render_all(variants, dir_map):
    """Write metadata.json + contents/ui/main.qml per variant into dir_map[v]."""
    written = {}
    for v in variants:
        d = dir_map[v]
        ui = os.path.join(d, "contents", "ui")
        os.makedirs(ui, exist_ok=True)
        open(os.path.join(d, "metadata.json"), "w").write(json.dumps(metadata(v), indent=2))
        open(os.path.join(ui, "main.qml"), "w").write(main_qml(v))
        written[v] = d
    return written


if __name__ == "__main__":
    print(main_qml("EL-Openglo"))
    sys.exit(0)
