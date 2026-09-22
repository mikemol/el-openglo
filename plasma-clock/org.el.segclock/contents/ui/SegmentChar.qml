// SegmentChar — ONE seven-segment character, the display every segment surface
// mounts. Generated from segment_topology (⊕SEGMENT-SUBSTRATE); do not hand-edit
// the geometry.
//
// ⚑ THIS IS AN EXTRACTION, NOT A DESIGN (W33, s133; the operator: "lift the
// clock's implementation so it's not just one theme, it's one abstraction").
// Its body IS the clock's `component Digit` / `component Segment` — the idiom
// that works: rounded caps (a Rectangle whose radius is half its thickness),
// antialiasing, the lit layer blurred into a halo and the ghost never bloomed.
// The previous body here drew square-capped Shapes and NOTHING INSTANTIATED IT
// (check_qml_lint --uses SegmentChar: 0 of 10), so there was no behaviour to
// keep; the wallpaper's own Canvas polygons were the third copy, and the
// operator's "rectangles of construction paper" was that copy being seen.
//
// THE AXES, so a mount parameterises rather than re-implements:
//   geometry  — segGeom / digSegs, the substrate's tables (shared already)
//   emission  — litColor / ghostColor / ghostAlpha / weight / ghostWeight / bloom
//   idiom     — rounded, antialiased, lit-only halo: NOT a parameter, the point
//   mount     — segLen and where the cell sits: the surface's, passed in
//   content   — `ch`, and whether a colon follows it
import QtQuick
import QtQuick.Effects

