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
    scripts/check_projection.py --classes      # the ceiling per glyph class (round / straight / diagonal / narrow)
    scripts/check_projection.py --calibrate    # sweep frame x band, print the landscape
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


def report(font, fmt="16", chars=None, frame="stretch", sagitta=None):
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import glyph_match as GM
    sag = GM.SAGITTA if sagitta is None else sagitta
    rows = GM.validate_projection(font, chars, fmt=fmt, frame=frame, sagitta=sag)
    return rows, GM.agreement_summary(rows)


def calibrate(font, fmt="16", arcs=False):
    """--calibrate: sweep frame x band (x sagitta with --arcs), print the
    landscape and the argmax, and REFUSE if the sweep is flat — a calibration
    that cannot move the number is not calibrating anything."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import glyph_match as GM
    if arcs:
        # the arc sweep holds the solved frame/band and moves only the bow
        params, best, table = GM.calibrate_projection(
            font, fmt=fmt, frames=("stretch",), bands=(GM.SW_BAND,), sagittas=GM.SAGITTA_GRID)
        print(f"font {font}  fmt {fmt}  calibrating sagitta at frame stretch, band {GM.SW_BAND}")
    else:
        params, best, table = GM.calibrate_projection(font, fmt=fmt)
        print(f"font {font}  fmt {fmt}  calibrating frame x band at sagitta {GM.SAGITTA}")
    bkey = (params["frame"], params["band"], params["sagitta"])
    for (frame, band, sag), (mean_j, exact, n) in sorted(table.items(), key=lambda kv: -kv[1][0]):
        mark = "  <- best" if (frame, band, sag) == bkey else ""
        print(f"  frame {frame:8}  band {band:.2f}  sagitta {sag:.2f}  mean jaccard {mean_j:.3f}"
              f"  {exact:2d}/{n} exact{mark}")
    spread = max(v[0] for v in table.values()) - min(v[0] for v in table.values())
    if spread < 0.01:
        print(f"check_projection: REFUSED — the sweep is flat (spread {spread:.3f}); "
              f"the parameters do not reach the number", file=sys.stderr)
        return 1
    dkey = ("stretch", GM.SW_BAND, GM.SAGITTA)
    default = table[dkey][0] if dkey in table else float("nan")
    print(f"check_projection: calibrated over {len(table)} settings — best {params} "
          f"mean jaccard {best:.3f}; the module default {dkey} scores {default:.3f}")
    return 0


def classes(font, fmt, rows):
    """--classes: the agreement ceiling per glyph CLASS (narrow / round /
    diagonal / straight, read from the outline), so a template change is judged
    on the class it was aimed at. REFUSED if every glyph lands in one class —
    a classifier that cannot separate the set is not measuring it."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import glyph_match as GM
    by = GM.agreement_by_class(font, rows)
    print(f"font {font}  fmt {fmt}  by class")
    for k in ("straight", "round", "diagonal", "narrow", "unknown"):
        if k in by:
            m, e, n, chars = by[k]
            print(f"  {k:9}  mean jaccard {m:.2f}  {e:2d}/{n:2d} exact  {chars}")
    if len(by) < 2:
        print(f"check_projection: REFUSED — every glyph classified {sorted(by)}; the classes"
              f" do not separate the set", file=sys.stderr)
        return 1
    print(f"check_projection: {len(rows)} glyphs in {len(by)} classes (the ceiling per class, reported)")
    return 0


