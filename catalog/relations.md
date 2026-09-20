# The palette, as declarative relations

*What must hold, not how to compute it.* Every entry below is a relation between named
quantities; none prescribes a search, an order, or an iteration. Where a relation is
currently implemented by a procedure, that is recorded as a **defect of the encoding**,
not as part of the relation.

The target consumer is `gcalc.solver`, whose input is exactly
`{(u, v): generator-name}` plus an `env` binding names to values — so a relation is
expressible here iff it is an **edge between two nodes with a value**.

---

## 0. The carrier

Every quantity below is a **positive rational**, dimensionless, with `1` as the pass
threshold. That is not a convention chosen for tidiness — it is what makes the relations
composable at all, because the two primitives are only defined on that carrier.

    NOT(x)   = 1/x            the involution: margin ↔ strain
    OR(a,b)  = a + b          parallel: alternative routes to one requirement
    AND(a,b) = ab/(a+b)       series: a chain where every link must hold

⚑ **A COLOUR IS NOT A QUANTITY HERE.** The carrier holds *relations between* colours. A
colour is a READ of a node, taken at the end, and three-channel — which is why §5 exists
as a separate concern rather than being folded in.

### ⚑ GEOMETRY IS THE SAME CARRIER, AND SPLITTING THEM WAS MY ERROR

I carried "the palette's discrete half" and "geometry fit as a network" as two items.
They are one. **Measured against the live constants:** every geometry quantity in this
tree is already a *fraction of the cell unit*, never an absolute length —

    litHalf   u*0.20      ghostHalf u*0.13      endGap    u*0.10
    dotFill   0.82        pitch     height*0.72 / rows

`litHalf = u*0.20` is "a fifth of the unit", not "4 pixels". So each is dimensionless
with 1.0 as its pass threshold, which is **the carrier above, exactly**. A geometry
requirement written as `measured / required` is the same kind of object as a contrast
margin, and the two compose under the same two primitives.

That the split existed at all is the error §1's own note warns about: *"had one
constraint been a ratio and another an absolute difference, they would not compose."*
They are both ratios. Nothing had to be made compatible; I had failed to notice they
already were.

The three magic numbers this is really about — `0.20`, `0.10`, `0.82` — are then not
tuning constants but *unsolved node values in the same netlist as the colours*.

⚑ **AND WRITING THEM AS MARGINS IMMEDIATELY CAUGHT A RELATION I HAD WRONG.** My first
pass had *"ends do not overlap"* as `endGap / litHalf`, which reads **0.500** — a margin
below 1.0, apparently contradicting `SegmentChar.qml:18`'s own comment that `endGap`
exists *"so segments don't overlap"*. Measured against `seg7_strokes()`: of the **10**
stroke pairs sharing a vertex, only **two** are collinear (`b~c`, `e~f` — the vertical
stacks). The other **8 are perpendicular corner joins**, where `endGap` cannot separate
anything at all — the pullback is *along* each stroke and the width is *across* it, so a
horizontal and a vertical overlap in a square of side `litHalf` whatever `endGap` is.

So the failing margin was **a relation that does not hold**, not a defect in the shape,
and encoding it would have gated a false constraint into the tree. What `endGap` governs
is the collinear case, and there it clears.

### What the unified graph measures — and what it does not

**Built.** The geometry family is 5 edges over 8 nodes in the one authority; the unified
netlist is **21 nodes, 40 edges**, hands to `frontier_solve`, and eliminates to the same
3 terms at 62 Q.

⚑ **AND IT CURRENTLY DOES NO WORK, WHICH IS THE HONEST RESULT.** Measured — 5 connected
components, and **zero** of them mix colour and geometry:

| component | nodes | edges | b₁ |
|---|---|---|---|
| colour (the constellation) | 10 | 33 | **24** |
| geometry (cell/stroke/aperture) | 4 | 3 | 0 |
| colour (selection) | 3 | 2 | 0 |
| geometry (endGap) | 2 | 1 | 0 |
| geometry (dots) | 2 | 1 | 0 |

The two share a **carrier** and no **constraint**. No colour value is determined by a
shape value or the reverse, every geometry component is a tree, and `b₁` is unchanged at
24. One graph, still two solves.

