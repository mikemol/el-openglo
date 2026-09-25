#!/usr/bin/env python3
"""check_urgency_cues.py — is marquee urgency VISIBLE without colour at panel size, from pixels (W72.h, W74)?

check_use_of_colour proves the cues EXIST in the painter's source. It cannot prove they
survive the board: the marquee is an APERTURE FIELD (templates/ApertureField.qml), whose
pips are hardware — fixed size, fixed grid — and whose only output per pip is a
brightness `opacity = coverage of the backdrop under its aperture`. So a dot drawn
smaller in the backdrop does NOT become a smaller pip; it becomes a DIMMER one, and by
the operator's ruling (2026-09-23) opacity is colour.

⚑ OPERATOR RULING 2026-09-23 (W74): urgency is carried by LETTERFORM — low = lowercase,
normal = UPPERCASE, critical = FLASHING UPPER CASE (plus its hot ink and lit underline
row). A footprint (lit AREA) cannot credit that: 'h' and 'H' light about as many pips.
So the measurement has three arms, all from the real widget's pixels:

  SHAPE (static). Per variant, per urgency, one still of the real widget mid-scroll
  through check_marquee_live's stager (one arrival, the same text, grabbed in a LIT
  phase of any flash), read back as a PIP GRID found from the pixels (the ghost
  field's gap columns/rows — nothing copied from the template). Each cell is reduced to
  one number per VIEW:

      gray         WCAG relative luminance (the grayscale view)
      protanomaly  \\
      deuteranomaly | CAM02-UCS J' under cvd_gate's Machado simulation, severity 100
      tritanomaly  /

  and BINARISED against the still's OWN peak (lit at >= LIT_FRACTION of it): the set
  of lit pips, with brightness normalised away — an opacity-only cue binarises to the
  SAME set and so scores zero. Per pair of urgencies, per view:

      shape = 1 - IoU(lit pips of a, lit pips of b), minimised over a +-SHIFT column
              alignment (so a sub-pip grab offset between stills is not credited)

  and the pair's verdict takes the WORST (smallest) view. `footprint` (area over own
  peak), `mass` (brightness vs normal's peak) and `underline` (the bottom row's lit
  fraction) are reported beside it.

  TEMPORAL. The same run records a FRAME SERIES (one grab per 40 ms virtual sample,
  check_marquee_live's frames). The text is longer than the board, so there is a span
  of frames in which the board is COVERED by text end to end; over those frames the
  lit mass (gray ink over the ghost floor) is read per frame, relative to the series'
  max. A frame below DARK_FRACTION is dark. Facts: covered frames, dark frames, the
  edges (lit<->dark changes) and the flash rate `edges / 2 / span`. Critical must
  alternate at the declared rate; low and normal must stay steady.

  PAUSE. One more run per variant with the hover-pause ON (the offscreen pointer rests
  at (0,0), so the board pauses as the text reaches it): the widget's own `flashLit`
  per sample while paused (WCAG 2.2.2: the flash must stop). This arm reads the
  widget's STATE, not pixels — see WEAKNESS.

  CHARSET. The registry the marquee ships (display_types 5x8 + the outline-font
  extension, as make_notify_marquee builds it) and every LETTER of the charset it
  declares (display_types.MATRIX_CHARSET): per urgency, what the SHIPPED
  marquee-body.js displays (displayChar) and which registry key its lookup lands on
  (glyphKey) — the displayed form, the char as sent, its upper case, or '?'. Plus the
  declared flash rate (Body.FLASH_HZ), read from the same shipped file.

The requirement is policy/urgency_cues.rego; this file only measures.

    scripts/check_urgency_cues.py --json            # the measurement (opa_gate urgency_cues decides)
    scripts/check_urgency_cues.py --list            # per variant, per urgency, the numbers
    scripts/check_urgency_cues.py --charset         # the letter census alone: n of m per urgency
    scripts/check_urgency_cues.py --stills <dir>    # also KEEP the stills and frames there
    scripts/check_urgency_cues.py --variant <name>  # one variant only
    scripts/check_urgency_cues.py --cells PNG VARIANT  # one still's grid and binarised pips
    scripts/check_urgency_cues.py --replay FRAMES STILL VARIANT  # a kept frame series' temporal facts
    scripts/check_urgency_cues.py --selftest        # the measurement can SEE opacity-only / hue-only / flash

WEAKNESS, STATED. One still per urgency, at whatever sub-pip offset the harness's grab
landed on; the +-SHIFT alignment absorbs a whole-cell slip, the half-peak binarisation
a partial pip. The shape metric proves the SETS of lit pips differ; it does not prove a
reader names the letters — legibility of the rasterised lowercase at 5x8 is a look at
the stills, not a number here. The temporal arm counts edges over the covered frames
only (~2.5 s virtual at the harness's speed 8); a flash slower than ~0.4 Hz shows fewer
than two edges there and reads as "does not flash". The PAUSE arm reads `flashLit`, the
widget's own flag, so a flag that stops while the pixels keep flashing would pass it;
the reduced-motion switch (Kirigami.Units.longDuration == 0) is not exercised at all —
the harness's theme has animations on. The grid is found from the ghost field, so a
variant run with the field hidden has no grid and is withheld. `withheld` when the qml
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
LIT_FRACTION = 0.5            # a cell is lit at >= half its still's peak
SHIFT = 2                     # the shape metric's column alignment search, in cells
DARK_FRACTION = 0.2           # a frame is dark below this fraction of the series' max lit mass
# mixed case on purpose: the letterform arm must see real letters change case, and
# the text is longer than the board so the temporal arm has frames it covers end to end.
# No descender letters (g j p q y) in the summary, so the bottom row is the underline's.
SUMMARY = " ".join(["Hello World"] * 9)
APP = "APP"
END_MS = 6000
HOVER_STOP_SAMPLES = 20


def variants():
    """The declared roster (scripts/variant_roster.py, W61 B2) — not render_screens'
    own typed VARIANTS, which is a producer's list and would shrink the check with it."""
    import variant_roster
    return variant_roster.ids()


