"""W75 negative fixture for policy/embedded_markup.rego: an SVG DOCUMENT held in a
string constant — the shape make_wallpaper.py had before its SVG moved to a
template (built at module level, un-previewable, un-lintable). Never imported;
only scanned, when planted by `check_embedded_markup.py --json <this>`.
`opa_gate.py embedded_markup <this> --expect denied:E1` must hold."""

WALLPAPER = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080" viewBox="0 0 1920 1080">
  <defs>
    <filter id="glow"><feGaussianBlur stdDeviation="6"/></filter>
  </defs>
  <rect width="1920" height="1080" fill="#081411"/>
  <g filter="url(#glow)" stroke="#4bfad7" stroke-width="18">
    <line x1="900" y1="400" x2="1020" y2="400"/>
    <line x1="1020" y1="400" x2="1020" y2="540"/>
  </g>
</svg>
"""
