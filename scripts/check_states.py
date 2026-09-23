#!/usr/bin/env python3
"""check_states.py — the decoration STATES (focus ring, hover ring, selection field) are pairwise
distinguishable under the gate's metric, and each clears its ground.

⚑ THE RELATION THIS MEASURES (relations.md §4b, W10).  `focus`, `hover` and
`sel_bg` are all the accent's hue — one family, "selecting anything switches the
backlight on" — and differ only in luminance. Until 2026-09-21 the differences
were authored nudges (hover ±0.12, sel_bg ±0.08) whose only justification was
prose in make_palette. The relation is:

    q(state_i, state_j)  >=  1      for every pair, under cvd_gate._worst_normalized
    WCAG(state, ground)  >=  FLOOR  for every state (a ring must be findable on its ground)

and the nudge magnitudes are SOLVED as the smallest luminance steps that satisfy
it (make_palette.solve_state_steps), not chosen.

    scripts/check_states.py            # the verdict, as opa_gate states decides it
    scripts/check_states.py --json     # the measurement policy/states.rego decides
    scripts/check_states.py --map      # per variant: the three states, pairwise q, each vs ground
    scripts/check_states.py --selftest

WEAKNESS. q is the gate's CVD-normalised metric on flat swatches; a 2px ring
next to a filled field is judged by the same number as two fields would be.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = ("focus", "hover", "sel_bg")
GROUND_FLOOR = 3.0     # the selftest's reference only; policy/states.rego owns the floor (S2)


def _rgb(s):
    return tuple(int(x) for x in s.split(","))


def measure(t):
    """{pairs: {(a, b): q}, grounds: {state: ratio}} for one token dict."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import cvd_gate as C
    floors = C.reference_floors()
    ground = _rgb(t["view"])
    cols = {s: _rgb(t[s]) for s in STATES}
    pairs = {}
    for i, a in enumerate(STATES):
        for b in STATES[i + 1:]:
            pairs[(a, b)] = C._worst_normalized(cols[a], cols[b], floors)[0]
    grounds = {s: C.wcag_ratio(cols[s], ground) for s in STATES}
    return {"pairs": pairs, "grounds": grounds, "cols": cols}


def as_case(vid, m):
    """One variant's measurement as policy/states.rego reads it."""
    return {"id": vid,
            "pairs": [{"a": a, "b": b, "q": q} for (a, b), q in m["pairs"].items()],
            "grounds": [{"state": s, "ratio": r} for s, r in m["grounds"].items()]}


def main(argv):
    known = {"--map", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_states: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_schemes as MS
    rows = [(t["id"], measure(t)) for (t, _d) in MS.GRID.values()]
    if "--json" in argv:
        import json
        print(json.dumps({"cases": [as_case(v, m) for v, m in rows]}, indent=1))
        return 0
    if "--map" in argv:
        for vid, m in rows:
            print(vid)
            for s in STATES:
                print(f"  {s:7} #{'%02x%02x%02x' % m['cols'][s]}   vs ground {m['grounds'][s]:.2f}:1")
            for (a, b), q in m["pairs"].items():
                print(f"  {a}/{b}: q={q:.2f}")
        return 0
    import opa_gate
    return opa_gate.gate("states")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # ⚑ THE MEASUREMENT CAN SEE (W50) the two fixtures policy/states_test.rego
    # refuses: identical states measure q = 0; a dim ring measures ~1.07:1 on its
    # ground. That they are defects is the policy's ruling (S1, S2).
    same = {"view": "8,20,17", "focus": "75,250,215", "hover": "75,250,215", "sel_bg": "35,249,206"}
    chk("identical focus and hover measure q = 0", measure(same)["pairs"][("focus", "hover")], 0.0)
    dim = {"view": "8,20,17", "focus": "12,28,24", "hover": "75,250,215", "sel_bg": "35,249,206"}
    r = measure(dim)["grounds"]["focus"]
    print(f"       (dim ring measures {r:.2f}:1 on its ground)")
    chk("a ring invisible on its ground measures below 3:1", r < GROUND_FLOOR, True)
    print("check_states selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
