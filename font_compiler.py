#!/usr/bin/env python3
"""font_compiler.py — an arbitrary TTF, compiled ONCE into the segment-display table (W30).

A font goes in, a deterministic JSON document comes out: {ch: sorted 22-seg ids},
keyed on the font file's sha256 and on a METHOD FINGERPRINT (the parameters plus
the sha256 of every source file the method reads), cached under .font-cache/. A
W61-style build key cuts off on those two hashes: same font bytes + same method
bytes = same table, no rerun. Coarser formats are segment_topology.project() of
the 22 set, never a second compiler.

⚑ SEGMENT-ONLY (operator, 2026-09-23). The dot-matrix half was DROPPED: W54 puts
plain Unifont behind the marquee's aperture and wants no compiled column table,
so display_types.font_extension / check_matrix_input are untouched by W30.

⚑ THE METHOD: THE STROKE SKELETON, MAPPED TO SEGMENT PATHS.  The authored tables
were designed for a segment display, not traced from a typeface, so the question
a compiler must answer is structural — WHICH segment paths does the glyph's
centreline traverse — not how much ink overlaps a template. So:

  1. rasterise the outline by nonzero winding on an ISOTROPIC grid in font units
     (a skeleton of an anisotropically squeezed glyph bends its diagonals);
  2. thin it to a one-pixel centreline (Zhang-Suen) and prune terminal
     whiskers shorter than SPUR_SW stroke widths (thinning's corner spurs);
  3. read the centreline as a GRAPH: ends and junctions are nodes (a junction
     is where THREE RUNS meet — a staircase diagonal's 3-neighbour pixels are
     not junctions), the ordered pixel runs between them are strokes; a
     node-free component is a closed loop, one smaller than DOT_EXTENT a dot;
  4. map into the lattice as a CENTRELINE frame (every frame line inset by half
     a stroke): cap -> 0, baseline -> 4, descent -> 6; lowercase ascender -> 0,
     x-height -> 2 (segment_topology.LETTERS22's convention); x spans the
     centreline of a wide glyph, the font's cell for a narrow one;
  5. MAP-MATCH every stroke onto the lattice: snap its ends to the nearest
     lattice nodes, carry the stroke onto them (_pin), and take the lattice
     walk between them that DYNAMIC TIME WARPING aligns most closely with the
     ordered stroke (_match) — the stroke is a GPS trace, the lattice the road
     network. A walk traverses whole segments, so the answer is a PATH;
  6. a dot lights the nearest dot segment (p1/p2) in reach.

⚑ THE DIGIT RULE.  The digit table IS the 7-segment digit set (DIGITS16 is
pinned from arXiv 1009.4977 Table 1 and every surface that shows digits —
clock, splash, wallpaper — is 7-seg): a digit is matched on the 7-seg
sub-lattice (FORMATS["7"]["mask"]: no diagonals, no centre verticals) and its
coarse bars light both halves (the merge map read backwards). Measured, it
takes '3' (whose short middle tongue lit only g2) and '8' (whose waist the
full lattice read through the diagonals) to their authored sets.

⚑ ITS KNOBS, AND THEIR WEAKNESS, STATED.  TURN (a diagonal segment stands for a
straight diagonal STROKE: a stroke point pays TURN x |sin| of its angle to a
diagonal sample; orthogonal samples pay none, because the display draws a bowl
with its orthogonal bars) and SPUR_SW were CHOSEN on ONE font, Liberation Mono
(2026-09-23): TURN 0 lets bowls cut through k/h ('R' 'S'), 0.6 pushed the
straight diagonal of 'M' onto j + a2; 0.3 holds both. Snapping is nearest-node,
so a junction between lattice rows ('e''s crossbar at half x-height) is decided
by which side of the midline it falls. And a display convention the face does
not share ('B' told from '8' by a centre spine, '1' on the right-hand stems) is
not in the ink at all: those are DECLARED per glyph in DECLARED, with the
reason, and the policy (policy/font_compiler.rego) admits a declared glyph only
while it still disagrees — an outgrown declaration is denied.

⚑ RESIDUE — WHAT WAS TRIED AND LOST, measured 22-seg exact of 72 on Liberation Mono:
  template match, one global phi tau (glyph_match.match, W30's first cut)   1
  skeleton, nearest-node snap + chamfer over enumerated simple paths       36
    (paths capped at 6 segments: a rectangle 'O' loop needs 8)
  per-segment COVERAGE of the centreline (no path at all)                  14
    (a round bowl never runs alongside half a bar: 'o' lit only c)
  DTW, open-ended (walk may start/end at any node)                         37
    (a stroke's end then skips its first half-bar cheaply: g1 lost in n h m)
  DTW, snapped ends, no TURN                                               39
  + the digit rule, TURN 0.6, the ascender frame, DOT_REACH 1.0            42
  + SPUR_SW 0.6 ('t'), TURN 0.3 ('M' 'z')                                  45

    font_compiler.py [--font F] --show           # n of m, the key
    font_compiler.py [--font F] --emit OUT.json  # the compiled document, deterministic bytes
    font_compiler.py [--font F] --key            # font sha256 + method fingerprint
    font_compiler.py [--font F] --glyph CH       # one glyph: strokes, snapped ends, chosen paths
    font_compiler.py [--font F] --diff           # every authored glyph: compiled vs authored
    font_compiler.py --selftest

SKIP (printed, exit 0) when no TTF is found and none is given.
"""
import hashlib
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(ROOT, ".font-cache")
FORMAT = 2
SEG_CHARSET = "".join(chr(c) for c in range(0x20, 0x7F))

