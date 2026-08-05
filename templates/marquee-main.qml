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

    fullRepresentation: Item {
        id: rep
        Layout.minimumWidth: 200
        Layout.preferredWidth: 420
        clip: true

        Rectangle { anchors.fill: parent; color: root.voidColor; radius: height*0.1 }

        // idle phosphor face when nothing is scrolling
        Text {
            anchors.centerIn: parent
            visible: root.tickerText.length === 0
            text: "— — —"
            color: root.ghostColor
            font.family: "monospace"; font.bold: true
            font.pixelSize: parent.height * 0.5
            opacity: 0.5
        }

        // the marquee: scroll the ticker right-to-left across the panel
        Text {
            id: marquee
            visible: root.tickerText.length > 0
            text: root.tickerText
            color: root.litColor
            font.family: "monospace"; font.bold: true
            font.pixelSize: parent.height * 0.55
            y: (parent.height - height) / 2
            x: rep.width
            NumberAnimation on x {
                running: marquee.visible
                from: rep.width; to: -marquee.width
                // speed scales with length so long feeds don't crawl
                duration: Math.max(6000, (rep.width + marquee.width) * 12)
                loops: Animation.Infinite
            }
        }
    }
}
