#!/usr/bin/env python3
"""Alt+Tab window switcher emitter (⊕TASKSWITCH; W31 — ONE package since W35, ⊕ONE-THEME).

A KWin/WindowSwitcher package: the task list as a phosphor departure board —
the selected window LIT, the rest the GHOST, on the void. The QML is
templates/taskswitch-main.qml; the package shape and the switcher contract
were read from the host's own /usr/share/kwin/tabbox/compact (Plasma 6.7,
2026-09-21). Selected by the Look-and-Feel defaults: [kwinrc][TabBox]
LayoutName=<package id>.

⚑ ONE PACKAGE, THE VARIANT IS THE ACTIVE COLOUR SCHEME (operator: "a single
theme whose color variant could be selected"; catalog/one-theme.md). The
colours are no longer holes: lit / ghost / void are Kirigami.Theme's
textColor / disabledTextColor / backgroundColor under colorSet View — the
same KColorScheme roles make_schemes.emit_colors writes fg / fg_in / view
into — so applying EL-Amber.colors IS selecting amber. The one thing that is
not a role, the ghost alpha, is GLOBAL across the variants since W23 and is
baked as a constant; ghost_alpha() refuses if a future solve makes it differ.

    make_taskswitch.py            # print main.qml
"""
import json
import os
import sys

import make_wallpaper_live as WL   # colors_for: the token-derived ground/lit/ghost/alpha
from emitters import LICENSE_SPDX   # the one licence id (W44)
from emitters import atomic_write

# the variants whose solved alpha must agree for the constant to be honest
VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
            "EL-Amber", "EL-Amber-Lit")
PACKAGE_ID = "org.el.taskswitch"


def ghost_alpha():
    """The solved looked-at ghost alpha, ONE value across every variant — or a refusal
    (make_wallpaper_live.global_alpha owns the measurement; the glanced twin is there too)."""
    return WL.global_alpha("looked_at")


def package_id():
    return PACKAGE_ID


def metadata():
    return {
        "KPackageStructure": "KWin/WindowSwitcher",
        "KPlugin": {
            "Authors": [{"Name": "EL Openglo"}],
            "Description": "Phosphor departure-board window switcher, coloured by the active scheme",
            "Icon": "preferences-system-windows-switcher-compact",
            "Id": PACKAGE_ID,
            "License": LICENSE_SPDX,
            "Name": "EL Openglo",
        },
    }


def main_qml():
    import templates.loader as TL
    return TL.render("taskswitch-main.qml", ghostAlpha=ghost_alpha())


def defaults_fragment():
    """The Look-and-Feel `defaults` group that selects this switcher (every variant's LnF)."""
    return f"[kwinrc][TabBox]\nLayoutName={PACKAGE_ID}\n\n"


def render_all(d):
    """Write metadata.json + contents/ui/main.qml into d (one package)."""
    ui = os.path.join(d, "contents", "ui")
    os.makedirs(ui, exist_ok=True)
    atomic_write(os.path.join(d, "metadata.json"), json.dumps(metadata(), indent=2))
    atomic_write(os.path.join(ui, "main.qml"), main_qml())
    return d


if __name__ == "__main__":
    print(main_qml())
    sys.exit(0)
