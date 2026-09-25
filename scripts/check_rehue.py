#!/usr/bin/env python3
"""check_rehue.py — a sender's hue on the lit token is GATED, and falls back.

⚑ WHAT IS CHECKED (relations.md §5a).  make_palette.rehue keeps fg's own
saturation and value, swaps in a sender's hue, and returns the candidate ONLY
if it clears the lit floor against the ground (APCA LIT_FLOOR_LC) and the
gate's own worst-view separation from the ghost; otherwise fg. This reads the
12-bucket hue table per variant and requires: fg itself clears the lit floor;
every accepted entry clears both floors; every fallback IS fg; the table is
not all-fallback (the read would be dead) — and, measured 2026-09-22, not
all-accepted on the dark variants either (blue/violet fall under Lc 60 there),
which is the gate discriminating.

    scripts/check_rehue.py           # exit 0 iff every variant's table is gated as stated
    scripts/check_rehue.py --map     # the table per variant
    scripts/check_rehue.py --selftest
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import cvd_gate as C                                              # noqa: E402
import make_palette as MP                                         # noqa: E402
import make_wallpaper_live as WL                                  # noqa: E402

sys.path.insert(0, os.path.join(ROOT, "scripts"))
import variant_roster                                              # noqa: E402


def tables():
    out = {}
    for v in variant_roster.ids():         # the declared roster (W61 B2), not a typed tuple
        ground, fg, ghost, _a = WL.colors_for(v)
        out[v] = (ground, fg, ghost, MP.hue_table(fg, ground, ghost))
    return out


def measure(tabs=None):
    """The MEASUREMENT policy/rehue.rego decides (W50): per variant, fg's lit
    Lc against the ground and the floor; per hue bucket its accepted flag, its
    colour's Lc, its worst-view separation from the ghost (normalised; >= 1 is
    separable), and whether it IS fg. No judgement here — which of those is a
    defect is the policy's ruling."""
    tabs = tables() if tabs is None else tabs
    floors = C.reference_floors()
    cases = []
    for v, (ground, fg, ghost, tab) in tabs.items():
        cases.append({
            "id": v,
            "floor": MP.LIT_FLOOR_LC,
            "fg_lc": abs(C.apca_Lc(fg, ground)),
            "buckets": [{"hue": h, "accepted": bool(ok), "is_fg": col == fg,
                         "lc": abs(C.apca_Lc(col, ground)),
                         "sep": C._worst_normalized(col, ghost, floors)[0]}
                        for h, col, ok in tab],
        })
    return {"roster": list(variant_roster.ids()), "cases": cases}


def main(argv):
    known = {"--map", "--selftest", "--json"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_rehue: unknown flag {a!r}", file=sys.stderr)
            return 2
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    if "--map" in argv:
        for v, (ground, fg, ghost, tab) in tables().items():
            acc = [f"{h:.0f}" for h, _c, ok in tab if ok]
            print(f"{v:16s} fg {fg}  accepted {len(acc)}/{len(tab)}: {' '.join(acc)}")
        return 0
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import opa_gate
    return opa_gate.gate("rehue")


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    # The MEASUREMENT can see; what is a defect is policy/rehue_test.rego's (W50).
    tabs = tables()
    m = measure(tabs)
    chk("every declared variant is measured", sorted(c["id"] for c in m["cases"]), sorted(m["roster"]))
    chk("some hue is rejected somewhere (the measurement discriminates)",
        any(not b["accepted"] for c in m["cases"] for b in c["buckets"]), True)
    # ⚑ SYNTHETIC: a ground equal to fg makes every hue fail the lit floor -> all
    # fallback; the measurement must report every bucket rejected and is_fg
    ground, fg, ghost, _t = tabs["EL-Azure"]
    dead = measure({"SYN": (fg, fg, ghost, MP.hue_table(fg, fg, ghost))})["cases"][0]
    chk("a dead table measures all-rejected, all fg",
        all(not b["accepted"] and b["is_fg"] for b in dead["buckets"]), True)
    col, accepted = MP.rehue(fg, 60.0, ground, ghost)
    chk("an accepted hue differs from fg", accepted and col != fg, True)
    col2, accepted2 = MP.rehue(fg, 240.0, ground, ghost)
    chk("a hue under the floor on the dark ground falls back to fg", (accepted2, col2), (False, fg))
    # a forged entry that claims ok on the ground colour itself measures Lc 0
    forged = measure({"SYN": (ground, fg, ghost, [(0.0, ground, True)])})["cases"][0]["buckets"][0]
    chk("a forged accepted entry is measured at its real Lc", (forged["accepted"], forged["lc"] < 1), (True, True))
    print("check_rehue selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
