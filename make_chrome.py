#!/usr/bin/env python3
"""Chrome/Chromium theme emitter (⊕CHROME-THEME).

A Chrome theme is the FOURTH emission target of the EL palette (peer of the
color scheme, wallpaper, Global-Theme preview, widget icon). It reads the SAME
tokens via make_preview.parse_scheme, so it cannot drift from the theme. Output
is a manifest.json per variant (manifest v3, `theme.colors` RGB triples) —
loadable unpacked via chrome://extensions, independent of GTK.
"""
import os, json
import make_preview as MP

ROOT = os.path.dirname(os.path.abspath(__file__))
VERSION = "1.0"


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def manifest(variant):
    """Build the Chrome theme manifest for a variant from its scheme tokens.
    ground -> frame/ntp background; phosphor -> text; accent -> toolbar/links."""
    c = MP.parse_scheme(variant)          # {ground, panel, phosphor, accent, sel}
    ground = _rgb(c["ground"])
    panel = _rgb(c["panel"])
    phosphor = _rgb(c["phosphor"])
    accent = _rgb(c["accent"])
    return {
        "manifest_version": 3,
        "version": VERSION,
        "name": f"EL Openglo ({variant})",
        "description": f"Electroluminescent watch display — {variant}",
        "theme": {
            "colors": {
                "frame": ground,
                "frame_inactive": ground,
                "toolbar": panel,
                "ntp_background": ground,
                "ntp_text": phosphor,
                "ntp_link": accent,
                "tab_text": phosphor,
                "tab_background_text": phosphor,
                "bookmark_text": phosphor,
                "button_background": panel,
            },
            "tints": {
                # keep buttons neutral so the accent isn't double-applied
                "buttons": [-1.0, -1.0, -1.0],
            },
            "properties": {
                "ntp_background_alignment": "center",
            },
        },
    }


def render_all(variants, out_dir_map):
    """Write manifest.json per variant into out_dir_map[variant]/manifest.json."""
    written = []
    for v in variants:
        m = manifest(v)
        d = out_dir_map[v]
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "manifest.json")
        open(p, "w").write(json.dumps(m, indent=2))
        written.append(p)
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/chrome-{v}" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "Chrome themes")
    for v in variants:
        m = manifest(v)
        print(" ", v, "frame", m["theme"]["colors"]["frame"],
              "text", m["theme"]["colors"]["ntp_text"])
