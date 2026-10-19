#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""typing_sources.py — where do this repo's Any findings come from? (W671, under W553)

75 percent of the house-strict findings are `Expression has type "Any"` (disallow_any_expr). An Any enters at a
BOUNDARY (json.loads, a subprocess read, an untyped library call) and then spreads through every expression that
touches it, so a few typed boundaries clear findings in bulk. This reads the SOURCE LINE of every such finding
(from scripts/typing_census.py's distinct findings) and counts the calls named on it, so the boundaries that
carry the most findings are the ones named first.

    scripts/typing_sources.py            # the 30 call names on the most Any-finding lines, and the files
    scripts/typing_sources.py --selftest

⚑ WEAKNESS, STATED. A call named on an Any line is a CANDIDATE source, not a proof: the line may only USE a value
that became Any earlier. The count says where the Any is TOUCHED most, which is where a typed boundary pays most;
which call is the root has to be read in the file. A line mypy reports may be a continuation of a longer
statement, so the call can sit on a neighbouring line.
"""

import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, str(ROOT / "scripts"))

CALL = re.compile(r"([A-Za-z_][A-Za-z0-9_.]*)\(")
KEYWORDS = frozenset(
    {
        "if",
        "for",
        "while",
        "and",
        "or",
        "not",
        "in",
        "is",
        "return",
        "print",
        "len",
        "str",
        "int",
        "list",
    }
)
TOP = 30


def call_names(text):
    """The distinct call names on one source line, builtins that never introduce an Any left out."""
    return {m for m in CALL.findall(text) if m not in KEYWORDS}


def sources(records, read_line):
    """(by_call, by_file, n): over the Any findings in `records` ((file, line, column, code, message) tuples),
    the calls named on their source lines and the files, and how many findings were read."""
    by_call, by_file, n = Counter(), Counter(), 0
    for path, line, _col, code, message in records:
        if code != "misc" or "Any" not in message:
            continue
        n += 1
        by_file[path] += 1
        text = read_line(path, line)
        for name in call_names(text):
            by_call[name] += 1
    return by_call, by_file, n


def reader(root):
    cache = {}

    def read_line(path, line):
        if path not in cache:
            cache[path] = (root / path).read_text(encoding="utf-8").splitlines()
        lines = cache[path]
        return (
            lines[line - 1] if isinstance(line, int) and 0 < line <= len(lines) else ""
        )

    return read_line


def main(argv):
    if argv[1:] != []:
        print(f"typing_sources: unknown arguments {argv[1:]!r}", file=sys.stderr)
        return 2
    import typing_census

    files, withheld, _passes, records = typing_census.census()
    if not records:
        print(
            "typing_sources: the census found no finding; the search is broken",
            file=sys.stderr,
        )
        return 2
    by_call, by_file, n = sources(records, reader(ROOT))
    for name, count in by_call.most_common(TOP):
        print(f"call\t{count}\t{name}")
    for path, count in by_file.most_common(TOP):
        print(f"file\t{count}\t{path}")
    print(
        f"typing_sources: {n} of {len(records)} finding(s) are Any expressions, over {len(by_file)} of {len(files)} file(s); "
        f"{len(withheld)} pass(es) withheld",
        file=sys.stderr,
    )
    return 3 if withheld else 0


def _selftest():
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk(
        "call names: a method call keeps its dotted name, a builtin that adds no Any is dropped",
        call_names("rows = json.loads(read_text(p)) if len(x) else None"),
        {"json.loads", "read_text"},
    )
    lines = {
        ("a.py", 1): "x = json.loads(s)",
        ("a.py", 2): "y = json.loads(t) + get(x)",
        ("b.py", 5): "z = other(1)",
    }
    records = [
        ("a.py", 1, 0, "misc", 'Expression has type "Any"'),
        ("a.py", 2, 0, "misc", 'Expression type contains "Any" (has type "set[Any]")'),
        ("b.py", 5, 0, "no-untyped-call", "Call to untyped function"),
        ("b.py", 5, 0, "misc", "Generator has incompatible item type"),
    ]
    by_call, by_file, n = sources(records, lambda p, ln: lines.get((p, ln), ""))
    chk("only the misc findings that mention Any are read", n, 2)
    chk("a call named on two Any lines counts twice", by_call["json.loads"], 2)
    chk("the files carry their Any counts", dict(by_file), {"a.py": 2})
    chk(
        "a line past the file is an empty read, not a crash",
        reader(ROOT)("scripts/typing_sources.py", 99999),
        "",
    )
    print("typing_sources selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
