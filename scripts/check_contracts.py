#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_contracts.py - the fields a surface GUARANTEES, against what it emits and what reads it (W204).

Operator, 2026-10-01: "we could use some opa around managing what kinds of information are
guaranteed to be present, to provide uniformity around design." A surface (a measurement
record or an authority) DECLARES the fields it always carries in policy/contracts.rego; this
MEASURES, per surface, the keys the producer emits and the keys each consumer reads, and the
policy decides: a read of an undeclared field is denied, and so is a declared field the
producer does not emit.

Specialises scripts/check_st_api.py (producer exports vs consumer references, the
requirement discovered from the consumers) from a module's names to a record's keys.

    scripts/check_contracts.py --json      # the measurement policy/contracts.rego decides
    scripts/check_contracts.py             # the verdict, as opa_gate contracts decides it
    scripts/check_contracts.py --selftest  # the measurement can see

WEAKNESS. Both sides are read from the AST: a producer's keys are the string keys of the
dict literals, the `row[...] =` stores and the returned literal of the functions named in
SURFACES; a consumer's reads are `<recv>["k"]` and `<recv>.get("k")` on the receiver NAMES
listed there. A key built at run time, a record passed through another name, and a
consumer that is a Rego policy (policy/screens.rego reads the same rows) are invisible.
Declaring that a field is guaranteed is not a proof it is guaranteed on every path.
"""

import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# WHAT to measure per surface (not what is required: the requirement is the policy's).
# producer: file, the function holding the surface's row loop, the loop's planner name,
# and the function whose returned literal the loop merges in. consumers: file -> receivers.
SURFACES = {
    "render_screens.animation": {
        "producer": {
            "file": "catalog/library/render_screens.py",
            "func": "measure",
            "loop_calls": "plan_animations",
            "merges": "animation_facts",
        },
        "consumers": {"scripts/check_screens.py": ["a", "anim"]},
    },
    # the still rows of the same measure(): their consumer is policy/screens.rego, which this reader cannot
    # see (W246 reads Rego consumers), so no Python consumer is listed and K2 has nothing to judge here
    "render_screens.still": {
        "producer": {
            "file": "catalog/library/render_screens.py",
            "func": "measure",
            "loop_calls": "plan",
        },
        "consumers": {},
    },
    # the palette record every emission target reads (W689): one dict literal returned by parse_scheme;
    # each consumer's receivers are the names bound to a call of it ("@parse_scheme")
    "make_preview.parse_scheme": {
        "producer": {
            "file": "make_preview.py",
            "func": "parse_scheme",
            "returns": True,
        },
        "consumers": {
            rel: "@parse_scheme"
            for rel in (
                "scripts/check_aperture.py",
                "scripts/check_ghost_surfaces.py",
                "scripts/check_marquee_live.py",
                "scripts/check_monet.py",
                "scripts/check_screens.py",
                "scripts/check_urgency_cues.py",
                "scripts/check_windows.py",
                "scripts/readme_fragments.py",
                "scripts/render_qml.py",
            )
        },
    },
}


def _str_keys(node):
    return [
        k.value
        for k in node.keys
        if isinstance(k, ast.Constant) and isinstance(k.value, str)
    ]


def _func(tree, name):
    return next(
        (
            n
            for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == name
        ),
        None,
    )


def _returned_keys(fn):
    keys = set()
    for n in ast.walk(fn):
        if isinstance(n, ast.Return) and isinstance(n.value, ast.Dict):
            keys.update(_str_keys(n.value))
    return keys


def emitted(source, spec):
    """The keys the producer's row loop stamps; None when the producer cannot be read."""
    tree = ast.parse(source)
    fn = _func(tree, spec["func"])
    if fn is None:
        return None
    if spec.get("returns"):
        # a producer that hands back one record: the keys of the dict literals it returns
        return sorted(_returned_keys(fn)) or None
    loops = [
        n
        for n in ast.walk(fn)
        if isinstance(n, ast.For)
        and isinstance(n.iter, ast.Call)
        and getattr(n.iter.func, "id", None) == spec["loop_calls"]
    ]
    if not loops:
        return None
    keys = set()
    for n in ast.walk(loops[0]):
        if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict):
            keys.update(_str_keys(n.value))
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if (
                    isinstance(t, ast.Subscript)
                    and isinstance(t.slice, ast.Constant)
                    and isinstance(t.slice.value, str)
                ):
                    keys.add(t.slice.value)
        elif (
            isinstance(n, ast.Call)
            and getattr(n.func, "attr", None) == "update"
            and any(
                getattr(a.func, "id", None) == spec.get("merges")
                for a in n.args
                if isinstance(a, ast.Call)
            )
        ):
            merged = _func(tree, spec["merges"])
            if merged is not None:
                keys.update(_returned_keys(merged))
        elif (
            isinstance(n, ast.Call)
            and getattr(n.func, "attr", None) == "update"
            and n.keywords
        ):
            # row.update(width=..., modal=...): the keyword NAMES are the keys it stamps
            keys.update(k.arg for k in n.keywords if k.arg)
    return sorted(keys)


