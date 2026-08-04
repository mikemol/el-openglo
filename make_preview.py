#!/usr/bin/env python3
"""Global Theme preview emitter (⊕VER-PREVIEW).

KDE shows contents/preview.png for each Look-and-Feel package. A preview is not
a screenshot (we have no live Plasma to capture) — it's a REPRESENTATION of the
theme identity, so we render it deterministically from the SAME color tokens the
scheme carries. The preview reads EL-<variant>.colors; it cannot drift from the
theme because it has no palette of its own.
"""
import os, cairosvg, re

ROOT = os.path.dirname(os.path.abspath(__file__))
W, H = 384, 256  # KDE thumbnail aspect


def parse_scheme(variant):
    """Pull the identity colors from EL-<variant>.colors."""
    path = os.path.join(ROOT, f"{variant}.colors")
    text = open(path).read()
    section = {}
    cur = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            cur = line
        elif "=" in line and cur:
            k, v = line.split("=", 1)
            section[(cur, k)] = v
    def rgb(sect, key):
        v = section.get((sect, key))
        if not v:
            raise KeyError(f"{variant}: missing {sect} {key}")
        return "#%02x%02x%02x" % tuple(int(x) for x in v.split(","))
    # window bg (ground), foreground (phosphor text), accent (lit segment)
    return {
        "ground": rgb("[Colors:Window]", "BackgroundNormal")
                  if ("[Colors:Window]", "BackgroundNormal") in section
                  else rgb("[Colors:Complementary]", "BackgroundNormal"),
        "panel":  rgb("[Colors:Header]", "BackgroundNormal"),
        "phosphor": rgb("[Colors:View]", "ForegroundNormal")
                    if ("[Colors:View]", "ForegroundNormal") in section
                    else rgb("[Colors:Button]", "ForegroundNormal"),
        "accent": rgb("[Colors:Button]", "DecorationFocus"),
        "sel":    rgb("[Colors:Selection]", "BackgroundNormal"),
    }


# ⚑ CLOCK_FIT — the bezel is DERIVED from the text it contains, not guessed.
#
# It was a hardcoded 76px box around 30px monospace "12:00" with 2px letter
# spacing: 5 glyphs x 18px advance + 4 x 2px = 98px of text in a 76px bezel,
# overflowing 15px left and 11px right. Only the right clip was VISIBLE (the left
# ran under the window), so it read as one bug and was two.
#
# Nothing caught it because every check here asks about COLOUR — is this legible
# against that. The SVG was valid, its palette correct, every contrast gate
# green: the artifact was right and the LAYOUT was wrong, which is a property
# only a rendering has. It took putting the samples somewhere they could be
# looked at (catalog/library/) to see it at all.
#
# So the geometry now follows the content. Change the time, the font size or the
# tracking and the bezel resizes with it; the previous form would silently clip
# again on any of those.
CLOCK_TEXT = "12:00"
CLOCK_FONT_PX = 30
CLOCK_TRACKING = 2
CLOCK_PAD = 10                      # breathing room between glyphs and bezel
# A monospace advance is ~0.6em. This is an ESTIMATE and is named as one: SVG has
# no measurable text without a rasteriser, so the honest move is a conservative
# constant plus padding, not a false precision.
CLOCK_ADVANCE_EM = 0.6


def clock_geometry(text=CLOCK_TEXT, font_px=CLOCK_FONT_PX,
                   tracking=CLOCK_TRACKING, pad=CLOCK_PAD):
    """(text_width, bezel_x, bezel_width) — the bezel sized to hold `text`.

    The text is centred on the bezel, so the box is the text plus padding on
    both sides and the anchor sits at its middle."""
    n = len(text)
    tw = n * font_px * CLOCK_ADVANCE_EM + max(0, n - 1) * tracking
    bw = tw + 2 * pad
    return tw, -pad - tw / 2, bw


def preview_svg(c):
    """A small mock desktop: dark ground, a panel, a window with phosphor text,
    and a segment-style clock reading the accent — unmistakably THIS variant."""
    _tw, _bx, _bw = clock_geometry()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
  <rect width="{W}" height="{H}" fill="{c['ground']}"/>
  <!-- window -->
  <rect x="42" y="40" width="230" height="150" rx="6" fill="{c['panel']}"
        stroke="{c['accent']}" stroke-width="1.5"/>
  <rect x="42" y="40" width="230" height="22" rx="6" fill="{c['sel']}"/>
  <circle cx="56" cy="51" r="4" fill="{c['phosphor']}"/>
  <circle cx="70" cy="51" r="4" fill="{c['accent']}"/>
  <!-- phosphor text lines -->
  <rect x="58" y="80"  width="140" height="7" rx="2" fill="{c['phosphor']}"/>
  <rect x="58" y="98"  width="180" height="7" rx="2" fill="{c['phosphor']}" opacity="0.75"/>
  <rect x="58" y="116" width="110" height="7" rx="2" fill="{c['phosphor']}" opacity="0.55"/>
  <rect x="58" y="150" width="70"  height="20" rx="3" fill="{c['accent']}"/>
  <!-- segment clock motif -->
  <g transform="translate(322,150)" font-family="monospace" font-weight="bold">
    <rect x="{_bx:.1f}" y="-26" width="{_bw:.1f}" height="44" rx="4" fill="{c['ground']}"
          stroke="{c['accent']}" stroke-width="1"/>
    <text x="0" y="7" font-size="{CLOCK_FONT_PX}" fill="{c['accent']}" text-anchor="middle"
          letter-spacing="{CLOCK_TRACKING}">{CLOCK_TEXT}</text>
  </g>
  <!-- panel -->
  <rect x="0" y="{H-26}" width="{W}" height="26" fill="{c['panel']}"/>
  <rect x="8" y="{H-19}" width="40" height="12" rx="3" fill="{c['accent']}"/>
  <rect x="{W-70}" y="{H-19}" width="60" height="12" rx="3" fill="{c['phosphor']}" opacity="0.7"/>
</svg>'''


def render_all(variants, out_map):
    """Render preview.png for each variant into out_map[variant] path."""
    for v in variants:
        c = parse_scheme(v)
        svg = preview_svg(c)
        out = out_map[v]
        os.makedirs(os.path.dirname(out), exist_ok=True)
        cairosvg.svg2png(bytestring=svg.encode(), write_to=out, output_width=W*2,
                         output_height=H*2)
    return list(out_map.values())


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/preview-{v}.png" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "previews")
    for v in variants:
        print(" ", v, parse_scheme(v)["phosphor"], parse_scheme(v)["accent"])
