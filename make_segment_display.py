#!/usr/bin/env python3
"""Shared segment-display emitter (⊕SEGMENT-SUBSTRATE).

ONE geometry source under every surface. Previously the wallpaper, clock,
plymouth, and marquee each RE-IMPLEMENTED the segment shapes (a silo). This makes
segment_topology the single geometry emitter and each surface a render target that
consumes its output, choosing only the FORMAT its character set needs:
  digits-only (clock, boot)  -> project to "7"
  alphanumeric (marquee)     -> project to "22"
The subset lattice 7 c 14 c 16 c 22 (shared keys identical geometry) is what makes
projection sound — dropping segments a format lacks never moves the ones it keeps.

Every stroke (h/v/d) normalizes to endpoint form (ax,ay)-(bx,by); one renderer
thickens any line into a vector quad via a perpendicular offset, so horizontals,
verticals, AND diagonals draw through the same path — no per-kind special-casing,
and diagonals (needed for letters) come for free.

Emits a reusable QML `SegmentChar` component (declarative PathLine quads — the
idiom proven to render, unlike a JS function in a path binding) plus the baked
geometry + glyph tables from the substrate. Surfaces instantiate it.
"""
import json
import segment_topology as ST


def _endpoints(spec):
    """Normalize any stroke to (ax, ay, bx, by) in unit-grid coords."""
    k = spec[0]
    if k == "h":
        return (spec[1], spec[3], spec[2], spec[3])
    if k == "v":
        return (spec[1], spec[2], spec[1], spec[3])
    if k == "d":
        return (spec[1][0], spec[1][1], spec[2][0], spec[2][1])
    raise ValueError(f"unknown stroke kind {k!r}")


def geometry_js():
    """The canonical geometry as a JS object literal: {seg: [ax,ay,bx,by]} for all
    GEOM22 strokes, from the substrate (single source)."""
    geo = {k: list(_endpoints(ST.GEOM22[k])) for k in ST.SEG22}
    return json.dumps(geo)


def glyphs_js(fmt):
    """{char: [lit segment labels]} projected to `fmt`, from the substrate glyph
    tables (lookup dictionary — authored, injectivity-gated, not computed)."""
    out = {}
    for tbl in (ST.DIGITS16, ST.LETTERS16, ST.SYMBOLS16):
        for ch, segs in tbl.items():
            g = set(segs.split()) if segs else set()
            projected = ST.project(g, fmt) if g else set()
            out[ch] = sorted(projected)
    return json.dumps(out)


def segment_char_component():
    """The reusable QML component: renders one character as vector segment quads.
    Every stroke is thickened via a perpendicular offset (handles h/v/d). Active
    segments = the char's projected glyph; inactive = subordinate ghost. Carries
    the three lit/ghost channels (ghost opacity, stroke-weight, bloom).

    ⚑ THE QML LIVES IN templates/SegmentChar.qml, NOT HERE.  It was 87 lines of
    markup held as a Python string: un-previewable, un-lintable by qmllint, and
    invisible to a diff except as "the .py changed". As a file it opens in a QML
    editor and its braces need no escaping. This function is now the ACCESSOR,
    which is what every caller already expected it to be."""
    import templates.loader as TL
    return TL.render("SegmentChar.qml")



if __name__ == "__main__":
    print("geometry strokes:", len(json.loads(geometry_js())))
    g7 = json.loads(glyphs_js("7"))
    print("digits at fmt 7:", {d: g7[d] for d in "0123456789" if d in g7})
    print("component chars:", len(segment_char_component()), "bytes")
