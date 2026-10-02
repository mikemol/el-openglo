#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""The operator's VictoriaMetrics on the panel: a Plasma 6 plasmoid (W77).

KDE's system monitors cannot read the operator's VictoriaMetrics; this widget does.

⚑ THE ENDPOINT IS LUTHEN'S, ASKED FOR AT RUNTIME (luthen-observability contract,
2026-10-02): the widget runs `endpoints_query.py vmsingle-http --side host` through
the Plasma5Support executable DataSource at start and on every retry, and builds
/api/v1/query from the JSON it prints. Nothing here, and nothing emitted, carries
luthen's host or port: their rule forbids address literals and policy/metrics.rego
M3 refuses one. Off-cluster (the laptop .deb target) the tool is absent and the
widget says so - reaching luthen from there would be an operator exposure decision.

The tool path and the query set are DATA below, emitted into the QML; the colours
are the active scheme's View roles (one package, ⊕ONE-THEME).

    make_metrics.py           # write plasma-metrics/org.el.metrics
    make_metrics.py --check   # build into a temp dir and run the gate only

WEAKNESS: the gate here is structural (metadata, balance, no address literal). That
the widget shows the right face per scenario is scripts/check_metrics.py's
(not yet built) and policy/metrics.rego's to judge, offscreen.
"""
import json
import os
import re
import shutil
import sys
import tempfile

from emitters import LICENSE_SPDX, atomic_write

PACKAGE_ID = "org.el.metrics"
OUT_DIR = "plasma-metrics"

# luthen's query tool, by absolute path (their contract: runs from any cwd)
LUTHEN = os.path.join(os.path.expanduser("~"), "github", "luthen-observability")
TOOL = [os.path.join(LUTHEN, ".venv", "bin", "python"),
        os.path.join(LUTHEN, "checks", "endpoints_query.py"), "vmsingle-http", "--side", "host"]

# what the widget shows: label, MetricsQL expression, decimals. Metric names are
# ones luthen ingests (policy/alerts/*.rego there); a query that returns no series
# reads as unreachable, never as a blank.
QUERIES = (
    {"label": "CPU", "expr": "sum(rate(container_cpu_usage_seconds_total[5m]))", "digits": 2},
    {"label": "OOM", "expr": "sum(increase(container_oom_events_total[1h]))", "digits": 0},
)

RETRY_MS = 30000

# an address literal: host:port, or a cluster service name
_ADDRESS = re.compile(r"(?:\b[a-z0-9-]+(?:\.[a-z0-9-]+)+:\d{2,5}\b)|(?:\bsvc\.cluster\.local\b)")


def metadata():
    return json.dumps({
        "KPlugin": {
            "Authors": [{"Name": "EL watch themes"}],
            "Category": "System Information",
            "Description": "The operator's VictoriaMetrics on the panel, coloured by the active scheme",
            "Icon": "utilities-system-monitor", "Id": PACKAGE_ID,
            "Name": "EL Metrics", "Version": "1.0",
            "License": LICENSE_SPDX},
        "KPackageStructure": "Plasma/Applet",
        "X-Plasma-API-Minimum-Version": "6.0"}, indent=2)


def tool_command():
    """The executable DataSource source string: the tool, its arguments, shell-quoted."""
    import shlex
    return " ".join(shlex.quote(p) for p in TOOL)


def main_qml():
    import templates.loader as TL
    return TL.render("metrics-main.qml", toolCommand=tool_command().replace('"', '\\"'),
                     queries=json.dumps(list(QUERIES)), retryMs=str(RETRY_MS))


def address_literals(text):
    """Every host:port or cluster service name in `text` - the M3 measurement."""
    return sorted(set(m.group(0) for m in _ADDRESS.finditer(text)))


def render_all(path):
    os.makedirs(os.path.join(path, "contents", "ui"), exist_ok=True)
    atomic_write(os.path.join(path, "metadata.json"), metadata())
    atomic_write(os.path.join(path, "contents", "ui", "main.qml"), main_qml())
    return path


def balanced(s, o, c):
    d = 0
    for ch in s:
        d += (ch == o) - (ch == c)
        if d < 0:
            return False
    return d == 0


def check(path):
    errs = []
    md = json.load(open(os.path.join(path, "metadata.json")))
    if md.get("KPackageStructure") != "Plasma/Applet":
        errs.append("KPackageStructure != Plasma/Applet")
    if md.get("X-Plasma-API-Minimum-Version") != "6.0":
        errs.append("missing X-Plasma-API-Minimum-Version 6.0")
    q = open(os.path.join(path, "contents", "ui", "main.qml")).read()
    if "PlasmoidItem {" not in q:
        errs.append("root is not PlasmoidItem")
    for o, c in (("{", "}"), ("(", ")"), ("[", "]")):
        if not balanced(q, o, c):
            errs.append(f"main.qml unbalanced {o}{c}")
    lits = address_literals(q)
    if lits:
        errs.append(f"address literal(s) in the package: {lits}")
    return errs


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    chk("an address literal is seen", address_literals("x = 'vmsingle.buildbuddy.svc.cluster.local:8428'") != [], True)
    chk("a bare cluster name is seen", address_literals("svc.cluster.local") != [], True)
    chk("a path is not an address", address_literals("/home/u/github/luthen-observability/checks/endpoints_query.py"), [])
    with tempfile.TemporaryDirectory() as td:
        p = render_all(os.path.join(td, PACKAGE_ID))
        chk("the emitted package passes its gate", check(p), [])
        q = open(os.path.join(p, "contents", "ui", "main.qml")).read()
        chk("the query set is emitted as data", all(x["expr"] in q for x in QUERIES), True)
        chk("the endpoint tool is emitted, not an address", ("endpoints_query.py" in q, address_literals(q)), (True, []))
    print("make_metrics selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in ("--check", "--selftest"):
            print(f"make_metrics: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--check" in argv:
        with tempfile.TemporaryDirectory() as td:
            errs = check(render_all(os.path.join(td, PACKAGE_ID)))
        print("make_metrics: gate", "PASS" if not errs else f"FAIL {errs}")
        return 1 if errs else 0
    shutil.rmtree(OUT_DIR, ignore_errors=True)
    path = render_all(os.path.join(OUT_DIR, PACKAGE_ID))
    errs = check(path)
    if errs:
        shutil.rmtree(path)
        print(f"NOT WRITTEN: {PACKAGE_ID}: {errs[:3]}")
        return 1
    print("wrote", PACKAGE_ID)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
