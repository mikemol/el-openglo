// ApertureField — the dot field as an APERTURE INTEGRAL (W54; operator, 2026-09-22:
// "pips with a brightness range... a supersampled mask over a higher-resolution
// backdrop scrolled at the display rate... pinholes"). Every pip is a pinhole over
// a backdrop drawn at `scale` backdrop pixels per pitch; its brightness is the
// backdrop's ink under its aperture at the current offset:
//
//     brightness = ghostOpacity + coverage * (1 - ghostOpacity)
//
// so an unlit pip is the ghost floor, a covered pip the lit ceiling, and a pip
// half under an edge is halfway — graded, not snapped. Scrolling moves `offset`
// (in backdrop pixels) and nothing is rebuilt: a real LED sign's sub-pixel smooth
// scroll IS this (PWM at fractional offsets).
//
// ⚑ NO SHADER. The software scene graph (the harness, the ebuild sandbox) has
// none (render_qml: MultiEffect drew nothing there, measured). The integral is a
// difference of PREFIX SUMS per backdrop row, so a frame costs cols x rows x
// scale lookups in JS — the same arithmetic a shader would do, on the CPU, and
// visible everywhere the gates run.
import QtQuick

Item {
    id: field
    property int rows: 8
    property real u: 4                 // pitch in px
    property real dotFill: 0.82
    property color ghostColor: "gray"
    property real ghostOpacity: 0.28
    property color litColor: "white"
    property bool showGhost: true
    property int scale: 4              // backdrop pixels per pitch (supersampling)
    property real offset: 0            // scroll, in backdrop pixels; grows as the scene moves left
    // ⚑ THE TRANSFER CURVE (operator, 2026-09-22, the sheet: "that bottom entry is
    // really faded — tonemapping? auto-stretching?"). A one-pixel stroke read at
    // 2:1 fills at most half an aperture, so the whole string sits at 0.25-0.5
    // coverage. brightness = coverage^gamma: 1 is the identity (the aperture gate
    // measures at 1); below 1 lifts partial coverage the way an LED driver's gamma
    // does. FIXED, not per-frame: an auto-stretch breathes as content scrolls.
    // W56's OCR score is the objective this is tuned against.
    property real gamma: 1.0
    // ⚑ COLOUR FROM THE INK (relations.md §5a through §5b): when on, a pip's lit
    // colour is the mean colour of the ink under its aperture — the marquee draws a
    // hue-table colour (already gated) into the backdrop for a coloured run; off,
    // ink is alpha only and every lit pip is litColor (the probes draw in black).
    property bool colourFromInk: false
    // the ring (W51): the outermost pips, painted in ringColor at ringOpacity —
    // the hover-pause's pulse; 0 = no ring
    property color ringColor: "white"
    property real ringOpacity: 0
    readonly property int cols: Math.max(0, Math.floor(width / u))
    readonly property real y0: (height - rows * u) / 2

    // the backdrop: whatever the owner drew into this canvas at backdrop resolution
    // (rows*scale tall; as wide as the scene). Ink = alpha. `sample()` after drawing.
    property alias backdrop: backdrop
    // the owner draws when this fires (a Canvas has no context until `available`)
    signal backdropReady()
    // ⚑ A RESIZED CANVAS IS DRAWABLE ONLY WITHIN THE WINDOW'S EXTENT UNTIL ONE PAINT
    // CYCLE COMMITS ITS NEW BUFFER (measured 2026-09-22: 111 cells drawn at x ≥ 464
    // on a 704 px backdrop in a 420 px window read back as zero ink; inside onPaint
    // after requestPaint, and any time after, every x lands). sizeBackdrop(w) does
    // the resize and emits backdropSized once the buffer is real; owners draw THEN.
    signal backdropSized()
    function sizeBackdrop(w) {
        w = Math.max(1, Math.round(w));
        if (backdrop.width === w) { backdropSized(); return; }
        backdrop.width = w;
        backdrop.sizing = true;
        backdrop.requestPaint();
    }
    Canvas {
        id: backdrop
        opacity: 0                     // present in the scene (so it initialises), unseen
        width: 1; height: field.rows * field.scale
        renderStrategy: Canvas.Immediate
        renderTarget: Canvas.Image
        property bool sizing: false
        onAvailableChanged: if (available) field.backdropReady()
        onPaint: if (sizing) { sizing = false; field.backdropSized(); }
    }
    // prefix[y][x] = ink summed over backdrop columns [0, x) of backdrop row y;
    // with colourFromInk, three more sums of ink-weighted r, g, b
    property var prefix: null
    property var prefixRGB: null
    property int backdropWidth: 0
    function sample() {
        var w = backdrop.width, h = backdrop.height;
        var ctx = backdrop.getContext("2d");
        var data = ctx.getImageData(0, 0, w, h).data;
        var p = [], prgb = colourFromInk ? [] : null;
        for (var y = 0; y < h; y++) {
            var row = new Float32Array(w + 1);
            var rr = colourFromInk ? new Float32Array(w + 1) : null;
            var gg = colourFromInk ? new Float32Array(w + 1) : null;
            var bb = colourFromInk ? new Float32Array(w + 1) : null;
            var acc = 0, ar = 0, ag = 0, ab = 0;
            for (var x = 0; x < w; x++) {
                var i = (y * w + x) * 4, a = data[i + 3] / 255;   // ink = alpha
                acc += a;
                row[x + 1] = acc;
                if (colourFromInk) {
                    ar += a * data[i]; ag += a * data[i + 1]; ab += a * data[i + 2];
                    rr[x + 1] = ar; gg[x + 1] = ag; bb[x + 1] = ab;
                }
            }
            p.push(row);
            if (colourFromInk) prgb.push([rr, gg, bb]);
        }
        backdropWidth = w;
        prefix = p;
        prefixRGB = prgb;
        integrate();
    }
    // coverage per pip, [row * cols + col], in [0, 1]; and, with colourFromInk,
    // the pip's colour (the ink's mean under its aperture)
    property var coverage: []
    property var inkColour: []
    function integrate() {
        if (!prefix) return;
        var s = scale, cov = new Array(rows * cols), area = s * s;
        var col = colourFromInk ? new Array(rows * cols) : null;
        var w = backdropWidth;
        for (var c = 0; c < cols; c++) {
            var x0 = Math.round(c * s + offset), x1 = x0 + s;
            var a = Math.max(0, Math.min(w, x0)), b = Math.max(0, Math.min(w, x1));
            for (var r = 0; r < rows; r++) {
                var sum = 0, sr = 0, sg = 0, sb = 0;
                if (b > a) for (var yy = r * s; yy < (r + 1) * s; yy++) {
                    sum += prefix[yy][b] - prefix[yy][a];
                    if (colourFromInk) {
                        sr += prefixRGB[yy][0][b] - prefixRGB[yy][0][a];
                        sg += prefixRGB[yy][1][b] - prefixRGB[yy][1][a];
                        sb += prefixRGB[yy][2][b] - prefixRGB[yy][2][a];
                    }
                }
                cov[r * cols + c] = gamma === 1.0 ? sum / area : Math.pow(sum / area, gamma);
                if (colourFromInk) col[r * cols + c] = sum > 0 ? Qt.rgba(sr / sum / 255, sg / sum / 255, sb / sum / 255, 1) : litColor;
            }
        }
        coverage = cov;
        if (colourFromInk) inkColour = col;
    }
    onOffsetChanged: integrate()
    onColsChanged: integrate()
    onGammaChanged: integrate()

    Repeater {
        model: field.rows * field.cols
        Item {
            readonly property int col: index % field.cols
            readonly property int row: Math.floor(index / field.cols)
            readonly property real cov: field.coverage[index] || 0
            x: col * field.u + (field.u - d) / 2
            y: field.y0 + row * field.u + (field.u - d) / 2
            readonly property real d: field.u * field.dotFill
            width: d; height: d
            // the floor: the ghost pip (the LED that is there), if shown
            Rectangle {
                anchors.fill: parent; radius: width / 2; antialiasing: true
                color: field.ghostColor; opacity: field.showGhost ? field.ghostOpacity : 0
            }
            // the PWM: the lit token (or the ink's colour) at the coverage
            Rectangle {
                anchors.fill: parent; radius: width / 2; antialiasing: true
                color: field.colourFromInk && field.inkColour.length > index ? field.inkColour[index] : field.litColor
                opacity: parent.cov
            }
            // the ring: the outermost pips, pulsed by the owner
            Rectangle {
                readonly property bool edge: parent.col === 0 || parent.col === field.cols - 1
                                             || parent.row === 0 || parent.row === field.rows - 1
                visible: edge && field.ringOpacity > 0
                anchors.fill: parent; radius: width / 2; antialiasing: true
                color: field.ringColor; opacity: field.ringOpacity
            }
        }
    }
}
