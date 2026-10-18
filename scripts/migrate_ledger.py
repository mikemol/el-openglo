#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""migrate_ledger.py — how much of the ledger can a structured reader read? (W89, under W91)

The ledger is `.claude/paths-forward.ledger`; mtools' own reader (mikemol.pathsforward.ledger.parse) reads a
line as `stamp kind symbol outcome mechanism "note" [evidence=...]` and returns the rest as Unparsed, with a
`why`. The legacy lines (hand echoes, `state_hash=` in place of `evidence=`, free text) are kept whole there
and nemik cannot read them. This is the first step: MEASURE them.

    scripts/migrate_ledger.py --report      # n of m lines parse; the unparsed, by reason and by legacy shape
    scripts/migrate_ledger.py --selftest

⚑ WEAKNESS, STATED. --report only reads: it rewrites nothing, and the legacy SHAPE it names is a first-token
heuristic (a stamp, a bare symbol, free text), not a grammar. The rewrite (--write, with the kind taken from
the line's origin, the symbol extracted and the full text kept as the note) is the next step and is not here.
"""

import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(ROOT, ".claude", "paths-forward.ledger")
OFFSET_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$")
QUOTED = re.compile(r"'[^']*'")


def shape(raw):
    """The legacy shape of an unparsed line: what its first token looks like."""
    first = raw.split(None, 1)[0] if raw.strip() else ""
    if "state_hash=" in raw:
        return "stamp + state_hash= in place of evidence="
    if OFFSET_STAMP.match(first):
        return "a stamp ending +00:00 instead of Z"
    if len(first) == 20 and first[4] == "-" and first.endswith("Z"):
        return "a stamp, then columns this reader does not take"
    if first.startswith("W") and first[1:].isdigit():
        return "a bare symbol first"
    return "free text"


def reason(why):
    """The reason an unparsed line gave, with the quoted value (a stamp, a symbol) taken out so equal
    reasons count together."""
    return QUOTED.sub("'…'", why)


def report(lines):
    """(parsed, by_why, by_shape, total) over `lines` (ledger.Parsed / ledger.Unparsed)."""
    from mikemol.pathsforward import ledger

    bad = [x for x in lines if isinstance(x, ledger.Unparsed)]
    return (
        len(lines) - len(bad),
        Counter(reason(x.why) for x in bad),
        Counter(shape(x.raw) for x in bad),
        len(lines),
    )


def last_legacy(lines):
    """The 1-based index of the last unparsed line in `lines`, or 0 when every line parses: every line after
    it was written by the structured writer, so it is where the legacy history ends."""
    from mikemol.pathsforward import ledger

    bad = [i for i, x in enumerate(lines, 1) if isinstance(x, ledger.Unparsed)]
    return bad[-1] if bad else 0


def main(argv):
    if argv[1:] != ["--report"]:
        print(f"migrate_ledger: unknown arguments {argv[1:]!r}", file=sys.stderr)
        return 2
    from mikemol.pathsforward import ledger

    lines = ledger.read(Path(LEDGER))
    if not lines:
        print(
            "migrate_ledger: the ledger is empty; the search is broken", file=sys.stderr
        )
        return 2
    parsed, by_why, by_shape, total = report(lines)
    for why, n in by_why.most_common():
        print(f"why\t{n}\t{why}")
    for kind, n in by_shape.most_common():
        print(f"shape\t{n}\t{kind}")
    print(
        f"migrate_ledger: {parsed} of {total} line(s) parse; {total - parsed} legacy; "
        f"the last legacy line is {last_legacy(lines)} of {total}",
        file=sys.stderr,
    )
    return 0


def _selftest():
    from mikemol.pathsforward import ledger

    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    good = '2026-10-17T22:43:55Z  tick  W662  advanced  sweep  "a note"'
    legacy = "2026-09-26T18:51:31Z tick W9 advanced sweep state_hash=v2:abc"
    free = "echo by hand: did a thing"
    lines = [ledger.parse(x) for x in (good, legacy, free)]
    parsed, by_why, by_shape, total = report(lines)
    chk("n of m: one structured line of three parses", (parsed, total), (1, 3))
    chk("the unparsed are counted by reason", sum(by_why.values()), 2)
    chk(
        "the legacy shapes are told apart",
        sorted(by_shape),
        ["free text", "stamp + state_hash= in place of evidence="],
    )
    chk(
        "a +00:00 stamp is its own shape, told from a Z stamp",
        (
            shape("2026-09-20T18:59:08+00:00 tick W9 advanced sweep note"),
            shape("2026-09-20T18:59:08Z tick W9 advanced sweep"),
        ),
        (
            "a stamp ending +00:00 instead of Z",
            "a stamp, then columns this reader does not take",
        ),
    )
    chk(
        "reasons that differ only in the quoted stamp count as one",
        reason("stamp '2026-09-20T18:59:08+00:00' is not x")
        == reason("stamp '2026-09-21T09:30:06+00:00' is not x"),
        True,
    )
    chk(
        "a bare symbol first is its own shape",
        shape("W12 did a thing"),
        "a bare symbol first",
    )
    chk(
        "last_legacy: the index of the last unparsed line, 0 when every line parses",
        (last_legacy(lines), last_legacy(lines[:1])),
        (3, 0),
    )
    chk("an empty ledger would be a refusal, not 0 of 0", report([])[3], 0)
    real = ledger.read(Path(LEDGER)) if os.path.isfile(LEDGER) else []
    chk("the live ledger has lines to read (n of m, never 0 of 0)", len(real) > 0, True)
    print("migrate_ledger selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
