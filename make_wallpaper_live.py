#!/usr/bin/env python3
"""Live wallpaper emitter (⊕WALLPAPER-LIVE) — the 8th palette surface, mounted
TWICE (desktop containment + lock screen) from ONE plugin.

A Plasma/Wallpaper QML package per variant: a WallpaperItem that fills the screen
with the void ground and draws a large centred phosphor seven-seg clock showing
the REAL current time (the system is up here, unlike the Plymouth boot stage, so
wall-clock is honestly sourceable — a true living watch face). Colors are baked
from the same scheme tokens (lit = stretch_lit, ghost = derive_ghost, void
ground), so it cannot drift.

FETCHED silent-fail traps (honored):
  - root MUST be WallpaperItem (org.kde.plasma.plasmoid), not plain Item;
  - metadata.json MUST carry "KPackageStructure":"Plasma/Wallpaper".
Config: wallpaper.configuration.<key>. `breathe` gates the continuous backlight
animation (rich on the lock mount, off/cheap on the desktop mount).
"""
import os
import json
import make_clock as MC
import make_preview as MP
import cvd_gate as C

ROOT = os.path.dirname(os.path.abspath(__file__))


def _rgb(css):
    css = css.strip().strip('"').lstrip("#")
    return tuple(int(css[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return '"#%02x%02x%02x"' % rgb


def colors_for(variant):
    """Derive the same lit/ghost/void the clock plasmoid uses, from tokens."""
    t = MC.variant_tokens(variant) if hasattr(MC, "variant_tokens") else None
    # fall back to GRID lookup keyed by variant name
    from make_schemes import GRID
    ph, mode = _variant_key(variant)
    tok = [tt for (p, m), (tt, d) in GRID.items() if p == ph and m == mode][0]
    ground = tuple(int(x) for x in tok["view"].split(","))
    lit0 = _rgb(MC.rgbcss(tok, "focus"))
    litS = C.stretch_lit(lit0, ground)
    ghost = C.derive_ghost(litS, ground)
    return ground, litS, ghost


def _variant_key(variant):
    v = variant.lower()
    mode = "lit" if v.endswith("-lit") else "off"
    if "openglo" in v:
        ph = "openglo"
    elif "azure" in v:
        ph = "azure"
    else:
        ph = "amber"
    return ph, mode


def metadata(variant):
    return {
        "KPackageStructure": "Plasma/Wallpaper",
        "KPlugin": {
            "Id": f"org.el.openglo.live.{variant.lower().replace('-', '')}",
            "Name": f"EL Openglo Live ({variant})",
            "Description": f"Living electroluminescent watch face — {variant}",
            "License": "GPLv3",
            "Authors": [{"Name": "EL Openglo"}],
        },
        "X-Plasma-API-Minimum-Version": "6.0",
    }


def main_qml(variant):
    ground, lit, ghost = colors_for(variant)
    gnd = _hex(ground)
    litc = _hex(lit)
    ghc = _hex(ghost)
    # seven-seg strokes on a 2x4 grid (matches make_plymouth / clock)
    return f'''import QtQuick
import org.kde.plasma.plasmoid

// WallpaperItem is REQUIRED as the root (plain Item renders zero-size off-screen).
WallpaperItem {{
    id: root
    property color litColor: {litc}
    property color ghostColor: {ghc}
    property color voidColor: {gnd}
    property bool breathe: (wallpaper.configuration.breathe === undefined) ? false
                           : wallpaper.configuration.breathe

    Rectangle {{ anchors.fill: parent; color: root.voidColor }}

    // seven-seg geometry: which coarse segments are lit per digit
    property var seg: ({{
        "0":"abcdef","1":"bc","2":"abdeg","3":"abcdg","4":"bcfg",
        "5":"acdfg","6":"acdefg","7":"abc","8":"abcdefg","9":"abcdfg"
    }})

    property string timeStr: "00:00"
    function tick() {{
        var d = new Date();
        var h = d.getHours(); var m = d.getMinutes();
        root.timeStr = (h<10?"0":"")+h + ":" + (m<10?"0":"")+m;
        clockCanvas.requestPaint();
    }}
    Timer {{ interval: 1000; running: true; repeat: true; triggeredOnStart: true; onTriggered: root.tick() }}

    // gentle backlight breathe (lock mount); off on desktop (config)
    property real glow: 1.0
    SequentialAnimation on glow {{
        running: root.breathe; loops: Animation.Infinite
        NumberAnimation {{ from: 0.85; to: 1.0; duration: 2200; easing.type: Easing.InOutSine }}
        NumberAnimation {{ from: 1.0; to: 0.85; duration: 2200; easing.type: Easing.InOutSine }}
    }}
    onGlowChanged: clockCanvas.requestPaint()

    Canvas {{
        id: clockCanvas
        anchors.centerIn: parent
        width: parent.width * 0.6
        height: width * 0.32
        renderTarget: Canvas.FramebufferObject
        onPaint: {{
            var ctx = getContext("2d"); ctx.reset();
            var s = root.timeStr;               // "HH:MM"
            var U = height / 5.0;                // unit; digit is 2U x 4U
            var T = U * 0.40;                    // lit stroke (stroke-weight)
            var Tg = U * 0.26;                   // ghost stroke
            var g = 0;
            var stroke = {{
                "a":["h",0,2,0],"g":["h",0,2,2],"d":["h",0,2,4],
                "f":["v",0,0,2],"b":["v",2,0,2],"e":["v",0,2,4],"c":["v",2,2,4]
            }};
            function drawStroke(spec, U, T, ox, oy, style) {{
                ctx.fillStyle = style; var gg = T*0.6;
                ctx.beginPath();
                if (spec[0]==="h") {{ var a=spec[1]*U,b=spec[2]*U,y=spec[3]*U;
                    ctx.moveTo(ox+a+gg,oy+y-T/2);ctx.lineTo(ox+b-gg,oy+y-T/2);
                    ctx.lineTo(ox+b-gg,oy+y+T/2);ctx.lineTo(ox+a+gg,oy+y+T/2); }}
                else {{ var x=spec[1]*U,y0=spec[2]*U,y1=spec[3]*U;
                    ctx.moveTo(ox+x-T/2,oy+y0+gg);ctx.lineTo(ox+x+T/2,oy+y0+gg);
                    ctx.lineTo(ox+x+T/2,oy+y1-gg);ctx.lineTo(ox+x-T/2,oy+y1-gg); }}
                ctx.closePath(); ctx.fill();
            }}
            // ⊕WALLPAPER-CONTRAST: lit-vs-ghost separation scales with parsing
            // mode. This is a GLANCED-AT ambient surface, so lit must POP: (1) the
            // ghost is drawn SUBORDINATE (low alpha — it recedes to texture, since
            // here only the lit time is parsed), (2) lit gets a BLOOM glow (the
            // channel the clock has and this surface was missing). Canvas-native
            // glow = lit stroke drawn underneath at wider T and low alpha.
            function drawDigit(ch, ox, oy) {{
                var on = root.seg[ch] || "";
                // pass 1: ghost, subordinate (recedes to texture)
                ctx.globalAlpha = 0.45;
                for (var k in stroke) {{
                    if (on.indexOf(k) < 0) drawStroke(stroke[k], U, Tg, ox, oy, root.ghostColor);
                }}
                ctx.globalAlpha = 1.0;
                // pass 2: lit bloom halo (wide, faint, lit-only) — makes lit POP
                ctx.globalAlpha = 0.18;
                for (var k2 in stroke) {{
                    if (on.indexOf(k2) >= 0) drawStroke(stroke[k2], U, T*2.1, ox, oy, root.litColor);
                }}
                ctx.globalAlpha = 0.30;
                for (var k3 in stroke) {{
                    if (on.indexOf(k3) >= 0) drawStroke(stroke[k3], U, T*1.5, ox, oy, root.litColor);
                }}
                // pass 3: crisp lit core
                ctx.globalAlpha = 1.0;
                for (var k4 in stroke) {{
                    if (on.indexOf(k4) >= 0) drawStroke(stroke[k4], U, T, ox, oy, root.litColor);
                }}
            }}
            var digitW = U*2 + U*0.6;
            var colonW = U*0.8;
            var chars = [s.charAt(0), s.charAt(1), ":", s.charAt(3), s.charAt(4)];
            var totalW = digitW*4 + colonW;
            var x = (width - totalW)/2;
            var y = (height - U*4)/2;
            ctx.globalAlpha = root.glow;
            for (var i=0;i<chars.length;i++) {{
                if (chars[i]===":") {{
                    var r=U*0.18;
                    // colon bloom halo (match the digit glow) then crisp core
                    ctx.fillStyle = root.litColor;
                    ctx.globalAlpha = 0.22;
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*1.3, r*2.0,0,2*Math.PI); ctx.fill();
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*2.7, r*2.0,0,2*Math.PI); ctx.fill();
                    ctx.globalAlpha = 1.0;
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*1.3, r,0,2*Math.PI); ctx.fill();
                    ctx.beginPath(); ctx.arc(x+colonW/2, y+U*2.7, r,0,2*Math.PI); ctx.fill();
                    x += colonW;
                }} else {{ drawDigit(chars[i], x, y); x += digitW; }}
            }}
            ctx.globalAlpha = 1.0;
        }}
    }}
}}
'''


def config_main_xml():
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<kcfg xmlns="http://www.kde.org/standards/kcfg/1.0">\n'
            '  <kcfgfile name=""/>\n'
            '  <group name="General">\n'
            '    <entry name="breathe" type="Bool"><default>false</default></entry>\n'
            '  </group>\n'
            '</kcfg>\n')


def render_all(variants, dir_map):
    written = {}
    for v in variants:
        d = dir_map[v]
        ui = os.path.join(d, "contents", "ui")
        cfg = os.path.join(d, "contents", "config")
        os.makedirs(ui, exist_ok=True)
        os.makedirs(cfg, exist_ok=True)
        open(os.path.join(d, "metadata.json"), "w").write(
            json.dumps(metadata(v), indent=2))
        open(os.path.join(ui, "main.qml"), "w").write(main_qml(v))
        open(os.path.join(cfg, "main.xml"), "w").write(config_main_xml())
        written[v] = d
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/wplive-{v}" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "live wallpapers")
    for v in variants:
        g, l, gh = colors_for(v)
        print(f"  {v}: void={g} lit={l} ghost={gh}")
