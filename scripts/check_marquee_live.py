#!/usr/bin/env python3
"""check_marquee_live.py — the WHOLE marquee, run headless against a stubbed notification model.

⚑ WHY (operator, 2026-09-22: "Is there a sandbox we can run the widget within,
to capture its output, and use that for positive validation that it responds
to notifications and stuff? Kinda like how web app integration test engines
might drive a headless chrome"). check_marquee_body proves the ARITHMETIC;
nothing ran the WIDGET, and the dead-rotation defect (COTYPE s98) lived
entirely in the widget: a `running:` binding the animation's own end
discarded. This is the sandbox: the emitted main.qml, rewritten exactly as
render_qml rewrites it (the Plasma root becomes an Item; `plasmoid` is a
mock whose configuration is the kcfg's defaults), loaded under Qt's `qml`
on the offscreen platform with `org.kde.notificationmanager` SHADOWED by a
stub module on QML2_IMPORT_PATH — a ListModel carrying the real role enum
values (measured from notificationmanager.qmltypes) so the widget's
`data(index, IdRole)` reads are honoured unchanged.

The harness drives the stub on a fixed timeline (arrive, expire, arrive,
replace, expire) and SAMPLES the board every 40 ms: tickerText, boardX,
boardRunning. The measurement (`--json`) is the events and the samples; the
requirement is policy/marquee_live.rego (a board that shows text is running;
every arrival is shown; a drained board wakes for the next arrival; x never
jumps forward mid-rotation), tested by opa test with the dead-rotation trace
as the refusing fixture.

    scripts/check_marquee_live.py --json      # the measurement
    scripts/check_marquee_live.py --trace     # the samples, one per line
    scripts/check_marquee_live.py --selftest  # the measurement can see

`withheld` when the qml runner is absent. WEAKNESS: the stub is a ListModel,
not libnotificationmanager — it honours count/index/data and the enums the
widget reads, nothing more; a widget reading a role the stub does not carry
gets undefined, which the trace shows as missing text rather than a crash.
The timeline is wall-clock inside qml (Timers), so a loaded host stretches
the samples' t; the rules are stated over ORDER and presence, never over
durations.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
QML = "/usr/lib64/qt6/bin/qml"
VARIANT = "EL-Openglo"

# the role ints the widget reads, from notificationmanager.qmltypes (Qt::UserRole + 0…)
STUB_QMLDIR = "module org.kde.notificationmanager\nNotifications 1.0 Notifications.qml\nsingleton StubRegistry 1.0 StubRegistry.qml\n"
STUB_REGISTRY = "pragma Singleton\nimport QtQuick\nQtObject { property var models: [] }\n"
STUB_MODEL = """import QtQuick
// ⚑ NOT A ListModel (measured 2026-09-22 against the operator's trace): ListModel
// emits countChanged synchronously inside append(), so a widget reading rows on
// countChanged saw a row the REAL model had already removed by the time its
// countChanged arrived (`rebuild count=0` for every single notify-send). This
// stub signals like the real one: rowsInserted synchronously at insertion with
// the data readable, count updated from a deferred call.
QtObject {
    id: stub
    readonly property bool isStub: true
    property var rows: []
    property int count: 0
    signal rowsInserted(var parent, int first, int last)
    signal rowsAboutToBeRemoved(var parent, int first, int last)
    signal rowsRemoved(var parent, int first, int last)
    signal dataChanged(var topLeft, var bottomRight, var roles)
    function syncCount() { stub.count = stub.rows.length; }
    function get(i) { return stub.rows[i]; }
    function append(obj) { stub.rows.push(obj); stub.rowsInserted(null, stub.rows.length - 1, stub.rows.length - 1); Qt.callLater(syncCount); }
    // the host trace's shape (2026-09-22): a row that was never signalled IN — only
    // its removal is signalled, ~5 s later
    function appendSilently(obj) { stub.rows.push(obj); }
    function remove(i) { stub.rowsAboutToBeRemoved(null, i, i); stub.rows.splice(i, 1); stub.rowsRemoved(null, i, i); Qt.callLater(syncCount); }
    function set(i, obj) { stub.rows[i] = obj; stub.dataChanged(stub.index(i, 0), stub.index(i, 0), []); }
    enum Roles { IdRole = 256, SummaryRole, ImageRole, IsGroupRole, GroupChildrenCountRole, ExpandedGroupChildrenCountRole,
                 IsGroupExpandedRole, IsInGroupRole, TypeRole, CreatedRole, UpdatedRole, BodyRole, IconNameRole,
                 DesktopEntryRole, NotifyRcNameRole, ApplicationNameRole, ApplicationIconNameRole, OriginNameRole,
                 JobStateRole, PercentageRole, JobErrorRole, SuspendableRole, KillableRole, JobDetailsRole,
                 ActionNamesRole, ActionLabelsRole, HasDefaultActionRole, DefaultActionLabelRole, UrlsRole,
                 UrgencyRole, TimeoutRole, ConfigurableRole, ConfigureActionLabelRole, ClosableRole, ExpiredRole,
                 DismissedRole, ReadRole, UserActionFeedbackRole }
    enum SortMode { SortByDate, SortByTypeAndUrgency }
    enum GroupMode { GroupDisabled, GroupApplicationsFlat, GroupApplicationsTree }
    property bool showNotifications: false
    property bool showJobs: false
    property int sortMode: Notifications.SortByDate
    property int groupMode: Notifications.GroupDisabled
    readonly property var roleNames: ({ 256: "notificationId", 257: "summary", 267: "body", 271: "applicationName",
                                        285: "urgency", 275: "percentage", 290: "expired" })
    function data(idx, role) { var r = stub.get(idx.row); if (!r) return undefined; var k = roleNames[role]; return k ? r[k] : undefined; }
    function index(row, col) { return { row: row, column: col }; }
    Component.onCompleted: StubRegistry.models.push(stub)
}
"""

# the timeline: (t ms, op, id, fields). The widget's rotation at speed 8 on a
# 420 px board is ~1.5 s, so each phase spans at least one full rotation.
TIMELINE = [
    # (t ms, op, id, model fields, the text the board must show afterwards)
    (300, "arrive", 1, {"summary": "hello", "body": "", "applicationName": "app"}, "app: hello"),
    (2600, "expire", 1, {}, ""),
    # ⚑ THE LIVE HOST'S CASE (operator's trace, 2026-09-22): the real model inserted
    # the row and removed it within the SAME turn — every single notify-send logged
    # `rebuild count=0`. A flash arrives and vanishes in one step; it is still owed
    # a rotation.
    (3900, "flash", 9, {"summary": "flash", "body": "", "applicationName": "app"}, "app: flash"),
    # the host trace's lone notification: never signalled in, removed ~5 s later
    (4300, "silent", 11, {"summary": "silent", "body": "", "applicationName": "app"}, ""),
    (4700, "expire", 11, {}, "app: silent"),
    (5200, "arrive", 2, {"summary": "second", "body": "<b>bold</b>", "applicationName": "app"}, "app: second — bold"),
    (5600, "replace", 2, {"summary": "second", "body": "changed", "applicationName": "app"}, "app: second — changed"),
    (8200, "expire", 2, {}, ""),
]
END_MS = 30000            # the CAP; the main run ends when every event has fired and the board drained
SAMPLE_MS = 40

HARNESS = """import QtQuick
import QtQuick.Window
import org.kde.notificationmanager as NM
Window {
    id: harness
    width: 420; height: 40; visible: true; color: "%(ground)s"
    property var plasmoid: QtObject { property var configuration: (%(config)s) }
    Loader {
        id: subject; anchors.fill: parent; source: "subject.qml"
        onStatusChanged: if (status === Loader.Error) { console.log("RESULT " + JSON.stringify({ error: "subject failed to load" })); Qt.quit(); }
    }
    // a watchdog: whatever happens, the run ends and says what it saw
    Timer { interval: %(end)d + 3000; running: true; onTriggered: { console.log("RESULT " + JSON.stringify({ error: "watchdog", status: subject.status, events: events, samples: samples })); Qt.quit(); } }
    property var events: []
    property var samples: []
    // the stub registers itself when the subject instantiates it; look it up late
    function model() { return NM.StubRegistry.models[0]; }
    // over the stub's ROWS, not its count: count is deferred like the real model's
    function rowOf(id) { var m = model(); for (var i = 0; i < m.rows.length; i++) if (m.rows[i].notificationId === id) return i; return -1; }
    function apply(step) {
        var m = model();
        if (step.op === "arrive") m.append(Object.assign({ notificationId: step.id }, step.fields));
        else if (step.op === "expire") { var r = rowOf(step.id); if (r >= 0) m.remove(r); }
        else if (step.op === "replace") { var r2 = rowOf(step.id); if (r2 >= 0) m.set(r2, Object.assign({ notificationId: step.id }, step.fields)); }
        else if (step.op === "flash") { m.append(Object.assign({ notificationId: step.id }, step.fields)); m.remove(rowOf(step.id)); }
        else if (step.op === "silent") m.appendSilently(Object.assign({ notificationId: step.id }, step.fields));
        events.push({ t: clock.elapsed(), op: step.op, id: step.id, shows: step.shows });
    }
    property var timeline: %(timeline)s
    property int next: 0
    property int pausedSeen: 0
    property bool sawText: false
    property bool grabbed: false
    property bool grabbedPaused: false
    QtObject { id: clock; property double t0: Date.now(); function elapsed() { return Date.now() - t0; } }
    Timer {
        interval: %(sample)d; running: subject.status === Loader.Ready; repeat: true
        onTriggered: {
            var now = clock.elapsed();
            while (harness.next < timeline.length && timeline[harness.next].t <= now) { apply(timeline[harness.next]); harness.next += 1; }
            var s = subject.item;
            samples.push({ t: now, text: s.tickerText, x: s.boardX, raw: s.boardRawX, w: s.boardWidth, running: s.boardRunning,
                           paused: s.boardPaused, ring: s.ringOpacity, count: model().count,
                           lit: String(s.litColor), ghost: String(s.ghostColor), ground: String(s.voidColor) });
            if (s.boardPaused) harness.pausedSeen += 1;
            // W52: a screenshot at the first sample with the text mid-board (its left
            // edge inside the board, still running), and one while the pulse holds it
            var grab = %(grab)s;
            if (grab && !harness.grabbed && s.tickerText !== "" && s.boardRunning && !s.boardPaused
                && s.boardX < harness.width * 0.5 && s.boardX > 0) {
                harness.grabbed = true;
                harness.contentItem.grabToImage(function (r) { r.saveToFile(grab); });
            }
            var grabPaused = %(grab_paused)s;
            if (grabPaused && !harness.grabbedPaused && s.boardPaused && harness.pausedSeen >= 8) {
                harness.grabbedPaused = true;
                harness.contentItem.grabToImage(function (r) { r.saveToFile(grabPaused); });
            }
            // the run ends on its CONDITION, else on the clock (a cap, not a plan):
            // the hovered run once enough paused samples are seen; the main run
            // once every event has fired and the board has drained (text empty,
            // not running) — a loaded host stretches the timeline and a fixed cap lied
            var drained = harness.next >= timeline.length && s.tickerText === "" && !s.boardRunning && harness.sawText;
            if (s.tickerText !== "") harness.sawText = true;
            if ((%(stop_paused)d > 0 && harness.pausedSeen >= %(stop_paused)d) || (%(stop_paused)d === 0 && drained) || now >= %(end)d) {
                console.log("RESULT " + JSON.stringify({ events: events, samples: samples, width: harness.width }));
                Qt.quit();
            }
        }
    }
}
"""


def subject(hover_pause=False, variant=VARIANT):
    """The emitted marquee, rewritten as render_qml rewrites it, plus its companions.

    hover_pause is OFF for the measured run: the offscreen platform's pointer rests at
    (0,0), so the Row is "hovered" the moment its left edge reaches the board's, and
    the hover-pause (a setting since W49, on by default) would hold every run there.
    The `--hovered` mode runs WITH it on, to show that this is the pointer and not
    the widget. `variant` selects the scheme the run resolves under (the emission is
    one package; the variant is the theme it is run in)."""
    import render_qml as RQ
    import make_notify_marquee as NM
    import make_preview
    qml = NM.main_qml()
    for pat, rep in RQ.SUBSTITUTIONS:
        qml = re.sub(pat, rep, qml, flags=re.M)
    config = RQ._kcfg_defaults(NM.config_xml())
    config["speed"] = 8.0        # a rotation ~1.5 s on the 420 px board
    config["hoverPause"] = hover_pause
    config["debugLog"] = True         # the widget's own trace lines ride on stderr
    return qml, config, make_preview.parse_scheme(variant)["ground"], {
        "MatrixChar.qml": NM.matrix_char_component(),
        "MatrixField.qml": NM.matrix_field_component(),
        "marquee-body.js": NM.body_parser(),
    }


HOVER_STOP_SAMPLES = 20   # the hovered run ends once this many paused samples are seen
HOVER_CAP_MS = 12000      # ...or here, on a host too slow to reach the pointer


def run(hover_pause=False, end_ms=None, stop_paused=0, variant=VARIANT, grab=None, grab_paused=None):
    """{'events': [...], 'samples': [...], 'width': W} or None when the runner is absent.

    ⚑ THE HOVERED RUN ENDS ON ITS CONDITION, NOT THE CLOCK (measured 2026-09-22:
    a 2.6 s cap passed on an idle host and refused under the pre-commit gate's
    load, where the board had not yet reached the pointer). The timeline is
    wall-clock inside qml; every rule is over order and presence, and now the
    run length is too.

    ⚑ UNDER THE REAL THEME (W35): the widget is BOUND to Kirigami.Theme, so the
    run happens in theme_probe.env_for(variant) — the KDE platform theme reading
    a private kdeglobals that IS the variant's .colors, as a widgets app. What
    the board draws is what that variant's scheme resolves to."""
    if not os.path.isfile(QML):
        return None
    os.chdir(ROOT)
    import theme_probe as TP
    if TP.scheme_path(variant) is None:
        return None
    qml, config, ground, files = subject(hover_pause, variant)
    with tempfile.TemporaryDirectory() as td:
        stub = os.path.join(td, "stub", "org", "kde", "notificationmanager")
        os.makedirs(stub)
        xdg = os.path.join(td, "xdg")
        os.makedirs(xdg)
        open(os.path.join(stub, "qmldir"), "w").write(STUB_QMLDIR)
        open(os.path.join(stub, "StubRegistry.qml"), "w").write(STUB_REGISTRY)
        open(os.path.join(stub, "Notifications.qml"), "w").write(STUB_MODEL)
        open(os.path.join(td, "subject.qml"), "w").write(qml)
        for name, text in files.items():
            open(os.path.join(td, name), "w").write(text)
        timeline = [{"t": t, "op": op, "id": i, "fields": f, "shows": s} for t, op, i, f, s in TIMELINE]
        open(os.path.join(td, "harness.qml"), "w").write(HARNESS % {
            "ground": ground, "config": json.dumps(config), "timeline": json.dumps(timeline),
            "sample": SAMPLE_MS, "end": end_ms or END_MS, "stop_paused": stop_paused,
            "grab": json.dumps(os.path.abspath(grab)) if grab else "null",
            "grab_paused": json.dumps(os.path.abspath(grab_paused)) if grab_paused else "null"})
        # theme_probe's environment (the real theme on the variant's scheme) plus the
        # notification stub on the import path. console.log IS a debug message and
        # the RESULT line rides on it, so only kirigami's own category is quieted.
        env = TP.env_for(variant, xdg)
        env.update(QML2_IMPORT_PATH=os.path.join(td, "stub"),
                   QT_QUICK_BACKEND=os.environ.get("EL_QUICK_BACKEND", "software"))
        r = subprocess.run([QML, "--apptype", "widget", os.path.join(td, "harness.qml")], env=env,
                           capture_output=True, text=True, timeout=120)
    log = [l.split("el-marquee ", 1)[1] for l in (r.stdout + r.stderr).splitlines() if "el-marquee " in l]
    for line in (r.stdout + r.stderr).splitlines():
        if "RESULT " in line:
            res = json.loads(line.split("RESULT ", 1)[1])
            if "error" in res:
                raise RuntimeError(f"marquee harness: {res['error']}: {(r.stderr or r.stdout)[-800:]}")
            res["log"] = log
            return res
    raise RuntimeError(f"no RESULT from the marquee harness (rc={r.returncode}): {(r.stderr or r.stdout)[-800:]}")


