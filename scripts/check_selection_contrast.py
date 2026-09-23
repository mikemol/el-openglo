#!/usr/bin/env python3
"""check_selection_contrast.py — selected text stays legible on the lit backlight.

THE THEME'S SIGNATURE INVERSION: selecting something switches the backlight on —
a bright teal background with DARK text, everywhere else being dark with glowing
text. That inversion is the one place a body-text token is the wrong choice, so
it is the one place worth measuring.

    scripts/check_selection_contrast.py           # the verdict, as opa_gate selection_contrast decides it
    scripts/check_selection_contrast.py --json    # the measurement policy/selection_contrast.rego decides
    scripts/check_selection_contrast.py --report  # per-scheme contrast ratios
    scripts/check_selection_contrast.py --semantic  # the semantic set on the selection field

⚑ THIS MEASURES, IT DOES NOT PREFER.  It asserts a legibility FLOOR (WCAG 2.x
contrast, the same ratio a UI toolkit is judged by), not a particular colour. A
value that clears the floor passes whatever its hue, so the check survives a
palette re-solve — which is the whole point of a generated theme.

⚑ OPEN QUESTION IT EXISTS TO TRACK.  Repairing make_schemes.py changed
Selection/ForegroundActive from a dark value to hot-glow, and rendered against
the lit background the bright value has visibly lower contrast than the
ForegroundNormal beside it. The floor below is deliberately set to the WCAG AA
large-text threshold: it catches an outright unreadable pairing today without
pre-judging the design question of which token belongs there. Raise it to 4.5
(AA body text) when that question is decided.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚑ THE REPO'S PREVAILING CONVENTION, NOT A NEW MECHANISM — and it is on W62's
# list to retire. check_css, check_monet, check_windows and ~25 others carry this
# exact line. A first draft here put it inside schemes() behind a conditional,
# which would have left W62 two patterns to migrate instead of one; conforming to
# the existing shape is what makes the sweep mechanical. The operator's ruling
# ("build a package out of it") is that sweep, not a per-file workaround.
sys.path.insert(0, ROOT)

# WCAG AA for large text. See the note above before changing this number.
# ⚑ THE GATE'S FLOOR IS policy/selection_contrast.rego's `floor` (W50). This copy
# exists because check_gtk imports it and the report modes flag by it; --selftest
# REFUSES if the two disagree, so it cannot drift silently.
FLOOR = 3.0

# The keys that render TEXT on the selection background.
FG_KEYS = ("ForegroundNormal", "ForegroundActive")


def _rel_luminance(rgb):
    """WCAG relative luminance."""
    out = []
    for c in rgb:
        s = c / 255.0
        out.append(s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4)
    r, g, b = out
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG contrast ratio between two RGB triples."""
    la, lb = _rel_luminance(a), _rel_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# The semantic foregrounds drawn on the selection field. ⚑ AUTHORED LITERALS
# until W10 (2026-09-21): make_palette emitted "45,10,10" / "45,30,8" /
# "10,40,20" for every variant, and this check never asked about them.
SEMANTIC_KEYS = ("ForegroundNegative", "ForegroundNeutral", "ForegroundPositive",
                 "ForegroundLink", "ForegroundVisited", "ForegroundInactive")
# The three semantic keys are GATED (below), like the text keys. Link/Visited/
# Inactive are reported by --semantic and not gated: Inactive is the ghost
# relation on this pair (subordinate by design) and Link/Visited have no
# relation yet — recorded in relations.md §4a, not smuggled under a floor.
GATED_SEMANTIC = ("ForegroundNegative", "ForegroundNeutral", "ForegroundPositive")
# A pair no colour can satisfy is PINNED at the solver's honest best — that table
# is policy/selection_contrast.rego's `pinned` since W50 (empty since W10).


def schemes():
    """The scheme ids this tree DECLARES, from the palette authority.

    ⚑ THE ROSTER IS DECLARED, NOT DISCOVERED (W65, 2026-09-22). This function
    used to be `os.listdir(ROOT)` filtered to `.colors` — one of the 42 undeclared
    domains build_graph measures — and a discovered population cannot tell a clean
    tree from a deleted one. make_schemes emits exactly one .colors per GRID
    entry, so GRID is the authority: add a variant and the expected count moves by
    itself; delete an emitted file and this REFUSES instead of quietly measuring
    less.

    ⚑ DELEGATES TO scripts/variant_roster.py (W61 B2): one roster, one reader."""
    import variant_roster
    return variant_roster.ids()


def roster_drift(declared, who):
    """[(variant, why)] — an emitter's own variant list against schemes(), BOTH ways.

    ⚑ W65 SWEEP (check_gtk, check_firefox, check_windows). Each emitter types its
    own VARIANTS list and each check used to iterate THAT, so dropping a variant
    from the emitter dropped it from the check too: 36 of 36 became 30 of 30,
    rc 0. The palette authority is the roster; an emitter that disagrees with it
    is a missing member, returned with its reason, never a smaller n.
    Delegates to variant_roster.drift (W61 B2)."""
    import variant_roster
    return variant_roster.drift(declared, who)


