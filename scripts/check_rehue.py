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


def problems(tabs):
    bad = []
    for v, (ground, fg, ghost, tab) in tabs.items():
        if abs(C.apca_Lc(fg, ground)) < MP.LIT_FLOOR_LC:
            bad.append(f"{v}: fg itself is under the lit floor ({abs(C.apca_Lc(fg, ground)):.1f} < {MP.LIT_FLOOR_LC})")
        for h, col, ok in tab:
            if ok:
                if abs(C.apca_Lc(col, ground)) < MP.LIT_FLOOR_LC:
                    bad.append(f"{v}: hue {h:.0f} accepted under the lit floor")
                if C._worst_normalized(col, ghost, C.reference_floors())[0] < 1.0:
                    bad.append(f"{v}: hue {h:.0f} accepted but not separable from the ghost")
            elif col != fg:
                bad.append(f"{v}: hue {h:.0f} fell back to {col}, not fg {fg}")
        if not any(ok for _h, _c, ok in tab):
            bad.append(f"{v}: every hue falls back — the read is dead")
    return bad


def main(argv):
    known = {"--map", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_rehue: unknown flag {a!r}", file=sys.stderr)
            return 2
    tabs = tables()
    if not tabs:
        print("check_rehue: REFUSED — no variants", file=sys.stderr)
        return 2
    if "--map" in argv:
        for v, (ground, fg, ghost, tab) in tabs.items():
            acc = [f"{h:.0f}" for h, _c, ok in tab if ok]
            print(f"{v:16s} fg {fg}  accepted {len(acc)}/{len(tab)}: {' '.join(acc)}")
        return 0
    bad = problems(tabs)
    if bad:
        print(f"check_rehue: REFUSED — {len(bad)} problem(s) over {len(tabs)} variants:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    n_acc = sum(1 for t in tabs.values() for _h, _c, ok in t[3] if ok)
    n_all = sum(len(t[3]) for t in tabs.values())
    print(f"check_rehue: {len(tabs)} of {len(tabs)} variants gate a sender's hue as stated — "
          f"{n_acc} of {n_all} hue buckets accepted, the rest fall back to fg")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    tabs = tables()
    chk("six variants", len(tabs), 6)
    chk("the real tables have no problems", problems(tabs), [])
    chk("some hue is rejected somewhere (the gate discriminates)",
        any(not okk for t in tabs.values() for _h, _c, okk in t[3]), True)
    # ⚑ SYNTHETIC: a ground equal to fg makes every hue fail the lit floor -> all fallback,
    # and the check must call that dead
    ground, fg, ghost, _t = tabs["EL-Azure"]
    dead = MP.hue_table(fg, fg, ghost)
    chk("a dead table is all fallback", all(not okk for _h, _c, okk in dead), True)
    chk("...and is refused", any("dead" in b for b in problems({"SYN": (fg, fg, ghost, dead)})), True)
    col, accepted = MP.rehue(fg, 60.0, ground, ghost)
    chk("an accepted hue differs from fg", accepted and col != fg, True)
    col2, accepted2 = MP.rehue(fg, 240.0, ground, ghost)
    chk("a hue under the floor on the dark ground falls back to fg", (accepted2, col2), (False, fg))
    # a forged table entry that claims ok but is under the floor is seen
    forged = [(0.0, ground, True)]
    chk("a forged accepted entry under the floor is seen",
        any("under the lit floor" in b for b in problems({"SYN": (ground, fg, ghost, forged)})), True)
    print("check_rehue selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
