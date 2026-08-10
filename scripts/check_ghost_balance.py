#!/usr/bin/env python3
"""check_ghost_balance.py — the ghost is SOLVED, and the solve beats the scan.

`cvd_gate.derive_ghost` walks 99 points along lit->ground and returns the best.
`ghost_solve.derive_ghost` solves the balance condition y = sqrt(ab) in closed
form. This measures the difference on the REAL palettes rather than asserting it.

    scripts/check_ghost_balance.py           # exit 0 iff the solve is >= the scan everywhere
    scripts/check_ghost_balance.py --compare # per-variant: scan vs solve, side by side
    scripts/check_ghost_balance.py --selftest

⚑ WHAT "BETTER" MEANS HERE, STATED.  The objective is max-min: maximise the WORSE
of the ghost's two sides. So the solve is better exactly when its worse side is
no worse than the scan's worse side, on every variant. That is a comparison of
two answers to ONE question, not a claim that one method is nicer.

⚑ THE SCAN'S REAL DEFECT IS NOT ITS ERROR, IT IS ITS SILENCE.  A 99-point grid
returns the best of 99 and says nothing about whether the true optimum lies
between two samples. Its answer can be close and cannot be shown wrong. The
solved form can be checked against the balance condition it claims to satisfy,
which is what `skew` reports — and that is the difference this gate exists to
keep.

⚑ THE WEAKNESS, STATED.  Solving for the LUMINANCE is exact; reaching it with an
8-bit sRGB triple on a discrete segment is not. So a small residual skew is
expected and is a quantisation fact, not a solver fault. The gate bounds it
rather than demanding 1.0, and prints the worst case so the bound is visible
rather than assumed.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cvd_gate as C                                               # noqa: E402
import ghost_solve as G                                            # noqa: E402

# The residual the 8-bit segment can leave after an exact luminance solve. A
# ghost whose two sides differ by more than this is not a quantisation artifact.
MAX_SKEW = 1.06


def pairs():
    """[(id, lit, ground)] for every shipped variant — the real inputs."""
    import make_schemes
    grid = getattr(make_schemes, "GRID", None) or {}
    out = []
    for value in (grid.values() if isinstance(grid, dict) else grid):
        for scheme in (value if isinstance(value, (list, tuple)) else (value,)):
            if isinstance(scheme, dict) and "view" in scheme:
                ground = tuple(int(x) for x in scheme["view"].split(","))
                lit = tuple(int(x) for x in scheme["fg"].split(","))
                out.append((scheme.get("id", "?"), lit, ground))
                break
    return out


def compare():
    """[(id, scan_worst, solve_worst, ideal, solve_skew)] over every variant."""
    rows = []
    for vid, lit, ground in pairs():
        scan = C.derive_ghost(lit, ground)
        solved = G.derive_ghost(lit, ground)
        s_lit, s_gnd, ideal, _ = G.balance_report(lit, ground, scan)
        v_lit, v_gnd, _, skew = G.balance_report(lit, ground, solved)
        rows.append((vid, min(s_lit, s_gnd), min(v_lit, v_gnd), ideal, skew))
    return rows


def main(argv):
    known = {"--compare", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_ghost_balance: unknown flag {a!r}", file=sys.stderr)
            return 2

    rows = compare()
    if not rows:
        print("check_ghost_balance: REFUSED — no variants; the grid is not built, "
              "not the ghost balanced", file=sys.stderr)
        return 2

    if "--compare" in argv:
        print(f"{'variant':18s} {'scan':>7s} {'solve':>7s} {'ideal':>7s} {'skew':>7s}")
        for vid, scan, solve, ideal, skew in rows:
            print(f"{vid:18s} {scan:7.3f} {solve:7.3f} {ideal:7.3f} {skew:7.4f}")
        return 0

    bad = []
    for vid, scan, solve, ideal, skew in rows:
        # the solve must not be WORSE than the scan on the shared objective
        if solve < scan - 1e-9:
            bad.append(f"{vid}: solved worst side {solve:.4f} < scanned {scan:.4f}")
        # and it must actually balance, to within what 8-bit quantisation allows
        if skew > MAX_SKEW:
            bad.append(f"{vid}: sides differ by {skew:.4f}x (> {MAX_SKEW}), so the "
                       f"ghost is not at the balance point")
    if bad:
        print(f"check_ghost_balance: REFUSED — {len(bad)} of {len(rows)} variant(s) "
              f"fail the balance condition:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    worst = max(r[4] for r in rows)
    gained = sum(1 for r in rows if r[2] > r[1] + 1e-9)
    print(f"check_ghost_balance: {len(rows)} of {len(rows)} variants balanced "
          f"(worst skew {worst:.4f} <= {MAX_SKEW}; the solve improves the worst "
          f"side on {gained})")
    return 0


def _selftest():
    """Prove the algebra, and prove the gate can fail.

    ⚑ THE CLOSED FORM IS CHECKED AGAINST ITS OWN DEFINITION, not against the scan.
    Checking a solve against the thing it replaces would only show they agree —
    including where both are wrong. y = sqrt(ab) is verified as the point where
    the two sides are EQUAL, which is what the optimum means."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("the real palettes balance", main(["x"]), 0)

    # 1. the balance point equalises the two sides, in LUMINANCE (exactly)
    lit, ground = (200, 240, 230), (12, 21, 23)
    a, b = G.offsets(lit, ground)
    y = G.balance_luminance(lit, ground)
    check("y = sqrt(ab) equalises a/y and y/b",
          abs((a / y) - (y / b)) < 1e-12, True)
    check("each side is sqrt(span)",
          abs((a / y) - G.balance_contrast(lit, ground)) < 1e-12, True)

    # 2. it is the MAXIMUM of the min, not merely a fixed point: perturbing y in
    #    either direction must make the worse side worse.
    worse = min(a / y, y / b)
    for k in (0.9, 1.1):
        w = min(a / (y * k), (y * k) / b)
        check(f"perturbing y by {k}x lowers the worse side", w < worse, True)

    # 3. the solve is symmetric under swapping lit and ground — the ghost sits
    #    between them regardless of which is brighter (off vs backlit polarity).
    check("balance is polarity-symmetric",
          abs(G.balance_luminance(lit, ground)
              - G.balance_luminance(ground, lit)) < 1e-12, True)

    # 4. the achieved luminance lands on the target to well under 8-bit resolution
    _t, achieved, target = G.solve_ghost_t(lit, ground)
    check("the root-find reaches the target", abs(achieved - target) < 1e-3, True)

    # 5. ⚑ THE GATE MUST FAIL ON AN UNBALANCED GHOST, or it certifies anything.
    #    A ghost at t=0.02 is nearly the lit colour: one side ~1.0, the other the
    #    whole span.
    off = C._lerp(lit, ground, 0.02)
    _sl, _sg, _id, skew = G.balance_report(lit, ground, off)
    check("a deliberately off-balance ghost skews past the bound",
          skew > MAX_SKEW, True)
    balanced = G.derive_ghost(lit, ground)
    _sl, _sg, _id, bskew = G.balance_report(lit, ground, balanced)
    check("...while the solved one does not", bskew <= MAX_SKEW, True)

    # 6. the solve is never worse than the scan on the shared max-min objective
    rows = compare()
    check("population is non-empty", len(rows) > 0, True)
    check("the solve never loses to the scan",
          [r[0] for r in rows if r[2] < r[1] - 1e-9], [])

    # 7. ⚑ THE CEILING IS A DIFFERENT OBJECTIVE AND ITS CONSTRAINT IS STRICT.
    #    It maximises |Lc| SUBJECT TO staying below a threshold, so the optimum is
    #    a supremum that must be approached and never touched. A solve that
    #    returned the boundary itself would emit a ghost that reads as text.
    ceil_bad = []
    for vid, lit, ground in pairs():
        scanned = C.derive_ghost_ceiling(lit, ground)
        solved = G.derive_ghost_ceiling(lit, ground)
        lc_scan = abs(C.apca_Lc(scanned, ground))
        lc_solve = abs(C.apca_Lc(solved, ground))
        if lc_solve >= C.GHOST_READABLE_LC:
            ceil_bad.append(f"{vid}: solved ghost Lc={lc_solve:.2f} REACHES the "
                            f"ceiling {C.GHOST_READABLE_LC}")
        if lc_solve < lc_scan - 1e-9:
            ceil_bad.append(f"{vid}: solved Lc={lc_solve:.3f} < scanned {lc_scan:.3f}")
    check("the ceiling solve stays strictly under and beats the scan", ceil_bad, [])

    # and it must REFUSE rather than invent when no point clears the ceiling
    t, lc = G.solve_ceiling_t((10, 10, 10), (12, 12, 12), 30.0)
    check("a span too small to fail readability returns t=0, not a guess",
          t == 0.0 and lc < 30.0, True)

    print("check_ghost_balance selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
