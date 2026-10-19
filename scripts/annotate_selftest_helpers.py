#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""annotate_selftest_helpers.py — annotate the nested selftest helpers chk and check (W750, under W743)

Nearly every check script defines, inside its selftest, a helper
`def chk(label, got, want):` (or `check`) and calls it a dozen times. Untyped, each call is
a house finding; typing_census --callees measured chk at 954 and check at 572 of the repo's
6884 no-untyped-call findings. The two share one signature, so one AST codemod annotates them:

    def chk(label: str, got: object, want: object) -> None:

    scripts/annotate_selftest_helpers.py           # dry run: the plan per file, then n of m
    scripts/annotate_selftest_helpers.py --write   # write each file, kept only if pycheck admits it
    scripts/annotate_selftest_helpers.py --selftest

The population is git's tracked *.py. A helper is planned only when its AST arguments are exactly
(label, got, want) with no annotation and no return type, AND its header line holds the unannotated
text once, so the edit is a replacement of that fragment on that line and never a pattern over the
file. A helper whose header is split over lines is listed as UNPLANNABLE, not guessed at.

⚑ WEAKNESS, STATED. It does not prove the body type-checks as annotated: that is mikemol-pycheck's
verdict (--write keeps a file only if pycheck --check-file admits it and restores it otherwise).
The signature says `object` for got and want, which is what every call site passes (any value);
a helper that does arithmetic on them would be refused by pycheck, not rewritten.
"""

import ast
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAMES = ("chk", "check")
ARGS = ["label", "got", "want"]
OLD = "(label, got, want):"
NEW = "(label: str, got: object, want: object) -> None:"
PYCHECK = os.path.join(ROOT, ".venv", "bin", "mikemol-pycheck")


def helpers(source):
    """([line numbers planned], [line numbers unplannable]) for the helpers in one source text."""
    lines = source.splitlines()
    planned, unplannable = [], []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.FunctionDef) or node.name not in NAMES:
            continue
        if [a.arg for a in node.args.args] != ARGS or node.returns is not None:
            continue
        if any(a.annotation is not None for a in node.args.args):
            continue
        header = lines[node.lineno - 1]
        if header.count(OLD) == 1 and header.rstrip().endswith(":"):
            planned.append(node.lineno)
        else:
            unplannable.append(node.lineno)
    return sorted(planned), sorted(unplannable)


def rewrite(source, planned):
    """The source with each planned header line annotated; every other line is untouched."""
    lines = source.splitlines(keepends=True)
    for number in planned:
        lines[number - 1] = lines[number - 1].replace(OLD, NEW, 1)
    return "".join(lines)


def admitted(path):
    """True when mikemol-pycheck --check-file admits the file as it now stands."""
    done = subprocess.run(
        [PYCHECK, "--check-file", path], capture_output=True, text=True, check=False
    )
    return done.returncode == 0


def tracked():
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import git_tracked

    return git_tracked.files("*.py", root=ROOT)


def main(argv):
    known = {"--write"}
    for a in argv[1:]:
        if a not in known:
            print(f"annotate_selftest_helpers: unknown flag {a!r}", file=sys.stderr)
            return 2
    write = "--write" in argv
    files = tracked()
    if not files:
        print("annotate_selftest_helpers: REFUSED, 0 tracked files", file=sys.stderr)
        return 2
    planned_files = kept = refused = unplannable_total = 0
    for rel in files:
        path = os.path.join(ROOT, rel)
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        planned, unplannable = helpers(source)
        unplannable_total += len(unplannable)
        for number in unplannable:
            print(f"UNPLANNABLE {rel}:{number}")
        if not planned:
            continue
        planned_files += 1
        print(f"PLAN {rel}: {len(planned)} helper(s) at line(s) {planned}")
        if not write:
            continue
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(rewrite(source, planned))
        if admitted(path):
            kept += 1
        else:
            refused += 1
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(source)
            print(f"REFUSED {rel}: pycheck does not admit it annotated; restored")
    print(
        f"annotate_selftest_helpers: {planned_files} of {len(files)} file(s) hold a plannable helper"
        + (f"; wrote {kept}, refused {refused}" if write else "")
        + f"; {unplannable_total} unplannable"
    )
    return 0


def _selftest():
    ok = True

    def check(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}")
        ok = ok and got == want

    src = (
        "def f():\n"
        "    def chk(label, got, want):\n"
        "        pass\n"
        "    def check(label, got, want):\n"
        "        pass\n"
        "    def other(label, got, want):\n"
        "        pass\n"
    )
    planned, unplannable = helpers(src)
    check("both helper names are planned, another name is not", planned, [2, 4])
    check("nothing is unplannable here", unplannable, [])
    out = rewrite(src, planned)
    check(
        "the header is annotated and nothing else changes",
        out.splitlines()[1],
        "    def chk(label: str, got: object, want: object) -> None:",
    )
    check("an unrelated def is untouched", out.splitlines()[5], src.splitlines()[5])
    done = "def chk(label: str, got: object, want: object) -> None:\n    pass\n"
    check("an annotated helper is not planned again", helpers(done), ([], []))
    split = "def chk(label, got,\n        want):\n    pass\n"
    check(
        "a header split over lines is unplannable, not guessed",
        helpers(split),
        ([], [1]),
    )
    check("this file's own tracked population is non-empty", len(tracked()) > 0, True)
    print("annotate_selftest_helpers selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
