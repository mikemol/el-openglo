import QtQuick
// ⚑ org.kde.kcm was the KF5 name; on Plasma 6 the module is org.kde.kcmutils and
// the old import made this page load NOTHING (blank, no error surfaced — the
// operator opened it 2026-09-21; nobody had since the recovery).
import org.kde.kcmutils as KCM
import org.kde.kirigami as Kirigami
import QtQuick.Controls as QQC2
import QtQuick.Layouts

KCM.SimpleKCM {
    property alias cfg_showGhost: showGhost.checked
    property alias cfg_use24h: use24h.checked
    property alias cfg_showSeconds: showSeconds.checked
    property alias cfg_blinkColon: blinkColon.checked
    // ⚑ THESE TWO SLIDERS EXISTED WITHOUT ALIASES — moving them changed nothing.
    property alias cfg_bloom: bloomSlider.value
    property alias cfg_weight: weightSlider.value
    property alias cfg_ghostWeight: ghostWeightSlider.value
    property alias cfg_digitGap: digitGapSlider.value
    // Plasma also sets cfg_<key>Default per entry (the marquee page showed the
    // refusals live, 2026-09-22; this page had the same eight, unseen) —
    // scripts/check_config_page.py measures; policy/config_page.rego holds it
    property bool cfg_showGhostDefault
    property bool cfg_use24hDefault
    property bool cfg_showSecondsDefault
    property bool cfg_blinkColonDefault
    property real cfg_bloomDefault
    property real cfg_weightDefault
    property real cfg_ghostWeightDefault
    property real cfg_digitGapDefault
    Kirigami.FormLayout {
        QQC2.CheckBox { id: showGhost; Kirigami.FormData.label: "Show ghost segments:" }
        QQC2.CheckBox { id: use24h; Kirigami.FormData.label: "24-hour clock:" }
        QQC2.CheckBox { id: showSeconds; Kirigami.FormData.label: "Show seconds:" }
        QQC2.CheckBox { id: blinkColon; Kirigami.FormData.label: "Blink colon:" }
        // to 6: the default is 4 now (the operator's tuning) and a slider whose
        // default sits at its end has no room above it
        QQC2.Slider { id: bloomSlider; from: 0; to: 6; stepSize: 0.5; Kirigami.FormData.label: "Bloom / glow:" }
        QQC2.Slider { id: weightSlider; from: 0; to: 1; stepSize: 0.25; Kirigami.FormData.label: "Lit stroke weight:" }
        QQC2.Slider { id: ghostWeightSlider; from: 0.3; to: 1.0; stepSize: 0.05; Kirigami.FormData.label: "Unlit stroke weight:" }
        // the minimum is the module pitch (segment_topology.MODULE_METRICS): two
        // packaged digits cannot sit closer, so the slider only opens the gap
        QQC2.Slider { id: digitGapSlider; from: $digitGapMin; to: 2.0; stepSize: 0.05; Kirigami.FormData.label: "Digit spacing:" }
    }
}
