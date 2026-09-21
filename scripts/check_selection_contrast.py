#!/usr/bin/env python3
"""check_selection_contrast.py — selected text stays legible on the lit backlight.

THE THEME'S SIGNATURE INVERSION: selecting something switches the backlight on —
a bright teal background with DARK text, everywhere else being dark with glowing
text. That inversion is the one place a body-text token is the wrong choice, so
it is the one place worth measuring.

    scripts/check_selection_contrast.py           # exit 0 iff every scheme clears
    scripts/check_selection_contrast.py --report  # per-scheme contrast ratios

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

# WCAG AA for large text. See the note above before changing this number.
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
# ⚑ A PAIR NO COLOUR CAN SATISFY IS NAMED HERE, PINNED AT THE SOLVER'S HONEST
# BEST, so that a change in EITHER direction is seen: a regression fails the
# floor arm, an improvement fails the pin and must leave the table. EMPTY since
# W10's second half (2026-09-21): EL-Openglo-Lit's negative-on-selection sat at
# 2.94 (red's luminance ceiling over a field at L 0.13 — ⊕SOLVER-SEL-BACKLIT)
# until the state relation solved the selection field one step darker, which
# gave the red room: 3.33. The pin refused the commit until it was removed —
# as designed.
KNOWN_INFEASIBLE = {}


def selection_pairs(keys=FG_KEYS):
    """[(scheme, key, fg, bg, ratio)] for every emitted .colors file."""
    out = []
    for fn in sorted(os.listdir(ROOT)):
        if not fn.endswith(".colors"):
            continue
        cur, sect = None, {}
        for line in open(os.path.join(ROOT, fn), encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                cur = line
            elif "=" in line and cur == "[Colors:Selection]":
                k, v = line.split("=", 1)
                sect[k.strip()] = v.strip()
        bg = sect.get("BackgroundNormal")
        if not bg:
            continue
        bg_rgb = tuple(int(x) for x in bg.split(","))
        for key in keys:
            v = sect.get(key)
            if not v:
                continue
            fg_rgb = tuple(int(x) for x in v.split(","))
            out.append((fn[:-len(".colors")], key, fg_rgb, bg_rgb,
                        contrast(fg_rgb, bg_rgb)))
    return out


def main(argv):
    known = {"--report", "--semantic"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_selection_contrast: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--semantic" in argv:
        for scheme, key, fg, bg, r in selection_pairs(SEMANTIC_KEYS):
            flag = "  " if r >= FLOOR else "！"
            print(f"{flag}{scheme}\t{key}\t{fg} on {bg}\t{r:.2f}:1")
        return 0
    pairs = selection_pairs(FG_KEYS + GATED_SEMANTIC)
    if "--report" in argv:
        for scheme, key, fg, bg, r in pairs:
            flag = "  " if r >= FLOOR else "！"
            print(f"{flag}{scheme}\t{key}\t{fg} on {bg}\t{r:.2f}:1")
        return 0
    if not pairs:
        print("check_selection_contrast: REFUSED — no schemes found; the search is "
              "broken, not the theme legible", file=sys.stderr)
        return 2
    bad, pinned = [], []
    for s, k, f, b, r in pairs:
        if (s, k) in KNOWN_INFEASIBLE:
            if abs(r - KNOWN_INFEASIBLE[(s, k)]) > 0.05:
                pinned.append((s, k, f, b, r))
            continue
        if r < FLOOR:
            bad.append((s, k, f, b, r))
    if pinned:
        print(f"check_selection_contrast: REFUSED — {len(pinned)} KNOWN_INFEASIBLE pair(s) "
              f"moved from their pinned ratio (an improvement must leave the table; a "
              f"regression is a defect):", file=sys.stderr)
        for s, k, f, b, r in pinned:
            print(f"    {s} {k}: {r:.2f}:1 (pinned {KNOWN_INFEASIBLE[(s, k)]})", file=sys.stderr)
        return 1
    if bad:
        print(f"check_selection_contrast: REFUSED — {len(bad)} of {len(pairs)} "
              f"selection pair(s) fall below {FLOOR}:1:", file=sys.stderr)
        for s, k, f, b, r in bad:
            print(f"    {s} {k}: {f} on {b} = {r:.2f}:1", file=sys.stderr)
        return 1
    gated = [p for p in pairs if (p[0], p[1]) not in KNOWN_INFEASIBLE]
    worst = min(r for *_, r in gated)
    print(f"check_selection_contrast: {len(gated)} of {len(pairs)} selection pairs "
          f"clear {FLOOR}:1 (worst {worst:.2f}:1)"
          + (f"; {len(KNOWN_INFEASIBLE)} pinned as infeasible: "
             + ", ".join(f"{s} {k} {v}" for (s, k), v in KNOWN_INFEASIBLE.items())
             if KNOWN_INFEASIBLE else ""))
    return 0


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
    check("found selection pairs", len(selection_pairs()) > 0, True)
    check("the semantic keys are read too",
          len(selection_pairs(GATED_SEMANTIC)) == 3 * len(selection_pairs(("ForegroundNormal",))), True)
    # ⚑ THE PIN MUST HOLD BOTH WAYS: the recorded pair is at its pinned ratio,
    # and a pin that drifted would be seen by main() (exercised via the table).
    got = {(s, k): r for s, k, _f, _b, r in selection_pairs(GATED_SEMANTIC)}
    for (s, k), v in KNOWN_INFEASIBLE.items():
        check(f"pinned pair {s} {k} is still at {v}", abs(got.get((s, k), 0) - v) <= 0.05, True)
    saved = dict(KNOWN_INFEASIBLE)
    try:
        # ⚑ A PIN THAT DOES NOT MATCH THE TREE MUST REFUSE — planted on a real
        # pair at a ratio it does not have (synthetic: the value, not the pair)
        KNOWN_INFEASIBLE.clear()
        KNOWN_INFEASIBLE[("EL-Openglo-Lit", "ForegroundNegative")] = 9.99
        check("a pinned pair that moved is REFUSED", main(["x"]), 1)
        KNOWN_INFEASIBLE.clear()
        check("with no pins the real tree clears the floor", main(["x"]), 0)
    finally:
        KNOWN_INFEASIBLE.clear()
        KNOWN_INFEASIBLE.update(saved)
    print("check_selection_contrast selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
