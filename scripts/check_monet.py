#!/usr/bin/env python3
"""check_monet.py — does Android's own scheme derivation, seeded from the palette, agree with it?

⚑ THE QUESTION ANDROID FORCES (W18).  Material You (Monet) derives its OWN tonal
palette from a seed colour — the wallpaper's, or one the launcher picks — and
apps read that, not a theme file. So the honest emit for Android is not a
theme: it is a wallpaper plus a documented SEED, and the claim is whether
Monet, seeded from this palette, lands on colours that satisfy the palette's
own relations. This runs Google's reference implementation
(material-color-utilities, the research extra) over each variant, seeded from
its lit colour, and compares Monet's surface / primary / on-surface roles to
the palette's ground / lit / fg with the palette's own floors.

    scripts/check_monet.py           # exit 0 iff agreement holds where the table says it must
    scripts/check_monet.py --map     # per variant: Monet's roles beside the palette's, and the gaps
    scripts/check_monet.py --selftest

SKIP (printed, counted, exit 0) when material-color-utilities is absent — a
fact about the machine. WEAKNESS: the library's version pins the algorithm;
a device's Monet may differ by Android release. What is measured is the
reference derivation, dated.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VARIANTS = ["EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit", "EL-Amber", "EL-Amber-Lit"]
HUE_TOL = 12.0      # degrees of HCT hue between the seed and Monet's primary (TonalSpot keeps hue; sRGB rounding moves it a few degrees)
SURFACE_TOL = 5.0   # worst-view dE between Monet's dark surface and our ground (measured 2.5-3.4 on 2026-09-21)


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


def compare(variant):
    """[(monet role, palette role, monet rgb, palette rgb, dE, wcag monet-pair)] and a verdict."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_preview as MP
    import cvd_gate as C
    c = MP.parse_scheme(variant)
    lit, ground, fg = _rgb(c["phosphor"]), _rgb(c["ground"]), _rgb(c["phosphor"])
    dark = not variant.endswith("-Lit")
    m = monet_roles(lit, dark)
    if m is None:
        return None
    rows = [("surface", "ground", m["surface"], ground),
            ("primary", "lit", m["primary"], lit),
            ("on_surface", "fg", m["on_surface"], fg)]
    out = []
    for mr, pr, mv, pv in rows:
        de = C.worst_view_dE(mv, pv)[0] if hasattr(C, "worst_view_dE") else None
        out.append((mr, pr, mv, pv, de))
    # the relations that must hold on MONET'S OWN pairs, with the palette's floors
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


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_monet: unknown flag {a!r}", file=sys.stderr)
            return 2
    res = {v: compare(v) for v in VARIANTS}
    if any(r is None for r in res.values()):
        print("check_monet: SKIP — material-color-utilities not installed "
              "(uv sync --extra research); 0 of 6 variants measured", file=sys.stderr)
        return 0
    if "--map" in argv:
        for v, r in res.items():
            print(f"{v} ({'dark' if r['dark'] else 'light'} scheme, seed = lit)")
            for mr, pr, mv, pv, de in r["rows"]:
                print(f"  {mr:11} {'#%02x%02x%02x' % mv}   {pr:6} {'#%02x%02x%02x' % pv}   "
                      f"worst-view dE {de:.1f}" if de is not None else f"  {mr} {mv} vs {pr} {pv}")
            print(f"  Monet on_surface/surface {r['text_on_surface']:.2f}:1; on_primary/primary "
                  f"{r['on_primary']:.2f}:1; primary hue Δ {r['hue_delta']:.1f}°; "
                  f"surface vs ground dE {r['surface_vs_ground_dE']:.1f}")
        return 0
    # ⚑ WHAT IS CLAIMED: Monet's own text pairs clear WCAG AA (4.5) on every
    # variant (seeding from this palette produces a usable scheme), and Monet's
    # primary keeps the seed's HUE within HUE_TOL. What is NOT claimed: that
    # Monet's surface equals ground on the Lit variants — it cannot (Monet's
    # light surfaces are near-white by design, ours are backlit phosphor), and
    # catalog/android.md records that as the disagreement. On the Off variants
    # the surface DOES land within SURFACE_TOL of ground, and that is claimed.
    bad = []
    for v, r in res.items():
        if r["text_on_surface"] < 4.5:
            bad.append(f"{v}: Monet on_surface/surface {r['text_on_surface']:.2f} < 4.5")
        if r["on_primary"] < 4.5:
            bad.append(f"{v}: Monet on_primary/primary {r['on_primary']:.2f} < 4.5")
        if r["hue_delta"] > HUE_TOL:
            bad.append(f"{v}: Monet primary hue drifted {r['hue_delta']:.1f}° from the seed")
        if r["dark"] and r["surface_vs_ground_dE"] > SURFACE_TOL:
            bad.append(f"{v}: Monet dark surface is {r['surface_vs_ground_dE']:.1f} dE from ground (> {SURFACE_TOL})")
    if bad:
        print(f"check_monet: REFUSED — {len(bad)} disagreement(s) over {len(res)} variants:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print(f"check_monet: {len(res)} of {len(res)} variants — Monet seeded from lit yields AA text "
          f"pairs and keeps the seed hue (reference implementation, material-color-utilities)")
    return 0


def _selftest():
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
        print("check_monet selftest: SKIP")
        return True
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
    # ⚑ THE HUE ARM MUST BE ABLE TO FAIL: a primary derived from amber measured
    # against a teal seed is far outside HUE_TOL
    from material_color_utilities import Hct
    dh = abs(Hct("#%02x%02x%02x" % b).hue - Hct("#4bfad7").hue)
    chk("a foreign-hue primary is outside HUE_TOL", min(dh, 360 - dh) > HUE_TOL, True)
    chk("the dark surfaces sit within SURFACE_TOL of ground on every Off variant",
        all(compare(v)["surface_vs_ground_dE"] <= SURFACE_TOL for v in VARIANTS if not v.endswith("-Lit")), True)
    chk("...and the Lit variants' do NOT (Monet's light surface is near-white)",
        all(compare(v)["surface_vs_ground_dE"] > SURFACE_TOL for v in VARIANTS if v.endswith("-Lit")), True)
    print("check_monet selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
