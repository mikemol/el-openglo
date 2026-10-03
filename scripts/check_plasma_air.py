#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_plasma_air.py — does a host Plasma Style follow the colour scheme, or bake its own?
(W223: the Air half of W37.)

A Plasma Style recolours with the session scheme only through the SVG's
`ColorScheme-*` stylesheet classes (and then only against the scheme the theme's own
`colors` file does NOT override). So the measurement is, per theme: whether a `colors`
file ships (a fixed palette for the theme's classed elements), and per SVG(Z): how many
elements are painted by a `ColorScheme-*` class vs by a literal colour (fill / stroke /
stop-color / flood-color hex or rgb()) outside the `<style>` element (the stylesheet's
own hexes are fallbacks the scheme overrides, so they are not counted as baked).

    scripts/check_plasma_air.py                 # n of m summary (theme: air)
    scripts/check_plasma_air.py --theme ID      # another theme under /usr/share/plasma/desktoptheme
    scripts/check_plasma_air.py --json          # the measurement; policy/plasma_air.rego decides
    scripts/check_plasma_air.py --selftest

Reuse: the EL Plasma Styles are emitted by make_plasma.py, which bakes hex fills and
a colors file; this reads a HOST theme the same way make_plasma.check reads an EL one.

WEAKNESS: a literal colour is counted by a regex over the SVG text, not by rendering;
an element recoloured by CSS the regex does not know (inline style on a class-less
element is covered, an external stylesheet is not), or a ColorScheme class that no
element uses, would be mis-seen. A host without the theme is withheld, not clean.
"""
import gzip
import json
import os
import re
import sys

BASE = "/usr/share/plasma/desktoptheme"
STYLE = re.compile(r"<style\b.*?</style>", re.S | re.I)
SCHEME = re.compile(r"""class\s*=\s*["'][^"']*ColorScheme-""")
BAKED = re.compile(r"""(?:fill|stroke|stop-color|flood-color)\s*[:=]\s*["']?\s*(?:#[0-9a-fA-F]{3,8}\b|rgba?\()""")
SECTION = re.compile(r"^\[(Colors:\w+)\]", re.M)


def read_svg(path):
    raw = open(path, "rb").read()
    return (gzip.decompress(raw) if path.endswith("z") else raw).decode("utf-8", "replace")


def measure_svg(text):
    body = STYLE.sub("", text)
    return {"scheme_classed": len(SCHEME.findall(body)), "baked": len(BAKED.findall(body))}


def measure_theme(base, tid):
    d = os.path.join(base, tid)
    if not os.path.isdir(d):
        return {"id": tid, "withheld": f"{d} is not on this host"}
    colors = os.path.join(d, "colors")
    sections = SECTION.findall(open(colors).read()) if os.path.exists(colors) else []
    svgs = []
    # population: the host's installed Plasma theme directory (a system tree, not tracked files)
    for dp, _dn, fns in sorted(os.walk(d)):
        for fn in sorted(fns):
            if fn.endswith((".svg", ".svgz")):
                p = os.path.join(dp, fn)
                svgs.append({"path": os.path.relpath(p, d), **measure_svg(read_svg(p))})
    return {"id": tid, "has_colors_file": os.path.exists(colors), "colors_sections": sections, "svgs": svgs}


def measure(base=BASE, tid="air"):
    return {"themes": [measure_theme(base, tid)]}


def _selftest():
    import tempfile
    seen = {
        "a literal fill is baked": measure_svg('<rect fill="#ff0000"/>') == {"scheme_classed": 0, "baked": 1},
        "a classed element is scheme-driven": measure_svg('<path class="ColorScheme-Text"/>')["scheme_classed"] == 1,
        "stylesheet fallback hexes are not baked":
            measure_svg('<style>.ColorScheme-Text{color:#232629}</style><path class="ColorScheme-Text"/>')["baked"] == 0,
        "inline style fill is baked": measure_svg('<g style="fill:#fff"/>')["baked"] == 1,
    }
    with tempfile.TemporaryDirectory() as t:
        os.makedirs(os.path.join(t, "x", "widgets"))
        open(os.path.join(t, "x", "colors"), "w").write("[Colors:View]\nBackgroundNormal=1,2,3\n")
        with gzip.open(os.path.join(t, "x", "widgets", "a.svgz"), "wb") as f:
            f.write(b'<svg><rect fill="#abc"/></svg>')
        m = measure_theme(t, "x")
        seen["a svgz is read and a colors file seen"] = (m["has_colors_file"] and m["colors_sections"] == ["Colors:View"]
                                                         and m["svgs"][0]["baked"] == 1)
        seen["an absent theme is withheld, not clean"] = "withheld" in measure_theme(t, "nope")
    for label, ok in seen.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    print("check_plasma_air selftest:", "PASS" if all(seen.values()) else "FAIL")
    return all(seen.values())


def main(argv):
    tid, rest, i = "air", [], 1
    while i < len(argv):
        a = argv[i]
        if a == "--theme" and i + 1 < len(argv):
            tid = argv[i + 1]
            i += 2
            continue
        rest.append(a)
        i += 1
    for a in rest:
        if a not in ("--json", "--selftest"):
            print(f"check_plasma_air: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in rest:
        return 0 if _selftest() else 1
    m = measure(BASE, tid)
    if "--json" in rest:
        print(json.dumps(m, indent=1))
        return 0
    for t in m["themes"]:
        if "withheld" in t:
            print(f"  {t['id']}: WITHHELD {t['withheld']}")
            continue
        n = len(t["svgs"])
        sc = sum(1 for s in t["svgs"] if s["scheme_classed"])
        bk = sum(1 for s in t["svgs"] if s["baked"])
        print(f"  {t['id']}: colors file {'present' if t['has_colors_file'] else 'absent'}; "
              f"{sc} of {n} svgs use ColorScheme classes; {bk} of {n} carry literal colours; verdict is `opa_gate.py plasma_air`")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
