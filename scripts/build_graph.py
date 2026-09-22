#!/usr/bin/env python3
"""build_graph.py — the build graph this repo HAS, derived from the tree (W61).

Operator ruling, 2026-09-22: "I still see a lot of the same defects I thought I'd
been pointing out, some of which I've pointed out twice ... I think part of this
comes from lack of proper re-use and sharing. And doing a proper build graph with
action isolation and declared inputs will dramatically accelerate our fixes AND
help identify our gaps ... discovering build orphans in the build graph will help
clarify, and discovering unconsumed/unbuilt files will help clarify."

⚑ THE RECURRENCE IS THE ARGUMENT. Each defect the operator had to name twice was
the SAME defect in a different COPY: the pip grid (position, then pitch), the
wallpaper failing to load (a renamed plugin id, then a missing companion), three
segment renderers, two render paths, a companion list written once per emitter. A
graph makes each of those visible as a structure rather than as a surprise:

    ORPHAN     a file nothing produces and nothing consumes
    UNBUILT    consumed but never produced — every host tool is one, and an
               undeclared input is exactly what moved the legibility scores when
               media-fonts/unifont appeared between two ticks
    DUPLICATE  two producers of the same output kind over overlapping inputs —
               where the recurring defects live
    UNREACHED  a node no gate depends on

⚑ IT FAILS CLOSED. A relation this tool cannot determine is reported as
INDETERMINATE and makes the run refuse, because an under-covered graph reports its
own blind spot as cleanliness — the same reason linux-sources' generator raises
rather than emit a target keyed on a guess.

    scripts/build_graph.py              # the four findings
    scripts/build_graph.py --nodes      # every node, its kind, its producer
    scripts/build_graph.py --json       # the measurement
    scripts/build_graph.py --selftest   # each finding can be seen

WEAKNESS, STATED: this reads the tree's OWN declarations (each emitter's
render_all, the parity pairs, the lint roster, the policy/check pairing, the
screens plan) plus a conservative scan for file reads. It does NOT trace runtime
behaviour, so a file opened through a computed path is INDETERMINATE rather than
silently absent. That is the fail-closed direction.
"""
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# the host binaries and data a check reaches through PATH or an absolute path.
# ⚑ EVERY ONE IS AN UNDECLARED INPUT: its version is not in any cache key, so a
# bump serves a stale verdict (luthen pins each by sha256 at the host's version
# precisely so a drift is a finding).
HOST_TOOLS = re.compile(
    r'"(/usr/[^"]+|opa|qmllint|qml|tesseract|pandoc|fc-match|fc-list|journalctl|pgrep|plasmashell)"')


# ⚑ NOT THIS TREE'S FILES, even though they sit under it. `worktrees` is where
# isolated agents keep FULL COPIES of the repo (.claude/worktrees/agent-*/).
# Measured 2026-09-22 during the first swarm: this walk descended into six of
# them, doubling every population, and crashed on a copy whose ../substrate
# symlinks do not resolve from that depth. That is this tool's own self-flagged
# undeclared-domain walk (it lists itself first in --undetermined) demonstrating
# exactly why the flag is there: a population nobody declared grew under it.
_NOT_THE_TREE = {".git", "__pycache__", ".ebuild-witness", ".venv", "node_modules",
                 "worktrees"}


def py_files():
    out = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in _NOT_THE_TREE]
        for n in names:
            if n.endswith(".py"):
                out.append(os.path.relpath(os.path.join(base, n), ROOT))
    return sorted(out)


def tree_files(exts=(".qml", ".js", ".kcfg", ".rego", ".bib", ".md", ".colors", ".png", ".svg")):
    out = []
    for base, dirs, names in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in _NOT_THE_TREE]
        for n in names:
            if n.endswith(exts):
                out.append(os.path.relpath(os.path.join(base, n), ROOT))
    return sorted(out)


def written_paths(path):
    """[(expr, func)] for every `open(X, "w")` in a Python file — the PRODUCER
    edges. ⚑ THE FIRST RUN OF THIS TOOL HAD NONE (s136) and reported 214 orphans,
    almost all of them files an emitter writes: a graph with only consumer edges
    calls every product an orphan, which is the tool measuring its own gap and
    printing it as a finding about the repo."""
    try:
        tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open"):
            continue
        mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else ""
        if "w" not in str(mode):
            continue
        out.append(_target_of(node.args[0]) if node.args else None)
    return [o for o in out if o]