# every file the compiled bytes are a function of, besides the font itself
METHOD_SOURCES = ("font_compiler.py", "make_glyph_ink.py", "segment_topology.py")

# ── the method's geometry (all in lattice units unless named px) ──────────────
PX = 16.0            # font units per raster pixel (Liberation Mono stem ~ 11 px)
SPUR_SW = 0.6        # a terminal stroke shorter than this x stroke width is a whisker
                     # (1.0 pruned the left arm of 't', which is one stem long)
DOT_EXTENT = 0.8     # a component whose lattice bbox is smaller than this is a dot
DOT_REACH = 1.0     # ... and lights the dot segment within this distance: half the
                     # p1-p2 spacing, i.e. the NEAREST dot segment in its column
SAMPLE = 0.1         # lattice sampling pitch
TURN = 0.3           # diagonal samples: cost per unit |sin| of stroke-vs-diagonal angle
WIDE = 0.45          # a glyph at least this fraction of the cell wide fills it
PARAMS = {"px": PX, "spur_sw": SPUR_SW, "dot_extent": DOT_EXTENT, "dot_reach": DOT_REACH,
          "sample": SAMPLE, "turn": TURN, "wide": WIDE, "digit_rule": "7-seg sub-lattice + merge closure",
          "charset": SEG_CHARSET}

# ⚑ DECLARED DISPLAY CONVENTIONS — per glyph, the side that is RIGHT when the
# compiled (face) reading and the authored (display) set disagree, with the
# reason. The policy (policy/font_compiler.rego) admits a declared disagreement,
# DENIES an undeclared one, and DENIES a declaration the compiler has OUTGROWN
# (compiled == authored at 22): a convention that stops disagreeing must leave.
#
# The classes, each a STRUCTURAL reason rather than a verdict of taste:
#   display       the uppercase / digit / symbol tables are PINNED FROM FETCHED
#                 REFERENCES (segment_topology: arXiv 1009.4977 Table 1, the fandom
#                 16-seg tables); where the face draws the glyph differently the
#                 reference is the display's convention and wins. The seed set is
#                 glyph_match.KNOWN_CONVENTION ('1' - _ = ' !) — of which '_' is no
#                 longer declared: the skeleton compiler REPRODUCES it (d1 d2).
#   mid-x-height  the 22-seg lowercase body is ONE lattice row (x-height g .. baseline
#                 d); a face feature at half x-height (a crossbar, a crossing, a
#                 junction) has no segment, and the display encodes it by a
#                 convention the ink does not contain.
#   descender     the descender sub-cell holds only the verticals dl dc dr: a tail
#                 that CURLS has no bar to run along.
#   lattice       the face's stroke needs a segment the 22-lattice does not have.
DECLARED = {
    "!": ("display", "the face sets '!' as a stem over a detached baseline dot; the display "
                     "draws the whole centre column j m (there is no baseline dot segment)"),
    "'": ("display", "the face's apostrophe is a short centre tick (j); the display sets it "
                     "on the upper-left stem f"),
    "-": ("display", "the face's hyphen is shorter than DOT_EXTENT and reads as a dot (p2); "
                     "the display's hyphen is the whole middle bar g1 g2"),
    "=": ("display", "the face's bars sit at 0.28 and 0.72 of cap height, both nearest the "
                     "middle row; the display draws '=' on the middle and baseline bars"),
    "1": ("display", "the face's '1' is a centre stem with flag and foot; the 7-segment '1' "
                     "is the right-hand stems b c"),
    "4": ("display", "the face closes the top of '4' with a diagonal, which on the 7-seg digit "
                     "lattice reads as the top bar a; the 7-segment '4' is open-topped (f g b c)"),
    "7": ("display", "the face's '7' stem is a diagonal to the bottom centre, which on the 7-seg "
                     "lattice routes down c and back along d and g; the 7-segment '7' is a b c"),
    "*": ("display", "the face's asterisk is a small six-armed star raised into the top half "
                     "(a1 a2 b f); the display's is the full-cell eight-armed starburst"),
    "?": ("display", "the face draws a hook over a detached baseline dot; the display runs the "
                     "hook into the centre stem m (there is no baseline dot segment)"),
    "B": ("display", "the display draws B as a D with a waist (spine j m, g2) so that B is not "
                     "8; the face's B is a stem and two bowls"),
    "D": ("display", "the display draws D with a centre spine (j m) so that D is not O or 0; "
                     "the face's D is a stem and a bowl (e f)"),
    "J": ("display", "the face's J carries a top bar (a2); the display's J is the bare hook "
                     "with its left stem e"),
    "Q": ("display", "the face's Q tail drops below the baseline (dr); the display keeps the "
                     "tail inside the cell as the diagonal l"),
    "V": ("display", "the face's V arms run corner to bottom centre, a full-height diagonal the "
                     "lattice lacks (its diagonals are half-height); the display's V is the "
                     "reference table's e f i k"),
    "W": ("display", "the face's W is four near-vertical strokes meeting in two feet (d1 d2) "
                     "under a centre apex (m); the display's W is the side stems with the "
                     "lower diagonals i l"),
    # i and l are NOT declared: the operator adopted the face's letterforms into
    # LETTERS22 (2026-09-25, "The compiled version is better"), so the compiler now
    # REPRODUCES them — and F5 would deny a declaration the compiler has outgrown.
    "a": ("mid-x-height", "the face's bowl top sits at half x-height; the compiler reads the "
                          "bowl's upper wall as the diagonal i, the display as the centre stem m"),
    "e": ("mid-x-height", "the face's crossbar sits at half x-height, so the bowl's junction snaps "
                          "to the x-height and the left wall e is lost; the display marks the "
                          "crossbar with the diagonal l"),
    "k": ("mid-x-height", "the face's arm and leg meet the stem at half x-height; the compiler "
                          "reads the arm as g2 + i, the display draws g1 l"),
    "s": ("mid-x-height", "the face's spine crosses half x-height; the compiler reads the two "
                          "bowls as bars with no spine, the display draws the spine as i"),
    "w": ("mid-x-height", "the face's inner apex rises to half x-height; the compiler reads the "
                          "inner left stroke as the diagonal i, the display as the baseline half d1"),
    "x": ("mid-x-height", "the face's arms cross at half x-height, below the lattice's only "
                          "crossing (1,2); the display uses i l n1"),
    "v": ("lattice", "the face's right arm runs from (2,2) to the bottom centre, the mirror of "
                     "n1, which the lattice does not have; the compiler reaches the vertex by "
                     "c then d2, the display draws the arm as c alone"),
    "g": ("descender", "the face's tail curls left below the baseline and reads as dl, which "
                       "makes g IDENTICAL to p; the authored dr dc is what keeps g distinct "
                       "(segment_topology's own no-collision selftest)"),
    "j": ("descender", "the face's hook curls left below the baseline (the compiler routes it "
                       "back along d1 d2 to dl) and its tittle sits over the right-hand stem, "
                       "not on the centre dot p1"),
    "y": ("descender", "the face's tail is a diagonal falling left through the baseline "
                       "(n1 into dl); the display's y is a u with a centre descender dc"),
}
DECLARED_CLASSES = ("display", "mid-x-height", "descender", "lattice")


