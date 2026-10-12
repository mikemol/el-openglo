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

MOUNTS: the clock and the live wallpaper (W267) are rendered as frozen stills. The marquee acts over
time, so it is measured by a SAMPLED run (W503): its own harness (check_marquee_live) is run at each
key's two ends and the stepped-capture frame SAMPLED_FRAME is compared, a fixed scroll offset on every
host. The halo keys (bloom, haloOpacity, glow) are drawn by a MultiEffect the software scene graph does
not render, so those runs go to the RHI inside a held kwin (EL_MARQUEE_RHI path, W121); a key that acts
only while another is on is measured with that one on, declared in NEEDS.

    scripts/check_config_reach.py            # the verdict, as opa_gate config_reach decides it
    scripts/check_config_reach.py --json     # the measurement
    scripts/check_config_reach.py --selftest

⚑ WEAKNESSES, STATED. (1) ONE still per mount at one size under one variant, so a key
that only acts at another size or over time is read as dead: it must be declared INERT
with its reason, never silently passed. (2) The two ends are the control's ends: a
setting that acts only between them (a non-monotone one) is seen as alive, and a
setting alive between but identical at both ends is read as dead. (3) Decoded-pixel
equality of the PNG (not file bytes: the same picture encodes to different bytes under
load): any visible change, including a one-pixel antialiasing difference, counts as
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

# (mount, key) that cannot show in ONE still, with the reason; a declaration is data the
# policy can read, so an exemption is visible rather than a quiet `continue`
_BLINK = "the colon toggles per tick and one still holds it lit either way"
_NOT_DRAWN = "not drawn: it changes behaviour or the trace, never a pixel of the board"
INERT = {
    ("clock", "blinkColon"): _BLINK,
    ("wallpaper", "blinkColon"): _BLINK,
    # the marquee's non-visual and state-dependent keys (W503). Declared, never silently passed; not rendered.
    ("marquee", "openLinks"): "a tap opens a link: " + _NOT_DRAWN,
    (
        "marquee",
        "hoverPause",
    ): "the pointer pauses the board (measured by check_marquee_live --hovered): the pointer is not part of a still",
    ("marquee", "debugLog"): "writes the widget's trace: " + _NOT_DRAWN,
    ("marquee", "traceLog"): "the persisted trace text: " + _NOT_DRAWN,
    (
        "marquee",
        "idleText",
    ): "shown only on an IDLE board; the sampled run holds a board with text",
    (
        "marquee",
        "maxItems",
    ): "caps the ring's items; visible only with more notifications than the cap",
}

# a key that acts only while ANOTHER is on is measured with that one on (the other keys stay default):
# the halo's opacity and brightness multiply a halo the marquee draws only when bloom is above 0, and bloom
# defaults to 0 (off: an unconfigured board is unchanged), so at the defaults they cannot show
NEEDS = {
    ("marquee", "haloOpacity"): {"bloom": 3.0},
    ("marquee", "glow"): {"bloom": 3.0},
}

# the keys drawn by the emission halo's MultiEffect, which only the RHI renders
HALO_KEYS = {"bloom", "haloOpacity", "glow"}

# the sampled measurement: the stepped-capture frame compared (the text is well on the board) and the
# wall-clock cap that bounds the run once that many frames are grabbed
# ⚑ FRAME 23, NOT 14 (W268). Frame 14 sits at an ALIGNED scroll phase (13 steps of 4.618 pips leave a
# fraction of 0.03), where every pip is fully lit or dark: a transfer curve (gamma) and the backdrop
# sampling (backdropScale) act on PARTIAL coverage and had nothing to act on, so both read as dead
# (measured: identical frames). Frame 23 leaves a fraction of 0.60: partial pips exist, and the
# backdrop resolutions 2 and 8 round that phase differently (0.5 against 0.625). Measured at 23:
# gamma and backdropScale each change about 2500 pixels; the same config twice is identical.
SAMPLED_FRAME = 23
SAMPLED_END_MS = 8000
SAMPLED_TEXT = " ".join(["Hello World"] * 9)

