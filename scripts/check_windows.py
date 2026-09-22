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

    scripts/check_windows.py           # exit 0 iff all five hold for every variant
    scripts/check_windows.py --map     # .theme key -> palette role
    scripts/check_windows.py --selftest

WEAKNESS. Windows is not here to open the file. This proves the format page's
requirements, not the Personalization panel's behaviour; and under Aero the
[Control Panel\\Colors] section is ignored by design, so its correctness is a
High Contrast user's benefit, not a desktop-wide one.
"""
import configparser
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIRED = ("Control Panel\\Desktop", "VisualStyles", "MasterThemeSelector")
# The arms check_theme reports for EVERY variant when given its folder — one
# declared dimension of the expected population (the other is GRID's roster).
ARMS = ("parses as INI", "required sections present with MTSM=DABJDKT",
        "colours are the palette roles", "ColorizationColor is the accent",
        "the referenced wallpaper exists beside the theme")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # sibling checks
from check_selection_contrast import schemes, roster_drift   # noqa: E402  (roster authority)


def _rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def check_theme(variant, text, folder=None):
    """[(arm, ok, detail)] for one .theme text; `folder` enables the wallpaper arm."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_windows as MWn
    import make_preview as MP
    out = []
    cp = configparser.ConfigParser(interpolation=None)
    cp.optionxform = str
    try:
        cp.read_string(text)
        out.append(("parses as INI", True, f"{len(cp.sections())} sections"))
    except configparser.Error as e:
        return [("parses as INI", False, str(e))]
    missing = [s for s in REQUIRED if s not in cp]
    ok = not missing and cp["MasterThemeSelector"].get("MTSM") == "DABJDKT" if not missing else False
    out.append(("required sections present with MTSM=DABJDKT", ok,
                f"missing {missing}" if missing else
                ("MTSM != DABJDKT" if not ok else "Desktop, VisualStyles, MasterThemeSelector")))
    c = MP.parse_scheme(variant)
    bad = []
    colors = cp["Control Panel\\Colors"] if "Control Panel\\Colors" in cp else {}
    for key, role in MWn.COLOR_KEYS:
        want = "%d %d %d" % _rgb(c[role])
        if colors.get(key) != want:
            bad.append(f"{key}={colors.get(key)!r} != {want} ({role})")
    out.append(("colours are the palette roles", not bad,
                "; ".join(bad[:3]) if bad else f"{len(MWn.COLOR_KEYS)} of {len(MWn.COLOR_KEYS)} keys"))
    r, g, b = _rgb(c["accent"])
    cz = cp["VisualStyles"].get("ColorizationColor", "") if "VisualStyles" in cp else ""
    out.append(("ColorizationColor is the accent", cz.upper().endswith("%02X%02X%02X" % (r, g, b))
                and cz.upper().startswith("0X") and len(cz) == 10,
                cz or "absent"))
    if folder is not None:
        wp = cp["Control Panel\\Desktop"].get("Wallpaper", "") if "Control Panel\\Desktop" in cp else ""
        p = os.path.join(folder, *wp.split("\\")) if wp else ""
        out.append(("the referenced wallpaper exists beside the theme",
                    bool(wp) and os.path.isfile(p), wp or "no Wallpaper key"))
    return out


