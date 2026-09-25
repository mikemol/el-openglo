#!/usr/bin/env python3
"""auto_push.py — push main after each commit, from the post-commit hook, in the background.

⚑ AUTHORISED BY THE OPERATOR (2026-09-25): "we're healthy and rigorous now I think we can
start auto pushing as a post-commit hook." Before this, every push waited on the operator.

⚑ WHAT KEEPS IT SAFE, BECAUSE A PUSH IS OUTWARD AND NOT UNDONE BY A LOCAL RESET:
  * it runs AFTER the post-commit amend (the advisory marker is in HEAD), and the push
    still goes through .githooks/pre-push -> pre-push.local: the marker on every pushed
    tip, then the tree-writes gate. Nothing here bypasses a hook; there is no --no-verify.
  * FAST-FORWARD ONLY. It fetches, and pushes only if origin/main is an ancestor of HEAD.
    A diverged history is logged and LEFT for a human — never a force, never a rebase.
  * main only; never mid-rebase/merge/cherry-pick (the hook exits before calling this).
  * serialised by a lock: overlapping commits do not start overlapping pushes; whoever
    holds the lock pushes the newest HEAD, so a later commit is never pushed stale.
  * detached from the commit: the hook starts it in the background, so the ~190 s CPU
    tree-writes gate does not block `git commit`. Every outcome goes to .git/auto-push.log.

    scripts/auto_push.py              # fetch, check fast-forward, push (logs to .git/auto-push.log)
    scripts/auto_push.py --dry-run    # decide and log, but do not push
    scripts/auto_push.py --selftest

Weakness: if the push is refused (the tree-writes gate reddens), the commit stays local
and the log says why — the refusal is visible only there and in `git status` (ahead N).
"""
import datetime
import fcntl
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REMOTE, BRANCH = "origin", "main"


def git(*args, check=False):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, check=check)


def git_dir():
    return os.path.join(ROOT, git("rev-parse", "--git-dir", check=True).stdout.strip())


def decide(branch, local, remote, remote_is_ancestor):
    """(push?, why) — the whole policy, as a pure function the selftest can drive."""
    if branch != BRANCH:
        return False, f"on {branch!r}, not {BRANCH!r}: auto-push is main-only"
    if remote is None:
        return False, f"no {REMOTE}/{BRANCH} to compare against"
    if local == remote:
        return False, "already pushed (HEAD == origin/main)"
    if not remote_is_ancestor:
        return False, "DIVERGED: origin/main is not an ancestor of HEAD — left for a human, never forced"
    return True, "fast-forward"


def log(line):
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    with open(os.path.join(git_dir(), "auto-push.log"), "a", encoding="utf-8") as fh:
        fh.write(f"{stamp}  {line}\n")


def main(argv):
    flags = [a for a in argv[1:] if a.startswith("--")]
    for a in flags:
        if a not in ("--dry-run", "--selftest"):
            print(f"auto_push: unknown flag {a!r}", file=sys.stderr)
            return 2
    lock = open(os.path.join(git_dir(), "auto-push.lock"), "w")
    fcntl.flock(lock, fcntl.LOCK_EX)          # serialise; the newest HEAD is read AFTER the lock
    try:
        fetched = git("fetch", "--quiet", REMOTE, BRANCH)
        if fetched.returncode != 0:
            log(f"NOT PUSHED: fetch failed: {fetched.stderr.strip()[-200:]}")
            return 1
        branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
        local = git("rev-parse", "HEAD").stdout.strip()
        r = git("rev-parse", "--verify", "--quiet", f"{REMOTE}/{BRANCH}")
        remote = r.stdout.strip() or None
        anc = remote is not None and git("merge-base", "--is-ancestor", remote, local).returncode == 0
        push, why = decide(branch, local, remote, anc)
        if not push:
            log(f"not pushed {local[:10]}: {why}")
            return 0
        if "--dry-run" in flags:
            log(f"DRY RUN: would push {local[:10]} ({why})")
            return 0
        p = git("push", REMOTE, f"HEAD:{BRANCH}")        # hooks run: marker + tree-writes
        if p.returncode != 0:
            log(f"PUSH REFUSED {local[:10]} (rc {p.returncode}): {(p.stderr or p.stdout).strip()[-400:]}")
            return 1
        log(f"pushed {remote[:10]}..{local[:10]} ({why})")
        return 0
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    a, b = "a" * 40, "b" * 40
    chk("a fast-forward on main pushes", decide("main", a, b, True)[0], True)
    chk("a diverged history is NOT pushed", decide("main", a, b, False)[0], False)
    chk("...and says it is left for a human", "never forced" in decide("main", a, b, False)[1], True)
    chk("another branch is not pushed", decide("feature", a, b, True)[0], False)
    chk("nothing new is not pushed", decide("main", a, a, True)[0], False)
    chk("no remote-tracking ref is not pushed", decide("main", a, None, False)[0], False)
    chk("the git dir resolves", os.path.isdir(git_dir()), True)
    print("auto_push selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
