// aperture-probe — the ApertureField over a SYNTHETIC backdrop, for the gate (W54).
// Not a shipped surface: render_qml renders it under a variant's scheme and
// check_aperture reads three pips — one clear of the block (the ghost floor),
// one the block's edge crosses at exactly half (halfway), one under it (lit).
// `$templates` is the templates directory as a file URL, filled by render_qml.
import QtQuick
import org.kde.kirigami as Kirigami
import "$templates" as EL

Item {
    id: probe
    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false
    // the three pips the check reads, and where the block's edge sits
    readonly property int edgeCol: 10
    EL.ApertureField {
        id: field
        anchors.fill: parent
        rows: 8; u: 4; scale: 4
        litColor: Kirigami.Theme.textColor
        ghostColor: Kirigami.Theme.disabledTextColor
        ghostOpacity: $ghostAlpha
        onBackdropReady: {
            backdrop.width = cols * scale;
            var ctx = backdrop.getContext("2d");
            ctx.clearRect(0, 0, backdrop.width, backdrop.height);
            ctx.fillStyle = "black";
            // the block's left edge half a pip into edgeCol; 30 pips wide, full height
            ctx.fillRect(probe.edgeCol * scale + scale / 2, 0, 30 * scale, backdrop.height);
            sample();
        }
    }
}
