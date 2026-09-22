#!/usr/bin/env python3
"""check_qml_lint.py — every EMITTED QML document lints, and no animation binds `running`.

⚑ WHY (operator, live 2026-09-22: "Current git head doesn't appear to respond to
notifications at all" — then "Sounds like we need qmllint in our precommit
gate"). qmllint ran over ONE surface (the switcher, via check_taskswitch) and
over nothing else; the marquee, the clock, the live wallpaper and the shipped
components were never linted at commit time. This lints the population: each
emitter's rendered document at one variant (the holes are filled the same way
for every variant, so one is the population for the markup around them).

⚑ WEAKNESS, STATED. qmllint sees syntax and types; it does NOT see the defect
that prompted this gate. The marquee bound `running: marquee.visible` on a
finite NumberAnimation, and a finite animation ASSIGNS running=false when it
ends — which discards the binding — so after the ring first drained the Row
became visible again and nothing ever ran. That is a semantic rule Qt does not
lint, so this check carries it itself: an animation with `loops: 1` (or any
finite count) must not bind `running:` — it must be started. The rule reads
the emitted document's animation blocks, not the QML type graph, so it is a
brace-matched scan of `NumberAnimation { … }` and its siblings; a `running:`
inside a NESTED block of the animation is out of its reach (none exist today).

    scripts/check_qml_lint.py            # exit 0 iff every document lints and obeys the rule
    scripts/check_qml_lint.py --list     # the population and each verdict
    scripts/check_qml_lint.py --selftest

SKIP (printed, counted) when qmllint is absent — qml_sanity says so per document;
the `running` rule needs no host tool and always runs.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# (module, accessor, argsrc, label) — argsrc as check_template_parity._value reads it
DOCS = (
    ("make_segment_display", "segment_char_component", None, "SegmentChar.qml"),
    ("make_clock", "CONFIG_QML", None, "clock-config.qml"),
    ("make_clock", "main_qml", None, "clock-main.qml"),   # one package since W35
    ("make_wallpaper_live", "main_qml", None, "live-wallpaper-main.qml"),   # one package since W35
    ("make_notify_marquee", "main_qml", ("PARITY_FONT",), "marquee-main.qml"),   # one package since W35
    ("make_notify_marquee", "config_qml", None, "marquee-config.qml"),
    ("make_notify_marquee", "matrix_char_component", None, "MatrixChar.qml"),
    ("make_notify_marquee", "matrix_field_component", None, "MatrixField.qml"),
    ("make_notify_marquee", "aperture_field_component", None, "ApertureField.qml"),   # W54
    ("make_taskswitch", "main_qml", None, "taskswitch-main.qml"),   # one package since W35
)

ANIMATIONS = ("NumberAnimation", "PropertyAnimation", "ColorAnimation", "RotationAnimation",
              "SequentialAnimation", "ParallelAnimation", "PauseAnimation")


def _blocks(qml, names):
    """[(name, body)] for every top-level `Name {…}` block of one of `names`, brace-matched."""
    out = []
    for m in re.finditer(r"\b(" + "|".join(names) + r")\s*\{", qml):
        depth, i = 1, m.end()
        while i < len(qml) and depth:
            depth += {"{": 1, "}": -1}.get(qml[i], 0)
            i += 1
        out.append((m.group(1), qml[m.end():i - 1]))
    return out


def bound_running(qml):
    """[(animation, loops)] — finite animations whose `running:` is a BINDING (an expression,
    not a literal true/false). A finite run ends by assigning running=false, which drops
    the binding: the animation then never restarts from the property it was bound to."""
    bad = []
    for name, body in _blocks(qml, ANIMATIONS):
        # only this block's own bindings: strip nested blocks first
        own = re.sub(r"\{[^{}]*\}", "", body)
        loops = re.search(r"(?m)(?:^|;)\s*loops\s*:\s*([^\n;]+)", own)
        running = re.search(r"(?m)(?:^|;)\s*running\s*:\s*([^\n;]+)", own)
        infinite = loops is not None and "Infinite" in loops.group(1)
        if running and not infinite and running.group(1).strip() not in ("true", "false"):
            bad.append((name, loops.group(1).strip() if loops else "1"))
    return bad


def documents():
    """[(label, text)] rendered, or (label, None) for a pair this host cannot evaluate."""
    import check_template_parity as CTP
    out = []
    for module, accessor, argsrc, label in DOCS:
        try:
            out.append((label, CTP._value(module, accessor, argsrc)))
        except CTP._Skip:
            out.append((label, None))
    return out


def problems(docs):
    """[(label, [messages])] — lint errors plus the running rule; SKIP for absent docs."""
    import qml_sanity as QS
    out = []
    for label, text in docs:
        if text is None:
            out.append((label, ["SKIP"]))
            continue
        msgs = list(QS.check_qml(text, label))
        for name, loops in bound_running(text):
            msgs.append(f"{label}: {name} with loops {loops} BINDS running: — a finite run "
                        f"overwrites the binding when it ends; start() it instead")
        out.append((label, msgs))
    return out


def measure(docs):
    """The MEASUREMENT, as policy/qml_lint.rego reads it (W50): per document, the
    lint diagnostics qml_sanity kept and the finite animations that bind running;
    a document this host cannot render is `withheld` with its reason. No verdict
    lives here — the requirement is the rego rule, tested by opa test."""
    import qml_sanity as QS
    out = {"documents": [], "qmllint": bool(QS._qmllint())}
    for label, text in docs:
        if text is None:
            out["documents"].append({"id": label, "withheld": "a pinned host file is absent"})
            continue
        out["documents"].append({
            "id": label,
            "lint": list(QS.check_qml(text, label)) if out["qmllint"] else [],
            "bound_running": [{"animation": n, "loops": l} for n, l in bound_running(text)],
        })
    return out


def main(argv):
    known = {"--list", "--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_qml_lint: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(documents()), indent=1))
        return 0
    res = problems(documents())
    skipped = [l for l, m in res if m == ["SKIP"]]
    bad = [(l, m) for l, m in res if m and m != ["SKIP"]]
    if "--list" in argv:
        for l, m in res:
            print(f"{l:28s} {'SKIP' if m == ['SKIP'] else ('ok' if not m else 'REFUSED')}")
            for x in (m if m != ["SKIP"] else []):
                print(f"    {x}")
        return 0
    if not res:
        print("check_qml_lint: REFUSED — empty population", file=sys.stderr)
        return 1
    if bad:
        print(f"check_qml_lint: REFUSED — {len(bad)} of {len(res)} documents:", file=sys.stderr)
        for l, m in bad:
            for x in m:
                print(f"    {x}", file=sys.stderr)
        return 1
    print(f"check_qml_lint: {len(res) - len(skipped)} of {len(res)} emitted QML documents lint "
          f"and bind no finite animation's `running` ({len(skipped)} SKIP)")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    # ⚑ THE RULE MUST SEE THE DEFECT THAT PROMPTED IT — the marquee's binding, verbatim
    bad = "Row { NumberAnimation { id: r; loops: 1; running: marquee.visible\n onFinished: {} } }"
    chk("a bound running on a finite animation is seen", bound_running(bad), [("NumberAnimation", "1")])
    chk("an infinite animation may bind running",
        bound_running("NumberAnimation { loops: Animation.Infinite\n running: x.visible }"), [])
    chk("a literal running is not a binding",
        bound_running("NumberAnimation { loops: 1\n running: true }"), [])
    chk("a nested block's running is charged to the nested block, not the outer",
        bound_running("SequentialAnimation { loops: 3\n NumberAnimation { running: a.b } }"),
        [("NumberAnimation", "1")])
    chk("an outer block does not inherit a nested running",
        bound_running("SequentialAnimation { loops: 3\n PauseAnimation { duration: 1 } }"), [])
    docs = documents()
    chk("the population is the declared documents", len(docs), len(DOCS))
    # ⚑ THE MEASUREMENT CAN SEE (W50). Whether what it sees is a DEFECT is
    # policy/qml_lint.rego's ruling, with its refuse/admit pairs in
    # policy/qml_lint_test.rego under `opa test` — not re-argued here.
    m = measure([("bad.qml", "NumberAnimation { loops: 1; running: a.b }"), ("skip.qml", None)])
    chk("the measurement reports a bound running as a fact", m["documents"][0]["bound_running"],
        [{"animation": "NumberAnimation", "loops": "1"}])
    chk("the measurement reports an unrenderable document as withheld", "withheld" in m["documents"][1], True)
    import qml_sanity as QS
    if QS._qmllint():
        broken = measure([("broken.qml", 'import QtQuick\nItem { color: ""#000" }')])
        chk("the measurement reports a syntax error as a fact", bool(broken["documents"][0]["lint"]), True)
    else:
        print("  SKIP qmllint absent — the syntax arm did not run")
    print("check_qml_lint selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
