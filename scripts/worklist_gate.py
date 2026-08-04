#!/usr/bin/env python3
"""worklist_gate.py — run the paperkit engine over `catalog/worklist/`.

⚑ WHY THIS EXISTS.  Paperkit is an ENGINE you point at a project directory, not
something to copy in.  But "point at" is otherwise a hand-assembled shell line —
`python3 ~/github/paperkit/paperkit/gate.py catalog/worklist` — carrying three
pieces of knowledge (where the engine lives, which entry point to call, which
directory is the project) in a string a human retypes.  A judgement that lives in
a retyped command evaporates when the turn ends.  This module owns all three.

    worklist_gate.py                 # GATE: are all cited claims discharged?
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
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# name -> project dir.  Order is the order they run in.
PROJECTS = {
    "worklist": os.path.join(ROOT, "catalog", "worklist"),
    "cotype":   os.path.join(ROOT, "catalog", "cotype"),
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


def main(argv):
    mode = None
    only = None
    args = argv[1:]
    if "--only" in args:
        i = args.index("--only")
        if i + 1 >= len(args) or args[i + 1] not in PROJECTS:
            print(f"worklist_gate: --only needs one of: {', '.join(PROJECTS)}",
                  file=sys.stderr)
            return 2
        only = args[i + 1]
        args = args[:i] + args[i + 2:]
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
            print(f"worklist_gate: unknown flag {a!r} "
                  f"(known: --project, --discriminate, --where, --only <name>)",
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

    targets = {only: PROJECTS[only]} if only else PROJECTS
    worst = 0
    for name, proj in targets.items():
        if not os.path.isdir(proj):
            print(f"worklist_gate: REFUSED — no project at {proj}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        if len(targets) > 1:
            print(f"── {name} ──")
        # The engine imports its own siblings by bare name, so it runs from its dir.
        rc = subprocess.run([sys.executable, path, proj],
                            cwd=os.path.join(engine, "paperkit")).returncode
        worst = max(worst, rc)
    return worst


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
    print("worklist_gate selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
