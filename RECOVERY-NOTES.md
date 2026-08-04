# EL-Indiglo — recovered source (from session transcripts)

Reconstructed after a container filesystem reset wiped the local (never-pushed) git repo.
Source: /mnt/transcripts (on-disk sessions through 2026-07-04 21:37).

---

## THE RENAME: why this file still says "Indiglo" and nothing else does

The project was first built as **el-indiglo**. "Indiglo" is a registered trademark
(Timex), so the project was **renamed to el-openglo** and the prior mark was retired
**everywhere** — not only as the project name, but in descriptive prose and in palette
token names (`indiglo-on` became `openglo-on`). The scrub is deliberately total rather
than nominative: the concern is a trademark, and keeping the word for "the effect it
describes" keeps the exposure. Prose that leaned on the mark was rewritten to describe
the effect instead ("selecting anything switches the backlight on").

Two files are excluded from the scrub, by policy, because they are **historical
records** and rewriting them would falsify the history they exist to preserve:

- **this file** — the verbatim provenance record of the pre-rename recovery;
- **COTYPE.md** — the append-only design log.

`scripts/check_mark.py` is the only place that spells the retired mark; it is the sole
authority on the scrub and the worklist cites it. It excludes those two paths by PATH,
never by obfuscating the search string — a needle spelled `"ind" + "iglo"` would hide
from the very grep a human runs to audit the check.

---

## CORRECTIONS TO THIS FILE (verified against the tree, 2026-08-04)

⚑ **The "main rebuild gap" below is STALE, and it is the reason this repo computes
status instead of recording it.** The notes say `segment_topology.py`'s later API — the
FORMATS 7/9/14/16/22 lattice, `project()`, and the `DIGITS16`/`LETTERS16`/`SYMBOLS16`
glyph tables — was not recovered. **All of those are present** in the recovered file.

What was genuinely absent, measured by diffing consumer references against module
exports: **`SEG22`, `GEOM22`, and `endpoints`** — three symbols, not a whole API.

- `endpoints` shipped in `segment_topology_ADDITIONS.py`, now merged in (that file is
  gone; its docstring said to append it).
- `SEG22` / `GEOM22` were **reconstructed** from COTYPE.md session 27 (⊕SEG22) and its
  closure section, which pin the structure exactly: 22-seg = 16-seg + six additions
  (two dots `p1`/`p2`, one lower-left diagonal `n1`, three descender bars `dl`/`dc`/`dr`
  below the baseline). The identifiers and their roles are **recovered**; the literal
  coordinates did **not** survive and are **derived** in the existing cell convention.
  The log also states the gate that makes this checkable rather than invented —
  *projection 22→16 is byte-equal to native `glyph16`* — and `segment_topology.py
  --selftest` asserts it across all uppercase and digits.

⚑ **A file the notes never knew was missing: `qml_sanity.py`.** `make_deb.py` imports it
from *inside a function body*, so its absence never surfaced as an import error. COTYPE.md
shows it was a module of this project (a qmllint gate over the emitted QML, using
PySide6), not a package. It is recorded as absent in `pyproject.toml`; the packaging
path's QML gate is missing until it is rebuilt.

⚑ **The lowercase 22-segment glyph tables are NOT recoverable** and no consumer
references them. The design log describes them (s/x use the extra diagonal, i uses the
two dots) but contains no table.

## What this IS
- The el-indiglo working tree as it existed in the ON-DISK transcript sessions.
- COTYPE.md = first creation + all 140 heredoc appends found on disk (the design log).

## HONEST GAPS (read before trusting a file)
- Files marked PARTIAL below had later str_replace edits whose anchor text was not found
  during replay -> they are at an INTERMEDIATE state, not their final form.
- Files created in LATER sessions (after 21:37, which were COMPACTED and whose transcripts
  are NOT on disk) are ABSENT here. Known-absent, high-value: glyph_match.py, project_font.py,
  make_glyph_ink.py, render_showcase.py, TYPES.md, ELProjection.agda, and COTYPE sessions ~66+.
  These exist only in the compaction summary / current context, not in on-disk transcripts.
