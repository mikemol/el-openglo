#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_routes.py — the structural-query hook reads a routing table of OUR own.

THE MEASURED FAILURE THIS EXISTS FOR.  The structural-query hook does not hold
its routing map; it PARSES it out of the struct-tools skill at run time, so
adding a row teaches the hook with no code change.  Resolve the hook's root from
`__file__` and symlink it into a repo with no such skill, and the table comes
back EMPTY — the hook then still fires, still refuses, and names no tool.  It
degrades to a contentless "don't" instead of failing loudly.  Verified by
experiment before the hook was adopted here.

So: a non-empty table is a claim in its own right, separate from the hook's
selftest passing.  The requirement is policy/routes.rego (decided by
scripts/opa_gate.py routes); this file MEASURES: is the hook installed, is the
local skill present, and which rows does the hook itself report.

    scripts/check_routes.py            # the verdict, as opa_gate routes decides it
    scripts/check_routes.py --json     # the measurement policy/routes.rego decides
    scripts/check_routes.py --routes   # the rows, as the hook sees them
    scripts/check_routes.py --selftest

Weakness: a row's tool is read as its FIRST word (W243): a path in the repo or a console script in the gate
venv's bin must exist (policy R4 denies a miss); a path outside the repo root (`../...`) is denied outright,
present or not (W738, operator ruling 2026-10-19: repos must not know sibling checkouts exist); a column
whose first word names no path is withheld, counted and printed.
"""

import json
import os
import sys

from check_venv_path import venv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# ⚑ THE HOOK IS mtools' INSTALLED COMMAND SINCE W99 (2026-10-02), not a symlinked
# script. It has no --routes flag (it reads a hook event from stdin and ignores argv),
# so the table is read through the SAME function the hook calls, from the installed
# package: mikemol.hooks.routing_table.routes - asking the tool, not re-parsing the skill.
# The environment is venv(ROOT): EL_VENV when the gate built a snapshot venv (W698), else .venv.
HOOK = os.path.join(venv(ROOT), "bin", "mikemol-hook-structural-query")
SKILL = os.path.join(ROOT, ".claude", "skills", "struct-tools", "SKILL.md")


def routes(hook=HOOK, skill=SKILL):
    """The hook's own view of its table: the installed hook's reader over our skill."""
    if not os.path.exists(hook) or not os.path.exists(skill):
        return None
    try:
        from pathlib import Path

        from mikemol.hooks import routing_table
    except ImportError:
        return None
    return [f"{a}\t{t}" for a, t in routing_table.routes(Path(skill))]


def tool_resolution(tool, root=ROOT):
    """(token, resolves): the first word of a row's tool column and whether it exists here (W243).

    A word with a "/" or ending in ".py" is a PATH, read against the repo root; a path outside the repo
    root (`../...`) never resolves (W738); a bare word that is a file in the gate venv's bin is a console script, and a
    "mikemol-" word that is not there does not resolve. A column whose first word names neither is
    (word, None): it names no path, so nothing is judged and the row is counted, never admitted as
    resolved. Weakness: only the FIRST word is read, so a row that joins two tools with ` + ` is judged
    by the first."""
    words = tool.replace("`", " ").split()
    if not words:
        return "", None
    word = words[0]
    if word.startswith("../"):
        # W738, operator ruling 2026-10-19: a repo must not know sibling checkouts exist, so a path outside
        # the repo root never resolves, whether or not the sibling is present on this machine
        return word, False
    if "/" in word or word.endswith(".py"):
        return word, os.path.exists(os.path.join(root, word))
    if os.path.exists(os.path.join(venv(root), "bin", word)):
        return word, True
    return word, False if word.startswith("mikemol-") else None


def measure(hook=HOOK, skill=SKILL):
    cases = []
    for r in routes(hook, skill) or []:
        _artifact, _, tool = r.partition("\t")
        word, resolves = tool_resolution(tool)
        cases.append({"row": r, "tool": word, "resolves": resolves})
    return {
        "hook": os.path.relpath(hook, ROOT),
        "hook_present": os.path.exists(hook),
        "skill": os.path.relpath(skill, ROOT),
        "skill_present": os.path.exists(skill),
        "cases": cases,
    }


def main(argv):
    known = {"--routes", "--json"}
    operands = [a for a in argv[1:] if not a.startswith("--")]
    for a in argv[1:]:
        if a.startswith("--") and a not in known:
            print(f"check_routes: unknown flag {a!r}", file=sys.stderr)
            return 2
    if len(operands) > 1 or (operands and "--json" not in argv):
        print("check_routes: --json takes at most one skill file", file=sys.stderr)
        return 2
    if "--json" in argv:
        # W75: one operand is a FIXTURE skill, measured instead of this repo's own table
        doc = measure(skill=operands[0]) if operands else measure()
        print(json.dumps(doc, indent=1))
        return 0
    if "--routes" in argv:
        print("\n".join(routes() or []))
        return 0
    import opa_gate

    return opa_gate.gate("routes")


def _selftest():
    """The measurement can SEE the table, and can SEE a hook that is not there."""
    ok = True

    def check(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    check("SKILL path is repo-local", SKILL.startswith(ROOT), True)
    check(
        "HOOK path is the gate venv's (EL_VENV when set, else the repo's .venv)",
        HOOK,
        os.path.join(venv(ROOT), "bin", "mikemol-hook-structural-query"),
    )
    gone = measure(
        hook=os.path.join(ROOT, ".venv", "bin", "mikemol-hook-no-such"),
        skill=os.path.join(ROOT, "no_such_skill.md"),
    )
    check(
        "an absent hook is SEEN, with no rows",
        (gone["hook_present"], gone["skill_present"], gone["cases"]),
        (False, False, []),
    )
    check("the live hook reports rows", len(measure()["cases"]) > 0, True)
    fixture = measure(
        skill=os.path.join(ROOT, "catalog/fixtures/routes/outside-root.md")
    )
    check(
        "a fixture skill with a row outside the repo root is SEEN as unresolved (W75)",
        [c["resolves"] for c in fixture["cases"]],
        [False],
    )
    check(
        "a path that exists resolves, one that does not does not, and a wrapped column reads its first word (W243)",
        (
            tool_resolution("scripts/check_routes.py")[1],
            tool_resolution("scripts/no_such_tool.py")[1],
            tool_resolution("`scripts/check_routes.py` + `x`")[0],
        ),
        (True, False, "scripts/check_routes.py"),
    )
    check(
        "a path outside the repo root never resolves, present or not (W738)",
        (
            tool_resolution("../no_such_sibling/tool.py")[1],
            tool_resolution("../el-openglo/scripts/check_routes.py")[1],
        ),
        (False, False),
    )
    check(
        "a mikemol- console script that is not installed does not resolve; a word naming no path is not judged",
        (
            tool_resolution("mikemol-no-such-tool")[1],
            tool_resolution("(none)")[1],
            tool_resolution("")[1],
        ),
        (False, None, None),
    )
    check(
        "an installed console script resolves",
        tool_resolution("mikemol-paths-forward")[1],
        True,
    )
    print("check_routes selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
