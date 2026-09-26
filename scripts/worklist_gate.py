#!/usr/bin/env python3
"""worklist_gate.py — run the paperkit engine over `catalog/worklist/`.

⚑ WHY THIS EXISTS.  Paperkit is an ENGINE you point at a project directory, not
something to copy in.  But "point at" is otherwise a hand-assembled shell line —
`python3 ~/github/paperkit/paperkit/gate.py catalog/worklist` — carrying three
pieces of knowledge (where the engine lives, which entry point to call, which
directory is the project) in a string a human retypes.  A judgement that lives in
a retyped command evaporates when the turn ends.  This module owns all three.

    worklist_gate.py                 # GATE: are all cited claims discharged?
    worklist_gate.py --summary       # one line per project, plus the open claims
    worklist_gate.py --next          # the open claims, RANKED: grounding, then
                                     #   leverage, then cost (all three derived)
    worklist_gate.py --project       # regenerate the projections from the claims
    worklist_gate.py --discriminate  # Δ: can each check actually FAIL?
    worklist_gate.py --where         # where the engine and the projects resolved
    worklist_gate.py --only <name>   # one project (worklist | cotype)

⚑ THERE ARE TWO PROJECTS, AND EVERY MODE RUNS BOTH.  `catalog/worklist/` is the
repo's own claim graph; `catalog/cotype/` is the 4,600-line design log read
structurally. They are separate paperkit projects because they answer different
questions, but a gate that covered only one would report green while the other
rotted — so the default is BOTH, and `--only` is the deliberate narrowing.

⚑ THE ENGINE IS LOCATED, NOT ASSUMED.  PAPERKIT is resolved from the environment,
then from the conventional checkout, and this REFUSES with the reason when it
cannot be found — never a silent skip.  A gate that degrades to measuring nothing
is worse than one that fails, because it reports green.

⚑ THE WORKLIST IS THE PROJECTION OF THE UNDISCHARGED SUBGRAPH.  There is no
open/closed field anywhere in this system: an item is OPEN exactly when its check
exits non-zero, recomputed every run.  Nothing records status, so nothing about
status can go stale — which is the failure this repo was born from, its own
recovery notes having called a mostly-recovered API "the main rebuild gap".

⚑ CHECKS RUN IN THE PROJECT'S ENVIRONMENT.  The claims exercise modules that need
the declared dependencies, so this re-execs under `uv run` when a project venv
exists and it is not already inside one.  Otherwise a red check would report the
INTERPRETER's missing module as the THEME's defect.
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ⚑ Δ's SWEEP SANDBOXES LIVE OFF md0 (luthen 2026-09-25, declared in luthen 9e216a7):
# paperkit's default ~/.cache/paperkit-sweep sits on the RAID6 under /home, where Δ's
# small writes become whole-stripe rewrites. /var/tmp is the NVMe root. A caller's own
# PAPERKIT_SCRATCH wins; the default only fills an unset one (a session older than the
# environment.d entry has none).
os.environ.setdefault("PAPERKIT_SCRATCH", "/var/tmp/paperkit-sweep")

# name -> project dir.  Order is the order they run in.
PROJECTS = {
    "worklist": os.path.join(ROOT, "catalog", "worklist"),
    "cotype":   os.path.join(ROOT, "catalog", "cotype"),
    # ⚑ README.md IS A PROJECTION (W69). paper.toml sits at the repo ROOT so
    # `out = "README.md"` needs no ../../ and the checks run where the tools
    # live; the claims are catalog/readme/readme.bib.
    "readme":   ROOT,
}
PROJECT = PROJECTS["worklist"]          # kept: the repo's own graph is the default subject

# Where the engine may live, in order.  The env var wins so a checkout elsewhere
# needs no edit here.
CANDIDATES = (
    os.environ.get("PAPERKIT"),
    os.path.expanduser("~/github/paperkit"),
)

ENTRY = {
    None:              ("gate.py", "GATE"),
    "--project":       ("project.py", "PROJECT"),
    "--discriminate":  ("discriminate.py", "DISCRIMINATE"),
}

# ⚑ `--summary` EXISTS BECAUSE ITS ABSENCE WAS BEING PAPERED OVER WITH A PIPE.
# The verdict lines were repeatedly extracted with `… | grep -E 'FAILED|PASS'`,
# which is the judgement living in the turn instead of in a program — the exact
# shape the no-chaining hook refuses. The honest response to "no mode answers
# this" is to add the mode, so: one line per project, plus the open claims.
_VERDICT = ("paperkit-gate: check FAILED", "paperkit-gate: PASS",
            "paperkit-gate: FAIL", "cited/placed/grounded", "coverage complete")

def warrants(bib):
    """{key: record} for one warrants .bib, read by PAPERKIT's own parser, or None.

    ⚑ THE ENGINE THAT GATES THE FILE IS THE ONE THAT READS IT (operator,
    2026-09-25: "Don't use substrate's bibstruct. Use paperkit's."). This read
    through substrate/scratch/bibstruct.py until substrate's in-flight mtools port
    made it import mikemol.witness — a module this venv does not carry — and every
    commit here was refused by a parser that is not even the gate's. paperkit's
    bib.py records consolidating THREE parsers into one; a borrowed fourth is how
    they drift again. Records carry `check` (scalar) and `rests-on` (list); the
    project's paper.toml `[paper] consumer_fields` are passed so none is
    loud-dropped. paperkit is an INSTALLED package (pyproject `tooling`); None when
    it is not importable — the caller refuses, never reads that as "no claims"."""
    try:
        from paperkit import bib as pkbib
    except ImportError:
        return None
    import tomllib
    from pathlib import Path
    toml = os.path.join(os.path.dirname(bib), "paper.toml")
    fields = ()
    if os.path.isfile(toml):
        with open(toml, "rb") as fh:
            fields = tuple(tomllib.load(fh).get("paper", {}).get("consumer_fields", ()))
    return pkbib.parse(Path(bib), consumer_fields=fields)


def _edges(bib):
    """({key: [keys it rests on]}, {key: [keys it enables]}) from warrants(), or None.

    ⚑ ASK THE TOOL THAT OWNS THE FORMAT.  paperkit's own bib.py opens by recording
    that it consolidated THREE parsers which had each re-derived the format; adding
    a fourth here to save one subprocess is how that happens again."""
    recs = warrants(bib)
    if recs is None:
        return None
    out, enables = {}, {}
    for key, rec in recs.items():
        out.setdefault(key, [])
        for parent in rec.get("rests-on") or ():
            out[key].append(parent)
            out.setdefault(parent, [])
        # ⚑ `enables` RAISES LEVERAGE AND NOT LAYER.  It is SEQUENCING — this work
        # is cheaper or safer first — whereas `rests-on` is GROUNDING: a claim
        # cannot be TRUE unless its premises are. Feeding sequencing into the
        # topological layer would assert a premise the source never made.
        for target in rec.get("enables") or ():
            enables.setdefault(key, []).append(target)
            out.setdefault(target, [])
        # `from` is prose order — neither grounding nor sequencing.
    return out, enables


def cost(key, proj, engine):
    """How many DISTINCT things a claim's witness says must change. None if unknown.

    ⚑ LEVERAGE ALONE RANKED A DAY'S WORK ABOVE A ONE-LINE FIX.  `@BUILD` sorted
    first on leverage 4 while `@ROLES` and `@CLOCKFIT` — each a single change,
    each already measured and visible in the sample library — sat below it with
    leverage 0. "What unblocks the most" is a real key and it is not the only
    one; ordering by it alone tells you to start the largest item first, which is
    exactly the sunk-cost ordering the leverage model was introduced to prevent,
    arrived at from the other direction.

    ⚑ COST IS DERIVED, NEVER DECLARED.  A hand-assigned effort number is a guess
    wearing a measurement's clothes, and it goes stale the moment the work moves.
    This asks the WITNESS instead: a failing check already enumerates what is
    wrong, and the number of DISTINCT items it names is the honest proxy for how
    many things must change.

    ⚑ AND DISTINCT IS NOT THE FAILURE COUNT.  @ROLES reports SIX collisions — one
    per variant — that reduce to ONE fix: make `accent` differ from `phosphor` in
    the solver. @BUILD reports THREE, in three different files, each its own
    change. Counting failures would have ranked @ROLES as the larger job; counting
    distinct kinds gets it right.

    Returns None when the witness names nothing enumerable — grade UNAVAILABLE,
    not zero, so the caller falls back rather than treating it as free.
    """
    script, _label = ENTRY[None]
    path = os.path.join(engine, "paperkit", script)
    r = subprocess.run([sys.executable, path, proj],
                       cwd=os.path.join(engine, "paperkit"),
                       capture_output=True, text=True)
    text = (r.stdout or "") + (r.stderr or "")
    line = next((l for l in text.splitlines()
                 if "FAILED" in l and f"[@{key}]" in l), None)
    if line is None:
        return None
    check = line.split(":", 2)[-1].strip()
    # Re-run the witness alone and count the DISTINCT items it names. The witness
    # is the authority on its own failure; this reads its report, never re-derives
    # the finding.
    parts = check.split(":", 1)
    if parts[0] == "tool":
        argv_ = parts[1].split()
        cmd = [sys.executable, os.path.join(ROOT, "scripts", argv_[0])] + argv_[1:]
    elif parts[0] == "concept":
        cmd = [sys.executable, os.path.join(ROOT, "catalog", "library", "concepts.py"),
               parts[1].strip()]
    else:
        return None
    w = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    out = (w.stdout or "") + (w.stderr or "")
    # ⚑ THE WITNESS DECLARES ITS OWN COST; THIS DOES NOT INFER IT.  The first
    # version scraped the failure prose for quoted findings and counted those —
    # and matched the APOSTROPHE in "another's colour", reporting @ROLES as 2
    # distinct fixes when it is 1. Inferring a number from someone else's
    # sentence is the same error as guessing a tool's output format: the witness
    # knows what it found, so it should say, in a form nobody has to parse.
    #
    #     fixes: <n>          — n distinct things must change
    #
    # A witness that says nothing returns None (grade UNAVAILABLE), and the
    # fallback below counts indented item lines, which is a SHAPE rather than a
    # guess at meaning.
    m = re.search(r"^\s*fixes:\s*(\d+)\s*$", out, re.M)
    if m:
        return int(m.group(1))
    items = [l.strip() for l in out.splitlines() if l.startswith("    ") and l.strip()]
    if items:
        return len(items)
    return 1 if w.returncode else None


def order(open_keys, bib, costs=None):
    """Open claims, topologically layered then ranked by unblocking leverage.

    ⚑ AN ORDER I ASSERT IS A GUESS; AN ORDER THE DAG COMPUTES IS A FACT ABOUT THE
    DAG.  Lifted from substrate's worklist_gate.order(), whose docstring records
    the failure this prevents: a worklist ordered by what the author happened to
    have open — sunk-cost ordering — while cheap high-leverage items sat untouched.

    Two keys, in precedence:
      1. TOPOLOGICAL LAYER — a claim cannot precede what it `rests-on`. Grounding
         is the only hard constraint.
      2. LEVERAGE within a layer — how many OPEN claims transitively rest on this
         one. Closed dependents are not counted, so discharging a claim collapses
         the cone it was holding open: the ordering updates itself rather than
         aging."""
    got = _edges(bib)
    if got is None:
        return None
    edges, enables = got
    openk = set(open_keys)

    depth, seen = {}, set()

    def layer(k):
        if k in depth:
            return depth[k]
        if k in seen:                      # a cycle is a fact to report, not to crash on
            return 0
        seen.add(k)
        d = 0
        for p in edges.get(k, ()):
            d = max(d, layer(p) + 1)
        depth[k] = d
        return d

    for k in edges:
        layer(k)

    # transitive OPEN dependents = leverage.  BOTH relations contribute here:
    # grounding (what rests on this) and sequencing (what this unblocks).
    dependents = {k: set() for k in edges}
    for k, parents in edges.items():
        for p in parents:
            dependents.setdefault(p, set()).add(k)
    for k, targets in enables.items():
        for t in targets:
            dependents.setdefault(k, set()).add(t)

    def cone(k, acc=None):
        acc = set() if acc is None else acc
        for d in dependents.get(k, ()):
            if d not in acc:
                acc.add(d)
                cone(d, acc)
        return acc

    rows = []
    for k in sorted(openk):
        lev = len(cone(k) & openk)
        c = costs.get(k) if costs else None
        # ⚑ THREE KEYS, IN PRECEDENCE, AND THE ORDER OF THE KEYS IS THE ARGUMENT.
        #   1. LAYER — grounding. A claim cannot precede what it rests-on. Hard.
        #   2. LEVERAGE — how many OPEN claims this unblocks. What to do first
        #      among things nothing is waiting on.
        #   3. COST — how many distinct things must change, derived from the
        #      witness. A TIEBREAK, never a promotion: cheap must not outrank
        #      grounding, or the ordering would tell you to do leaves first and
        #      leave the thing everything waits on until last.
        # Unknown cost sorts LAST within its tier, not first: an unmeasured item
        # is not a free one.
        rows.append((depth.get(k, 0), -lev,
                     c if c is not None else 1 << 30, k, lev, c))
    rows.sort()
    return [(k, d, lev, c) for d, _n, _c, k, lev, c in rows]


def locate():
    """(engine_dir, None) or (None, reason) — never a silent skip."""
    tried = []
    for cand in CANDIDATES:
        if not cand:
            continue
        tried.append(cand)
        if os.path.isfile(os.path.join(cand, "paperkit", "gate.py")):
            return cand, None
    return None, ("paperkit not found (looked for paperkit/gate.py in: "
                  + ", ".join(tried or ["<nothing: PAPERKIT unset>"])
                  + "). Set PAPERKIT=/path/to/paperkit.")


def _reexec_under_uv():
    """Re-run this script inside the project venv, if there is one and we're outside it."""
    if os.environ.get("_WORKLIST_IN_UV") or os.environ.get("VIRTUAL_ENV"):
        return None
    if not os.path.isdir(os.path.join(ROOT, ".venv")):
        return None
    env = dict(os.environ, _WORKLIST_IN_UV="1")
    return subprocess.run(["uv", "run", "--no-sync", "python3",
                           os.path.abspath(__file__)] + sys.argv[1:],
                          cwd=ROOT, env=env).returncode


