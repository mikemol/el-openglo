#!/usr/bin/env python3
"""check_symbol.py — the per-symbol witness for the design log's open work.

⚑ WHY THIS EXISTS.  The design log's 35 open items lived as PROSE that a reader
summarised. `cotype_index.py` made the log queryable — sessions, symbols, ledger
buckets — but every claim in `catalog/cotype/` was about the READING APPARATUS
("does the log parse", "is it coherent"), not about the work. Four meta-claims
over thirty-five items. That is a migration stopped halfway: the log became
legible without becoming checkable, so "what is actually done?" still resolved to
someone's reading rather than to the tree.

This tool closes that. Each open symbol gets a WITNESS — a predicate over the
tree that is true when the work exists — so the log's worklist becomes the same
kind of object as the repo's own: open exactly when its check exits non-zero.

    scripts/check_symbol.py <SYMBOL>     # exit 0 iff that symbol's work is present
    scripts/check_symbol.py --list       # every symbol with a witness, and what it is
    scripts/check_symbol.py --status     # all of them, done/open
    scripts/check_symbol.py --unwitnessed  # open symbols with NO witness here

⚑ AN OPERATOR-BLOCKED SYMBOL GETS NO WITNESS, AND THAT IS NOT AN OMISSION.  The
log's LIVE bucket is work only a human at a real desktop can verify — "does the
boot splash look right", "is the ghost legible at a glance". No predicate over
this tree can discharge one, and writing a green-by-default check for it would
manufacture exactly the unfalsifiable claim the whole worklist refuses. They are
covered by @OPERATOR (are they legible and correctly bucketed), never by @done.

⚑ A WITNESS IS NECESSARY, NOT SUFFICIENT.  `SegmentChar wired into make_clock`
does not prove the clock renders correctly — that is the LIVE half. The witness
asserts the ARTIFACT EXISTS; the operator asserts it is right. Claiming more
would be the same overclaim the log's own `✓PoC` was careful to avoid.

⚑ FIVE OF THE FIRST SEVEN PASSES WERE FALSE, AND THEY FAILED THE SAME WAY: the
witness was aimed at a NOUN THE LOG MENTIONS instead of the CRITERIA THE LOG
STATES.  ⊕PLA2 matched the frame() helper that built the panel it was deferred
FROM; ⊕KVT2 matched the three widgets that shipped, when it means coverage beyond
them; ⊕SEG-FONT-PROJECT matched the PoC the log calls "NOT wired, NOT calibrated,
NOT validated"; ⊕SEG-TABLE-VALIDATE matched the words "cross-check" in a
docstring; ⊕PANEL-LAYOUT matched the basic layout.js it exists to improve on.

A deferred item is usually deferred FROM something adjacent that already exists,
so the near miss is the DEFAULT failure, not an unlucky one. When the log
enumerates what remains ("NOT wired to fontTools, NOT calibrated, NOT validated
against all 44"), that list IS the witness. When it does not, aim at a definition
rather than a mention — a `def`-anchored pattern over the bare word "validate".
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "scripts", "cotype_index.py")


# Symbols no predicate over THIS tree can decide, each with the reason. These are
# not gaps: a witness here would be an unfalsifiable claim wearing a checkmark.
UNWITNESSABLE = {
    "⊕GTK-ADW": "the log calls it unreachable by design — pure-libadwaita apps "
                "honour no override, so no artifact here can satisfy it (:704)",
}


def _reads(path, pat, count=1):
    """True iff `path` matches `pat` at least `count` times."""
    p = os.path.join(ROOT, path)
    if not os.path.isfile(p):
        return False
    text = open(p, encoding="utf-8", errors="replace").read()
    return len(re.findall(pat, text)) >= count


def _any(paths, pat):
    return any(_reads(p, pat) for p in paths)


# symbol -> (what the witness looks for, predicate)
# ⚑ EACH PREDICATE IS DERIVED FROM THE LOG'S OWN STATEMENT of the item, cited by
# line. A witness invented from the symbol's NAME would test my paraphrase.
WITNESS = {
    # ── BUILD: touches the shipped package ──
    "⊕SEGMENT-SUBSTRATE": (
        "SegmentChar is the one geometry substrate under wallpaper/clock/marquee/plymouth,"
        " not just defined in its own emitter (:4399)",
        lambda: _any(["make_wallpaper.py", "make_wallpaper_live.py", "make_clock.py",
                      "make_plymouth.py"], r"SegmentChar")),
    "⊕NOTIFY-MATRIXRENDER": (
        "the marquee renders via a MATRIX, not a font — the topology the user corrected (:4524)",
        lambda: _reads("make_notify_marquee.py", r"(?i)matrix")),
    "⊕MATRIX-FONT-INPUT": (
        "arbitrary text reaches the matrix by rasterising a font into it (:4534)",
        lambda: _reads("make_notify_marquee.py", r"(?i)rasteri|font.*matrix|matrix.*font")),

    # ── RESEARCH: design work, no package impact ──
    # ⚑ THE LOG STATES THIS ONE'S CRITERIA AND MY FIRST WITNESS IGNORED THEM.  It
    # matched the PoC and reported done, while the log says outright: "PoC-level
    # … NOT wired to fontTools glyph ingest, NOT calibrated, NOT validated against
    # all 44. A proven PRINCIPLE, not a shipped pipeline" (:4644). When the log
    # enumerates what remains, the witness is that list — not the name.
    "⊕SEG-FONT-PROJECT": (
        "wired to real fontTools glyph ingest and validated across all 44 glyphs,"
        " not the synthetic-stroke PoC (:4644)",
        lambda: _reads("project_font.py", r"(?i)fontTools|TTFont") and
                _reads("project_font.py", r"(?i)all.?44|validate")),
    "⊕SEG-PROJECT-CALIBRATE": (
        "bandwidth/tau CALIBRATED from agreement with the authored 44, not hand-set (:4631)",
        lambda: _any(["project_font.py", "glyph_match.py"],
                     r"(?i)calibrat|bandwidth.*agree|tau.*agree")),
    # ⚑ MATCHED THE WORD IN A COMMENT.  The first witness hit "cross-check" inside
    # a segment_topology docstring — prose ABOUT the idea, not a routine doing it.
    # A witness over source must aim at a definition, not a noun.
    "⊕SEG-TABLE-VALIDATE": (
        "a routine that cross-checks the projection against the authored table,"
        " not a comment mentioning the idea (:4632)",
        lambda: _any(["project_font.py", "glyph_match.py", "segment_topology.py"],
                     r"def\s+\w*(?:validate|crosscheck|cross_check)\w*")),
    "⊕SEG22-DESCENDERS": (
        "lowercase g/j/p/q/y carry descender segments in a 22-seg glyph table (:4455)",
        lambda: _reads("segment_topology.py", r"LETTERS22|DESCENDER_GLYPHS|glyph22")),
    "⊕GHOST-DENSITY": (
        "ghost separation re-verified at 22-seg inter-stroke density, where strokes"
        " tighten and the same Lc may read mushier (:4459)",
        lambda: _any(["scripts/check_selection_contrast.py", "cvd_gate.py",
                      "glance_audit.py"], r"(?i)inter.?stroke|density.*ghost|ghost.*density")),

    # ── TUNE ──
    "⊕SOLVER-PERF": (
        "the solver memoizes across variants rather than re-solving each (:4182)",
        lambda: _reads("make_schemes.py", r"_palette-cache|_solved_grid") or
                _reads("make_palette.py", r"(?i)memo|lru_cache")),
    "⊕SOLVER-UI-TOKENS": (
        "the ~5 UI tokens are solved rather than authored (:3928)",
        lambda: _reads("make_palette.py", r"(?i)ui_token|solve_ui")),
    "⊕ICONS-INHERIT": (
        "an icon theme that INHERITS rather than reimplements a set (:2774)",
        lambda: _any(["make_deb.py", "make_plasma.py"], r"(?i)Inherits=.*icon|icon.*Inherits")),
    "⊕CURSOR-INHERIT": (
        "a cursor theme that inherits (:2806)",
        lambda: _any(["make_deb.py", "make_plasma.py"], r"(?i)cursor.*Inherits|Inherits=.*cursor")),
    # The BASIC layout.js already ships (it sets wallpaper + adds the clock); the
    # item is a RICHER template than that (:2785). Witnessing layout.js at all
    # reports the thing being improved on as the improvement.
    "⊕PANEL-LAYOUT": (
        "a richer layout template than the basic wallpaper+clock one that ships —"
        " panel arrangement, systray, task manager (:2785)",
        lambda: _reads("make_deb.py", r"(?i)systemtray|taskmanager|panel\.addWidget")),
    "⊕TASKSWITCH": (
        "an Alt+Tab task switcher in the Plasma Style (:2787)",
        lambda: _any(["make_plasma.py", "make_deb.py"], r"(?i)windowswitcher|tabbox|taskswitch")),

    # ── TIER 3 ──
    "⊕CLOCK-VECTOR": (
        "the clock draws vector segments rather than raster (:4228)",
        lambda: _reads("make_clock.py", r"(?i)Shape\s*\{|ShapePath|SegmentChar")),
    "⊕PLYMOUTH-VECTOR": (
        "the boot splash is vector rather than PNG-baked (:4228)",
        lambda: _reads("make_plymouth.py", r"(?i)svg|vector|SegmentChar")),

    # ── RESIDUE: kept, deliberately unbuilt ──
    "⊕NOTIFY-SEGRENDER": (
        "the ticker renders in the actual 7-seg/dot primitive (:3568)",
        lambda: _reads("make_notify_marquee.py", r"(?i)SegmentChar|segment_topology")),
    "⊕SUPERSAMPLE-WP": (
        "the wallpaper generator supersamples at generation time (:2583)",
        lambda: _reads("make_wallpaper.py", r"(?i)supersampl|scale\s*=\s*[2-9]")),
    "⊕HDR-EMIT": (
        "extended-range colour is emitted, once Qt exposes it to QML (:2411)",
        lambda: _any(["make_schemes.py", "make_clock.py"], r"(?i)\bhdr\b|extended.?range")),
    "⊕VER-SYSCLOCK": (
        "the system clock itself renders in EL, not only the plasmoid (:2074)",
        lambda: _reads("make_deb.py", r"(?i)sysclock|system.*clock")),
    # ⚑ ⊕GTK-ADW HAS NO WITNESS AND MUST NOT GET ONE.  The log calls it
    # "unreachable by design" (:704): pure-libadwaita apps honour no override, so
    # NO artifact in this tree can ever satisfy it. My first witness matched
    # `gtk-4.0` in make_deb and reported it DONE — dressing an impossibility as an
    # achievement. It belongs in UNWITNESSABLE below, beside the operator-blocked
    # work, for the same reason: no predicate here decides it.
    # Buttons, line edits and the segmented progress bar SHIPPED; ⊕KVT2 is the
    # FULL vocabulary beyond them, deferred "if the element vocabulary proves
    # large" (:585). Witnessing the shipped three would report the deferral done.
    "⊕KVT2": (
        "Kvantum coverage beyond the shipped buttons/line-edits/progress-bar —"
        " scrollbars, sliders, tabs, menus (:585)",
        lambda: _reads("make_kvantum.py", r"(?i)ScrollBar|Slider|TabWidget|MenuItem")),
    # ⚑ THIS WITNESS WAS WRONG ONCE, AND IT PASSED.  It matched `FrameSvg|prefix`,
    # which hits the generic frame() helper building the panel/dialog/tooltip that
    # were DONE. What ⊕PLA2 defers is the WIDGET-BY-WIDGET SVGs — tasks, buttons,
    # sliders — whose "prefix vocabularies are larger and each wrong ID renders
    # invisible chrome" (:541). A witness aimed at the wrong noun reports the
    # completed work as evidence for the deferred work.
    "⊕PLA2": (
        "widget-by-widget Plasma SVGs (tasks/buttons/sliders), not just the panel,"
        " dialog and tooltip frames that shipped (:541)",
        lambda: _reads("make_plasma.py", r"(?i)\btasks\b|\bbutton\b|\bslider\b")),
    "⊕KNB2": (
        "the designer's export is wired through the actual generators (:787)",
        lambda: _any(["make_palette.py", "make_schemes.py"], r"(?i)designer|phosphor-designer")),
}


def open_symbols():
    """{symbol: bucket} for the log's currently-open work."""
    import json
    r = subprocess.run([sys.executable, INDEX, "--json"],
                       capture_output=True, text=True, cwd=ROOT)
    if r.returncode != 0:
        return None
    out = {}
    for bucket, syms in json.loads(r.stdout)["open"].items():
        for s in syms:
            out[s] = bucket
    return out


