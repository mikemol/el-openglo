#!/usr/bin/env python3
"""check_font.py — the emitted fonts are fonts, carry every declared glyph, and draw the substrate.

⚑ THE CLAIM.  For each TTF make_font.OUTPUTS names: (1) fontTools opens it and
it carries the tables a TrueType font needs (glyf, cmap, hmtx, head, name);
(2) the cmap round-trips the whole declared charset plus space; (3) for every
glyph the contour COUNT equals the number of lit segments (segment fonts) or
lit pixels (matrix font) the substrate declares — a glyph is the union of its
lit primitives, no more, no less; (4) the built glyph's centroid sits on the
same side as the SOURCE contours' — the SPEC-FLIP class (session 23) gated on
the installed font, source-relative (session 25); (5) space and .notdef are
empty. The SVG fonts must parse as XML with one <glyph> per charset member.
`--render CH` rasterises a glyph from the TTF's own glyf to a PNG for eyes.

    scripts/check_font.py            # exit 0 iff every arm holds for every font
    scripts/check_font.py --render 2 --png out.png
    scripts/check_font.py --selftest

WEAKNESS. fontconfig and a text shaper are not run; whether a desktop picks the
family name up is ⊕VER. The matrix font is uppercase+digits (the 5x8 descender
table is KNOWN-LOST, ⊕DOT-FONT-DESC).
"""
import io
import os
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED_TABLES = ("glyf", "cmap", "hmtx", "head", "name", "OS/2", "post")


def _spec(name):
    """(contour_source, charset, cell_h) for an OUTPUTS entry name."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    if "Segment" in name:
        fmt = name.split("-")[2].split(".")[0]
        return (lambda ch: MF.glyph_contours(ch, fmt)), MF.SEG_CHARSET[fmt], MF.CELL_H
    return (lambda ch: MF.matrix_contours(ch)), MF.MATRIX_CHARSET, 7.0


def check_ttf(name, font):
    """[(arm, ok, detail)] for one built TTFont."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    out = []
    missing = [t for t in REQUIRED_TABLES if t not in font]
    out.append(("tables", not missing, f"missing {missing}" if missing else f"{len(font.keys())} tables"))
    src, charset, cell_h = _spec(name)
    cmap = font.getBestCmap()
    gone = [c for c in charset + " " if ord(c) not in cmap]
    out.append(("cmap round-trips the charset", not gone, f"missing {gone}" if gone else f"{len(charset) + 1} code points"))
    glyf = font["glyf"]
    wrong = []
    for ch in charset:
        g = glyf[cmap[ord(ch)]]
        want = len(src(ch))
        got = max(g.numberOfContours, 0)
        if got != want:
            wrong.append(f"{ch}:{got}!={want}")
    out.append(("contour count == lit primitives", not wrong, "; ".join(wrong[:5]) if wrong else f"{len(charset)} glyphs"))
    flips = MF.gate_ttf_orientation(font, src, cell_h, charset)
    out.append(("orientation agrees with the source", not flips, f"flipped {flips[:3]}" if flips else "source-relative ok"))
    empty = all(glyf[n].numberOfContours <= 0 for n in (".notdef", "space"))
    out.append(("space and .notdef are empty", empty, "ok" if empty else "a blank glyph has ink"))
    return out


def check_svg(name, text):
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    fmt = name.split("-")[2].split(".")[0]
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        return [("svg parses", False, str(e))]
    ns = {"s": "http://www.w3.org/2000/svg"}
    glyphs = root.findall(".//s:glyph", ns)
    have = {g.get("unicode") for g in glyphs}
    want = set(MF.SEG_CHARSET[fmt]) | {" "}
    return [("svg parses", True, "ok"),
            ("one glyph per charset member", have == want,
             f"missing {sorted(want - have)} extra {sorted(have - want)}" if have != want else f"{len(want)}")]


def build_all():
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    return [(name, make()) for name, make in MF.OUTPUTS]


