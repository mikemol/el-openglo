#!/usr/bin/env python3
"""check_populations.py — does any check build its population by walking the DISK
from the repo root?

⚑ WHY (2026-09-22 build_graph, 2026-09-23 check_compiles). Twice a check walked
the repo root, descended into .claude/worktrees/ (agents' private checkouts),
.build/, .tree-writes/ or .ebuild-witness/, counted files that are not in this
tree, and failed the gate on an agent's dangling symlink. The fix is not a longer
skip-list (that is the scratch dirs we happen to know about TODAY) but the
authority: `scripts/git_tracked.py` (git ls-files + pathspec), or a declared
roster (emitters.ROLES, render_screens.plan_all(), warrants.bib).

    scripts/check_populations.py            # human report, n of m
    scripts/check_populations.py --json     # the measurement, for policy/populations.rego
    scripts/check_populations.py --selftest # the scan SEES a bare os.walk(ROOT)
    scripts/opa_gate.py populations         # the verdict

POPULATION (read from git, not the disk): tracked scripts/*.py, catalog/library/*.py
and top-level *.py. A SITE is a disk enumeration: os.walk, Path.rglob, glob.glob /
glob.iglob / Path.glob whose pattern holds `**` or that pass recursive=True,
os.listdir, os.scandir. `ast.walk` and friends are not disk walks and are not sites.

REACH of a site's root argument, judged statically:
  root     — a name bound (anywhere in the module) to a __file__-derived dirname /
             parent chain, a name spelled root/ROOT/REPO/HERE, ".", "", os.getcwd();
             or a join whose first component is one of those and whose next is `**`.
  bounded  — a join of a root with a literal subdirectory (root/"catalog", ...),
             or a name bound to one.
  unknown  — anything else (a parameter, a tempdir, a computed path).
A recursive site (walk/rglob/recursive glob) at `root` or `unknown` reach must carry
`# population: <reason>` on its line or the line above — the reason says why the
walk is bounded (a private tempdir, an untracked build out dir, a fixture). The
policy refuses an empty reason. A one-level listdir/scandir at `root` reach cannot
descend into scratch, so it is ADVISORY (reported, not denied): it still sees
untracked root entries, e.g. emitters.atomic_path's in-flight `.<name>.<rand>.colors`.

BORROWED files (symlinks into ../substrate) are measured but judged apart: a finding
there is substrate's to fix, reported as withheld, never edited here.

WEAKNESSES, stated: (1) STATIC — a root computed through a helper call, or passed as
a parameter, reads as `unknown`, which is conservative (it must be marked), never
silent. (2) A literal subdirectory under root is admitted as bounded even if THAT
directory holds scratch — none of catalog/, policy/, etc. does today. (3) It sees
the spelled call; a walk routed through a third-party API (pathlib's own recursion
under another name) is invisible.
"""
import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import git_tracked  # noqa: E402

TAG = "population:"
SCOPE = ("scripts/*.py", "catalog/library/*.py", ":(glob)*.py")
ROOT_NAMES = {"ROOT", "root", "REPO", "repo", "HERE", "REPO_ROOT", "_ROOT", "BASE"}
RECURSIVE = {"walk", "rglob", "glob-recursive"}


def _call_name(f):
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else None
        return base, f.attr
    if isinstance(f, ast.Name):
        return None, f.id
    return None, None


def _from_file(e):
    """Is `e` a dirname/abspath/parent chain over __file__ with no literal subdir?"""
    if isinstance(e, ast.Name):
        return e.id == "__file__"
    if isinstance(e, ast.Attribute) and e.attr in ("parent", "parents"):
        return _from_file(e.value)
    if isinstance(e, ast.Subscript):
        return _from_file(e.value)
    if isinstance(e, ast.Call):
        _, n = _call_name(e.func)
        if n in ("dirname", "abspath", "realpath", "resolve", "Path", "normpath", "absolute", "expanduser"):
            if e.args:
                return _from_file(e.args[0])
            if isinstance(e.func, ast.Attribute):
                return _from_file(e.func.value)
    return False


