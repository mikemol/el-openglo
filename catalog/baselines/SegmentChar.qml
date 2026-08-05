// SegmentChar — one character as vector segments off the shared substrate.
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
