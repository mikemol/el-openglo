#!/usr/bin/env python3
"""Phosphor cursor themes, one per variant (W36).

The operator asked (2026-09-22): "isn't the cursor supposed to inherit something
related to the color scheme?" It cannot by inheritance: an XCursor is a fixed
ARGB image, and make_inherit's cursor theme (W31) only NAMES Breeze's. So the
palette reaches the pointer as a DERIVATION: every glyph is drawn here as SVG in
the display's own idiom, a LIT OUTLINE in the variant's phosphor token around a
DARK BODY in its ground, rasterised at 24/32/48 px and written as XCursor files.

⚑ NO COLOUR IS COMPUTED HERE. The two colours are make_preview.parse_scheme's
`phosphor` and `ground` for the variant, read from the solved .colors file
(scripts/check_token_source.py refuses an emitter that reads no authority).

⚑ THE THEME DIRECTORY IS make_inherit's. make_inherit.cursor_theme_name(v)
(`<variant>-cursors`) already ships index.theme with `Inherits=` Breeze and is
what the Look-and-Feel defaults select ([kcminputrc][Mouse] cursorTheme). This
emitter fills its `cursors/`; every shape NOT drawn here still resolves through
the inheritance, so the set can grow without ever leaving a hole.

The writer is pure Python (the XCursor file format: "Xcur", a TOC of image
chunks, premultiplied ARGB little-endian) — xcursorgen is not installed on this
host and is not needed. cairosvg rasterises; it is already a dependency of
make_deb, and its absence is reported by the caller as a SKIP.

    make_cursors.py                 # list the shapes, their aliases and hotspots
    make_cursors.py --out DIR       # write every variant's theme under DIR
    make_cursors.py --sheet PNG     # a contact sheet of every glyph x variant, for eyes
"""
import os
import struct
import sys

import make_inherit as _inh
import make_preview as _mp
from emitters import atomic_write

VARIANTS = _inh.VARIANTS
SIZES = (24, 32, 48)
BOX = 32            # the SVG design grid; each size scales it
OUTLINE = 3.0       # the stroke that becomes the lit rim (half of it shows)


def tokens(variant):
    """{'lit', 'ground'} — the two glyph colours, from the solved scheme."""
    c = _mp.parse_scheme(variant)
    return {"lit": c["phosphor"], "ground": c["ground"]}


# --- the glyphs: path data on a 32-unit grid, and the hotspot on that grid ----
_ARROW = "M5,3 L5,24 L10,19.5 L13.5,27.5 L17,26 L13.5,18 L20.5,18 Z"
_EW = "M3,16 L9,10 L9,14 L23,14 L23,10 L29,16 L23,22 L23,18 L9,18 L9,22 Z"


def _rot(d, deg):
    return f'<g transform="rotate({deg} 16 16)">{d}</g>'


def _paths(*ds, rotate=0):
    """A glyph as the UNION of filled paths: every path's lit rim first, then
    every body over it, so overlapping parts share one outline."""
    def draw(lit, ground):
        rims = "".join(f'<path d="{d}" fill="{lit}" stroke="{lit}" stroke-width="{OUTLINE}" '
                       'stroke-linejoin="round"/>' for d in ds)
        bodies = "".join(f'<path d="{d}" fill="{ground}"/>' for d in ds)
        g = rims + bodies
        return _rot(g, rotate) if rotate else g
    return draw


def _ring(lit, ground, cx=16, cy=16, r=10.5):
    """The wait glyph: a ground disc with a lit rim, and six lit SEGMENTS round it
    (a segment display's ring, not a spinner's arc)."""
    segs = "".join(
        f'<rect x="{cx - 1.3}" y="{cy - r + 2.6}" width="2.6" height="5" rx="1.2" fill="{lit}" '
        f'transform="rotate({a} {cx} {cy})"/>' for a in range(0, 360, 60))
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{ground}" stroke="{lit}" '
            f'stroke-width="{OUTLINE / 2}"/>' + segs)


def _not_allowed(lit, ground):
    return (f'<circle cx="16" cy="16" r="11" fill="{ground}" stroke="{lit}" stroke-width="3"/>'
            f'<line x1="8.5" y1="8.5" x2="23.5" y2="23.5" stroke="{lit}" stroke-width="3"/>')


def _progress(lit, ground):
    arrow = _paths("M4,2 L4,19 L8,15.5 L10.8,21.8 L13.6,20.6 L10.8,14.3 L16.4,14.3 Z")(lit, ground)
    return arrow + _ring(lit, ground, cx=22, cy=22, r=7)


def _wait(lit, ground):
    return _ring(lit, ground)


