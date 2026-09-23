#!/usr/bin/env python3
"""check_migration.py — the one-shot Plasma update script, run headless against a fake shell.

⚑ WHY. templates/one-theme-update.js runs ONCE, on the user's real containments,
by plasmashell — there is no second try. So it runs here first, under Qt's qml
runner, against a fake of the Plasma desktop-scripting API (desktops(),
panels(), widgetIds, widgetById, addWidget, readConfig/writeConfig, remove)
populated like the operator's appletsrc of 2026-09-22: a desktop whose
wallpaperPlugin is a legacy id, a panel with a legacy clock and marquee among
stock widgets. The measurement is what the fake shell looks like afterwards.

    scripts/check_migration.py            # exit 0 iff the migration lands as stated
    scripts/check_migration.py --json     # the measurement
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


def problems(m):
    bad = []
    if m["desktops"][0]["wallpaper"] != "org.el.openglo.live":
        bad.append(f"desktop wallpaper is {m['desktops'][0]['wallpaper']!r}, not org.el.openglo.live")
    types = [w["type"] for w in m["panels"][0]["widgets"]]
    for legacy in ("org.el.segclock.elazure", "org.el.notifymarquee.elazure"):
        if legacy in types:
            bad.append(f"legacy applet {legacy} survived")
    for one in ("org.el.segclock", "org.el.notifymarquee"):
        if types.count(one) != 1:
            bad.append(f"{one} appears {types.count(one)} times, not once")
    if "org.kde.plasma.kickoff" not in types:
        bad.append("a stock widget was lost")
    mq = [w for w in m["panels"][0]["widgets"] if w["type"] == "org.el.notifymarquee"]
    if mq and mq[0]["config"].get("hoverPause") != "false":
        bad.append(f"the marquee's settings were not carried (hoverPause={mq[0]['config'].get('hoverPause')!r})")
    if mq and mq[0]["geometry"] != [300, 0, 420, 30]:
        bad.append(f"the marquee moved: {mq[0]['geometry']}")
    return bad


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_migration: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = run()
    if m is None:
        print(f"check_migration: SKIP — {QML} not present", file=sys.stderr)
        return 0
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    bad = problems(m)
    if bad:
        print(f"check_migration: REFUSED — {len(bad)} problem(s):", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print("check_migration: the one-shot update moves 1 desktop wallpaper and 2 legacy applets to the one ids, "
          "settings and geometry kept, stock widgets untouched")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    m = run()
    if m is None:
        print("  SKIP — no qml runner")
        print("check_migration selftest: SKIP")
        return True
    chk("the migration lands", problems(m), [])
    # ⚑ THE CHECK CAN FAIL: an untouched fake shell is refused
    stale = json.loads(json.dumps(m))
    stale["desktops"][0]["wallpaper"] = "org.el.openglo.live.elazure"
    chk("a desktop still on a legacy wallpaper is seen", any("wallpaper" in b for b in problems(stale)), True)
    stale = json.loads(json.dumps(m))
    stale["panels"][0]["widgets"].append({"type": "org.el.segclock.elazure", "config": {}, "geometry": [0, 0, 1, 1]})
    chk("a surviving legacy applet is seen", any("survived" in b for b in problems(stale)), True)
    print("check_migration selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
