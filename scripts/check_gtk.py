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

    scripts/check_gtk.py            # the verdict, as opa_gate gtk decides it
    scripts/check_gtk.py --json     # the measurement policy/gtk.rego decides
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

from check_selection_contrast import schemes, roster_drift   # noqa: E402  (roster authority)


def _rgb(hexs):
    hexs = hexs.lstrip("#")
    return tuple(int(hexs[i:i + 2], 16) for i in (0, 2, 4))


def vars_in(css):
    return dict(re.findall(r"^\s*(--[a-z0-9-]+)\s*:\s*([^;]+);", css, re.M))


def defines_in(css):
    return dict(re.findall(r"^@define-color\s+(\w+)\s+([^;]+);", css, re.M))


def facts(variant, gtk4, gtk3):
    """What one variant's two sheets SAY — no verdict (policy/gtk.rego rules, W50).

    `parse_errors` is null when tinycss2 is absent (a fact about the machine).
    ⚑ A PAIR WHOSE VARIABLE IS ABSENT IS REPORTED, NOT DROPPED (W65): it used to
    be skipped, so deleting a variable shrank the pair population and stayed
    green. Here it is `present: false, ratio: null`, and the policy denies it."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_gtk as MG
    import cvd_gate as C
    from check_selection_contrast import FLOOR as SEL_FLOOR
    try:
        import tinycss2
        parse_errors = sum(1 for r in tinycss2.parse_stylesheet(
            gtk4 + gtk3, skip_comments=True, skip_whitespace=True) if r.type == "error")
    except ImportError:
        parse_errors = None
    v4, d3 = vars_in(gtk4), defines_in(gtk3)
    r = MG.roles(variant)
    wrong = [{"name": v, "role": role, "got": v4.get(v, "").strip(), "want": r[role]}
             for v, role in MG.ADW_VARS if v4.get(v, "").strip() != r[role]]
    wrong += [{"name": n, "role": role, "got": d3.get(n, "").strip(), "want": r[role]}
              for n, role in MG.GTK3_DEFINES if d3.get(n, "").strip() != r[role]]
    pairs = []
    for bg, fg, floor in PAIRS:
        present = bg in v4 and fg in v4
        pairs.append({"bg": bg, "fg": fg, "floor": SEL_FLOOR if floor is None else floor,
                      "present": present,
                      "ratio": C.wcag_ratio(_rgb(v4[fg].strip()), _rgb(v4[bg].strip()))
                      if present else None})
    return {"id": variant, "parse_errors": parse_errors,
            "unknown_gtk4": sorted(set(v4) - MG.ADW_NAMED),
            "unknown_gtk3": sorted(set(d3) - {n for n, _r in MG.GTK3_DEFINES}),
            "wrong_values": wrong, "pairs": pairs}


def measure():
    """{roster, roster_drift, cases} over the DECLARED roster (make_schemes.GRID).

    ⚑ W65: the population was make_gtk.VARIANTS — the emitter's own typed list —
    so dropping a variant there took "24 of 24" to "20 of 20", rc 0. It is now
    GRID (via check_selection_contrast.schemes); the emitter's drift is reported."""
    if ROOT not in sys.path:
        sys.path.insert(0, ROOT)
    import make_gtk as MG
    roster = schemes()
    return {"roster": list(roster),
            "pairs_declared": len(PAIRS),
            "roster_drift": [{"variant": v, "why": why}
                             for v, why in roster_drift(MG.VARIANTS, "make_gtk")],
            "cases": [facts(v, MG.gtk4_css(v), MG.gtk3_css(v)) for v in roster]}


def main(argv):
    known = {"--map", "--json"}
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
    if "--json" in argv:
        import json
        print(json.dumps(measure(), indent=1))
        return 0
    import opa_gate
    return opa_gate.gate("gtk")


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
    # The MEASUREMENT can see; what is a defect is policy/gtk_test.rego's (W50).
    g4, g3 = MG.gtk4_css("EL-Openglo"), MG.gtk3_css("EL-Openglo")
    f = facts("EL-Openglo", g4, g3)
    chk("the real emission measures clean",
        (f["unknown_gtk4"], f["unknown_gtk3"], f["wrong_values"],
         all(p["present"] for p in f["pairs"]), len(f["pairs"])), ([], [], [], True, len(PAIRS)))
    # ⚑ SESSION 14'S HOLE: a NAME typo must be seen
    chk("a typo'd variable name is seen",
        facts("EL-Openglo", g4.replace("--headerbar-bg-color", "--headerbar-bg-colour"), g3)["unknown_gtk4"],
        ["--headerbar-bg-colour"])
    chk("a typo'd @define-color name is seen",
        facts("EL-Openglo", g4, g3.replace("theme_bg_color", "theme_bg_colour"))["unknown_gtk3"],
        ["theme_bg_colour"])
    chk("an authored value is seen",
        [w["name"] for w in facts("EL-Openglo", g4.replace("--view-fg-color: #", "--view-fg-color: #00"), g3)["wrong_values"]],
        ["--view-fg-color"])
    r = MG.roles("EL-Openglo")
    swapped = g4.replace(f"--window-fg-color: {r['window_fg']}", f"--window-fg-color: {r['ground']}")
    win = next(p for p in facts("EL-Openglo", swapped, g3)["pairs"] if p["fg"] == "--window-fg-color")
    chk("fg == bg is measured at ratio 1", round(win["ratio"], 2), 1.0)
    chk("ADW_NAMED covers every emitted variable", set(v for v, _ in MG.ADW_VARS) <= MG.ADW_NAMED, True)
    # ⚑ W65: an absent pair variable is REPORTED absent, not dropped from the pairs
    gone = facts("EL-Openglo", g4.replace("--card-fg-color", "--card-fg-gone"), g3)["pairs"]
    chk("an absent pair variable is reported, the pair count kept",
        (len(gone), [p["fg"] for p in gone if not p["present"]]), (len(PAIRS), ["--card-fg-color"]))
    # ⚑ THE LIVENESS CONJUNCT: every declared variant measured, and not vacuously
    got = measure()
    chk("every declared variant is measured",
        sorted(c["id"] for c in got["cases"]), sorted(got["roster"]))
    chk("and it is not vacuously complete", len(got["cases"]) > 0, True)
    saved = list(MG.VARIANTS)
    try:
        MG.VARIANTS[:] = saved[:-1]
        chk("an emitter that drops a GRID variant is reported as drift",
            len(measure()["roster_drift"]) > 0, True)
    finally:
        MG.VARIANTS[:] = saved
    print("check_gtk selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
