#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2026 Mike Mol
"""check_android_clock.py — every value in the Android clock JSON traces to its authority (W193).

    scripts/check_android_clock.py            # the verdict, as opa_gate android_clock decides it
    scripts/check_android_clock.py --json     # the measurement policy/android_clock.rego decides
    scripts/check_android_clock.py --selftest # the measurement can see a wrong colour, geometry or stale file

Per declared variant (variant_roster, the palette authority): whether
catalog/android/clock/<variant>.json exists and parses, which required sections it lacks,
the palette roles whose value differs from make_schemes.GRID (read HERE directly, not through
make_tokens, so the emitter's path is not the check's), the geometry sections that differ
from segment_topology / display_types read afresh, the digits 0-9 without a mask, whether the
file is byte-equal to a fresh make_android_clock emission, and any file in the directory that
no declared variant owns (an orphan).

WEAKNESS: it proves the JSON equals what its authorities say today, not that an Android
renderer draws it. The palette read-back shares the GRID with the emitter (one authority, two
code paths): a wrong GRID is the palette gate's to catch, not this one's.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
REQUIRED = ("schema", "variant", "palette", "geometry", "display", "sources")


def _grid_tokens():
    import make_schemes
    out = {}
    for value in make_schemes.GRID.values():
        t = value[0] if isinstance(value, (list, tuple)) else value
        if isinstance(t, dict) and "id" in t:
            out[t["id"]] = t
    return out


def _rgb_hex(v):
    r, g, b = (int(p) for p in str(v).split(","))
    return f"#{r:02x}{g:02x}{b:02x}"


def expected_palette(t):
    import make_android_clock as MA
    p = {role: _rgb_hex(t[key]) for role, key in MA.ROLES.items()}
    for a in MA.ALPHAS:
        p[a] = round(float(t[a]), 4)
    return p


def palette_mismatch(doc, t):
    """[role] whose value in the file is not the GRID's."""
    want, got = expected_palette(t), doc.get("palette")
    if not isinstance(got, dict):
        return sorted(want)
    return sorted(k for k in want if got.get(k) != want[k])


def geometry_mismatch(doc):
    """[section] of geometry/display whose file content differs from a fresh read of its authority."""
    import make_android_clock as MA
    want_geo, got_geo = MA.geometry(), doc.get("geometry")
    out = []
    for k in sorted(want_geo):
        if not isinstance(got_geo, dict) or got_geo.get(k) != json.loads(json.dumps(want_geo[k])):
            out.append(f"geometry.{k}")
    if doc.get("display") != json.loads(json.dumps(MA.display())):
        out.append("display")
    return out


def digit_gaps(doc):
    geo = doc.get("geometry")
    ds = geo.get("digSegs") if isinstance(geo, dict) else None
    ds = ds if isinstance(ds, dict) else {}
    return [d for d in "0123456789" if not ds.get(d)]


def case(vid, t, out_dir, fresh):
    path = os.path.join(out_dir, f"{vid}.json")
    if not os.path.exists(path):
        return {"variant": vid, "present": False}
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    try:
        doc = json.loads(raw)
    except ValueError as e:
        return {"variant": vid, "present": True, "parse_error": f"{e}"}
    if not isinstance(doc, dict):
        return {"variant": vid, "present": True, "parse_error": "not a JSON object"}
    return {"variant": vid, "present": True, "parse_error": None,
            "missing_keys": [k for k in REQUIRED if k not in doc],
            "palette_mismatch": palette_mismatch(doc, t),
            "geometry_mismatch": geometry_mismatch(doc),
            "digit_gaps": digit_gaps(doc),
            "current": raw == fresh.get(f"{vid}.json")}


def measure(out_dir=None):
    import variant_roster

    import make_android_clock as MA
    out_dir = out_dir or MA.OUT_DIR
    roster = list(variant_roster.ids())
    toks, fresh = _grid_tokens(), MA.documents()
    cases = [case(v, toks[v], out_dir, fresh) if v in toks else {"variant": v, "present": False}
             for v in roster]
    files = sorted(f for f in os.listdir(out_dir)) if os.path.isdir(out_dir) else []
    orphans = [f for f in files if f[:-len(".json")] not in roster] if files else []
    return {"roster": roster, "cases": cases, "orphans": orphans, "withheld": []}


def _selftest():
    import shutil
    import tempfile

    import make_android_clock as MA
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    docs = MA.documents()
    with tempfile.TemporaryDirectory() as td:
        for name, text in docs.items():
            with open(os.path.join(td, name), "w", encoding="utf-8") as fh:
                fh.write(text)
        m = measure(td)
        good = all(c["present"] and c["current"] and not c["palette_mismatch"] and not c["geometry_mismatch"]
                   and not c["missing_keys"] and not c["digit_gaps"] for c in m["cases"])
        chk("a fresh tree is present, current and traces everywhere", (good, m["orphans"]), (True, []))
        v = m["roster"][0]
        p = os.path.join(td, f"{v}.json")
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        d["palette"]["lit"] = "#ff00ff"
        d["geometry"]["digSegs"]["8"] = ""
        d["geometry"]["metrics"]["pitch"] = 9.9
        del d["sources"]
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(d))
        c = measure(td)["cases"][0]
        chk("a wrong lit colour, a blank digit, a moved metric and a dropped section are each seen",
            (c["palette_mismatch"], c["digit_gaps"], c["geometry_mismatch"], c["missing_keys"], c["current"]),
            (["lit"], ["8"], ["geometry.digSegs", "geometry.metrics"], ["sources"], False))
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("{")
        chk("an unparseable file is a parse error, not a pass", measure(td)["cases"][0]["parse_error"] is not None, True)
        os.remove(p)
        with open(os.path.join(td, "stray.json"), "w") as fh:
            fh.write("{}")
        m = measure(td)
        chk("a missing file is absent and a stray file is an orphan",
            (m["cases"][0]["present"], m["orphans"]), (False, ["stray.json"]))
        shutil.rmtree(td, ignore_errors=True)
    print("check_android_clock selftest:", "PASS" if ok else "FAIL")
    return ok


def main(argv):
    for a in argv[1:]:
        if a not in {"--json", "--selftest"}:
            print(f"check_android_clock: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--selftest" in argv:
        return 0 if _selftest() else 1
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("android_clock")


if __name__ == "__main__":
    sys.exit(main(sys.argv))
