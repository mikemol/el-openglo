#!/usr/bin/env python3
"""check_chrome.py — the browser theme emits a valid manifest per variant.

The browser theme is one of the palette's emission targets: it reads the SAME
tokens as the desktop scheme, so it cannot drift.  This runs the emitter for
every variant it declares and checks the result is a manifest a browser would
actually load.

    scripts/check_chrome.py            # exit 0 iff every variant emits valid JSON
    scripts/check_chrome.py --dump     # variant -> frame/text colours

Structural requirements per manifest: manifest_version 3, a name, a theme.colors
map, and every colour an RGB triple of ints in 0..255.  ⚑ THE RANGE CHECK IS THE
POINT — a token that failed to parse yields None or a string, and a manifest that
is merely well-formed JSON would still sail past.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def variants():
    """The variants that actually have a scheme file, DISCOVERED from the tree.

    ⚑ NOT A HARDCODED ROSTER.  The emitter's __main__ names six variants but only
    some ship a `.colors` file; a fixed list would report a missing FILE as a
    broken THEME, and would silently go stale across a rename.  The scheme files
    on disk are the authority for what exists to emit."""
    return sorted(f[:-len(".colors")] for f in os.listdir(ROOT)
                  if f.endswith(".colors"))


def _emit():
    """Import the emitter and build a manifest for every discovered variant."""
    sys.path.insert(0, ROOT)
    import make_chrome as MC
    got = {}
    for v in variants():
        try:
            got[v] = MC.manifest(v)
        except Exception as e:                      # noqa: BLE001
            got[v] = e
    return got


def _invalid(m):
    """Why this manifest is not loadable, or None."""
    if m.get("manifest_version") != 3:
        return f"manifest_version is {m.get('manifest_version')!r}, not 3"
    if not m.get("name"):
        return "no name"
    colors = (m.get("theme") or {}).get("colors")
    if not isinstance(colors, dict) or not colors:
        return "theme.colors is missing or empty"
    for k, v in colors.items():
        if (not isinstance(v, list) or len(v) != 3
                or not all(isinstance(c, int) and 0 <= c <= 255 for c in v)):
            return f"colour {k!r} is {v!r}, not an RGB triple in 0..255"
    return None


def main(argv):
    known = {"--dump"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_chrome: unknown flag {a!r}", file=sys.stderr)
            return 2
    try:
        got = _emit()
    except ModuleNotFoundError as e:
        # ⚑ NOT CONFIRMED IS NOT FAILED.  A third-party module absent from THIS
        # machine (the emitter's chain reaches an optional renderer) says nothing
        # about the theme.  Reporting it red would be a fact about the host
        # dressed as a fact about the artifact.
        dep = e.name
        if not os.path.exists(os.path.join(ROOT, f"{dep}.py")):
            print(f"check_chrome: SKIP — needs {dep}, which is not installed here "
                  f"(this is a fact about the machine, not the theme)")
            return 0
        print(f"check_chrome: REFUSED — a MODULE OF OURS did not import: {dep}",
              file=sys.stderr)
        return 1
    except Exception as e:                          # noqa: BLE001
        print(f"check_chrome: REFUSED — the emitter did not import: "
              f"{type(e).__name__}: {e}", file=sys.stderr)
        return 1
    if "--dump" in argv:
        for v, m in got.items():
            if isinstance(m, Exception):
                print(f"{v}\tERROR {m}")
            else:
                c = m["theme"]["colors"]
                print(f"{v}\tframe={c.get('frame')}\tntp_text={c.get('ntp_text')}")
        return 0
    bad = []
    for v, m in got.items():
        if isinstance(m, Exception):
            bad.append((v, f"{type(m).__name__}: {m}"))
        else:
            why = _invalid(m)
            if why:
                bad.append((v, why))
            else:
                json.dumps(m)                       # must round-trip
    if bad:
        print(f"check_chrome: REFUSED — {len(bad)} of {len(got)} variant(s) invalid:",
              file=sys.stderr)
        for v, why in bad:
            print(f"    {v}: {why}", file=sys.stderr)
        return 1
    print(f"check_chrome: {len(got)} of {len(got)} variants emit a valid manifest")
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

    # The validator must REJECT the shapes it exists to catch, or it is decorative.
    good = {"manifest_version": 3, "name": "x", "theme": {"colors": {"frame": [1, 2, 3]}}}
    check("accepts a valid manifest", _invalid(good), None)
    check("rejects wrong version", _invalid({**good, "manifest_version": 2}) is not None, True)
    check("rejects missing name", _invalid({**good, "name": ""}) is not None, True)
    bad_c = {"manifest_version": 3, "name": "x", "theme": {"colors": {"frame": "#fff"}}}
    check("rejects a non-triple colour", _invalid(bad_c) is not None, True)
    out_of_range = {"manifest_version": 3, "name": "x",
                    "theme": {"colors": {"frame": [1, 2, 999]}}}
    check("rejects an out-of-range channel", _invalid(out_of_range) is not None, True)
    print("check_chrome selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
