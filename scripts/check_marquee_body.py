#!/usr/bin/env python3
"""check_marquee_body.py — the marquee's body-markup parser, run headless on synthetic bodies.

⚑ WHY A HARNESS.  templates/marquee-body.js is JavaScript that qmllint parses
but never RUNS, and the marquee cannot be rendered headless (it imports
org.kde.notificationmanager). So this writes the SAME .js the package ships
into a tempdir beside a tiny QML that calls parseBody on fixed inputs and
prints JSON, runs it under Qt's `qml` on the offscreen platform, and compares.
The freedesktop spec's legal set — <b> <i> <u> <a href> <img alt> — plus
Plasma's <br> and entities are each a case; a tag that survives into the
text, a run whose span is wrong, or an entity left encoded is a failure.

    scripts/check_marquee_body.py            # exit 0 iff every case parses as stated
    scripts/check_marquee_body.py --cases    # print the cases and what the parser returned
    scripts/check_marquee_body.py --selftest

SKIP (printed, exit 0) when the qml runner is absent (a fact about the host).
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import qt_sandbox as QT  # noqa: E402

QML = QT.QML

# (body, expected text, expected runs as (start, end, flag) with flag in {bold, italic,
#  underline, link, color} or None for plain)
CASES = [
    ("hi", "hi", []),
    ("<b>hi</b>", "hi", [(0, 2, "bold")]),
    ("a <i>b</i> c", "a b c", [(2, 3, "italic")]),
    ("<u>x</u>", "x", [(0, 1, "underline")]),
    ('<a href="http://e.x/">link</a>', "link", [(0, 4, "link")]),
    ('<img src="/p.png" alt="pic"/> after', "[pic] after", []),
    ("one<br>two", "one two", []),
    ("Tom &amp; Jerry &lt;3", "Tom & Jerry <3", []),
    ("&#65;&#x42;", "AB", []),
    ("<strong>S</strong><em>E</em>", "SE", [(0, 1, "bold"), (1, 2, "italic")]),
    ('<font color="#ff0000">red</font>', "red", [(0, 3, "color")]),
    ('<span style="color: teal">t</span>', "t", [(0, 1, "color")]),
    ("unclosed <b", "unclosed <b", []),
    ("<unknown>k</unknown>", "k", []),
    # whitespace collapses INSIDE the parser so run offsets are exact
    ("  a \n\n <b>b</b>  c", "a b c", [(2, 3, "bold")]),
    # two links in one body: two link runs, each carrying its own href (W40)
    ('<a href="http://a/">A</a> and <a href="http://b/">B</a>', "A and B", [(0, 1, "link"), (6, 7, "link")]),
]

# joinItem: (app, summary, body) -> expected text, expected styled runs. The
# SUMMARY is plain — its <b> stays literal; the body's becomes a bold run (W45).
JOIN_CASES = [
    (("notify-send", "oh <b>hi</b>", ""), "notify-send: oh <b>hi</b>", []),
    (("notify-send", "oh", "<b>hi</b>"), "notify-send: oh — hi", [(18, 20, "bold")]),
    (("", "just a summary", ""), "just a summary", []),
    (("app", "", "<i>only body</i>"), "app: only body", [(5, 14, "italic")]),
    (("app", "s", "trailing <u>u</u>  "), "app: s — trailing u", [(18, 19, "underline")]),
]

# ⚑ THE TRAVERSAL INVARIANT, stepped. Each scenario is a list of boundaries;
# at each: arrivals are upserted, then ringNext runs against the live ids.
# Expected: the ring's ids at each boundary, and the queue's ids after.
RING_CASES = [
    ("arrive-and-expire-before-boundary still scrolls once",
     [dict(arrive=["n1"], live=[], max=12)], [(["n1"], [])]),
    ("an active item keeps cycling",
     [dict(arrive=["n1"], live=["n1"], max=12), dict(arrive=[], live=["n1"], max=12)],
     [(["n1"], ["n1"]), (["n1"], ["n1"])]),
    ("an expired item drops only after its rotation",
     [dict(arrive=["n1"], live=["n1"], max=12), dict(arrive=[], live=[], max=12),
      dict(arrive=[], live=[], max=12)],
     [(["n1"], ["n1"]), ([], []), ([], [])]),
    ("a mid-rotation arrival waits for the boundary, then leads",
     [dict(arrive=["n1"], live=["n1"], max=12), dict(arrive=["n2"], live=["n1", "n2"], max=12)],
     [(["n1"], ["n1"]), (["n2", "n1"], ["n2", "n1"])]),
    ("a replaced id shows the new text once more",
     [dict(arrive=["n1"], live=["n1"], max=12), dict(arrive=["n1"], live=["n1"], max=12)],
     [(["n1"], ["n1"]), (["n1"], ["n1"])]),
    ("the cap holds an unshown item back, still owed",
     [dict(arrive=["n1", "n2", "n3"], live=["n1", "n2", "n3"], max=2),
      dict(arrive=[], live=[], max=2)],
     [(["n1", "n2"], ["n1", "n2", "n3"]), (["n3"], [])]),
    # W46: a TRANSIENT item gets exactly one traversal — dropped after it even
    # while the model still holds it; a live non-transient beside it keeps cycling
    ("a transient item scrolls once and is not re-queued while live",
     [dict(arrive=["t1", "n1"], transient=["t1"], live=["t1", "n1"], max=12),
      dict(arrive=[], live=["t1", "n1"], max=12)],
     [(["t1", "n1"], ["n1"]), (["n1"], ["n1"])]),
    # W46: an item's actions join as " [Label]" runs after its text
    ("an item's actions are appended as runs",
     [dict(arrive=["n1"], actions={"n1": [["open", "Open"], ["dismiss", "Dismiss"]]}, live=["n1"], max=12,
           text="n1#1 [Open] [Dismiss]")],
     [(["n1"], ["n1"])]),
    # W46 jobs: three progress replaces (same text, new percentage) keep the item's
    # place and `shown` — the ring is unchanged, the history grows to three samples,
    # and the join carries a series run: text + " " + one placeholder (3 samples ≤ 6 cells)
    ("a job's progress replaces grow its history without re-owing a rotation",
     [dict(arrive=["j1"], progress={"j1": 10}, live=["j1"], max=12, text="j1#1 ░", series={"j1": [10]}),
      dict(arrive=["j1"], progress={"j1": 50}, live=["j1"], max=12, text="j1#1 ░", series={"j1": [10, 50]}),
      dict(arrive=["j1"], progress={"j1": 90}, live=["j1"], max=12, text="j1#1 ░", series={"j1": [10, 50, 90]})],
     [(["j1"], ["j1"]), (["j1"], ["j1"]), (["j1"], ["j1"])]),
]

# seriesToColumns (W48): (values, rows, min, max) -> expected column heights
SERIES_CASES = [
    ("a ramp fills the rows", ([0, 25, 50, 75, 100], 8, 0, 100), [0, 2, 4, 6, 8]),
    ("a flat series is a baseline, not nothing", ([5, 5, 5], 8, 5, 5), [1, 1, 1]),
    ("a spike clamps at the top", ([10, 500, 10], 8, 0, 100), [1, 8, 1]),
    ("an empty series is no columns", ([], 8, 0, 100), []),
    ("a value below the floor clamps at zero", ([-10, 50], 8, 0, 100), [0, 4]),
    ("a non-number is a zero column", (["x", 100], 8, 0, 100), [0, 8]),
]

# displayChar (W74, urgency is a letterform): (char, urgency) -> the character the
# board RASTERISES. low lowercase, normal and critical upper case; a mapping that is
# not one char to one char is refused (ß -> "SS" would shift every later index);
# anything else (no urgency, a digit, punctuation) is shown as sent.
DISPLAY_CASES = [
    ("low lowercases", ("A", 0), "a"),
    ("low keeps a lowercase", ("a", 0), "a"),
    ("normal uppercases", ("a", 1), "A"),
    ("critical uppercases", ("a", 2), "A"),
    ("Latin-1 uppercases", ("é", 1), "É"),
    ("Latin-1 lowercases", ("É", 0), "é"),
    ("ß has no one-char upper case: shown as sent", ("ß", 2), "ß"),
    ("a digit has no case", ("7", 0), "7"),
    ("punctuation has no case", ("[", 2), "["),
    ("no urgency: shown as sent", ("a", None), "a"),
]

# kernOffsets (W76, the closed loop on the pip mask): two glyphs, their pitch s and plain
# advance; the EXPECTED OUTCOME is named and the policy (M9) rules on it. H is 5 columns
# x 7 rows; s = 4 px, advance = 6 cells = 24 px (5 glyph columns + 1 gap).
_H = [0x7F, 0x08, 0x08, 0x08, 0x7F]
KERN_CASES = [
    ("regular pair keeps the plain advance", ([{"bytes": _H, "grow": 0}, {"bytes": _H, "grow": 0}], 7, 4, 24), "plain"),
    ("bold pair bleeds, then is pushed apart until a dark column separates it",
     ([{"bytes": _H, "grow": 2}, {"bytes": _H, "grow": 2}], 7, 4, 24), "separated"),
    ("a pair that can never separate stops at the cap, not forever",
     ([{"bytes": _H, "grow": 400}, {"bytes": _H, "grow": 400}], 7, 4, 24), "capped"),
]

HARNESS = """import QtQuick
import "marquee-body.js" as Body
QtObject {
    Component.onCompleted: {
        var bodies = %s, joins = %s, rings = %s, series = %s, display = %s, kern = %s;
        var out = { parse: [], join: [], ring: [], series: [], display: [], kern: [] };
        for (var d = 0; d < display.length; d++) out.display.push(Body.displayChar(display[d][0], display[d][1]));
        for (d = 0; d < kern.length; d++) {
            var g = kern[d][0], off = Body.kernOffsets(g, kern[d][1], kern[d][2], kern[d][3]);
            var inkA = Body.glyphInk(g[0].bytes, kern[d][1], kern[d][2], g[0].grow, off[0]);
            var inkB = Body.glyphInk(g[1].bytes, kern[d][1], kern[d][2], g[1].grow, off[1]);
            out.kern.push({ offsets: off, bleeds_after: Body.pairBleeds(inkA, inkB, kern[d][1], kern[d][2]),
                            bleeds_at_plain: Body.pairBleeds(inkA, Body.glyphInk(g[1].bytes, kern[d][1], kern[d][2], g[1].grow, off[0] + kern[d][3]), kern[d][1], kern[d][2]),
                            cap: Body.KERN_CAP });
        }
        for (var i = 0; i < bodies.length; i++) out.parse.push(Body.parseBody(bodies[i]));
        for (i = 0; i < joins.length; i++) out.join.push(Body.joinItem(joins[i][0], joins[i][1], joins[i][2]));
        for (i = 0; i < series.length; i++) out.series.push(Body.seriesToColumns(series[i][0], series[i][1], series[i][2], series[i][3]));
        for (i = 0; i < rings.length; i++) {
            var queue = [], trace = [], serial = 0;
            for (var s = 0; s < rings[i].length; s++) {
                var step = rings[i][s];
                for (var a = 0; a < step.arrive.length; a++) {
                    var id = step.arrive[a];
                    var tr = (step.transient || []).indexOf(id) >= 0;
                    var acts = ((step.actions || {})[id] || []).map(function (p) { return { id: p[0], label: p[1] }; });
                    var prog = (step.progress || {})[id];
                    // a job's progress replace keeps its TEXT (serial 1) and brings a percentage
                    var txt = prog !== undefined ? id + "#1" : id + "#" + (++serial);
                    queue = Body.queueUpsert(queue, { id: id, text: txt, runs: [], transient: tr, actions: acts,
                                                      percentage: prog === undefined ? null : prog, jobState: prog === undefined ? null : 1 });
                }
                var r = Body.ringNext(queue, step.live, step.max);
                queue = r.queue;
                var ids = [], qids = [], series = {};
                for (var k = 0; k < r.ring.length; k++) ids.push(r.ring[k].id);
                for (k = 0; k < queue.length; k++) qids.push(queue[k].id);
                var joined = Body.ringJoin(r.ring, " | ");
                for (k = 0; k < joined.runs.length; k++) if (joined.runs[k].series) series[joined.runs[k].item] = joined.runs[k].series;
                trace.push({ ring: ids, queue: qids, text: joined.text, series: series });
            }
            out.ring.push(trace);
        }
        console.log("RESULT " + JSON.stringify(out));
        Qt.quit();
    }
}
"""


def run(bodies=None):
    """{parse: [...], join: [...], ring: [...]} over the cases, or None when the runner is absent."""
    if not os.path.isfile(QML):
        return None
    bodies = [c[0] for c in CASES] if bodies is None else bodies
    src = open(os.path.join(ROOT, "templates", "marquee-body.js"), encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "marquee-body.js"), "w", encoding="utf-8").write(src)
        h = os.path.join(td, "harness.qml")
        open(h, "w", encoding="utf-8").write(HARNESS % (
            json.dumps(bodies), json.dumps([list(c[0]) for c in JOIN_CASES]),
            json.dumps([c[1] for c in RING_CASES]), json.dumps([list(c[1]) for c in SERIES_CASES]),
            json.dumps([list(c[1]) for c in DISPLAY_CASES]),
            json.dumps([list(c[1]) for c in KERN_CASES])))
        r = QT.run([QML, h], capture_output=True, text=True, timeout=60)
    for line in (r.stdout + r.stderr).splitlines():
        if "RESULT " in line:
            return json.loads(line.split("RESULT ", 1)[1])
    raise RuntimeError(f"no RESULT from the qml harness (rc={r.returncode}): {(r.stderr or r.stdout)[:300]}")


GLYPH_HARNESS = """import QtQuick
import "marquee-body.js" as Body
QtObject {
    Component.onCompleted: {
        var font = %s, chars = %s, out = { flash_hz: Body.FLASH_HZ, flash_ms: Body.FLASH_MS, chars: [] };
        for (var i = 0; i < chars.length; i++) {
            var row = { ch: chars[i], forms: [] };
            for (var u = 0; u < 3; u++)
                row.forms.push({ urgency: u, shown: Body.displayChar(chars[i], u), key: Body.glyphKey(font, chars[i], u) });
            out.chars.push(row);
        }
        console.log("RESULT " + JSON.stringify(out));
        Qt.quit();
    }
}
"""


def glyph_census(font, chars):
    """W74: per character, per urgency, what the SHIPPED marquee-body.js rasterises —
    the displayed form (displayChar) and the registry key the lookup lands on
    (glyphKey: the displayed form, else the character as sent, else '?') — plus the
    declared flash rate. Run under Qt's qml like run(); None when the runner is absent."""
    if not os.path.isfile(QML):
        return None
    src = open(os.path.join(ROOT, "templates", "marquee-body.js"), encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "marquee-body.js"), "w", encoding="utf-8").write(src)
        h = os.path.join(td, "harness.qml")
        open(h, "w", encoding="utf-8").write(GLYPH_HARNESS % (json.dumps(font), json.dumps(list(chars))))
        r = QT.run([QML, h], capture_output=True, text=True, timeout=60)
    for line in (r.stdout + r.stderr).splitlines():
        if "RESULT " in line:
            return json.loads(line.split("RESULT ", 1)[1])
    raise RuntimeError(f"no RESULT from the glyph harness (rc={r.returncode}): {(r.stderr or r.stdout)[:300]}")


