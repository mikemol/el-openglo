"""palette_relations — the palette's constraints as DECLARATIVE RELATIONS.

⚑ THIS MODULE COMPUTES NOTHING.  It states what must hold, in the shape
`gcalc.solver` consumes: `{(u, v): generator-name}` plus an `env` binding names to
values. Everything else — elimination order, cost, the verdict — is the solver's,
and every scalar is a READ taken at a declared boundary.

The prose companion is `catalog/relations.md`; this is the same content in the
form a solver can accept, and `scripts/check_relations.py` gates that the two
agree rather than letting a second copy drift.

⚑ WHY A RELATION AND NOT A PROCEDURE.  The current solver searches: a max-min
hillclimb with restarts. Measured, that encoding is BLIND to most of the palette
at any step — 47% of single-slot moves change the objective not at all, and of
117 moves on slots outside the binding pair only 26 change it. Restarts exist to
re-roll out of the resulting flat regions. That is a fact about the ENCODING, and
the repair is to state the relation and hand it to a solver, not to buy more
re-rolls.

⚑ AND THE GHOST IS THE PROOF THAT THIS WORKS.  `lit ── ghost ── ground` is a
voltage divider: pin the terminals and the interior node is DETERMINED. Verified
through `gcalc.solver.laplacian` — `V_M = y1/(y1+y2)` exactly over `Fraction`, and
eliminating the interior node leaves ONE edge carrying `y1·y2/(y1+y2)`, which is
`AND`, at a cost of 1 Q. No search. `ghost_solve.py` derives that closed form by
hand, which is a REIMPLEMENTATION of what the solver returns as a term — recorded
here as a defect of the encoding, not defended.
"""
from __future__ import annotations

import palette_graph as _PG

# ── the roles, split by what determines them ─────────────────────────────────
#
# ⚑ PINNED IS A ROLE, NOT A PROPERTY.  These three are pinned because the theme's
# IDENTITY is chosen rather than solved (hue seed, polarity); everything else is a
# consequence. A relation set that pins something else describes a different
# palette, not a broken one.

PINNED = ("view", "fg", "fg_act")

# Determined by a continuous relation once the pinned terminals are fixed.
INTERIOR = ("fg_in",)

# Determined by a DISCRETE choice — which candidate occupies each slot.
DISCRETE = _PG.SEMANTIC

# Computed from other nodes by a fixed transform, carrying no floor.
DERIVED = ("hover", "sel_bg", "sel_fg", "sel_act")


class Relation:
    """One thing that must hold, between two nodes.

    `kind` is what makes it checkable rather than decorative:
        floor       y >= 1 — the constraint clears
        ceiling     y <  1 — the quantity must stay BELOW a bound (the ghost's
                    readability limit; a strict inequality whose optimum is a
                    supremum that is never attained)
        balance     the two sides are equal — a fixed point of the involution
        arrow       b is computed FROM a; no floor, not a constraint
    """
    __slots__ = ("u", "v", "kind", "quantity", "bound", "why")

    def __init__(self, u, v, kind, quantity, bound=None, why=""):
        self.u, self.v, self.kind = u, v, kind
        self.quantity, self.bound, self.why = quantity, bound, why

    @property
    def generator(self):
        """The edge's name in the netlist — what `env` will bind."""
        a, b = (self.u, self.v) if self.u <= self.v else (self.v, self.u)
        return f"y_{a}_{b}"

    def __repr__(self):
        return f"<{self.kind} {self.u}~{self.v}>"


def relations():
    """Every relation, derived from the ONE edge authority.

    ⚑ DERIVED FROM palette_graph, NEVER RESTATED.  A second hand-written list of
    edges is the exact defect `palette_graph` was built to end: the table, the
    gate and the objective drifting apart with nothing able to notice."""
    out = []
    for e in _PG.edges():
        if e.family == _PG.DERIVATION:
            out.append(Relation(e.u, e.v, "arrow", "transform", None, e.why))
        elif e.family == _PG.LEGIBILITY:
            kind = "ceiling" if "ceiling" in (e.why or "") else "floor"
            out.append(Relation(e.u, e.v, kind, "wcag_ratio", e.floor, e.why))
        elif e.family == _PG.GEOMETRY:
            # ⚑ A STROKE WIDTH IS NOT A COLOUR DISTANCE, AND SAYING SO MATTERS.
            # The else-branch below labels every non-legibility edge `worst_view_dE`,
            # which silently gave the geometry edges the COLOUR metric — the same
            # kind-confusion `_worst_normalized` reading only `floors["enforced"]`
            # had. The carrier is shared (a dimensionless ratio clearing 1.0); the
            # QUANTITY is not, and a relation that names the wrong one cannot be
            # checked against anything real.
            out.append(Relation(e.u, e.v, "floor", "length_ratio", e.floor, e.why))
        else:
            out.append(Relation(e.u, e.v, "floor", "worst_view_dE", e.floor, e.why))

    # ⚑ THE SERIES CHAIN IS A RELATION NOTHING ELSE STATES.  The pairwise edges
    # say lit~ghost and ghost~ground each clear; they do NOT say the ghost BALANCES
    # them, which is the relation that DETERMINES it. It is the composite, and it
    # is why the ghost needs no search.
    out.append(Relation("fg", "view", "balance", "series_through_fg_in",
                        None, "AND(y(fg,fg_in), y(fg_in,view)) — the divider"))
    return tuple(out)


