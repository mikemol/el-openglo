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
$displayDecls
    // MOUNT layer: this clock's own
    property alias cfg_use24h: use24h.checked
    property alias cfg_showSeconds: showSeconds.checked
    property alias cfg_blinkColon: blinkColon.checked
    property bool cfg_use24hDefault
    property bool cfg_showSecondsDefault
    property bool cfg_blinkColonDefault
    Kirigami.FormLayout {
$displayControls
        QQC2.CheckBox { id: use24h; Kirigami.FormData.label: "24-hour clock:" }
        QQC2.CheckBox { id: showSeconds; Kirigami.FormData.label: "Show seconds:" }
        QQC2.CheckBox { id: blinkColon; Kirigami.FormData.label: "Blink colon:" }
    }
}
