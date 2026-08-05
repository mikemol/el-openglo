#!/usr/bin/env python3
"""check_plymouth_digits.py — the boot splash draws the substrate's glyphs.

⚑ PLYMOUTH IS THE SURFACE THAT LOOKED DE-SILOED AND WAS NOT.  It imports
segment_topology — so an import census reports it reading the shared geometry —
while carrying SEVENSEG and SEG_STROKE, its own copies of the digit glyphs and
the coarse strokes. Importing an authority and then not using it is the harder
version of the silo, because every scan that asks "does this read the substrate?"
says yes.

    scripts/check_plymouth_digits.py           # exit 0 iff its glyphs match
    scripts/check_plymouth_digits.py --table   # digit -> substrate vs plymouth

⚑ THIS COMPARES GLYPHS, NOT PIXELS.  The renderer's job is to turn a segment set
into a polygon; the SUBSTRATE's job is to say which segments a digit lights.
Comparing rendered PNGs would conflate the two and fail on an antialiasing
change. What must agree is the segment set, in the substrate's own lowercase
7-seg naming.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def rows():
    """[(digit, substrate_segments, plymouth_segments)] for 0-9."""
    os.chdir(ROOT)
    import segment_topology as ST
    import make_plymouth as MP
    out = []
    for d in "0123456789":
        want = set(ST.project(ST.glyph16(d), "7"))
        got = set(MP.SEVENSEG.get(d, ()))
        out.append((d, sorted(want), sorted(got)))
    return out


def main(argv):
    known = {"--table"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_plymouth_digits: unknown flag {a!r}", file=sys.stderr)
            return 2
    try:
        data = rows()
    except Exception as e:                       # noqa: BLE001
        print(f"check_plymouth_digits: REFUSED — {type(e).__name__}: {e}",
              file=sys.stderr)
        return 2
    if "--table" in argv:
        for d, want, got in data:
            mark = "  " if want == got else "！"
            print(f"{mark}{d}\tsubstrate={''.join(want)}\tplymouth={''.join(got)}")
        return 0
    bad = [(d, w, g) for d, w, g in data if w != g]
    if bad:
        print(f"check_plymouth_digits: REFUSED — {len(bad)} of {len(data)} digit(s) "
              f"differ from the substrate:", file=sys.stderr)
        for d, w, g in bad:
            print(f"    '{d}': substrate {''.join(w)} vs plymouth {''.join(g)}",
                  file=sys.stderr)
        print(f"  fixes: {len(bad)}", file=sys.stderr)
        return 1
    print(f"check_plymouth_digits: {len(data)} of {len(data)} digits match the "
          f"substrate's 7-seg projection")
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

    data = rows()
    check("all ten digits are compared", len(data), 10)
    check("the substrate side is non-empty",
          all(w for _d, w, _g in data), True)
    # ⚑ THE COMPARISON MUST BE ABLE TO FAIL: a digit whose sets differ must be
    # reported, so the check is not merely observing two views of one table.
    fake = [("X", ["a", "b"], ["a"])]
    check("a differing digit would be caught",
          [d for d, w, g in fake if w != g], ["X"])
    print("check_plymouth_digits selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
