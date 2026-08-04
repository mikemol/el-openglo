#!/usr/bin/env python3
"""EL scheme generator: the knob, for the whole theme.

Emits KDE .colors and Konsole .colorscheme files for every cell of the grid
    phosphor {openglo, azure, amber} x mode {off, lit}
from per-variant token tables. 'off' = backlight off (EL segments illuminate a
black panel); 'lit' = backlight on (dark LCD occludes the glowing panel).

Run: python3 make_schemes.py [--verify]
--verify additionally diffs regenerated output against the original hand-made
.colors files (must be byte-identical) and runs a WCAG contrast audit.
"""
import sys, os

# ---------------------------------------------------------------- token tables
# Each variant: ~30 base tokens; the emitter expands them to every INI slot.
# Semantic rule: negative/neutral/positive keep meaning everywhere, but shift
# hue/value when they'd collide with the phosphor field (amber) or lose
# contrast against it (lit modes).

IND_OFF = dict(
  name="EL Openglo", id="EL-Openglo",
  view="6,11,13", view_alt="10,18,20", window="12,21,23", window_alt="10,19,21",
  button="18,34,37", button_alt="16,30,33", header="8,16,18", header_alt="10,18,20",
  hdr_in_bg="6,11,13", hdr_in_alt="8,14,16", comp="6,11,13", comp_alt="8,14,16",
  tt_bg="10,18,20", tt_alt="8,14,16",
  fg="140,232,218", fg_act="168,255,242", fg_in="61,102,96",
  link="69,216,240", visited="58,151,166",
  neg="255,110,99", neu="255,180,84", pos="85,240,160",
  focus="0,224,194", hover="26,165,147",
  sel_bg="0,205,176", sel_alt="0,180,155", sel_fg="4,33,29", sel_in="10,64,56",
  sel_link="6,58,84", sel_vis="12,66,74",
  sel_neg="120,26,20", sel_neu="110,66,8", sel_pos="8,74,40",
  fx_dis="6,11,13", fx_in="8,14,16",
  tt_is_sel=False,
)

AZR_OFF = dict(
  name="EL Azure", id="EL-Azure",
  view="5,9,14", view_alt="9,16,24", window="11,19,27", window_alt="9,17,25",
  button="18,28,42", button_alt="16,26,38", header="7,14,22", header_alt="9,16,24",
  hdr_in_bg="5,9,14", hdr_in_alt="7,12,19", comp="5,9,14", comp_alt="7,12,19",
  tt_bg="9,16,24", tt_alt="7,12,19",
  fg="138,196,242", fg_act="169,220,255", fg_in="61,85,102",
  link="79,227,232", visited="58,127,166",
  neg="255,110,99", neu="255,180,84", pos="85,240,160",
  focus="79,168,255", hover="42,111,184",
  sel_bg="61,155,240", sel_alt="52,133,210", sel_fg="4,20,35", sel_in="10,44,70",
  sel_link="12,52,92", sel_vis="14,54,88",
  sel_neg="120,26,20", sel_neu="110,66,8", sel_pos="8,74,40",
  fx_dis="5,9,14", fx_in="7,12,19",
  tt_is_sel=False,
)

AMB_OFF = dict(
  name="EL Amber", id="EL-Amber",
  view="10,7,4", view_alt="20,16,9", window="23,18,11", window_alt="21,17,10",
  button="37,29,16", button_alt="33,26,15", header="18,14,8", header_alt="20,16,9",
  hdr_in_bg="10,7,4", hdr_in_alt="16,12,7", comp="10,7,4", comp_alt="16,12,7",
  tt_bg="20,16,9", tt_alt="16,12,7",
  fg="232,196,140", fg_act="255,226,168", fg_in="102,87,61",
  link="111,216,232", visited="90,150,160",          # functional cold color
  neg="255,110,99", neu="255,235,110", pos="85,240,160",  # neutral de-collided
  focus="255,162,61", hover="184,116,40",
  sel_bg="217,154,40", sel_alt="190,133,32", sel_fg="33,23,6", sel_in="70,50,14",
  sel_link="10,70,84", sel_vis="20,60,66",
  sel_neg="120,26,20", sel_neu="92,74,6", sel_pos="8,74,40",
  fx_dis="10,7,4", fx_in="16,12,7",
  tt_is_sel=False,
)

