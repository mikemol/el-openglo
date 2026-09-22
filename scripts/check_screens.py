#!/usr/bin/env python3
"""check_screens.py — the themed screenshots, MEASURED; policy/screens.rego decides (W52).

The pictures are catalog/library/render_screens.py's; this reports, per planned
still, whether the file exists, its size, how many distinct colours it has and
its modal colour, beside the two honest grounds of its variant (the harness
window's and the View background a bound surface draws). The requirement — a
still exists, is not blank, and sits on its variant's ground — is the policy's.

    scripts/check_screens.py --json      # the measurement
    scripts/check_screens.py --selftest  # the measurement can see

A missing screens/ directory is reported as every still absent (the policy
denies), because the pictures are checked in: an emitter change without a
regeneration is exactly what this catches.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "catalog", "library"))


def measure():
    import render_screens as RS
    return RS.measure()


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_screens: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    print(f"check_screens: {sum(1 for r in m['screens'] if r['exists'])} of {len(m['screens'])} stills present; "
          f"the verdict is `opa_gate.py screens`")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    import render_screens as RS
    import tempfile
    from PIL import Image
    m = measure()
    chk("the plan is 6 stills x 6 variants", len(m["screens"]), 36)
    # ⚑ THE MEASUREMENT CAN SEE: a blank picture has one distinct colour; a picture
    # on the wrong ground has a modal colour that is neither of the variant's
    with tempfile.TemporaryDirectory() as td:
        Image.new("RGB", (40, 20), (255, 0, 0)).save(os.path.join(td, "clock-EL-Amber.png"))
        rows = RS.measure(td)["screens"]
        r = next(x for x in rows if x["file"] == "clock-EL-Amber.png")
        chk("a blank still is a fact (1 distinct colour)", r["distinct"], 1)
        chk("a wrong ground is a fact", r["modal"] in r["grounds"], False)
        chk("an absent still is a fact", next(x for x in rows if x["file"] == "switcher-EL-Amber.png")["exists"], False)
        # an animation the measurement can see TEAR: a FIELD of ghost pips (one
        # column every 4 px) with three lit pips that shift left by one pip, then
        # move RIGHT by twelve (a restart — no left shift explains it), then shift
        # left by one again; the first frame is the empty field, the last is not
        ghost, litc, gnd = (152, 126, 90), (255, 212, 153), (20, 15, 8)
        frames = []
        for lit_at in (None, 75, 74, 86, 85):
            f = Image.new("RGB", (400, 20), gnd)
            for c in range(100):
                on = lit_at is not None and lit_at <= c < lit_at + 3
                for y in range(4, 16):
                    f.putpixel((4 * c + 2, y), litc if on else ghost)
            frames.append(f)
        ap = os.path.join(td, "marquee-anim-EL-Amber.png")
        frames[0].save(ap, format="PNG", save_all=True, append_images=frames[1:], duration=40, loop=0)
        a = RS.animation_facts(ap, "#ffd499", "#140f08")
        chk("the frames are counted", a["frames"], 5)
        chk("the pips are found from the empty board", a["pips"], 100)
        chk("a rightward move is a tear, the one-pip shifts are not", [t["frame"] for t in a["tears"]], [3])
        chk("the one-pip shifts are read", [k for k in a["shifts"] if k == 1.0], [1.0, 1.0])
        chk("an open loop is a fact (first and last frames differ)", a["seamless"], False)
        # along y (the viewport): a field of pip ROWS with one lit row stepping down
        # one pip per frame, then up — a ping-pong is admitted on the y axis
        frames = []
        for lit_row in (2, 3, 4, 3, 2):
            f = Image.new("RGB", (60, 40), gnd)
            for r in range(10):
                for c in range(15):
                    for dx in range(4):
                        for dy in (1, 2):
                            f.putpixel((4 * c + dx, 4 * r + dy), litc if r == lit_row else ghost)
            frames.append(f)
        ap = os.path.join(td, "pinholes-anim-EL-Amber.png")
        frames[0].save(ap, format="PNG", save_all=True, append_images=frames[1:], duration=40, loop=0)
        a = RS.animation_facts(ap, "#ffd499", "#140f08", axis="y")
        chk("the pip rows are found along y", a["pips"], 10)
        # content moving DOWN the field is a shift of -1 (the viewport's band moving
        # down the backdrop moves content UP: +1); a ping-pong is admitted on y
        chk("a ping-pong along y is shifts of -1 then +1, no tear", (a["shifts"], a["tears"]), ([-1.0, -1.0, 1.0, 1.0], []))
        chk("...and it loops", a["seamless"], True)
    print("check_screens selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
