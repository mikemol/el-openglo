#!/usr/bin/env python3
"""check_qt_sandbox.py — every Qt-tool spawn in the tree goes through qt_sandbox (W73).

⚑ WHY.  2026-09-22 20:28 EDT: check_ebuild's staging ran the render gate's
`qml --apptype widget` harness on the operator's real X display and NVIDIA
driver; it SIGSEGV'd in libnvidia-glcore under QRhi::endFrame, wrote a 6.5M
core and raised a KDE crash notification on the desktop. qt_sandbox.run is the
one spawn that strips the session, forces the software scene graph (unless the
operator opts into EL_QT_GPU=1), turns KCrash off and forbids a core. This
check MEASURES which spawn sites use it; policy/qt_sandbox.rego DECIDES.

    scripts/check_qt_sandbox.py             # n of m sites routed; exit 0 iff all
    scripts/check_qt_sandbox.py --json      # the measurement (for opa_gate)
    scripts/check_qt_sandbox.py --list      # one line per site: file:line tool routed gpu
    scripts/check_qt_sandbox.py --selftest  # the measurement can SEE an unrouted fixture
    scripts/check_qt_sandbox.py --root DIR --list   # measure another checkout
    scripts/opa_gate.py qt_sandbox          # the verdict

The population is every spawn call (subprocess.run/Popen/call/check_call/
check_output, os.system, os.exec*/spawn*) in scripts/*.py, catalog/library/*.py
and the top-level *.py whose argv[0] RESOLVES to a Qt tool (QT_TOOLS), plus every
qt_sandbox.run call whatever its argv. argv[0] is resolved through a list
literal's first element, a local or module-level assignment, a call's callee name
(`exe = _qmllint()` → qmllint) and an attribute's name (`RQ.QML` → qml).

⚑ WEAKNESS, STATED.  Resolution is by NAME, one module deep: an argv built in
another function and passed in, or a tool path read from a file, is invisible
(its spawn is not in the population, so it cannot be denied). A spawn of a
Python script that itself spawns qml is counted at the inner site, not the outer.
qt_sandbox.py itself is excluded — its own subprocess.run IS the routing.
"""
import ast
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

QT_TOOLS = frozenset({
    "qml", "qmlscene", "qmltestrunner", "qmllint", "qmlformat", "qmlplugindump",
    "qmlpreview", "plasmoidviewer", "plasmawindowed", "sddm-greeter", "sddm-greeter-qt6",
    "kwin_wayland", "kwin_x11", "plasmashell", "xvfb", "xvfb-run",
})
SPAWN_ATTRS = frozenset({"run", "Popen", "call", "check_call", "check_output"})
OS_SPAWN_PREFIX = ("system", "exec", "spawn", "posix_spawn")
EXCLUDE = frozenset({"qt_sandbox.py"})


def population_files(root=ROOT):
    files = (glob.glob(os.path.join(root, "*.py"))
             + glob.glob(os.path.join(root, "scripts", "*.py"))
             + glob.glob(os.path.join(root, "catalog", "library", "*.py")))
    return sorted(f for f in files if os.path.basename(f) not in EXCLUDE)


def _tool_token(text):
    """'qmllint' from '/usr/lib64/qt6/bin/qmllint', 'QMLLINT', '_qmllint'."""
    t = os.path.basename(str(text)).strip("_").lower()
    return t


class _Module:
    def __init__(self, tree):
        self.tree = tree
        self.consts = {}              # module-level NAME -> value node
        self.qt_aliases = set()       # names bound to the qt_sandbox module
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for a in node.names:
                    if a.name == "qt_sandbox":
                        self.qt_aliases.add(a.asname or a.name)
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        self.consts[t.id] = node.value
        self.parent_fn = {}
        for fn in ast.walk(tree):
            if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for n in ast.walk(fn):
                    self.parent_fn[n] = fn     # innermost wins: ast.walk is outer-first

    def _local(self, fn, name):
        if fn is None:
            return None
        for n in ast.walk(fn):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == name:
                        return n.value
        return None

    def resolve(self, expr, fn, depth=0):
        """The Qt-tool token argv[0] resolves to, or the best name found, or None."""
        if expr is None or depth > 6:
            return None
        if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
            return _tool_token(expr.value)
        if isinstance(expr, (ast.List, ast.Tuple)):
            return self.resolve(expr.elts[0], fn, depth + 1) if expr.elts else None
        if isinstance(expr, ast.BinOp):
            left = self.resolve(expr.left, fn, depth + 1)
            right = self.resolve(expr.right, fn, depth + 1)
            return right if right in QT_TOOLS else left
        if isinstance(expr, ast.Name):
            v = self._local(fn, expr.id)
            if v is None:
                v = self.consts.get(expr.id)
            if v is not None:
                r = self.resolve(v, fn, depth + 1)
                if r is not None:
                    return r
            return _tool_token(expr.id)
        if isinstance(expr, ast.Attribute):
            return _tool_token(expr.attr)
        if isinstance(expr, ast.Call):
            f = expr.func
            name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", None)
            return _tool_token(name) if name else None
        return None

    def spawn_kind(self, call):
        """'qt_sandbox' | 'subprocess' | 'os' | None for a Call node."""
        f = call.func
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            # popen: the streamed twin of run (check_marquee_live, W63), same sandbox
            if f.value.id in self.qt_aliases and f.attr in ("run", "popen"):
                return "qt_sandbox"
            if f.value.id == "subprocess" and f.attr in SPAWN_ATTRS:
                return "subprocess"
            if f.value.id == "os" and f.attr.startswith(OS_SPAWN_PREFIX):
                return "os"
        return None