IND_LIT = dict(
  name="EL Openglo Lit", id="EL-Openglo-Lit",
  view="175,242,226", view_alt="160,235,218", window="157,230,213", window_alt="147,222,204",
  button="138,218,203", button_alt="126,208,192", header="147,222,204", header_alt="160,235,218",
  hdr_in_bg="196,237,228", hdr_in_alt="196,237,228", comp=None, comp_alt=None,
  tt_bg="11,31,28", tt_alt="8,24,21",
  fg="10,38,34", fg_act="3,27,23", fg_in="78,138,128",
  link="6,106,138", visited="42,106,116",
  neg="166,35,24", neu="138,90,10", pos="7,102,53",
  focus="0,112,95", hover="14,138,118",
  sel_bg="11,31,28", sel_alt="8,24,21", sel_fg="124,243,223", sel_in="78,138,128",
  sel_link="124,232,255", sel_vis="140,200,210",
  sel_neg="255,154,140", sel_neu="255,204,133", sel_pos="140,247,190",
  sel_focus="0,224,194", sel_hover="26,165,147",     # dark-mode glow on the sel panel
  fx_dis="175,242,226", fx_in="196,237,228",
  tt_is_sel=True,
)

AZR_LIT = dict(
  name="EL Azure Lit", id="EL-Azure-Lit",
  view="178,220,250", view_alt="165,210,244", window="160,206,240", window_alt="150,196,232",
  button="140,188,226", button_alt="128,176,216", header="150,196,232", header_alt="165,210,244",
  hdr_in_bg="198,228,248", hdr_in_alt="198,228,248", comp=None, comp_alt=None,
  tt_bg="8,18,30", tt_alt="6,14,24",
  fg="10,26,42", fg_act="3,17,31", fg_in="74,110,140",
  link="6,120,138", visited="42,96,120",
  neg="166,35,24", neu="138,90,10", pos="7,102,53",
  focus="20,90,170", hover="28,110,190",
  sel_bg="8,18,30", sel_alt="6,14,24", sel_fg="133,203,255", sel_in="74,110,140",
  sel_link="124,240,255", sel_vis="150,196,220",
  sel_neg="255,154,140", sel_neu="255,204,133", sel_pos="140,247,190",
  sel_focus="79,168,255", sel_hover="42,111,184",
  fx_dis="178,220,250", fx_in="198,228,248",
  tt_is_sel=True,
)

AMB_LIT = dict(
  name="EL Amber Lit", id="EL-Amber-Lit",
  view="250,220,160", view_alt="242,208,142", window="238,204,138", window_alt="228,192,124",
  button="218,182,116", button_alt="205,170,105", header="228,192,124", header_alt="242,208,142",
  hdr_in_bg="250,232,196", hdr_in_alt="250,232,196", comp=None, comp_alt=None,
  tt_bg="33,23,6", tt_alt="26,18,5",
  fg="42,30,8", fg_act="30,20,4", fg_in="140,114,70",
  link="8,105,120", visited="50,95,105",
  neg="150,30,20", neu="108,86,6", pos="6,95,48",
  focus="150,92,10", hover="176,110,16",
  sel_bg="33,23,6", sel_alt="26,18,5", sel_fg="255,206,117", sel_in="140,114,70",
  sel_link="140,235,250", sel_vis="200,180,140",
  sel_neg="255,154,140", sel_neu="255,240,150", sel_pos="140,247,190",
  sel_focus="255,162,61", sel_hover="184,116,40",
  fx_dis="250,220,160", fx_in="250,232,196",
  tt_is_sel=True,
)

