#!/usr/bin/env python3
"""Konsole colorscheme emitter (⊕KONSOLE).

Fifth palette emitter. A terminal's 16 ANSI colors carry MEANING (error=red,
success=green), so the invariant is: keep them semantically SEPARABLE — they must
survive the same CVD/distinctness gate the rest of the theme uses — while tinting
them toward the variant's phosphor family on its void ground. Not monochrome
(unusable), not generic Breeze (identity-less): phosphor-tinted-but-distinct.
"""
import os
import make_preview as MP
import cvd_gate as C

ROOT = os.path.dirname(os.path.abspath(__file__))

# canonical semantic ANSI hues (what red/green/etc MUST remain readable as).
# base16 order: 0 black,1 red,2 green,3 yellow,4 blue,5 magenta,6 cyan,7 white.
BREEZE_ANSI = [
    (35, 38, 39), (237, 21, 21), (17, 209, 22), (246, 116, 0),
    (29, 153, 243), (155, 89, 182), (26, 188, 156), (252, 252, 252),
]


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _tint(color, toward, t):
    """Pull `color` a fraction t toward the phosphor accent `toward`, preserving
    its own hue identity (small t) so red stays red but gains phosphor cast."""
    return tuple(int(round(color[i] + (toward[i] - color[i]) * t)) for i in range(3))


def _ansi16(accent, ground, tint=0.22):
    """Phosphor-tinted ANSI that stays pairwise-distinct. Tint each Breeze ANSI
    toward the accent; if tinting collapses any pair below the distinctness
    floor, back the tint off for that scheme until all pairs clear it."""
    # ⚑ REVERTED TO THE ORIGINAL CALL, AND THE EARLIER "REPAIR" WAS THE WRONG
    # DIAGNOSIS.  This line called `C.reference_floors()` (plural, dict-valued); an
    # earlier pass read that as a replay typo for the singular `reference_floor()`
    # and rewrote it to `reference_floor()[0]`.  It was not a typo: the plural is a
    # real, separate function that returns the floor PER PAIR CLASS, and it had
    # simply gone missing with the rest of the cvd_gate API.  Rewriting the caller
    # made the symptom disappear while the actual break — 8 of 10 referenced
    # attributes absent — stayed invisible.  Fixing a caller to match a damaged
    # module is how a gap gets sealed over instead of found.
    floor = min(C.reference_floors().values()) * 0.5  # half the OI hue-floor: ANSI
    # pairs are allowed closer than palette pairs, but must stay separable.
    t = tint
    for _ in range(20):
        cols = [_tint(c, accent, t) for c in BREEZE_ANSI]
        # color0 (black) should sit near the ground, not tint to accent
        cols[0] = _tint(ground, accent, 0.15)
        ok = True
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                if C.worst_view_dE(cols[i], cols[j])[0] < floor:
                    ok = False
                    break
            if not ok:
                break
        if ok:
            return cols, t
        t *= 0.8  # too collapsed — reduce tint and retry
    return cols, t


def colorscheme(variant):
    c = MP.parse_scheme(variant)
    ground = _rgb(c["ground"])
    phosphor = _rgb(c["phosphor"])
    accent = _rgb(c["accent"])
    ansi, used_t = _ansi16(accent, ground)
    intense = [_tint(x, (255, 255, 255), 0.25) for x in ansi]   # brighter bank
    faint = [_tint(x, ground, 0.35) for x in ansi]               # dimmer bank

    def block(name, rgb):
        return f"[{name}]\nColor={rgb[0]},{rgb[1]},{rgb[2]}\n"

    out = []
    out.append(block("Background", ground))
    out.append(block("BackgroundFaint", ground))
    out.append(block("BackgroundIntense", _tint(ground, (0, 0, 0), 0.3)))
    out.append(block("Foreground", phosphor))
    out.append(block("ForegroundFaint", _tint(phosphor, ground, 0.3)))
    out.append(block("ForegroundIntense", _tint(phosphor, (255, 255, 255), 0.2)))
    for i in range(8):
        out.append(block(f"Color{i}", ansi[i]))
        out.append(block(f"Color{i}Faint", faint[i]))
        out.append(block(f"Color{i}Intense", intense[i]))
    out.append(f"[General]\nDescription=EL Openglo ({variant})\n"
               f"Opacity=1\nBlur=false\nColorRandomization=false\nWallpaper=\n")
    return "\n".join(out)


def render_all(variants, out_map):
    written = []
    for v in variants:
        p = out_map[v]
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, "w").write(colorscheme(v))
        written.append(p)
    return written


if __name__ == "__main__":
    variants = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
                "EL-Amber", "EL-Amber-Lit"]
    outs = {v: f"/tmp/{v}.colorscheme" for v in variants}
    render_all(variants, outs)
    print("rendered", len(outs), "Konsole colorschemes")
    for v in variants:
        c = MP.parse_scheme(v)
        ansi, t = _ansi16(_rgb(c["accent"]), _rgb(c["ground"]))
        print(f"  {v}: tint={t:.2f} red={ansi[1]} green={ansi[2]} blue={ansi[4]}")
