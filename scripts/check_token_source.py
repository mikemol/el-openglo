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

    scripts/check_token_source.py          # the verdict, as opa_gate token_source decides it
    scripts/check_token_source.py --json   # the measurement policy/token_source.rego decides
    scripts/check_token_source.py --map    # emitter -> the authority it reads

WEAKNESS. "Reads an authority" is an import found by regex in the source text:
an import that is never USED still counts, and the `via` sibling is not itself
checked to read the palette on the path the emitter takes.

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
# the repo's prevailing convention for reaching the tree's modules; W62 retires
# every instance at once by making them a package, not one at a time by hand
sys.path.insert(0, ROOT)

# An emitter is a generator that WRITES a themed artifact.  The roster is
# DECLARED in emitters.ROLES and the tree is checked against it (W65).
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
    "make_inherit.py":  "emits icon/cursor themes that INHERIT Breeze and draw nothing; "
                        "the palette reaches the icons through FollowsColorScheme, not "
                        "through this file (W31)",
}


def emitters():
    """[(filename, [authorities it reads])] for each DECLARED colour emitter.

    ⚑ THE ROSTER IS DECLARED, NOT DISCOVERED (W65, 2026-09-22). This walked
    os.listdir(ROOT) for make_*.py and subtracted a local exemption dict — a
    DISCOVERED population, which cannot tell a clean tree from a deleted one.
    Remove make_css.py and this reported "15 of 15 emitters source from the
    palette" and exited 0: n of n is green for every n.

    ⚑ AND emitters.py ALREADY CLAIMED TO BE THE ROSTER. Its docstring says "ONE
    ROSTER, TWO READERS" and names the incident that cost an install its Aurorae
    decorations when two readers disagreed. This file was the THIRD reader,
    keeping its own list — so the fix is a collapse, not a new mechanism:
    emitters.ROLES now carries a role per module and this reads `emitter` from
    it. The local NON_EMITTER dict kept its REASONS, which the roles do not
    carry, so it stays as prose beside them rather than as a second population."""
    import emitters as ROSTER
    out = []
    for mod in ROSTER.declared("emitter"):
        fn = mod + ".py"
        path = os.path.join(ROOT, fn)
        if not os.path.isfile(path):
            out.append((fn, None))          # declared and absent — main() refuses
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        reads = []
        for a in AUTHORITIES:
            # a direct import, or a transitive one via another emitter
            if re.search(r"\b(?:import\s+%s\b|from\s+%s\s+import)" % (a, a), text):
                reads.append(a)
        # a target may reach tokens through a sibling emitter (e.g. the marquee
        # reuses the live wallpaper's colors_for) — that is still sourcing.
        # the siblings are the DECLARED roster too, not os.listdir(ROOT) — which
        # also held untracked files, and whose order made the `via` pick arbitrary
        if not reads:
            for other in ROSTER.declared():
                if other.startswith("make_") and other + ".py" != fn:
                    mod = other
                    if re.search(r"\b(?:import\s+%s\b|from\s+%s\s+import)" % (mod, mod), text):
                        reads.append(f"via {mod}")
                        break
        out.append((fn, reads))
    return out


def measure(em=None, drift=None, declared=None):
    """The MEASUREMENT policy/token_source.rego decides (W50): per declared
    emitter, whether its file is present and which authorities it reads (direct
    or `via` a sibling emitter); the roster drift (emitters.drift: modules in the
    tree without a role, roles without a module) beside the number declared.
    That drift, an absent file, an empty roster and an emitter reading nothing
    are defects by the policy's ruling, not here."""
    import emitters as ROSTER
    em = emitters() if em is None else em
    undeclared, absent = ROSTER.drift(ROOT) if drift is None else drift
    return {"authorities": list(AUTHORITIES),
            "declared": len(ROSTER.ROLES) if declared is None else declared,
            "undeclared": [f"{m}.py" for m in undeclared],
            "absent": [f"{m}.py" for m in absent],
            "cases": [{"file": fn, "present": reads is not None, "reads": reads or []}
                      for fn, reads in em]}


def main(argv):
    known = {"--map", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_token_source: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--map" in argv:
        for fn, reads in emitters():
            print(f"{fn}\t{'ABSENT' if reads is None else (', '.join(reads) or '(NONE)')}")
        return 0
    import opa_gate
    return opa_gate.gate("token_source")


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
    # ⚑ THE MEASUREMENT CAN SEE (W50) the three shapes the policy refuses —
    # make_wallpaper computing its own colours (reads nothing), a declared file
    # deleted (the W65 shrink), an undeclared generator — as facts.
    m = measure([("make_wallpaper.py", []), ("make_css.py", None)], (["make_new"], ["make_css"]), 2)
    check("an emitter reading no authority is seen", m["cases"][0],
          {"file": "make_wallpaper.py", "present": True, "reads": []})
    check("a declared, absent emitter is seen", m["cases"][1]["present"], False)
    check("roster drift is seen", (m["undeclared"], m["absent"]), (["make_new.py"], ["make_css.py"]))
    print("check_token_source selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