import os as _os
# ⊕PARAMETRIC-PALETTE: when USE_SOLVER=1, the GRID is DERIVED by solving each
# token against its constraint (make_palette), instead of the authored table
# below. The authored GRID is kept as residue (the shadow-engineer loop) and is
# the default until the solved palette is live-validated (operator=other). Flip
# the flag to re-solve every token from (hue seed x thresholds) — e.g. a
# WCAG->APCA threshold change becomes a one-line edit, not hand-chasing colors.
USE_SOLVER = _os.environ.get("USE_SOLVER") == "1"
if USE_SOLVER:
    import make_palette as _mp
    GRID = _mp.build_grid()
else:
    GRID = _AUTHORED_GRID  # noqa: F821  (defined just below as the residue table)

_AUTHORED__AUTHORED_GRID = {  # (phosphor, mode) -> (tokens, dark-counterpart for Complementary)
  ("openglo","off"): (IND_OFF, IND_OFF), ("openglo","lit"): (IND_LIT, IND_OFF),
  ("azure","off"):   (AZR_OFF, AZR_OFF), ("azure","lit"):   (AZR_LIT, AZR_OFF),
  ("amber","off"):   (AMB_OFF, AMB_OFF), ("amber","lit"):   (AMB_LIT, AMB_OFF),
}

import os as _os
# ⊕PARAMETRIC-PALETTE / ⊕SOLVER-DEFAULT (BLOCKED): the solver (make_palette) so far
# solves only the 4 DISPLAY primitives (void/lit/ghost/accent). The ~5 SEMANTIC
# tokens (neg/neu/pos/link/visited) are still generic and FAIL make_schemes' own
# hue-sector + contrast-vs-view + neg~pos-distinctness gates on the derived
# grounds. So the solved palette is NOT yet shippable as a complete scheme.
# Default stays AUTHORED (ships correct today); EL_SOLVER=1 builds the partial
# solved palette for development. Unblocks when ⊕SOLVER-SEMANTIC solves the
# semantic accents too (then flip the default — the user installs deb-only, so the
# solved palette must be the DEFAULT to be reachable at all).
if _os.environ.get("EL_SOLVER") == "1":
    import make_palette as _mp
    GRID = _mp.build_grid()
else:
    GRID = _AUTHORED_GRID

import os as _os
# ⊕PARAMETRIC-PALETTE: USE_SOLVER=1 DERIVES the GRID by solving each token against
# its constraint (make_palette) from (hue seed x thresholds), instead of the
# authored table above. Authored GRID kept as residue (shadow-engineer loop),
# default until the solved palette is live-validated (operator=other). Flipping
# the flag re-solves every token — e.g. a WCAG->APCA threshold change is then a
# one-line edit, not hand-chasing colors.
if _os.environ.get("USE_SOLVER") == "1":
    import make_palette as _mp
    GRID = _mp.build_grid()
else:
    GRID = _AUTHORED_GRID

# ---------------------------------------------------------------- .colors emit
def fgset(t):
    return (t["fg_act"], t["fg_in"], t["link"], t["neg"], t["neu"],
            t["fg"], t["pos"], t["visited"])

def section(title, bg_alt, bg, focus, hover, fgs, fg_normal_override=None):
    a, i, l, n, u, f, p, v = fgs
    if fg_normal_override: f = fg_normal_override
    return (f"[{title}]\n"
            f"BackgroundAlternate={bg_alt}\nBackgroundNormal={bg}\n"
            f"DecorationFocus={focus}\nDecorationHover={hover}\n"
            f"ForegroundActive={a}\nForegroundInactive={i}\nForegroundLink={l}\n"
            f"ForegroundNegative={n}\nForegroundNeutral={u}\nForegroundNormal={f}\n"
            f"ForegroundPositive={p}\nForegroundVisited={v}\n")

