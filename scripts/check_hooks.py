#!/usr/bin/env python3
"""check_hooks.py — the borrowed structural hooks pass their selftests HERE.

The hooks are symlinked from the repo they were written in.  A symlinked script
resolves its own root from `__file__`, so it reads THIS repo's files while its
code lives elsewhere — which is the whole reason it must be re-verified from
here rather than trusted because it passes upstream.

    scripts/check_hooks.py           # the verdict, as opa_gate hooks decides it
    scripts/check_hooks.py --json    # the measurement policy/hooks.rego decides
    scripts/check_hooks.py --list    # the hooks checked, and where each resolves

⚑ A MISSING HOOK IS A FAILURE, NOT A SKIP.  If the symlink is dangling or the
upstream file moved, the honest report is red: a check that quietly passes when
its subject is absent measures nothing.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = ("hook_no_chaining.py", "hook_structural_query.py")


def measure(hooks=HOOKS):
    """The MEASUREMENT policy/hooks.rego decides (W50): per borrowed hook, whether
    it resolves here, where, and its --selftest exit code and last output line
    run FROM THIS REPO. An absent hook and a failing selftest are defects by the
    policy's ruling (H1, H2), not here."""
    cases = []
    for h in hooks:
        p = os.path.join(ROOT, "scripts", h)
        if not os.path.exists(p):
            cases.append({"hook": h, "present": False, "resolves": None, "rc": None, "tail": ""})
            continue
        r = subprocess.run([sys.executable, p, "--selftest"],
                           capture_output=True, text=True, cwd=ROOT)
        tail = (r.stdout + r.stderr).strip().splitlines()
        cases.append({"hook": h, "present": True, "resolves": os.path.realpath(p),
                      "rc": r.returncode, "tail": tail[-1] if tail else ""})
    return {"cases": cases}


def main(argv):
    known = {"--list", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_hooks: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--list" in argv:
        for h in HOOKS:
            p = os.path.join(ROOT, "scripts", h)
            where = os.path.realpath(p) if os.path.exists(p) else "(ABSENT)"
            print(f"{h}\t{where}")
        return 0
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("hooks")


def _selftest():
    """The measurement can SEE an absent hook (the dangling-symlink case the
    docstring names); policy/hooks_test.rego holds that it is a defect (W50)."""
    ok = len(HOOKS) > 0
    print(f"  {'ok  ' if ok else 'FAIL'} roster is non-empty")
    seen = measure(("hook_that_does_not_exist.py",))["cases"][0]["present"] is False
    print(f"  {'ok  ' if seen else 'FAIL'} an absent hook is measured as absent")
    ok = ok and seen
    print("check_hooks selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
