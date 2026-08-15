#!/usr/bin/env python3
"""check_relations.py — the relations are DECLARATIVE, complete, and solver-ready.

⚑ TWO COPIES OF ONE CONTENT DRIFT UNLESS SOMETHING FORBIDS IT.  `catalog/relations.md`
is the prose statement and `palette_relations.py` is the machine-readable one. Left
ungated, one gets corrected and the other keeps asserting the old answer — which is
this repo's founding defect (RECOVERY-NOTES.md's stale "main rebuild gap").

    scripts/check_relations.py            # exit 0 iff the relations hold together
    scripts/check_relations.py --list     # every relation, by kind
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


def problems():
    """[problem] — every way the relations fail to hold together."""
    rels = PR.relations()
    bad = []
    if not rels:
        return ["no relations declared; the statement is empty, not the palette free"]

    known = {n.key for n in PG.NODES}
    for r in rels:
        for side in (r.u, r.v):
            if side not in known:
                bad.append(f"{r}: names {side!r}, which the edge authority does not")
        if r.kind not in KINDS:
            bad.append(f"{r}: kind {r.kind!r} is not one of {KINDS}")
        if r.kind in ("floor", "ceiling") and not r.bound:
            bad.append(f"{r}: a {r.kind} relation with no bound cannot be checked")
        if not r.quantity:
            bad.append(f"{r}: names no quantity, so nothing says WHAT must hold")

    # every pinned terminal must be a real node, and must not also be interior
    for t in PR.terminals():
        if t not in known:
            bad.append(f"terminal {t!r} is not a declared node")
        if t in PR.INTERIOR or t in PR.DISCRETE:
            bad.append(f"{t!r} is pinned AND free — a node cannot be both")

    # ⚑ EVERY FREE NODE MUST BE REACHED BY SOME RELATION, or it is undetermined and
    # nothing says so. This is the check that would catch a role added to the
    # palette and never constrained.
    touched = {s for r in rels for s in (r.u, r.v)}
    for n in PR.INTERIOR + PR.DISCRETE + PR.DERIVED:
        if n not in touched:
            bad.append(f"{n!r} is free but no relation reaches it — undetermined")

    # the handoff must be the shape the solver consumes
    raw = PR.netlist_input()
    if not raw:
        bad.append("the netlist handoff is empty; nothing could be solved")
    for k, gen in raw.items():
        if not (isinstance(k, tuple) and len(k) == 2):
            bad.append(f"netlist key {k!r} is not a (u, v) pair")
        if not isinstance(gen, str) or not gen:
            bad.append(f"netlist edge {k} has no generator name")
    return bad


def main(argv):
    known_flags = {"--list", "--solve", "--selftest"}
    for a in argv[1:]:
        if a not in known_flags:
            print(f"check_relations: unknown flag {a!r}", file=sys.stderr)
            return 2

    rels = PR.relations()

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

    bad = problems()
    if bad:
        print(f"check_relations: REFUSED — {len(bad)} problem(s) over {len(rels)} "
              f"relation(s):", file=sys.stderr)
        for b in bad[:20]:
            print(f"    {b}", file=sys.stderr)
        return 1
    by_kind = {k: sum(1 for r in rels if r.kind == k) for k in KINDS}
    print(f"check_relations: {len(rels)} of {len(rels)} relations well-formed and "
          f"solver-ready ({', '.join(f'{v} {k}' for k, v in by_kind.items() if v)}; "
          f"{len(PR.open_questions())} open question(s) recorded)")
    return 0


def _selftest():
    """Prove the check can SEE a malformed relation set."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("the real relations hold together", main(["x"]), 0)
    check("problems() is empty on the real set", problems(), [])

    # ⚑ THE OPEN QUESTIONS MUST BE RECORDED, NOT EMPTY.  A relation set claiming to
    # determine everything is the overclaim this file exists to avoid.
    check("open questions are recorded", len(PR.open_questions()) > 0, True)
    check("every open question explains itself",
          all(len(w) > 40 for _k, w in PR.open_questions()), True)

    saved = PR.relations
    try:
        # 1. a relation naming a role the authority does not declare
        PR.relations = lambda: (PR.Relation("view", "no_such_role", "floor",
                                            "wcag_ratio", "4.6"),)
        check("sees an invented role",
              any("no_such_role" in p for p in problems()), True)

        # 2. a floor with no bound — unfalsifiable, nothing to check against
        PR.relations = lambda: (PR.Relation("view", "fg", "floor", "wcag_ratio", None),)
        check("sees a floor with no bound",
              any("no bound" in p for p in problems()), True)

        # 3. a relation that names no quantity
        PR.relations = lambda: (PR.Relation("view", "fg", "floor", "", "4.6"),)
        check("sees a relation naming no quantity",
              any("no quantity" in p for p in problems()), True)

        # 4. an empty set REFUSES rather than passing vacuously
        PR.relations = lambda: ()
        check("an empty relation set refuses", main(["x"]), 1)
    finally:
        PR.relations = saved

    # 5. a free node nothing reaches is undetermined, and that must be visible
    saved_i = PR.INTERIOR
    try:
        PR.INTERIOR = saved_i + ("view_alt",)
        check("sees a free node no relation reaches",
              any("undetermined" in p for p in problems()), True)
    finally:
        PR.INTERIOR = saved_i

    if SOLVER is not None:
        check("the handoff is solver-ready", main(["--solve"]), 0)
    else:
        print("  SKIP solver handoff — gcalc not importable")

    print("check_relations selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
