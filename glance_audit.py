#!/usr/bin/env python3
"""Glance audit (⊕GLANCE-AUDIT) — a pre-ship gate for the invariant that
lit-vs-ghost distinction must scale with a surface's PARSING MODE.

The bug in ⊕WALLPAPER-CONTRAST was general: a surface dropped a distinguishing
channel (bloom) on the surface that could least afford it (glanced-at), and
nothing caught it before it shipped and had to be *noticed*. This audit encodes
the fix as a gate.

It does NOT merely count channels (that's a proxy). It measures the actual
quantity that determines legibility — EFFECTIVE lit/ghost separation — and
compares it to a floor that scales with parsing mode:

  - LOOKED-AT (foveal, deliberate: the clock you check): floor ~3:1. You bring
    full acuity; color contrast + a reinforcing channel suffices.
  - GLANCED-AT (peripheral, brief: wallpaper, splash, boot): floor ~5.5:1.
    Lower acuity is available, so more separation is required.

Effective separation is the measurable color ratio (raised when the ghost is
subordinated — drawn at reduced opacity it composites toward the ground and
recedes), times labeled HEURISTIC bonuses for bloom (a lit-only luminous halo)
and stroke-weight (lit drawn wider = more integrated area = perceived brighter).
The color+subordination part is exact; the bloom/stroke parts are honest
perceptual weightings, flagged as such.
"""
import cvd_gate as C

LOOKED_AT = "looked_at"
TRANSITIONAL = "transitional"
GLANCED_AT = "glanced_at"

# Floor scales with PARSING DEMAND. Three modes, not two:
#  - looked_at: foveal, deliberate, persistent (the clock you check) — 3.0
#  - transitional: brief, progressive reveal, then gone (splash, boot) — 4.5.
#    Genuinely less demanding than a persistent ambient surface: you glimpse it
#    mid-animation during a state change, you don't dwell on or read from it.
#  - glanced_at: peripheral but PERSISTENT/AMBIENT (the always-on wallpaper you
#    might read the time from) — 5.5, the most demanding glance.
MODE_FLOOR = {
    LOOKED_AT: 3.0,
    TRANSITIONAL: 4.5,
    GLANCED_AT: 5.5,
}

# labeled HEURISTIC perceptual bonuses (not WCAG quantities)
BLOOM_BONUS = 1.30      # lit-only glow halo raises figure/ground pop
WEIGHT_BONUS = 1.15     # lit stroke wider -> more integrated area -> perceived brighter


def _composite(fg, bg, a):
    return tuple(int(round(fg[i] * a + bg[i] * (1 - a))) for i in range(3))


def effective_separation(lit, ghost, ground, ghost_alpha=1.0,
                         bloom=False, stroke_weight=False):
    """The measurable lit/ghost separation as actually perceived on the surface.
    Exact part: color ratio vs the (possibly subordinated) ghost. Heuristic part:
    bloom/stroke bonuses (flagged)."""
    ghost_eff = ghost if ghost_alpha >= 1.0 else _composite(ghost, ground, ghost_alpha)
    ratio = C.wcag_ratio(lit, ghost_eff)
    if bloom:
        ratio *= BLOOM_BONUS
    if stroke_weight:
        ratio *= WEIGHT_BONUS
    return ratio


def audit_surface(name, mode, lit, ghost, ground, ghost_alpha=1.0,
                  bloom=False, stroke_weight=False, has_ghost=True):
    """Returns (ok, eff, floor, detail). Surfaces with no ghost distinction
    (e.g. lit-text-on-void marquee) are EXEMPT."""
    if not has_ghost:
        return (True, None, None, "exempt (no lit/ghost distinction)")
    floor = MODE_FLOOR[mode]
    eff = effective_separation(lit, ghost, ground, ghost_alpha, bloom, stroke_weight)
    chans = []
    if ghost_alpha < 1.0:
        chans.append(f"ghost-subordinate({ghost_alpha:.2f})")
    if bloom:
        chans.append("bloom")
    if stroke_weight:
        chans.append("stroke-weight")
    return (eff >= floor, eff, floor, "+".join(["color"] + chans))


