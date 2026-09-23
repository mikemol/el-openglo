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

    scripts/check_font.py            # the verdict, as opa_gate font decides it
    scripts/check_font.py --json     # the measurement (per-font facts) policy/font.rego decides
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
    """The FACTS for one built TTFont — what was measured, never whether it is
    acceptable (policy/font.rego decides that, W50): the required tables it
    lacks, the charset code points its cmap lacks, the glyphs whose contour
    count differs from the substrate's lit primitives, the glyphs the
    orientation gate reports flipped, the blank glyphs that carry ink, the
    glyphs reaching below the baseline beside the declared descenders, and (5x8)
    the descent metrics."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    src, charset, cell_h = _spec(name)
    cmap = font.getBestCmap()
    glyf = font["glyf"]
    wrong = []
    for ch in charset:
        if ord(ch) not in cmap:
            continue
        g = glyf[cmap[ord(ch)]]
        want = len(src(ch))
        got = max(g.numberOfContours, 0)
        if got != want:
            wrong.append({"glyph": ch, "contours": got, "primitives": want})
    facts = {"kind": "ttf", "font": name, "charset": charset,
             "tables_missing": [t for t in REQUIRED_TABLES if t not in font],
             "cmap_missing": [c for c in charset + " " if ord(c) not in cmap],
             "contour_mismatch": wrong,
             "flipped": [str(f) for f in MF.gate_ttf_orientation(font, src, cell_h, charset)],
             "blank_inked": [n for n in (".notdef", "space") if glyf[n].numberOfContours > 0]}
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
    below = []
    for ch in charset:
        if ord(ch) not in cmap:
            continue
        g = glyf[cmap[ord(ch)]]
        if g.numberOfContours <= 0:
            continue
        ymin = min(p[1] for p in g.getCoordinates(glyf)[0])
        if ymin < tol:
            below.append(ch)
    facts["below_baseline"] = sorted(below)
    facts["descenders"] = sorted(want_desc)
    # the baseline font (5x8) declares a descent; the top-aligned ones do not
    facts["descent"] = ({"hhea": font["hhea"].descent, "os2": font["OS/2"].sTypoDescender}
                        if "5x8" in name else None)
    return facts


def check_svg(name, text):
    """The FACTS for one SVG font: its parse error, or the charset members it
    lacks and the glyphs it carries beyond them."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_font as MF
    fmt = name.split("-")[2].split(".")[0]
    facts = {"kind": "svg", "font": name, "parse_error": None, "missing": [], "extra": []}
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        facts["parse_error"] = str(e)
        return facts
    ns = {"s": "http://www.w3.org/2000/svg"}
    have = {g.get("unicode") for g in root.findall(".//s:glyph", ns)}
    want = set(MF.SEG_CHARSET[fmt]) | {" "}
    facts["missing"], facts["extra"] = sorted(want - have), sorted(h or "" for h in have - want)
    return facts


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


def measure():
    """The MEASUREMENT policy/font.rego decides: one case per make_font.OUTPUTS
    entry, carrying check_ttf / check_svg's facts. fontTools absent is a fact
    about the HOST: no cases, and `withheld` says why (the policy withholds)."""
    try:
        import fontTools  # noqa: F401
    except ImportError:
        return {"cases": [], "withheld": "fontTools not installed (declared in pyproject; uv sync)"}
    cases = []
    for name, obj in build_all():
        facts = check_svg(name, obj) if isinstance(obj, str) else check_ttf(name, obj)
        cases.append(dict(facts, id=name))
    return {"cases": cases, "withheld": None}


def main(argv):
    known = {"--render", "--png", "--font", "--json"}
    args = [a for a in argv[1:] if a.startswith("--")]
    rest = [a for a in argv[1:] if not a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_font: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in args:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--render" not in args:
        import opa_gate
        return opa_gate.gate("font")
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
    # ⚑ THE SELFTEST ASKS WHETHER THE MEASUREMENT SEES; which facts are defects
    # is policy/font_test.rego's ruling (W50). `clean` is the empty-facts shape a
    # sound font measures to — the policy's admit case, read back here only to
    # show the synthetic breakages MOVE a fact off it.
    def clean(f):
        return (not f["tables_missing"] and not f["cmap_missing"] and not f["contour_mismatch"]
                and not f["flipped"] and not f["blank_inked"]
                and set(f["below_baseline"]) == set(f["descenders"]))

    seg7 = MF.build_segment_ttf("7")
    chk("the real 7-seg TTF measures clean", clean(check_ttf("EL-Segment-7.ttf", seg7)), True)
    # ⚑ A SPEC-FLIP MUST BE CAUGHT ON THE BUILT FONT: mirror the source in x
    flipped = MF.build_ttf(lambda ch: [[(MF.CELL_W - x, y) for x, y in c] for c in MF.glyph_contours(ch, "7")],
                           MF.SEG_CHARSET["7"], MF.CELL_W, MF.CELL_H, "flip")
    bad = MF.gate_ttf_orientation(flipped, lambda ch: MF.glyph_contours(ch, "7"), MF.CELL_H, "27JLP")
    chk("an x-mirrored build is seen by the orientation gate", bool(bad), True)
    # a dropped contour is seen by the count arm
    dropped = MF.build_ttf(lambda ch: MF.glyph_contours(ch, "7")[1:], MF.SEG_CHARSET["7"],
                           MF.CELL_W, MF.CELL_H, "drop")
    chk("a dropped segment is seen", bool(check_ttf("EL-Segment-7.ttf", dropped)["contour_mismatch"]), True)
    mtx = MF.build_matrix_ttf()
    chk("the matrix TTF measures clean", clean(check_ttf("EL-Matrix-5x7.ttf", mtx)), True)
    m58 = MF.build_matrix_ttf(5, 8)
    f58 = check_ttf("EL-Matrix-5x8.ttf", m58)
    chk("the 5x8 descender TTF measures clean, with a descent",
        (clean(f58), f58["descent"]["hhea"] < 0), (True, True))
    # ⚑ THE OFF-BY-ONE THE CLOSURE RECORDS: baseline as a ROW index (6, not the
    # line 7) puts every body row below the line — must be seen
    import display_types as DT
    wrong = MF.build_ttf(lambda ch: MF.matrix_contours(ch, 5, 8), MF.MATRIX_CHARSET + MF.LOWER_CHARSET,
                         5.0, 8.0, "wrong", baseline=DT.FONT5x8_BASELINE)
    fw = check_ttf("EL-Matrix-5x8.ttf", wrong)
    chk("a baseline given as the row index (off by one) is seen",
        set(fw["below_baseline"]) != set(fw["descenders"]), True)
    chk("5x7 stays byte-neutral under the baseline map (baseline=None)",
        MF.build_matrix_ttf(5, 7)["glyf"]["u0041"].getCoordinates(MF.build_matrix_ttf(5, 7)["glyf"])[0]
        == mtx["glyf"]["u0041"].getCoordinates(mtx["glyf"])[0], True)
    svg = MF.emit_svg_font("7")
    fs = check_svg("EL-Segment-7.svg", svg)
    chk("the SVG font measures clean", (fs["parse_error"], fs["missing"], fs["extra"]), (None, [], []))
    fs = check_svg("EL-Segment-7.svg", svg.replace('unicode="7"', 'unicode="x"'))
    chk("a missing SVG glyph is seen", (fs["missing"], fs["extra"]), (["7"], ["x"]))
    chk("the real tree measures every OUTPUTS entry",
        len(measure()["cases"]) == len(MF.OUTPUTS) > 0, True)
    print("check_font selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