def font_sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def method_fingerprint(half, params):
    """sha256 over the half's parameters and the bytes of every METHOD_SOURCES file."""
    h = hashlib.sha256(json.dumps({"format": FORMAT, "half": half, "params": params},
                                  sort_keys=True).encode())
    for rel in METHOD_SOURCES:
        with open(os.path.join(ROOT, rel), "rb") as f:
            h.update(rel.encode() + b"\0" + hashlib.sha256(f.read()).digest())
    return h.hexdigest()


# ── 1. raster ────────────────────────────────────────────────────────────────

def _raster(polys, px=PX):
    """Nonzero-winding raster of font-unit polylines on an isotropic grid.
    Returns (mask[row, col], x_of_col, y_of_row) with row 0 at the TOP."""
    import numpy as np
    xs = [p[0] for pl in polys for p in pl]; ys = [p[1] for pl in polys for p in pl]
    x0, x1 = min(xs) - 2 * px, max(xs) + 2 * px
    y0, y1 = min(ys) - 2 * px, max(ys) + 2 * px
    cx = np.arange(x0, x1, px) + px / 2
    cy = np.arange(y1, y0, -px) - px / 2
    X, Y = np.meshgrid(cx, cy)
    w = np.zeros(X.shape, dtype=np.int32)
    for pl in polys:
        for (ax, ay), (bx, by) in zip(pl, pl[1:]):
            if ay == by:
                continue
            up = (ay <= Y) & (by > Y)
            dn = (by <= Y) & (ay > Y)
            cross = (bx - ax) * (Y - ay) - (X - ax) * (by - ay)
            w += (up & (cross > 0)).astype(np.int32)
            w -= (dn & (cross < 0)).astype(np.int32)
    return w != 0, cx, cy


# ── 2. thin ──────────────────────────────────────────────────────────────────

def _thin(mask):
    """Zhang-Suen thinning, vectorised: a one-pixel, 8-connected centreline."""
    import numpy as np
    img = np.pad(mask.astype(np.uint8), 1)
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            P = np.pad(img, 1)
            p2, p3, p4 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:]
            p5, p6, p7 = P[2:, 2:], P[2:, 1:-1], P[2:, :-2]
            p8, p9 = P[1:-1, :-2], P[:-2, :-2]
            ring = [p2, p3, p4, p5, p6, p7, p8, p9, p2]
            B = sum(r.astype(np.int32) for r in ring[:-1])
            A = sum(((ring[i] == 0) & (ring[i + 1] == 1)).astype(np.int32) for i in range(8))
            if step == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            m = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if m.any():
                img[m] = 0
                changed = True
    return img[1:-1, 1:-1].astype(bool)


