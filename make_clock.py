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

# --- single source of truth: the segment substrate (⊕SEGMENT-SUBSTRATE) ------
# ⚑ THIS READ THE WALLPAPER'S SOURCE TEXT AND eval'd IT.  Three lines of regex
# over another module's FILE, pulling out `SEGS = {...}` and `DIGIT = {...}` as
# literals — so this file's geometry depended on the wallpaper's literal SYNTAX,
# not on any interface. Reformatting that dict, or deriving it, broke this file
# at import with a NoneType.group() traceback naming neither cause nor cure.
#
# It called itself "single source of truth", and it was the opposite: a COPY
# taken by scraping. The substrate is the source; both surfaces read it, and the
# format ("7" for digits) is the only per-surface choice.
import segment_topology as _ST

SEGS = _ST.seg7_svg_grid()
DIGIT = {ch: _ST.glyph7_letters(ch) for ch in "0123456789"}

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
def _t(name, **holes):
    import templates.loader as TL
    return TL.render(name, **holes)


# ⚑ PITCH, STROKE AND DOT ARE THE SUBSTRATE'S (segment_topology.MODULE_METRICS,
# four datasheets), in this surface's unit: the digit is 2·segLen tall and its
# centreline box is segLen wide, so the Row gap is pitch - segLen. The lit
# stroke at weight=1 is 1.25x the base, so the base is stroke/1.25. The colon
# adds no advance (the 88:88 module keeps 12.7 across it).
def _metrics_holes():
    m = _ST.metrics(2.0)                      # H = 2 segLen -> lengths in segLen
    return {"digitGap": f"{m['pitch'] - 1.0:.3f}",
            "strokeBase": f"{m['stroke'] / 1.25:.3f}",
            "dot": f"{m['dot']:.3f}",
            "colonAdvance": f"{m['colon_advance']:.3f}"}


CONFIG_XML = _t("clock-config.kcfg", **_metrics_holes())
CONFIG_QML = _t("clock-config.qml", **_metrics_holes())

def main_qml(t):
    # ⚑ THE COLOURS ARE READ FROM THE TOKEN DICT, NOT RE-DERIVED HERE.  This took
    # `focus` (the ACCENT) as lit, pushed it through cvd_gate.stretch_lit
    # (⊕CONTRAST-STRETCH, session 39) and then cvd_gate.derive_ghost (the 99-point
    # balance scan) — "not taken from fg_in (which failed WCAG on every lit-mode
    # variant)", as the old comment said, and that was true of the AUTHORED
    # palette. The solver (sessions 57-58) then took over both: solve_lit embodies
    # the same push-lit-away-from-ground invariant, and fg_in is solved THROUGH the
    # render alpha against an APCA floor (relations.md §3b). Nobody retired this
    # copy, so the clock drew a lit and a ghost the palette never saw and drew the
    # ghost OPAQUE — measured 2026-09-20 by scripts/check_ghost_surfaces.py, 6 of 6
    # variants. Operator ruling (W8): one colour chain. The residue is the docstring
    # of cvd_gate.stretch_lit / derive_ghost, which still exist for the checks.
    lit = rgbcss(t, "fg"); ghost = rgbcss(t, "fg_in"); hot = rgbcss(t, "fg_act")
    alpha = float(t["ghost_alpha"])
    # ⚑ THE QML IS templates/clock-main.qml.  It was 104 lines of markup in an
    # f-string, which cost ~40 DOUBLED BRACE PAIRS — every `{{` and `}}` an
    # artifact of surviving as a Python literal rather than anything QML asked
    # for. As a template it is the document verbatim: qmllint can read it, an
    # editor can open it, and a diff shows which binding moved.
    import templates.loader as TL
    return TL.render("clock-main.qml", tables=qml_tables(),
                     lit=lit, ghost=ghost, hot=hot, ghostAlpha=alpha,
                     **_metrics_holes())

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