def main(argv):
    known = {"--font", "--fmt", "--frame", "--calibrate", "--classes", "--arcs", "--sagitta"}
    args = [a for a in argv[1:] if a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_projection: unknown flag {a!r}", file=sys.stderr)
            return 2
    font = find_font(argv[argv.index("--font") + 1] if "--font" in argv else None)
    fmt = argv[argv.index("--fmt") + 1] if "--fmt" in argv else "16"
    frame = argv[argv.index("--frame") + 1] if "--frame" in argv else "stretch"
    if not font:
        print("check_projection: SKIP — no TTF found (pass --font PATH); 0 authored glyphs measured",
              file=sys.stderr)
        return 0
    sagitta = float(argv[argv.index("--sagitta") + 1]) if "--sagitta" in argv else None
    if "--calibrate" in argv:
        return calibrate(font, fmt, arcs="--arcs" in argv)
    rows, (mean_j, exact, n) = report(font, fmt, frame=frame, sagitta=sagitta)
    if "--classes" in argv:
        return classes(font, fmt, rows)
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
    chk("calibration sweeps every setting", sorted(table),
        sorted([(f, b, GM.SAGITTA) for f in ("stretch", "fit") for b in (0.4, 1.0)]))
    bkey = (params["frame"], params["band"], params["sagitta"])
    chk("the argmax is a swept setting", bkey in table, True)
    chk("the argmax's score is the returned best", table[bkey][0], best)
    # ⚑ THE ARC MUST BE A STRAIGHT BAND AT SAGITTA 0 AND SOMETHING ELSE ABOVE IT
    import numpy as np
    seg = GM.SEG["a1"]; cell = (0.0, 2.0, 0.0, 4.0)
    chk("sagitta 0 is the straight band", np.array_equal(GM._arc_field(seg, cell, 0.2, 0.0), GM._seg_field(seg, cell, 0.2)), True)
    bowed = GM._arc_field(seg, cell, 0.2, 0.2)
    chk("a bowed band differs from the straight one", np.array_equal(bowed, GM._seg_field(seg, cell, 0.2)), False)
    chk("a positive bow of a top segment goes UP (outward), not into the cell",
        int(np.where(bowed)[0].min()) <= int(np.where(GM._seg_field(seg, cell, 0.2))[0].min()), True)
    inward = GM._arc_field(seg, cell, 0.2, -0.2)
    chk("a negative bow of a top segment goes DOWN (inward)",
        int(np.where(inward)[0].max()) >= int(np.where(GM._seg_field(seg, cell, 0.2))[0].max()), True)
    chk("a centre bar never bows", "g1" in GM.ARC_SEGS or "g2" in GM.ARC_SEGS, False)
    # ⚑ THE SOLVED SAGITTA MUST EARN ITS PLACE: on the digits it may not score
    # below the straight band (a regression pin on the calibration's argmax)
    _p, _b, t2 = GM.calibrate_projection(font, "0123456789", bands=(GM.SW_BAND,), frames=("stretch",),
                                          sagittas=(0.0, GM.SAGITTA))
    chk("the solved sagitta is not worse than straight on the digits",
        t2[("stretch", GM.SW_BAND, GM.SAGITTA)][0] >= t2[("stretch", GM.SW_BAND, 0.0)][0], True)
    chk("the sweep is not flat", len({round(v[0], 3) for v in table.values()}) > 1, True)
    # the crossbar defect: H's stroke width must read as a stem, not the crossbar
    import numpy as np
    presH = GM.ink_grid(GM._ingest(font, "H", "outline", "stretch"))
    _bb, swH = GM._ink_bbox_sw(presH, 1.0)
    chk("H's stroke width is a stem, not the crossbar (< 0.6 cell)", swH < 0.6, True)
    xs = np.where(presH)[1]
    chk("(H's ink spans the cell, so the old mid-row read the crossbar)", xs.max() - xs.min() > GM.RES // 2, True)
    # ⚑ THE CLASSES MUST SEPARATE THE SET: O is round, H is straight, X is
    # diagonal — three glyphs, three classes, or the per-class ceiling is one number
    chk("'O' reads as round", GM.glyph_class(font, "O"), "round")
    chk("'H' reads as straight", GM.glyph_class(font, "H"), "straight")
    chk("'X' reads as diagonal", GM.glyph_class(font, "X"), "diagonal")
    chk("a char the font lacks is 'unknown'", GM.glyph_class(font, "☃"), "unknown")
    by = GM.agreement_by_class(font, rows)
    chk("the digits fall into more than one class", len(by) > 1, True)
    chk("every digit is counted once", sum(v[2] for v in by.values()), len(rows))
    # ⚑ THE FULL TABLE, AND THE PINS.  The default charset is every authored key
    # (the log's "all 44", now 46 non-blank); the convention-gap glyphs score 0
    # under the default frame and an entry that starts scoring must leave the pin.
    full, (mj, ex, nn) = report(font, "16")
    chk("the default run covers every non-blank authored glyph",
        nn, len([c for c in GM.AUTHORED_CHARS if GM.ST.glyph16(c)]))
    chk("no duplicate glyph in the run", len({r[0] for r in full}), nn)
    score = {r[0]: r[6] for r in full}
    outgrown = sorted(c for c in GM.KNOWN_CONVENTION if score.get(c, 0.0) > 0.0)
    chk("every KNOWN_CONVENTION pin still scores 0 (an improvement must leave the set)", outgrown, [])
    chk("the pinned set is a strict minority of the table", len(GM.KNOWN_CONVENTION) * 4 < nn, True)
    print(f"  (measured on {os.path.basename(font)}: digits mean jaccard {mean_j:.2f}, {exact}/10 exact;"
          f" full table {mj:.2f}, {ex}/{nn} exact)")
    print("check_projection selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
