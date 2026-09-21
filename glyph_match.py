#!/usr/bin/env python3
# [RECONSTRUCTED from this session's own tool calls — later compacted session, not on-disk
#  transcript. Faithful to the create_file content (incl. the digit-table __main__ fix).
#  Verify before trusting as final.]
"""glyph_match.py — the font->segment projection matcher, REIFIED.

Sessions 78-83 developed this pipeline entirely in throwaway inline heredocs; the
design lived in COTYPE.md but the CODE evaporated each turn. This module is the single
auditable home for it. Shared geometry primitives come from segment_topology (no
re-derivation); ink ingest comes from project_font (winding/raster). Every layer above
ingest is COORDINATE-FREE.

Pipeline (⊕-symbols in COTYPE):
  ingest ink field  (project_font.winding_ink | raster_ink)          [by font KIND]
    -> region-adjacency graph   region_graph()                        ⊕REGION-GRAPH-MATCH
    -> graded strata core/mantle/rim   strata()                       ⊕STRATA-MANTLE
    -> congruence match per segment (Matthews phi, full 2x2)  match()  ⊕CONGRUENCE-MATCH
    -> derez via segment_topology.project() to any display            ⊕MATCH-AT-JOIN

Honest ceiling (COTYPE session 83): straight-segment templates vs ROUND glyph walls cap
phi at partial overlap; round-glyph margins stay slightly negative until curvature-aware
templates exist (⊕SEG-DOTPRODUCT-TEMPLATES). L (all-straight) already recovers 4/4.
"""
import math
import numpy as np
from scipy import ndimage
import segment_topology as ST
import project_font as PF

SEG = {k: ST.endpoints(k) for k in ST.SEG22}
RES = 64
# every char the authored 16-seg tables know — the log's "all 44" (:4644): 10
# digits, 26 letters, 8 symbols (two of which, ' ' and ':', are known blanks)
AUTHORED_CHARS = "".join(dict.fromkeys(list(ST.DIGITS16) + list(ST.LETTERS16) + list(ST.SYMBOLS16)))
# ⚑ PINNED BY NAME, NOT SMOOTHED (session 82). These score Jaccard 0 under every
# frame because the authored table follows DISPLAY convention and the face
# follows TYPE convention: '1' is b c on a display and centred in a font; the
# punctuation sits where a display centres it (g for '-', d for '_') and
# where a face sets it (x-height, below the baseline, high for '*' and "'").
# Under "stretch" a thin symbol's bbox becomes a slab; under "metrics" it lands
# where the face put it. An entry that starts scoring must LEAVE this set — the
# selftest refuses a pin that has been outgrown.
KNOWN_CONVENTION = frozenset("1-_='!")


def ink_grid(G, res=RES):
    """Sample a two-valued ink field to a boolean presence grid."""
    return np.array([[G(i/res*2.0, j/res*4.0) > 0 for i in range(res+1)]
                     for j in range(res+1)], dtype=bool)


def region_graph(pres):
    """⊕REGION-GRAPH-MATCH: presence/absence connected components; classify absence as
    enclosed HOLE (counter) vs BACKGROUND (touches outside = pure not-here). The hole
    count is Betti-1 — the shift/scale/rotation-invariant glyph identity."""
    holes = ndimage.binary_fill_holes(pres) & ~pres
    n_pres = ndimage.label(pres)[1]
    n_holes = ndimage.label(holes)[1]
    bg = ~ndimage.binary_fill_holes(pres)
    n_bg = ndimage.label(bg)[1]
    return dict(presence=n_pres, holes=n_holes, background=n_bg)


def strata(pres):
    """⊕STRATA-MANTLE: grade the presence region by distance-to-boundary into
    core (landlocked) / mantle (isthmus: borders core to coast) / rim (outer coast)."""
    core = ndimage.binary_erosion(pres, iterations=2)
    mantle = (ndimage.binary_dilation(core) & pres) & ~core
    rim = (pres & ~core) & ~mantle
    return dict(core=core, mantle=mantle, rim=rim,
                rim_frac=round(rim.sum()/max(1, pres.sum()), 3))


# Template half-width as a fraction of the measured stroke width. SOLVED by
# calibrate_projection on LiberationMono, 36 glyphs, 16-seg (session 75): the
# landscape is a plateau 0.70-1.00 (mean Jaccard 0.638-0.653), argmax 0.85; the
# old 0.7 was a guess that happened to sit on the plateau's edge.
SW_BAND = 0.85


