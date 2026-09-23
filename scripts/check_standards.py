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
The requirement is policy/standards.rego (decided by scripts/opa_gate.py
standards); this file MEASURES each cited (module, attr): does the module
import, and does it carry the attribute.

    scripts/check_standards.py           # the verdict, as opa_gate standards decides it
    scripts/check_standards.py --json    # the measurement policy/standards.rego decides
    scripts/check_standards.py --cited   # the (module, attribute) pairs it found
    scripts/check_standards.py --selftest

⚑ THIS CHECKS THE MAPPING, NOT THE MATHS.  Whether `apca_Lc` correctly implements
APCA is `cvd_gate --selftest`'s job, and it answers it against published reference
vectors. This answers the different question: does the thing the document credits
still exist? Both are needed — a correct implementation nobody can find is as
lost as an absent one.  Weakness: a citation is a backticked `module.attr` whose
module is a .py at the root; a citation in another form is not seen.
"""
import importlib
import json
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


def cited(doc=DOC):
    """[(module, attr)] pairs the document credits with applying a standard."""
    if not os.path.exists(doc):
        return None
    out = []
    with open(doc, encoding="utf-8") as fh:
        text = fh.read()
    for m in CITE.finditer(text):
        mod, attr = m.group(1), m.group(2)
        if mod in NOT_OURS or attr in NOT_ATTRS:
            continue
        if not os.path.exists(os.path.join(ROOT, mod + ".py")):
            continue                      # not a module of ours; prose, not a citation
        out.append((mod, attr))
    return sorted(set(out))


def measure(doc=DOC):
    """{'doc', 'doc_present', 'cases': [{module, attr, imports, error, present}]}."""
    pairs = cited(doc)
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    cases = []
    for mod, attr in pairs or []:
        try:
            m = importlib.import_module(mod)
        except Exception as e:            # noqa: BLE001
            cases.append({"module": mod, "attr": attr, "imports": False, "error": str(e), "present": False})
            continue
        cases.append({"module": mod, "attr": attr, "imports": True, "error": None,
                      "present": hasattr(m, attr)})
    return {"doc": os.path.relpath(doc, ROOT), "doc_present": pairs is not None, "cases": cases}


def main(argv):
    known = {"--cited", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_standards: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--cited" in argv:
        for mod, attr in cited() or []:
            print(f"{mod}.{attr}")
        return 0
    import opa_gate
    return opa_gate.gate("standards")


def _selftest():
    """The measurement can SEE the appliers this repo lost, and an absent one."""
    import tempfile
    ok = True

    def check(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    pairs = cited()
    check("the document exists and cites appliers", bool(pairs), True)
    # ⚑ The scan must find the specific appliers this repo lost, or it is blind to
    # exactly the failure it was written for.
    flat = {f"{m}.{a}" for m, a in (pairs or [])}
    for needed in ("cvd_gate.apca_Lc", "cvd_gate.wcag_ratio", "cvd_gate.SECTORS"):
        check(f"cites {needed}", needed in flat, True)
    with tempfile.TemporaryDirectory() as td:
        d = os.path.join(td, "STANDARDS.md")
        check("an absent document is SEEN", measure(d)["doc_present"], False)
        open(d, "w").write("APCA is `cvd_gate.apca_Lc`; gone is `cvd_gate.no_such_applier`.\n")
        got = {(c["attr"], c["present"]) for c in measure(d)["cases"]}
        check("a present and an ABSENT applier are both seen", got,
              {("apca_Lc", True), ("no_such_applier", False)})
    print("check_standards selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