def emit_colors(t, dark):
    selfgs = (t["fg_act"], t["sel_in"], t["sel_link"], t["sel_neg"],
              t["sel_neu"], t["sel_fg"], t["sel_pos"], t["sel_vis"])
    sf = t.get("sel_focus", t["focus"]); sh = t.get("sel_hover", t["hover"])
    ttfgs = selfgs if t["tt_is_sel"] else fgset(t)
    ttf, tth = (sf, sh) if t["tt_is_sel"] else (t["focus"], t["hover"])
    comp, comp_alt = (t["comp"] or dark["comp"]), (t["comp_alt"] or dark["comp_alt"])
    parts = [
      "[ColorEffects:Disabled]\n"
      f"Color={t['fx_dis']}\nColorAmount=0.35\nColorEffect=2\nContrastAmount=0.6\n"
      "ContrastEffect=1\nIntensityAmount=-1\nIntensityEffect=0\n",
      "[ColorEffects:Inactive]\nChangeSelectionColor=true\n"
      f"Color={t['fx_in']}\nColorAmount=0.2\nColorEffect=2\nContrastAmount=0.25\n"
      "ContrastEffect=2\nEnable=true\nIntensityAmount=0\nIntensityEffect=0\n",
      section("Colors:Button", t["button_alt"], t["button"], t["focus"], t["hover"], fgset(t)),
      section("Colors:Complementary", comp_alt, comp, dark["focus"], dark["hover"], fgset(dark)),
      section("Colors:Header", t["header_alt"], t["header"], t["focus"], t["hover"], fgset(t)),
      section("Colors:Header][Inactive", t["hdr_in_alt"], t["hdr_in_bg"], t["focus"],
              t["hover"], fgset(t), fg_normal_override=t["fg_in"]),
      section("Colors:Selection", t["sel_alt"], t["sel_bg"], sf, sh, selfgs),
      section("Colors:Tooltip", t["tt_alt"], t["tt_bg"], ttf, tth, ttfgs),
      section("Colors:View", t["view_alt"], t["view"], t["focus"], t["hover"], fgset(t)),
      section("Colors:Window", t["window_alt"], t["window"], t["focus"], t["hover"], fgset(t)),
      f"[General]\nColorScheme={t['id']}\nName={t['name']}\nshadeSortColumn=true\n",
      "[KDE]\ncontrast=4\n",
      f"[WM]\nactiveBackground={t['window']}\nactiveBlend={t['focus']}\n"
      f"activeForeground={t['fg_act']}\n"
      f"inactiveBackground={t['hdr_in_bg'] if t['tt_is_sel'] else t['view']}\n"
      f"inactiveBlend={t['fg_in']}\ninactiveForeground={t['fg_in']}\n",
    ]
    return "\n".join(parts)

# ------------------------------------------------------------- konsole emit
def rgb(s): return tuple(int(x) for x in s.split(","))
def mix(a, b, k): return tuple(round(x + (y - x) * k) for x, y in zip(rgb(a) if isinstance(a,str) else a, rgb(b) if isinstance(b,str) else b))
def s3(c): return ",".join(map(str, c))

ANSI = {  # variant id -> (c0, c1..c7 bases); fg/bg pulled from token table
  "EL-Openglo":    ("10,18,20","255,110,99","85,240,160","255,180,84","79,168,232","176,140,232","0,224,194","140,232,218"),
  "EL-Azure":      ("9,16,24","255,110,99","85,240,160","255,180,84","79,168,255","176,140,232","79,227,232","138,196,242"),
  "EL-Amber":      ("20,16,9","255,110,99","85,240,160","255,235,110","100,170,235","176,140,232","111,216,232","232,196,140"),
  "EL-Openglo-Lit":("11,31,28","166,35,24","10,122,66","138,90,10","10,90,154","106,58,154","0,112,95","96,160,150"),
  "EL-Azure-Lit":  ("8,18,30","166,35,24","10,122,66","138,90,10","20,90,170","106,58,154","6,120,138","90,140,170"),
  "EL-Amber-Lit":  ("33,23,6","150,30,20","6,95,48","108,86,6","20,80,150","100,55,145","8,105,120","150,120,80"),
}

