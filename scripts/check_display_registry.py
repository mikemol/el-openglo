#!/usr/bin/env python3
"""check_display_registry.py — the emitted registry IS the Python one.

⚑ THIS CHECK EXISTS BECAUSE ITS SUBJECT VANISHED AND ITS CLOSURE DID NOT.
COTYPE.md's ⊕DOT-WIRE closure states that make_clock emits the whole
display_types registry via `display_types.as_qml_js()` — "single source, nothing
retyped". Measured during the g-calculus work: `as_qml_js` had ZERO definitions
and ZERO callers, and `litPrimitives` was absent from every consumer. The
capability was lost in the recovery; the prose asserting it survived.

That is the same defect shape as RECOVERY-NOTES.md's stale "main rebuild gap" —
a hand-written status that decayed into a false claim — and the repo's answer is
to compute status instead of recording it. So this recomputes the agreement every
run rather than trusting either side.

    scripts/check_display_registry.py           # exit 0 iff the emission round-trips
    scripts/check_display_registry.py --show    # the registry's shape, n of m
    scripts/check_display_registry.py --selftest

⚑ WHAT IS ACTUALLY CHECKED.  `as_qml_js` is JSON-compatible by construction, so
this parses it back and compares against `registry()` — a ROUND TRIP, not a
re-derivation. That catches a serialisation that drops or mangles a table, which
is the failure a byte-count cannot see. It does NOT prove the QML consuming it
renders correctly; only a rendered sample does that, which is what @SAMPLES and
the clipped-plymouth episode are for.

⚑ AND THE GLYPH TABLES ARE COMPARED AGAINST THE SUBSTRATE, not merely against
themselves. A registry that round-trips perfectly while disagreeing with
segment_topology would be internally consistent and wrong — exactly the
"instrument agrees with itself" failure mode.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import display_types as DT                                        # noqa: E402
import segment_topology as ST                                     # noqa: E402


def roundtrip():
    """(ok, [problem]) — does as_qml_js() parse back to registry()?"""
    want = DT.registry()
    try:
        got = json.loads(DT.as_qml_js())
    except ValueError as e:
        return False, [f"as_qml_js is not parseable: {e}"]
    bad = []
    for key in sorted(set(want) | set(got)):
        if key not in got:
            bad.append(f"{key}: emitted registry is missing it")
        elif key not in want:
            bad.append(f"{key}: emitted registry invents it")
        elif json.loads(json.dumps(want[key], sort_keys=True)) != got[key]:
            bad.append(f"{key}: emitted value differs from registry()")
    return not bad, bad


def against_substrate():
    """[problem] — the registry's glyphs agree with segment_topology's own."""
    r = DT.registry()
    bad = []
    for fmt, table in sorted(r["segGlyphs"].items()):
        for ch, segs in sorted(table.items()):
            src = None
            for tbl in (ST.DIGITS16, ST.LETTERS16, ST.SYMBOLS16):
                if ch in tbl:
                    src = tbl[ch]
                    break
            if src is None:
                bad.append(f"segGlyphs[{fmt}][{ch!r}] is in no substrate table")
                continue
            g = set(src.split()) if src else set()
            want = sorted(ST.project(g, fmt)) if g else []
            if want != segs:
                bad.append(f"segGlyphs[{fmt}][{ch!r}] = {segs} but the substrate "
                           f"projects {want}")
    # every stroke the geometry names must exist in the substrate
    for sid in sorted(r["segGeom"]):
        if sid not in ST.GEOM22:
            bad.append(f"segGeom names {sid!r}, which GEOM22 does not define")
    return bad


def counts():
    r = DT.registry()
    return {
        "segGeom strokes": len(r["segGeom"]),
        "segGlyph formats": len(r["segGlyphs"]),
        "font5x7 glyphs": len(r["font5x7"]),
        "displays": len(r["displays"]),
    }


def main(argv):
    known = {"--show", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_display_registry: unknown flag {a!r}", file=sys.stderr)
            return 2

    n = counts()
    if "--show" in argv:
        r = DT.registry()
        for label, v in n.items():
            print(f"{label}\t{v}")
        for key, d in sorted(r["displays"].items()):
            print(f"  display {key}\tkind={d['kind']}\tcell={d['cell']}")
        return 0

    # ⚑ AN EMPTY POPULATION IS A BROKEN SEARCH, NOT AN AGREEING REGISTRY.
    if not all(n.values()):
        print(f"check_display_registry: REFUSED — an empty population ({n}); the "
              f"registry is not built, not the emission faithful", file=sys.stderr)
        return 2

    ok, bad = roundtrip()
    bad += against_substrate()
    total = sum(n.values())
    if bad:
        print(f"check_display_registry: REFUSED — {len(bad)} disagreement(s) over "
              f"{total} registry entries:", file=sys.stderr)
        for b in bad[:20]:
            print(f"    {b}", file=sys.stderr)
        if len(bad) > 20:
            print(f"    ... and {len(bad) - 20} more", file=sys.stderr)
        return 1
    print(f"check_display_registry: {total} of {total} entries round-trip and agree "
          f"with the substrate ({n['segGeom strokes']} strokes, "
          f"{n['segGlyph formats']} formats, {n['font5x7 glyphs']} matrix glyphs, "
          f"{n['displays']} displays)")
    return 0


def _selftest():
    """Prove the comparison can SEE a corrupted emission.

    ⚑ THE ROUND TRIP MUST BE ABLE TO FAIL.  A comparison of a value with itself
    always passes, and that is the shape a careless round-trip check takes: emit,
    parse, compare, green forever. So each case below breaks one side and asserts
    the check reports it."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("the real registry agrees", main(["x"]), 0)
    check("the round trip is clean", roundtrip()[0], True)
    check("nothing disagrees with the substrate", against_substrate(), [])

    # 1. a serialisation that DROPS a table
    saved = DT.as_qml_js
    try:
        DT.as_qml_js = lambda indent=None: json.dumps(
            {k: v for k, v in DT.registry().items() if k != "font5x7"})
        good, bad = roundtrip()
        check("sees a dropped table", good is False and any("font5x7" in b for b in bad),
              True)
    finally:
        DT.as_qml_js = saved

    # 2. a serialisation that MANGLES a value
    try:
        def _mangled(indent=None):
            r = DT.registry()
            r["segGeom"] = {k: [0, 0, 0, 0] for k in r["segGeom"]}
            return json.dumps(r)
        DT.as_qml_js = _mangled
        good, bad = roundtrip()
        check("sees a mangled table", good is False and any("segGeom" in b for b in bad),
              True)
    finally:
        DT.as_qml_js = saved

    # ⚑ THE SUBSET MUST BE A SUBSET, AND MUST REFUSE A NAME IT DOES NOT HAVE.
    # `registry_for` exists because emitting the whole registry shipped five
    # segment formats into a dot-matrix widget that reads none of them. A subset
    # that quietly returns the wrong tables — or an empty one for a typo'd key —
    # would restore that defect while every byte-count looked plausible.
    matrix_only = DT.registry_for("5x7")
    check("a matrix-only subset carries the font", "font5x7" in matrix_only, True)
    check("a matrix-only subset drops segment glyphs",
          "segGlyphs" not in matrix_only, True)
    check("a matrix-only subset drops segment geometry",
          "segGeom" not in matrix_only, True)
    check("a matrix-only subset names one display", len(matrix_only["displays"]), 1)

    seg_only = DT.registry_for("7")
    check("a segment-only subset carries geometry", "segGeom" in seg_only, True)
    check("a segment-only subset drops the matrix font",
          "font5x7" not in seg_only, True)
    check("a segment-only subset carries ONLY its format",
          sorted(seg_only["segGlyphs"]), ["7"])

    both = DT.registry_for("7", "5x7")
    check("a mixed subset carries both",
          "segGeom" in both and "font5x7" in both, True)

    try:
        DT.registry_for("no-such-display")
        check("an unknown display refuses", False, True)
    except KeyError:
        check("an unknown display refuses", True, True)

    # every subset must still be a faithful restriction of the whole
    whole = DT.registry()
    for key in ("7", "5x7"):
        sub = DT.registry_for(key)
        check(f"subset {key} agrees with the whole on its display",
              sub["displays"][key], whole["displays"][key])

    # 3. a registry that disagrees with the SUBSTRATE while round-tripping fine
    saved_reg = DT.registry
    try:
        def _wrong():
            r = saved_reg()
            fmt = sorted(r["segGlyphs"])[0]
            ch = sorted(r["segGlyphs"][fmt])[0]
            r["segGlyphs"][fmt][ch] = ["zz"]
            return r
        DT.registry = _wrong
        check("sees a substrate disagreement", len(against_substrate()) > 0, True)
    finally:
        DT.registry = saved_reg

    print("check_display_registry selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