def run_hovered(variant=VARIANT, grab_paused=None):
    return run(hover_pause=True, end_ms=HOVER_CAP_MS, stop_paused=HOVER_STOP_SAMPLES, variant=variant,
               grab_paused=grab_paused)


def screenshot(variant, out_scroll, out_paused):
    """Two stills of the real widget under `variant`'s scheme (W52): mid-scroll, and
    held by the hover-pause with the ring pulsing. Returns the two paths that exist."""
    run(variant=variant, end_ms=4000, grab=out_scroll)
    run_hovered(variant, grab_paused=out_paused)
    return [p for p in (out_scroll, out_paused) if os.path.isfile(p)]


def expected_colors(variant):
    """The variant's solved tokens as the widget's bound colours must resolve (W35)."""
    import make_wallpaper_live as WL
    ground, lit, ghost, _a = WL.colors_for(variant)
    return {"lit": "#%02x%02x%02x" % lit, "ghost": "#%02x%02x%02x" % ghost, "ground": "#%02x%02x%02x" % ground}


def measure(res, hovered=None, variant=VARIANT):
    """The measurement: the main run, and (W51) the HOVERED run — hover-pause on,
    the offscreen pointer at (0,0) holding the board — so the pulse rule has a
    paused trace to range over. Both are the real widget, run under `variant`'s
    scheme (W35); `expected` carries that variant's tokens for the binding rule."""
    if res is None:
        return {"runner": False, "variant": variant, "expected": expected_colors(variant),
                "events": [], "samples": [], "width": 0, "log": [], "hovered": {"samples": []}}
    return {"runner": True, "variant": variant, "expected": expected_colors(variant),
            "events": res["events"], "samples": res["samples"], "width": res["width"],
            "log": res.get("log", []),
            "hovered": {"samples": hovered["samples"] if hovered else []}}


