#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""typing_edges.py — make the typing cleanup order a graph (W691, under W553)

Operator, 2026-10-18: the house census follows imports on purpose, "it provides a topological
sort order for getting things cleaned up". A weight cannot carry that order (nemik recomputes
weights from the graph), so this writes it as edges: the debt card of a file that imports
another debt file is blocked on that file's card, which leaves the files whose imports are
clean as the only ready ones.

    scripts/typing_edges.py            # the edges it would write, the cycles it cut, n of m
    scripts/typing_edges.py --apply    # write them with mikemol-paths-forward --update
    scripts/typing_edges.py --selftest

The importers come from `mikemol-pycodemod importers MODULE ROOT` (one call per debt file,
the repo's static-import reader; this does not read imports itself).

⚑ WEAKNESS, STATED. The module name is the file's stem, so two files with one stem (a script
and a root module) share importers, and an import inside a function counts like one at the
top. A dependency cycle cannot be an order: the edge that closes it is cut, listed, and left
unwritten. A card that already has blockers keeps them; the new ones are added.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

PYCODEMOD = os.path.join(ROOT, ".venv", "bin", "mikemol-pycodemod")


def importer_files(output: str) -> set[str]:
    """The repo-relative files named by `importers` rows (`<kind> <names> <path>:<line>`)."""
    out: set[str] = set()
    for row in output.splitlines():
        head = row.split(" ", 1)[0]
        if head not in ("import", "from"):
            continue
        where = row.rsplit(" ", 1)[-1]
        path = where.rsplit(":", 1)[0]
        if path.startswith(ROOT + os.sep):
            out.add(os.path.relpath(path, ROOT))
    return out


def edges_of(importers: dict[str, set[str]], debt: set[str]) -> set[tuple[str, str]]:
    """(importer, imported) pairs between two debt files, never a file with itself."""
    return {(g, f) for f, gs in importers.items() for g in gs if g in debt and g != f}


def acyclic(
    edges: set[tuple[str, str]],
) -> tuple[set[tuple[str, str]], list[tuple[str, str]]]:
    """(kept, cut): edges in a deterministic order, each kept unless it closes a cycle."""
    kept: set[tuple[str, str]] = set()
    cut: list[tuple[str, str]] = []
    reach: dict[str, set[str]] = {}

    def below(x: str) -> set[str]:
        seen: set[str] = set()
        todo = [x]
        while todo:
            n = todo.pop()
            for g, f in kept:
                if g == n and f not in seen:
                    seen.add(f)
                    todo.append(f)
        return seen

    for g, f in sorted(edges):
        reach[f] = below(f)
        if g in reach[f]:
            cut.append((g, f))
        else:
            kept.add((g, f))
    return kept, cut


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args not in ([], ["--apply"]):
        print(f"typing_edges: unknown arguments {args!r}", file=sys.stderr)
        return 2
    import typing_plan

    with open(typing_plan.STATE, encoding="utf-8") as fh:
        cards = typing_plan.debt_cards(json.load(fh)["waypoints"])
    if not cards:
        print("typing_edges: no open debt card was read", file=sys.stderr)
        return 2
    sym = {f: s for s, f in cards}
    importers: dict[str, set[str]] = {}
    for f in sorted(sym):
        mod = os.path.splitext(os.path.basename(f))[0]
        run = subprocess.run(
            [
                PYCODEMOD,
                "importers",
                mod,
                ROOT,
                "--exclude",
                ".venv",
                "--exclude",
                "worktrees",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        importers[f] = importer_files(run.stdout)
    kept, cut = acyclic(edges_of(importers, set(sym)))
    enables: dict[str, list[str]] = {}
    waiting: set[str] = set()
    for g, f in sorted(kept):
        enables.setdefault(f, []).append(sym[g])
        waiting.add(g)
    for f in sorted(enables):
        print(f"{sym[f]}\t{f}\tenables {' '.join(sorted(enables[f]))}")
        if args == ["--apply"]:
            argv_w = [typing_plan.WRITER, "--state", typing_plan.STATE]
            argv_w += ["--update", sym[f], "--add-enables", *sorted(enables[f])]
            subprocess.run(argv_w, check=True)
    for g, f in cut:
        print(f"CUT\t{g} imports {f}: the edge closes a cycle")
    print(
        f"typing_edges: {len(waiting)} of {len(sym)} debt card(s) wait on an imported "
        f"debt file, {len(sym) - len(waiting)} are leaves; {len(cut)} cycle edge(s) cut",
        file=sys.stderr,
    )
    return 0


def _selftest() -> bool:
    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        mark = "ok  " if got == want else "FAIL"
        extra = "" if got == want else f": got {got!r} want {want!r}"
        print(f"  {mark} {label}{extra}")
        ok = ok and got == want

    row = (
        f"from atomic_write {ROOT}/make_x.py:22\nimport emitters {ROOT}/scripts/c.py:5"
    )
    chk(
        "importer rows give repo-relative files",
        importer_files("skipped 1 virtualenvs\n" + row),
        {"make_x.py", "scripts/c.py"},
    )
    chk(
        "a path outside the repo is not an importer",
        importer_files("import x /other/y.py:1"),
        set(),
    )
    imp = {"a.py": {"b.py", "z.py"}, "b.py": {"c.py"}, "c.py": set()}
    chk(
        "only edges between two debt files are kept, never a self edge",
        edges_of({**imp, "a.py": {"b.py", "z.py", "a.py"}}, {"a.py", "b.py", "c.py"}),
        {("b.py", "a.py"), ("c.py", "b.py")},
    )
    kept, cut = acyclic({("b.py", "a.py"), ("a.py", "b.py"), ("c.py", "b.py")})
    chk("an edge that closes a cycle is cut and listed", (len(kept), len(cut)), (2, 1))
    chk(
        "an acyclic set is kept whole",
        acyclic({("b.py", "a.py"), ("c.py", "b.py")}),
        ({("b.py", "a.py"), ("c.py", "b.py")}, []),
    )
    print("typing_edges selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
