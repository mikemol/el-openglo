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

    scripts/check_display_registry.py           # the verdict, as opa_gate display_registry decides it
    scripts/check_display_registry.py --json    # the measurement policy/display_registry.rego decides
    scripts/check_display_registry.py --show    # the registry's shape, n of m
    scripts/check_display_registry.py --glyph CHARS   # a matrix glyph's bitmap
    scripts/check_display_registry.py --selftest

⚑ THE REQUIREMENT IS REGO (W50). policy/display_registry.rego holds the four
rules — D0 a non-empty population of every kind, D1 the round trip, D2 agreement
with the substrate, D3 the font's own structure — and policy/
display_registry_test.rego holds their refusing cases, including the exact 'A'
that shipped (crossbar one row low). This file only MEASURES.

⚑ WHAT IS ACTUALLY CHECKED.  `as_qml_js` is JSON-compatible by construction, so
the measurement parses it back and reports, per key, whether it equals
`registry()` — a ROUND TRIP, not a re-derivation. That catches a serialisation
that drops or mangles a table, which is the failure a byte-count cannot see. It
does NOT prove the QML consuming it renders correctly; only a rendered sample
does that, which is what @SAMPLES and the clipped-plymouth episode are for.

⚑ AND THE GLYPH TABLES ARE COMPARED AGAINST THE SUBSTRATE, not merely against
themselves: each emitted glyph is reported beside segment_topology's own
projection. A registry that round-trips perfectly while disagreeing with the
substrate would be internally consistent and wrong.

WEAKNESS. The font-structure rule (D3) cannot certify a glyph CORRECT — only
that it does not contradict its own font; a letter wrong in the way every other
letter is wrong passes. Rendering and looking remains the only witness for that.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import display_types as DT                                        # noqa: E402
import segment_topology as ST                                     # noqa: E402


def _substrate_source(fmt, ch):
    """The substrate's projection of `ch` at `fmt` (sorted segment ids), or None
    when `ch` is in no substrate table. Lowercase lives in LETTERS22, at 22 only."""
    tables = (ST.DIGITS16, ST.LETTERS16, ST.SYMBOLS16)
    if fmt == "22":
        tables = tables + (ST.LETTERS22,)
    for tbl in tables:
        if ch in tbl:
            g = set(tbl[ch].split()) if tbl[ch] else set()
            return sorted(ST.project(g, fmt)) if g else []
    return None


def measure():
    """The MEASUREMENT policy/display_registry.rego decides (W50). Facts only:
      roundtrip — did as_qml_js() parse, and per registry key: present on each
                  side, and equal after a JSON normalisation;
      cases     — the population: every segGeom stroke (is it in GEOM22?),
                  every segGlyphs format (each glyph's emitted segments beside
                  the substrate's projection, null if in no table), every
                  font5x7 glyph (its column bytes), every display.
    Which of these is a disagreement — including the font's structural
    relations (crossbar row, symmetry, cell fit) — is the policy's ruling."""
    r = DT.registry()
    rt = {"parsed": True, "error": None, "keys": []}
    try:
        got = json.loads(DT.as_qml_js())
    except ValueError as e:
        rt.update(parsed=False, error=str(e))
        got = {}
    for key in sorted(set(r) | set(got)):
        rt["keys"].append({"key": key, "emitted": key in got, "registry": key in r,
                           "equal": key in got and key in r and
                           json.loads(json.dumps(r[key], sort_keys=True)) == got[key]})
    cases = [{"kind": "stroke", "id": sid, "in_substrate": sid in ST.GEOM22}
             for sid in sorted(r["segGeom"])]
    for fmt, table in sorted(r["segGlyphs"].items()):
        cases.append({"kind": "format", "id": fmt, "glyphs": [
            {"ch": ch, "emitted": list(segs), "substrate": _substrate_source(fmt, ch)}
            for ch, segs in sorted(table.items())]})
    cases += [{"kind": "matrix", "id": ch, "cols": list(cols)}
              for ch, cols in sorted(r["font5x7"].items())]
    cases += [{"kind": "display", "id": key} for key in sorted(r["displays"])]
    return {"roundtrip": rt, "cases": cases}


def counts():
    r = DT.registry()
    return {
        "segGeom strokes": len(r["segGeom"]),
        "segGlyph formats": len(r["segGlyphs"]),
        "font5x7 glyphs": len(r["font5x7"]),
        "displays": len(r["displays"]),
    }


def main(argv):
    known = {"--show", "--glyph", "--json", "--selftest"}
    for a in argv[1:]:
        if a.startswith("--") and a not in known:
            print(f"check_display_registry: unknown flag {a!r}", file=sys.stderr)
            return 2

    if "--glyph" in argv:
        # ⚑ THIS MODE EXISTS BECAUSE A RENDERED SAMPLE CAUGHT A BAD GLYPH AND THE
        # SOURCE COULD NOT SETTLE IT.  FONT5x7's comment says
        # 'A' = 0x7e,0x09,0x09,0x09,0x7e and the table one line below holds
        # 0x7e,0x11,0x11,0x11,0x7e — the two disagree about the middle columns.
        # "Which is right" was being answered by squinting at a picture, i.e. in
        # the turn. Printing the bitmap makes it a one-command question.
        rest = [a for a in argv[1:] if not a.startswith("--")]
        if not rest:
            print("check_display_registry: --glyph needs a character",
                  file=sys.stderr)
            return 2
        r = DT.registry()
        font, shown = r["font5x7"], 0
        for ch in rest[0]:
            cols = font.get(ch) or font.get(ch.upper())
            if cols is None:
                print(f"{ch!r}: not in the font ({len(font)} glyphs)")
                continue
            shown += 1
            print(f"{ch!r}  {', '.join(f'0x{c:02x}' for c in cols)}")
            for row in range(7):
                print("  " + "".join("#" if c & (1 << row) else "."
                                     for c in cols))
        print(f"glyph: {shown} of {len(rest[0])} character(s) in the font")
        return 0 if shown else 1

    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0

    if "--show" in argv:
        r = DT.registry()
        for label, v in counts().items():
            print(f"{label}\t{v}")
        for key, d in sorted(r["displays"].items()):
            print(f"  display {key}\tkind={d['kind']}\tcell={d['cell']}")
        return 0

    import opa_gate
    return opa_gate.gate("display_registry")


