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
selftest passing.  The requirement is policy/routes.rego (decided by
scripts/opa_gate.py routes); this file MEASURES: is the hook installed, is the
local skill present, and which rows does the hook itself report.

    scripts/check_routes.py            # the verdict, as opa_gate routes decides it
    scripts/check_routes.py --json     # the measurement policy/routes.rego decides
    scripts/check_routes.py --routes   # the rows, as the hook sees them
    scripts/check_routes.py --selftest

Weakness: it counts rows; it does not check a row names a tool that exists.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "scripts", "hook_structural_query.py")
SKILL = os.path.join(ROOT, ".claude", "skills", "struct-tools", "SKILL.md")


def routes(hook=HOOK):
    """The hook's own view of its table (ask the tool, never re-parse the skill)."""
    if not os.path.exists(hook):
        return None
    r = subprocess.run([sys.executable, hook, "--routes"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


def measure(hook=HOOK, skill=SKILL):
    return {"hook": os.path.relpath(hook, ROOT), "hook_present": os.path.exists(hook),
            "skill": os.path.relpath(skill, ROOT), "skill_present": os.path.exists(skill),
            "cases": [{"row": r} for r in (routes(hook) or [])]}


def main(argv):
    known = {"--routes", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_routes: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--routes" in argv:
        print("\n".join(routes() or []))
        return 0
    import opa_gate
    return opa_gate.gate("routes")


def _selftest():
    """The measurement can SEE the table, and can SEE a hook that is not there."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    check("SKILL path is repo-local", SKILL.startswith(ROOT), True)
    check("HOOK path is repo-local", HOOK.startswith(ROOT), True)
    gone = measure(hook=os.path.join(ROOT, "scripts", "no_such_hook.py"),
                   skill=os.path.join(ROOT, "no_such_skill.md"))
    check("an absent hook is SEEN, with no rows", (gone["hook_present"], gone["skill_present"], gone["cases"]),
          (False, False, []))
    check("the live hook reports rows", len(measure()["cases"]) > 0, True)
    print("check_routes selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
