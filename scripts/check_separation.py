#!/usr/bin/env python3
"""check_separation.py — the declared separation pairs are actually GATED.

⚑ THIS CHECK EXISTS BECAUSE ITS SUBJECT HAD NO CALLER.  `cvd_gate.audit_variant` is the
only consumer of the ENFORCED/SURFACED pair lists, and nothing in the tree invoked it —
not a script, not a __main__ block, not another module.  Eight separation pairs were
DECLARED and never checked, which is worse than not declaring them: a reader sees a pair
list and concludes the pairs are gated.

    scripts/check_separation.py            # the verdict, as opa_gate separation decides it
    scripts/check_separation.py --json     # the measurement policy/separation.rego decides
    scripts/check_separation.py --surfaced # also report the SURFACED pairs (never gating)
    scripts/check_separation.py --selftest # prove the walk can SEE a violation

⚑ THE FLOOR IS THE POLICY'S (W50).  This file measures, per variant and ENFORCED
pair, the worst-view CAM02-UCS distance (cvd_gate.worst_view_dE — the metric
audit_variant walks) and the reference floor; the 0.8 factor that turns the
floor into a requirement, and the verdict, live in policy/separation.rego.
audit_variant is still called — by --surfaced and by the selftest's fixtures.

⚑ WHY ENFORCED GATES AND SURFACED DOES NOT.  The class is a real distinction: where colour
is the SOLE carrier of a meaning, a CVD viewer who cannot separate two colours loses the
message, so the pair is enforced.  Where geometry co-carries it (an accent underlines, a
focus ring surrounds), colour is redundant and the pair is reported for attention rather
than gated.  That is a claim about the DESIGN, not about the arithmetic — which is exactly
why it must be recorded per-edge and not inferred from a floor.

⚑ THE WEAKNESS, STATED.  This gates the pairs the authority declares.  It cannot tell you
that the RIGHT pairs are declared — 11 of the 15 constellation pairs are optimised by
`solve_semantic_set` and gated by nobody, and `check_palette_graph.py --edges` is where
that shows up.  A green run here means "every declared pair clears", never "every pair
that matters clears".
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import cvd_gate as C                                              # noqa: E402
import palette_graph as PG                                        # noqa: E402


def variants():
    """[(id, token-dict)] for every solved variant — the same GRID the emitters ship."""
    import make_schemes
    grid = getattr(make_schemes, "GRID", None) or {}
    out = []
    for value in (grid.values() if isinstance(grid, dict) else grid):
        for scheme in (value if isinstance(value, (list, tuple)) else (value,)):
            if isinstance(scheme, dict) and "id" in scheme:
                out.append((scheme["id"], scheme))
                break                      # the 2nd element is the dark COUNTERPART
    return out


def measure(vs=None, enforced=None):
    """The MEASUREMENT policy/separation.rego decides: the variants, the ENFORCED
    pair names, the reference floor (dE), and one case per (variant, pair) — its
    worst-view dE and the view that collapses it, or `dE: null` with the reason
    it could not be read (a token the variant does not carry).

    ⚑ AN EMPTY POPULATION IS A BROKEN SEARCH.  Zero variants or zero declared pairs
    make every case list vacuous; that is the failure mode the house rule names,
    and it is not hypothetical — check_palette_graph shipped with it. The policy's
    D0 denies it; this file only reports the lists it walked."""
    vs = variants() if vs is None else vs
    enforced = tuple(C.ENFORCED) if enforced is None else tuple(enforced)
    cases = []
    for vid, t in vs:
        for name, a, b in enforced:
            case = {"id": f"{vid}/{name}", "variant": vid, "pair": name, "a": a, "b": b}
            try:
                d, view = C.worst_view_dE(C.rgb(t[a]), C.rgb(t[b]))
                case.update(dE=round(d, 4), view=view, why=None)
            except KeyError as e:
                case.update(dE=None, view=None, why=f"the variant carries no token {e}")
            cases.append(case)
    return {"variants": [v for v, _t in vs], "enforced": [n for n, _a, _b in enforced],
            "surfaced": [n for n, _a, _b in C.SURFACED],
            "floor": round(C.reference_floor()[0], 4), "cases": cases}


def main(argv):
    known = {"--surfaced", "--selftest", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_separation: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--surfaced" in argv:
        floor = C.reference_floor()[0]
        for _vid, t in variants():
            C.audit_variant(t, floor)
        return 0
    import opa_gate
    return opa_gate.gate("separation")


def _selftest():
    """Prove the walk can SEE a violation.

    ⚑ A GATE THAT HAS NEVER REPORTED A FAILURE IS NOT KNOWN TO BE ABLE TO.  That is
    precisely how `audit_variant` sat uncalled without anyone noticing — an all-clear and
    a never-run are the same silence.  So this feeds it a variant engineered to fail and
    asserts it says so, and feeds it one engineered to pass and asserts it does not."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    floor = C.reference_floor()[0]
    m = measure()
    check("the real palette is measured, every pair read",
          (len(m["cases"]) == len(m["variants"]) * len(m["enforced"]) > 0,
           [c["id"] for c in m["cases"] if c["dE"] is None]), (True, []))
    check("the authority declares enforced pairs", len(C.ENFORCED) > 0, True)
    check("the authority declares surfaced pairs", len(C.SURFACED) > 0, True)

    # ⚑ THE PAIRS COME FROM THE AUTHORITY.  If palette_graph and cvd_gate disagreed, this
    # would be gating a different set than the one declared — check_palette_graph gates
    # that they agree, and this asserts the wiring is live rather than a coincidence.
    check("ENFORCED is the authority's projection",
          set(C.ENFORCED), set(PG.gate_pairs("enforced")))

    import io
    import contextlib

    # a variant where every enforced pair is the SAME colour: maximal violation.
    # ⚑ THE FIXTURE MUST COVER SURFACED TOO.  `audit_variant` walks BOTH lists, so a
    # fixture built from the enforced keys alone raises KeyError on `focus` — the selftest
    # failing on its own fixture rather than on the subject.
    keys = {k for _, a, b in tuple(C.ENFORCED) + tuple(C.SURFACED) for k in (a, b)}
    broken = {"id": "SELFTEST-BAD"}
    for k in keys:
        broken[k] = "128,128,128"
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        viol = C.audit_variant(broken, floor)
    check("sees identical colours as violations", len(viol), len(C.ENFORCED))
    # ...and the MEASUREMENT sees them too: every pair at dE 0. That dE 0 is
    # DENIED is policy/separation_test.rego's ruling.
    check("the measurement reads identical colours as dE 0",
          {c["dE"] for c in measure(vs=[("SELFTEST-BAD", broken)])["cases"]}, {0.0})
    check("a variant missing a token is measured as unreadable, not skipped",
          [c["why"] is not None for c in measure(vs=[("SELFTEST-EMPTY", {"id": "x"})])["cases"]],
          [True] * len(C.ENFORCED))

    # and a variant built from the Okabe-Ito reference itself: must NOT violate
    names = list(C.OKABE_ITO)
    good = {"id": "SELFTEST-OK"}
    for i, k in enumerate(sorted(keys)):
        good[k] = ",".join(str(x) for x in C.OKABE_ITO[names[i % len(names)]])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        viol_ok = C.audit_variant(good, floor)
    check("a spread palette is not flagged wholesale", len(viol_ok) < len(C.ENFORCED), True)

    # ⟡PARAMETRIC: the pair list is an argument, so a hypothetical edge set can be audited
    # without mutating module state.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        viol_p = C.audit_variant(broken, floor,
                                 enforced=[("probe", "neg", "pos")], surfaced=[])
    check("the pair list is parametric", len(viol_p), 1)

    print("check_separation selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
