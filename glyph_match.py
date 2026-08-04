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


def _ink_bbox_sw(pres):
    ys, xs = np.where(pres)
    if len(xs) == 0:
        return (0, 2, 0, 4), 0.2
    bb = (xs.min()/RES*2, xs.max()/RES*2, ys.min()/RES*4, ys.max()/RES*4)
    ym = (ys.min()+ys.max())//2
    runs = []; r = 0
    for v in pres[ym]:
        if v: r += 1
        elif r: runs.append(r); r = 0
    if r: runs.append(r)
    sw = (min(runs)/RES*2) if runs else 0.2
    return bb, max(0.12, sw*0.7)


def _seg_field(seg, bb, sw):
    x0, x1, y0, y1 = bb; ax, ay, bx, by = seg
    sax, say = x0+(x1-x0)*ax/2, y0+(y1-y0)*ay/4
    sbx, sby = x0+(x1-x0)*bx/2, y0+(y1-y0)*by/4
    dx, dy = sbx-sax, sby-say; L2 = dx*dx+dy*dy or 1e-9
    S = np.zeros((RES+1, RES+1), bool)
    for j in range(RES+1):
        py = j/RES*4.0
        for i in range(RES+1):
            px = i/RES*2.0
            t = max(0, min(1, ((px-sax)*dx+(py-say)*dy)/L2))
            if math.hypot(px-(sax+t*dx), py-(say+t*dy)) < sw:
                S[j, i] = True
    return S


def _phi(S, G):
    """⊕CONGRUENCE-MATCH: Matthews phi over the full 2x2 (seg{+,-} x ink{+,-}).
    Symmetric in both objects and both polarities; class-imbalance corrected."""
    a = np.sum(S & G); b = np.sum(S & ~G); c = np.sum(~S & G); d = np.sum(~S & ~G)
    den = math.sqrt((a+b)*(a+c)*(d+b)*(d+c))
    return (a*d - b*c)/den if den > 0 else 0.0


def match(pres, top=None, tau=None):
    """Score every 22-seg by congruence (phi) with the ink; return {seg: phi}, and the
    lit set (top-N strongest, or phi>tau). Match at the 22-JOIN; derez with
    segment_topology.project(lit, fmt)."""
    bb, sw = _ink_bbox_sw(pres)
    scores = {k: _phi(_seg_field(SEG[k], bb, sw), pres) for k in ST.SEG22}
    if top is not None:
        lit = set(sorted(ST.SEG22, key=lambda k: -scores[k])[:top])
    elif tau is not None:
        lit = {k for k, v in scores.items() if v > tau}
    else:
        lit = {k for k, v in scores.items() if v > 0}
    return scores, lit


def project_glyph(path, ch, kind="outline", top=None, tau=None):
    """Full pipeline: ingest by KIND -> presence grid -> congruence match @22."""
    G = (PF.raster_ink if kind == "bitmap" else PF.winding_ink)(path, ch)
    pres = ink_grid(G)
    return match(pres, top=top, tau=tau)


if __name__ == "__main__":
    LIB = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
    for ch in "OE8L":
        tbl = ST.DIGITS16 if ch.isdigit() else ST.LETTERS16
        G = PF.winding_ink(LIB, ch); pres = ink_grid(G)
        rg = region_graph(pres); st = strata(pres)
        _, lit = match(pres, top=len(tbl[ch].split()))
        print(f"{ch}: holes={rg['holes']} rim_frac={st['rim_frac']} "
              f"lit@22={sorted(lit)} derez@7={sorted(ST.project(lit,'7'))}")
