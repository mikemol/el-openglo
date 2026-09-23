#!/usr/bin/env python3
"""check_partial.py — the partial-recovery record is intact and honest.

The archive replayed the lost tree from session transcripts.  Eight files hit a
later edit whose anchor text was not found, so they stand at an INTERMEDIATE
state: syntactically fine, behaviourally unverified.  ALL OF THEM COMPILE, which
is why compilation cannot be the witness for them.

The requirement (policy/partial.rego, decided by scripts/opa_gate.py partial):
  1. every file recorded as partial still EXISTS (a record naming a vanished
     file is stale, and staleness here means a reader trusts the wrong set);
  2. the record is REACHABLE — the provenance note is present in the tree and
     names every partial file, so a reader meets the caveat without being told
     to look for it.
This file only MEASURES: for each roster entry, does it exist, is it named.

    scripts/check_partial.py           # the verdict, as opa_gate partial decides it
    scripts/check_partial.py --json    # the measurement policy/partial.rego decides
    scripts/check_partial.py --list    # the files known to be partial
    scripts/check_partial.py --selftest

⚑ THIS IS A RECORD CHECK, NOT A CORRECTNESS CHECK.  It cannot tell you a partial
file behaves correctly — nothing here can, short of running the original.  It
keeps the SET honest so the uncertainty stays visible instead of decaying into
an assumption that everything recovered cleanly.  Weakness: "named" is a
substring test on the notes, so a name mentioned in passing counts.
"""
import json
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


def measure(root=ROOT, roster=PARTIAL):
    """{'notes': NOTES, 'notes_present': bool, 'cases': [{file, exists, named}]}."""
    notes = os.path.join(root, NOTES)
    text = None
    if os.path.exists(notes):
        with open(notes, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
    return {"notes": NOTES, "notes_present": text is not None,
            "cases": [{"file": f, "exists": os.path.exists(os.path.join(root, f)),
                       "named": text is not None and f in text} for f in roster]}


def main(argv):
    known = {"--list", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_partial: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--list" in argv:
        print("\n".join(PARTIAL))
        return 0
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("partial")


def _selftest():
    """The measurement can SEE a vanished file and an unnamed one."""
    import tempfile
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    check("roster is non-empty", len(PARTIAL) > 0, True)
    check("roster has no duplicates", len(set(PARTIAL)), len(PARTIAL))
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "a.py"), "w").write("")
        check("notes absent is SEEN", measure(td, ("a.py",))["notes_present"], False)
        open(os.path.join(td, NOTES), "w").write("a.py is partial\n")
        m = measure(td, ("a.py", "b.py"))
        check("a present, named file is seen as such", m["cases"][0], {"file": "a.py", "exists": True, "named": True})
        check("a vanished, unnamed file is SEEN", m["cases"][1], {"file": "b.py", "exists": False, "named": False})
    print("check_partial selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
