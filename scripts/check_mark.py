#!/usr/bin/env python3
"""check_mark.py — the trademark-scrub witness.

The project was first built under a name derived from a registered trademark.
Every occurrence was removed; this asks whether it has come back.

    scripts/check_mark.py            # exit 0 iff the mark is absent; else list the hits
    scripts/check_mark.py --count    # print the occurrence count (the figure for a claim)
    scripts/check_mark.py --files    # the files carrying it, one per line

⚑ THE SCRUB IS ONE QUESTION WITH ONE OWNER.  This is the only place that knows
the retired mark, so a second spelling of the check cannot drift from it.  The
worklist cites this script; the pre-commit gate runs the same script.

⚑ THIS FILE IS NECESSARILY THE ONE EXCEPTION.  A checker for a string must name
the string it looks for, so this file always "contains the mark" — and a naive
scan of the tree would therefore never go green.  SELF is excluded by PATH, not
by a clever spelling: obfuscating the needle (`"ind" + "iglo"`) would hide it
from the very grep a human runs to audit this, which is worse than an honest
exclusion recorded here.

⚑ AND THE WORKLIST'S OWN PROSE IS NOT EXCLUDED.  A claim that says "the mark is
gone" must itself not carry it, or the document certifying the absence would be
a counterexample to it.  The claims are phrased as "the prior mark" precisely so
this scan can cover them.
"""
import os
import subprocess
import sys

# The retired mark, case-insensitive.  One definition, one owner.
MARK = "indiglo"

# Paths excluded from the scan, each for a stated reason.
EXCLUDE = {
    "scripts/check_mark.py":   "this file must name the mark to look for it",
    "RECOVERY-NOTES.md":       "verbatim provenance record of the pre-rename recovery",
}

# ⚑ ATTRIBUTION IS NOT SELF-NAMING, AND THE CHECK MUST TELL THEM APART.
#
# Two different acts share the same word.  Calling the project by the mark is
# what the rename ended.  Naming the product that INSPIRED the look — "the Timex
# Indiglo era: ZnS:Cu phosphor…" — is nominative reference: it describes what the
# theme imitates, which is a fact about the visual target and is exactly how you
# are permitted to refer to someone else's mark.
#
# So the scan is not a blanket ban on a string.  A line is ALLOWED when it reads
# as attribution; every other occurrence is a finding.  This is deliberately
# narrow: it matches the ATTRIBUTION PHRASE, not the bare word, so a future line
# that merely mentions the mark in passing still shows up.
ATTRIBUTION = (
    "timex indiglo era",        # the design log's statement of the visual target
)


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Directories never worth scanning (and ruinous to walk).
_SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".mypy_cache"}


def _is_attribution(line):
    """True if this line names the mark as the thing the theme IMITATES."""
    low = line.lower()
    return any(phrase in low for phrase in ATTRIBUTION)


def _hits_git():
    """Fast path: ask git, which already knows what is tracked.  None if unavailable.

    ⚑ PER LINE, NOT PER FILE.  `git grep -c` counts matches per file, which cannot
    tell an allowed attribution from a disallowed self-naming in the same file —
    and one allowed line would then excuse every other occurrence around it."""
    r = subprocess.run(["git", "-C", ROOT, "grep", "-Iin", "-e", MARK, "--", "."],
                       capture_output=True, text=True)
    # rc 1 = no match (clean); rc >1 = git could not answer (e.g. not a repo).
    if r.returncode > 1:
        return None
    counts = {}
    for entry in r.stdout.splitlines():
        path, _, rest = entry.partition(":")
        _lineno, _, text = rest.partition(":")
        if not path or _is_attribution(text):
            continue
        counts[path] = counts.get(path, 0) + text.lower().count(MARK)
    return sorted(counts.items())


def _hits_walk():
    """Fallback: walk the tree.

    ⚑ WHY THIS EXISTS.  The git path cannot run where there is no git repo — which
    is precisely the Δ mutation sandbox, a plain copy of the tree.  With only the
    git path this check REFUSED there, so paperkit could not grade it and it stood
    `broken`: an ungradeable check is one nobody has shown can fail.  The scan must
    be able to answer wherever the files are, not only where the VCS is."""
    out = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if d not in _SKIP_DIRS]
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            # per LINE, so an allowed attribution cannot excuse its neighbours
            n = sum(line.lower().count(MARK) for line in text.splitlines()
                    if not _is_attribution(line))
            if n:
                out.append((os.path.relpath(p, ROOT), n))
    return sorted(out)


def hits():
    """[(path, n_occurrences)] for files carrying the mark, excluding EXCLUDE."""
    got = _hits_git()
    if got is None:
        got = _hits_walk()
    return [(p, n) for p, n in got if p not in EXCLUDE]


def main(argv):
    known = {"--count", "--files"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_mark: unknown flag {a!r} (known: {', '.join(sorted(known))})",
                  file=sys.stderr)
            return 2
    h = hits()
    total = sum(n for _, n in h)
    if "--count" in argv:
        print(total)
        return 0
    if "--files" in argv:
        for p, _ in h:
            print(p)
        return 0
    if h:
        print(f"check_mark: REFUSED — the retired mark appears {total}× in {len(h)} file(s):",
              file=sys.stderr)
        for p, n in h:
            print(f"    {p}  ({n})", file=sys.stderr)
        return 1
    print(f"check_mark: clean — 0 occurrences ({len(EXCLUDE)} path(s) excluded by policy)")
    return 0


def _selftest():
    """The scan must SEE the mark where it exists, or its all-clear means nothing."""
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # The exclusion list must not be able to swallow the whole tree.
    check("SELF is excluded", "scripts/check_mark.py" in EXCLUDE, True)
    check("exclusions are documented", all(EXCLUDE.values()), True)
    # hits() must return a list of (path, positive-count) pairs.
    h = hits()
    check("hits() shape", all(isinstance(p, str) and n > 0 for p, n in h), True)
    check("hits() excludes EXCLUDE", not any(p in EXCLUDE for p, _ in h), True)

    # ⚑ THE SCAN MUST SEE THE MARK, or its all-clear means nothing.  Both paths
    # are exercised: the walk is the one the Δ sandbox uses (no git there), so
    # testing only the git path would leave the load-bearing branch unproven.
    import tempfile
    global ROOT
    keep = ROOT
    try:
        with tempfile.TemporaryDirectory() as td:
            open(os.path.join(td, "planted.txt"), "w").write(f"a {MARK} here\n")
            ROOT = td
            walked = _hits_walk()
            check("the walk SEES a planted mark", walked, [("planted.txt", 1)])
            check("the walk is used when git cannot answer", _hits_git(), None)
            os.remove(os.path.join(td, "planted.txt"))
            check("the walk reports clean when absent", _hits_walk(), [])

            # ⚑ ATTRIBUTION PASSES, SELF-NAMING DOES NOT — and both must be
            # proven, or the allowance is a hole nobody has measured.
            open(os.path.join(td, "attrib.md"), "w").write(
                "looks like the Timex Indiglo era: ZnS:Cu phosphor\n")
            check("an attribution line is allowed", _hits_walk(), [])
            open(os.path.join(td, "selfname.md"), "w").write(
                "welcome to EL-Indiglo, our theme\n")
            check("self-naming is still caught",
                  [p for p, _ in _hits_walk()], ["selfname.md"])
    finally:
        ROOT = keep
    print("check_mark selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
