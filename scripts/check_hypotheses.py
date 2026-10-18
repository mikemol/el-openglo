#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_hypotheses.py — the register of hypotheses, MEASURED; policy/hypotheses.rego decides (W206)

Operator, 2026-10-01: a hypothesis marks an ambiguity between the Rego model and the
implementation, and it closes only when both sides are refined at that boundary. The records
live in catalog/hypotheses.json, one object per hypothesis:

    id, status (open|closed), question, rule, structure, boundary

This reads them and reports; the requirement (a closed record names its question, its rule and
its checkable structure and leaves no open edge) is the policy's.

    scripts/check_hypotheses.py --json      # the measurement policy/hypotheses.rego decides
    scripts/check_hypotheses.py             # the verdict, as opa_gate hypotheses decides it
    scripts/check_hypotheses.py --selftest  # the measurement can see

WEAKNESS. It reads the shape of each record, not whether the named rule is the right one or
the named structure really makes it checkable; and a record nobody wrote is invisible, so the
register is only as complete as the people who file into it. An unreadable or missing register
is reported (exit 2), never read as an empty one.
"""

import json
import os
import sys
from typing import cast

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.path.join(ROOT, "catalog", "hypotheses.json")
FIELDS = ("id", "status", "question", "rule", "structure", "boundary")


def load(text: str) -> list[dict[str, object]]:
    """The records of a register's text; a text that is not a list of objects is a ValueError."""
    raw = cast(object, json.loads(text))
    if not isinstance(raw, list):
        msg = "the register is not a JSON list"
        raise TypeError(msg)
    out: list[dict[str, object]] = []
    for i, item in enumerate(cast(list[object], raw)):
        if not isinstance(item, dict):
            msg = f"record {i} is not an object"
            raise TypeError(msg)
        out.append({str(k): v for k, v in cast(dict[object, object], item).items()})
    return out


def measure(records: list[dict[str, object]]) -> dict[str, object]:
    """The facts the policy decides on: the records, each limited to the register's fields."""
    return {
        "hypotheses": [{k: r[k] for k in FIELDS if k in r} for r in records],
    }


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args not in ([], ["--json"]):
        print(f"check_hypotheses: unknown arguments {args!r}", file=sys.stderr)
        return 2
    try:
        with open(REGISTER, encoding="utf-8") as fh:
            records = load(fh.read())
    except (OSError, ValueError, TypeError) as exc:
        print(f"check_hypotheses: REFUSED: {exc}", file=sys.stderr)
        return 2
    doc = measure(records)
    if args == ["--json"]:
        print(json.dumps(doc, indent=1))
        return 0
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import opa_gate

    return int(opa_gate.gate("hypotheses"))


def _selftest() -> bool:
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        mark = "ok  " if got == want else "FAIL"
        extra = "" if got == want else f": got {got!r} want {want!r}"
        print(f"  {mark} {label}{extra}")
        ok = ok and got == want

    text = json.dumps(
        [{"id": "H1", "status": "open", "question": "q", "extra": 1}, {"id": "H2"}]
    )
    recs = load(text)
    chk("a register of objects is read", [r["id"] for r in recs], ["H1", "H2"])
    chk(
        "measure keeps only the register's fields",
        measure(recs)["hypotheses"],
        [{"id": "H1", "status": "open", "question": "q"}, {"id": "H2"}],
    )
    try:
        load('{"id": "H1"}')
        refused = False
    except TypeError:
        refused = True
    chk("a register that is not a list is refused, not read as empty", refused, True)
    try:
        load("[1]")
        refused = False
    except TypeError:
        refused = True
    chk("a record that is not an object is refused", refused, True)
    chk("an unknown flag is refused", main(["x", "--queit"]), 2)
    live = os.path.isfile(REGISTER)
    if live:
        with open(REGISTER, encoding="utf-8") as fh:
            records = load(fh.read())
        chk(
            "the live register has records (n of m, never 0 of 0)",
            len(records) > 0,
            True,
        )
    print("check_hypotheses selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
