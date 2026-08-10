"""ghost_solve — the ghost as a SOLVED balance point, not a scanned one.

⚑ THE SCAN FINDS NUMERICALLY WHAT IS ALGEBRAICALLY DETERMINED, AND CANNOT SAY SO.
`cvd_gate.derive_ghost` walks 99 points along lit->ground and returns the best of
99. That is not merely imprecise — it is UNFALSIFIABLE ABOUT ITS OWN OPTIMALITY:
nothing in the result says whether the true optimum lies between two samples, so
the answer cannot be shown wrong. An exact derivation can be.

⚑ AND THE DIFFERENCE IS OF KIND, NOT OF MAGNITUDE.  Measured on the six shipped
palettes the solve improves the worse side on four and ties on two, by margins
around 0.01-0.04 — which is easy to misreport as a small win, and I did at first.
It is not a small win; it is a DIFFERENT KIND OF ANSWER. The scan's number is the
best of a sample and carries no statement about the optimum. The solve's number
satisfies `a/y = y/b`, an identity that can be checked, perturbed, and refuted.
A grid that happens to land close is still guessing; that the guess is good is a
fact about this objective being smooth in one dimension, not about the method.

THE ALGEBRA. WCAG contrast is a ratio of offset luminances,

    contrast(p, q) = (L_p + 0.05) / (L_q + 0.05)   for L_p >= L_q

so writing a = L_lit + 0.05, b = L_ground + 0.05, y = L_ghost + 0.05, the ghost's
two sides are exactly

    lit  -> ghost :  a / y          (how much the ghost gives up to the lit)
    ghost -> ground:  y / b          (how much it keeps above the ground)

`derive_ghost` maximises min(a/y, y/b). Both are monotone in y and they move in
OPPOSITE directions, so the maximum of their minimum is where they meet:

    a/y = y/b   =>   y^2 = ab   =>   y = sqrt(ab)

the GEOMETRIC MEAN of the two offset luminances, at which each side equals
sqrt(a/b) = sqrt(span). The docstring in cvd_gate already asserts "the achievable
optimum is ~sqrt(contrast(lit, ground)) per side" — it is a THEOREM, and the scan
was rediscovering it to two decimal places on every call.

⚑ THIS IS THE `AND` SERIES CHAIN, READ IN THE CARRIER.  The ghost sits BETWEEN lit
and ground and both links must hold, so the composite is series composition:
strains add, and a series chain is balanced exactly when its two shortfalls are
equal. In gcalc's terms the involution `NOT(x) = 1/x` exchanges the two sides and
the optimum is its FIXED POINT — which is why the answer is a geometric mean
rather than an arithmetic one.

WHAT THIS DOES NOT CLAIM. Solving for the luminance is exact; REACHING it is not.
A colour is three channels and this determines ONE scalar, so the returned colour
is still the point on the lit->ground segment whose luminance is closest to the
solved target. That last step is a projection, and it is why `solve_ghost_t`
returns the parameter and its exactness separately from the colour: the relation
is the answer, and a particular colour is a READ of it.
"""
from __future__ import annotations

import cvd_gate as C

# WCAG's offset. Normative (W3C WCAG 2.1, SC 1.4.3) — not a tunable.
_OFFSET = 0.05


def offsets(lit, ground):
    """(a, b) = the offset luminances, ordered (brighter, darker).

    Ordered because contrast is defined on the ordered pair; the ghost lies
    between them either way, so the solve is symmetric under swapping them."""
    la = C._wcag_L(lit) + _OFFSET
    lb = C._wcag_L(ground) + _OFFSET
    return (la, lb) if la >= lb else (lb, la)


def balance_luminance(lit, ground):
    """The EXACT offset luminance at which the ghost's two sides are equal.

    y = sqrt(ab). No search, no grid — a closed form in the inputs, so re-solving
    for a different span is an evaluation rather than another scan."""
    a, b = offsets(lit, ground)
    return (a * b) ** 0.5


def balance_contrast(lit, ground):
    """The contrast each side achieves at the balance point: sqrt(span).

    Equal on both sides BY CONSTRUCTION, which is what "balanced" means. This is
    the number cvd_gate.feasible_ghost_floor approximates as sqrt(span) * 0.95."""
    a, b = offsets(lit, ground)
    return (a / b) ** 0.5


def solve_ghost_t(lit, ground):
    """The parameter t along lit->ground whose LUMINANCE is the balance point.

    ⚑ LUMINANCE IS NOT LINEAR IN t, WHICH IS WHY THIS IS NOT sqrt(0.5).  sRGB
    channels are gamma-encoded and _wcag_L linearises them, so L(lerp(lit, ground,
    t)) is a nonlinear function of t. The BALANCE is solved exactly in luminance;
    finding the t that lands on it is a monotone root-find, which bisection solves
    to machine precision rather than to a 1/99 grid.

    Returns (t, achieved_luminance, target_luminance). Reporting the achieved
    value beside the target is the honest form: it says how well the segment can
    reach the solved point, instead of quietly returning whatever it reached."""
    target = balance_luminance(lit, ground)

    def lum_at(t):
        return C._wcag_L(C._lerp(lit, ground, t)) + _OFFSET

    lo, hi = 0.0, 1.0
    lo_v, hi_v = lum_at(lo), lum_at(hi)
    # the segment runs from lit to ground; luminance is monotone along it, but
    # which END is brighter depends on polarity (off vs backlit).
    ascending = hi_v > lo_v
    for _ in range(60):                     # 2^-60 on t: far below 8-bit quantisation
        mid = (lo + hi) / 2.0
        v = lum_at(mid)
        if (v < target) == ascending:
            lo = mid
        else:
            hi = mid
    t = (lo + hi) / 2.0
    return t, lum_at(t), target