SCHEMES_ACTION = os.path.join(ROOT, "schemes_artifact.py")


def _materialise_schemes():
    """{PAPERKIT_BUILT_ARTIFACTS: ...} declaring `schemes=<snapshot>`, or None (REFUSED,
    reason printed). A snapshot this run cannot take is a refusal, never a silent
    fall-back to per-check reads of the mutable tree."""
    r = subprocess.run([sys.executable, SCHEMES_ACTION, "--materialise"],
                       cwd=ROOT, capture_output=True, text=True)
    fields = (r.stdout or "").split()
    if r.returncode != 0 or len(fields) != 2:
        print(f"worklist_gate: REFUSED — the schemes artifact could not be materialised: "
              f"{(r.stderr or r.stdout).strip()}", file=sys.stderr)
        return None
    digest, path = fields
    pairs = [p for p in os.environ.get("PAPERKIT_BUILT_ARTIFACTS", "").split()
             if p.partition("=")[0] != "schemes"] + [f"schemes={path}"]
    print(f"worklist_gate: schemes artifact {digest[:16]}… declared to every check",
          file=sys.stderr)
    return {"PAPERKIT_BUILT_ARTIFACTS": " ".join(pairs)}


_FAILED = re.compile(r"check FAILED for \[@([^\]]+)\]:\s*(\S+):(.+?)\s*$", re.M)


