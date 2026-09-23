#!/usr/bin/env python3
"""check_mark.py — the trademark-scrub witness.

The project was first built under a name derived from a registered trademark.
Every occurrence was removed; this asks whether it has come back.

The requirement is policy/mark.rego (decided by scripts/opa_gate.py mark): which
paths are excluded and why, and that an ATTRIBUTION line is allowed while every
other occurrence is a finding. This file only MEASURES: every file in the tree
(the population, from scripts/git_tracked.py) and, per file, each line carrying
the mark — its count, and whether it reads as attribution.

    scripts/check_mark.py            # the verdict, as opa_gate mark decides it
    scripts/check_mark.py --json     # the measurement policy/mark.rego decides
    scripts/check_mark.py --count    # the occurrence count the POLICY finds (the figure for a claim)
    scripts/check_mark.py --files    # the files the POLICY finds carrying it, one per line
    scripts/check_mark.py --selftest # the measurement can SEE the mark

⚑ THE SCRUB IS ONE QUESTION WITH ONE OWNER.  This is the only place that knows
the retired mark, so a second spelling of the check cannot drift from it.  The
worklist cites the gate over this script; the pre-commit gate runs the same one.

⚑ THIS FILE IS NECESSARILY THE ONE EXCEPTION.  A checker for a string must name
the string it looks for, so this file always "contains the mark" — and a naive
scan of the tree would therefore never go green.  SELF is excluded by PATH (in
policy/mark.rego), not by a clever spelling: obfuscating the needle
(`"ind" + "iglo"`) would hide it from the very grep a human runs to audit this,
which is worse than an honest exclusion recorded there.

⚑ AND THE WORKLIST'S OWN PROSE IS NOT EXCLUDED.  A claim that says "the mark is
gone" must itself not carry it, or the document certifying the absence would be
a counterexample to it.  The claims are phrased as "the prior mark" precisely so
this scan can cover them.

Weakness: binary files are not read (git grep -I; the walk reads them as text
with replacement); a mark split across a line break is not seen.
"""
import json
import os
import subprocess
import sys

# The retired mark, case-insensitive.  One definition, one owner.
MARK = "indiglo"

# ⚑ ATTRIBUTION IS NOT SELF-NAMING, AND THE MEASUREMENT MUST TELL THEM APART.
#
# Two different acts share the same word.  Calling the project by the mark is
# what the rename ended.  Naming the product that INSPIRED the look — "the Timex
# Indiglo era: ZnS:Cu phosphor…" — is nominative reference: it describes what the
# theme imitates, which is a fact about the visual target and is exactly how you
# are permitted to refer to someone else's mark.
#
# So each line is measured for the ATTRIBUTION PHRASE, not the bare word, so a
# future line that merely mentions the mark in passing still shows up; the policy
# decides that an attribution line is allowed.
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


def _line(lineno, text):
    return {"line": lineno, "count": text.lower().count(MARK), "attribution": _is_attribution(text)}


def _lines_git(root):
    """{path: [line facts]} from git grep, which knows what is tracked. None if git
    cannot answer.

    ⚑ PER LINE, NOT PER FILE.  `git grep -c` counts matches per file, which cannot
    tell an allowed attribution from a disallowed self-naming in the same file —
    and one allowed line would then excuse every other occurrence around it."""
    r = subprocess.run(["git", "-C", root, "grep", "-Iin", "-e", MARK, "--", "."],
                       capture_output=True, text=True)
    # rc 1 = no match; rc >1 = git could not answer (e.g. not a repo).
    if r.returncode > 1:
        return None
    out = {}
    for entry in r.stdout.splitlines():
        path, _, rest = entry.partition(":")
        lineno, _, text = rest.partition(":")
        if path:
            out.setdefault(path, []).append(_line(int(lineno), text))
    return out


