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


def solve_floor_t(lit, ground, floor_lc):
    """The LARGEST t along lit->ground whose |Lc| against ground still clears `floor_lc`.

    |Lc| is monotone decreasing in t (t=1 IS the ground, Lc 0), so the boundary
    is a root and bisection finds it. Returns None when even the lit end (t=0)
    cannot clear the floor — a refusal, not a clamp.

    ⚑ IN APCA, LIKE THE CEILING.  This solved a WCAG floor until 2026-09-20; see
    `cvd_gate.feasible_ghost_floor` (residue) for why one metric is required."""
    def ratio_at(t):
        return abs(C.apca_Lc(C._lerp(lit, ground, t), ground))
    if ratio_at(0.0) < floor_lc:
        return None
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if ratio_at(mid) >= floor_lc:
            lo = mid
        else:
            hi = mid
    return lo


def alpha_min(lit, ground, floor=None):
    """The smallest render alpha at which SOME declared ghost can clear `floor` on screen.

    ⚑ THE COMPOSITE IS A POINT ON THE SAME SEGMENT.  Source-over of a flat alpha
    toward `ground` is a lerp toward `ground`, so a ghost declared at t renders at
    t' = 1 - a(1 - t).  The most contrast any declared ghost can give is at t=0
    (the lit colour itself), which renders at t' = 1 - a; that clears the floor
    iff 1 - a <= t_floor, i.e. a >= 1 - t_floor.  Below this alpha the ghost's
    COLOUR cannot fix the floor, whatever it is solved to.

    Returns None when the floor is unreachable at any alpha (the lit colour itself
    fails it) — which would be a palette defect, not an alpha one."""
    if floor is None:
        floor = C.feasible_ghost_floor_lc(lit, ground)
    t_floor = solve_floor_t(lit, ground, floor)
    return None if t_floor is None else 1.0 - t_floor


def solve_ghost_alpha(pairs):
    """ONE global alpha for every variant: the max of their alpha_min values.

    ⚑ ONE KNOB, SOLVED, NOT SIX AND NOT AUTHORED.  Operator ruling 2026-09-20 (W3):
    a single global alpha, owned by the palette authority and EMITTED to the
    renderer — replacing the 0.45 that SegmentChar.qml:73 held as a constant no
    check could see. The max is the only global value at which every variant's
    ghost colour still has room to be solved; anything lower makes at least one
    variant's floor unreachable by colour.

    `pairs` is [(id, lit, ground)]. Returns (alpha, [(id, alpha_min)]); refuses
    (raises) on an empty population or an unreachable floor, because a silently
    returned default IS the defect this replaces."""
    rows = []
    for vid, lit, ground in pairs:
        a = alpha_min(lit, ground)
        if a is None:
            raise ValueError(f"{vid}: the lit colour itself cannot clear the ghost "
                             f"floor — no alpha helps; the palette is the defect")
        rows.append((vid, a))
    if not rows:
        raise ValueError("solve_ghost_alpha: empty population — nothing was solved")
    return max(a for _v, a in rows), rows


def alpha_max_vs_lit(lit, ground, ghost, lit_floor):
    """The LARGEST alpha at which the SEEN ghost still sits `lit_floor` (WCAG) from lit.

    ⚑ THE GHOST'S OTHER SIDE.  `alpha_min` bounds alpha from BELOW (the seen ghost
    must clear the ground floor); this bounds it from ABOVE: the more opaque the
    ghost, the closer it sits to lit, and a glanced-at surface needs it further
    away than a looked-at one (glance_audit's MODE_FLOOR). Lit-vs-seen-ghost is
    monotone decreasing in alpha for a ghost between lit and ground, so the
    boundary is a root and bisection finds it. Returns None when even alpha 0
    (the ghost IS the ground) cannot clear the floor — the lit/ground span itself
    is too small for this mode."""
    import palette_graph as _pg

    def ratio_at(a):
        return C.wcag_ratio(lit, _pg.composite(ghost, ground, a))

    if ratio_at(0.0) < lit_floor:
        return None
    if ratio_at(1.0) >= lit_floor:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if ratio_at(mid) >= lit_floor:
            lo = mid
        else:
            hi = mid
    return lo


