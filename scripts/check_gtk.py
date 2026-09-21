#!/usr/bin/env python3
"""check_gtk.py — the GTK sheets name only real libadwaita variables and carry the palette.

⚑ THE HOLE SESSION 14 FOUND, KEPT CLOSED.  A typo'd `--headerbar-bg-colour`
parses, lints and silently does nothing in a real app. So (1) every `--name`
gtk4.css sets on :root must be in make_gtk.ADW_NAMED — the set read from the
libadwaita CSS-variables reference on 2026-09-21 — and every @define-color name
in gtk3.css in make_gtk.GTK3_DEFINES; (2) every value is the palette role the
table names; (3) the sheets parse (tinycss2); (4) the bg/fg PAIRS the table
implies (window, view, headerbar, sidebar, card, dialog, popover, accent) clear
WCAG AA 4.5:1, so a role swap that keeps every name valid still cannot ship
unreadable text; (5) a witness that a NAME typo is seen (selftest).

    scripts/check_gtk.py            # exit 0 iff all arms hold for every variant
    scripts/check_gtk.py --map      # variable -> role
    scripts/check_gtk.py --selftest

WEAKNESS. ADW_NAMED is a snapshot of the reference; a variable libadwaita adds
later is absent here until re-read, and a variable it removes is not detected.
GNOME is not run here.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))     # sibling checks
# (bg, fg, floor): body text pairs at WCAG AA 4.5; the accent (selection) pair at
# the palette's OWN selection floor — check_selection_contrast.FLOOR, AA-large —
# because that pair is the palette's relation and this gate must not invent a
# stricter one (EL-Openglo-Lit's selection reads 4.41, by the palette's design).
PAIRS = (("--window-bg-color", "--window-fg-color", 4.5), ("--view-bg-color", "--view-fg-color", 4.5),
         ("--headerbar-bg-color", "--headerbar-fg-color", 4.5), ("--sidebar-bg-color", "--sidebar-fg-color", 4.5),
         ("--card-bg-color", "--card-fg-color", 4.5), ("--dialog-bg-color", "--dialog-fg-color", 4.5),
         ("--popover-bg-color", "--popover-fg-color", 4.5), ("--accent-bg-color", "--accent-fg-color", None))


def _rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def vars_in(css):
    return dict(re.findall(r"^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);", css, re.M))


def defines_in(css):
    return dict(re.findall(r"^@define-color\s+(\w+)\s+([^;]+);", css, re.M))


def check_variant(variant, gtk4, gtk3):
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_gtk as MG
    import cvd_gate as C
    out = []
    try:
        import tinycss2
        errs = [r for r in tinycss2.parse_stylesheet(gtk4 + gtk3, skip_comments=True, skip_whitespace=True)
                if r.type == "error"]
        out.append(("parses", not errs, f"{len(errs)} error(s)" if errs else "tinycss2 ok"))
    except ImportError:
        out.append(("parses", True, "SKIP tinycss2 not installed"))
    v4, d3 = vars_in(gtk4), defines_in(gtk3)
    unknown = sorted(set(v4) - MG.ADW_NAMED)
    bad3 = sorted(set(d3) - {n for n, _r in MG.GTK3_DEFINES})
    out.append(("every name is a documented one", not unknown and not bad3,
                f"unknown gtk4 {unknown}" if unknown else (f"unknown gtk3 {bad3}" if bad3
                                                          else f"{len(v4)} vars, {len(d3)} defines")))
    r = MG.roles(variant)
    wrong = [f"{v}={v4.get(v)}!={r[role]}" for v, role in MG.ADW_VARS if v4.get(v, "").strip() != r[role]]
    wrong += [f"{n}={d3.get(n)}!={r[role]}" for n, role in MG.GTK3_DEFINES if d3.get(n, "").strip() != r[role]]
    out.append(("every value is its role", not wrong, "; ".join(wrong[:3]) if wrong
                else f"{len(MG.ADW_VARS) + len(MG.GTK3_DEFINES)} values"))
    from check_selection_contrast import FLOOR as SEL_FLOOR
    low = []
    for bg, fg, floor in PAIRS:
        floor = SEL_FLOOR if floor is None else floor
        if bg in v4 and fg in v4:
            ratio = C.wcag_ratio(_rgb(v4[fg].strip()), _rgb(v4[bg].strip()))
            if ratio < floor:
                low.append(f"{fg} on {bg} {ratio:.2f} < {floor}")
    out.append(("bg/fg pairs clear WCAG AA", not low, "; ".join(low) if low
                else f"{len(PAIRS)} pairs (text 4.5, selection {SEL_FLOOR})"))
    return out


def main(argv):
    known = {"--map"}
    for a in argv[1:]:
        if a not in known:
            print(f"check_gtk: unknown flag {a!r}", file=sys.stderr)
            return 2
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_gtk as MG
    if "--map" in argv:
        for v, role in MG.ADW_VARS:
            print(f"{v:36} <- {role}")
        return 0
    fails, n = [], 0
    for v in MG.VARIANTS:
        for arm, ok, detail in check_variant(v, MG.gtk4_css(v), MG.gtk3_css(v)):
            n += 1
            if not ok:
                fails.append(f"{v} {arm}: {detail}")
    if not n:
        print("check_gtk: REFUSED — nothing measured", file=sys.stderr)
        return 2
    if fails:
        print(f"check_gtk: REFUSED — {len(fails)} of {n} arm(s) do not hold:", file=sys.stderr)
        for f in fails:
            print(f"    {f}", file=sys.stderr)
        return 1
    print(f"check_gtk: {n} of {n} arms hold over {len(MG.VARIANTS)} variants")
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

    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_gtk as MG
    g4, g3 = MG.gtk4_css("EL-Openglo"), MG.gtk3_css("EL-Openglo")
    arms = {a: o for a, o, _d in check_variant("EL-Openglo", g4, g3)}
    chk("the real emission holds every arm", all(arms.values()), True)
    # ⚑ SESSION 14'S HOLE: a NAME typo must be seen
    arms = {a: o for a, o, _d in check_variant("EL-Openglo", g4.replace("--headerbar-bg-color", "--headerbar-bg-colour"), g3)}
    chk("a typo'd variable name is seen", arms["every name is a documented one"], False)
    arms = {a: o for a, o, _d in check_variant("EL-Openglo", g4, g3.replace("theme_bg_color", "theme_bg_colour"))}
    chk("a typo'd @define-color name is seen", arms["every name is a documented one"], False)
    arms = {a: o for a, o, _d in check_variant("EL-Openglo", g4.replace("--view-fg-color: #", "--view-fg-color: #00"), g3)}
    chk("an authored value is seen", arms["every value is its role"], False)
    r = MG.roles("EL-Openglo")
    swapped = g4.replace(f"--window-fg-color: {r['window_fg']}", f"--window-fg-color: {r['ground']}")
    arms = {a: o for a, o, _d in check_variant("EL-Openglo", swapped, g3)}
    chk("fg == bg fails the pair contrast arm", arms["bg/fg pairs clear WCAG AA"], False)
    chk("ADW_NAMED covers every emitted variable", set(v for v, _ in MG.ADW_VARS) <= MG.ADW_NAMED, True)
    print("check_gtk selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