def _kinds(skel):
    """(ends, junctions) of a thinned skeleton.

    ⚑ A JUNCTION IS WHERE THREE RUNS MEET, not a pixel with three neighbours: a
    staircase diagonal has plain path pixels with three 8-neighbours, and
    counting neighbours cut every diagonal into a dozen 'junctions'. So a
    candidate cluster (pixels of >= 3 neighbours) is KEPT only when removing
    it leaves >= 3 distinct runs touching it. An end is a pixel of one
    neighbour, or of two ADJACENT neighbours (a thinned end's last corner)."""
    import numpy as np
    from scipy import ndimage
    P = np.pad(skel.astype(np.int8), 1)
    ring = [P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:], P[2:, 2:],
            P[2:, 1:-1], P[2:, :-2], P[1:-1, :-2], P[:-2, :-2]]
    cn = sum(((ring[i] == 0) & (ring[(i + 1) % 8] == 1)).astype(np.int32) for i in range(8))
    nb = sum(r.astype(np.int32) for r in ring)
    ends = skel & ((nb == 1) | ((nb == 2) & (cn == 1)))
    cand = skel & (nb >= 3)
    S8 = np.ones((3, 3))
    clab, n = ndimage.label(cand, structure=S8)
    runs, _nr = ndimage.label(skel & ~cand, structure=S8)
    junct = np.zeros_like(skel)
    for c in range(1, n + 1):
        cl = clab == c
        ring_px = ndimage.binary_dilation(cl, structure=S8) & ~cl
        if len(set(np.unique(runs[ring_px])) - {0}) >= 3:
            junct |= cl
    return ends & ~junct, junct


def _order(pix):
    """The pixels of one thinned run as a walk from one end to the other (a
    closed run: from an arbitrary pixel around), stepping to an unvisited
    neighbour and preferring the 4-connected one (a staircase's corner)."""
    S = set(map(tuple, pix))
    nb = {p: [(p[0] + dr, p[1] + dc) for dr in (-1, 0, 1) for dc in (-1, 0, 1)
              if (dr or dc) and (p[0] + dr, p[1] + dc) in S] for p in S}
    start = min(S, key=lambda p: (len(nb[p]), p))
    walk, seen = [start], {start}
    while True:
        cur = walk[-1]
        nxt = sorted((q for q in nb[cur] if q not in seen),
                     key=lambda q: (abs(q[0] - cur[0]) + abs(q[1] - cur[1]), q))
        if not nxt:
            break
        walk.append(nxt[0]); seen.add(nxt[0])
    return walk


def _graph(skel):
    """(nodes, strokes): nodes = [(row, col) centroid] of endpoint/junction pixel
    clusters; strokes = [(ordered pixels, start node | None, end node | None)] —
    the runs between them, each ORIENTED from the node its first pixel touches.
    A component with no node pixel is ONE stroke with no nodes (a closed loop)."""
    import numpy as np
    from scipy import ndimage
    S8 = np.ones((3, 3))
    ends, junct = _kinds(skel)
    nodepx = ends | junct
    nlab, nn = ndimage.label(nodepx, structure=S8)
    nodes = [tuple(float(v) for v in c) for c in ndimage.center_of_mass(nodepx, nlab, range(1, nn + 1))]
    elab, ne = ndimage.label(skel & ~nodepx, structure=S8)
    H, W = skel.shape

    def touching(p):
        return sorted({int(nlab[r, c]) - 1 for r in range(max(0, p[0] - 1), min(H, p[0] + 2))
                       for c in range(max(0, p[1] - 1), min(W, p[1] + 2)) if nlab[r, c]})
    strokes = []
    for e in range(1, ne + 1):
        walk = _order(np.argwhere(elab == e))
        a, b = touching(walk[0]), touching(walk[-1])
        if not a and not b:
            strokes.append((walk, None, None))
            continue
        if not a:
            walk.reverse(); a, b = b, a
        u = a[0]
        v = next((n for n in b if n != u), b[0] if b else u)
        strokes.append((walk, u, v))
    # two node clusters adjacent with no run between them: a zero-length stroke
    for a in range(nn):
        ring = ndimage.binary_dilation(nlab == a + 1, structure=S8)
        for b in set(int(v) - 1 for v in np.unique(nlab[ring]) if v) - {a}:
            if a < b:
                strokes.append(([], a, b))
    return nodes, strokes


def _prune(skel, sw):
    """Drop terminal whiskers shorter than SPUR_SW x the stroke width, re-reading
    the graph after each round (a pruned whisker turns its junction into a bend)."""
    import numpy as np
    from scipy import ndimage
    for _ in range(4):
        ends, junct = _kinds(skel)
        runs = skel & ~junct
        lab, n = ndimage.label(runs, structure=np.ones((3, 3)))
        cut = False
        for e in range(1, n + 1):
            pix = lab == e
            if not (pix & ends).any():
                continue
            ring = ndimage.binary_dilation(pix, structure=np.ones((3, 3)))
            if not (ring & junct).any():
                continue                      # an isolated run: a stroke, not a whisker
            if pix.sum() < SPUR_SW * sw:
                skel = skel & ~pix
                cut = True
        if not cut:
            break
    return skel


# ── 4. the lattice ───────────────────────────────────────────────────────────

def _lattice(mask=None):
    """(nodes, edges): the 22-seg lattice as a graph — node (x, y) per segment
    end, edge per non-degenerate segment; the dot segments (p1 p2) separately.
    `mask` restricts it to a format's segments (segment_topology.FORMATS)."""
    import segment_topology as ST
    edges, dots = {}, {}
    for k in ST.SEG22:
        if mask is not None and k not in mask:
            continue
        ax, ay, bx, by = ST.endpoints(k)
        if (ax, ay) == (bx, by):
            dots[k] = (float(ax), float(ay))
        else:
            edges[k] = ((float(ax), float(ay)), (float(bx), float(by)))
    nodes = sorted({p for e in edges.values() for p in e})
    return nodes, edges, dots


_SG = {}


