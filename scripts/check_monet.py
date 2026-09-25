#!/usr/bin/env python3
"""check_monet.py — does Android's own scheme derivation, seeded from the palette, agree with it?

⚑ THE QUESTION ANDROID FORCES (W18).  Material You (Monet) derives its OWN tonal
palette from a seed colour — the wallpaper's, or one the launcher picks — and
apps read that, not a theme file. So the honest emit for Android is not a
theme: it is a wallpaper plus a documented SEED, and the claim is whether
Monet, seeded from this palette, lands on colours that satisfy the palette's
own relations. This runs Google's reference implementation
(material-color-utilities, the research extra) over each variant, seeded from
its lit colour, and measures Monet's surface / primary / on-surface roles
against the palette's ground / lit / fg.

    scripts/check_monet.py            # the verdict, as opa_gate monet decides it
    scripts/check_monet.py --json     # the measurement policy/monet.rego decides
    scripts/check_monet.py --map      # per variant: Monet's roles beside the palette's, and the gaps
    scripts/check_monet.py --selftest # the measurement can SEE each defect

What must hold — AA (4.5) on Monet's own text pairs, the seed's hue kept within
a tolerance, a dark surface within a tolerance of ground — and the tolerances
themselves are policy/monet.rego's ruling (W50). This file measures.

WITHHELD (printed, counted, exit 0) when material-color-utilities is absent — a
fact about the machine. WEAKNESS: the library's version pins the algorithm;
a device's Monet may differ by Android release. What is measured is the
reference derivation, dated.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def variants():
    """The variant ids this tree DECLARES, from the palette authority (make_schemes.GRID).

    ⚑ W65, 2026-09-22: this was a typed list in this file, and dropping one entry
    took "6 of 6" to "5 of 5", exit 0 (check_discriminates, probe
    monet/typed-variants). Add a variant and the expectation moves by itself.
    Read through scripts/variant_roster.py (W61 B2): one roster, one reader."""
    import variant_roster
    return variant_roster.ids()


def have_library():
    try:
        import material_color_utilities  # noqa: F401
        return True
    except ImportError:
        return False


def _rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def _argb(rgb):
    r, g, b = rgb
    return (0xFF << 24) | (r << 16) | (g << 8) | b


def _from_argb(argb):
    return ((argb >> 16) & 0xFF, (argb >> 8) & 0xFF, argb & 0xFF)


def monet_roles(seed_rgb, dark):
    """{role: (r, g, b)} for surface / primary / on_surface / on_primary from Monet's
    default (TonalSpot) scheme at the given polarity. Returns None if the library is absent."""
    try:
        from material_color_utilities import theme_from_color, Variant
    except ImportError:
        return None
    # TonalSpot at contrast 0 is what Android's system theming applies by default
    # (material-color-utilities' own scheme_generation.md); the library's function
    # default is VIBRANT at 0.25, which is not the phone's.
    theme = theme_from_color("#%02x%02x%02x" % seed_rgb, 0.0, Variant.TONALSPOT)
    s = theme.schemes.dark if dark else theme.schemes.light
    return {k: _rgb(getattr(s, k)) for k in
            ("surface", "primary", "on_surface", "on_primary", "primary_container")}


def compare(variant, roles=None):
    """Monet's roles beside the palette's, and the four quantities the policy rules on.
    `roles` substitutes Monet's output (the selftest's planted defects)."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_preview as MP
    import cvd_gate as C
    c = MP.parse_scheme(variant)
    lit, ground, fg = _rgb(c["phosphor"]), _rgb(c["ground"]), _rgb(c["phosphor"])
    dark = not variant.endswith("-Lit")
    m = roles or monet_roles(lit, dark)
    if m is None:
        return None
    rows = [("surface", "ground", m["surface"], ground),
            ("primary", "lit", m["primary"], lit),
            ("on_surface", "fg", m["on_surface"], fg)]
    out = []
    for mr, pr, mv, pv in rows:
        de = C.worst_view_dE(mv, pv)[0] if hasattr(C, "worst_view_dE") else None
        out.append((mr, pr, mv, pv, de))
    # the relations that must hold on MONET'S OWN pairs
    text = C.wcag_ratio(m["on_surface"], m["surface"])
    prim = C.wcag_ratio(m["on_primary"], m["primary"])
    # TonalSpot keeps the seed's HCT HUE and chooses tone and chroma itself, so
    # "the seed survives" is a hue question, not a dE one (a 3x-floor dE arm let
    # a 31.9 dE drift pass on the first run — measured, replaced)
    from material_color_utilities import Hct
    h_seed = Hct("#%02x%02x%02x" % lit).hue
    h_prim = Hct("#%02x%02x%02x" % m["primary"]).hue
    dh = min(abs(h_seed - h_prim), 360 - abs(h_seed - h_prim))
    surface_de = C.worst_view_dE(m["surface"], ground)[0]
    return {"rows": out, "text_on_surface": text, "on_primary": prim,
            "hue_delta": dh, "surface_vs_ground_dE": surface_de, "dark": dark}


