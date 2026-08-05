import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    // --- geometry: the SAME tables as the wallpaper (do not hand-edit) ---
    property var segGeom: ({ "A": ["h", 0, 0], "G": ["h", 0, 1], "D": ["h", 0, 2], "F": ["v", 0, 0], "B": ["v", 1, 0], "E": ["v", 0, 1], "C": ["v", 1, 1] })
    property var digSegs: ({ "0": "ABCDEF", "1": "BC", "2": "ABGED", "3": "ABGCD", "4": "FGBC", "5": "AFGCD", "6": "AFGEDC", "7": "ABC", "8": "ABCDEFG", "9": "ABCFGD" })

    property color litColor: "#4ba2fa"
    property color ghostColor: "#2a5989"
    property color hotColor: "#4ba2fa"
    property int segLen: Math.max(6, Math.floor(height * 0.42))
    property int segThick: Math.max(2, Math.floor(segLen * 0.18))

    property string timeStr: "0000"
    property bool colonOn: true

    Timer {
        interval: 500; running: true; repeat: true
        onTriggered: {
            var d = new Date();
            var h = d.getHours();
            if (!plasmoid.configuration.use24h) { h = h % 12; if (h === 0) h = 12; }
            var mm = d.getMinutes();
            var ss = d.getSeconds();
            var s = (h < 10 ? "0" : "") + h + (mm < 10 ? "0" : "") + mm;
            if (plasmoid.configuration.showSeconds) s += (ss < 10 ? "0" : "") + ss;
            root.timeStr = s;
            if (plasmoid.configuration.blinkColon) root.colonOn = !root.colonOn;
            else root.colonOn = true;
        }
    }

    preferredRepresentation: fullRepresentation
    fullRepresentation: Item {
        Layout.preferredWidth: segRow.implicitWidth + segLen
        Layout.minimumWidth: segRow.implicitWidth + segLen
        Row {
            id: segRow
            anchors.centerIn: parent
            spacing: Math.floor(segLen * 0.25)
            Repeater {
                model: root.timeStr.length
                Digit {
                    ch: root.timeStr.charAt(index)
                    insertColon: (index === 2)
                }
            }
        }
    }

    component Digit: Item {
        property string ch: "8"
        property bool insertColon: false
        width: segLen + (insertColon ? segLen * 0.7 : 0)
        height: segLen * 2

        // one seven-segment glyph; ghost layer under lit layer
        Repeater {
            model: ["A","B","C","D","E","F","G"]
            Segment {
                seg: modelData
                on: root.digSegs[parent.ch] !== undefined
                    && root.digSegs[parent.ch].indexOf(modelData) !== -1
            }
        }
        // colon dots after this digit
        Rectangle {
            visible: parent.insertColon
            width: segThick; height: segThick; radius: segThick/2
            color: root.colonOn ? root.litColor : root.ghostColor
            x: segLen + segLen*0.25; y: segLen*0.62
        }
        Rectangle {
            visible: parent.insertColon
            width: segThick; height: segThick; radius: segThick/2
            color: root.colonOn ? root.litColor : root.ghostColor
            x: segLen + segLen*0.25; y: segLen*1.38 - segThick
        }
    }

    component Segment: Item {
        property string seg: "A"
        property bool on: false
        property var g: root.segGeom[seg]         // [kind, ux, uy]
        property bool horiz: g[0] === "h"
        property real gap: segThick * 0.62
        anchors.fill: parent
        Rectangle {
            property bool showGhost: plasmoid.configuration.showGhost
            visible: parent.on || showGhost
            color: parent.on ? root.litColor : root.ghostColor
            antialiasing: true
            radius: segThick/2
            width:  horiz ? segLen - gap*2 : segThick
            height: horiz ? segThick : segLen - gap*2
            x: (g[1] * segLen) + (horiz ? gap : 0)
            y: (g[2] * segLen) + (horiz ? 0 : gap)
        }
    }
}
