# Bazel survey (⟐W78) — how the active repos build, before el-openglo moves

Operator, 2026-09-25: re-rendering, re-recording the parity baseline and re-writing
the action keys by hand after every painter edit "is a strong argument to shift to
the bazel pattern most of the other active repos are using" — and: "speak with the
agents over the repos you find BUILD files in."

Repos with a root `MODULE.bazel`: cassian-observability, linux-sources,
luthen-observability, mtools, paperkit, sre-troubleshooting. Sessions live for four;
the same questions went to each (host-coupled actions, Python deps, the remote cache,
checks-as-tests, and what they would do differently). cassian-observability and
sre-troubleshooting have no session and are read directly.

This file records the ANSWERS as given, with their paths. The synthesis — the pattern
they share and what el-openglo adopts — comes after all replies are in, and is proposed
to the operator before anything is built.

## What el-openglo builds by hand today (what Bazel would replace)

- `scripts/check_action_key.py` — per-output input hashes, `--write` after a rebuild
- `catalog/library/render_screens.py` — re-renders only stale outputs
- `schemes_artifact.py` — content-addressed palette builds under `.build/schemes/`
- `scripts/check_template_parity.py --record` — stays a human REVIEW of a template diff
- the host-coupled parts: the `qml` runner and `qmllint`, the KDE platform theme,
  the optional GPU path, and `sys-apps/sandbox` inside @EBUILD's staging

## What a Qt render actually reads — decomposed (operator, 2026-09-25)

I first wrote "our Qt renders that need the live KDE theme belong in the host-reading
tier". The operator: "If you think this, you should recursively decompose what you're
doing there." Decomposed, from the code (`scripts/render_qml.py:407-444`,
`theme_probe.py`, `qt_sandbox.py`), a render reads:

1. **Tree inputs** — the QML template and its companions (marquee-body.js,
   ApertureField.qml), the harness, a config dict. Declared; hermetic.
2. **The variant's colour scheme** — NOT the live theme. `theme_probe.env_for(variant,
   xdg)` gives every render a PRIVATE `XDG_CONFIG_HOME` whose `kdeglobals` IS the
   variant's `.colors` (a build output of make_schemes). Hermetic once .colors is an input.
3. **The display session** — none. `qt_sandbox` strips DISPLAY / WAYLAND_* / XAUTHORITY,
   sets `QT_QPA_PLATFORM=offscreen`, `KDE_DEBUG=1`, `RLIMIT_CORE=0`; the gated path is the
   software scene graph.
4. **The toolchain** — the `qml` runner, Qt 6, KF6 (Kirigami, the KDE platform-theme
   plugin), Mesa's software GL. Host PACKAGES with versions: pinnable — stamped into the
   key (linux-sources' `toolchain` tier) or baked into an executor image (paperkit's).
5. **Fonts — an UNDECLARED HOST INPUT, found by this decomposition.** Nothing sets
   `FONTCONFIG_FILE` / `XDG_DATA_DIRS`, so fontconfig resolves against the host's installed
   font set. This is what action_key's withheld "screens sees the host and the host is
   UNPINNED" was measuring. Fix: a declared fonts.conf over declared font files — then it
   is an input, not a tier.
6. **Time** — the widget runs on virtual time, yet two animation strips TORE under load
   (⟐R9). Something still reads the wall clock: a hidden input, i.e. a bug, not a tier.
7. **The GPU** — only under `EL_QT_GPU=1` (the halo via MultiEffect). Genuinely host
   hardware + driver — but an OPT-IN diagnostic path, not the gated render.

So the gated renders are **toolchain-tier and hermetic** once fonts are declared and the
wall-clock read is found: a pure function of (template, .colors, fonts, the Qt/KF/Mesa
versions). The only host-reading steps are the opt-in GPU halo and the operator's live-
desktop look (the LIVE bucket), which is not a build step at all. The "host-reading tier"
claim was reasoning from the word "KDE", not from what the process opens.

## paperkit (paperkit-e1, 2026-09-25, paths at 88e535d)

1. **pk_* rules are paperkit-INTERNAL in practice.** The graph is a module extension
   (`tools/bibtex.bzl`, `bib.project(...)` in paperkit's MODULE.bazel) that reads each
   project's warrants.bib at fetch and generates `@paperkit_<proj>` repos. Its generated
   BUILD files use `@@//…` (the MAIN repo) — as a bazel_dep those would resolve into the
   consumer, not paperkit (unverified). Rules: `tools/verb.bzl` (pk_cmd / pk_file /
   pk_result / pk_gate, tiers), `tools/calc.bzl` (pk_calc / pk_eval / pk_pyc, the per-cell
   sweep), `tools/grade.bzl`, `tools/witness.bzl`. A supported consumer surface is a
   summit decision (≥2 consumers). **linux-sources and cassian each COPIED verb.bzl.**