def _sample_graph(mask=None):
    """The lattice as a DIRECTED SAMPLE GRAPH: one sample per lattice node, and
    each segment walked both ways as a chain of interior samples SAMPLE apart.
    Returns (coords[S, 2], seg[S] (None at a node), src[E], dst[E], node index).
    A walk that enters a segment's chain must leave by its far node, so a walk
    between nodes traverses whole segments — the lattice's own granularity."""
    import numpy as np
    key = frozenset(mask) if mask is not None else None
    if key not in _SG:
        nodes, edges, _dots = _lattice(mask)
        idx = {n: i for i, n in enumerate(nodes)}
        coords, seg, src, dst = [list(n) for n in nodes], [None] * len(nodes), [], []
        for k, (a, b) in sorted(edges.items()):
            for u, v in ((a, b), (b, a)):
                m = max(2, int(round(math.hypot(v[0] - u[0], v[1] - u[1]) / SAMPLE)))
                prev = idx[u]
                for j in range(1, m):
                    t = j / m
                    coords.append([u[0] + (v[0] - u[0]) * t, u[1] + (v[1] - u[1]) * t])
                    seg.append(k)
                    src.append(prev); dst.append(len(coords) - 1); prev = len(coords) - 1
                src.append(prev); dst.append(idx[v])
        dirs = np.zeros((len(coords), 2))
        for j, k in enumerate(seg):
            if k is not None:
                (ax, ay), (bx, by) = edges[k]
                L = math.hypot(bx - ax, by - ay)
                dirs[j] = ((bx - ax) / L, (by - ay) / L)
        _SG[key] = (np.array(coords), seg, np.array(src), np.array(dst), idx, dirs)
    return _SG[key]


def _tangents(P, w=3):
    """Unit tangent at each point of an ordered stroke, over +-w points."""
    import numpy as np
    n = len(P)
    T = np.array([P[min(n - 1, i + w)] - P[max(0, i - w)] for i in range(n)], float)
    L = np.hypot(T[:, 0], T[:, 1]); L[L == 0] = 1.0
    return T / L[:, None]


def _match(P, u=None, v=None, mask=None):
    """DYNAMIC TIME WARPING of the ordered stroke P against every lattice walk
    from node u to node v: the walk whose samples, aligned monotonically with
    the stroke's points, lie closest in total. Returns (sorted segment ids,
    mean cost, (start node, end node)). This is map-matching — the stroke is a
    GPS trace, the lattice the road network — and it is STRUCTURAL: the answer
    is a path, and a segment is lit only when the centreline runs its whole
    length.

    u / v: a node, a list of admissible nodes, or None (any node).

    The point cost is the distance to the sample plus, on a DIAGONAL segment
    only, TURN x |sin| of the angle between the stroke's tangent and the
    diagonal: a diagonal segment stands for a diagonal STROKE, and a bowl
    curving past one is still a bowl — which the display draws with its
    orthogonal bars (an 'O' is a rectangle), so orthogonal samples pay none."""
    import numpy as np
    C, seg, src, dst, idx, dirs = _sample_graph(mask)
    S = len(C); n = len(P); INF = float("inf")
    node_ix = sorted(idx.values())

    def ixs(x):
        if x is None:
            return node_ix
        return [idx[x]] if isinstance(x, tuple) else sorted(idx[q] for q in x)
    u_ix, v_ix = ixs(u), ixs(v)
    D = np.full((n, S), INF)
    # distance, plus TURN x |sin| between the stroke's tangent and the
    # segment's direction: a horizontal bar lying NEAR a vertical segment is
    # not that segment (node samples carry no direction and pay none)
    tan = _tangents(P)
    diag =(np.abs(dirs[:, 0]) > 1e-9) & (np.abs(dirs[:, 1]) > 1e-9)
    w = np.where(diag, TURN, 0.0)
    cost = [np.hypot(C[:, 0] - p[0], C[:, 1] - p[1])
            + w * np.abs(dirs[:, 0] * t[1] - dirs[:, 1] * t[0]) for p, t in zip(P, tan)]

    def relax(row, c):
        while True:
            new = row.copy()
            np.minimum.at(new, dst, row[src] + c[dst])
            if not (new < row).any():
                return row
            row = new
    for i in range(n):
        c = cost[i]
        if i == 0:
            base = np.full(S, INF)
            for q in u_ix:
                base[q] = c[q]
        else:
            prev = D[i - 1]
            both = np.full(S, INF); np.minimum.at(both, dst, prev[src])
            base = np.minimum(prev, both) + c
        D[i] = relax(base, c)
    # backtrack: which samples did the optimal alignment visit
    preds = {}
    for a, b in zip(src.tolist(), dst.tolist()):
        preds.setdefault(b, []).append(a)
    end = min(v_ix, key=lambda q: (D[n - 1, q], q))
    starts = set(u_ix)
    i, s, lit = n - 1, end, set()
    for _ in range(n * S):
        if seg[s] is not None:
            lit.add(seg[s])
        if i == 0 and s in starts and math.isclose(D[0, s], cost[0][s], abs_tol=1e-9):
            break
        here = D[i, s] - cost[i][s]
        if i > 0 and math.isclose(here, D[i - 1, s], abs_tol=1e-9):
            i -= 1; continue
        step = None
        if i > 0:
            step = next((q for q in preds.get(s, []) if math.isclose(here, D[i - 1, q], abs_tol=1e-9)), None)
            if step is not None:
                i -= 1; s = step; continue
        step = next((q for q in preds.get(s, []) if math.isclose(here, D[i, q], abs_tol=1e-9)), None)
        if step is None:
            break
        s = step
    inv = {i_: n_ for n_, i_ in idx.items()}
    return sorted(lit), float(D[n - 1, end]) / n, (inv.get(s), inv[end])


