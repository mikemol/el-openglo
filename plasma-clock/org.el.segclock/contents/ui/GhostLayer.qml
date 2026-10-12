// GhostLayer — the ONE un-energised layer both displays mount (W532, under W273). The ghost is the LEDs or
// segments that are THERE but not lit: drawn flat, never bloomed, never gradient-fed. The unlit primitives
// (a digit's unlit segments, an aperture field's pips) are this item's CHILDREN, each drawing itself in
// `ghostColor`; the layer owns the one opacity law and the show flag, so ghostAlpha, glow and showGhost mean
// the same on every display that mounts it (operator, W271: one renderer, so the same config points).
//
// THE LAW: a ghost primitive's opacity is ghostAlpha x glow (the whole cell's emission level), times whatever
// coverage the primitive itself stands for (a segment thinner than the grid dims by its coverage). The layer
// carries the first two; the child carries its own coverage. Qt multiplies a parent's opacity into its
// children's without a layer, so this is the same arithmetic as the per-child product it replaces.
//
// A DISPLAY THAT SHOULD NOT SHOW ITS GHOST sets showGhost false: the whole layer hides (nothing is drawn).
import QtQuick

Item {
    id: ghost
    property color ghostColor: "gray"   // the colour the primitives draw in; they read it from here
    property real ghostAlpha: 0.28      // the unlit substrate's opacity
    property real glow: 1.0             // a mount may breathe the whole cell
    property bool showGhost: true

    // the unlit primitives are mounted as this item's children
    default property alias content: slot.data

    visible: ghost.showGhost
    opacity: ghost.ghostAlpha * ghost.glow

    Item { id: slot; anchors.fill: parent }
}
