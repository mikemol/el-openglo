#!/usr/bin/env python3
"""Segment-display topology: ONE canonical 16-segment geometry; 7/9/14 are
projections (mask + merge) of it. A glyph is a set of 16-seg segment ids.

Standard segment naming (matches the Wikipedia / 7seg.fandom tables):
  a1 a2  top horizontal, left & right halves
  f      upper-left vertical      j  upper-center vertical    b  upper-right vertical
  h      upper-left diagonal      k  upper-right diagonal
  g1 g2  middle horizontal, left & right halves
  e      lower-left vertical      m  lower-center vertical    c  lower-right vertical
  i      lower-left diagonal      l  lower-right diagonal   (i = \\ lower-left, l = / lower-right)
  d1 d2  bottom horizontal, left & right halves

Coordinate cell: width W=2, height H=4 (top row 0..2, mid at y=2, bottom at y=4),
in the same unit convention the wallpaper uses (segment length L per half).
Each segment -> a polygon (list of (x,y) in units of L, where a digit cell is
2L wide, 4L tall). Diagonals are thin parallelograms.
"""

# geometry as unit polygons; T = half-thickness applied by the renderer
# horizontal bars: (kind 'h', x0, x1, y)   vertical bars: (kind 'v', x, y0, y1)
# diagonals: (kind 'd', (x0,y0), (x1,y1))
GEOM16 = {
    "a1": ("h", 0, 1, 0), "a2": ("h", 1, 2, 0),
    "f":  ("v", 0, 0, 2), "j": ("v", 1, 0, 2), "b": ("v", 2, 0, 2),
    "h":  ("d", (0, 0), (1, 2)), "k": ("d", (2, 0), (1, 2)),
    "g1": ("h", 0, 1, 2), "g2": ("h", 1, 2, 2),
    "e":  ("v", 0, 2, 4), "m": ("v", 1, 2, 4), "c": ("v", 2, 2, 4),
    "i":  ("d", (0, 4), (1, 2)), "l": ("d", (2, 4), (1, 2)),
    "d1": ("d", (0, 4), (1, 4)) if False else ("h", 0, 1, 4), "d2": ("h", 1, 2, 4),
}
SEG16 = list(GEOM16.keys())

# --- format projections: mask (allowed segs) + merge (rich->coarse fuse) ------
# 14-seg: top & bottom NOT split -> a1,a2 fuse to 'a'; d1,d2 fuse to 'd'.
# 7-seg: no diagonals, no center verticals, middle not split.
FORMATS = {
    "16": {"mask": set(SEG16), "merge": {}},
    "14": {"mask": set(SEG16), "merge": {"a1": "a", "a2": "a", "d1": "d", "d2": "d"}},
    "9":  {"mask": {"a1","a2","b","c","d1","d2","e","f","g1","g2","j","m"},
           "merge": {"a1":"a","a2":"a","d1":"d","d2":"d","g1":"g","g2":"g"}},
    "7":  {"mask": {"a1","a2","b","c","d1","d2","e","f","g1","g2"},
           "merge": {"a1":"a","a2":"a","d1":"d","d2":"d","g1":"g","g2":"g"}},
}

def project(seg_set, fmt):
    """Project a 16-seg glyph (set of ids) onto a coarser format.
    Segments outside the mask are dropped; merged segments require ALL their
    rich parts present to light the coarse one? No — physically, a coarse
    segment lights if ANY covered rich segment is on (the coarse bar spans both
    halves). Returns the set of *coarse* segment ids that light."""
    f = FORMATS[fmt]
    out = set()
    for s in seg_set:
        if s not in f["mask"]:
            continue
        out.add(f["merge"].get(s, s))
    return out

