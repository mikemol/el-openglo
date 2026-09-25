#!/usr/bin/env python3
"""pre_push_local.py — what THIS repo requires before a push, beyond the shared hook.

⚑ WHY IT EXISTS (2026-09-25). The shared pre-push is now mtools'
`mikemol-githook-pre-push` (mtools ec71fe7). It reads git's stdin once, refuses
while a git operation is in flight, then runs `<toplevel>/.githooks/pre-push.local`
with the same args and stdin replayed. Two things moved onto THIS repo with it:

  1. THE POST-COMMIT MARKER. CLAUDE.md's commit policy: the post-commit hook
     amends each commit to fold in its advisory, and a tip WITHOUT
     `post-commit advisory (auto-captured)` must not be pushed — the amend had not
     landed. That check lived in substrate's shared body ("check 2") and LEFT it
     when the body moved to mtools; nothing enforced it here after that.
  2. THE TREE-WRITES GATE. Operator ruling 2026-09-23: scripts/check_tree_writes.py
     runs before each PUSH and each MERGE (~190 s CPU — not per commit). The merge
     half is .githooks/pre-merge-commit; the push half waited for exactly this
     extension point.

    .githooks/pre-push.local -> scripts/pre_push_local.py REMOTE URL   (stdin: git's ref lines)
    scripts/pre_push_local.py --selftest

A deleted ref (local sha all zeros) has no tip to check. Weakness: the marker is
checked on each pushed TIP, not on every commit in the range — the post-commit
hook amends the commit it just made, so the tip is where a missing amend shows.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKER = "post-commit advisory (auto-captured)"
ZERO = "0" * 40


def pushed_tips(stdin_text):
    """[(local_ref, local_sha)] for every ref git is pushing, deletions excluded.

    git's pre-push stdin: `<local ref> <local sha> <remote ref> <remote sha>` per line."""
    out = []
    for line in stdin_text.splitlines():
        parts = line.split()
        if len(parts) != 4:
            continue
        local_ref, local_sha = parts[0], parts[1]
        if local_sha.strip("0") == "":
            continue                          # a deletion: nothing to certify
        out.append((local_ref, local_sha))
    return out


def has_marker(message):
    return MARKER in message


def message_of(sha):
    return subprocess.run(["git", "-C", ROOT, "log", "-1", "--format=%B", sha],
                          capture_output=True, text=True, check=True).stdout


def main(argv):
    flags = [a for a in argv[1:] if a.startswith("--")]
    for a in flags:
        if a != "--selftest":
            print(f"pre_push_local: unknown flag {a!r}", file=sys.stderr)
            return 2
    tips = pushed_tips(sys.stdin.read())
    if not tips:
        print("pre_push_local: no ref with a tip is being pushed (deletions only); nothing to check")
        return 0
    missing = [(ref, sha) for ref, sha in tips if not has_marker(message_of(sha))]
    if missing:
        for ref, sha in missing:
            print(f"pre-push: REFUSED — {ref} tip {sha[:10]} has no '{MARKER}' marker: the "
                  f"post-commit amend has not landed. Wait for it (CLAUDE.md commit policy).",
                  file=sys.stderr)
        return 1
    print(f"pre-push: {len(tips)} of {len(tips)} pushed tip(s) carry the post-commit marker")
    # the operator's ruling: no gated check writes the tree — checked before each push
    runner = [os.path.join(ROOT, ".venv", "bin", "python3")]
    if not os.path.isfile(runner[0]):
        runner = [sys.executable]
    r = subprocess.run(runner + [os.path.join(ROOT, "scripts", "opa_gate.py"), "tree_writes"], cwd=ROOT)
    if r.returncode != 0:
        print("pre-push: REFUSED — a gated check writes a tracked file (W68); "
              "run scripts/check_tree_writes.py --list, fix the writer, then push", file=sys.stderr)
        return 1
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    a, b = "a" * 40, "b" * 40
    chk("a pushed ref's tip is read from git's stdin line",
        pushed_tips(f"refs/heads/main {a} refs/heads/main {b}\n"), [("refs/heads/main", a)])
    chk("a deletion (all-zero local sha) is not a tip to check",
        pushed_tips(f"(delete) {ZERO} refs/heads/old {b}\n"), [])
    chk("a malformed line is ignored, not guessed at", pushed_tips("garbage\n"), [])
    # ⚑ THE CHECK CAN SEE A MISSING MARKER — the case this exists for
    chk("a message with the marker passes", has_marker(f"subject\n\n── {MARKER} ──\n"), True)
    chk("a message WITHOUT the marker is seen", has_marker("subject\n\nbody, no amend yet\n"), False)
    # and on the real repo: HEAD's own message is readable (the amend normally carries it)
    chk("HEAD's message is readable from git", len(message_of("HEAD")) > 0, True)
    print("pre_push_local selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
