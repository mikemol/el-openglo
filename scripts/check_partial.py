#!/usr/bin/env python3
"""check_partial.py — the partial-recovery record is intact and honest.

The archive replayed the lost tree from session transcripts.  Eight files hit a
later edit whose anchor text was not found, so they stand at an INTERMEDIATE
state: syntactically fine, behaviourally unverified.  ALL OF THEM COMPILE, which
is why compilation cannot be the witness for them.

This tool asks two things the recovery's honesty depends on:
  1. every file recorded as partial still EXISTS (a record naming a vanished
     file is stale, and staleness here means a reader trusts the wrong set);
  2. the record is REACHABLE — the provenance note is present in the tree, so a
     reader meets the caveat without being told to look for it.

    scripts/check_partial.py           # exit 0 iff the record is intact
    scripts/check_partial.py --list    # the files known to be partial

⚑ THIS IS A RECORD CHECK, NOT A CORRECTNESS CHECK.  It cannot tell you a partial
file behaves correctly — nothing here can, short of running the original.  It
keeps the SET honest so the uncertainty stays visible instead of decaying into
an assumption that everything recovered cleanly.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOTES = "RECOVERY-NOTES.md"

# The archive's own ** PARTIAL ** roster.  Hand-transcribed from the recovery
# notes ONCE; the notes remain the provenance record and this is the checkable
# form.  A file leaves this set only when something verifies its behaviour.
PARTIAL = (
    "cvd_gate.py",
    "glance_audit.py",
    "make_clock.py",
    "make_deb.py",
    "make_font.py",
    "make_palette.py",
    "make_schemes.py",
    "make_wallpaper.py",
)


def main(argv):
    known = {"--list"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_partial: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--list" in argv:
        print("\n".join(PARTIAL))
        return 0
    problems = []
    gone = [f for f in PARTIAL if not os.path.exists(os.path.join(ROOT, f))]
    if gone:
        problems.append(f"recorded as partial but absent from the tree: {', '.join(gone)}")
    notes = os.path.join(ROOT, NOTES)
    if not os.path.exists(notes):
        problems.append(f"{NOTES} is absent — the provenance record is unreachable")
    else:
        text = open(notes, encoding="utf-8", errors="replace").read()
        unmentioned = [f for f in PARTIAL if f not in text]
        if unmentioned:
            problems.append(f"{NOTES} does not mention: {', '.join(unmentioned)}")
    if problems:
        print(f"check_partial: REFUSED — the partial-recovery record is not intact:",
              file=sys.stderr)
        for p in problems:
            print(f"    {p}", file=sys.stderr)
        return 1
    print(f"check_partial: {len(PARTIAL)} of {len(PARTIAL)} partial files present "
          f"and named in {NOTES}")
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

    check("roster is non-empty", len(PARTIAL) > 0, True)
    check("roster has no duplicates", len(set(PARTIAL)), len(PARTIAL))
    print("check_partial selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
