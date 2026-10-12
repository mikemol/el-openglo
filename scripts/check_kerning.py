#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_kerning.py — do adjacent letters bleed into one another through the pip mask? (W76)

⚑ THE REQUIREMENT IS policy/kerning.rego; THIS IS THE MEASUREMENT. The operator's
ruling (2026-09-25): kerning is a CLOSED LOOP — a pair is pushed apart only while
it bleeds — so the gate reads the RESULT from pixels, never the widget's offsets.
Two stills of the real widget (check_urgency_cues.bold_facts: the same body text
plain and <b>…</b>, where grow overhangs into neighbour pips) are read back as pip
grids; per view, the widths of the runs of lit columns between fully dark ones.
Letters that bleed merge into one run about twice a glyph wide; kerned letters stay
one glyph (+ its bloom) each.

    scripts/check_kerning.py --json [VARIANT]   # the facts rego judges (default EL-Openglo)
    scripts/check_kerning.py --json --frame N   # the stills from the STEPPED capture's frame N, a fixed
                                                # scroll offset on every host and scene graph (W525); the
                                                # gate uses the default moment-grab, see W526 for why
    scripts/check_kerning.py --selftest          # the run reader can SEE a merge
    scripts/opa_gate.py kerning [VARIANT]        # measurement + policy, one verdict

The glyph width is the registry's (display_types.DISPLAYS[make_notify_marquee.
MATRIX_DISPLAY].cols) — the one number the widget's advanceCells derives from.

WEAKNESS: one variant by default (each still is a real Qt run, ~CPU seconds each);
runs are per COLUMN over all rows, so a letter pair whose ink never shares a column
cannot merge in this measure even if a diagonal bleed would read as touching; the
first and last runs are dropped as possibly clipped by the board's edges.
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

VARIANT = "EL-Openglo"


def glyph_cols():
    import display_types as DT
    import make_notify_marquee as MNM

    return DT.DISPLAYS[MNM.MATRIX_DISPLAY].cols


def interior(runs):
    """The runs a caller may judge: the edge runs may be clipped by the board."""
    return runs[1:-1] if len(runs) > 2 else []


# the stepped frames the graded gap sweeps: 15 consecutive frames span several cycles of the 0.618-pip
# step, so aligned and half-pip phases are both met. Frame 22 is the last: from frame 23 the bold text
# garbles (W528), a separate defect this sweep must not be asked to judge until it is understood.
GAP_FRAMES = range(8, 23)


def measure(variant, still_frame=None):
    import check_urgency_cues as UC

    with tempfile.TemporaryDirectory() as td:
        f = UC.bold_facts(variant, td, still_frame)
        g = UC.gap_facts(variant, td, GAP_FRAMES)
    if "withheld" in f or "withheld" in g:
        return {
            "cases": [],
            "gaps": [],
            "withheld": [
                {"variant": variant, "reason": f.get("withheld") or g["withheld"]}
            ],
        }
    cols = glyph_cols()
    gaps = [
        {
            "variant": variant,
            "view": view,
            "style": style,
            "glyph_cols": cols,
            "frames": cell["frames"],
            "max_group": cell["group"],
            "worst_gap_ratio": cell["worst"],
        }
        for view, styles in sorted(g["views"].items())
        for style, cell in sorted(styles.items())
    ]
    cases = []
    for view, v in sorted(f["views"].items()):
        for style in ("regular", "bold"):
            runs = v[f"runs_{style}"]
            cases.append(
                {
                    "variant": variant,
                    "view": view,
                    "style": style,
                    "glyph_cols": cols,
                    "runs": runs,
                    "interior_runs": interior(runs),
                }
            )
    return {"cases": cases, "gaps": gaps, "withheld": []}


def _selftest():
    import check_urgency_cues as UC
    import numpy as np

    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: got {got!r}")

    # two 5-wide letters with a dark column between vs the same two touching
    apart = np.zeros((8, 20), bool)
    apart[:, 1:6] = True
    apart[:, 7:12] = True
    merged = np.zeros((8, 20), bool)
    merged[:, 1:6] = True
    merged[:, 6:11] = True
    chk("kerned letters read as two runs", UC.lit_runs(apart), [5, 5])
    chk("bleeding letters read as ONE run twice as wide", UC.lit_runs(merged), [10])
    chk("the edge runs are not judged", interior([3, 5, 5, 2]), [5, 5])
    # the graded gap: a dark gap reads 0, a half-lit gap reads 0.5, no gap at all reads 1.0
    dark = np.zeros((8, 20))
    dark[:, 1:6] = 1.0
    dark[:, 7:12] = 1.0
    half = dark.copy()
    half[:, 6] = 0.5
    fused = dark.copy()
    fused[:, 6] = 1.0
    chk("a dark gap reads as ratio 0", UC.valley_ratios(dark), [0.0])
    chk("a half-lit gap reads as ratio 0.5", UC.valley_ratios(half), [0.5])
    chk("no gap at all reads as no valley", UC.valley_ratios(fused), [])
    chk("a blank still has no valleys", UC.valley_ratios(np.zeros((8, 20))), [])
    # the stroke group: the fused pair is the one the valley cannot see, and the group width does
    four = np.zeros((8, 26))
    for start in (1, 7, 13, 19):
        four[:, start : start + 5] = 1.0
    fused = four.copy()
    fused[:, 12] = 1.0  # the gap between the middle pair filled
    chk(
        "four kerned letters: both interior groups are one glyph wide",
        UC.stroke_groups(four),
        [5, 5],
    )
    chk(
        "a fused middle pair reads as one interior group twice a glyph wide",
        UC.stroke_groups(fused),
        [11],
    )
    chk("the registry names a glyph width", glyph_cols() > 0, True)
    print(f"check_kerning selftest: {'PASS' if ok else 'FAIL'}")
    return ok


def main(argv):
    args = argv[1:]
    known = {"--json", "--selftest", "--frame"}
    flags = [a for a in args if a.startswith("--")]
    for a in flags:
        if a not in known:
            print(f"check_kerning: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in flags:
        return 0 if _selftest() else 1
    still_frame = None
    if "--frame" in args:
        i = args.index("--frame")
        if i + 1 >= len(args) or not args[i + 1].isdigit():
            print("check_kerning: --frame needs a frame number", file=sys.stderr)
            return 2
        still_frame = int(args[i + 1])
        del args[i : i + 2]
    rest = [a for a in args if not a.startswith("--")]
    if "--json" not in flags or len(rest) > 1:
        print(
            "usage: check_kerning.py --json [--frame N] [VARIANT] | --selftest",
            file=sys.stderr,
        )
        return 2
    print(json.dumps(measure(rest[0] if rest else VARIANT, still_frame), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