def timeline(u):
    return [(300, "arrive", 1, {"summary": SUMMARY, "body": "", "applicationName": APP, "urgency": u},
             f"{APP}: {SUMMARY}")]


def still(variant, u, out, frames):
    """Grab the real widget mid-scroll with one arrival of urgency `u`, and its frame
    series into `frames`. The harness result, or None when the runner is absent."""
    import check_marquee_live as ML
    os.makedirs(frames, exist_ok=True)
    res = ML.run(variant=variant, end_ms=END_MS, grab=out, frames=frames, timeline=timeline(u))
    if res is not None:          # kept beside the frames, so --replay can re-read them
        json.dump({k: res[k] for k in ("width", "samples", "frames") if k in res},
                  open(os.path.join(frames, "result.json"), "w"))
    return res


def replay(frames, still_png, variant):
    """The temporal facts, recomputed from a kept frame series (--stills) — no Qt run."""
    ground = ground_of(variant)
    ink = read_still(still_png, ground)
    res = json.load(open(os.path.join(frames, "result.json")))
    return temporal_facts(res, frames, ground, ink["_grid"])


def bold_facts(variant, out_dir):
    """⟐W72.f — does a BOLD run differ from a regular one in the SET of lit pips, or only
    in brightness? Operator (2026-09-25): grow=s/2 overhangs into NEIGHBOUR pips, so a
    heavier stroke should show as a wider footprint through the aperture — "a bloom
    behind the pip mask, captured by pip brightness" — not as the same pips brighter.
    Two stills of the real widget, identical text in the BODY (the only markup field,
    W45), plain vs <b>…</b>, normal urgency. Per view: lit cells (binarised to each
    still's OWN peak, so brightness drops out), mass, and 1-IoU of the lit sets."""
    import check_marquee_live as ML
    body = " ".join(["Hello World"] * 9)
    got = {}
    for name, b in (("regular", body), ("bold", f"<b>{body}</b>")):
        png = os.path.join(out_dir, f"{variant}-{name}.png")
        tl = [(300, "arrive", 1, {"summary": "", "body": b, "applicationName": APP, "urgency": 1},
               f"{APP}: {body}")]
        if ML.run(variant=variant, end_ms=END_MS, grab=png, timeline=tl) is None:
            return {"variant": variant, "withheld": "the qml runner is not on this host"}
        got[name] = read_still(png, ground_of(variant))
        if got[name] is None:
            return {"variant": variant, "withheld": f"no pip grid found in the {name} still"}
    views = {}
    for v in VIEWS:
        r, bd = got["regular"][v], got["bold"][v]
        lr, lb = lit_set(r), lit_set(bd)
        views[v] = {"lit_regular": int(lr.sum()), "lit_bold": int(lb.sum()),
                    "mass_regular": round(float(r.sum()), 3), "mass_bold": round(float(bd.sum()), 3),
                    "shape": shape_difference(lr, lb)[0]}
    return {"variant": variant, "views": views}


