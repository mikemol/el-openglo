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
        var n = Math.min(notifModel.count, 12);
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
    property var registry: $registry
    property var matrix: registry.displays["5x7"]

    fullRepresentation: Item {
        id: rep
        Layout.minimumWidth: 200
        Layout.preferredWidth: 420
        clip: true

        // dot pitch from the panel height: the cell is `rows` dots tall, and we
        // leave a little vertical air so the glyph does not touch the bezel.
        property real pitch: Math.max(1, (height * 0.72) / root.matrix.rows)
        property real cellW: root.matrix.cols * pitch
        property real advance: cellW + pitch      // one blank column between chars

        Rectangle { anchors.fill: parent; color: root.voidColor; radius: height*0.1 }

        // idle phosphor face when nothing is scrolling — the same display, so the
        // idle state cannot drift from the active one.
        Row {
            anchors.centerIn: parent
            visible: root.tickerText.length === 0
            spacing: rep.pitch
            Repeater {
                model: ["-", " ", "-", " ", "-"]
                MatrixChar {
                    font: root.registry.font5x7
                    cols: root.matrix.cols; rows: root.matrix.rows
                    ch: modelData
                    u: rep.pitch
                    litColor: root.ghostColor
                    ghostColor: root.ghostColor
                    glow: 0.5
                }
            }
        }

        // the marquee: scroll the ticker right-to-left across the panel
        Row {
            id: marquee
            visible: root.tickerText.length > 0
            spacing: rep.pitch
            y: (parent.height - rep.matrixHeight) / 2
            x: rep.width
            Repeater {
                model: root.tickerText.split("")
                MatrixChar {
                    font: root.registry.font5x7
                    cols: root.matrix.cols; rows: root.matrix.rows
                    ch: modelData
                    u: rep.pitch
                    litColor: root.litColor
                    ghostColor: root.ghostColor
                }
            }
            NumberAnimation on x {
                running: marquee.visible
                from: rep.width; to: -marquee.width
                // speed scales with length so long feeds don't crawl
                duration: Math.max(6000, (rep.width + marquee.width) * 12)
                loops: Animation.Infinite
            }
        }

        property real matrixHeight: root.matrix.rows * pitch
    }
}
