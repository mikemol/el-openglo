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
