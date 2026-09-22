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

    scripts/check_firefox.py           # exit 0 iff every arm holds for every variant
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

# The arms measured for EVERY variant — one declared dimension of the expected
# population (the other is make_schemes.GRID's roster). web-ext lint is an arm
# whose SKIP (tool absent) counts as measured-and-not-failed, printed as such.
ARMS = ("parses as JSON", "required keys present",
        "every colour is its role or its solved composite",
        "color_scheme matches the variant's polarity",
        "a stable gecko id for AMO signing", "web-ext lint")


def check_manifest(variant, text):
    """[(arm, ok, detail)] for one manifest text."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_firefox as MF
    out = []
    try:
        m = json.loads(text)
    except json.JSONDecodeError as e:
        return [("parses as JSON", False, str(e))]
    out.append(("parses as JSON", True, "ok"))
    colors = m.get("theme", {}).get("colors", {})
    missing = [k for k in MF.REQUIRED if k not in colors]
    out.append(("required keys present", not missing,
                f"missing {missing}" if missing else "frame, tab_background_text"))
    r = MF.roles(variant)
    bad = [f"{k}={colors.get(k)} != {r[role]} ({role})" for k, role in MF.KEYS
           if colors.get(k) != r[role]]
    extra = sorted(set(colors) - {k for k, _ in MF.KEYS})
    out.append(("every colour is its role or its solved composite", not bad and not extra,
                "; ".join(bad[:3]) if bad else (f"unmapped keys {extra}" if extra
                                                else f"{len(MF.KEYS)} of {len(MF.KEYS)} keys")))
    want = "light" if variant.endswith("-Lit") else "dark"
    got = m.get("theme", {}).get("properties", {}).get("color_scheme")
    out.append(("color_scheme matches the variant's polarity", got == want, f"{got} (want {want})"))
    gid = m.get("browser_specific_settings", {}).get("gecko", {}).get("id", "")
    out.append(("a stable gecko id for AMO signing", bool(gid) and variant.lower() in gid, gid or "absent"))
    return out


def lint(folder):
    """web-ext lint over a theme folder; (ok, detail); SKIP when web-ext is absent."""
    exe = shutil.which("web-ext")
    if not exe:
        return True, "SKIP web-ext not installed"
    r = subprocess.run([exe, "lint", "--source-dir", folder, "--output", "json", "--no-input"],
                       capture_output=True, text=True)
    try:
        rep = json.loads(r.stdout)
        errs = rep.get("errors", [])
        return not errs, f"web-ext: {len(errs)} error(s)" + (f": {errs[0].get('message')}" if errs else "")
    except json.JSONDecodeError:
        return r.returncode == 0, f"web-ext rc={r.returncode}"


def measure():
    """([(variant, arm, ok, detail)], [(variant, why)]) over the DECLARED roster.

    ⚑ W65: the population was make_firefox.VARIANTS — the emitter's own typed
    list — so dropping a variant there took "36 of 36" to "30 of 30", rc 0. It is
    now make_schemes.GRID; emitter drift, and any arm a manifest did not reach
    (an unparsable manifest reports ONE arm), are RETURNED as missing."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_firefox as MF
    results, missing = [], list(roster_drift(MF.VARIANTS, "make_firefox"))
    roster = schemes()
    with tempfile.TemporaryDirectory() as td:
        outs = {v: os.path.join(td, v) for v in roster}
        MF.render_all(roster, outs)
        for v in roster:
            text = open(os.path.join(outs[v], "manifest.json"), encoding="utf-8").read()
            arms = check_manifest(v, text)
            arms.append(("web-ext lint",) + lint(outs[v]))
            seen = {a for a, _o, _d in arms}
            missing += [(v, f"arm {a!r} was not measured") for a in ARMS if a not in seen]
            results += [(v, a, o, d) for a, o, d in arms if a in ARMS]
    return results, missing


def main(argv):
    known = {"--map"}
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
    results, missing = measure()
    roster = schemes()
    # ⚑ THE POPULATION IS ASSERTED BEFORE THE OUTCOME (W65): roster x ARMS.
    expected = len(roster) * len(ARMS)
    if missing or len(results) != expected or not results:
        print(f"check_firefox: REFUSED — measured {len(results)} of {expected} declared arm(s) "
              f"({len(roster)} variant(s) x {len(ARMS)} arm(s)). A SHRINKING POPULATION "
              f"IS NOT A PASSING ONE: n of n is green for every n.", file=sys.stderr)
        for v, why in missing:
            print(f"    {v}: {why}", file=sys.stderr)
        return 2
    n = len(results)
    fails = [f"{v} {arm}: {detail}" for v, arm, ok, detail in results if not ok]
    if fails:
        print(f"check_firefox: REFUSED — {len(fails)} of {n} arm(s) do not hold:", file=sys.stderr)
        for f in fails:
            print(f"    {f}", file=sys.stderr)
        return 1
    skip = "" if shutil.which("web-ext") else " (web-ext lint SKIPPED: not installed)"
    print(f"check_firefox: {n} of {expected} arms hold over {len(roster)} themes "
          f"(roster: make_schemes.GRID){skip}")
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
    import make_firefox as MF
    good = json.dumps(MF.manifest("EL-Openglo"))
    arms = {a: o for a, o, _d in check_manifest("EL-Openglo", good)}
    check("the real emission holds every arm", all(arms.values()), True)
    m = json.loads(good)
    del m["theme"]["colors"]["frame"]
    arms = {a: o for a, o, _d in check_manifest("EL-Openglo", json.dumps(m))}
    check("a missing required key is seen", arms["required keys present"], False)
    m = json.loads(good)
    m["theme"]["colors"]["toolbar"] = [1, 2, 3]
    arms = {a: o for a, o, _d in check_manifest("EL-Openglo", json.dumps(m))}
    check("an authored colour is seen", arms["every colour is its role or its solved composite"], False)
    m = json.loads(good)
    m["theme"]["colors"]["accentcolor"] = [1, 2, 3]
    arms = {a: o for a, o, _d in check_manifest("EL-Openglo", json.dumps(m))}
    check("an unmapped key is seen", arms["every colour is its role or its solved composite"], False)
    m = json.loads(good)
    m["theme"]["properties"]["color_scheme"] = "light"
    arms = {a: o for a, o, _d in check_manifest("EL-Openglo", json.dumps(m))}
    check("a wrong colour scheme is seen", arms["color_scheme matches the variant's polarity"], False)
    arms = {a: o for a, o, _d in check_manifest("EL-Openglo", "{not json")}
    check("unparsable JSON is seen", arms["parses as JSON"], False)
    check("hover fill is fainter than active fill (glanced < looked alpha)",
          MF.roles("EL-Openglo")["_alphas"]["hover"] < MF.roles("EL-Openglo")["_alphas"]["active"], True)
    # ⚑ THE LIVENESS CONJUNCT: complete AND not vacuously complete
    results, missing = measure()
    check("the declared population is complete on a clean tree",
          (missing, len(results) == len(schemes()) * len(ARMS)), ([], True))
    check("and it is not vacuously complete", len(results) > 0, True)
    saved = list(MF.VARIANTS)
    try:
        MF.VARIANTS[:] = saved[:-1]
        check("an emitter that drops a GRID variant is REFUSED", main(["x"]), 2)
    finally:
        MF.VARIANTS[:] = saved
    print("check_firefox selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
