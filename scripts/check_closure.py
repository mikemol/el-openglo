#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_closure.py — which tracked files does each gate stage actually READ? (W493, under W458)

⚑ WHY. `//:precommit`'s stages (BUILD.bazel) each declare every tracked file as `data` (the fail-safe
over-approximation, W491), so the census (W488) is vacuous and no stage can be cached. A stage's REAL input
closure is what it opens: the Python modules it imports, the policy and test it hands opa, the templates
and catalogs it reads. Writing that by hand drifts; deriving it from imports misses every data file. So it
is OBSERVED: the stage (gate/stage.sh, the same command the gate runs) is run under strace and the tracked
files it opened are the closure.

    scripts/check_closure.py --observe scripts/check_x.py     # one stage's closure, one path per line
    scripts/check_closure.py --write                          # every selftest stage -> closures.bzl
    scripts/check_closure.py --json                           # the measurement policy/closure.rego decides
    scripts/check_closure.py                                  # the verdict, as opa_gate closure decides it
    scripts/check_closure.py --selftest

`closures.bzl` (repo root, loaded by BUILD.bazel) is `CLOSURES = {"scripts/check_x.py": [files...]}`.

⚑ WEAKNESSES, STATED. (1) OBSERVED IS AN UNDER-APPROXIMATION: a path the selftest does not take (an error
arm, a skipped optional dependency) reads nothing and is not listed. The closure is therefore a CLAIM that
the witness (W494: run the stage with only its closure present, and plant a defect in a listed file) must
test; this file never says a closure is complete. (2) Reads are resolved from the syscall's path; a path
relative to a directory fd, or to a subprocess's own cwd, is resolved against the repo root and dropped
when that is not a tracked file, so a subprocess's relative reads can be missed. (3) Only TRACKED files are
inputs: the venv, the host's tools and untracked caches are the host tier's (W459) and are not listed.
(4) strace needs ptrace: where it is absent the observation is `withheld`, never an empty closure.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

CLOSURES = os.path.join(ROOT, "closures.bzl")
SYSCALLS = "openat,open,execve,stat,newfstatat,statx,access,faccessat,faccessat2,readlink,readlinkat"
_STAT = ("stat", "newfstatat", "statx", "access", "faccessat", "faccessat2")
# `[pid N] ` or `N ` prefix, the syscall name, the first quoted argument, the return value
_LINE = re.compile(
    r'^(?:\[pid\s+\d+\]\s+|\d+\s+)?(\w+)\((?:AT_FDCWD,\s*)?"((?:[^"\\]|\\.)*)".*\)\s+=\s+(-?\d+)'
)


def parse_trace(text, root, tracked, import_only=frozenset(), dirs=None):
    """The tracked repo-relative paths a strace log shows SUCCESSFULLY touched (return value >= 0).

    `import_only` is the set of repo-relative directories whose listing was made by Python's import system and
    by nothing else (see import_only_dirs): such a listing is how `import` finds a module, not an input of the
    stage, so it does not declare the files in the directory.

    `dirs` (W692) is None for the old rule, where a listed directory declares the tracked files directly
    inside it. With a set, a listing that is not import-only of a directory holding tracked files is collected
    into `dirs` (the root is ".") and declares none of its children: the NAMES are structure, kept apart from
    the CONTENT of the files the stage actually opened. A file opened inside a listed directory is still content."""
    seen = set()
    children = {}
    first_under = {}
    for p in sorted(tracked):
        children.setdefault(os.path.dirname(p) or ".", []).append(p)
        d = os.path.dirname(p)
        while True:
            first_under.setdefault(d or ".", p)
            if not d:
                break
            d = os.path.dirname(d)
    for line in text.splitlines():
        m = _LINE.match(line)
        if not m or int(m.group(3)) < 0:
            continue
        path = m.group(2)
        full = path if os.path.isabs(path) else os.path.join(root, path)
        rel = os.path.relpath(os.path.normpath(full), root)
        if rel in tracked:
            seen.add(rel)
        elif "O_DIRECTORY" in line:
            # ⚑ A DIRECTORY LISTING IS AN INPUT: a stage that scans for names (emitters --drift counts the
            # make_*.py the tree holds) reads the NAMES of what is in it. Declare the tracked files directly
            # inside (the names are the input; over-approximate on content), or a closure-only tree
            # silently loses a file the scan would have found (found by the W494 witness, check_discriminates)
            if rel not in import_only:
                if dirs is not None and rel in children:
                    dirs.add(rel)
                else:
                    seen.update(children.get(rel, ()))
        elif m.group(1) in _STAT and rel in first_under:
            # a stat of a directory (os.path.isdir) reads that it EXISTS: one tracked file under it
            # keeps it in a closure-only tree (W494, worklist_gate's "every project dir exists")
            seen.add(first_under[rel])
    return seen


