#!/usr/bin/env python3
"""variant_roster.py — THE answer to "which variants exist": the DECLARATION, never a listing.

⚑ WHY (W61 B2, 2026-09-23). Nine functions named `variants()` and three more readers
answered this one question from four different places: make_schemes.GRID (the solved
palette), schemes_artifact.variants() (a listdir of the colours snapshot), a
`git ls-files *.colors` (render_samples, and concepts.py through it), and typed tuples
(check_aperture, check_rehue, render_screens.VARIANTS via check_urgency_cues). A
listing cannot tell a clean tree from a deleted file — delete EL-Amber.colors and a
roster read off the listing goes from "6 of 6" to "5 of 5", exit 0 — and a stale or
stray `.colors` (an atomic_path temp, a renamed variant's leftover) is counted as a
variant. The declaration is what a stale or missing FILE cannot fool.

THE ROSTER IS make_schemes.GRID's ids: make_schemes emits exactly one `<id>.colors`
per GRID entry, so GRID is what the tree is SUPPOSED to hold. Everything else is
compared TO it:
  · drift(declared, who)      — an emitter's own typed VARIANTS, both ways (W65)
  · listing_drift(names, what) — a file listing (the snapshot, the tracked tree):
                                 a declared variant with no file, a file with no
                                 declaration. This is where "which files exist" is
                                 legitimately asked: to catch a MISSING file, never
                                 to BE the population.

    scripts/variant_roster.py             # the roster, one per line; n on stderr
    scripts/variant_roster.py --compare   # snapshot + tracked .colors vs the roster, n of m
    scripts/variant_roster.py --selftest  # a missing and a stray file are both SEEN

WEAKNESS, stated: importing make_schemes solves the palette (seconds from the warm
.palette-cache.json, ~108 s CPU cold). A reader that wants only the NAMES pays that.
And GRID is itself read by path (.palette-cache.json), not content-addressed: this
fixes WHICH question is asked, not W75's snapshot of GRID.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def ids():
    """Sorted variant ids the palette DECLARES (make_schemes.GRID)."""
    import make_schemes
    return sorted(t["id"] for (t, _dark) in make_schemes.GRID.values())


def ordered():
    """The same roster in GRID's DECLARED order (hue, then off before lit) — for a
    reader that DISPLAYS the variants (a README column, a gallery section). ⚑ The
    order is declared by GRID's insertion order, not by any emitter's VARIANTS
    (which are compared to the roster as a set): measured 2026-09-23, every
    emitter's VARIANTS happened to equal this order, so moving a display onto it
    changes no output — but if an emitter reorders, the display does not follow."""
    import make_schemes
    return [t["id"] for (t, _dark) in make_schemes.GRID.values()]


def drift_facts(declared_by, roster=None):
    """[{variant, who, why}] — drift() over {who: declared VARIANTS}, as JSON facts a
    policy can deny on (each check's `roster_drift`)."""
    return [{"variant": v, "who": who, "why": why}
            for who, declared in declared_by.items()
            for v, why in drift(declared, who, roster)]


def drift(declared, who, roster=None):
    """[(variant, why)] — a typed roster `declared` (named `who`) against the roster, BOTH ways."""
    want, mine = set(ids() if roster is None else roster), set(declared)
    return ([(v, f"{who}.VARIANTS does not declare it (GRID does)") for v in sorted(want - mine)]
            + [(v, f"{who}.VARIANTS declares it but GRID does not") for v in sorted(mine - want)])


def listing_drift(names, what, roster=None):
    """[(variant, why)] — a LISTING of files (variant names) compared to the roster.
    A declared variant with no file is missing; a file with no declaration is a stray."""
    want, have = set(ids() if roster is None else roster), set(names)
    return ([(v, f"declared by GRID but absent from {what}") for v in sorted(want - have)]
            + [(v, f"present in {what} but GRID does not declare it") for v in sorted(have - want)])


def listings():
    """{what: [variant names]} — the two listings of the `.colors` roster this tree keeps."""
    import git_tracked
    import schemes_artifact
    suffix = schemes_artifact.SUFFIX
    return {
        "the schemes snapshot": sorted(schemes_artifact.variants()),
        "the tracked tree": sorted(f[:-len(suffix)] for f in
                                   git_tracked.files(":(glob)*" + suffix, root=ROOT)),
    }


def _selftest():
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and bool(cond)

    roster = ("A", "B", "C")
    see("a listing equal to the roster has no drift", listing_drift(["A", "B", "C"], "x", roster) == [])
    got = listing_drift(["A", "C", "Z"], "x", roster)
    see(f"a MISSING file is seen ({got})", ("B", "declared by GRID but absent from x") in got)
    see("a STRAY file is seen", ("Z", "present in x but GRID does not declare it") in got)
    see("an emitter roster that drops one is seen", [v for v, _ in drift(["A", "B"], "m", roster)] == ["C"])
    facts = drift_facts({"m": ["A", "B"], "n": ["A", "B", "C"]}, roster)
    see(f"drift_facts names the emitter that dropped one ({facts})",
        [(f["who"], f["variant"]) for f in facts] == [("m", "C")])
    live = ids()
    see(f"the live roster is non-empty ({len(live)})", len(live) > 0)
    see("ordered() is the same set as ids()", sorted(ordered()) == live)
    print("variant_roster selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    known = {"--selftest", "--compare"}
    for a in argv[1:]:
        if a not in known:
            print(f"variant_roster: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return _selftest()
    roster = ids()
    if not roster:
        print("variant_roster: REFUSED — GRID declares no variant; the palette did not load",
              file=sys.stderr)
        return 2
    if "--compare" in argv:
        bad = 0
        for what, names in listings().items():
            d = listing_drift(names, what, roster)
            bad += len(d)
            present = len(set(roster) & set(names))
            print(f"variant_roster: {present} of {len(roster)} declared variant(s) present in "
                  f"{what}; {len(d)} drift")
            for v, why in d:
                print(f"    {v}: {why}", file=sys.stderr)
        return 1 if bad else 0
    for v in roster:
        print(v)
    print(f"variant_roster: {len(roster)} variant(s) declared by make_schemes.GRID", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
