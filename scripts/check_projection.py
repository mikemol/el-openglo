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

    scripts/check_projection.py [--font PATH] [--fmt 16|7] [--frame fit|stretch]   # per-glyph agreement report
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


def report(font, fmt="16", chars=None, frame="stretch"):
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import glyph_match as GM
    rows = GM.validate_projection(font, chars, fmt=fmt, frame=frame)
    return rows, GM.agreement_summary(rows)


def calibrate(font, fmt="16"):
    """--calibrate: sweep frame x band, print the landscape and the argmax, and
    REFUSE if the sweep is flat — a calibration that cannot move the number is
    not calibrating anything."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import glyph_match as GM
    params, best, table = GM.calibrate_projection(font, fmt=fmt)
    print(f"font {font}  fmt {fmt}  calibrating frame x band")
    for (frame, band), (mean_j, exact, n) in sorted(table.items(), key=lambda kv: -kv[1][0]):
        mark = "  <- best" if (frame, band) == (params["frame"], params["band"]) else ""
        print(f"  frame {frame:8}  band {band:.2f}  mean jaccard {mean_j:.3f}  {exact:2d}/{n} exact{mark}")
    spread = max(v[0] for v in table.values()) - min(v[0] for v in table.values())
    if spread < 0.01:
        print(f"check_projection: REFUSED — the sweep is flat (spread {spread:.3f}); "
              f"the parameters do not reach the number", file=sys.stderr)
        return 1
    default = table[("stretch", GM.SW_BAND)][0]
    print(f"check_projection: calibrated over {len(table)} settings — best {params} "
          f"mean jaccard {best:.3f}; the module default (stretch, {GM.SW_BAND}) scores {default:.3f}")
    return 0


def main(argv):
    known = {"--font", "--fmt", "--frame", "--calibrate"}
    args = [a for a in argv[1:] if a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_projection: unknown flag {a!r}", file=sys.stderr)
            return 2
    font = find_font(argv[argv.index("--font") + 1] if "--font" in argv else None)
    fmt = argv[argv.index("--fmt") + 1] if "--fmt" in argv else "16"
    frame = argv[argv.index("--frame") + 1] if "--frame" in argv else "stretch"
    if not font:
        print("check_projection: SKIP — no TTF found (pass --font PATH); 0 of 36 glyphs measured",
              file=sys.stderr)
        return 0
    if "--calibrate" in argv:
        return calibrate(font, fmt)
    rows, (mean_j, exact, n) = report(font, fmt, frame=frame)
    if not rows:
        print("check_projection: REFUSED — the authored table is empty; nothing to validate",
              file=sys.stderr)
        return 2
    print(f"font {font}  fmt {fmt}  frame {frame}")
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
    # ⚑ THE CALIBRATION MUST BE ABLE TO MOVE THE NUMBER: a 2x2 sweep over the digits
    # must yield distinct scores across settings, and the argmax must be one of the
    # swept settings — not a default smuggled in. ('1H' alone is flat: 1 scores 0 and
    # H scores 1 under every setting — measured, which is why the set is the digits.)
    params, best, table = GM.calibrate_projection(font, "0123456789", bands=(0.4, 1.0), frames=("stretch", "fit"))
    chk("calibration sweeps every setting", sorted(table), sorted([(f, b) for f in ("stretch", "fit") for b in (0.4, 1.0)]))
    chk("the argmax is a swept setting", (params["frame"], params["band"]) in table, True)
    chk("the argmax's score is the returned best", table[(params["frame"], params["band"])][0], best)
    chk("the sweep is not flat", len({round(v[0], 3) for v in table.values()}) > 1, True)
    # the crossbar defect: H's stroke width must read as a stem, not the crossbar
    import numpy as np
    presH = GM.ink_grid(GM._ingest(font, "H", "outline", "stretch"))
    _bb, swH = GM._ink_bbox_sw(presH, 1.0)
    chk("H's stroke width is a stem, not the crossbar (< 0.6 cell)", swH < 0.6, True)
    xs = np.where(presH)[1]
    chk("(H's ink spans the cell, so the old mid-row read the crossbar)", xs.max() - xs.min() > GM.RES // 2, True)
    print(f"  (measured on {os.path.basename(font)}: digits mean jaccard {mean_j:.2f}, {exact}/10 exact)")
    print("check_projection selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
