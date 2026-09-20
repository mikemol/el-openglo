"""palette_graph — THE CONSTRAINT GRAPH, AS DATA.  One authority; everything else READS.

⚑ THIS MODULE INVENTS NOTHING.  Every edge below already existed, scattered across four
sites that had no way to notice when they disagreed:

    cvd_gate.ENFORCED           4 separation pairs   — declared, and NEVER GATED (no caller)
    cvd_gate.SURFACED           4 separation pairs   — printed, never enforced
    make_palette.solve_semantic_set   the K6 implied by `min_pair` over 5 slots + 1 anchor
    make_palette._candidates    the contrast floor and the raw-dE hot prune

Naming the union is the whole content.  The four sites become readers, and three defects
close as a CONSEQUENCE of there being one authority rather than as three separate repairs:

  * `audit_variant` had no caller.  An authority has a consumer list, so the gate acquires one.
  * `reference_floors()` returns two IDENTICAL scalars and `_worst_normalized` reads only
    `enforced`, so the enforced/surfaced distinction its docstring defends does not exist in
    the arithmetic.  Here the class is a FIELD ON THE EDGE, so two equal floats can no longer
    masquerade as a distinction — the class travels with the edge that is judged by it.
  * `_candidates` prunes against `hot` with a raw `_cached_dE < 5.0`, contradicting the
    module's own doctrine that the solver must optimise THE GATE'S metric, not raw dE.

⚑ THE THREE NAMESPACES COLLAPSE HERE OR NOWHERE.  There are three vocabularies for one set
of roles, and until this module they were related only by a reader's memory:

    SOLVER LOCAL   ground, lit, ghost, accent      locals in solve_scheme; never emitted
    EMITTED KEY    view, fg, fg_in, fg_act, ...    the 44 keys a variant actually carries
    GATE NAME      fg, focus, neg, neu, pos, link  what ENFORCED/SURFACED are written against

`NODES` states the mapping once and `check_palette_graph.py` proves it total in both
directions.  Without that proof this file is a FOURTH namespace and strictly worse than the
scatter it replaces — which is why the check is not optional decoration.

⚑ WHAT THIS FILE DOES NOT DO.  It holds no colours, computes no distances, and imports
nothing from the solver.  It is the SHAPE of the problem, available before any colour is
chosen — which is exactly what makes `b1` computable in advance of a solve.
"""
from __future__ import annotations


# ── the roles, one namespace, stated once ────────────────────────────────────
#
# A Node is (key, solver_local, gate_name).  `None` means "this role has no name in that
# vocabulary", and that is DATA rather than an omission: `visited` appears in the solver's
# sector table and in the emitted keys but in NO gate pair, and the honest record of that is
# a hole, not a silently-dropped row.

class Node:
    """One palette role, under every name it answers to.

    ⚑ TWO ROLES SHARING A VALUE ARE STILL TWO NODES.  `fg_act` and `focus` are both the
    solved `accent`, and `fx_dis`/`fx_in`/`fg_in` are all the solved `ghost`.  Collapsing
    them here would erase exactly the distinction whose absence WAS the @ROLES bug — a
    focus ring the colour of the text it surrounds passed every check because no check
    asked whether two ROLES differ.  Aliasing is recorded (`same_as`) and never merged."""
    __slots__ = ("key", "local", "gate", "same_as")

    def __init__(self, key, local=None, gate=None, same_as=None):
        self.key, self.local, self.gate, self.same_as = key, local, gate, same_as

    def __repr__(self):
        return f"<node {self.key}>"


NODES = (
    # emitted key   solver local   gate name    alias-of
    Node("view",    "ground",      None),
    Node("fg",      "lit",         "fg"),
    Node("fg_in",   "ghost",       None),
    Node("fg_act",  "accent",      None),
    Node("focus",   "accent",      "focus",     same_as="fg_act"),
    Node("hover",   None,          None),
    Node("neg",     None,          "neg"),
    Node("neu",     None,          "neu"),
    Node("pos",     None,          "pos"),
    Node("link",    None,          "link"),
    Node("visited", None,          None),
    Node("sel_bg",  None,          None),
    Node("sel_fg",  None,          None),
    Node("sel_act", None,          None),
)

