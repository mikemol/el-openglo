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
from emitters import atomic_write

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


def ansi_table(variant):
    """THE terminal palette for a variant — one table, every format reads it.

    ⚑ FIVE FORMATS, ONE DERIVATION.  Konsole, Alacritty, foot, Windows Terminal
    and Termux all want the same sixteen ANSI colours plus a ground and a
    foreground; only the syntax differs. The Alacritty/foot emitters were lost in
    the recovery (make_deb printed a SKIP for them until 2026-09-21) and W16/W18
    add two more targets, so the derivation lives here once and each format is a
    serialiser over this dict. Keys: ground, foreground, fg_faint, fg_intense,
    bg_intense, normal[8], bright[8] (the Intense bank), faint[8], tint."""
    c = MP.parse_scheme(variant)
    ground = _rgb(c["ground"])
    phosphor = _rgb(c["phosphor"])
    accent = _rgb(c["accent"])
    ansi, used_t = _ansi16(accent, ground)
    return {
        "ground": ground,
        "bg_intense": _tint(ground, (0, 0, 0), 0.3),
        "foreground": phosphor,
        "fg_faint": _tint(phosphor, ground, 0.3),
        "fg_intense": _tint(phosphor, (255, 255, 255), 0.2),
        "normal": ansi,
        "bright": [_tint(x, (255, 255, 255), 0.25) for x in ansi],   # brighter bank
        "faint": [_tint(x, ground, 0.35) for x in ansi],             # dimmer bank
        "tint": used_t,
    }


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(rgb)


def colorscheme(variant):
    t = ansi_table(variant)
    ground, phosphor = t["ground"], t["foreground"]
    ansi, intense, faint = t["normal"], t["bright"], t["faint"]

    def block(name, rgb):
        return f"[{name}]\nColor={rgb[0]},{rgb[1]},{rgb[2]}\n"

    out = []
    out.append(block("Background", ground))
    out.append(block("BackgroundFaint", ground))
    out.append(block("BackgroundIntense", t["bg_intense"]))
    out.append(block("Foreground", phosphor))
    out.append(block("ForegroundFaint", t["fg_faint"]))
    out.append(block("ForegroundIntense", t["fg_intense"]))
    for i in range(8):
        out.append(block(f"Color{i}", ansi[i]))
        out.append(block(f"Color{i}Faint", faint[i]))
        out.append(block(f"Color{i}Intense", intense[i]))
    out.append(f"[General]\nDescription=EL Openglo ({variant})\n"
               f"Opacity=1\nBlur=false\nColorRandomization=false\nWallpaper=\n")
    return "\n".join(out)


def profile(variant):
    """A Konsole PROFILE naming this variant's scheme.

    ⚑ A SCHEME NOBODY'S PROFILE NAMES IS NOT APPLIED.  Konsole colours are per
    profile, not per kdeglobals, and the stock profile is the read-only Built-in
    one. Measured 2026-09-21 on luthen: the six .colorscheme files were installed
    and listed; picking one in the profile editor wrote ~/.local/share/konsole/
    'Profile 1.profile' — but konsolerc named no DefaultProfile, so every tab
    stayed on Built-in and "nothing changed". This file, plus el-openglo-apply
    writing konsolerc DefaultProfile, is the missing half of ⊕KONSOLE."""
    return (f"[Appearance]\nColorScheme={variant}\n\n"
            f"[General]\nName=EL Openglo ({variant})\nParent=FALLBACK/\n")


ANSI_NAMES = ("black", "red", "green", "yellow", "blue", "magenta", "cyan", "white")


def alacritty_toml(variant):
    """Alacritty's [colors] table (TOML, alacritty >= 0.13)."""
    t = ansi_table(variant)
    lines = [f"# EL Openglo ({variant}) — generated by make_konsole.py from the palette",
             "[colors.primary]",
             f'background = "{_hex(t["ground"])}"',
             f'foreground = "{_hex(t["foreground"])}"',
             f'dim_foreground = "{_hex(t["fg_faint"])}"',
             f'bright_foreground = "{_hex(t["fg_intense"])}"', ""]
    for bank in ("normal", "bright"):
        lines.append(f"[colors.{bank}]")
        for name, rgb in zip(ANSI_NAMES, t[bank]):
            lines.append(f'{name} = "{_hex(rgb)}"')
        lines.append("")
    lines.append("[colors.dim]")
    for name, rgb in zip(ANSI_NAMES, t["faint"]):
        lines.append(f'{name} = "{_hex(rgb)}"')
    return "\n".join(lines) + "\n"


def foot_ini(variant):
    """foot's [colors] section (foot.ini; colours are bare rrggbb)."""
    t = ansi_table(variant)
    lines = [f"# EL Openglo ({variant}) — generated by make_konsole.py from the palette",
             "[colors]",
             f"background={_hex(t['ground'])[1:]}",
             f"foreground={_hex(t['foreground'])[1:]}"]
    for i, rgb in enumerate(t["normal"]):
        lines.append(f"regular{i}={_hex(rgb)[1:]}")
    for i, rgb in enumerate(t["bright"]):
        lines.append(f"bright{i}={_hex(rgb)[1:]}")
    for i, rgb in enumerate(t["faint"]):
        lines.append(f"dim{i}={_hex(rgb)[1:]}")
    return "\n".join(lines) + "\n"


def windows_terminal_json(variant):
    """A Windows Terminal colour scheme object (paste into settings.json `schemes`)."""
    import json
    t = ansi_table(variant)
    wt_names = ("black", "red", "green", "yellow", "blue", "purple", "cyan", "white")
    scheme = {"name": f"EL Openglo ({variant})",
              "background": _hex(t["ground"]), "foreground": _hex(t["foreground"]),
              "cursorColor": _hex(t["foreground"]),
              "selectionBackground": _hex(t["fg_faint"])}
    for name, rgb in zip(wt_names, t["normal"]):
        scheme[name] = _hex(rgb)
    for name, rgb in zip(wt_names, t["bright"]):
        scheme["bright" + name.capitalize()] = _hex(rgb)
    return json.dumps(scheme, indent=2) + "\n"


def termux_properties(variant):
    """Termux's ~/.termux/colors.properties."""
    t = ansi_table(variant)
    lines = [f"# EL Openglo ({variant}) — generated by make_konsole.py from the palette",
             f"background={_hex(t['ground'])}", f"foreground={_hex(t['foreground'])}",
             f"cursor={_hex(t['foreground'])}"]
    for i, rgb in enumerate(t["normal"] + t["bright"]):
        lines.append(f"color{i}={_hex(rgb)}")
    return "\n".join(lines) + "\n"


# ⚑ THE TERMINAL ROSTER IS DECLARED HERE, BY THE EMITTER (W65, 2026-09-22). The
# five formats catalog/publishing.md names used to be typed into check_terminals
# as a tuple of strings, so dropping one made "30 of 30" read "24 of 24" — green.
# The emitter owns what it emits; the check holds its reader roster against this.
TERMINAL_FORMATS = {
    "konsole": colorscheme,
    "alacritty": alacritty_toml,
    "foot": foot_ini,
    "windows-terminal": windows_terminal_json,
    "termux": termux_properties,
}


def render_all(variants, out_map):
    written = []
    for v in variants:
        p = out_map[v]
        os.makedirs(os.path.dirname(p), exist_ok=True)
        atomic_write(p, colorscheme(v))
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
