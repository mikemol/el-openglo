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


def resolution(qml):
    """{variant: {'resolved': {lit, ghost, void}, 'expected': {lit, ghost, void}}} — the emitted
    binding lines RUN under each variant's scheme by the real Kirigami.Theme (theme_probe),
    beside the tokens the palette solved for that variant. None when the runner is absent."""
    import theme_probe as TP
    import make_wallpaper_live as WL
    names = [f"{k}Color" for k in ROLES]
    import variant_roster as VR
    block = TP.binding_block(qml, names)
    out = {}
    for v in VR.ids():                  # the ROSTER, never MT.VARIANTS (W61 R1)
        got = TP.resolve(v, block, names)
        if got is None:
            return None
        ground, lit, ghost, _a = WL.colors_for(v)
        out[v] = {"resolved": {"lit": got["litColor"], "ghost": got["ghostColor"], "void": got["voidColor"]},
                  "expected": {"lit": "#%02x%02x%02x" % lit, "ghost": "#%02x%02x%02x" % ghost, "void": "#%02x%02x%02x" % ground}}
    return out


def measure(qml=None, resolve=True):
    """The package's facts; `qml` overrides the emission (the selftest's synthetic input)."""
    meta = MT.metadata()
    qml = MT.main_qml() if qml is None else qml
    m = re.search(r"LayoutName=(\S+)", MT.defaults_fragment())
    alpha = re.search(r"property real ghostAlpha:\s*([0-9.]+)", qml)
    b, cs = bindings(qml)
    res = resolution(qml) if resolve else None
    import variant_roster as VR
    return {
        "roster_drift": VR.drift_facts({"make_taskswitch": MT.VARIANTS}),
        "resolution": res,                 # None = the qml runner is absent (withheld)
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
        for v, r in (m["resolution"] or {}).items():
            flags = "".join(f" {k}≠" for k in r["resolved"] if r["resolved"][k] != r["expected"][k])
            print(f"  {v:16s} resolves lit {r['resolved']['lit']} ghost {r['resolved']['ghost']} void {r['resolved']['void']}{flags}")
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
                .replace("Kirigami.Theme.colorSet: Kirigami.Theme.View", ""), resolve=False)
    chk("a missing root is a fact", r["root"], False)
    chk("a baked hex is a fact", r["bindings"]["lit"], "#99ffeb")
    chk("a missing colorSet is a fact", r["colorSet"], None)
    # ⚑ THE RESOLUTION CAN SEE: the real Kirigami.Theme, under a variant's scheme,
    # resolves a WRONG role to a colour that is not the variant's token
    if m["resolution"] is not None:
        wrong = resolution(base.replace("property color litColor: Kirigami.Theme.textColor",
                                        "property color litColor: Kirigami.Theme.backgroundColor"))
        chk("a wrong role resolves to the wrong colour", wrong["EL-Amber"]["resolved"]["lit"] == wrong["EL-Amber"]["expected"]["lit"], False)
        chk("the right role resolves to the token", m["resolution"]["EL-Amber"]["resolved"], m["resolution"]["EL-Amber"]["expected"])
    else:
        print("  SKIP the qml runner is absent — the resolution arm did not run")
    chk("the live emitter agrees with the roster", m["roster_drift"], [])
    kept = MT.VARIANTS
    try:
        MT.VARIANTS = [x for x in kept if x != "EL-Amber"]      # a planted drop
        dropped = measure(resolve=False)["roster_drift"]
    finally:
        MT.VARIANTS = kept
    chk("an emitter that drops a variant is a fact", [(d["who"], d["variant"]) for d in dropped],
        [("make_taskswitch", "EL-Amber")])
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
