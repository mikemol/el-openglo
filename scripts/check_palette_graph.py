#!/usr/bin/env python3
"""check_palette_graph.py — the constraint graph is ONE authority, and its cycle rank.

`palette_graph` claims to be the single place the palette's constraint edges are named.
That claim is worth exactly what proves it, and there are two things to prove:

  1. THE NAMESPACES ARE TOTAL.  Three vocabularies name these roles — the solver's locals,
     the emitted keys, and the gate's pair names.  If the mapping is partial in either
     direction the module is a FOURTH namespace and strictly worse than the scatter it
     replaced.  This resolves every declared name against the real modules.

  2. THE DECLARED EDGES ARE THE LIVE ONES.  `cvd_gate.ENFORCED`/`SURFACED` are literals;
     if they and the authority disagree, one of them is wrong and nothing else would say so.

    scripts/check_palette_graph.py            # the verdict, as opa_gate palette_graph decides it
    scripts/check_palette_graph.py --json     # the measurement policy/palette_graph.rego decides
    scripts/check_palette_graph.py --roster   # what GRID actually holds, and the keys the walk finds
    scripts/check_palette_graph.py --b1       # the cycle rank, and WHICH cycles
    scripts/check_palette_graph.py --edges    # the edge inventory, by family
    scripts/check_palette_graph.py --selftest # prove this check can SEE a break

⚑ WHY b1 IS A MEASUREMENT AND NOT A STATISTIC.  On a cycle, pairwise-satisfied constraints
need not glue: every individual check passes and the composite is still wrong.  That is the
shape of `phosphor == accent` and `sel_act` at 1.00:1 — both had every check green, and both
were caught by LOOKING.  b1 counts how many independent such failures the graph can hide,
and it is computable from the edge set alone, before any colour is chosen.

⚑ THE WEAKNESS, STATED.  b1 > 0 does NOT mean a defect exists; it bounds how many could hide
undetectably.  This check measures the graph's CAPACITY for undetectable failure, never the
presence of one.  A run that reports 19 cycles has found no bug and is not claiming to.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import palette_graph as PG                                        # noqa: E402

# gcalc is LOCATED, not vendored — same discipline as paperkit in worklist_gate.py.
# A missing optional dependency is a SKIP, counted and printed: a fact about the machine,
# not about the artifact.  NOT CONFIRMED IS NOT FAILED.
_GCALC = os.path.expanduser("~/github/gcalculus")
try:
    if os.path.isdir(_GCALC):
        sys.path.insert(0, _GCALC)
    from gcalc import solver as SOLVER
except Exception:                                                 # pragma: no cover
    SOLVER = None


def _resolve(mod, name):
    """Does `name` exist in `mod`?  Structural, not textual."""
    return name is None or hasattr(mod, name)


def _emitted_keys(grid, _depth=0):
    """Every token key reachable in GRID, found by WALKING rather than by assuming.

    ⚑ I GUESSED THIS SHAPE TWICE AND WAS WRONG TWICE.  GRID is a dict keyed
    `(phosphor, mode)` whose values are `(scheme, dark_counterpart)` PAIRS — so a
    `for variant in grid` loop yields tuple keys, and an `isinstance(v, dict)` filter over
    the values matches neither. Both mistakes produced an EMPTY SET, and an empty set is
    exactly what a vacuous check reports as a pass.

    So this does not encode a shape at all: it recurses through mappings and sequences and
    collects the keys of any dict whose values look like tokens. A third shape change is
    then absorbed rather than silently zeroing the population.

    THE DISCRIMINATOR is a str->str mapping: a token dict maps names to "r,g,b" strings.
    Keying on that rather than on nesting depth is what makes the walk shape-agnostic."""
    if _depth > 4 or grid is None:
        return set()
    if isinstance(grid, dict):
        vals = list(grid.values())
        if vals and all(isinstance(v, str) for v in vals):
            return set(grid)                      # a token dict: names -> "r,g,b"
        out = set()
        for v in vals:
            out |= _emitted_keys(v, _depth + 1)
        return out
    if isinstance(grid, (list, tuple)):
        out = set()
        for v in grid:
            out |= _emitted_keys(v, _depth + 1)
        return out
    return set()


# ⚑ THE NAMESPACE AND AGREEMENT JUDGEMENTS ARE policy/palette_graph.rego's (W50):
# every node's emitted key and gate name resolve, every gate name is claimed, and
# the authority's pairs are cvd_gate's. THE EMITTED KEY is read from the AUTHORED
# fallback tables in make_schemes (running the solver is too slow for a gate) —
# check_palette_chain.py separately gates that the two agree.


def components(ns, raw):
    """The connected components of the constraint graph, as node lists.

    ⚑ CONNECTIVITY IS NOT AN ASSUMPTION THIS GRAPH SATISFIES.  The selection tokens
    (`sel_bg`, `sel_fg`, `sel_act`) are judged only against each other, so they form a
    SECOND component with no edge to the body/semantic constellation."""
    adj = {}
    for (u, v) in raw:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
    seen, comps = set(), []
    for v in ns:
        if v in seen:
            continue
        comp, stack = [], [v]
        while stack:
            w = stack.pop()
            if w in seen:
                continue
            seen.add(w)
            comp.append(w)
            stack.extend(adj.get(w, ()) - seen)
        comps.append(sorted(comp))
    return comps


def cycles():
    """(b1, cycle-list) over the CONSTRAINING edges, PER COMPONENT.

    Uses `solver.cycle_basis`, where `|co-tree| = b1` by construction — one fundamental
    cycle per co-tree edge. Derivation edges are excluded: they carry no floor, so they are
    arrows in the dependency DAG, not constraints that could fail to glue.

    ⚑ PER COMPONENT, AND THIS CHECK GOT IT WRONG FIRST.  `spanning_tree` seeds from
    `nodes[0]` and grows ONE tree, so on a disconnected graph every edge of every other
    component falls into the co-tree and is reported as a fundamental cycle. The tell was
    visible in the output and I nearly missed it: two "cycles" of a SINGLE edge each
    (`sel_bg~sel_fg`, `sel_act~sel_bg`), which no fundamental cycle can be.

    My own docstring had already named the trap — "rather than counting E-V+C and hoping
    the graph is connected" — while the code hoped exactly that. b1 = E - V + C, and the
    C is not decoration."""
    if SOLVER is None:
        return None, []
    raw = PG.netlist_edges(constraining_only=True)
    ns = list(PG.nodes(constraining_only=True))
    out = []
    for comp in components(ns, raw):
        sub = {k: g for k, g in raw.items() if k[0] in comp and k[1] in comp}
        if len(sub) < len(comp):                  # a tree or a forest: no cycle to find
            continue
        out.extend(SOLVER.cycle_basis(comp, sub))
    return len(out), out


def main(argv):
    known = {"--b1", "--edges", "--roster", "--selftest", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_palette_graph: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0

    if "--roster" in argv:
        # ⚑ THIS MODE EXISTS BECAUSE I GUESSED GRID'S SHAPE TWICE AND WAS WRONG TWICE.
        # "What does the authority actually hold?" had no mode, so the answer was being
        # re-derived in the turn from a source read — which is the judgement living outside
        # a program. It reports what it FOUND rather than what it expected, so a third
        # shape change surfaces as a different printout instead of another empty set.
        import make_schemes
        grid = getattr(make_schemes, "GRID", None)
        print(f"GRID is {type(grid).__name__} with {len(grid)} entries")
        for k, v in (grid.items() if isinstance(grid, dict) else enumerate(grid)):
            kinds = ", ".join(type(x).__name__ for x in v) if isinstance(v, tuple) \
                else type(v).__name__
            print(f"  key={k!r:28s} value=({kinds})")
            break
        keys = _emitted_keys(grid)
        print(f"{len(keys)} distinct emitted keys: {', '.join(sorted(keys)) or '(NONE)'}")
        return 0

    if "--edges" in argv:
        # ⚑ THE FAMILY LIST WAS HARDCODED AND WENT STALE THE MOMENT A FAMILY WAS
        # ADDED.  It read (SEPARATION, LEGIBILITY, DERIVATION), so the geometry
        # edges existed in the authority and were INVISIBLE to the mode that lists
        # the authority — a check reporting its own coverage as the tree's content,
        # which is the shape this repo keeps paying for. Derived from the edges now,
        # so a fourth family cannot hide the same way.
        for fam in sorted({e.family for e in PG.edges()}):
            es = PG.edges(family=fam)
            print(f"{fam} ({len(es)}):")
            for e in es:
                cls = f" [{e.cls}]" if e.cls else ""
                print(f"    {e.u:9s} ~ {e.v:9s}{cls}  floor={e.floor}  {e.why}")
        return 0

    if "--b1" in argv:
        b1, cyc = cycles()
        if b1 is None:
            print("check_palette_graph: SKIP — gcalc not importable "
                  f"(looked in {_GCALC}); this is a fact about the machine")
            return 0
        ns = PG.nodes(constraining_only=True)
        es = PG.edges(constraining_only=True)
        print(f"b1 = {b1} independent cycles over {len(ns)} nodes, {len(es)} edges")
        for i, c in enumerate(cyc):
            print(f"  cycle {i + 1}: " + " ".join(f"{u}~{v}" for (u, v) in sorted(c)))
        return 0

    import opa_gate
    return opa_gate.gate("palette_graph")


def measure():
    """The MEASUREMENT policy/palette_graph.rego decides (W50): the authority's
    nodes (`cases`: key + gate name), the emitted keys found by WALKING GRID, the
    gate names cvd_gate's ENFORCED/SURFACED pairs use, the edge count, and per
    class the pairs the authority declares beside the ones cvd_gate declares
    (each pair sorted). That every name resolves both ways and the two pair sets
    agree — and that an empty population is a broken search — is the policy's
    ruling, not here."""
    import cvd_gate
    import make_schemes
    gate_names = set()
    for _, a, b in tuple(cvd_gate.ENFORCED) + tuple(cvd_gate.SURFACED):
        gate_names |= {a, b}
    pairs = {}
    for cls, live in (("enforced", cvd_gate.ENFORCED), ("surfaced", cvd_gate.SURFACED)):
        pairs[cls] = {"authority": sorted(sorted([a, b]) for _, a, b in PG.gate_pairs(cls)),
                      "declared": sorted(sorted([a, b]) for _, a, b in live)}
    return {"cases": [{"id": n.key, "gate": n.gate} for n in PG.NODES],
            "emitted": sorted(_emitted_keys(getattr(make_schemes, "GRID", None))),
            "gate_names": sorted(gate_names), "edges": len(PG.EDGES), "pairs": pairs}


def _selftest():
    """Prove the scan can SEE each break it claims to look for.

    ⚑ AN ALL-CLEAR THAT HAS NEVER BEEN SHOWN TO DIFFER FROM A FOUND-SOMETHING IS NOT A
    MEASUREMENT.  Each case below breaks the authority in one specific way and asserts the
    check reports it — including the cycle detector, which must not read a known-cyclic
    graph as a tree."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # ⚑ THE MEASUREMENT MUST SEE each break (W50: that each is a DENY is
    # policy/palette_graph_test.rego's ruling). The walk finds a non-empty key set:
    m = measure()
    check("the GRID walk finds emitted keys (the vacuous-population defect)",
          len(m["emitted"]) > 0, True)

    # 1. an emitted key nothing emits
    saved = PG.NODES
    try:
        PG.NODES = saved + (PG.Node("no_such_token", None, None),)
        m = measure()
        check("sees a bogus emitted key",
              ("no_such_token" in [c["id"] for c in m["cases"]], "no_such_token" in m["emitted"]),
              (True, False))
    finally:
        PG.NODES = saved

    # 2. a gate name cvd_gate does not use
    try:
        PG.NODES = saved + (PG.Node("view", None, "no_such_gate_name"),)
        m = measure()
        check("sees a bogus gate name",
              ("no_such_gate_name" in [c["gate"] for c in m["cases"]], "no_such_gate_name" in m["gate_names"]),
              (True, False))
    finally:
        PG.NODES = saved

    # 3. a declared pair the authority does not carry
    import cvd_gate
    saved_e = cvd_gate.ENFORCED
    try:
        cvd_gate.ENFORCED = tuple(saved_e) + (("bogus~pair", "neg", "visited"),)
        p = measure()["pairs"]["enforced"]
        check("sees a gate/authority disagreement",
              (["neg", "visited"] in p["declared"], ["neg", "visited"] in p["authority"]), (True, False))
    finally:
        cvd_gate.ENFORCED = saved_e

    # 4. the cycle detector is not blind
    if SOLVER is None:
        print("  SKIP cycle detector — gcalc not importable")
    else:
        tri = {("a", "b"): "y1", ("b", "c"): "y2", ("a", "c"): "y3"}
        check("a triangle has b1=1",
              len(SOLVER.cycle_basis(["a", "b", "c"], tri)), 1)
        path = {("a", "b"): "y1", ("b", "c"): "y2"}
        check("a path has b1=0",
              len(SOLVER.cycle_basis(["a", "b", "c"], path)), 0)
        # ⚑ THE DISCONNECTED CASE, WHICH THIS CHECK ORIGINALLY GOT WRONG.  A triangle plus
        # a SEPARATE single edge has b1 = 1, not 2: the lone edge is its own component and
        # a tree. Passing the whole thing to `cycle_basis` in one call reports 2, because
        # `spanning_tree` grows from nodes[0] and files the far component's edge as
        # co-tree. If this case is not exercised the per-component fix is unwitnessed.
        split = {("a", "b"): "y1", ("b", "c"): "y2", ("a", "c"): "y3", ("d", "e"): "y4"}
        naive = len(SOLVER.cycle_basis(["a", "b", "c", "d", "e"], split))
        check("the naive whole-graph call over-counts", naive, 2)
        comps = components(["a", "b", "c", "d", "e"], split)
        check("components() splits them", len(comps), 2)
        per = 0
        for comp in comps:
            sub = {k: g for k, g in split.items() if k[0] in comp and k[1] in comp}
            if len(sub) >= len(comp):
                per += len(SOLVER.cycle_basis(comp, sub))
        check("per-component b1 is 1, not 2", per, 1)
        b1, _ = cycles()
        check("the real graph is measured, not assumed", b1 is not None and b1 > 0, True)

    print("check_palette_graph selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
