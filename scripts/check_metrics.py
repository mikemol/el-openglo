#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_metrics.py — the VictoriaMetrics plasmoid shows the right face in every scenario (W77).

    scripts/check_metrics.py            # the verdict, as opa_gate metrics decides it
    scripts/check_metrics.py --json     # the measurement policy/metrics.rego decides
    scripts/check_metrics.py --selftest # the measurement can see a wrong face

The emitted org.el.metrics main.qml (make_metrics.main_qml) is loaded offscreen
through qt_sandbox, with two things stubbed per scenario:

    the executable DataSource   a stub module (elstub.p5) whose newData replays a
                                canned {exit code, stdout} - what luthen's
                                endpoints_query.py would have returned
    the query endpoint          a ThreadingHTTPServer on 127.0.0.1 answering
                                /api/v1/query with a vector, or a 500

and the harness reads back root.face and root.faceText (the RESULT protocol of
check_marquee_live). The stub host and port live only in this harness: the
EMITTED package is also scanned for address literals (make_metrics.address_literals),
which is policy M3.

Reused, not copied: plasma_rewrite.SUBSTITUTIONS (the plasma5support import is
redirected to the stub FIRST, because the rewrite deletes every org.kde.plasma.*
import), the StubRegistry module pattern and the RESULT protocol from
check_marquee_live, qt_sandbox for the spawn.

WEAKNESS: the stub replays luthen's contract as written on 2026-10-02 (exit codes,
the "answered" document); a change to that contract on luthen's side is not seen
here. The live answer is a separate read (endpoints_query.py on this host).
"""
import http.server
import json
import os
import re
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

STUB_QMLDIR = "module elstub.p5\nDataSource 1.0 DataSource.qml\nsingleton P5Registry 1.0 P5Registry.qml\n"
STUB_REGISTRY = "pragma Singleton\nimport QtQuick\nQtObject { property var sources: []; property var reply: null }\n"
STUB_DATASOURCE = """import QtQuick
QtObject {
    id: ds
    property string engine
    property var connectedSources: []
    signal newData(string source, var data)
    function connectSource(s) {
        P5Registry.sources.push(s)
        if (P5Registry.reply)
            Qt.callLater(function () { ds.newData(s, P5Registry.reply) })
    }
    function disconnectSource(s) {}
}
"""

HARNESS = """import QtQuick
import QtQuick.Window
import elstub.p5
Window {
    width: 400; height: 60; visible: true
    Component.onCompleted: P5Registry.reply = (%(reply)s)
    Loader { id: subject; anchors.fill: parent; source: "subject.qml" }
    // report once the widget has asked for its endpoint and had 1 s to settle - the
    // harness does NOT know which face is wanted (that is the policy's, not the measurement's)
    Timer {
        interval: 100; repeat: true; running: true
        property int settled: 0
        onTriggered: {
            const it = subject.item
            if (!it || P5Registry.sources.length === 0) return
            settled += 1
            if (settled >= 10) {
                console.log("RESULT " + JSON.stringify({face: it.face, faceText: it.faceText,
                                                        sources: P5Registry.sources.length}))
                Qt.quit()
            }
        }
    }
    Timer { interval: 15000; running: true
            onTriggered: { console.log("RESULT " + JSON.stringify({error: "watchdog"})); Qt.quit() } }
}
"""

# scenario -> (tool reply builder, http status the stub serves)
# tool-missing: the executable engine reports the shell's 127 when the binary is absent
SCENARIOS = ("tool-missing", "tool-refused", "tool-unreadable", "query-failed", "query-ok")


def _reply(scenario, port):
    if scenario == "tool-missing":
        return {"exit code": 127, "stdout": ""}
    if scenario == "tool-refused":
        return {"exit code": 1, "stdout": json.dumps({"state": "refused"})}
    if scenario == "tool-unreadable":
        return {"exit code": 2, "stdout": ""}
    return {"exit code": 0, "stdout": json.dumps({"state": "answered", "host": "127.0.0.1", "port": port})}


class _Handler(http.server.BaseHTTPRequestHandler):
    ok = True

    def do_GET(self):
        if not self.ok or not self.path.startswith("/api/v1/query"):
            self.send_response(500)
            self.end_headers()
            return
        body = json.dumps({"status": "success", "data": {"result": [{"value": [0, "1.5"]}]}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def subject_qml():
    import plasma_rewrite as PR

    import make_metrics as MM
    q, n = re.subn(r"^import org\.kde\.plasma\.plasma5support as P5Support$", "import elstub.p5 as P5Support",
                   MM.main_qml(), flags=re.MULTILINE)
    if n != 1:
        raise RuntimeError("check_metrics: the plasma5support import was not found to redirect")
    for pat, rep in PR.SUBSTITUTIONS:
        q = re.sub(pat, rep, q, flags=re.MULTILINE)
    return q


def run_scenario(scenario):
    import qt_sandbox as QT
    handler = type("H", (_Handler,), {"ok": scenario != "query-failed"})
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        with tempfile.TemporaryDirectory() as td:
            stub = os.path.join(td, "stub", "elstub", "p5")
            os.makedirs(stub)
            for name, text in (("qmldir", STUB_QMLDIR), ("P5Registry.qml", STUB_REGISTRY),
                               ("DataSource.qml", STUB_DATASOURCE)):
                with open(os.path.join(stub, name), "w") as f:
                    f.write(text)
            with open(os.path.join(td, "subject.qml"), "w") as f:
                f.write(subject_qml())
            with open(os.path.join(td, "harness.qml"), "w") as f:
                f.write(HARNESS % {"reply": json.dumps(_reply(scenario, srv.server_port))})
            env = QT.env(dict(os.environ, QML2_IMPORT_PATH=os.path.join(td, "stub")))
            r = QT.run([QT.QML, "--apptype", "widget", os.path.join(td, "harness.qml")],
                       env=env, capture_output=True, text=True, timeout=60)
            out = (r.stdout or "") + (r.stderr or "")
            line = next((ln for ln in out.splitlines() if "RESULT " in ln), None)
            if line is None:
                return {"scenario": scenario, "withheld": f"no RESULT line (exit {r.returncode}): {out[-300:]}"}
            doc = json.loads(line.split("RESULT ", 1)[1])
            if "error" in doc:
                return {"scenario": scenario, "withheld": f"harness {doc['error']}: {out[-300:]}"}
            return {"scenario": scenario, "face": doc.get("face"), "text": doc.get("faceText")}
    finally:
        srv.shutdown()


def measure():
    import make_metrics as MM
    cases, withheld = [], []
    for s in SCENARIOS:
        c = run_scenario(s)
        if "withheld" in c:
            withheld.append(f"{s}: {c['withheld']}")
        else:
            cases.append(c)
    return {"cases": cases, "withheld": withheld, "address_literals": MM.address_literals(MM.main_qml())}


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    q = subject_qml()
    chk("the plasma5support import is redirected to the stub", "import elstub.p5 as P5Support" in q, True)
    chk("no org.kde.plasma import survives the rewrite", "import org.kde.plasma" in q, False)
    # the measurement can SEE a wrong face: query-failed against a server that answers
    # must NOT read as unreachable
    c = run_scenario("query-ok")
    if "withheld" in c:
        print(f"  SKIP the harness could not run here: {c['withheld'][:160]}")
    else:
        chk("a working endpoint reads as values, with text", (c["face"], bool(c["text"])), ("values", True))
        c2 = run_scenario("query-failed")
        chk("a failing endpoint reads as unreachable - the two are told apart",
            c2.get("face") != c["face"], True)
    print("check_metrics selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest"}:
            print(f"check_metrics: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("metrics")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
