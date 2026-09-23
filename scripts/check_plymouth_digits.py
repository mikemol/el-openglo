#!/usr/bin/env python3
"""check_plymouth_digits.py — the boot splash draws the substrate's glyphs.

⚑ PLYMOUTH IS THE SURFACE THAT LOOKED DE-SILOED AND WAS NOT.  It imports
segment_topology — so an import census reports it reading the shared geometry —
while carrying SEVENSEG and SEG_STROKE, its own copies of the digit glyphs and
the coarse strokes. Importing an authority and then not using it is the harder
version of the silo, because every scan that asks "does this read the substrate?"
says yes.

    scripts/check_plymouth_digits.py           # the verdict, as opa_gate plymouth_digits decides it
    scripts/check_plymouth_digits.py --json    # the measurement policy/plymouth_digits.rego decides
    scripts/check_plymouth_digits.py --table   # digit -> substrate vs plymouth
    scripts/check_plymouth_digits.py --selftest

⚑ THIS COMPARES GLYPHS, NOT PIXELS.  The renderer's job is to turn a segment set
into a polygon; the SUBSTRATE's job is to say which segments a digit lights.
Comparing rendered PNGs would conflate the two and fail on an antialiasing
change. What must agree is the segment set, in the substrate's own lowercase
7-seg naming. Which digits must be compared, and that the two sets must be
equal, is the policy's ruling (W50); this file only reads both tables.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

DIGITS = "0123456789"


def rows():
    """[(digit, substrate_segments, plymouth_segments)] for 0-9."""
    os.chdir(ROOT)
    import segment_topology as ST
    import make_plymouth as MP
    out = []
    for d in DIGITS:
        want = set(ST.project(ST.glyph16(d), "7"))
        got = set(MP.SEVENSEG.get(d, ()))
        out.append((d, sorted(want), sorted(got)))
    return out


def measure():
    """The MEASUREMENT policy/plymouth_digits.rego decides: one case per digit —
    the substrate's 7-seg projection and plymouth's SEVENSEG entry — or, when
    either table cannot be read at all, no cases and the `error` that stopped it."""
    try:
        data = rows()
    except Exception as e:                       # noqa: BLE001
        return {"cases": [], "error": f"{type(e).__name__}: {e}"}
    return {"error": None,
            "cases": [{"id": d, "substrate": w, "plymouth": g} for d, w, g in data]}


def main(argv):
    known = {"--table", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_plymouth_digits: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--table" in argv:
        m = measure()
        if m["error"]:
            print(f"check_plymouth_digits: cannot read the tables — {m['error']}", file=sys.stderr)
            return 2
        for c in m["cases"]:
            mark = "  " if c["substrate"] == c["plymouth"] else "！"
            print(f"{mark}{c['id']}\tsubstrate={''.join(c['substrate'])}\tplymouth={''.join(c['plymouth'])}")
        return 0
    import opa_gate
    return opa_gate.gate("plymouth_digits")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    m = measure()
    check("the tables are read", m["error"], None)
    check("all ten digits are measured", [c["id"] for c in m["cases"]], list(DIGITS))
    check("the substrate side is non-empty",
          all(c["substrate"] for c in m["cases"]), True)
    # ⚑ THE MEASUREMENT MUST SEE PLYMOUTH'S OWN TABLE, not a second view of the
    # substrate: drop a segment from plymouth's copy and the case must carry it.
    # That a differing digit is DENIED is policy/plymouth_digits_test.rego's ruling.
    import make_plymouth as MP
    saved = MP.SEVENSEG
    try:
        MP.SEVENSEG = dict(saved, **{"8": tuple(saved["8"])[1:]})
        c8 = next(c for c in measure()["cases"] if c["id"] == "8")
        check("a segment dropped from plymouth's table is measured",
              len(c8["plymouth"]), len(c8["substrate"]) - 1)
    finally:
        MP.SEVENSEG = saved
    print("check_plymouth_digits selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
