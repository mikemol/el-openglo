#!/usr/bin/env python3
"""Parametric palette solver (⊕PARAMETRIC-PALETTE).

The project's inversion: stop AUTHORING color values and TESTING them; instead
DERIVE every color as the solution (argmax) of the constraint it must satisfy.
A stored value is a cache of a computation that goes stale when the constraint
changes; solving on demand means nothing can rot.

Two inputs are NOT derivable and remain explicit:
  1. HUE_SEED — the identity (openglo/azure/amber). No contrast constraint implies
     a hue; derive it and all variants collapse to the same legible palette and
     identity evaporates. The seed picks WHERE in the admissible region we sit.
  2. THRESHOLDS — Lc readability ceiling, chroma floor, void luminance. Judgment
     lives here now (which constraint at which value), not in "which color".

Everything else is solved/derived:
  void  = argmax darkness on the hue s.t. luminance <= void_max AND chroma held
  lit   = argmax APCA contrast from ground within the hue, chroma >= chroma_floor
  ghost = argmax contrast s.t. it FAILS readability (APCA |Lc| < ghost_ceiling)
  accent= the hue at full usable chroma
  ...then ~34 UI tokens derived by fixed transforms off those primitives.
"""
import colorsys
import random as _random
import cvd_gate as C

# ---- the two non-derivable inputs -----------------------------------------
HUE_SEEDS = {          # base hue (HSV degrees) — the identity, chosen not solved
    "openglo": 168.0,  # teal-green electroluminescent
    "azure":   210.0,  # blue backlight
    "amber":   35.0,   # classic LCD amber
}

THRESHOLDS = dict(
    void_max_lum=C.OLED_VOID_MAX_LUM,   # 2% — ground reads as OLED void
    chroma_floor=40,                    # keep the phosphor hue (not grey/black)
    ghost_ceiling_lc=C.GHOST_READABLE_LC,  # 30 — ghost must FAIL readability
)


def _hsv(h_deg, s, v):
    r, g, b = colorsys.hsv_to_rgb((h_deg % 360) / 360.0, s, v)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def _chroma(rgb):
    return max(rgb) - min(rgb)


def solve_void(hue, thr):
    """Deepest ground on the hue that still reads as OLED void (L <= void_max) AND
    keeps a faint substrate chroma. argmax darkness s.t. void + hue held."""
    best = None
    # walk value up from black; keep the darkest that is void AND has some chroma
    for k in range(2, 40):
        v = k / 500.0                      # very low values
        cand = _hsv(hue, 0.62, v)          # saturated so a little chroma survives
        L = C._wcag_L(cand)
        if L <= thr["void_max_lum"] and _chroma(cand) >= 3:
            best = cand
        elif L > thr["void_max_lum"]:
            break
    return best or _hsv(hue, 0.6, 0.03)


def solve_lit(hue, ground, thr):
    """Max APCA contrast from the ground within the hue, chroma >= floor. For a
    dark ground this drives lit bright; for a light (backlit) ground, dark."""
    dark_ground = C._wcag_L(ground) < 0.4
    best = None
    best_lc = -1
    for si in range(4, 11):                 # saturation 0.4..1.0
        s = si / 10.0
        vs = range(55, 101) if dark_ground else range(8, 46)
        for vi in vs:
            v = vi / 100.0
            cand = _hsv(hue, s, v)
            if _chroma(cand) < thr["chroma_floor"]:
                continue
            lc = abs(C.apca_Lc(cand, ground))
            if lc > best_lc:
                best_lc, best = lc, cand
    return best or _hsv(hue, 0.9, 0.9 if dark_ground else 0.2)


def solve_ghost(lit, ground, thr):
    """The ceiling ghost: max contrast that FAILS readability (APCA |Lc| < ceiling)."""
    return C.derive_ghost_ceiling(lit, ground, thr["ghost_ceiling_lc"])


