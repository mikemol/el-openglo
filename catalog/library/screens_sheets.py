# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""screens_sheets — the contact sheets and the strip: post-render code for the DERIVED outputs (W61).

Split out of render_screens.py so the sheet code keys only sheet-* and strip.png:
keyed whole in render_screens, a comment anywhere in that file moved 55 of 56 output
keys (measured 2026-10-02).
"""
import os


def contact_sheets(out_dir, variants, tiles_of, only=None):
    """One sheet per variant (its surfaces stacked, `tiles_of(v)` in order) and one strip
    of the sheets; with `only`, just the sheets (and strip) named in it."""
    from PIL import Image, ImageDraw
    sheets = []
    per_variant = []
    for v in variants:
        if only is not None and f"sheet-{v}.png" not in only:
            if "strip.png" in only and os.path.isfile(os.path.join(out_dir, f"sheet-{v}.png")):
                per_variant.append(Image.open(os.path.join(out_dir, f"sheet-{v}.png")).convert("RGB"))
            continue
        tiles = [Image.open(os.path.join(out_dir, t)).convert("RGB")
                 for t in tiles_of(v) if os.path.isfile(os.path.join(out_dir, t))]
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
