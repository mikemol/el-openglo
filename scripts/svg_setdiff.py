#!/usr/bin/env python3
"""svg_setdiff.py — do two SVGs draw the SAME MARKS, regardless of order?

⚑ BYTE EQUALITY IS THE WRONG QUESTION FOR A RENDER.  Two SVGs that emit the same
polygons in a different sequence are the same picture; `cmp` calls them
different, and a reviewer left with "they differ at byte 5943" has to decide by
eye whether that matters. It does not, if the marks are a set.

That case is not hypothetical here. Replacing a hand-authored glyph table with
the substrate's projection changed the ORDER segments are listed in — sorted
labels rather than drawing order — while every polygon stayed identical. The
picture is unchanged and the bytes are not.

    scripts/svg_setdiff.py <a.svg> <b.svg>          # same marks?
    scripts/svg_setdiff.py <a.svg> <b.svg> --marks  # the differing marks

⚑ A REORDERING IS NOT ALWAYS HARMLESS, AND THIS SAYS SO.  SVG paints in document
order, so if two marks OVERLAP, swapping them changes what covers what. This
answers the set question only; it reports the count of marks whose position
moved, so a caller can decide whether occlusion is in play rather than being told
"identical" about a z-order change.
"""
import os
import re
import sys

# every drawable element, with its attributes — the "marks" of the picture
_MARK = re.compile(r"<(polygon|rect|circle|path|text|line|ellipse)\b([^>]*)>")


def marks(path):
    """[(tag, attrs)] in document order."""
    text = open(path, encoding="utf-8", errors="replace").read()
    return [(m.group(1), m.group(2).strip()) for m in _MARK.finditer(text)]


def compare(a, b):
    """(same_set, only_a, only_b, moved) for two SVGs."""
    ma, mb = marks(a), marks(b)
    sa, sb = sorted(ma), sorted(mb)
    only_a = [m for m in sa if sa.count(m) > sb.count(m)]
    only_b = [m for m in sb if sb.count(m) > sa.count(m)]
    moved = sum(1 for x, y in zip(ma, mb) if x != y)
    return (sa == sb, only_a, only_b, moved)


def main(argv):
    known = {"--marks"}
    args = [a for a in argv[1:] if not a.startswith("--")]
    for a in argv[1:]:
        if a.startswith("--") and a not in known:
            print(f"svg_setdiff: unknown flag {a!r}", file=sys.stderr)
            return 2
    if len(args) != 2:
        print("usage: svg_setdiff.py <a.svg> <b.svg> [--marks]", file=sys.stderr)
        return 2
    for p in args:
        if not os.path.isfile(p):
            print(f"svg_setdiff: REFUSED — no such file {p}", file=sys.stderr)
            return 2
    same, only_a, only_b, moved = compare(*args)
    na, nb = len(marks(args[0])), len(marks(args[1]))
    if not na or not nb:
        print(f"svg_setdiff: REFUSED — {na} and {nb} marks; the scan found "
              f"nothing to compare", file=sys.stderr)
        return 2
    if "--marks" in argv[1:]:
        for m in only_a:
            print(f"- {m[0]} {m[1][:100]}")
        for m in only_b:
            print(f"+ {m[0]} {m[1][:100]}")
        return 0
    if not same:
        print(f"svg_setdiff: DIFFERENT — {len(only_a)} only in {os.path.basename(args[0])}, "
              f"{len(only_b)} only in {os.path.basename(args[1])} "
              f"(of {na} and {nb} marks)", file=sys.stderr)
        return 1
    if moved:
        print(f"svg_setdiff: SAME MARKS, {moved} of {na} REORDERED. Identical "
              f"picture unless marks overlap — SVG paints in document order, so "
              f"check occlusion before calling this cosmetic.")
        return 0
    print(f"svg_setdiff: identical — {na} marks, same order")
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

    import tempfile
    with tempfile.TemporaryDirectory() as td:
        a = os.path.join(td, "a.svg")
        b = os.path.join(td, "b.svg")
        c = os.path.join(td, "c.svg")
        open(a, "w").write('<svg><rect x="1"/><rect x="2"/></svg>')
        open(b, "w").write('<svg><rect x="2"/><rect x="1"/></svg>')   # reordered
        open(c, "w").write('<svg><rect x="1"/><rect x="3"/></svg>')   # changed
        same, oa, obb, moved = compare(a, b)
        check("a reordering has the same mark set", same, True)
        check("and reports how many moved", moved, 2)
        same2, oa2, ob2, _ = compare(a, c)
        check("a changed mark is DIFFERENT", same2, False)
        check("and names what differs", (len(oa2), len(ob2)), (1, 1))
    print("svg_setdiff selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
