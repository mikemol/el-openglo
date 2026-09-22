#!/usr/bin/env python3
"""render_samples.py — render the theme into catalog/library/samples/, so it can be SEEN.

⚑ WHY THIS EXISTS.  Nine emitters in this tree produce PNG or SVG, and every one
of them writes to /tmp or to a gitignored repo root. The theme was fully
generated, fully gated, and completely invisible: nowhere to open and LOOK at
what the palette actually renders as. A theme whose only description is a token
table is a theme nobody can review.

    catalog/library/render_samples.py            # render every sample, write the index
    catalog/library/render_samples.py --list     # what would be rendered, and from where
    catalog/library/render_samples.py --check    # verify existing samples, render nothing

⚑ THE SAMPLES ARE COMMITTED, DELIBERATELY.  They are build output, which this
repo otherwise gitignores (see .gitignore: wallpapers, previews, aurorae/,
plasma/). These are the exception because their PURPOSE is to be looked at — on
GitHub, in a diff, by someone who has not run anything. A gitignored sample is a
sample nobody sees, which is the problem this solves rather than a rule it breaks.
That also makes a palette change VISIBLE in review: the diff shows the picture.

⚑ AND THE INDEX IS GENERATED.  catalog/library/library.md is written from what actually
rendered, never hand-listed — a hand-maintained index of images is a list that
silently outlives the files it names.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SAMPLES = os.path.join(HERE, "samples")

sys.path.insert(0, ROOT)


def variants():
    """The variants that have a scheme file — discovered, never hardcoded."""
    return sorted(f[:-len(".colors")] for f in os.listdir(ROOT)
                  if f.endswith(".colors"))


# surface -> (filename template, renderer). Each renderer takes (variant, path)
# and writes that file, or raises.
def _preview(variant, path):
    """The scheme rendered as a mock desktop — VECTOR, straight from the emitter.

    ⚑ make_preview ALREADY BUILDS THIS AS SVG and then rasterises it (its
    render_all calls cairosvg.svg2png). Taking preview_svg() directly skips a
    lossy step to reach a file that diffs as text."""
    import make_preview as MP
    open(path, "w", encoding="utf-8").write(MP.preview_svg(MP.parse_scheme(variant)))


def _swatch(variant, path):
    """A palette swatch: every token in the scheme, labelled, as it renders.

    ⚑ THE ONE SAMPLE THAT IS NOT AN EMITTER'S OUTPUT.  The emitters render the
    theme in USE; this renders the palette ITSELF, which is what you want when
    the question is "did that token change?" rather than "does the desktop look
    right".

    ⚑ SVG, AND THE FORMAT IS THE POINT.  A raster swatch diffs as "binary file
    changed" — it shows you that the palette moved but never WHICH token, so a
    reviewer has to open two images side by side and compare by eye. In SVG the
    hex is literally in the diff: `fill="#99ffeb"` becomes `fill="#8ce8da"` on
    the labelled element. That turns the sample from something you look at into
    something you can REVIEW, which is what a library in a git repo is for.
    It also drops the Pillow dependency from this path — one fewer reason a
    sample fails to render on a machine that has not run `uv sync`."""
    import make_preview as MP
    c = MP.parse_scheme(variant)
    order = [k for k in ("ground", "panel", "phosphor", "accent", "sel") if k in c]
    sw, sh, pad, top = 220, 96, 12, 34
    W = pad + len(order) * (sw + pad)
    H = top + sh + 22
    # ⚑ THE LABEL MUST BE READABLE ON THE SWATCH IT LABELS, and the first version
    # was not: it drew every label in `ground`, so the `ground` and `panel` cells
    # rendered as invisible text on themselves — a swatch that cannot say which
    # colour it is showing. Pick whichever of black/white contrasts better,
    # measured with cvd_gate's WCAG function rather than a fresh one, so the
    # sample and the gates agree on what "readable" means.
    import cvd_gate as C
    cells = []
    for i, k in enumerate(order):
        x = pad + i * (sw + pad)
        bg = _rgb(c[k])
        ink = "#000000" if C.wcag_ratio(bg, (0, 0, 0)) >= C.wcag_ratio(bg, (255, 255, 255)) \
              else "#ffffff"
        cells.append(
            f'  <rect x="{x}" y="{top}" width="{sw}" height="{sh}" fill="{c[k]}"/>\n'
            f'  <text x="{x + 8}" y="{top + sh - 10}" font-family="monospace"'
            f' font-size="13" fill="{ink}">{k} {c[k]}</text>')
    open(path, "w", encoding="utf-8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}"'
        f' viewBox="0 0 {W} {H}">\n'
        f'  <rect width="{W}" height="{H}" fill="{c["ground"]}"/>\n'
        f'  <text x="{pad}" y="22" font-family="monospace" font-size="14"'
        f' fill="{c["phosphor"]}">{variant}</text>\n'
        + "\n".join(cells) + "\n</svg>\n")


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _wallpaper(variant, path):
    """The wallpaper — the surface ⊕SEGMENT-SUBSTRATE rewires, so it is sampled.

    ⚑ SAMPLED BECAUSE IT IS ABOUT TO CHANGE.  The BUILD work rewires the
    wallpaper's clock from an inline stroke table to the shared segment
    substrate. "Does it still look right afterward" is answerable only against a
    BEFORE, so the before is captured here first — that is what the library is
    for, and saying a human must check by hand while a sample library sits
    unused would be the same evasion twice."""
    import make_wallpaper as MW
    open(path, "w", encoding="utf-8").write(MW.wallpaper_svg())


SURFACES = (
    ("swatch", "{v}-swatch.svg", _swatch,
     "the palette itself — every scheme token, labelled"),
    ("preview", "{v}-preview.svg", _preview,
     "the scheme rendered as a mock desktop"),
)

# ⚑ NOT EVERY SURFACE IS PER-VARIANT, and pretending otherwise would emit six
# identical files. The wallpaper reads module-level colours with a standalone
# fallback rather than taking a variant, so it renders ONCE. The distinction is
# in the data instead of a special case in targets(): a surface is either keyed
# by variant or it is not.
def _splash_digits(variant, path):
    """The boot splash's digit strip — the surface that renders in PIL, not SVG.

    ⚑ SAMPLED BECAUSE ⊕SEGMENT-SUBSTRATE REWIRES ITS GEOMETRY.  Plymouth draws
    with Pillow rather than emitting markup, so it has no SVG to diff and no QML
    to lint: the only way to see whether its digits still form is to render them
    and look. It was also the hardest silo to detect — it IMPORTED the substrate
    while carrying its own stroke table — so "does it still look right" is
    exactly the question that could not be answered from the source."""
    from PIL import Image
    import make_plymouth as MPL
    import make_preview as MP
    c = MP.parse_scheme(variant)
    ground = MPL._rgb(c["ground"])
    lit = MPL._rgb(c["phosphor"])
    ghost = MPL.ghost_from(lit, ground)
    digits = [MPL.render_digit(d, lit, ghost, U=28) for d in "0123456789"]
    w = sum(d.width for d in digits)
    h = max(d.height for d in digits)
    strip = Image.new("RGBA", (w, h), ground + (255,))
    x = 0
    for d in digits:
        strip.alpha_composite(d, (x, 0))
        x += d.width
    strip.save(path)


def _marquee(variant, path):
    """The notification ticker's 5x7 dot-matrix face, from the SHIPPED registry.

    ⚑ THIS SAMPLE EXISTS BECAUSE NOTHING ELSE CAN SEE THE TICKER.  The marquee
    emits QML, so there is no SVG to diff and no bitmap to open; its gate
    (check_display_registry) compares Python to Python and therefore cannot tell
    a correct font from one rendered upside down. Plymouth shipped CLIPPED DIGITS
    with every check green — valid PNGs of wrong glyphs — and the only thing that
    caught it was a rendered sample. This is that exposure, on a new surface.

    ⚑ IT IS A MIRROR, AND THE MIRROR CAN LIE.  This draws the dots in SVG the way
    marquee-main.qml's drawBackdrop paints them (since s120; MatrixChar.qml before
    that, retired s124); it does not run the QML. So it witnesses
    that THE FONT AND THE REGISTRY are right — a mangled glyph, a bad bit order, a
    dropped column all show up here — and NOT that the QML consuming them renders.
    Two ways to disagree remain: this mirror could drift from the component, and
    the component could be wrong in a way the data is not. Stated rather than
    papered over, because a sample that overclaims is worse than none.

    To keep the drift as small as possible it reads the SAME registry emission the
    plasmoid receives (`as_qml_js("5x7")`, parsed back) rather than reaching into
    display_types — if the emission is broken, this picture breaks with it."""
    import json
    import make_notify_marquee as MM
    import make_preview as MP
    import display_types as DT

    # the SAME emission the plasmoid receives: the 5x8 display, the authored
    # table plus the build-time font extension (⊕MATRIX-FONT-INPUT)
    reg = json.loads(DT.as_qml_js(MM.MATRIX_DISPLAY, font_path=MM.matrix_font()))
    disp = reg["displays"][MM.MATRIX_DISPLAY]
    font = reg["font" + disp["font"]]
    cols, rows = disp["cols"], disp["rows"]

    ground, lit, ghost, _alpha = MM.WL.colors_for(variant)
    # ⚑ THE SAMPLE MUST EXERCISE THE FONT, NOT JUST THE SURFACE.  This first read
    # "EL OPENGLO 13:37" — which contains no 'A', the one glyph that was WRONG.
    # I fixed the font, re-rendered, and the picture was byte-identical, which I
    # briefly misread as the fix not landing. A sample that cannot show the defect
    # is not a witness for it, so this spans the full alphabet and digits: every
    # glyph in the font appears, and a malformed one is visible on sight. The
    # lowercase row shows the authored descenders; the last group is the font
    # EXTENSION (Latin-1, rasterised) and one char outside it, drawn as '?'.
    text = ("ABCDEFGHIJKLM NOPQRSTUVWXYZ 0123456789 -:./+*? "
            "abcdefghijklm nopqrstuvwxyz éèüñç {}[]@#% ☃")

    u = 9.0                       # dot pitch, px
    fill = 0.82                   # matches MatrixChar.dotFill
    pad = u * 2
    adv = cols * u + u            # cell plus one blank column, as the Row spacing does
    W = pad * 2 + adv * len(text) - u
    H = pad * 2 + rows * u

    def _h(rgb):
        return "#%02x%02x%02x" % rgb

    dots = []
    # ⚑ THE FIELD FIRST, BEZEL TO BEZEL, then the lit dots over it — the way the
    # widget draws since W34 (MatrixField under lit-only MatrixChars; the ghost
    # had been per character and scrolled with the text — operator, 2026-09-22).
    # The mirror pads the field to the whole sample width, at the solved alpha.
    field_cols = int(W // u)
    for c in range(field_cols):
        for r in range(rows):
            dots.append(
                f'  <circle cx="{c * u + u / 2:.1f}" cy="{pad + r * u + u / 2:.1f}"'
                f' r="{u * fill / 2:.2f}" fill="{_h(ghost)}" opacity="{_alpha:.3f}"/>')
    for i, ch in enumerate(text):
        # the same fallback chain drawBackdrop walks: char, uppercase, '?'
        colbytes = font.get(ch) or font.get(ch.upper()) or font.get("?") or []
        ox = pad + i * adv
        for c in range(cols):
            byte = colbytes[c] if c < len(colbytes) else 0
            for r in range(rows):
                if not (byte & (1 << r)):
                    continue                      # unlit: the field's dot shows
                cx = ox + c * u + u / 2
                cy = pad + r * u + u / 2
                dots.append(
                    f'  <circle cx="{cx:.1f}" cy="{cy:.1f}" r="{u * fill / 2:.2f}"'
                    f' fill="{_h(lit)}"/>')

    open(path, "w", encoding="utf-8").write(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" height="{H:.0f}"'
        f' viewBox="0 0 {W:.0f} {H:.0f}">\n'
        f'  <rect width="{W:.0f}" height="{H:.0f}" fill="{_h(ground)}"/>\n'
        + "\n".join(dots) + "\n</svg>\n")


SINGLETONS = (
    ("wallpaper", "wallpaper.svg", _wallpaper,
     "the desktop wallpaper — the clock face ⊕SEGMENT-SUBSTRATE rewires"),
    ("splash-digits", "splash-digits.png", lambda _v, p:
     _splash_digits("EL-Openglo", p),
     "the boot splash's 0-9, rendered in PIL from the shared geometry"),
    ("marquee", "marquee.svg", lambda _v, p: _marquee("EL-Openglo", p),
     "the notification ticker's 5x7 matrix face, mirrored from the shipped registry"),
)


def targets():
    """[(variant, surface, path, describe, renderer)] for everything renderable."""
    out = []
    for v in variants():
        for name, tmpl, fn, desc in SURFACES:
            out.append((v, name, os.path.join(SAMPLES, tmpl.format(v=v)), desc, fn))
    for name, fname, fn, desc in SINGLETONS:
        out.append(("(all)", name, os.path.join(SAMPLES, fname), desc, fn))
    return out


def write_index(rendered, failed):
    """library.md — generated from what ACTUALLY rendered."""
    lines = ["# EL Openglo — sample library", "",
             "*Generated by `catalog/library/render_samples.py`. Do not hand-edit:"
             " a hand-maintained index outlives the files it names.*", ""]
    if failed:
        lines += ["> **Incomplete.** %d sample(s) did not render; they are named"
                  " at the bottom rather than silently omitted." % len(failed), ""]
    by_variant = {}
    for v, surface, path, desc, _ in rendered:
        by_variant.setdefault(v, []).append((surface, path, desc))
    for v in sorted(by_variant):
        lines += [f"## {v}", ""]
        for surface, path, desc in sorted(by_variant[v]):
            rel = os.path.relpath(path, HERE)
            lines += [f"**{surface}** — {desc}", "", f"![{v} {surface}]({rel})", ""]
    if failed:
        lines += ["## Did not render", ""]
        for v, surface, why in failed:
            lines.append(f"- `{v}` / {surface}: {why}")
        lines.append("")
    open(os.path.join(HERE, "library.md"), "w", encoding="utf-8").write(
        "\n".join(lines))


def main(argv):
    known = {"--list", "--check"}
    for a in argv[1:]:
        if a not in known:
            print(f"render_samples: unknown flag {a!r}", file=sys.stderr)
            return 2
    tgts = targets()
    if not tgts:
        print("render_samples: REFUSED — no variants found; the scheme files are "
              "missing, not the theme empty", file=sys.stderr)
        return 2

    if "--list" in argv:
        for v, surface, path, desc, _ in tgts:
            print(f"{v}\t{surface}\t{os.path.relpath(path, ROOT)}\t{desc}")
        return 0

    if "--check" in argv:
        missing = [(v, s, p) for v, s, p, _d, _f in tgts if not os.path.isfile(p)]
        empty = [(v, s, p) for v, s, p, _d, _f in tgts
                 if os.path.isfile(p) and os.path.getsize(p) < 128]
        if missing or empty:
            print(f"render_samples: REFUSED — {len(missing)} missing, {len(empty)} "
                  f"empty of {len(tgts)} sample(s):", file=sys.stderr)
            for v, s, p in missing + empty:
                print(f"    {v} {s}: {os.path.relpath(p, ROOT)}", file=sys.stderr)
            return 1
        print(f"render_samples: {len(tgts)} of {len(tgts)} samples present and non-empty")
        return 0

    os.makedirs(SAMPLES, exist_ok=True)
    rendered, failed = [], []
    for v, surface, path, desc, fn in tgts:
        try:
            fn(v, path)
            rendered.append((v, surface, path, desc, fn))
        except Exception as e:                       # noqa: BLE001
            # ⚑ A FAILED SAMPLE IS NAMED, NEVER SKIPPED. An index that quietly
            # omits what would not render shows a complete-looking theme with a
            # hole in it.
            failed.append((v, surface, f"{type(e).__name__}: {e}"))
    write_index(rendered, failed)
    print(f"render_samples: {len(rendered)} rendered, {len(failed)} failed")
    for v, surface, why in failed:
        print(f"    FAILED {v} {surface}: {why}", file=sys.stderr)
    return 1 if failed else 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("variants are discovered", len(variants()) > 0, True)
    check("every surface has a describer", all(d for _n, _t, _f, d in SURFACES), True)
    check("targets cover variants x surfaces, plus the singletons",
          len(targets()), len(variants()) * len(SURFACES) + len(SINGLETONS))
    check("every singleton has a describer", all(d for _n, _f, _r, d in SINGLETONS), True)
    check("singleton filenames carry no variant slot",
          [f for _n, f, _r, _d in SINGLETONS if "{v}" in f], [])
    check("_rgb parses a hex triple", _rgb("#0c1517"), (12, 21, 23))
    print("render_samples selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
