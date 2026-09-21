"""emitters — the generator roster, in dependency order, and how to run it.

⚑ ONE ROSTER, TWO READERS.  scripts/check_emitters_run.py (the @EMITTERS gate)
and make_deb.stage() (the install staging, for the .deb and the ebuild) must
agree on which generators write the tree and in what order. They did not have
to: the gate carried the list and the packager assumed the outputs were already
on disk. On this checkout they were (gitignored, written by earlier runs); on a
git-r3 clone they are not, and `x11-themes/el-openglo-9999` installed with NO
Aurorae decorations, NO Plasma style and NO wallpaper — the `isdir` guards in
system_mapping skipped them in silence (measured 2026-09-21, `qlist`).

    emitters.run_all(root)   # run every generator in order; returns [(module, rc)]
"""
import os
import subprocess
import sys

# (module, why it sits here) — dependency order, not alphabetical.
ORDER = (
    ("make_schemes",   "writes the .colors files every other emitter reads"),
    ("make_preview",   "owns parse_scheme; renders the previews"),
    ("make_chrome",    "browser manifests, from the scheme tokens"),
    ("make_konsole",   "terminal scheme, from the scheme tokens"),
    ("make_aurorae",   "window decoration, from GRID"),
    ("make_plasma",    "Plasma theme SVGs, from GRID"),
    ("make_wallpaper", "wallpaper; sources tokens with a standalone fallback"),
    ("make_clock",     "the segment-clock plasmoid packages (plasma-clock/), from GRID"),
    ("make_css",       "the palette as CSS custom properties, from GRID (W19)"),
    ("make_union",     "Union styles: Breeze with its alphas solved, from the schemes (W14)"),
    ("make_windows",   "Windows .theme per variant: wallpaper + accent + colour table (W16)"),
    ("make_firefox",   "Firefox theme manifests, Firefox's own key vocabulary (W15)"),
)

# Emitters that need an input this machine may not have.  Absent -> SKIP, named.
EXTERNAL = {
    "make_kvantum": ("/tmp/KvFlat.kvconfig",
                     "recolours the upstream KvFlat theme; stage it to run this"),
}


# ⚑ THE EMITTERS WHOSE OUTPUT THE INSTALL MAPPING COPIES FROM THE TREE.  The
# others (chrome, konsole, plymouth, live wallpaper, marquee) are rendered by
# make_deb.stage() itself, straight into the DESTDIR via their render_all(); their
# __main__ blocks are DEMOS that write under /tmp. Running those under Portage's
# sandbox died with EACCES on /tmp/EL-Openglo.colorscheme and a cairo write
# error (emerge, 2026-09-21) — the first thing the sandbox proved that
# check_ebuild's stated weakness said it could not. Staging runs THIS subset.
STAGE = ("make_schemes", "make_aurorae", "make_plasma", "make_wallpaper", "make_clock")


def run_all(root, python=None, quiet=True, only=None):
    """Run every emitter in ORDER (or the `only` subset) from `root`.

    Returns [(module, returncode, stderr_tail)]. A non-zero rc is returned, not
    raised, so a caller can report n of m rather than stop at the first."""
    out = []
    for mod, _why in ORDER:
        if only is not None and mod not in only:
            continue
        r = subprocess.run([python or sys.executable, os.path.join(root, mod + ".py")],
                           cwd=root, capture_output=True, text=True)
        out.append((mod, r.returncode, r.stderr.strip()[-400:]))
    return out
