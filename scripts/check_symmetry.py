#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
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

    scripts/check_symmetry.py             # the verdict, as opa_gate symmetry decides it (the grid)
    scripts/check_symmetry.py --list      # every case: the located asymmetries (diagnostic)
    scripts/check_symmetry.py --json      # the measurement policy/symmetry.rego decides
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
    # ⚑ NO `regular` HERE (W50): it was `len(set(widths)) <= 1 and len(set(gaps)) <= 1`,
    # which a BLANK board satisfies (no columns, no widths, no gaps). policy/symmetry.rego
    # judges the distinct widths and gaps, and refuses a board with too few columns.
    return {"pip_widths": sorted(set(body)), "gaps": sorted(set(gaps)), "columns": len(runs)}


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


FIT_TOL = 1.0       # px: a segment whose centroid misses the fit by more is the offender


def _unit_centres(segs):
    """{seg: (a, b)} — each segment's centre in segLen units, from (kind, ux, uy)."""
    return {s: ((ux + 0.5, uy) if k == "h" else (ux, uy + 0.5)) for s, (k, ux, uy) in segs.items()}


def _solve3(m, v):
    """Solve the 3x3 system m x = v by Cramer's rule (no numpy dependency)."""
    def det(a):
        return (a[0][0] * (a[1][1] * a[2][2] - a[1][2] * a[2][1])
                - a[0][1] * (a[1][0] * a[2][2] - a[1][2] * a[2][0])
                + a[0][2] * (a[1][0] * a[2][1] - a[1][1] * a[2][0]))
    d = det(m)
    if abs(d) < 1e-12:
        return None
    out = []
    for i in range(3):
        mi = [row[:] for row in m]
        for r in range(3):
            mi[r][i] = v[r]
        out.append(det(mi) / d)
    return out


def segment_fit(im, segs, iters=4):
    """W165: the CONSTRUCTIVE half of the oracle. Fit the rendered segments to the
    substrate's unit coordinates by least squares — cx = ox + L·a, cy = oy + L·b over
    every segment's centroid — and return {seg: residual px} plus the fit. A mirror
    cannot see a defect symmetric in both planes (the WEAKNESS above); a fit to the
    substrate can, and it NAMES the segment.

    Lit core only: a pixel at least half the brightest one's luminance, so the
    bloom halo does not drag a centroid. Each pixel goes to the segment whose line
    is nearest under the current fit, and the fit is re-solved from the centroids.
    WEAKNESS: the first assignment assumes the core's bbox is the digit; a segment
    missing from the render has no centroid and is reported absent, not fitted."""
    px = im.load()
    lum = [[sum(px[x, y][:3]) for x in range(im.width)] for y in range(im.height)]
    peak = max(max(r) for r in lum)
    core = [(x, y) for y in range(im.height) for x in range(im.width) if lum[y][x] * 2 >= peak]
    if not core:
        return None
    uc = _unit_centres(segs)
    xs, ys = [p[0] for p in core], [p[1] for p in core]
    L = (max(ys) - min(ys)) / 2.0
    ox, oy = min(xs) + (max(xs) - min(xs) - L) / 2.0, min(ys)
    cent = {}
    for _ in range(iters):
        acc = {s: [0.0, 0.0, 0] for s in segs}
        for x, y in core:
            best, bd = None, None
            for s, (k, ux, uy) in segs.items():
                x0, y0 = ox + L * ux, oy + L * uy
                x1, y1 = (x0 + L, y0) if k == "h" else (x0, y0 + L)
                tx = min(max(x, min(x0, x1)), max(x0, x1))
                ty = min(max(y, min(y0, y1)), max(y0, y1))
                d = (x - tx) ** 2 + (y - ty) ** 2
                if bd is None or d < bd:
                    best, bd = s, d
            a = acc[best]
            a[0] += x; a[1] += y; a[2] += 1
        cent = {s: (a[0] / a[2], a[1] / a[2]) for s, a in acc.items() if a[2]}
        # normal equations for [ox, oy, L]
        m = [[0.0] * 3 for _ in range(3)]
        v = [0.0] * 3
        for s, (cx, cy) in cent.items():
            a, b = uc[s]
            for row, val in (([1.0, 0.0, a], cx), ([0.0, 1.0, b], cy)):
                for i in range(3):
                    v[i] += row[i] * val
                    for j in range(3):
                        m[i][j] += row[i] * row[j]
        sol = _solve3(m, v)
        if sol is None:
            break
        ox, oy, L = sol
    resid = {s: round(((cx - (ox + L * uc[s][0])) ** 2 + (cy - (oy + L * uc[s][1])) ** 2) ** 0.5, 2)
             for s, (cx, cy) in cent.items()}
    return {"fit": {"ox": round(ox, 2), "oy": round(oy, 2), "segLen": round(L, 2)},
            "residuals": resid, "absent": sorted(set(segs) - set(cent)),
            "offenders": sorted(s for s, r in resid.items() if r > FIT_TOL)}


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
                if text[0] == "8":                   # every segment lit: the fit sees all seven
                    import make_clock as MC
                    row["segment_fit"] = segment_fit(im, MC.SEGS)
            row["size"] = [im.width, im.height]
            row["planes"] = {}
            for p in planes:
                pts = mirror_points(im, p)
                regs = regions(pts)
                for r in regs:
                    r["where"] = place_of(r["box"], im.width, im.height)
                row["planes"][p] = {"regions": regs, "pixels": len(pts)}
        rows.append(row)
    # matrix_cases() is NOT wired yet (W166): on the real held board the core crop
    # took the whole 419x31 board (the hover-pause ring, W51, is lit to the core
    # threshold and spans the width), so its "symmetric" was vacuous
    return {"cases": rows, "grids": grid_cases(), "noise": NOISE}


