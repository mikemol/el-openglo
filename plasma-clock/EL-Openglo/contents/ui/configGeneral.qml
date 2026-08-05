import QtQuick
import org.kde.kcm as KCM
import org.kde.kirigami as Kirigami
import QtQuick.Controls as QQC2
import QtQuick.Layouts

KCM.SimpleKCM {
    property alias cfg_showGhost: showGhost.checked
    property alias cfg_use24h: use24h.checked
    property alias cfg_showSeconds: showSeconds.checked
    property alias cfg_blinkColon: blinkColon.checked
    Kirigami.FormLayout {
        QQC2.CheckBox { id: showGhost; Kirigami.FormData.label: "Show ghost segments:" }
        QQC2.CheckBox { id: use24h; Kirigami.FormData.label: "24-hour clock:" }
        QQC2.CheckBox { id: showSeconds; Kirigami.FormData.label: "Show seconds:" }
        QQC2.CheckBox { id: blinkColon; Kirigami.FormData.label: "Blink colon:" }
        QQC2.Slider { id: bloomSlider; from: 0; to: 4; stepSize: 0.5; Kirigami.FormData.label: "Bloom / glow:" }
        QQC2.Slider { id: weightSlider; from: 0; to: 1; stepSize: 0.25; Kirigami.FormData.label: "Lit stroke weight:" }
    }
}
