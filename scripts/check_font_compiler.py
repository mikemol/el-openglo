#!/usr/bin/env python3
"""check_font_compiler.py — does the compiled font reproduce the authored segment tables?

MEASUREMENT ONLY (the requirement is policy/font_compiler.rego; opa_gate joins them).
For the bundled font (check_projection.find_font — Liberation Mono here) it
compiles the segment table through font_compiler (the skeleton map-matcher,
segment-only since the operator dropped the dot-matrix half, 2026-09-23) and
emits, per non-blank authored glyph:

  22 : the compiled 22-seg set vs the registry's segGlyphs["22"]
   7 : segment_topology.project(compiled, "7") vs segGlyphs["7"]

and, per glyph, whether font_compiler.DECLARED names it a display convention
(class + reason). The policy judges; this only reports. A glyph declared AND
reproduced at 22 is reported too — the policy calls that an outgrown declaration.

    scripts/check_font_compiler.py                   # the verdict, as opa_gate decides it
    scripts/check_font_compiler.py --json [FIXTURE]  # the measurement (FIXTURE: a planted table)
    scripts/check_font_compiler.py --table           # human: n of m per format, every declaration
    scripts/check_font_compiler.py --selftest        # the measurement can SEE a wrong segment

FIXTURE is a JSON file {"22": {ch: [segment ids]}} whose entries REPLACE the
compiled ones — the negative witness: catalog/fixtures/font_compiler/wrong-8.json
drops one segment from '8', and `opa_gate.py font_compiler <it> --expect
denied:F4` must hold.

⚑ WEAKNESS.  The only font measured is the one find_font resolves on THIS host.
The declarations are DATA a reader can audit, not a proof: the policy can refuse
an undeclared, unreasoned, unknown-class or outgrown declaration, but it cannot
tell a true display convention from a compiler defect wearing one's name — the
reasons are what a reviewer reads. A missing font is `withheld`.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, ROOT)
from check_projection import find_font   # noqa: E402  one font finder, not two

FORMATS = ("22", "7")


def measure(font, compiled=None):
    """The measurement document. `compiled` overrides the compiler's 22-seg
    glyph table (the selftest's and a FIXTURE's way of planting a wrong glyph)."""
    import display_types as DT
    import font_compiler as FC
    import glyph_match as GM
    import segment_topology as ST
    if not font:
        return {"font": None, "withheld": "no TTF found on this host (pass one to find_font)",
                "cases": [], "declarations": []}
    doc = FC.compile_font(font)
    seg = dict(doc["segment"]["22"]["glyphs"])
    seg.update(compiled or {})
    reg = DT.registry()["segGlyphs"]
    cases = []
    for fmt in FORMATS:
        for ch, auth in sorted(reg[fmt].items()):
            if not auth:
                continue                      # a known blank has nothing to agree with
            raw = seg.get(ch)
            got = None if raw is None else sorted(ST.project(set(raw), fmt))
            cls, why = FC.DECLARED.get(ch, (None, None))
            cases.append({"fmt": fmt, "ch": ch, "authored": list(auth), "compiled": got,
                          "agree": got == list(auth), "declared": ch in FC.DECLARED,
                          "class": cls, "reason": why})
    agree22 = {c["ch"]: c["agree"] for c in cases if c["fmt"] == "22"}
    decls = [{"ch": ch, "class": cls, "reason": why, "authored": ch in agree22,
              "agree22": agree22.get(ch, False)} for ch, (cls, why) in sorted(FC.DECLARED.items())]
    return {"font": os.path.basename(font), "withheld": None,
            "font_sha256": FC.font_sha256(font), "font_sha256_in_doc": doc["font"]["sha256"],
            "method": doc["segment"]["22"]["method"], "classes": list(FC.DECLARED_CLASSES),
            "known_convention": sorted(GM.KNOWN_CONVENTION),
            "cases": cases, "declarations": decls}


def _fixture(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)["22"]


def _table(doc):
    if doc.get("withheld"):
        print(f"check_font_compiler: SKIP — {doc['withheld']}", file=sys.stderr)
        return 0
    print(f"font {doc['font']}  sha256 {doc['font_sha256'][:16]}  method {doc['method'][:16]}")
    for fmt in FORMATS:
        cs = [c for c in doc["cases"] if c["fmt"] == fmt]
        ok = sum(c["agree"] for c in cs)
        dec = [c["ch"] for c in cs if not c["agree"] and c["declared"]]
        bad = [c["ch"] for c in cs if not c["agree"] and not c["declared"]]
        print(f"  {fmt:>2}-seg: {ok} of {len(cs)} authored glyphs reproduced; "
              f"{len(dec)} of {len(cs)} declared convention {''.join(dec)!r}; "
              f"{len(bad)} of {len(cs)} undeclared {''.join(bad)!r}")
    for d in doc["declarations"]:
        print(f"  declared {d['ch']!r:5s} {d['class']:13s} {'OUTGROWN ' if d['agree22'] else ''}{d['reason']}")
    seeds = doc["known_convention"]
    outgrown = [ch for ch in seeds if ch not in {d["ch"] for d in doc["declarations"]}]
    print(f"  glyph_match.KNOWN_CONVENTION: {len(seeds) - len(outgrown)} of {len(seeds)} declared; "
          f"reproduced by the compiler, so not declared: {''.join(outgrown)!r}")
    return 0


def main(argv):
    known = {"--json", "--table"}
    flags = [a for a in argv[1:] if a.startswith("--")]
    for a in flags:
        if a not in known:
            print(f"check_font_compiler: unknown flag {a!r}", file=sys.stderr)
            return 2
    ops = [a for a in argv[1:] if not a.startswith("--")]
    if "--json" in flags:
        planted = _fixture(ops[0]) if ops else None
        print(json.dumps(measure(find_font(), planted), sort_keys=True))
        return 0
    if "--table" in flags:
        return _table(measure(find_font()))
    import opa_gate
    return opa_gate.gate("font_compiler")


def _selftest():
    """The measurement can SEE: a planted wrong segment is a disagreement, the
    authored set planted back is an agreement, and a missing font is withheld."""
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    chk("no font is withheld, with an empty population", measure(None)["cases"], [])
    font = find_font()
    if not font:
        print("  SKIP — no TTF on this host")
        print("check_font_compiler selftest: SKIP")
        return ok
    import segment_topology as ST
    auth8 = sorted(ST.glyph16("8"))
    by = lambda d: {(c["fmt"], c["ch"]): c for c in d["cases"]}  # noqa: E731
    good = by(measure(font, {"8": auth8}))
    chk("an '8' equal to the authored set is seen as reproduced at 22", good[("22", "8")]["agree"], True)
    chk("... and at 7", good[("7", "8")]["agree"], True)
    wrong = by(measure(font, {"8": [s for s in auth8 if s != "g2"]}))
    chk("an '8' missing g2 is SEEN as a disagreement at 22", wrong[("22", "8")]["agree"], False)
    chk("... and NOT at 7 (g1 still lights the coarse g: the projection is honest)",
        wrong[("7", "8")]["agree"], True)
    wrong7 = by(measure(font, {"8": [s for s in auth8 if s not in ("g1", "g2")]}))
    chk("an '8' missing its whole middle bar is SEEN at 7", wrong7[("7", "8")]["agree"], False)
    chk("'8' is not declared (a disagreement there is undeclared)", wrong[("22", "8")]["declared"], False)
    print("check_font_compiler selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