def solve_ghost_alpha_for_mode(rows, lit_floor):
    """ONE alpha for a parsing mode: the largest that clears `lit_floor` on EVERY variant.

    `rows` is [(id, lit, ground, ghost, a_min)] — the ghost already solved through
    the looked-at alpha, and each variant's ground-floor minimum. For each variant
    a_max = alpha_max_vs_lit(...); the mode's alpha is min(a_max) over variants,
    which every variant then clears on the lit side. ⚑ AND IT MUST STILL CLEAR THE
    GROUND SIDE: if the mode alpha falls below any variant's a_min, that variant
    cannot satisfy both floors at any alpha — a JOINT INFEASIBILITY reported by
    name (like W3's Lit variants), never clamped into a number that looks solved.

    Returns (alpha, [(id, a_min, a_max)], infeasible_ids). Refuses on an empty
    population or a floor unreachable at alpha 0."""
    if not rows:
        raise ValueError("solve_ghost_alpha_for_mode: empty population — nothing was solved")
    per = []
    for vid, lit, ground, ghost, a_min in rows:
        a_max = alpha_max_vs_lit(lit, ground, ghost, lit_floor)
        if a_max is None:
            raise ValueError(f"{vid}: lit/ground span cannot reach a {lit_floor}:1 "
                             f"lit-vs-ghost floor at any alpha; the palette is the defect")
        per.append((vid, a_min, a_max))
    alpha = min(a for _v, _lo, a in per)
    infeasible = [v for v, lo, _hi in per if alpha < lo]
    return alpha, per, infeasible


def derive_ghost_through_alpha(lit, ground, alpha, ceiling_lc=None):
    """The DECLARED ghost whose RENDERED form (at `alpha` over ground) is the ceiling ghost.

    ⚑ THE SOLVE HAPPENS ON THE SCREEN'S SEGMENT AND IS INVERTED TO THE DECLARATION.
    `derive_ghost_ceiling` answers "which point on lit->ground is the most visible
    ghost that does not read as text" — but the renderer composites the declared
    colour at `alpha`, and source-over toward ground is a lerp toward ground, so
    the eye sees t' = 1 - alpha(1 - t), not t.  Solving the ceiling on t' and then
    emitting t = 1 - (1 - t')/alpha makes the gated ghost and the seen ghost the
    same point — the property @GHOSTCOMP measures.

    ⚑ THE REACHABLE WINDOW IS [1 - alpha, 1].  A declared colour cannot lie beyond
    the lit end, so t' >= 1 - alpha.  The target is therefore
    max(t_ceiling, 1 - alpha): the ceiling point when it is reachable, and the lit
    colour itself (t = 0) when alpha is the binding constraint — which, at the
    solved global alpha (`solve_ghost_alpha`), is exactly the case on the variant
    whose a_min set it.  If even 1 - alpha exceeds the FLOOR's boundary the
    caller's alpha was not solved by this module, and `check_ghost_composite`
    will say so; this function refuses nothing it cannot see.

    Returns (declared_colour, t_declared, t_screen)."""
    if ceiling_lc is None:
        ceiling_lc = C.GHOST_READABLE_LC
    t_c, _lc = solve_ceiling_t(lit, ground, ceiling_lc)
    if t_c is None:
        t_c = 0.5                              # the scan's own fallback, kept
    t_screen = max(t_c, 1.0 - alpha)
    t_declared = 1.0 - (1.0 - t_screen) / alpha
    t_declared = min(1.0, max(0.0, t_declared))   # 1e-16 noise, never a real clamp
    # ⚑ THE STRICT BOUND IS CHECKED ON THE QUANTISED PIPELINE, NOT THE REAL ONE.
    # The boundary was found in continuous t, but the declared colour is 8-bit and
    # the renderer composites 8-bit — two roundings that can land the seen ghost a
    # few tenths of an Lc OVER the ceiling (measured: 30.2 against 30 on EL-Openglo).
    # Step the declaration toward ground until the composite of the ROUNDED colour
    # is strictly under; each step is one part in 4096 of the segment.
    import palette_graph as _pg
    colour = C._lerp(lit, ground, t_declared)
    for _ in range(64):
        seen = _pg.composite(colour, ground, alpha)
        if abs(C.apca_Lc(seen, ground)) < ceiling_lc:
            break
        t_declared = min(1.0, t_declared + 1.0 / 4096)
        colour = C._lerp(lit, ground, t_declared)
    return colour, t_declared, t_screen


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