def selection_pairs(keys=FG_KEYS):
    """([(scheme, key, fg, bg, ratio)], [missing]) over the DECLARED roster.

    ⚑ EVERY `continue` HERE USED TO SHRINK THE POPULATION SILENTLY, and that is
    the defect W65 names. Measured 2026-09-22 by check_discriminates: renaming the
    [Colors:Selection] header in one scheme took the report from "30 of 30
    selection pairs clear 3.0:1" to "25 of 25" — EXIT 0 BOTH TIMES. The corruption
    did not falsify the predicate, it removed five members from the population,
    and n of n is green for every n. Corrupt every scheme and you arrive at 0 of
    0: green. So a skipped pair is now RETURNED as missing, never dropped."""
    out, missing = [], []
    for scheme in schemes():
        path = os.path.join(ROOT, f"{scheme}.colors")
        if not os.path.isfile(path):
            missing.extend((scheme, k, "the .colors file is absent") for k in keys)
            continue
        cur, sect = None, {}
        for line in open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                cur = line
            elif "=" in line and cur == "[Colors:Selection]":
                k, v = line.split("=", 1)
                sect[k.strip()] = v.strip()
        bg = sect.get("BackgroundNormal")
        if not bg:
            missing.extend((scheme, k, "[Colors:Selection] BackgroundNormal is absent")
                           for k in keys)
            continue
        bg_rgb = tuple(int(x) for x in bg.split(","))
        for key in keys:
            v = sect.get(key)
            if not v:
                missing.append((scheme, key, f"[Colors:Selection] {key} is absent"))
                continue
            fg_rgb = tuple(int(x) for x in v.split(","))
            out.append((scheme, key, fg_rgb, bg_rgb, contrast(fg_rgb, bg_rgb)))
    return out, missing


def measure(keys=FG_KEYS + GATED_SEMANTIC):
    """The MEASUREMENT policy/selection_contrast.rego decides (W50): the declared
    roster, the gated keys, and one case per (scheme, key) — its WCAG ratio, or
    `ratio: null` with the reason it could not be read. The floor, the pins and
    "a shrinking population is not a passing one" are the policy's, not here."""
    pairs, missing = selection_pairs(keys)
    cases = [{"id": f"{s}/{k}", "scheme": s, "key": k, "fg": list(f), "bg": list(b),
              "ratio": r, "why": None} for s, k, f, b, r in pairs]
    cases += [{"id": f"{s}/{k}", "scheme": s, "key": k, "fg": None, "bg": None,
               "ratio": None, "why": why} for s, k, why in missing]
    return {"roster": list(schemes()), "keys": list(keys), "cases": cases}


def _report(keys):
    for c in measure(keys)["cases"]:
        if c["ratio"] is None:
            print(f"！{c['scheme']}\t{c['key']}\tMISSING — {c['why']}")
            continue
        flag = "  " if c["ratio"] >= FLOOR else "！"
        print(f"{flag}{c['scheme']}\t{c['key']}\t{tuple(c['fg'])} on {tuple(c['bg'])}\t{c['ratio']:.2f}:1")
    return 0


def main(argv):
    known = {"--report", "--semantic", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_selection_contrast: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--semantic" in argv:
        return _report(SEMANTIC_KEYS)
    if "--report" in argv:
        return _report(FG_KEYS + GATED_SEMANTIC)
    import opa_gate
    return opa_gate.gate("selection_contrast")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # Anchor the maths against the two ratios WCAG itself fixes.
    check("black on white is 21:1", round(contrast((0, 0, 0), (255, 255, 255)), 1), 21.0)
    check("a colour against itself is 1:1",
          round(contrast((0, 205, 176), (0, 205, 176)), 2), 1.0)
    check("the measure is symmetric",
          round(contrast((0, 0, 0), (255, 255, 255)), 4),
          round(contrast((255, 255, 255), (0, 0, 0)), 4))
    check("found selection pairs", len(selection_pairs()[0]) > 0, True)
    check("the semantic keys are read too",
          len(selection_pairs(GATED_SEMANTIC)[0]) == 3 * len(selection_pairs(("ForegroundNormal",))[0]), True)
    # ⚑ THE POPULATION IS COMPLETE ON A CLEAN TREE, AND SAYS SO. Without this the
    # expected-count assertion in main() could only ever be observed failing; a
    # rule whose satisfied case is never asserted cannot retire, and "the tree is
    # whole" and "the reader stopped looking" would render the same. This is
    # linux-sources-9c's liveness conjunct at the third site today.
    pairs, missing = selection_pairs(FG_KEYS + GATED_SEMANTIC)
    check("the declared population is complete on a clean tree",
          (len(missing), len(pairs) == len(schemes()) * len(FG_KEYS + GATED_SEMANTIC)),
          (0, True))
    check("and it is not vacuously complete", len(pairs) > 0, True)
    # ⚑ THE MEASUREMENT MUST SEE A MISSING MEMBER as a case with a reason, never
    # a smaller population (W65) — that it is a DENY is policy/selection_contrast
    # _test.rego's ruling, as are the floor and a pin that moved.
    saved = globals()["schemes"]
    try:
        globals()["schemes"] = lambda: list(saved()) + ["EL-NoSuch"]
        m = measure()
        gone = [c for c in m["cases"] if c["scheme"] == "EL-NoSuch"]
        check("an absent scheme is measured as missing cases, one per key",
              (len(gone), all(c["ratio"] is None and c["why"] for c in gone)),
              (len(m["keys"]), True))
    finally:
        globals()["schemes"] = saved
    import opa_gate
    if opa_gate.OPA:
        check("FLOOR (imported by check_gtk) is the policy's floor",
              opa_gate.value("selection_contrast", measure())["floor"], FLOOR)
    else:
        print("  SKIP FLOOR vs policy — opa absent")
    print("check_selection_contrast selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
