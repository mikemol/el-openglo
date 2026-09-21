#!/usr/bin/env python3
"""check_union.py — the emitted Union styles override only what Breeze defines, with solved values.

⚑ THE CLAIM.  For every variant, make_union emits a style that imports Breeze and
overrides a set of :root variables. Three things must hold, and each can fail:
(1) the CSS parses (tinycss2); (2) every variable the override sets EXISTS in
Breeze's own variables.css on this host — an override of a name Breeze does not
read is a silent no-op; (3) every alpha in the override is the number
make_union.alphas() solves for that variant, at or above its floor — not an
authored one.

    scripts/check_union.py            # exit 0 iff all three hold for every variant
    scripts/check_union.py --map      # per variant: variable -> solved alpha (Breeze's beside it)
    scripts/check_union.py --selftest

SKIPS, counted and printed: tinycss2 absent (the tooling extra); Breeze's
variables.css absent (Union not installed here — then arm 2 cannot be measured
and says so, it does not pass).

WEAKNESS. This proves the emitted text, not the engine's reading of it. Whether
Union's cascade applies a later :root, and whether it resolves var() lazily,
needs the engine (USE=tools ruleinspector, or the desktop) — a SKIP here, an
⊕VER there.
"""
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


def check_variant(variant, css_text, breeze):
    """[(arm, ok, detail)] for one variant's overrides.css."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_union as MU
    out = []
    try:
        import tinycss2
        rules = tinycss2.parse_stylesheet(css_text, skip_comments=True, skip_whitespace=True)
        errs = [r for r in rules if r.type == "error"]
        # tinycss2 is lenient at the top level; the declarations are where a
        # broken emission shows (a missing colon, a bare token)
        for r in rules:
            if r.type == "qualified-rule":
                errs += [d for d in tinycss2.parse_declaration_list(
                    r.content, skip_comments=True, skip_whitespace=True) if d.type == "error"]
        out.append(("parses", not errs, f"{len(errs)} parse error(s)" if errs else "tinycss2 ok"))
    except ImportError:
        out.append(("parses", True, "SKIP tinycss2 not installed"))
    ov = overridden(css_text)
    if breeze is None:
        out.append(("overrides exist in Breeze", False, "SKIP-AS-FAIL: Breeze variables.css absent — unmeasured"))
    else:
        unknown = sorted(set(ov) - breeze)
        out.append(("overrides exist in Breeze", not unknown,
                    f"unknown: {unknown}" if unknown else f"{len(ov)} of {len(ov)} names are Breeze's"))
    solved = MU.alphas(variant)
    bad = []
    for var, (a, _fg, _gnd, _floor, _breeze) in solved.items():
        if a is None:
            continue
        if var not in ov:
            bad.append(f"{var} missing")
            continue
        nums = _numbers(ov[var])
        if a not in nums:
            bad.append(f"{var}: emitted {nums} != solved {a}")
    out.append(("values are the solved alphas", not bad,
                "; ".join(bad) if bad else f"{len(solved)} of {len(solved)} variables carry their solve"))
    return out


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_union: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_union as MU
    if "--map" in argv:
        for v in MU.VARIANTS:
            print(v)
            for var, (a, fg, gnd, floor, breeze) in MU.alphas(v).items():
                print(f"  {var:26} {a!s:>6}  Breeze {breeze}  ({fg} over {gnd}, Lc>={floor})")
        return 0
    breeze = breeze_variables()
    fails, total = [], 0
    for v in MU.VARIANTS:
        for arm, ok, detail in check_variant(v, MU.overrides_css(v), breeze):
            total += 1
            if not ok:
                fails.append(f"{v} {arm}: {detail}")
    if not total:
        print("check_union: REFUSED — no variants; nothing measured", file=sys.stderr)
        return 2
    if fails:
        print(f"check_union: REFUSED — {len(fails)} of {total} arm(s) do not hold:", file=sys.stderr)
        for f in fails:
            print(f"    {f}", file=sys.stderr)
        return 1
    print(f"check_union: {total} of {total} arms hold over {len(MU.VARIANTS)} styles"
          + ("" if breeze else " (Breeze absent: override-existence unmeasured)"))
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

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_union as MU
    breeze = {"--indicator-color", "--focus-outline-alpha", "--focus-color",
              "--highlight-hover-color", "--card-hover-color"}
    good = MU.overrides_css("EL-Openglo")
    arms = {a: ok_ for a, ok_, _d in check_variant("EL-Openglo", good, breeze)}
    check("the real emission holds every arm", all(arms.values()), True)
    # ⚑ EACH ARM MUST BE ABLE TO FAIL.
    unknown = good.replace("--indicator-color", "--indicator-colour")
    arms = {a: ok_ for a, ok_, _d in check_variant("EL-Openglo", unknown, breeze)}
    check("an override Breeze does not define is seen", arms["overrides exist in Breeze"], False)
    authored = re.sub(r"set-alpha 0\.\d+\)", "set-alpha 0.4)", good, count=1)
    arms = {a: ok_ for a, ok_, _d in check_variant("EL-Openglo", authored, breeze)}
    check("an authored alpha in place of the solved one is seen", arms["values are the solved alphas"], False)
    arms = {a: ok_ for a, ok_, _d in check_variant("EL-Openglo", good, None)}
    check("an absent Breeze is not a pass", arms["overrides exist in Breeze"], False)
    try:
        import tinycss2  # noqa: F401
        arms = {a: ok_ for a, ok_, _d in check_variant("EL-Openglo", ":root { indicator red; --focus-outline-alpha 0.3 }", breeze)}
        check("a malformed stylesheet is seen", arms["parses"], False)
    except ImportError:
        print("  SKIP parse arm — tinycss2 not installed")
    check("every solved alpha is at or above 0 and at most 1",
          all(0 <= a <= 1 for v in MU.VARIANTS for a, *_ in MU.alphas(v).values() if a is not None), True)
    print("check_union selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
