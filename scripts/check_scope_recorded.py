#!/usr/bin/env python3
"""check_scope_recorded.py — the rename decision is legible where a reader meets it.

A DECISION ITEM IS CLOSED WHILE DECIDED — it is not debt, and it must not block.
But "not blocking" and "not falsifiable" are separable, and every item needs the
first WITHOUT the second: a check that cannot fail grades `indeterminate` under
paperkit's own Δ grader, and an unfalsifiable claim the gate certifies is worse
than no claim at all.  So this does not ask whether the decision was right.  It
asks whether it is RECORDED where someone meeting the rename would find it.

The decision: the prior mark was retired EVERYWHERE — not just as a project name
but in descriptive prose and in palette-token names — because the concern is a
trademark, and a scrub that keeps the word for "the effect" keeps the exposure.

    scripts/check_scope_recorded.py           # exit 0 iff the decision is recorded
    scripts/check_scope_recorded.py --where   # the file and line that records it

⚑ THIS CAN FAIL, AND THAT IS THE DESIGN.  Delete the rationale from the notes and
it goes red — which is what makes it a claim rather than a comment.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the decision must be legible, and the substance it must carry.  The
# marker is a PHRASE a human would write, not a magic token: a check keyed to a
# sentinel string tests that someone pasted the sentinel.
RECORD = "RECOVERY-NOTES.md"
NEEDLES = ("trademark", "rename")


def found():
    """[(lineno, text)] lines in the record carrying the decision's substance."""
    p = os.path.join(ROOT, RECORD)
    if not os.path.exists(p):
        return None
    hits = []
    for i, line in enumerate(open(p, encoding="utf-8", errors="replace"), 1):
        low = line.lower()
        if all(n in low for n in NEEDLES) or (
                "trademark" in low and ("scrub" in low or "retired" in low)):
            hits.append((i, line.rstrip()))
    return hits


def main(argv):
    known = {"--where"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_scope_recorded: unknown flag {a!r}", file=sys.stderr)
            return 2
    hits = found()
    if hits is None:
        print(f"check_scope_recorded: REFUSED — {RECORD} is absent; the decision has "
              f"nowhere legible to live", file=sys.stderr)
        return 1
    if "--where" in argv:
        for i, text in hits:
            print(f"{RECORD}:{i}: {text}")
        return 0
    if not hits:
        print(f"check_scope_recorded: REFUSED — {RECORD} does not record WHY the "
              f"prior mark was retired", file=sys.stderr)
        print(f"    A reader meeting the rename would find the change but not its "
              f"reason.", file=sys.stderr)
        return 1
    print(f"check_scope_recorded: the rename decision is recorded in {RECORD} "
          f"({len(hits)} line(s))")
    return 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("needles are non-empty", all(NEEDLES), True)
    check("record is named", bool(RECORD), True)
    print("check_scope_recorded selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
