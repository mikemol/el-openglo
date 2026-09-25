#!/usr/bin/env python3
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
VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit", "EL-Amber", "EL-Amber-Lit")

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
ANIMATIONS = (("marquee-anim", ("marquee", "animate", "x")),
              ("pinholes-anim", ("aperture-text", "scroll-y", "y")))
# ⚑ THE GLYPH MOVES, THEN IT IS PIXELATED — NOT THE OTHER WAY (operator,
# 2026-09-22, seeing pinholes-anim: "it looks like the pixelation of the glyphs is
# calculated, and then the pixelated glyphs are moved up and down the grid. What we
# want instead is for the glyphs to move and the pixelation RECALCULATED, so we get
# subpixel rendering on a temporal axis"). These steps were whole PIPS, so every
# frame sampled an identically-aligned band and the field just translated a fixed
# pattern. The backdrop carries `scale` pixels per pip, so a step of 1/scale is a
# real re-sampling — and it is also the Nyquist bound: the backdrop pixel is the
# finest feature the aperture can resolve, so a finer step adds nothing.
VIEWPORT_SUBSTEPS = 4                                          # = ApertureField.scale
VIEWPORT_STEPS = ([i / VIEWPORT_SUBSTEPS for i in range(0, 8 * VIEWPORT_SUBSTEPS + 1)]
                  + [i / VIEWPORT_SUBSTEPS for i in range(8 * VIEWPORT_SUBSTEPS - 1, -1, -1)])
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
    import render_qml as RQ
    import check_marquee_live as ML
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
    grain — a helper both stager modules import (qt_sandbox, theme_probe) keys
    every output that reaches it, which is correct but coarse; and this file is
    keyed whole, so a comment in it still moves every output."""
    import check_action_key as AK
    sentinel = "/@OUT@"
    here = os.path.relpath(os.path.abspath(__file__), ROOT)
    host, missing = AK.host_inputs()
    keys, code_files = {}, {here}
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
            seed = os.path.relpath(stage.__code__.co_filename, ROOT)
            code = sorted(set(AK.runner_code([seed])) | {here})
            code_files.update(code)
            for rel in code:
                inputs[f"code:{rel}"] = AK.digest_rel(rel)
        inputs.update(host)
        keys[fn] = {"key": AK.key_over(inputs), "inputs": inputs}
    # a derived output runs only this file's sheet code over tiles already keyed
    code_inputs = {f"code:{here}": AK.digest_rel(here)}
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
    return [fn for fn in (f for f, _v, _h in plan_all())
            if rec.get(fn) != keys[fn]["key"] or not os.path.isfile(os.path.join(SCREENS, fn))]


def animate_viewport(variant, out_apng):
    """The text probe rendered once per band of its backdrop (offsetRows 0..8..0),
    assembled as an APNG: the field scrolling down a 16-row Unifont cell and back.
    Returns the frame count.

    ⚑ ONE qml PROCESS FOR ALL 65 FRAMES (render speed #2): render_qml.render_frames
    steps offsetRows through the probe's plasmoid.configuration BINDING and grabs
    each step. It was 65 processes, each paying the startup floor for one grab
    (measured on EL-Openglo: 37.7 s CPU old, see catalog/render-speed.md). The
    field's offsetY is read back per frame and must equal step x scale — a frame
    whose binding did not deliver its step is refused, not assembled. A frame
    count short of the plan is also refused (0): the old loop silently dropped a
    failed step (64 of 65 once, measured) and the ping-pong was then no longer
    symmetric."""
    import tempfile
    import render_qml as RQ
    from PIL import Image
    want = [s * VIEWPORT_SUBSTEPS for s in VIEWPORT_STEPS]
    with tempfile.TemporaryDirectory() as td:
        # the same backend as the stills (rhi where the host has it): the frames
        # must look like the picture beside them
        s, w, h, key, steps, probe = VIEWPORT_JOB
        rc, err, seen = RQ.render_frames(s, variant, w, h, td, key, steps, probe)
        names = sorted(n for n in os.listdir(td) if n.startswith("frame-"))
        if rc != 0 or seen != want or len(names) != len(VIEWPORT_STEPS):
            print(f"render_screens: pinholes-anim {variant} REFUSED — rc={rc}, {len(names)} of "
                  f"{len(VIEWPORT_STEPS)} frames, offsetY read back {seen!r}\n{err[-400:]}", file=sys.stderr)
            return 0
        ims = [Image.open(os.path.join(td, n)).convert("RGB") for n in names]
    ims[0].save(out_apng, format="PNG", save_all=True, append_images=ims[1:], duration=VIEWPORT_FRAME_MS, loop=0)
    return len(ims)


def render_one(v, how, out):
    """Produce one planned still or animation at `out`; its jobs are stagers()'s."""
    import render_qml as RQ
    import check_marquee_live as ML
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
    except RuntimeError as e:          # a harness that reported no RESULT: a hole, named
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
        done_ok = list(ex.map(lambda t: render_one(t[1], t[2], os.path.join(out_dir, t[0])), todo))
    written += [os.path.join(out_dir, fn) for (fn, _v, _h), ok in zip(todo, done_ok) if ok]
    sheets = contact_sheets(out_dir, only=want)
    if "README.md" in want:
        open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8").write(index_md())
    if keys is not None:
        import check_action_key as AK
        done = {os.path.basename(p) for p in written}
        # ⚑ A DERIVED OUTPUT IS RECORDED ONLY WHEN EVERY INPUT IT STACKS EXISTS: a
        # sheet built around a failed tile would otherwise carry a key that says the
        # tile was in it, and read current after the tile is repaired.
        for fn, v, how in plan_derived():
            src = derived_inputs(fn, v, how) or []
            if fn in want and os.path.isfile(os.path.join(out_dir, fn)) and all(
                    os.path.isfile(os.path.join(out_dir, s)) for s in src):
                done.add(fn)
        AK.record_outputs("screens", {fn: keys[fn]["key"] for fn in done})
    return written, sheets


def index_md():
    """The screens directory's own README — generated with the pictures, never edited."""
    lines = ["# Screens — every surface, every variant, through the theme", "",
             "GENERATED by `catalog/library/render_screens.py`; do not edit. Each picture is the",
             "emitted surface rendered by Qt under the KDE platform theme with that variant's",
             "colour scheme applied in a private kdeglobals — what the desktop draws, not a mock-up.",
             "`scripts/opa_gate.py screens` holds every still to exist, be non-blank and sit on its",
             "variant's ground.", "",
             "![all six variants](strip.png)", ""]
    for v in VARIANTS:
        lines += [f"## {v}", "", f"![{v}](sheet-{v}.png)", ""]
        for name, _how in STILLS:
            lines.append(f"- `{name}-{v}.png`")
        for name, how in ANIMATIONS:
            what = "the widget scrolling" if how[1] == "animate" else "the field scrolling down a 16-row Unifont cell and back (the viewport)"
            lines.append(f"- `{name}-{v}.png` — APNG, {what} (S5: never tears; S6: loops)")
        lines.append("")
        lines += [f"![{v} scrolling](marquee-anim-{v}.png)", "", f"![{v} viewport](pinholes-anim-{v}.png)", ""]
    return "\n".join(lines)


def contact_sheets(out_dir=SCREENS, only=None):
    """One sheet per variant (its surfaces stacked) and one strip of the six sheets;
    with `only`, just the sheets (and strip) named in it."""
    from PIL import Image, ImageDraw
    sheets = []
    per_variant = []
    for v in VARIANTS:
        if only is not None and f"sheet-{v}.png" not in only:
            if "strip.png" in only and os.path.isfile(os.path.join(out_dir, f"sheet-{v}.png")):
                per_variant.append(Image.open(os.path.join(out_dir, f"sheet-{v}.png")).convert("RGB"))
            continue
        tiles = [Image.open(os.path.join(out_dir, t)).convert("RGB")
                 for t in sheet_tiles(v) if os.path.isfile(os.path.join(out_dir, t))]
        if not tiles:
            continue
        w = max(t.width for t in tiles) + 16
        h = sum(t.height for t in tiles) + 8 * (len(tiles) + 1) + 20
        sheet = Image.new("RGB", (w, h), tiles[-1].getpixel((0, 0)))
        d = ImageDraw.Draw(sheet)
        d.text((8, 4), v, fill=tiles[0].getpixel((tiles[0].width // 2, tiles[0].height // 2)))
        y = 20
        for t in tiles:
            sheet.paste(t, (8, y))
            y += t.height + 8
        p = os.path.join(out_dir, f"sheet-{v}.png")
        sheet.save(p)
        sheets.append(p)
        per_variant.append(sheet)
    if per_variant and (only is None or "strip.png" in only):
        strip = Image.new("RGB", (sum(s.width for s in per_variant) + 8 * (len(per_variant) + 1),
                                  max(s.height for s in per_variant) + 16), (0, 0, 0))
        x = 8
        for s in per_variant:
            strip.paste(s, (x, 8))
            x += s.width + 8
        p = os.path.join(out_dir, "strip.png")
        strip.save(p)
        sheets.append(p)
    return sheets


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
        row = {"file": fn, "variant": v, "exists": os.path.isfile(p),
               "grounds": [MP.parse_scheme(v)["ground"], "#%02x%02x%02x" % WL.colors_for(v)[0]]}
        if row["exists"]:
            im = Image.open(p).convert("RGB")
            colours = im.getcolors(im.width * im.height)
            n, modal = max(colours)
            row.update(width=im.width, height=im.height, modal="#%02x%02x%02x" % modal,
                       distinct=len(colours))
        rows.append(row)
    anims = []
    for fn, v, how in plan_animations():
        p = os.path.join(out_dir, fn)
        row = {"file": fn, "variant": v, "exists": os.path.isfile(p)}
        if row["exists"]:
            row.update(animation_facts(p, MP.parse_scheme(v)["phosphor"], "#%02x%02x%02x" % WL.colors_for(v)[0],
                                       axis=how[2]))
        anims.append(row)
    return {"screens": rows, "animations": anims, "dir": out_dir}


def _hex(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


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
    return [[max(0.0, min(1.0, sum((px[x, y][i] - ground[i]) * lg[i] for i in range(3)) / norm))
             for x in range(frame.width)] for y in range(frame.height)]


def pip_centres(frame, lit, ground, axis="x"):
    """The x of every pip column (axis "x") or the y of every pip row (axis "y"),
    from the picture alone: lines whose pixels sit off the ground (the field's
    ghost pips, lit or not) form periodic bumps; a bump's peak is a pip's centre."""
    L = _litness(frame, lit, ground)
    if axis == "x":
        prof = [sum(L[y][x] for y in range(frame.height)) for x in range(frame.width)]
    else:
        prof = [sum(L[y]) for y in range(frame.height)]
    return [i for i in range(1, len(prof) - 1)
            if prof[i] > 0 and prof[i] >= prof[i - 1] and prof[i] > prof[i + 1]]


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
        for f in (0.0, 0.25, 0.5, 0.75):
            mism = 0.0
            lo, hi = max(0, -k), n - max(0, k) - 1
            for c in range(lo, hi):
                mism += abs(cur[c] - ((1 - f) * prev[c + k] + f * prev[c + k + 1]))
            if best[2] is None or mism < best[2]:
                best = (k, f, mism)
    return best


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
    f = 0 special case a snapping field satisfies."""
    from PIL import Image, ImageSequence
    lit, ground = _hex(lit_hex), _hex(ground_hex)
    im = Image.open(path)
    width = im.width
    profiles, rgb_first, rgb_last, centres, floor = [], None, None, None, 0.0
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
        profiles.append(pip_profile(rgb, centres, lit, ground, floor, axis))
        rgb_last = rgb
    shifts, tears = [], []
    for i in range(len(profiles) - 1):
        prev, cur = profiles[i], profiles[i + 1]
        total = max(sum(prev), sum(cur))
        if total < 0.5:
            continue
        k, f, mism = best_pip_shift(prev, cur, max(1, len(centres) // 4), both_ways=(axis == "y"))
        shifts.append(k + f)
        if mism > tolerance * total:
            tears.append({"frame": i + 1, "shift": k + f, "mismatch": round(mism, 2), "total": round(total, 2)})
    # a seamless loop: the run starts and ends on the same picture (the empty board).
    # Compared from the one forward pass — re-seeking an APNG in PIL re-composites.
    seamless = rgb_first is not None and rgb_first.tobytes() == rgb_last.tobytes()
    return {"frames": len(profiles), "width": width, "axis": axis, "pips": len(centres), "floor": round(floor, 3),
            "shifts": shifts, "tears": tears, "seamless": seamless}


def main(argv):
    known = {"--list", "--json", "--outputs", "--keys", "--stale", "--all"}
    jobs = 1
    for a in argv[1:]:
        if a.startswith("--jobs=") and a[7:].isdigit() and int(a[7:]) > 0:
            jobs = int(a[7:])
        elif a not in known:
            print(f"render_screens: unknown flag {a!r}", file=sys.stderr)
            return 2
    # ⚑ THE GPU OPT-IN IS DECLARED HERE, NOT REMEMBERED (operator ruling 2026-09-22,
    # W73): every Qt spawn runs headless on the software scene graph by default, and
    # MultiEffect's bloom halo draws NOTHING there. The screenshots are the one place
    # the halo must show, so this process — and only this one — opts into the RHI.
    # It still gets no core and no DrKonqi from qt_sandbox, but it DOES reach the GPU
    # driver: the vector W73 closed for every test. Set BEFORE --keys, because the
    # opt-in is part of every job's environment and so of every key.
    os.environ.setdefault("EL_QT_GPU", "1")
    if "--keys" in argv:
        # ⚑ THE PER-OUTPUT KEYS, AS DATA (W61) — check_action_key's reader
        print(json.dumps(output_keys(), indent=1, sort_keys=True))
        return 0
    if "--stale" in argv:
        k = output_keys()
        if k["missing_host"]:
            print(f"render_screens: WITHHELD — host identity uncomputable: {k['missing_host']}", file=sys.stderr)
            return 3
        st = stale(k["outputs"])
        for fn in st:
            print(f"  stale  {fn}")
        print(f"render_screens: {len(st)} of {len(plan_all())} declared output(s) stale")
        return 0
    if "--list" in argv:
        for fn, _v, how in plan_all():
            print(f"{fn:36s} {how}")
        print(f"\nrender_screens: {len(plan_all())} declared output(s) — "
              f"{len(plan())} still(s), {len(plan_animations())} animation(s), "
              f"{len(plan_derived())} derived")
        return 0
    if "--outputs" in argv:
        # ⚑ THE DECLARATION, AS DATA. A consumer asking "what does this action
        # produce" must not parse --list's columns: a reader keyed on a column
        # width reports its own blind spot as a fact about the plan.
        print(json.dumps({"dir": os.path.relpath(SCREENS, ROOT),
                          "outputs": [{"file": fn, "variant": v, "how": list(how)}
                                      for fn, v, how in plan_all()]}, indent=1))
        return 0
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import render_qml as RQ
    if not os.path.exists(RQ.QML):
        print(f"render_screens: SKIP — {RQ.QML} is not installed", file=sys.stderr)
        return 0
    # ⚑ INCREMENTAL BY DEFAULT (W61): only the outputs whose key moved (or that are
    # absent, or were never recorded) are rendered. --all renders every one.
    k = output_keys()
    if k["missing_host"]:
        print(f"render_screens: WITHHELD — host identity uncomputable: {k['missing_host']}", file=sys.stderr)
        return 3
    only = None if "--all" in argv else stale(k["outputs"])
    written, sheets = render_all(only=only, keys=k["outputs"], jobs=jobs)
    rendered = [fn for fn, _v, _h in plan() + plan_animations() if only is None or fn in only]
    print(f"render_screens: {len(written)} of {len(rendered)} stale stills + animations rendered "
          f"({len(plan()) + len(plan_animations()) - len(rendered)} current, skipped), "
          f"{len(sheets)} sheets -> {SCREENS}")
    return 0 if len(written) == len(rendered) else 1


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main(sys.argv))
