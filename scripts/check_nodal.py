#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_nodal.py — the palette's first NUMERIC nodal solve, through gcalc.solver (W221).

    scripts/check_nodal.py            # the verdict, as opa_gate nodal decides it
    scripts/check_nodal.py --json     # the measurement policy/nodal.rego decides
    scripts/check_nodal.py --selftest # the measurement can see a transitive near-collision
    scripts/check_nodal.py --moves    # single-slot moves the objective is BLIND to: max-min vs series

Until this, el-openglo used gcalc only SYMBOLICALLY (netlist_render, check_relations):
no env had ever been bound to measured palette values. This binds one.

⚑ ORIENTATION: MARGIN IS RESISTANCE (operator 2026-10-02, "see how g-calculus
achieves NOT()"; gcalc NOT = x -> 1/x). Each constraint edge's margin m (1.0 =
exactly at its floor) is read as a RESISTANCE and bound as conductance 1/m. Colour
distance obeys the triangle inequality, so distances compose in SERIES, which is
resistance. Effective resistance is then a metric bounded above by the direct edge
(Rayleigh: a parallel path only lowers it). An edge whose own margin clears
(m >= 1) while its effective resistance falls below 1 is a pair that is NEAR
THROUGH OTHER COLOURS - a chain of near neighbours no per-edge gate can see, which
is exactly what the graph's b1 > 0 loops can hide.

