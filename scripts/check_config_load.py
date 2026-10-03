#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_config_load.py — does each EMITTED config page LOAD headless, and does Qt say
`Created graphical object was not placed in the graphics scene` while it does? (W163)

catalog/runtime-warnings.json carried that plasmashell line as an open class since
2026-09-22 ("a consequence of the cfg Default refusals, or its own class?"). This
loads each emitted config page (clock, marquee; the page text is the EMITTERS' output,
read through check_template_parity._value, as check_config_page does) in Qt's `qml`
runner under qt_sandbox's mesa route, inside a wrapper Loader that logs the load
status and quits after 2.5 s, and records the page's stderr.

    scripts/check_config_load.py            # n of m summary
    scripts/check_config_load.py --json     # the measurement; policy/config_load.rego decides
    scripts/check_config_load.py --selftest

Reuse: specialises check_config_page's emitted-page read (clock, marquee of its PAIRS)
and uses qt_sandbox.run (the one Qt spawn).

⚑ THE POSITIVE CONTROL. A clean stderr only means something if the harness could have
shown the line. `control_provokes_unplaced` is MEASURED: a document that creates an
Item with `Component.createObject(null)` is run through the same route and its stderr
read for the line. Measured 2026-10-03: it does NOT provoke it, and the string is in no
library under /usr/lib64 (the line comes from plasmashell's own config loader path, not
Qt Quick's), so this host has no headless reproducer. The policy then WITHHOLDS (a
counted SKIP) instead of admitting: not reproduced is not absent.

WEAKNESS: the real KCM host (plasmashell's ConfigModel / AppletConfiguration) is not
here, so the page is loaded as a Loader child, not as plasmashell parents it; a warning
that depends on that parenting cannot appear. kwin_wayland (qt_sandbox mesa) missing,
a timeout, or a crash is a withheld fact. Page loading proves instantiation, not draw.
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
LINE = "Created graphical object was not placed in the graphics scene"
WRAP = (
    "import QtQuick\nItem {\n    width: 600; height: 400\n"
    '    Loader { id: l; anchors.fill: parent; source: "%s"\n'
    '        onStatusChanged: console.log("LOADSTATUS", status) }\n'
    "    Timer { interval: 2500; running: true; onTriggered: Qt.quit() }\n}\n"
)
CONTROL = (
    "import QtQuick\nItem {\n    width: 100; height: 100\n"
    "    Component { id: c; Item {} }\n"
    "    Component.onCompleted: c.createObject(null)\n"
    "    Timer { interval: 1500; running: true; onTriggered: Qt.quit() }\n}\n"
)
PAGES = (
    ("clock-config.qml", "make_clock", "CONFIG_QML"),
    ("marquee-config.qml", "make_notify_marquee", "config_qml"),
)


def read_stderr(text):
    """What the stderr of one run says: the unplaced line's count, the Qt warnings
    other than the harness's own qml: log lines, and the last LOADSTATUS."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    status = None
    others = []
    for ln in lines:
        if ln.startswith("qml: LOADSTATUS"):
            status = int(ln.split()[-1])
        elif not ln.startswith("qml: "):
            others.append(ln[:200])
    return {
        "unplaced": sum(1 for ln in lines if LINE in ln),
        "load_status": status,
        "other_stderr": others,
    }


def run_doc(qml_text, name, runner=None):
    """(fact dict) for one document run headless; a could-not-run is a `withheld`."""
    import qt_sandbox as QT

    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, name), "w") as fh:
            fh.write(qml_text)
        try:
            r = (runner or QT.run)(
                [QT.QML, os.path.join(d, name)],
                mesa=True,
                capture_output=True,
                text=True,
                timeout=90,
                cpu=60,
            )
        except Exception as e:  # noqa: BLE001
            return {"withheld": f"{type(e).__name__}: {str(e)[:160]}"}
    if r.returncode != 0:
        return {"withheld": f"qml exited {r.returncode}", **read_stderr(r.stderr)}
    return read_stderr(r.stderr)


def measure(runner=None, pages=PAGES):
    import check_template_parity as CTP

    out = {"control_provokes_unplaced": None, "pages": []}
    c = run_doc(CONTROL, "control.qml", runner)
    out["control_provokes_unplaced"] = None if "withheld" in c else c["unplaced"] > 0
    for label, mod, acc in pages:
        try:
            page = CTP._value(mod, acc, None)
        except Exception as e:  # noqa: BLE001
            out["pages"].append(
                {
                    "page": label,
                    "withheld": f"{mod}.{acc} raised {type(e).__name__}: {e}",
                }
            )
            continue
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, label), "w") as fh:
                fh.write(page)
            with open(os.path.join(d, "wrap.qml"), "w") as fh:
                fh.write(WRAP % label)
            import qt_sandbox as QT

            try:
                r = (runner or QT.run)(
                    [QT.QML, os.path.join(d, "wrap.qml")],
                    mesa=True,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    cpu=60,
                )
            except Exception as e:  # noqa: BLE001
                out["pages"].append(
                    {"page": label, "withheld": f"{type(e).__name__}: {str(e)[:160]}"}
                )
                continue
        fact = {"page": label, **read_stderr(r.stderr)}
        if r.returncode != 0:
            fact["withheld"] = f"qml exited {r.returncode}"
        out["pages"].append(fact)
    return out


class _R:
    def __init__(self, rc, err):
        self.returncode, self.stderr = rc, err


def _selftest():
    ok_line = read_stderr(f"qml: LOADSTATUS 1\nQQuickItem: {LINE}.\n")
    clean = read_stderr("qml: LOADSTATUS 1\n")
    err = read_stderr(
        'qml: LOADSTATUS 3\nfile:///x.qml:3: module "org.kde.kcm" is not installed\n'
    )
    seen = {
        "the unplaced line is counted": ok_line["unplaced"] == 1,
        "a clean run counts none and reads status": clean["unplaced"] == 0
        and clean["load_status"] == 1,
        "an error status and its Qt line are seen": err["load_status"] == 3
        and len(err["other_stderr"]) == 1,
    }
    m = measure(
        runner=lambda *a, **k: _R(0, f"qml: LOADSTATUS 1\nW: {LINE}\n"),
        pages=(("clock-config.qml", "make_clock", "CONFIG_QML"),),
    )
    seen["a provoking control is seen"] = m["control_provokes_unplaced"] is True
    seen["a provoked page is seen"] = m["pages"][0]["unplaced"] == 1
    m = measure(
        runner=lambda *a, **k: (_ for _ in ()).throw(OSError("no kwin")),
        pages=(("clock-config.qml", "make_clock", "CONFIG_QML"),),
    )
    seen["a spawn failure is withheld, not clean"] = (
        "withheld" in m["pages"][0] and m["control_provokes_unplaced"] is None
    )
    for label, ok in seen.items():
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
    print("check_config_load selftest:", "PASS" if all(seen.values()) else "FAIL")
    return all(seen.values())


def main(argv):
    for a in argv[1:]:
        if a not in ("--json", "--selftest"):
            print(f"check_config_load: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    n = len(m["pages"])
    ready = sum(
        1 for p in m["pages"] if p.get("load_status") == 1 and "withheld" not in p
    )
    hit = sum(p.get("unplaced", 0) > 0 for p in m["pages"])
    print(
        f"check_config_load: {ready} of {n} page(s) loaded Ready; {hit} of {n} showed the unplaced line; "
        f"control provokes it: {m['control_provokes_unplaced']}; the verdict is `opa_gate.py config_load`"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
