#!/usr/bin/env python3
"""check_cotype_open.py — the open worklist is bucketed by WHO CAN ACT.

The design log sorts its open work by operator, and the buckets are not
interchangeable:

    BUILD     touches the shipped package — do first
    RESEARCH  design work, no package impact
    LIVE      operator=other: only a human at a real desktop can run it
    TUNE      parameter work
    TIER 3    deferred surface
    RESIDUE   kept, deliberately unbuilt

⚑ LIVE IS THE ONE THAT MATTERS TO A GATE.  No check this repo could write can
discharge "does the theme look right on the login screen" — that needs a person,
a monitor, and a reboot. So a LIVE item must never be mistaken for work a check
could close, and no claim may assert one is DONE. This tool asserts the weaker,
true thing: the open set is legible, every item lands in exactly one bucket, and
the operator-blocked ones are named as such.

    scripts/check_cotype_open.py           # exit 0 iff the open set is well-formed
    scripts/check_cotype_open.py --report  # the open set, by bucket
    scripts/check_cotype_open.py --live    # only the operator-blocked items

⚑ THIS IS A LEGIBILITY CHECK, NOT A PROGRESS CHECK.  It goes green on a large
open set and red on an unreadable one. Wanting it to measure progress instead is
wanting a number that would drop when someone deleted a line.
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "scripts", "cotype_index.py")

# The buckets the log itself uses. A bucket outside this set means the log grew a
# new category and this tool has not been taught it — which is a finding.
KNOWN = {"BUILD", "RESEARCH", "LIVE", "TUNE", "TIER 3", "RESIDUE"}

# Buckets no automated check can ever discharge.
OPERATOR_BLOCKED = {"LIVE"}


def index():
    r = subprocess.run([sys.executable, INDEX, "--json"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    return json.loads(r.stdout)


def main(argv):
    known = {"--report", "--live"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_cotype_open: unknown flag {a!r}", file=sys.stderr)
            return 2
    d = index()
    if d is None:
        print("check_cotype_open: REFUSED — the index would not run", file=sys.stderr)
        return 2
    opn = d["open"]

    if "--live" in argv:
        for b in sorted(OPERATOR_BLOCKED):
            for s in opn.get(b, []):
                print(f"{b}\t{s}")
        return 0
    if "--report" in argv:
        for b, syms in sorted(opn.items()):
            tag = "  (operator=other)" if b in OPERATOR_BLOCKED else ""
            print(f"{b} ({len(syms)}){tag}: {' '.join(syms)}")
        return 0

    total = sum(len(v) for v in opn.values())
    if not opn or total == 0:
        print("check_cotype_open: REFUSED — the open set is EMPTY; the ledger is "
              "unreadable, not the work finished", file=sys.stderr)
        return 2

    problems = []
    unknown = sorted(set(opn) - KNOWN)
    if unknown:
        problems.append(f"bucket(s) this tool does not know: {', '.join(unknown)}")
    # A symbol in two buckets has an ambiguous owner.
    seen = {}
    for b, syms in opn.items():
        for s in syms:
            seen.setdefault(s, []).append(b)
    doubled = {s: bs for s, bs in seen.items() if len(bs) > 1}
    if doubled:
        problems.append("symbol(s) in more than one bucket: "
                        + ", ".join(f"{s} ({'/'.join(bs)})" for s, bs in sorted(doubled.items())))
    if not any(b in opn for b in OPERATOR_BLOCKED):
        problems.append("no operator-blocked bucket found — the LIVE distinction "
                        "has been lost, and operator work now reads as closable")

    if problems:
        print(f"check_cotype_open: REFUSED — the open set is not well-formed:",
              file=sys.stderr)
        for p in problems:
            print(f"    {p}", file=sys.stderr)
        return 1

    live = sum(len(opn.get(b, [])) for b in OPERATOR_BLOCKED)
    print(f"check_cotype_open: {total} open across {len(opn)} bucket(s); "
          f"{live} operator-blocked (no check can discharge these)")
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

    check("operator-blocked is a subset of known", OPERATOR_BLOCKED <= KNOWN, True)
    d = index()
    check("the index answers", d is not None, True)
    if d:
        opn = d["open"]
        check("the open set is non-empty", sum(len(v) for v in opn.values()) > 0, True)
        # The LIVE bucket is the reason this tool exists; if it vanishes, the
        # tool must fail rather than quietly pass a set it can no longer sort.
        check("the LIVE bucket is present", "LIVE" in opn, True)
    print("check_cotype_open selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
