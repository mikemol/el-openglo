#!/usr/bin/env python3
"""check_ghost_composite.py — the ghost the GATE certifies is the ghost the EYE sees.

⚑ THE DEFECT THIS MEASURES SPANS TWO CONCERNS AND SO NO SINGLE-CONCERN CHECK COULD
SEE IT.  `SegmentChar.qml:73` draws the unlit core at `opacity: 0.45`. Every colour
check in this tree measures `fg_in` against `view` DIRECTLY, and none of them knows
that number exists — so the contrast that is gated and the contrast that renders
are different quantities.

Measured on the shipped palette:

    variant           declared   composited
    EL-Openglo          4.16:1       1.79:1     against a floor of 3.00
    EL-Azure            4.27:1       1.77:1
    EL-Amber            4.20:1       1.79:1
    ...and the three Lit variants are already under the floor BEFORE compositing.

    scripts/check_ghost_composite.py            # the verdict, as opa_gate ghost_composite decides it
    scripts/check_ghost_composite.py --json     # the measurement policy/ghost_composite.rego decides
    scripts/check_ghost_composite.py --mode glanced   # the verdict for the glanced-at alpha
    scripts/check_ghost_composite.py --compare  # declared vs composited, per variant
    scripts/check_ghost_composite.py --selftest

⚑ THE SOLVE OPTIMISES THE BOUND THAT IS NOT IN DANGER.  The ghost has two
requirements pulling opposite ways: a CEILING (|Lc| < 30, it must not read as text)
and a FLOOR (it must still read as shape). Alpha makes the ceiling SAFER and the
floor HARDER. Measured: |Lc| is 29.8 declared and 7.7 composited against a limit of
30 — the shipped `derive_ghost_ceiling` is pushing hard against a bound with a 22
point margin, while the floor it does not model is missed on every variant.

⚑ AND THE THREE KNOBS ARE ONE QUANTITY.  Ghost subordination is carried by its
COLOUR, its ALPHA (0.45) and its WIDTH (ghostHalf/litHalf = 0.65) multiplying
together. Trading any one against the others is invisible to a check that sees only
colours or only lengths, which is why this check exists at the join rather than in
either family.

⚑ THE WEAKNESS, STATED.  This models source-over compositing of a flat alpha, which
is what the QML does for the unlit CORE. It does NOT model the lit bloom underlay
(a second, wider, fainter pass). The matrix surface is MEASURED, not gated
(`--matrix`, ⊕GHOST-DENSITY, session 80): per dot its ghost is the stroke ghost,
as a field it is thinned by the dot's coverage — Lc ~10 against a 25 floor on
every variant — and whether the eye reads a dot field per dot or per cell is not
a thing this arithmetic can decide.

    scripts/check_ghost_composite.py --matrix   # the dot field's ghost beside the stroke's
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cvd_gate as C                                              # noqa: E402
import palette_graph as PG                                        # noqa: E402


# The parsing mode under measurement (W12): looked-at surfaces draw ghost_alpha,
# glanced-at ones ghost_alpha_glanced, and each mode has its own ground floor.
MODE = "looked_at"

# How far under the ceiling a looked-at seen ghost may sit and still count as ON
# TARGET is policy/ghost_composite.rego's `target_slack` since W50.


def _alpha():
    """The alpha the renderer is filled with — the palette authority's, not a copy."""
    import make_schemes
    if MODE == "looked_at":
        return make_schemes.GHOST_ALPHA
    seen = set()
    for value in make_schemes.GRID.values():
        t = value[0] if isinstance(value, (list, tuple)) else value
        if isinstance(t, dict) and "view" in t:
            seen.add(t.get("ghost_alpha_glanced", t.get("ghost_alpha", "0.45")))
    if len(seen) != 1:
        raise ValueError(f"GRID carries {len(seen)} distinct ghost_alpha_glanced values")
    return float(seen.pop())


