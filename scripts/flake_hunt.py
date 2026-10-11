#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""flake_hunt.py — run a gate check many times and KEEP the first failing run's account.

⚑ WHY (operator, 2026-10-10: "A flake is a blocker"). The gate's replay prints only the REPLAY's
output when a check fails once and passes on retry, so the failing run's account is lost every
time, and the flake is re-diagnosed from nothing: @EBUILD (W212), then on 2026-10-10 @REGO
(`opa_gate.py --test`), @WORKLIST (`worklist_gate.py --selftest`) and @CONFIG-REACH-SEES, each
passing on replay. A flake cannot be root-caused from its passes. This runs the check N times,
J at a time (J > 1 reproduces the CONTENTION the gate runs under), each run under the gate's own
limits (paperkit's clean environment and RLIMIT_CPU), captures EVERY run, and prints the failing
runs' verdict lines, so the evidence exists the first time it fails.

    scripts/flake_hunt.py --key REGO -n 30 -j 4         # a warrant of catalog/worklist/warrants.bib
    scripts/flake_hunt.py -n 20 -j 1 -- python3 scripts/check_symbol.py --regressions
    scripts/flake_hunt.py --selftest

Times are CPU seconds (user + sys of the child, from wait4) and wall seconds, each labelled: they
are different quantities, and a CPU-cap kill (SIGXCPU, SIGKILL) is a COST, not a flake.

⚑ WEAKNESSES, STATED. (1) It reproduces what contention it is given: a flake that needs the
whole gate's load, or a specific peer process, may not show at J = 4; raise J, or run the hunt
beside the gate. (2) `n of m` bounds the flake rate from above only: 0 of 30 is not "fixed", it is
"30 consecutive passes under THIS contention", which is the bar W454 states. (3) Without paperkit
importable the runs use the plain environment and say so (a SKIP of the limits, counted).
"""

import os
import signal
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

BIB = os.path.join(ROOT, "catalog", "worklist", "warrants.bib")
PROJ = os.path.join(ROOT, "catalog", "worklist")
VERDICT_WORDS = ("DENY", "REFUSED", "FAIL", "Traceback", "Error", "KILLED", "killed")


def limits():
    """(env, cpu, note): the gate's own limits when paperkit is importable, else plain."""
    try:
        from paperkit import resolver as PKR
    except ImportError:
        return (
            None,
            None,
            "paperkit not importable: runs use the plain environment and no CPU cap",
        )
    cpu = int(os.environ.get("PAPERKIT_CHECK_CPU", PKR.CHECK_CPU))
    return PKR.clean_env(), cpu, f"paperkit's clean env and RLIMIT_CPU {cpu} s"


def run_one(cmd, cwd, env, cpu, shell):
    """One run: (rc, signal-or-None, cpu_s, wall_s, output lines). The CPU cap is set by
    qt_sandbox's launcher (a child that sets its own limits and execs), never a preexec_fn:
    that is unsafe under threads, and these runs are threaded."""
    import qt_sandbox as QT

    started = time.monotonic()
    argv = ["sh", "-c", cmd] if shell else list(cmd)
    with tempfile.TemporaryFile() as out:
        proc = subprocess.Popen(
            QT.launch_argv(argv, cpu=cpu),
            cwd=cwd,
            env=env,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        _pid, status, rusage = os.wait4(proc.pid, 0)
        proc.returncode = 0  # reaped by wait4; the status below is authoritative
        wall = time.monotonic() - started
        out.seek(0)
        lines = out.read().decode("utf-8", "replace").splitlines()
    sig = os.WTERMSIG(status) if os.WIFSIGNALED(status) else None
    rc = -sig if sig is not None else os.WEXITSTATUS(status)
    return rc, sig, rusage.ru_utime + rusage.ru_stime, wall, lines


def resolve_key(key):
    """(cmd, cwd) of warrant `key` of catalog/worklist/warrants.bib, by the gate's own reader."""
    import tomllib

    import worklist_gate

    recs = worklist_gate.warrants(BIB)
    if recs is None:
        raise SystemExit(
            "flake_hunt: REFUSED — paperkit is not importable; cannot read the warrants"
        )
    if key not in recs:
        raise SystemExit(f"flake_hunt: REFUSED — no warrant {key!r} in {BIB}")
    check = recs[key].get("check")
    if not isinstance(check, str) or ":" not in check:
        raise SystemExit(
            f"flake_hunt: REFUSED — warrant {key} has no `kind:target` check ({check!r})"
        )
    kind, target = check.split(":", 1)
    with open(os.path.join(PROJ, "paper.toml"), "rb") as fh:
        tmpl = tomllib.load(fh).get("checks", {}).get(kind, {}).get("cmd")
    if not tmpl:
        raise SystemExit(
            f"flake_hunt: REFUSED — paper.toml declares no `{kind}` check type"
        )
    return tmpl.replace("{target}", target.strip()), PROJ


def hunt(cmd, cwd, n, jobs, shell):
    """The measurement: every run's record, in order."""
    if n < 1 or jobs < 1:
        raise SystemExit("flake_hunt: REFUSED — n and j must be at least 1")
    if not cmd:
        raise SystemExit("flake_hunt: REFUSED — no command: the population is empty")
    env, cpu, note = limits()
    with ThreadPoolExecutor(max_workers=jobs) as ex:
        runs = list(ex.map(lambda _i: run_one(cmd, cwd, env, cpu, shell), range(n)))
    return runs, note


def report(runs, note, jobs):
    """Print the n-of-m and every failing run's account; return the exit code."""
    failed = [(i, r) for i, r in enumerate(runs) if r[0] != 0]
    cpus = sorted(r[2] for r in runs)
    print(f"flake_hunt: {len(failed)} of {len(runs)} runs FAILED at j={jobs} ({note})")
    print(
        f"  cpu seconds (user+sys): min {cpus[0]:.1f} median {cpus[len(cpus) // 2]:.1f} "
        f"max {cpus[-1]:.1f}; wall seconds of the slowest: {max(r[3] for r in runs):.1f}"
    )
    for i, (rc, sig, cpu, wall, lines) in failed:
        how = f"signal {signal.Signals(sig).name}" if sig else f"exit {rc}"
        print(f"  run {i + 1}: {how}, cpu {cpu:.1f} s, wall {wall:.1f} s")
        verdicts = [ln for ln in lines if any(w in ln for w in VERDICT_WORDS)]
        for ln in verdicts[:8] or lines[-8:]:
            print(f"      {ln}")
        print(f"      ({len(lines)} line(s) captured)")
    return 1 if failed else 0


def main(argv):
    args = argv[1:]
    n, jobs, key, cmd = 20, 1, None, []
    known = {"-n", "-j", "--key", "--selftest", "--"}
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--":
            cmd = args[i + 1 :]
            break
        if a not in known:
            print(f"flake_hunt: unknown flag {a!r}", file=sys.stderr)
            return 2
        if a == "--selftest":
            i += 1
            continue
        if i + 1 >= len(args):
            print(f"flake_hunt: {a} needs a value", file=sys.stderr)
            return 2
        v = args[i + 1]
        if a == "-n":
            n = int(v)
        elif a == "-j":
            jobs = int(v)
        else:
            key = v
        i += 2
    if key is not None:
        text, cwd = resolve_key(key)
        runs, note = hunt(text, cwd, n, jobs, True)
    else:
        runs, note = hunt(cmd, ROOT, n, jobs, False)
    return report(runs, note, jobs)


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    runs, _note = hunt(["true"], ROOT, 4, 2, False)
    chk("a stable command passes every run", [r[0] for r in runs], [0, 0, 0, 0])
    with tempfile.TemporaryDirectory() as td:
        counter = os.path.join(td, "n")
        with open(counter, "w", encoding="utf-8") as fh:
            fh.write("0")
        flaky = (
            f"n=$(cat {counter}); echo $((n+1)) > {counter}; "
            f'if [ $((n % 3)) -eq 2 ]; then echo "DENY: planted flake on run $n"; exit 1; fi'
        )
        runs, _note = hunt(flaky, ROOT, 6, 1, True)
        chk(
            "a flake that fails every third run is seen",
            [r[0] != 0 for r in runs],
            [False, False, True, False, False, True],
        )
        chk(
            "its failing run's account is KEPT",
            [ln for ln in runs[2][4] if "DENY" in ln],
            ["DENY: planted flake on run 2"],
        )
    killed, _note = hunt("kill -9 $$", ROOT, 1, 1, True)
    chk(
        "a child killed by a signal is named as one (negative rc, signal set)",
        (killed[0][0], killed[0][1]),
        (-9, 9),
    )
    for bad in ((["true"], 0, 1), ([], 1, 1), (["true"], 1, 0)):
        try:
            hunt(bad[0], ROOT, bad[1], bad[2], False)
            refused = False
        except SystemExit:
            refused = True
        chk(
            f"an empty population or n or j below 1 is REFUSED ({bad[1:]!r})",
            refused,
            True,
        )
    print("flake_hunt selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv[: sys.argv.index("--") if "--" in sys.argv else None]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
