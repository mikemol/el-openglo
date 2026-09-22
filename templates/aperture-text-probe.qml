// aperture-text-probe — TEXT through the pinholes (W54 step 3; operator: "plain
// Unifont behind the mask"). The backdrop is a Qt Text item — whatever font Qt
// can shape, with the hinting knobs Text has and a Canvas fillText does not —
// grabbed once into the field's backdrop canvas. No glyph table, no column
// bytes: the aperture does the quantisation live. `$font` and `$text` are the
// probe's holes; `$templates` is where ApertureField lives.
import QtQuick
import org.kde.kirigami as Kirigami
import "$templates" as EL

Item {
    id: probe
    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false
    EL.ApertureField {
        id: field
        anchors.fill: parent
        rows: 8; u: 4; scale: 4
        litColor: Kirigami.Theme.textColor
        ghostColor: Kirigami.Theme.disabledTextColor
        ghostOpacity: $ghostAlpha
        gamma: $gamma
        // the viewport (W47): the backdrop is $backdropRows rows tall — a 16-row
        // Unifont cell read 1:1, one Unifont pixel per pip — and the 8-row field
        // looks through the band starting $offsetRows rows down
        backdropRows: $backdropRows
        // the harness may override the band per frame (render_qml --set offsetRows=N):
        // that is how the vertical scroll is captured, one render per step
        offsetY: ((typeof plasmoid !== "undefined" && plasmoid.configuration.offsetRows !== undefined)
                  ? plasmoid.configuration.offsetRows : $offsetRows) * scale
        // grab the source, hand the grab to an Image (what a Canvas can draw),
        // draw it into the backdrop, integrate. The grab result is held so its
        // url stays valid until the Image has it.
        property var grab: null
        onBackdropReady: source.grabToImage(function (r) { field.grab = r; carrier.source = r.url; })
    }
    Image {
        id: carrier
        x: -width - 1000; y: 0
        cache: false
        onStatusChanged: if (status === Image.Ready) {
            field.backdrop.width = width;
            var ctx = field.backdrop.getContext("2d");
            ctx.clearRect(0, 0, field.backdrop.width, field.backdrop.height);
            ctx.drawImage(carrier, 0, 0);
            field.sample();
        }
    }
    // the backdrop source, at backdrop resolution: rows*scale px tall. Drawn in
    // black on transparent — ink is alpha. Two grids made commensurate: the
    // pixel size is the field's height in backdrop pixels, hinted to that grid.
    Text {
        id: source
        // parked outside the window: an item at opacity 0 grabs as transparent
        x: -width - 1000; y: 0
        height: field.backdropRows * field.scale
        text: "$text"
        color: "black"
        font.family: "$font"
        // the em IS the backdrop's height in backdrop pixels: with backdropRows =
        // the bitmap font's cell (16 for Unifont) one font pixel is one pip; the
        // two grids commensurate, no hinting machinery needed
        font.pixelSize: field.backdropRows * field.scale
        font.hintingPreference: Font.PreferFullHinting
        renderType: Text.NativeRendering
        verticalAlignment: Text.AlignVCenter
    }
}
