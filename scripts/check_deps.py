#!/usr/bin/env python3
"""check_deps.py — every third-party import is accounted for in the manifest.

A dependency named only in a docstring is a permission slip.  This walks the AST
of every module, subtracts the standard library and this project's own modules,
and refuses if what remains is not either DECLARED in pyproject.toml or RECORDED
there as deliberately absent.

    scripts/check_deps.py            # the verdict, as opa_gate deps decides it
    scripts/check_deps.py --json     # the measurement policy/deps.rego decides
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
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import git_tracked  # noqa: E402

# import-name -> distribution-name, where they differ.
DIST = {"PIL": "pillow", "fontTools": "fonttools", "PySide6": "pyside6",
        "material_color_utilities": "material-color-utilities"}


# ⚑ THE SCAN WAS ROOT-ONLY, AND THAT WAS A BLIND SPOT IN THE DEPENDENCY CHECKER
# ITSELF.  It walked os.listdir(ROOT) and nothing else, so a dependency
# introduced by a TOOL was invisible to it: scripts/identify.py imports `magic`
# and this reported "8 of 8 accounted for" — correct over the set it looked at,
# and the set was wrong. The checkers are Python too, and their imports are
# dependencies of the same tree.
SCAN_DIRS = (".", "scripts", "templates", "catalog/library")


def _python_files():
    """[(relpath, abspath)] for every TRACKED .py directly in the scanned directories
    (scripts/git_tracked.py — the tree is what git tracks, not what the disk holds)."""
    specs = [":(glob)*.py" if d == "." else f":(glob){d}/*.py" for d in SCAN_DIRS]
    return [(rel, os.path.join(ROOT, rel)) for rel in git_tracked.files(*specs, root=ROOT)]


def _tracked_top():
    """(top-level module names, top-level directory names) in the tracked tree."""
    rels = git_tracked.files(root=ROOT)
    mods = {r[:-3] for r in rels if "/" not in r and r.endswith(".py")}
    dirs = {r.split("/", 1)[0]: set() for r in rels if "/" in r}
    for r in rels:
        if r.count("/") == 1:
            dirs[r.split("/", 1)[0]].add(r.split("/", 1)[1])
    return mods, dirs


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


def imports(files=None):
    """{top-level module: {files}} for every non-stdlib, non-local import.

    `files` — [(label, path)] — overrides the tree walk, for a planted fixture."""
    std = set(sys.stdlib_module_names)
    local, top_dirs = _tracked_top()
    # ⚑ A DIRECTORY IS NOT A PACKAGE, AND TREATING IT AS ONE HID A REAL
    # DEPENDENCY.  This counted every top-level DIRECTORY as an importable local
    # module, so creating `magic/` — which holds libmagic SIGNATURES, not Python
    # — made `import magic` look local and vanish from the census. The
    # discriminator is an __init__.py or a like-named module, not a name that
    # happens to match.
    local |= {d for d, members in top_dirs.items()
              if "__init__.py" in members or d in local}
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
    for fn, path in (files if files is not None else _python_files()):
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


def _dist_name(spec):
    """The distribution NAME of a PEP 508 requirement: the leading identifier.

    ⚑ THIS WAS `split('[')...split('<')`, WHICH MISSES `@` AND `;`. A direct
    reference — `paperkit @ git+https://…` — came out as the whole URL, so the
    declared set never contained `paperkit`, and the import passed only because
    the word appeared somewhere in the file (the "recorded" fallback). A pass for
    the wrong reason is a check that would not have caught its absence."""
    import re
    m = re.match(r"\s*([A-Za-z0-9][A-Za-z0-9._-]*)", spec)
    return m.group(1).lower() if m else spec.strip().lower()


def declared():
    """(declared distribution names, the manifest's raw text)."""
    p = os.path.join(ROOT, "pyproject.toml")
    if not os.path.exists(p):
        return None, ""
    raw = open(p, encoding="utf-8").read()
    cfg = tomllib.loads(raw)
    proj = cfg.get("project", {})
    out = {_dist_name(s) for s in proj.get("dependencies", [])}
    for group in (proj.get("optional-dependencies") or {}).values():
        out |= {_dist_name(s) for s in group}
    return out, raw


def measure():
    """The MEASUREMENT policy/deps.rego decides (W50): whether a manifest exists,
    and per third-party import (the AST walk over every tracked module in
    SCAN_DIRS): its distribution name, the files importing it, whether that
    distribution is DECLARED (dependencies or an extra), and whether the name is
    RECORDED in the manifest's text — the "deliberately absent" notes. The two
    are separate facts so a pass by mention is visible as one."""
    decl, raw = declared()
    found = imports()
    return {
        "manifest": decl is not None,
        "cases": [{"id": mod, "dist": DIST.get(mod, mod).lower(),
                   "files": sorted(files),
                   "declared": decl is not None and DIST.get(mod, mod).lower() in decl,
                   "recorded": mod in raw}
                  for mod, files in sorted(found.items())],
    }


def main(argv):
    known = {"--imports", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_deps: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--imports" in argv:
        for m, files in sorted(imports().items()):
            print(f"{m}\t{', '.join(sorted(files))}")
        return 0
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("deps")


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
    # case a naive top-of-file scan misses. ⚑ THIS FIXTURE WAS `qml_sanity` —
    # a name that read as third-party only because the module was LOST in the
    # recovery; when W25 rebuilt it (2026-09-21) the arm failed. A fixture
    # pinned to the tree's damage is a fixture that breaks on repair. Synthetic:
    # a planted module with a body-level import of a name nothing provides.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "planted.py"), "w").write(
            "def f():\n    import el_openglo_selftest_absent_dep\n    return 1\n")
        planted = imports(files=[("planted.py", os.path.join(td, "planted.py"))])
        check("the walk sees a function-body import (planted)",
              "el_openglo_selftest_absent_dep" in planted, True)
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
    # ⚑ A DIRECT REFERENCE IS DECLARED BY ITS NAME, not found by mention
    check("a PEP 508 direct reference parses to its name",
          _dist_name("paperkit @ git+https://github.com/mikemol/paperkit.git@7081cd1"), "paperkit")
    check("an extra and a marker do not leak into the name",
          (_dist_name("pillow[webp]>=12 ; python_version >= '3.11'"), _dist_name("numpy")),
          ("pillow", "numpy"))
    by = {c["id"]: c for c in measure()["cases"]}
    check("paperkit is measured DECLARED, not merely mentioned",
          by.get("paperkit", {}).get("declared"), True)
    print("check_deps selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
