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

if __name__ == "__main__":
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
