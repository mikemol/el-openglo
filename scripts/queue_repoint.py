#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""queue_repoint.py - move every card that waits on one blocker to wait on another (W704).

nemik reads a card blocked on another repo's UMBRELLA as under-specified ("cite the one that unblocks
you"): 50 typing-debt cards waited on mtools:W1513 while the step they actually need is its annotating
mode, mtools:W1516. A blind bulk update would drop each card's other blockers (many also wait on local
debt cards), so this replaces ONE token in place and keeps the rest, in order.

    scripts/queue_repoint.py FROM TO                      # the plan and its hash; writes nothing
    scripts/queue_repoint.py FROM TO --apply --plan HASH  # write it, only if the plan still hashes to HASH
    scripts/queue_repoint.py --selftest

⚑ THE ORDER IS MECHANICAL (github-8f, 2026-10-18): --apply refuses without the hash the dry run printed and
refuses when the recomputed plan differs, so a bulk edit cannot run unread.

WEAKNESS. It edits the queue through mikemol-paths-forward --update, one call per card; a card's blocked_kind
is kept as it is. It does not check that TO exists or is open: that is the caller's reading to make.
"""

import hashlib
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, ".claude", "paths-forward.json")
WRITER = os.path.join(ROOT, ".venv", "bin", "mikemol-paths-forward")


def repoint(held, old, new):
    """{card: blocked_on with `old` replaced by `new`}, only for cards that wait on `old`.

    The replacement is in place so the order of the other blockers is kept, and `new` is not added twice
    when the card already waits on it."""
    out = {}
    for card, blockers in held.items():
        if old not in blockers:
            continue
        moved = []
        for b in blockers:
            b = new if b == old else b
            if b not in moved:
                moved.append(b)
        out[card] = moved
    return out


def plan_lines(moves):
    """The plan as sorted text lines, one per card."""
    return [f"{c} blocked_on {' '.join(b)}" for c, b in sorted(moves.items())]


def plan_hash(lines):
    """A short hash of the plan text."""
    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]


def main(argv):
    args = argv[1:]
    if len(args) not in (2, 5) or any(a.startswith("--") for a in args[:2]):
        print(
            "queue_repoint: usage: FROM TO [--apply --plan HASH]",
            file=sys.stderr,
        )
        return 2
    if len(args) == 5 and args[2:4] != ["--apply", "--plan"]:
        print(f"queue_repoint: unknown arguments {args[2:]!r}", file=sys.stderr)
        return 2
    old, new = args[0], args[1]
    with open(STATE, encoding="utf-8") as fh:
        wps = json.load(fh)["waypoints"]
    held = {
        w["symbol"]: list(w.get("blocked_on") or [])
        for w in wps
        if w.get("status") != "done"
    }
    kinds = {w["symbol"]: w.get("blocked_kind") or "agent" for w in wps}
    moves = repoint(held, old, new)
    lines = plan_lines(moves)
    digest = plan_hash(lines)
    print("\n".join(lines))
    print(f"plan {digest}")
    print(
        f"queue_repoint: {len(moves)} of {len(held)} open card(s) wait on {old}",
        file=sys.stderr,
    )
    if not moves:
        print("queue_repoint: nothing waits on that blocker", file=sys.stderr)
        return 2
    if len(args) == 5:
        if args[4] != digest:
            print(
                f"queue_repoint: REFUSED: the plan is {digest}, not {args[4]}; "
                "run the dry run again and read it before applying",
                file=sys.stderr,
            )
            return 1
        for card in sorted(moves):
            argv_w = [WRITER, "--state", STATE, "--update", card]
            argv_w += ["--blocked-on", *moves[card], "--blocked-kind", kinds[card]]
            subprocess.run(argv_w, check=True)
    return 0


def _selftest():
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    held = {
        "W1": ["m:W1513"],
        "W2": ["W1", "m:W1513", "W9"],
        "W3": ["m:W1516", "m:W1513"],
        "W4": ["W9"],
    }
    moves = repoint(held, "m:W1513", "m:W1516")
    chk(
        "repoint: replaced in place, the other blockers and their order kept",
        moves["W2"],
        ["W1", "m:W1516", "W9"],
    )
    chk(
        "repoint: a card that already waits on the new blocker is not doubled",
        moves["W3"],
        ["m:W1516"],
    )
    chk(
        "repoint: only cards that wait on the old blocker are named",
        sorted(moves),
        ["W1", "W2", "W3"],
    )
    chk(
        "repoint: nothing waits on it is an empty plan",
        repoint(held, "m:W0", "m:W1"),
        {},
    )
    lines = plan_lines(moves)
    chk(
        "plan_hash: stable for one plan and different for another",
        (
            plan_hash(lines) == plan_hash(list(lines)),
            plan_hash(lines) == plan_hash(lines[:1]),
        ),
        (True, False),
    )
    chk(
        "refused: no arguments, a flag as a blocker, --apply without --plan",
        (
            main(["x"]),
            main(["x", "--apply", "b"]),
            main(["x", "a", "b", "--apply", "--bogus", "h"]),
        ),
        (2, 2, 2),
    )
    print("queue_repoint selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
