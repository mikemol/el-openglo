#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_census.py — is every tracked file a named input of some gate stage?

⚑ WHY (W488, operator rule 2026-10-06: "a tracked gated file missing from the list must itself fail the
gate"). Naming inputs one by one (select_tracked, never a glob) only helps if a file nobody named is
SEEN. A stage reads what its runfiles hold, and its runfiles hold exactly its declared `data`, so the
census is itself a stage whose `data` is the UNION of every other stage's inputs (BUILD.bazel computes
it) and it asks: is each tracked file present in my runfiles tree, or declared exempt with a reason?
(A bazel query from inside a bazel test would deadlock on the server lock; the runfiles are the
declaration, already materialised.)

    scripts/check_census.py            # the verdict, as opa_gate census decides it
    scripts/check_census.py --json     # the measurement (policy/census.rego decides)
    scripts/check_census.py --selftest

The runfiles tree comes from $CENSUS_RUNFILES (gate/stage.sh sets it under bazel). Outside bazel there
is no declaration to compare against, so the measurement is WITHHELD (counted, printed), never a pass.
The exempt list is gate/census_exempt.tsv: `path<TAB>reason`, one per line, `#` comments.

⚑ WEAKNESSES, STATED. (1) With every stage's `data` the whole tracked list (the fail-safe
over-approximation, until W458 narrows each stage to its closure) every file is named, so the census
is vacuous on the real tree TODAY; the selftest proves it can refuse on fixtures, and it becomes the
guard the day a stage's data is narrowed. (2) Present in the runfiles means DECLARED, not READ: a
named file no stage reads is not seen here (that is W458's closure). (3) Only the index is the
population: an untracked file is not a tracked file nobody named.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

EXEMPT_FILE = os.path.join("gate", "census_exempt.tsv")


def parse_exempt(text):
    """{path: reason} from the exempt list's text (`path<TAB>reason`, `#` comments)."""
    out = {}
    for raw in text.splitlines():
        line = raw.rstrip("\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        path, _, reason = line.partition("\t")
        out[path.strip()] = reason.strip()
    return out


def runfiles_listing(runfiles):
    """The repo-relative paths of every file in a runfiles tree (symlinks to files included)."""
    seen = set()
    # population: the census stage's own runfiles tree, which IS what is measured (its declared data), not the repo's work tree
    for dirpath, _dirs, files in os.walk(runfiles):
        for f in files:
            seen.add(os.path.relpath(os.path.join(dirpath, f), runfiles))
    return seen


def measure(tracked, named, exempt, checked=True):
    """The MEASUREMENT policy/census.rego decides. `named` is the set of paths the runfiles hold
    (None when there is no runfiles tree to compare against)."""
    if not checked or named is None:
        return {
            "checked": False,
            "cases": [],
            "tracked": len(tracked),
            "withheld": "no runfiles tree: not run under bazel (CENSUS_RUNFILES unset)",
        }
    cases = []
    for p in sorted(tracked):
        is_named = p in named
        if p in exempt:
            status = "stale" if is_named else ("exempt" if exempt[p] else "unreasoned")
        else:
            status = "named" if is_named else "unnamed"
        cases.append({"path": p, "status": status, "reason": exempt.get(p, "")})
    for p in sorted(set(exempt) - set(tracked)):
        cases.append({"path": p, "status": "gone", "reason": exempt[p]})
    return {"checked": True, "cases": cases, "tracked": len(tracked), "withheld": None}


def measure_here():
    """measure() over this tree: the index, the exempt file, and $CENSUS_RUNFILES."""
    import git_tracked

    tracked = git_tracked.files()
    exempt_path = os.path.join(ROOT, EXEMPT_FILE)
    exempt = {}
    if os.path.isfile(exempt_path):
        with open(exempt_path, encoding="utf-8") as fh:
            exempt = parse_exempt(fh.read())
    runfiles = os.environ.get("CENSUS_RUNFILES", "")
    named = runfiles_listing(runfiles) if runfiles and os.path.isdir(runfiles) else None
    return measure(tracked, named, exempt)


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_census: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json

        print(json.dumps(measure_here(), indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("census")


def _selftest():
    import tempfile

    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    def states(m):
        return {c["path"]: c["status"] for c in m["cases"]}

    tracked = ["a.py", "b.py", "c.py"]
    chk(
        "a tracked file in the runfiles is named, one outside them is UNNAMED",
        states(measure(tracked, {"a.py", "b.py"}, {})),
        {"a.py": "named", "b.py": "named", "c.py": "unnamed"},
    )
    chk(
        "an unnamed file declared exempt WITH a reason is exempt",
        states(measure(tracked, {"a.py", "b.py"}, {"c.py": "generated"}))["c.py"],
        "exempt",
    )
    chk(
        "an exemption with no reason is its own state",
        states(measure(tracked, {"a.py", "b.py"}, {"c.py": ""}))["c.py"],
        "unreasoned",
    )
    chk(
        "an exemption for a file that IS named is stale",
        states(measure(tracked, {"a.py", "b.py", "c.py"}, {"c.py": "old"}))["c.py"],
        "stale",
    )
    chk(
        "an exemption for a file that is not tracked is gone",
        states(measure(tracked, set(tracked), {"zz.py": "was here"}))["zz.py"],
        "gone",
    )
    m = measure(tracked, None, {})
    chk(
        "no runfiles tree is withheld with its reason, never judged",
        (m["checked"], m["cases"], bool(m["withheld"])),
        (False, [], True),
    )
    chk(
        "the exempt list parses path, tab, reason and skips comments and blanks",
        parse_exempt("# c\n\nx.py\tgenerated\ny.py\t\n"),
        {"x.py": "generated", "y.py": ""},
    )
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "d"))
        for rel in ("a.py", os.path.join("d", "b.py")):
            with open(os.path.join(td, rel), "w", encoding="utf-8") as fh:
                fh.write("x")
        os.symlink(os.path.join(td, "a.py"), os.path.join(td, "linked.py"))
        chk(
            "a runfiles tree lists files in subdirectories and symlinks to files",
            sorted(runfiles_listing(td)),
            ["a.py", "d/b.py", "linked.py"],
        )
    print("check_census selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
