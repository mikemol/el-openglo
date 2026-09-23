#!/usr/bin/env python3
"""check_compiles.py — every generator in the tree byte-compiles.

    scripts/check_compiles.py           # the verdict, as opa_gate compiles decides it
    scripts/check_compiles.py --json    # the measurement policy/compiles.rego decides
    scripts/check_compiles.py --list    # the files checked, one per line
    scripts/check_compiles.py --selftest

⚑ THIS IS A WEAK WITNESS AND SAYS SO.  Eight recovered files are at an
INTERMEDIATE state (a later edit's anchor was not found during replay) and all
of them compile.  Compiling proves the syntax survived the recovery; it proves
nothing about behaviour.  The partial-file record is a SEPARATE claim for
exactly that reason — see check_partial.py.

⚑ n OF m, NEVER A BARE COUNT.  An empty corpus and a fully-passing one must not
print the same thing, or a glob that silently matches nothing reads as success —
policy/compiles.rego's K0 denies the empty population (W50).
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
    not the tree; scripts/git_tracked.py is (and its bounded walk where there is
    no git — the Δ sandbox). A new file is checked once it is staged, which is
    exactly when a commit is about to certify it."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import git_tracked
    out = []
    for rel in git_tracked.files("*.py", root=ROOT):
        if rel.startswith("scripts/") or rel.split("/", 1)[0] in SKIP_DIRS:
            continue
        out.append(rel.replace("/", os.sep))
    return sorted(out)


def compile_error(path):
    """None when `path` byte-compiles, else the compiler's last line.

    ⚑ quiet=1, NEVER 2 (found by this file's first selftest arm that fed it a
    syntax error, W50 batch 5, 2026-09-23). py_compile raises under doraise ONLY
    when quiet < 2 — at quiet=2 it swallows the error and returns. The check
    shipped with `doraise=True, quiet=2`, so every source "compiled": its
    all-clear had never been shown to differ from its found-something."""
    try:
        py_compile.compile(path, doraise=True, quiet=1)
    except py_compile.PyCompileError as e:
        return str(e).strip().splitlines()[-1]
    return None


def measure(src=None):
    """The MEASUREMENT policy/compiles.rego decides: one case per tracked source,
    with the compiler's error or null. Whether an error is a defect is the
    policy's ruling, not this file's."""
    src = sources() if src is None else src
    return {"cases": [{"id": rel.replace(os.sep, "/"), "error": compile_error(os.path.join(ROOT, rel))}
                      for rel in src]}


def main(argv):
    known = {"--list", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_compiles: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--list" in argv:
        print("\n".join(sources()))
        return 0
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("compiles")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    src = sources()
    chk("sources() finds files", len(src) > 0, True)
    chk("sources() excludes the checkers themselves",
        [s for s in src if s.startswith("scripts" + os.sep)], [])
    # ⚑ THE MEASUREMENT MUST SEE A SYNTAX ERROR (synthetic: a scratch file). That
    # a case carrying one is DENIED is policy/compiles_test.rego's ruling.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        bad = os.path.join(td, "bad.py")
        with open(bad, "w", encoding="utf-8") as fh:
            fh.write("def f(:\n")
        chk("a syntax error is measured", compile_error(bad) is not None, True)
        good = os.path.join(td, "good.py")
        with open(good, "w", encoding="utf-8") as fh:
            fh.write("x = 1\n")
        chk("a clean file measures no error", compile_error(good), None)
    print("check_compiles selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
