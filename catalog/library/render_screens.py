#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""render_screens.py — screenshots of every surface x variant, through the theme (W52).

⚑ THESE ARE NOT MOCK-UPS. Each PNG is the emitted surface rendered by Qt under
the real KDE platform theme with a private kdeglobals holding that variant's
scheme (theme_probe.env_for) — what the desktop draws when that scheme is
applied. The marquee stills come from check_marquee_live's harness (the
widget mid-scroll; the widget held by the hover-pause, ring pulsing); the
switcher from render_qml's KWin rewrite over a three-caption stub model;
the clock and live wallpaper from render_qml as the render gate draws them.

    catalog/library/render_screens.py            # render ONLY the outputs whose key moved (W61)
    catalog/library/render_screens.py --all      # render every output
    catalog/library/render_screens.py --jobs=8   # N qml processes side by side (default 1)
    catalog/library/render_screens.py --stale    # which outputs would render, n of m
    catalog/library/render_screens.py --keys     # the per-output keys and their inputs, as data
    catalog/library/render_screens.py --list     # what would be written
    catalog/library/render_screens.py --json     # the measurement: per file, exists / size / modal colour

One script regenerates everything, so the pictures cannot drift from the
emitters. The README references them through the projection, never by hand.
WEAKNESS: ~2 s wall of qml per still on an idle host; the marquee stills add
a hovered run each. A missing qml runner is a printed SKIP.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
SCREENS = os.path.join(ROOT, "catalog", "library", "screens")
VARIANTS = (
    "EL-Openglo",
    "EL-Openglo-Lit",
    "EL-Azure",
    "EL-Azure-Lit",
    "EL-Amber",
    "EL-Amber-Lit",
)

# (name, how) — how: ("render_qml", surface, w, h) or ("marquee", which)
STILLS = (
    ("clock", ("render_qml", "clock", 400, 48)),
    ("switcher", ("render_qml", "switcher", 480, 200)),
    ("live-wallpaper", ("render_qml", "live-wallpaper", 480, 300)),
    ("marquee", ("marquee", "scroll")),
    ("marquee-paused", ("marquee", "paused")),
    # W54: a Qt Text item read through the aperture field — no glyph table
    ("pinholes", ("render_qml", "aperture-text", 420, 40)),
)


# W52's second half: the marquee SCROLLING, one APNG per variant, frames grabbed
# by the harness while the text is on the move (check_marquee_live.animate); and
# W54's viewport: the 8-row field scrolling DOWN a 16-row Unifont backdrop and
# back — one grab per band, all in one qml process (render_qml.render_frames), ping-pong so the
# loop closes (S6), the scroll invariant measured along y (S5)
ANIMATIONS = (
    ("marquee-anim", ("marquee", "animate", "x")),
    ("pinholes-anim", ("aperture-text", "scroll-y", "y")),
)
# ⚑ THE GLYPH MOVES, THEN IT IS PIXELATED — NOT THE OTHER WAY (operator,
# 2026-09-22, seeing pinholes-anim: "it looks like the pixelation of the glyphs is
# calculated, and then the pixelated glyphs are moved up and down the grid. What we
# want instead is for the glyphs to move and the pixelation RECALCULATED, so we get
# subpixel rendering on a temporal axis"). These steps were whole PIPS, so every
# frame sampled an identically-aligned band and the field just translated a fixed
# pattern. The backdrop carries `scale` pixels per pip, so a step of 1/scale is a
# real re-sampling — and it is also the Nyquist bound: the backdrop pixel is the
# finest feature the aperture can resolve, so a finer step adds nothing.
VIEWPORT_SUBSTEPS = 4  # = ApertureField.scale
VIEWPORT_STEPS = [i / VIEWPORT_SUBSTEPS for i in range(8 * VIEWPORT_SUBSTEPS + 1)] + [
    i / VIEWPORT_SUBSTEPS for i in range(8 * VIEWPORT_SUBSTEPS - 1, -1, -1)
]
VIEWPORT_FRAME_MS = 40


def plan():
    return [(f"{name}-{v}.png", v, how) for v in VARIANTS for name, how in STILLS]


def plan_animations():
    return [(f"{name}-{v}.png", v, how) for v in VARIANTS for name, how in ANIMATIONS]


def plan_derived():
    """The outputs render_all writes that are DERIVED from the stills rather than
    rendered: one contact sheet per variant, the strip of all six, and the index.

    ⚑ THE PLAN UNDER-DECLARED ITS OWN OUTPUTS BY 19 OF 55 (measured 2026-09-22 by
    scripts/check_action_key.py, which counted 55 .png in the output directory
    while `--list` printed 36). `--list` says it prints "what would be written"
    and printed neither the 12 animations nor the 7 sheets, and render_all also
    writes README.md, which nothing declared at all.

    ⚑ AND THAT IS THE PRECONDITION FAILURE FOR PER-RENDER ACTIONS. Splitting this
    action into one backward cone per output requires the outputs to be ENUMERABLE
    from the declaration; a producer that names 36 of the 55 files it writes
    cannot be split, and every unnamed file is one whose staleness nobody can
    attribute. A count taken from the output DIRECTORY instead would agree with
    itself no matter how wrong the plan was — it measures the disk, not the claim."""
    out = [(f"sheet-{v}.png", v, ("sheet", "variant")) for v in VARIANTS]
    out.append(("strip.png", None, ("sheet", "strip")))
    out.append(("README.md", None, ("index", "md")))
    return out


def plan_all():
    """Every file render_all writes, declared. The population @CURRENCY keys on."""
    return plan() + plan_animations() + plan_derived()


# the viewport's one-process job: (surface, w, h, config key, steps, read-back probe)
VIEWPORT_JOB = ("aperture-text", 420, 40, "offsetRows", VIEWPORT_STEPS, "offsetY")


