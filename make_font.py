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


def _seg_points(spec):
    """One segment polygon as [(x, y)] in cell units, y-DOWN (the lattice's frame)."""
    T = THICK
    g = T * 0.6
    if spec[0] == "h":
        _, a, b, y = spec
        return [(a + g, y - T / 2), (b - g, y - T / 2), (b - g, y + T / 2), (a + g, y + T / 2)]
    if spec[0] == "v":
        _, x, y0, y1 = spec
        return [(x - T / 2, y0 + g), (x + T / 2, y0 + g), (x + T / 2, y1 - g), (x - T / 2, y1 - g)]
    _, (ax, ay), (bx, by) = spec
    return [(ax - T / 2, ay), (ax + T / 2, ay), (bx + T / 2, by), (bx - T / 2, by)]


def glyph_contours(ch, fmt="7"):
    """[[(x, y), ...], ...] — one closed contour per LIT segment of `ch` at `fmt`,
    in cell units, y-down. THE shared source: glyph_path (SVG) and build_ttf both
    consume it (⊕SEG-FONT-TTF: a TTF is a peer emitter of the topology, not an
    SVG->TTF conversion)."""
    f = _seg.FORMATS[fmt]
    lit = _seg.project(_seg.glyph16(ch), fmt)
    out = []
    for sid, spec in _seg.GEOM16.items():
        if sid not in f["mask"]:
            continue
        if f["merge"].get(sid, sid) in lit:
            out.append(_seg_points(spec))
    return out


def matrix_contours(ch, cols=5, rows=7, dot=0.86):
    """[[(x, y) x4], ...] — one square contour per LIT pixel of the 5x7 matrix
    glyph (display_types.MatrixDisplay), cell units, y-down. Square, not round:
    crisp at small TTF sizes (⊕DOT-FONT-TTF); the plasmoid's dots stay round."""
    import display_types as DT
    d = DT.DISPLAYS["5x7"] if (cols, rows) == (5, 7) else DT.MatrixDisplay(cols, rows)
    pad = (1.0 - dot) / 2
    out = []
    for (c, r) in sorted(d.glyph(ch)):
        x0, y0 = c + pad, r + pad
        out.append([(x0, y0), (x0 + dot, y0), (x0 + dot, y0 + dot), (x0, y0 + dot)])
    return out


def glyph_path(ch, fmt="7"):
    """Union path of all lit segments for `ch` at `fmt` (SVG font d=)."""
    subpaths = []
    for pts in glyph_contours(ch, fmt):
        out = []
        for i, (x, y) in enumerate(pts):
            fx = round(x * SCALE)
            fy = round((CELL_H - y) * SCALE)
            out.append(f"{'M' if i == 0 else 'L'}{fx} {fy}")
        subpaths.append("".join(out) + "Z")
    return "".join(subpaths)


def _xml_char(ch):
    return {"<": "&lt;", ">": "&gt;", "&": "&amp;", '"': "&quot;",
            "'": "&apos;"}.get(ch, ch)


def emit_svg_font(fmt="7", family="EL Segment"):
    advance = round(CELL_W * SCALE) + 120  # cell width + inter-char gap
    charset = SEG_CHARSET[fmt]                 # 7-seg: the legible letters only
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


SEG_CHARSET = {"7": "0123456789ABCDEFHJLPU",
               "16": "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"}
MATRIX_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_MARGIN = 0.15          # cell units of side bearing, both sides


def _cell_to_font(cell_w, cell_h, em=EM):
    """(scale, x_pad_units, y_flip) — fit a cell_w x cell_h cell into the em square
    on HEIGHT (a 2x4 segment cell maps as before; a 5x7 matrix cell fits its aspect)."""
    scale = em / cell_h
    return scale, _MARGIN * scale


def _shoelace(pts):
    return sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])) / 2


def build_ttf(contours_of, charset, cell_w, cell_h, family, style="Regular"):
    """A fontTools TTFont from a CONTOUR SOURCE (ch -> [[(x, y)...]] in cell
    units, y-down) — display-agnostic (⊕DOT-FONT-TTF lifted it). TrueType wants
    clockwise outer contours; every contour here is a solid, so each is wound CW
    after the y-flip (shoelace sign)."""
    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    scale, x_pad = _cell_to_font(cell_w, cell_h)
    advance = round(cell_w * scale + 2 * x_pad)
    names = ["space"] + [f"u{ord(c):04X}" for c in charset]
    fb = FontBuilder(EM, isTTF=True)
    fb.setupGlyphOrder([".notdef"] + names)
    fb.setupCharacterMap({0x20: "space", **{ord(c): f"u{ord(c):04X}" for c in charset}})
    glyphs, metrics = {}, {}
    pen = TTGlyphPen(None)
    glyphs[".notdef"] = pen.glyph()
    metrics[".notdef"] = (advance, 0)
    pen = TTGlyphPen(None)
    glyphs["space"] = pen.glyph()
    metrics["space"] = (advance, 0)
    for ch in charset:
        pen = TTGlyphPen(None)
        for pts in contours_of(ch):
            fpts = [(round(x * scale + x_pad), round((cell_h - y) * scale)) for x, y in pts]
            if _shoelace(fpts) > 0:              # CCW after the flip -> reverse to CW
                fpts = fpts[::-1]
            pen.moveTo(fpts[0])
            for p in fpts[1:]:
                pen.lineTo(p)
            pen.closePath()
        glyphs[f"u{ord(ch):04X}"] = pen.glyph()
        metrics[f"u{ord(ch):04X}"] = (advance, 0)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=EM, descent=0)
    fb.setupNameTable({"familyName": family, "styleName": style})
    fb.setupOS2(sTypoAscender=EM, sTypoDescender=0, usWinAscent=EM, usWinDescent=0)
    fb.setupPost(isFixedPitch=1)
    return fb.font