def paused(variant):
    """A critical arrival with the hover-pause ON: the samples while the board is held."""
    import check_marquee_live as ML
    return ML.run(hover_pause=True, stop_paused=HOVER_STOP_SAMPLES, variant=variant,
                  end_ms=ML.HOVER_CAP_MS, timeline=timeline(2))


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


def grid(img_gray, ground_gray):
    """(pitch, x0, y_rows) — the pip grid, from the pixels: the ghost field's profile is
    periodic with a gap column per pitch. y_rows are the top rows of the pip bands."""
    ink = np.abs(img_gray - ground_gray)
    colp, rowp = ink.sum(axis=0), ink.sum(axis=1)
    if colp.max() <= 0:
        return None
    # ⚑ THE GAPS, NOT THE INK: pips are hardware of one size on one pitch, so the
    # column between two pips is ground in EVERY row whatever the text is. The glyph
    # pattern swamps an autocorrelation of the ink profile; the spacing of the empty
    # columns is the pitch outright. (measured: the board's void is NOT the window's
    # ground — the marquee paints its own darker void — so a gap is the profile's
    # FLOOR, not zero ink)
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
    starts = list(range(y0, img_gray.shape[0] - pitch + 1, pitch))
    sums = [float(ink[y:y + pitch].sum()) for y in starts]
    top = max(sums) if sums else 0.0
    floor = min(sums) if sums else 0.0
    bands = [y for y, s in zip(starts, sums) if top > floor and s > floor + 0.01 * (top - floor)]
    return pitch, x0, bands


def cells(img, pitch, x0, bands):
    """[rows x cols] cell means of a scalar image."""
    cols = list(range(x0, img.shape[1] - pitch + 1, pitch))
    return np.array([[img[y:y + pitch, x:x + pitch].mean() for x in cols] for y in bands])


def _rgb(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB"), dtype=float)


def read_still(path, ground):
    """{view: cell-ink matrix} for one still, or None when no grid is found."""
    return ink_views(_rgb(path), ground)


def ink_views(rgb, ground, views=VIEWS):
    g = np.array(ground, dtype=float).reshape(1, 1, 3)
    gray = view_image(rgb, "gray")
    gg = float(view_image(g, "gray")[0, 0])
    gr = grid(gray, gg)
    if gr is None or not gr[2]:
        return None
    pitch, x0, bands = gr
    out = {"_grid": {"pitch": pitch, "x0": x0, "rows": len(bands), "bands": bands}}
    for v in views:
        im = gray if v == "gray" else view_image(rgb, v)
        c = cells(im, pitch, x0, bands)
        out[v] = np.abs(c - np.median(c))
    return out


def lit_set(c):
    """The binarised text: cells at >= LIT_FRACTION of the still's own peak."""
    peak = float(c.max())
    return c >= LIT_FRACTION * peak if peak > 0 else np.zeros_like(c, bool)


def shape_difference(a, b, shift=SHIFT):
    """1 - IoU of two lit sets, minimised over a +-shift column alignment; (value, dx)."""
    best = (1.0, 0) if (a.any() or b.any()) else (0.0, 0)
    n = a.shape[1]
    for dx in range(-shift, shift + 1):
        aa = a[:, max(0, dx):n + min(0, dx)]
        bb = b[:, max(0, -dx):n - max(0, dx)]
        union = int((aa | bb).sum())
        if union == 0:
            continue
        d = 1.0 - int((aa & bb).sum()) / union
        if d < best[0]:
            best = (d, dx)
    return round(best[0], 4), best[1]


def still_facts(ink, ref_peak):
    """Per view: mass, footprint, underline, lit cells for one still. ref_peak: the
    NORMAL still's peak cell ink in that view."""
    out = {}
    for v in VIEWS:
        c = ink[v]
        peak = float(c.max())
        lit = lit_set(c)
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
                  "footprint": round(float(span.sum() / peak / span.size), 4),
                  "underline": round(float(spanlit[-1].mean()), 4),
                  "lit_cells": int(spanlit.sum()), "span_cells": int(spanlit.size)}
    return out


