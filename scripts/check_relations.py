#!/usr/bin/env python3
"""check_relations.py — the relations are DECLARATIVE, complete, and solver-ready.

⚑ TWO COPIES OF ONE CONTENT DRIFT UNLESS SOMETHING FORBIDS IT.  `catalog/relations.md`
is the prose statement and `palette_relations.py` is the machine-readable one. Left
ungated, one gets corrected and the other keeps asserting the old answer — which is
this repo's founding defect (RECOVERY-NOTES.md's stale "main rebuild gap").

    scripts/check_relations.py            # the verdict, as opa_gate relations decides it
    scripts/check_relations.py --json     # the measurement policy/relations.rego decides
    scripts/check_relations.py --list    # every relation, by kind
    scripts/check_relations.py --solve    # hand them to gcalc and report what it determines
    scripts/check_relations.py --selftest

⚑ WHAT IS ACTUALLY CHECKED.  Three things, none of which is "the file exists":
  1. every node a relation names is a node the authority declares — so the relations
     cannot invent a role, which would make them a FOURTH namespace;
  2. every relation is DECLARATIVE — it names a quantity and a kind, never a search;
  3. the netlist handoff is accepted by `gcalc.solver` and the terminals are pinnable,
     i.e. the relations are solver-ready rather than merely well-formed prose.

⚑ THE WEAKNESS, STATED.  This gates that the relations are WELL-FORMED and CONSUMABLE.
It does not gate that they are TRUE of the palette — that is what @SEPARATION, @GHOST
and @MARGIN do — and it emphatically does not claim the relations are COMPLETE. What
they do not determine is recorded in `open_questions()` and printed by --list, because
a relation set that hid its gaps would read as finished.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import palette_graph as PG                                        # noqa: E402
import palette_relations as PR                                    # noqa: E402

_GCALC = os.path.expanduser("~/github/gcalculus")
try:
    if os.path.isdir(_GCALC):
        sys.path.insert(0, _GCALC)
    from gcalc import solver as SOLVER
    from gcalc import carrier as CARRIER
except Exception:                                                 # pragma: no cover
    SOLVER = CARRIER = None

KINDS = ("floor", "ceiling", "balance", "arrow")


def measure():
    """The MEASUREMENT policy/relations.rego decides (W50): every relation's
    (u, v, kind, quantity, bound); the nodes the edge authority declares; the
    pinned terminals; the free nodes; the netlist handoff's edges (is the key a
    (u, v) pair, what generator name); the number of open questions. An invented
    role, a boundless floor, an unreached free node, an empty handoff are defects
    by the policy's ruling, not here.

    ⚑ `declared_nodes()`, NOT `NODES` — the latter is the colour half only, and
    asking it refused every geometry edge for naming a role the authority "does
    not" declare. The union lives in the authority so a consumer cannot ask the
    wrong half."""
    raw = PR.netlist_input()
    return {
        "known": sorted(n.key for n in PG.declared_nodes()),
        "terminals": sorted(PR.terminals()),
        # INTERIOR and DISCRETE are the free nodes (a terminal must not be one);
        # DERIVED is not free but must, like them, be reached by a relation
        "free": list(PR.INTERIOR + PR.DISCRETE),
        "derived": list(PR.DERIVED),
        "open_questions": len(PR.open_questions()),
        "netlist": [{"key": "~".join(map(str, k)) if isinstance(k, tuple) else repr(k),
                     "pair": isinstance(k, tuple) and len(k) == 2,
                     "generator": gen if isinstance(gen, str) else ""}
                    for k, gen in raw.items()],
        "cases": [{"u": r.u, "v": r.v, "kind": r.kind, "quantity": r.quantity or "",
                   "bound": r.bound if r.bound else None} for r in PR.relations()],
    }


def main(argv):
    known_flags = {"--list", "--solve", "--selftest", "--json"}
    for a in argv[1:]:
        if a not in known_flags:
            print(f"check_relations: unknown flag {a!r}", file=sys.stderr)
            return 2

    rels = PR.relations()

    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0

    if "--list" in argv:
        for kind in KINDS:
            group = [r for r in rels if r.kind == kind]
            print(f"{kind} ({len(group)}):")
            for r in group:
                b = f" bound={r.bound}" if r.bound else ""
                print(f"    {r.u:9s} ~ {r.v:9s}  {r.quantity}{b}")
        print("\npinned terminals:")
        for t, why in sorted(PR.terminals().items()):
            print(f"    {t:9s}  {why}")
        print("\nOPEN — what these relations do not determine:")
        for key, why in PR.open_questions():
            print(f"    {key}: {why}")
        return 0

    if "--solve" in argv:
        if SOLVER is None:
            print(f"check_relations: SKIP — gcalc not importable (looked in {_GCALC}); "
                  f"a fact about the machine, not the relations")
            return 0
        raw = PR.netlist_input()
        nodes = sorted({n for k in raw for n in k})
        edges = SOLVER.netlist(raw)
        keep = tuple(PR.terminals())
        interior = [n for n in nodes if n not in keep]
        sec, out_edges, _gauge = SOLVER.frontier_solve(nodes, edges, interior, keep=keep)
        print(f"nodes={len(nodes)} edges={len(raw)} pinned={len(keep)}")
        print(f"eliminating {len(interior)} interior node(s) -> "
              f"{len(out_edges)} surviving edge(s), {SOLVER.total_cost(sec)} Q, "
              f"verdict={SOLVER.verdict(sec)}")
        for k in sorted(out_edges):
            t = out_edges[k]
            print(f"    {k[0]} ~ {k[1]}: {len(tuple(CARRIER.parts_of(t)))} part(s), "
                  f"support={sorted(CARRIER.support(t))[:4]}")
        return 0

    import opa_gate
    return opa_gate.gate("relations")


def _selftest():
    """Prove the MEASUREMENT can see a malformed relation set; what is a defect is
    policy/relations_test.rego's business (W50)."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    m = measure()
    check("the real relations are measured", len(m["cases"]) > 0, True)
    # ⚑ open-question PROSE is not a policy fact; the count is (R6)
    check("every open question explains itself",
          all(len(w) > 40 for _k, w in PR.open_questions()), True)

    saved = PR.relations
    try:
        PR.relations = lambda: (PR.Relation("view", "no_such_role", "floor",
                                            "wcag_ratio", "4.6"),)
        check("an invented role is measured as named",
              measure()["cases"][0]["v"] == "no_such_role"
              and "no_such_role" not in measure()["known"], True)
        PR.relations = lambda: (PR.Relation("view", "fg", "floor", "wcag_ratio", None),)
        check("a floor with no bound is measured as bound null",
              measure()["cases"][0]["bound"], None)
        PR.relations = lambda: ()
        check("an empty relation set measures as empty", measure()["cases"], [])
    finally:
        PR.relations = saved

    saved_i = PR.INTERIOR
    try:
        PR.INTERIOR = saved_i + ("view_alt",)
        check("an added free node is measured", "view_alt" in measure()["free"], True)
    finally:
        PR.INTERIOR = saved_i

    # ⚑ ACCEPTANCE, NOT THE SOLVE (2026-09-25).  This arm ran the full frontier
    # elimination (`--solve`): 66 s of CPU, over paperkit's 60 s RLIMIT_CPU per
    # check — so under the gate the kernel killed it (SIGXCPU) every time, and the
    # uncapped replay passed, which the gate reported as a FLAKE three commits
    # running. It was deterministic. Claim 3 is that the handoff is ACCEPTED and
    # the terminals PINNABLE; that is what is asked here. `--solve` keeps the
    # elimination for a human, uncapped.
    if SOLVER is not None:
        raw = PR.netlist_input()
        nodes = {n for k in raw for n in k}
        edges = SOLVER.netlist(raw)
        check("the handoff is accepted by gcalc.solver.netlist",
              len(edges) == len(raw) and len(raw) > 0, True)
        check("every pinned terminal is a node of the handoff",
              sorted(set(PR.terminals()) - nodes), [])
    else:
        print("  SKIP solver handoff — gcalc not importable")

    print("check_relations selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
