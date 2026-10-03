#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""make_firefox.py — the palette as a Firefox WebExtension theme (W15).

⚑ FIREFOX IS NOT CHROME WITH A DIFFERENT NAME.  make_chrome emits Chrome's
`theme.colors` vocabulary; Firefox's (MDN: manifest.json/theme, read
2026-09-21) is a different key set — `frame` and `tab_background_text` are
REQUIRED, popups, sidebars and toolbar fields have their own keys, and
`properties.color_scheme` tells the browser whether the theme is dark or
light. Both accept `[r, g, b]` arrays. Firefox loads a theme only when AMO has
signed it (bug 1545109), so the route is addons.mozilla.org — unlisted is
enough for self-use; W13 records it.

    make_firefox.py               # writes firefox/<variant>/manifest.json
    make_firefox.py --map         # theme key -> palette role (or the relation that solves it)
    make_firefox.py --dynamic     # writes dist/firefox-dynamic/: ONE extension carrying all six

⚑ ONE EXTENSION, SIX THEMES (W135).  A static theme carries one palette; an extension
with the `theme` permission applies any of them at runtime (browser.theme.update).
themes.json is GENERATED from manifest(v)["theme"] for every variant, so the dynamic
extension and the six static themes cannot drift. The options page is the chooser, and
the place AMO permits a paid reference "clearly identified as belonging to the add-on"
(W113); that text waits on the paid listings (life:W16). dist/ is build output.

⚑ EVERY COLOUR IS A ROLE OR A SOLVED COMPOSITE, NEVER A NUMBER.  Ground, panel,
view, text, accent, selection are parse_scheme roles. The three that are not
plain roles are the ghost relation on three pairs (relations.md §3b/§3d):
  toolbar_field_border / separators:  the SEEN ghost — fg_in over ground at ghost_alpha
  button_background_hover:            highlight over panel at the GLANCED-AT floor
  button_background_active:           highlight over panel at the LOOKED-AT floor
— the same solve make_union applies to Breeze's hover and indicator alphas.
"""
import json
import os
import sys

from emitters import atomic_write

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

VARIANTS = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
            "EL-Amber", "EL-Amber-Lit"]
VERSION = "1.0"

# theme.colors key -> palette role. Roles are parse_scheme keys, or one of the
# three composites named in the docstring.
KEYS = (
    ("frame", "ground"), ("frame_inactive", "ground"),
    ("ntp_background", "ground"), ("ntp_card_background", "panel"), ("ntp_text", "phosphor"),
    ("toolbar", "panel"), ("toolbar_text", "phosphor"), ("bookmark_text", "phosphor"),
    ("tab_background_text", "phosphor"), ("tab_text", "phosphor"),
    ("tab_selected", "panel"), ("tab_line", "accent"), ("tab_loading", "accent"),
    ("icons", "phosphor"), ("icons_attention", "accent"),
    ("toolbar_field", "view_bg"), ("toolbar_field_text", "phosphor"),
    ("toolbar_field_focus", "view_bg"), ("toolbar_field_text_focus", "phosphor"),
    ("toolbar_field_border", "ghost_seen"), ("toolbar_field_border_focus", "focus"),
    ("toolbar_field_highlight", "sel"), ("toolbar_field_highlight_text", "sel_fg"),
    ("toolbar_top_separator", "ghost_seen"), ("toolbar_bottom_separator", "ghost_seen"),
    ("toolbar_vertical_separator", "ghost_seen"),
    ("popup", "panel"), ("popup_text", "phosphor"), ("popup_border", "ghost_seen"),
    ("popup_highlight", "sel"), ("popup_highlight_text", "sel_fg"),
    ("sidebar", "ground"), ("sidebar_text", "phosphor"), ("sidebar_border", "ghost_seen"),
    ("sidebar_highlight", "sel"), ("sidebar_highlight_text", "sel_fg"),
    ("button_background_hover", "hover_fill"), ("button_background_active", "active_fill"),
)
REQUIRED = ("frame", "tab_background_text")


def _rgb(hexs):
    hexs = hexs.lstrip("#")
    return [int(hexs[i:i + 2], 16) for i in (0, 2, 4)]


def roles(variant):
    """{role: [r, g, b]} — parse_scheme's roles plus the three solved composites."""
    import cvd_gate as C
    import ghost_solve as GS
    import make_preview as MP
    import palette_graph as PG
    c = MP.parse_scheme(variant)
    out = {k: _rgb(v) for k, v in c.items() if isinstance(v, str) and v.startswith("#")}
    ground, panel, sel = tuple(out["ground"]), tuple(out["panel"]), tuple(out["sel"])
    out["ghost_seen"] = list(PG.composite(tuple(out["ghost"]), ground, float(c["ghost_alpha"])))
    a_h = GS.alpha_min(sel, panel, C.GHOST_VISIBLE_LC_GLANCED)
    a_a = GS.alpha_min(sel, panel, C.GHOST_VISIBLE_LC)
    out["hover_fill"] = list(PG.composite(sel, panel, a_h if a_h is not None else 1.0))
    out["active_fill"] = list(PG.composite(sel, panel, a_a if a_a is not None else 1.0))
    out["_alphas"] = {"hover": a_h, "active": a_a}
    return out


