#!/usr/bin/env python3
"""SDDM greeter emitter (W66) — the segment display's FOURTH MOUNT.

One SDDM theme per variant, /usr/share/sddm/themes/el-openglo-<slug>/:
metadata.desktop, theme.conf, Main.qml, SegmentChar.qml. Each is a real
`Type=sddm-theme` with `QtVersion=6` (the keys the stock breeze theme carries,
/usr/share/sddm/themes/breeze/metadata.desktop:103-113), so it is listed by
System Settings' login-screen page — which the el-openglo-sddm helper (a stock
Breeze theme repointed at an EL wallpaper) never was.

⚑ PER-VARIANT DIRECTORIES, NOT ONE THEME WITH A VARIANT KEY. The other Plasma
mounts are ONE package BOUND to the active colour scheme (⊕ONE-THEME, W35); a
greeter cannot do that — it runs as the sddm user, before any session, with no
Kirigami and no kdeglobals, so there is no active scheme to bind to. The palette
must be BAKED. Six baked directories make the variant a choice in the picker;
one directory with a theme.conf `variant=` key would make it an edit to a root-
owned file that the picker cannot show. The QML is one template; only its colour
holes differ, so the six cannot drift in markup.

⚑ THE COLOURS ARE READ, NOT COMPUTED: every hole comes from make_schemes.GRID
(the tokens the palette solver wrote), through make_wallpaper_live.colors_for
for lit / ghost / ground / alpha — the same read the live wallpaper does.

WEAKNESS: the greeter's runtime (the `sddm`, `userModel`, `sessionModel`,
`config` context objects) exists only inside sddm-greeter-qt6. The render gate
(scripts/check_sddm.py) drives this document against STUBS of them; a stub that
differs from SDDM's real object is invisible to it. `sddm-greeter-qt6
--test-mode --theme <dir>` is the live check and needs a display.
"""
import os
import sys

from make_schemes import GRID
from emitters import LICENSE_SPDX   # the one licence id (W44)
import make_wallpaper_live as _WPL
from emitters import atomic_write

ROOT = os.path.dirname(os.path.abspath(__file__))
VARIANTS = _WPL.ALL_VARIANTS


def theme_id(variant):
    """el-openglo-<slug>: EL-Azure-Lit -> el-openglo-azure-lit."""
    return "el-openglo-" + variant.lower()[len("el-"):]


def _tok(variant):
    ph, mode = _WPL._variant_key(variant)
    return [tt for (p, m), (tt, _d) in GRID.items() if p == ph and m == mode][0]


def _hex(csv):
    return "#%02x%02x%02x" % tuple(int(x) for x in csv.split(","))


def colors(variant):
    """{hole: "#rrggbb" or alpha} for the template — a READ of GRID."""
    ground, lit, ghost, alpha = _WPL.colors_for(variant, "glanced_at")
    t = _tok(variant)
    return {"ground": "#%02x%02x%02x" % ground, "lit": "#%02x%02x%02x" % lit,
            "ghost": "#%02x%02x%02x" % ghost, "ghostAlpha": f"{alpha}",
            "field": _hex(t["button"]), "focus": _hex(t["focus"]),
            "negative": _hex(t["neg"])}


def main_qml(variant):
    """templates/sddm-main.qml with the variant's palette and the display's tables."""
    import templates.loader as TL
    import segment_topology as _ST
    import make_clock as _MC
    m = _ST.metrics(4.0)
    return TL.render("sddm-main.qml", tables=_MC.qml_tables(),
                     pitch=f"{m['pitch']:.3f}", strokeBase=f"{m['stroke'] / 1.25:.3f}",
                     dotR=f"{m['dot'] / 2:.3f}", colonAdvance=f"{m['colon_advance']:.3f}",
                     **colors(variant))


def metadata_desktop(variant):
    tid = theme_id(variant)
    return ("[SddmGreeterTheme]\n"
            f"Name=EL Openglo ({variant})\n"
            f"Description=Electroluminescent segment-clock login screen — {variant}\n"
            "Author=EL Openglo\n"
            f"License={LICENSE_SPDX}\n"
            "Type=sddm-theme\n"
            "Version=0.1\n"
            "MainScript=Main.qml\n"
            "ConfigFile=theme.conf\n"
            f"Theme-Id={tid}\n"
            "Theme-API=2.0\n"
            "QtVersion=6\n")


def theme_conf(variant):
    # needsFullUserModel: the theme shows a user SELECTOR, so it asks for the list
    return f"[General]\nvariant={variant}\nneedsFullUserModel=true\n"


def render_all(themes_dir, variants=VARIANTS):
    """Write one theme directory per variant under themes_dir; returns the dirs."""
    import make_segment_display as SD
    out = []
    for v in variants:
        d = os.path.join(themes_dir, theme_id(v))
        os.makedirs(d, exist_ok=True)
        atomic_write(os.path.join(d, "metadata.desktop"), metadata_desktop(v))
        atomic_write(os.path.join(d, "theme.conf"), theme_conf(v))
        atomic_write(os.path.join(d, "Main.qml"), main_qml(v))
        # the display ships beside the mount: Main.qml names SegmentChar bare
        atomic_write(os.path.join(d, "SegmentChar.qml"), SD.segment_char_component())
        out.append(d)
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1:
        raise SystemExit(f"make_sddm: unknown argument {sys.argv[1]!r} (no modes; writes /tmp/el-sddm)")
    dirs = render_all("/tmp/el-sddm")
    print(f"rendered {len(dirs)} of {len(VARIANTS)} SDDM themes into /tmp/el-sddm")