def build_segment_ttf(fmt="7"):
    return build_ttf(lambda ch: glyph_contours(ch, fmt), SEG_CHARSET[fmt],
                     CELL_W, CELL_H, f"EL Segment {fmt}")


def build_matrix_ttf(cols=5, rows=7):
    return build_ttf(lambda ch: matrix_contours(ch, cols, rows), MATRIX_CHARSET,
                     float(cols), float(rows), f"EL Matrix {cols}x{rows}")


def ttf_glyph_centroid_side(font, ch):
    """(x_side, y_side) of the built glyph's centroid relative to its bbox middle:
    +1 / -1 / 0 — read from the TTF's OWN glyf table, not from the source."""
    name = f"u{ord(ch):04X}"
    g = font["glyf"][name]
    if g.numberOfContours <= 0:
        return None
    coords = g.getCoordinates(font["glyf"])[0]
    xs, ys = [p[0] for p in coords], [p[1] for p in coords]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    sgn = lambda v: (v > 1) - (v < -1)
    return sgn(cx - mx), sgn(cy - my)


def source_centroid_side(contours, cell_h):
    """The same side test on the SOURCE contours, mapped through the same y-flip —
    so the orientation gate is source-relative (⊕DOT-FONT-TTF: an absolute threshold
    calibrated on one display false-failed on another)."""
    pts = [(x, cell_h - y) for c in contours for (x, y) in c]
    if not pts:
        return None
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
    mx, my = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    sgn = lambda v: (v > 0.02) - (v < -0.02)
    return sgn(cx - mx), sgn(cy - my)


def gate_ttf_orientation(font, contours_of, cell_h, chars):
    """[(ch, ttf_side, source_side)] where the built glyph's centroid side disagrees
    with the source's — a SPEC-FLIP (session 23) reaching the installed font."""
    bad = []
    for ch in chars:
        t = ttf_glyph_centroid_side(font, ch)
        s = source_centroid_side(contours_of(ch), cell_h)
        if t is None or s is None:
            continue
        # compare only on axes where the source is decisively off-centre
        if any(sv and tv != sv for tv, sv in zip(t, s)):
            bad.append((ch, t, s))
    return bad


OUTPUTS = (("EL-Segment-7.ttf", lambda: build_segment_ttf("7")),
           ("EL-Segment-16.ttf", lambda: build_segment_ttf("16")),
           ("EL-Matrix-5x7.ttf", lambda: build_matrix_ttf(5, 7)),
           ("EL-Segment-7.svg", lambda: emit_svg_font("7")),
           ("EL-Segment-16.svg", lambda: emit_svg_font("16")))


def render_all(out_dir):
    """Write every font under out_dir; returns the paths."""
    import os
    os.makedirs(out_dir, exist_ok=True)
    written = []
    for name, make in OUTPUTS:
        p = os.path.join(out_dir, name)
        obj = make()
        if isinstance(obj, str):
            open(p, "w", encoding="utf-8").write(obj)
        else:
            obj.save(p)
        written.append(p)
    return written


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


if __name__ == "__main__":
    import os
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    out = render_all(os.path.join(here, "fonts"))
    open(os.path.join(here, "fonts", "README-DSEG.txt"), "w").write(DSEG_NOTE)
    print(f"make_font: wrote {len(out)} fonts under fonts/")
    for name, make in OUTPUTS:
        if name.endswith(".ttf"):
            f = make()
            src = ((lambda ch: glyph_contours(ch, name.split("-")[2].split(".")[0]))
                   if "Segment" in name else (lambda ch: matrix_contours(ch)))
            cell_h = CELL_H if "Segment" in name else 7.0
            chars = SEG_CHARSET.get(name.split("-")[2].split(".")[0], MATRIX_CHARSET)
            bad = gate_ttf_orientation(f, src, cell_h, chars)
            print(f"  {name}: {len(f.getGlyphOrder())} glyphs; orientation gate: "
                  f"{'ok' if not bad else bad}")
            if bad:
                sys.exit(1)
