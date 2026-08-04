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
SINGLETONS = (
    ("wallpaper", "wallpaper.svg", _wallpaper,
     "the desktop wallpaper — the clock face ⊕SEGMENT-SUBSTRATE rewires"),
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