def _min_run(row):
    runs = []; r = 0
    for v in row:
        if v: r += 1
        elif r: runs.append(r); r = 0
    if r: runs.append(r)
    return min(runs) if runs else None


def _ink_bbox_sw(pres, band=SW_BAND):
    """The ink's bbox in cell units and the template band half-width.

    ⚑ Stroke width is the MEDIAN over rows of each row's shortest run. It was
    the mid-row's shortest run, and the mid-row of H, A, 4, E, B is the
    CROSSBAR: H measured sw = 1.4 (the whole cell), every band covered
    everything, and all 22 phi collapsed toward 0 — that is why H lost its
    stems (⊕SEG-PROJECT-CALIBRATE, COTYPE session 75)."""
    ys, xs = np.where(pres)
    if len(xs) == 0:
        return (0, 2, 0, 4), 0.2
    bb = (xs.min()/RES*2, xs.max()/RES*2, ys.min()/RES*4, ys.max()/RES*4)
    mins = [m for m in (_min_run(pres[y]) for y in range(ys.min(), ys.max()+1)) if m]
    sw = (float(np.median(mins))/RES*2) if mins else 0.2
    return bb, max(0.12, sw*band)


_GX, _GY = np.meshgrid(np.arange(RES+1)/RES*2.0, np.arange(RES+1)/RES*4.0)


def _band(pts, sw):
    """Grid points within `sw` of the polyline `pts` — vectorised over the grid
    (the per-pixel Python loop it replaces pushed check_symbol --regressions to
    3m15 once the arc field arrived, past the gate's timeout; session 79)."""
    S = np.zeros((RES+1, RES+1), bool)
    for (qx, qy), (rx, ry) in zip(pts, pts[1:]):
        ex, ey = rx-qx, ry-qy; L2 = ex*ex+ey*ey or 1e-9
        t = np.clip(((_GX-qx)*ex + (_GY-qy)*ey)/L2, 0.0, 1.0)
        S |= np.hypot(_GX-(qx+t*ex), _GY-(qy+t*ey)) < sw
    return S


def _seg_field(seg, bb, sw):
    x0, x1, y0, y1 = bb; ax, ay, bx, by = seg
    sax, say = x0+(x1-x0)*ax/2, y0+(y1-y0)*ay/4
    sbx, sby = x0+(x1-x0)*bx/2, y0+(y1-y0)*by/4
    return _band([(sax, say), (sbx, sby)], sw)


# ⊕SEG-DOTPRODUCT-TEMPLATES (session 79): which of the 22 may BOW. The outer
# horizontals and the side verticals are the strokes a round glyph's bowl
# replaces with an arc; the centre bars, the centre verticals and the diagonals
# have no bowl to follow and stay straight at every sagitta.
ARC_SEGS = frozenset({"a1", "a2", "d1", "d2", "b", "c", "e", "f"})
ARC_N = 16


def _arc_field(seg, bb, sw, sagitta):
    """The band of `seg` bent to an arc bowing OUTWARD (away from the cell's
    centre) by `sagitta` x the segment's length; sagitta 0 is exactly the
    straight band. The arc is a quadratic Bezier through the chord's ends whose
    apex sits at the sagitta, sampled to a polyline of ARC_N pieces; a point is
    in the field when it lies within `sw` of any piece."""
    if sagitta == 0:
        return _seg_field(seg, bb, sw)
    x0, x1, y0, y1 = bb; ax, ay, bx, by = seg
    sax, say = x0+(x1-x0)*ax/2, y0+(y1-y0)*ay/4
    sbx, sby = x0+(x1-x0)*bx/2, y0+(y1-y0)*by/4
    dx, dy = sbx-sax, sby-say; L = math.hypot(dx, dy) or 1e-9
    nx, ny = -dy/L, dx/L
    mx, my = (sax+sbx)/2, (say+sby)/2
    cx, cy = (x0+x1)/2, (y0+y1)/2
    if (mx-cx)*nx + (my-cy)*ny < 0:          # make the normal point away from the centre
        nx, ny = -nx, -ny
    s = sagitta * L
    px_, py_ = mx + 2*s*nx, my + 2*s*ny     # Bezier control: apex lands at s
    pts = [((1-t)**2*sax + 2*(1-t)*t*px_ + t*t*sbx,
            (1-t)**2*say + 2*(1-t)*t*py_ + t*t*sby) for t in (i/ARC_N for i in range(ARC_N+1))]
    return _band(pts, sw)


