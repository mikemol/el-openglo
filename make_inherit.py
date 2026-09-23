#!/usr/bin/env python3
"""Inheriting icon + cursor themes (⊕ICONS-INHERIT, ⊕CURSOR-INHERIT; W31).

⚑ THESE THEMES DRAW NOTHING OF THEIR OWN, AND THAT IS THE DESIGN.  An icon set
is not a palette emission — but Breeze's icons are `FollowsColorScheme=true`:
they take their colours from kdeglobals at render time. So an icon theme that
INHERITS Breeze and is selected by the Look-and-Feel is how the solved palette
reaches every icon, with nothing retyped and no SVG shipped. The cursor theme
is the same move one level down: XCursor honours `Inherits=` in index.theme.
⚑ SINCE W36 THE CURSOR THEME ALSO DRAWS: make_cursors fills this theme's
cursors/ with phosphor glyphs from the palette (a cursor is a fixed image, so
inheritance alone could never colour it); Inherits= stays as the fallback for
every shape it does not draw.

The contract, read from the host (Plasma 6.7, 2026-09-21):
  - an icon theme is `[Icon Theme]` with Name, Comment, Inherits (a comma list
    ending in hicolor), Example, FollowsColorScheme, the size defaults, and a
    Directories= list — KIconTheme treats a theme with no directories as
    invalid, so one real directory ships (the segclock icon, so the entry is
    not a lie);
  - a cursor theme is `[Icon Theme]` with Name, Comment and Inherits — no
    Directories — plus the parent's `cursors/` reached through Inherits.

Which parent (DECISION, recorded): the Off variants have a DARK ground, so
they inherit breeze-dark icons and Breeze_Light cursors (light arrows on a
dark desktop); the Lit variants inherit breeze icons and breeze_cursors.

    make_inherit.py               # print every variant's index.theme
"""
import os
import sys
from emitters import atomic_write

VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
            "EL-Amber", "EL-Amber-Lit")


def is_lit(variant):
    return variant.endswith("-Lit")


def icon_theme_name(variant):
    return variant                       # the variant name already carries EL-


def cursor_theme_name(variant):
    return f"{variant}-cursors"


def icon_parents(variant):
    """The Inherits chain for the icon theme, hicolor last (the spec's fallback)."""
    return ["breeze", "hicolor"] if is_lit(variant) else ["breeze-dark", "breeze", "hicolor"]


def cursor_parent(variant):
    return "breeze_cursors" if is_lit(variant) else "Breeze_Light"


# the one directory the icon theme carries: the plasmoid's own icon
ICON_DIR = "256x256/apps"


def icon_index(variant):
    return (
        "[Icon Theme]\n"
        f"Name={icon_theme_name(variant)}\n"
        f"Comment=EL Openglo {variant} — Breeze icons recoloured by the EL colour scheme\n"
        f"Inherits={','.join(icon_parents(variant))}\n"
        "Example=folder\n"
        "FollowsColorScheme=true\n"
        "DisplayDepth=32\n"
        f"Directories={ICON_DIR}\n"
        "KDE-Extensions=.svg\n"
        "\n"
        f"[{ICON_DIR}]\n"
        "Size=256\n"
        "Context=Applications\n"
        "Type=Fixed\n"
    )


def cursor_index(variant):
    return (
        "[Icon Theme]\n"
        f"Name={cursor_theme_name(variant)}\n"
        f"Comment=EL Openglo {variant} cursors — phosphor glyphs, {cursor_parent(variant)} for the rest\n"
        f"Inherits={cursor_parent(variant)}\n"
    )


def cursor_theme_file(variant):
    """cursor.theme — the X11 (xcursor) discovery file beside index.theme."""
    return f"[Icon Theme]\nInherits={cursor_theme_name(variant)}\n"


def defaults_fragment(variant):
    """The Look-and-Feel `defaults` groups that select these themes."""
    return (
        "[kdeglobals][Icons]\n"
        f"Theme={icon_theme_name(variant)}\n\n"
        "[kcminputrc][Mouse]\n"
        f"cursorTheme={cursor_theme_name(variant)}\n\n"
    )


def render_all(variants, icons_root, icon_png=None):
    """Write usr/share/icons/<v>/ and <v>-cursors/ under `icons_root`.
    `icon_png(variant)` -> path of a 256px PNG to place in the icon theme's one
    directory as el-segclock.png; None leaves the directory present but empty."""
    written = {}
    for v in variants:
        idir = os.path.join(icons_root, icon_theme_name(v))
        os.makedirs(os.path.join(idir, ICON_DIR), exist_ok=True)
        atomic_write(os.path.join(idir, "index.theme"), icon_index(v))
        if icon_png is not None:
            src = icon_png(v)
            if src and os.path.isfile(src):
                import shutil
                from emitters import atomic_path
                with atomic_path(os.path.join(idir, ICON_DIR, "el-segclock.png")) as tmp:
                    shutil.copyfile(src, tmp)
        cdir = os.path.join(icons_root, cursor_theme_name(v))
        os.makedirs(cdir, exist_ok=True)
        atomic_write(os.path.join(cdir, "index.theme"), cursor_index(v))
        atomic_write(os.path.join(cdir, "cursor.theme"), cursor_theme_file(v))
        written[v] = (idir, cdir)
    return written


if __name__ == "__main__":
    for v in VARIANTS:
        print(f"── {icon_theme_name(v)} ──")
        print(icon_index(v))
        print(f"── {cursor_theme_name(v)} ──")
        print(cursor_index(v))
    sys.exit(0)