def derive_ghost(lit, ground, floor=None):
    """The balanced ghost — the drop-in for cvd_gate.derive_ghost.

    ⚑ SAME SIGNATURE, SAME CONTRACT, DIFFERENT EPISTEMICS.  The scan returned the
    best of 99 samples; this returns the point solving the balance condition, and
    `balance_report` can say by how much each side deviates. `floor` is accepted
    and ignored exactly as the scan ignored it — recorded rather than silently
    dropped, because a caller passing it deserves to know it does nothing."""
    t, _achieved, _target = solve_ghost_t(lit, ground)
    return C._lerp(lit, ground, t)


def solve_ceiling_t(lit, ground, ceiling_lc):
    """The t whose APCA |Lc| against the ground is the LARGEST still below the ceiling.

    ⚑ A DIFFERENT OBJECTIVE FROM THE BALANCE, AND IT MUST NOT BE CONFLATED.
    `derive_ghost` balances two sides; `derive_ghost_ceiling` maximises ONE
    quantity subject to a strict upper bound — the ghost must be visible as shape
    and must NOT read as text, so it is defined as the supremum of |Lc| strictly
    below the readability threshold. That is a constrained maximum, not a fixed
    point of an involution, so there is no geometric mean to reach for.

    ⚑ AND THE SUPREMUM IS NOT ATTAINED, WHICH IS THE WHOLE DIFFICULTY.  The
    constraint is STRICT (`lc < ceiling`), so the exact optimum is a limit point
    the answer must approach from below and never touch. A 99-point scan hides
    that by only ever sampling interior points; solving it honestly means finding
    the boundary and then stepping back to the last representable colour under it.

    |Lc| is monotone along lit->ground (both endpoints are fixed, the segment is a
    straight line in sRGB), so the boundary is a root and bisection finds it to
    machine precision. Returns (t, lc_at_t) with lc_at_t < ceiling guaranteed, or
    (None, None) when the whole segment already fails the ceiling — a REFUSAL
    rather than a silent midpoint."""
    def lc_at(t):
        return abs(C.apca_Lc(C._lerp(lit, ground, t), ground))

    lo, hi = 0.0, 1.0
    lo_v, hi_v = lc_at(lo), lc_at(hi)
    # t=1 IS the ground, where |Lc| is 0, so the ceiling is satisfied there and
    # violated (or not) at the lit end. If even the lit end clears the ceiling,
    # the span is too small to fail by design and there is no boundary to find.
    if lo_v < ceiling_lc:
        return 0.0, lo_v
    if hi_v >= ceiling_lc:
        return None, None                  # nothing on the segment is under it
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if lc_at(mid) >= ceiling_lc:
            lo = mid                       # still too readable: move toward ground
        else:
            hi = mid                       # under the ceiling: this side is feasible
    return hi, lc_at(hi)


def derive_ghost_ceiling(lit, ground, ceiling_lc=None):
    """The ceiling ghost — the drop-in for cvd_gate.derive_ghost_ceiling.

    Falls back to the segment midpoint exactly as the scan does when no point on
    the segment fails readability, so the contract is unchanged."""
    if ceiling_lc is None:
        ceiling_lc = C.GHOST_READABLE_LC
    t, _lc = solve_ceiling_t(lit, ground, ceiling_lc)
    if t is None:
        return C._lerp(lit, ground, 0.5)
    return C._lerp(lit, ground, t)


def balance_report(lit, ground, ghost=None):
    """How well a ghost balances: (side_lit, side_ground, ideal, skew).

    ⚑ THE PROVENANCE THE SCAN DISCARDED.  `derive_ghost` returned a colour and
    nothing about WHY — which side was binding, how much slack the other had. The
    balance point is a relation between three colours, so a read of it should be
    able to report that relation. `skew` is the ratio of the two sides: 1.0 is
    perfectly balanced, and its distance from 1.0 is the quantity the 99-point
    grid could never bound."""
    if ghost is None:
        ghost = derive_ghost(lit, ground)
    side_lit = C.wcag_ratio(lit, ghost)
    side_ground = C.wcag_ratio(ghost, ground)
    ideal = balance_contrast(lit, ground)
    lo, hi = sorted((side_lit, side_ground))
    skew = (hi / lo) if lo else float("inf")
    return side_lit, side_ground, ideal, skew
