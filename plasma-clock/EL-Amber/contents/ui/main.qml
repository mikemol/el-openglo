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

    property color litColor: "#ffd499"
    property color ghostColor: "#e5bf89"
    property color hotColor: "#fab14b"
    // ghost opacity — SOLVED by the palette (ghost_alpha on every token). The
    // ghost segments were drawn OPAQUE here, so the seen ghost was the declared
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
    property real ghostWeight: (plasmoid.configuration.ghostWeight === undefined) ? 0.81
                               : plasmoid.configuration.ghostWeight
    property real strokeGhost: segThick * ghostWeight
    // gap between digit boxes, in segLen: the substrate's module PITCH minus the
    // box (segment_topology.MODULE_METRICS — four datasheets agree on 12.7 mm
    // for a 14.22 mm digit). It is a FLOOR: the slider starts here.
    property real digitGap: (plasmoid.configuration.digitGap === undefined) ? 0.786
                            : plasmoid.configuration.digitGap
    // ⊕BLOOM: the halo is a BLUR of the lit layer only — never the ghost, never
    // a wider opaque copy. 0 disables the layer (crisp fallback); default 1.5.
    property real bloom: (plasmoid.configuration.bloom === undefined) ? 1.5
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
                Digit {
                    ch: root.timeStr.charAt(index)
                    // the colon follows the SECOND digit (HH:MM) and the fourth
                    // when seconds show — this said index 2 and drew "232: 0"
                    // (operator, 2026-09-21; the headless render showed it too)
                    insertColon: (index === 1) || (index === 3 && root.timeStr.length > 4)
                }
            }
        }
    }

    component Digit: Item {
        property string ch: "8"
        property bool insertColon: false
        // the colon adds the substrate's colon_advance (ZERO on the 88:88 module —
        // the dots sit in the ordinary gap, centred between the two digits)
        property real colonSlot: segLen * 0.000
        property real colonX: segLen + (colonSlot + segRow.spacing) / 2 - root.dotSize / 2
        width: segLen + (insertColon ? colonSlot : 0)
        height: segLen * 2

        function isOn(s) {
            return root.digSegs[ch] !== undefined && root.digSegs[ch].indexOf(s) !== -1
        }
        // one seven-segment glyph, three passes: ghost (un-energised, no halo),
        // then the lit layer blurred into a halo, then the crisp lit core on top
        Repeater {
            model: ["A","B","C","D","E","F","G"]
            Segment {
                seg: modelData
                visible: plasmoid.configuration.showGhost && !parent.isOn(modelData)
                color: root.ghostColor
                opacity: root.ghostAlpha
                thick: root.strokeGhost
            }
        }
        Item {
            id: halo
            anchors.fill: parent
            visible: root.bloom > 0
            layer.enabled: root.bloom > 0
            // ⚑ THE HALO IS SIZED BY THE STROKE, NOT IN PIXELS.  A fixed 64px
            // blurMax on a 3px panel stroke smeared the whole digit into one haze
            // (⊕VER 2026-09-21); `brightness` lifted the transparent surround
            // too. The radius is a few stroke widths, scaled by the slider, and
            // the halo is the lit colour itself at reduced opacity.
            layer.effect: MultiEffect {
                blurEnabled: true
                blur: 1.0
                blurMax: Math.max(2, Math.round(root.strokeLit * 2 * root.bloom))
                blurMultiplier: 1.0
            }
            opacity: 0.75
            Repeater {
                model: ["A","B","C","D","E","F","G"]
                Segment {
                    seg: modelData
                    visible: parent.parent.isOn(modelData)
                    color: root.litColor
                    thick: root.strokeLit
                }
            }
            ColonDot { visible: parent.parent.insertColon && root.colonOn; y: segLen*0.62 }
            ColonDot { visible: parent.parent.insertColon && root.colonOn; y: segLen*1.38 - root.dotSize }
        }
        Repeater {
            model: ["A","B","C","D","E","F","G"]
            Segment {
                seg: modelData
                visible: parent.isOn(modelData)
                color: root.litColor
                thick: root.strokeLit
            }
        }
        // colon dots after this digit: lit when on, ghost (never bloomed) when off
        ColonDot {
            visible: parent.insertColon
            color: root.colonOn ? root.litColor : root.ghostColor
            opacity: root.colonOn ? 1.0 : root.ghostAlpha
            y: segLen*0.62
        }
        ColonDot {
            visible: parent.insertColon
            color: root.colonOn ? root.litColor : root.ghostColor
            opacity: root.colonOn ? 1.0 : root.ghostAlpha
            y: segLen*1.38 - root.dotSize
        }
    }

    component ColonDot: Rectangle {
        width: root.dotSize; height: root.dotSize; radius: root.dotSize/2
        color: root.litColor
        antialiasing: true
        x: parent.colonX !== undefined ? parent.colonX : parent.parent.colonX
    }

    // one segment as a scene-graph vector item; the caller says which colour,
    // opacity and stroke weight — the geometry is the substrate's alone
    component Segment: Rectangle {
        property string seg: "A"
        property real thick: root.segThick
        property var g: root.segGeom[seg]         // [kind, ux, uy]
        property bool horiz: g[0] === "h"
        property real gap: segThick * 0.62
        antialiasing: true
        radius: thick/2
        width:  horiz ? segLen - gap*2 : thick
        height: horiz ? thick : segLen - gap*2
        // centred on the segment's axis so a heavier stroke grows both ways
        x: (g[1] * segLen) + (horiz ? gap : (segThick - thick)/2)
        y: (g[2] * segLen) + (horiz ? (segThick - thick)/2 : gap)
    }
}
