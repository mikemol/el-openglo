#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_wall_limits.py — which WALL-CLOCK limits does this tree impose on its checks? (W68)

⚑ WHY. Fourteen checks across two nights failed once inside the pre-commit gate and
passed on an immediate replay against an unchanged tree, always with host CPU PSI
near 40%. paperkit caps each check with RLIMIT_CPU=60 s — CPU seconds, which
contention does not inflate — so the suspect is a WALL-CLOCK bound somewhere on a
check's path. This is the census that names every such bound, instead of a grep.

    scripts/check_wall_limits.py --list       # every site: file:line kind bound, claims, on-flaked-path
    scripts/check_wall_limits.py --json       # the measurement (sites, population, claims)
    scripts/check_wall_limits.py --measure    # run the flaked claims' gate commands UNLOADED:
                                              # wall + children CPU, and each on-path bound's
                                              # headroom (bound / measured wall), lowest first
    scripts/check_wall_limits.py --selftest   # the census SEES a subprocess timeout and a Timer

KINDS. `timeout=` on any call (subprocess.run/call/check_output, Popen.wait,
.communicate, a harness's own run(timeout=…)); a `timeout` parameter DEFAULT (a caller
that omits it inherits that bound); threading.Timer(s); signal.alarm(s); a deadline
`time.time()/monotonic()/perf_counter() + N` (best effort); a QML `Timer { interval: N }`
inside a Python string constant (the harness templates), in ms converted to seconds.
A bound that is not a literal, arithmetic of literals, or a module-level constant of
the same file is `dynamic`.

CLAIMS. A site serves a gate claim when its file is REACHABLE from that claim's
`tool:` command (catalog/worklist/warrants.bib, read with mikemol-bibparse):
reach = static imports (including function-local ones) plus any string constant that
names a tree module (`make_schemes`, `render_screens.py`), transitively; an
`opa_gate.py <name>` command also reaches `check_<name>.py`.

⚑ WEAKNESSES, STATED.
  · Reach over-approximates: a string that merely NAMES a module counts as a spawn,
    and every function of a reached file counts as on-path, used or not.
  · Reach under-approximates anything named by a computed string (f"check_{n}.py"
    outside opa_gate) and any spawn of a non-Python program (qml, qmllint, opa)
    whose OWN internal timeouts are invisible here.
  · QML: only `Timer { … interval: N }` in Python string constants (f-string pieces
    joined) is seen; `.qml` files on disk and QML-side `Qt.callLater`/animation
    durations that END a harness are NOT scanned. A QML Timer is not necessarily a
    limit; it is listed because a harness that quits on one IS one.
  · Deadline loops are read from the `clock() + N` expression only; a deadline built
    elsewhere and compared later is `dynamic` or missed.
  · --measure times ONE unloaded run; it is a baseline, not a distribution.
"""

import ast
import json
import os
import re
import resource
import shlex
import subprocess
import sys
import time
from collections.abc import Collection, Iterable, Mapping
from pathlib import Path
from typing import TypedDict, cast

from mikemol.bibparse.bibparse import BibSyntaxError
from mikemol.bibparse.fields import EmptyPopulationError, field_values

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIB = os.path.join(ROOT, "catalog", "worklist", "warrants.bib")
FLAKED = ("EMITTERS", "SCREENS", "TASKSWITCH")  # W68: the three that failed tonight
CLOCKS = {"time", "monotonic", "perf_counter"}


class Site(TypedDict):
    """One wall-clock bound; bound_s is seconds or the string "dynamic"."""

    file: str
    line: int
    kind: str
    callee: str
    bound_s: float | str


class ClaimedSite(Site):
    """A Site plus the gate claims whose command reaches its file."""

    claims: list[str]
    flaked_path: list[str]


class _MeasureBase(TypedDict):
    population: int
    files_with_sites: int
    sites: list[ClaimedSite]
    flaked: list[str]
    flaked_commands: dict[str, str]


class Measure(_MeasureBase, total=False):
    withheld: str


class Run(TypedDict):
    wall_s: float
    cpu_s: float
    rc: int
    tail: str


def _const(node: ast.Constant) -> object:
    """A Constant's value; typeshed types it Any, the cast keeps it out of the census."""
    return cast(object, node.value)


def _str_of(node: ast.AST) -> str | None:
    """The text of a string Constant, else None."""
    if isinstance(node, ast.Constant):
        v = _const(node)
        if isinstance(v, str):
            return v
    return None


