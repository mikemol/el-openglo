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
    the three lit/ghost channels (ghost opacity, stroke-weight, bloom)."""
    return '''// SegmentChar — one character as vector segments off the shared substrate.
// Generated from segment_topology (⊕SEGMENT-SUBSTRATE); do not hand-edit geometry.
import QtQuick
import QtQuick.Shapes

Item {
    id: sc
    property var geom: ({})          // {seg: [ax,ay,bx,by]} unit-grid
    property var glyphs: ({})        // {char: [lit segs]}
    property string ch: " "
    property real u: 20              // unit; digit box is 2u x 4u (x 5u with descender)
    property color litColor: "white"
    property color ghostColor: "gray"
    property real glow: 1.0
    property real bloomStrength: 0.30
    property real litHalf: u*0.20    // lit stroke half-width
    property real ghostHalf: u*0.13  // ghost thinner (stroke-weight channel)
    property real endGap: u*0.10     // pull ends in so segments don't overlap
    // explicit size = the digit cell (2u wide x 5u tall incl. descender band), so
    // the per-segment Items (anchors.fill: parent) have real bounds — without this
    // they fill a 0-size box and strokes clip to nothing.
    implicitWidth: u*2.4
    implicitHeight: u*5
    width: implicitWidth
    height: implicitHeight

    property var litSet: glyphs[ch] || []

    Repeater {
        model: Object.keys(sc.geom)
        Item {
            anchors.fill: parent
            property string segId: modelData
            property var e: sc.geom[segId]          // [ax,ay,bx,by]
            property bool on: sc.litSet.indexOf(segId) >= 0
            property real half: on ? sc.litHalf : sc.ghostHalf
            // endpoints in px
            property real ax: e[0]*sc.u
            property real ay: e[1]*sc.u
            property real bx: e[2]*sc.u
            property real by: e[3]*sc.u
            property real dx: bx-ax
            property real dy: by-ay
            property real len: Math.max(0.0001, Math.sqrt(dx*dx+dy*dy))
            // unit direction + perpendicular
            property real ux: dx/len
            property real uy: dy/len
            property real px: -uy
            property real py: ux
            // shortened endpoints (gap) then perpendicular-offset corners
            property real sax: ax+ux*endGapEff
            property real say: ay+uy*endGapEff
            property real sbx: bx-ux*endGapEff
            property real sby: by-uy*endGapEff
            property real endGapEff: Math.min(sc.endGap, len*0.4)

            // bloom underlay (lit only): a wider, fainter copy behind the core
            Shape {
                anchors.fill: parent; antialiasing: true
                visible: parent.on; opacity: sc.bloomStrength * sc.glow
                ShapePath {
                    fillColor: sc.litColor; strokeWidth: -1
                    startX: parent.sax + parent.px*(parent.half*2.1); startY: parent.say + parent.py*(parent.half*2.1)
                    PathLine { x: parent.parent.sbx + parent.parent.px*(parent.parent.half*2.1); y: parent.parent.sby + parent.parent.py*(parent.parent.half*2.1) }
                    PathLine { x: parent.parent.sbx - parent.parent.px*(parent.parent.half*2.1); y: parent.parent.sby - parent.parent.py*(parent.parent.half*2.1) }
                    PathLine { x: parent.parent.sax - parent.parent.px*(parent.parent.half*2.1); y: parent.parent.say - parent.parent.py*(parent.parent.half*2.1) }
                    PathLine { x: parent.parent.sax + parent.parent.px*(parent.parent.half*2.1); y: parent.parent.say + parent.parent.py*(parent.parent.half*2.1) }
                }
            }
            // crisp core (lit or ghost), thickened perpendicular
            Shape {
                anchors.fill: parent; antialiasing: true
                opacity: parent.on ? sc.glow : 0.45
                ShapePath {
                    fillColor: parent.on ? sc.litColor : sc.ghostColor
                    strokeWidth: -1
                    startX: parent.sax + parent.px*parent.half; startY: parent.say + parent.py*parent.half
                    PathLine { x: parent.parent.sbx + parent.parent.px*parent.parent.half; y: parent.parent.sby + parent.parent.py*parent.parent.half }
                    PathLine { x: parent.parent.sbx - parent.parent.px*parent.parent.half; y: parent.parent.sby - parent.parent.py*parent.parent.half }
                    PathLine { x: parent.parent.sax - parent.parent.px*parent.parent.half; y: parent.parent.say - parent.parent.py*parent.parent.half }
                    PathLine { x: parent.parent.sax + parent.parent.px*parent.parent.half; y: parent.parent.say + parent.parent.py*parent.parent.half }
                }
            }
        }
    }
}
'''


if __name__ == "__main__":
    print("geometry strokes:", len(json.loads(geometry_js())))
    g7 = json.loads(glyphs_js("7"))
    print("digits at fmt 7:", {d: g7[d] for d in "0123456789" if d in g7})
    print("component chars:", len(segment_char_component()), "bytes")