class _Reach:
    def __init__(self, tree):
        self.bind = {}
        for n in ast.walk(tree):
            if isinstance(n, ast.Assign) and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name):
                self.bind.setdefault(n.targets[0].id, n.value)

    def of(self, e, depth=0):
        """('root'|'bounded'|'unknown', detail)."""
        if depth > 6:
            return "unknown", "binding too deep"
        if isinstance(e, ast.Constant) and e.value in (".", "", "./"):
            return "root", repr(e.value)
        if isinstance(e, ast.Constant) and isinstance(e.value, str):
            head = e.value.split("/", 1)[0]
            if head == "**":
                return "root", repr(e.value)
            return "bounded", repr(e.value)
        if isinstance(e, ast.Name):
            if e.id in self.bind and e.id not in ("root",):
                v = self.bind[e.id]
                if _from_file(v):
                    return "root", e.id
                r, d = self.of(v, depth + 1)
                if r != "unknown":
                    return r, f"{e.id}={d}"
            if e.id in ROOT_NAMES:
                return "root", e.id
            return "unknown", e.id
        if _from_file(e):
            return "root", ast.unparse(e)
        if isinstance(e, ast.Call):
            b, n = _call_name(e.func)
            if n == "getcwd":
                return "root", "os.getcwd()"
            if n == "join" and e.args:
                return self._join(e.args[0], e.args[1:], depth)
            if n in ("Path", "abspath", "realpath", "normpath", "resolve") and e.args:
                return self.of(e.args[0], depth + 1)
            if n in ("resolve", "absolute") and isinstance(e.func, ast.Attribute):
                return self.of(e.func.value, depth + 1)
        if isinstance(e, ast.BinOp) and isinstance(e.op, ast.Div):
            return self._join(*self._flatten_div(e), depth)
        if isinstance(e, ast.JoinedStr):
            return "unknown", ast.unparse(e)
        return "unknown", ast.unparse(e)

    @staticmethod
    def _flatten_div(e):
        parts = []
        while isinstance(e, ast.BinOp) and isinstance(e.op, ast.Div):
            parts.insert(0, e.right)
            e = e.left
        return e, parts

    def _join(self, head, rest, depth):
        r, d = self.of(head, depth + 1)
        if r != "root":
            return r, d
        if not rest:
            return "root", d
        nxt = rest[0]
        if isinstance(nxt, ast.Constant) and isinstance(nxt.value, str):
            if nxt.value.split("/", 1)[0] in ("**", "", "."):
                return "root", f"{d}/{nxt.value}"
            return "bounded", f"{d}/{nxt.value}"
        r2, d2 = self.of(nxt, depth + 1)
        return ("bounded", f"{d}/{d2}") if r2 == "bounded" else ("unknown", f"{d}/{ast.unparse(nxt)}")


def _marker(lines, lineno):
    for ln in (lineno, lineno - 1):
        if 1 <= ln <= len(lines):
            t = lines[ln - 1]
            i = t.find("# " + TAG)
            if i >= 0:
                return t[i + len(TAG) + 2:].strip(" —-:\t")
    return None


def _pattern_recursive(call):
    if any(k.arg == "recursive" and isinstance(k.value, ast.Constant) and k.value.value for k in call.keywords):
        return True
    for a in call.args[:1]:
        for n in ast.walk(a):
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and "**" in n.value:
                return True
    return False


def sites(source, module):
    """[{module, line, kind, recursive, reach, root, marked, reason}] for every disk walk."""
    tree = ast.parse(source)
    lines = source.splitlines()
    reach = _Reach(tree)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        base, name = _call_name(node.func)
        kind, arg = None, node.args[0] if node.args else None
        if name == "walk" and base == "os":
            kind = "walk"
        elif name == "rglob":
            kind, arg = "rglob", node.func.value
        elif name in ("glob", "iglob") and base == "glob":
            kind = "glob-recursive" if _pattern_recursive(node) else None
        elif name == "glob" and isinstance(node.func, ast.Attribute) and base != "glob":
            kind, arg = ("glob-recursive", node.func.value) if _pattern_recursive(node) else (None, None)
        elif name in ("listdir", "scandir") and base == "os":
            kind = name
        if kind is None:
            continue
        if arg is None:
            r, d = "root", "(no argument: cwd)"
        elif kind == "glob-recursive" and base == "glob":
            r, d = reach.of(arg)
        else:
            r, d = reach.of(arg)
        m = _marker(lines, node.lineno)
        out.append({"module": module, "line": node.lineno, "kind": kind,
                    "recursive": kind in RECURSIVE, "reach": r, "root": d,
                    "marked": m is not None, "reason": m})
    return sorted(out, key=lambda s: s["line"])


def needs_mark(c):
    """The rule, restated for the human report (the policy is the authority)."""
    return c["recursive"] and c["reach"] in ("root", "unknown")


def advisory(c):
    """A one-level listdir/scandir of the root: it cannot DESCEND into scratch, so it
    is reported, not denied — but it does see untracked entries (atomic_path's
    `.`-temp among them), which is why most of them were moved to git_tracked."""
    return not c["recursive"] and c["reach"] == "root" and not c["marked"]