def population(root: str = ROOT) -> list[str]:
    """[relpath] — scripts/*.py, catalog/library/*.py and the top-level *.py."""
    out: list[str] = []
    for d in ("", "scripts", os.path.join("catalog", "library")):
        full = os.path.join(root, d)
        if os.path.isdir(full):
            out += sorted(
                os.path.join(d, f) if d else f
                for f in os.listdir(full)
                if f.endswith(".py") and os.path.isfile(os.path.join(full, f))
            )
    return out


def _consts(tree: ast.Module) -> dict[str, float]:
    """{name: number} for module-level `NAME = <numeric expression>`."""
    out: dict[str, float] = {}
    for n in tree.body:
        if (
            isinstance(n, ast.Assign)
            and len(n.targets) == 1
            and isinstance(n.targets[0], ast.Name)
        ):
            v = _num(n.value, out)
            if isinstance(v, (int, float)):
                out[n.targets[0].id] = v
    return out


def _num(node: ast.AST, consts: Mapping[str, float]) -> float | None:
    """A number, or None when the expression is not static."""
    if isinstance(node, ast.Constant):
        cv = _const(node)
        if isinstance(cv, (int, float)) and not isinstance(cv, bool):
            return cv
    if isinstance(node, ast.Name) and node.id in consts:
        return consts[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        v = _num(node.operand, consts)
        return None if v is None else -v
    if isinstance(node, ast.IfExp):
        # `120 if extra else 60` (render_qml): the TIGHTER branch is the bound that bites
        a, b = _num(node.body, consts), _num(node.orelse, consts)
        return None if a is None or b is None else min(a, b)
    if isinstance(node, ast.BinOp):
        a, b = _num(node.left, consts), _num(node.right, consts)
        if a is None or b is None:
            return None
        op = node.op
        if isinstance(op, ast.Add):
            return a + b
        if isinstance(op, ast.Sub):
            return a - b
        if isinstance(op, ast.Mult):
            return a * b
        if isinstance(op, ast.Div):
            return a / b if b else None
        return None
    return None


def _callee(call: ast.Call) -> tuple[str, str]:
    f = call.func
    if isinstance(f, ast.Attribute):
        base = f.value.id if isinstance(f.value, ast.Name) else "?"
        return f"{base}.{f.attr}", f.attr
    if isinstance(f, ast.Name):
        return f.id, f.id
    return "?", "?"


def _is_clock(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and _callee(node)[1] in CLOCKS and not node.args


def _strings(tree: ast.AST) -> list[tuple[int, str]]:
    """[(lineno, text)] — every string constant; an f-string's literal pieces joined.
    Docstrings (a bare string statement) are prose, not templates, and are skipped."""
    out: list[tuple[int, str]] = []
    inner: set[int] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Expr) and _str_of(n.value) is not None:
            inner.add(id(n.value))
    for n in ast.walk(tree):
        if isinstance(n, ast.JoinedStr):
            pieces = [_str_of(v) for v in n.values]
            out.append((n.lineno, "".join("0" if p is None else p for p in pieces)))
            inner.update(id(v) for v in n.values)
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and id(n) not in inner:
            text = _str_of(n)
            if text is not None:
                out.append((n.lineno, text))
    return out


QML_TIMER = re.compile(r"\bTimer\s*\{")


def _qml_timers(text: str) -> list[tuple[int, float | None]]:
    """[(line offset, interval ms or None)] for each `Timer { … }` block (brace-matched)."""
    out: list[tuple[int, float | None]] = []
    for m in QML_TIMER.finditer(text):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        body = text[m.end() : i - 1]
        iv = re.search(r"\binterval\s*:\s*([0-9.]+)\s*(?:[;\n}]|$)", body)
        out.append(
            (
                text.count("\n", 0, m.start()),
                float(body[iv.start(1) : iv.end(1)]) if iv else None,
            )
        )
    return out


def sites_of(path: str, src: str) -> list[Site]:
    """[{file, line, kind, callee, bound_s}] — every wall-clock bound in one file."""
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return [
            {
                "file": path,
                "line": e.lineno or 0,
                "kind": "unparsed",
                "callee": "",
                "bound_s": "dynamic",
            }
        ]
    consts = _consts(tree)
    # a bound passed as a PARAMETER resolves through that parameter's static default
    # (check_marquee_live: `Timer(wall_cap, …)` with `wall_cap=WALL_CAP_S`) — the
    # bound a caller that omits the argument gets. Same-name params in two functions:
    # the last default wins (weakness).
    defaults: dict[str, float] = {}
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            pos = n.args.posonlyargs + n.args.args
            for arg, d in list(
                zip(pos[len(pos) - len(n.args.defaults) :], n.args.defaults)
            ) + [
                (k, d)
                for k, d in zip(n.args.kwonlyargs, n.args.kw_defaults)
                if d is not None
            ]:
                v = _num(d, consts)
                if v is not None:
                    defaults[arg.arg] = v
    out: list[Site] = []

    def add(
        node: ast.expr | ast.stmt, kind: str, callee: str, value: ast.expr | None
    ) -> None:
        v = _num(value, consts) if value is not None else None
        if v is None and isinstance(value, ast.Name) and value.id in defaults:
            v, callee = defaults[value.id], f"{callee} (via default {value.id})"
        out.append(
            {
                "file": path,
                "line": node.lineno,
                "kind": kind,
                "callee": callee,
                "bound_s": "dynamic" if v is None else v,
            }
        )

    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            full, attr = _callee(n)
            for kw in n.keywords:
                if kw.arg == "timeout":
                    kind = {"wait": "wait", "communicate": "communicate"}.get(
                        attr, "call-timeout"
                    )
                    add(n, kind, full, kw.value)
            if attr == "Timer" and full in ("threading.Timer", "Timer"):
                add(n, "threading.Timer", full, n.args[0] if n.args else None)
            if full == "signal.alarm" or (attr == "alarm" and full == "alarm"):
                add(n, "signal.alarm", full, n.args[0] if n.args else None)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            a = n.args
            pos = a.posonlyargs + a.args
            pairs = list(zip(pos[len(pos) - len(a.defaults) :], a.defaults))
            pairs += [
                (k, d) for k, d in zip(a.kwonlyargs, a.kw_defaults) if d is not None
            ]
            for arg, d in pairs:
                if arg.arg == "timeout" and not (
                    isinstance(d, ast.Constant) and _const(d) is None
                ):
                    add(n, "timeout-default", n.name, d)
        elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Add):
            clock, other = (n.left, n.right) if _is_clock(n.left) else (n.right, n.left)
            if isinstance(clock, ast.Call) and _is_clock(clock):
                add(n, "deadline", _callee(clock)[0], other)
    for line, text in _strings(tree):
        for off, ms in _qml_timers(text):
            out.append(
                {
                    "file": path,
                    "line": line + off,
                    "kind": "qml-Timer",
                    "callee": "Timer",
                    "bound_s": "dynamic" if ms is None else ms / 1000.0,
                }
            )
    return sorted(out, key=_line_of)


