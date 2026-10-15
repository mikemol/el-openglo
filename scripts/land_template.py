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
    scripts/land_template.py --selftest

`--plan` prints each phase and the command it would run, and runs nothing: the chain is reviewable
before it is runnable. `--run [NAME ...] [--fresh]` runs it: in order, halting on the first failed
phase (the phase and the tail of its output are printed), with a resume marker under .git keyed to the
changed templates' names and content, so a rerun resumes after the last phase that finished and any
further edit starts over; `--fresh` drops the marker. The render and the worklist gate run as capped
systemd services. Run it in the BACKGROUND: the worklist phase alone is several minutes.

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


def plan(names, stale_keys, roster):
    """The chain as DATA: an ordered [(phase, argv, note)] for the changed templates `names`.

    The closure phase appears only for names the roster declares (`stale_keys` are the closures behind),
    and only when there are stale ones; everything else runs for any shipped template. Nothing is run
    here: this is what the chain WOULD do, reviewable before it is runnable."""
    py = ".venv/bin/python3"
    steps = []
    new = [n for n in names if n in roster]
    if stale_keys:
        argv = [py, "scripts/check_closure.py", "--write", *stale_keys]
        note = f"{len(stale_keys)} stale for {', '.join(new)}"
        steps.append(("closures", argv, note))
    elif new:
        steps.append(("closures", None, "none stale: nothing to regenerate"))
    steps.append(("keys", [py, "scripts/check_action_key.py", "--write"], "re-record"))
    if names:
        argv = [py, "scripts/check_template_parity.py", "--record", *names]
        steps.append(("parity", argv, f"{len(names)} template(s)"))
    render = [py, "catalog/library/render_screens.py"]
    steps.append(("render", render, "a capped service; then see which stills moved"))
    for gate in GATES:
        steps.append((f"gate:{gate}", [py, "scripts/opa_gate.py", gate], "antichain"))
    worklist = [py, "scripts/worklist_gate.py"]
    steps.append(("worklist", worklist, "the full local pre-flight"))
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


MARKER = os.path.join(ROOT, ".git", "land_template.marker")
HEAVY = ("render_screens.py", "worklist_gate.py", "check_closure.py")


def chain_key(names):
    """A short digest of the changed templates' NAMES and CONTENT: the marker is valid only for the exact
    edit it recorded, so a further edit to any of them starts the chain over."""
    import hashlib

    h = hashlib.sha256()
    for n in sorted(names):
        h.update(n.encode())
        path = os.path.join(ROOT, "templates", n)
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                h.update(fh.read())
    return h.hexdigest()[:16]


def read_marker(path, key):
    """The phases the marker records as done for THIS key; [] when absent, unreadable or for another edit."""
    import json

    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        return []
    return list(doc.get("done", [])) if doc.get("key") == key else []


def write_marker(path, key, done):
    import json

    with open(
        path, "w", encoding="utf-8"
    ) as fh:  # atomic-write: exempt, a resume marker in .git
        json.dump({"key": key, "done": done}, fh)


def real_runner(argv):
    """(rc, tail): run one phase from the repo root. The heavy ones (the render, the worklist gate) run as
    memory-capped systemd services with their stdio piped back, never as a bare child of this process."""
    import subprocess

    if any(a.endswith(HEAVY) for a in argv):
        capped = ["systemd-run", "--user", "--pipe", "--wait", "--collect"]
        capped += ["-p", "MemoryMax=8G", "-p", "MemorySwapMax=0"]
        argv = capped + [f"--working-directory={ROOT}", *argv]
    r = subprocess.run(argv, cwd=ROOT, capture_output=True, text=True, check=False)
    return r.returncode, (r.stdout + r.stderr)[-1200:]


def run_plan(steps, key, marker, runner):
    """Run `steps` in order; halt on the first failure. Returns (ok, failed_phase, done, tail).

    A phase the marker already records as done for this key is skipped, so a rerun resumes after the last
    one that finished. A step with no argv is a skip the plan decided (nothing to do) and counts as done."""
    done = read_marker(marker, key)
    for phase, argv, _note in steps:
        if phase in done:
            continue
        rc, tail = (0, "") if argv is None else runner(argv)
        if rc != 0:
            return False, phase, done, tail
        done.append(phase)
        write_marker(marker, key, done)
    return True, None, done, ""


