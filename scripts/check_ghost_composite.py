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

    scripts/check_ghost_composite.py            # exit 0 iff the rendered ghost clears its floor
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

# How far under the ceiling a looked-at seen ghost may sit and still count as
# ON TARGET: the 8-bit stepping in derive_ghost_through_alpha lands 0.1-0.4 Lc
# under; a whole Lc is the widest that stepping can cost. Azure's 5.0 shortfall
# (W23) is a different kind of number.
TARGET_SLACK = 1.0


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
# ⚑ A DOT IS THE STROKE'S COMPOSITE; A DOT FIELD IS NOT.  MatrixChar draws every
# unlit dot at the same ghostAlpha SegmentChar draws its core, so per DOT the
# seen ghost is identical to the stroke ghost. But a dot covers only
# dotFill^2 * pi/4 of its cell, and at a glance the eye averages the cell: the
# FIELD's mean colour is the dot composite lerped toward ground by the coverage
# — i.e. an effective alpha of ghostAlpha * coverage. That is the density
# question the log left open at s65 (:4519): the same alpha reads as a thinner
# texture on the matrix than on a stroke, by exactly this factor.

def matrix_dot_fill():
    """MatrixChar's dotFill, parsed from the EMITTED component (not the template
    hole): None if the property is absent."""
    import make_notify_marquee
    for line in make_notify_marquee.matrix_char_component().splitlines():
        s = line.strip()
        if s.startswith("property real dotFill:"):
            return float(s.split(":", 1)[1].split("//")[0].strip())
    return None


def matrix_rendered_alpha(variant_id):
    """The ghostAlpha the EMITTED marquee passes to MatrixChar for `variant_id`."""
    import make_notify_marquee
    for line in make_notify_marquee.main_qml(variant_id).splitlines():
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