def main(argv):
    known = {"--list", "--status", "--unwitnessed", "--bucket"}
    args = [a for a in argv[1:] if a.startswith("--")]
    syms = [a for a in argv[1:] if not a.startswith("--")]
    for a in args:
        if a not in known:
            print(f"check_symbol: unknown flag {a!r}", file=sys.stderr)
            return 2

    if "--bucket" in args:
        # exit 0 iff EVERY witnessed symbol in this bucket is present.
        # ⚑ THE BUCKET IS THE LOG'S OWN UNIT, so a claim per bucket tracks the
        # log's structure rather than imposing one. Per-symbol detail is --status.
        if len(syms) != 1:
            print("check_symbol: --bucket needs exactly one bucket name",
                  file=sys.stderr)
            return 2
        want = syms[0].upper().replace("_", " ")
        opn = open_symbols()
        if opn is None:
            print("check_symbol: REFUSED — the index would not run", file=sys.stderr)
            return 2
        members = sorted(s for s, b in opn.items()
                         if b.upper() == want and s in WITNESS)
        if not members:
            print(f"check_symbol: REFUSED — no witnessed symbol in bucket {want!r}; "
                  f"the bucket is empty, renamed, or unwitnessed", file=sys.stderr)
            return 2
        openv = [s for s in members if not WITNESS[s][1]()]
        if openv:
            print(f"check_symbol: {want} — {len(openv)} of {len(members)} open:",
                  file=sys.stderr)
            for s in openv:
                print(f"    {s}: {WITNESS[s][0]}", file=sys.stderr)
            return 1
        print(f"check_symbol: {want} — {len(members)} of {len(members)} present")
        return 0

    if "--list" in args:
        for s, (what, _) in sorted(WITNESS.items()):
            print(f"{s}\t{what}")
        return 0

    opn = open_symbols()
    if opn is None:
        print("check_symbol: REFUSED — the index would not run", file=sys.stderr)
        return 2

    if "--unwitnessed" in args:
        # LIVE is operator-blocked BY DESIGN, so it is not a gap.
        gaps = sorted(s for s, b in opn.items()
                      if b != "LIVE" and s not in WITNESS
                      and s not in UNWITNESSABLE)
        for s in gaps:
            print(f"{s}\t{opn[s]}")
        for s, why in sorted(UNWITNESSABLE.items()):
            print(f"{s}\t(by design) {why}")
        return 0

    if "--status" in args:
        for s in sorted(WITNESS):
            what, pred = WITNESS[s]
            state = "done" if pred() else "open"
            print(f"{state:5} {s:26} {opn.get(s, '(not in the open set)')}")
        return 0

    if not syms:
        print("check_symbol: name a symbol, or use --list / --status / --unwitnessed",
              file=sys.stderr)
        return 2
    rc = 0
    for s in syms:
        key = s if s.startswith("⊕") else "⊕" + s
        if key not in WITNESS:
            print(f"check_symbol: REFUSED — no witness for {key}. Operator-blocked "
                  f"work has none BY DESIGN; anything else is a gap to fill.",
                  file=sys.stderr)
            rc = max(rc, 2)
            continue
        what, pred = WITNESS[key]
        if pred():
            print(f"check_symbol: {key} — present ({what})")
        else:
            print(f"check_symbol: {key} — OPEN: {what}", file=sys.stderr)
            rc = max(rc, 1)
    return rc