# ⚑ THE GEOMETRY NODES ARE THE SAME GRAPH, NOT A SECOND ONE.  They are kept in
# their own tuple only because they answer to no EMITTED KEY and no GATE NAME —
# a stroke half-width is not a token in a `.colors` file — so folding them into
# NODES would make the namespace-totality check refuse them for lacking names they
# cannot have.  `nodes()` unions both, and `check_palette_graph` skips the
# emitted-key arm for these while still requiring every edge to name a real node.
GEOMETRY_NODES = (
    Node("cell"),           # the 2u x 4u digit box every fraction is taken of
    Node("lit_stroke"),     # litHalf
    Node("ghost_stroke"),   # ghostHalf
    Node("end_gap"),        # endGap
    Node("aperture"),       # the open counter a glyph needs to stay legible
    Node("collinear_join"), # the b~c / e~f vertical stacks endGap governs
    Node("dot_fill"),       # dotFill
    Node("dot_gap"),        # the space between adjacent matrix dots
)

BY_KEY = {n.key: n for n in NODES}


def declared_nodes():
    """Every node the authority declares — colour AND geometry, in one read.

    ⚑ A SECOND LIST IS A SECOND AUTHORITY UNLESS SOMETHING UNIONS IT.  Adding
    GEOMETRY_NODES beside NODES immediately broke `check_relations`, which asked
    `PG.NODES` and correctly refused five geometry edges for naming roles "the edge
    authority does not" — the check was right and the split was mine. Consumers ask
    THIS rather than either tuple, so a third family cannot repeat it."""
    return NODES + GEOMETRY_NODES


# ── the edge families ────────────────────────────────────────────────────────

LEGIBILITY = "legibility"        # wcag_ratio(fg, bg) >= floor
SEPARATION = "separation"        # worst_view_dE(a, b) / need >= 1
DERIVATION = "derivation"        # b is computed FROM a; no floor, a forward arrow
GEOMETRY = "geometry"            # a ratio of lengths in the cell >= floor

# ── the geometry quantities, as fractions of the cell unit ───────────────────
#
# ⚑ GEOMETRY IS NOT A SECOND NETWORK — IT IS UNSTATED EDGES OF THIS ONE, and
# carrying it as separate work was an error corrected by measurement.  Every value
# below is already a FRACTION OF THE CELL UNIT and never an absolute length, so
# each is dimensionless with 1.0 as its pass threshold — which is exactly the
# carrier the colour edges use.  Nothing had to be made compatible; they already
# were, and `catalog/relations.md` §1 states the test I failed to run: "had one
# constraint been a ratio and another an absolute difference, they would not
# compose."  Both are ratios.
#
# Read from templates/SegmentChar.qml and MatrixChar.qml rather than remembered.
LIT_HALF = 0.20        # SegmentChar: lit stroke half-width, u*0.20
GHOST_HALF = 0.13      # SegmentChar: ghost half-width, u*0.13
END_GAP = 0.10         # SegmentChar: ends pulled in, u*0.10
DOT_FILL = 0.82        # MatrixChar: dot diameter as a fraction of the pitch
CELL_W = 2.0           # GEOM16's digit box: 2u wide
CELL_H = 4.0           # ... 4u tall (5u with the descender band)

# ⚑ THE GHOST'S ALPHA IS THE EDGE THAT COUPLES SHAPE TO COLOUR — AND IT NO LONGER
# LIVES HERE.  SegmentChar.qml drew the unlit core at a literal `opacity: 0.45`,
# so what the eye received was a BLEND of ghostColor over the ground that no colour
# check knew existed; this file carried the 0.45 as a read-from-the-QML record.
# Measured (check_ghost_composite --solve), at 0.45 three of six variants cannot
# clear the ghost floor by ANY choice of colour — alpha was the binding knob and
# the one of the three subordination channels that was authored.  It is now SOLVED
# (`ghost_solve.solve_ghost_alpha`) and EMITTED (`make_schemes.GHOST_ALPHA`) into
# the template hole `$ghostAlpha`.  A solved quantity is a colour-chain OUTPUT,
# and this module holds the shape of the problem before any colour is chosen, so
# `composite` takes alpha as an argument rather than defaulting to a number that
# would drift from the emitted one.


