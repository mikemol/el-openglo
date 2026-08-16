"""netlist_render — the constraint graph as a picture, and as a sequence.

⚑ THE POINT IS TO SEE HOW VALUES RESOLVE, NOT TO HAVE A DIAGRAM.  A static
node-and-edge drawing of 21 nodes says almost nothing; what a reader wants is
WHICH edges are constraints and which are arrows, WHERE the boundary condition
sits, WHICH loops can hide an undetectable failure, and HOW the interior collapses
into the terminals. So the emitter carries the graph's own structure — family,
pinned-ness, cycle membership, elimination step — rather than laying out a bag of
circles.

Two views, one emitter, because the sequence IS the static view replayed:

    --dot           the whole graph, coloured by family, terminals boxed
    --step N        the graph as it stands after N eliminations, fill-in marked

⚑ AND THE ELIMINATION ORDER IS A GAUGE, WHICH THE SEQUENCE MAKES VISIBLE.
Measured: `min_degree` costs 62 Q over 15 steps; the fixed order the relations
check uses costs 68 Q. Same terminals, same answer, different cost — which is
`Elimination.as_gauge()` and `.as_cost()` being genuinely separate, not a
discrepancy. A reader watching the sequence is watching one gauge choice among
many, and the cost counter says what it bought.

⚑ NETWORKX IS USED FOR LAYOUT ONLY, NEVER FOR THE SOLVE.  The elimination is
gcalc's; networkx computes positions so the picture is stable between frames, and
nothing about the answer passes through it. Emitting `.dot` directly means the
render works with `dot` alone when networkx is absent — a SKIP that is counted and
printed rather than a failure.
"""
from __future__ import annotations

import palette_graph as PG

# Family -> (colour, style). The colours are Okabe-Ito members, which is not
# decoration: this repo's own `role_theme` solves role->colour for CVD separation,
# and a diagram about a colour-accessibility graph that was itself illegible to a
# CVD reader would be the instrument failing in its own domain.
FAMILY_STYLE = {
    PG.SEPARATION: ("#0072b2", "solid"),    # blue
    PG.LEGIBILITY: ("#009e73", "solid"),    # bluegreen
    PG.GEOMETRY:   ("#d55e00", "solid"),    # vermillion
    PG.DERIVATION: ("#cc79a7", "dashed"),   # purple — an ARROW, not a constraint
}


def _terminals():
    import palette_relations as PR
    return set(PR.terminals())


def _geometry_nodes():
    return {n.key for n in PG.GEOMETRY_NODES}


def cycle_edges():
    """Every edge that lies on at least one fundamental cycle.

    ⚑ THE LOOPS ARE THE POINT OF DRAWING THIS AT ALL.  b1 = 24 counts how many
    independent gluing failures the graph can hide — places where pairwise-satisfied
    constraints need not compose — and an edge on no cycle cannot participate in
    one. Marking them separates 'this constraint can fail alone' from 'this
    constraint can fail in company', which is the distinction every per-edge check
    in this tree is blind to."""
    try:
        import sys
        import os
        gc = os.path.expanduser("~/github/gcalculus")
        if os.path.isdir(gc) and gc not in sys.path:
            sys.path.insert(0, gc)
        from gcalc import solver as S
    except Exception:                                    # pragma: no cover
        return None
    raw = PG.netlist_edges(constraining_only=True)
    ns = list(PG.nodes(constraining_only=True))
    adj = {}
    for (u, v) in raw:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
    seen, on_cycle = set(), set()
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
            stack.extend(adj.get(w, set()) - seen)
        sub = {k: g for k, g in raw.items() if k[0] in comp and k[1] in comp}
        if len(sub) < len(comp):
            continue
        for cyc in S.cycle_basis(sorted(comp), sub):
            on_cycle |= set(cyc)
    return on_cycle


def frames(keep=None):
    """[(step, eliminated, nodes, edges, fill_in, q)] — the elimination sequence.

    Drives `Frozen` directly rather than using `stream_steps`, which deliberately
    holds nothing (its docstring: retention is the carrier's job, not the read's).
    A picture needs the state, so this is the read that keeps it — and it keeps
    only what a frame draws."""
    import os
    import sys
    gc = os.path.expanduser("~/github/gcalculus")
    if os.path.isdir(gc) and gc not in sys.path:
        sys.path.insert(0, gc)
    from gcalc import solver as S

    keep = tuple(keep or _terminals())
    raw = PG.netlist_edges(constraining_only=True)
    fz = S.freeze(list(PG.nodes(constraining_only=True)), S.netlist(raw), keep=keep)

    out = [(0, None, tuple(fz.nodes), tuple(sorted(fz.edges)), (), 0)]
    prev = set(fz.edges)
    step = 0
    while True:
        nxt = S.min_degree(fz)
        if nxt is None:
            break
        fz = fz.step(nxt)
        step += 1
        now = set(fz.edges)
        out.append((step, nxt, tuple(fz.nodes), tuple(sorted(now)),
                    tuple(sorted(now - prev)), sum(m for _, m in fz.cost)))
        prev = now
    return out


