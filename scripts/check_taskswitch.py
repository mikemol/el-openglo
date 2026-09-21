#!/usr/bin/env python3
"""check_taskswitch.py — the Alt+Tab switcher packages, MEASURED; policy/taskswitch.rego decides.

⚑ WHAT IS MEASURED.  make_taskswitch emits a KWin/WindowSwitcher package per
variant. KWin loads it by KPackageStructure and by the id the LnF defaults
name in [kwinrc][TabBox] LayoutName; an id mismatch is a stock switcher in
silence, and QML that does not parse is no switcher at all. So, per variant,
this reads: the structure and id the metadata declares; the id the defaults
name; whether the QML root is KWin.TabBoxSwitcher; the three colour holes and
the ghost alpha as filled; qml_sanity's kept diagnostics. The REQUIREMENT —
which of those is a defect — is policy/taskswitch.rego (W50), with its
refuse/admit pairs under opa test.

    scripts/check_taskswitch.py --json    # the measurement
    scripts/check_taskswitch.py --map     # variant -> package id, lit/ghost/ground
    scripts/check_taskswitch.py --selftest

The weakness, stated: this measures the package's SHAPE and lints the QML; it
does not run KWin, so a role KWin renamed would pass here and fail on Alt+Tab.
That is ⊕VER's probe. qmllint absent is a `qmllint: false` fact, not a pass.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)                                                   # templates read by bare name
import make_taskswitch as MT                                     # noqa: E402
import qml_sanity as QS                                          # noqa: E402


def row(v, qml=None):
    """One variant's facts; `qml` overrides the emission (the selftest's synthetic input)."""
    meta = MT.metadata(v)
    qml = MT.main_qml(v) if qml is None else qml
    d = MT.defaults_fragment(v)
    m = re.search(r"LayoutName=(\S+)", d)
    cols = {k: re.search(rf'property color {k}Color:\s*"(#[0-9a-f]{{6}})"', qml)
            for k in ("lit", "ghost", "void")}
    alpha = re.search(r"property real ghostAlpha:\s*([0-9.]+)", qml)
    return {
        "variant": v,
        "structure": meta.get("KPackageStructure"),
        "id": meta["KPlugin"].get("Id"),
        "defaults_id": m.group(1) if m else None,
        "root": "KWin.TabBoxSwitcher {" in qml,
        "colors": {k: (c.group(1) if c else None) for k, c in cols.items()},
        "alpha": float(alpha.group(1)) if alpha else None,
        "lint": list(QS.check_qml(qml, "taskswitch-main.qml")) if QS._qmllint() else [],
    }


def measure():
    return {"qmllint": bool(QS._qmllint()), "variants": [row(v) for v in MT.VARIANTS]}


def main(argv):
    known = {"--map", "--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_taskswitch: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    if "--map" in argv:
        for r in m["variants"]:
            c = r["colors"]
            print(f"{r['variant']:16s}  {r['id']:36s}  lit {c['lit']}  ghost {c['ghost']}  void {c['void']}  alpha {r['alpha']}")
        return 0
    print(f"check_taskswitch: {len(m['variants'])} switcher package(s) measured; the verdict is "
          f"`opa_gate.py taskswitch` (policy/taskswitch.rego)")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    m = measure()
    chk("six variants measured", len(m["variants"]), 6)
    # ⚑ THE MEASUREMENT CAN SEE (W50): a synthetic emission with a doubled brace,
    # no root and an unfilled hole is reported as such — whether that is a
    # defect is policy/taskswitch.rego's ruling
    base = MT.main_qml(MT.VARIANTS[0])
    r = row(MT.VARIANTS[0], base.replace("KWin.TabBoxSwitcher {", "Item {{").replace("property color litColor", "property color xColor"))
    chk("a missing root is a fact", r["root"], False)
    chk("an unfilled hole is a fact", r["colors"]["lit"], None)
    if m["qmllint"]:
        chk("a syntax error is a fact", bool(r["lint"]), True)
    else:
        print("  SKIP qmllint absent — the syntax arm did not run")
    print("check_taskswitch selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