def solve_accent(hue, ground, min_contrast=4.6):
    """Full-chroma hue for highlights/selection — the 'hot' phosphor. Argmax'd so
    it CLEARS contrast against the ground (on light backlit grounds a bright accent
    fails, so drive value down until it clears)."""
    dark_ground = C._wcag_L(ground) < 0.4
    best, best_c = None, -1.0
    for si in (7, 8, 9):
        s = si / 10.0
        vs = range(80, 101, 3) if dark_ground else range(30, 62, 3)
        for vi in vs:
            cand = _hsv(hue, s, vi / 100.0)
            cr = C.wcag_ratio(cand, ground)
            if cr >= min_contrast and cr > best_c:
                best_c, best = cr, cand
    return best or _hsv(hue, 0.85, 0.95 if dark_ground else 0.4)


# required hue sectors for semantic accents (from cvd_gate.SECTORS)
# ⚑ THE SECTOR TABLE IS NOT OURS TO KEEP A COPY OF.  A private `_SECTORS` fork
# lived here — the same table the gate audits against, duplicated in the module
# that optimises against it.  Two copies of one authority is the carrier-locality
# disease: edit the gate's table and the solver keeps optimising for the old
# sectors, silently, with every scheme still "passing" its own stale assumption.
# One table, one home, imported.
_SECTORS = C.SECTORS


def _sector_hue(sector):
    lo, hi = sector
    return ((lo + hi) / 2.0) if lo <= hi else (((lo + hi + 360) / 2.0) % 360)


def _candidates(sector, ground, min_contrast, hot):
    """In-sector colors clearing contrast-vs-ground and CVD-distinct from hot.
    ⊕SOLVER-BACKLIT-CVD: the constellation's distinctness lives in whatever axis is
    FREE. On a dark ground VALUE is free (bright->dark), so a narrow hue span
    suffices. On a LIGHT ground value is PINNED dark by the contrast floor, so we
    widen HUE (full sector) and CHROMA (deeper sats) to recover the separation
    value can't provide. (Not by lowering the contrast floor — that harms
    readability; wrong axis.)"""
    lo, hi = sector
    hmid = _sector_hue(sector)
    dark = C._wcag_L(ground) < 0.4
    # Hue span: wider on light grounds (value pinned -> distinctness in hue/chroma).
    # Value span: FULL range on BOTH grounds — when the hue seed collides with a
    # semantic sector (e.g. blue azure phosphor vs the blue `link` sector), the
    # only way to separate is by LIGHTNESS, so we must not starve the value axis.
    span = range(-24, 25, 8) if dark else range(-40, 41, 6)
    sats = (0.5, 0.7, 0.85, 1.0)
    vs = range(34, 101, 7) if dark else range(20, 64, 5)
    out = []
    for dh in span:
        h = (hmid + dh) % 360
        # strictly inside the sector with a 1-degree margin (a candidate exactly on
        # the boundary, e.g. hue 90 for the 90-170 pos sector, trips the exclusive
        # gate check).
        if lo > hi:
            inside = (h >= lo + 1) or (h <= hi - 1)
        else:
            inside = (lo + 1) <= h <= (hi - 1)
        if not inside:
            continue
        for s in sats:
            for vi in vs:
                cand = _hsv(h, s, vi / 100.0)
                if C.wcag_ratio(cand, ground) < min_contrast:
                    continue
                if hot is not None and _cached_dE(cand, hot) < 5.0:
                    continue
                out.append(cand)
    # cap to a diverse subset (even stride keeps the value/hue spread) — the
    # max-min search cost is superlinear in candidate count, and ~40 well-spread
    # candidates carry the same reachable optima as hundreds.
    if len(out) > 40:
        stride = len(out) / 40.0
        out = [out[int(i * stride)] for i in range(40)]
    return out


_DE_CACHE = {}
def _cached_dE(a, b):
    key = (a, b) if a <= b else (b, a)
    v = _DE_CACHE.get(key)
    if v is None:
        v = C.worst_view_dE(a, b)[0]
        _DE_CACHE[key] = v
    return v