⚑ **THE COUPLING THAT WOULD DO WORK IS ALREADY NAMED IN THE SOURCE AND WRITTEN NOWHERE.**
`SegmentChar.qml:17` calls `ghostHalf` the **"stroke-weight channel"** — so a thinner
ghost stroke and a lower-contrast ghost colour *buy the same thing*, and the
`{lit, ghost, ground}` series chain of §3 has a geometry leg nobody has stated. Until
that edge exists, the unification is real and idle.

---

## 1. Nodes

    N  =  the palette roles

Measured (`palette_graph.NODES`, and `check_palette_graph` proves the three namespaces
total in both directions):

| node | pinned? | what pins it |
|---|---|---|
| `view` (ground) | **pinned** | `L(view) ≤ OLED_VOID_MAX_LUM`, hue seed |
| `fg` (lit) | **pinned** | argmax \|Lc\| from `view`, chroma ≥ floor |
| `fg_act` (accent) | **pinned** | hue at full usable chroma, contrast ≥ 4.6 |
| `fg_in` (ghost) | **free** | determined by §3 |
| `neg` `neu` `pos` `link` `visited` | **free, discrete** | §4 |
| `hover` `sel_bg` `sel_fg` `sel_act` | **free** | §6 |

⚑ **PINNED IS A ROLE, NOT A PROPERTY.** `view`, `fg`, `fg_act` are pinned because the
*identity* is chosen rather than solved (hue seed, polarity). Everything else is a
consequence. A relation that pins something else is a different palette, not a bug.

---

## 2. Edges

    E  ⊆  N × N,   each valued by a MARGIN

    y(u,v)  =  measured(u,v) / required(u,v)

⚑ **THE MARGIN IS THE CONDUCTANCE, AND THIS IS THE LOAD-BEARING CHOICE.** A larger `y`
is a better-satisfied constraint: plentiful margin conducts, a tight constraint resists.
`NOT(y) = 1/y` is then the *strain* — the shortfall factor — and the involution is exactly
the change of view between "how much room" and "how much stress".

Two measured families, and they are **the same kind** (this is why the network reading is
available at all — had one been a ratio and the other an absolute difference, they would
not compose):

    LEGIBILITY:   y = wcag_ratio(u, v) / floor
    SEPARATION:   y = worst_view_dE(u, v) / (okabe_floor · 0.8)

**Clearing is a read, not an object:** `y ≥ 1`. There are no truth values in the carrier
(`operator/reachable/constant`: no constant operator is reachable), so a verdict cannot be
smuggled in as a value.

---

## 3. The ghost — an interior node, determined

    lit ──y₁── ghost ──y₂── ground

**Relation.** The ghost lies on the `lit→ground` segment and both links must hold, so the
composite is SERIES:

    y(lit, ground)  =  AND( y(lit, ghost), y(ghost, ground) )

**Determination.** Maximising the worse side balances the two, and the balance point is
the fixed point of the involution — where `★` exchanging the sides leaves them equal:

    a/y = y/b        ⟹     y = √(ab)          a = L(lit)+0.05, b = L(ground)+0.05

each side then exactly `√span`.

⚑ **VERIFIED THROUGH THE SOLVER, NOT BY HAND.** `laplacian` on `A─y₁─M─y₂─B` gives
`V_M = y₁/(y₁+y₂)` exactly over `Fraction` (measured: `y₁=2,y₂=5 → 2/7`; `y₁=⅓,y₂=⅐ → 7/10`).
Eliminating `M` leaves ONE edge carrying the term `y₁·y₂/(y₁+y₂)` — which is `AND` — at a
cost of **1 Q**. No search.

⚑ **DEFECT OF THE CURRENT ENCODING.** `ghost_solve.py` derives `√(ab)` by hand. That is a
reimplementation of what `frontier_solve` returns as a term, and it is recorded as such:
the relation is the netlist, the closed form is a read of it.

### 3a. The ceiling ghost — a different relation, not a variant

    maximise |Lc|(ghost, ground)   subject to   |Lc| < GHOST_READABLE_LC

