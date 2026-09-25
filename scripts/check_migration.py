#!/usr/bin/env python3
"""check_migration.py — the one-shot Plasma update script, run headless against a fake shell.

⚑ WHY. templates/one-theme-update.js runs ONCE, on the user's real containments,
by plasmashell — there is no second try. So it runs here first, under Qt's qml
runner, against a fake of the Plasma desktop-scripting API (desktops(),
panels(), widgetIds, widgetById, addWidget, readConfig/writeConfig, remove)
populated like the operator's appletsrc of 2026-09-22: a desktop whose
wallpaperPlugin is a legacy id, a panel with a legacy clock and marquee among
stock widgets. The measurement is what the fake shell looks like afterwards.

    scripts/check_migration.py            # the verdict, as opa_gate migration decides it
    scripts/check_migration.py --json     # the measurement policy/migration.rego decides
    scripts/check_migration.py --selftest

SKIP when the qml runner is absent. WEAKNESS: the fake API is the subset the
script uses; a Plasma API difference (e.g. currentConfigGroup semantics) is
invisible here — that is the live ⊕VER after the emerge.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import qt_sandbox as QT  # noqa: E402

QML = QT.QML


def run():
    import make_deb
    script = make_deb.one_theme_update_js()
    import templates.loader as TL
    harness = TL.render("migration-harness.qml")
    if not os.path.isfile(QML):
        return None
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "update.js"), "w").write(script)
        h = os.path.join(td, "harness.qml")
        open(h, "w").write(harness)
        # the harness reads update.js through XMLHttpRequest, which Qt 6 refuses on
        # file:// unless told otherwise
        env = dict(os.environ, QML_XHR_ALLOW_FILE_READ="1")
        r = QT.run([QML, h], capture_output=True, text=True, env=env, timeout=60)
    for line in (r.stdout + r.stderr).splitlines():
        if "RESULT " in line:
            return json.loads(line.split("RESULT ", 1)[1])
    raise RuntimeError(f"no RESULT from the migration harness (rc={r.returncode}): {(r.stderr or r.stdout)[-600:]}")


def measure():
    """The MEASUREMENT policy/migration.rego decides (W50): the fake shell AFTER
    the one-shot script ran — its desktops (wallpaper plugin) and panels (each
    widget's type, config, geometry). `runner: false` when the qml runner is
    absent: nothing ran, which is withheld, never admitted. What the shell SHOULD
    look like (the one ids, the settings carried, the geometry kept) is the
    policy's ruling, not this function's."""
    m = run()
    if m is None:
        return {"runner": False, "why": f"{QML} not present"}
    return {"runner": True, "desktops": m.get("desktops"), "panels": m.get("panels")}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_migration: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import opa_gate
    return opa_gate.gate("migration")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    # The MEASUREMENT can see; what is a defect is policy/migration_test.rego's (W50).
    m = measure()
    if not m["runner"]:
        print(f"  SKIP — {m['why']}")
        print("check_migration selftest: SKIP")
        return True
    chk("the fake shell reports a desktop", len(m["desktops"] or []) > 0, True)
    chk("the fake shell reports a panel with widgets",
        len((m["panels"] or [{}])[0].get("widgets", [])) > 0, True)
    types = [w["type"] for w in m["panels"][0]["widgets"]]
    # the harness starts from legacy ids; seeing a non-legacy id proves the script RAN
    chk("the script changed the shell (a legacy id was rewritten)",
        "org.el.segclock" in types and m["desktops"][0]["wallpaper"] != "org.el.openglo.live.elazure", True)
    print("check_migration selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