def reads(source, receivers):
    """[{field, line}] for every `<recv>["k"]` / `<recv>.get("k")` over the named receivers."""
    out = []
    for n in ast.walk(ast.parse(source)):
        if (
            isinstance(n, ast.Subscript)
            and isinstance(n.value, ast.Name)
            and n.value.id in receivers
            and isinstance(n.slice, ast.Constant)
            and isinstance(n.slice.value, str)
            and isinstance(n.ctx, ast.Load)
        ):
            out.append({"field": n.slice.value, "line": n.lineno})
        elif (
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "get"
            and isinstance(n.func.value, ast.Name)
            and n.func.value.id in receivers
            and n.args
            and isinstance(n.args[0], ast.Constant)
            and isinstance(n.args[0].value, str)
        ):
            out.append({"field": n.args[0].value, "line": n.lineno})
    return sorted(out, key=lambda r: (r["line"], r["field"]))


def assigned_from(source, func):
    """[(first, last, names)]: the names bound to a call of `func` (bare or attribute), with the line
    span of the def holding the binding (the whole module at top level): a receiver name reused for
    something else in another def is not this record."""
    tree = ast.parse(source)
    spans = []
    for scope in [tree, *(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))]:
        inner = {
            id(x)
            for f in ast.walk(scope)
            if f is not scope and isinstance(f, ast.FunctionDef)
            for x in ast.walk(f)
        }
        names = set()
        for n in ast.walk(scope):
            if (
                id(n) not in inner
                and isinstance(n, ast.Assign)
                and isinstance(n.value, ast.Call)
                and (
                    getattr(n.value.func, "id", None) == func
                    or getattr(n.value.func, "attr", None) == func
                )
            ):
                names.update(t.id for t in n.targets if isinstance(t, ast.Name))
        if names:
            spans.append(
                (
                    getattr(scope, "lineno", 1),
                    getattr(scope, "end_lineno", 10**9),
                    names,
                )
            )
    return spans


def _read(rel):
    try:
        with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def measure(surfaces=None, read=_read):
    """The MEASUREMENT policy/contracts.rego decides: per surface, the keys its producer
    emits (null: unreadable, so withheld) and each consumer file's reads."""
    out = []
    for name, spec in sorted((SURFACES if surfaces is None else surfaces).items()):
        src = read(spec["producer"]["file"])
        keys = emitted(src, spec["producer"]) if src is not None else None
        cons = []
        for rel, recv in sorted(spec["consumers"].items()):
            csrc = read(rel)
            if csrc is None:
                got = None
            elif isinstance(recv, str):
                # "@func": the receivers are the names bound to a call of func, within the def that binds them
                got = sorted(
                    (
                        r
                        for first, last, names in assigned_from(csrc, recv[1:])
                        for r in reads(csrc, names)
                        if first <= r["line"] <= last
                    ),
                    key=lambda r: (r["line"], r["field"]),
                )
            else:
                got = reads(csrc, set(recv))
            cons.append({"file": rel, "reads": got})
        out.append({"surface": name, "emitted": keys, "consumers": cons})
    return {"surfaces": out}