⚑ **THIS IS NOT A BALANCE AND MUST NOT BE CONFLATED WITH ONE.** It is a constrained
maximum whose optimum is a **supremum that is never attained** — the constraint is strict,
because a ghost that reaches the threshold *reads as text* and stops being ghost. There is
no geometric mean to reach for; the relation is an open boundary.

### 3b. The ghost is judged where it is SEEN, and both of its bounds share one metric

    seen(ghost)  =  composite(ghost, ground, α)  =  lerp(lit, ground, 1 − α(1 − t))

    GHOST_VISIBLE_LC  ≤  |Lc|(seen(ghost), ground)  <  GHOST_READABLE_LC
              25.0                                          30.0

**Relation.** The renderer draws the unlit core at alpha `α` over the ground. Source-over
of a flat alpha toward `ground` is a lerp toward `ground`, so the seen ghost is a point on
the SAME `lit→ground` segment as the declared one — at `t′ = 1 − α(1 − t)`. Every bound on
the ghost is therefore a bound on `t′`, and the declaration is recovered by
`t = 1 − (1 − t′)/α`. The ceiling of §3a is solved on `t′` and inverted
(`ghost_solve.derive_ghost_through_alpha`); before 2026-09-20 it was solved on `t`, and the
gate certified a ghost 2.2–2.5 WCAG points brighter than anyone saw (@GHOSTCOMP, 6 of 6).

**α is solved, not authored, and it is ONE number.** `SegmentChar.qml` held `opacity: 0.45`
as a literal. Measured, at 0.45 three of six variants could not reach the floor by any
colour. `α = max over variants of a_min`, where `a_min = 1 − t_floor` is the smallest alpha
at which the lit colour itself, composited, clears the floor (`ghost_solve.solve_ghost_alpha`;
operator ruling 2026-09-20: one global value). The variant whose `a_min` sets `α` renders
exactly on its floor by construction, so `α` is rounded UP. It is emitted with the schemes
(`make_palette` stamps `ghost_alpha` on every token; `make_schemes.GHOST_ALPHA` reads it) and
filled into the template hole `$ghostAlpha`; `check_ghost_composite` parses the emitted QML
back and refuses if it carries any other number.

**One metric, because APCA is polarity-asymmetric.** The floor was WCAG 3.0 and the ceiling
APCA 30. On the three light-ground (Lit) variants, |Lc| = 30 is only ~1.9:1 WCAG — the two
bounds were *jointly infeasible* there in any colour at any alpha, and nothing in either
bound said so. Both are now APCA. `GHOST_VISIBLE_LC = 25` is **derived**: the three Off
variants, solved through alpha at the ceiling, render at composited |Lc| 29.8 / 25.4 / 29.9
(2026-09-20); the floor is their minimum rounded down, so what exists passes and a
regression below what was achieved does not. Re-derive by the same read if the ceiling or
the alpha solve moves. The WCAG floor is kept as residue in
`cvd_gate.feasible_ghost_floor`.

**Recorded, not gated:** the lit bloom underlay and the matrix surface's own
`ghostOpacity: 0.28` are further instances of the same relation and are not yet solved
through it.

---

## 4. The constellation — the discrete relation

    S  =  { neg, neu, pos, link, visited },   plus the anchor  fg

**Relation.** Every pair must separate:

    ∀ u,v ∈ S ∪ {fg},  u ≠ v :   y(u,v) ≥ 1

**Objective.** Maximise the worst margin — equivalently, under `★`, minimise the worst
strain:

    maximise  min  y(e)        ≡        minimise  max  NOT(y(e))
               e∈E                                 e∈E

**Domain.** Each slot draws from its satisfactory set:

    S_k  =  { c : hue(c) ∈ sector_k
                ∧ wcag_ratio(c, view) ≥ 4.6
                ∧ separated(c, fg_act) }

⚑ **THE CONSTELLATION IS COMPLETE (K₆), AND THAT IS MEASURED.** 15 pairs over 6 values.
`b₁ = 24` over the whole constraint graph, 10 of which are the K₆ alone — so pairwise
satisfaction does **not** imply global consistency, and a per-edge check cannot see the
difference.

⚑ **WHY THE CURRENT ENCODING NEEDS RESTARTS, MEASURED.** The objective is max-min over
pairs while the search moves one slot at a time. At a sampled seed: **47% of single-slot
moves change `min_pair` not at all**, and of 117 moves on slots *outside* the binding pair,
only 26 change it. The objective is blind to most of the palette at any step, so the climb
has nothing to descend and restarts re-roll into a different flat region.

