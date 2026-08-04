#!/usr/bin/env python3
"""CVD distinctness gate, calibrated by the Okabe-Ito constellation.

Semantic ambiguity of a color pair = its minimum CAM02-UCS distance across
four views of color vision: trichromat identity + simulated protanopia,
deuteranopia, tritanopia (Machado model, severity 100, via colorspacious).

The floor is not hand-picked: it is the tightest worst-view separation inside
the Okabe-Ito color-universal-design palette itself. A pair of ours is
admissible if it is at least as separated (x a class factor) as the reference
shape's own tightest pair.
"""
import numpy as np
from colorspacious import cspace_convert

VIEWS = [None, "protanomaly", "deuteranomaly", "tritanomaly"]

def _ucs(rgb255, cvd):
    c = np.asarray(rgb255, dtype=float) / 255.0
    src = "sRGB1" if cvd is None else {"name": "sRGB1+CVD", "cvd_type": cvd, "severity": 100}
    return cspace_convert(c, src, "CAM02-UCS")

def worst_view_dE(a, b):
    """min over views of CAM02-UCS distance; also returns the collapsing view."""
    best = (1e9, "none")
    for v in VIEWS:
        d = float(np.linalg.norm(_ucs(a, v) - _ucs(b, v)))
        if d < best[0]:
            best = (d, v or "trichromat")
    return best

# Okabe & Ito (2008) Color Universal Design palette, chromatic members
OKABE_ITO = {
    "orange": (230, 159, 0), "sky": (86, 180, 233), "bluegreen": (0, 158, 115),
    "yellow": (240, 228, 66), "blue": (0, 114, 178), "vermillion": (213, 94, 0),
    "purple": (204, 121, 167),
}

def reference_floor():
    names = list(OKABE_ITO)
    floor = (1e9, None, None, None)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d, view = worst_view_dE(OKABE_ITO[names[i]], OKABE_ITO[names[j]])
            if d < floor[0]:
                floor = (d, names[i], names[j], view)
    return floor

def rgb(s):
    return tuple(int(x) for x in s.split(","))

# pair classes: color-as-sole-carrier -> enforced; accent-adjacent (geometry
# co-carries meaning) -> surfaced
ENFORCED = [("neg~pos", "neg", "pos"), ("neg~neu", "neg", "neu"),
            ("neu~pos", "neu", "pos"), ("link~body", "link", "fg")]
SURFACED = [("neu~accent", "neu", "focus"), ("link~accent", "link", "focus"),
            ("neg~accent", "neg", "focus"), ("pos~accent", "pos", "focus")]

def audit_variant(t, floor, factor=0.8):
    need = floor * factor
    viol = []
    for name, a, b in ENFORCED:
        d, view = worst_view_dE(rgb(t[a]), rgb(t[b]))
        ok = d >= need
        print(f"  {t['id']:16s} {name:12s} dE={d:5.1f} worst={view:11s} need {need:.1f}  {'ok' if ok else 'VIOLATION'}")
        if not ok:
            viol.append(f"{name} dE={d:.1f}<{need:.1f} ({view})")
    for name, a, b in SURFACED:
        d, view = worst_view_dE(rgb(t[a]), rgb(t[b]))
        print(f"  {t['id']:16s} {name:12s} dE={d:5.1f} worst={view:11s} (surfaced)")
    return viol

if __name__ == "__main__":
    f, a, b, v = reference_floor()
    print(f"Okabe-Ito floor: dE={f:.1f} ({a}~{b} under {v})")
