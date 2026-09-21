#!/usr/bin/env python3
"""theme_probe.py — resolve Kirigami.Theme bindings against a VARIANT, headless, with the real engine.

⚑ MEASURED 2026-09-22 (W35). A QML-defined stub of Kirigami.Theme cannot exist:
`Kirigami.Theme.colorSet:` is an ATTACHED property, which only a C++ type can
provide ("Non-existent attached object"). But the REAL module resolves fine
under Qt's `qml` runner on the offscreen platform, given: the KDE platform
theme (QT_QPA_PLATFORMTHEME=kde), Kirigami's org.kde.desktop platform plugin
(QT_QUICK_CONTROLS_STYLE=org.kde.desktop), a WIDGETS application (`--apptype
widget` — the platform theme hands its palette to QApplication), and a private
XDG_CONFIG_HOME whose kdeglobals IS the variant's .colors file. The colours
arrive one event-loop turn after load, so the probe reads them from a timer.
Result for EL-Amber: View textColor #ffd499 = fg, backgroundColor #140f08 =
view, disabledTextColor #e5bf89 = fg_in — the roles catalog/one-theme.md maps.

This is what "a bound surface follows the active scheme" means, measured on
this host without touching the operator's desktop: the private kdeglobals is
plasma-apply-colorscheme in a sandbox.

    theme_probe.py EL-Amber        # print the resolved View/Window roles

resolve(variant, bindings) runs the BINDING LINES an emitter produced, verbatim,
inside a probe root, so a check asserts what the emitted text resolves to, not
what it says. None when the qml runner is absent (a SKIP for the caller).
WEAKNESS: the probe root is an Item, not the surface's real root (KWin's
TabBoxSwitcher cannot load headless); a binding whose value depends on the
surface's own hierarchy (colorSet inheritance from a parent) resolves here as
it would at the root. ~0.6 s wall of qml per variant.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
QML = "/usr/lib64/qt6/bin/qml"
SCHEMES = "/usr/share/color-schemes"

# the probe document is templates/theme-probe.qml (two holes: the binding lines, the reads)


def scheme_path(variant):
    """The variant's .colors: the tree's emission if present, else the installed one."""
    for p in (os.path.join(ROOT, f"{variant}.colors"), os.path.join(SCHEMES, f"{variant}.colors")):
        if os.path.isfile(p):
            return p
    return None


def env_for(variant, xdg):
    """The environment under which the real Kirigami.Theme reads `variant`."""
    with open(scheme_path(variant), encoding="utf-8") as f:
        open(os.path.join(xdg, "kdeglobals"), "w", encoding="utf-8").write(f.read())
    return dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QPA_PLATFORMTHEME="kde",
                QT_QUICK_CONTROLS_STYLE="org.kde.desktop", XDG_CURRENT_DESKTOP="KDE",
                XDG_CONFIG_HOME=xdg, QT_LOGGING_RULES="kf.kirigami.platform=false")


def resolve(variant, bindings, names):
    """{name: '#rrggbb'} for each property `names` declares, after `bindings` (QML lines,
    verbatim from an emission) run at the probe root under `variant`'s scheme."""
    if not os.path.isfile(QML) or scheme_path(variant) is None:
        return None
    reads = ", ".join(f'"{n}": String(probe.{n})' for n in names)
    import templates.loader as TL
    doc = TL.render("theme-probe.qml", bindings=bindings, reads=reads)
    with tempfile.TemporaryDirectory() as td:
        xdg = os.path.join(td, "xdg")
        os.makedirs(xdg)
        p = os.path.join(td, "probe.qml")
        open(p, "w", encoding="utf-8").write(doc)
        r = subprocess.run([QML, "--apptype", "widget", p], env=env_for(variant, xdg),
                           capture_output=True, text=True, timeout=60)
    for line in (r.stdout + r.stderr).splitlines():
        if "RESULT " in line:
            return json.loads(line.split("RESULT ", 1)[1])
    raise RuntimeError(f"theme_probe: no RESULT for {variant} (rc={r.returncode}): {(r.stderr or r.stdout)[-400:]}")


def binding_block(qml, names):
    """The emitted lines that declare `names` plus the Kirigami.Theme.colorSet/inherit lines."""
    keep = []
    for line in qml.splitlines():
        s = line.strip()
        if s.startswith("Kirigami.Theme.colorSet:") or s.startswith("Kirigami.Theme.inherit:"):
            keep.append("    " + s)
        elif any(re.match(rf"property color {n}\b", s) for n in names):
            keep.append("    " + s)
    return "\n".join(keep)


if __name__ == "__main__":
    v = sys.argv[1] if len(sys.argv) > 1 else "EL-Amber"
    block = ("    Kirigami.Theme.colorSet: Kirigami.Theme.View\n    Kirigami.Theme.inherit: false\n"
             "    property color lit: Kirigami.Theme.textColor\n"
             "    property color ghost: Kirigami.Theme.disabledTextColor\n"
             "    property color ground: Kirigami.Theme.backgroundColor\n"
             "    property color hot: Kirigami.Theme.activeTextColor\n")
    print(json.dumps(resolve(v, block, ["lit", "ghost", "ground", "hot"]), indent=1))
