#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_bazel_build.py — do this tree's BUILD files name their inputs, one file at a time?

⚑ WHY (W487, operator rule 2026-10-06: "BUILD inputs are named files — never a glob, never a
directory; a tracked gated file missing from the list must itself fail the gate"). A glob() makes
the input set whatever the disk holds when bazel looks, so a stage's key moves with files nobody
named and a gated file nobody listed is simply absent from the gate. mtools' `tracked.bzl`
(`select_tracked`, names from `git ls-files`) is the generator; this refuses what bypasses it.

    scripts/check_bazel_build.py            # the verdict, as opa_gate bazel_build decides it
    scripts/check_bazel_build.py --json     # the measurement (policy/bazel_build.rego decides)
    scripts/check_bazel_build.py --selftest

Per tracked BUILD / BUILD.bazel file it reports every `glob()` call, and every LITERAL file label in
`srcs`/`data` with whether it is a file, a directory or absent. Starlark is Python syntax, so the
file is read with `ast`; nothing is executed.

⚑ WEAKNESSES, STATED. (1) Only LITERAL labels are resolved: an input produced by a call
(`select_tracked(...)`, a list comprehension, a macro) is not seen here — it is the generator's, and
a glob hidden inside a macro defined in a `.bzl` is not seen either (the `.bzl` files are not
parsed). (2) A label in another package (`//pkg:file`) is resolved as `pkg/file`; an external
(`@repo//...`) one is not this tree's and is skipped. (3) No BUILD file at all is a refusal, not a
clean tree: the population is empty.
"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

INPUT_ATTRS = ("srcs", "data")


def _name_of(call):
    """The called name of a Call node (`glob`, `native.glob` -> `glob`), else ''."""
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return ""


def _literals(node):
    """The string constants directly listed in a list / tuple / string expression, on either
    side of a `+` (`["a.sh"] + select_tracked(...)`: the literal half is read, the call is not)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _literals(node.left) + _literals(node.right)
    if isinstance(node, (ast.List, ast.Tuple)):
        return [
            e.value
            for e in node.elts
            if isinstance(e, ast.Constant) and isinstance(e.value, str)
        ]
    return []


def resolve(label, build_dir):
    """The repo-relative path a literal label names, or None when it is not this tree's file
    (a target ':x', an external '@repo//...')."""
    if label.startswith(("@", ":")):
        return None
    if label.startswith("//"):
        pkg, _, name = label[2:].partition(":")
        return os.path.join(pkg, name) if name else pkg
    return os.path.normpath(os.path.join(build_dir, label)) if build_dir else label


def kind_of(path, root=ROOT):
    """'file', 'directory' or 'absent' for a repo-relative path."""
    full = os.path.join(root, path)
    if os.path.isdir(full):
        return "directory"
    return "file" if os.path.isfile(full) else "absent"


def inspect(source, rel, root=ROOT):
    """(globs, inputs) of one BUILD file's text: [{build, line, patterns}] and
    [{build, line, target, attr, label, path, kind}]."""
    tree = ast.parse(source)
    build_dir = os.path.dirname(rel)
    globs, inputs = [], []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if _name_of(node) == "glob":
            globs.append(
                {
                    "build": rel,
                    "line": node.lineno,
                    "patterns": _literals(node.args[0]) if node.args else [],
                }
            )
        target = next(
            (
                kw.value.value
                for kw in node.keywords
                if kw.arg == "name"
                and isinstance(kw.value, ast.Constant)
                and isinstance(kw.value.value, str)
            ),
            "",
        )
        for kw in node.keywords:
            if kw.arg not in INPUT_ATTRS:
                continue
            for label in _literals(kw.value):
                path = resolve(label, build_dir)
                if path is None:
                    continue
                inputs.append(
                    {
                        "build": rel,
                        "line": kw.value.lineno,
                        "target": target,
                        "attr": kw.arg,
                        "label": label,
                        "path": path,
                        "kind": kind_of(path, root),
                    }
                )
    # ast.walk is breadth-first: report in source order, which is what a reader can follow
    return sorted(globs, key=lambda g: g["line"]), sorted(
        inputs, key=lambda i: (i["line"], i["label"])
    )


def measure(sources=None, root=ROOT):
    """The MEASUREMENT policy/bazel_build.rego decides. `sources` is {rel path: text}."""
    if sources is None:
        import git_tracked

        sources = {}
        for rel in git_tracked.files(
            "BUILD.bazel", "*/BUILD.bazel", "BUILD", "*/BUILD"
        ):
            with open(os.path.join(root, rel), encoding="utf-8") as fh:
                sources[rel] = fh.read()
    globs, inputs = [], []
    for rel, text in sorted(sources.items()):
        g, i = inspect(text, rel, root)
        globs += g
        inputs += i
    return {"builds": sorted(sources), "globs": globs, "inputs": inputs}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_bazel_build: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json

        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("bazel_build")


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

    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "gate", "sub"))
        for rel in ("gate/a.sh", "MODULE.bazel"):
            with open(os.path.join(td, rel), "w", encoding="utf-8") as fh:
                fh.write("x\n")
        src = (
            'sh_test(name = "t", srcs = ["gate/a.sh"], data = ["MODULE.bazel", "gate/sub",'
            ' "gate/gone.sh", "@tracked//:tracked.txt", ":other"] + glob(["gate/*.sh"]))\n'
            'filegroup(name = "g", srcs = native.glob(["**"]))\n'
        )
        globs, inputs = inspect(src, "BUILD.bazel", td)
        chk(
            "a glob() and a native.glob() are both seen",
            [g["line"] for g in globs],
            [1, 2],
        )
        chk(
            "a glob's literal patterns are reported",
            globs[0]["patterns"],
            ["gate/*.sh"],
        )
        got = {(i["label"], i["kind"]) for i in inputs}
        chk(
            "a file, a directory and an absent path are told apart",
            got,
            {
                ("gate/a.sh", "file"),
                ("MODULE.bazel", "file"),
                ("gate/sub", "directory"),
                ("gate/gone.sh", "absent"),
            },
        )
        chk(
            "an external label and a target label are not this tree's files",
            {i["label"] for i in inputs} & {"@tracked//:tracked.txt", ":other"},
            set(),
        )
        chk("the target name is carried", {i["target"] for i in inputs}, {"t"})
        nested = inspect('sh_test(name="n", srcs=["b.sh"])\n', "gate/BUILD.bazel", td)[
            1
        ]
        chk("a label resolves against its own package", nested[0]["path"], "gate/b.sh")
        pkg = resolve("//gate:a.sh", "")
        chk("a //pkg:file label resolves to pkg/file", pkg, "gate/a.sh")
    real = measure()
    chk(
        "the real tree has at least one BUILD file (the population is not empty)",
        len(real["builds"]) > 0,
        True,
    )
    print("check_bazel_build selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
