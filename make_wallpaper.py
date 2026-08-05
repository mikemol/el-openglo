#!/usr/bin/env python3
"""EL-Openglo wallpaper generator.

Draws a seven-segment watch face: the full 'ghost' segment field (every LCD
segment faintly present, as on a real watch) with 12:00 lit over it -- the
just-reset flashing clock. Emits SVG, and a PNG if cairosvg is available.
"""

W, H = 3840, 2160

# ⚑ THE COLOURS ARE SOURCED, NOT SPELLED.  This is the OLDEST generator — it
# predates make_preview/make_schemes, so it grew its own hexes, and it was the
# one emitter of ten still doing so.  That is precisely the drift the
# one-palette design exists to prevent: a target with private colours silently
# stops matching the theme when the palette is re-solved.  Measured by
# scripts/check_token_source.py, which is why this is wired rather than noted.
#
# The literals remain as the FALLBACK, so the wallpaper still renders standalone
# (no scheme file, no cairosvg install) — and they are exactly the values this
# file used before, so sourcing is appearance-neutral by construction.
_FALLBACK = {"ground": "#04080A", "panel": "#081114", "ghost": "#152826",
             "lit": "#66F5DF", "accent": "#00E0C2"}


def _tokens(variant="EL-Openglo"):
    """Palette tokens from the scheme, falling back to this file's own literals."""
    try:
        import make_preview as MP
        c = MP.parse_scheme(variant)
        return {"ground": c["ground"], "panel": c.get("panel", c["ground"]),
                "ghost": _FALLBACK["ghost"],      # ghost is derived, not a scheme key
                "lit": c["phosphor"], "accent": c["accent"]}
    except Exception:                              # noqa: BLE001 - any absence
        return dict(_FALLBACK)


_C = _tokens()
BG_EDGE = _C["ground"]
BG_MID = _C["panel"]
GHOST = _C["ghost"]        # unlit segment
LIT = _C["lit"]            # lit segment core
GLOW = _C["accent"]        # phosphor glow

# seven-segment geometry -----------------------------------------------------
# ⚑ DERIVED FROM THE SUBSTRATE, NOT OWNED HERE (⊕SEGMENT-SUBSTRATE).
#
# These were two hand-authored tables, and three other surfaces carried their own
# copies of the same shapes — the defect the design log names outright:
# "GEOMETRY IS A TOKEN SET EXACTLY LIKE COLOR. I did this for COLOR (palette
# solver feeds all) but NOT for GEOMETRY." make_clock went further and re-read
# THESE tables out of this file's SOURCE with a regex at import time.
#
# segment_topology is the one lattice; a surface chooses a FORMAT, never a shape.
# The wallpaper is digits-only, so it projects to "7".
#
# ⚑ THE RENAME IS THE SUBSTRATE'S OWN, NOT A TRANSLATION LAYER.  The substrate
# labels 7-seg strokes a..g; this file's SVG has always used A..G, and
# segment_topology carries SEG7_RENAME/glyph7_letters precisely so the two agree.
# Its selftest asserts the projection is BYTE-EQUAL to the table that used to
# live here, which is what makes this replacement provably behaviour-preserving
# rather than a re-derivation that happens to look right.
import segment_topology as _ST

SEGS = _ST.seg7_svg_grid()
DIGIT = {ch: _ST.glyph7_letters(ch) for ch in "0123456789"}

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
def wallpaper_svg():
    """The wallpaper as an SVG string — no file written, nothing printed.

    ⚑ THIS WAS MODULE-LEVEL CODE, WHICH MADE THE WALLPAPER UNSAMPLEABLE.  The
    whole render ran on IMPORT and wrote EL-Openglo-wallpaper.svg as a side
    effect, so the only way to see it was to run the module and read a file whose
    name it chose. The sample library therefore had no wallpaper at all: its
    renderer called a `wallpaper_svg()` that did not exist, and the surface
    stayed silently absent from the thing built for looking at surfaces.

    Building it now RETURNS; __main__ still writes the files it always wrote.
    """
    ghost_big, wb = clock("88:88", 0, 0, L, T, GHOST, ghost_all=True)
    lit_big, _ = clock("12:00", 0, 0, L, T, LIT)
    ghost_sec, ws = clock("88", 0, 0, Ls, Ts, GHOST, ghost_all=True)
    lit_sec, _ = clock("00", 0, 0, Ls, Ts, LIT)

    total_w = wb + 90 + ws
    ox = (W - total_w) / 2
    oy = (H - 2 * L) / 2
    sec_x, sec_y = ox + wb + 90, oy + 2 * L - 2 * Ls

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
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

if __name__ == "__main__":
    # ⚑ THE SIDE EFFECTS LIVE HERE NOW, NOT AT IMPORT.  A module that writes
    # files and prints when merely imported cannot be sampled, tested, or
    # composed — every consumer inherits its filenames and its stdout.
    svg = wallpaper_svg()
    open("EL-Openglo-wallpaper.svg", "w").write(svg)
    print("wrote SVG")
    try:
        import cairosvg
        cairosvg.svg2png(url="EL-Openglo-wallpaper.svg",
                         write_to="EL-Openglo-wallpaper.png",
                         output_width=2560, output_height=1440)
        cairosvg.svg2png(url="EL-Openglo-wallpaper.svg",
                         write_to="preview.png", output_width=1280, output_height=720)
        print("wrote PNGs")
    except Exception as e:
        print("no PNG:", e)