def stagers(v, how, out):
    """[stage] — the qml process(es) that produce one planned output, BUILT EXACTLY AS
    render_one BUILDS THEM (the same *_args / *_stager constructors). ⚑ This is where
    a key's input list comes from (W61): not a list of files someone believes the
    render reads, but the job itself, staged and digested. `out` is where the
    output would go; the key passes a sentinel so no output is read as an input."""
    import check_marquee_live as ML
    import render_qml as RQ

    if how[0] == "render_qml":
        _k, surface, w, h = how
        return [RQ.render_stager(surface, v, w, h, out)]
    if how == ("marquee", "scroll"):
        return [ML.stager(**ML.scroll_still_args(v, out))]
    if how == ("marquee", "paused"):
        return [ML.stager(**ML.hovered_args(v, out))]
    if how[:2] == ("marquee", "animate"):
        return [ML.stager(**ML.animate_args(v, out))]
    if how[:2] == ("aperture-text", "scroll-y"):
        s, w, h, key, steps, probe = VIEWPORT_JOB
        return [RQ.frames_stager(s, v, w, h, out, key, steps, probe)]
    raise ValueError(f"no job for {how!r}")


_LIB = os.path.relpath(os.path.dirname(os.path.abspath(__file__)), ROOT)

# how[0] -> the post-render code an output of that kind runs after its qml job, as
# repo-relative files (W61). Stills have none: their pixels are the job's bytes. The
# marquee animation's frames are assembled by its own stager module (`seed`); the
# viewport's by screens_viewport.
POST_CODE = {
    ("aperture-text", "scroll-y"): lambda seed: [
        os.path.join(_LIB, "screens_viewport.py")
    ],
    ("marquee", "animate"): lambda seed: [seed],
}


def sheet_tiles(v):
    """The stills a variant's contact sheet stacks, in order — the sheet's inputs."""
    return [f"{name}-{v}.png" for name, _h in STILLS]


def derived_inputs(fn, v, how):
    """The planned outputs a DERIVED output reads (a sheet its tiles; the strip the
    sheets), or None for the index, whose key is its own emitted text."""
    if how == ("sheet", "variant"):
        return sheet_tiles(v)
    if how == ("sheet", "strip"):
        return [f"sheet-{x}.png" for x in VARIANTS]
    return None


def output_keys():
    """{file: {"key", "inputs"}} for every declared output, plus the code files and
    host facts they were keyed over (W61, the operator's fine-grained build graph).

    ⚑ EARLY CUTOFF. A rendered output is keyed on what its qml process is HANDED —
    the staged job directory (subject.qml, companions, harness with its fill values,
    kdeglobals = that variant's .colors bytes, the notification stub), the repo
    files the job names by path and QML resolves from there (a directory import's
    types), the Qt environment, argv — plus the RUNNER's code and the host. An
    emitter's SOURCE is never in it: a rebuilt emitter whose bytes did not move
    stops there. The runner code is the import closure of the modules the job and
    its post-processing run in, PRUNED at every generator emitters.ROLES declares,
    because a generator's contribution is already in the key as bytes.

    ⚑ A DERIVED OUTPUT IS KEYED ON ITS INPUTS' KEYS plus this module's code (a sheet
    on its tiles, the strip on the sheets); the index on its own emitted text.

    WEAKNESS: an input the process reads that the job does NOT name — a host font
    by family, a Qt plugin, an env var outside JOB_ENV — is not in the key, so a
    change there reads CURRENT when it is stale. The host fingerprint and the
    residue (computed reads in the runner code) are the declared bound on that.
    WEAKNESS (per-kind runner code): the code term is per job KIND at MODULE
    grain (POST_CODE). This file is no longer keyed (W61, 2026-10-02): a change to
    its dispatch that matters changes the staged job, which is keyed as bytes; a
    change that does not (a comment, plan bookkeeping) moves nothing."""
    import check_action_key as AK

    sentinel = "/@OUT@"
    host, missing = AK.host_inputs()
    keys, code_files = {}, set()
    for fn, v, how in plan() + plan_animations():
        inputs = {}
        for i, stage in enumerate(stagers(v, how, os.path.join(sentinel, fn))):
            for k, d in AK.job_inputs(stage).items():
                inputs[f"job{i}:{k}"] = d
            # ⚑ THE RUNNER CODE IS PER JOB KIND (W61 follow-up): the closure of the
            # module that OWNS this job's stager (render_qml or check_marquee_live),
            # plus this file as a FILE — the dispatch and post-processing (APNG
            # assembly) it runs. NOT this file's import closure: that reaches both
            # harnesses, so a comment in check_marquee_live re-keyed the clock
            # (measured on main: 55 of 56 outputs, for one comment).
            # ⚑ ONLY CODE THAT SHAPES THE PIXELS AFTER THE JOB IS STAGED (W96). The
            # closure's job-builders (render_qml, plasma_rewrite, templates/loader,
            # ...) are already in the key as the job0:* bytes they produce; keying
            # them whole-file too re-rendered 30 stills for an analysis-only edit
            # (render_qml.texture(), 2026-09-26/27). What stays: this file (the
            # viewport APNG and the sheets) and the stager's own module where it
            # assembles frames after qml (check_marquee_live.animate).
            # ⚑ W159: qt_sandbox is keyed as DATA (job_inputs' `backend`, from
            # qt_sandbox.backend_facts), not as a file — a comment or a selftest edit
            # in it re-rendered 55 of 56 outputs (W158).
            if f"job{i}:backend" not in inputs:
                raise RuntimeError(
                    f"render_screens: {fn}: job {i} has no backend fact — "
                    "the key would omit the scene-graph route"
                )
            # ⚑ PER KIND, NOT THIS FILE (W61, 2026-10-02): keyed whole, this file moved
            # 55 of 56 keys for one comment. A still's pixels are its job bytes (already
            # keyed); an animation adds only the module that assembles its frames.
            seed = os.path.relpath(stage.__code__.co_filename, ROOT)
            post = POST_CODE.get(tuple(how[:2]))
            code = sorted(post(seed) if post else [])
            code_files.update(code)
            for rel in code:
                inputs[f"code:{rel}"] = AK.digest_rel(rel)
        inputs.update(host)
        keys[fn] = {"key": AK.key_over(inputs), "inputs": inputs}
    # a derived output runs only the sheet module over tiles already keyed
    sheets_rel = os.path.relpath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "screens_sheets.py"),
        ROOT,
    )
    code_files.add(sheets_rel)
    code_inputs = {f"code:{sheets_rel}": AK.digest_rel(sheets_rel)}
    for fn, v, how in plan_derived():
        src = derived_inputs(fn, v, how)
        if src is None:
            inputs = {"content": AK.digest_text(index_md())}
        else:
            inputs = dict(code_inputs, **{f"input:{s}": keys[s]["key"] for s in src})
        keys[fn] = {"key": AK.key_over(inputs), "inputs": inputs}
    return {"outputs": keys, "code": sorted(code_files), "missing_host": missing}


