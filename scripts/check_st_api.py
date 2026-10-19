#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_st_api.py — segment_topology exports what its consumers import.

THE RECOVERY'S ONE REAL GAP.  The archive's own notes call the later segment API
"the main rebuild gap" and list the format lattice, the projection function, and
the glyph tables as missing.  Measured against the file, those are all PRESENT —
the note is stale.  What is genuinely absent is the 22-segment geometry.

This tool answers the question the note tried to: for every `ST.<name>` any
consumer actually imports, does the module export it?  The required set is
DISCOVERED from the consumers, never hand-listed, so a new consumer reference
cannot be missed by a roster nobody updated.

    scripts/check_st_api.py            # the verdict, as opa_gate st_api decides it
    scripts/check_st_api.py --json     # the measurement policy/st_api.rego decides
    scripts/check_st_api.py --used     # symbol -> the files referencing it
    scripts/check_st_api.py --missing  # just the absent ones

WEAKNESS. Both sides are read TEXTUALLY: a reference is `ST.<name>` in a file
that imports segment_topology as ST, and an export is a column-0 assignment,
def or class. A name re-exported by `from x import *` is invisible.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def referenced():
    """{symbol: [files]} for every ST.<sym> in the tree (the module aliased as ST)."""
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import git_tracked  # the tree is what git tracks, not the disk

    used = {}
    for fn in git_tracked.files(":(glob)*.py", root=ROOT):
        if fn == "segment_topology.py":
            continue
        p = os.path.join(ROOT, fn)
        with open(p, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        if not re.search(r"import\s+segment_topology\s+as\s+ST\b", text):
            continue
        for m in re.finditer(r"\bST\.([A-Za-z_][A-Za-z0-9_]*)", text):
            used.setdefault(m.group(1), []).append(fn)
    return used


def exported():
    """The module's public names, read WITHOUT importing it (it may be mid-repair)."""
    p = os.path.join(ROOT, "segment_topology.py")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    names = set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", text, re.MULTILINE))
    names |= set(re.findall(r"^def\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.MULTILINE))
    names |= set(re.findall(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.MULTILINE))
    return names


_READ = object()  # "read the tree" — distinct from None, which means module absent


def measure(used=_READ, have=_READ):
    """The MEASUREMENT policy/st_api.rego decides (W50): whether the module is
    present, and per referenced symbol the files naming it and whether the module
    exports it. An empty population and an absent module are the policy's to refuse."""
    used = referenced() if used is _READ else used
    have = exported() if have is _READ else have
    return {
        "module_present": have is not None,
        "cases": [
            {
                "symbol": s,
                "files": sorted(set(f)),
                "exported": have is not None and s in have,
            }
            for s, f in sorted(used.items())
        ],
    }


def measure_fixture(path):
    """The tree's measurement plus the `ST.<name>` references of ONE fixture consumer (W747).

    The fixture is a text file that imports segment_topology as ST; its references join the discovered
    set under the file name "fixture", so a symbol the module does not export reaches policy A2 end to
    end. A file that does not import the module as ST is refused (ValueError): it would reference
    nothing and the measurement would pass for the wrong reason. Named .txt so the tree scan, which reads
    tracked *.py, never counts it."""
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if not re.search(r"import\s+segment_topology\s+as\s+ST\b", text):
        raise ValueError(f"{path}: does not import segment_topology as ST")
    used = referenced()
    for m in re.finditer(r"\bST\.([A-Za-z_][A-Za-z0-9_]*)", text):
        used.setdefault(m.group(1), []).append("fixture")
    return measure(used)


def main(argv):
    known = {"--used", "--missing", "--json"}
    operands = [a for a in argv[1:] if not a.startswith("--")]
    for a in argv[1:]:
        if a.startswith("--") and a not in known:
            print(f"check_st_api: unknown flag {a!r}", file=sys.stderr)
            return 2
    if len(operands) > 1 or (operands and "--json" not in argv):
        print("check_st_api: --json takes at most one fixture file", file=sys.stderr)
        return 2
    if "--json" in argv:
        import json

        if operands and not os.path.isfile(operands[0]):
            print(f"check_st_api: no such fixture {operands[0]!r}", file=sys.stderr)
            return 2
        doc = measure_fixture(operands[0]) if operands else measure()
        print(json.dumps(doc, indent=1))
        return 0
    if "--used" in argv or "--missing" in argv:
        # listings of the measured facts; `!` / --missing is `exported: false`
        m = measure()
        if not m["module_present"]:
            print(
                "check_st_api: segment_topology.py is absent — nothing is exported",
                file=sys.stderr,
            )
            return 2
        for c in m["cases"]:
            if "--used" in argv:
                print(
                    f"{' ' if c['exported'] else '!'} {c['symbol']}\t{', '.join(c['files'])}"
                )
            elif not c["exported"]:
                print(c["symbol"])
        return 0
    import opa_gate

    return opa_gate.gate("st_api")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    # The scan must find the consumers at all, or "nothing missing" is vacuous.
    check("referenced() found symbols", len(referenced()) > 0, True)
    have = exported()
    check("exported() parsed the module", have is not None and len(have) > 0, True)
    # A symbol the module plainly defines must be seen as exported.
    check("exported() sees GEOM16", "GEOM16" in (have or set()), True)
    # ⚑ THE MEASUREMENT CAN SEE a symbol the module lacks and an absent module
    # (the recovery's gap: 22-segment geometry referenced, not defined). The
    # verdict is policy/st_api.rego's, refused and admitted in st_api_test.rego.
    m = measure({"GEOM22": ["make_x.py"], "GEOM16": ["make_x.py"]}, {"GEOM16"})
    check(
        "a referenced, unexported symbol is seen",
        m["cases"][1],
        {"symbol": "GEOM22", "files": ["make_x.py"], "exported": False},
    )
    check(
        "an absent module is seen",
        measure({"GEOM16": ["a.py"]}, None)["module_present"],
        False,
    )
    import tempfile

    fixture = os.path.join(ROOT, "catalog/fixtures/st_api/unexported-use.txt")
    check(
        "a fixture consumer's unexported symbol joins the cases and is seen as unexported (W747)",
        [
            (c["symbol"], c["files"], c["exported"])
            for c in measure_fixture(fixture)["cases"]
            if c["symbol"] == "NO_SUCH_SYMBOL_FIXTURE"
        ],
        [("NO_SUCH_SYMBOL_FIXTURE", ["fixture"], False)],
    )
    with tempfile.TemporaryDirectory() as td:
        plain = os.path.join(td, "plain.txt")
        with open(plain, "w", encoding="utf-8") as fh:
            fh.write("ST.GEOM16\n")
        try:
            measure_fixture(plain)
            refused = False
        except ValueError:
            refused = True
        check(
            "a fixture that does not import the module as ST is REFUSED", refused, True
        )
    print("check_st_api selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
