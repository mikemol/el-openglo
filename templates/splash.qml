import QtQuick 2.15

Item {
    id: root
    property int stage: 0
    readonly property int total: 6
    anchors.fill: parent

    Rectangle { anchors.fill: parent; color: $ground }

    Row {
        anchors.centerIn: parent
        spacing: parent.width * 0.02
        Repeater {
            model: ["1","2",":","0","0"]
            Item {
                width: root.width*0.07; height: root.width*0.12
                property bool lit: index <= (root.stage / root.total) * 5
                Text {
                    anchors.fill: parent
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: modelData
                    font.pixelSize: parent.height
                    font.family: "monospace"; font.bold: true
                    color: $lit
                    opacity: 0.22
                }
                Text {
                    anchors.fill: parent
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    text: modelData
                    font.pixelSize: parent.height
                    font.family: "monospace"; font.bold: true
                    color: $lit
                    opacity: parent.lit ? 1.0 : 0.0
                    Behavior on opacity { NumberAnimation { duration: 220 } }
                }
            }
        }
    }
}
