#!/usr/bin/env python3
"""Aurorae window decorations for the EL grid — flat, no skeuomorphism.

Frame: panel-off (or lit-panel) flat borders. The active window's only
ornament is a 2px phosphor seam under the titlebar. Buttons are segment
glyphs: ghost at rest, lit on hover, backlight-pressed on click.

Emits aurorae/themes/<id>/ per grid cell. A spec-checklist gate (required
FrameSvg element IDs, parseable rc/metadata) runs on every generation and
fails loudly; live render remains for the user's Plasma session.
Spec: https://develop.kde.org/docs/plasma/aurorae/
"""
import os, sys, shutil, configparser
import xml.etree.ElementTree as ET
from make_schemes import GRID

def rgb2hex(s):
    r, g, b = s.split(",")
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

SIDES = ["topleft", "top", "topright", "left", "center", "right",
         "bottomleft", "bottom", "bottomright"]

def frame_group(prefix, x0, frame, seam=None):
    """One FrameSvg (9 elements) at x-offset x0. Geometry:
    top row h=30 (title area), sides w=2, bottom h=2, top corners r=4."""
    g = []
    def rect(sid, x, y, w, h, fill, extra=""):
        g.append(f'<rect id="{prefix}-{sid}" x="{x0+x}" y="{y}" width="{w}" height="{h}" fill="{fill}"{extra}/>')
    # top-left corner: rounded outer corner via path
    g.append(f'<path id="{prefix}-topleft" d="M {x0+0} 30 L {x0+0} 4 Q {x0+0} 0 {x0+4} 0 L {x0+8} 0 L {x0+8} 30 Z" fill="{frame}"/>')
    rect("top", 8, 0, 16, 30, frame)
    g.append(f'<path id="{prefix}-topright" d="M {x0+24} 0 L {x0+28} 0 Q {x0+32} 0 {x0+32} 4 L {x0+32} 30 L {x0+24} 30 Z" fill="{frame}"/>')
    rect("left", 0, 30, 2, 16, frame)
    rect("center", 8, 34, 16, 8, frame, ' opacity="0"')
    rect("right", 30, 30, 2, 16, frame)
    rect("bottomleft", 0, 46, 2, 2, frame)
    rect("bottom", 8, 46, 16, 2, frame)
    rect("bottomright", 30, 46, 2, 2, frame)
    if seam:  # the EL seam: 2px glow across the bottom of the title area
        g.append(f'<rect x="{x0+0}" y="28" width="8" height="2" fill="{seam}"/>')
        g.append(f'<rect x="{x0+8}" y="28" width="16" height="2" fill="{seam}"/>')
        g.append(f'<rect x="{x0+24}" y="28" width="8" height="2" fill="{seam}"/>')
    return "\n".join(g)

def decoration_svg(t):
    frame = rgb2hex(t["view"]); seam = rgb2hex(t["focus"])
    groups = [
        frame_group("decoration", 0, frame, seam),
        frame_group("decoration-inactive", 40, frame, None),
        frame_group("decoration-opaque", 80, frame, seam),
        frame_group("decoration-opaque-inactive", 120, frame, None),
        f'<rect id="decoration-maximized-center" x="160" y="0" width="16" height="16" fill="{frame}"/>',
        f'<rect id="decoration-maximized-inactive-center" x="180" y="0" width="16" height="16" fill="{frame}"/>',
    ]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="48">\n'
            + "\n".join(groups) + "\n</svg>\n")

GLYPHS = {  # 18x18 viewbox glyph builders -> list of shapes (as segments)
  "close":    lambda c: (f'<path d="M4 4 L14 14 M14 4 L4 14" stroke="{c}" stroke-width="2.4" stroke-linecap="round" fill="none"/>'),
  "minimize": lambda c: (f'<rect x="4" y="12" width="10" height="2.4" rx="1.2" fill="{c}"/>'),
  "maximize": lambda c: (f'<rect x="4" y="4" width="10" height="10" rx="1" fill="none" stroke="{c}" stroke-width="2.2"/>'),
  "restore":  lambda c: (f'<rect x="6.5" y="4" width="7.5" height="7.5" rx="1" fill="none" stroke="{c}" stroke-width="2"/>'
                         f'<rect x="4" y="6.5" width="7.5" height="7.5" rx="1" fill="none" stroke="{c}" stroke-width="2"/>'),
}

