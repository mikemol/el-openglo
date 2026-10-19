#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_worktrees.py - the census of the agent worktrees under .claude/worktrees (W233).

    scripts/check_worktrees.py            # one row per worktree: class, ahead, changed, unported, sha, path; n of m
    scripts/check_worktrees.py --remove   # the `git worktree remove` commands for the removable classes, printed, never run
    scripts/check_worktrees.py --selftest

Dozens of agent worktrees piled up under .claude/worktrees. Deleting one blind can lose work, so this reads each
and classes it by what git says and nothing else. The question "does it carry unported work?" has an exact
answer: for every path the worktree changes, is the file byte-identical to main's version (or, for a deletion,
already absent from main)? Those paths are PORTED; any other is UNPORTED work to read.

    safe       its tip is an ancestor of main and its tree has no change at all
    ported     merged, changes present, but EVERY changed path already equals main: removing it loses nothing
    unported   merged, with at least one changed path that differs from main: work to read first
    ahead      carries commits main does not have
    locked     git marks it locked
    missing    registered but its directory is gone (`git worktree prune`, not removal)

WEAKNESS. "Merged" is ancestry of the main branch, so a worktree whose branch was squash-merged or rebased reads
`ahead` though its work is in main: those need a human read of the diff. "Ported" compares file bytes with main's
CURRENT version, so a path main has since changed again reads unported though the work landed once. `--remove`
prints commands only (ported ones with --force, since git refuses a changed tree); running them is a separate
act. The .tree-writes worktrees are check_tree_writes' own and are not listed. An untracked directory is
unported. An empty population is refused: the search is broken.
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN = "main"
MARK = os.sep + ".claude" + os.sep + "worktrees" + os.sep


def parse(porcelain):
    """[{path, head, branch, locked}] from `git worktree list --porcelain` text."""
    out, cur = [], {}
    for line in porcelain.splitlines() + [""]:
        if not line:
            if cur:
                out.append(cur)
            cur = {}
        elif line.startswith("worktree "):
            cur = {"path": line[9:], "head": "", "branch": None, "locked": False}
        elif line.startswith("HEAD "):
            cur["head"] = line[5:]
        elif line.startswith("branch "):
            cur["branch"] = line[7:]
        elif line.startswith("locked"):
            cur["locked"] = True
    return out


def changed_paths(status):
    """The paths a `git status --porcelain` text names (the new name of a rename)."""
    out = []
    for line in status.splitlines():
        path = line[3:]
        out.append(path.split(" -> ")[-1].strip('"'))
    return out


def classify(entry, merged, changed, unported, exists):
    """The class of one worktree from the facts git gave."""
    if not exists:
        return "missing"
    if entry["locked"]:
        return "locked"
    if not merged:
        return "ahead"
    if changed == 0:
        return "safe"
    return "unported" if unported else "ported"


def git(args, cwd=ROOT):
    return subprocess.run(
        ["git", "-C", cwd, *args], capture_output=True, text=True, check=False
    )


def equals_main(root, wt, path):
    """True when `path` in worktree `wt` is byte-identical to main's version (or deleted and absent from main)."""
    here = os.path.join(wt, path)
    in_main = git(["rev-parse", "--verify", "--quiet", f"{MAIN}:{path}"], root)
    if not os.path.lexists(here):
        return in_main.returncode != 0
    if os.path.isdir(here) or in_main.returncode != 0:
        return False
    return (
        git(["hash-object", "--", here], root).stdout.strip() == in_main.stdout.strip()
    )


def census(root=ROOT):
    """[(class, ahead, changed, unported, entry)] for every agent worktree, in path order."""
    listed = parse(git(["worktree", "list", "--porcelain"], root).stdout)
    rows = []
    for e in sorted(listed, key=lambda x: x["path"]):
        if MARK not in e["path"] + os.sep:
            continue
        exists = os.path.isdir(e["path"])
        merged = (
            git(["merge-base", "--is-ancestor", e["head"], MAIN], root).returncode == 0
        )
        ahead_out = git(["rev-list", "--count", f"{MAIN}..{e['head']}"], root).stdout
        ahead = int(ahead_out) if ahead_out.strip().isdigit() else -1
        paths = (
            changed_paths(git(["status", "--porcelain"], e["path"]).stdout)
            if exists
            else []
        )
        unported = sum(1 for p in paths if not equals_main(root, e["path"], p))
        rows.append(
            (
                classify(e, merged, len(paths), unported, exists),
                ahead,
                len(paths),
                unported,
                e,
            )
        )
    return rows