def _pin(P, ends, snapped):
    """Carry the stroke onto its snapped ends: each point moves by the blend of
    the two ends' snap offsets, weighted by where it projects along the stroke's
    chord. A stroke is compared to a path by SHAPE, not by its offset from the
    lattice — an H stem inset from the cell edge is still the stem."""
    import numpy as np
    (e0, e1), (s0, s1) = [np.array(e, float) for e in ends], [np.array(s, float) for s in snapped]
    d = e1 - e0; L2 = float(d @ d)
    t = np.clip(((P - e0) @ d) / L2, 0.0, 1.0)[:, None] if L2 > 1e-9 else np.zeros((len(P), 1))
    return P + (1 - t) * (s0 - e0) + t * (s1 - e1)


# ── the frame: font units -> lattice cell ────────────────────────────────────

_FRAMES = {}


def _frame(path):
    """(x0, x1, cap, xh, desc): the font's CELL — x from the union of the digit
    and uppercase bboxes (a segment cell is monospace: one frame for every
    glyph, so a narrow '!' stays centred instead of being stretched to a slab),
    y from cap height / x-height / the measured descender."""
    if path not in _FRAMES:
        import make_glyph_ink as GI
        _f, _gs, cmap = GI._font(path)
        xs = []
        for ch in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if ord(ch) in cmap:
                for pl in GI.contours(path, ch):
                    xs += [p[0] for p in pl]
        cap, desc = GI.font_frame(path)
        xh = GI.font_xheight(path) or cap * 0.5
        # the ASCENDER line: where b d h k l reach (a lowercase face's top is
        # not its cap height — Liberation Mono's ascenders overshoot it, and an
        # 'i' tittle mapped against cap lands a full row above the cell)
        tops = [p[1] for ch in "bdhkl" if ord(ch) in cmap
                for pl in GI.contours(path, ch) for p in pl]
        _FRAMES[path] = (min(xs), max(xs), cap, xh, desc, max(tops) if tops else cap)
    return _FRAMES[path]


def _piecewise(anchors):
    """Piecewise-linear map through (from, to) anchors, EXTRAPOLATED past both
    ends on the end pieces' slopes (np.interp clamps, which would fold every
    point above cap height onto the top row)."""
    a = sorted(anchors)

    def f(v):
        i = 0 if v <= a[0][0] else len(a) - 2 if v >= a[-1][0] else \
            max(j for j in range(len(a) - 1) if a[j][0] <= v)
        (u0, w0), (u1, w1) = a[i], a[i + 1]
        return w0 + (v - u0) * (w1 - w0) / (u1 - u0)
    return f


def _to_lattice(path, lower, sw_units, xspan=None):
    """Font units -> lattice.

    ⚑ THE LATTICE IS A CENTRELINE LATTICE, so every frame line is inset by half
    a stroke: the top bar's centreline is half a stem below cap height, the
    baseline bar's half a stem above the baseline. Uppercase, digits and
    symbols: cap -> 0, baseline -> 4, descent -> 6. Lowercase (the lattice's
    convention, segment_topology.LETTERS22): cap -> 0, x-height -> 2, baseline
    -> 4, descent -> 6.

    `xspan` (the CENTRELINE's own x extent) replaces the font's cell for a glyph
    at least WIDE of it: a segment display puts a wide glyph's outer strokes ON
    the outer segments. A narrow glyph keeps the font's cell and stays where the
    face set it."""
    x0, x1, cap, xh, desc, asc = _frame(path)
    h = sw_units / 2.0
    if xspan is not None and (xspan[1] - xspan[0]) >= WIDE * (x1 - x0):
        X = _piecewise([(xspan[0], 0.0), (xspan[1], 2.0)])
    else:
        X = _piecewise([(x0 + h, 0.0), (x1 - h, 2.0)])
    if lower:
        ys = [(asc - h, 0.0), (xh - h, 2.0), (h, 4.0), (desc + h, 6.0)]
    else:
        ys = [(cap - h, 0.0), (h, 4.0), (desc + h, 6.0)]
    Y = _piecewise(ys)

    def T(px, py):
        return X(px), Y(py)
    return T


# ── the compiler ─────────────────────────────────────────────────────────────

