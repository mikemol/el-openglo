// Primitive — the ONE drawn thing both displays are made of (W533, under W273): a rounded, antialiased
// rectangle whose ends are fully round (radius is half its SHORT side) and whose opacity is its COVERAGE.
// A segment is a long Primitive (a bar) and a pip a square one (a dot); the geometry, the one swappable
// input, is whatever width and height the display gives it.
//
// COVERAGE is the fraction of the primitive's own area that stands for light, from 0 to 1: a segment thinner
// than the device grid draws at the grid width with coverage thick / grid, an aperture pip at the fraction of
// its aperture the ink covers. Perceived brightness is luminance times AREA, so coverage IS that area: both
// displays state brightness the same way, and the layers (GhostLayer, EmissionHalo, the lit pass) take
// primitives without caring which display made them.
import QtQuick

Rectangle {
    id: prim
    property real coverage: 1.0   // 0 to 1: the fraction of this primitive's area that is light
    antialiasing: true
    radius: Math.min(width, height) / 2
    opacity: prim.coverage
}