def _line_of(site: Site) -> int:
    return site["line"]


def _edges(path: str, src: str, stems: Collection[str]) -> set[str]:
    """{stem} this file reaches: imports + string constants naming a tree module."""
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return set()
    out: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out.update(a.name.split(".")[-1] for a in n.names)
        elif isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module.split(".")[-1])
            out.update(a.name for a in n.names)
    for _, s in _strings(tree):
        s = s.strip()
        base = os.path.basename(s)
        out.add(base[:-3] if base.endswith(".py") else s)
    me = os.path.splitext(os.path.basename(path))[0]
    return {s for s in out if s in stems and s != me}


def reach(roots: Iterable[str], graph: Mapping[str, set[str]]) -> set[str]:
    """Transitive closure of stems from `roots` over `graph`."""
    seen: set[str] = set()
    todo = list(roots)
    while todo:
        s = todo.pop()
        if s in seen or s not in graph:
            continue
        seen.add(s)
        todo += graph[s]
    return seen


def claims() -> tuple[dict[str, str], str | None]:
    """({claim: 'tool:… args'}, withheld reason or None) from warrants.bib, read with
    mikemol-bibparse's strict parser; a bib it cannot read is withheld with the reason."""
    try:
        reading = field_values([Path(BIB)], "check")
    except (OSError, BibSyntaxError, EmptyPopulationError) as exc:
        return {}, f"warrants.bib was not readable: {exc}"
    return {k: v for k, v in reading.values.items() if v.startswith("tool:")}, None


def claim_roots(check: str) -> set[str]:
    """The stems a `tool:` command starts from."""
    argv = shlex.split(check[len("tool:") :])
    roots = {os.path.splitext(argv[0])[0]}
    if argv[0] == "opa_gate.py" and len(argv) > 1 and not argv[1].startswith("--"):
        roots.add(f"check_{argv[1]}")
    return roots