def emit_konsole(t):
    lit = t["tt_is_sel"]
    bg, fg = t["view"], t["fg"]
    cols = ANSI[t["id"]]
    out = [f"[Background]\nColor={bg}\n", f"[BackgroundFaint]\nColor={bg}\n",
           f"[BackgroundIntense]\nColor={t['view_alt']}\n"]
    for i, base in enumerate(cols):
        if i == 0:
            faint = s3(mix(base, bg, 0.35)); intense = t["fg_act"] if lit else s3(mix(base, "255,255,255", 0.12))
        else:
            faint = s3(mix(base, bg, 0.45 if lit else 0.48))
            intense = s3(mix(base, "255,255,255", 0.18 if lit else 0.35))
        out.append(f"[Color{i}]\nColor={base}\n")
        out.append(f"[Color{i}Faint]\nColor={faint}\n")
        out.append(f"[Color{i}Intense]\nColor={intense}\n")
    out += [f"[Foreground]\nColor={fg}\n",
            f"[ForegroundFaint]\nColor={s3(mix(fg, bg, 0.35))}\n",
            f"[ForegroundIntense]\nColor={t['fg_act']}\n",
            "[General]\nAnchors=0.5,0.5\nBlur=false\nColorRandomization=false\n"
            f"Description={t['name']}\nFillStyle=Tile\nOpacity=1\nWallpaper=\n"
            "WallpaperFlipType=NoFlip\nWallpaperOpacity=1\n"]
    return "\n".join(out)

# ------------------------------------------------------------------ audit
def lum(c):
    def f(v):
        v /= 255
        return v/12.92 if v <= 0.03928 else ((v+0.055)/1.055)**2.4
    r, g, b = c
    return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)

def ratio(a, b):
    la, lb = sorted((lum(rgb(a)), lum(rgb(b))), reverse=True)
    return (la+0.05)/(lb+0.05)

def audit(t):
    rows = [("body/view", t["fg"], t["view"]), ("body/button", t["fg"], t["button"]),
            ("link/view", t["link"], t["view"]), ("neg/view", t["neg"], t["view"]),
            ("neu/view", t["neu"], t["view"]), ("pos/view", t["pos"], t["view"]),
            ("sel", t["sel_fg"], t["sel_bg"])]
    bad = []
    for name, f, b in rows:
        r = ratio(f, b)
        flag = "" if r >= 4.5 else (" *" if r >= 3 else " FAIL")
        if r < 4.5: bad.append((name, round(r, 2)))
        print(f"  {t['id']:16s} {name:12s} {r:5.2f}:1{flag}")
    return bad

# -------------------------------------------------------------------- main
if __name__ == "__main__":
    verify = "--verify" in sys.argv
    for (ph, mode), (t, dark) in GRID.items():
        open(f"{t['id']}.colors", "w").write(emit_colors(t, dark))
        open(f"{t['id']}.colorscheme", "w").write(emit_konsole(t))
        print("wrote", t["id"])
    if verify:
        print("\n-- byte-exact check vs hand-made .colors --")
        import subprocess
        for f in ["EL-Openglo.colors", "EL-Azure.colors", "EL-Openglo-Lit.colors"]:
            r = subprocess.run(["git", "diff", "--no-index", "--stat", f"/tmp/hand/{f}", f],
                               capture_output=True, text=True)
            print(f, "IDENTICAL" if r.returncode == 0 else "DIFFERS")
        print("\n-- WCAG audit --")
        for (ph, mode), (t, d) in GRID.items():
            audit(t)