def _styled(got):
    return [(r["start"], r["end"], _flag(r)) for r in got["runs"] if _flag(r)]


def join_problems(results):
    bad = []
    for (args, text, runs), got in zip(JOIN_CASES, results):
        if got["text"] != text:
            bad.append(f"join{args!r}: text {got['text']!r}, expected {text!r}")
        if _styled(got) != runs:
            bad.append(f"join{args!r}: styled runs {_styled(got)}, expected {runs}")
    return bad


def ring_problems(results):
    bad = []
    for (label, _steps, want), trace in zip(RING_CASES, results):
        got = [(t["ring"], t["queue"]) for t in trace]
        if got != want:
            bad.append(f"ring {label!r}: {got}, expected {want}")
    # the replaced id must carry the NEW text on its second rotation
    rep = results[4]
    if not (rep[0]["text"] == "n1#1" and rep[1]["text"] == "n1#2"):
        bad.append(f"ring replace: texts {[t['text'] for t in rep]}, expected n1#1 then n1#2")
    # a step that states its joined text (W46 actions) or its series (W46 jobs) must produce it
    for (label, steps, _want), trace in zip(RING_CASES, results):
        for i, step in enumerate(steps):
            if "text" in step and trace[i]["text"] != step["text"]:
                bad.append(f"ring {label!r}: boundary {i} text {trace[i]['text']!r}, expected {step['text']!r}")
            if "series" in step and trace[i].get("series") != step["series"]:
                bad.append(f"ring {label!r}: boundary {i} series {trace[i].get('series')!r}, expected {step['series']!r}")
    return bad


