#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""typing_edges.py — make the typing cleanup order a graph (W691, under W553)

Operator, 2026-10-18: the house census follows imports on purpose, "it provides a topological
sort order for getting things cleaned up". A weight cannot carry that order (nemik recomputes
weights from the graph), so this writes it as edges: the debt card of a file that imports
another debt file is blocked on that file's card, which leaves the files whose imports are
clean as the only ready ones.

    scripts/typing_edges.py            # the plan (what it would drop, enable and block), its hash, n of m
    scripts/typing_edges.py --check    # diff the plan against nemik-check --integrity: exit 1 on any difference
    scripts/typing_edges.py --apply --plan HASH   # write it, only if the plan still hashes to HASH
    scripts/typing_edges.py --selftest

⚑ THE ORDER IS MECHANICAL (github-8f, 2026-10-18, after a bulk apply ran before it was compared with nemik):
--apply refuses without the hash the dry run printed and refuses when the recomputed plan differs, and --check
diffs the plan against nemik's own reading, so the reading cannot be skipped.

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


def waits(
    kept: set[tuple[str, str]], sym: dict[str, str], held: dict[str, list[str]]
) -> dict[str, list[str]]:
    """{importer card: its blocked_on}: what it already waits on, then the card of each debt file it
    imports. ⚑ THE ENABLES EDGE ALONE DISAGREES WITH THE QUEUE (nemik:W695, 2026-10-18, 155 findings):
    a card that enables another says that one cannot proceed without it, so the enabled card must wait
    on it too. Only importers that gain a blocker are returned."""
    out: dict[str, list[str]] = {}
    for g, f in sorted(kept):
        mine = out.setdefault(sym[g], list(held.get(sym[g], [])))
        if sym[f] not in mine:
            mine.append(sym[f])
    return {s: b for s, b in out.items() if b != held.get(s, [])}


def waits_on(card: str, other: str, held: dict[str, list[str]]) -> bool:
    """True when `card` is blocked on `other`, directly or through other cards (nemik's reading of an
    enables edge: a join that also waits on others still waits on this one)."""
    seen: set[str] = set()
    todo = [card]
    while todo:
        n = todo.pop()
        for b in held.get(n, []):
            if b == other:
                return True
            if b not in seen:
                seen.add(b)
                todo.append(b)
    return False


def stale_enables(
    kept: set[tuple[str, str]],
    sym: dict[str, str],
    now: dict[str, list[str]],
    held: dict[str, list[str]] | None = None,
) -> dict[str, list[str]]:
    """{debt card: its enables without the disagreeing ones}: an enables edge between two debt cards that
    the current import analysis does not support AND whose target does not wait on the card.
    ⚑ `--add-enables` ONLY ADDS (nemik:W695, 2026-10-18): an edge written under an earlier cycle cut stays
    after the analysis stops producing it. Only the edges nemik reads as disagreeing are dropped (12 of
    156 findings); a stale edge whose target waits on the card through another chain is not an integrity
    finding and stays (github-8f: the edges changed equal the findings, nothing extra). Edges to cards
    that are not debt cards are left alone; only cards that lose an edge are returned."""
    waiting = held or {}
    debt = set(sym.values())
    want = {f: {sym[g] for g, h in kept if h == f} for f in sym}
    out: dict[str, list[str]] = {}
    for f, card in sym.items():
        have = now.get(card, [])
        keep = [
            e
            for e in have
            if e not in debt or e in want[f] or waits_on(e, card, waiting)
        ]
        if keep != have:
            out[card] = keep
    return out


def plan_lines(
    drops: dict[str, list[str]],
    adds: dict[str, list[str]],
    blocked: dict[str, list[str]],
) -> list[str]:
    """The plan as sorted text lines: what --apply would drop, enable and block, nothing else."""
    lines = [
        f"drop {c} enables {' '.join(sorted(d))}" for c, d in sorted(drops.items())
    ]
    lines += [
        f"enable {c} enables {' '.join(sorted(a))}" for c, a in sorted(adds.items())
    ]
    lines += [f"block {c} blocked_on {' '.join(b)}" for c, b in sorted(blocked.items())]
    return lines


def plan_hash(lines: list[str]) -> str:
    """A short hash of the plan text: the dry run prints it, --apply must be given it back."""
    import hashlib

    return hashlib.sha256("\n".join(lines).encode()).hexdigest()[:16]


def fix_edges(
    drops: dict[str, list[str]],
    blocked: dict[str, list[str]],
    held: dict[str, list[str]],
    now: dict[str, list[str]],
) -> set[tuple[str, str]]:
    """(enabler, enabled) edges the plan changes that ALREADY exist as enables edges: a dropped edge, or a
    blocker added to the enabled card. A new enables edge written with its blocker together is a new
    consistent pair, not the repair of a finding, so it is not here."""
    existing = {(g, e) for g, es in now.items() for e in es}
    dropped = {(c, e) for c, es in drops.items() for e in es}
    added = {
        (b, c) for c, bs in blocked.items() for b in bs if b not in held.get(c, [])
    }
    return (dropped | added) & existing