def recorded_keys():
    """{file: key} as recorded at the last build of each output (catalog/actions.json)."""
    import check_action_key as AK

    return AK.recorded_outputs("screens")


def stale(keys=None):
    """[file] whose current key differs from the recorded one, or was never recorded,
    or is declared and absent from disk — the outputs a build must (re)produce."""
    keys = keys or output_keys()["outputs"]
    rec = recorded_keys()
    return [
        fn
        for fn in (f for f, _v, _h in plan_all())
        if rec.get(fn) != keys[fn]["key"]
        or not os.path.isfile(os.path.join(SCREENS, fn))
    ]


def animate_viewport(variant, out_apng):
    """The pinholes-anim APNG (offsetRows 0..8..0, offsetY read back per frame);
    the assembly lives in screens_viewport so it keys only these outputs (W61)."""
    import screens_viewport as SV

    return SV.animate_viewport(
        variant, out_apng, VIEWPORT_JOB, [s * VIEWPORT_SUBSTEPS for s in VIEWPORT_STEPS]
    )


def render_one(v, how, out):
    """Produce one planned still or animation at `out`; its jobs are stagers()'s."""
    import check_marquee_live as ML
    import render_qml as RQ

    try:
        if how[0] == "render_qml":
            _k, surface, w, h = how
            RQ.render(surface, v, w, h, out)
        elif how == ("marquee", "scroll"):
            ML.run(**ML.scroll_still_args(v, out))
        elif how == ("marquee", "paused"):
            ML.run(**ML.hovered_args(v, out))
        elif how[:2] == ("marquee", "animate"):
            ML.animate(v, out)
        elif how[:2] == ("aperture-text", "scroll-y"):
            animate_viewport(v, out)
    except RuntimeError as e:  # a harness that reported no RESULT: a hole, named
        print(f"render_screens: {os.path.basename(out)} REFUSED — {e}", file=sys.stderr)
    return os.path.isfile(out)


def render_all(out_dir=SCREENS, only=None, keys=None, jobs=1):
    """Render the planned outputs — all of them, or `only` those named — and return
    (written, sheets). With `keys` ({file: key}), each output this run PRODUCED has
    the key it was built from recorded (check_action_key.record_outputs): the key is
    computed BEFORE the render, over the inputs the render then reads, so the record
    is not an assertion by whoever ran --write."""
    os.makedirs(out_dir, exist_ok=True)
    want = set(only) if only is not None else {fn for fn, _v, _h in plan_all()}
    written = []
    # ⚑ A STALE FILE MUST NOT COUNT AS A RENDER (measured 2026-09-23: under W73's
    # sandbox every render_qml call failed — X authority stripped — and this loop
    # still reported "42 of 48", because `os.path.isfile(out)` found LAST NIGHT'S
    # pictures). Every output about to be rendered is removed first, so only a
    # render this run produced can be counted — and a failure leaves a hole
    # @SCREENS will refuse.
    for fn, _v, _how in plan() + plan_animations():
        p = os.path.join(out_dir, fn)
        if fn in want and os.path.isfile(p):
            os.remove(p)
    # ⚑ PARALLEL (operator, 2026-09-25: "hardly using any CPU at all"): each job
    # is a qml process that mostly WAITS on its own real-time harness, so `jobs`
    # of them run side by side. Safe for the animations only since R9's capture
    # hold: a frame grab no longer races the scroll on a loaded host.
    from concurrent.futures import ThreadPoolExecutor

    todo = [(fn, v, how) for fn, v, how in plan() + plan_animations() if fn in want]
    with ThreadPoolExecutor(max_workers=max(1, jobs)) as ex:
        done_ok = list(
            ex.map(lambda t: render_one(t[1], t[2], os.path.join(out_dir, t[0])), todo)
        )
    written += [
        os.path.join(out_dir, fn) for (fn, _v, _h), ok in zip(todo, done_ok) if ok
    ]
    sheets = contact_sheets(out_dir, only=want)
    if "README.md" in want:
        with open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8") as fh:
            fh.write(index_md())
    if keys is not None:
        import check_action_key as AK

        done = {os.path.basename(p) for p in written}
        # ⚑ A DERIVED OUTPUT IS RECORDED ONLY WHEN EVERY INPUT IT STACKS EXISTS: a
        # sheet built around a failed tile would otherwise carry a key that says the
        # tile was in it, and read current after the tile is repaired.
        for fn, v, how in plan_derived():
            src = derived_inputs(fn, v, how) or []
            if (
                fn in want
                and os.path.isfile(os.path.join(out_dir, fn))
                and all(os.path.isfile(os.path.join(out_dir, s)) for s in src)
            ):
                done.add(fn)
        AK.record_outputs("screens", {fn: keys[fn]["key"] for fn in done})
    return written, sheets


def index_md():
    """The screens directory's own README — generated with the pictures, never edited."""
    lines = [
        "# Screens — every surface, every variant, through the theme",
        "",
        "GENERATED by `catalog/library/render_screens.py`; do not edit. Each picture is the",
        "emitted surface rendered by Qt under the KDE platform theme with that variant's",
        "colour scheme applied in a private kdeglobals — what the desktop draws, not a mock-up.",
        "`scripts/opa_gate.py screens` holds every still to exist, be non-blank and sit on its",
        "variant's ground.",
        "",
        "![all six variants](strip.png)",
        "",
    ]
    for v in VARIANTS:
        lines += [f"## {v}", "", f"![{v}](sheet-{v}.png)", ""]
        for name, _how in STILLS:
            lines.append(f"- `{name}-{v}.png`")
        for name, how in ANIMATIONS:
            what = (
                "the widget scrolling"
                if how[1] == "animate"
                else "the field scrolling down a 16-row Unifont cell and back (the viewport)"
            )
            lines.append(
                f"- `{name}-{v}.png` — APNG, {what} (S5: never tears; S6: loops)"
            )
        lines.append("")
        lines += [
            f"![{v} scrolling](marquee-anim-{v}.png)",
            "",
            f"![{v} viewport](pinholes-anim-{v}.png)",
            "",
        ]
    return "\n".join(lines)


