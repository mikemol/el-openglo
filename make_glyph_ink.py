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
from fontTools.pens.recordingPen import DecomposingRecordingPen


def _flatten_q(p0, c, p1, n=12):
    return [((1-t)**2*p0[0]+2*(1-t)*t*c[0]+t*t*p1[0],
             (1-t)**2*p0[1]+2*(1-t)*t*c[1]+t*t*p1[1])
            for t in [i/n for i in range(1, n+1)]]


def contours(path, ch):
    """Native oriented contours as closed polylines (winding preserved).

    ⚑ COMPOSITE GLYPHS DECOMPOSE.  A plain RecordingPen records `addComponent`
    for 'é' (= 'e' + acute) and nothing else, so every accented character
    ingested as EMPTY ink — measured 2026-09-21 (⊕MATRIX-FONT-INPUT, session
    76): 'e' 2 contours, 'é' 0. The decomposing pen draws the components
    through the glyph set with their offsets applied."""
    f = TTFont(path); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    pen = DecomposingRecordingPen(gs); gs[cmap[ord(ch)]].draw(pen)
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


def outline_stats(path, ch, axis_tol=0.15):
    """Outline length by KIND, in font units: {"straight", "diagonal", "curve"}
    plus "bbox". A lineTo whose direction is within `axis_tol` (as |dy/dx| or
    |dx/dy|) of an axis is straight, any other lineTo is diagonal, and every
    flattened curve piece is curve. This is what a glyph CLASS is read from
    (⊕SEG-DOTPRODUCT-TEMPLATES, session 78): the shape the templates must
    follow, measured on the ink rather than guessed from the letter."""
    import math
    f = TTFont(path); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    if ord(ch) not in cmap:
        return None
    pen = DecomposingRecordingPen(gs); gs[cmap[ord(ch)]].draw(pen)
    out = {"straight": 0.0, "diagonal": 0.0, "curve": 0.0}
    xs = []; ys = []
    last = start = (0, 0)
    for op, a in pen.value:
        if op == "moveTo":
            last = start = a[0]; xs.append(a[0][0]); ys.append(a[0][1])
        elif op == "lineTo":
            p = a[0]; dx, dy = p[0]-last[0], p[1]-last[1]
            L = math.hypot(dx, dy)
            if L:
                ratio = min(abs(dx), abs(dy)) / max(abs(dx), abs(dy))
                out["straight" if ratio <= axis_tol else "diagonal"] += L
            last = p; xs.append(p[0]); ys.append(p[1])
        elif op in ("qCurveTo", "curveTo"):
            pts = list(a); on = pts[-1]
            prev = last
            for q in pts:
                if q is None:
                    continue
                out["curve"] += math.hypot(q[0]-prev[0], q[1]-prev[1]); prev = q
                xs.append(q[0]); ys.append(q[1])
            last = on
        elif op == "closePath":
            dx, dy = start[0]-last[0], start[1]-last[1]
            L = math.hypot(dx, dy)
            if L:
                ratio = min(abs(dx), abs(dy)) / max(abs(dx), abs(dy))
                out["straight" if ratio <= axis_tol else "diagonal"] += L
            last = start
    out["bbox"] = (min(xs), max(xs), min(ys), max(ys)) if xs else None
    return out


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


def ink_field(path, ch, box=(2.0, 4.0), frame="stretch"):
    """Two-valued native ink field G(gx,gy) in the segment box: +1 ink / -1 no-ink,
    via nonzero winding (holes subtract). y-flipped (font up -> grid down).

    frame="stretch" (default): the glyph's own bbox is stretched anisotropically
    onto the box. A display cell is 1:2; a LiberationMono cap is ~0.68:1, so
    every glyph is squeezed to the cell — which is what a segment display does.
    frame="fit": aspect-preserving — fit on the tighter axis, centre on the
    other. ⚑ MEASURED WORSE (⊕SEG-PROJECT-CALIBRATE, COTYPE session 75): the
    wide glyphs fit on width, leave top/bottom margins, and every a/d segment
    misses — mean Jaccard 0.43 vs 0.64. Kept as a mode because the frame
    hypothesis was the calibration's first input and its rejection is the
    record; a proportional font's narrow glyphs may yet want it."""
    polys = contours(path, ch)
    xs = [p[0] for pl in polys for p in pl]; ys = [p[1] for pl in polys for p in pl]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    W, H = box
    if frame == "stretch":
        sx, sy, ox, oy = W/(x1-x0), H/(y1-y0), 0.0, 0.0
    elif frame == "fit":
        s = min(W/(x1-x0), H/(y1-y0))
        sx = sy = s
        ox, oy = (W-(x1-x0)*s)/2, (H-(y1-y0)*s)/2
    elif frame == "metrics":
        # ⚑ THE FONT'S FRAME, as matrix_glyph uses (session 76): x from the
        # glyph's own bbox (a segment cell is monospace), y from CAP HEIGHT ->
        # BASELINE so a hyphen stays a bar at mid-height instead of being
        # stretched into a slab, and a descender goes below the cell (session
        # 82: - _ = ' ! all scored 0 under "stretch" for exactly this reason).
        cap, _desc = font_frame(path)
        sx, sy = W/(x1-x0), H/cap
        ox, oy = 0.0, 0.0
        y0 = 0.0                      # font baseline is cell bottom
    else:
        raise ValueError(f"ink_field: unknown frame {frame!r} (stretch|fit|metrics)")
    tp = [[(ox+(px-x0)*sx, H-oy-(py-y0)*sy) for px, py in pl] for pl in polys]
    return lambda gx, gy: 1 if _winding(gx, gy, tp) != 0 else -1


