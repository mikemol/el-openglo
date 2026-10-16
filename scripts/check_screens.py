#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_screens.py — the themed screenshots, MEASURED; policy/screens.rego decides (W52).

The pictures are catalog/library/render_screens.py's; this reports, per planned
still, whether the file exists, its size, how many distinct colours it has and
its modal colour, beside the two honest grounds of its variant (the harness
window's and the View background a bound surface draws). The requirement — a
still exists, is not blank, and sits on its variant's ground — is the policy's.

    scripts/check_screens.py --json      # the measurement
    scripts/check_screens.py --motion    # per animation: moving steps, fractional share of them
    scripts/check_screens.py --frames FILE  # every frame pair of one animation: shift, mismatch, tear
    scripts/check_screens.py --selftest  # the measurement can see

--motion (W173): a ZERO shift is excluded from the population (operator 2026-10-01: no
motion, no apparent flicker), so the share is fractional moving steps of MOVING steps; an
animation with no moving step prints as WITHHELD, never as a share. WEAKNESS: it reads the
shifts render_screens measured, so it is only as fine as that measurement's eighth-pip grid.

A missing screens/ directory is reported as every still absent (the policy
denies), because the pictures are checked in: an emitter change without a
regeneration is exactly what this catches.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "catalog", "library"))


def measure():
    import render_screens as RS

    return RS.measure()


def logged_steps(path):
    """The widget's own per-frame steps (W208) - ONE reader, render_screens.logged_steps,
    which the measurement also uses (W209); this delegates rather than keep a second copy."""
    import render_screens as RS

    return RS.logged_steps(path)


def logged_motion(steps):
    """(moving, fractional) from logged steps; a step within 1e-3 pip of an integer is whole."""
    moving = [s for s in steps if abs(s) > 1e-6]
    return len(moving), sum(1 for s in moving if abs(s - round(s)) > 1e-3)


def motion(anim):
    """(moving, fractional) step counts of one animation; a zero shift is not a step."""
    moving = [s for s in anim.get("shifts") or [] if s != 0]
    return len(moving), sum(1 for s in moving if s != int(s))