def trace(path, ch):
    """The whole derivation for one glyph: [{"kind", "ends", "snap", "path", "cost"}]
    per stroke/dot, and the lit set. None when the font lacks the glyph."""
    import numpy as np
    from scipy import ndimage
    import make_glyph_ink as GI
    _f, _gs, cmap = GI._font(path)
    if ord(ch) not in cmap:
        return None
    polys = GI.contours(path, ch)
    if not polys:
        return {"strokes": [], "lit": []}
    mask, cx, cy = _raster(polys)
    sw = 2.0 * float(np.median(ndimage.distance_transform_edt(mask)[_thin(mask)]))
    skel = _prune(_thin(mask), sw)
    cols = np.where(skel.any(axis=0))[0]
    T = _to_lattice(path, ch in _lower_chars(), sw * PX,
                    (float(cx[cols.min()]), float(cx[cols.max()])) if len(cols) else None)

    def lat(rc):
        r, c = rc
        return T(np.interp(c, np.arange(len(cx)), cx), np.interp(r, np.arange(len(cy)), cy))

    fmask = _digit_mask() if ch in _digits() else None
    lnodes, ledges, ldots = _lattice(fmask)

    def snap(p):
        return min(lnodes, key=lambda q: (math.hypot(p[0] - q[0], p[1] - q[1]), q))

    out, lit = [], set()
    comp, nc = ndimage.label(skel, structure=np.ones((3, 3)))
    nodes, strokes = _graph(skel)
    r2 = lambda e: [round(float(v), 2) for v in e]   # noqa: E731
    small = set()
    for ci in range(1, nc + 1):
        pts = np.array([lat(rc) for rc in np.argwhere(comp == ci)])
        if (pts.max(0) - pts.min(0)).max() >= DOT_EXTENT:
            continue
        small.add(ci)
        c = tuple(pts.mean(0))
        k = min(ldots, key=lambda d: math.hypot(c[0] - ldots[d][0], c[1] - ldots[d][1])) if ldots else None
        near = k is not None and math.hypot(c[0] - ldots[k][0], c[1] - ldots[k][1]) <= DOT_REACH
        out.append({"kind": "dot", "ends": [r2(c)], "snap": None, "path": [k] if near else [], "cost": 0.0})
        if near:
            lit.add(k)
    for walk, a, b in strokes:
        anchor = walk[0] if walk else tuple(int(round(v)) for v in nodes[a])
        if comp[anchor] in small:
            continue
        if a is None:                           # a closed, node-free loop: start
            P = [lat(rc) for rc in walk]        # at the pixel nearest a lattice node
            k = min(range(len(P)), key=lambda j: math.hypot(*np.subtract(P[j], snap(P[j]))))
            P = P[k:] + P[:k] + [P[k]]
            ends = [P[0], P[0]]
        else:
            P = [lat(nodes[a])] + [lat(rc) for rc in walk] + [lat(nodes[b])]
            ends = [P[0], P[-1]]
        P = _thin_points(np.array(P))
        if a is None:                           # a loop closes on its own start
            su = snap(ends[0])
            segs, cost, placed = _match(P, su, su, fmask)
        else:
            su, sv = snap(ends[0]), snap(ends[1])
            if su != sv:
                P = _pin(P, ends, (su, sv))
            segs, cost, placed = _match(P, su, sv, fmask)
        lit |= set(segs)
        out.append({"kind": "loop" if a is None else "stroke", "ends": [r2(e) for e in ends],
                    "snap": [list(p) if p else None for p in placed],
                    "path": segs, "cost": round(cost, 3)})
    if fmask is not None:
        lit = _seven_closure(lit)
    return {"strokes": out, "lit": sorted(lit)}


def _digits():
    import segment_topology as ST
    return set(ST.DIGITS16)


def _digit_mask():
    import segment_topology as ST
    return ST.FORMATS["7"]["mask"]


def _seven_closure(lit):
    """A digit's 22-seg set as the 7-segment digit it is: every coarse 7-seg bar
    lit lights BOTH its halves (segment_topology.FORMATS["7"]["merge"], read
    backwards). See DIGIT RULE in the module docstring."""
    import segment_topology as ST
    merge = ST.FORMATS["7"]["merge"]
    coarse = ST.project(set(lit), "7")
    return {k for k in _digit_mask() if merge.get(k, k) in coarse}


def _thin_points(P, step=0.05):
    """Keep one point per `step` of arc length (the raster is ~30 points per
    lattice unit; the matcher's cost is linear in the count)."""
    keep, acc = [0], 0.0
    for j in range(1, len(P)):
        acc += math.hypot(*(P[j] - P[j - 1]))
        if acc >= step or j == len(P) - 1:
            keep.append(j); acc = 0.0
    return P[keep]


def _lower_chars():
    import segment_topology as ST
    return set(ST.LETTERS22)


def compile_segments(path, charset=SEG_CHARSET):
    """{ch: sorted 22-seg ids} for every char in `charset` the font HAS."""
    out = {}
    for ch in charset:
        t = trace(path, ch)
        if t is not None:
            out[ch] = t["lit"]
    return out


# ── the cached, keyed entry point ────────────────────────────────────────────

_MEMO = {}


def _half(path, half, params, build):
    key = (font_sha256(path), method_fingerprint(half, params))
    if key in _MEMO:
        return _MEMO[key]
    cpath = os.path.join(CACHE_DIR, f"{key[0]}.{half}.{key[1][:16]}.json")
    doc = None
    try:
        with open(cpath, encoding="utf-8") as f:
            doc = json.load(f)
        if doc.get("font_sha256") != key[0] or doc.get("method") != key[1]:
            doc = None
    except (OSError, ValueError):
        doc = None
    if doc is None:
        doc = {"font_sha256": key[0], "method": key[1], "params": params, "glyphs": build()}
        try:
            os.makedirs(CACHE_DIR, exist_ok=True)
            tmp = f"{cpath}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(dumps(doc))
            os.replace(tmp, cpath)
        except OSError:
            pass          # an unwritable cache is a slower build, not a wrong one
    _MEMO[key] = doc
    return doc


def segment_table(path):
    """The compiled segment table at 22: {"font_sha256", "method", "params", "glyphs"}."""
    return _half(path, "segment22", PARAMS, lambda: compile_segments(path))