def judge_variant(variant, inks):
    """inks: {urgency name: ink_views} -> a case: per urgency per view facts, and per pair
    the worst view's shape difference (with the footprint ratio there, for the record)."""
    ref = {v: float(inks["normal"][v].max()) or 1.0 for v in VIEWS}
    facts = {name: still_facts(inks[name], ref) for name, _ in URGENCIES}
    pairs = []
    names = [n for n, _ in URGENCIES]
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            worst = None
            for v in VIEWS:
                d, dx = shape_difference(lit_set(inks[a][v]), lit_set(inks[b][v]))
                fa, fb = facts[a][v]["footprint"], facts[b][v]["footprint"]
                fr = (max(fa, fb) / min(fa, fb)) if min(fa, fb) > 0 else 0.0
                ma, mb = facts[a][v]["mass"], facts[b][v]["mass"]
                mr = (max(ma, mb) / min(ma, mb)) if min(ma, mb) > 0 else 0.0
                if worst is None or d < worst["shape"]:
                    worst = {"a": a, "b": b, "view": v, "shape": d, "shift": dx,
                             "footprint_ratio": round(fr, 3), "mass_ratio": round(mr, 3)}
            pairs.append(worst)
    return {"variant": variant, "grid": {k: v for k, v in inks["normal"]["_grid"].items() if k != "bands"},
            "urgencies": facts, "pairs": pairs}


# ── the frame series ────────────────────────────────────────────────────────────

def temporal_facts(res, frames_dir, ground, grid_):
    """Over the frames in which text covers the board end to end: per-frame lit mass
    (gray ink over the ghost floor, relative to the series' max), dark frames, edges and
    the rate edges / 2 / span. `grid_` is the still's grid (the frames share it)."""
    width = res.get("width", 0)
    w = max([s.get("w") or 0 for s in res.get("samples", [])] or [0])
    fx = res.get("frames") or []
    pitch, x0, bands = grid_["pitch"], grid_["x0"], grid_["bands"]
    gg = float(view_image(np.array(ground, float).reshape(1, 1, 3), "gray")[0, 0])
    # ⚑ RUNS, NOT ONE SERIES (measured 2026-09-23, first run): the frames span two
    # rotations, and the uncovered stretch between them hides whole flash cycles —
    # counting edges across it read a 2 Hz flash as 1.45 Hz. So the covered frames are
    # split into contiguous RUNS and edges are counted and timed within each. A run's
    # first and last frame are dropped: a grab lands a render after its sample, and at
    # a rotation's end that render is already the next rotation's empty board (the one
    # dark frame low and normal each showed).
    runs, cur, prev = [], [], None
    for n, f in enumerate(fx):
        path = os.path.join(frames_dir, f"frame-{n:03d}.png")
        if not os.path.isfile(path) or f["x"] > 0 or f["x"] + w < width:
            continue
        if prev is not None and n != prev + 1 and cur:
            runs.append(cur)
            cur = []
        c = cells(view_image(_rgb(path), "gray"), pitch, x0, bands)
        ink = np.abs(c - gg)
        # the floor is the ghost: a cell's ink over the dimmest decile of the board
        floor = float(np.percentile(ink, 10))
        cur.append((f["t"], float(np.clip(ink - floor, 0, None).sum())))
        prev = n
    if cur:
        runs.append(cur)
    runs = [r[1:-1] for r in runs if len(r) > 2]
    series = [p for r in runs for p in r]
    if not series:
        return {"frames": len(fx), "covered": 0, "runs": 0, "dark": 0, "edges": 0, "span_ms": 0, "hz": 0.0,
                "steady_min": 0.0, "series": []}
    top = max(m for _, m in series) or 1.0
    edges, half_periods, span, dark_n, lit = 0, 0, 0.0, 0, []
    for r in runs:
        rel = [(t, m / top) for t, m in r]
        dark = [m < DARK_FRACTION for _, m in rel]
        dark_n += sum(dark)
        lit += [m for (_, m), d in zip(rel, dark) if not d]
        edge_t = [rel[k][0] for k in range(1, len(rel)) if dark[k] != dark[k - 1]]
        edges += len(edge_t)
        if len(edge_t) >= 2:
            half_periods += len(edge_t) - 1
            span += edge_t[-1] - edge_t[0]
    hz = round(half_periods / 2 / (span / 1000.0), 3) if span > 0 else 0.0
    return {"frames": len(fx), "covered": len(series), "runs": len(runs), "dark": int(dark_n), "edges": edges,
            "span_ms": round(span, 1), "hz": hz,
            # the steadiest reading of the lit frames: min over max (1.0 = perfectly steady)
            "steady_min": round(min(lit), 4) if lit else 0.0,
            "series": [[round(t, 1), round(m / top, 3)] for t, m in series]}


