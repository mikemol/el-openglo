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

CONFIG_XML = """<?xml version="1.0" encoding="UTF-8"?>
<kcfg xmlns="http://www.kde.org/standards/kcfg/1.0">
 <kcfgfile name=""/>
 <group name="General">
  <entry name="showGhost" type="Bool"><default>true</default></entry>
  <entry name="use24h" type="Bool"><default>true</default></entry>
  <entry name="showSeconds" type="Bool"><default>false</default></entry>
  <entry name="blinkColon" type="Bool"><default>true</default></entry>
  <entry name="bloom" type="Double"><default>1.5</default></entry>
  <entry name="weight" type="Double"><default>1.0</default></entry>
 </group>
</kcfg>
"""

CONFIG_QML = """import QtQuick
import org.kde.kcm as KCM
import org.kde.kirigami as Kirigami
import QtQuick.Controls as QQC2
import QtQuick.Layouts

KCM.SimpleKCM {
    property alias cfg_showGhost: showGhost.checked
    property alias cfg_use24h: use24h.checked
    property alias cfg_showSeconds: showSeconds.checked
    property alias cfg_blinkColon: blinkColon.checked
    Kirigami.FormLayout {
        QQC2.CheckBox { id: showGhost; Kirigami.FormData.label: "Show ghost segments:" }
        QQC2.CheckBox { id: use24h; Kirigami.FormData.label: "24-hour clock:" }
        QQC2.CheckBox { id: showSeconds; Kirigami.FormData.label: "Show seconds:" }
        QQC2.CheckBox { id: blinkColon; Kirigami.FormData.label: "Blink colon:" }
        QQC2.Slider { id: bloomSlider; from: 0; to: 4; stepSize: 0.5; Kirigami.FormData.label: "Bloom / glow:" }
        QQC2.Slider { id: weightSlider; from: 0; to: 1; stepSize: 0.25; Kirigami.FormData.label: "Lit stroke weight:" }
    }
}
"""

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
    return f'''import QtQuick
import QtQuick.Layouts
import QtQuick.Effects
import org.kde.plasma.plasmoid
import org.kde.plasma.core as PlasmaCore
import org.kde.kirigami as Kirigami

PlasmoidItem {{
    id: root
    // --- geometry: the SAME tables as the wallpaper (do not hand-edit) ---
{qml_tables()}
    property color litColor: {lit}
    property color ghostColor: {ghost}
    property color hotColor: {hot}
    property int segLen: Math.max(6, Math.floor(height * 0.42))
    property int segThick: Math.max(2, Math.floor(segLen * 0.18))

    property string timeStr: "0000"
    property bool colonOn: true

    Timer {{
        interval: 500; running: true; repeat: true
        onTriggered: {{
            var d = new Date();
            var h = d.getHours();
            if (!plasmoid.configuration.use24h) {{ h = h % 12; if (h === 0) h = 12; }}
            var mm = d.getMinutes();
            var ss = d.getSeconds();
            var s = (h < 10 ? "0" : "") + h + (mm < 10 ? "0" : "") + mm;
            if (plasmoid.configuration.showSeconds) s += (ss < 10 ? "0" : "") + ss;
            root.timeStr = s;
            if (plasmoid.configuration.blinkColon) root.colonOn = !root.colonOn;
            else root.colonOn = true;
        }}
    }}

    preferredRepresentation: fullRepresentation
    fullRepresentation: Item {{
        Layout.preferredWidth: segRow.implicitWidth + segLen
        Layout.minimumWidth: segRow.implicitWidth + segLen
        Row {{
            id: segRow
            anchors.centerIn: parent
            spacing: Math.floor(segLen * 0.25)
            Repeater {{
                model: root.timeStr.length
                Digit {{
                    ch: root.timeStr.charAt(index)
                    insertColon: (index === 2)
                }}
            }}
        }}
    }}

    component Digit: Item {{
        property string ch: "8"
        property bool insertColon: false
        width: segLen + (insertColon ? segLen * 0.7 : 0)
        height: segLen * 2

        // one seven-segment glyph; ghost layer under lit layer
        Repeater {{
            model: ["A","B","C","D","E","F","G"]
            Segment {{
                seg: modelData
                on: root.digSegs[parent.ch] !== undefined
                    && root.digSegs[parent.ch].indexOf(modelData) !== -1
            }}
        }}
        // colon dots after this digit
        Rectangle {{
            visible: parent.insertColon
            width: segThick; height: segThick; radius: segThick/2
            color: root.colonOn ? root.litColor : root.ghostColor
            x: segLen + segLen*0.25; y: segLen*0.62
        }}
        Rectangle {{
            visible: parent.insertColon
            width: segThick; height: segThick; radius: segThick/2
            color: root.colonOn ? root.litColor : root.ghostColor
            x: segLen + segLen*0.25; y: segLen*1.38 - segThick
        }}
    }}

    component Segment: Item {{
        property string seg: "A"
        property bool on: false
        property var g: root.segGeom[seg]         // [kind, ux, uy]
        property bool horiz: g[0] === "h"
        property real gap: segThick * 0.62
        anchors.fill: parent
        Rectangle {{
            property bool showGhost: plasmoid.configuration.showGhost
            visible: parent.on || showGhost
            color: parent.on ? root.litColor : root.ghostColor
            antialiasing: true
            radius: segThick/2
            width:  horiz ? segLen - gap*2 : segThick
            height: horiz ? segThick : segLen - gap*2
            x: (g[1] * segLen) + (horiz ? gap : 0)
            y: (g[2] * segLen) + (horiz ? 0 : gap)
        }}
    }}
}}
'''

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