# W166: the matrix's MIRROR, per glyph. A self-mirror glyph is the app name of one
# injected notification on a HOVERED run, so the board freezes with the text's left
# edge at the board's (a whole-pip offset: the offscreen pointer rests at 0,0). Not a
# mid-scroll still — W60 resamples a fractional offset on purpose — and not a full
# board, whose mirror is only grid_regularity's translation symmetry again.
MATRIX_GLYPHS = (("matrix-H", "H", ("h", "v")), ("matrix-O", "O", ("h",)))
MATRIX_VARIANT = "EL-Amber"
MATRIX_PITCH = 4    # px per pip column: grid_regularity measures pip 3 + gap 1 on this board


def _runs(flags, max_gap):
    """[(start, end)] of True runs, merging runs separated by <= max_gap False."""
    runs, start, last = [], None, None
    for i, on in enumerate(flags):
        if on:
            if start is None:
                start = i
            elif i - last - 1 > max_gap:
                runs.append((start, last + 1))
                start = i
            last = i
    if start is not None:
        runs.append((start, last + 1))
    return runs


def first_glyph_box(im, max_gap=2, ring=False):
    """The FIRST glyph's core box on a matrix board: core pixels are at least half the
    peak luminance (the ghost pips covering the board are excluded); columns within
    a glyph are 1 px pip gaps apart, glyphs a blank pip column apart, so columns are
    grouped by gaps <= max_gap. None when nothing is lit."""
    px = im.load()
    lum = [[sum(px[x, y][:3]) for x in range(im.width)] for y in range(im.height)]
    peak = max(max(r) for r in lum)
    if peak == 0:
        return None
    # ⚑ THE GLYPH IS LIT ABOVE THE GHOST, NOT ABOVE BLACK (W168, measured 2026-10-01):
    # on the real board every ghost pip is above half the peak, so a half-peak core
    # was the whole board in every frame, glyph or none. Lit pips are a small share of
    # all pips, so the MEDIAN pip luminance is the ghost level; the core is what sits
    # above halfway from ghost to peak.
    pip = sorted(v for r in lum for v in r if v * 4 > peak)
    ghost = pip[len(pip) // 2] if pip else 0
    # a board with no ghost level of its own (the median pip IS the peak: only the
    # glyph is lit) keeps the half-peak cut
    cut = (ghost + peak) / 2 if ghost < peak else peak / 2
    core = [[lum[y][x] > cut for x in range(im.width)] for y in range(im.height)]
    # ⚑ THE HOVER RING IS NOT A GLYPH (W166, measured 2026-10-01): held, the board's
    # outer ring of pips pulses (W51) to the core threshold and spans the width, and
    # the first real crop was the whole 419x31 board. Each pip row and pip column is
    # its own band (max_gap 0); with a ring present the outermost band on each side
    # is the ring, so only the interior is grouped.
    if ring:
        rbands = _runs([any(r) for r in core], 0)
        cbands = _runs([any(core[y][x] for y in range(im.height)) for x in range(im.width)], 0)
        if len(rbands) < 3 or len(cbands) < 3:
            return None
        iy0, iy1 = rbands[1][0], rbands[-2][1]
        ix0, ix1 = cbands[1][0], cbands[-2][1]
    else:
        iy0, iy1, ix0, ix1 = 0, im.height, 0, im.width
    cols = [ix0 <= x < ix1 and any(core[y][x] for y in range(iy0, iy1)) for x in range(im.width)]
    runs = _runs(cols, max_gap)
    if not runs:
        return None
    x0, x1 = runs[0]
    rows = [iy0 <= y < iy1 and any(core[y][x] for x in range(x0, x1)) for y in range(im.height)]
    ys = [y for y, on in enumerate(rows) if on]
    return (x0, min(ys), x1, max(ys) + 1)


def matrix_cases(glyphs=MATRIX_GLYPHS, variant=MATRIX_VARIANT):
    """One mirror case per injected glyph, through the marquee's own harness."""
    from PIL import Image
    import check_marquee_live as ML
    out = []
    for label, ch, planes in glyphs:
        row = {"label": label, "scope": "matrix", "text": ch, "variant": variant}
        if not os.path.isfile(ML.QML):
            row["withheld"] = f"{ML.QML} is not installed"
            out.append(row)
            continue
        # ⚑ THE SCROLLING RUN, NOT THE HOVER HOLD (W168, measured 2026-10-01): the held
        # board shows NO text, while a scrolling run carries the glyph across it. A
        # frame at a whole-pip phase crops the full glyph (19 px = 5 pips on the real
        # board); a fractional phase crops less (W60 resampling dims the side
        # columns), and a frame past the board's left edge can merge two glyphs (23 px
        # at x -13, measured). So the frame mirrored is the first whose crop is the
        # MODAL full-height size: the glyph as most whole-pip frames show it.
        with tempfile.TemporaryDirectory() as td:
            probe = matrix_probe(td, ch, variant)
            full = [f for f in probe["frames"] if f["crop_w"] and f["crop_w"] < 100]
            if not full:
                row["withheld"] = f"no frame of {probe['frame_count']} showed the glyph alone"
                out.append(row)
                continue
            dims = [(f["crop"][2] - f["crop"][0], f["crop"][3] - f["crop"][1]) for f in full]
            tall = max(h for _w, h in dims)
            sizes = [d for d in dims if d[1] == tall]
            best = max(set(sizes), key=sizes.count)
            # ...and of those, the one nearest a WHOLE-PIP phase: x on the pitch, so W60's
            # resampling lights both side columns alike (x 381.3 = 1.3 px off read as a
            # 29-level left/right difference that is the resampling, not a defect)
            at = [f for f, d in zip(full, dims) if d == best and f["x"] is not None]
            pitch = MATRIX_PITCH

            def off(f):
                r = f["x"] % pitch
                return min(r, pitch - r)
            pick = min(at, key=off)
            row["glyph_size"], row["frames_at_size"] = list(best), sizes.count(best)
            row["phase_off_px"] = round(off(pick), 2)
            im = Image.open(os.path.join(td, pick["frame"])).convert("RGB").crop(tuple(pick["crop"]))
            row["frame"], row["x"] = pick["frame"], pick["x"]
            row["size"] = [im.width, im.height]
            row["planes"] = {}
            for p in planes:
                pts = mirror_points(im, p)
                regs = regions(pts)
                for r in regs:
                    r["where"] = place_of(r["box"], im.width, im.height)
                row["planes"][p] = {"regions": regs, "pixels": len(pts)}
        out.append(row)
    return out


def matrix_probe(out_dir, ch="H", variant=MATRIX_VARIANT):
    """W168's question as a tool: WHEN is an injected glyph on the board, and at what
    offset? A scrolling run (no hover hold, so no ring) with the harness's frame
    capture into out_dir; per frame its t and x and the first-glyph crop. A frame
    whose crop is about one glyph wide, at a whole-pip x, is the one to mirror."""
    from PIL import Image
    import check_marquee_live as ML
    tl = [(300, "arrive", 1, {"summary": "x", "body": "", "applicationName": ch}, f"{ch}: x")]
    res = ML.run(variant=variant, end_ms=4000, frames=out_dir, timeline=tl) or {}
    names = sorted(n for n in os.listdir(out_dir) if n.startswith("frame-"))
    fx = res.get("frames", [])
    rows = []
    for i, n in enumerate(names):
        im = Image.open(os.path.join(out_dir, n)).convert("RGB")
        box = first_glyph_box(im)
        f = fx[i] if i < len(fx) else {}
        rows.append({"frame": n, "t": f.get("t"), "x": f.get("x"),
                     "crop": list(box) if box else None,
                     "crop_w": (box[2] - box[0]) if box else None})
    return {"frames": rows, "frame_count": len(names), "listed": len(fx)}


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
    known = {"--json", "--selftest", "--list", "--matrix", "--matrix-probe"}
    args = list(argv[1:])
    if "--matrix-probe" in args:                # W168: --matrix-probe DIR
        i = args.index("--matrix-probe")
        if i + 1 >= len(args) or not os.path.isdir(args[i + 1]):
            print("check_symmetry: --matrix-probe needs an existing directory", file=sys.stderr)
            return 2
        print(json.dumps(matrix_probe(args[i + 1]), indent=1))
        return 0
    for a in args:
        if a not in known:
            print(f"check_symmetry: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--matrix" in argv:                      # the matrix glyph cases alone (W166)
        print(json.dumps(matrix_cases(), indent=1))
        return 0
    if "--list" not in argv:
        import opa_gate
        return opa_gate.gate("symmetry")
    # --list: the DIAGNOSTIC report — every located mirror asymmetry, and the grids
    m = measure()
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
    for g in m["grids"]:
        if g.get("withheld"):
            print(f"  {g['label']:12s} WITHHELD {g['withheld']}")
            continue
        print(f"  {g['label']:12s} grid: {g['columns']} columns, "
              f"pip widths {g['pip_widths']}, gaps {g['gaps']}")
    print(f"check_symmetry: {found} located asymmetr{'y' if found == 1 else 'ies'} to fix "
          f"(diagnostic); the grid verdict is `opa_gate.py symmetry`")
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
    ge = grid_regularity(even)
    chk("an integer pitch measures one width and one gap", (ge["pip_widths"], ge["gaps"]), ([3], [1]))
    odd = Image.new("RGB", (40, 8), (0, 0, 0))
    for c in range(8):
        x = round(c * 4.5)
        for dx in range(3):
            if x + dx < 40:
                odd.putpixel((x + dx, 4), (255, 255, 255))
    g = grid_regularity(odd)
    chk("a fractional pitch measures more than one gap", len(g["gaps"]) > 1, True)
    chk("a blank board measures NO columns (the policy refuses it)",
        grid_regularity(Image.new("RGB", (40, 8), (0, 0, 0)), ground=(0, 0, 0))["columns"], 0)
    # ⚑ THE FIT CAN NAME A SEGMENT (W165): seven synthetic bars on the substrate's own
    # coordinates fit clean; shift ONE by 3 px and the fit names exactly that one
    import make_clock as MC

    def eight(shift=None, L=40, t=6, o=10):
        img = Image.new("RGB", (L + 2 * o, 2 * L + 2 * o), (0, 0, 0))
        for s, (k, ux, uy) in MC.SEGS.items():
            x0, y0 = o + L * ux, o + L * uy
            dx = 3 if s == shift else 0
            if k == "h":
                box = (x0 + t + dx, y0 - t // 2, x0 + L - t + dx, y0 + t // 2)
            else:
                box = (x0 - t // 2 + dx, y0 + t, x0 + t // 2 + dx, y0 + L - t)
            for x in range(int(box[0]), int(box[2])):
                for y in range(int(box[1]), int(box[3])):
                    img.putpixel((x, y), (255, 255, 255))
        return img
    clean = segment_fit(eight(), MC.SEGS)
    chk("a clean synthetic 8 fits with no offender", clean["offenders"], [])
    chk("...and recovers its segLen", abs(clean["fit"]["segLen"] - 40) < 1, True)
    bent = segment_fit(eight(shift="B"), MC.SEGS)
    chk("a segment shifted 3 px is NAMED by the fit", bent["offenders"], ["B"])
    # ⚑ THE MATRIX CASE CAN SEE (W166): a synthetic 5x7 pip H (3 px pips, 1 px gaps)
    # after a second glyph is cropped to its FIRST glyph, mirrors clean, and a
    # removed pip is located
    H = ["X...X", "X...X", "X...X", "XXXXX", "X...X", "X...X", "X...X"]

    def board(drop=None):
        img = Image.new("RGB", (60, 40), (20, 20, 20))         # the ghost-pip ground
        for gx in (2, 30):                                      # two glyphs, a blank column apart
            for r, line in enumerate(H):
                for c, ch in enumerate(line):
                    if ch == "X" and not (gx == 2 and (r, c) == drop):
                        for dx in range(3):
                            for dy in range(3):
                                img.putpixel((gx + c * 4 + dx, 2 + r * 4 + dy), (255, 200, 0))
        return img
    b = board()
    box = first_glyph_box(b)
    chk("the first glyph is cropped alone (5 pips wide, the second glyph excluded)", box, (2, 2, 21, 29))
    g = b.crop(box)
    chk("a clean pip H mirrors in both planes", (mirror_points(g, "h"), mirror_points(g, "v")), ([], []))
    notched = board(drop=(0, 0)).crop(box)
    chk("a removed pip is located by the mirror", len(regions(mirror_points(notched, "h"))) > 0, True)
    # ...and WITH the W51 ring lit around the board, the crop is still the first glyph
    # (the real board's first crop was the whole board: the ring had swallowed it)
    ringed = Image.new("RGB", (68, 44), (20, 20, 20))
    for x in range(0, 68, 4):
        for y in (0, 40):
            for dx in range(3):
                for dy in range(3):
                    ringed.putpixel((x + dx, y + dy), (255, 200, 0))
    for y in range(0, 44, 4):
        for x in (0, 64):
            for dx in range(3):
                for dy in range(3):
                    ringed.putpixel((x + dx, y + dy), (255, 200, 0))
    ringed.paste(b, (4, 4))
    rbox = first_glyph_box(ringed, ring=True)
    chk("with the hover ring lit, the crop is still the first glyph alone", rbox, (6, 6, 25, 33))
    chk("...and without ring exclusion it would not be", first_glyph_box(ringed) != rbox, True)
    # ...and on a board whose GHOST pips sit above half the peak (the real board,
    # W168), the glyph is still told apart from them
    ghosted = Image.new("RGB", (64, 40), (20, 20, 20))
    for c in range(15):
        for r in range(9):
            for dx in range(3):
                for dy in range(3):
                    ghosted.putpixel((2 + c * 4 + dx, 2 + r * 4 + dy), (170, 140, 0))
    for gx in (2, 30):
        for r, line in enumerate(H):
            for c, ch in enumerate(line):
                if ch == "X":
                    for dx in range(3):
                        for dy in range(3):
                            ghosted.putpixel((gx + c * 4 + dx, 2 + r * 4 + dy), (255, 210, 0))
    chk("with ghost pips above half the peak, the crop is still the first glyph",
        first_glyph_box(ghosted), (2, 2, 21, 29))
    print("check_symmetry selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
