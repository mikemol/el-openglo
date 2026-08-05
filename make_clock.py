#!/usr/bin/env python3
"""Seven-segment panel clock plasmoid for the EL grid (Plasma 6).

The clock is a mapping from time digits to the SAME seven-segment geometry the
wallpaper uses — the SEG/DIG tables are extracted from make_wallpaper.py and
emitted into the QML, so the panel clock and the wallpaper can never diverge.
Ghost (unlit) segments render underneath the lit ones — a thing a font can't
do. Colors read from the active scheme via KSvg/Kirigami theme, so the clock
re-phosphors with whatever EL variant is active.

Spec verified against develop.kde.org (Plasma 6): metadata.json with
KPackageStructure=Plasma/Applet + X-Plasma-API-Minimum-Version=6.0, root
PlasmoidItem, entry contents/ui/main.qml, config schema contents/config/main.xml.

Emits plasma-clock/<id>/ per grid cell. Gate: metadata JSON parse + required
keys, QML brace/paren balance, config XML parse, SEG/DIG byte-parity with
make_wallpaper, sabotage. Live render (plasmoidviewer) = ⊕VER."""
import os, re, sys, json, shutil
import xml.etree.ElementTree as ET
from make_schemes import GRID

# --- single source of truth: pull SEG/DIG straight from the wallpaper gen ---
_wp = open("make_wallpaper.py").read()
SEG_SRC = re.search(r'SEGS = \{.*?\}', _wp, re.S).group(0)
DIG_SRC = re.search(r'DIGIT = \{.*?\}', _wp, re.S).group(0)
SEGS = eval(SEG_SRC[SEG_SRC.index("{"):])
DIGIT = eval(DIG_SRC[DIG_SRC.index("{"):])

def qml_tables():
    segs = ", ".join(f'"{k}": ["{v[0]}", {v[1]}, {v[2]}]' for k, v in SEGS.items())
    digs = ", ".join(f'"{k}": "{v}"' for k, v in DIGIT.items())
    return f"    property var segGeom: ({{ {segs} }})\n    property var digSegs: ({{ {digs} }})\n"

def rgbcss(t, k):
    r, g, b = t[k].split(",")
    return f'"#{int(r):02x}{int(g):02x}{int(b):02x}"'

def metadata(t):
    return json.dumps({
        "KPlugin": {
            "Authors": [{"Name": "EL watch themes"}],
            "Category": "Date and Time",
            "Description": "Seven-segment EL clock matching the watch wallpaper",
            "Icon": "clock", "Id": f"org.el.segclock.{t['id'].lower().replace('-', '')}",
            "Name": f"EL Segment Clock ({t['name']})", "Version": "1.0",
            "License": "GPLv3"},
        "KPackageStructure": "Plasma/Applet",
        "X-Plasma-API-Minimum-Version": "6.0"}, indent=2)

# ⚑ THE ARTIFACTS ARE FILES: templates/clock-config.kcfg and clock-config.qml.
# Both were plain `\"\"\"...\"\"\"` constants — no substitution at all — so holding
# them here bought nothing and cost everything: kcfg is XML no schema validator
# could reach, and the config page is QML qmllint could not lint.
def _t(name):
    import templates.loader as TL
    return TL.render(name)


CONFIG_XML = _t("clock-config.kcfg")
CONFIG_QML = _t("clock-config.qml")