# ⚑ EVERY RENDER HOLDS THE COLON STEADY (W454, 2026-10-10: the @CONFIG-REACH-SEES flake).
# The colon's own 1 Hz timer starts when the subject LOADS while the harness grabs at a fixed
# 1200 ms after the WINDOW opens, so under load the grab landed either side of the second
# toggle: two renders of the same inputs differed by 2.5-7.4k px (clock) and the whole frame
# (wallpaper, the glow), from the kept account of a failed run. A still must be a function of
# its inputs, so the blink is pinned off beneath every render and a key's own value wins.
PIN = {"blinkColon": False}


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
        elif isinstance(default, str):
            # a text key has no ends: it must be declared INERT (a string is never a slider)
            out.append((key, "String", default, default))
        else:
            out.append((key, "Double", float(default), float(default) * 2 + 1))
    return out


def differs(a, b):
    """True iff two PNGs are different PICTURES: same size and RGBA pixels, not same file.

    ⚑ BYTES ARE NOT THE PICTURE (W454, 2026-10-10: @CONFIG-REACH-SEES flaked in the gate
    on both mounts). scripts/flake_hunt.py reproduced it at 14 of 200 under load, and the
    two renders of the same inputs had IDENTICAL pixels, the same backend, and different
    PNG bytes: a dead setting read as alive, and a live one could never read as dead. So
    the comparison decodes. Bytes that are not a PNG (the selftest's arms) fall back to
    byte equality, since there is no picture to decode."""
    import io

    from PIL import Image

    try:
        with Image.open(io.BytesIO(a)) as ia, Image.open(io.BytesIO(b)) as ib:
            ra, rb = ia.convert("RGBA"), ib.convert("RGBA")
            return ra.size != rb.size or ra.tobytes() != rb.tobytes()
    except OSError:
        return a != b


def how_differ(a, b):
    """A sentence saying HOW two renders differ (for a failing arm's account): decoded
    sizes, differing pixels and their bounding box, or why they could not be decoded."""
    import io

    from PIL import Image, ImageChops

    try:
        with Image.open(io.BytesIO(a)) as ia, Image.open(io.BytesIO(b)) as ib:
            ra, rb = ia.convert("RGBA"), ib.convert("RGBA")
            if ra.size != rb.size:
                return f"sizes {ra.size} vs {rb.size}"
            delta = ImageChops.difference(ra, rb)
            box = delta.convert("RGB").getbbox()
            n = sum(1 for px in delta.get_flattened_data() if px != (0, 0, 0, 0))
            return f"{n} px differ within {box}; {len(a)} vs {len(b)} bytes"
    except OSError as e:
        return f"could not decode ({type(e).__name__}: {e}); {len(a)} vs {len(b)} bytes"


def specs():
    """{mount: MountSpec} from the ONE registry every horizontal check reads
    (display_params.MOUNT_REGISTRY, W271): no per-mount table lives here."""
    import display_params as DP

    return DP.MOUNT_REGISTRY


def resolve(ref):
    """The value a (module, attribute) pair names, called when it is callable."""
    import importlib

    value = getattr(importlib.import_module(ref[0]), ref[1])
    return value() if callable(value) else value


def mount_inputs(spec):
    """(kcfg text, display-row holes) of a measurable mount: what its emitter hands
    the page."""
    holes = resolve(spec.holes) if spec.holes else {}
    return resolve(spec.kcfg), holes


def sampled_png(overrides, mesa, td, tag):
    """The stepped-capture frame SAMPLED_FRAME of the marquee harness under `overrides` as PNG bytes,
    or None when the run produced no such frame. The same offset on every host (R9), so a frame is a
    function of its inputs; `mesa` runs it on the RHI inside a held kwin."""
    import check_marquee_live as ML

    fdir = os.path.join(td, tag)
    os.makedirs(fdir, exist_ok=True)
    timeline = [
        (
            300,
            "arrive",
            1,
            {
                "summary": "",
                "body": SAMPLED_TEXT,
                "applicationName": "app",
                "urgency": 1,
            },
            "",
        )
    ]
    saved = ML.BACKEND["mesa"]
    ML.BACKEND["mesa"] = mesa
    try:
        ML.run(
            variant=VARIANT,
            end_ms=SAMPLED_END_MS,
            frames=fdir,
            timeline=timeline,
            config_overrides=overrides,
            frame_cap=SAMPLED_FRAME + 1,
        )
    except RuntimeError:
        # a kwin that would not start, or a harness that printed no RESULT, is a fact about the
        # machine: no frame, so the key is WITHHELD (counted and printed), never a crash or a pass
        return None
    finally:
        ML.BACKEND["mesa"] = saved
    png = os.path.join(fdir, f"frame-{SAMPLED_FRAME:03d}.png")
    if not os.path.exists(png):
        return None
    with open(png, "rb") as fh:
        return fh.read()