def contact_sheets(out_dir=SCREENS, only=None):
    """One sheet per variant and the strip; the drawing lives in screens_sheets so it
    keys only the derived outputs (W61)."""
    import screens_sheets as SS

    return SS.contact_sheets(out_dir, VARIANTS, sheet_tiles, only=only)


def measure(out_dir=SCREENS):
    """Per planned still: exists, size, modal colour, the variant's ground — the facts
    policy/screens.rego decides on."""
    from PIL import Image

    import make_preview as MP
    import make_wallpaper_live as WL

    rows = []
    for fn, v, _how in plan():
        p = os.path.join(out_dir, fn)
        # two honest grounds per variant: the harness window's (parse_scheme's
        # "ground", the Window background) and the View background a bound
        # surface draws as its own void
        row = {
            "file": fn,
            "variant": v,
            "exists": os.path.isfile(p),
            "grounds": [
                MP.parse_scheme(v)["ground"],
                "#{:02x}{:02x}{:02x}".format(*WL.colors_for(v)[0]),
            ],
        }
        if row["exists"]:
            im = Image.open(p).convert("RGB")
            colours = im.getcolors(im.width * im.height)
            _n, modal = max(colours)
            row.update(
                width=im.width,
                height=im.height,
                modal="#{:02x}{:02x}{:02x}".format(*modal),
                distinct=len(colours),
            )
        rows.append(row)
    anims = []
    for fn, v, how in plan_animations():
        p = os.path.join(out_dir, fn)
        row = {"file": fn, "variant": v, "exists": os.path.isfile(p)}
        if row["exists"]:
            row.update(
                animation_facts(
                    p,
                    MP.parse_scheme(v)["phosphor"],
                    "#{:02x}{:02x}{:02x}".format(*WL.colors_for(v)[0]),
                    axis=how[2],
                )
            )
            row["logged_steps"] = logged_steps(
                p
            )  # null: no harness log, the policy uses the image fit
        anims.append(row)
    return {"screens": rows, "animations": anims, "dir": out_dir}


def _hex(s):
    return tuple(int(s[i : i + 2], 16) for i in (1, 3, 5))


def lit_columns(frame, lit, ground):
    """Per column, how many LIT pixels: nearer the phosphor than the ground by a
    factor — the ghost field composites at alpha 0.566, near the midpoint, so a
    plain "nearer lit" counts it; lit is within a quarter (squared) of the ground
    distance, which the ghost's 0.434 remainder is not. A COUNT, not a flag: the
    dots scroll at pixel positions over a 4 px pitch, so an edge column's class
    flips with the phase; weighted by pixels that flip is small against a tear."""
    px = frame.load()
    cols = [0] * frame.width
    for x in range(frame.width):
        for y in range(frame.height):
            r, g, b = px[x, y]
            dl = (r - lit[0]) ** 2 + (g - lit[1]) ** 2 + (b - lit[2]) ** 2
            dg = (r - ground[0]) ** 2 + (g - ground[1]) ** 2 + (b - ground[2]) ** 2
            if 4 * dl < dg:
                cols[x] += 1
    return cols


def best_shift(prev, cur, max_shift):
    """The left shift k (0..max_shift) under which `cur` best matches `prev`, and
    the mismatch under it — sum over columns c in [0, w-k) of |prev[c+k] - cur[c]|
    in lit pixels. The k columns entering at the right are new content and are
    not compared."""
    best = (None, None)
    for k in range(max_shift + 1):
        mism = sum(abs(prev[c + k] - cur[c]) for c in range(len(cur) - k))
        if best[1] is None or mism < best[1]:
            best = (k, mism)
    return best


def _litness(frame, lit, ground):
    """Per pixel, the projection onto ground→lit clamped to [0, 1], as a 2-D list [y][x]."""
    px = frame.load()
    lg = [l - g for l, g in zip(lit, ground)]
    norm = sum(v * v for v in lg) or 1
    return [
        [
            max(
                0.0,
                min(
                    1.0, sum((px[x, y][i] - ground[i]) * lg[i] for i in range(3)) / norm
                ),
            )
            for x in range(frame.width)
        ]
        for y in range(frame.height)
    ]


def pip_centres(frame, lit, ground, axis="x"):
    """The x of every pip column (axis "x") or the y of every pip row (axis "y"),
    from the picture alone: lines whose pixels sit off the ground (the field's
    ghost pips, lit or not) form periodic bumps; a bump's peak is a pip's centre."""
    L = _litness(frame, lit, ground)
    if axis == "x":
        prof = [sum(L[y][x] for y in range(frame.height)) for x in range(frame.width)]
    else:
        prof = [sum(L[y]) for y in range(frame.height)]
    return [
        i
        for i in range(1, len(prof) - 1)
        if prof[i] > 0 and prof[i] >= prof[i - 1] and prof[i] > prof[i + 1]
    ]


def pip_profile(frame, centres, lit, ground, floor, axis="x"):
    """Per pip column (or row), its brightness ABOVE the ghost floor in [0, 1]: the
    mean lit-ness along the line, the floor removed."""
    L = _litness(frame, lit, ground)
    out = []
    for c in centres:
        if axis == "x":
            s = sum(L[y][c] for y in range(frame.height)) / frame.height
        else:
            s = sum(L[c]) / frame.width
        out.append(max(0.0, (s - floor) / (1 - floor)) if floor < 1 else 0.0)
    return out


FRACTIONS = tuple(i / 8 for i in range(8))