def measure(root: str = ROOT) -> Measure:
    pop = population(root)
    srcs: dict[str, str] = {}
    for p in pop:
        with open(os.path.join(root, p), encoding="utf-8", errors="replace") as f:
            srcs[p] = f.read()
    stems = {os.path.splitext(os.path.basename(p))[0]: p for p in pop}
    graph = {s: _edges(p, srcs[p], stems) for s, p in stems.items()}
    cl: dict[str, str]
    why: str | None
    if root == ROOT:
        cl, why = claims()
    else:
        cl, why = {}, "fixture tree — no bib"
    served: dict[str, list[str]] = {}
    for key, check in cl.items():
        for stem in reach(claim_roots(check), graph):
            served.setdefault(stems[stem], []).append(key)
    sites: list[ClaimedSite] = []
    for p in pop:
        for site in sites_of(p, srcs[p]):
            claimed = sorted(served.get(p, []))
            sites.append(
                ClaimedSite(
                    file=site["file"],
                    line=site["line"],
                    kind=site["kind"],
                    callee=site["callee"],
                    bound_s=site["bound_s"],
                    claims=claimed,
                    flaked_path=sorted(set(claimed) & set(FLAKED)),
                )
            )
    out: Measure = {
        "population": len(pop),
        "files_with_sites": len({s["file"] for s in sites}),
        "sites": sites,
        "flaked": list(FLAKED),
        "flaked_commands": {k: cl[k] for k in FLAKED if k in cl},
    }
    if why:
        out["withheld"] = why
    return out


def run_unloaded(check: str) -> Run:
    """{wall_s, cpu_s, rc} for one gate command: wall plus RUSAGE_CHILDREN user+sys delta."""
    argv = shlex.split(check[len("tool:") :])
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    t0 = time.monotonic()
    r = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", argv[0])] + argv[1:],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    wall = time.monotonic() - t0
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = (after.ru_utime - before.ru_utime) + (after.ru_stime - before.ru_stime)
    return {
        "wall_s": round(wall, 2),
        "cpu_s": round(cpu, 2),
        "rc": r.returncode,
        "tail": (r.stdout.strip().splitlines() or [""])[-1][:160],
    }


def headroom(
    m: Measure, runs: Mapping[str, Run]
) -> list[tuple[float, str, ClaimedSite]]:
    """[(ratio, claim, site)] — each numeric on-path bound over that claim's measured wall."""
    rows: list[tuple[float, str, ClaimedSite]] = []
    for s in m["sites"]:
        bound = s["bound_s"]
        for c in s["flaked_path"]:
            if c in runs and isinstance(bound, (int, float)) and runs[c]["wall_s"] > 0:
                rows.append((bound / runs[c]["wall_s"], c, s))
    return sorted(rows, key=_ratio)


def _ratio(row: tuple[float, str, ClaimedSite]) -> float:
    return row[0]


def _fmt(s: Site) -> str:
    b = s["bound_s"]
    return f"{s['file']}:{s['line']:<5} {s['kind']:16s} {b if b == 'dynamic' else f'{b:g}s':>9}  {s['callee']}"