def _target_of(expr):
    """The BASENAME a write expression ends in, when it is a literal — os.path.join
    with a trailing constant, or a bare constant. Anything else is INDETERMINATE
    and the caller says so rather than guessing."""
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return os.path.basename(expr.value)
    if isinstance(expr, ast.Call) and getattr(expr.func, "attr", None) == "join":
        last = expr.args[-1] if expr.args else None
        if isinstance(last, ast.Constant) and isinstance(last.value, str):
            return os.path.basename(last.value)
    if isinstance(expr, ast.JoinedStr):          # an f-string: a computed name
        return None
    return None


def computed_edges(path):
    """[(line, direction, why)] for every edge whose target this tool CANNOT
    determine — an f-string, a joined path ending in a variable, a glob, a walk —
    in BOTH directions, read and write.

    ⚑ BOTH BOUNDARIES OR NEITHER (operator, 2026-09-22): "you want both directions,
    consumed and produced. This is boundary-of-a-boundary topological measurement."
    The first fail-closed pass covered reads only, which is the same asymmetry that
    produced the bad number: make_schemes WRITES f"{variant}.colors" and
    make_preview READS it, so the schemes are invisible on both boundaries, and an
    indeterminacy carried on one side alone cancels nothing. ∂ applied to a partial
    ∂ does not vanish; it reports the gap as a finding.

    ⚑ AND THIS IS THE FAIL-CLOSED POINT (s136). The first version called every
    file it could not see a read of an ORPHAN, which is an indeterminate relation
    reported as a finding — the exact inversion this tool's docstring forbids. The
    .colors schemes are opened as f"{variant}.colors" and read every run; 55
    pictures are opened through os.path.join(out_dir, fn). While any of these are
    unresolved, ORPHAN is an upper bound and the run REFUSES rather than certify a
    graph it knows it cannot see."""
    try:
        tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
        # ⚑ A WALK IS AN UNDECLARED DOMAIN, not merely an undeclared edge
        # (operator, 2026-09-22: "the build graph can't be trusted if something
        # walks without it being declared"). It hides the POPULATION, so neither
        # boundary can be computed over it at all — the same defect as a check
        # printing a bare count over a population it never established. This tool
        # walks too; its own walks are in this population and it says so.
        if fn in ("glob", "iglob", "walk", "listdir", "scandir", "rglob"):
            out.append((node.lineno, "domain", f"{fn}(): the population is not declared"))
            continue
        if fn not in ("open", "copy", "copy2", "copytree", "copyfile", "rename", "replace"):
            continue
        if fn != "open":
            args = [a for a in node.args if not isinstance(a, ast.Constant)]
            if args:
                out.append((node.lineno, "write", f"{fn}(<expr>): the target is computed"))
            continue
        if not node.args:
            continue
        mode = (node.args[1].value
                if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r")
        for kw in node.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                mode = kw.value.value
        direction = "write" if any(c in str(mode) for c in "wax") else "read"
        a = node.args[0]
        if isinstance(a, ast.Constant):
            continue
        if isinstance(a, ast.JoinedStr):
            out.append((node.lineno, direction, "open(f-string): the name is computed"))
        elif isinstance(a, ast.Call) and getattr(a.func, "attr", None) == "join":
            last = a.args[-1] if a.args else None
            if not isinstance(last, ast.Constant):
                out.append((node.lineno, direction, "open(join(..., <expr>)): the name is computed"))
        elif isinstance(a, ast.Name):
            out.append((node.lineno, direction, "open(<variable>): the name is computed"))
    return out


def literal_paths(path):
    """Every string literal in a Python file that names a file in this tree, with
    the function it appears in — the conservative read of what it touches."""
    try:
        tree = ast.parse(open(os.path.join(ROOT, path), encoding="utf-8").read())
    except SyntaxError:
        return []
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            if v and ("/" in v or v.endswith((".qml", ".js", ".kcfg", ".rego", ".bib", ".md", ".png"))):
                out.append(v)
    return out


def template_names():
    """The templates each emitter renders, from templates.loader.render's first
    argument — the loader is the ONE reader of templates/, so its call sites are
    the producer edges for every emitted document."""
    out = {}
    for p in py_files():
        text = open(os.path.join(ROOT, p), encoding="utf-8").read()
        for m in re.finditer(r'TL\.render\(\s*"([^"]+)"', text):
            out.setdefault(m.group(1), set()).add(p)
        for m in re.finditer(r'loader\.render\(\s*"([^"]+)"', text):
            out.setdefault(m.group(1), set()).add(p)
    return {k: sorted(v) for k, v in out.items()}


def policy_pairs():
    """{policy: check} — the repo's convention is policy/<n>.rego <-> check_<n>.py,
    and opa_gate.py --list is the authority. A policy with no check, or a check
    whose --json nothing decides, is a broken edge."""
    pol = {}
    pdir = os.path.join(ROOT, "policy")
    for n in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if n.endswith(".rego") and not n.endswith("_test.rego"):
            name = n[:-5]
            pol[f"policy/{n}"] = f"scripts/check_{name}.py"
    return pol


def graph():
    """{nodes: {path: {kind, producers, consumers}}, host: [...], indeterminate: [...]}"""
    nodes = {}
    indeterminate = []

    def touch(path, kind):
        nodes.setdefault(path, {"kind": kind, "producers": [], "consumers": []})

    for p in tree_files():
        kind = ("template" if p.startswith("templates/") else
                "baseline" if p.startswith("catalog/baselines/") else
                "policy" if p.startswith("policy/") else
                "picture" if p.startswith("catalog/library/screens/") else
                "document" if p.endswith(".md") else
                "scheme" if p.endswith(".colors") else
                "package" if p.startswith(("plasma-clock/", "plasma-", "chrome/", "firefox/")) else
                "artifact")
        touch(p, kind)
    for p in py_files():
        touch(p, "tool")

    # templates/<name> is PRODUCED by nothing (it is a source) and CONSUMED by the
    # emitters that render it
    for name, emitters in template_names().items():
        path = f"templates/{name}"
        touch(path, "template")
        nodes[path]["consumers"] = sorted(set(nodes[path]["consumers"]) | set(emitters))

    # a check reads the files its literals name
    for p in py_files():
        for lit in literal_paths(p):
            cand = lit.lstrip("./")
            if cand in nodes and cand != p:
                nodes[cand]["consumers"] = sorted(set(nodes[cand]["consumers"]) | {p})

    # ...and PRODUCES the files it writes. A write names a basename (the directory
    # is usually computed), so a node whose basename matches is credited — an
    # over-attribution in the safe direction: it can call a real product produced,
    # never an orphan produced.
    by_base = {}
    for p in nodes:
        by_base.setdefault(os.path.basename(p), []).append(p)
    for p in py_files():
        for base in written_paths(p):
            for target in by_base.get(base, []):
                nodes[target]["producers"] = sorted(set(nodes[target]["producers"]) | {p})

    # a policy's check is its consumer, and the pairing is a declared edge
    for pol, chk in policy_pairs().items():
        if pol not in nodes:
            indeterminate.append(f"{pol}: a policy with no node")
            continue
        if chk in nodes:
            nodes[pol]["consumers"] = sorted(set(nodes[pol]["consumers"]) | {chk})
        else:
            indeterminate.append(f"{pol}: names {chk}, which is not in the tree")

    host = sorted({m.group(1) for p in py_files()
                   for m in HOST_TOOLS.finditer(open(os.path.join(ROOT, p), encoding="utf-8").read())})

    # ⚑ ∂∂: BOTH BOUNDARIES, AND THE DOMAIN UNDER THEM. Every edge this tool
    # cannot resolve is collected in the direction it runs, so an unresolved
    # WRITE suppresses an "unconsumed" claim exactly as an unresolved READ
    # suppresses an "orphan" one. A declared domain is the precondition for
    # either: a walk hides the population, so neither boundary is computable
    # over it at all.
    undet = {"read": [], "write": [], "domain": []}
    for p in py_files():
        for line, direction, why in computed_edges(p):
            undet[direction].append(f"{p}:{line}: {why}")
    return {"nodes": nodes, "host": host, "indeterminate": indeterminate,
            "undetermined": undet}


def findings(g):
    """⚑ PRODUCED IS NOT CONSUMED (operator, 2026-09-22, correcting this tool's
    first report: "Yes, but are they CONSUMED? Because our gallery and readme are
    relatively sparse"). A file the tree generates and nothing reads is either a
    DELIVERABLE — something stages it for shipping, and that staging is its
    consumer of record — or it is dead output, and the two look identical until
    the staging edge is drawn. So four buckets, not two."""
    nodes = {p: n for p, n in g["nodes"].items() if n["kind"] != "tool"}
    def has(p, k):
        return bool(nodes[p][k])
    u = g["undetermined"]
    # ⚑ AN UNDETERMINED BOUNDARY IS NOT AN ABSENT ONE. While any read is computed,
    # "nothing consumes this" is a statement about the SCAN; while any write is,
    # so is "nothing produces this"; while any domain is undeclared, so is the
    # population both range over. The buckets below are therefore UPPER BOUNDS and
    # the run refuses — reporting them as findings is this tool committing the
    # error it was built to find.
    bounded = bool(u["read"] or u["write"] or u["domain"])
    return {
        "bounded": bounded, "undetermined": u,
        "live": sorted(p for p in nodes if has(p, "producers") and has(p, "consumers")),
        # generated, and nothing in the tree reads it back
        "unconsumed": sorted(p for p in nodes if has(p, "producers") and not has(p, "consumers")),
        # read, but nothing here makes it: a source file, or an undeclared input
        "unproduced": sorted(p for p in nodes if not has(p, "producers") and has(p, "consumers")),
        # neither end attached
        "orphans": sorted(p for p in nodes if not has(p, "producers") and not has(p, "consumers")),
        "host_unbuilt": g["host"], "indeterminate": g["indeterminate"],
        "counts": {k: sum(1 for n in nodes.values() if n["kind"] == k)
                   for k in sorted({n["kind"] for n in nodes.values()})}}


def undetermined_census(g):
    """{idiom: [site]} — the undetermined edges grouped by the SHAPE that defeated
    the scan, so the next resolver is chosen by what would pay rather than by what
    is easy.

    ⚑ MEASURE THE BLIND SPOT BEFORE WIDENING THE APERTURE. paperkit's
    tools/closure.py resolves `Path(__file__).parents[N]`, `ROOT / "sub"` chains
    and names bound to `X.read_text()` — the exact class this tool calls
    INDETERMINATE. That proves the category is a fact about THIS scanner, not
    about the substrate. But paperkit's idioms are pathlib and this tree's are
    os.path.join and f-strings, so porting its rules blind would resolve edges
    that do not exist here and leave the ones that do."""
    out = {}
    for direction, sites in g["undetermined"].items():
        for s in sites:
            idiom = s.split(": ", 1)[1] if ": " in s else s
            out.setdefault(f"{direction}: {idiom}", []).append(s.split(": ", 1)[0])
    return out


def main(argv):
    known = {"--nodes", "--json", "--selftest", "--undetermined"}
    for a in argv[1:]:
        if a not in known:
            print(f"build_graph: unknown flag {a!r}", file=sys.stderr)
            return 2
    g = graph()
    f = findings(g)
    if "--json" in argv:
        print(json.dumps({"graph": g, "findings": f}, indent=1))
        return 0
    if "--undetermined" in argv:
        census = undetermined_census(g)
        total = sum(len(v) for v in census.values())
        if not total:
            print("build_graph: REFUSED — the undetermined population is EMPTY, which "
                  "means the scan found nothing to grade, not that the graph is closed",
                  file=sys.stderr)
            return 1
        for idiom, sites in sorted(census.items(), key=lambda kv: -len(kv[1])):
            files = sorted(set(sites))
            print(f"  {len(sites):4d}  {idiom}")
            print(f"        across {len(files)} file(s): {', '.join(files[:4])}"
                  + (f", +{len(files) - 4} more" if len(files) > 4 else ""))
        print(f"\nbuild_graph: {total} undetermined relation(s) in "
              f"{len(census)} idiom(s)")
        return 0
    if "--nodes" in argv:
        for p, n in sorted(g["nodes"].items()):
            print(f"  {n['kind']:10s} {p}")
            for c in n["consumers"]:
                print(f"             <- {c}")
        return 0
    print(f"nodes by kind: {f['counts']}")
    u = f["undetermined"]
    if f["bounded"]:
        print(f"\n⚑ UPPER BOUNDS ONLY — {len(u['read'])} read / {len(u['write'])} write edge(s)"
              f" computed, {len(u['domain'])} undeclared domain(s).")
        print("  Every bucket below is an OVER-report by exactly what these hide.")
    print(f"\nLIVE — produced here and read here: {len(f['live'])}")
    print(f"\nUNCONSUMED — generated, and NOTHING in the tree reads it back ({len(f['unconsumed'])}).")
    print("  ⚑ Either a DELIVERABLE whose staging edge is not drawn, or dead output.")
    by_kind = {}
    for p in f["unconsumed"]:
        by_kind.setdefault(g["nodes"][p]["kind"], []).append(p)
    for k in sorted(by_kind):
        ps = by_kind[k]
        print(f"    {k:10s} {len(ps):3d}  e.g. {', '.join(ps[:3])}")
    print(f"\nORPHANS — no producer, no consumer ({len(f['orphans'])}):")
    by_kind = {}
    for p in f["orphans"]:
        by_kind.setdefault(g["nodes"][p]["kind"], []).append(p)
    for k in sorted(by_kind):
        ps = by_kind[k]
        print(f"    {k:10s} {len(ps):3d}  e.g. {', '.join(ps[:3])}")
    print(f"\nUNBUILT — reached but produced by nothing, i.e. the UNDECLARED INPUTS ({len(f['host_unbuilt'])}):")
    for h in f["host_unbuilt"]:
        print(f"    {h}")
    if f["bounded"]:
        print("\nUNDETERMINED — the graph cannot be closed over these:")
        for d in ("domain", "write", "read"):
            for i in u[d][:6]:
                print(f"    {d:6s} {i}")
            if len(u[d]) > 6:
                print(f"    {d:6s} ... and {len(u[d]) - 6} more")
    if f["indeterminate"] or f["bounded"]:
        n = len(f["indeterminate"]) + sum(len(v) for v in u.values())
        print(f"\nbuild_graph: REFUSED — {n} relation(s) INDETERMINATE; "
              f"the buckets above are upper bounds, not findings", file=sys.stderr)
        for i in f["indeterminate"]:
            print(f"    {i}", file=sys.stderr)
        return 1
    print(f"\nbuild_graph: {len(g['nodes'])} nodes, every relation determined")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    g = graph()
    chk("the tree has nodes", len(g["nodes"]) > 50, True)
    # ⚑ THE CENSUS MUST PARTITION, not merely count. Measured 2026-09-22: 205
    # undetermined relations fall into 11 idioms, and 116 of them are ONE idiom
    # (`open(<variable>)`), which is what makes a resolver worth writing. A census
    # whose buckets do not sum to the population is a different measurement
    # wearing the population's name.
    census = undetermined_census(g)
    total_sites = sum(len(v) for v in g["undetermined"].values())
    # PARTITION holds at any population size, including zero, so it stays on
    # production: a census whose buckets do not sum to the population is broken
    # whatever the tree looks like.
    chk("the census partitions the undetermined population",
        sum(len(v) for v in census.values()), total_sites)
    # ⚑ POPULATION OVER A FIXTURE, RETIREMENT OVER PRODUCTION (linux-sources-99,
    # 2026-09-22). This used to assert, over PRODUCTION, that the census "is not a
    # single bucket" and that every site names a line — so the day the binding
    # resolver (W61) pays the residue down to one idiom or to zero, the gate goes
    # RED at the moment of the repair. `all()` over an empty census was also
    # vacuously True, so the line check proved nothing once the population
    # retired. Both are claims about whether the SCANNER can see, and they belong
    # on a fixture that cannot be resolved by construction.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        fx = os.path.join(d, "fixture_undetermined.py")
        with open(fx, "w", encoding="utf-8") as fh:
            fh.write("import os, shutil\n"
                     "def f(a, b, c):\n"
                     "    open(a).read()\n"                 # computed read
                     "    open(b, 'w').write('x')\n"        # computed write
                     "    shutil.copy(c, a)\n"              # computed write, another idiom
                     "    return os.listdir(c)\n")          # undeclared domain
        edges = computed_edges(fx)
        fixture_census = {}
        for line, direction, why in edges:
            fixture_census.setdefault(f"{direction}: {why}", []).append(f"{fx}:{line}")
    chk("the census SEES more than one idiom in a fixture", len(fixture_census) > 1, True)
    chk("...and every fixture site names a file and a line",
        (len(edges) > 0, all(":" in s for v in fixture_census.values() for s in v)),
        (True, True))
    # ⚑ THE MEASUREMENT CAN SEE: a template the loader renders has its emitter as a
    # consumer, and a host tool is in the unbuilt set
    tpl = g["nodes"].get("templates/SegmentChar.qml", {})
    chk("a rendered template names its emitter",
        any("make_segment_display" in c for c in tpl.get("consumers", [])), True)
    chk("a host tool is reported as unbuilt", any("opa" in h or "/usr/" in h for h in g["host"]), True)
    chk("a policy names its check",
        "scripts/check_symmetry.py" in g["nodes"].get("policy/aperture.rego", {}).get("consumers", [])
        or "scripts/check_aperture.py" in g["nodes"].get("policy/aperture.rego", {}).get("consumers", []),
        True)
    print("build_graph selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
