#!/usr/bin/env python3
"""plasma_rewrite.py — the Plasma-runtime rewrite BOTH headless harnesses apply.

render_qml (clock, switcher, live-wallpaper, pinholes) and check_marquee_live (the
marquee) each load an emitted Plasma surface in Qt's plain `qml` runner. Its root
is PlasmoidItem / WallpaperItem, types only Plasma's applet loader can create, and
it reads `plasmoid.configuration` / `wallpaper.configuration`. The rewrite is:

  SUBSTITUTIONS    three anchored substitutions on the emitted text — the root type
                   becomes a plain Item carrying the two representation properties,
                   the org.kde.plasma imports are dropped;
  _kcfg_defaults   the kcfg's defaults, typed — the `configuration` the harness
                   supplies in Plasma's place.

⚑ WHY IT IS ITS OWN MODULE (W61 follow-up). The per-output key hashes the import
closure of the module that owns a job's stager. check_marquee_live imported
render_qml for these two names alone, so a comment in render_qml re-keyed 55 of 56
outputs. Owned here, each harness's closure reaches only what it runs; an edit HERE
correctly re-keys both kinds, because both run it.

WEAKNESS: the rewrite is textual (anchored regexes), not a QML parse; a template
whose root line moves defeats it, and render_qml's switcher rewrite refuses loudly
on a no-match where this one does not.
"""
import re

# root-type rewrite: the Plasma container becomes a sized Item that instantiates
# its own fullRepresentation, exactly as the applet loader would
SUBSTITUTIONS = (
    (r"^import org\.kde\.plasma\.[^\n]*\n", ""),
    # org.kde.kirigami is KEPT (W35): the real module loads headless, and a bound
    # surface reads Kirigami.Theme — theme_probe.env_for makes it resolve a variant
    (r"^PlasmoidItem \{",
     "Item {\n    property var preferredRepresentation\n"
     "    property Component fullRepresentation\n"
     "    Loader { anchors.fill: parent; sourceComponent: parent.fullRepresentation }"),
    (r"^WallpaperItem \{", "Item {"),
)


def _kcfg_defaults(xml_text):
    """{name: default} from a kcfg, typed."""
    out = {}
    for m in re.finditer(r'<entry name="(\w+)" type="(\w+)"><default>([^<]*)</default>',
                         xml_text):
        name, typ, val = m.groups()
        out[name] = ({"Bool": lambda v: v == "true", "Double": float, "Int": int}
                     .get(typ, str))(val)
    return out