def pause_facts(res):
    ss = res.get("samples", []) if res else []
    held = [s for s in ss if s.get("paused")]
    before = [s for s in ss if not s.get("paused") and s.get("running")]
    return {"paused_samples": len(held), "paused_dark": sum(1 for s in held if s.get("flash") is False),
            # how long the pause held, in virtual ms: an ungated flash toggles within a
            # half-cycle, so a hold shorter than one cycle could not have caught it
            "paused_ms": round(held[-1]["t"] - held[0]["t"], 1) if held else 0,
            "running_dark": sum(1 for s in before if s.get("flash") is False)}


# ── the charset ─────────────────────────────────────────────────────────────────

def charset_facts():
    """The registry the marquee ships, and per LETTER of the declared charset what the
    shipped lookup rasterises at each urgency; None when the runner is absent."""
    import display_types as DT
    import make_notify_marquee as NM
    import check_marquee_body as MB
    font_path = NM.matrix_font()
    reg = json.loads(DT.as_qml_js(NM.MATRIX_DISPLAY, font_path=font_path))
    font = reg["font" + reg["displays"][NM.MATRIX_DISPLAY]["font"]]
    letters = [ch for ch in DT.MATRIX_CHARSET if ch.isalpha()]
    got = MB.glyph_census(font, letters)
    if got is None:
        return None
    charset = set(DT.MATRIX_CHARSET)
    cases = []
    for row in got["chars"]:
        for f in row["forms"]:
            # the case partner is IN the declared charset (ÿ's Ÿ is not: outside Latin-1)
            f["partner_in_charset"] = f["shown"] in charset
            f["case_applied"] = f["key"] == f["shown"]
        cases.append(row)
    return {"font": os.path.basename(font_path) if font_path else None, "glyphs": len(font),
            "declared": len(DT.MATRIX_CHARSET), "letters": len(letters), "cases": cases,
            "flash_hz": got["flash_hz"], "flash_ms": got["flash_ms"]}


