#!/usr/bin/env python3
"""check_symmetry.py — the display checked against its own mirrors, to LOCATE
defects (W57).

Operator, 2026-09-22, photographing a clock digit whose top-left corner notches
while the bottom-left is clean: "that should have been symmetrical! That gives
us another tool: planes of symmetry." And, on what the tool is for: "we don't
expect it to match exactly in this case. We expect it to fix defects."

⚑ SO THIS IS AN INSTRUMENT, NOT A THRESHOLD. A seven-segment 8 is invariant
under a horizontal mirror and a vertical one (the lattice pairs A/D, B/C, F/E
and fixes G); 0 likewise; 00:00 is a palindrome of self-mirror glyphs, so the
whole FACE mirrors horizontally. An antialiased render will never equal its
mirror to the byte, and saying so is not the finding — WHERE it disagrees is.
Every asymmetry is reported as a region with its magnitude and the SEGMENT it
falls in, so the output names what to fix rather than grading the picture.

    glyph   one cell, cropped from the face   -> the DISPLAY's geometry
    face    the whole surface at 00:00        -> the MOUNT: kerning, colon centring

    scripts/check_symmetry.py             # every case: the located asymmetries
    scripts/check_symmetry.py --json      # the measurement
    scripts/check_symmetry.py --selftest  # the locator can see a planted defect

WEAKNESS: a defect symmetric in BOTH planes is invisible (a segment inset
equally at all four corners reads clean); the mirror is about the picture's own
centre, so for the FACE scope an off-centre face reports the offset — which is
the point there, and a caveat for the GLYPH scope; and a region is attributed to
the segment whose rectangle it most overlaps, which for a corner defect names one
of the two segments that meet there, not both.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
VARIANT = "EL-Openglo"
NOISE = 12          # a channel delta at or under this is the toolkit's antialiasing


def mirror_points(im, axis):
    """[(x, y, delta)] where the picture disagrees with its mirror by more than
    the antialiasing noise. The mirror is about the picture's own centre."""
    from PIL import ImageOps
    m = ImageOps.mirror(im) if axis == "h" else ImageOps.flip(im)
    a, b = im.load(), m.load()
    out = []
    for y in range(im.height):
        for x in range(im.width):
            p, q = a[x, y], b[x, y]
            d = max(abs(p[i] - q[i]) for i in range(3))
            if d > NOISE:
                out.append((x, y, d))
    return out


def regions(points, gap=3):
    """Cluster the disagreeing points into regions (a simple grid-flood), each
    with its bounding box, count and worst delta — one region per defect, so the
    report names places rather than pixels."""
    todo = {(x, y): d for x, y, d in points}
    out = []
    while todo:
        (sx, sy), _ = next(iter(todo.items()))
        stack, seen = [(sx, sy)], []
        del todo[(sx, sy)]
        while stack:
            x, y = stack.pop()
            seen.append((x, y))
            for dx in range(-gap, gap + 1):
                for dy in range(-gap, gap + 1):
                    k = (x + dx, y + dy)
                    if k in todo:
                        del todo[k]
                        stack.append(k)
        xs = [p[0] for p in seen]
        ys = [p[1] for p in seen]
        worst = max(d for (x, y, d) in points if (x, y) in set(seen))
        out.append({"box": [min(xs), min(ys), max(xs) + 1, max(ys) + 1],
                    "pixels": len(seen), "worst": worst})
    return sorted(out, key=lambda r: -r["pixels"])