def _matrix_report():
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
    known = {"--compare", "--selftest", "--solve", "--mode", "looked", "glanced", "--matrix"}
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

    rows = measure()
    if not rows:
        print("check_ghost_composite: REFUSED — no variants; the grid is not built, "
              "not the ghost visible", file=sys.stderr)
        return 2

    if "--compare" in argv:
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

    bad = []
    # ⚑ THE BAND IS NOT THE TARGET.  Until 2026-09-21 the looked-at ghost passed
    # this check on EL-Azure at Lc 25.0 — inside [25, 30) — while every other
    # variant sat at ~29.8: the global alpha reached Azure's FLOOR and no further
    # (W23). The relation's target is the ceiling; a seen ghost more than
    # TARGET_SLACK under it is the solve landing short, not a different taste.
    # Glanced mode has its own (lower) alpha and is not held to the ceiling.
    if MODE == "looked_at":
        for vid, decl, comp, floor, lc_d, lc_c in rows:
            if lc_c < C.GHOST_READABLE_LC - TARGET_SLACK:
                bad.append(f"{vid}: the seen ghost sits at Lc {lc_c:.1f}, more than "
                           f"{TARGET_SLACK} under the {C.GHOST_READABLE_LC} ceiling it is "
                           f"solved toward — the alpha reaches this variant's floor, not "
                           f"its target (W23)")
    for vid, decl, comp, floor, lc_d, lc_c in rows:
        if lc_c < floor:
            bad.append(f"{vid}: the ghost renders at Lc {lc_c:.1f} against a floor "
                       f"of Lc {floor:.1f} — it is declared at Lc {lc_d:.1f} and "
                       f"drawn at alpha {_alpha()}, so {lc_d - lc_c:.1f} Lc lives "
                       f"between the check and the screen (WCAG {decl:.2f} → {comp:.2f})")
        if lc_c >= C.GHOST_READABLE_LC:
            bad.append(f"{vid}: the composited ghost reads at Lc {lc_c:.1f}, at or "
                       f"over the {C.GHOST_READABLE_LC} readability ceiling — it "
                       f"would render as TEXT rather than as texture")
    if bad:
        n_bad = len({b.split(":")[0] for b in bad})
        print(f"check_ghost_composite: REFUSED — {n_bad} of {len(rows)} "
              f"variant(s) render a ghost their gate did not measure:",
              file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    # ⚑ THE MEASUREMENT ABOVE USED THE SOLVED ALPHA; THE SCREEN MUST USE IT TOO.
    # If the emitted component carries a different number, everything above was
    # measured against an alpha nobody renders — the original defect, one level up.
    # In glanced mode the component question is check_ghost_surfaces' (which
    # surface draws which mode's alpha); SegmentChar carries the looked-at one.
    rendered = rendered_alpha() if MODE == "looked_at" else _alpha()
    if rendered is None or abs(rendered - _alpha()) > 1e-9:
        print(f"check_ghost_composite: REFUSED — the emitted SegmentChar.qml carries "
              f"ghostAlpha={rendered}, not the solved {_alpha()}; the gate measured "
              f"an alpha the screen does not draw", file=sys.stderr)
        return 1
    worst = min(lc for _v, _d, _c, _f, _a, lc in rows)
    print(f"check_ghost_composite: {len(rows)} of {len(rows)} variants render a "
          f"ghost that clears its floor and stays under its ceiling (worst Lc "
          f"{worst:.1f}, alpha {_alpha()}, carried by the emitted component)")
    return 0


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
    check("the emitted marquee carries the solved alpha",
          matrix_rendered_alpha(variants()[0][0]) == _alpha() if variants() else False, True)

    saved = globals()["measure"]
    saved_r = globals()["rendered_alpha"]
    try:
        # a hypothetical palette whose composited ghost sits between its bounds
        # rows: (id, wcag_decl, wcag_comp, FLOOR_LC, lc_decl, lc_comp)
        globals()["measure"] = lambda: [("SELFTEST-OK", 9.0, 4.0, 25.0, 60.0, 29.5)]
        check("a clearing palette passes", main(["x"]), 0)
        # ⚑ INSIDE THE BAND BUT SHORT OF THE TARGET — Azure's shape on 2026-09-21
        # (Lc 25.0 exactly, in [25, 30)) must be seen, not passed.
        globals()["measure"] = lambda: [("SELFTEST-SHORT", 9.0, 3.6, 25.0, 72.0, 25.0)]
        check("a looked-at ghost on its floor, 5 Lc under its target, is seen", main(["x"]), 1)
        # ⚑ ...but NOT if the screen draws a different alpha than was measured.
        globals()["rendered_alpha"] = lambda: 0.45
        check("a clearing palette whose component carries a stale alpha is REFUSED",
              main(["x"]), 1)
        globals()["rendered_alpha"] = lambda: None
        check("...and so is a component with no ghostAlpha property at all",
              main(["x"]), 1)
        globals()["rendered_alpha"] = saved_r
        # and one whose composited ghost reads as TEXT — the other bound
        globals()["measure"] = lambda: [("SELFTEST-LOUD", 9.0, 8.0, 25.0, 60.0, 35.0)]
        check("a ghost over the readability ceiling is seen", main(["x"]), 1)
        # and one under its floor — the original defect, still seeable
        globals()["measure"] = lambda: [("SELFTEST-DIM", 4.0, 1.8, 25.0, 60.0, 8.0)]
        check("a ghost under its floor is seen", main(["x"]), 1)
        # ⚑ THE LIT CASE THAT MOTIVATED THE METRIC CHANGE: WCAG 1.9:1 but Lc 29.7 —
        # under the OLD floor, between the bounds under the one that is stated now.
        globals()["measure"] = lambda: [("SELFTEST-LIT", 4.0, 1.9, 25.0, 57.0, 29.7)]
        globals()["rendered_alpha"] = saved_r
        check("a light-ground ghost at 1.9:1 / Lc 29.7 PASSES (one metric)", main(["x"]), 0)
        globals()["measure"] = lambda: []
        check("an empty population REFUSES", main(["x"]), 2)
    finally:
        globals()["measure"] = saved
        globals()["rendered_alpha"] = saved_r

    print("check_ghost_composite selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