def _replay(proj, output):
    """Re-run each check the gate reported FAILED, and print its account.

    ⚑ A VERDICT THAT IS AN EXIT CODE WITH NO ACCOUNT IS A DIAGNOSIS NOBODY CAN
    MAKE. luthen-observability measured the cost directly: a failing slice's
    entire report went to /dev/null and ONE failure bought four wrong diagnoses,
    because the only datum was a number. This repo paid it twice on 2026-09-22 —
    @MARQUEE-LIVE denied then admitted on an unchanged tree, and eleven palette
    checks failed then passed — and both re-runs were done BY HAND, which is the
    judgement-in-the-turn this tree exists to stop.

    ⚑ AND THE REPLAY'S OTHER VERDICT IS THE USEFUL ONE. A check that PASSES on
    replay is not a check that was fine: it is a FLAKE, and saying so names a
    defect that "re-run it and it went green" otherwise buries. A reproducible
    failure prints its output; a non-reproducible one is reported as such,
    against the same tree, in the same run.

    ⚑ THE COMMAND TEMPLATE IS READ FROM paper.toml, NOT RESTATED. The project
    declares `[checks.<type>] cmd` with {target}; copying those templates here
    would make this a second reader of a declaration that already has one — the
    defect s142 collapsed one level down."""
    keys = _FAILED.findall(output)
    if not keys:
        return
    toml_path = os.path.join(proj, "paper.toml")
    try:
        import tomllib
        decl = tomllib.load(open(toml_path, "rb")).get("checks", {})
    except (OSError, ValueError, ImportError) as e:
        print(f"\n  replay: WITHHELD — cannot read {toml_path}'s check templates ({e})",
              file=sys.stderr)
        return
    print(f"\n── replay: {len(keys)} failing check(s), re-run for their account ──",
          file=sys.stderr)
    flaky, real = [], []
    for key, kind, target in keys:
        tmpl = decl.get(kind, {}).get("cmd")
        if not tmpl:
            print(f"  @{key}: WITHHELD — paper.toml declares no `{kind}` check type",
                  file=sys.stderr)
            continue
        cmd = tmpl.replace("{target}", target.strip())
        # ⚑ REPLAY UNDER THE GATE'S OWN LIMITS (W68, 2026-09-25). This ran uncapped
        # in our env, while paperkit runs every check under RLIMIT_CPU and its
        # clean_env. @RELATIONS-SEES burned 68 s of CPU against the 60 s cap: SIGXCPU
        # in every gate run, a pass here, "FLAKE" three commits running — a
        # deterministic failure mislabelled by the one tool meant to name it. The
        # cap, the preexec and the env are paperkit's, imported, never restated.
        try:
            from paperkit import resolver as PKR
        except ImportError:
            print(f"  @{key}: WITHHELD — paperkit is not importable under {sys.executable}; "
                  f"the replay cannot apply the gate's limits, so it does not run "
                  f"(uv sync --extra tooling)", file=sys.stderr)
            continue
        cpu = int(os.environ.get("PAPERKIT_CHECK_CPU", PKR.CHECK_CPU))
        r = subprocess.run(cmd, shell=True, cwd=proj, capture_output=True, text=True,
                           env=PKR.clean_env(), start_new_session=True,
                           preexec_fn=PKR._cpu_rlimit(cpu))
        tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        if r.returncode in (-24, -9):          # SIGXCPU at the soft cap, SIGKILL at the hard
            tail.insert(0, f"FAIL: killed by signal {-r.returncode} — exceeded the gate's "
                           f"{cpu} s CPU cap (RLIMIT_CPU); a cost, not a flake")
        if r.returncode == 0:
            flaky.append(key)
            print(f"  @{key}: ⚑ PASSED ON REPLAY (exit 0) — the gate's failure was "
                  f"NOT reproducible on an unchanged tree. That is a FLAKE, which is "
                  f"a defect in the check or its inputs, not an absence of one.",
                  file=sys.stderr)
        else:
            real.append(key)
            print(f"  @{key}: REPRODUCED (exit {r.returncode})", file=sys.stderr)
        # ⚑ THE VERDICT LINES FIRST, THEN THE TAIL — because a bare tail CUT THE
        # FINDING. Measured 2026-09-22, the first run of this replay: @CURRENCY
        # reproduced and the printed account was six WITHHELD rows, with the DENY
        # that caused the exit sitting just above the window. An account that
        # omits the finding is the defect this replay was built to cure, reproduced
        # inside the cure.
        verdicts = [l for l in tail if any(w in l for w in ("DENY", "REFUSED", "FAIL",
                                                            "Traceback", "Error"))]
        shown = verdicts[:6] or []
        rest = [l for l in tail[-6:] if l not in shown]
        for line in shown + rest:
            print(f"      {line}", file=sys.stderr)
        if len(tail) > len(shown) + len(rest):
            print(f"      … {len(tail) - len(shown) - len(rest)} more line(s)",
                  file=sys.stderr)
    print(f"  replay: {len(real)} reproduced, {len(flaky)} flaky of {len(keys)} "
          f"reported failure(s)", file=sys.stderr)


