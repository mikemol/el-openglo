import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
// PUBLIC notification model (libnotificationmanager) — the same feed the stock
// applet reads. NOT the deprecated org.kde.plasma.private.notifications.
import org.kde.notificationmanager as NotificationManager

PlasmoidItem {
    id: root
    property color litColor: "$lit"
    property color ghostColor: "$ghost"
    property color voidColor: "$ground"
    // the unlit dot field's opacity — the palette's solved ghost_alpha, passed to
    // every MatrixChar below in place of the component's authored 0.28. Whether a
    // DOT FIELD at this alpha reads as the same texture as strokes do is
    // ⊕GHOST-DENSITY's question, still open; the relation itself is one.
    property real ghostAlpha: $ghostAlpha

    // ⚑ THE SETTINGS (W34 c). Each reads plasmoid.configuration with the solved or
    // authored value as the fallback, so an unconfigured widget draws exactly
    // what the palette emitted; a slider is an override, never the source.
    property real cfgSpeed: (plasmoid.configuration.speed === undefined) ? 1.0
                            : plasmoid.configuration.speed
    property real cfgPitchScale: (plasmoid.configuration.pitchScale === undefined) ? 1.0
                                 : plasmoid.configuration.pitchScale
    property real cfgDotFill: (plasmoid.configuration.dotFill === undefined) ? 0.82
                              : plasmoid.configuration.dotFill
    property real cfgGhostAlpha: (plasmoid.configuration.ghostAlpha === undefined) ? root.ghostAlpha
                                 : plasmoid.configuration.ghostAlpha
    property bool cfgShowField: (plasmoid.configuration.showField === undefined) ? true
                                : plasmoid.configuration.showField
    property string cfgIdleText: (plasmoid.configuration.idleText === undefined) ? ""
                                 : plasmoid.configuration.idleText
    property int cfgMaxItems: (plasmoid.configuration.maxItems === undefined) ? 12
                              : plasmoid.configuration.maxItems

    preferredRepresentation: fullRepresentation

    // --- the notification feed (degrades to idle if unavailable) ------------
    property string tickerText: ""
    property bool haveModel: false

    NotificationManager.Notifications {
        id: notifModel
        showNotifications: true
        showJobs: true
        // newest first so the ticker leads with the latest
        sortMode: NotificationManager.Notifications.SortByDate
        groupMode: NotificationManager.Notifications.GroupDisabled
        Component.onCompleted: root.haveModel = true
        onCountChanged: root.rebuild()
    }

    function rebuild() {
        var parts = [];
        var n = Math.min(notifModel.count, root.cfgMaxItems);
        for (var i = 0; i < n; i++) {
            var idx = notifModel.index(i, 0);
            var app = notifModel.data(idx, NotificationManager.Notifications.ApplicationNameRole);
            var sum = notifModel.data(idx, NotificationManager.Notifications.SummaryRole);
            var body = notifModel.data(idx, NotificationManager.Notifications.BodyRole);
            var seg = "";
            if (app) seg += app + ": ";
            if (sum) seg += sum;
            if (body) seg += " — " + body;
            seg = seg.replace(/\s+/g, " ").trim();
            if (seg.length) parts.push(seg);
        }
        root.tickerText = parts.length ? parts.join("     •     ")
                                       : "";   // empty -> idle face
    }

    // ⚑ THE DISPLAY REGISTRY, EMITTED — NOT RETYPED.  display_types.as_qml_js()
    // is the single source; this surface holds no font and no geometry of its own.
    // It rendered `font.family: "monospace"` before, which is why
    // check_geometry_source flagged it: a phosphor ticker drawn in the system's
    // font is not this theme, it is text that happens to be the right colour.
    // 5x8: the body rows plus one descent row, so lowercase notification text
    // keeps its descenders. The table is the authored FONT5x8 plus the Latin-1
    // extension rasterised at build time (⊕MATRIX-FONT-INPUT).
    property var registry: $registry
    property var matrix: registry.displays["5x8"]
    property var matrixFont: registry["font" + matrix.font]

    fullRepresentation: Item {
        id: rep
        Layout.minimumWidth: 200
        Layout.preferredWidth: 420
        clip: true

        // dot pitch from the panel height: the cell is `rows` dots tall, and we
        // leave a little vertical air so the glyph does not touch the bezel.
        property real pitch: Math.max(1, (height * 0.72) / root.matrix.rows * root.cfgPitchScale)
        property real cellW: root.matrix.cols * pitch
        property real advance: cellW + pitch      // one blank column between chars

        Rectangle { anchors.fill: parent; color: root.voidColor; radius: height*0.1 }

        // ⚑ THE FIELD IS THE HARDWARE.  Every unlit LED, bezel to bezel, drawn
        // once and never moved; the idle face IS this field. (Operator, live
        // 2026-09-22: the pips scrolled with the glyphs and stopped at the
        // message's end — the ghost had been drawn per character.)
        MatrixField {
            id: field
            anchors.fill: parent
            visible: root.cfgShowField
            rows: root.matrix.rows
            u: rep.pitch
            dotFill: root.cfgDotFill
            ghostColor: root.ghostColor
            ghostOpacity: root.cfgGhostAlpha
        }

        // idle text (settings), lit on the field, centred and snapped to the pitch
        Row {
            visible: root.tickerText.length === 0 && root.cfgIdleText.length > 0
            spacing: rep.pitch
            y: (parent.height - rep.matrixHeight) / 2
            x: Math.round(((rep.width - width) / 2) / rep.pitch) * rep.pitch
            Repeater {
                model: root.cfgIdleText.split("")
                MatrixChar {
                    font: root.matrixFont
                    cols: root.matrix.cols; rows: root.matrix.rows
                    ch: modelData
                    u: rep.pitch
                    dotFill: root.cfgDotFill
                    litColor: root.litColor
                    ghostColor: root.ghostColor
                    ghostOpacity: root.cfgGhostAlpha
                    showGhost: false
                }
            }
        }

        // the marquee: the LIT dots scroll right-to-left OVER the field. The
        // characters draw no ghost of their own, and x is snapped to the field's
        // pitch so every lit dot lands on a field cell rather than between two.
        Row {
            id: marquee
            visible: root.tickerText.length > 0
            spacing: rep.pitch
            y: (parent.height - rep.matrixHeight) / 2
            property real rawX: rep.width
            x: Math.round(rawX / rep.pitch) * rep.pitch
            Repeater {
                model: root.tickerText.split("")
                MatrixChar {
                    font: root.matrixFont
                    cols: root.matrix.cols; rows: root.matrix.rows
                    ch: modelData
                    u: rep.pitch
                    dotFill: root.cfgDotFill
                    litColor: root.litColor
                    ghostColor: root.ghostColor
                    ghostOpacity: root.cfgGhostAlpha
                    showGhost: false
                }
            }
            NumberAnimation on rawX {
                running: marquee.visible
                from: rep.width; to: -marquee.width
                // speed scales with length so long feeds don't crawl; the
                // settings' speed factor divides the duration
                duration: Math.max(1500, (rep.width + marquee.width) * 12 / root.cfgSpeed)
                loops: Animation.Infinite
            }
        }

        property real matrixHeight: root.matrix.rows * pitch
    }
}
