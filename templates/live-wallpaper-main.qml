import QtQuick
import QtQuick.Effects
import org.kde.plasma.plasmoid
// the ACTIVE colour scheme's roles (⊕ONE-THEME, W35); Kirigami is live inside a
// WallpaperItem — the stock org.kde.color wallpaper reads Kirigami.Units there
import org.kde.kirigami as Kirigami

// WallpaperItem is REQUIRED as the root (plain Item renders zero-size off-screen).
WallpaperItem {
    id: root
    // ⚑ BOUND, NOT BAKED (catalog/one-theme.md): lit = ForegroundNormal (fg),
    // ghost = ForegroundInactive (fg_in), void = [Colors:View] BackgroundNormal
    // (view), under the View set. ONE package: the applied EL-*.colors is the variant.
    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false
    property color litColor: Kirigami.Theme.textColor
    property color ghostColor: Kirigami.Theme.disabledTextColor
    property color voidColor: Kirigami.Theme.backgroundColor
    // ghost pass opacity — SOLVED by the palette for a GLANCED-AT surface
    // (ghost_alpha_glanced), global across the variants (0.309) and so baked; not
    // the 0.45 this held as a literal no colour check could see.
    property real ghostAlpha: $ghostAlpha
    property bool breathe: (wallpaper.configuration.breathe === undefined) ? false
                           : wallpaper.configuration.breathe
    property bool blinkColon: (wallpaper.configuration.blinkColon === undefined) ? true
                              : wallpaper.configuration.blinkColon
    // ⊕STROKE-WEIGHT: lit stroke fuller than ghost (luminance x area); weight=1
    // -> 0.40U vs 0.26U as session 41 built it, weight=0 -> equal 0.32U.
    property real weight: (wallpaper.configuration.weight === undefined) ? 1.0
                          : wallpaper.configuration.weight
    // stroke base in U (H = 4U): the substrate's module stroke (0.105 H) at weight=1
    property real strokeLit: $strokeBase * (1 + 0.25 * weight)
    property real ghostWeight: (wallpaper.configuration.ghostWeight === undefined) ? 0.81
                               : wallpaper.configuration.ghostWeight
    property real strokeGhost: $strokeBase * ghostWeight
    // digit PITCH in U (segment_topology.MODULE_METRICS): four datasheets agree on
    // 12.7 mm for a 14.22 mm digit, and the 88:88 module keeps it across the colon
    property real pitch: $pitch
    property real colonAdvance: $colonAdvance
    property real dotR: $dotR
    // ⊕BLOOM: the halo is a BLUR of a lit-only canvas under the crisp one — not
    // the two wider opaque rectangles this drew before (the stepped halo the
    // operator photographed, 2026-09-21). Ghost is never bloomed. 0 = off.
    property real bloom: (wallpaper.configuration.bloom === undefined) ? 1.5
                         : wallpaper.configuration.bloom

    Rectangle { anchors.fill: parent; color: root.voidColor }

    // ⚑ GEOMETRY IS A TOKEN SET EXACTLY LIKE COLOUR, and these tables are the
    // substrate's projection rather than this surface's opinion. They were hand-
    // written here — a seven-seg map and a stroke table, inside an f-string, where
    // no gate could see them: check_geometry_source scans module-level assignments
    // and a table living in a QML string literal is invisible to it. Since s133
    // they are the DISPLAY's tables, emitted by the same call the clock uses.
$tables

    property string timeStr: "00:00"
    property bool colonOn: true
    function tick() {
        var d = new Date();
        var h = d.getHours(); var m = d.getMinutes();
        root.timeStr = (h<10?"0":"")+h + ":" + (m<10?"0":"")+m;
        // the colon blinks at 1 Hz like the clock's; steady when blink is off
        root.colonOn = root.blinkColon ? !root.colonOn : true;
    }
    Timer { interval: 1000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.tick() }

    // gentle backlight breathe (lock mount); off on desktop (config)
    property real glow: 1.0
    SequentialAnimation on glow {
        running: root.breathe; loops: Animation.Infinite
        NumberAnimation { from: 0.85; to: 1.0; duration: 2200; easing.type: Easing.InOutSine }
        NumberAnimation { from: 1.0; to: 0.85; duration: 2200; easing.type: Easing.InOutSine }
    }
    // the glow reaches the cells as a bound property now; no canvas to repaint

    // ⚑ THE MOUNT (W33, s133; the operator: "one rendering engine for the clock
    // and the live wallpaper, then fixes to one are fixes to both"). This surface
    // owns WHERE and HOW BIG — the face is centred and sized to the frame, which
    // is the wallpaper's own problem (the clock sizes its digits off the panel's
    // HEIGHT and would overflow 16:9, measured s132) — and SegmentChar owns what a
    // digit looks like. The two Canvases and paintFace's polygon strokes are gone:
    // they were the third copy of the display, and the copy the operator saw as
    // "rectangles of construction paper".
    Row {
        id: face
        anchors.centerIn: parent
        // ⚑ THE MOUNT FITS THE FRAME, IN THE DISPLAY'S UNIT (measured s133: the
        // first attempt overflowed because this surface's metrics are in U with
        // H = 4U while SegmentChar's segLen is H/2 — a digit is 2 segLen tall).
        // The face takes 60% of the width: four cells plus three gaps plus the
        // colon slot, and never taller than 60% of the frame.
        // this surface's metrics are in U (H = 4U); the display's cell is segLen
        // (H = 2 segLen), so a length in U halves into the display's unit
        readonly property real gapRatio: root.pitch / 2 - 1.0
        readonly property real colonRatio: root.colonAdvance / 2
        property real cellLen: Math.max(6, Math.floor(Math.min(
            parent.width * 0.6 / (4 + 3 * gapRatio + colonRatio),
            parent.height * 0.6 / 2)))
        spacing: Math.round(cellLen * gapRatio)
        Repeater {
            model: 4
            SegmentChar {
                required property int index
                segGeom: root.segGeom
                digSegs: root.digSegs
                // "HHMM": the colon rides the second cell, as on the module
                ch: root.timeStr.charAt(index < 2 ? index : index + 1)
                insertColon: index === 1
                colonOn: root.colonOn
                segLen: face.cellLen
                // 1 U = 0.5 segLen; $dotR is a RADIUS in U, so its doubling into a
                // diameter and its halving into segLen cancel
                segThick: Math.max(2, Math.floor(face.cellLen * $strokeBase * 0.5))
                dotSize: Math.max(2, face.cellLen * $dotR)
                colonAdvance: face.colonRatio
                cellGap: face.spacing
                litColor: root.litColor
                ghostColor: root.ghostColor
                ghostAlpha: root.ghostAlpha
                weight: root.weight
                ghostWeight: root.ghostWeight
                bloom: root.bloom
                glow: root.glow
            }
        }
    }
}
