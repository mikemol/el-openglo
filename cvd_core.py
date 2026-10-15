#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The pure core of the CVD distinctness gate (W544): numpy and colorspacious, no repo import.

Semantic ambiguity of a colour pair = its minimum CAM02-UCS distance across four views of colour vision:
trichromat identity plus simulated protanopia, deuteranopia and tritanopia (Machado model, severity 100,
via colorspacious). The floor is not hand-picked: it is the tightest worst-view separation inside the
Okabe-Ito colour-universal-design palette itself.

⚑ WHY A MODULE OF ITS OWN. cvd_gate.py held this beside the palette authority: ENFORCED and SURFACED are
evaluated at import from palette_graph, so `import cvd_gate` drags the whole palette solver in, and nemik
(nemik:W438) could not take the worst-view arm without it. This file is the part that needs neither. It is
the staging area for the mtools distribution W544 asks for; cvd_gate re-exports every name here, so every
caller that resolves one through cvd_gate keeps working.

WEAKNESS, STATED. The WCAG and APCA contrast code (also pure) still lives in cvd_gate.py: this cut is the
CVD arm only, which is what was asked for. The Okabe-Ito table is the 2008 chromatic set, seven colours;
the floor is recomputed (and cached) from it, never stored.
"""

import functools

import numpy as np
from colorspacious import cspace_convert

VIEWS = [None, "protanomaly", "deuteranomaly", "tritanomaly"]


def _ucs(rgb255, cvd):
    c = np.asarray(rgb255, dtype=float)
    if c.shape == (3,):
        # ⚑ RENDER-SPEED #3b: a pure conversion, memoised on the exact float
        # triple (the same bits colorspacious would have seen). The palette
        # re-asks the same few colours thousands of times — 11,616 conversions
        # per make_notify_marquee.main_qml. A COPY is returned so a caller that
        # mutates the result cannot poison the cache.
        return _ucs_one(tuple(float(x) for x in c), cvd).copy()
    src = (
        "sRGB1"
        if cvd is None
        else {"name": "sRGB1+CVD", "cvd_type": cvd, "severity": 100}
    )
    return cspace_convert(c / 255.0, src, "CAM02-UCS")


@functools.cache
def _ucs_one(rgb255, cvd):
    c = np.asarray(rgb255, dtype=float) / 255.0
    src = (
        "sRGB1"
        if cvd is None
        else {"name": "sRGB1+CVD", "cvd_type": cvd, "severity": 100}
    )
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
    "orange": (230, 159, 0),
    "sky": (86, 180, 233),
    "bluegreen": (0, 158, 115),
    "yellow": (240, 228, 66),
    "blue": (0, 114, 178),
    "vermillion": (213, 94, 0),
    "purple": (204, 121, 167),
}


@functools.cache
def reference_floor():
    # Cached: a constant of the module-level OKABE_ITO table (an immutable tuple),
    # recomputed per rehue call before — 168 conversions each (render-speed #3b).
    names = list(OKABE_ITO)
    floor = (1e9, None, None, None)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            d, view = worst_view_dE(OKABE_ITO[names[i]], OKABE_ITO[names[j]])
            if d < floor[0]:
                floor = (d, names[i], names[j], view)
    return floor


def reference_floors():
    """{class: floor} — the per-class Okabe-Ito floor.

    ⚑ RESTORED (see the module header note).  Consumers want the floor keyed by
    pair class, not as one scalar: `reference_floor()` returns the single tightest
    pair, this returns the floor each class is judged against.  Both are real and
    they are NOT interchangeable — an earlier repair rewrote a caller of this into
    `reference_floor()[0]` and so silently changed which number the gate used."""
    f = reference_floor()[0]
    return {"enforced": f, "surfaced": f}


def rgb(s):
    return tuple(int(x) for x in s.split(","))


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    # the measurement can SEE a collapse: two warm colours a CVD view cannot tell apart are close, and
    # a vermillion against a blue is far, so the minimum over views is not a constant
    close, _ = worst_view_dE((213, 94, 0), (230, 159, 0))
    far, _ = worst_view_dE((213, 94, 0), (0, 114, 178))
    chk("a vermillion/orange pair is closer than vermillion/blue", close < far, True)
    chk(
        "identical colours are at distance 0",
        worst_view_dE((1, 2, 3), (1, 2, 3))[0],
        0.0,
    )
    chk("four views are read", len(VIEWS), 4)
    floor = reference_floor()
    members = (floor[1] in OKABE_ITO, floor[2] in OKABE_ITO)
    chk("the Okabe-Ito floor names two palette members", members, (True, True))
    chk("the floor is a positive distance", floor[0] > 0, True)
    chk(
        "the per-class floors are the one number twice",
        len({*reference_floors().values()}),
        1,
    )
    chk("rgb parses a comma triple", rgb("1,2,3"), (1, 2, 3))
    print("cvd_core selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
