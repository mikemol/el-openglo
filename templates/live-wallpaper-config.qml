import QtQuick
import org.kde.kirigami as Kirigami
import QtQuick.Controls as QQC2
import QtQuick.Layouts

// EL Openglo Live — settings (W59). The wallpaper declared a kcfg and NO page, so
// its display parameters existed and no user could reach them. A Plasma/Wallpaper
// package's page is contents/ui/config.qml; its keys are the same cfg_ contract.
Kirigami.FormLayout {
$displayDecls
    // MOUNT layer: this wallpaper's own
    property alias cfg_breathe: breathe.checked
    property alias cfg_blinkColon: blinkColon.checked
    property bool cfg_breatheDefault
    property bool cfg_blinkColonDefault
$displayControls
    QQC2.CheckBox { id: breathe; Kirigami.FormData.label: "Breathe (backlight):" }
    QQC2.CheckBox { id: blinkColon; Kirigami.FormData.label: "Blink colon:" }
}
