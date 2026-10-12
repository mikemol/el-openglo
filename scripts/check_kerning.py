#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_kerning.py — do adjacent letters bleed into one another through the pip mask? (W76)

⚑ THE REQUIREMENT IS policy/kerning.rego; THIS IS THE MEASUREMENT. The operator's
ruling (2026-09-25): kerning is a CLOSED LOOP — a pair is pushed apart only while
it bleeds — so the gate reads the RESULT from pixels, never the widget's offsets.
The same body text is run plain and <b>…</b> (bold's grow overhangs into neighbour
pips) through the STEPPED capture of the real widget, and every frame of a phase
sweep is read back as a pip grid; per view and style, the widest interior STROKE
GROUP (columns whose brightest ink is at least 0.6 of the still's peak). Letters
that bleed fuse into a group about twice a glyph wide; kerned letters stay one
glyph (+ its bloom) each.

    scripts/check_kerning.py --json [VARIANT]   # the facts rego judges (default EL-Openglo)
    scripts/check_kerning.py --selftest          # the group reader can SEE a fused pair
    scripts/opa_gate.py kerning [VARIANT]        # measurement + policy, one verdict

⚑ THE BINARY LIT-RUN RULE (K1) IS RETIRED (W529). It read ONE still, taken at the first sample with the
text mid-board, so the scroll phase depended on frame timing (the same RHI run gave three different run
lists at one speed), and at a half-pip phase the colour-vision views' per-still threshold fused the whole
text into an 18 to 45 column run. The stroke group is graded against the still's peak, reads identically
in every view at every phase (4 or 5 columns regular, 5 or 6 bold, measured over stepped frames 8 to
22), and catches the same defect: with the kern loop disabled (KERN_CAP = 0) K1 and K4 both denied, in
all four views, at a 30-column group.

The glyph width is the registry's (display_types.DISPLAYS[make_notify_marquee.
MATRIX_DISPLAY].cols) — the one number the widget's advanceCells derives from.

WEAKNESS: one variant by default (each style is a real Qt run, ~CPU seconds each); groups are per
COLUMN over all rows, so a letter pair whose ink never shares a column cannot fuse in this measure even
if a diagonal bleed would read as touching; the first and last groups are dropped as possibly clipped by
the board's edges; the sweep stops at frame 22 because bold text garbles from frame 23 (W528), a
separate defect not yet understood.
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


# the stepped frames the sweep reads: 15 consecutive frames span several cycles of the 0.618-pip step,
# so aligned and half-pip phases are both met. Frame 22 is the last: from frame 23 the bold text
# garbles (W528), a separate defect this sweep must not be asked to judge until it is understood.
GAP_FRAMES = range(8, 23)


def measure(variant):
    import check_urgency_cues as UC

    with tempfile.TemporaryDirectory() as td:
        g = UC.gap_facts(variant, td, GAP_FRAMES)
    if "withheld" in g:
        return {"gaps": [], "withheld": [{"variant": variant, "reason": g["withheld"]}]}
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
    return {"gaps": gaps, "withheld": []}


def _selftest():
    import check_urgency_cues as UC
    import numpy as np

    ok = True

    def chk(label, got, want):
        nonlocal ok
        good = got == want
        ok &= good
        print(f"  {'ok  ' if good else 'FAIL'} {label}: got {got!r}")

    # the graded gap: a dark gap reads 0, a half-lit gap reads 0.5, no gap at all reads no valley
    dark = np.zeros((8, 20))
    dark[:, 1:6] = 1.0
    dark[:, 7:12] = 1.0
    half = dark.copy()
    half[:, 6] = 0.5
    filled = dark.copy()
    filled[:, 6] = 1.0
    chk("a dark gap reads as ratio 0", UC.valley_ratios(dark), [0.0])
    chk("a half-lit gap reads as ratio 0.5", UC.valley_ratios(half), [0.5])
    chk("no gap at all reads as no valley", UC.valley_ratios(filled), [])
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
    # the half-pip phase that fused the old binary rule: every column at half coverage but for the gaps
    half_pip = np.zeros((8, 26))
    for start in (1, 7, 13, 19):
        half_pip[:, start : start + 5] = 0.5
        half_pip[:, start + 1 : start + 4] = 1.0
    chk(
        "a half-covered edge pip does not widen the group (graded, not binarised)",
        UC.stroke_groups(half_pip),
        [3, 3],
    )
    chk("the registry names a glyph width", glyph_cols() > 0, True)
    print(f"check_kerning selftest: {'PASS' if ok else 'FAIL'}")
    return ok


def main(argv):
    args = argv[1:]
    known = {"--json", "--selftest"}
    flags = [a for a in args if a.startswith("--")]
    for a in flags:
        if a not in known:
            print(f"check_kerning: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in flags:
        return 0 if _selftest() else 1
    rest = [a for a in args if not a.startswith("--")]
    if "--json" not in flags or len(rest) > 1:
        print("usage: check_kerning.py --json [VARIANT] | --selftest", file=sys.stderr)
        return 2
    print(json.dumps(measure(rest[0] if rest else VARIANT), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
