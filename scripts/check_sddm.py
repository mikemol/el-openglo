#!/usr/bin/env python3
"""check_sddm.py — the SDDM greeter (W66) DRAWS and ACCEPTS INPUT, headless.

⚑ A GREETER IS AN AUTH SURFACE: one that renders but cannot be typed into is a
login screen nobody can pass. So this measures, per variant, under
scripts/render_qml.py's `sddm` surface (stubbed sddm / userModel / sessionModel):
  · lit pixels on the grab (the clock mount drew)
  · the password field exists, echoes as Password, holds active focus at start
  · clicking the login button calls sddm.login(user, password, session) with the
    typed password, the userModel's lastIndex user and the sessionModel's lastIndex
  · loginFailed makes a failure message visible and re-focuses the field
  · Enter in the field (accepted) calls sddm.login again
The requirement is policy/sddm.rego; this prints only the measurement (--json).

    scripts/check_sddm.py --json        # the measurement
    scripts/opa_gate.py sddm            # the verdict
    scripts/check_sddm.py --selftest    # the measurement can see

⚑ WEAKNESS, STATED: the stubs are this repo's reading of breeze's use of SDDM's
objects, not SDDM itself; a real greeter whose objects differ (a userModel with
another role name) passes here and fails live. `sddm-greeter-qt6 --test-mode
--theme <dir>` is the live arm and needs a display. A missing qml runner is a
`withheld` fact, per variant.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def probe_line(stderr):
    """The harness's `SDDM-PROBE {json}` as a dict, or None."""
    for line in stderr.splitlines():
        i = line.find("SDDM-PROBE ")
        if i >= 0:
            return json.loads(line[i + len("SDDM-PROBE "):])
    return None


def measure_variant(variant, w=800, h=450):
    import render_qml as RQ
    if not os.path.exists(RQ.QML):
        return {"id": variant, "withheld": f"{RQ.QML} is not installed"}
    with tempfile.TemporaryDirectory() as td:
        png = os.path.join(td, "sddm.png")
        rc, err = RQ.render("sddm", variant, w, h, png)
        probe = probe_line(err)
        lit = RQ.pixels(png, variant)["lit"] if os.path.exists(png) else 0
    return {"id": variant, "rc": rc, "lit_px": lit, "probe": probe,
            "stderr_tail": None if probe else err[-400:]}


def measure(variants=None):
    import variant_roster                   # the declared roster (W61 B2), not make_sddm's own
    vs = list(variants or variant_roster.ids())
    return {"cases": [measure_variant(v) for v in vs],
            "expected": {"user": "bob", "session": 1, "password": "hunter2"}}


def main(argv):
    known = {"--json", "--selftest", "--variant"}
    args = argv[1:]
    for a in args:
        if a.startswith("--") and a not in known:
            print(f"check_sddm: unknown flag {a!r}", file=sys.stderr)
            return 2
    vs = [args[args.index("--variant") + 1]] if "--variant" in args else None
    doc = measure(vs)
    if "--json" in args:
        print(json.dumps(doc, indent=1))
        return 0
    for c in doc["cases"]:
        print(json.dumps(c))
    print("check_sddm: measured %d case(s); the verdict is scripts/opa_gate.py sddm" % len(doc["cases"]))
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want
    chk("the probe line is read", probe_line('x\nqml: SDDM-PROBE {"a": 1}\n'), {"a": 1})
    chk("no probe line is None, not {}", probe_line("qml: nothing"), None)
    m = measure(["EL-Openglo"])["cases"][0]
    if "withheld" in m:
        print(f"  SKIP render arm — {m['withheld']}")
    else:
        chk("the harness drove the form (a probe came back)", m["probe"] is not None, True)
        chk("the render has lit pixels", m["lit_px"] > 0, True)
    print("check_sddm selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