def measure():
    """The MEASUREMENT policy/monet.rego decides, over the DECLARED roster.

    ⚑ A VARIANT THAT CANNOT BE MEASURED IS A CASE WITH A REASON, never dropped.
    The library being absent is a top-level `library: false` (a fact about the
    machine); a per-variant failure is a fact about the tree."""
    roster = variants()
    if not have_library():
        return {"library": False, "roster": roster, "cases": []}
    cases = []
    for v in roster:
        try:
            r = compare(v)
        except Exception as e:                           # noqa: BLE001
            cases.append({"id": v, "missing": f"compare() failed: {type(e).__name__}: {e}"})
            continue
        if r is None:
            cases.append({"id": v, "missing": "compare() returned no measurement"})
            continue
        cases.append({"id": v, "missing": None, "dark": r["dark"],
                      "text_on_surface": r["text_on_surface"], "on_primary": r["on_primary"],
                      "hue_delta": r["hue_delta"], "surface_vs_ground_dE": r["surface_vs_ground_dE"]})
    return {"library": True, "roster": roster, "cases": cases}


def main(argv):
    known = {"--map", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_monet: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        print(json.dumps(measure(), indent=1))
        return 0
    if "--map" in argv:
        if not have_library():
            print("check_monet: SKIP — material-color-utilities not installed "
                  "(uv sync --extra research)", file=sys.stderr)
            return 0
        for v in variants():
            r = compare(v)
            print(f"{v} ({'dark' if r['dark'] else 'light'} scheme, seed = lit)")
            for mr, pr, mv, pv, de in r["rows"]:
                print(f"  {mr:11} {'#%02x%02x%02x' % mv}   {pr:6} {'#%02x%02x%02x' % pv}   "
                      f"worst-view dE {de:.1f}" if de is not None else f"  {mr} {mv} vs {pr} {pv}")
            print(f"  Monet on_surface/surface {r['text_on_surface']:.2f}:1; on_primary/primary "
                  f"{r['on_primary']:.2f}:1; primary hue Δ {r['hue_delta']:.1f}°; "
                  f"surface vs ground dE {r['surface_vs_ground_dE']:.1f}")
        return 0
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import opa_gate
    return opa_gate.gate("monet")


def _selftest():
    global compare
    ok = True

    def chk(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    if monet_roles((0, 0, 255), True) is None:
        print("  SKIP — material-color-utilities not installed")
        chk("an absent library is measured as such", measure()["library"], False)
        print("check_monet selftest: SKIP")
        return ok
    chk("argb round-trips", _from_argb(_argb((12, 34, 56))), (12, 34, 56))
    d = monet_roles((75, 250, 215), True)
    l = monet_roles((75, 250, 215), False)
    chk("a dark scheme's surface is darker than a light scheme's",
        sum(d["surface"]) < sum(l["surface"]), True)
    chk("on_surface contrasts with surface (dark)", sum(d["on_surface"]) > sum(d["surface"]), True)
    r = compare("EL-Openglo")
    chk("compare() measures the three role pairs", len(r["rows"]), 3)
    # ⚑ THE SEED MATTERS: a different seed hue moves primary
    a = monet_roles((75, 250, 215), True)["primary"]
    b = monet_roles((250, 160, 35), True)["primary"]
    chk("a different seed gives a different primary", a != b, True)
    # ⚑ EACH DEFECT MUST BE MEASURED (that it is DENIED is policy/monet_test.rego's
    # ruling). Planted through `roles`: Monet's output bent one role at a time.
    real = monet_roles((75, 250, 215), True)
    foreign = dict(real, primary=b)
    chk("a foreign-hue primary is measured far from the seed",
        compare("EL-Openglo", foreign)["hue_delta"] > 90, True)
    flat = dict(real, on_surface=real["surface"])
    chk("a text pair with no contrast is measured at 1:1",
        round(compare("EL-Openglo", flat)["text_on_surface"], 3), 1.0)
    white = dict(real, surface=(255, 255, 255))
    chk("a dark surface far from ground is measured",
        compare("EL-Openglo", white)["surface_vs_ground_dE"] > compare("EL-Openglo", real)["surface_vs_ground_dE"] + 20,
        True)
    m = measure()
    chk("every declared variant is measured", [c["id"] for c in m["cases"]], m["roster"])
    chk("and the population is not empty", len(m["cases"]) > 0, True)
    chk("no variant is missing on a clean tree", [c["id"] for c in m["cases"] if c["missing"]], [])
    # ⚑ A VARIANT compare() CANNOT MEASURE IS MISSING, NOT DROPPED (synthetic)
    kept = compare
    try:
        compare = lambda v: None if v == "EL-Amber" else kept(v)   # noqa: E731
        chk("an unmeasurable variant is a case with a reason",
            [c["id"] for c in measure()["cases"] if c["missing"]], ["EL-Amber"])
    finally:
        compare = kept
    print("check_monet selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