# name -> (draw(lit, ground) -> svg body, hotspot (x, y) on the 32 grid, aliases)
# ⚑ THE ALIASES ARE THE NAMES KDE (Qt's CSS names), GTK (the CSS cursor names)
# AND legacy X11 (the core font names) look up, read from breeze_cursors' own
# cursors/ listing on this host (2026-09-23).
SHAPES = {
    "default":     (_paths(_ARROW), (5, 3),
                    ("left_ptr", "arrow", "top_left_arrow")),
    "text":        (_paths("M11,4 H21 V7.5 H17.8 V24.5 H21 V28 H11 V24.5 H14.2 V7.5 H11 Z"), (16, 16),
                    ("xterm", "ibeam")),
    "pointer":     (_paths("M11,3.5 L15,3.5 L15,12.5 L25,14.5 L25,22.5 L21,28.5 L13,28.5 "
                           "L6.5,21 L6.5,16 L11,18.5 Z"), (13, 4),
                    ("hand2", "hand1", "pointing_hand")),
    "wait":        (_wait, (16, 16), ("watch",)),
    "progress":    (_progress, (4, 2),
                    ("left_ptr_watch", "half-busy",
                     "08e8e1c95fe2fc01f976f1e063a24ccd", "3ecb610c1bf2410f44200f48c40d3599")),
    # pixel-aligned at 32: body edges on whole pixels, so the rim and the body
    # each own whole columns (at 14.8/17.2 the blended rim/body column was the
    # glyph's DOMINANT colour — check_cursors saw it, C3)
    "crosshair":   (_paths("M15,3 H17 V15 H29 V17 H17 V29 H15 V17 H3 V15 H15 Z"),
                    (16, 16), ("cross", "tcross")),
    "not-allowed": (_not_allowed, (16, 16),
                    ("forbidden", "crossed_circle", "circle", "no-drop", "dnd-no-drop")),
    "ew-resize":   (_paths(_EW), (16, 16),
                    ("e-resize", "w-resize", "col-resize", "sb_h_double_arrow", "h_double_arrow",
                     "size_hor", "size-hor", "left_side", "right_side", "split_h")),
    "ns-resize":   (_paths(_EW, rotate=90), (16, 16),
                    ("n-resize", "s-resize", "row-resize", "sb_v_double_arrow", "v_double_arrow",
                     "size_ver", "size-ver", "top_side", "bottom_side", "split_v")),
    "nwse-resize": (_paths(_EW, rotate=45), (16, 16),
                    ("nw-resize", "se-resize", "size_fdiag", "size-fdiag",
                     "top_left_corner", "bottom_right_corner")),
    "nesw-resize": (_paths(_EW, rotate=-45), (16, 16),
                    ("ne-resize", "sw-resize", "size_bdiag", "size-bdiag",
                     "top_right_corner", "bottom_left_corner")),
    "move":        (_paths(_EW, "M16,3 L22,9 L18,9 L18,23 L22,23 L16,29 L10,23 L14,23 L14,9 L10,9 Z"),
                    (16, 16), ("all-scroll", "fleur", "size_all")),
}


def svg(shape, variant, colours=None):
    """The glyph's SVG document for one variant (`colours` overrides the tokens —
    for a check's fixture, never for an emission)."""
    t = colours or tokens(variant)
    draw = SHAPES[shape][0]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{BOX}" height="{BOX}" '
            f'viewBox="0 0 {BOX} {BOX}">{draw(t["lit"], t["ground"])}</svg>')


# --- XCursor: the file format, both directions ---------------------------------
XC_MAGIC = b"Xcur"
XC_IMAGE = 0xFFFD0002


