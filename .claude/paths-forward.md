<!-- DERIVED. Regenerated every tick by scripts/paths_forward.py --render.
     Edits here vanish; edit .claude/paths-forward.json (or tell the loop). -->
# paths-forward — el-openglo

heartbeat 2026-09-20T22:35:10+00:00 · job `5c4707e2` · counter 11 · hash `52100ab909573431`

| # | status | title | blocked on | next bounded step |
|---|---|---|---|---|
| W1 | done | Restore the borrowed hooks' selftests: scripts/ needs __init__.py and hook_cmdparse (symlink into substrate) — @HOOKS | — | — |
| W11 | done | Answer summit's three letters in inbox/ (axis 4 Δ-sandbox root, axis 5 wrapper shape, axis 10 vendoring posture) — answers go in the axis files under the operator's name | — | — |
| W2 | done | Structural-query hook reports an EMPTY routing table — @ROUTES | — | — |
| W3 | done | The ghost that renders is not the ghost that is gated: alpha 0.45 lives between check and screen, 6 of 6 variants — @GHOSTCOMP | — | — |
| W4 | done | cotype warrants.bib's `enables` field is DROPPED by paperkit until catalog/cotype/paper.toml declares consumer_fields | — | — |
| W5 | done | SegmentChar as the one geometry substrate under wallpaper/clock/marquee/plymouth — cotype ⊕SEGMENT-SUBSTRATE | — | — |
| W6 | ready | Arbitrary text reaches the matrix by rasterising a font into it — cotype ⊕MATRIX-FONT-INPUT | — | Read the cotype entry (:4534) and the matrix font emitter; state the input contract in evidence. |
| W7 | ready | Segment projection chain: real fontTools ingest → calibrate bandwidth/tau → validate against the authored 44 → descenders in 22-seg — cotype ⊕SEG-FONT-PROJECT, ⊕SEG-PROJECT-CALIBRATE, ⊕SEG-TABLE-VALIDATE, ⊕SEG22-DESCENDERS | — | Confirm the chain order in the cotype (:4644,:4631,:4632,:4455); the first bounded step is ⊕SEG-TABLE-VALIDATE — a routine that cross-checks projection vs authored table — since calibration needs it as its measure. |
| W8 | ready | ⊕SEGMENT-ROLLOUT: every surface draws the palette fg/fg_in at ghost_alpha — 24 of 24 emissions differ; SegmentChar.qml has zero consumers (+ ⊕GHOST-DENSITY) | — | Step 2: make_clock.main_qml — read lit=t["fg"], ghost=t["fg_in"], alpha=t["ghost_alpha"]; drop stretch_lit/derive_ghost there (record as residue in the docstring: session-39 pipeline retired); clock-main.qml gets `property real ghostAlpha: $ghostAlpha` and the Segment rectangle gets `opacity: parent.on ? 1.0 : root.ghostAlpha` (colon dots too). Baseline: clock has no main_qml parity pair (only CONFIG_*), so none to re-capture. Step 3: make_plymouth.render_assets reads fg_in + ghost_alpha via parse_scheme tokens (check parse_scheme exposes fg_in/ghost_alpha; else read GRID); alpha byte = round(255*ghost_alpha). Re-run check_ghost_surfaces → 24 of 24; then ⊕SEGMENT-ROLLOUT closure in COTYPE (Four gates line) and ⊕GHOST-DENSITY next. |
| W9 | ready | ⊕PLYMOUTH-VECTOR: the boot splash pre-rendered at the target resolution (or SVG) — ⊕CLOCK-VECTOR done | — | Find where the splash size/target is known (make_deb? the plymouth script plugin reads Window.GetWidth()/GetHeight() at boot — assets cannot know the screen at build time). So the honest form is likely: emit digits at a set of standard resolutions (or a U derived from a declared target), and have the plymouth .script pick by Window.GetHeight(). Read make_plymouth render_assets callers and the .script template; state the mechanism in evidence before building. |
| W10 | ready | TUNE bucket: cursor inherit, icons inherit, solver-owned UI tokens, Alt+Tab switcher — cotype ⊕CURSOR-INHERIT, ⊕ICONS-INHERIT, ⊕SOLVER-UI-TOKENS, ⊕TASKSWITCH | — | ⊕SOLVER-UI-TOKENS: list the ~5 authored UI tokens (:3928) and state which relation in catalog/relations.md each would be solved by. |

