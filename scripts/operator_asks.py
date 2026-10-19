#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""operator_asks.py - the asks this repo's queue holds for the operator (W707, under W705).

nemik warns when a repo holds more needs-you asks than its cap (10), but neither nemik-operator (it prints
the whole fleet) nor the queue writer (--queue takes no filter) lists one repo's asks. This reads this repo's
own queue file: every open card blocked on the operator, oldest first, with how long it has waited and how
many cards wait behind it.

    scripts/operator_asks.py            # symbol, days waiting, cards behind it, the ask; n of m
    scripts/operator_asks.py --selftest

WEAKNESS. A card counts as an operator ask when its blocked_kind is human or a blocker starts with
`operator:`; nemik sorts asks further (needs-you, answered, condition) and that sort is not redone here, so
this count can exceed nemik's. `behind` counts only cards of this repo that cite the ask's symbol.
"""

import json
import os
import sys
from datetime import UTC, datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, ".claude", "paths-forward.json")
CAP = 10


def is_ask(card):
    """True when an open card waits on the operator."""
    if card.get("status") in ("done", "dropped"):
        return False
    blockers = card.get("blocked_on") or []
    return card.get("blocked_kind") == "human" or any(
        b.startswith("operator:") for b in blockers
    )


def asks(cards, now):
    """[(symbol, days waiting, cards behind it, ask text)] oldest first."""
    behind = {}
    for c in cards:
        for b in c.get("blocked_on") or []:
            behind.setdefault(b, set()).add(c["symbol"])
    out = []
    for c in cards:
        if not is_ask(c):
            continue
        issued = datetime.fromisoformat(c["issued_at"].replace("Z", "+00:00"))
        text = next(
            (b for b in c.get("blocked_on") or [] if b.startswith("operator:")), ""
        )
        out.append(
            (
                c["symbol"],
                (now - issued).days,
                len(behind.get(c["symbol"], ())),
                text,
            )
        )
    return sorted(out, key=lambda r: -r[1])


def main(argv):
    if argv[1:]:
        print(f"operator_asks: unknown arguments {argv[1:]!r}", file=sys.stderr)
        return 2
    with open(STATE, encoding="utf-8") as fh:
        cards = json.load(fh)["waypoints"]
    if not cards:
        print(
            "operator_asks: the queue holds no card; the search is broken",
            file=sys.stderr,
        )
        return 2
    rows = asks(cards, datetime.now(UTC))
    for sym, days, behind, text in rows:
        print(f"{sym}\t{days}d\tbehind {behind}\t{text[:150]}")
    print(
        f"operator_asks: {len(rows)} of {len(cards)} card(s) wait on the operator; "
        f"cap {CAP}{'' if len(rows) <= CAP else f', {len(rows) - CAP} over'}",
        file=sys.stderr,
    )
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

    now = datetime(2026, 10, 20, tzinfo=UTC)
    cards = [
        {
            "symbol": "W1",
            "status": "blocked",
            "blocked_kind": "human",
            "blocked_on": ["operator: decide x"],
            "issued_at": "2026-10-10T00:00:00Z",
        },
        {
            "symbol": "W2",
            "status": "blocked",
            "blocked_kind": "agent",
            "blocked_on": ["W1"],
            "issued_at": "2026-10-11T00:00:00Z",
        },
        {
            "symbol": "W3",
            "status": "blocked",
            "blocked_kind": "agent",
            "blocked_on": ["W1"],
            "issued_at": "2026-10-12T00:00:00Z",
        },
        {
            "symbol": "W4",
            "status": "blocked",
            "blocked_kind": "agent",
            "blocked_on": ["operator: act y"],
            "issued_at": "2026-10-05T00:00:00Z",
        },
        {
            "symbol": "W5",
            "status": "done",
            "blocked_kind": "human",
            "blocked_on": ["operator: old"],
            "issued_at": "2026-10-01T00:00:00Z",
        },
    ]
    rows = asks(cards, now)
    chk(
        "asks: oldest first, with days waiting and cards behind",
        [(r[0], r[1], r[2]) for r in rows],
        [("W4", 15, 0), ("W1", 10, 2)],
    )
    chk(
        "a done card is not an ask, even with an operator blocker",
        "W5" in [r[0] for r in rows],
        False,
    )
    chk(
        "a card waiting only on another card is not an ask",
        "W2" in [r[0] for r in rows],
        False,
    )
    chk("an unknown flag is refused (2)", main(["x", "--bogus"]), 2)
    print("operator_asks selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
