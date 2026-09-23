# The colours as a declared build output (W75)

> Operator, 2026-09-23: "that's why all that shit needs to be passed as build artifacts."

W68 stopped gated checks from writing the tree. `emitters.atomic_write` stopped readers
seeing half a file. Neither one controls which version of the palette a reader sees.
About 20 readers opened the tracked `EL-*.colors` by path through
`make_preview.parse_scheme`, so two checks in one gate run could judge two different
palettes if anything rewrote the working tree between them. Timing decided the order.
The target is:

**`schemes` is an action whose OUTPUT is one content-addressed artifact, and every
reader DECLARES that artifact as an INPUT.** A reader then sees exactly one version,
and this holds by construction, not by timing.

## 1. Census: who reads the palette

Measured 2026-09-23 with `pycodemod --calls parse_scheme` (33 calls), `--importers
make_preview` (30 sites in 21 files), `--importers make_schemes` (23 sites in 20 files)
and `--literal .colors` (for population reads that go through `listdir`).

### Readers of the `.colors` (through `parse_scheme`, or directly)

| reader | kind | how it reads | first step (this change) |
|---|---|---|---|
| make_chrome, make_firefox, make_konsole, make_union, make_windows, make_cursors, make_plymouth, make_wallpaper, make_wallpaper_live, make_preview (`__main__`) | emitter | `parse_scheme` | snapshot, via `parse_scheme` |
| make_deb (`:538`, `:799`) | emitter (packager) | `parse_scheme` | snapshot, via `parse_scheme` |
| scripts/readme_fragments | emitter (README projection) | `parse_scheme` | snapshot, via `parse_scheme` |
| scripts/render_qml, catalog/library/render_screens, catalog/library/render_samples | renderer | `parse_scheme` | snapshot, via `parse_scheme` |
| theme_probe (`scheme_path`, `env_for` → kdeglobals) | renderer (feeds render_qml, check_taskswitch, check_marquee_live) | opened by path | **snapshot** (`scheme_path` edited) |
| check_aperture, check_ghost_surfaces, check_marquee_live, check_monet, check_urgency_cues, check_windows, concepts.py (`palette-roles-distinct`) | check | `parse_scheme` | snapshot, via `parse_scheme` |
| check_chrome (`variants()`) | check | **population** by `listdir(ROOT)` | **snapshot** (`variants()` edited) |
| render_samples.variants, concepts.py:129-130 | renderer / check | **population** by `listdir` | ⚑ still the tree (B2) |
| check_selection_contrast | check | population from `make_schemes`; checks whether the `.colors` exists | ⚑ still the tree (B2) |

### Readers of `make_schemes.GRID` (the solved palette itself)

- **Emitters:** make_aurorae, make_clock, make_css, make_kvantum, make_plasma, make_sddm,
  make_segment_display, make_wallpaper_live.
- **Checks:** check_geometry_source, check_ghost_balance, check_ghost_composite,
  check_ghost_surfaces, check_inherit, check_monet, check_palette_chain,
  check_palette_graph, check_selection_contrast, check_separation, check_states,
  check_terminals, and check_firefox (for its roster).

`GRID` comes from `.palette-cache.json`, which is written with a flock and an atomic
write. It is the same shape as the `.colors` problem one step further upstream: a
mutable file read by path. The `schemes` artifact is the first edge. The `solve`
artifact is the next one (B3).

## 2. The action graph

What `scripts/check_action_key.py` declares today (`ACTIONS`):

| action | entry | output domain | keyed |
|---|---|---|---|
| `schemes` | make_schemes.py | `./*.colors` | whole action, over its import closure + `templates/` |
| `wallpapers` | make_wallpaper.py | `./*-wallpaper.{png,svg}` | whole action |
| `screens` | catalog/library/render_screens.py | `catalog/library/screens/*.png` | per output (W61), with early cutoff at generators |

Proposed. An edge means "declares as an input, keyed on the producer's content digest":

```
solve (.palette-cache.json)                              ← B3: artifact #2
  └─> schemes  (EL-*.colors)  ══ digest ══╗              ← THIS STEP: artifact #1
                                          ║
        ╔═════════════════════════════════╩═════════════════════════════╗
        ▼                          ▼                                    ▼
  emitters (chrome, firefox,   renderers (render_qml,            checks (~20: aperture,
  konsole, union, windows,     theme_probe → screens,            chrome, firefox, monet,
  cursors, plymouth, preview,  samples)                          taskswitch, screens, …)
  wallpaper[s], readme)             │
        │                           ▼
        └──────────> package (make_deb) consumes emitter outputs
```

- **Actions that should declare `schemes`:** every emitter in the table above, the
  `screens` and `wallpapers` actions, and `render_samples`. These are the readers that
  PRODUCE something. Each one's key should contain the `schemes` digest instead of the
  `.colors` bytes it happened to open. That gives early cutoff for free: if a re-solve
  emits byte-identical `.colors`, the digest does not change and nothing downstream
  rebuilds.
- **Checks are not actions.** They are consumers. What a check needs is to read the
  declared artifact and never the tree, and this step gives it that.

### Where paperkit's Bazel path fits

