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
    // ⚑ THE GHOST BELONGS TO THE FIELD, NOT THE GLYPH.  A character that scrolls
    // over a MatrixField sets this false and draws LIT dots only — its unlit
    // positions are the field's own dots underneath (operator, 2026-09-22: the
    // pips must not scroll with the glyphs). Standalone (a sample, a static
    // label) it keeps drawing its own field.
    property bool showGhost: true
    // ⚑ PER-CHARACTER STYLE (W39, relations.md §5a). A body's style run may LIFT
    // this character: litColorOverride is a colour from the variant's solved hue
    // table (transparent = none: draw litColor); bold is a FULLER lit dot —
    // ⊕STROKE-WEIGHT's rule, perceived brightness = luminance x area, the same
    // move as the clock's weight slider — via the caller's dotFill. Nothing is
    // computed here: the table was gated at build time; the field is untouched.
    property color litColorOverride: "transparent"
    readonly property color litDrawn: litColorOverride.a > 0 ? litColorOverride : litColor
    // ⚑ UNDERLINE IS THE DESCENT ROW LIT (W40): a link's (or a <u> run's)
    // characters light their bottom row across every column — the bar a
    // departure board draws under a flight number. Nothing else in the glyph
    // changes; a descender glyph's own bottom-row dots simply stay lit.
    property bool underline: false

    implicitWidth: cols * u
    implicitHeight: rows * u
    width: implicitWidth
    height: implicitHeight

    // the glyph's column bytes; bit b of column c = row b (b0 = top), HD44780
    // lineage. An unknown char falls back to its uppercase form, then to '?'
    // (⊕MATRIX-FONT-INPUT: a char outside the table must be SEEN as unrenderable,
    // not vanish into a blank cell), then to blank if the table has no '?' —
    // never a crash.
    property var colBytes: font[ch] || font[ch.toUpperCase()] || font["?"] || []

    Repeater {
        model: mc.cols * mc.rows
        Rectangle {
            property int c: index % mc.cols
            property int r: Math.floor(index / mc.cols)
            property int colByte: mc.colBytes.length > c ? mc.colBytes[c] : 0
            property bool on: ((colByte & (1 << r)) !== 0) || (mc.underline && r === mc.rows - 1)
            visible: on || mc.showGhost

            width: mc.u * mc.dotFill
            height: width
            radius: width / 2
            x: c * mc.u + (mc.u - width) / 2
            y: r * mc.u + (mc.u - height) / 2
            color: on ? mc.litDrawn : mc.ghostColor
            opacity: on ? mc.glow : mc.ghostOpacity
        }
    }
}
