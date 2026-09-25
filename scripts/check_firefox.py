#!/usr/bin/env python3
"""check_firefox.py — the emitted Firefox theme manifests are loadable and carry the palette.

⚑ THE CLAIM.  For every variant: (1) the manifest parses as JSON with the shape
MDN's `theme` key documents — `theme.colors` present, `frame` and
`tab_background_text` present (Firefox refuses a theme without them);
(2) every colour under theme.colors is the palette role make_firefox.KEYS
names, or the solved composite it names, as an [r, g, b] array; (3)
`properties.color_scheme` is dark for Off variants and light for Lit; (4) the
gecko id is present and stable (AMO signing needs one per theme). Arm (5),
`web-ext lint`, runs when the tool is installed and is a SKIP otherwise.

    scripts/check_firefox.py           # the verdict, as opa_gate firefox decides it
    scripts/check_firefox.py --json    # the measurement policy/firefox.rego decides
    scripts/check_firefox.py --map     # theme key -> palette role
    scripts/check_firefox.py --selftest

WEAKNESS. Firefox is not run here; this proves the manifest, not the render.
Whether Firefox honours every key it documents is Firefox's, and two keys MDN
marks unsupported since 89 are deliberately not emitted.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # sibling checks
from check_selection_contrast import schemes, roster_drift   # noqa: E402  (roster authority)


def facts(variant, text):
    """What one manifest text SAYS — no verdict (policy/firefox.rego rules, W50).

    `parse_error` is the JSON error or null; when it is non-null nothing else
    could be read, and the other fields are null (unmeasured, not clean)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_firefox as MF
    try:
        m = json.loads(text)
    except json.JSONDecodeError as e:
        return {"id": variant, "parse_error": str(e), "missing_required": None,
                "wrong_colours": None, "unmapped_keys": None, "color_scheme": None,
                "want_scheme": "light" if variant.endswith("-Lit") else "dark",
                "gecko_id": None}
    colors = m.get("theme", {}).get("colors", {})
    r = MF.roles(variant)
    return {
        "id": variant,
        "parse_error": None,
        "missing_required": [k for k in MF.REQUIRED if k not in colors],
        "wrong_colours": [{"key": k, "role": role, "got": colors.get(k), "want": r[role]}
                          for k, role in MF.KEYS if colors.get(k) != r[role]],
        "unmapped_keys": sorted(set(colors) - {k for k, _ in MF.KEYS}),
        "color_scheme": m.get("theme", {}).get("properties", {}).get("color_scheme"),
        "want_scheme": "light" if variant.endswith("-Lit") else "dark",
        "gecko_id": m.get("browser_specific_settings", {}).get("gecko", {}).get("id", ""),
    }


def lint(folder):
    """web-ext lint's error messages over a theme folder, or None when web-ext is
    absent (a fact about the machine — withheld, not passed)."""
    exe = shutil.which("web-ext")
    if not exe:
        return None
    r = subprocess.run([exe, "lint", "--source-dir", folder, "--output", "json", "--no-input"],
                       capture_output=True, text=True)
    try:
        return [e.get("message", "") for e in json.loads(r.stdout).get("errors", [])]
    except json.JSONDecodeError:
        return [] if r.returncode == 0 else [f"web-ext rc={r.returncode}, output not JSON"]


def measure():
    """{roster, roster_drift, cases} over the DECLARED roster (make_schemes.GRID).

    ⚑ W65: the population was make_firefox.VARIANTS — the emitter's own typed
    list — so dropping a variant there took "36 of 36" to "30 of 30", rc 0. The
    roster is GRID; the emitter's drift from it is reported for the policy."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_firefox as MF
    roster = schemes()
    cases = []
    with tempfile.TemporaryDirectory() as td:
        outs = {v: os.path.join(td, v) for v in roster}
        MF.render_all(roster, outs)
        for v in roster:
            text = open(os.path.join(outs[v], "manifest.json"), encoding="utf-8").read()
            cases.append(dict(facts(v, text), lint_errors=lint(outs[v])))
    return {"roster": list(roster),
            "roster_drift": [{"variant": v, "why": why}
                             for v, why in roster_drift(MF.VARIANTS, "make_firefox")],
            "cases": cases}


def main(argv):
    known = {"--map", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_firefox: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_firefox as MF
    if "--map" in argv:
        for k, role in MF.KEYS:
            print(f"{k:30} <- {role}")
        return 0
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("firefox")


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
    import make_firefox as MF
    # The MEASUREMENT can see; what is a defect is policy/firefox_test.rego's (W50).
    good = json.dumps(MF.manifest("EL-Openglo"))
    f = facts("EL-Openglo", good)
    check("the real emission measures clean",
          (f["parse_error"], f["missing_required"], f["wrong_colours"], f["unmapped_keys"],
           f["color_scheme"] == f["want_scheme"]), (None, [], [], [], True))
    m = json.loads(good)
    del m["theme"]["colors"]["frame"]
    check("a missing required key is seen",
          "frame" in facts("EL-Openglo", json.dumps(m))["missing_required"], True)
    m = json.loads(good)
    m["theme"]["colors"]["toolbar"] = [1, 2, 3]
    check("an authored colour is seen",
          [w["key"] for w in facts("EL-Openglo", json.dumps(m))["wrong_colours"]], ["toolbar"])
    m = json.loads(good)
    m["theme"]["colors"]["accentcolor"] = [1, 2, 3]
    check("an unmapped key is seen", facts("EL-Openglo", json.dumps(m))["unmapped_keys"], ["accentcolor"])
    m = json.loads(good)
    m["theme"]["properties"]["color_scheme"] = "light"
    check("a wrong colour scheme is seen", facts("EL-Openglo", json.dumps(m))["color_scheme"], "light")
    bad = facts("EL-Openglo", "{not json")
    check("unparsable JSON is seen, and nothing else is claimed",
          (bad["parse_error"] is not None, bad["missing_required"]), (True, None))
    check("hover fill is fainter than active fill (glanced < looked alpha)",
          MF.roles("EL-Openglo")["_alphas"]["hover"] < MF.roles("EL-Openglo")["_alphas"]["active"], True)
    # ⚑ THE LIVENESS CONJUNCT: every declared variant measured, and not vacuously
    got = measure()
    check("every declared variant is measured",
          sorted(c["id"] for c in got["cases"]), sorted(got["roster"]))
    check("and it is not vacuously complete", len(got["cases"]) > 0, True)
    saved = list(MF.VARIANTS)
    try:
        MF.VARIANTS[:] = saved[:-1]
        check("an emitter that drops a GRID variant is reported as drift",
              len(measure()["roster_drift"]) > 0, True)
    finally:
        MF.VARIANTS[:] = saved
    print("check_firefox selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
