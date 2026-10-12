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
    property real u: 4                 // pitch in px, as the mount asks for it
    // ⚑ THE PITCH IS AN INTEGER NUMBER OF DEVICE PIXELS (operator, 2026-09-22,
    // twice: first "the pip grid should be regular", then — after the positions
    // alone were rounded — "those little boxes should all have the same shape and
    // the same width borders between them. Maybe it's a tiling alignment
    // problem?"). It is: rounding each pip's POSITION off a fractional pitch
    // leaves gaps of 4, 4, 5, 4, 5 …, so the boxes alternate width by
    // construction. A board's LEDs sit on one pitch; rounding the PITCH makes
    // every gap identical, and the field simply spans fewer or more pips.
    readonly property int uPx: Math.max(2, Math.round(u))
    property real dotFill: 0.82
    property color ghostColor: "gray"
    property real ghostOpacity: 0.28
    property color litColor: "white"
    property bool showGhost: true
    property int scale: 4              // backdrop pixels per pitch (supersampling)
    property real offset: 0            // scroll, in backdrop pixels; grows as the scene moves left
    // ⚑ THE VIEWPORT (W47, folded into W54): the backdrop may be TALLER than the
    // field — backdropRows of it — and offsetY (backdrop px) is which band the
    // pips look through. A 16-row Unifont glyph, an icon raster, a QR: taller than
    // 8 LEDs, scrolled vertically through them. The same integral, other axis.
    property int backdropRows: rows
    property real offsetY: 0
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
    // the halo around the lit pips (EmissionHalo): 0 = none
    property real bloom: 0
    property real haloOpacity: 0.75
    property real glow: 1.0
    // the ring (W51): the outermost pips, painted in ringColor at ringOpacity —
    // the hover-pause's pulse; 0 = no ring
    property color ringColor: "white"
    property real ringOpacity: 0
    readonly property int cols: Math.max(0, Math.floor(width / uPx))
    readonly property int y0: Math.round((height - rows * uPx) / 2)

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
        width: 1; height: field.backdropRows * field.scale
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
    // ⚑ INK PER BACKDROP COLUMN, summed over every row (W523): a column range with none is blank for
    // every pip row at once, so integrate() skips it whole. Float64, not the rows' Float32: at the
    // backdrop's total (up to ~190k) a Float32 swallows an edge's 1/255 and a column with ink would
    // read as blank; a double cannot, so a zero here is exactly zero ink.
    property var colPrefix: null
    property int backdropWidth: 0
    function sample() {
        var w = backdrop.width, h = backdrop.height;
        var ctx = backdrop.getContext("2d");
        var data = ctx.getImageData(0, 0, w, h).data;
        var colSum = new Float64Array(w);
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
                colSum[x] += a;
                row[x + 1] = acc;
                if (colourFromInk) {
                    ar += a * data[i]; ag += a * data[i + 1]; ab += a * data[i + 2];
                    rr[x + 1] = ar; gg[x + 1] = ag; bb[x + 1] = ab;
                }
            }
            p.push(row);
            if (colourFromInk) prgb.push([rr, gg, bb]);
        }
        var cp = new Float64Array(w + 1);
        for (var cx = 0; cx < w; cx++) cp[cx + 1] = cp[cx] + colSum[cx];
        colPrefix = cp;
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
        var w = backdropWidth, h = prefix.length, oy = Math.round(offsetY);
        for (var c = 0; c < cols; c++) {
            var x0 = Math.round(c * s + offset), x1 = x0 + s;
            var a = Math.max(0, Math.min(w, x0)), b = Math.max(0, Math.min(w, x1));
            // a column with no ink under its aperture is blank in every row: the same zeros the row
            // loop would find, without the rows * scale lookups (W523)
            if (b <= a || (colPrefix && colPrefix[b] - colPrefix[a] === 0)) {
                var dark = gamma === 1.0 ? 0 : Math.pow(0, gamma);
                for (var rb = 0; rb < rows; rb++) {
                    cov[rb * cols + c] = dark;
                    if (colourFromInk) col[rb * cols + c] = litColor;
                }
                continue;
            }
            for (var r = 0; r < rows; r++) {
                var sum = 0, sr = 0, sg = 0, sb = 0;
                var y0 = Math.max(0, r * s + oy), y1 = Math.min(h, (r + 1) * s + oy);
                if (b > a) for (var yy = y0; yy < y1; yy++) sum += prefix[yy][b] - prefix[yy][a];
                // ⚑ THE INK'S COLOUR ONLY WHERE THERE IS INK (W521): most pips are dark, and the
                // three colour sums cost three more nested lookups per backdrop row for each of
                // them, every frame (measured in the soak: colourFromInk off saved 37 % of the
                // CPU). The sums and their order are unchanged for a pip that has ink, so the
                // colour it gets is bit-identical.
                if (colourFromInk && sum > 0) for (var yc = y0; yc < y1; yc++) {
                    sr += prefixRGB[yc][0][b] - prefixRGB[yc][0][a];
                    sg += prefixRGB[yc][1][b] - prefixRGB[yc][1][a];
                    sb += prefixRGB[yc][2][b] - prefixRGB[yc][2][a];
                }
                cov[r * cols + c] = gamma === 1.0 ? sum / area : Math.pow(sum / area, gamma);
                if (colourFromInk) col[r * cols + c] = sum > 0 ? Qt.rgba(sr / sum / 255, sg / sum / 255, sb / sum / 255, 1) : litColor;
            }
        }
        coverage = cov;
        if (colourFromInk) inkColour = col;
        // ⚑ ONLY THE PIPS THAT CHANGED ARE WRITTEN (W522). The delegates used to BIND to the two
        // arrays above, so every new array made all of them (1064 on a marquee) re-evaluate their
        // coverage and colour bindings whether or not their own value moved: with the colour table
        // that was 37 % of the CPU and the whole of the GUI-thread cost (soak, 2026-10-12: 19 ms of
        // CPU per frame, over one core at 60 fps). Now each delegate holds `cov` and `ink` as plain
        // properties, set here only when they differ; a dark pip that stays dark is not touched.
        // `coverage` and `inkColour` stay assigned for the readers that take them whole.
        for (var i = 0; i < cov.length; i++) {
            var pip = pips.itemAt(i);
            if (!pip) continue;
            if (pip.cov !== cov[i]) pip.cov = cov[i];
            if (col) {
                var want = cov[i] > 0 ? col[i] : null;
                if (want !== null || pip.ink !== null) pip.ink = want;
            }
        }
    }
    onOffsetChanged: integrate()
    onOffsetYChanged: integrate()
    onColsChanged: integrate()
    onGammaChanged: integrate()

    Repeater {
        id: pips
        model: field.rows * field.cols
        Item {
            id: pip
            readonly property int col: index % field.cols
            readonly property int row: Math.floor(index / field.cols)
            // set by field.integrate() when it changes, never bound (W522); the ink's colour is
            // null for a pip with none, which draws in litColor
            property real cov: 0
            property var ink: null
            Component.onCompleted: {
                cov = field.coverage[index] || 0;
                ink = (field.colourFromInk && field.inkColour.length > index && cov > 0) ? field.inkColour[index] : null;
            }
            // ⚑ THE PIPS ARE HARDWARE: THE GRID IS PIXEL-REGULAR AND NEVER MOVES
            // (operator, 2026-09-22, seeing the scroll: "there's some serious grid
            // glitching ... are we aligning the pips to the font, rather than the
            // other way around? The pip grid should be regular"). The pitch is
            // fractional, so an unrounded position put every pip on a different
            // subpixel phase and the field shimmered as the backdrop moved —
            // exactly backwards for a board whose LEDs are fixed. The position is
            // rounded to the device grid; only the COVERAGE varies.
            x: col * field.uPx + Math.round((field.uPx - d) / 2)
            y: field.y0 + row * field.uPx + Math.round((field.uPx - d) / 2)
            readonly property int d: Math.max(1, Math.round(field.uPx * field.dotFill))
            width: d; height: d
            // the floor: the ghost pip (the LED that is there), if shown
            Rectangle {
                anchors.fill: parent; radius: width / 2; antialiasing: true
                color: field.ghostColor; opacity: field.showGhost ? field.ghostOpacity : 0
            }
            // the PWM: the lit token (or the ink's colour) at the coverage
            Rectangle {
                anchors.fill: parent; radius: width / 2; antialiasing: true
                color: pip.ink !== null && field.colourFromInk ? pip.ink : field.litColor
                opacity: pip.cov
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

    // the emission: the lit pips again, blurred under the shared halo component
    // (W501; the clock and wallpaper mount the same one over their lit segments).
    // bloom 0 = no halo and no pips built, so the unconfigured field is unchanged.
    EmissionHalo {
        anchors.fill: parent
        bloom: field.bloom
        haloOpacity: field.haloOpacity
        glow: field.glow
        radiusUnit: field.uPx * field.dotFill
        Repeater {
            model: field.bloom > 0 ? field.rows * field.cols : 0
            Rectangle {
                readonly property int d: Math.max(1, Math.round(field.uPx * field.dotFill))
                x: (index % field.cols) * field.uPx + Math.round((field.uPx - d) / 2)
                y: field.y0 + Math.floor(index / field.cols) * field.uPx + Math.round((field.uPx - d) / 2)
                width: d; height: d; radius: d / 2; antialiasing: true
                color: field.colourFromInk && field.inkColour.length > index ? field.inkColour[index] : field.litColor
                opacity: field.coverage[index] || 0
            }
        }
    }
}
