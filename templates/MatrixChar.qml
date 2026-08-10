// MatrixChar — one character as a dot-matrix cell, off the shared registry.
// Generated from display_types (⊕DOT / ⊕DOT-WIRE); do not hand-edit the font.
//
// The twin of SegmentChar.qml, and deliberately NOT a variant of it: ⊕DOT records
// that a segment is a subset of a topology while a pixel-cell is a raster, so the
// two share a CONTRACT (a cell, a set of lit primitives) rather than a substrate.
// Both take their table as a property; neither owns a shape.
import QtQuick

Item {
    id: mc
    property var font: ({})          // {char: [colByte x cols]} from the registry
    property int cols: 5
    property int rows: 7
    property string ch: " "
    property real u: 4               // dot pitch in px; cell is cols*u x rows*u
    property color litColor: "white"
    property color ghostColor: "gray"
    property real glow: 1.0
    property real dotFill: 0.82      // dot diameter as a fraction of the pitch
    property real ghostOpacity: 0.28 // the unlit field recedes to texture

    implicitWidth: cols * u
    implicitHeight: rows * u
    width: implicitWidth
    height: implicitHeight

    // the glyph's column bytes; bit b of column c = row b (b0 = top), HD44780
    // lineage. An unknown char falls back to its uppercase form, then to blank —
    // a missing glyph must render as an empty cell, never as a crash.
    property var colBytes: font[ch] || font[ch.toUpperCase()] || []

    Repeater {
        model: mc.cols * mc.rows
        Rectangle {
            property int c: index % mc.cols
            property int r: Math.floor(index / mc.cols)
            property int colByte: mc.colBytes.length > c ? mc.colBytes[c] : 0
            property bool on: (colByte & (1 << r)) !== 0

            width: mc.u * mc.dotFill
            height: width
            radius: width / 2
            x: c * mc.u + (mc.u - width) / 2
            y: r * mc.u + (mc.u - height) / 2
            color: on ? mc.litColor : mc.ghostColor
            opacity: on ? mc.glow : mc.ghostOpacity
        }
    }
}
