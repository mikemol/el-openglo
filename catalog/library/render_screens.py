#!/usr/bin/env python3
"""render_screens.py — screenshots of every surface x variant, through the theme (W52).

⚑ THESE ARE NOT MOCK-UPS. Each PNG is the emitted surface rendered by Qt under
the real KDE platform theme with a private kdeglobals holding that variant's
scheme (theme_probe.env_for) — what the desktop draws when that scheme is
applied. The marquee stills come from check_marquee_live's harness (the
widget mid-scroll; the widget held by the hover-pause, ring pulsing); the
switcher from render_qml's KWin rewrite over a three-caption stub model;
the clock and live wallpaper from render_qml as the render gate draws them.

    catalog/library/render_screens.py            # write catalog/library/screens/*.png + sheets
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
# back — one render per band (render_qml --set offsetRows), ping-pong so the
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


def animate_viewport(variant, out_apng):
    """The text probe rendered once per band of its backdrop (offsetRows 0..8..0),
    assembled as an APNG: the field scrolling down a 16-row Unifont cell and back.
    Returns the frame count. Each frame is a full themed render (~2 s wall on an
    idle host), which is why this is a run, not a gate."""
    import tempfile
    import render_qml as RQ
    from PIL import Image
    ims = []
    with tempfile.TemporaryDirectory() as td:
        # the same backend as the stills (rhi where the host has it): the frames
        # must look like the picture beside them
        for i, step in enumerate(VIEWPORT_STEPS):
            out = os.path.join(td, f"frame-{i:03d}.png")
            rc, _err = RQ.render("aperture-text", variant, 420, 40, out, {"offsetRows": step})
            if rc == 0 and os.path.isfile(out):
                ims.append(Image.open(out).convert("RGB"))
    if not ims:
        return 0
    ims[0].save(out_apng, format="PNG", save_all=True, append_images=ims[1:], duration=VIEWPORT_FRAME_MS, loop=0)
    return len(ims)


def render_all(out_dir=SCREENS):
    import render_qml as RQ
    import check_marquee_live as ML
    os.makedirs(out_dir, exist_ok=True)
    written = []
    # ⚑ A STALE FILE MUST NOT COUNT AS A RENDER (measured 2026-09-23: under W73's
    # sandbox every render_qml call failed — X authority stripped — and this loop
    # still reported "42 of 48", because `os.path.isfile(out)` found LAST NIGHT'S
    # pictures). Every planned output is removed first, so only a render this run
    # produced can be counted — and a failure leaves a hole @SCREENS will refuse.
    for fn, _v, _how in plan() + plan_animations():
        p = os.path.join(out_dir, fn)
        if os.path.isfile(p):
            os.remove(p)
    for v in VARIANTS:
        for name, how in STILLS:
            out = os.path.join(out_dir, f"{name}-{v}.png")
            if how[0] == "render_qml":
                _k, surface, w, h = how
                rc, _err = RQ.render(surface, v, w, h, out)
            elif how == ("marquee", "scroll"):
                ML.screenshot(v, out, os.path.join(out_dir, f"marquee-paused-{v}.png"))
            elif how == ("marquee", "paused"):
                pass                                   # written by the scroll step
            if os.path.isfile(out):
                written.append(out)
        for name, how in ANIMATIONS:
            out = os.path.join(out_dir, f"{name}-{v}.png")
            n = ML.animate(v, out) if how[1] == "animate" else animate_viewport(v, out)
            if n:
                written.append(out)
    sheets = contact_sheets(out_dir)
    open(os.path.join(out_dir, "README.md"), "w", encoding="utf-8").write(index_md())
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


def contact_sheets(out_dir=SCREENS):
    """One sheet per variant (its surfaces stacked) and one strip of the six sheets."""
    from PIL import Image, ImageDraw
    sheets = []
    per_variant = []
    for v in VARIANTS:
        tiles = [Image.open(os.path.join(out_dir, f"{name}-{v}.png")).convert("RGB")
                 for name, _h in STILLS if os.path.isfile(os.path.join(out_dir, f"{name}-{v}.png"))]
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
    if per_variant:
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
    known = {"--list", "--json", "--outputs"}
    for a in argv[1:]:
        if a not in known:
            print(f"render_screens: unknown flag {a!r}", file=sys.stderr)
            return 2
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
    # ⚑ THE GPU OPT-IN IS DECLARED HERE, NOT REMEMBERED (operator ruling 2026-09-22,
    # W73): every Qt spawn runs headless on the software scene graph by default, and
    # MultiEffect's bloom halo draws NOTHING there. The screenshots are the one place
    # the halo must show, so this process — and only this one — opts into the RHI.
    # It still gets no core and no DrKonqi from qt_sandbox, but it DOES reach the GPU
    # driver: the vector W73 closed for every test.
    os.environ.setdefault("EL_QT_GPU", "1")
    import render_qml as RQ
    if not os.path.exists(RQ.QML):
        print(f"render_screens: SKIP — {RQ.QML} is not installed", file=sys.stderr)
        return 0
    written, sheets = render_all()
    want = len(plan()) + len(plan_animations())
    print(f"render_screens: {len(written)} of {want} stills + animations, {len(sheets)} sheets -> {SCREENS}")
    return 0 if len(written) == want else 1


if __name__ == "__main__":
    os.chdir(ROOT)
    sys.exit(main(sys.argv))