# the gate stages that are not one check's selftest, keyed by their gate/stage.sh kind (W496)
STAGE_KINDS = ("opa-test", "pytestspec", "segment-lattice", "worklist", "readme")


def stage_args(key):
    """gate/stage.sh's arguments for a closure key: a script path is that check's selftest, a name in
    STAGE_KINDS is that stage itself."""
    return ["selftest", key] if key.endswith(".py") else [key]


# ⚑ WHO LISTED THE DIRECTORY? (W666) strace sees a directory read but not WHY. Python's import system lists every
# sys.path directory to find a module (importlib's FileFinder), so a stage that imports one root module opens
# the repo root as a directory, and the rule "a listed directory declares the tracked files inside it" then
# declared EVERY root-level file for 101 of 110 stages. The audit hook below is placed on PYTHONPATH as a
# sitecustomize for the stage under observation: each os.listdir / os.scandir appends `I<TAB>dir` when its
# immediate caller is importlib, else `R<TAB>dir`, to the file named by CLOSURE_LISTINGS.
LISTING_HOOK = """import os
import sys

_LOG = os.environ.get("CLOSURE_LISTINGS")


def _hook(event, args):
    if event not in ("os.listdir", "os.scandir") or not args:
        return
    path = "." if args[0] is None else args[0]
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    via = "I" if "importlib" in sys._getframe(1).f_code.co_filename else "R"
    line = f"{via}\\t{os.path.abspath(os.fsdecode(path))}\\n"
    fd = os.open(_LOG, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
    try:
        os.write(fd, line.encode())
    finally:
        os.close(fd)


if _LOG:
    sys.addaudithook(_hook)
"""


def import_only_dirs(text, root):
    """The repo-relative directories only the import system listed, from the hook's log: a directory any
    other caller also listed stays declared. WEAKNESS: a non-Python tool (git, opa, bash) listing a
    directory the import system also listed is invisible to the hook, so that listing is dropped too."""
    imported, real = set(), set()
    for line in text.splitlines():
        via, _, path = line.partition("\t")
        if path:
            (imported if via == "I" else real).add(os.path.relpath(path, root))
    return imported - real