def main(argv):
    mode = None
    only = None
    args = argv[1:]
    if "--selftest" in args:
        return _selftest()
    summary = "--summary" in args
    want_next = "--next" in args
    args = [a for a in args if a not in ("--summary", "--next")]
    if want_next:
        summary = True
    if "--only" in args:
        i = args.index("--only")
        if i + 1 >= len(args) or args[i + 1] not in PROJECTS:
            print(f"worklist_gate: --only needs one of: {', '.join(PROJECTS)}",
                  file=sys.stderr)
            return 2
        only = args[i + 1]
        args = args[:i] + args[i + 2:]
    if "--sandbox" in args:
        # ⚑ Δ's SANDBOX, BUILT BY Δ's OWN COPY (R5, 2026-09-25). paperkit deletes its
        # sandbox unconditionally (no keep knob — paperkit W40), so a check that is
        # `broken` only there could not be looked at. This builds the same tree with
        # paperkit.layout._copy_sandbox — the function Δ calls, not a re-derivation of
        # its skip list — so the check can be re-run on it and its population measured.
        i = args.index("--sandbox")
        if i + 1 >= len(args):
            print("worklist_gate: --sandbox needs a destination directory", file=sys.stderr)
            return 2
        dest = os.path.abspath(args[i + 1])
        if os.path.exists(dest) and os.listdir(dest):
            print(f"worklist_gate: REFUSED — {dest} is not empty", file=sys.stderr)
            return 2
        try:
            from paperkit import layout as PKL
        except ImportError:
            print("worklist_gate: --sandbox needs paperkit importable (uv sync --extra tooling)",
                  file=sys.stderr)
            return 3
        from pathlib import Path
        PKL._copy_sandbox(Path(ROOT), Path(dest))
        # population: the Δ-shaped COPY just written to `dest` — outside git by construction
        n = sum(len(fs) for _d, _ds, fs in os.walk(dest))
        print(f"worklist_gate: Δ-shaped sandbox of {ROOT} at {dest} ({n} files; "
              f"skipped {sorted(PKL.SKIP_DIRS)} + *.pyc, exactly as Δ does)")
        return 0
    for a in args:
        if a == "--where":
            eng, why = locate()
            print(f"engine:  {eng or '(NOT FOUND) ' + why}")
            for name, path in PROJECTS.items():
                print(f"project: {name:9} {path}"
                      f"{'' if os.path.isdir(path) else '  (ABSENT)'}")
            print(f"venv:    {os.path.join(ROOT, '.venv')}"
                  f"{'' if os.path.isdir(os.path.join(ROOT, '.venv')) else ' (absent)'}")
            return 0
        if a in ENTRY:
            mode = a
        else:
            print(f"worklist_gate: unknown flag {a!r} (known: --project, "
                  f"--discriminate, --summary, --next, --where, --selftest, "
                  f"--only <name>)",
                  file=sys.stderr)
            return 2

    rc = _reexec_under_uv()
    if rc is not None:
        return rc

    engine, why = locate()
    if engine is None:
        print(f"worklist_gate: REFUSED — {why}", file=sys.stderr)
        return 2

    script, label = ENTRY[mode]
    path = os.path.join(engine, "paperkit", script)
    if not os.path.isfile(path):
        print(f"worklist_gate: REFUSED — the engine has no {script} "
              f"(looked in {os.path.dirname(path)})", file=sys.stderr)
        return 2

    # ⚑ THE `schemes` ARTIFACT IS MATERIALISED ONCE, BEFORE ANY CHECK RUNS (W75), and
    # handed to every check as a DECLARED INPUT through paperkit's own `builds`
    # variable. ~20 checks read the palette; reading the tracked EL-*.colors by path
    # let two checks in one run judge two palettes if the tree moved between them.
    # Materialised as its own PROCESS (the action boundary), not an import.
    snap = _materialise_schemes()
    if snap is None:
        return 2
    os.environ.update(snap)

    targets = {only: PROJECTS[only]} if only else PROJECTS
    worst = 0
    for name, proj in targets.items():
        if not os.path.isdir(proj):
            print(f"worklist_gate: REFUSED — no project at {proj}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        if len(targets) > 1 and not summary:
            print(f"── {name} ──")
        # The engine imports its own siblings by bare name, so it runs from its dir.
        # ⚑ ALWAYS CAPTURED, so a FAILURE CAN BE REPLAYED (see _replay). Before
        # this, a red gate printed "check FAILED for [@X]: tool:check_x.py" and
        # nothing else — a verdict that is an exit code with no account. Measured
        # twice on 2026-09-22: @MARQUEE-LIVE denied then admitted, and eleven
        # palette checks failed then passed, both on an unchanged tree, and both
        # times the re-run was done BY HAND because the tool could not do it.
        run = subprocess.run([sys.executable, path, proj],
                             cwd=os.path.join(engine, "paperkit"),
                             capture_output=True, text=True)
        if not summary:
            sys.stdout.write(run.stdout or "")
            sys.stderr.write(run.stderr or "")
        if run.returncode != 0 and not summary:
            _replay(proj, (run.stdout or "") + (run.stderr or ""))
        if summary:
            lines = (run.stdout or "").splitlines() + (run.stderr or "").splitlines()
            verdict = [l.strip() for l in lines
                       if any(v in l for v in _VERDICT)]
            failed = [l.strip() for l in verdict if "FAILED" in l]
            state = "PASS" if run.returncode == 0 else "FAIL"
            counted = next((l for l in verdict if "cited/placed/grounded" in l), "")
            print(f"{name:9} {state}  {counted.split(': ', 1)[-1] if counted else ''}"
                  .rstrip())
            open_keys = []
            for f in failed:
                tail = f.split("for ", 1)[-1]
                key = tail.split("]")[0].lstrip("[@").strip()
                open_keys.append(key)
                if not want_next:
                    print(f"          open: {tail}")
            if want_next and open_keys:
                costs = {k: cost(k, proj, engine) for k in open_keys}
                ranked = order(open_keys, os.path.join(proj, "warrants.bib"), costs)
                if ranked is None:
                    print("          (cannot rank: bibstruct unavailable)")
                    for k in open_keys:
                        print(f"          open: @{k}")
                else:
                    for k, d, lev, c in ranked:
                        blocks = f"unblocks {lev}" if lev else "unblocks nothing yet"
                        eff = f", {c} to change" if c is not None else ", cost unknown"
                        print(f"          @{k}  layer {d}, {blocks}{eff}")
        worst = max(worst, exit_of(name, run.returncode))
    return worst


def exit_of(name, rc):
    """The gate's exit for an engine returncode — a SIGNAL DEATH IS NOT A PASS.

    ⚑ (2026-09-25) subprocess reports a signal as a NEGATIVE returncode, and
    `max(worst, -24)` is 0 — so an engine killed by SIGXCPU mid-run (measured:
    --discriminate under a prlimit, dead at 84 of 86, no summary printed) exited
    this gate 0. A negative rc is named and becomes the shell's 128+N."""
    if rc >= 0:
        return rc
    import signal as _signal
    try:
        sig = _signal.Signals(-rc).name
    except ValueError:
        sig = f"signal {-rc}"
    print(f"worklist_gate: {name}: the engine was KILLED by {sig} before it "
          f"reported — nothing it printed is a verdict", file=sys.stderr)
    return 128 - rc


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # The refusal path is the point: an absent engine must REFUSE, not pass.
    saved = os.environ.get("PAPERKIT")
    try:
        os.environ["PAPERKIT"] = "/nonexistent/paperkit"
        global CANDIDATES
        keep = CANDIDATES
        CANDIDATES = ("/nonexistent/paperkit",)
        eng, why = locate()
        check("absent engine returns no path", eng, None)
        check("absent engine gives a reason", bool(why), True)
        # ⚑ locate() returning None is not the refusal; main() is. Drive it, so
        # "an absent engine REFUSES with exit 2" is tested rather than read.
        import contextlib
        import io
        saved_uv = os.environ.get("_WORKLIST_IN_UV")
        os.environ["_WORKLIST_IN_UV"] = "1"
        err = io.StringIO()
        try:
            with contextlib.redirect_stderr(err):
                rc = main(["worklist_gate.py"])
        finally:
            if saved_uv is None:
                os.environ.pop("_WORKLIST_IN_UV", None)
            else:
                os.environ["_WORKLIST_IN_UV"] = saved_uv
        check("absent engine: main() exits 2", rc, 2)
        check("absent engine: main() says REFUSED", "REFUSED" in err.getvalue(), True)
        CANDIDATES = keep
    finally:
        if saved is None:
            os.environ.pop("PAPERKIT", None)
        else:
            os.environ["PAPERKIT"] = saved

    eng, why = locate()
    check("engine is locatable here", eng is not None, True)
    # ⚑ BOTH projects must exist, or the default gate silently covers less than
    # it claims — the failure this tool exists to prevent, one level up.
    missing = [n for n, p in PROJECTS.items() if not os.path.isdir(p)]
    check(f"every project dir exists ({missing})", missing, [])
    check("more than one project is wired", len(PROJECTS) > 1, True)

    # ⚑ THE RANKING'S KEY ORDER IS THE ARGUMENT, so it is asserted rather than
    # left to a reading of the sort tuple. Grounding outranks leverage outranks
    # cost: a cheap leaf must never be promoted above the thing everything waits
    # on, which is what ordering by cost alone would do.
    fake_edges = {"deep": ["mid"], "mid": ["base"], "base": [], "leaf": []}

    def _fake(_bib, _e=fake_edges):
        return _e, {}

    real, globals()["_edges"] = _edges, _fake
    try:
        # same layer, differing cost -> cheaper first
        r = order(["base", "leaf"], "x", {"base": 9, "leaf": 1})
        check("within a layer, cheaper sorts first", [k for k, *_ in r],
              ["leaf", "base"])
        # deeper layer never outranks a shallower one, however cheap
        r = order(["base", "deep"], "x", {"base": 9, "deep": 1})
        check("cost never beats grounding", [k for k, *_ in r], ["base", "deep"])
        # unknown cost sorts last in its tier, not first
        r = order(["base", "leaf"], "x", {"base": 2, "leaf": None})
        check("unknown cost is not free", [k for k, *_ in r], ["base", "leaf"])
    finally:
        globals()["_edges"] = real

    # ⚑ BOTH REPLAY VERDICTS ARE DRIVEN, because the FLAKE arm is the one that
    # matters and the one that never fires on a healthy tree. A replay that can
    # only ever print REPRODUCED has never been shown to differ from its
    # found-something, which is not a measurement.
    proj = PROJECTS["worklist"]
    check("the project declares check templates",
          os.path.isfile(os.path.join(proj, "paper.toml")), True)
    line = "paperkit-gate: check FAILED for [@RESIDUE]: tool:check_symbol.py --bucket RESIDUE"
    check("a failure line parses to (key, kind, target)", _FAILED.findall(line),
          [("RESIDUE", "tool", "check_symbol.py --bucket RESIDUE")])
    check("a passing run parses to nothing", _FAILED.findall("paperkit-gate: PASS"), [])

    import contextlib
    import io

    def replay_of(text):
        buf = io.StringIO()
        with contextlib.redirect_stderr(buf):
            _replay(proj, text)
        return buf.getvalue()

    # the gate is TOLD a passing check failed; the replay must NAME the
    # disagreement rather than swallow it as "fine now"
    try:
        import paperkit.resolver  # noqa: F401  the replay runs under ITS limits
        have_pk = True
    except ImportError:
        have_pk = False
    if not have_pk:
        # a fact about the interpreter, not the replay: counted and printed, not failed
        print(f"  SKIP replay arms (4) — paperkit not importable under {sys.executable}")
        out = replay_of("check FAILED for [@X]: tool:check_hooks.py --list")
        check("...and without it the replay WITHHOLDS rather than crashing", "WITHHELD" in out, True)
    else:
        out = replay_of("check FAILED for [@X]: tool:check_hooks.py --list")
        check("a check that passes on replay is called a FLAKE", "FLAKE" in out, True)
        check("...and is counted as flaky", "1 flaky" in out, True)
        out = replay_of("check FAILED for [@X]: tool:check_symbol.py --bucket RESIDUE")
        check("a check that fails on replay is REPRODUCED", "REPRODUCED" in out, True)
        check("...and is counted as reproduced", "1 reproduced" in out, True)
    out = replay_of("check FAILED for [@X]: nosuchtype:whatever")
    check("an undeclared check type is WITHHELD", "WITHHELD" in out, True)

    # ⚑ THE SCHEMES ARTIFACT (W75) IS DRIVEN, not read: the gate's materialise arm
    # yields a declaration whose `schemes=` directory is named by its own content.
    decl = _materialise_schemes()
    check("the gate declares a schemes snapshot", bool(decl), True)
    if decl:
        # a CHECK handed that declaration verifies it (digest == name) and reads IT
        r = subprocess.run([sys.executable, SCHEMES_ACTION, "--where"],
                           env=dict(os.environ, **decl), capture_output=True, text=True)
        check("...which a check reads as DECLARED, digest verified",
              (r.returncode, "declared" in r.stdout), (0, True))

    # ⚑ A KILLED ENGINE MUST NOT EXIT 0: SIGXCPU (-24) and SIGKILL (-9) fail as 128+N,
    # and a real exit code passes through untouched
    check("an engine killed by SIGXCPU fails the gate (152), never 0", exit_of("selftest", -24), 152)
    check("an engine killed by SIGKILL fails the gate (137)", exit_of("selftest", -9), 137)
    check("a real exit code is passed through", (exit_of("selftest", 0), exit_of("selftest", 1)), (0, 1))
    # and a REAL killed child reaches it: python dies of SIGKILL, rc -9
    r = subprocess.run([sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGKILL)"])
    check("a child really killed by a signal is seen as one", exit_of("selftest", r.returncode), 137)

    print("worklist_gate selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
