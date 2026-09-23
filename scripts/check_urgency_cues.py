#!/usr/bin/env python3
"""check_urgency_cues.py — is marquee urgency VISIBLE by weight at panel size, from pixels (W72.h)?

check_use_of_colour proves the W72 cues EXIST in the painter's source (critical grows
+s/2 and lights its descent row; low and suspended shrink -s/4). It cannot prove they
survive the board: the marquee is an APERTURE FIELD (templates/ApertureField.qml), whose
pips are hardware — fixed size, fixed grid — and whose only output per pip is a
brightness `opacity = coverage of the backdrop under its aperture`. So a dot drawn
smaller in the backdrop does NOT become a smaller pip; it becomes a DIMMER one. And by
the operator's ruling (2026-09-23) opacity is colour.

THE MEASUREMENT. Per variant (render_screens.VARIANTS), three runs of the real widget
through check_marquee_live's stager — one arrival each, urgency 0 / 1 / 2, the same
text — grabbed mid-scroll at the harness's board size (420x40, the size the screens
gallery renders the marquee at). Each still is read back as a PIP GRID found from the
pixels (the ghost field's gap columns/rows: autocorrelation for the pitch, the minimum
of the profile for the phase — nothing copied from the template), and each cell is
reduced to one number per VIEW:

    gray         WCAG relative luminance (the grayscale view)
    protanomaly  \\
    deuteranomaly | CAM02-UCS J' under cvd_gate's Machado simulation, severity 100
    tritanomaly  /

A cell's ink is |cell mean - ghost floor| (the floor is the median cell: most of the
board is ghost). Per still, per view:

  * mass      — mean ink per lit cell, as a fraction of the NORMAL still's peak cell in
                the same view: how bright the text is. This is what a grayscale viewer
                sees, and it is colour-inclusive: an opacity cue lives here.
  * footprint — the text's AREA-EQUIVALENT lit fraction: the span's summed ink over the
                STILL'S OWN PEAK cell, per span cell. Self-normalised, so it is
                CONTRAST-FREE: an urgency drawn as the same pips at a quarter of the
                brightness has the same footprint, and a half-lit neighbour counts as
                half a pip (no threshold to land on either side of). This is the weight
                cue, and the only one the ruling admits.
  * underline — the fraction of the span's bottom-row cells lit at half the peak.

The distinguishability of two urgencies in a view is max/min of their footprints; the
verdict takes the WORST view. The requirement (policy/urgency_cues.rego) denies a pair
below WEIGHT_RATIO_MIN, and denies a critical whose underline row is not lit.

⚑ MEASURED 2026-09-23, FIRST RUN: low~normal is 1.007-1.045 in all six variants (mass
ratio 3.7-4.2x) — the -s/4 light dot integrates to ~1/4 coverage under a pip's aperture
and renders as the SAME pips at ~1/4 opacity. No larger shrink can pass: shrinking only
lowers coverage. Critical passes (2.0-2.5x, underline row 1.00). A whole-pip change
does pass — the light glyph drawn at full ink on odd rows only measured 1.87-1.93x on
every variant — but costs legibility (an H reads as dashes); that trade is the
operator's, so the template was left as it is and this check stays red until it is made.

WEIGHT_RATIO_MIN = 1.25 — THE PROJECT'S JUDGEMENT, not a standard's. WCAG's 3:1
non-text contrast (SC 1.4.11) is a LUMINANCE ratio, i.e. colour, so it cannot be the
floor for a cue whose whole point is to survive the removal of colour. Weight is an
AREA: the footprint ratio is the ratio of lit area over the same glyphs. Typography's
own weight steps set the scale — Regular to Bold stems run ~1.5-1.7x, and Semibold
(~1.25x) is the smallest step a reader reliably picks out at text size. A glanced panel
ticker is not easier than body text, so the floor sits at the smallest step that reads
as a different weight, and no lower.

    scripts/check_urgency_cues.py --json            # the measurement (opa_gate urgency_cues decides)
    scripts/check_urgency_cues.py --list            # per variant, per urgency, the numbers
    scripts/check_urgency_cues.py --stills <dir>    # also KEEP the stills there (for inspection)
    scripts/check_urgency_cues.py --variant <name>  # one variant only
    scripts/check_urgency_cues.py --selftest        # the measurement can SEE an indistinguishable fixture

WEAKNESS, STATED. One still per urgency, at whatever sub-pip offset the harness's grab
landed on — partial pips at the text's edges move `mass` by a few percent between
runs (the footprint's half-peak threshold is what keeps that out of the verdict). The
grid is found from the ghost field, so a variant run with the field hidden has no grid
and is withheld. The text is upper-case on purpose (no descender may pose as an
underline); a lower-case board is not what this measures. `withheld` when the qml
runner is absent.
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "catalog", "library"))

URGENCIES = (("low", 0), ("normal", 1), ("critical", 2))
VIEWS = ("gray", "protanomaly", "deuteranomaly", "tritanomaly")
WEIGHT_RATIO_MIN = 1.25
LIT_FRACTION = 0.5            # a cell is lit at >= half its still's peak (the footprint's threshold)
SUMMARY = "HHHHHHHH"          # upper case: no descender may pose as an underline
APP = "APP"
END_MS = 4000


def variants():
    """The declared roster (scripts/variant_roster.py, W61 B2) — not render_screens'
    own typed VARIANTS, which is a producer's list and would shrink the check with it."""
    import variant_roster
    return variant_roster.ids()


