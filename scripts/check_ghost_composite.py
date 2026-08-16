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
    """[(id, declared, composited, floor, lc_declared, lc_composited)]."""
    rows = []
    for vid, ground, lit, ghost in variants():
        comp = PG.composite(ghost, ground)
        rows.append((
            vid,
            C.wcag_ratio(ghost, ground),
            C.wcag_ratio(comp, ground),
            C.feasible_ghost_floor(lit, ground),
            abs(C.apca_Lc(ghost, ground)),
            abs(C.apca_Lc(comp, ground)),
        ))
    return rows


def main(argv):
    known = {"--compare", "--selftest"}
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
        print(f"alpha = {PG.GHOST_ALPHA} (SegmentChar.qml:73), applied at render "
              f"and invisible to every colour check\n")
        print(f"{'variant':18s} {'declared':>9s} {'composited':>11s} {'floor':>7s} "
              f"{'Lc decl':>8s} {'Lc comp':>8s}")
        for vid, decl, comp, floor, lc_d, lc_c in rows:
            flag = "" if comp >= floor else "  ⚑ UNDER"
            print(f"{vid:18s} {decl:8.2f}: {comp:10.2f}: {floor:7.2f} "
                  f"{lc_d:8.1f} {lc_c:8.1f}{flag}")
        print(f"\nceiling is {C.GHOST_READABLE_LC}; the composited Lc is far under "
              f"it, so the solve is optimising against the bound NOT in danger.")
        return 0

    bad = []
    for vid, decl, comp, floor, _lc_d, lc_c in rows:
        if comp < floor:
            bad.append(f"{vid}: the ghost renders at {comp:.2f}:1 against a floor "
                       f"of {floor:.2f} — it is gated at {decl:.2f}:1 and drawn at "
                       f"alpha {PG.GHOST_ALPHA}, so {decl - comp:.2f} of contrast "
                       f"lives between the check and the screen")
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
    worst = min(c for _v, _d, c, _f, _a, _b in rows)
    print(f"check_ghost_composite: {len(rows)} of {len(rows)} variants render a "
          f"ghost that clears its floor (worst {worst:.2f}:1, alpha "
          f"{PG.GHOST_ALPHA})")
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

    rows = measure()
    check("population is non-empty", len(rows) > 0, True)
    # ⚑ COMPOSITING MUST LOWER THE CONTRAST, or the model is not modelling.
    check("compositing lowers contrast on every variant",
          all(c < d for _v, d, c, _f, _a, _b in rows), True)

    # ⚑ AND THE CHECK MUST CURRENTLY FAIL, because the defect is REAL and unfixed.
    # A green result here today would mean the check is not measuring.
    check("the shipped palette FAILS this check", main(["x"]), 1)

    saved = globals()["measure"]
    try:
        # a hypothetical palette whose composited ghost clears its floor
        globals()["measure"] = lambda: [("SELFTEST-OK", 9.0, 4.0, 3.0, 29.0, 12.0)]
        check("a clearing palette passes", main(["x"]), 0)
        # and one whose composited ghost reads as TEXT — the other bound
        globals()["measure"] = lambda: [("SELFTEST-LOUD", 9.0, 8.0, 3.0, 29.0, 35.0)]
        check("a ghost over the readability ceiling is seen", main(["x"]), 1)
        globals()["measure"] = lambda: []
        check("an empty population REFUSES", main(["x"]), 2)
    finally:
        globals()["measure"] = saved

    print("check_ghost_composite selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
