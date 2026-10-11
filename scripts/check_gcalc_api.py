#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_gcalc_api.py — does the ONE adapter to the gcalculus sibling still name real things?

⚑ WHY (W485, 2026-10-10). gcalculus split `gcalc/solver.py` into a package of namespaces and four
checks here died with `AttributeError: module 'gcalc.solver' has no attribute 'freeze'`, caught only
by the commit gate and four times over, because each caller kept its own copy of the import. Now
gcalc_api.py is the one place (a name -> defining-module table, NAMES), and this measures it two ways:

  1. EVERY NAME RESOLVES: each NAMES entry is imported from the sibling module it claims, so a
     moved or removed name is named, not a bare AttributeError in a distant check;
  2. EVERY READ IS DECLARED: every attribute a caller reads off the adapter (`S.netlist`,
     `SOLVER.cycle_basis`, `CARRIER.support` ...) is a NAMES entry, so a caller cannot grow a read
     the adapter does not provide.

    scripts/check_gcalc_api.py            # the verdict, as opa_gate gcalc_api decides it
    scripts/check_gcalc_api.py --json     # the measurement (policy/gcalc_api.rego decides)
    scripts/check_gcalc_api.py --selftest

⚑ WEAKNESSES, STATED. (1) Reads are found by AST on names BOUND to the adapter (an import alias,
or a module-level assignment of it): an attribute read through a name passed as a parameter, or
fetched with getattr, is not seen. (2) It proves a name EXISTS in the sibling, not that its
signature is the one the stubs under stubs/gcalc declare. (3) The sibling absent is `withheld`
(counted, printed): a fact about the machine, never a pass.
"""

import ast
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import gcalc_api


def _is_module(value, aliases):
    """Is this expression the adapter module itself (a bound name, or a conditional of one)?"""
    if isinstance(value, ast.Name):
        return value.id in aliases
    if isinstance(value, ast.IfExp):
        return _is_module(value.body, aliases) or _is_module(value.orelse, aliases)
    return False


def adapter_aliases(tree):
    """The module-level names of `tree` bound to the adapter module itself: an import of
    gcalc_api (with or without `as`), and a name assigned from one (SOLVER = gcalc_api ...)."""
    aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name == "gcalc_api":
                    aliases.add(a.asname or "gcalc_api")
    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            targets, value = [], None
            if isinstance(node, ast.Assign):
                targets, value = node.targets, node.value
            elif isinstance(node, ast.AnnAssign) and node.value is not None:
                targets, value = [node.target], node.value
            if value is None:
                continue
            # the module ITSELF only: `X = gcalc_api`, `X = Y`, `X = gcalc_api if cond else None`.
            # A call's RESULT (`fz = S.freeze(...)`) is not the module, so its reads are not charged
            if _is_module(value, aliases):
                for t in targets:
                    if isinstance(t, ast.Name) and t.id not in aliases:
                        aliases.add(t.id)
                        changed = True
    return aliases


def reads(source):
    """{attribute: first line} read off the adapter in one module's source."""
    tree = ast.parse(source)
    aliases = adapter_aliases(tree)
    out = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id in aliases
        ):
            out.setdefault(node.attr, node.lineno)
    return out


def measure(sources=None, names=None):
    """The MEASUREMENT policy/gcalc_api.rego decides: per NAMES entry whether the sibling's
    module defines it; per caller read whether NAMES declares it; `present` says whether the
    sibling is importable at all. `sources` is {path: text}; `names` the NAMES table."""
    if names is None:
        names = gcalc_api.NAMES
    if sources is None:
        import git_tracked

        sources = {}
        for rel in git_tracked.files("*.py", "scripts/*.py"):
            if rel == "gcalc_api.py" or rel == "scripts/check_gcalc_api.py":
                continue
            with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
                text = fh.read()
            if "gcalc_api" in text:
                sources[rel] = text
    present = os.path.isdir(gcalc_api.GCALC)
    resolved = []
    for name, module in sorted(names.items()):
        ok, why = False, ""
        if present:
            try:
                ok = hasattr(importlib.import_module(module), name)
                why = "" if ok else f"{module} defines no {name}"
            except ImportError as exc:
                why = f"{module} does not import: {exc}"
        resolved.append({"name": name, "module": module, "defined": ok, "why": why})
    callers = []
    for rel, text in sorted(sources.items()):
        for attr, line in sorted(reads(text).items()):
            if attr in ("AVAILABLE", "GCALC", "NAMES"):
                continue
            callers.append(
                {"file": rel, "line": line, "name": attr, "declared": attr in names}
            )
    return {"present": present, "names": resolved, "callers": callers}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_gcalc_api: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json

        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("gcalc_api")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    src = (
        "import gcalc_api as S\n"
        "import gcalc_api\n"
        "SOLVER = S if S.AVAILABLE else None\n"
        "def f():\n"
        "    return SOLVER.netlist([]), S.freeze, gcalc_api.nope, other.netlist\n"
    )
    chk(
        "a read through an alias, a derived name and the bare module is seen",
        sorted(reads(src)),
        ["AVAILABLE", "freeze", "netlist", "nope"],
    )
    chk(
        "a read off an unrelated name is not",
        "other" in adapter_aliases(ast.parse(src)),
        False,
    )
    chk(
        "a call's RESULT is not the module: its attribute reads are not charged to the adapter",
        sorted(reads("import gcalc_api as S\nfz = S.freeze()\nfz.nodes\n")),
        ["freeze"],
    )
    m = measure(
        {"a.py": src},
        {"netlist": "gcalc.solver.netlist", "freeze": "gcalc.solver.driver"},
    )
    declared = {c["name"]: c["declared"] for c in m["callers"]}
    chk(
        "a caller read the adapter does not declare is a fact",
        declared,
        {"freeze": True, "netlist": True, "nope": False},
    )
    ghost = measure({}, {"nothing_here": "gcalc.solver.netlist"})
    chk(
        "a name its module does not define is measured undefined and names why",
        [(n["name"], n["defined"], bool(n["why"])) for n in ghost["names"]]
        if ghost["present"]
        else [("nothing_here", False, True)],
        [("nothing_here", False, True)],
    )
    real = measure({}, gcalc_api.NAMES)
    chk(
        "the real adapter's names all resolve against the real sibling (or it is absent)",
        all(n["defined"] for n in real["names"]) or not real["present"],
        True,
    )
    print("check_gcalc_api selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
