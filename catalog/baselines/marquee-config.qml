import QtQuick
// the Plasma 6 module (org.kde.kcm was KF5's and loaded a blank page — clock, 2026-09-21)
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami
import QtQuick.Controls as QQC2
import QtQuick.Layouts

// EL Notification Marquee — settings (⊕VER-MARQUEE, W34: "there's nothing
// configurable in the notification widget"). Every control is ALIASED to its
// cfg_ key; a slider without an alias moves nothing (the clock shipped two).
KCM.SimpleKCM {
    property alias cfg_speed: speedSlider.value
    property alias cfg_pitchScale: pitchSlider.value
    property alias cfg_dotFill: fillSlider.value
    property alias cfg_ghostAlpha: ghostSlider.value
    property alias cfg_showField: showField.checked
    property alias cfg_idleText: idleText.text
    property alias cfg_maxItems: maxItems.value
    property alias cfg_openLinks: openLinks.checked
    Kirigami.FormLayout {
        QQC2.Slider { id: speedSlider; from: 0.25; to: 4.0; stepSize: 0.25; Kirigami.FormData.label: "Scroll speed:" }
        QQC2.Slider { id: pitchSlider; from: 0.5; to: 1.5; stepSize: 0.05; Kirigami.FormData.label: "Dot pitch:" }
        QQC2.Slider { id: fillSlider; from: 0.5; to: 1.0; stepSize: 0.02; Kirigami.FormData.label: "Dot size:" }
        // the default is the palette's solved alpha (the kcfg hole); this is an override
        QQC2.Slider { id: ghostSlider; from: 0.0; to: 1.0; stepSize: 0.02; Kirigami.FormData.label: "Unlit field opacity:" }
        QQC2.CheckBox { id: showField; Kirigami.FormData.label: "Show unlit field:" }
        QQC2.TextField { id: idleText; Kirigami.FormData.label: "Idle text:"; placeholderText: "(empty: bare field)" }
        QQC2.SpinBox { id: maxItems; from: 1; to: 50; Kirigami.FormData.label: "Notifications shown:" }
        QQC2.CheckBox { id: openLinks; Kirigami.FormData.label: "Open links on click:" }
    }
}
