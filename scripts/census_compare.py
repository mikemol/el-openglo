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
import os
import subprocess
import sys
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))


def parse(text: str) -> object:
    """The JSON value of a tool output: the object that opens at its first line starting
    with a brace, whatever banner comes before it and whatever trailer follows it."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("{"):
            value, _end = cast(
                "tuple[object, int]",
                json.JSONDecoder().raw_decode("\n".join(lines[i:])),
            )
            return value
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


def order(pyc: dict[str, int], own: dict[str, int]) -> list[tuple[int, int, str]]:
    """The cleanup order the import-following census gives (operator 2026-10-18: it
    "provides a topological sort order for getting things cleaned up").

    The packaged count of a file is its own findings plus those of the modules it
    imports, so `pyc - own` is what its imports still owe. A file with nothing owed has
    clean imports and goes first; ties go to the file with fewer findings of its own.

    Returns:
        (owed by imports, own findings, file) for each file with own findings, sorted.
    """
    rows = [(max(pyc.get(f, 0) - n, 0), n, f) for f, n in own.items() if n > 0]
    return sorted(rows)


def weights(
    rows: list[tuple[int, int, str]], cards: list[tuple[str, str]]
) -> list[tuple[str, int]]:
    """(symbol, weight) for each open debt card whose file is in the order: the first
    file gets the highest weight, so a higher weight sorts first (--weight)."""
    place = {name: i for i, (_owed, _n, name) in enumerate(rows)}
    return [(sym, len(rows) - place[f]) for sym, f in cards if f in place]


def apply_weights(rows: list[tuple[int, int, str]]) -> int:
    """Write the weights onto the open typing debt cards through the writer."""
    import typing_plan

    with open(typing_plan.STATE, encoding="utf-8") as fh:
        state = cast(dict[str, list[dict[str, str]]], json.load(fh))
    todo = weights(rows, typing_plan.debt_cards(state["waypoints"]))
    for sym, w in todo:
        argv = [typing_plan.WRITER, "--state", typing_plan.STATE]
        subprocess.run([*argv, "--update", sym, "--weight", str(w)], check=True)
    print(f"census_compare: weighted {len(todo)} open debt card(s) by the order")
    return 0


def main_order(pyc: dict[str, int], own: dict[str, int], apply: bool) -> int:
    rows = order(pyc, own)
    if apply:
        return apply_weights(rows)
    for owed, n, name in rows:
        print(f"{owed}\t{n}\t{name}")
    clean = sum(1 for owed, _n, _f in rows if owed == 0)
    unseen = sum(1 for _o, _n, f in rows if f not in pyc)
    print(
        f"census_compare: {len(rows)} file(s) to clean, {clean} with clean imports "
        f"first; {unseen} not seen by the packaged census (owed read as 0)"
    )
    return 0


def main(argv: list[str]) -> int:
    args = argv[1:]
    ordering = bool(args) and args[0] == "--order"
    if ordering:
        args = args[1:]
    apply = ordering and bool(args) and args[0] == "--apply"
    if apply:
        args = args[1:]
    if len(args) != 2:
        print(
            "census_compare: need [--order] PYCHECK_OUTPUT CENSUS_OUTPUT",
            file=sys.stderr,
        )
        return 2
    try:
        with open(args[0], encoding="utf-8") as f:
            pyc = counts(parse(f.read()), None)
        with open(args[1], encoding="utf-8") as f:
            own = counts(parse(f.read()), "files")
    except (OSError, ValueError, TypeError) as exc:
        print(f"census_compare: REFUSED: {exc}", file=sys.stderr)
        return 2
    if ordering:
        return main_order(pyc, own, apply)
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
    chk(
        "a file whose imports are clean goes first, ties by fewer own findings",
        order(
            {"leaf": 4, "mid": 9, "top": 30, "clean": 1},
            {"leaf": 4, "mid": 5, "top": 3, "clean": 1},
        ),
        [(0, 1, "clean"), (0, 4, "leaf"), (4, 5, "mid"), (27, 3, "top")],
    )
    chk(
        "a file the packaged census did not see is owed nothing, not negative",
        order({}, {"x": 2}),
        [(0, 2, "x")],
    )
    rows = [(0, 1, "clean.py"), (4, 5, "mid.py"), (27, 3, "top.py")]
    chk(
        "the first file gets the highest weight, unmatched cards get none",
        weights(rows, [("W1", "top.py"), ("W2", "clean.py"), ("W3", "gone.py")]),
        [("W1", 1), ("W2", 3)],
    )
    chk(
        "a file with no findings of its own is not in the order",
        order({"a": 5}, {"a": 0}),
        [],
    )
    print("census_compare selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
