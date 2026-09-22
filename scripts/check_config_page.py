#!/usr/bin/env python3
"""check_config_page.py — does each config page declare what Plasma will SET on it?

⚑ WHY (operator, live 2026-09-22, plasmashell's stderr on opening the marquee's
settings): `Setting initial properties failed: SimpleKCM does not have a property
called cfg_speedDefault` — thirteen of them — and `Created graphical object was
not placed in the graphics scene`. Plasma 6's configuration loader sets, on the
page, ONE INITIAL PROPERTY PER KCFG ENTRY TWICE: `cfg_<key>` (the value) and
`cfg_<key>Default` (the schema default). A page that declares only the aliases it
draws controls for is refused for every key it does not name — including keys it
has no control for on purpose (traceLog is the widget's own log, not a setting).

The measurement: for each (kcfg, page) pair under templates/, the kcfg's entries
and the page's declared `cfg_…` properties; per entry, whether `cfg_<key>` and
`cfg_<key>Default` are both declared. policy/config_page.rego decides.

    scripts/check_config_page.py --json      # the measurement
    scripts/check_config_page.py --selftest  # the measurement can see

WEAKNESS: a declaration is read by its `property … cfg_<name>` line — the QML
grammar's own reading is qmllint's (check_qml_lint), and it does not know Plasma's
setter contract. A page with no kcfg (the live wallpaper has a kcfg and no page)
is not a pair and is not measured.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES = os.path.join(ROOT, "templates")
PAIRS = (("clock-config.kcfg", "clock-config.qml"),
         ("marquee-config.kcfg", "marquee-config.qml"))
KCFG_NS = "{http://www.kde.org/standards/kcfg/1.0}"
# a declaration with or without an initialiser: `property real cfg_xDefault` is one
DECL = re.compile(r"^\s*(?:default\s+|readonly\s+)?property\s+(?:alias|\w+)\s+(cfg_\w+)\s*(?::|$)", re.M)


def entries(kcfg_text):
    root = ET.fromstring(kcfg_text)
    return [(e.get("name"), e.get("type")) for e in root.iter(f"{KCFG_NS}entry")]


def declared(qml_text):
    return DECL.findall(qml_text)


def measure_pair(kcfg_text, qml_text, label):
    names = entries(kcfg_text)
    decl = set(declared(qml_text))
    return {"page": label, "entries": len(names), "declared": sorted(decl), "keys": [
        {"key": k, "type": t, "value": f"cfg_{k}" in decl, "default": f"cfg_{k}Default" in decl}
        for k, t in names]}


def measure(templates=TEMPLATES, pairs=PAIRS):
    pages = []
    for kcfg, qml in pairs:
        kp, qp = os.path.join(templates, kcfg), os.path.join(templates, qml)
        if not (os.path.isfile(kp) and os.path.isfile(qp)):
            pages.append({"page": qml, "withheld": f"{kcfg} or {qml} is absent"})
            continue
        pages.append(measure_pair(open(kp, encoding="utf-8").read(),
                                  open(qp, encoding="utf-8").read(), qml))
    return {"pages": pages}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_config_page: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    for p in m["pages"]:
        if "withheld" in p:
            print(f"  {p['page']}: WITHHELD {p['withheld']}")
            continue
        both = sum(1 for k in p["keys"] if k["value"] and k["default"])
        print(f"  {p['page']}: {both} of {p['entries']} entries declare value + default")
    print(f"check_config_page: {len(m['pages'])} page(s) measured; the verdict is `opa_gate.py config_page`")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    kcfg = ('<?xml version="1.0"?><kcfg xmlns="http://www.kde.org/standards/kcfg/1.0"><group name="G">'
            '<entry name="speed" type="Double"><default>1</default></entry>'
            '<entry name="traceLog" type="String"><default></default></entry></group></kcfg>')
    page = ("KCM.SimpleKCM {\n    property alias cfg_speed: s.value\n"
            "    property real cfg_speedDefault\n    property string cfg_traceLog\n}\n")
    r = measure_pair(kcfg, page, "t")
    chk("the kcfg's entries are read", r["entries"], 2)
    chk("a declared value and default are seen", [k["value"] and k["default"] for k in r["keys"]][0], True)
    chk("a missing Default is a fact", [k["default"] for k in r["keys"]][1], False)
    chk("an undeclared key is a fact", measure_pair(kcfg, "KCM.SimpleKCM {}\n", "t")["keys"][0]["value"], False)
    print("check_config_page selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
