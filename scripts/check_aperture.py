#!/usr/bin/env python3
"""check_aperture.py — the aperture field's brightness relation, MEASURED on pixels (W54).

The relation (operator, 2026-09-22: pips with a brightness RANGE — a mask over a
higher-resolution backdrop): a pip's seen colour is ghost composited at
ghostAlpha + coverage·(1−ghostAlpha) over the ground, lit at full coverage. The
probe (templates/aperture-probe.qml, rendered by render_qml under each variant's
scheme) puts a block's edge exactly half a pip into column 10, so three pips
carry the whole relation: column 9 (clear: the ghost floor), column 10 (half),
column 11 (covered: the lit token). This reads those pixels beside what the
scheme says they should be; policy/aperture.rego decides.

    scripts/check_aperture.py --json      # the measurement, six variants
    scripts/check_aperture.py --selftest  # the measurement can see

WEAKNESS: one pixel per pip, at the pip's centre — the antialiased rim is not
read. A missing qml runner is a withheld fact per variant, not a failure. Renders
under the software scene graph on purpose (EL_RENDER_SOFTWARE): the field must
be seen where the ebuild sandbox sees it.
"""
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))
VARIANTS = ("EL-Openglo", "EL-Openglo-Lit", "EL-Azure", "EL-Azure-Lit", "EL-Amber", "EL-Amber-Lit")
U, ROWS, EDGE_COL = 4, 8, 10          # the probe's pitch, rows and edge column


def _hex(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def expected(variant):
    """{ground, ghost, lit, alpha, pips: {clear, half, covered}} — what the scheme says
    the three pips should read: ghost over ground at alpha, at alpha+0.5(1-alpha) the
    ghost layer plus half the lit layer, and lit."""
    import make_preview as MP
    import make_wallpaper_live as WL
    s = MP.parse_scheme(variant)
    ground = _hex(s["ground"])        # the harness window's ground (render_qml), not the View one
    ghost, lit = _hex(s["ghost"]), _hex(s["phosphor"])
    a = WL.global_alpha("looked_at")

    def over(base, top, alpha):
        return tuple(round(b + (t - b) * alpha) for b, t in zip(base, top))
    clear = over(ground, ghost, a)
    return {"ground": ground, "ghost": ghost, "lit": lit, "alpha": a,
            "pips": {"clear": clear, "half": over(clear, lit, 0.5), "covered": lit}}


def read_pips(png, height=40):
    from PIL import Image
    im = Image.open(png).convert("RGB")
    y = (height - ROWS * U) // 2 + 4 * U + U // 2      # row 4's centre
    return {name: im.getpixel((col * U + U // 2, y))
            for name, col in (("clear", EDGE_COL - 1), ("half", EDGE_COL), ("covered", EDGE_COL + 1))}


def measure(variants=VARIANTS):
    import render_qml as RQ
    rows = []
    for v in variants:
        row = {"variant": v, "expected": {k: list(p) for k, p in expected(v)["pips"].items()}}
        if not os.path.exists(RQ.QML):
            row["withheld"] = f"{RQ.QML} is not installed"
            rows.append(row)
            continue
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "ap.png")
            rc, err = RQ.render("aperture", v, 420, 40, out, software=True)
            if rc != 0 or not os.path.isfile(out):
                row["withheld"] = f"render failed (rc={rc}): {err[-300:]}"
            else:
                seen = read_pips(out)
                row["seen"] = {k: list(p) for k, p in seen.items()}
                row["error"] = {k: max(abs(a - b) for a, b in zip(seen[k], expected(v)["pips"][k])) for k in seen}
        rows.append(row)
    return {"variants": rows}


def main(argv):
    known = {"--json", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_aperture: unknown flag {a!r}", file=sys.stderr)
            return 2
    m = measure()
    if "--json" in argv:
        print(json.dumps(m, indent=1))
        return 0
    for r in m["variants"]:
        if "withheld" in r:
            print(f"  {r['variant']}: WITHHELD {r['withheld']}")
        else:
            print(f"  {r['variant']}: clear/half/covered max error {r['error']}")
    print(f"check_aperture: {len(m['variants'])} variant(s) measured; the verdict is `opa_gate.py aperture`")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    from PIL import Image
    e = expected("EL-Amber")
    chk("the half pip is between the floor and the lit token",
        all(e["pips"]["clear"][i] <= e["pips"]["half"][i] <= e["pips"]["covered"][i] for i in range(3)), True)
    # ⚑ THE MEASUREMENT CAN SEE: a picture where every pip is the ghost floor (no
    # lit layer at all — a field that ignored its backdrop) reads a wrong half and
    # a wrong covered pip
    with tempfile.TemporaryDirectory() as td:
        im = Image.new("RGB", (420, 40), e["ground"])
        for c in range(105):
            im.putpixel((c * U + U // 2, (40 - ROWS * U) // 2 + 4 * U + U // 2), e["pips"]["clear"])
        p = os.path.join(td, "flat.png")
        im.save(p)
        seen = read_pips(p)
        chk("a field that ignored its backdrop is seen (covered pip is not lit)", seen["covered"] == e["pips"]["covered"], False)
        chk("...and its clear pip still reads the floor", seen["clear"], e["pips"]["clear"])
    print("check_aperture selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    os.chdir(ROOT)
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
