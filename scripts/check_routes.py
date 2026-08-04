#!/usr/bin/env python3
"""check_routes.py — the structural-query hook reads a routing table of OUR own.

THE MEASURED FAILURE THIS EXISTS FOR.  The structural-query hook does not hold
its routing map; it PARSES it out of the struct-tools skill at run time, so
adding a row teaches the hook with no code change.  Resolve the hook's root from
`__file__` and symlink it into a repo with no such skill, and the table comes
back EMPTY — the hook then still fires, still refuses, and names no tool.  It
degrades to a contentless "don't" instead of failing loudly.  Verified by
experiment before the hook was adopted here.

So: a non-empty table is a claim in its own right, separate from the hook's
selftest passing.

    scripts/check_routes.py            # exit 0 iff the local table has rows
    scripts/check_routes.py --routes   # the rows, as the hook sees them
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "scripts", "hook_structural_query.py")
SKILL = os.path.join(ROOT, ".claude", "skills", "struct-tools", "SKILL.md")


def routes():
    """The hook's own view of its table (ask the tool, never re-parse the skill)."""
    if not os.path.exists(HOOK):
        return None
    r = subprocess.run([sys.executable, HOOK, "--routes"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def main(argv):
    known = {"--routes"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_routes: unknown flag {a!r}", file=sys.stderr)
            return 2
    if not os.path.exists(HOOK):
        print("check_routes: REFUSED — the structural-query hook is not installed",
              file=sys.stderr)
        return 1
    if not os.path.exists(SKILL):
        print(f"check_routes: REFUSED — no local routing table at "
              f"{os.path.relpath(SKILL, ROOT)}", file=sys.stderr)
        print("    The hook would parse an ABSENT file and fire with no tool named.",
              file=sys.stderr)
        return 1
    rs = routes()
    if "--routes" in argv:
        print("\n".join(rs or []))
        return 0
    if not rs:
        print("check_routes: REFUSED — the hook reports an EMPTY routing table",
              file=sys.stderr)
        print("    It would refuse textual queries without naming the owning tool.",
              file=sys.stderr)
        return 1
    print(f"check_routes: the local routing table has {len(rs)} row(s)")
    return 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # The paths this reasons about must be the ones the hook actually uses.
    check("SKILL path is repo-local", SKILL.startswith(ROOT), True)
    check("HOOK path is repo-local", HOOK.startswith(ROOT), True)
    print("check_routes selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