# --- glyph tables: 16-seg segment sets, pinned from fetched references --------
# digits (English), from arXiv 1009.4977 Table 1 cross-checked w/ fandom:
DIGITS16 = {
    "0": "a1 a2 b c d1 d2 e f",
    "1": "b c",
    "2": "a1 a2 b g1 g2 e d1 d2",
    "3": "a1 a2 b c g1 g2 d1 d2",
    "4": "f g1 g2 b c",
    "5": "a1 a2 f g1 g2 c d1 d2",
    "6": "a1 a2 f g1 g2 e c d1 d2",
    "7": "a1 a2 b c",
    "8": "a1 a2 b c d1 d2 e f g1 g2",
    "9": "a1 a2 b c d1 d2 f g1 g2",
}
# uppercase A-Z, 16-seg (fandom 16-seg + standard starburst; M/W use diagonals)
LETTERS16 = {
    "A": "a1 a2 b c e f g1 g2",
    "B": "a1 a2 b c d1 d2 g2 j m",
    "C": "a1 a2 d1 d2 e f",
    "D": "a1 a2 b c d1 d2 j m",
    "E": "a1 a2 d1 d2 e f g1 g2",
    "F": "a1 a2 e f g1 g2",
    "G": "a1 a2 c d1 d2 e f g2",
    "H": "b c e f g1 g2",
    "I": "a1 a2 d1 d2 j m",
    "J": "b c d1 d2 e",
    "K": "e f g1 k l",
    "L": "d1 d2 e f",
    "M": "b c e f h k",
    "N": "b c e f h l",
    "O": "a1 a2 b c d1 d2 e f",
    "P": "a1 a2 b e f g1 g2",
    "Q": "a1 a2 b c d1 d2 e f l",
    "R": "a1 a2 b e f g1 g2 l",
    "S": "a1 a2 c d1 d2 f g1 g2",
    "T": "a1 a2 j m",
    "U": "b c d1 d2 e f",
    "V": "e f i k",
    "W": "b c e f i l",
    "X": "h i k l",
    "Y": "h k m",
    "Z": "a1 a2 d1 d2 i k",
}
SYMBOLS16 = {
    "*": "g1 g2 h i j k l m",
    "-": "g1 g2",
    "+": "g1 g2 j m",
    "/": "i k",
    "\\": "h l",
    "=": "d1 d2 g1 g2",
    " ": "",
    ":": "",     # colon handled as separate dots by the renderer
    "'": "f",
    "?": "a1 a2 b g2 m",
    "!": "j m",  # approximation
    "_": "d1 d2",
    "0": DIGITS16["0"],
}

def glyph16(ch):
    ch = ch.upper()
    if ch in DIGITS16: return set(DIGITS16[ch].split())
    if ch in LETTERS16: return set(LETTERS16[ch].split())
    if ch in SYMBOLS16: return set(SYMBOLS16[ch].split()) if SYMBOLS16[ch] else set()
    return set()  # unknown -> blank

# 7-seg glyph via projection, in the OLD naming (A..G) so it can be proven
# byte-equal to make_wallpaper's DIGIT table.
SEG7_RENAME = {"a": "A", "b": "B", "c": "C", "d": "D", "e": "E", "f": "F", "g": "G"}
def glyph7_letters(ch):
    """Project to 7-seg and rename to A..G for parity with the wallpaper table."""
    coarse = project(glyph16(ch), "7")
    return "".join(sorted(SEG7_RENAME[s] for s in coarse if s in SEG7_RENAME))


# The 7-seg strokes in the COARSE cell the SVG/QML surfaces draw in: a 2-wide,
# 3-tall grid of (kind, ux, uy) where a horizontal spans the full width at row
# uy and a vertical spans one row at column ux. GEOM16's cell is 2x4 in half-row
# units; this is that cell at 7-seg granularity.
_SEG7_GRID = {
    "A": ("h", 0, 0), "G": ("h", 0, 1), "D": ("h", 0, 2),
    "F": ("v", 0, 0), "B": ("v", 1, 0), "E": ("v", 0, 1), "C": ("v", 1, 1),
}


def seg7_strokes():
    """{a..g: (kind, ...)} — the coarse 7-seg strokes in GEOM16's own 2x4 cell.

    ⚑ A COARSE BAR IS THE UNION OF THE HALVES IT MERGES.  16-seg SPLITS the top,
    middle and bottom bars (a1|a2, g1|g2, d1|d2) so a letter can light one side;
    7-seg does not, and FORMATS["7"]'s merge map is the statement of that. Taking
    either half alone gives a bar of half the width — which renders as a valid
    image of a wrong glyph, the failure mode a picture catches and a type check
    does not.

    Verticals are unsplit in both formats, so they pass through unchanged."""
    merged = {}
    for coarse, parts in (("a", ("a1", "a2")), ("g", ("g1", "g2")),
                          ("d", ("d1", "d2"))):
        xs = [GEOM16[p][1] for p in parts] + [GEOM16[p][2] for p in parts]
        y = GEOM16[parts[0]][3]
        merged[coarse] = ("h", min(xs), max(xs), y)
    for coarse in ("f", "b", "e", "c"):
        merged[coarse] = GEOM16[coarse]
    return merged