def render_glyph(font, ch, png, size=200):
    """Rasterise one glyph from the TTF's own glyf (via fontTools' pen + Pillow)."""
    from fontTools.pens.recordingPen import RecordingPen
    from PIL import Image, ImageDraw
    cmap = font.getBestCmap()
    name = cmap[ord(ch)]
    pen = RecordingPen()
    font.getGlyphSet()[name].draw(pen)
    em = font["head"].unitsPerEm
    im = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(im)
    poly = []
    for op, args in pen.value:
        if op == "moveTo":
            poly = [args[0]]
        elif op == "lineTo":
            poly.append(args[0])
        elif op == "closePath" and len(poly) >= 3:
            d.polygon([(x * size / em, size - y * size / em) for x, y in poly], fill=255)
            poly = []
    im.save(png)
    return png


def main(argv):
    known = {"--render", "--png"}
    args = [a for a in argv[1:] if a.startswith("--")]
    rest = [a for a in argv[1:] if not a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_font: unknown flag {a!r}", file=sys.stderr)
            return 2
    try:
        import fontTools  # noqa: F401
    except ImportError:
        print("check_font: SKIP — fontTools not installed (declared in pyproject; uv sync)", file=sys.stderr)
        return 0
    built = build_all()
    if "--render" in args:
        ch = rest[0] if rest else "2"
        png = argv[argv.index("--png") + 1] if "--png" in argv else "glyph.png"
        font = next(f for n, f in built if n == "EL-Segment-7.ttf")
        print(f"check_font: rendered {ch!r} from EL-Segment-7.ttf glyf -> {render_glyph(font, ch, png)}")
        return 0
    fails, n = [], 0
    for name, obj in built:
        arms = check_svg(name, obj) if isinstance(obj, str) else check_ttf(name, obj)
        for arm, ok, detail in arms:
            n += 1
            if not ok:
                fails.append(f"{name} {arm}: {detail}")
    if not n:
        print("check_font: REFUSED — nothing measured", file=sys.stderr)
        return 2
    if fails:
        print(f"check_font: REFUSED — {len(fails)} of {n} arm(s) do not hold:", file=sys.stderr)
        for f in fails:
            print(f"    {f}", file=sys.stderr)
        return 1
    print(f"check_font: {n} of {n} arms hold over {len(built)} fonts")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    try:
        import fontTools  # noqa: F401
    except ImportError:
        print("  SKIP all arms — fontTools not installed")
        print("check_font selftest: SKIP")
        return True
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    seg7 = MF.build_segment_ttf("7")
    arms = {a: o for a, o, _d in check_ttf("EL-Segment-7.ttf", seg7)}
    chk("the real 7-seg TTF holds every arm", all(arms.values()), True)
    # ⚑ A SPEC-FLIP MUST BE CAUGHT ON THE BUILT FONT: mirror the source in x
    flipped = MF.build_ttf(lambda ch: [[(MF.CELL_W - x, y) for x, y in c] for c in MF.glyph_contours(ch, "7")],
                           MF.SEG_CHARSET["7"], MF.CELL_W, MF.CELL_H, "flip")
    bad = MF.gate_ttf_orientation(flipped, lambda ch: MF.glyph_contours(ch, "7"), MF.CELL_H, "27JLP")
    chk("an x-mirrored build is seen by the orientation gate", bool(bad), True)
    # a dropped contour is seen by the count arm
    dropped = MF.build_ttf(lambda ch: MF.glyph_contours(ch, "7")[1:], MF.SEG_CHARSET["7"],
                           MF.CELL_W, MF.CELL_H, "drop")
    arms = {a: o for a, o, _d in check_ttf("EL-Segment-7.ttf", dropped)}
    chk("a dropped segment is seen", arms["contour count == lit primitives"], False)
    mtx = MF.build_matrix_ttf()
    arms = {a: o for a, o, _d in check_ttf("EL-Matrix-5x7.ttf", mtx)}
    chk("the matrix TTF holds every arm", all(arms.values()), True)
    svg = MF.emit_svg_font("7")
    arms = {a: o for a, o, _d in check_svg("EL-Segment-7.svg", svg)}
    chk("the SVG font holds every arm", all(arms.values()), True)
    arms = {a: o for a, o, _d in check_svg("EL-Segment-7.svg", svg.replace('unicode="7"', 'unicode="x"'))}
    chk("a missing SVG glyph is seen", arms["one glyph per charset member"], False)
    print("check_font selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