def _lines_walk(root, paths):
    """{path: [line facts]} by reading each file.

    ⚑ WHY THIS EXISTS.  The git path cannot run where there is no git repo — which
    is precisely the Δ mutation sandbox, a plain copy of the tree.  With only the
    git path this check REFUSED there, so paperkit could not grade it and it stood
    `broken`: an ungradeable check is one nobody has shown can fail.  The scan must
    be able to answer wherever the files are, not only where the VCS is."""
    out = {}
    for rel in paths:
        try:
            with open(os.path.join(root, rel), encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        hits = [_line(i, ln) for i, ln in enumerate(text.splitlines(), 1) if MARK in ln.lower()]
        if hits:
            out[rel] = hits
    return out


def measure(root=ROOT):
    """{'mark', 'source', 'cases': [{path, lines: [{line, count, attribution}]}]} over
    EVERY file in the tree — the population is the tree, not the hits, so an empty
    scan and a clean one differ.

    ⚑ AND THE SANDBOX HOLDS MORE THAN THE TREE (2026-09-23). paperkit copies the
    root whole, so .claude/worktrees/ (agents' full checkouts) came with it and a
    bare walk scanned every one. The population is scripts/git_tracked.py's, whose
    no-git path is a walk bounded structurally (nested checkouts and copies of this
    tree, .gitignore'd dirs) — one authority, not a skip-list here."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import git_tracked
    paths = [p for p in git_tracked.files(root=root) if p.split("/", 1)[0] not in _SKIP_DIRS]
    got = _lines_git(root)
    source = "git"
    if got is None:
        got, source = _lines_walk(root, paths), "walk"
    return {"mark": MARK, "source": source,
            "cases": [{"path": p, "lines": got.get(p, [])} for p in paths]}


def main(argv):
    known = {"--count", "--files", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_mark: unknown flag {a!r} (known: {', '.join(sorted(known))})",
                  file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    if "--count" in argv or "--files" in argv:
        if not opa_gate.OPA:
            print("check_mark: SKIP — opa is not installed on this host", file=sys.stderr)
            return 0
        offending = opa_gate.value("mark", measure()).get("offending", {})
        if "--count" in argv:
            print(sum(offending.values()))
        else:
            for p in sorted(offending):
                print(p)
        return 0
    return opa_gate.gate("mark")


def _selftest():
    """The scan must SEE the mark where it exists, or its all-clear means nothing."""
    import shutil
    import tempfile
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    def hits(m):
        return {c["path"]: c["lines"] for c in m["cases"] if c["lines"]}

    live = measure()
    check("the live population is non-empty", len(live["cases"]) > 0, True)
    check("the live scan SEES this file's own needle", "scripts/check_mark.py" in hits(live), True)

    # ⚑ BOTH PATHS ARE EXERCISED: the walk is the one the Δ sandbox uses (no git
    # there), so testing only the git path would leave the load-bearing branch unproven.
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "planted.txt"), "w").write(f"a {MARK} here\n")
        m = measure(td)
        check("the walk is used when git cannot answer", m["source"], "walk")
        check("the walk SEES a planted mark", hits(m),
              {"planted.txt": [{"line": 1, "count": 1, "attribution": False}]})
        # a worktree copy inside the sandbox is not the tree (2026-09-23)
        wt = os.path.join(td, ".claude", "worktrees", "a")
        os.makedirs(os.path.join(wt, "scripts"))
        open(os.path.join(wt, "scripts", "git_tracked.py"), "w").write("")
        open(os.path.join(wt, "planted.txt"), "w").write(f"a {MARK} here\n")
        check("the walk does NOT descend a nested copy of the tree", list(hits(measure(td))), ["planted.txt"])
        shutil.rmtree(os.path.join(td, ".claude"))
        os.remove(os.path.join(td, "planted.txt"))
        open(os.path.join(td, "attrib.md"), "w").write(
            "looks like the Timex Indiglo era: ZnS:Cu phosphor\n")
        open(os.path.join(td, "selfname.md"), "w").write("welcome to EL-Indiglo, our theme\n")
        h = hits(measure(td))
        check("an attribution line is SEEN as attribution", h.get("attrib.md", [{}])[0].get("attribution"), True)
        check("self-naming is SEEN as not attribution", h.get("selfname.md", [{}])[0].get("attribution"), False)
    print("check_mark selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