def rendered_alpha():
    """The alpha the EMITTED SegmentChar.qml actually carries, parsed back out.

    ⚑ THE CHECK MUST READ THE ARTIFACT, NOT TRUST THE HOLE.  A template hole that
    was renamed, or a render that fell back to a stale baseline, would leave the
    emitted QML at the old literal while `make_schemes` reports the solved value.
    Returns None if no `ghostAlpha:` property is present."""
    import make_segment_display
    for line in make_segment_display.segment_char_component().splitlines():
        s = line.strip()
        if s.startswith("property real ghostAlpha:"):
            return float(s.split(":", 1)[1].strip())
    return None


def variants():
    """[(id, ground, lit, ghost)] for every shipped variant."""
    import make_schemes
    grid = getattr(make_schemes, "GRID", None) or {}
    out = []
    for value in (grid.values() if isinstance(grid, dict) else grid):
        for scheme in (value if isinstance(value, (list, tuple)) else (value,)):
            if isinstance(scheme, dict) and "view" in scheme:
                out.append((
                    scheme.get("id", "?"),
                    tuple(int(x) for x in scheme["view"].split(",")),
                    tuple(int(x) for x in scheme["fg"].split(",")),
                    tuple(int(x) for x in scheme["fg_in"].split(",")),
                ))
                break
    return out


def measure():
    """[(id, declared, composited, floor_lc, lc_declared, lc_composited)].

    `declared`/`composited` are WCAG ratios, kept for the reader; the FLOOR is
    APCA (`cvd_gate.feasible_ghost_floor_lc`) and is judged against
    `lc_composited` — the same metric as the ceiling, so the two bounds behave
    the same way on a light ground as on a dark one."""
    rows = []
    for vid, ground, lit, ghost in variants():
        comp = PG.composite(ghost, ground, _alpha())
        rows.append((
            vid,
            C.wcag_ratio(ghost, ground),
            C.wcag_ratio(comp, ground),
            C.feasible_ghost_floor_lc(lit, ground, MODE),
            abs(C.apca_Lc(ghost, ground)),
            abs(C.apca_Lc(comp, ground)),
        ))
    return rows


def solve_through_alpha(lit, ground, alpha=None, floor=None, ceiling=None):
    """What fg_in WOULD have to be for the RENDERED ghost to clear floor and ceiling.

    ⚑ THE COMPOSITE IS A POINT ON THE SAME SEGMENT.  Source-over of a flat alpha
    toward `ground` is a lerp toward `ground`, so for a declared ghost at parameter
    t along lit->ground the screen shows

        composite(lerp(lit, ground, t), ground, a) = lerp(lit, ground, 1 - a(1 - t))

    The on-screen point t' = 1 - a(1 - t) is therefore solvable by the SAME
    machinery ghost_solve already owns, and the declared parameter is recovered
    by t = 1 - (1 - t')/a.  Alpha enters the solve; the render is untouched.

    ⚑ AND THE INVERSION CAN LEAVE THE SEGMENT.  t < 0 means the declared colour
    would have to lie BEYOND the lit end — no fg_in at this alpha can render at
    the required contrast.  That is reported as `feasible=False`, never rounded
    to t=0, because rounding would re-create the silent miss this check exists
    to see.

    Returns a dict: t_floor (on-screen t' at which composited WCAG == floor),
    t_ceiling (t' at which |Lc| == ceiling, or None if unreachable), t_screen
    (the chosen t': the floor side, since the ceiling has a 22-point margin),
    t_declared (inverted), fg_in_required, feasible, and what the current
    declared ghost's t is, for the declared-vs-required line."""
    if alpha is None:
        alpha = _alpha()
    if floor is None:
        floor = C.feasible_ghost_floor_lc(lit, ground)
    if ceiling is None:
        ceiling = C.GHOST_READABLE_LC

    import ghost_solve as G
    t_floor = G.solve_floor_t(lit, ground, floor)      # None: even lit fails the floor
    t_ceiling, _lc = G.solve_ceiling_t(lit, ground, ceiling)
    # the floor is the binding side (the ceiling is 22 Lc away composited); the
    # honest on-screen point is the floor's boundary, checked against the ceiling.
    t_screen = t_floor
    feasible = t_screen is not None
    if feasible and t_ceiling is not None and t_screen < t_ceiling:
        feasible = False                     # the floor point would read as text
    t_declared = None
    if feasible:
        t_declared = 1.0 - (1.0 - t_screen) / alpha
        if t_declared < 0.0:
            feasible = False                 # beyond the lit end: alpha too low
    return {
        "t_floor": t_floor, "t_ceiling": t_ceiling, "t_screen": t_screen,
        "t_declared": t_declared, "feasible": feasible,
        "fg_in_required": (C._lerp(lit, ground, t_declared) if feasible else None),
        "alpha_min": (1.0 - t_screen) if t_screen is not None else None,
    }