def composite(fg, bg, alpha):
    """Source-over: what the eye receives when `fg` is drawn at `alpha` on `bg`.

    ⚑ THE RENDER APPLIES THIS, AND THE CHECK NOW APPLIES THE SAME NUMBER — pass
    `make_schemes.GHOST_ALPHA`, the value the template is filled with.  Measured
    on the shipped palette at the old 0.45: declared ghost contrast 4.16:1 on
    EL-Openglo, composited 1.79:1 — a 2.37 drop between the gate and the screen."""
    return tuple(int(round(f * alpha + b * (1 - alpha)))
                 for f, b in zip(fg, bg))

# ⚑ A CONSTRAINT IN THE WRONG METRIC, NAMED SO IT CAN BE ARGUED WITH.
# `_candidates` prunes each semantic candidate against `hot` (the accent) with a
# RAW worst-view dE below this number — while the very function that consumes the
# result documents the opposite doctrine: "THE OBJECTIVE IS THE GATE'S OWN METRIC,
# NOT RAW ΔE ... a solver maximising raw global min-ΔE optimises a PROXY and can
# hand back a palette the gate then rejects."  The filter and the objective it
# feeds disagree, inside one function.
#
# It is 5.0 here and not `reference_floors()["enforced"] * 0.8` (≈ the gate's
# number) because CHANGING IT CHANGES WHICH CANDIDATES SURVIVE, and therefore the
# emitted colours.  That is step 4/5 work, gated by re-captured baselines and by
# LOOKING at the samples.  Naming it is what makes the divergence visible and the
# swap a one-line decision instead of an archaeology of why 5.0.
HOT_PRUNE_DE = 5.0

# pair classes, per cvd_gate's comment: colour-as-sole-carrier -> enforced;
# accent-adjacent (geometry co-carries meaning) -> surfaced.
ENFORCED_CLS = "enforced"
SURFACED_CLS = "surfaced"


class Edge:
    """One constraint, with the floor it is judged against and the class of that floor.

    ⚑ THE CLASS IS A FIELD, NOT A LOOKUP.  `_worst_normalized(a, b, floors)` reads
    `floors["enforced"]` unconditionally, so a SURFACED pair is silently judged by the
    ENFORCED floor.  That is invisible today only because `reference_floors()` happens to
    return the same number twice; the day those diverge, four pairs change class without
    anything changing in the code.  Carrying the class on the edge makes the read take it."""
    __slots__ = ("u", "v", "family", "cls", "floor", "why")

    def __init__(self, u, v, family, cls=None, floor=None, why=""):
        self.u, self.v, self.family, self.cls = u, v, family, cls
        self.floor, self.why = floor, why

    @property
    def key(self):
        return (self.u, self.v) if self.u <= self.v else (self.v, self.u)

    def __repr__(self):
        return f"<{self.family} {self.u}~{self.v}>"


# The five semantic slots plus the body-text anchor: `solve_semantic_set.min_pair` walks
# every pair of these, so the distinctness family is the COMPLETE graph on them.  The
# complete-ness is not a modelling choice here — it is read off `min_pair`'s double loop.
SEMANTIC = ("neg", "neu", "pos", "link", "visited")
CONSTELLATION = SEMANTIC + ("fg",)

# Which of those pairs cvd_gate additionally declares, and at which class.  Everything in
# CONSTELLATION is already an edge; these rows say what CLASS each declared pair carries.
_DECLARED_CLASS = {
    ("neg", "pos"): ENFORCED_CLS, ("neg", "neu"): ENFORCED_CLS,
    ("neu", "pos"): ENFORCED_CLS, ("fg", "link"): ENFORCED_CLS,
    ("focus", "neu"): SURFACED_CLS, ("focus", "link"): SURFACED_CLS,
    ("focus", "neg"): SURFACED_CLS, ("focus", "pos"): SURFACED_CLS,
}