2. **Tier is a warrant field**: `tier = {sandbox|local|toolchain}`, default sandbox,
   honoured by `_tier_exec` in `tools/verb.bzl`. sandbox = hermetic cell, Δ-swept;
   local = host-coupled, unsandboxed; toolchain = a specific external tool, run in the
   executor POOL and STAMPED with the image digest (`STABLE_TOOLCHAIN_IMAGE` via
   `tools/toolchain_status.sh` → `tools/image_digest.py`). **Our Qt-render checks are
   `toolchain`, and the tool belongs in an executor image, not on the host**
   (`image/executor/Containerfile`: pinned tools, one layer each; `exec_properties Pool`,
   `tools/pool.bzl`).
3. **Python**: cells run under the executor's python with the engine staged as its import
   cone (`calc.bzl:434-463`); build-time deps via rules_python `pip.parse`
   (`tools/requirements_build.txt`); tool deps in the executor image; **never the host
   python for a gated verdict.** Wheel: `//paperkit:wheel` (`tools/wheel.py`).
4. **Hindsight:** (a) declared inputs from day one — 11 claims walked the tree, which no
   declaration covers; (b) records-as-deps (`result:` edges) instead of re-running another
   gate inside a check; (c) finer cones — every cell imports resolver.py, so one edit
   re-ran 172,926 of 172,988 actions; (d) remote execution with no local fallback from
   the start (integrity, not speed); (e) file labels (`builds`), not directories;
   (f) no per-spawn JSON execution log — it cost an OOM; take metrics from BES /
   BuildBuddy's execution records.

## luthen-observability (luthen-observability-85, 2026-09-25, paths in ~/github/luthen-observability)

1. **Host-coupled actions are TESTS, forced into a tier.** `tools/verb.bzl` `pk_witness`
   (~251) with `_WITNESS_TAGS` (~191) = ["external","local","no-sandbox","no-cache",
   "no-remote"], FORCED by the macro, not defaulted; env pass-through `_WITNESS_ENV`.
   Key fact (bazel 8.7 source, via linux-sources): an `external`-tagged TEST runs
   unconditionally; no build action has that property — so a host-reading step is a test,
   never a stamped genrule. **Qt renders that must see the live KDE theme/GPU belong there;
   qmllint over declared inputs can be hermetic.**
2. **Python**: `python.toolchain` (MODULE.bazel ~27) + `pip.parse(hub_name="checks_pip",
   requirements_lock="//tools:checks-runtime.lock")` (~81) — a uv-compiled, hashed lock
   (`tools/checks-runtime.in` → `.lock`). Not the host .venv: a staged venv resolves
   outside the sandbox (MODULE.bazel ~65-80).
3. **Remote**: BuildBuddy on the box, in k3s. `.bazelrc` ~8-16 (`build:remote`,
   `build:incluster`). **Never copy addresses** — resolve them
   (`python -m checks.endpoints_query --side host grpc-bes`); paperkit's
   `tools/project_endpoints.py` writes them into .bazelrc by name.
4. **Checks as tests, two rungs**: hermetic py_tests from `checks/unit_tests.bzl` (a
   DECLARED population, not globbed) and local witnesses via pk_witness (BUILD.bazel
   ~140-222). Exit semantics 0 ok · 1 refused · 2 cannot run · 3 withheld;
   `checks/check_producer.py` (~21/68) maps them (EXPECTED = {0,1,3}, else 2) and
   `tools/verdict.py` writes the verdict record into the test's undeclared outputs.
5. **Hindsight:** declare the test population and the witness tier on day one
   (retrofitted after stale-cache false greens); ONE subprocess seam (`checks/run_tool.py`,
   enforced by the gate); no wall-clock timeouts (prlimit --cpu, soft == hard).

## mtools (mtools-35, 2026-09-25, paths in ~/github/mtools)