# ── ⊕GHOST-DENSITY: the dot field beside the stroke ─────────────────────────
#
# ⚑ A DOT IS THE STROKE'S COMPOSITE; A DOT FIELD IS NOT.  The field (ApertureField
# since s120; MatrixChar before, retired s124) draws every unlit pip at the same
# ghostAlpha SegmentChar draws its core, so per DOT the
# seen ghost is identical to the stroke ghost. But a dot covers only
# dotFill^2 * pi/4 of its cell, and at a glance the eye averages the cell: the
# FIELD's mean colour is the dot composite lerped toward ground by the coverage
# — i.e. an effective alpha of ghostAlpha * coverage. That is the density
# question the log left open at s65 (:4519): the same alpha reads as a thinner
# texture on the matrix than on a stroke, by exactly this factor.

def matrix_dot_fill():
    """The field's dotFill, parsed from the EMITTED component (ApertureField; not
    the template hole): None if the property is absent."""
    import make_notify_marquee
    for line in make_notify_marquee.aperture_field_component().splitlines():
        s = line.strip()
        if s.startswith("property real dotFill:"):
            return float(s.split(":", 1)[1].split("//")[0].strip())
    return None


def matrix_rendered_alpha(variant_id):
    """The ghostAlpha the EMITTED marquee passes to its field — ONE package since
    W35, so the same baked (measured-global) alpha for every `variant_id`."""
    import make_notify_marquee
    for line in make_notify_marquee.main_qml().splitlines():
        s = line.strip()
        if s.startswith("property real ghostAlpha:"):
            return float(s.split(":", 1)[1].strip())
    return None


def measure_matrix(dot_fill=None):
    """[(id, lc_stroke, lc_dot, lc_field, coverage, floor_lc, alpha_field_equiv)].

    lc_dot equals lc_stroke by construction when the marquee carries the same
    alpha (asserted separately); lc_field is the area-averaged cell against
    ground; alpha_field_equiv is the alpha a STROKE would need to read like the
    dot field does."""
    import math
    fill = matrix_dot_fill() if dot_fill is None else dot_fill
    if fill is None:
        return []
    coverage = fill * fill * math.pi / 4.0
    rows = []
    for vid, ground, lit, ghost in variants():
        a = _alpha()
        dot = PG.composite(ghost, ground, a)
        field = PG.composite(dot, ground, coverage)
        rows.append((vid, abs(C.apca_Lc(dot, ground)), abs(C.apca_Lc(dot, ground)),
                     abs(C.apca_Lc(field, ground)), coverage,
                     C.feasible_ghost_floor_lc(lit, ground, MODE), a * coverage))
    return rows


def format_coverage(fmt):
    """The fraction of the 2x4 cell an unlit FIELD of format `fmt` covers — the
    union of its strokes' bands at the module stroke width (MODULE_METRICS,
    0.105 H), rasterised on glyph_match's cell grid. 22 uses every SEG22 stroke;
    the others use segment_topology.FORMATS[fmt]['mask'] over GEOM16."""
    import numpy as np
    import glyph_match as GM
    import segment_topology as ST
    sw = ST.metrics(4.0)["stroke"] / 2.0
    keys = list(ST.SEG22) if fmt == "22" else [k for k in ST.GEOM16 if k in ST.FORMATS[fmt]["mask"]]
    if not keys:
        return None
    field = np.zeros((GM.RES + 1, GM.RES + 1), bool)
    for k in keys:
        field |= GM._seg_field(ST.endpoints(k), (0.0, 2.0, 0.0, 4.0), sw)
    return float(field.mean()), len(keys)


