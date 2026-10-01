#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_hooks.py — the borrowed structural hooks pass their selftests HERE.

The hooks are symlinked from the repo they were written in.  A symlinked script
resolves its own root from `__file__`, so it reads THIS repo's files while its
code lives elsewhere — which is the whole reason it must be re-verified from
here rather than trusted because it passes upstream.

    scripts/check_hooks.py           # the verdict, as opa_gate hooks decides it
    scripts/check_hooks.py --json    # the measurement policy/hooks.rego decides
    scripts/check_hooks.py --list    # the hooks checked, and where each resolves,
                                     # then EVERY scripts/ symlink that resolves
                                     # outside the tree, n of m (W100)

⚑ THE HOOK ROSTER IS NOT THE BORROW.  HOOKS names the two hooks whose selftests
run here; the borrow is every scripts/ entry that is a symlink out of the tree
(six on 2026-09-27: the hooks, their tokenizer, ratchet, gate_ledger,
run_selftests). --list reports both, so a deletion (W99, W101) is witnessed as
the count falling rather than as a claim. WEAKNESS: one directory level only.

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


def borrowed(root=ROOT):
    """(entries, borrowed): every entry directly under root/scripts, and the
    [(name, target)] among them that are symlinks resolving outside root."""
    d = os.path.join(root, "scripts")
    names = sorted(os.listdir(d))
    real_root = os.path.realpath(root) + os.sep
    out = []
    for n in names:
        p = os.path.join(d, n)
        if os.path.islink(p):
            t = os.path.realpath(p)
            if not t.startswith(real_root):
                out.append((n, t))
    return names, out


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
        names, out = borrowed()
        if not names:
            print("check_hooks: REFUSED — scripts/ lists 0 entries; the census is broken", file=sys.stderr)
            return 1
        print(f"borrowed: {len(out)} of {len(names)} scripts/ entries are symlinks out of the tree")
        for n, t in out:
            print(f"  {n}\t{t}")
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
    # the census can SEE a borrow: plant one symlink out of a fake tree, one inside
    import tempfile
    with tempfile.TemporaryDirectory() as tree, tempfile.TemporaryDirectory() as away:
        os.makedirs(os.path.join(tree, "scripts"))
        open(os.path.join(tree, "scripts", "own.py"), "w").close()
        open(os.path.join(away, "far.py"), "w").close()
        os.symlink(os.path.join(away, "far.py"), os.path.join(tree, "scripts", "far.py"))
        os.symlink(os.path.join(tree, "scripts", "own.py"), os.path.join(tree, "scripts", "near.py"))
        names, out = borrowed(tree)
        got = (len(names), [n for n, _ in out])
    planted = got == (3, ["far.py"])
    print(f"  {'ok  ' if planted else 'FAIL'} a planted out-of-tree symlink is counted, an in-tree one is not (got {got})")
    ok = ok and planted
    print("check_hooks selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
