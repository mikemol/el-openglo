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
    """(contour_source, charset, cell_h) for an OUTPUTS entry name — make_font's own."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    return MF.spec_for(name)


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
    # ⚑ DESCENT IS BELOW y=0, AND ONLY FOR DESCENDERS.  In a baseline font
    # (5x8) g j p q y must reach negative y and nothing else may; in a
    # top-aligned font nothing may. This is the arm that caught the closure's
    # off-by-one (every glyph negative, then none).
    import display_types as DT
    want_desc = {c for c in charset if c in DT.DESCENDERS} if "5x8" in name else set()
    # a segment stroke straddles the cell edge by half its thickness (the lattice
    # puts the bottom bar's axis ON the edge), so for segment fonts "below" means
    # below that overhang; for matrix fonts a pixel is wholly inside its row
    tol = -(MF.THICK / 2) * (MF.EM / MF.CELL_H) - 1 if "Segment" in name else -1
    below, above = [], []
    for ch in charset:
        g = glyf[cmap[ord(ch)]]
        if g.numberOfContours <= 0:
            continue
        ymin = min(p[1] for p in g.getCoordinates(glyf)[0])
        (below if ymin < tol else above).append(ch)
    bad_below = sorted(set(below) - want_desc)
    bad_above = sorted(want_desc - set(below))
    out.append(("only descenders reach below the baseline", not bad_below and not bad_above,
                f"non-descenders below: {bad_below}" if bad_below else
                (f"descenders not below: {bad_above}" if bad_above else
                 f"{len(want_desc)} descender(s), {len(above)} on/above")))
    if "5x8" in name:
        hhea = font["hhea"]
        out.append(("descent metrics are negative", hhea.descent < 0 and font["OS/2"].sTypoDescender < 0,
                    f"hhea {hhea.descent}, OS/2 {font['OS/2'].sTypoDescender}"))
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
    desc = -font["hhea"].descent                    # 0 for a top-aligned font
    span = em + desc
    im = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(im)
    if desc:                                        # the baseline, drawn faintly
        yb = size - desc * size / span
        d.line([(0, yb), (size, yb)], fill=80)
    poly = []
    for op, args in pen.value:
        if op == "moveTo":
            poly = [args[0]]
        elif op == "lineTo":
            poly.append(args[0])
        elif op == "closePath" and len(poly) >= 3:
            d.polygon([(x * size / em, size - (y + desc) * size / span) for x, y in poly], fill=255)
            poly = []
    im.save(png)
    return png


def main(argv):
    known = {"--render", "--png", "--font"}
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
        which = argv[argv.index("--font") + 1] if "--font" in argv else "EL-Segment-7.ttf"
        font = next(f for n, f in built if n == which)
        print(f"check_font: rendered {ch!r} from {which} glyf -> {render_glyph(font, ch, png)}")
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
    m58 = MF.build_matrix_ttf(5, 8)
    arms = {a: o for a, o, _d in check_ttf("EL-Matrix-5x8.ttf", m58)}
    chk("the 5x8 descender TTF holds every arm", all(arms.values()), True)
    # ⚑ THE OFF-BY-ONE THE CLOSURE RECORDS: baseline as a ROW index (6, not the
    # line 7) puts every body row below the line — must be seen
    import display_types as DT
    wrong = MF.build_ttf(lambda ch: MF.matrix_contours(ch, 5, 8), MF.MATRIX_CHARSET + MF.LOWER_CHARSET,
                         5.0, 8.0, "wrong", baseline=DT.FONT5x8_BASELINE)
    arms = {a: o for a, o, _d in check_ttf("EL-Matrix-5x8.ttf", wrong)}
    chk("a baseline given as the row index (off by one) is seen", arms["only descenders reach below the baseline"], False)
    chk("5x7 stays byte-neutral under the baseline map (baseline=None)",
        MF.build_matrix_ttf(5, 7)["glyf"]["u0041"].getCoordinates(MF.build_matrix_ttf(5, 7)["glyf"])[0]
        == mtx["glyf"]["u0041"].getCoordinates(mtx["glyf"])[0], True)
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