def timeline(u):
    return [(300, "arrive", 1, {"summary": SUMMARY, "body": "", "applicationName": APP, "urgency": u},
             f"{APP}: {SUMMARY}")]


def still(variant, u, out):
    """Grab the real widget mid-scroll with one arrival of urgency `u`. Returns the harness
    result (for the ground colour and the grab sample) or None when the runner is absent."""
    import check_marquee_live as ML
    return ML.run(variant=variant, end_ms=END_MS, grab=out, timeline=timeline(u))


# ── the pixels ──────────────────────────────────────────────────────────────────

def _lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def view_image(rgb, view):
    """One scalar per pixel: luminance (gray) or CAM02-UCS J' under a CVD simulation."""
    rgb = np.asarray(rgb, dtype=float)
    if view == "gray":
        lin = _lin(rgb)
        return 0.2126 * lin[..., 0] + 0.7152 * lin[..., 1] + 0.0722 * lin[..., 2]
    import cvd_gate
    return cvd_gate._ucs(rgb.reshape(-1, 3), view)[:, 0].reshape(rgb.shape[:2])


def _period(profile, lo=2, hi=12):
    """The FUNDAMENTAL period: the smallest lag whose autocorrelation is within 20% of the
    best (a glyph pattern on top of the pip grid peaks again at multiples of the pitch)."""
    p = profile - profile.mean()
    ks = list(range(lo, min(hi, len(p) // 2) + 1))
    ac = [float(np.dot(p[:-k], p[k:])) / (len(p) - k) for k in ks]
    if not ac or max(ac) <= 0:
        return None
    best = max(ac)
    for k, v in zip(ks, ac):
        if v >= 0.8 * best:
            return k
    return None


def grid(img_gray, ground_gray):
    """(pitch, x0, y_rows) — the pip grid, from the pixels: the ghost field's profile is
    periodic with a gap column per pitch. y_rows are the top rows of the pip bands."""
    ink = np.abs(img_gray - ground_gray)
    colp, rowp = ink.sum(axis=0), ink.sum(axis=1)
    if colp.max() <= 0:
        return None
    # ⚑ THE GAPS, NOT THE INK: pips are hardware of one size on one pitch, so the
    # column between two pips is ground in EVERY row whatever the text is. The glyph
    # pattern (an H every 6 cells) swamps an autocorrelation of the ink profile; the
    # spacing of the empty columns is the pitch outright.
    # (measured: the board's void is NOT the window's ground — the marquee paints its
    # own darker void — so a gap is the profile's FLOOR, not zero ink)
    lo, hi = float(colp.min()), float(colp.max())
    gaps = np.where(colp <= lo + 0.02 * (hi - lo))[0]
    steps = np.diff(gaps)
    steps = steps[steps > 1]
    if len(steps) == 0:
        return None
    vals, counts = np.unique(steps, return_counts=True)
    pitch = int(vals[np.argmax(counts)])
    x0 = int(np.argmin([colp[k::pitch].mean() for k in range(pitch)]))
    y0 = int(np.argmin([rowp[k::pitch].mean() for k in range(pitch)]))
    # the pip bands: cell rows whose band carries ink (the ghost field's rows)
    starts = list(range(y0, img_gray.shape[0] - pitch + 1, pitch))
    sums = [float(ink[y:y + pitch].sum()) for y in starts]
    top = max(sums) if sums else 0.0
    floor = min(sums) if sums else 0.0
    # any ink over the void's floor: a ghost-only row is a row
    bands = [y for y, s in zip(starts, sums) if top > floor and s > floor + 0.01 * (top - floor)]
    return pitch, x0, bands


def cells(img, pitch, x0, bands):
    """[rows x cols] cell means of a scalar image."""
    cols = list(range(x0, img.shape[1] - pitch + 1, pitch))
    return np.array([[img[y:y + pitch, x:x + pitch].mean() for x in cols] for y in bands])


def read_still(path, ground):
    """{view: cell-ink matrix} for one still, or None when no grid is found."""
    from PIL import Image
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    return ink_views(rgb, ground)


def ink_views(rgb, ground):
    g = np.array(ground, dtype=float).reshape(1, 1, 3)
    gray = view_image(rgb, "gray")
    gg = float(view_image(g, "gray")[0, 0])
    gr = grid(gray, gg)
    if gr is None or not gr[2]:
        return None
    pitch, x0, bands = gr
    out = {"_grid": {"pitch": pitch, "x0": x0, "rows": len(bands)}}
    for v in VIEWS:
        im = gray if v == "gray" else view_image(rgb, v)
        c = cells(im, pitch, x0, bands)
        floor = np.median(c)
        out[v] = np.abs(c - floor)
    return out


def still_facts(ink, ref_peak):
    """Per view: mass, footprint, underline for one still. ref_peak: the NORMAL still's
    peak cell ink in that view (the full-pip reference mass is judged against)."""
    out = {}
    for v in VIEWS:
        c = ink[v]
        peak = float(c.max())
        lit = c >= LIT_FRACTION * peak if peak > 0 else np.zeros_like(c, bool)
        anyink = c >= 0.1 * ref_peak[v]
        colsw = np.where(anyink.any(axis=0))[0]
        if peak <= 0 or len(colsw) == 0:
            out[v] = {"mass": 0.0, "footprint": 0.0, "underline": 0.0, "lit_cells": 0, "span_cells": 0}
            continue
        a, b = int(colsw[0]), int(colsw[-1]) + 1
        span = c[:, a:b]
        spanlit = lit[:, a:b]
        inked = span[anyink[:, a:b]]
        out[v] = {"mass": round(float(inked.mean() / ref_peak[v]), 4),
                  # area-equivalent: sum of ink over the still's OWN peak — invariant to
                  # scaling the brightness (an opacity cue), counting a half-lit
                  # neighbour as half a pip rather than choosing a side of a threshold
                  "footprint": round(float(span.sum() / peak / span.size), 4),
                  "underline": round(float(spanlit[-1].mean()), 4),
                  "lit_cells": int(spanlit.sum()), "span_cells": int(spanlit.size)}
    return out


def judge_variant(variant, inks):
    """inks: {urgency name: ink_views} -> a case: per urgency per view facts, and per pair
    the worst-view footprint ratio."""
    ref = {v: float(inks["normal"][v].max()) or 1.0 for v in VIEWS}
    facts = {name: still_facts(inks[name], ref) for name, _ in URGENCIES}
    pairs = []
    names = [n for n, _ in URGENCIES]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            worst = None
            for v in VIEWS:
                fa, fb = facts[a][v]["footprint"], facts[b][v]["footprint"]
                r = (max(fa, fb) / min(fa, fb)) if min(fa, fb) > 0 else float("inf") if max(fa, fb) > 0 else 1.0
                ma, mb = facts[a][v]["mass"], facts[b][v]["mass"]
                mr = (max(ma, mb) / min(ma, mb)) if min(ma, mb) > 0 else 0.0
                if worst is None or r < worst["ratio"]:
                    worst = {"a": a, "b": b, "view": v, "ratio": round(r, 3), "mass_ratio": round(mr, 3)}
            pairs.append(worst)
    return {"variant": variant, "grid": inks["normal"]["_grid"], "urgencies": facts, "pairs": pairs}


def measure(only=None, stills_dir=None):
    import tempfile
    import make_preview
    import check_marquee_live as ML
    if not os.path.isfile(ML.QML):
        return {"cases": [], "withheld": [{"variant": "*", "reason": "no qml runner on this host"}],
                "threshold": WEIGHT_RATIO_MIN, "views": list(VIEWS)}
    ML._emitted()                                     # once, before the pool
    todo = [v for v in variants() if only in (None, v)]
    keep = stills_dir or tempfile.mkdtemp(prefix="urgency-cues-")
    os.makedirs(keep, exist_ok=True)
    jobs = [(v, n, u, os.path.join(keep, f"urgency-{n}-{v}.png")) for v in todo for n, u in URGENCIES]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=int(os.environ.get("EL_URGENCY_JOBS", "3"))) as pool:
        results = list(pool.map(lambda j: (j, still(j[0], j[2], j[3])), jobs))
    cases, withheld = [], []
    for v in todo:
        ground = make_preview.parse_scheme(v)["ground"]
        ground = tuple(int(ground[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(ground, str) else tuple(ground)
        inks, why = {}, None
        for (vv, n, u, path), res in results:
            if vv != v:
                continue
            if res is None or not os.path.isfile(path):
                why = f"{n}: no still (runner absent or the grab never fired)"
                break
            ink = read_still(path, ground)
            if ink is None:
                why = f"{n}: no pip grid found in the still"
                break
            inks[n] = ink
        if why:
            withheld.append({"variant": v, "reason": why})
        else:
            c = judge_variant(v, inks)
            c["stills"] = {n: os.path.join(keep, f"urgency-{n}-{v}.png") for n, _ in URGENCIES}
            cases.append(c)
    return {"cases": cases, "withheld": withheld, "threshold": WEIGHT_RATIO_MIN, "views": list(VIEWS)}


def ground_of(variant):
    import make_preview
    g = make_preview.parse_scheme(variant)["ground"]
    return tuple(int(g[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(g, str) else tuple(g)


def cells_report(path, variant):
    """The diagnostic a failed grid needs: the column profile's gaps and the cell matrix."""
    from PIL import Image
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=float)
    ground = ground_of(variant)
    gray = view_image(rgb, "gray")
    gg = float(view_image(np.array(ground, float).reshape(1, 1, 3), "gray")[0, 0])
    ink = np.abs(gray - gg)
    colp = ink.sum(axis=0)
    print(f"{path}: {rgb.shape[1]}x{rgb.shape[0]} ground {ground} (gray {gg:.4f})")
    print("column ink profile, first 24 columns (x1000):", [round(float(v) * 1000) for v in colp[:24]])
    print("row ink profile (x1000):", [round(float(v) * 1000) for v in ink.sum(axis=1)])
    print("distinct pixel colours in rows 18-21, cols 200-216:",
          sorted({tuple(int(x) for x in rgb[y, x]) for y in range(18, 22) for x in range(200, 216)}))
    gr = grid(gray, gg)
    print("grid:", gr)
    iv = ink_views(rgb, ground)
    if iv is None:
        print("no grid")
        return 1
    for row in iv["gray"]:
        print(" ".join(f"{int(v * 1000):3d}" for v in row[:60]))
    return 0


def listing(m):
    for c in m["cases"]:
        print(f"{c['variant']}  grid pitch={c['grid']['pitch']} rows={c['grid']['rows']}")
        for n, _ in URGENCIES:
            f = c["urgencies"][n]
            print(f"  {n:9s} " + "  ".join(
                f"{v[:5]}: mass {f[v]['mass']:.2f} foot {f[v]['footprint']:.3f} "
                f"ul {f[v]['underline']:.2f}" for v in VIEWS))
        for p in c["pairs"]:
            flag = "ok  " if p["ratio"] >= m["threshold"] else "FAIL"
            print(f"  {flag} {p['a']}~{p['b']}: footprint ratio {p['ratio']} (worst view {p['view']}); "
                  f"mass ratio there {p['mass_ratio']}")
    for w in m["withheld"]:
        print(f"  withheld {w['variant']}: {w['reason']}")
    good = sum(all(p["ratio"] >= m["threshold"] for p in c["pairs"]) for c in m["cases"])
    print(f"\ncheck_urgency_cues: {good} of {len(m['cases'])} variant(s) tell all three urgencies apart by weight "
          f"(footprint ratio >= {m['threshold']} in every view); {len(m['withheld'])} withheld")


def main(argv):
    args = list(argv[1:])
    opts = {}
    for flag in ("--stills", "--variant"):
        if flag in args:
            i = args.index(flag)
            if i + 1 >= len(args):
                print(f"check_urgency_cues: {flag} needs a value", file=sys.stderr)
                return 2
            opts[flag] = args[i + 1]
            del args[i:i + 2]
    if "--cells" in args:
        # one still, read back: the grid found and the gray cell-ink matrix (x100)
        i = args.index("--cells")
        if i + 2 >= len(args):
            print("check_urgency_cues: --cells needs PNG VARIANT", file=sys.stderr)
            return 2
        path, variant = args[i + 1], args[i + 2]
        return cells_report(path, variant)
    for a in args:
        if a not in {"--json", "--list", "--selftest"}:
            print(f"check_urgency_cues: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--json" in args or "--list" in args:
        m = measure(opts.get("--variant"), opts.get("--stills"))
        if "--json" in args:
            print(json.dumps(m, indent=1))
        else:
            listing(m)
        return 0
    print("usage: check_urgency_cues.py --json | --list [--stills DIR] [--variant NAME] | --selftest  "
          "(the verdict: scripts/opa_gate.py urgency_cues)", file=sys.stderr)
    return 2


# ── the selftest: synthetic boards drawn the way ApertureField draws them ─────────

H_GLYPH = [0x7F, 0x08, 0x08, 0x08, 0x7F]      # an 'H', 5 columns x 7 rows


def synth_board(coverage, ground=(6, 11, 13), ghost=(40, 60, 60), lit=(140, 232, 218), pitch=4, d=3,
                rows=8, width=420, height=40, ghost_alpha=0.28):
    """An RGB board: each cell a d x d pip, ghost at ghost_alpha, lit composited at the
    cell's coverage (ApertureField's `opacity: cov`)."""
    img = np.zeros((height, width, 3)) + np.array(ground, float)
    y0 = round((height - rows * pitch) / 2)
    off = round((pitch - d) / 2 + 1e-9)
    for r in range(rows):
        for c in range(width // pitch):
            x, y = c * pitch + off, y0 + r * pitch + off
            px = np.array(ground, float) * (1 - ghost_alpha) + np.array(ghost, float) * ghost_alpha
            cov = coverage[r][c] if c < len(coverage[r]) else 0.0
            px = px * (1 - cov) + np.array(lit, float) * cov
            img[y:y + d, x:x + d] = px
    return img


def synth_coverage(weight, n=8, start=20, underline=False, cols=105, rows=8):
    """Backdrop coverage of n 'H's: weight 'normal' (1.0 per dot), 'dim' (the same dots at
    0.25 — a light dot as the aperture renders it), 'heavy' (each dot spreads half a cell
    into its 4-neighbours)."""
    cov = [[0.0] * cols for _ in range(rows)]
    for k in range(n):
        for c, byte in enumerate(H_GLYPH):
            for r in range(rows):
                on = bool(byte & (1 << r)) or (underline and r == rows - 1)
                if not on:
                    continue
                x = start + k * 6 + c
                if x >= cols:
                    continue
                if weight == "heavy":
                    for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                        rr, cc = r + dr, x + dc
                        if 0 <= rr < rows and 0 <= cc < cols:
                            cov[rr][cc] = max(cov[rr][cc], 0.5)
                cov[r][x] = 0.25 if weight == "dim" else 1.0
    return cov


def _selftest():
    """The measurement can SEE: an opacity-only light dot (the same pips at a quarter of
    the coverage) is INDISTINGUISHABLE from normal by footprint while its mass differs;
    a spread (heavy) dot with an underline is distinguishable, and its underline row is
    seen lit; the grid is found from pixels."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    ground = (6, 11, 13)
    inks = {"low": ink_views(synth_board(synth_coverage("dim")), ground),
            "normal": ink_views(synth_board(synth_coverage("normal")), ground),
            "critical": ink_views(synth_board(synth_coverage("heavy", underline=True)), ground)}
    chk("the grid is found from the pixels (pitch 4, 8 rows)",
        (inks["normal"]["_grid"]["pitch"], inks["normal"]["_grid"]["rows"]), (4, 8))
    c = judge_variant("fixture", inks)
    pr = {(p["a"], p["b"]): p for p in c["pairs"]}
    chk("an opacity-only light dot is INDISTINGUISHABLE by footprint (ratio < threshold)",
        pr[("low", "normal")]["ratio"] < WEIGHT_RATIO_MIN, True)
    chk("...while its mass differs (the cue is there, but it is opacity)",
        pr[("low", "normal")]["mass_ratio"] > 2, True)
    chk("a heavy + underlined dot IS distinguishable from normal", pr[("normal", "critical")]["ratio"] >= WEIGHT_RATIO_MIN, True)
    chk("the heavy still's underline row is lit, the normal one's is not",
        (c["urgencies"]["critical"]["gray"]["underline"] > 0.5, c["urgencies"]["normal"]["gray"]["underline"]), (True, 0.0))
    # a hue-only change survives nothing: the same pips in another ink are the same footprint in every view
    hot = ink_views(synth_board(synth_coverage("normal"), lit=(240, 90, 60)), ground)
    c2 = judge_variant("fixture-hue", {"low": inks["normal"], "normal": inks["normal"], "critical": hot})
    chk("a hue-only critical is indistinguishable by footprint",
        {(p["a"], p["b"]): p for p in c2["pairs"]}[("normal", "critical")]["ratio"] < WEIGHT_RATIO_MIN, True)
    chk("the population is the six variants", len(variants()), 6)
    print("check_urgency_cues selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
