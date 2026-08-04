# EL-Indiglo — recovered source (from session transcripts)

Reconstructed after a container filesystem reset wiped the local (never-pushed) git repo.
Source: /mnt/transcripts (on-disk sessions through 2026-07-04 21:37).

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
