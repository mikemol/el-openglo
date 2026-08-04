#!/usr/bin/env python3
"""Display-type abstraction (⊕DOT).

A rendered character = a set of lit PRIMITIVES in a cell. Two instances:

  - SegmentDisplay: primitive = polygon from segment_topology.GEOM16;
    glyph = set of segment ids; formats 7/9/14/16 via projection.
  - MatrixDisplay: primitive = pixel at (col,row); glyph = set of (col,row);
    parametric MxN, classic 5x7.

Both expose the SAME contract the renderers consume:
  .cell_aspect()            -> (width_units, height_units) of one cell
  .lit_primitives(ch, opts) -> list of ('rect'|'poly'|'dot', geometry, on)
so make_wallpaper / make_clock render a DISPLAY, not specifically segments.

This subsumes ⊕SEG*: SegmentDisplay is the segment path unchanged.
"""
import segment_topology as _seg


class SegmentDisplay:
    kind = "segment"

    def __init__(self, fmt="7"):
        assert fmt in _seg.FORMATS, fmt
        self.fmt = fmt

    def cell_aspect(self):
        return (2.0, 4.0)  # 2L wide, 4L tall — matches GEOM16 unit cell

    def glyph(self, ch):
        return _seg.project(_seg.glyph16(ch), self.fmt)

    def lit_primitives(self, ch, show_ghost=True):
        """Yield (type, spec, on). type 'poly' with spec = GEOM16 entry."""
        f = _seg.FORMATS[self.fmt]
        lit = self.glyph(ch)
        out = []
        for sid, spec in _seg.GEOM16.items():
            if sid not in f["mask"]:
                continue
            coarse = f["merge"].get(sid, sid)
            on = coarse in lit
            if not on and not show_ghost:
                continue
            out.append(("seg", spec, on))
        return out


# --- 5x7 font, column-byte convention (HD44780 lineage) ----------------------
# Each glyph = 5 column bytes; bit b of a column = row b (b0 = top row).
# 'A' = 0x7e,0x09,0x09,0x09,0x7e verified against Newhaven/edaboard reference.
FONT5x7 = {
    "0": [0x3e,0x51,0x49,0x45,0x3e], "1": [0x00,0x42,0x7f,0x40,0x00],
    "2": [0x42,0x61,0x51,0x49,0x46], "3": [0x21,0x41,0x45,0x4b,0x31],
    "4": [0x18,0x14,0x12,0x7f,0x10], "5": [0x27,0x45,0x45,0x45,0x39],
    "6": [0x3c,0x4a,0x49,0x49,0x30], "7": [0x01,0x71,0x09,0x05,0x03],
    "8": [0x36,0x49,0x49,0x49,0x36], "9": [0x06,0x49,0x49,0x29,0x1e],
    "A": [0x7e,0x11,0x11,0x11,0x7e], "B": [0x7f,0x49,0x49,0x49,0x36],
    "C": [0x3e,0x41,0x41,0x41,0x22], "D": [0x7f,0x41,0x41,0x22,0x1c],
    "E": [0x7f,0x49,0x49,0x49,0x41], "F": [0x7f,0x09,0x09,0x09,0x01],
    "G": [0x3e,0x41,0x49,0x49,0x7a], "H": [0x7f,0x08,0x08,0x08,0x7f],
    "I": [0x00,0x41,0x7f,0x41,0x00], "J": [0x20,0x40,0x41,0x3f,0x01],
    "K": [0x7f,0x08,0x14,0x22,0x41], "L": [0x7f,0x40,0x40,0x40,0x40],
    "M": [0x7f,0x02,0x0c,0x02,0x7f], "N": [0x7f,0x04,0x08,0x10,0x7f],
    "O": [0x3e,0x41,0x41,0x41,0x3e], "P": [0x7f,0x09,0x09,0x09,0x06],
    "Q": [0x3e,0x41,0x51,0x21,0x5e], "R": [0x7f,0x09,0x19,0x29,0x46],
    "S": [0x46,0x49,0x49,0x49,0x31], "T": [0x01,0x01,0x7f,0x01,0x01],
    "U": [0x3f,0x40,0x40,0x40,0x3f], "V": [0x1f,0x20,0x40,0x20,0x1f],
    "W": [0x7f,0x20,0x18,0x20,0x7f], "X": [0x63,0x14,0x08,0x14,0x63],
    "Y": [0x03,0x04,0x78,0x04,0x03], "Z": [0x61,0x51,0x49,0x45,0x43],
    " ": [0x00,0x00,0x00,0x00,0x00], "-": [0x08,0x08,0x08,0x08,0x08],
    ":": [0x00,0x36,0x36,0x00,0x00], ".": [0x00,0x60,0x60,0x00,0x00],
    "/": [0x20,0x10,0x08,0x04,0x02], "*": [0x14,0x08,0x3e,0x08,0x14],
    "+": [0x08,0x08,0x3e,0x08,0x08], "?": [0x02,0x01,0x51,0x09,0x06],
}


class MatrixDisplay:
    kind = "matrix"

    def __init__(self, cols=5, rows=7, font=None):
        self.cols, self.rows = cols, rows
        self.font = font or FONT5x7
        assert (cols, rows) == (5, 7) or font, "non-5x7 needs an explicit font"

    def cell_aspect(self):
        # cols wide, rows tall, plus we render at unit=1 per dot
        return (float(self.cols), float(self.rows))

    def glyph(self, ch):
        """Return the set of lit (col,row) pixels."""
        cols = self.font.get(ch)
        if cols is None:
            cols = self.font.get(ch.upper())
        if cols is None:
            return set()
        px = set()
        for c, colbyte in enumerate(cols):
            for r in range(self.rows):
                if colbyte & (1 << r):
                    px.add((c, r))
        return px

    def lit_primitives(self, ch, show_ghost=True):
        """Yield ('dot', (col,row), on) for every cell position."""
        lit = self.glyph(ch)
        out = []
        for c in range(self.cols):
            for r in range(self.rows):
                on = (c, r) in lit
                if not on and not show_ghost:
                    continue
                out.append(("dot", (c, r), on))
        return out


# --- display registry + legibility that spans the whole lattice --------------
DISPLAYS = {
    "7": SegmentDisplay("7"), "9": SegmentDisplay("9"),
    "14": SegmentDisplay("14"), "16": SegmentDisplay("16"),
    "5x7": MatrixDisplay(5, 7),
}
# partial order by expressiveness (NOT subset — matrix isn't a segment refinement)
LATTICE_ORDER = ["7", "9", "14", "16", "5x7"]


def collision_classes(disp_key, charset):
    """Chars whose glyphs are identical under display `disp_key`."""
    d = DISPLAYS[disp_key]
    groups = {}
    for c in charset:
        key = frozenset(d.glyph(c))
        groups.setdefault(key, []).append(c)
    return [sorted(g) for g in groups.values() if len(g) > 1]


if __name__ == "__main__":
    # verify the canonical 'A' bitmap and print it, plus lattice legibility
    m = MatrixDisplay()
    A = m.glyph("A")
    print("A pixel rows (top->bottom):")
    for r in range(7):
        print("  " + "".join("#" if (c, r) in A else "." for c in range(5)))
    charset = list("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    print("\ncollision count across the display lattice:")
    for k in LATTICE_ORDER:
        n = sum(len(g) - 1 for g in collision_classes(k, charset))
        print(f"  {k:4s}: {n} colliding chars")
