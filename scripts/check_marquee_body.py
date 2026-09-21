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
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
QML = "/usr/lib64/qt6/bin/qml"

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

HARNESS = """import QtQuick
import "marquee-body.js" as Body
QtObject {
    Component.onCompleted: {
        var inputs = %s;
        var out = [];
        for (var i = 0; i < inputs.length; i++) out.push(Body.parseBody(inputs[i]));
        console.log("RESULT " + JSON.stringify(out));
        Qt.quit();
    }
}
"""


def run(bodies=None):
    """[parseBody results] for the bodies, or None when the runner is absent."""
    if not os.path.isfile(QML):
        return None
    bodies = [c[0] for c in CASES] if bodies is None else bodies
    src = open(os.path.join(ROOT, "templates", "marquee-body.js"), encoding="utf-8").read()
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, "marquee-body.js"), "w", encoding="utf-8").write(src)
        h = os.path.join(td, "harness.qml")
        open(h, "w", encoding="utf-8").write(HARNESS % json.dumps(bodies))
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        r = subprocess.run([QML, h], capture_output=True, text=True, env=env, timeout=60)
    for line in (r.stdout + r.stderr).splitlines():
        if "RESULT " in line:
            return json.loads(line.split("RESULT ", 1)[1])
    raise RuntimeError(f"no RESULT from the qml harness (rc={r.returncode}): {(r.stderr or r.stdout)[:300]}")


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
    known = {"--cases", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_marquee_body: unknown flag {a!r}", file=sys.stderr)
            return 2
    results = run()
    if results is None:
        print(f"check_marquee_body: SKIP — {QML} not present; 0 of {len(CASES)} cases run", file=sys.stderr)
        return 0
    if "--cases" in argv:
        for (body, _t, _r), got in zip(CASES, results):
            print(f"{body!r:40s} -> {got['text']!r}  runs {[(r['start'], r['end'], _flag(r)) for r in got['runs']]}")
        return 0
    bad = problems(results)
    if bad:
        print(f"check_marquee_body: REFUSED — {len(bad)} of {len(CASES)} cases disagree:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print(f"check_marquee_body: {len(CASES)} of {len(CASES)} body-markup cases parse as stated "
          f"(spec tags b i u a img, br, entities; unknown tags dropped; an unclosed tag kept)")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    results = run()
    if results is None:
        print("  SKIP — no qml runner")
        print("check_marquee_body selftest: SKIP")
        return True
    chk("every case returns", len(results), len(CASES))
    chk("the real cases agree", problems(results), [])
    two = results[-1]["runs"]
    links = [r["link"] for r in two if r["link"]]
    chk("two links carry two distinct hrefs", links, ["http://a/", "http://b/"])
    # ⚑ THE COMPARISON MUST BE ABLE TO FAIL: a wrong text and a wrong run are seen
    wrong = json.loads(json.dumps(results))
    wrong[1]["text"] = "<b>hi</b>"
    chk("a tag surviving into the text is seen", any("survived" in b or "text" in b for b in problems(wrong)), True)
    wrong = json.loads(json.dumps(results))
    wrong[1]["runs"][0]["bold"] = False
    chk("a lost bold run is seen", any("runs" in b for b in problems(wrong)), True)
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