def place_of(box, w, h):
    """WHERE in the cell (or face) a region sits, as a name any reader can check
    against the picture: the third it falls in, vertically and horizontally.

    ⚑ NOT THE SEGMENT ID (s134). The first version predicted each segment's
    rectangle from the substrate's table and named the overlapping one — and it
    reported a region at the cell's RIGHT edge as "segment A", the top bar,
    because the crop starts at the lit content's bounding box (bloom halo
    included) and the prediction did not carry that offset. A name derived from
    the region's own coordinates cannot be wrong that way; the segment it belongs
    to is then one look at the picture, or the regression W57 still owes."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    col = "left" if cx < w / 3 else ("right" if cx > 2 * w / 3 else "centre")
    row = "upper" if cy < h / 3 else ("lower" if cy > 2 * h / 3 else "middle")
    return f"{row}-{col}"


def render_face(text, out_png, w=420, h=120, variant=VARIANT):
    """The clock's mount showing `text`. ⚑ THE TIME IS PINNED: the mount reads the
    clock, and a symmetry instrument cannot depend on what minute it is."""
    import re
    import render_qml as RQ
    import make_clock as MC
    import make_taskswitch as TS
    import templates.loader as TL
    qml = TL.render("clock-main.qml", tables=MC.qml_tables(), ghostAlpha=TS.ghost_alpha(),
                    **MC._metrics_holes())
    qml, n = re.subn(r"root\.timeStr = s;", f'root.timeStr = "{text}";', qml)
    if n != 1:
        raise RuntimeError("the clock's time assignment moved; the symmetry probe cannot pin it")
    for pat, rep in RQ.SUBSTITUTIONS:
        qml = re.sub(pat, rep, qml, flags=re.M)
    cfg = RQ._kcfg_defaults(MC.CONFIG_XML)
    cfg["blinkColon"] = False          # a blinking colon is not an asymmetry
    return RQ.render_document(qml, variant, w, h, out_png, cfg, None, True, RQ.companions("clock"))


CASES = (
    ("glyph-8", "glyph", "8888", ("h", "v")),
    ("glyph-0", "glyph", "0000", ("h", "v")),
    ("face-0000", "face", "0000", ("h",)),
)
# the matrix board is checked for the OTHER symmetry a display owes: its pips are
# hardware, so the grid is invariant under translation by one pitch (W59: a pip is
# a segment). Measured through the marquee harness, which is its only renderer.
GRIDS = (("marquee-field", "EL-Amber"),)


def grid_regularity(im, ground=None):
    """The pip grid's own regularity, read from a picture (W57 on the matrix; the
    operator caught this twice by eye). A board's LEDs sit on ONE pitch, so the
    gaps between the columns that carry any pip must all be equal — and so must
    the pips' widths. Returns the distinct column-run widths and the distinct gaps
    between them; one of each is a regular grid."""
    px = im.load()
    if ground is None:
        ground = max(im.getcolors(im.width * im.height))[1]
    on = [any(px[x, y] != ground for y in range(im.height)) for x in range(im.width)]
    runs, gaps, start, last_end = [], [], None, None
    for x, v in enumerate(on + [False]):
        if v and start is None:
            start = x
            if last_end is not None:
                gaps.append(x - last_end)
        elif not v and start is not None:
            runs.append(x - start)
            last_end, start = x, None
    # the first and last runs may be clipped by the picture's edge
    body = runs[1:-1] if len(runs) > 2 else runs
    return {"pip_widths": sorted(set(body)), "gaps": sorted(set(gaps)),
            "columns": len(runs), "regular": len(set(body)) <= 1 and len(set(gaps)) <= 1}


def _cell_box(im):
    """The first lit cell's bounding box, read from the picture."""
    px = im.load()
    ground = max(im.getcolors(im.width * im.height))[1]
    cols = [any(px[x, y] != ground for y in range(im.height)) for x in range(im.width)]
    runs, start = [], None
    for x, on in enumerate(cols + [False]):
        if on and start is None:
            start = x
        elif not on and start is not None:
            runs.append((start, x))
            start = None
    if not runs:
        return (0, 0, im.width, im.height)
    x0, x1 = runs[0]
    rows = [any(px[x, y] != ground for x in range(x0, x1)) for y in range(im.height)]
    ys = [y for y, on in enumerate(rows) if on]
    return (x0, min(ys), x1, max(ys) + 1)


def measure(cases=CASES, variant=VARIANT):
    import render_qml as RQ
    from PIL import Image
    rows = []
    for label, scope, text, planes in cases:
        row = {"label": label, "scope": scope, "text": text, "variant": variant}
        if not os.path.exists(RQ.QML):
            row["withheld"] = f"{RQ.QML} is not installed"
            rows.append(row)
            continue
        with tempfile.TemporaryDirectory() as td:
            png = os.path.join(td, "face.png")
            rc, err = render_face(text, png, variant=variant)
            if rc != 0 or not os.path.isfile(png):
                row["withheld"] = f"render failed: {err[-200:]}"
                rows.append(row)
                continue
            im = Image.open(png).convert("RGB")
            if scope == "glyph":
                im = im.crop(_cell_box(im))
            row["size"] = [im.width, im.height]
            row["planes"] = {}
            for p in planes:
                pts = mirror_points(im, p)
                regs = regions(pts)
                for r in regs:
                    r["where"] = place_of(r["box"], im.width, im.height)
                row["planes"][p] = {"regions": regs, "pixels": len(pts)}
        rows.append(row)
    return {"cases": rows, "grids": grid_cases(), "noise": NOISE}


