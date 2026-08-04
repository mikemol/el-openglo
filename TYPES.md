<!-- [RECONSTRUCTED from this session's own tool call — later compacted session, not on-disk
     transcript. Faithful to the create_file content.] -->
# TYPES.md — the projection pipeline as typed input→output

Grounded in the reified code (glyph_match.py, project_font.py, segment_topology.py).
Purpose: see the data flow, guide its shape. ⊕-symbols cross-ref COTYPE.

## Core types (the vocabulary everything is built from)

    Point      = (ℝ, ℝ)                        -- a location in the 2×4 glyph cell
    Sign       = ABSENT | PRESENT              -- the fundamental two-valued datum (∓1)
    Grade      = ABSENT | RIM | MANTLE | CORE  -- Sign REFINED by distance-to-boundary
    Field[T]   = Point → T                     -- a spatial field valued in T
    Grid[T]    = T[(N+1)×(N+1)]                -- Field discretized on a sampling lattice
    SegKey     = "a1"|"a2"|…|"m"               -- one of the 22 segment names
    Format     = 7 | 9 | 14 | 16 | 22          -- display resolution (a lattice: 7⊂…⊂22)
    SegSet@F   = Set[SegKey]                    -- which segments are lit, at format F
    Phi        = [-1, +1]                       -- Matthews correlation = congruence
    Endpoints  = (ℝ,ℝ,ℝ,ℝ)
    RegionGraph= { presence:ℕ, holes:ℕ, background:ℕ }   -- holes = Betti-1

## The pieces, as typed input → output

### 1. INGEST — construct the presence/absence field (dispatched by font KIND)
    winding_ink : FontPath × Char → Field[Sign]   -- OUTLINE: CSG membership; curve intent kept
    raster_ink  : FontPath × Char → Field[Sign]   -- BITMAP: native pixel grid; no fill rule
    -- invariant: OUTSIDE the cell = ABSENT ("pure not-here"). kind changes the CONSTRUCTOR,
    -- not the type. ⊕FONT-INK-INGEST

### 2. SAMPLE — discretize
    ink_grid : Field[Sign] → Grid[Sign]

### 3. TOPOLOGY — quotient the field by connectivity  (⊕REGION-GRAPH-MATCH)
    region_graph : Grid[Sign] → RegionGraph
    -- holes = shift/scale/rotation-invariant glyph identity (Betti-1).

### 4. MORPHOLOGY — refine the codomain Sign→Grade  (⊕STRATA-MANTLE)
    strata : Grid[Sign] → Grid[Grade]   (+ rim_frac : [0,1])
    -- core=landlocked, mantle=isthmus (borders core↔coast), rim=outer coast.
    -- discriminates same-topology glyphs (E/F/C/L) that region_graph cannot.

### 5. SEGMENT AS A FIELD — the segment inhabits the SAME type as the glyph
    seg_field : SegKey × BBox × StrokeWidth → Grid[Sign]

### 6. MATCH — pair two Grid[Sign] into a scalar  (⊕CONGRUENCE-MATCH)
    phi   : Grid[Sign] × Grid[Sign] → Phi
    match : Grid[Sign] → (SegKey ⇀ Phi) × SegSet@22
    -- phi is the full-2×2 symmetric correlation; match ranks strongest. At the 22-JOIN.

### 7. DEREZ — lattice morphism, coverage-monotone  (⊕MATCH-AT-JOIN / ⊕DEREZ-COVERAGE-GATE)
    project : SegSet@22 × Format → SegSet@F      -- drops/merges; never extinguishes coverage

### 8. RENDER
    display_geom : Format → (SegKey ⇀ Endpoints) -- POST-merge geometry (⊕SUBSTRATE-PRIMITIVES)
    render       : SegSet@F × Format → Image

## The bottoming-out (the invariant under all the pieces)

Both glyph and segment inhabit **Field[Sign]** (discretized Grid[Sign]). MATCH is a
**self-pairing of that type**:  Field[Sign] × Field[Sign] → Phi. That single fact is why
the pipeline composes — the two "sides" of the match are the same object.

Two orthogonal enrichments of that base type:
- REFINE the codomain:  Sign → Grade  (strata). More values per point = richer channels.
- QUOTIENT the domain:  Field → Graph (region_graph). Connectivity collapses coordinates away.

⊕RICH-PROJECTION, in types: match generalizes to  Field[Grade] × Field[Grade] → Phi^k  (one
component per grade/channel) then reduce; RELIABILITY = k = the dimension.

## Where the OPEN lever sits in the type structure  (⊕SEG-DOTPRODUCT-TEMPLATES)

Today  seg_field : SegKey × BBox × StrokeWidth → Grid[Sign]  builds a STRAIGHT stroke field.
The curvature-aware version only enriches the CONSTRUCTOR:
    seg_template : JetOrder × SegKey → Field[Sign]   where JetOrder = SINGLE | PAIR | TRIPLE
The OUTPUT type is unchanged (Field[Sign]) — so it drops straight into `match` without
touching the pairing. In substrate terms: raise the bilinear form's rank.

## Shape observations (for guiding)
- One linear chain Field[Sign] → … → SegSet, with two side-refinements (strata, region_graph).
- The only place two objects meet is `match` (the pairing).
- Font KIND is dispatched once, at ingest, then erased.
- Format enters only at derez/render — the match is format-agnostic (always @22).