def compile_font(path):
    """The whole compiled document for `path`."""
    s = segment_table(path)
    return {"format": FORMAT,
            "font": {"file": os.path.basename(path), "sha256": s["font_sha256"]},
            "segment": {"22": {k: s[k] for k in ("method", "params", "glyphs")}}}


def dumps(doc):
    """THE serialisation: sorted keys, fixed separators, ASCII-escaped — same doc, same bytes."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"


# ── CLI ──────────────────────────────────────────────────────────────────────

def _find_font(argv):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    from check_projection import find_font
    return find_font(argv[argv.index("--font") + 1] if "--font" in argv else None)


def diff_rows(path):
    """[(fmt, ch, authored, compiled, declared)] for every non-blank authored glyph."""
    import display_types as DT
    import segment_topology as ST
    seg = segment_table(path)["glyphs"]
    rows = []
    for fmt in ("22", "7"):
        for ch, auth in sorted(DT.registry()["segGlyphs"][fmt].items()):
            if not auth:
                continue
            raw = seg.get(ch)
            got = None if raw is None else sorted(ST.project(set(raw), fmt))
            rows.append((fmt, ch, list(auth), got, ch in DECLARED))
    return rows


def main(argv):
    known = {"--font", "--show", "--emit", "--key", "--glyph", "--diff"}
    for a in (x for x in argv[1:] if x.startswith("--")):
        if a not in known:
            print(f"font_compiler: unknown flag {a!r}", file=sys.stderr)
            return 2
    font = _find_font(argv)
    if not font:
        print("font_compiler: SKIP — no TTF found (pass --font PATH); 0 glyphs compiled", file=sys.stderr)
        return 0
    if "--key" in argv:
        print(f"font    {font_sha256(font)}  {font}")
        print(f"segment {method_fingerprint('segment22', PARAMS)}")
        return 0
    if "--glyph" in argv:
        ch = argv[argv.index("--glyph") + 1]
        t = trace(font, ch)
        if t is None:
            print(f"{ch!r}: the font lacks it")
            return 0
        for s in t["strokes"]:
            print(f"  {s['kind']:6s} ends {s['ends']}  snap {s['snap']}"
                  f"  -> {' '.join(s['path']) or '-'}  (mean cost {s['cost']})")
        print(f"{ch!r} lit @22: {' '.join(t['lit']) or '-'}")
        return 0
    if "--diff" in argv:
        rows = diff_rows(font)
        for fmt in ("22", "7"):
            rs = [r for r in rows if r[0] == fmt]
            for _f, ch, a, g, dec in rs:
                if a != g:
                    miss = sorted(set(a) - set(g or [])); extra = sorted(set(g or []) - set(a))
                    print(f"  {fmt:>2} {ch!r:5s} {'DECLARED ' if dec else ''}authored {' '.join(a)}"
                          f" | compiled {' '.join(g or []) or '-'} | miss {' '.join(miss) or '-'}"
                          f" extra {' '.join(extra) or '-'}")
            print(f"font_compiler: {fmt}-seg {sum(1 for r in rs if r[2] == r[3])} of {len(rs)} "
                  f"authored glyphs reproduced; {sum(1 for r in rs if r[2] != r[3] and r[4])} "
                  f"of the rest declared convention")
        return 0
    doc = compile_font(font)
    if "--emit" in argv:
        out = argv[argv.index("--emit") + 1]
        with open(out, "w", encoding="utf-8") as f:
            f.write(dumps(doc))
        print(f"font_compiler: wrote {out} ({len(dumps(doc))} bytes)")
        return 0
    s = doc["segment"]["22"]["glyphs"]
    print(f"font {font}  sha256 {doc['font']['sha256']}")
    print(f"  segment 22 : {len(s)} of {len(SEG_CHARSET)} charset glyphs present, "
          f"{sum(1 for v in s.values() if v)} lit  (method {doc['segment']['22']['method'][:16]})")
    return 0


def _selftest():
    """The MEASUREMENT can see: the fingerprint moves, the serialisation is
    stable, and the skeleton method recovers the straight-stroke glyphs whose
    authored sets are unambiguous (H L T) and tells a stroke from a serif."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    p = {"px": 16}
    chk("the method fingerprint moves with a parameter",
        method_fingerprint("m", p) != method_fingerprint("m", {"px": 8}), True)
    chk("the method fingerprint is stable", method_fingerprint("m", p), method_fingerprint("m", dict(p)))
    chk("dumps is key-order independent", dumps({"b": 1, "a": [1]}), dumps({"a": [1], "b": 1}))
    chk("the lattice has 20 strokes and 2 dots", tuple(len(x) for x in _lattice()[1:]), (20, 2))
    font = _find_font([])
    if not font:
        print("  SKIP — no TTF on this host (the lattice arms above still ran)")
        print("font_compiler selftest: SKIP")
        return ok
    seg = compile_segments(font, charset="HLT ☃")
    chk("'H' compiles to its stems and crossbar", seg["H"], sorted("b c e f g1 g2".split()))
    chk("'L' compiles to its stem and foot", seg["L"], sorted("d1 d2 e f".split()))
    chk("'T' compiles to its bar and centre stem", seg["T"], sorted("a1 a2 j m".split()))
    chk("a space lights nothing", seg[" "], [])
    chk("a char the font lacks is absent", "☃" in seg, False)
    print("font_compiler selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
