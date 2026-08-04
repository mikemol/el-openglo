#!/usr/bin/env python3
"""check_standards.py — STANDARDS.md names modules that actually apply them.

⚑ A STANDARDS DOCUMENT IS THE EASIEST THING IN A REPO TO LET ROT.  It is prose
about code, it is never executed, and it stays plausible long after the code
moved. This repo already learned that the expensive way: most of `cvd_gate.py`
went missing in the recovery — WCAG, APCA, the normalized-q metric — and nothing
noticed, because every file still byte-compiled and the only symptom was a
washed-out palette.

So the mapping is checked: every module STANDARDS.md names must exist, and every
attribute it credits with applying a standard must be present in that module.

    scripts/check_standards.py           # exit 0 iff every cited applier resolves
    scripts/check_standards.py --cited   # the (module, attribute) pairs it found

⚑ THIS CHECKS THE MAPPING, NOT THE MATHS.  Whether `apca_Lc` correctly implements
APCA is `cvd_gate --selftest`'s job, and it answers it against published reference
vectors. This answers the different question: does the thing the document credits
still exist? Both are needed — a correct implementation nobody can find is as
lost as an absent one.
"""
import importlib
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, "STANDARDS.md")

# `module.attr` mentions inside backticks are the appliers the doc credits.
CITE = re.compile(r"`([a-z_][a-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)`")

# Modules named in the doc that are not Python of ours (or are prose nouns).
NOT_OURS = {"theme", "pyproject", "apca", "wcag"}

# `cvd_gate.py` is a FILENAME, not an attribute reference — the citation regex
# cannot tell them apart, so the file extensions are named here.
NOT_ATTRS = {"py", "md", "toml", "json", "colors", "colorscheme"}


def cited():
    """[(module, attr)] pairs the document credits with applying a standard."""
    if not os.path.exists(DOC):
        return None
    out = []
    for m in CITE.finditer(open(DOC, encoding="utf-8").read()):
        mod, attr = m.group(1), m.group(2)
        if mod in NOT_OURS or attr in NOT_ATTRS:
            continue
        if not os.path.exists(os.path.join(ROOT, mod + ".py")):
            continue                      # not a module of ours; prose, not a citation
        out.append((mod, attr))
    return sorted(set(out))


def main(argv):
    known = {"--cited"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_standards: unknown flag {a!r}", file=sys.stderr)
            return 2
    pairs = cited()
    if pairs is None:
        print(f"check_standards: REFUSED — STANDARDS.md is absent; the standards "
              f"this project applies are recorded nowhere", file=sys.stderr)
        return 1
    if "--cited" in argv:
        for mod, attr in pairs:
            print(f"{mod}.{attr}")
        return 0
    if not pairs:
        print("check_standards: REFUSED — the document credits no applier at all; "
              "the citation format changed, or the scan is broken", file=sys.stderr)
        return 2

    sys.path.insert(0, ROOT)
    missing = []
    for mod, attr in pairs:
        try:
            m = importlib.import_module(mod)
        except Exception as e:            # noqa: BLE001
            missing.append((f"{mod}.{attr}", f"module will not import: {e}"))
            continue
        if not hasattr(m, attr):
            missing.append((f"{mod}.{attr}", "named in STANDARDS.md, absent from the module"))
    if missing:
        print(f"check_standards: REFUSED — {len(missing)} of {len(pairs)} cited "
              f"applier(s) do not resolve:", file=sys.stderr)
        for what, why in missing:
            print(f"    {what}: {why}", file=sys.stderr)
        return 1
    print(f"check_standards: {len(pairs)} of {len(pairs)} cited appliers resolve")
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

    pairs = cited()
    check("the document exists and cites appliers", bool(pairs), True)
    # ⚑ The scan must find the specific appliers this repo lost, or it is blind to
    # exactly the failure it was written for.
    flat = {f"{m}.{a}" for m, a in (pairs or [])}
    for needed in ("cvd_gate.apca_Lc", "cvd_gate.wcag_ratio", "cvd_gate.SECTORS"):
        check(f"cites {needed}", needed in flat, True)
    print("check_standards selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