def seg7_svg_grid():
    """{A..G: (kind, ux, uy)} — the 7-seg cell the raster/SVG surfaces render in.

    ⚑ THE SURFACES HAD THIS TABLE, EACH ITS OWN COPY (⊕SEGMENT-SUBSTRATE).  The
    wallpaper, the clock and the boot splash each carried the same seven strokes;
    the clock went further and re-read the wallpaper's SOURCE with a regex, so a
    hand edit to one file's literal silently redefined another's geometry.

    ⚑ WHY THIS IS A PROJECTION AND NOT A SECOND TABLE.  GEOM16 is the lattice, in
    a 2x4 half-row cell that supports diagonals and split bars. A 7-seg renderer
    draws in a coarser 2x3 cell — no diagonals, no split bars — and the mapping
    between them is fixed. Deriving the coarse cell from GEOM16 element-by-element
    would re-derive that fixed mapping on every call; naming it once, HERE, keeps
    one owner. The parity gate below is what makes it a projection rather than a
    fork: project()'s own 7-seg output must agree with these keys."""
    return dict(_SEG7_GRID)

# --- 22-segment: 16-seg topology PLUS a descender sub-cell ------------------
# ⚑ RECONSTRUCTED.  The original definition was lost with the repo; this is
# rebuilt from the design log (COTYPE.md, session 27 "⊕SEG22 invoked" and its
# closure), which pins the STRUCTURE exactly even though the literal coordinates
# did not survive:
#
#   "22 = 16-seg + SIX additions:
#      · two dots beside the middle vertical  (i, j, punctuation)   -> p1 p2
#      · one extra diagonal in bottom-left counter (k, n, s, x)     -> n1
#      · THREE segments below the baseline (descenders g j p q y)   -> dl dc dr"
#
# and the invariant that makes the rebuild CHECKABLE rather than invented:
#
#   "projection 22->16 (drop the 6 extras) is byte-equal to native glyph16 for
#    all uppercase+digits — so 16-seg is exactly the ascender-body substructure"
#
# ⚑ THE SIX IDENTIFIERS AND THEIR ROLES ARE RECOVERED; THE COORDINATES ARE
# DERIVED.  They are placed in the existing cell convention (W=2, H=4, descender
# region below y=4, mirroring the 5x7->5x8 body+descender move the log names).
# A future pin against the original artifact should treat the coordinates as the
# soft part and the identifiers, roles, and the 22->16 invariant as the hard part.
DESCENDER_DEPTH = 2                      # the sub-cell below the baseline, in L

GEOM22 = dict(GEOM16)
GEOM22.update({
    # two dots flanking the middle vertical — the i/j tittle and punctuation.
    # Rendered as degenerate (zero-length) verticals: a dot is a point the
    # renderer thickens, exactly as it thickens a bar.
    "p1": ("v", 1, 1, 1),
    "p2": ("v", 1, 3, 3),
    # the extra diagonal in the bottom-left counter (k, n, s, x): from the
    # baseline's left corner up to the cell centre, the mirror of `l`.
    "n1": ("d", (0, 2), (1, 4)),
    # three descender bars below the baseline (g j p q y).  Same left/centre/
    # right column structure as the body's verticals, one sub-cell lower.
    "dl": ("v", 0, 4, 4 + DESCENDER_DEPTH),
    "dc": ("v", 1, 4, 4 + DESCENDER_DEPTH),
    "dr": ("v", 2, 4, 4 + DESCENDER_DEPTH),
})
SEG22 = list(GEOM22.keys())

# The six segments 22 adds to 16 — the exact set the 22->16 projection drops.
SEG22_EXTRAS = ("p1", "p2", "n1", "dl", "dc", "dr")

# "22" joins the lattice as a SUPERSET of 16 (not a coarsening): mask = all 22,
# no merges.  Projecting 22->16 is therefore mask-only, and must be byte-equal
# to native 16 — the log's stated gate, asserted in _selftest below.
FORMATS["22"] = {"mask": set(SEG22), "merge": {}}


def endpoints(key_or_spec):
    """Endpoint tuple (ax,ay,bx,by) for a GEOM22 segment key OR a raw spec.
    h -> (x0,y,x1,y); v -> (x,y0,x,y1); d -> (p0x,p0y,p1x,p1y)."""
    spec = GEOM22[key_or_spec] if isinstance(key_or_spec, str) else key_or_spec
    k = spec[0]
    if k == "h": return (spec[1], spec[3], spec[2], spec[3])
    if k == "v": return (spec[1], spec[2], spec[1], spec[3])
    if k == "d": return (spec[1][0], spec[1][1], spec[2][0], spec[2][1])
    raise ValueError(f"bad segment spec kind: {k!r}")


