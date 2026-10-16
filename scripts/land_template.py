#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""land_template.py — the new-template landing chain as ONE command (W538, under W458).

⚑ WHY. Adding a shared component (Primitive, GhostLayer, LitLayer) or editing a shipped template meant the
same hand-run sequence, five times on 2026-10-13, and the gate refused it each time a step was forgotten:
a parity baseline not recorded, a render-constants disposition, a stale closure, the action keys. A routine
typed twice is a command (operator, via github-8f). This is the chain's first mode, the QUERY every later
phase reads; the phases follow as named functions (stale closures, closure write, action keys, parity
record, render re-run, the local worklist gate, the commit), each halting on the first failure.

    scripts/land_template.py --closures NAME.qml [NAME.qml ...]   # stored closures the new component(s) are missing from
    scripts/land_template.py --split OLD NEW      # closures holding OLD that lack NEW, after a module is cut
    scripts/land_template.py --plan [NAME ...]    # the chain as data for the changed templates (default: git's)
    scripts/land_template.py --commit WAYPOINT SUBJECT [PATH ...]   # stage, commit, compare what landed
    scripts/land_template.py --selftest

`--commit` is the chain's last phase: it stages the NAMED paths (default: every tracked change, never an
untracked file or the overlay cache; never `git commit -a`, whose temporary index makes the gates see 0
files) with `git add -A`, runs mikemol-commit with the private staged dir and the subject as ONE argv element
(a backtick in it is data), and then compares HEAD with the ask: the subject, the Waypoint trailer, the
post-commit advisory marker, and any deletion left staged (github-8f 2026-10-13: a commit that printed
success had another subject and a deletion no one named). Run it in the BACKGROUND: the gate is ~30 min.

`--plan` prints each phase and the command it would run, and runs nothing: the chain is reviewable
before it is runnable. `--run [NAME ...]` runs it: in order, halting on the first failed phase (the phase
and the tail of its output are printed). NOTHING RECORDS PROGRESS (W556; the waldo shape, mtools:W1067):
a phase is skipped when a cheap reading of the tree says its work is already there (closures by the
closure check, parity by the template_parity gate, the render and the keys by the action key check), so a
rerun after ANY edit asks the tree again and cannot resume from a stale record; a gate, a selftest and the
worklist have no reading, since running them is the reading. The render and the worklist gate run as capped
systemd services. Run it in the BACKGROUND: the worklist phase alone is several minutes.

