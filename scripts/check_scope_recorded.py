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

The requirement is policy/scope_recorded.rego (decided by scripts/opa_gate.py
scope_recorded); this file MEASURES: is the record present, and which paragraph
windows in it carry every needle plus a word of the decision (retired / scrub /
concern).

    scripts/check_scope_recorded.py           # the verdict, as opa_gate decides it
    scripts/check_scope_recorded.py --json    # the measurement the policy decides
    scripts/check_scope_recorded.py --where   # the file and line that records it
    scripts/check_scope_recorded.py --selftest

⚑ THIS CAN FAIL, AND THAT IS THE DESIGN.  Delete the rationale from the notes and
it goes red — which is what makes it a claim rather than a comment.  Weakness: the
test is words co-occurring in a 7-line window, not that the paragraph says why.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Where the decision must be legible, and the substance it must carry.  The
# marker is a PHRASE a human would write, not a magic token: a check keyed to a
# sentinel string tests that someone pasted the sentinel.
RECORD = "RECOVERY-NOTES.md"
NEEDLES = ("trademark", "rename")
DECISION = ("retired", "scrub", "concern")


def found(root=ROOT):
    """[(lineno, text)] evidence in the record that the decision is explained;
    None when the record is absent.

    ⚑ THE UNIT IS A PARAGRAPH, NOT A LINE.  This first required every needle on
    ONE line and reported a rationale that was plainly present as absent — the
    check's world-model was too strict, not the document deficient.  Prose wraps;
    a witness that assumes it does not is measuring the line breaks."""
    p = os.path.join(root, RECORD)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    for i, line in enumerate(lines, 1):
        # a window around this line, so a rationale spanning a wrapped
        # paragraph counts as the single statement it reads as
        window = " ".join(lines[max(0, i - 4):i + 3]).lower()
        if all(n in window for n in NEEDLES) and any(d in window for d in DECISION):
            return [(i, line.rstrip())]                 # one witness is enough
    return []


def measure(root=ROOT):
    ev = found(root)
    return {"cases": [{"record": RECORD, "present": ev is not None,
                       "evidence": [{"line": i, "text": t} for i, t in (ev or [])]}]}


def main(argv):
    known = {"--where", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_scope_recorded: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--where" in argv:
        for i, text in found() or []:
            print(f"{RECORD}:{i}: {text}")
        return 0
    import opa_gate
    return opa_gate.gate("scope_recorded")


def _selftest():
    """The measurement can SEE a recorded rationale, a missing one, and a missing record."""
    import tempfile
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    check("needles are non-empty", all(NEEDLES), True)
    with tempfile.TemporaryDirectory() as td:
        check("an absent record is SEEN", measure(td)["cases"][0]["present"], False)
        p = os.path.join(td, RECORD)
        open(p, "w").write("# notes\nnothing about it\n")
        check("a record without the rationale has no evidence", measure(td)["cases"][0]["evidence"], [])
        # the wrapped paragraph that the one-line version reported absent
        open(p, "w").write("The rename was about a\ntrademark; the prior mark was\nretired everywhere.\n")
        check("a WRAPPED rationale is seen", len(measure(td)["cases"][0]["evidence"]), 1)
    print("check_scope_recorded selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
