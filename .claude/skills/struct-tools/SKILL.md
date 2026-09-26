---
name: struct-tools
description: The artifact → tool routing table for this repo. Read this before reaching for grep/sed/awk over a structured artifact; it names the tool that owns the question. Also the live table the PreToolUse structural-query hook parses.
---

# Structural tools — ask the tool, not the text

**If you have a question the tooling doesn't answer directly, fix the tooling so it
answers your question.** No hand-assembled command lines, no greps, no judgements that
live in a turn instead of a program. A textual query over a structured artifact gets you
a string; the tool gets you the answer.

⚑ **A missing mode is WORK, not a finding.** "No tool covers this, so grep is legitimate
here" is a fact about the METHOD reported as a fact about the SUBSTRATE — the same error
as reading *no match found* as *no such thing exists*. There are no exceptions, only
tools that do not exist yet.

⚑ **THIS TABLE IS READ AT RUN TIME BY THE HOOK.** `scripts/hook_structural_query.py`
parses the rows below to name the owning tool when a textual query hits a structured
artifact. Adding a row teaches the hook with no code change. The hook resolves this file
from the repo root, so it must live HERE — a symlink to another repo's skill routes this
repo's questions to tools that do not exist here, and an ABSENT file makes the hook fire
with no tool named at all (measured, before the hook was adopted).

## artifact → tool

⚑ **FOUR COLUMNS, AND THE LAST ONE IS LOAD-BEARING.** `claims` declares which file
suffixes a tool owns. The hook no longer carries a hardcoded suffix list — it reads
this column — so a suffix claimed by no row is a suffix the hook will not guard, and
adding a tool without filling this in leaves its artifacts unprotected.

⚑ **SUBSTRATE PROVIDES THE GENERAL READERS; USE THEM.** Python, markdown and BibTeX
already have structural readers in `../substrate/scratch/`, built precisely because
someone kept reaching for `grep` at them. Do not grep those artifacts here and do not
reimplement a reader for them — point outward, exactly as the two PreToolUse hooks do.
This repo's own `check_*.py` answer questions about THIS project (is the mark gone, do
the emitters agree on one palette); they are not general readers and do not replace these.