def solve_semantic_set(sectors, ground, hot, min_contrast=4.6, anchors=()):
    """JOINT solve of the semantic-accent constellation. Each slot draws from its
    in-sector, contrast-clearing, hot-distinct candidates; we choose one per slot
    to MAXIMIZE THE MINIMUM pairwise separation across the whole set (the binding
    constraint that independent argmax ignores).

    `anchors` are colours already fixed (the lit foreground) that the constellation
    must ALSO stay separated from — they participate in the min-pair objective but
    are never chosen.

    ⚑ THE OBJECTIVE IS THE GATE'S OWN METRIC, NOT RAW ΔE.  This is the ⊕SOLVER-
    BACKLIT-CVD result, and it is the whole reason the solver can be trusted to
    ship: the gate normalizes ΔE by a per-view floor and fails if q < 1 in ANY
    view, so a solver maximising raw global min-ΔE optimises a PROXY and can hand
    back a palette the gate then rejects. Instrument-vs-world. Maximise q.

    ⚑ MULTI-RESTART, NOT SINGLE GREEDY.  Greedy local optima oscillated under the
    floor; a greedy seed plus deterministic random restarts converges reliably.
    The seed is fixed, so the solve is reproducible — a palette that changed
    between runs would make every downstream diff meaningless."""
    slots = list(sectors.keys())
    cands = {k: _candidates(sectors[k], ground, min_contrast, hot) for k in slots}
    # relax contrast if any slot has no candidate (report via fallback)
    for k in slots:
        if not cands[k]:
            mc = min_contrast
            while not cands[k] and mc > 3.0:
                mc -= 0.3
                cands[k] = _candidates(sectors[k], ground, mc, hot)
            if not cands[k]:
                cands[k] = [_hsv(_sector_hue(sectors[k]), 0.85,
                                 0.85 if C._wcag_L(ground) < 0.4 else 0.4)]

    _floors = C.reference_floors()

    def min_pair(chosen):
        """The GATE's metric: worst normalized q over every pair, anchors included."""
        vals = list(chosen.values()) + [tuple(a) for a in anchors]
        m = 1e9
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                q = C._worst_normalized(vals[i], vals[j], _floors)[0]
                m = min(m, q)
        return m

    def _hillclimb(seed):
        """Local search from one seed; returns (chosen, score)."""
        chosen = dict(seed)
        best_score = min_pair(chosen)
        improved, _rounds = True, 0
        while improved and _rounds < 6:  # max-min converges fast; bound the search
            improved = False
            _rounds += 1
            for k in slots:
                for cand in cands[k]:
                    if cand == chosen[k]:
                        continue
                    trial = dict(chosen, **{k: cand})
                    s = min_pair(trial)
                    if s > best_score:
                        chosen, best_score, improved = trial, s, True
        return chosen, best_score

    # greedy seed: each slot's most-saturated candidate …
    greedy = {k: max(cands[k], key=lambda c: _chroma(c)) for k in slots}
    chosen, best_score = _hillclimb(greedy)

    # … then deterministic random restarts, because greedy alone oscillated under
    # the floor.  Stop early once the gate is satisfied (q >= 1 in every view).
    if best_score < 1.0:
        rng = _random.Random(20260804)          # fixed: the solve must reproduce
        for _ in range(8):
            seed = {k: rng.choice(cands[k]) for k in slots}
            cand_chosen, cand_score = _hillclimb(seed)
            if cand_score > best_score:
                chosen, best_score = cand_chosen, cand_score
            if best_score >= 1.0:
                break
    return chosen, best_score




# ---- derived transforms (no search) ---------------------------------------
def _lum_nudge(rgb, delta):
    h, l, s = colorsys.rgb_to_hls(*[c / 255.0 for c in rgb])
    l = max(0.0, min(1.0, l + delta))
    r, g, b = colorsys.hls_to_rgb(h, l, s)
    return (int(round(r * 255)), int(round(g * 255)), int(round(b * 255)))


def _mix(a, b, t):
    return tuple(int(round(a[i] * (1 - t) + b[i] * t)) for i in range(3))


def _s(rgb):
    return "%d,%d,%d" % rgb


_SECTOR_OVERRIDES = {"EL-Amber-Lit": {"neu": (30, 95)}}


def _sect(slot, vid):
    return _SECTOR_OVERRIDES.get(vid, {}).get(slot, _SECTORS[slot])


