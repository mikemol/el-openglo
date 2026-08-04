#!/usr/bin/env python3
"""check_hooks.py — the borrowed structural hooks pass their selftests HERE.

The hooks are symlinked from the repo they were written in.  A symlinked script
resolves its own root from `__file__`, so it reads THIS repo's files while its
code lives elsewhere — which is the whole reason it must be re-verified from
here rather than trusted because it passes upstream.

    scripts/check_hooks.py           # exit 0 iff every hook's selftest passes
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


def main(argv):
    known = {"--list"}
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
    bad = []
    for h in HOOKS:
        p = os.path.join(ROOT, "scripts", h)
        if not os.path.exists(p):
            bad.append((h, "absent (dangling symlink, or not installed yet)"))
            continue
        r = subprocess.run([sys.executable, p, "--selftest"],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            tail = (r.stdout + r.stderr).strip().splitlines()
            bad.append((h, tail[-1] if tail else f"exit {r.returncode}"))
    if bad:
        print(f"check_hooks: REFUSED — {len(bad)} of {len(HOOKS)} hook selftest(s) "
              f"did not pass:", file=sys.stderr)
        for h, why in bad:
            print(f"    {h}: {why}", file=sys.stderr)
        return 1
    print(f"check_hooks: {len(HOOKS)} of {len(HOOKS)} hook selftests pass from this repo")
    return 0


def _selftest():
    ok = len(HOOKS) > 0
    print(f"  {'ok  ' if ok else 'FAIL'} roster is non-empty")
    print("check_hooks selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
