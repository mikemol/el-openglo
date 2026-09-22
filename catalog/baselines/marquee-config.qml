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
    // ⚑ PLASMA SETS TWO PROPERTIES PER KCFG ENTRY: cfg_<key> and cfg_<key>Default
    // (the schema default, for the Defaults button) — for EVERY entry, controls or
    // not. Undeclared, each is `Setting initial properties failed` on the live
    // shell's stderr (operator, 2026-09-22: thirteen lines on opening this page).
    // scripts/check_config_page.py measures; policy/config_page.rego holds it.
    // DISPLAY layer: display_params.MOUNTS['marquee']
    property alias cfg_showField: showFieldControl.checked
    property alias cfg_ghostAlpha: ghostAlphaControl.value
    property alias cfg_dotFill: dotFillControl.value
    property alias cfg_pitchScale: pitchScaleControl.value
    property bool cfg_showFieldDefault
    property real cfg_ghostAlphaDefault
    property real cfg_dotFillDefault
    property real cfg_pitchScaleDefault
    // MOUNT layer: this marquee's own
    property alias cfg_speed: speedSlider.value
    property alias cfg_idleText: idleText.text
    property alias cfg_maxItems: maxItems.value
    property alias cfg_openLinks: openLinks.checked
    property alias cfg_hoverPause: hoverPause.checked
    property real cfg_speedDefault
    property string cfg_idleTextDefault
    property int cfg_maxItemsDefault
    property bool cfg_openLinksDefault
    property bool cfg_hoverPauseDefault
    // INSTRUMENT layer — traceLog is the widget's own log, never a control: declared, not drawn
    property alias cfg_debugLog: debugLog.checked
    property string cfg_traceLog
    property bool cfg_debugLogDefault
    property string cfg_traceLogDefault
    Kirigami.FormLayout {
        QQC2.CheckBox { id: showFieldControl; Kirigami.FormData.label: "Show unlit substrate:" }
        QQC2.Slider { id: ghostAlphaControl; from: 0.0; to: 1.0; stepSize: 0.02; Kirigami.FormData.label: "Unlit opacity:" }
        QQC2.Slider { id: dotFillControl; from: 0.5; to: 1.0; stepSize: 0.02; Kirigami.FormData.label: "Primitive fill:" }
        QQC2.Slider { id: pitchScaleControl; from: 0.5; to: 1.5; stepSize: 0.05; Kirigami.FormData.label: "Cell pitch:" }
        QQC2.Slider { id: speedSlider; from: 0.25; to: 4.0; stepSize: 0.25; Kirigami.FormData.label: "Scroll speed:" }
        QQC2.TextField { id: idleText; Kirigami.FormData.label: "Idle text:"; placeholderText: "(empty: bare field)" }
        QQC2.SpinBox { id: maxItems; from: 1; to: 50; Kirigami.FormData.label: "Notifications shown:" }
        QQC2.CheckBox { id: openLinks; Kirigami.FormData.label: "Open links on click:" }
        QQC2.CheckBox { id: hoverPause; Kirigami.FormData.label: "Pause while hovered:" }
        QQC2.CheckBox { id: debugLog; Kirigami.FormData.label: "Log to plasmashell's stderr:" }
    }
}