Item {
    id: sc
    // --- geometry: the substrate's tables, passed in by the emitter ---------
    property var segGeom: ({})        // {seg: [kind, ux, uy]}
    property var digSegs: ({})        // {char: "lit segment ids"}
    property string ch: "8"
    property bool insertColon: false

    // --- mount: the cell's size, the surface's choice ----------------------
    property int segLen: 20           // the digit is 2 segLen tall, segLen wide
    property real colonAdvance: 0     // extra advance when a colon follows
    // the gap the MOUNT puts between cells, in px: the colon is centred in the
    // whole space between its two neighbours, so the display cannot assume it
    property real cellGap: segLen * 0.5
    property real dotSize: Math.max(2, segLen * 0.12)

    // --- emission ----------------------------------------------------------
    property color litColor: "white"
    property color ghostColor: "gray"
    // ⚑ SOLVED, NOT AUTHORED: the default is make_schemes.GHOST_ALPHA filled at
    // emit time (it was a literal 0.45 no colour check could see). A mount may
    // bind its own — the live wallpaper is GLANCED-AT and passes the glanced
    // alpha — but the default is the palette's.
    property real ghostAlpha: 0.566
    property bool showGhost: true
    property bool colonOn: true
    // ⊕STROKE-WEIGHT: perceived brightness = luminance x AREA, so the lit stroke
    // is drawn FULLER than the ghost outline (a real segment is physically fuller
    // than its etched ghost). weight=1 -> lit 1.25x; weight=0 -> equal strokes.
    property int segThick: Math.max(2, Math.floor(segLen * 0.084))
    property real weight: 1.0
    property real ghostWeight: 0.81
    readonly property real strokeLit: segThick * (1 + 0.25 * weight)
    readonly property real strokeGhost: segThick * ghostWeight
    // ⊕BLOOM: the halo is a BLUR of the lit layer only — never the ghost, never a
    // wider opaque copy. 0 disables the layer (crisp fallback).
    property real bloom: 1.5
    property real glow: 1.0           // a mount may breathe the whole cell

    readonly property real colonSlot: segLen * colonAdvance
    readonly property real colonX: segLen + (colonSlot + cellGap) / 2 - dotSize / 2
    implicitWidth: segLen + (insertColon ? colonSlot : 0)
    implicitHeight: segLen * 2
    width: implicitWidth
    height: implicitHeight

    function isOn(s) {
        return sc.digSegs[ch] !== undefined && sc.digSegs[ch].indexOf(s) !== -1
    }

    // one glyph, three passes: ghost (un-energised, no halo), the lit layer
    // blurred into a halo, then the crisp lit core on top
    Repeater {
        model: ["A", "B", "C", "D", "E", "F", "G"]
        Segment {
            seg: modelData
            visible: sc.showGhost && !sc.isOn(modelData)
            color: sc.ghostColor
            opacity: sc.ghostAlpha * sc.glow
            thick: sc.strokeGhost
        }
    }
    Item {
        id: halo
        anchors.fill: parent
        visible: sc.bloom > 0
        layer.enabled: sc.bloom > 0
        // ⚑ THE HALO IS SIZED BY THE STROKE, NOT IN PIXELS. A fixed blurMax on a
        // 3 px panel stroke smeared the whole digit into one haze (⊕VER 2026-09-21);
        // the radius is a few stroke widths, scaled by the slider.
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: 1.0
            blurMax: Math.max(2, Math.round(sc.strokeLit * 2 * sc.bloom))
            blurMultiplier: 1.0
        }
        opacity: 0.75 * sc.glow
        Repeater {
            model: ["A", "B", "C", "D", "E", "F", "G"]
            Segment {
                seg: modelData
                visible: sc.isOn(modelData)
                color: sc.litColor
                thick: sc.strokeLit
            }
        }
        ColonDot { visible: sc.insertColon && sc.colonOn; y: sc.segLen * 0.62 }
        ColonDot { visible: sc.insertColon && sc.colonOn; y: sc.segLen * 1.38 - sc.dotSize }
    }
    Repeater {
        model: ["A", "B", "C", "D", "E", "F", "G"]
        Segment {
            seg: modelData
            visible: sc.isOn(modelData)
            color: sc.litColor
            opacity: sc.glow
            thick: sc.strokeLit
        }
    }
    // the colon after this cell: lit when on, ghost (never bloomed) when off
    ColonDot {
        visible: sc.insertColon
        color: sc.colonOn ? sc.litColor : sc.ghostColor
        opacity: (sc.colonOn ? 1.0 : sc.ghostAlpha) * sc.glow
        y: sc.segLen * 0.62
    }
    ColonDot {
        visible: sc.insertColon
        color: sc.colonOn ? sc.litColor : sc.ghostColor
        opacity: (sc.colonOn ? 1.0 : sc.ghostAlpha) * sc.glow
        y: sc.segLen * 1.38 - sc.dotSize
    }

    component ColonDot: Rectangle {
        width: sc.dotSize; height: sc.dotSize; radius: sc.dotSize / 2
        color: sc.litColor
        antialiasing: true
        x: sc.colonX
    }

    // ⚑ THE IDIOM: one segment as a scene-graph rectangle with ROUNDED CAPS
    // (radius = half the thickness) and antialiasing — what makes a segment read
    // as a lit bar rather than a cut rectangle (W33, measured s132). The caller
    // says colour, opacity and weight; the geometry is the substrate's alone.
    component Segment: Rectangle {
        property string seg: "A"
        property real thick: sc.segThick
        property var g: sc.segGeom[seg]          // [kind, ux, uy]
        property bool horiz: g[0] === "h"
        property real gap: sc.segThick * 0.62
        antialiasing: true
        radius: thick / 2
        width:  horiz ? sc.segLen - gap * 2 : thick
        height: horiz ? thick : sc.segLen - gap * 2
        // ⚑ CENTRED ON THE LATTICE LINE, NOT RESTING BESIDE IT (W57, s134; the
        // operator photographed the consequence: a digit whose top-left corner
        // notches while the bottom-left is clean). This read
        // `+ (segThick - thick)/2`, which put the stroke in a segThick-wide band
        // STARTING at the line — so the left vertical sat inside the cell at
        // [0, thick] while its mirror sat at [segLen, segLen+thick], a whole
        // stroke outside it, and the middle bar hung below the cell's midline.
        // check_symmetry located all six regions of it; centring on the line is
        // the one fix, and it makes the glyph its own mirror by construction.
        x: (g[1] * sc.segLen) + (horiz ? gap : -thick / 2)
        y: (g[2] * sc.segLen) + (horiz ? -thick / 2 : gap)
    }
}