def observe(script, root=ROOT, dirs=None):
    """(closure, why): the tracked files `gate/stage.sh` opens for the stage `script` names (a check's
    selftest, or one of STAGE_KINDS), or (None, reason). With a set for `dirs` (W692) the directories the
    stage listed are added to it, and the listing no longer declares their children (see parse_trace)."""
    if shutil.which("strace") is None:
        return None, "strace is not installed"
    import git_tracked

    tracked = set(git_tracked.files(root=root))
    with tempfile.TemporaryDirectory() as td:
        log = os.path.join(td, "trace.txt")
        hook = os.path.join(td, "hook")
        listings = os.path.join(td, "listings.txt")
        os.makedirs(hook)
        with open(os.path.join(hook, "sitecustomize.py"), "w", encoding="utf-8") as fh:
            fh.write(LISTING_HOOK)
        env = dict(os.environ, CLOSURE_LISTINGS=listings)
        env["PYTHONPATH"] = os.pathsep.join(
            p for p in (hook, os.environ.get("PYTHONPATH", "")) if p
        )
        r = subprocess.run(
            ["strace", "-f", "-qq", "-e", f"trace={SYSCALLS}", "-o", log]
            + [os.path.join(root, "gate", "stage.sh"), *stage_args(script)],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        if not os.path.isfile(log) or os.path.getsize(log) == 0:
            return (
                None,
                f"strace wrote no trace (exit {r.returncode}): {r.stderr[-200:]}",
            )
        skip = set()
        if os.path.isfile(listings):
            with open(listings, encoding="utf-8", errors="replace") as fh:
                skip = import_only_dirs(fh.read(), root)
        with open(log, encoding="utf-8", errors="replace") as fh:
            closure = parse_trace(fh.read(), root, tracked, skip, dirs)
    closure.add(script if script.endswith(".py") else "gate/stage.sh")
    return sorted(closure), ""


# stages the sufficiency witness cannot judge, each with the reason (withheld WITH it, never a pass). EMPTY
# since the closure-only tree became a git repository under the home cache (W504, 2026-10-11): check_ebuild
# and check_tree_writes were exempt "for want of a repository" and the readme stage's three ebuild claims
# were known failures for the same reason; all of them passed once the tree was one.
WITNESS_EXEMPT: dict = {}


# claims a whole-gate stage is KNOWN to fail in a closure-only tree, each with its reason: the stage is
# then "sufficient except for" them (arm1 `known`: counted and printed, never a pass and never a deny)
# while any OTHER failing claim is an incomplete closure. The reasons are about the HARNESS, not about the
# closure: here, the untracked build outputs a closure of tracked files cannot hold.
WITNESS_KNOWN = {
    "worklist": {
        "CURRENCY": "reads the untracked emitted outputs (screens, wallpapers): a closure of TRACKED files cannot hold them",
    },
}

# files the gate's own machinery reads that no stage's observed closure holds (BUILD analysis, the
# witness and the census read these; they are inputs of the suite, not of a check)
EXTRA_NAMED = (
    "BUILD.bazel",
    "MODULE.bazel",
    "MODULE.bazel.lock",
    "closures.bzl",
    "stages.bzl",
    "gate/stage.sh",
    "gate/staged.sh",
    "gate/census_exempt.tsv",
)

# ⚑ A STAGE THAT READS (NEARLY) EVERY TRACKED FILE IS RECORDED AS "*", NOT AS AN ENUMERATION. check_license,
# check_mark, check_deps, the worklist and readme stages each opened 657-671 of 671 tracked files: a stored
# list of them goes stale the moment ANY commit adds a file, so the closure witness refused the next commit
# for a file that no stage had even been asked to read (measured: gate/staged.sh, 2026-10-11). "*" means the
# stage's closure IS the tracked list, so it follows the tree by construction; a narrow closure still has to
# be re-observed when a file it reads appears (the witness says so, loudly).
WHOLE = "*"
WHOLE_TREE = 0.95

# ⚑ STAGES THAT CLONE THE TRACKED TREE ARE THE WHOLE TREE BY CONSTRUCTION (W504, 2026-10-11, found by the
# witness): check_ebuild archives the index into a clean clone and runs the emitters THERE, so what it reads
# happens at paths inside the clone, which an observation of the real tree cannot attribute to tracked
# files. Its observed closure (226) understated it, and in a closure-only tree the clone lacked
# templates/ ("No module named templates"). What a clone reads is whatever the index holds.
CLONING = ("scripts/check_ebuild.py",)


def compress(closure, tracked):
    """["*"] when `closure` covers at least WHOLE_TREE of the tracked files, else the closure itself."""
    if tracked and len(set(closure) & set(tracked)) >= WHOLE_TREE * len(tracked):
        return [WHOLE]
    return closure


def expand(files, root=ROOT):
    """The tracked list when `files` is the whole-tree marker, else `files` unchanged."""
    if files == [WHOLE]:
        import git_tracked

        return git_tracked.files(root=root)
    return files


def holding(closures, path):
    """(keys, whole): the stage keys whose stored closure lists `path`, and how many closures are the whole-tree
    marker. A whole-tree closure follows the tree by construction, so it is counted and never listed."""
    keys = sorted(k for k, v in closures.items() if v != [WHOLE] and path in v)
    return keys, sum(1 for v in closures.values() if v == [WHOLE])


MAX_VICTIMS = 12


def _victims(script, closure, root):
    """The closure .py files the stage's script imports BY NAME (at most MAX_VICTIMS), where a planted
    defect might reach the verdict. A name in an `import` line is a CANDIDATE, not a proof it runs: the
    import may sit in a branch the selftest never takes, so arm 2 tries them until one reaches the
    verdict (W494). A stage that is not one script (STAGE_KINDS) has no single script to read: none."""
    if not script.endswith(".py"):
        return []
    with open(os.path.join(root, script), encoding="utf-8") as fh:
        text = fh.read()
    out = []
    for f in sorted(closure):
        if not f.endswith(".py") or f == script:
            continue
        mod = os.path.splitext(os.path.basename(f))[0]
        if re.search(rf"^\s*(?:import|from)\s+{re.escape(mod)}\b", text, re.MULTILINE):
            out.append(f)
    return out[:MAX_VICTIMS]


# ⚑ NOT UNDER /tmp OR /var/tmp: check_ebuild stages inside the tree under portage's sandbox with
# SANDBOX_DENY=/tmp:/var/tmp, and DENY covers READS, so a witness tree there cannot read its own venv
# (the same reason gate/staged.sh keeps the staged tree under the home cache).
WITNESS_DIR = os.path.join(os.path.expanduser("~"), ".cache", "el-openglo-witness")


def witness(script, closure, defect_in=None, root=ROOT):
    """(rc, tail): run `gate/stage.sh selftest SCRIPT` in a temp tree holding ONLY its closure
    (plus MODULE.bazel, which locates the root, the venv by symlink and the warm palette cache: the
    host's, declared). Arm 1 (defect_in None): it must pass, or the closure is incomplete and the missing
    file is in the output. Arm 2: a `raise SystemExit(99)` appended to the closure file `defect_in`
    must make it fail, or that file does not reach the verdict on the selftest's path."""
    os.makedirs(WITNESS_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=WITNESS_DIR) as td:
        for rel in set(closure) | {"MODULE.bazel"}:
            dst = os.path.join(td, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(root, rel), dst)
        cache = os.path.join(root, ".palette-cache.json")
        if os.path.isfile(cache):
            shutil.copy2(cache, os.path.join(td, ".palette-cache.json"))
        os.symlink(os.path.join(root, ".venv"), os.path.join(td, ".venv"))
        # the stage under witness must not inherit the request to run the witness (it would recurse)
        env = {
            k: v
            for k, v in os.environ.items()
            if not k.startswith("GIT_") and k != "CLOSURE_WITNESS"
        }
        # ⚑ THE CLOSURE-ONLY TREE IS A REPOSITORY, ITS INDEX EXACTLY THE CLOSURE (W504, 2026-10-11). Without
        # one git_tracked falls back to a directory WALK, whose population races with the sibling checks of
        # the same stage writing bytecode and caches into the tree: @LICENSE failed once and passed on
        # replay inside the witness (0 of 40 under contention in the real tree). The staged tree
        # (gate/staged.sh) is a repository for the same reason; the closure-only tree now is too.
        names = "\0".join(sorted(set(closure) | {"MODULE.bazel"})).encode()
        subprocess.run(["git", "-C", td, "init", "-q"], env=env, check=True)
        subprocess.run(
            [
                "git",
                "-C",
                td,
                "add",
                "-f",
                "--pathspec-from-file=-",
                "--pathspec-file-nul",
            ],
            input=names,
            env=env,
            check=True,
        )
        if defect_in is not None:
            with open(os.path.join(td, defect_in), "a", encoding="utf-8") as fh:
                fh.write("\nraise SystemExit(99)\n")
        env.update(TEST_SRCDIR=os.path.dirname(td), TEST_WORKSPACE=os.path.basename(td))
        r = subprocess.run(
            ["bash", os.path.join(td, "gate", "stage.sh"), *stage_args(script)],
            cwd=td,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    return r.returncode, (r.stderr or r.stdout)[-30000:]


def judge(script, closure):
    """One stage's witness case: {script, arm1, arm2, victim, detail}. arm1 is pass / fail / exempt;
    arm2 is refused (the planted defect reached the verdict) / survived / none (no module to plant in)."""
    if script in WITNESS_EXEMPT:
        return {
            "script": script,
            "arm1": "exempt",
            "arm2": "none",
            "victim": None,
            "detail": WITNESS_EXEMPT[script],
        }
    closure = expand(closure, ROOT)
    rc1, tail1 = witness(script, closure)
    arm1, detail = "pass" if rc1 == 0 else "fail", "" if rc1 == 0 else tail1
    if rc1 != 0 and script in WITNESS_KNOWN:
        # the failing claims, read from the engine's own `check FAILED for [@KEY]` lines: sufficient
        # EXCEPT the named known ones (each with its harness reason), else the closure is incomplete
        keys = set(re.findall(r"check FAILED for \[@([^\]]+)\]", tail1))
        known = WITNESS_KNOWN[script]
        if keys and keys <= set(known):
            arm1 = "known"
            detail = "; ".join(f"@{k}: {known[k]}" for k in sorted(keys))
    case = {
        "script": script,
        "arm1": arm1,
        "arm2": "none",
        "victim": None,
        "detail": detail,
    }
    if arm1 in ("pass", "known"):
        victims = _victims(script, closure, ROOT)
        # none: no module to plant in; refused: a planted defect reached the verdict (victim names it);
        # unproven: every candidate import survived a defect (each may sit on a path the selftest never
        # takes) - NOT CONFIRMED IS NOT FAILED, so it is counted and printed, never denied
        case["arm2"] = "unproven" if victims else "none"
        for v in victims:
            rc2, _tail2 = witness(script, closure, defect_in=v)
            if rc2 != 0:
                case["arm2"] = "refused"
                case["victim"] = v
                break
    return case


def witness_all(scripts, closures, jobs=4):
    """The witness measurement policy/closure_witness.rego decides: judge() per stage, in parallel
    (each runs in its own temp tree, so they cannot interfere)."""
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=jobs) as ex:
        cases = list(ex.map(lambda s: judge(s, closures[s]), scripts))
    return {"cases": cases}


def stage_scripts(root=ROOT):
    """The scripts BUILD.bazel makes a selftest stage of: every tracked check and worklist_gate."""
    import git_tracked

    return [
        p
        for p in git_tracked.files(
            "scripts/check_*.py", "scripts/worklist_gate*.py", root=root
        )
    ]


def stage_keys(root=ROOT):
    """Every closure key: the selftest scripts, then the stages that are not one check's selftest."""
    return stage_scripts(root) + list(STAGE_KINDS)


def render(closures):
    """closures.bzl's text: deterministic, sorted, one file per line."""
    out = [
        "# SPDX-License-Identifier: Apache-2.0",
        "# Copyright (c) 2026 Mike Mol",
        '"""GENERATED by scripts/check_closure.py --write (W493): the tracked files each selftest stage opened',
        "when run under strace. A CLAIM, not a proof of completeness (the witness, W494, tests it). Never edit.",
        '"""',
        "",
        "CLOSURES = {",
    ]
    for script in sorted(closures):
        out.append(f'    "{script}": [')
        out += [f'        "{p}",' for p in closures[script]]
        out.append("    ],")
    out.append("}")
    out += [
        "",
        "# files the suite's own machinery reads that no stage's closure holds (BUILD, the witness, the census)",
    ]
    out += ["EXTRA_NAMED = ["] + [f'    "{p}",' for p in EXTRA_NAMED] + ["]"]
    return "\n".join(out) + "\n"


def write_closures(closures, root=ROOT):
    """Write the closure declaration as the nested tree (closures/ and the root closures.bzl; W662).

    Each policy spec's family comes from its rego METADATA (scripts/spec_families.py), so a spec with no
    family is a ValueError, never filed under the machinery. Returns (changed, stale): the repo paths written,
    and the closures/*.bzl files the declaration no longer names (the caller removes those from git)."""
    import closure_tree
    import spec_families

    population = spec_families.specs(root)
    tags = spec_families.read_tags(population, root)
    family_of = {s: f for s, f in tags.items() if f}
    plan = closure_tree.plan_tree(
        closures, family_of, EXTRA_NAMED, population, by_spec=True
    )
    return closure_tree.write_tree(plan, root)


def load_closures(text, root=ROOT):
    """{script: [files]} from closures.bzl's text, read with ast and never run.

    Two forms: a Starlark dict literal (the flat file, and the fixtures), or the ROOT of the closure tree (it
    `load()`s closures/*.bzl; W662), in which case the tree under `root` is read. A text in neither form is a
    ValueError: an unreadable declaration must never read as an empty one."""
    import ast

    import closure_tree

    tree = ast.parse(text)
    loads = [
        n
        for n in tree.body
        if isinstance(n, ast.Expr)
        and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name)
        and n.value.func.id == "load"
    ]
    if loads:
        return closure_tree.load_tree(root)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "CLOSURES" for t in node.targets
        ):
            return ast.literal_eval(node.value)
    msg = "closures.bzl is neither a CLOSURES literal nor the root of the closure tree"
    raise ValueError(msg)


