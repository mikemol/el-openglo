// EmissionHalo — the ONE emission layer both displays mount (W500, under W272). A halo is a BLUR of the
// LIT layer only: never the ghost, never a wider opaque copy. The lit primitives (a digit's segments, an
// aperture field's pips) are this item's CHILDREN; the blur, its radius law and its opacity live here, so a
// display that mounts it gains bloom, haloOpacity and glow by mounting it, and the three settings mean the
// same on every display (operator, W271: one renderer, so the same config points).
//
// ⚑ THE RADIUS IS A FEW UNITS OF THE DISPLAY'S OWN LENGTH, NOT PIXELS. A fixed blurMax on a 3 px panel
// stroke smeared the whole digit into one haze (⊕VER 2026-09-21): the radius is `radiusUnit` x 2 x bloom,
// where radiusUnit is the length one unit of bloom stands for - the lit stroke width for the segments, the
// pip for the aperture. 0 bloom disables the layer (crisp fallback: nothing is drawn, nothing blurred).
//
// ⚑ THE SOFTWARE SCENE GRAPH HAS NO MultiEffect: under it this layer draws nothing, which is why the halo is
// observable only on the RHI path (the mesa kwin session, qt_sandbox mesa=True).
import QtQuick
import QtQuick.Effects

Item {
    id: halo
    property real bloom: 1.5          // the radius scale; 0 disables the layer
    property real haloOpacity: 0.75   // the halo's opacity (configurable: every render value is)
    property real glow: 1.0           // a mount may breathe the whole cell
    property real radiusUnit: 2       // the length one unit of bloom stands for (a stroke width, a pip)

    // the lit primitives are mounted as this item's children, inside the blurred layer
    default property alias content: slot.data

    visible: halo.bloom > 0
    layer.enabled: halo.bloom > 0
    layer.effect: MultiEffect {
        blurEnabled: true
        blur: 1.0
        blurMax: Math.max(2, Math.round(halo.radiusUnit * 2 * halo.bloom))
        blurMultiplier: 1.0
    }
    opacity: halo.haloOpacity * halo.glow

    Item { id: slot; anchors.fill: parent }
}