def main(argv: list[str]) -> int:
    known = {"--json", "--list", "--measure", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_wall_limits: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if not m["population"]:
        print(
            "check_wall_limits: REFUSED — empty population (the search is broken)",
            file=sys.stderr,
        )
        return 1
    if "--measure" in argv:
        runs = {c: run_unloaded(cmd) for c, cmd in m["flaked_commands"].items()}
        for c, r in runs.items():
            print(
                f"{c:11s} rc={r['rc']} wall={r['wall_s']}s cpu(children user+sys)={r['cpu_s']}s "
                f"cpu/wall={r['cpu_s'] / r['wall_s']:.2f}  [{m['flaked_commands'][c]}]"
            )
        rows = headroom(m, runs)
        print(
            f"-- headroom (bound / unloaded wall), lowest first: {len(rows)} numeric on-path bound(s)"
        )
        for ratio, c, s in rows:
            print(f"  {ratio:8.2f}x {c:11s} {_fmt(s)}")
        dyn = [s for s in m["sites"] if s["flaked_path"] and s["bound_s"] == "dynamic"]
        print(f"-- {len(dyn)} dynamic on-path bound(s):")
        for s in dyn:
            print(f"  {','.join(s['flaked_path']):20s} {_fmt(s)}")
        if "--json" in argv:
            payload: dict[str, dict[str, Run]] = {"runs": runs}
            print(json.dumps(payload, indent=1))
        return 0
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    if "--list" in argv:
        for s in m["sites"]:
            flag = (
                f"  ⚑ flaked-path {','.join(s['flaked_path'])}"
                if s["flaked_path"]
                else ""
            )
            print(f"{_fmt(s)}  claims={len(s['claims'])}{flag}")
    on = [s for s in m["sites"] if s["flaked_path"]]
    print(
        f"check_wall_limits: {len(m['sites'])} wall-clock bound(s) in {m['files_with_sites']} of "
        f"{m['population']} files; {len(on)} on the path of {'/'.join(FLAKED)}"
        + (f"  (WITHHELD: {m['withheld']})" if "withheld" in m else "")
    )
    return 0


FIXTURE = '''
import subprocess, threading, time, signal
LIMIT = 30
def run(cmd, timeout=45):
    subprocess.run(cmd, timeout=LIMIT * 2)
    subprocess.run(cmd, timeout=timeout)
    threading.Timer(5, lambda: None).start()
    signal.alarm(7)
    deadline = time.monotonic() + 12
QML = """Item { Timer { interval: 2500; running: true; onTriggered: Qt.quit() } }"""
'''


def _selftest() -> bool:
    import tempfile

    ok = True

    def chk(label: str, got: object, want: object) -> None:
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    got = {(s["kind"], s["bound_s"]) for s in sites_of("fixture.py", FIXTURE)}
    chk(
        "sees a subprocess timeout, a module constant resolved",
        ("call-timeout", 60) in got,
        True,
    )
    chk(
        "a parameter passed through resolves via its default",
        ("call-timeout", 45) in got,
        True,
    )
    chk(
        "a name with no static value is dynamic",
        [s["bound_s"] for s in sites_of("d.py", "f(timeout=cfg.t)\n")],
        ["dynamic"],
    )
    chk("sees a threading.Timer", ("threading.Timer", 5) in got, True)
    chk("sees a timeout parameter default", ("timeout-default", 45) in got, True)
    chk("sees signal.alarm", ("signal.alarm", 7) in got, True)
    chk("sees a monotonic deadline", ("deadline", 12) in got, True)
    chk(
        "sees a QML Timer interval in a string, in seconds",
        ("qml-Timer", 2.5) in got,
        True,
    )
    chk(
        "a file with no bound yields nothing",
        sites_of("clean.py", "import os\nos.getcwd()\n"),
        [],
    )
    chk(
        "a docstring naming Timer { } is prose, not a template",
        sites_of("doc.py", '"""a Timer { interval: 5 } in prose"""\n'),
        [],
    )
    chk(
        "a conditional bound reports its tighter branch",
        [s["bound_s"] for s in sites_of("c.py", "f(timeout=120 if x else 60)\n")],
        [60],
    )
    with tempfile.TemporaryDirectory() as td:
        os.makedirs(os.path.join(td, "scripts"))
        with open(os.path.join(td, "scripts", "check_x.py"), "w") as f:
            f.write("import helper\n")
        with open(os.path.join(td, "helper.py"), "w") as f:
            f.write("import subprocess\nsubprocess.run(['x'], timeout=9)\n")
        fm = measure(td)
        chk("the fixture population is 2 files", fm["population"], 2)
        chk(
            "the fixture timeout is found through the tree walk",
            [(s["file"], s["bound_s"]) for s in fm["sites"]],
            [("helper.py", 9)],
        )
    with tempfile.TemporaryDirectory() as td:
        chk(
            "an empty tree is an empty population (main refuses it)",
            measure(td)["population"],
            0,
        )
    graph = {"a": {"b"}, "b": {"c"}, "c": set(), "d": set()}
    chk("reach is transitive and bounded", reach({"a"}, graph), {"a", "b", "c"})
    chk(
        "opa_gate reaches its check",
        claim_roots("tool:opa_gate.py screens"),
        {"opa_gate", "check_screens"},
    )
    cl, why = claims()
    chk(
        "the claims are read from the real bib through mikemol-bibparse",
        (len(cl) > 0, why),
        (True, None),
    )
    chk("an unknown flag is refused", main(["x", "--queit"]), 2)
    print("check_wall_limits selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
