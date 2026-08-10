#!/usr/bin/env python3
"""check_separation.py — the declared separation pairs are actually GATED.

⚑ THIS CHECK EXISTS BECAUSE ITS SUBJECT HAD NO CALLER.  `cvd_gate.audit_variant` is the
only consumer of the ENFORCED/SURFACED pair lists, and nothing in the tree invoked it —
not a script, not a __main__ block, not another module.  Eight separation pairs were
DECLARED and never checked, which is worse than not declaring them: a reader sees a pair
list and concludes the pairs are gated.

    scripts/check_separation.py            # exit 0 iff every ENFORCED pair clears its floor
    scripts/check_separation.py --surfaced # also report the SURFACED pairs (never gating)
    scripts/check_separation.py --selftest # prove the walk can SEE a violation

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


def audit(quiet=True):
    """[(variant_id, violation)] over every variant, via cvd_gate's own walker.

    Calls `audit_variant` — the point of this file is that this call exists."""
    floor = C.reference_floor()[0]
    out = []
    for vid, t in variants():
        if quiet:
            import io
            import contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                viol = C.audit_variant(t, floor)
        else:
            viol = C.audit_variant(t, floor)
        for v in viol:
            out.append((vid, v))
    return out


def main(argv):
    known = {"--surfaced", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_separation: unknown flag {a!r}", file=sys.stderr)
            return 2

    vs = variants()
    n_enf = len(C.ENFORCED)
    # ⚑ AN EMPTY POPULATION IS A BROKEN SEARCH.  Zero variants or zero declared pairs
    # would make every loop below vacuous and print a pass; that is the failure mode the
    # house rule names, and it is not hypothetical — check_palette_graph shipped with it.
    if not vs or not n_enf:
        print(f"check_separation: REFUSED — an empty population ({len(vs)} variants, "
              f"{n_enf} enforced pairs); the search is broken, not the palette clean",
              file=sys.stderr)
        return 2

    if "--surfaced" in argv:
        floor = C.reference_floor()[0]
        for _vid, t in vs:
            C.audit_variant(t, floor)
        return 0

    bad = audit()
    total = len(vs) * n_enf
    if bad:
        print(f"check_separation: REFUSED — {len(bad)} of {total} enforced pair(s) "
              f"fall below the CVD separation floor:", file=sys.stderr)
        for vid, v in bad:
            print(f"    {vid}: {v}", file=sys.stderr)
        return 1
    print(f"check_separation: {total} of {total} enforced pairs clear the CVD floor "
          f"({len(vs)} variants x {n_enf} pairs, {len(C.SURFACED)} surfaced pairs reported)")
    return 0


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
    check("the real palette passes", main(["x"]), 0)
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
