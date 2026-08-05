#!/usr/bin/env python3
"""check_geometry_source.py — every surface reads ONE geometry, or names its own.

⚑ THE DEFECT THIS MEASURES IS THE COLOUR DEFECT ON THE SHAPE AXIS.  The design
log states it outright: "GEOMETRY IS A TOKEN SET EXACTLY LIKE COLOR. I did this
for COLOR (palette solver feeds all) but NOT for GEOMETRY (each surface carries
its own shape copy)." Four surfaces — wallpaper, clock, plymouth, marquee — each
re-implemented the segment shapes while segment_topology, the emitter built to
supply them, fed none of them.

check_token_source.py asks this about colour. Nothing asked it about shape, so
the four-silo state was invisible to every gate while being named in the log.

    scripts/check_geometry_source.py          # exit 0 iff no surface owns geometry
    scripts/check_geometry_source.py --map    # surface -> what it reads, or its own

⚑ A SURFACE MAY LEGITIMATELY CHOOSE A FORMAT; IT MAY NOT CHOOSE A SHAPE.  The
per-surface decision is "7" for digits or "22" for alphanumerics — a projection
of the one lattice. Carrying a stroke table is a different act, and that is what
this looks for.
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The authorities: importing either of these IS reading the shared geometry.
AUTHORITIES = ("segment_topology", "make_segment_display")

# Names that, assigned at module level, mean this file OWNS a stroke table.
# Measured from the four silos the log names, not guessed.
OWN_GEOMETRY = ("SEGS", "SEG", "SEVENSEG", "SEG_STROKE", "DIGIT", "DIGITS",
                "STROKES", "litPrimitives")

# Surfaces that render segments. A file here must read an authority.
SURFACES = ("make_wallpaper.py", "make_wallpaper_live.py", "make_clock.py",
            "make_plymouth.py", "make_notify_marquee.py")


def _module_assigns(path):
    """Module-level names bound to a LITERAL stroke table.

    ⚑ THE NAME IS NOT THE DEFECT; THE LITERAL IS.  A surface may hold `SEGS`
    perfectly well when its value is DERIVED — `SEGS = _ST.seg7_svg_grid()` reads
    the substrate and is exactly what de-siloing looks like. What makes a silo is
    a hand-authored dict or a string of segment labels: a shape this file decided.
    Flagging the name alone reported the fix as the defect."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except (SyntaxError, OSError):
        return set()

    def _is_literal(node):
        # a dict/set/list literal, or a comprehension over one — a table this
        # file authored. A Call (seg7_svg_grid(), project(...)) is derivation.
        return isinstance(node, (ast.Dict, ast.Set, ast.List, ast.Tuple))

    out = set()
    for node in tree.body:
        target, value = None, None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        if isinstance(target, ast.Name) and value is not None and _is_literal(value):
            out.add(target.id)
    return out


def _imports(path):
    """Top-level module names this file imports, at any depth."""
    try:
        tree = ast.parse(open(path, encoding="utf-8", errors="replace").read())
    except (SyntaxError, OSError):
        return set()
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module.split(".")[0])
    return out


def survey():
    """[(surface, reads, owns)] — what each renders from."""
    out = []
    for fn in SURFACES:
        path = os.path.join(ROOT, fn)
        if not os.path.isfile(path):
            continue
        reads = sorted(_imports(path) & set(AUTHORITIES))
        owns = sorted(_module_assigns(path) & set(OWN_GEOMETRY))
        out.append((fn, reads, owns))
    return out


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_geometry_source: unknown flag {a!r}", file=sys.stderr)
            return 2
    rows = survey()
    if not rows:
        print("check_geometry_source: REFUSED — no surfaces found; the roster is "
              "stale, not the tree de-siloed", file=sys.stderr)
        return 2
    if "--map" in argv:
        for fn, reads, owns in rows:
            r = ", ".join(reads) if reads else "(NONE)"
            o = f"  owns: {', '.join(owns)}" if owns else ""
            print(f"{fn}\t{r}{o}")
        return 0

    bad = [(fn, reads, owns) for fn, reads, owns in rows if owns or not reads]
    if bad:
        print(f"check_geometry_source: REFUSED — {len(bad)} of {len(rows)} "
              f"surface(s) do not render from the shared geometry:", file=sys.stderr)
        for fn, reads, owns in bad:
            why = []
            if not reads:
                why.append("reads no geometry authority")
            if owns:
                why.append(f"carries its own table ({', '.join(owns)})")
            print(f"    {fn}: {'; '.join(why)}", file=sys.stderr)
        print(f"    A surface chooses a FORMAT (\"7\" digits / \"22\" alphanumeric);",
              file=sys.stderr)
        print(f"    carrying a stroke table is a re-implementation.", file=sys.stderr)
        print(f"  fixes: {len(bad)}", file=sys.stderr)
        return 1
    print(f"check_geometry_source: {len(rows)} of {len(rows)} surfaces render "
          f"from the shared geometry")
    return 0


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    rows = survey()
    check("the roster resolves to real files", len(rows) > 0, True)
    stale = [f for f in SURFACES if not os.path.isfile(os.path.join(ROOT, f))]
    check(f"no surface in the roster is missing ({stale})", stale, [])
    # ⚑ THE SCAN MUST SEE AN OWNED TABLE, or its all-clear means nothing.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "s.py")
        open(p, "w").write('SEGS = {"A": ("h", 0, 1, 0)}\n')
        check("sees a module-level stroke table",
              bool(_module_assigns(p) & set(OWN_GEOMETRY)), True)
        # ⚑ AND A DERIVED TABLE IS NOT A SILO — the distinction the check turns
        # on. Without this the fix reads as the defect and de-siloing can never
        # go green.
        p3 = os.path.join(td, "d.py")
        open(p3, "w").write("import segment_topology as _ST\n"
                            "SEGS = _ST.seg7_svg_grid()\n")
        check("a DERIVED table is not owned",
              bool(_module_assigns(p3) & set(OWN_GEOMETRY)), False)
        # a comprehension is still authoring: it names the shapes here
        p4 = os.path.join(td, "e.py")
        open(p4, "w").write('SEGS = {"A": ("h", 0, 0), "B": ("v", 1, 0)}\n')
        check("a literal dict is owned",
              bool(_module_assigns(p4) & set(OWN_GEOMETRY)), True)
        p2 = os.path.join(td, "t.py")
        open(p2, "w").write("import segment_topology as ST\nx = ST.SEG22\n")
        check("sees an authority import",
              bool(_imports(p2) & set(AUTHORITIES)), True)
    print("check_geometry_source selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