def _selftest():
    """The measurement can SEE a corrupted emission, a substrate disagreement, and
    the glyph bytes that shipped wrong. Whether each is a DEFECT is policy/
    display_registry.rego's ruling, refused and admitted under `opa test`."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    m0 = measure()
    kinds = {c["kind"] for c in m0["cases"]}
    check("the real registry is measured, every kind present", kinds,
          {"stroke", "format", "matrix", "display"})
    check("the population is the registry's shape",
          len(m0["cases"]), sum(counts().values()))
    check("the real round trip parses and every key is equal",
          m0["roundtrip"]["parsed"] and all(k["equal"] for k in m0["roundtrip"]["keys"]), True)
    r0 = DT.registry()
    check("the 22 table carries the lowercase", "g" in r0["segGlyphs"]["22"], True)
    check("...and no coarser table does", all("g" not in r0["segGlyphs"][f] for f in ("7", "14", "16")), True)
    check("a lowercase at 22 is glyph22's set", r0["segGlyphs"]["22"]["g"], sorted(ST.glyph22("g")))

    # ⚑ THE EXACT BYTES THAT SHIPPED WRONG reach the measurement verbatim, and the
    # round trip stays clean — which is WHY the structural rule (D3) exists.
    saved_font = DT.FONT5x7["A"]
    try:
        DT.FONT5x7["A"] = [0x7e, 0x11, 0x11, 0x11, 0x7e]
        m = measure()
        a = next(c for c in m["cases"] if c["kind"] == "matrix" and c["id"] == "A")
        check("sees the 'A' that shipped (its column bytes)", a["cols"], [0x7e, 0x11, 0x11, 0x11, 0x7e])
        check("...while the round trip stays clean", all(k["equal"] for k in m["roundtrip"]["keys"]), True)
    finally:
        DT.FONT5x7["A"] = saved_font

    # 1. a serialisation that DROPS a table
    saved = DT.as_qml_js
    try:
        DT.as_qml_js = lambda indent=None: json.dumps(
            {k: v for k, v in DT.registry().items() if k != "font5x7"})
        keys = {k["key"]: k for k in measure()["roundtrip"]["keys"]}
        check("sees a dropped table", keys["font5x7"]["emitted"], False)
    finally:
        DT.as_qml_js = saved

    # 2. a serialisation that MANGLES a value
    try:
        def _mangled(indent=None):
            r = DT.registry()
            r["segGeom"] = {k: [0, 0, 0, 0] for k in r["segGeom"]}
            return json.dumps(r)
        DT.as_qml_js = _mangled
        keys = {k["key"]: k for k in measure()["roundtrip"]["keys"]}
        check("sees a mangled table", keys["segGeom"]["equal"], False)
    finally:
        DT.as_qml_js = saved

    # 3. an unparseable emission
    try:
        DT.as_qml_js = lambda indent=None: "{not json"
        check("sees an unparseable emission", measure()["roundtrip"]["parsed"], False)
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

    # ⚑ ⊕MATRIX-FONT-INPUT: the 5x8 display names the 5x8 font, and a font path
    # EXTENDS that table without touching an authored glyph.
    m8 = DT.registry_for("5x8")
    check("a 5x8 subset carries font5x8, not font5x7",
          "font5x8" in m8 and "font5x7" not in m8, True)
    check("the 5x8 display names its font", m8["displays"]["5x8"]["font"], "5x8")
    check("the 5x8 display carries its baseline", m8["displays"]["5x8"].get("baseline"), DT.FONT5x8_BASELINE)
    from check_projection import find_font
    font = find_font()
    if font:
        ext = DT.registry_for("5x8", font_path=font)
        check("a font extends the 5x8 table", len(ext["font5x8"]) > len(m8["font5x8"]), True)
        check("the extension is reported", ext.get("fontExtension", {}).get("glyphs", 0) > 0, True)
        check("authored glyphs win over the font",
              all(ext["font5x8"][ch] == list(DT.FONT5x8[ch]) for ch in DT.FONT5x8), True)
        check("the extension reaches Latin-1 ('é')", "é" in ext["font5x8"], True)
        check("no extension glyph is blank",
              all(any(cb) for ch, cb in ext["font5x8"].items() if ch != " "), True)
    else:
        print("  SKIP the font-extension arms — no TTF on this host")

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

    # 4. a registry that disagrees with the SUBSTRATE while round-tripping fine
    saved_reg = DT.registry
    try:
        def _wrong():
            r = saved_reg()
            fmt = sorted(r["segGlyphs"])[0]
            ch = sorted(r["segGlyphs"][fmt])[0]
            r["segGlyphs"][fmt][ch] = ["zz"]
            return r
        DT.registry = _wrong
        g = next(c for c in measure()["cases"] if c["kind"] == "format")["glyphs"][0]
        check("sees a substrate disagreement (emitted beside the projection)",
              g["emitted"] == ["zz"] and g["substrate"] != ["zz"], True)
    finally:
        DT.registry = saved_reg

    print("check_display_registry selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
