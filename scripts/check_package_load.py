#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_package_load.py — load each shipped applet the way Plasma does, and read its errors (W172).

⚑ WHY. check_package_imports asks qmllint whether every type RESOLVES; a package
whose types resolve can still fail to LOAD (a binding error, a missing config key,
a bad import version). This loads the real thing: `plasmawindowed <id>`, Plasma's
own applet host, finding the applet in the tree make_deb.stage() laid down
(XDG_DATA_DIRS = <stage>/usr/share), through qt_sandbox (offscreen, sessionless,
no core). A loaded applet never exits, so each run is read for a fixed window and
then killed; the answer is the LOAD ERRORS on its output, never the exit code.

    scripts/check_package_load.py --json [--stage DIR]   # the measurement
    scripts/check_package_load.py --list [--stage DIR]
    scripts/check_package_load.py --selftest
    scripts/opa_gate.py package_load                     # the verdict (policy/package_load.rego)

WEAKNESS, STATED. plasmawindowed hosts APPLETS: a wallpaper plugin needs a
containment, so org.el.openglo.live is OUTSIDE this population and is reported as
`not_loadable` rather than silently absent. A load error printed after the window
closes is missed; the window is wall time, so on a loaded host an applet that is
still starting reads as clean - the window is generous and the run is reported with
how many output lines it produced, so a silent run is visible as such.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
PLASMAWINDOWED = "/usr/bin/plasmawindowed"
WINDOW_S = 8
# the lines Plasma and the QML engine print when an applet fails to load
ERROR_RE = re.compile(
    r"(is not a type|is not installed|module \"[^\"]+\" .*not|Error loading|"
    r"Cannot assign|ReferenceError|TypeError|failed to load|Could not load|"
    r"plugin .* not found|Unable to assign|Invalid property)",
    re.IGNORECASE,
)


def applets(stage):
    """[id] — every shipped applet (usr/share/plasma/plasmoids/<id>/metadata.json), canonical first."""
    base = os.path.join(stage, "usr", "share", "plasma", "plasmoids")
    ids = sorted(
        d
        for d in (os.listdir(base) if os.path.isdir(base) else [])
        if os.path.isfile(os.path.join(base, d, "metadata.json"))
    )
    return ids


def not_loadable(stage):
    """[id] — shipped plugins plasmawindowed cannot host (wallpapers need a containment)."""
    base = os.path.join(stage, "usr", "share", "plasma", "wallpapers")
    return sorted(
        d
        for d in (os.listdir(base) if os.path.isdir(base) else [])
        if os.path.isfile(os.path.join(base, d, "metadata.json"))
    )


