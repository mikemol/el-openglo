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
    readonly property int cols: Math.max(0, Math.floor(width / u))
    readonly property real y0: (height - rows * u) / 2

    // the backdrop: whatever the owner drew into this canvas at backdrop resolution
    // (rows*scale tall; as wide as the scene). Ink = alpha. `sample()` after drawing.
    property alias backdrop: backdrop
    // the owner draws when this fires (a Canvas has no context until `available`)
    signal backdropReady()
    Canvas {
        id: backdrop
        opacity: 0                     // present in the scene (so it initialises), unseen
        width: 1; height: field.rows * field.scale
        renderStrategy: Canvas.Immediate
        renderTarget: Canvas.Image
        onAvailableChanged: if (available) field.backdropReady()
    }
    // prefix[y][x] = ink summed over backdrop columns [0, x) of backdrop row y
    property var prefix: null
    property int backdropWidth: 0
    function sample() {
        var w = backdrop.width, h = backdrop.height;
        var ctx = backdrop.getContext("2d");
        var data = ctx.getImageData(0, 0, w, h).data;
        var p = [];
        for (var y = 0; y < h; y++) {
            var row = new Float32Array(w + 1);
            var acc = 0;
            for (var x = 0; x < w; x++) {
                acc += data[(y * w + x) * 4 + 3] / 255;   // ink = alpha
                row[x + 1] = acc;
            }
            p.push(row);
        }
        backdropWidth = w;
        prefix = p;
        integrate();
    }
    // coverage per pip, [row * cols + col], in [0, 1]
    property var coverage: []
    function integrate() {
        if (!prefix) return;
        var s = scale, cov = new Array(rows * cols), area = s * s;
        var w = backdropWidth;
        for (var c = 0; c < cols; c++) {
            var x0 = Math.round(c * s + offset), x1 = x0 + s;
            var a = Math.max(0, Math.min(w, x0)), b = Math.max(0, Math.min(w, x1));
            for (var r = 0; r < rows; r++) {
                var sum = 0;
                if (b > a) for (var yy = r * s; yy < (r + 1) * s; yy++) sum += prefix[yy][b] - prefix[yy][a];
                cov[r * cols + c] = sum / area;
            }
        }
        coverage = cov;
    }
    onOffsetChanged: integrate()
    onColsChanged: integrate()

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
            // the PWM: the lit token at the coverage
            Rectangle {
                anchors.fill: parent; radius: width / 2; antialiasing: true
                color: field.litColor; opacity: parent.cov
            }
        }
    }
}
