import QtQuick
import org.kde.kirigami as Kirigami
import QtQuick.Controls as QQC2
import QtQuick.Layouts

// EL Openglo Live — settings (W59). The wallpaper declared a kcfg and NO page, so
// its display parameters existed and no user could reach them. A Plasma/Wallpaper
// package's page is contents/ui/config.qml; its keys are the same cfg_ contract.
Kirigami.FormLayout {
    // DISPLAY layer: display_params.MOUNTS['wallpaper']
    property alias cfg_showGhost: showGhostControl.checked
    property alias cfg_ghostAlpha: ghostAlphaControl.value
    property alias cfg_weight: weightControl.value
    property alias cfg_ghostWeight: ghostWeightControl.value
    property alias cfg_bloom: bloomControl.value
    property alias cfg_haloOpacity: haloOpacityControl.value
    property alias cfg_litGradient: litGradientControl.value
    property alias cfg_boundaryDepth: boundaryDepthControl.value
    property alias cfg_glow: glowControl.value
    property bool cfg_showGhostDefault
    property real cfg_ghostAlphaDefault
    property real cfg_weightDefault
    property real cfg_ghostWeightDefault
    property real cfg_bloomDefault
    property real cfg_haloOpacityDefault
    property real cfg_litGradientDefault
    property real cfg_boundaryDepthDefault
    property real cfg_glowDefault
    // MOUNT layer: this wallpaper's own
    property alias cfg_breathe: breathe.checked
    property alias cfg_blinkColon: blinkColon.checked
    property bool cfg_breatheDefault
    property bool cfg_blinkColonDefault
    QQC2.CheckBox { id: showGhostControl; Kirigami.FormData.label: "Show unlit substrate:" }
    QQC2.Slider { id: ghostAlphaControl; from: 0.0; to: 1.0; stepSize: 0.02; Kirigami.FormData.label: "Unlit opacity:" }
    QQC2.Slider { id: weightControl; from: 0; to: 1; stepSize: 0.25; Kirigami.FormData.label: "Lit stroke weight:" }
    QQC2.Slider { id: ghostWeightControl; from: 0; to: 1.0; stepSize: 0.05; Kirigami.FormData.label: "Unlit stroke weight:" }
    QQC2.Slider { id: bloomControl; from: 0; to: 6; stepSize: 0.5; Kirigami.FormData.label: "Bloom / glow:" }
    QQC2.Slider { id: haloOpacityControl; from: 0; to: 1; stepSize: 0.05; Kirigami.FormData.label: "Halo opacity:" }
    QQC2.Slider { id: litGradientControl; from: 0; to: 1; stepSize: 0.05; Kirigami.FormData.label: "Lit gradient:" }
    QQC2.Slider { id: boundaryDepthControl; from: 0; to: 0.5; stepSize: 0.05; Kirigami.FormData.label: "Gradient reach:" }
    QQC2.Slider { id: glowControl; from: 0; to: 1; stepSize: 0.05; Kirigami.FormData.label: "Brightness:" }
    QQC2.CheckBox { id: breathe; Kirigami.FormData.label: "Breathe (backlight):" }
    QQC2.CheckBox { id: blinkColon; Kirigami.FormData.label: "Blink colon:" }
}
