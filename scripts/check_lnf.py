#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_lnf.py — every Look-and-Feel package the packager stages selects what it claims (W37).

    scripts/check_lnf.py            # the verdict, as opa_gate lnf decides it
    scripts/check_lnf.py --json     # the measurement policy/lnf.rego decides
    scripts/check_lnf.py --selftest # the measurement can see a package and its keys

The measurement stages the LnF packages through make_deb.build_lnf_packages (the
same function `make_deb --stage` calls, into its private mkdtemp) and reads back
each package's metadata.json and contents/defaults. The declared population is
make_deb.VARIANTS x make_deb.ENGINES; a declared id the stage does not contain is
a case with a reason, never a smaller population. What each engine must select
is make_deb.ENGINES, carried into the measurement as `engines` so the policy
judges against the packager's own declaration.

⚑ WEAKNESS: this proves the DEFAULTS name the engine; it does not prove Plasma
applies them or that the engine draws with the EL scheme. That is a render in
the k8s VM (W37's next step), not something a file read can see.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def parse_defaults(text):
    """{'kdeglobals/KDE': {key: value}} — an LnF defaults file, groups joined by '/'."""
    out, cur = {}, None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            cur = "/".join(p.strip("[]") for p in line.replace("][", "]\0[").split("\0"))
            out.setdefault(cur, {})
        elif "=" in line and cur is not None:
            k, v = line.split("=", 1)
            out[cur][k.strip()] = v.strip()
    return out


def measure_dir(pkg_dir):
    """The facts one staged package carries, or a reason it could not be read."""
    meta_p = os.path.join(pkg_dir, "metadata.json")
    def_p = os.path.join(pkg_dir, "contents", "defaults")
    for p in (meta_p, def_p):
        if not os.path.isfile(p):
            return {"missing": f"{os.path.relpath(p, pkg_dir)} is absent"}
    try:
        meta = json.load(open(meta_p, encoding="utf-8"))
    except ValueError as e:
        return {"missing": f"metadata.json does not parse: {e}"}
    d = parse_defaults(open(def_p, encoding="utf-8").read())
    deco = d.get("kwinrc/org.kde.kdecoration2", {})
    return {
        "missing": None,
        "meta_id": meta.get("KPlugin", {}).get("Id"),
        "structure": meta.get("KPackageStructure"),
        "color_scheme": d.get("kdeglobals/General", {}).get("ColorScheme"),
        "widget_style": d.get("kdeglobals/KDE", {}).get("widgetStyle"),
        "lnf_package": d.get("kdeglobals/KDE", {}).get("LookAndFeelPackage"),
        "deco_library": deco.get("library"),
        "deco_theme": deco.get("theme"),
    }


def measure():
    import make_deb
    staged = {os.path.basename(src): src for src, _dest in make_deb.build_lnf_packages()}
    engines = {e: {"widget": E["widget"], "deco_library": E["deco"]("X")[0],
                   "deco_theme": E["deco"]("X")[1] is not None}
               for e, E in make_deb.ENGINES.items()}
    cases = []
    for v in make_deb.VARIANTS:
        for e in make_deb.ENGINES:
            pid = make_deb.lnf_id(v, e)
            case = {"id": pid, "variant": v, "engine": e}
            if pid not in staged:
                case["missing"] = "declared but not staged by build_lnf_packages"
            else:
                case.update(measure_dir(staged[pid]))
            cases.append(case)
    declared = {c["id"] for c in cases}
    extra = sorted(set(staged) - declared)
    return {"engines": engines, "cases": cases, "undeclared_staged": extra}


def _selftest():
    import tempfile
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    d = parse_defaults("[kdeglobals][KDE]\nwidgetStyle=oxygen\n\n[kwinrc][org.kde.kdecoration2]\nlibrary=org.kde.oxygen\n")
    check("nested groups join with /", sorted(d), ["kdeglobals/KDE", "kwinrc/org.kde.kdecoration2"])
    check("a key is read under its group", d["kdeglobals/KDE"]["widgetStyle"], "oxygen")
    with tempfile.TemporaryDirectory() as t:
        check("an empty package dir is missing, with a reason",
              measure_dir(t)["missing"] is not None, True)
        os.makedirs(os.path.join(t, "contents"))
        with open(os.path.join(t, "metadata.json"), "w") as f:
            json.dump({"KPackageStructure": "Plasma/LookAndFeel", "KPlugin": {"Id": "x"}}, f)
        with open(os.path.join(t, "contents", "defaults"), "w") as f:
            f.write("[kdeglobals][General]\nColorScheme=EL-Azure\n[kdeglobals][KDE]\nwidgetStyle=Breeze\n")
        m = measure_dir(t)
        check("a well-formed package is read", (m["missing"], m["color_scheme"], m["widget_style"],
                                                m["deco_library"]), (None, "EL-Azure", "Breeze", None))
    print("check_lnf selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest"}:
            print(f"check_lnf: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("lnf")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
