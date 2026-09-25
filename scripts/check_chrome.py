#!/usr/bin/env python3
"""check_chrome.py — the browser theme emits a valid manifest per variant.

The browser theme is one of the palette's emission targets: it reads the SAME
tokens as the desktop scheme, so it cannot drift.  This runs the emitter for
every variant the palette declares and reads back what it produced.

    scripts/check_chrome.py            # the verdict, as opa_gate chrome decides it
    scripts/check_chrome.py --json     # the measurement policy/chrome.rego decides
    scripts/check_chrome.py --dump     # variant -> frame/text colours
    scripts/check_chrome.py --selftest # the measurement can SEE each defect

What makes a manifest loadable — manifest_version 3, a name, a theme.colors map,
every colour an RGB triple of ints in 0..255 — is policy/chrome.rego's ruling
(W50). ⚑ THE RANGE CHECK IS THE POINT — a token that failed to parse yields None
or a string, and a manifest that is merely well-formed JSON would still sail past.
This file only reports what the emitter produced: each colour's value AS JSON
and whether every channel was a Python int (JSON cannot tell 3 from 3.0 once
serialised, so the type is measured here, where it is still visible).

WEAKNESS: the manifest is judged by its shape; no browser loads it.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def variants():
    """The variants the palette DECLARES (scripts/variant_roster.py, make_schemes.GRID).

    ⚑ THE ROSTER IS THE DECLARATION, NOT A LISTING (W61 B2, 2026-09-23). This was
    schemes_artifact.variants() — a listdir of the colours snapshot — and before
    that a listdir of the tree. A listing cannot tell a clean tree from a deleted
    file: drop EL-Amber.colors and "6 of 6" became "5 of 5", exit 0. Now a
    declared variant whose file is absent fails its manifest (parse_scheme raises)
    and is measured as an error; the snapshot's listing is emitted beside the
    roster, so a stray file is seen too. The colours still come from the W75
    snapshot, through parse_scheme."""
    import variant_roster
    return variant_roster.ids()


def _snapshot():
    """The colours snapshot's member names (a LISTING, compared to the roster by policy)."""
    sys.path.insert(0, ROOT)
    import schemes_artifact
    return sorted(schemes_artifact.variants())


def _emit():
    """Import the emitter and build a manifest for every declared variant."""
    sys.path.insert(0, ROOT)
    import make_chrome as MC
    got = {}
    for v in variants():
        try:
            got[v] = MC.manifest(v)
        except Exception as e:                      # noqa: BLE001
            got[v] = e
    return got


def _is_int(c):
    return isinstance(c, int) and not isinstance(c, bool)


def _case(v, m):
    """One variant's facts: what the emitter returned, or the error it raised."""
    if isinstance(m, Exception):
        return {"id": v, "error": f"{type(m).__name__}: {m}", "manifest_version": None,
                "name": None, "colors": None, "roundtrips": None}
    colors = (m.get("theme") or {}).get("colors") if isinstance(m, dict) else None
    try:
        json.dumps(m)
        rt = True
    except (TypeError, ValueError):
        rt = False
    cols = None
    if isinstance(colors, dict):
        cols = [{"key": str(k),
                 "value": json.loads(json.dumps(val, default=lambda o: f"<{type(o).__name__}>")),
                 "ints": isinstance(val, (list, tuple)) and all(_is_int(c) for c in val)}
                for k, val in colors.items()]
    elif colors is not None:
        cols = f"<{type(colors).__name__}>"
    return {"id": v, "error": None, "manifest_version": m.get("manifest_version"),
            "name": m.get("name"), "colors": cols, "roundtrips": rt}


def measure():
    """The MEASUREMENT policy/chrome.rego decides: the declared roster, the snapshot's
    listing, and per declared variant the emitted manifest's facts. A third-party
    module absent from THIS machine is `withheld` (a fact about the host); a module
    of ours that will not import is the `error` that stopped the read."""
    try:
        got = _emit()
    except ModuleNotFoundError as e:
        dep = e.name
        if not os.path.exists(os.path.join(ROOT, f"{dep}.py")):
            return {"roster": [], "snapshot": [], "cases": [], "error": None,
                    "withheld": f"needs {dep}, which is not installed here"}
        return {"roster": [], "snapshot": [], "cases": [], "withheld": None,
                "error": f"a module of ours did not import: {dep}"}
    except Exception as e:                          # noqa: BLE001
        return {"roster": [], "snapshot": [], "cases": [], "withheld": None,
                "error": f"the emitter did not import: {type(e).__name__}: {e}"}
    return {"roster": sorted(got), "snapshot": _snapshot(), "error": None, "withheld": None,
            "cases": [_case(v, m) for v, m in got.items()]}


def main(argv):
    known = {"--dump", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_chrome: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--dump" in argv:
        for v, m in _emit().items():
            if isinstance(m, Exception):
                print(f"{v}\tERROR {m}")
            else:
                c = m["theme"]["colors"]
                print(f"{v}\tframe={c.get('frame')}\tntp_text={c.get('ntp_text')}")
        return 0
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import opa_gate
    return opa_gate.gate("chrome")


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
    check("the emitter is read", (m["error"], m["withheld"]), (None, None))
    check("every declared variant is measured", [c["id"] for c in m["cases"]], m["roster"])
    check("and the population is not empty", len(m["cases"]) > 0, True)
    # ⚑ THE MEASUREMENT MUST SEE EACH DEFECT the policy rules on — that the policy
    # DENIES it is policy/chrome_test.rego's ruling.
    import make_chrome as MC
    real = MC.manifest

    def planted(fn):
        MC.manifest = fn
        try:
            return {c["id"]: c for c in measure()["cases"]}
        finally:
            MC.manifest = real

    first = m["roster"][0]

    def bend(edit):
        def fn(v):
            out = real(v)
            if v == first:
                out = edit(json.loads(json.dumps(out)))
            return out
        return fn

    def out_of_range(o):
        o["theme"]["colors"]["frame"] = [1, 2, 999]
        return o
    c = planted(bend(out_of_range))[first]
    check("an out-of-range channel is measured",
          next(x["value"] for x in c["colors"] if x["key"] == "frame"), [1, 2, 999])

    def float_channel(o):
        o["theme"]["colors"]["frame"] = [1.0, 2, 3]
        return o
    c = planted(bend(float_channel))[first]
    check("a float channel is measured as not-int",
          next(x["ints"] for x in c["colors"] if x["key"] == "frame"), False)

    def hex_string(o):
        o["theme"]["colors"]["frame"] = "#fff"
        return o
    c = planted(bend(hex_string))[first]
    check("a string colour is measured",
          next(x["value"] for x in c["colors"] if x["key"] == "frame"), "#fff")

    def v2(o):
        o["manifest_version"] = 2
        return o
    check("a wrong manifest_version is measured", planted(bend(v2))[first]["manifest_version"], 2)

    def raising(v):
        if v == first:
            raise FileNotFoundError(f"{v}.colors")
        return real(v)
    check("a variant whose scheme is gone is measured as an error, not dropped",
          (planted(raising)[first]["error"] or "").startswith("FileNotFoundError"), True)
    print("check_chrome selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
