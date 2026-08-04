#!/usr/bin/env python3
# [RECONSTRUCTED from this session's own tool calls — later compacted session, not on-disk
#  transcript. Faithful to the create_file content. Verify before trusting as final.]
"""Projected (not authored) segment glyphs — the COMPOSED pipeline.

Two stages, not two competing approaches:
  1. CONSTRUCT the presence/absence ink field.
     - outline font: native winding (make_glyph_ink.ink_field) — curve intent preserved.
     - bitmap font (Unifont): rasterize at native cell size (raster_ink).
     Either way: G(x,y) = +1 ink / -1 not-ink, and OUTSIDE the cell is pure not-here (-1).
  2. CONSUME it with the cohomological (boundary-relative) matcher: probe in the ink's
     OWN bbox frame (shift/scale invariant) with flank offset scaled to the measured
     stroke width, presence AND absence conjunction. Match at the 22-JOIN; derez down.

NOTE: superseded as the MATCHER by glyph_match.py (region-graph + Matthews-phi congruence);
project_font remains LIVE for its ingest (winding_ink / raster_ink), which glyph_match uses.
"""
import math
import segment_topology as ST
import make_glyph_ink as GI


def endpoints(spec):
    k = spec[0]
    if k == "h": return (spec[1], spec[3], spec[2], spec[3])
    if k == "v": return (spec[1], spec[2], spec[1], spec[3])
    if k == "d": return (spec[1][0], spec[1][1], spec[2][0], spec[2][1])

SEG = {k: endpoints(ST.GEOM22[k]) for k in ST.SEG22}


def winding_ink(path, ch, box=(2.0, 4.0)):
    """Outline font: CSG membership via winding. Curve intent preserved."""
    return GI.ink_field(path, ch, box=box)


def raster_ink(path, ch, box=(2.0, 4.0), cell=64):
    """Bitmap font (Unifont): rasterize the glyph to its native pixel grid, sample.
    OUTSIDE the drawn area is pure not-here (-1)."""
    from PIL import Image, ImageFont, ImageDraw
    import numpy as np
    f = ImageFont.truetype(path, cell)
    im = Image.new("L", (cell, cell), 0)
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), ch, font=f)
    w = bb[2]-bb[0] or 1; h = bb[3]-bb[1] or 1
    d.text((-bb[0], -bb[1]), ch, fill=255, font=f)
    arr = np.array(im)[:h, :w]
    if arr.max() == 0:
        return lambda x, y: -1
    W, H = box
    def G(gx, gy):
        if not (0 <= gx <= W and 0 <= gy <= H):
            return -1
        px = min(w-1, int(gx/W*(w-1))); py = min(h-1, int(gy/H*(h-1)))
        return 1 if arr[py, px] > 96 else -1
    return G


def _ink_bbox(G, W=2.0, H=4.0, res=56):
    xs = []; ys = []
    for i in range(res+1):
        for j in range(res+1):
            x = i/res*W; y = j/res*H
            if G(x, y) > 0: xs.append(x); ys.append(y)
    return (min(xs), max(xs), min(ys), max(ys)) if xs else (0, W, 0, H)


def _stroke_width(G, bb, res=56):
    x0, x1, y0, y1 = bb
    runs = []
    for frac in (0.3, 0.5, 0.7):
        ym = y0 + (y1-y0)*frac; run = 0
        for i in range(res+1):
            x = x0 + (x1-x0)*i/res
            if G(x, ym) > 0: run += 1
            elif run: runs.append(run); run = 0
        if run: runs.append(run)
    runs = sorted(runs)
    med = runs[len(runs)//2] if runs else res*0.1
    return max(0.06, med/res*(x1-x0))


def project(G, tau=0.34):
    """Cohomological match at the 22-join. Boundary-relative: bbox frame +
    stroke-width flank + outside=not-here. Returns the lit 22-seg set."""
    x0, x1, y0, y1 = _ink_bbox(G)
    sw = _stroke_width(G, (x0, x1, y0, y1))
    off = sw * 1.5
    def remap(px, py):
        return (x0 + (x1-x0)*px/2.0, y0 + (y1-y0)*py/4.0)
    lit = set()
    for k, s in SEG.items():
        ax, ay, bx, by = s; dx, dy = bx-ax, by-ay
        L = math.hypot(dx, dy) or 1e-9; nx, ny = -dy/L, dx/L
        n = 11; here = 0; nt = 0
        for i in range(n):
            cx, cy = ax + dx*i/(n-1), ay + dy*i/(n-1)
            here += 1 if G(*remap(cx, cy)) > 0 else 0
            for sgn in (1, -1):
                fx, fy = remap(cx + sgn*nx*off, cy + sgn*ny*off)
                nt += 1 if G(fx, fy) < 0 else 0
        if (here/n)*(nt/(2*n)) > tau:
            lit.add(k)
    return lit


def project_char(path, ch, kind="outline", tau=0.34):
    G = (raster_ink if kind == "bitmap" else winding_ink)(path, ch)
    return project(G, tau)