def _separation_edges():
    """The constellation K6, plus the accent fan — with each pair's declared class.

    ⚑ AN UNDECLARED PAIR IS STILL AN EDGE.  `min_pair` optimises all 15 constellation
    pairs while `ENFORCED` names only 4 of them, so 11 pairs are solved-for and never
    gated.  Defaulting them to `enforced` would invent a floor nobody wrote; they are
    carried with class `None`, which reads as "optimised, not gated" and is the truth."""
    out = []
    n = len(CONSTELLATION)
    for i in range(n):
        for j in range(i + 1, n):
            u, v = CONSTELLATION[i], CONSTELLATION[j]
            k = (u, v) if u <= v else (v, u)
            out.append(Edge(u, v, SEPARATION, cls=_DECLARED_CLASS.get(k),
                            floor="reference_floors", why="solve_semantic_set.min_pair"))
    for (u, v), cls in _DECLARED_CLASS.items():
        if "focus" in (u, v):
            out.append(Edge(u, v, SEPARATION, cls=cls, floor="reference_floors",
                            why="cvd_gate.SURFACED"))
    return tuple(out)


def _legibility_edges():
    """Every foreground against the ground it is drawn on.

    ⚑ `hot` IS THIS FAMILY WEARING THE OTHER FAMILY'S CLOTHES.  `_candidates` prunes each
    semantic candidate against `accent` with a raw `_cached_dE < 5.0` — a SEPARATION
    constraint with a hardcoded floor in the wrong metric, sitting inside the contrast
    filter.  It is recorded here as what it is, so the repair is a floor swap rather than
    an archaeology of why 5.0."""
    out = [
        Edge("fg", "view", LEGIBILITY, floor="solve_lit/apca-argmax",
             why="argmax |Lc|, no floor; chroma_floor=40 is the only gate"),
        Edge("fg_in", "view", LEGIBILITY, floor="GHOST_READABLE_LC",
             why="an UPPER ceiling, not a floor: derive_ghost_ceiling"),
        Edge("fg_in", "fg", LEGIBILITY, floor="feasible_ghost_floor",
             why="the {lit, ghost, ground} series chain"),
        Edge("fg_act", "view", LEGIBILITY, floor="4.6", why="solve_accent min_contrast"),
        Edge("sel_fg", "sel_bg", LEGIBILITY, floor="3.0",
             why="check_selection_contrast FLOOR"),
        Edge("sel_act", "sel_bg", LEGIBILITY, floor="3.0",
             why="check_selection_contrast FLOOR"),
    ]
    for s in SEMANTIC:
        out.append(Edge(s, "view", LEGIBILITY, floor="4.6",
                        why="_candidates min_contrast"))
        out.append(Edge(s, "fg_act", SEPARATION, cls=None, floor=HOT_PRUNE_DE,
                        why="_candidates hot-prune — RAW dE, not the gate's metric"))
    return tuple(out)


