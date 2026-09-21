#!/usr/bin/env python3
"""check_ghost_surfaces.py — the ghost each SURFACE draws is the ghost the PALETTE solved.

⚑ THE DEFECT.  @GHOSTCOMP proved the palette's `fg_in`, composited at the emitted
alpha, clears its floor and stays under its ceiling — on the token. It never
asked what colour a surface actually hands the renderer. Measured 2026-09-20:
every segment surface derives its OWN lit and ghost on the way in —

    make_wallpaper_live.colors_for  lit = stretch_lit(focus); ghost = derive_ghost(lit)
    make_notify_marquee.main_qml    (via colors_for)
    make_clock.main_qml             lit = stretch_lit(focus); ghost = derive_ghost(lit); alpha 1
    make_plymouth.render_assets     ghost = lerp(phosphor, ground, 0.6); alpha 0.5

— a pipeline from session 39 (⊕CONTRAST-STRETCH), written before the palette
solver existed (sessions 57-58) and never retired when the solver took over the
same invariant. So the solved `fg_in` — and every fix W3 made to it — reaches
the .colors files and NO display surface. The gated ghost is the seen ghost on
zero of four.

    scripts/check_ghost_surfaces.py           # exit 0 iff every surface draws the palette's ghost
    scripts/check_ghost_surfaces.py --map     # surface -> (lit, ghost, alpha) it emits vs the palette's
    scripts/check_ghost_surfaces.py --selftest

WEAKNESS, STATED.  This reads what each generator EMITS (the colour it fills into
its template or bakes into its PNG), through the generator's own accessor. It
does not render. A surface that receives the right colour and then draws it
wrongly is @GHOSTCOMP's or a render witness's problem, not this one's.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _rgb(s):
    s = s.strip().strip('"')
    if s.startswith("#"):
        return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))
    return tuple(int(x) for x in s.split(","))


def _hole(qml, name):
    m = re.search(rf"property color {name}:\s*\"?(#[0-9a-fA-F]{{6}})", qml)
    return _rgb(m.group(1)) if m else None


def _bound(qml, name, role, token_hex):
    """The colour a BOUND surface draws under a variant: the variant's token iff
    `name` is bound to Kirigami.Theme.<role> under colorSet View; else None."""
    m = re.search(rf"(?m)^\s*property color {name}:\s*Kirigami\.Theme\.{role}\s*$", qml)
    cs = re.search(r"(?m)^\s*Kirigami\.Theme\.colorSet:\s*Kirigami\.Theme\.View\s*$", qml)
    return _rgb(token_hex) if (m and cs) else None


def _alpha(qml):
    m = re.search(r"property real ghostAlpha:\s*([0-9.]+)", qml)
    return float(m.group(1)) if m else None


# Each surface's PARSING MODE (glance_audit's), which selects the alpha it must
# draw: looked-at surfaces read ghost_alpha, glanced-at ones ghost_alpha_glanced.
SURFACE_MODE = {
    "make_wallpaper_live": "glanced_at",
    "make_notify_marquee": "looked_at",
    "make_clock": "looked_at",
    "make_plymouth": "glanced_at",
    # the Alt+Tab switcher (W31): the eye is ON it while it is up
    "make_taskswitch": "looked_at",
}


def palette():
    """{variant_id: (lit, ghost, {mode: alpha})} — what the palette SOLVED."""
    import make_schemes
    out = {}
    for value in make_schemes.GRID.values():
        t = value[0] if isinstance(value, (list, tuple)) else value
        if isinstance(t, dict) and "fg_in" in t:
            out[t["id"]] = (_rgb(t["fg"]), _rgb(t["fg_in"]),
                            {"looked_at": float(t.get("ghost_alpha", 0.45)),
                             "glanced_at": float(t.get("ghost_alpha_glanced",
                                                       t.get("ghost_alpha", 0.45)))})
    return out


def surfaces(variant_id):
    """[(surface, lit, ghost, alpha)] — what each surface EMITS for this variant."""
    os.chdir(ROOT)
    import make_schemes
    tok = next(v[0] for v in make_schemes.GRID.values()
               if isinstance(v[0], dict) and v[0].get("id") == variant_id)
    out = []

    import make_wallpaper_live as WL
    qml = WL.main_qml(variant_id)
    out.append(("make_wallpaper_live", _hole(qml, "litColor") or _hole(qml, "lit"),
                _hole(qml, "ghostColor") or _hole(qml, "ghost"), _alpha(qml)))

    import make_notify_marquee as NM
    qml = NM.main_qml(variant_id)
    out.append(("make_notify_marquee", _hole(qml, "litColor") or _hole(qml, "lit"),
                _hole(qml, "ghostColor") or _hole(qml, "ghost"), _alpha(qml)))

    # ⚑ A BOUND SURFACE (⊕ONE-THEME, W35): the switcher is ONE package whose
    # colours are Kirigami.Theme roles of the ACTIVE scheme, so "what it draws
    # under variant V" is the token the scheme writes into that role — lit is
    # ForegroundNormal (fg) iff bound to textColor, ghost is ForegroundInactive
    # (fg_in) iff bound to disabledTextColor. A baked hex or a wrong role resolves
    # to None here and fails the comparison, which is the assertion this check
    # makes of a live surface (catalog/one-theme.md, Gates).
    import make_taskswitch as TS
    qml = TS.main_qml()
    out.append(("make_taskswitch", _bound(qml, "litColor", "textColor", tok["fg"]),
                _bound(qml, "ghostColor", "disabledTextColor", tok["fg_in"]), _alpha(qml)))

    import make_clock as MC
    qml = MC.main_qml(tok)
    out.append(("make_clock", _hole(qml, "litColor"), _hole(qml, "ghostColor"),
                _alpha(qml) if _alpha(qml) is not None else 1.0))

    import make_plymouth as MP
    import make_preview
    c = make_preview.parse_scheme(variant_id)
    # what render_assets hands render_digit: the scheme's phosphor, its
    # ForegroundInactive, and [EL] GhostAlpha (parse_scheme defaults 0.45 when
    # the .colors predates the solve — which this check then reports as a miss)
    out.append(("make_plymouth", MP._rgb(c["phosphor"]), MP._rgb(c["ghost"]),
                float(c["ghost_alpha_glanced"])))            # what render_assets passes
    return out


def measure():
    """[(variant, surface, lit_ok, ghost_ok, alpha_ok, emitted, solved)].

    The alpha a surface must draw is the one for ITS parsing mode (SURFACE_MODE)."""
    rows = []
    for vid, (lit, ghost, alphas) in palette().items():
        for name, s_lit, s_ghost, s_alpha in surfaces(vid):
            alpha = alphas[SURFACE_MODE[name]]
            rows.append((vid, name, s_lit == lit, s_ghost == ghost,
                         s_alpha is not None and abs(s_alpha - alpha) < 1e-9,
                         (s_lit, s_ghost, s_alpha), (lit, ghost, alpha)))
    return rows


def main(argv):
    known = {"--map", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_ghost_surfaces: unknown flag {a!r}", file=sys.stderr)
            return 2
    rows = measure()
    if not rows:
        print("check_ghost_surfaces: REFUSED — no variants or no surfaces; the "
              "population is empty, not the surfaces faithful", file=sys.stderr)
        return 2
    if "--map" in argv:
        print(f"{'variant':16s} {'surface':22s} {'lit':>13s} {'ghost':>13s} {'alpha':>6s}   vs palette")
        for vid, name, lo, go, ao, (sl, sg, sa), (pl, pg, pa) in rows:
            flags = ("" if lo else " LIT≠") + ("" if go else " GHOST≠") + ("" if ao else " ALPHA≠")
            print(f"{vid:16s} {name:22s} {str(sl):>13s} {str(sg):>13s} {str(sa):>6s}   "
                  f"{pl} {pg} {pa}{flags}")
        return 0
    bad = [r for r in rows if not (r[3] and r[4])]
    if bad:
        by = {}
        for vid, name, lo, go, ao, em, so in bad:
            by.setdefault(name, []).append(vid)
        print(f"check_ghost_surfaces: REFUSED — {len(bad)} of {len(rows)} surface×variant "
              f"emissions draw a ghost the palette did not solve:", file=sys.stderr)
        for name, vids in by.items():
            print(f"    {name}: {len(vids)} of 6 variants (derives its own ghost)", file=sys.stderr)
        return 1
    print(f"check_ghost_surfaces: {len(rows)} of {len(rows)} surface×variant emissions "
          f"draw the palette's ghost at the palette's alpha")
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

    rows = measure()
    check(f"population: 6 variants × {len(SURFACE_MODE)} surfaces", len(rows), 6 * len(SURFACE_MODE))
    check("every surface enumerated is one that surfaces() emits",
          sorted({r[1] for r in rows}), sorted(SURFACE_MODE))
    check("the palette solved a ghost for every variant", len(palette()), 6)
    # ⚑ A BOUND SURFACE (W35): the right role under View resolves to the token; a
    # baked hex, the wrong role, or a missing colorSet resolves to None
    good = ("Kirigami.Theme.colorSet: Kirigami.Theme.View\n"
            "    property color ghostColor: Kirigami.Theme.disabledTextColor\n")
    check("a role-bound colour resolves to the variant's token",
          _bound(good, "ghostColor", "disabledTextColor", "#7ed3c3"), _rgb("#7ed3c3"))
    check("a baked hex does not", _bound(good.replace("Kirigami.Theme.disabledTextColor", '"#7ed3c3"'),
                                         "ghostColor", "disabledTextColor", "#7ed3c3"), None)
    check("the wrong role does not", _bound(good.replace("disabledTextColor", "textColor"),
                                            "ghostColor", "disabledTextColor", "#7ed3c3"), None)
    check("a missing colorSet does not", _bound(good.replace("Kirigami.Theme.colorSet: Kirigami.Theme.View", ""),
                                                "ghostColor", "disabledTextColor", "#7ed3c3"), None)
    # ⚑ THE CHECK MUST SEE A FAITHFUL SURFACE AND AN UNFAITHFUL ONE.
    saved = globals()["measure"]
    try:
        globals()["measure"] = lambda: [("V", "s", True, True, True, (0, 0, 0), (0, 0, 0))]
        check("a faithful surface passes", main(["x"]), 0)
        globals()["measure"] = lambda: [("V", "s", True, False, True, (0, 0, 0), (0, 0, 0))]
        check("a surface drawing its own ghost is seen", main(["x"]), 1)
        globals()["measure"] = lambda: [("V", "s", True, True, False, (0, 0, 0), (0, 0, 0))]
        check("a surface drawing at its own alpha is seen", main(["x"]), 1)
        globals()["measure"] = lambda: []
        check("an empty population REFUSES", main(["x"]), 2)
    finally:
        globals()["measure"] = saved
    print("check_ghost_surfaces selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
