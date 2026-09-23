#!/usr/bin/env python3
"""make_gtk.py — the palette as GTK4/libadwaita CSS variables and a GTK3 @define-color sheet (⊕GTK, W17).

⚑ REBUILT.  ⊕GTK closed in session 14 (gtk/<id>/gtk{3,4}.css, every name verified
against the Adw CSS-variables reference) and its emitter, output and gate did
not survive the recovery; el-openglo-apply step 3 skipped it behind an isdir
guard, silently. Measured 2026-09-21 (W17), rebuilt from the reference read the
same day: https://gnome.pages.gitlab.gnome.org/libadwaita/doc/main/css-variables.html

⚑ HOW THE PALETTE REACHES GNOME, measured, not recalled.  libadwaita apps take
their colours from CSS variables on :root, and GTK4 loads ~/.config/gtk-4.0/
gtk.css for every app — including pure-libadwaita ones. So gtk4.css sets the
documented `--*-color` variables (the legacy @define-color names are emitted
too, marked compatibility by the reference). GTK3 apps read gtk3.css only
through a theme that forwards the names — adw-gtk3 is the standard one — so
gtk3.css is the @define-color set adw-gtk3 forwards. ⊕GTK-ADW's "unreachable
by design" was about THEMES; variables are the sanctioned channel and this
uses it. GNOME Shell (the top bar) is not reached from here: that is a
user-theme extension question, recorded, not claimed.

    make_gtk.py              # writes gtk/<variant>/{gtk3.css,gtk4.css}
    make_gtk.py --map        # variable -> palette role
"""
import os
import sys
from emitters import atomic_write

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

VARIANTS = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit",
            "EL-Amber", "EL-Amber-Lit"]

# libadwaita CSS variable -> palette role (make_preview.parse_scheme keys, or
# the composites make_firefox.roles() adds: ghost_seen / hover_fill / active_fill)
ADW_VARS = (
    ("--accent-bg-color", "sel"), ("--accent-fg-color", "sel_fg"), ("--accent-color", "accent"),
    ("--window-bg-color", "ground"), ("--window-fg-color", "window_fg"),
    ("--view-bg-color", "view_bg"), ("--view-fg-color", "phosphor"),
    ("--headerbar-bg-color", "panel"), ("--headerbar-fg-color", "phosphor"),
    ("--headerbar-border-color", "ghost_seen"), ("--headerbar-backdrop-color", "ground"),
    ("--headerbar-shade-color", "ghost_seen"), ("--headerbar-darker-shade-color", "ghost_seen"),
    ("--sidebar-bg-color", "panel"), ("--sidebar-fg-color", "phosphor"),
    ("--sidebar-backdrop-color", "ground"), ("--sidebar-border-color", "ghost_seen"),
    ("--sidebar-shade-color", "ghost_seen"),
    ("--secondary-sidebar-bg-color", "ground"), ("--secondary-sidebar-fg-color", "phosphor"),
    ("--secondary-sidebar-backdrop-color", "ground"), ("--secondary-sidebar-border-color", "ghost_seen"),
    ("--secondary-sidebar-shade-color", "ghost_seen"),
    ("--card-bg-color", "panel"), ("--card-fg-color", "phosphor"), ("--card-shade-color", "ghost_seen"),
    ("--thumbnail-bg-color", "panel"), ("--thumbnail-fg-color", "phosphor"),
    ("--overview-bg-color", "ground"), ("--overview-fg-color", "phosphor"),
    ("--dialog-bg-color", "panel"), ("--dialog-fg-color", "phosphor"),
    ("--popover-bg-color", "panel"), ("--popover-fg-color", "phosphor"), ("--popover-shade-color", "ghost_seen"),
    ("--active-toggle-bg-color", "active_fill"), ("--active-toggle-fg-color", "phosphor"),
    ("--shade-color", "ghost_seen"), ("--scrollbar-outline-color", "ghost_seen"),
)
# every --name above, verified against the reference (2026-09-21); check_gtk holds
# the emission to this set so a typo'd name cannot no-op in silence (session 14's hole)
ADW_NAMED = frozenset(v for v, _r in ADW_VARS) | frozenset({
    "--destructive-bg-color", "--destructive-fg-color", "--destructive-color",
    "--success-bg-color", "--success-fg-color", "--success-color",
    "--warning-bg-color", "--warning-fg-color", "--warning-color",
    "--error-bg-color", "--error-fg-color", "--error-color",
    "--border-color", "--border-opacity", "--dim-opacity", "--disabled-opacity",
    "--window-radius", "--standalone-color-oklab",
})