def measure():
    """([(variant, arm, ok, detail)], [(variant, why)]) over the DECLARED roster.

    ⚑ W65: the population was make_windows.VARIANTS — the emitter's own typed
    list — so dropping a variant there took "30 of 30" to "25 of 25", rc 0. It is
    now make_schemes.GRID; emitter drift, and any arm a theme did not reach (an
    unparsable INI reports ONE arm), are RETURNED as missing."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_windows as MWn
    results, missing = [], list(roster_drift(MWn.VARIANTS, "make_windows"))
    roster = schemes()
    with tempfile.TemporaryDirectory() as td:
        outs = {v: os.path.join(td, v) for v in roster}
        MWn.render_all(roster, outs)
        for v in roster:
            text = open(os.path.join(outs[v], f"{v}.theme"), encoding="utf-8").read()
            arms = check_theme(v, text, outs[v])
            seen = {a for a, _o, _d in arms}
            missing += [(v, f"arm {a!r} was not measured") for a in ARMS if a not in seen]
            results += [(v, a, o, d) for a, o, d in arms if a in ARMS]
    return results, missing


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_windows: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_windows as MWn
    if "--map" in argv:
        for key, role in MWn.COLOR_KEYS:
            print(f"{key:20} <- {role}")
        return 0
    results, missing = measure()
    roster = schemes()
    # ⚑ THE POPULATION IS ASSERTED BEFORE THE OUTCOME (W65): roster x ARMS.
    expected = len(roster) * len(ARMS)
    if missing or len(results) != expected or not results:
        print(f"check_windows: REFUSED — measured {len(results)} of {expected} declared arm(s) "
              f"({len(roster)} variant(s) x {len(ARMS)} arm(s)). A SHRINKING POPULATION "
              f"IS NOT A PASSING ONE: n of n is green for every n.", file=sys.stderr)
        for v, why in missing:
            print(f"    {v}: {why}", file=sys.stderr)
        return 2
    n = len(results)
    fails = [f"{v} {arm}: {detail}" for v, arm, ok, detail in results if not ok]
    if fails:
        print(f"check_windows: REFUSED — {len(fails)} of {n} arm(s) do not hold:", file=sys.stderr)
        for f in fails:
            print(f"    {f}", file=sys.stderr)
        return 1
    print(f"check_windows: {n} of {expected} arms hold over {len(roster)} themes "
          f"(roster: make_schemes.GRID)")
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

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_windows as MWn
    good = MWn.theme_ini("EL-Openglo", "DesktopBackground\\EL-Openglo.png")
    arms = {a: o for a, o, _d in check_theme("EL-Openglo", good)}
    check("the real emission holds every text arm", all(arms.values()), True)
    # ⚑ EACH ARM MUST BE ABLE TO FAIL.
    arms = {a: o for a, o, _d in check_theme("EL-Openglo", good.replace("MTSM=DABJDKT", "MTSM=NOPE"))}
    check("a wrong MTSM tag is seen", arms["required sections present with MTSM=DABJDKT"], False)
    arms = {a: o for a, o, _d in check_theme("EL-Openglo", good.replace("[VisualStyles]", "[VisualStyle]"))}
    check("a missing required section is seen", arms["required sections present with MTSM=DABJDKT"], False)
    arms = {a: o for a, o, _d in check_theme("EL-Openglo", good.replace("WindowText=", "WindowText=1 2 3 ;"))}
    check("an authored colour is seen", arms["colours are the palette roles"], False)
    arms = {a: o for a, o, _d in check_theme("EL-Openglo", good.replace("ColorizationColor=0x", "ColorizationColor=0x00"))}
    check("a wrong accent is seen", arms["ColorizationColor is the accent"], False)
    arms = {a: o for a, o, _d in check_theme("EL-Openglo", "[Theme\nDisplayName=x")}
    check("an unparsable file is seen", arms["parses as INI"], False)
    with tempfile.TemporaryDirectory() as td:
        arms = {a: o for a, o, _d in check_theme("EL-Openglo", good, td)}
        check("a wallpaper that is not there is seen", arms["the referenced wallpaper exists beside the theme"], False)
    # ⚑ THE LIVENESS CONJUNCT: complete AND not vacuously complete
    results, missing = measure()
    check("the declared population is complete on a clean tree",
          (missing, len(results) == len(schemes()) * len(ARMS)), ([], True))
    check("and it is not vacuously complete", len(results) > 0, True)
    saved = list(MWn.VARIANTS)
    try:
        MWn.VARIANTS[:] = saved[:-1]
        check("an emitter that drops a GRID variant is REFUSED", main(["x"]), 2)
    finally:
        MWn.VARIANTS[:] = saved
    print("check_windows selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
