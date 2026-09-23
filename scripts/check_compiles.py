#!/usr/bin/env python3
"""check_compiles.py — every generator in the tree byte-compiles.

    scripts/check_compiles.py           # exit 0 iff all compile; else list failures
    scripts/check_compiles.py --list    # the files checked, one per line

⚑ THIS IS A WEAK WITNESS AND SAYS SO.  Eight recovered files are at an
INTERMEDIATE state (a later edit's anchor was not found during replay) and all
of them compile.  Compiling proves the syntax survived the recovery; it proves
nothing about behaviour.  The partial-file record is a SEPARATE claim for
exactly that reason — see check_partial.py.

⚑ n OF m, NEVER A BARE COUNT.  An empty corpus and a fully-passing one must not
print the same thing, or a glob that silently matches nothing reads as success.
"""
import os
import py_compile
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "__pycache__", ".venv", "catalog"}


def sources():
    """Every TRACKED .py except tooling's own (scripts/) and the catalog.

    ⚑ THE POPULATION COMES FROM git, NOT FROM THE DISK (2026-09-23). An os.walk
    of ROOT descended into .claude/worktrees/ — agents' private checkouts — and
    compiled a dangling symlink an agent's worktree had under .build/, failing
    the gate on a file that is not in this tree at all. Whatever else lives in
    the directory (worktrees, .build, .tree-writes, .ebuild-witness scratch) is
    not the tree; `git ls-files` is. A new file is checked once it is staged,
    which is exactly when a commit is about to certify it."""
    import subprocess
    r = subprocess.run(["git", "-C", ROOT, "ls-files", "-z", "--", "*.py"],
                       capture_output=True, check=True)
    out = []
    for rel in r.stdout.decode("utf-8").split("\0"):
        if not rel or rel.startswith("scripts/"):
            continue
        if rel.split("/", 1)[0] in SKIP_DIRS:
            continue
        out.append(rel.replace("/", os.sep))
    return sorted(out)


def main(argv):
    known = {"--list"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_compiles: unknown flag {a!r}", file=sys.stderr)
            return 2
    src = sources()
    if "--list" in argv:
        print("\n".join(src))
        return 0
    if not src:
        print("check_compiles: REFUSED — no sources found; the search is broken, "
              "not the tree clean", file=sys.stderr)
        return 2
    bad = []
    for rel in src:
        try:
            py_compile.compile(os.path.join(ROOT, rel), doraise=True, quiet=2)
        except py_compile.PyCompileError as e:
            bad.append((rel, str(e).strip().splitlines()[-1]))
    if bad:
        print(f"check_compiles: REFUSED — {len(bad)} of {len(src)} failed to compile:",
              file=sys.stderr)
        for rel, msg in bad:
            print(f"    {rel}: {msg}", file=sys.stderr)
        return 1
    print(f"check_compiles: {len(src)} of {len(src)} compile")
    return 0


def _selftest():
    ok = True
    src = sources()
    if not src:
        print("  FAIL sources() found nothing")
        ok = False
    else:
        print(f"  ok   sources() found {len(src)} file(s)")
    if any(s.startswith("scripts" + os.sep) for s in src):
        print("  FAIL sources() includes the checkers themselves")
        ok = False
    else:
        print("  ok   sources() excludes scripts/")
    print("check_compiles selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
