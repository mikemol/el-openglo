# Render speed — where the screens CPU goes, and what to cut

Measured 2026-09-22 (swarm-2 study; one variant, EL-Openglo, extrapolated ×6).
CPU = user+sys from getrusage, OPENBLAS_NUM_THREADS=1. Measurement scripts were
scratch-only and are not kept.

## Where ~460 s of CPU per full run goes

| component | CPU |
|---|---|
| pinholes-anim frames: 390 separate `qml` processes × 0.67 s | ~260 s (~130 s of it process startup) |
| `make_notify_marquee.main_qml()` re-run 18× with identical output, ~8 s each | ~145 s |
| marquee `qml` children | ~41 s |
| 24 `render_qml` stills | ~12 s |
| contact sheets, imports | ~2 s |

- Every still and every animation frame is its own `qml` process, run serially:
  432 processes per full run. The startup floor is 0.33 s CPU (1.8 s wall).
- `main_qml()` has no variant input, so all 18 calls produce the same text. Its
  8 s splits into `make_glyph_ink.matrix_glyph` ×121 (fontTools rebuilds the glyph
  set 241 times) and `make_palette.hue_table` → `cvd_gate.worst_view_dE`
  (11,616 colorspacious conversions).
- The palette solve is NOT re-run: the cache is warm and the W68 lock is only
  taken on a miss.
- A fixed 1200 ms timer before each grab costs wall time, not CPU.

## Ranked speedups

| # | change | CPU saved | risk | kind |
|---|---|---|---|---|
| 1 | Key screens per (surface, variant) over what each `qml` process actually reads (subject.qml bytes, companion QML/JS, harness + fill, `<variant>.colors` bytes, QT_* env, runner/post-processing code, host). A rebuilt input with identical bytes stops there (early cutoff). | all of it on a no-op upstream change; about ⅔ on a one-template change (estimate) | medium: an under-declared key reads fresh when it is stale | structural (W61) |
| 2 | One `qml` process per variant for pinholes-anim: step `offsetRows` in the harness and grab each frame (the pattern `check_marquee_live` already uses). | ~127 s | medium: the frame sequence must still pass S5/S6 | tactical |
| 3 | Memoise `main_qml()` once per process. Also a precondition for #1, whose key computation runs the Python half. | ~135 s | low | tactical |
| 3b | Make `main_qml` fast: open the font once in `matrix_glyph`; memoise `hue_table` and the CVD floors. Helps every checker that emits it. | ~7 s per call (estimate) | low | tactical |
| 4 | Up to `min(4, cpu_count//8)` worker processes (not threads: `subject()` calls chdir and edits sys.path) for stills and frames; marquee stays serial because its grabs depend on wall-clock timing. | ~0 CPU; 2–3× less wall (estimate) | low–medium: GPU contention | tactical |
| 5 | Grab after N frames drawn instead of the 1200 ms timer. | ~0 CPU; up to ~6 min of wall | medium: the palette and halo arrive a turn late | tactical |

#2 + #3 take a full run from ~460 s to ~200 s of CPU (measured parts only).

## Why the W68 lock re-rendered all 55 screens

The render reads the palette only as `.colors` bytes (`parse_scheme`,
`theme_probe.env_for`) and as `hue_table` output embedded in `subject.qml`. The
lock changed neither. A consumer keyed on its producer's EMITTED CONTENT, with the
producer keyed on its own source, would not have moved. Keying on the import
closure is correct only for the Python that runs inside the action.
Open: which import path puts make_schemes.py in the screens closure
(`check_action_key --importers` should answer it).