def main(argv):
    known = {"--json", "--trace", "--hovered", "--variant", "--selftest"}
    variant = VARIANT
    args = list(argv[1:])
    if "--variant" in args:
        i = args.index("--variant")
        if i + 1 >= len(args):
            print("check_marquee_live: --variant needs a name", file=sys.stderr)
            return 2
        variant = args[i + 1]
        del args[i:i + 2]
    for a in args:
        if a not in known:
            print(f"check_marquee_live: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--hovered" in args:
        # the pointer explanation, shown: with hover-pause ON the run halts at x≈0.
        # With --json too, the stalled trace is emitted AS THE MAIN RUN — the
        # policy's refusing input for L6, produced by the real widget rather than typed.
        h = run_hovered(variant)
        m = measure(h, h, variant)
        if "--json" in argv:
            print(json.dumps(m, indent=1))
            return 0
        held = [s for s in m["samples"] if s["running"] and abs(s["x"]) < 20]
        pulsing = len({round(s["ring"], 2) for s in m["samples"] if s["paused"]})
        print(f"check_marquee_live --hovered: {len(held)} of {len(m['samples'])} samples held at x≈0 "
              f"while running (the offscreen pointer at (0,0) hovers the Row); "
              f"the ring took {pulsing} distinct opacities while paused")
        return 0
    m = measure(run(variant=variant), run_hovered(variant), variant)
    if "--trace" in argv:
        print(f"variant {variant}: expected lit {m['expected']['lit']} ghost {m['expected']['ghost']} ground {m['expected']['ground']}")
        for l in m["log"]:
            print(f"widget {l}")
        for e in m["events"]:
            print(f"event  t={e['t']:6.0f}  {e['op']:8s} id={e['id']} shows {e['shows']!r}")
        for s in m["samples"]:
            print(f"sample t={s['t']:6.0f}  x={s['x']:7.1f} raw={s['raw']:7.1f} w={s['w']:6.1f}  running={s['running']!s:5s} "
                  f"paused={s['paused']!s:5s} ring={s['ring']:.2f} lit={s['lit']}  count={s['count']}  {s['text']!r}")
        for s in m["hovered"]["samples"]:
            print(f"hovered t={s['t']:6.0f}  x={s['x']:7.1f}  running={s['running']!s:5s} paused={s['paused']!s:5s} ring={s['ring']:.2f}  {s['text']!r}")
        return 0
    print(json.dumps(m, indent=1))
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    res = run()
    if res is None:
        print("  SKIP — no qml runner")
        print("check_marquee_live selftest: SKIP")
        return True
    m = measure(res, run_hovered())
    # ⚑ THE MEASUREMENT CAN SEE: every timeline step was applied and logged, the
    # board was sampled across the whole run, the samples carry the observables,
    # and the hovered run has paused samples for the pulse rule to range over.
    # Whether the traces SATISFY the invariant is policy/marquee_live.rego's ruling.
    chk("every timeline step became an event", [e["op"] for e in m["events"]], [s[1] for s in TIMELINE])
    last = m["samples"][-1]
    chk("the run ended with every event fired and the board drained",
        (m["events"][-1]["t"] <= last["t"], last["text"], last["running"]), (True, "", False))
    chk("a sample carries text, x, raw, w, running, paused, ring, count and the bound colours",
        sorted(m["samples"][0].keys()),
        ["count", "ghost", "ground", "lit", "paused", "raw", "ring", "running", "t", "text", "w", "x"])
    # ⚑ THE THEME CAN SEE (W35): run under another variant, the bound colours change
    amber = measure(run(variant="EL-Amber", end_ms=1500), None, "EL-Amber")
    chk("under EL-Amber the sampled lit is EL-Amber's fg", amber["samples"][-1]["lit"], amber["expected"]["lit"])
    chk("...and differs from EL-Openglo's", amber["samples"][-1]["lit"] != m["expected"]["lit"], True)
    chk("the hovered run has paused samples", any(s["paused"] for s in m["hovered"]["samples"]), True)
    chk("the stub reported its rows to the board (some sample saw text)", any(s["text"] for s in m["samples"]), True)
    chk("a runner-less host is withheld", measure(None)["runner"], False)
    print("check_marquee_live selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
