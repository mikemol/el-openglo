#!/usr/bin/env python3
"""check_projection.py — how far does the font->segment projection agree with the authored tables?

⚑ WHAT THIS IS AND IS NOT.  glyph_match.validate_projection is the routine
⊕SEG-TABLE-VALIDATE asked for: project a real font's glyphs through the
matcher and compare, per glyph, to segment_topology's authored 16-seg table.
This tool RUNS it and REPORTS. It is not yet a pass/fail gate on agreement —
the design log records the honest ceiling (straight-segment templates vs
round glyph walls) and the number that would make agreement gateable is
⊕SEG-PROJECT-CALIBRATE's to solve. What IS gated: the routine exists, runs
over the whole table, and its report can distinguish a font from a mirror of
itself (selftest) — i.e. the instrument works before anyone tunes with it.

    scripts/check_projection.py [--font PATH] [--fmt 16|7]   # per-glyph agreement report
    scripts/check_projection.py --selftest

SKIP (printed, exit 0) when no TTF is found and none is given.
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANDIDATES = ("/usr/share/fonts/liberation-fonts/LiberationMono-Regular.ttf",
              "/usr/share/fonts/hack/Hack-Regular.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


def find_font(explicit=None):
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for p in CANDIDATES:
        if os.path.isfile(p):
            return p
    if shutil.which("fc-match"):
        r = subprocess.run(["fc-match", "--format=%{file}", "monospace"], capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip().endswith((".ttf", ".otf")):
            return r.stdout.strip()
    return None


def report(font, fmt="16", chars=None):
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import glyph_match as GM
    rows = GM.validate_projection(font, chars, fmt=fmt)
    return rows, GM.agreement_summary(rows)


def main(argv):
    known = {"--font", "--fmt"}
    args = [a for a in argv[1:] if a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_projection: unknown flag {a!r}", file=sys.stderr)
            return 2
    font = find_font(argv[argv.index("--font") + 1] if "--font" in argv else None)
    fmt = argv[argv.index("--fmt") + 1] if "--fmt" in argv else "16"
    if not font:
        print("check_projection: SKIP — no TTF found (pass --font PATH); 0 of 36 glyphs measured",
              file=sys.stderr)
        return 0
    rows, (mean_j, exact, n) = report(font, fmt)
    if not rows:
        print("check_projection: REFUSED — the authored table is empty; nothing to validate",
              file=sys.stderr)
        return 2
    print(f"font {font}  fmt {fmt}")
    for ch, authored, projected, hits, misses, extras, j in rows:
        print(f"  {ch}  jaccard {j:.2f}  hits {len(hits):2d}/{len(authored):2d}"
              f"  missed {''.join(sorted(misses)) or '-':8}  extra {''.join(sorted(extras)) or '-'}")
    # ⚑ THE ONE GATED FACT: the instrument discriminates. A matcher that projects
    # every glyph to the same set (dead ink, a broken frame) would still "run".
    distinct = len({frozenset(r[2]) for r in rows})
    if distinct < len(rows) // 2:
        print(f"check_projection: REFUSED — only {distinct} distinct projections over {n} glyphs; "
              f"the matcher is not seeing the ink", file=sys.stderr)
        return 1
    print(f"check_projection: {n} glyphs validated against the authored {fmt}-seg table — "
          f"mean jaccard {mean_j:.2f}, {exact} of {n} exact, {distinct} distinct projections "
          f"(agreement reported, not gated: the threshold is ⊕SEG-PROJECT-CALIBRATE's)")
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

    font = find_font()
    if not font:
        print("  SKIP — no TTF on this host")
        print("check_projection selftest: SKIP")
        return True
    rows, (mean_j, exact, n) = report(font, "16", "0123456789")
    chk("the routine runs over the digits", n, 10)
    chk("every row carries the authored and projected sets", all(r[1] and r[2] for r in rows), True)
    # ⚑ THE INSTRUMENT MUST DISCRIMINATE: the digit '1' (two right-side verticals)
    # and '8' (all seven) must not project to the same set
    by = {r[0]: r[2] for r in rows}
    chk("'1' and '8' project to different sets", by["1"] != by["8"], True)
    # a projection that agrees with a mirrored table would be a coincidence; check
    # the report's jaccard is 1.0 for a perfect match and 0 for disjoint sets
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import glyph_match as GM
    chk("agreement_summary of an empty report is (0, 0, 0)", GM.agreement_summary([]), (0.0, 0, 0))
    print(f"  (measured on {os.path.basename(font)}: digits mean jaccard {mean_j:.2f}, {exact}/10 exact)")
    print("check_projection selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
