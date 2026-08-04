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


# ⚑ THE SCAN WAS ROOT-ONLY, AND THAT WAS A BLIND SPOT IN THE DEPENDENCY CHECKER
# ITSELF.  It walked os.listdir(ROOT) and nothing else, so a dependency
# introduced by a TOOL was invisible to it: scripts/identify.py imports `magic`
# and this reported "8 of 8 accounted for" — correct over the set it looked at,
# and the set was wrong. The checkers are Python too, and their imports are
# dependencies of the same tree.
SCAN_DIRS = (".", "scripts", "templates", "catalog/library")


def _python_files():
    """[(relpath, abspath)] for every .py in the scanned directories."""
    out = []
    for d in SCAN_DIRS:
        base = os.path.join(ROOT, d) if d != "." else ROOT
        if not os.path.isdir(base):
            continue
        for fn in sorted(os.listdir(base)):
            if fn.endswith(".py"):
                rel = fn if d == "." else f"{d}/{fn}"
                out.append((rel, os.path.join(base, fn)))
    return out


def _symlink_siblings():
    """Module names that resolve BESIDE a symlinked tool, in its own repo.

    A symlink's imports are satisfied where the real file lives, so its
    neighbours are local to IT even though they are absent here."""
    out = set()
    for _rel, path in _python_files():
        if not os.path.islink(path):
            continue
        real_dir = os.path.dirname(os.path.realpath(path))
        if not os.path.isdir(real_dir):
            continue
        # ⚑ AND ITS REPO'S PEER DIRECTORIES, NOT ONLY ITS OWN.  run_selftests.py
        # lives in substrate/scripts/ and imports spool and tsdbprobe from
        # substrate/scratch/, which it puts on sys.path at runtime. A sibling
        # scan of one directory misses those and reports them as undeclared
        # third-party — a fact about the borrowing, not about this tree.
        for d in (real_dir, os.path.join(os.path.dirname(real_dir), "scratch")):
            if os.path.isdir(d):
                out |= {f[:-3] for f in os.listdir(d) if f.endswith(".py")}
    return out


def imports():
    """{top-level module: {files}} for every non-stdlib, non-local import."""
    std = set(sys.stdlib_module_names)
    local = {f[:-3] for f in os.listdir(ROOT) if f.endswith(".py")}
    # ⚑ A DIRECTORY IS NOT A PACKAGE, AND TREATING IT AS ONE HID A REAL
    # DEPENDENCY.  This counted every top-level DIRECTORY as an importable local
    # module, so creating `magic/` — which holds libmagic SIGNATURES, not Python
    # — made `import magic` look local and vanish from the census. The
    # discriminator is an __init__.py or a like-named module, not a name that
    # happens to match.
    local |= {d for d in os.listdir(ROOT)
              if os.path.isdir(os.path.join(ROOT, d))
              and (os.path.exists(os.path.join(ROOT, d, "__init__.py"))
                   or os.path.exists(os.path.join(ROOT, d + ".py")))}
    # a module in a scanned subdir is local to a sibling importing it
    local |= {os.path.basename(rel)[:-3] for rel, _ in _python_files()}
    # ⚑ A SYMLINKED TOOL'S SIBLINGS ARE ITS OWN REPO'S, NOT OURS.  Several
    # scripts/ entries point into ../substrate, and they import THEIR neighbours
    # (hook_cmdparse, tsdbprobe, …) by bare name. Those resolve beside the real
    # file, so they are not third-party and not ours to declare — widening the
    # scan surfaced them as unaccounted, which is a fact about where the file
    # LIVES rather than about this tree's dependencies.
    local |= _symlink_siblings()
    found = {}
    for fn, path in _python_files():
        try:
            tree = ast.parse(open(path, encoding="utf-8",
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
    # ⚑ THE SCAN REACHES THE TOOLS, NOT ONLY THE ROOT.  It was root-only, so a
    # dependency introduced by a checker was invisible to the dependency
    # checker — it reported "8 of 8 accounted for" while scripts/identify.py
    # imported an undeclared `magic`.
    check("the scan reaches scripts/",
          any(f.startswith("scripts/") for fs in found.values() for f in fs), True)
    # ⚑ AND A DATA DIRECTORY IS NOT A PACKAGE.  Every top-level DIRECTORY was
    # treated as an importable local module, so creating `magic/` (libmagic
    # signatures, no Python) made `import magic` look local and disappear.
    check("a data directory does not shadow a package",
          "magic" in found or not os.path.isdir(os.path.join(ROOT, "magic")), True)
    print("check_deps selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
