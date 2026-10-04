#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_config_reach.py — does every setting of a mount reach the pixels?

⚑ WHY (W264, operator 2026-10-03: "does 'lit stroke weight' even do anything?").
check_config_page proves each kcfg entry declares a value and a default and that a mount
names its key; nothing proved that moving the setting CHANGES WHAT IS DRAWN. Three sliders
of the clock were dead at panel size (the lit weight, the unlit weight, the unlit
opacity had no control at all) and every gate was green.

This renders each mount (render_qml, frozen instant, so a render is a function of its
inputs) with each kcfg key at the low and at the high end of its control, every other key
at its default, and records whether the two PNGs differ. `--json` is the MEASUREMENT;
policy/config_reach.rego decides: a key whose two renders are identical is a dead
setting unless it is declared INERT here with the reason it cannot show in one still.

MOUNTS TODAY: the clock and the live wallpaper (W267). The marquee acts over time and
needs a sampled run per key end (check_marquee_live): its keys are not measured here yet.

    scripts/check_config_reach.py            # the verdict, as opa_gate config_reach decides it
    scripts/check_config_reach.py --json     # the measurement
    scripts/check_config_reach.py --selftest

⚑ WEAKNESSES, STATED. (1) ONE still per mount at one size under one variant, so a key
that only acts at another size or over time is read as dead: it must be declared INERT
with its reason, never silently passed. (2) The two ends are the control's ends: a
setting that acts only between them (a non-monotone one) is seen as alive, and a
setting alive between but identical at both ends is read as dead. (3) Byte equality of
the PNG: any visible change, including a one-pixel antialiasing difference, counts as
reaching; whether the change is LEGIBLE is not measured here. (4) SKIPPED (counted,
printed, `withheld`) where the qml runner is absent: a fact about the machine.
"""

import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

VARIANT = "EL-Openglo"
# mount -> (the render_qml surface, the still's size)
SURFACES = {"clock": ("clock", (160, 48)), "wallpaper": ("live-wallpaper", (320, 180))}

# (mount, key) that cannot show in ONE still, with the reason; a declaration is data the
# policy can read, so an exemption is visible rather than a quiet `continue`
_BLINK = "the colon toggles per tick and one still holds it lit either way"
INERT = {
    ("clock", "blinkColon"): _BLINK,
    ("wallpaper", "blinkColon"): _BLINK,
}


def ends(entries, holes, mount="clock"):
    """[(key, type, low, high)] for every kcfg key of `mount`: a Bool's two values, a
    Double's control ends (display rows) or its default and its double + 1 (a row with
    no control)."""
    import display_params as DP

    out = []
    seen = set()
    for param, e in DP.exposed(mount):
        seen.add(e.spelling)
        if param.type == "Bool":
            out.append((e.spelling, "Bool", False, True))
        else:
            lo, hi, _step = (float(DP._fill(x, holes)) for x in e.control)
            out.append((e.spelling, "Double", lo, hi))
    for key, default in entries.items():
        if key in seen:
            continue
        if isinstance(default, bool):
            out.append((key, "Bool", False, True))
        else:
            out.append((key, "Double", float(default), float(default) * 2 + 1))
    return out


def differs(a, b):
    """True iff two byte strings are different pictures."""
    return a != b


def mount_inputs(mount):
    """(kcfg text, display-row holes) of a mount: what its emitter hands the page."""
    if mount == "clock":
        import make_clock

        return make_clock.CONFIG_XML, make_clock._display_holes()
    import make_wallpaper_live

    return make_wallpaper_live.config_main_xml(), {
        "ghostAlpha": make_wallpaper_live.global_alpha("glanced_at")
    }


def measure():
    """The MEASUREMENT policy/config_reach.rego decides: per mount and key, whether the
    render at its low end differs from the render at its high end; `withheld` says why
    nothing could be measured (no qml runner)."""
    import plasma_rewrite
    import render_qml

    if not os.path.exists(render_qml.QML):
        return {"cases": [], "withheld": f"{render_qml.QML} is not installed"}
    cases = []
    with tempfile.TemporaryDirectory() as td:
        for mount, (surface, size) in SURFACES.items():
            kcfg, holes = mount_inputs(mount)
            entries = plasma_rewrite._kcfg_defaults(kcfg)
            for key, typ, lo, hi in ends(entries, holes, mount):
                shots = []
                for tag, value in (("lo", lo), ("hi", hi)):
                    png = os.path.join(td, f"{mount}-{key}-{tag}.png")
                    rc, err = render_qml.render(
                        surface, VARIANT, size[0], size[1], png, {key: value}
                    )
                    if rc != 0 or not os.path.exists(png):
                        why = f"{mount}/{key}={value}: rc {rc}: {err}"
                        return {"cases": cases, "withheld": why}
                    with open(png, "rb") as fh:
                        shots.append(fh.read())
                cases.append(
                    {
                        "mount": mount,
                        "key": key,
                        "type": typ,
                        "low": lo,
                        "high": hi,
                        "differs": differs(shots[0], shots[1]),
                        "inert": INERT.get((mount, key)),
                    }
                )
    return {"cases": cases, "withheld": None}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_config_reach: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json

        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate

    return opa_gate.gate("config_reach")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    chk("identical pictures do not differ", differs(b"png", b"png"), False)
    chk("different pictures differ", differs(b"png", b"pnG"), True)
    rows = ends(
        {"showGhost": True, "use24h": True, "extra": 0.5},
        {"digitGap": "0.786", "digitGapMin": "0.786", "ghostAlpha": "0.5"},
    )
    keys = [r[0] for r in rows]
    chk("every display key of the clock is a member", "weight" in keys, True)
    chk(
        "a key with no control is a member (its default and its double + 1)",
        ("extra", "Double", 0.5, 2.0) in rows,
        True,
    )
    chk("each key appears once", len(keys) == len(set(keys)), True)
    wall = [r[0] for r in ends({}, {"ghostAlpha": "0.3"}, "wallpaper")]
    chk(
        "the wallpaper's own rows are its population (it exposes the unlit opacity)",
        "ghostAlpha" in wall and "weight" in wall,
        True,
    )
    chk("every mount has a surface to render", sorted(SURFACES), ["clock", "wallpaper"])
    # the LIVE arms: the measurement sees a key that reaches the pixels, and one that
    # does not (a key the template never reads), against the same renderer
    import render_qml

    if not os.path.exists(render_qml.QML):
        print("  SKIP no qml runner — the live arms did not run")
    else:
        with tempfile.TemporaryDirectory() as td:

            def shot(surface, size, cfg):
                png = os.path.join(td, "s.png")
                rc, _err = render_qml.render(
                    surface, VARIANT, size[0], size[1], png, cfg
                )
                with open(png, "rb") as fh:
                    return rc, fh.read()

            for mount, (surface, size) in SURFACES.items():
                rc0, base = shot(surface, size, {})
                rc1, ghost = shot(surface, size, {"showGhost": False})
                rc2, unread = shot(
                    surface, size, {"noSuchKeyTheTemplateNeverReads": 7.0}
                )
                chk(f"{mount}: the renders ran", (rc0, rc1, rc2), (0, 0, 0))
                chk(
                    f"{mount}: a key the template reads changes the picture",
                    differs(base, ghost),
                    True,
                )
                chk(
                    f"{mount}: a key it never reads does not",
                    differs(base, unread),
                    False,
                )
    print("check_config_reach selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
