import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
// PUBLIC notification model (libnotificationmanager) — the same feed the stock
// applet reads. NOT the deprecated org.kde.plasma.private.notifications.
import org.kde.notificationmanager as NotificationManager

PlasmoidItem {
    id: root
    property color litColor: "#4bfad7"
    property color ghostColor: "#277e6c"
    property color voidColor: "#081411"

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
    property var registry: {"displays": {"5x7": {"cell": [5.0, 7.0], "cols": 5, "font": "5x7", "kind": "matrix", "rows": 7}}, "font5x7": {" ": [0, 0, 0, 0, 0], "*": [20, 8, 62, 8, 20], "+": [8, 8, 62, 8, 8], "-": [8, 8, 8, 8, 8], ".": [0, 96, 96, 0, 0], "/": [32, 16, 8, 4, 2], "0": [62, 81, 73, 69, 62], "1": [0, 66, 127, 64, 0], "2": [66, 97, 81, 73, 70], "3": [33, 65, 69, 75, 49], "4": [24, 20, 18, 127, 16], "5": [39, 69, 69, 69, 57], "6": [60, 74, 73, 73, 48], "7": [1, 113, 9, 5, 3], "8": [54, 73, 73, 73, 54], "9": [6, 73, 73, 41, 30], ":": [0, 54, 54, 0, 0], "?": [2, 1, 81, 9, 6], "A": [126, 9, 9, 9, 126], "B": [127, 73, 73, 73, 54], "C": [62, 65, 65, 65, 34], "D": [127, 65, 65, 34, 28], "E": [127, 73, 73, 73, 65], "F": [127, 9, 9, 9, 1], "G": [62, 65, 73, 73, 122], "H": [127, 8, 8, 8, 127], "I": [0, 65, 127, 65, 0], "J": [32, 64, 65, 63, 1], "K": [127, 8, 20, 34, 65], "L": [127, 64, 64, 64, 64], "M": [127, 2, 12, 2, 127], "N": [127, 4, 8, 16, 127], "O": [62, 65, 65, 65, 62], "P": [127, 9, 9, 9, 6], "Q": [62, 65, 81, 33, 94], "R": [127, 9, 25, 41, 70], "S": [70, 73, 73, 73, 49], "T": [1, 1, 127, 1, 1], "U": [63, 64, 64, 64, 63], "V": [31, 32, 64, 32, 31], "W": [127, 32, 24, 32, 127], "X": [99, 20, 8, 20, 99], "Y": [3, 4, 120, 4, 3], "Z": [97, 81, 73, 69, 67]}, "lattice": ["7", "9", "14", "16", "5x7"]}
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