# GTK3 @define-color names adw-gtk3 forwards -> palette role
GTK3_DEFINES = (
    ("theme_bg_color", "ground"), ("theme_fg_color", "window_fg"),
    ("theme_base_color", "view_bg"), ("theme_text_color", "phosphor"),
    ("theme_selected_bg_color", "sel"), ("theme_selected_fg_color", "sel_fg"),
    ("theme_unfocused_bg_color", "ground"), ("theme_unfocused_fg_color", "phosphor"),
    ("theme_unfocused_base_color", "view_bg"), ("theme_unfocused_text_color", "phosphor"),
    ("theme_unfocused_selected_bg_color", "sel"), ("theme_unfocused_selected_fg_color", "sel_fg"),
    ("borders", "ghost_seen"), ("unfocused_borders", "ghost_seen"),
    ("headerbar_bg_color", "panel"), ("headerbar_fg_color", "phosphor"),
    ("headerbar_border_color", "ghost_seen"), ("headerbar_backdrop_color", "ground"),
    ("headerbar_shade_color", "ghost_seen"),
    ("sidebar_bg_color", "panel"), ("sidebar_fg_color", "phosphor"),
    ("sidebar_backdrop_color", "ground"), ("sidebar_shade_color", "ghost_seen"),
    ("card_bg_color", "panel"), ("card_fg_color", "phosphor"), ("card_shade_color", "ghost_seen"),
    ("dialog_bg_color", "panel"), ("dialog_fg_color", "phosphor"),
    ("popover_bg_color", "panel"), ("popover_fg_color", "phosphor"),
    ("accent_bg_color", "sel"), ("accent_fg_color", "sel_fg"), ("accent_color", "accent"),
    ("window_bg_color", "ground"), ("window_fg_color", "window_fg"),
    ("view_bg_color", "view_bg"), ("view_fg_color", "phosphor"),
)


def roles(variant):
    """{role: '#rrggbb'} — parse_scheme's roles plus the solved composites."""
    import make_firefox as MF
    r = MF.roles(variant)
    return {k: "#%02x%02x%02x" % tuple(v) for k, v in r.items() if not k.startswith("_")}


def gtk4_css(variant):
    r = roles(variant)
    lines = [f"/* EL Openglo ({variant}) — libadwaita CSS variables from the one palette.",
             " * Generated by make_gtk.py; edit the palette, not this file. */",
             ":root {"]
    for var, role in ADW_VARS:
        lines.append(f"  {var}: {r[role]};")
    lines.append("}")
    lines.append("/* legacy names, kept for compatibility (the reference marks them so) */")
    for name, role in GTK3_DEFINES:
        lines.append(f"@define-color {name} {r[role]};")
    return "\n".join(lines) + "\n"


def gtk3_css(variant):
    r = roles(variant)
    lines = [f"/* EL Openglo ({variant}) — GTK3 named colours, read through adw-gtk3.",
             " * Generated by make_gtk.py; edit the palette, not this file. */"]
    for name, role in GTK3_DEFINES:
        lines.append(f"@define-color {name} {r[role]};")
    return "\n".join(lines) + "\n"


def render_all(variants, out_map):
    written = []
    for v in variants:
        d = out_map[v]
        os.makedirs(d, exist_ok=True)
        for name, body in (("gtk3.css", gtk3_css(v)), ("gtk4.css", gtk4_css(v))):
            p = os.path.join(d, name)
            atomic_write(p, body)
            written.append(p)
    return written


if __name__ == "__main__":
    if "--map" in sys.argv:
        for var, role in ADW_VARS:
            print(f"{var:36} <- {role}")
        print(f"gtk3: {len(GTK3_DEFINES)} @define-color names via adw-gtk3")
        sys.exit(0)
    outs = {v: os.path.join(ROOT, "gtk", v) for v in VARIANTS}
    w = render_all(VARIANTS, outs)
    print(f"make_gtk: wrote {len(w)} files for {len(VARIANTS)} variants under gtk/")
