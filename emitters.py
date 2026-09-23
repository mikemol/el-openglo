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

# ⚑ THE ONE LICENCE DECLARATION (W44, operator 2026-09-22: Apache-2.0, not GPL-3).
# Every generator that writes a licence into emitted metadata — KPackage
# metadata.json "License", .desktop `License=` / `X-KDE-PluginInfo-License=` —
# imports THIS, never a literal, so a relicence is one edit. An SPDX id: KPackage,
# Gentoo and PEP 639 all accept it verbatim. scripts/check_license.py measures
# every declaration site and policy/license.rego refuses any other id, and any
# generator site that spells the id as a literal instead of naming this constant.
# ⚑ NOT FOR DERIVED THIRD-PARTY WORK: make_kvantum recolours KvFlat (GPL-family,
# upstream's licence preserved) and must never declare this.
LICENSE_SPDX = "Apache-2.0"

# ⚑ THE THIRD-PARTY PARTS, DECLARED ONCE: scripts/check_license.py lists them as
# excluded from the Apache population, and make_deb.copyright_text() gives each
# one that SHIPS (`files` non-empty: DEP-5 globs under the .deb root) its own
# stanza in /usr/share/doc/<pkg>/copyright. `files: ()` = not in the package.
# KvFlat: Kvantum's source headers read "GPL ... version 3 of the License, or (at
# your option) any later version" (tsujan/Kvantum, read 2026-09-23).
THIRD_PARTY = (
    {"what": "overlay/dev-python/colorspacious", "spdx": "MIT", "files": (),
     "copyright": "Nathaniel J. Smith", "note": "upstream's ebuild; overlay only, not in the package"},
    {"what": "KvFlat, recoloured by make_kvantum", "spdx": "GPL-3.0-or-later",
     "files": ("usr/share/el-openglo/kvantum/*",),
     "copyright": "Pedram Pourang (tsujan), the Kvantum authors",
     "note": "a recolour of KvFlat from https://github.com/tsujan/Kvantum is a derived work and keeps upstream's licence"},
    {"what": "DSEG fonts, named in make_font.DSEG_NOTE", "spdx": "OFL-1.1", "files": (),
     "copyright": "keshikan", "note": "named only; not shipped"},
    {"what": "Liberation Mono, rasterised by make_notify_marquee", "spdx": "OFL-1.1",
     "files": ("usr/share/plasma/plasmoids/org.el.notifymarquee*",),
     "copyright": "Red Hat, Inc. (Liberation fonts)",
     "note": "the marquee's dot-matrix glyphs are rasterised from Liberation Mono at build time"},
)

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
    ("make_gtk",       "GTK4/libadwaita :root variables + GTK3 @define-color (⊕GTK, rebuilt W17)"),
    ("make_font",      "the segment and matrix fonts, TTF + SVG, from the substrate (⊕SEG-FONT family, rebuilt W24)"),
)

# Emitters that need an input this machine may not have.  Absent -> SKIP, named.
EXTERNAL = {
    "make_kvantum": ("/tmp/KvFlat.kvconfig",
                     "recolours the upstream KvFlat theme; stage it to run this"),
}


