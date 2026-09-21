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
import os
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
#
# ⚑ THE COMMENT AND THE TABLE DISAGREED, AND THE TABLE WAS WRONG.  'A' held
# 0x7e,0x11,0x11,0x11,0x7e — the crossbar on row 4 of 0..6 instead of the middle,
# with a flat 3-dot apex. The comment directly above it carried the correct
# 0x09 columns, and ⊕DOT's closure claims "canonical glyphs (0,A,H,E) verified
# against Newhaven/edaboard references", so the value was checked once and the
# checked value is not what shipped.
#
# ⚑ AND NOTHING COULD SEE IT.  check_display_registry compares the emission to
# registry() — Python to Python — so a wrong glyph round-trips perfectly. The
# 5x7 collision count stayed 0 because a malformed 'A' still differs from every
# other letter. It took RENDERING the marquee and looking, which is the same way
# plymouth's clipped digits were caught, and the same reason those samples exist.
# Measured against its own neighbours: 'H' puts its bar on row 3 and 'E' its bars
# on 0/3/6; 'A' was the only glyph disagreeing with the set it belongs to.
FONT5x7 = {
    "0": [0x3e,0x51,0x49,0x45,0x3e], "1": [0x00,0x42,0x7f,0x40,0x00],
    "2": [0x42,0x61,0x51,0x49,0x46], "3": [0x21,0x41,0x45,0x4b,0x31],
    "4": [0x18,0x14,0x12,0x7f,0x10], "5": [0x27,0x45,0x45,0x45,0x39],
    "6": [0x3c,0x4a,0x49,0x49,0x30], "7": [0x01,0x71,0x09,0x05,0x03],
    "8": [0x36,0x49,0x49,0x49,0x36], "9": [0x06,0x49,0x49,0x29,0x1e],
    "A": [0x7e,0x09,0x09,0x09,0x7e], "B": [0x7f,0x49,0x49,0x49,0x36],
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


def _cols(*rows):
    """Column bytes from row strings ('#' lit), bit r = row r — so a glyph can be
    READ in the source instead of decoded from hex (the 'A' that was wrong for a
    session was hex nobody could see)."""
    w = len(rows[0])
    assert all(len(r) == w for r in rows), "ragged glyph"
    return [sum(1 << r for r, row in enumerate(rows) if row[c] == "#") for c in range(w)]


# ⚑ "DESCENDER" IS PIXELS BELOW A DECLARED BASELINE LINE, NOT A TALLER GRID
# (⊕DOT-FONT-DESC, session 26; the table itself was lost in the recovery and is
# RE-AUTHORED here, W26 2026-09-21). Rows 0-6 are the body, shared byte-for-byte
# with FONT5x7's uppercase and digits; row 7 is descent, used by g j p q y. The
# lowercase follows standard pixel-font conventions (spleen / HD44780-A02
# lineage) and is authored, not pinned to a vendor bitmap — the closure's residue.
FONT5x8_BASELINE = 6            # the last BODY row; the baseline LINE is its bottom edge, cell-y 7
FONT5x8 = dict(FONT5x7)
FONT5x8.update({
    "a": _cols(".....", ".....", ".###.", "....#", ".####", "#...#", ".####", "....."),
    "b": _cols("#....", "#....", "####.", "#...#", "#...#", "#...#", "####.", "....."),
    "c": _cols(".....", ".....", ".####", "#....", "#....", "#....", ".####", "....."),
    "d": _cols("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####", "....."),
    "e": _cols(".....", ".....", ".###.", "#...#", "#####", "#....", ".####", "....."),
    "f": _cols("..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#...", "....."),
    "g": _cols(".....", ".....", ".####", "#...#", "#...#", ".####", "....#", ".###."),
    "h": _cols("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#", "....."),
    "i": _cols("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###.", "....."),
    "j": _cols("...#.", ".....", "..##.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "k": _cols("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "....."),
    "l": _cols(".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###.", "....."),
    "m": _cols(".....", ".....", "##.#.", "#.#.#", "#.#.#", "#...#", "#...#", "....."),
    "n": _cols(".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#", "....."),
    "o": _cols(".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###.", "....."),
    "p": _cols(".....", ".....", "####.", "#...#", "#...#", "####.", "#....", "#...."),
    "q": _cols(".....", ".....", ".####", "#...#", "#...#", ".####", "....#", "....#"),
    "r": _cols(".....", ".....", "#.##.", "##..#", "#....", "#....", "#....", "....."),
    "s": _cols(".....", ".....", ".####", "#....", ".###.", "....#", "####.", "....."),
    "t": _cols(".#...", ".#...", "###..", ".#...", ".#...", ".#..#", "..##.", "....."),
    "u": _cols(".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#", "....."),
    "v": _cols(".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#..", "....."),
    "w": _cols(".....", ".....", "#...#", "#...#", "#.#.#", "#.#.#", ".#.#.", "....."),
    "x": _cols(".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "....."),
    "y": _cols(".....", ".....", "#...#", "#...#", "#...#", ".####", "....#", ".###."),
    "z": _cols(".....", ".....", "#####", "...#.", "..#..", ".#...", "#####", "....."),
})
DESCENDERS = frozenset("gjpqy")


class MatrixDisplay:
    kind = "matrix"

    def __init__(self, cols=5, rows=7, font=None, baseline=None):
        self.cols, self.rows = cols, rows
        self.font = font or FONT5x7
        # the last body row, or None for a top-aligned display with no baseline
        self.baseline = baseline
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
    "5x8": MatrixDisplay(5, 8, font=FONT5x8, baseline=FONT5x8_BASELINE),
}
# partial order by expressiveness (NOT subset — matrix isn't a segment refinement)
LATTICE_ORDER = ["7", "9", "14", "16", "5x7", "5x8"]


def collision_classes(disp_key, charset):
    """Chars whose glyphs are identical under display `disp_key`."""
    d = DISPLAYS[disp_key]
    groups = {}
    for c in charset:
        key = frozenset(d.glyph(c))
        groups.setdefault(key, []).append(c)
    return [sorted(g) for g in groups.values() if len(g) > 1]


# --- the registry, emitted for QML (⊕DOT-WIRE) -------------------------------
#
# ⚑ THIS FUNCTION WAS LOST IN THE RECOVERY, AND ITS CLOSURE TEXT OUTLIVED IT.
# COTYPE.md's ⊕DOT-WIRE closure reads "make_clock emits the whole display_types
# registry (geom16+segFormats+segGlyphs+font5x7+font5x8+displays) via
# display_types.as_qml_js() — single source, nothing retyped", and measured:
# `as_qml_js` had ZERO definitions and ZERO callers, and `litPrimitives` was
# absent from every consumer. A closure describing machinery that is not there is
# exactly the stale-status failure this repo was rebuilt to stop making — the same
# shape as RECOVERY-NOTES.md's "main rebuild gap".
#
# ⚑ WHAT THE CONTRACT IS, AND WHY THE QML CANNOT JUST TAKE SEGMENTS.  ⊕DOT
# rejected "matrix as FORMATS['5x7'], reuse project()" as a side-pick: a segment
# is a subset of a topology, a pixel-cell is a raster, and they share no
# substrate. The abstraction was lifted one level instead — both displays expose
# `cell_aspect()` and `lit_primitives()`, and a renderer consumes A DISPLAY. So
# this emits BOTH kinds under one registry with `kind` as the dispatch tag, and
# the QML branches on that rather than on which table it was handed.

def _seg_endpoints(spec):
    """Any stroke -> (ax, ay, bx, by) in unit-grid coords.

    ⚑ DELIBERATELY THE SAME NORMALISATION make_segment_display._endpoints DOES,
    and that duplication is a finding rather than a design: two functions turning
    GEOM16 specs into endpoints is two places to disagree. Recorded here and left
    for a follow-up, because merging them changes make_segment_display's emitted
    bytes and this commit is meant to restore a lost capability, not move output."""
    k = spec[0]
    if k == "h":
        return (spec[1], spec[3], spec[2], spec[3])
    if k == "v":
        return (spec[1], spec[2], spec[1], spec[3])
    if k == "d":
        return (spec[1][0], spec[1][1], spec[2][0], spec[2][1])
    raise ValueError(f"unknown stroke kind {k!r}")


def registry():
    """The whole display registry as plain data — the thing QML needs, as Python.

    Separated from its serialisation so a CHECK can compare this against what the
    QML carries without re-parsing JavaScript. `as_qml_js` is then a one-line read
    of this, and the two cannot drift."""
    seg_geom = {k: list(_seg_endpoints(_seg.GEOM22[k])) for k in _seg.SEG22}

    seg_glyphs = {}
    for fmt in ("7", "9", "14", "16", "22"):
        if fmt not in _seg.FORMATS:
            continue
        table = {}
        for tbl in (_seg.DIGITS16, _seg.LETTERS16, _seg.SYMBOLS16):
            for ch, segs in tbl.items():
                g = set(segs.split()) if segs else set()
                table[ch] = sorted(_seg.project(g, fmt)) if g else []
        if fmt == "22":
            # the lowercase are 22-seg glyphs only (⊕SEG22-DESCENDERS): a 22-seg
            # surface renders text, and at any coarser format they fold to upper
            for ch, segs in _seg.LETTERS22.items():
                table[ch] = sorted(set(segs.split()))
        seg_glyphs[fmt] = table

    displays = {}
    for key, d in DISPLAYS.items():
        entry = {"kind": d.kind, "cell": list(d.cell_aspect())}
        if d.kind == "segment":
            entry["fmt"] = d.fmt
        else:
            entry["cols"], entry["rows"] = d.cols, d.rows
            # ⚑ the table a display READS is named by the display, not assumed:
            # every matrix display said "5x7" here, so the 5x8 display was
            # emitted pointing at a font with no row 7 (found wiring the marquee
            # to 5x8, ⊕MATRIX-FONT-INPUT, session 77)
            entry["font"] = f"{d.cols}x{d.rows}"
            if d.baseline is not None:
                entry["baseline"] = d.baseline
        displays[key] = entry

    return {
        "segGeom": seg_geom,
        "segGlyphs": seg_glyphs,
        "font5x7": {ch: list(cols) for ch, cols in FONT5x7.items()},
        "font5x8": {ch: list(cols) for ch, cols in FONT5x8.items()},
        "displays": displays,
        "lattice": list(LATTICE_ORDER),
    }


# ⚑ ⊕MATRIX-FONT-INPUT — the charset a ticker must be able to show, and the
# font it is rasterised from.  Notification text is arbitrary; the authored
# table is 70 glyphs. The extension covers printable Latin-1 (ASCII 0x20-0x7E
# and 0xA0-0xFF) from an OUTLINE FONT resolved at BUILD time — the emission is
# deterministic for a given font, and the font is a recorded build input
# (make_notify_marquee.matrix_font), not whatever fc-match says on the host.
# Authored glyphs WIN: the extension fills only what the table lacks, so a
# designed 'A' is never replaced by a rasterised one. Anything outside the
# charset falls back to '?' in the QML — the log's fallback (:4534).
MATRIX_CHARSET = "".join(chr(c) for c in range(0x20, 0x7F)) + "".join(chr(c) for c in range(0xA0, 0x100))


def font_extension(path, cols=5, rows=8, baseline=FONT5x8_BASELINE, charset=MATRIX_CHARSET,
                   exclude=None):
    """{ch: column bytes} rasterised from `path` for every char in `charset` that
    is not in `exclude` and that the font has. Chars the font lacks are simply
    absent (the QML's '?' fallback handles them); a glyph that rasterises blank
    is DROPPED rather than shipped as an invisible cell."""
    import make_glyph_ink as GI
    exclude = exclude or {}
    out = {}
    for ch in charset:
        if ch in exclude:
            continue
        cb = GI.matrix_glyph(path, ch, cols=cols, rows=rows, baseline=baseline)
        if cb is None or (not any(cb) and ch != " "):
            continue
        out[ch] = cb
    return out


def registry_for(*keys, font_path=None):
    """The registry restricted to the displays a surface actually instantiates.

    ⚑ "ONE SOURCE" IS NOT "EVERY TABLE IN EVERY SURFACE".  Emitting the whole
    registry into the marquee shipped all five segment formats — 48 glyphs each,
    ~9KB — into a DOT-MATRIX widget that reads none of them. That is not
    single-sourcing; it is a surface carrying tables it cannot use, which is the
    same weight the silo had with none of the locality.

    The single-source property is that a surface never SPELLS a table. Taking
    only the displays it names preserves that exactly, and a surface asking for a
    display the registry lacks is a REFUSAL rather than a silently empty cell."""
    r = registry()
    unknown = [k for k in keys if k not in r["displays"]]
    if unknown:
        raise KeyError(f"no such display(s): {unknown}; have {sorted(r['displays'])}")
    displays = {k: r["displays"][k] for k in keys}
    kinds = {d["kind"] for d in displays.values()}
    out = {"displays": displays, "lattice": r["lattice"]}
    if "segment" in kinds:
        out["segGeom"] = r["segGeom"]
        # only the formats the requested segment displays actually project to
        fmts = {d["fmt"] for d in displays.values() if d["kind"] == "segment"}
        out["segGlyphs"] = {f: r["segGlyphs"][f] for f in sorted(fmts)}
    if "matrix" in kinds:
        # only the fonts the requested matrix displays NAME
        for fname in sorted({d["font"] for d in displays.values() if d["kind"] == "matrix"}):
            out[f"font{fname}"] = dict(r[f"font{fname}"])
        # ⊕MATRIX-FONT-INPUT: the rasterised extension goes under the authored
        # table it extends — authored glyphs win, the font fills the rest
        if font_path and "font5x8" in out:
            ext = font_extension(font_path, exclude=out["font5x8"])
            out["font5x8"] = {**ext, **out["font5x8"]}
            out["fontExtension"] = {"path": os.path.basename(font_path), "glyphs": len(ext)}
    return out


def as_qml_js(*keys, indent=None, font_path=None):
    """The registry as a QML/JS object literal — ONE source, nothing retyped.

    ⚑ THE POINT IS THAT A SURFACE NEVER SPELLS A TABLE.  make_wallpaper_live
    carried its own seven-seg map and stroke table inside a QML string, and
    check_geometry_source could not see them because they were not module-level
    assignments. A surface that reads this cannot hold a private shape, because
    there is nothing left for it to hold.

    With no keys this emits everything, which is what a surface offering the full
    display picker needs; with keys it emits only those displays' tables."""
    import json as _json
    data = registry_for(*keys, font_path=font_path) if keys else registry()
    return _json.dumps(data, sort_keys=True, indent=indent)


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
    r = registry()
    print("\nregistry (⊕DOT-WIRE), as QML would receive it:")
    print(f"  segGeom   : {len(r['segGeom'])} strokes")
    print(f"  segGlyphs : {', '.join(f'{k}={len(v)}' for k, v in sorted(r['segGlyphs'].items()))}")
    print(f"  font5x7   : {len(r['font5x7'])} glyphs")
    kinds = ", ".join(f"{k}({v['kind']})" for k, v in sorted(r["displays"].items()))
    print(f"  displays  : {kinds}")
    print(f"  as_qml_js : {len(as_qml_js())} bytes")