paperkit already has the protocol. A warrant declares `builds = {<label>}`, and
`tools/cell.bzl: cell_builds_env` exports `PAPERKIT_BUILT_ARTIFACTS="<name>=$PWD/<path> …"`
before the cell runs. `paperkit/tests/boundaries_wheel.py` reads it and keeps no
fallback ladder. That design came from a measured false green: a check walked out to
the checkout and "found" an artifact that had never been handed to it.

**Recommendation: the first step stays inside this repo's graph, and it speaks
paperkit's variable.** `scripts/worklist_gate.py` materialises the snapshot and exports
`schemes=<dir>` in `PAPERKIT_BUILT_ARTIFACTS`, which is exactly what a Bazel cell with
`builds = {//:schemes}` would export. The reasons:

1. **The readers do not change when Bazel arrives.** Moving to Bazel then only changes
   which process sets the variable. No reader is touched again. That is the part worth
   getting right first, and it is done.
2. **el-openglo has no MODULE.bazel.** Adopting one to fix a race means taking on a
   toolchain (a hermetic Python, wheel install, sandbox staging) that none of the flaky
   checks needs.
3. **The host is unpinned** (`catalog/host.json`: declared, not adopted). A Bazel cache
   hit for the Qt-rendering actions (`screens`, TASKSWITCH, MARQUEE-LIVE) is not yet
   licensed across hosts, so Bazel's main payoff (a transportable cache) is not
   available for the expensive half. `schemes` is pure Python, so it would be the first
   target when Bazel does come (B5).

## 3. The first step (implemented)

- **`schemes_artifact.py`** (new, at the root, stdlib only):
  - `materialise()` reads every `*.colors` twice. It refuses to proceed unless both reads
    agree, retrying up to 5 times, and it refuses an empty population. It then writes
    the files read-only into `.build/schemes/<sha256 over (name, sha256(bytes))>/` and
    renames that directory into place in one step.
  - `resolve()` picks the snapshot once per process. It uses the DECLARED path if there
    is one: that path is re-verified, so a digest that does not match the directory name
    RAISES and nothing falls back. Otherwise the process self-materialises.
  - Modes: `--materialise`, `--where`, `--json [--parsed]`, `--race`, `--selftest`. An
    unknown flag is refused.
- **`make_preview.parse_scheme`** reads `schemes_artifact.path(variant)`. That one edit
  moves all 33 call sites.
- **`theme_probe.scheme_path`** reads the snapshot before the installed scheme. This
  covers the kdeglobals that TASKSWITCH, SCREENS and MARQUEE-LIVE hand to Qt.
- **`check_chrome.variants`** takes its population from the snapshot. Otherwise it would
  judge one version's colours against another version's roster.
- **`scripts/worklist_gate.py`** materialises ONCE, as its own process, before paperkit
  runs, and exports the declaration to every check and replay. If the snapshot cannot be
  taken, the gate is REFUSED (exit 2). Its selftest drives this arm.
- **`scripts/check_emitters_run.py`** removes the declaration from its private copy. That
  copy is a build: its `make_schemes` emits the copy's own `.colors`, and every later
  emitter must read those, not the tracked palette.
- **`.gitignore`**: `.build/`.

## 4. Next steps

- **B1**: `check_action_key.ACTIONS["schemes"]` and `schemes_artifact.SUFFIX` both
  declare the output roster (`./*.colors`). Make one of them the authority.
- **B2**: move the remaining tree-population readers (`render_samples.variants`,
  `concepts.py:129`, `check_selection_contrast`) to `schemes_artifact.variants()`.
- **B3**: make `solve` the second artifact: `.palette-cache.json` → `.build/solve/<digest>`,
  and `make_schemes.GRID` reads the declared one. That covers the 21 GRID readers.
- **B4**: key the emitter and `screens` actions on the `schemes` DIGEST in place of the
  `.colors` bytes and `parse_scheme`'s code, so a byte-identical re-solve cuts off early.
- **B5**: when Bazel is adopted, `schemes` becomes the first `genrule` or `pk_*` target
  and the gate stops setting the variable. No reader changes.
- **B6** (a finding, not part of this step): `clock-*`, `live-wallpaper-*` and
  `marquee-anim-*` renders depend on the WALL CLOCK. Re-rendering at 09:59 changed 27
  PNGs, including sheets and the strip, whose HEAD versions showed 08:02. That is an
  undeclared input: the per-output key does not contain time, so these outputs are not
  reproducible from their key. Pin the clock in the harness, or declare time as an input.
- **B7**: collect old snapshots under `.build/schemes` (for example, keep the N most
  recent).

## Weaknesses

1. The snapshot is taken from the working tree. The double read closes the window
   against a writer that finishes. A writer that never stops makes the snapshot RAISE,
   so it never mixes versions. But the gate still judges whatever the tree held at
   materialisation, which is not necessarily the index being committed.
2. Only `.colors` is content-addressed. Templates, the reader's own code and `GRID` are
   still read by path (B3). The race is closed for the `.colors` edge only.
3. A reader that opens `ROOT/EL-*.colors` itself, without going through `parse_scheme`,
   `scheme_path` or `variants()`, bypasses the snapshot. Nothing yet refuses such a
   read. A check for that would be the natural next gate (a `build_graph` rule: no
   literal path to a declared artifact's output domain).
4. Under `check_action_key` the change is honestly STALE: `make_preview` is in the
   import closure of every action. Landing it means re-rendering `screens` and running
   `check_action_key.py --write`, and B6 means that re-render also moves the
   time-dependent PNGs.