def manifest(variant):
    r = roles(variant)
    lit = variant.endswith("-Lit")
    return {
        "manifest_version": 2,
        "name": f"EL Openglo ({variant})",
        "version": VERSION,
        "description": f"Electroluminescent watch display — {variant}",
        "browser_specific_settings": {
            "gecko": {"id": f"el-openglo-{variant.lower()}@el-openglo.theme"}},
        "theme": {
            "colors": {key: r[role] for key, role in KEYS},
            "properties": {"color_scheme": "light" if lit else "dark"},
        },
    }


def render_all(variants, out_map):
    written = []
    for v in variants:
        d = out_map[v]
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "manifest.json")
        atomic_write(p, json.dumps(manifest(v), indent=2) + "\n")
        written.append(p)
    return written


DYNAMIC_ID = "el-openglo@el-openglo.theme"
DYNAMIC_OUT = os.path.join(ROOT, "dist", "firefox-dynamic")

BACKGROUND_JS = """// generated by make_firefox.py --dynamic (W135); themes.json is the palette, not this file
const DEFAULT = %(default)s;
async function apply() {
  const themes = await (await fetch(browser.runtime.getURL("themes.json"))).json();
  const {variant} = await browser.storage.local.get({variant: DEFAULT});
  await browser.theme.update(themes[variant] || themes[DEFAULT]);
}
browser.storage.onChanged.addListener(apply);
browser.runtime.onStartup.addListener(apply);
browser.runtime.onInstalled.addListener(apply);
apply();
"""

OPTIONS_HTML = """<!doctype html>
<meta charset="utf-8">
<title>EL Openglo</title>
<label for="variant">Variant</label>
<select id="variant"></select>
<script src="options.js"></script>
"""

OPTIONS_JS = """// generated by make_firefox.py --dynamic (W135)
(async () => {
  const themes = await (await fetch(browser.runtime.getURL("themes.json"))).json();
  const sel = document.getElementById("variant");
  for (const v of Object.keys(themes)) sel.add(new Option(v, v));
  sel.value = (await browser.storage.local.get({variant: %(default)s})).variant;
  sel.addEventListener("change", () => browser.storage.local.set({variant: sel.value}));
})();
"""


def dynamic_files(variants=VARIANTS, default="EL-Openglo"):
    """{relative path: text} for the ONE extension carrying every variant (W135)."""
    themes = {v: manifest(v)["theme"] for v in variants}
    d = json.dumps(default)
    return {
        "manifest.json": json.dumps({
            "manifest_version": 2,
            "name": "EL Openglo",
            "version": VERSION,
            "description": "Electroluminescent watch display: six phosphor palettes, chosen in the add-on's options",
            # AMO requires data_collection_permissions on every NEW extension (web-ext lint
            # MISSING_DATA_COLLECTION_PERMISSIONS, measured W142); this one collects nothing
            "browser_specific_settings": {"gecko": {
                "id": DYNAMIC_ID, "data_collection_permissions": {"required": ["none"]}}},
            "permissions": ["theme", "storage"],
            "background": {"scripts": ["background.js"]},
            "options_ui": {"page": "options.html"},
        }, indent=2) + "\n",
        "themes.json": json.dumps(themes, indent=2) + "\n",
        "background.js": BACKGROUND_JS % {"default": d},
        "options.html": OPTIONS_HTML,
        "options.js": OPTIONS_JS % {"default": d},
    }


def render_dynamic(out_dir=DYNAMIC_OUT, variants=VARIANTS):
    written = []
    for rel, text in dynamic_files(variants).items():
        p = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        atomic_write(p, text)
        written.append(p)
    return written


if __name__ == "__main__":
    if "--dynamic" in sys.argv:
        w = render_dynamic()
        print(f"make_firefox: wrote {len(w)} files of the dynamic extension under {DYNAMIC_OUT}")
        sys.exit(0)
    if "--map" in sys.argv:
        for key, role in KEYS:
            print(f"{key:30} <- {role}")
        r = roles("EL-Openglo")
        print(f"hover/active alphas (EL-Openglo): {r['_alphas']}")
        sys.exit(0)
    outs = {v: os.path.join(ROOT, "firefox", v) for v in VARIANTS}
    w = render_all(VARIANTS, outs)
    print(f"make_firefox: wrote {len(w)} manifests under firefox/")