def _phi(S, G):
    """⊕CONGRUENCE-MATCH: Matthews phi over the full 2x2 (seg{+,-} x ink{+,-}).
    Symmetric in both objects and both polarities; class-imbalance corrected."""
    a = np.sum(S & G); b = np.sum(S & ~G); c = np.sum(~S & G); d = np.sum(~S & ~G)
    den = math.sqrt((a+b)*(a+c)*(d+b)*(d+c))
    return (a*d - b*c)/den if den > 0 else 0.0


# The arc bow of ARC_SEGS as a fraction of segment length, NEGATIVE = inward.
# SOLVED by calibrate_projection --arcs (session 79, LiberationMono, 36, 16-seg):
# plateau -0.05..-0.15 (0.668-0.672, 10/36 exact), argmax -0.15; 0 scores
# 0.653; every outward value is worse. Per class at -0.15: round 0.60 -> 0.62
# (the first exact round glyph), straight 0.77 -> 0.79, diagonal 0.67 -> 0.68.
SAGITTA = -0.15


def match(pres, top=None, tau=None, band=SW_BAND, sagitta=SAGITTA):
    """Score every 22-seg by congruence (phi) with the ink; return {seg: phi}, and the
    lit set (top-N strongest, or phi>tau). Match at the 22-JOIN; derez with
    segment_topology.project(lit, fmt). `band` is the template half-width as a
    fraction of the measured stroke width (calibrate_projection solves it)."""
    # ⚑ The template is laid out in the CELL, not the ink's bbox. Under the
    # anisotropic ("stretch") ingest the two coincide; under the aspect-preserving
    # frame the ink of a narrow glyph does not fill the cell, and stretching the
    # template into its bbox would put the frame defect back.
    _bb, sw = _ink_bbox_sw(pres, band)
    cell = (0.0, 2.0, 0.0, 4.0)
    scores = {k: _phi(_arc_field(SEG[k], cell, sw, sagitta if k in ARC_SEGS else 0.0), pres)
              for k in ST.SEG22}
    if top is not None:
        lit = set(sorted(ST.SEG22, key=lambda k: -scores[k])[:top])
    elif tau is not None:
        lit = {k for k, v in scores.items() if v > tau}
    else:
        lit = {k for k, v in scores.items() if v > 0}
    return scores, lit


def _ingest(path, ch, kind, frame):
    if kind == "bitmap":
        return PF.raster_ink(path, ch)
    return PF.winding_ink(path, ch, frame=frame)


def project_glyph(path, ch, kind="outline", top=None, tau=None, frame="stretch"):
    """Full pipeline: ingest by KIND -> presence grid -> congruence match @22."""
    pres = ink_grid(_ingest(path, ch, kind, frame))
    return match(pres, top=top, tau=tau)


def validate_projection(path, chars=None, fmt="16", kind="outline", frame="stretch",
                        band=SW_BAND, sagitta=SAGITTA):
    """⊕SEG-TABLE-VALIDATE: cross-check the PROJECTION against the AUTHORED table,
    per glyph, and REPORT — a routine, not a comment (the first witness for this
    symbol matched the word "cross-check" in a docstring; session 69).

    For each glyph: project the font's ink at the 22-join with top-N = the
    authored segment count (so the comparison is of WHICH segments, not how
    many), derez to `fmt`, and compare to segment_topology's authored set.
    Returns [(ch, authored, projected, hits, misses, extras, jaccard)] sorted by
    agreement. No threshold is applied here: the honest ceiling is partial
    (round glyph walls vs straight templates, session 83) and the number that
    would make this a gate is ⊕SEG-PROJECT-CALIBRATE's to solve, not this
    routine's to assume."""
    if chars is None:
        chars = AUTHORED_CHARS
    rows = []
    for ch in chars:
        authored = set(ST.project(ST.glyph16(ch), fmt))
        if not authored:
            continue          # a KNOWN blank (' ', ':') has nothing to agree with
        pres = ink_grid(_ingest(path, ch, kind, frame))
        _scores, lit22 = match(pres, top=len(ST.glyph16(ch)), band=band, sagitta=sagitta)
        projected = set(ST.project(lit22, fmt))
        hits = authored & projected
        union = authored | projected
        rows.append((ch, authored, projected, hits, authored - projected,
                     projected - authored, len(hits) / len(union) if union else 1.0))
    return sorted(rows, key=lambda r: -r[6])