def _gpu_fact(call):
    for kw in call.keywords:
        if kw.arg == "gpu":
            if isinstance(kw.value, ast.Constant):
                return bool(kw.value.value)
            return "conditional: " + ast.unparse(kw.value)
    return False


def measure_source(src, rel):
    """[case] for one module's source."""
    m = _Module(ast.parse(src, rel))
    cases = []
    for node in ast.walk(m.tree):
        if not isinstance(node, ast.Call):
            continue
        kind = m.spawn_kind(node)
        if kind is None:
            continue
        argv = node.args[0] if node.args else next(
            (k.value for k in node.keywords if k.arg in ("args", "cmd")), None)
        if kind == "os" and node.func.attr.startswith(("exec", "spawn", "posix_spawn")):
            argv = node.args[1] if len(node.args) > 1 else argv
        tool = m.resolve(argv, m.parent_fn.get(node))
        if kind != "qt_sandbox" and tool not in QT_TOOLS:
            continue
        cases.append({"id": f"{rel}:{node.lineno}", "file": rel, "line": node.lineno,
                      "tool": tool, "via": kind, "routed": kind == "qt_sandbox",
                      "gpu": _gpu_fact(node) if kind == "qt_sandbox" else None})
    return cases


def measure(root=ROOT):
    files = population_files(root)
    cases, unparsed = [], []
    for p in files:
        rel = os.path.relpath(p, root)
        try:
            with open(p, encoding="utf-8") as f:
                cases += measure_source(f.read(), rel)
        except (SyntaxError, UnicodeDecodeError, OSError) as e:
            unparsed.append({"id": rel, "withheld": f"{type(e).__name__}: {e}"})
    cases.sort(key=lambda c: (c["file"], c["line"]))
    return {"files_scanned": len(files), "cases": cases + unparsed}


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(("  ok   " if got == want else "  FAIL ") + label +
              ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    fixture = '''
import subprocess
import qt_sandbox as QT
QML = "/usr/lib64/qt6/bin/qml"
def bare(h):
    return subprocess.run([QML, h], capture_output=True)
def via_var(p):
    exe = _qmllint()
    cmd = [exe, "--json", p]
    return subprocess.run(cmd)
def routed(h):
    return QT.run([QML, h], gpu=True)
def not_qt():
    return subprocess.run(["git", "status"])
'''
    cs = {c["line"]: c for c in measure_source(fixture, "fixture.py")}
    check("an unrouted qml spawn is SEEN", (cs.get(6) or {}).get("routed"), False)
    check("...an unrouted qmllint spawn through two assignments is SEEN",
          ((cs.get(10) or {}).get("tool"), (cs.get(10) or {}).get("routed")), ("qmllint", False))
    check("a routed spawn is seen as routed, gpu recorded",
          ((cs.get(12) or {}).get("routed"), (cs.get(12) or {}).get("gpu")), (True, True))
    check("a non-Qt spawn is not in the population", 14 in cs, False)
    check("the population is exactly the three Qt sites", sorted(cs), [6, 10, 12])
    doc = measure()
    check("the real tree's population is non-empty", len(doc["cases"]) > 0, True)
    print("check_qt_sandbox selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    known = {"--json", "--list", "--selftest", "--root"}
    args = argv[1:]
    root = ROOT
    if "--root" in args:
        i = args.index("--root")
        if i + 1 >= len(args) or not os.path.isdir(args[i + 1]):
            print("check_qt_sandbox: --root needs a directory", file=sys.stderr)
            return 2
        root = os.path.abspath(args.pop(i + 1))
    for a in args:
        if a not in known:
            print(f"check_qt_sandbox: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    doc = measure(root)
    if "--json" in argv:
        print(json.dumps(doc, indent=1))
        return 0
    cases = [c for c in doc["cases"] if "withheld" not in c]
    if "--list" in argv:
        for c in cases:
            print(f"{c['id']:44s} {c['tool']:10s} {'routed' if c['routed'] else 'UNROUTED'}"
                  + (f"  gpu={c['gpu']}" if c["routed"] else ""))
        return 0
    if not cases:
        print(f"check_qt_sandbox: REFUSED — 0 Qt spawn sites over {doc['files_scanned']} files; "
              "the search is broken, not the tree clean", file=sys.stderr)
        return 1
    bad = [c for c in cases if not c["routed"]]
    gpu = [c for c in cases if c["routed"] and c["gpu"]]
    if bad:
        print(f"check_qt_sandbox: REFUSED — {len(bad)} of {len(cases)} Qt spawn sites bypass qt_sandbox:",
              file=sys.stderr)
        for c in bad:
            print(f"    {c['id']} ({c['tool']})", file=sys.stderr)
        return 1
    print(f"check_qt_sandbox: {len(cases)} of {len(cases)} Qt spawn sites routed through qt_sandbox "
          f"over {doc['files_scanned']} files; {len(gpu)} ask for the GPU (granted only under EL_QT_GPU=1): "
          + ", ".join(c["id"] for c in gpu))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