def rasterise(svg_text, size):
    """(width, height, [premultiplied ARGB u32]) at size x size."""
    import io
    import cairosvg
    from PIL import Image
    png = cairosvg.svg2png(bytestring=svg_text.encode(), output_width=size, output_height=size)
    im = Image.open(io.BytesIO(png)).convert("RGBA")
    raw = im.tobytes()
    px = []
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
        px.append((a << 24) | ((r * a // 255) << 16) | ((g * a // 255) << 8) | (b * a // 255))
    return size, size, px


def sheet(path, size=48):
    """A contact sheet PNG: one row per variant, one column per shape, each glyph
    at `size` over a mid-grey (so both a dark and a light rim read) — for eyes."""
    from PIL import Image
    im = Image.new("RGBA", ((size + 8) * len(SHAPES) + 8, (size + 8) * len(VARIANTS) + 8),
                   (128, 128, 128, 255))
    for row, v in enumerate(VARIANTS):
        for col, shape in enumerate(SHAPES):
            w, h, px = rasterise(svg(shape, v), size)
            g = Image.new("RGBA", (w, h))
            g.putdata([((p >> 16) & 255, (p >> 8) & 255, p & 255, p >> 24) for p in _unpremultiply(px)])
            im.alpha_composite(g, (8 + col * (size + 8), 8 + row * (size + 8)))
    from emitters import atomic_path
    with atomic_path(path) as tmp:
        im.save(tmp)
    return path


def _unpremultiply(px):
    out = []
    for p in px:
        a = p >> 24
        if a == 0:
            out.append(0)
            continue
        r, g, b = (((p >> s) & 255) * 255 // a for s in (16, 8, 0))
        out.append((a << 24) | (min(r, 255) << 16) | (min(g, 255) << 8) | min(b, 255))
    return out


def xcursor_bytes(images):
    """images: [(nominal, w, h, xhot, yhot, pixels)] -> the XCursor file."""
    ntoc = len(images)
    head = struct.pack("<4sIII", XC_MAGIC, 16, 0x10000, ntoc)
    pos = 16 + 12 * ntoc
    toc, chunks = b"", b""
    for nominal, w, h, xh, yh, px in images:
        toc += struct.pack("<III", XC_IMAGE, nominal, pos)
        chunk = struct.pack("<IIIIIIIII", 36, XC_IMAGE, nominal, 1, w, h, xh, yh, 0)
        chunk += struct.pack(f"<{len(px)}I", *px)
        chunks += chunk
        pos += len(chunk)
    return head + toc + chunks


def read_xcursor(path):
    """{nominal: (w, h, xhot, yhot, [ARGB])} — the inverse of xcursor_bytes, for
    the check. Raises ValueError on a file that is not an XCursor."""
    data = open(path, "rb").read()
    if data[:4] != XC_MAGIC:
        raise ValueError(f"{path}: not an XCursor file")
    _m, hsize, _ver, ntoc = struct.unpack_from("<4sIII", data, 0)
    out = {}
    for i in range(ntoc):
        typ, sub, pos = struct.unpack_from("<III", data, hsize + 12 * i)
        if typ != XC_IMAGE:
            continue
        _h, _t, nominal, _v, w, h, xh, yh, _d = struct.unpack_from("<IIIIIIIII", data, pos)
        px = list(struct.unpack_from(f"<{w * h}I", data, pos + 36))
        out[nominal] = (w, h, xh, yh, px)
    return out


def cursor_file(shape, variant, colours=None):
    """The XCursor bytes for one shape: one image per size, hotspot scaled."""
    doc = svg(shape, variant, colours)
    hx, hy = SHAPES[shape][1]
    imgs = []
    for s in SIZES:
        w, h, px = rasterise(doc, s)
        imgs.append((s, w, h, min(w - 1, round(hx * s / BOX)), min(h - 1, round(hy * s / BOX)), px))
    return xcursor_bytes(imgs)


def render_all(variants, icons_root):
    """Fill <icons_root>/<make_inherit.cursor_theme_name(v)>/cursors/ per variant:
    one XCursor file per shape and a RELATIVE symlink per alias. index.theme and
    cursor.theme are make_inherit's (the Inherits= fallback); written here too if
    absent, so this emitter's output is a complete theme on its own."""
    written = {}
    for v in variants:
        tdir = os.path.join(icons_root, _inh.cursor_theme_name(v))
        cdir = os.path.join(tdir, "cursors")
        os.makedirs(cdir, exist_ok=True)
        for fn, body in (("index.theme", _inh.cursor_index(v)),
                         ("cursor.theme", _inh.cursor_theme_file(v))):
            p = os.path.join(tdir, fn)
            if not os.path.exists(p):
                atomic_write(p, body)
        for shape, (_d, _hot, aliases) in SHAPES.items():
            atomic_write(os.path.join(cdir, shape), cursor_file(shape, v))
            for a in aliases:
                ap = os.path.join(cdir, a)
                if os.path.lexists(ap):
                    os.remove(ap)
                os.symlink(shape, ap)
        written[v] = tdir
    return written


def main(argv):
    args = argv[1:]
    known = {"--out", "--sheet"}
    flags = [a for a in args if a.startswith("--")]
    for a in flags:
        if a not in known:
            print(f"make_cursors: unknown flag {a!r} (modes: none, --out DIR, --sheet PNG)",
                  file=sys.stderr)
            return 2
    if "--sheet" in args:
        i = args.index("--sheet")
        if i + 1 >= len(args):
            print("make_cursors: --sheet needs a PNG path", file=sys.stderr)
            return 2
        print(f"make_cursors: sheet of {len(SHAPES)} shapes x {len(VARIANTS)} variants -> "
              f"{sheet(os.path.abspath(args[i + 1]))}")
        return 0
    if "--out" in args:
        i = args.index("--out")
        if i + 1 >= len(args):
            print("make_cursors: --out needs a directory", file=sys.stderr)
            return 2
        out = render_all(VARIANTS, os.path.abspath(args[i + 1]))
        n = sum(1 + len(a) for _d, _h, a in SHAPES.values())
        print(f"make_cursors: {len(out)} of {len(VARIANTS)} variant theme(s) written, "
              f"{len(SHAPES)} shapes + {n - len(SHAPES)} aliases x {len(SIZES)} sizes each, under {args[i + 1]}")
        return 0
    for shape, (_d, hot, aliases) in SHAPES.items():
        print(f"  {shape:12s} hot={hot}  {', '.join(aliases)}")
    for v in VARIANTS:
        t = tokens(v)
        print(f"  {_inh.cursor_theme_name(v):24s} lit={t['lit']} ground={t['ground']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
