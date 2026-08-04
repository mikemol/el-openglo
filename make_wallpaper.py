#!/usr/bin/env python3
"""EL-Indiglo wallpaper generator.

Draws a seven-segment watch face: the full 'ghost' segment field (every LCD
segment faintly present, as on a real watch) with 12:00 lit over it -- the
just-reset flashing clock. Emits SVG, and a PNG if cairosvg is available.
"""

W, H = 3840, 2160
BG_EDGE = "#04080A"
BG_MID = "#081114"
GHOST = "#152826"          # unlit segment
LIT = "#66F5DF"            # lit segment core
GLOW = "#00E0C2"           # phosphor glow

# seven-segment geometry -----------------------------------------------------
SEGS = {  # (kind, x, y) in units of L; kind h/v; origin = digit top-left
    "A": ("h", 0, 0), "G": ("h", 0, 1), "D": ("h", 0, 2),
    "F": ("v", 0, 0), "B": ("v", 1, 0), "E": ("v", 0, 1), "C": ("v", 1, 1),
}
DIGIT = {
    "0": "ABCDEF", "1": "BC", "2": "ABGED", "3": "ABGCD", "4": "FGBC",
    "5": "AFGCD", "6": "AFGEDC", "7": "ABC", "8": "ABCDEFG", "9": "ABCFGD",
}

def seg_poly(kind, L, t, gap):
    h = t / 2.0
    a, b = gap, L - gap
    pts = [(a, 0), (a + h, -h), (b - h, -h), (b, 0), (b - h, h), (a + h, h)]
    if kind == "v":
        pts = [(y, x) for (x, y) in pts]
    return pts

def digit_svg(ch, x, y, L, t, on_color, segs=None):
    """One digit at (x,y); segs overrides which segments to draw."""
    want = segs if segs is not None else DIGIT.get(ch, "")
    out = []
    for name in want:
        kind, ux, uy = SEGS[name]
        pts = seg_poly(kind, L, t, t * 0.62)
        px, py = x + ux * L, y + uy * L
        p = " ".join(f"{px+dx:.1f},{py+dy:.1f}" for dx, dy in pts)
        out.append(f'<polygon points="{p}" fill="{on_color}"/>')
    return "".join(out)

def clock(text, x, y, L, t, color, ghost_all=False):
    """Render a HH:MM string; ':' becomes dots, digits advance the cursor."""
    out, cx = [], x
    adv = L * 1.55
    for ch in text:
        if ch == ":":
            r = t * 0.62
            for dy in (L * 0.62, L * 1.38):
                out.append(f'<rect x="{cx:.1f}" y="{y+dy-r:.1f}" '
                           f'width="{2*r:.1f}" height="{2*r:.1f}" fill="{color}"/>')
            cx += L * 0.72
        else:
            segs = "ABCDEFG" if ghost_all else None
            out.append(digit_svg(ch, cx, y, L, t, color, segs))
            cx += adv
    return "".join(out), cx - x

L, T = 340, 62                       # segment length / thickness (big digits)
Ls, Ts = 150, 30                     # seconds digits
ghost_big, wb = clock("88:88", 0, 0, L, T, GHOST, ghost_all=True)
lit_big, _ = clock("12:00", 0, 0, L, T, LIT)
ghost_sec, ws = clock("88", 0, 0, Ls, Ts, GHOST, ghost_all=True)
lit_sec, _ = clock("00", 0, 0, Ls, Ts, LIT)

total_w = wb + 90 + ws
ox = (W - total_w) / 2
oy = (H - 2 * L) / 2
sec_x, sec_y = ox + wb + 90, oy + 2 * L - 2 * Ls

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <radialGradient id="panel" cx="50%" cy="46%" r="75%">
    <stop offset="0%" stop-color="{BG_MID}"/>
    <stop offset="100%" stop-color="{BG_EDGE}"/>
  </radialGradient>
  <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="22" result="b1"/>
    <feFlood flood-color="{GLOW}" flood-opacity="0.55"/>
    <feComposite in2="b1" operator="in" result="halo"/>
    <feGaussianBlur in="SourceGraphic" stdDeviation="3" result="soft"/>
    <feMerge><feMergeNode in="halo"/><feMergeNode in="halo"/>
      <feMergeNode in="soft"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect width="{W}" height="{H}" fill="url(#panel)"/>
<g transform="translate({ox:.0f},{oy:.0f}) skewX(-5)">{ghost_big}</g>
<g transform="translate({sec_x:.0f},{sec_y:.0f}) skewX(-5)">{ghost_sec}</g>
<g transform="translate({ox:.0f},{oy:.0f}) skewX(-5)" filter="url(#glow)">{lit_big}</g>
<g transform="translate({sec_x:.0f},{sec_y:.0f}) skewX(-5)" filter="url(#glow)">{lit_sec}</g>
<g font-family="monospace" font-size="54" letter-spacing="14">
  <text x="{ox:.0f}" y="{oy-80:.0f}" fill="{GHOST}">ALARM  CHIME  24HR</text>
  <text x="{ox:.0f}" y="{oy-80:.0f}" fill="{LIT}" filter="url(#glow)">AL</text>
</g>
</svg>'''

open("EL-Indiglo-wallpaper.svg", "w").write(svg)
print("wrote SVG")
try:
    import cairosvg
    cairosvg.svg2png(url="EL-Indiglo-wallpaper.svg",
                     write_to="EL-Indiglo-wallpaper.png",
                     output_width=2560, output_height=1440)
    cairosvg.svg2png(url="EL-Indiglo-wallpaper.svg",
                     write_to="preview.png", output_width=1280, output_height=720)
    print("wrote PNGs")
except Exception as e:
    print("no PNG:", e)