def spectral_lines(profiles):
    """W173: the scroll's brightness SPECTRUM. Per pip, its brightness over the run is
    a time series; its DFT's power, summed over pips, with the DC term dropped, is the
    run's temporal spectrum. Returns (dominant period in frames, that line's share of
    the non-DC power, total non-DC power, the period-2 line's share). A see-saw
    between two states (a scroll alternating whole and half pips) concentrates power
    at period 2.
    WEAKNESS: a run of fewer than 4 frames has no spectrum (None, None, 0)."""
    import numpy as np

    if len(profiles) < 4 or not profiles[0]:
        return None, None, 0.0, None
    series = np.array(profiles, dtype=float)  # frames x pips
    series = series - series.mean(axis=0)
    power = (np.abs(np.fft.rfft(series, axis=0)) ** 2).sum(axis=1)[1:]  # drop DC
    total = float(power.sum())
    if total <= 0:
        return None, None, 0.0, None
    i = int(power.argmax())
    period = len(profiles) / (i + 1)
    # ⚑ THE SEE-SAW LINE, NOT THE STRONGEST ONE (measured 2026-10-01): the strongest
    # line on every real run is period = run length (the text entering and leaving
    # once, ~1/3 of the power), which says nothing about a whole/half alternation.
    # That alternation lives at period 2 frames: the highest bin of the rfft.
    n = len(profiles)
    p2 = (
        round(float(power[n // 2 - 1]) / total, 4)
        if n % 2 == 0
        else round(float(power[-1]) / total, 4)
    )
    return round(period, 3), round(float(power[i]) / total, 4), round(total, 3), p2


def prime_fields(profiles):
    """The two fields an animation's record carries for W175: how even the power is over the prime periods
    (1.0 even) and the prime that holds the most with its share; both None when there is no spectrum."""
    got = prime_lines(profiles)
    return {
        "prime_evenness": got["evenness"] if got else None,
        "prime_peak": list(got["peak"]) if got else None,
    }


def primes_upto(n):
    """The primes <= n, ascending."""
    return [p for p in range(2, n + 1) if all(p % q for q in range(2, int(p**0.5) + 1))]


def prime_lines(profiles):
    """W175 (operator 2026-10-01, lower priority): the brightness power at the PRIME periods 2, 3, 5, 7, 11 ...
    up to half the run, "not powers of 2 fft, but prime lines". Per pip, its brightness over the frames is a
    series; the power at period p is |sum_t s_t exp(-2 pi i t / p)| squared, a direct DFT at the frequency
    1/p, so a period that is no bin of the run's FFT is still read exactly; summed over pips, mean removed.

    Returns {"lines": {p: share}, "evenness": spectral flatness, "peak": (p, share)}: the shares sum to 1
    over the primes read, `evenness` is the geometric over the arithmetic mean of the line powers (1.0 is
    perfectly even, 0.0 is a line with no power at all), `peak` the prime holding the most. None when the run
    has fewer than 4 frames, fewer than two primes fit, or nothing varies.
    WEAKNESS: it reads the lines that exist in the series, not whether they are the RIGHT ones: an even
    spread is a property of the scroll's timing, and this measures what a render did, not what it was built
    to do. A text's own spatial spectrum rides on every line, so the figure judges a whole run."""
    import numpy as np

    if len(profiles) < 4 or not profiles[0]:
        return None
    primes = primes_upto(len(profiles) // 2)
    if len(primes) < 2:
        return None
    series = np.array(profiles, dtype=float)
    series = series - series.mean(axis=0)
    t = np.arange(len(profiles))
    powers = []
    for p in primes:
        basis = np.exp(-2j * np.pi * t / p)
        powers.append(float((np.abs(basis @ series) ** 2).sum()))
    total = sum(powers)
    if total <= 0:
        return None
    mean = total / len(powers)
    geo = float(np.exp(np.mean(np.log(np.maximum(powers, 1e-300)))))
    flat = geo / mean if min(powers) > 0 else 0.0
    peak = max(range(len(primes)), key=lambda i: powers[i])
    return {
        "lines": {p: round(w / total, 4) for p, w in zip(primes, powers, strict=True)},
        "evenness": round(flat, 4),
        "peak": (primes[peak], round(powers[peak] / total, 4)),
    }


def best_pip_shift(prev, cur, max_shift, both_ways=False):
    """The shift in PIPS (whole k plus a fraction f) under which `cur` best matches
    `prev` moved left — cur[c] ≈ (1-f)·prev[c+k] + f·prev[c+k+1] — and the
    mismatch under it, in brightness. A graded field never moves its pips; their
    brightness moves, by fractions of a pip per frame. The k entering pips at the
    edge are new content and are not compared. `both_ways` admits negative k (a
    scroll that reverses, like the viewport's ping-pong); the marquee's is one-way,
    where a rightward move is a restart."""
    best = (None, None, None)
    n = len(cur)
    for k in range(-max_shift if both_ways else 0, max_shift + 1):
        # EIGHTHS of a pip (W173): at quarters a slow mover's 1/8-pip step read as whole
        for f in FRACTIONS:
            mism = 0.0
            lo, hi = max(0, -k), n - max(0, k) - 1
            for c in range(lo, hi):
                mism += abs(cur[c] - ((1 - f) * prev[c + k] + f * prev[c + k + 1]))
            if best[2] is None or mism < best[2]:
                best = (k, f, mism)
    return best


def logged_steps(path):
    """W208/W209: the widget's OWN per-frame steps in pips, from the APNG's `el-frames` text
    chunk (board x per grabbed frame and px per pip, written by check_marquee_live.animate).
    None when the picture carries no log (rendered before W208, or not harness-driven).
    Frame 0 is the empty-board bookend and is not a step.

    ⚑ THIS IS WHAT THE HARNESS DID, NOT A FIT OF WHAT IT DREW. Measured 2026-10-02: the
    marquee-anim log is 60 steps of exactly +2.75 pip, while the linear-blend image fit (below)
    reported tears on the same run - the fit mis-reads the coverage-graded aperture (W207)."""
    from PIL import Image

    raw = getattr(Image.open(path), "text", {}).get("el-frames")
    if not raw:
        return None
    log = json.loads(raw)
    pitch, xs = log.get("pitch"), [f["x"] for f in log.get("frames", [])[1:]]
    if not pitch or len(xs) < 2:
        return None
    return [(xs[i] - xs[i + 1]) / pitch for i in range(len(xs) - 1)]


def pip_lattice(frame, lit, ground):
    """(cols, rows): the pip centres in both axes, with the spurious lines removed.

    pip_centres finds peaks of the line profile, and a stray peak between two pips (or past the board's
    edge) is a 'row' with no pip on it: EL-Azure and EL-Amber read 9 and 10 rows of an 8-row board. A
    true line crosses ghost pips all along it, so a line is kept when its mean lit-ness over the OTHER
    axis's centres is at least half the best line's."""
    cols = pip_centres(frame, lit, ground, "x")
    rows = pip_centres(frame, lit, ground, "y")
    L = _litness(frame, lit, ground)
    if not cols or not rows:
        return cols, rows
    col_mean = [sum(L[r][c] for r in rows) / len(rows) for c in cols]
    row_mean = [sum(L[r][c] for c in cols) / len(cols) for r in rows]
    cols = [c for c, m in zip(cols, col_mean) if m >= 0.5 * max(col_mean)]
    rows = [r for r, m in zip(rows, row_mean) if m >= 0.5 * max(row_mean)]
    return cols, rows


def pip_values(frame, cols, rows, lit, ground, floor):
    """Each pip's brightness above the ghost floor in [0, 1], one value per (row, column)
    centre of the lattice: the lit-ness AT the pip, not averaged along its column, so a
    stroke that straddles two pips reads as two partial pips and one that sits whole
    reads as one full one."""
    L = _litness(frame, lit, ground)
    if floor >= 1:
        return [0.0 for _r in rows for _c in cols]
    return [max(0.0, (L[r][c] - floor) / (1 - floor)) for r in rows for c in cols]


def whole_share(values, inked=0.1, whole=0.9):
    """(share, n): of the pips INKED above the floor (value over `inked`), the share that
    are WHOLE (value at or over `whole`); 1.0 is every stroke sitting whole on the pips,
    low is graded edges. (None, 0) when no pip is inked, which is the empty board, not a
    score of zero."""
    ink = [v for v in values if v > inked]
    if not ink:
        return None, 0
    return sum(v >= whole for v in ink) / len(ink), len(ink)


def animation_facts(path, lit_hex, ground_hex, tolerance=0.5, axis="x"):
    """A scroll is a LEFT SHIFT OF THE PIPS' BRIGHTNESS: the field never moves (W34a,
    the pips are the hardware); the backdrop behind it does, by a fraction of a pip
    per frame, so each pip's brightness is the previous frame's profile sampled a
    fraction further along (W54's aperture relation). Per adjacent pair, the best
    shift (whole pips + a quarter-pip fraction, ≤ a quarter of the board) and the
    brightness mismatch under it over the larger frame's total brightness; a pair
    over `tolerance` is a TEAR — a rebuilt board, a restart, a frame out of order.
    The ring's wrap IS a left shift and passes. The pip columns and the ghost floor
    are read from the FIRST frame (the empty board) — the measurement needs no
    pitch from the emitter. WEAKNESS: a pair with no brightness above the floor in
    either frame (the board empty) has nothing to compare and is skipped, not
    judged; the tolerance is re-measured on the graded field (see COTYPE s120).
    Before W54 this compared pixel columns under a whole-pixel shift, which is the
    f = 0 special case a snapping field satisfies.

    WHOLE ON THE PIPS (W174, reported not required): `whole_best` is the frame where the
    largest share of the inked pips sit whole (value >= 0.9 above the per-pip ghost floor),
    chosen among frames with at least half the most inked pips any frame has (a handful of
    pips scores 1.0 by chance); `whole_median` is the share over all scored frames.
    WEAKNESS: the `phase` is the profile fit's scroll position mod one pip, and it differs
    between variants for the SAME frame (measured 0.25, 0.0, 0.375 at marquee frame 13), so
    only the frame index is reliable; the lattice is detected from peaks and filtered by
    ghost lit-ness (pip_lattice), with no selftest arm of its own; an empty board scores
    None, not zero."""
    from PIL import Image, ImageSequence

    lit, ground = _hex(lit_hex), _hex(ground_hex)
    im = Image.open(path)
    width = im.width
    profiles, rgb_first, rgb_last, centres, floor = [], None, None, None, 0.0
    grid_c, grid_r, scores, pip_floor = [], [], [], 0.0
    for fr in ImageSequence.Iterator(im):
        rgb = fr.convert("RGB")
        if rgb_first is None:
            rgb_first = rgb
            centres = pip_centres(rgb, lit, ground, axis)
            # the floor: the ghost's lit-ness where nothing is lit. Along x the empty
            # bookend frame gives it; along y (the viewport, whose first frame is
            # not empty) the least-lit pip line does
            raw = pip_profile(rgb, centres, lit, ground, 0.0, axis)
            floor = ((sum(raw) / len(raw)) if axis == "x" else min(raw)) if raw else 0.0
            # the pip lattice in BOTH axes, for the per-pip reading below. ⚑ ITS OWN FLOOR: the profile
            # floor above is a mean down a whole column, gaps between pips included, so a ghost pip read
            # AT ITS CENTRE sits well over it and the whole board read as inked (840 of 840, measured)
            grid_c, grid_r = pip_lattice(rgb, lit, ground)
            vals0 = pip_values(rgb, grid_c, grid_r, lit, ground, 0.0)
            if vals0:
                pip_floor = (sum(vals0) / len(vals0)) if axis == "x" else min(vals0)
        profiles.append(pip_profile(rgb, centres, lit, ground, floor, axis))
        scores.append(
            whole_share(pip_values(rgb, grid_c, grid_r, lit, ground, pip_floor))
        )
        rgb_last = rgb
    shifts, tears, phases, acc = [], [], {0: 0.0}, 0.0
    for i in range(len(profiles) - 1):
        prev, cur = profiles[i], profiles[i + 1]
        total = max(sum(prev), sum(cur))
        if total < 0.5:
            continue
        k, f, mism = best_pip_shift(
            prev, cur, max(1, len(centres) // 4), both_ways=(axis == "y")
        )
        shifts.append(k + f)
        acc += k + f
        phases[i + 1] = acc % 1.0
        if mism > tolerance * total:
            tears.append(
                {
                    "frame": i + 1,
                    "shift": k + f,
                    "mismatch": round(mism, 2),
                    "total": round(total, 2),
                }
            )
    # a seamless loop: the run starts and ends on the same picture (the empty board).
    # Compared from the one forward pass — re-seeking an APNG in PIL re-composites.
    seamless = rgb_first is not None and rgb_first.tobytes() == rgb_last.tobytes()
    frac = [s for s in shifts if s != int(s)]
    period, line_share, power, p2 = spectral_lines(profiles)
    # ⚑ WHOLE ON THE PIPS (W174): per frame, of the pips inked above the floor, the share that are
    # whole. Reported, not required: whether a scroll MUST pass through an alignment where every
    # stroke sits whole is an operator decision. `phase` is the scroll's cumulative shift mod one pip
    # at that frame (pairs with nothing to compare add no shift, so a phase after one is approximate).
    scored = [(s, i, n) for i, (s, n) in enumerate(scores) if s is not None]
    # a frame with a handful of inked pips scores 1.0 by chance (measured: a Lit pinholes frame 2), so the
    # best frame is chosen among those with at least half the most inked pips any frame has
    top_n = max((n for _s, _i, n in scored), default=0)
    full = [t for t in scored if t[2] * 2 >= top_n]
    best = max(full, key=lambda t: (t[0], -t[1])) if full else None
    ordered = sorted(s for s, _i, _n in scored)
    whole = (
        {
            "frame": best[1],
            "score": round(best[0], 4),
            "inked": best[2],
            "phase": round(phases[best[1]], 3) if best[1] in phases else None,
        }
        if best
        else None
    )
    return {
        "whole_best": whole,
        "whole_median": round(ordered[len(ordered) // 2], 4) if ordered else None,
        "whole_frames": len(scored),
        "frames": len(profiles),
        "width": width,
        "axis": axis,
        "pips": len(centres),
        "floor": round(floor, 3),
        "shifts": shifts,
        "tears": tears,
        "seamless": seamless,
        "fractional_share": round(len(frac) / len(shifts), 4) if shifts else None,
        "dominant_period": period,
        "dominant_line_share": line_share,
        "spectral_power": power,
        "period2_share": p2,
        **prime_fields(profiles),
    }


def selftest():
    """W96's falsifier: a key moves exactly when something that shapes the PIXELS
    moves. Each arm perturbs one code file's digest (check_action_key.digest_rel,
    monkeypatched — no file is edited, no render runs) and compares output_keys().

      (1) render_qml.py only BUILDS the job (render -> run_stager -> QT.run; nothing
          touches the png after qml writes it), and the job is already in the key as
          job0:* bytes — so perturbing it must leave every render_qml still's key
          unchanged. ⚑ FAILS on the whole-file code term (W96's finding).
      (2) a SegmentChar-drawn still must name SegmentChar among its job inputs, so a
          template edit still reaches it through the job bytes (structural, not a
          perturbation: job_inputs digests the staged bytes, not digest_rel).
      (3) check_marquee_live.animate assembles the APNG's frame delays AFTER qml —
          perturbing that file must move every marquee-anim key.

    WEAKNESS: arm (2) checks that the input is NAMED, not that its digest moves
    the key; key_over over a named input is what makes that follow."""
    import check_action_key as AK

    real = AK.digest_rel
    base = output_keys()["outputs"]

    def perturbed(target):
        AK.digest_rel = lambda rel: (
            ("perturbed:" + real(rel)) if rel == target else real(rel)
        )
        try:
            return output_keys()["outputs"]
        finally:
            AK.digest_rel = real

    ok, n = 0, 0
    rq = perturbed("scripts/render_qml.py")
    stills = [fn for fn, _v, how in plan() if how[0] == "render_qml"]
    moved = [fn for fn in stills if rq[fn]["key"] != base[fn]["key"]]
    n += 1
    ok += not moved
    print(
        f"  {'ok  ' if not moved else 'FAIL'} (1) render_qml.py edit: {len(moved)} of {len(stills)} "
        f"render_qml still key(s) moved (want 0)"
    )
    seg = [fn for fn in stills if fn.startswith(("clock-", "wallpaper-live-"))]
    named = [fn for fn in seg if any("SegmentChar" in k for k in base[fn]["inputs"])]
    n += 1
    ok += bool(seg) and len(named) == len(seg)
    print(
        f"  {'ok  ' if seg and len(named) == len(seg) else 'FAIL'} (2) SegmentChar named in "
        f"{len(named)} of {len(seg)} clock/live-wallpaper still(s)' job inputs (want all, >0)"
    )
    ml = perturbed("scripts/check_marquee_live.py")
    anims = [fn for fn, _v, how in plan_animations() if how[0] == "marquee"]
    moved = [fn for fn in anims if ml[fn]["key"] != base[fn]["key"]]
    n += 1
    ok += bool(anims) and len(moved) == len(anims)
    print(
        f"  {'ok  ' if anims and len(moved) == len(anims) else 'FAIL'} (3) check_marquee_live.py edit: "
        f"{len(moved)} of {len(anims)} marquee-anim key(s) moved (want all, >0)"
    )
    # (4)-(6) W174, the whole-on-the-pips score: it must SEE a stroke that straddles pips
    from PIL import Image

    lit_c, ground_c = (200, 100, 50), (10, 10, 10)
    frame = Image.new("RGB", (12, 12), ground_c)
    frame.putpixel((2, 2), lit_c)  # a pip fully lit
    frame.putpixel((6, 2), (105, 55, 30))  # a pip half lit: an edge between two pips
    vals = pip_values(frame, [2, 6, 10], [2], lit_c, ground_c, 0.0)
    arms = (
        (
            "(4) a whole stroke scores 1.0 over its inked pips",
            whole_share([1.0, 1.0, 0.95]),
            (1.0, 3),
        ),
        (
            "(5) a graded edge pip lowers it, and an unlit pip is not inked",
            whole_share([1.0, 0.5, 0.4, 0.0]),
            (1 / 3, 3),
        ),
        (
            "(6) an empty board has NO score (not zero)",
            whole_share([0.0, 0.05]),
            (None, 0),
        ),
        (
            "(7) pip_values reads the lit-ness AT each pip (full, half, none)",
            [round(v, 2) for v in vals],
            [1.0, 0.5, 0.0],
        ),
    )
    for label, got, want in arms:
        n += 1
        ok += got == want
        print(
            f"  {'ok  ' if got == want else 'FAIL'} {label}"
            + ("" if got == want else f": got {got!r} want {want!r}")
        )
    print(f"render_screens selftest: {ok}/{n}")
    return 0 if ok == n else 1


def main(argv):
    known = {
        "--list",
        "--json",
        "--outputs",
        "--keys",
        "--stale",
        "--all",
        "--selftest",
        "--whole",
        "--primes",
    }
    jobs = 1
    for a in argv[1:]:
        if a.startswith("--jobs=") and a[7:].isdigit() and int(a[7:]) > 0:
            jobs = int(a[7:])
        elif a not in known:
            print(f"render_screens: unknown flag {a!r}", file=sys.stderr)
            return 2
    # ⚑ NO GPU OPT-IN ANY MORE (W158, 2026-10-01). This process once set EL_QT_GPU=1 so
    # the screenshots could draw the bloom halo on the RHI, which reached the GPU
    # driver (the W73 crash vector). render_qml now draws its RHI on Mesa llvmpipe under
    # a private SIGKILLed kwin (qt_sandbox mesa=True, W108/W114), so the halo renders
    # with no GPU driver and no opt-in. Removing the variable changed every job's
    # environment, and so every screens key: the outputs were re-rendered (on Mesa).
    if "--selftest" in argv:
        return selftest()
    if "--keys" in argv:
        # ⚑ THE PER-OUTPUT KEYS, AS DATA (W61) — check_action_key's reader
        print(json.dumps(output_keys(), indent=1, sort_keys=True))
        return 0
    if "--stale" in argv:
        k = output_keys()
        if k["missing_host"]:
            print(
                f"render_screens: WITHHELD — host identity uncomputable: {k['missing_host']}",
                file=sys.stderr,
            )
            return 3
        st = stale(k["outputs"])
        for fn in st:
            print(f"  stale  {fn}")
        print(
            f"render_screens: {len(st)} of {len(plan_all())} declared output(s) stale"
        )
        return 0
    if "--list" in argv:
        for fn, _v, how in plan_all():
            print(f"{fn:36s} {how}")
        print(
            f"\nrender_screens: {len(plan_all())} declared output(s) — "
            f"{len(plan())} still(s), {len(plan_animations())} animation(s), "
            f"{len(plan_derived())} derived"
        )
        return 0
    if "--outputs" in argv:
        # ⚑ THE DECLARATION, AS DATA. A consumer asking "what does this action
        # produce" must not parse --list's columns: a reader keyed on a column
        # width reports its own blind spot as a fact about the plan.
        print(
            json.dumps(
                {
                    "dir": os.path.relpath(SCREENS, ROOT),
                    "outputs": [
                        {"file": fn, "variant": v, "how": list(how)}
                        for fn, v, how in plan_all()
                    ],
                },
                indent=1,
            )
        )
        return 0
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--primes" in argv:
        # ⚑ W175: how evenly each scroll's brightness power sits on the prime periods (1.0 even); the
        # prime holding the most and its share. Reported: the by-construction design is the card's next step.
        rows = [a for a in measure()["animations"] if a.get("exists")]
        for a in rows:
            pk = a.get("prime_peak")
            print(
                f"  {a['file']:34s} frames {a['frames']:3d} "
                + (
                    f"evenness {a['prime_evenness']:.4f}, peak prime {pk[0]} holds {pk[1]:.3f}"
                    if pk
                    else "no spectrum"
                )
            )
        print(
            f"render_screens --primes: {len(rows)} of {len(plan_animations())} animation(s) read"
        )
        return 0
    if "--whole" in argv:
        # ⚑ W174: does each scroll pass through the alignment where every stroke sits whole on the
        # pips? One line per animation; reported, not required (an operator decision).
        rows = [a for a in measure()["animations"] if a.get("exists")]
        for a in rows:
            w = a.get("whole_best")
            print(
                f"  {a['file']:34s} frames {a['frames']:3d} scored {a['whole_frames']:3d} "
                + (
                    f"best frame {w['frame']:3d} score {w['score']:.3f} of {w['inked']:3d} "
                    f"inked, phase {w['phase']}, median {a['whole_median']:.3f}"
                    if w
                    else "no pip is ever inked"
                )
            )
        print(
            f"render_screens --whole: {len(rows)} of {len(plan_animations())} animation(s) read"
        )
        return 0
    import render_qml as RQ

    if not os.path.exists(RQ.QML):
        print(f"render_screens: SKIP — {RQ.QML} is not installed", file=sys.stderr)
        return 0
    # ⚑ INCREMENTAL BY DEFAULT (W61): only the outputs whose key moved (or that are
    # absent, or were never recorded) are rendered. --all renders every one.
    k = output_keys()
    if k["missing_host"]:
        print(
            f"render_screens: WITHHELD — host identity uncomputable: {k['missing_host']}",
            file=sys.stderr,
        )
        return 3
    only = None if "--all" in argv else stale(k["outputs"])
    written, sheets = render_all(only=only, keys=k["outputs"], jobs=jobs)
    rendered = [
        fn for fn, _v, _h in plan() + plan_animations() if only is None or fn in only
    ]
    print(
        f"render_screens: {len(written)} of {len(rendered)} stale stills + animations rendered "
        f"({len(plan()) + len(plan_animations()) - len(rendered)} current, skipped), "
        f"{len(sheets)} sheets -> {SCREENS}"
    )
    return 0 if len(written) == len(rendered) else 1


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main(sys.argv))