def load(stage, pid, window=WINDOW_S):
    """{id, lines, errors} — one plasmawindowed run, read for `window` seconds then killed."""
    import qt_sandbox as QT

    env = dict(
        os.environ, XDG_DATA_DIRS=os.path.join(stage, "usr", "share") + ":/usr/share"
    )
    proc = QT.popen(
        [PLASMAWINDOWED, pid],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    timer = threading.Timer(window, proc.kill)
    timer.start()
    try:
        out = proc.stdout.read()
    finally:
        timer.cancel()
        proc.kill()
        proc.wait()
    lines = [ln for ln in out.splitlines() if ln.strip()]
    return {
        "id": pid,
        "lines": len(lines),
        "errors": [ln for ln in lines if ERROR_RE.search(ln)],
    }


def measure(stage):
    if not os.path.isfile(PLASMAWINDOWED):
        return {
            "stage": stage,
            "cases": [],
            "not_loadable": [],
            "withheld": f"{PLASMAWINDOWED} is not installed",
        }
    ids = applets(stage)
    if not ids and not os.path.isdir(os.path.join(stage, "usr", "share", "plasma")):
        return {
            "stage": stage,
            "cases": [],
            "not_loadable": [],
            "withheld": f"{stage} is not a staged install tree",
        }
    return {
        "stage": stage,
        "cases": [load(stage, i) for i in ids],
        "not_loadable": not_loadable(stage),
        "withheld": None,
    }


def staged_measure(stage=None):
    if stage:
        return measure(stage)
    import make_deb

    with tempfile.TemporaryDirectory() as td:
        make_deb.stage(td)
        return measure(td)


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            ("  ok   " if got == want else "  FAIL ")
            + label
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk(
        "a type error line is SEEN as a load error",
        bool(ERROR_RE.search("file:///x/main.qml:105:13: SegmentChar is not a type")),
        True,
    )
    chk(
        "a missing module is SEEN",
        bool(ERROR_RE.search('module "org.kde.kcm" is not installed')),
        True,
    )
    chk(
        "an ordinary log line is not",
        bool(ERROR_RE.search("qml: el-marquee rebuild count=0")),
        False,
    )
    with tempfile.TemporaryDirectory() as s:
        os.makedirs(os.path.join(s, "usr", "share", "plasma", "plasmoids", "org.el.a"))
        with open(
            os.path.join(
                s, "usr", "share", "plasma", "plasmoids", "org.el.a", "metadata.json"
            ),
            "w",
        ) as fh:
            fh.write("{}")
        os.makedirs(os.path.join(s, "usr", "share", "plasma", "wallpapers", "org.el.w"))
        with open(
            os.path.join(
                s, "usr", "share", "plasma", "wallpapers", "org.el.w", "metadata.json"
            ),
            "w",
        ) as fh:
            fh.write("{}")
        chk(
            "applets are the plasmoids; wallpapers are named not_loadable, not dropped",
            (applets(s), not_loadable(s)),
            (["org.el.a"], ["org.el.w"]),
        )
    chk(
        "an unstaged tree is withheld",
        measure(tempfile.gettempdir())["withheld"] is not None
        or not os.path.isfile(PLASMAWINDOWED),
        True,
    )
    # ⚑ THE POSITIVE CONTROL: a real plasmawindowed run must SEE a broken applet and a
    # missing one, or a clean result over the shipped applets means nothing
    if not os.path.isfile(PLASMAWINDOWED):
        print(
            f"  SKIP {PLASMAWINDOWED} not installed (2 positive-control arms not run)"
        )
    else:
        with tempfile.TemporaryDirectory() as s:
            ui = os.path.join(
                s,
                "usr",
                "share",
                "plasma",
                "plasmoids",
                "org.el.broken",
                "contents",
                "ui",
            )
            os.makedirs(ui)
            with open(os.path.join(ui, "..", "..", "metadata.json"), "w") as fh:
                json.dump(
                    {
                        "KPlugin": {"Id": "org.el.broken", "Name": "broken"},
                        "KPackageStructure": "Plasma/Applet",
                        "X-Plasma-API-Minimum-Version": "6.0",
                    },
                    fh,
                )
            with open(os.path.join(ui, "main.qml"), "w") as fh:
                fh.write(
                    "import QtQuick\nimport org.kde.plasma.plasmoid\nPlasmoidItem { NoSuchType {} }\n"
                )
            broken = load(s, "org.el.broken")
            chk(
                "a real load of an applet naming a missing type REPORTS a load error",
                len(broken["errors"]) > 0,
                True,
            )
            missing = load(s, "org.el.nothing.shipped")
            chk("...and so does an id nothing ships", len(missing["errors"]) > 0, True)
            if not (broken["errors"] and missing["errors"]):
                print("    broken run said:", broken)
                print("    missing run said:", missing)
    print("check_package_load selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    args = list(argv[1:])
    stage = None
    if "--stage" in args:
        i = args.index("--stage")
        if i + 1 >= len(args) or not os.path.isdir(args[i + 1]):
            print(
                "check_package_load: --stage needs an existing directory",
                file=sys.stderr,
            )
            return 2
        stage = args[i + 1]
        del args[i : i + 2]
    for a in args:
        if a not in ("--json", "--list", "--selftest"):
            print(f"check_package_load: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    m = staged_measure(stage)
    if "--json" in args:
        print(json.dumps(m, indent=1))
        return 0
    if "--list" in args:
        for c in m["cases"]:
            print(
                f"  {c['id']:36} {c['lines']:4} line(s)  {len(c['errors'])} load error(s)"
            )
            for e in c["errors"]:
                print(f"      {e}")
        for w in m["not_loadable"]:
            print(
                f"  {w:36} not loadable by plasmawindowed (a wallpaper needs a containment)"
            )
        bad = sum(1 for c in m["cases"] if c["errors"])
        print(
            f"check_package_load: {len(m['cases']) - bad} of {len(m['cases'])} applet(s) load clean; "
            f"{len(m['not_loadable'])} wallpaper(s) outside the population"
            + (f"; WITHHELD: {m['withheld']}" if m["withheld"] else "")
        )
        return 0
    print(
        "usage: check_package_load.py --json | --list | --selftest [--stage DIR]",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
