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


VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
            "EL-Amber", "EL-Amber-Lit")


def _tokens(variant="EL-Openglo"):
    """Palette tokens from the scheme, falling back to this file's own literals.

    ⚑ THE GHOST IS THE SCHEME'S, AT THE GLANCED ALPHA.  This read
    `_FALLBACK["ghost"]` with the note "ghost is derived, not a scheme key" —
    true once, false since W8: the scheme carries ForegroundInactive (the solved
    fg_in) and [EL] GhostAlphaGlanced (a wallpaper is glanced-at, relations §3c).
    That literal was the EIGHTH ghost model in the tree, and the only one no
    check could see because this generator emitted one variant behind an
    `exists` guard."""
    try:
        import make_preview as MP
        c = MP.parse_scheme(variant)
        return {"ground": c["ground"], "panel": c.get("panel", c["ground"]),
                "ghost": c["ghost"], "ghost_alpha": c["ghost_alpha_glanced"],
                "lit": c["phosphor"], "accent": c["accent"]}
    except Exception:                              # noqa: BLE001 - any absence
        return dict(_FALLBACK, ghost_alpha=1.0)


def output_name(variant):
    """`<Base>-wallpaper.png` / `<Base>-lit-wallpaper.png` — the names make_deb maps."""
    base = variant[:-4] if variant.endswith("-Lit") else variant
    return f"{base}{'-lit' if variant.endswith('-Lit') else ''}-wallpaper"

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
from emitters import atomic_path, atomic_write

SEGS = _ST.seg7_svg_grid()
DIGIT = {ch: _ST.glyph7_letters(ch) for ch in "0123456789"}

def seg_poly(kind, L, t, gap):
    h = t / 2.0
    a, b = gap, L - gap
    pts = [(a, 0), (a + h, -h), (b - h, -h), (b, 0), (b - h, h), (a + h, h)]
    if kind == "v":
        pts = [(y, x) for (x, y) in pts]
    return pts

def digit_svg(ch, x, y, L, t, on_color, segs=None, opacity=1.0):
    """One digit at (x,y); segs overrides which segments to draw."""
    want = segs if segs is not None else DIGIT.get(ch, "")
    out = []
    op = "" if opacity >= 1.0 else f' fill-opacity="{opacity:.3f}"'
    for name in want:
        kind, ux, uy = SEGS[name]
        pts = seg_poly(kind, L, t, t * 0.62)
        px, py = x + ux * L, y + uy * L
        p = " ".join(f"{px+dx:.1f},{py+dy:.1f}" for dx, dy in pts)
        out.append(f'<polygon points="{p}" fill="{on_color}"{op}/>')
    return "".join(out)

def clock(text, x, y, L, t, color, ghost_all=False, opacity=1.0):
    """Render a HH:MM string; ':' becomes dots, digits advance the cursor."""
    out, cx = [], x
    # the digit is L wide, 2L tall: pitch, dot and colon advance are the
    # substrate's module metrics in L (segment_topology.MODULE_METRICS). This
    # authored 1.55L and a 0.72L colon slot; the module says 1.786L and none.
    m = _ST.metrics(2.0)
    adv = L * m["pitch"]
    op = "" if opacity >= 1.0 else f' fill-opacity="{opacity:.3f}"'
    for ch in text:
        if ch == ":":
            r = L * m["dot"] / 2
            # centred in the gap the previous digit left, plus any colon advance
            dx = -(adv - L) / 2 + L * m["colon_advance"] / 2
            for dy in (L * 0.62, L * 1.38):
                out.append(f'<rect x="{cx+dx-r:.1f}" y="{y+dy-r:.1f}" '
                           f'width="{2*r:.1f}" height="{2*r:.1f}" fill="{color}"{op}/>')
            cx += L * m["colon_advance"]
        else:
            segs = "ABCDEFG" if ghost_all else None
            out.append(digit_svg(ch, cx, y, L, t, color, segs, opacity))
            cx += adv
    return "".join(out), cx - x

L, T = 340, 62                       # segment length / thickness (big digits)
Ls, Ts = 150, 30                     # seconds digits
def wallpaper_svg(variant="EL-Openglo"):
    """The wallpaper for `variant` as an SVG string — no file written, nothing printed.

    ⚑ THIS WAS MODULE-LEVEL CODE, WHICH MADE THE WALLPAPER UNSAMPLEABLE.  The
    whole render ran on IMPORT and wrote EL-Openglo-wallpaper.svg as a side
    effect, so the only way to see it was to run the module and read a file whose
    name it chose. The sample library therefore had no wallpaper at all: its
    renderer called a `wallpaper_svg()` that did not exist, and the surface
    stayed silently absent from the thing built for looking at surfaces.

    ⚑ AND IT WAS ONE VARIANT.  The colours were module globals read once at
    import, so only EL-Openglo ever got a wallpaper; make_deb's `exists` guard
    made the other five variants' absence look like a choice. Measured when the
    ebuild's staging refused by name (2026-09-21). Every colour is now an
    argument of the variant, and the ghost composites at the glanced alpha
    through fill-opacity — the same seen-ghost the other surfaces draw.
    """
    c = _tokens(variant)
    BG_EDGE, BG_MID, GHOST, LIT, GLOW = (c["ground"], c["panel"], c["ghost"],
                                         c["lit"], c["accent"])
    ga = float(c["ghost_alpha"])
    ghost_big, wb = clock("88:88", 0, 0, L, T, GHOST, ghost_all=True, opacity=ga)
    lit_big, _ = clock("12:00", 0, 0, L, T, LIT)
    ghost_sec, ws = clock("88", 0, 0, Ls, Ts, GHOST, ghost_all=True, opacity=ga)
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
    # Every variant, named as make_deb.system_mapping expects them.
    # ⚑ AN UNKNOWN FLAG IS REFUSED (W68): check_action_key's `--keys` / `--outputs`
    # probes ran this emission in the real tree because every flag was ignored.
    import sys
    if sys.argv[1:]:
        print(f"make_wallpaper: unknown flag(s) {sys.argv[1:]} (no modes; run bare to emit)",
              file=sys.stderr)
        sys.exit(2)
    try:
        import cairosvg
    except ImportError:                             # the SVGs still land
        cairosvg = None
        print("make_wallpaper: SKIP PNG — cairosvg not importable; SVGs written")
    for v in VARIANTS:
        name = output_name(v)
        svg = wallpaper_svg(v)
        atomic_write(f"{name}.svg", svg)
        if cairosvg is not None:
            with atomic_path(f"{name}.png") as tmp:
                cairosvg.svg2png(url=f"{name}.svg", write_to=tmp,
                                 output_width=2560, output_height=1440)
        print("wrote", name)
    if cairosvg is not None:                        # the legacy preview, EL-Openglo
        with atomic_path("preview.png") as tmp:
            cairosvg.svg2png(url="EL-Openglo-wallpaper.svg", write_to=tmp,
                             output_width=1280, output_height=720)