def solve_scheme(seed_name, polarity, thr=THRESHOLDS):
    """polarity: 'off' (dark display) or 'lit' (backlit). Returns a full token
    dict — every value SOLVED or DERIVED from (hue, polarity, thresholds)."""
    hue = HUE_SEEDS[seed_name]
    # in lit/backlit mode the ground is the bright field, lit is the dark segment:
    # solve the OFF ground first, then invert for lit polarity.
    dark_ground = solve_void(hue, thr)
    if polarity == "off":
        ground = dark_ground
    else:
        # backlit: ground is the phosphor field lit up (bright), a light tint of hue
        ground = _hsv(hue, 0.28, 0.92)
    lit = solve_lit(hue, ground, thr)
    ghost = solve_ghost(lit, ground, thr)
    accent = solve_accent(hue, ground)

    name = f"EL {seed_name.capitalize()}" + ("" if polarity == "off" else " Lit")
    vid = "EL-" + seed_name.capitalize() + ("" if polarity == "off" else "-Lit")

    # semantic accents — JOINT constellation solve (⊕SOLVER-SEMANTIC): all five
    # placed together to maximize the MIN pairwise CVD-distance, each in-sector,
    # contrast-clearing, hot-distinct. The coupling is the constraint.
    _sem_sectors = {k: _sect(k, vid) for k in ("neg", "neu", "pos", "link", "visited")}
    _min_c = 4.6 if C._wcag_L(ground) < 0.4 else 4.6
    _sem, _sem_score = solve_semantic_set(_sem_sectors, ground, accent, _min_c,
                                          anchors=[lit])

    # panel ladder: ground raised by small fixed steps (derived, no search)
    up = 1 if C._wcag_L(ground) < 0.4 else -1
    window = _lum_nudge(ground, 0.03 * up)
    header = _lum_nudge(ground, 0.02 * up)
    tt_bg = _lum_nudge(ground, 0.025 * up)
    button = _lum_nudge(ground, 0.06 * up)
    comp = ground

    name = f"EL {seed_name.capitalize()}" + ("" if polarity == "off" else " Lit")
    vid = "EL-" + seed_name.capitalize() + ("" if polarity == "off" else "-Lit")

    t = {
        "name": name, "id": vid,
        "view": _s(ground), "view_alt": _s(_lum_nudge(ground, 0.015 * up)),
        "window": _s(window), "window_alt": _s(_lum_nudge(window, 0.01 * up)),
        "button": _s(button), "button_alt": _s(_lum_nudge(button, 0.01 * up)),
        "header": _s(header), "header_alt": _s(_lum_nudge(header, 0.01 * up)),
        "hdr_in_bg": _s(header), "hdr_in_alt": _s(_lum_nudge(header, 0.01 * up)),
        "comp": _s(comp), "comp_alt": _s(_lum_nudge(comp, 0.01 * up)),
        "tt_bg": _s(tt_bg), "tt_alt": _s(_lum_nudge(tt_bg, 0.01 * up)),
        # phosphor foregrounds = the solved lit / ghost primitives
        "fg": _s(lit), "fg_act": _s(accent), "fg_in": _s(ghost),
        # ⚑ THE FOCUS RING IS THE ACCENT, NOT THE BODY TEXT.  `focus` read
        # `_s(lit)` — the same value as `fg` — so DecorationFocus and
        # View/ForegroundNormal emitted byte-identically in all six variants, and
        # a focus ring the exact colour of the text it surrounds cannot mark
        # anything. The README names them as different roles (`body-glow` is
        # normal text, `el-core` is the focus ring / accent), and `accent` was
        # already solved and already in use for fg_act and hover.
        #
        # ⚑ NO EXISTING GATE COULD SEE IT.  Every colour check here asks whether
        # something is legible AGAINST A BACKGROUND, and both values are — just
        # not from each other. "Is this role distinguishable from THAT role" is a
        # different question, and it took rendering the palette into
        # catalog/library/ and looking at the swatch to ask it.
        # ⚑ AND HOVER IS NOT FOCUS EITHER.  Pointing `focus` at `accent` alone
        # would have moved the collision rather than removed it, since `hover`
        # was already `accent`. The log records the intended relation — "old
        # focus demoted to hover" (:277) — so they are two decoration STATES: the
        # ring you have focused and the one you are merely over. Hover is the
        # accent stepped toward the ground, which keeps the hue and separates the
        # state.
        "focus": _s(accent),
        "hover": _s(_lum_nudge(accent, -0.12 if C._wcag_L(ground) < 0.4 else 0.12)),
        # semantic accents — from the JOINT constellation solve (mutually distinct)
        "link": _s(_sem["link"]),
        "visited": _s(_sem["visited"]),
        "neg": _s(_sem["neg"]),
        "neu": _s(_sem["neu"]),
        "pos": _s(_sem["pos"]),
        # selection = accent-tinted
        # selection = accent field. sel_fg must contrast the accent bg; on dark
        # grounds the void works, on light grounds this is the compressed-range
        # hard case tracked as ⊕SOLVER-SEL-BACKLIT (residue).
        # ⚑ sel_act IS A FOREGROUND, AND IT WAS BEING DERIVED FROM THE BACKGROUND.
        # It read `_lum_nudge(accent, 0.1)` — the selection background nudged 10%
        # in luminance — so by construction it could never contrast with the
        # surface it is drawn on. Measured across all six variants: 1.00:1 to
        # 1.89:1, i.e. text very nearly the exact colour of its own background.
        # `sel_fg` beside it already had the right idea (the inverted `ground`,
        # measuring 7.2:1-14.3:1), so ACTIVE is that same inversion pushed further
        # from the background rather than nearer to it — active text should be the
        # MOST legible thing in the group, not the least.
        # ⚑ THE SELECTION FIELD IS THE ACCENT'S HUE, NOT THE ACCENT'S VALUE.
        # `sel_bg` read `_s(accent)` — byte-identical to `focus` once the focus
        # ring stopped borrowing `lit` — so a focused item inside a selection had
        # a ring the exact colour of the field it sat on. Sharing the HUE is the
        # design ("selecting anything switches the backlight on", the same
        # el-core family); sharing the VALUE erases the boundary between the two.
        # Nudged toward the ground, as `sel_alt` beside it already does.
        "sel_bg": _s(_lum_nudge(accent, -0.08 if C._wcag_L(ground) < 0.4 else 0.08)),
        "sel_act": _s(_lum_nudge(ground, -0.15)),
        "sel_alt": _s(_lum_nudge(accent, -0.05)),
        "sel_fg": _s(ground), "sel_in": _s(_mix(accent, ground, 0.5)),
        "sel_link": _s(ground), "sel_vis": _s(_mix(ground, accent, 0.3)),
        "sel_neg": "45,10,10", "sel_neu": "45,30,8", "sel_pos": "10,40,20",
        "fx_dis": _s(ghost), "fx_in": _s(ghost),
        "tt_is_sel": "false",
    }
    return t


def build_grid():
    """Derive the whole GRID from seeds — the OUTPUT that used to be authored.
    The 2nd tuple element is the dark-counterpart SCHEME (a token dict) used for
    the Complementary color group — matching the authored GRID's shape, NOT a
    bool. Off-variant is its own counterpart; lit uses the off scheme."""
    grid = {}
    for seed in HUE_SEEDS:
        off = solve_scheme(seed, "off")
        lit = solve_scheme(seed, "lit")
        grid[(seed, "off")] = (off, off)
        grid[(seed, "lit")] = (lit, off)
    return grid


if __name__ == "__main__":
    for seed in HUE_SEEDS:
        for pol in ("off", "lit"):
            t = solve_scheme(seed, pol)
            g = tuple(int(x) for x in t["view"].split(","))
            l = tuple(int(x) for x in t["focus"].split(","))
            gh = tuple(int(x) for x in t["fg_in"].split(","))
            print(f"{t['id']:<16} void={t['view']:<12} lit={t['focus']:<12} "
                  f"ghost={t['fg_in']:<12} lit/void={C.wcag_ratio(l,g):.1f} "
                  f"ghostLc={abs(C.apca_Lc(gh,g)):.0f}")