def netlist_input(constraining_only=True):
    """`{(u, v): generator-name}` — the shape `gcalc.solver.netlist` consumes.

    ⚑ THE HANDOFF, AND IT IS DELIBERATELY THE WHOLE INTERFACE.  Nothing about
    elimination order, cost or verdicts appears here: those are the solver's, and
    a relation that presumed them would be a procedure wearing a relation's
    clothes."""
    out = {}
    for r in relations():
        if constraining_only and r.kind == "arrow":
            continue
        if r.kind == "balance":
            continue                    # a composite, not an edge
        a, b = (r.u, r.v) if r.u <= r.v else (r.v, r.u)
        out[(a, b)] = r.generator
    return out


def terminals():
    """The pinned nodes — the solve's boundary condition.

    A divider needs two fixed terminals; this says which nodes those are and why
    each is fixed, so a reader is never left inferring it from the code."""
    return {
        "view": "the ground: L <= OLED_VOID_MAX_LUM at the seed hue",
        "fg": "the lit phosphor: argmax |Lc| from view, chroma >= floor",
        "fg_act": "the accent: full usable chroma, contrast >= 4.6 vs view",
    }


def open_questions():
    """What these relations do NOT yet determine.

    ⚑ RECORDED AS RESIDUE, NOT OMITTED.  An explanation is a place defects hide,
    and a relation set that quietly covered its gaps would read as complete."""
    return (
        ("discrete-occupancy",
         "A nodal solve gives continuous potentials; slot occupancy is a DISCRETE "
         "choice among ~40 candidates. Voronoi cells over the candidate sites under "
         "the gate's metric are the regions where the answer's SHAPE is constant, "
         "with the Delaunay dual naming which candidate can displace which. The "
         "machinery exists (spanning_tree/cycle_basis) and NOTHING HERE HAS "
         "MEASURED IT."),
        ("series-composition-witness",
         "That two distinguishing axes chain in SERIES as strains is one "
         "proposition about the DOMAIN, not an assumption about how margins add. "
         "It still needs a witness; it is now the kind of thing a witness could "
         "refute."),
        ("bias-as-conjunct",
         "The stride cap in _candidates and every _lum_nudge are biases that are "
         "not expressible as constraints, so none can be checked, removed or "
         "compared. The fix is to move them INTO the satisfactory set, not to add "
         "a bias mechanism."),
        ("geometry-is-the-same-netlist",
         "⚑ GEOMETRY IS NOT A SECOND NETWORK — it is unstated edges of THIS one, "
         "and carrying it as separate work was an error corrected by measurement. "
         "Every geometry quantity here is already a fraction of the cell unit "
         "(litHalf u*0.20, ghostHalf u*0.13, endGap u*0.10, dotFill 0.82) — never "
         "an absolute length — so each is dimensionless with 1.0 as its pass "
         "threshold, which is exactly the carrier the colour relations use. "
         "Nothing had to be made compatible; they already were. BUILT: the "
         "geometry family is now 5 edges over 8 nodes in the ONE authority, and "
         "the unified netlist (21 nodes, 40 edges) hands to the solver and "
         "eliminates to the same 3 terms at 62 Q."),
        ("geometry-and-colour-now-TOUCH",
         "⚑ CLOSED, AND THE EDGE FOUND A LIVE DEFECT. The halves were disjoint — "
         "5 components, none mixing colour and geometry — until fg_in~ghost_stroke "
         "was written. Now 4 components with the main one MIXED (14 nodes, b1=24), "
         "and the solve cost moved 62 Q -> 68 Q with `fg ~ view` growing from 7 "
         "parts to 9, so the edge composes into the surviving terms rather than "
         "sitting inert. THE DEFECT: SegmentChar.qml:73 draws the unlit core at "
         "opacity 0.45, so ghost subordination is carried by COLOUR and ALPHA and "
         "WIDTH (0.65x) multiplying into one perceived quantity — and the "
         "composited ghost is UNDER feasible_ghost_floor on all six variants "
         "(EL-Openglo gated at 4.16:1, renders at 1.79:1, floor 3.00). @GHOSTCOMP "
         "is RED and must be."),
        ("the-solve-optimises-the-bound-not-in-danger",
         "The ghost has a CEILING (must not read as text) and a FLOOR (must still "
         "read as shape), and alpha makes the ceiling SAFER while making the floor "
         "HARDER. Measured |Lc|: 29.8 declared, 7.7 composited, against a limit of "
         "30 — derive_ghost_ceiling pushes to within 0.2 of a bound carrying a "
         "22-point margin, while nothing models the one being missed. The fix is "
         "NOT to lower alpha or widen the stroke by hand: it is to give the ghost "
         "solve a floor term in the composited quantity, so the three knobs are "
         "solved together instead of traded blind. NOT YET BUILT."),
    )
