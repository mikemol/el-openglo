#!/usr/bin/env python3
"""SVG-font emitter (⊕SEG-FONT).

A font is a SERIALIZATION of the glyph tables segment_topology already owns —
not a fourth render backend. This emits an SVG font where each <glyph> path is
the union of the lit segment polygons at that character's projection, so an
installed EL-Segment font renders exactly the segments the wallpaper and clock
light. Ghost segments are inherently absent (a glyph is one path) — the declared
tradeoff, and the reason the phosphor plasmoid still exists.

Default format is 7-segment (the classic digital-watch face). 16-segment is
available for a full-alphabet font.

SVG-font coords are y-UP with baseline at 0; GEOM16 is y-DOWN in a 2x4 cell —
the emitter flips y and scales to the font em square.
"""
import segment_topology as _seg

EM = 1000            # units per em
CELL_W, CELL_H = 2.0, 4.0
SCALE = EM / CELL_H  # 4 cell-units tall -> full em
THICK = 0.34         # segment half-thickness in cell units (matches renderers)


def _seg_path(spec):
    """Return an SVG subpath (M..Z) for one segment polygon, flipped to y-UP."""
    T = THICK
    g = T * 0.6
    if spec[0] == "h":
        _, a, b, y = spec
        a, b, y = a, b, y
        pts = [(a + g, y - T / 2), (b - g, y - T / 2),
               (b - g, y + T / 2), (a + g, y + T / 2)]
    elif spec[0] == "v":
        _, x, y0, y1 = spec
        pts = [(x - T / 2, y0 + g), (x + T / 2, y0 + g),
               (x + T / 2, y1 - g), (x - T / 2, y1 - g)]
    else:  # diagonal
        _, (ax, ay), (bx, by) = spec
        pts = [(ax - T / 2, ay), (ax + T / 2, ay),
               (bx + T / 2, by), (bx - T / 2, by)]
    # flip y (cell y-down -> font y-up) and scale
    out = []
    for i, (x, y) in enumerate(pts):
        fx = round(x * SCALE)
        fy = round((CELL_H - y) * SCALE)
        out.append(f"{'M' if i == 0 else 'L'}{fx} {fy}")
    return "".join(out) + "Z"


def glyph_path(ch, fmt="7"):
    """Union path of all lit segments for `ch` at `fmt`."""
    f = _seg.FORMATS[fmt]
    lit = _seg.project(_seg.glyph16(ch), fmt)
    subpaths = []
    for sid, spec in _seg.GEOM16.items():
        if sid not in f["mask"]:
            continue
        coarse = f["merge"].get(sid, sid)
        if coarse in lit:
            subpaths.append(_seg_path(spec))
    return "".join(subpaths)


def _xml_char(ch):
    return {"<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;",
            "'": "&apos;"}.get(ch, ch)


def emit_svg_font(fmt="7", family="EL Segment"):
    advance = round(CELL_W * SCALE) + 120  # cell width + inter-char gap
    charset = "0123456789" + ("ABCDEFGHIJKLMNOPQRSTUVWXYZ" if fmt != "7"
                              else "ABCDEFHJLPU")  # 7-seg legible letters only
    glyphs = []
    # space
    glyphs.append(f'<glyph unicode=" " glyph-name="space" horiz-adv-x="{advance}"/>')
    for ch in charset:
        d = glyph_path(ch, fmt)
        name = f"u{ord(ch):04X}"
        glyphs.append(f'<glyph unicode="{_xml_char(ch)}" glyph-name="{name}" '
                      f'horiz-adv-x="{advance}" d="{d}"/>')
    glyphs_xml = "\n".join(glyphs)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg">
<defs>
<font id="ELSegment{fmt}" horiz-adv-x="{advance}">
<font-face font-family="{family} {fmt}" units-per-em="{EM}"
  ascent="{EM}" descent="0" cap-height="{EM}" x-height="{EM}"/>
<missing-glyph horiz-adv-x="{advance}"/>
{glyphs_xml}
</font>
</defs>
</svg>
'''


DSEG_NOTE = """EL Segment font — zero-dependency alternative (DSEG7)
=====================================================
If you'd rather not use the phosphor plasmoid, the free DSEG font family
(Keshikan, SIL Open Font License — redistributable) renders seven- and
fourteen-segment digits with the stock Plasma Digital Clock:

  1. Download DSEG from https://github.com/keshikan/DSEG (OFL)
  2. Install: cp DSEG7Classic-*.ttf ~/.local/share/fonts/ && fc-cache -f
  3. Digital Clock widget -> Configure -> font -> DSEG7 Classic

Tradeoffs vs. the EL plasmoid: a font glyph is a single path, so it CANNOT show
the unlit "ghost" segments or the EL phosphor glow/grid — you get lit segments
on the panel background only. The EL-Segment SVG font emitted here has the same
limitation (fonts are inherently single-layer); it exists so OUR exact glyph
geometry is installable system-wide, sharing the one topology source.
"""
