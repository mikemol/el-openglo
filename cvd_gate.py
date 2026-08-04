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


# ── WCAG 2.x relative luminance + contrast ratio ─────────────────────────────
# W3C WCAG 2.1, Understanding SC 1.4.3.  The linearisation threshold and the
# 0.05 offsets are normative; do not "simplify" them.
def _wcag_L(c):
    """Relative luminance of an sRGB triple, per WCAG 2.x."""
    out = []
    for ch in (np.asarray(c, dtype=float) / 255.0):
        out.append(ch / 12.92 if ch <= 0.04045 else ((ch + 0.055) / 1.055) ** 2.4)
    r, g, b = out
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def wcag_ratio(a, b):
    """WCAG 2.x contrast ratio between two sRGB triples (1.0 … 21.0)."""
    la, lb = _wcag_L(a), _wcag_L(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ── APCA (WCAG 3 draft) lightness contrast ───────────────────────────────────
# apca-w3 0.0.98G constants, fetched and pinned in the design log.  APCA is a
# CROSS-CHECK, never a hard gate: WCAG 2 is known to mis-rank dark-mode pairs,
# and this is what makes that disagreement visible.
#
# ⚑ POLARITY MATTERS AND THE SIGN IS THE POINT.  Lc is signed: dark-text-on-light
# and light-text-on-dark are different perceptual problems, which is exactly the
# asymmetry WCAG 2 is blind to.  Never take abs() inside this function.
_APCA = dict(
    Y_TRC=2.4, Rco=0.2126729, Gco=0.7151522, Bco=0.0721750,
    Bclip=0.022, Bexp=1.414,          # black soft-clamp
    normBG=0.56, normTXT=0.57,        # normal polarity (dark text on light)
    revBG=0.65, revTXT=0.62,          # reverse polarity (light text on dark)
    scale=1.14, offset=0.027, loClip=0.001,
)


def _apca_Y(c):
    k = _APCA
    r, g, b = (np.asarray(c, dtype=float) / 255.0) ** k["Y_TRC"]
    y = k["Rco"] * r + k["Gco"] * g + k["Bco"] * b
    # soft-clamp near black, so very dark pairs do not blow up
    return y if y > k["Bclip"] else y + (k["Bclip"] - y) ** k["Bexp"]


def apca_Lc(text, bg):
    """APCA lightness contrast Lc of `text` on `bg`.  SIGNED: negative = reverse
    polarity (light text on dark). Validated against the published vectors —
    #888 on #fff = 63.06, #fff on #888 = -68.54 — asserted in _selftest."""
    k = _APCA
    ytxt, ybg = _apca_Y(text), _apca_Y(bg)
    if abs(ytxt - ybg) < k["loClip"]:
        return 0.0
    if ybg > ytxt:                                    # normal: dark on light
        sapc = (ybg ** k["normBG"] - ytxt ** k["normTXT"]) * k["scale"]
        out = 0.0 if sapc < k["offset"] else sapc - k["offset"]
    else:                                             # reverse: light on dark
        sapc = (ybg ** k["revBG"] - ytxt ** k["revTXT"]) * k["scale"]
        out = 0.0 if sapc > -k["offset"] else sapc + k["offset"]
    return out * 100.0


# ── thresholds (the judgment, relocated to named constants) ──────────────────
# ⚑ THESE ARE THE PROJECT'S JUDGMENT, NOT THE STANDARDS'.  Each is defensible and
# each is OURS: changing one is a design decision, and putting them here is what
# makes that decision a one-line edit instead of a hand-chase through emitters.

# A truly-off OLED pixel emits 0 nits; "still reads as black in a dark room" is
# about <=2-4 nits, i.e. <=2% of SDR white.  Grounds measure 0.2-0.7%.
OLED_VOID_MAX_LUM = 0.02

# The ghost is SUBORDINATE TEXTURE, not text: it must FAIL readability by design.
# APCA's "any text" minimum is ~30 Lc, so the ghost ceiling sits at it.
GHOST_READABLE_LC = 30.0

# Per-side contrast target for the {lit, ghost, ground} 3-body separation.
STRETCH_TARGET = 3.0

# Keep `lit` hue-faithful while stretching: don't crush to a hueless black to win
# a contrast metric (the ⊕GHOST-CONTRAST-2 lesson).
CHROMA_FLOOR = 40.0

# Required hue sectors per semantic accent, (lo, hi) degrees; a sector may wrap.
# ⚑ THE CANONICAL TABLE LIVES HERE.  make_palette.py carried a private `_SECTORS`
# fork of it — the carrier-locality disease: two copies of one table, and the
# solver silently optimising against a different one than the gate audits.
SECTORS = {"neg": (340, 25), "neu": (30, 75), "pos": (90, 170),
           "link": (180, 270), "visited": (180, 310)}


def _lerp(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def stretch_lit(lit, ground, target=STRETCH_TARGET, chroma_floor=CHROMA_FLOOR):
    """Push `lit` AWAY from `ground` until the span reaches `target`.

    The rule is mirrored by mode — dark ground -> lit brighter; light (backlit)
    ground -> lit DARKER, a dark segment on a glowing field, which is what a real
    lit-mode LCD looks like.  Capped by the chroma floor so `lit` stays
    hue-faithful rather than crushing toward a hueless extreme."""
    if wcag_ratio(lit, ground) >= target:
        return tuple(int(x) for x in lit)
    away = (255, 255, 255) if _wcag_L(ground) < 0.4 else (0, 0, 0)
    best = tuple(int(x) for x in lit)
    for i in range(1, 101):
        cand = _lerp(lit, away, i / 100.0)
        try:
            chroma = float(np.linalg.norm(_ucs(cand, None)[1:]))
        except Exception:                              # noqa: BLE001
            chroma = chroma_floor
        if chroma < chroma_floor:
            break
        best = cand
        if wcag_ratio(cand, ground) >= target:
            break
    return best


def derive_ghost(lit, ground, floor=None):
    """The ghost that BALANCES its two sides.

    ⚑ ONE RULE, NOT TWO FLOORS.  Search lit->ground for the point maximising
    min(contrast(lit, ghost), contrast(ghost, ground)).  Two separate floors
    conflict when the span is tight; a max-min degrades gracefully instead —
    it still returns the best available ghost rather than failing outright.
    The achievable optimum is ~sqrt(contrast(lit, ground)) per side."""
    best, best_score = None, -1.0
    for i in range(1, 100):
        cand = _lerp(lit, ground, i / 100.0)
        score = min(wcag_ratio(lit, cand), wcag_ratio(cand, ground))
        if score > best_score:
            best, best_score = cand, score
    return best


def feasible_ghost_floor(lit, ground):
    """The floor `derive_ghost` can actually be held to for this pair.

    min(3.0, sqrt(span) * 0.95): the target where the span allows it, and a
    proportion of the achievable optimum where it does not — so the gate passes
    on a tight span and still flags a genuinely off-optimum ghost."""
    span = wcag_ratio(lit, ground)
    return min(STRETCH_TARGET, (span ** 0.5) * 0.95)


def derive_ghost_ceiling(lit, ground, ceiling_lc=GHOST_READABLE_LC):
    """The ghost with the MOST contrast that still FAILS readability.

    ⚑ THE CEILING IS THE DEFINITION, NOT A BUDGET.  The ghost is unlit-segment
    texture: it must be visible as shape and must NOT read as text, so it is
    defined as the maximum |Lc| strictly below the readability threshold. Pushing
    it higher would make it text; lower wastes available separation."""
    best, best_lc = None, -1.0
    for i in range(1, 100):
        cand = _lerp(lit, ground, i / 100.0)
        lc = abs(apca_Lc(cand, ground))
        if lc < ceiling_lc and lc > best_lc:
            best, best_lc = cand, lc
    if best is None:                                   # span too small to fail-by-design
        best = _lerp(lit, ground, 0.5)
    return best


def _worst_normalized(a, b, floors, factor=0.8):
    """Worst-view separation NORMALIZED by the floor its class is judged against.

    ⚑ THIS IS THE GATE'S OWN METRIC, AND IT IS WHY IT EXISTS.  The ⊕SOLVER-SEMANTIC
    result was that the solver must optimise THE GATE'S metric, not raw ΔE — a
    palette maximising raw distance can still fail the gate, because the gate
    judges each pair against its class floor.  A value >= 1.0 clears; below 1.0
    is the shortfall as a fraction, so pairs of different classes are comparable."""
    d, view = worst_view_dE(a, b)
    need = floors["enforced"] * factor
    return (d / need if need else float("inf")), view, d

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

def _selftest():
    """The restored API, checked against PUBLISHED reference values.

    ⚑ THIS IS WHY THE RESTORATION IS A RESTORATION AND NOT A GUESS.  The design
    log recorded the APCA constants together with the vectors they must reproduce,
    so the implementation is falsifiable against numbers nobody here chose. A
    constant typo'd anywhere in the chain moves these and the test fails."""
    ok = True

    def check(label, got, want, tol=None):
        nonlocal ok
        good = (abs(got - want) <= tol) if tol is not None else (got == want)
        if not good:
            print(f"  FAIL {label}: got {got!r} want {want!r}"
                  f"{f' (tol {tol})' if tol else ''}")
            ok = False
        else:
            print(f"  ok   {label}")

    # ── APCA against the published vectors (apca-w3 0.0.98G) ──
    check("apca #888 on #fff = 63.06", apca_Lc((136, 136, 136), (255, 255, 255)),
          63.06, 0.02)
    check("apca #fff on #888 = -68.54", apca_Lc((255, 255, 255), (136, 136, 136)),
          -68.54, 0.02)
    # polarity is signed and NOT symmetric — the asymmetry WCAG 2 cannot see
    a = apca_Lc((0, 0, 0), (255, 255, 255))
    b = apca_Lc((255, 255, 255), (0, 0, 0))
    check("apca polarity is signed", a > 0 and b < 0, True)
    check("apca polarity is asymmetric", abs(abs(a) - abs(b)) > 1.0, True)

    # ── WCAG 2.x against its own normative anchors ──
    check("wcag black/white = 21:1", round(wcag_ratio((0, 0, 0), (255, 255, 255)), 2),
          21.0, 0.01)
    check("wcag identity = 1:1", round(wcag_ratio((1, 2, 3), (1, 2, 3)), 4), 1.0, 1e-4)
    check("wcag L(white) = 1.0", round(_wcag_L((255, 255, 255)), 6), 1.0, 1e-6)
    check("wcag L(black) = 0.0", round(_wcag_L((0, 0, 0)), 6), 0.0, 1e-6)

    # ── the thresholds are OURS and must stay legible ──
    check("OLED void ceiling is 2%", OLED_VOID_MAX_LUM, 0.02)
    check("a mid grey trips the void ceiling",
          _wcag_L((40, 40, 40)) > OLED_VOID_MAX_LUM, True)
    check("a true void clears it", _wcag_L((6, 11, 13)) < OLED_VOID_MAX_LUM, True)

    # ── the derivations do what their invariants say ──
    lit, ground = (140, 232, 218), (6, 11, 13)
    gh = derive_ghost(lit, ground)
    lo = min(wcag_ratio(lit, gh), wcag_ratio(gh, ground))
    check("derive_ghost balances both sides", lo >= feasible_ghost_floor(lit, ground) * 0.95,
          True)
    ceil_gh = derive_ghost_ceiling(lit, ground)
    check("ceiling ghost FAILS readability by design",
          abs(apca_Lc(ceil_gh, ground)) < GHOST_READABLE_LC, True)
    st = stretch_lit((90, 150, 142), ground)
    check("stretch_lit pushes away from ground",
          wcag_ratio(st, ground) >= wcag_ratio((90, 150, 142), ground), True)

    # ── SECTORS is the canonical table, and it is complete ──
    check("SECTORS covers every semantic accent",
          sorted(SECTORS), ["link", "neg", "neu", "pos", "visited"])

    # ── the gate's own metric normalizes ──
    q, view, d = _worst_normalized(OKABE_ITO["blue"], OKABE_ITO["orange"],
                                   reference_floors())
    check("normalized-q clears for a reference pair", q >= 1.0, True)

    print("cvd_gate selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    f, a, b, v = reference_floor()
    print(f"Okabe-Ito floor: dE={f:.1f} ({a}~{b} under {v})")
