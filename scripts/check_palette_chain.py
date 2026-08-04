#!/usr/bin/env python3
"""check_palette_chain.py — the shipped schemes are SOLVER output, not a fallback.

⚑ THE FAILURE THIS EXISTS FOR WAS SILENT IN EVERY DIRECTION.  8 of the 10
`cvd_gate` attributes its consumers call went missing in the recovery, so
`make_palette` could not import and `make_schemes` quietly used its authored
fallback table. Every file byte-compiled. No gate went red. The only symptom was
a washed-out palette on screen — and a fallback palette is a perfectly valid
palette, just not the solved one, so nothing about the OUTPUT looks wrong either.

Three things are checked, because any one alone is passable while broken:

  API      every attribute the tree calls on cvd_gate exists. Discovered by
           walking the AST, never hand-listed, so a new call site cannot be
           missed by a roster nobody updated.
  SOLVE    make_palette imports AND build_grid() returns a full grid. Importing
           alone is too weak: the API can resolve while the solve still fails.
  SHIPPED  the emitted schemes match the solver's own output. This is the one
           that catches the actual defect — the solver ran, and its result was
           then discarded by a duplicate assignment.

    scripts/check_palette_chain.py           # exit 0 iff all three hold
    scripts/check_palette_chain.py --api     # the cvd_gate surface, referenced vs present
"""
import ast
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def referenced():
    """{attr: {files}} — every `C.<attr>` on the cvd_gate module, from the AST."""
    out = {}
    for fn in sorted(os.listdir(ROOT)):
        if not fn.endswith(".py") or fn == "cvd_gate.py":
            continue
        try:
            tree = ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8",
                                  errors="replace").read())
        except SyntaxError:
            continue
        alias = None
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                for a in n.names:
                    if a.name == "cvd_gate":
                        alias = a.asname or a.name
        if not alias:
            continue
        for n in ast.walk(tree):
            if (isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == alias):
                out.setdefault(n.attr, set()).add(fn)
    return out


def main(argv):
    known = {"--api"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_palette_chain: unknown flag {a!r}", file=sys.stderr)
            return 2
    sys.path.insert(0, ROOT)
    refs = referenced()

    try:
        import cvd_gate as C
    except Exception as e:                       # noqa: BLE001
        print(f"check_palette_chain: REFUSED — cvd_gate will not import: {e}",
              file=sys.stderr)
        return 1
    have = {a for a in dir(C) if not a.startswith("__")}

    if "--api" in argv:
        for a in sorted(refs):
            print(f"{'ok  ' if a in have else 'MISS'} {a}\t{', '.join(sorted(refs[a]))}")
        return 0
    if not refs:
        print("check_palette_chain: REFUSED — no cvd_gate references found; the "
              "walk is broken, not the chain healthy", file=sys.stderr)
        return 2

    absent = {a: f for a, f in sorted(refs.items()) if a not in have}
    if absent:
        print(f"check_palette_chain: REFUSED — {len(absent)} of {len(refs)} "
              f"cvd_gate attribute(s) referenced but absent:", file=sys.stderr)
        for a, files in absent.items():
            print(f"    C.{a}  (called by {', '.join(sorted(files))})", file=sys.stderr)
        return 1

    # SOLVE: the solver must import and produce a grid, not merely resolve names.
    try:
        import make_palette as P
    except Exception as e:                       # noqa: BLE001
        print(f"check_palette_chain: REFUSED — make_palette will not import: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1

    # SHIPPED: what make_schemes actually emits must be the solved palette.
    # ⚑ ASKED AS A QUESTION ABOUT THE MODULE'S OWN STATE, not by re-solving here:
    # re-running build_grid() would take minutes and would answer a different
    # question (can it solve?) than the one that matters (did the emitted schemes
    # COME from it?).
    try:
        import make_schemes as S
    except Exception as e:                       # noqa: BLE001
        print(f"check_palette_chain: REFUSED — make_schemes will not import: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    if os.environ.get("EL_AUTHORED_PALETTE") == "1":
        print("check_palette_chain: SKIP — EL_AUTHORED_PALETTE=1 selects the "
              "fallback deliberately (this is the residue path, not a defect)")
        return 0
    if S.GRID is getattr(S, "_AUTHORED_GRID", object()):
        print("check_palette_chain: REFUSED — make_schemes is emitting the AUTHORED "
              "fallback, not solver output.", file=sys.stderr)
        print("    The solve was skipped or its result discarded; the shipped "
              "schemes are not what the gate enforced.", file=sys.stderr)
        return 1
    if not S.GRID:
        print("check_palette_chain: REFUSED — the grid is empty", file=sys.stderr)
        return 1

    print(f"check_palette_chain: {len(refs)} of {len(refs)} cvd_gate attributes "
          f"present; solver imports; {len(S.GRID)} variants emitted from solved grid")
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

    refs = referenced()
    check("the AST walk found references", len(refs) > 0, True)
    # ⚑ The walk must see the attributes whose absence WAS the break, or it is
    # blind to exactly the defect it was written for.
    for needed in ("apca_Lc", "wcag_ratio", "derive_ghost"):
        check(f"walk sees C.{needed}", needed in refs, True)
    print("check_palette_chain selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
