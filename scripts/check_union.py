#!/usr/bin/env python3
"""check_union.py — the emitted Union styles override only what Breeze defines, with solved values.

⚑ THE CLAIM.  For every variant, make_union emits a style that imports Breeze and
overrides a set of :root variables. Three things must hold, and each can fail:
(1) the CSS parses (tinycss2); (2) every variable the override sets EXISTS in
Breeze's own variables.css on this host — an override of a name Breeze does not
read is a silent no-op; (3) every alpha in the override is the number
make_union.alphas() solves for that variant — not an authored one.

    scripts/check_union.py            # the verdict, as opa_gate union decides it
    scripts/check_union.py --json     # the measurement policy/union.rego decides
    scripts/check_union.py --map      # per variant: variable -> solved alpha (Breeze's beside it)
    scripts/check_union.py --selftest # the measurement can SEE each defect

The three requirements are policy/union.rego's ruling (W50); this file reports,
per variant, the parse-error count, each overridden name with the numbers in its
value, and each solved alpha — and, once, the names Breeze defines here.

WITHHELD, not failed: tinycss2 absent (the tooling extra; parse_errors is null);
Breeze's variables.css absent (Union not installed here; breeze is null). Each is
a fact about the machine. ⚑ BEFORE W50 an absent Breeze DENIED ("SKIP-AS-FAIL");
the policy withholds it — unmeasured is not failed, and it is not passed either:
beside the admitted parse and solve arms it is a counted, printed SKIP.

WEAKNESS. This proves the emitted text, not the engine's reading of it. Whether
Union's cascade applies a later :root, and whether it resolves var() lazily,
needs the engine (USE=tools ruleinspector, or the desktop) — a SKIP here, an
⊕VER there.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BREEZE_VARS = "/usr/share/union/css/styles/breeze/variables.css"


def breeze_variables(path=BREEZE_VARS):
    """The set of --names Breeze's variables.css defines, or None if absent."""
    if not os.path.isfile(path):
        return None
    return set(re.findall(r"^\s*(--[a-z0-9-]+)\s*:", open(path, encoding="utf-8").read(), re.M))


def overridden(css_text):
    """{--name: declaration value} from the emitted overrides.css."""
    out = {}
    for m in re.finditer(r"^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);", css_text, re.M):
        out[m.group(1)] = m.group(2).strip()
    return out


def _numbers(value):
    return [float(x) for x in re.findall(r"(?<![\w.])(\d?\.\d+|\d+\.\d*|\d+)(?![\w.])", value)]


def parse_errors(css_text):
    """tinycss2's error count over the sheet and its declarations, or None if absent."""
    try:
        import tinycss2
    except ImportError:
        return None
    rules = tinycss2.parse_stylesheet(css_text, skip_comments=True, skip_whitespace=True)
    errs = [r for r in rules if r.type == "error"]
    # tinycss2 is lenient at the top level; the declarations are where a
    # broken emission shows (a missing colon, a bare token)
    for r in rules:
        if r.type == "qualified-rule":
            errs += [d for d in tinycss2.parse_declaration_list(
                r.content, skip_comments=True, skip_whitespace=True) if d.type == "error"]
    return len(errs)


def facts(variant, css_text):
    """One variant's facts: parse errors, the overrides (name + numbers), the solve."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_union as MU
    return {"id": variant, "parse_errors": parse_errors(css_text),
            "overrides": [{"name": k, "numbers": _numbers(v)}
                          for k, v in sorted(overridden(css_text).items())],
            "solved": [{"var": var, "alpha": a}
                       for var, (a, _fg, _gnd, _floor, _breeze) in MU.alphas(variant).items()]}


def measure(breeze_path=BREEZE_VARS):
    """The MEASUREMENT policy/union.rego decides, over the DECLARED roster (W61 R1:
    never MU.VARIANTS, which is emitted as `roster_drift`)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_union as MU
    import variant_roster as VR
    roster = VR.ids()
    breeze = breeze_variables(breeze_path)
    return {"roster": roster, "breeze": sorted(breeze) if breeze is not None else None,
            "roster_drift": VR.drift_facts({"make_union": MU.VARIANTS}, roster),
            "cases": [facts(v, MU.overrides_css(v)) for v in roster]}


def main(argv):
    known = {"--map", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_union: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--map" in argv:
        import make_union as MU
        import variant_roster as VR
        for v in VR.ids():
            print(v)
            for var, (a, fg, gnd, floor, breeze) in MU.alphas(v).items():
                print(f"  {var:26} {a!s:>6}  Breeze {breeze}  ({fg} over {gnd}, Lc>={floor})")
        return 0
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import opa_gate
    return opa_gate.gate("union")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_union as MU
    good = MU.overrides_css("EL-Openglo")
    f = facts("EL-Openglo", good)
    check("the real emission's overrides are read", len(f["overrides"]) > 0, True)
    check("and its solve", any(s["alpha"] is not None for s in f["solved"]), True)
    # ⚑ EACH DEFECT MUST BE MEASURED (that it is DENIED is policy/union_test.rego's ruling).
    unknown = facts("EL-Openglo", good.replace("--indicator-color", "--indicator-colour"))
    check("an override under a name Breeze does not define is measured",
          "--indicator-colour" in {o["name"] for o in unknown["overrides"]}, True)
    authored = re.sub(r"set-alpha 0\.\d+\)", "set-alpha 0.4)", good, count=1)
    check("an authored alpha is measured",
          any(0.4 in o["numbers"] for o in facts("EL-Openglo", authored)["overrides"]), True)
    n = parse_errors(":root { indicator red; --focus-outline-alpha 0.3 }")
    if n is None:
        print("  SKIP parse arm — tinycss2 not installed")
    else:
        check("a malformed stylesheet is measured", n > 0, True)
        check("...and the real one is not", f["parse_errors"], 0)
    check("an absent Breeze is measured as null, not as empty",
          measure("/nonexistent/variables.css")["breeze"], None)
    m = measure()
    check("every declared variant is measured", [c["id"] for c in m["cases"]], m["roster"])
    check("and the population is not empty", len(m["cases"]) > 0, True)
    kept = MU.VARIANTS
    try:
        MU.VARIANTS = [x for x in kept if x != "EL-Amber"]     # a planted drop
        check("an emitter that drops a variant is measured as drift",
              [d["variant"] for d in measure()["roster_drift"]], ["EL-Amber"])
    finally:
        MU.VARIANTS = kept
    print("check_union selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