1. **The pattern for a Python repo whose distributions are also uv-installable — and a
   CONSUMER of the wheels does not need it** (we install mikemol-* sha-pinned with uv; that
   is the whole consumer contract). mtools' Bazel side is its own gate: MODULE.bazel with
   TWO pip hubs per dist — `<dist>_deps` from `<dist>/requirements.txt` (shipping closure)
   and `<dist>_dev` from `<dist>/uv.lock` (dev group). Two resolvers over one pyproject
   once disagreed ("TWO-RESOLVERS-DISAGREE"), so the dev hubs read uv.lock directly.
   `patches/`: a rules_python patch so git-sourced deps in uv.lock (paperkit) reach pip
   as `pkg @ git+…@sha`. `venv.bzl` `venv_from_hub` builds `//<dist>:.venv` — the hermetic
   venv the checkers run in. Cleanest BUILD template: `ledger/BUILD.bazel`
   (`pycodemod/BUILD.bazel` for a third-party dep).
2. **Tests**: one py_test PER TEST MODULE through `pytest_main.py` (`--strict-markers
   --strict-config`); ruff (`@ruff//:bin`), mypy (`mypy_check.sh` + `mypy_runner.py`),
   ratchet, a mutation grid (`mutate_runner.py`: each def body -> raise; refuses a SURVIVED
   site), shellcheck. **Bazel tests use ONLY hub deps, never a host venv**; the host
   `.venv` is for the edit loop.
3. **Remote**: `.bazelrc` ~105-170 — disk cache `~/.cache/bazel-disk/<repo>`; remote cache
   + BES at the in-cluster BuildBuddy; `--config=remote` for RBE with an explicit exec
   platform (`rbe/BUILD.bazel`). Shared infrastructure — point at it, read the comments
   first. **`--remote_instance_name` does NOT isolate** (measured cache hit across names —
   not a tenancy boundary). `--config=remote` is fail-closed (no `--remote_local_fallback`).
4. **Hindsight:** BES coupling — a BES upload failure makes `bazel test` exit 38 with every
   test green; keep BES opt-in, or tell "tests failed" from "upload failed". One resolver
   on day one (dev hubs read uv.lock). Set implicit `__init__.py` handling once in
   MODULE.bazel. Start every dist from the `ledger/` template.

## linux-sources (linux-sources-1b, 2026-09-25) — note: it does NOT build kernels

It reads pinned source corpora; its Bazel graph is a CHECK gate, not a product build.

1. **Dependencies**: paperkit arrives TWICE. For Bazel, a module extension builds a
   **WHEEL** from sibling `../paperkit` at fetch (`tools/paperkit_ext.bzl`,
   `tools/paperkit_wheel.bzl`; a local path). **Why a wheel, not editable/.pth: an editable
   pointer resolves through the execroot symlink into the LIVE tree, so a check imports
   unstaged source and passes** — "the most important single lesson here". For uv,
   pyproject pins `paperkit @ git+…@<full sha>`. Corpora: `tools/corpus_ext.bzl` GENERATED
   from `corpora.tsv` (http archives with integrity hashes; only confirmed-hash rows).
   BCR: rules_python 2.3.3, platforms. (Residue, stated: a stale `substrate_ext` wheel.)
2. **Host-coupled work: a TIER on every action as execution_requirements**
   (`tools/verb.bzl` `_tier_exec`): `local` = {local, no-sandbox, no-cache, no-remote};
   `toolchain` = {local, no-sandbox, no-remote} — host-coupled but CACHED, correct because
   identity is STAMPED into the key (`build --stamp`, `--workspace_status_command=
   tools/check_status.sh` emitting STABLE_ keys, read via `ctx.info_file`); `sandbox` = {}
   (default). From bazel 8.7 source: execution_requirements are part of the action KEY (tiers
   never collide); `use_default_shell_env` keys `--action_env` by name AND value, but a
   pass-through with no value is keyed by NAME ONLY — a stale-green surface.
3. **Python**: rules_python for the interpreter, uv for the lock, never the host venv in a
   sandbox. `python.toolchain(3.14)` + two `pip.parse` hubs from `uv pip compile` locks:
   `gate_pip` (hermetic mypy) and `slice_runtime_pip` (what the interpreter needs to RUN) —
   different questions (a .pyi stub satisfies mypy, is worthless at runtime). The uv .venv
   is deliberately NOT wired in (host-absolute pointers escape the sandbox).
