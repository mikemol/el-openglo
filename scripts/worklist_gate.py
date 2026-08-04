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

# ⚑ `--summary` EXISTS BECAUSE ITS ABSENCE WAS BEING PAPERED OVER WITH A PIPE.
# The verdict lines were repeatedly extracted with `… | grep -E 'FAILED|PASS'`,
# which is the judgement living in the turn instead of in a program — the exact
# shape the no-chaining hook refuses. The honest response to "no mode answers
# this" is to add the mode, so: one line per project, plus the open claims.
_VERDICT = ("paperkit-gate: check FAILED", "paperkit-gate: PASS",
            "paperkit-gate: FAIL", "cited/placed/grounded", "coverage complete")

# substrate's structural reader for a warrants .bib — the claim-DAG, not its text.
BIBSTRUCT = os.path.expanduser("~/github/substrate/scratch/bibstruct.py")


def _edges(bib):
    """{key: [keys it rests on]} — read with substrate's reader, not a regex.

    ⚑ ASK THE TOOL THAT OWNS THE FORMAT.  paperkit's own bib.py opens by recording
    that it consolidated THREE parsers which had each re-derived the format; adding
    a fourth here to save one subprocess is how that happens again."""
    r = subprocess.run([sys.executable, BIBSTRUCT, "--edges", bib],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return None
    # The reader emits "  <relation>  CHILD  -> PARENT", then a summary line.
    # ⚑ THIS PARSER WAS WRONG ONCE, BY GUESSING THE SHAPE INSTEAD OF READING IT:
    # it took field 0 as the key and returned two "claims" named `edges` and
    # `rests-on`. A tool's output format is something to look at, not infer.
    out, enables = {}, {}
    for line in r.stdout.splitlines():
        if "->" not in line:
            continue
        lhs, _, target = line.partition("->")
        parts = lhs.split()
        if len(parts) < 2:
            continue
        rel, src, target = parts[0], parts[1], target.strip()
        if rel == "rests-on":
            out.setdefault(src, []).append(target)
            out.setdefault(target, [])
        elif rel == "enables":
            # ⚑ `enables` RAISES LEVERAGE AND NOT LAYER.  It is SEQUENCING — this
            # work is cheaper or safer first — whereas `rests-on` is GROUNDING: a
            # claim cannot be TRUE unless its premises are. Feeding sequencing
            # into the topological layer would assert a premise the source never
            # made, just to obtain a sort order.
            enables.setdefault(src, []).append(target)
            out.setdefault(src, [])
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


def main(argv):
    mode = None
    only = None
    args = argv[1:]
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
                  f"--discriminate, --summary, --next, --where, --only <name>)",
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
        if len(targets) > 1 and not summary:
            print(f"── {name} ──")
        # The engine imports its own siblings by bare name, so it runs from its dir.
        run = subprocess.run([sys.executable, path, proj],
                             cwd=os.path.join(engine, "paperkit"),
                             capture_output=summary, text=True)
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
        worst = max(worst, run.returncode)
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
    print("worklist_gate selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