Margins, per palette_graph edge floor kind:
    "reference_floors"        worst-view normalized q (cvd_gate._worst_normalized)
    numeric, LEGIBILITY       WCAG ratio / floor
    numeric, SEPARATION       raw worst-view dE / floor (the hot prune's own metric)
    anything else             WITHHELD: an APCA argmax, a ceiling or a composite
                              floor has no margin form here yet; never guessed

⚑ THE ABOVE READING IS RETIRED FOR SEPARATION (2026-10-02, measured): with margin
as resistance, effective resistance over the dense constraint graph read 177 of
192 edges as "near through other colours" - it measures how CONNECTED two colours
are, not how separated. gcalc's own position (families/operator/machine.py:424)
is that conductance is the physics and min its mass-losing shadow, so the policy
now judges the SEPARATION OBJECTIVE: margins as CONDUCTANCES composed in SERIES
(AND = 1/sum(1/q), a smooth min). `--json` emits move visibility; `measure()`
and `solve()` stay for the linear relations (the ghost divider pilot).

⚑ WEAKNESS: series is strictly monotone in every margin, so N2 can deny only a
move that leaves every margin exactly unchanged - falsifiable (policy test) but
near-certain to admit. The comparison it records (max-min blind to 129 of 1079
moves, series to 0) is the information; the verdict is the guard that it stays so.
Geometry edges are out of scope (no colour values).
"""

import json
import os
import sys
from fractions import Fraction

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _gcalc():
    gc = os.path.expanduser("~/github/gcalculus")
    if os.path.isdir(gc) and gc not in sys.path:
        sys.path.insert(0, gc)
    from gcalc import solver as S

    return S


def margin(edge, tok, C, floors):
    """(margin, None) or (None, why-withheld) for one palette_graph edge on one variant."""
    if edge.u not in tok or edge.v not in tok:
        return None, "a node has no colour in this variant's tokens"
    a, b = C.rgb(tok[edge.u]), C.rgb(tok[edge.v])
    f = edge.floor
    if f == "reference_floors":
        return float(C._worst_normalized(a, b, floors)[0]), None
    try:
        x = float(f)
    except (TypeError, ValueError):
        return None, f"floor kind {f!r} has no margin form here"
    import palette_graph as PG

    if edge.family == PG.LEGIBILITY:
        return C.wcag_ratio(a, b) / x, None
    return float(C.worst_view_dE(a, b)[0]) / x, None


def components(nodes, keys):
    adj = {n: set() for n in nodes}
    for u, v in keys:
        adj[u].add(v)
        adj[v].add(u)
    seen, out = set(), []
    for n in nodes:
        if n in seen:
            continue
        comp, stack = [], [n]
        while stack:
            w = stack.pop()
            if w not in seen:
                seen.add(w)
                comp.append(w)
                stack.extend(adj[w] - seen)
        out.append(sorted(comp))
    return out


def solve(margins, S):
    """{(u,v): r_eff} over the network whose edge conductance is 1/margin."""
    gen = {k: f"y_{k[0]}_{k[1]}" for k in margins}
    env = {gen[k]: 1 / Fraction(m).limit_denominator(10**6) for k, m in margins.items()}
    nodes = sorted({n for k in margins for n in k})
    out = {}
    for comp in components(nodes, margins):
        sub = {k: g for k, g in gen.items() if k[0] in comp}
        if not sub:
            continue
        net = S.netlist(sub)
        for k in sub:
            out[k] = float(S.r_eff(comp, net, env, k[0], k[1]))
    return out


def measure():
    import cvd_gate as C
    import make_palette as mp
    import palette_graph as PG

    S = _gcalc()
    floors = C.reference_floors()
    edges = [e for e in PG.edges() if e.family in (PG.SEPARATION, PG.LEGIBILITY)]
    cases, withheld = [], []
    for t, _d in mp.build_grid().values():
        margins = {}
        for e in edges:
            m, why = margin(e, t, C, floors)
            if m is None:
                withheld.append(f"{t['id']}: {e.u}~{e.v}: {why}")
            elif m > 0:
                margins[e.key] = min(
                    margins.get(e.key, m), m
                )  # a doubled edge keeps its tighter margin
        r = solve(margins, S)
        for k, m in sorted(margins.items()):
            cases.append(
                {
                    "id": f"{t['id']}/{k[0]}~{k[1]}",
                    "variant": t["id"],
                    "u": k[0],
                    "v": k[1],
                    "margin": m,
                    "r_eff": r.get(k),
                }
            )
    return {"cases": cases, "withheld": sorted(set(withheld))}


def series(qs):
    """gcalc SERIES composition of margins read as conductances: AND = 1 / sum(1/q),
    a SMOOTH min - every margin moves it (machine.py:424: min is its shadow)."""
    return 1.0 / sum(1.0 / q for q in qs)


def move_visibility():
    """Per variant: of every single-slot candidate swap in the window semantic set,
    how many change the objective under the shipped hard max-min and under SERIES.

    The objective is over every pair of the constellation (palette_graph.CONSTELLATION,
    the slots plus the fixed `fg` anchor), margin = worst-view normalized q - exactly
    solve_semantic_set.min_pair's population. palette_relations' docstring measured
    the max-min side once (47% of moves change nothing); this re-measures both."""
    import cvd_gate as C
    import make_palette as mp
    import palette_graph as PG

    floors = C.reference_floors()
    out = []
    for t, _d in mp.build_grid().values():
        vid = t["id"]
        ground, hot = C.rgb(t["view"]), C.rgb(t["focus"])
        chosen = {k: C.rgb(t[k]) for k in PG.SEMANTIC}
        anchor = C.rgb(t["fg"])

        def qs(ch, anchor=anchor):
            vals = list(ch.values()) + [anchor]
            return [
                max(1e-9, C._worst_normalized(vals[i], vals[j], floors)[0])
                for i in range(len(vals))
                for j in range(i + 1, len(vals))
            ]

        base = qs(chosen)
        b_min, b_ser = min(base), series(base)
        moves = flat_min = flat_ser = 0
        for k in PG.SEMANTIC:
            for c in mp._candidates(mp._sect(k, vid), ground, 4.6, hot):
                if c == chosen[k]:
                    continue
                trial = qs(dict(chosen, **{k: c}))
                moves += 1
                flat_min += abs(min(trial) - b_min) < 1e-12
                flat_ser += abs(series(trial) - b_ser) < 1e-12
        out.append(
            {
                "variant": vid,
                "moves": moves,
                "flat_max_min": flat_min,
                "flat_series": flat_ser,
            }
        )
    return out


def divider_interior(Va, Vb, S, y1=1, y2=1):
    """The interior potential of lit -(y1)- ghost -(y2)- ground with both ends pinned,
    read off gcalc.solver.laplacian: the Kirchhoff row of the interior node,
    L_MM V_M = -(L_Ma V_a + L_Mb V_b). Exact over Fraction."""
    nodes = ["fg", "fg_in", "view"]
    net = S.netlist({("fg", "fg_in"): "y1", ("fg_in", "view"): "y2"})
    L, idx = S.laplacian(nodes, net, {"y1": Fraction(y1), "y2": Fraction(y2)})
    i = {n: dict(idx.items())[n] for n in nodes}
    m, a, b = i["fg_in"], i["fg"], i["view"]
    return -(L[m][a] * Va + L[m][b] * Vb) / L[m][m]


def ghost_pilot():
    """W221 pilot: ghost_solve's closed form y = sqrt(ab) against the divider solve.

    The ghost's balance (ghost_solve: a/y = y/b) is a divider in LOG offset
    luminance with equal conductances - log y = (log a + log b)/2 is the interior
    potential of a two-resistor chain. This reads it from gcalc's Laplacian instead
    of the hand-derived formula, per variant, and reports the difference."""
    import math

    import cvd_gate as C
    import ghost_solve as GS
    import make_palette as mp

    S = _gcalc()
    out = []
    for t, _d in mp.build_grid().values():
        lit, ground = C.rgb(t["fg"]), C.rgb(t["view"])
        a, b = GS.offsets(lit, ground)
        Vm = divider_interior(Fraction(math.log(a)), Fraction(math.log(b)), S)
        y_solver = math.exp(float(Vm))
        y_closed = GS.balance_luminance(lit, ground)
        out.append(
            {
                "variant": t["id"],
                "closed_form": y_closed,
                "solver": y_solver,
                "rel_diff": abs(y_solver - y_closed) / y_closed,
            }
        )
    return out


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    S = _gcalc()
    # a lone edge: r_eff IS its margin (resistance in, resistance out)
    r = solve({("a", "b"): 2.0}, S)
    check(
        "a lone edge's effective resistance is its margin", round(r[("a", "b")], 6), 2.0
    )
    # the transitive near-collision: a~c clears alone (m=1.5) but a~b~c is a near
    # chain (0.4 + 0.4 in series = 0.8), and in parallel 1.5 || 0.8 < 1
    r = solve({("a", "c"): 1.5, ("a", "b"): 0.4, ("b", "c"): 0.4}, S)
    check(
        "a clearing edge with a near chain beside it reads below 1",
        r[("a", "c")] < 1.0,
        True,
    )
    check(
        "Rayleigh: effective resistance never exceeds the direct edge",
        all(
            r[k] <= m + 1e-12
            for k, m in {("a", "c"): 1.5, ("a", "b"): 0.4, ("b", "c"): 0.4}.items()
        ),
        True,
    )
    check(
        "two components are solved apart, not as one singular system",
        sorted(solve({("a", "b"): 1.0, ("c", "d"): 3.0}, S).values()),
        [1.0, 3.0],
    )
    # the divider: equal conductances put the interior at the midpoint; 3:1 at the weighted mean
    check(
        "an equal divider puts the interior at the midpoint",
        divider_interior(Fraction(1), Fraction(0), S),
        Fraction(1, 2),
    )
    check(
        "a 3:1 divider is the conductance-weighted mean (V_M = y1/(y1+y2) for V=1,0)",
        divider_interior(Fraction(1), Fraction(0), S, 3, 1),
        Fraction(3, 4),
    )
    # series is a SMOOTH min: below min, and moved by a non-binding margin
    check(
        "series lies below the min (AND(a,b) < min(a,b))",
        series([2.0, 3.0]) < 2.0,
        True,
    )
    check(
        "a non-binding margin moves series but not min",
        (min([2.0, 3.0]) == min([2.0, 5.0]), series([2.0, 3.0]) != series([2.0, 5.0])),
        (True, True),
    )
    print("check_nodal selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest", "--moves", "--ghost"}:
            print(f"check_nodal: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--ghost" in argv:
        rows = ghost_pilot()
        for r in rows:
            print(
                f"{r['variant']}\tclosed form {r['closed_form']:.12f}\tsolver {r['solver']:.12f}"
                f"\trel diff {r['rel_diff']:.2e}"
            )
        print(
            f"max rel diff over {len(rows)} variants: {max(r['rel_diff'] for r in rows):.2e}"
        )
        return 0
    if "--moves" in argv:
        rows = move_visibility()
        for r in rows:
            print(
                f"{r['variant']}\t{r['moves']} moves\tmax-min blind to {r['flat_max_min']} of {r['moves']}"
                f"\tseries blind to {r['flat_series']} of {r['moves']}"
            )
        m = sum(r["moves"] for r in rows)
        print(
            f"total: max-min blind to {sum(r['flat_max_min'] for r in rows)} of {m}; "
            f"series blind to {sum(r['flat_series'] for r in rows)} of {m}"
        )
        return 0
    if "--json" in argv:
        doc = {"cases": move_visibility(), "ghost": [], "withheld": []}
        try:
            doc["ghost"] = ghost_pilot()
        except ImportError as e:  # gcalc is LOCATED, not a dependency (pyproject)
            doc["withheld"].append(
                f"ghost: gcalc not importable here ({e}); the divider witness was not run"
            )
        print(json.dumps(doc, indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("nodal")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
