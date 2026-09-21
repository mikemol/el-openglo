// theme-probe.qml — theme_probe.resolve's subject: an emission's BINDING LINES,
// verbatim, at a probe root, read after the theme has settled (the colours arrive
// one event-loop turn after load). Rendered by theme_probe under a variant's
// private kdeglobals with the real Kirigami.Theme.
import QtQuick
import org.kde.kirigami as Kirigami
Item {
    id: probe
$bindings
    Timer {
        interval: 300; running: true
        onTriggered: { console.log("RESULT " + JSON.stringify({$reads})); Qt.quit(); }
    }
}