def measure(
    closures=None, scripts=None, tracked=None, with_witness=False, with_tree=False
):
    """The MEASUREMENT policy/closure.rego decides: per stage script whether it has a closure, and
    which listed files are not tracked; keys no stage uses are stale. `with_witness` adds the
    sufficiency witness's cases (minutes of work: only the gate stage that asks for it pays, and an
    EXPLICIT argument, not the environment, so a fixture call in a selftest cannot start it).
    `with_tree` adds the closure tree's own shape (dangling loads, orphan nodes: L6, L7), read from
    the disk, so a fixture call does not ask for it either."""
    import git_tracked

    if closures is None:
        closures = {}
        if os.path.isfile(CLOSURES):
            with open(CLOSURES, encoding="utf-8") as fh:
                closures = load_closures(fh.read())
    if scripts is None:
        scripts = stage_keys()
    if tracked is None:
        tracked = set(git_tracked.files())
    cases = []
    for s in scripts:
        files = closures.get(s)
        if files == [WHOLE]:
            # the whole tracked list, by definition: it lists its own script and nothing untracked
            files = sorted(tracked)
        cases.append(
            {
                "script": s,
                "has_closure": files is not None,
                "files": 0 if files is None else len(files),
                "self_listed": files is not None
                and (s if s.endswith(".py") else "gate/stage.sh") in files,
                "untracked": sorted(f for f in (files or []) if f not in tracked),
            }
        )
    result = {"cases": cases, "stale": sorted(set(closures) - set(scripts))}
    if with_tree:
        import closure_tree

        result["tree"] = closure_tree.shape()
    if with_witness:
        result["witness"] = witness_all(
            [s for s in scripts if s in closures], closures
        )["cases"]
    return result