def series_problems(results):
    bad = []
    for (label, args, want), got in zip(SERIES_CASES, results):
        if got != want:
            bad.append(f"series {label!r}: {got}, expected {want}")
    if len(results) != len(SERIES_CASES):
        bad.append(f"series: {len(results)} of {len(SERIES_CASES)} cases returned")
    return bad


def display_problems(results):
    bad = [f"display {label!r}: {args!r} -> {got!r}, expected {want!r}"
           for (label, args, want), got in zip(DISPLAY_CASES, results) if got != want]
    if len(results) != len(DISPLAY_CASES):
        bad.append(f"display: {len(results)} of {len(DISPLAY_CASES)} cases returned")
    return bad


def all_problems(res):
    return (problems(res["parse"]) + join_problems(res["join"]) + ring_problems(res["ring"])
            + series_problems(res.get("series", [])) + display_problems(res.get("display", [])))


N_CASES = len(CASES) + len(JOIN_CASES) + len(RING_CASES) + len(SERIES_CASES) + len(DISPLAY_CASES)


def measure(res):
    """The MEASUREMENT, as policy/marquee_body.rego reads it (W50): every case
    with what was EXPECTED beside what the shipped parser RETURNED, and every ring
    scenario with its steps beside the trace. The comparison is the policy's; the
    runner's absence is a `withheld` fact, not a pass."""
    if res is None:
        return {"runner": False, "parse": [], "join": [], "ring": [], "series": [], "display": [], "kern": []}
    out = {"runner": True, "parse": [], "join": [], "ring": [], "series": [], "display": [], "kern": []}
    for (label, args, expect), got in zip(KERN_CASES, res.get("kern", [])):
        out["kern"].append({"label": label, "expect": expect, "advance": args[3],
                            "offsets": got.get("offsets"), "bleeds_after": got.get("bleeds_after"),
                            "bleeds_at_plain": got.get("bleeds_at_plain"), "cap": got.get("cap")})
    for (label, args, want), got in zip(SERIES_CASES, res.get("series", [])):
        out["series"].append({"label": label, "args": list(args), "expected": want, "columns": got})
    for (label, args, want), got in zip(DISPLAY_CASES, res.get("display", [])):
        out["display"].append({"label": label, "args": list(args), "expected": want, "shown": got})
    for (body, text, runs), got in zip(CASES, res["parse"]):
        out["parse"].append({"body": body, "expected_text": text, "text": got["text"],
                             "expected_runs": [list(r) for r in runs], "runs": [list(r) for r in _styled(got)]})
    for (args, text, runs), got in zip(JOIN_CASES, res["join"]):
        out["join"].append({"args": list(args), "expected_text": text, "text": got["text"],
                            "expected_runs": [list(r) for r in runs], "runs": [list(r) for r in _styled(got)]})
    for (label, steps, want), trace in zip(RING_CASES, res["ring"]):
        out["ring"].append({"label": label, "steps": steps,
                            "expected": [{"ring": r, "queue": q} for r, q in want],
                            "trace": trace})
    return out