def measure(only=None, stills_dir=None):
    import tempfile
    import make_preview
    import check_marquee_live as ML
    if not os.path.isfile(ML.QML):
        return {"cases": [], "withheld": [{"variant": "*", "reason": "no qml runner on this host"}],
                "views": list(VIEWS), "charset": None}
    ML._emitted()                                     # once, before the pool
    todo = [v for v in variants() if only in (None, v)]
    keep = stills_dir or tempfile.mkdtemp(prefix="urgency-cues-")
    os.makedirs(keep, exist_ok=True)
    jobs = [(v, n, u, os.path.join(keep, f"urgency-{n}-{v}.png"), os.path.join(keep, f"frames-{n}-{v}"))
            for v in todo for n, u in URGENCIES]
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=int(os.environ.get("EL_URGENCY_JOBS", "3"))) as pool:
        results = list(pool.map(lambda j: (j, still(j[0], j[2], j[3], j[4])), jobs))
        held = dict(zip(todo, pool.map(paused, todo)))
    cases, withheld = [], []
    for v in todo:
        ground = make_preview.parse_scheme(v)["ground"]
        ground = tuple(int(ground[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(ground, str) else tuple(ground)
        inks, temporal, why = {}, {}, None
        for (vv, n, u, path, frames), res in results:
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
            temporal[n] = temporal_facts(res, frames, ground, ink["_grid"])
        if why:
            withheld.append({"variant": v, "reason": why})
            continue
        c = judge_variant(v, inks)
        c["temporal"] = temporal
        c["pause"] = pause_facts(held.get(v))
        c["stills"] = {n: os.path.join(keep, f"urgency-{n}-{v}.png") for n, _ in URGENCIES}
        cases.append(c)
    return {"cases": cases, "withheld": withheld, "views": list(VIEWS), "charset": charset_facts()}


def ground_of(variant):
    import make_preview
    g = make_preview.parse_scheme(variant)["ground"]
    return tuple(int(g[i:i + 2], 16) for i in (1, 3, 5)) if isinstance(g, str) else tuple(g)


def cells_report(path, variant):
    """The diagnostic a failed grid needs: the grid found and the gray cell-ink matrix."""
    rgb = _rgb(path)
    ground = ground_of(variant)
    gray = view_image(rgb, "gray")
    gg = float(view_image(np.array(ground, float).reshape(1, 1, 3), "gray")[0, 0])
    print(f"{path}: {rgb.shape[1]}x{rgb.shape[0]} ground {ground} (gray {gg:.4f})")
    print("grid:", grid(gray, gg))
    iv = ink_views(rgb, ground, views=("gray",))
    if iv is None:
        print("no grid")
        return 1
    lit = lit_set(iv["gray"])
    for row in lit:
        print("".join("#" if x else "." for x in row))
    return 0


def charset_listing(cs):
    if cs is None:
        print("check_urgency_cues: charset withheld — no qml runner")
        return
    print(f"registry: {cs['glyphs']} glyphs (font extension: {cs['font']}); declared charset {cs['declared']} chars, "
          f"{cs['letters']} letters; declared flash {cs['flash_hz']} Hz")
    for u, name in ((0, "low (lowercase)"), (1, "normal (UPPER)"), (2, "critical (UPPER)")):
        forms = [f for row in cs["cases"] for f in row["forms"] if f["urgency"] == u]
        paired = [f for f in forms if f["partner_in_charset"]]
        ok = [f for f in paired if f["case_applied"]]
        q = [f for f in forms if f["key"] == "?"]
        lost = sorted({row["ch"] for row in cs["cases"] for f in row["forms"]
                       if f["urgency"] == u and f["partner_in_charset"] and not f["case_applied"]})
        unpaired = sorted({row["ch"] for row in cs["cases"] for f in row["forms"]
                           if f["urgency"] == u and not f["partner_in_charset"]})
        print(f"  {name:18s} {len(ok)} of {len(paired)} letters rasterise in their displayed case; "
              f"{len(q)} render '?'; case lost: {''.join(lost) or '-'}; partner outside the charset: {''.join(unpaired) or '-'}")
    for rng, u in (("abcdefghijklmnopqrstuvwxyz", 0), ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", 1)):
        have = [row["ch"] for row in cs["cases"] if row["ch"] in rng
                for f in row["forms"] if f["urgency"] == u and f["case_applied"]]
        print(f"  {rng[0]}-{rng[-1]}: {len(have)} of {len(rng)} have their own glyph")


def listing(m):
    for c in m["cases"]:
        print(f"{c['variant']}  grid pitch={c['grid']['pitch']} rows={c['grid']['rows']}")
        for n, _ in URGENCIES:
            f = c["urgencies"][n]
            t = c["temporal"][n]
            print(f"  {n:9s} gray: lit {f['gray']['lit_cells']:4d} mass {f['gray']['mass']:.2f} "
                  f"foot {f['gray']['footprint']:.3f} ul {f['gray']['underline']:.2f} | frames covered "
                  f"{t['covered']:3d} dark {t['dark']:3d} edges {t['edges']:2d} -> {t['hz']:.2f} Hz, "
                  f"steady_min {t['steady_min']:.2f}")
        for p in c["pairs"]:
            print(f"  {p['a']}~{p['b']}: shape {p['shape']:.3f} (worst view {p['view']}, shift {p['shift']}); "
                  f"footprint ratio {p['footprint_ratio']}, mass ratio {p['mass_ratio']}")
        pz = c["pause"]
        print(f"  paused: {pz['paused_dark']} of {pz['paused_samples']} held samples dark "
              f"({pz['running_dark']} dark while running)")
    for w in m["withheld"]:
        print(f"  withheld {w['variant']}: {w['reason']}")
    charset_listing(m.get("charset"))
    print(f"\ncheck_urgency_cues: {len(m['cases'])} variant(s) measured, {len(m['withheld'])} withheld "
          f"(the verdict: scripts/opa_gate.py urgency_cues)")


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
        i = args.index("--cells")
        if i + 2 >= len(args):
            print("check_urgency_cues: --cells needs PNG VARIANT", file=sys.stderr)
            return 2
        return cells_report(args[i + 1], args[i + 2])
    if "--replay" in args:
        i = args.index("--replay")
        if i + 3 >= len(args):
            print("check_urgency_cues: --replay needs FRAMES_DIR STILL_PNG VARIANT", file=sys.stderr)
            return 2
        print(json.dumps(replay(args[i + 1], args[i + 2], args[i + 3])))
        return 0
    if "--bold" in args:
        # ⟐W72.f: DIAGNOSTIC — bold vs regular footprint, one variant, stills kept
        i = args.index("--bold")
        if i + 1 >= len(args):
            print("check_urgency_cues: --bold needs OUT_DIR", file=sys.stderr)
            return 2
        os.makedirs(args[i + 1], exist_ok=True)
        print(json.dumps(bold_facts(opts.get("--variant") or "EL-Openglo", args[i + 1]), indent=1))
        return 0
    for a in args:
        if a not in {"--json", "--list", "--selftest", "--charset"}:
            print(f"check_urgency_cues: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--charset" in args:
        charset_listing(charset_facts())
        return 0
    if "--json" in args or "--list" in args:
        m = measure(opts.get("--variant"), opts.get("--stills"))
        if "--json" in args:
            print(json.dumps(m, indent=1))
        else:
            listing(m)
        return 0
    print("usage: check_urgency_cues.py --json | --list [--stills DIR] [--variant NAME] | --charset | "
          "--cells PNG VARIANT | --selftest  (the verdict: scripts/opa_gate.py urgency_cues)", file=sys.stderr)
    return 2


# ── the selftest: synthetic boards drawn the way ApertureField draws them ─────────

H_GLYPH = [0x7F, 0x08, 0x08, 0x08, 0x7F]      # an 'H', 5 columns x 7 rows
h_GLYPH = [0x7F, 0x08, 0x04, 0x04, 0x78]      # an 'h'


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


def synth_coverage(glyph=H_GLYPH, level=1.0, n=8, start=20, underline=False, cols=105, rows=8):
    """Backdrop coverage of n glyphs at `level` (0.25 = the same dots as the aperture
    renders a shrunk one: an opacity-only cue)."""
    cov = [[0.0] * cols for _ in range(rows)]
    for k in range(n):
        for c, byte in enumerate(glyph):
            for r in range(rows):
                if bool(byte & (1 << r)) or (underline and r == rows - 1):
                    x = start + k * 6 + c
                    if x < cols:
                        cov[r][x] = level
    return cov


def _selftest():
    """The measurement can SEE: an opacity-only low (the same pips at a quarter) and a
    hue-only critical are INDISTINGUISHABLE by shape while their mass differs; a
    lowercase low and an underlined critical ARE distinguishable; the grid is found from
    pixels; the frame arm sees a flash's edges and rate and a steady series' none."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    ground = (6, 11, 13)
    normal = ink_views(synth_board(synth_coverage()), ground)
    dim = ink_views(synth_board(synth_coverage(level=0.25)), ground)
    lower = ink_views(synth_board(synth_coverage(h_GLYPH)), ground)
    crit = ink_views(synth_board(synth_coverage(underline=True), lit=(240, 90, 60)), ground)
    hot = ink_views(synth_board(synth_coverage(), lit=(240, 90, 60)), ground)
    chk("the grid is found from the pixels (pitch 4, 8 rows)",
        (normal["_grid"]["pitch"], normal["_grid"]["rows"]), (4, 8))
    c = judge_variant("fixture", {"low": dim, "normal": normal, "critical": crit})
    pr = {(p["a"], p["b"]): p for p in c["pairs"]}
    chk("an opacity-only low is INDISTINGUISHABLE by shape (0 lit pips differ)", pr[("low", "normal")]["shape"], 0.0)
    chk("...while its brightness differs (the cue is there, but it is opacity)",
        float(dim["gray"].max()) < 0.5 * float(normal["gray"].max()), True)
    chk("an underlined critical IS distinguishable from normal by shape", pr[("normal", "critical")]["shape"] > 0.2, True)
    chk("the critical still's underline row is lit, the normal one's is not",
        (c["urgencies"]["critical"]["gray"]["underline"] > 0.5, c["urgencies"]["normal"]["gray"]["underline"]), (True, 0.0))
    c2 = judge_variant("fixture-hue", {"low": lower, "normal": normal, "critical": hot})
    pr2 = {(p["a"], p["b"]): p for p in c2["pairs"]}
    chk("a hue-only critical is INDISTINGUISHABLE by shape", pr2[("normal", "critical")]["shape"], 0.0)
    chk("a lowercase low IS distinguishable from upper case by shape", pr2[("low", "normal")]["shape"] > 0.2, True)
    chk("a one-cell slip between stills is not credited as shape",
        shape_difference(lit_set(normal["gray"]), np.roll(lit_set(normal["gray"]), 1, axis=1))[0], 0.0)
    # the frame arm, on a synthetic series: 4 Hz edges over 40 ms samples (2 Hz flash)
    import tempfile
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        lit_img = synth_board(synth_coverage(n=17, start=0))
        dark_img = synth_board(synth_coverage(n=17, start=0, level=0.0))
        frames = []
        for k in range(50):
            t = k * 40
            img = lit_img if (t // 250) % 2 == 0 else dark_img
            Image.fromarray(img.astype(np.uint8)).save(os.path.join(td, f"frame-{k:03d}.png"))
            frames.append({"t": t, "x": -10})
        res = {"width": 420, "samples": [{"w": 1000}], "frames": frames}
        g = ink_views(lit_img, ground)["_grid"]
        tf = temporal_facts(res, td, ground, g)
        chk("a 2 Hz flash is seen as 2 Hz (+-0.25)", abs(tf["hz"] - 2.0) <= 0.25, True)
        chk("...with dark frames", tf["dark"] > 10, True)
        for k in range(50):
            Image.fromarray(lit_img.astype(np.uint8)).save(os.path.join(td, f"frame-{k:03d}.png"))
        steady = temporal_facts(res, td, ground, g)
        chk("a steady series has no edges and no dark frame", (steady["edges"], steady["dark"]), (0, 0))
        chk("an uncovered series (text never spans the board) is 0 covered frames",
            temporal_facts(dict(res, samples=[{"w": 100}]), td, ground, g)["covered"], 0)
    chk("the population is the six variants", len(variants()), 6)
    print("check_urgency_cues selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