4. **Hindsight:** GENERATE every BUILD file from a declaration and gate it against drift
   (`ls_gate/gen_*.py`; a hand list went 19 declared -> 2 wired in three ticks). Run the gate
   over the STAGED tree in a fixed-path sibling worktree with its own venv
   (`tools/gate_staged.sh`; a working-tree gate certifies unstaged edits). `--config=remote`
   on UNCONDITIONAL lines, no `--remote_local_fallback`, `test --notest_keep_going`. Every
   "it works" claim two-armed with a control (`bazel clean` + `--disk_cache=`; a warm output
   base gave greens that measured nothing, twice). Trap: a no-cache verdict that fails
   transiently is REPLAYED from the action cache until an input changes (their W25). "Your
   stale-only re-renders map onto action-cache hits; content-addressed palette builds are
   what the CAS already is — you're mostly deleting code."

## cassian-observability (read directly, 2026-09-25)

1. **Engine**: `tools/verb.bzl` — `pk_cmd` (one check = one action writing a
   `<name>.verdict.json` via `tools/verdict.py`; the verdict is the EXIT CODE, never a parsed
   transcript) and `pk_gate_test` (aggregates the records; `bazel test //:gate` reds iff any
   reads fail). Copied from linux-sources, which copied paperkit's.
2. **Tiers** (`_tier_exec`): `sandbox` (hermetic, cached — ALSO the tier for arms that WRITE
   a tree: the sandbox is a throwaway copy; "a writer wants MORE sandbox, not less", learned
   from a measured escape), `toolchain` (host env, cached on declared inputs, no stamp),
   `local` (host, never cached — only for true live-host probes).
3. **BUILD.bazel is GENERATED** (`tools/gen-gate-build.py` from the check / arm registries)
   and a `stale-gate-build` target reds the gate if it drifts. Arm `data=` is a declared glob.
4. **.bazelrc**: disk cache + UNCONDITIONAL remote cache and BES on the loopback BuildBuddy
   (operator directive 2026-09-07: no opt-in, no fallback); `--config=local-k8s` routes
   actions to the executor pod, fail-closed. A failing action replays its stdout to stderr
   only on rc≠0, so a red check explains itself and a green one stays quiet.

## sre-troubleshooting (read directly, 2026-09-25) — scaffolding, UNTRACKED

`MODULE.bazel`, `.bazelrc` and `tools/` exist but are untracked (git status `??`), so the
survey's "has a root MODULE.bazel" is true of the disk, not of the repo's history. Its ONE
job: run veraPDF (the PDF/UA verdict) in luthen's `paperkit` EXECUTOR POOL, because the host
has no JVM. paperkit's checks enter as `new_local_repository` over the sibling checkout;
`.bazelrc` is `--enable_bzlmod` plus `try-import .bazelrc.remote` (generated). **The pattern
el-openglo needs from it: a TOOLCHAIN THE HOST LACKS, SUPPLIED BY AN EXECUTOR IMAGE.** For us
that is Qt + the declared fonts (R10): a render action in an image whose fontconfig names
only declared files keys on the image digest, and the host-font weakness `output_keys`
names goes away instead of being recorded.

## el-openglo design — PROPOSAL (for the operator; nothing is built)

- **Engine**: adopt `verb.bzl` + `verdict.py` as the three copies did — but as paperkit's
  packaged rules if summit's ≥2-consumer decision has landed, not a fourth copy.
- **Gates**: each warrant's `tool:` check becomes a `pk_cmd`, BUILD generated from
  `warrants.bib` through paperkit's parser, with a staleness target — the same shape as
  cassian's registry-generated BUILD. Tiers: pure policy/selftests `sandbox`; Qt harness
  checks `toolchain` until an image exists, then executor.
- **Renders**: each declared output of `render_screens.plan_all()` becomes ITS OWN action
  (outputs = the PNG), inputs = what `stagers()` stages. This replaces `check_action_key`'s
  hand-computed keys and `--jobs` with the action cache and Bazel's scheduler. The derived
  sheets depend on their tiles as build edges. The key's named weaknesses (host fonts, the
  runner code at module grain) become either declared inputs or an image digest.
- **Order**: (1) gates only, the `pk_gate_test` beside today's pre-commit, differential
  until they agree; (2) renders as actions under `toolchain`; (3) the executor image (R10).
- **Open questions for the operator**: packaged rules vs a fourth copy; whether renders
  belong in the unconditional remote cache (a GPU render is only as pure as its image).
