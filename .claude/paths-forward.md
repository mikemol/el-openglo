<!-- DERIVED. Regenerated every tick by scripts/paths_forward.py --render.
     Edits here vanish; edit .claude/paths-forward.json (or tell the loop). -->
# paths-forward — el-openglo

heartbeat 2026-09-20T20:57:10+00:00 · job `cd86e5e3` · counter 11 · hash `daa785ccf90d18ef`

| # | status | title | blocked on | next bounded step |
|---|---|---|---|---|
| W1 | done | Restore the borrowed hooks' selftests: scripts/ needs __init__.py and hook_cmdparse (symlink into substrate) — @HOOKS | — | — |
| W11 | done | Answer summit's three letters in inbox/ (axis 4 Δ-sandbox root, axis 5 wrapper shape, axis 10 vendoring posture) — answers go in the axis files under the operator's name | — | — |
| W2 | done | Structural-query hook reports an EMPTY routing table — @ROUTES | — | — |
| W3 | done | The ghost that renders is not the ghost that is gated: alpha 0.45 lives between check and screen, 6 of 6 variants — @GHOSTCOMP | — | — |
| W4 | done | cotype warrants.bib's `enables` field is DROPPED by paperkit until catalog/cotype/paper.toml declares consumer_fields | — | — |
| W5 | ready | SegmentChar as the one geometry substrate under wallpaper/clock/marquee/plymouth — cotype ⊕SEGMENT-SUBSTRATE | — | Write the coverable witness: `check_geometry_source.py --coverable` — for each SURFACE, obtain its emitted geometry-bearing artifact through an accessor (make_segment_display.geometry_js/glyphs_js for the QML surfaces; make_plymouth's digit projection for PIL), monkeypatch ONE stroke in segment_topology.GEOM22, re-emit, and assert every surface's output changed; then request a glyph the table lacks and assert a refusal, not an empty set. Selftest: prove the witness sees a surface that IGNORES the substrate. Then append a `### ⊕SEGMENT-SUBSTRATE closure (four gates)` section + re-stated ledger to COTYPE.md so check_symbol closes it. |
| W6 | ready | Arbitrary text reaches the matrix by rasterising a font into it — cotype ⊕MATRIX-FONT-INPUT | — | Read the cotype entry (:4534) and the matrix font emitter; state the input contract in evidence. |
| W7 | ready | Segment projection chain: real fontTools ingest → calibrate bandwidth/tau → validate against the authored 44 → descenders in 22-seg — cotype ⊕SEG-FONT-PROJECT, ⊕SEG-PROJECT-CALIBRATE, ⊕SEG-TABLE-VALIDATE, ⊕SEG22-DESCENDERS | — | Confirm the chain order in the cotype (:4644,:4631,:4632,:4455); the first bounded step is ⊕SEG-TABLE-VALIDATE — a routine that cross-checks projection vs authored table — since calibration needs it as its measure. |
| W8 | ready | Ghost separation re-verified at 22-seg inter-stroke density — cotype ⊕GHOST-DENSITY | — | W3 landed. Read the cotype entry ⊕GHOST-DENSITY (:4459); state what "22-seg inter-stroke density" changes in the composite model (the bloom underlay and neighbouring-stroke overlap are the two recorded-not-gated instances in relations.md §3b) and which of them this item is; then extend check_ghost_composite or add a witness. |
| W9 | blocked | Clock and boot splash draw vector segments rather than raster — cotype ⊕CLOCK-VECTOR, ⊕PLYMOUTH-VECTOR | W5 | After W5: pick the clock first (it already has @CLOCKFIT as a witness). |
| W10 | ready | TUNE bucket: cursor inherit, icons inherit, solver-owned UI tokens, Alt+Tab switcher — cotype ⊕CURSOR-INHERIT, ⊕ICONS-INHERIT, ⊕SOLVER-UI-TOKENS, ⊕TASKSWITCH | — | ⊕SOLVER-UI-TOKENS: list the ~5 authored UI tokens (:3928) and state which relation in catalog/relations.md each would be solved by. |

## evidence

- **W1** — scripts/__init__.py + scripts/hook_cmdparse.py -> ../../substrate/scripts/hook_cmdparse.py; struct-tools SKILL.md gained two filename-claim rows (54/55 → 55/55). `python3 scripts/check_hooks.py` → "2 of 2 hook selftests pass from this repo".
- **W11** — Operator declined all three (AskUserQuestion, 2026-09-20). Decline sent to summit-b0 via SendMessage msg_id=e43c0981 (queued; delivery notice pending). Recording in the axis files is summit's convention, left to summit.
- **W2** — Same cause as W1, as predicted: `python3 scripts/check_routes.py` → "the local routing table has 20 row(s)" (now 22), exit 0.
- **W3** — DONE (tick 8): floor in APCA — cvd_gate.GHOST_VISIBLE_LC=25 (derived from Off variants composited 29.8/25.4/29.9, rounded down) + feasible_ghost_floor_lc; WCAG floor kept as residue; ghost_solve.solve_floor_t/alpha_min in Lc; alpha rounded UP (0.503); check_ghost_composite floor/refusal/--compare in Lc, selftest 16/16 incl. the Lit case; relations.md §3b records the relation, the alpha derivation and the one-metric argument; baseline re-captured. `python3 scripts/check_ghost_composite.py` → 6 of 6 clear, worst Lc 25.0. `python3 scripts/worklist_gate.py` → paperkit-gate: PASS, 44 claims resolve. Note: a COLD .palette-cache.json makes ~13 checks time out under paperkit; warm it (any palette check) before reading the gate.
- **W4** — catalog/cotype/paper.toml: consumer_fields = ["enables"]. `python3 scripts/worklist_gate.py` no longer prints the DROPPED warning; COTYPE-WORKLIST.md ≡ projection (unchanged).
- **W5** — MEASURED (tick 9) against the log's own four-gate plan (COTYPE.md:4427-4432): reachable — check_geometry_source --map: 5 of 5 surfaces import an authority (segment_topology ×4, display_types for the matrix marquee); observable — check_geometry_source: 5 of 5, no surface binds a literal stroke table (AST, not grep); constructible — @EMITTERS and @SAMPLES green. Coverable — NO WITNESS: nothing proves that moving one GEOM stroke moves every surface, or that an absent glyph is reported rather than rendered empty. The cotype ledger still lists ⊕SEGMENT-SUBSTRATE open because no closure section was ever written; three of four gates are already measured by tools.
- **W6** — check_symbol.py --bucket BUILD: open.
- **W7** — check_symbol.py --bucket RESEARCH: 4 of the 5 open items.
- **W8** — check_symbol.py --bucket RESEARCH: open (:4459).
- **W9** — check_symbol.py --bucket TIER_3: 2 of 2 open (:4228).
- **W10** — check_symbol.py --bucket TUNE: 4 of 6 open.

## residue

- (none)