def _flag(run_):
    if run_["bold"]:
        return "bold"
    if run_["italic"]:
        return "italic"
    if run_["underline"]:
        return "underline"
    if run_["link"]:
        return "link"
    if run_["color"]:
        return "color"
    return None


def problems(results):
    bad = []
    for (body, text, runs), got in zip(CASES, results):
        if got["text"] != text:
            bad.append(f"{body!r}: text {got['text']!r}, expected {text!r}")
        styled = [(r["start"], r["end"], _flag(r)) for r in got["runs"] if _flag(r)]
        if styled != runs:
            bad.append(f"{body!r}: styled runs {styled}, expected {runs}")
        if "<" in got["text"] and "<" not in text:
            bad.append(f"{body!r}: a tag survived into the text")
    return bad


def main(argv):
    known = {"--cases", "--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_marquee_body: unknown flag {a!r}", file=sys.stderr)
            return 2
    res = run()
    if "--json" in argv:
        print(json.dumps(measure(res), indent=1))
        return 0
    if res is None:
        print(f"check_marquee_body: SKIP — {QML} not present; 0 of {N_CASES} cases run", file=sys.stderr)
        return 0
    if "--cases" in argv:
        for (body, _t, _r), got in zip(CASES, res["parse"]):
            print(f"{body!r:40s} -> {got['text']!r}  runs {[(r['start'], r['end'], _flag(r)) for r in got['runs']]}")
        for (args, _t, _r), got in zip(JOIN_CASES, res["join"]):
            print(f"join{args!r:40} -> {got['text']!r}  runs {_styled(got)}")
        for (label, _s, _w), trace in zip(RING_CASES, res["ring"]):
            print(f"ring {label}: {[(t['ring'], t['queue']) for t in trace]}")
        for (label, args, _w), got in zip(DISPLAY_CASES, res.get("display", [])):
            print(f"display {label}: displayChar{args!r} -> {got!r}")
        return 0
    bad = all_problems(res)
    if bad:
        print(f"check_marquee_body: REFUSED — {len(bad)} of {N_CASES} cases disagree:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print(f"check_marquee_body: {N_CASES} of {N_CASES} cases hold — {len(CASES)} body-markup, "
          f"{len(JOIN_CASES)} joinItem (summary plain, body parsed), {len(RING_CASES)} ring scenarios "
          f"(every item scrolls once; an expired item drops after its rotation; a replace re-shows), "
          f"{len(SERIES_CASES)} series (a sparkline's column heights, W48), "
          f"{len(DISPLAY_CASES)} display (urgency's letterform, W74)")
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
        print("check_marquee_body selftest: SKIP")
        return True
    results = res["parse"]
    chk("every case returns", (len(results), len(res["join"]), len(res["ring"])),
        (len(CASES), len(JOIN_CASES), len(RING_CASES)))
    # ⚑ THE MEASUREMENT CAN SEE (W50). Whether a case's result is a DEFECT is
    # policy/marquee_body.rego's ruling (M1 parse, M2 join, M3 trace, M4 every
    # arrival rung), with the refuse/admit pairs in policy/marquee_body_test.rego
    # under `opa test`. Here: the measurement carries expected beside got for
    # every case, and a runner-less host reports withheld, not a pass.
    m = measure(res)
    chk("every parse case carries expected and got", all("expected_text" in c and "text" in c for c in m["parse"]), True)
    chk("every ring scenario carries steps, expected and trace",
        all(len(s["trace"]) == len(s["expected"]) and s["steps"] for s in m["ring"]), True)
    chk("a runner-less host is withheld", measure(None)["runner"], False)
    chk("every display (letterform) case carries expected and shown",
        len([c for c in m["display"] if "expected" in c and "shown" in c]), len(DISPLAY_CASES))
    g = glyph_census({"a": [1], "A": [2], "?": [3]}, ["a", "b"])
    chk("the glyph census sees a lowercase glyph used, and a missing one land on '?'",
        [[f["key"] for f in row["forms"]] for row in g["chars"]], [["a", "A", "A"], ["?", "?", "?"]])
    two = results[-1]["runs"]
    links = [r["link"] for r in two if r["link"]]
    chk("two links carry two distinct hrefs", links, ["http://a/", "http://b/"])
    # the shipped file IS the tested file
    import make_notify_marquee as MM
    chk("the package ships the parser this ran",
        MM.body_parser() == open(os.path.join(ROOT, "templates", "marquee-body.js")).read(), True)
    print("check_marquee_body selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.path.insert(0, ROOT)
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
