#!/usr/bin/env python3
"""check_consumers.py — the research pipeline imports cleanly.

Compiling proves syntax; IMPORTING runs the module's top level and resolves its
own imports, so it is the stronger witness that the recovered pipeline is
actually wired together.  These are the modules the archive reconstructed from
context rather than mechanical replay, which is exactly why they get a check
that executes something.

    scripts/check_consumers.py           # the verdict, as opa_gate consumers decides it
    scripts/check_consumers.py --json [PY...]  # the measurement policy/consumers.rego decides;
                                               # PY modules are PLANTED beside the roster (W75)
    scripts/check_consumers.py --list    # the modules checked

A module whose third-party dependency is absent (PIL, fontTools) reports SKIP,
not failure — a missing optional dependency is a fact about this machine, not
about the recovery.  ⚑ Skips are COUNTED and PRINTED: `n ok, m skipped of k` is
the honest report, because "everything that ran, ran" is not "everything ran".
"""
import importlib
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The reconstructed research pipeline — the modules most at risk from the
# recovery, each importing the segment API this repo had to rebuild.
#
# ⚑ THE COLOUR CHAIN IS HERE BECAUSE ITS ABSENCE WAS THE GAP.  This roster once
# held only the SEGMENT pipeline, and the gate was correct for that scope — but
# scope was the whole problem: cvd_gate -> make_palette -> make_schemes was
# broken (8 of 10 referenced cvd_gate attributes absent) and NOTHING went red.
# check_compiles passed, because the files byte-compile; the only symptom was a
# washed-out palette on screen, which is what a scheme looks like when the gate
# that enforced its separation never ran.
#
# The rule this encodes: a module that DERIVES what ships belongs in an import
# gate, not merely a compile gate.
MODULES = (
    # segment pipeline
    "segment_topology", "glyph_match", "render_showcase",
    "project_font", "make_glyph_ink", "display_types",
    # colour chain — cvd_gate is the authority, make_palette the solver,
    # make_schemes the emitter that every other target reads
    "cvd_gate", "make_palette", "make_schemes", "make_preview",
)


def measure(root=ROOT, modules=MODULES):
    """The MEASUREMENT policy/consumers.rego decides (W50): per roster module,
    whether its file exists and what IMPORTING it did — `ok`, or the exception
    (type, message) and, for a ModuleNotFoundError, the missing name and whether
    that name is a module of THIS tree (ours: a defect) or not (third-party: a
    fact about the machine). No verdict here."""
    if root not in sys.path:
        sys.path.insert(0, root)
    cases = []
    for m in modules:
        c = {"id": m, "present": os.path.exists(os.path.join(root, m + ".py")),
             "imported": None, "error": None, "missing": None, "missing_is_ours": None}
        if c["present"]:
            try:
                importlib.import_module(m)
                c["imported"] = True
            except ModuleNotFoundError as e:
                c.update(imported=False, error=f"ModuleNotFoundError: {e}", missing=e.name,
                         missing_is_ours=e.name is None
                         or os.path.exists(os.path.join(root, str(e.name) + ".py")))
            except Exception as e:                  # noqa: BLE001 - any import-time error
                c.update(imported=False, error=f"{type(e).__name__}: {e}")
        cases.append(c)
    return {"cases": cases}


def main(argv):
    known = {"--list", "--json"}
    for a in argv[1:]:
        if a.startswith("--") and a not in known:
            print(f"check_consumers: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--list" in argv:
        print("\n".join(MODULES))
        return 0
    if "--json" in argv:
        import json
        doc = measure()
        # W75: .py operands are PLANTED — imported by the same routine, beside the roster
        for a in (x for x in argv[1:] if not x.startswith("--")):
            p = a if os.path.isabs(a) else os.path.join(ROOT, a)
            doc["cases"] += measure(os.path.dirname(p), (os.path.basename(p)[:-3],))["cases"]
        print(json.dumps(doc, indent=1))
        return 0
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import opa_gate
    return opa_gate.gate("consumers")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # The MEASUREMENT can see; what is a defect is policy/consumers_test.rego's (W50).
    check("roster is non-empty", len(MODULES) > 0, True)
    real = measure()["cases"]
    check("every roster module is measured", [c["id"] for c in real], list(MODULES))
    # ⚑ PLANTED MODULES, because the old selftest never showed an import FAILURE
    # could be seen — only that the roster's files existed.
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        for name, body in (("pk_boom", "raise ValueError('top-level failure')\n"),
                           ("pk_theirs", "import no_such_thirdparty_pkg_x\n"),
                           ("pk_fine", "X = 1\n")):
            open(os.path.join(td, name + ".py"), "w").write(body)
        got = {c["id"]: c for c in measure(td, ("pk_boom", "pk_theirs", "pk_fine", "pk_absent"))["cases"]}
        sys.path.remove(td)
    check("a top-level exception is seen", (got["pk_boom"]["imported"], got["pk_boom"]["error"]),
          (False, "ValueError: top-level failure"))
    check("a missing third-party module is seen as not ours",
          (got["pk_theirs"]["missing"], got["pk_theirs"]["missing_is_ours"]),
          ("no_such_thirdparty_pkg_x", False))
    check("a clean module imports", got["pk_fine"]["imported"], True)
    check("an absent module file is seen", (got["pk_absent"]["present"], got["pk_absent"]["imported"]),
          (False, None))
    print("check_consumers selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