**That is a fact about the encoding, not about the problem.** Stated here so the relation
is not confused with the machinery currently failing to solve it.

### 4a. What is still open

A nodal solve determines *continuous* potentials; slot occupancy is **discrete**. The
formalization's answer:

- the **Voronoi cells** over candidate sites under the gate's own metric are the regions
  where the answer's *shape* is constant — one symbolic form per cell;
- the **boundaries** are tie surfaces, where the winning candidate switches;
- the **Delaunay dual** is which candidate can displace which.

⚑ **NOT YET VALIDATED.** This is the piece that would make restarts unnecessary rather
than merely retired, and it is honestly open. The machinery to try it exists
(`spanning_tree`/`cycle_basis`, cut and cycle sides of the same duality) but nothing here
has measured it.

---

## 5. Reads — where a relation becomes a colour

    determine   →   a scalar per node (a luminance, a margin)
    read        →   a three-channel sRGB triple

⚑ **THE SOLVE DETERMINES ONE SCALAR; A COLOUR HAS THREE CHANNELS.** So the last step is a
PROJECTION onto the admissible locus (for the ghost, the `lit→ground` segment), and it is
where exactness stops. Residual skew after an exact luminance solve is **8-bit
quantisation**, not solver error — measured worst 1.0200 on the shipped palettes.

Stating this separately is what keeps "solved exactly" from over-claiming.

---

## 6. Derivations are NOT constraints

    hover    ← lum_nudge(fg_act, ∓0.12)
    sel_bg   ← lum_nudge(fg_act, ∓0.08)
    sel_act  ← lum_nudge(view, −0.15)
    sel_in   ← mix(fg_act, view, 0.5)

These are **forward arrows** — `b` computed from `a`, carrying no floor. They belong in the
same graph so a check can ask *"is this token derived from something it must also contrast
with?"* — the question that would have caught `sel_act` at 1.00:1, derived from the
background it is drawn on.

⚑ **A DERIVATION THAT SHOULD BE A CONSTRAINT IS THE `@SELECTION` BUG.** The distinction is
in the graph, not in a naming convention.

---

## 7. Bias — a conjunctive constraint, never a post-hoc nudge

    S    =  { x : ∀e,  y_e(x) ≥ 1 }      the satisfactory set
    S∩B  =  { x ∈ S :  B(x) }            the biased solve

⚑ **SATISFACTION IS PRESERVED BY CONSTRUCTION.** Intersection can only shrink the set,
never admit a point outside it — so every member of `S∩B` satisfies every original
constraint. The failure mode is an **empty intersection**, which is a refusal ("no
candidate meets both the floor and the preference"), not a violation.

Two biases exist today and neither is expressible as a constraint:

- **the stride cap** — `_candidates` discards satisfactory points to bound search cost;
- **every `_lum_nudge`** — preference applied *after* the solve, outside the set.

⚑ **THE FIX IS TO MOVE THEM INTO THE SET, NOT TO ADD A BIAS MECHANISM.** Named as
conjuncts they become checkable, removable and comparable; left as procedure they are none
of the three.

---

## 8. What this collection does NOT claim

- **Not that ΔE composes as a conductance.** The *margins* are ratios with a common
  threshold, which makes them the right kind of object. What needs a witness is narrower:
  **that two distinguishing axes chain in SERIES as strains.** One proposition about the
  domain, and the kind of thing a witness could refute.
- **Not that the whole solve reduces to `r_eff`.** The series chain has a closed form; the
  candidate selection is discrete and §4a is open.
- **Not that `b₁ > 0` implies a bug.** It bounds how many independent gluing failures are
  *possible*. Whether the current palette realises any is a measurement nobody has taken.
- **Not that "conductance" is more than a shared shape here.** In gcalculus the carrier IS
  conductance and `network/kirchhoff` witnesses the calculus as nodal analysis' reducible
  shadow. For the palette this asserts a *shared shape*, and
  `shadow/010/a-shared-shape-is-not-a-shared-claim` warns exactly against reading the
  second as the first.
