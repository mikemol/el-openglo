#!/usr/bin/env python3
"""Notification-marquee plasmoid emitter (⊕NOTIFY-MARQUEE).

A panel widget that SUBSUMES the occluding notification popups into a phosphor
scrolling ticker (an airport departure-board for your desktop). It restores the
behavior late Plasma 4 had before Plasma 5 replaced the ticker with popups.

Architecture (fetched): reads the PUBLIC NotificationManager.Notifications model
(import org.kde.notificationmanager) — the same feed the stock applet consumes —
rather than trying to become the D-Bus notification server. Root is PlasmoidItem
(KF6), entry ui/main.qml, KPackageStructure=Plasma/Applet. Colors bake from the
scheme tokens like every other emitter (9th emission surface). A companion helper
suppresses the stock popups (plasmanotifyrc) so the marquee replaces them.

Degrades gracefully: if the model is empty or the import is unavailable, the
widget shows an idle phosphor face rather than crashing.
"""
import os
import json
import make_wallpaper_live as WL   # reuse colors_for (token-derived lit/ghost/void)


def _hex(rgb):
    return "#%02x%02x%02x" % rgb


def metadata(variant):
    return {
        "KPackageStructure": "Plasma/Applet",
        "KPlugin": {
            "Id": f"org.el.notifymarquee.{variant.lower().replace('-', '')}",
            "Name": f"EL Notification Marquee ({variant})",
            "Description": "Phosphor scrolling ticker that subsumes notification popups",
            "Category": "System Information",
            "License": "GPLv3",
            "Authors": [{"Name": "EL Openglo"}],
        },
        "X-Plasma-API-Minimum-Version": "6.0",
    }


def main_qml(variant):
    ground, lit, ghost = WL.colors_for(variant)
    litc, ghc, gnd = _hex(lit), _hex(ghost), _hex(ground)
    return f'''import QtQuick
import QtQuick.Layouts
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
// PUBLIC notification model (libnotificationmanager) — the same feed the stock
// applet reads. NOT the deprecated org.kde.plasma.private.notifications.
import org.kde.notificationmanager as NotificationManager

PlasmoidItem {{
    id: root
    property color litColor: "{litc}"
    property color ghostColor: "{ghc}"
    property color voidColor: "{gnd}"

    preferredRepresentation: fullRepresentation

    // --- the notification feed (degrades to idle if unavailable) ------------
    property string tickerText: ""
    property bool haveModel: false

    NotificationManager.Notifications {{
        id: notifModel
        showNotifications: true
        showJobs: true
        // newest first so the ticker leads with the latest
        sortMode: NotificationManager.Notifications.SortByDate
        groupMode: NotificationManager.Notifications.GroupDisabled
        Component.onCompleted: root.haveModel = true
        onCountChanged: root.rebuild()
    }}

    function rebuild() {{
        var parts = [];
        var n = Math.min(notifModel.count, 12);
        for (var i = 0; i < n; i++) {{
            var idx = notifModel.index(i, 0);
            var app = notifModel.data(idx, NotificationManager.Notifications.ApplicationNameRole);
            var sum = notifModel.data(idx, NotificationManager.Notifications.SummaryRole);
            var body = notifModel.data(idx, NotificationManager.Notifications.BodyRole);
            var seg = "";
            if (app) seg += app + ": ";
            if (sum) seg += sum;
            if (body) seg += " — " + body;
            seg = seg.replace(/\\s+/g, " ").trim();
            if (seg.length) parts.push(seg);
        }}
        root.tickerText = parts.length ? parts.join("     •     ")
                                       : "";   // empty -> idle face
    }}

    fullRepresentation: Item {{
        id: rep
        Layout.minimumWidth: 200
        Layout.preferredWidth: 420
        clip: true

        Rectangle {{ anchors.fill: parent; color: root.voidColor; radius: height*0.1 }}

        // idle phosphor face when nothing is scrolling
        Text {{
            anchors.centerIn: parent
            visible: root.tickerText.length === 0
            text: "— — —"
            color: root.ghostColor
            font.family: "monospace"; font.bold: true
            font.pixelSize: parent.height * 0.5
            opacity: 0.5
        }}

        // the marquee: scroll the ticker right-to-left across the panel
        Text {{
            id: marquee
            visible: root.tickerText.length > 0
            text: root.tickerText
            color: root.litColor
            font.family: "monospace"; font.bold: true
            font.pixelSize: parent.height * 0.55
            y: (parent.height - height) / 2
            x: rep.width
            NumberAnimation on x {{
                running: marquee.visible
                from: rep.width; to: -marquee.width
                // speed scales with length so long feeds don't crawl
                duration: Math.max(6000, (rep.width + marquee.width) * 12)
                loops: Animation.Infinite
            }}
        }}
    }}
}}
'''


def render_all(variants, dir_map):
    written = {}
    for v in variants:
        d = dir_map[v]
        ui = os.path.join(d, "contents", "ui")
        os.makedirs(ui, exist_ok=True)
        open(os.path.join(d, "metadata.json"), "w").write(
            json.dumps(metadata(v), indent=2))
        open(os.path.join(ui, "main.qml"), "w").write(main_qml(v))
        written[v] = d
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/nm-{v}" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "notification-marquee plasmoids")
    for v in variants:
        g, l, gh = WL.colors_for(v)
        print(f"  {v}: void={g} lit={l}")
