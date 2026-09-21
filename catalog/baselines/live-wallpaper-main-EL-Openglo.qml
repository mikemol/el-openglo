import QtQuick
import QtQuick.Effects
import org.kde.plasma.plasmoid

// WallpaperItem is REQUIRED as the root (plain Item renders zero-size off-screen).
WallpaperItem {
    id: root
    property color litColor: "#99ffeb"
    property color ghostColor: "#8debd9"
    property color voidColor: "#081411"
    // ghost pass opacity — SOLVED by the palette (ghost_alpha on every token), not
    // the 0.45 this held as a literal no colour check could see.
    property real ghostAlpha: 0.308
    property bool breathe: (wallpaper.configuration.breathe === undefined) ? false
                           : wallpaper.configuration.breathe
    property bool blinkColon: (wallpaper.configuration.blinkColon === undefined) ? true
                              : wallpaper.configuration.blinkColon
    // ⊕STROKE-WEIGHT: lit stroke fuller than ghost (luminance x area); weight=1
    // -> 0.40U vs 0.26U as session 41 built it, weight=0 -> equal 0.32U.
    property real weight: (wallpaper.configuration.weight === undefined) ? 1.0
                          : wallpaper.configuration.weight
    property real strokeLit: 0.32 * (1 + 0.25 * weight)
    property real strokeGhost: 0.32 * (1 - 0.19 * weight)
    // ⊕BLOOM: the halo is a BLUR of a lit-only canvas under the crisp one — not
    // the two wider opaque rectangles this drew before (the stepped halo the
    // operator photographed, 2026-09-21). Ghost is never bloomed. 0 = off.
    property real bloom: (wallpaper.configuration.bloom === undefined) ? 1.5
                         : wallpaper.configuration.bloom

    Rectangle { anchors.fill: parent; color: root.voidColor }

    // ⚑ GEOMETRY IS A TOKEN SET EXACTLY LIKE COLOUR, and these two tables are the
    // substrate's projection rather than this surface's opinion. They were hand-
    // written here — a seven-seg map and a stroke table, inside an f-string, where
    // no gate could see them: check_geometry_source scans module-level assignments
    // and a table living in a QML string literal is invisible to it.
    property var seg: ({"0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg", "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg"})
    property var stroke: ({"a": ["h", 0, 2, 0], "b": ["v", 2, 0, 2], "c": ["v", 2, 2, 4], "d": ["h", 0, 2, 4], "e": ["v", 0, 2, 4], "f": ["v", 0, 0, 2], "g": ["h", 0, 2, 2]})

    property string timeStr: "00:00"
    property bool colonOn: true
    function tick() {
        var d = new Date();
        var h = d.getHours(); var m = d.getMinutes();
        root.timeStr = (h<10?"0":"")+h + ":" + (m<10?"0":"")+m;
        // the colon blinks at 1 Hz like the clock's; steady when blink is off
        root.colonOn = root.blinkColon ? !root.colonOn : true;
        haloCanvas.requestPaint();
        clockCanvas.requestPaint();
    }
    Timer { interval: 1000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.tick() }

    // gentle backlight breathe (lock mount); off on desktop (config)
    property real glow: 1.0
    SequentialAnimation on glow {
        running: root.breathe; loops: Animation.Infinite
        NumberAnimation { from: 0.85; to: 1.0; duration: 2200; easing.type: Easing.InOutSine }
        NumberAnimation { from: 1.0; to: 0.85; duration: 2200; easing.type: Easing.InOutSine }
    }
    onGlowChanged: { haloCanvas.requestPaint(); clockCanvas.requestPaint() }

    // One paint routine, two canvases. pass "lit" draws only energised strokes
    // and the lit colon (what the halo blurs); pass "all" draws ghost then lit.
    function paintFace(ctx, width, height, pass) {
        ctx.reset();
        var s = root.timeStr;               // "HH:MM"
        var U = height / 5.0;                // unit; digit is 2U x 4U
        var T = U * root.strokeLit;
        var Tg = U * root.strokeGhost;
        var stroke = root.stroke;
        function drawStroke(spec, U, T, ox, oy, style) {
            ctx.fillStyle = style; var gg = T*0.6;
            ctx.beginPath();
            if (spec[0]==="h") { var a=spec[1]*U,b=spec[2]*U,y=spec[3]*U;
                ctx.moveTo(ox+a+gg,oy+y-T/2);ctx.lineTo(ox+b-gg,oy+y-T/2);
                ctx.lineTo(ox+b-gg,oy+y+T/2);ctx.lineTo(ox+a+gg,oy+y+T/2); }
            else { var x=spec[1]*U,y0=spec[2]*U,y1=spec[3]*U;
                ctx.moveTo(ox+x-T/2,oy+y0+gg);ctx.lineTo(ox+x+T/2,oy+y0+gg);
                ctx.lineTo(ox+x+T/2,oy+y1-gg);ctx.lineTo(ox+x-T/2,oy+y1-gg); }
            ctx.closePath(); ctx.fill();
        }
        // ⊕WALLPAPER-CONTRAST: a GLANCED-AT ambient surface — the ghost recedes
        // to texture at the solved alpha; the lit time is what is parsed.
        function drawDigit(ch, ox, oy) {
            var on = root.seg[ch] || "";
            if (pass === "all") {
                ctx.globalAlpha = root.ghostAlpha * root.glow;
                for (var k in stroke) {
                    if (on.indexOf(k) < 0) drawStroke(stroke[k], U, Tg, ox, oy, root.ghostColor);
                }
            }
            ctx.globalAlpha = root.glow;
            for (var k4 in stroke) {
                if (on.indexOf(k4) >= 0) drawStroke(stroke[k4], U, T, ox, oy, root.litColor);
            }
        }
        var digitW = U*2 + U*0.6;
        var colonW = U*0.8;
        var chars = [s.charAt(0), s.charAt(1), ":", s.charAt(3), s.charAt(4)];
        var totalW = digitW*4 + colonW;
        var x = (width - totalW)/2;
        var y = (height - U*4)/2;
        for (var i=0;i<chars.length;i++) {
            if (chars[i]===":") {
                var r=U*0.18;
                if (root.colonOn) {
                    ctx.fillStyle = root.litColor; ctx.globalAlpha = root.glow;
                } else if (pass === "all") {
                    ctx.fillStyle = root.ghostColor; ctx.globalAlpha = root.ghostAlpha * root.glow;
                } else {
                    x += colonW; continue;      // an off colon is ghost: never bloomed
                }
                ctx.beginPath(); ctx.arc(x+colonW/2, y+U*1.3, r,0,2*Math.PI); ctx.fill();
                ctx.beginPath(); ctx.arc(x+colonW/2, y+U*2.7, r,0,2*Math.PI); ctx.fill();
                x += colonW;
            } else { drawDigit(chars[i], x, y); x += digitW; }
        }
        ctx.globalAlpha = 1.0;
    }

    // the halo: lit-only, blurred, under the crisp face
    Canvas {
        id: haloCanvas
        anchors.centerIn: parent
        width: parent.width * 0.6
        height: width * 0.32
        renderTarget: Canvas.FramebufferObject
        visible: root.bloom > 0
        layer.enabled: root.bloom > 0
        layer.effect: MultiEffect {
            blurEnabled: true
            blur: 1.0
            blurMax: 64
            blurMultiplier: root.bloom
            brightness: 0.15
        }
        onPaint: root.paintFace(getContext("2d"), width, height, "lit")
    }

    Canvas {
        id: clockCanvas
        anchors.centerIn: parent
        width: parent.width * 0.6
        height: width * 0.32
        renderTarget: Canvas.FramebufferObject
        onPaint: root.paintFace(getContext("2d"), width, height, "all")
    }
}
