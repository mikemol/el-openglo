#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_gate_accounts.py - which kept account belongs to which gate check (W212, under W454).

keep_account.py writes the whole output of every FAILING gate check to
/var/tmp/el-openglo-gate-accounts/<stamp>-<pid>.log, headed by the command and its exit. A flake
that passes on replay still left the account of its FIRST failure there, but the directory holds
hundreds of logs, and finding one meant reading them by hand. This asks the directory instead.

    scripts/check_gate_accounts.py --list [NEEDLE]   # newest first: path, exit, command; n of m
    scripts/check_gate_accounts.py --selftest

NEEDLE is a substring of the command (`emitters_run`, `action_key`); no needle lists every account.

WEAKNESS. It reads only the two header lines keep_account wrote, so an account written by anything
else, or truncated, is counted as unreadable and listed apart, never matched. The stamp is the
local time of the process that wrote it (the gate's clock may differ from the shell's), so order
is by stamp text, not by an absolute time. An empty directory is refused: the search is broken.
"""

import os
import sys

ACCOUNTS = "/var/tmp/el-openglo-gate-accounts"


def header(path):
    """(command, how) from an account's first two lines, or None when it is not an account."""
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            first, second = fh.readline(), fh.readline()
    except OSError:
        return None
    if not (first.startswith("# ") and second.startswith("# ")):
        return None
    return first[2:].strip(), second[2:].strip()


def scan(directory=ACCOUNTS):
    """([(name, command, how)] newest stamp first, [name] of unreadable files) over `directory`."""
    logs = (n for n in os.listdir(directory) if n.endswith(".log"))
    rows, unreadable = [], []
    for name in sorted(logs, reverse=True):
        got = header(os.path.join(directory, name))
        if got is None:
            unreadable.append(name)
        else:
            rows.append((name, got[0], got[1]))
    return rows, unreadable


def matching(rows, needle):
    """The rows whose command contains `needle` (every row when it is empty)."""
    return [r for r in rows if needle in r[1]]


def main(argv):
    args = argv[1:]
    if args[:1] != ["--list"] or len(args) > 2:
        print(f"check_gate_accounts: unknown arguments {args!r}", file=sys.stderr)
        return 2
    if not os.path.isdir(ACCOUNTS) or not os.listdir(ACCOUNTS):
        print(f"check_gate_accounts: {ACCOUNTS} holds no account", file=sys.stderr)
        return 2
    rows, unreadable = scan()
    hits = matching(rows, args[1] if len(args) == 2 else "")
    for name, command, how in hits:
        print(f"{os.path.join(ACCOUNTS, name)}\t{how}\t{command}")
    print(
        f"check_gate_accounts: {len(hits)} of {len(rows)} readable account(s) match; "
        f"{len(unreadable)} unreadable",
        file=sys.stderr,
    )
    return 0


def _selftest():
    import tempfile

    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    emit = "# python3 ../../scripts/opa_gate.py emitters_run\n"
    files = {
        "20261018T100000-1.log": emit + "# exit 1\nboom\n",
        "20261018T110000-2.log": "# python3 ../../scripts/opa_gate.py action_key\n# exit 1\nx\n",
        "20261018T120000-3.log": emit + "# signal SIGKILL\n",
        "20261018T130000-4.log": "not an account\n",
    }
    with tempfile.TemporaryDirectory() as td:
        for name, text in files.items():
            with open(os.path.join(td, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        rows, unreadable = scan(td)
        chk(
            "readable accounts are newest stamp first",
            [r[0][9:15] for r in rows],
            ["120000", "110000", "100000"],
        )
        chk(
            "a file that is not an account is listed apart, never matched",
            unreadable,
            ["20261018T130000-4.log"],
        )
        chk(
            "a needle keeps the accounts of one check, with how each ended",
            [(r[0][9:15], r[2]) for r in matching(rows, "emitters_run")],
            [("120000", "signal SIGKILL"), ("100000", "exit 1")],
        )
        chk("no needle matches every readable account", len(matching(rows, "")), 3)
        chk("a needle nothing matches is empty", matching(rows, "no_such_check"), [])
    chk("an unknown flag is refused (2)", main(["x", "--bogus"]), 2)
    print("check_gate_accounts selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
