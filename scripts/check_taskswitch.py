#!/usr/bin/env python3
"""check_taskswitch.py — the Alt+Tab switcher packages are what KWin will load.

⚑ WHAT IS CHECKED.  make_taskswitch emits a KWin/WindowSwitcher package per
variant. KWin loads it by KPackageStructure and by the id the LnF defaults
name in [kwinrc][TabBox] LayoutName; an id mismatch is a stock switcher in
silence, and QML that does not parse is no switcher at all. So, per variant:
the metadata declares the structure and an id; the defaults name that id;
the emitted QML lints (qml_sanity's error ids) and its root is
KWin.TabBoxSwitcher; the four colour holes are filled from the variant's
tokens (ground/lit/ghost distinct; the ghost alpha is the solved one).

    scripts/check_taskswitch.py           # exit 0 iff every variant's package is loadable
    scripts/check_taskswitch.py --map     # variant -> package id, lit/ghost/ground
    scripts/check_taskswitch.py --selftest

The weakness, stated: this proves the package's SHAPE and that the QML parses
under qmllint; it does not run KWin, so a role KWin renamed would pass here
and fail on Alt+Tab. That is ⊕VER's probe.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.chdir(ROOT)                                                   # templates read by bare name
import make_taskswitch as MT                                     # noqa: E402
import qml_sanity as QS                                          # noqa: E402


def rows():
    out = []
    for v in MT.VARIANTS:
        meta = MT.metadata(v)
        qml = MT.main_qml(v)
        d = MT.defaults_fragment(v)
        m = re.search(r"LayoutName=(\S+)", d)
        cols = {k: re.search(rf'property color {k}Color:\s*"(#[0-9a-f]{{6}})"', qml)
                for k in ("lit", "ghost", "void")}
        alpha = re.search(r"property real ghostAlpha:\s*([0-9.]+)", qml)
        out.append({
            "variant": v,
            "structure": meta.get("KPackageStructure"),
            "id": meta["KPlugin"].get("Id"),
            "defaults_id": m.group(1) if m else None,
            "root": "KWin.TabBoxSwitcher {" in qml,
            "colors": {k: (c.group(1) if c else None) for k, c in cols.items()},
            "alpha": float(alpha.group(1)) if alpha else None,
            "qml": qml,
        })
    return out


def lint(qml):
    return QS.check_qml(qml, "taskswitch-main.qml")


def problems(rs):
    bad = []
    for r in rs:
        v = r["variant"]
        if r["structure"] != "KWin/WindowSwitcher":
            bad.append(f"{v}: KPackageStructure is {r['structure']!r}, not KWin/WindowSwitcher")
        if not r["id"] or r["id"] != r["defaults_id"]:
            bad.append(f"{v}: the LnF defaults name {r['defaults_id']!r} but the package id is {r['id']!r}")
        if not r["root"]:
            bad.append(f"{v}: the QML root is not KWin.TabBoxSwitcher")
        c = r["colors"]
        if None in c.values():
            bad.append(f"{v}: a colour hole is unfilled ({c})")
        elif len(set(c.values())) < 3:
            bad.append(f"{v}: lit/ghost/void are not distinct ({c})")
        if r["alpha"] is None or not (0.0 < r["alpha"] < 1.0):
            bad.append(f"{v}: ghostAlpha is {r['alpha']!r}")
        errs = lint(r["qml"])
        if errs:
            bad.append(f"{v}: the emitted QML has {len(errs)} error(s): {errs[0]}")
    return bad


def main(argv):
    known = {"--map", "--selftest"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_taskswitch: unknown flag {a!r}", file=sys.stderr)
            return 2
    rs = rows()
    if not rs:
        print("check_taskswitch: REFUSED — no variants", file=sys.stderr)
        return 2
    if "--map" in argv:
        for r in rs:
            c = r["colors"]
            print(f"{r['variant']:16s}  {r['id']:36s}  lit {c['lit']}  ghost {c['ghost']}  void {c['void']}  alpha {r['alpha']}")
        return 0
    bad = problems(rs)
    if bad:
        print(f"check_taskswitch: REFUSED — {len(bad)} problem(s) over {len(rs)} variants:", file=sys.stderr)
        for b in bad:
            print(f"    {b}", file=sys.stderr)
        return 1
    print(f"check_taskswitch: {len(rs)} of {len(rs)} switcher packages are loadable by shape "
          f"(structure, id named by the defaults, TabBoxSwitcher root, lint-clean, tokens filled)")
    return 0


def _selftest():
    ok = True

    def chk(label, got, want):
        nonlocal ok
        print(f"  {'ok  ' if got == want else 'FAIL'} {label}" + ("" if got == want else f": got {got!r} want {want!r}"))
        ok = ok and got == want

    rs = rows()
    chk("six variants", len(rs), 6)
    chk("the real packages have no problems", problems(rs), [])
    # ⚑ EACH ARM MUST BE ABLE TO FAIL, on synthetic rows
    base = dict(rs[0])
    wrong_id = dict(base, defaults_id="org.el.other")
    chk("an id the defaults do not name is seen", any("defaults name" in b for b in problems([wrong_id])), True)
    same_cols = dict(base, colors={"lit": "#111111", "ghost": "#111111", "void": "#111111"})
    chk("indistinct colours are seen", any("distinct" in b for b in problems([same_cols])), True)
    no_root = dict(base, root=False)
    chk("a non-TabBoxSwitcher root is seen", any("root" in b for b in problems([no_root])), True)
    broken = dict(base, qml=base["qml"].replace("KWin.TabBoxSwitcher {", "KWin.TabBoxSwitcher {{"))
    chk("QML that does not parse is seen", any("error" in b for b in problems([broken])), True)
    bad_alpha = dict(base, alpha=1.5)
    chk("an out-of-range ghostAlpha is seen", any("ghostAlpha" in b for b in problems([bad_alpha])), True)
    print("check_taskswitch selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
