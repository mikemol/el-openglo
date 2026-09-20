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
(a second, wider, fainter pass) or the matrix surface's own `ghostOpacity: 0.28`.
Those are further instances of the same shape and are recorded rather than gated —
a check that claimed to cover them would be asserting more than it measures.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cvd_gate as C                                              # noqa: E402
import palette_graph as PG                                        # noqa: E402


def _alpha():
    """The alpha the renderer is filled with — the palette authority's, not a copy."""
    import make_schemes
    return make_schemes.GHOST_ALPHA


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
            C.feasible_ghost_floor_lc(lit, ground),
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
    known = {"--compare", "--selftest", "--solve"}
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
        print(f"check_ghost_composite: REFUSED — {len(bad)} of {len(rows)} "
              f"variant(s) render a ghost their gate did not measure:",
              file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    # ⚑ THE MEASUREMENT ABOVE USED THE SOLVED ALPHA; THE SCREEN MUST USE IT TOO.
    # If the emitted component carries a different number, everything above was
    # measured against an alpha nobody renders — the original defect, one level up.
    rendered = rendered_alpha()
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

    saved = globals()["measure"]
    saved_r = globals()["rendered_alpha"]
    try:
        # a hypothetical palette whose composited ghost sits between its bounds
        # rows: (id, wcag_decl, wcag_comp, FLOOR_LC, lc_decl, lc_comp)
        globals()["measure"] = lambda: [("SELFTEST-OK", 9.0, 4.0, 25.0, 60.0, 27.0)]
        check("a clearing palette passes", main(["x"]), 0)
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
