#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_solver_roots.py — the solver's candidates cover every root of its contrast floor (W220).

    scripts/check_solver_roots.py            # the verdict, as opa_gate solver_roots decides it
    scripts/check_solver_roots.py --json     # the measurement policy/solver_roots.rego decides
    scripts/check_solver_roots.py --selftest # the measurement can see a one-sided candidate set

⚑ |contrast| >= X HAS TWO ROOTS (operator, 2026-10-02: "when you take the absolute
value of something ... there are two input values that solve"): text lighter than
the field and text darker than it. make_palette._candidates guessed ONE by
`L(ground) < 0.4`, and its saturations started at 0.5, so a sector's pale tints
were never offered. This measures, per (variant, field, slot) and per SIDE, the
best contrast REACHABLE anywhere in the slot's sector (a dense sweep of hue,
saturation and value) against the best the solver's own candidate set offers on
that side. The policy denies a side that can reach the floor but that the
candidates do not cover: the solver then reports infeasible a pair that is not.

The fields are the two grounds the solver places semantic sets on: the view
ground (neg/neu/pos/link/visited) and the selection field (neg/neu/pos), with
the solver's own floor (make_palette's 4.6, WCAG) and its own `hot` (the accent).

⚑ WEAKNESS: "reachable" is a sweep, not a proof - a root narrower than the sweep
step could be missed, which would UNDER-report a gap, never invent one. The
hot-separation prune is not applied to the sweep, so a reachable side may still
be unusable against the accent; the measurement records the candidate count per
side so that case reads as "covered by nothing" rather than silently passing.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

FLOOR = 4.6                       # make_palette.solve_scheme's _min_c
SWEEP_H = 2                       # degrees
SWEEP_S = [i / 10 for i in range(1, 11)]
SWEEP_V = [i / 50 for i in range(1, 51)]


def side_of(c, bg, C):
    return "lighter" if C._wcag_L(c) > C._wcag_L(bg) else "darker"


def sector_hues(sector):
    lo, hi = sector
    span = (hi - lo) % 360
    return [(lo + 1 + k) % 360 for k in range(0, max(1, span - 1), SWEEP_H)]


def measure_slot(sector, bg, hot, mp, C):
    """{side: {reachable, candidate, n_candidates}} for one slot on one field."""
    out = {s: {"reachable": 0.0, "candidate": None, "n_candidates": 0,
               "n_unpruned": 0, "reachable_sat_min": None}
           for s in ("lighter", "darker")}
    for h in sector_hues(sector):
        for s in SWEEP_S:
            for v in SWEEP_V:
                c = mp._hsv(h, s, v)
                side = out[side_of(c, bg, C)]
                r = C.wcag_ratio(c, bg)
                side["reachable"] = max(side["reachable"], r)
                if r >= FLOOR and (side["reachable_sat_min"] is None or s > side["reachable_sat_min"]):
                    side["reachable_sat_min"] = s     # the most saturated colour that still clears
    # candidates WITHOUT the hot prune: tells a grid gap from a separation prune
    for c in mp._candidates(sector, bg, FLOOR, None):
        out[side_of(c, bg, C)]["n_unpruned"] += 1
    for c in mp._candidates(sector, bg, FLOOR, hot):
        side = out[side_of(c, bg, C)]
        r = C.wcag_ratio(c, bg)
        side["candidate"] = r if side["candidate"] is None else max(side["candidate"], r)
        side["n_candidates"] += 1
    return out


def measure():
    import cvd_gate as C
    import make_palette as mp
    grid = mp.build_grid()
    cases = []
    for (t, _d) in grid.values():
        vid = t["id"]
        hot = C.rgb(t["focus"])
        fields = (("view", C.rgb(t["view"]), ("neg", "neu", "pos", "link", "visited")),
                  ("selection", C.rgb(t["sel_bg"]), ("neg", "neu", "pos")))
        for field, bg, slots in fields:
            for slot in slots:
                sides = measure_slot(mp._sect(slot, vid), bg, hot, mp, C)
                for side, m in sides.items():
                    cases.append({"id": f"{vid}/{field}/{slot}/{side}", "variant": vid,
                                  "field": field, "slot": slot, "side": side, **m})
    return {"floor": FLOOR, "cases": cases}


def _selftest():
    import cvd_gate as C
    import make_palette as mp
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    grey = (128, 128, 128)
    check("white is lighter than mid grey", side_of((255, 255, 255), grey, C), "lighter")
    check("black is darker than mid grey", side_of((0, 0, 0), grey, C), "darker")
    m = measure_slot((340, 20), grey, None, mp, C)
    check("on mid grey, red reaches some contrast on both sides",
          (m["lighter"]["reachable"] > 1.0, m["darker"]["reachable"] > 1.0), (True, True))
    saved = mp._candidates
    try:
        mp._candidates = lambda sector, ground, mc, hot: [(255, 200, 200)]
        m = measure_slot((340, 20), grey, None, mp, C)
        check("a one-sided candidate set is SEEN as covering one side only",
              (m["lighter"]["n_candidates"], m["darker"]["n_candidates"], m["darker"]["candidate"]),
              (1, 0, None))
    finally:
        mp._candidates = saved
    print("check_solver_roots selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest"}:
            print(f"check_solver_roots: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("solver_roots")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