def button_svg(kind, t):
    ghost = rgb2hex(t["fg_in"]); lit = rgb2hex(t["focus"])
    press_bg = rgb2hex(t["sel_bg"]); press_fg = rgb2hex(t["sel_fg"])
    hot = rgb2hex(t["fg_act"])
    def state(prefix, x0, glyph_color, bg=None):
        inner = (f'<rect x="1" y="1" width="16" height="16" rx="4" fill="{bg}"/>' if bg else "")
        return (f'<g id="{prefix}-center" transform="translate({x0},0)">'
                f'<rect x="0" y="0" width="18" height="18" fill="none" opacity="0"/>'
                f"{inner}{GLYPHS[kind](glyph_color)}</g>")
    states = [
        state("active", 0, ghost),
        state("hover", 20, lit),
        state("pressed", 40, press_fg, bg=press_bg),
        state("inactive", 60, ghost),
        state("hover-inactive", 80, hot),
        state("pressed-inactive", 100, press_fg, bg=press_bg),
        state("deactivated", 120, rgb2hex(t["view_alt"])),
    ]
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="140" height="18">\n'
            + "\n".join(states) + "\n</svg>\n")

def rc_text(t):
    return (f"[General]\nActiveTextColor={t['fg_act']},255\nInactiveTextColor={t['fg_in']},255\n"
            "Animation=120\nTitleAlignment=Center\nTitleVerticalAlignment=Center\n"
            "LeftButtons=M\nRightButtons=IAX\nShadow=false\n\n"
            "[Layout]\nBorderLeft=2\nBorderRight=2\nBorderBottom=2\n"
            "TitleEdgeTop=4\nTitleEdgeBottom=4\nTitleEdgeLeft=6\nTitleEdgeRight=6\n"
            "TitleBorderLeft=4\nTitleBorderRight=4\nTitleHeight=22\n"
            "ButtonWidth=22\nButtonHeight=22\nButtonSpacing=4\nButtonMarginTop=0\n"
            "ExplicitButtonSpacer=8\nPaddingTop=0\nPaddingBottom=0\nPaddingLeft=0\nPaddingRight=0\n")

def metadata_text(t):
    return ("[Desktop Entry]\n"
            f"Name={t['name']} (window decoration)\n"
            "Comment=Flat EL phosphor decoration: unlit frame, glow seam on the active titlebar\n"
            f"X-KDE-PluginInfo-Name={t['id']}\n"
            "X-KDE-PluginInfo-Author=EL watch themes\n"
            "X-KDE-PluginInfo-Version=1.0\nX-KDE-PluginInfo-License=GPLv3\n")

# ------------------------------------------------------------------ gate
def check_theme(path, tid):
    errs = []
    tree = ET.parse(os.path.join(path, "decoration.svg"))
    ids = {e.get("id") for e in tree.iter() if e.get("id")}
    for prefix in ["decoration", "decoration-inactive", "decoration-opaque", "decoration-opaque-inactive"]:
        for s in SIDES:
            if f"{prefix}-{s}" not in ids:
                errs.append(f"decoration.svg missing {prefix}-{s}")
    for extra in ["decoration-maximized-center", "decoration-maximized-inactive-center"]:
        if extra not in ids: errs.append(f"decoration.svg missing {extra}")
    for b in GLYPHS:
        btree = ET.parse(os.path.join(path, f"{b}.svg"))
        bids = {e.get("id") for e in btree.iter() if e.get("id")}
        if "active-center" not in bids:
            errs.append(f"{b}.svg missing mandatory active-center")
        for st in ["hover", "pressed", "inactive", "hover-inactive", "pressed-inactive", "deactivated"]:
            if f"{st}-center" not in bids: errs.append(f"{b}.svg missing {st}-center")
    cp = configparser.ConfigParser(); cp.optionxform = str
    cp.read(os.path.join(path, f"{tid}rc"))
    if not cp.has_section("General") or not cp.has_section("Layout"):
        errs.append("rc missing [General]/[Layout]")
    md = configparser.ConfigParser(); md.optionxform = str
    md.read(os.path.join(path, "metadata.desktop"))
    if md.get("Desktop Entry", "X-KDE-PluginInfo-Name", fallback="") != tid:
        errs.append("metadata plugin name != folder name")
    return errs

if __name__ == "__main__":
    out = "aurorae/themes"
    shutil.rmtree("aurorae", ignore_errors=True)
    failures = {}
    for (ph, mode), (t, dark) in GRID.items():
        path = os.path.join(out, t["id"]); os.makedirs(path, exist_ok=True)
        open(os.path.join(path, "decoration.svg"), "w").write(decoration_svg(t))
        for b in GLYPHS:
            open(os.path.join(path, f"{b}.svg"), "w").write(button_svg(b, t))
        open(os.path.join(path, f"{t['id']}rc"), "w").write(rc_text(t))
        open(os.path.join(path, "metadata.desktop"), "w").write(metadata_text(t))
        errs = check_theme(path, t["id"])
        if errs:
            failures[t["id"]] = errs
            shutil.rmtree(path)  # gate: violating theme is not shipped
            print(f"NOT WRITTEN: {t['id']}: {errs}")
        else:
            print("wrote", t["id"])
    sys.exit(1 if failures else 0)
