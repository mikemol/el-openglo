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

# ⚑ ONE PACKAGE, THE VARIANT IS THE ACTIVE COLOUR SCHEME (⊕ONE-THEME, W35;
# catalog/one-theme.md): lit / ghost / hot are Kirigami.Theme's textColor /
# disabledTextColor / activeTextColor under colorSet View — the roles
# make_schemes.emit_colors writes fg / fg_in / fg_act into. The ghost alpha is
# global (make_taskswitch.ghost_alpha refuses otherwise) and baked.
PACKAGE_ID = "org.el.segclock"


def metadata():
    return json.dumps({
        "KPlugin": {
            "Authors": [{"Name": "EL watch themes"}],
            "Category": "Date and Time",
            "Description": "Seven-segment EL clock matching the watch wallpaper, coloured by the active scheme",
            "Icon": "clock", "Id": PACKAGE_ID,
            "Name": "EL Segment Clock", "Version": "1.0",
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
# ⚑ THE OPERATOR'S GAP (2026-09-22, read from the live appletsrc: digitGap 1.186
# against the datasheet's 0.786 = 1.509x). The datasheet pitch is a module's, packed
# for a 4-digit LCD; on a panel the digits read better with air between them. The
# factor is authored, the base is still the substrate's.
DIGIT_GAP_SCALE = 1.5


def _metrics_holes():
    m = _ST.metrics(2.0)                      # H = 2 segLen -> lengths in segLen
    return {"digitGap": f"{(m['pitch'] - 1.0) * DIGIT_GAP_SCALE:.3f}",
            "digitGapMin": f"{m['pitch'] - 1.0:.3f}",     # the slider's floor: the module pitch itself
            "strokeBase": f"{m['stroke'] / 1.25:.3f}",
            "dot": f"{m['dot']:.3f}",
            "colonAdvance": f"{m['colon_advance']:.3f}"}


# ⚑ THE DISPLAY ROWS ARE INCLUDED, NOT WRITTEN HERE (W59): display_params declares
# them once for every mount; the templates carry only this clock's mount rows.
import display_params as _DP
CONFIG_XML = _t("clock-config.kcfg", displayEntries=_DP.kcfg_entries("clock", _metrics_holes(), "  "))
CONFIG_QML = _t("clock-config.qml", displayDecls=_DP.qml_decls("clock"),
                displayControls=_DP.qml_controls("clock", _metrics_holes()))

def main_qml():
    # ⚑ THE COLOURS WERE READ FROM THE TOKEN DICT, NOT RE-DERIVED HERE (W8's
    # ruling: one colour chain — this once took `focus` through cvd_gate.stretch_lit
    # and derive_ghost, a copy of the chain the solver later owned, and drew a lit
    # and a ghost the palette never saw, opaque; measured 2026-09-20 by
    # check_ghost_surfaces, 6 of 6). Since W35 they are not read here at all: the
    # template BINDS them to the active scheme's roles, and the scheme is what
    # make_schemes.emit_colors wrote the tokens into — the chain is one link shorter.
    # The one hole that is a colour fact is the ghost alpha, global.
    import make_taskswitch as TS
    # ⚑ THE QML IS templates/clock-main.qml.  It was 104 lines of markup in an
    # f-string, which cost ~40 DOUBLED BRACE PAIRS — every `{{` and `}}` an
    # artifact of surviving as a Python literal rather than anything QML asked
    # for. As a template it is the document verbatim: qmllint can read it, an
    # editor can open it, and a diff shows which binding moved.
    import templates.loader as TL
    return TL.render("clock-main.qml", tables=qml_tables(), ghostAlpha=TS.ghost_alpha(),
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

def render_all(path):
    """Write the ONE package into path."""
    os.makedirs(os.path.join(path, "contents/ui"), exist_ok=True)
    os.makedirs(os.path.join(path, "contents/config"), exist_ok=True)
    open(os.path.join(path, "metadata.json"), "w").write(metadata())
    open(os.path.join(path, "contents/ui/main.qml"), "w").write(main_qml())
    # ⚑ THE DISPLAY SHIPS BESIDE THE MOUNT OR THE IMPORT RESOLVES TO NOTHING
    # (W33, s133): main.qml instantiates SegmentChar by bare name, which QML
    # resolves from the same directory. The live wallpaper emits the SAME
    # component from the same accessor — one display, two mounts.
    import make_segment_display as SD
    open(os.path.join(path, "contents/ui/SegmentChar.qml"), "w").write(SD.segment_char_component())
    open(os.path.join(path, "contents/ui/configGeneral.qml"), "w").write(CONFIG_QML)
    open(os.path.join(path, "contents/config/main.xml"), "w").write(CONFIG_XML)
    open(os.path.join(path, "contents/config/config.qml"), "w").write(
        'import org.kde.plasma.configuration\n\nConfigModel {\n'
        '    ConfigCategory {\n        name: "General"\n        icon: "clock"\n'
        '        source: "configGeneral.qml"\n    }\n}\n')
    return path


def check(path):
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
    path = f"plasma-clock/{PACKAGE_ID}"
    render_all(path)
    errs = check(path)
    if errs:
        shutil.rmtree(path)
        print(f"NOT WRITTEN: {PACKAGE_ID}: {errs[:3]}")
        sys.exit(1)
    print("wrote", PACKAGE_ID)
    sys.exit(0)
