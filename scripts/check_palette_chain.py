#!/usr/bin/env python3
"""check_palette_chain.py — the shipped schemes are SOLVER output, not a fallback.

⚑ THE FAILURE THIS EXISTS FOR WAS SILENT IN EVERY DIRECTION.  8 of the 10
`cvd_gate` attributes its consumers call went missing in the recovery, so
`make_palette` could not import and `make_schemes` quietly used its authored
fallback table. Every file byte-compiled. No gate went red. The only symptom was
a washed-out palette on screen — and a fallback palette is a perfectly valid
palette, just not the solved one, so nothing about the OUTPUT looks wrong either.

Three things are measured, because any one alone is passable while broken:

  API      every attribute the tree calls on cvd_gate, and whether cvd_gate has
           it. Discovered by walking the AST, never hand-listed, so a new call
           site cannot be missed by a roster nobody updated.
  SOLVE    whether make_palette imports. The API can resolve while the solve
           still fails.
  SHIPPED  whether make_schemes.GRID IS its _AUTHORED_GRID fallback, and how many
           variants it holds. This catches the actual defect — the solver ran,
           and its result was then discarded by a duplicate assignment.

    scripts/check_palette_chain.py            # the verdict, as opa_gate palette_chain decides it
    scripts/check_palette_chain.py --json     # the measurement policy/palette_chain.rego decides
    scripts/check_palette_chain.py --api      # the cvd_gate surface, referenced vs present
    scripts/check_palette_chain.py --selftest # the measurement can SEE each defect

That each must hold — and that EL_AUTHORED_PALETTE=1 withholds the SHIPPED
verdict (the residue path, chosen deliberately) — is policy/palette_chain.rego's
ruling (W50).

WEAKNESS: SHIPPED asks the module's own state (identity with the fallback), not
the emitted files; re-running build_grid() would take minutes and answer a
different question (can it solve?).
"""
import ast
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def referenced():
    """{attr: {files}} — every `C.<attr>` on the cvd_gate module, from the AST."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import git_tracked                 # the tree is what git tracks, not the disk
    out = {}
    for fn in git_tracked.files(":(glob)*.py", root=ROOT):
        if fn == "cvd_gate.py":
            continue
        try:
            tree = ast.parse(open(os.path.join(ROOT, fn), encoding="utf-8",
                                  errors="replace").read())
        except SyntaxError:
            continue
        out_f = _attrs(tree)
        for a in out_f:
            out.setdefault(a, set()).add(fn)
    return out


def _attrs(tree):
    """The attributes read off whatever name `cvd_gate` is imported as."""
    alias = None
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name == "cvd_gate":
                    alias = a.asname or a.name
    if not alias:
        return set()
    return {n.attr for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
            and n.value.id == alias}


def _import(name):
    """(module, None) or (None, 'Type: message')."""
    try:
        return __import__(name), None
    except Exception as e:                       # noqa: BLE001
        return None, f"{type(e).__name__}: {e}"


def measure():
    """The MEASUREMENT policy/palette_chain.rego decides: one case per referenced
    cvd_gate attribute (its callers, whether cvd_gate has it), each module's import
    error, and make_schemes' grid facts."""
    sys.path.insert(0, ROOT)
    refs = referenced()
    C, cvd_err = _import("cvd_gate")
    have = {a for a in dir(C) if not a.startswith("__")} if C else set()
    out = {"cvd_gate_error": cvd_err, "make_palette_error": None, "make_schemes_error": None,
           "authored_env": os.environ.get("EL_AUTHORED_PALETTE") == "1",
           "grid_is_authored": None, "grid_count": None,
           "cases": [{"id": a, "files": sorted(f), "present": a in have}
                     for a, f in sorted(refs.items())]}
    _P, out["make_palette_error"] = _import("make_palette")
    S, out["make_schemes_error"] = _import("make_schemes")
    if S is not None:
        out["grid_is_authored"] = S.GRID is getattr(S, "_AUTHORED_GRID", object())
        out["grid_count"] = len(S.GRID or ())
    return out


def main(argv):
    known = {"--api", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_palette_chain: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--api" in argv:
        m = measure()
        if m["cvd_gate_error"]:
            print(f"check_palette_chain: cvd_gate will not import — {m['cvd_gate_error']}",
                  file=sys.stderr)
            return 2
        for c in m["cases"]:
            print(f"{'ok  ' if c['present'] else 'MISS'} {c['id']}\t{', '.join(c['files'])}")
        return 0
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import opa_gate
    return opa_gate.gate("palette_chain")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    m = measure()
    check("the AST walk found references", len(m["cases"]) > 0, True)
    # ⚑ The walk must see the attributes whose absence WAS the break, or it is
    # blind to exactly the defect it was written for.
    #
    # ⚑ `derive_ghost` WAS ON THIS LIST AND IS NO LONGER REFERENCED BY ANY
    # CONSUMER — retired from make_clock on 2026-09-20 (W8) when the surfaces
    # switched to the palette's solved fg_in. The arm then failed, reporting a
    # fact about the FIXTURE (a name pinned to the tree's state when the check
    # was written) as a fact about the WALK. The walk's ability to see an
    # attribute is proved on a planted module below, where the reference cannot
    # go away; the live list keeps only what the chain still reads.
    ids = {c["id"] for c in m["cases"]}
    for needed in ("apca_Lc", "wcag_ratio"):
        check(f"walk sees C.{needed}", needed in ids, True)
    seen = _attrs(ast.parse("import cvd_gate as C\nx = C.derive_ghost\ny = C.nothing_here\n"))
    check("walk sees a planted C.derive_ghost", "derive_ghost" in seen, True)
    check("...and a planted attribute cvd_gate lacks", "nothing_here" in seen, True)
    # ⚑ THE MEASUREMENT MUST SEE EACH DEFECT (that it is DENIED is
    # policy/palette_chain_test.rego's ruling). The recovery's break: an attribute
    # the tree calls is gone from cvd_gate.
    import cvd_gate as C
    saved = C.wcag_ratio
    try:
        del C.wcag_ratio
        c = next(c for c in measure()["cases"] if c["id"] == "wcag_ratio")
        check("an attribute removed from cvd_gate is measured absent", c["present"], False)
    finally:
        C.wcag_ratio = saved
    # the second half of the break: make_schemes emitting its authored fallback
    import make_schemes as S
    if hasattr(S, "_AUTHORED_GRID"):
        grid = S.GRID
        try:
            S.GRID = S._AUTHORED_GRID
            check("a grid that IS the authored fallback is measured", measure()["grid_is_authored"], True)
        finally:
            S.GRID = grid
    else:
        print("  SKIP make_schemes has no _AUTHORED_GRID to plant")
    check("the live grid is not the fallback", m["grid_is_authored"], False)
    print("check_palette_chain selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
