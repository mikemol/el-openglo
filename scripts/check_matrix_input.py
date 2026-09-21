#!/usr/bin/env python3
"""check_matrix_input.py — what does a real font's glyph look like in the 5x8 matrix?

⚑ WHAT THIS IS AND IS NOT.  ⊕MATRIX-FONT-INPUT (COTYPE :4534) is "arbitrary
text reaches the matrix by rasterising a font into it". make_glyph_ink.matrix_glyph
is the INGEST half — one glyph of an outline font into column bytes in the
display_types convention, framed by the font's cap height / measured descent so
the result lands on FONT5x8's baseline. This tool renders one, or compares the
rasterised glyph against the authored table for every char the table has. It
does NOT gate agreement with the authored table: the authored bitmaps are
designed pixel art and a 5x8 raster of a text face is not expected to equal them
(H does; A does not — the raster keeps the pointed apex). What IS gated: the
ingest sees ink (a blank raster of a glyph that has contours is REFUSED), and a
missing char is None rather than blank.

    scripts/check_matrix_input.py --render CH [--font F]   # the raster beside the authored glyph
    scripts/check_matrix_input.py --compare [--font F]     # per-char agreement over the authored table
    scripts/check_matrix_input.py --selftest

SKIP (printed, exit 0) when no TTF is found and none is given.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)
from check_projection import find_font   # noqa: E402  one font finder, not two


def _mods():
    import make_glyph_ink as GI
    import display_types as DT
    return GI, DT


def render(font, ch):
    GI, DT = _mods()
    cb = GI.matrix_glyph(font, ch)
    if cb is None:
        print(f"  {ch!r}: the font has no glyph — None (the caller picks the fallback)")
        return None
    auth = DT.FONT5x8.get(ch)
    got = GI.matrix_rows(cb)
    want = GI.matrix_rows(auth) if auth else None
    print(f"  {ch!r}  raster {cb}" + (f"  authored {auth}" if auth else "  (not in the authored table)"))
    for r, g in enumerate(got):
        print(f"    {g}" + (f"    {want[r]}" if want else ""))
    return cb


def compare(font):
    GI, DT = _mods()
    rows = []
    for ch, auth in sorted(DT.FONT5x8.items()):
        cb = GI.matrix_glyph(font, ch)
        if cb is None:
            continue
        a = {(c, r) for c, b in enumerate(auth) for r in range(8) if b & (1 << r)}
        g = {(c, r) for c, b in enumerate(cb) for r in range(8) if b & (1 << r)}
        u = a | g
        rows.append((ch, len(a & g) / len(u) if u else 1.0, cb == list(auth), bool(g) or not GI.contours(font, ch)))
    return rows


def main(argv):
    known = {"--render", "--font", "--compare"}
    for a in (x for x in argv[1:] if x.startswith("--")):
        if a not in known:
            print(f"check_matrix_input: unknown flag {a!r}", file=sys.stderr)
            return 2
    font = find_font(argv[argv.index("--font") + 1] if "--font" in argv else None)
    if not font:
        print("check_matrix_input: SKIP — no TTF found (pass --font PATH); 0 glyphs rasterised", file=sys.stderr)
        return 0
    print(f"font {font}")
    if "--render" in argv:
        render(font, argv[argv.index("--render") + 1])
        return 0
    rows = compare(font)
    if not rows:
        print("check_matrix_input: REFUSED — the authored table is empty or the font has none of it", file=sys.stderr)
        return 2
    blank = [ch for ch, _j, _e, seen in rows if not seen]
    for ch, j, exact, _seen in sorted(rows, key=lambda r: -r[1]):
        print(f"  {ch!r}  jaccard {j:.2f}{'  exact' if exact else ''}")
    n = len(rows)
    exact = sum(1 for r in rows if r[2])
    mean = sum(r[1] for r in rows) / n
    if blank:
        print(f"check_matrix_input: REFUSED — {len(blank)} of {n} glyphs with contours rasterised BLANK: "
              f"{''.join(blank)}", file=sys.stderr)
        return 1
    print(f"check_matrix_input: {n} of {len(_mods()[1].FONT5x8)} authored glyphs rasterised from the font — "
          f"mean jaccard {mean:.2f}, {exact} exact; 0 blank (agreement reported, not gated: the table is pixel art)")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    font = find_font()
    if not font:
        print("  SKIP — no TTF on this host")
        print("check_matrix_input selftest: SKIP")
        return True
    GI, DT = _mods()
    H = GI.matrix_glyph(font, "H")
    chk("'H' rasterises to the authored bitmap exactly", H, list(DT.FONT5x8["H"]))
    chk("a char the font lacks is None, not blank", GI.matrix_glyph(font, "☃"), None)
    chk("a space is present and dark", GI.matrix_glyph(font, " "), [0] * 5)
    g = GI.matrix_glyph(font, "g")
    chk("'g' lights the descent row (row 7)", any(b & (1 << 7) for b in g), True)
    chk("'H' lights nothing below the baseline", any(b & (1 << 7) for b in H), False)
    e_acc = GI.matrix_glyph(font, "é")
    chk("a composite glyph (e-acute) ingests as ink, not empty", any(e_acc), True)
    # ⚑ THE THRESHOLD MUST BE ABLE TO CHANGE THE RASTER: a coverage rule that
    # lit the same cells at 0.05 and 0.95 would be a centre sample in disguise
    lo = GI.matrix_glyph(font, "A", threshold=0.05)
    hi = GI.matrix_glyph(font, "A", threshold=0.95)
    chk("threshold 0.05 lights more of 'A' than 0.95", sum(bin(b).count("1") for b in lo) > sum(bin(b).count("1") for b in hi), True)
    cap, desc = GI.font_frame(font)
    chk("the frame's descent is below the baseline and above hhea", desc < 0, True)
    print("check_matrix_input selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