def grid_cases(grids=GRIDS):
    """The matrix board's grid regularity, per variant, through its own renderer."""
    from PIL import Image
    import check_marquee_live as ML
    out = []
    for label, variant in grids:
        row = {"label": label, "variant": variant}
        if not os.path.isfile(ML.QML):
            row["withheld"] = f"{ML.QML} is not installed"
        else:
            with tempfile.TemporaryDirectory() as td:
                png = os.path.join(td, "board.png")
                ML.screenshot(variant, png, os.path.join(td, "paused.png"))
                if os.path.isfile(png):
                    row.update(grid_regularity(Image.open(png).convert("RGB")))
                else:
                    row["withheld"] = "the marquee harness produced no picture"
        out.append(row)
    return out


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_symmetry: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    found = 0
    for r in m["cases"]:
        if "withheld" in r:
            print(f"  {r['label']:12s} WITHHELD {r['withheld']}")
            continue
        for p, d in r["planes"].items():
            if not d["regions"]:
                print(f"  {r['label']:12s} {p}: symmetric (nothing over the {m['noise']} noise floor)")
                continue
            print(f"  {r['label']:12s} {p}: {len(d['regions'])} asymmetric region(s), {d['pixels']} px")
            for reg in d["regions"][:6]:
                found += 1
                print(f"        {reg['where']:13s} box {reg['box']}  {reg['pixels']} px  worst {reg['worst']}")
    # ⚑ TWO KINDS OF FINDING, AND ONLY ONE IS A VERDICT. The mirror regions are
    # DIAGNOSTIC — the operator: "we don't expect it to match exactly, we expect
    # it to fix defects" — so they are reported and never fail the run. The GRID
    # is a claim that can be false: a board's pips sit on one pitch or they do
    # not, and @GRID-REGULAR cites this exit status.
    irregular = [g for g in m["grids"] if not g.get("withheld") and not g["regular"]]
    for g in m["grids"]:
        if g.get("withheld"):
            print(f"  {g['label']:12s} WITHHELD {g['withheld']}")
            continue
        state = "regular" if g["regular"] else "IRREGULAR"
        print(f"  {g['label']:12s} grid: {state} — {g['columns']} columns, "
              f"pip widths {g['pip_widths']}, gaps {g['gaps']}")
    print(f"check_symmetry: {found} located asymmetr{'y' if found == 1 else 'ies'} to fix (diagnostic); "
          f"{len(m['grids']) - len(irregular)} of {len(m['grids'])} matrix grid(s) sit on one pitch")
    if irregular:
        for g in irregular:
            print(f"check_symmetry: REFUSED — {g['label']} pip widths {g['pip_widths']}, "
                  f"gaps {g['gaps']}: the grid is not one pitch", file=sys.stderr)
        return 1
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    from PIL import Image
    im = Image.new("RGB", (21, 21), (0, 0, 0))
    for x in range(6, 15):
        for y in range(6, 15):
            im.putpixel((x, y), (255, 255, 255))
    chk("a symmetric block has no asymmetry over the noise floor", mirror_points(im, "h"), [])
    chk("...in either plane", mirror_points(im, "v"), [])
    # ⚑ THE LOCATOR CAN SEE: a planted notch reports ITS OWN place, not a count
    im.putpixel((6, 6), (0, 0, 0))                  # bite the top-left corner
    regs = regions(mirror_points(im, "h"))
    # ⚑ A MIRROR DIFFERENCE ALWAYS APPEARS TWICE — at the defect and at the place
    # it should have matched. That pair IS the report: one box is the notch, the
    # other is the clean corner it disagrees with.
    chk("a planted corner notch reports the notch AND its mirror", len(regs), 2)
    chk("...one of them at the notch", [6, 6, 7, 7] in [r["box"] for r in regs], True)
    chk("...the other at its mirror", [14, 6, 15, 7] in [r["box"] for r in regs], True)
    chk("a difference at or under the noise floor is not reported",
        mirror_points(Image.new("RGB", (4, 4), (10, 10, 10)), "h"), [])
    im2 = Image.new("RGB", (40, 10), (0, 0, 0))
    for x in list(range(4, 10)) + list(range(20, 26)):
        im2.putpixel((x, 5), (255, 255, 255))
    chk("the glyph box is the FIRST cell, not the whole face", _cell_box(im2), (4, 5, 10, 6))
    chk("a region names where it sits, from its own coordinates",
        (place_of([0, 0, 10, 10], 90, 90), place_of([80, 80, 90, 90], 90, 90)),
        ("upper-left", "lower-right"))
    # ⚑ THE GRID CHECK CAN SEE WHAT THE OPERATOR SAW: an integer pitch is regular,
    # a fractional one rounded per-pip alternates its gaps
    even = Image.new("RGB", (40, 8), (0, 0, 0))
    for c in range(8):
        for dx in range(3):
            even.putpixel((c * 4 + dx, 4), (255, 255, 255))
    chk("an integer pitch is regular", grid_regularity(even)["regular"], True)
    odd = Image.new("RGB", (40, 8), (0, 0, 0))
    for c in range(8):
        x = round(c * 4.5)
        for dx in range(3):
            if x + dx < 40:
                odd.putpixel((x + dx, 4), (255, 255, 255))
    g = grid_regularity(odd)
    chk("a fractional pitch is not", g["regular"], False)
    chk("...and the gaps it reports are the uneven ones", len(g["gaps"]) > 1, True)
    print("check_symmetry selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
