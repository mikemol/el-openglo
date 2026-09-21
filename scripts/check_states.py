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

    scripts/check_states.py            # exit 0 iff the relation holds on every variant
    scripts/check_states.py --map      # per variant: the three states, pairwise q, each vs ground
    scripts/check_states.py --selftest

WEAKNESS. q is the gate's CVD-normalised metric on flat swatches; a 2px ring
next to a filled field is judged by the same number as two fields would be.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATES = ("focus", "hover", "sel_bg")
GROUND_FLOOR = 3.0     # AA-large: a ring or field must be findable on its ground


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


def verdict(m):
    bad = [f"{a}/{b} q={q:.2f}" for (a, b), q in m["pairs"].items() if q < 1.0]
    bad += [f"{s} on ground {r:.2f} < {GROUND_FLOOR}" for s, r in m["grounds"].items() if r < GROUND_FLOOR]
    return bad


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_states: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_schemes as MS
    rows = [(t["id"], measure(t)) for (t, _d) in MS.GRID.values()]
    if not rows:
        print("check_states: REFUSED — no variants", file=sys.stderr)
        return 2
    if "--map" in argv:
        for vid, m in rows:
            print(vid)
            for s in STATES:
                print(f"  {s:7} #{'%02x%02x%02x' % m['cols'][s]}   vs ground {m['grounds'][s]:.2f}:1")
            for (a, b), q in m["pairs"].items():
                print(f"  {a}/{b}: q={q:.2f}")
        return 0
    bad = [f"{vid}: {'; '.join(b)}" for vid, m in rows if (b := verdict(m))]
    if bad:
        print(f"check_states: REFUSED — {len(bad)} of {len(rows)} variant(s) break the state relation:",
              file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    worst = min(q for _v, m in rows for q in m["pairs"].values())
    print(f"check_states: {len(rows)} of {len(rows)} variants — focus/hover/selection pairwise "
          f"distinct (worst q {worst:.2f}) and each >= {GROUND_FLOOR}:1 on its ground")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # ⚑ THE RELATION MUST BE ABLE TO FAIL: identical states are q = 0
    same = {"view": "8,20,17", "focus": "75,250,215", "hover": "75,250,215", "sel_bg": "35,249,206"}
    chk("identical focus and hover are seen", "focus/hover" in "; ".join(verdict(measure(same))), True)
    dim = {"view": "8,20,17", "focus": "12,28,24", "hover": "75,250,215", "sel_bg": "35,249,206"}
    chk("a ring invisible on its ground is seen", "focus on ground" in "; ".join(verdict(measure(dim))), True)
    print("check_states selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
