#!/usr/bin/env python3
"""check_consumers.py — the research pipeline imports cleanly.

Compiling proves syntax; IMPORTING runs the module's top level and resolves its
own imports, so it is the stronger witness that the recovered pipeline is
actually wired together.  These are the modules the archive reconstructed from
context rather than mechanical replay, which is exactly why they get a check
that executes something.

    scripts/check_consumers.py           # exit 0 iff each imports
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
MODULES = ("segment_topology", "glyph_match", "render_showcase",
           "project_font", "make_glyph_ink", "display_types")


def main(argv):
    known = {"--list"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_consumers: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--list" in argv:
        print("\n".join(MODULES))
        return 0
    sys.path.insert(0, ROOT)
    ok, skipped, failed = [], [], []
    for m in MODULES:
        if not os.path.exists(os.path.join(ROOT, m + ".py")):
            failed.append((m, "module file absent"))
            continue
        try:
            importlib.import_module(m)
            ok.append(m)
        except ModuleNotFoundError as e:
            # a MISSING module of our own is a failure; a missing third-party is a skip
            if e.name in (None,) or os.path.exists(os.path.join(ROOT, str(e.name) + ".py")):
                failed.append((m, f"{type(e).__name__}: {e}"))
            else:
                skipped.append((m, str(e.name)))
        except Exception as e:                      # noqa: BLE001 - any import-time error
            failed.append((m, f"{type(e).__name__}: {e}"))
    total = len(MODULES)
    if failed:
        print(f"check_consumers: REFUSED — {len(failed)} of {total} failed to import:",
              file=sys.stderr)
        for m, why in failed:
            print(f"    {m}: {why}", file=sys.stderr)
        return 1
    note = "".join(f"\n    SKIP {m} (needs {dep})" for m, dep in skipped)
    print(f"check_consumers: {len(ok)} ok, {len(skipped)} skipped of {total}{note}")
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

    check("roster is non-empty", len(MODULES) > 0, True)
    stale = [m for m in MODULES if not os.path.exists(os.path.join(ROOT, m + ".py"))]
    check(f"no module in the roster is missing ({stale})", stale, [])
    print("check_consumers selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
