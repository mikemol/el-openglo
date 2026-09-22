#!/usr/bin/env python3
"""check_config_page.py — does each config page declare what Plasma will SET on it,
and does every mount answer for every DISPLAY parameter?

⚑ WHY (operator, live 2026-09-22, plasmashell's stderr on opening the marquee's
settings): `Setting initial properties failed: SimpleKCM does not have a property
called cfg_speedDefault` — thirteen of them. Plasma 6's configuration loader sets,
on the page, ONE INITIAL PROPERTY PER KCFG ENTRY TWICE: `cfg_<key>` (the value)
and `cfg_<key>Default` (the schema default).

⚑ AND WHY THE SECOND QUESTION (W59, catalog/one-display.md): three mounts of one
display spelled the same display parameters in two vocabularies, one mount
reached `bloom` and another could not, and the live wallpaper had no page at all
— and nothing recorded any of it, because no artefact held the lists at once.
display_params declares the DISPLAY layer once; each mount answers every
parameter Exposed(spelling) or Withheld(reason). This measures, per mount and
parameter: what the declaration says, whether the spelling is in the EMITTED kcfg
and on the EMITTED page, and any other mount's display spelling that turned up in
this mount's kcfg undeclared. policy/config_page.rego (D-rules) decides; an
UNEXPLAINED ABSENCE is a denial.

    scripts/check_config_page.py             # n of m summary
    scripts/check_config_page.py --json      # the measurement
    scripts/check_config_page.py --selftest  # the measurement can see

The documents are the EMITTERS' output (the templates carry include holes since
W59), read through check_template_parity._value — so this imports the emitters and
is as slow as they are.

WEAKNESS: a declaration is read by its `property … cfg_<name>` line (qmllint owns
the grammar). An exposed key the mount's main.qml never READS is not seen here;
nor is a display parameter that exists in a display component but was never
entered into display_params.DISPLAY — the population is the declaration.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
# (mount, page label, (module, kcfg accessor), (module, page accessor))
PAIRS = (("clock", "clock-config.qml", ("make_clock", "CONFIG_XML"), ("make_clock", "CONFIG_QML")),
         ("marquee", "marquee-config.qml", ("make_notify_marquee", "config_xml"),
          ("make_notify_marquee", "config_qml")),
         ("wallpaper", "live-wallpaper-config.qml", ("make_wallpaper_live", "config_main_xml"),
          ("make_wallpaper_live", "config_qml")))
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


def measure_display(mount, kcfg_text, qml_text, display, mounts):
    """Per parameter: the declaration's answer and what the emitted documents hold."""
    from display_params import Exposed, Withheld
    keys = {k for k, _t in entries(kcfg_text)}
    decl = set(declared(qml_text)) if qml_text is not None else set()
    answers = mounts.get(mount, {})
    rows = []
    for p in display:
        a = answers.get(p.key)
        row = {"param": p.key}
        if isinstance(a, Exposed):
            row.update(declared="exposed", spelling=a.spelling, in_kcfg=a.spelling in keys,
                       on_page=f"cfg_{a.spelling}" in decl)
        elif isinstance(a, Withheld):
            row.update(declared="withheld", reason=a.reason)
        else:
            row.update(declared="absent")
        rows.append(row)
    own = {a.spelling for a in answers.values() if isinstance(a, Exposed)}
    every = {a.spelling for m in mounts.values() for a in m.values() if isinstance(a, Exposed)}
    return {"mount": mount, "has_page": qml_text is not None, "params": rows,
            "stray": sorted((keys & every) - own)}


def measure():
    import check_template_parity as CTP
    import display_params as DP
    pages, display = [], []
    for mount, label, (km, ka), (qm, qa) in PAIRS:
        try:
            kcfg = CTP._value(km, ka, None)
            qml = CTP._value(qm, qa, None)
        except Exception as e:                   # noqa: BLE001
            pages.append({"page": label, "withheld": f"{km}.{ka} / {qm}.{qa} raised {type(e).__name__}: {e}"})
            continue
        pages.append(measure_pair(kcfg, qml, label))
        display.append(measure_display(mount, kcfg, qml, DP.DISPLAY, DP.MOUNTS))
    return {"pages": pages, "display": {"params": [p.key for p in DP.DISPLAY], "mounts": display}}


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
    n = len(m["display"]["params"])
    for d in m["display"]["mounts"]:
        ex = [r["param"] for r in d["params"] if r["declared"] == "exposed"]
        wh = [r["param"] for r in d["params"] if r["declared"] == "withheld"]
        ab = [r["param"] for r in d["params"] if r["declared"] == "absent"]
        print(f"  display @ {d['mount']}: {len(ex)} exposed, {len(wh)} withheld, "
              f"{len(ab)} UNEXPLAINED of {n}" + (f" ({', '.join(ab)})" if ab else ""))
    print(f"check_config_page: {len(m['pages'])} page(s), {len(m['display']['mounts'])} mount(s) "
          f"measured; the verdict is `opa_gate.py config_page`")
    return 0


def _selftest():
    """The measurement can SEE: an undeclared cfg_ key, a missing Default, and an
    UNEXPLAINED ABSENCE of a display parameter. The verdicts are the rego tests'."""
    import display_params as DP
    kcfg = ('<?xml version="1.0"?><kcfg xmlns="http://www.kde.org/standards/kcfg/1.0"><group name="G">'
            '<entry name="speed" type="Double"><default>1</default></entry>'
            '<entry name="bloom" type="Double"><default>1</default></entry>'
            '<entry name="traceLog" type="String"><default></default></entry></group></kcfg>')
    page = ("KCM.SimpleKCM {\n    property alias cfg_speed: s.value\n"
            "    property real cfg_speedDefault\n    property string cfg_traceLog\n}\n")
    r = measure_pair(kcfg, page, "t")
    display = (DP.Param("bloom", "Double", "B", ""), DP.Param("pitch", "Double", "P", ""))
    seen = {
        "the kcfg's entries are read": r["entries"] == 3,
        "a declared value and default are seen": r["keys"][0]["value"] and r["keys"][0]["default"],
        "a missing Default is a fact": r["keys"][2]["default"] is False,
        "an undeclared key is a fact": measure_pair(kcfg, "KCM.SimpleKCM {}\n", "t")["keys"][0]["value"] is False,
    }
    # ⚑ AN UNEXPLAINED ABSENCE IS SEEN: `pitch` is in neither answer set
    d = measure_display("m", kcfg, page, display, {"m": {"bloom": DP.Exposed("bloom", "1")}})
    seen["an unexplained absence is seen"] = d["params"][1]["declared"] == "absent"
    seen["an exposed key missing from the page is seen"] = d["params"][0]["on_page"] is False
    w = measure_display("m", kcfg, page, display,
                        {"m": {"bloom": DP.Withheld("r"), "pitch": DP.Withheld("r")}})
    seen["a withheld answer carries its reason"] = [x.get("reason") for x in w["params"]] == ["r", "r"]
    # another mount's display spelling in THIS kcfg, undeclared here, is a stray
    s = measure_display("m", kcfg, page, display, {"m": {"bloom": DP.Withheld("r")},
                                                   "n": {"bloom": DP.Exposed("bloom", "1")}})
    seen["another mount's spelling, undeclared here, is stray"] = s["stray"] == ["bloom"]
    for label, ok in seen.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    ok = all(seen.values())
    print("check_config_page selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
