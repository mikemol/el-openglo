#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""census_compare.py — do the two house typing censuses agree? (W687, under W553)

mtools ships `mikemol-pycheck --census ROOT --house` (mtools W1512); this repo's own
measure is `scripts/typing_census.py --json`. Both count mypy findings per file under the
house flags. This reads one output of each and prints the totals side by side, then the
files on which they disagree, so a disagreement goes to mtools as a list and not as a
feeling.

    scripts/census_compare.py PYCHECK_OUTPUT CENSUS_OUTPUT   # n of m, totals, disagreements
    scripts/census_compare.py --selftest

Each argument is a file holding the tool's stdout; lines before the first `{` (a
systemd-run banner) are skipped. PYCHECK_OUTPUT is a JSON object {file: count};
CENSUS_OUTPUT is `typing_census.py --json`, whose "files" object is read.

⚑ WEAKNESS, STATED. It compares two files, so it proves the two numbers were equal when
those outputs were taken, not that the tools agree at any other HEAD; run both at one HEAD.
An output with no JSON object is REFUSED (exit 2), never read as zero findings.
"""

import json
import sys
from typing import cast


def parse(text: str) -> object:
    """The JSON value of a tool output: the object that opens at its first line starting
    with a brace, whatever banner comes before it and whatever trailer follows it."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("{"):
            value, _end = json.JSONDecoder().raw_decode("\n".join(lines[i:]))
            return cast(object, value)
    msg = "no JSON object in the output"
    raise ValueError(msg)


def counts(value: object, key: str | None) -> dict[str, int]:
    """{file: count} from a parsed output; `key` names the inner object to read, if any."""
    if not isinstance(value, dict):
        msg = "the output is not a JSON object"
        raise TypeError(msg)
    inner: object = value if key is None else value.get(key)
    if not isinstance(inner, dict):
        msg = f"no {key!r} object in the output"
        raise TypeError(msg)
    out: dict[str, int] = {}
    for name, n in inner.items():
        if isinstance(name, str) and isinstance(n, int):
            out[name] = n
    return out


def compare(a: dict[str, int], b: dict[str, int]) -> list[tuple[str, int, int]]:
    """(file, count in a, count in b) for every file whose counts differ; absent is 0."""
    names = sorted(set(a) | set(b))
    return [(f, a.get(f, 0), b.get(f, 0)) for f in names if a.get(f, 0) != b.get(f, 0)]


def nonzero(c: dict[str, int]) -> int:
    return sum(1 for n in c.values() if n > 0)


def main(argv: list[str]) -> int:
    args = argv[1:]
    if len(args) != 2:
        print("census_compare: need PYCHECK_OUTPUT CENSUS_OUTPUT", file=sys.stderr)
        return 2
    try:
        with open(args[0], encoding="utf-8") as f:
            pyc = counts(parse(f.read()), None)
        with open(args[1], encoding="utf-8") as f:
            own = counts(parse(f.read()), "files")
    except (OSError, ValueError, TypeError) as exc:
        print(f"census_compare: REFUSED: {exc}", file=sys.stderr)
        return 2
    print(f"pycheck --census --house: {sum(pyc.values())} in {nonzero(pyc)} file(s)")
    print(f"typing_census.py --json:  {sum(own.values())} in {nonzero(own)} file(s)")
    diff = compare(pyc, own)
    for name, x, y in diff:
        print(f"differs\t{name}\tpycheck={x}\ttyping_census={y}")
    print(f"census_compare: {len(diff)} of {len(set(pyc) | set(own))} file(s) differ")
    return 1 if diff else 0


def _selftest() -> bool:
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        mark = "ok  " if got == want else "FAIL"
        extra = "" if got == want else f": got {got!r} want {want!r}"
        print(f"  {mark} {label}{extra}")
        ok = ok and got == want

    banner = "Running as unit: x.service\n"
    chk(
        "a banner line before the object is skipped",
        parse(banner + '{"a": 1}'),
        {"a": 1},
    )
    chk(
        "a trailer after the object is ignored",
        parse('{"a": 1}\nFinished: ok'),
        {"a": 1},
    )
    try:
        parse("no json here")
        refused = False
    except ValueError:
        refused = True
    chk("an output with no object is refused, not read as zero", refused, True)
    chk(
        "the inner object is read by key",
        counts({"files": {"a.py": 2}}, "files"),
        {"a.py": 2},
    )
    chk("the bare form reads the object itself", counts({"a.py": 2}, None), {"a.py": 2})
    chk("equal counts do not differ", compare({"a": 1}, {"a": 1}), [])
    chk(
        "a differing and a one-sided file are both reported, absent being 0",
        compare({"a": 1, "b": 2}, {"a": 3}),
        [("a", 1, 3), ("b", 2, 0)],
    )
    chk("files with findings are counted", nonzero({"a": 0, "b": 3, "c": 1}), 2)
    print("census_compare selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
