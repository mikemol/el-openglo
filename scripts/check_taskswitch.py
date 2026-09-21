#!/usr/bin/env python3
"""check_taskswitch.py — the Alt+Tab switcher package, MEASURED; policy/taskswitch.rego decides.

⚑ WHAT IS MEASURED.  make_taskswitch emits ONE KWin/WindowSwitcher package
(⊕ONE-THEME, W35). KWin loads it by KPackageStructure and by the id the LnF
defaults name in [kwinrc][TabBox] LayoutName; an id mismatch is a stock
switcher in silence, and QML that does not parse is no switcher at all. So
this reads: the structure and id the metadata declares; the id the defaults
name; whether the QML root is KWin.TabBoxSwitcher; which Kirigami.Theme ROLE
each colour is BOUND to and under which colorSet (the variant is the active
scheme, so a colour that is a baked hex here is a defect: it would not follow
the scheme); the ghost alpha as baked; qml_sanity's kept diagnostics. The
REQUIREMENT is policy/taskswitch.rego (W50), with its refuse/admit pairs
under opa test.

    scripts/check_taskswitch.py --json    # the measurement
    scripts/check_taskswitch.py --map     # the package id and the bindings
    scripts/check_taskswitch.py --selftest

The weakness, stated: this measures the package's SHAPE, the bindings' TEXT
and lints the QML; it does not run KWin and cannot see Kirigami.Theme resolve
against a scheme — whether the bound switcher FOLLOWS plasma-apply-colorscheme
without reinstall is ⊕VER's probe. qmllint absent is a `qmllint: false` fact.
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

# the hole -> the role it must be bound to (catalog/one-theme.md)
ROLES = {"lit": "textColor", "ghost": "disabledTextColor", "void": "backgroundColor"}


def bindings(qml):
    """{hole: bound role or baked literal or None} + the colorSet, from the emitted text."""
    out = {}
    for k in ROLES:
        m = re.search(rf'(?m)^\s*property color {k}Color:\s*(\S+)', qml)
        out[k] = m.group(1).strip('"') if m else None
    cs = re.search(r"(?m)^\s*Kirigami\.Theme\.colorSet:\s*Kirigami\.Theme\.(\w+)", qml)
    return out, (cs.group(1) if cs else None)


def measure(qml=None):
    """The package's facts; `qml` overrides the emission (the selftest's synthetic input)."""
    meta = MT.metadata()
    qml = MT.main_qml() if qml is None else qml
    m = re.search(r"LayoutName=(\S+)", MT.defaults_fragment())
    alpha = re.search(r"property real ghostAlpha:\s*([0-9.]+)", qml)
    b, cs = bindings(qml)
    return {
        "qmllint": bool(QS._qmllint()),
        "structure": meta.get("KPackageStructure"),
        "id": meta["KPlugin"].get("Id"),
        "defaults_id": m.group(1) if m else None,
        "root": "KWin.TabBoxSwitcher {" in qml,
        "bindings": b,
        "colorSet": cs,
        "roles": ROLES,
        "alpha": float(alpha.group(1)) if alpha else None,
        "lint": list(QS.check_qml(qml, "taskswitch-main.qml")) if QS._qmllint() else [],
    }


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
        print(f"{m['id']}  colorSet {m['colorSet']}  " + "  ".join(f"{k} -> {v}" for k, v in m["bindings"].items())
              + f"  alpha {m['alpha']}")
        return 0
    print("check_taskswitch: one switcher package measured; the verdict is "
          "`opa_gate.py taskswitch` (policy/taskswitch.rego)")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    m = measure()
    chk("the bindings are read", m["bindings"], {"lit": "Kirigami.Theme.textColor", "ghost": "Kirigami.Theme.disabledTextColor",
                                                 "void": "Kirigami.Theme.backgroundColor"})
    chk("the colorSet is read", m["colorSet"], "View")
    # ⚑ THE MEASUREMENT CAN SEE (W50): a synthetic emission with a doubled brace, no
    # root, a BAKED hex where a binding belongs and no colorSet is reported as such —
    # whether that is a defect is policy/taskswitch.rego's ruling
    base = MT.main_qml()
    r = measure(base.replace("KWin.TabBoxSwitcher {", "Item {{")
                .replace("property color litColor: Kirigami.Theme.textColor", 'property color litColor: "#99ffeb"')
                .replace("Kirigami.Theme.colorSet: Kirigami.Theme.View", ""))
    chk("a missing root is a fact", r["root"], False)
    chk("a baked hex is a fact", r["bindings"]["lit"], "#99ffeb")
    chk("a missing colorSet is a fact", r["colorSet"], None)
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