def measure_formats(fmts=("7", "14", "16", "22")):
    """[(fmt, strokes, coverage, alpha_field_equiv)] — the segment twin of
    measure_matrix: at the 22-join the same cell carries 22 strokes at the same
    width, so the unlit FIELD is denser than at 7 by exactly this coverage."""
    out = []
    for f in fmts:
        r = format_coverage(f)
        if r is None:
            continue
        cov, n = r
        out.append((f, n, cov, _alpha() * cov))
    return out


def _matrix_report():
    rows = measure_matrix()
    fmts = measure_formats()
    if fmts:
        print("segment formats — the unlit FIELD's cell coverage at the module stroke width:")
        for f, n, cov, a_eq in fmts:
            print(f"  {f:>3}-seg  {n:2d} strokes  coverage {cov:.3f}  field alpha {a_eq:.3f}")
        print()
    rows = measure_matrix()
    if not rows:
        print("check_ghost_composite: REFUSED — no variants, or MatrixChar carries no dotFill",
              file=sys.stderr)
        return 2
    fill = matrix_dot_fill()
    print(f"alpha = {_alpha()}; MatrixChar dotFill = {fill} -> a dot covers "
          f"{rows[0][4]:.3f} of its cell; the field's effective alpha is {rows[0][6]:.3f}\n")
    print(f"{'variant':18s} {'Lc stroke':>9s} {'Lc dot':>7s} {'Lc field':>9s} {'floor':>6s}  marquee alpha")
    agree = 0
    for vid, lc_s, lc_d, lc_f, cov, floor, a_eq in rows:
        ma = matrix_rendered_alpha(vid)
        same = ma is not None and abs(ma - _alpha()) < 1e-9
        agree += same
        flag = "" if lc_f >= floor else "  ⚑ FIELD UNDER FLOOR"
        print(f"{vid:18s} {lc_s:9.1f} {lc_d:7.1f} {lc_f:9.1f} {floor:6.1f}  "
              f"{ma}{'' if same else '  ⚑ NOT THE SOLVED ALPHA'}{flag}")
    print(f"\n{agree} of {len(rows)} marquee emissions carry the solved alpha; per dot the ghost "
          f"is the stroke ghost, as a FIELD it reads {rows[0][6]/_alpha():.2f}x as dense "
          f"(reported, not gated: whether the eye judges a dot field per dot or per cell is "
          f"⊕GLANCE-CALIBRATE's live question)")
    return 0 if agree == len(rows) else 1


def _solve_report():
    print(f"alpha = {_alpha()}; the on-screen ghost is lerp(lit, ground, 1 - "
          f"alpha(1 - t)), so fg_in is solved on the SAME segment through alpha.\n")
    print(f"{'variant':18s} {'declared':>18s} {'required':>18s} {'t_decl':>7s} "
          f"{'a_min':>6s}  feasible")
    n_ok = 0
    rows = variants()
    for vid, ground, lit, ghost in rows:
        s = solve_through_alpha(lit, ground)
        req = s["fg_in_required"]
        req_s = ",".join(str(int(round(c))) for c in req) if req else "—"
        t_s = f"{s['t_declared']:.3f}" if s["t_declared"] is not None else "  <0  "
        a_s = f"{s['alpha_min']:.2f}" if s["alpha_min"] is not None else "  —"
        n_ok += bool(s["feasible"])
        print(f"{vid:18s} {','.join(map(str, ghost)):>18s} {req_s:>18s} {t_s:>7s} "
              f"{a_s:>6s}  {'yes' if s['feasible'] else 'NO — alpha too low'}")
    print(f"\n{n_ok} of {len(rows)} variants can clear the floor at alpha "
          f"{_alpha()}; a_min is the smallest alpha at which fg_in = lit would.")
    solved, rendered = _alpha(), rendered_alpha()
    agree = rendered is not None and abs(solved - rendered) < 1e-9
    print(f"SOLVED global alpha (make_schemes.GHOST_ALPHA) = {solved}; the emitted "
          f"SegmentChar.qml carries ghostAlpha = {rendered} — "
          f"{'agree' if agree else 'DISAGREE: the emitted component does not carry the solved value'}")
    return 0


