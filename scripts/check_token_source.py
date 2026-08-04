#!/usr/bin/env python3
"""check_token_source.py — every emission target reads the ONE palette.

The design's core property: many emission targets (Plasma colours, terminal
scheme, window decoration, widget style, boot splash, wallpapers, browser
theme, …) all render the SAME palette, so they cannot drift apart.  That holds
only while each target SOURCES its colours from a shared authority instead of
spelling hexes of its own.

Two authorities are sanctioned, both discovered from the tree rather than
assumed:
  · make_preview.parse_scheme — parses a scheme file into tokens
  · make_schemes.GRID         — the solved palette grid

    scripts/check_token_source.py          # exit 0 iff every emitter sources tokens
    scripts/check_token_source.py --map    # emitter -> the authority it reads

⚑ THE WITNESS IS "SOURCES FROM", NOT "CONTAINS NO HEX".  A generator legitimately
mentions hexes — a fallback, a mask, a test vector, pure black.  Banning the
literal would force noisy exemptions and would still miss the real defect, which
is a target that computes its palette independently.  So this asks the structural
question (does it read an authority?) and lets literals be.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# An emitter is a generator that WRITES a themed artifact.  Discovered by name;
# the roster is checked against the tree so a new make_*.py cannot be ignored.
AUTHORITIES = ("make_preview", "make_schemes")

# Generators that legitimately do NOT read the palette, with the reason.
NON_EMITTER = {
    "make_palette.py":  "SOLVES the palette; it is upstream of every token consumer",
    "make_schemes.py":  "IS an authority (owns GRID and emits the scheme files)",
    "make_preview.py":  "IS an authority (owns parse_scheme)",
    "make_font.py":     "emits glyph outlines; carries no colour",
    "make_glyph_ink.py": "emits an ink field from font winding; carries no colour",
    "make_segment_display.py": "emits QML geometry; colour is bound by the caller",
    "make_deb.py":      "packages what the emitters produced; reads no token itself",
}


def emitters():
    """[(filename, [authorities it reads])] for each make_*.py that should read tokens."""
    out = []
    for fn in sorted(os.listdir(ROOT)):
        if not (fn.startswith("make_") and fn.endswith(".py")):
            continue
        if fn in NON_EMITTER:
            continue
        text = open(os.path.join(ROOT, fn), encoding="utf-8", errors="replace").read()
        reads = []
        for a in AUTHORITIES:
            # a direct import, or a transitive one via another emitter
            if re.search(r"\b(?:import\s+%s\b|from\s+%s\s+import)" % (a, a), text):
                reads.append(a)
        # a target may reach tokens through a sibling emitter (e.g. the marquee
        # reuses the live wallpaper's colors_for) — that is still sourcing.
        if not reads:
            for other in os.listdir(ROOT):
                if other.startswith("make_") and other.endswith(".py") and other != fn:
                    mod = other[:-3]
                    if re.search(r"\b(?:import\s+%s\b|from\s+%s\s+import)" % (mod, mod), text):
                        reads.append(f"via {mod}")
                        break
        out.append((fn, reads))
    return out


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_token_source: unknown flag {a!r}", file=sys.stderr)
            return 2
    em = emitters()
    if "--map" in argv:
        for fn, reads in em:
            print(f"{fn}\t{', '.join(reads) if reads else '(NONE)'}")
        return 0
    if not em:
        print("check_token_source: REFUSED — no emitters found; the search is broken, "
              "not the tree clean", file=sys.stderr)
        return 2
    orphan = [fn for fn, reads in em if not reads]
    if orphan:
        print(f"check_token_source: REFUSED — {len(orphan)} of {len(em)} emitter(s) "
              f"read no palette authority:", file=sys.stderr)
        for fn in orphan:
            print(f"    {fn}", file=sys.stderr)
        print(f"    (authorities: {', '.join(AUTHORITIES)}; a target that computes its",
              file=sys.stderr)
        print("     own colours can drift from every other target)", file=sys.stderr)
        return 1
    print(f"check_token_source: {len(em)} of {len(em)} emitters source from the palette")
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

    check("every exemption is documented", all(NON_EMITTER.values()), True)
    em = emitters()
    check("emitters() found some", len(em) > 0, True)
    # the exemptions must name files that actually exist, or they are stale
    missing = [f for f in NON_EMITTER if not os.path.exists(os.path.join(ROOT, f))]
    check(f"no stale exemption ({missing})", missing, [])
    print("check_token_source selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
