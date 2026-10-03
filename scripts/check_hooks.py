#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_hooks.py — the PreToolUse hooks this repo runs behave correctly HERE.

⚑ THE ROSTER IS WHAT .claude/settings.json RUNS (W99, 2026-10-02). The hooks were
symlinks into substrate; they are now mtools' installed commands (mikemol-hooks in
the tooling extra), so the population is read from the settings file's PreToolUse
commands, not from scripts/. Each is measured by BEHAVIOUR, run from this repo:
it must DENY a known-bad event and ADMIT a known-good one (PROBES). An installed
command reads this repo's struct-tools table at run time, which is exactly what
must be re-verified here rather than trusted because it passes upstream.

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
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

# A hook sees a TOOL call, so a probe is a (tool_name, tool_input) event.
# _PROBE_PY is never written: the pycheck hook lints the payload it is handed.
_PROBE_PY = os.path.join(ROOT, "scripts", "_hook_probe.py")


def _bash(command):
    return ("Bash", {"command": command})


def _write_py(content):
    return ("Write", {"file_path": _PROBE_PY, "content": content})


# hook command basename -> (an event it must DENY, an event it must ADMIT)
PROBES = {
    "mikemol-hook-no-chaining": (_bash("ls a && ls b"), _bash("ls a")),
    "mikemol-hook-structural-query": (
        _bash("grep foo scripts/check_hooks.py"),
        _bash("ls scripts"),
    ),
    "mikemol-hook-no-verify": (
        _bash("git commit --no-verify -m probe"),
        _bash("git commit -m probe"),
    ),
    "mikemol-hook-shellcheck": (_bash("echo $unquoted"), _bash("ls scripts")),
    # a ruff finding (F401 unused import) is refused; a clean, formatted module is admitted
    "mikemol-hook-pycheck": (
        _write_py("import os\n"),
        _write_py("x = 1\n"),
    ),
}


def roster(settings=SETTINGS):
    """[(name, argv, env)] for every PreToolUse hook command in settings.json, whatever
    its matcher (a hook is measured by the probe PROBES declares for it).

    A command is `VAR=1 "$CLAUDE_PROJECT_DIR/path"`: leading assignments become env,
    $CLAUDE_PROJECT_DIR expands to this repo."""
    import json
    import shlex

    with open(settings, encoding="utf-8") as fh:
        doc = json.load(fh)
    out = []
    for block in doc.get("hooks", {}).get("PreToolUse", []):
        for h in block.get("hooks", []):
            words = shlex.split(
                h.get("command", "").replace("$CLAUDE_PROJECT_DIR", ROOT)
            )
            env = {}
            while words and "=" in words[0] and not words[0].startswith(("/", ".")):
                k, v = words.pop(0).split("=", 1)
                env[k] = v
            if words:
                out.append((os.path.basename(words[0]), words, env))
    return out


def _decision(argv, env, probe):
    """'deny' or 'allow' for one sample PreToolUse event (tool_name, tool_input), as the
    hook answers it."""
    import json

    tool, tool_input = probe
    event = json.dumps({"tool_name": tool, "tool_input": tool_input, "cwd": ROOT})
    r = subprocess.run(
        argv,
        input=event,
        capture_output=True,
        text=True,
        cwd=ROOT,
        env=dict(os.environ, **env),
        check=False,
    )
    try:
        d = (
            json.loads(r.stdout or "{}")
            .get("hookSpecificOutput", {})
            .get("permissionDecision")
        )
    except ValueError:
        d = None
    return d or ("deny" if r.returncode == 2 else "allow")