def surface_registry(variant="EL-Azure"):
    """The live surfaces and how each renders lit/ghost, read from the emitters.
    (Channel flags reflect what each emitter actually draws.)"""
    # ⚑ THE REGISTRY READS THE PALETTE, NOT A MODEL OF EACH SURFACE.  It carried
    # per-surface guesses — the clock at alpha 1.0 (it WAS opaque), the wallpaper's
    # alpha detected by grepping "0.45" out of its QML, and the splash/plymouth
    # ghost as `lit` at an adaptive opacity scanned here a THIRD time (the same
    # scan make_deb ran, which was the sixth ghost model). Since W8 every surface
    # draws fg_in at ghost_alpha and scripts/check_ghost_surfaces.py refuses one
    # that does not, so the audit's inputs are one read of the token dict. An
    # instrument that models the world separately from the world is the
    # INSTRUMENT-VS-WORLD entry the log has banked nine times.
    import make_wallpaper_live as WL
    ground, lit, ghost, alpha_looked = WL.colors_for(variant, parsing="looked_at")
    _g, _l, _gh, alpha_glanced = WL.colors_for(variant, parsing="glanced_at")
    wq = WL.main_qml()            # one package since W35; the idiom flags below are variant-free
    reg = []

    # clock plasmoid — LOOKED-AT; color + subordinated ghost + stroke-weight + bloom
    reg.append(dict(name="clock", mode=LOOKED_AT, lit=lit, ghost=ghost, ground=ground,
                    ghost_alpha=alpha_looked, bloom=True, stroke_weight=True))

    # live wallpaper — GLANCED-AT; the bloom and stroke-weight channels are still
    # detected from the emitted Canvas idiom (a dropped channel is what this audit
    # was written to catch); the alpha is the palette's GLANCED one (W12 §3c).
    reg.append(dict(name="wallpaper-live", mode=GLANCED_AT, lit=lit, ghost=ghost,
                    ground=ground, ghost_alpha=alpha_glanced,
                    bloom=(("T*2.1" in wq and "T*1.5" in wq) or "U*0.84" in wq),
                    stroke_weight=(("U * 0.40" in wq and "U * 0.26" in wq)
                                   or ("U*0.40" in wq and "U*0.26" in wq))))

    # KDE splash & plymouth — GLANCED-AT; the palette's ghost at the glanced alpha
    reg.append(dict(name="kde-splash", mode=GLANCED_AT, lit=lit, ghost=ghost,
                    ground=ground, ghost_alpha=alpha_glanced, bloom=False, stroke_weight=False))
    reg.append(dict(name="plymouth", mode=GLANCED_AT, lit=lit, ghost=ghost,
                    ground=ground, ghost_alpha=alpha_glanced, bloom=False, stroke_weight=False))

    # notify marquee — lit text on void, no ghost -> exempt
    reg.append(dict(name="notify-marquee", mode=LOOKED_AT, lit=lit, ghost=ghost,
                    ground=ground, has_ghost=False))

    return reg


def run(variant="EL-Azure", verbose=True):
    rows = []
    allok = True
    for s in surface_registry(variant):
        ok, eff, floor, detail = audit_surface(
            s["name"], s.get("mode", GLANCED_AT), s["lit"], s["ghost"], s["ground"],
            s.get("ghost_alpha", 1.0), s.get("bloom", False),
            s.get("stroke_weight", False), s.get("has_ghost", True))
        rows.append((s["name"], s.get("mode"), ok, eff, floor, detail))
        if not ok:
            allok = False
    if verbose:
        print(f"glance audit ({variant}):")
        for name, mode, ok, eff, floor, detail in rows:
            e = f"{eff:.2f}" if eff is not None else "  -"
            f = f"{floor:.1f}" if floor is not None else " - "
            print(f"  {name:<16} {mode:<11} eff={e:>5} floor={f:>4} "
                  f"[{detail}] {'OK' if ok else 'FAIL'}")
    return allok, rows


if __name__ == "__main__":
    ok, _ = run("EL-Azure")
    print("all surfaces meet their parsing-mode floor:", ok)