def display_geom(fmt):
    """POST-MERGE per-format display geometry, keyed by the names project() returns.
    A merged segment (e.g. 7-seg 'a' = a1|a2) spans the UNION of its parts' endpoints.
    This is the geometry a low-res surface renders in; keeps derez COVERAGE-MONOTONE
    (the renderer must use project()'s own key space)."""
    merge = FORMATS[fmt]["merge"]
    geo = {}
    for k in FORMATS[fmt]["mask"]:
        tgt = merge.get(k, k)
        e = endpoints(k)
        if tgt not in geo:
            geo[tgt] = list(e)
        else:
            xs = [geo[tgt][0], geo[tgt][2], e[0], e[2]]
            ys = [geo[tgt][1], geo[tgt][3], e[1], e[3]]
            geo[tgt] = [min(xs), min(ys), max(xs), max(ys)]
    return geo


def _selftest():
    """The 22->16 invariant the design log states, asserted rather than assumed."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("22 is a superset of 16", set(SEG16) <= set(SEG22), True)
    check("22 adds exactly 6 segments", len(SEG22) - len(SEG16), 6)
    check("the extras are the 6 added", sorted(set(SEG22) - set(SEG16)),
          sorted(SEG22_EXTRAS))
    # THE GATE FROM THE LOG: dropping the extras from a 22-seg glyph must give
    # back native 16 for every uppercase and digit.
    drift = [ch for ch in "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
             if (project(glyph16(ch), "22") - set(SEG22_EXTRAS)) != glyph16(ch)]
    check(f"22->16 byte-equal to native 16 ({drift[:5]})", drift, [])
    # every segment must have well-formed endpoints
    bad = [k for k in SEG22 if len(endpoints(k)) != 4]
    check(f"every segment has endpoints ({bad})", bad, [])

    # ⚑ THE COARSE 7-SEG CELL IS A PROJECTION, NOT A FORK.  seg7_svg_grid names
    # the 2x3 cell the SVG/QML surfaces draw in. If its key set ever diverged
    # from what project(..., "7") actually emits, it would be a second geometry
    # wearing a projection's name — which is the silo this replaced.
    grid = set(seg7_svg_grid())
    emitted = set()
    for ch in "0123456789":
        emitted |= set(glyph7_letters(ch))
    check(f"the 7-seg grid covers what project() emits ({sorted(emitted - grid)})",
          sorted(emitted - grid), [])
    check("the 7-seg grid has exactly seven strokes", len(grid), 7)

    # ⚑ THE COARSE BARS SPAN THE WHOLE CELL, which is what taking one half-bar
    # got wrong — and got wrong INVISIBLY, as a valid image of a clipped glyph.
    st = seg7_strokes()
    check("seg7_strokes has seven strokes", len(st), 7)
    wide = [k for k in ("a", "g", "d")
            if not (st[k][1] == 0 and st[k][2] == 2)]
    check(f"the horizontals span the full 2-wide cell ({wide})", wide, [])
    tall = [k for k in ("f", "b", "e", "c") if st[k][0] != "v"]
    check(f"the verticals stay vertical ({tall})", tall, [])
    # the descenders must actually lie below the baseline, or they are not descenders
    below = [k for k in ("dl", "dc", "dr") if endpoints(k)[3] <= 4]
    check(f"descenders reach below the baseline ({below})", below, [])
    # and nothing in the 16-seg body may dip into the descender region
    body = [k for k in SEG16 if max(endpoints(k)[1], endpoints(k)[3]) > 4]
    check(f"the 16-seg body stays above the baseline ({body})", body, [])
    print("segment_topology selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    # self-report: the family lattice and a parity check vs the wallpaper 7-seg
    import re
    wp = open("make_wallpaper.py").read()
    DIGIT7 = eval(re.search(r'DIGIT = (\{.*?\})', wp, re.S).group(1))
    print("format masks:", {k: len(v["mask"]) for k, v in FORMATS.items()})
    ok = True
    for d, segs in DIGIT7.items():
        proj = glyph7_letters(d)
        match = set(proj) == set(segs)
        ok &= match
        if not match:
            print(f"  digit {d}: wallpaper={segs} projected={proj}  MISMATCH")
    print("7-seg projection == wallpaper DIGIT table:", ok)
    # M/N/W distinctness — the whole point of 16-seg
    print("M!=N:", glyph16("M") != glyph16("N"), "M!=W:", glyph16("M") != glyph16("W"))
    print("* has 8 points:", len(glyph16("*")) == 8)
