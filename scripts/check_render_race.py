#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_render_race.py — the render gate's grab race, FORCED (W781).

⚑ WHY. qml_sanity.render_nonempty ran the single-still harness, which grabs a fixed 1200 ms after
the WINDOW opens and not from the subject's LOAD (scripts/render_qml.py HARNESS). Under load the
subject loads after the grab and the picture is blank: `RENDER-GATE failed: clock: 0 lit px`, 4 of 17
stagings at once (W780). Counting runs under load is a measurement of that race; this FORCES it.
The harness's Loader is held inactive for HOLD_MS, past the 1200 ms grab, with a Timer that then
activates it, so the interleaving is the same every run and does not depend on the host's load.

    scripts/check_render_race.py --json   # what the three cases measured, for policy/render_race.rego
    scripts/check_render_race.py --selftest

Three cases, each rendered REPEATS times: `control` (the settled harness with a LONG settle and
no hold: the instrument can see lit pixels), `held-default` (the default harness, the load held:
the grab lands before it, so a blank picture is the EXPECTED result and the forcing worked) and
`held-settled` (the same long-settle harness, the same hold: the grab is timed from the load, so
it must be lit). The policy requires the third and the first, and requires the second to stay
blank, so the witness cannot go quiet by the default harness being fixed or the hold ceasing to
hold. The two LIT cases use a settle of SETTLE_MS (three times the measured 4000 ms) because the
first version put the control on the default harness, and under the gate's load that control
read blank: @RENDER-RACE failed in the gate and passed on replay, in two stages. The BLANK case
needs no margin: its Timers start together and fire in interval order, load or none.

⚑ WEAKNESS, STATED. It forces the LOAD-LATE interleaving of one surface (the clock). It does not
force the other way a grab can miss (the window not yet exposed, so grabToImage never calls back),
which is the suspected shape of the 13 wall kills at 17-way and is W782's to show.
"""

import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

HOLD_MS = 2500  # past the default harness's 1200 ms grab
MIN_LIT = 20  # qml_sanity.render_nonempty's floor
REPEATS = 3
VARIANT = "EL-Openglo"
SURFACE = "clock"
SOURCE = 'source: "subject.qml"'
LOADER = "Loader { id: subject;"


# three times the settled harness's measured 4000 ms, for the cases that must read LIT
SETTLE_MS = 12000
SETTLE = "id: settle; interval: 4000"


def settle(harness, ms=SETTLE_MS):
    """`harness` (the settled one) grabbing `ms` ms after the subject loads instead of its measured 4000.

    The cases that must read LIT run under the gate's load, where the clock can need longer than
    4000 ms to draw (@RENDER-RACE failed in the gate and passed on replay, twice, with the
    control on the default harness). A longer settle is a margin, not a fix: the cases that must
    read BLANK do not depend on it."""
    if SETTLE not in harness:
        raise ValueError("the harness has no settle Timer to lengthen")
    return harness.replace(SETTLE, f"id: settle; interval: {ms}")


def hold(harness, ms=HOLD_MS):
    """`harness` with the subject Loader inactive until a Timer activates it `ms` ms after the window."""
    if SOURCE not in harness or LOADER not in harness:
        raise ValueError("the harness has no subject Loader to hold")
    timer = f"Timer {{ interval: {ms}; running: true; onTriggered: subject.active = true }}\n    "
    return harness.replace(SOURCE, SOURCE + "; active: false").replace(
        LOADER, timer + LOADER
    )


def lit_pixels(harness):
    """(lit pixel count, None) of the clock rendered under `harness`; (None, why) when it could not be."""
    import render_qml as RQ

    if not os.path.exists(RQ.QML):
        return None, f"{RQ.QML} is not installed"
    if os.environ.get("SANDBOX_ON") == "1":
        return None, "a build sandbox forbids the GPU device the qml runner opens"
    with tempfile.TemporaryDirectory() as td:
        out = os.path.join(td, "r.png")
        rc, err = RQ.render(SURFACE, VARIANT, 400, 48, out, harness=harness)
        if not os.path.exists(out):
            return None, f"the qml runner produced no image (rc={rc}): {err[-160:]}"
        return RQ.pixels(out, VARIANT)["lit"], None


def measure(repeats=REPEATS):
    """The facts: every render's lit-pixel count by case, and what could not be rendered."""
    import render_qml as RQ

    long_settle = settle(RQ.HARNESS_SETTLED)
    plain = {
        "control": long_settle,
        "held-default": hold(RQ.HARNESS),
        "held-settled": hold(long_settle),
    }
    cases, withheld = [], []
    for name, harness in plain.items():
        for _ in range(repeats):
            lit, why = lit_pixels(harness)
            if lit is None:
                withheld.append(f"{name}: {why}")
            else:
                cases.append({"name": name, "lit": lit})
    return {
        "min_lit": MIN_LIT,
        "hold_ms": HOLD_MS,
        "repeats": repeats,
        "cases": cases,
        "withheld": withheld,
    }


def main(argv):
    args = argv[1:]
    for a in args:
        if a not in ("--json", "--selftest"):
            print(f"check_render_race: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in args:
        return 0 if _selftest() else 1
    if "--json" not in args:
        print("check_render_race: needs --json or --selftest", file=sys.stderr)
        return 2
    print(json.dumps(measure(), indent=2))
    return 0


def _selftest():
    import render_qml as RQ

    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    for label, base in (("default", RQ.HARNESS), ("settled", RQ.HARNESS_SETTLED)):
        held = hold(base)
        chk(
            f"the {label} harness is held: one Timer, the Loader inactive",
            (held.count("subject.active = true"), held.count("active: false")),
            (1, 1),
        )
    try:
        hold("Window { }")
        refused = False
    except ValueError:
        refused = True
    chk("a harness with no subject Loader is refused", refused, True)
    chk(
        "the settle is lengthened in the settled harness and nowhere else",
        (
            settle(RQ.HARNESS_SETTLED).count(f"interval: {SETTLE_MS}"),
            SETTLE in settle(RQ.HARNESS_SETTLED),
        ),
        (1, False),
    )
    try:
        settle(RQ.HARNESS)
        refused = False
    except ValueError:
        refused = True
    chk("the default harness has no settle Timer to lengthen: refused", refused, True)
    m = measure(repeats=1)
    by = {c["name"]: c["lit"] for c in m["cases"]}
    if m["withheld"]:
        print(f"  SKIP the forced cases: {m['withheld'][0]}")
    else:
        chk(
            "the control sees lit pixels (the instrument can see)",
            by["control"] >= MIN_LIT,
            True,
        )
        chk(
            "the default harness with the load held reads blank (the race is forced)",
            by["held-default"] < MIN_LIT,
            True,
        )
        chk(
            "the settled harness with the same hold is lit",
            by["held-settled"] >= MIN_LIT,
            True,
        )
    print("check_render_race selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    sys.exit(main(sys.argv))