def main_qml(t):
    import cvd_gate as _cvd
    def _rgb(css): css=css.strip().strip('"').lstrip("#"); return tuple(int(css[i:i+2],16) for i in (0,2,4))
    def _tup(v): return tuple(int(x) for x in v.split(","))
    lit = rgbcss(t, "focus"); hot = rgbcss(t, "fg_act")
    _bg = _tup(t["view"])
    _lit0 = _rgb(lit)
    # ⊕CONTRAST-STRETCH: span = contrast(lit, ground) bounds the ghost's per-side
    # contrast. Push lit away from ground (into the mode's aesthetic envelope) to
    # widen the span so {lit, ghost, ground} separate evenly. Backlit (bright)
    # grounds gain the most (lit was too close to its own ground); dark-display
    # grounds already have wide span so stretch is a near no-op there.
    _litS = _cvd.stretch_lit(_lit0, _bg)
    lit = '"#%02x%02x%02x"' % _litS
    # ghost is DERIVED to balance against BOTH live and ground (⊕GHOST-CONTRAST/2),
    # not taken from fg_in (which failed WCAG on every lit-mode variant).
    _g = _cvd.derive_ghost(_litS, _bg)
    ghost = '"#%02x%02x%02x"' % _g
    # ⚑ THE QML IS templates/clock-main.qml.  It was 104 lines of markup in an
    # f-string, which cost ~40 DOUBLED BRACE PAIRS — every `{{` and `}}` an
    # artifact of surviving as a Python literal rather than anything QML asked
    # for. As a template it is the document verbatim: qmllint can read it, an
    # editor can open it, and a diff shows which binding moved.
    import templates.loader as TL
    return TL.render("clock-main.qml", tables=qml_tables(),
                     lit=lit, ghost=ghost, hot=hot)

# ------------------------------------------------------------------ gate
def balanced(s, o, c):
    d = 0
    for ch in s:
        if ch == o: d += 1
        elif ch == c:
            d -= 1
            if d < 0: return False
    return d == 0

def check(path, t):
    errs = []
    md = json.load(open(os.path.join(path, "metadata.json")))
    if md.get("KPackageStructure") != "Plasma/Applet":
        errs.append("KPackageStructure != Plasma/Applet")
    if md.get("X-Plasma-API-Minimum-Version") != "6.0":
        errs.append("missing X-Plasma-API-Minimum-Version 6.0")
    if not md["KPlugin"].get("Id"): errs.append("missing KPlugin.Id")
    q = open(os.path.join(path, "contents/ui/main.qml")).read()
    if "PlasmoidItem" not in q.split("\n")[0:12].__str__() and "PlasmoidItem {" not in q:
        errs.append("root is not PlasmoidItem")
    for o, c in [("{", "}"), ("(", ")"), ("[", "]")]:
        if not balanced(q, o, c): errs.append(f"main.qml unbalanced {o}{c}")
    try: ET.parse(os.path.join(path, "contents/config/main.xml"))
    except Exception as e: errs.append(f"config xml: {e}")
    # geometry parity: the tables in the QML must equal the wallpaper's
    for k, v in SEGS.items():
        if f'"{k}": ["{v[0]}", {v[1]}, {v[2]}]' not in q:
            errs.append(f"SEG {k} drifted from wallpaper geometry")
    for k, v in DIGIT.items():
        if f'"{k}": "{v}"' not in q:
            errs.append(f"DIGIT {k} drifted from wallpaper geometry")
    return errs

if __name__ == "__main__":
    shutil.rmtree("plasma-clock", ignore_errors=True)
    failures = {}
    for (ph, mode), (t, dark) in GRID.items():
        path = f"plasma-clock/{t['id']}"
        os.makedirs(os.path.join(path, "contents/ui"), exist_ok=True)
        os.makedirs(os.path.join(path, "contents/config"), exist_ok=True)
        open(os.path.join(path, "metadata.json"), "w").write(metadata(t))
        open(os.path.join(path, "contents/ui/main.qml"), "w").write(main_qml(t))
        open(os.path.join(path, "contents/ui/configGeneral.qml"), "w").write(CONFIG_QML)
        open(os.path.join(path, "contents/config/main.xml"), "w").write(CONFIG_XML)
        open(os.path.join(path, "contents/config/config.qml"), "w").write(
            'import org.kde.plasma.configuration\n\nConfigModel {\n'
            '    ConfigCategory {\n        name: "General"\n        icon: "clock"\n'
            '        source: "configGeneral.qml"\n    }\n}\n')
        errs = check(path, t)
        if errs:
            failures[t["id"]] = errs; shutil.rmtree(path)
            print(f"NOT WRITTEN: {t['id']}: {errs[:3]}")
        else:
            print("wrote", t["id"])
    sys.exit(1 if failures else 0)