THE CHAIN IS FOR THREE POPULATIONS, read from one `git status` (2026-10-16, after W185 and W544 each reached
the commit gate with a defect the chain did not look for): the changed shipped templates, the changed checks
(scripts/check_*.py: each gets its own --selftest phase, the commit's own stage), and the untracked files
(`git add`ed first by the track phase, since a closure holds only tracked files). A change to a check alone
is a chain too: selftest, render the stale stills, re-record the keys AFTER the render, the gate batch (the
Rego lint and the page and deps gates among it), then the worklist. THE WORKLIST PHASE IS BELIEVED THROUGH A
JUDGE: red only on a claim KNOWN_RED names (@RESIDUE, red by design) is green; any other red, or a failure
that names no claim, halts. WEAKNESS: the gate set is the ones a landing has been refused by so far, not the
commit's 110 stages; a stage not listed can still refuse, and the chain then grows one phase.

`--closures` answers: which stored stage closures READ THE COMPONENT ROSTER (hold every other roster
template) yet lack the new one. Those are the closures `check_closure.py --write` must regenerate in the same
commit, or the closure witness runs them in a tree without the new file. One key per line, then `n of m`.

WEAKNESS, STATED. It reads closures.bzl, so it sees a closure's MEMBERSHIP and nothing of a file's content;
a stage with no stored closure at all is not in the population and is not reported (check_closure's own
measurement says that); a closure that holds only SOME roster templates for another reason is not flagged,
which is right for a stage that never reads the roster and wrong for one that reads it only partly.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

CLOSURES_BZL = os.path.join(ROOT, "closures.bzl")


def stale_closures(closures, roster, names):
    """The closure keys that hold EVERY roster template but `names` and lack at least one of `names`.

    closures: {key: [files]} (check_closure.load_closures); roster: the bare file names of every shared
    component; names: the new component(s). A whole-tree closure (["*"]) holds everything and is never
    stale. Pure, so the selftest drives it without a tree."""
    new = {f"templates/{n}" for n in names}
    siblings = {f"templates/{n}" for n in roster} - new
    out = []
    for key, files in sorted(closures.items()):
        if files == ["*"]:
            continue
        held = set(files)
        if siblings <= held and not new <= held:
            out.append(key)
    return out


def roster_files():
    """The bare file names of every shared component display_params declares."""
    import display_params as DP

    return [c.file for c in DP.COMPONENTS]


def stored_closures():
    """{key: [files]} from closures.bzl, read with check_closure's own reader."""
    import check_closure as CC

    with open(CLOSURES_BZL, encoding="utf-8") as fh:
        return CC.load_closures(fh.read())


def closures_report(names):
    """(keys, m, why): the stale closure keys, how many closures were read, and a refusal reason or None.

    REFUSES an empty name list, a name the roster does not declare (add the Component first), and an empty
    closure population (a broken read, not a clean tree)."""
    roster = roster_files()
    if not names:
        return [], 0, "no component named: pass one or more NAME.qml"
    unknown = [n for n in names if n not in roster]
    if unknown:
        return [], 0, f"not in display_params.COMPONENTS: {unknown} (add it first)"
    closures = stored_closures()
    if not closures:
        return [], 0, "closures.bzl holds no closure: a broken read, not a clean tree"
    return stale_closures(closures, roster, names), len(closures), None


SHIPPED_SUFFIXES = (".qml", ".js")
# the cheap independent gates, in the order a template edit has been refused by them (W545: parity;
# W546: log_content, render_constants); marquee_live and config_reach are the live ones
GATES = (
    "template_parity",
    "render_constants",
    "log_content",
    "qml_lint",
    "marquee_live",
    "config_reach",
    # W185: a new rule in a policy reached the commit with a bare reference the Rego lint refuses; the
    # page and the deps gates are the other two a landing edit has been refused by
    "rego_lint",
    "config_page",
    "deps",
)


def changed_templates(porcelain):
    """The bare names of the shipped templates (.qml and .js, directly under templates/) that a
    `git status --porcelain -- templates` text lists as modified, added or untracked."""
    out = []
    for line in porcelain.splitlines():
        code, path = line[:2].strip(), line[3:]
        shipped = path.endswith(SHIPPED_SUFFIXES) and path.count("/") == 1
        if code and path.startswith("templates/") and shipped:
            out.append(path.split("/", 1)[1])
    return sorted(out)


# ⚑ THE ONE RED THE LOCAL WORKLIST GATE SHOWS BY DESIGN (CLAUDE.md; measured on every run of W538's first
# week): the open-residue symbols the tree owns. A chain that treated it as a failure could never be green;
# a chain that admitted ANY red would hide a real one. So the judge below admits exactly the claims named here.
KNOWN_RED = {"@RESIDUE": "the open-residue symbols the tree owns, red by design"}


def red_claims(text):
    """The claim tags the paperkit gate printed as failed, in order and once each: the `[@TAG]` of every
    'check FAILED for [@TAG]: ...' line of `text`."""
    out = []
    for line in text.splitlines():
        if "check FAILED for [" not in line:
            continue
        tag = line.split("check FAILED for [", 1)[1].split("]", 1)[0]
        if tag not in out:
            out.append(tag)
    return out


def judge_worklist(rc, text):
    """The exit code the chain should believe: 0 when the gate was red ONLY on claims KNOWN_RED names, else
    the gate's own. A failing gate that names no claim at all is a crash, not a known red, and stays red.
    WEAKNESS: it trusts the gate's own 'check FAILED for' lines; a gate that died before printing them is
    caught only by that rule (no named claim), not by what it would have said."""
    if rc == 0:
        return 0
    red = red_claims(text)
    return 0 if red and all(tag in KNOWN_RED for tag in red) else rc


JUDGES = {"worklist": judge_worklist}


def _porcelain_paths(porcelain):
    """[(code, path)] of a `git status --porcelain` text, the path unquoted as git printed it."""
    return [(line[:2].strip(), line[3:]) for line in porcelain.splitlines() if line]


def changed_scripts(porcelain):
    """The checks whose own --selftest a commit is refused by: scripts/check_*.py (not nested) that
    `git status --porcelain` lists as modified, added or untracked."""
    out = []
    for code, path in _porcelain_paths(porcelain):
        name = path.rsplit("/", 1)[-1]
        top = path.startswith("scripts/") and path.count("/") == 1
        if code and top and name.startswith("check_") and name.endswith(".py"):
            out.append(path)
    return sorted(out)


# paths git reports as untracked that are not work (a generated cache the overlay rebuilds)
NOT_WORK = ("overlay/metadata/",)


def untracked_files(porcelain):
    """The untracked FILES a landing should `git add` first (a closure holds only tracked files, so a new
    file nothing tracks yet leaves every closure incomplete): the '??' paths, directories and NOT_WORK left out."""
    return sorted(
        path
        for code, path in _porcelain_paths(porcelain)
        if code == "??" and not path.endswith("/") and not path.startswith(NOT_WORK)
    )


def plan(names, stale_keys, roster, scripts=(), untracked=()):
    """The chain as DATA: an ordered [(phase, argv, note)] for the changed templates `names` and the
    changed checks `scripts` (either may be empty, not both).

    The closure phase appears only for names the roster declares (`stale_keys` are the closures behind),
    and only when there are stale ones; the track phase only when files are untracked; a parity phase only
    for templates; a selftest phase per changed check (the gate refuses a commit whose check's selftest
    fails, so it is run first); the keys are re-recorded AFTER the render they describe. Nothing is run
    here: this is what the chain WOULD do, reviewable before it is runnable."""
    py = ".venv/bin/python3"
    steps = []
    if untracked:
        steps.append(
            ("track", ["git", "add", "--", *untracked], f"{len(untracked)} file(s)")
        )
    new = [n for n in names if n in roster]
    if stale_keys:
        argv = [py, "scripts/check_closure.py", "--write", *stale_keys]
        note = f"{len(stale_keys)} stale for {', '.join(new)}"
        steps.append(("closures", argv, note))
    elif new:
        steps.append(("closures", None, "none stale: nothing to regenerate"))
    if names:
        argv = [py, "scripts/check_template_parity.py", "--record", *names]
        steps.append(("parity", argv, f"{len(names)} template(s)"))
    for path in scripts:
        steps.append(
            (f"selftest:{path}", [py, path, "--selftest"], "the commit's own stage")
        )
    render = [py, "catalog/library/render_screens.py"]
    steps.append(("render", render, "a capped service, the stale stills only"))
    steps.append(("keys", [py, "scripts/check_action_key.py", "--write"], "re-record"))
    for gate in GATES:
        steps.append((f"gate:{gate}", [py, "scripts/opa_gate.py", gate], "antichain"))
    worklist = [py, "scripts/worklist_gate.py"]
    steps.append(
        ("worklist", worklist, "the full local pre-flight; @RESIDUE alone is admitted")
    )
    return steps


def lacking_after_split(closures, old, new):
    """The closure keys that hold `old` and lack `new`: after a module is cut, every stage that read the
    old file now reads the new one too, and its stored closure must be regenerated. A whole-tree closure
    holds both and is never listed. Pure."""
    return sorted(
        key
        for key, files in closures.items()
        if files != ["*"] and old in files and new not in files
    )


def split_report(paths):
    """(keys, m, why) for `--split OLD NEW` (repo-relative paths): the closures behind, how many were read,
    and a refusal reason or None. REFUSES anything but exactly two paths, a path that is not a file, and an
    empty closure population."""
    if len(paths) != 2:
        return [], 0, "pass exactly two paths: the file that was cut, then the new one"
    missing = [p for p in paths if not os.path.isfile(os.path.join(ROOT, p))]
    if missing:
        return [], 0, f"not a file in the tree: {missing}"
    closures = stored_closures()
    if not closures:
        return [], 0, "closures.bzl holds no closure: a broken read, not a clean tree"
    return lacking_after_split(closures, *paths), len(closures), None


HEAVY = ("render_screens.py", "worklist_gate.py", "check_closure.py")


def probes(names):
    """{phase: argv}: the cheap READING of the world that says a phase's work is already there (W556; the
    waldo shape, mtools:W1067: a phase is done when a witness over the world says so, never because a file
    remembers it). A phase with a probe is skipped when its probe exits 0. The closures phase is read by the
    closure check, the parity phase by the template_parity gate, and the render and the keys by the action
    key check (current keys mean the stills they describe are current). A gate, a selftest and the worklist
    have none: running them IS their reading, so they run every time. Nothing is recorded, so nothing can
    be stale: a rerun after any edit asks the tree again."""
    py = ".venv/bin/python3"
    out = {
        "closures": [py, "scripts/check_closure.py"],
        "render": [py, "scripts/check_action_key.py"],
        "keys": [py, "scripts/check_action_key.py"],
    }
    if names:
        out["parity"] = [py, "scripts/opa_gate.py", "template_parity"]
    return out


def real_runner(argv):
    """(rc, text): run one phase from the repo root, its whole output (a judge reads the claim lines at the
    top of a long gate report; the chain prints only the tail). The heavy ones (the render, the worklist
    gate) run as memory-capped systemd services with their stdio piped back, never as a bare child."""
    import subprocess

    if any(a.endswith(HEAVY) for a in argv):
        capped = ["systemd-run", "--user", "--pipe", "--wait", "--collect"]
        capped += ["-p", "MemoryMax=8G", "-p", "MemorySwapMax=0"]
        argv = capped + [f"--working-directory={ROOT}", *argv]
    r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
    return r.returncode, r.stdout + r.stderr


def run_plan(steps, runner, judges=JUDGES, readings=None):
    """Run `steps` in order; halt on the first failure. Returns (ok, failed_phase, done, tail).

    A phase whose reading (`readings[phase]`, an argv) exits 0 is already done in the world and is skipped, so
    a rerun resumes exactly where the tree says it is, and nothing records progress. A step with no argv is a
    skip the plan decided (nothing to do) and counts as done. A phase with a judge is believed through it: the
    judge sees the phase's rc and whole output, and returns the rc the chain should act on (the worklist's
    by-design red is the case)."""
    done = []
    for phase, argv, _note in steps:
        reading = (readings or {}).get(phase)
        if reading is not None and runner(reading)[0] == 0:
            done.append(phase)
            continue
        rc, text = (0, "") if argv is None else runner(argv)
        if phase in judges:
            rc = judges[phase](rc, text)
        if rc != 0:
            return False, phase, done, text[-1200:]
        done.append(phase)
    return True, None, done, ""


def git_porcelain():
    """`git status --porcelain` for the whole tree: what the landing chain reads its three populations from."""
    import subprocess

    return subprocess.run(
        ["git", "-C", ROOT, "status", "--porcelain"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def git_changed():
    """The shipped templates git says changed, via changed_templates over `git status --porcelain`."""
    return changed_templates(git_porcelain())


def chain_for(names, porcelain=None):
    """(names, scripts, untracked, steps): the chain for the working tree. `names` default to the templates
    git says changed; the changed checks and the untracked files come from the same `git status`. `steps` is
    None when there is nothing to land (no template and no check changed)."""
    porcelain = git_porcelain() if porcelain is None else porcelain
    names = names or changed_templates(porcelain)
    scripts = changed_scripts(porcelain)
    untracked = untracked_files(porcelain)
    if not names and not scripts:
        return names, scripts, untracked, None
    roster = roster_files()
    keys, _m, why = closures_report([n for n in names if n in roster])
    steps = plan(names, [] if why else keys, roster, scripts, untracked)
    return names, scripts, untracked, steps


# the staged dir this session's commits use while the katas sweep can collide on the shared one (the gate
# died on a staged file the sweep removed under it); a private dir is a path nothing else writes
PRIVATE_STAGED = os.path.expanduser("~/.cache/el-openglo-staged-claude")


def commit_paths(porcelain):
    """The paths a landing commit NAMES: every tracked path git lists as changed (modified, added, deleted),
    never an untracked one (the track phase adds those) and never NOT_WORK. `git commit -a` is never used (its
    temporary index makes the gates see 0 files), so the paths are named, sorted."""
    return sorted(
        path
        for code, path in _porcelain_paths(porcelain)
        if code and code != "??" and not path.startswith(NOT_WORK)
    )


def commit_argv(waypoint, subject, paths):
    """The argv of the one commit call. A list, never a shell string: a backtick or a quote in the subject
    is data here (an unquoted one executed and dropped waypoint text three times)."""
    head = [".venv/bin/mikemol-commit", "el-openglo", "--waypoint", waypoint]
    return head + ["--subject", subject, *paths]


def verify_commit(head_subject, head_body, waypoint, subject, porcelain):
    """[problem]: where the commit that LANDED differs from the one asked for (github-8f 2026-10-13: a commit
    that printed success had another subject and a staged deletion no one named). Empty means it matches.

    It compares the subject, the Waypoint trailer and the post-commit advisory marker (pre-push blocks a tip
    without it), and reports every deletion still staged at the index, which a finished commit leaves none of."""
    problems = []
    if head_subject != subject:
        problems.append(f"HEAD subject is {head_subject[:70]!r}, not the one asked")
    if f"Waypoint: {waypoint}" not in head_body.splitlines():
        problems.append(f"HEAD carries no 'Waypoint: {waypoint}' trailer")
    if "post-commit advisory (auto-captured)" not in head_body:
        problems.append("HEAD lacks the post-commit advisory marker (not pushable yet)")
    for line in porcelain.splitlines():
        if line[:1] == "D":
            problems.append(f"a deletion is still staged: {line[3:]}")
    return problems


def git_head():
    """(subject, body) of HEAD."""
    import subprocess

    def fmt(spec):
        return subprocess.run(
            ["git", "-C", ROOT, "log", "-1", f"--format={spec}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.rstrip("\n")

    return fmt("%s"), fmt("%b")


def commit_runner(argv):
    """(rc, text): the commit call, from the repo root, with the private staged dir in its environment."""
    import subprocess

    env = dict(os.environ, EL_STAGED_DIR=PRIVATE_STAGED)
    r = subprocess.run(
        argv, cwd=ROOT, capture_output=True, text=True, check=False, env=env
    )
    return r.returncode, r.stdout + r.stderr


def commit_report(
    waypoint, subject, paths, run=commit_runner, head=git_head, status=git_porcelain
):
    """Stage the named paths (default: every tracked change) and commit them under `waypoint`, then compare
    what landed with what was asked. Exit 0 when the commit landed and matches, 1 when the gate refused it or
    HEAD differs, 2 on a refusal before anything ran. `run`, `head` and `status` are the seams a selftest fakes."""
    import re

    if not re.fullmatch(r"W\d+", waypoint or ""):
        print(
            f"land_template: REFUSED: {waypoint!r} is not a waypoint symbol",
            file=sys.stderr,
        )
        return 2
    if not (subject or "").strip():
        print("land_template: REFUSED: an empty subject", file=sys.stderr)
        return 2
    paths = paths or commit_paths(status())
    if not paths:
        print("land_template: REFUSED: no tracked change to commit", file=sys.stderr)
        return 2
    rc, text = run(["git", "add", "-A", "--", *paths])
    if rc != 0:
        print(f"land_template: git add refused (rc {rc}):\n{text[-1200:]}")
        return 1
    rc, text = run(commit_argv(waypoint, subject, paths))
    if rc != 0:
        print(f"land_template: the commit was refused (rc {rc}); HEAD is unchanged:")
        print(text[-1200:])
        return 1
    problems = verify_commit(*head(), waypoint, subject, status())
    for p in problems:
        print(f"land_template: MISMATCH: {p}")
    if problems:
        return 1
    print(
        f"land_template --commit: {waypoint} landed, {len(paths)} path(s), HEAD matches the ask"
    )
    return 0


def run_report(names):
    """Run the chain for `names` (default: git's changed templates), halting on the first failed phase.
    Exit 0 when every phase passed, 1 on a failure (the phase and the tail of its output are printed), 2 on
    a refusal. A phase the tree already shows done is skipped by its reading (probes), not by a record."""
    names, scripts, _untracked, steps = chain_for(names)
    if steps is None:
        print(
            "land_template: REFUSED: no changed template or check to land",
            file=sys.stderr,
        )
        return 2
    ok, failed, done, tail = run_plan(steps, real_runner, readings=probes(names))
    total = len(steps)
    if not ok:
        print(
            f"land_template: FAILED at phase {failed!r} ({len(done)} of {total} done):"
        )
        print(tail)
        return 1
    print(
        f"land_template --run: {len(done)} of {total} phase(s) done "
        f"for {', '.join(names + scripts)}"
    )
    return 0


def plan_report(names):
    """Print the chain for `names` (default: the templates git says changed). Exit 0, or 2 on a refusal."""
    names, scripts, _untracked, steps = chain_for(names)
    if steps is None:
        print(
            "land_template: REFUSED: no changed template or check to land",
            file=sys.stderr,
        )
        return 2
    for phase, argv, note in steps:
        cmd = " ".join(argv) if argv else "(skipped)"
        print(f"  {phase:24s} {cmd}  # {note}")
    print(
        f"land_template --plan: {len(names)} template(s), {len(scripts)} check(s): "
        f"{', '.join(names + scripts)}"
    )
    return 0


def main(argv):
    args = argv[1:]
    flags = [a for a in args if a.startswith("--")]
    for a in flags:
        if a not in (
            "--closures",
            "--plan",
            "--run",
            "--split",
            "--regen",
            "--commit",
            "--selftest",
        ):
            print(f"land_template: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in flags:
        return 0 if _selftest() else 1
    if "--commit" in flags:
        rest = [a for a in args if not a.startswith("--")]
        if len(rest) < 2:
            print(
                "land_template: --commit needs WAYPOINT SUBJECT [PATH ...]",
                file=sys.stderr,
            )
            return 2
        return commit_report(rest[0], rest[1], rest[2:])
    if "--run" in flags:
        names = [a for a in args if not a.startswith("--")]
        return run_report(names)
    if "--split" in flags:
        keys, m, why = split_report([a for a in args if not a.startswith("--")])
        if why:
            print(f"land_template: REFUSED: {why}", file=sys.stderr)
            return 2
        for k in keys:
            print(k)
        print(
            f"land_template: {len(keys)} of {m} stored closure(s) "
            "hold the old file and lack the new"
        )
        if "--regen" in flags and keys:
            argv = [".venv/bin/python3", "scripts/check_closure.py", "--write", *keys]
            rc, text = real_runner(argv)
            print(text[-1200:])
            print(f"land_template: regenerated {len(keys)} closure(s): rc {rc}")
            return rc
        return 0
    if "--plan" in flags:
        return plan_report([a for a in args if not a.startswith("--")])
    if "--closures" in flags:
        names = [a for a in args if not a.startswith("--")]
        keys, m, why = closures_report(names)
        if why:
            print(f"land_template: REFUSED: {why}", file=sys.stderr)
            return 2
        for k in keys:
            print(k)
        lacking = ", ".join(f"templates/{n}" for n in names)
        print(
            f"land_template: {len(keys)} of {m} stored closure(s) read the "
            f"component roster and lack {lacking}"
        )
        return 0
    print(
        "usage: land_template.py --closures NAME.qml [NAME.qml ...] | --selftest",
        file=sys.stderr,
    )
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

    roster = ["A.qml", "B.qml", "New.qml"]
    both = ["templates/A.qml", "templates/B.qml"]
    closures = {
        "reads_roster_lacks_new": both + ["x.py"],
        "reads_roster_has_new": both + ["templates/New.qml"],
        "reads_part_of_roster": ["templates/A.qml"],
        "reads_none": ["x.py"],
        "whole_tree": ["*"],
    }
    chk(
        "a closure holding every sibling and lacking the new one is stale, only it",
        stale_closures(closures, roster, ["New.qml"]),
        ["reads_roster_lacks_new"],
    )
    chk(
        "a whole-tree closure is never stale",
        "whole_tree" in stale_closures(closures, roster, ["New.qml"]),
        False,
    )
    chk(
        "two new components at once: the closure lacking either is stale",
        stale_closures(
            {"k": ["templates/A.qml"], "j": ["templates/A.qml", "templates/B.qml"]},
            ["A.qml", "B.qml", "C.qml"],
            ["B.qml", "C.qml"],
        ),
        ["j", "k"],
    )
    chk("no closures is an empty answer", stale_closures({}, roster, ["New.qml"]), [])
    # the REAL tree: the roster is declared, the closures are read, and every roster
    # component is current (a stale closure here is exactly what the next landing
    # would be refused for)
    r = roster_files()
    chk("the roster declares components", len(r) > 0, True)
    real = stored_closures()
    chk("closures.bzl holds closures", len(real) > 0, True)
    behind = {n: stale_closures(real, r, [n]) for n in r}
    chk(
        "every stored closure is current for every roster component",
        {n: ks for n, ks in behind.items() if ks},
        {},
    )
    porcelain = (
        " M templates/marquee-main.qml\n"
        "A  templates/LitLayer.qml\n"
        "?? templates/Primitive.qml\n"
        " M templates/loader.py\n"
        " M templates/sub/dir.qml\n"
        " M scripts/check_x.py\n"
        " M templates/marquee-body.js\n"
    )
    chk(
        "changed_templates: modified, added, untracked; not .py, nested or elsewhere",
        changed_templates(porcelain),
        ["LitLayer.qml", "Primitive.qml", "marquee-body.js", "marquee-main.qml"],
    )
    chk("changed_templates: a clean tree names none", changed_templates(""), [])
    steps = plan(["New.qml", "x.js"], ["scripts/k.py"], ["A.qml", "New.qml"])
    chk(
        "plan: closures, parity, render, THEN the keys it describes, the gate batch, then the worklist",
        [s[0] for s in steps],
        ["closures", "parity", "render", "keys"]
        + [f"gate:{g}" for g in GATES]
        + ["worklist"],
    )
    chk(
        "plan: the parity phase names every changed template",
        steps[1][1][-2:],
        ["New.qml", "x.js"],
    )
    chk(
        "plan: no stale closure means the closure phase is skipped, not run",
        plan(["New.qml"], [], ["New.qml"])[0][1],
        None,
    )
    chk(
        "plan: a template outside the roster has no closure phase at all",
        plan(["x.js"], [], ["A.qml"])[0][0],
        "parity",
    )
    cut = {
        "reads_old_lacks_new": ["old.py", "x.py"],
        "reads_both": ["old.py", "new.py"],
        "reads_neither": ["x.py"],
        "reads_new_only": ["new.py"],
        "whole_tree": ["*"],
    }
    chk(
        "split: only the closure holding the old file and lacking the new is behind",
        lacking_after_split(cut, "old.py", "new.py"),
        ["reads_old_lacks_new"],
    )
    chk(
        "split: nothing is behind once every reader holds the new file",
        lacking_after_split({"k": ["old.py", "new.py"]}, "old.py", "new.py"),
        [],
    )
    chk("split: one path is refused", split_report(["only.py"])[2] is not None, True)
    chk(
        "split: a path that is not a file is refused",
        split_report(["cvd_gate.py", "NoSuch.py"])[2] is not None,
        True,
    )
    import contextlib
    import io

    calls = []

    def runner(argv):
        calls.append(argv[0])
        return (1, "boom") if argv[0] == "bad" else (0, "")

    steps = [
        ("a", ["ok1"], ""),
        ("b", None, "skipped by the plan"),
        ("c", ["ok2"], ""),
        ("d", ["bad"], ""),
        ("e", ["never"], ""),
    ]
    first = run_plan(steps, runner)
    chk("run: halts at the first failing phase, naming it", first[:2], (False, "d"))
    chk("run: the later phases never ran", "never" in calls, False)
    chk(
        "run: finished phases are listed, a plan skip too",
        first[2],
        ["a", "b", "c"],
    )
    chk("run: the failing phase's output is returned", first[3], "boom")
    # W556: progress is READ from the world, never recorded; a phase whose reading passes is skipped
    calls.clear()
    fixed = steps[:3] + [("d", ["ok3"], ""), ("e", ["ok4"], "")]
    read = {"a": ["reads-done"], "c": ["reads-undone-c"]}

    def reading_runner(argv):
        calls.append(argv[0])
        if argv[0] == "reads-undone-c":
            return 1, ""
        return (1, "boom") if argv[0] == "bad" else (0, "")

    again = run_plan(fixed, reading_runner, readings=read)
    chk(
        "run: a phase whose reading passes is skipped, one whose reading fails runs, the rest run",
        calls,
        ["reads-done", "reads-undone-c", "ok2", "ok3", "ok4"],
    )
    chk(
        "run: ...and completes, every phase listed done",
        (again[0], again[2]),
        (True, ["a", "b", "c", "d", "e"]),
    )
    calls.clear()
    run_plan(steps[:3], reading_runner)
    chk(
        "run: with no readings there is no memory: every phase runs again (nothing records status)",
        calls,
        ["ok1", "ok2"],
    )
    pr = probes(["x.qml"])
    chk(
        "probes: closures, parity, render and keys are read by the checks that already measure them",
        sorted(pr),
        ["closures", "keys", "parity", "render"],
    )
    chk(
        "probes: render and keys share the action key reading",
        pr["render"] == pr["keys"],
        True,
    )
    chk(
        "probes: a check-only change has no parity reading",
        "parity" in probes([]),
        False,
    )
    chk(
        "probes: no gate and no worklist has a reading, since running them IS the reading",
        [p for p in pr if p.startswith("gate:") or p == "worklist"],
        [],
    )
    chk(
        "an unknown name is refused",
        closures_report(["NoSuch.qml"])[2] is not None,
        True,
    )
    chk("an empty name list is refused", closures_report([])[2] is not None, True)
    # W538 (2026-10-16): the gaps the first real landings showed, each an arm that can fail
    report = (
        "paperkit-gate: check FAILED for [@RESIDUE]: tool:check_symbol.py --bucket RESIDUE\n"
        "paperkit-gate: FAIL\n"
        "paperkit-gate: check FAILED for [@REGO-LINT]: tool:opa_gate.py rego_lint\n"
        "paperkit-gate: check FAILED for [@RESIDUE]: again\n"
    )
    chk(
        "red_claims: each failed claim once, in order",
        red_claims(report),
        ["@RESIDUE", "@REGO-LINT"],
    )
    chk(
        "red_claims: a passing report names none",
        red_claims("paperkit-gate: PASS\n"),
        [],
    )
    only = "paperkit-gate: check FAILED for [@RESIDUE]: x\n"
    chk("judge: a green gate stays green", judge_worklist(0, ""), 0)
    chk(
        "judge: red ONLY on the by-design @RESIDUE is admitted",
        judge_worklist(1, only),
        0,
    )
    chk(
        "judge: @RESIDUE beside a real red stays red",
        judge_worklist(1, report),
        1,
    )
    chk(
        "judge: a failing gate that names no claim is a crash, not a known red",
        judge_worklist(1, "Traceback (most recent call last)\n"),
        1,
    )
    chk(
        "judge: the exit code is the gate's own when it is not admitted",
        judge_worklist(3, report),
        3,
    )
    porc = (
        " M scripts/check_marquee_live.py\n"
        "A  scripts/check_new.py\n"
        "?? scripts/check_untracked.py\n"
        " M scripts/make_x.py\n"
        " M scripts/sub/check_nested.py\n"
        " M policy/marquee_live.rego\n"
        "?? scripts/helper.py\n"
        "?? overlay/metadata/md5-cache/\n"
        "?? newdir/\n"
        "?? overlay/metadata/other.txt\n"
    )
    chk(
        "changed_scripts: checks directly under scripts/, modified, added or untracked; not other scripts or nested",
        changed_scripts(porc),
        [
            "scripts/check_marquee_live.py",
            "scripts/check_new.py",
            "scripts/check_untracked.py",
        ],
    )
    chk(
        "untracked_files: untracked files only; a directory and the overlay cache are left out",
        untracked_files(porc),
        ["scripts/check_untracked.py", "scripts/helper.py"],
    )
    chk("untracked_files: a clean tree names none", untracked_files(""), [])
    sc = plan(
        [],
        [],
        ["A.qml"],
        ["scripts/check_a.py"],
        ["scripts/new.py"],
    )
    chk(
        "plan: a check-only change tracks, runs its selftest, renders, re-keys, gates, then the worklist; no parity",
        [s[0] for s in sc],
        ["track", "selftest:scripts/check_a.py", "render", "keys"]
        + [f"gate:{g}" for g in GATES]
        + ["worklist"],
    )
    chk(
        "plan: the track phase adds exactly the untracked files",
        sc[0][1],
        ["git", "add", "--", "scripts/new.py"],
    )
    chk(
        "plan: a selftest phase runs the check's own --selftest",
        sc[1][1][-2:],
        ["scripts/check_a.py", "--selftest"],
    )
    chk(
        "plan: the gate batch holds the Rego lint a new rule was refused by",
        "gate:rego_lint" in [s[0] for s in sc],
        True,
    )
    chk(
        "chain_for: a clean tree has nothing to land",
        chain_for([], "")[3],
        None,
    )
    chk(
        "chain_for: a changed check alone is a chain",
        chain_for([], " M scripts/check_marquee_live.py\n")[3] is not None,
        True,
    )
    seen = []

    def judged(argv):
        seen.append(argv[0])
        if argv[0] == "wl":
            return 1, only
        return (2, "crash") if argv[0] == "crash" else (0, "")

    steps = [("a", ["ok"], ""), ("worklist", ["wl"], ""), ("z", ["after"], "")]
    res = run_plan(steps, judged)
    chk(
        "run: the worklist phase red only on @RESIDUE does not halt the chain",
        (res[0], seen),
        (True, ["ok", "wl", "after"]),
    )
    seen.clear()
    steps = [("worklist", ["crash"], ""), ("z", ["after"], "")]
    res = run_plan(steps, judged)
    chk(
        "run: a worklist crash halts the chain at the worklist",
        (res[:2], "after" in seen),
        ((False, "worklist"), False),
    )
    # W538 gap 4: the commit call and the check that what landed is what was asked
    chk(
        "commit_paths: tracked changes only; an untracked file, a directory and the overlay cache are not named",
        commit_paths(" M a.py\nA  b.py\n D c.py\n?? d.py\n?? overlay/metadata/x\n"),
        ["a.py", "b.py", "c.py"],
    )
    chk("commit_paths: a clean tree names none", commit_paths(""), [])
    chk(
        "commit_argv: a list, the subject one element whatever it holds",
        commit_argv("W9", "a `b` 'c' $d", ["x.py", "y.py"]),
        [".venv/bin/mikemol-commit", "el-openglo", "--waypoint", "W9"]
        + ["--subject", "a `b` 'c' $d", "x.py", "y.py"],
    )
    body = "Waypoint: W9\n\nCo-Authored-By: x\n\npost-commit advisory (auto-captured):\n  y"
    chk(
        "verify_commit: the commit asked for matches",
        verify_commit("subj", body, "W9", "subj", ""),
        [],
    )
    chk(
        "verify_commit: another subject is reported",
        len(verify_commit("other", body, "W9", "subj", "")),
        1,
    )
    chk(
        "verify_commit: another waypoint's trailer is reported",
        len(verify_commit("subj", body, "W10", "subj", "")),
        1,
    )
    chk(
        "verify_commit: a missing advisory marker is reported",
        len(verify_commit("subj", "Waypoint: W9\n", "W9", "subj", "")),
        1,
    )
    chk(
        "verify_commit: a deletion left staged is reported by its path",
        verify_commit("subj", body, "W9", "subj", "D  gone.py\n M ok.py\n"),
        ["a deletion is still staged: gone.py"],
    )
    ran = []

    def fake_run(argv):
        ran.append(argv)
        return (1, "gate refused") if "--waypoint" in argv and bad_gate else (0, "")

    bad_gate = False
    quiet = io.StringIO()
    with contextlib.redirect_stdout(quiet):
        good = commit_report(
            "W9",
            "subj",
            ["a.py"],
            run=fake_run,
            head=lambda: ("subj", body),
            status=lambda: "",
        )
    chk(
        "commit_report: stages the named paths with -A, then commits, and a matching HEAD is exit 0",
        (good, [r[:3] for r in ran]),
        (
            0,
            [
                ["git", "add", "-A"],
                [".venv/bin/mikemol-commit", "el-openglo", "--waypoint"],
            ],
        ),
    )
    ran.clear()
    with contextlib.redirect_stdout(quiet):
        wrong = commit_report(
            "W9",
            "subj",
            ["a.py"],
            run=fake_run,
            head=lambda: ("another", body),
            status=lambda: "",
        )
    chk("commit_report: a HEAD with another subject is exit 1", wrong, 1)
    bad_gate = True
    with contextlib.redirect_stdout(quiet):
        refused = commit_report(
            "W9",
            "subj",
            ["a.py"],
            run=fake_run,
            head=lambda: ("subj", body),
            status=lambda: "",
        )
    chk("commit_report: a refused commit is exit 1 and never inspects HEAD", refused, 1)
    with contextlib.redirect_stderr(quiet):
        chk(
            "commit_report: a non-symbol waypoint is refused before anything runs",
            commit_report("nine", "subj", ["a.py"], run=fake_run),
            2,
        )
        chk(
            "commit_report: an empty subject is refused",
            commit_report("W9", "  ", ["a.py"], run=fake_run),
            2,
        )
        chk(
            "commit_report: no tracked change is refused",
            commit_report("W9", "subj", [], run=fake_run, status=lambda: "?? new.py\n"),
            2,
        )
    print("land_template selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