def main(argv):
    global MODE
    known = {"--compare", "--selftest", "--solve", "--mode", "looked", "glanced", "--matrix", "--json"}
    if "--matrix" in argv:
        return _matrix_report()
    if "--mode" in argv:
        i = argv.index("--mode")
        if i + 1 >= len(argv) or argv[i + 1] not in ("looked", "glanced"):
            print("check_ghost_composite: --mode needs `looked` or `glanced`", file=sys.stderr)
            return 2
        MODE = "looked_at" if argv[i + 1] == "looked" else "glanced_at"
    if "--solve" in argv:
        if not variants():
            print("check_ghost_composite: REFUSED — no variants", file=sys.stderr)
            return 2
        return _solve_report()
    for a in argv[1:]:
        if a not in known:
            print(f"check_ghost_composite: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measurement(), indent=1))
        return 0

    if "--compare" in argv:
        rows = measure()
        if not rows:
            print("check_ghost_composite: REFUSED — no variants", file=sys.stderr)
            return 2
        print(f"alpha = {_alpha()} (make_schemes.GHOST_ALPHA, filled into "
              f"SegmentChar.qml's $ghostAlpha), applied at render\n")
        print(f"{'variant':18s} {'wcag decl':>9s} {'wcag comp':>11s} "
              f"{'Lc decl':>8s} {'Lc comp':>8s} {'Lc floor':>9s}")
        for vid, decl, comp, floor, lc_d, lc_c in rows:
            flag = ("" if lc_c >= floor else "  ⚑ UNDER") + \
                   ("" if lc_c < C.GHOST_READABLE_LC else "  ⚑ OVER CEILING")
            print(f"{vid:18s} {decl:8.2f}: {comp:10.2f}: "
                  f"{lc_d:8.1f} {lc_c:8.1f} {floor:9.1f}{flag}")
        print(f"\nfloor and ceiling are both APCA: {C.GHOST_VISIBLE_LC} <= |Lc| < "
              f"{C.GHOST_READABLE_LC}, judged on the COMPOSITED ghost.")
        return 0

    import opa_gate
    return opa_gate.gate("ghost_composite", ["--mode", "looked" if MODE == "looked_at" else "glanced"])


def measurement():
    """The MEASUREMENT policy/ghost_composite.rego decides (W50): the parsing mode,
    the solved alpha, the readability ceiling (cvd_gate's, the palette
    authority's constant — an input, not a copy), the alpha the EMITTED
    SegmentChar.qml carries (looked-at mode only: in glanced mode which surface
    draws which alpha is check_ghost_surfaces' question, so it is null), and per
    variant the declared and composited WCAG and |Lc| and its APCA floor. The
    band, the W23 target slack and "the screen draws the solved alpha" are the
    policy's ruling, not here."""
    return {"mode": MODE, "alpha": _alpha(), "ceiling": C.GHOST_READABLE_LC,
            "rendered_alpha": rendered_alpha() if MODE == "looked_at" else None,
            "cases": [{"id": vid, "wcag_declared": decl, "wcag_composited": comp,
                       "floor_lc": floor, "lc_declared": lc_d, "lc_composited": lc_c}
                      for vid, decl, comp, floor, lc_d, lc_c in measure()]}


def _selftest():
    """Prove the composite is modelled and that the check can fail either way."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # ⚑ THE COMPOSITE ITSELF, against values chosen so the answer is arithmetic.
    check("alpha 1.0 is the source unchanged",
          PG.composite((10, 20, 30), (200, 200, 200), 1.0), (10, 20, 30))
    check("alpha 0.0 is the ground unchanged",
          PG.composite((10, 20, 30), (200, 200, 200), 0.0), (200, 200, 200))
    check("alpha 0.5 is the midpoint",
          PG.composite((0, 0, 0), (200, 200, 200), 0.5), (100, 100, 100))

    # ⚑ THE SOLVE'S PREMISE IS AN IDENTITY, AND IT IS CHECKED HERE, NOT ASSUMED.
    # composite(lerp(l, g, t), g, a) must equal lerp(l, g, 1 - a(1 - t)) to within
    # 8-bit rounding, or the inversion through alpha is solving the wrong segment.
    lit0, gnd0, a0, t0 = (240, 200, 60), (20, 24, 30), 0.45, 0.3
    lhs = PG.composite(C._lerp(lit0, gnd0, t0), gnd0, a0)
    rhs = C._lerp(lit0, gnd0, 1.0 - a0 * (1.0 - t0))
    check("composite of a segment point is a segment point",
          all(abs(x - y) <= 1 for x, y in zip(lhs, rhs)), True)
    # ⚑ AND THE INVERSION ROUND-TRIPS: the required fg_in, composited, clears the floor.
    s = solve_through_alpha(lit0, gnd0, alpha=1.0)          # alpha 1: screen == declared
    check("at alpha 1 the required ghost IS the on-screen ghost",
          s["feasible"] and abs(s["t_declared"] - s["t_screen"]) < 1e-9, True)
    s = solve_through_alpha(lit0, gnd0, alpha=0.05)         # near-invisible: infeasible
    check("an alpha too low to reach the floor is REFUSED, not rounded",
          s["feasible"], False)

    rows = measure()
    check("population is non-empty", len(rows) > 0, True)
    # ⚑ COMPOSITING MUST LOWER THE CONTRAST, or the model is not modelling.
    check("compositing lowers contrast on every variant",
          all(c < d for _v, d, c, _f, _a, _b in rows), True)

    # ⚑ THE EMITTED COMPONENT CARRIES THE SOLVED ALPHA — parsed back out of the
    # rendered QML, not read from the hole.  This is the arm that turns "wired"
    # from a claim into a measurement.
    check("the emitted SegmentChar.qml carries the solved alpha",
          rendered_alpha() is not None and abs(rendered_alpha() - _alpha()) < 1e-9,
          True)

    # ⚑ ⊕GHOST-DENSITY: the dot field is the dot composite thinned by coverage,
    # and the arm must SEE a coverage change. dotFill 1.0 -> coverage pi/4; a
    # field can never be denser than its dots; a full cell (coverage 1) IS the dot.
    import math
    m1 = measure_matrix(dot_fill=1.0)
    check("dotFill 1.0 covers pi/4 of the cell", m1 and abs(m1[0][4] - math.pi / 4) < 1e-9, True)
    check("a field is never denser than its dots", all(r[3] <= r[2] + 1e-9 for r in m1), True)
    m_full = measure_matrix(dot_fill=math.sqrt(4 / math.pi))      # coverage exactly 1
    check("at coverage 1 the field IS the dot", all(abs(r[3] - r[2]) < 0.6 for r in m_full), True)
    m_small = measure_matrix(dot_fill=0.5)
    check("a smaller dot thins the field", all(s[3] < b[3] for s, b in zip(m_small, m1)), True)
    check("the emitted MatrixChar carries a dotFill", matrix_dot_fill() is not None, True)
    # the segment twin: coverage is a fraction, grows with the format, and an
    # unknown format is None rather than a number
    fm = {f: cov for f, _n, cov, _a in measure_formats()}
    check("every format's coverage is in (0, 1]", all(0 < c <= 1 for c in fm.values()), True)
    check("22-seg covers at least 16-seg covers at least 7-seg",
          fm.get("22", 0) >= fm.get("16", 0) >= fm.get("7", 1), True)
    check("7-seg leaves more than half the cell unlit-and-empty", fm.get("7", 1) < 0.5, True)
    try:
        format_coverage("99")
        check("an unknown format refuses", False, True)
    except KeyError:
        check("an unknown format refuses", True, True)
    check("the emitted marquee carries the solved alpha",
          matrix_rendered_alpha(variants()[0][0]) == _alpha() if variants() else False, True)

    # ⚑ THE MEASUREMENT CARRIES WHAT THE POLICY JUDGES (W50): the band, the W23
    # target, a stale or absent emitted alpha and an empty population are
    # policy/ghost_composite_test.rego's refusing cases, not arms here.
    m = measurement()
    check("the measurement carries the emitted alpha in looked-at mode",
          m["rendered_alpha"] is not None and abs(m["rendered_alpha"] - m["alpha"]) < 1e-9, True)
    check("...one case per variant", len(m["cases"]), len(variants()))

    print("check_ghost_composite selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