def sampled_cases(mount, entries, holes, td):
    """([case], withheld-or-None) for a SAMPLED mount: each key's two ends compared at the stepped frame.
    A key declared INERT is not rendered (its reason is the case); a key in NEEDS is measured with its
    prerequisite on; a halo key goes to the RHI."""
    cases = []
    for key, typ, lo, hi in ends(entries, holes, mount):
        inert = INERT.get((mount, key))
        context = NEEDS.get((mount, key), {})
        case = {
            "mount": mount,
            "key": key,
            "type": typ,
            "low": lo,
            "high": hi,
            "inert": inert,
            "context": context,
        }
        if inert:
            cases.append({**case, "differs": False})
            continue
        mesa = key in HALO_KEYS
        shots = []
        for tag, value in (("lo", lo), ("hi", hi)):
            blob = sampled_png(
                {**context, key: value}, mesa, td, f"{mount}-{key}-{tag}"
            )
            if blob is None:
                return (
                    cases,
                    f"{mount}/{key}={value}: the sampled run produced no frame",
                )
            shots.append(blob)
        cases.append({**case, "differs": differs(shots[0], shots[1])})
    return cases, None


def measure():
    """The MEASUREMENT policy/config_reach.rego decides: per mount and key, whether the
    render at its low end differs from the render at its high end; `withheld` says why
    nothing could be measured (no qml runner)."""
    import plasma_rewrite
    import render_qml

    if not os.path.exists(render_qml.QML):
        return {
            "cases": [],
            "unmeasured": [],
            "withheld": f"{render_qml.QML} is not installed",
        }
    cases = []
    unmeasured = []
    with tempfile.TemporaryDirectory() as td:
        for mount, spec in specs().items():
            if spec.sampled:
                kcfg, holes = mount_inputs(spec)
                got, why = sampled_cases(
                    mount, plasma_rewrite._kcfg_defaults(kcfg), holes, td
                )
                cases += got
                if why:
                    return {"cases": cases, "unmeasured": unmeasured, "withheld": why}
                continue
            if spec.surface is None or spec.size is None:
                unmeasured.append({"mount": mount, "reason": spec.unmeasured})
                continue
            surface, size = spec.surface, spec.size
            kcfg, holes = mount_inputs(spec)
            entries = plasma_rewrite._kcfg_defaults(kcfg)
            for key, typ, lo, hi in ends(entries, holes, mount):
                shots = []
                for tag, value in (("lo", lo), ("hi", hi)):
                    png = os.path.join(td, f"{mount}-{key}-{tag}.png")
                    rc, err = render_qml.render(
                        surface,
                        VARIANT,
                        size[0],
                        size[1],
                        png,
                        {**PIN, key: value},
                        harness=render_qml.HARNESS_SETTLED,
                    )
                    if rc != 0 or not os.path.exists(png):
                        why = f"{mount}/{key}={value}: rc {rc}: {err}"
                        return {
                            "cases": cases,
                            "unmeasured": unmeasured,
                            "withheld": why,
                        }
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
    return {"cases": cases, "unmeasured": unmeasured, "withheld": None}


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
    import io

    from PIL import Image

    def png_of(px, level):
        buf = io.BytesIO()
        Image.new("RGBA", (4, 4), px).save(buf, "PNG", compress_level=level)
        return buf.getvalue()

    same_a, same_b = png_of((9, 9, 9, 255), 0), png_of((9, 9, 9, 255), 9)
    chk("the encodings really differ (the arm is not vacuous)", same_a != same_b, True)
    chk("one picture in two encodings is NOT different", differs(same_a, same_b), False)
    chk(
        "one changed pixel IS different",
        differs(same_a, png_of((9, 9, 10, 255), 0)),
        True,
    )
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
    wall_holes = mount_inputs(specs()["wallpaper"])[1]
    wall = [r[0] for r in ends({}, wall_holes, "wallpaper")]
    chk(
        "the wallpaper's own rows are its population (it exposes the unlit opacity)",
        "ghostAlpha" in wall and "weight" in wall,
        True,
    )
    measured = {m: s for m, s in specs().items() if s.surface is not None}
    chk("the registry's measurable mounts", sorted(measured), ["clock", "wallpaper"])
    chk(
        "an unmeasurable mount states why",
        all(s.unmeasured for m, s in specs().items() if m not in measured),
        True,
    )
    # the sampled mount's declarations name real keys (a stale INERT or NEEDS entry would exempt nothing)
    import plasma_rewrite

    sampled = {m: s for m, s in specs().items() if s.sampled}
    chk("only the marquee is sampled", sorted(sampled), ["marquee"])
    for mount, spec in sampled.items():
        kcfg_keys = set(plasma_rewrite._kcfg_defaults(mount_inputs(spec)[0]))
        declared = {k for (m, k) in [*INERT, *NEEDS] if m == mount}
        chk(
            f"{mount}: every INERT and NEEDS key is a real setting",
            sorted(declared - kcfg_keys),
            [],
        )
        chk(
            f"{mount}: every halo key is a real setting",
            sorted(HALO_KEYS - kcfg_keys),
            [],
        )
    chk(
        "a text key gets a String row, never a slider",
        ("idle", "String", "", "") in ends({"idle": ""}, {}, "marquee"),
        True,
    )
    # the SAMPLED live arms: the sampled measurement sees a setting that reaches the board and one that
    # does not, on the software scene graph; and, where kwin exists, that the RHI draws the halo
    # (bloom 0 against 6), which the software scene graph cannot
    import render_qml as rq

    if not os.path.exists(rq.QML):
        print("  SKIP no qml runner — the sampled live arms did not run")
    else:
        with tempfile.TemporaryDirectory() as std:
            base = sampled_png({}, False, std, "base")
            ghost = sampled_png({"showField": False}, False, std, "ghost")
            unread = sampled_png(
                {"noSuchKeyTheTemplateNeverReads": 7.0}, False, std, "unread"
            )
            chk(
                "sampled: the three runs produced a frame",
                (base is None, ghost is None, unread is None),
                (False, False, False),
            )
            if None not in (base, ghost, unread):
                chk(
                    "sampled: a setting the board reads changes the frame",
                    differs(base, ghost),
                    True,
                )
                chk(
                    "sampled: a key it never reads does not",
                    differs(base, unread),
                    False,
                )
            import shutil

            import qt_sandbox

            if shutil.which(qt_sandbox.KWIN):
                off = sampled_png({"bloom": 0.0}, True, std, "bloom-off")
                on = sampled_png({"bloom": 6.0}, True, std, "bloom-on")
                chk(
                    "sampled on the RHI: bloom 6 draws a halo that bloom 0 does not",
                    None not in (off, on) and differs(off, on),
                    True,
                )
            else:
                print(f"  SKIP no {qt_sandbox.KWIN} — the RHI halo arm did not run")
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
                    surface,
                    VARIANT,
                    size[0],
                    size[1],
                    png,
                    cfg,
                    harness=render_qml.HARNESS_SETTLED,
                )
                with open(png, "rb") as fh:
                    return rc, fh.read()

            for mount, spec in measured.items():
                surface, size = spec.surface, spec.size
                rc0, base = shot(surface, size, dict(PIN))
                rc1, ghost = shot(surface, size, {**PIN, "showGhost": False})
                rc2, unread = shot(
                    surface, size, {**PIN, "noSuchKeyTheTemplateNeverReads": 7.0}
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
                if differs(base, unread):
                    import keep_account

                    print(f"       {mount}: base vs unread: {how_differ(base, unread)}")
                    keep = f"{keep_account.ACCOUNTS}/reach-{os.getpid()}-{mount}"
                    os.makedirs(keep_account.ACCOUNTS, exist_ok=True)
                    for tag, blob in (("base", base), ("unread", unread)):
                        with open(f"{keep}-{tag}.png", "wb") as fh:
                            fh.write(blob)
                    print(f"       kept {keep}-base.png and -unread.png")
    print("check_config_reach selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
