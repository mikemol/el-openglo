// MatrixField — the FIXED dot field of a matrix display: every unlit LED, bezel to
// bezel, at the display's pitch. Generated from display_types (⊕DOT); do not
// hand-edit.
//
// ⚑ THE FIELD DOES NOT MOVE.  The operator's live report (2026-09-22): "the pip
// ghosts are scrolling with the glyphs, when the glyphs should be scrolling over
// the pips" and "the pips don't span the widget". MatrixChar drew its own ghost
// dots per character, so the ghost travelled with the text and ended where it
// did. On a real board the unlit LEDs are the hardware; the text is what lights
// them. So the ghost is drawn ONCE here, across the whole width, on a Canvas
// (one paint, not cols x rows Items), and the scrolling characters draw LIT
// dots only, snapped to this field's pitch so a lit dot lands on a field cell.
import QtQuick

Canvas {
    id: field
    property int rows: 8
    property real u: 4               // dot pitch in px — the SAME u the characters use
    property real dotFill: 0.82      // dot diameter as a fraction of the pitch (MatrixChar's)
    property color ghostColor: "gray"
    property real ghostOpacity: 0.28 // the palette's solved ghost alpha (passed in)
    readonly property int cols: Math.max(0, Math.floor(width / u))

    onWidthChanged: requestPaint()
    onHeightChanged: requestPaint()
    onUChanged: requestPaint()
    onDotFillChanged: requestPaint()
    onGhostColorChanged: requestPaint()
    onGhostOpacityChanged: requestPaint()
    onRowsChanged: requestPaint()

    onPaint: {
        var ctx = getContext("2d");
        ctx.clearRect(0, 0, width, height);
        ctx.fillStyle = ghostColor;
        ctx.globalAlpha = ghostOpacity;
        var r = u * dotFill / 2;
        // the field is vertically centred in whatever height the panel gives it
        var y0 = (height - rows * u) / 2;
        for (var c = 0; c < cols; c++) {
            for (var row = 0; row < rows; row++) {
                ctx.beginPath();
                ctx.arc(c * u + u / 2, y0 + row * u + u / 2, r, 0, 2 * Math.PI);
                ctx.fill();
            }
        }
    }
}