def main(argv):
    args = argv[1:]
    if args[:1] == ["--observe"] and len(args) == 2:
        closure, why = observe(args[1])
        if closure is None:
            print(f"check_closure: WITHHELD — {why}", file=sys.stderr)
            return 3
        print("\n".join(closure))
        return 0
    if args[:1] == ["--write"]:
        # `--write` regenerates every closure; `--write SCRIPT...` re-observes only those and keeps the
        # rest (a NEW check needs its closure the commit it is added; the whole sweep takes ~10 min)
        stages = stage_keys()
        unknown = [s for s in args[1:] if s not in stages]
        if unknown:
            print(f"check_closure: not a stage: {unknown}", file=sys.stderr)
            return 2
        closures = {}
        if args[1:] and os.path.isfile(CLOSURES):
            with open(CLOSURES, encoding="utf-8") as fh:
                closures = {
                    k: v for k, v in load_closures(fh.read()).items() if k in stages
                }
        import git_tracked

        every = git_tracked.files()
        for s in args[1:] or stages:
            closure, why = observe(s)
            if closure is None:
                print(f"check_closure: WITHHELD {s} — {why}", file=sys.stderr)
                return 3
            closures[s] = [WHOLE] if s in CLONING else compress(closure, every)
            note = " (whole tree: recorded as *)" if closures[s] == [WHOLE] else ""
            print(f"check_closure: {s}: {len(closure)} file(s){note}")
        changed, stale = write_closures(closures)
        for path in stale:
            print(
                f"check_closure: STALE {path}: no longer named; git rm it",
                file=sys.stderr,
            )
        print(
            f"check_closure: wrote {len(closures)} closure(s); {len(changed)} file(s) changed in the tree"
        )
        return 1 if stale else 0
    if args[:1] in (["--witness"], ["--witness-json"]):
        with open(CLOSURES, encoding="utf-8") as fh:
            closures = load_closures(fh.read())
        scripts = args[1:] or sorted(closures)
        unknown = [s for s in scripts if s not in closures]
        if unknown:
            print(f"check_closure: no closure for {unknown}", file=sys.stderr)
            return 2
        result = witness_all(scripts, closures)
        if args[0] == "--witness-json":
            import json

            print(json.dumps(result, indent=1))
            return 0
        bad = 0
        for c in result["cases"]:
            note = f" ({c['detail'][:90]})" if c["detail"] else ""
            print(f"  {c['script']}: arm1 {c['arm1']}, arm2 {c['arm2']}{note}")
            bad += c["arm1"] == "fail"
        counts = {}
        for c in result["cases"]:
            counts[c["arm2"]] = counts.get(c["arm2"], 0) + 1
        print(
            f"check_closure: {bad} of {len(result['cases'])} stage(s) failed arm 1 (closure sufficient); "
            f"arm 2 (a planted defect reaches the verdict): {counts}"
        )
        return 1 if bad else 0
    if args == ["--compress"]:
        # re-record every closure that covers the whole tracked list as the marker, WITHOUT re-observing:
        # the fix for a closures.bzl written before the marker existed
        import git_tracked

        every = git_tracked.files()
        with open(CLOSURES, encoding="utf-8") as fh:
            closures = {
                k: [WHOLE]
                if k in CLONING
                else compress(expand(v) if v == [WHOLE] else v, every)
                for k, v in load_closures(fh.read()).items()
            }
        write_closures(closures)
        whole = sorted(k for k, v in closures.items() if v == [WHOLE])
        print(
            f"check_closure: {len(whole)} of {len(closures)} closure(s) are the whole tree: {whole}"
        )
        return 0
    if args[:1] == ["--holding"] and len(args) == 2:
        with open(CLOSURES, encoding="utf-8") as fh:
            closures = load_closures(fh.read())
        if not closures:
            print(
                "check_closure: no closure was read; the search is broken",
                file=sys.stderr,
            )
            return 2
        keys, whole = holding(closures, args[1])
        print("\n".join(keys))
        print(
            f"check_closure: {len(keys)} of {len(closures)} closure(s) hold {args[1]} "
            f"({whole} whole-tree closure(s) follow the tree and are not listed)",
            file=sys.stderr,
        )
        return 0
    if args == ["--unnamed"]:
        import git_tracked

        with open(CLOSURES, encoding="utf-8") as fh:
            closures = load_closures(fh.read())
        named = {p for files in closures.values() for p in expand(files)} | set(
            EXTRA_NAMED
        )
        tracked = git_tracked.files()
        unnamed = [p for p in tracked if p not in named]
        print("\n".join(unnamed))
        print(
            f"check_closure: {len(unnamed)} of {len(tracked)} tracked file(s) are in no stage's closure",
            file=sys.stderr,
        )
        return 0
    if args == ["--json"]:
        import json

        asked = os.environ.get("CLOSURE_WITNESS") == "1"
        print(json.dumps(measure(with_witness=asked, with_tree=True), indent=1))
        return 0
    if args == []:
        import opa_gate

        return opa_gate.gate("closure")
    print(f"check_closure: unknown arguments {args!r}", file=sys.stderr)
    return 2


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    tracked = {"a.py", "d/b.json", "c.rego"}
    log = """\
123 openat(AT_FDCWD, "/r/a.py", O_RDONLY|O_CLOEXEC) = 3
[pid 124] openat(AT_FDCWD, "d/b.json", O_RDONLY) = 4
123 openat(AT_FDCWD, "/r/c.rego", O_RDONLY) = -1 ENOENT (No such file or directory)
123 stat("/r/untracked.txt", {st_mode=S_IFREG|0644}) = 0
123 execve("/usr/bin/python3", ["python3"], 0x7ff) = 0
123 newfstatat(AT_FDCWD, "/r/./d/../a.py", {st_mode=S_IFREG}, 0) = 0
"""
    chk(
        "a successful touch of a tracked file is in the closure (absolute, relative, pid-prefixed)",
        parse_trace(log, "/r", tracked),
        {"a.py", "d/b.json"},
    )
    chk(
        "a FAILED open (ENOENT) is not a read",
        "c.rego" in parse_trace(log, "/r", tracked),
        False,
    )
    chk(
        "a directory the stage lists declares the tracked files directly inside it (the names are the input)",
        parse_trace(
            '1 openat(AT_FDCWD, "/r/d", O_RDONLY|O_NONBLOCK|O_DIRECTORY) = 5\n',
            "/r",
            tracked,
        ),
        {"d/b.json"},
    )
    chk(
        "a stat of a directory keeps ONE tracked file under it (the directory exists), not all of them",
        parse_trace(
            '1 newfstatat(AT_FDCWD, "/r/d", {st_mode=S_IFDIR|0755}, 0) = 0\n',
            "/r",
            tracked | {"d/z.json"},
        ),
        {"d/b.json"},
    )
    chk(
        "a directory only the import system listed declares none of its files (W666)",
        parse_trace(
            '1 openat(AT_FDCWD, "/r/d", O_RDONLY|O_NONBLOCK|O_DIRECTORY) = 5\n',
            "/r",
            tracked,
            {"d"},
        ),
        set(),
    )
    listed = '1 openat(AT_FDCWD, "/r/d", O_RDONLY|O_NONBLOCK|O_DIRECTORY) = 5\n'
    got_dirs = set()
    chk(
        "with dirs, a listed directory is collected and declares none of its children (W692)",
        (parse_trace(listed, "/r", tracked, frozenset(), got_dirs), got_dirs),
        (set(), {"d"}),
    )
    got_dirs = set()
    chk(
        "with dirs, a file opened inside a listed directory is still content",
        parse_trace(
            listed + '2 openat(AT_FDCWD, "/r/d/b.json", O_RDONLY) = 6\n',
            "/r",
            tracked,
            frozenset(),
            got_dirs,
        ),
        {"d/b.json"},
    )
    got_dirs = set()
    chk(
        "with dirs, an import-only listing is neither a dir nor content",
        (parse_trace(listed, "/r", tracked, {"d"}, got_dirs), got_dirs),
        (set(), set()),
    )
    chk(
        "without dirs the old rule holds: the listing declares the files directly inside",
        parse_trace(listed, "/r", tracked, frozenset(), None),
        {"d/b.json"},
    )
    chk(
        "import_only_dirs: a directory another caller also listed stays declared",
        import_only_dirs("I\t/r/d\nI\t/r/e\nR\t/r/e\n", "/r"),
        {"d"},
    )
    with tempfile.TemporaryDirectory() as td:
        mod = os.path.join(td, "mod")
        scan = os.path.join(td, "scan")
        hook = os.path.join(td, "hook")
        for d in (mod, scan, hook):
            os.makedirs(d)
        with open(os.path.join(mod, "zz_mod.py"), "w", encoding="utf-8") as fh:
            fh.write("X = 1\n")
        with open(os.path.join(hook, "sitecustomize.py"), "w", encoding="utf-8") as fh:
            fh.write(LISTING_HOOK)
        listings = os.path.join(td, "listings.txt")
        prog = (
            f"import sys; sys.path.insert(0, {mod!r}); import zz_mod; import os; "
            f"os.listdir({scan!r})"
        )
        env = dict(os.environ, CLOSURE_LISTINGS=listings, PYTHONPATH=hook)
        subprocess.run([sys.executable, "-c", prog], env=env, check=True)
        with open(listings, encoding="utf-8") as fh:
            seen_listings = fh.read()
        chk(
            "the hook marks the import system's listing of a sys.path directory I and an explicit listdir R",
            (f"I\t{mod}" in seen_listings, f"R\t{scan}" in seen_listings),
            (True, True),
        )
        chk(
            "...so only the directory the import system alone listed is dropped",
            import_only_dirs(seen_listings, td) & {"mod", "scan"},
            {"mod"},
        )
    chk(
        "an untracked file and a host binary are not inputs",
        sorted(p for p in parse_trace(log, "/r", tracked) if p not in tracked),
        [],
    )
    chk(
        "a script path is that check's selftest, a stage kind is the stage itself",
        (stage_args("scripts/check_x.py"), stage_args("worklist")),
        (["selftest", "scripts/check_x.py"], ["worklist"]),
    )
    every = [f"f{i}.py" for i in range(20)]
    chk(
        "a closure covering 95% of the tracked list is the whole-tree marker, a narrow one is kept",
        (compress(every[:19], every), compress(every[:10], every)),
        ([WHOLE], every[:10]),
    )
    chk(
        "the whole-tree marker follows the tree: it expands to the tracked list, a narrow closure to itself",
        ("scripts/check_closure.py" in expand([WHOLE]), expand(["a.py"])),
        (True, ["a.py"]),
    )
    m_whole = measure({"s.py": [WHOLE]}, ["s.py"], {"s.py", "t.py"})
    chk(
        "a whole-tree stage lists its own script and nothing untracked",
        [
            (c["has_closure"], c["self_listed"], c["untracked"])
            for c in m_whole["cases"]
        ],
        [(True, True, [])],
    )
    text = render({"scripts/check_x.py": ["a.py", "scripts/check_x.py"]})
    chk(
        "closures.bzl round-trips through render and load",
        load_closures(text),
        {"scripts/check_x.py": ["a.py", "scripts/check_x.py"]},
    )
    chk(
        "holding: the narrow closures that list the file, the whole-tree ones counted and not listed",
        holding({"a": ["x", "f"], "b": ["x"], "c": [WHOLE], "d": ["f"]}, "f"),
        (["a", "d"], 1),
    )
    import closure_tree

    sample = {
        "scripts/check_a.py": ["a.py"],
        "worklist": ["w"],
        "pytestspec": ["policy/x.rego"],
    }
    with tempfile.TemporaryDirectory() as td:
        plan = closure_tree.plan_tree(sample, {"x": "gate"}, ["BUILD.bazel"])
        closure_tree.write_tree(plan, td)
        chk(
            "the root of the closure tree reads as the closures it was made from",
            load_closures(plan["closures.bzl"], td),
            sample,
        )
    try:
        load_closures("x = 1\n")
        refused = False
    except ValueError:
        refused = True
    chk("a text in neither form is refused, never read as empty", refused, True)
    m = measure(
        {"s.py": ["s.py", "gone.py"], "old.py": ["old.py"]},
        ["s.py", "new.py"],
        {"s.py"},
    )
    got = {
        c["script"]: (c["has_closure"], c["untracked"], c["self_listed"])
        for c in m["cases"]
    }
    chk(
        "a stage with no closure, an untracked listed file and a stale key are each a fact",
        (got, m["stale"]),
        ({"s.py": (True, ["gone.py"], True), "new.py": (False, [], False)}, ["old.py"]),
    )
    closure, why = observe("scripts/check_bazel_build.py")
    if closure is None:
        print(f"  SKIP the live observation: {why}")
    else:
        chk(
            "a live observation lists the check itself and a module it imports (git_tracked)",
            (
                "scripts/check_bazel_build.py" in closure,
                "scripts/git_tracked.py" in closure,
            ),
            (True, True),
        )
    stage = "scripts/check_bazel_build.py"
    if os.path.isfile(CLOSURES):
        with open(CLOSURES, encoding="utf-8") as fh:
            have = load_closures(fh.read()).get(stage)
    else:
        have = None
    if have is None:
        print("  SKIP the witness arms: no closure for the sample stage (run --write)")
    else:
        chk(
            "arm 1: the stage passes in a tree holding only its closure",
            witness(stage, have)[0],
            0,
        )
        chk(
            "arm 1 CAN FAIL: a closure missing a module the stage imports is refused",
            witness(stage, [f for f in have if f != "scripts/git_tracked.py"])[0] != 0,
            True,
        )
        chk(
            "arm 2: a planted defect in a closure module reaches the verdict",
            witness(stage, have, defect_in="scripts/git_tracked.py")[0] != 0,
            True,
        )
    print("check_closure selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
