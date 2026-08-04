#!/usr/bin/env python3
"""Kvantum widget styles for the EL grid.

Strategy: substrate = KvFlat (complete, proven element set, fetched from the
Kvantum repo) recolored onto our tokens — grays through a phosphor-tinted
lightness ramp, chromatic accents through an explicit map — plus an appended
`elprogress` element family: the segmented LCD progress bar, wired in by
config override. No reliance on missing-element fallback.

Gate on every generation: kvconfig parses; every element referenced by the
config resolves in the SVG; the appended family is state/part complete; no
substrate accent hex survives recoloring. Violating themes deleted."""
import os, re, sys, shutil, colorsys, configparser
import xml.etree.ElementTree as ET
from make_schemes import GRID

SUB_CFG = open("/tmp/KvFlat.kvconfig").read()
SUB_SVG = open("/tmp/KvFlat.svg").read()

def rgbT(t, k): return tuple(int(x) for x in t[k].split(","))
def hexs(c): return "#%02x%02x%02x" % tuple(c)

ACCENTS = {  # KvFlat chromatic tokens -> our token keys
    "#3f67a5": "sel_bg", "#2e4c7a": "hover", "#2EB8E6": "link", "#FF6666": "neg",
}

def make_mapper(t, lit):
    h_p, s_p, _ = colorsys.rgb_to_hls(*[v/255 for v in rgbT(t, "focus")])
    def gray_map(v):  # v in 0..1 (substrate lightness)
        L = (0.96 - 0.86 * v) if lit else (v * 0.92 + 0.02)
        s = 0.10 + 0.14 * (1 - abs(2*L - 1))
        r, g, b = colorsys.hls_to_rgb(h_p, L, s)
        return "#%02x%02x%02x" % (round(r*255), round(g*255), round(b*255))
    def map_hex(m):
        hx = m.group(0)
        low = hx.lower()
        for a, key in ACCENTS.items():
            if low == a.lower(): return hexs(rgbT(t, key))
        r, g, b = int(hx[1:3],16), int(hx[3:5],16), int(hx[5:7],16)
        if max(r,g,b) - min(r,g,b) < 14:                # grayscale
            return gray_map((r+g+b)/765.0)
        return hx
    return map_hex

PARTS = ["top","bottom","left","right","topleft","topright","bottomleft","bottomright"]
STATES = ["normal","focused","pressed","toggled","disabled"]

def elprogress_family(t):
    """LCD segment tile: 6px lit segment + 3px gap, tiled by Kvantum."""
    seg, groove = hexs(rgbT(t, "focus")), hexs(rgbT(t, "view"))
    out = []
    y = 0
    for st in STATES:
        color = seg if st != "disabled" else hexs(rgbT(t, "fg_in"))
        out.append(f'<g id="elprogress-{st}"><rect x="0" y="{y}" width="9" height="16" fill="{groove}"/>'
                   f'<rect x="1" y="{y+2}" width="6" height="12" rx="1" fill="{color}"/></g>')
        for p in PARTS:
            out.append(f'<rect id="elprogress-{st}-{p}" x="12" y="{y}" width="1" height="1" fill="none" opacity="0"/>')
        y += 20
    return "\n".join(out)

def build(t, lit):
    mapper = make_mapper(t, lit)
    svg = re.sub(r"#[0-9a-fA-F]{6}", mapper, SUB_SVG)
    svg = svg.replace("</svg>", elprogress_family(t) + "\n</svg>")
    cfg = re.sub(r"#[0-9a-fA-F]{6}", mapper, SUB_CFG)
    cfg = cfg.replace("=white", "=" + hexs(rgbT(t, "fg")))
    cfg = cfg.replace("author=Tsu Jan", f"author=EL watch themes (KvFlat substrate by Tsu Jan)")
    cfg = cfg.replace("comment=A dark flat theme inspired by Breeze",
                      f"comment={t['name']} — EL phosphor widgets on the KvFlat substrate")
    cfg = re.sub(r"\[ProgressbarContents\]\ninherits=PanelButtonCommand\nframe=true\n"
                 r"frame\.element=progress-pattern\ninterior\.element=progress-pattern",
                 "[ProgressbarContents]\ninherits=PanelButtonCommand\nframe=true\n"
                 "frame.element=elprogress\ninterior.element=elprogress", cfg)
    cfg = cfg.replace("progressbar_thickness=3font", "progressbar_thickness=10")
    # GeneralColors: rewrite wholesale from tokens
    gc = {"window.color": "window", "base.color": "view", "alt.base.color": "view_alt",
          "button.color": "button", "light.color": "button_alt", "mid.light.color": "button",
          "dark.color": "view", "mid.color": "window_alt", "highlight.color": "sel_bg",
          "inactive.highlight.color": "hover", "text.color": "fg", "window.text.color": "fg",
          "button.text.color": "fg", "disabled.text.color": "fg_in", "tooltip.text.color": "fg_act",
          "highlight.text.color": "sel_fg", "link.color": "link", "link.visited.color": "visited"}
    for k, tok in gc.items():
        cfg = re.sub(rf"^{re.escape(k)}=.*$", f"{k}={hexs(rgbT(t, tok))}", cfg, flags=re.M)
    return cfg, svg

def check(cfg, svg, t):
    errs = []
    cp = configparser.ConfigParser(strict=False, interpolation=None); cp.optionxform = str
    try: cp.read_string(cfg)
    except Exception as e: errs.append(f"kvconfig parse: {e}"); return errs
    ids = set(re.findall(r'id="([^"]+)"', svg))
    for name in set(re.findall(r"element=([A-Za-z-]+)", cfg)):
        if f"{name}-normal" not in ids and not any(i.startswith(name + "-normal-") for i in ids):
            errs.append(f"config references '{name}' but no {name}-normal* in svg")
    for st in STATES:
        if f"elprogress-{st}" not in ids: errs.append(f"missing elprogress-{st}")
        for p in PARTS:
            if f"elprogress-{st}-{p}" not in ids: errs.append(f"missing elprogress-{st}-{p}")
    for a in ACCENTS:
        if a.lower() in svg.lower(): errs.append(f"substrate accent {a} survived recolor")
    return errs

if __name__ == "__main__":
    shutil.rmtree("kvantum", ignore_errors=True)
    failures = {}
    for (ph, mode), (t, dark) in GRID.items():
        lit = t["tt_is_sel"]
        cfg, svg = build(t, lit)
        errs = check(cfg, svg, t)
        path = f"kvantum/{t['id']}"
        if errs:
            failures[t["id"]] = errs
            print(f"NOT WRITTEN: {t['id']}: {errs[:3]}")
            continue
        os.makedirs(path, exist_ok=True)
        open(f"{path}/{t['id']}.kvconfig", "w").write(cfg)
        open(f"{path}/{t['id']}.svg", "w").write(svg)
        print("wrote", t["id"])
    sys.exit(1 if failures else 0)