def measure(hooks=None):
    """The MEASUREMENT policy/hooks.rego decides (W50): per hook settings.json runs,
    whether its executable is present, and rc = 0 iff it denied its bad probe and
    admitted its good one, run FROM THIS REPO (tail says which probe misbehaved).
    An absent hook and a misbehaving one are defects by the policy (H1, H2).
    `unwired` lists every hook PROBES declares (the adopted set) that settings.json
    does not run: installed-but-not-wired was the adoption gap (W253), so it is a
    measured fact, not a remembered one (H4)."""
    cases = []
    for name, argv, env in hooks if hooks is not None else roster():
        if not os.path.isfile(argv[0]):
            cases.append(
                {
                    "hook": name,
                    "present": False,
                    "resolves": None,
                    "rc": None,
                    "tail": "",
                }
            )
            continue
        bad, good = PROBES.get(name, (None, None))
        if bad is None:
            cases.append(
                {
                    "hook": name,
                    "present": True,
                    "resolves": argv[0],
                    "rc": None,
                    "tail": "no probe declared for this hook",
                }
            )
            continue
        got = (_decision(argv, env, bad), _decision(argv, env, good))
        ok = got == ("deny", "allow")
        cases.append(
            {
                "hook": name,
                "present": True,
                "resolves": argv[0],
                "rc": 0 if ok else 1,
                "tail": f"bad probe -> {got[0]}, good probe -> {got[1]}",
            }
        )
    unwired = sorted(set(PROBES) - {c["hook"] for c in cases})
    return {"cases": cases, "unwired": unwired}


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
        for name, hargv, _env in roster():
            where = hargv[0] if os.path.isfile(hargv[0]) else "(ABSENT)"
            print(f"{name}\t{where}")
        names, out = borrowed()
        if not names:
            print(
                "check_hooks: REFUSED — scripts/ lists 0 entries; the census is broken",
                file=sys.stderr,
            )
            return 1
        print(
            f"borrowed: {len(out)} of {len(names)} scripts/ entries are symlinks out of the tree"
        )
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
    ok = len(roster()) > 0
    print(f"  {'ok  ' if ok else 'FAIL'} the settings.json roster is non-empty")
    seen = (
        measure([("ghost", ["/nonexistent/mikemol-hook-ghost"], {})])["cases"][0][
            "present"
        ]
        is False
    )
    print(f"  {'ok  ' if seen else 'FAIL'} an absent hook is measured as absent")
    ok = ok and seen
    # the probe can SEE a hook that admits everything: /bin/true never denies
    lax = measure([("mikemol-hook-no-chaining", ["/bin/true"], {})])["cases"][0]["rc"]
    print(
        f"  {'ok  ' if lax == 1 else 'FAIL'} a hook that never denies is measured as misbehaving (rc {lax})"
    )
    ok = ok and lax == 1
    # the adopted set can SEE an unwired hook: one wired hook leaves the others unwired
    unwired = measure([("mikemol-hook-no-chaining", ["/bin/true"], {})])["unwired"]
    seen_unwired = unwired == sorted(set(PROBES) - {"mikemol-hook-no-chaining"})
    print(
        f"  {'ok  ' if seen_unwired else 'FAIL'} an adopted hook missing from settings.json is measured as unwired ({len(unwired)} of {len(PROBES)})"
    )
    ok = ok and seen_unwired
    # the census can SEE a borrow: plant one symlink out of a fake tree, one inside
    import tempfile

    with tempfile.TemporaryDirectory() as tree, tempfile.TemporaryDirectory() as away:
        os.makedirs(os.path.join(tree, "scripts"))
        open(os.path.join(tree, "scripts", "own.py"), "w").close()
        open(os.path.join(away, "far.py"), "w").close()
        os.symlink(
            os.path.join(away, "far.py"), os.path.join(tree, "scripts", "far.py")
        )
        os.symlink(
            os.path.join(tree, "scripts", "own.py"),
            os.path.join(tree, "scripts", "near.py"),
        )
        names, out = borrowed(tree)
        got = (len(names), [n for n, _ in out])
    planted = got == (3, ["far.py"])
    print(
        f"  {'ok  ' if planted else 'FAIL'} a planted out-of-tree symlink is counted, an in-tree one is not (got {got})"
    )
    ok = ok and planted
    print("check_hooks selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