| artifact | tool | run bare to list its modes | claims |
|---|---|---|---|
| Python — structure of any module | `../substrate/scratch/pycodemod.py` | `python3 ../substrate/scratch/pycodemod.py` | `.py` `.pyi` |
| markdown — headers, tables, cells; `append-section`/`replace-section --apply` WRITE (the published `mikemol-mdstruct`, installed by `uv sync --extra tooling`; substrate's scratch copy is retired) | `mdstruct` | `uv run --no-sync mdstruct` | `.md` |
| BibTeX — the claim-DAG, not its text | `../substrate/scratch/bibstruct.py` | `python3 ../substrate/scratch/bibstruct.py` | `.bib` |
| this repo's Python: does it compile / import (compile: `--json` is what policy/compiles.rego decides) | `scripts/check_compiles.py` + `scripts/check_consumers.py` | `python3 scripts/check_compiles.py --list` | `opa_gate.py compiles` |
| the claim graph's STATUS (are claims discharged) | `scripts/worklist_gate.py` | `python3 scripts/worklist_gate.py --summary` | — |
| **what to work on next** | `scripts/worklist_gate.py --next` | `python3 scripts/worklist_gate.py --next` | — |
| **what KIND of content is this** | `scripts/identify.py` | `python3 scripts/identify.py --db` | — |
| markup embedded in source | `scripts/check_embedded_markup.py` | `python3 scripts/check_embedded_markup.py --report` | — |
| **what the theme LOOKS like** | `catalog/library/library.md` (samples) | `python3 catalog/library/render_samples.py --list` | `.svg` |
| a concept the library owns and grades | `catalog/library/concepts.py` | `python3 catalog/library/concepts.py --list` | — |
| the design log's symbols, closures and open set | `scripts/cotype_index.py` | `python3 scripts/cotype_index.py` | — |
| does a QML document PARSE (Qt's qmllint, gated on error ids; Plasma context properties are not errors) | `qml_sanity.py` | `python3 qml_sanity.py <file.qml>` | — |
| **what a Plasma surface DRAWS** (headless render of the emitted clock / live wallpaper / switcher / aperture probe under the REAL theme for `--variant`; lit/ghost/ground census) | `scripts/render_qml.py` | `python3 scripts/render_qml.py clock --variant EL-Amber --png out.png --pixels` | — |
| **which emitted QML documents INSTANTIATE a component** (bare or qualified `Name {`; the consumer census a retirement needs — MatrixChar: 0 of 12 since the s120 port) | `scripts/check_qml_lint.py` | `python3 scripts/check_qml_lint.py --uses MatrixChar` | — |
| **what the host's NOTIFICATION MODEL exposes** (roles / enums / methods from org.kde.notificationmanager's qmltypes, beside what W46 needs and what the harness stub models; the numbers are declaration ordinals) | `scripts/check_notify_roles.py` | `python3 scripts/check_notify_roles.py` | `opa_gate.py notify_roles` |
| **how HARD are a surface's stroke edges** (intermediate pixels that touch a lit one, per lit pixel; W33 — ⚑ scale-dependent, so compare surfaces only at one digit height) | `scripts/render_qml.py` | `python3 scripts/render_qml.py clock --variant EL-Azure --edges` | — |
| **is the display SYMMETRIC / is the pip grid REGULAR** (an 8 and a 0 against their own mirrors, 00:00 as a face, and the matrix grid against one pitch; the mirror regions are diagnostic, the grid is a verdict) | `scripts/check_symmetry.py` | `python3 scripts/check_symmetry.py` | — |
| **the BUILD GRAPH: what produces a file, what consumes it, what is an undeclared input** (`--nodes`, `--json`; it REFUSES while any edge is computed or any domain undeclared — the buckets are upper bounds, not findings) | `scripts/build_graph.py` | `python3 scripts/build_graph.py` | — |
| **is a committed artifact CURRENT** (the digest of each action's declared domain — import closure, data directories, HOST inputs — against the key recorded when its outputs were built; `--list`, `--write` after a build) | `scripts/check_action_key.py` | `python3 scripts/check_action_key.py` | `opa_gate.py action_key` |
| **does a check actually FLIP when its input is corrupted** (one declared input, one check, restored on every path; a mis-aimed probe is WITHHELD, never a quiet non-flip. ⚑ It found that corruption REMOVES POPULATION MEMBERS — `30 of 30` becomes `25 of 25`, still green — which is why 66 of 72 checks grade `indeterminate`) | `scripts/check_discriminates.py` | `python3 scripts/check_discriminates.py --list` | — |
| **does an emitted PACKAGE resolve every type it names** (qmllint inside the package's own ui dir — Plasma's resolution; the wallpaper has failed to load twice) | `scripts/check_package_imports.py` | `python3 scripts/check_package_imports.py` | — |
| **can a machine READ the board** (a string through the aperture field → low-pass → tesseract → similarity, per font / rows / language; `--sweep` = γ × blur as the alignment's objective; a language without tessdata is withheld) | `scripts/check_legibility.py` | `python3 scripts/check_legibility.py` | `opa_gate.py legibility` |
| **does the aperture field GRADE a pip** (the three pips of the probe — clear / half / covered — as seen under each variant vs the scheme's floor / halfway / lit; W54) | `scripts/check_aperture.py` | `python3 scripts/check_aperture.py --json` | `opa_gate.py aperture` |
| the SCREENSHOTS: every surface x variant through the theme, contact sheets, the strip, and their generated index (`--list` the plan; `--json` the measurement policy/screens.rego decides) | `catalog/library/render_screens.py` | `python3 catalog/library/render_screens.py --list` | — |
| is a symbol's work IN THE TREE — open ones (`--status`) and closed ones (`--regressions`) | `scripts/check_symbol.py` | `python3 scripts/check_symbol.py --list` | — |
| Plasma / Konsole colour schemes (`--semantic` for the semantic set on the selection field; the verdict is `scripts/opa_gate.py selection_contrast`) | `scripts/check_selection_contrast.py` | `python3 scripts/check_selection_contrast.py --report` | `.colors` `.colorscheme` |
| how the font→segment projection agrees with the authored tables, per glyph (hits/misses/extras/Jaccard) | `scripts/check_projection.py` | `python3 scripts/check_projection.py [--font F] [--fmt 16\|7]` | — |
| a real font's glyph in the 5x8 matrix (`--render CH` beside the authored bitmap; `--compare` over the authored table) | `scripts/check_matrix_input.py` | `python3 scripts/check_matrix_input.py --render g` | — |
| the ghost as SEEN: composited through alpha per variant (`--compare`), solved through alpha (`--solve`), and the marquee's dot field beside the stroke (`--matrix`); `--json` is what policy/ghost_composite.rego decides | `scripts/check_ghost_composite.py` | `python3 scripts/check_ghost_composite.py --compare` | `opa_gate.py ghost_composite` |
| the ghost's BALANCE: cvd_gate's scan vs ghost_solve's closed form per variant, and the solve's skew (`--json` is what policy/ghost_balance.rego decides) | `scripts/check_ghost_balance.py` | `python3 scripts/check_ghost_balance.py --json` | `opa_gate.py ghost_balance` |
| the palette's constraint GRAPH: declared edges vs the gates that enforce them (`--edges`; `--json` is what policy/palette_graph.rego decides) | `scripts/check_palette_graph.py` | `python3 scripts/check_palette_graph.py --edges` | `opa_gate.py palette_graph` |
| CVD SEPARATION of the declared enforced pairs, per variant (worst-view dE; `--surfaced` also prints the never-gating pairs; `--json` is what policy/separation.rego decides) | `scripts/check_separation.py` | `python3 scripts/check_separation.py --surfaced` | `opa_gate.py separation` |
| the solved ROLE THEME (role → Okabe-Ito colour for a graphviz consumer): optimality, the on-white variant, whether the .dot renders (`--compare` vs the consumer's live assignment; `--json` is what policy/role_theme.rego decides) | `scripts/check_role_theme.py` | `python3 scripts/check_role_theme.py --compare` | `opa_gate.py role_theme` |
| the boot splash's digit glyphs vs the substrate's 7-seg projection (`--table`; `--json` is what policy/plymouth_digits.rego decides) | `scripts/check_plymouth_digits.py` | `python3 scripts/check_plymouth_digits.py --table` | `opa_gate.py plymouth_digits` |
| the decoration states (focus / hover / selection) — pairwise q under the gate's metric, each vs ground | `scripts/check_states.py` | `python3 scripts/check_states.py --map` | — |
| **every place the project DECLARES its licence** (emitters.LICENSE_SPDX, each generator's metadata `License` site by AST, LICENSE / pyproject / ebuild; third-party licences listed and excluded; `--json` is what policy/license.rego decides) | `scripts/check_license.py` | `python3 scripts/check_license.py --list` | `opa_gate.py license` |
| **what the ROOT HELPERS do** (`el-openglo-plymouth`, `el-openglo-sddm` run against a scratch root with a stubbed PATH: which alternative / drop-in they write, whether a missing tool fails loudly; the plymouth `<name>/<name>.plymouth` layout; `--json` is what policy/root_helpers.rego decides) | `scripts/check_root_helpers.py` | `python3 scripts/check_root_helpers.py --list` | `opa_gate.py root_helpers` |
| the retired trademark, anywhere in the tree (`--json` is what policy/mark.rego decides) | `scripts/check_mark.py` | `python3 scripts/check_mark.py --files` | `opa_gate.py mark` |
| third-party imports vs the manifest | `scripts/check_deps.py` | `python3 scripts/check_deps.py --imports` | `.toml` |
| which emitter reads which palette authority (`--json` is what policy/token_source.rego decides) | `scripts/check_token_source.py` | `python3 scripts/check_token_source.py --map` | `opa_gate.py token_source` |
| which segment surface reads which geometry authority, or owns a stroke table (`--json` is what policy/geometry_source.rego decides; `--coverable` perturbs the lattice) | `scripts/check_geometry_source.py` | `python3 scripts/check_geometry_source.py --map` | `opa_gate.py geometry_source` |
| the display registry: its shape, a matrix glyph's bitmap (`--glyph A`), and the round trip / substrate / font-structure facts (`--json` is what policy/display_registry.rego decides) | `scripts/check_display_registry.py` | `python3 scripts/check_display_registry.py --show` | `opa_gate.py display_registry` |
| `segment_topology.py`'s exported API vs its consumers (`--json` is what policy/st_api.rego decides) | `scripts/check_st_api.py` | `python3 scripts/check_st_api.py --used` | `opa_gate.py st_api` |
| the browser theme's emitted manifests (`--json` is what policy/chrome.rego decides; the verdict is `scripts/opa_gate.py chrome`) | `scripts/check_chrome.py` | `python3 scripts/check_chrome.py --dump` | `.json` |
| the partial-recovery record (`--json` is what policy/partial.rego decides) | `scripts/check_partial.py` | `python3 scripts/check_partial.py --list` | `opa_gate.py partial` |
| the segment lattice's own invariants | `segment_topology.py` | `python3 segment_topology.py --selftest` | — |
| Agda source (`ELProjection.agda`) | `../substrate/scratch/agda_defs.py` + `agda_lex.py` | `python3 ../substrate/scratch/agda_defs.py <name>` | `.agda` `.agdai` `.lagda` |
| the git hooks: which are installed, where each resolves | `scripts/check_hooks.py` | `python3 scripts/check_hooks.py --list` | `pre-commit` `post-commit` `pre-push` |
| the paths-forward queue (symbols, order, lock, residue, ledger) | `.venv/bin/mikemol-paths-forward` (mtools; the ONE writer, paths-forward-loop §0) | `.venv/bin/mikemol-paths-forward --state .claude/paths-forward.json --queue` | `paths-forward.json` `paths-forward.ledger` |
| the Gentoo overlay: markers, the ebuild, the staged install tree | `scripts/check_ebuild.py` | `python3 scripts/check_ebuild.py --tree` | `.ebuild` `layout.conf` `repo_name` |
| the install set (what the theme puts under /usr) | `make_deb.py` | `python3 make_deb.py --stage <dir>` | — |
| the palette as CSS custom properties (web / site) | `scripts/check_css.py` | `python3 scripts/check_css.py --map` | `.css` |
| the Union styles: which Breeze alphas are solved, to what, and which are OPEN (`--json` is what policy/union.rego decides; the verdict is `scripts/opa_gate.py union`) | `scripts/check_union.py` | `python3 scripts/check_union.py --map` | `overrides.css` `variables.css` |
| the terminal palettes (Konsole, Alacritty, foot, Windows Terminal, Termux) — one ansi table, five syntaxes | `scripts/check_terminals.py` | `python3 scripts/check_terminals.py --map` | `.alacritty.toml` `.foot.ini` `.windows-terminal.json` `.termux.properties` |
| the Windows .theme files: required sections, colour roles, accent, wallpaper (`--json` is what policy/windows.rego decides; the verdict is `scripts/opa_gate.py windows`) | `scripts/check_windows.py` | `python3 scripts/check_windows.py --map` | `.theme` |
| the Firefox theme manifests: key → role, required keys, colour_scheme, gecko id | `scripts/check_firefox.py` | `python3 scripts/check_firefox.py --map` | — |
| the emitted fonts: tables, cmap, contour count vs the substrate, orientation; `--render CH` draws a glyph from the TTF; the verdict is `scripts/opa_gate.py font` (`--json` is what policy/font.rego decides) | `scripts/check_font.py` | `python3 scripts/check_font.py --render 2 --png out.png` | `.ttf` |
| the GTK sheets: libadwaita variable → role, the documented-name set, bg/fg pairs | `scripts/check_gtk.py` | `python3 scripts/check_gtk.py --map` | `gtk3.css` `gtk4.css` |
| the inheriting icon + cursor themes: parent chain per variant, directories, the LnF defaults that select them, parents installed here; the verdict is `scripts/opa_gate.py inherit` (`--json` is what policy/inherit.rego decides) | `scripts/check_inherit.py` | `python3 scripts/check_inherit.py --map` | `index.theme` `cursor.theme` |
| a sender's hue on the lit token, gated (the 12-bucket table per variant; which hues fall back) | `scripts/check_rehue.py` | `python3 scripts/check_rehue.py --map` | — |
| the marquee's body-markup parser, run headless on synthetic bodies (`--cases` shows text + style runs) | `scripts/check_marquee_body.py` | `python3 scripts/check_marquee_body.py --cases` | `.js` |
| the one-shot Plasma update script (legacy per-variant ids -> the one ids) run headless against a fake shell shaped like the operator's appletsrc; `--json` is the shell afterwards | `scripts/check_migration.py` | `python3 scripts/check_migration.py --json` | — |
| what the marquee did on THIS desktop (`--containments`: every containment's plugin, wallpaper plugin and applets — what decides whether the desktop comes up): the shell's stderr target, journal lines (only under the systemd unit), and each applet instance's settings + trace tail from the appletsrc | `scripts/check_marquee_host.py` | `python3 scripts/check_marquee_host.py` | `appletsrc` |
| THE WIDGET UNDER TEST: the whole marquee run headless against a stubbed notification model on a timeline; `--trace` prints every sample (text / x / running / count); `--hovered` shows the pointer-at-(0,0) stall; `--motion` how the board MOVES (snapped vs raw x velocity, the snap's quantum — the jump the operator sees); `--json` is what policy/marquee_live.rego decides | `scripts/check_marquee_live.py` | `python3 scripts/check_marquee_live.py --trace` | — |
| the ONE Alt+Tab switcher package: structure, the id the LnF defaults name, the root, lint, which Kirigami.Theme role each colour is BOUND to, and what those bindings RESOLVE to per variant under the real theme engine (`--json` is the measurement policy/taskswitch.rego decides) | `scripts/check_taskswitch.py` | `python3 scripts/check_taskswitch.py --map` | — |
| what Kirigami.Theme bindings resolve to under a VARIANT — the real engine on a private kdeglobals (the headless plasma-apply-colorscheme probe) | `theme_probe.py` | `python3 theme_probe.py EL-Amber` | — |
| EVERY emitted QML document: qmllint's error set + the finite-animation `running:` binding rule (`--list` per document; `--json` is the MEASUREMENT policy/qml_lint.rego decides) | `scripts/check_qml_lint.py` | `python3 scripts/check_qml_lint.py --list` | `.qml` |
| the REQUIREMENTS as rego: which policies exist, whether each check measures (`--list`), every rule's refuse/admit pair (`--test`), one check's verdict (`<name>`: deny / withheld sets → exit 0/1/3), a NEGATIVE fixture's typed denial (`<name> FIXTURE --expect denied:S0`: 0 only when exactly those rule ids denied; a crashed reader is 1, never 0), the W50 migration census (`--census [--cpu]`: which warrants still cite a check that decides in Python) | `scripts/opa_gate.py` | `python3 scripts/opa_gate.py --list` | `.rego` |
| what Android's Monet derives from the palette (surface/primary/on_surface vs ground/lit/fg, per variant; `--json` is what policy/monet.rego decides) | `scripts/check_monet.py` | `python3 scripts/check_monet.py --map` | `opa_gate.py monet` |
| is the shipped palette SOLVER output: every cvd_gate attribute the tree calls (AST walk), whether make_palette / make_schemes import, whether GRID is the authored fallback (`--api`; `--json` is what policy/palette_chain.rego decides) | `scripts/check_palette_chain.py` | `python3 scripts/check_palette_chain.py --api` | `opa_gate.py palette_chain` |
| where each emission is published, and the KDE Store's category taxonomy (OCS; `--json` is what policy/publishing.rego decides) | `scripts/check_publishing.py` | `python3 scripts/check_publishing.py --rows` | `publishing.md` `ocs-categories.xml` |

⚑ **THE LAST TWO ROWS CLAIM FILENAMES, NOT SUFFIXES.** A hook script has no suffix, so a
suffix-only table could never route it; the borrowed hook's selftest asserts that the
live table carries both kinds of claim, and this repo's table failed that arm (54/55)
the day the hooks first ran here. Suffix wins over filename when both match, so
`paths-forward.json` is still routed by `.json` to `check_chrome.py` — the row here
records ownership; the routing precedence is substrate's.

⚑ **THE AGDA ROW POINTS OUT OF THIS REPO, AND THAT IS CORRECT.** `ELProjection.agda`
models this system in substrate's F₂ vocabulary, and substrate *provides* the readers for
that artifact kind — the same relationship as the two PreToolUse hooks. A tool is named
by where it lives, not by which repo happens to hold the file it reads; reimplementing an
Agda reader here to avoid pointing outward would be the reuse-search miss the standing
rule warns about.

## How to use one

**Run a tool bare to list its modes.** Every tool takes `--selftest`, refuses an unknown
flag rather than silently degrading to verbose-but-passing, and reports **n of m** rather
than a bare count — so an empty population is distinguishable from a clean result.

⚑ **A tool that finds nothing says which.** `check_compiles` refuses when its search
matches no files at all, because "0 failures over 0 files" and "0 failures over 24 files"
must not print the same thing. If you see a bare count anywhere, that is a bug.

## For dispatched agents

If you are answering a question about this repo, find its row above and run that tool.
If no row fits, say so plainly and **name the tool that should exist** — do not fall back
to grep and present the result as if it were the answer. The gap is the finding.
