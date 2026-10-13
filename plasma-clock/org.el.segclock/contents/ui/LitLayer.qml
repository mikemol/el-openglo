// LitLayer — the ONE energised layer both displays mount (W534, under W273): the crisp lit core on top of the
// halo. The lit primitives (a digit's lit segments, an aperture field's pips) are this item's CHILDREN, each
// drawing itself in the lit colour at its own coverage; the layer owns the emission level, so `glow` dims the
// lit core the same way on every display that mounts it (operator, W271: one renderer, so the same config
// points). Before this the clock dimmed its lit core by glow and the marquee did not: the setting reached the
// marquee's ghost and halo and left the core at full.
//
// THE LAW: a lit primitive's opacity is glow x its own coverage. The layer carries the first factor, the
// primitive (Primitive.qml) the second. Qt multiplies a parent's opacity into its children's without a layer,
// so this is the same arithmetic as the per-child product it replaces; a glow of 1.0 changes nothing.
import QtQuick

Item {
    id: lit
    property real glow: 1.0             // a mount may breathe the whole cell

    // the lit primitives are mounted as this item's children
    default property alias content: slot.data

    opacity: lit.glow

    Item { id: slot; anchors.fill: parent }
}
