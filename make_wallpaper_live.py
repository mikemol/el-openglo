#!/usr/bin/env python3
"""Live wallpaper emitter (⊕WALLPAPER-LIVE) — the 8th palette surface, mounted
TWICE (desktop containment + lock screen) from ONE plugin.

A Plasma/Wallpaper QML package per variant: a WallpaperItem that fills the screen
with the void ground and draws a large centred phosphor seven-seg clock showing
the REAL current time (the system is up here, unlike the Plymouth boot stage, so
wall-clock is honestly sourceable — a true living watch face). Colors are baked
from the same scheme tokens (lit = stretch_lit, ghost = derive_ghost, void
ground), so it cannot drift.

FETCHED silent-fail traps (honored):
  - root MUST be WallpaperItem (org.kde.plasma.plasmoid), not plain Item;
  - metadata.json MUST carry "KPackageStructure":"Plasma/Wallpaper".
Config: wallpaper.configuration.<key>. `breathe` gates the continuous backlight
animation (rich on the lock mount, off/cheap on the desktop mount).
"""
import os
import json
import make_clock as MC
import make_preview as MP
import cvd_gate as C
# ⚑ GEOMETRY IS A TOKEN SET EXACTLY LIKE COLOUR.  This surface carried its own
# seven-seg map AND its own stroke table, hand-written INSIDE a QML f-string —
# which is why two separate gates were blind to them: check_geometry_source scans
# module-level assignments, and a table living in a string literal is not one;
# check_embedded_markup looks for markup strings, and found the QML but had no
# reason to care what was nested inside it.
#
# Measured after the swap: the substrate's projection is SEMANTICALLY IDENTICAL to
# what was hand-written here — same segments per digit, same (kind, x0, x1, y) per
# stroke. The tables were right; nothing could prove they would stay right.
import segment_topology as _ST
import ghost_solve as _GS

ROOT = os.path.dirname(os.path.abspath(__file__))

# The one lattice, projected to this surface's FORMAT ("7" digits).  A surface may
# choose a format; carrying a shape is a re-implementation.
#
# ⚑ LOWERCASE, AND THAT IS WHY THIS PROJECTION AND NOT `glyph7_letters`.  That one
# renames to A..G for the SVG wallpaper's table; the QML canvas keys its strokes by
# `seg7_strokes()`'s own a..g, so the two must be the same projection read at the
# same case or a digit silently lights nothing.
SEGS = _ST.seg7_strokes()
DIGIT = {ch: "".join(sorted(_ST.project(_ST.glyph16(ch), "7")))
         for ch in "0123456789"}


def _rgb(css):
    css = css.strip().strip('"').lstrip("#")
    return tuple(int(css[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return '"#%02x%02x%02x"' % rgb


def colors_for(variant):
    """Derive the same lit/ghost/void the clock plasmoid uses, from tokens."""
    t = MC.variant_tokens(variant) if hasattr(MC, "variant_tokens") else None
    # fall back to GRID lookup keyed by variant name
    from make_schemes import GRID
    ph, mode = _variant_key(variant)
    tok = [tt for (p, m), (tt, d) in GRID.items() if p == ph and m == mode][0]
    ground = tuple(int(x) for x in tok["view"].split(","))
    lit0 = _rgb(MC.rgbcss(tok, "focus"))
    litS = C.stretch_lit(lit0, ground)
    # ⚑ SOLVED, NOT SCANNED.  The balance point is y = sqrt(ab) in offset
    # luminance — the fixed point of the involution that exchanges the ghost's two
    # sides — so this is a closed form rather than the best of 99 samples.
    ghost = _GS.derive_ghost(litS, ground)
    return ground, litS, ghost


def _variant_key(variant):
    v = variant.lower()
    mode = "lit" if v.endswith("-lit") else "off"
    if "openglo" in v:
        ph = "openglo"
    elif "azure" in v:
        ph = "azure"
    else:
        ph = "amber"
    return ph, mode


def metadata(variant):
    return {
        "KPackageStructure": "Plasma/Wallpaper",
        "KPlugin": {
            "Id": f"org.el.openglo.live.{variant.lower().replace('-', '')}",
            "Name": f"EL Openglo Live ({variant})",
            "Description": f"Living electroluminescent watch face — {variant}",
            "License": "GPLv3",
            "Authors": [{"Name": "EL Openglo"}],
        },
        "X-Plasma-API-Minimum-Version": "6.0",
    }


def _qml_obj(table):
    """A Python table as a QML/JS object literal.

    ⚑ json.dumps IS THE RIGHT TOOL AND ALMOST THE WRONG ONE.  QML object literals
    are JSON-compatible for these shapes, so this is a serialisation rather than a
    hand-built string — and the stroke table holds TUPLES, which json renders as
    ARRAYS, which is exactly what the canvas indexes with spec[0]/spec[1]. Had it
    rendered them as anything else the digits would draw nothing, which is why the
    parity baseline compares the emitted document rather than this function."""
    return json.dumps(table, sort_keys=True)


def main_qml(variant):
    """The live wallpaper — templates/live-wallpaper-main.qml.

    ⚑ THE COLOURS AND THE GEOMETRY ARE HOLES; THE DOCUMENT IS A FILE.  This was
    120 lines of QML in an f-string, brace-doubled throughout, carrying two tables
    it had no business owning. Five holes go in; the document comes out."""
    ground, lit, ghost = colors_for(variant)
    import templates.loader as TL
    return TL.render("live-wallpaper-main.qml",
                     lit=_hex(lit), ghost=_hex(ghost), ground=_hex(ground),
                     seg=_qml_obj(DIGIT), stroke=_qml_obj(SEGS))


def config_main_xml():
    """The kcfg schema — templates/live-wallpaper-config.kcfg.

    ⚑ IT WAS AN IMPLICIT CONCATENATION, which is the same defect wearing a
    different shape: seven adjacent string literals, each ending in a visible
    `\\n`, reassembled at parse time. The AST sees ONE constant (which is why the
    scanner caught it), but a reader sees escape sequences instead of XML, and no
    schema validator sees it at all."""
    import templates.loader as TL
    return TL.render("live-wallpaper-config.kcfg")


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
        open(os.path.join(cfg, "main.xml"), "w").write(config_main_xml())
        written[v] = d
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/wplive-{v}" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "live wallpapers")
    for v in variants:
        g, l, gh = colors_for(v)
        print(f"  {v}: void={g} lit={l} ghost={gh}")
