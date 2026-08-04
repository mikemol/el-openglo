#!/usr/bin/env python3
"""check_st_api.py — segment_topology exports what its consumers import.

THE RECOVERY'S ONE REAL GAP.  The archive's own notes call the later segment API
"the main rebuild gap" and list the format lattice, the projection function, and
the glyph tables as missing.  Measured against the file, those are all PRESENT —
the note is stale.  What is genuinely absent is the 22-segment geometry.

This tool answers the question the note tried to: for every `ST.<name>` any
consumer actually imports, does the module export it?  The required set is
DISCOVERED from the consumers, never hand-listed, so a new consumer reference
cannot be missed by a roster nobody updated.

    scripts/check_st_api.py            # exit 0 iff every referenced symbol exists
    scripts/check_st_api.py --used     # symbol -> the files referencing it
    scripts/check_st_api.py --missing  # just the absent ones
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def referenced():
    """{symbol: [files]} for every ST.<sym> in the tree (the module aliased as ST)."""
    used = {}
    for fn in sorted(os.listdir(ROOT)):
        if not fn.endswith(".py") or fn == "segment_topology.py":
            continue
        p = os.path.join(ROOT, fn)
        text = open(p, encoding="utf-8", errors="replace").read()
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
    text = open(p, encoding="utf-8", errors="replace").read()
    names = set(re.findall(r"^([A-Za-z_][A-Za-z0-9_]*)\s*=", text, re.M))
    names |= set(re.findall(r"^def\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
    names |= set(re.findall(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)", text, re.M))
    return names


def main(argv):
    known = {"--used", "--missing"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_st_api: unknown flag {a!r}", file=sys.stderr)
            return 2
    used = referenced()
    have = exported()
    if have is None:
        print("check_st_api: REFUSED — segment_topology.py is absent", file=sys.stderr)
        return 2
    if not used:
        print("check_st_api: REFUSED — no consumer references found; the search is "
              "broken, not the API complete", file=sys.stderr)
        return 2
    missing = {s: f for s, f in sorted(used.items()) if s not in have}
    if "--used" in argv:
        for s, files in sorted(used.items()):
            mark = " " if s in have else "!"
            print(f"{mark} {s}\t{', '.join(sorted(set(files)))}")
        return 0
    if "--missing" in argv:
        print("\n".join(sorted(missing)))
        return 0
    if missing:
        print(f"check_st_api: REFUSED — {len(missing)} of {len(used)} referenced "
              f"symbol(s) are not exported:", file=sys.stderr)
        for s, files in missing.items():
            print(f"    ST.{s}  (imported by {', '.join(sorted(set(files)))})",
                  file=sys.stderr)
        return 1
    print(f"check_st_api: {len(used)} of {len(used)} referenced symbols exported")
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

    # The scan must find the consumers at all, or "nothing missing" is vacuous.
    check("referenced() found symbols", len(referenced()) > 0, True)
    have = exported()
    check("exported() parsed the module", have is not None and len(have) > 0, True)
    # A symbol the module plainly defines must be seen as exported.
    check("exported() sees GEOM16", "GEOM16" in (have or set()), True)
    print("check_st_api selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
