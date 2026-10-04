#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_render_constants.py — which render-time values of the QML templates are NOT settings?

⚑ WHY (W268, operator 2026-10-03/04: "every value that is consumed at render time needs
to be exposed and effectful in the configuration view", for all widgets and the live
wallpapers). The clock shipped dead sliders and hidden constants (lit gradient 0.35, halo
opacity 0.75, gradient reach 0.5, brightness) while every gate was green, because no gate
asked what a template CONSUMES, only what its config page DECLARES.

This is the census, as a program: for each tracked QML template it lists every property
declared with a LITERAL default (a number, a boolean, a quoted string) — the values a
mount or a user could set — and says which ones a kcfg key reaches. `--list` prints each
template with its literals and their disposition; `--json` is the MEASUREMENT.

    scripts/check_render_constants.py           # the verdict, as opa_gate render_constants decides it
    scripts/check_render_constants.py --list    # per template: n of m literals configurable
    scripts/check_render_constants.py --json    # the measurement (catalog/render-constants.json holds
                                                # the disposition of every literal no key reaches)
    scripts/check_render_constants.py --selftest

A literal property is CONFIGURABLE when its template reads a configuration key into it
(`plasmoid.configuration.` or `wallpaper.configuration.` in its own default or in the
property's binding), or when the template is a COMPONENT whose mount binds the property
from such a key (the component's literal is then the DEFAULT of a setting, and the mount
is what the census of the mount reads). Everything else is UNCONFIGURED: a render value
no dialog reaches.

⚑ WEAKNESSES, STATED. (1) TEXTUAL, not Qt's parser: a property declared across two lines,
or a literal that is an expression (`2 * Math.max(...)`), is not seen. (2) NUMERIC LITERALS
INSIDE BINDINGS (`Math.floor(height * 0.42)`, `interval: 500`) are not properties and are
not counted here: they are the second pass (W268). (3) A component's literal counts as
configurable only if some mount in the population binds that property from a key. (4) It
does not say whether a configurable property is EFFECTFUL: that is check_config_reach.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

LITERAL = (
    r"(?P<lit>-?\d+(?:\.\d+)?|true|false|\"[^\"]*\")"  # a number, a boolean, a string
)
PROP = re.compile(
    r"^\s*property\s+(?P<type>real|int|bool|string)\s+(?P<name>\w+)\s*:\s*"
    + LITERAL
    + r"\s*(?://.*)?$"
)
CFG = re.compile(r"(?:plasmoid|wallpaper)\.configuration\.(?P<key>\w+)")


def literals(text):
    """[(name, type, literal, line)] — every property with a literal default."""
    out = []
    for n, line in enumerate(text.splitlines(), 1):
        m = PROP.match(line)
        if m:
            out.append((m["name"], m["type"], m["lit"], n))
    return out


def config_reads(text):
    """The kcfg keys a template reads."""
    return sorted(set(CFG.findall(text)))


def bound_by(mount_text, name):
    """True iff some `name: <expression>` line of the mount reads a configuration key,
    directly or through a root property that does (a property of the mount whose own
    definition reads a key)."""
    keyed = {
        m["name"]
        for m in re.finditer(
            r"property\s+\w+\s+(?P<name>\w+)\s*:[^\n]*\n?[^\n]*configuration\.",
            mount_text,
        )
    }
    for m in re.finditer(
        rf"^\s*{re.escape(name)}\s*:\s*(?P<expr>[^\n]+)", mount_text, re.MULTILINE
    ):
        expr = m["expr"]
        if CFG.search(expr) or any(re.search(rf"\broot\.{k}\b", expr) for k in keyed):
            return True
    return False


REGISTRY = os.path.join(ROOT, "catalog", "render-constants.json")


def load_registry():
    """{template: {property: disposition}} from catalog/render-constants.json."""
    import json

    with open(REGISTRY, encoding="utf-8") as fh:
        doc = json.load(fh)
    return {k: v for k, v in doc.items() if not k.startswith("_")}


def measure(templates=None, registry=None):
    """The MEASUREMENT: per template, its literal properties and for each whether a
    configuration key reaches it, and the DISPOSITION the registry records for one no
    key reaches (None: undeclared). `registry_stale` lists registry entries that name
    no property of their template. `templates` is {path: text}."""
    if templates is None:
        import git_tracked

        templates = {}
        for rel in git_tracked.files("templates/*.qml"):
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                templates[rel] = fh.read()
    if registry is None:
        registry = load_registry()
    mounts = {p: t for p, t in templates.items() if config_reads(t)}
    cases = []
    seen = set()
    for path, text in sorted(templates.items()):
        own = config_reads(text) != []
        props = []
        for name, typ, lit, line in literals(text):
            # a literal the template itself keys (its own default under a cfg read) or a
            # component literal some mount binds from a key
            keyed = own and bool(
                re.search(
                    rf"property\s+\w+\s+{re.escape(name)}\s*:[^\n]*\n?[^\n]*configuration\.",
                    text,
                )
            )
            configurable = keyed or any(bound_by(t, name) for t in mounts.values())
            seen.add((path, name))
            props.append(
                {
                    "name": name,
                    "type": typ,
                    "literal": lit,
                    "line": line,
                    "configurable": configurable,
                    "disposition": registry.get(path, {}).get(name),
                }
            )
        cases.append({"template": path, "keys": config_reads(text), "props": props})
    stale = sorted(
        f"{path}:{name}"
        for path, entries in registry.items()
        for name in entries
        if (path, name) not in seen
    )
    return {"cases": cases, "registry_stale": stale}


def main(argv):
    known = {"--list", "--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_render_constants: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if not m["cases"]:
        print(
            "check_render_constants: REFUSED — 0 templates read; the census is broken",
            file=sys.stderr,
        )
        return 1
    if "--json" in argv:
        import json

        print(json.dumps(m, indent=1))
        return 0
    if "--list" not in argv:
        import opa_gate

        return opa_gate.gate("render_constants")
    total = unconfigured = 0
    for c in m["cases"]:
        if not c["props"]:
            continue
        un = [p for p in c["props"] if not p["configurable"]]
        total += len(c["props"])
        unconfigured += len(un)
        print(
            f"{c['template']}: {len(c['props']) - len(un)} of {len(c['props'])} "
            f"literal properties configurable ({len(c['keys'])} kcfg keys read)"
        )
        for p in un:
            how = p["disposition"] or "UNDECLARED"
            print(f"    {how:<14s} L{p['line']:<4d} {p['name']} = {p['literal']}")
    declared = sum(
        1 for c in m["cases"] for p in c["props"] if p["disposition"] is not None
    )
    print(
        f"check_render_constants: {total - unconfigured} of {total} literal "
        f"properties over {len(m['cases'])} templates are configurable; "
        f"{declared} more carry a disposition; "
        f"{unconfigured - declared} UNDECLARED; {len(m['registry_stale'])} stale registry entries"
    )
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    comp = 'Item {\n    property real glow: 1.0\n    property bool on: true // note\n    property color c: "white"\n}\n'
    chk(
        "a literal property is seen (number, boolean, not a colour name)",
        [(n, t, lit) for n, t, lit, _l in literals(comp)],
        [("glow", "real", "1.0"), ("on", "bool", "true")],
    )
    mount = (
        "PlasmoidItem {\n"
        "    property real glow: (plasmoid.configuration.glow === undefined) ? 1.0\n"
        "                        : plasmoid.configuration.glow\n"
        "    SegmentChar {\n        glow: root.glow\n    }\n}\n"
    )
    m = measure({"c.qml": comp, "m.qml": mount}, {})
    props = {p["name"]: p["configurable"] for p in m["cases"][0]["props"]}
    chk(
        "a component literal a mount binds from a key is configurable",
        props["glow"],
        True,
    )
    chk("one no mount binds is UNCONFIGURED", props["on"], False)
    chk("the mount reads its key", m["cases"][1]["keys"], ["glow"])
    chk("an empty template set measures nothing", measure({}, {})["cases"], [])
    # the registry: a disposition is carried onto its property, an undeclared one is None,
    # and an entry that names no property of its template is reported stale
    r = measure(
        {"c.qml": comp, "m.qml": mount},
        {"c.qml": {"on": "STATE", "ghost": "STATE"}},
    )
    disp = {p["name"]: p["disposition"] for p in r["cases"][0]["props"]}
    chk("a registered property carries its disposition", disp["on"], "STATE")
    chk("an unregistered one is undeclared (None)", disp["glow"], None)
    chk(
        "a registry entry naming no property is stale",
        r["registry_stale"],
        ["c.qml:ghost"],
    )
    print("check_render_constants selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
