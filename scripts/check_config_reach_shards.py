#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_config_reach_shards.py — does every shard of @CONFIG-REACH have a warrant that runs it (W778).

⚑ WHY. check_config_reach takes mount operands so no one claim runs past paperkit's wall backstop
(W771): its SHARDS are an exact partition of the mount registry, and warrants.bib runs one claim per
shard. The partition is checked from the registry side by that check's selftest; nothing checked it
from the BIB side, so a shard whose warrant was dropped (or a warrant whose operands drifted from the
shard) left a slice of the registry never measured, and every claim stayed green over a smaller
population. This measures the join: the shards declared, and the operands every config_reach
warrant actually passes.

    scripts/check_config_reach_shards.py --json [BIB]   # what the check measured, for policy/config_reach_shards.rego
    scripts/check_config_reach_shards.py --selftest

It reports only what it measured; the requirement is policy/config_reach_shards.rego, joined by
`scripts/opa_gate.py config_reach_shards`. A warrants .bib it cannot read (paperkit not importable) is
a `withheld` fact, never an empty list.

⚑ WEAKNESS, STATED. It reads the warrants' `check` text, so a warrant that reaches config_reach
through a wrapper script, or one whose operands are built at run time, is not seen as a config_reach
warrant at all; the join proves the bib NAMES every shard, not that the named warrant passes.
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

BIB = os.path.join(ROOT, "catalog", "worklist", "warrants.bib")
RUNNER = "tool:opa_gate.py"
POLICY = "config_reach"


def operands(check):
    """The mount operands of a `tool:opa_gate.py config_reach ...` check, or None for any other check."""
    words = check.split()
    if len(words) < 2 or words[0] != RUNNER or words[1] != POLICY:
        return None
    return words[2:]


def measure(bib=BIB):
    """The facts: the shards declared, every config_reach warrant's operands, what could not be read."""
    import check_config_reach
    import worklist_gate

    shards = [list(s) for s in check_config_reach.SHARDS]
    recs = worklist_gate.warrants(bib)
    if recs is None:
        return {
            "shards": shards,
            "warrants": [],
            "withheld": ["paperkit is not importable: the warrants could not be read"],
        }
    found = []
    for key, rec in recs.items():
        ops = operands(rec.get("check", ""))
        if ops is not None:
            found.append({"key": key, "operands": ops})
    return {
        "shards": shards,
        "warrants": found,
        "warrants_read": len(recs),
        "withheld": [],
    }


def main(argv):
    args = argv[1:]
    known = {"--json", "--selftest"}
    flags = [a for a in args if a.startswith("-")]
    paths = [a for a in args if not a.startswith("-")]
    for a in flags:
        if a not in known:
            print(f"check_config_reach_shards: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in flags:
        return 0 if _selftest() else 1
    if "--json" not in flags:
        print("check_config_reach_shards: needs --json or --selftest", file=sys.stderr)
        return 2
    if len(paths) > 1:
        print("check_config_reach_shards: at most one BIB operand", file=sys.stderr)
        return 2
    m = measure(paths[0] if paths else BIB)
    print(json.dumps(m, indent=2))
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk(
        "a sharded warrant's operands are read",
        operands("tool:opa_gate.py config_reach clock wallpaper"),
        ["clock", "wallpaper"],
    )
    chk(
        "an unsharded config_reach warrant has no operands",
        operands("tool:opa_gate.py config_reach"),
        [],
    )
    chk(
        "another policy is not a config_reach warrant",
        operands("tool:opa_gate.py css"),
        None,
    )
    chk(
        "another runner is not one either",
        operands("tool:check_config_reach.py --selftest"),
        None,
    )
    with tempfile.TemporaryDirectory() as td:
        path = os.path.join(td, "w.bib")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(
                "@misc{A,\n  claim = {a},\n  check = {tool:opa_gate.py config_reach marquee},\n}\n"
                "@misc{B,\n  claim = {b},\n  check = {tool:opa_gate.py css},\n}\n"
            )
        m = measure(path)
        chk(
            "a bib is read: only the config_reach warrant is listed",
            [w["key"] for w in m["warrants"]],
            ["A"],
        )
        chk("...and the bib's whole population is counted", m.get("warrants_read"), 2)
    real = measure()
    chk(
        "the real bib names a warrant for every declared shard",
        sorted(sorted(w["operands"]) for w in real["warrants"]),
        sorted(sorted(s) for s in real["shards"]),
    )
    print("check_config_reach_shards selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