def main(argv):
    if argv[1:] not in ([], ["--remove"]):
        print(f"check_worktrees: unknown arguments {argv[1:]!r}", file=sys.stderr)
        return 2
    rows = census()
    if not rows:
        print(
            "check_worktrees: no agent worktree was read; the search is broken",
            file=sys.stderr,
        )
        return 2
    if argv[1:] == ["--remove"]:
        out = [r for r in rows if r[0] in ("safe", "ported")]
        for cls, _a, _c, _u, e in out:
            force = " --force" if cls == "ported" else ""
            print(f"git worktree remove{force} {e['path']}")
        print(
            f"check_worktrees: {len(out)} of {len(rows)} worktree(s) are removable (safe or ported); "
            "commands printed, none run",
            file=sys.stderr,
        )
        return 0
    for cls, ahead, changed, unported, e in rows:
        print(
            f"{cls}\tahead {ahead}\tchanged {changed}\tunported {unported}\t{e['head'][:7]}\t{e['path']}"
        )
    counts = {}
    for r in rows:
        counts[r[0]] = counts.get(r[0], 0) + 1
    print(
        f"check_worktrees: {len(rows)} agent worktree(s): "
        + ", ".join(f"{n} {k}" for k, n in sorted(counts.items())),
        file=sys.stderr,
    )
    return 0


def _selftest():
    import tempfile

    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    text = (
        "worktree /r\nHEAD aaa\nbranch refs/heads/main\n\n"
        "worktree /r/.claude/worktrees/a\nHEAD bbb\nbranch refs/heads/x\nlocked reason\n\n"
        "worktree /r/.claude/worktrees/b\nHEAD ccc\ndetached\n"
    )
    got = parse(text)
    chk(
        "parse reads every worktree block",
        [e["path"] for e in got],
        ["/r", "/r/.claude/worktrees/a", "/r/.claude/worktrees/b"],
    )
    chk(
        "parse reads the branch, the lock and a detached HEAD",
        (got[1]["branch"], got[1]["locked"], got[2]["branch"]),
        ("refs/heads/x", True, None),
    )
    chk(
        "changed_paths reads modified, staged, untracked and the new name of a rename",
        changed_paths(" M a.py\nA  b/c.rego\n?? d.txt\nR  old.py -> new.py\n"),
        ["a.py", "b/c.rego", "d.txt", "new.py"],
    )
    e = {"locked": False}
    chk("merged with no change is safe", classify(e, True, 0, 0, True), "safe")
    chk(
        "merged with changes that all equal main is ported",
        classify(e, True, 3, 0, True),
        "ported",
    )
    chk(
        "merged with a changed path that differs from main is unported",
        classify(e, True, 3, 1, True),
        "unported",
    )
    chk("not merged is ahead", classify(e, False, 0, 0, True), "ahead")
    chk(
        "locked wins over merged and clean",
        classify({"locked": True}, True, 0, 0, True),
        "locked",
    )
    chk("a gone directory is missing", classify(e, True, 0, 0, False), "missing")
    with tempfile.TemporaryDirectory() as td:

        def run(*a, cwd=td):
            subprocess.run(
                ["git", "-C", cwd, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                check=True,
                capture_output=True,
            )

        run("init", "-q", "-b", MAIN)
        for name in ("f.txt", "same.txt"):
            with open(os.path.join(td, name), "w", encoding="utf-8") as fh:
                fh.write("one\n")
        run("add", "f.txt", "same.txt")
        run("commit", "-q", "-m", "c")
        with open(os.path.join(td, "f.txt"), "w", encoding="utf-8") as fh:
            fh.write("two\n")
        with open(os.path.join(td, "new.txt"), "w", encoding="utf-8") as fh:
            fh.write("new\n")
        chk(
            "a path whose bytes equal main's is ported",
            equals_main(td, td, "same.txt"),
            True,
        )
        chk("a modified path differs from main", equals_main(td, td, "f.txt"), False)
        chk("a new path main lacks is unported", equals_main(td, td, "new.txt"), False)
        os.remove(os.path.join(td, "same.txt"))
        chk(
            "a deleted path that main has is unported",
            equals_main(td, td, "same.txt"),
            False,
        )
        chk(
            "a deleted path that main lacks is ported",
            equals_main(td, td, "never.txt"),
            True,
        )
    chk("an unknown flag is refused (2)", main(["x", "--bogus"]), 2)
    print("check_worktrees selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