# ⚑ ONE ROSTER, THREE READERS — AND THE THIRD DISCOVERED ITS OWN (W65,
# 2026-09-22).  The docstring above says "one roster, two readers" and was true
# when written; scripts/check_token_source.py is the third, and it built its
# population from `os.listdir(ROOT)` filtered to `make_*.py`.  A DISCOVERED
# population cannot tell a clean tree from a deleted one: remove make_css.py and
# that check reports "15 of 15 emitters source from the palette" and exits 0.
# n of n is green for every n.
#
# ⚑ SO THE ROSTER IS DECLARED WITH A ROLE, AND THE TREE IS CHECKED AGAINST IT
# rather than the other way round.  Declaring the MEMBERS is the roster's job;
# what must never be typed is a COUNT, which would have to be maintained by
# whoever broke the invariant.  A new make_*.py that nobody declares REFUSES, and
# so does a declared one that vanishes — drift is visible in both directions.
ROLES = {
    # authorities — every other target reads its tokens through these
    "make_palette":         "authority",   # SOLVES the palette, upstream of all
    "make_schemes":         "authority",   # owns GRID, emits the .colors files
    "make_preview":         "authority",   # owns parse_scheme
    # colour emitters — each MUST read an authority (@TOKENS)
    "make_aurorae":         "emitter",
    "make_chrome":          "emitter",
    "make_clock":           "emitter",
    "make_css":             "emitter",
    "make_cursors":         "emitter",     # phosphor XCursor glyphs per variant (W36)
    "make_firefox":         "emitter",
    "make_gtk":             "emitter",
    "make_konsole":         "emitter",
    "make_kvantum":         "emitter",
    "make_notify_marquee":  "emitter",
    "make_plasma":          "emitter",
    "make_plymouth":        "emitter",
    "make_sddm":            "emitter",     # the greeter: baked per variant (W66)
    "make_taskswitch":      "emitter",
    "make_union":           "emitter",
    "make_wallpaper":       "emitter",
    "make_wallpaper_live":  "emitter",
    "make_windows":         "emitter",
    # generators that carry NO colour, each with the reason it is exempt
    "make_font":            "colourless",  # glyph outlines only
    "make_glyph_ink":       "colourless",  # an ink field from font winding
    "make_segment_display": "colourless",  # QML geometry; colour bound by caller
    "make_inherit":         "colourless",  # icon/cursor themes that INHERIT Breeze;
                                           # the palette reaches icons through
                                           # FollowsColorScheme, not this file (W31),
                                           # and cursors through make_cursors (W36)
    "make_deb":             "packager",    # stages what the emitters produced
}


def declared(role=None):
    """The declared module names, optionally of one role."""
    return sorted(m for m, r in ROLES.items() if role is None or r == role)


def drift(root):
    """([undeclared], [absent]) — how the TREE differs from the declaration.

    ⚑ BOTH DIRECTIONS, because each is a different defect. An UNDECLARED
    make_*.py is a generator no gate ranges over — it can compute its own colours
    unseen, which is the exact defect check_token_source exists to catch and the
    one make_wallpaper was committing. An ABSENT declared module is a deletion
    that every n-of-n check would otherwise absorb silently."""
    found = {f[:-len(".py")] for f in os.listdir(root)
             if f.startswith("make_") and f.endswith(".py")}
    return sorted(found - set(ROLES)), sorted(set(ROLES) - found)


# ⚑ THE EMITTERS WHOSE OUTPUT THE INSTALL MAPPING COPIES FROM THE TREE.  The
# others (chrome, konsole, plymouth, live wallpaper, marquee) are rendered by
# make_deb.stage() itself, straight into the DESTDIR via their render_all(); their
# __main__ blocks are DEMOS that write under /tmp. Running those under Portage's
# sandbox died with EACCES on /tmp/EL-Openglo.colorscheme and a cairo write
# error (emerge, 2026-09-21) — the first thing the sandbox proved that
# check_ebuild's stated weakness said it could not. Staging runs THIS subset.
STAGE = ("make_schemes", "make_aurorae", "make_plasma", "make_wallpaper", "make_clock", "make_font")


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


def main(argv):
    """⚑ THE ROSTER ANSWERS FOR ITSELF. Without a mode, "does the declaration
    match the tree" is a question every reader answers with an inline script —
    which is judgement in the turn, re-derived differently by the next reader."""
    known = {"--roster", "--drift"}
    for a in argv[1:]:
        if a not in known:
            print(f"emitters: unknown flag {a!r}", file=sys.stderr)
            return 2
    root = os.path.dirname(os.path.abspath(__file__))
    undeclared, absent = drift(root)
    if "--roster" in argv:
        for role in ("authority", "emitter", "colourless", "packager"):
            names = declared(role)
            print(f"  {role:11s} {len(names):2d}  {', '.join(names)}")
        print(f"\nemitters: {len(ROLES)} declared module(s); "
              f"{len(ORDER)} run in order, {len(STAGE)} staged, {len(EXTERNAL)} external")
        return 0
    if undeclared or absent:
        print(f"emitters: REFUSED — the tree and the roster disagree "
              f"({len(undeclared)} undeclared, {len(absent)} absent of "
              f"{len(ROLES)} declared):", file=sys.stderr)
        for m in undeclared:
            print(f"    undeclared  {m}.py — a generator no gate ranges over; "
                  f"give it a role in emitters.ROLES", file=sys.stderr)
        for m in absent:
            print(f"    absent      {m}.py — declared and not in the tree", file=sys.stderr)
        return 1
    print(f"emitters: {len(ROLES)} of {len(ROLES)} declared module(s) present, "
          f"and the tree adds none")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
