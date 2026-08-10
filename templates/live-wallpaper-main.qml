import QtQuick
import org.kde.plasma.plasmoid

// WallpaperItem is REQUIRED as the root (plain Item renders zero-size off-screen).
WallpaperItem {
    id: root
    property color litColor: $lit
    property color ghostColor: $ghost
    property color voidColor: $ground
    property bool breathe: (wallpaper.configuration.breathe === undefined) ? false
                           : wallpaper.configuration.breathe

    Rectangle { anchors.fill: parent; color: root.voidColor }

    // ⚑ GEOMETRY IS A TOKEN SET EXACTLY LIKE COLOUR, and these two tables are the
    // substrate's projection rather than this surface's opinion. They were hand-
    // written here — a seven-seg map and a stroke table, inside an f-string, where
    // no gate could see them: check_geometry_source scans module-level assignments
    // and a table living in a QML string literal is invisible to it.
    property var seg: ($seg)

    property string timeStr: "00:00"
    function tick() {
        var d = new Date();
        var h = d.getHours(); var m = d.getMinutes();
        root.timeStr = (h<10?"0":"")+h + ":" + (m<10?"0":"")+m;
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
    onGlowChanged: clockCanvas.requestPaint()

    Canvas {
        id: clockCanvas
        anchors.centerIn: parent
        width: parent.width * 0.6
        height: width * 0.32
        renderTarget: Canvas.FramebufferObject
        onPaint: {
            var ctx = getContext("2d"); ctx.reset();
            var s = root.timeStr;               // "HH:MM"
            var U = height / 5.0;                // unit; digit is 2U x 4U
            var T = U * 0.40;                    // lit stroke (stroke-weight)
            var Tg = U * 0.26;                   // ghost stroke
            var g = 0;
            var stroke = $stroke;
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
            // ⊕WALLPAPER-CONTRAST: lit-vs-ghost separation scales with parsing
            // mode. This is a GLANCED-AT ambient surface, so lit must POP: (1) the
            // ghost is drawn SUBORDINATE (low alpha — it recedes to texture, since
            // here only the lit time is parsed), (2) lit gets a BLOOM glow (the
            // channel the clock has and this surface was missing). Canvas-native
            // glow = lit stroke drawn underneath at wider T and low alpha.
            function drawDigit(ch, ox, oy) {
                var on = root.seg[ch] || "";
                // pass 1: ghost, subordinate (recedes to texture)
                ctx.globalAlpha = 0.45;
                for (var k in stroke) {
                    if (on.indexOf(k) < 0) drawStroke(stroke[k], U, Tg, ox, oy, root.ghostColor);
                }
                ctx.globalAlpha = 1.0;
                // pass 2: lit bloom halo (wide, faint, lit-only) — makes lit POP
                ctx.globalAlpha = 0.18;
                for (var k2 in stroke) {
                    if (on.indexOf(k2) >= 0) drawStroke(stroke[k2], U, T*2.1, ox, oy, root.litColor);
                }
                ctx.globalAlpha = 0.30;
                for (var k3 in stroke) {
                    if (on.indexOf(k3) >= 0) drawStroke(stroke[k3], U, T*1.5, ox, oy, root.litColor);
                }
                // pass 3: crisp lit core
                ctx.globalAlpha = 1.0;
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
            ctx.globalAlpha = root.glow;
            for (var i=0;i<chars.length;i++) {
                if (chars[i]===":") {
                    var r=U*0.18;
                    // colon bloom halo (match the digit glow) then crisp core
                    ctx.fillStyle = root.litColor;
                    ctx.globalAlpha = 0.22;
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*1.3, r*2.0,0,2*Math.PI); ctx.fill();
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*2.7, r*2.0,0,2*Math.PI); ctx.fill();
                    ctx.globalAlpha = 1.0;
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*1.3, r,0,2*Math.PI); ctx.fill();
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*2.7, r,0,2*Math.PI); ctx.fill();
                    x += colonW;
                } else { drawDigit(chars[i], x, y); x += digitW; }
            }
            ctx.globalAlpha = 1.0;
        }
    }
}
