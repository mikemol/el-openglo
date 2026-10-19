#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_post_commit.py — the post-commit hook's amend takes the message, never the index.

THE MEASURED FAILURE THIS EXISTS FOR (W561, 2026-10-17).  .githooks/post-commit folds its advisory
into the tip with `git commit --amend`, and a plain amend commits the WHOLE index.  A file staged
while a stack's gate ran (a `git add` for the next stack) therefore landed in that stack's last
commit: root_helpers.cases.json and urgency_cues.cases.json rode in the config_page commit, outside
its declared paths, with a closure that did not list them.  `git reflog` showed a `commit (amend)`
entry after every `mikemol-commit stack` line; mtools-ad read stackland, found nothing there that
reads the real index, and the hook line was the cause.

So the claim is BEHAVIOURAL and is measured: this runs the repo's REAL hook in a scratch repository
with one file staged before the commit it fires on, then reads what the tip holds and what is still
staged.  The requirement is policy/post_commit.rego (decided by scripts/opa_gate.py post_commit);
this file MEASURES.

    scripts/check_post_commit.py            # the verdict, as opa_gate post_commit decides it
    scripts/check_post_commit.py --json     # the measurement policy/post_commit.rego decides
    scripts/check_post_commit.py --selftest

Weakness: one scenario (a file staged beside the committed one).  It does not run the hook inside a
mikemol-commit snapshot, so the isolated path (MIKEMOL_REAL_ROOT) is not exercised; the amend is the
same line either way.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, ".githooks", "post-commit")
MARKER = "post-commit advisory (auto-captured)"
ENV = {
    "GIT_AUTHOR_NAME": "t",
    "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t",
    "GIT_COMMITTER_EMAIL": "t@t",
    "EL_NO_AUTO_PUSH": "1",
}
# the defective hook, as a stand-in the measurement must SEE: a plain amend commits the whole index.
# Guarded like the real one: the amend re-fires post-commit, and an unguarded stand-in recurses forever.
PLAIN_AMEND = f"""#!/usr/bin/env bash
[ -n "${{GUARD:-}}" ] && exit 0
GUARD=1 git commit --amend --no-verify -m "reworded {MARKER}" >/dev/null 2>&1 || true
"""


def _git(repo, *args):
    """stdout of one git call in `repo`, '' on a non-zero exit (the scenario reads state, not codes)."""
    env = {**os.environ, **ENV}
    res = subprocess.run(
        ["git", "-C", repo, *args], capture_output=True, text=True, env=env, check=False
    )
    return res.stdout if res.returncode == 0 else ""


def scenario(hook=HOOK):
    """One case: commit file `a` while file `b` is staged, with `hook` as the repo's post-commit.

    Returns the facts the policy reads: whether the hook amended (the marker is in HEAD), whether HEAD
    holds `b` (folded), and whether `b` is still staged afterwards."""
    repo = tempfile.mkdtemp(prefix="check_post_commit-")
    try:
        os.makedirs(os.path.join(repo, ".githooks"))
        shutil.copy(hook, os.path.join(repo, ".githooks", "post-commit"))
        _git(repo, "init", "-q")
        _git(repo, "config", "core.hooksPath", ".githooks")
        for name in ("a", "b"):
            with open(os.path.join(repo, name), "w", encoding="utf-8") as fh:
                fh.write(name + "\n")
        _git(repo, "add", "a", "b")
        # commit ONLY `a`: `b` stays staged, exactly as a `git add` made during a gate leaves it
        _git(repo, "commit", "-q", "-m", "first", "--", "a")
        body = _git(repo, "log", "-1", "--format=%B")
        head_files = _git(repo, "show", "--name-only", "--format=", "HEAD").split()
        staged = _git(repo, "diff", "--cached", "--name-only").split()
        return {
            "scenario": "staged-beside-the-committed-file",
            "amended": MARKER in body,
            "folded": "b" in head_files,
            "still_staged": "b" in staged,
        }
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def measure(hook=HOOK):
    present = os.path.exists(hook)
    return {
        "hook": os.path.relpath(hook, ROOT) if hook.startswith(ROOT) else hook,
        "hook_present": present,
        "cases": [scenario(hook)] if present else [],
    }


def main(argv):
    known = {"--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_post_commit: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("post_commit")


def _selftest():
    """The measurement SEES a hook that folds the index (a plain amend) and the real hook that does not."""
    ok = True

    def check(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    check("the hook path is repo-local", HOOK.startswith(ROOT), True)
    live = measure()
    check(
        "the live hook is present and exercised",
        (live["hook_present"], len(live["cases"])),
        (True, 1),
    )
    case = live["cases"][0]
    check("the live hook amended (its marker is in the tip)", case["amended"], True)
    check("the live hook leaves the staged file out of the tip", case["folded"], False)
    check("the live hook leaves the staged file staged", case["still_staged"], True)
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "post-commit")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write(PLAIN_AMEND)
        os.chmod(bad, 0o755)
        seen = scenario(bad)
        check(
            "a plain-amend hook IS seen folding the staged file", seen["folded"], True
        )
    gone = measure(os.path.join(ROOT, ".githooks", "no-such-hook"))
    check(
        "an absent hook is SEEN, with no case",
        (gone["hook_present"], gone["cases"]),
        (False, []),
    )
    print("check_post_commit selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
