#!/usr/bin/env python3
"""check_windows.py — the emitted .theme files are ones Windows would list, and carry the palette.

⚑ THE CLAIM.  For every variant, make_windows emits a .theme that (1) parses as
INI; (2) carries the THREE sections Microsoft's format page says are required
— [Control Panel\\Desktop], [VisualStyles], [MasterThemeSelector] with
MTSM=DABJDKT — without which "the system ignores your Theme" (silently: a
theme that never appears looks like a theme that was never installed);
(3) every [Control Panel\\Colors] value is the palette role make_windows.COLOR_KEYS
names, as `R G B`; (4) ColorizationColor is the accent as 0xAARRGGBB; (5) the
wallpaper it references exists beside it after render_all.

    scripts/check_windows.py            # the verdict, as opa_gate windows decides it
    scripts/check_windows.py --json     # the measurement policy/windows.rego decides
    scripts/check_windows.py --map      # .theme key -> palette role
    scripts/check_windows.py --selftest # the measurement can SEE each defect

The five requirements are policy/windows.rego's ruling (W50); this file reads each
emitted .theme and reports what it holds beside what the palette says it should.

WEAKNESS. Windows is not here to open the file. This proves the format page's
requirements, not the Personalization panel's behaviour; and under Aero the
[Control Panel\\Colors] section is ignored by design, so its correctness is a
High Contrast user's benefit, not a desktop-wide one.
"""
import configparser
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # sibling checks
from check_selection_contrast import schemes   # noqa: E402  (roster authority)


def _rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def facts(variant, text, folder=None):
    """What one .theme text holds, beside what the palette wants. `folder` enables
    the wallpaper fact (null without it)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_windows as MWn
    import make_preview as MP
    out = {"id": variant, "missing": None, "parse_error": None, "sections": [], "mtsm": None,
           "colors": [], "colorization": None, "accent": None,
           "wallpaper": None, "wallpaper_exists": None}
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    try:
        cp.read_string(text)
    except configparser.Error as e:
        out["parse_error"] = f"{type(e).__name__}: {e}"
        return out
    out["sections"] = cp.sections()
    if "MasterThemeSelector" in cp:
        out["mtsm"] = cp["MasterThemeSelector"].get("MTSM")
    c = MP.parse_scheme(variant)
    colors = cp["Control Panel\\Colors"] if "Control Panel\\Colors" in cp else {}
    out["colors"] = [{"key": key, "role": role, "got": colors.get(key),
                      "want": "%d %d %d" % _rgb(c[role])} for key, role in MWn.COLOR_KEYS]
    out["accent"] = "%02X%02X%02X" % _rgb(c["accent"])
    if "VisualStyles" in cp:
        out["colorization"] = cp["VisualStyles"].get("ColorizationColor")
    if folder is not None and "Control Panel\\Desktop" in cp:
        wp = cp["Control Panel\\Desktop"].get("Wallpaper", "") or None
        out["wallpaper"] = wp
        out["wallpaper_exists"] = bool(wp) and os.path.isfile(os.path.join(folder, *wp.split("\\")))
    return out


def measure():
    """The MEASUREMENT policy/windows.rego decides, over the DECLARED roster.

    ⚑ W65: the population was make_windows.VARIANTS — the emitter's own typed
    list — so dropping a variant there took "30 of 30" to "25 of 25", rc 0. It is
    make_schemes.GRID; the emitter's own list is emitted as `roster_drift` facts."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_windows as MWn
    import variant_roster as VR
    roster = schemes()
    cases = []
    with tempfile.TemporaryDirectory() as td:
        outs = {v: os.path.join(td, v) for v in roster}
        try:
            MWn.render_all(roster, outs)
        except Exception as e:                           # noqa: BLE001
            return {"roster": roster, "roster_drift": [], "cases": [],
                    "error": f"render_all: {type(e).__name__}: {e}"}
        for v in roster:
            p = os.path.join(outs[v], f"{v}.theme")
            if not os.path.isfile(p):
                cases.append({"id": v, "missing": f"render_all wrote no {v}.theme"})
                continue
            cases.append(facts(v, open(p, encoding="utf-8").read(), outs[v]))
    return {"roster": roster, "error": None, "cases": cases,
            "roster_drift": VR.drift_facts({"make_windows": MWn.VARIANTS}, roster)}


def main(argv):
    known = {"--map", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_windows: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--map" in argv:
        import make_windows as MWn
        for key, role in MWn.COLOR_KEYS:
            print(f"{key:20} <- {role}")
        return 0
    import opa_gate
    return opa_gate.gate("windows")


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_windows as MWn
    good = MWn.theme_ini("EL-Openglo", "DesktopBackground\\EL-Openglo.png")
    f = facts("EL-Openglo", good)
    check("the real emission parses and carries MTSM", (f["parse_error"], f["mtsm"]), (None, "DABJDKT"))
    check("every colour key is read", len(f["colors"]), len(MWn.COLOR_KEYS))
    # ⚑ EACH DEFECT MUST BE MEASURED (that it is DENIED is policy/windows_test.rego's ruling).
    check("a wrong MTSM tag is measured",
          facts("EL-Openglo", good.replace("MTSM=DABJDKT", "MTSM=NOPE"))["mtsm"], "NOPE")
    check("a missing required section is measured",
          "VisualStyles" in facts("EL-Openglo", good.replace("[VisualStyles]", "[VisualStyle]"))["sections"], False)
    bent = facts("EL-Openglo", good.replace("WindowText=", "WindowText=1 2 3 ;"))
    wt = next(c for c in bent["colors"] if c["key"] == "WindowText")
    check("an authored colour is measured beside the palette's", wt["got"] != wt["want"], True)
    check("a wrong accent is measured",
          facts("EL-Openglo", good.replace("ColorizationColor=0x", "ColorizationColor=0x00"))["colorization"][:4],
          "0x00")
    check("an unparsable file is measured",
          facts("EL-Openglo", "[Theme\nDisplayName=x")["parse_error"] is not None, True)
    with tempfile.TemporaryDirectory() as td:
        check("a wallpaper that is not there is measured",
              facts("EL-Openglo", good, td)["wallpaper_exists"], False)
    m = measure()
    check("every declared variant is measured", [c["id"] for c in m["cases"]], m["roster"])
    check("and the population is not empty", len(m["cases"]) > 0, True)
    check("the real wallpapers are there", all(c.get("wallpaper_exists") for c in m["cases"]), True)
    saved = list(MWn.VARIANTS)
    try:
        MWn.VARIANTS[:] = saved[:-1]
        check("an emitter that drops a GRID variant is measured as drift",
              [d["variant"] for d in measure()["roster_drift"]], [saved[-1]])
    finally:
        MWn.VARIANTS[:] = saved
    print("check_windows selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
