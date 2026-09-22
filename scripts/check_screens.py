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
    chk("the plan is 5 stills x 6 variants", len(m["screens"]), 30)
    # ⚑ THE MEASUREMENT CAN SEE: a blank picture has one distinct colour; a picture
    # on the wrong ground has a modal colour that is neither of the variant's
    with tempfile.TemporaryDirectory() as td:
        Image.new("RGB", (40, 20), (255, 0, 0)).save(os.path.join(td, "clock-EL-Amber.png"))
        rows = RS.measure(td)["screens"]
        r = next(x for x in rows if x["file"] == "clock-EL-Amber.png")
        chk("a blank still is a fact (1 distinct colour)", r["distinct"], 1)
        chk("a wrong ground is a fact", r["modal"] in r["grounds"], False)
        chk("an absent still is a fact", next(x for x in rows if x["file"] == "switcher-EL-Amber.png")["exists"], False)
        # an animation the measurement can see TEAR: a lit block that shifts left
        # by 6, then moves RIGHT (a restart — no left shift explains it), then
        # shifts left by 6 again
        frames = []
        for x in (300, 294, 340, 334):
            f = Image.new("RGB", (400, 20), (20, 15, 8))
            for dx in range(10):
                for y in range(5, 15):
                    f.putpixel((x + dx, y), (255, 212, 153))
            frames.append(f)
        ap = os.path.join(td, "marquee-anim-EL-Amber.png")
        frames[0].save(ap, format="PNG", save_all=True, append_images=frames[1:], duration=40, loop=0)
        a = RS.animation_facts(ap, "#ffd499", "#140f08")
        chk("the frames are counted", a["frames"], 4)
        chk("a rightward move is a tear, the left shifts are not", [t["frame"] for t in a["tears"]], [2])
        chk("the left shifts are read", [k for k in a["shifts"] if k == 6], [6, 6])
    print("check_screens selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
