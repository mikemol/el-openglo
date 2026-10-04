import QtQuick
// ⚑ org.kde.kcm was the KF5 name; on Plasma 6 the module is org.kde.kcmutils and
// the old import made this page load NOTHING (blank, no error surfaced — the
// operator opened it 2026-09-21; nobody had since the recovery).
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami
import QtQuick.Controls as QQC2
import QtQuick.Layouts

KCM.SimpleKCM {
    // Plasma sets cfg_<key> AND cfg_<key>Default per kcfg entry (the marquee page
    // showed the refusals live, 2026-09-22) — scripts/check_config_page.py
    // measures; policy/config_page.rego holds it. Every control is ALIASED: a
    // slider without an alias moves nothing (this page once shipped two).
    // DISPLAY layer: display_params.MOUNTS['clock']
    property alias cfg_showGhost: showGhostControl.checked
    property alias cfg_ghostAlpha: ghostAlphaControl.value
    property alias cfg_weight: weightControl.value
    property alias cfg_ghostWeight: ghostWeightControl.value
    property alias cfg_digitGap: digitGapControl.value
    property alias cfg_bloom: bloomControl.value
    property alias cfg_haloOpacity: haloOpacityControl.value
    property alias cfg_litGradient: litGradientControl.value
    property alias cfg_boundaryDepth: boundaryDepthControl.value
    property alias cfg_glow: glowControl.value
    property bool cfg_showGhostDefault
    property real cfg_ghostAlphaDefault
    property real cfg_weightDefault
    property real cfg_ghostWeightDefault
    property real cfg_digitGapDefault
    property real cfg_bloomDefault
    property real cfg_haloOpacityDefault
    property real cfg_litGradientDefault
    property real cfg_boundaryDepthDefault
    property real cfg_glowDefault
    // MOUNT layer: this clock's own
    property alias cfg_use24h: use24h.checked
    property alias cfg_showSeconds: showSeconds.checked
    property alias cfg_blinkColon: blinkColon.checked
    property bool cfg_use24hDefault
    property bool cfg_showSecondsDefault
    property bool cfg_blinkColonDefault
    Kirigami.FormLayout {
        QQC2.CheckBox { id: showGhostControl; Kirigami.FormData.label: "Show unlit substrate:" }
        QQC2.Slider { id: ghostAlphaControl; from: 0.0; to: 1.0; stepSize: 0.02; Kirigami.FormData.label: "Unlit opacity:" }
        QQC2.Slider { id: weightControl; from: 0; to: 1; stepSize: 0.25; Kirigami.FormData.label: "Lit stroke weight:" }
        QQC2.Slider { id: ghostWeightControl; from: 0; to: 1.0; stepSize: 0.05; Kirigami.FormData.label: "Unlit stroke weight:" }
        QQC2.Slider { id: digitGapControl; from: 0.786; to: 2.0; stepSize: 0.05; Kirigami.FormData.label: "Cell pitch:" }
        QQC2.Slider { id: bloomControl; from: 0; to: 6; stepSize: 0.5; Kirigami.FormData.label: "Bloom / glow:" }
        QQC2.Slider { id: haloOpacityControl; from: 0; to: 1; stepSize: 0.05; Kirigami.FormData.label: "Halo opacity:" }
        QQC2.Slider { id: litGradientControl; from: 0; to: 1; stepSize: 0.05; Kirigami.FormData.label: "Lit gradient:" }
        QQC2.Slider { id: boundaryDepthControl; from: 0; to: 0.5; stepSize: 0.05; Kirigami.FormData.label: "Gradient reach:" }
        QQC2.Slider { id: glowControl; from: 0; to: 1; stepSize: 0.05; Kirigami.FormData.label: "Brightness:" }
        QQC2.CheckBox { id: use24h; Kirigami.FormData.label: "24-hour clock:" }
        QQC2.CheckBox { id: showSeconds; Kirigami.FormData.label: "Show seconds:" }
        QQC2.CheckBox { id: blinkColon; Kirigami.FormData.label: "Blink colon:" }
    }
}