def frame_pairs(path, lit_hex, ground_hex, tolerance=0.5):
    """Per adjacent frame pair of one x-axis animation: (frame, shift, mismatch, total, tear).

    W203: the SAME helpers render_screens.animation_facts uses (pip_centres, pip_profile,
    best_pip_shift), reused rather than reimplemented, but keeping the frame index that
    animation_facts' `shifts` list drops - so a tear's neighbourhood is readable. An empty
    pair (nothing above the floor) is reported as such, not skipped silently."""
    import render_screens as RS
    from PIL import Image, ImageSequence

    lit, ground = RS._hex(lit_hex), RS._hex(ground_hex)
    profiles, centres, floor = [], None, 0.0
    for fr in ImageSequence.Iterator(Image.open(path)):
        rgb = fr.convert("RGB")
        if centres is None:
            centres = RS.pip_centres(rgb, lit, ground, "x")
            raw = RS.pip_profile(rgb, centres, lit, ground, 0.0, "x")
            floor = sum(raw) / len(raw) if raw else 0.0
        profiles.append(RS.pip_profile(rgb, centres, lit, ground, floor, "x"))
    rows = []
    for i in range(len(profiles) - 1):
        prev, cur = profiles[i], profiles[i + 1]
        total = max(sum(prev), sum(cur))
        if total < 0.5:
            rows.append((i + 1, None, None, round(total, 2), False))
            continue
        k, f, mism = RS.best_pip_shift(
            prev, cur, max(1, len(centres) // 4), both_ways=False
        )
        rows.append(
            (i + 1, k + f, round(mism, 2), round(total, 2), mism > tolerance * total)
        )
    return rows


def main(argv):
    known = {"--json", "--motion", "--frames", "--logged", "--selftest"}
    flags = [a for a in argv[1:] if a.startswith("--")]
    for a in flags:
        if a not in known:
            print(f"check_screens: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--logged" in argv:
        # W209: the widget's OWN per-frame steps (pips), from the el-frames chunk W208 writes -
        # what the harness did, not an image fit of what it drew
        rest = [a for a in argv[1:] if not a.startswith("--")]
        if len(rest) != 1:
            print(
                "check_screens: --logged takes one animation file (e.g. marquee-anim-EL-Amber.png)",
                file=sys.stderr,
            )
            return 2
        path = (
            rest[0]
            if os.path.isfile(rest[0])
            else os.path.join(measure()["dir"], os.path.basename(rest[0]))
        )
        if not os.path.isfile(path):
            print(f"check_screens: {path} does not exist", file=sys.stderr)
            return 1
        steps = logged_steps(path)
        if steps is None:
            print(
                f"check_screens: {os.path.basename(path)} carries no el-frames log (rendered before W208, or not "
                f"harness-driven); only the image fit can describe it",
                file=sys.stderr,
            )
            return 3
        for i, s in enumerate(steps, 2):
            print(f"  frame {i:3d}: step {s:+9.4f} pip")
        print(
            f"check_screens --logged: {len(steps)} step(s) in {os.path.basename(path)}; "
            f"min {min(steps):+.4f}, max {max(steps):+.4f}"
        )
        return 0
    if "--frames" in argv:
        rest = [a for a in argv[1:] if not a.startswith("--")]
        if len(rest) != 1:
            print(
                "check_screens: --frames takes one animation file (e.g. marquee-anim-EL-Amber.png)",
                file=sys.stderr,
            )
            return 2
        import render_screens as RS

        name = os.path.basename(rest[0])
        # the variant, axis and colours from the SAME plan and authorities measure() uses
        plan = {fn: (v, how) for fn, v, how in RS.plan_animations()}
        if name not in plan:
            print(
                f"check_screens: {name} is not a planned animation ({len(plan)} planned)",
                file=sys.stderr,
            )
            return 1
        variant, how = plan[name]
        if how[2] != "x":
            print(
                f"check_screens: --frames reads x-axis animations; {name} scrolls along {how[2]}",
                file=sys.stderr,
            )
            return 2
        path = os.path.join(measure()["dir"], name)
        if not os.path.isfile(path):
            print(f"check_screens: {path} does not exist", file=sys.stderr)
            return 1
        import make_preview as MP  # the same two authorities render_screens.measure reads
        import make_wallpaper_live as WL

        rows = frame_pairs(
            path,
            MP.parse_scheme(variant)["phosphor"],
            "#{:02x}{:02x}{:02x}".format(*WL.colors_for(variant)[0]),
        )
        for fr, shift, mism, total, tear in rows:
            print(
                f"  frame {fr:3d}: "
                + (
                    "empty pair"
                    if shift is None
                    else f"shift {shift:+7.3f}  mismatch {mism:6.2f} of {total:6.2f}{'  TEAR' if tear else ''}"
                )
            )
        print(
            f"check_screens --frames: {len(rows)} pair(s), {sum(1 for r in rows if r[4])} tear(s) in {name}"
        )
        return 0
    m = measure()
    if "--motion" in argv:
        anims = m.get("animations") or []
        if not anims:
            print(
                "check_screens: REFUSED - no animations measured; the search is broken, not the motion clean",
                file=sys.stderr,
            )
            return 1
        for a in anims:
            steps = (
                logged_steps(os.path.join(m["dir"], a["file"]))
                if a.get("exists")
                else None
            )
            n, f = logged_motion(steps) if steps is not None else motion(a)
            source = "logged offsets" if steps is not None else "image fit"
            share = f"{f / n:.2f}" if n else "WITHHELD (no moving step)"
            print(
                f"  {a.get('file')}: {f} of {n} moving steps fractional = {share} ({source}); "
                f"period2_share {a.get('period2_share')}"
            )
        print(f"check_screens --motion: {len(anims)} animation(s)")
        return 0
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    print(
        f"check_screens: {sum(1 for r in m['screens'] if r['exists'])} of {len(m['screens'])} stills present; "
        f"the verdict is `opa_gate.py screens`"
    )
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
        ok = ok and got == want

    import tempfile

    import render_screens as RS
    from PIL import Image

    m = measure()
    chk("the plan is 6 stills x 6 variants", len(m["screens"]), 36)
    # ⚑ THE MEASUREMENT CAN SEE: a blank picture has one distinct colour; a picture
    # on the wrong ground has a modal colour that is neither of the variant's
    with tempfile.TemporaryDirectory() as td:
        Image.new("RGB", (40, 20), (255, 0, 0)).save(
            os.path.join(td, "clock-EL-Amber.png")
        )
        rows = RS.measure(td)["screens"]
        r = next(x for x in rows if x["file"] == "clock-EL-Amber.png")
        chk("a blank still is a fact (1 distinct colour)", r["distinct"], 1)
        chk("a wrong ground is a fact", r["modal"] in r["grounds"], False)
        chk(
            "an absent still is a fact",
            next(x for x in rows if x["file"] == "switcher-EL-Amber.png")["exists"],
            False,
        )
        # an animation the measurement can see TEAR: a FIELD of ghost pips (one
        # column every 4 px) with three lit pips that shift left by one pip, then
        # move RIGHT by twelve (a restart — no left shift explains it), then shift
        # left by one again; the first frame is the empty field, the last is not
        ghost, litc, gnd = (152, 126, 90), (255, 212, 153), (20, 15, 8)
        frames = []
        for lit_at in (None, 75, 74, 86, 85):
            f = Image.new("RGB", (400, 20), gnd)
            for c in range(100):
                on = lit_at is not None and lit_at <= c < lit_at + 3
                for y in range(4, 16):
                    f.putpixel((4 * c + 2, y), litc if on else ghost)
            frames.append(f)
        ap = os.path.join(td, "marquee-anim-EL-Amber.png")
        frames[0].save(
            ap,
            format="PNG",
            save_all=True,
            append_images=frames[1:],
            duration=40,
            loop=0,
        )
        a = RS.animation_facts(ap, "#ffd499", "#140f08")
        chk("the frames are counted", a["frames"], 5)
        chk("the pips are found from the empty board", a["pips"], 100)
        chk(
            "a rightward move is a tear, the one-pip shifts are not",
            [t["frame"] for t in a["tears"]],
            [3],
        )
        chk(
            "the one-pip shifts are read",
            [k for k in a["shifts"] if k == 1.0],
            [1.0, 1.0],
        )
        chk(
            "an open loop is a fact (first and last frames differ)",
            a["seamless"],
            False,
        )
        # W203: --frames keeps the frame index animation_facts drops, and sees the same tear
        fr = frame_pairs(ap, "#ffd499", "#140f08")
        chk(
            "--frames sees the tear at frame 3 and only there",
            [r[0] for r in fr if r[4]],
            [3],
        )
        chk(
            "--frames reports the empty first pair, not skips it",
            fr[0][1] is None or fr[0][0] == 1,
            True,
        )
        # along y (the viewport): a field of pip ROWS with one lit row stepping down
        # one pip per frame, then up — a ping-pong is admitted on the y axis
        frames = []
        for lit_row in (2, 3, 4, 3, 2):
            f = Image.new("RGB", (60, 40), gnd)
            for r in range(10):
                for c in range(15):
                    for dx in range(4):
                        for dy in (1, 2):
                            f.putpixel(
                                (4 * c + dx, 4 * r + dy),
                                litc if r == lit_row else ghost,
                            )
            frames.append(f)
        ap = os.path.join(td, "pinholes-anim-EL-Amber.png")
        frames[0].save(
            ap,
            format="PNG",
            save_all=True,
            append_images=frames[1:],
            duration=40,
            loop=0,
        )
        a = RS.animation_facts(ap, "#ffd499", "#140f08", axis="y")
        chk("the pip rows are found along y", a["pips"], 10)
        # content moving DOWN the field is a shift of -1 (the viewport's band moving
        # down the backdrop moves content UP: +1); a ping-pong is admitted on y
        chk(
            "a ping-pong along y is shifts of -1 then +1, no tear",
            (a["shifts"], a["tears"]),
            ([-1.0, -1.0, 1.0, 1.0], []),
        )
        chk("...and it loops", a["seamless"], True)

        # W202: a SEE-SAW (three pips alternating whole and half lit, frame after frame)
        # puts the run's temporal power at period 2; a steady scroll of the same three pips
        # does not. The positive control for the S9 rule.
        def block_field(cols, level):
            f = Image.new("RGB", (400, 20), gnd)
            for c in range(100):
                lv = level if c in cols else 0.0
                px = tuple(round(g + (lt - g) * lv) for g, lt in zip(ghost, litc))
                for y in range(4, 16):
                    f.putpixel((4 * c + 2, y), px)
            return f

        runs = {
            "see-saw": [block_field((), 0.0)]
            + [
                block_field((40, 41, 42), 1.0 if k % 2 == 0 else 0.5) for k in range(23)
            ],
            "steady scroll": [block_field((), 0.0)]
            + [block_field((at, at + 1, at + 2), 1.0) for at in range(80, 57, -1)],
        }
        p2 = {}
        for name, fs in runs.items():
            path = os.path.join(td, f"{name.replace(' ', '-')}-anim-EL-Amber.png")
            fs[0].save(
                path,
                format="PNG",
                save_all=True,
                append_images=fs[1:],
                duration=40,
                loop=0,
            )
            p2[name] = RS.animation_facts(path, "#ffd499", "#140f08")["period2_share"]
        chk(
            "a see-saw concentrates the power at period 2 (share over 0.5)",
            p2["see-saw"] is not None and p2["see-saw"] > 0.5,
            True,
        )
        chk(
            "a steady scroll does not (share under 0.25)",
            p2["steady scroll"] is not None and p2["steady scroll"] < 0.25,
            True,
        )
        print(f"    (measured: see-saw {p2['see-saw']}, steady {p2['steady scroll']})")
    # W175: the prime-period reading can SEE a single line, an even spread and a partial one, and it
    # refuses a run too short to have a spectrum. Cosines, not sines: a sine at period 2 is zero at every
    # integer frame and would read as silent.
    import math

    def tone(periods, n=60):
        return [
            [sum(math.cos(2 * math.pi * t / p) for p in periods)] * 4 for t in range(n)
        ]

    one = RS.prime_lines(tone([7]))
    spread = RS.prime_lines(tone([2, 3, 5, 7, 11, 13, 17, 19, 23, 29]))
    part = RS.prime_lines(tone([3, 5, 7]))
    chk(
        "one line at period 7 is read as prime 7 holding over 0.9 of the power",
        (one["peak"][0], one["peak"][1] > 0.9),
        (7, True),
    )
    chk("...and as concentrated (evenness under 0.1)", one["evenness"] < 0.1, True)
    chk(
        "equal power on every prime up to 29 is read as even (evenness over 0.8)",
        spread["evenness"] > 0.8,
        True,
    )
    chk(
        "equal power on only three of those primes is NOT even (evenness under 0.2)",
        part["evenness"] < 0.2,
        True,
    )
    chk(
        "primes_upto lists them",
        RS.primes_upto(20),
        [2, 3, 5, 7, 11, 13, 17, 19],
    )
    chk("a 3-frame run has no spectrum", RS.prime_lines([[0.0]] * 3), None)
    chk(
        "a run that never varies has no spectrum",
        RS.prime_lines([[1.0, 1.0]] * 20),
        None,
    )
    chk(
        "the fields on a record are the evenness and the peak, or None for both",
        (RS.prime_fields([[0.0]] * 3), sorted(RS.prime_fields(tone([7])))),
        (
            {"prime_evenness": None, "prime_peak": None},
            ["prime_evenness", "prime_peak"],
        ),
    )
    print("check_screens selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