def _geometry_edges():
    """Shape requirements as MARGINS in the same carrier as the colour edges.

    ⚑ EVERY ONE IS `measured / required`, A RATIO OF LENGTHS IN ONE CELL, so it is
    dimensionless with 1.0 as the pass threshold — identical in kind to a contrast
    margin, and composable with it under the same two primitives.

    ⚑ AND ONE RELATION I FIRST WROTE HERE WAS WRONG, CAUGHT BY MEASURING THE REAL
    GEOMETRY.  I had `endGap / litHalf` as "ends do not overlap" and it read 0.500 —
    a margin below 1.0, apparently contradicting SegmentChar's own comment that
    endGap exists so segments do not overlap.  Measured against `seg7_strokes()`:
    of the 10 stroke pairs sharing a vertex, only TWO are collinear (b~c and e~f,
    the vertical stacks).  The other 8 are PERPENDICULAR corner joins, where endGap
    cannot separate anything — the pullback is ALONG each stroke and the width is
    ACROSS it, so a horizontal and a vertical overlap in a square of side litHalf
    whatever endGap is.  So the failing margin was a relation that does not hold
    rather than a defect in the shape, and encoding it would have gated a false
    constraint into the tree.

    What endGap DOES govern is the collinear case, and there it clears."""
    out = [
        # ⚑ THE GHOST MUST BE SUBORDINATE, which is the stroke-weight channel the
        # design log names: the unlit field recedes to texture rather than
        # competing with the lit glyph.  Same relation as the colour ghost's
        # readability CEILING, one axis over.
        Edge("lit_stroke", "ghost_stroke", GEOMETRY, floor="ghost_subordinate",
             why=f"litHalf/ghostHalf = {LIT_HALF / GHOST_HALF:.3f}; the unlit field "
                 f"must read as texture, not as a second glyph"),

        # The aperture: two parallel strokes bounding a counter must leave a gap.
        # At litHalf=0.20 a 1u span between stroke CENTRES leaves 1 - 2*0.20 = 0.60u
        # of open counter. Below zero the glyph closes into a blob.
        Edge("lit_stroke", "aperture", GEOMETRY, floor="aperture_open",
             why=f"(1 - 2*litHalf) = {1 - 2 * LIT_HALF:.2f}u of counter across a 1u "
                 f"span; at 0 the glyph closes up"),

        # ⚑ COLLINEAR ONLY — the case endGap actually governs, measured.
        Edge("end_gap", "collinear_join", GEOMETRY, floor="ends_separate",
             why=f"2*endGap = {2 * END_GAP:.2f}u between the drawn ends of b~c and "
                 f"e~f, the only two collinear shared-vertex pairs of the 10"),

        # The matrix dot must not touch its neighbour, or the field becomes a blob.
        Edge("dot_fill", "dot_gap", GEOMETRY, floor="dots_separate",
             why=f"(1 - dotFill) = {1 - DOT_FILL:.2f} of the pitch between adjacent "
                 f"dots; at 0 the matrix reads as filled area"),

        # ⚑ THE CELL IS THE GROUND EVERY SHAPE QUANTITY IS A FRACTION OF, which is
        # what makes them commensurable at all — the same role `view` plays for the
        # colour edges.
        Edge("cell", "lit_stroke", GEOMETRY, floor="stroke_fits",
             why=f"litHalf = {LIT_HALF}u against a {CELL_W}x{CELL_H}u cell; a stroke "
                 f"wider than the cell's own features cannot render"),

        # ⚑⚑ THE EDGE THAT CROSSES. Everything above is shape-to-shape and
        # everything in the colour families is colour-to-colour; this one joins
        # them, and until it existed the graph was one graph with two disjoint
        # halves.
        #
        # THE GHOST IS SUBORDINATED BY THREE KNOBS MULTIPLYING INTO ONE PERCEIVED
        # QUANTITY: its colour (`fg_in` vs `view`), its ALPHA, and its WIDTH
        # (ghostHalf/litHalf = 0.65). Trading any one against the others is
        # invisible to every check, because the colour checks do not know about
        # alpha or width and the shape constants are not colours.
        #
        # ⚑ IT WAS BROKEN ON ALL SIX VARIANTS, AND ALPHA WAS THE KNOB. Measured at
        # the authored 0.45: the composited ghost was UNDER `feasible_ghost_floor`
        # everywhere — EL-Openglo declared 4.16:1 and rendered 1.79:1 against a
        # floor of 3.00 — and on the three Lit variants NO colour could fix it
        # (`check_ghost_composite --solve`: a_min 0.49-0.51 with fg_in = lit). The
        # CEILING was satisfied with huge margin (|Lc| 29.8 declared, 7.7
        # composited against 30), so the solve optimised the bound not in danger.
        # Alpha is now SOLVED (`ghost_solve.solve_ghost_alpha`) and EMITTED
        # (`make_schemes.GHOST_ALPHA` -> SegmentChar.qml's `$ghostAlpha`); the
        # value is not quoted here because this graph holds relations, not
        # solver output — `check_ghost_composite` reads the emitted number.
        Edge("fg_in", "ghost_stroke", GEOMETRY, floor="ghost_visible_as_shape",
             why=f"the ghost's SUBORDINATION is carried by colour AND alpha "
                 f"(solved: make_schemes.GHOST_ALPHA) AND width "
                 f"({GHOST_HALF / LIT_HALF:.2f}x) multiplying into one perceived "
                 f"quantity; the composited ghost must clear feasible_ghost_floor"),
    ]
    return tuple(out)


