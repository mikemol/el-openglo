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
DIGIT = {ch: "".join(sorted(_ST.project(_ST.glyph16(ch, strict=True), "7")))
         for ch in "0123456789"}                  # strict: a missing digit is a defect


def _rgb(css):
    css = css.strip().strip('"').lstrip("#")
    return tuple(int(css[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return '"#%02x%02x%02x"' % rgb


def colors_for(variant, parsing="looked_at"):
    """(ground, lit, ghost, ghost_alpha) — READ from the palette's tokens, not re-derived.

    `parsing` picks the alpha: "looked_at" (the clock, the marquee you read) or
    "glanced_at" (the wallpaper, splash, plymouth — surfaces where the ghost must
    recede further from lit; W12, relations.md §3c).

    ⚑ THIS DERIVED ITS OWN LIT AND GHOST, AND SO DID EVERY OTHER SURFACE.  It took
    `focus` (the ACCENT) as lit, pushed it through cvd_gate.stretch_lit and then
    ghost_solve.derive_ghost — the session-39 ⊕CONTRAST-STRETCH pipeline, written
    before the palette solver existed and never retired when make_palette.solve_lit
    took over the same "push lit away from ground" invariant. Measured 2026-09-20
    (scripts/check_ghost_surfaces.py): 24 of 24 surface×variant emissions differed
    from the palette, so the solver's fg/fg_in — and every fix made to fg_in
    (alpha solved, ghost solved THROUGH it, floor in APCA) — reached the .colors
    files and no display. Operator ruling 2026-09-20 (W8): one colour chain.
    The token dict is the authority; this function is a READ of it, shared by the
    live wallpaper and the marquee."""
    from make_schemes import GRID
    ph, mode = _variant_key(variant)
    tok = [tt for (p, m), (tt, d) in GRID.items() if p == ph and m == mode][0]
    ground = tuple(int(x) for x in tok["view"].split(","))
    lit = tuple(int(x) for x in tok["fg"].split(","))
    ghost = tuple(int(x) for x in tok["fg_in"].split(","))
    if parsing not in ("looked_at", "glanced_at"):
        raise ValueError(f"colors_for: unknown parsing mode {parsing!r}")
    key = "ghost_alpha" if parsing == "looked_at" else "ghost_alpha_glanced"
    alpha = float(tok[key])
    return ground, lit, ghost, alpha


ALL_VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit")


def global_alpha(parsing="looked_at"):
    """The solved ghost alpha for `parsing`, ONE value across every variant — or a
    refusal. ⊕ONE-THEME (W35): a single package bakes it as a constant, which is
    honest only while the solve keeps it global (0.566 looked-at, 0.309 glanced-at
    since W23); if a future solve makes it per variant, this refuses and the
    six-row-lookup fallback in catalog/one-theme.md applies."""
    alphas = {v: colors_for(v, parsing)[3] for v in ALL_VARIANTS}
    if len(set(alphas.values())) != 1:
        raise ValueError(f"the {parsing} ghost alpha is per variant ({alphas}); a single "
                         f"package cannot bake it — see catalog/one-theme.md, Residue")
    return next(iter(alphas.values()))


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


# ⚑ ONE PACKAGE, THE VARIANT IS THE ACTIVE COLOUR SCHEME (⊕ONE-THEME, W35):
# lit / ghost / void are Kirigami.Theme roles under View; the glanced alpha is
# global and baked.
PACKAGE_ID = "org.el.openglo.live"


def metadata():
    return {
        "KPackageStructure": "Plasma/Wallpaper",
        "KPlugin": {
            "Id": PACKAGE_ID,
            "Name": "EL Openglo Live",
            "Description": "Living electroluminescent watch face, coloured by the active scheme",
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


def main_qml():
    """The live wallpaper — templates/live-wallpaper-main.qml.

    ⚑ THE GEOMETRY AND THE ALPHA ARE HOLES; THE DOCUMENT IS A FILE.  This was 120
    lines of QML in an f-string, brace-doubled throughout, carrying two tables it
    had no business owning. Since W35 the colours are not holes either: the
    template binds them to the active scheme's roles (one package)."""
    import templates.loader as TL
    # pitch / stroke / dot from the substrate's module metrics, in U (H = 4U);
    # the lit stroke at weight=1 is 1.25x the base
    import segment_topology as _ST
    m = _ST.metrics(4.0)
    # ⚑ THE TABLES ARE THE DISPLAY'S NOW (W33, s133). This surface used to carry
    # `seg` (a glyph map) and `stroke` (a geometry table) in ITS OWN spelling,
    # for its own Canvas painter. Since it mounts SegmentChar it passes the
    # display's tables — the SAME ones make_clock emits, from the same substrate
    # call — so the two mounts cannot drift in geometry even by accident.
    import make_clock as _MC
    return TL.render("live-wallpaper-main.qml",
                     ghostAlpha=global_alpha("glanced_at"),     # ambient: glanced
                     tables=_MC.qml_tables(),
                     pitch=f"{m['pitch']:.3f}", strokeBase=f"{m['stroke'] / 1.25:.3f}",
                     dotR=f"{m['dot'] / 2:.3f}", colonAdvance=f"{m['colon_advance']:.3f}")


def config_main_xml():
    """The kcfg schema — templates/live-wallpaper-config.kcfg.

    ⚑ IT WAS AN IMPLICIT CONCATENATION, which is the same defect wearing a
    different shape: seven adjacent string literals, each ending in a visible
    `\\n`, reassembled at parse time. The AST sees ONE constant (which is why the
    scanner caught it), but a reader sees escape sequences instead of XML, and no
    schema validator sees it at all."""
    import templates.loader as TL
    return TL.render("live-wallpaper-config.kcfg")


def render_all(d):
    """Write the ONE package into d."""
    ui = os.path.join(d, "contents", "ui")
    cfg = os.path.join(d, "contents", "config")
    os.makedirs(ui, exist_ok=True)
    os.makedirs(cfg, exist_ok=True)
    open(os.path.join(d, "metadata.json"), "w").write(json.dumps(metadata(), indent=2))
    open(os.path.join(ui, "main.qml"), "w").write(main_qml())
    # ⚑ THE DISPLAY SHIPS BESIDE THE MOUNT OR THE WALLPAPER DOES NOT LOAD.
    # main.qml instantiates SegmentChar by bare name, which QML resolves from the
    # same directory. Measured LIVE, s134 (the operator's shell after emerging the
    # merge): "SegmentChar is not a type" and the wallpaper failed to load — I had
    # added this line to make_clock and not here, and the emitters' own gates
    # could not see it because they read the emitted TEXT, never the directory.
    import make_segment_display as SD
    open(os.path.join(ui, "SegmentChar.qml"), "w").write(SD.segment_char_component())
    open(os.path.join(cfg, "main.xml"), "w").write(config_main_xml())
    return d


if __name__ == "__main__":
    out = "/tmp/wplive-el"
    render_all(out)
    print(f"rendered the live wallpaper ({PACKAGE_ID}) into {out}; glanced alpha={global_alpha('glanced_at')}")