def git_changed():
    """The shipped templates git says changed, via changed_templates over `git status --porcelain`."""
    import subprocess

    porcelain = subprocess.run(
        ["git", "-C", ROOT, "status", "--porcelain", "--", "templates"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return changed_templates(porcelain)


def run_report(names, fresh):
    """Run the chain for `names` (default: git's changed templates), halting on the first failed phase.
    Exit 0 when every phase passed, 1 on a failure (the phase and the tail of its output are printed), 2 on
    a refusal. `fresh` drops the resume marker first."""
    names = names or git_changed()
    if not names:
        print("land_template: REFUSED: no changed template to land", file=sys.stderr)
        return 2
    roster = roster_files()
    keys, _m, why = closures_report([n for n in names if n in roster])
    steps = plan(names, [] if why else keys, roster)
    key = chain_key(names)
    if fresh and os.path.exists(MARKER):
        os.remove(MARKER)
    before = len(read_marker(MARKER, key))
    ok, failed, done, tail = run_plan(steps, key, MARKER, real_runner)
    total = len(steps)
    if before:
        print(f"land_template: resumed after {before} phase(s) the marker records")
    if not ok:
        print(
            f"land_template: FAILED at phase {failed!r} ({len(done)} of {total} done):"
        )
        print(tail)
        return 1
    print(
        f"land_template --run: {len(done)} of {total} phase(s) done "
        f"for {', '.join(names)}"
    )
    return 0


def plan_report(names):
    """Print the chain for `names` (default: the templates git says changed). Exit 0, or 2 on a refusal."""
    names = names or git_changed()
    if not names:
        print("land_template: REFUSED: no changed template to land", file=sys.stderr)
        return 2
    roster = roster_files()
    keys, _m, why = closures_report([n for n in names if n in roster])
    stale = keys if not why else []
    for phase, argv, note in plan(names, stale, roster):
        cmd = " ".join(argv) if argv else "(skipped)"
        print(f"  {phase:24s} {cmd}  # {note}")
    print(f"land_template --plan: {len(names)} template(s): {', '.join(names)}")
    return 0


def main(argv):
    args = argv[1:]
    flags = [a for a in args if a.startswith("--")]
    for a in flags:
        if a not in (
            "--closures",
            "--plan",
            "--run",
            "--fresh",
            "--split",
            "--regen",
            "--selftest",
        ):
            print(f"land_template: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in flags:
        return 0 if _selftest() else 1
    if "--run" in flags:
        names = [a for a in args if not a.startswith("--")]
        return run_report(names, "--fresh" in flags)
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
            rc, tail = real_runner(argv)
            print(tail)
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
        "plan: closures, keys, parity, render, the gate batch, then the worklist",
        [s[0] for s in steps],
        ["closures", "keys", "parity", "render"]
        + [f"gate:{g}" for g in GATES]
        + ["worklist"],
    )
    chk(
        "plan: the parity phase names every changed template",
        steps[2][1][-2:],
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
        "keys",
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
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        mk = os.path.join(td, "marker")
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
        first = run_plan(steps, "k1", mk, runner)
        chk("run: halts at the first failing phase, naming it", first[:2], (False, "d"))
        chk("run: the later phases never ran", "never" in calls, False)
        chk(
            "run: finished phases are recorded, a plan skip too",
            first[2],
            ["a", "b", "c"],
        )
        chk("run: the failing phase's output is returned", first[3], "boom")
        calls.clear()
        fixed = steps[:3] + [("d", ["ok3"], ""), ("e", ["ok4"], "")]
        again = run_plan(fixed, "k1", mk, runner)
        chk(
            "run: a rerun resumes, so only the remaining phases run",
            calls,
            ["ok3", "ok4"],
        )
        chk("run: ...and completes", again[0], True)
        calls.clear()
        run_plan(steps[:3], "k2", mk, runner)
        chk(
            "run: another key (the templates changed) starts over",
            calls,
            ["ok1", "ok2"],
        )
        chk(
            "run: a missing marker reads as none",
            read_marker(os.path.join(td, "x"), "k"),
            [],
        )
    chk(
        "chain_key: the same templates give the same key, other ones another",
        (
            chain_key(["Primitive.qml"]) == chain_key(["Primitive.qml"]),
            chain_key(["Primitive.qml"]) == chain_key(["GhostLayer.qml"]),
        ),
        (True, False),
    )
    chk(
        "an unknown name is refused",
        closures_report(["NoSuch.qml"])[2] is not None,
        True,
    )
    chk("an empty name list is refused", closures_report([])[2] is not None, True)
    print("land_template selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