def _selftest():
    ok = True

    def check(label, got, want):
        nonlocal ok
        if got != want:
            print(f"  FAIL {label}: got {got!r} want {want!r}")
            ok = False
        else:
            print(f"  ok   {label}")

    check("every witness carries a description",
          all(w and callable(p) for w, p in WITNESS.values()), True)
    check("every description cites a log line",
          all(re.search(r":\d+\)", w) for w, _ in WITNESS.values()), True)
    opn = open_symbols()
    check("the index answers", opn is not None, True)
    if opn:
        # ⚑ NO NON-LIVE OPEN SYMBOL MAY LACK A WITNESS. That is the migration
        # being complete: prose became predicate for everything a check CAN
        # reach, and the rest is honestly operator-blocked.
        gaps = sorted(s for s, b in opn.items() if b != "LIVE"
                      and s not in WITNESS and s not in UNWITNESSABLE)
        check(f"no unwitnessed non-LIVE open symbol ({gaps})", gaps, [])
        check("every unwitnessable symbol states why",
              all(UNWITNESSABLE.values()), True)
        check("unwitnessable and witnessed are disjoint",
              sorted(set(UNWITNESSABLE) & set(WITNESS)), [])
        # ⚑ AND NO WITNESS FOR OPERATOR-BLOCKED WORK: a green check there would
        # be an unfalsifiable claim wearing a checkmark.
        live = sorted(s for s, b in opn.items() if b == "LIVE" and s in WITNESS)
        check(f"no witness claims LIVE work ({live})", live, [])
    # every predicate must RUN without raising
    for s, (_w, p) in WITNESS.items():
        try:
            p()
        except Exception as e:                      # noqa: BLE001
            check(f"{s} predicate runs", f"raised {e}", "ok")
    print("check_symbol selftest:", "PASS" if ok else "FAIL")
    return ok


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(0 if _selftest() else 1)
    sys.exit(main(sys.argv))