def as_dot(step=None, keep=None):
    """The graph as graphviz. `step=None` is the whole netlist; `step=N` is the
    state after N eliminations, with fill-in edges marked."""
    terms = _terminals()
    geom = _geometry_nodes()
    on_cycle = cycle_edges() or set()

    fr = frames(keep) if step is not None else None
    if fr is not None:
        step = max(0, min(step, len(fr) - 1))
        _s, elim, live_nodes, live_edges, fill_in, q = fr[step]
        live = set(live_nodes)
        live_e = set(live_edges)
        fill = set(fill_in)
    else:
        elim, q, fill = None, None, set()
        live = set(PG.nodes())
        live_e = None

    L = ["graph netlist {",
         '  graph [fontname="monospace", labelloc="t", fontsize=11];',
         '  node  [fontname="monospace", fontsize=10, shape=ellipse];',
         '  edge  [fontname="monospace", fontsize=8];']

    if fr is not None:
        title = (f"elimination step {step} of {len(fr) - 1}"
                 + (f" — eliminated {elim}" if elim else " — the netlist as given")
                 + f"\\n{len(live)} nodes, {len(live_e)} edges, {q} Q spent")
    else:
        title = (f"the constraint netlist — {len(PG.nodes())} nodes, "
                 f"{len(PG.edges())} edges\\nb1 = {len(_basis())} independent "
                 f"cycles; terminals are boxed")
    L.append(f'  label="{title}";')

    for n in sorted(set(PG.nodes()) | terms):
        if n not in live:
            # ⚑ AN ELIMINATED NODE IS DRAWN FAINT, NOT DELETED. Removing it would
            # make each frame a different graph and the sequence unreadable; the
            # reader is watching ONE graph resolve, not fifteen pictures.
            L.append(f'  "{n}" [style=dotted, color="#999999", '
                     f'fontcolor="#999999"];')
            continue
        shape = "box" if n in terms else "ellipse"
        pen = "2.4" if n in terms else "1.0"
        fill_c = "#f0e442" if n == elim else ("#eeeeee" if n in geom else "white")
        L.append(f'  "{n}" [shape={shape}, penwidth={pen}, style=filled, '
                 f'fillcolor="{fill_c}"];')

    drawn = set()
    for e in PG.edges():
        key = e.key
        if key in drawn:
            continue
        drawn.add(key)
        colour, style = FAMILY_STYLE.get(e.family, ("#555555", "solid"))
        attrs = [f'color="{colour}"', f'style={style}']
        if live_e is not None and key not in live_e:
            attrs = ['color="#dddddd"', "style=dotted"]
        elif key in on_cycle:
            # on a fundamental cycle: this constraint can fail IN COMPANY
            attrs.append("penwidth=2.0")
        L.append(f'  "{e.u}" -- "{e.v}" [{", ".join(attrs)}];')

    if live_e is not None:
        for (u, v) in sorted(fill):
            # ⚑ FILL-IN IS THE STAR->MESH TRANSFORM MADE VISIBLE, and it is the
            # one thing a static picture cannot show: eliminating a node replaces
            # its incident star with a mesh among its neighbours, which is where
            # the Q cost comes from.
            L.append(f'  "{u}" -- "{v}" [color="#d55e00", penwidth=3.0, '
                     f'style=bold, label="fill-in"];')

    L.append("}")
    return "\n".join(L) + "\n"


def _basis():
    """The fundamental cycles, for the static view's label."""
    import os
    import sys
    gc = os.path.expanduser("~/github/gcalculus")
    if os.path.isdir(gc) and gc not in sys.path:
        sys.path.insert(0, gc)
    from gcalc import solver as S
    raw = PG.netlist_edges(constraining_only=True)
    ns = list(PG.nodes(constraining_only=True))
    adj = {}
    for (u, v) in raw:
        adj.setdefault(u, set()).add(v)
        adj.setdefault(v, set()).add(u)
    seen, out = set(), []
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
            stack.extend(adj.get(w, set()) - seen)
        sub = {k: g for k, g in raw.items() if k[0] in comp and k[1] in comp}
        if len(sub) >= len(comp):
            out.extend(S.cycle_basis(sorted(comp), sub))
    return out