- The shipped .deb (up to 1.25.0) and all PNGs survive separately in /mnt/user-data/outputs/.

## Files recovered (create_file/str_replace replay)
- COTYPE.md  (2810 bytes)
- EL-Indiglo-Lit.colors  (3446 bytes)
- EL-Indiglo-Lit.colorscheme  (1104 bytes)
- EL-Indiglo.colors  (3414 bytes)
- EL-Indiglo.colorscheme  (1112 bytes)
- README.md  (2538 bytes)
- cvd_gate.py  (2994 bytes)  ** PARTIAL **
- display_types.py  (5883 bytes)
- el-phosphor-designer.jsx  (15006 bytes)
- glance_audit.py  (7204 bytes)  ** PARTIAL **
- make_aurorae.py  (8138 bytes)
- make_chrome.py  (2812 bytes)
- make_clock.py  (11273 bytes)  ** PARTIAL **
- make_deb.py  (32513 bytes)  ** PARTIAL **
- make_font.py  (4372 bytes)  ** PARTIAL **
- make_konsole.py  (4220 bytes)
- make_kvantum.py  (5915 bytes)
- make_notify_marquee.py  (5837 bytes)
- make_palette.py  (14312 bytes)  ** PARTIAL **
- make_plasma.py  (5898 bytes)
- make_plymouth.py  (11926 bytes)
- make_preview.py  (4411 bytes)
- make_schemes.py  (15346 bytes)  ** PARTIAL **
- make_segment_display.py  (7566 bytes)
- make_wallpaper.py  (4583 bytes)  ** PARTIAL **
- make_wallpaper_live.py  (9875 bytes)
- segment_topology.py  (6038 bytes)
## Context-reconstructed research files (added in a second pass)

These are the ACTIVELY-DEVELOPED research pipeline files from the later (compacted)
sessions. They are NOT in the on-disk transcripts, so they were reconstructed from THIS
conversation's own create_file/heredoc tool calls (high fidelity — the actual text I
wrote, still in context — but not a mechanical replay, so verify behavior):

- make_glyph_ink.py      — native TTF winding ink field (⊕FONT-INK-INGEST). OK compile.
- project_font.py        — ingest (winding_ink/raster_ink) + cohomological matcher. OK.
- glyph_match.py         — REIFIED matcher: region_graph + strata + Matthews-phi congruence
                           + derez. OK compile. (The current, canonical matcher.)
- render_showcase.py     — phosphor renderer for the showcase PNGs. OK compile.
- TYPES.md               — the typed data-flow model of the whole pipeline.
- ELProjection.agda      — the system modeled in substrate F₂ vocabulary. CAVEAT: current
                           substrate HEAD's ⟡ban-decompose gate rejects `using` imports;
                           rewrite to bare imports before committing.
- segment_topology_ADDITIONS.py — endpoints() + display_geom() to APPEND to the (early,
                           transcript-recovered) segment_topology.py.

### Still not fully recoverable (design log has the intent; code is partial/absent)
- segment_topology.py's LATER growth: the full GEOM22, the FORMATS 7/9/14/16/22 lattice
  with merge maps, and the DIGITS16/LETTERS16/SYMBOLS16 glyph tables + project(). The
  recovered base is an EARLY version; glyph_match/render_showcase IMPORT the later API
  (ST.SEG22, ST.FORMATS, ST.project, ST.DIGITS16/LETTERS16/SYMBOLS16, ST.GEOM16/GEOM22).
  Reconcile from COTYPE.md before running. This is the main rebuild gap.
- make_segment_display.py (SegmentChar QML) is transcript-recovered (present, full).
- COTYPE sessions ~66-92 (research + substrate arc): the DESIGN narrative is in this
  conversation's compaction summary; the on-disk COTYPE.md ends earlier.

### Bottom line
Runnable-after-reconciliation: the build tree (transcript-recovered) + these research
files, once segment_topology.py's later API (FORMATS lattice + glyph tables) is restored
from COTYPE.md. The single highest-value missing piece is that segment_topology API.
