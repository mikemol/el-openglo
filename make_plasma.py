#!/usr/bin/env python3
"""Plasma Styles for the EL grid — panel, dialog, tooltip; everything else
inherits the default theme, recolored by the bundled colors file (the
breeze-light/-dark pattern, per develop.kde.org/docs/plasma/theme/).

Emits plasma/desktoptheme/<id>/ per grid cell. Checklist gate runs on every
generation: 9-part frames + mask frames present, colors file byte-derived
from make_schemes.emit_colors minus [ColorEffects:*], metadata Id == folder.
Violating themes are deleted, not shipped."""
import os, sys, json, shutil, re
import xml.etree.ElementTree as ET
from make_schemes import GRID, emit_colors

def hexc(s):
    r, g, b = s.split(",")
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"

POS = ["topleft", "top", "topright", "left", "center", "right",
       "bottomleft", "bottom", "bottomright"]

def frame(prefix, fill, r=0, x0=0, y0=0, edge=None):
    """9-part FrameSvg. r>0 rounds the outer corners. edge = 1px top
    hairline color (panel definition line). prefix '' = default frame."""
    p = (prefix + "-") if prefix else ""
    b, c = 8, 24  # border, center sizes
    out = []
    def rect(sid, x, y, w, h, rx=0):
        out.append(f'<rect id="{p}{sid}" x="{x0+x}" y="{y0+y}" width="{w}" height="{h}"'
                   + (f' rx="{rx}"' if rx else "") + f' fill="{fill}"/>')
    if r:
        out.append(f'<path id="{p}topleft" d="M {x0} {y0+b} L {x0} {y0+r} Q {x0} {y0} {x0+r} {y0} L {x0+b} {y0} L {x0+b} {y0+b} Z" fill="{fill}"/>')
        rect("top", b, 0, c, b)
        out.append(f'<path id="{p}topright" d="M {x0+b+c} {y0} L {x0+2*b+c-r} {y0} Q {x0+2*b+c} {y0} {x0+2*b+c} {y0+r} L {x0+2*b+c} {y0+b} L {x0+b+c} {y0+b} Z" fill="{fill}"/>')
        rect("left", 0, b, b, c); rect("center", b, b, c, c); rect("right", b + c, b, b, c)
        out.append(f'<path id="{p}bottomleft" d="M {x0} {y0+b+c} L {x0+b} {y0+b+c} L {x0+b} {y0+2*b+c} L {x0+r} {y0+2*b+c} Q {x0} {y0+2*b+c} {x0} {y0+2*b+c-r} Z" fill="{fill}"/>')
        rect("bottom", b, b + c, c, b)
        out.append(f'<path id="{p}bottomright" d="M {x0+b+c} {y0+b+c} L {x0+2*b+c} {y0+b+c} L {x0+2*b+c} {y0+2*b+c-r} Q {x0+2*b+c} {y0+2*b+c} {x0+2*b+c-r} {y0+2*b+c} L {x0+b+c} {y0+2*b+c} Z" fill="{fill}"/>')
    else:
        rect("topleft", 0, 0, b, b); rect("top", b, 0, c, b); rect("topright", b + c, 0, b, b)
        rect("left", 0, b, b, c); rect("center", b, b, c, c); rect("right", b + c, b, b, c)
        rect("bottomleft", 0, b + c, b, b); rect("bottom", b, b + c, c, b); rect("bottomright", b + c, b + c, b, b)
    if edge:
        out.append(f'<rect x="{x0}" y="{y0}" width="{2*b+c}" height="1" fill="{edge}"/>')
    return "\n".join(out)

def svg(*groups, w=100, h=100):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">\n'
            + "\n".join(groups) + "\n</svg>\n")

def panel_svg(t, square=False):
    fill = hexc(t["view"]); edge = hexc(t["view_alt"])
    return svg(frame("", fill, 0, 0, 0, edge=edge),
               frame("mask", "#000000", 0, 50, 0),
               w=100, h=44)

def dialog_svg(t, square=False):
    r = 0 if square else 6
    fill = hexc(t["window"])
    return svg(frame("", fill, r, 0, 0),
               frame("mask", "#000000", r, 50, 0),
               w=100, h=44)

def tooltip_svg(t, square=False):
    r = 0 if square else 4
    fill = hexc(t["tt_bg"])
    return svg(frame("", fill, r, 0, 0),
               frame("mask", "#000000", r, 50, 0),
               w=100, h=44)

def metadata(t):
    return json.dumps({"KPlugin": {
        "Authors": [{"Name": "EL watch themes"}],
        "Name": f"{t['name']}", "Description": "Flat EL phosphor Plasma Style",
        "Id": t["id"], "Version": "1.0", "License": "GPLv3",
        "EnabledByDefault": True}, "X-Plasma-API": "5.0"}, indent=1)

def colors_file(t, dark):
    txt = emit_colors(t, dark)
    # per spec: everything EXCEPT the [ColorEffects:*] sections
    return re.sub(r"\[ColorEffects:[^\]]*\]\n(?:[^\[\n][^\n]*\n)*\n?", "", txt)

FILES = {  # relpath -> builder(t, square)
    "widgets/panel-background.svg": panel_svg,
    "solid/widgets/panel-background.svg": lambda t, s=True: panel_svg(t, True),
    "dialogs/background.svg": dialog_svg,
    "solid/dialogs/background.svg": lambda t, s=True: dialog_svg(t, True),
    "widgets/tooltip.svg": tooltip_svg,
    "solid/widgets/tooltip.svg": lambda t, s=True: tooltip_svg(t, True),
}

def check(path, t, dark):
    errs = []
    for rel in FILES:
        tree = ET.parse(os.path.join(path, rel))
        ids = {e.get("id") for e in tree.iter() if e.get("id")}
        for pos in POS:
            if pos not in ids: errs.append(f"{rel}: missing {pos}")
            if f"mask-{pos}" not in ids: errs.append(f"{rel}: missing mask-{pos}")
    md = json.load(open(os.path.join(path, "metadata.json")))
    if md["KPlugin"]["Id"] != t["id"]: errs.append("metadata Id != folder")
    want = colors_file(t, dark)
    if open(os.path.join(path, "colors")).read() != want:
        errs.append("colors file not byte-derived from emit_colors")
    if "[ColorEffects" in want: errs.append("ColorEffects sections not stripped")
    return errs

if __name__ == "__main__":
    shutil.rmtree("plasma", ignore_errors=True)
    failures = {}
    for (ph, mode), (t, dark) in GRID.items():
        path = f"plasma/desktoptheme/{t['id']}"
        for rel, builder in FILES.items():
            os.makedirs(os.path.dirname(os.path.join(path, rel)), exist_ok=True)
            open(os.path.join(path, rel), "w").write(builder(t))
        open(os.path.join(path, "metadata.json"), "w").write(metadata(t))
        open(os.path.join(path, "colors"), "w").write(colors_file(t, dark))
        errs = check(path, t, dark)
        if errs:
            failures[t["id"]] = errs; shutil.rmtree(path)
            print(f"NOT WRITTEN: {t['id']}: {errs[:3]}")
        else:
            print("wrote", t["id"])
    sys.exit(1 if failures else 0)