def finding_edges(text: str) -> tuple[set[tuple[str, str]], int]:
    """(edges, other): the local (enabler, enabled) pairs nemik's integrity reading names, and the number of
    findings it names that point into another repo (this tool cannot repair those)."""
    import re

    local = re.compile(
        r"^el-openglo:(W\d+): enables el-openglo:(W\d+), which does not wait"
    )
    edges: set[tuple[str, str]] = set()
    other = 0
    for row in text.splitlines():
        m = local.match(row)
        if m:
            edges.add((m[1], m[2]))
        elif ", which does not wait on it" in row:
            other += 1
    return edges, other


def diff_plan(
    plan_fix: set[tuple[str, str]],
    findings: set[tuple[str, str]],
    debt: set[str],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """(unfixed, extra): findings between two debt cards the plan does not repair, and edges the plan changes
    that no finding names. Both empty means the plan equals nemik's reading in the plan's domain."""
    domain = {(a, b) for a, b in findings if a in debt and b in debt}
    return sorted(domain - plan_fix), sorted(plan_fix - domain)


def main(argv: list[str]) -> int:
    args = argv[1:]
    if args[:1] == ["--apply"]:
        if len(args) != 3 or args[1] != "--plan":
            print(
                "typing_edges: --apply needs --plan HASH, the hash the dry run printed",
                file=sys.stderr,
            )
            return 2
        mode = "apply"
    elif args == ["--check"]:
        mode = "check"
    elif args == []:
        mode = "plan"
    else:
        print(f"typing_edges: unknown arguments {args!r}", file=sys.stderr)
        return 2
    import typing_plan

    with open(typing_plan.STATE, encoding="utf-8") as fh:
        wps = json.load(fh)["waypoints"]
    cards = typing_plan.debt_cards(wps)
    held = {w["symbol"]: list(w.get("blocked_on") or []) for w in wps}
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
    blockers = waits(kept, sym, held)
    now = {w["symbol"]: list(w.get("enables") or []) for w in wps}
    stale = stale_enables(kept, sym, now, held)
    drops = {c: sorted(set(now[c]) - set(keep)) for c, keep in stale.items()}
    adds = {sym[f]: sorted(es) for f, es in enables.items()}
    lines = plan_lines(drops, adds, blockers)
    digest = plan_hash(lines)
    print("\n".join(lines))
    for g, f in cut:
        print(f"CUT\t{g} imports {f}: the edge closes a cycle")
    print(f"plan {digest}")
    print(
        f"typing_edges: {len(waiting)} of {len(sym)} debt card(s) wait on an imported "
        f"debt file, {len(sym) - len(waiting)} are leaves; {len(cut)} cycle edge(s) cut",
        file=sys.stderr,
    )
    if mode == "check":
        return check_against_nemik(drops, blockers, held, now, set(sym.values()))
    if mode == "apply":
        if args[2] != digest:
            print(
                f"typing_edges: REFUSED: the plan is {digest}, not {args[2]}; "
                "run the dry run again and read it before applying",
                file=sys.stderr,
            )
            return 1
        write = [typing_plan.WRITER, "--state", typing_plan.STATE, "--update"]
        for card, keep in sorted(stale.items()):
            subprocess.run([*write, card, "--enables", *keep], check=True)
        for f in sorted(enables):
            add = ["--add-enables", *sorted(enables[f])]
            subprocess.run([*write, sym[f], *add], check=True)
        for card in sorted(blockers):
            block = ["--blocked-on", *blockers[card], "--blocked-kind", "agent"]
            subprocess.run([*write, card, *block], check=True)
    return 0


NEMIK_CHECK = "/home/mikemol/github/nemik/.venv/bin/nemik-check"


def check_against_nemik(
    drops: dict[str, list[str]],
    blockers: dict[str, list[str]],
    held: dict[str, list[str]],
    now: dict[str, list[str]],
    debt: set[str],
) -> int:
    """Diff the plan against nemik's integrity reading of this repo: 0 equal, 1 any symmetric difference,
    3 nemik could not be read. ⚑ Weakness: nemik prints text, so the findings are read from its lines."""
    tool = os.environ.get("NEMIK_CHECK") or NEMIK_CHECK
    if not os.path.exists(tool):
        print(f"typing_edges: WITHHELD: {tool} is not installed", file=sys.stderr)
        return 3
    run = subprocess.run(
        [tool, "--root", os.path.dirname(ROOT), "--integrity", "--repo", "el-openglo"],
        capture_output=True,
        text=True,
        check=False,
    )
    if run.returncode != 0:
        print(f"typing_edges: WITHHELD: nemik exited {run.returncode}", file=sys.stderr)
        return 3
    findings, other = finding_edges(run.stdout)
    fixed = fix_edges(drops, blockers, held, now)
    unfixed, extra = diff_plan(fixed, findings, debt)
    for a, b in unfixed:
        print(f"UNFIXED\t{a} enables {b}: nemik names it, the plan does not repair it")
    for a, b in extra:
        print(f"EXTRA\t{a} enables {b}: the plan changes it, nemik names no finding")
    print(
        f"typing_edges: {len(findings)} local finding(s), the plan repairs {len(fixed)} edge(s); "
        f"{len(unfixed)} unfixed, {len(extra)} extra; {other} finding(s) point into another repo",
        file=sys.stderr,
    )
    return 1 if unfixed or extra else 0


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
    sym = {"a.py": "W1", "b.py": "W2", "c.py": "W3"}
    kept2 = {("b.py", "a.py"), ("c.py", "b.py"), ("c.py", "a.py")}
    chk(
        "an importer keeps what it waits on and gains the card of each debt file it imports",
        waits(kept2, sym, {"W2": ["mtools:W1513"], "W3": ["mtools:W1513"]}),
        {"W2": ["mtools:W1513", "W1"], "W3": ["mtools:W1513", "W1", "W2"]},
    )
    chk(
        "an importer that already waits on the cards it imports is not returned",
        waits({("b.py", "a.py")}, sym, {"W2": ["mtools:W1513", "W1"]}),
        {},
    )
    chk(
        "a file nothing imports and a leaf gain nothing",
        waits(set(), sym, {"W1": ["mtools:W1513"]}),
        {},
    )
    chk(
        "a stale debt-to-debt enables edge is dropped, a supported one and a non-debt one stay",
        stale_enables(
            {("b.py", "a.py")},
            sym,
            {"W1": ["W2", "W3", "mtools:W9"], "W2": [], "W3": []},
        ),
        {"W1": ["W2", "mtools:W9"]},
    )
    chk(
        "waits_on follows blocked_on through other cards, and stops on a cycle",
        (
            waits_on("W3", "W1", {"W3": ["W2"], "W2": ["W1"]}),
            waits_on("W3", "W9", {"W3": ["W2"], "W2": ["W3"]}),
        ),
        (True, False),
    )
    chk(
        "a stale edge whose target already waits on the card is not an integrity finding and stays",
        stale_enables(set(), sym, {"W1": ["W2", "W3"]}, {"W2": ["W1"], "W3": []}),
        {"W1": ["W2"]},
    )
    plan = plan_lines({"W1": ["W3", "W2"]}, {"W2": ["W5"]}, {"W4": ["m:W1", "W2"]})
    chk(
        "plan_lines: drops, then enables, then blocks, each sorted",
        plan,
        [
            "drop W1 enables W2 W3",
            "enable W2 enables W5",
            "block W4 blocked_on m:W1 W2",
        ],
    )
    chk(
        "plan_hash: stable for one plan, different for another",
        (
            plan_hash(plan) == plan_hash(list(plan)),
            plan_hash(plan) == plan_hash(plan[:2]),
        ),
        (True, False),
    )
    fixed = fix_edges(
        {"W1": ["W2"]}, {"W4": ["W1", "m:W9"]}, {"W4": ["m:W9"]}, {"W1": ["W2", "W4"]}
    )
    chk(
        "fix_edges: a dropped edge and a new blocker on an existing enables edge, not a blocker already held",
        fixed,
        {("W1", "W2"), ("W1", "W4")},
    )
    text = (
        "el-openglo: 3 finding(s)\n"
        "el-openglo:W274: enables el-openglo:W324, which does not wait on it\n"
        "    drop the enables edge: x\n"
        "el-openglo:W235: enables luthen-observability:W127, which does not wait on it\n"
    )
    chk(
        "finding_edges: local pairs, and a count of the ones pointing into another repo",
        finding_edges(text),
        ({("W274", "W324")}, 1),
    )
    chk(
        "finding_edges: no findings is an empty set, not an error",
        finding_edges(""),
        (set(), 0),
    )
    chk(
        "diff_plan: equal sets give no difference, a missed finding and an extra edge are each named",
        (
            diff_plan({("W1", "W2")}, {("W1", "W2")}, {"W1", "W2"}),
            diff_plan({("W1", "W2")}, {("W3", "W4")}, {"W1", "W2", "W3", "W4"}),
        ),
        (([], []), ([("W3", "W4")], [("W1", "W2")])),
    )
    chk(
        "diff_plan: a finding outside the plan's domain (a non-debt card) is not compared",
        diff_plan(set(), {("W3", "W4")}, {"W1"}),
        ([], []),
    )
    chk(
        "--apply without --plan HASH is refused (2), and so is a flag it does not know",
        (
            main(["x", "--apply"]),
            main(["x", "--apply", "--plan"]),
            main(["x", "--bogus"]),
        ),
        (2, 2, 2),
    )
    chk(
        "nothing stale means nothing returned",
        stale_enables({("b.py", "a.py")}, sym, {"W1": ["W2"]}),
        {},
    )
    print("typing_edges selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if sys.argv[1:] == ["--selftest"]:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