def _derivation_edges():
    """Forward arrows: b is computed FROM a.  No floor — these are not constraints.

    ⚑ RECORDED PRECISELY BECAUSE THEY ARE NOT CONSTRAINTS.  `sel_act = _lum_nudge(ground,
    -0.15)` is a derivation whose RESULT is judged by a legibility edge against `sel_bg`,
    and it reached 1.00:1 because nothing related the two.  Holding derivations in the same
    graph is what lets a check ask "is this token derived from something it must also
    contrast with?" — the question that would have caught it."""
    return (
        Edge("fg_act", "hover", DERIVATION, why="_lum_nudge(accent, -+0.12)"),
        Edge("fg_act", "sel_bg", DERIVATION, why="_lum_nudge(accent, -+0.08)"),
        Edge("view", "sel_act", DERIVATION, why="_lum_nudge(ground, -0.15)"),
        Edge("view", "sel_fg", DERIVATION, why="sel_fg = ground inverted"),
        Edge("view", "fg_in", DERIVATION, why="ghost lerps along lit->ground"),
        Edge("fg", "fg_in", DERIVATION, why="ghost lerps along lit->ground"),
    )


EDGES = (_separation_edges() + _legibility_edges() + _geometry_edges()
         + _derivation_edges())

BY_KEY.update({n.key: n for n in GEOMETRY_NODES})


# ── reads ────────────────────────────────────────────────────────────────────

def edges(family=None, cls=None, constraining_only=False):
    """The edge set, filtered.  ⟡PARAMETRIC: a caller takes what it needs as an argument.

    `constraining_only` drops DERIVATION, which carries no floor — the netlist wants
    constraints, the derivation-cycle check wants everything."""
    out = EDGES
    if family is not None:
        out = tuple(e for e in out if e.family == family)
    if cls is not None:
        out = tuple(e for e in out if e.cls == cls)
    if constraining_only:
        out = tuple(e for e in out if e.family != DERIVATION)
    return out


def nodes(constraining_only=False):
    """The nodes actually touched by the selected edges — never a hardcoded list.

    Derived from the edges so the two cannot disagree; a node in NODES that no edge
    mentions is a finding, and `check_palette_graph.py` reports it rather than hiding it."""
    es = edges(constraining_only=constraining_only)
    seen = []
    for e in es:
        for v in (e.u, e.v):
            if v not in seen:
                seen.append(v)
    return tuple(sorted(seen))


def netlist_edges(constraining_only=True):
    """{(u, v): generator-name} — the shape `gcalc.solver.netlist` consumes.

    One generator per edge, named for the pair, so the symbolic term that comes back out
    of the elimination mentions the CONSTRAINT by name rather than a positional index."""
    out = {}
    for e in edges(constraining_only=constraining_only):
        u, v = e.key
        out[(u, v)] = f"y_{u}_{v}"
    return out


def gate_pairs(cls):
    """The (name, a, b) triples cvd_gate.audit_variant walks — in GATE vocabulary.

    ⚑ THIS IS WHERE ENFORCED/SURFACED NOW COME FROM.  The literal lists in cvd_gate become
    readers of this, so a pair cannot be declared in one place and judged in another."""
    out = []
    for e in edges(family=SEPARATION, cls=cls):
        a, b = BY_KEY[e.u], BY_KEY[e.v]
        if a.gate is None or b.gate is None:
            continue
        label = f"{a.gate}~{b.gate}"
        out.append((label, a.gate, b.gate))
    return tuple(sorted(set(out)))