BAND_GRID = (0.4, 0.5, 0.6, 0.7, 0.85, 1.0, 1.2)
FRAMES = ("stretch", "fit", "metrics")


# negative = INWARD (toward the cell centre). Outward was the first guess and
# is monotonically worse (session 79): a bowl sits inside the stretched cell's
# corners, so the outer strokes must bow in, not out.
SAGITTA_GRID = (-0.2, -0.15, -0.1, -0.075, -0.05, -0.025, 0.0, 0.05, 0.1, 0.2)


def calibrate_projection(path, chars=None, fmt="16", kind="outline",
                         bands=BAND_GRID, frames=FRAMES, sagittas=(SAGITTA,)):
    """⊕SEG-PROJECT-CALIBRATE: solve the matcher's free parameters — the ingest
    frame, the template band fraction and (⊕SEG-DOTPRODUCT-TEMPLATES) the arc
    sagitta — by mean Jaccard against the authored table over the whole glyph
    set. Returns (params, mean_jaccard, table) where params = {"frame", "band",
    "sagitta"} and table = {(frame, band, sagitta): (mean, exact, n)} is the
    full sweep, so the reader sees the landscape, not just the argmax.

    ⚑ What it does NOT solve: top-N is the authored count (the comparison is of
    WHICH segments, so it cannot be free). A calibrated number is the best THIS
    matcher can do, not a proof that it is right."""
    table = {}
    for frame in frames:
        for band in bands:
            for sag in sagittas:
                rows = validate_projection(path, chars, fmt=fmt, kind=kind, frame=frame,
                                           band=band, sagitta=sag)
                table[(frame, band, sag)] = agreement_summary(rows)
    best = max(table, key=lambda k: (table[k][0], table[k][1]))
    return {"frame": best[0], "band": best[1], "sagitta": best[2]}, table[best][0], table


CLASS_CURVE = 0.35      # curve length fraction above which a glyph is "round"
CLASS_DIAG = 0.20       # diagonal length fraction above which it is "diagonal"
CLASS_NARROW = 0.40     # bbox width/height below which it is "narrow"


def glyph_class(path, ch):
    """One of "narrow" | "round" | "diagonal" | "straight", read from the ink's
    outline (make_glyph_ink.outline_stats), in that precedence — so a narrow
    round glyph is narrow (its frame is the problem before its walls are)."""
    import make_glyph_ink as GI
    st = GI.outline_stats(path, ch)
    if not st or not st["bbox"]:
        return "unknown"
    x0, x1, y0, y1 = st["bbox"]
    total = st["straight"] + st["diagonal"] + st["curve"] or 1.0
    if (x1 - x0) / max(1.0, (y1 - y0)) < CLASS_NARROW:
        return "narrow"
    if st["curve"] / total > CLASS_CURVE:
        return "round"
    if st["diagonal"] / total > CLASS_DIAG:
        return "diagonal"
    return "straight"


def agreement_by_class(path, rows):
    """{class: (mean jaccard, exact, n, chars)} over validate_projection rows —
    the ceiling as a NUMBER PER CLASS, which is what decides whether a template
    change helped the class it was aimed at rather than the mean."""
    groups = {}
    for r in rows:
        groups.setdefault(glyph_class(path, r[0]), []).append(r)
    out = {}
    for k, rs in groups.items():
        m, e, n = agreement_summary(rs)
        out[k] = (m, e, n, "".join(r[0] for r in rs))
    return out


def agreement_summary(rows):
    """(mean jaccard, exact count, n) over validate_projection rows."""
    if not rows:
        return 0.0, 0, 0
    exact = sum(1 for r in rows if not r[4] and not r[5])
    return sum(r[6] for r in rows) / len(rows), exact, len(rows)


if __name__ == "__main__":
    LIB = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    for ch in "OE8L":
        tbl = ST.DIGITS16 if ch.isdigit() else ST.LETTERS16
        G = PF.winding_ink(LIB, ch); pres = ink_grid(G)
        rg = region_graph(pres); st = strata(pres)
        _, lit = match(pres, top=len(tbl[ch].split()))
        print(f"{ch}: holes={rg['holes']} rim_frac={st['rim_frac']} "
              f"lit@22={sorted(lit)} derez@7={sorted(ST.project(lit,'7'))}")
