#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""keep_account.py — run a gate check and KEEP its account when it fails.

    scripts/keep_account.py CMD [ARG...]      # exit status is CMD's (a signal death is 128+N)
    scripts/keep_account.py --selftest

⚑ WHY (W454, operator 2026-10-10: "A flake is a blocker"). paperkit runs a check with stdout
on DEVNULL and carries only the LAST LINE of stderr into its verdict, so a selftest that
printed `FAIL <arm>` on stdout reached the gate as `check FAILED for [@X]` and nothing else; the
replay then passed, and the failing run's account was gone. @WORKLIST, @CONFIG-REACH-SEES, @REGO
and @EBUILD each flaked that way and were re-diagnosed from nothing. This wraps the `tool` check
template (catalog/worklist/paper.toml): on a non-zero exit it writes the WHOLE merged output to
`/var/tmp/el-openglo-gate-accounts/<stamp>-<pid>.log` (outside the tree, never read by a gate) and prints the verdict lines
and then the log path on stderr, so the path is the line paperkit carries.

⚑ WEAKNESS, STATED. It keeps what the check printed; a check that printed nothing has an empty
account (the log says so). It adds one process per check. The log directory is never pruned here.
"""

import os
import signal
import subprocess
import sys
import tempfile
import time

# ⚑ A FIXED PLACE OUTSIDE THE TREE, not under ROOT: the gate runs checks from a snapshot of the
# staged tree that is deleted afterwards, and the first version wrote `.gate-accounts/` under
# the snapshot's root (2026-10-10: a @WORKLIST flake, no account found).
ACCOUNTS = "/var/tmp/el-openglo-gate-accounts"
VERDICT_WORDS = ("DENY", "REFUSED", "FAIL", "Traceback", "Error", "KILLED", "WITHHELD")
SHOWN = 6


def run(argv, accounts=ACCOUNTS):
    """Run argv; return its exit status, keeping the account (and printing it) on failure."""
    with tempfile.TemporaryFile() as out:
        proc = subprocess.run(argv, stdout=out, stderr=subprocess.STDOUT, check=False)
        out.seek(0)
        text = out.read().decode("utf-8", "replace")
    rc = proc.returncode
    if rc == 0:
        sys.stdout.write(text)
        return 0
    status = 128 - rc if rc < 0 else rc
    os.makedirs(accounts, exist_ok=True)
    path = os.path.join(accounts, f"{time.strftime('%Y%m%dT%H%M%S')}-{os.getpid()}.log")
    how = f"signal {signal.Signals(-rc).name}" if rc < 0 else f"exit {rc}"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(
            f"# {' '.join(argv)}\n# {how}\n{text or '# (the check printed nothing)\n'}"
        )
    lines = [ln for ln in text.splitlines() if any(w in ln for w in VERDICT_WORDS)]
    for ln in (lines or text.splitlines())[:SHOWN]:
        print(ln, file=sys.stderr)
    print(f"account kept ({how}): {path}", file=sys.stderr)
    return status


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    with tempfile.TemporaryDirectory() as td:
        chk(
            "a passing command exits 0, keeps nothing",
            (run(["true"], td), os.listdir(td)),
            (0, []),
        )
        rc = run([sys.executable, "-c", "print('FAIL arm 7'); raise SystemExit(3)"], td)
        logs = os.listdir(td)
        chk("a failing command passes its exit code through", rc, 3)
        chk("...and keeps exactly one account", len(logs), 1)
        with open(os.path.join(td, logs[0]), encoding="utf-8") as fh:
            chk(
                "...holding the stdout the gate would have dropped",
                "FAIL arm 7" in fh.read(),
                True,
            )
        rc = run(["sh", "-c", "kill -9 $$"], td)
        chk("a signal death is 128+N, never 0", rc, 137)
    print("keep_account selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    if not args or args[0].startswith("--"):
        print(
            "keep_account: REFUSED — usage: keep_account.py CMD [ARG...]",
            file=sys.stderr,
        )
        sys.exit(2)
    sys.exit(run(args))