## evidence

- **W1** — scripts/__init__.py + scripts/hook_cmdparse.py -> ../../substrate/scripts/hook_cmdparse.py; struct-tools SKILL.md gained two filename-claim rows (54/55 → 55/55). `python3 scripts/check_hooks.py` → "2 of 2 hook selftests pass from this repo".
- **W11** — Operator declined all three (AskUserQuestion, 2026-09-20). Decline sent to summit-b0 via SendMessage msg_id=e43c0981 (queued; delivery notice pending). Recording in the axis files is summit's convention, left to summit.
- **W2** — Same cause as W1, as predicted: `python3 scripts/check_routes.py` → "the local routing table has 20 row(s)" (now 22), exit 0.
- **W3** — DONE (tick 8): floor in APCA — cvd_gate.GHOST_VISIBLE_LC=25 (derived from Off variants composited 29.8/25.4/29.9, rounded down) + feasible_ghost_floor_lc; WCAG floor kept as residue; ghost_solve.solve_floor_t/alpha_min in Lc; alpha rounded UP (0.503); check_ghost_composite floor/refusal/--compare in Lc, selftest 16/16 incl. the Lit case; relations.md §3b records the relation, the alpha derivation and the one-metric argument; baseline re-captured. `python3 scripts/check_ghost_composite.py` → 6 of 6 clear, worst Lc 25.0. `python3 scripts/worklist_gate.py` → paperkit-gate: PASS, 44 claims resolve. Note: a COLD .palette-cache.json makes ~13 checks time out under paperkit; warm it (any palette check) before reading the gate.
- **W4** — catalog/cotype/paper.toml: consumer_fields = ["enables"]. `python3 scripts/worklist_gate.py` no longer prints the DROPPED warning; COTYPE-WORKLIST.md ≡ projection (unchanged).
- **W5** — DONE (tick 12, commit e212032): glyph16(strict=)/has_glyph contract; digit paths strict; --coverable 3 of 3; @SUBSTRATE-COVERABLE green; COTYPE.md session 67 + closure section + ledger; `check_symbol.py SEGMENT-SUBSTRATE` → present; BUILD bucket 1 of 2 open (⊕MATRIX-FONT-INPUT only). Reading apparatus fixed twice: check_symbol witness now runs the tool (was a noun regex); cotype_index selftest rule 4 on a synthetic doc (was pinned to this symbol).
- **W6** — check_symbol.py --bucket BUILD: open.
- **W7** — check_symbol.py --bucket RESEARCH: 4 of the 5 open items.
- **W8** — STEP 1 (tick 15, commit 34d54bd): colors_for reads (ground, fg, fg_in, ghost_alpha) from the tokens; live-wallpaper-main.qml ghost pass uses $ghostAlpha (was literal 0.45); marquee passes ghostOpacity=$ghostAlpha to every MatrixChar (was 0.28, flagged for ⊕GHOST-DENSITY). check_ghost_surfaces: 12 of 24 match (was 0). Two baselines re-captured. Worklist 44/44.
- **W9** — MEASURED (tick 13, commit f94ff8c): ⊕CLOCK-VECTOR was DONE — emitted clock has no Canvas, segments are antialiased scene-graph Rectangles (the :4221-4225 criterion); witness was stale on file+idiom, now reads the emitted QML. ⊕PLYMOUTH-VECTOR genuinely open: PIL polygons from the substrate at FIXED U=48; log defines vector there as pre-render at target res or SVG; witness asks for either. TIER 3: 1 of 2. COTYPE session 68. Found: ghost colour silo on clock (:86 derive_ghost, opaque) AND plymouth (:107 ghost_from lerp .6, alpha .5) → W8.
- **W10** — check_symbol.py --bucket TUNE: 4 of 6 open.

## residue

- (none)
