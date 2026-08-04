#!/usr/bin/env python3
# [RECONSTRUCTED from this session's own tool calls — later compacted session, not on-disk
#  transcript. Faithful to the create_file content. Verify before trusting as final.]
"""Native TTF ink field (⊕FONT-INK-INGEST) — operate the engine, don't farm it out.

A glyph's fill is the WINDING NUMBER over its ORIENTED contours (TrueType: nonzero
rule). Computing it ourselves from the native outline (a) fixes holes analytically —
a counter is wound opposite, so its crossings subtract to winding 0 = hollow — and
(b) keeps the oriented ink boundary, which is exactly the contrast signal the
conjunction matcher needs. Farming fill to matplotlib/PIL discarded that orientation
(concatenated contours lose which way each winds) — the lossy-external-projector
error. Curves are flattened to fine polylines (orientation preserved; NOT the same as
rasterizing to a pixel grid — no boundary detail is quantized away)."""
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen


def _flatten_q(p0, c, p1, n=12):
    return [((1-t)**2*p0[0]+2*(1-t)*t*c[0]+t*t*p1[0],
             (1-t)**2*p0[1]+2*(1-t)*t*c[1]+t*t*p1[1])
            for t in [i/n for i in range(1, n+1)]]


def contours(path, ch):
    """Native oriented contours as closed polylines (winding preserved)."""
    f = TTFont(path); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    pen = RecordingPen(); gs[cmap[ord(ch)]].draw(pen)
    polys = []; cur = []; last = (0, 0)
    for op, a in pen.value:
        if op == "moveTo":
            cur = [a[0]]; last = a[0]
        elif op == "lineTo":
            cur.append(a[0]); last = a[0]
        elif op == "qCurveTo":
            pts = list(a); on = pts[-1]; offs = pts[:-1]; prev = last
            for i in range(len(offs)):
                c = offs[i]
                nxt = on if i == len(offs)-1 else ((offs[i][0]+offs[i+1][0])/2,
                                                   (offs[i][1]+offs[i+1][1])/2)
                cur += _flatten_q(prev, c, nxt); prev = nxt
            last = on
        elif op == "curveTo":
            cur.append(a[-1]); last = a[-1]
        elif op == "closePath":
            if len(cur) >= 3:
                cur.append(cur[0])         # explicitly close
                polys.append(cur); cur = []
    return polys


def _is_left(a, b, p):
    return (b[0]-a[0])*(p[1]-a[1]) - (p[0]-a[0])*(b[1]-a[1])


def _winding(px, py, polys):
    """Winding number of (px,py) over all oriented contours (Sunday wn_PnPoly)."""
    wn = 0
    for poly in polys:
        for i in range(len(poly)-1):
            a, b = poly[i], poly[i+1]
            if a[1] <= py:
                if b[1] > py and _is_left(a, b, (px, py)) > 0:
                    wn += 1
            else:
                if b[1] <= py and _is_left(a, b, (px, py)) < 0:
                    wn -= 1
    return wn


def ink_field(path, ch, box=(2.0, 4.0)):
    """Two-valued native ink field G(gx,gy) in the segment box: +1 ink / -1 no-ink,
    via nonzero winding (holes subtract). y-flipped (font up -> grid down)."""
    polys = contours(path, ch)
    xs = [p[0] for pl in polys for p in pl]; ys = [p[1] for pl in polys for p in pl]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H = box
    tp = [[((px-x0)/(x1-x0)*W, H-(py-y0)/(y1-y0)*H) for px, py in pl] for pl in polys]
    return lambda gx, gy: 1 if _winding(gx, gy, tp) != 0 else -1