def measure(root=ROOT):
    files = git_tracked.files(*SCOPE, root=root)
    cases, unreadable = [], []
    for rel in files:
        path = os.path.join(root, rel)
        borrowed = os.path.islink(path)
        try:
            with open(path, encoding="utf-8") as fh:
                src = fh.read()
            found = sites(src, rel)
        except (OSError, SyntaxError, ValueError) as e:
            unreadable.append({"module": rel, "withheld": f"unreadable: {e}"})
            continue
        for c in found:
            c["borrowed"] = borrowed
        cases.extend(found)
    return {"scope": list(SCOPE), "files": files, "cases": cases, "unreadable": unreadable}


def _selftest():
    ok = True

    def see(label, cond):
        nonlocal ok
        print(f"  {'ok  ' if cond else 'FAIL'} {label}")
        ok = ok and cond

    fixture = (
        "import os, glob, ast\n"
        "from pathlib import Path\n"
        "ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n"
        "for dp, dn, fs in os.walk(ROOT): pass\n"
        "for dp, dn, fs in os.walk(os.path.join(ROOT, 'catalog')): pass\n"
        "# population: a private tempdir\n"
        "for dp, dn, fs in os.walk(d): pass\n"
        "glob.glob(os.path.join(ROOT, '**', '*.py'), recursive=True)\n"
        "Path(ROOT).rglob('*.qml')\n"
        "ast.walk(tree)\n"
        "os.listdir(ROOT)\n"
        "os.listdir(os.path.join(ROOT, 'policy'))\n"
        "glob.glob(os.path.join(ROOT, 'catalog', '*.py'))\n"
        "for dp, dn, fs in os.walk(tmp): pass\n"
    )
    s = {x["line"]: x for x in sites(fixture, "fixture")}
    see("a bare os.walk(ROOT) is a root-reach recursive site, unmarked",
        s.get(4, {}).get("reach") == "root" and s[4]["recursive"] and not s[4]["marked"] and needs_mark(s[4]))
    see("os.walk(join(ROOT, 'catalog')) is bounded", s.get(5, {}).get("reach") == "bounded" and not needs_mark(s[5]))
    see("a marked walk carries its reason", s.get(7, {}).get("reason") == "a private tempdir")
    see("a recursive glob from ROOT/** is root reach", s.get(8, {}).get("reach") == "root"
        and s[8]["kind"] == "glob-recursive")
    see("Path(ROOT).rglob is root reach", s.get(9, {}).get("kind") == "rglob" and s[9]["reach"] == "root")
    see("ast.walk is NOT a disk site", 10 not in s)
    see("os.listdir(ROOT) is root reach, non-recursive: advisory, not denied",
        s.get(11, {}).get("reach") == "root" and not s[11]["recursive"]
        and advisory(s[11]) and not needs_mark(s[11]))
    see("os.listdir(ROOT/policy) is bounded", s.get(12, {}).get("reach") == "bounded")
    see("a non-recursive glob is not a site", 13 not in s)
    see("an unmarked walk of an unknown root must be marked", s.get(14, {}).get("reach") == "unknown"
        and needs_mark(s[14]))
    doc = measure()
    see(f"the live population is non-empty ({len(doc['files'])} files, {len(doc['cases'])} sites)",
        len(doc["files"]) > 0 and len(doc["cases"]) > 0)
    print("check_populations selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_populations: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return _selftest()
    doc = measure()
    if "--json" in argv:
        print(json.dumps(doc, indent=1))
        return 0
    cases = doc["cases"]
    if not doc["files"]:
        print("check_populations: REFUSED — no file in scope; the search is broken", file=sys.stderr)
        return 1
    bad, sub = [], []
    for c in cases:
        need = needs_mark(c)
        tag = (("MARKED (" + (c["reason"] or "") + ")") if c["marked"] else
               "UNMARKED" if need else "advisory: one-level root listing" if advisory(c) else "ok")
        if need and not (c["marked"] and c["reason"]):
            (sub if c["borrowed"] else bad).append(c)
        b = " [borrowed]" if c["borrowed"] else ""
        print(f"  {c['module']}:{c['line']:<5d} {c['kind']:15s} {c['reach']:8s} {c['root'][:40]:40s} {tag}{b}")
    for u in doc["unreadable"]:
        print(f"  SKIP {u['module']}: {u['withheld']}")
    print(f"\ncheck_populations: {len(doc['unreadable'])} file(s) withheld; {len(bad)} unmarked root/unknown walk(s) of {len(cases)} site(s) "
          f"in {len(doc['files'])} file(s); {len(sub)} more in borrowed (substrate) files")
    return 1 if bad or not cases else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
