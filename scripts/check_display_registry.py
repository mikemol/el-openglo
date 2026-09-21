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


def font_structure():
    """[problem] — glyphs whose STRUCTURE contradicts the font they belong to.

    ⚑ A WRONG GLYPH ROUND-TRIPS PERFECTLY.  The emission check compares Python to
    Python, so a malformed letter survives it untouched; the collision count stays
    0 because a malformed 'A' still differs from every other letter. 'A' shipped
    with its crossbar one row low and a flat apex, and the only thing that caught
    it was rendering the marquee and LOOKING.

    So this asks what a picture asks: does each glyph agree with the others about
    where the shared features of this font sit? These are NOT general typographic
    truths — they are relations WITHIN this 5x7 set, checkable because the set is
    internally consistent everywhere except where it is wrong.

    ⚑ THE WEAKNESS, STATED.  This cannot certify a glyph is CORRECT — only that it
    does not contradict its own font. A letter wrong in a way every other letter
    is also wrong passes. Rendering and looking remains the only witness for that,
    which is why catalog/library/samples/marquee.svg exists and is committed."""
    r = DT.registry()
    font = r["font5x7"]
    bad = []

    def rows_of(ch):
        cols = font.get(ch)
        if cols is None:
            return None
        return [{c for c, b in enumerate(cols) if b & (1 << row)} for row in range(7)]

    # 1. every glyph must fit the declared cell — a column byte above 0x7f would
    #    light a row that does not exist.
    for ch, cols in sorted(font.items()):
        if len(cols) != 5:
            bad.append(f"{ch!r}: {len(cols)} columns, not 5")
        for i, b in enumerate(cols):
            if b & ~0x7f:
                bad.append(f"{ch!r} column {i} = 0x{b:02x} lights a row past 7")

    # 2. THE CROSSBAR FAMILY.  A, H and E all carry a full-width or near-full
    #    horizontal bar, and in a 7-row cell it belongs on the middle row (3).
    #    'A' had it on row 4 while 'H' and 'E' had it on 3 — the disagreement that
    #    was visible in the render and in nothing else.
    for ch in ("A", "H"):
        rows = rows_of(ch)
        if rows is None:
            bad.append(f"{ch!r}: absent from the font")
            continue
        full = [i for i, on in enumerate(rows) if len(on) == 5]
        if full != [3]:
            bad.append(f"{ch!r}: full-width row(s) at {full}, expected [3] — the "
                       f"crossbar disagrees with the rest of the font")

    # 3. 'E' bars the top, middle and bottom; its middle bar shares row 3.
    rows = rows_of("E")
    if rows is not None:
        barred = [i for i, on in enumerate(rows) if len(on) >= 4]
        if barred != [0, 3, 6]:
            bad.append(f"'E': barred rows {barred}, expected [0, 3, 6]")

    # 4. symmetric letters must be left-right symmetric in their columns.
    #
    # ⚑ '0' IS DELIBERATELY EXCLUDED, AND I HAD IT WRONG FIRST.  I listed it as
    # symmetric and the check fired on the real font — but this '0' carries the
    # slashed/dotted diagonal that distinguishes it from 'O' (0x3e,0x51,0x49,
    # 0x45,0x3e: the lit bits walk from bottom-left to top-right), so its
    # asymmetry is the FEATURE. My instrument was wrong about the world before the
    # artifact was, which is the recurring family ⊕DOT-WIRE's residue names.
    for ch in ("A", "H", "O", "T", "U", "V", "W", "X", "M"):
        cols = font.get(ch)
        if cols and list(cols) != list(reversed(cols)):
            bad.append(f"{ch!r} is not left-right symmetric: "
                       f"{[hex(c) for c in cols]}")

    # 5. no glyph but ' ' may be blank — a silently empty cell is how a missing
    #    glyph looks on the panel.
    for ch, cols in sorted(font.items()):
        if ch != " " and not any(cols):
            bad.append(f"{ch!r}: every column is empty")
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
    known = {"--show", "--glyph", "--selftest"}
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
    bad += font_structure()
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
    check("the font is structurally consistent", font_structure(), [])

    # ⚑ THE EXACT BYTES THAT SHIPPED WRONG.  'A' held 0x7e,0x11,0x11,0x11,0x7e —
    # crossbar on row 4, flat apex — and every check was green because the
    # emission round-tripped and the collision count was unaffected. If this
    # regression case does not fail, the structural check is decoration.
    saved_font = DT.FONT5x7["A"]
    try:
        DT.FONT5x7["A"] = [0x7e, 0x11, 0x11, 0x11, 0x7e]
        probs = font_structure()
        check("sees the 'A' that shipped (crossbar one row low)",
              any("'A'" in p and "crossbar" in p for p in probs), True)
        # and it must still round-trip cleanly, which is WHY looking was needed
        check("...while the round trip stays clean", roundtrip()[0], True)
    finally:
        DT.FONT5x7["A"] = saved_font

    # an asymmetric 'H' is a different failure the same check must catch
    saved_h = DT.FONT5x7["H"]
    try:
        DT.FONT5x7["H"] = [0x7f, 0x08, 0x08, 0x08, 0x3f]
        check("sees an asymmetric symmetric letter",
              any("'H'" in p and "symmetric" in p for p in font_structure()), True)
    finally:
        DT.FONT5x7["H"] = saved_h

    # a column byte that lights a row outside the cell
    saved_z = DT.FONT5x7["Z"]
    try:
        DT.FONT5x7["Z"] = [0xff, 0x51, 0x49, 0x45, 0x43]
        check("sees a column past the cell",
              any("'Z'" in p and "past" in p for p in font_structure()), True)
    finally:
        DT.FONT5x7["Z"] = saved_z

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

    # ⚑ ⊕MATRIX-FONT-INPUT: the 5x8 display names the 5x8 font, and a font path
    # EXTENDS that table without touching an authored glyph.
    m8 = DT.registry_for("5x8")
    check("a 5x8 subset carries font5x8, not font5x7",
          "font5x8" in m8 and "font5x7" not in m8, True)
    check("the 5x8 display names its font", m8["displays"]["5x8"]["font"], "5x8")
    check("the 5x8 display carries its baseline", m8["displays"]["5x8"].get("baseline"), DT.FONT5x8_BASELINE)
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
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