def main(argv):
    for a in argv[1:]:
        if a != "--json":
            print(f"check_contracts: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import opa_gate

    return opa_gate.gate("contracts")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    prod = (
        "def facts(p):\n    return {'frames': 1, 'tears': []}\n"
        "def measure():\n"
        "    for fn, v in plan_animations():\n"
        "        row = {'file': fn, 'exists': True}\n"
        "        row.update(facts(fn))\n"
        "        row['logged'] = 1\n"
        "    for fn in plan():\n"
        "        row = {'screen_only': 1}\n"
    )
    spec = {
        "file": "p.py",
        "func": "measure",
        "loop_calls": "plan_animations",
        "merges": "facts",
    }
    chk(
        "emitted sees the literal, the update merge and the store, not another loop",
        emitted(prod, spec),
        ["exists", "file", "frames", "logged", "tears"],
    )
    kw_prod = (
        "def measure():\n"
        "    for fn, v in plan():\n"
        "        row = {'file': fn, 'exists': True}\n"
        "        if row['exists']:\n"
        "            row.update(width=1, modal='#000')\n"
        "    for fn in plan_animations():\n"
        "        row = {'other': 1}\n"
    )
    chk(
        "emitted reads the keyword names of row.update(...), with no merged function, in its own loop only",
        emitted(kw_prod, {"func": "measure", "loop_calls": "plan"}),
        ["exists", "file", "modal", "width"],
    )
    chk(
        "a producer without the loop is unreadable (None)",
        emitted("def measure():\n    pass\n", spec),
        None,
    )
    cons = "def f(a, b):\n    x = a['frames']\n    y = a.get('seamless')\n    z = b['other']\n    a['w'] = 1\n"
    chk(
        "reads sees subscripts and .get on the named receiver only, not stores",
        [r["field"] for r in reads(cons, {"a"})],
        ["frames", "seamless"],
    )
    m = measure(
        {"s": {"producer": spec, "consumers": {"c.py": ["a"]}}},
        read={"p.py": prod, "c.py": cons}.get,
    )
    chk(
        "measure joins them",
        (
            m["surfaces"][0]["emitted"][0],
            len(m["surfaces"][0]["consumers"][0]["reads"]),
        ),
        ("exists", 2),
    )
    gone = measure(
        {"s": {"producer": spec, "consumers": {"c.py": ["a"]}}}, read=lambda _p: None
    )
    chk(
        "an unreadable producer is null, not empty",
        gone["surfaces"][0]["emitted"],
        None,
    )
    chk(
        "a returns producer emits the keys of the dict it returns",
        emitted(
            "def rec(v):\n    def inner():\n        return 1\n    return {'a': 1, 'b': 2}\n",
            {"func": "rec", "returns": True},
        ),
        ["a", "b"],
    )
    chk(
        "a returns producer whose function returns no literal is unreadable (None)",
        emitted("def rec(v):\n    return v\n", {"func": "rec", "returns": True}),
        None,
    )
    bound = (
        "def one(v):\n    s = rec(v)\n    return s['a']\n"
        "def two(v):\n    s = {'id': v}\n    return s['id']\n"
    )
    scoped = measure(
        {"r": {"producer": spec, "consumers": {"c.py": "@rec"}}},
        read={"p.py": prod, "c.py": bound}.get,
    )
    chk(
        "an @func consumer reads only the def that binds the name, not another def reusing it",
        [r["field"] for r in scoped["surfaces"][0]["consumers"][0]["reads"]],
        ["a"],
    )
    real = measure()
    chk(
        "the real surface is read (emitted a non-empty list)",
        bool(real["surfaces"][0]["emitted"]),
        True,
    )
    chk(
        "the real consumer reads at least one field",
        len(real["surfaces"][0]["consumers"][0]["reads"]) > 0,
        True,
    )
    print("check_contracts selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
