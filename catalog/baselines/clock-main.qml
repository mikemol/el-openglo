import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    // --- geometry: the SAME tables as the wallpaper (do not hand-edit) ---
    property var segGeom: ({ "A": ["h", 0, 0], "G": ["h", 0, 1], "D": ["h", 0, 2], "F": ["v", 0, 0], "B": ["v", 1, 0], "E": ["v", 0, 1], "C": ["v", 1, 1] })
    property var digSegs: ({ "0": "ABCDEF", "1": "BC", "2": "ABDEG", "3": "ABCDG", "4": "BCFG", "5": "ACDFG", "6": "ACDEFG", "7": "ABC", "8": "ABCDEFG", "9": "ABCDFG" })

    // ⚑ BOUND, NOT BAKED (⊕ONE-THEME, W35; catalog/one-theme.md): lit = ForegroundNormal
    // (the fg token), ghost = ForegroundInactive (fg_in), hot = ForegroundActive
    // (fg_act) — the active scheme's View roles. ONE package: applying
    // EL-Amber.colors is what makes this clock amber. The panel is the ground.
    Kirigami.Theme.colorSet: Kirigami.Theme.View
    Kirigami.Theme.inherit: false
    property color litColor: Kirigami.Theme.textColor
    property color ghostColor: Kirigami.Theme.disabledTextColor
    property color hotColor: Kirigami.Theme.activeTextColor
    // ghost opacity — SOLVED by the palette (ghost_alpha on every token), GLOBAL
    // across the variants (W23) and so bakeable in one package. The ghost
    // segments were drawn OPAQUE here, so the seen ghost was the declared
    // colour rather than its composite over the ground the palette solved for.
    property real ghostAlpha: 0.566
    property int segLen: Math.max(6, Math.floor(height * 0.42))
    // stroke base in segLen: the substrate's module stroke (0.105 H) at weight=1
    property int segThick: Math.max(2, Math.floor(segLen * 0.169))
    property real dotSize: Math.max(2, segLen * 0.211)
    // ⊕STROKE-WEIGHT: perceived brightness = luminance x AREA, so the lit stroke
    // is drawn FULLER than the ghost outline (a real EL segment is physically
    // fuller than its etched ghost). weight=1 -> lit 1.25x, ghost 0.81x, ratio
    // 1.54; weight=0 -> equal strokes. Lost in the recovery and rebuilt from
    // COTYPE.md session 41; the kcfg had kept the key all along.
    property real weight: (plasmoid.configuration.weight === undefined) ? 1.0
                          : plasmoid.configuration.weight
    property real strokeLit: segThick * (1 + 0.25 * weight)
    // the ghost's weight is its own slider (operator: "I want to be able to
    // make that still a bit smaller"); 0.81 is what weight=1 used to give
    // 0.4 is the operator's live tuning, promoted to the default (2026-09-22)
    property real ghostWeight: (plasmoid.configuration.ghostWeight === undefined) ? 0.4
                               : plasmoid.configuration.ghostWeight
    property real strokeGhost: segThick * ghostWeight
    // gap between digit boxes, in segLen: the substrate's module PITCH minus the
    // box (segment_topology.MODULE_METRICS — four datasheets agree on 12.7 mm
    // for a 14.22 mm digit). It is a FLOOR: the slider starts here.
    property real digitGap: (plasmoid.configuration.digitGap === undefined) ? 1.179
                            : plasmoid.configuration.digitGap
    // ⊕BLOOM: the halo is a BLUR of the lit layer only — never the ghost, never
    // a wider opaque copy. 0 disables the layer (crisp fallback); default 4.0 —
    // the operator's live tuning (2026-09-22), up from the authored 1.5.
    property real bloom: (plasmoid.configuration.bloom === undefined) ? 4.0
                         : plasmoid.configuration.bloom

    property string timeStr: "0000"
    property bool colonOn: true

    Timer {
        interval: 500; running: true; repeat: true
        onTriggered: {
            var d = new Date();
            var h = d.getHours();
            if (!plasmoid.configuration.use24h) { h = h % 12; if (h === 0) h = 12; }
            var mm = d.getMinutes();
            var ss = d.getSeconds();
            var s = (h < 10 ? "0" : "") + h + (mm < 10 ? "0" : "") + mm;
            if (plasmoid.configuration.showSeconds) s += (ss < 10 ? "0" : "") + ss;
            root.timeStr = s;
            if (plasmoid.configuration.blinkColon) root.colonOn = !root.colonOn;
            else root.colonOn = true;
        }
    }

    preferredRepresentation: fullRepresentation
    fullRepresentation: Item {
        Layout.preferredWidth: segRow.implicitWidth + segLen
        Layout.minimumWidth: segRow.implicitWidth + segLen
        Row {
            id: segRow
            anchors.centerIn: parent
            // ⚑ THE KERNING.  A digit's strokes overhang its segLen box by half a
            // stroke on each side, so a 0.25·segLen gap read as touching while the
            // colon slot added 0.7·segLen on ONE side (operator, 2026-09-21: "the
            // crime is in the kerning"). The gap is the digitGap slider, and the
            // colon is CENTRED in the whole space between its two neighbours.
            spacing: Math.round(segLen * root.digitGap)
            Repeater {
                model: root.timeStr.length
                // ⚑ THE DISPLAY IS SHARED, THE MOUNT IS OURS (W33, s133): this
                // cell's body used to live here as `component Digit` and is now
                // SegmentChar.qml — the one segment display every surface mounts
                // (the live wallpaper drew its own Canvas copy; the operator saw
                // that copy as "rectangles of construction paper"). What stays
                // here is the mount: the digit height off the panel, the gap, and
                // which cell carries the colon.
                SegmentChar {
                    segGeom: root.segGeom
                    digSegs: root.digSegs
                    ch: root.timeStr.charAt(index)
                    // the colon follows the SECOND digit (HH:MM) and the fourth
                    // when seconds show — this said index 2 and drew "232: 0"
                    // (operator, 2026-09-21; the headless render showed it too)
                    insertColon: (index === 1) || (index === 3 && root.timeStr.length > 4)
                    colonOn: root.colonOn
                    segLen: root.segLen
                    segThick: root.segThick
                    dotSize: root.dotSize
                    colonAdvance: 0.000
                    cellGap: segRow.spacing
                    litColor: root.litColor
                    ghostColor: root.ghostColor
                    ghostAlpha: root.ghostAlpha
                    showGhost: plasmoid.configuration.showGhost
                    weight: root.weight
                    ghostWeight: root.ghostWeight
                    bloom: root.bloom
                }
            }
        }
    }

    // ⚑ THE DIGIT AND ITS SEGMENT LIVED HERE (W33, s133). They are
    // templates/SegmentChar.qml now — the ONE segment display, mounted by this
    // clock and by the live wallpaper, so an emission fix (a gradient, a
    // boundary, diffusion) lands on both at once and the clock inherits it at
    // any DPI. The colon's advance and the cell gap are passed IN: they are the
    // mount's, not the display's.
}