# ── ⊕MATRIX-FONT-INPUT: a font glyph into the dot matrix ─────────────────────
#
# ⚑ THE FRAME IS THE FONT'S, NOT THE GLYPH'S.  ink_field stretches a glyph's own
# bbox onto the cell, which is right for a segment display (every glyph fills
# the module) and WRONG for a matrix with a baseline: 'g' would fill all eight
# rows and 'a' would stand as tall as 'H'. Here the body rows (0..baseline) span
# CAP HEIGHT -> BASELINE in font units and the rows below span BASELINE ->
# DESCENDER, so an x-height glyph lands short and a descender goes under —
# the same convention FONT5x8 is authored in (display_types.FONT5x8_BASELINE).
# Horizontally the glyph's own bbox is stretched to the columns: a matrix font
# is monospace, and the authored table does the same by hand.

DESCENDER_PROBES = "gjpqy"


def font_frame(path):
    """(cap_height, descender) in font units. Cap height: OS/2 sCapHeight when
    declared, else the 'H' bbox top. Descender: the LOWEST point the font's
    descender glyphs (g j p q y) actually reach, not hhea.descent — measured
    2026-09-21 on LiberationMono: hhea says -615, 'g' reaches -400, and a single
    descent row spanning -615 left 'g' under the coverage threshold with row 7
    dark. Falls back to hhea when none of the probes exist."""
    f = TTFont(path); gs = f.getGlyphSet(); cmap = f.getBestCmap()
    from fontTools.pens.boundsPen import BoundsPen
    cap = getattr(f["OS/2"], "sCapHeight", 0) if "OS/2" in f else 0
    if not cap and ord("H") in cmap:
        bp = BoundsPen(gs); gs[cmap[ord("H")]].draw(bp)
        cap = bp.bounds[3]
    lows = []
    for ch in DESCENDER_PROBES:
        if ord(ch) in cmap:
            bp = BoundsPen(gs); gs[cmap[ord(ch)]].draw(bp)
            if bp.bounds:
                lows.append(bp.bounds[1])
    desc = min(lows) if lows else (f["hhea"].descent if "hhea" in f else -cap * 0.25)
    return float(cap), float(desc)


def matrix_glyph(path, ch, cols=5, rows=8, baseline=6, threshold=0.5, sub=4):
    """Rasterise one glyph of an outline font into column bytes in the
    display_types convention (bit r of column c = row r lit), or None when the
    font has no glyph for `ch` — the caller decides the fallback ('?' per the
    log, blank per MatrixDisplay.glyph today), not this function.

    A cell is lit when at least `threshold` of its sub x sub sample points are
    inside the winding (a COVERAGE threshold, not a centre sample — a thin
    stroke that misses every cell centre would otherwise vanish)."""
    f = TTFont(path); cmap = f.getBestCmap()
    if ord(ch) not in cmap:
        return None
    polys = contours(path, ch)
    if not polys:
        return [0] * cols                       # a space: present, nothing lit
    cap, desc = font_frame(path)
    xs = [p[0] for pl in polys for p in pl]
    x0, x1 = min(xs), max(xs)
    if x1 - x0 <= 0:
        return [0] * cols
    body = baseline + 1
    below = rows - body

    def font_y(cell_y):
        if cell_y <= body:
            return cap - cell_y / body * cap
        return (cell_y - body) / max(1, below) * desc

    out = [0] * cols
    for c in range(cols):
        for r in range(rows):
            hits = 0
            for i in range(sub):
                for j in range(sub):
                    fx = x0 + (c + (i + 0.5) / sub) / cols * (x1 - x0)
                    fy = font_y(r + (j + 0.5) / sub)
                    if _winding(fx, fy, polys) != 0:
                        hits += 1
            if hits >= threshold * sub * sub:
                out[c] |= 1 << r
    return out


def matrix_rows(colbytes, rows=8):
    """Column bytes -> row strings ('#' lit), the readable form _cols() authors in."""
    return ["".join("#" if b & (1 << r) else "." for b in colbytes) for r in range(rows)]
