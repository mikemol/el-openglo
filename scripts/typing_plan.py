#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""typing_plan.py — write the typing census onto the typing debt cards (W676, under W553)

Each debt card is titled "el-openglo typing: FILE (N findings)". Its plan is the
house count of FILE now and the idiom that dominates it, which
`typing_census.by_file_idiom` already computes; this joins the two so the cards
carry the tool's output instead of a hand-written plan.

    scripts/typing_plan.py           # the next step each open debt card would get, then n of m
    scripts/typing_plan.py --apply   # write it with mikemol-paths-forward --update SYMBOL --next TEXT
    scripts/typing_plan.py --selftest

⚑ WEAKNESS, STATED. It runs the census (mypy over three passes: minutes of CPU),
so it measures the tree as it stands, not the title's count. A card whose file
the census no longer reports is listed as CLEARED, not written and not closed:
whether the debt is paid is the gate's reading, and the earlier false closure of
these cards came from taking a weaker measure for it. The state file is read as
JSON and written only through the writer.
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

STATE = os.path.join(ROOT, ".claude", "paths-forward.json")
WRITER = os.path.join(ROOT, ".venv", "bin", "mikemol-paths-forward")
TITLE = re.compile(r"^el-openglo typing: (\S+) \((\d+) findings\)$")


def debt_cards(waypoints):
    """[(symbol, file)] for each open debt card, in queue order."""
    out = []
    for w in waypoints:
        m = TITLE.match(w.get("title", ""))
        if m and w.get("status") != "done":
            out.append((w["symbol"], m.group(1)))
    return out


def step_text(path, row):
    return (
        f"{path}: {row['count']} house finding(s) (typing_census --by-file-idiom); "
        f"the dominant idiom is {row['code']} x{row['idiom_count']}: {row['idiom']}. "
        "Annotate from the consumers, judged by the house count of this file."
    )


SMALL_MAX = 50
MEDIUM_MAX = 300


def size_of(count):
    """The size class of a file's debt: small up to 50 findings, medium up to 300, else large."""
    if count <= SMALL_MAX:
        return "small"
    return "medium" if count <= MEDIUM_MAX else "large"


def plan(cards, rows):
    """(writes, cleared): [(symbol, text, file, size)] for files the census reports, [(symbol, file)] else."""
    writes, cleared = [], []
    for symbol, path in cards:
        if path in rows:
            text = step_text(path, rows[path])
            writes.append((symbol, text, path, size_of(rows[path]["count"])))
        else:
            cleared.append((symbol, path))
    return writes, cleared


def refuse(message, code):
    print(f"typing_plan: {message}", file=sys.stderr)
    return code


def main(argv):
    args = argv[1:]
    if args not in ([], ["--apply"]):
        return refuse(f"unknown arguments {args!r}", 2)
    import typing_census

    with open(STATE, encoding="utf-8") as f:
        cards = debt_cards(json.load(f)["waypoints"])
    if not cards:
        return refuse(
            "no open debt card was read; the title shape or state is wrong", 2
        )
    _files, withheld, _n, records = typing_census.census()
    if withheld:
        return refuse(
            f"{len(withheld)} census pass(es) withheld; no plan on a partial measure", 3
        )
    writes, cleared = plan(cards, typing_census.by_file_idiom(records))
    for symbol, text, path, size in writes:
        print(f"{symbol}\t{size}\t{text}")
        if args == ["--apply"]:
            argv_w = [WRITER, "--state", STATE, "--update", symbol, "--next", text]
            argv_w += ["--manifest", path, "--size", size]
            subprocess.run(argv_w, check=True)
    for symbol, path in cleared:
        print(
            f"CLEARED {symbol}\t{path}: the census reports no finding; verify with the gate"
        )
    print(
        f"typing_plan: {len(writes)} of {len(cards)} open debt card(s) planned, "
        f"{len(cleared)} cleared",
        file=sys.stderr,
    )
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        mark = "ok  " if got == want else "FAIL"
        print(
            f"  {mark} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    title = "el-openglo typing: {} ({} findings)"
    ways = [
        {"symbol": "W1", "title": title.format("a.py", 12), "status": "blocked"},
        {"symbol": "W2", "title": title.format("b.py", 3), "status": "done"},
        {"symbol": "W3", "title": title.format("c.py", 5), "status": "ready"},
        {"symbol": "W4", "title": "something else (2 findings)", "status": "ready"},
    ]
    cards = debt_cards(ways)
    chk(
        "only open cards with the debt title are read",
        cards,
        [("W1", "a.py"), ("W3", "c.py")],
    )
    row = {"count": 7, "code": "misc", "idiom_count": 4, "idiom": "Any"}
    writes, cleared = plan(cards, {"a.py": row})
    chk(
        "a card whose file the census reports is planned",
        [w[0] for w in writes],
        ["W1"],
    )
    chk("the text carries the count", "7 house finding(s)" in writes[0][1], True)
    chk("the text carries the dominant idiom", "misc x4: Any" in writes[0][1], True)
    chk("a file no longer reported is cleared, not written", cleared, [("W3", "c.py")])
    chk("no open debt card means nothing to plan", debt_cards([]), [])
    chk("the card's manifest is its file", writes[0][2], "a.py")
    chk(
        "size bands: 50 small, 51 medium, 300 medium, 301 large",
        [size_of(n) for n in (50, 51, 300, 301)],
        ["small", "medium", "medium", "large"],
    )
    print("typing_plan selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
