#!/usr/bin/env python3
"""check_deps.py — every third-party import is accounted for in the manifest.

A dependency named only in a docstring is a permission slip.  This walks the AST
of every module, subtracts the standard library and this project's own modules,
and refuses if what remains is not either DECLARED in pyproject.toml or RECORDED
there as deliberately absent.

    scripts/check_deps.py            # exit 0 iff every import is accounted for
    scripts/check_deps.py --imports  # module -> the files importing it

⚑ THE WALK IS THE AUTHORITY, NOT A REMEMBERED LIST.  The manifest was first
written FROM this walk; this re-runs it so the two cannot drift.  An import added
tomorrow inside a function body — where it never surfaces as a compile error —
is caught here.  That is not hypothetical: `qml_sanity` reached the tree exactly
that way and is absent from the archive's own recovery notes.

⚑ IMPORT NAME vs DISTRIBUTION NAME.  `import PIL` is installed as `pillow`,
`import fontTools` as `fonttools`.  The mapping is data below, because guessing
it (lowercase and hope) silently mis-reports both directions.
"""
import ast
import os
import sys
import tomllib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# import-name -> distribution-name, where they differ.
DIST = {"PIL": "pillow", "fontTools": "fonttools", "PySide6": "pyside6"}


def imports():
    """{top-level module: {files}} for every non-stdlib, non-local import."""
    std = set(sys.stdlib_module_names)
    local = {f[:-3] for f in os.listdir(ROOT) if f.endswith(".py")}
    local |= {d for d in os.listdir(ROOT) if os.path.isdir(os.path.join(ROOT, d))}
    found = {}
    for fn in sorted(os.listdir(ROOT)):
        if not fn.endswith(".py"):
            continue
        try:
            tree = ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8",
                                  errors="replace").read())
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            for name in names:
                top = name.split(".")[0]
                if top not in std and top not in local:
                    found.setdefault(top, set()).add(fn)
    return found


def declared():
    """(declared distribution names, the manifest's raw text)."""
    p = os.path.join(ROOT, "pyproject.toml")
    if not os.path.exists(p):
        return None, ""
    raw = open(p, encoding="utf-8").read()
    cfg = tomllib.loads(raw)
    proj = cfg.get("project", {})
    out = set()
    for spec in proj.get("dependencies", []):
        out.add(spec.split("[")[0].split(">")[0].split("=")[0].split("<")[0].strip().lower())
    for group in (proj.get("optional-dependencies") or {}).values():
        for spec in group:
            out.add(spec.split("[")[0].split(">")[0].split("=")[0].split("<")[0].strip().lower())
    return out, raw


def main(argv):
    known = {"--imports"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_deps: unknown flag {a!r}", file=sys.stderr)
            return 2
    found = imports()
    if "--imports" in argv:
        for m, files in sorted(found.items()):
            print(f"{m}\t{', '.join(sorted(files))}")
        return 0
    decl, raw = declared()
    if decl is None:
        print("check_deps: REFUSED — no pyproject.toml to account against",
              file=sys.stderr)
        return 1
    if not found:
        print("check_deps: REFUSED — the import walk found nothing; the walk is "
              "broken, not the tree dependency-free", file=sys.stderr)
        return 2
    unaccounted = []
    for mod in sorted(found):
        dist = DIST.get(mod, mod).lower()
        if dist in decl:
            continue
        # not declared — is it RECORDED as deliberately absent?
        if mod in raw:
            continue
        unaccounted.append(mod)
    if unaccounted:
        print(f"check_deps: REFUSED — {len(unaccounted)} of {len(found)} third-party "
              f"import(s) are neither declared nor recorded as absent:", file=sys.stderr)
        for mod in unaccounted:
            print(f"    {mod}  (imported by {', '.join(sorted(found[mod]))})",
                  file=sys.stderr)
        return 1
    print(f"check_deps: {len(found)} of {len(found)} third-party imports accounted for")
    return 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    found = imports()
    check("the walk found imports", len(found) > 0, True)
    # The walk must see an import buried inside a function body, which is the
    # case a naive top-of-file scan misses.
    check("sees a function-body import (qml_sanity)", "qml_sanity" in found, True)
    check("stdlib is excluded", "os" not in found and "sys" not in found, True)
    print("check_deps selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
